"""Load and cache normalized tutorial tasks from task1/2/3.json."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.tutorial_normalize import load_all_tutorial_tasks

_CACHE: Optional[List[Dict[str, Any]]] = None


def _backend_dir() -> Path:
    return Path(__file__).resolve().parent


def get_tutorial_tasks() -> List[Dict[str, Any]]:
    global _CACHE
    if _CACHE is None:
        _CACHE = load_all_tutorial_tasks(_backend_dir())
    return _CACHE


def reload_tutorial_cache() -> None:
    global _CACHE
    _CACHE = None


def get_tutorial_task(task_id: str) -> Optional[Dict[str, Any]]:
    tid = task_id.strip().lower()
    for t in get_tutorial_tasks():
        if str(t.get("task_id", "")).lower() == tid:
            return t
    return None
