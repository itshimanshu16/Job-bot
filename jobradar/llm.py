"""Optional AI re-ranking through any OpenAI-compatible chat API (Gemini, OpenAI, Groq, Ollama...).

Only the top jobs by keyword score are sent, and each job is scored once (results are cached
in the state file), so a free API tier is plenty.
"""
from __future__ import annotations

import json
import os
import re

import requests

from .models import Job

PROMPT = """You screen job postings for one job seeker. Rate how well this job fits them and pick the best resume to submit.

ABOUT THE JOB SEEKER ({track_label}):
{profile}

RESUME OPTIONS:
{resumes}

JOB:
Title: {title}
Company: {company}
Location: {location}
Description (truncated):
{description}

Reply with JSON only, no other text:
{{"score": <0-100 integer, 100 = excellent fit and eligible>, "reason": "<one short sentence>", "resume": "<exact file name of one of the listed resume options>"}}"""

_JSON_RE = re.compile(r"\{.*\}", re.S)


class LLMScorer:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.api_key = os.environ.get(cfg.get("api_key_env", "LLM_API_KEY"), "").strip()
        self.url = cfg.get("base_url", "https://generativelanguage.googleapis.com/v1beta/openai").rstrip("/") + "/chat/completions"
        self.errors: list[str] = []

    @property
    def ready(self) -> bool:
        if not self.cfg.get("enabled"):
            return False
        if not self.api_key:
            self.errors.append(f"LLM enabled but environment variable {self.cfg.get('api_key_env', 'LLM_API_KEY')} is not set; skipped.")
            return False
        return True

    def score(self, job: Job, track: dict | None = None) -> tuple[int, str, str | None] | None:
        track = track or {}
        track_label = track.get("label", "General Track")
        profile = track.get("profile") or self.cfg.get("profile") or "Fresh graduate looking for entry-level roles."
        resume_items = track.get("resumes", [])
        if resume_items:
            resumes_text = "\n".join(f"- {r['file']}: {r.get('use_for', '')}" for r in resume_items)
        else:
            resumes_text = "(standard resume)"

        prompt = PROMPT.format(
            track_label=track_label,
            profile=profile.strip(),
            resumes=resumes_text.strip(),
            title=job.title,
            company=job.company,
            location=job.location or "not stated",
            description=(job.description or "(no description provided)")[:3500],
        )
        try:
            resp = requests.post(
                self.url,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.cfg.get("model", "gemini-3.8-flash"),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                },
                timeout=60,
            )
        except requests.RequestException as exc:
            self.errors.append(f"LLM request failed: {exc.__class__.__name__}")
            return None
        if resp.status_code != 200:
            self.errors.append(f"LLM API returned HTTP {resp.status_code}: {resp.text[:160]}")
            return None
        try:
            content = resp.json()["choices"][0]["message"]["content"]
            parsed = json.loads(_JSON_RE.search(content).group(0))
            value = max(0, min(100, int(parsed["score"])))
            reason = str(parsed.get("reason", ""))[:240]
            picked_resume = parsed.get("resume")
            valid_files = {r["file"] for r in resume_items}
            if picked_resume and str(picked_resume).strip() in valid_files:
                return value, reason, str(picked_resume).strip()
            return value, reason, None
        except (KeyError, IndexError, ValueError, TypeError, AttributeError):
            self.errors.append("LLM reply could not be parsed for one job; skipped it.")
            return None
