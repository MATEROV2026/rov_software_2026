"""Task list loaded from the backend GET /tasks."""
from __future__ import annotations

from typing import Any, Dict, List

import customtkinter as ctk


class TaskMenuScreen(ctk.CTkFrame):
    """Shows task id + title rows; app maps selection to task id."""

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkFrame,
        tasks: List[Dict[str, Any]],
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._tasks = tasks
        self._selected = 0
        self._labels: list[ctk.CTkLabel] = []

        title = ctk.CTkLabel(
            self,
            text="Select a task",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.pack(pady=(16, 8))

        body = ctk.CTkScrollableFrame(self, width=520, height=360)
        body.pack(fill="both", expand=True, padx=12, pady=8)

        for t in tasks:
            tid = t.get("id", "?")
            ttitle = t.get("title", "")
            line = f"{tid} — {ttitle}"
            lb = ctk.CTkLabel(
                body,
                text=line,
                font=ctk.CTkFont(size=15),
                anchor="w",
                justify="left",
            )
            lb.pack(fill="x", pady=4, padx=4)
            self._labels.append(lb)

        self._apply_highlight()

    @property
    def option_count(self) -> int:
        return max(1, len(self._tasks))

    def selection(self) -> int:
        return self._selected

    def set_selection(self, index: int) -> None:
        self._selected = max(0, min(self.option_count - 1, index))
        self._apply_highlight()

    def move(self, delta: int) -> None:
        self.set_selection(self._selected + delta)

    def selected_task_id(self) -> str:
        if not self._tasks:
            return ""
        return str(self._tasks[self._selected].get("id", ""))

    def _apply_highlight(self) -> None:
        for i, lb in enumerate(self._labels):
            if i == self._selected:
                lb.configure(text_color=("#1f538d", "#5dade2"))
            else:
                lb.configure(text_color=("gray20", "gray80"))
