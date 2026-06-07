"""Bookmarks engine — JSON-backed with constellation grouping and spatial positions."""

import json
import math
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal


def _data_dir() -> Path:
    p = Path.home() / ".local" / "share" / "orbio"
    p.mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class Bookmark:
    """A single bookmark — a 'star' in the constellation map."""
    id: str = ""
    url: str = ""
    title: str = ""
    constellation: str = "Unsorted"
    x: float = 0.0
    y: float = 0.0
    favicon_path: str = ""
    created_at: float = 0.0

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]
        if not self.created_at:
            import time
            self.created_at = time.time()


@dataclass
class Constellation:
    """A group of bookmarks — a named cluster."""
    name: str = "Unsorted"
    color: str = "#4da6ff"
    center_x: float = 0.5
    center_y: float = 0.5


class BookmarkManager(QObject):
    """Manages bookmarks with JSON persistence and constellation grouping."""

    bookmark_added = pyqtSignal(object)
    bookmark_removed = pyqtSignal(str)
    bookmarks_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._path = _data_dir() / "bookmarks.json"
        self._bookmarks: list[Bookmark] = []
        self._constellations: list[Constellation] = [
            Constellation("Unsorted", "#4da6ff", 0.5, 0.5),
        ]
        self._load()

    @property
    def bookmarks(self) -> list[Bookmark]:
        return self._bookmarks

    @property
    def constellations(self) -> list[Constellation]:
        return self._constellations

    def add_bookmark(self, url: str, title: str = "", constellation: str = "Unsorted") -> Bookmark:
        """Add a new bookmark. Auto-positions it in a spiral from the constellation center."""
        # Check for duplicate
        for b in self._bookmarks:
            if b.url == url:
                return b

        # Find constellation center
        const = next((c for c in self._constellations if c.name == constellation), self._constellations[0])

        # Spiral placement: each new star spirals out from center
        count_in_const = sum(1 for b in self._bookmarks if b.constellation == constellation)
        angle = count_in_const * 137.5  # golden angle in degrees
        radius = 0.05 + count_in_const * 0.03
        x = const.center_x + radius * math.cos(math.radians(angle))
        y = const.center_y + radius * math.sin(math.radians(angle))

        bookmark = Bookmark(url=url, title=title, constellation=constellation, x=x, y=y)
        self._bookmarks.append(bookmark)
        self._save()
        self.bookmark_added.emit(bookmark)
        self.bookmarks_changed.emit()
        return bookmark

    def remove_bookmark(self, bookmark_id: str):
        """Remove a bookmark by ID."""
        self._bookmarks = [b for b in self._bookmarks if b.id != bookmark_id]
        self._save()
        self.bookmark_removed.emit(bookmark_id)
        self.bookmarks_changed.emit()

    def update_position(self, bookmark_id: str, x: float, y: float):
        """Update a bookmark's spatial position (from drag)."""
        for b in self._bookmarks:
            if b.id == bookmark_id:
                b.x = x
                b.y = y
                break
        self._save()

    def move_to_constellation(self, bookmark_id: str, constellation_name: str):
        """Move a bookmark to a different constellation."""
        for b in self._bookmarks:
            if b.id == bookmark_id:
                b.constellation = constellation_name
                break
        self._save()
        self.bookmarks_changed.emit()

    def add_constellation(self, name: str, color: str = "#4da6ff") -> Constellation:
        """Create a new constellation group."""
        for c in self._constellations:
            if c.name == name:
                return c

        # Position new constellation in an open area
        n = len(self._constellations)
        angle = n * 90
        cx = 0.5 + 0.25 * math.cos(math.radians(angle))
        cy = 0.5 + 0.25 * math.sin(math.radians(angle))

        const = Constellation(name, color, cx, cy)
        self._constellations.append(const)
        self._save()
        self.bookmarks_changed.emit()
        return const

    def remove_constellation(self, name: str):
        """Remove a constellation, moving its bookmarks to Unsorted."""
        if name == "Unsorted":
            return
        for b in self._bookmarks:
            if b.constellation == name:
                b.constellation = "Unsorted"
        self._constellations = [c for c in self._constellations if c.name != name]
        self._save()
        self.bookmarks_changed.emit()

    def is_bookmarked(self, url: str) -> bool:
        """Check if a URL is bookmarked."""
        return any(b.url == url for b in self._bookmarks)

    def get_by_url(self, url: str) -> Optional[Bookmark]:
        """Get bookmark by URL."""
        for b in self._bookmarks:
            if b.url == url:
                return b
        return None

    def get_constellation_bookmarks(self, name: str) -> list[Bookmark]:
        """Get all bookmarks in a constellation."""
        return [b for b in self._bookmarks if b.constellation == name]

    def _save(self):
        """Persist bookmarks and constellations to JSON."""
        data = {
            "bookmarks": [asdict(b) for b in self._bookmarks],
            "constellations": [asdict(c) for c in self._constellations],
        }
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load(self):
        """Load bookmarks from disk."""
        if not self._path.exists():
            self._save()
            return

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))

            self._bookmarks = []
            for b_data in data.get("bookmarks", []):
                b = Bookmark()
                for k, v in b_data.items():
                    if hasattr(b, k):
                        setattr(b, k, v)
                self._bookmarks.append(b)

            self._constellations = [Constellation("Unsorted", "#4da6ff", 0.5, 0.5)]
            for c_data in data.get("constellations", []):
                c = Constellation()
                for k, v in c_data.items():
                    if hasattr(c, k):
                        setattr(c, k, v)
                if c.name != "Unsorted":
                    self._constellations.append(c)
                else:
                    self._constellations[0] = c

        except (json.JSONDecodeError, KeyError, TypeError):
            self._bookmarks = []
            self._constellations = [Constellation("Unsorted", "#4da6ff", 0.5, 0.5)]
