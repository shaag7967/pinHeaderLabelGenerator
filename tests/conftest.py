"""Shared fixtures.

On Linux Qt runs headless (offscreen platform); tests that need Qt request the
``qapp`` fixture.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

if sys.platform.startswith("linux"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pin_header_label.i18n import Language, set_language
from pin_header_label.layout import LabelLayout
from pin_header_label.model import Project

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


class MonospaceMetrics:
    """Predictable text metrics: every character is 60 units wide."""

    CHAR_WIDTH = 60.0
    TOP, BOTTOM = -75.0, 20.0

    def __init__(self, family: str = "", bold: bool = False) -> None:
        self.family = family
        self.bold = bold

    def advance(self, text: str) -> float:
        return len(text) * self.CHAR_WIDTH * (1.1 if self.bold else 1.0)

    def vertical_bounds(self, text: str) -> tuple[float, float]:
        return self.TOP, self.BOTTOM


def make_layout(project: Project) -> LabelLayout:
    return LabelLayout(project, MonospaceMetrics)


@pytest.fixture(autouse=True)
def english() -> None:
    """Every test starts with the English translation."""
    set_language(Language.ENGLISH)
    yield
    set_language(Language.ENGLISH)


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def example_project() -> Project:
    return Project.load(EXAMPLES / "example_header.json")


@pytest.fixture
def small_project() -> Project:
    """2x4 header with a few labels and colors."""
    project = Project(rows=4, cols=2)
    project.pin(0, 0).label = "GND"
    project.pin(0, 1).label = "VCC"
    project.pin(1, 0).label = "SDA"
    project.pin(1, 0).color = "#1565c0"
    project.pin(3, 1).label = "SCL"
    return project
