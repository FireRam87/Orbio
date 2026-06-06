"""Main browser window for Orbio."""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget
)
from PyQt6.QtCore import Qt, QUrl, QSize
from PyQt6.QtGui import QIcon, QKeySequence, QShortcut
from PyQt6.QtWebEngineCore import QWebEngineProfile

from orbio.webview import OrbioWebView
from orbio.ui.tab_bar import OrbioTabBar
from orbio.ui.radial_tabs import RadialTabRing
from orbio.ui.arc_navbar import ArcNavBar
from orbio.ui.fire_button import FireButton
from orbio.engine.privacy import PrivacyEngine
from orbio.engine.cookies import CookieManager


class OrbioBrowserWindow(QMainWindow):
    """The main Orbio browser window."""

    def __init__(self):
        super().__init__()
        self.tabs: list[OrbioWebView] = []
        self.active_tab_index = -1
        self._radial_mode = True

        self._setup_privacy()
        self._setup_profile()
        self._setup_ui()
        self._setup_shortcuts()
        self._new_tab("https://duckduckgo.com")

    def _setup_privacy(self):
        """Initialize the privacy/blocking engine."""
        self.privacy_engine = PrivacyEngine(parent=self)

    def _setup_profile(self):
        """Create a private-by-default web engine profile."""
        self.profile = QWebEngineProfile("Orbio", self)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )
        self.profile.setUrlRequestInterceptor(self.privacy_engine.interceptor)

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

        # Radial tab ring (signature UI)
        self.radial_ring = RadialTabRing()
        self.radial_ring.tab_activated.connect(self._switch_to_tab)
        self.radial_ring.new_tab_requested.connect(
            lambda: self._new_tab("https://duckduckgo.com")
        )
        layout.addWidget(self.radial_ring)

        # Linear tab bar (alternative mode)
        self.tab_bar = OrbioTabBar()
        self.tab_bar.tab_activated.connect(self._switch_to_tab)
        self.tab_bar.new_tab_requested.connect(
            lambda: self._new_tab("https://duckduckgo.com")
        )
        self.tab_bar.setVisible(not self._radial_mode)
        layout.addWidget(self.tab_bar)

        # Arc navigation bar
        self.arc_nav = ArcNavBar()
        self.arc_nav.navigate_requested.connect(self._on_arc_navigate)
        self.arc_nav.back_requested.connect(self._go_back)
        self.arc_nav.forward_requested.connect(self._go_forward)
        self.arc_nav.reload_requested.connect(self._reload)
        layout.addWidget(self.arc_nav)

        # Web content stack
        self.web_stack = QStackedWidget()
        layout.addWidget(self.web_stack)

        # Fire button (floating bottom-right)
        self.fire_button = FireButton(self)
        self.fire_button.burn_15min.connect(lambda: self._burn_data("15min"))
        self.fire_button.burn_1hour.connect(lambda: self._burn_data("1hour"))
        self.fire_button.burn_session.connect(lambda: self._burn_data("session"))
        self.fire_button.burn_everything.connect(lambda: self._burn_data("everything"))


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
        QShortcut(QKeySequence("Ctrl+Shift+R"), self, self._toggle_tab_mode)

    def _new_tab(self, url: str = "https://duckduckgo.com"):
        """Create a new tab and navigate to the URL."""
        view = OrbioWebView(profile=self.profile, parent=self)
        view.title_changed.connect(self._on_tab_title_changed)
        view.url_changed.connect(self._on_tab_url_changed)

        self.tabs.append(view)
        self.web_stack.addWidget(view)
        self.tab_bar.add_tab("New Tab")
        self.radial_ring.add_tab("New Tab")
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
        self.radial_ring.remove_tab(idx)

        new_idx = min(idx, len(self.tabs) - 1)
        self._switch_to_tab(new_idx)

    def _switch_to_tab(self, index: int):
        """Switch to a specific tab by index."""
        if 0 <= index < len(self.tabs):
            self.active_tab_index = index
            self.web_stack.setCurrentWidget(self.tabs[index])
            self.tab_bar.set_active(index)
            self.radial_ring.set_active(index)
            self._update_url_bar()
            title = self.tabs[index].title() or "Orbio"
            self.setWindowTitle(f"{title} — Orbio")

    def _current_view(self) -> OrbioWebView | None:
        """Get the current active web view."""
        if 0 <= self.active_tab_index < len(self.tabs):
            return self.tabs[self.active_tab_index]
        return None

    def _on_arc_navigate(self, text: str):
        """Handle navigation from the arc nav bar."""
        view = self._current_view()
        if view:
            view.navigate(text)


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
        self.arc_nav.focus_url()

    def _update_url_bar(self):
        """Update the URL bar with the current tab's URL."""
        view = self._current_view()
        if view:
            url = view.url().toString()
            if url and url != "about:blank":
                self.arc_nav.set_url(url)

    def _toggle_tab_mode(self):
        """Toggle between radial and linear tab modes."""
        self._radial_mode = not self._radial_mode
        self.radial_ring.setVisible(self._radial_mode)
        self.tab_bar.setVisible(not self._radial_mode)

    def _on_tab_title_changed(self, title: str):
        """Update window title when the active tab title changes."""
        sender = self.sender()
        if sender in self.tabs:
            idx = self.tabs.index(sender)
            self.tab_bar.set_tab_title(idx, title)
            self.radial_ring.set_tab_title(idx, title)
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
            self.arc_nav.set_url(url.toString())

    def _burn_data(self, level: str):
        """Clear browsing data at the specified level."""
        cookie_mgr = CookieManager(self.profile)

        if level == "everything":
            cookie_mgr.clear_all()
            self.profile.clearHttpCache()
            self.profile.clearAllVisitedLinks()
        elif level == "session":
            cookie_mgr.clear_session()
            self.profile.clearHttpCache()
        elif level == "1hour":
            cookie_mgr.clear_all()
            self.profile.clearHttpCache()
        elif level == "15min":
            cookie_mgr.clear_session()

        self.privacy_engine.stats.reset()

    def resizeEvent(self, event):
        """Reposition floating elements on resize."""
        super().resizeEvent(event)
        self.fire_button.move(
            self.width() - self.fire_button.width() - 20,
            self.height() - self.fire_button.height() - 20
        )
