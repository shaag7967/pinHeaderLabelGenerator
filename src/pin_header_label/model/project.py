"""The label project: header geometry, styling, page settings and pin data."""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field, fields
from enum import StrEnum
from pathlib import Path

from ..core.auto_color import AutoColorizer
from ..core.labels import clean_label
from .enums import ColorStyle, LeaderMode, Numbering, SideMode
from .numbering import PinNumbering
from .pin import Pin

FORMAT_VERSION = 1

MAX_ROWS = 200
MAX_COPIES = 60
FONT_PT_MIN, FONT_PT_MAX = 4.0, 14.0
PITCH_MIN, PITCH_MAX = 0.5, 20.0
GAP_MIN, GAP_MAX = 0.3, 30.0
SCALE_MIN, SCALE_MAX = 50.0, 150.0

# Common pin header pitches in mm
STANDARD_PITCHES = (2.54, 2.0, 1.27, 2.5, 3.5, 3.96, 5.0, 5.08)

# Pins are always stored for both columns so switching between one- and
# two-row headers does not lose data.
_STORED_COLUMNS = 2


class ProjectFormatError(ValueError):
    """Raised when a project file cannot be parsed."""


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _coerce(value: object, default: object) -> object:
    """Convert a JSON value to the type of ``default``; fall back to ``default``."""
    try:
        if isinstance(default, bool):
            if isinstance(value, str):
                return value.strip().lower() in ("1", "true", "yes", "on")
            return bool(value)
        if isinstance(default, StrEnum):
            return type(default)(value)
        if isinstance(default, int):
            return int(float(value))  # type: ignore[arg-type]
        if isinstance(default, float):
            return float(value)  # type: ignore[arg-type]
        if isinstance(default, str):
            return "" if value is None else str(value)
    except (TypeError, ValueError):
        pass
    return default


