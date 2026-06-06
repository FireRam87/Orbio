"""Privacy dashboard overlay — shows blocking stats visually."""

import math
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QPushButton
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QPainterPath, QFont,
    QRadialGradient, QLinearGradient, QPaintEvent
)

from orbio.engine.privacy import PrivacyStats


class StatRing(QWidget):
    """A single circular stat display (radial progress ring)."""

    def __init__(self, label: str, color: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(100, 120)
        self._label = label
        self._color = QColor(color)
        self._value = 0
        self._max_value = 100

    def set_value(self, value: int, max_value: int = 100):
        self._value = value
        self._max_value = max(max_value, 1)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        cx = w / 2
        cy = 50
        radius = 35

        # Background ring
        painter.setPen(QPen(QColor(42, 42, 58), 6))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        # Progress ring
        if self._value > 0:
            progress = min(self._value / self._max_value, 1.0)
            span = int(-progress * 360 * 16)

            pen = QPen(self._color, 6)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)

            rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
            painter.drawArc(rect, 90 * 16, span)

        # Value text
        painter.setPen(QPen(QColor("#e8e8f0")))
        font = QFont("Inter", 14, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(0, cy - 12, w, 24),
                        Qt.AlignmentFlag.AlignCenter, str(self._value))

        # Label
        painter.setPen(QPen(QColor("#8888aa")))
        font = QFont("Inter", 9)
        painter.setFont(font)
        painter.drawText(QRectF(0, 95, w, 20),
                        Qt.AlignmentFlag.AlignCenter, self._label)

        painter.end()


class DomainBar(QWidget):
    """A single horizontal bar showing a blocked domain."""

    def __init__(self, domain: str, count: int, max_count: int, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self._domain = domain
        self._count = count
        self._max_count = max(max_count, 1)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Bar background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(26, 26, 37)))
        painter.drawRoundedRect(QRectF(0, 2, w, h - 4), 4, 4)

        # Fill bar
        fill_w = max(4, (self._count / self._max_count) * (w - 120))
        gradient = QLinearGradient(0, 0, fill_w, 0)
        gradient.setColorAt(0, QColor(77, 166, 255, 180))
        gradient.setColorAt(1, QColor(77, 166, 255, 60))
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(QRectF(0, 2, fill_w, h - 4), 4, 4)

        # Domain text
        painter.setPen(QPen(QColor("#ccccdd")))
        font = QFont("Inter", 10)
        painter.setFont(font)
        painter.drawText(QRectF(8, 0, w - 60, h),
                        Qt.AlignmentFlag.AlignVCenter, self._domain)

        # Count text
        painter.setPen(QPen(QColor("#4da6ff")))
        painter.drawText(QRectF(w - 50, 0, 42, h),
                        Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                        str(self._count))

        painter.end()


class PrivacyDashboard(QWidget):
    """Full privacy stats dashboard overlay."""

    close_requested = pyqtSignal()

    def __init__(self, stats: PrivacyStats, parent=None):
        super().__init__(parent)
        self.stats = stats
        self.setMinimumSize(500, 400)
        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(10, 10, 15, 240);
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Privacy Dashboard")
        title.setStyleSheet("color: #e8e8f0; font-size: 18px; font-weight: bold; background: transparent;")
        header_layout.addWidget(title)

        subtitle = QLabel("Your browsing protection at a glance")
        subtitle.setStyleSheet("color: #8888aa; font-size: 12px; background: transparent;")
        header_layout.addWidget(subtitle)

        layout.addWidget(header)

        # Stat rings container
        self.rings_container = QWidget()
        self.rings_container.setStyleSheet("background: transparent;")
        self.rings_layout = QVBoxLayout(self.rings_container)
        self.rings_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.rings_container)

        # Blocked domains section
        domains_label = QLabel("Top Blocked Domains")
        domains_label.setStyleSheet("color: #8888aa; font-size: 11px; font-weight: bold; background: transparent;")
        layout.addWidget(domains_label)

        self.domains_scroll = QScrollArea()
        self.domains_scroll.setWidgetResizable(True)
        self.domains_scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { width: 6px; background: transparent; }
            QScrollBar::handle:vertical { background: #2a2a3a; border-radius: 3px; }
        """)
        self.domains_container = QWidget()
        self.domains_container.setStyleSheet("background: transparent;")
        self.domains_layout = QVBoxLayout(self.domains_container)
        self.domains_layout.setContentsMargins(0, 0, 0, 0)
        self.domains_layout.setSpacing(4)
        self.domains_scroll.setWidget(self.domains_container)
        layout.addWidget(self.domains_scroll)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background: #1a1a25;
                color: #8888aa;
                border: 1px solid #2a2a3a;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #2a2a3a;
                color: #4da6ff;
                border-color: #4da6ff;
            }
        """)
        close_btn.clicked.connect(self._close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def show_dashboard(self):
        """Refresh stats and show the dashboard."""
        self._refresh()
        self.show()
        self.raise_()

    def _refresh(self):
        """Update all displayed stats."""
        # Clear old rings
        while self.rings_layout.count():
            item = self.rings_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create stat rings in a horizontal row widget
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        from PyQt6.QtWidgets import QHBoxLayout
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(20)

        trackers_ring = StatRing("Trackers", "#4da6ff")
        trackers_ring.set_value(self.stats.trackers_blocked, max(self.stats.trackers_blocked, 50))
        row_layout.addWidget(trackers_ring)

        requests_ring = StatRing("Requests", "#44dd88")
        requests_ring.set_value(self.stats.total_requests, max(self.stats.total_requests, 100))
        row_layout.addWidget(requests_ring)

        domains_ring = StatRing("Domains", "#ffaa33")
        domains_ring.set_value(len(self.stats.blocked_domains), max(len(self.stats.blocked_domains), 20))
        row_layout.addWidget(domains_ring)

        row_layout.addStretch()
        self.rings_layout.addWidget(row)

        # Clear and refresh domain bars
        while self.domains_layout.count():
            item = self.domains_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        sorted_domains = sorted(
            self.stats.blocked_domains.items(),
            key=lambda x: x[1], reverse=True
        )[:10]

        if sorted_domains:
            max_count = sorted_domains[0][1]
            for domain, count in sorted_domains:
                bar = DomainBar(domain, count, max_count)
                self.domains_layout.addWidget(bar)
        else:
            no_data = QLabel("No blocked domains yet — browse to see stats")
            no_data.setStyleSheet("color: #555566; font-size: 11px; background: transparent;")
            self.domains_layout.addWidget(no_data)

        self.domains_layout.addStretch()

    def _close(self):
        self.hide()
        self.close_requested.emit()
