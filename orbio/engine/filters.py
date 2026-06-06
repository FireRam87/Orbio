"""EasyList/EasyPrivacy filter list parser for Orbio."""

import re
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class FilterRule:
    """A parsed filter rule from EasyList format."""
    pattern: str
    is_exception: bool = False
    is_regex: bool = False
    domains: dict[str, bool] = field(default_factory=dict)
    resource_types: set[str] = field(default_factory=set)
    third_party: Optional[bool] = None
    compiled: Optional[re.Pattern] = None


class FilterListParser:
    """Parses ABP/EasyList format filter lists into usable rules."""

    def __init__(self):
        self.blocking_rules: list[FilterRule] = []
        self.exception_rules: list[FilterRule] = []
        self._domain_cache: dict[str, list[FilterRule]] = {}

    def load_from_file(self, filepath: str):
        """Load and parse a filter list file."""
        path = Path(filepath)
        if not path.exists():
            return

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(("!", "[Adblock")):
                    continue
                self._parse_rule(line)

    def load_from_string(self, content: str):
        """Load rules from a string (for testing or inline lists)."""
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith(("!", "[Adblock")):
                continue
            self._parse_rule(line)

    def _parse_rule(self, raw: str):
        """Parse a single filter rule line."""
        # Skip cosmetic/element hiding rules
        if "##" in raw or "#@#" in raw or "#?#" in raw:
            return

        rule = FilterRule(pattern=raw)

        # Exception rules start with @@
        if raw.startswith("@@"):
            rule.is_exception = True
            raw = raw[2:]

        # Split options from pattern
        options_str = ""
        if "$" in raw and not raw.startswith("/"):
            parts = raw.rsplit("$", 1)
            raw = parts[0]
            options_str = parts[1] if len(parts) > 1 else ""

        # Parse options
        if options_str:
            self._parse_options(rule, options_str)

        # Convert pattern to regex
        rule.compiled = self._pattern_to_regex(raw)

        if rule.is_exception:
            self.exception_rules.append(rule)
        else:
            self.blocking_rules.append(rule)

    def _parse_options(self, rule: FilterRule, options: str):
        """Parse filter rule options (after $)."""
        for opt in options.split(","):
            opt = opt.strip()
            if opt == "third-party":
                rule.third_party = True
            elif opt == "~third-party":
                rule.third_party = False
            elif opt.startswith("domain="):
                domains = opt[7:].split("|")
                for d in domains:
                    if d.startswith("~"):
                        rule.domains[d[1:]] = False
                    else:
                        rule.domains[d] = True
            elif opt in ("script", "image", "stylesheet", "xmlhttprequest",
                        "subdocument", "ping", "websocket", "font", "media",
                        "object", "popup", "document"):
                rule.resource_types.add(opt)

    def _pattern_to_regex(self, pattern: str) -> Optional[re.Pattern]:
        """Convert an ABP filter pattern to a compiled regex."""
        if not pattern:
            return None

        # Already a regex (enclosed in /)
        if pattern.startswith("/") and pattern.endswith("/"):
            try:
                return re.compile(pattern[1:-1], re.IGNORECASE)
            except re.error:
                return None

        # Escape special regex characters except our wildcards
        regex = re.escape(pattern)

        # ABP wildcards: * matches anything, ^ matches separator
        regex = regex.replace(r"\*", ".*")
        regex = regex.replace(r"\^", r"[^\w\d\-.%]")

        # || at start means domain anchor
        if regex.startswith(r"\|\|"):
            regex = r"^https?://([^/]*\.)?" + regex[4:]
        elif regex.startswith(r"\|"):
            regex = "^" + regex[2:]

        # | at end means end anchor
        if regex.endswith(r"\|"):
            regex = regex[:-2] + "$"

        try:
            return re.compile(regex, re.IGNORECASE)
        except re.error:
            return None

    def should_block(self, url: str, source_domain: str = "",
                     resource_type: str = "") -> bool:
        """Check if a URL should be blocked."""
        # Check exception rules first
        for rule in self.exception_rules:
            if self._matches(rule, url, source_domain, resource_type):
                return False

        # Check blocking rules
        for rule in self.blocking_rules:
            if self._matches(rule, url, source_domain, resource_type):
                return True

        return False

    def _matches(self, rule: FilterRule, url: str, source_domain: str,
                 resource_type: str) -> bool:
        """Check if a rule matches the given URL."""
        if rule.compiled is None:
            return False

        if not rule.compiled.search(url):
            return False

        # Check third-party constraint
        if rule.third_party is not None:
            is_third_party = self._is_third_party(url, source_domain)
            if rule.third_party != is_third_party:
                return False

        # Check domain constraints
        if rule.domains:
            domain_match = False
            for domain, include in rule.domains.items():
                if source_domain == domain or source_domain.endswith("." + domain):
                    domain_match = include
                    break
            if not domain_match:
                return False

        # Check resource type
        if rule.resource_types and resource_type:
            if resource_type not in rule.resource_types:
                return False

        return True

    def _is_third_party(self, url: str, source_domain: str) -> bool:
        """Determine if a request is third-party."""
        try:
            from urllib.parse import urlparse
            request_domain = urlparse(url).netloc
            if not source_domain or not request_domain:
                return False
            return not (request_domain == source_domain or
                       request_domain.endswith("." + source_domain) or
                       source_domain.endswith("." + request_domain))
        except Exception:
            return False

    @property
    def rule_count(self) -> int:
        return len(self.blocking_rules) + len(self.exception_rules)
