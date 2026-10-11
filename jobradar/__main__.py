"""Command line:

  python -m jobradar run                 fetch, filter, rank and write web/public/data/jobs.json
  python -m jobradar check               test every board in companies.yaml and show job counts
  python -m jobradar detect <url> [...]  find the board type + slug from a company's careers page
  python -m jobradar demo                write sample data from made-up companies (no internet needed)
"""
from __future__ import annotations

import argparse
import copy
import logging
import sys
import tempfile
from pathlib import Path

from . import __version__
from .config import ConfigError, load_companies, load_config
from .detect import detect
from .http import Http
from .pipeline import run
from .report import write_all
from .sources import SOURCES


def _summary(result, path: Path) -> None:
    new = sum(1 for j in result.jobs if j.is_new)
    failed = [b for b in result.boards if b.error]
    print(f"Fetched {result.total_fetched} open jobs from {len(result.boards) - len(failed)} boards.")
    print(f"{len(result.jobs)} match your search, {new} of them new.")
    for b in failed:
        print(f"  ! {b.source}/{b.slug}: {b.error}")
    for n in result.notes:
        print(f"  note: {n}")
    print(f"Saved: {path}")


def cmd_run(args) -> int:
    cfg = load_config(args.config)
    if args.out:
        cfg["output"]["dir"] = args.out
    companies = load_companies(args.companies)
    http = Http(timeout=cfg["fetch"]["timeout_seconds"])
    result = run(cfg, companies, http)
    path = write_all(result, cfg)
    _summary(result, path)
    ok = any(not b.error for b in result.boards)
    return 0 if ok else 2


def cmd_check(args) -> int:
    companies = load_companies(args.companies)
    http = Http(timeout=20, retries=1)
    bad = 0
    for source, slugs in companies.items():
        for slug in slugs:
            try:
                name, jobs = SOURCES[source].fetch(slug, http)
                print(f"  ok   {source:<16}{slug:<28}{len(jobs):>5} jobs  ({name})")
            except Exception as exc:
                bad += 1
                print(f"  FAIL {source:<16}{slug:<28}{exc}")
    print(f"\n{bad} board(s) failed." if bad else "\nAll boards reachable.")
    return 1 if bad else 0


def cmd_detect(args) -> int:
    http = Http(timeout=20, retries=0)
    rc = 0
    for url in args.urls:
        hits = detect(url, http)
        if not hits:
            rc = 1
            print(f"{url}\n  no supported job board found (it may use Workday, SuccessFactors or its own site)")
            continue
        print(url)
        for source, slug in hits:
            print(f"  {source}: {slug}      -> add under '{source}:' in companies.yaml")
    return rc


def cmd_demo(args) -> int:
    from .config import DEFAULTS
    from .demo import DEMO_COMPANIES, DemoHttp

    cfg = copy.deepcopy(DEFAULTS)
    cfg["search"].update({
        "keywords": ["business analyst", "data analyst", "product analyst", "supply chain analyst",
                     "graduate engineer trainee", "design engineer", "founder's office"],
        "skills": ["sql", "excel", "python", "power bi", "cad"],
        "locations": ["india", "bengaluru", "gurugram", "pune", "chennai", "noida", "delhi"],
        "max_years_experience": 2,
        "min_score": 20,
    })
    cfg["output"]["dir"] = args.out
    cfg["output"]["title"] = "Job Radar (demo)"
    cfg["state"]["path"] = str(Path(tempfile.mkdtemp()) / "seen.json")
    result = run(cfg, DEMO_COMPANIES, DemoHttp())
    result.notes.insert(0, "Demo data: these companies and jobs are made up, to show what the report looks like.")
    path = write_all(result, cfg)
    _summary(result, path)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jobradar", description="Fresh jobs from public company job boards.")
    parser.add_argument("--version", action="version", version=f"jobradar {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="fetch, filter and write the report")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--companies", default="companies.yaml")
    p.add_argument("--out", help="output folder (default: output.dir in config)")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("check", help="test that every board in companies.yaml works")
    p.add_argument("--companies", default="companies.yaml")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("detect", help="find the job board behind a careers page URL")
    p.add_argument("urls", nargs="+")
    p.set_defaults(func=cmd_detect)

    p = sub.add_parser("demo", help="write sample data from made-up companies")
    p.add_argument("--out", default="web/public/data")
    p.set_defaults(func=cmd_demo)

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"Config problem: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
