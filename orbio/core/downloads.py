"""Download manager — hooks into QWebEngineProfile for download handling."""

import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, QUrl
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest


class DownloadState(Enum):
    SINKING = "sinking"      # In progress (downloading)
    RESTING = "resting"      # Completed
    FAILED = "failed"        # Error / cancelled
    PAUSED = "paused"


@dataclass
class DownloadItem:
    """A single download tracked by the manager."""
    id: int = 0
    url: str = ""
    filename: str = ""
    save_path: str = ""
    total_bytes: int = 0
    received_bytes: int = 0
    state: DownloadState = DownloadState.SINKING
    speed: float = 0.0
    started_at: float = 0.0
    finished_at: float = 0.0
    _request: Optional[QWebEngineDownloadRequest] = field(default=None, repr=False)

    @property
    def progress(self) -> float:
        if self.total_bytes <= 0:
            return 0.0
        return min(self.received_bytes / self.total_bytes, 1.0)

    @property
    def is_complete(self) -> bool:
        return self.state == DownloadState.RESTING

    @property
    def elapsed(self) -> float:
        end = self.finished_at if self.finished_at else time.time()
        return end - self.started_at if self.started_at else 0


class DownloadManager(QObject):
    """Manages all downloads, emitting signals for UI updates."""

    download_started = pyqtSignal(object)
    download_progress = pyqtSignal(int, float)  # id, progress 0-1
    download_finished = pyqtSignal(int)
    download_failed = pyqtSignal(int, str)

    def __init__(self, default_dir: str = "", parent=None):
        super().__init__(parent)
        self._downloads: list[DownloadItem] = []
        self._next_id = 1
        self._default_dir = default_dir or str(Path.home() / "Downloads")
        self._last_bytes: dict[int, int] = {}
        self._last_time: dict[int, float] = {}

    @property
    def downloads(self) -> list[DownloadItem]:
        return self._downloads

    @property
    def active_count(self) -> int:
        return sum(1 for d in self._downloads if d.state == DownloadState.SINKING)

    def handle_download(self, request: QWebEngineDownloadRequest):
        """Handle a new download request from Qt WebEngine."""
        item = DownloadItem(
            id=self._next_id,
            url=request.url().toString(),
            filename=request.downloadFileName(),
            save_path=os.path.join(self._default_dir, request.downloadFileName()),
            total_bytes=request.totalBytes(),
            state=DownloadState.SINKING,
            started_at=time.time(),
            _request=request,
        )
        self._next_id += 1

        # Set save directory
        request.setDownloadDirectory(self._default_dir)

        # Connect signals
        request.receivedBytesChanged.connect(lambda: self._on_progress(item))
        request.isFinishedChanged.connect(lambda: self._on_finished(item))
        request.stateChanged.connect(lambda state: self._on_state_changed(item, state))

        request.accept()

        self._downloads.insert(0, item)
        self._last_bytes[item.id] = 0
        self._last_time[item.id] = time.time()
        self.download_started.emit(item)

    def _on_progress(self, item: DownloadItem):
        """Update progress for a download."""
        if item._request is None:
            return
        received = item._request.receivedBytes()
        total = item._request.totalBytes()
        item.received_bytes = received
        if total > 0:
            item.total_bytes = total

        # Calculate speed
        now = time.time()
        elapsed = now - self._last_time.get(item.id, now)
        if elapsed > 0.5:
            bytes_delta = received - self._last_bytes.get(item.id, 0)
            item.speed = bytes_delta / elapsed
            self._last_bytes[item.id] = received
            self._last_time[item.id] = now

        self.download_progress.emit(item.id, item.progress)

    def _on_finished(self, item: DownloadItem):
        """Handle download completion."""
        if item._request and item._request.isFinished():
            item.state = DownloadState.RESTING
            item.finished_at = time.time()
            item.received_bytes = item.total_bytes
            self.download_finished.emit(item.id)

    def _on_state_changed(self, item: DownloadItem, state):
        """Handle Qt state changes."""
        if state == QWebEngineDownloadRequest.DownloadState.DownloadInterrupted:
            item.state = DownloadState.FAILED
            item.finished_at = time.time()
            reason = item._request.interruptReasonString() if item._request else "Unknown error"
            self.download_failed.emit(item.id, reason)
        elif state == QWebEngineDownloadRequest.DownloadState.DownloadCancelled:
            item.state = DownloadState.FAILED
            item.finished_at = time.time()
            self.download_failed.emit(item.id, "Cancelled")

    def cancel(self, download_id: int):
        """Cancel an active download."""
        for item in self._downloads:
            if item.id == download_id and item._request:
                item._request.cancel()
                item.state = DownloadState.FAILED
                break

    def retry(self, download_id: int):
        """Retry is not directly supported — user must re-trigger the download."""
        pass

    def remove(self, download_id: int):
        """Remove a download from the list (does not delete file)."""
        self._downloads = [d for d in self._downloads if d.id != download_id]

    def open_file(self, download_id: int):
        """Open the downloaded file with system default."""
        for item in self._downloads:
            if item.id == download_id and item.state == DownloadState.RESTING:
                import subprocess
                subprocess.Popen(["xdg-open", item.save_path])
                break

    def open_folder(self, download_id: int):
        """Open the containing folder."""
        for item in self._downloads:
            if item.id == download_id:
                folder = os.path.dirname(item.save_path)
                import subprocess
                subprocess.Popen(["xdg-open", folder])
                break

    @staticmethod
    def format_size(bytes_val: int) -> str:
        """Human-readable file size."""
        if bytes_val < 1024:
            return f"{bytes_val} B"
        elif bytes_val < 1024 * 1024:
            return f"{bytes_val / 1024:.1f} KB"
        elif bytes_val < 1024 * 1024 * 1024:
            return f"{bytes_val / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_val / (1024 * 1024 * 1024):.2f} GB"

    @staticmethod
    def format_speed(bytes_per_sec: float) -> str:
        """Human-readable speed."""
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.0f} B/s"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
