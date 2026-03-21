"""Pick local image files and POST them to /upload-images/{task_id}."""
from __future__ import annotations

import tkinter.filedialog as filedialog
from typing import List

import customtkinter as ctk


class UploadScreen(ctk.CTkFrame):
    """
    Menu:
      0 — Choose files… (opens OS dialog; mouse may be needed)
      1 — Upload to server
      2 — Back
    """

    ACTIONS = ("Choose files…", "Upload to server", "Back")

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkFrame,
        task_id: str,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.task_id = task_id
        self._paths: List[str] = []
        self._selected = 0
        self._action_labels: list[ctk.CTkLabel] = []

        ctk.CTkLabel(
            self,
            text=f"Upload images — task {task_id}",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(16, 8))

        self._status = ctk.CTkLabel(
            self,
            text="No files selected.",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        )
        self._status.pack(pady=4)

        self._list = ctk.CTkTextbox(self, width=520, height=200)
        self._list.pack(fill="both", expand=True, padx=16, pady=8)

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

    def file_paths(self) -> List[str]:
        return list(self._paths)

    def choose_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select images",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("All files", "*.*"),
            ],
        )
        self._paths = list(paths)
        self._refresh_list()

    def set_status(self, message: str, *, ok: bool = True) -> None:
        color = ("green", "#2ecc71") if ok else ("darkred", "#e74c3c")
        self._status.configure(text=message, text_color=color)

    def _refresh_list(self) -> None:
        self._list.configure(state="normal")
        self._list.delete("1.0", "end")
        if not self._paths:
            self._list.insert("1.0", "(no files)")
            self.set_status("No files selected.", ok=True)
        else:
            self._list.insert("1.0", "\n".join(self._paths))
            self.set_status(f"{len(self._paths)} file(s) ready.", ok=True)
        self._list.configure(state="disabled")

    def _apply_highlight(self) -> None:
        for i, lb in enumerate(self._action_labels):
            if i == self._selected:
                lb.configure(text_color=("#1f538d", "#5dade2"))
            else:
                lb.configure(text_color=("gray20", "gray80"))
