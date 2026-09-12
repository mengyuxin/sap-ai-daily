"""Explicitly unavailable until a future, separately reviewed production phase."""

from sap_ai_daily.models import DailyBrief, PublishResult


class WeiboPublisher:
    def publish(self, brief: DailyBrief) -> PublishResult:
        """Fail closed even if credentials and PUBLISH_ENABLED are supplied."""
        raise RuntimeError("Phase 1 禁止真实发布；请使用 --dry-run")
