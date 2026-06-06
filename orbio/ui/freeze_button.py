"""Freeze button — frost your browsing data into oblivion."""

import math
import random
from PyQt6.QtWidgets import QWidget, QMenu, QApplication
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, pyqtSignal, QTimer, QPropertyAnimation,
    QEasingCurve, pyqtProperty
)
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QPainterPath,
    QRadialGradient, QFont, QMouseEvent, QAction
)


class FrostParticle:
    """A single frost/ice crystal particle for the freeze animation."""

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.vx = random.uniform(-1.5, 1.5)
        self.vy = random.uniform(-0.5, 1.5)
        self.life = 1.0
        self.decay = random.uniform(0.015, 0.04)
        self.size = random.uniform(2, 6)
        self.rotation = random.uniform(0, 360)
        self.rot_speed = random.uniform(-3, 3)
        self.crystal_type = random.choice(["flake", "shard", "dot"])

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.98
        self.vy *= 0.98
        self.life -= self.decay
        self.rotation += self.rot_speed

    @property
    def alive(self) -> bool:
        return self.life > 0

    @property
    def color(self) -> QColor:
        alpha = int(220 * self.life)
        if self.crystal_type == "flake":
            return QColor(200, 230, 255, alpha)
        elif self.crystal_type == "shard":
            return QColor(140, 200, 255, alpha)
        else:
            return QColor(220, 240, 255, alpha)


