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

    def stop(self) -> None:
        self.player.stop()

    def set_position(self, position: int) -> None:
        """Set playback position in milliseconds"""
        self.player.setPosition(position)

    def get_position(self) -> int:
        """Get current playback position in milliseconds"""
        return self.player.position()

    def get_duration(self) -> int:
        """Get track duration in milliseconds"""
        return self.player.duration()

    def is_playing(self) -> bool:
        """Check if currently playing"""
        return self.player.playbackState() == QMediaPlayer.PlayingState
