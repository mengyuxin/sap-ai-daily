"""Conservative URL and text normalization."""

import hashlib
import re
import unicodedata
from html import unescape
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def plain_text(value: str) -> str:
    """Remove feed markup without interpreting embedded instructions."""
    value = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", "", value, flags=re.S | re.I)
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", value)).split())


def normalize_title(value: str) -> str:
    """Normalize Unicode, punctuation and whitespace."""
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", value).casefold()))


def canonical_url(value: str) -> str:
    """Remove known tracking parameters while preserving semantic query parameters."""
    parts = urlsplit(value)
    query = sorted(
        (key, val)
        for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}
    )
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path or "/",
            urlencode(query),
            "",
        )
    )


def fingerprint(value: str) -> str:
    """Return a stable content identity."""
    return hashlib.sha256(value.encode()).hexdigest()
