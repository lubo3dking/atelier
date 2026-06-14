"""Base class shared by every agent.

An agent is just a name, a system prompt, and a handle to the shared LLM client.
Prompts are loaded from the `prompts/` directory by convention (`<name>.md`).
"""
from __future__ import annotations

from pathlib import Path

from .. import config
from ..llm.client import LLMClient


class Agent:
    def __init__(self, name: str, system_prompt: str, client: LLMClient) -> None:
        self.name = name
        self.system_prompt = system_prompt
        self.client = client

    @classmethod
    def from_prompt_file(
        cls,
        name: str,
        client: LLMClient,
        prompts_dir: Path = config.PROMPTS_DIR,
        **kwargs,
    ) -> "Agent":
        system_prompt = (Path(prompts_dir) / f"{name}.md").read_text(encoding="utf-8")
        return cls(name=name, system_prompt=system_prompt, client=client, **kwargs)
