import hashlib
import secrets
from typing import List
from urllib.parse import urljoin

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

    def _get(self, endpoint: str, **params):
        url = urljoin(self.config.base_url.rstrip("/") + "/", endpoint.lstrip("/"))
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

    def get_tracks(self, size: int = 100) -> List[Track]:
        container = self._get("rest/getRandomSongs.view", size=size)
        songs = container.get("randomSongs", {}).get("song", [])
        if isinstance(songs, dict):
            songs = [songs]
        tracks: List[Track] = []
        for s in songs:
            tracks.append(
                Track(
                    id=str(s.get("id", "")),
                    title=s.get("title", "Unknown"),
                    artist=s.get("artist", "Unknown Artist"),
                    album=s.get("album", "Unknown Album"),
                    duration=int(s.get("duration", 0) or 0),
                    cover_art=str(s.get("coverArt", "")),
                )
            )
        return tracks

    def stream_url(self, track_id: str) -> str:
        params = self._auth_params()
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.config.base_url.rstrip('/')}/rest/stream.view?id={track_id}&{query}"


    def cover_art_url(self, cover_art_id: str, size: int = 300) -> str:
        if not cover_art_id:
            return ""
        params = self._auth_params()
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.config.base_url.rstrip('/')}/rest/getCoverArt.view?id={cover_art_id}&size={size}&{query}"
