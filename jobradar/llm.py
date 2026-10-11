"""Optional AI re-ranking through any OpenAI-compatible chat API (Gemini, OpenAI, Groq, Ollama...).

Only the top jobs by keyword score are sent, and each job is scored once (results are cached
in the state file), so a free API tier is plenty.
Includes automatic retries with exponential backoff and multi-model fallback cascade
to handle high-demand spikes (HTTP 503), rate limits (HTTP 429), and network timeouts.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time

import requests

from .models import Job

log = logging.getLogger("jobradar")

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

DEFAULT_FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-flash-latest",
    "gemini-2.5-pro",
]


class LLMScorer:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.api_key = os.environ.get(cfg.get("api_key_env", "LLM_API_KEY"), "").strip()
        self.url = cfg.get("base_url", "https://generativelanguage.googleapis.com/v1beta/openai").rstrip("/") + "/chat/completions"
        self.errors: list[str] = []
        self.active_model: str = str(cfg.get("model") or "gemini-2.5-flash").strip()

    @property
    def ready(self) -> bool:
        if not self.cfg.get("enabled"):
            return False
        if not self.api_key:
            self.errors.append(f"LLM enabled but environment variable {self.cfg.get('api_key_env', 'LLM_API_KEY')} is not set; skipped.")
            return False
        return True

    def _record_error(self, msg: str) -> None:
        if msg not in self.errors and len(self.errors) < 8:
            self.errors.append(msg)

    def _get_candidate_models(self) -> list[str]:
        configured_primary = str(self.cfg.get("model") or "gemini-2.5-flash").strip()
        configured_fallbacks = [
            str(m).strip() for m in self.cfg.get("fallback_models") or DEFAULT_FALLBACK_MODELS if str(m).strip()
        ]
        models: list[str] = []
        if self.active_model and self.active_model not in models:
            models.append(self.active_model)
        if configured_primary and configured_primary not in models:
            models.append(configured_primary)
        for m in configured_fallbacks:
            if m not in models:
                models.append(m)
        return models

    def _try_model(self, model: str, prompt: str) -> tuple[int, str, str | None] | None:
        retries = max(1, int(self.cfg.get("max_retries", 2)))
        timeout = max(5.0, float(self.cfg.get("timeout_seconds", 25.0)))

        for attempt in range(retries):
            try:
                resp = requests.post(
                    self.url,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0,
                    },
                    timeout=timeout,
                )
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                err_type = exc.__class__.__name__
                if attempt < retries - 1:
                    log.warning("LLM model %s timed out (%s), retrying (attempt %d/%d)...", model, err_type, attempt + 1, retries)
                    time.sleep(1.5 * (attempt + 1))
                    continue
                self._record_error(f"LLM model '{model}' failed: {err_type}")
                return None
            except requests.RequestException as exc:
                self._record_error(f"LLM request error with '{model}': {exc.__class__.__name__}")
                return None

            if resp.status_code == 200:
                try:
                    content = resp.json()["choices"][0]["message"]["content"]
                    match = _JSON_RE.search(content)
                    if not match:
                        self._record_error(f"LLM reply from '{model}' contained no JSON block.")
                        return None
                    parsed = json.loads(match.group(0))
                    value = max(0, min(100, int(parsed["score"])))
                    reason = str(parsed.get("reason", ""))[:240]
                    picked_resume = parsed.get("resume")
                    return value, reason, picked_resume
                except (KeyError, IndexError, ValueError, TypeError, AttributeError) as exc:
                    self._record_error(f"LLM reply from '{model}' could not be parsed: {exc}")
                    return None

            # Handle transient high-demand spikes (503), rate limits (429), or gateway hiccups (500/502/504)
            if resp.status_code in (429, 500, 502, 503, 504):
                if attempt < retries - 1:
                    log.warning("LLM model %s returned HTTP %d, retrying with backoff...", model, resp.status_code)
                    time.sleep(2.0 * (attempt + 1))
                    continue
                self._record_error(f"LLM model '{model}' temporarily unavailable (HTTP {resp.status_code})")
                return None

            # Non-retryable error (e.g. 400 Bad Request, 404 Model Not Found)
            self._record_error(f"LLM model '{model}' returned HTTP {resp.status_code}: {resp.text[:120]}")
            return None

        return None

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

        candidates = self._get_candidate_models()
        valid_files = {r["file"] for r in resume_items}

        for idx, model in enumerate(candidates):
            result = self._try_model(model, prompt)
            if result is not None:
                value, reason, picked_resume = result
                # If a fallback succeeded, latch onto it to avoid failing on subsequent jobs
                if model != self.active_model:
                    log.info("Switched active LLM model to working fallback: %s", model)
                    self.active_model = model

                if picked_resume and str(picked_resume).strip() in valid_files:
                    return value, reason, str(picked_resume).strip()
                return value, reason, None

            if idx < len(candidates) - 1:
                next_model = candidates[idx + 1]
                log.warning("LLM model '%s' failed, falling back to '%s'", model, next_model)

        return None
