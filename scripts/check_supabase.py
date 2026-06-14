"""Live connectivity check for the Supabase memory backend.

Reads SUPABASE_URL / SUPABASE_KEY (and optionally SUPABASE_TABLE) from the
environment, writes one test record, reads recent records back, and prints the
result. The `runs` table must already exist — see docs/supabase-schema.sql.

Usage (from the project root):
    SUPABASE_URL=https://<ref>.supabase.co SUPABASE_KEY=<service-role-key> \
        ./.venv/bin/python scripts/check_supabase.py
"""
from __future__ import annotations

import pathlib
import sys

# Make the project root importable when run as a plain script.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src import config  # noqa: E402
from src.memory.supabase_store import SupabaseMemoryStore  # noqa: E402

MARKER = "[supabase connectivity check]"


def main() -> int:
    if not (config.SUPABASE_URL and config.SUPABASE_KEY):
        print(
            "SUPABASE_URL and SUPABASE_KEY must be set in the environment.",
            file=sys.stderr,
        )
        return 2

    store = SupabaseMemoryStore()
    print(f"Connected: {config.SUPABASE_URL}  (table={config.SUPABASE_TABLE})")

    store.add({"goal": MARKER, "approved": True, "score": 100, "attempts": 1})
    print("Inserted a test record.")

    recent = store.recent(3)
    print(f"Read back {len(recent)} recent record(s):")
    for r in recent:
        print("  ", r)

    print("\nOK — Supabase memory backend is working end-to-end.")
    print(f"(You can delete the test row where goal = '{MARKER}'.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
