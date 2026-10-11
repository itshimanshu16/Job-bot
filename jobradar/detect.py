"""Work out which job board a company uses from its careers URL."""
from __future__ import annotations

import re

PATTERNS: list[tuple[str, re.Pattern]] = [
    ("greenhouse", re.compile(r"boards-api\.greenhouse\.io/v1/boards/([A-Za-z0-9_-]+)", re.I)),
    ("greenhouse", re.compile(r"greenhouse\.io/embed/job_board(?:/js)?\?for=([A-Za-z0-9_-]+)", re.I)),
    ("greenhouse", re.compile(r"(?:job-boards|boards)(?:\.eu)?\.greenhouse\.io/([A-Za-z0-9_-]+)", re.I)),
    ("lever", re.compile(r"(?:jobs|api)\.lever\.co/(?:v0/postings/)?([A-Za-z0-9._-]+)", re.I)),
    ("ashby", re.compile(r"(?:jobs\.ashbyhq\.com|posting-api/job-board)/([A-Za-z0-9._%-]+)", re.I)),
    ("smartrecruiters", re.compile(r"(?:jobs|careers)\.smartrecruiters\.com/([A-Za-z0-9_-]+)", re.I)),
    ("smartrecruiters", re.compile(r"api\.smartrecruiters\.com/v1/companies/([A-Za-z0-9_-]+)", re.I)),
    ("workable", re.compile(r"apply\.workable\.com/(?!api/|j/)([A-Za-z0-9_-]+)", re.I)),
    ("workable", re.compile(r"widget/accounts/([A-Za-z0-9_-]+)", re.I)),
    ("workable", re.compile(r"https?://(?!www\.|apply\.|jobs\.)([A-Za-z0-9_-]+)\.workable\.com", re.I)),
]

_IGNORE = {"embed", "api", "v1", "j", "jobs", "careers", "static", "assets", "js"}


def find_boards(text: str) -> list[tuple[str, str]]:
    """Every (board type, slug) pair mentioned in a URL or HTML page, in order, de-duplicated."""
    found: list[tuple[str, str]] = []
    for source, rx in PATTERNS:
        for m in rx.finditer(text or ""):
            slug = m.group(1).strip("/.")
            if slug.lower() in _IGNORE:
                continue
            pair = (source, slug)
            if pair not in found:
                found.append(pair)
    return found


def detect(url: str, http=None) -> list[tuple[str, str]]:
    hits = find_boards(url)
    if hits or http is None:
        return hits
    try:
        page = http.get_text(url)
    except Exception:
        return []
    return find_boards(page)
