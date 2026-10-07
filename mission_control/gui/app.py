"""Mission desktop; HTTP work runs off the Tk thread, with vehicle feedback."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import queue
import sys

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import customtkinter as ctk

from gui import api as api_mod
from gui.controller import build_mission_input
from gui.screens.home import HomeScreen
from gui.screens.iceberg import IcebergScreen
from gui.screens.task_detail import TaskDetailScreen
from gui.screens.task_menu import TaskMenuScreen
from gui.screens.thrusters import ThrusterScreen
from gui.screens.upload_screen import UploadScreen


class MissionApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('Matrov — Mission Control')
        self.geometry('680x760')
        ctk.set_appearance_mode('dark')
        self._state, self._screen = 'home', None
        self._tasks, self._current_task = [], {}
        self._uploads = {}
        self._iceberg_form = {}  # survives leaving the calculator screen
        self._vehicle_armed = None
        self._closing = False
        self._destroyed = False
        self._pending = set()
        self._results = queue.Queue()
        self._workers = ThreadPoolExecutor(max_workers=3, thread_name_prefix='gui-http')
        # Ordered control requests prevent a delayed arm from overtaking stop/close.
        self._control_worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix='gui-control')
        self._container = ctk.CTkFrame(self)
        self._container.pack(fill='both', expand=True)
        self._footer = ctk.CTkFrame(self)
        self._footer.pack(fill='x', side='bottom')
        self._backend_lbl = ctk.CTkLabel(self._footer, text='Vehicle: checking…')
        self._backend_lbl.pack(fill='x')
        self._sensor_lbl = ctk.CTkLabel(self._footer, text='Sensors: waiting for data')
        self._sensor_lbl.pack(fill='x')
        self._mission_lbl = ctk.CTkLabel(self._footer, text='Mission: idle', wraplength=640)
        self._mission_lbl.pack(fill='x')
        self._input_lbl = ctk.CTkLabel(self._footer, text='', wraplength=640)
        self._input_lbl.pack(fill='x')
        self._controller = build_mission_input(self)
        self._show_home()
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        self.bind_all('<Escape>', self._escape, add=True)
        self.after(40, self._drain_results)
        self.after(50, self._input_tick)
        self._check_backend()

    def _submit(self, work, done, failed=None, key=None, control=False):
        if key and key in self._pending:
            return
        if key:
            self._pending.add(key)
        pool = self._control_worker if control else self._workers
        future = pool.submit(work)
        future.add_done_callback(lambda result: self._results.put((result, done, failed, key)))

    def _drain_results(self):
        while not self._results.empty():
            future, done, failed, key = self._results.get_nowait()
            self._pending.discard(key)
            try:
                value = future.result()
            except Exception as exc:
                (failed or self._toast)(str(exc))
            else:
                done(value)
            if self._destroyed:
                return
        self.after(40, self._drain_results)

    def _check_backend(self):
        if self._closing:
            return
        self._submit(lambda: api_mod.send_command({'command': 'get_status'}),
                     self._receive_status, self._status_error, key='status')
        self.after(1000, self._check_backend)

    def _status_error(self, detail):
        self._vehicle_armed = None
        self._backend_lbl.configure(text=f'Vehicle: UNKNOWN — {detail[:100]}')
        self._sensor_lbl.configure(text='Sensors: telemetry unavailable')
        if isinstance(self._screen, ThrusterScreen):
            self._screen.set_status(None, 'No fresh vehicle acknowledgment')

    def _receive_status(self, result):
        if not result.get('connected') or result.get('control') is None:
            self._status_error(result.get('detail', 'No fresh vehicle heartbeat'))
            return
        state = result['control']
        self._vehicle_armed = state['armed']
        label = 'ARMED' if state['armed'] else 'DISARMED'
        if state.get('inhibited'):
            label += ' — actuation inhibited'
        if not state.get('serial_connected'):
            label += ' — serial unavailable'
        self._backend_lbl.configure(text=f'Vehicle: {label}')
        ages = result.get('sensors', {})
        self._sensor_lbl.configure(text=' | '.join(
            f'{name}: ' + ('live' if ages.get(name, float('inf')) < 2 else 'no fresh data')
            for name in ('camera', 'imu', 'pressure', 'zed')))

        if result.get('mission_status'):
            self._mission_lbl.configure(text='Mission: ' + result['mission_status'])
        if isinstance(self._screen, ThrusterScreen):
            self._screen.set_status(state['armed'], state.get('reason', ''))

    def _clear_screen(self):
        if self._screen is not None:
            self._screen.destroy()
        self._screen = None

    def _mount(self, state, screen_class, *args):
        self._clear_screen()
        self._state = state
        self._screen = screen_class(self._container, *args)
        self._screen.pack(fill='both', expand=True)

    def _show_home(self):
        self._mount('home', HomeScreen)

    def _show_menu(self):
        self._clear_screen()
        self._state = 'menu'
        loading = ctk.CTkLabel(self._container, text='Loading tasks… (Esc to go back)')
        self._screen = loading
        loading.pack(expand=True)

        def loaded(tasks):
            if self._screen is loading:
                self._tasks = tasks
                self._mount('menu', TaskMenuScreen, tasks)
        self._submit(api_mod.get_tasks, loaded, self._toast)

    def _show_detail(self, task):
        self._current_task = task
        self._mount('detail', TaskDetailScreen, task)

    def _show_thrusters(self):
        self._mount('thrusters', ThrusterScreen)

    def _show_upload(self, task_id):
        self._mount('upload', UploadScreen, task_id)

    def _show_iceberg(self):
        self._mount('iceberg', IcebergScreen, self._iceberg_form)

    def _input_tick(self):
        if self._closing:
            return
        try:
            # Once armed, sticks/buttons belong exclusively to vehicle control.
            allow_joy = self._vehicle_armed is False and 'control' not in self._pending
            for event in self._controller.poll(allow_joystick=allow_joy):
                self._dispatch_nav(event)
            self._input_lbl.configure(text=self._controller.status_hint())
        except Exception as exc:
            self._input_lbl.configure(text=f'Input error: {exc}')
        self.after(50, self._input_tick)

    def _escape(self, event=None):
        if self._state == 'thrusters' or self._vehicle_armed is not False:
            self._stop()

    def _dispatch_nav(self, event):
        if event in ('up', 'down'):
            self._nav_move(-1 if event == 'up' else 1)
        elif event == 'select':
            self._nav_select()
        elif event == 'back':
            self._nav_back()

    def _nav_move(self, delta):
        if hasattr(self._screen, 'move'):
            self._screen.move(delta)

    def _nav_select(self):
        screen = self._screen
        if isinstance(screen, HomeScreen):
            {'Browse Tasks': self._show_menu, 'Thruster Control': self._show_thrusters,
             'Exit': self.destroy}[screen.selected_label()]()
        elif isinstance(screen, ThrusterScreen):
            action = screen.selected_action()
            if action == 'Back':
                self._nav_back()
            else:
                self._set_thrusters(screen, action == 'Arm thrusters')
        elif isinstance(screen, TaskMenuScreen):
            task_id = screen.selected_task_id()
            if task_id:
                def loaded(task):
                    if self._screen is screen:
                        self._show_detail(task)
                self._submit(lambda: api_mod.get_task(task_id), loaded, key='detail')
        elif isinstance(screen, TaskDetailScreen):
            action, task_id = screen.selected_action(), screen.task_id()
            if action == 'Upload images':
                self._show_upload(task_id)
            elif action == 'Run reconstruction':
                self._run_reconstruction_command(task_id)
            elif action == 'Iceberg threat calculator':
                self._show_iceberg()
            elif action == 'Back':
                self._show_menu()
        elif isinstance(screen, IcebergScreen):
            screen.compute()
        elif isinstance(screen, UploadScreen):
            action = screen.selected_action()
            if action == 'Choose files…':
                screen.choose_files()
            elif action == 'Upload to server':
                self._do_upload(screen)
            elif action == 'Back':
                self._show_detail(self._current_task)

    def _nav_back(self):
        if self._state == 'thrusters':
            self._stop()
            self._show_home()
        elif self._state == 'menu':
            self._show_home()
        elif self._state == 'detail':
            self._show_menu()
        elif self._state in ('upload', 'iceberg'):
            self._show_detail(self._current_task)

    def _do_upload(self, screen):
        paths = screen.file_paths()
        if not paths:
            screen.set_status('Select files first.', ok=False)
            return
        screen.set_status('Uploading…')

        def done(result):
            self._uploads[screen.task_id] = result['saved_files']
            self._mission_lbl.configure(text=f"Mission: {result['count']} images uploaded")
            if self._screen is screen:
                screen.set_status('Upload successful.')

        def failed(detail):
            if self._screen is screen:
                screen.set_status(f'Upload failed: {detail}', ok=False)
        self._submit(lambda: api_mod.upload_images(screen.task_id, paths), done, failed, key='upload')

    def _set_thrusters(self, screen, running):
        if running and ('control' in self._pending or self._closing):
            return
        command = 'enable_thrusters' if running else 'disable_thrusters'
        if isinstance(screen, ThrusterScreen) and screen is self._screen:
            screen.set_status(None, 'Waiting for vehicle acknowledgment…')

        def done(result):
            state = result.get('control')
            if not result.get('acknowledged') or state is None:
                self._status_error('Missing vehicle acknowledgment')
                return
            self._receive_status({'connected': True, 'control': state})
        # Stop is never deduplicated behind an in-flight arm request.
        self._submit(lambda: api_mod.send_command({'command': command}), done,
                     self._status_error, key='control' if running else None, control=True)

    def _stop(self):
        self._set_thrusters(self._screen, False)

    def _run_reconstruction_command(self, task_id):
        self._submit(lambda: api_mod.send_command(
            {'command': 'run_reconstruction', 'task_id': task_id}),
            lambda result: self._mission_lbl.configure(text='Mission: capture requested'),
            key='reconstruction')

    def _toast(self, message):
        self._mission_lbl.configure(text=str(message)[:180])

    def destroy(self):
        if self._closing:
            return
        self._closing = True
        self._backend_lbl.configure(text='Closing: requesting disarm…')
        self._submit(lambda: api_mod.send_command({'command': 'disable_thrusters'}),
                     lambda result: self._finish_close(),
                     lambda error: self._finish_close(error), control=True)

    def _finish_close(self, error=None):
        if error:
            print(f'GUI close: disarm unconfirmed: {error}', file=sys.stderr)
        self._controller.close()
        self._workers.shutdown(wait=False, cancel_futures=True)
        self._control_worker.shutdown(wait=False, cancel_futures=True)
        self._destroyed = True
        for timer in self.tk.call('after', 'info'):
            # Cancel at the Tcl level only: after_cancel() would delete a
            # callback that a child widget still owns, and that widget's own
            # destroy() then fails with "can't delete Tcl command".
            self.tk.call('after', 'cancel', timer)
        super().destroy()


def main():
    MissionApp().mainloop()


if __name__ == '__main__':
    main()
