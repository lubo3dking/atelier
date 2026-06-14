"""Tool registry.

A `Tool` bundles an Anthropic tool definition (name / description / input
schema) with the Python handler that executes it. The `ToolRegistry` exposes the
definitions to the Executor and dispatches calls by name, catching handler errors
so a bad tool call never crashes the agent loop.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], str]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def definitions(self) -> list[dict[str, Any]]:
        """The `tools` payload for the Messages API."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in self._tools.values()
        ]

    def call(self, name: str, tool_input: dict[str, Any]) -> str:
        """Dispatch a tool call. Returns the result text, or an error string the
        model can read and recover from (never raises)."""
        tool = self._tools.get(name)
        if tool is None:
            return f"Error: unknown tool {name!r}."
        try:
            return tool.handler(tool_input)
        except Exception as exc:  # surfaced back to the model, not fatal
            return f"Error: {type(exc).__name__}: {exc}"

    def __len__(self) -> int:
        return len(self._tools)
