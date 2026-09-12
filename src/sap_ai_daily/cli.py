"""One safe entry point for the Phase 1 pipeline."""

import argparse
import logging
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from time import monotonic
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx

from sap_ai_daily.config import Settings, Source, load_config
from sap_ai_daily.fetch.rss import USER_AGENT, RSSAdapter
from sap_ai_daily.models import DailyBrief, NewsItem
from sap_ai_daily.process.deduplicate import deduplicate
from sap_ai_daily.process.rank import rank_news
from sap_ai_daily.publish.dry_run import DryRunPublisher
from sap_ai_daily.storage.history import save_history, was_published

logger = logging.getLogger(__name__)


def window(day: date, now: datetime, hours: int) -> tuple[datetime, datetime]:
    """Use Shanghai calendar boundaries and exclude any future publication time."""
    if now.tzinfo is None:
        raise ValueError("Timezone-aware now required")
    end = datetime.combine(day + timedelta(days=1), time.min, ZoneInfo("Asia/Shanghai"))
    cutoff = min(end, now)
    return cutoff - timedelta(hours=hours), cutoff


def run(
    settings: Settings,
    sources: list[Source],
    day: date,
    client: httpx.Client,
    force: bool = False,
    now: datetime | None = None,
) -> Path:
    """Fetch, select and save a dry-run brief; record failures without secret values."""
    now = now or datetime.now(UTC)
    run_id = uuid4().hex
    started = monotonic()
    record = {
        "date": day.isoformat(),
        "run_id": run_id,
        "generated_at": now.isoformat(),
        "sources": [],
        "fetched_count": 0,
        "deduplicated_count": 0,
        "selected_count": 0,
        "status": "running",
        "errors": [],
    }
    try:
        if was_published(settings.history_dir, day.isoformat()) and not force:
            raise RuntimeError("Existing successful publication")
        if day > now.astimezone(ZoneInfo(settings.timezone)).date():
            raise ValueError("Future business date")
        start, cutoff = window(day, now, settings.lookback_hours)
        adapter = RSSAdapter(client)
        items: list[NewsItem] = []
        succeeded: set[str] = set()
        for source in sources:
            source_start = monotonic()
            result = {"source": source.id, "url": str(source.url), "count": 0}
            try:
                fetched = adapter.fetch(source)
                items.extend(fetched)
                succeeded.add(source.id)
                result.update(status="ok", count=len(fetched), skipped=adapter.skipped)
            except (httpx.HTTPError, ValueError) as exc:
                result.update(status="failed", error=type(exc).__name__)
                record["errors"].append(
                    {"source": source.id, "error": type(exc).__name__}
                )
            record["sources"].append(result)
            logger.info(
                "run_id=%s stage=fetch source=%s count=%s "
                "duration=%.3f status=%s error=%s",
                run_id,
                source.id,
                result["count"],
                monotonic() - source_start,
                result["status"],
                result.get("error", "none"),
            )
        record["fetched_count"] = len(items)
        core = {source.id for source in sources if source.core}
        if not succeeded or (core and not core.intersection(succeeded)):
            raise RuntimeError("All core sources failed")
        fresh = [item for item in items if start <= item.published_at < cutoff]
        priorities = {source.id: source.priority for source in sources}
        unique = deduplicate(fresh, priorities)
        record["deduplicated_count"] = len(unique)
        selected = rank_news(unique, priorities, cutoff)[: settings.max_items]
        record["selected_count"] = len(selected)
        if not selected:
            raise RuntimeError("No eligible fresh news; no draft generated")
        brief = DailyBrief(
            date=day,
            items=selected,
            source_count=len({i.source_id for i in selected}),
            generated_at=now,
        )
        record["brief"] = brief.model_dump(mode="json")
        result = DryRunPublisher(settings).publish(brief)
        record.update(status="dry_run", publish=result.model_dump(mode="json"))
        return Path(result.path)
    except Exception as exc:
        record["status"] = "failed"
        record["errors"].append({"stage": "pipeline", "error": type(exc).__name__})
        raise
    finally:
        record["duration"] = round(monotonic() - started, 3)
        save_history(settings.history_dir, record)
        logger.info(
            "run_id=%s stage=pipeline source=all count=%s "
            "duration=%.3f status=%s error=%s",
            run_id,
            record["selected_count"],
            record["duration"],
            record["status"],
            "see_history" if record["errors"] else "none",
        )


def main() -> int:
    """Run only a local dry run; production remains unavailable in this release."""
    parser = argparse.ArgumentParser(description="AI・SAP 早报（Phase 1 / Dry Run）")
    parser.add_argument("command", choices=["run"])
    parser.add_argument("--dry-run", action="store_true", help="默认行为，不发送内容")
    parser.add_argument("--date", type=date.fromisoformat)
    parser.add_argument("--config-dir", type=Path, default=Path("config"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        settings, sources = load_config(args.config_dir)
        day = args.date or datetime.now(ZoneInfo(settings.timezone)).date()
        with httpx.Client(
            timeout=20, follow_redirects=True, headers={"User-Agent": USER_AGENT}
        ) as client:
            path = run(settings, sources, day, client, args.force)
        print(f"Dry Run 已生成：{path}")
        return 0
    except Exception as exc:
        logger.error(
            "stage=cli status=failed error=%s；请检查配置和运行记录", type(exc).__name__
        )
        return 1
