"""Made-up job boards for `python -m jobradar demo` and the tests. No network needed.

The companies are fictional; the JSON shapes match the real public APIs.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .http import HttpError

DEMO_COMPANIES = {
    "greenhouse": ["orbitpay"],
    "lever": ["kettle-foods"],
    "ashby": ["northwind-labs"],
    "smartrecruiters": ["AcmeMotors"],
    "workable": ["brightline-logistics"],
}


def _iso(now: datetime, days: float) -> str:
    return (now - timedelta(days=days)).isoformat()


def payloads(now: datetime | None = None) -> dict[str, object]:
    now = now or datetime.now(timezone.utc)
    ms = lambda d: int((now - timedelta(days=d)).timestamp() * 1000)  # noqa: E731
    gh_content = lambda body: body.replace("<", "&lt;").replace(">", "&gt;")  # noqa: E731
    return {
        "greenhouse/orbitpay": {"jobs": [
            {"id": 101, "title": "Business Analyst - Graduate Program", "company_name": "OrbitPay",
             "absolute_url": "https://example.com/orbitpay/101", "location": {"name": "Bengaluru, India"},
             "first_published": _iso(now, 1), "departments": [{"name": "Strategy"}],
             "content": gh_content("<p>Join our graduate program. 0-1 years of experience. Strong SQL and Excel; "
                                   "Power BI is a plus. 2026 batch and 2027 batch welcome.</p>")},
            {"id": 102, "title": "Senior Business Analyst", "company_name": "OrbitPay",
             "absolute_url": "https://example.com/orbitpay/102", "location": {"name": "Bengaluru, India"},
             "first_published": _iso(now, 2), "content": gh_content("<p>6+ years of experience in analytics.</p>")},
            {"id": 103, "title": "Data Analyst", "company_name": "OrbitPay",
             "absolute_url": "https://example.com/orbitpay/103", "location": {"name": "Remote - India"},
             "first_published": _iso(now, 6),
             "content": gh_content("<p>1-3 years of experience with SQL, Python and dashboards.</p>")},
            {"id": 104, "title": "Data Analyst", "company_name": "OrbitPay",
             "absolute_url": "https://example.com/orbitpay/104", "location": {"name": "London, UK"},
             "first_published": _iso(now, 3), "content": gh_content("<p>2+ years of experience.</p>")},
        ]},
        "lever/kettle-foods": [
            {"id": "kf-1", "text": "Supply Chain Analyst", "hostedUrl": "https://example.com/kettle/kf-1",
             "applyUrl": "https://example.com/kettle/kf-1/apply", "createdAt": ms(0.5), "workplaceType": "onsite",
             "categories": {"location": "Gurugram, India", "allLocations": ["Gurugram, India"],
                            "team": "Operations", "commitment": "Full-time"},
             "descriptionPlain": "Plan warehouse capacity and demand. Freshers welcome; we train you.",
             "lists": [{"text": "What we look for", "content": "<li>SQL and Excel</li><li>Clear communication</li>"}]},
            {"id": "kf-2", "text": "Operations Manager", "hostedUrl": "https://example.com/kettle/kf-2",
             "createdAt": ms(4), "categories": {"location": "Mumbai, India"},
             "descriptionPlain": "8+ years of experience running plants."},
            {"id": "kf-3", "text": "Graduate Engineer Trainee - Mechanical", "hostedUrl": "https://example.com/kettle/kf-3",
             "createdAt": ms(2), "workplaceType": "onsite",
             "categories": {"location": "Pune, India", "allLocations": ["Pune, India"], "commitment": "Full-time"},
             "descriptionPlain": "Production and maintenance rotations. B.Tech Mechanical, 2026 batch. "
                                 "Contact our HR on WhatsApp and pay a refundable deposit of Rs 2,000."},
        ],
        "ashby/northwind-labs": {"jobs": [
            {"id": "nw-1", "title": "Product Analyst", "location": "Bengaluru", "secondaryLocations": [],
             "publishedAt": _iso(now, 0.2), "isListed": True, "workplaceType": "Hybrid",
             "employmentType": "FullTime", "department": "Product",
             "jobUrl": "https://example.com/northwind/nw-1", "applyUrl": "https://example.com/northwind/nw-1/apply",
             "descriptionPlain": "Early career role. Own funnel metrics with SQL. Python helps."},
            {"id": "nw-2", "title": "Founder's Office Associate", "location": "Remote", "isListed": True,
             "workplaceType": "Remote", "publishedAt": _iso(now, 9),
             "jobUrl": "https://example.com/northwind/nw-2",
             "descriptionPlain": "Work with the founders on strategy and operations. Any background; analytics mindset."},
            {"id": "nw-3", "title": "Product Analyst (unlisted)", "location": "Bengaluru", "isListed": False,
             "publishedAt": _iso(now, 1), "jobUrl": "https://example.com/northwind/nw-3", "descriptionPlain": ""},
        ]},
        "smartrecruiters/AcmeMotors": {"totalFound": 2, "content": [
            {"id": "sr-1", "name": "Design Engineer - CAD", "releasedDate": _iso(now, 1.5),
             "company": {"identifier": "AcmeMotors", "name": "Acme Motors"},
             "location": {"city": "Chennai", "country": "in", "remote": False},
             "experienceLevel": {"id": "entry_level", "label": "Entry Level"},
             "typeOfEmployment": {"label": "Full-time"}, "department": {"label": "Engineering"}},
            {"id": "sr-2", "name": "Design Engineer - CAD", "releasedDate": _iso(now, 1.5),
             "company": {"identifier": "AcmeMotors", "name": "Acme Motors"},
             "location": {"city": "Detroit", "country": "us", "remote": False},
             "experienceLevel": {"id": "mid_senior_level", "label": "Mid-Senior Level"}},
        ]},
        "workable/brightline-logistics": {"name": "Brightline Logistics", "jobs": [
            {"title": "Business Analyst", "shortcode": "BL1", "url": "https://example.com/brightline/BL1",
             "published_on": (now - timedelta(days=12)).date().isoformat(), "telecommuting": False,
             "locations": [{"city": "Noida", "region": "Uttar Pradesh", "country": "India"}],
             "experience": "Entry level", "description": "<p>Walk-in drive on Saturday, bring your resume.</p>"},
            {"title": "Business Analyst", "shortcode": "BL2", "url": "https://example.com/brightline/BL2",
             "published_on": (now - timedelta(days=60)).date().isoformat(),
             "locations": [{"city": "Delhi", "country": "India"}], "description": "<p>Excel and SQL.</p>"},
        ]},
    }


class DemoHttp:
    """Stands in for Http and answers from the made-up payloads above."""

    def __init__(self, now: datetime | None = None, fail: set[str] | None = None):
        self.data = payloads(now)
        self.fail = fail or set()

    def get_json(self, url: str, params: dict | None = None):
        for key, payload in self.data.items():
            source, slug = key.split("/")
            if slug in url and _host_matches(source, url):
                if source in self.fail:
                    raise HttpError(404, "board not found (check the company slug)")
                if source == "lever" and params and params.get("skip"):
                    return []
                return payload
        raise HttpError(404, "board not found (check the company slug)")

    def get_text(self, url: str) -> str:
        return ""


def _host_matches(source: str, url: str) -> bool:
    hosts = {"greenhouse": "greenhouse.io", "lever": "lever.co", "ashby": "ashbyhq.com",
             "smartrecruiters": "smartrecruiters.com", "workable": "workable.com"}
    return hosts[source] in url
