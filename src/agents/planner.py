"""Planner agent — turns a goal into an ordered, concrete plan."""
from __future__ import annotations

from ..schemas import Plan
from .base import Agent


class Planner(Agent):
    def plan(self, goal: str, memory_context: str = "") -> Plan:
        user = f"Goal:\n{goal}"
        if memory_context:
            user += f"\n\nContext from prior runs:\n{memory_context}"
        return self.client.parse(
            system=self.system_prompt,
            messages=[{"role": "user", "content": user}],
            schema=Plan,
        )
