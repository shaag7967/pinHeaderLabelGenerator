"""Pin lists from text and CSV files.

Supported formats (see README for examples):

* ``.txt`` - one label per line in pin number order (pin 1, 2, 3, ...).
* ``.csv`` / ``.tsv`` with a header row:

  * ``pin``, ``label`` [, ``color``] - labels by pin number, in any order;
  * ``left``, ``right`` [, ``left_color``, ``right_color``] - two-row header,
    one line per row, top to bottom;
  * ``label`` [, ``color``] - single-row header, top to bottom.

* ``.csv`` / ``.tsv`` without a header row: if the first column holds pin
  numbers it is read as ``pin, label[, color]``, otherwise as labels only
  (one column per header column).

Pin numbers are mapped to positions with the numbering scheme of the target
project (zigzag for two-row headers without numbering).
"""

from __future__ import annotations

import csv
import io
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ..core.labels import clean_label, split_lines
from ..core.palette import resolve_color
from ..i18n import tr
from ..model import PinNumbering, Project
from ..model.project import MAX_ROWS

CSV_SUFFIXES = (".csv", ".tsv")
TEXT_SUFFIXES = (".txt",)
SUPPORTED_SUFFIXES = TEXT_SUFFIXES + CSV_SUFFIXES

_PIN_NUMBER_RE = re.compile(r"^\s*(?:pin\s*|p)?(\d+)\s*$", re.I)


class PinListFormatError(ValueError):
    """Raised when a pin list cannot be read."""


@dataclass(frozen=True)
class PinEntry:
    label: str = ""
    color: str = ""


class PinList(ABC):
    """Imported pin assignments that can be applied to a project."""

    @property
    @abstractmethod
    def label_count(self) -> int:
        """Number of non-empty labels."""

    @abstractmethod
    def apply_to(self, project: Project) -> None:
        """Replace all labels and colors of ``project`` and resize it to fit."""

    @staticmethod
    def _check_rows(rows: int) -> None:
        if rows > MAX_ROWS:
            raise PinListFormatError(tr("Too many pins: at most {n} rows are supported.", n=MAX_ROWS))

    @staticmethod
    def _reset(project: Project, rows: int) -> None:
        project.resize(rows)
        project.trim_pins()
        project.clear_pins()


@dataclass
class RowPinList(PinList):
    """Labels row by row, top to bottom; one entry per header column."""

    rows: list[tuple[PinEntry, ...]]
    columns: int  # 1 or 2

    @property
    def label_count(self) -> int:
        return sum(1 for row in self.rows for entry in row if entry.label)

    def apply_to(self, project: Project) -> None:
        self._check_rows(len(self.rows))
        project.cols = self.columns
        self._reset(project, len(self.rows))
        for r, entries in enumerate(self.rows):
            for c, entry in enumerate(entries[: self.columns]):
                pin = project.pin(r, c)
                pin.label, pin.color = entry.label, entry.color


@dataclass
class NumberedPinList(PinList):
    """Labels by pin number; positions follow the project's numbering scheme."""

    entries: dict[int, PinEntry]

    @property
    def pin_count(self) -> int:
        return max(self.entries, default=0)

    @property
    def label_count(self) -> int:
        return sum(1 for entry in self.entries.values() if entry.label)

    def apply_to(self, project: Project) -> None:
        rows = PinNumbering.rows_for(self.pin_count, project.cols)
        self._check_rows(rows)
        self._reset(project, rows)
        numbering = project.numbering_scheme
        for number, entry in self.entries.items():
            pin = project.pin(*numbering.position(number))
            pin.label, pin.color = entry.label, entry.color


class _Column(Enum):
    PIN = "pin"
    LABEL = "label"
    COLOR = "color"
    LEFT = "left"
    RIGHT = "right"
    LEFT_COLOR = "left_color"
    RIGHT_COLOR = "right_color"


_HEADER_ALIASES: dict[_Column, tuple[str, ...]] = {
    _Column.PIN: ("pin", "pin no", "pin nr", "pin number", "number", "no", "nr", "#", "nummer"),
    _Column.LABEL: ("label", "name", "signal", "function", "net", "bezeichnung", "funktion"),
    _Column.COLOR: ("color", "colour", "farbe"),
    _Column.LEFT: ("left", "left label", "links"),
    _Column.RIGHT: ("right", "right label", "rechts"),
    _Column.LEFT_COLOR: ("left color", "left colour", "color left", "farbe links"),
    _Column.RIGHT_COLOR: ("right color", "right colour", "color right", "farbe rechts"),
}
_ALIAS_INDEX = {alias: column for column, aliases in _HEADER_ALIASES.items() for alias in aliases}

# (line number, cells)
_CsvRow = tuple[int, list[str]]


def _normalize_header(cell: str) -> str:
    return " ".join(re.sub(r"[_\-.]", " ", cell.strip().lower()).split())


def _cell(cells: list[str], index: int | None) -> str:
    if index is None or index >= len(cells):
        return ""
    return cells[index].strip()


