"""Control Deck — Orbio's reimagined settings panel.

A full-window overlay with layered cards on the left rail and a detail
panel on the right. Animated transitions, live theme preview, frost-glow toggles.
"""

import math
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QLineEdit, QComboBox, QGraphicsOpacityEffect
)
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, pyqtSignal, QPropertyAnimation,
    QEasingCurve, QParallelAnimationGroup, QTimer, QSize
)
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QPainterPath,
    QLinearGradient, QRadialGradient, QFont, QMouseEvent, QPaintEvent
)

from orbio.core.settings import SettingsManager


class FrostToggle(QWidget):
    """A toggle switch with frost-glow on/off states."""

    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = checked
        self._knob_x = 24.0 if checked else 4.0
        self._glow = 1.0 if checked else 0.0

        self._anim = QPropertyAnimation(self, b"knob_x")
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self._glow_anim = QPropertyAnimation(self, b"glow_value")
        self._glow_anim.setDuration(200)

    def get_knob_x(self):
        return self._knob_x

    def set_knob_x(self, val):
        self._knob_x = val
        self.update()

    knob_x = property(get_knob_x, set_knob_x)

    def get_glow_value(self):
        return self._glow

    def set_glow_value(self, val):
        self._glow = val
        self.update()

    glow_value = property(get_glow_value, set_glow_value)

    @property
    def checked(self) -> bool:
        return self._checked

    def setChecked(self, val: bool):
        if val == self._checked:
            return
        self._checked = val
        self._anim.setStartValue(self._knob_x)
        self._anim.setEndValue(24.0 if val else 4.0)
        self._anim.start()
        self._glow_anim.setStartValue(self._glow)
        self._glow_anim.setEndValue(1.0 if val else 0.0)
        self._glow_anim.start()

    def mousePressEvent(self, event):
        self._checked = not self._checked
        self._anim.setStartValue(self._knob_x)
        self._anim.setEndValue(24.0 if self._checked else 4.0)
        self._anim.start()
        self._glow_anim.setStartValue(self._glow)
        self._glow_anim.setEndValue(1.0 if self._checked else 0.0)
        self._glow_anim.start()
        self.toggled.emit(self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        r = h / 2

        # Track
        track_color = QColor(26, 140, 255, int(180 * self._glow)) if self._checked else QColor(42, 42, 58)
        p.setBrush(QBrush(track_color))
        p.setPen(QPen(QColor(60, 60, 80), 1))
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)

        # Glow behind knob when on
        if self._glow > 0.1:
            glow_grad = QRadialGradient(self._knob_x + 10, h / 2, 16)
            glow_grad.setColorAt(0, QColor(77, 166, 255, int(100 * self._glow)))
            glow_grad.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(glow_grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(self._knob_x + 10, h / 2), 14, 14)

        # Knob
        knob_color = QColor(220, 240, 255) if self._checked else QColor(140, 140, 160)
        p.setBrush(QBrush(knob_color))
        p.setPen(QPen(QColor(200, 220, 240) if self._checked else QColor(80, 80, 100), 1))
        p.drawEllipse(QPointF(self._knob_x + 10, h / 2), 9, 9)

        p.end()


class CategoryCard(QWidget):
    """A clickable category card in the left rail."""

    clicked = pyqtSignal()

    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self._icon = icon
        self._label = label
        self._active = False
        self._hover = False
        self.setFixedHeight(56)
        self.setMinimumWidth(180)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

    def set_active(self, active: bool):
        self._active = active
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def mousePressEvent(self, event):
        self.clicked.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        if self._active:
            bg = QColor(26, 30, 46)
            border = QColor(77, 166, 255)
            text_color = QColor(230, 240, 255)
        elif self._hover:
            bg = QColor(20, 24, 36)
            border = QColor(60, 60, 80)
            text_color = QColor(200, 210, 230)
        else:
            bg = QColor(14, 16, 24)
            border = QColor(42, 42, 58)
            text_color = QColor(136, 136, 170)

        # Card background
        p.setBrush(QBrush(bg))
        p.setPen(QPen(border, 1.5 if self._active else 1))
        p.drawRoundedRect(QRectF(4, 4, w - 8, h - 8), 10, 10)

        # Active glow bar on left edge
        if self._active:
            p.setPen(Qt.PenStyle.NoPen)
            glow = QLinearGradient(8, h * 0.2, 8, h * 0.8)
            glow.setColorAt(0, QColor(77, 166, 255, 0))
            glow.setColorAt(0.5, QColor(77, 166, 255, 200))
            glow.setColorAt(1, QColor(77, 166, 255, 0))
            p.setBrush(QBrush(glow))
            p.drawRoundedRect(QRectF(6, h * 0.2, 3, h * 0.6), 1.5, 1.5)

        # Icon
        p.setFont(QFont("Inter", 16))
        p.setPen(QPen(text_color))
        p.drawText(QRectF(20, 0, 36, h), Qt.AlignmentFlag.AlignCenter, self._icon)

        # Label
        p.setFont(QFont("Inter", 11))
        p.drawText(QRectF(56, 0, w - 64, h), Qt.AlignmentFlag.AlignVCenter, self._label)

        p.end()


