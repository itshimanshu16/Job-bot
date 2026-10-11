"""Decide which jobs to keep and how well each one matches the search."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from .models import Job
from .text import contains_term, norm

# "3+ years", "2-4 years", "2 to 4 yrs", "at least 3 years", "3 years of experience"
_RANGE = re.compile(r"(\d{1,2})\s*\+?\s*(?:-|–|—|to)\s*(\d{1,2})\s*\+?\s*(?:years?|yrs?)\b", re.I)
_PLUS = re.compile(r"(\d{1,2})\s*\+\s*(?:years?|yrs?)\b", re.I)
_MIN = re.compile(r"(?:minimum|min\.?|at\s+least|over)\s*(?:of\s*)?(\d{1,2})\s*(?:years?|yrs?)\b", re.I)
_EXP = re.compile(r"(\d{1,2})\s*(?:years?|yrs?)\s+(?:of\s+)?(?:[a-z/&-]+\s+){0,4}experience", re.I)

# Board-provided seniority labels (SmartRecruiters, Workable)
_LEVELS = {
    "internship": 0, "entry level": 0, "entry-level": 0, "associate": 1,
    "mid-senior level": 4, "mid level": 3, "senior level": 5, "director": 10, "executive": 15,
}

_FEE_TERMS = ["registration fee", "security deposit", "training fee", "processing fee",
              "refundable deposit", "pay a fee", "joining fee", "documentation charge"]
_CONTACT_TERMS = ["whatsapp", "telegram"]
_PERSONAL_MAIL = re.compile(r"[\w.+-]+@(gmail|yahoo|hotmail|outlook|rediffmail)\.com", re.I)


def required_years(job: Job) -> int | None:
    """Best guess of the minimum years of experience the posting asks for."""
    if job.seniority:
        level = _LEVELS.get(norm(job.seniority))
        if level is not None:
            return level
    text = job.description
    if not text:
        return None
    found: list[int] = []
    for m in _RANGE.finditer(text):
        found.append(int(m.group(1)))
    stripped = _RANGE.sub(" ", text)
    for rx in (_PLUS, _MIN, _EXP):
        for m in rx.finditer(stripped):
            found.append(int(m.group(1)))
    found = [n for n in found if n <= 25]
    return max(found) if found else None


def scam_flags(job: Job) -> list[str]:
    low = job.description.lower()
    flags = []
    if any(t in low for t in _FEE_TERMS):
        flags.append("mentions a fee or deposit")
    if any(t in low for t in _CONTACT_TERMS):
        flags.append("asks for WhatsApp/Telegram contact")
    if _PERSONAL_MAIL.search(job.description):
        flags.append("uses a personal email address")
    return flags


class Matcher:
    def __init__(self, search: dict, now: datetime | None = None):
        self.s = search
        self.now = now or datetime.now(timezone.utc)
        self.drops: dict[str, int] = {}

    def _drop(self, reason: str) -> bool:
        self.drops[reason] = self.drops.get(reason, 0) + 1
        return False

    def _location_ok(self, job: Job) -> tuple[bool, str]:
        loc = norm(job.location)
        for bad in self.s["exclude_locations"]:
            if contains_term(loc, bad):
                return False, ""
        wanted = self.s["locations"]
        is_remote = job.remote is True or "remote" in loc
        if not wanted:
            return True, "remote" if is_remote else ""
        for place in wanted:
            if contains_term(loc, place):
                return True, place
        if is_remote and self.s["include_remote"]:
            return True, "remote"
        if not loc and job.remote is None:
            return True, ""  # unknown location: let the person decide
        return False, ""

    def evaluate(self, job: Job) -> bool:
        """Return True if the job is kept. Fills job.score / reasons / flags / min_years."""
        s = self.s
        title = norm(job.title)
        body = job.description.lower()
        reasons: list[str] = []
        score = 0

        # 1. Role keywords
        title_hits = [k for k in s["keywords"] if contains_term(title, k)]
        body_hits = [k for k in s["keywords"] if k not in title_hits and contains_term(body, k)]
        if title_hits:
            score += 40 + min(10 * (len(title_hits) - 1), 20)
            reasons.append("title: " + ", ".join(title_hits[:3]))
        elif s["search_description"] and body_hits:
            score += 18
            reasons.append("description mentions: " + ", ".join(body_hits[:3]))
        else:
            return self._drop("role keywords not matched")

        # 2. Hard excludes
        if any(contains_term(title, x) for x in s["exclude_title"]):
            return self._drop("excluded title word (e.g. senior/manager)")
        if any(x.lower() in body or x.lower() in title for x in s["exclude_text"]):
            return self._drop("excluded phrase in description")

        # 3. Location
        loc_ok, loc_reason = self._location_ok(job)
        if not loc_ok:
            return self._drop("location not wanted")
        if loc_reason == "remote":
            score += 5
            reasons.append("remote")
        elif loc_reason:
            score += 10
            reasons.append(f"location: {loc_reason}")

        # 4. Freshness
        if job.posted:
            age = self.now - job.posted
            if s["max_age_days"] and age > timedelta(days=s["max_age_days"]):
                return self._drop("older than max_age_days")
            if age <= timedelta(days=3):
                score += 10
                reasons.append("posted in last 3 days")
            elif age <= timedelta(days=7):
                score += 5

        # 5. Experience
        years = required_years(job)
        job.min_years = years
        limit = s["max_years_experience"]
        if limit is not None:
            if years is None:
                if s["unknown_experience"] == "drop":
                    return self._drop("experience not stated")
            elif years > limit:
                return self._drop("asks for more experience than max_years_experience")
            else:
                score += 5
                reasons.append(f"asks ≤{limit} yrs" if years else "no experience required")

        # 6. Fresher / early-career signals
        fresh_title = [t for t in s["fresher_terms"] if contains_term(title, t)]
        fresh_body = [t for t in s["fresher_terms"] if t not in fresh_title and contains_term(body, t)]
        if fresh_title or norm(job.seniority) in ("entry level", "entry-level", "internship"):
            score += 15
            reasons.append("early-career role")
        elif fresh_body:
            score += 8
            reasons.append("mentions " + fresh_body[0])

        # 7. Skills
        skill_hits = [k for k in s["skills"] if contains_term(body, k) or contains_term(title, k)]
        if skill_hits:
            score += min(3 * len(skill_hits), 15)
            reasons.append("skills: " + ", ".join(skill_hits[:5]))

        # 8. Scam signals (flag, don't hide)
        job.flags = scam_flags(job)
        if job.flags:
            score -= 30

        job.score = max(0, min(100, score))
        job.reasons = reasons
        if job.score < s["min_score"]:
            return self._drop("below min_score")
        return True
