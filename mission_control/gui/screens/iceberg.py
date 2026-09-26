"""Task 2.3 iceberg threat calculator: judge's sheet in, eight threat calls
and the required map out. The rules and geometry live in shared/iceberg.py.

Keyboard: Up/Down move between fields, Enter computes, Esc goes back. The
form is kept in a dict owned by the app, so leaving the screen by accident
does not lose what was typed.
"""
from __future__ import annotations

import math
import re
import tkinter as tk
from typing import Callable, Dict, List

import customtkinter as ctk

from shared import iceberg as ice

PLATFORM_NAMES = ('Hibernia', 'Sea Rose', 'Terra Nova', 'Hebron')
PLATFORM_FIELDS = ('lat', 'lon', 'depth')

# Practice only: approximate real-world positions and a scenario that
# exercises every rule. In the pool, type the judge's sheet instead.
PRACTICE = {
    'ice_lat': '47 00.0 N', 'ice_lon': '49 02.0 W', 'ice_heading': '135', 'ice_keel': '100',
    'Hibernia_lat': '46 45.0 N', 'Hibernia_lon': '48 47.0 W', 'Hibernia_depth': '80',
    'Sea Rose_lat': '46 47.4 N', 'Sea Rose_lon': '48 01.0 W', 'Sea Rose_depth': '120',
    'Terra Nova_lat': '46 28.5 N', 'Terra Nova_lon': '48 28.8 W', 'Terra Nova_depth': '95',
    'Hebron_lat': '46 32.7 N', 'Hebron_lon': '48 29.9 W', 'Hebron_depth': '93',
}

THREAT_COLOURS = {ice.GREEN: '#1e8449', ice.YELLOW: '#b7950b', ice.RED: '#c0392b'}
WARN_COLOUR = ('#b9770e', '#f5b041')
ERROR_COLOUR = ('#c0392b', '#e74c3c')
MAP_BG, MAP_INK, MAP_DIM = '#0e2a3d', '#ecf0f1', '#7f8c8d'


def _number(text: str, label: str) -> float:
    cleaned = re.sub(r'[\s°]|[mMtT]$', '', text.strip())
    try:
        return float(cleaned)
    except ValueError:
        raise ValueError(f'{label}: enter a number (got {text!r})') from None


