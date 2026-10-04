"""Minimal immutable 2D geometry types."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    x: float = 0.0
    y: float = 0.0


@dataclass(frozen=True)
class Rect:
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0

    @property
    def left(self) -> float:
        return self.x

    @property
    def top(self) -> float:
        return self.y

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @classmethod
    def from_edges(cls, left: float, top: float, right: float, bottom: float) -> Rect:
        return cls(left, top, right - left, bottom - top)

    @classmethod
    def bounding(cls, points: Iterable[Point]) -> Rect:
        pts = list(points)
        if not pts:
            return cls()
        return cls.from_edges(
            min(p.x for p in pts), min(p.y for p in pts), max(p.x for p in pts), max(p.y for p in pts)
        )

    def united(self, other: Rect) -> Rect:
        return Rect.from_edges(
            min(self.left, other.left),
            min(self.top, other.top),
            max(self.right, other.right),
            max(self.bottom, other.bottom),
        )

    def adjusted(self, dx1: float, dy1: float, dx2: float, dy2: float) -> Rect:
        """Move the edges like ``QRectF.adjusted`` (left, top, right, bottom)."""
        return Rect.from_edges(self.left + dx1, self.top + dy1, self.right + dx2, self.bottom + dy2)

    def contains_rect(self, other: Rect, tolerance: float = 1e-9) -> bool:
        return (
            other.left >= self.left - tolerance
            and other.top >= self.top - tolerance
            and other.right <= self.right + tolerance
            and other.bottom <= self.bottom + tolerance
        )
