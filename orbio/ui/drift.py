"""Drift — visual timeline history view.

History flows as a horizontal timeline: days are sections, sites with more
time spent render as larger ice blocks. Browsing paths shown as faint lines.
"""

import math
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QScrollArea
)
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, pyqtSignal, QTimer, QSize
)
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QPainterPath,
    QLinearGradient, QRadialGradient, QFont, QFontMetrics, QMouseEvent
)

from orbio.core.history import HistoryManager, HistoryEntry


class DriftBlock(QWidget):
    """A single history entry rendered as an ice block. Size = time spent."""

    clicked = pyqtSignal(str)

    def __init__(self, entry: HistoryEntry, max_duration: float, parent=None):
        super().__init__(parent)
        self._entry = entry
        self._hover = False
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Size based on duration relative to max
        ratio = min(entry.duration / max(max_duration, 1), 1.0)
        w = int(80 + ratio * 100)
        h = int(50 + ratio * 30)
        self.setFixedSize(w, h)
        self.setToolTip(f"{entry.title}\n{entry.url}\n{int(entry.duration)}s spent")

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._entry.url)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        rect = QRectF(2, 2, w - 4, h - 4)

        # Ice block appearance
        if self._hover:
            fill = QColor(30, 60, 90, 200)
            border = QColor(100, 200, 255)
            text_color = QColor(230, 245, 255)
        else:
            fill = QColor(16, 28, 44, 180)
            border = QColor(60, 100, 140)
            text_color = QColor(180, 200, 220)

        # Draw block
        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(border, 1.5))
        p.drawPath(path)

        # Frost edge highlight
        if self._hover:
            glow = QLinearGradient(0, 0, w, 0)
            glow.setColorAt(0, QColor(77, 166, 255, 0))
            glow.setColorAt(0.5, QColor(77, 166, 255, 60))
            glow.setColorAt(1, QColor(77, 166, 255, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(glow))
            p.drawRoundedRect(QRectF(4, 2, w - 8, 3), 1, 1)

        # Title text
        p.setPen(QPen(text_color))
        font = QFont("Inter", 9)
        p.setFont(font)
        fm = QFontMetrics(font)
        title = self._entry.title or self._entry.domain
        elided = fm.elidedText(title, Qt.TextElideMode.ElideRight, w - 16)
        p.drawText(QRectF(8, 4, w - 16, h * 0.5), Qt.AlignmentFlag.AlignVCenter, elided)

        # Duration / time subtitle
        p.setPen(QPen(QColor(100, 140, 180)))
        p.setFont(QFont("Inter", 8))
        time_str = self._entry.datetime.strftime("%H:%M")
        dur_str = self._format_duration(self._entry.duration)
        p.drawText(QRectF(8, h * 0.5, w - 16, h * 0.45),
                   Qt.AlignmentFlag.AlignVCenter, f"{time_str} · {dur_str}")

        p.end()

    @staticmethod
    def _format_duration(seconds: float) -> str:
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds / 60)}m"
        else:
            return f"{seconds / 3600:.1f}h"


class DaySection(QWidget):
    """A section representing one day of history."""

    navigate_requested = pyqtSignal(str)

    def __init__(self, date: datetime, entries: list[HistoryEntry], parent=None):
        super().__init__(parent)
        self._date = date
        self._entries = entries
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(4)

        # Day header
        if date.date() == datetime.now().date():
            day_label = "Today"
        elif date.date() == (datetime.now() - timedelta(days=1)).date():
            day_label = "Yesterday"
        else:
            day_label = date.strftime("%A, %B %d")

        header = QLabel(day_label)
        header.setFont(QFont("Inter", 13, QFont.Weight.Bold))
        header.setStyleSheet("color: #c8d0e8; background: transparent; padding: 4px 0;")
        layout.addWidget(header)

        # Entry count subtitle
        count_label = QLabel(f"{len(entries)} sites visited")
        count_label.setFont(QFont("Inter", 9))
        count_label.setStyleSheet("color: #5a6a8a; background: transparent;")
        layout.addWidget(count_label)

        # Flow layout for ice blocks
        flow = QWidget()
        flow.setStyleSheet("background: transparent;")
        flow_layout = QHBoxLayout(flow)
        flow_layout.setContentsMargins(0, 8, 0, 0)
        flow_layout.setSpacing(8)
        flow_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        max_dur = max((e.duration for e in entries), default=60)

        for entry in entries[:30]:
            block = DriftBlock(entry, max_dur)
            block.clicked.connect(self.navigate_requested.emit)
            flow_layout.addWidget(block)

        layout.addWidget(flow)


