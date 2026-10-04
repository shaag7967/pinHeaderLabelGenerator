"""Translator and language selection."""

from __future__ import annotations

import locale
import os
from enum import StrEnum

from .catalog_de import GERMAN


class Language(StrEnum):
    """Supported user interface languages (value = ISO 639-1 code)."""

    ENGLISH = "en"
    GERMAN = "de"

    @property
    def native_name(self) -> str:
        """Name of the language in the language itself (for menus)."""
        return _NATIVE_NAMES[self]

    @classmethod
    def from_code(cls, code: str | None, default: Language | None = None) -> Language:
        """Map a locale-like code (``de``, ``de_DE.UTF-8``, ``en-US``) to a language."""
        fallback = default if default is not None else cls.ENGLISH
        if not code:
            return fallback
        prefix = code.strip().lower().replace("-", "_").split(":")[0].split("_")[0].split(".")[0]
        for language in cls:
            if language.value == prefix:
                return language
        return fallback

    @classmethod
    def system_default(cls) -> Language:
        """Best guess of the user's preferred language from the environment."""
        for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
            value = os.environ.get(var)
            if value and value not in ("C", "POSIX") and not value.startswith("C."):
                return cls.from_code(value)
        try:
            return cls.from_code(locale.getlocale()[0])
        except ValueError:
            return cls.ENGLISH


_NATIVE_NAMES = {Language.ENGLISH: "English", Language.GERMAN: "Deutsch"}
_CATALOGS: dict[Language, dict[str, str]] = {Language.ENGLISH: {}, Language.GERMAN: GERMAN}
_DECIMAL_SEPARATORS = {Language.ENGLISH: ".", Language.GERMAN: ","}


def format_number(
    value: float, decimals: int = 2, trim_zeros: bool = True, decimal_separator: str = "."
) -> str:
    """Format a number with a fixed number of decimals.

    With ``trim_zeros`` trailing zeros (and a trailing separator) are removed,
    e.g. ``2.50 -> 2.5`` and ``100.00 -> 100``.
    """
    text = f"{value:.{decimals}f}"
    if trim_zeros and "." in text:
        text = text.rstrip("0").rstrip(".")
    return text.replace(".", decimal_separator)


class Translator:
    """Translates English source strings into the selected language."""

    def __init__(self, language: Language = Language.ENGLISH) -> None:
        self.language = language

    @property
    def language(self) -> Language:
        return self._language

    @language.setter
    def language(self, language: Language) -> None:
        self._language = Language(language)
        self._catalog = _CATALOGS[self._language]

    @property
    def decimal_separator(self) -> str:
        return _DECIMAL_SEPARATORS[self._language]

    def tr(self, text: str, /, **kwargs: object) -> str:
        """Return the translation of ``text``, with ``kwargs`` formatted in."""
        translated = self._catalog.get(text, text)
        return translated.format(**kwargs) if kwargs else translated

    def format_number(self, value: float, decimals: int = 2, trim_zeros: bool = True) -> str:
        """Format a number using the language's decimal separator."""
        return format_number(value, decimals, trim_zeros, self.decimal_separator)


_translator = Translator()


def get_translator() -> Translator:
    """The application-wide translator used by :func:`tr`."""
    return _translator


def set_language(language: Language) -> None:
    """Switch the application-wide language."""
    _translator.language = language


def tr(text: str, /, **kwargs: object) -> str:
    """Translate ``text`` with the application-wide translator."""
    return _translator.tr(text, **kwargs)
