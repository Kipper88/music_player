from collections import Counter
from typing import List

from app.models.entities import Track


class RecommendationService:
    """Простая рекомендательная логика на основе частоты прослушиваний по артисту."""

    def __init__(self) -> None:
        self.artist_counter: Counter[str] = Counter()

    def register_play(self, track: Track) -> None:
        self.artist_counter[track.artist] += 1

    def recommend(self, tracks: List[Track], limit: int = 20) -> List[Track]:
        if not tracks:
            return []
        # Чем чаще слушали артиста, тем выше трек в выдаче.
        scored = sorted(tracks, key=lambda t: self.artist_counter[t.artist], reverse=True)
        return scored[:limit]
