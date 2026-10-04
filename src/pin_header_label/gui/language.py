"""User interface language selection (persisted in QSettings)."""

from __future__ import annotations

from PySide6.QtCore import QLibraryInfo, QLocale, QObject, QSettings, QTranslator, Signal
from PySide6.QtWidgets import QApplication

from ..i18n import Language, set_language


class LanguageManager(QObject):
    """Switches the application language, including Qt's own dialogs and buttons."""

    language_changed = Signal(object)  # Language

    SETTINGS_KEY = "ui/language"

    def __init__(self, app: QApplication, settings: QSettings) -> None:
        super().__init__(app)
        self._app = app
        self._settings = settings
        self._qt_translator: QTranslator | None = None
        self._language = Language.ENGLISH

    @property
    def language(self) -> Language:
        return self._language

    def saved_language(self) -> Language:
        """Language stored in the settings, else the system language."""
        system = Language.from_code(QLocale.system().name())
        return Language.from_code(str(self._settings.value(self.SETTINGS_KEY, "")), default=system)

    def apply(self, language: Language, persist: bool = True) -> None:
        self._language = language
        set_language(language)
        QLocale.setDefault(QLocale(language.value))  # number format of spin boxes
        self._install_qt_translations(language)
        if persist:
            self._settings.setValue(self.SETTINGS_KEY, language.value)
        self.language_changed.emit(language)

    def _install_qt_translations(self, language: Language) -> None:
        if self._qt_translator is not None:
            self._app.removeTranslator(self._qt_translator)
            self._qt_translator = None
        if language == Language.ENGLISH:
            return
        translator = QTranslator(self)
        path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        if translator.load(f"qtbase_{language.value}", path):
            self._app.installTranslator(translator)
            self._qt_translator = translator
