from typing import Protocol

from sap_ai_daily.config import Source
from sap_ai_daily.models import NewsItem


class SourceAdapter(Protocol):
    def fetch(self, source: Source) -> list[NewsItem]:
        """Read publicly accessible source entries."""
        ...
