#!/usr/bin/env python3
"""
Start the FastAPI server reliably on macOS.

Avoid ``uvicorn`` CLI with ``--reload`` alone: the reloader can break with
``ModuleNotFoundError: uvicorn`` in the child process, and WatchFiles may
reload endlessly when ``.venv/`` changes during ``pip install``.

This uses ``uvicorn.run`` and limits reload to ``backend/`` and ``shared/``.

Usage (from the ``project/`` directory, venv active):

  python run_backend.py

No auto-reload (simplest):

  python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parent


def main() -> None:
    import uvicorn  # noqa: PLC0415

    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[
            str(_ROOT / "backend"),
            str(_ROOT / "shared"),
        ],
    )


if __name__ == "__main__":
    main()
