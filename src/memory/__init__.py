"""Memory backends and the factory that selects one.

`get_memory()` returns the backend named by `AGENT_MEMORY_BACKEND` (default
`json`). The Supabase backend is imported lazily so its dependency is only
needed when that backend is selected.
"""
from __future__ import annotations

from .. import config
from .base import BaseMemory
from .store import MemoryStore


def get_memory(backend: str | None = None) -> BaseMemory:
    backend = (backend or config.MEMORY_BACKEND).lower()
    if backend == "json":
        return MemoryStore(config.MEMORY_FILE)
    if backend == "supabase":
        from .supabase_store import SupabaseMemoryStore

        return SupabaseMemoryStore()
    raise ValueError(
        f"Unknown memory backend: {backend!r} (expected 'json' or 'supabase')"
    )


__all__ = ["BaseMemory", "MemoryStore", "get_memory"]
