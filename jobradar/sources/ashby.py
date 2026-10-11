"""Ashby Posting API: https://api.ashbyhq.com/posting-api/job-board/{org}"""
from __future__ import annotations

import re

from ..models import Job
from ..text import html_to_text, parse_date

NAME = "ashby"
BOARD_URL = "https://jobs.ashbyhq.com/{slug}"


def fetch(slug: str, http) -> tuple[str, list[Job]]:
    data = http.get_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", {"includeCompensation": "false"})
    return parse(slug, data)


def parse(slug: str, data: dict) -> tuple[str, list[Job]]:
    company = slug.replace("-", " ").title()
    jobs = []
    for j in data.get("jobs") or []:
        if j.get("isListed") is False:
            continue
        locs = [j.get("location") or ""]
        locs += [s.get("location", "") for s in (j.get("secondaryLocations") or [])]
        workplace = (j.get("workplaceType") or "").lower()
        if workplace:
            remote = workplace == "remote"
        else:
            remote = bool(j.get("isRemote")) if j.get("isRemote") is not None else None
        jobs.append(
            Job(
                source=NAME,
                company=company,
                company_slug=slug,
                job_id=str(j.get("id")),
                title=(j.get("title") or "").strip(),
                url=j.get("jobUrl") or "",
                apply_url=j.get("applyUrl") or "",
                location="; ".join(l for l in locs if l),
                remote=remote,
                posted=parse_date(j.get("publishedAt")),
                department=j.get("department") or j.get("team") or "",
                employment_type=re.sub(r"(?<=[a-z])(?=[A-Z])", " ", j.get("employmentType") or "").capitalize(),
                description=j.get("descriptionPlain") or html_to_text(j.get("descriptionHtml")),
            )
        )
    return company, jobs
