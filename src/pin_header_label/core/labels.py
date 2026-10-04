"""Normalization of label text entered or pasted by the user."""

from __future__ import annotations

import re

_BULLET_RE = re.compile(r"^[*\-•·]\s+")

# Words that mark an unused pin in pasted lists
EMPTY_MARKERS = frozenset({"leer", "empty", "-", "–", "—"})


def clean_label(text: str) -> str:
    """Strip whitespace and list bullets; empty markers become ``""``."""
    text = _BULLET_RE.sub("", text.strip())
    if text.lower() in EMPTY_MARKERS:
        return ""
    return text


def split_lines(text: str) -> list[str]:
    """Split text into lines (any line ending), dropping trailing blank lines."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    return lines
