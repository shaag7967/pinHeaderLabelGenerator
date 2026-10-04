"""Export of label pages to PDF, PNG, SVG and printers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QMarginsF, QPointF, QRectF, QSize
from PySide6.QtGui import QColor, QImage, QPageLayout, QPageSize, QPainter, QPdfWriter

from .. import APP_NAME
from ..i18n import Translator, get_translator
from ..layout import PAGE_HEIGHT_MM, PAGE_WIDTH_MM
from ..model import Project
from .label_painter import LabelPainter
from .page_painter import PagePainter
from .primitives import begin_mm
from .qt_metrics import create_layout

if TYPE_CHECKING:
    from PySide6.QtPrintSupport import QPrinter

PDF_RESOLUTION = 1200
SVG_UNITS_PER_MM = 10.0


@dataclass(frozen=True)
class ExportResult:
    path: Path | None
    copies_placed: int
    copies_requested: int

    @property
    def complete(self) -> bool:
        """All requested copies fit on the page."""
        return self.copies_placed >= self.copies_requested


@dataclass(frozen=True)
class _Content:
    """What to draw and how large it is (mm)."""

    width: float
    height: float
    paint: Callable[[QPainter], None]
    copies_placed: int
    copies_requested: int

    def result(self, path: Path | None) -> ExportResult:
        return ExportResult(path, self.copies_placed, self.copies_requested)


class Exporter:
    """Renders a project to files or a printer.

    A full page contains instructions, check rulers, all label copies that fit
    and a footer. With ``label_only`` a single label without page decoration
    is exported (PNG/SVG), which is handy for documentation.
    """

    def __init__(self, project: Project, translator: Translator | None = None) -> None:
        self.project = project
        self.translator = translator or get_translator()

    def _content(self, label_only: bool = False) -> _Content:
        layout = create_layout(self.project)
        if label_only:
            label = LabelPainter(layout)
            return _Content(
                layout.bbox.width, layout.bbox.height, lambda p: label.paint(p, QPointF(0, 0)), 1, 1
            )
        page = PagePainter(layout, self.translator)
        return _Content(PAGE_WIDTH_MM, PAGE_HEIGHT_MM, page.paint, page.page.placed, self.project.copies)

    def _title(self) -> str:
        return self.project.title or self.translator.tr("Pin label")

    def export_pdf(self, path: str | Path) -> ExportResult:
        path = Path(path)
        content = self._content()
        writer = QPdfWriter(str(path))
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        writer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
        writer.setResolution(PDF_RESOLUTION)
        writer.setTitle(self._title())
        writer.setCreator(APP_NAME)
        painter = QPainter(writer)
        begin_mm(painter, writer.resolution())
        content.paint(painter)
        painter.end()
        return content.result(path)

    def export_png(self, path: str | Path, dpi: int = 600, label_only: bool = False) -> ExportResult:
        path = Path(path)
        content = self._content(label_only)
        width_px = round(content.width / 25.4 * dpi)
        height_px = round(content.height / 25.4 * dpi)
        image = QImage(width_px, height_px, QImage.Format.Format_RGB32)
        image.fill(QColor("#ffffff"))
        dots_per_meter = round(dpi / 0.0254)
        image.setDotsPerMeterX(dots_per_meter)
        image.setDotsPerMeterY(dots_per_meter)
        painter = QPainter(image)
        begin_mm(painter, dpi)
        content.paint(painter)
        painter.end()
        if not image.save(str(path)):
            raise OSError(self.translator.tr("Could not save PNG file: {path}", path=path))
        return content.result(path)

    def export_svg(self, path: str | Path, label_only: bool = False) -> ExportResult:
        from PySide6.QtSvg import QSvgGenerator

        path = Path(path)
        content = self._content(label_only)
        k = SVG_UNITS_PER_MM
        generator = QSvgGenerator()
        generator.setFileName(str(path))
        generator.setResolution(round(25.4 * k))  # -> width/height are written in mm
        generator.setSize(QSize(round(content.width * k), round(content.height * k)))
        generator.setViewBox(QRectF(0, 0, content.width * k, content.height * k))
        generator.setTitle(self._title())
        painter = QPainter(generator)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.scale(k, k)
        content.paint(painter)
        painter.end()
        return content.result(path)

    def print_to(self, printer: QPrinter) -> ExportResult:
        content = self._content()
        painter = QPainter(printer)
        begin_mm(painter, printer.resolution())
        content.paint(painter)
        painter.end()
        return content.result(None)

    @staticmethod
    def create_printer() -> QPrinter:
        """A4 portrait printer drawing from the paper corner (no driver margins)."""
        from PySide6.QtPrintSupport import QPrinter

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)
        printer.setFullPage(True)
        return printer
