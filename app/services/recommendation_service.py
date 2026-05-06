import json
from collections import Counter
from pathlib import Path
from typing import List

from app.models.entities import Track


class RecommendationService:
    """Рекомендации на основе истории прослушиваний.

    Логика специально простая и предсказуемая: чем чаще пользователь слушает
    артиста, тем выше треки этого артиста поднимаются в разделе рекомендаций.
    Счётчик сохраняется на диск, поэтому рекомендации не сбрасываются после
    перезапуска приложения.
    """

    def __init__(self, path: str = "listening_history.json") -> None:
        self.path = Path(path)
        self.artist_counter: Counter[str] = Counter()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return

        if isinstance(raw, dict):
            self.artist_counter.update(
                {str(artist): int(count) for artist, count in raw.items()}
            )

    def _save(self) -> None:
        self.path.write_text(
            json.dumps(dict(self.artist_counter), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def register_play(self, track: Track) -> None:
        """Фиксирует прослушивание и сразу сохраняет историю."""
        self.artist_counter[track.artist] += 1
        self._save()

    def recommend(self, tracks: List[Track], limit: int = 20) -> List[Track]:
        """Возвращает треки, отсортированные по похожести на историю слушателя."""
        if not tracks:
            return []

        scored = sorted(
            tracks,
            key=lambda track: (
                self.artist_counter[track.artist],
                track.artist.lower(),
                track.title.lower(),
            ),
            reverse=True,
        )
        return scored[:limit]
