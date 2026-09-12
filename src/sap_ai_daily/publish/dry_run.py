"""Local-only output: no network client or credentials."""

from sap_ai_daily.config import Settings
from sap_ai_daily.models import DailyBrief, PublishResult
from sap_ai_daily.process.normalize import fingerprint
from sap_ai_daily.render.weibo import render_weibo


class DryRunPublisher:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def publish(self, brief: DailyBrief) -> PublishResult:
        """Write a deterministic review draft to the local output directory."""
        text = render_weibo(brief, self.settings)
        path = self.settings.output_dir / f"{brief.date.isoformat()}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".md.tmp")
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(path)
        return PublishResult(
            status="dry_run", content_hash=fingerprint(text), text=text, path=str(path)
        )
