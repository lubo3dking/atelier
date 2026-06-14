"""Executor agent — carries out the plan using a manual tool-use loop.

The loop is manual (rather than the SDK tool-runner) so every tool call is
visible and gated by our `ToolRegistry`, which is the auditable boundary between
the model and the file system.
"""
from __future__ import annotations

from .. import config
from ..llm.client import LLMClient, extract_text
from ..schemas import Plan
from ..tools.registry import ToolRegistry
from .base import Agent


class Executor(Agent):
    def __init__(
        self,
        name: str,
        system_prompt: str,
        client: LLMClient,
        tools: ToolRegistry,
        max_tool_iterations: int = config.MAX_TOOL_ITERATIONS,
    ) -> None:
        super().__init__(name=name, system_prompt=system_prompt, client=client)
        self.tools = tools
        self.max_tool_iterations = max_tool_iterations

    def _build_task(self, goal: str, plan: Plan, feedback: str | None) -> str:
        steps = "\n".join(f"{i}. {s.description}" for i, s in enumerate(plan.steps, 1))
        task = f"Goal:\n{goal}\n\nPlan to carry out:\n{steps}"
        if feedback:
            task += (
                "\n\nA previous attempt was rejected on review. Address this "
                f"feedback in your work:\n{feedback}"
            )
        task += "\n\nWhen finished, summarize what you did and the outcome."
        return task

    def execute(self, goal: str, plan: Plan, feedback: str | None = None) -> str:
        messages: list[dict] = [
            {"role": "user", "content": self._build_task(goal, plan, feedback)}
        ]
        tool_defs = self.tools.definitions()

        for _ in range(self.max_tool_iterations):
            response = self.client.create(
                system=self.system_prompt,
                messages=messages,
                tools=tool_defs or None,
            )
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                return extract_text(response)

            tool_results = []
            for block in response.content:
                if getattr(block, "type", None) == "tool_use":
                    result = self.tools.call(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )
            messages.append({"role": "user", "content": tool_results})

        # Iteration cap hit — return whatever the last turn produced.
        return extract_text(response)
