"""Task 2.3 iceberg threat assessment, following the 2026 MATE Explorer rules.

Pure math with no GUI or ROS imports, so it can be unit tested: parse the
judge's coordinates, find where the iceberg's track passes each platform,
and grade the surface and subsea threat levels.

Distances are great-circle nautical miles on a sphere where one minute of
latitude is exactly 1 nm, as the manual says. A minute of longitude is only
cos(latitude) nm (about 0.69 nm on the Grand Banks), so treating it as a
full nautical mile overstates east-west distances by ~45%, which is enough
to flip a call.

Assumption to confirm against the manual: the iceberg keeps drifting along
its heading, so a platform's distance is the closest approach along that
track, or the current distance if the iceberg has already passed it.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math
import re
from typing import List, Sequence, Tuple

EARTH_RADIUS_NM = 10800 / math.pi  # one minute of arc is one nautical mile

SURFACE_RED_NM = 5.0       # closer than this: red
SURFACE_YELLOW_NM = 10.0   # up to this: yellow; beyond: green
SUBSEA_RANGE_NM = 25.0     # subsea assets only matter within this range
GROUNDING_PERCENT = 110    # keel >= 110% of water depth grounds first
BOUNDARY_MARGIN_NM = 0.25  # flag passes this close to a distance limit
MAX_SPREAD_NM = 150.0      # farther apart than this: probably a sign error

GREEN, YELLOW, RED = 'green', 'yellow', 'red'


@dataclass(frozen=True)
class Platform:
    name: str
    lat: float  # decimal degrees, north positive
    lon: float  # decimal degrees, east positive (the Grand Banks are negative)
    water_depth_m: float


@dataclass(frozen=True)
class Iceberg:
    lat: float
    lon: float
    heading_deg: float  # true direction the iceberg is drifting towards
    keel_depth_m: float


@dataclass(frozen=True)
class Assessment:
    platform: Platform
    distance_now_nm: float
    closest_nm: float
    along_track_nm: float  # how far the iceberg drifts to its closest point
    keel_percent: float    # keel depth as a percentage of water depth
    surface: str
    surface_reason: str
    subsea: str
    subsea_reason: str
    notes: Tuple[str, ...]  # near-boundary cases worth a second look


# --- coordinates ---------------------------------------------------------------


def parse_coordinate(text: str, axis: str) -> float:
    """Decimal degrees from e.g. "46°45.3'N", '46 45 18 N', 'W48 46.9', '-48.78'.

    `axis` is 'lat' or 'lon'. North and east are positive. Accepts degrees,
    degrees + minutes, or degrees + minutes + seconds, with either a leading
    minus sign or a hemisphere letter (not both).
    """
    if axis not in ('lat', 'lon'):
        raise ValueError("axis must be 'lat' or 'lon'")
    name = 'latitude' if axis == 'lat' else 'longitude'
    raw = text.strip().upper()
    if not raw:
        raise ValueError(f'Enter a {name}')
    letters = re.findall(r'[A-Z]', raw)
    allowed = 'NS' if axis == 'lat' else 'EW'
    if len(letters) > 1 or any(letter not in allowed for letter in letters):
        raise ValueError(f'{text!r}: use {allowed[0]} or {allowed[1]} for {name}')
    negative = raw.startswith('-')
    if negative and letters:
        raise ValueError(f'{text!r}: use a minus sign or a hemisphere letter, not both')
    cleaned = re.sub(r"[°º'\"′″:NSEW+\-]", ' ', raw)
    parts = cleaned.split()
    if not 1 <= len(parts) <= 3 or not all(re.fullmatch(r'\d+(\.\d+)?', p) for p in parts):
        raise ValueError(f'{text!r}: expected degrees, degrees minutes, or degrees minutes seconds')
    if any('.' in p for p in parts[:-1]):
        raise ValueError(f'{text!r}: only the last number may have decimals')
    degrees, minutes, seconds = ([float(p) for p in parts] + [0.0, 0.0])[:3]
    if minutes >= 60 or seconds >= 60:
        raise ValueError(f'{text!r}: minutes and seconds must be below 60')
    value = degrees + minutes / 60 + seconds / 3600
    limit = 90 if axis == 'lat' else 180
    if value > limit:
        raise ValueError(f'{text!r}: {name} must be within {limit}°')
    return -value if negative or (letters and letters[0] in 'SW') else value


def format_coordinate(value: float, axis: str) -> str:
    """46.755, 'lat' -> "46°45.30′N" (degrees and decimal minutes)."""
    hemisphere = ('N' if value >= 0 else 'S') if axis == 'lat' else ('E' if value >= 0 else 'W')
    total_minutes = round(abs(value) * 60, 2)
    degrees, minutes = divmod(total_minutes, 60)
    return f'{int(degrees)}°{minutes:05.2f}′{hemisphere}'


# --- geometry ------------------------------------------------------------------


def _angle_and_bearing(lat1, lon1, lat2, lon2):
    """Central angle (radians) and initial bearing (radians) from point 1 to 2."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    h = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2)
    angle = 2 * math.asin(min(1.0, math.sqrt(h)))
    bearing = math.atan2(math.sin(dlon) * math.cos(p2),
                         math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dlon))
    return angle, bearing


