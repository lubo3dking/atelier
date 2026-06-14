"""Run the Atelier web app (browser frontend + API).

Loads a local .env (so ANTHROPIC_API_KEY and any optional Stripe/Resend keys are
picked up) and starts uvicorn. Open the printed URL, upload an inspiration photo
+ notes, pick sizes, and download the tech pack — no terminal needed after this.

Usage (from the project root):
    ./.venv/bin/python scripts/serve.py                 # http://localhost:8000
    ./.venv/bin/python scripts/serve.py --port 9000 --reload

The same code is started in production by the Dockerfile via uvicorn directly.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))


def _load_dotenv(path: pathlib.Path) -> None:
    """Minimal .env loader: KEY=VALUE lines, no override of existing env vars."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


# Load .env BEFORE importing config — config reads os.environ at import time, so
# the file must be in the environment first (owner key, rate limit, price, etc.).
_load_dotenv(_ROOT / ".env")

from src import config  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the Atelier web app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="Auto-reload on code changes (dev).")
    args = parser.parse_args(argv)

    import uvicorn

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("WARNING: ANTHROPIC_API_KEY is not set — generation will fail until you add it "
              "to .env. The app will still start so you can see the UI.", file=sys.stderr)

    print(f"\n  {config.BRAND_NAME} is running:  http://{args.host}:{args.port}\n")
    uvicorn.run(
        "src.web:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
