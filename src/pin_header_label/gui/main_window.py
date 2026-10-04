"""Main application window."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QLocale, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME, __version__
from ..i18n import Language, get_translator, tr
from ..importers import PinListFormatError, PinListReader
from ..layout import LabelLayout, PageLayout
from ..model import Project, ProjectFormatError
from ..rendering import Exporter, ExportResult, create_layout
from .dialogs import PinListDialog
from .language import LanguageManager
from .pin_table import PinTable
from .preview import PreviewView
from .settings_panel import SettingsPanel
from .widgets import make_combo

REFRESH_DELAY_MS = 40
STATUS_TIMEOUT_MS = 6000
DEFAULT_SPLITTER_SIZES = [350, 430, 670]
PROJECT_FILTER = "*.json"
PIN_LIST_FILTER = "*.txt *.csv *.tsv"


class MainWindow(QMainWindow):
    def __init__(self, project: Project, path: Path | None, languages: LanguageManager) -> None:
        super().__init__()
        self.project = project
        self.path = path
        self.dirty = False
        self.languages = languages
        self._page_view_before: bool | None = None
        self._actions: list[QAction] = []
        self._toolbar: QToolBar | None = None

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(REFRESH_DELAY_MS)
        self._refresh_timer.timeout.connect(self.refresh)

        self.status_label = QLabel()
        self.statusBar().addWidget(self.status_label, 1)

        self._build_ui()
        self._show_project()
        languages.language_changed.connect(self._on_language_changed)
        self.resize(1450, 860)

    # -- UI construction ----------------------------------------------------
    def _build_ui(self, view_index: int = 0, splitter_sizes: list[int] | None = None) -> None:
        """(Re)build all widgets and menus in the current language."""
        self.setLocale(QLocale())  # children inherit it (decimal separator of spin boxes)
        self.settings = SettingsPanel()
        self.settings.changed.connect(self._on_settings_changed)
        self.settings.auto_colors_requested.connect(self.auto_colors)
        self.settings.remove_colors_requested.connect(self.remove_colors)
        self.settings.paste_lists_requested.connect(self.paste_lists)
        self.settings.import_requested.connect(self.import_pin_list)
        scroll = QScrollArea()
        scroll.setWidget(self.settings)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(340)

        self.table = PinTable(self.project)
        self.table.pins_changed.connect(self.mark_dirty)
        self.table.rows_changed.connect(lambda: self.settings.set_rows(self.project.rows))
        table_box = QWidget()
        table_layout = QVBoxLayout(table_box)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.addWidget(self.table)
        hint = QLabel(
            tr(
                "Type/double-click: text · click a color cell: color · "
                "Ctrl+V: paste list · Del: clear · right-click: more"
            )
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")
        table_layout.addWidget(hint)

        preview_box = QWidget()
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        self.view_mode = make_combo([(tr("Label sheet"), "sheet"), (tr("Whole page (A4)"), "page")])
        self.view_mode.setCurrentIndex(view_index)
        self.view_mode.currentIndexChanged.connect(lambda _i: self.refresh())
        fit_button = QPushButton(tr("Fit"))
        real_button = QPushButton("1:1")
        real_button.setToolTip(tr("Approximately real size on screen"))
        bar.addWidget(QLabel(tr("Preview:")))
        bar.addWidget(self.view_mode)
        bar.addStretch(1)
        bar.addWidget(fit_button)
        bar.addWidget(real_button)
        preview_layout.addLayout(bar)
        self.preview = PreviewView()
        fit_button.clicked.connect(self.preview.fit)
        real_button.clicked.connect(self.preview.real_size)
        preview_layout.addWidget(self.preview)

        self.splitter = QSplitter()
        self.splitter.addWidget(scroll)
        self.splitter.addWidget(table_box)
        self.splitter.addWidget(preview_box)
        self.splitter.setStretchFactor(2, 1)
        self.splitter.setSizes(splitter_sizes or DEFAULT_SPLITTER_SIZES)
        self.setCentralWidget(self.splitter)
        self._build_menus()

    def _action(self, text: str, slot: Callable[[], object], shortcut: object = None) -> QAction:
        action = QAction(text, self)
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.triggered.connect(lambda _checked=False: slot())
        self._actions.append(action)
        return action

    def _build_menus(self) -> None:
        for action in self._actions:
            action.deleteLater()
        self._actions.clear()
        self.menuBar().clear()
        if self._toolbar is not None:
            self.removeToolBar(self._toolbar)
            self._toolbar.deleteLater()

        new = self._action(tr("New"), self.new_project, QKeySequence.StandardKey.New)
        open_ = self._action(tr("Open…"), self.open_project, QKeySequence.StandardKey.Open)
        save = self._action(tr("Save"), self.save, QKeySequence.StandardKey.Save)
        save_as = self._action(tr("Save as…"), self.save_as, QKeySequence.StandardKey.SaveAs)
        import_list = self._action(tr("Import pin list…"), self.import_pin_list, "Ctrl+I")
        pdf = self._action(tr("Export PDF…"), self.export_pdf, "Ctrl+E")
        png = self._action(tr("Export PNG…"), self.export_png)
        svg = self._action(tr("Export SVG…"), self.export_svg)
        preview = self._action(tr("Print preview…"), self.print_preview)
        print_ = self._action(tr("Print…"), self.print_page, QKeySequence.StandardKey.Print)
        quit_ = self._action(tr("Quit"), self.close, QKeySequence.StandardKey.Quit)

        file_menu = self.menuBar().addMenu(tr("&File"))
        for action in (
            new,
            open_,
            save,
            save_as,
            None,
            import_list,
            None,
            pdf,
            png,
            svg,
            None,
            preview,
            print_,
            None,
            quit_,
        ):
            file_menu.addSeparator() if action is None else file_menu.addAction(action)

        edit_menu = self.menuBar().addMenu(tr("&Edit"))
        edit_menu.addAction(self._action(tr("Paste pin lists…"), self.paste_lists))
        edit_menu.addAction(self._action(tr("Color GND/VCC automatically"), self.auto_colors))
        edit_menu.addAction(self._action(tr("Remove all colors"), self.remove_colors))
        edit_menu.addAction(self._action(tr("Clear all labels"), self.clear_all))

        language_menu = self.menuBar().addMenu(tr("&Language"))
        group = QActionGroup(language_menu)
        for language in Language:
            action = self._action(language.native_name, lambda lang=language: self.languages.apply(lang))
            action.setCheckable(True)
            action.setChecked(language == self.languages.language)
            group.addAction(action)
            language_menu.addAction(action)

        help_menu = self.menuBar().addMenu(tr("&Help"))
        help_menu.addAction(self._action(tr("About…"), self.about))

        self._toolbar = self.addToolBar(tr("Tools"))
        self._toolbar.setMovable(False)
        for action in (new, open_, save, None, pdf, png, None, preview, print_):
            self._toolbar.addSeparator() if action is None else self._toolbar.addAction(action)

    def _on_language_changed(self, _language: Language) -> None:
        self._build_ui(self.view_mode.currentIndex(), self.splitter.sizes())
        self._show_project(refit=False)

    # -- project <-> UI -----------------------------------------------------
    def _show_project(self, refit: bool = True) -> None:
        self.settings.load(self.project)
        self.table.set_project(self.project)
        self._update_title()
        self.refresh(refit=refit)

    def _set_project(self, project: Project, path: Path | None) -> None:
        self.project = project
        self.path = path
        self.dirty = False
        self._show_project()

    def _on_settings_changed(self) -> None:
        if self.settings.apply_to(self.project):
            self.table.rebuild()
        self.mark_dirty()

    def mark_dirty(self) -> None:
        if not self.dirty:
            self.dirty = True
            self._update_title()
        self._refresh_timer.start()

    def _update_title(self) -> None:
        name = self.path.name if self.path else tr("Untitled")
        self.setWindowTitle(f"{APP_NAME} – {name}{' *' if self.dirty else ''}")

    def refresh(self, refit: bool = False) -> None:
        layout = create_layout(self.project)
        page = self.view_mode.currentData() == "page"
        refit = refit or page != self._page_view_before
        self._page_view_before = page
        self.preview.show_layout(layout, page, refit)
        self.status_label.setText(self._status_text(layout))

    def _status_text(self, layout: LabelLayout) -> str:
        t = get_translator()
        parts = [tr("{n} labels", n=len(layout.labels))]
        if layout.shifted_count:
            parts.append(tr("{n} shifted (leader lines)", n=layout.shifted_count))
        parts.append(
            tr(
                "label {w} × {h} mm",
                w=t.format_number(layout.bbox.width, 1, trim_zeros=False),
                h=t.format_number(layout.bbox.height, 1, trim_zeros=False),
            )
        )
        page = PageLayout.for_sheet(layout.bbox, self.project.copies, self.project.scale_bar)
        if not page.fits_all:
            parts.append(
                tr(
                    "Note: only {placed} of {requested} copies fit on A4",
                    placed=page.placed,
                    requested=self.project.copies,
                )
            )
        return " · ".join(parts)

    # -- edit actions -------------------------------------------------------
    def paste_lists(self) -> None:
        dialog = PinListDialog(self, self.project)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.project.set_column_labels(dialog.lists(), dialog.fit_rows)
        self.settings.set_rows(self.project.rows)
        self.table.rebuild()
        self.mark_dirty()

    def import_pin_list(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, tr("Import pin list"), self._directory(), f"{tr('Pin lists')} ({PIN_LIST_FILTER})"
        )
        if not filename:
            return
        try:
            pin_list = PinListReader().read(filename)
        except (OSError, PinListFormatError) as exc:
            QMessageBox.critical(self, tr("Error"), tr("Could not import the pin list:\n{error}", error=exc))
            return
        if (
            self.project.label_count
            and QMessageBox.question(
                self, tr("Import pin list"), tr("Replace all labels and colors with the pin list?")
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        try:
            pin_list.apply_to(self.project)
        except PinListFormatError as exc:
            QMessageBox.critical(self, tr("Error"), tr("Could not import the pin list:\n{error}", error=exc))
            return
        self.settings.load(self.project)
        self.table.rebuild()
        self.mark_dirty()
        self.statusBar().showMessage(
            tr("Imported {n} labels from {path}", n=pin_list.label_count, path=filename), STATUS_TIMEOUT_MS
        )

    def auto_colors(self) -> None:
        self.project.apply_auto_colors()
        self.table.refresh_colors()
        self.mark_dirty()

    def remove_colors(self) -> None:
        self.project.clear_colors()
        self.table.refresh_colors()
        self.mark_dirty()

    def clear_all(self) -> None:
        if (
            QMessageBox.question(self, tr("Clear all labels"), tr("Delete all labels and colors?"))
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.project.clear_pins()
        self.table.rebuild()
        self.mark_dirty()

    # -- files --------------------------------------------------------------
    def _maybe_save(self) -> bool:
        if not self.dirty:
            return True
        answer = QMessageBox.question(
            self,
            tr("Unsaved changes"),
            tr("Save changes?"),
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self.save()
        return answer == QMessageBox.StandardButton.Discard

    def new_project(self) -> None:
        if self._maybe_save():
            self._set_project(Project(), None)

    def open_project(self) -> None:
        if not self._maybe_save():
            return
        filename, _ = QFileDialog.getOpenFileName(
            self, tr("Open project"), self._directory(), f"{tr('Pin label project')} ({PROJECT_FILTER})"
        )
        if filename:
            self.open_path(Path(filename))

    def open_path(self, path: Path) -> bool:
        try:
            self._set_project(Project.load(path), path)
        except (OSError, ProjectFormatError) as exc:
            QMessageBox.critical(self, tr("Error"), tr("Could not load the file:\n{error}", error=exc))
            return False
        return True

    def save(self) -> bool:
        if not self.path:
            return self.save_as()
        try:
            self.project.save(self.path)
        except OSError as exc:
            QMessageBox.critical(self, tr("Error"), tr("Saving failed:\n{error}", error=exc))
            return False
        self.dirty = False
        self._update_title()
        self.statusBar().showMessage(tr("Saved: {path}", path=self.path), STATUS_TIMEOUT_MS)
        return True

    def save_as(self) -> bool:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            tr("Save project"),
            str(Path(self._directory()) / f"{self._file_stem()}.json"),
            f"{tr('Pin label project')} ({PROJECT_FILTER})",
        )
        if not filename:
            return False
        self.path = Path(filename)
        return self.save()

    def _directory(self) -> str:
        return str(self.path.parent) if self.path else str(Path.home())

    def _file_stem(self) -> str:
        if self.path:
            return self.path.stem
        return re.sub(r"[^\w\-]+", "_", self.project.title.strip()) or "pinlabel"

    # -- export and print ---------------------------------------------------
    def _export(self, title: str, extension: str, export: Callable[[Path], ExportResult]) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            title,
            str(Path(self._directory()) / f"{self._file_stem()}.{extension}"),
            f"{extension.upper()} (*.{extension})",
        )
        if not filename:
            return
        try:
            result = export(Path(filename))
        except OSError as exc:
            QMessageBox.critical(self, tr("Error"), tr("Export failed:\n{error}", error=exc))
            return
        message = tr("Exported: {path}", path=filename)
        if not result.complete:
            message += " " + tr(
                "(only {placed} of {requested} copies fit on A4)",
                placed=result.copies_placed,
                requested=result.copies_requested,
            )
        self.statusBar().showMessage(message, STATUS_TIMEOUT_MS)

    def export_pdf(self) -> None:
        self._export(tr("Export PDF"), "pdf", Exporter(self.project).export_pdf)

    def export_png(self) -> None:
        choices = ["300 dpi", "600 dpi"]
        item, ok = QInputDialog.getItem(self, tr("Export PNG"), tr("Resolution:"), choices, 1, False)
        if ok:
            dpi = int(item.split()[0])
            self._export(tr("Export PNG"), "png", lambda path: Exporter(self.project).export_png(path, dpi))

    def export_svg(self) -> None:
        self._export(tr("Export SVG"), "svg", Exporter(self.project).export_svg)

    def print_page(self) -> None:
        from PySide6.QtPrintSupport import QPrintDialog

        printer = Exporter.create_printer()
        if QPrintDialog(printer, self).exec() == QDialog.DialogCode.Accepted:
            Exporter(self.project).print_to(printer)

    def print_preview(self) -> None:
        from PySide6.QtPrintSupport import QPrintPreviewDialog

        printer = Exporter.create_printer()
        dialog = QPrintPreviewDialog(printer, self)
        dialog.paintRequested.connect(lambda target: Exporter(self.project).print_to(target))
        dialog.resize(900, 1000)
        dialog.exec()

    def about(self) -> None:
        QMessageBox.about(
            self,
            tr("About {app}", app=APP_NAME),
            tr(
                "<h3>{app} {version}</h3>"
                "<p>Printable pin-out labels for pin headers.</p>"
                "<p>License: GNU GPL v3 or later<br>"
                '<a href="https://github.com/shaag7967/pinHeaderLabelGenerator">'
                "github.com/shaag7967/pinHeaderLabelGenerator</a></p>",
                app=APP_NAME,
                version=__version__,
            ),
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._maybe_save():
            event.accept()
        else:
            event.ignore()
