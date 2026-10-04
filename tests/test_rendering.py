"""Qt rendering and export (headless)."""

import pytest

from pin_header_label.i18n import Language, Translator
from pin_header_label.layout import PAGE_HEIGHT_MM, PAGE_WIDTH_MM
from pin_header_label.model import ColorStyle, Numbering

pytestmark = pytest.mark.usefixtures("qapp")


@pytest.fixture
def exporter(example_project):
    from pin_header_label.rendering import Exporter

    return Exporter(example_project)


def test_qt_metrics_measure_text():
    from pin_header_label.rendering import QtTextMetrics

    metrics = QtTextMetrics.for_font("", False)
    assert metrics.advance("WWW") > metrics.advance("i") > 0
    top, bottom = metrics.vertical_bounds("Hg")
    assert top < 0 < bottom


def test_create_layout_with_real_fonts(example_project):
    from pin_header_label.rendering import create_layout

    layout = create_layout(example_project)
    assert len(layout.labels) == example_project.label_count
    assert layout.bbox.width > layout.width


def test_pdf(exporter, tmp_path):
    result = exporter.export_pdf(tmp_path / "out.pdf")
    data = (tmp_path / "out.pdf").read_bytes()
    assert data.startswith(b"%PDF")
    assert result.complete
    assert result.copies_placed == 1


def test_png_page_size_and_dpi(exporter, tmp_path):
    from PySide6.QtGui import QImage

    exporter.export_png(tmp_path / "out.png", dpi=100)
    image = QImage(str(tmp_path / "out.png"))
    assert image.width() == round(PAGE_WIDTH_MM / 25.4 * 100)
    assert image.height() == round(PAGE_HEIGHT_MM / 25.4 * 100)
    assert round(image.dotsPerMeterX() * 0.0254) == 100


def test_png_label_only_is_cropped_and_not_blank(exporter, example_project, tmp_path):
    from PySide6.QtGui import QColor, QImage

    from pin_header_label.rendering import create_layout

    exporter.export_png(tmp_path / "label.png", dpi=200, label_only=True)
    image = QImage(str(tmp_path / "label.png"))
    bbox = create_layout(example_project).bbox
    assert image.width() == round(bbox.width / 25.4 * 200)
    colors = {image.pixelColor(x, image.height() // 2).name() for x in range(0, image.width(), 3)}
    assert len(colors - {QColor("#ffffff").name()}) > 3


def test_svg_is_written_in_mm(exporter, tmp_path):
    exporter.export_svg(tmp_path / "out.svg")
    text = (tmp_path / "out.svg").read_text(encoding="utf-8")
    assert "<svg" in text
    assert 'width="210mm"' in text or 'width="210.0mm"' in text or "210mm" in text


def test_copies_that_do_not_fit_are_reported(example_project, tmp_path):
    from pin_header_label.rendering import Exporter

    example_project.copies = 60
    result = Exporter(example_project).export_pdf(tmp_path / "many.pdf")
    assert not result.complete
    assert 1 < result.copies_placed < 60


@pytest.mark.parametrize("style", list(ColorStyle))
@pytest.mark.parametrize("numbering", [Numbering.NONE, Numbering.DIP])
def test_all_styles_render(example_project, tmp_path, style, numbering):
    from pin_header_label.rendering import Exporter

    example_project.color_style = style
    example_project.numbering = numbering
    example_project.title = "J1"
    Exporter(example_project).export_png(tmp_path / "s.png", dpi=72, label_only=True)
    assert (tmp_path / "s.png").stat().st_size > 0


def test_footer_text_is_translated(example_project):
    from pin_header_label.rendering import PagePainter, create_layout

    example_project.scale_x = 101.5
    layout = create_layout(example_project)
    english = PagePainter(layout, Translator(Language.ENGLISH)).footer_text()
    german = PagePainter(layout, Translator(Language.GERMAN)).footer_text()
    assert english == "2×15 pins · pitch 2.54 mm · font 8.0 pt · correction X 101.5 % / Y 100 %"
    assert german == "2×15 Pins · Raster 2,54 mm · Schrift 8,0 pt · Korrektur X 101,5 % / Y 100 %"


def test_unwritable_png_raises(exporter, tmp_path):
    with pytest.raises(OSError):
        exporter.export_png(tmp_path / "missing_dir" / "x.png", dpi=72)
