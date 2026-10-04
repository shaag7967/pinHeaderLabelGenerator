# Pin Header Label Generator

[![CI](https://github.com/shaag7967/pinHeaderLabelGenerator/actions/workflows/ci.yml/badge.svg)](https://github.com/shaag7967/pinHeaderLabelGenerator/actions/workflows/ci.yml)
[![License: GPL v3+](https://img.shields.io/badge/license-GPL--3.0--or--later-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.11%20%E2%80%93%203.14-blue.svg)

Print a pin-out label, push the pins of your pin header through the paper, and
every signal name sits right next to its pin. No more counting pins when you
plug in jumper wires.

<p align="center">
  <img src="https://raw.githubusercontent.com/shaag7967/pinHeaderLabelGenerator/main/docs/images/example_label.png" alt="Example label" width="380">
  &nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/shaag7967/pinHeaderLabelGenerator/main/docs/images/raspberry_pi_label.png" alt="Raspberry Pi GPIO label" width="300">
</p>

## Features

- Single-row and two-row pin headers with any number of rows and any pitch
  (2.54 mm, 2.0 mm, 1.27 mm, …)
- Labels fan out automatically with leader lines when the text is taller than
  the pin pitch
- Per-pin colors (typical jumper wire colors or any custom color), shown as
  background, text color or frame; GND/VCC can be colored automatically
- Optional pin numbers (zigzag, DIP/U shape, column by column), pin 1 mark,
  title, header outline and cutting frame
- Exact output: vector PDF in millimeters, PNG with DPI metadata, SVG, or
  direct printing; several copies per A4 page
- Check rulers on the page and a scale correction for printers that do not
  print at exactly 100 %
- **Pin list import** from text and CSV files, plus pasting from the
  clipboard or a spreadsheet
- Graphical user interface **in English and German** and a command line
  version for scripts and automation
- Projects are saved as human-readable JSON

## Installation

You need Python 3.11 or newer. The only dependency is
[PySide6](https://doc.qt.io/qtforpython/) (Qt for Python), which pip
installs automatically.

From PyPI (once published):

```bash
pip install pin-header-label-generator
```

Directly from GitHub:

```bash
pip install git+https://github.com/shaag7967/pinHeaderLabelGenerator.git
```

[pipx](https://pipx.pypa.io/) works too and keeps the tool in its own
environment: `pipx install pin-header-label-generator`.

The package provides two commands:

| Command        | Purpose                                         |
|----------------|-------------------------------------------------|
| `pinlabel-gui` | starts the graphical user interface             |
| `pinlabel`     | command line: `export`, `import` and `gui`      |

`python -m pin_header_label` is the same as `pinlabel`.

## Using the GUI

```bash
pinlabel-gui                      # new project
pinlabel-gui my_header.json       # open a project (or create it under this name)
pinlabel-gui --lang de            # German for this session
```

![Main window](https://raw.githubusercontent.com/shaag7967/pinHeaderLabelGenerator/main/docs/images/gui.png)

The window has three parts:

1. **Settings** (left): header size and pitch, font, label distance,
   leader lines, pin numbering, color display, marks, copies and printer
   scale.
2. **Pin table** (middle): one line per header row. Two-row headers are shown
   like the real header: `left label | color | color | right label`.
3. **Preview** (right): the label or the whole A4 page. Zoom with the mouse
   wheel, drag to pan, double-click to fit, and use *1:1* for roughly real
   size.

Editing the pin table:

| Action                        | How                                                     |
|-------------------------------|---------------------------------------------------------|
| Enter a label                 | type or double-click a label cell                        |
| Set a color                   | click a color cell (applies to all selected pins)       |
| Paste a list                  | `Ctrl+V` (lines become rows, tabs become columns)       |
| Copy labels                   | `Ctrl+C`                                                |
| Clear cells                   | `Del` / `Backspace`                                     |
| Insert / delete rows, colors  | right-click                                             |

**Language:** choose *Language → English / Deutsch*. The interface switches
immediately and the choice is remembered. The texts printed on the page
(instructions and footer) follow the selected language too.

### Printing

1. Print at **100 % / "Actual size"**, not "Fit to page".
2. Check the printed 50 mm ruler. If it is not exactly 50 mm, set
   *Scale X / Y* to `50 / measured × 100 %` (for example 50 / 49.5 × 100 % =
   101.01 %).
3. You can also check the pitch ruler: put the real header on it.
4. Cut the label out along the dashed cutting frame and push the pins
   through the crosses.

## Importing pin lists

There are three ways to get pin names into a project.

### 1. Paste into the table

Copy a column (or two columns) from a spreadsheet, a datasheet or a text
editor, click the start cell in the pin table and press `Ctrl+V`. Each line
becomes a row and tab characters separate the left and right side. Rows are
added when the list is longer than the header.

### 2. *Paste pin lists…* dialog

*Edit → Paste pin lists…* opens one text box per header side. Enter one pin
per line, from top to bottom. A blank line, `-` or `empty`/`leer` marks an
unused pin; bullets (`*`, `-`, `•`) at the start of a line are removed. The
number of rows can be adjusted to the longest list. Colors are kept.

### 3. Import a pin list file

*File → Import pin list…* (`Ctrl+I`) in the GUI, or on the command line:

```bash
pinlabel import pins.csv -o my_header.json
pinlabel export pins.csv --pdf my_header.pdf     # import and export in one step
```

An import **replaces all labels and colors** of the project and sets the
number of rows to fit the list. All other settings (font, pitch, …) stay as
they are. Three file formats are supported:

#### Text file (`.txt`): one label per line, in pin number order

```text
GND
CTS
VCC
TXD
RXD
RTS
```

Line 1 is pin 1, line 2 is pin 2, and so on. Use `-` for unused pins at the
end of the list, because trailing blank lines are ignored.

#### CSV by pin number (`pin`, `label`, optional `color`)

```csv
pin,label,color
1,3V3,orange
2,5V,red
3,GPIO2 SDA,blue
6,GND,black
```

Lines can be in any order and gaps are allowed. See
[`examples/raspberry_pi_gpio.csv`](examples/raspberry_pi_gpio.csv) for a
complete Raspberry Pi header.

#### CSV row by row (`left`, `right`, optional `left_color`, `right_color`)

```csv
left;left_color;right;right_color
VCC;red;GND;black
SDA;blue;SCL;blue
INT;yellow;RESET;
-;;LED;green
```

Each line is one header row, from top to bottom. This always makes a two-row
header. For a single-row header use a `label` column (and optionally
`color`) without a `pin` column.

#### How pin numbers are mapped to positions

Pin numbers (text files and `pin` columns) are placed with the pin
numbering selected in the project:

| Numbering                  | Two-row header with 3 rows        |
|----------------------------|-----------------------------------|
| zigzag, or none (default)  | `1 2` / `3 4` / `5 6`             |
| U shape / DIP              | `1 6` / `2 5` / `3 4`             |
| column by column           | `1 4` / `2 5` / `3 6`             |

Single-row headers are always numbered from top to bottom. On the command
line, choose the layout with `--cols` and `--numbering`, or take it from an
existing project with `--template`.

#### Details

- **Column names** are case-insensitive. Accepted names:
  `pin` (`no`, `nr`, `number`, `#`), `label` (`name`, `signal`, `function`,
  `net`), `color` (`colour`, `farbe`), `left`/`right` (`links`/`rechts`),
  `left_color`/`right_color`.
- **Without a header line**, a file whose first column contains pin numbers
  (`1`, `P1`, `Pin 1`) is read as `pin, label, color`. Otherwise every column
  is a list of labels: one column for a single-row header, two columns for
  left and right.
- **Colors** can be hex values (`#d32f2f`, `#f00`) or palette names in English
  or German: black, brown, red, orange, yellow, green, blue, violet, gray,
  white, light red, light yellow, light green, light blue (schwarz, braun, rot,
  …).
- **Separators** (`,` `;` or tab) are detected automatically, and `.tsv`
  files always use tabs. Files may be UTF-8 (with or without BOM) or
  Windows-1252, which Excel writes on German systems.
- Errors name the line number, for example
  `Line 5: unknown color 'plaid'.`

## Command line

```text
pinlabel [--lang {en,de}] [--version] COMMAND ...
```

### `pinlabel export`

Exports a project (`.json`) or a pin list (`.txt`, `.csv`, `.tsv`).

```bash
pinlabel export my_header.json --pdf my_header.pdf
pinlabel export my_header.json --png my_header.png --dpi 300
pinlabel export my_header.json --svg label.svg --label-only
pinlabel export pins.csv --template my_header.json --pdf pins.pdf
```

| Option              | Meaning                                                    |
|---------------------|------------------------------------------------------------|
| `--pdf FILE`        | write a PDF (A4, vector, exact millimeters)                |
| `--png FILE`        | write a PNG                                                |
| `--svg FILE`        | write an SVG (dimensions in mm)                            |
| `--dpi N`           | PNG resolution, default 600                                |
| `--label-only`      | PNG/SVG: only the label, without page decoration           |
| `--template PROJECT`| settings to use when the input is a pin list               |

The export also works on Linux machines without a display (servers, CI): Qt's
`offscreen` platform is selected automatically.

### `pinlabel import`

Creates a project file from a pin list.

```bash
pinlabel import pins.txt                          # writes pins.json
pinlabel import pins.txt --cols 1 --pitch 2.0 --title J3
pinlabel import pi.csv -o pi.json --numbering zigzag
pinlabel import pins.csv -o new.json --template old.json --force
```

| Option               | Meaning                                                 |
|----------------------|---------------------------------------------------------|
| `-o, --output FILE`  | project file to write (default: pin list name + `.json`)|
| `--template PROJECT` | take all settings from this project                     |
| `--cols {1,2}`       | pin rows of the header                                  |
| `--numbering ...`    | `none`, `zigzag`, `dip` or `column`                     |
| `--pitch MM`         | pin pitch in mm                                         |
| `--title TEXT`       | label title                                             |
| `-f, --force`        | overwrite an existing file                              |

### `pinlabel gui`

`pinlabel gui [PROJECT]` starts the GUI, just like `pinlabel-gui`.

Exit codes: `0` success, `1` error (message on stderr), `2` invalid
arguments.

## Project files

Projects are JSON files that you can edit or generate yourself:

```json
{
  "format_version": 1,
  "title": "J1",
  "rows": 4,
  "cols": 2,
  "pitch": 2.54,
  "font_family": "",
  "font_pt": 6.0,
  "numbering": "zigzag",
  "color_style": "fill",
  "pins": [
    [{"label": "VCC", "color": "#d32f2f"}, {"label": "GND", "color": "#1b1b1b"}],
    [{"label": "SDA", "color": ""}, {"label": "SCL", "color": ""}]
  ]
}
```

Missing settings get their default values and invalid values are corrected
when the file is loaded. `pins` holds one list per row with one entry per pin
column. The other settings are `side_mode` (`right`, `left`, `alternate`),
`bold`, `gap_mm`, `leaders` (`auto`, `always`), `pin1_marker`, `outline`,
`cut_frame`, `copies`, `scale_x`, `scale_y` and `scale_bar`.
[`examples/`](examples/) contains complete projects and pin lists.

## Development

```bash
git clone https://github.com/shaag7967/pinHeaderLabelGenerator.git
cd pinHeaderLabelGenerator
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

pytest                     # unit tests (Qt runs headless on Linux)
ruff check src tests       # lint
ruff format src tests      # format
```

Code layout:

```text
src/pin_header_label/
├── core/        colors, palette, label cleaning, GND/VCC auto colors (no Qt)
├── model/       Project, Pin, enums and pin numbering (no Qt)
├── layout/      label placement and page geometry in mm (no Qt)
├── importers/   pin list reader for .txt / .csv / .tsv (no Qt)
├── rendering/   Qt painting and export: PDF, PNG, SVG, printer
├── gui/         PySide6 widgets: main window, settings, pin table, preview
├── i18n/        translator and German catalog
└── cli.py       command line interface
```

Only `rendering/` and `gui/` use Qt. The layout algorithm measures text
through a small `TextMetrics` protocol, so tests can use predictable fake
font metrics.

**Translations:** UI strings are written in English and wrapped in `tr()`.
German translations live in `src/pin_header_label/i18n/catalog_de.py`. A
test fails if a string is missing from the catalog or its placeholders do not
match. To add a language, add it to `Language` and add a catalog.

## Publishing to PyPI

The workflow [`.github/workflows/publish.yml`](.github/workflows/publish.yml)
uses PyPI [Trusted Publishing](https://docs.pypi.org/trusted-publishers/),
so no API token has to be stored in GitHub.

One-time setup:

1. On [pypi.org](https://pypi.org/manage/account/publishing/) (and on
   [test.pypi.org](https://test.pypi.org/manage/account/publishing/)) add a
   *pending publisher*: project `pin-header-label-generator`, owner
   `shaag7967`, repository `pinHeaderLabelGenerator`, workflow `publish.yml`,
   environment `pypi` (or `testpypi`).
2. In the GitHub repository go to *Settings → Environments* and create the
   environments `pypi` and `testpypi`. Requiring a manual approval for
   `pypi` is a good idea.

Releasing a version:

1. Update `__version__` in `src/pin_header_label/__init__.py` and
   `CHANGELOG.md`.
2. Optional: *Actions → Publish → Run workflow* with target `testpypi`, then
   test with
   `pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ pin-header-label-generator`.
3. Create a GitHub release with the tag `v<version>` (for example `v0.1.0`).
   The workflow checks that the tag matches the package version, builds the
   sdist and wheel and uploads them to PyPI.

## License

Copyright © 2026 shaag7967

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version. See [LICENSE](LICENSE).

Everyone may use the tool freely, including for commercial work. If you
distribute modified versions, they must also be under the GPL with their
source code. The labels you create with the tool are yours: the license does
not apply to them.

## Acknowledgements

This project was developed with [Claude Code](https://claude.com/claude-code),
using Anthropic's Claude Opus 5.5 model.
