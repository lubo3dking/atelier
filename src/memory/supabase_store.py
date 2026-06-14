"""Supabase-backed memory of past runs.

Persists run records to a Supabase (Postgres) table via the official `supabase`
Python client. The client is imported lazily so the dependency is only required
when this backend is actually selected. See `docs/supabase-schema.sql` for the
table definition.
"""
from __future__ import annotations

from typing import Any

from .. import config
from .base import BaseMemory

# Columns persisted to the table. `created_at` is set by the DB default.
_COLUMNS = ("goal", "approved", "score", "attempts")


class SupabaseMemoryStore(BaseMemory):
    def __init__(
        self,
        *,
        url: str | None = None,
        key: str | None = None,
        table: str | None = None,
        client: Any | None = None,
    ) -> None:
        self.table_name = table or config.SUPABASE_TABLE
        if client is None:
            url = url or config.SUPABASE_URL
            key = key or config.SUPABASE_KEY
            if not (url and key):
                raise ValueError(
                    "SUPABASE_URL and SUPABASE_KEY must be set to use the supabase "
                    "memory backend."
                )
            from supabase import create_client  # lazy: optional dependency

            client = create_client(url, key)
        self._client = client

    def add(self, record: dict[str, Any]) -> None:
        row = {col: record.get(col) for col in _COLUMNS}
        self._client.table(self.table_name).insert(row).execute()

    def recent(self, n: int = 5) -> list[dict[str, Any]]:
        response = (
            self._client.table(self.table_name)
            .select("*")
            .order("created_at", desc=True)
            .limit(n)
            .execute()
        )
        rows = list(response.data or [])
        rows.reverse()  # most recent last, matching the JSON store's ordering
        return rows
