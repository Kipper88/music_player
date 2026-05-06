from __future__ import annotations

import random
import os
from typing import Optional, Callable
from functools import lru_cache

from PySide6.QtCore import Qt, QSize, QThread, Signal, QRectF, QPointF
from PySide6.QtGui import QPixmap, QIcon, QPainter, QColor, QPainterPath, QPen, QBrush, QPolygonF
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QScrollArea,
    QSlider, QVBoxLayout, QWidget, QInputDialog, QGraphicsDropShadowEffect,
    QApplication, QMenu
)

from app.ui.styles import SpotifyColors
from app.ui.components import *

os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)


class ImageLoader(QThread):
    """Background image loader with proper cleanup"""
    finished = Signal(str, QPixmap)
    
    def __init__(self, url: str, size: int = 300):
        super().__init__()
        self.url = url
        self.size = size
        self._is_running = True
    
    def run(self):
        if not self._is_running:
            return
        try:
            import requests
            response = requests.get(self.url, timeout=10)
            if response.status_code == 200 and self._is_running:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(self.size, self.size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    if self._is_running:
                        self.finished.emit(self.url, scaled)
        except Exception:
            pass
    
    def stop(self):
        self._is_running = False


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
        self.setWindowTitle("Settings")
        self.setFixedSize(450, 350)
        self.setStyleSheet(f"""
            QDialog {{
                background: {SpotifyColors.DARK_BASE};
            }}
            QLabel {{
                color: {SpotifyColors.WHITE};
                font-size: 14px;
            }}
            QLineEdit {{
                background: {SpotifyColors.DARK_HIGHLIGHT};
                border: 1px solid {SpotifyColors.DARK_PRESS};
                border-radius: 4px;
                padding: 12px;
                color: {SpotifyColors.WHITE};
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {SpotifyColors.WHITE};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(32, 32, 32, 32)
        
        title = QLabel("Server Settings")
        title.setStyleSheet(f"color: {SpotifyColors.WHITE}; font-size: 24px; font-weight: 700;")
        layout.addWidget(title)
        
        form = QFormLayout()
        form.setSpacing(16)
        
        self.url = QLineEdit(str(settings.get("server/url", "http://localhost:4533")))
        self.user = QLineEdit(str(settings.get("server/user", "")))
        self.password = QLineEdit(str(settings.get("server/password", "")))
        self.password.setEchoMode(QLineEdit.Password)
        
        form.addRow("Server URL", self.url)
        form.addRow("Username", self.user)
        form.addRow("Password", self.password)
        
        layout.addLayout(form)
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        cancel = QPushButton("Cancel")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        cancel.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {SpotifyColors.SUBDUED};
                color: {SpotifyColors.WHITE};
                border-radius: 20px;
                padding: 12px 32px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                border-color: {SpotifyColors.WHITE};
            }}
        """)
        
        save = QPushButton("Save")
        save.setCursor(Qt.PointingHandCursor)
        save.clicked.connect(self.accept)
        save.setStyleSheet(f"""
            QPushButton {{
                background: {SpotifyColors.GREEN};
                color: {SpotifyColors.BLACK};
                border: none;
                border-radius: 20px;
                padding: 12px 32px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {SpotifyColors.GREEN_HOVER};
            }}
        """)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel)
        btn_layout.addWidget(save)
        layout.addLayout(btn_layout)

    def persist(self):
        self.settings.set("server/url", self.url.text().strip())
        self.settings.set("server/user", self.user.text().strip())
        self.settings.set("server/password", self.password.text())
        self.settings.sync()


