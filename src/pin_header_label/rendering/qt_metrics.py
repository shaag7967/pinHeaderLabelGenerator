"""Fonts and Qt implementation of :class:`~pin_header_label.layout.TextMetrics`."""

from __future__ import annotations

from PySide6.QtGui import QFont, QFontDatabase, QFontMetricsF

from ..layout import LabelLayout
from ..layout.label_layout import REFERENCE_PX
from ..model import Project


def make_font(family: str, bold: bool) -> QFont:
    """Font at the reference pixel size; ``family=''`` selects the system font."""
    font = QFont(family) if family else QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
    font.setPixelSize(int(REFERENCE_PX))
    font.setBold(bold)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    font.setKerning(True)
    return font


class QtTextMetrics:
    """Text measurement with :class:`QFontMetricsF` (requires a QGuiApplication)."""

    def __init__(self, font: QFont) -> None:
        self.font = font
        self._metrics = QFontMetricsF(font)

    @classmethod
    def for_font(cls, family: str, bold: bool) -> QtTextMetrics:
        return cls(make_font(family, bold))

    def advance(self, text: str) -> float:
        return self._metrics.horizontalAdvance(text)

    def vertical_bounds(self, text: str) -> tuple[float, float]:
        rect = self._metrics.tightBoundingRect(text)
        return rect.top(), rect.bottom()


def create_layout(project: Project) -> LabelLayout:
    """Layout of ``project`` measured with the real fonts."""
    return LabelLayout(project, QtTextMetrics.for_font)
