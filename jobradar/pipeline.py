from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .filters import Matcher
from .llm import LLMScorer
from .models import Job
from .sources import SOURCES
from .state import SeenStore

log = logging.getLogger("jobradar")


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


def rank(jobs: list[Job], cfg: dict, store: SeenStore, now: datetime) -> tuple[list[Job], dict, list[str]]:
    matcher = Matcher(cfg["search"], now=now)
    unique: dict[str, Job] = {}
    for j in jobs:
        unique.setdefault(j.uid, j)

    kept = [j for j in unique.values() if matcher.evaluate(j)]

    window = timedelta(hours=cfg["output"]["new_window_hours"])
    for j in kept:
        j.first_seen = store.touch(j.uid, now)
        try:
            j.is_new = now - datetime.fromisoformat(j.first_seen) <= window
        except ValueError:
            j.is_new = False

    notes: list[str] = []
    llm_cfg = cfg["llm"]
    scorer = LLMScorer(llm_cfg)
    if scorer.ready:
        kept.sort(key=lambda j: j.score, reverse=True)
        budget = int(llm_cfg["max_jobs_per_run"])
        failures = 0
        for j in kept:
            cached = store.llm_cache(j.uid)
            if cached:
                j.llm_score, j.llm_reason = cached["score"], cached["reason"]
                continue
            if budget <= 0 or failures >= 3:
                continue
            budget -= 1
            result = scorer.score(j)
            if result is None:
                failures += 1
                continue
            j.llm_score, j.llm_reason = result
            store.set_llm(j.uid, *result)
        w = float(llm_cfg["weight"])
        for j in kept:
            if j.llm_score is not None:
                j.score = round((1 - w) * j.score + w * j.llm_score)
    for msg in dict.fromkeys(scorer.errors):  # de-duplicated, order kept
        notes.append(msg)

    far_past = datetime(1970, 1, 1, tzinfo=timezone.utc)
    kept.sort(key=lambda j: (j.score, j.posted or far_past), reverse=True)
    return kept[: cfg["output"]["max_jobs"]], matcher.drops, notes


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
