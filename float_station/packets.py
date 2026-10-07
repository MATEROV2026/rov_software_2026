"""Data packets from the float: MATE Floats! 2027's "defined data packet".

MATE's example:  EX01 1:51:42 UTC 9.8 kpa  1.00 meters 23.6oC  0.546 V

MATE fixes WHAT is sent (company number, time, pressure and/or depth,
temperature, light) but not HOW. `parse_packet` reads that style with the
usual unit spellings, and `format_packet` renders packets the same way for
the judge's screen. An optional NMEA-style "*HH" checksum at the end lets
the station drop lines garbled by radio noise.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional

GRAVITY = 9.80665        # m/s^2
POOL_WATER = 1000.0      # kg/m^3; fresh water, matching MATE's 9.8 kPa = 1.00 m example


@dataclass(frozen=True)
class Packet:
    company: str
    time_s: float               # seconds since midnight, or on the float's own clock
    time_text: str              # as sent, e.g. "1:51:42 UTC"
    pressure_kpa: Optional[float]
    depth_m: float              # pressure-sensor depth (sent, or derived from pressure)
    temperature_c: float
    light: float
    light_unit: str
    raw: str


_COMPANY = re.compile(r'^\s*([A-Z]{2}\d{1,3})\b')
_TIME = re.compile(r'\b(\d{1,2}):(\d{2}):(\d{2}(?:\.\d+)?)(\s*(?:UTC|local))?', re.IGNORECASE)
_SECONDS = re.compile(r'\bT\+?(\d+(?:\.\d+)?)\s*s\b', re.IGNORECASE)
_PRESSURE = re.compile(r'(-?\d+(?:\.\d+)?)\s*(kpa|pa)\b', re.IGNORECASE)
_DEPTH = re.compile(r'(-?\d+(?:\.\d+)?)\s*(meters?|metres?|cm|m)\b', re.IGNORECASE)
_TEMPERATURE = re.compile(r'(-?\d+(?:\.\d+)?)\s*(?:°|º|o|deg)?\s*C\b')
_LIGHT = re.compile(r'(-?\d+(?:\.\d+)?)\s*(mV|V|lux|lx|W/m2|W/m²|counts?|ohms?|kohms?|Ω|kΩ|mA|uA)(?=\s|$)',
                    re.IGNORECASE)


def nmea_checksum(text: str) -> str:
    value = 0
    for char in text:
        value ^= ord(char)
    return f'{value:02X}'


def _take(pattern: re.Pattern, text: str):
    """First match, plus the text with that span blanked so no value is read twice."""
    match = pattern.search(text)
    if not match:
        return None, text
    return match, text[:match.start()] + ' ' * (match.end() - match.start()) + text[match.end():]


def parse_packet(line: str) -> Packet:
    raw = line.strip()
    body = raw
    if '*' in raw:
        body, _, checksum = raw.rpartition('*')
        if nmea_checksum(body) != checksum.strip().upper():
            raise ValueError(f'checksum mismatch: {raw!r}')

    company, rest = _take(_COMPANY, body)
    if not company:
        raise ValueError(f'no company number (like EX01) at the start: {raw!r}')
    clock, rest = _take(_TIME, rest)
    if clock:
        hours, minutes, seconds, zone = clock.groups()
        time_s = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        time_text = f'{hours}:{minutes}:{seconds}{(zone or "").upper().replace("LOCAL", "local")}'
    else:
        elapsed, rest = _take(_SECONDS, rest)
        if not elapsed:
            raise ValueError(f'no time (like 1:51:42 UTC or T+123s): {raw!r}')
        time_s, time_text = float(elapsed.group(1)), elapsed.group(0)

    pressure, rest = _take(_PRESSURE, rest)
    pressure_kpa = None
    if pressure:
        pressure_kpa = float(pressure.group(1)) / (1000.0 if pressure.group(2).lower() == 'pa' else 1.0)
    depth, rest = _take(_DEPTH, rest)
    if depth:
        depth_m = float(depth.group(1)) / (100.0 if depth.group(2).lower() == 'cm' else 1.0)
    elif pressure_kpa is not None:
        depth_m = pressure_kpa * 1000.0 / (POOL_WATER * GRAVITY)  # gauge pressure
    else:
        raise ValueError(f'no depth or pressure: {raw!r}')
    temperature, rest = _take(_TEMPERATURE, rest)
    if not temperature:
        raise ValueError(f'no temperature (like 23.6°C): {raw!r}')
    light, rest = _take(_LIGHT, rest)
    if not light:
        raise ValueError(f'no light reading with a unit (like 0.546 V): {raw!r}')

    return Packet(company.group(1), time_s, time_text, pressure_kpa, depth_m,
                  float(temperature.group(1)), float(light.group(1)), light.group(2), raw)


def format_packet(packet: Packet) -> str:
    """MATE's display style: EX01 1:51:42 UTC 9.8 kpa  1.00 meters 23.6°C  0.546 V"""
    pressure = f'{packet.pressure_kpa:.1f} kpa  ' if packet.pressure_kpa is not None else ''
    return (f'{packet.company} {packet.time_text} {pressure}{packet.depth_m:.2f} meters '
            f'{packet.temperature_c:.1f}°C  {packet.light:g} {packet.light_unit}')
