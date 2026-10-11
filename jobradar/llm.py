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

PROMPT = """You screen job postings for one job seeker. Rate how well this job fits them.

ABOUT THE JOB SEEKER:
{profile}

JOB:
Title: {title}
Company: {company}
Location: {location}
Description (truncated):
{description}

Reply with JSON only, no other text:
{{"score": <0-100 integer, 100 = excellent fit and eligible>, "reason": "<one short sentence>"}}"""

_JSON_RE = re.compile(r"\{.*\}", re.S)


class LLMScorer:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.api_key = os.environ.get(cfg["api_key_env"], "").strip()
        self.url = cfg["base_url"].rstrip("/") + "/chat/completions"
        self.errors: list[str] = []

    @property
    def ready(self) -> bool:
        if not self.cfg.get("enabled"):
            return False
        if not self.api_key:
            self.errors.append(f"LLM enabled but environment variable {self.cfg['api_key_env']} is not set; skipped.")
            return False
        if not (self.cfg.get("profile") or "").strip():
            self.errors.append("LLM enabled but llm.profile is empty; skipped.")
            return False
        return True

    def score(self, job: Job) -> tuple[int, str] | None:
        prompt = PROMPT.format(
            profile=self.cfg["profile"].strip(),
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
                    "model": self.cfg["model"],
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
            return value, str(parsed.get("reason", ""))[:240]
        except (KeyError, IndexError, ValueError, TypeError, AttributeError):
            self.errors.append("LLM reply could not be parsed for one job; skipped it.")
            return None
