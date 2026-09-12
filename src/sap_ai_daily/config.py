"""YAML configuration; credentials are never loaded into logs."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, HttpUrl, model_validator

from .models import Category, Record


class Source(Record):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str
    category: Category
    type: Literal["rss"] = "rss"
    url: HttpUrl
    priority: int = Field(ge=0, le=100)
    enabled: bool
    core: bool = True


class SourceList(Record):
    sources: list[Source]

    @model_validator(mode="after")
    def unique_ids(self) -> "SourceList":
        """Reject ambiguous source identities."""
        if len({s.id for s in self.sources}) != len(self.sources):
            raise ValueError("Duplicate source IDs")
        return self


class Settings(Record):
    timezone: Literal["Asia/Shanghai"] = "Asia/Shanghai"
    max_items: int = Field(default=8, ge=1, le=8)
    lookback_hours: int = Field(default=48, ge=1, le=168)
    max_length: int = Field(default=2000, ge=100)
    include_links: bool = False
    output_dir: Path = Path("output")
    history_dir: Path = Path("data")


def load_config(directory: Path) -> tuple[Settings, list[Source]]:
    """Load configuration; relative output paths use the current working directory."""
    settings = Settings.model_validate(
        yaml.safe_load((directory / "settings.yaml").read_text()) or {}
    )
    sources = SourceList.model_validate(
        yaml.safe_load((directory / "sources.yaml").read_text())
    )
    return settings, [source for source in sources.sources if source.enabled]
