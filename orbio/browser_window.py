"""Main browser window for Orbio."""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QStackedWidget, QLabel
)
from PyQt6.QtCore import Qt, QUrl, QSize
from PyQt6.QtGui import QIcon, QKeySequence, QShortcut
from PyQt6.QtWebEngineCore import QWebEngineProfile

from orbio.webview import OrbioWebView
from orbio.ui.tab_bar import OrbioTabBar


class OrbioBrowserWindow(QMainWindow):
    """The main Orbio browser window."""

    def __init__(self):
        super().__init__()
        self.tabs: list[OrbioWebView] = []
        self.active_tab_index = -1

        self._setup_profile()
        self._setup_ui()
        self._setup_shortcuts()
        self._new_tab("https://duckduckgo.com")

    def _setup_profile(self):
        """Create a private-by-default web engine profile."""
        self.profile = QWebEngineProfile("Orbio", self)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )

    def _setup_ui(self):
        """Build the browser UI."""
        self.setWindowTitle("Orbio")
        self.setMinimumSize(1024, 700)
        self.resize(1400, 900)

        self._apply_dark_style()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab bar
        self.tab_bar = OrbioTabBar()
        self.tab_bar.tab_activated.connect(self._switch_to_tab)
        self.tab_bar.new_tab_requested.connect(
            lambda: self._new_tab("https://duckduckgo.com")
        )
        layout.addWidget(self.tab_bar)

        # Navigation bar
        nav_bar = self._create_nav_bar()
        layout.addWidget(nav_bar)

        # Web content stack
        self.web_stack = QStackedWidget()
        layout.addWidget(self.web_stack)

    def _create_nav_bar(self) -> QWidget:
        """Create the navigation bar."""
        nav = QWidget()
        nav.setFixedHeight(48)
        nav.setStyleSheet("background-color: #12121a; border-bottom: 1px solid #2a2a3a;")

        layout = QHBoxLayout(nav)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        btn_style = """
            QPushButton {
                background: transparent;
                color: #8888aa;
                border: none;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #1a1a25;
                color: #4da6ff;
            }
            QPushButton:pressed {
                background: #2a2a3a;
            }
        """

        self.btn_back = QPushButton("←")
        self.btn_back.setStyleSheet(btn_style)
        self.btn_back.clicked.connect(self._go_back)
        layout.addWidget(self.btn_back)

        self.btn_forward = QPushButton("→")
        self.btn_forward.setStyleSheet(btn_style)
        self.btn_forward.clicked.connect(self._go_forward)
        layout.addWidget(self.btn_forward)

        self.btn_reload = QPushButton("↻")
        self.btn_reload.setStyleSheet(btn_style)
        self.btn_reload.clicked.connect(self._reload)
        layout.addWidget(self.btn_reload)

        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Search with DuckDuckGo or enter URL...")
        self.url_bar.setStyleSheet("""
            QLineEdit {
                background: #0a0a0f;
                color: #e8e8f0;
                border: 1px solid #2a2a3a;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 13px;
                selection-background-color: #4da6ff;
            }
            QLineEdit:focus {
                border-color: #4da6ff;
                box-shadow: 0 0 8px rgba(77, 166, 255, 0.3);
            }
        """)
        self.url_bar.returnPressed.connect(self._navigate_to_url)
        layout.addWidget(self.url_bar)

        self.btn_new_tab = QPushButton("+")
        self.btn_new_tab.setStyleSheet(btn_style)
        self.btn_new_tab.clicked.connect(lambda: self._new_tab("https://duckduckgo.com"))
        layout.addWidget(self.btn_new_tab)

        return nav

    def _apply_dark_style(self):
        """Apply the dark Orbio theme to the window."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0a0a0f;
            }
        """)

    def _setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        QShortcut(QKeySequence("Ctrl+T"), self, lambda: self._new_tab("https://duckduckgo.com"))
        QShortcut(QKeySequence("Ctrl+W"), self, self._close_current_tab)
        QShortcut(QKeySequence("Ctrl+L"), self, self._focus_url_bar)
        QShortcut(QKeySequence("Ctrl+R"), self, self._reload)
        QShortcut(QKeySequence("F5"), self, self._reload)
        QShortcut(QKeySequence("Alt+Left"), self, self._go_back)
        QShortcut(QKeySequence("Alt+Right"), self, self._go_forward)
        QShortcut(QKeySequence("Ctrl+Tab"), self, self._next_tab)
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self, self._prev_tab)

    def _new_tab(self, url: str = "https://duckduckgo.com"):
        """Create a new tab and navigate to the URL."""
        view = OrbioWebView(profile=self.profile, parent=self)
        view.title_changed.connect(self._on_tab_title_changed)
        view.url_changed.connect(self._on_tab_url_changed)

        self.tabs.append(view)
        self.web_stack.addWidget(view)
        self.tab_bar.add_tab("New Tab")
        self._switch_to_tab(len(self.tabs) - 1)
        view.navigate(url)

    def _close_current_tab(self):
        """Close the active tab."""
        if len(self.tabs) <= 1:
            return

        idx = self.active_tab_index
        view = self.tabs.pop(idx)
        self.web_stack.removeWidget(view)
        view.deleteLater()
        self.tab_bar.remove_tab(idx)

        new_idx = min(idx, len(self.tabs) - 1)
        self._switch_to_tab(new_idx)

    def _switch_to_tab(self, index: int):
        """Switch to a specific tab by index."""
        if 0 <= index < len(self.tabs):
            self.active_tab_index = index
            self.web_stack.setCurrentWidget(self.tabs[index])
            self.tab_bar.set_active(index)
            self._update_url_bar()
            title = self.tabs[index].title() or "Orbio"
            self.setWindowTitle(f"{title} — Orbio")

    def _current_view(self) -> OrbioWebView | None:
        """Get the current active web view."""
        if 0 <= self.active_tab_index < len(self.tabs):
            return self.tabs[self.active_tab_index]
        return None

    def _navigate_to_url(self):
        """Navigate the current tab to the URL bar content."""
        view = self._current_view()
        if view:
            view.navigate(self.url_bar.text())

    def _go_back(self):
        view = self._current_view()
        if view:
            view.back()

    def _go_forward(self):
        view = self._current_view()
        if view:
            view.forward()

    def _reload(self):
        view = self._current_view()
        if view:
            view.reload()

    def _focus_url_bar(self):
        self.url_bar.setFocus()
        self.url_bar.selectAll()

    def _update_url_bar(self):
        """Update the URL bar with the current tab's URL."""
        view = self._current_view()
        if view:
            url = view.url().toString()
            if url and url != "about:blank":
                self.url_bar.setText(url)

    def _on_tab_title_changed(self, title: str):
        """Update window title when the active tab title changes."""
        view = self._current_view()
        sender = self.sender()
        if sender in self.tabs:
            idx = self.tabs.index(sender)
            self.tab_bar.set_tab_title(idx, title)
            if idx == self.active_tab_index:
                self.setWindowTitle(f"{title} — Orbio")

    def _next_tab(self):
        """Switch to the next tab."""
        if self.tabs:
            self._switch_to_tab((self.active_tab_index + 1) % len(self.tabs))

    def _prev_tab(self):
        """Switch to the previous tab."""
        if self.tabs:
            self._switch_to_tab((self.active_tab_index - 1) % len(self.tabs))

    def _on_tab_url_changed(self, url: QUrl):
        """Update URL bar when navigation occurs."""
        view = self._current_view()
        if view and view == self.sender():
            self.url_bar.setText(url.toString())
