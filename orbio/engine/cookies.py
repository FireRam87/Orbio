"""Cookie management for Orbio privacy engine."""

from PyQt6.QtWebEngineCore import QWebEngineProfile
from PyQt6.QtNetwork import QNetworkCookie
from PyQt6.QtCore import QObject


class CookieManager(QObject):
    """Manages cookie policies and clearing."""

    def __init__(self, profile: QWebEngineProfile, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.cookie_store = profile.cookieStore()

    def clear_all(self):
        """Delete all cookies."""
        self.cookie_store.deleteAllCookies()

    def clear_session(self):
        """Delete session cookies only."""
        self.cookie_store.deleteSessionCookies()

    def clear_for_domain(self, domain: str):
        """Delete cookies for a specific domain (not directly supported, clears all)."""
        self.clear_all()