class SettingRow(QWidget):
    """A single setting row: label on left, control on right."""

    def __init__(self, label: str, description: str = "", parent=None):
        super().__init__(parent)
        self._label = label
        self._description = description
        self.setFixedHeight(64 if description else 48)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        h = self.height()
        w = self.width()

        # Label
        p.setFont(QFont("Inter", 12))
        p.setPen(QPen(QColor(220, 225, 240)))
        p.drawText(QRectF(16, 0, w * 0.6, h * 0.6 if self._description else h),
                   Qt.AlignmentFlag.AlignVCenter, self._label)

        # Description
        if self._description:
            p.setFont(QFont("Inter", 9))
            p.setPen(QPen(QColor(100, 100, 130)))
            p.drawText(QRectF(16, h * 0.5, w * 0.6, h * 0.4),
                       Qt.AlignmentFlag.AlignTop, self._description)

        p.end()


class ControlDeck(QWidget):
    """The main Control Deck overlay — Orbio's settings UI."""

    closed = pyqtSignal()
    theme_change_requested = pyqtSignal(str)
    settings_updated = pyqtSignal()

    CATEGORIES = [
        ("🛡", "Privacy Shield"),
        ("🎨", "Appearance"),
        ("🔍", "Search Engine"),
        ("⚙", "Behavior"),
        ("⌨", "Shortcuts"),
        ("ℹ", "About"),
    ]

    def __init__(self, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self._settings = settings_manager
        self._active_category = 0
        self._cards: list[CategoryCard] = []
        self._detail_widgets: list[QWidget] = []

        self.setStyleSheet("background: transparent;")
        self._build_ui()

    def _build_ui(self):
        """Construct the Control Deck layout."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left rail (category cards)
        left_rail = QWidget()
        left_rail.setFixedWidth(210)
        left_rail.setStyleSheet("background: #0a0a10; border-right: 1px solid #1a1a2a;")
        left_layout = QVBoxLayout(left_rail)
        left_layout.setContentsMargins(12, 24, 12, 24)
        left_layout.setSpacing(4)

        # Title
        title = QLabel("Control Deck")
        title.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #e8e8f0; background: transparent; border: none; padding: 8px 0 16px 8px;")
        left_layout.addWidget(title)

        for i, (icon, label) in enumerate(self.CATEGORIES):
            card = CategoryCard(icon, label)
            card.clicked.connect(lambda idx=i: self._switch_category(idx))
            self._cards.append(card)
            left_layout.addWidget(card)

        left_layout.addStretch()

        # Version label at bottom
        ver_label = QLabel("Orbio v0.2.0")
        ver_label.setFont(QFont("Inter", 9))
        ver_label.setStyleSheet("color: #555566; background: transparent; border: none; padding: 8px;")
        left_layout.addWidget(ver_label)

        main_layout.addWidget(left_rail)

        # Right detail panel
        self._detail_area = QScrollArea()
        self._detail_area.setWidgetResizable(True)
        self._detail_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._detail_area.setStyleSheet("""
            QScrollArea { background: #0e0e16; border: none; }
            QScrollBar:vertical { width: 6px; background: transparent; }
            QScrollBar::handle:vertical { background: #2a2a3a; border-radius: 3px; }
        """)

        self._build_detail_panels()
        main_layout.addWidget(self._detail_area)

        self._switch_category(0)

    def _build_detail_panels(self):
        """Build all category detail panels."""
        self._detail_widgets = [
            self._build_privacy_panel(),
            self._build_appearance_panel(),
            self._build_search_panel(),
            self._build_behavior_panel(),
            self._build_shortcuts_panel(),
            self._build_about_panel(),
        ]

    def _build_privacy_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background: #0e0e16;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(8)

        header = QLabel("Privacy Shield")
        header.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        header.setStyleSheet("color: #e8e8f0; background: transparent;")
        layout.addWidget(header)

        desc = QLabel("Control how Orbio protects your browsing.")
        desc.setFont(QFont("Inter", 11))
        desc.setStyleSheet("color: #8888aa; background: transparent; margin-bottom: 16px;")
        layout.addWidget(desc)

        # Block Trackers
        row1 = self._make_toggle_row("Block Trackers", "Prevent known tracking scripts from loading",
                                     self._settings.privacy.block_trackers,
                                     lambda v: self._update_privacy("block_trackers", v))
        layout.addWidget(row1)

        # Block Ads
        row2 = self._make_toggle_row("Block Ads", "Remove advertisements using filter lists",
                                     self._settings.privacy.block_ads,
                                     lambda v: self._update_privacy("block_ads", v))
        layout.addWidget(row2)

        # HTTPS Only
        row3 = self._make_toggle_row("HTTPS-Only Mode", "Automatically upgrade connections to HTTPS",
                                     self._settings.privacy.https_only,
                                     lambda v: self._update_privacy("https_only", v))
        layout.addWidget(row3)

        # Cookie Auto-Clear
        row4 = self._make_toggle_row("Clear Cookies on Tab Close", "Delete cookies when you close a tab",
                                     self._settings.privacy.cookie_auto_clear_on_tab_close,
                                     lambda v: self._update_privacy("cookie_auto_clear_on_tab_close", v))
        layout.addWidget(row4)

        # DNT
        row5 = self._make_toggle_row("Send Do Not Track", "Request websites not to track you",
                                     self._settings.privacy.send_dnt,
                                     lambda v: self._update_privacy("send_dnt", v))
        layout.addWidget(row5)

        layout.addStretch()
        return panel

    def _build_appearance_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background: #0e0e16;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(8)

        header = QLabel("Appearance")
        header.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        header.setStyleSheet("color: #e8e8f0; background: transparent;")
        layout.addWidget(header)

        desc = QLabel("Customize the look and feel of Orbio.")
        desc.setFont(QFont("Inter", 11))
        desc.setStyleSheet("color: #8888aa; background: transparent; margin-bottom: 16px;")
        layout.addWidget(desc)

        # Theme selector
        theme_row = QWidget()
        theme_row.setFixedHeight(56)
        theme_row.setStyleSheet("background: transparent;")
        tr_layout = QHBoxLayout(theme_row)
        tr_layout.setContentsMargins(16, 0, 16, 0)

        tr_label = QLabel("Theme")
        tr_label.setFont(QFont("Inter", 12))
        tr_label.setStyleSheet("color: #e0e0f0; background: transparent;")
        tr_layout.addWidget(tr_label)
        tr_layout.addStretch()

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["default", "midnight", "emerald"])
        self._theme_combo.setCurrentText(self._settings.appearance.theme)
        self._theme_combo.setStyleSheet("""
            QComboBox {
                background: #1a1a25; color: #e0e0f0; border: 1px solid #2a2a3a;
                border-radius: 6px; padding: 6px 12px; min-width: 120px;
            }
            QComboBox:hover { border-color: #4da6ff; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: #1a1a25; color: #e0e0f0; border: 1px solid #2a2a3a;
                selection-background-color: #4da6ff;
            }
        """)
        self._theme_combo.currentTextChanged.connect(self._on_theme_changed)
        tr_layout.addWidget(self._theme_combo)
        layout.addWidget(theme_row)

        # Radial tabs toggle
        row1 = self._make_toggle_row("Radial Tab Ring", "Use the circular tab ring (vs linear tab bar)",
                                     self._settings.appearance.radial_tabs,
                                     lambda v: self._update_appearance("radial_tabs", v))
        layout.addWidget(row1)

        # Glow effects
        row2 = self._make_toggle_row("Glow Effects", "Show frost-glow animations on interactive elements",
                                     self._settings.appearance.show_glow_effects,
                                     lambda v: self._update_appearance("show_glow_effects", v))
        layout.addWidget(row2)

        layout.addStretch()
        return panel

    def _build_search_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background: #0e0e16;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(8)

        header = QLabel("Search Engine")
        header.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        header.setStyleSheet("color: #e8e8f0; background: transparent;")
        layout.addWidget(header)

        desc = QLabel("Choose your default search provider.")
        desc.setFont(QFont("Inter", 11))
        desc.setStyleSheet("color: #8888aa; background: transparent; margin-bottom: 16px;")
        layout.addWidget(desc)

        # Engine selector
        engine_row = QWidget()
        engine_row.setFixedHeight(56)
        engine_row.setStyleSheet("background: transparent;")
        er_layout = QHBoxLayout(engine_row)
        er_layout.setContentsMargins(16, 0, 16, 0)

        er_label = QLabel("Default Engine")
        er_label.setFont(QFont("Inter", 12))
        er_label.setStyleSheet("color: #e0e0f0; background: transparent;")
        er_layout.addWidget(er_label)
        er_layout.addStretch()

        self._engine_combo = QComboBox()
        engines = list(self._settings.search.engines.keys())
        self._engine_combo.addItems(engines)
        self._engine_combo.setCurrentText(self._settings.search.engine)
        self._engine_combo.setStyleSheet("""
            QComboBox {
                background: #1a1a25; color: #e0e0f0; border: 1px solid #2a2a3a;
                border-radius: 6px; padding: 6px 12px; min-width: 140px;
            }
            QComboBox:hover { border-color: #4da6ff; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: #1a1a25; color: #e0e0f0; border: 1px solid #2a2a3a;
                selection-background-color: #4da6ff;
            }
        """)
        self._engine_combo.currentTextChanged.connect(self._on_engine_changed)
        er_layout.addWidget(self._engine_combo)
        layout.addWidget(engine_row)

        # Search suggestions
        row1 = self._make_toggle_row("Search Suggestions", "Show suggestions as you type (requires network)",
                                     self._settings.search.search_suggestions,
                                     lambda v: self._update_search("search_suggestions", v))
        layout.addWidget(row1)

        layout.addStretch()
        return panel

    def _build_behavior_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background: #0e0e16;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(8)

        header = QLabel("Behavior")
        header.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        header.setStyleSheet("color: #e8e8f0; background: transparent;")
        layout.addWidget(header)

        desc = QLabel("Control how Orbio behaves.")
        desc.setFont(QFont("Inter", 11))
        desc.setStyleSheet("color: #8888aa; background: transparent; margin-bottom: 16px;")
        layout.addWidget(desc)

        # Restore session
        row1 = self._make_toggle_row("Restore Session", "Reopen tabs from your last session on launch",
                                     self._settings.behavior.restore_session,
                                     lambda v: self._update_behavior("restore_session", v))
        layout.addWidget(row1)

        # Show greeting
        row2 = self._make_toggle_row("Show Greeting", "Display a time-based greeting on the Surface page",
                                     self._settings.behavior.show_greeting,
                                     lambda v: self._update_behavior("show_greeting", v))
        layout.addWidget(row2)

        # Smooth scrolling
        row3 = self._make_toggle_row("Smooth Scrolling", "Enable smooth scroll animations",
                                     self._settings.behavior.smooth_scrolling,
                                     lambda v: self._update_behavior("smooth_scrolling", v))
        layout.addWidget(row3)

        layout.addStretch()
        return panel

    def _build_shortcuts_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background: #0e0e16;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(8)

        header = QLabel("Shortcuts")
        header.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        header.setStyleSheet("color: #e8e8f0; background: transparent;")
        layout.addWidget(header)

        desc = QLabel("Keyboard shortcuts reference.")
        desc.setFont(QFont("Inter", 11))
        desc.setStyleSheet("color: #8888aa; background: transparent; margin-bottom: 16px;")
        layout.addWidget(desc)

        shortcuts = [
            ("Ctrl+T", "New tab"),
            ("Ctrl+W", "Close tab"),
            ("Ctrl+L", "Focus URL bar"),
            ("Ctrl+Tab", "Next tab"),
            ("Ctrl+Shift+Tab", "Previous tab"),
            ("Ctrl+Shift+R", "Toggle radial/linear tabs"),
            ("Ctrl+Shift+P", "Privacy dashboard"),
            ("Ctrl+H", "History (Drift)"),
            ("Ctrl+B", "Bookmarks (Constellations)"),
            ("Ctrl+J", "Downloads (Depths)"),
            ("Ctrl+,", "Control Deck (this panel)"),
            ("Ctrl+F", "Find in page"),
            ("F5", "Reload"),
        ]

        for key, action in shortcuts:
            row = QWidget()
            row.setFixedHeight(36)
            row.setStyleSheet("background: transparent;")
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(16, 0, 16, 0)

            action_lbl = QLabel(action)
            action_lbl.setFont(QFont("Inter", 11))
            action_lbl.setStyleSheet("color: #c8c8e0; background: transparent;")
            r_layout.addWidget(action_lbl)
            r_layout.addStretch()

            key_lbl = QLabel(key)
            key_lbl.setFont(QFont("JetBrains Mono", 10))
            key_lbl.setStyleSheet(
                "color: #4da6ff; background: #1a1a25; border: 1px solid #2a2a3a; "
                "border-radius: 4px; padding: 2px 8px;"
            )
            r_layout.addWidget(key_lbl)
            layout.addWidget(row)

        layout.addStretch()
        return panel

    def _build_about_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background: #0e0e16;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(12)

        header = QLabel("About Orbio")
        header.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        header.setStyleSheet("color: #e8e8f0; background: transparent;")
        layout.addWidget(header)

        info_lines = [
            ("Version", "0.2.0"),
            ("Engine", "Qt WebEngine (Chromium)"),
            ("Framework", "PyQt6"),
            ("License", "MIT"),
            ("Privacy", "No telemetry, no accounts, no tracking"),
        ]

        for label, value in info_lines:
            row = QWidget()
            row.setFixedHeight(36)
            row.setStyleSheet("background: transparent;")
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(16, 0, 16, 0)

            lbl = QLabel(label)
            lbl.setFont(QFont("Inter", 11))
            lbl.setStyleSheet("color: #8888aa; background: transparent;")
            r_layout.addWidget(lbl)
            r_layout.addStretch()

            val = QLabel(value)
            val.setFont(QFont("Inter", 11))
            val.setStyleSheet("color: #e0e0f0; background: transparent;")
            r_layout.addWidget(val)
            layout.addWidget(row)

        layout.addStretch()

        tagline = QLabel("Privacy-first browsing, reimagined.")
        tagline.setFont(QFont("Inter", 10))
        tagline.setStyleSheet("color: #555566; background: transparent;")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tagline)

        return panel

    def _make_toggle_row(self, label: str, description: str, initial: bool, callback) -> QWidget:
        """Create a setting row with a frost toggle."""
        row = QWidget()
        row.setFixedHeight(64)
        row.setStyleSheet("background: transparent;")
        r_layout = QHBoxLayout(row)
        r_layout.setContentsMargins(16, 0, 16, 0)

        text_widget = QWidget()
        text_widget.setStyleSheet("background: transparent;")
        t_layout = QVBoxLayout(text_widget)
        t_layout.setContentsMargins(0, 0, 0, 0)
        t_layout.setSpacing(2)

        lbl = QLabel(label)
        lbl.setFont(QFont("Inter", 12))
        lbl.setStyleSheet("color: #e0e0f0; background: transparent;")
        t_layout.addWidget(lbl)

        desc_lbl = QLabel(description)
        desc_lbl.setFont(QFont("Inter", 9))
        desc_lbl.setStyleSheet("color: #6a6a8a; background: transparent;")
        t_layout.addWidget(desc_lbl)

        r_layout.addWidget(text_widget)
        r_layout.addStretch()

        toggle = FrostToggle(initial)
        toggle.toggled.connect(callback)
        r_layout.addWidget(toggle)

        return row

    def _switch_category(self, index: int):
        """Switch to a different category panel."""
        self._active_category = index
        for i, card in enumerate(self._cards):
            card.set_active(i == index)

        if 0 <= index < len(self._detail_widgets):
            self._detail_area.setWidget(self._detail_widgets[index])

    def _update_privacy(self, key: str, value):
        setattr(self._settings.privacy, key, value)
        self._settings.save()
        self.settings_updated.emit()

    def _update_appearance(self, key: str, value):
        setattr(self._settings.appearance, key, value)
        self._settings.save()
        self.settings_updated.emit()

    def _update_search(self, key: str, value):
        setattr(self._settings.search, key, value)
        self._settings.save()
        self.settings_updated.emit()

    def _update_behavior(self, key: str, value):
        setattr(self._settings.behavior, key, value)
        self._settings.save()
        self.settings_updated.emit()

    def _on_theme_changed(self, name: str):
        self._settings.appearance.theme = name
        self._settings.save()
        self.theme_change_requested.emit(name)

    def _on_engine_changed(self, name: str):
        self._settings.search.engine = name
        self._settings.save()
        self.settings_updated.emit()

    def paintEvent(self, event):
        """Draw the frosted glass backdrop."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(6, 6, 12, 240))
        p.end()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.closed.emit()
        else:
            super().keyPressEvent(event)
