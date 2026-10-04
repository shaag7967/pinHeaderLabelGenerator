"""Settings form (header, text, colors, page)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFontComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..i18n import get_translator, tr
from ..model import ColorStyle, LeaderMode, Numbering, Project, SideMode
from ..model.project import (
    FONT_PT_MAX,
    FONT_PT_MIN,
    GAP_MAX,
    GAP_MIN,
    MAX_COPIES,
    MAX_ROWS,
    PITCH_MAX,
    PITCH_MIN,
    STANDARD_PITCHES,
)
from ..rendering.qt_metrics import make_font
from .widgets import make_combo, select_combo_data

# The GUI offers a narrower range than the file format allows
SCALE_SPIN_MIN, SCALE_SPIN_MAX = 90.0, 110.0
HINT_STYLE = "color: #666;"


def _double_spin(low: float, high: float, step: float, decimals: int, suffix: str) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(low, high)
    spin.setSingleStep(step)
    spin.setDecimals(decimals)
    spin.setSuffix(suffix)
    return spin


def _hint(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet(HINT_STYLE)
    return label


class SettingsPanel(QWidget):
    """All project settings except the pins themselves.

    ``changed`` is emitted on every user edit; call :meth:`apply_to` to copy
    the values into the project.
    """

    changed = Signal()
    auto_colors_requested = Signal()
    remove_colors_requested = Signal()
    paste_lists_requested = Signal()
    import_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._loading = False
        layout = QVBoxLayout(self)
        layout.addWidget(self._header_group())
        layout.addWidget(self._text_group())
        layout.addWidget(self._color_group())
        layout.addWidget(self._page_group())
        paste = QPushButton(tr("Paste pin lists…"))
        paste.clicked.connect(self.paste_lists_requested)
        import_button = QPushButton(tr("Import pin list…"))
        import_button.clicked.connect(self.import_requested)
        layout.addWidget(paste)
        layout.addWidget(import_button)
        layout.addStretch(1)
        self._connect_signals()

    # -- construction -------------------------------------------------------
    def _header_group(self) -> QGroupBox:
        group = QGroupBox(tr("Pin header"))
        form = QFormLayout(group)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText(tr("optional, e.g. J1"))
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, MAX_ROWS)
        self.cols_combo = make_combo([(tr("2 rows (double row)"), 2), (tr("1 row"), 1)])
        self.side_combo = make_combo(
            [
                (tr("right"), SideMode.RIGHT),
                (tr("left"), SideMode.LEFT),
                (tr("alternating"), SideMode.ALTERNATE),
            ]
        )
        self.pitch_spin = _double_spin(PITCH_MIN, PITCH_MAX, 0.01, 2, " mm")
        pitch_button = QToolButton()
        pitch_button.setText("▾")
        pitch_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        pitch_menu = QMenu(pitch_button)
        translator = get_translator()
        for value in STANDARD_PITCHES:
            pitch_menu.addAction(
                f"{translator.format_number(value)} mm", lambda v=value: self.pitch_spin.setValue(v)
            )
        pitch_button.setMenu(pitch_menu)
        pitch_row = QHBoxLayout()
        pitch_row.addWidget(self.pitch_spin, 1)
        pitch_row.addWidget(pitch_button)
        form.addRow(tr("Title:"), self.title_edit)
        form.addRow(tr("Rows (pins per column):"), self.rows_spin)
        form.addRow(tr("Type:"), self.cols_combo)
        form.addRow(tr("Labels (1 row):"), self.side_combo)
        form.addRow(tr("Pitch:"), pitch_row)
        return group

    def _text_group(self) -> QGroupBox:
        group = QGroupBox(tr("Font && labels"))
        form = QFormLayout(group)
        self.font_combo = QFontComboBox()
        self.font_spin = _double_spin(FONT_PT_MIN, FONT_PT_MAX, 0.5, 1, " pt")
        self.bold_check = QCheckBox(tr("bold"))
        self.gap_spin = _double_spin(GAP_MIN, GAP_MAX, 0.2, 1, " mm")
        self.leader_combo = make_combo(
            [(tr("only when needed"), LeaderMode.AUTO), (tr("always"), LeaderMode.ALWAYS)]
        )
        self.numbering_combo = make_combo(
            [
                (tr("none"), Numbering.NONE),
                (tr("zigzag (1|2, 3|4 …)"), Numbering.ZIGZAG),
                (tr("U shape / DIP"), Numbering.DIP),
                (tr("column by column"), Numbering.COLUMN),
            ]
        )
        form.addRow(tr("Font:"), self.font_combo)
        form.addRow(tr("Font size:"), self.font_spin)
        form.addRow("", self.bold_check)
        form.addRow(tr("Distance to header:"), self.gap_spin)
        form.addRow(tr("Leader lines:"), self.leader_combo)
        form.addRow(tr("Pin numbers:"), self.numbering_combo)
        return group

    def _color_group(self) -> QGroupBox:
        group = QGroupBox(tr("Colors && marks"))
        form = QFormLayout(group)
        self.style_combo = make_combo(
            [
                (tr("colored background"), ColorStyle.FILL),
                (tr("colored text"), ColorStyle.TEXT),
                (tr("colored frame"), ColorStyle.OUTLINE),
            ]
        )
        self.pin1_check = QCheckBox(tr("Pin 1 mark (▼ top left)"))
        self.outline_check = QCheckBox(tr("Header outline"))
        self.cut_check = QCheckBox(tr("Cutting frame"))
        auto_button = QPushButton(tr("Color GND/VCC automatically"))
        auto_button.clicked.connect(self.auto_colors_requested)
        remove_button = QPushButton(tr("Remove all colors"))
        remove_button.clicked.connect(self.remove_colors_requested)
        form.addRow(tr("Color display:"), self.style_combo)
        form.addRow(self.pin1_check)
        form.addRow(self.outline_check)
        form.addRow(self.cut_check)
        form.addRow(auto_button)
        form.addRow(remove_button)
        return group

    def _page_group(self) -> QGroupBox:
        group = QGroupBox(tr("Page && print (A4)"))
        form = QFormLayout(group)
        self.copies_spin = QSpinBox()
        self.copies_spin.setRange(1, MAX_COPIES)
        self.scale_x_spin = _double_spin(SCALE_SPIN_MIN, SCALE_SPIN_MAX, 0.1, 2, " %")
        self.scale_y_spin = _double_spin(SCALE_SPIN_MIN, SCALE_SPIN_MAX, 0.1, 2, " %")
        self.scale_bar_check = QCheckBox(tr("Check ruler on the page"))
        form.addRow(tr("Copies:"), self.copies_spin)
        form.addRow(tr("Scale X:"), self.scale_x_spin)
        form.addRow(tr("Scale Y:"), self.scale_y_spin)
        form.addRow(self.scale_bar_check)
        form.addRow(
            _hint(
                tr(
                    "Only change the scale if the printed 50 mm ruler does not measure exactly "
                    "50 mm (correction = 50 / measured × 100 %)."
                )
            )
        )
        return group

    def _connect_signals(self) -> None:
        self.title_edit.textChanged.connect(self._on_edit)
        for spin in (
            self.rows_spin,
            self.copies_spin,
            self.pitch_spin,
            self.font_spin,
            self.gap_spin,
            self.scale_x_spin,
            self.scale_y_spin,
        ):
            spin.valueChanged.connect(self._on_edit)
        for combo in (
            self.cols_combo,
            self.side_combo,
            self.leader_combo,
            self.numbering_combo,
            self.style_combo,
        ):
            combo.currentIndexChanged.connect(self._on_edit)
        for check in (
            self.bold_check,
            self.pin1_check,
            self.outline_check,
            self.cut_check,
            self.scale_bar_check,
        ):
            check.toggled.connect(self._on_edit)
        self.font_combo.currentFontChanged.connect(self._on_edit)

    # -- data exchange ------------------------------------------------------
    def load(self, project: Project) -> None:
        """Show the settings of ``project`` without emitting ``changed``."""
        self._loading = True
        self.title_edit.setText(project.title)
        self.rows_spin.setValue(project.rows)
        select_combo_data(self.cols_combo, project.cols)
        select_combo_data(self.side_combo, project.side_mode)
        self.pitch_spin.setValue(project.pitch)
        self.font_combo.setCurrentFont(make_font(project.font_family, False))
        self.font_spin.setValue(project.font_pt)
        self.bold_check.setChecked(project.bold)
        self.gap_spin.setValue(project.gap_mm)
        select_combo_data(self.leader_combo, project.leaders)
        select_combo_data(self.numbering_combo, project.numbering)
        select_combo_data(self.style_combo, project.color_style)
        self.pin1_check.setChecked(project.pin1_marker)
        self.outline_check.setChecked(project.outline)
        self.cut_check.setChecked(project.cut_frame)
        self.copies_spin.setValue(project.copies)
        self.scale_x_spin.setValue(project.scale_x)
        self.scale_y_spin.setValue(project.scale_y)
        self.scale_bar_check.setChecked(project.scale_bar)
        self.side_combo.setEnabled(project.cols == 1)
        self._loading = False

    def set_rows(self, rows: int) -> None:
        """Update the row count display without emitting ``changed``."""
        self._loading = True
        self.rows_spin.setValue(rows)
        self._loading = False

    def apply_to(self, project: Project) -> bool:
        """Copy the form values into ``project``.

        Returns True if the table structure (rows, columns, numbering) changed.
        """
        before = (project.rows, project.cols, project.numbering)
        project.title = self.title_edit.text()
        project.resize(self.rows_spin.value())
        project.cols = int(self.cols_combo.currentData())
        project.side_mode = SideMode(self.side_combo.currentData())
        project.pitch = self.pitch_spin.value()
        project.font_family = self.font_combo.currentFont().family()
        project.font_pt = self.font_spin.value()
        project.bold = self.bold_check.isChecked()
        project.gap_mm = self.gap_spin.value()
        project.leaders = LeaderMode(self.leader_combo.currentData())
        project.numbering = Numbering(self.numbering_combo.currentData())
        project.color_style = ColorStyle(self.style_combo.currentData())
        project.pin1_marker = self.pin1_check.isChecked()
        project.outline = self.outline_check.isChecked()
        project.cut_frame = self.cut_check.isChecked()
        project.copies = self.copies_spin.value()
        project.scale_x = self.scale_x_spin.value()
        project.scale_y = self.scale_y_spin.value()
        project.scale_bar = self.scale_bar_check.isChecked()
        self.side_combo.setEnabled(project.cols == 1)
        return (project.rows, project.cols, project.numbering) != before

    def _on_edit(self, *_args: object) -> None:
        if not self._loading:
            self.changed.emit()
