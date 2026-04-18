"""
FastAPI entrypoint. Wires HTTP routes to the task catalog and RobotInterface.

Run from the ``project/`` directory (venv activated). Prefer one of:

  python run_backend.py

  python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

Avoid bare ``uvicorn ... --reload`` if the reloader reports
``ModuleNotFoundError: uvicorn`` (use ``python -m uvicorn`` or
``run_backend.py``). Limit reload to ``backend/`` and ``shared/`` so
``.venv`` changes do not trigger endless reloads.

The GUI (``gui/app.py``) talks to this API only — no ROS2 imports here.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


# Allow `shared` import when running as `uvicorn backend.main:app`
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.routes.tasks import router as tasks_router
from backend.routes.uploads import router as uploads_router
from shared.robot_interface import RobotInterface

app = FastAPI(
    title="Matrov Mission Control API",
    description="REST API for ROV mission tasks, uploads, and robot commands.",
    version="0.1.0",
)

# Single process robot bridge used by the desktop app.
_robot = RobotInterface()

app.include_router(tasks_router)
app.include_router(uploads_router)


class CommandBody(BaseModel):
    """JSON body for POST /command."""

    command: str = Field(..., description="e.g. run_task, get_status, send_images")
    task_id: Optional[str] = None
    image_paths: Optional[List[str]] = Field(
        default=None,
        description="Server paths for send_images (from upload response).",
    )


@app.post("/command")
def post_command(body: CommandBody) -> Dict[str, Any]:
    """
    POST /command — dispatch to RobotInterface.

    Examples:
      {"command": "run_task", "task_id": "1.1"}
      {"command": "get_status"}
      {"command": "send_images", "task_id": "1.1", "image_paths": [...]}
    """
    cmd = body.command.strip().lower()

    if cmd == "run_task":
        if not body.task_id:
            raise HTTPException(
                status_code=400, detail="task_id required for run_task"
            )
        return _robot.run_task(body.task_id)

    if cmd == "get_status":
        return _robot.get_status()

    if cmd == "send_images":
        if not body.task_id:
            raise HTTPException(
                status_code=400, detail="task_id required for send_images"
            )
        paths = body.image_paths or []
        return _robot.send_images(body.task_id, paths)

    if cmd == "run_reconstruction":
        if not body.task_id:
            raise HTTPException(
                status_code=400, detail="task_id required for run_reconstruction"
            )
        paths = body.image_paths or []
        return _robot.run_reconstruction(body.task_id, paths)

    raise HTTPException(status_code=400, detail=f"Unknown command: {body.command}")
