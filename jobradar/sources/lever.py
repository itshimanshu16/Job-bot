"""Lever Postings API: https://api.lever.co/v0/postings/{site}?mode=json"""
from __future__ import annotations

from ..models import Job
from ..text import html_to_text, parse_date

NAME = "lever"
BOARD_URL = "https://jobs.lever.co/{slug}"
PAGE = 100


def fetch(slug: str, http) -> tuple[str, list[Job]]:
    postings: list[dict] = []
    skip = 0
    while True:
        page = http.get_json(
            f"https://api.lever.co/v0/postings/{slug}", {"mode": "json", "skip": skip, "limit": PAGE}
        )
        if not isinstance(page, list) or not page:
            break
        postings.extend(page)
        if len(page) < PAGE:
            break
        skip += PAGE
        if skip > 5000:  # safety stop
            break
    return parse(slug, postings)


def parse(slug: str, postings: list[dict]) -> tuple[str, list[Job]]:
    company = slug.replace("-", " ").title()
    jobs = []
    for p in postings:
        cats = p.get("categories") or {}
        all_locs = cats.get("allLocations") or ([cats["location"]] if cats.get("location") else [])
        workplace = (p.get("workplaceType") or "").lower()
        parts = [p.get("descriptionPlain") or html_to_text(p.get("description"))]
        for block in p.get("lists") or []:
            parts.append(block.get("text") or "")
            parts.append(html_to_text(block.get("content")))
        parts.append(p.get("additionalPlain") or "")
        jobs.append(
            Job(
                source=NAME,
                company=company,
                company_slug=slug,
                job_id=str(p.get("id")),
                title=(p.get("text") or "").strip(),
                url=p.get("hostedUrl") or "",
                apply_url=p.get("applyUrl") or "",
                location="; ".join(all_locs),
                remote=True if workplace == "remote" else (False if workplace in ("onsite", "on-site", "hybrid") else None),
                posted=parse_date(p.get("createdAt")),
                department=cats.get("team") or cats.get("department") or "",
                employment_type=cats.get("commitment") or "",
                description="\n".join(x for x in parts if x).strip(),
            )
        )
    return company, jobs
