"""Lightweight translation support.

Source strings are written in English and looked up in per-language catalogs at
runtime. Placeholders use :meth:`str.format` syntax and are filled in after the
lookup, so a translation may reorder them freely.
"""

from .translator import Language, Translator, format_number, get_translator, set_language, tr

__all__ = ["Language", "Translator", "format_number", "get_translator", "set_language", "tr"]
