"""Automatic coloring of well-known signal names (ground, supply)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .palette import GROUND_COLOR, POWER_COLOR


@dataclass(frozen=True)
class ColorRule:
    pattern: re.Pattern[str]
    color: str

    def matches(self, label: str) -> bool:
        return bool(self.pattern.match(label.strip()))


GROUND_RULE = ColorRule(re.compile(r"^(gnd\w*|agnd|dgnd|pgnd|vss\w*|0v|masse)$", re.I), GROUND_COLOR)
POWER_RULE = ColorRule(
    re.compile(r"^(\+?\d+([.,]\d+)?v\d*|vcc\w*|vdd\w*|vin|vbat\w*|vbus|v\+)$", re.I), POWER_COLOR
)


class AutoColorizer:
    """Assigns colors to labels by matching them against an ordered rule list."""

    DEFAULT_RULES: tuple[ColorRule, ...] = (GROUND_RULE, POWER_RULE)

    def __init__(self, rules: tuple[ColorRule, ...] = DEFAULT_RULES) -> None:
        self.rules = rules

    def color_for(self, label: str) -> str | None:
        """Color of the first matching rule, or ``None`` if no rule matches."""
        for rule in self.rules:
            if rule.matches(label):
                return rule.color
        return None
