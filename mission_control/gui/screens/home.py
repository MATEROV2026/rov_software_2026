"""Home screen: entry point with Browse / Exit."""
from __future__ import annotations

import customtkinter as ctk


class HomeScreen(ctk.CTkFrame):
    """Mission home; selection drives navigation in gui.app."""

    ITEMS = ("Operator Tutorial", "Browse Tasks", "Exit")

    def __init__(self, master: ctk.CTk | ctk.CTkFrame, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self._selected = 0
        self._labels: list[ctk.CTkLabel] = []

        title = ctk.CTkLabel(
            self,
            text="Matrov Mission Control",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title.pack(pady=(24, 8))

        hint = ctk.CTkLabel(
            self,
            text="Keyboard: ↑ ↓  ·  Enter  ·  Esc\n"
            "Gamepad: map to keys in System Settings (macOS), or use "
            "MATROV_JOY_BACKEND=pygame on Linux/Windows",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        hint.pack(pady=(0, 16))

        for text in self.ITEMS:
            lb = ctk.CTkLabel(self, text=text, font=ctk.CTkFont(size=18))
            lb.pack(pady=10)
            self._labels.append(lb)

        self._apply_highlight()

    @property
    def option_count(self) -> int:
        return len(self.ITEMS)

    def selection(self) -> int:
        return self._selected

    def set_selection(self, index: int) -> None:
        self._selected = max(0, min(self.option_count - 1, index))
        self._apply_highlight()

    def move(self, delta: int) -> None:
        self.set_selection(self._selected + delta)

    def selected_label(self) -> str:
        return self.ITEMS[self._selected]

    def _apply_highlight(self) -> None:
        for i, lb in enumerate(self._labels):
            if i == self._selected:
                lb.configure(text_color=("#1f538d", "#5dade2"))
            else:
                lb.configure(text_color=("gray20", "gray80"))
