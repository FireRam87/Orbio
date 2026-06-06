"""Tab bar widget for Orbio — horizontal tab strip."""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont


class TabButton(QPushButton):
    """Individual tab button."""

    close_requested = pyqtSignal(int)
    activated = pyqtSignal(int)

    def __init__(self, index: int, title: str = "New Tab", parent=None):
        super().__init__(parent)
        self.index = index
        self._title = title
        self._active = False
        self.setFixedHeight(34)
        self.setMinimumWidth(100)
        self.setMaximumWidth(220)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setText(self._truncate(title))
        self.clicked.connect(lambda: self.activated.emit(self.index))
        self._apply_style()

    def set_active(self, active: bool):
        self._active = active
        self._apply_style()

    def set_title(self, title: str):
        self._title = title
        self.setText(self._truncate(title))
        self.setToolTip(title)

    def _truncate(self, text: str, max_len: int = 22) -> str:
        return text[:max_len] + "…" if len(text) > max_len else text

    def _apply_style(self):
        if self._active:
            self.setStyleSheet("""
                QPushButton {
                    background: #1a1a25;
                    color: #4da6ff;
                    border: 1px solid #4da6ff;
                    border-radius: 6px;
                    padding: 4px 12px;
                    font-size: 12px;
                    text-align: left;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #8888aa;
                    border: 1px solid transparent;
                    border-radius: 6px;
                    padding: 4px 12px;
                    font-size: 12px;
                    text-align: left;
                }
                QPushButton:hover {
                    background: #1a1a25;
                    color: #ccccdd;
                    border-color: #2a2a3a;
                }
            """)


class OrbioTabBar(QWidget):
    """Horizontal tab bar that displays all open tabs."""

    tab_activated = pyqtSignal(int)
    tab_close_requested = pyqtSignal(int)
    new_tab_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tab_buttons: list[TabButton] = []
        self._active_index = -1
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedHeight(42)
        self.setStyleSheet("background-color: #0a0a0f; border-bottom: 1px solid #1a1a25;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.tabs_container = QWidget()
        self.tabs_layout = QHBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs_layout.setSpacing(4)
        self.tabs_layout.addStretch()

        self.scroll_area.setWidget(self.tabs_container)
        layout.addWidget(self.scroll_area)

        new_btn = QPushButton("+")
        new_btn.setFixedSize(30, 30)
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8888aa;
                border: 1px solid #2a2a3a;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #1a1a25;
                color: #4da6ff;
                border-color: #4da6ff;
            }
        """)
        new_btn.clicked.connect(self.new_tab_requested.emit)
        layout.addWidget(new_btn)

    def add_tab(self, title: str = "New Tab") -> int:
        """Add a new tab and return its index."""
        index = len(self.tab_buttons)
        btn = TabButton(index, title)
        btn.activated.connect(self._on_tab_activated)
        self.tab_buttons.append(btn)
        self.tabs_layout.insertWidget(self.tabs_layout.count() - 1, btn)
        return index

    def remove_tab(self, index: int):
        """Remove a tab at the given index."""
        if 0 <= index < len(self.tab_buttons):
            btn = self.tab_buttons.pop(index)
            self.tabs_layout.removeWidget(btn)
            btn.deleteLater()
            # Re-index remaining tabs
            for i, b in enumerate(self.tab_buttons):
                b.index = i

    def set_active(self, index: int):
        """Set the active tab."""
        self._active_index = index
        for i, btn in enumerate(self.tab_buttons):
            btn.set_active(i == index)

    def set_tab_title(self, index: int, title: str):
        """Update a tab's title."""
        if 0 <= index < len(self.tab_buttons):
            self.tab_buttons[index].set_title(title)

    def _on_tab_activated(self, index: int):
        self.set_active(index)
        self.tab_activated.emit(index)
