from __future__ import annotations

import time

import requests

USER_AGENT = "job-radar/1.0 (+https://github.com/; personal job alerts)"


class HttpError(Exception):
    def __init__(self, status: int | None, message: str):
        super().__init__(message)
        self.status = status


class Http:
    """Tiny JSON GET client with timeouts and polite retries."""

    def __init__(self, timeout: float = 25.0, retries: int = 2, backoff: float = 2.0):
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})

    def get_json(self, url: str, params: dict | None = None):
        last_err: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                last_err = HttpError(None, f"network error: {exc.__class__.__name__}")
            else:
                if resp.status_code == 200:
                    try:
                        return resp.json()
                    except ValueError:
                        raise HttpError(200, "response was not JSON")
                if resp.status_code in (404, 410):
                    raise HttpError(resp.status_code, "board not found (check the company slug)")
                if resp.status_code in (429, 500, 502, 503, 504):
                    last_err = HttpError(resp.status_code, f"HTTP {resp.status_code}")
                else:
                    raise HttpError(resp.status_code, f"HTTP {resp.status_code}")
            if attempt < self.retries:
                time.sleep(self.backoff * (attempt + 1))
        raise last_err or HttpError(None, "unknown error")

    def get_text(self, url: str) -> str:
        resp = self.session.get(url, timeout=self.timeout, headers={"Accept": "text/html,*/*"})
        resp.raise_for_status()
        return resp.text
