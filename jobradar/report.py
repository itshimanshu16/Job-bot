"""Writes the results the React app reads: jobs.json (plus jobs.csv for spreadsheets)."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from .pipeline import RunResult

CSV_FIELDS = ["score", "is_new", "title", "company", "location", "remote", "posted", "min_years",
              "source", "url", "apply_url", "reasons", "flags", "llm_reason"]


def build_payload(result: RunResult, cfg: dict) -> dict:
    meta = {
        "title": cfg["output"]["title"],
        "generated": result.started.isoformat(timespec="seconds"),
        "first_run": result.first_run,
        "total_fetched": result.total_fetched,
        "boards_ok": sum(1 for b in result.boards if not b.error),
        "boards": [b.__dict__ for b in result.boards],
        "drops": result.drops,
        "notes": result.notes,
        "keywords": cfg["search"]["keywords"],
    }
    return {"meta": meta, "jobs": [j.to_dict() for j in result.jobs]}


def write_all(result: RunResult, cfg: dict) -> Path:
    out = Path(cfg["output"]["dir"])
    out.mkdir(parents=True, exist_ok=True)
    payload = build_payload(result, cfg)
    path = out / "jobs.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)  # the app never sees a half-written file

    with (out / "jobs.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in payload["jobs"]:
            r = dict(r)
            r["reasons"] = "; ".join(r["reasons"])
            r["flags"] = "; ".join(r["flags"])
            w.writerow(r)
    return path
