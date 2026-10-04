"""Predefined label colors (typical Dupont jumper wire colors)."""

from __future__ import annotations

from dataclasses import dataclass

from ..i18n import Language, Translator, tr
from .colors import is_hex_color, normalize_hex


@dataclass(frozen=True)
class PaletteColor:
    name: str  # English name, also the translation key
    hex: str  # '#rrggbb'


JUMPER_PALETTE: tuple[PaletteColor, ...] = (
    PaletteColor("Black", "#1b1b1b"),
    PaletteColor("Brown", "#7b4a1e"),
    PaletteColor("Red", "#d32f2f"),
    PaletteColor("Orange", "#f57c00"),
    PaletteColor("Yellow", "#fdd835"),
    PaletteColor("Green", "#2e7d32"),
    PaletteColor("Blue", "#1565c0"),
    PaletteColor("Violet", "#7b1fa2"),
    PaletteColor("Gray", "#808080"),
    PaletteColor("White", "#ffffff"),
    # light tints save ink
    PaletteColor("Light red", "#ef9a9a"),
    PaletteColor("Light yellow", "#fff59d"),
    PaletteColor("Light green", "#a5d6a7"),
    PaletteColor("Light blue", "#90caf9"),
)

GROUND_COLOR = "#1b1b1b"
POWER_COLOR = "#d32f2f"

_BY_HEX = {c.hex: c for c in JUMPER_PALETTE}


def _build_name_index() -> dict[str, str]:
    """Map lower-case color names in every supported language to hex values."""
    index: dict[str, str] = {}
    for language in Language:
        translator = Translator(language)
        for color in JUMPER_PALETTE:
            for name in (color.name, translator.tr(color.name)):
                index[name.lower()] = color.hex
                index[name.lower().replace(" ", "")] = color.hex
    index["grey"] = index["gray"]
    return index


_BY_NAME = _build_name_index()


def color_display_name(hex_color: str) -> str:
    """Translated palette name of ``hex_color``, or the hex value for custom colors."""
    if not hex_color:
        return ""
    color = _BY_HEX.get(hex_color.lower())
    return tr(color.name) if color else hex_color


def resolve_color(value: str) -> str:
    """Turn user input (hex value or palette name in any language) into ``#rrggbb``.

    An empty string means "no color" and is returned unchanged.
    Raises :class:`ValueError` for unknown values.
    """
    text = value.strip()
    if not text:
        return ""
    if is_hex_color(text):
        return normalize_hex(text)
    key = text.lower()
    if key in _BY_NAME:
        return _BY_NAME[key]
    if key.replace(" ", "") in _BY_NAME:
        return _BY_NAME[key.replace(" ", "")]
    raise ValueError(f"unknown color: {value!r}")
