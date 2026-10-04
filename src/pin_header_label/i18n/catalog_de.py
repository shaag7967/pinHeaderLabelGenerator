"""German translations (English source text -> German).

Placeholders in braces must be kept unchanged; ``&`` marks menu accelerators
and ``&&`` a literal ampersand in group box titles.
"""

GERMAN: dict[str, str] = {
    # -- palette colors --------------------------------------------------------
    "Black": "Schwarz",
    "Brown": "Braun",
    "Red": "Rot",
    "Orange": "Orange",
    "Yellow": "Gelb",
    "Green": "Grün",
    "Blue": "Blau",
    "Violet": "Violett",
    "Gray": "Grau",
    "White": "Weiß",
    "Light red": "Hellrot",
    "Light yellow": "Hellgelb",
    "Light green": "Hellgrün",
    "Light blue": "Hellblau",
    # -- page texts ------------------------------------------------------------
    "Pin label": "Pin-Label",
    "Print at 100 % or “Actual size” – not “Fit to page”.  Push the header pins through the crosses.": (
        "Mit 100 % bzw. „Tatsächliche Größe“ drucken – nicht „An Seite anpassen“.  "
        "Header-Pins durch die Kreuze stechen."
    ),
    "{cols}×{rows} pins · pitch {pitch} mm · font {size} pt": (
        "{cols}×{rows} Pins · Raster {pitch} mm · Schrift {size} pt"
    ),
    "{n} × {pitch} mm = {length} mm (pitch)": "{n} × {pitch} mm = {length} mm (Raster)",
    " · correction X {x} % / Y {y} %": " · Korrektur X {x} % / Y {y} %",
    "Could not save PNG file: {path}": "PNG konnte nicht gespeichert werden: {path}",
    # -- pin list import -------------------------------------------------------
    "The pin list has no label column.": "Die Pinliste hat keine Label-Spalte.",
    "Too many pins: at most {n} rows are supported.": "Zu viele Pins: höchstens {n} Reihen sind möglich.",
    "The pin list contains no labels.": "Die Pinliste enthält keine Labels.",
    "A 'pin' column needs a 'label' column.": "Zu einer Spalte „pin“ gehört eine Spalte „label“.",
    "Line {line}: invalid pin number {value!r}.": "Zeile {line}: ungültige Pinnummer {value!r}.",
    "Line {line}: pin {n} appears twice.": "Zeile {line}: Pin {n} kommt doppelt vor.",
    "Line {line}: unknown color {value!r}.": "Zeile {line}: unbekannte Farbe {value!r}.",
    "Line {line}: pin number missing.": "Zeile {line}: Pinnummer fehlt.",
    # -- command line ----------------------------------------------------------
    "{app} - printable pin-out labels for pin headers.": "{app} – druckbare Pinbelegungs-Labels für Stiftleisten.",
    "language of messages and page texts (default: system language)": (
        "Sprache für Meldungen und Seitentexte (Standard: Systemsprache)"
    ),
    "export a project or pin list to PDF, PNG and/or SVG": (
        "Projekt oder Pinliste als PDF, PNG und/oder SVG exportieren"
    ),
    "project file (.json) or pin list (.txt, .csv, .tsv)": "Projektdatei (.json) oder Pinliste (.txt, .csv, .tsv)",
    "write a PDF file": "PDF-Datei schreiben",
    "write a PNG file": "PNG-Datei schreiben",
    "write an SVG file": "SVG-Datei schreiben",
    "PNG resolution (default: 600)": "Auflösung für PNG (Standard: 600)",
    "PNG/SVG: only the label, without the A4 page": "PNG/SVG: nur das Etikett, ohne A4-Seite",
    "settings for a pin list input (.json)": "Einstellungen für eine Pinliste als Eingabe (.json)",
    "create a project file from a pin list": "Projektdatei aus einer Pinliste erzeugen",
    "pin list (.txt, .csv, .tsv)": "Pinliste (.txt, .csv, .tsv)",
    "project file to write (default: pin list name with .json)": (
        "zu schreibende Projektdatei (Standard: Name der Pinliste mit .json)"
    ),
    "take all settings from this project": "alle Einstellungen aus diesem Projekt übernehmen",
    "pin rows of the header (1 or 2)": "Pin-Reihen des Headers (1 oder 2)",
    "pin numbering scheme used to place numbered pins": "Pinnummerierung zum Platzieren nummerierter Pins",
    "pin pitch in mm": "Rastermaß in mm",
    "label title": "Titel des Etiketts",
    "overwrite an existing project file": "vorhandene Projektdatei überschreiben",
    "start the graphical user interface": "grafische Oberfläche starten",
    "project file to open": "zu öffnende Projektdatei",
    "Nothing to do: give at least one of --pdf, --png or --svg.": (
        "Nichts zu tun: mindestens eine der Optionen --pdf, --png oder --svg angeben."
    ),
    "Written: {path}": "Geschrieben: {path}",
    "Written: {path} ({labels} labels, {cols}×{rows} pins)": "Geschrieben: {path} ({labels} Labels, {cols}×{rows} Pins)",
    "Unsupported file type: {path}": "Nicht unterstützter Dateityp: {path}",
    "{path} exists already (use --force to overwrite).": "{path} existiert bereits (--force zum Überschreiben).",
    "error: {message}": "Fehler: {message}",
    "Warning: only {placed} of {requested} copies fit on A4.": (
        "Warnung: nur {placed} von {requested} Kopien passen auf A4."
    ),
    # -- main window -----------------------------------------------------------
    "Type/double-click: text · click a color cell: color · Ctrl+V: paste list · Del: clear · right-click: more": (
        "Tippen/Doppelklick: Text · Farbzelle anklicken: Farbe · "
        "Strg+V: Liste einfügen · Entf: leeren · Rechtsklick: mehr"
    ),
    "Label sheet": "Etikett",
    "Label": "Label",
    "Whole page (A4)": "Ganze Seite (A4)",
    "Fit": "Einpassen",
    "Approximately real size on screen": "Ungefähr echte Größe auf dem Bildschirm",
    "Preview:": "Vorschau:",
    "New": "Neu",
    "Open…": "Öffnen…",
    "Save": "Speichern",
    "Save as…": "Speichern unter…",
    "Import pin list…": "Pinliste importieren…",
    "Export PDF…": "PDF exportieren…",
    "Export PNG…": "PNG exportieren…",
    "Export SVG…": "SVG exportieren…",
    "Print preview…": "Druckvorschau…",
    "Print…": "Drucken…",
    "Quit": "Beenden",
    "&File": "&Datei",
    "&Edit": "&Bearbeiten",
    "&Language": "&Sprache",
    "&Help": "&Hilfe",
    "About…": "Über…",
    "Tools": "Werkzeuge",
    "Untitled": "Unbenannt",
    "{n} labels": "{n} Labels",
    "{n} shifted (leader lines)": "{n} versetzt (Führungslinien)",
    "label {w} × {h} mm": "Etikett {w} × {h} mm",
    "Note: only {placed} of {requested} copies fit on A4": "Achtung: nur {placed} von {requested} Kopien passen auf A4",
    "Paste pin lists…": "Pinlisten einfügen…",
    "Color GND/VCC automatically": "GND/VCC automatisch färben",
    "Remove all colors": "Alle Farben entfernen",
    "Clear all labels": "Alle Labels leeren",
    "Delete all labels and colors?": "Alle Labels und Farben löschen?",
    "Import pin list": "Pinliste importieren",
    "Pin lists": "Pinlisten",
    "Imported {n} labels from {path}": "{n} Labels importiert aus {path}",
    "Could not import the pin list:\n{error}": "Pinliste konnte nicht importiert werden:\n{error}",
    "Replace all labels and colors with the pin list?": "Alle Labels und Farben durch die Pinliste ersetzen?",
    "Unsaved changes": "Ungespeicherte Änderungen",
    "Save changes?": "Änderungen speichern?",
    "Open project": "Projekt öffnen",
    "Save project": "Projekt speichern",
    "Pin label project": "Pin-Label-Projekt",
    "Saved: {path}": "Gespeichert: {path}",
    "Error": "Fehler",
    "Could not load the file:\n{error}": "Datei konnte nicht geladen werden:\n{error}",
    "Saving failed:\n{error}": "Speichern fehlgeschlagen:\n{error}",
    "Export failed:\n{error}": "Export fehlgeschlagen:\n{error}",
    "Export PDF": "PDF exportieren",
    "Export PNG": "PNG exportieren",
    "Export SVG": "SVG exportieren",
    "Resolution:": "Auflösung:",
    "Exported: {path}": "Exportiert: {path}",
    "(only {placed} of {requested} copies fit on A4)": "(nur {placed} von {requested} Kopien passen auf A4)",
    "About {app}": "Über {app}",
    (
        "<h3>{app} {version}</h3>"
        "<p>Printable pin-out labels for pin headers.</p>"
        "<p>License: GNU GPL v3 or later<br>"
        '<a href="https://github.com/shaag7967/pinHeaderLabelGenerator">'
        "github.com/shaag7967/pinHeaderLabelGenerator</a></p>"
    ): (
        "<h3>{app} {version}</h3>"
        "<p>Druckbare Pinbelegungs-Labels für Stiftleisten.</p>"
        "<p>Lizenz: GNU GPL v3 oder neuer<br>"
        '<a href="https://github.com/shaag7967/pinHeaderLabelGenerator">'
        "github.com/shaag7967/pinHeaderLabelGenerator</a></p>"
    ),
    # -- pin table -------------------------------------------------------------
    "Left side": "Linke Seite",
    "Right side": "Rechte Seite",
    "Color": "Farbe",
    "Color for selection": "Farbe für Auswahl",
    "Clear selected cells": "Auswahl leeren",
    "Insert row above": "Reihe darüber einfügen",
    "Insert row below": "Reihe darunter einfügen",
    "Delete row": "Reihe löschen",
    "No color": "Keine Farbe",
    "Other color…": "Andere Farbe…",
    "Choose color": "Farbe wählen",
    # -- paste dialog ----------------------------------------------------------
    "Paste pin lists": "Pinlisten einfügen",
    "One line per pin, from top to bottom. “-”, “empty” or a blank line = unused.\n"
    "Bullets (*, -, •) at the start of a line are removed.": (
        "Eine Zeile pro Pin, von oben nach unten. „-“, „leer“ oder eine leere Zeile = nicht belegt.\n"
        "Aufzählungszeichen (*, -, •) am Zeilenanfang werden entfernt."
    ),
    "Pins": "Pins",
    "Set number of rows to the longest list": "Anzahl Reihen an die längste Liste anpassen",
    # -- settings panel --------------------------------------------------------
    "Pin header": "Pin-Header",
    "Title:": "Titel:",
    "optional, e.g. J1": "optional, z. B. J1",
    "Rows (pins per column):": "Reihen (Pins pro Spalte):",
    "Type:": "Bauform:",
    "2 rows (double row)": "2-reihig (Doppelreihe)",
    "1 row": "1-reihig",
    "Labels (1 row):": "Labels (1-reihig):",
    "right": "rechts",
    "left": "links",
    "alternating": "abwechselnd",
    "Pitch:": "Rastermaß:",
    "Font && labels": "Schrift && Labels",
    "Font:": "Schriftart:",
    "Font size:": "Schriftgröße:",
    "bold": "fett",
    "Distance to header:": "Abstand zum Header:",
    "Leader lines:": "Führungslinien:",
    "only when needed": "nur wenn nötig",
    "always": "immer",
    "Pin numbers:": "Pinnummern:",
    "none": "keine",
    "zigzag (1|2, 3|4 …)": "Zickzack (1|2, 3|4 …)",
    "U shape / DIP": "U-Form / DIP",
    "column by column": "spaltenweise",
    "Colors && marks": "Farben && Markierungen",
    "Color display:": "Farbdarstellung:",
    "colored background": "farbiger Hintergrund",
    "colored text": "farbige Schrift",
    "colored frame": "farbiger Rahmen",
    "Pin 1 mark (▼ top left)": "Pin-1-Markierung (▼ oben links)",
    "Header outline": "Header-Umriss",
    "Cutting frame": "Schnittrahmen",
    "Page && print (A4)": "Seite && Druck (A4)",
    "Copies:": "Kopien:",
    "Scale X:": "Skalierung X:",
    "Scale Y:": "Skalierung Y:",
    "Check ruler on the page": "Prüf-Lineal auf der Seite",
    "Only change the scale if the printed 50 mm ruler does not measure exactly "
    "50 mm (correction = 50 / measured × 100 %).": (
        "Skalierung nur ändern, wenn das gedruckte 50-mm-Lineal nicht genau 50 mm misst "
        "(Korrektur = 50 / gemessen × 100 %)."
    ),
}
