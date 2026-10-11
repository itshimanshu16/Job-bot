import copy
import json
from datetime import datetime, timedelta, timezone

import pytest

from jobradar.config import DEFAULTS, ConfigError, load_companies, load_config
from jobradar.demo import DEMO_COMPANIES, DemoHttp, payloads
from jobradar.detect import find_boards
from jobradar.filters import Matcher, required_years
from jobradar.models import Job
from jobradar.pipeline import run
from jobradar.report import write_all
from jobradar.sources import ashby, greenhouse, lever, smartrecruiters, workable
from jobradar.text import contains_term, html_to_text, parse_date

NOW = datetime(2026, 10, 12, 6, 0, tzinfo=timezone.utc)


def job(**kw):
    base = dict(source="greenhouse", company="Co", company_slug="co", job_id="1", title="Data Analyst",
                url="https://x.test/1", location="Bengaluru, India", posted=NOW - timedelta(days=1))
    base.update(kw)
    return Job(**base)


def search(**kw):
    s = copy.deepcopy(DEFAULTS["search"])
    s.update({"keywords": ["data analyst", "business analyst"], "min_score": 0})
    s.update(kw)
    return s


@pytest.fixture
def cfg(tmp_path):
    c = copy.deepcopy(DEFAULTS)
    c["search"].update({"keywords": ["business analyst", "data analyst", "product analyst",
                                     "supply chain analyst", "graduate engineer trainee", "design engineer"],
                        "locations": ["india"], "max_years_experience": 2, "min_score": 20})
    c["output"]["dir"] = str(tmp_path / "out")
    c["state"]["path"] = str(tmp_path / "state" / "seen.json")
    return c


# ── text helpers ────────────────────────────────────────────────────────────

def test_html_to_text_handles_greenhouse_double_escaping():
    raw = "&lt;p&gt;Hello &amp;amp; welcome&lt;/p&gt;&lt;ul&gt;&lt;li&gt;SQL&lt;/li&gt;&lt;/ul&gt;"
    assert html_to_text(raw) == "Hello & welcome\nSQL"


@pytest.mark.parametrize("value", ["2026-10-01T10:00:00Z", "2026-10-01T15:30:00+05:30", 1790848800000, "2026-10-01"])
def test_parse_date_formats(value):
    d = parse_date(value)
    assert d is not None and d.tzinfo is not None


def test_parse_date_bad_input():
    assert parse_date("not a date") is None and parse_date(None) is None


def test_contains_term_whole_words():
    assert contains_term("advanced sql skills", "SQL")
    assert not contains_term("nosql databases", "sql")
    assert contains_term("c++ developer", "c++")
    assert not contains_term("senior analyst", "sr")


# ── sources ─────────────────────────────────────────────────────────────────

def test_each_source_parses_demo_payload():
    p = payloads(NOW)
    _, gh = greenhouse.parse("orbitpay", p["greenhouse/orbitpay"])
    assert gh[0].company == "OrbitPay" and "SQL" in gh[0].description and "<" not in gh[0].description
    _, lv = lever.parse("kettle-foods", p["lever/kettle-foods"])
    assert lv[0].apply_url.endswith("/apply") and "Clear communication" in lv[0].description
    assert lv[0].remote is False
    _, ab = ashby.parse("northwind-labs", p["ashby/northwind-labs"])
    assert len(ab) == 2  # unlisted job skipped
    assert ab[1].remote is True and ab[0].remote is False
    assert ab[0].employment_type == "Full time"
    name, sr = smartrecruiters.parse("AcmeMotors", p["smartrecruiters/AcmeMotors"]["content"])
    assert name == "Acme Motors" and sr[0].seniority == "Entry Level"
    assert sr[0].url == "https://jobs.smartrecruiters.com/AcmeMotors/sr-1"
    name, wk = workable.parse("brightline-logistics", p["workable/brightline-logistics"])
    assert name == "Brightline Logistics" and wk[0].location == "Noida, Uttar Pradesh, India"


