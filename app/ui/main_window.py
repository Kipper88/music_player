from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QScrollArea,
    QSlider, QSplitter, QVBoxLayout, QWidget, QInputDialog
)

from app.core.player_controller import PlayerController
from app.models.entities import ServerConfig, Track
from app.services.playlist_service import PlaylistService
from app.services.recommendation_service import RecommendationService
from app.services.settings_service import SettingsService
from app.services.subsonic_client import SubsonicClient


class SettingsDialog(QDialog):
    def __init__(self, settings: SettingsService, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Настройки")
        l = QFormLayout(self)
        self.url = QLineEdit(str(settings.get("server/url", "http://localhost:4533")))
        self.user = QLineEdit(str(settings.get("server/user", "")))
        self.password = QLineEdit(str(settings.get("server/password", ""))); self.password.setEchoMode(QLineEdit.Password)
        self.volume = QSlider(Qt.Horizontal); self.volume.setRange(0, 100); self.volume.setValue(int(settings.get("player/volume", 60)))
        save = QPushButton("Сохранить"); save.clicked.connect(self.accept)
        l.addRow("URL", self.url); l.addRow("User", self.user); l.addRow("Password", self.password); l.addRow("Громкость", self.volume); l.addRow(save)

    def persist(self):
        self.settings.set("server/url", self.url.text().strip())
        self.settings.set("server/user", self.user.text().strip())
        self.settings.set("server/password", self.password.text())
        self.settings.set("player/volume", self.volume.value())
        self.settings.sync()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = SettingsService()
        self.playlist_service = PlaylistService()
        self.recommendation_service = RecommendationService()
        self.playlists = self.playlist_service.load()
        self.client: Optional[SubsonicClient] = None
        self.player = PlayerController()
        self.tracks: list[Track] = []
        self.seek_is_dragging = False

        self.setWindowTitle("Spotify-like Navidrome Player")
        self.resize(1600, 900)

        root = QWidget(); self.setCentralWidget(root)
        layout = QVBoxLayout(root); layout.setContentsMargins(10, 10, 10, 10); layout.setSpacing(10)
        layout.addLayout(self._topbar())
        layout.addWidget(self._workspace(), 1)
        layout.addWidget(self._bottom_player())

        vol = int(self.settings.get("player/volume", 60))
        self.player.audio.setVolume(vol / 100)

        self.player.player.positionChanged.connect(self._on_position_changed)
        self.player.player.durationChanged.connect(self._on_duration_changed)

        self.setStyleSheet("""
        QMainWindow{background:#0d0d0d;color:#fff;} QWidget{color:#fff;}
        QFrame#Panel{background:#121212;border:1px solid #202020;border-radius:14px;}
        QLineEdit,QListWidget{background:#1a1a1a;border:1px solid #333;border-radius:10px;padding:8px;color:#fff;}
        QPushButton{background:#1db954;border:none;border-radius:14px;padding:8px 12px;color:#fff;font-weight:600;}
        QPushButton:hover{background:#1ed760;}
        """)

    def _topbar(self):
        r = QHBoxLayout()
        self.url_input = QLineEdit(str(self.settings.get("server/url", "http://localhost:4533")))
        self.user_input = QLineEdit(str(self.settings.get("server/user", "")))
        self.pass_input = QLineEdit(str(self.settings.get("server/password", ""))); self.pass_input.setEchoMode(QLineEdit.Password)
        self.global_search = QLineEdit(); self.global_search.setPlaceholderText("What do you want to play?")
        for txt, fn in [("Подключиться", self.connect_server), ("Настройки", self.open_settings), ("Рекомендации", self.show_recommendations)]:
            b = QPushButton(txt); b.clicked.connect(fn); r.addWidget(b)
        r.addWidget(self.global_search, 2); r.addWidget(self.url_input); r.addWidget(self.user_input); r.addWidget(self.pass_input)
        return r

    def _workspace(self):
        s = QSplitter(Qt.Horizontal)
        s.addWidget(self._left_sidebar())
        s.addWidget(self._center_panel())
        s.addWidget(self._right_panel())
        s.setSizes([120, 980, 380])
        return s

    def _left_sidebar(self):
        panel = QFrame(); panel.setObjectName("Panel")
        l = QVBoxLayout(panel)
        for txt in ["⌂", "🔎", "❤", "🎵", "📚"]:
            b = QPushButton(txt); b.setFixedHeight(42); l.addWidget(b)
        l.addStretch()
        return panel

    def _center_panel(self):
        panel = QFrame(); panel.setObjectName("Panel")
        l = QVBoxLayout(panel)
        chips = QHBoxLayout()
        for txt in ["All", "Music", "Podcasts", "Audiobooks"]:
            b = QPushButton(txt); b.setStyleSheet("background:#2a2a2a;border-radius:16px;padding:6px 14px;")
            chips.addWidget(b)
        chips.addStretch(); l.addLayout(chips)

        self.playlist_list = QListWidget(); self.refresh_playlists_ui()
        add_pl = QPushButton("+ Плейлист"); add_pl.clicked.connect(self.create_playlist)

        self.search_input = QLineEdit(); self.search_input.setPlaceholderText("Поиск по трекам..."); self.search_input.textChanged.connect(self.filter_tracks)
        self.track_list = QListWidget(); self.track_list.itemDoubleClicked.connect(self.play_selected)
        add_to = QPushButton("Добавить в плейлист"); add_to.clicked.connect(self.add_selected_to_playlist)

        l.addWidget(QLabel("Плейлисты")); l.addWidget(self.playlist_list); l.addWidget(add_pl)
        l.addWidget(QLabel("Треки")); l.addWidget(self.search_input); l.addWidget(self.track_list); l.addWidget(add_to)
        return panel

    def _right_panel(self):
        panel = QFrame(); panel.setObjectName("Panel")
        l = QVBoxLayout(panel)
        self.cover = QLabel(); self.cover.setFixedSize(320, 320); self.cover.setStyleSheet("background:#242424;border-radius:12px;"); self.cover.setAlignment(Qt.AlignCenter)
        self.now = QLabel("Ничего не играет"); self.now.setStyleSheet("font-size:30px;font-weight:800;")
        self.meta = QLabel("Подключитесь к серверу"); self.meta.setWordWrap(True)
        l.addWidget(QLabel("Now playing view")); l.addWidget(self.cover, alignment=Qt.AlignCenter); l.addWidget(self.now); l.addWidget(self.meta); l.addStretch()
        return panel

    def _bottom_player(self):
        panel = QFrame(); panel.setObjectName("Panel"); panel.setFixedHeight(120)
        l = QVBoxLayout(panel)
        row = QHBoxLayout()
        self.btn_prev = QPushButton("⏮")
        self.btn_play = QPushButton("⏯"); self.btn_play.clicked.connect(self.play_selected)
        self.btn_pause = QPushButton("⏸"); self.btn_pause.clicked.connect(self.player.pause)
        self.btn_next = QPushButton("⏭")
        self.btn_reload = QPushButton("Обновить"); self.btn_reload.clicked.connect(self.load_tracks)
        self.volume_slider = QSlider(Qt.Horizontal); self.volume_slider.setRange(0, 100); self.volume_slider.setValue(int(self.settings.get("player/volume", 60)))
        self.volume_slider.valueChanged.connect(lambda v: self.player.audio.setVolume(v / 100))
        for w in [self.btn_prev, self.btn_play, self.btn_pause, self.btn_next, self.btn_reload, QLabel("🔊"), self.volume_slider]: row.addWidget(w)

        seek_row = QHBoxLayout()
        self.time_current = QLabel("0:00")
        self.seek_slider = QSlider(Qt.Horizontal); self.seek_slider.setRange(0, 0)
        self.time_total = QLabel("0:00")
        self.seek_slider.sliderPressed.connect(lambda: setattr(self, "seek_is_dragging", True))
        self.seek_slider.sliderReleased.connect(self._seek_to_slider)
        seek_row.addWidget(self.time_current); seek_row.addWidget(self.seek_slider, 1); seek_row.addWidget(self.time_total)

        l.addLayout(row); l.addLayout(seek_row)
        return panel

    def _fmt_ms(self, ms: int) -> str:
        s = ms // 1000
        return f"{s//60}:{s%60:02d}"

    def _on_position_changed(self, pos: int):
        if not self.seek_is_dragging:
            self.seek_slider.setValue(pos)
        self.time_current.setText(self._fmt_ms(pos))

    def _on_duration_changed(self, dur: int):
        self.seek_slider.setRange(0, dur)
        self.time_total.setText(self._fmt_ms(dur))

    def _seek_to_slider(self):
        self.seek_is_dragging = False
        self.player.player.setPosition(self.seek_slider.value())

    def open_settings(self):
        d = SettingsDialog(self.settings, self)
        if d.exec():
            d.persist()
            self.url_input.setText(d.url.text()); self.user_input.setText(d.user.text()); self.pass_input.setText(d.password.text())
            self.volume_slider.setValue(d.volume.value())

    def connect_server(self):
        self.client = SubsonicClient(ServerConfig(self.url_input.text().strip(), self.user_input.text().strip(), self.pass_input.text()))
        try:
            self.client.ping(); self.load_tracks(); QMessageBox.information(self, "OK", "Подключено")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def load_tracks(self):
        if not self.client: return
        self.tracks = self.client.get_tracks(200); self.render_tracks(self.tracks)

    def render_tracks(self, items: list[Track]):
        self.track_list.clear()
        for t in items:
            i = QListWidgetItem(f"{t.title} — {t.artist} [{t.pretty_duration}]")
            i.setData(Qt.UserRole, t.id); self.track_list.addItem(i)

    def filter_tracks(self, text: str):
        q = text.lower().strip()
        self.render_tracks([t for t in self.tracks if q in f"{t.title} {t.artist} {t.album}".lower()] if q else self.tracks)

    def play_selected(self):
        if not self.client or not self.track_list.currentItem(): return
        tid = self.track_list.currentItem().data(Qt.UserRole)
        tr = next((x for x in self.tracks if x.id == tid), None)
        if not tr: return
        self.player.play_url(self.client.stream_url(tid))
        self.recommendation_service.register_play(tr)
        self.now.setText(tr.title); self.meta.setText(f"{tr.artist}\n{tr.album}")
        if tr.cover_art:
            p = QPixmap(); p.loadFromData(self.client.session.get(self.client.cover_art_url(tr.cover_art), timeout=20).content)
            self.cover.setPixmap(p.scaled(320, 320, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))

    def refresh_playlists_ui(self):
        if hasattr(self, "playlist_list"):
            self.playlist_list.clear(); self.playlist_list.addItems(self.playlists.keys())

    def create_playlist(self):
        name, ok = QInputDialog.getText(self, "Новый плейлист", "Название")
        if ok and name.strip():
            self.playlists.setdefault(name.strip(), [])
            self.playlist_service.save(self.playlists)
            self.refresh_playlists_ui()

    def add_selected_to_playlist(self):
        item = self.track_list.currentItem(); pl_item = self.playlist_list.currentItem()
        if not item or not pl_item: return
        tid = item.data(Qt.UserRole); pl = pl_item.text()
        self.playlists.setdefault(pl, [])
        if tid not in self.playlists[pl]:
            self.playlists[pl].append(tid); self.playlist_service.save(self.playlists)

    def show_recommendations(self):
        self.render_tracks(self.recommendation_service.recommend(self.tracks, 30))
