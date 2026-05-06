from typing import Callable  # Для аннотаций on_click: Callable
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, 
    QVBoxLayout, QWidget, QGraphicsDropShadowEffect, QMenu
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import (
    QPixmap, QPainter, QPainterPath, QColor, QIcon
)

# Импорты из твоего проекта
from app.ui.styles import SpotifyColors
from app.ui.icons import Icons
# Предполагается, что класс Track определен в моделях
from app.models.entities import Track

class IconButton(QPushButton):
    """Button with icon"""
    def __init__(self, icon_name: str, size: int = 32, icon_size: int = 18, 
                 color: str = SpotifyColors.SUBDUED, hover_color: str = SpotifyColors.WHITE,
                 bg: str = "transparent", bg_hover: str = None, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.icon_size = icon_size
        self.color = color
        self.hover_color = hover_color
        self._active_color = color
        
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setIcon(Icons.get(icon_name, icon_size, color))
        self.setIconSize(QSize(icon_size, icon_size))
        
        bg_hover = bg_hover or bg
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                border: none;
                border-radius: {size // 2}px;
            }}
            QPushButton:hover {{
                background: {bg_hover};
            }}
        """)
    
    def set_active(self, active: bool, active_color: str = None):
        active_color = active_color or SpotifyColors.GREEN
        self._active_color = active_color if active else self.color
        self.setIcon(Icons.get(self.icon_name, self.icon_size, self._active_color))
    
    def set_icon(self, icon_name: str):
        self.icon_name = icon_name
        self.setIcon(Icons.get(icon_name, self.icon_size, self._active_color))
    
    def enterEvent(self, event):
        self.setIcon(Icons.get(self.icon_name, self.icon_size, self.hover_color if self._active_color == self.color else self._active_color))
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self.setIcon(Icons.get(self.icon_name, self.icon_size, self._active_color))
        super().leaveEvent(event)


class SidebarItem(QFrame):
    """Sidebar navigation item"""
    def __init__(self, icon_name: str, text: str, on_click: Callable = None, active: bool = False, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.on_click = on_click
        self.active = active
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(16)
        
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        self._update_icon()
        
        self.text_label = QLabel(text)
        self.text_label.setStyleSheet(f"font-size: 14px; font-weight: 700; background: transparent;")
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.addStretch()
    
    def _update_style(self):
        color = SpotifyColors.WHITE if self.active else SpotifyColors.SUBDUED
        self.setStyleSheet(f"""
            QFrame {{
                background: transparent;
                border-radius: 4px;
            }}
            QFrame:hover {{
                background: {SpotifyColors.DARK_HIGHLIGHT};
            }}
            QLabel {{
                color: {color};
            }}
        """)
    
    def _update_icon(self):
        color = SpotifyColors.WHITE if self.active else SpotifyColors.SUBDUED
        self.icon_label.setPixmap(Icons.pixmap(self.icon_name, 24, color))
    
    def setActive(self, active: bool):
        self.active = active
        self._update_style()
        self._update_icon()
    
    def mousePressEvent(self, event):
        if self.on_click:
            self.on_click()
        super().mousePressEvent(event)


class PlaylistCard(QFrame):
    """Small horizontal playlist card"""
    def __init__(self, title: str, on_click: Callable = None, cover_url: str = None, parent=None):
        super().__init__(parent)
        self.title = title
        self.on_click = on_click
        self.cover_url = cover_url
        self.setFixedHeight(64)
        self.setMinimumWidth(200)
        self.setCursor(Qt.PointingHandCursor)
        
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(255,255,255,0.05);
                border-radius: 4px;
            }}
            QFrame:hover {{
                background: rgba(255,255,255,0.1);
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 16, 0)
        layout.setSpacing(16)
        
        # Cover image
        self.cover = QLabel()
        self.cover.setFixedSize(64, 64)
        self.cover.setAlignment(Qt.AlignCenter)
        self._set_placeholder_cover()
        
        # Title
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"""
            color: {SpotifyColors.WHITE};
            font-size: 14px;
            font-weight: 700;
            background: transparent;
        """)
        self.title_label.setWordWrap(True)
        
        # Play button
        self.play_btn = IconButton("play", 40, 16, SpotifyColors.BLACK, SpotifyColors.BLACK, 
                                    SpotifyColors.GREEN, SpotifyColors.GREEN_HOVER)
        self.play_btn.hide()
        
        layout.addWidget(self.cover)
        layout.addWidget(self.title_label, 1)
        layout.addWidget(self.play_btn)
    
    def _set_placeholder_cover(self):
        self.cover.setPixmap(Icons.pixmap("music_note", 32, SpotifyColors.SUBDUED))
        self.cover.setStyleSheet(f"""
            background: {SpotifyColors.DARK_HIGHLIGHT};
            border-radius: 4px 0 0 4px;
        """)
    
    def set_cover(self, pixmap: QPixmap):
        scaled = pixmap.scaled(64, 64, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self.cover.setPixmap(scaled)
        self.cover.setStyleSheet("border-radius: 4px 0 0 4px;")
    
    def enterEvent(self, event):
        self.play_btn.show()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self.play_btn.hide()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        if self.on_click:
            self.on_click(self.title)
        super().mousePressEvent(event)


class AlbumCard(QFrame):
    """Large album/artist card with hover play button"""
    def __init__(self, title: str, subtitle: str = "", on_click: Callable = None, 
                 cover_url: str = None, is_artist: bool = False, parent=None):
        super().__init__(parent)
        self.title_text = title
        self.subtitle_text = subtitle
        self.on_click = on_click
        self.cover_url = cover_url
        self.is_artist = is_artist
        self.setFixedSize(180, 260)
        self.setCursor(Qt.PointingHandCursor)
        
        self.setStyleSheet(f"""
            QFrame {{
                background: {SpotifyColors.DARK_ELEVATED};
                border-radius: 8px;
            }}
            QFrame:hover {{
                background: {SpotifyColors.DARK_HIGHLIGHT};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 16)
        layout.setSpacing(12)
        
        # Cover container
        cover_container = QWidget()
        cover_container.setFixedSize(156, 156)
        cover_layout = QVBoxLayout(cover_container)
        cover_layout.setContentsMargins(0, 0, 0, 0)
        
        # Album cover
        self.cover = QLabel()
        self.cover.setFixedSize(156, 156)
        self.cover.setAlignment(Qt.AlignCenter)
        self._set_placeholder_cover()
        
        cover_layout.addWidget(self.cover)
        
        # Play button overlay
        self.play_btn = IconButton("play", 48, 20, SpotifyColors.BLACK, SpotifyColors.BLACK,
                                    SpotifyColors.GREEN, SpotifyColors.GREEN_HOVER)
        self.play_btn.hide()
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.play_btn.setGraphicsEffect(shadow)
        
        layout.addWidget(cover_container)
        
        # Title
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"""
            color: {SpotifyColors.WHITE};
            font-size: 14px;
            font-weight: 700;
            background: transparent;
        """)
        self.title_label.setWordWrap(True)
        self.title_label.setMaximumHeight(40)
        
        # Subtitle
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet(f"""
            color: {SpotifyColors.TEXT_SECONDARY};
            font-size: 12px;
            background: transparent;
        """)
        self.subtitle_label.setWordWrap(True)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addStretch()
    
    def _set_placeholder_cover(self):
        border_radius = "78px" if self.is_artist else "4px"
        icon = "user" if self.is_artist else "music_note"
        self.cover.setPixmap(Icons.pixmap(icon, 64, SpotifyColors.SUBDUED))
        self.cover.setStyleSheet(f"""
            background: {SpotifyColors.DARK_HIGHLIGHT};
            border-radius: {border_radius};
        """)
    
    def set_cover(self, pixmap: QPixmap):
        if self.is_artist:
            size = 156
            scaled = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            
            rounded = QPixmap(size, size)
            rounded.fill(Qt.transparent)
            
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.Antialiasing)
            path = QPainterPath()
            path.addEllipse(0, 0, size, size)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, scaled)
            painter.end()
            
            self.cover.setPixmap(rounded)
            self.cover.setStyleSheet("background: transparent;")
        else:
            scaled = pixmap.scaled(156, 156, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.cover.setPixmap(scaled)
            self.cover.setStyleSheet("border-radius: 4px;")
    
    def enterEvent(self, event):
        self.play_btn.show()
        self.play_btn.raise_()
        self.play_btn.move(self.cover.x() + 96, self.cover.y() + 96)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self.play_btn.hide()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        if self.on_click:
            self.on_click(self.title_text, self.subtitle_text)
        super().mousePressEvent(event)



class TrackRow(QFrame):
    """Single track row"""
    def __init__(self, index: int, track: Track, is_playing: bool = False, 
                 is_favorite: bool = False, on_play: Callable = None,
                 on_favorite: Callable = None, on_add_playlist: Callable = None,
                 cover_url: str = None, parent=None):
        super().__init__(parent)
        self.track = track
        self.index = index
        self.on_play = on_play
        self.on_favorite = on_favorite
        self.on_add_playlist = on_add_playlist
        self.is_playing = is_playing
        self.is_favorite = is_favorite
        self.cover_url = cover_url
        
        self.setFixedHeight(56)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)
        
        # Track number / playing indicator
        self.number_label = QLabel()
        self.number_label.setFixedSize(24, 24)
        self.number_label.setAlignment(Qt.AlignCenter)
        self._update_number_display()
        
        # Cover art
        self.cover = QLabel()
        self.cover.setFixedSize(40, 40)
        self.cover.setPixmap(Icons.pixmap("music_note", 24, SpotifyColors.SUBDUED))
        self.cover.setStyleSheet(f"background: {SpotifyColors.DARK_HIGHLIGHT}; border-radius: 4px;")
        self.cover.setAlignment(Qt.AlignCenter)
        
        # Track info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        title_color = SpotifyColors.GREEN if is_playing else SpotifyColors.WHITE
        self.title_label = QLabel(track.title)
        self.title_label.setStyleSheet(f"color: {title_color}; font-size: 14px; background: transparent;")
        
        self.artist_label = QLabel(track.artist)
        self.artist_label.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 12px; background: transparent;")
        
        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.artist_label)
        
        # Album
        self.album_label = QLabel(track.album)
        self.album_label.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 14px; background: transparent;")
        self.album_label.setFixedWidth(200)
        
        # Favorite button
        self.fav_btn = IconButton("heart" if is_favorite else "heart_outline", 32, 16,
                                   SpotifyColors.GREEN if is_favorite else SpotifyColors.SUBDUED)
        self.fav_btn.clicked.connect(self._toggle_favorite)
        if not is_favorite:
            self.fav_btn.hide()
        
        # Duration
        self.duration_label = QLabel(track.pretty_duration)
        self.duration_label.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 14px; background: transparent;")
        self.duration_label.setFixedWidth(50)
        self.duration_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        # Menu button
        self.menu_btn = IconButton("more", 32, 16)
        self.menu_btn.clicked.connect(self._show_menu)
        self.menu_btn.hide()
        
        layout.addWidget(self.number_label)
        layout.addWidget(self.cover)
        layout.addLayout(info_layout, 1)
        layout.addWidget(self.album_label)
        layout.addWidget(self.fav_btn)
        layout.addWidget(self.duration_label)
        layout.addWidget(self.menu_btn)
    
    def _update_number_display(self):
        if self.is_playing:
            self.number_label.setPixmap(Icons.pixmap("play", 16, SpotifyColors.GREEN))
        else:
            self.number_label.setText(str(self.index + 1))
            self.number_label.setStyleSheet(f"color: {SpotifyColors.SUBDUED}; font-size: 14px; background: transparent;")
    
    def _update_style(self):
        bg = SpotifyColors.DARK_HIGHLIGHT if self.is_playing else "transparent"
        self.setStyleSheet(f"""
            QFrame {{
                background: {bg};
                border-radius: 4px;
            }}
            QFrame:hover {{
                background: {SpotifyColors.DARK_HIGHLIGHT};
            }}
        """)
    
    def set_cover(self, pixmap: QPixmap):
        scaled = pixmap.scaled(40, 40, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self.cover.setPixmap(scaled)
    
    def enterEvent(self, event):
        self.fav_btn.show()
        self.menu_btn.show()
        self.number_label.setPixmap(Icons.pixmap("play", 16, SpotifyColors.WHITE))
        self.number_label.setText("")
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        if not self.is_favorite:
            self.fav_btn.hide()
        self.menu_btn.hide()
        self._update_number_display()
        super().leaveEvent(event)
    
    def _toggle_favorite(self):
        if self.on_favorite:
            self.on_favorite(self.track)
    
    def _show_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {SpotifyColors.DARK_HIGHLIGHT};
                border: 1px solid {SpotifyColors.DARK_PRESS};
                border-radius: 4px;
                padding: 4px;
            }}
            QMenu::item {{
                color: {SpotifyColors.WHITE};
                padding: 8px 16px;
                border-radius: 2px;
            }}
            QMenu::item:selected {{
                background: {SpotifyColors.DARK_PRESS};
            }}
        """)
        
        menu.addAction("Add to playlist", lambda: self.on_add_playlist(self.track) if self.on_add_playlist else None)
        menu.addAction("Add to queue", lambda: None)
        menu.addSeparator()
        menu.addAction("Go to artist", lambda: None)
        menu.addAction("Go to album", lambda: None)
        
        menu.exec(self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomLeft()))
    
    def mouseDoubleClickEvent(self, event):
        if self.on_play:
            self.on_play(self.track)
        super().mouseDoubleClickEvent(event)