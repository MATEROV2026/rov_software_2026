"""MATE Floats! 2027 station: receive the float's packets, check them against
the scoring rules, and graph temperature and light against depth.

    cd float_station && .venv/bin/python app.py

Packets come from a serial radio receiver, a saved log, or the simulator.
Only packets with this team's company number are shown; MATE says the
station must not show anyone else's transmissions.
"""
from __future__ import annotations

import queue
import threading
from tkinter import filedialog
from typing import Dict, List, Optional

import customtkinter as ctk
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
import serial  # noqa: E402
from serial.tools import list_ports  # noqa: E402

from packets import Packet, format_packet, parse_packet  # noqa: E402
from profile import ProfileCheck, Rules, check_profile, split_profiles, unique_in_order  # noqa: E402
from simulator import simulate_run  # noqa: E402

GOOD, BAD, WARN, DIM = '#2ecc71', '#e74c3c', '#f5b041', '#8c8c8c'
SETTINGS = (('company', 'Company', 'EX01', 70), ('offset', 'Sensor below top (m)', '0.00', 60),
            ('mate_temp', "MATE's temperature (°C)", '', 60), ('hold', 'Hold depth (m)', '2.0', 50),
            ('deepest', 'Max depth (m)', '4.0', 50), ('pool', 'Pool depth (m)', '5.18', 55))


class SerialReader(threading.Thread):
    """Reads lines from the radio receiver into a queue, off the GUI thread."""

    def __init__(self, port: str, baud: int, out: queue.Queue) -> None:
        super().__init__(daemon=True)
        self.port, self.baud, self.out = port, baud, out
        self.stopping = threading.Event()

    def run(self) -> None:
        try:
            with serial.Serial(self.port, self.baud, timeout=0.3) as link:
                self.out.put(('status', f'Listening on {self.port} at {self.baud} baud'))
                pending = b''
                while not self.stopping.is_set():
                    pending += link.read(512)
                    *lines, pending = pending.split(b'\n')
                    for line in lines:
                        if line.strip():
                            self.out.put(('line', line.decode('utf-8', 'replace').strip()))
        except (OSError, serial.SerialException) as exc:
            self.out.put(('status', f'Serial {self.port}: {exc}'))


