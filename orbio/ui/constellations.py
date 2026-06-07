"""Constellations — spatial bookmark canvas.

Bookmarks are stars on a spatial map. Constellations are named clusters
connected by faint lines. Drag to reposition, click to navigate.
"""

import math
from PyQt6.QtWidgets import QWidget, QMenu, QInputDialog, QLabel, QVBoxLayout
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, pyqtSignal, QTimer
)
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QPainterPath,
    QRadialGradient, QFont, QFontMetrics, QMouseEvent, QAction
)

from orbio.core.bookmarks import BookmarkManager, Bookmark, Constellation


class ConstellationView(QWidget):
    """The Constellations bookmark panel — spatial star map."""

    navigate_requested = pyqtSignal(str)
    closed = pyqtSignal()

    def __init__(self, bookmark_manager: BookmarkManager, parent=None):
        super().__init__(parent)
        self._bookmarks = bookmark_manager
        self._hover_id: str = ""
        self._drag_id: str = ""
        self._drag_offset = QPointF(0, 0)
        self._scale = 1.0

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._pulse_value = 0.7
        self._pulse_dir = 1
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse)
        self._pulse_timer.start(50)

    def _pulse(self):
        self._pulse_value += 0.015 * self._pulse_dir
        if self._pulse_value >= 1.0:
            self._pulse_dir = -1
        elif self._pulse_value <= 0.5:
            self._pulse_dir = 1
        self.update()

    def show_constellations(self):
        self.show()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # Dark space background
        p.fillRect(self.rect(), QColor(6, 6, 14))

        # Draw subtle background particles (distant stars)
        self._draw_background_stars(p, w, h)

        # Draw constellation connections
        self._draw_connections(p, w, h)

        # Draw constellation labels
        self._draw_constellation_labels(p, w, h)

        # Draw bookmark stars
        self._draw_stars(p, w, h)

        # Header overlay
        self._draw_header(p, w)

        p.end()

    def _draw_background_stars(self, p: QPainter, w: int, h: int):
        """Draw tiny static background dots for atmosphere."""
        p.setPen(Qt.PenStyle.NoPen)
        import random
        rng = random.Random(42)
        for _ in range(80):
            x = rng.random() * w
            y = rng.random() * h
            size = rng.uniform(0.5, 1.5)
            alpha = rng.randint(30, 80)
            p.setBrush(QBrush(QColor(180, 200, 255, alpha)))
            p.drawEllipse(QPointF(x, y), size, size)

    def _draw_connections(self, p: QPainter, w: int, h: int):
        """Draw faint lines between stars in the same constellation."""
        constellations = self._bookmarks.constellations
        for const in constellations:
            stars = self._bookmarks.get_constellation_bookmarks(const.name)
            if len(stars) < 2:
                continue

            color = QColor(const.color)
            color.setAlpha(40)
            p.setPen(QPen(color, 0.8))

            # Connect sequential stars with lines
            for i in range(len(stars) - 1):
                x1 = stars[i].x * w
                y1 = stars[i].y * h
                x2 = stars[i + 1].x * w
                y2 = stars[i + 1].y * h
                p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _draw_constellation_labels(self, p: QPainter, w: int, h: int):
        """Draw constellation group names."""
        for const in self._bookmarks.constellations:
            stars = self._bookmarks.get_constellation_bookmarks(const.name)
            if not stars:
                continue

            # Position label at constellation center
            cx = const.center_x * w
            cy = const.center_y * h - 30

            p.setFont(QFont("Inter", 10, QFont.Weight.DemiBold))
            color = QColor(const.color)
            color.setAlpha(120)
            p.setPen(QPen(color))
            p.drawText(QRectF(cx - 60, cy, 120, 20),
                       Qt.AlignmentFlag.AlignCenter, const.name)

    def _draw_stars(self, p: QPainter, w: int, h: int):
        """Draw each bookmark as a star point."""
        for bookmark in self._bookmarks.bookmarks:
            x = bookmark.x * w
            y = bookmark.y * h
            is_hover = (bookmark.id == self._hover_id)
            is_drag = (bookmark.id == self._drag_id)

            # Star size
            base_size = 6.0
            size = base_size * (1.3 if is_hover else 1.0)

            # Get constellation color
            const = next(
                (c for c in self._bookmarks.constellations if c.name == bookmark.constellation),
                self._bookmarks.constellations[0]
            )
            star_color = QColor(const.color)

            # Glow
            if is_hover or is_drag:
                glow = QRadialGradient(x, y, size * 3)
                glow.setColorAt(0, QColor(star_color.red(), star_color.green(), star_color.blue(),
                                          int(150 * self._pulse_value)))
                glow.setColorAt(1, QColor(0, 0, 0, 0))
                p.setBrush(QBrush(glow))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(x, y), size * 3, size * 3)

            # Star body
            p.setBrush(QBrush(star_color if is_hover else QColor(
                star_color.red(), star_color.green(), star_color.blue(), 200)))
            p.setPen(QPen(QColor(255, 255, 255, 100 if is_hover else 40), 0.5))
            p.drawEllipse(QPointF(x, y), size, size)

            # Title tooltip on hover
            if is_hover:
                p.setFont(QFont("Inter", 9))
                p.setPen(QPen(QColor(220, 230, 250)))
                title = bookmark.title or bookmark.url
                fm = QFontMetrics(QFont("Inter", 9))
                elided = fm.elidedText(title, Qt.TextElideMode.ElideRight, 160)
                p.drawText(QRectF(x - 80, y + size + 8, 160, 18),
                           Qt.AlignmentFlag.AlignCenter, elided)

    def _draw_header(self, p: QPainter, w: int):
        """Draw the panel title."""
        # Semi-transparent header area
        header_grad = QRadialGradient(w / 2, 0, w)
        header_grad.setColorAt(0, QColor(6, 6, 14, 200))
        header_grad.setColorAt(1, QColor(6, 6, 14, 0))

        p.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        p.setPen(QPen(QColor(230, 235, 250)))
        p.drawText(QRectF(24, 16, 300, 32), Qt.AlignmentFlag.AlignVCenter, "Constellations")

        p.setFont(QFont("Inter", 11))
        p.setPen(QPen(QColor(100, 110, 140)))
        count = len(self._bookmarks.bookmarks)
        p.drawText(QRectF(24, 48, 300, 20), Qt.AlignmentFlag.AlignVCenter,
                   f"{count} bookmarks")

    def _hit_test(self, pos: QPointF) -> str:
        """Find which bookmark star is under the cursor."""
        w, h = self.width(), self.height()
        for bookmark in reversed(self._bookmarks.bookmarks):
            bx = bookmark.x * w
            by = bookmark.y * h
            dx = pos.x() - bx
            dy = pos.y() - by
            if math.sqrt(dx * dx + dy * dy) < 12:
                return bookmark.id
        return ""

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            bid = self._hit_test(event.position())
            if bid:
                self._drag_id = bid
                bookmark = next((b for b in self._bookmarks.bookmarks if b.id == bid), None)
                if bookmark:
                    w, h = self.width(), self.height()
                    self._drag_offset = QPointF(
                        event.position().x() - bookmark.x * w,
                        event.position().y() - bookmark.y * h
                    )

        elif event.button() == Qt.MouseButton.RightButton:
            bid = self._hit_test(event.position())
            if bid:
                self._show_context_menu(event.globalPosition().toPoint(), bid)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._drag_id:
                # If barely moved, treat as click (navigate)
                bookmark = next((b for b in self._bookmarks.bookmarks if b.id == self._drag_id), None)
                if bookmark:
                    w, h = self.width(), self.height()
                    expected_x = bookmark.x * w
                    expected_y = bookmark.y * h
                    dx = abs(event.position().x() - self._drag_offset.x() - expected_x)
                    dy = abs(event.position().y() - self._drag_offset.y() - expected_y)
                    # Essentially no drag movement — interpret as click
                    if dx < 3 and dy < 3:
                        self.navigate_requested.emit(bookmark.url)
            self._drag_id = ""
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()

        if self._drag_id:
            w, h = self.width(), self.height()
            new_x = (pos.x() - self._drag_offset.x()) / w
            new_y = (pos.y() - self._drag_offset.y()) / h
            new_x = max(0.02, min(0.98, new_x))
            new_y = max(0.05, min(0.95, new_y))
            self._bookmarks.update_position(self._drag_id, new_x, new_y)
            self.update()
        else:
            old_hover = self._hover_id
            self._hover_id = self._hit_test(pos)
            if old_hover != self._hover_id:
                self.update()

    def leaveEvent(self, event):
        self._hover_id = ""
        self.update()

    def _show_context_menu(self, pos, bookmark_id: str):
        """Show right-click context menu for a star."""
        bookmark = next((b for b in self._bookmarks.bookmarks if b.id == bookmark_id), None)
        if not bookmark:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #0e1420; color: #e0e8f0; border: 1px solid #2a3a4a;
                border-radius: 8px; padding: 4px;
            }
            QMenu::item { padding: 8px 20px; border-radius: 4px; }
            QMenu::item:selected { background: #4da6ff; color: white; }
        """)

        open_action = menu.addAction("Open")
        menu.addSeparator()

        # Move to constellation submenu
        move_menu = menu.addMenu("Move to...")
        for const in self._bookmarks.constellations:
            if const.name != bookmark.constellation:
                act = move_menu.addAction(const.name)
                act.setData(const.name)

        new_const_action = move_menu.addAction("+ New constellation...")
        menu.addSeparator()
        delete_action = menu.addAction("Delete")

        action = menu.exec(pos)
        if action == open_action:
            self.navigate_requested.emit(bookmark.url)
        elif action == delete_action:
            self._bookmarks.remove_bookmark(bookmark_id)
            self.update()
        elif action == new_const_action:
            name, ok = QInputDialog.getText(self, "New Constellation", "Name:")
            if ok and name:
                self._bookmarks.add_constellation(name)
                self._bookmarks.move_to_constellation(bookmark_id, name)
                self.update()
        elif action and action.data():
            self._bookmarks.move_to_constellation(bookmark_id, action.data())
            self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.closed.emit()
        else:
            super().keyPressEvent(event)
