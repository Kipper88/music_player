"""
Демонстрационное desktop-приложение на PySide6.

Идея интерфейса:
- Трёхколоночный layout в стиле стримингового сервиса (как на эскизе).
- Левая узкая панель навигации.
- Центральная область: поиск, фильтры, карточки плейлистов.
- Правая панель: подробности выбранного трека/исполнителя.
- Нижний фиксированный mini-player с базовыми кнопками управления.

Важно:
Это UI-прототип. Реальные запросы к Navidrome/Subsonic API здесь не выполняются,
но структура кода уже подготовлена для дальнейшей интеграции.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import List

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


# --- МОДЕЛИ ДАННЫХ -----------------------------------------------------------


@dataclass
class PlaylistCardData:
    """Модель данных для карточки плейлиста/альбома в центральной колонке."""

    title: str
    subtitle: str
    accent: str


@dataclass
class TrackInfo:
    """Модель данных для нижнего плеера и правой инфо-панели."""

    title: str
    artist: str
    album: str
    duration: str


# --- ВСПОМОГАТЕЛЬНЫЕ WIDGETS ------------------------------------------------


class SideNavButton(QPushButton):
    """
    Кнопка в левой вертикальной панели.

    Почему отдельный класс:
    - единая стилизация;
    - компактное переиспользование;
    - проще модифицировать активное/неактивное состояние в одном месте.
    """

    def __init__(self, icon_text: str, tooltip: str = "") -> None:
        super().__init__(icon_text)
        self.setToolTip(tooltip)
        self.setFixedSize(54, 54)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            """
            QPushButton {
                background-color: #1a1d23;
                color: #d7dce7;
                border: 1px solid #2c313d;
                border-radius: 14px;
                font-size: 20px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #222733;
                border: 1px solid #3a4152;
            }
            """
        )


class PlaylistCard(QFrame):
    """Визуальная карточка плейлиста: цветной квадрат + заголовок + подзаголовок."""

    def __init__(self, data: PlaylistCardData) -> None:
        super().__init__()
        self.setObjectName("playlistCard")
        self.setStyleSheet(
            """
            QFrame#playlistCard {
                background-color: #181c24;
                border: 1px solid #252b36;
                border-radius: 12px;
            }
            QFrame#playlistCard:hover {
                background-color: #202636;
                border: 1px solid #354056;
            }
            """
        )

        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(12)

        cover = QFrame()
        cover.setFixedSize(62, 62)
        cover.setStyleSheet(
            f"background-color: {data.accent}; border-radius: 8px; border: none;"
        )

        txt_wrap = QVBoxLayout()
        txt_wrap.setSpacing(4)

        title = QLabel(data.title)
        title.setStyleSheet("color: #f7faff; font-size: 18px; font-weight: 700;")

        subtitle = QLabel(data.subtitle)
        subtitle.setStyleSheet("color: #9ba6b6; font-size: 13px;")

        txt_wrap.addWidget(title)
        txt_wrap.addWidget(subtitle)

        root.addWidget(cover)
        root.addLayout(txt_wrap)


class TagPill(QPushButton):
    """Небольшая кнопка-фильтр (All / Music / Podcasts ...)."""

    def __init__(self, text: str, active: bool = False) -> None:
        super().__init__(text)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(36)
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {'#eef3ff' if active else '#242a35'};
                color: {'#121722' if active else '#d6ddeb'};
                border: 1px solid {'#eef3ff' if active else '#374153'};
                border-radius: 18px;
                padding: 0 14px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {'#ffffff' if active else '#2d3544'};
            }}
            """
        )


# --- ГЛАВНОЕ ОКНО ------------------------------------------------------------


