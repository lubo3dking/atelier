"""Shared offline test fixtures.

The whole system talks to Claude only through `LLMClient`, so tests inject a
scripted stand-in with the same `.create` / `.parse` interface. No API key, no
network — the loop logic, tools, and memory are all exercised deterministically.
"""
from __future__ import annotations

import types

import pytest

from src.schemas import DesignBrief, Plan, ReviewVerdict


def text_block(text: str):
    return types.SimpleNamespace(type="text", text=text)


def tool_use_block(block_id: str, name: str, tool_input: dict):
    return types.SimpleNamespace(type="tool_use", id=block_id, name=name, input=tool_input)


def message(content: list, stop_reason: str = "end_turn"):
    return types.SimpleNamespace(content=content, stop_reason=stop_reason)


class ScriptedLLM:
    """Stand-in for `LLMClient` driven by pre-scripted responses.

    - `parse` returns `plan` for the Plan schema and pops `verdicts` for the
      ReviewVerdict schema.
    - `create` pops the next queued `create_responses` entry.
    Call records are kept for assertions.
    """

    def __init__(
        self,
        *,
        plan: Plan | None = None,
        create_responses=None,
        verdicts=None,
        design_brief: DesignBrief | None = None,
    ):
        self.plan = plan
        self._create_responses = list(create_responses or [])
        self._verdicts = list(verdicts or [])
        self.design_brief = design_brief
        self.create_calls: list[dict] = []
        self.parse_calls: list[dict] = []

    def create(self, *, system, messages, tools=None, max_tokens=None):
        self.create_calls.append({"system": system, "messages": messages, "tools": tools})
        return self._create_responses.pop(0)

    def parse(self, *, system, messages, schema, max_tokens=None, json_mode=False):
        self.parse_calls.append(
            {"system": system, "messages": messages, "schema": schema, "json_mode": json_mode}
        )
        if schema is Plan:
            assert self.plan is not None, "ScriptedLLM.parse(Plan) with no plan set"
            return self.plan
        if schema is ReviewVerdict:
            return self._verdicts.pop(0)
        if schema is DesignBrief:
            assert self.design_brief is not None, "ScriptedLLM.parse(DesignBrief) with no brief set"
            return self.design_brief
        raise AssertionError(f"Unexpected parse schema: {schema!r}")


@pytest.fixture
def scripted_llm():
    return ScriptedLLM
