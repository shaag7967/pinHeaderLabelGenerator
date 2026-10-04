"""Small drawing helpers (all coordinates in millimeters)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen

from ..core.colors import relative_luminance
from ..layout import Point, Rect


def qpoint(p: Point) -> QPointF:
    return QPointF(p.x, p.y)


def qrect(r: Rect) -> QRectF:
    return QRectF(r.x, r.y, r.width, r.height)


def draw_text(
    painter: QPainter, font: QFont, scale: float, x: float, baseline: float, text: str, color: QColor
) -> None:
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
    pen.setDashPattern([dash / width, space / width])  # pattern is in units of pen width
    return pen


def luminance(color: QColor) -> float:
    return relative_luminance(color.name())


def ink(color: QColor) -> QColor:
    """Color usable for thin lines / text on white paper (darkens light colors)."""
    return color.darker(170) if luminance(color) > 0.55 else color


def begin_mm(painter: QPainter, dpi: float) -> None:
    """Set up ``painter`` so that one unit equals one millimeter."""
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    painter.scale(dpi / 25.4, dpi / 25.4)
