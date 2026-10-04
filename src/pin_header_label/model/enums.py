"""Enumerations for project settings.

The values are stored verbatim in project files, so they must not change.
"""

from enum import StrEnum


class SideMode(StrEnum):
    """Label side for single-row headers."""

    RIGHT = "right"
    LEFT = "left"
    ALTERNATE = "alternate"


class LeaderMode(StrEnum):
    """When to draw leader lines between pin and label."""

    AUTO = "auto"  # only where a label had to be shifted
    ALWAYS = "always"


class ColorStyle(StrEnum):
    """How a pin color is shown on its label."""

    FILL = "fill"  # colored background
    TEXT = "text"  # colored text
    OUTLINE = "outline"  # colored frame


class Numbering(StrEnum):
    """Pin numbering scheme of two-row headers."""

    NONE = "none"
    ZIGZAG = "zigzag"  # 1|2, 3|4, ... (box headers, IDC)
    DIP = "dip"  # down the left side, up the right side
    COLUMN = "column"  # down the left side, then down the right side
