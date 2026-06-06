"""Fire button — burn your browsing data with style."""

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


class FireParticle:
    """A single fire particle for the burn animation."""

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-4, -1)
        self.life = 1.0
        self.decay = random.uniform(0.02, 0.05)
        self.size = random.uniform(3, 8)
        self.color_phase = random.uniform(0, 1)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy -= 0.05
        self.life -= self.decay
        self.size *= 0.97

    @property
    def alive(self) -> bool:
        return self.life > 0

    @property
    def color(self) -> QColor:
        if self.color_phase < 0.3:
            return QColor(255, 60, 20, int(255 * self.life))
        elif self.color_phase < 0.6:
            return QColor(255, 140, 0, int(255 * self.life))
        else:
            return QColor(255, 220, 50, int(255 * self.life))


class FireButton(QWidget):
    """The Orbio fire button — clear browsing data with animation."""

    burn_15min = pyqtSignal()
    burn_1hour = pyqtSignal()
    burn_session = pyqtSignal()
    burn_everything = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

        self._hover = False
        self._burning = False
        self._particles: list[FireParticle] = []
        self._burn_progress = 0.0

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate)

        self._pulse_value = 0.0
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse)
        self._pulse_timer.start(50)
        self._pulse_dir = 1

    def _pulse(self):
        if self._hover and not self._burning:
            self._pulse_value += 0.08 * self._pulse_dir
            if self._pulse_value >= 1.0:
                self._pulse_dir = -1
            elif self._pulse_value <= 0.0:
                self._pulse_dir = 1
            self.update()

    def start_burn(self):
        """Trigger the fire animation."""
        self._burning = True
        self._burn_progress = 0.0
        self._particles.clear()
        self._anim_timer.start(30)

    def _animate(self):
        """Update fire particles."""
        self._burn_progress += 0.03

        # Spawn new particles during the first 60% of animation
        if self._burn_progress < 0.6:
            cx = self.width() / 2
            cy = self.height() / 2
            for _ in range(3):
                self._particles.append(
                    FireParticle(cx + random.uniform(-8, 8),
                               cy + random.uniform(-4, 4))
                )

        # Update existing particles
        self._particles = [p for p in self._particles if p.alive]
        for p in self._particles:
            p.update()

        # End animation
        if self._burn_progress >= 1.0 and not self._particles:
            self._burning = False
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

        # Draw fire particles behind the button
        for p in self._particles:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(p.color))
            painter.drawEllipse(QPointF(p.x, p.y), p.size, p.size)

        # Button circle
        if self._burning:
            glow_color = QColor(255, 100, 0, 120)
            border_color = QColor(255, 80, 20)
            fill = QColor(60, 15, 5)
        elif self._hover:
            intensity = int(60 + 60 * self._pulse_value)
            glow_color = QColor(255, 80, 0, intensity)
            border_color = QColor(255, 100, 30)
            fill = QColor(40, 12, 5)
        else:
            glow_color = QColor(0, 0, 0, 0)
            border_color = QColor("#3a2a2a")
            fill = QColor("#1a1215")

        # Glow
        if glow_color.alpha() > 0:
            grad = QRadialGradient(cx, cy, radius + 6)
            grad.setColorAt(0, glow_color)
            grad.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(cx, cy), radius + 6, radius + 6)

        # Main circle
        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(border_color, 1.5))
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        # Fire icon (flame shape)
        self._draw_flame_icon(painter, cx, cy)

        painter.end()

    def _draw_flame_icon(self, painter: QPainter, cx: float, cy: float):
        """Draw a simple flame icon."""
        path = QPainterPath()
        path.moveTo(cx, cy - 10)
        path.cubicTo(cx - 4, cy - 6, cx - 6, cy - 2, cx - 5, cy + 2)
        path.cubicTo(cx - 4, cy + 5, cx - 2, cy + 7, cx, cy + 8)
        path.cubicTo(cx + 2, cy + 7, cx + 4, cy + 5, cx + 5, cy + 2)
        path.cubicTo(cx + 6, cy - 2, cx + 4, cy - 6, cx, cy - 10)

        if self._burning:
            flame_color = QColor(255, 200, 50)
        elif self._hover:
            flame_color = QColor(255, 120, 40)
        else:
            flame_color = QColor("#ff4444")

        painter.setBrush(QBrush(flame_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)

        # Inner flame
        inner = QPainterPath()
        inner.moveTo(cx, cy - 5)
        inner.cubicTo(cx - 2, cy - 2, cx - 3, cy, cx - 2, cy + 3)
        inner.cubicTo(cx - 1, cy + 5, cx + 1, cy + 5, cx + 2, cy + 3)
        inner.cubicTo(cx + 3, cy, cx + 2, cy - 2, cx, cy - 5)

        inner_color = QColor(255, 240, 100) if self._burning else QColor(255, 180, 60)
        painter.setBrush(QBrush(inner_color))
        painter.drawPath(inner)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._show_burn_menu()

    def enterEvent(self, event):
        self._hover = True
        self._pulse_value = 0.0
        self._pulse_dir = 1
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def _show_burn_menu(self):
        """Show the burn options context menu."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #12121a;
                color: #e8e8f0;
                border: 1px solid #2a2a3a;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #ff4444;
                color: white;
            }
        """)

        a15 = menu.addAction("Last 15 minutes")
        a1h = menu.addAction("Last hour")
        asess = menu.addAction("This session")
        menu.addSeparator()
        aall = menu.addAction("Everything")

        action = menu.exec(self.mapToGlobal(QPointF(0, self.height()).toPoint()))

        if action == a15:
            self.start_burn()
            self.burn_15min.emit()
        elif action == a1h:
            self.start_burn()
            self.burn_1hour.emit()
        elif action == asess:
            self.start_burn()
            self.burn_session.emit()
        elif action == aall:
            self.start_burn()
            self.burn_everything.emit()
