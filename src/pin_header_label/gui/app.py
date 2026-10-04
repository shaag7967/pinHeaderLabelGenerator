"""GUI entry point (``pinlabel-gui``)."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from .. import APP_NAME, __version__
from ..i18n import Language
from ..model import Project
from .language import LanguageManager
from .main_window import MainWindow

ORGANIZATION = "pin-header-label-generator"


def run_gui(project_path: Path | None = None, language: Language | None = None) -> int:
    """Start the GUI, optionally opening ``project_path``.

    ``language`` overrides the language saved in the settings for this session.
    """
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(ORGANIZATION)

    languages = LanguageManager(app, QSettings(ORGANIZATION, "pinlabel"))
    languages.apply(language or languages.saved_language(), persist=language is None)

    existing = project_path is not None and project_path.exists()
    # a path that does not exist yet is used as file name for a new project
    window = MainWindow(Project(), None if existing else project_path, languages)
    if existing:
        window.open_path(project_path)
    window.show()
    return app.exec()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pinlabel-gui", description=APP_NAME)
    parser.add_argument("project", nargs="?", type=Path, help="project file (.json) to open")
    parser.add_argument("--lang", choices=[lang.value for lang in Language], help="user interface language")
    args = parser.parse_args(argv)
    return run_gui(args.project, Language(args.lang) if args.lang else None)


if __name__ == "__main__":
    sys.exit(main())
