"""Pick a tutorial task from GET /tutorial/tasks catalog."""
from __future__ import annotations

from typing import Any, Dict, List

import customtkinter as ctk


class TutorialTaskPickScreen(ctk.CTkFrame):
    """Lists task_id and title; app reads selection for full task load."""

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
            text="Operator tutorial — choose a task",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title.pack(pady=(20, 6))

        sub = ctk.CTkLabel(
            self,
            text="Tasks load from task1.json, task2.json, task3.json on the server.",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        )
        sub.pack(pady=(0, 12))

        body = ctk.CTkScrollableFrame(self, width=560, height=380)
        body.pack(fill="both", expand=True, padx=16, pady=8)

        for t in tasks:
            tid = t.get("task_id", "?")
            ttitle = t.get("title", "")
            nsub = t.get("subsection_count", 0)
            line = f"{tid} — {ttitle}  ({nsub} parts)"
            lb = ctk.CTkLabel(
                body,
                text=line,
                font=ctk.CTkFont(size=17),
                anchor="w",
                justify="left",
            )
            lb.pack(fill="x", pady=6, padx=6)
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
        return str(self._tasks[self._selected].get("task_id", ""))

    def _apply_highlight(self) -> None:
        for i, lb in enumerate(self._labels):
            if i == self._selected:
                lb.configure(text_color=("#1f538d", "#5dade2"))
            else:
                lb.configure(text_color=("gray20", "gray80"))
