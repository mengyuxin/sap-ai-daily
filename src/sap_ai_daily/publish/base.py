from typing import Protocol

from sap_ai_daily.models import DailyBrief, PublishResult


class Publisher(Protocol):
    def publish(self, brief: DailyBrief) -> PublishResult:
        """Publish through an explicitly chosen adapter."""
        ...
