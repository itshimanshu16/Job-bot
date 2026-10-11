from __future__ import annotations

import copy
from pathlib import Path

import yaml

DEFAULTS: dict = {
    "search": {
        "keywords": [],
        "search_description": False,
        "skills": [],
        "exclude_title": ["senior", "sr", "sr.", "lead", "principal", "staff", "manager", "director",
                          "head of", "vp", "vice president", "chief"],
        "exclude_text": ["walk-in", "walk in interview", "walk-in drive"],
        "locations": [],
        "exclude_locations": [],
        "include_remote": True,
        "max_years_experience": None,
        "unknown_experience": "keep",
        "max_age_days": 30,
        "fresher_terms": ["fresher", "freshers", "new grad", "new graduate", "recent graduate",
                          "graduate trainee", "graduate engineer trainee", "graduate program",
                          "entry level", "entry-level", "early career", "early talent", "campus",
                          "trainee", "junior", "apprentice", "0-1 years", "0-2 years",
                          "0 to 2 years", "2026 batch", "2027 batch"],
        "min_score": 30,
    },
    "output": {
        "dir": "web/public/data",
        "max_jobs": 400,
        "new_window_hours": 24,
        "title": "Job Radar",
    },
    "fetch": {
        "concurrency": 8,
        "timeout_seconds": 25,
    },
    "llm": {
        "enabled": False,
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-flash-latest",
        "api_key_env": "LLM_API_KEY",
        "max_jobs_per_run": 40,
        "weight": 0.5,
        "profile": "",
    },
    "state": {
        "path": "state/seen.json",
        "forget_after_days": 45,
    },
}


class ConfigError(ValueError):
    pass


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"config file not found: {p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    cfg = _merge(DEFAULTS, raw)
    s = cfg["search"]
    for key in ("keywords", "skills", "exclude_title", "exclude_text", "locations",
                "exclude_locations", "fresher_terms"):
        s[key] = [str(x) for x in (s.get(key) or []) if str(x).strip()]
    if not s["keywords"]:
        raise ConfigError("search.keywords is empty. Add at least one role keyword, e.g. 'data analyst'.")
    if s["unknown_experience"] not in ("keep", "drop"):
        raise ConfigError("search.unknown_experience must be 'keep' or 'drop'")
    return cfg


def load_companies(path: str | Path) -> dict[str, list[str]]:
    from .sources import SOURCES

    p = Path(path)
    if not p.exists():
        raise ConfigError(f"companies file not found: {p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    unknown = set(raw) - set(SOURCES)
    if unknown:
        raise ConfigError(f"unknown board type(s) in {p.name}: {', '.join(sorted(unknown))}. "
                          f"Use: {', '.join(SOURCES)}")
    out: dict[str, list[str]] = {}
    for source, slugs in raw.items():
        clean = []
        for s in slugs or []:
            s = str(s).strip().strip("/")
            if s and s not in clean:
                clean.append(s)
        if clean:
            out[source] = clean
    if not out:
        raise ConfigError(f"{p.name} lists no companies.")
    return out
