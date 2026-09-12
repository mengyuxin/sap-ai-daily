import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from sap_ai_daily.cli import run, window
from sap_ai_daily.config import Settings, Source, load_config
from sap_ai_daily.fetch.rss import RSSAdapter
from sap_ai_daily.models import DailyBrief, NewsItem
from sap_ai_daily.process.deduplicate import deduplicate
from sap_ai_daily.process.normalize import canonical_url, normalize_title
from sap_ai_daily.process.rank import rank_news
from sap_ai_daily.publish.dry_run import DryRunPublisher
from sap_ai_daily.publish.weibo import WeiboPublisher
from sap_ai_daily.render.weibo import render_weibo

NOW = datetime(2026, 9, 12, 0, tzinfo=UTC)
DAY = date(2026, 9, 12)
FEED = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>Test fixture</title>
<item><title>Test fixture: enterprise agent update</title>
<link>https://example.org/news/1</link><pubDate>Fri, 11 Sep 2026 10:00:00 GMT</pubDate>
<description>Fixture only. No real news.</description></item></channel></rss>"""


def source(name: str = "test", core: bool = True) -> Source:
    return Source(
        id=name,
        name=name,
        category="ai",
        url=f"https://{name}.example/feed",
        priority=100,
        enabled=True,
        core=core,
    )


def item(title: str = "Enterprise agent update", **changes: object) -> NewsItem:
    values = dict(
        id="1",
        title=title,
        url="https://example.org/1",
        source_id="test",
        source_name="Test",
        category="ai",
        published_at=NOW - timedelta(hours=1),
        fetched_at=NOW,
        summary_raw="First complete sentence. Second sentence.",
    )
    values.update(changes)
    return NewsItem(**values)


def brief() -> DailyBrief:
    return DailyBrief(
        date=DAY,
        items=rank_news([item()], {"test": 100}, NOW),
        source_count=1,
        generated_at=NOW,
    )


def settings(tmp_path: Path, **changes: object) -> Settings:
    return Settings(
        output_dir=tmp_path / "output", history_dir=tmp_path / "data", **changes
    )


def client(fail_hosts: tuple[str, ...] = (), body: bytes = FEED) -> httpx.Client:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.host in fail_hosts:
            return httpx.Response(503)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, content=body)

    return httpx.Client(transport=httpx.MockTransport(handle))


def test_normalization() -> None:
    assert normalize_title("ＡＩ:  SAP—Cloud!") == "ai sap cloud"
    assert (
        canonical_url("https://EXAMPLE.org/a?utm_source=x&id=3#top")
        == "https://example.org/a?id=3"
    )
    assert canonical_url("https://example.org/a?id=4") != canonical_url(
        "https://example.org/a?id=3"
    )


def test_dedup_related_sources_and_versions() -> None:
    a = item("SAP announces enterprise agent platform 2")
    b = item(
        "SAP announces enterprise agent platform 2!",
        url="https://example.net/b",
        source_id="other",
    )
    c = item("SAP announces enterprise agent platform 3", url="https://example.net/c")
    result = deduplicate([b, a, c], {"test": 100, "other": 50})
    assert len(result) == 2
    assert result[0].source_id == "test"
    assert next(i for i in result if i.title == a.title).related_urls == [str(b.url)]
    assert not a.related_urls


def test_canonical_duplicates() -> None:
    assert (
        len(
            deduplicate(
                [
                    item(),
                    item("Other title", url="https://example.org/1?utm_medium=rss"),
                ],
                {},
            )
        )
        == 1
    )


def test_ranking_does_not_claim_verification() -> None:
    old = item(
        "Sponsored rumor",
        url="https://example.org/2",
        published_at=NOW - timedelta(hours=40),
    )
    ranked = rank_news([old, item()], {"test": 100}, NOW)
    assert ranked[0].title == "Enterprise agent update"
    assert not ranked[0].verified
    assert ranked[0].confidence_score == 0


def test_render_length_and_links() -> None:
    text = render_weibo(brief(), Settings(max_length=150))
    assert len(text) <= 150
    assert "Enterprise agent update" in text
    assert "https://" not in text
    assert "https://example.org/1" in render_weibo(
        brief(), Settings(include_links=True)
    )
    b = brief()
    b.items[0].title = "X" * 300
    with pytest.raises(ValueError):
        render_weibo(b, Settings(max_length=100))


def test_dry_run_needs_no_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("Dry run attempted network access")

    monkeypatch.setattr(httpx.Client, "send", forbidden)
    publisher = DryRunPublisher(settings(tmp_path))
    first = publisher.publish(brief())
    second = publisher.publish(brief())
    assert first.content_hash == second.content_hash
    assert Path(first.path).read_text() == first.text
    assert first.status == "dry_run"


@pytest.mark.parametrize("enabled", ["false", "true"])
def test_production_always_closed(
    enabled: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PUBLISH_ENABLED", enabled)
    for key in ("WEIBO_CLIENT_ID", "WEIBO_CLIENT_SECRET", "WEIBO_ACCESS_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(RuntimeError):
        WeiboPublisher().publish(brief())


def test_configuration() -> None:
    config, sources = load_config(Path("config"))
    assert config.timezone == "Asia/Shanghai"
    assert len(sources) == 3
    with pytest.raises(ValidationError):
        Settings(timezone="UTC")


def test_timezone() -> None:
    start, end = window(date(2026, 9, 11), NOW, 24)
    assert end == datetime(2026, 9, 11, 16, tzinfo=UTC)
    assert end - start == timedelta(days=1)
    with pytest.raises(ValidationError):
        item(published_at=datetime(2026, 9, 11))


def test_rss_valid_and_missing_date() -> None:
    adapter = RSSAdapter(client())
    assert len(adapter.fetch(source())) == 1
    body = FEED.replace(b"<pubDate>Fri, 11 Sep 2026 10:00:00 GMT</pubDate>", b"")
    adapter = RSSAdapter(client(body=body))
    assert adapter.fetch(source()) == []
    assert adapter.skipped == 1


def test_robots_denial() -> None:
    c = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text="User-agent: *\nDisallow: /")
        )
    )
    with pytest.raises(ValueError, match="robots"):
        RSSAdapter(c).fetch(source())


def test_invalid_feed() -> None:
    with pytest.raises(ValueError):
        RSSAdapter(client(body=b"<html>unavailable</html>")).fetch(source())


def test_pipeline_partial_failure_and_history(tmp_path: Path) -> None:
    config = settings(tmp_path)
    path = run(
        config, [source("broken"), source()], DAY, client(("broken.example",)), now=NOW
    )
    assert path.exists()
    record = json.loads((config.history_dir / f"{DAY}.json").read_text())
    assert record["status"] == "dry_run"
    assert record["selected_count"] == 1
    assert record["errors"][0]["source"] == "broken"
    assert record["brief"]["items"][0]["url"] == "https://example.org/news/1"
    run(config, [source()], DAY, client(), now=NOW)
    assert len(list(config.history_dir.glob("*.json"))) == 3


def test_all_core_fail_even_if_other_succeeds(tmp_path: Path) -> None:
    config = settings(tmp_path)
    with pytest.raises(RuntimeError, match="core"):
        run(
            config,
            [source("broken"), source("other", core=False)],
            DAY,
            client(("broken.example",)),
            now=NOW,
        )
    assert not config.output_dir.exists()
    assert (
        json.loads((config.history_dir / f"{DAY}.json").read_text())["status"]
        == "failed"
    )


@pytest.mark.parametrize(
    "body",
    [
        FEED.replace(b"11 Sep 2026", b"01 Sep 2026"),
        FEED.replace(b"11 Sep 2026", b"13 Sep 2026"),
    ],
)
def test_stale_and_future_news_not_selected(tmp_path: Path, body: bytes) -> None:
    with pytest.raises(RuntimeError, match="No eligible"):
        run(settings(tmp_path), [source()], DAY, client(body=body), now=NOW)
    assert not (tmp_path / "output").exists()


def test_published_guard_and_force(tmp_path: Path) -> None:
    config = settings(tmp_path)
    config.history_dir.mkdir()
    (config.history_dir / f"{DAY}-previous.json").write_text(
        json.dumps({"publish": {"status": "published", "content_hash": "old"}})
    )
    with pytest.raises(RuntimeError, match="successful"):
        run(config, [source()], DAY, client(), now=NOW)
    assert run(config, [source()], DAY, client(), force=True, now=NOW).exists()


def test_consumer_gaming_is_excluded() -> None:
    assert rank_news([item("New games on GeForce NOW")], {"test": 100}, NOW) == []
