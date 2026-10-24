"""Live accelerometer/gyro orientation view for the vehicle IMU."""
import argparse
import math
import sys
import threading
import time

import cv2
import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu


WIDTH, HEIGHT = 900, 640
GRAVITY = 9.80665
AXIS_COLORS = ((80, 90, 255), (90, 220, 100), (255, 170, 70))


class ImuVisualizer(Node):
    def __init__(self):
        super().__init__('imu_visualizer')
        self.declare_parameter('topic', '/imu/data_raw')
        self.declare_parameter('filter_alpha', 0.98)
        self.alpha = float(self.get_parameter('filter_alpha').value)
        self.alpha = min(0.999, max(0.8, self.alpha))
        self.latest = None
        self.last_sample_at = None
        self.orientation = None
        self.gyro_bias = np.zeros(3)
        self.calibration = None
        self.calibration_result = 'Press C while the sensor is still to calibrate gyro bias'
        self.serial = None
        self.serial_thread = None
        self.serial_error = None

    def on_imu(self, msg):
        accel = [msg.linear_acceleration.x, msg.linear_acceleration.y,
                 msg.linear_acceleration.z]
        gyro = [msg.angular_velocity.x, msg.angular_velocity.y,
                msg.angular_velocity.z]
        self.accept_sample(accel, gyro)

    def accept_sample(self, accel, gyro):
        now = time.monotonic()
        accel = np.asarray(accel, dtype=float)
        gyro = np.asarray(gyro, dtype=float)
        self.latest = (accel, gyro)
        if self.calibration is not None:
            self.calibration.append(gyro.copy())

        roll_accel = math.atan2(accel[1], accel[2])
        pitch_accel = math.atan2(-accel[0], math.hypot(accel[1], accel[2]))
        if self.orientation is None or self.last_sample_at is None:
            self.orientation = np.array([roll_accel, pitch_accel, 0.0])
        else:
            dt = min(0.1, max(0.0, now - self.last_sample_at))
            corrected = gyro - self.gyro_bias
            roll, pitch, _ = self.orientation
            pitch = min(math.radians(85), max(math.radians(-85), pitch))
            roll_rate = (corrected[0] + math.sin(roll) * math.tan(pitch) * corrected[1]
                         + math.cos(roll) * math.tan(pitch) * corrected[2])
            pitch_rate = (math.cos(roll) * corrected[1]
                          - math.sin(roll) * corrected[2])
            yaw_rate = ((math.sin(roll) * corrected[1] + math.cos(roll) * corrected[2])
                        / math.cos(pitch))
            predicted_roll = roll + roll_rate * dt
            predicted_pitch = pitch + pitch_rate * dt
            roll_error = (roll_accel - predicted_roll + math.pi) % (2 * math.pi) - math.pi
            pitch_error = (pitch_accel - predicted_pitch + math.pi) % (2 * math.pi) - math.pi
            self.orientation[0] = predicted_roll + (1.0 - self.alpha) * roll_error
            self.orientation[1] = predicted_pitch + (1.0 - self.alpha) * pitch_error
            self.orientation[2] += yaw_rate * dt
        self.last_sample_at = now

    def start_serial(self, port, baud, accel_unit, gyro_unit):
        import serial

        self.serial = serial.Serial(port, baud, timeout=1)
        stream = self.serial

        def read_lines():
            while stream.is_open:
                try:
                    line = stream.readline().decode('utf-8', errors='ignore').strip()
                    fields = [float(value.strip()) for value in line.split(',')]
                    if len(fields) != 6:
                        continue
                    accel = np.asarray(fields[:3], dtype=float)
                    gyro = np.asarray(fields[3:], dtype=float)
                    if accel_unit == 'g':
                        accel *= GRAVITY
                    if gyro_unit == 'deg/s':
                        gyro = np.radians(gyro)
                    self.accept_sample(accel, gyro)
                except (ValueError, OSError) as exc:
                    if isinstance(exc, OSError):
                        self.serial_error = str(exc)
                        break

        self.serial_thread = threading.Thread(target=read_lines, daemon=True)
        self.serial_thread.start()

    def close_serial(self):
        if self.serial is not None:
            self.serial.close()
            self.serial = None

    def start_calibration(self):
        self.calibration = []
        self.calibration_started = time.monotonic()
        self.calibration_result = 'Calibrating: keep the IMU motionless for 3 seconds'

    def finish_calibration_if_ready(self):
        if self.calibration is None or time.monotonic() - self.calibration_started < 3.0:
            return
        samples = np.asarray(self.calibration)
        self.calibration = None
        if len(samples) < 30:
            self.calibration_result = 'Calibration failed: too few IMU samples'
            return
        spread = np.max(np.std(samples, axis=0))
        if spread > 0.03:
            self.calibration_result = 'Calibration rejected: IMU moved; retry while stationary'
            return
        self.gyro_bias = np.mean(samples, axis=0)
        self.orientation = None
        self.calibration_result = 'Gyro bias saved for this run: ' + self.vec_text(self.gyro_bias, 'rad/s')

    @staticmethod
    def vec_text(values, unit):
        return f'X {values[0]:+.3f}  Y {values[1]:+.3f}  Z {values[2]:+.3f} {unit}'

    @staticmethod
    def rotation(roll, pitch, yaw):
        cr, sr = math.cos(roll), math.sin(roll)
        cp, sp = math.cos(pitch), math.sin(pitch)
        cy, sy = math.cos(yaw), math.sin(yaw)
        rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
        ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
        rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
        return rz @ ry @ rx

    @staticmethod
    def project(points, center, scale):
        return np.asarray([[int(center[0] + scale * (p[0] - 0.42 * p[2])),
                            int(center[1] - scale * (p[1] - 0.30 * p[2]))]
                           for p in points], dtype=np.int32)

    def draw(self):
        self.finish_calibration_if_ready()
        frame = np.full((HEIGHT, WIDTH, 3), (22, 27, 34), dtype=np.uint8)
        cv2.putText(frame, 'IMU ORIENTATION', (32, 42), cv2.FONT_HERSHEY_SIMPLEX,
                    0.9, (235, 240, 245), 2, cv2.LINE_AA)
        if self.latest is None or self.orientation is None:
            source = getattr(self, 'source_label', self.get_parameter('topic').value)
            cv2.putText(frame, 'Waiting for IMU data on ' + source,
                        (32, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 190, 200), 1)
            return frame

        accel, gyro = self.latest
        roll, pitch, yaw = self.orientation
        age = time.monotonic() - self.last_sample_at
        values = [('ROLL', roll), ('PITCH', pitch), ('YAW (RELATIVE)', yaw)]
        for i, (label, value) in enumerate(values):
            y = 105 + i * 70
            cv2.putText(frame, label, (40, y), cv2.FONT_HERSHEY_SIMPLEX,
                        0.48, (155, 170, 185), 1, cv2.LINE_AA)
            cv2.putText(frame, f'{math.degrees(value):+7.1f} deg', (40, y + 34),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.78, (245, 247, 250), 2, cv2.LINE_AA)

        center = (570, 300)
        rotation = self.rotation(roll, pitch, yaw)
        cube = np.array([[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
                         [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]], dtype=float)
        points = self.project(cube @ rotation.T, center, 105)
        for start, end in ((0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6),
                           (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)):
            cv2.line(frame, tuple(points[start]), tuple(points[end]), (90, 115, 140), 2, cv2.LINE_AA)

        basis = np.eye(3) @ rotation.T
        origin = self.project([[0, 0, 0]], center, 140)[0]
        for i, axis in enumerate(basis):
            tip = self.project([axis], center, 140)[0]
            cv2.arrowedLine(frame, tuple(origin), tuple(tip), AXIS_COLORS[i], 3,
                            cv2.LINE_AA, tipLength=0.14)
            cv2.putText(frame, 'XYZ'[i], (int(tip[0] + 8), int(tip[1] - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, AXIS_COLORS[i], 2, cv2.LINE_AA)

        accel_norm = float(np.linalg.norm(accel))
        gyro_corrected = gyro - self.gyro_bias
        lines = [
            f'Accel: {self.vec_text(accel, "m/s^2")}  |  magnitude {accel_norm:.2f} m/s^2',
            f'Gyro:  {self.vec_text(gyro_corrected, "rad/s")}',
            f'Gravity error: {accel_norm - GRAVITY:+.2f} m/s^2',
            f'Filter gyro weight: {self.alpha:.3f}   [ / ] adjust',
            self.calibration_result,
            ('STALE  ' if age > 1.0 else '')
            + f'Data age: {age:.2f}s   |   C calibrate gyro   R reset yaw   Q quit',
        ]
        if self.serial_error:
            lines[4] = 'Serial error: ' + self.serial_error[:90]
        for i, line in enumerate(lines):
            cv2.putText(frame, line, (32, 485 + i * 25), cv2.FONT_HERSHEY_SIMPLEX,
                        0.46, (195, 205, 215), 1, cv2.LINE_AA)
        cv2.putText(frame, 'Yaw integrates gyro only and drifts without a heading reference.',
                    (32, HEIGHT - 13), cv2.FONT_HERSHEY_SIMPLEX, 0.48,
                    (80, 190, 255), 1, cv2.LINE_AA)
        return frame


def main(args=None):
    parser = argparse.ArgumentParser(description='Visualize ROS IMU or Arduino CSV serial data.')
    parser.add_argument('--serial-port', help='Arduino port, such as /dev/ttyACM0')
    parser.add_argument('--baud', type=int, default=115200)
    parser.add_argument('--accel-unit', choices=('m/s2', 'g'), default='m/s2')
    parser.add_argument('--gyro-unit', choices=('rad/s', 'deg/s'), default='rad/s')
    parsed, ros_args = parser.parse_known_args(args if args is not None else sys.argv[1:])
    rclpy.init(args=ros_args)
    node = ImuVisualizer()
    try:
        if parsed.serial_port:
            node.source_label = parsed.serial_port
            node.start_serial(parsed.serial_port, parsed.baud,
                              parsed.accel_unit, parsed.gyro_unit)
        else:
            node.source_label = node.get_parameter('topic').value
            node.create_subscription(Imu, node.source_label, node.on_imu,
                                     qos_profile_sensor_data)
        cv2.namedWindow('IMU Orientation', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('IMU Orientation', WIDTH, HEIGHT)
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.01)
            cv2.imshow('IMU Orientation', node.draw())
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), 27):
                break
            if key == ord('c'):
                node.start_calibration()
            elif key == ord('r') and node.orientation is not None:
                node.orientation[2] = 0.0
            elif key in (ord('['), ord(',')):
                node.alpha = max(0.8, node.alpha - 0.005)
            elif key in (ord(']'), ord('.')):
                node.alpha = min(0.999, node.alpha + 0.005)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.close_serial()
        cv2.destroyAllWindows()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

# Built by Raneem Mousa
