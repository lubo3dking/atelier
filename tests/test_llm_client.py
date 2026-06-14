"""Tests for the LLMClient wrapper, using a fake Anthropic client that records
the kwargs it receives — so we verify model id, adaptive thinking, effort, and
tool plumbing without any network call."""
import types

from src.llm.client import LLMClient, extract_text
from src.schemas import ReviewVerdict


class FakeMessages:
    def __init__(self):
        self.create_kwargs = None
        self.parse_kwargs = None

    def create(self, **kwargs):
        self.create_kwargs = kwargs
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text="hi")],
            stop_reason="end_turn",
        )

    def parse(self, **kwargs):
        self.parse_kwargs = kwargs
        verdict = ReviewVerdict(approved=True, score=100, feedback="")
        return types.SimpleNamespace(parsed_output=verdict)


class FakeAnthropic:
    def __init__(self):
        self.messages = FakeMessages()


def test_create_sets_model_thinking_effort():
    fake = FakeAnthropic()
    client = LLMClient(model="claude-opus-4-8", effort="high", anthropic_client=fake)
    client.create(system="sys", messages=[{"role": "user", "content": "x"}])
    kw = fake.messages.create_kwargs
    assert kw["model"] == "claude-opus-4-8"
    assert kw["thinking"] == {"type": "adaptive"}
    assert kw["output_config"] == {"effort": "high"}
    assert kw["system"] == "sys"
    assert "tools" not in kw  # omitted when none passed


def test_create_passes_tools():
    fake = FakeAnthropic()
    client = LLMClient(anthropic_client=fake)
    tools = [{"name": "t", "description": "d", "input_schema": {"type": "object", "properties": {}}}]
    client.create(system="s", messages=[], tools=tools)
    assert fake.messages.create_kwargs["tools"] == tools


def test_parse_returns_parsed_output():
    fake = FakeAnthropic()
    client = LLMClient(anthropic_client=fake)
    out = client.parse(system="s", messages=[], schema=ReviewVerdict)
    assert isinstance(out, ReviewVerdict)
    assert out.approved is True
    assert fake.messages.parse_kwargs["output_format"] is ReviewVerdict


def test_extract_text_skips_non_text_blocks():
    msg = types.SimpleNamespace(
        content=[
            types.SimpleNamespace(type="thinking", thinking="..."),
            types.SimpleNamespace(type="text", text="hello "),
            types.SimpleNamespace(type="text", text="world"),
        ]
    )
    assert extract_text(msg) == "hello world"
