"""Countdown logic and warning thresholds (UI updates live in app.py)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Set, Tuple

# (seconds_remaining_threshold, message)
WARNING_THRESHOLDS = (
    (300, "Stay on pace"),
    (120, "Finish this subsection soon"),
    (60, "Do not go over the time limit"),
    (30, "Do not go over the time limit"),
)


@dataclass
class TutorialCountdown:
    """Mutable countdown; call tick() once per second when not paused."""

    total_seconds: int
    remaining: int = field(init=False)
    paused: bool = False
    _fired: Set[int] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.remaining = self.total_seconds

    def reset(self, seconds: Optional[int] = None) -> None:
        if seconds is not None:
            self.total_seconds = seconds
        self.remaining = self.total_seconds
        self.paused = False
        self._fired.clear()

    def tick(self) -> None:
        if self.paused or self.remaining <= 0:
            return
        self.remaining -= 1

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def format_clock(self) -> str:
        if self.remaining <= 0:
            return "0:00"
        m, s = divmod(self.remaining, 60)
        return f"{m:d}:{s:02d}"

    def urgency_level(self) -> str:
        """Return color hint for the header timer label."""
        if self.remaining <= 0:
            return "expired"
        if self.remaining <= 30:
            return "critical"
        if self.remaining <= 60:
            return "severe"
        if self.remaining <= 120:
            return "warn"
        if self.remaining <= 300:
            return "caution"
        return "ok"

    def timer_color(self) -> Tuple[str, str]:
        """(light_hex, dark_hex) for CustomTkinter text_color."""
        u = self.urgency_level()
        if u == "expired":
            return "#7b241c", "#e74c3c"
        if u == "critical":
            return "#922b21", "#ff6b6b"
        if u == "severe":
            return "#b7950b", "#f39c12"
        if u == "warn":
            return "#9a7d0a", "#f4d03f"
        if u == "caution":
            return "#1e8449", "#58d68d"
        return "#1f538d", "#5dade2"

    def consume_warnings(self) -> Optional[str]:
        """
        If we just crossed a threshold, return its message once per crossing.
        """
        if self.remaining <= 0:
            if "expired" not in self._fired:
                self._fired.add("expired")
                return "Time limit reached"
            return None
        msg: Optional[str] = None
        for sec, text in WARNING_THRESHOLDS:
            if self.remaining <= sec and sec not in self._fired:
                self._fired.add(sec)
                msg = text
        return msg
