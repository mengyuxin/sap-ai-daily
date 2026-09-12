"""Append-only per-run records plus a convenient daily snapshot."""

import json
from pathlib import Path
from typing import Any


def save_history(directory: Path, record: dict[str, Any]) -> None:
    """Preserve each attempt, including failures; never overwrite successful records."""
    directory.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    run_path = directory / f"{record['date']}-{record['run_id']}.json"
    with run_path.open("x", encoding="utf-8") as handle:
        handle.write(encoded)
    path = directory / f"{record['date']}.json"
    temp = path.with_suffix(".json.tmp")
    temp.write_text(encoded, encoding="utf-8")
    temp.replace(path)


def was_published(directory: Path, day: str) -> bool:
    """Refuse to replace a date with any recorded successful publication."""
    for path in directory.glob(f"{day}*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("publish", {}).get("status") == "published":
            return True
    return False
