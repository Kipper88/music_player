import json
from pathlib import Path
from typing import Dict, List


class PlaylistService:
    """Сервис локального хранения пользовательских плейлистов.

    Сейчас плейлисты сохраняются в JSON-файл рядом с приложением. Это простой и
    понятный формат, который удобно переносить и отлаживать вручную. Внутри
    каждого плейлиста лежат id треков из Subsonic/Navidrome.
    """

    def __init__(self, path: str = "playlists.json") -> None:
        self.path = Path(path)

    def load(self) -> Dict[str, List[str]]:
        """Загружает плейлисты и безопасно восстанавливает базовую структуру."""
        if not self.path.exists():
            return {"Favorites": []}

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"Favorites": []}

        if not isinstance(raw, dict):
            return {"Favorites": []}

        playlists: Dict[str, List[str]] = {}
        for name, track_ids in raw.items():
            if isinstance(name, str) and isinstance(track_ids, list):
                playlists[name] = [str(track_id) for track_id in track_ids]

        return playlists or {"Favorites": []}

    def save(self, data: Dict[str, List[str]]) -> None:
        """Сохраняет плейлисты с pretty-print, чтобы файл легко читался."""
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
