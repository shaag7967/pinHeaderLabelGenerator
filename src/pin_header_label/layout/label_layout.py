"""Geometry of one label sheet.

The layout is computed in millimeters with the origin at the top-left corner of
the header outline. Text measurement is delegated to a :class:`TextMetrics`
implementation, so the algorithm itself does not depend on Qt.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from ..model import ColorStyle, LeaderMode, Project, SideMode
from .geometry import Point, Rect
from .placement import place_labels

MM_PER_PT = 25.4 / 72.0
REFERENCE_PX = 100.0  # font size the metrics are measured at; text is scaled from this
VERTICAL_PROBE = "Hbdfhklgjpqy_0123456789"  # probe string for the vertical text extent

LEFT, RIGHT = -1, 1


class TextMetrics(Protocol):
    """Measures text set in a font of :data:`REFERENCE_PX` pixels."""

    def advance(self, text: str) -> float:
        """Horizontal advance of ``text``."""
        ...

    def vertical_bounds(self, text: str) -> tuple[float, float]:
        """Tight (top, bottom) ink extent relative to the baseline (top is negative)."""
        ...


# (font family, bold) -> metrics
MetricsFactory = Callable[[str, bool], TextMetrics]


@dataclass
class LabelGeometry:
    """Placement of a single label."""

    row: int
    col: int
    side: int  # LEFT or RIGHT
    text: str
    number: str
    color: str
    pin: Point  # pin center
    center_y: float = 0.0  # vertical label center
    shifted: bool = False  # moved away from its pin
    box: Rect = field(default_factory=Rect)
    text_x: float = 0.0
    number_x: float = 0.0
    baseline: float = 0.0
    leader: list[Point] = field(default_factory=list)


class LabelLayout:
    """Computes the geometry of all labels, marks and the title of a project."""

    CUT_MARGIN = 2.0
    STUB = 0.6  # straight leader part outside the header outline
    MARKER_RADIUS = 0.45  # radius of the pierce marker
    BOX_GAP = 0.08  # min. vertical gap between stacked label boxes
    NUMBER_SCALE = 0.75  # pin number size relative to the label text
    TITLE_SCALE = 1.2

    def __init__(self, project: Project, metrics_factory: MetricsFactory) -> None:
        project.ensure_pins()
        self.project = project
        self.width = project.cols * project.pitch
        self.height = project.rows * project.pitch

        self.metrics = metrics_factory(project.font_family, project.bold)
        self.title_metrics = metrics_factory(project.font_family, True)
        self.em = project.font_pt * MM_PER_PT
        self.text_scale = self.em / REFERENCE_PX
        self.number_scale = self.text_scale * self.NUMBER_SCALE
        self.title_scale = self.text_scale * self.TITLE_SCALE

        top, bottom = self.metrics.vertical_bounds(VERTICAL_PROBE)
        self.text_top = top * self.text_scale
        self.text_bottom = bottom * self.text_scale
        boxed = project.color_style in (ColorStyle.FILL, ColorStyle.OUTLINE)
        outline = project.color_style == ColorStyle.OUTLINE
        self.pad_v = (0.18 if outline else 0.12) if boxed else 0.0
        self.pad_h = (0.45 if outline else 0.40) if boxed else 0.0
        self.box_height = (self.text_bottom - self.text_top) + 2 * self.pad_v
        self.min_distance = self.box_height + self.BOX_GAP

        self.labels: list[LabelGeometry] = []
        self.shifted_count = 0
        self.fanned_sides: list[int] = []
        self.title = project.title.strip()
        self.title_origin = Point()
        self.pin1_marker: list[Point] | None = None
        self.bbox = Rect()
        self._build()

    # -- geometry helpers ---------------------------------------------------
    def pin_center(self, row: int, col: int) -> Point:
        pitch = self.project.pitch
        return Point((col + 0.5) * pitch, (row + 0.5) * pitch)

    def side_of(self, row: int, col: int) -> int:
        project = self.project
        if project.cols == 2:
            return LEFT if col == 0 else RIGHT
        if project.side_mode == SideMode.LEFT:
            return LEFT
        if project.side_mode == SideMode.ALTERNATE:
            return LEFT if row % 2 == 0 else RIGHT
        return RIGHT

    @property
    def header_rect(self) -> Rect:
        return Rect(0.0, 0.0, self.width, self.height)

    # -- layout -------------------------------------------------------------
    def _build(self) -> None:
        groups: dict[int, list[LabelGeometry]] = {LEFT: [], RIGHT: []}
        for row, col, pin in self.project.iter_pins():
            text = pin.label.strip()
            if not text:
                continue
            number = self.project.pin_number(row, col)
            side = self.side_of(row, col)
            groups[side].append(
                LabelGeometry(
                    row=row,
                    col=col,
                    side=side,
                    text=text,
                    number=str(number) if number else "",
                    color=pin.color,
                    pin=self.pin_center(row, col),
                )
            )
        for side, items in groups.items():
            if items:
                self._layout_side(side, items)

        rect = self.header_rect
        for label in self.labels:
            rect = rect.united(label.box)
        if self.project.pin1_marker:
            x = self.pin_center(0, 0).x
            self.pin1_marker = [Point(x, -0.3), Point(x - 0.6, -1.3), Point(x + 0.6, -1.3)]
            rect = rect.united(Rect.bounding(self.pin1_marker))
        if self.title:
            rect = rect.united(self._layout_title(rect))
        m = self.CUT_MARGIN
        self.bbox = rect.adjusted(-m, -m, m, m)

    def _layout_side(self, side: int, items: list[LabelGeometry]) -> None:
        project = self.project
        items.sort(key=lambda g: g.pin.y)
        ys = place_labels([g.pin.y for g in items], self.min_distance)
        displacement = max(abs(y - g.pin.y) for g, y in zip(items, ys, strict=True))
        fanned = displacement > 1e-3
        fan = min(14.0, max(2.0, 1.1 * displacement)) if fanned else 0.0
        if fanned:
            self.fanned_sides.append(side)
            gap = max(project.gap_mm, self.STUB + fan + 0.8)
        else:
            gap = max(project.gap_mm, self.STUB + 0.4)
        edge = 0.0 if side == LEFT else self.width
        x_inner = edge + side * gap  # inner edge of the label boxes
        draw_leader = project.leaders == LeaderMode.ALWAYS or fanned
        # a common number column per side keeps the texts aligned (1 vs. 2 digits)
        number_col = max(
            (self.metrics.advance(g.number) * self.number_scale for g in items if g.number), default=0.0
        )
        number_gap = 0.35 * self.em if number_col else 0.0

        for g, y in zip(items, ys, strict=True):
            g.center_y = y
            g.shifted = abs(y - g.pin.y) > 1e-3
            self.shifted_count += int(g.shifted)
            text_w = self.metrics.advance(g.text) * self.text_scale
            number_w = self.metrics.advance(g.number) * self.number_scale if g.number else 0.0
            box_w = text_w + number_col + number_gap + 2 * self.pad_h
            g.baseline = y - (self.text_top + self.text_bottom) / 2.0
            top = y - self.box_height / 2.0
            if side == LEFT:  # text right-aligned, number column next to the header
                g.box = Rect(x_inner - box_w, top, box_w, self.box_height)
                g.number_x = x_inner - self.pad_h - number_col
                g.text_x = g.number_x - number_gap - text_w
            else:  # number right-aligned in its column, text left-aligned
                g.box = Rect(x_inner, top, box_w, self.box_height)
                g.number_x = x_inner + self.pad_h + number_col - number_w
                g.text_x = x_inner + self.pad_h + number_col + number_gap
            if draw_leader:
                g.leader = self._leader(g, side, edge, x_inner, fan)
            self.labels.append(g)

    def _leader(self, g: LabelGeometry, side: int, edge: float, x_inner: float, fan: float) -> list[Point]:
        end_x = x_inner - side * (0.3 if self.pad_h == 0 else 0.0)
        start = Point(g.pin.x + side * self.MARKER_RADIUS, g.pin.y)
        if not g.shifted:
            return [start, Point(end_x, g.pin.y)]
        return [
            start,
            Point(edge + side * self.STUB, g.pin.y),
            Point(edge + side * (self.STUB + fan), g.center_y),
            Point(end_x, g.center_y),
        ]

    def _layout_title(self, content: Rect) -> Rect:
        top, bottom = self.title_metrics.vertical_bounds(VERTICAL_PROBE)
        s = self.title_scale
        width = self.title_metrics.advance(self.title) * s
        baseline = min(content.top, 0.0) - 1.0 - bottom * s
        self.title_origin = Point(self.width / 2.0 - width / 2.0, baseline)
        return Rect(self.title_origin.x, baseline + top * s, width, (bottom - top) * s)
