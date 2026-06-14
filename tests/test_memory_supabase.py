"""Offline tests for the Supabase memory backend and the backend factory.

A fake Supabase client mimics the `client.table(...).insert(...).execute()` and
`.select(...).order(...).limit(...).execute()` call chains, so the store is
exercised without the `supabase` package, credentials, or a network.
"""
import types

import pytest

from src.memory import MemoryStore, get_memory
from src.memory.supabase_store import SupabaseMemoryStore


class FakeTable:
    def __init__(self, parent, name):
        self.parent = parent
        self.name = name
        self._selecting = False

    def insert(self, row):
        self.parent.inserted.append((self.name, row))
        return self

    def select(self, *_args):
        self._selecting = True
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, n):
        self.parent.limit_seen = n
        return self

    def execute(self):
        data = list(self.parent.rows) if self._selecting else None
        return types.SimpleNamespace(data=data)


class FakeSupabase:
    def __init__(self, rows=None):
        self.inserted = []
        self.rows = rows or []  # as returned by the DB: newest first
        self.limit_seen = None

    def table(self, name):
        return FakeTable(self, name)


def test_add_persists_only_known_columns():
    fake = FakeSupabase()
    store = SupabaseMemoryStore(table="runs", client=fake)
    store.add({"goal": "g", "approved": True, "score": 90, "attempts": 2, "extra": "ignored"})

    assert len(fake.inserted) == 1
    table_name, row = fake.inserted[0]
    assert table_name == "runs"
    assert row == {"goal": "g", "approved": True, "score": 90, "attempts": 2}
    assert "extra" not in row  # unknown keys are dropped


def test_recent_reverses_to_oldest_first():
    # DB returns newest-first; the store should hand back oldest-first.
    rows = [{"goal": "newest"}, {"goal": "middle"}, {"goal": "oldest"}]
    fake = FakeSupabase(rows=rows)
    store = SupabaseMemoryStore(client=fake)

    recent = store.recent(3)
    assert [r["goal"] for r in recent] == ["oldest", "middle", "newest"]
    assert fake.limit_seen == 3


def test_context_for_shared_with_base():
    fake = FakeSupabase(
        rows=[{"goal": "build x", "approved": True, "score": 95, "attempts": 1}]
    )
    store = SupabaseMemoryStore(client=fake)
    ctx = store.context_for("build x")
    assert "build x" in ctx and "approved" in ctx


def test_missing_credentials_raises():
    with pytest.raises(ValueError):
        SupabaseMemoryStore(url="", key="")  # no client, no creds


def test_factory_json_default():
    assert isinstance(get_memory("json"), MemoryStore)


def test_factory_unknown_backend_raises():
    with pytest.raises(ValueError):
        get_memory("redis")


def test_factory_supabase_requires_credentials(monkeypatch):
    # With no creds configured, selecting supabase surfaces the clear error.
    monkeypatch.setattr("src.config.SUPABASE_URL", "")
    monkeypatch.setattr("src.config.SUPABASE_KEY", "")
    with pytest.raises(ValueError):
        get_memory("supabase")
