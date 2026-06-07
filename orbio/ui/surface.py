"""Surface — the new-tab page.

A frozen surface with ambient drifting particles, crystal tiles for
frequent sites, centered search bar with ice-crack aesthetic, and
privacy stats glowing faintly beneath.
"""

import math
import random
from datetime import datetime
from PyQt6.QtWidgets import QWidget, QLineEdit
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, pyqtSignal, QTimer, QSize
)
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QPainterPath,
    QLinearGradient, QRadialGradient, QFont, QFontMetrics, QMouseEvent
)


class AmbientParticle:
    """A slow-drifting frost particle for atmosphere."""

    def __init__(self, w: int, h: int):
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)
        self.vx = random.uniform(-0.3, 0.3)
        self.vy = random.uniform(-0.15, 0.15)
        self.size = random.uniform(1, 3)
        self.alpha = random.randint(20, 60)
        self.w = w
        self.h = h

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.x < 0:
            self.x = self.w
        elif self.x > self.w:
            self.x = 0
        if self.y < 0:
            self.y = self.h
        elif self.y > self.h:
            self.y = 0


class CrystalTile:
    """A frequently-visited site rendered as a crystal tile."""

    def __init__(self, url: str, title: str, visits: int, x: float, y: float, size: float):
        self.url = url
        self.title = title
        self.visits = visits
        self.x = x
        self.y = y
        self.size = size
        self.hover = False