@dataclass
class Project:
    # header
    title: str = ""
    rows: int = 15
    cols: int = 2  # 1 or 2 pin rows
    side_mode: SideMode = SideMode.RIGHT  # single-row headers only
    pitch: float = 2.54  # mm
    # text and labels
    font_family: str = ""  # '' = system default
    font_pt: float = 6.0
    bold: bool = False
    gap_mm: float = 1.2  # distance header outline -> label
    leaders: LeaderMode = LeaderMode.AUTO
    numbering: Numbering = Numbering.NONE
    # colors and marks
    color_style: ColorStyle = ColorStyle.FILL
    pin1_marker: bool = False
    outline: bool = True
    cut_frame: bool = True
    # page and print
    copies: int = 1
    scale_x: float = 100.0  # printer scale correction in percent
    scale_y: float = 100.0
    scale_bar: bool = True
    # pins[row][col]; may hold more rows than used (keeps data when the user
    # temporarily reduces the number of rows)
    pins: list[list[Pin]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.ensure_pins()

    # -- pin storage --------------------------------------------------------
    def ensure_pins(self) -> None:
        """Make sure pin storage covers all rows with two pins each."""
        while len(self.pins) < self.rows:
            self.pins.append([Pin() for _ in range(_STORED_COLUMNS)])
        for row in self.pins:
            while len(row) < _STORED_COLUMNS:
                row.append(Pin())

    def trim_pins(self) -> None:
        """Drop stored rows beyond ``rows``."""
        del self.pins[self.rows :]

    def normalize(self) -> None:
        """Clamp all settings to their valid ranges."""
        self.rows = int(_clamp(int(self.rows), 1, MAX_ROWS))
        self.cols = 1 if int(self.cols) == 1 else 2
        self.pitch = _clamp(float(self.pitch), PITCH_MIN, PITCH_MAX)
        self.font_pt = _clamp(float(self.font_pt), FONT_PT_MIN, FONT_PT_MAX)
        self.gap_mm = _clamp(float(self.gap_mm), GAP_MIN, GAP_MAX)
        self.copies = int(_clamp(int(self.copies), 1, MAX_COPIES))
        self.scale_x = _clamp(float(self.scale_x), SCALE_MIN, SCALE_MAX)
        self.scale_y = _clamp(float(self.scale_y), SCALE_MIN, SCALE_MAX)
        self.ensure_pins()

    # -- access -------------------------------------------------------------
    @property
    def numbering_scheme(self) -> PinNumbering:
        return PinNumbering(self.numbering, self.rows, self.cols)

    def pin_number(self, row: int, col: int) -> int | None:
        return self.numbering_scheme.number(row, col)

    def pin(self, row: int, col: int) -> Pin:
        return self.pins[row][col]

    def iter_pins(self) -> Iterator[tuple[int, int, Pin]]:
        """All visible pins as ``(row, col, pin)``, row by row."""
        for row in range(self.rows):
            for col in range(self.cols):
                yield row, col, self.pins[row][col]

    @property
    def label_count(self) -> int:
        return sum(1 for _r, _c, pin in self.iter_pins() if not pin.is_empty)

    # -- editing ------------------------------------------------------------
    def resize(self, rows: int) -> None:
        self.rows = int(_clamp(rows, 1, MAX_ROWS))
        self.ensure_pins()

    def insert_row(self, index: int) -> bool:
        if self.rows >= MAX_ROWS:
            return False
        self.trim_pins()
        self.pins.insert(index, [Pin() for _ in range(_STORED_COLUMNS)])
        self.resize(self.rows + 1)
        return True

    def delete_row(self, index: int) -> bool:
        if self.rows <= 1 or not 0 <= index < self.rows:
            return False
        self.trim_pins()
        self.pins.pop(index)
        self.resize(self.rows - 1)
        return True

    def clear_pins(self) -> None:
        for row in self.pins:
            for pin in row:
                pin.clear()

    def clear_colors(self) -> None:
        for row in self.pins:
            for pin in row:
                pin.color = ""

    def apply_auto_colors(self, colorizer: AutoColorizer | None = None) -> int:
        """Color well-known signal names; returns the number of changed pins."""
        colorizer = colorizer or AutoColorizer()
        changed = 0
        for _row, _col, pin in self.iter_pins():
            color = colorizer.color_for(pin.label)
            if color and color != pin.color:
                pin.color = color
                changed += 1
        return changed

    def set_column_labels(self, columns: Sequence[Sequence[str]], fit_rows: bool = True) -> None:
        """Replace the labels column by column (top to bottom); colors are kept.

        With ``fit_rows`` the number of rows is set to the longest list.
        """
        self.trim_pins()
        longest = max((len(labels) for labels in columns), default=0)
        if fit_rows and longest > 0:
            self.resize(longest)
        for col, labels in enumerate(columns[: self.cols]):
            for row in range(self.rows):
                self.pins[row][col].label = clean_label(labels[row]) if row < len(labels) else ""

    def paste_labels(self, row: int, col: int, grid: Sequence[Sequence[str]]) -> None:
        """Paste a block of labels with its top-left cell at (row, col).

        Rows are added when the block reaches beyond the last row; cells beyond
        the last column are ignored.
        """
        self.trim_pins()
        if row + len(grid) > self.rows:
            self.resize(row + len(grid))
        for dr, cells in enumerate(grid):
            if row + dr >= self.rows:
                break
            for dc, text in enumerate(cells):
                if col + dc >= self.cols:
                    break
                self.pins[row + dr][col + dc].label = clean_label(text)

    # -- serialization ------------------------------------------------------
    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {"format_version": FORMAT_VERSION}
        for f in fields(self):
            if f.name == "pins":
                continue
            value = getattr(self, f.name)
            data[f.name] = value.value if isinstance(value, StrEnum) else value
        data["pins"] = [[pin.to_dict() for pin in row[: self.cols]] for row in self.pins[: self.rows]]
        return data

    @classmethod
    def from_dict(cls, data: object) -> Project:
        if not isinstance(data, dict):
            raise ProjectFormatError("project data must be a JSON object")
        defaults = cls()
        project = cls()
        for f in fields(cls):
            if f.name != "pins" and f.name in data:
                setattr(project, f.name, _coerce(data[f.name], getattr(defaults, f.name)))
        raw_pins = data.get("pins", [])
        if not isinstance(raw_pins, list):
            raise ProjectFormatError("'pins' must be a list of rows")
        project.pins = [
            [Pin.from_dict(p) for p in row[:_STORED_COLUMNS]] for row in raw_pins if isinstance(row, list)
        ]
        project.normalize()
        return project

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n"

    @classmethod
    def from_json(cls, text: str) -> Project:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProjectFormatError(f"invalid JSON: {exc}") from exc
        return cls.from_dict(data)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> Project:
        return cls.from_json(Path(path).read_text(encoding="utf-8"))
