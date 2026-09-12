"""Render review-only drafts, reducing summaries before removing complete items."""

import re

from sap_ai_daily.config import Settings
from sap_ai_daily.models import DailyBrief

NUMBERS = "①②③④⑤⑥⑦⑧"


def render_weibo(brief: DailyBrief, settings: Settings) -> str:
    """Keep complete titles; shorten using whole sentences, never slice final text."""

    def render(summary_limit: int, count: int) -> str:
        lines = [
            f"【{brief.headline}｜{brief.date:%Y.%m.%d}】",
            "",
            "（Dry Run · 待人工编辑）",
        ]
        for index, item in enumerate(brief.items[:count]):
            lines.extend(["", f"{NUMBERS[index]} {item.title}"])
            sentences = re.split(r"(?<=[。！？.!?])\s*", item.summary_raw)
            summary = ""
            for sentence in sentences:
                candidate = (summary + " " + sentence).strip()
                if len(candidate) > summary_limit:
                    break
                summary = candidate
            if summary:
                lines.append(summary)
            if settings.include_links:
                lines.append(str(item.url))
        if count < len(brief.items):
            lines.extend(["", f"另有 {len(brief.items) - count} 条见运行记录。"])
        lines.extend(
            [
                "",
                "今日关注：",
                brief.editor_note,
                "",
                " ".join(f"#{t}" for t in brief.hashtags),
            ]
        )
        return "\n".join(lines) + "\n"

    for limit in (120, 60, 0):
        text = render(limit, len(brief.items))
        if len(text) <= settings.max_length:
            return text
    for count in range(len(brief.items) - 1, 0, -1):
        text = render(0, count)
        if len(text) <= settings.max_length:
            return text
    raise ValueError("Length limit cannot fit one complete item")
