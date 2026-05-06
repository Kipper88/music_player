from PySide6.QtCore import QSettings


class SettingsService:
    def __init__(self) -> None:
        self._settings = QSettings("Kipper88", "MusicPlayer")

    def get(self, key: str, default=None):
        return self._settings.value(key, default)

    def set(self, key: str, value) -> None:
        self._settings.setValue(key, value)

    def sync(self) -> None:
        self._settings.sync()
