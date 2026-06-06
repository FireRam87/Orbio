"""Privacy engine — request interception and tracker blocking."""

import os
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional

from PyQt6.QtWebEngineCore import (
    QWebEngineUrlRequestInterceptor,
    QWebEngineUrlRequestInfo
)
from PyQt6.QtCore import QObject, pyqtSignal

from orbio.engine.filters import FilterListParser


# Map Qt resource types to filter list type names
RESOURCE_TYPE_MAP = {
    QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMainFrame: "document",
    QWebEngineUrlRequestInfo.ResourceType.ResourceTypeSubFrame: "subdocument",
    QWebEngineUrlRequestInfo.ResourceType.ResourceTypeStylesheet: "stylesheet",
    QWebEngineUrlRequestInfo.ResourceType.ResourceTypeScript: "script",
    QWebEngineUrlRequestInfo.ResourceType.ResourceTypeImage: "image",
    QWebEngineUrlRequestInfo.ResourceType.ResourceTypeFontResource: "font",
    QWebEngineUrlRequestInfo.ResourceType.ResourceTypeSubResource: "",
    QWebEngineUrlRequestInfo.ResourceType.ResourceTypeObject: "object",
    QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMedia: "media",
    QWebEngineUrlRequestInfo.ResourceType.ResourceTypePing: "ping",
    QWebEngineUrlRequestInfo.ResourceType.ResourceTypeXhr: "xmlhttprequest",
}

FILTER_LIST_URLS = {
    "easylist": "https://easylist.to/easylist/easylist.txt",
    "easyprivacy": "https://easylist.to/easylist/easyprivacy.txt",
}


class PrivacyStats:
    """Track blocking statistics."""

    def __init__(self):
        self.trackers_blocked: int = 0
        self.ads_blocked: int = 0
        self.total_requests: int = 0
        self.blocked_domains: dict[str, int] = {}
        self.site_stats: dict[str, dict] = {}

    def record_block(self, url: str, source_domain: str):
        """Record a blocked request."""
        domain = urlparse(url).netloc
        self.blocked_domains[domain] = self.blocked_domains.get(domain, 0) + 1

        if source_domain not in self.site_stats:
            self.site_stats[source_domain] = {"blocked": 0, "total": 0}
        self.site_stats[source_domain]["blocked"] += 1

    def record_request(self, source_domain: str):
        """Record any request (blocked or not)."""
        self.total_requests += 1
        if source_domain not in self.site_stats:
            self.site_stats[source_domain] = {"blocked": 0, "total": 0}
        self.site_stats[source_domain]["total"] += 1

    def reset(self):
        """Reset all stats."""
        self.trackers_blocked = 0
        self.ads_blocked = 0
        self.total_requests = 0
        self.blocked_domains.clear()
        self.site_stats.clear()


class OrbioRequestInterceptor(QWebEngineUrlRequestInterceptor):
    """Intercepts web requests and blocks trackers/ads."""

    request_blocked = pyqtSignal(str, str)

    def __init__(self, privacy_engine: "PrivacyEngine", parent=None):
        super().__init__(parent)
        self.privacy_engine = privacy_engine

    def interceptRequest(self, info: QWebEngineUrlRequestInfo):
        url = info.requestUrl().toString()
        first_party = info.firstPartyUrl().host()
        resource_type = RESOURCE_TYPE_MAP.get(info.resourceType(), "")

        self.privacy_engine.stats.record_request(first_party)

        if self.privacy_engine.should_block(url, first_party, resource_type):
            info.block(True)
            self.privacy_engine.stats.record_block(url, first_party)
            self.privacy_engine.stats.trackers_blocked += 1


class PrivacyEngine(QObject):
    """Main privacy engine that manages filter lists and blocking."""

    tracker_blocked = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parser = FilterListParser()
        self.stats = PrivacyStats()
        self.interceptor = OrbioRequestInterceptor(self)
        self._filter_dir = self._get_filter_dir()
        self._load_filters()

    def _get_filter_dir(self) -> Path:
        """Get or create the filter lists directory."""
        data_dir = Path.home() / ".local" / "share" / "orbio" / "filter_lists"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    def _load_filters(self):
        """Load filter lists from disk."""
        for name in FILTER_LIST_URLS:
            filepath = self._filter_dir / f"{name}.txt"
            if filepath.exists():
                self.parser.load_from_file(str(filepath))

        # If no filters loaded, create a minimal built-in blocklist
        if self.parser.rule_count == 0:
            self._load_builtin_filters()

    def _load_builtin_filters(self):
        """Load minimal built-in tracker blocking rules."""
        builtin = """
||doubleclick.net^
||googlesyndication.com^
||googleadservices.com^
||google-analytics.com^
||googletagmanager.com^
||facebook.com/tr^
||facebook.net/signals^
||analytics.twitter.com^
||bat.bing.com^
||scorecardresearch.com^
||quantserve.com^
||adnxs.com^
||adsrvr.org^
||demdex.net^
||krxd.net^
||bluekai.com^
||outbrain.com^
||taboola.com^
||amazon-adsystem.com^
||moatads.com^
||rubiconproject.com^
||pubmatic.com^
||openx.net^
||casalemedia.com^
||criteo.com^
||hotjar.com^
||mixpanel.com^
||segment.io^
||amplitude.com^
||newrelic.com^
||sentry.io/api^$third-party
"""
        self.parser.load_from_string(builtin)

    def should_block(self, url: str, source_domain: str = "",
                     resource_type: str = "") -> bool:
        """Check if a URL should be blocked."""
        # Never block first-party main frame requests
        if resource_type == "document":
            return False
        return self.parser.should_block(url, source_domain, resource_type)

    async def update_filter_lists(self):
        """Download the latest filter lists (call periodically)."""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            for name, url in FILTER_LIST_URLS.items():
                try:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            content = await resp.text()
                            filepath = self._filter_dir / f"{name}.txt"
                            filepath.write_text(content, encoding="utf-8")
                except Exception:
                    pass
        # Reload after update
        self.parser = FilterListParser()
        self._load_filters()

    def download_filter_lists_sync(self):
        """Synchronous filter list download (for initial setup)."""
        import urllib.request
        for name, url in FILTER_LIST_URLS.items():
            filepath = self._filter_dir / f"{name}.txt"
            if filepath.exists():
                continue
            try:
                urllib.request.urlretrieve(url, str(filepath))
            except Exception:
                pass

        if self.parser.rule_count == 0:
            self.parser = FilterListParser()
            self._load_filters()
