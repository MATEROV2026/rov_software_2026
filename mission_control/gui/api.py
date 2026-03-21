"""
HTTP client for the FastAPI backend using only the Python standard library.

Avoids extra wheels (e.g. httpx’s dependency tree) so a bad native binary in
the venv cannot crash the GUI before the first request. Local dev uses HTTP
to 127.0.0.1 — no TLS required.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def _join(base: str, path: str) -> str:
    b = base.rstrip("/")
    p = path if path.startswith("/") else f"/{path}"
    return f"{b}{p}"


def _urlopen_json(
    req: urllib.request.Request,
    *,
    timeout: float,
    base_url: str,
) -> Any:
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            if not raw:
                return {}
            return json.loads(raw.decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode(errors="replace")) from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Cannot reach the API at {base_url}.\n\n"
            "Start the backend (from the project folder, other terminal):\n"
            "  uvicorn backend.main:app --host 127.0.0.1 --port 8000\n\n"
            f"Underlying error: {e}"
        ) from e
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Server did not return JSON (wrong port or not FastAPI?). {e}"
        ) from e


def get_tasks(base_url: str = DEFAULT_BASE_URL) -> List[Dict[str, Any]]:
    """GET /tasks — list all tasks."""
    req = urllib.request.Request(_join(base_url, "/tasks"), method="GET")
    data = _urlopen_json(req, timeout=15.0, base_url=base_url)
    if not isinstance(data, list):
        raise RuntimeError(f"Expected a JSON list from /tasks, got {type(data)}")
    return data


def get_task(
    task_id: str, base_url: str = DEFAULT_BASE_URL
) -> Dict[str, Any]:
    """GET /tasks/{task_id} — task detail."""
    req = urllib.request.Request(
        _join(base_url, f"/tasks/{task_id}"),
        method="GET",
    )
    data = _urlopen_json(req, timeout=15.0, base_url=base_url)
    if not isinstance(data, dict):
        raise RuntimeError(f"Expected a JSON object for task, got {type(data)}")
    return data


def upload_images(
    task_id: str,
    file_paths: List[str],
    base_url: str = DEFAULT_BASE_URL,
) -> Dict[str, Any]:
    """
    POST /upload-images/{task_id} — multipart form, field name ``files`` each.
    """
    boundary = uuid.uuid4().hex
    chunks: List[bytes] = []

    for path_str in file_paths:
        path = Path(path_str)
        data = path.read_bytes()
        mime = "application/octet-stream"
        suffix = path.suffix.lower()
        if suffix in (".jpg", ".jpeg"):
            mime = "image/jpeg"
        elif suffix == ".png":
            mime = "image/png"
        safe_name = path.name.replace('"', "_")
        chunks.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="files"; '
                f'filename="{safe_name}"\r\n'
                f"Content-Type: {mime}\r\n\r\n"
            ).encode("utf-8")
            + data
            + b"\r\n"
        )

    body = b"".join(chunks) + f"--{boundary}--\r\n".encode("utf-8")
    url = _join(base_url, f"/upload-images/{task_id}")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        },
    )
    data = _urlopen_json(req, timeout=120.0, base_url=base_url)
    if not isinstance(data, dict):
        raise RuntimeError(f"Expected JSON object from upload, got {type(data)}")
    return data


def send_command(
    command_json: Dict[str, Any],
    base_url: str = DEFAULT_BASE_URL,
) -> Dict[str, Any]:
    """POST /command — dispatch robot / mission commands."""
    payload = json.dumps(command_json).encode("utf-8")
    req = urllib.request.Request(
        _join(base_url, "/command"),
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Content-Length": str(len(payload)),
        },
    )
    data = _urlopen_json(req, timeout=30.0, base_url=base_url)
    if not isinstance(data, dict):
        raise RuntimeError(f"Expected JSON object from /command, got {type(data)}")
    return data


def check_backend(base_url: str = DEFAULT_BASE_URL) -> Optional[str]:
    """Return error message if /tasks is unreachable, else None."""
    req = urllib.request.Request(_join(base_url, "/tasks"), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            resp.read()
        return None
    except Exception as exc:  # noqa: BLE001
        return str(exc)