def test_lever_paginates():
    calls = []

    class H:
        def get_json(self, url, params):
            calls.append(params["skip"])
            n = 100 if params["skip"] < 200 else 7
            return [{"id": f"{params['skip']}-{i}", "text": "Analyst", "categories": {}} for i in range(n)]

    _, jobs = lever.fetch("acme", H())
    assert calls == [0, 100, 200] and len(jobs) == 207


def test_workable_dedupes_repeated_jobs():
    data = {"name": "X", "jobs": [{"title": "A", "shortcode": "S1"}, {"title": "A", "shortcode": "S1"}]}
    assert len(workable.parse("x", data)[1]) == 1


# ── experience parsing ──────────────────────────────────────────────────────

@pytest.mark.parametrize("text,years", [
    ("We need 3+ years of experience in SQL.", 3),
    ("0-2 years of experience.", 0),
    ("2 to 4 yrs in analytics", 2),
    ("At least 5 years in sales", 5),
    ("Minimum of 4 years working with clients", 4),
    ("3 years of hands-on experience", 3),
    ("3+ years in X and 5+ years in Y", 5),
    ("Founded 40 years ago, we love freshers.", None),
    ("No numbers here", None),
])
def test_required_years(text, years):
    assert required_years(job(description=text)) == years


def test_board_seniority_label_beats_text():
    assert required_years(job(seniority="Mid-Senior Level", description="0-1 years")) == 4


# ── filters ─────────────────────────────────────────────────────────────────

def test_title_keyword_required():
    m = Matcher(search(), now=NOW)
    assert not m.evaluate(job(title="Software Engineer"))
    assert m.drops == {"role keywords not matched": 1}


def test_description_matching_is_opt_in():
    j = job(title="Analyst I", description="You will work as a data analyst on our team.")
    assert not Matcher(search(), now=NOW).evaluate(j)
    assert Matcher(search(search_description=True), now=NOW).evaluate(j)


def test_excluded_titles_and_phrases():
    m = Matcher(search(), now=NOW)
    assert not m.evaluate(job(title="Senior Data Analyst"))
    assert not m.evaluate(job(title="Sr. Data Analyst"))
    assert not m.evaluate(job(description="Walk-in interview this Saturday"))
    assert m.evaluate(job(title="Data Analyst (Leadership team)")) is True  # 'lead' is a whole word only


def test_location_rules():
    s = search(locations=["india", "delhi"], exclude_locations=["us-remote"])
    m = Matcher(s, now=NOW)
    assert m.evaluate(job(location="New Delhi"))
    assert not m.evaluate(job(location="London, UK"))
    assert m.evaluate(job(location="Remote", remote=True))
    assert not m.evaluate(job(location="US-Remote", remote=True))
    assert not Matcher(search(locations=["india"], include_remote=False), now=NOW).evaluate(job(location="Remote"))
    assert m.evaluate(job(location="", remote=None))  # unknown location is kept


def test_experience_limit_and_unknown_policy():
    s = search(max_years_experience=2)
    assert not Matcher(s, now=NOW).evaluate(job(description="5+ years of experience"))
    assert Matcher(s, now=NOW).evaluate(job(description="1-2 years of experience"))
    assert Matcher(s, now=NOW).evaluate(job(description="Great team"))
    assert not Matcher(search(max_years_experience=2, unknown_experience="drop"), now=NOW).evaluate(
        job(description="Great team"))


def test_old_postings_dropped():
    assert not Matcher(search(max_age_days=30), now=NOW).evaluate(job(posted=NOW - timedelta(days=45)))


def test_scam_signals_flag_and_penalise():
    clean, shady = job(description="SQL role"), job(description="Pay a refundable deposit, message us on WhatsApp")
    Matcher(search(), now=NOW).evaluate(clean)
    Matcher(search(), now=NOW).evaluate(shady)
    assert len(shady.flags) == 2 and shady.score < clean.score


