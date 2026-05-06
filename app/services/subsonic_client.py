import hashlib
import secrets
from typing import List
from urllib.parse import urlencode, urljoin

import requests

from app.models.entities import ServerConfig, Track


class SubsonicClient:
    """Клиент для Navidrome/Subsonic-совместимых API."""

    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self.session = requests.Session()

    def _auth_params(self) -> dict:
        salt = secrets.token_hex(8)
        token = hashlib.md5((self.config.password + salt).encode("utf-8")).hexdigest()
        return {
            "u": self.config.username,
            "t": token,
            "s": salt,
            "v": self.config.api_version,
            "c": self.config.client_name,
            "f": "json",
        }

    def _url(self, endpoint: str) -> str:
        return urljoin(self.config.base_url.rstrip("/") + "/", endpoint.lstrip("/"))

    def _get(self, endpoint: str, **params):
        url = self._url(endpoint)
        merged = {**self._auth_params(), **params}
        response = self.session.get(url, params=merged, timeout=20)
        response.raise_for_status()
        data = response.json()
        container = data.get("subsonic-response", {})
        if container.get("status") != "ok":
            raise RuntimeError(container.get("error", {}).get("message", "Unknown API error"))
        return container

    def ping(self) -> bool:
        self._get("rest/ping.view")
        return True

    def _parse_songs(self, songs) -> List[Track]:
        """Преобразует ответ Subsonic song в список Track.

        Subsonic-серверы иногда возвращают одиночный объект вместо массива,
        поэтому нормализуем оба варианта в единый список.
        """
        if isinstance(songs, dict):
            songs = [songs]
        if not isinstance(songs, list):
            return []

        tracks: List[Track] = []
        for song in songs:
            tracks.append(
                Track(
                    id=str(song.get("id", "")),
                    title=song.get("title", "Unknown"),
                    artist=song.get("artist", "Unknown Artist"),
                    album=song.get("album", "Unknown Album"),
                    duration=int(song.get("duration", 0) or 0),
                    cover_art=str(song.get("coverArt", "")),
                )
            )
        return tracks

    def search_tracks(self, query: str = "", count: int = 100, offset: int = 0) -> List[Track]:
        """Загружает треки через search3 с пагинацией.

        В Navidrome/Subsonic это более подходящий способ получать библиотеку
        порциями, чем getRandomSongs: random часто ограничивается сервером
        примерно 20 элементами, из-за чего UI выглядел так, будто треки
        "закончились".
        """
        container = self._get(
            "rest/search3.view",
            query=query,
            songCount=count,
            songOffset=offset,
            artistCount=0,
            albumCount=0,
        )
        songs = container.get("searchResult3", {}).get("song", [])
        return self._parse_songs(songs)

    def get_tracks(self, size: int = 500, offset: int = 0) -> List[Track]:
        """Возвращает страницу треков из библиотеки.

        Сначала используем search3 с offset/count. Если конкретный сервер не
        умеет возвращать пустой search-запрос, откатываемся на getRandomSongs.
        """
        try:
            tracks = self.search_tracks(query="", count=size, offset=offset)
        except Exception:
            tracks = []
        if tracks:
            return tracks

        container = self._get("rest/getRandomSongs.view", size=size)
        songs = container.get("randomSongs", {}).get("song", [])
        return self._parse_songs(songs)

    def stream_url(self, track_id: str) -> str:
        params = {**self._auth_params(), "id": track_id}
        return f"{self._url('rest/stream.view')}?{urlencode(params)}"

    def cover_art_url(self, cover_art_id: str, size: int = 300) -> str:
        if not cover_art_id:
            return ""
        params = {**self._auth_params(), "id": cover_art_id, "size": size}
        return f"{self._url('rest/getCoverArt.view')}?{urlencode(params)}"

    def get_cover_art(self, cover_art_id: str, size: int = 300) -> bytes:
        """Загружает байты обложки через Subsonic getCoverArt."""
        if not cover_art_id:
            return b""

        response = self.session.get(self.cover_art_url(cover_art_id, size), timeout=20)
        response.raise_for_status()
        return response.content
