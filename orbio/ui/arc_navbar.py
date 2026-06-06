"""Arc-shaped navigation bar for Orbio."""

import math
from PyQt6.QtWidgets import QWidget, QLineEdit, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QSize
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QPainterPath,
    QLinearGradient, QFont, QMouseEvent, QPaintEvent
)


class ArcNavBar(QWidget):
    """A curved navigation bar that matches the radial UI paradigm."""

    navigate_requested = pyqtSignal(str)
    back_requested = pyqtSignal()
    forward_requested = pyqtSignal()
    reload_requested = pyqtSignal()
    bookmark_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setMouseTracking(True)

        self._url_text = ""
        self._placeholder = "Search with DuckDuckGo or enter URL..."
        self._focused = False
        self._hover_btn = -1
        self._buttons = ["←", "→", "↻", "☆"]
        self._btn_rects: list[QRectF] = []
        self._url_rect = QRectF()
        self._editing = False

        # Embedded line edit for actual text input
        self._editor = QLineEdit(self)
        self._editor.setStyleSheet("""
            QLineEdit {
                background: transparent;
                color: #e8e8f0;
                border: none;
                font-size: 13px;
                padding: 0;
                selection-background-color: #4da6ff;
            }
        """)
        self._editor.returnPressed.connect(self._on_enter)
        self._editor.hide()

    def set_url(self, url: str):
        """Set the displayed URL."""
        self._url_text = url
        if self._editing:
            self._editor.setText(url)
        self.update()

    def get_url(self) -> str:
        if self._editing:
            return self._editor.text()
        return self._url_text

    def focus_url(self):
        """Focus the URL bar for editing."""
        self._start_editing()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Draw the arc background shape
        self._draw_arc_background(painter, w, h)

        # Draw navigation buttons
        self._draw_buttons(painter, w, h)

        # Draw URL text (when not editing)
        if not self._editing:
            self._draw_url(painter, w, h)

        painter.end()

    def _draw_arc_background(self, painter: QPainter, w: int, h: int):
        """Draw the curved navbar background."""
        path = QPainterPath()

        # Subtle arc shape — slightly curved top edge
        arc_depth = 6
        margin = 12

        path.moveTo(margin, h - 4)
        path.lineTo(margin, arc_depth + 8)
        path.quadTo(w / 2, -arc_depth, w - margin, arc_depth + 8)
        path.lineTo(w - margin, h - 4)
        path.quadTo(w / 2, h + 2, margin, h - 4)

        # Fill with dark gradient
        gradient = QLinearGradient(0, 0, 0, h)
        gradient.setColorAt(0, QColor("#14141e"))
        gradient.setColorAt(1, QColor("#0e0e16"))

        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor("#2a2a3a"), 1))
        painter.drawPath(path)

        # Glow line at the top curve
        glow_path = QPainterPath()
        glow_path.moveTo(margin + 20, arc_depth + 8)
        glow_path.quadTo(w / 2, -arc_depth + 2, w - margin - 20, arc_depth + 8)

        glow_pen = QPen(QColor(77, 166, 255, 60), 1.5)
        painter.setPen(glow_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(glow_path)

    def _draw_buttons(self, painter: QPainter, w: int, h: int):
        """Draw the navigation buttons."""
        self._btn_rects.clear()
        btn_y = h / 2 - 14
        btn_size = 28
        x_start = 24

        for i, label in enumerate(self._buttons):
            x = x_start + i * (btn_size + 8)
            rect = QRectF(x, btn_y, btn_size, btn_size)
            self._btn_rects.append(rect)

            is_hover = (i == self._hover_btn)

            # Button background
            if is_hover:
                painter.setBrush(QBrush(QColor(26, 26, 37, 180)))
                painter.setPen(QPen(QColor("#4da6ff"), 1))
            else:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor("#2a2a3a"), 1))

            painter.drawRoundedRect(rect, 6, 6)

            # Button text
            if is_hover:
                painter.setPen(QPen(QColor("#4da6ff")))
            else:
                painter.setPen(QPen(QColor("#8888aa")))

            font = QFont("Inter", 12, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

        # URL area starts after buttons
        url_x = x_start + len(self._buttons) * (btn_size + 8) + 12
        url_w = w - url_x - 24
        self._url_rect = QRectF(url_x, btn_y - 2, url_w, btn_size + 4)

        # URL background
        if self._focused:
            painter.setPen(QPen(QColor("#4da6ff"), 1.5))
        else:
            painter.setPen(QPen(QColor("#2a2a3a"), 1))

        painter.setBrush(QBrush(QColor("#0a0a0f")))
        painter.drawRoundedRect(self._url_rect, 8, 8)

    def _draw_url(self, painter: QPainter, w: int, h: int):
        """Draw the URL text."""
        font = QFont("Inter", 12)
        painter.setFont(font)

        text_rect = self._url_rect.adjusted(12, 0, -12, 0)

        if self._url_text:
            painter.setPen(QPen(QColor("#e8e8f0")))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, self._url_text)
        else:
            painter.setPen(QPen(QColor("#555566")))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, self._placeholder)

    def mousePressEvent(self, event: QMouseEvent):
        pos = event.position()

        # Check button clicks
        for i, rect in enumerate(self._btn_rects):
            if rect.contains(pos):
                if i == 0:
                    self.back_requested.emit()
                elif i == 1:
                    self.forward_requested.emit()
                elif i == 2:
                    self.reload_requested.emit()
                elif i == 3:
                    self.bookmark_requested.emit()
                return

        # Check URL area click
        if self._url_rect.contains(pos):
            self._start_editing()

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()
        old_hover = self._hover_btn
        self._hover_btn = -1
        for i, rect in enumerate(self._btn_rects):
            if rect.contains(pos):
                self._hover_btn = i
                break
        if old_hover != self._hover_btn:
            self.update()

    def leaveEvent(self, event):
        self._hover_btn = -1
        self.update()

    def _start_editing(self):
        """Switch to edit mode with the line edit visible."""
        self._editing = True
        self._focused = True
        r = self._url_rect
        self._editor.setGeometry(
            int(r.x()) + 12, int(r.y()) + 2,
            int(r.width()) - 24, int(r.height()) - 4
        )
        self._editor.setText(self._url_text)
        self._editor.show()
        self._editor.setFocus()
        self._editor.selectAll()
        self.update()

    def _stop_editing(self):
        """Exit edit mode."""
        self._editing = False
        self._focused = False
        self._editor.hide()
        self.update()

    def _on_enter(self):
        """Handle Enter in the URL editor."""
        text = self._editor.text().strip()
        if text:
            self._url_text = text
            self.navigate_requested.emit(text)
        self._stop_editing()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._editing:
            r = self._url_rect
            self._editor.setGeometry(
                int(r.x()) + 12, int(r.y()) + 2,
                int(r.width()) - 24, int(r.height()) - 4
            )
