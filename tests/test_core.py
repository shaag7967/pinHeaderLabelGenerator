"""Colors, palette, label cleaning and auto coloring."""

import pytest

from pin_header_label.core.auto_color import AutoColorizer
from pin_header_label.core.colors import (
    DARK_TEXT,
    LIGHT_TEXT,
    contrast_text_color,
    hex_to_rgb,
    is_hex_color,
    normalize_hex,
    relative_luminance,
)
from pin_header_label.core.labels import clean_label, split_lines
from pin_header_label.core.palette import (
    GROUND_COLOR,
    JUMPER_PALETTE,
    POWER_COLOR,
    color_display_name,
    resolve_color,
)
from pin_header_label.i18n import Language, set_language


class TestColors:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [("#ABCDEF", "#abcdef"), ("abc", "#aabbcc"), ("  #123456 ", "#123456"), ("#fff", "#ffffff")],
    )
    def test_normalize_hex(self, value, expected):
        assert normalize_hex(value) == expected

    @pytest.mark.parametrize("value", ["", "#12345", "red", "#ggg", "#1234567"])
    def test_invalid_hex(self, value):
        assert not is_hex_color(value)
        with pytest.raises(ValueError):
            normalize_hex(value)

    def test_hex_to_rgb(self):
        assert hex_to_rgb("#ff8000") == (255, 128, 0)

    def test_luminance_extremes(self):
        assert relative_luminance("#000000") == pytest.approx(0.0)
        assert relative_luminance("#ffffff") == pytest.approx(1.0)
        assert relative_luminance("#808080") == pytest.approx(0.2158, abs=1e-3)

    @pytest.mark.parametrize(
        ("background", "text"),
        [("#1b1b1b", LIGHT_TEXT), ("#1565c0", LIGHT_TEXT), ("#fdd835", DARK_TEXT), ("#ffffff", DARK_TEXT)],
    )
    def test_contrast_text(self, background, text):
        assert contrast_text_color(background) == text


class TestPalette:
    def test_palette_hex_values_are_normalized_and_unique(self):
        values = [c.hex for c in JUMPER_PALETTE]
        assert all(normalize_hex(v) == v for v in values)
        assert len(set(values)) == len(values)

    def test_display_name_is_translated(self):
        assert color_display_name("#d32f2f") == "Red"
        set_language(Language.GERMAN)
        assert color_display_name("#D32F2F") == "Rot"

    def test_display_name_of_custom_and_empty_color(self):
        assert color_display_name("#123456") == "#123456"
        assert color_display_name("") == ""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("red", "#d32f2f"),
            ("Rot", "#d32f2f"),
            ("LIGHT BLUE", "#90caf9"),
            ("lightblue", "#90caf9"),
            ("hellgrün", "#a5d6a7"),
            ("grey", "#808080"),
            ("#ABC", "#aabbcc"),
            ("", ""),
        ],
    )
    def test_resolve_color(self, value, expected):
        assert resolve_color(value) == expected

    def test_resolve_unknown_color(self):
        with pytest.raises(ValueError):
            resolve_color("ultraviolet")


class TestLabels:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("  GND ", "GND"),
            ("* SDA", "SDA"),
            ("- SCL", "SCL"),
            ("• TX", "TX"),
            ("-", ""),
            ("leer", ""),
            ("Empty", ""),
            ("—", ""),
            ("-5V", "-5V"),  # no blank after the dash: not a bullet
            ("*RESET", "*RESET"),
        ],
    )
    def test_clean_label(self, text, expected):
        assert clean_label(text) == expected

    def test_split_lines_handles_all_line_endings(self):
        assert split_lines("a\r\nb\rc\nd\n\n  \n") == ["a", "b", "c", "d"]

    def test_split_lines_keeps_inner_blank_lines(self):
        assert split_lines("a\n\nb") == ["a", "", "b"]


class TestAutoColorizer:
    @pytest.mark.parametrize("label", ["GND", "gnd1", "AGND", "VSS", "0V", "Masse", " GND "])
    def test_ground(self, label):
        assert AutoColorizer().color_for(label) == GROUND_COLOR

    @pytest.mark.parametrize(
        "label", ["VCC", "3V3", "+5V", "3.3V", "3,3V", "VDD_IO", "VIN", "VBAT", "VBUS", "V+"]
    )
    def test_power(self, label):
        assert AutoColorizer().color_for(label) == POWER_COLOR

    @pytest.mark.parametrize("label", ["SDA", "GPIO5", "V_SENSE", "", "LED"])
    def test_other_labels_are_not_colored(self, label):
        assert AutoColorizer().color_for(label) is None
