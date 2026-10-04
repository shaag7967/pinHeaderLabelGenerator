"""Mapping between pin positions (row, column) and pin numbers."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .enums import Numbering


@dataclass(frozen=True)
class PinNumbering:
    """Pin numbering of a header with ``rows`` rows and ``cols`` (1 or 2) columns.

    Rows and columns are zero based, pin numbers start at 1. Single-row headers
    are always numbered top to bottom.
    """

    scheme: Numbering
    rows: int
    cols: int

    @property
    def pin_count(self) -> int:
        return self.rows * self.cols

    def number(self, row: int, col: int) -> int | None:
        """Pin number at (row, col), or ``None`` if numbering is switched off."""
        if self.scheme == Numbering.NONE:
            return None
        if self.cols == 1:
            return row + 1
        if self.scheme == Numbering.ZIGZAG:
            return 2 * row + col + 1
        if self.scheme == Numbering.DIP:
            return row + 1 if col == 0 else 2 * self.rows - row
        return col * self.rows + row + 1

    def position(self, number: int) -> tuple[int, int]:
        """(row, col) of pin ``number``.

        Without a numbering scheme two-row headers are treated as zigzag
        (pin 1 left, pin 2 right, ...), the most common header layout.
        """
        if not 1 <= number <= self.pin_count:
            raise ValueError(f"pin {number} out of range 1..{self.pin_count}")
        index = number - 1
        if self.cols == 1:
            return index, 0
        if self.scheme in (Numbering.ZIGZAG, Numbering.NONE):
            return index // 2, index % 2
        if self.scheme == Numbering.DIP:
            return (index, 0) if index < self.rows else (2 * self.rows - number, 1)
        return (index, 0) if index < self.rows else (index - self.rows, 1)

    @staticmethod
    def rows_for(pin_count: int, cols: int) -> int:
        """Number of rows needed for ``pin_count`` pins."""
        return max(1, math.ceil(pin_count / cols))
