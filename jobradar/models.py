from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Job:
    """One job posting, normalized across all job-board sources."""

    source: str                      # greenhouse | lever | ashby | smartrecruiters | workable
    company: str                     # display name
    company_slug: str                # board identifier used in the API
    job_id: str
    title: str
    url: str
    apply_url: str = ""
    location: str = ""               # human-readable, may list several places
    remote: bool | None = None       # True / False / unknown
    posted: datetime | None = None   # timezone-aware UTC
    department: str = ""
    employment_type: str = ""
    seniority: str = ""              # board-provided level label, if any
    description: str = ""            # plain text

    # Filled in by the pipeline
    score: int = 0
    reasons: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    min_years: int | None = None
    is_new: bool = False
    first_seen: str = ""
    llm_score: int | None = None
    llm_reason: str = ""

    @property
    def uid(self) -> str:
        return f"{self.source}:{self.company_slug}:{self.job_id}".lower()

    def to_dict(self) -> dict:
        return {
            "uid": self.uid,
            "source": self.source,
            "company": self.company,
            "title": self.title,
            "url": self.url,
            "apply_url": self.apply_url or self.url,
            "location": self.location,
            "remote": self.remote,
            "posted": self.posted.isoformat() if self.posted else None,
            "department": self.department,
            "employment_type": self.employment_type,
            "seniority": self.seniority,
            "score": self.score,
            "reasons": self.reasons,
            "flags": self.flags,
            "min_years": self.min_years,
            "is_new": self.is_new,
            "first_seen": self.first_seen,
            "llm_score": self.llm_score,
            "llm_reason": self.llm_reason,
            "snippet": self.description[:400],
        }
