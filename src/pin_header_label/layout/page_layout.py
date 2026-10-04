"""Arrangement of label copies on an A4 page."""

from __future__ import annotations

from .geometry import Point, Rect

PAGE_WIDTH_MM, PAGE_HEIGHT_MM = 210.0, 297.0  # A4 portrait
PAGE_MARGIN_MM = 12.0
HEADER_SPACE_MM = 5.0  # print instructions at the top / footer at the bottom
RULER_SPACE_MM = 10.0
COPY_SPACING_MM = 2.0


class PageLayout:
    """Places as many label copies on the page as requested and fit, row by row."""

    def __init__(self, sheet_width: float, sheet_height: float, copies: int, scale_bar: bool) -> None:
        self.sheet_width = sheet_width
        self.sheet_height = sheet_height
        self.copies = copies
        self.content_top = PAGE_MARGIN_MM + HEADER_SPACE_MM + (RULER_SPACE_MM if scale_bar else 0.0)
        self.positions = self._place()

    @classmethod
    def for_sheet(cls, bbox: Rect, copies: int, scale_bar: bool) -> PageLayout:
        return cls(bbox.width, bbox.height, copies, scale_bar)

    @property
    def placed(self) -> int:
        return len(self.positions)

    @property
    def fits_all(self) -> bool:
        return self.placed >= self.copies

    def _place(self) -> list[Point]:
        eps = 1e-6
        w, h = self.sheet_width, self.sheet_height
        x, y = PAGE_MARGIN_MM, self.content_top
        right = PAGE_WIDTH_MM - PAGE_MARGIN_MM
        bottom = PAGE_HEIGHT_MM - PAGE_MARGIN_MM - HEADER_SPACE_MM
        positions: list[Point] = []
        for _ in range(self.copies):
            if x + w > right + eps and x > PAGE_MARGIN_MM:
                x, y = PAGE_MARGIN_MM, y + h + COPY_SPACING_MM
            if y + h > bottom + eps or x + w > right + eps:
                break
            positions.append(Point(x, y))
            x += w + COPY_SPACING_MM
        return positions
