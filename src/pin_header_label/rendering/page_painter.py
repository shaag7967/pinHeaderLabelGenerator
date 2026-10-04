"""Draws a complete A4 page: instructions, check rulers, label copies and footer."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QFontMetricsF, QPainter, QPen

from ..i18n import Translator, get_translator
from ..layout import PAGE_HEIGHT_MM, PAGE_MARGIN_MM, LabelLayout, PageLayout
from ..layout.label_layout import REFERENCE_PX
from .label_painter import LabelPainter
from .primitives import draw_text, qpoint
from .qt_metrics import make_font

TEXT_COLOR = QColor("#111111")
HINT_COLOR = QColor("#555555")
FOOTER_COLOR = QColor("#888888")

RULER_LENGTH_MM = 50.0
PITCH_RULER_OFFSET_MM = 64.0
PITCH_RULER_MAX_MM = 70.0


class PagePainter:
    """Paints a page with all label copies that fit; one painter unit = 1 mm."""

    def __init__(self, layout: LabelLayout, translator: Translator | None = None) -> None:
        self.layout = layout
        self.project = layout.project
        self.page = PageLayout.for_sheet(layout.bbox, self.project.copies, self.project.scale_bar)
        self.translator = translator or get_translator()
        self.font = make_font("", False)
        self.label_painter = LabelPainter(layout)

    def paint(self, painter: QPainter) -> None:
        project, t = self.project, self.translator
        painter.save()
        painter.scale(project.scale_x / 100.0, project.scale_y / 100.0)
        y = PAGE_MARGIN_MM + 2.4
        instructions = t.tr(
            "Print at 100 % or “Actual size” – not “Fit to page”.  Push the header pins through the crosses."
        )
        draw_text(painter, self.font, 2.4 / REFERENCE_PX, PAGE_MARGIN_MM, y, instructions, HINT_COLOR)
        if project.scale_bar:
            self._paint_rulers(painter, PAGE_MARGIN_MM, y + 3.0)
        for position in self.page.positions:
            self.label_painter.paint(painter, qpoint(position))
        draw_text(
            painter,
            self.font,
            2.0 / REFERENCE_PX,
            PAGE_MARGIN_MM,
            PAGE_HEIGHT_MM - PAGE_MARGIN_MM,
            self.footer_text(),
            FOOTER_COLOR,
        )
        painter.restore()

    def footer_text(self) -> str:
        project, t = self.project, self.translator
        text = t.tr(
            "{cols}×{rows} pins · pitch {pitch} mm · font {size} pt",
            cols=project.cols,
            rows=project.rows,
            pitch=t.format_number(project.pitch),
            size=t.format_number(project.font_pt, 1, trim_zeros=False),
        )
        title = project.title.strip()
        if title:
            text = f"{title} · {text}"
        if project.scale_x != 100.0 or project.scale_y != 100.0:
            text += t.tr(
                " · correction X {x} % / Y {y} %",
                x=t.format_number(project.scale_x),
                y=t.format_number(project.scale_y),
            )
        return text

    def _paint_rulers(self, painter: QPainter, x: float, y: float) -> None:
        """A 50 mm check bar and a pitch ruler (lay the real header on it)."""
        t = self.translator
        scale = 2.0 / REFERENCE_PX
        metrics = QFontMetricsF(self.font)
        painter.save()
        bar_height = 1.4
        segments = 5
        segment = RULER_LENGTH_MM / segments
        for i in range(segments):
            painter.setPen(QPen(TEXT_COLOR, 0.1))
            painter.setBrush(TEXT_COLOR if i % 2 == 0 else QColor("#ffffff"))
            painter.drawRect(QRectF(x + segment * i, y, segment, bar_height))
        for i in range(segments + 1):
            mark = str(round(segment * i))
            mark_x = x + segment * i - metrics.horizontalAdvance(mark) * scale / 2
            draw_text(painter, self.font, scale, mark_x, y + bar_height + 2.3, mark, TEXT_COLOR)
        draw_text(painter, self.font, scale, x + RULER_LENGTH_MM + 2.0, y + bar_height, "mm", TEXT_COLOR)

        pitch = self.project.pitch
        count = max(2, min(self.project.rows, 20, int(PITCH_RULER_MAX_MM / pitch)))
        x2 = x + PITCH_RULER_OFFSET_MM
        base = y + bar_height
        painter.setPen(QPen(TEXT_COLOR, 0.12))
        painter.drawLine(QPointF(x2, base), QPointF(x2 + count * pitch, base))
        for k in range(count + 1):
            tick = 1.4 if (k % 5 == 0 or k == count) else 0.8
            painter.drawLine(QPointF(x2 + k * pitch, base), QPointF(x2 + k * pitch, base - tick))
        text = t.tr(
            "{n} × {pitch} mm = {length} mm (pitch)",
            n=count,
            pitch=t.format_number(pitch),
            length=t.format_number(count * pitch),
        )
        draw_text(painter, self.font, scale, x2 + count * pitch + 2.0, base, text, TEXT_COLOR)
        painter.restore()