def test_fresher_and_skill_bonus_raise_score():
    a = job(title="Data Analyst", description="")
    b = job(title="Data Analyst - Graduate Program", description="sql, excel, python")
    s = search(skills=["sql", "excel", "python"])
    Matcher(s, now=NOW).evaluate(a)
    Matcher(s, now=NOW).evaluate(b)
    assert b.score > a.score


# ── pipeline + state ────────────────────────────────────────────────────────

def test_pipeline_end_to_end_and_new_marking(cfg):
    r1 = run(cfg, DEMO_COMPANIES, DemoHttp(NOW), now=NOW)
    titles = [j.title for j in r1.jobs]
    assert "Business Analyst - Graduate Program" in titles
    assert "Senior Business Analyst" not in titles
    assert all("London" not in j.location for j in r1.jobs)
    assert r1.first_run and all(j.is_new for j in r1.jobs)
    assert r1.jobs == sorted(r1.jobs, key=lambda j: j.score, reverse=True)

    later = NOW + timedelta(days=2)
    r2 = run(cfg, DEMO_COMPANIES, DemoHttp(NOW), now=later)
    assert not r2.first_run and not any(j.is_new for j in r2.jobs)


def test_one_broken_board_does_not_stop_the_run(cfg):
    r = run(cfg, DEMO_COMPANIES, DemoHttp(NOW, fail={"lever"}), now=NOW)
    broken = [b for b in r.boards if b.error]
    assert [b.source for b in broken] == ["lever"] and r.jobs


def test_llm_rerank_is_cached(cfg, monkeypatch):
    calls = []

    def fake_score(self, j):
        calls.append(j.uid)
        return 90, "good fit"

    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setattr("jobradar.llm.LLMScorer.score", fake_score)
    cfg["llm"].update({"enabled": True, "profile": "Fresh graduate", "max_jobs_per_run": 3})
    r1 = run(cfg, DEMO_COMPANIES, DemoHttp(NOW), now=NOW)
    assert len(calls) == 3 and sum(1 for j in r1.jobs if j.llm_score == 90) == 3
    r2 = run(cfg, DEMO_COMPANIES, DemoHttp(NOW), now=NOW + timedelta(hours=4))
    assert len(calls) == min(6, len(r1.jobs))      # second run only scores jobs not yet scored
    assert len(set(calls)) == len(calls)           # no job is ever sent twice
    assert all(j.llm_score == 90 for j in r2.jobs if j.uid in calls)


def test_llm_without_key_is_skipped_with_note(cfg, monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    cfg["llm"].update({"enabled": True, "profile": "x"})
    r = run(cfg, DEMO_COMPANIES, DemoHttp(NOW), now=NOW)
    assert any("LLM_API_KEY" in n for n in r.notes)


# ── report ──────────────────────────────────────────────────────────────────

def test_report_files_written(cfg):
    r = run(cfg, DEMO_COMPANIES, DemoHttp(NOW), now=NOW)
    path = write_all(r, cfg)
    data = json.loads(path.read_text())
    assert path.name == "jobs.json" and len(data["jobs"]) == len(r.jobs)
    assert data["meta"]["first_run"] is True and data["meta"]["boards_ok"] == 5
    assert set(data["jobs"][0]) >= {"uid", "title", "company", "score", "reasons", "flags", "is_new", "apply_url"}
    assert (path.parent / "jobs.csv").read_text().startswith("score,is_new,title")
    assert not (path.parent / "jobs.tmp").exists()


# ── detect + config ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("https://boards.greenhouse.io/stripe", ("greenhouse", "stripe")),
    ("https://job-boards.greenhouse.io/stripe/jobs/123", ("greenhouse", "stripe")),
    ('<script src="https://boards.greenhouse.io/embed/job_board/js?for=acme"></script>', ("greenhouse", "acme")),
    ("https://jobs.lever.co/palantir/abc-123", ("lever", "palantir")),
    ("https://jobs.ashbyhq.com/notion", ("ashby", "notion")),
    ("https://careers.smartrecruiters.com/Visa", ("smartrecruiters", "Visa")),
    ("https://apply.workable.com/acme-co/", ("workable", "acme-co")),
    ("https://acme.workable.com/", ("workable", "acme")),
])
def test_detect(text, expected):
    assert find_boards(text)[0] == expected