class FloatStation(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title('MATE Floats! station')
        self.geometry('1180x820')
        ctk.set_appearance_mode('dark')
        self.incoming: queue.Queue = queue.Queue()
        self.raw: List[str] = []       # every line received, in order (the audit trail)
        self.feed: List[str] = []      # simulated / file lines still to deliver
        self.reader: Optional[SerialReader] = None
        self.checks: List[ProfileCheck] = []
        self.vars: Dict[str, ctk.StringVar] = {}
        self._build()
        self._analyse()
        self.after(100, self._poll)

    # --- layout -----------------------------------------------------------------
    def _build(self) -> None:
        settings = ctk.CTkFrame(self)
        settings.pack(fill='x', padx=10, pady=(10, 4))
        for column, (key, label, default, width) in enumerate(SETTINGS):
            ctk.CTkLabel(settings, text=label, font=ctk.CTkFont(size=12)).grid(
                row=0, column=column, padx=6, sticky='w')
            var = ctk.StringVar(value=default)
            var.trace_add('write', lambda *_: self._analyse())
            ctk.CTkEntry(settings, textvariable=var, width=width).grid(row=1, column=column, padx=6, pady=(0, 6))
            self.vars[key] = var

        sources = ctk.CTkFrame(self, fg_color='transparent')
        sources.pack(fill='x', padx=10)
        ctk.CTkButton(sources, text='Simulate run', width=110, command=self._simulate).pack(side='left')
        ctk.CTkButton(sources, text='Open log…', width=90, command=self._open_log).pack(side='left', padx=6)
        ports = [p.device for p in list_ports.comports()] or ['(no serial ports)']
        self.port = ctk.CTkOptionMenu(sources, values=ports, width=190)
        self.port.pack(side='left', padx=(18, 4))
        self.baud = ctk.CTkEntry(sources, width=70)
        self.baud.insert(0, '115200')
        self.baud.pack(side='left')
        self.listen = ctk.CTkButton(sources, text='Listen', width=80, command=self._toggle_serial)
        self.listen.pack(side='left', padx=6)
        for text, command in (('Clear', self._clear), ('Save log…', self._save_log),
                              ('Save graphs…', self._save_graphs)):
            ctk.CTkButton(sources, text=text, width=96, fg_color='gray30', command=command).pack(side='right', padx=3)
        self.status = ctk.CTkLabel(self, text='', anchor='w', text_color=DIM, font=ctk.CTkFont(size=12))
        self.status.pack(fill='x', padx=14)

        middle = ctk.CTkFrame(self, fg_color='transparent')
        middle.pack(fill='both', expand=True, padx=10, pady=4)
        self.log = ctk.CTkTextbox(middle, width=700, font=ctk.CTkFont(family='Menlo', size=12), wrap='none')
        self.log.pack(side='left', fill='both', expand=True)
        self.checklist = ctk.CTkTextbox(middle, width=440, font=ctk.CTkFont(family='Menlo', size=12))
        self.checklist.pack(side='left', fill='y', padx=(8, 0))
        for box in (self.log, self.checklist):
            for tag, colour in (('good', GOOD), ('bad', BAD), ('warn', WARN), ('dim', DIM)):
                box.tag_config(tag, foreground=colour)

        graphs = ctk.CTkFrame(self)
        graphs.pack(fill='x', padx=10, pady=(4, 10))
        self.profile_choice = ctk.CTkSegmentedButton(graphs, values=['Profile 1'],
                                                     command=lambda _: self._draw_graphs())
        self.profile_choice.set('Profile 1')
        self.profile_choice.pack(anchor='w', padx=8, pady=(6, 0))
        self.figure = Figure(figsize=(11.4, 2.9), dpi=100, facecolor='#2b2b2b')
        self.canvas = FigureCanvasTkAgg(self.figure, master=graphs)
        self.canvas.get_tk_widget().pack(fill='x', padx=6, pady=6)

    # --- input --------------------------------------------------------------------
    def _poll(self) -> None:
        changed = False
        for _ in range(4):  # deliver simulated / file lines a few at a time, like a radio
            if self.feed:
                self.raw.append(self.feed.pop(0))
                changed = True
        while not self.incoming.empty():
            kind, text = self.incoming.get_nowait()
            if kind == 'line':
                self.raw.append(text)
                changed = True
            else:
                self.status.configure(text=text)
        if changed:
            self._analyse()
        self.after(100, self._poll)

    def _simulate(self) -> None:
        self.feed += simulate_run(self._rules(), company=self.vars['company'].get().strip() or 'EX01')

    def _open_log(self) -> None:
        path = filedialog.askopenfilename(title='Float log', filetypes=[('Text', '*.txt *.log'), ('All', '*')])
        if path:
            with open(path, encoding='utf-8', errors='replace') as handle:
                self.feed += [line.strip() for line in handle if line.strip()]

    def _toggle_serial(self) -> None:
        if self.reader is not None:
            self.reader.stopping.set()
            self.reader = None
            self.listen.configure(text='Listen')
            self.status.configure(text='Stopped listening')
            return
        try:
            baud = int(self.baud.get())
        except ValueError:
            self.status.configure(text='Baud rate must be a whole number')
            return
        self.reader = SerialReader(self.port.get(), baud, self.incoming)
        self.reader.start()
        self.listen.configure(text='Stop')

    def _clear(self) -> None:
        self.raw, self.feed = [], []
        self._analyse()

    def _save_log(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension='.txt', initialfile='float_log.txt')
        if path:
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write('\n'.join(self.raw) + '\n')

    def _save_graphs(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension='.png', initialfile='float_graphs.png')
        if path:
            self.figure.savefig(path, facecolor=self.figure.get_facecolor(), dpi=150)

    # --- analysis -----------------------------------------------------------------
    def _rules(self) -> Rules:
        def number(key, default):
            try:
                return float(self.vars[key].get())
            except (KeyError, ValueError):
                return default
        return Rules(sensor_offset_m=number('offset', 0.0), hold_depth_m=number('hold', 2.0),
                     max_depth_m=number('deepest', 4.0), pool_depth_m=number('pool', 5.18))

    def _analyse(self) -> None:
        if not hasattr(self, 'log'):
            return
        rules = self._rules()
        company = self.vars['company'].get().strip().upper()
        try:
            mate_temperature = float(self.vars['mate_temp'].get())
        except ValueError:
            mate_temperature = None
        ours, rejected, others = [], 0, 0
        for line in self.raw:
            try:
                packet = parse_packet(line)
            except ValueError:
                rejected += 1
                continue
            if packet.company != company:
                others += 1
                continue
            ours.append(packet)
        ours = unique_in_order(ours)
        pre_dive, dives = split_profiles(ours, rules)
        self.checks = [check_profile(dive, rules, mate_temperature) for dive in dives]
        if self.reader is None:
            self.status.configure(text=f'{len(ours)} packets from {company or "?"}  ·  '
                                       f'{others} from other teams ignored  ·  {rejected} unreadable lines')
        self._show_log(ours, pre_dive, dives)
        self._show_checklist(pre_dive, mate_temperature)
        names = [f'Profile {i + 1}' for i in range(max(1, len(self.checks)))]
        current = self.profile_choice.get()
        self.profile_choice.configure(values=names)
        self.profile_choice.set(current if current in names else names[-1])
        self._draw_graphs()

    def _show_log(self, ours: List[Packet], pre_dive: Optional[Packet], dives) -> None:
        notes: Dict[int, str] = {}
        if pre_dive is not None:
            notes[id(pre_dive)] = "pre-dive (Mic'd Up)"
        headers: Dict[int, int] = {}
        claimed = set()
        for number, (dive, check) in enumerate(zip(dives, self.checks), start=1):
            first = dive[1] if id(dive[0]) in claimed and len(dive) > 1 else dive[0]
            headers[id(first)] = number
            claimed.update(id(p) for p in dive)
            if check.hold:
                for n, i in enumerate(range(check.hold[0], check.hold[1] + 1), start=1):
                    notes[id(dive[i])] = f'hold {n}/{check.rules.hold_packets}'
            for depth, i in check.samples.items():
                if i is not None:
                    notes[id(dive[i])] = (notes.get(id(dive[i])) + ', ' if id(dive[i]) in notes else '') \
                        + f'{depth:.1f} m sample'
        self.log.configure(state='normal')
        self.log.delete('1.0', 'end')
        self.log.insert('end', f"{'#':>3}  {'packet as received':<62}note\n", 'dim')
        for n, packet in enumerate(ours, start=1):
            if id(packet) in headers:
                self.log.insert('end', f'     ── profile {headers[id(packet)]} ──\n', 'dim')
            note = notes.get(id(packet), '')
            self.log.insert('end', f'{n:>3}  {format_packet(packet):<62}')
            self.log.insert('end', note + '\n', 'good' if note else None)
        if not ours:
            self.log.insert('end', '\n  Waiting for packets: Listen on the radio, Open log…, or Simulate run.\n', 'dim')
        self.log.configure(state='disabled')
        self.log.see('end')

    def _show_checklist(self, pre_dive: Optional[Packet], mate_temperature: Optional[float]) -> None:
        box = self.checklist
        box.configure(state='normal')
        box.delete('1.0', 'end')

        def row(label: str, ok: Optional[bool], points: str = '', detail: str = '') -> None:
            mark, tag = {True: ('✓', 'good'), False: ('✗', 'bad'), None: ('?', 'warn')}[ok]
            box.insert('end', f' {mark} ', tag)
            box.insert('end', f'{label:<31}{points:>4}\n')
            if detail:
                box.insert('end', f'     {detail}\n', 'dim')

        total = (5 if pre_dive else 0) + sum(check.points() for check in self.checks)
        box.insert('end', f"{'Total so far (graphs not included)':<35}{total:>4}\n\n")
        row("Pre-dive packet (Mic'd Up)", pre_dive is not None, '5' if pre_dive else '0',
            pre_dive.time_text if pre_dive else 'none yet')
        for number, check in enumerate(self.checks, start=1):
            rules = check.rules
            box.insert('end', f'\nProfile {number}\n')
            row(f'Reached {rules.max_depth_m:g} m and surfaced', check.completed,
                '10' if check.completed else '0', f'deepest {check.deepest_m:.2f} m (top of float)')
            row('At least 10 packets', check.enough_packets,
                '5' if check.completed and check.enough_packets else '0', f'{len(check.packets)} received')
            hold_detail = (f'packets {check.packets[check.hold[0]].time_text} to '
                           f'{check.packets[check.hold[1]].time_text}' if check.hold else
                           f'need 7 in a row, 5 s apart, {rules.hold_depth_m - rules.hold_tolerance_m:.2f}'
                           f'–{rules.hold_depth_m + rules.hold_tolerance_m:.2f} m')
            row(f'Hold {rules.hold_depth_m:g} m for 30 s', check.hold is not None,
                '5' if check.completed and check.hold else '0', hold_detail)
            missing = [f'{d:g}' for d, i in check.samples.items() if i is None]
            temp_ok = check.temperatures_ok
            sensor_detail = (f'missing {", ".join(missing)} m' if missing else
                             'enter MATE\'s temperature to check' if temp_ok is None else
                             f'all {len(check.samples)} depths, within 2 °C of {mate_temperature:g} °C'
                             if temp_ok else f'a temperature is more than 2 °C from {mate_temperature:g} °C')
            row('Temperature and light, every 0.5 m', None if (not missing and temp_ok is None) else check.sensors_ok,
                '5' if check.completed and check.sensors_ok else '0', sensor_detail)
            row('Stayed off the bottom', not check.touched_bottom, '-5' if check.touched_bottom else '',
                'likely touched: float may have reached the bottom' if check.touched_bottom else '')
            box.insert('end', f"{'':<5}{'profile points':<29}{check.points():>4}\n")
        box.configure(state='disabled')

    def _draw_graphs(self) -> None:
        self.figure.clear()
        index = int(self.profile_choice.get().split()[-1]) - 1
        check = self.checks[index] if 0 <= index < len(self.checks) else None
        axes = [self.figure.add_subplot(1, 2, i) for i in (1, 2)]
        unit = 'V'
        for ax in axes:
            ax.set_facecolor('#1f1f1f')
            ax.tick_params(colors='#dddddd')
            for spine in ax.spines.values():
                spine.set_color('#666666')
            ax.grid(True, color='#444444', linewidth=0.6)
        if check is None or not any(i is not None for i in check.samples.values()):
            for ax in axes:
                ax.text(0.5, 0.5, 'Waiting for a profile', ha='center', va='center',
                        color='#999999', transform=ax.transAxes)
        else:
            chosen = sorted((check.rules.top(check.packets[i]), check.packets[i])
                            for i in check.samples.values() if i is not None)
            depths = [d for d, _ in chosen]
            unit = chosen[0][1].light_unit
            axes[0].plot([p.temperature_c for _, p in chosen], depths, 'o-', color='#5dade2')
            axes[1].plot([p.light for _, p in chosen], depths, 'o-', color='#f5b041')
            missing = [f'{d:g}' for d, i in check.samples.items() if i is None]
            if missing:
                for ax in axes:
                    ax.text(0.98, 0.04, f'missing {", ".join(missing)} m', ha='right', color=BAD,
                            transform=ax.transAxes)
        number = index + 1
        for ax, xlabel, title in ((axes[0], 'Temperature (°C)', f'Temperature vs depth, profile {number}'),
                                  (axes[1], f'Light ({unit})', f'Light vs depth, profile {number}')):
            ax.set_xlabel(xlabel, color='#dddddd')
            ax.set_ylabel('Depth (m)', color='#dddddd')
            ax.set_title(title, color='#ffffff', fontsize=11)
            ax.invert_yaxis()  # surface at the top, like the water column
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def destroy(self) -> None:
        if self.reader is not None:
            self.reader.stopping.set()
        super().destroy()


if __name__ == '__main__':
    FloatStation().mainloop()