class FreezeButton(QWidget):
    """The Orbio freeze button — frost your browsing data."""

    freeze_15min = pyqtSignal()
    freeze_1hour = pyqtSignal()
    freeze_session = pyqtSignal()
    freeze_everything = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

        self._hover = False
        self._freezing = False
        self._particles: list[FrostParticle] = []
        self._freeze_progress = 0.0

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate)

        self._pulse_value = 0.0
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse)
        self._pulse_timer.start(50)
        self._pulse_dir = 1

    def _pulse(self):
        if self._hover and not self._freezing:
            self._pulse_value += 0.06 * self._pulse_dir
            if self._pulse_value >= 1.0:
                self._pulse_dir = -1
            elif self._pulse_value <= 0.0:
                self._pulse_dir = 1
            self.update()

    def start_freeze(self):
        """Trigger the frost animation."""
        self._freezing = True
        self._freeze_progress = 0.0
        self._particles.clear()
        self._anim_timer.start(30)

    def _animate(self):
        """Update frost particles."""
        self._freeze_progress += 0.025

        if self._freeze_progress < 0.7:
            cx = self.width() / 2
            cy = self.height() / 2
            for _ in range(2):
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(4, 14)
                px = cx + math.cos(angle) * dist
                py = cy + math.sin(angle) * dist
                self._particles.append(FrostParticle(px, py))

        self._particles = [p for p in self._particles if p.alive]
        for p in self._particles:
            p.update()

        if self._freeze_progress >= 1.0 and not self._particles:
            self._freezing = False
            self._anim_timer.stop()

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2
        cy = h / 2
        radius = 18

        # Draw frost particles
        for p in self._particles:
            painter.save()
            painter.translate(p.x, p.y)
            painter.rotate(p.rotation)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(p.color))

            if p.crystal_type == "flake":
                self._draw_snowflake(painter, p.size)
            elif p.crystal_type == "shard":
                self._draw_ice_shard(painter, p.size)
            else:
                painter.drawEllipse(QPointF(0, 0), p.size * 0.5, p.size * 0.5)

            painter.restore()

        # Button circle
        if self._freezing:
            glow_color = QColor(100, 200, 255, 140)
            border_color = QColor(120, 210, 255)
            fill = QColor(10, 30, 50)
        elif self._hover:
            intensity = int(50 + 70 * self._pulse_value)
            glow_color = QColor(80, 180, 240, intensity)
            border_color = QColor(100, 190, 250)
            fill = QColor(8, 20, 40)
        else:
            glow_color = QColor(0, 0, 0, 0)
            border_color = QColor("#2a3a4a")
            fill = QColor("#0e1a28")

        # Glow
        if glow_color.alpha() > 0:
            grad = QRadialGradient(cx, cy, radius + 8)
            grad.setColorAt(0, glow_color)
            grad.setColorAt(0.6, QColor(60, 160, 220, int(glow_color.alpha() * 0.3)))
            grad.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(cx, cy), radius + 8, radius + 8)

        # Main circle
        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(border_color, 1.5))
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        # Ice cube icon
        self._draw_ice_cube(painter, cx, cy)

        painter.end()

    def _draw_ice_cube(self, painter: QPainter, cx: float, cy: float):
        """Draw an ice cube icon."""
        if self._freezing:
            ice_color = QColor(180, 230, 255)
            edge_color = QColor(220, 245, 255)
        elif self._hover:
            ice_color = QColor(120, 200, 245)
            edge_color = QColor(160, 220, 255)
        else:
            ice_color = QColor(80, 160, 220)
            edge_color = QColor(120, 190, 240)

        s = 7.0

        # Front face (slightly transparent look)
        front = QPainterPath()
        front.moveTo(cx - s, cy - s * 0.3)
        front.lineTo(cx + s, cy - s * 0.3)
        front.lineTo(cx + s, cy + s)
        front.lineTo(cx - s, cy + s)
        front.closeSubpath()
        painter.setBrush(QBrush(QColor(ice_color.red(), ice_color.green(), ice_color.blue(), 160)))
        painter.setPen(QPen(edge_color, 1.0))
        painter.drawPath(front)

        # Top face (lighter)
        top = QPainterPath()
        top.moveTo(cx - s, cy - s * 0.3)
        top.lineTo(cx - s * 0.3, cy - s)
        top.lineTo(cx + s * 0.7, cy - s)
        top.lineTo(cx + s, cy - s * 0.3)
        top.closeSubpath()
        painter.setBrush(QBrush(QColor(edge_color.red(), edge_color.green(), edge_color.blue(), 140)))
        painter.drawPath(top)

        # Right face (darker)
        right = QPainterPath()
        right.moveTo(cx + s, cy - s * 0.3)
        right.lineTo(cx + s * 0.7, cy - s)
        right.lineTo(cx + s * 0.7, cy + s * 0.3)
        right.lineTo(cx + s, cy + s)
        right.closeSubpath()
        painter.setBrush(QBrush(QColor(ice_color.red() - 30, ice_color.green() - 20, ice_color.blue(), 140)))
        painter.drawPath(right)

        # Frost sparkle
        painter.setPen(QPen(QColor(255, 255, 255, 180), 1.5))
        painter.drawPoint(QPointF(cx - s * 0.4, cy - s * 0.6))
        painter.drawPoint(QPointF(cx + s * 0.2, cy - s * 0.1))

    def _draw_snowflake(self, painter: QPainter, size: float):
        """Draw a tiny snowflake shape."""
        painter.setPen(QPen(painter.brush().color(), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(6):
            angle = math.radians(i * 60)
            x2 = math.cos(angle) * size
            y2 = math.sin(angle) * size
            painter.drawLine(QPointF(0, 0), QPointF(x2, y2))

    def _draw_ice_shard(self, painter: QPainter, size: float):
        """Draw a small ice shard (diamond/crystal shape)."""
        path = QPainterPath()
        path.moveTo(0, -size)
        path.lineTo(size * 0.4, 0)
        path.lineTo(0, size * 0.7)
        path.lineTo(-size * 0.4, 0)
        path.closeSubpath()
        painter.drawPath(path)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._show_freeze_menu()

    def enterEvent(self, event):
        self._hover = True
        self._pulse_value = 0.0
        self._pulse_dir = 1
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def _show_freeze_menu(self):
        """Show the freeze options context menu."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0e1a28;
                color: #e8f0f8;
                border: 1px solid #2a4a6a;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #4da6ff;
                color: white;
            }
        """)

        a15 = menu.addAction("Frost last 15 minutes")
        a1h = menu.addAction("Frost last hour")
        asess = menu.addAction("Freeze this session")
        menu.addSeparator()
        aall = menu.addAction("Deep freeze everything")

        action = menu.exec(self.mapToGlobal(QPointF(0, self.height()).toPoint()))

        if action == a15:
            self.start_freeze()
            self.freeze_15min.emit()
        elif action == a1h:
            self.start_freeze()
            self.freeze_1hour.emit()
        elif action == asess:
            self.start_freeze()
            self.freeze_session.emit()
        elif action == aall:
            self.start_freeze()
            self.freeze_everything.emit()
