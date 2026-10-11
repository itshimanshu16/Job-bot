"""Workable public widget API: https://apply.workable.com/api/v1/widget/accounts/{subdomain}?details=true"""
from __future__ import annotations

from ..models import Job
from ..text import html_to_text, parse_date

NAME = "workable"
BOARD_URL = "https://apply.workable.com/{slug}"


def fetch(slug: str, http) -> tuple[str, list[Job]]:
    data = http.get_json(f"https://apply.workable.com/api/v1/widget/accounts/{slug}", {"details": "true"})
    return parse(slug, data)


def _location(j: dict) -> str:
    places = []
    for loc in j.get("locations") or []:
        if loc.get("hidden"):
            continue
        places.append(", ".join(x for x in (loc.get("city"), loc.get("region"), loc.get("country")) if x))
    if not places:
        places.append(", ".join(x for x in (j.get("city"), j.get("state"), j.get("country")) if x))
    seen, out = set(), []
    for p in places:  # the widget repeats multi-location jobs
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return "; ".join(out)


def parse(slug: str, data: dict) -> tuple[str, list[Job]]:
    company = data.get("name") or slug
    jobs, seen_codes = [], set()
    for j in data.get("jobs") or []:
        code = j.get("shortcode") or j.get("code") or j.get("id")
        if code in seen_codes:
            continue
        seen_codes.add(code)
        desc = "\n".join(
            html_to_text(j.get(k)) for k in ("description", "requirements", "benefits") if j.get(k)
        )
        jobs.append(
            Job(
                source=NAME,
                company=company,
                company_slug=slug,
                job_id=str(code),
                title=(j.get("title") or "").strip(),
                url=j.get("url") or j.get("shortlink") or f"https://apply.workable.com/{slug}/j/{code}/",
                apply_url=j.get("application_url") or "",
                location=_location(j),
                remote=bool(j.get("telecommuting")) if j.get("telecommuting") is not None else None,
                posted=parse_date(j.get("published_on") or j.get("created_at")),
                department=j.get("department") or "",
                employment_type=j.get("employment_type") or "",
                seniority=j.get("experience") or "",
                description=desc,
            )
        )
    return company, jobs
