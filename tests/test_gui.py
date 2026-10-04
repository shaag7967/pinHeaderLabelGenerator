"""GUI smoke tests (offscreen)."""

import pytest

from pin_header_label.i18n import Language
from pin_header_label.model import Numbering, Project

from conftest import EXAMPLES

pytestmark = pytest.mark.usefixtures("qapp")


@pytest.fixture
def languages(qapp, tmp_path):
    from PySide6.QtCore import QSettings

    from pin_header_label.gui.language import LanguageManager

    manager = LanguageManager(qapp, QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat))
    manager.apply(Language.ENGLISH)
    yield manager
    manager.apply(Language.ENGLISH, persist=False)


@pytest.fixture
def window(languages):
    from pin_header_label.gui.main_window import MainWindow

    win = MainWindow(Project(), None, languages)
    assert win.open_path(EXAMPLES / "example_header.json")
    yield win
    win.dirty = False
    win.close()
    win.deleteLater()


def test_opens_project(window):
    assert window.project.label_count == 19
    assert window.table.rowCount() == 15
    assert window.table.columnCount() == 4
    assert "example_header.json" in window.windowTitle()
    assert "19 labels" in window.status_label.text()


def test_settings_change_updates_project_and_table(window):
    window.settings.cols_combo.setCurrentIndex(window.settings.cols_combo.findData(1))
    assert window.project.cols == 1
    assert window.table.columnCount() == 2
    assert window.dirty
    assert window.windowTitle().endswith("*")

    window.settings.rows_spin.setValue(20)
    assert window.project.rows == 20
    assert window.table.rowCount() == 20


def test_numbering_changes_row_headers(window):
    combo = window.settings.numbering_combo
    combo.setCurrentIndex(combo.findData(Numbering.ZIGZAG))
    assert window.project.numbering == Numbering.ZIGZAG
    assert window.table.verticalHeaderItem(0).text() == "1 | 2"


def test_editing_a_label_cell(window):
    window.table.item(6, 0).setText("NEW")
    assert window.project.pin(6, 0).label == "NEW"
    assert window.dirty


def test_table_row_operations_keep_settings_in_sync(window):
    window.table.insert_row(0)
    assert window.project.rows == 16
    assert window.settings.rows_spin.value() == 16
    assert window.project.pin(1, 1).label == "NTC housing"
    window.table.delete_row(0)
    assert window.settings.rows_spin.value() == 15


def test_color_actions(window):
    window.remove_colors()
    assert all(not pin.color for _r, _c, pin in window.project.iter_pins())
    window.auto_colors()
    assert window.project.pin(8, 0).color == "#1b1b1b"  # GND
    assert window.table.item(8, 1).text() == "Black"


def test_clipboard_paste(window):
    from PySide6.QtGui import QGuiApplication

    QGuiApplication.clipboard().setText("A\tB\nC\tD\n")
    window.table.setCurrentCell(14, 0)
    window.table.paste_clipboard()
    assert window.project.rows == 16
    assert window.settings.rows_spin.value() == 16
    assert [window.project.pin(15, c).label for c in (0, 1)] == ["C", "D"]


def test_language_switch_rebuilds_ui(window, languages):
    languages.apply(Language.GERMAN)
    assert [a.text() for a in window.menuBar().actions()] == ["&Datei", "&Bearbeiten", "&Sprache", "&Hilfe"]
    assert window.table.horizontalHeaderItem(0).text() == "Linke Seite"
    assert "Labels" in window.status_label.text()
    assert window.project.label_count == 19  # project survives the rebuild
    languages.apply(Language.ENGLISH)
    assert window.menuBar().actions()[0].text() == "&File"


def test_language_is_persisted(languages):
    languages.apply(Language.GERMAN)
    assert languages.saved_language() == Language.GERMAN


def test_save(window, tmp_path):
    window.path = tmp_path / "saved.json"
    window.mark_dirty()
    assert window.save()
    assert not window.dirty
    assert Project.load(tmp_path / "saved.json").label_count == 19


def test_preview_page_mode(window):
    window.view_mode.setCurrentIndex(1)
    window.refresh()
    assert window.preview.item.page_painter is not None
