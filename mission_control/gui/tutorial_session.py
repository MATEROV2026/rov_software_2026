"""Linear navigation over normalized tutorial subsections and task_final_flow."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class TutorialPosition:
    """Index into flattened tutorial timeline."""

    segment_index: int
    step_index: int


class TutorialNavigator:
    """
    ``segments`` is a list of step lists: one per subsection, plus optional
    final segment from ``task_final_flow``.
    """

    def __init__(self, task: Dict[str, Any]) -> None:
        self.task = task
        self.subsections: List[Dict[str, Any]] = list(task.get("subsections") or [])
        self.segments: List[List[Dict[str, Any]]] = [
            list(s.get("steps") or []) for s in self.subsections
        ]
        raw_final = task.get("task_final_flow")
        self.final_flow: Optional[Dict[str, Any]] = (
            raw_final if isinstance(raw_final, dict) else None
        )
        if self.final_flow and self.final_flow.get("steps"):
            self.segments.append(list(self.final_flow["steps"]))

        if not self.segments:
            self.segments = [[]]
        self.pos = TutorialPosition(0, 0)

    def is_final_segment(self) -> bool:
        if not self.final_flow:
            return False
        return self.pos.segment_index == len(self.subsections)

    def current_subsection(self) -> Optional[Dict[str, Any]]:
        if self.is_final_segment():
            return None
        if 0 <= self.pos.segment_index < len(self.subsections):
            return self.subsections[self.pos.segment_index]
        return None

    def current_step(self) -> Optional[Dict[str, Any]]:
        seg = self._current_segment()
        if not seg or self.pos.step_index >= len(seg):
            return None
        return seg[self.pos.step_index]

    def _current_segment(self) -> List[Dict[str, Any]]:
        if 0 <= self.pos.segment_index < len(self.segments):
            return self.segments[self.pos.segment_index]
        return []

    def at_start(self) -> bool:
        return self.pos.segment_index == 0 and self.pos.step_index == 0

    def at_end(self) -> bool:
        seg = self._current_segment()
        return (
            self.pos.segment_index == len(self.segments) - 1
            and self.pos.step_index >= max(0, len(seg) - 1)
            and len(seg) > 0
        )

    def progress_label(self) -> str:
        n_seg = len(self.segments)
        seg = self._current_segment()
        n_steps = max(1, len(seg))
        return (
            f"Part {self.pos.segment_index + 1}/{n_seg}  ·  "
            f"Step {self.pos.step_index + 1}/{n_steps}"
        )

    def subsection_title_for_header(self) -> str:
        if self.is_final_segment() and self.final_flow:
            return str(self.final_flow.get("title") or "Task completion")
        sub = self.current_subsection()
        if sub:
            return str(sub.get("title") or sub.get("subtask_id") or "Subsection")
        return "—"

    def advance(self) -> bool:
        """Move to next step. Return False if already at last step."""
        seg = self._current_segment()
        if not seg:
            return False
        if self.pos.step_index < len(seg) - 1:
            self.pos.step_index += 1
            return True
        if self.pos.segment_index < len(self.segments) - 1:
            self.pos.segment_index += 1
            self.pos.step_index = 0
            return True
        return False

    def go_back(self) -> bool:
        """Move to previous step. Return False if at first step."""
        if self.pos.step_index > 0:
            self.pos.step_index -= 1
            return True
        if self.pos.segment_index > 0:
            self.pos.segment_index -= 1
            prev = self.segments[self.pos.segment_index]
            self.pos.step_index = max(0, len(prev) - 1)
            return True
        return False

    def skip_subsection(self) -> bool:
        """
        Jump to the start of the next segment. Return False if none.
        """
        if self.pos.segment_index >= len(self.segments) - 1:
            return False
        self.pos.segment_index += 1
        self.pos.step_index = 0
        return True
