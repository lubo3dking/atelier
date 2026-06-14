"""Tests for LLMClient's JSON fallback when the structured-output grammar fails."""
import types

import pytest

from src.llm.client import LLMClient, _extract_json
from src.schemas import BomItem


def test_extract_json_strips_fences_and_prose():
    assert _extract_json('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert _extract_json('here you go {"a": 2} thanks') == '{"a": 2}'
    assert _extract_json('{"a": 3}') == '{"a": 3}'


class _Resp:
    def __init__(self, text):
        self.content = [types.SimpleNamespace(type="text", text=text)]


class _FakeAnthropic:
    """messages.parse raises; messages.create returns canned JSON text."""

    def __init__(self, parse_exc, create_text):
        self._parse_exc = parse_exc
        self._create_text = create_text
        self.messages = self

    def parse(self, **_kw):
        raise self._parse_exc

    def create(self, **_kw):
        return _Resp(self._create_text)


def test_parse_falls_back_to_json_on_grammar_error():
    fake = _FakeAnthropic(
        Exception("Grammar compilation timed out."),
        '{"component": "X", "specification": "Y", "quantity": "1"}',
    )
    client = LLMClient(anthropic_client=fake)
    out = client.parse(system="s", messages=[], schema=BomItem)
    assert isinstance(out, BomItem) and out.component == "X"


def test_parse_reraises_non_grammar_errors():
    fake = _FakeAnthropic(Exception("some other error"), "{}")
    client = LLMClient(anthropic_client=fake)
    with pytest.raises(Exception, match="some other error"):
        client.parse(system="s", messages=[], schema=BomItem)


class _RecordingAnthropic:
    """Records whether the structured parse() path is used."""

    def __init__(self, create_text):
        self._create_text = create_text
        self.parse_called = False
        self.messages = self

    def parse(self, **_kw):
        self.parse_called = True
        raise AssertionError("structured parse should be skipped in json_mode")

    def create(self, **_kw):
        return _Resp(self._create_text)


def test_json_mode_skips_structured_call():
    fake = _RecordingAnthropic('{"component": "X", "specification": "Y", "quantity": "1"}')
    client = LLMClient(anthropic_client=fake)
    out = client.parse(system="s", messages=[], schema=BomItem, json_mode=True)
    assert isinstance(out, BomItem) and out.component == "X"
    assert fake.parse_called is False  # one call (create), no failed structured attempt
