"""A single header pin."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Pin:
    label: str = ""
    color: str = ""  # '#rrggbb' or '' (no color)

    @property
    def is_empty(self) -> bool:
        return not self.label.strip()

    def clear(self) -> None:
        self.label = ""
        self.color = ""

    def to_dict(self) -> dict[str, str]:
        return {"label": self.label, "color": self.color}

    @classmethod
    def from_dict(cls, data: object) -> Pin:
        if not isinstance(data, dict):
            return cls()
        return cls(label=str(data.get("label", "") or ""), color=str(data.get("color", "") or ""))
