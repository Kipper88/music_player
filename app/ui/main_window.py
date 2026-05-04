from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QInputDialog,
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
        self.password = QLineEdit(str(settings.get("server/password", "")))
        self.password.setEchoMode(QLineEdit.Password)
        self.volume = QSlider(Qt.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(int(settings.get("player/volume", 60)))
        save = QPushButton("Сохранить")
        save.clicked.connect(self.accept)
        l.addRow("URL", self.url)
        l.addRow("User", self.user)
        l.addRow("Password", self.password)
        l.addRow("Громкость", self.volume)
        l.addRow(save)

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

        self.setWindowTitle("Spotify-like Navidrome Player")
        self.resize(1460, 900)

        root = QWidget(); self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.addLayout(self._topbar())
        layout.addWidget(self._body(), 1)
        layout.addLayout(self._player())

        vol = int(self.settings.get("player/volume", 60))
        self.player.audio.setVolume(vol / 100)

        self.setStyleSheet("""
        QMainWindow{background:#121212;color:#fff;} QWidget{font-size:14px;color:#fff;}
        QLineEdit,QListWidget{background:#181818;border:1px solid #333;border-radius:10px;padding:6px;}
        QPushButton{background:#1db954;border:none;border-radius:10px;padding:8px 12px;color:#fff;font-weight:600;}
        QPushButton:hover{background:#1ed760;}
        """)

    def _topbar(self):
        r=QHBoxLayout()
        self.url_input = QLineEdit(str(self.settings.get("server/url", "http://localhost:4533")))
        self.user_input = QLineEdit(str(self.settings.get("server/user", "")))
        self.pass_input = QLineEdit(str(self.settings.get("server/password", ""))); self.pass_input.setEchoMode(QLineEdit.Password)
        for txt,fn in [("Подключиться",self.connect_server),("Настройки",self.open_settings),("Рекомендации",self.show_recommendations)]:
            b=QPushButton(txt); b.clicked.connect(fn); r.addWidget(b)
        r.addWidget(self.url_input,2); r.addWidget(self.user_input); r.addWidget(self.pass_input)
        return r

    def _body(self):
        s=QSplitter(Qt.Horizontal)
        self.playlist_list = QListWidget(); self.refresh_playlists_ui()
        add_pl=QPushButton("+ Плейлист"); add_pl.clicked.connect(self.create_playlist)
        left=QWidget(); ll=QVBoxLayout(left); ll.addWidget(QLabel("Плейлисты")); ll.addWidget(self.playlist_list); ll.addWidget(add_pl)

        center=QWidget(); cl=QVBoxLayout(center)
        self.search_input=QLineEdit(); self.search_input.setPlaceholderText("Поиск..."); self.search_input.textChanged.connect(self.filter_tracks)
        self.track_list=QListWidget(); self.track_list.itemDoubleClicked.connect(self.play_selected)
        add_to=QPushButton("Добавить в плейлист"); add_to.clicked.connect(self.add_selected_to_playlist)
        cl.addWidget(self.search_input); cl.addWidget(self.track_list); cl.addWidget(add_to)

        right=QWidget(); rl=QVBoxLayout(right)
        self.cover=QLabel(); self.cover.setFixedSize(280,280); self.cover.setStyleSheet("background:#222;border-radius:12px;")
        self.cover.setAlignment(Qt.AlignCenter)
        self.now=QLabel("Ничего не играет"); self.meta=QLabel("...")
        rl.addWidget(self.cover); rl.addWidget(self.now); rl.addWidget(self.meta); rl.addStretch()

        s.addWidget(left); s.addWidget(center); s.addWidget(right); s.setSizes([260,820,320]); return s

    def _player(self):
        r=QHBoxLayout()
        play=QPushButton("Play"); pause=QPushButton("Pause"); reload=QPushButton("Обновить")
        self.volume_slider=QSlider(Qt.Horizontal); self.volume_slider.setRange(0,100); self.volume_slider.setValue(int(self.settings.get("player/volume",60)))
        self.volume_slider.valueChanged.connect(lambda v: self.player.audio.setVolume(v/100))
        play.clicked.connect(self.play_selected); pause.clicked.connect(self.player.pause); reload.clicked.connect(self.load_tracks)
        r.addWidget(play); r.addWidget(pause); r.addWidget(reload); r.addWidget(QLabel("Громкость")); r.addWidget(self.volume_slider)
        return r

    def open_settings(self):
        d=SettingsDialog(self.settings,self)
        if d.exec():
            d.persist()
            self.url_input.setText(d.url.text()); self.user_input.setText(d.user.text()); self.pass_input.setText(d.password.text())
            self.volume_slider.setValue(d.volume.value())

    def connect_server(self):
        self.client=SubsonicClient(ServerConfig(self.url_input.text().strip(),self.user_input.text().strip(),self.pass_input.text()))
        try:
            self.client.ping(); self.load_tracks(); QMessageBox.information(self,"OK","Подключено")
        except Exception as e:
            QMessageBox.critical(self,"Ошибка",str(e))

    def load_tracks(self):
        if not self.client: return
        self.tracks=self.client.get_tracks(200); self.render_tracks(self.tracks)

    def render_tracks(self, items:list[Track]):
        self.track_list.clear()
        for t in items:
            i=QListWidgetItem(f"{t.title} — {t.artist} [{t.pretty_duration}]"); i.setData(Qt.UserRole,t.id); self.track_list.addItem(i)

    def filter_tracks(self, text:str):
        q=text.lower().strip();
        self.render_tracks([t for t in self.tracks if q in f"{t.title} {t.artist} {t.album}".lower()] if q else self.tracks)

    def play_selected(self):
        if not self.client or not self.track_list.currentItem(): return
        tid=self.track_list.currentItem().data(Qt.UserRole)
        tr=next((x for x in self.tracks if x.id==tid),None)
        if not tr: return
        self.player.play_url(self.client.stream_url(tid))
        self.recommendation_service.register_play(tr)
        self.now.setText(tr.title); self.meta.setText(f"{tr.artist}\n{tr.album}")
        if tr.cover_art:
            p=QPixmap(); p.loadFromData(self.client.session.get(self.client.cover_art_url(tr.cover_art),timeout=20).content)
            self.cover.setPixmap(p.scaled(280,280,Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation))

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
        item = self.track_list.currentItem()
        pl_item = self.playlist_list.currentItem()
        if not item or not pl_item:
            return
        tid = item.data(Qt.UserRole)
        pl = pl_item.text()
        self.playlists.setdefault(pl, [])
        if tid not in self.playlists[pl]:
            self.playlists[pl].append(tid)
            self.playlist_service.save(self.playlists)

    def show_recommendations(self):
        recs = self.recommendation_service.recommend(self.tracks, 30)
        self.render_tracks(recs)