class SurfacePage(QWidget):
    """The Surface new-tab page widget."""

    navigate_requested = pyqtSignal(str)
    search_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._particles: list[AmbientParticle] = []
        self._tiles: list[CrystalTile] = []
        self._hover_tile: int = -1
        self._show_greeting = True
        self._trackers_blocked = 0
        self._frequent_sites: list[dict] = []

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Search input
        self._search = QLineEdit(self)
        self._search.setPlaceholderText("Search or enter URL...")
        self._search.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._search.returnPressed.connect(self._on_search)
        self._search.setStyleSheet("""
            QLineEdit {
                background: rgba(10, 14, 24, 180);
                color: #e8f0ff;
                border: 1px solid rgba(77, 166, 255, 0.3);
                border-radius: 24px;
                padding: 14px 28px;
                font-size: 15px;
                font-family: "Inter";
                selection-background-color: #4da6ff;
            }
            QLineEdit:focus {
                border-color: rgba(77, 166, 255, 0.7);
                background: rgba(8, 12, 20, 220);
            }
        """)

        # Animation timer
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate)
        self._anim_timer.start(50)

        self._init_particles()

    def _init_particles(self):
        """Create ambient frost particles."""
        w = max(self.width(), 1200)
        h = max(self.height(), 800)
        self._particles = [AmbientParticle(w, h) for _ in range(50)]

    def set_frequent_sites(self, sites: list[dict]):
        """Update the crystal tiles from history data."""
        self._frequent_sites = sites[:8]
        self._rebuild_tiles()

    def set_trackers_blocked(self, count: int):
        """Update the privacy stat display."""
        self._trackers_blocked = count
        self.update()

    def set_show_greeting(self, show: bool):
        self._show_greeting = show
        self.update()

    def _rebuild_tiles(self):
        """Position crystal tiles in a centered grid."""
        self._tiles.clear()
        if not self._frequent_sites:
            return

        w = self.width()
        h = self.height()
        center_y = h * 0.62

        count = len(self._frequent_sites)
        cols = min(count, 4)
        rows = math.ceil(count / cols)

        tile_w = 130
        tile_h = 80
        gap = 16
        total_w = cols * tile_w + (cols - 1) * gap
        start_x = (w - total_w) / 2

        max_visits = max((s.get("visits", 1) for s in self._frequent_sites), default=1)

        for i, site in enumerate(self._frequent_sites):
            col = i % cols
            row = i // cols
            x = start_x + col * (tile_w + gap)
            y = center_y + row * (tile_h + gap)

            # Size varies with visit frequency
            ratio = site.get("visits", 1) / max(max_visits, 1)
            size = 0.8 + ratio * 0.4

            self._tiles.append(CrystalTile(
                url=site.get("url", ""),
                title=site.get("title", ""),
                visits=site.get("visits", 0),
                x=x, y=y, size=size
            ))

    def _animate(self):
        for particle in self._particles:
            particle.update()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # Deep dark background with subtle gradient
        bg_grad = QLinearGradient(0, 0, 0, h)
        bg_grad.setColorAt(0, QColor(6, 8, 16))
        bg_grad.setColorAt(0.5, QColor(8, 12, 22))
        bg_grad.setColorAt(1, QColor(4, 6, 12))
        p.fillRect(self.rect(), QBrush(bg_grad))

        # Ambient particles
        self._draw_particles(p)

        # Ice surface texture at center
        self._draw_surface_glow(p, w, h)

        # Greeting
        if self._show_greeting:
            self._draw_greeting(p, w, h)

        # Crystal tiles
        self._draw_tiles(p)

        # Privacy stats beneath surface
        self._draw_privacy_stats(p, w, h)

        p.end()

    def _draw_particles(self, p: QPainter):
        """Draw ambient frost particles."""
        p.setPen(Qt.PenStyle.NoPen)
        for particle in self._particles:
            p.setBrush(QBrush(QColor(180, 210, 255, particle.alpha)))
            p.drawEllipse(QPointF(particle.x, particle.y), particle.size, particle.size)

    def _draw_surface_glow(self, p: QPainter, w: int, h: int):
        """Draw the subtle frozen surface glow at center."""
        cx, cy = w / 2, h * 0.35

        # Large diffuse glow
        glow = QRadialGradient(cx, cy, w * 0.4)
        glow.setColorAt(0, QColor(20, 60, 100, 25))
        glow.setColorAt(0.5, QColor(10, 40, 80, 10))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(glow))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), w * 0.4, h * 0.3)

        # Ice crack lines
        p.setPen(QPen(QColor(40, 80, 120, 30), 0.5))
        angles = [15, 75, 135, 200, 260, 320]
        for angle in angles:
            rad = math.radians(angle)
            length = random.Random(angle).uniform(60, 150)
            x2 = cx + math.cos(rad) * length
            y2 = cy + math.sin(rad) * length * 0.5
            p.drawLine(QPointF(cx, cy), QPointF(x2, y2))

    def _draw_greeting(self, p: QPainter, w: int, h: int):
        """Draw time-based greeting."""
        hour = datetime.now().hour
        if hour < 6:
            greeting = "Quiet hours"
        elif hour < 12:
            greeting = "Good morning"
        elif hour < 17:
            greeting = "Good afternoon"
        elif hour < 21:
            greeting = "Good evening"
        else:
            greeting = "Night browsing"

        p.setFont(QFont("Inter", 22, QFont.Weight.Light))
        p.setPen(QPen(QColor(180, 200, 230, 180)))
        p.drawText(QRectF(0, h * 0.12, w, 40), Qt.AlignmentFlag.AlignCenter, greeting)

    def _draw_tiles(self, p: QPainter):
        """Draw crystal tiles for frequent sites."""
        for i, tile in enumerate(self._tiles):
            is_hover = (i == self._hover_tile)
            self._draw_crystal_tile(p, tile, is_hover)

    def _draw_crystal_tile(self, p: QPainter, tile: CrystalTile, hover: bool):
        """Draw a single crystal tile."""
        tw = int(120 * tile.size)
        th = int(70 * tile.size)
        rect = QRectF(tile.x, tile.y, tw, th)

        if hover:
            bg = QColor(20, 40, 60, 200)
            border = QColor(100, 200, 255)
            text_color = QColor(230, 245, 255)
        else:
            bg = QColor(12, 20, 32, 160)
            border = QColor(40, 70, 100, 150)
            text_color = QColor(160, 180, 210)

        # Tile body
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        p.setBrush(QBrush(bg))
        p.setPen(QPen(border, 1.5 if hover else 0.8))
        p.drawPath(path)

        # Hover glow
        if hover:
            glow = QRadialGradient(rect.center(), tw * 0.6)
            glow.setColorAt(0, QColor(77, 166, 255, 30))
            glow.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(glow))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(rect.adjusted(-4, -4, 4, 4), 12, 12)

        # Title
        p.setFont(QFont("Inter", 9))
        p.setPen(QPen(text_color))
        fm = QFontMetrics(QFont("Inter", 9))
        title = tile.title or tile.url
        elided = fm.elidedText(title, Qt.TextElideMode.ElideRight, tw - 16)
        p.drawText(rect.adjusted(8, 8, -8, -th * 0.4), Qt.AlignmentFlag.AlignLeft, elided)

        # Visit count
        p.setFont(QFont("Inter", 8))
        p.setPen(QPen(QColor(80, 120, 160)))
        p.drawText(rect.adjusted(8, th * 0.5, -8, -4),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
                   f"{tile.visits} visits")

    def _draw_privacy_stats(self, p: QPainter, w: int, h: int):
        """Draw subtle privacy stats near bottom."""
        if self._trackers_blocked <= 0:
            return

        p.setFont(QFont("Inter", 10))
        p.setPen(QPen(QColor(60, 120, 180, 120)))
        text = f"🛡 {self._trackers_blocked} trackers blocked this session"
        p.drawText(QRectF(0, h - 48, w, 24), Qt.AlignmentFlag.AlignCenter, text)

    def _on_search(self):
        text = self._search.text().strip()
        if text:
            self.search_requested.emit(text)
            self._search.clear()

    def _tile_hit_test(self, pos: QPointF) -> int:
        """Find which tile the cursor is over."""
        for i, tile in enumerate(self._tiles):
            tw = int(120 * tile.size)
            th = int(70 * tile.size)
            rect = QRectF(tile.x, tile.y, tw, th)
            if rect.contains(pos):
                return i
        return -1

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            idx = self._tile_hit_test(event.position())
            if idx >= 0:
                self.navigate_requested.emit(self._tiles[idx].url)

    def mouseMoveEvent(self, event):
        old = self._hover_tile
        self._hover_tile = self._tile_hit_test(event.position())
        if old != self._hover_tile:
            self.setCursor(Qt.CursorShape.PointingHandCursor if self._hover_tile >= 0
                          else Qt.CursorShape.ArrowCursor)
            self.update()

    def leaveEvent(self, event):
        self._hover_tile = -1
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()

        # Reposition search bar
        search_w = min(520, w - 80)
        self._search.setGeometry(
            int((w - search_w) / 2), int(h * 0.3),
            search_w, 48
        )

        # Reinit particles for new size
        for particle in self._particles:
            particle.w = w
            particle.h = h

        # Rebuild tiles for new layout
        self._rebuild_tiles()

    def keyPressEvent(self, event):
        # Typing focuses the search bar
        if event.text() and event.text().isprintable() and not self._search.hasFocus():
            self._search.setFocus()
            self._search.setText(event.text())
        else:
            super().keyPressEvent(event)
