from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.core.player_controller import PlayerController
from app.models.entities import ServerConfig, Track
from app.services.subsonic_client import SubsonicClient


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Navidrome-compatible Desktop Player")
        self.resize(1400, 900)

        self.client: Optional[SubsonicClient] = None
        self.player = PlayerController()
        self.tracks: list[Track] = []

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        layout.addLayout(self._build_connection_bar())
        layout.addWidget(self._build_main_splitter(), stretch=1)
        layout.addLayout(self._build_player_bar())

        self.setStyleSheet("""
            QMainWindow { background:#0d1117; color:#e6edf3; }
            QWidget { color:#e6edf3; font-size:14px; }
            QLineEdit, QListWidget { background:#161b22; border:1px solid #30363d; border-radius:8px; padding:6px; }
            QPushButton { background:#238636; border:none; border-radius:8px; padding:8px 12px; color:white; }
            QPushButton:hover { background:#2ea043; }
        """)

    def _build_connection_bar(self):
        row = QHBoxLayout()
        self.url_input = QLineEdit("http://localhost:4533")
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Username")
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.Password)
        connect_btn = QPushButton("Подключиться")
        connect_btn.clicked.connect(self.connect_server)

        row.addWidget(QLabel("Server:"))
        row.addWidget(self.url_input, 2)
        row.addWidget(self.user_input)
        row.addWidget(self.pass_input)
        row.addWidget(connect_btn)
        return row

    def _build_main_splitter(self):
        splitter = QSplitter(Qt.Horizontal)
        self.left_list = QListWidget()
        self.left_list.addItems(["Home", "Random", "Favorites", "Albums"])

        center = QWidget()
        center_l = QVBoxLayout(center)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по загруженным трекам...")
        self.search_input.textChanged.connect(self.filter_tracks)
        self.track_list = QListWidget()
        self.track_list.itemDoubleClicked.connect(self.play_selected)
        center_l.addWidget(self.search_input)
        center_l.addWidget(self.track_list)

        right = QWidget()
        right_l = QVBoxLayout(right)
        self.now_label = QLabel("Ничего не играет")
        self.meta_label = QLabel("Подключитесь к серверу и загрузите треки")
        self.meta_label.setWordWrap(True)
        right_l.addWidget(QLabel("Now Playing"))
        right_l.addWidget(self.now_label)
        right_l.addWidget(self.meta_label)
        right_l.addStretch()

        splitter.addWidget(self.left_list)
        splitter.addWidget(center)
        splitter.addWidget(right)
        splitter.setSizes([180, 760, 300])
        return splitter

    def _build_player_bar(self):
        row = QHBoxLayout()
        self.play_btn = QPushButton("Play")
        self.pause_btn = QPushButton("Pause")
        reload_btn = QPushButton("Обновить треки")
        self.play_btn.clicked.connect(self.play_selected)
        self.pause_btn.clicked.connect(self.player.pause)
        reload_btn.clicked.connect(self.load_tracks)
        row.addWidget(self.play_btn)
        row.addWidget(self.pause_btn)
        row.addWidget(reload_btn)
        row.addStretch()
        return row

    def connect_server(self):
        """Создаём клиент и проверяем доступность сервера."""
        cfg = ServerConfig(
            base_url=self.url_input.text().strip(),
            username=self.user_input.text().strip(),
            password=self.pass_input.text(),
        )
        self.client = SubsonicClient(cfg)
        try:
            self.client.ping()
            QMessageBox.information(self, "OK", "Подключение успешно")
            self.load_tracks()
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка подключения", str(exc))

    def load_tracks(self):
        """Загружаем реальные треки с сервера через getRandomSongs."""
        if not self.client:
            QMessageBox.warning(self, "Нет клиента", "Сначала подключитесь к серверу")
            return
        try:
            self.tracks = self.client.get_tracks(size=200)
            self._render_tracks(self.tracks)
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка загрузки", str(exc))

    def _render_tracks(self, tracks: list[Track]):
        self.track_list.clear()
        for tr in tracks:
            item = QListWidgetItem(f"{tr.title} — {tr.artist} [{tr.pretty_duration}]")
            item.setData(Qt.UserRole, tr.id)
            self.track_list.addItem(item)

    def filter_tracks(self, text: str):
        query = text.strip().lower()
        if not query:
            self._render_tracks(self.tracks)
            return
        filtered = [t for t in self.tracks if query in f"{t.title} {t.artist} {t.album}".lower()]
        self._render_tracks(filtered)

    def play_selected(self):
        if not self.client:
            return
        item = self.track_list.currentItem()
        if not item:
            return
        track_id = item.data(Qt.UserRole)
        track = next((t for t in self.tracks if t.id == track_id), None)
        if not track:
            return
        stream = self.client.stream_url(track_id)
        self.player.play_url(stream)
        self.now_label.setText(track.title)
        self.meta_label.setText(f"{track.artist}\n{track.album}\nДлительность: {track.pretty_duration}")
