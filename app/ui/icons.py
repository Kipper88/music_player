import math
from functools import lru_cache

from PySide6.QtWidgets import (
    QApplication
)
from PySide6.QtGui import (
    QIcon, 
    QPixmap, 
    QPainter, 
    QPainterPath, 
    QPen, 
    QBrush, 
    QColor, 
    QPolygonF
)
from PySide6.QtCore import (
    Qt, 
    QPointF, 
    QRectF, 
    QSize
)

from app.ui.styles import SpotifyColors

class Icons:
    """SVG icons drawn with QPainter - cached"""
    
    @staticmethod
    @lru_cache(maxsize=100)
    def _create_icon(name: str, size: int, color: str) -> QIcon:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        pen = QPen(QColor(color))
        pen.setWidth(max(1, size // 12))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        
        brush = QBrush(QColor(color))
        
        margin = size * 0.2
        inner = size - 2 * margin
        
        cx, cy = size / 2, size / 2
        
        if name == "home":
            # House icon
            path = QPainterPath()
            # Roof
            path.moveTo(margin, cy)
            path.lineTo(cx, margin)
            path.lineTo(size - margin, cy)
            # Walls
            path.moveTo(margin + inner * 0.15, cy)
            path.lineTo(margin + inner * 0.15, size - margin)
            path.lineTo(size - margin - inner * 0.15, size - margin)
            path.lineTo(size - margin - inner * 0.15, cy)
            painter.drawPath(path)
            
        elif name == "search":
            # Magnifying glass
            r = inner * 0.35
            cx, cy = size * 0.42, size * 0.42
            painter.drawEllipse(QPointF(cx, cy), r, r)
            painter.drawLine(
                QPointF(cx + r * 0.7, cy + r * 0.7),
                QPointF(size - margin, size - margin)
            )
            
        elif name == "library":
            # Stack of books/lines
            y_start = margin + inner * 0.1
            y_end = size - margin - inner * 0.1
            x1 = margin + inner * 0.1
            x2 = size - margin - inner * 0.1
            for i in range(4):
                y = y_start + i * (y_end - y_start) / 3
                painter.drawLine(QPointF(x1, y), QPointF(x2, y))
                
        elif name == "play":
            # Play triangle
            painter.setPen(Qt.NoPen)
            painter.setBrush(brush)
            triangle = QPolygonF([
                QPointF(margin + inner * 0.2, margin),
                QPointF(size - margin, cy),
                QPointF(margin + inner * 0.2, size - margin)
            ])
            painter.drawPolygon(triangle)
            
        elif name == "pause":
            # Two vertical bars
            painter.setPen(Qt.NoPen)
            painter.setBrush(brush)
            bar_w = inner * 0.25
            painter.drawRect(QRectF(margin + inner * 0.15, margin, bar_w, inner))
            painter.drawRect(QRectF(size - margin - inner * 0.15 - bar_w, margin, bar_w, inner))
            
        elif name == "prev":
            # Previous track
            painter.setPen(Qt.NoPen)
            painter.setBrush(brush)
            # Bar
            painter.drawRect(QRectF(margin, margin + inner * 0.15, inner * 0.15, inner * 0.7))
            # Triangle
            triangle = QPolygonF([
                QPointF(size - margin, margin + inner * 0.1),
                QPointF(margin + inner * 0.25, cy),
                QPointF(size - margin, size - margin - inner * 0.1)
            ])
            painter.drawPolygon(triangle)
            
        elif name == "next":
            # Next track
            painter.setPen(Qt.NoPen)
            painter.setBrush(brush)
            # Bar
            painter.drawRect(QRectF(size - margin - inner * 0.15, margin + inner * 0.15, inner * 0.15, inner * 0.7))
            # Triangle
            triangle = QPolygonF([
                QPointF(margin, margin + inner * 0.1),
                QPointF(size - margin - inner * 0.25, cy),
                QPointF(margin, size - margin - inner * 0.1)
            ])
            painter.drawPolygon(triangle)
            
        elif name == "shuffle":
            # Crossed arrows
            y1 = margin + inner * 0.3
            y2 = size - margin - inner * 0.3
            painter.drawLine(QPointF(margin, y2), QPointF(size - margin - inner * 0.2, y1))
            painter.drawLine(QPointF(margin, y1), QPointF(size - margin - inner * 0.2, y2))
            # Arrow heads
            ah = inner * 0.15
            painter.drawLine(QPointF(size - margin, y1), QPointF(size - margin - ah, y1 - ah * 0.5))
            painter.drawLine(QPointF(size - margin, y1), QPointF(size - margin - ah, y1 + ah * 0.5))
            painter.drawLine(QPointF(size - margin, y2), QPointF(size - margin - ah, y2 - ah * 0.5))
            painter.drawLine(QPointF(size - margin, y2), QPointF(size - margin - ah, y2 + ah * 0.5))
            
        elif name == "repeat":
            # Repeat arrows
            r = inner * 0.35
            cx, cy = size / 2, size / 2
            painter.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2), 30 * 16, 280 * 16)
            # Arrow
            ah = inner * 0.12
            ax = cx + r * 0.85
            ay = cy - r * 0.5
            painter.drawLine(QPointF(ax, ay), QPointF(ax - ah, ay - ah))
            painter.drawLine(QPointF(ax, ay), QPointF(ax + ah, ay - ah))
            
        elif name == "repeat_one":
            # Repeat with 1
            r = inner * 0.35
            cx, cy = size / 2, size / 2
            painter.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2), 30 * 16, 280 * 16)
            # "1" in center
            painter.drawLine(QPointF(cx, cy - inner * 0.15), QPointF(cx, cy + inner * 0.15))
            
        elif name == "heart":
            # Heart shape
            painter.setPen(Qt.NoPen)
            painter.setBrush(brush)
            path = QPainterPath()
            cx, cy = size / 2, size / 2
            path.moveTo(cx, size - margin - inner * 0.1)
            path.cubicTo(margin, cy, margin, margin + inner * 0.2, cx, margin + inner * 0.35)
            path.cubicTo(size - margin, margin + inner * 0.2, size - margin, cy, cx, size - margin - inner * 0.1)
            painter.drawPath(path)
            
        elif name == "heart_outline":
            # Heart outline
            pen.setWidth(max(1, size // 14))
            painter.setPen(pen)
            path = QPainterPath()
            cx, cy = size / 2, size / 2
            path.moveTo(cx, size - margin - inner * 0.1)
            path.cubicTo(margin, cy, margin, margin + inner * 0.2, cx, margin + inner * 0.35)
            path.cubicTo(size - margin, margin + inner * 0.2, size - margin, cy, cx, size - margin - inner * 0.1)
            painter.drawPath(path)
            
        elif name == "volume_high":
            # Speaker with waves
            # Speaker body
            sw = inner * 0.25
            sh = inner * 0.4
            painter.setPen(Qt.NoPen)
            painter.setBrush(brush)
            painter.drawRect(QRectF(margin, cy - sh / 2, sw, sh))
            # Cone
            cone = QPolygonF([
                QPointF(margin + sw, cy - sh / 2),
                QPointF(margin + sw + inner * 0.2, cy - inner * 0.4),
                QPointF(margin + sw + inner * 0.2, cy + inner * 0.4),
                QPointF(margin + sw, cy + sh / 2)
            ])
            painter.drawPolygon(cone)
            # Waves
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            wave_x = margin + sw + inner * 0.35
            painter.drawArc(QRectF(wave_x, cy - inner * 0.15, inner * 0.2, inner * 0.3), -60 * 16, 120 * 16)
            painter.drawArc(QRectF(wave_x + inner * 0.1, cy - inner * 0.25, inner * 0.3, inner * 0.5), -60 * 16, 120 * 16)
            
        elif name == "volume_low":
            # Speaker with one wave
            sw = inner * 0.25
            sh = inner * 0.4
            painter.setPen(Qt.NoPen)
            painter.setBrush(brush)
            painter.drawRect(QRectF(margin, cy - sh / 2, sw, sh))
            cone = QPolygonF([
                QPointF(margin + sw, cy - sh / 2),
                QPointF(margin + sw + inner * 0.2, cy - inner * 0.4),
                QPointF(margin + sw + inner * 0.2, cy + inner * 0.4),
                QPointF(margin + sw, cy + sh / 2)
            ])
            painter.drawPolygon(cone)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            wave_x = margin + sw + inner * 0.35
            painter.drawArc(QRectF(wave_x, cy - inner * 0.15, inner * 0.2, inner * 0.3), -60 * 16, 120 * 16)
            
        elif name == "volume_mute":
            # Speaker with X
            sw = inner * 0.25
            sh = inner * 0.4
            painter.setPen(Qt.NoPen)
            painter.setBrush(brush)
            painter.drawRect(QRectF(margin, cy - sh / 2, sw, sh))
            cone = QPolygonF([
                QPointF(margin + sw, cy - sh / 2),
                QPointF(margin + sw + inner * 0.2, cy - inner * 0.4),
                QPointF(margin + sw + inner * 0.2, cy + inner * 0.4),
                QPointF(margin + sw, cy + sh / 2)
            ])
            painter.drawPolygon(cone)
            # X
            painter.setPen(pen)
            x_start = margin + sw + inner * 0.4
            painter.drawLine(QPointF(x_start, cy - inner * 0.2), QPointF(size - margin, cy + inner * 0.2))
            painter.drawLine(QPointF(x_start, cy + inner * 0.2), QPointF(size - margin, cy - inner * 0.2))
            
        elif name == "queue":
            # Three lines
            y1 = margin + inner * 0.2
            y2 = cy
            y3 = size - margin - inner * 0.2
            painter.drawLine(QPointF(margin, y1), QPointF(size - margin, y1))
            painter.drawLine(QPointF(margin, y2), QPointF(size - margin, y2))
            painter.drawLine(QPointF(margin, y3), QPointF(size - margin, y3))
            
        elif name == "fullscreen":
            # Four corners
            corner_len = inner * 0.3
            # Top-left
            painter.drawLine(QPointF(margin, margin + corner_len), QPointF(margin, margin))
            painter.drawLine(QPointF(margin, margin), QPointF(margin + corner_len, margin))
            # Top-right
            painter.drawLine(QPointF(size - margin - corner_len, margin), QPointF(size - margin, margin))
            painter.drawLine(QPointF(size - margin, margin), QPointF(size - margin, margin + corner_len))
            # Bottom-left
            painter.drawLine(QPointF(margin, size - margin - corner_len), QPointF(margin, size - margin))
            painter.drawLine(QPointF(margin, size - margin), QPointF(margin + corner_len, size - margin))
            # Bottom-right
            painter.drawLine(QPointF(size - margin - corner_len, size - margin), QPointF(size - margin, size - margin))
            painter.drawLine(QPointF(size - margin, size - margin), QPointF(size - margin, size - margin - corner_len))
            
        elif name == "plus":
            # Plus sign
            painter.drawLine(QPointF(cx, margin), QPointF(cx, size - margin))
            painter.drawLine(QPointF(margin, cy), QPointF(size - margin, cy))
            
        elif name == "settings":
            # Gear icon
            r_outer = inner * 0.45
            r_inner = inner * 0.25
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), r_inner, r_inner)
            # Teeth
            for i in range(6):
                import math
                angle = i * 60 * math.pi / 180
                x1 = cx + r_inner * 0.9 * math.cos(angle)
                y1 = cy + r_inner * 0.9 * math.sin(angle)
                x2 = cx + r_outer * math.cos(angle)
                y2 = cy + r_outer * math.sin(angle)
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
                
        elif name == "back":
            # Left arrow
            painter.drawLine(QPointF(size - margin - inner * 0.2, margin + inner * 0.2), QPointF(margin + inner * 0.2, cy))
            painter.drawLine(QPointF(margin + inner * 0.2, cy), QPointF(size - margin - inner * 0.2, size - margin - inner * 0.2))
            
        elif name == "forward":
            # Right arrow
            painter.drawLine(QPointF(margin + inner * 0.2, margin + inner * 0.2), QPointF(size - margin - inner * 0.2, cy))
            painter.drawLine(QPointF(size - margin - inner * 0.2, cy), QPointF(margin + inner * 0.2, size - margin - inner * 0.2))
            
        elif name == "music_note":
            # Music note
            painter.setPen(Qt.NoPen)
            painter.setBrush(brush)
            # Note head
            painter.drawEllipse(QPointF(margin + inner * 0.3, size - margin - inner * 0.2), inner * 0.2, inner * 0.15)
            # Stem
            pen.setWidth(max(1, size // 10))
            painter.setPen(pen)
            stem_x = margin + inner * 0.45
            painter.drawLine(QPointF(stem_x, size - margin - inner * 0.25), QPointF(stem_x, margin + inner * 0.2))
            # Flag
            painter.drawArc(QRectF(stem_x, margin + inner * 0.1, inner * 0.3, inner * 0.3), 90 * 16, -180 * 16)
            
        elif name == "user":
            # User/person icon
            # Head
            head_r = inner * 0.22
            painter.drawEllipse(QPointF(cx, margin + head_r + inner * 0.05), head_r, head_r)
            # Body
            painter.drawArc(
                QRectF(margin + inner * 0.15, cy + inner * 0.1, inner * 0.7, inner * 0.6),
                0, 180 * 16
            )
            
        elif name == "more":
            # Three dots
            dot_r = inner * 0.08
            painter.setPen(Qt.NoPen)
            painter.setBrush(brush)
            painter.drawEllipse(QPointF(margin + inner * 0.2, cy), dot_r, dot_r)
            painter.drawEllipse(QPointF(cx, cy), dot_r, dot_r)
            painter.drawEllipse(QPointF(size - margin - inner * 0.2, cy), dot_r, dot_r)
            
        elif name == "close":
            # X
            painter.drawLine(QPointF(margin, margin), QPointF(size - margin, size - margin))
            painter.drawLine(QPointF(size - margin, margin), QPointF(margin, size - margin))
            
        elif name == "check":
            # Checkmark
            painter.drawLine(QPointF(margin + inner * 0.1, cy), QPointF(cx - inner * 0.1, size - margin - inner * 0.2))
            painter.drawLine(QPointF(cx - inner * 0.1, size - margin - inner * 0.2), QPointF(size - margin - inner * 0.1, margin + inner * 0.2))
        
        elif name == "clock":
            # Clock
            r = inner * 0.4
            painter.drawEllipse(QPointF(cx, cy), r, r)
            painter.drawLine(QPointF(cx, cy), QPointF(cx, cy - r * 0.6))
            painter.drawLine(QPointF(cx, cy), QPointF(cx + r * 0.4, cy + r * 0.2))
        
        painter.end()
        return QIcon(pixmap)
    
    @classmethod
    def get(cls, name: str, size: int = 24, color: str = SpotifyColors.SUBDUED) -> QIcon:
        return cls._create_icon(name, size, color)
    
    @classmethod
    def pixmap(cls, name: str, size: int = 24, color: str = SpotifyColors.SUBDUED) -> QPixmap:
        return cls.get(name, size, color).pixmap(QSize(size, size))