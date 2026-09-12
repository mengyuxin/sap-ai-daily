"""Explainable scoring; source trust is not a factual verification claim."""

from datetime import datetime

from sap_ai_daily.models import NewsItem, SelectedNewsItem


def rank_news(
    items: list[NewsItem], priorities: dict[str, int], cutoff: datetime
) -> list[SelectedNewsItem]:
    """Score freshness, category, enterprise relevance and promotional language."""
    ranked = []
    for item in items:
        title = item.title.casefold()
        if any(term in title for term in ("geforce now", "game ready driver")):
            continue
        relevance = {"ai": 20, "sap": 18, "enterprise": 10}[item.category]
        relevance += 10 * any(
            word in title
            for word in ("security", "s/4hana", "agent", "enterprise", "joule")
        )
        age = max(0, (cutoff - item.published_at).total_seconds() / 3600)
        penalty = 25 * any(word in title for word in ("rumor", "rumour", "sponsored"))
        score = priorities.get(item.source_id, 0) * 0.5 + max(0, 24 - age / 2)
        ranked.append(
            SelectedNewsItem(
                **item.model_dump(),
                importance_score=score + relevance - penalty,
                relevance_score=relevance,
                reason="来源优先级 + 新鲜度 + 分类及企业关键词；未进行独立事实核验",
            )
        )
    return sorted(ranked, key=lambda i: (-i.importance_score, str(i.url)))
