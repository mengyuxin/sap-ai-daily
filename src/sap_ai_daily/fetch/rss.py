"""RSS/Atom adapter with bounded reads and strict publication dates."""

from datetime import UTC, datetime
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import feedparser
import httpx
from pydantic import ValidationError

from sap_ai_daily.config import Source
from sap_ai_daily.models import NewsItem
from sap_ai_daily.process.normalize import canonical_url, fingerprint, plain_text

MAX_BYTES = 5_000_000
USER_AGENT = "sap-ai-daily/0.1"


class RSSAdapter:
    def __init__(self, client: httpx.Client) -> None:
        self.client = client
        self.skipped = 0

    def _read(self, url: str) -> bytes:
        with self.client.stream("GET", url) as response:
            response.raise_for_status()
            chunks = bytearray()
            for chunk in response.iter_bytes():
                chunks.extend(chunk)
                if len(chunks) > MAX_BYTES:
                    raise ValueError("Feed exceeds size limit")
            return bytes(chunks)

    def fetch(self, source: Source) -> list[NewsItem]:
        """Read a permitted feed; reject invalid documents and undated items."""
        self.skipped = 0
        robots_url = urljoin(str(source.url), "/robots.txt")
        try:
            robots = self._read(robots_url).decode("utf-8", errors="replace")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in {404, 410}:
                raise
        else:
            policy = RobotFileParser()
            policy.parse(robots.splitlines())
            if not policy.can_fetch(USER_AGENT, str(source.url)):
                raise ValueError("Feed disallowed by robots.txt")
        feed = feedparser.parse(self._read(str(source.url)))
        if not feed.get("version") or feed.get("bozo"):
            raise ValueError("Invalid RSS/Atom document")
        items = []
        fetched_at = datetime.now(UTC)
        for entry in feed.entries:
            # Do not substitute updated_at/fetched_at for a missing publication date.
            published = entry.get("published_parsed")
            if not published or not entry.get("title") or not entry.get("link"):
                self.skipped += 1
                continue
            try:
                url = canonical_url(urljoin(str(source.url), entry.link))
                item = NewsItem(
                    id=fingerprint(url),
                    title=plain_text(entry.title),
                    url=url,
                    source_id=source.id,
                    source_name=source.name,
                    category=source.category,
                    published_at=datetime(*published[:6], tzinfo=UTC),
                    fetched_at=fetched_at,
                    summary_raw=plain_text(entry.get("summary", "")),
                    language=feed.feed.get("language", "und"),
                    canonical_url=url,
                    fingerprint=fingerprint(url),
                )
                items.append(item)
            except (ValidationError, ValueError, OverflowError):
                self.skipped += 1
        return items