def distance_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return _angle_and_bearing(lat1, lon1, lat2, lon2)[0] * EARTH_RADIUS_NM


def destination(lat: float, lon: float, bearing_deg: float, dist_nm: float) -> Tuple[float, float]:
    """Point reached by travelling dist_nm from (lat, lon) on an initial bearing."""
    p1, l1 = math.radians(lat), math.radians(lon)
    b, d = math.radians(bearing_deg), dist_nm / EARTH_RADIUS_NM
    p2 = math.asin(math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(b))
    l2 = l1 + math.atan2(math.sin(b) * math.sin(d) * math.cos(p1),
                         math.cos(d) - math.sin(p1) * math.sin(p2))
    return math.degrees(p2), (math.degrees(l2) + 540) % 360 - 180


def track_pass(iceberg: Iceberg, lat: float, lon: float) -> Tuple[float, float, float]:
    """(closest_nm, along_track_nm, distance_now_nm) for a point off the track."""
    angle, bearing = _angle_and_bearing(iceberg.lat, iceberg.lon, lat, lon)
    now = angle * EARTH_RADIUS_NM
    offset = bearing - math.radians(iceberg.heading_deg)
    if math.cos(offset) <= 0 or angle == 0:
        return now, 0.0, now  # already abeam or behind: it only gets farther
    cross = math.asin(max(-1.0, min(1.0, math.sin(angle) * math.sin(offset))))
    along = math.acos(max(-1.0, min(1.0, math.cos(angle) / math.cos(cross))))
    return abs(cross) * EARTH_RADIUS_NM, along * EARTH_RADIUS_NM, now


# --- threat rules --------------------------------------------------------------


def _keel_at_least(keel_m: float, water_m: float, percent: int) -> bool:
    # Exact decimal comparison: 99 m over 90 m must count as 110%, not 109.99...%.
    return Fraction(str(keel_m)) * 100 >= Fraction(str(water_m)) * percent


def surface_threat(closest_nm: float, keel_m: float, water_m: float) -> Tuple[str, str]:
    if _keel_at_least(keel_m, water_m, GROUNDING_PERCENT):
        return GREEN, 'keel ≥110% of water depth: grounds before reaching it'
    if closest_nm > SURFACE_YELLOW_NM:
        return GREEN, 'passes more than 10 nm away'
    if closest_nm >= SURFACE_RED_NM:
        return YELLOW, 'passes 5–10 nm away'
    return RED, 'passes within 5 nm'


def subsea_threat(closest_nm: float, keel_m: float, water_m: float) -> Tuple[str, str]:
    if closest_nm > SUBSEA_RANGE_NM:
        return GREEN, 'never comes within 25 nm'
    if _keel_at_least(keel_m, water_m, GROUNDING_PERCENT):
        return GREEN, 'keel ≥110% of water depth: grounds first'
    if _keel_at_least(keel_m, water_m, 90):
        return RED, 'keel 90–110% of water depth: critical danger'
    if _keel_at_least(keel_m, water_m, 70):
        return YELLOW, 'keel 70–90% of water depth: may impact the seafloor'
    return GREEN, 'keel below 70% of water depth: safe clearance'


def _boundary_notes(closest_nm: float, keel_m: float, water_m: float) -> Tuple[str, ...]:
    notes = [f'passes within {BOUNDARY_MARGIN_NM:g} nm of the {limit:g} nm limit'
             for limit in (SURFACE_RED_NM, SURFACE_YELLOW_NM, SUBSEA_RANGE_NM)
             if abs(closest_nm - limit) <= BOUNDARY_MARGIN_NM]
    notes += [f'keel is exactly {percent}% of water depth' for percent in (70, 90, 110)
              if Fraction(str(keel_m)) * 100 == Fraction(str(water_m)) * percent]
    return tuple(notes)


def assess(iceberg: Iceberg, platforms: Sequence[Platform]) -> List[Assessment]:
    if not 0 <= iceberg.heading_deg <= 360:
        raise ValueError('Heading must be between 0 and 360 degrees')
    if iceberg.keel_depth_m <= 0:
        raise ValueError('Keel depth must be positive')
    results = []
    for platform in platforms:
        if platform.water_depth_m <= 0:
            raise ValueError(f'{platform.name}: water depth must be positive')
        closest, along, now = track_pass(iceberg, platform.lat, platform.lon)
        keel, water = iceberg.keel_depth_m, platform.water_depth_m
        surface, surface_reason = surface_threat(closest, keel, water)
        subsea, subsea_reason = subsea_threat(closest, keel, water)
        results.append(Assessment(platform, now, closest, along, 100 * keel / water,
                                  surface, surface_reason, subsea, subsea_reason,
                                  _boundary_notes(closest, keel, water)))
    return results


def spread_warnings(iceberg: Iceberg, platforms: Sequence[Platform]) -> List[str]:
    """Catch the classic slip of dropping a W or S from one coordinate."""
    return [f'{p.name} is {d:.0f} nm from the iceberg: check N/S and E/W'
            for p in platforms
            if (d := distance_nm(iceberg.lat, iceberg.lon, p.lat, p.lon)) > MAX_SPREAD_NM]
