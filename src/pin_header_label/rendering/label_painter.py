"""Draws one label sheet from a :class:`~pin_header_label.layout.LabelLayout`."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF

from ..core.colors import DARK_TEXT, contrast_text_color
from ..layout import LabelGeometry, LabelLayout
from ..model import ColorStyle
from .primitives import dashed_pen, draw_text, ink, luminance, qpoint, qrect
from .qt_metrics import make_font

CUT_FRAME_COLOR = QColor("#9a9a9a")
OUTLINE_COLOR = QColor("#8a8a8a")
UNUSED_PIN_COLOR = QColor("#b0b0b0")
PLAIN_PIN_COLOR = QColor("#333333")
PLAIN_LEADER_COLOR = QColor("#555555")
MARK_COLOR = QColor("#222222")


class LabelPainter:
    """Paints a label sheet with QPainter; one painter unit = 1 mm."""

    def __init__(self, layout: LabelLayout) -> None:
        self.layout = layout
        project = layout.project
        self.font = make_font(project.font_family, project.bold)
        self.title_font = make_font(project.font_family, True)

    def paint(self, painter: QPainter, origin: QPointF) -> None:
        """Draw the sheet so that the top-left corner of its bounding box lands on ``origin``."""
        layout, project = self.layout, self.layout.project
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.translate(origin.x() - layout.bbox.left, origin.y() - layout.bbox.top)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if project.cut_frame:
            painter.setPen(dashed_pen(CUT_FRAME_COLOR, 0.12, 1.2, 0.8))
            painter.drawRect(qrect(layout.bbox))
        if project.outline:
            painter.setPen(dashed_pen(OUTLINE_COLOR, 0.12, 0.6, 0.4))
            painter.drawRect(qrect(layout.header_rect))

        for label in layout.labels:
            self._paint_leader(painter, label)

        by_pin = {(g.row, g.col): g for g in layout.labels}
        for row, col, _pin in project.iter_pins():
            center = layout.pin_center(row, col)
            self._paint_marker(painter, center.x, center.y, by_pin.get((row, col)))

        for label in layout.labels:
            self._paint_label(painter, label)

        if layout.pin1_marker is not None:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(MARK_COLOR)
            painter.drawPolygon(QPolygonF([qpoint(p) for p in layout.pin1_marker]))
        if layout.title:
            draw_text(
                painter,
                self.title_font,
                layout.title_scale,
                layout.title_origin.x,
                layout.title_origin.y,
                layout.title,
                QColor(DARK_TEXT),
            )
        painter.restore()

    @staticmethod
    def _paint_leader(painter: QPainter, label: LabelGeometry) -> None:
        if not label.leader:
            return
        color = ink(QColor(label.color)) if label.color else PLAIN_LEADER_COLOR
        pen = QPen(color, 0.16)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPolyline(QPolygonF([qpoint(p) for p in label.leader]))

    def _paint_marker(self, painter: QPainter, cx: float, cy: float, label: LabelGeometry | None) -> None:
        """Circle with a cross where the pin pierces the paper."""
        r = self.layout.MARKER_RADIUS
        if label is None:
            painter.setPen(QPen(UNUSED_PIN_COLOR, 0.1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            cross = UNUSED_PIN_COLOR
        elif label.color:
            color = QColor(label.color)
            painter.setPen(QPen(QColor("#444444") if luminance(color) > 0.5 else color.darker(140), 0.1))
            painter.setBrush(color)
            cross = QColor(contrast_text_color(label.color))
        else:
            painter.setPen(QPen(PLAIN_PIN_COLOR, 0.12))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            cross = PLAIN_PIN_COLOR
        painter.drawEllipse(QPointF(cx, cy), r, r)
        painter.setPen(QPen(cross, 0.06))
        k = r * 0.65
        painter.drawLine(QPointF(cx - k, cy), QPointF(cx + k, cy))
        painter.drawLine(QPointF(cx, cy - k), QPointF(cx, cy + k))

    def _paint_label(self, painter: QPainter, label: LabelGeometry) -> None:
        style = self.layout.project.color_style
        foreground = QColor(DARK_TEXT)
        if label.color:
            color = QColor(label.color)
            box = qrect(label.box)
            if style == ColorStyle.FILL:
                painter.setBrush(color)
                if luminance(color) > 0.8:  # keep very light boxes visible
                    painter.setPen(QPen(QColor("#888888"), 0.08))
                else:
                    painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(box, 0.35, 0.35)
                foreground = QColor(contrast_text_color(label.color))
            elif style == ColorStyle.OUTLINE:
                pen_width = 0.2
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(ink(color), pen_width))
                inset = pen_width / 2
                painter.drawRoundedRect(QRectF(box).adjusted(inset, inset, -inset, -inset), 0.3, 0.3)
            else:
                foreground = ink(color)
        layout = self.layout
        draw_text(painter, self.font, layout.text_scale, label.text_x, label.baseline, label.text, foreground)
        if label.number:
            number_color = QColor(foreground)
            number_color.setAlphaF(0.6)
            draw_text(
                painter,
                self.font,
                layout.number_scale,
                label.number_x,
                label.baseline,
                label.number,
                number_color,
            )
