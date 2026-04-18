"""
Mission control GUI: CustomTkinter screens + pygame controller polling.

Run the backend first (from ``project/``, venv active):
  python run_backend.py
  # or: python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

Then start the GUI:
  python gui/app.py

If the process aborts with a macOS version message, run:
  python diagnose_gui.py
If it dies at tkinter.Tk(), your Python's Tcl/Tk targets a newer macOS than
yours — recreate the venv with Homebrew ``python@3.12`` (see diagnose_gui.py).

Architecture: screens render UI; gui.api talks to FastAPI; input is polled on a
timer. Keyboard uses Tk bindings. Pygame is optional and never loaded on macOS
(see requirements-joystick.txt for Linux/Windows gamepad support).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

# Project root before any `gui.*` import (must run before third-party imports
# that might confuse package resolution).
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import customtkinter as ctk

from gui import api as api_mod
from gui.controller import build_mission_input
from gui.screens.home import HomeScreen
from gui.screens.task_detail import TaskDetailScreen
from gui.screens.task_menu import TaskMenuScreen
from gui.screens.upload_screen import UploadScreen

Screen = Union[HomeScreen, TaskMenuScreen, TaskDetailScreen, UploadScreen]
State = Literal["home", "menu", "detail", "upload"]


class MissionApp(ctk.CTk):
    """Single window; swaps frames and routes controller events."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Matrov — Mission Control")
        self.geometry("640x720")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._state: State = "home"
        self._tasks: List[Dict[str, Any]] = []
        self._current_task: Dict[str, Any] = {}
        self._container = ctk.CTkFrame(self)
        self._container.pack(fill="both", expand=True)

        self._footer = ctk.CTkFrame(self)
        self._footer.pack(fill="x", side="bottom")
        foot_row1 = ctk.CTkFrame(self._footer, fg_color="transparent")
        foot_row1.pack(fill="x")
        self._backend_lbl = ctk.CTkLabel(
            foot_row1,
            text="Backend: checking…",
            font=ctk.CTkFont(size=11),
        )
        self._backend_lbl.pack(side="left", padx=8, pady=(4, 0))
        self._mission_lbl = ctk.CTkLabel(
            foot_row1,
            text="Mission status: READY",
            font=ctk.CTkFont(size=11),
        )
        self._mission_lbl.pack(side="right", padx=8, pady=(4, 0))
        self._input_lbl = ctk.CTkLabel(
            self._footer,
            text="Input: …",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w",
        )
        self._input_lbl.pack(fill="x", padx=8, pady=(0, 6))

        self._screen: Optional[Screen] = None
        self._controller = build_mission_input(self)
        self._input_lbl.configure(text=self._controller.status_hint())

        self._show_home()
        self._check_backend()
        self.after(50, self._input_tick)

    def destroy(self) -> None:  # noqa: A003 — Tk name
        self._controller.close()
        super().destroy()

    # --- mission status (bonus indicator) ---------------------------------
    def _set_mission_status(self, text: str) -> None:
        self._mission_lbl.configure(text=f"Mission status: {text}")

    def _reset_mission_ready(self) -> None:
        self._set_mission_status("READY")

    def _set_mission_uploaded(self) -> None:
        self._set_mission_status("UPLOADED")

    def _set_mission_sent(self) -> None:
        self._set_mission_status("SENT")

    # --- backend health -----------------------------------------------------
    def _check_backend(self) -> None:
        err = api_mod.check_backend()
        if err:
            self._backend_lbl.configure(
                text=f"Backend: OFFLINE ({err[:60]}…)"
                if len(err) > 60
                else f"Backend: OFFLINE ({err})",
                text_color="#e74c3c",
            )
        else:
            self._backend_lbl.configure(
                text="Backend: OK (127.0.0.1:8000)",
                text_color="#2ecc71",
            )

    # --- screen helpers -----------------------------------------------------
    def _clear_screen(self) -> None:
        if self._screen is not None:
            self._screen.destroy()
            self._screen = None

    def _show_home(self) -> None:
        self._state = "home"
        self._clear_screen()
        self._screen = HomeScreen(self._container)
        self._screen.pack(fill="both", expand=True)
        self._reset_mission_ready()

    def _show_menu(self) -> None:
        self._state = "menu"
        self._clear_screen()
        try:
            self._tasks = api_mod.get_tasks()
        except Exception as exc:  # noqa: BLE001
            self._screen = ctk.CTkLabel(
                self._container,
                text=(
                    f"Could not load tasks:\n{exc}\n\n"
                    "Press Esc to go back."
                ),
                font=ctk.CTkFont(size=14),
                justify="left",
            )
            self._screen.pack(expand=True)
            return
        if not self._tasks:
            self._screen = ctk.CTkLabel(
                self._container,
                text="No tasks returned from the server.\n\nPress Esc to go back.",
                font=ctk.CTkFont(size=14),
            )
            self._screen.pack(expand=True)
            return
        self._screen = TaskMenuScreen(self._container, self._tasks)
        self._screen.pack(fill="both", expand=True)

    def _show_detail(self, task: Dict[str, Any]) -> None:
        self._state = "detail"
        self._current_task = task
        self._clear_screen()
        self._screen = TaskDetailScreen(self._container, task)
        self._screen.pack(fill="both", expand=True)
        self._reset_mission_ready()

    def _show_upload(self, task_id: str) -> None:
        self._state = "upload"
        self._clear_screen()
        self._screen = UploadScreen(self._container, task_id)
        self._screen.pack(fill="both", expand=True)

    # --- input loop ---------------------------------------------------------
    def _input_tick(self) -> None:
        try:
            for ev in self._controller.poll():
                self._dispatch_nav(ev)
        except Exception:
            pass
        self.after(50, self._input_tick)

    def _dispatch_nav(self, ev: str) -> None:
        if ev == "up":
            self._nav_move(-1)
        elif ev == "down":
            self._nav_move(1)
        elif ev == "select":
            self._nav_select()
        elif ev == "back":
            self._nav_back()

    def _nav_move(self, delta: int) -> None:
        s = self._screen
        if s is None:
            return
        if isinstance(s, ctk.CTkLabel):
            return
        s.move(delta)

    def _nav_select(self) -> None:
        s = self._screen
        if s is None:
            return

        if isinstance(s, ctk.CTkLabel):
            # Error / empty-task message on task menu — Enter returns home.
            if self._state == "menu":
                self._show_home()
            return

        if self._state == "home" and isinstance(s, HomeScreen):
            choice = s.selected_label()
            if choice == "Browse Tasks":
                self._show_menu()
            elif choice == "Exit":
                self.destroy()
            return

        if self._state == "menu" and isinstance(s, TaskMenuScreen):
            tid = s.selected_task_id()
            if not tid:
                return
            try:
                task = api_mod.get_task(tid)
            except Exception as exc:  # noqa: BLE001
                self._toast(str(exc))
                return
            self._show_detail(task)
            return

        if self._state == "detail" and isinstance(s, TaskDetailScreen):
            act = s.selected_action()
            tid = s.task_id()
            if act == "Upload images":
                self._show_upload(tid)
            elif act == "Send run_task command":
                self._run_task_command(tid)
            elif act == "Back":
                self._show_menu()
            return

        if self._state == "upload" and isinstance(s, UploadScreen):
            act = s.selected_action()
            if act == "Choose files…":
                s.choose_files()
            elif act == "Upload to server":
                self._do_upload(s)
            elif act == "Back":
                self._show_detail(self._current_task)
            return

    def _nav_back(self) -> None:
        if self._state == "home":
            return
        if self._state == "menu":
            self._show_home()
        elif self._state == "detail":
            self._show_menu()
        elif self._state == "upload":
            self._show_detail(self._current_task)

    def _do_upload(self, screen: UploadScreen) -> None:
        paths = screen.file_paths()
        if not paths:
            screen.set_status("Select files first.", ok=False)
            return
        try:
            api_mod.upload_images(screen.task_id, paths)
        except Exception as exc:  # noqa: BLE001
            screen.set_status(f"Upload failed: {exc}", ok=False)
            return
        screen.set_status("Upload successful.", ok=True)
        self._set_mission_uploaded()

    def _run_task_command(self, task_id: str) -> None:
        try:
            api_mod.send_command({"command": "run_task", "task_id": task_id})
        except Exception as exc:  # noqa: BLE001
            self._toast(f"Command failed: {exc}")
            return
        self._set_mission_sent()
        self._toast(f"run_task sent for {task_id}")

    def _toast(self, message: str) -> None:
        # Lightweight feedback without extra dialogs.
        win = ctk.CTkToplevel(self)
        win.title("Notice")
        win.geometry("420x120")
        ctk.CTkLabel(win, text=message, wraplength=380).pack(
            expand=True, padx=12, pady=12
        )
        win.after(2500, win.destroy)


def main() -> None:
    app = MissionApp()
    app.mainloop()


if __name__ == "__main__":
    main()
