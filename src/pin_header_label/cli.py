"""Command line interface (``pinlabel``)."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from . import APP_NAME, __version__
from .i18n import Language, set_language, tr
from .importers import PinListFormatError, PinListReader
from .importers.pin_list import SUPPORTED_SUFFIXES
from .model import Numbering, Project, ProjectFormatError


class CliError(Exception):
    """An error reported to the user without a traceback."""


def ensure_qt_application() -> object:
    """Create the QGuiApplication needed for fonts and painting.

    On Linux machines without a display the offscreen platform is used, so the
    export also works on servers and in CI.
    """
    if sys.platform.startswith("linux") and not (
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    ):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    return QGuiApplication.instance() or QGuiApplication(["pinlabel"])


def load_project(path: Path, template: Path | None = None) -> Project:
    """Load a project file, or build a project from a pin list file.

    Pin lists are applied to ``template`` (or to the default settings).
    """
    try:
        if path.suffix.lower() == ".json":
            return Project.load(path)
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            raise CliError(tr("Unsupported file type: {path}", path=path))
        project = Project.load(template) if template else Project()
        PinListReader().read(path).apply_to(project)
        return project
    except (OSError, ProjectFormatError, PinListFormatError) as exc:
        raise CliError(f"{path}: {exc}") from exc


def _language_from_argv(argv: Sequence[str]) -> Language | None:
    """Find ``--lang`` before the parser is built, so help texts can be translated."""
    for i, arg in enumerate(argv):
        if arg == "--lang" and i + 1 < len(argv):
            return Language.from_code(argv[i + 1])
        if arg.startswith("--lang="):
            return Language.from_code(arg.split("=", 1)[1])
    return None


class CommandLineInterface:
    """Parses arguments and runs the ``export``, ``import`` and ``gui`` commands."""

    def __init__(self, stdout: TextIO | None = None, stderr: TextIO | None = None) -> None:
        self.stdout = stdout or sys.stdout
        self.stderr = stderr or sys.stderr

    def build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="pinlabel",
            description=tr("{app} - printable pin-out labels for pin headers.", app=APP_NAME),
        )
        parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
        parser.add_argument(
            "--lang",
            choices=[lang.value for lang in Language],
            help=tr("language of messages and page texts (default: system language)"),
        )
        sub = parser.add_subparsers(dest="command", metavar="COMMAND")

        export = sub.add_parser("export", help=tr("export a project or pin list to PDF, PNG and/or SVG"))
        export.add_argument(
            "input", type=Path, help=tr("project file (.json) or pin list (.txt, .csv, .tsv)")
        )
        export.add_argument("--pdf", type=Path, metavar="FILE", help=tr("write a PDF file"))
        export.add_argument("--png", type=Path, metavar="FILE", help=tr("write a PNG file"))
        export.add_argument("--svg", type=Path, metavar="FILE", help=tr("write an SVG file"))
        export.add_argument("--dpi", type=int, default=600, help=tr("PNG resolution (default: 600)"))
        export.add_argument(
            "--label-only", action="store_true", help=tr("PNG/SVG: only the label, without the A4 page")
        )
        export.add_argument(
            "--template", type=Path, metavar="PROJECT", help=tr("settings for a pin list input (.json)")
        )
        export.set_defaults(handler=self._export)

        imp = sub.add_parser("import", help=tr("create a project file from a pin list"))
        imp.add_argument("pin_list", type=Path, help=tr("pin list (.txt, .csv, .tsv)"))
        imp.add_argument(
            "-o", "--output", type=Path, help=tr("project file to write (default: pin list name with .json)")
        )
        imp.add_argument(
            "--template", type=Path, metavar="PROJECT", help=tr("take all settings from this project")
        )
        imp.add_argument("--cols", type=int, choices=(1, 2), help=tr("pin rows of the header (1 or 2)"))
        imp.add_argument(
            "--numbering",
            choices=[n.value for n in Numbering],
            help=tr("pin numbering scheme used to place numbered pins"),
        )
        imp.add_argument("--pitch", type=float, help=tr("pin pitch in mm"))
        imp.add_argument("--title", help=tr("label title"))
        imp.add_argument("-f", "--force", action="store_true", help=tr("overwrite an existing project file"))
        imp.set_defaults(handler=self._import)

        gui = sub.add_parser("gui", help=tr("start the graphical user interface"))
        gui.add_argument("project", nargs="?", type=Path, help=tr("project file to open"))
        gui.set_defaults(handler=self._gui)
        return parser

    def run(self, argv: Sequence[str] | None = None) -> int:
        argv = list(sys.argv[1:] if argv is None else argv)
        set_language(_language_from_argv(argv) or Language.system_default())
        parser = self.build_parser()
        args = parser.parse_args(argv)
        if not getattr(args, "handler", None):
            parser.print_help(self.stdout)
            return 0
        try:
            return args.handler(args)
        except CliError as exc:
            print(tr("error: {message}", message=exc), file=self.stderr)
            return 1

    # -- commands -----------------------------------------------------------
    def _export(self, args: argparse.Namespace) -> int:
        if not (args.pdf or args.png or args.svg):
            raise CliError(tr("Nothing to do: give at least one of --pdf, --png or --svg."))
        project = load_project(args.input, args.template)
        ensure_qt_application()
        from .rendering import Exporter

        exporter = Exporter(project)
        jobs = [
            (args.pdf, lambda path: exporter.export_pdf(path)),
            (args.png, lambda path: exporter.export_png(path, args.dpi, args.label_only)),
            (args.svg, lambda path: exporter.export_svg(path, args.label_only)),
        ]
        for path, export in jobs:
            if not path:
                continue
            try:
                result = export(path)
            except OSError as exc:
                raise CliError(str(exc)) from exc
            print(tr("Written: {path}", path=path), file=self.stdout)
            if not result.complete:
                print(
                    tr(
                        "Warning: only {placed} of {requested} copies fit on A4.",
                        placed=result.copies_placed,
                        requested=result.copies_requested,
                    ),
                    file=self.stderr,
                )
        return 0

    def _import(self, args: argparse.Namespace) -> int:
        output: Path = args.output or args.pin_list.with_suffix(".json")
        if output.exists() and not args.force:
            raise CliError(tr("{path} exists already (use --force to overwrite).", path=output))
        try:
            project = Project.load(args.template) if args.template else Project()
        except (OSError, ProjectFormatError) as exc:
            raise CliError(f"{args.template}: {exc}") from exc
        if args.cols:
            project.cols = args.cols
        if args.numbering:
            project.numbering = Numbering(args.numbering)
        if args.pitch:
            project.pitch = args.pitch
        if args.title is not None:
            project.title = args.title
        project.normalize()
        try:
            PinListReader().read(args.pin_list).apply_to(project)
            project.save(output)
        except (OSError, PinListFormatError) as exc:
            raise CliError(f"{args.pin_list}: {exc}") from exc
        print(
            tr(
                "Written: {path} ({labels} labels, {cols}×{rows} pins)",
                path=output,
                labels=project.label_count,
                cols=project.cols,
                rows=project.rows,
            ),
            file=self.stdout,
        )
        return 0

    def _gui(self, args: argparse.Namespace) -> int:
        from .gui.app import run_gui

        return run_gui(args.project, Language(args.lang) if args.lang else None)


def main(argv: Sequence[str] | None = None) -> int:
    return CommandLineInterface().run(argv)
