"""
Default countdown duration for the operator tutorial timer.

Override with environment variable ``MATROV_TIMER_SECONDS`` (integer seconds).
Example: ``export MATROV_TIMER_SECONDS=1200`` for 20 minutes.
"""
from __future__ import annotations

import os

_DEFAULT = 15 * 60  # 15:00


def default_timer_seconds() -> int:
    raw = os.environ.get("MATROV_TIMER_SECONDS", "").strip()
    if not raw:
        return _DEFAULT
    try:
        return max(1, int(raw))
    except ValueError:
        return _DEFAULT
