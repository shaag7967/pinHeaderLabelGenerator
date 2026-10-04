"""Dialogs."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.labels import split_lines
from ..i18n import tr
from ..model import Project


class PinListDialog(QDialog):
    """Paste plain pin lists, one line per pin from top to bottom, per header side."""

    def __init__(self, parent: QWidget, project: Project) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Paste pin lists"))
        self.resize(560, 520)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                tr(
                    "One line per pin, from top to bottom. “-”, “empty” or a blank line = unused.\n"
                    "Bullets (*, -, •) at the start of a line are removed."
                )
            )
        )
        columns = QHBoxLayout()
        self.edits: list[QPlainTextEdit] = []
        names = [tr("Left side"), tr("Right side")] if project.cols == 2 else [tr("Pins")]
        for col, name in enumerate(names):
            box = QVBoxLayout()
            box.addWidget(QLabel(name))
            edit = QPlainTextEdit()
            edit.setPlainText(self._prefill(project, col))
            box.addWidget(edit)
            columns.addLayout(box)
            self.edits.append(edit)
        layout.addLayout(columns)
        self.fit_rows_check = QCheckBox(tr("Set number of rows to the longest list"))
        self.fit_rows_check.setChecked(True)
        layout.addWidget(self.fit_rows_check)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _prefill(project: Project, col: int) -> str:
        labels = [project.pin(row, col).label for row in range(project.rows)]
        while labels and not labels[-1]:
            labels.pop()
        return "\n".join(label or "-" for label in labels)

    def lists(self) -> list[list[str]]:
        """The raw lines of every side (cleaned by :meth:`Project.set_column_labels`)."""
        return [split_lines(edit.toPlainText()) for edit in self.edits]

    @property
    def fit_rows(self) -> bool:
        return self.fit_rows_check.isChecked()
