"""Check float dives against the MATE Floats! 2027 scoring rules.

Packet depths come from the pressure sensor, but the rules are about the
top of the float, so a sensor mounted lower is corrected by
`sensor_offset_m`. Regional pools move the depths; everything lives in
`Rules`, whose defaults are the World Championship's (5.18 m pool).

Per vertical profile (MATE's points):
  10  surface -> top of float at 4.0 m or deeper -> surface
   5  at least 10 packets from the profile sent to the station
   5  hold: 7 consecutive packets, 5 s apart, top within 2.0 m +- 0.33 m
   5  one packet within +-20 cm of each of 4.0, 3.5 ... 0.0 m on the ascent,
      temperature within 2.0 °C of MATE's readout, plus a light reading
  -5  touching the pool bottom (at most once per profile)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from packets import Packet


@dataclass(frozen=True)
class Rules:
    hold_depth_m: float = 2.0
    hold_tolerance_m: float = 0.33
    hold_packets: int = 7
    packet_interval_s: float = 5.0
    interval_tolerance_s: float = 1.0
    max_depth_m: float = 4.0
    sample_step_m: float = 0.5
    sample_tolerance_m: float = 0.20
    temperature_tolerance_c: float = 2.0
    min_packets: int = 10
    surface_m: float = 0.20        # top of float this shallow counts as at the surface
    pool_depth_m: float = 5.18
    float_height_m: float = 0.60   # MATE's limit; used to flag likely bottom contact
    sensor_offset_m: float = 0.0   # pressure sensor this far below the top of the float

    def top(self, packet: Packet) -> float:
        return packet.depth_m - self.sensor_offset_m

    def required_depths(self) -> List[float]:
        steps = round(self.max_depth_m / self.sample_step_m)
        return [round(self.max_depth_m - i * self.sample_step_m, 3) for i in range(steps + 1)]


@dataclass
class ProfileCheck:
    packets: List[Packet]
    rules: Rules
    completed: bool = False
    deepest_m: float = 0.0
    hold: Optional[Tuple[int, int]] = None          # first and last packet of the hold window
    samples: Dict[float, Optional[int]] = field(default_factory=dict)  # depth -> packet index
    temperatures_ok: Optional[bool] = None          # None until MATE's readout is entered
    touched_bottom: bool = False

    @property
    def enough_packets(self) -> bool:
        return len(self.packets) >= self.rules.min_packets

    @property
    def sensors_ok(self) -> bool:
        return all(i is not None for i in self.samples.values()) and self.temperatures_ok is True

    def points(self) -> int:
        if not self.completed:
            return 0
        return (10 + 5 * self.enough_packets + 5 * (self.hold is not None)
                + 5 * self.sensors_ok - 5 * self.touched_bottom)


def unique_in_order(packets: Iterable[Packet]) -> List[Packet]:
    """Time-ordered, without the repeats a float sends when it re-transmits."""
    seen, out = set(), []
    for packet in sorted(packets, key=lambda p: p.time_s):
        key = (packet.company, packet.time_s)
        if key not in seen:
            seen.add(key)
            out.append(packet)
    return out


def split_profiles(packets: Iterable[Packet], rules: Rules) -> Tuple[Optional[Packet], List[List[Packet]]]:
    """(first surface packet before any dive, dives). Each dive starts with the
    last surface packet before it and ends with the first one after it."""
    pre_dive, dives, current, last_surface = None, [], [], None
    for packet in unique_in_order(packets):
        if rules.top(packet) > rules.surface_m:
            if not current and last_surface is not None:
                current.append(last_surface)
            current.append(packet)
        else:
            if current:
                current.append(packet)
                dives.append(current)
                current = []
            elif pre_dive is None and not dives:
                pre_dive = packet
            last_surface = packet
    if current:
        dives.append(current)  # still under water, or the rest has not arrived yet
    return pre_dive, dives


def find_hold(packets: List[Packet], rules: Rules) -> Optional[Tuple[int, int]]:
    low = rules.hold_depth_m - rules.hold_tolerance_m
    high = rules.hold_depth_m + rules.hold_tolerance_m
    start = None
    for i, packet in enumerate(packets):
        if not low <= rules.top(packet) <= high:
            start = None  # left the range: MATE wants a whole new 30 s period
            continue
        spaced = i > 0 and abs(packet.time_s - packets[i - 1].time_s - rules.packet_interval_s) \
            <= rules.interval_tolerance_s
        if start is None or not spaced:
            start = i
        if i - start + 1 >= rules.hold_packets:
            return start, i
    return None


def check_profile(packets: List[Packet], rules: Rules,
                  mate_temperature_c: Optional[float] = None) -> ProfileCheck:
    check = ProfileCheck(packets, rules)
    if not packets:
        return check
    depths = [rules.top(p) for p in packets]
    deepest = max(range(len(packets)), key=lambda i: depths[i])
    check.deepest_m = depths[deepest]
    check.completed = (depths[0] <= rules.surface_m and depths[-1] <= rules.surface_m
                       and check.deepest_m >= rules.max_depth_m)
    check.hold = find_hold(packets, rules)
    for target in rules.required_depths():
        near = [i for i in range(deepest, len(packets))
                if abs(depths[i] - target) <= rules.sample_tolerance_m]
        check.samples[target] = min(near, key=lambda i: abs(depths[i] - target)) if near else None
    if mate_temperature_c is not None:
        check.temperatures_ok = all(
            abs(packets[i].temperature_c - mate_temperature_c) <= rules.temperature_tolerance_c
            for i in check.samples.values() if i is not None)
    check.touched_bottom = check.deepest_m + rules.float_height_m >= rules.pool_depth_m - 0.05
    return check
