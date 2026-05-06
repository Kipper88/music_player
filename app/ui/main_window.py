from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
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
    """Окно глобальных настроек приложения.

    Все значения пишутся в SettingsService, поэтому переживают закрытие окна и
    перезапуск приложения. Пароль сохраняется локально через QSettings; для
    production-версии лучше заменить это на системное хранилище секретов.
    """

    def __init__(self, settings: SettingsService, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(420)

        layout = QFormLayout(self)
        self.url = QLineEdit(str(settings.get("server/url", "http://localhost:4533")))
        self.user = QLineEdit(str(settings.get("server/user", "")))
        self.password = QLineEdit(str(settings.get("server/password", "")))
        self.password.setEchoMode(QLineEdit.Password)

        self.volume = QSlider(Qt.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(int(settings.get("player/volume", 60)))

        save = QPushButton("Сохранить")
        save.clicked.connect(self.accept)

        layout.addRow("URL сервера", self.url)
        layout.addRow("Пользователь", self.user)
        layout.addRow("Пароль", self.password)
        layout.addRow("Громкость", self.volume)
        layout.addRow(save)

    def persist(self) -> None:
        """Сохраняет все поля формы в глобальные настройки."""
        self.settings.set("server/url", self.url.text().strip())
        self.settings.set("server/user", self.user.text().strip())
        self.settings.set("server/password", self.password.text())
        self.settings.set("player/volume", self.volume.value())
        self.settings.sync()


class MainWindow(QMainWindow):
    """Главное окно Spotify-like клиента для Navidrome/Subsonic."""

    def __init__(self) -> None:
        super().__init__()
        self.settings = SettingsService()
        self.playlist_service = PlaylistService()
        self.recommendation_service = RecommendationService()
        self.playlists = self.playlist_service.load()

        self.client: Optional[SubsonicClient] = None
        self.player = PlayerController()
        self.tracks: list[Track] = []
        self.visible_tracks: list[Track] = []
        self.quick_track_buttons: list[QPushButton] = []
        self.track_page_size = 100
        self.track_offset = 0
        self.seek_is_dragging = False

        self.setWindowTitle("Spotify-like Navidrome Player")
        self.resize(1600, 900)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.addLayout(self._topbar())
        layout.addWidget(self._workspace(), 1)
        layout.addWidget(self._bottom_player())

        volume = int(self.settings.get("player/volume", 60))
        self.player.audio.setVolume(volume / 100)
        self.player.player.positionChanged.connect(self._on_position_changed)
        self.player.player.durationChanged.connect(self._on_duration_changed)

        self._apply_spotify_style()

    def _apply_spotify_style(self) -> None:
        """Единая тёмная тема, приближенная к Spotify на скриншоте."""
        self.setStyleSheet(
            """
            QMainWindow { background: #000000; color: #ffffff; }
            QWidget { color: #ffffff; font-size: 14px; }
            QFrame#Panel { background: #121212; border: 1px solid #202020; border-radius: 14px; }
            QFrame#HeroPanel { background: #233011; border: 1px solid #334219; border-radius: 14px; }
            QLineEdit, QListWidget {
                background: #1f1f1f;
                border: 1px solid #333333;
                border-radius: 12px;
                padding: 8px;
                color: #ffffff;
                selection-background-color: #1db954;
            }
            QPushButton {
                background: #242424;
                border: none;
                border-radius: 18px;
                padding: 8px 12px;
                color: #ffffff;
                font-weight: 700;
            }
            QPushButton:hover { background: #303030; }
            QPushButton#PrimaryButton { background: #1db954; color: #000000; }
            QPushButton#PrimaryButton:hover { background: #1ed760; }
            QSlider::groove:horizontal { height: 5px; background: #4d4d4d; border-radius: 2px; }
            QSlider::sub-page:horizontal { background: #ffffff; border-radius: 2px; }
            QSlider::handle:horizontal { background: #ffffff; width: 12px; margin: -4px 0; border-radius: 6px; }
            """
        )

    def _topbar(self) -> QHBoxLayout:
        """Верхняя панель: действия + глобальный поиск + данные сервера."""
        row = QHBoxLayout()
        row.setSpacing(10)

        connect = self._button("Подключиться", primary=True)
        connect.clicked.connect(self.connect_server)
        settings = self._button("Настройки")
        settings.clicked.connect(self.open_settings)
        recommendations = self._button("Рекомендации")
        recommendations.clicked.connect(self.show_recommendations)

        self.global_search = QLineEdit()
        self.global_search.setPlaceholderText("What do you want to play?")
        self.global_search.textChanged.connect(self.filter_tracks)

        self.url_input = QLineEdit(str(self.settings.get("server/url", "http://localhost:4533")))
        self.user_input = QLineEdit(str(self.settings.get("server/user", "")))
        self.pass_input = QLineEdit(str(self.settings.get("server/password", "")))
        self.pass_input.setEchoMode(QLineEdit.Password)

        row.addWidget(connect)
        row.addWidget(settings)
        row.addWidget(recommendations)
        row.addWidget(self.global_search, 2)
        row.addWidget(self.url_input)
        row.addWidget(self.user_input)
        row.addWidget(self.pass_input)
        return row

    def _workspace(self) -> QSplitter:
        """Три колонки как на Spotify: rail / content / now-playing."""
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._left_sidebar())
        splitter.addWidget(self._center_panel())
        splitter.addWidget(self._right_panel())
        splitter.setSizes([92, 1040, 380])
        return splitter

    def _left_sidebar(self) -> QFrame:
        """Узкая вертикальная панель с крупными иконками-разделами."""
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        for text, tooltip, handler in [
            ("⌂", "Главная", self.show_all_tracks),
            ("🔎", "Поиск", self.focus_search),
            ("❤", "Избранное", self.show_favorites),
            ("🎵", "Музыка", self.show_all_tracks),
            ("📚", "Библиотека", self.focus_library),
        ]:
            button = self._button(text)
            button.setToolTip(tooltip)
            button.setFixedSize(52, 52)
            button.clicked.connect(handler)
            layout.addWidget(button)

        layout.addStretch()
        return panel

    def _center_panel(self) -> QFrame:
        """Основная область: фильтры, быстрые действия, плейлисты и треки."""
        panel = QFrame()
        panel.setObjectName("HeroPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        chips = QHBoxLayout()
        for text, handler in [
            ("All", self.show_all_tracks),
            ("Music", self.show_all_tracks),
            ("Podcasts", lambda: self.show_content_placeholder("Подкасты")),
            ("Audiobooks", lambda: self.show_content_placeholder("Аудиокниги")),
        ]:
            button = self._button(text)
            button.clicked.connect(handler)
            chips.addWidget(button)
        chips.addStretch()
        layout.addLayout(chips)

        quick = QHBoxLayout()
        for text, handler in [
            ("▶ Загрузить библиотеку", self.load_tracks),
            ("➕ Ещё треки", self.load_more_tracks),
            ("❤ Favorites", self.show_favorites),
            ("✨ For you", self.show_recommendations),
        ]:
            button = self._button(text, primary=text.startswith("▶"))
            button.clicked.connect(handler)
            quick.addWidget(button)
        quick.addStretch()
        layout.addLayout(quick)

        layout.addWidget(self._title("Быстрый доступ"))
        layout.addWidget(self._quick_access_panel())

        self.playlist_list = QListWidget()
        self.playlist_list.itemClicked.connect(self.show_playlist)
        self.refresh_playlists_ui()

        add_playlist = self._button("+ Плейлист", primary=True)
        add_playlist.clicked.connect(self.create_playlist)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по загруженным трекам...")
        self.search_input.textChanged.connect(self.filter_tracks)

        self.track_list = QListWidget()
        self.track_list.itemDoubleClicked.connect(self.play_selected)

        add_to_playlist = self._button("Добавить выбранный трек в плейлист")
        add_to_playlist.clicked.connect(self.add_selected_to_playlist)

        layout.addWidget(self._title("Плейлисты"))
        layout.addWidget(self.playlist_list, 1)
        layout.addWidget(add_playlist)
        layout.addWidget(self._title("Треки"))
        layout.addWidget(self.search_input)
        layout.addWidget(self.track_list, 4)
        layout.addWidget(add_to_playlist)
        return panel

    def _quick_access_panel(self) -> QFrame:
        """Возвращает карточки быстрого доступа, которые были в первом макете UI.

        Карточки остаются частью интерфейса, но теперь они не захардкожены: после
        загрузки сервера сюда попадают реальные треки из текущей библиотеки.
        """
        panel = QFrame()
        panel.setObjectName("Panel")
        grid = QGridLayout(panel)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        for index in range(8):
            button = self._button("Загрузите треки")
            button.setMinimumHeight(54)
            button.clicked.connect(lambda _checked=False, row=index: self.play_quick_track(row))
            self.quick_track_buttons.append(button)
            grid.addWidget(button, index // 4, index % 4)

        return panel

    def _right_panel(self) -> QFrame:
        """Правая панель с крупной обложкой и информацией о текущем треке."""
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        self.cover = QLabel("Нет обложки")
        self.cover.setFixedSize(320, 320)
        self.cover.setAlignment(Qt.AlignCenter)
        self.cover.setStyleSheet("background:#242424;border-radius:12px;color:#a7a7a7;")

        self.now = QLabel("Ничего не играет")
        self.now.setWordWrap(True)
        self.now.setStyleSheet("font-size:30px;font-weight:800;")

        self.meta = QLabel("Подключитесь к серверу и выберите трек")
        self.meta.setWordWrap(True)
        self.meta.setStyleSheet("color:#b3b3b3;font-size:16px;")

        layout.addWidget(self._title("Now playing view"))
        layout.addWidget(self.cover, alignment=Qt.AlignCenter)
        layout.addWidget(self.now)
        layout.addWidget(self.meta)
        layout.addWidget(self._title("About the artist"))
        layout.addWidget(QLabel("Здесь позже можно показать биографию, жанры и похожих исполнителей."))
        layout.addStretch()
        return panel

    def _bottom_player(self) -> QFrame:
        """Нижний плеер: transport, перемотка, время и громкость."""
        panel = QFrame()
        panel.setObjectName("Panel")
        panel.setFixedHeight(120)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 10, 16, 10)

        controls = QHBoxLayout()
        self.btn_prev = self._button("⏮")
        self.btn_prev.clicked.connect(self.play_previous)
        self.btn_play = self._button("▶", primary=True)
        self.btn_play.clicked.connect(self.play_selected)
        self.btn_pause = self._button("⏸")
        self.btn_pause.clicked.connect(self.player.pause)
        self.btn_next = self._button("⏭")
        self.btn_next.clicked.connect(self.play_next)
        self.btn_reload = self._button("Обновить")
        self.btn_reload.clicked.connect(self.load_tracks)
        self.btn_more = self._button("Ещё")
        self.btn_more.clicked.connect(self.load_more_tracks)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(self.settings.get("player/volume", 60)))
        self.volume_slider.valueChanged.connect(self.change_volume)

        for widget in [
            self.btn_prev,
            self.btn_play,
            self.btn_pause,
            self.btn_next,
            self.btn_reload,
            self.btn_more,
            QLabel("🔊"),
            self.volume_slider,
        ]:
            controls.addWidget(widget)

        seek_row = QHBoxLayout()
        self.time_current = QLabel("0:00")
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.time_total = QLabel("0:00")
        self.seek_slider.sliderPressed.connect(lambda: setattr(self, "seek_is_dragging", True))
        self.seek_slider.sliderReleased.connect(self._seek_to_slider)
        seek_row.addWidget(self.time_current)
        seek_row.addWidget(self.seek_slider, 1)
        seek_row.addWidget(self.time_total)

        layout.addLayout(controls)
        layout.addLayout(seek_row)
        return panel

    def _button(self, text: str, primary: bool = False) -> QPushButton:
        button = QPushButton(text)
        if primary:
            button.setObjectName("PrimaryButton")
        return button

    def _title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-size:22px;font-weight:800;")
        return label

    def _fmt_ms(self, ms: int) -> str:
        seconds = ms // 1000
        return f"{seconds // 60}:{seconds % 60:02d}"

    def _on_position_changed(self, position: int) -> None:
        if not self.seek_is_dragging:
            self.seek_slider.setValue(position)
        self.time_current.setText(self._fmt_ms(position))

    def _on_duration_changed(self, duration: int) -> None:
        self.seek_slider.setRange(0, duration)
        self.time_total.setText(self._fmt_ms(duration))

    def _seek_to_slider(self) -> None:
        self.seek_is_dragging = False
        self.player.player.setPosition(self.seek_slider.value())

    def change_volume(self, value: int) -> None:
        """Меняет громкость и сразу сохраняет её как глобальную настройку."""
        self.player.audio.setVolume(value / 100)
        self.settings.set("player/volume", value)
        self.settings.sync()

    def _persist_connection_fields(self) -> None:
        """Сохраняет данные подключения, введённые в верхней панели."""
        self.settings.set("server/url", self.url_input.text().strip())
        self.settings.set("server/user", self.user_input.text().strip())
        self.settings.set("server/password", self.pass_input.text())
        self.settings.sync()

    def focus_search(self) -> None:
        """Переводит фокус в глобальный поиск, как кнопка Search в Spotify."""
        self.global_search.setFocus()
        self.global_search.selectAll()

    def focus_library(self) -> None:
        """Переводит фокус на список плейлистов/библиотеку."""
        self.playlist_list.setFocus()
        if self.playlist_list.count() and self.playlist_list.currentRow() < 0:
            self.playlist_list.setCurrentRow(0)

    def show_all_tracks(self) -> None:
        """Показывает все загруженные с сервера треки."""
        self.search_input.clear()
        self.global_search.clear()
        self.render_tracks(self.tracks)

    def show_content_placeholder(self, title: str) -> None:
        """Обрабатывает разделы, которых ещё нет в Subsonic-загрузке."""
        self.render_tracks([])
        self.now.setText(title)
        self.meta.setText(
            "Этот раздел уже подключён к интерфейсу, "
            "но для него нужно добавить отдельный API-запрос сервера."
        )

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            dialog.persist()
            self.url_input.setText(dialog.url.text())
            self.user_input.setText(dialog.user.text())
            self.pass_input.setText(dialog.password.text())
            self.volume_slider.setValue(dialog.volume.value())

    def connect_server(self) -> None:
        self.client = SubsonicClient(
            ServerConfig(
                self.url_input.text().strip(),
                self.user_input.text().strip(),
                self.pass_input.text(),
            )
        )
        try:
            self.client.ping()
            self._persist_connection_fields()
            self.load_tracks()
            QMessageBox.information(self, "OK", "Подключено")
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", str(exc))

    def load_tracks(self) -> None:
        """Загружает первую страницу реальных треков с сервера."""
        if not self.client:
            QMessageBox.warning(self, "Нет подключения", "Сначала подключитесь к серверу")
            return
        try:
            self.track_offset = 0
            self.tracks = self.client.get_tracks(
                size=self.track_page_size,
                offset=self.track_offset,
            )
            self.track_offset += len(self.tracks)
            self.render_tracks(self.tracks)
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка загрузки", str(exc))

    def load_more_tracks(self) -> None:
        """Догружает следующую страницу треков, а не ограничивается первыми 20."""
        if not self.client:
            QMessageBox.warning(self, "Нет подключения", "Сначала подключитесь к серверу")
            return
        try:
            new_tracks = self.client.get_tracks(
                size=self.track_page_size,
                offset=self.track_offset,
            )
            existing_ids = {track.id for track in self.tracks}
            unique_tracks = [track for track in new_tracks if track.id not in existing_ids]
            self.tracks.extend(unique_tracks)
            self.track_offset += len(new_tracks)
            self.render_tracks(self.tracks)
            if not unique_tracks:
                QMessageBox.information(
                    self,
                    "Больше треков нет",
                    "Сервер не вернул новые треки для следующей страницы.",
                )
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка догрузки", str(exc))

    def _refresh_quick_access(self, items: list[Track]) -> None:
        """Обновляет карточки быстрого доступа реальными треками сервера."""
        for index, button in enumerate(self.quick_track_buttons):
            if index < len(items):
                track = items[index]
                button.setText(f"▶ {track.title}\n{track.artist}")
                button.setEnabled(True)
            else:
                button.setText("Загрузите треки")
                button.setEnabled(False)

    def play_quick_track(self, index: int) -> None:
        """Запускает трек из карточки быстрого доступа."""
        if index >= len(self.visible_tracks):
            return
        track = self.visible_tracks[index]
        self._select_track_in_list(track.id)
        self.play_track_by_id(track.id)

    def _select_track_in_list(self, track_id: str) -> None:
        """Выделяет трек в списке, если он сейчас видим."""
        for row in range(self.track_list.count()):
            if self.track_list.item(row).data(Qt.UserRole) == track_id:
                self.track_list.setCurrentRow(row)
                return

    def render_tracks(self, items: list[Track]) -> None:
        self.visible_tracks = items
        self.track_list.clear()
        for track in items:
            item = QListWidgetItem(
                f"{track.title} — {track.artist} • {track.album} [{track.pretty_duration}]"
            )
            item.setData(Qt.UserRole, track.id)
            self.track_list.addItem(item)
        self._refresh_quick_access(items)

    def filter_tracks(self, text: str) -> None:
        query = text.lower().strip()
        if not query:
            self.render_tracks(self.tracks)
            return

        filtered = [
            track
            for track in self.tracks
            if query in f"{track.title} {track.artist} {track.album}".lower()
        ]
        self.render_tracks(filtered)

    def play_selected(self, _item: QListWidgetItem | None = None) -> None:
        item = self.track_list.currentItem()
        if item is None and self.track_list.count() > 0:
            self.track_list.setCurrentRow(0)
            item = self.track_list.currentItem()
        if not self.client or item is None:
            return
        self.play_track_by_id(item.data(Qt.UserRole))

    def play_track_by_id(self, track_id: str) -> None:
        track = next((item for item in self.tracks if item.id == track_id), None)
        if not self.client or not track:
            return

        self.player.play_url(self.client.stream_url(track_id))
        self.recommendation_service.register_play(track)
        self.now.setText(track.title)
        self.meta.setText(f"{track.artist}\n{track.album}\nДлительность: {track.pretty_duration}")
        self._load_cover(track)

    def _load_cover(self, track: Track) -> None:
        if not self.client or not track.cover_art:
            self.cover.setText("Нет обложки")
            self.cover.setPixmap(QPixmap())
            return

        try:
            pixmap = QPixmap()
            pixmap.loadFromData(self.client.get_cover_art(track.cover_art, size=420))
            self.cover.setPixmap(
                pixmap.scaled(
                    320,
                    320,
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation,
                )
            )
        except Exception:
            self.cover.setText("Не удалось загрузить обложку")

    def play_next(self) -> None:
        current = self.track_list.currentRow()
        if current < self.track_list.count() - 1:
            self.track_list.setCurrentRow(current + 1)
            self.play_selected()

    def play_previous(self) -> None:
        current = self.track_list.currentRow()
        if current > 0:
            self.track_list.setCurrentRow(current - 1)
            self.play_selected()

    def refresh_playlists_ui(self) -> None:
        if hasattr(self, "playlist_list"):
            self.playlist_list.clear()
            self.playlist_list.addItems(self.playlists.keys())

    def create_playlist(self) -> None:
        name, ok = QInputDialog.getText(self, "Новый плейлист", "Название")
        if ok and name.strip():
            self.playlists.setdefault(name.strip(), [])
            self.playlist_service.save(self.playlists)
            self.refresh_playlists_ui()

    def add_selected_to_playlist(self) -> None:
        item = self.track_list.currentItem()
        playlist_item = self.playlist_list.currentItem()
        if not item:
            QMessageBox.information(self, "Нет трека", "Сначала выберите трек")
            return
        if not playlist_item:
            QMessageBox.information(self, "Нет плейлиста", "Сначала выберите плейлист")
            return

        track_id = item.data(Qt.UserRole)
        playlist_name = playlist_item.text()
        self.playlists.setdefault(playlist_name, [])
        if track_id not in self.playlists[playlist_name]:
            self.playlists[playlist_name].append(track_id)
            self.playlist_service.save(self.playlists)

    def show_playlist(self, item: QListWidgetItem) -> None:
        track_ids = set(self.playlists.get(item.text(), []))
        self.render_tracks([track for track in self.tracks if track.id in track_ids])

    def show_favorites(self) -> None:
        track_ids = set(self.playlists.get("Favorites", []))
        self.render_tracks([track for track in self.tracks if track.id in track_ids])

    def show_recommendations(self) -> None:
        self.render_tracks(self.recommendation_service.recommend(self.tracks, 30))
