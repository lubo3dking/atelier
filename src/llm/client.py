"""The single wrapper around the Anthropic SDK.

Every call to Claude in this system goes through `LLMClient`. Keeping it in one
place means model id, adaptive thinking, and effort are configured once, and the
rest of the codebase never touches the SDK directly — which also makes the whole
system trivially testable by injecting a fake client.
"""
from __future__ import annotations

from typing import Any

from .. import config


def extract_text(message: Any) -> str:
    """Concatenate the text content blocks of a response message.

    Thinking / tool_use blocks are skipped — only `type == "text"` carries the
    model's natural-language output.
    """
    parts = []
    for block in message.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts)


def _extract_json(text: str) -> str:
    """Pull the outermost JSON object out of a model response (strips fences/prose)."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    start, end = text.find("{"), text.rfind("}")
    return text[start : end + 1] if start != -1 and end != -1 else text


class LLMClient:
    def __init__(
        self,
        *,
        model: str = config.MODEL,
        effort: str = config.EFFORT,
        max_tokens: int = config.MAX_TOKENS,
        anthropic_client: Any | None = None,
    ) -> None:
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens
        if anthropic_client is None:
            import anthropic  # imported lazily so tests need not install/configure it

            anthropic_client = anthropic.Anthropic()
        self._client = anthropic_client

    def _common_kwargs(self, max_tokens: int | None) -> dict[str, Any]:
        return {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": self.effort},
        }

    def create(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        """Raw message turn. Returns the SDK response (with .content / .stop_reason)."""
        kwargs = self._common_kwargs(max_tokens)
        kwargs.update(system=system, messages=messages)
        if tools:
            kwargs["tools"] = tools
        return self._client.messages.create(**kwargs)

    def parse(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        schema: type,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> Any:
        """Structured turn. Returns a validated instance of `schema`.

        Uses Anthropic's native structured output. If the server's grammar
        compiler rejects the schema (it can time out on large/complex schemas),
        we fall back to plain JSON mode and validate with Pydantic.

        Pass ``json_mode=True`` to skip the native structured attempt entirely and
        go straight to JSON mode — one API call instead of a guaranteed-to-fail
        structured call followed by the JSON retry. Use this for schemas known to
        time out the grammar compiler (the Designer's DesignBrief).
        """
        if json_mode:
            return self._parse_via_json(system, messages, schema, max_tokens)
        kwargs = self._common_kwargs(max_tokens)
        kwargs.update(system=system, messages=messages, output_format=schema)
        try:
            response = self._client.messages.parse(**kwargs)
            return response.parsed_output
        except Exception as exc:  # noqa: BLE001 - inspect message to decide fallback
            if "grammar" not in str(exc).lower():
                raise
            return self._parse_via_json(system, messages, schema, max_tokens)

    def _parse_via_json(self, system, messages, schema, max_tokens) -> Any:
        """Fallback: ask for raw JSON and validate it with Pydantic."""
        import json

        schema_json = json.dumps(schema.model_json_schema())
        system2 = (
            system
            + "\n\nReturn ONLY a single JSON object conforming to this JSON Schema. "
            "No prose, no explanation, no markdown code fences.\n\nJSON Schema:\n"
            + schema_json
        )
        response = self.create(system=system2, messages=messages, max_tokens=max_tokens)
        return schema.model_validate_json(_extract_json(extract_text(response)))
