"""Memory backend interface.

A memory backend records completed runs and exposes a digest of recent ones to
the Planner. Concrete backends implement only `add` and `recent`; the
Planner-facing `context_for` digest is defined once here and shared by all
backends.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseMemory(ABC):
    @abstractmethod
    def add(self, record: dict[str, Any]) -> None:
        """Persist one run record."""

    @abstractmethod
    def recent(self, n: int = 5) -> list[dict[str, Any]]:
        """Return up to the n most recent records, oldest first."""

    def context_for(self, goal: str, n: int = 5) -> str:
        """A short natural-language digest of recent runs for the Planner."""
        records = self.recent(n)
        if not records:
            return "No prior runs recorded."
        lines = ["Recent runs (most recent last):"]
        for r in records:
            status = "approved" if r.get("approved") else "not approved"
            lines.append(
                f"- goal={r.get('goal', '?')!r} -> {status}"
                f" (score={r.get('score', '?')}, attempts={r.get('attempts', '?')})"
            )
        return "\n".join(lines)
