"""Depths — download manager panel with sinking/resting visual states.

Downloads descend into a depth meter. In-progress items sink;
completed items rest at the bottom as solid ice chunks.
"""

import math
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QMenu, QScrollArea
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
)
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QPainterPath,
    QLinearGradient, QRadialGradient, QFont, QFontMetrics, QMouseEvent
)

from orbio.core.downloads import DownloadManager, DownloadItem, DownloadState


class DepthItem(QWidget):
    """A single download rendered as a sinking/resting ice chunk."""

    def __init__(self, item: DownloadItem, manager: DownloadManager, parent=None):
        super().__init__(parent)
        self._item = item
        self._manager = manager
        self._hover = False
        self.setFixedHeight(72)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def update_item(self, item: DownloadItem):
        self._item = item
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._item.state == DownloadState.RESTING:
                self._manager.open_file(self._item.id)
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #0e1420; color: #e0e8f0; border: 1px solid #2a3a4a;
                border-radius: 8px; padding: 4px;
            }
            QMenu::item { padding: 8px 20px; border-radius: 4px; }
            QMenu::item:selected { background: #4da6ff; color: white; }
        """)

        if self._item.state == DownloadState.RESTING:
            open_act = menu.addAction("Open file")
            folder_act = menu.addAction("Open folder")
            menu.addSeparator()
        elif self._item.state == DownloadState.SINKING:
            cancel_act = menu.addAction("Cancel")
            menu.addSeparator()

        remove_act = menu.addAction("Remove from list")

        action = menu.exec(pos)
        if not action:
            return

        if action.text() == "Open file":
            self._manager.open_file(self._item.id)
        elif action.text() == "Open folder":
            self._manager.open_folder(self._item.id)
        elif action.text() == "Cancel":
            self._manager.cancel(self._item.id)
        elif action.text() == "Remove from list":
            self._manager.remove(self._item.id)
            self.deleteLater()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        rect = QRectF(8, 4, w - 16, h - 8)

        state = self._item.state

        # Background based on state
        if state == DownloadState.SINKING:
            bg = QColor(12, 24, 42, 200)
            border = QColor(60, 140, 220)
            accent = QColor(77, 166, 255)
        elif state == DownloadState.RESTING:
            bg = QColor(10, 30, 20, 200)
            border = QColor(60, 180, 120)
            accent = QColor(68, 221, 136)
        elif state == DownloadState.FAILED:
            bg = QColor(30, 12, 16, 200)
            border = QColor(200, 80, 100)
            accent = QColor(255, 68, 102)
        else:
            bg = QColor(20, 20, 30, 200)
            border = QColor(80, 80, 100)
            accent = QColor(120, 120, 150)

        if self._hover:
            bg = QColor(bg.red() + 10, bg.green() + 10, bg.blue() + 10, bg.alpha())

        # Card
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        p.setBrush(QBrush(bg))
        p.setPen(QPen(border, 1.5 if self._hover else 1))
        p.drawPath(path)

        # Progress bar (for sinking state)
        if state == DownloadState.SINKING and self._item.progress > 0:
            bar_y = h - 10
            bar_w = (w - 32) * self._item.progress
            bar_rect = QRectF(16, bar_y, bar_w, 3)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(accent))
            p.drawRoundedRect(bar_rect, 1.5, 1.5)

            # Track
            track_rect = QRectF(16 + bar_w, bar_y, (w - 32) - bar_w, 3)
            p.setBrush(QBrush(QColor(30, 30, 40)))
            p.drawRoundedRect(track_rect, 1.5, 1.5)

        # Filename
        p.setFont(QFont("Inter", 11))
        p.setPen(QPen(QColor(220, 230, 245)))
        fm = QFontMetrics(QFont("Inter", 11))
        name = fm.elidedText(self._item.filename, Qt.TextElideMode.ElideMiddle, w - 48)
        p.drawText(QRectF(20, 8, w - 40, 24), Qt.AlignmentFlag.AlignVCenter, name)

        # Status line
        p.setFont(QFont("Inter", 9))
        p.setPen(QPen(QColor(100, 130, 170)))

        if state == DownloadState.SINKING:
            size_str = DownloadManager.format_size(self._item.received_bytes)
            total_str = DownloadManager.format_size(self._item.total_bytes)
            speed_str = DownloadManager.format_speed(self._item.speed)
            status = f"{size_str} / {total_str} — {speed_str}"
        elif state == DownloadState.RESTING:
            size_str = DownloadManager.format_size(self._item.total_bytes)
            status = f"Complete — {size_str}"
            p.setPen(QPen(QColor(80, 180, 120)))
        elif state == DownloadState.FAILED:
            status = "Failed"
            p.setPen(QPen(QColor(200, 80, 100)))
        else:
            status = "Paused"

        p.drawText(QRectF(20, 32, w - 40, 20), Qt.AlignmentFlag.AlignVCenter, status)

        # State icon on the right
        p.setFont(QFont("Inter", 16))
        p.setPen(QPen(accent))
        icon = {"sinking": "↓", "resting": "✓", "failed": "✗", "paused": "⏸"}
        p.drawText(QRectF(w - 44, 0, 28, h),
                   Qt.AlignmentFlag.AlignCenter, icon.get(state.value, "?"))

        p.end()


class DepthsPanel(QWidget):
    """The Depths download panel — slides in from the right."""

    closed = pyqtSignal()

    def __init__(self, download_manager: DownloadManager, parent=None):
        super().__init__(parent)
        self._manager = download_manager
        self._items: dict[int, DepthItem] = {}
        self._build_ui()

        # Connect manager signals
        self._manager.download_started.connect(self._on_download_started)
        self._manager.download_progress.connect(self._on_progress)
        self._manager.download_finished.connect(self._on_finished)
        self._manager.download_failed.connect(self._on_failed)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_active)
        self._refresh_timer.start(500)

    def _build_ui(self):
        self.setFixedWidth(340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(64)
        header.setStyleSheet("background: #0a0a12; border-bottom: 1px solid #1a1a2a;")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(16, 12, 16, 8)

        title = QLabel("Depths")
        title.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #e8e8f0; background: transparent; border: none;")
        h_layout.addWidget(title)

        self._count_label = QLabel("No downloads")
        self._count_label.setFont(QFont("Inter", 9))
        self._count_label.setStyleSheet("color: #6a6a8a; background: transparent; border: none;")
        h_layout.addWidget(self._count_label)

        layout.addWidget(header)

        # Scrollable download list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { background: #0e0e16; border: none; }
            QScrollBar:vertical { width: 6px; background: transparent; }
            QScrollBar::handle:vertical { background: #2a2a3a; border-radius: 3px; }
        """)

        self._list_widget = QWidget()
        self._list_widget.setStyleSheet("background: #0e0e16;")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(8, 8, 8, 8)
        self._list_layout.setSpacing(4)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self._list_widget)
        layout.addWidget(scroll)

    def _on_download_started(self, item: DownloadItem):
        widget = DepthItem(item, self._manager)
        self._items[item.id] = widget
        self._list_layout.insertWidget(0, widget)
        self._update_count()

    def _on_progress(self, download_id: int, progress: float):
        if download_id in self._items:
            item = next((d for d in self._manager.downloads if d.id == download_id), None)
            if item:
                self._items[download_id].update_item(item)

    def _on_finished(self, download_id: int):
        if download_id in self._items:
            item = next((d for d in self._manager.downloads if d.id == download_id), None)
            if item:
                self._items[download_id].update_item(item)
        self._update_count()

    def _on_failed(self, download_id: int, reason: str):
        if download_id in self._items:
            item = next((d for d in self._manager.downloads if d.id == download_id), None)
            if item:
                self._items[download_id].update_item(item)
        self._update_count()

    def _refresh_active(self):
        """Periodically refresh active download widgets for speed display."""
        for item in self._manager.downloads:
            if item.state == DownloadState.SINKING and item.id in self._items:
                self._items[item.id].update_item(item)

    def _update_count(self):
        total = len(self._manager.downloads)
        active = self._manager.active_count
        if total == 0:
            self._count_label.setText("No downloads")
        elif active > 0:
            self._count_label.setText(f"{active} downloading, {total} total")
        else:
            self._count_label.setText(f"{total} downloads")

    def show_depths(self):
        self._update_count()
        self.show()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(10, 10, 18, 250))
        p.end()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.closed.emit()
        else:
            super().keyPressEvent(event)
