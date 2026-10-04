"""Qt-independent label and page geometry (all units in millimeters)."""

from .geometry import Point, Rect
from .label_layout import LabelGeometry, LabelLayout, MetricsFactory, TextMetrics
from .page_layout import PAGE_HEIGHT_MM, PAGE_MARGIN_MM, PAGE_WIDTH_MM, PageLayout

__all__ = [
    "PAGE_HEIGHT_MM",
    "PAGE_MARGIN_MM",
    "PAGE_WIDTH_MM",
    "LabelGeometry",
    "LabelLayout",
    "MetricsFactory",
    "PageLayout",
    "Point",
    "Rect",
    "TextMetrics",
]
