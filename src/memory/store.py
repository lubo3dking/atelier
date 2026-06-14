"""JSON-file-backed memory of past runs.

Lightweight, zero-dependency default: each completed run appends a small record,
and the Planner is given a digest of recent runs (via the shared `context_for`)
so it can learn from prior outcomes.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .base import BaseMemory


class MemoryStore(BaseMemory):
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _save(self, records: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(records, indent=2), encoding="utf-8")

    def add(self, record: dict[str, Any]) -> None:
        records = self._load()
        record = {"timestamp": datetime.now(timezone.utc).isoformat(), **record}
        records.append(record)
        self._save(records)

    def recent(self, n: int = 5) -> list[dict[str, Any]]:
        return self._load()[-n:]
