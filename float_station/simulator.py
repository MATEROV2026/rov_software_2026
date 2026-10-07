"""Simulated float runs, as the lines a float would transmit.

Lets the station be built, tested and demonstrated before the float exists:

    ../float_station/.venv/bin/python simulator.py > run.txt

A run is one pre-dive packet, then each profile's log as it would be sent
after surfacing. The log follows the firmware rules the station checks:
a packet every 5 s, plus one at each 0.5 m level on the way up.
"""
from __future__ import annotations

import argparse
import math
import random
from typing import Iterable, List, Tuple

from packets import nmea_checksum
from profile import Rules


def _line(company, t, depth, rng, checksum):
    depth = max(0.0, depth + rng.gauss(0, 0.01))
    temperature = 25.0 - 0.35 * depth + rng.gauss(0, 0.05)     # slightly cooler with depth
    light = 0.95 * math.exp(-0.28 * depth) + rng.gauss(0, 0.004)  # photodiode volts
    h, rem = divmod(int(t), 3600)
    clock = f'{h}:{rem // 60:02d}:{rem % 60:02d} UTC'
    text = (f'{company} {clock} {depth * 9.80665:.1f} kpa  {depth:.2f} meters '
            f'{temperature:.1f}oC  {light:.3f} V')
    return f'{text}*{nmea_checksum(text)}' if checksum else text


def simulate_profile(rules: Rules, t0: float, rng: random.Random, *, drift: bool = False,
                     touch_bottom: bool = False, skip: Iterable[float] = ()) -> Tuple[List[Tuple[float, float]], float]:
    """(time, sensor depth) samples for one profile, and the time it ends."""
    offset, interval = rules.sensor_offset_m, rules.packet_interval_s
    samples, t = [(t0, offset)], t0
    depth = offset
    # Descend to the hold depth at ~0.1 m/s, logging every 5 s.
    while depth < rules.hold_depth_m + offset - 0.05:
        t += interval
        depth = min(rules.hold_depth_m + offset, depth + 0.5)
        samples.append((t, depth))
    # Hold for 40 s; a drifting float leaves the range once and must start over.
    hold_steps = 9
    for step in range(hold_steps + (6 if drift else 0)):
        t += interval
        wobble = rng.uniform(-0.12, 0.12)
        if drift and step == 3:
            wobble = rules.hold_tolerance_m + 0.08
        samples.append((t, rules.hold_depth_m + offset + wobble))
    # Down to 4 m (or the bottom), then up, logging at each 0.5 m level.
    bottom = rules.pool_depth_m - rules.float_height_m + offset if touch_bottom else rules.max_depth_m + offset + 0.05
    while depth < bottom - 0.01:
        t += interval
        depth = min(bottom, depth + 0.4)
        samples.append((t, depth))
    skipped = {round(s, 3) for s in skip}
    for level in rules.required_depths()[1:]:
        t += 6.0
        if round(level, 3) not in skipped:
            samples.append((t, level + offset + rng.uniform(-0.08, 0.08)))
    return samples, t + interval


def simulate_run(rules: Rules = Rules(), company: str = 'EX01', start: str = '1:50:00',
                 profiles: int = 2, seed: int = 1, checksum: bool = True, **faults) -> List[str]:
    """Lines in arrival order: pre-dive packet, then each profile's log."""
    rng = random.Random(seed)
    h, m, s = (int(x) for x in start.split(':'))
    t = h * 3600 + m * 60 + s
    lines = [_line(company, t, rules.sensor_offset_m, rng, checksum)]
    t += 20
    for _ in range(profiles):
        samples, t = simulate_profile(rules, t, rng, **faults)
        lines += [_line(company, ts, d, rng, checksum) for ts, d in samples]
        t += 60  # transmit, then start the next profile
    return lines


def main():
    parser = argparse.ArgumentParser(description='Print a simulated float run, one packet per line.')
    parser.add_argument('--company', default='EX01')
    parser.add_argument('--drift', action='store_true', help='the hold leaves the 2.0 m range once')
    parser.add_argument('--touch-bottom', action='store_true')
    parser.add_argument('--skip', type=float, nargs='*', default=(), help='required depths to miss')
    args = parser.parse_args()
    for line in simulate_run(company=args.company, drift=args.drift,
                             touch_bottom=args.touch_bottom, skip=args.skip):
        print(line)


if __name__ == '__main__':
    main()
