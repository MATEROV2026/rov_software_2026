from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


class RobotInterface:
    def __init__(self) -> None:
        self._controller = None
        self._controller_error: str | None = None

    def _ensure_ros_paths(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        laptop_pkg_root = repo_root / "ros" / "src" / "laptop"
        if str(laptop_pkg_root) not in sys.path:
            sys.path.insert(0, str(laptop_pkg_root))

    def _get_controller(self):
        if self._controller is not None:
            return self._controller
        if self._controller_error is not None:
            raise RuntimeError(self._controller_error)

        try:
            self._ensure_ros_paths()
            from laptop.laptop_controller import LaptopController

            self._controller = LaptopController()
            return self._controller
        except Exception as exc:  # noqa: BLE001
            self._controller_error = f"ROS controller unavailable: {exc}"
            raise RuntimeError(self._controller_error) from exc

    def run_task(self, task_id: str) -> dict[str, Any]:
        return {"ok": True, "task_id": task_id, "message": "task received"}

    def send_images(self, task_id: str, image_paths: list[str]) -> dict[str, Any]:
        return {
            "ok": True,
            "task_id": task_id,
            "image_paths": image_paths,
            "count": len(image_paths),
            "message": "images registered",
        }

    def run_reconstruction(self, task_id: str, image_paths: list[str]) -> dict[str, Any]:
        controller = self._get_controller()
        controller.send_command("run_reconstruction")
        return {
            "ok": True,
            "task_id": task_id,
            "image_paths": image_paths,
            "message": "reconstruction command sent",
        }

    def get_status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "connected": self._controller_error is None,
            "mode": "ros2",
            "detail": self._controller_error or "ready",
        }