class PinListReader:
    """Reads pin lists from text and CSV files."""

    def read(self, path: str | Path) -> PinList:
        path = Path(path)
        text = self._decode(path.read_bytes())
        suffix = path.suffix.lower()
        if suffix in CSV_SUFFIXES:
            return self.parse_csv(text, delimiter="\t" if suffix == ".tsv" else None)
        return self.parse_text(text)

    @staticmethod
    def _decode(data: bytes) -> str:
        try:
            return data.decode("utf-8-sig")
        except UnicodeDecodeError:
            return data.decode("cp1252", errors="replace")  # e.g. CSV saved by Excel

    # -- plain text ---------------------------------------------------------
    def parse_text(self, text: str) -> NumberedPinList:
        """One label per line in pin number order."""
        entries = {i + 1: PinEntry(clean_label(line)) for i, line in enumerate(split_lines(text))}
        result = NumberedPinList(entries)
        if not result.label_count:
            raise PinListFormatError(tr("The pin list contains no labels."))
        return result

    # -- CSV ----------------------------------------------------------------
    def parse_csv(self, text: str, delimiter: str | None = None) -> PinList:
        rows = self._csv_rows(text, delimiter)
        if not rows:
            raise PinListFormatError(tr("The pin list contains no labels."))
        columns = self._header_columns(rows[0][1])
        result = self._with_header(columns, rows[1:]) if columns else self._without_header(rows)
        if not result.label_count:
            raise PinListFormatError(tr("The pin list contains no labels."))
        return result

    @staticmethod
    def _csv_rows(text: str, delimiter: str | None) -> list[_CsvRow]:
        if delimiter is None:
            try:
                delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t").delimiter
            except csv.Error:
                delimiter = ","
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        rows = [(reader.line_num, cells) for cells in reader]
        while rows and not any(c.strip() for c in rows[-1][1]):
            rows.pop()
        return rows

    @staticmethod
    def _header_columns(cells: list[str]) -> dict[_Column, int]:
        columns: dict[_Column, int] = {}
        for index, cell in enumerate(cells):
            column = _ALIAS_INDEX.get(_normalize_header(cell))
            if column is not None and column not in columns:
                columns[column] = index
        return columns

    def _with_header(self, columns: dict[_Column, int], rows: list[_CsvRow]) -> PinList:
        if _Column.PIN in columns:
            if _Column.LABEL not in columns:
                raise PinListFormatError(tr("A 'pin' column needs a 'label' column."))
            return self._numbered(
                rows, columns[_Column.PIN], columns[_Column.LABEL], columns.get(_Column.COLOR)
            )
        if _Column.LEFT in columns or _Column.RIGHT in columns:
            spec = [
                (columns.get(_Column.LEFT), columns.get(_Column.LEFT_COLOR)),
                (columns.get(_Column.RIGHT), columns.get(_Column.RIGHT_COLOR)),
            ]
            return self._by_row(rows, spec)
        if _Column.LABEL in columns:
            return self._by_row(rows, [(columns[_Column.LABEL], columns.get(_Column.COLOR))])
        raise PinListFormatError(tr("The pin list has no label column."))

    def _without_header(self, rows: list[_CsvRow]) -> PinList:
        filled = [cells for _line, cells in rows if any(c.strip() for c in cells)]
        if all(len(cells) >= 2 and _PIN_NUMBER_RE.match(cells[0]) for cells in filled):
            return self._numbered(rows, 0, 1, 2)
        width = max(len(cells) for cells in filled)
        spec = [(0, None), (1, None)] if width >= 2 else [(0, None)]
        return self._by_row(rows, spec)

    def _numbered(
        self, rows: list[_CsvRow], pin_col: int, label_col: int, color_col: int | None
    ) -> NumberedPinList:
        entries: dict[int, PinEntry] = {}
        for line, cells in rows:
            raw_number = _cell(cells, pin_col)
            label = clean_label(_cell(cells, label_col))
            color = _cell(cells, color_col)
            if not raw_number:
                if label or color:
                    raise PinListFormatError(tr("Line {line}: pin number missing.", line=line))
                continue
            match = _PIN_NUMBER_RE.match(raw_number)
            if not match or int(match.group(1)) < 1:
                raise PinListFormatError(
                    tr("Line {line}: invalid pin number {value!r}.", line=line, value=raw_number)
                )
            number = int(match.group(1))
            if number in entries:
                raise PinListFormatError(tr("Line {line}: pin {n} appears twice.", line=line, n=number))
            entries[number] = PinEntry(label, self._color(color, line))
        return NumberedPinList(entries)

    def _by_row(self, rows: list[_CsvRow], spec: list[tuple[int | None, int | None]]) -> RowPinList:
        result = [
            tuple(
                PinEntry(clean_label(_cell(cells, label_col)), self._color(_cell(cells, color_col), line))
                for label_col, color_col in spec
            )
            for line, cells in rows
        ]
        return RowPinList(result, columns=len(spec))

    @staticmethod
    def _color(value: str, line: int) -> str:
        try:
            return resolve_color(value)
        except ValueError:
            raise PinListFormatError(
                tr("Line {line}: unknown color {value!r}.", line=line, value=value)
            ) from None
