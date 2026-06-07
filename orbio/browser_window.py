"""Main browser window for Orbio."""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget
)
from PyQt6.QtCore import Qt, QUrl, QSize, QTimer
from PyQt6.QtGui import QIcon, QKeySequence, QShortcut
from PyQt6.QtWebEngineCore import QWebEngineProfile

from orbio.webview import OrbioWebView
from orbio.ui.tab_bar import OrbioTabBar
from orbio.ui.radial_tabs import RadialTabRing
from orbio.ui.arc_navbar import ArcNavBar
from orbio.ui.freeze_button import FreezeButton
from orbio.ui.privacy_dash import PrivacyDashboard
from orbio.ui.control_deck import ControlDeck
from orbio.ui.drift import DriftView
from orbio.ui.constellations import ConstellationView
from orbio.ui.depths import DepthsPanel
from orbio.ui.surface import SurfacePage
from orbio.engine.privacy import PrivacyEngine
from orbio.engine.cookies import CookieManager
from orbio.themes.engine import ThemeEngine
from orbio.core.settings import SettingsManager
from orbio.core.history import HistoryManager
from orbio.core.bookmarks import BookmarkManager
from orbio.core.downloads import DownloadManager


class OrbioBrowserWindow(QMainWindow):
    """The main Orbio browser window."""

    def __init__(self):
        super().__init__()
        self.tabs: list[OrbioWebView] = []
        self.active_tab_index = -1

        self._setup_core()
        self._setup_privacy()
        self._setup_theme()
        self._setup_profile()
        self._setup_ui()
        self._setup_overlays()
        self._setup_shortcuts()
        self._open_initial_tabs()

    def _setup_core(self):
        """Initialize core managers."""
        self.settings_mgr = SettingsManager(parent=self)
        self.history_mgr = HistoryManager(parent=self)
        self.bookmark_mgr = BookmarkManager(parent=self)
        self.download_mgr = DownloadManager(
            default_dir=self.settings_mgr.behavior.download_dir,
            parent=self
        )

    def _setup_privacy(self):
        """Initialize the privacy/blocking engine."""
        self.privacy_engine = PrivacyEngine(parent=self)

    def _setup_theme(self):
        """Initialize the theme engine."""
        self.theme_engine = ThemeEngine(parent=self)
        theme_name = self.settings_mgr.appearance.theme
        if not self.theme_engine.load_theme(theme_name):
            self.theme_engine.load_default()
        self.theme_engine.theme_changed.connect(self._apply_theme)

    def _setup_profile(self):
        """Create a private-by-default web engine profile."""
        self.profile = QWebEngineProfile("Orbio", self)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )
        self.profile.setUrlRequestInterceptor(self.privacy_engine.interceptor)
        self.profile.downloadRequested.connect(self._on_download_requested)

    def _setup_ui(self):
        """Build the browser UI."""
        self.setWindowTitle("Orbio")
        self.setMinimumSize(1024, 700)
        self.resize(1400, 900)

        self._apply_dark_style()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Main content column
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Radial tab ring (signature UI)
        self.radial_ring = RadialTabRing()
        self.radial_ring.tab_activated.connect(self._switch_to_tab)
        self.radial_ring.new_tab_requested.connect(self._new_tab_surface)
        layout.addWidget(self.radial_ring)

        # Linear tab bar (alternative mode)
        self.tab_bar = OrbioTabBar()
        self.tab_bar.tab_activated.connect(self._switch_to_tab)
        self.tab_bar.new_tab_requested.connect(self._new_tab_surface)
        self.tab_bar.setVisible(not self.settings_mgr.appearance.radial_tabs)
        self.radial_ring.setVisible(self.settings_mgr.appearance.radial_tabs)
        layout.addWidget(self.tab_bar)

        # Arc navigation bar
        self.arc_nav = ArcNavBar()
        self.arc_nav.navigate_requested.connect(self._on_arc_navigate)
        self.arc_nav.back_requested.connect(self._go_back)
        self.arc_nav.forward_requested.connect(self._go_forward)
        self.arc_nav.reload_requested.connect(self._reload)
        self.arc_nav.bookmark_requested.connect(self._toggle_bookmark)
        layout.addWidget(self.arc_nav)

        # Web content stack (holds webviews + surface page)
        self.web_stack = QStackedWidget()
        layout.addWidget(self.web_stack)

        # Surface page (new tab page)
        self.surface_page = SurfacePage()
        self.surface_page.navigate_requested.connect(self._navigate_current)
        self.surface_page.search_requested.connect(self._search_from_surface)
        self.web_stack.addWidget(self.surface_page)

        main_layout.addWidget(content)

        # Downloads panel (right sidebar, hidden by default)
        self.depths_panel = DepthsPanel(self.download_mgr, self)
        self.depths_panel.closed.connect(self._hide_depths)
        self.depths_panel.setVisible(False)
        main_layout.addWidget(self.depths_panel)

        # Freeze button (floating bottom-right)
        self.freeze_button = FreezeButton(self)
        self.freeze_button.freeze_15min.connect(lambda: self._freeze_data("15min"))
        self.freeze_button.freeze_1hour.connect(lambda: self._freeze_data("1hour"))
        self.freeze_button.freeze_session.connect(lambda: self._freeze_data("session"))
        self.freeze_button.freeze_everything.connect(lambda: self._freeze_data("everything"))

        # Privacy dashboard overlay
        self.privacy_dash = PrivacyDashboard(self.privacy_engine.stats, self)

    def _setup_overlays(self):
        """Create overlay panels (Control Deck, Drift, Constellations)."""
        self.control_deck = ControlDeck(self.settings_mgr, self)
        self.control_deck.closed.connect(self._hide_control_deck)
        self.control_deck.theme_change_requested.connect(self._on_theme_switch)
        self.control_deck.settings_updated.connect(self._on_settings_updated)
        self.control_deck.setVisible(False)

        self.drift_view = DriftView(self.history_mgr, self)
        self.drift_view.navigate_requested.connect(self._navigate_from_overlay)
        self.drift_view.closed.connect(self._hide_drift)
        self.drift_view.setVisible(False)

        self.constellation_view = ConstellationView(self.bookmark_mgr, self)
        self.constellation_view.navigate_requested.connect(self._navigate_from_overlay)
        self.constellation_view.closed.connect(self._hide_constellations)
        self.constellation_view.setVisible(False)

    def _apply_dark_style(self):
        """Apply the current theme stylesheet."""
        self.setStyleSheet(self.theme_engine.generate_stylesheet())

    def _apply_theme(self, theme):
        """Handle theme change signal."""
        self.setStyleSheet(self.theme_engine.generate_stylesheet())

    def _setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        QShortcut(QKeySequence("Ctrl+T"), self, self._new_tab_surface)
        QShortcut(QKeySequence("Ctrl+W"), self, self._close_current_tab)
        QShortcut(QKeySequence("Ctrl+L"), self, self._focus_url_bar)
        QShortcut(QKeySequence("Ctrl+R"), self, self._reload)
        QShortcut(QKeySequence("F5"), self, self._reload)
        QShortcut(QKeySequence("Alt+Left"), self, self._go_back)
        QShortcut(QKeySequence("Alt+Right"), self, self._go_forward)
        QShortcut(QKeySequence("Ctrl+Tab"), self, self._next_tab)
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self, self._prev_tab)
        QShortcut(QKeySequence("Ctrl+Shift+R"), self, self._toggle_tab_mode)
        QShortcut(QKeySequence("Ctrl+Shift+P"), self, self._toggle_privacy_dash)
        QShortcut(QKeySequence("Ctrl+,"), self, self._toggle_control_deck)
        QShortcut(QKeySequence("Ctrl+H"), self, self._toggle_drift)
        QShortcut(QKeySequence("Ctrl+B"), self, self._toggle_constellations)
        QShortcut(QKeySequence("Ctrl+J"), self, self._toggle_depths)

    def _open_initial_tabs(self):
        """Open session tabs or a fresh surface page."""
        if self.settings_mgr.behavior.restore_session and self.settings_mgr.settings.session_tabs:
            for url in self.settings_mgr.settings.session_tabs:
                self._new_tab(url)
            active = self.settings_mgr.settings.session_active_tab
            if 0 <= active < len(self.tabs):
                self._switch_to_tab(active)
        else:
            self._new_tab_surface()

    # ──── Tab management ────

    def _new_tab_surface(self):
        """Open a new tab showing the Surface page."""
        self._new_tab(None)

    def _new_tab(self, url: str | None = None):
        """Create a new tab. If url is None, show the Surface page."""
        view = OrbioWebView(profile=self.profile, parent=self)
        view.title_changed.connect(self._on_tab_title_changed)
        view.url_changed.connect(self._on_tab_url_changed)
        view.loading_finished.connect(self._on_tab_load_finished)

        self.tabs.append(view)
        self.web_stack.addWidget(view)
        self.tab_bar.add_tab("New Tab")
        self.radial_ring.add_tab("New Tab")
        self._switch_to_tab(len(self.tabs) - 1)

        if url:
            view.navigate(url)
            self.web_stack.setCurrentWidget(view)
        else:
            self._show_surface()

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
            # Capture thumbnail of the tab we're leaving
            self._capture_thumbnail(self.active_tab_index)

            self.active_tab_index = index
            view = self.tabs[index]

            # If this tab has never navigated, show surface
            if view.url().isEmpty() or view.url().toString() == "about:blank":
                self._show_surface()
            else:
                self.web_stack.setCurrentWidget(view)

            self.tab_bar.set_active(index)
            self.radial_ring.set_active(index)
            self._update_url_bar()
            title = view.title() or "Orbio"
            self.setWindowTitle(f"{title} — Orbio")

    def _show_surface(self):
        """Display the Surface new-tab page."""
        frequent = self.history_mgr.get_frequent_sites(8)
        self.surface_page.set_frequent_sites(frequent)
        self.surface_page.set_trackers_blocked(self.privacy_engine.stats.trackers_blocked)
        self.surface_page.set_show_greeting(self.settings_mgr.behavior.show_greeting)
        self.web_stack.setCurrentWidget(self.surface_page)
        self.arc_nav.set_url("")

    def _capture_thumbnail(self, index: int):
        """Capture a thumbnail of the given tab for the radial ring preview."""
        if 0 <= index < len(self.tabs):
            view = self.tabs[index]
            if not view.url().isEmpty() and view.url().toString() != "about:blank":
                pixmap = view.grab()
                self.radial_ring.set_thumbnail(index, pixmap)

    def _current_view(self) -> OrbioWebView | None:
        """Get the current active web view."""
        if 0 <= self.active_tab_index < len(self.tabs):
            return self.tabs[self.active_tab_index]
        return None

    # ──── Navigation ────

    def _on_arc_navigate(self, text: str):
        """Handle navigation from the arc nav bar."""
        view = self._current_view()
        if view:
            if self.web_stack.currentWidget() == self.surface_page:
                self.web_stack.setCurrentWidget(view)
            view.navigate(text)

    def _navigate_current(self, url: str):
        """Navigate the current tab to a URL."""
        view = self._current_view()
        if view:
            self.web_stack.setCurrentWidget(view)
            view.navigate(url)

    def _navigate_from_overlay(self, url: str):
        """Navigate from an overlay (drift/constellations) — opens in new tab."""
        self._new_tab(url)
        self._hide_all_overlays()

    def _search_from_surface(self, query: str):
        """Handle search from the surface page."""
        url = self.settings_mgr.get_search_url(query)
        view = self._current_view()
        if view:
            self.web_stack.setCurrentWidget(view)
            view.navigate(url)

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
            else:
                self.arc_nav.set_url("")

    # ──── Tab UI ────

    def _toggle_tab_mode(self):
        """Toggle between radial and linear tab modes."""
        radial = not self.radial_ring.isVisible()
        self.radial_ring.setVisible(radial)
        self.tab_bar.setVisible(not radial)
        self.settings_mgr.appearance.radial_tabs = radial
        self.settings_mgr.save()

    def _next_tab(self):
        if self.tabs:
            self._switch_to_tab((self.active_tab_index + 1) % len(self.tabs))

    def _prev_tab(self):
        if self.tabs:
            self._switch_to_tab((self.active_tab_index - 1) % len(self.tabs))

    def _on_tab_title_changed(self, title: str):
        """Update window title when the active tab title changes."""
        sender = self.sender()
        if sender in self.tabs:
            idx = self.tabs.index(sender)
            self.tab_bar.set_tab_title(idx, title)
            self.radial_ring.set_tab_title(idx, title)
            if idx == self.active_tab_index:
                self.setWindowTitle(f"{title} — Orbio")

    def _on_tab_url_changed(self, url: QUrl):
        """Update URL bar and record history when navigation occurs."""
        view = self._current_view()
        if view and view == self.sender():
            url_str = url.toString()
            self.arc_nav.set_url(url_str)

            # Record in history
            referrer = ""
            self.history_mgr.record_visit(url_str, view.title() or "", referrer)

    def _on_tab_load_finished(self, ok: bool):
        """Handle page load completion — update history title, capture thumbnail."""
        view = self.sender()
        if view and view in self.tabs:
            idx = self.tabs.index(view)
            if ok and view.title():
                self.history_mgr.update_title(view.url().toString(), view.title())
            # Capture thumbnail after load
            QTimer.singleShot(500, lambda i=idx: self._capture_thumbnail(i))

    # ──── Bookmarks ────

    def _toggle_bookmark(self):
        """Add/remove bookmark for the current page."""
        view = self._current_view()
        if not view or view.url().isEmpty():
            return

        url = view.url().toString()
        if self.bookmark_mgr.is_bookmarked(url):
            bm = self.bookmark_mgr.get_by_url(url)
            if bm:
                self.bookmark_mgr.remove_bookmark(bm.id)
        else:
            self.bookmark_mgr.add_bookmark(url, view.title() or url)

    # ──── Downloads ────

    def _on_download_requested(self, request):
        """Handle download request from web engine."""
        self.download_mgr.handle_download(request)
        if not self.depths_panel.isVisible():
            self.depths_panel.show_depths()
            self.depths_panel.setVisible(True)

    # ──── Overlays ────

    def _toggle_control_deck(self):
        if self.control_deck.isVisible():
            self._hide_control_deck()
        else:
            self._hide_all_overlays()
            self.control_deck.setGeometry(self.centralWidget().rect())
            self.control_deck.setVisible(True)
            self.control_deck.raise_()

    def _hide_control_deck(self):
        self.control_deck.setVisible(False)

    def _toggle_drift(self):
        if self.drift_view.isVisible():
            self._hide_drift()
        else:
            self._hide_all_overlays()
            self.drift_view.setGeometry(self.centralWidget().rect())
            self.drift_view.show_drift()
            self.drift_view.raise_()

    def _hide_drift(self):
        self.drift_view.setVisible(False)

    def _toggle_constellations(self):
        if self.constellation_view.isVisible():
            self._hide_constellations()
        else:
            self._hide_all_overlays()
            self.constellation_view.setGeometry(self.centralWidget().rect())
            self.constellation_view.show_constellations()
            self.constellation_view.raise_()

    def _hide_constellations(self):
        self.constellation_view.setVisible(False)

    def _toggle_depths(self):
        visible = self.depths_panel.isVisible()
        self.depths_panel.setVisible(not visible)
        if not visible:
            self.depths_panel.show_depths()

    def _hide_depths(self):
        self.depths_panel.setVisible(False)

    def _toggle_privacy_dash(self):
        """Toggle the privacy dashboard overlay."""
        if self.privacy_dash.isVisible():
            self.privacy_dash.hide()
        else:
            self.privacy_dash.setGeometry(
                self.width() // 2 - 250,
                self.height() // 2 - 200,
                500, 400
            )
            self.privacy_dash.show_dashboard()

    def _hide_all_overlays(self):
        """Hide all full-screen overlays."""
        self.control_deck.setVisible(False)
        self.drift_view.setVisible(False)
        self.constellation_view.setVisible(False)

    # ──── Settings & Theme ────

    def _on_theme_switch(self, name: str):
        """Handle theme change from the Control Deck."""
        self.theme_engine.load_theme(name)

    def _on_settings_updated(self):
        """React to settings changes."""
        self.radial_ring.setVisible(self.settings_mgr.appearance.radial_tabs)
        self.tab_bar.setVisible(not self.settings_mgr.appearance.radial_tabs)

    # ──── Data clearing ────

    def _freeze_data(self, level: str):
        """Clear browsing data at the specified level."""
        cookie_mgr = CookieManager(self.profile)

        if level == "everything":
            cookie_mgr.clear_all()
            self.profile.clearHttpCache()
            self.profile.clearAllVisitedLinks()
            self.history_mgr.clear_all()
        elif level == "session":
            cookie_mgr.clear_session()
            self.profile.clearHttpCache()
        elif level == "1hour":
            cookie_mgr.clear_all()
            self.profile.clearHttpCache()
            self.history_mgr.clear_range(1)
        elif level == "15min":
            cookie_mgr.clear_session()

        self.privacy_engine.stats.reset()

    # ──── Window events ────

    def resizeEvent(self, event):
        """Reposition floating elements on resize."""
        super().resizeEvent(event)
        self.freeze_button.move(
            self.width() - self.freeze_button.width() - 20,
            self.height() - self.freeze_button.height() - 20
        )
        # Resize overlays to match
        rect = self.centralWidget().rect()
        if self.control_deck.isVisible():
            self.control_deck.setGeometry(rect)
        if self.drift_view.isVisible():
            self.drift_view.setGeometry(rect)
        if self.constellation_view.isVisible():
            self.constellation_view.setGeometry(rect)

    def closeEvent(self, event):
        """Save session state on close."""
        # Save open tabs for session restore
        urls = []
        for view in self.tabs:
            url = view.url().toString()
            if url and url != "about:blank":
                urls.append(url)
        self.settings_mgr.settings.session_tabs = urls
        self.settings_mgr.settings.session_active_tab = self.active_tab_index
        self.settings_mgr.save()

        self.history_mgr.close()
        super().closeEvent(event)
