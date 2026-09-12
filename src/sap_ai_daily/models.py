"""Validated, timezone-aware pipeline records."""

from datetime import date
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl

Category = Literal["ai", "sap", "enterprise"]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NewsItem(Record):
    id: str
    title: str = Field(min_length=1)
    url: HttpUrl
    source_id: str
    source_name: str
    category: Category
    published_at: AwareDatetime
    fetched_at: AwareDatetime
    summary_raw: str = ""
    content_raw: str = ""
    language: str = "und"
    canonical_url: str = ""
    fingerprint: str = ""
    related_urls: list[str] = Field(default_factory=list)


class SelectedNewsItem(NewsItem):
    importance_score: float
    relevance_score: float
    confidence_score: float = 0
    reason: str
    verified: bool = False


class DailyBrief(Record):
    date: date
    headline: str = "AI・SAP 科技早报"
    items: list[SelectedNewsItem]
    editor_note: str = "来源原文草稿；请人工核验并编辑后使用。"
    hashtags: list[str] = Field(default_factory=lambda: ["AI", "SAP", "科技早报"])
    source_count: int
    generated_at: AwareDatetime


class PublishResult(Record):
    status: Literal["dry_run", "published"]
    content_hash: str
    text: str
    path: str | None = None
    publish_id: str | None = None
