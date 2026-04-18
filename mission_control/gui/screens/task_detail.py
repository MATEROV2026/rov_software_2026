"""Task detail: instructions, required images, actions."""
from __future__ import annotations

from typing import Any, Dict, List

import customtkinter as ctk


class TaskDetailScreen(ctk.CTkFrame):
    """
    Displays one task; bottom menu drives Upload / run_task / Back.

    Indices:
      0 — Upload images
      1 — Send run_task command
      2 — Back
    """

    ACTIONS = ("Upload images", "Send run_task command", "Back")

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkFrame,
        task: Dict[str, Any],
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._task = task
        self._selected = 0
        self._action_labels: list[ctk.CTkLabel] = []

        tid = task.get("id", "")
        title = task.get("title", "")
        ctk.CTkLabel(
            self,
            text=f"Task {tid}",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(16, 4))
        ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(size=15),
            wraplength=520,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 8))

        ctk.CTkLabel(
            self,
            text="Instructions",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16)

        inst: List[str] = list(task.get("instructions") or [])
        inst_box = ctk.CTkTextbox(self, width=520, height=140)
        inst_box.pack(fill="x", padx=16, pady=4)
        inst_box.insert("1.0", "\n".join(f"• {s}" for s in inst) or "(none)")
        inst_box.configure(state="disabled")

        ctk.CTkLabel(
            self,
            text="Required images",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(8, 4))

        req: List[str] = list(task.get("required_images") or [])
        req_text = ", ".join(req) if req else "(none specified)"
        ctk.CTkLabel(
            self,
            text=req_text,
            font=ctk.CTkFont(size=13),
            wraplength=520,
            justify="left",
        ).pack(anchor="w", padx=16)

        ctk.CTkLabel(
            self,
            text="Actions",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(12, 4))

        for text in self.ACTIONS:
            lb = ctk.CTkLabel(self, text=text, font=ctk.CTkFont(size=16))
            lb.pack(pady=6)
            self._action_labels.append(lb)

        self._apply_highlight()

    @property
    def option_count(self) -> int:
        return len(self.ACTIONS)

    def set_selection(self, index: int) -> None:
        self._selected = max(0, min(self.option_count - 1, index))
        self._apply_highlight()

    def move(self, delta: int) -> None:
        self.set_selection(self._selected + delta)

    def selected_action(self) -> str:
        return self.ACTIONS[self._selected]

    def task_id(self) -> str:
        return str(self._task.get("id", ""))

    def _apply_highlight(self) -> None:
        for i, lb in enumerate(self._action_labels):
            if i == self._selected:
                lb.configure(text_color=("#1f538d", "#5dade2"))
            else:
                lb.configure(text_color=("gray20", "gray80"))
