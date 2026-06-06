"""Radial tab ring widget — the signature Orbio UI element."""

import math
from PyQt6.QtWidgets import QWidget, QToolTip
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, pyqtSignal, QPropertyAnimation,
    QEasingCurve, pyqtProperty, QTimer
)
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QFont, QFontMetrics,
    QPainterPath, QRadialGradient, QLinearGradient, QMouseEvent
)


class RadialTabRing(QWidget):
    """Circular tab ring that displays tabs as arcs around a ring."""

    tab_activated = pyqtSignal(int)
    tab_close_requested = pyqtSignal(int)
    new_tab_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tabs: list[dict] = []
        self._active_index: int = -1
        self._hover_index: int = -1
        self._ring_radius: float = 0
        self._center: QPointF = QPointF(0, 0)
        self._glow_intensity: float = 0.7
        self._rotation_offset: float = 0.0
        self._visible = True

        self.setMinimumHeight(80)
        self.setMaximumHeight(100)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Animation for glow pulse
        self._pulse_value = 0.7
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_tick)
        self._pulse_direction = 1
        self._pulse_timer.start(50)

    def _pulse_tick(self):
        self._pulse_value += 0.02 * self._pulse_direction
        if self._pulse_value >= 1.0:
            self._pulse_direction = -1
        elif self._pulse_value <= 0.5:
            self._pulse_direction = 1
        self.update()

    def set_tabs(self, tabs: list[dict]):
        """Set the tab list. Each dict has 'title', 'active', 'index'."""
        self._tabs = tabs
        self.update()

    def set_active(self, index: int):
        self._active_index = index
        self.update()

    def add_tab(self, title: str) -> int:
        index = len(self._tabs)
        self._tabs.append({"title": title, "index": index})
        self.update()
        return index

    def remove_tab(self, index: int):
        if 0 <= index < len(self._tabs):
            self._tabs.pop(index)
            for i, tab in enumerate(self._tabs):
                tab["index"] = i
            self.update()

    def set_tab_title(self, index: int, title: str):
        if 0 <= index < len(self._tabs):
            self._tabs[index]["title"] = title
            self.update()

    def tab_count(self) -> int:
        return len(self._tabs)

    def paintEvent(self, event):
        if not self._tabs:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        self._center = QPointF(w / 2, h * 1.2)
        self._ring_radius = min(w * 0.42, h * 2.0)

        n = len(self._tabs)
        arc_span = 160.0
        start_angle = -90 - arc_span / 2

        if n == 1:
            gap = 0
            tab_arc = arc_span
        else:
            gap = min(3.0, arc_span / (n * 4))
            total_gaps = gap * (n - 1)
            tab_arc = (arc_span - total_gaps) / n

        for i, tab in enumerate(self._tabs):
            angle_start = start_angle + i * (tab_arc + gap)
            is_active = (i == self._active_index)
            is_hover = (i == self._hover_index)

            self._draw_tab_arc(painter, i, angle_start, tab_arc,
                             tab["title"], is_active, is_hover)

        # Draw new-tab button at the end
        self._draw_new_tab_button(painter, start_angle + n * (tab_arc + gap))

        painter.end()

    def _draw_tab_arc(self, painter: QPainter, index: int, start_deg: float,
                      span_deg: float, title: str, active: bool, hover: bool):
        """Draw a single tab as an arc segment."""
        cx = self._center.x()
        cy = self._center.y()
        r = self._ring_radius

        # Compute arc path
        path = QPainterPath()
        inner_r = r - 30
        outer_r = r

        start_rad = math.radians(start_deg)
        end_rad = math.radians(start_deg + span_deg)

        # Outer arc
        outer_rect = QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2)
        inner_rect = QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2)

        path.arcMoveTo(outer_rect, start_deg)
        path.arcTo(outer_rect, start_deg, span_deg)

        # Connect to inner arc
        path.arcTo(inner_rect, start_deg + span_deg, -span_deg)
        path.closeSubpath()

        # Colors
        if active:
            base_color = QColor("#4da6ff")
            fill_color = QColor(26, 140, 255, int(80 * self._pulse_value))
            glow_color = QColor(77, 166, 255, int(120 * self._pulse_value))
            text_color = QColor("#e8e8f0")
        elif hover:
            base_color = QColor("#6688aa")
            fill_color = QColor(40, 60, 80, 60)
            glow_color = QColor(100, 136, 170, 80)
            text_color = QColor("#ccccdd")
        else:
            base_color = QColor("#2a2a3a")
            fill_color = QColor(20, 20, 30, 40)
            glow_color = QColor(42, 42, 58, 40)
            text_color = QColor("#8888aa")

        # Draw glow behind active tab
        if active:
            glow_pen = QPen(glow_color, 4)
            painter.setPen(glow_pen)
            painter.drawPath(path)

        # Fill
        painter.setBrush(QBrush(fill_color))
        painter.setPen(QPen(base_color, 1.5))
        painter.drawPath(path)

        # Draw title text along the mid arc
        mid_r = (inner_r + outer_r) / 2
        mid_angle = math.radians(start_deg + span_deg / 2)
        text_x = cx + mid_r * math.cos(mid_angle)
        text_y = cy + mid_r * math.sin(mid_angle)

        painter.setPen(QPen(text_color))
        font = QFont("Inter", 9)
        painter.setFont(font)

        fm = QFontMetrics(font)
        max_text_width = int(span_deg / 160 * self._ring_radius * 0.8)
        elided = fm.elidedText(title, Qt.TextElideMode.ElideRight, max_text_width)

        text_rect = QRectF(text_x - 50, text_y - 8, 100, 16)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, elided)

    def _draw_new_tab_button(self, painter: QPainter, angle_start: float):
        """Draw a small + button at the end of the ring."""
        cx = self._center.x()
        cy = self._center.y()
        mid_r = self._ring_radius - 15
        mid_angle = math.radians(angle_start + 5)
        bx = cx + mid_r * math.cos(mid_angle)
        by = cy + mid_r * math.sin(mid_angle)

        painter.setPen(QPen(QColor("#2a2a3a"), 1.5))
        painter.setBrush(QBrush(QColor(20, 20, 30, 80)))
        painter.drawEllipse(QPointF(bx, by), 12, 12)

        painter.setPen(QPen(QColor("#8888aa"), 2))
        painter.drawLine(QPointF(bx - 5, by), QPointF(bx + 5, by))
        painter.drawLine(QPointF(bx, by - 5), QPointF(bx, by + 5))

    def mousePressEvent(self, event: QMouseEvent):
        index = self._hit_test(event.position())
        if index == -2:
            self.new_tab_requested.emit()
        elif index >= 0:
            self.tab_activated.emit(index)

    def mouseMoveEvent(self, event: QMouseEvent):
        index = self._hit_test(event.position())
        old_hover = self._hover_index
        self._hover_index = max(index, -1)
        if old_hover != self._hover_index:
            self.update()
            if index >= 0 and index < len(self._tabs):
                QToolTip.showText(event.globalPosition().toPoint(),
                                 self._tabs[index]["title"])

    def leaveEvent(self, event):
        self._hover_index = -1
        self.update()

    def _hit_test(self, pos: QPointF) -> int:
        """Determine which tab (or new-tab button) was clicked. -1 = none, -2 = new tab."""
        if not self._tabs:
            return -1

        cx = self._center.x()
        cy = self._center.y()
        dx = pos.x() - cx
        dy = pos.y() - cy
        dist = math.sqrt(dx * dx + dy * dy)

        inner_r = self._ring_radius - 30
        outer_r = self._ring_radius

        if dist < inner_r or dist > outer_r + 15:
            return -1

        angle = math.degrees(math.atan2(dy, dx))

        n = len(self._tabs)
        arc_span = 160.0
        start_angle = -90 - arc_span / 2
        gap = min(3.0, arc_span / (n * 4)) if n > 1 else 0
        tab_arc = (arc_span - gap * max(0, n - 1)) / n

        for i in range(n):
            a_start = start_angle + i * (tab_arc + gap)
            a_end = a_start + tab_arc
            if a_start <= angle <= a_end:
                return i

        # Check new-tab button area
        new_angle = start_angle + n * (tab_arc + gap) + 5
        if abs(angle - new_angle) < 10 and dist < outer_r:
            return -2

        return -1
