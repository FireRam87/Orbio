"""History engine — SQLite-backed browsing history with duration tracking."""

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from PyQt6.QtCore import QObject, pyqtSignal


def _data_dir() -> Path:
    p = Path.home() / ".local" / "share" / "orbio"
    p.mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class HistoryEntry:
    """A single history record."""
    id: int = 0
    url: str = ""
    title: str = ""
    timestamp: float = 0.0
    duration: float = 0.0
    referrer_url: str = ""
    visit_count: int = 1

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp)

    @property
    def domain(self) -> str:
        from urllib.parse import urlparse
        return urlparse(self.url).netloc


class HistoryManager(QObject):
    """Manages browsing history with SQLite storage."""

    entry_added = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db_path = _data_dir() / "history.db"
        self._conn: Optional[sqlite3.Connection] = None
        self._current_entry: Optional[HistoryEntry] = None
        self._current_start: float = 0.0
        self._init_db()

    def _init_db(self):
        """Create the history database and table."""
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                title TEXT DEFAULT '',
                timestamp REAL NOT NULL,
                duration REAL DEFAULT 0,
                referrer_url TEXT DEFAULT '',
                visit_count INTEGER DEFAULT 1
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp DESC)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_url ON history(url)
        """)
        self._conn.commit()

    def record_visit(self, url: str, title: str = "", referrer_url: str = ""):
        """Record a new page visit. Finalizes any previous visit's duration."""
        self._finalize_current()

        if not url or url.startswith("orbio://"):
            return

        now = time.time()
        self._current_start = now

        # Check if we visited this URL recently (within 5 min) — update instead of duplicate
        cursor = self._conn.execute(
            "SELECT id, visit_count FROM history WHERE url = ? AND timestamp > ? ORDER BY timestamp DESC LIMIT 1",
            (url, now - 300)
        )
        row = cursor.fetchone()

        if row:
            self._conn.execute(
                "UPDATE history SET title = ?, timestamp = ?, visit_count = visit_count + 1, referrer_url = ? WHERE id = ?",
                (title, now, referrer_url, row[0])
            )
            self._current_entry = HistoryEntry(id=row[0], url=url, title=title, timestamp=now)
        else:
            cursor = self._conn.execute(
                "INSERT INTO history (url, title, timestamp, referrer_url) VALUES (?, ?, ?, ?)",
                (url, title, now, referrer_url)
            )
            self._current_entry = HistoryEntry(
                id=cursor.lastrowid, url=url, title=title,
                timestamp=now, referrer_url=referrer_url
            )
            self.entry_added.emit(self._current_entry)

        self._conn.commit()

    def update_title(self, url: str, title: str):
        """Update the title for the most recent visit to a URL."""
        self._conn.execute(
            "UPDATE history SET title = ? WHERE url = ? ORDER BY timestamp DESC LIMIT 1",
            (title, url)
        )
        self._conn.commit()
        if self._current_entry and self._current_entry.url == url:
            self._current_entry.title = title

    def _finalize_current(self):
        """Record duration for the current page visit."""
        if self._current_entry and self._current_start > 0:
            duration = time.time() - self._current_start
            if duration > 1.0:
                self._conn.execute(
                    "UPDATE history SET duration = ? WHERE id = ?",
                    (duration, self._current_entry.id)
                )
                self._conn.commit()
        self._current_entry = None
        self._current_start = 0.0

    def get_entries(self, limit: int = 200, offset: int = 0,
                    search: str = "", days: int = 0) -> list[HistoryEntry]:
        """Retrieve history entries with optional filtering."""
        query = "SELECT id, url, title, timestamp, duration, referrer_url, visit_count FROM history"
        params = []
        conditions = []

        if search:
            conditions.append("(title LIKE ? OR url LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        if days > 0:
            cutoff = time.time() - (days * 86400)
            conditions.append("timestamp > ?")
            params.append(cutoff)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = self._conn.execute(query, params)
        entries = []
        for row in cursor.fetchall():
            entries.append(HistoryEntry(
                id=row[0], url=row[1], title=row[2],
                timestamp=row[3], duration=row[4],
                referrer_url=row[5], visit_count=row[6]
            ))
        return entries

    def get_frequent_sites(self, limit: int = 12) -> list[dict]:
        """Get most frequently visited sites (by domain), for the Surface page."""
        cursor = self._conn.execute("""
            SELECT url, title, COUNT(*) as visits, SUM(duration) as total_time
            FROM history
            WHERE timestamp > ?
            GROUP BY url
            ORDER BY visits DESC
            LIMIT ?
        """, (time.time() - 30 * 86400, limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                "url": row[0],
                "title": row[1],
                "visits": row[2],
                "total_time": row[3] or 0,
            })
        return results

    def get_entries_for_day(self, date: datetime) -> list[HistoryEntry]:
        """Get all entries for a specific day."""
        start = datetime(date.year, date.month, date.day).timestamp()
        end = start + 86400
        return self.get_entries(limit=500, search="", days=0)

    def clear_all(self):
        """Delete all history."""
        self._conn.execute("DELETE FROM history")
        self._conn.commit()

    def clear_range(self, hours: int):
        """Delete history older than N hours ago."""
        cutoff = time.time() - (hours * 3600)
        self._conn.execute("DELETE FROM history WHERE timestamp > ?", (cutoff,))
        self._conn.commit()

    def delete_entry(self, entry_id: int):
        """Delete a single history entry."""
        self._conn.execute("DELETE FROM history WHERE id = ?", (entry_id,))
        self._conn.commit()

    def close(self):
        """Finalize and close the database."""
        self._finalize_current()
        if self._conn:
            self._conn.close()
            self._conn = None
