"""HTTP routes for the step-by-step tutorial API."""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from backend.tutorial_repository import get_tutorial_task, get_tutorial_tasks

router = APIRouter(prefix="/tutorial", tags=["tutorial"])


@router.get("/tasks")
def list_tutorial_tasks() -> List[Dict[str, Any]]:
    """Summary list for the task picker."""
    return [
        {
            "task_id": t.get("task_id"),
            "title": t.get("title"),
            "subsection_count": len(t.get("subsections") or []),
            "has_final_flow": t.get("task_final_flow") is not None,
        }
        for t in get_tutorial_tasks()
    ]


@router.get("/tasks/{task_id}")
def get_full_tutorial_task(task_id: str) -> Dict[str, Any]:
    """Full normalized task for the GUI (all subsections and steps)."""
    t = get_tutorial_task(task_id)
    if not t:
        raise HTTPException(status_code=404, detail=f"Unknown tutorial task: {task_id}")
    return t


@router.post("/reload-cache")
def reload_cache() -> Dict[str, str]:
    """Dev-only: clear normalized cache after editing JSON."""
    from backend.tutorial_repository import reload_tutorial_cache

    reload_tutorial_cache()
    return {"ok": "true", "message": "tutorial cache cleared"}