class DriftView(QWidget):
    """The Drift history panel — visual timeline of browsing history."""

    navigate_requested = pyqtSignal(str)
    closed = pyqtSignal()

    def __init__(self, history_manager: HistoryManager, parent=None):
        super().__init__(parent)
        self._history = history_manager
        self._search_text = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with search
        header = QWidget()
        header.setFixedHeight(72)
        header.setStyleSheet("background: #0a0a12; border-bottom: 1px solid #1a1a2a;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(24, 16, 24, 16)

        title = QLabel("Drift")
        title.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #e8e8f0; background: transparent; border: none;")
        h_layout.addWidget(title)

        subtitle = QLabel("Your browsing timeline")
        subtitle.setFont(QFont("Inter", 11))
        subtitle.setStyleSheet("color: #6a6a8a; background: transparent; border: none; margin-left: 12px;")
        h_layout.addWidget(subtitle)
        h_layout.addStretch()

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search history...")
        self._search_input.setFixedWidth(240)
        self._search_input.setStyleSheet("""
            QLineEdit {
                background: #12121a; color: #e0e0f0; border: 1px solid #2a2a3a;
                border-radius: 8px; padding: 8px 14px; font-size: 12px;
            }
            QLineEdit:focus { border-color: #4da6ff; }
        """)
        self._search_input.textChanged.connect(self._on_search)
        h_layout.addWidget(self._search_input)

        layout.addWidget(header)

        # Scrollable content area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea { background: #0e0e16; border: none; }
            QScrollBar:vertical { width: 6px; background: transparent; }
            QScrollBar::handle:vertical { background: #2a2a3a; border-radius: 3px; }
        """)
        layout.addWidget(self._scroll)

        self._content = QWidget()
        self._content.setStyleSheet("background: #0e0e16;")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(24, 16, 24, 16)
        self._content_layout.setSpacing(16)
        self._scroll.setWidget(self._content)

    def refresh(self):
        """Reload history entries and rebuild the timeline."""
        # Clear existing
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        entries = self._history.get_entries(limit=500, search=self._search_text)

        if not entries:
            empty = QLabel("No history yet. Start browsing!")
            empty.setFont(QFont("Inter", 13))
            empty.setStyleSheet("color: #5a5a7a; background: transparent;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._content_layout.addWidget(empty)
            self._content_layout.addStretch()
            return

        # Group by day
        days: dict[str, list[HistoryEntry]] = {}
        for entry in entries:
            day_key = entry.datetime.strftime("%Y-%m-%d")
            if day_key not in days:
                days[day_key] = []
            days[day_key].append(entry)

        for day_key in sorted(days.keys(), reverse=True):
            day_entries = days[day_key]
            date = datetime.strptime(day_key, "%Y-%m-%d")
            section = DaySection(date, day_entries)
            section.navigate_requested.connect(self.navigate_requested.emit)
            self._content_layout.addWidget(section)

        self._content_layout.addStretch()

    def _on_search(self, text: str):
        self._search_text = text.strip()
        self.refresh()

    def show_drift(self):
        """Show the drift view and refresh data."""
        self.refresh()
        self.show()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(8, 8, 14, 245))
        p.end()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.closed.emit()
        else:
            super().keyPressEvent(event)
