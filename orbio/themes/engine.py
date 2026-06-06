"""Theme engine for Orbio — loads and applies JSON themes."""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor


@dataclass
class ThemeColors:
    """All theme colors."""
    background: str = "#0a0a0f"
    surface: str = "#12121a"
    surface_elevated: str = "#1a1a25"
    primary: str = "#4da6ff"
    primary_glow: str = "#1a8cff"
    accent: str = "#66b3ff"
    text: str = "#e8e8f0"
    text_secondary: str = "#8888aa"
    border: str = "#2a2a3a"
    tab_active: str = "#4da6ff"
    tab_inactive: str = "#2a2a3a"
    freeze_button: str = "#4da6ff"
    success: str = "#44dd88"
    warning: str = "#ffaa33"
    error: str = "#ff4466"


@dataclass
class ThemeGlow:
    """Glow effect settings."""
    enabled: bool = True
    intensity: float = 0.7
    color: str = "#4da6ff"
    radius: int = 12


@dataclass
class ThemeFonts:
    """Font preferences."""
    ui: str = "Inter"
    mono: str = "JetBrains Mono"


@dataclass
class Theme:
    """A complete Orbio theme."""
    name: str = "Orbio Blue"
    author: str = "Orbio"
    version: str = "1.0"
    base: str = "dark"
    colors: ThemeColors = field(default_factory=ThemeColors)
    glow: ThemeGlow = field(default_factory=ThemeGlow)
    fonts: ThemeFonts = field(default_factory=ThemeFonts)


class ThemeEngine(QObject):
    """Manages theme loading, saving, and application."""

    theme_changed = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_theme: Theme = Theme()
        self._themes_dir = self._get_themes_dir()
        self._available_themes: dict[str, Path] = {}
        self._scan_themes()

    def _get_themes_dir(self) -> Path:
        """Get or create the themes directory."""
        # Built-in themes (in package)
        builtin = Path(__file__).parent
        # User themes
        user_dir = Path.home() / ".local" / "share" / "orbio" / "themes"
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def _scan_themes(self):
        """Scan for available themes."""
        self._available_themes.clear()

        # Scan built-in themes
        builtin_dir = Path(__file__).parent
        for f in builtin_dir.glob("*.json"):
            self._available_themes[f.stem] = f

        # Scan user themes
        for f in self._themes_dir.glob("*.json"):
            self._available_themes[f.stem] = f

    @property
    def current_theme(self) -> Theme:
        return self._current_theme

    @property
    def available_themes(self) -> list[str]:
        return list(self._available_themes.keys())

    def load_theme(self, name: str) -> bool:
        """Load a theme by name."""
        if name not in self._available_themes:
            return False

        filepath = self._available_themes[name]
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._current_theme = self._parse_theme(data)
            self.theme_changed.emit(self._current_theme)
            return True
        except (json.JSONDecodeError, KeyError):
            return False

    def load_default(self):
        """Load the default Orbio Blue theme."""
        self.load_theme("default")

    def save_theme(self, theme: Theme, filename: str = None):
        """Save a theme to disk."""
        if not filename:
            filename = theme.name.lower().replace(" ", "_")
        filepath = self._themes_dir / f"{filename}.json"

        data = {
            "name": theme.name,
            "author": theme.author,
            "version": theme.version,
            "base": theme.base,
            "colors": vars(theme.colors),
            "glow": vars(theme.glow),
            "fonts": vars(theme.fonts),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        self._scan_themes()

    def _parse_theme(self, data: dict) -> Theme:
        """Parse a JSON theme dict into a Theme object."""
        theme = Theme()
        theme.name = data.get("name", "Untitled")
        theme.author = data.get("author", "Unknown")
        theme.version = data.get("version", "1.0")
        theme.base = data.get("base", "dark")

        if "colors" in data:
            for key, value in data["colors"].items():
                if hasattr(theme.colors, key):
                    setattr(theme.colors, key, value)

        if "glow" in data:
            for key, value in data["glow"].items():
                if hasattr(theme.glow, key):
                    setattr(theme.glow, key, value)

        if "fonts" in data:
            for key, value in data["fonts"].items():
                if hasattr(theme.fonts, key):
                    setattr(theme.fonts, key, value)

        return theme

    def get_color(self, name: str) -> QColor:
        """Get a theme color by name as QColor."""
        value = getattr(self._current_theme.colors, name, "#ffffff")
        return QColor(value)

    def get_glow_color(self) -> QColor:
        """Get the glow effect color."""
        return QColor(self._current_theme.glow.color)

    def get_glow_intensity(self) -> float:
        """Get glow intensity (0.0 - 1.0)."""
        return self._current_theme.glow.intensity

    def generate_stylesheet(self) -> str:
        """Generate a complete Qt stylesheet from the current theme."""
        c = self._current_theme.colors
        f = self._current_theme.fonts

        return f"""
            QMainWindow {{
                background-color: {c.background};
            }}
            QWidget {{
                font-family: "{f.ui}", sans-serif;
            }}
            QLabel {{
                color: {c.text};
            }}
            QPushButton {{
                background-color: {c.surface};
                color: {c.text};
                border: 1px solid {c.border};
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {c.surface_elevated};
                border-color: {c.primary};
                color: {c.primary};
            }}
            QLineEdit {{
                background-color: {c.background};
                color: {c.text};
                border: 1px solid {c.border};
                border-radius: 8px;
                padding: 8px 14px;
                selection-background-color: {c.primary};
            }}
            QLineEdit:focus {{
                border-color: {c.primary};
            }}
            QMenu {{
                background-color: {c.surface};
                color: {c.text};
                border: 1px solid {c.border};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item:selected {{
                background-color: {c.primary};
                color: white;
            }}
            QScrollBar:vertical {{
                width: 6px;
                background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: {c.border};
                border-radius: 3px;
            }}
        """
