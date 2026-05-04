import json
from pathlib import Path
from typing import Dict, List


class PlaylistService:
    def __init__(self, path: str = "playlists.json") -> None:
        self.path = Path(path)

    def load(self) -> Dict[str, List[str]]:
        if not self.path.exists():
            return {"Favorites": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, data: Dict[str, List[str]]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
