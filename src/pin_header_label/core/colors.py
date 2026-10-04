"""Color math on ``#rrggbb`` strings (no Qt required)."""

from __future__ import annotations

import re

_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

DARK_TEXT = "#111111"
LIGHT_TEXT = "#ffffff"


def is_hex_color(value: str) -> bool:
    """True for ``#rgb`` / ``#rrggbb`` (the leading ``#`` is optional)."""
    return bool(_HEX_RE.match(value.strip()))


def normalize_hex(value: str) -> str:
    """Return a lower-case ``#rrggbb`` string; raises :class:`ValueError` otherwise."""
    match = _HEX_RE.match(value.strip())
    if not match:
        raise ValueError(f"not a hex color: {value!r}")
    digits = match.group(1).lower()
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    return f"#{digits}"


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    digits = normalize_hex(value)[1:]
    return int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16)


def relative_luminance(value: str) -> float:
    """WCAG relative luminance in the range 0 (black) .. 1 (white)."""

    def channel(v: int) -> float:
        x = v / 255.0
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4

    r, g, b = hex_to_rgb(value)
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_text_color(background: str) -> str:
    """Black or white text, whichever has more contrast on ``background``."""
    lum = relative_luminance(background)
    white_contrast = 1.05 / (lum + 0.05)
    black_contrast = (lum + 0.05) / 0.05
    return LIGHT_TEXT if white_contrast > black_contrast else DARK_TEXT
