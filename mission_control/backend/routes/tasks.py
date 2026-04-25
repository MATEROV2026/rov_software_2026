"""
Task catalog HTTP routes. Data is loaded from tasks.json next to main.py
so operators can edit missions without changing code.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/tasks", tags=["tasks"])

_TASKS_PATH = Path(__file__).resolve().parent.parent / "tasks.json"
_TASKS_CACHE: List[Dict[str, Any]] | None = None


def _load_tasks() -> List[Dict[str, Any]]:
    global _TASKS_CACHE
    if _TASKS_CACHE is None:
        if not _TASKS_PATH.exists():
            _TASKS_CACHE = []
        else:
            with _TASKS_PATH.open(encoding="utf-8") as f:
                _TASKS_CACHE = json.load(f)
    return _TASKS_CACHE


def reload_tasks_cache() -> None:
    """Clear cache so the next request reloads tasks.json from disk."""
    global _TASKS_CACHE
    _TASKS_CACHE = None


@router.get("")
def list_tasks() -> List[Dict[str, Any]]:
    """GET /tasks — list all mission tasks."""
    return _load_tasks()


@router.get("/{task_id}")
def get_task(task_id: str) -> Dict[str, Any]:
    """GET /tasks/{task_id} — single task with instructions and image keys."""
    for item in _load_tasks():
        if item.get("id") == task_id:
            return item
    raise HTTPException(status_code=404, detail=f"Unknown task_id: {task_id}")
