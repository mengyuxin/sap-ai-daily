"""Merge clear duplicate reports and retain their source URLs."""

import re
from difflib import SequenceMatcher

from sap_ai_daily.models import NewsItem
from sap_ai_daily.process.normalize import canonical_url, normalize_title


def same_event(left: NewsItem, right: NewsItem) -> bool:
    """Match URLs or similar titles, protecting differing numbers/product versions."""
    if canonical_url(str(left.url)) == canonical_url(str(right.url)):
        return True
    a, b = normalize_title(left.title), normalize_title(right.title)
    if abs((left.published_at - right.published_at).total_seconds()) > 172800:
        return False
    if re.findall(r"\d+", a) != re.findall(r"\d+", b):
        return False
    return a == b or (
        min(len(a), len(b)) >= 20 and SequenceMatcher(None, a, b).ratio() >= 0.88
    )


def deduplicate(items: list[NewsItem], priorities: dict[str, int]) -> list[NewsItem]:
    """Keep the highest priority report for each approximate event."""
    kept: list[NewsItem] = []
    for item in sorted(
        items, key=lambda i: (-priorities.get(i.source_id, 0), str(i.url))
    ):
        duplicate = next((other for other in kept if same_event(item, other)), None)
        if duplicate is None:
            kept.append(item.model_copy(deep=True))
        else:
            duplicate.related_urls = sorted(
                set(duplicate.related_urls + [str(item.url)] + item.related_urls)
            )
    return kept
