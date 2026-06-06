"""Custom QWebEngineView wrapper for Orbio."""

from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PyQt6.QtCore import QUrl, pyqtSignal


class OrbioWebView(QWebEngineView):
    """A web view with privacy defaults and signal hooks."""

    title_changed = pyqtSignal(str)
    url_changed = pyqtSignal(QUrl)
    icon_changed = pyqtSignal()
    loading_started = pyqtSignal()
    loading_finished = pyqtSignal(bool)

    def __init__(self, profile: QWebEngineProfile = None, parent=None):
        super().__init__(parent)

        if profile:
            page = QWebEnginePage(profile, self)
            self.setPage(page)

        self.titleChanged.connect(self._on_title_changed)
        self.urlChanged.connect(self._on_url_changed)
        self.iconChanged.connect(self._on_icon_changed)
        self.loadStarted.connect(self._on_load_started)
        self.loadFinished.connect(self._on_load_finished)

    def _on_title_changed(self, title: str):
        self.title_changed.emit(title)

    def _on_url_changed(self, url: QUrl):
        self.url_changed.emit(url)

    def _on_icon_changed(self):
        self.icon_changed.emit()

    def _on_load_started(self):
        self.loading_started.emit()

    def _on_load_finished(self, ok: bool):
        self.loading_finished.emit(ok)

    def navigate(self, url_string: str):
        """Navigate to a URL string, adding https:// if needed."""
        if not url_string.startswith(("http://", "https://", "file://")):
            if "." in url_string and " " not in url_string:
                url_string = "https://" + url_string
            else:
                url_string = f"https://duckduckgo.com/?q={url_string}"
        self.setUrl(QUrl(url_string))
