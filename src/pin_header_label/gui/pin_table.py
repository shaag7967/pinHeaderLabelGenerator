"""Table for editing pin labels and colors."""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QKeyEvent, QKeySequence
from PySide6.QtWidgets import QAbstractItemView, QMenu, QTableWidget, QTableWidgetItem

from ..core.colors import contrast_text_color
from ..core.labels import split_lines
from ..core.palette import color_display_name
from ..i18n import tr
from ..model import Numbering, Project
from .widgets import populate_color_menu

LABEL_COLUMN_WIDTH = 150
COLOR_COLUMN_WIDTH = 72
ROW_HEIGHT = 24


class CellKind(Enum):
    LABEL = "label"
    COLOR = "color"


class PinTable(QTableWidget):
    """Edits the pins of a project.

    Two-row headers are shown as ``left label | color | color | right label`` so
    the table mirrors the physical header.
    """

    pins_changed = Signal()  # labels or colors changed
    rows_changed = Signal()  # number of rows changed

    def __init__(self, project: Project) -> None:
        super().__init__()
        self.project = project
        self._updating = False
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        self.itemChanged.connect(self._on_item_changed)
        self.cellClicked.connect(self._on_cell_clicked)
        self.customContextMenuRequested.connect(self._on_context_menu)

    # -- structure ----------------------------------------------------------
    def set_project(self, project: Project) -> None:
        self.project = project
        self.rebuild()

    def column_map(self) -> list[tuple[CellKind, int]]:
        """Table columns as (kind, pin column)."""
        if self.project.cols == 2:
            return [(CellKind.LABEL, 0), (CellKind.COLOR, 0), (CellKind.COLOR, 1), (CellKind.LABEL, 1)]
        return [(CellKind.LABEL, 0), (CellKind.COLOR, 0)]

    def rebuild(self) -> None:
        project = self.project
        columns = self.column_map()
        self._updating = True
        self.clear()
        self.setColumnCount(len(columns))
        self.setRowCount(project.rows)
        if project.cols == 2:
            self.setHorizontalHeaderLabels([tr("Left side"), tr("Color"), tr("Color"), tr("Right side")])
        else:
            self.setHorizontalHeaderLabels([tr("Label"), tr("Color")])
        for row in range(project.rows):
            for index, (kind, col) in enumerate(columns):
                pin = project.pin(row, col)
                if kind == CellKind.LABEL:
                    item = QTableWidgetItem(pin.label)
                    if project.cols == 2 and col == 0:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item = QTableWidgetItem()
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    self._style_color_item(item, pin.color)
                self.setItem(row, index, item)
        self.setVerticalHeaderLabels([self._row_header(row) for row in range(project.rows)])
        for index, (kind, _col) in enumerate(columns):
            self.setColumnWidth(index, LABEL_COLUMN_WIDTH if kind == CellKind.LABEL else COLOR_COLUMN_WIDTH)
        self._updating = False

    def _row_header(self, row: int) -> str:
        project = self.project
        if project.numbering == Numbering.NONE:
            return str(row + 1)
        if project.cols == 2:
            return f"{project.pin_number(row, 0)} | {project.pin_number(row, 1)}"
        return str(project.pin_number(row, 0))

    @staticmethod
    def _style_color_item(item: QTableWidgetItem, hex_color: str) -> None:
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if hex_color:
            item.setBackground(QColor(hex_color))
            item.setForeground(QColor(contrast_text_color(hex_color)))
            item.setText(color_display_name(hex_color))
        else:
            item.setData(Qt.ItemDataRole.BackgroundRole, None)
            item.setData(Qt.ItemDataRole.ForegroundRole, None)
            item.setText("–")

    def refresh_colors(self) -> None:
        self._updating = True
        for row in range(self.project.rows):
            for index, (kind, col) in enumerate(self.column_map()):
                if kind == CellKind.COLOR:
                    self._style_color_item(self.item(row, index), self.project.pin(row, col).color)
        self._updating = False

    # -- selection ----------------------------------------------------------
    def selected_pins(self) -> list[tuple[int, int]]:
        columns = self.column_map()
        return sorted({(i.row(), columns[i.column()][1]) for i in self.selectedIndexes()})

    # -- editing ------------------------------------------------------------
    def apply_color(self, pins: list[tuple[int, int]], hex_color: str) -> None:
        for row, col in pins:
            self.project.pin(row, col).color = hex_color
        self.refresh_colors()
        self.pins_changed.emit()

    def clear_selected_cells(self) -> None:
        columns = self.column_map()
        for index in self.selectedIndexes():
            kind, col = columns[index.column()]
            pin = self.project.pin(index.row(), col)
            if kind == CellKind.LABEL:
                pin.label = ""
            else:
                pin.color = ""
        self.rebuild()
        self.pins_changed.emit()

    def insert_row(self, row: int) -> None:
        if self.project.insert_row(row):
            self._structure_changed()

    def delete_row(self, row: int) -> None:
        if self.project.delete_row(row):
            self._structure_changed()

    def paste_clipboard(self) -> None:
        """Paste text (lines = rows, tabs = columns) at the current cell."""
        lines = split_lines(QGuiApplication.clipboard().text())
        if not lines:
            return
        current = self.currentIndex()
        row = max(current.row(), 0)
        col = self.column_map()[max(current.column(), 0)][1]
        rows_before = self.project.rows
        self.project.paste_labels(row, col, [line.split("\t") for line in lines])
        self.rebuild()
        if self.project.rows != rows_before:
            self.rows_changed.emit()
        self.pins_changed.emit()

    def copy_selection(self) -> None:
        """Copy the selected labels as tab separated text."""
        columns = self.column_map()
        indexes = [i for i in self.selectedIndexes() if columns[i.column()][0] == CellKind.LABEL]
        if not indexes:
            return
        rows = sorted({i.row() for i in indexes})
        cols = sorted({i.column() for i in indexes})
        lines = ["\t".join(self.item(r, c).text() for c in cols) for r in rows]
        QGuiApplication.clipboard().setText("\n".join(lines))

    def _structure_changed(self) -> None:
        self.rebuild()
        self.rows_changed.emit()
        self.pins_changed.emit()

    # -- events -------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.matches(QKeySequence.StandardKey.Paste):
            self.paste_clipboard()
        elif event.matches(QKeySequence.StandardKey.Copy):
            self.copy_selection()
        elif event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.clear_selected_cells()
        else:
            super().keyPressEvent(event)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._updating:
            return
        kind, col = self.column_map()[item.column()]
        if kind != CellKind.LABEL:
            return
        self.project.pin(item.row(), col).label = item.text().strip()
        self.pins_changed.emit()

    def _on_cell_clicked(self, row: int, column: int) -> None:
        kind, col = self.column_map()[column]
        if kind != CellKind.COLOR:
            return
        pins = self.selected_pins()
        if (row, col) not in pins:
            pins = [(row, col)]
        menu = QMenu(self)
        populate_color_menu(menu, self, lambda h: self.apply_color(pins, h))
        rect = self.visualItemRect(self.item(row, column))
        menu.exec(self.viewport().mapToGlobal(rect.bottomLeft()))

    def _on_context_menu(self, pos: QPoint) -> None:
        pins = self.selected_pins()
        row = self.rowAt(pos.y())
        menu = QMenu(self)
        if pins:
            color_menu = menu.addMenu(tr("Color for selection"))
            populate_color_menu(color_menu, self, lambda h: self.apply_color(pins, h))
            menu.addAction(tr("Clear selected cells"), self.clear_selected_cells)
            menu.addSeparator()
        if row >= 0:
            menu.addAction(tr("Insert row above"), lambda: self.insert_row(row))
            menu.addAction(tr("Insert row below"), lambda: self.insert_row(row + 1))
            menu.addAction(tr("Delete row"), lambda: self.delete_row(row))
        menu.exec(self.viewport().mapToGlobal(pos))
