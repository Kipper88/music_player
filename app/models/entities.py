from dataclasses import dataclass


@dataclass
class ServerConfig:
    base_url: str
    username: str
    password: str
    api_version: str = "1.16.1"
    client_name: str = "PyNavidromeDesktop"


@dataclass
class Track:
    id: str
    title: str
    artist: str
    album: str
    duration: int = 0

    @property
    def pretty_duration(self) -> str:
        minutes = self.duration // 60
        seconds = self.duration % 60
        return f"{minutes}:{seconds:02d}"
