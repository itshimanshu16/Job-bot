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


def load_profiles(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"profiles file not found: {p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    candidate = raw.get("candidate")
    if not candidate or not isinstance(candidate, dict):
        raise ConfigError(f"{p.name}: missing or invalid 'candidate' section")

    tracks = raw.get("tracks")
    if not tracks or not isinstance(tracks, list):
        raise ConfigError(f"{p.name}: missing or invalid 'tracks' section")

    clean_tracks: list[dict] = []
    for idx, t in enumerate(tracks):
        if not isinstance(t, dict):
            raise ConfigError(f"{p.name}: track #{idx+1} is not a mapping")
        for req in ("id", "label"):
            if not t.get(req):
                raise ConfigError(f"{p.name}: track #{idx+1} missing required field '{req}'")
        keywords = [str(k).strip() for k in (t.get("keywords") or []) if str(k).strip()]
        if not keywords:
            raise ConfigError(f"{p.name}: track '{t.get('id')}' must have at least one keyword")

        raw_resumes = t.get("resumes")
        if not raw_resumes or not isinstance(raw_resumes, list):
            raise ConfigError(f"{p.name}: track '{t.get('id')}' must have at least one resume")

        defaults = [r for r in raw_resumes if r.get("default") is True]
        if len(defaults) > 1:
            raise ConfigError(f"{p.name}: track '{t.get('id')}' has multiple default resumes")
        if len(defaults) == 0:
            raw_resumes[0]["default"] = True

        clean_resumes: list[dict] = []
        for r in raw_resumes:
            if not r.get("file"):
                raise ConfigError(f"{p.name}: track '{t.get('id')}' has a resume without 'file'")
            clean_resumes.append({
                "file": str(r["file"]).strip(),
                "use_for": str(r.get("use_for", "")).strip(),
                "prefer_when": [str(x).strip() for x in (r.get("prefer_when") or []) if str(x).strip()],
                "default": bool(r.get("default", False)),
            })

        clean_tracks.append({
            "id": str(t["id"]).strip(),
            "label": str(t["label"]).strip(),
            "keywords": keywords,
            "skills": [str(s).strip() for s in (t.get("skills") or []) if str(s).strip()],
            "profile": str(t.get("profile", "")).strip(),
            "resumes": clean_resumes,
        })

    return {
        "candidate": candidate,
        "tracks": clean_tracks,
    }


def load_config(path: str | Path, profiles_path: str | Path | None = None) -> dict:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"config file not found: {p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    cfg = _merge(DEFAULTS, raw)

    # Check for profiles
    prof_path: Path | None = None
    if profiles_path:
        prof_path = Path(profiles_path)
    else:
        candidate_prof = p.parent / "profiles.yaml"
        if candidate_prof.exists():
            prof_path = candidate_prof

    if prof_path and prof_path.exists():
        prof_data = load_profiles(prof_path)
        cfg["candidate"] = prof_data["candidate"]
        cfg["tracks"] = prof_data["tracks"]
        all_keywords = []
        all_skills = []
        for t in cfg["tracks"]:
            for k in t["keywords"]:
                if k not in all_keywords:
                    all_keywords.append(k)
            for sk in t["skills"]:
                if sk not in all_skills:
                    all_skills.append(sk)
        if not cfg["search"].get("keywords"):
            cfg["search"]["keywords"] = all_keywords
        if not cfg["search"].get("skills"):
            cfg["search"]["skills"] = all_skills
        if "locations" in cfg["candidate"] and not cfg["search"].get("locations"):
            cfg["search"]["locations"] = [str(x) for x in cfg["candidate"]["locations"]]
        if "max_years_experience" in cfg["candidate"] and cfg["search"].get("max_years_experience") is None:
            cfg["search"]["max_years_experience"] = cfg["candidate"]["max_years_experience"]
        if "include_remote" in cfg["candidate"]:
            cfg["search"]["include_remote"] = cfg["candidate"]["include_remote"]

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
