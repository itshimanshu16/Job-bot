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


def parse_batch_years(text: str) -> set[int]:
    """Extract graduation/pass-out years mentioned in text."""
    years: set[int] = set()
    # Ranges like 2024-2026 graduates, 2025-2027 batch, 2025 to 2027
    r_range = re.findall(r"\b(20[2-3]\d)\s*(?:-|–|—|to)\s*(20[2-3]\d)\s*(?:batch|pass-?outs?|graduates?|passing\s+out)?\b", text, re.I)
    for y1, y2 in r_range:
        y1_int, y2_int = int(y1), int(y2)
        if y1_int <= y2_int:
            years.update(range(y1_int, y2_int + 1))

    # Patterns with batch context
    patterns = [
        r"(?:class\s+of|graduating\s+in|batch\s+of)\s*(20[2-3]\d)",
        r"\b(20[2-3]\d)\s*(?:/|\s+and\s+|\s+or\s+|,)\s*(20[2-3]\d)\s*(?:batch|pass-?outs?|graduates?|passing\s+out)?",
        r"\b(20[2-3]\d)\s*(?:batch|pass-?outs?|graduates?|passouts?)",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, re.I):
            for g in m.groups():
                if g:
                    years.add(int(g))
    return years


def parse_cgpa_cutoff(text: str) -> tuple[float | None, str | None]:
    """Detect CGPA cutoffs on 10-point scale. Returns (numeric_cutoff, matched_str)."""
    # X/10 scale
    m_10 = re.search(r"\b(\d+(?:\.\d+)?)\s*/\s*10\b", text, re.I)
    if m_10:
        return float(m_10.group(1)), m_10.group(1)

    # Ignore 4-point scales, e.g. /4, /4.0
    if re.search(r"\b\d+(?:\.\d+)?\s*/\s*4(?:\.0)?\b", text, re.I):
        return None, None

    # Patterns like minimum 8 CGPA, CGPA of 7.5 and above, minimum CGPA 8.0, CGPA 7 and above
    patterns = [
        r"(?:minimum|min\.?|at\s+least)?\s*(?:cgpa|gpa)\s*(?:of|is|:)?\s*(?:minimum|min\.?|at\s+least)?\s*(\d+(?:\.\d+)?)\s*(?:and\s+above|\+)?",
        r"(?:minimum|min\.?|at\s+least)?\s*(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:cgpa|gpa)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            val_str = m.group(1)
            val = float(val_str)
            # If <= 4.0 and refers to GPA without /10 or without CGPA, ignore as 4-point scale
            if val <= 4.0 and "cgpa" not in text.lower():
                continue
            return val, val_str

    return None, None


def check_branch_restriction(text: str, track_id: str) -> bool:
    """True if posting limits eligibility to CS/IT/ECE and does not allow mechanical or any branch."""
    if track_id != "software":
        return False
    low = text.lower()
    open_terms = ["any branch", "all branches", "any engineering", "mechanical"]
    if any(term in low for term in open_terms):
        return False

    patterns = [
        r"\b(?:b\.?tech|be|b\.?e\.?|degree|graduates?)\s*(?:in|from)?\s*(?:computer\s+science|cs\b|cse\b|information\s+technology|it\b)",
        r"\b(?:cse|cs|it|ece)\s*(?:/|\s+or\s+|\s+and\s+|,)?\s*(?:it|ece|cse|cs)?\s*(?:only|branches?|degree)",
        r"\b(?:b\.?tech\s+cse/it\s+only)\b",
    ]
    return any(re.search(pat, low, re.I) for pat in patterns)


def pick_resume(track: dict, job: Job) -> tuple[str, str]:
    """Select the best resume file and reason for a given job within a track."""
    for r in track.get("resumes", []):
        for term in r.get("prefer_when", []):
            if contains_term(job.title, term) or contains_term(job.company, term) or contains_term(job.description, term):
                return r["file"], f"mentions {term}"
    for r in track.get("resumes", []):
        if r.get("default"):
            return r["file"], "default for this track"
    if track.get("resumes"):
        return track["resumes"][0]["file"], "default for this track"
    return "", ""


class Matcher:
    def __init__(self, search: dict, now: datetime | None = None):
        self.s = search
        self.now = now or datetime.now(timezone.utc)
        self.drops: dict[str, int] = {}
        self.last_drop_reason: str = ""

    def _drop(self, reason: str) -> bool:
        self.drops[reason] = self.drops.get(reason, 0) + 1
        self.last_drop_reason = reason
        return False

    def _location_ok(self, job: Job) -> tuple[bool, str]:
        loc = norm(job.location)
        for bad in self.s.get("exclude_locations", []):
            if contains_term(loc, bad):
                return False, ""
        wanted = self.s.get("locations", [])
        is_remote = job.remote is True or "remote" in loc
        if not wanted:
            return True, "remote" if is_remote else ""
        for place in wanted:
            if contains_term(loc, place):
                return True, place
        if is_remote and self.s.get("include_remote", True):
            return True, "remote"
        if not loc and job.remote is None:
            return True, ""  # unknown location: let the person decide
        return False, ""

    def evaluate(self, job: Job) -> bool:
        """Return True if the job is kept. Fills job.score / reasons / flags / min_years."""
        s = self.s
        title = norm(job.title)
        body = job.description.lower()
        full_text = f"{title} {body}"
        reasons: list[str] = []
        score = 0
        job.flags = scam_flags(job)

        # 1. Role keywords
        keywords = s.get("keywords", [])
        title_hits = [k for k in keywords if contains_term(title, k)]
        body_hits = [k for k in keywords if k not in title_hits and contains_term(body, k)]
        if title_hits:
            score += 40 + min(10 * (len(title_hits) - 1), 20)
            reasons.append("title: " + ", ".join(title_hits[:3]))
        elif s.get("search_description") and body_hits:
            score += 18
            reasons.append("description mentions: " + ", ".join(body_hits[:3]))
        else:
            return self._drop("role keywords not matched")

        # 2. Hard excludes
        if any(contains_term(title, x) for x in s.get("exclude_title", [])):
            return self._drop("excluded title word (e.g. senior/manager)")
        if any(x.lower() in body or x.lower() in title for x in s.get("exclude_text", [])):
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
            if s.get("max_age_days") and age > timedelta(days=s["max_age_days"]):
                return self._drop("older than max_age_days")
            if age <= timedelta(days=3):
                score += 10
                reasons.append("posted in last 3 days")
            elif age <= timedelta(days=7):
                score += 5

        # 5. Experience
        years = required_years(job)
        job.min_years = years
        limit = s.get("max_years_experience")
        if limit is not None:
            if years is None:
                if s.get("unknown_experience") == "drop":
                    return self._drop("experience not stated")
            elif years > limit:
                return self._drop("asks for more experience than max_years_experience")
            else:
                score += 5
                reasons.append(f"asks ≤{limit} yrs" if years else "no experience required")

        # 6. Graduation batch eligibility check
        batch_years = parse_batch_years(full_text)
        cand_grad_year = s.get("candidate_grad_year", 2027)
        if batch_years:
            if cand_grad_year not in batch_years:
                return self._drop(f"not open to the {cand_grad_year} batch")
            score += 10
            reasons.append(f"open to {cand_grad_year} batch")

        # 7. Fresher / early-career signals
        fresher_terms = s.get("fresher_terms", [])
        fresh_title = [t for t in fresher_terms if contains_term(title, t)]
        fresh_body = [t for t in fresher_terms if t not in fresh_title and contains_term(body, t)]
        if fresh_title or norm(job.seniority) in ("entry level", "entry-level", "internship"):
            score += 15
            reasons.append("early-career role")
        elif fresh_body:
            score += 8
            reasons.append("mentions " + fresh_body[0])

        # 8. Skills
        skill_hits = [k for k in s.get("skills", []) if contains_term(body, k) or contains_term(title, k)]
        if skill_hits:
            score += min(3 * len(skill_hits), 15)
            reasons.append("skills: " + ", ".join(skill_hits[:5]))

        # 9. CGPA cutoff check
        cand_cgpa = s.get("candidate_cgpa", 7.64)
        if cand_cgpa is not None:
            cgpa_val, cgpa_str = parse_cgpa_cutoff(full_text)
            if cgpa_val is not None and cgpa_val > cand_cgpa:
                flag = f"asks for CGPA {cgpa_str}+ (resume shows {cand_cgpa})"
                if flag not in job.flags:
                    job.flags.append(flag)
                score -= 15

        # 10. Branch restriction check (software track only)
        track_id = s.get("track_id", "")
        if check_branch_restriction(full_text, track_id):
            flag = "may require a CS/IT degree"
            if flag not in job.flags:
                job.flags.append(flag)
            score -= 10

        # 11. Scam signals (flag, don't hide)
        if scam_flags(job):
            score -= 30

        job.score = max(0, min(100, score))
        job.reasons = reasons
        if job.score < s.get("min_score", 0):
            return self._drop("below min_score")
        return True
