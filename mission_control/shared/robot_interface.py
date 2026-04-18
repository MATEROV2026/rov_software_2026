"""
Robot command path for the competition stack.

All future Jetson/ROS2 integration should live behind RobotInterface
implementations so the FastAPI layer and GUI stay decoupled from ROS2.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class RobotInterface(ABC):
    """Abstract bridge to the vehicle / mission computer."""

    @abstractmethod
    def run_task(self, task_id: str) -> Dict[str, Any]:
        """Start or signal execution of a mission task on the robot."""

    @abstractmethod
    def send_images(self, task_id: str, image_paths: List[str]) -> Dict[str, Any]:
        """Push image paths or blobs to the robot or downstream pipeline."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Return connectivity / mode / health for the mission UI."""


class MockRobotInterface(RobotInterface):
    """Development stand-in; swap for a real implementation later."""

    def __init__(self) -> None:
        self._last_task: str | None = None
        self._last_images: Dict[str, List[str]] = {}

    def run_task(self, task_id: str) -> Dict[str, Any]:
        self._last_task = task_id
        return {"ok": True, "task_id": task_id, "message": "mock: run_task accepted"}

    def send_images(
        self, task_id: str, image_paths: List[str]
    ) -> Dict[str, Any]:
        self._last_images[task_id] = list(image_paths)
        return {
            "ok": True,
            "task_id": task_id,
            "count": len(image_paths),
            "message": "mock: send_images recorded",
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "connected": True,
            "mode": "mock",
            "last_task": self._last_task,
        }
