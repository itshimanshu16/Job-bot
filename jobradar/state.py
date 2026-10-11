"""Remembers which jobs were already seen, so each run can highlight what's new."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


class SeenStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.data: dict[str, dict] = {}
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8")) or {}
            except (ValueError, OSError):
                self.data = {}  # a corrupt file just means everything looks new once

    def touch(self, uid: str, now: datetime) -> str:
        """Mark a job as seen now; return when it was first seen (ISO)."""
        iso = now.isoformat(timespec="seconds")
        entry = self.data.setdefault(uid, {"first_seen": iso})
        entry["last_seen"] = iso
        return entry["first_seen"]

    def llm_cache(self, uid: str) -> dict | None:
        return (self.data.get(uid) or {}).get("llm")

    def set_llm(self, uid: str, score: int, reason: str) -> None:
        self.data.setdefault(uid, {})["llm"] = {"score": score, "reason": reason}

    def prune(self, now: datetime, days: int) -> int:
        cutoff = now - timedelta(days=days)
        stale = []
        for uid, e in self.data.items():
            try:
                last = datetime.fromisoformat(e.get("last_seen") or e.get("first_seen"))
            except (TypeError, ValueError):
                stale.append(uid)
                continue
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if last < cutoff:
                stale.append(uid)
        for uid in stale:
            del self.data[uid]
        return len(stale)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=1, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)