def test_detect_ignores_workable_job_links():
    assert find_boards("https://apply.workable.com/j/ABC123") == []


def test_config_validation(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("search:\n  keywords: []\n")
    with pytest.raises(ConfigError):
        load_config(p)
    p.write_text("search:\n  keywords: [analyst]\n")
    cfg = load_config(p)
    assert cfg["search"]["keywords"] == ["analyst"] and cfg["output"]["dir"] == "web/public/data"
    comp = tmp_path / "co.yaml"
    comp.write_text("greenhouse: [stripe, stripe, ' x/ ']\nlever: []\n")
    assert load_companies(comp) == {"greenhouse": ["stripe", "x"]}
    comp.write_text("workday: [x]\n")
    with pytest.raises(ConfigError):
        load_companies(comp)


def test_shipped_config_files_load():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    assert load_config(root / "config.yaml")["search"]["keywords"]
    assert load_companies(root / "companies.yaml")


# ── Step 5: Profiles, Tracks, Resumes & Eligibility Tests ────────────────────

from jobradar.config import load_profiles
from jobradar.filters import parse_batch_years, parse_cgpa_cutoff, check_branch_restriction, pick_resume
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def test_profiles_load_and_validation(tmp_path):
    prof = load_profiles(ROOT / "profiles.yaml")
    assert prof["candidate"]["graduation_year"] == 2027
    assert len(prof["tracks"]) == 3
    assert {t["id"] for t in prof["tracks"]} == {"software", "analyst", "supply_chain"}

    bad = tmp_path / "bad.yaml"
    bad.write_text("candidate: {}\ntracks:\n  - id: t1\n    # missing label\n    keywords: [x]\n    resumes: [{file: a.pdf}]\n")
    with pytest.raises(ConfigError):
        load_profiles(bad)

    bad2 = tmp_path / "bad2.yaml"
    bad2.write_text("candidate: {}\ntracks:\n  - id: t1\n    label: Track 1\n    keywords: []\n    resumes: [{file: a.pdf}]\n")
    with pytest.raises(ConfigError):
        load_profiles(bad2)


def test_track_and_resume_picking():
    prof = load_profiles(ROOT / "profiles.yaml")
    tracks = {t["id"]: t for t in prof["tracks"]}

    # Software track
    j1 = job(title="Frontend Developer", description="React, Next.js, TypeScript developer")
    assert pick_resume(tracks["software"], j1) == ("HIMANSHU_FINAL_TECH.pdf", "default for this track")

    j1_tredence = job(title="Frontend Developer", company="Tredence", description="React and TypeScript")
    assert pick_resume(tracks["software"], j1_tredence) == ("Tredence_New_Tech_1.pdf", "mentions tredence")

    # Analyst track
    j2_bank = job(title="Business Analyst - Retail Banking", company="HDFC", description="Banking analytics, SQL")
    assert pick_resume(tracks["analyst"], j2_bank) == ("icic_1.pdf", "mentions banking")

    j2_genai = job(title="Business Analyst - GenAI Practice", company="OrbitPay", description="LLM prompt and workflows")
    assert pick_resume(tracks["analyst"], j2_genai) == ("GEN_AI___NON_TECH_1.pdf", "mentions genai")

    j2_plain = job(title="Business Analyst", company="Acme", description="Excel and SQL")
    assert pick_resume(tracks["analyst"], j2_plain) == ("INTERN_ADDED_NON_TECH.pdf", "default for this track")

    # Supply Chain track
    j3_sc = job(title="Demand Planner", company="Kettle", description="Warehouse capacity planning")
    assert pick_resume(tracks["supply_chain"], j3_sc) == ("Supply_chain.pdf", "default for this track")


def test_multitrack_matching_and_track_scores(tmp_path):
    cfg_full = load_config(ROOT / "config.yaml", profiles_path=ROOT / "profiles.yaml")
    cfg_full["output"]["dir"] = str(tmp_path / "out")
    cfg_full["state"]["path"] = str(tmp_path / "state" / "seen.json")

    # Job that touches both Software and Analyst keywords
    # e.g. "Data Engineer" or "Analytics Engineer" or "Business Analyst" with React & SQL
    j = job(title="Analytics Engineer", company="Stripe", description="SQL, Python, React, data pipelines, cohort analytics")
    r = run(cfg_full, {"greenhouse": ["co"]}, None, now=NOW)
    # Direct test via pipeline rank
    from jobradar.pipeline import rank
    from jobradar.state import SeenStore
    store = SeenStore(cfg_full["state"]["path"])
    ranked, drops, notes = rank([j], cfg_full, store, now=NOW)
    assert len(ranked) == 1
    matched_job = ranked[0]
    assert matched_job.track in ("software", "analyst")
    # Both tracks scored and reported in track_scores
    assert len(matched_job.track_scores) >= 1
    assert matched_job.track_scores[matched_job.track] == matched_job.score


def test_batch_eligibility():
    s = search(candidate_grad_year=2027)
    m = Matcher(s, now=NOW)

    j_dropped = job(title="Data Analyst", description="open to 2025 and 2026 batch candidates only")
    assert not m.evaluate(j_dropped)
    assert m.last_drop_reason == "not open to the 2027 batch"

    j_bonus = job(title="Data Analyst", description="2026/2027 graduates welcome")
    assert m.evaluate(j_bonus)
    assert "open to 2027 batch" in j_bonus.reasons

    j_range = job(title="Data Analyst", description="2025-2027 batch eligible")
    assert m.evaluate(j_range)
    assert "open to 2027 batch" in j_range.reasons


def test_cgpa_cutoff_eligibility():
    s = search(candidate_cgpa=7.64)
    m = Matcher(s, now=NOW)

    j_high = job(title="Data Analyst", description="minimum CGPA 8.0 required")
    m.evaluate(j_high)
    assert any("asks for CGPA 8.0+ (resume shows 7.64)" in f for f in j_high.flags)

    j_ok = job(title="Data Analyst", description="CGPA 7 and above")
    m.evaluate(j_ok)
    assert not any("CGPA" in f for f in j_ok.flags)

    j_4point = job(title="Data Analyst", description="GPA 3.5/4 required")
    m.evaluate(j_4point)
    assert not any("CGPA" in f for f in j_4point.flags)


def test_branch_restriction_eligibility():
    s = search(track_id="software", keywords=["software engineer"])
    m = Matcher(s, now=NOW)

    j_cs = job(title="Software Engineer", description="B.Tech CSE/IT only")
    m.evaluate(j_cs)
    assert any("may require a CS/IT degree" in f for f in j_cs.flags)

    j_any = job(title="Software Engineer", description="B.Tech any branch")
    m.evaluate(j_any)
    assert not any("CS/IT degree" in f for f in j_any.flags)


def test_no_phone_or_email_in_jobs_json(tmp_path):
    import re
    cfg_full = load_config(ROOT / "config.yaml", profiles_path=ROOT / "profiles.yaml")
    cfg_full["output"]["dir"] = str(tmp_path / "out")
    cfg_full["state"]["path"] = str(tmp_path / "state" / "seen.json")
    r = run(cfg_full, DEMO_COMPANIES, DemoHttp(NOW), now=NOW)
    path = write_all(r, cfg_full)
    content = path.read_text(encoding="utf-8")

    # Email pattern
    emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", content)
    assert emails == [], f"Found emails in jobs.json: {emails}"

    # Phone pattern (10+ digits with optional country code)
    phone_numbers = re.findall(r"\b(?:\+91[\-\s]?)?[6-9]\d{9}\b", content)
    assert phone_numbers == [], f"Found phone numbers in jobs.json: {phone_numbers}"
