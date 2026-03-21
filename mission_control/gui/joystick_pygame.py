"""
Optional pygame joystick backend — **do not import on macOS** from the main app.

Load only via ``gui.controller.build_mission_input`` when
``MATROV_JOY_BACKEND=pygame`` and ``sys.platform != \"darwin\"``.

Install: ``pip install pygame`` (see ``requirements-joystick.txt``).
"""
from __future__ import annotations

import time
from typing import List, Optional


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


class PygameJoystickInput:
    """Poll first connected joystick (Linux/Windows)."""

    def __init__(self) -> None:
        import pygame  # noqa: PLC0415

        self._pygame = pygame
        pygame.init()
        pygame.joystick.init()
        self._joystick: Optional[pygame.joystick.Joystick] = None
        self._stick_deadzone = 0.45
        self._cd = _Cooldown()
        self._prev_hat: tuple[int, int] = (0, 0)
        self._prev_axis_sign: int = 0
        self._prev_buttons: tuple[bool, bool] = (False, False)

        if pygame.joystick.get_count() > 0:
            self._joystick = pygame.joystick.Joystick(0)
            self._joystick.init()

    def poll(self) -> List[str]:
        pygame = self._pygame
        events: List[str] = []
        pygame.event.pump()

        joy = self._joystick
        if joy:
            if joy.get_numhats() > 0:
                hat = joy.get_hat(0)
                hy_prev = self._prev_hat[1]
                hy = hat[1]
                if hy == 1 and hy_prev != 1 and self._cd.ok("hat_up"):
                    events.append("up")
                if hy == -1 and hy_prev != -1 and self._cd.ok("hat_down"):
                    events.append("down")
                self._prev_hat = hat

            if joy.get_numaxes() > 1:
                ay = joy.get_axis(1)
                sign = 0
                if ay < -self._stick_deadzone:
                    sign = -1
                elif ay > self._stick_deadzone:
                    sign = 1
                if sign != 0 and sign != self._prev_axis_sign:
                    if sign < 0 and self._cd.ok("axis_up"):
                        events.append("up")
                    if sign > 0 and self._cd.ok("axis_down"):
                        events.append("down")
                self._prev_axis_sign = sign

            b0 = bool(joy.get_numbuttons() > 0 and joy.get_button(0))
            b1 = bool(joy.get_numbuttons() > 1 and joy.get_button(1))
            if b0 and not self._prev_buttons[0] and self._cd.ok("btn_a"):
                events.append("select")
            if b1 and not self._prev_buttons[1] and self._cd.ok("btn_b"):
                events.append("back")
            self._prev_buttons = (b0, b1)

        return events

    def close(self) -> None:
        self._pygame.quit()
