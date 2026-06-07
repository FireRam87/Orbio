"""Persistent settings for Orbio — JSON-backed with typed dataclass model."""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, QFileSystemWatcher


def _data_dir() -> Path:
    """Get the Orbio data directory."""
    p = Path.home() / ".local" / "share" / "orbio"
    p.mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class PrivacySettings:
    """Privacy-related preferences."""
    block_trackers: bool = True
    block_ads: bool = True
    https_only: bool = False
    cookie_auto_clear_on_tab_close: bool = False
    cookie_whitelist: list[str] = field(default_factory=list)
    send_dnt: bool = True
    block_fingerprinting: bool = False


@dataclass
class AppearanceSettings:
    """Look and feel preferences."""
    theme: str = "default"
    radial_tabs: bool = True
    show_glow_effects: bool = True
    font_size: int = 13


@dataclass
class SearchSettings:
    """Search engine preferences."""
    engine: str = "duckduckgo"
    engines: dict[str, str] = field(default_factory=lambda: {
        "duckduckgo": "https://duckduckgo.com/?q={}",
        "google": "https://www.google.com/search?q={}",
        "brave": "https://search.brave.com/search?q={}",
        "startpage": "https://www.startpage.com/do/dsearch?query={}",
    })
    search_suggestions: bool = False


@dataclass
class BehaviorSettings:
    """Browser behavior preferences."""
    homepage: str = "orbio://surface"
    new_tab_page: str = "orbio://surface"
    restore_session: bool = True
    show_greeting: bool = True
    smooth_scrolling: bool = True
    download_dir: str = ""


@dataclass
class ShortcutSettings:
    """Keyboard shortcut overrides (key = action, value = shortcut string)."""
    overrides: dict[str, str] = field(default_factory=dict)


@dataclass
class OrbioSettings:
    """Complete settings model for Orbio."""
    privacy: PrivacySettings = field(default_factory=PrivacySettings)
    appearance: AppearanceSettings = field(default_factory=AppearanceSettings)
    search: SearchSettings = field(default_factory=SearchSettings)
    behavior: BehaviorSettings = field(default_factory=BehaviorSettings)
    shortcuts: ShortcutSettings = field(default_factory=ShortcutSettings)
    session_tabs: list[str] = field(default_factory=list)
    session_active_tab: int = 0


class SettingsManager(QObject):
    """Manages loading, saving, and watching the settings JSON file."""

    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._path = _data_dir() / "config.json"
        self._settings = OrbioSettings()
        self._watcher: Optional[QFileSystemWatcher] = None
        self._load()
        self._setup_watcher()

    @property
    def settings(self) -> OrbioSettings:
        return self._settings

    @property
    def privacy(self) -> PrivacySettings:
        return self._settings.privacy

    @property
    def appearance(self) -> AppearanceSettings:
        return self._settings.appearance

    @property
    def search(self) -> SearchSettings:
        return self._settings.search

    @property
    def behavior(self) -> BehaviorSettings:
        return self._settings.behavior

    @property
    def shortcuts(self) -> ShortcutSettings:
        return self._settings.shortcuts

    def save(self):
        """Persist current settings to disk."""
        data = self._serialize(self._settings)
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def reset(self):
        """Reset to defaults and save."""
        self._settings = OrbioSettings()
        self.save()
        self.settings_changed.emit()

    def get_search_url(self, query: str) -> str:
        """Build a search URL from the current engine and query."""
        engine = self._settings.search.engine
        template = self._settings.search.engines.get(
            engine, "https://duckduckgo.com/?q={}"
        )
        return template.format(query)

    def _load(self):
        """Load settings from disk, falling back to defaults."""
        if not self._path.exists():
            self.save()
            return

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._settings = self._deserialize(data)
        except (json.JSONDecodeError, KeyError, TypeError):
            self._settings = OrbioSettings()
            self.save()

    def _setup_watcher(self):
        """Watch the config file for external changes."""
        self._watcher = QFileSystemWatcher([str(self._path)], self)
        self._watcher.fileChanged.connect(self._on_file_changed)

    def _on_file_changed(self, path: str):
        """Reload settings when the file changes externally."""
        self._load()
        self.settings_changed.emit()
        if not self._watcher.files():
            self._watcher.addPath(str(self._path))

    def _serialize(self, settings: OrbioSettings) -> dict:
        """Convert settings dataclass tree to a JSON-safe dict."""
        return asdict(settings)

    def _deserialize(self, data: dict) -> OrbioSettings:
        """Reconstruct an OrbioSettings from a dict, filling defaults for missing keys."""
        s = OrbioSettings()

        if "privacy" in data:
            for k, v in data["privacy"].items():
                if hasattr(s.privacy, k):
                    setattr(s.privacy, k, v)

        if "appearance" in data:
            for k, v in data["appearance"].items():
                if hasattr(s.appearance, k):
                    setattr(s.appearance, k, v)

        if "search" in data:
            for k, v in data["search"].items():
                if hasattr(s.search, k):
                    setattr(s.search, k, v)

        if "behavior" in data:
            for k, v in data["behavior"].items():
                if hasattr(s.behavior, k):
                    setattr(s.behavior, k, v)

        if "shortcuts" in data:
            for k, v in data["shortcuts"].items():
                if hasattr(s.shortcuts, k):
                    setattr(s.shortcuts, k, v)

        if "session_tabs" in data:
            s.session_tabs = data["session_tabs"]
        if "session_active_tab" in data:
            s.session_active_tab = data["session_active_tab"]

        return s