class IcebergScreen(ctk.CTkScrollableFrame):
    def __init__(self, master, store: Dict[str, str], **kwargs) -> None:
        super().__init__(master, **kwargs)
        self._store = store
        self._vars: Dict[str, tk.StringVar] = {}
        self._entries: List[ctk.CTkEntry] = []
        self._result_cells: Dict[str, tuple] = {}
        self._last = None
        self._timers: List[str] = []

        ctk.CTkLabel(self, text='Task 2.3 — Iceberg threat assessment',
                     font=ctk.CTkFont(size=18, weight='bold')).pack(anchor='w', padx=12, pady=(10, 0))
        ctk.CTkLabel(
            self, justify='left', wraplength=620, text_color='gray', font=ctk.CTkFont(size=12),
            text=("Type the judge's sheet. Coordinates like 46 45.3 N, 46°45.3′N or -48.78.\n"
                  'Enter computes · ↑/↓ move between fields · Esc goes back.'),
        ).pack(anchor='w', padx=12, pady=(0, 6))

        iceberg = ctk.CTkFrame(self)
        iceberg.pack(fill='x', padx=12, pady=4)
        for column, (key, label, width) in enumerate((
                ('ice_lat', 'Iceberg latitude', 130), ('ice_lon', 'Longitude', 130),
                ('ice_heading', 'Heading (°)', 90), ('ice_keel', 'Keel depth (m)', 100))):
            ctk.CTkLabel(iceberg, text=label, font=ctk.CTkFont(size=12)).grid(
                row=0, column=column, padx=6, pady=(4, 0), sticky='w')
            self._entry(iceberg, key, width).grid(row=1, column=column, padx=6, pady=(0, 6))

        table = ctk.CTkFrame(self)
        table.pack(fill='x', padx=12, pady=4)
        for column, heading in enumerate(('Platform', 'Latitude', 'Longitude', 'Water (m)',
                                          'Closest', 'Surface', 'Subsea')):
            ctk.CTkLabel(table, text=heading, font=ctk.CTkFont(size=12, weight='bold')).grid(
                row=0, column=column, padx=4, pady=(4, 0), sticky='w')
        for row, name in enumerate(PLATFORM_NAMES, start=1):
            ctk.CTkLabel(table, text=name).grid(row=row, column=0, padx=4, sticky='w')
            for column, (field, width) in enumerate(zip(PLATFORM_FIELDS, (112, 112, 64)), start=1):
                self._entry(table, f'{name}_{field}', width).grid(row=row, column=column, padx=4, pady=3)
            closest = ctk.CTkLabel(table, text='—', width=60)
            surface = ctk.CTkLabel(table, text='—', width=62, corner_radius=6)
            subsea = ctk.CTkLabel(table, text='—', width=62, corner_radius=6)
            for column, cell in enumerate((closest, surface, subsea), start=4):
                cell.grid(row=row, column=column, padx=4, pady=3)
            self._result_cells[name] = (closest, surface, subsea)

        buttons = ctk.CTkFrame(self, fg_color='transparent')
        buttons.pack(fill='x', padx=12, pady=(6, 0))
        ctk.CTkButton(buttons, text='Compute (Enter)', width=140, command=self.compute).pack(side='left')
        practice = ctk.CTkButton(buttons, text='Load practice data', width=150, fg_color='gray30')
        practice.configure(command=lambda: self._two_step(practice, 'Load practice data', self._load_practice))
        practice.pack(side='left', padx=8)
        clear = ctk.CTkButton(buttons, text='Clear', width=80, fg_color='gray30')
        clear.configure(command=lambda: self._two_step(clear, 'Clear', self._clear))
        clear.pack(side='left')

        self._message = ctk.CTkLabel(self, text='', justify='left', wraplength=620,
                                     font=ctk.CTkFont(size=12))
        self._message.pack(anchor='w', padx=12, pady=(4, 2))

        self._map = tk.Canvas(self, height=240, bg=MAP_BG, highlightthickness=0)
        self._map.pack(fill='x', padx=12, pady=(0, 4))
        self._details = ctk.CTkLabel(self, text='', justify='left', wraplength=620,
                                     font=ctk.CTkFont(size=12), text_color=('gray20', 'gray80'))
        self._details.pack(anchor='w', padx=12, pady=(0, 10))
        self._map.bind('<Configure>', lambda event: self._last and self._draw_map(*self._last))

        self._later(100, self._entries[0].focus_set)
        if store.get('_computed'):
            self._later(150, self.compute)

    def _later(self, ms: int, callback: Callable[[], None]) -> None:
        self._timers.append(self.after(ms, callback))

    def destroy(self) -> None:
        for timer in self._timers:
            self.after_cancel(timer)
        super().destroy()

    # --- form ---------------------------------------------------------------
    def _entry(self, master, key: str, width: int) -> ctk.CTkEntry:
        var = tk.StringVar(value=self._store.get(key, ''))
        var.trace_add('write', lambda *_: self._on_edit(key, var))
        entry = ctk.CTkEntry(master, textvariable=var, width=width)
        self._vars[key] = var
        self._entries.append(entry)
        return entry

    def _on_edit(self, key: str, var: tk.StringVar) -> None:
        self._store[key] = var.get()
        if self._last is not None:  # never show calls computed from other inputs
            self._blank_results()
            self._message.configure(text='Inputs changed: press Enter to recompute.',
                                    text_color=WARN_COLOUR)

    def _blank_results(self) -> None:
        self._last = None
        self._store.pop('_computed', None)
        for closest, surface, subsea in self._result_cells.values():
            closest.configure(text='—')
            for cell in (surface, subsea):
                cell.configure(text='—', fg_color='transparent')
        self._map.delete('all')
        self._details.configure(text='')

    def move(self, delta: int) -> None:
        focused = self.focus_get()
        # CTkEntry focuses an inner tk.Entry; match on either.
        index = next((i for i, e in enumerate(self._entries)
                      if focused in (e, getattr(e, '_entry', None))), -1)
        self._entries[(index + delta) % len(self._entries)].focus_set()

    def _two_step(self, button: ctk.CTkButton, text: str, action: Callable[[], None]) -> None:
        """Overwriting typed data takes a second click within 3 s."""
        if not getattr(button, '_armed', False) and any(v.get().strip() for v in self._vars.values()):
            button._armed = True
            button.configure(text=f'{text}? Click again')
            self._later(3000, lambda: self._disarm(button, text))
            return
        self._disarm(button, text)
        action()

    @staticmethod
    def _disarm(button: ctk.CTkButton, text: str) -> None:
        button._armed = False
        button.configure(text=text)

    def _load_practice(self) -> None:
        for key, value in PRACTICE.items():
            self._vars[key].set(value)
        self.compute()
        self._message.configure(text='PRACTICE DATA (approximate real positions). '
                                     "Use the judge's sheet in competition.\n"
                                     + self._message.cget('text'))

    def _clear(self) -> None:
        for var in self._vars.values():
            var.set('')
        self._blank_results()
        self._message.configure(text='')
        self._entries[0].focus_set()

    # --- compute ------------------------------------------------------------
    def compute(self) -> None:
        value = lambda key: self._vars[key].get()
        try:
            iceberg = ice.Iceberg(ice.parse_coordinate(value('ice_lat'), 'lat'),
                                  ice.parse_coordinate(value('ice_lon'), 'lon'),
                                  _number(value('ice_heading'), 'Heading'),
                                  _number(value('ice_keel'), 'Keel depth'))
            platforms = [ice.Platform(name,
                                      ice.parse_coordinate(value(f'{name}_lat'), 'lat'),
                                      ice.parse_coordinate(value(f'{name}_lon'), 'lon'),
                                      _number(value(f'{name}_depth'), f'{name} water depth'))
                         for name in PLATFORM_NAMES]
            results = ice.assess(iceberg, platforms)
        except ValueError as exc:
            self._blank_results()
            self._message.configure(text=f'Cannot compute: {exc}', text_color=ERROR_COLOUR)
            return
        self._store['_computed'] = '1'

        for result in results:
            closest, surface, subsea = self._result_cells[result.platform.name]
            closest.configure(text=f'{result.closest_nm:.1f} nm')
            for cell, level in ((surface, result.surface), (subsea, result.subsea)):
                cell.configure(text=level.upper(), fg_color=THREAT_COLOURS[level], text_color='white')

        read_back = (f'Iceberg read as {ice.format_coordinate(iceberg.lat, "lat")} '
                     f'{ice.format_coordinate(iceberg.lon, "lon")}, heading {iceberg.heading_deg:g}°, '
                     f'keel {iceberg.keel_depth_m:g} m.')
        warnings = ice.spread_warnings(iceberg, platforms)
        warnings += [f'Check {r.platform.name}: {note}' for r in results for note in r.notes]
        self._message.configure(text='\n'.join(['⚠ ' + w for w in warnings] + [read_back]),
                                text_color=WARN_COLOUR if warnings else ('gray20', 'gray80'))
        self._details.configure(text='\n'.join(
            ['Map: squares show the surface threat; dashed rings are 5 nm (red) and 10 nm (yellow).'] + [
            f'{r.platform.name}: keel {r.keel_percent:.0f}% of {r.platform.water_depth_m:g} m. '
            f'Surface {r.surface}: {r.surface_reason}. Subsea {r.subsea}: {r.subsea_reason}.'
            for r in results]))
        self._last = (iceberg, results)
        self._draw_map(iceberg, results)

    # --- map ----------------------------------------------------------------
    def _draw_map(self, iceberg: ice.Iceberg, results: List[ice.Assessment]) -> None:
        canvas = self._map
        canvas.delete('all')
        width, height = max(canvas.winfo_width(), 200), max(canvas.winfo_height(), 150)

        lat0 = sum([iceberg.lat] + [r.platform.lat for r in results]) / (len(results) + 1)
        lon0 = sum([iceberg.lon] + [r.platform.lon for r in results]) / (len(results) + 1)
        east_nm_per_degree = 60 * math.cos(math.radians(lat0))

        def local(lat, lon):  # nautical miles east / north of the map centre
            return (lon - lon0) * east_nm_per_degree, (lat - lat0) * 60

        track_nm = max([r.along_track_nm for r in results] + [0.0]) + 8
        start = local(iceberg.lat, iceberg.lon)
        end = local(*ice.destination(iceberg.lat, iceberg.lon, iceberg.heading_deg, track_nm))
        spots = [local(r.platform.lat, r.platform.lon) for r in results]
        xs = [start[0], end[0]] + [x + d for x, _ in spots for d in (-10, 10)]
        ys = [start[1], end[1]] + [y + d for _, y in spots for d in (-10, 10)]
        margin = 18
        scale = min((width - 2 * margin) / (max(xs) - min(xs)),
                    (height - 2 * margin) / (max(ys) - min(ys)))
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2

        def px(point):
            return width / 2 + (point[0] - cx) * scale, height / 2 - (point[1] - cy) * scale

        for (x, y), result in zip(spots, results):
            for radius, colour in ((10, THREAT_COLOURS[ice.YELLOW]), (5, THREAT_COLOURS[ice.RED])):
                left, top = px((x - radius, y + radius))
                right, bottom = px((x + radius, y - radius))
                canvas.create_oval(left, top, right, bottom, outline=colour, dash=(3, 3))

        canvas.create_line(*px(start), *px(end), fill=MAP_INK, width=2, arrow=tk.LAST)
        for spot, result in zip(spots, results):
            p = result.platform
            if result.along_track_nm > 0:
                near = local(*ice.destination(iceberg.lat, iceberg.lon, iceberg.heading_deg,
                                              result.along_track_nm))
            else:
                near = start
            (x1, y1), (x2, y2) = px(near), px(spot)
            canvas.create_line(x1, y1, x2, y2, fill=MAP_DIM, dash=(2, 3))
            canvas.create_rectangle(x2 - 6, y2 - 6, x2 + 6, y2 + 6,
                                    fill=THREAT_COLOURS[result.surface], outline=MAP_INK)
            self._map_label(x2 + 9, y2, f'{p.name} · {result.closest_nm:.1f} nm', MAP_INK)

        sx, sy = px(start)
        canvas.create_polygon(sx, sy - 7, sx + 6, sy, sx, sy + 7, sx - 6, sy, fill='white')
        self._map_label(sx + 9, sy - 9, 'Iceberg', 'white')

        canvas.create_line(width - 24, 40, width - 24, 14, fill=MAP_INK, width=2, arrow=tk.LAST)
        canvas.create_text(width - 24, 50, text='N', fill=MAP_INK, font=('TkDefaultFont', 10, 'bold'))
        bar_nm = 10 if 10 * scale < width / 3 else 5
        canvas.create_line(12, 14, 12 + bar_nm * scale, 14, fill=MAP_INK, width=2)
        self._map_label(18 + bar_nm * scale, 14, f'{bar_nm} nm', MAP_INK, size=9)

    def _map_label(self, x: float, y: float, text: str, colour: str, size: int = 10) -> None:
        item = self._map.create_text(x, y, text=text, fill=colour, anchor='w',
                                     font=('TkDefaultFont', size, 'bold'))
        left, top, right, bottom = self._map.bbox(item)
        backing = self._map.create_rectangle(left - 2, top, right + 2, bottom, fill=MAP_BG, outline='')
        self._map.tag_lower(backing, item)