class QueueDialog(QDialog):
    """Queue dialog"""
    def __init__(self, tracks: list[Track], current_index: int, on_select: Callable = None, parent=None):
        super().__init__(parent)
        self.tracks = tracks
        self.on_select = on_select
        self.setWindowTitle("Play Queue")
        self.setFixedSize(500, 600)
        self.setStyleSheet(f"""
            QDialog {{
                background: {SpotifyColors.DARK_BASE};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        header = QHBoxLayout()
        title = QLabel("Queue")
        title.setStyleSheet(f"color: {SpotifyColors.WHITE}; font-size: 24px; font-weight: 700;")
        
        clear_btn = QPushButton("Clear")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {SpotifyColors.SUBDUED};
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                color: {SpotifyColors.WHITE};
            }}
        """)
        
        header.addWidget(title)
        header.addStretch()
        header.addWidget(clear_btn)
        layout.addLayout(header)
        
        # Now playing
        if 0 <= current_index < len(tracks):
            now_label = QLabel("Now playing")
            now_label.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 12px; font-weight: 700;")
            layout.addWidget(now_label)
            
            current = tracks[current_index]
            current_row = QFrame()
            current_row.setFixedHeight(56)
            current_row.setStyleSheet(f"background: {SpotifyColors.DARK_HIGHLIGHT}; border-radius: 4px;")
            
            row_layout = QHBoxLayout(current_row)
            row_layout.setContentsMargins(12, 0, 12, 0)
            
            cover = QLabel()
            cover.setFixedSize(40, 40)
            cover.setPixmap(Icons.pixmap("music_note", 24, SpotifyColors.SUBDUED))
            cover.setAlignment(Qt.AlignCenter)
            cover.setStyleSheet(f"background: {SpotifyColors.DARK_PRESS}; border-radius: 4px;")
            
            info = QVBoxLayout()
            title_l = QLabel(current.title)
            title_l.setStyleSheet(f"color: {SpotifyColors.GREEN}; font-size: 14px;")
            artist_l = QLabel(current.artist)
            artist_l.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 12px;")
            info.addWidget(title_l)
            info.addWidget(artist_l)
            
            row_layout.addWidget(cover)
            row_layout.addLayout(info, 1)
            
            layout.addWidget(current_row)
        
        # Next in queue
        next_label = QLabel("Next in queue")
        next_label.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 12px; font-weight: 700;")
        layout.addWidget(next_label)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none; background: transparent;")
        
        queue_widget = QWidget()
        queue_layout = QVBoxLayout(queue_widget)
        queue_layout.setContentsMargins(0, 0, 0, 0)
        queue_layout.setSpacing(4)
        
        for i, track in enumerate(tracks):
            if i == current_index:
                continue
            
            row = QFrame()
            row.setFixedHeight(48)
            row.setCursor(Qt.PointingHandCursor)
            row.setStyleSheet(f"""
                QFrame {{
                    background: transparent;
                    border-radius: 4px;
                }}
                QFrame:hover {{
                    background: {SpotifyColors.DARK_HIGHLIGHT};
                }}
            """)
            
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 0, 12, 0)
            
            title_l = QLabel(f"{track.title} - {track.artist}")
            title_l.setStyleSheet(f"color: {SpotifyColors.WHITE}; font-size: 14px; background: transparent;")
            
            duration_l = QLabel(track.pretty_duration)
            duration_l.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 14px; background: transparent;")
            
            row_layout.addWidget(title_l, 1)
            row_layout.addWidget(duration_l)
            
            def make_click_handler(idx):
                def handler(event):
                    if self.on_select:
                        self.on_select(idx)
                    self.accept()
                return handler
            
            row.mousePressEvent = make_click_handler(i)
            queue_layout.addWidget(row)
        
        queue_layout.addStretch()
        scroll.setWidget(queue_widget)
        layout.addWidget(scroll, 1)


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
        self.displayed_tracks: list[Track] = []
        self.seek_is_dragging = False
        self.current_track: Optional[Track] = None
        self.current_track_index: int = -1
        
        # Image loaders and cache
        self.image_cache: dict[str, QPixmap] = {}
        self.pending_images: dict[str, list] = {}
        self.active_loaders: list[ImageLoader] = []
        
        # Playback state
        self.shuffle_enabled = False
        self.repeat_mode = 0
        self.favorites: set[str] = set()
        self._prev_volume = 60
        
        self.current_view = "home"
        self.artists: dict[str, list[Track]] = {}

        self.setWindowTitle("Music Player")
        self.resize(1400, 900)
        self.setMinimumSize(1100, 700)

        root = QWidget()
        self.setCentralWidget(root)
        
        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        content_area = QHBoxLayout()
        content_area.setContentsMargins(0, 0, 0, 0)
        content_area.setSpacing(0)
        
        content_area.addWidget(self._create_sidebar())
        content_area.addWidget(self._create_main_content(), 1)
        content_area.addWidget(self._create_now_playing_panel())
        
        main_layout.addLayout(content_area, 1)
        main_layout.addWidget(self._create_player_bar())

        vol = int(self.settings.get("player/volume", 60))
        self.player.audio.setVolume(vol / 100)
        self._prev_volume = vol

        self.player.player.positionChanged.connect(self._on_position_changed)
        self.player.player.durationChanged.connect(self._on_duration_changed)
        self.player.player.mediaStatusChanged.connect(self._on_media_status_changed)

        self._apply_global_styles()
        self._load_favorites()

    def closeEvent(self, event):
        # Stop all image loaders
        for loader in self.active_loaders:
            loader.stop()
            loader.quit()
            loader.wait(1000)
        super().closeEvent(event)

    def _load_favorites(self):
        if "Favorites" in self.playlists:
            self.favorites = set(self.playlists["Favorites"])

    def _save_favorites(self):
        self.playlists["Favorites"] = list(self.favorites)
        self.playlist_service.save(self.playlists)

    def _apply_global_styles(self):
        self.setStyleSheet(f"""
            QMainWindow {{
                background: {SpotifyColors.BLACK};
            }}
            QWidget {{
                font-family: 'Segoe UI', 'SF Pro Display', -apple-system, sans-serif;
            }}
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255,255,255,0.3);
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(255,255,255,0.5);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)

    def _create_sidebar(self):
        sidebar = QFrame()
        sidebar.setFixedWidth(280)
        sidebar.setStyleSheet(f"background: {SpotifyColors.BLACK};")
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Nav panel
        nav_panel = QFrame()
        nav_panel.setStyleSheet(f"background: {SpotifyColors.DARK_BASE}; border-radius: 8px;")
        nav_layout = QVBoxLayout(nav_panel)
        nav_layout.setContentsMargins(12, 12, 12, 12)
        nav_layout.setSpacing(4)
        
        self.home_item = SidebarItem("home", "Home", self._show_home, active=True)
        self.search_item = SidebarItem("search", "Search", self._show_search)
        
        nav_layout.addWidget(self.home_item)
        nav_layout.addWidget(self.search_item)
        
        # Library panel
        library_panel = QFrame()
        library_panel.setStyleSheet(f"background: {SpotifyColors.DARK_BASE}; border-radius: 8px;")
        library_layout = QVBoxLayout(library_panel)
        library_layout.setContentsMargins(0, 0, 0, 0)
        library_layout.setSpacing(0)
        
        lib_header = QHBoxLayout()
        lib_header.setContentsMargins(12, 12, 12, 12)
        
        lib_icon = QLabel()
        lib_icon.setPixmap(Icons.pixmap("library", 24, SpotifyColors.SUBDUED))
        
        lib_title = QLabel("Your Library")
        lib_title.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 14px; font-weight: 700;")
        lib_title.setCursor(Qt.PointingHandCursor)
        lib_title.mousePressEvent = lambda e: self._show_library()
        
        add_btn = IconButton("plus", 32, 16, bg_hover=SpotifyColors.DARK_HIGHLIGHT)
        add_btn.clicked.connect(self._create_playlist)
        
        lib_header.addWidget(lib_icon)
        lib_header.addWidget(lib_title)
        lib_header.addStretch()
        lib_header.addWidget(add_btn)
        library_layout.addLayout(lib_header)
        
        # Filter chips
        chips_layout = QHBoxLayout()
        chips_layout.setContentsMargins(12, 0, 12, 12)
        chips_layout.setSpacing(8)
        
        for text in ["Playlists", "Artists", "Albums"]:
            chip = QPushButton(text)
            chip.setCursor(Qt.PointingHandCursor)
            chip.setStyleSheet(f"""
                QPushButton {{
                    background: {SpotifyColors.DARK_HIGHLIGHT};
                    border: none;
                    color: {SpotifyColors.WHITE};
                    border-radius: 14px;
                    padding: 6px 12px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background: {SpotifyColors.DARK_PRESS};
                }}
            """)
            chips_layout.addWidget(chip)
        chips_layout.addStretch()
        library_layout.addLayout(chips_layout)
        
        # Playlists
        playlist_scroll = QScrollArea()
        playlist_scroll.setWidgetResizable(True)
        playlist_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.playlist_container = QWidget()
        self.playlist_layout = QVBoxLayout(self.playlist_container)
        self.playlist_layout.setContentsMargins(8, 0, 8, 8)
        self.playlist_layout.setSpacing(2)
        self._update_sidebar_playlists()
        
        playlist_scroll.setWidget(self.playlist_container)
        library_layout.addWidget(playlist_scroll, 1)
        
        layout.addWidget(nav_panel)
        layout.addSpacing(8)
        layout.addWidget(library_panel, 1)
        layout.addSpacing(8)
        
        return sidebar

    def _update_sidebar_playlists(self):
        while self.playlist_layout.count():
            child = self.playlist_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        playlist_names = list(self.playlists.keys()) if self.playlists else []
        
        liked = self._create_sidebar_playlist_item("Liked Songs", len(self.favorites), is_liked=True)
        self.playlist_layout.addWidget(liked)
        
        for name in playlist_names:
            if name != "Favorites":
                item = self._create_sidebar_playlist_item(name, len(self.playlists.get(name, [])))
                self.playlist_layout.addWidget(item)
        
        self.playlist_layout.addStretch()

    def _create_sidebar_playlist_item(self, name: str, count: int, is_liked: bool = False):
        item = QFrame()
        item.setFixedHeight(64)
        item.setCursor(Qt.PointingHandCursor)
        item.setStyleSheet(f"""
            QFrame {{
                background: transparent;
                border-radius: 4px;
            }}
            QFrame:hover {{
                background: {SpotifyColors.DARK_HIGHLIGHT};
            }}
        """)
        
        layout = QHBoxLayout(item)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        
        cover = QLabel()
        cover.setFixedSize(48, 48)
        cover.setAlignment(Qt.AlignCenter)
        
        if is_liked:
            cover.setPixmap(Icons.pixmap("heart", 24, SpotifyColors.WHITE))
            cover.setStyleSheet(f"""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #450af5, stop:1 #c4efd9);
                border-radius: 4px;
            """)
        else:
            cover.setPixmap(Icons.pixmap("music_note", 24, SpotifyColors.SUBDUED))
            cover.setStyleSheet(f"""
                background: {SpotifyColors.DARK_HIGHLIGHT};
                border-radius: 4px;
            """)
        
        info = QVBoxLayout()
        info.setSpacing(2)
        
        title = QLabel(name)
        title.setStyleSheet(f"color: {SpotifyColors.WHITE}; font-size: 14px; background: transparent;")
        
        subtitle = QLabel(f"Playlist - {count} songs")
        subtitle.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 12px; background: transparent;")
        
        info.addWidget(title)
        info.addWidget(subtitle)
        
        layout.addWidget(cover)
        layout.addLayout(info, 1)
        
        def click_handler(event, n=name, liked=is_liked):
            if liked:
                self._show_favorites()
            else:
                self._show_playlist(n)
        
        item.mousePressEvent = click_handler
        
        return item

    def _create_main_content(self):
        container = QFrame()
        container.setStyleSheet(f"background: {SpotifyColors.DARK_BASE}; border-radius: 8px;")
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        header = self._create_header()
        layout.addWidget(header)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(24, 16, 24, 24)
        self.content_layout.setSpacing(32)
        
        self._build_home_view()
        
        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll, 1)
        
        return container

    def _create_header(self):
        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet("background: transparent;")
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 16, 24, 0)
        layout.setSpacing(16)
        
        self.back_btn = IconButton("back", 32, 14, bg="rgba(0,0,0,0.7)", bg_hover="rgba(0,0,0,0.9)")
        self.forward_btn = IconButton("forward", 32, 14, bg="rgba(0,0,0,0.7)", bg_hover="rgba(0,0,0,0.9)")
        
        self.back_btn.clicked.connect(self._navigate_back)
        self.forward_btn.clicked.connect(self._navigate_forward)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("What do you want to listen to?")
        self.search_input.setFixedHeight(40)
        self.search_input.setMinimumWidth(350)
        self.search_input.textChanged.connect(self._on_search)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background: {SpotifyColors.WHITE};
                border: none;
                border-radius: 20px;
                padding: 8px 16px 8px 40px;
                color: {SpotifyColors.BLACK};
                font-size: 14px;
            }}
        """)
        
        layout.addWidget(self.back_btn)
        layout.addWidget(self.forward_btn)
        layout.addSpacing(8)
        layout.addWidget(self.search_input)
        layout.addStretch()
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setCursor(Qt.PointingHandCursor)
        self.connect_btn.clicked.connect(self._connect_server)
        self.connect_btn.setStyleSheet(f"""
            QPushButton {{
                background: {SpotifyColors.WHITE};
                color: {SpotifyColors.BLACK};
                border: none;
                border-radius: 16px;
                padding: 8px 24px;
                font-size: 13px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: #f0f0f0;
            }}
        """)
        
        settings_btn = IconButton("settings", 32, 16, bg="rgba(0,0,0,0.7)", bg_hover="rgba(0,0,0,0.9)")
        settings_btn.clicked.connect(self._open_settings)
        
        layout.addWidget(self.connect_btn)
        layout.addWidget(settings_btn)
        
        return header

    def _build_home_view(self):
        self._clear_content()
        
        greeting = self._get_greeting()
        greeting_label = QLabel(greeting)
        greeting_label.setStyleSheet(f"color: {SpotifyColors.WHITE}; font-size: 32px; font-weight: 700;")
        self.content_layout.addWidget(greeting_label)
        
        self.quick_cards_grid = QGridLayout()
        self.quick_cards_grid.setSpacing(16)
        self._update_quick_cards()
        self.content_layout.addLayout(self.quick_cards_grid)
        
        self._add_section("Made For You", self._get_made_for_you())
        self._add_section("Recently Played", self._get_recently_played())
        
        if self.tracks:
            self._add_tracks_section("All Tracks", self.tracks[:20])
        
        self.content_layout.addStretch()

    def _get_greeting(self):
        from datetime import datetime
        hour = datetime.now().hour
        if hour < 12:
            return "Good morning"
        elif hour < 18:
            return "Good afternoon"
        else:
            return "Good evening"

    def _update_quick_cards(self):
        while self.quick_cards_grid.count():
            child = self.quick_cards_grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        items = []
        items.append(("Liked Songs", len(self.favorites), True))
        
        for name in list(self.playlists.keys())[:5]:
            if name != "Favorites":
                items.append((name, len(self.playlists.get(name, [])), False))
        
        while len(items) < 6:
            items.append((f"Mix {len(items)+1}", 0, False))
        
        for i, (name, count, is_liked) in enumerate(items[:6]):
            def make_click_handler(n, liked):
                def handler(playlist_name):
                    if liked:
                        self._show_favorites()
                    else:
                        self._show_playlist(n)
                return handler
            
            card = PlaylistCard(name, on_click=make_click_handler(name, is_liked))
            row = i // 3
            col = i % 3
            self.quick_cards_grid.addWidget(card, row, col)

    def _add_section(self, title: str, items: list):
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        header = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {SpotifyColors.WHITE}; font-size: 24px; font-weight: 700;")
        
        show_all = QPushButton("Show all")
        show_all.setCursor(Qt.PointingHandCursor)
        show_all.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {SpotifyColors.SUBDUED};
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                color: {SpotifyColors.WHITE};
                text-decoration: underline;
            }}
        """)
        
        header.addWidget(title_label)
        header.addStretch()
        header.addWidget(show_all)
        layout.addLayout(header)
        
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(24)
        
        for item in items[:5]:
            card = AlbumCard(
                item.get("title", ""),
                item.get("subtitle", ""),
                on_click=lambda t, s: self._on_card_click(t, s),
                is_artist=item.get("is_artist", False)
            )
            cards_layout.addWidget(card)
        
        cards_layout.addStretch()
        layout.addLayout(cards_layout)
        
        self.content_layout.addWidget(section)

    def _add_tracks_section(self, title: str, tracks: list[Track]):
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        if title:
            header = QHBoxLayout()
            title_label = QLabel(title)
            title_label.setStyleSheet(f"color: {SpotifyColors.WHITE}; font-size: 24px; font-weight: 700;")
            
            play_btn = QPushButton("Play All")
            play_btn.setCursor(Qt.PointingHandCursor)
            play_btn.clicked.connect(lambda: self._play_all(tracks))
            play_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {SpotifyColors.GREEN};
                    border: none;
                    color: {SpotifyColors.BLACK};
                    border-radius: 20px;
                    padding: 10px 24px;
                    font-size: 14px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background: {SpotifyColors.GREEN_HOVER};
                }}
            """)
            
            header.addWidget(title_label)
            header.addStretch()
            header.addWidget(play_btn)
            layout.addLayout(header)
        
        # Column headers
        col_header = QHBoxLayout()
        col_header.setContentsMargins(16, 0, 16, 0)
        col_header.setSpacing(16)
        
        num_label = QLabel("#")
        num_label.setFixedWidth(24)
        num_label.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 12px;")
        
        title_h = QLabel("TITLE")
        title_h.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 12px; font-weight: 600;")
        
        album_h = QLabel("ALBUM")
        album_h.setFixedWidth(200)
        album_h.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 12px; font-weight: 600;")
        
        clock_label = QLabel()
        clock_label.setPixmap(Icons.pixmap("clock", 14, SpotifyColors.SUBDUED))
        clock_label.setFixedWidth(50)
        clock_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        col_header.addWidget(num_label)
        col_header.addSpacing(56)
        col_header.addWidget(title_h, 1)
        col_header.addWidget(album_h)
        col_header.addSpacing(32)
        col_header.addWidget(clock_label)
        col_header.addSpacing(32)
        
        layout.addLayout(col_header)
        
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {SpotifyColors.DARK_HIGHLIGHT};")
        layout.addWidget(sep)
        
        for i, track in enumerate(tracks):
            is_playing = self.current_track and self.current_track.id == track.id
            is_fav = track.id in self.favorites
            
            row = TrackRow(
                i, track,
                is_playing=is_playing,
                is_favorite=is_fav,
                on_play=self._play_track,
                on_favorite=self._toggle_favorite,
                on_add_playlist=self._add_to_playlist
            )
            layout.addWidget(row)
            
            if track.cover_art and self.client:
                url = self.client.cover_art_url(track.cover_art, 80)
                self._load_image(url, row, "set_cover", 40)
        
        self.content_layout.addWidget(section)

    def _get_made_for_you(self):
        return [
            {"title": "Daily Mix 1", "subtitle": "Based on your listening"},
            {"title": "Discover Weekly", "subtitle": "Your weekly mixtape"},
            {"title": "Release Radar", "subtitle": "New music for you"},
            {"title": "Time Capsule", "subtitle": "Throwback tracks"},
            {"title": "On Repeat", "subtitle": "Songs you love"},
        ]

    def _get_recently_played(self):
        if not self.tracks:
            return [
                {"title": "Liked Songs", "subtitle": "Playlist"},
                {"title": "My Playlist #1", "subtitle": "Playlist"},
            ]
        
        artists = {}
        for t in self.tracks[:20]:
            if t.artist not in artists:
                artists[t.artist] = t
        
        return [
            {"title": artist, "subtitle": "Artist", "is_artist": True}
            for artist in list(artists.keys())[:5]
        ]

    def _clear_content(self):
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())

    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())

    def _create_now_playing_panel(self):
        panel = QFrame()
        panel.setFixedWidth(320)
        panel.setStyleSheet(f"background: {SpotifyColors.DARK_BASE}; border-radius: 8px;")
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        header = QHBoxLayout()
        self.np_title = QLabel("Now Playing")
        self.np_title.setStyleSheet(f"color: {SpotifyColors.WHITE}; font-size: 14px; font-weight: 700;")
        
        close_btn = IconButton("close", 24, 12)
        
        header.addWidget(self.np_title)
        header.addStretch()
        header.addWidget(close_btn)
        layout.addLayout(header)
        
        # Large cover
        self.large_cover = QLabel()
        self.large_cover.setFixedSize(288, 288)
        self.large_cover.setAlignment(Qt.AlignCenter)
        self.large_cover.setPixmap(Icons.pixmap("music_note", 80, SpotifyColors.SUBDUED))
        self.large_cover.setStyleSheet(f"""
            background: {SpotifyColors.DARK_HIGHLIGHT};
            border-radius: 8px;
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.large_cover.setGraphicsEffect(shadow)
        
        layout.addWidget(self.large_cover)
        
        # Track info
        info_layout = QHBoxLayout()
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        self.np_track_title = QLabel("No track playing")
        self.np_track_title.setStyleSheet(f"color: {SpotifyColors.WHITE}; font-size: 20px; font-weight: 700;")
        self.np_track_title.setWordWrap(True)
        
        self.np_artist = QLabel("Connect to server")
        self.np_artist.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 14px;")
        self.np_artist.setWordWrap(True)
        self.np_artist.setCursor(Qt.PointingHandCursor)
        
        text_layout.addWidget(self.np_track_title)
        text_layout.addWidget(self.np_artist)
        
        self.np_fav_btn = IconButton("heart_outline", 32, 18)
        self.np_fav_btn.clicked.connect(self._toggle_current_favorite)
        
        info_layout.addLayout(text_layout, 1)
        info_layout.addWidget(self.np_fav_btn, alignment=Qt.AlignTop)
        layout.addLayout(info_layout)
        
        # Artist section
        artist_header = QLabel("About the artist")
        artist_header.setStyleSheet(f"color: {SpotifyColors.WHITE}; font-size: 16px; font-weight: 700;")
        layout.addWidget(artist_header)
        
        self.artist_card = QFrame()
        self.artist_card.setStyleSheet(f"background: {SpotifyColors.DARK_HIGHLIGHT}; border-radius: 8px;")
        artist_layout = QVBoxLayout(self.artist_card)
        artist_layout.setContentsMargins(16, 16, 16, 16)
        artist_layout.setSpacing(12)
        
        self.artist_avatar = QLabel()
        self.artist_avatar.setFixedSize(80, 80)
        self.artist_avatar.setAlignment(Qt.AlignCenter)
        self.artist_avatar.setPixmap(Icons.pixmap("user", 40, SpotifyColors.SUBDUED))
        self.artist_avatar.setStyleSheet(f"""
            background: {SpotifyColors.DARK_PRESS};
            border-radius: 40px;
        """)
        
        self.artist_name = QLabel("Artist")
        self.artist_name.setStyleSheet(f"color: {SpotifyColors.WHITE}; font-size: 16px; font-weight: 700;")
        
        self.artist_followers = QLabel("View artist")
        self.artist_followers.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 12px;")
        
        artist_layout.addWidget(self.artist_avatar, alignment=Qt.AlignCenter)
        artist_layout.addWidget(self.artist_name, alignment=Qt.AlignCenter)
        artist_layout.addWidget(self.artist_followers, alignment=Qt.AlignCenter)
        
        self.artist_card.setCursor(Qt.PointingHandCursor)
        self.artist_card.mousePressEvent = lambda e: self._show_artist(self.artist_name.text())
        
        layout.addWidget(self.artist_card)
        layout.addStretch()
        
        scroll.setWidget(content)
        
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addWidget(scroll)
        
        return panel

    def _create_player_bar(self):
        bar = QFrame()
        bar.setFixedHeight(90)
        bar.setStyleSheet(f"background: {SpotifyColors.BLACK}; border-top: 1px solid {SpotifyColors.DARK_HIGHLIGHT};")
        
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(0)
        
        # Left: Current track
        left = QHBoxLayout()
        left.setSpacing(12)
        
        self.mini_cover = QLabel()
        self.mini_cover.setFixedSize(56, 56)
        self.mini_cover.setAlignment(Qt.AlignCenter)
        self.mini_cover.setPixmap(Icons.pixmap("music_note", 28, SpotifyColors.SUBDUED))
        self.mini_cover.setStyleSheet(f"background: {SpotifyColors.DARK_HIGHLIGHT}; border-radius: 4px;")
        
        track_info = QVBoxLayout()
        track_info.setSpacing(2)
        
        self.mini_title = QLabel("No track")
        self.mini_title.setStyleSheet(f"color: {SpotifyColors.WHITE}; font-size: 14px;")
        self.mini_title.setCursor(Qt.PointingHandCursor)
        
        self.mini_artist = QLabel("Connect to server")
        self.mini_artist.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 12px;")
        self.mini_artist.setCursor(Qt.PointingHandCursor)
        
        track_info.addWidget(self.mini_title)
        track_info.addWidget(self.mini_artist)
        
        self.mini_fav = IconButton("heart_outline", 32, 16)
        self.mini_fav.clicked.connect(self._toggle_current_favorite)
        
        left.addWidget(self.mini_cover)
        left.addLayout(track_info)
        left.addWidget(self.mini_fav)
        
        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setFixedWidth(300)
        
        # Center: Controls
        center = QVBoxLayout()
        center.setSpacing(8)
        
        controls = QHBoxLayout()
        controls.setAlignment(Qt.AlignCenter)
        controls.setSpacing(20)
        
        self.shuffle_btn = IconButton("shuffle", 32, 16)
        self.shuffle_btn.clicked.connect(self._toggle_shuffle)
        
        self.prev_btn = IconButton("prev", 32, 18)
        self.prev_btn.clicked.connect(self._play_previous)
        
        self.play_btn = IconButton("play", 40, 18, SpotifyColors.BLACK, SpotifyColors.BLACK,
                                    SpotifyColors.WHITE, "#f0f0f0")
        self.play_btn.clicked.connect(self._toggle_playback)
        
        self.next_btn = IconButton("next", 32, 18)
        self.next_btn.clicked.connect(self._play_next)
        
        self.repeat_btn = IconButton("repeat", 32, 16)
        self.repeat_btn.clicked.connect(self._toggle_repeat)
        
        controls.addWidget(self.shuffle_btn)
        controls.addWidget(self.prev_btn)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.next_btn)
        controls.addWidget(self.repeat_btn)
        
        center.addLayout(controls)
        
        # Progress
        progress = QHBoxLayout()
        progress.setSpacing(12)
        
        self.time_current = QLabel("0:00")
        self.time_current.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 11px;")
        self.time_current.setFixedWidth(40)
        self.time_current.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.setFixedWidth(400)
        self.seek_slider.sliderPressed.connect(lambda: setattr(self, "seek_is_dragging", True))
        self.seek_slider.sliderReleased.connect(self._seek_to)
        self.seek_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {SpotifyColors.DARK_PRESS};
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {SpotifyColors.WHITE};
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }}
            QSlider::sub-page:horizontal {{
                background: {SpotifyColors.WHITE};
                border-radius: 2px;
            }}
            QSlider:hover QSlider::sub-page:horizontal {{
                background: {SpotifyColors.GREEN};
            }}
        """)
        
        self.time_total = QLabel("0:00")
        self.time_total.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 11px;")
        self.time_total.setFixedWidth(40)
        
        progress.addStretch()
        progress.addWidget(self.time_current)
        progress.addWidget(self.seek_slider)
        progress.addWidget(self.time_total)
        progress.addStretch()
        
        center.addLayout(progress)
        
        # Right: Volume
        right = QHBoxLayout()
        right.setAlignment(Qt.AlignRight)
        right.setSpacing(8)
        
        queue_btn = IconButton("queue", 32, 16)
        queue_btn.setToolTip("Queue")
        queue_btn.clicked.connect(self._show_queue)
        
        self.volume_btn = IconButton("volume_high", 32, 16)
        self.volume_btn.clicked.connect(self._toggle_mute)
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(self.settings.get("player/volume", 60)))
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        self.volume_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {SpotifyColors.DARK_PRESS};
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {SpotifyColors.WHITE};
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }}
            QSlider::sub-page:horizontal {{
                background: {SpotifyColors.WHITE};
                border-radius: 2px;
            }}
        """)
        
        fs_btn = IconButton("fullscreen", 32, 16)
        fs_btn.clicked.connect(self._toggle_fullscreen)
        
        right.addWidget(queue_btn)
        right.addWidget(self.volume_btn)
        right.addWidget(self.volume_slider)
        right.addWidget(fs_btn)
        
        right_widget = QWidget()
        right_widget.setLayout(right)
        right_widget.setFixedWidth(250)
        
        layout.addWidget(left_widget)
        layout.addLayout(center, 1)
        layout.addWidget(right_widget)
        
        return bar

    # ========== Image Loading ==========
    
    def _load_image(self, url: str, widget, method: str, size: int = 300):
        if not url:
            return
        
        if url in self.image_cache:
            getattr(widget, method)(self.image_cache[url])
            return
        
        if url in self.pending_images:
            self.pending_images[url].append((widget, method))
            return
        
        self.pending_images[url] = [(widget, method)]
        
        loader = ImageLoader(url, size)
        loader.finished.connect(self._on_image_loaded)
        self.active_loaders.append(loader)
        loader.start()

    def _on_image_loaded(self, url: str, pixmap: QPixmap):
        if pixmap.isNull():
            return
        
        self.image_cache[url] = pixmap
        
        if url in self.pending_images:
            for widget, method in self.pending_images[url]:
                try:
                    getattr(widget, method)(pixmap)
                except Exception:
                    pass
            del self.pending_images[url]

    # ========== Navigation ==========
    
    def _show_home(self):
        self.current_view = "home"
        self.home_item.setActive(True)
        self.search_item.setActive(False)
        self._build_home_view()

    def _show_search(self):
        self.current_view = "search"
        self.home_item.setActive(False)
        self.search_item.setActive(True)
        self._clear_content()
        
        placeholder = QLabel("Search for artists, songs, or albums")
        placeholder.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 18px;")
        placeholder.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(placeholder)
        self.content_layout.addStretch()

    def _show_library(self):
        self.current_view = "library"
        self._clear_content()
        
        title = QLabel("Your Library")
        title.setStyleSheet(f"color: {SpotifyColors.WHITE}; font-size: 32px; font-weight: 700;")
        self.content_layout.addWidget(title)
        
        if self.tracks:
            self._add_tracks_section("All Songs", self.tracks)
        
        self.content_layout.addStretch()

    def _show_favorites(self):
        self.current_view = "favorites"
        self._clear_content()
        
        header = QFrame()
        header.setFixedHeight(200)
        header.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                stop:0 #5038a0, stop:1 {SpotifyColors.DARK_BASE});
            border-radius: 8px;
        """)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 24, 24, 24)
        header_layout.setSpacing(24)
        
        cover = QLabel()
        cover.setFixedSize(160, 160)
        cover.setAlignment(Qt.AlignCenter)
        cover.setPixmap(Icons.pixmap("heart", 60, SpotifyColors.WHITE))
        cover.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #450af5, stop:1 #c4efd9);
            border-radius: 4px;
        """)
        
        info = QVBoxLayout()
        info.setSpacing(8)
        
        playlist_label = QLabel("PLAYLIST")
        playlist_label.setStyleSheet(f"color: {SpotifyColors.WHITE}; font-size: 12px; font-weight: 700;")
        
        title = QLabel("Liked Songs")
        title.setStyleSheet(f"color: {SpotifyColors.WHITE}; font-size: 48px; font-weight: 900;")
        
        count = QLabel(f"{len(self.favorites)} songs")
        count.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 14px;")
        
        info.addStretch()
        info.addWidget(playlist_label)
        info.addWidget(title)
        info.addWidget(count)
        info.addStretch()
        
        header_layout.addWidget(cover)
        header_layout.addLayout(info, 1)
        
        self.content_layout.addWidget(header)
        
        fav_tracks = [t for t in self.tracks if t.id in self.favorites] if self.tracks else []
        if fav_tracks:
            self._add_tracks_section("", fav_tracks)
        else:
            empty = QLabel("Songs you like will appear here")
            empty.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 16px;")
            empty.setAlignment(Qt.AlignCenter)
            self.content_layout.addWidget(empty)
        
        self.content_layout.addStretch()

    def _show_playlist(self, name: str):
        self.current_view = f"playlist:{name}"
        self._clear_content()
        
        header = QFrame()
        header.setFixedHeight(200)
        header.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                stop:0 #535353, stop:1 {SpotifyColors.DARK_BASE});
        """)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 24, 24, 24)
        header_layout.setSpacing(24)
        
        cover = QLabel()
        cover.setFixedSize(160, 160)
        cover.setAlignment(Qt.AlignCenter)
        cover.setPixmap(Icons.pixmap("music_note", 60, SpotifyColors.SUBDUED))
        cover.setStyleSheet(f"""
            background: {SpotifyColors.DARK_HIGHLIGHT};
            border-radius: 4px;
        """)
        
        info = QVBoxLayout()
        info.setSpacing(8)
        
        playlist_label = QLabel("PLAYLIST")
        playlist_label.setStyleSheet(f"color: {SpotifyColors.WHITE}; font-size: 12px; font-weight: 700;")
        
        title = QLabel(name)
        title.setStyleSheet(f"color: {SpotifyColors.WHITE}; font-size: 48px; font-weight: 900;")
        
        track_ids = self.playlists.get(name, [])
        count = QLabel(f"{len(track_ids)} songs")
        count.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 14px;")
        
        info.addStretch()
        info.addWidget(playlist_label)
        info.addWidget(title)
        info.addWidget(count)
        info.addStretch()
        
        header_layout.addWidget(cover)
        header_layout.addLayout(info, 1)
        
        self.content_layout.addWidget(header)
        
        playlist_tracks = [t for t in self.tracks if t.id in track_ids] if self.tracks else []
        if playlist_tracks:
            self.displayed_tracks = playlist_tracks
            self._add_tracks_section("", playlist_tracks)
        else:
            empty = QLabel("No songs in this playlist yet")
            empty.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 16px;")
            empty.setAlignment(Qt.AlignCenter)
            self.content_layout.addWidget(empty)
        
        self.content_layout.addStretch()

    def _show_artist(self, artist_name: str):
        self.current_view = f"artist:{artist_name}"
        self._clear_content()
        
        artist_tracks = [t for t in self.tracks if t.artist == artist_name] if self.tracks else []
        
        header = QFrame()
        header.setFixedHeight(280)
        header.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                stop:0 #404040, stop:1 {SpotifyColors.DARK_BASE});
        """)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 24, 24, 24)
        header_layout.setSpacing(24)
        header_layout.setAlignment(Qt.AlignBottom | Qt.AlignLeft)
        
        info = QVBoxLayout()
        
        verified = QHBoxLayout()
        check_icon = QLabel()
        check_icon.setPixmap(Icons.pixmap("check", 14, SpotifyColors.WHITE))
        verified_text = QLabel("Verified Artist")
        verified_text.setStyleSheet(f"color: {SpotifyColors.WHITE}; font-size: 12px;")
        verified.addWidget(check_icon)
        verified.addWidget(verified_text)
        verified.addStretch()
        
        name = QLabel(artist_name)
        name.setStyleSheet(f"color: {SpotifyColors.WHITE}; font-size: 64px; font-weight: 900;")
        
        listeners = QLabel(f"{len(artist_tracks)} songs in library")
        listeners.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 14px;")
        
        info.addStretch()
        info.addLayout(verified)
        info.addWidget(name)
        info.addWidget(listeners)
        
        header_layout.addLayout(info, 1)
        self.content_layout.addWidget(header)
        
        # Actions
        actions = QHBoxLayout()
        actions.setSpacing(16)
        
        play_btn = IconButton("play", 56, 24, SpotifyColors.BLACK, SpotifyColors.BLACK,
                               SpotifyColors.GREEN, SpotifyColors.GREEN_HOVER)
        play_btn.clicked.connect(lambda: self._play_all(artist_tracks))
        
        follow_btn = QPushButton("Follow")
        follow_btn.setCursor(Qt.PointingHandCursor)
        follow_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {SpotifyColors.SUBDUED};
                color: {SpotifyColors.WHITE};
                border-radius: 16px;
                padding: 8px 24px;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                border-color: {SpotifyColors.WHITE};
            }}
        """)
        
        actions.addWidget(play_btn)
        actions.addWidget(follow_btn)
        actions.addStretch()
        self.content_layout.addLayout(actions)
        
        if artist_tracks:
            self.displayed_tracks = artist_tracks
            self._add_tracks_section("Popular", artist_tracks[:10])
        
        self.content_layout.addStretch()

    def _on_card_click(self, title: str, subtitle: str):
        if subtitle == "Artist" or "Artist" in subtitle:
            self._show_artist(title)

    def _navigate_back(self):
        pass

    def _navigate_forward(self):
        pass

    def _on_search(self, text: str):
        if self.current_view != "search":
            return
        
        q = text.lower().strip()
        self._clear_content()
        
        if not q:
            placeholder = QLabel("Search for artists, songs, or albums")
            placeholder.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 18px;")
            placeholder.setAlignment(Qt.AlignCenter)
            self.content_layout.addWidget(placeholder)
            self.content_layout.addStretch()
            return
        
        if not self.tracks:
            no_results = QLabel("Connect to server first")
            no_results.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 18px;")
            no_results.setAlignment(Qt.AlignCenter)
            self.content_layout.addWidget(no_results)
            self.content_layout.addStretch()
            return
        
        filtered = [t for t in self.tracks if q in f"{t.title} {t.artist} {t.album}".lower()]
        
        if filtered:
            self._add_tracks_section(f"Results for \"{text}\"", filtered)
        else:
            no_results = QLabel(f"No results found for \"{text}\"")
            no_results.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 18px;")
            no_results.setAlignment(Qt.AlignCenter)
            self.content_layout.addWidget(no_results)
        
        self.content_layout.addStretch()

    # ========== Playback ==========
    
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

    def _on_media_status_changed(self, status):
        from PySide6.QtMultimedia import QMediaPlayer
        if status == QMediaPlayer.EndOfMedia:
            if self.repeat_mode == 2:
                self.player.player.setPosition(0)
                self.player.player.play()
            else:
                self._play_next()

    def _seek_to(self):
        self.seek_is_dragging = False
        self.player.player.setPosition(self.seek_slider.value())

    def _on_volume_changed(self, value: int):
        self.player.audio.setVolume(value / 100)
        self._update_volume_icon()

    def _update_volume_icon(self):
        vol = self.volume_slider.value()
        if vol == 0:
            self.volume_btn.set_icon("volume_mute")
        elif vol < 50:
            self.volume_btn.set_icon("volume_low")
        else:
            self.volume_btn.set_icon("volume_high")

    def _toggle_mute(self):
        if self.volume_slider.value() > 0:
            self._prev_volume = self.volume_slider.value()
            self.volume_slider.setValue(0)
        else:
            self.volume_slider.setValue(self._prev_volume)

    def _toggle_playback(self):
        if self.player.player.playbackState().name == "PlayingState":
            self.player.pause()
            self.play_btn.set_icon("play")
        else:
            if self.current_track:
                self.player.player.play()
                self.play_btn.set_icon("pause")
            elif self.displayed_tracks:
                self._play_track(self.displayed_tracks[0])

    def _toggle_shuffle(self):
        self.shuffle_enabled = not self.shuffle_enabled
        self.shuffle_btn.set_active(self.shuffle_enabled)

    def _toggle_repeat(self):
        self.repeat_mode = (self.repeat_mode + 1) % 3
        if self.repeat_mode == 0:
            self.repeat_btn.set_icon("repeat")
            self.repeat_btn.set_active(False)
        elif self.repeat_mode == 1:
            self.repeat_btn.set_icon("repeat")
            self.repeat_btn.set_active(True)
        else:
            self.repeat_btn.set_icon("repeat_one")
            self.repeat_btn.set_active(True)

    def _play_previous(self):
        if not self.displayed_tracks:
            return
        
        if self.current_track_index > 0:
            self.current_track_index -= 1
        elif self.repeat_mode == 1:
            self.current_track_index = len(self.displayed_tracks) - 1
        else:
            return
        
        self._play_track(self.displayed_tracks[self.current_track_index])

    def _play_next(self):
        if not self.displayed_tracks:
            return
        
        if self.shuffle_enabled:
            self.current_track_index = random.randint(0, len(self.displayed_tracks) - 1)
        elif self.current_track_index < len(self.displayed_tracks) - 1:
            self.current_track_index += 1
        elif self.repeat_mode == 1:
            self.current_track_index = 0
        else:
            return
        
        self._play_track(self.displayed_tracks[self.current_track_index])

    def _play_track(self, track: Track):
        if not self.client:
            return
        
        self.current_track = track
        self.current_track_index = self.displayed_tracks.index(track) if track in self.displayed_tracks else 0
        
        self.player.play_url(self.client.stream_url(track.id))
        self.recommendation_service.register_play(track)
        
        self.np_track_title.setText(track.title)
        self.np_artist.setText(track.artist)
        self.mini_title.setText(track.title)
        self.mini_artist.setText(track.artist)
        self.artist_name.setText(track.artist)
        self.play_btn.set_icon("pause")
        
        self._update_favorite_ui()
        
        if track.cover_art:
            url = self.client.cover_art_url(track.cover_art, 300)
            self._load_image(url, self.large_cover, "setPixmap", 288)
            
            url_small = self.client.cover_art_url(track.cover_art, 100)
            self._load_image(url_small, self.mini_cover, "setPixmap", 56)

    def _play_all(self, tracks: list[Track]):
        if not tracks:
            return
        
        self.displayed_tracks = tracks
        
        if self.shuffle_enabled:
            self.current_track_index = random.randint(0, len(tracks) - 1)
        else:
            self.current_track_index = 0
        
        self._play_track(tracks[self.current_track_index])

    # ========== Favorites ==========
    
    def _toggle_favorite(self, track: Track):
        if track.id in self.favorites:
            self.favorites.discard(track.id)
        else:
            self.favorites.add(track.id)
        
        self._save_favorites()
        self._update_sidebar_playlists()
        
        if self.current_view == "favorites":
            self._show_favorites()

    def _toggle_current_favorite(self):
        if self.current_track:
            self._toggle_favorite(self.current_track)
            self._update_favorite_ui()

    def _update_favorite_ui(self):
        if self.current_track and self.current_track.id in self.favorites:
            self.mini_fav.set_icon("heart")
            self.mini_fav.set_active(True)
            self.np_fav_btn.set_icon("heart")
            self.np_fav_btn.set_active(True)
        else:
            self.mini_fav.set_icon("heart_outline")
            self.mini_fav.set_active(False)
            self.np_fav_btn.set_icon("heart_outline")
            self.np_fav_btn.set_active(False)

    def _add_to_playlist(self, track: Track):
        playlists = [p for p in self.playlists.keys() if p != "Favorites"]
        
        if not playlists:
            QMessageBox.information(self, "No Playlists", "Create a playlist first")
            return
        
        name, ok = QInputDialog.getItem(self, "Add to Playlist", "Select playlist:", playlists, 0, False)
        if ok and name:
            if track.id not in self.playlists[name]:
                self.playlists[name].append(track.id)
                self.playlist_service.save(self.playlists)
                self._update_sidebar_playlists()

    # ========== Server ==========
    
    def _open_settings(self):
        d = SettingsDialog(self.settings, self)
        if d.exec():
            d.persist()

    def _connect_server(self):
        url = str(self.settings.get("server/url", "http://localhost:4533"))
        user = str(self.settings.get("server/user", ""))
        password = str(self.settings.get("server/password", ""))
        
        self.client = SubsonicClient(ServerConfig(url, user, password))
        try:
            self.client.ping()
            self._load_tracks()
            self.connect_btn.setText("Connected")
            self.connect_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {SpotifyColors.GREEN};
                    color: {SpotifyColors.BLACK};
                    border: none;
                    border-radius: 16px;
                    padding: 8px 24px;
                    font-size: 13px;
                    font-weight: 700;
                }}
            """)
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))

    def _load_tracks(self):
        if not self.client:
            return
        
        self.tracks = self.client.get_tracks(500)
        self.displayed_tracks = self.tracks
        
        self.artists = {}
        for t in self.tracks:
            if t.artist not in self.artists:
                self.artists[t.artist] = []
            self.artists[t.artist].append(t)
        
        self._build_home_view()
        self._update_sidebar_playlists()
        self._update_quick_cards()

    def _create_playlist(self):
        name, ok = QInputDialog.getText(self, "New Playlist", "Playlist name:")
        if ok and name.strip():
            self.playlists[name.strip()] = []
            self.playlist_service.save(self.playlists)
            self._update_sidebar_playlists()
            self._update_quick_cards()

    def _show_queue(self):
        if self.displayed_tracks:
            dialog = QueueDialog(
                self.displayed_tracks, 
                self.current_track_index,
                on_select=lambda i: self._play_track(self.displayed_tracks[i]),
                parent=self
            )
            dialog.exec()

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
