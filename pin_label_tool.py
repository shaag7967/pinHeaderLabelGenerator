#!/usr/bin/env python3
"""
Pin Header Label Generator
==========================

Print a pin-out label on paper, push the header pins through the paper and the
signal names sit right next to each pin - handy for plugging in jumper wires.

Features
  * 1- or 2-row pin headers, any number of rows, adjustable pitch
  * Labels fan out with leader lines when the text is taller than the pitch
  * Per-pin colors (jumper-wire palette or any custom color)
  * Optional pin numbering (zigzag / DIP / column-wise) and pin-1 marker
  * Exports: PDF (vector, mm-exact), PNG (with DPI metadata), SVG; direct printing
  * Projects are saved as JSON

Requirements: Python 3.9+, PySide6   (pip install PySide6)

GUI:       python pin_label_tool.py [project.json]
Headless:  python pin_label_tool.py project.json --pdf out.pdf [--png out.png --dpi 600] [--svg out.svg]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from PySide6.QtCore import QMarginsF, QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import (
    QAction, QColor, QFont, QFontDatabase, QFontMetricsF, QGuiApplication, QIcon,
    QImage, QKeySequence, QPageLayout, QPageSize, QPainter, QPdfWriter, QPen,
    QPixmap, QPolygonF,
)

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------
MM_PER_PT = 25.4 / 72.0
REF_PX = 100.0                         # reference font pixel size; text is scaled from this
V_PROBE = "Hbdfhklgjpqy_0123456789"    # probe string for the vertical text extent
PAGE_W, PAGE_H = 210.0, 297.0          # A4 portrait in mm
PAGE_MARGIN = 12.0
FONT_PT_MIN, FONT_PT_MAX = 4.0, 14.0

# Typical Dupont jumper wire colors plus a few light tints (ink saving)
PALETTE = [
    ("Schwarz", "#1b1b1b"),
    ("Braun", "#7b4a1e"),
    ("Rot", "#d32f2f"),
    ("Orange", "#f57c00"),
    ("Gelb", "#fdd835"),
    ("Grün", "#2e7d32"),
    ("Blau", "#1565c0"),
    ("Violett", "#7b1fa2"),
    ("Grau", "#808080"),
    ("Weiß", "#ffffff"),
    ("Hellrot", "#ef9a9a"),
    ("Hellgelb", "#fff59d"),
    ("Hellgrün", "#a5d6a7"),
    ("Hellblau", "#90caf9"),
]
PALETTE_NAMES = {h.lower(): n for n, h in PALETTE}

RE_GND = re.compile(r"^(gnd\w*|agnd|dgnd|pgnd|vss\w*|0v|masse)$", re.I)
RE_PWR = re.compile(r"^(\+?\d+([.,]\d+)?v\d*|vcc\w*|vdd\w*|vin|vbat\w*|vbus|v\+)$", re.I)


# ----------------------------------------------------------------------------
# Data model
# ----------------------------------------------------------------------------
@dataclass
class Pin:
    label: str = ""
    color: str = ""          # '#rrggbb' or '' (no color)


@dataclass
class Project:
    title: str = ""
    rows: int = 15
    cols: int = 2                    # 1 or 2 pin rows
    side_mode: str = "right"         # single-row header only: right | left | alternate
    pitch: float = 2.54              # mm
    font_family: str = ""            # '' = system default
    font_pt: float = 6.0
    bold: bool = False
    gap_mm: float = 1.2              # distance header outline -> label
    leaders: str = "auto"            # auto (only where labels are shifted) | always
    color_style: str = "fill"        # fill | text | outline
    numbering: str = "none"          # none | zigzag | dip | column
    pin1_marker: bool = False
    outline: bool = True
    cut_frame: bool = True
    copies: int = 1
    scale_x: float = 100.0           # printer scale correction in percent
    scale_y: float = 100.0
    scale_bar: bool = True
    # pins[row][col]; always 2 entries per row, may hold more rows than used
    # (keeps data when the user temporarily reduces rows/cols)
    pins: list = field(default_factory=list)

    def ensure(self) -> None:
        while len(self.pins) < self.rows:
            self.pins.append([Pin(), Pin()])
        for row in self.pins:
            while len(row) < 2:
                row.append(Pin())

    def trim(self) -> None:
        del self.pins[self.rows:]

    def clamp(self) -> None:
        self.rows = max(1, min(200, int(self.rows)))
        self.cols = 1 if int(self.cols) == 1 else 2
        self.pitch = max(0.5, min(20.0, float(self.pitch)))
        self.font_pt = max(FONT_PT_MIN, min(FONT_PT_MAX, float(self.font_pt)))
        self.gap_mm = max(0.3, min(30.0, float(self.gap_mm)))
        self.copies = max(1, min(60, int(self.copies)))
        self.scale_x = max(50.0, min(150.0, float(self.scale_x)))
        self.scale_y = max(50.0, min(150.0, float(self.scale_y)))
        if self.side_mode not in ("right", "left", "alternate"):
            self.side_mode = "right"
        if self.leaders not in ("auto", "always"):
            self.leaders = "auto"
        if self.color_style not in ("fill", "text", "outline"):
            self.color_style = "fill"
        if self.numbering not in ("none", "zigzag", "dip", "column"):
            self.numbering = "none"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["pins"] = [[asdict(p) for p in row[: self.cols]] for row in self.pins[: self.rows]]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        prj = cls()
        for k, v in d.items():
            if k == "pins" or not hasattr(prj, k):
                continue
            setattr(prj, k, type(getattr(prj, k))(v))
        prj.pins = [
            [Pin(label=str(p.get("label", "")), color=str(p.get("color", ""))) for p in row]
            for row in d.get("pins", [])
        ]
        prj.clamp()
        prj.ensure()
        return prj

    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Project":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def clean_label(s: str) -> str:
    """Normalize pasted text: strip bullets, treat 'leer' / '-' as empty."""
    s = s.strip()
    s = re.sub(r"^[*\-•·]\s+", "", s)
    if s.lower() in ("leer", "-", "–", "—"):
        return ""
    return s


def pin_number(prj: Project, r: int, c: int) -> int:
    if prj.numbering == "none":
        return 0
    if prj.cols == 1:
        return r + 1
    if prj.numbering == "zigzag":
        return 2 * r + c + 1
    if prj.numbering == "dip":
        return r + 1 if c == 0 else 2 * prj.rows - r
    return c * prj.rows + r + 1          # column-wise


def fmt(v: float, nd: int = 2) -> str:
    """German number formatting."""
    s = f"{v:.{nd}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".") if nd > 1 else s
    return s.replace(".", ",")


# ----------------------------------------------------------------------------
# Color helpers
# ----------------------------------------------------------------------------
def luminance(c: QColor) -> float:
    def ch(v: int) -> float:
        x = v / 255.0
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c.red()) + 0.7152 * ch(c.green()) + 0.0722 * ch(c.blue())


def text_on(c: QColor) -> QColor:
    """Black or white, whichever has more contrast on background c."""
    lum = luminance(c)
    return QColor("#ffffff") if 1.05 / (lum + 0.05) > (lum + 0.05) / 0.05 else QColor("#111111")


def ink(c: QColor) -> QColor:
    """Color usable for thin lines / text on white paper (darkens light colors)."""
    return c.darker(170) if luminance(c) > 0.55 else c


def color_name(h: str) -> str:
    return PALETTE_NAMES.get(h.lower(), h) if h else ""


# ----------------------------------------------------------------------------
# Drawing primitives (all coordinates in mm)
# ----------------------------------------------------------------------------
def make_font(family: str, bold: bool) -> QFont:
    f = QFont(family) if family else QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
    f.setPixelSize(int(REF_PX))
    f.setBold(bold)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    f.setKerning(True)
    return f


def draw_text(painter: QPainter, font: QFont, scale: float, x: float, baseline: float,
              text: str, color: QColor) -> None:
    """Draw text with a reference-size font scaled to mm (device independent)."""
    if not text:
        return
    painter.save()
    painter.translate(x, baseline)
    painter.scale(scale, scale)
    painter.setFont(font)
    painter.setPen(QPen(color))
    painter.drawText(QPointF(0.0, 0.0), text)
    painter.restore()


def dashed_pen(color: QColor, width: float, dash: float, space: float) -> QPen:
    pen = QPen(color, width)
    pen.setDashPattern([dash / width, space / width])   # pattern is in units of pen width
    return pen


def place_1d(desired: list[float], min_dist: float) -> list[float]:
    """Place sorted label positions with a minimum distance, minimizing the
    squared displacement (clusters are merged and centered on their pins)."""
    clusters: list[list] = []        # [first_index, count, top]
    for i, d in enumerate(desired):
        clusters.append([i, 1, d])
        while len(clusters) > 1:
            a, b = clusters[-2], clusters[-1]
            if a[2] + a[1] * min_dist <= b[2] + 1e-9:
                break
            first, n = a[0], a[1] + b[1]
            top = sum(desired[first + k] - k * min_dist for k in range(n)) / n
            clusters[-2:] = [[first, n, top]]
    out: list[float] = []
    for _first, n, top in clusters:
        out += [top + k * min_dist for k in range(n)]
    return out


# ----------------------------------------------------------------------------
# Layout of one label sheet
# ----------------------------------------------------------------------------
@dataclass
class LabelGeom:
    row: int
    col: int
    side: int                 # -1 = left, +1 = right
    text: str
    number: str
    color: str
    px: float                 # pin center
    py: float
    y: float = 0.0            # label center
    shifted: bool = False
    box: QRectF = field(default_factory=QRectF)
    text_x: float = 0.0
    num_x: float = 0.0
    baseline: float = 0.0
    leader: list = field(default_factory=list)


class Layout:
    """Computes label geometry in mm. Origin = top-left corner of the header outline."""

    CUT_MARGIN = 2.0
    STUB = 0.6          # straight leader part outside the header outline
    MARKER_R = 0.45     # pierce marker radius
    BOX_GAP = 0.08      # min. vertical gap between stacked label boxes

    def __init__(self, prj: Project):
        prj.ensure()
        self.prj = prj
        p = prj.pitch
        self.W = prj.cols * p
        self.H = prj.rows * p

        self.font = make_font(prj.font_family, prj.bold)
        self.fm = QFontMetricsF(self.font)
        self.em = prj.font_pt * MM_PER_PT
        self.s = self.em / REF_PX
        self.num_s = self.s * 0.75
        tight = self.fm.tightBoundingRect(V_PROBE)
        self.t_top = tight.top() * self.s          # negative = above baseline
        self.t_bot = tight.bottom() * self.s
        boxed = prj.color_style in ("fill", "outline")
        self.pad_v = (0.18 if prj.color_style == "outline" else 0.12) if boxed else 0.0
        self.pad_h = (0.45 if prj.color_style == "outline" else 0.40) if boxed else 0.0
        self.box_h = (self.t_bot - self.t_top) + 2 * self.pad_v
        self.min_dist = self.box_h + self.BOX_GAP

        self.title_font = make_font(prj.font_family, True)
        self.title_fm = QFontMetricsF(self.title_font)
        self.title_s = self.s * 1.2

        self.labels: list[LabelGeom] = []
        self.shifted_count = 0
        self.fanned_sides: list[int] = []
        self.title_pos = QPointF()
        self.pin1_poly: QPolygonF | None = None
        self._build()

    # -- geometry helpers ------------------------------------------------------
    def pin_xy(self, r: int, c: int) -> tuple[float, float]:
        p = self.prj.pitch
        return (c + 0.5) * p, (r + 0.5) * p

    def side_of(self, r: int, c: int) -> int:
        if self.prj.cols == 2:
            return -1 if c == 0 else 1
        if self.prj.side_mode == "left":
            return -1
        if self.prj.side_mode == "alternate":
            return -1 if r % 2 == 0 else 1
        return 1

    # -- layout ----------------------------------------------------------------
    def _build(self) -> None:
        prj = self.prj
        groups: dict[int, list[LabelGeom]] = {-1: [], 1: []}
        for r in range(prj.rows):
            for c in range(prj.cols):
                pin = prj.pins[r][c]
                text = pin.label.strip()
                if not text:
                    continue
                px, py = self.pin_xy(r, c)
                n = pin_number(prj, r, c)
                groups[self.side_of(r, c)].append(LabelGeom(
                    row=r, col=c, side=self.side_of(r, c), text=text,
                    number=str(n) if n else "", color=pin.color, px=px, py=py))

        for side, items in groups.items():
            if not items:
                continue
            items.sort(key=lambda g: g.py)
            ys = place_1d([g.py for g in items], self.min_dist)
            disp = max(abs(y - g.py) for g, y in zip(items, ys))
            fanned = disp > 1e-3
            fan = min(14.0, max(2.0, 1.1 * disp)) if fanned else 0.0
            if fanned:
                self.fanned_sides.append(side)
                gap = max(prj.gap_mm, self.STUB + fan + 0.8)
            else:
                gap = max(prj.gap_mm, self.STUB + 0.4)
            edge = 0.0 if side < 0 else self.W
            x_in = edge + side * gap            # inner edge of the label box
            draw_leader = prj.leaders == "always" or fanned
            # number column width per side keeps the texts aligned (1 vs. 2 digits)
            ncol = max((self.fm.horizontalAdvance(g.number) * self.num_s for g in items if g.number), default=0.0)
            ngap = 0.35 * self.em if ncol else 0.0

            for g, y in zip(items, ys):
                g.y = y
                g.shifted = abs(y - g.py) > 1e-3
                self.shifted_count += int(g.shifted)
                tw = self.fm.horizontalAdvance(g.text) * self.s
                nw = self.fm.horizontalAdvance(g.number) * self.num_s if g.number else 0.0
                w = tw + ncol + ngap + 2 * self.pad_h
                g.baseline = y - (self.t_top + self.t_bot) / 2.0
                top = y - self.box_h / 2.0
                if side < 0:     # text right-aligned, number column next to the header
                    g.box = QRectF(x_in - w, top, w, self.box_h)
                    g.num_x = x_in - self.pad_h - ncol          # left-aligned in its column
                    g.text_x = g.num_x - ngap - tw
                else:            # number right-aligned in its column, text left-aligned
                    g.box = QRectF(x_in, top, w, self.box_h)
                    g.num_x = x_in + self.pad_h + ncol - nw
                    g.text_x = x_in + self.pad_h + ncol + ngap
                if draw_leader:
                    end_x = x_in - side * (0.3 if self.pad_h == 0 else 0.0)
                    start = QPointF(g.px + side * self.MARKER_R, g.py)
                    if g.shifted:
                        g.leader = [start,
                                    QPointF(edge + side * self.STUB, g.py),
                                    QPointF(edge + side * (self.STUB + fan), y),
                                    QPointF(end_x, y)]
                    else:
                        g.leader = [start, QPointF(end_x, g.py)]
                self.labels.append(g)

        # bounding box, pin-1 marker and title
        rect = QRectF(0, 0, self.W, self.H)
        for g in self.labels:
            rect = rect.united(g.box)
        if prj.pin1_marker:
            x = self.pin_xy(0, 0)[0]
            self.pin1_poly = QPolygonF([QPointF(x, -0.3), QPointF(x - 0.6, -1.3), QPointF(x + 0.6, -1.3)])
            rect = rect.united(self.pin1_poly.boundingRect())
        if prj.title.strip():
            tb = self.title_fm.tightBoundingRect(V_PROBE)
            tw = self.title_fm.horizontalAdvance(prj.title.strip()) * self.title_s
            base = min(rect.top(), 0.0) - 1.0 - tb.bottom() * self.title_s
            self.title_pos = QPointF(self.W / 2.0 - tw / 2.0, base)
            rect = rect.united(QRectF(self.title_pos.x(), base + tb.top() * self.title_s,
                                      tw, (tb.bottom() - tb.top()) * self.title_s))
        m = self.CUT_MARGIN
        self.bbox = rect.adjusted(-m, -m, m, m)

    # -- drawing ---------------------------------------------------------------
    def draw(self, painter: QPainter, origin: QPointF) -> None:
        """Draw the sheet so that its bounding box top-left lands on origin (mm)."""
        prj = self.prj
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.translate(origin.x() - self.bbox.left(), origin.y() - self.bbox.top())
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if prj.cut_frame:
            painter.setPen(dashed_pen(QColor("#9a9a9a"), 0.12, 1.2, 0.8))
            painter.drawRect(self.bbox)
        if prj.outline:
            painter.setPen(dashed_pen(QColor("#8a8a8a"), 0.12, 0.6, 0.4))
            painter.drawRect(QRectF(0, 0, self.W, self.H))

        for g in self.labels:
            if not g.leader:
                continue
            c = ink(QColor(g.color)) if g.color else QColor("#555555")
            pen = QPen(c, 0.16)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPolyline(QPolygonF(g.leader))

        by_pin = {(g.row, g.col): g for g in self.labels}
        for r in range(prj.rows):
            for c in range(prj.cols):
                cx, cy = self.pin_xy(r, c)
                self._draw_marker(painter, cx, cy, by_pin.get((r, c)))

        for g in self.labels:
            self._draw_label(painter, g)

        if self.pin1_poly is not None:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#222222"))
            painter.drawPolygon(self.pin1_poly)
        if prj.title.strip():
            draw_text(painter, self.title_font, self.title_s, self.title_pos.x(), self.title_pos.y(),
                      prj.title.strip(), QColor("#111111"))
        painter.restore()

    def _draw_marker(self, painter: QPainter, cx: float, cy: float, g: LabelGeom | None) -> None:
        r = self.MARKER_R
        if g is None:
            painter.setPen(QPen(QColor("#b0b0b0"), 0.1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            cross = QColor("#b0b0b0")
        elif g.color:
            col = QColor(g.color)
            painter.setPen(QPen(QColor("#444444") if luminance(col) > 0.5 else col.darker(140), 0.1))
            painter.setBrush(col)
            cross = text_on(col)
        else:
            painter.setPen(QPen(QColor("#333333"), 0.12))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            cross = QColor("#333333")
        painter.drawEllipse(QPointF(cx, cy), r, r)
        painter.setPen(QPen(cross, 0.06))
        k = r * 0.65
        painter.drawLine(QPointF(cx - k, cy), QPointF(cx + k, cy))
        painter.drawLine(QPointF(cx, cy - k), QPointF(cx, cy + k))

    def _draw_label(self, painter: QPainter, g: LabelGeom) -> None:
        style = self.prj.color_style
        fg = QColor("#111111")
        if g.color:
            col = QColor(g.color)
            if style == "fill":
                painter.setBrush(col)
                if luminance(col) > 0.8:
                    painter.setPen(QPen(QColor("#888888"), 0.08))
                else:
                    painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(g.box, 0.35, 0.35)
                fg = text_on(col)
            elif style == "outline":
                pw = 0.2
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(ink(col), pw))
                painter.drawRoundedRect(g.box.adjusted(pw / 2, pw / 2, -pw / 2, -pw / 2), 0.3, 0.3)
            else:
                fg = ink(col)
        draw_text(painter, self.font, self.s, g.text_x, g.baseline, g.text, fg)
        if g.number:
            nc = QColor(fg)
            nc.setAlphaF(0.6)
            draw_text(painter, self.font, self.num_s, g.num_x, g.baseline, g.number, nc)


# ----------------------------------------------------------------------------
# Page composition (A4) and outputs
# ----------------------------------------------------------------------------
def page_top(prj: Project) -> float:
    return PAGE_MARGIN + 5.0 + (10.0 if prj.scale_bar else 0.0)


def page_layout(prj: Project, lay: Layout) -> list[QPointF]:
    """Positions (top-left, mm) of all copies that fit on the page."""
    sw, sh = lay.bbox.width(), lay.bbox.height()
    x, y = PAGE_MARGIN, page_top(prj)
    right, bottom = PAGE_W - PAGE_MARGIN, PAGE_H - PAGE_MARGIN - 5.0
    out: list[QPointF] = []
    for _ in range(prj.copies):
        if x + sw > right + 1e-6 and x > PAGE_MARGIN:
            x, y = PAGE_MARGIN, y + sh + 2.0
        if y + sh > bottom + 1e-6 or x + sw > right + 1e-6:
            break
        out.append(QPointF(x, y))
        x += sw + 2.0
    return out


def draw_rulers(painter: QPainter, prj: Project, x: float, y: float, font: QFont) -> None:
    """50 mm check bar and a pitch ruler (lay the real header on it)."""
    fs = 2.0 / REF_PX
    fm = QFontMetricsF(font)
    black = QColor("#111111")
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    h = 1.4
    for i in range(5):
        painter.setPen(QPen(black, 0.1))
        painter.setBrush(black if i % 2 == 0 else QColor("#ffffff"))
        painter.drawRect(QRectF(x + 10 * i, y, 10, h))
    for i in range(6):
        t = str(10 * i)
        draw_text(painter, font, fs, x + 10 * i - fm.horizontalAdvance(t) * fs / 2, y + h + 2.3, t, black)
    draw_text(painter, font, fs, x + 52.0, y + h, "mm", black)

    p = prj.pitch
    n = max(2, min(prj.rows, 20, int(70.0 / p)))
    x2 = x + 64.0
    yb = y + h
    painter.setPen(QPen(black, 0.12))
    painter.drawLine(QPointF(x2, yb), QPointF(x2 + n * p, yb))
    for k in range(n + 1):
        tick = 1.4 if (k % 5 == 0 or k == n) else 0.8
        painter.drawLine(QPointF(x2 + k * p, yb), QPointF(x2 + k * p, yb - tick))
    txt = f"{n} × {fmt(p)} mm = {fmt(n * p)} mm (Raster)"
    draw_text(painter, font, fs, x2 + n * p + 2.0, yb, txt, black)
    painter.restore()


def draw_page(painter: QPainter, prj: Project, lay: Layout, positions: list[QPointF]) -> None:
    painter.save()
    painter.scale(prj.scale_x / 100.0, prj.scale_y / 100.0)
    font = make_font("", False)
    gray = QColor("#555555")
    y = PAGE_MARGIN + 2.4
    draw_text(painter, font, 2.4 / REF_PX, PAGE_MARGIN, y,
              "Mit 100 % bzw. „Tatsächliche Größe“ drucken – nicht „An Seite anpassen“.  "
              "Header-Pins durch die Kreuze stechen.", gray)
    if prj.scale_bar:
        draw_rulers(painter, prj, PAGE_MARGIN, y + 3.0, font)
    for pos in positions:
        lay.draw(painter, pos)
    foot = (f"{prj.title.strip() + ' · ' if prj.title.strip() else ''}"
            f"{prj.cols}×{prj.rows} Pins · Raster {fmt(prj.pitch)} mm · Schrift {fmt(prj.font_pt, 1)} pt")
    if prj.scale_x != 100.0 or prj.scale_y != 100.0:
        foot += f" · Korrektur X {fmt(prj.scale_x)} % / Y {fmt(prj.scale_y)} %"
    draw_text(painter, font, 2.0 / REF_PX, PAGE_MARGIN, PAGE_H - PAGE_MARGIN, foot, QColor("#888888"))
    painter.restore()


def begin_mm(painter: QPainter, dpi: float) -> None:
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    painter.scale(dpi / 25.4, dpi / 25.4)


def export_pdf(prj: Project, path: str) -> int:
    lay = Layout(prj)
    pos = page_layout(prj, lay)
    w = QPdfWriter(str(path))
    w.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    w.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
    w.setResolution(1200)
    w.setTitle(prj.title or "Pin-Label")
    w.setCreator("Pin-Label-Generator")
    p = QPainter(w)
    begin_mm(p, w.resolution())
    draw_page(p, prj, lay, pos)
    p.end()
    return len(pos)


def export_png(prj: Project, path: str, dpi: int = 600) -> int:
    lay = Layout(prj)
    pos = page_layout(prj, lay)
    img = QImage(round(PAGE_W / 25.4 * dpi), round(PAGE_H / 25.4 * dpi), QImage.Format.Format_RGB32)
    img.fill(QColor("#ffffff"))
    dpm = round(dpi / 0.0254)
    img.setDotsPerMeterX(dpm)
    img.setDotsPerMeterY(dpm)
    p = QPainter(img)
    begin_mm(p, dpi)
    draw_page(p, prj, lay, pos)
    p.end()
    if not img.save(str(path)):
        raise OSError(f"PNG konnte nicht gespeichert werden: {path}")
    return len(pos)


def export_svg(prj: Project, path: str) -> int:
    from PySide6.QtSvg import QSvgGenerator
    lay = Layout(prj)
    pos = page_layout(prj, lay)
    k = 10.0                                   # SVG user units per mm
    gen = QSvgGenerator()
    gen.setFileName(str(path))
    gen.setResolution(round(25.4 * k))         # -> width/height written in mm
    gen.setSize(QSize(round(PAGE_W * k), round(PAGE_H * k)))
    gen.setViewBox(QRectF(0, 0, PAGE_W * k, PAGE_H * k))
    gen.setTitle(prj.title or "Pin-Label")
    p = QPainter(gen)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.scale(k, k)
    draw_page(p, prj, lay, pos)
    p.end()
    return len(pos)


def make_printer():
    from PySide6.QtPrintSupport import QPrinter
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    printer.setPageOrientation(QPageLayout.Orientation.Portrait)
    printer.setFullPage(True)          # painter origin = paper corner, no driver margins
    return printer


def paint_to_printer(printer, prj: Project) -> None:
    lay = Layout(prj)
    pos = page_layout(prj, lay)
    p = QPainter(printer)
    begin_mm(p, printer.resolution())
    draw_page(p, prj, lay, pos)
    p.end()


# ----------------------------------------------------------------------------
# GUI
# ----------------------------------------------------------------------------
from PySide6.QtWidgets import (  # noqa: E402  (GUI imports kept together)
    QAbstractItemView, QApplication, QCheckBox, QColorDialog, QComboBox, QDialog,
    QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFontComboBox, QFormLayout,
    QGraphicsItem, QGraphicsScene, QGraphicsView, QGroupBox, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox,
    QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QSplitter, QTableWidget,
    QTableWidgetItem, QToolButton, QVBoxLayout, QWidget,
)


def color_icon(h: str, size: int = 14) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(QColor("#666666"))
    p.setBrush(QColor(h) if h else Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(0.5, 0.5, size - 1, size - 1), 3, 3)
    if not h:
        p.drawLine(QPointF(3, size - 3), QPointF(size - 3, 3))
    p.end()
    return QIcon(pm)


def make_combo(items: list[tuple[str, object]]) -> QComboBox:
    cb = QComboBox()
    for text, data in items:
        cb.addItem(text, data)
    return cb


def set_combo(cb: QComboBox, data) -> None:
    i = cb.findData(data)
    cb.setCurrentIndex(max(0, i))


class PreviewItem(QGraphicsItem):
    def __init__(self):
        super().__init__()
        self.prj: Project | None = None
        self.lay: Layout | None = None
        self.page = False
        self.positions: list[QPointF] = []

    def set_content(self, prj: Project, lay: Layout, page: bool) -> None:
        self.prepareGeometryChange()
        self.prj, self.lay, self.page = prj, lay, page
        self.positions = page_layout(prj, lay) if page else []
        self.update()

    def paper_rect(self) -> QRectF:
        if self.page:
            return QRectF(0, 0, PAGE_W, PAGE_H)
        if self.lay is None:
            return QRectF(0, 0, 10, 10)
        return QRectF(0, 0, self.lay.bbox.width(), self.lay.bbox.height())

    def boundingRect(self) -> QRectF:
        return self.paper_rect().adjusted(-1, -1, 2, 2)

    def paint(self, painter, option, widget=None):
        if self.lay is None:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        r = self.paper_rect()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 45))
        painter.drawRect(r.translated(0.5, 0.5))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRect(r)
        if self.page:
            draw_page(painter, self.prj, self.lay, self.positions)
        else:
            self.lay.draw(painter, QPointF(0, 0))


class PreviewView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.item = PreviewItem()
        self.scene().addItem(self.item)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing
                            | QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QColor("#d6d8dd"))
        self.setMinimumWidth(320)

    def show_layout(self, prj: Project, lay: Layout, page: bool, refit: bool) -> None:
        self.item.set_content(prj, lay, page)
        self.scene().setSceneRect(self.item.boundingRect().adjusted(-6, -6, 6, 6))
        if refit:
            self.fit()

    def fit(self) -> None:
        self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def real_size(self) -> None:
        scr = self.screen()
        dpi = scr.physicalDotsPerInch() if scr else 96.0
        self.resetTransform()
        self.scale(dpi / 25.4, dpi / 25.4)

    def wheelEvent(self, e):
        f = 1.2 if e.angleDelta().y() > 0 else 1 / 1.2
        self.scale(f, f)

    def mouseDoubleClickEvent(self, e):
        self.fit()

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, self.fit)


class PinTable(QTableWidget):
    def __init__(self, win: "MainWindow"):
        super().__init__()
        self.win = win

    def keyPressEvent(self, e):
        if e.matches(QKeySequence.StandardKey.Paste):
            self.win.paste_into_table()
            return
        if e.matches(QKeySequence.StandardKey.Copy):
            self.win.copy_from_table()
            return
        if e.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.win.clear_selection()
            return
        super().keyPressEvent(e)


class ListDialog(QDialog):
    """Paste plain pin lists (one line per pin, top to bottom)."""

    def __init__(self, parent: QWidget, prj: Project):
        super().__init__(parent)
        self.setWindowTitle("Pinlisten einfügen")
        self.resize(560, 520)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Eine Zeile pro Pin, von oben nach unten. "
                             "„leer“, „-“ oder eine leere Zeile = nicht belegt.\n"
                             "Aufzählungszeichen (*, -, •) am Zeilenanfang werden entfernt."))
        row = QHBoxLayout()
        self.edits: list[QPlainTextEdit] = []
        names = ["Linke Seite", "Rechte Seite"] if prj.cols == 2 else ["Pins"]
        for c, name in enumerate(names):
            box = QVBoxLayout()
            box.addWidget(QLabel(name))
            ed = QPlainTextEdit()
            ed.setPlainText(self._prefill(prj, c))
            box.addWidget(ed)
            row.addLayout(box)
            self.edits.append(ed)
        lay.addLayout(row)
        self.adjust = QCheckBox("Anzahl Reihen an die längste Liste anpassen")
        self.adjust.setChecked(True)
        lay.addWidget(self.adjust)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    @staticmethod
    def _prefill(prj: Project, c: int) -> str:
        labels = [prj.pins[r][c].label for r in range(prj.rows)]
        while labels and not labels[-1]:
            labels.pop()
        return "\n".join(l if l else "-" for l in labels)

    def lists(self) -> list[list[str]]:
        out = []
        for ed in self.edits:
            lines = ed.toPlainText().replace("\r", "").split("\n")
            while lines and not lines[-1].strip():
                lines.pop()
            out.append([clean_label(l) for l in lines])
        return out


class MainWindow(QMainWindow):
    def __init__(self, prj: Project, path: Path | None = None):
        super().__init__()
        self.prj = prj
        self.prj.ensure()
        self.path = Path(path) if path else None
        self.dirty = False
        self._building = False
        self._page_prev: bool | None = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self.refresh)

        self._build_ui()
        self._load_settings_ui()
        self.rebuild_table()
        self.refresh(refit=True)
        self._update_title()
        self.resize(1450, 860)

    # -- UI construction -----------------------------------------------------
    def _build_ui(self) -> None:
        settings = self._build_settings()
        scroll = QScrollArea()
        scroll.setWidget(settings)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(340)

        self.table = PinTable(self)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked
                                   | QAbstractItemView.EditTrigger.EditKeyPressed
                                   | QAbstractItemView.EditTrigger.AnyKeyPressed)
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.cellClicked.connect(self.on_cell_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.on_table_menu)
        self.table.verticalHeader().setDefaultSectionSize(24)
        table_box = QWidget()
        tv = QVBoxLayout(table_box)
        tv.setContentsMargins(0, 0, 0, 0)
        tv.addWidget(self.table)
        hint = QLabel("Tippen/Doppelklick: Text · Farbzelle anklicken: Farbe · "
                      "Strg+V: Liste einfügen · Entf: leeren · Rechtsklick: mehr")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")
        tv.addWidget(hint)

        prev_box = QWidget()
        pv = QVBoxLayout(prev_box)
        pv.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        self.view_mode = make_combo([("Etikett", "sheet"), ("Ganze Seite (A4)", "page")])
        self.view_mode.currentIndexChanged.connect(lambda _i: self.refresh())
        b_fit = QPushButton("Einpassen")
        b_fit.clicked.connect(lambda: self.preview.fit())
        b_real = QPushButton("1:1")
        b_real.setToolTip("Ungefähr echte Größe auf dem Bildschirm")
        b_real.clicked.connect(lambda: self.preview.real_size())
        bar.addWidget(QLabel("Vorschau:"))
        bar.addWidget(self.view_mode)
        bar.addStretch(1)
        bar.addWidget(b_fit)
        bar.addWidget(b_real)
        pv.addLayout(bar)
        self.preview = PreviewView()
        pv.addWidget(self.preview)

        split = QSplitter()
        split.addWidget(scroll)
        split.addWidget(table_box)
        split.addWidget(prev_box)
        split.setStretchFactor(2, 1)
        split.setSizes([350, 430, 670])
        self.setCentralWidget(split)

        self.status_label = QLabel()
        self.statusBar().addWidget(self.status_label, 1)
        self._build_menus()

    def _build_settings(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)

        # header
        g1 = QGroupBox("Pin-Header")
        f1 = QFormLayout(g1)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("optional, z. B. J1")
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 200)
        self.cols_combo = make_combo([("2-reihig (Doppelreihe)", 2), ("1-reihig", 1)])
        self.side_combo = make_combo([("rechts", "right"), ("links", "left"), ("abwechselnd", "alternate")])
        pitch_row = QHBoxLayout()
        self.pitch_spin = QDoubleSpinBox()
        self.pitch_spin.setRange(0.5, 20.0)
        self.pitch_spin.setDecimals(2)
        self.pitch_spin.setSingleStep(0.01)
        self.pitch_spin.setSuffix(" mm")
        pitch_btn = QToolButton()
        pitch_btn.setText("▾")
        pitch_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        pm = QMenu(pitch_btn)
        for val in (2.54, 2.0, 1.27, 2.5, 3.5, 3.96, 5.0, 5.08):
            pm.addAction(f"{fmt(val)} mm", lambda v_=val: self.pitch_spin.setValue(v_))
        pitch_btn.setMenu(pm)
        pitch_row.addWidget(self.pitch_spin, 1)
        pitch_row.addWidget(pitch_btn)
        f1.addRow("Titel:", self.title_edit)
        f1.addRow("Reihen (Pins pro Spalte):", self.rows_spin)
        f1.addRow("Bauform:", self.cols_combo)
        f1.addRow("Labels (1-reihig):", self.side_combo)
        f1.addRow("Rastermaß:", pitch_row)
        v.addWidget(g1)

        # text
        g2 = QGroupBox("Schrift && Labels")
        f2 = QFormLayout(g2)
        self.font_combo = QFontComboBox()
        self.font_spin = QDoubleSpinBox()
        self.font_spin.setRange(FONT_PT_MIN, FONT_PT_MAX)
        self.font_spin.setSingleStep(0.5)
        self.font_spin.setDecimals(1)
        self.font_spin.setSuffix(" pt")
        self.bold_check = QCheckBox("fett")
        self.gap_spin = QDoubleSpinBox()
        self.gap_spin.setRange(0.3, 30.0)
        self.gap_spin.setSingleStep(0.2)
        self.gap_spin.setDecimals(1)
        self.gap_spin.setSuffix(" mm")
        self.leader_combo = make_combo([("nur wenn nötig", "auto"), ("immer", "always")])
        self.num_combo = make_combo([("keine", "none"), ("Zickzack (1|2, 3|4 …)", "zigzag"),
                                     ("U-Form / DIP", "dip"), ("spaltenweise", "column")])
        f2.addRow("Schriftart:", self.font_combo)
        f2.addRow("Schriftgröße:", self.font_spin)
        f2.addRow("", self.bold_check)
        f2.addRow("Abstand zum Header:", self.gap_spin)
        f2.addRow("Führungslinien:", self.leader_combo)
        f2.addRow("Pinnummern:", self.num_combo)
        v.addWidget(g2)

        # colors / marks
        g3 = QGroupBox("Farben && Markierungen")
        f3 = QFormLayout(g3)
        self.style_combo = make_combo([("farbiger Hintergrund", "fill"), ("farbige Schrift", "text"),
                                       ("farbiger Rahmen", "outline")])
        self.pin1_check = QCheckBox("Pin-1-Markierung (▼ oben links)")
        self.outline_check = QCheckBox("Header-Umriss")
        self.cut_check = QCheckBox("Schnittrahmen")
        b_auto = QPushButton("GND/VCC automatisch färben")
        b_auto.clicked.connect(self.auto_colors)
        b_nocol = QPushButton("Alle Farben entfernen")
        b_nocol.clicked.connect(self.remove_colors)
        f3.addRow("Farbdarstellung:", self.style_combo)
        f3.addRow(self.pin1_check)
        f3.addRow(self.outline_check)
        f3.addRow(self.cut_check)
        f3.addRow(b_auto)
        f3.addRow(b_nocol)
        v.addWidget(g3)

        # page / print
        g4 = QGroupBox("Seite && Druck (A4)")
        f4 = QFormLayout(g4)
        self.copies_spin = QSpinBox()
        self.copies_spin.setRange(1, 60)
        self.sx_spin = QDoubleSpinBox()
        self.sy_spin = QDoubleSpinBox()
        for sp in (self.sx_spin, self.sy_spin):
            sp.setRange(90.0, 110.0)
            sp.setDecimals(2)
            sp.setSingleStep(0.1)
            sp.setSuffix(" %")
        self.bar_check = QCheckBox("Prüf-Lineal auf der Seite")
        f4.addRow("Kopien:", self.copies_spin)
        f4.addRow("Skalierung X:", self.sx_spin)
        f4.addRow("Skalierung Y:", self.sy_spin)
        f4.addRow(self.bar_check)
        info = QLabel("Skalierung nur ändern, wenn das gedruckte 50-mm-Lineal "
                      "nicht genau 50 mm misst (Korrektur = 50 / gemessen × 100 %).")
        info.setWordWrap(True)
        info.setStyleSheet("color: #666;")
        f4.addRow(info)
        v.addWidget(g4)

        b_lists = QPushButton("Pinlisten einfügen…")
        b_lists.clicked.connect(self.paste_lists_dialog)
        v.addWidget(b_lists)
        v.addStretch(1)

        # change signals
        self.title_edit.textChanged.connect(self.on_settings_changed)
        for sp in (self.rows_spin, self.copies_spin):
            sp.valueChanged.connect(self.on_settings_changed)
        for sp in (self.pitch_spin, self.font_spin, self.gap_spin, self.sx_spin, self.sy_spin):
            sp.valueChanged.connect(self.on_settings_changed)
        for cb in (self.cols_combo, self.side_combo, self.leader_combo, self.num_combo, self.style_combo):
            cb.currentIndexChanged.connect(self.on_settings_changed)
        for ch in (self.bold_check, self.pin1_check, self.outline_check, self.cut_check, self.bar_check):
            ch.toggled.connect(self.on_settings_changed)
        self.font_combo.currentFontChanged.connect(self.on_settings_changed)
        return w

    def _build_menus(self) -> None:
        def act(text, slot, shortcut=None):
            a = QAction(text, self)
            if shortcut:
                a.setShortcut(shortcut)
            a.triggered.connect(slot)
            return a

        a_new = act("Neu", self.new_project, QKeySequence.StandardKey.New)
        a_open = act("Öffnen…", self.open_project, QKeySequence.StandardKey.Open)
        a_save = act("Speichern", self.save, QKeySequence.StandardKey.Save)
        a_save_as = act("Speichern unter…", self.save_as, QKeySequence.StandardKey.SaveAs)
        a_pdf = act("PDF exportieren…", self.export_pdf_dialog, "Ctrl+E")
        a_png = act("PNG exportieren…", self.export_png_dialog)
        a_svg = act("SVG exportieren…", self.export_svg_dialog)
        a_prev = act("Druckvorschau…", self.print_preview)
        a_print = act("Drucken…", self.print_dialog, QKeySequence.StandardKey.Print)
        a_quit = act("Beenden", self.close, QKeySequence.StandardKey.Quit)

        m = self.menuBar().addMenu("&Datei")
        for a in (a_new, a_open, a_save, a_save_as, None, a_pdf, a_png, a_svg, None, a_prev, a_print, None, a_quit):
            m.addSeparator() if a is None else m.addAction(a)
        m2 = self.menuBar().addMenu("&Bearbeiten")
        m2.addAction(act("Pinlisten einfügen…", self.paste_lists_dialog))
        m2.addAction(act("GND/VCC automatisch färben", self.auto_colors))
        m2.addAction(act("Alle Farben entfernen", self.remove_colors))
        m2.addAction(act("Alle Labels leeren", self.clear_all))

        tb = self.addToolBar("Werkzeuge")
        tb.setMovable(False)
        for a in (a_new, a_open, a_save, None, a_pdf, a_png, None, a_prev, a_print):
            tb.addSeparator() if a is None else tb.addAction(a)

    # -- settings <-> UI -----------------------------------------------------
    def _load_settings_ui(self) -> None:
        p = self.prj
        self._building = True
        self.title_edit.setText(p.title)
        self.rows_spin.setValue(p.rows)
        set_combo(self.cols_combo, p.cols)
        set_combo(self.side_combo, p.side_mode)
        self.pitch_spin.setValue(p.pitch)
        self.font_combo.setCurrentFont(make_font(p.font_family, False))
        self.font_spin.setValue(p.font_pt)
        self.bold_check.setChecked(p.bold)
        self.gap_spin.setValue(p.gap_mm)
        set_combo(self.leader_combo, p.leaders)
        set_combo(self.num_combo, p.numbering)
        set_combo(self.style_combo, p.color_style)
        self.pin1_check.setChecked(p.pin1_marker)
        self.outline_check.setChecked(p.outline)
        self.cut_check.setChecked(p.cut_frame)
        self.copies_spin.setValue(p.copies)
        self.sx_spin.setValue(p.scale_x)
        self.sy_spin.setValue(p.scale_y)
        self.bar_check.setChecked(p.scale_bar)
        self.side_combo.setEnabled(p.cols == 1)
        self._building = False

    def on_settings_changed(self, *_args) -> None:
        if self._building:
            return
        p = self.prj
        old = (p.rows, p.cols, p.numbering)
        p.title = self.title_edit.text()
        p.rows = self.rows_spin.value()
        p.cols = self.cols_combo.currentData()
        p.side_mode = self.side_combo.currentData()
        p.pitch = self.pitch_spin.value()
        p.font_family = self.font_combo.currentFont().family()
        p.font_pt = self.font_spin.value()
        p.bold = self.bold_check.isChecked()
        p.gap_mm = self.gap_spin.value()
        p.leaders = self.leader_combo.currentData()
        p.numbering = self.num_combo.currentData()
        p.color_style = self.style_combo.currentData()
        p.pin1_marker = self.pin1_check.isChecked()
        p.outline = self.outline_check.isChecked()
        p.cut_frame = self.cut_check.isChecked()
        p.copies = self.copies_spin.value()
        p.scale_x = self.sx_spin.value()
        p.scale_y = self.sy_spin.value()
        p.scale_bar = self.bar_check.isChecked()
        p.ensure()
        self.side_combo.setEnabled(p.cols == 1)
        if (p.rows, p.cols, p.numbering) != old:
            self.rebuild_table()
        self.mark_dirty()

    # -- table ---------------------------------------------------------------
    def colmap(self) -> list[tuple[str, int]]:
        if self.prj.cols == 2:
            return [("label", 0), ("color", 0), ("color", 1), ("label", 1)]
        return [("label", 0), ("color", 0)]

    def rebuild_table(self) -> None:
        self._building = True
        t = self.table
        cm = self.colmap()
        t.clear()
        t.setColumnCount(len(cm))
        t.setRowCount(self.prj.rows)
        if self.prj.cols == 2:
            t.setHorizontalHeaderLabels(["Linke Seite", "Farbe", "Farbe", "Rechte Seite"])
        else:
            t.setHorizontalHeaderLabels(["Label", "Farbe"])
        for r in range(self.prj.rows):
            for ci, (kind, pc) in enumerate(cm):
                pin = self.prj.pins[r][pc]
                if kind == "label":
                    it = QTableWidgetItem(pin.label)
                    if self.prj.cols == 2 and pc == 0:
                        it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    it = QTableWidgetItem()
                    it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    self._style_color_item(it, pin.color)
                t.setItem(r, ci, it)
        heads = []
        for r in range(self.prj.rows):
            if self.prj.numbering == "none":
                heads.append(str(r + 1))
            elif self.prj.cols == 2:
                heads.append(f"{pin_number(self.prj, r, 0)} | {pin_number(self.prj, r, 1)}")
            else:
                heads.append(str(pin_number(self.prj, r, 0)))
        t.setVerticalHeaderLabels(heads)
        for ci, (kind, _pc) in enumerate(cm):
            t.setColumnWidth(ci, 150 if kind == "label" else 72)
        self._building = False

    @staticmethod
    def _style_color_item(it: QTableWidgetItem, h: str) -> None:
        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if h:
            c = QColor(h)
            it.setBackground(c)
            it.setForeground(text_on(c))
            it.setText(color_name(h))
        else:
            it.setData(Qt.ItemDataRole.BackgroundRole, None)
            it.setData(Qt.ItemDataRole.ForegroundRole, None)
            it.setText("–")

    def refresh_color_items(self) -> None:
        self._building = True
        for r in range(self.prj.rows):
            for ci, (kind, pc) in enumerate(self.colmap()):
                if kind == "color":
                    self._style_color_item(self.table.item(r, ci), self.prj.pins[r][pc].color)
        self._building = False

    def on_item_changed(self, it: QTableWidgetItem) -> None:
        if self._building:
            return
        kind, pc = self.colmap()[it.column()]
        if kind != "label":
            return
        self.prj.pins[it.row()][pc].label = it.text().strip()
        self.mark_dirty()

    def selected_pins(self) -> list[tuple[int, int]]:
        cm = self.colmap()
        return sorted({(i.row(), cm[i.column()][1]) for i in self.table.selectedIndexes()})

    def _fill_color_menu(self, menu: QMenu, cb) -> None:
        a = menu.addAction(color_icon(""), "Keine Farbe")
        a.triggered.connect(lambda: cb(""))
        menu.addSeparator()
        for name, h in PALETTE:
            a = menu.addAction(color_icon(h), name)
            a.triggered.connect(lambda _=False, h_=h: cb(h_))
        menu.addSeparator()
        a = menu.addAction("Andere Farbe…")
        a.triggered.connect(lambda: self._custom_color(cb))

    def _custom_color(self, cb) -> None:
        c = QColorDialog.getColor(QColor("#1565c0"), self, "Farbe wählen")
        if c.isValid():
            cb(c.name())

    def on_cell_clicked(self, r: int, c: int) -> None:
        kind, pc = self.colmap()[c]
        if kind != "color":
            return
        pins = self.selected_pins()
        if (r, pc) not in pins:
            pins = [(r, pc)]
        menu = QMenu(self)
        self._fill_color_menu(menu, lambda h: self.apply_color(pins, h))
        rect = self.table.visualItemRect(self.table.item(r, c))
        menu.exec(self.table.viewport().mapToGlobal(rect.bottomLeft()))

    def on_table_menu(self, pos) -> None:
        pins = self.selected_pins()
        row = self.table.rowAt(pos.y())
        menu = QMenu(self)
        if pins:
            cm = menu.addMenu("Farbe für Auswahl")
            self._fill_color_menu(cm, lambda h: self.apply_color(pins, h))
            menu.addAction("Auswahl leeren", self.clear_selection)
            menu.addSeparator()
        if row >= 0:
            menu.addAction("Reihe darüber einfügen", lambda: self.insert_row(row))
            menu.addAction("Reihe darunter einfügen", lambda: self.insert_row(row + 1))
            menu.addAction("Reihe löschen", lambda: self.delete_row(row))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def apply_color(self, pins: list[tuple[int, int]], h: str) -> None:
        for r, pc in pins:
            self.prj.pins[r][pc].color = h
        self.refresh_color_items()
        self.mark_dirty()

    def clear_selection(self) -> None:
        cm = self.colmap()
        for i in self.table.selectedIndexes():
            kind, pc = cm[i.column()]
            pin = self.prj.pins[i.row()][pc]
            if kind == "label":
                pin.label = ""
            else:
                pin.color = ""
        self.rebuild_table()
        self.mark_dirty()

    def set_rows(self, n: int) -> None:
        self.prj.rows = max(1, min(200, n))
        self.prj.ensure()
        self._building = True
        self.rows_spin.setValue(self.prj.rows)
        self._building = False
        self.rebuild_table()

    def insert_row(self, r: int) -> None:
        self.prj.trim()
        self.prj.pins.insert(r, [Pin(), Pin()])
        self.set_rows(self.prj.rows + 1)
        self.mark_dirty()

    def delete_row(self, r: int) -> None:
        if self.prj.rows <= 1:
            return
        self.prj.trim()
        self.prj.pins.pop(r)
        self.set_rows(self.prj.rows - 1)
        self.mark_dirty()

    def paste_into_table(self) -> None:
        text = QGuiApplication.clipboard().text()
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        while lines and not lines[-1].strip():
            lines.pop()
        if not lines:
            return
        cm = self.colmap()
        label_cols = [ci for ci, (k, _pc) in enumerate(cm) if k == "label"]
        cur = self.table.currentIndex()
        r0 = max(cur.row(), 0)
        pc0 = cm[max(cur.column(), 0)][1]
        start = next(i for i, ci in enumerate(label_cols) if cm[ci][1] == pc0)
        self.prj.trim()
        if r0 + len(lines) > self.prj.rows:
            self.prj.rows = r0 + len(lines)
            self.prj.ensure()
        for i, line in enumerate(lines):
            for j, part in enumerate(line.split("\t")):
                li = start + j
                if li >= len(label_cols):
                    break
                self.prj.pins[r0 + i][cm[label_cols[li]][1]].label = clean_label(part)
        self.set_rows(self.prj.rows)
        self.mark_dirty()

    def copy_from_table(self) -> None:
        cm = self.colmap()
        idx = [i for i in self.table.selectedIndexes() if cm[i.column()][0] == "label"]
        if not idx:
            return
        rows = sorted({i.row() for i in idx})
        cols = sorted({i.column() for i in idx})
        lines = ["\t".join(self.table.item(r, c).text() for c in cols) for r in rows]
        QGuiApplication.clipboard().setText("\n".join(lines))

    # -- bulk actions --------------------------------------------------------
    def paste_lists_dialog(self) -> None:
        dlg = ListDialog(self, self.prj)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        lists = dlg.lists()
        self.prj.trim()
        n = max((len(l) for l in lists), default=0)
        if dlg.adjust.isChecked() and n > 0:
            self.prj.rows = n
        self.prj.ensure()
        for c, items in enumerate(lists):
            for r in range(self.prj.rows):
                self.prj.pins[r][c].label = items[r] if r < len(items) else ""
        self.set_rows(self.prj.rows)
        self.mark_dirty()

    def auto_colors(self) -> None:
        for row in self.prj.pins[: self.prj.rows]:
            for pin in row[: self.prj.cols]:
                t = pin.label.strip()
                if RE_GND.match(t):
                    pin.color = "#1b1b1b"
                elif RE_PWR.match(t):
                    pin.color = "#d32f2f"
        self.refresh_color_items()
        self.mark_dirty()

    def remove_colors(self) -> None:
        for row in self.prj.pins:
            for pin in row:
                pin.color = ""
        self.refresh_color_items()
        self.mark_dirty()

    def clear_all(self) -> None:
        if QMessageBox.question(self, "Alle Labels leeren", "Alle Labels und Farben löschen?") \
                != QMessageBox.StandardButton.Yes:
            return
        for row in self.prj.pins:
            for pin in row:
                pin.label, pin.color = "", ""
        self.rebuild_table()
        self.mark_dirty()

    # -- refresh -------------------------------------------------------------
    def mark_dirty(self) -> None:
        if not self.dirty:
            self.dirty = True
            self._update_title()
        self._timer.start()

    def _update_title(self) -> None:
        name = self.path.name if self.path else "Unbenannt"
        self.setWindowTitle(f"Pin-Label-Generator – {name}{' *' if self.dirty else ''}")

    def refresh(self, refit: bool = False) -> None:
        lay = Layout(self.prj)
        page = self.view_mode.currentData() == "page"
        refit = refit or page != self._page_prev
        self._page_prev = page
        self.preview.show_layout(self.prj, lay, page, refit)
        fits = len(page_layout(self.prj, lay))
        msg = f"{len(lay.labels)} Labels"
        if lay.shifted_count:
            msg += f" · {lay.shifted_count} versetzt (Führungslinien)"
        msg += f" · Etikett {fmt(lay.bbox.width(), 1)} × {fmt(lay.bbox.height(), 1)} mm"
        if fits < self.prj.copies:
            msg += f" · Achtung: nur {fits} von {self.prj.copies} Kopien passen auf A4"
        self.status_label.setText(msg)

    # -- files ---------------------------------------------------------------
    def _maybe_save(self) -> bool:
        if not self.dirty:
            return True
        r = QMessageBox.question(
            self, "Ungespeicherte Änderungen", "Änderungen speichern?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Save:
            return self.save()
        return r == QMessageBox.StandardButton.Discard

    def _set_project(self, prj: Project, path: Path | None) -> None:
        self.prj = prj
        self.prj.ensure()
        self.path = path
        self._load_settings_ui()
        self.rebuild_table()
        self.dirty = False
        self._update_title()
        self.refresh(refit=True)

    def new_project(self) -> None:
        if self._maybe_save():
            self._set_project(Project(), None)

    def open_project(self) -> None:
        if not self._maybe_save():
            return
        fn, _ = QFileDialog.getOpenFileName(self, "Projekt öffnen", self._dir(), "Pin-Label-Projekt (*.json)")
        if not fn:
            return
        try:
            self._set_project(Project.load(Path(fn)), Path(fn))
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Fehler", f"Datei konnte nicht geladen werden:\n{e}")

    def save(self) -> bool:
        if not self.path:
            return self.save_as()
        try:
            self.prj.save(self.path)
        except OSError as e:
            QMessageBox.critical(self, "Fehler", f"Speichern fehlgeschlagen:\n{e}")
            return False
        self.dirty = False
        self._update_title()
        self.statusBar().showMessage(f"Gespeichert: {self.path}", 4000)
        return True

    def save_as(self) -> bool:
        fn, _ = QFileDialog.getSaveFileName(self, "Projekt speichern", str(Path(self._dir()) / f"{self._stem()}.json"),
                                            "Pin-Label-Projekt (*.json)")
        if not fn:
            return False
        self.path = Path(fn)
        return self.save()

    def _dir(self) -> str:
        return str(self.path.parent) if self.path else str(Path.home())

    def _stem(self) -> str:
        if self.path:
            return self.path.stem
        t = re.sub(r"[^\w\-]+", "_", self.prj.title.strip())
        return t or "pinlabel"

    def _export(self, title: str, ext: str, filt: str, func) -> None:
        fn, _ = QFileDialog.getSaveFileName(self, title, str(Path(self._dir()) / f"{self._stem()}.{ext}"), filt)
        if not fn:
            return
        try:
            n = func(fn)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Fehler", f"Export fehlgeschlagen:\n{e}")
            return
        msg = f"Exportiert: {fn}"
        if n < self.prj.copies:
            msg += f" (nur {n} von {self.prj.copies} Kopien passen auf A4)"
        self.statusBar().showMessage(msg, 6000)

    def export_pdf_dialog(self) -> None:
        self._export("PDF exportieren", "pdf", "PDF (*.pdf)", lambda fn: export_pdf(self.prj, fn))

    def export_png_dialog(self) -> None:
        item, ok = QInputDialog.getItem(self, "PNG exportieren", "Auflösung:", ["300 dpi", "600 dpi"], 1, False)
        if ok:
            dpi = int(item.split()[0])
            self._export("PNG exportieren", "png", "PNG (*.png)", lambda fn: export_png(self.prj, fn, dpi))

    def export_svg_dialog(self) -> None:
        self._export("SVG exportieren", "svg", "SVG (*.svg)", lambda fn: export_svg(self.prj, fn))

    def print_dialog(self) -> None:
        from PySide6.QtPrintSupport import QPrintDialog
        printer = make_printer()
        dlg = QPrintDialog(printer, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            paint_to_printer(printer, self.prj)

    def print_preview(self) -> None:
        from PySide6.QtPrintSupport import QPrintPreviewDialog
        printer = make_printer()
        dlg = QPrintPreviewDialog(printer, self)
        dlg.paintRequested.connect(lambda pr: paint_to_printer(pr, self.prj))
        dlg.resize(900, 1000)
        dlg.exec()

    def closeEvent(self, e):
        if self._maybe_save():
            e.accept()
        else:
            e.ignore()


# ----------------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Pin-Header-Label-Generator")
    ap.add_argument("project", nargs="?", help="Projektdatei (.json)")
    ap.add_argument("--pdf", help="PDF exportieren und beenden")
    ap.add_argument("--png", help="PNG exportieren und beenden")
    ap.add_argument("--svg", help="SVG exportieren und beenden")
    ap.add_argument("--dpi", type=int, default=600, help="Auflösung für PNG (Standard 600)")
    args = ap.parse_args(argv)

    if args.pdf or args.png or args.svg:
        app = QGuiApplication(sys.argv[:1])  # noqa: F841  (needed for fonts)
        if not args.project:
            ap.error("Für den Export wird eine Projektdatei benötigt.")
        prj = Project.load(Path(args.project))
        for out, func in ((args.pdf, export_pdf), (args.svg, export_svg)):
            if out:
                n = func(prj, out)
                print(f"{out}: {n} Kopie(n)")
        if args.png:
            n = export_png(prj, args.png, args.dpi)
            print(f"{args.png}: {n} Kopie(n), {args.dpi} dpi")
        return 0

    app = QApplication(sys.argv[:1])
    app.setApplicationName("Pin-Label-Generator")
    path = Path(args.project) if args.project else None
    prj = Project.load(path) if path and path.exists() else Project()
    prj.ensure()
    win = MainWindow(prj, path)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
