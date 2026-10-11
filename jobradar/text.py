from __future__ import annotations

import html
import re
from datetime import datetime, timezone

_TAG_RE = re.compile(r"<[^>]+>")
_BLOCK_RE = re.compile(r"</?(p|div|li|ul|ol|br|h[1-6]|tr|section)[^>]*>", re.I)
_WS_RE = re.compile(r"[ \t\r\f\v]+")
_NL_RE = re.compile(r"\n\s*\n+")


def html_to_text(raw: str | None) -> str:
    """Turn (possibly HTML-escaped) HTML into readable plain text."""
    if not raw:
        return ""
    text = html.unescape(raw)
    if "&lt;" in text or "&gt;" in text:  # Greenhouse double-escapes its content
        text = html.unescape(text)
    text = _BLOCK_RE.sub("\n", text)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text).replace("\xa0", " ")
    text = _WS_RE.sub(" ", text)
    text = _NL_RE.sub("\n", text)
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def parse_date(value) -> datetime | None:
    """Parse ISO strings, epoch seconds or epoch milliseconds into aware UTC datetimes."""
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)):
            seconds = value / 1000 if value > 10_000_000_000 else value
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        s = str(value).strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        if len(s) == 10:  # plain date
            s += "T00:00:00+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def contains_term(haystack_lower: str, term: str) -> bool:
    """Case-insensitive whole-word-ish match. 'sql' won't match 'nosql' but 'c++' works."""
    t = norm(term)
    if not t:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])"
    return re.search(pattern, haystack_lower) is not None
