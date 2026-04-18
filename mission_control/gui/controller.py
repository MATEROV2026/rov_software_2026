"""
Navigation input for the mission GUI.

**Default (all platforms, especially macOS):** Tk ``bind_all`` only — no pygame.
Many pygame wheels ship SDL binaries that call ``abort()`` on import when the
OS is older than their minimum (e.g. \"macOS 26 required\"). That happens while
loading ``pygame.base`` and cannot be caught in Python.

**Optional joystick (Linux / Windows only):** install pygame and set
``MATROV_JOY_BACKEND=pygame``. See ``gui/joystick_pygame.py``.

Keyboard:
  Up/Down → move selection
  Return / Enter → select
  Escape → back

Joystick (when enabled on non-macOS):
  D-pad / stick Y → up/down
  Button 0 (A) → select, 1 (B) → back
"""
from __future__ import annotations

import os
import sys
import time
from collections import deque
from typing import List, Optional, Protocol


# --- shared cooldown -----------------------------------------------------------


class _Cooldown:
    def __init__(self, period_s: float = 0.2) -> None:
        self._period = period_s
        self._next_allowed: dict[str, float] = {}

    def ok(self, key: str) -> bool:
        now = time.monotonic()
        if now < self._next_allowed.get(key, 0):
            return False
        self._next_allowed[key] = now + self._period
        return True


# --- Tk keyboard input ---------------------------------------------------------


class TkKeyboardInput:
    """Arrow / Enter / Esc via bind_all; enqueued for the same poll() API."""

    def __init__(self, widget) -> None:
        self._q: deque[str] = deque()
        self._cd = _Cooldown()
        for seq, key, action in (
            ("<Up>", "up_k", "up"),
            ("<Down>", "down_k", "down"),
            ("<Return>", "ret_k", "select"),
            ("<KP_Enter>", "kpe_k", "select"),
            ("<Escape>", "esc_k", "back"),
        ):
            widget.bind_all(
                seq,
                lambda e, k=key, a=action: self._push(k, a),
                add=True,
            )

    def _push(self, cd_key: str, action: str) -> str:
        if self._cd.ok(cd_key):
            self._q.append(action)
        return "break"

    def poll(self) -> List[str]:
        out: List[str] = []
        while self._q:
            out.append(self._q.popleft())
        return out

    def close(self) -> None:
        pass


class MissionInput(Protocol):
    def poll(self) -> List[str]: ...
    def close(self) -> None: ...


class CombinedInput:
    """Tk keyboard plus an optional joystick backend (never pygame on macOS)."""

    def __init__(self, root_widget, joystick: Optional[object] = None) -> None:
        self._keyboard = TkKeyboardInput(root_widget)
        self._joy = joystick
        self.joystick_active = bool(
            joystick is not None
            and getattr(joystick, "_joystick", None) is not None
        )

    def poll(self) -> List[str]:
        out = self._keyboard.poll()
        if self._joy is not None:
            out.extend(self._joy.poll())  # type: ignore[attr-defined]
        return out

    def close(self) -> None:
        self._keyboard.close()
        if self._joy is not None:
            self._joy.close()  # type: ignore[attr-defined]

    def status_hint(self) -> str:
        if self._joy is None:
            if sys.platform == "darwin":
                return (
                    "Input: keyboard (macOS: use System Settings to map a "
                    "controller to keys, or run on Linux/Win + pygame — "
                    "see requirements-joystick.txt)"
                )
            return (
                "Input: keyboard (set MATROV_JOY_BACKEND=pygame + pip install "
                "pygame for joystick)"
            )
        if self.joystick_active:
            return "Input: keyboard + joystick (pygame)"
        return "Input: keyboard + joystick module (plug in controller)"


def build_mission_input(root_widget) -> CombinedInput:
    """
    Never import pygame on macOS — SDL dylibs in the wheel can abort Python
    during ``import pygame`` before any try/except runs.
    """
    joy = None
    want = os.environ.get("MATROV_JOY_BACKEND", "").strip().lower()
    if want == "pygame" and sys.platform != "darwin":
        try:
            from gui.joystick_pygame import PygameJoystickInput

            joy = PygameJoystickInput()
        except Exception:
            joy = None
    return CombinedInput(root_widget, joystick=joy)
