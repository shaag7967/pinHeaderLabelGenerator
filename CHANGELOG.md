# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/) and the
project uses [Semantic Versioning](https://semver.org/).

## [0.1.0] - unreleased

First packaged release, refactored from the original single-file script.

### Added
- Installable Python package with two commands: `pinlabel` (command line) and
  `pinlabel-gui` (graphical user interface).
- English and German user interface, selectable in the *Language* menu.
- Import of pin lists from `.txt`, `.csv` and `.tsv` files (GUI and CLI),
  by pin number or row by row, with optional colors.
- `pinlabel import` creates a project file from a pin list.
- `pinlabel export --label-only` writes PNG/SVG files of the label alone.
- Unit tests, GitHub Actions for CI and for publishing to PyPI.

### Changed
- Code split into packages (model, layout, rendering, importers, GUI, CLI);
  the layout algorithm no longer depends on Qt.
- Project files get a `format_version` field; older files still load.
