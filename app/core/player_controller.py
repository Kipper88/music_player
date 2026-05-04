from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


class PlayerController:
    def __init__(self) -> None:
        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)
        self.audio.setVolume(0.6)

    def play_url(self, url: str) -> None:
        self.player.setSource(QUrl(url))
        self.player.play()

    def pause(self) -> None:
        self.player.pause()

    def resume(self) -> None:
        self.player.play()
