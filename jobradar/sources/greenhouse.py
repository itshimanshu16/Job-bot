"""Greenhouse Job Board API: https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"""
from __future__ import annotations

from ..models import Job
from ..text import html_to_text, parse_date

NAME = "greenhouse"
BOARD_URL = "https://boards.greenhouse.io/{slug}"


def fetch(slug: str, http) -> tuple[str, list[Job]]:
    data = http.get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", {"content": "true"})
    return parse(slug, data)


def parse(slug: str, data: dict) -> tuple[str, list[Job]]:
    raw_jobs = data.get("jobs") or []
    company = next((j.get("company_name") for j in raw_jobs if j.get("company_name")), slug)
    jobs = []
    for j in raw_jobs:
        location = (j.get("location") or {}).get("name") or ""
        offices = ", ".join(o.get("name", "") for o in (j.get("offices") or []) if o.get("name"))
        depts = ", ".join(d.get("name", "") for d in (j.get("departments") or []) if d.get("name"))
        jobs.append(
            Job(
                source=NAME,
                company=company,
                company_slug=slug,
                job_id=str(j.get("id")),
                title=(j.get("title") or "").strip(),
                url=j.get("absolute_url") or "",
                location=location if location else offices,
                remote=True if "remote" in location.lower() else None,
                posted=parse_date(j.get("first_published") or j.get("updated_at")),
                department=depts,
                description=html_to_text(j.get("content")),
            )
        )
    return company, jobs
