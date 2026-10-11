"""SmartRecruiters Posting API: https://api.smartrecruiters.com/v1/companies/{id}/postings

The list endpoint has no description text, so filtering relies on title, location and the
board's experience level. That keeps it to one request per 100 postings.
"""
from __future__ import annotations

from ..models import Job
from ..text import parse_date

NAME = "smartrecruiters"
BOARD_URL = "https://careers.smartrecruiters.com/{slug}"
PAGE = 100


def fetch(slug: str, http) -> tuple[str, list[Job]]:
    content: list[dict] = []
    offset = 0
    while True:
        data = http.get_json(
            f"https://api.smartrecruiters.com/v1/companies/{slug}/postings", {"limit": PAGE, "offset": offset}
        )
        batch = data.get("content") or []
        content.extend(batch)
        total = data.get("totalFound") or 0
        offset += PAGE
        if not batch or offset >= total or offset > 5000:
            break
    return parse(slug, content)


def parse(slug: str, postings: list[dict]) -> tuple[str, list[Job]]:
    company = slug
    jobs = []
    for p in postings:
        comp = p.get("company") or {}
        company = comp.get("name") or company
        loc = p.get("location") or {}
        location = loc.get("fullLocation") or ", ".join(
            x for x in (loc.get("city"), loc.get("region"), loc.get("country", "").upper()) if x
        )
        ident = comp.get("identifier") or slug
        jobs.append(
            Job(
                source=NAME,
                company=company,
                company_slug=slug,
                job_id=str(p.get("id")),
                title=(p.get("name") or "").strip(),
                url=f"https://jobs.smartrecruiters.com/{ident}/{p.get('id')}",
                location=location,
                remote=bool(loc.get("remote")) if loc.get("remote") is not None else None,
                posted=parse_date(p.get("releasedDate")),
                department=(p.get("department") or {}).get("label", ""),
                employment_type=(p.get("typeOfEmployment") or {}).get("label", ""),
                seniority=(p.get("experienceLevel") or {}).get("label", ""),
            )
        )
    return company, jobs
