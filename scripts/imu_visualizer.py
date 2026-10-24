"""Standalone Arduino IMU viewer for serial CSV streams; no ROS required."""
import argparse
import math
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk

import serial
from serial.tools import list_ports


GRAVITY = 9.80665
WIDTH, HEIGHT = 920, 660
AXIS_COLORS = ('#ff6b6b', '#63d471', '#62a8ff')


class ImuViewer:
    def __init__(self, port, baud, accel_unit, gyro_unit, alpha):
        self.port = port
        self.baud = baud
        self.accel_unit = accel_unit
        self.gyro_unit = gyro_unit
        self.root = tk.Tk()
        self.alpha = tk.DoubleVar(master=self.root, value=alpha)
        self.samples = queue.Queue(maxsize=1)
        self.stop_event = threading.Event()
        self.orientation = None
        self.last_sample_at = None
        self.last_sample = None
        self.gyro_bias = [0.0, 0.0, 0.0]
        self.calibration_samples = None
        self.calibration_started = None
        self.calibration_text = 'Press C or click Calibrate while the sensor is still'
        self.error_text = ''
        self.serial_note = ''

        self.root.title('Arduino IMU Orientation')
        self.root.geometry(f'{WIDTH}x{HEIGHT}')
        self.root.configure(bg='#161b22')
        self.root.bind('c', lambda _event: self.start_calibration())
        self.root.bind('r', lambda _event: self.reset_yaw())
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = tk.Label(self.root, text='IMU ORIENTATION', bg='#161b22', fg='#f0f4f8',
                          font=('Helvetica', 18, 'bold'))
        header.grid(row=0, column=0, sticky='w', padx=24, pady=(16, 6))
        controls = ttk.Frame(self.root)
        controls.grid(row=2, column=0, sticky='ew', padx=24, pady=(4, 8))
        ttk.Button(controls, text='Calibrate gyro (C)', command=self.start_calibration).pack(side='left')
        ttk.Button(controls, text='Reset yaw (R)', command=self.reset_yaw).pack(side='left', padx=8)
        ttk.Label(controls, text='Gyro filter weight').pack(side='left', padx=(20, 6))
        ttk.Scale(controls, from_=0.8, to=0.999, variable=self.alpha,
                  orient='horizontal', length=220).pack(side='left')

        self.canvas = tk.Canvas(self.root, width=WIDTH - 48, height=HEIGHT - 132,
                                bg='#161b22', highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky='nsew', padx=24)

        self.serial = None
        try:
            self.serial = serial.Serial(port, baud, timeout=1)
        except (OSError, serial.SerialException) as exc:
            self.error_text = f'Could not open {port}: {exc}'
        else:
            self.reader = threading.Thread(target=self.read_serial, daemon=True)
            self.reader.start()
        self.root.after(20, self.update)

    def read_serial(self):
        while not self.stop_event.is_set():
            try:
                line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith('#'):
                    self.serial_note = line[1:].strip()
                    continue
                fields = [float(value.strip()) for value in line.split(',')]
                if len(fields) != 6 or not all(math.isfinite(value) for value in fields):
                    continue
                accel = fields[:3]
                gyro = fields[3:]
                if self.accel_unit == 'g':
                    accel = [value * GRAVITY for value in accel]
                if self.gyro_unit == 'deg/s':
                    gyro = [math.radians(value) for value in gyro]
                sample = (time.monotonic(), accel, gyro)
                try:
                    self.samples.put_nowait(sample)
                except queue.Full:
                    try:
                        self.samples.get_nowait()
                    except queue.Empty:
                        pass
                    self.samples.put_nowait(sample)
            except ValueError:
                continue
            except (OSError, serial.SerialException) as exc:
                self.error_text = str(exc)
                break

    def accept_sample(self, sampled_at, accel, gyro):
        self.last_sample = (accel, gyro)
        if self.calibration_samples is not None:
            self.calibration_samples.append(gyro)
        roll_accel = math.atan2(accel[1], accel[2])
        pitch_accel = math.atan2(-accel[0], math.hypot(accel[1], accel[2]))
        if self.orientation is None or self.last_sample_at is None:
            self.orientation = [roll_accel, pitch_accel, 0.0]
        else:
            dt = min(0.1, max(0.0, sampled_at - self.last_sample_at))
            gx, gy, gz = (gyro[i] - self.gyro_bias[i] for i in range(3))
            roll, pitch, _yaw = self.orientation
            pitch = min(math.radians(85), max(math.radians(-85), pitch))
            roll_rate = gx + math.sin(roll) * math.tan(pitch) * gy + math.cos(roll) * math.tan(pitch) * gz
            pitch_rate = math.cos(roll) * gy - math.sin(roll) * gz
            yaw_rate = (math.sin(roll) * gy + math.cos(roll) * gz) / math.cos(pitch)
            predicted_roll = roll + roll_rate * dt
            predicted_pitch = pitch + pitch_rate * dt
            weight = self.alpha.get()
            roll_error = (roll_accel - predicted_roll + math.pi) % (2 * math.pi) - math.pi
            pitch_error = (pitch_accel - predicted_pitch + math.pi) % (2 * math.pi) - math.pi
            self.orientation[0] = predicted_roll + (1.0 - weight) * roll_error
            self.orientation[1] = predicted_pitch + (1.0 - weight) * pitch_error
            self.orientation[2] += yaw_rate * dt
        self.last_sample_at = sampled_at

    def start_calibration(self):
        self.calibration_samples = []
        self.calibration_started = time.monotonic()
        self.calibration_text = 'Calibrating for 3 seconds — keep the sensor motionless'

    def finish_calibration(self):
        if self.calibration_samples is None or time.monotonic() - self.calibration_started < 3:
            return
        samples = self.calibration_samples
        self.calibration_samples = None
        if len(samples) < 30:
            self.calibration_text = 'Calibration failed: too few samples'
            return
        spread = max(math.sqrt(sum((row[axis] - sum(r[axis] for r in samples) / len(samples)) ** 2
                                   for row in samples) / len(samples)) for axis in range(3))
        if spread > 0.03:
            self.calibration_text = 'Calibration rejected: movement detected; retry while still'
            return
        self.gyro_bias = [sum(row[axis] for row in samples) / len(samples) for axis in range(3)]
        self.orientation = None
        self.calibration_text = ('Gyro bias for this run: ' +
                                 '  '.join(f'{axis} {value:+.3f}'
                                           for axis, value in zip('XYZ', self.gyro_bias)) + ' rad/s')

    @staticmethod
    def project(point, center, scale):
        x, y, z = point
        return center[0] + scale * (x - 0.42 * z), center[1] - scale * (y - 0.30 * z)

    @staticmethod
    def rotate(point, roll, pitch, yaw):
        x, y, z = point
        cr, sr = math.cos(roll), math.sin(roll)
        cp, sp = math.cos(pitch), math.sin(pitch)
        cy, sy = math.cos(yaw), math.sin(yaw)
        x, y, z = x, cr * y - sr * z, sr * y + cr * z
        x, y, z = cp * x + sp * z, y, -sp * x + cp * z
        return cy * x - sy * y, sy * x + cy * y, z

    def draw(self):
        canvas = self.canvas
        canvas.delete('all')
        canvas.create_text(26, 34, anchor='w', text=f'PORT  {self.port}  @ {self.baud}',
                           fill='#9aa9b8', font=('Helvetica', 11))
        if self.orientation is None or self.last_sample is None:
            message = (self.error_text or self.serial_note
                       or 'Waiting for Arduino CSV rows: ax,ay,az,gx,gy,gz')
            canvas.create_text(26, 85, anchor='w', text=message, fill='#d7e0e8',
                               font=('Helvetica', 14))
            return

        roll, pitch, yaw = self.orientation
        for i, (label, value) in enumerate((('ROLL', roll), ('PITCH', pitch), ('YAW · RELATIVE', yaw))):
            y = 108 + i * 76
            canvas.create_text(28, y, anchor='w', text=label, fill='#9aa9b8',
                               font=('Helvetica', 11, 'bold'))
            canvas.create_text(28, y + 32, anchor='w', text=f'{math.degrees(value):+7.1f}°',
                               fill='#f0f4f8', font=('Helvetica', 23, 'bold'))

        center = (590, 255)
        cube = [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
                (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]
        points = [self.project(self.rotate(point, roll, pitch, yaw), center, 100) for point in cube]
        edges = ((0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6),
                 (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7))
        for start, end in edges:
            canvas.create_line(*points[start], *points[end], fill='#607386', width=2)

        origin = self.project((0, 0, 0), center, 138)
        unit_axes = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
        for label, axis, color in zip('XYZ', unit_axes, AXIS_COLORS):
            tip = self.project(self.rotate(axis, roll, pitch, yaw), center, 138)
            canvas.create_line(*origin, *tip, fill=color, width=4, arrow=tk.LAST)
            canvas.create_text(tip[0] + 13, tip[1] - 10, text=label, fill=color,
                               font=('Helvetica', 13, 'bold'))

        accel, gyro = self.last_sample
        magnitude = math.sqrt(sum(value * value for value in accel))
        corrected = [gyro[i] - self.gyro_bias[i] for i in range(3)]
        age = time.monotonic() - self.last_sample_at
        warning = '  ·  STALE' if age > 1.0 else ''
        status = [
            f'ACCEL  X {accel[0]:+.2f}  Y {accel[1]:+.2f}  Z {accel[2]:+.2f} m/s²',
            f'GYRO   X {corrected[0]:+.3f}  Y {corrected[1]:+.3f}  Z {corrected[2]:+.3f} rad/s',
            f'ACCEL MAGNITUDE  {magnitude:.2f} m/s²  (stationary reference ≈ 9.81)',
            f'FILTER GYRO WEIGHT  {self.alpha.get():.3f}  ·  Higher is smoother, but drift lasts longer',
            self.calibration_text,
            (f'SERIAL ERROR  {self.error_text}' if self.error_text else
             f'DATA AGE  {age:.2f}s{warning}  ·  Yaw integrates gyro and drifts without a heading reference'),
        ]
        for i, line in enumerate(status):
            canvas.create_text(26, 410 + i * 24, anchor='w', text=line,
                               fill='#ffbd69' if i == 5 else '#c5d0da',
                               font=('Helvetica', 10))

    def reset_yaw(self):
        if self.orientation is not None:
            self.orientation[2] = 0.0

    def update(self):
        try:
            while True:
                self.accept_sample(*self.samples.get_nowait())
        except queue.Empty:
            pass
        try:
            self.finish_calibration()
            self.draw()
        except Exception as exc:
            self.canvas.delete('all')
            self.canvas.create_text(24, 40, anchor='w',
                                    text=f'Viewer drawing error: {exc}',
                                    fill='#ff8080', font=('Helvetica', 14))
            print(f'IMU viewer drawing error: {exc}')
        if not self.stop_event.is_set():
            self.root.after(20, self.update)

    def close(self):
        self.stop_event.set()
        if self.serial is not None and self.serial.is_open:
            self.serial.close()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    parser = argparse.ArgumentParser(description='Visualize Arduino IMU CSV data without ROS.')
    parser.add_argument('--port', help='Serial port, e.g. /dev/cu.usbmodem1101')
    parser.add_argument('--baud', type=int, default=115200)
    parser.add_argument('--accel-unit', choices=('m/s2', 'g'), default='g')
    parser.add_argument('--gyro-unit', choices=('rad/s', 'deg/s'), default='deg/s')
    parser.add_argument('--alpha', type=float, default=0.98)
    parser.add_argument('--list-ports', action='store_true')
    args = parser.parse_args()
    ports = list(list_ports.comports())
    if args.list_ports:
        for port in ports:
            print(f'{port.device}\t{port.description}')
        return
    if not args.port:
        parser.error('choose a port with --port, or use --list-ports')
    if not 0.8 <= args.alpha <= 0.999:
        parser.error('--alpha must be between 0.8 and 0.999')
    ImuViewer(args.port, args.baud, args.accel_unit, args.gyro_unit, args.alpha).run()


if __name__ == '__main__':
    main()

# Built by Raneem Mousa
