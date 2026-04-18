"""
Image upload endpoint. Files are stored under backend/uploaded_images/{task_id}/.
The GUI sends multipart files; this module only handles HTTP and filesystem I/O.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile

from .tasks import _load_tasks

router = APIRouter(tags=["uploads"])

_UPLOAD_ROOT = Path(__file__).resolve().parent.parent / "uploaded_images"


def _task_exists(task_id: str) -> bool:
    return any(t.get("id") == task_id for t in _load_tasks())


@router.post("/upload-images/{task_id}")
async def upload_images(
    task_id: str,
    files: List[UploadFile] = File(),
) -> dict:
    """POST /upload-images/{task_id} — accept multiple image uploads."""
    if not _task_exists(task_id):
        raise HTTPException(status_code=404, detail=f"Unknown task_id: {task_id}")
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    dest_dir = _UPLOAD_ROOT / task_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    saved: List[str] = []
    for uf in files:
        safe_name = Path(uf.filename or "image.bin").name
        out_path = dest_dir / safe_name
        content = await uf.read()
        out_path.write_bytes(content)
        saved.append(str(out_path.resolve()))

    return {
        "ok": True,
        "task_id": task_id,
        "saved_files": saved,
        "count": len(saved),
    }