class MusicWindow(QMainWindow):
    """Основное окно приложения."""

    def __init__(self) -> None:
        super().__init__()

        # Базовые window-параметры.
        self.setWindowTitle("Navidrome Desktop Player (PySide6)")
        self.resize(1450, 900)
        self.setMinimumSize(1200, 760)

        # Условные данные (временная заглушка).
        self.current_track = TrackInfo(
            title="МОЙ БАТЯ",
            artist="Полароид",
            album="Daily Mix 2",
            duration="1:58",
        )

        # Корневой контейнер.
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # Верхняя/центральная рабочая зона + нижний плеер.
        root.addWidget(self._build_workspace(), stretch=1)
        root.addWidget(self._build_bottom_player(), stretch=0)

        # Общий фон (тёмная тема в духе эскиза).
        self.setStyleSheet("QMainWindow { background-color: #0b0e13; }")

    def _build_workspace(self) -> QWidget:
        """Создаёт верхнюю часть: 3-колоночный layout (left / center / right)."""
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(self._build_left_sidebar(), stretch=0)
        layout.addWidget(self._build_center_column(), stretch=1)
        layout.addWidget(self._build_right_info_panel(), stretch=0)

        return wrapper

    def _build_left_sidebar(self) -> QWidget:
        """Левая колонка: иконки разделов/библиотеки."""
        panel = QFrame()
        panel.setFixedWidth(86)
        panel.setStyleSheet(
            """
            QFrame {
                background-color: #0f131b;
                border: 1px solid #1f2632;
                border-radius: 16px;
            }
            """
        )

        col = QVBoxLayout(panel)
        col.setContentsMargins(14, 14, 14, 14)
        col.setSpacing(12)

        col.addWidget(SideNavButton("⌂", "Главная"))
        col.addWidget(SideNavButton("🔍", "Поиск"))
        col.addWidget(SideNavButton("❤", "Избранное"))
        col.addWidget(SideNavButton("🎵", "Плейлисты"))
        col.addWidget(SideNavButton("📚", "Библиотека"))

        col.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        profile = SideNavButton("И")
        profile.setStyleSheet(
            """
            QPushButton {
                background-color: #4c8dff;
                color: #ffffff;
                border: none;
                border-radius: 27px;
                font-size: 18px;
                font-weight: 800;
            }
            QPushButton:hover { background-color: #5b97ff; }
            """
        )
        col.addWidget(profile)

        return panel

    def _build_center_column(self) -> QWidget:
        """Центральная часть: поиск, фильтры, сетка карточек."""
        panel = QFrame()
        panel.setStyleSheet(
            """
            QFrame {
                background-color: #10151f;
                border: 1px solid #1e2735;
                border-radius: 16px;
            }
            """
        )

        root = QVBoxLayout(panel)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        # Верхняя строка: кнопка home + поиск + action.
        top = QHBoxLayout()
        top.setSpacing(10)

        home_btn = QPushButton("⌂")
        home_btn.setFixedSize(44, 44)
        home_btn.setStyleSheet(
            "background-color:#232a38; color:#e5ebf7; border:none; border-radius:22px; font-size:20px;"
        )

        search = QLineEdit()
        search.setPlaceholderText("Что вы хотите включить?")
        search.setFixedHeight(44)
        search.setStyleSheet(
            """
            QLineEdit {
                background-color:#1a202d;
                color:#f5f8ff;
                border:1px solid #303a4f;
                border-radius:22px;
                padding:0 16px;
                font-size:15px;
            }
            """
        )

        action_btn = QPushButton("☰")
        action_btn.setFixedSize(44, 44)
        action_btn.setStyleSheet(
            "background-color:#232a38; color:#e5ebf7; border:none; border-radius:22px; font-size:20px;"
        )

        top.addWidget(home_btn)
        top.addWidget(search, stretch=1)
        top.addWidget(action_btn)

        root.addLayout(top)

        # Теги-фильтры.
        tags = QHBoxLayout()
        tags.setSpacing(8)
        tags.addWidget(TagPill("All", active=True))
        tags.addWidget(TagPill("Music"))
        tags.addWidget(TagPill("Podcasts"))
        tags.addWidget(TagPill("Audiobooks"))
        tags.addStretch(1)
        root.addLayout(tags)

        # Область скролла с карточками.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(16)

        # Секция "быстрый доступ".
        hero = QLabel("Популярное у ваших друзей")
        hero.setStyleSheet("color:#f2f6ff; font-size:30px; font-weight:800;")
        body.addWidget(hero)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        demo_data: List[PlaylistCardData] = [
            PlaylistCardData("Daily Mix 2", "Подборка для вас", "#8a9611"),
            PlaylistCardData("Liked Songs", "Избранные треки", "#7357ff"),
            PlaylistCardData("KSB music Radio", "Радио", "#16a085"),
            PlaylistCardData("Как испортить вечеринку?", "Плейлист", "#8899aa"),
            PlaylistCardData("The Best of Korn", "Громко и тяжело", "#63666e"),
            PlaylistCardData("ЕБАНЬКО Radio", "Подкасты", "#9f5cc1"),
            PlaylistCardData("Против царя", "Альбом", "#9d2f2f"),
            PlaylistCardData("New Noise", "Исполнитель", "#c7a85f"),
        ]

        for i, item in enumerate(demo_data):
            row, col = divmod(i, 4)
            grid.addWidget(PlaylistCard(item), row, col)

        body.addLayout(grid)

        # Дополнительная секция, чтобы экран выглядел "живее" и был похож на эскиз.
        section = QLabel("Сделано для Ивана")
        section.setStyleSheet("color:#f2f6ff; font-size:26px; font-weight:800;")
        body.addWidget(section)

        row_albums = QHBoxLayout()
        row_albums.setSpacing(12)
        for name, color in [
            ("ellie's sketchbook", "#357abd"),
            ("Hazbin Hotel Covers!", "#b84bc2"),
            ("Danny's Cafe", "#4b4b4b"),
            ("KYLEHASASTYLE", "#801515"),
            ("Ellie's Imagination", "#8f79a9"),
        ]:
            card = QFrame()
            card.setFixedWidth(190)
            card.setStyleSheet(
                "background-color:#121722; border:1px solid #263143; border-radius:12px;"
            )
            c = QVBoxLayout(card)
            c.setContentsMargins(8, 8, 8, 8)
            cover = QFrame()
            cover.setMinimumHeight(130)
            cover.setStyleSheet(f"background-color:{color}; border-radius:8px;")
            lbl = QLabel(name)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color:#ecf2ff; font-size:16px; font-weight:700;")
            c.addWidget(cover)
            c.addWidget(lbl)
            row_albums.addWidget(card)

        row_albums.addStretch(1)
        body.addLayout(row_albums)

        body.addStretch(1)

        scroll.setWidget(content)
        root.addWidget(scroll)

        return panel

    def _build_right_info_panel(self) -> QWidget:
        """Правая узкая колонка: большая обложка + текущий трек + credits."""
        panel = QFrame()
        panel.setFixedWidth(360)
        panel.setStyleSheet(
            """
            QFrame {
                background-color: #10141d;
                border: 1px solid #1e2634;
                border-radius: 16px;
            }
            """
        )

        root = QVBoxLayout(panel)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        title = QLabel("Daily Mix 2")
        title.setStyleSheet("color:#f3f7ff; font-size:38px; font-weight:800;")

        cover = QFrame()
        cover.setMinimumHeight(470)
        cover.setStyleSheet("background-color:#313744; border-radius:14px;")

        track = QLabel(f"{self.current_track.title}\n{self.current_track.artist}")
        track.setStyleSheet("color:#f5f8ff; font-size:36px; font-weight:800;")

        credits_box = QFrame()
        credits_box.setStyleSheet("background-color:#141a25; border:1px solid #242f41; border-radius:12px;")
        credits_layout = QVBoxLayout(credits_box)
        credits_layout.setContentsMargins(12, 12, 12, 12)

        credits_title = QLabel("Credits")
        credits_title.setStyleSheet("color:#f5f8ff; font-size:22px; font-weight:700;")
        credits_artist = QLabel(f"{self.current_track.artist}\nMain Artist")
        credits_artist.setStyleSheet("color:#c8d2e3; font-size:18px;")

        credits_layout.addWidget(credits_title)
        credits_layout.addWidget(credits_artist)

        root.addWidget(title)
        root.addWidget(cover)
        root.addWidget(track)
        root.addWidget(credits_box)
        root.addStretch(1)

        return panel

    def _build_bottom_player(self) -> QWidget:
        """Нижняя панель-плеер: текущий трек, кнопки, прогресс-бар."""
        panel = QFrame()
        panel.setFixedHeight(105)
        panel.setStyleSheet(
            """
            QFrame {
                background-color: #090c11;
                border: 1px solid #182131;
                border-radius: 16px;
            }
            """
        )

        row = QHBoxLayout(panel)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(14)

        # Левый блок: трек + исполнитель.
        left = QVBoxLayout()
        now = QLabel(self.current_track.title)
        now.setStyleSheet("color:#eff4ff; font-size:24px; font-weight:800;")
        artist = QLabel(self.current_track.artist)
        artist.setStyleSheet("color:#98a3b5; font-size:16px;")
        left.addWidget(now)
        left.addWidget(artist)

        # Центр: кнопки управления и псевдо-прогресс.
        center = QVBoxLayout()
        controls = QHBoxLayout()
        controls.setSpacing(8)

        for txt in ("⤮", "⏮", "⏯", "⏭", "🔁"):
            btn = QPushButton(txt)
            btn.setFixedSize(40, 40)
            btn.setStyleSheet(
                "background-color:#1d2431; color:#e6edf9; border:none; border-radius:20px; font-size:17px;"
            )
            controls.addWidget(btn)

        controls_wrap = QWidget()
        controls_wrap.setLayout(controls)

        progress_track = QFrame()
        progress_track.setFixedHeight(8)
        progress_track.setStyleSheet("background-color:#30394b; border-radius:4px;")

        progress_fill = QFrame(progress_track)
        progress_fill.setGeometry(0, 0, 380, 8)
        progress_fill.setStyleSheet("background-color:#f0f4ff; border-radius:4px;")

        time_lbl = QLabel(f"0:20 / {self.current_track.duration}")
        time_lbl.setStyleSheet("color:#a9b4c5; font-size:13px;")
        time_lbl.setAlignment(Qt.AlignCenter)

        center.addWidget(controls_wrap, alignment=Qt.AlignCenter)
        center.addWidget(progress_track)
        center.addWidget(time_lbl)

        # Правый блок: заглушки доп. действий.
        right = QHBoxLayout()
        right.setSpacing(8)
        for icon in ("✎", "☰", "🖵", "🔊", "⛶"):
            b = QPushButton(icon)
            b.setFixedSize(34, 34)
            b.setStyleSheet(
                "background-color:#1a212e; color:#dce4f3; border:none; border-radius:17px; font-size:15px;"
            )
            right.addWidget(b)

        right_wrap = QWidget()
        right_wrap.setLayout(right)

        row.addLayout(left, stretch=1)
        row.addLayout(center, stretch=2)
        row.addWidget(right_wrap, stretch=0)

        return panel


def main() -> None:
    """
    Точка входа приложения.

    Важно для Windows:
    - PySide6 корректно работает с HiDPI, поэтому интерфейс должен выглядеть
      аккуратно на масштабах 125/150/200%.
    - В реальном приложении сюда удобно добавить чтение конфига (URL Navidrome,
      логин/пароль, токены), запуск инициализации API-клиента и восстановление
      последней сессии.
    """

    app = QApplication(sys.argv)

    # Шрифт интерфейса. На Windows Segoe UI обычно доступен "из коробки".
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MusicWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
