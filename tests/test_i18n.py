"""Translations: language detection, number format and catalog completeness."""

import ast
import re
import string
from pathlib import Path

import pytest

from pin_header_label.core.palette import JUMPER_PALETTE
from pin_header_label.i18n import Language, Translator, format_number, get_translator, set_language, tr
from pin_header_label.i18n.catalog_de import GERMAN

SOURCE_DIR = Path(__file__).resolve().parent.parent / "src" / "pin_header_label"


def translatable_strings() -> set[str]:
    """All string literals passed as first argument to ``tr()`` / ``.tr()`` in the sources."""
    found: set[str] = set()
    for path in SOURCE_DIR.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not (isinstance(node, ast.Call) and node.args):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            first = node.args[0]
            if name == "tr" and isinstance(first, ast.Constant) and isinstance(first.value, str):
                found.add(first.value)
    return found


def placeholders(text: str) -> set[str]:
    return {field for _, field, _, _ in string.Formatter().parse(text) if field is not None}


class TestLanguage:
    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            ("de", Language.GERMAN),
            ("de_DE.UTF-8", Language.GERMAN),
            ("de-AT", Language.GERMAN),
            ("de:en", Language.GERMAN),
            ("en_US", Language.ENGLISH),
            ("fr_FR", Language.ENGLISH),
            ("", Language.ENGLISH),
            (None, Language.ENGLISH),
        ],
    )
    def test_from_code(self, code, expected):
        assert Language.from_code(code) == expected

    def test_from_code_custom_default(self):
        assert Language.from_code("xx", default=Language.GERMAN) == Language.GERMAN

    @pytest.mark.parametrize(
        ("env", "expected"),
        [
            ({"LANG": "de_DE.UTF-8"}, Language.GERMAN),
            ({"LC_ALL": "en_GB.UTF-8", "LANG": "de_DE"}, Language.ENGLISH),
        ],
    )
    def test_system_default(self, monkeypatch, env, expected):
        for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
            monkeypatch.delenv(var, raising=False)
        for var, value in env.items():
            monkeypatch.setenv(var, value)
        assert Language.system_default() == expected

    def test_native_names(self):
        assert [lang.native_name for lang in Language] == ["English", "Deutsch"]


class TestTranslator:
    def test_english_is_identity(self):
        assert Translator(Language.ENGLISH).tr("Save") == "Save"

    def test_german(self):
        assert Translator(Language.GERMAN).tr("Save") == "Speichern"

    def test_placeholders_are_filled_after_lookup(self):
        assert Translator(Language.GERMAN).tr("{n} labels", n=3) == "3 Labels"

    def test_unknown_text_falls_back_to_source(self):
        assert Translator(Language.GERMAN).tr("no such text") == "no such text"

    def test_global_translator(self):
        set_language(Language.GERMAN)
        assert get_translator().language == Language.GERMAN
        assert tr("Quit") == "Beenden"

    @pytest.mark.parametrize(
        ("value", "decimals", "trim", "expected"),
        [(2.54, 2, True, "2.54"), (38.10, 2, True, "38.1"), (100.0, 2, True, "100"), (9.0, 1, False, "9.0")],
    )
    def test_format_number(self, value, decimals, trim, expected):
        assert format_number(value, decimals, trim) == expected

    def test_german_decimal_separator(self):
        assert Translator(Language.GERMAN).format_number(2.54) == "2,54"
        assert Translator(Language.ENGLISH).format_number(2.54) == "2.54"


class TestGermanCatalog:
    def test_every_ui_string_is_translated(self):
        missing = sorted(translatable_strings() - GERMAN.keys())
        assert missing == []

    def test_palette_names_are_translated(self):
        assert all(color.name in GERMAN for color in JUMPER_PALETTE)

    def test_no_unused_entries(self):
        used = translatable_strings() | {color.name for color in JUMPER_PALETTE}
        assert sorted(GERMAN.keys() - used) == []

    @pytest.mark.parametrize("source", sorted(GERMAN))
    def test_placeholders_match(self, source):
        assert placeholders(GERMAN[source]) == placeholders(source)

    @pytest.mark.parametrize("source", sorted(GERMAN))
    def test_accelerators_and_ampersands_match(self, source):
        assert source.count("&&") == GERMAN[source].count("&&")
        assert bool(re.match(r"^&\w", source)) == bool(re.match(r"^&\w", GERMAN[source]))
