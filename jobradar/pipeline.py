from __future__ import annotations

import copy
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .filters import Matcher, pick_resume
from .llm import LLMScorer
from .models import Job
from .sources import SOURCES
from .state import SeenStore

log = logging.getLogger("jobradar")

DROP_ORDER = [
    "below min_score",
    "asks for more experience than max_years_experience",
    "not open to the 2027 batch",
    "location not wanted",
    "older than max_age_days",
    "excluded title word (e.g. senior/manager)",
    "excluded phrase in description",
    "experience not stated",
    "role keywords not matched",
]


@dataclass
class BoardResult:
    source: str
    slug: str
    company: str = ""
    count: int = 0
    error: str = ""


@dataclass
class RunResult:
    jobs: list[Job]
    boards: list[BoardResult]
    total_fetched: int
    drops: dict[str, int]
    notes: list[str] = field(default_factory=list)
    started: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    first_run: bool = False


def fetch_all(companies: dict[str, list[str]], http, concurrency: int = 8) -> tuple[list[Job], list[BoardResult]]:
    tasks = [(src, slug) for src, slugs in companies.items() for slug in slugs]
    jobs: list[Job] = []
    boards: list[BoardResult] = []

    def work(src: str, slug: str):
        return SOURCES[src].fetch(slug, http)

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futures = {pool.submit(work, src, slug): (src, slug) for src, slug in tasks}
        for fut in as_completed(futures):
            src, slug = futures[fut]
            br = BoardResult(src, slug)
            try:
                company, found = fut.result()
                br.company, br.count = company, len(found)
                jobs.extend(found)
            except Exception as exc:  # one bad board must never stop the run
                br.error = str(exc) or exc.__class__.__name__
                log.warning("%s/%s failed: %s", src, slug, br.error)
            boards.append(br)
    boards.sort(key=lambda b: (b.source, b.slug))
    return jobs, boards


def _best_drop_reason(reasons: list[str]) -> str:
    if not reasons:
        return "role keywords not matched"
    for expected in DROP_ORDER:
        if expected in reasons:
            return expected
    return reasons[0]


def rank(jobs: list[Job], cfg: dict, store: SeenStore, now: datetime) -> tuple[list[Job], dict, list[str]]:
    unique: dict[str, Job] = {}
    for j in jobs:
        unique.setdefault(j.uid, j)

    tracks = cfg.get("tracks", [])
    candidate = cfg.get("candidate", {})
    tracks_by_id = {t["id"]: t for t in tracks}
    drops: dict[str, int] = {}
    kept: list[Job] = []

    if tracks:
        for j in unique.values():
            attempts: list[dict] = []
            drop_reasons: list[str] = []
            track_scores: dict[str, int] = {}

            for track in tracks:
                t_search = dict(cfg.get("search", {}))
                t_search["keywords"] = track["keywords"]
                t_search["skills"] = track.get("skills", [])
                if "locations" in candidate:
                    t_search["locations"] = candidate["locations"]
                if "max_years_experience" in candidate:
                    t_search["max_years_experience"] = candidate["max_years_experience"]
                if "include_remote" in candidate:
                    t_search["include_remote"] = candidate["include_remote"]
                t_search["candidate_grad_year"] = candidate.get("graduation_year", 2027)
                t_search["candidate_cgpa"] = candidate.get("cgpa", 7.64)
                t_search["track_id"] = track["id"]

                test_j = copy.copy(j)
                matcher = Matcher(t_search, now=now)
                passed = matcher.evaluate(test_j)
                if passed:
                    track_scores[track["id"]] = test_j.score
                    attempts.append({
                        "track": track,
                        "score": test_j.score,
                        "reasons": test_j.reasons,
                        "flags": test_j.flags,
                        "min_years": test_j.min_years,
                    })
                else:
                    drop_reasons.append(matcher.last_drop_reason or "role keywords not matched")

            if attempts:
                # Keep track with highest score. In Python, max with stable key keeps earlier track on tie.
                best = max(attempts, key=lambda a: a["score"])
                win_track = best["track"]
                j.score = best["score"]
                j.reasons = best["reasons"]
                j.flags = best["flags"]
                j.min_years = best["min_years"]
                j.track = win_track["id"]
                j.track_label = win_track["label"]
                j.track_scores = track_scores
                j.resume, j.resume_reason = pick_resume(win_track, j)
                kept.append(j)
            else:
                reason = _best_drop_reason(drop_reasons)
                drops[reason] = drops.get(reason, 0) + 1
    else:
        matcher = Matcher(cfg["search"], now=now)
        kept = [j for j in unique.values() if matcher.evaluate(j)]
        drops = matcher.drops

    window = timedelta(hours=cfg["output"]["new_window_hours"])
    for j in kept:
        j.first_seen = store.touch(j.uid, now)
        try:
            j.is_new = now - datetime.fromisoformat(j.first_seen) <= window
        except ValueError:
            j.is_new = False

    notes: list[str] = []
    llm_cfg = cfg.get("llm", {})
    scorer = LLMScorer(llm_cfg)
    if scorer.ready:
        kept.sort(key=lambda j: j.score, reverse=True)
        budget = int(llm_cfg.get("max_jobs_per_run", 40))
        max_failures = int(llm_cfg.get("max_failures", 5))
        failures = 0
        for j in kept:
            cached = store.llm_cache(j.uid, track_id=j.track)
            if cached:
                j.llm_score, j.llm_reason = cached["score"], cached["reason"]
                if cached.get("resume"):
                    j.resume = cached["resume"]
                    j.resume_reason = f"AI pick: {cached['reason']}"
                continue
            if budget <= 0 or failures >= max_failures:
                continue
            budget -= 1
            cur_track = tracks_by_id.get(j.track)
            try:
                res = scorer.score(j, track=cur_track)
            except TypeError:
                res = scorer.score(j)
            if res is None:
                failures += 1
                continue
            if len(res) == 3:
                sc_val, reason_str, ai_res = res
            else:
                sc_val, reason_str = res[0], res[1]
                ai_res = None
            j.llm_score = sc_val
            j.llm_reason = reason_str
            if ai_res:
                j.resume = ai_res
                j.resume_reason = f"AI pick: {reason_str}"
            store.set_llm(j.uid, sc_val, reason_str, resume=ai_res or "", track_id=j.track)
        w = float(llm_cfg.get("weight", 0.5))
        for j in kept:
            if j.llm_score is not None:
                j.score = round((1 - w) * j.score + w * j.llm_score)
    for msg in dict.fromkeys(scorer.errors):  # de-duplicated, order kept
        notes.append(msg)

    far_past = datetime(1970, 1, 1, tzinfo=timezone.utc)
    kept.sort(key=lambda j: (j.score, j.posted or far_past), reverse=True)
    return kept[: cfg["output"]["max_jobs"]], drops, notes


def run(cfg: dict, companies: dict[str, list[str]], http, now: datetime | None = None) -> RunResult:
    now = now or datetime.now(timezone.utc)
    store = SeenStore(cfg["state"]["path"])
    first_run = not store.data
    raw, boards = fetch_all(companies, http, cfg["fetch"]["concurrency"])
    ranked, drops, notes = rank(raw, cfg, store, now)
    store.prune(now, cfg["state"]["forget_after_days"])
    store.save()
    return RunResult(jobs=ranked, boards=boards, total_fetched=len(raw), drops=drops, notes=notes, started=now,
                      first_run=first_run)
