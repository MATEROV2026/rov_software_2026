#!/usr/bin/env python3
"""Measure gyroscope bias from a running imu_sensor_node.

Averages /imu/data_raw while the vehicle is stationary and prints a YAML block
ready to paste into ros/src/materov/config/imu_calibration.yaml.

Measuring here rather than on the bench matters: this is the real wiring, the
real sensor configuration, and - once the vehicle has been powered a while -
the real temperature. Zero-rate output moves about 0.05 deg/s per degree C on
this part, so a bias taken on a cool bench does not describe a warm vehicle.

Run it with the node already publishing and the vehicle completely still:

    source /opt/ros/humble/setup.bash
    source install/setup.bash
    python3 scripts/imu_gyro_bias.py            # 30 s
    python3 scripts/imu_gyro_bias.py --seconds 60

If gyro_bias is already set in the YAML, the node has subtracted it before
publishing. What this measures is then the *residual*, which should be near
zero - pass --current to have the remainder folded back in.
"""
import argparse
import math
import sys

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, Temperature

# Above this, the sample set is not a stationary one. 0.5 deg/s is far larger
# than any plausible bias and far smaller than a deliberate movement.
MOTION_LIMIT_DPS = 0.5
GRAVITY = 9.80665
# A tilted-but-still vehicle is fine; one that is being carried is not.
ACCEL_TOLERANCE = 0.5       # m/s^2 away from 1 g


class GyroBiasCollector(Node):
    def __init__(self, seconds):
        super().__init__('imu_gyro_bias')
        self.seconds = seconds
        self.samples = []
        self.accel_magnitudes = []
        self.temperatures = []
        self.create_subscription(Imu, '/imu/data_raw', self._on_imu, 50)
        self.create_subscription(
            Temperature, '/imu/temperature', self._on_temperature, 10)
        self.start = self.get_clock().now()
        self._last_report = 0

    def _on_imu(self, msg):
        w = msg.angular_velocity
        a = msg.linear_acceleration
        self.samples.append((w.x, w.y, w.z))
        self.accel_magnitudes.append(math.sqrt(a.x * a.x + a.y * a.y + a.z * a.z))
        elapsed = int(self._elapsed())
        if elapsed != self._last_report:
            self._last_report = elapsed
            print(f'\r  {elapsed:3d}/{self.seconds} s  '
                  f'{len(self.samples)} samples', end='', flush=True)

    def _on_temperature(self, msg):
        self.temperatures.append(msg.temperature)

    def _elapsed(self):
        return (self.get_clock().now() - self.start).nanoseconds / 1e9

    def done(self):
        return self._elapsed() >= self.seconds


def mean(values):
    return sum(values) / len(values)


def stdev(values, average):
    if len(values) < 2:
        return 0.0
    return math.sqrt(sum((v - average) ** 2 for v in values) / (len(values) - 1))


def fmt(value, places=6):
    """Format for YAML: fixed notation, always with a decimal point.

    Two traps here. A bare whole number is read as an int, which ROS refuses
    for a double_array. And exponent notation like 2e-06 is not a float in
    YAML 1.1 unless written 2.0e-06, so variances - which are around 1e-6 -
    get enough decimal places to stay readable in fixed form instead.
    """
    text = f'{value:.{places}f}'
    return text if '.' in text else text + '.0'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=30.0,
                        help='how long to average (default 30)')
    parser.add_argument('--current', type=float, nargs=3, metavar=('X', 'Y', 'Z'),
                        help='gyro_bias already in the YAML, in rad/s; the '
                             'measured residual is added to it')
    args = parser.parse_args()

    rclpy.init()
    node = GyroBiasCollector(args.seconds)
    print(f'Averaging /imu/data_raw for {args.seconds:.0f} s. Keep it still.')
    try:
        while rclpy.ok() and not node.done():
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        print()
        return 1
    finally:
        print()

    samples = node.samples
    if len(samples) < 50:
        print(f'Only {len(samples)} samples. Is imu_sensor_node publishing?')
        print('Check:  ros2 topic hz /imu/data_raw')
        node.destroy_node()
        rclpy.shutdown()
        return 1

    axes = list(zip(*samples))
    bias = [mean(axis) for axis in axes]
    noise = [stdev(axis, b) for axis, b in zip(axes, bias)]

    accel = mean(node.accel_magnitudes)
    moved = max(abs(math.degrees(n)) for n in noise)

    print(f'\n{len(samples)} samples over {args.seconds:.0f} s'
          f'  ({len(samples) / args.seconds:.0f} Hz)')
    if node.temperatures:
        print(f'Die temperature: {mean(node.temperatures):.1f} C '
              f'(range {min(node.temperatures):.1f} to {max(node.temperatures):.1f})')
    else:
        print('Die temperature: no /imu/temperature messages seen')

    print('\n            bias (deg/s)   noise sigma (deg/s)   drift (deg/min)')
    for name, b, n in zip('XYZ', bias, noise):
        print(f'  {name}     {math.degrees(b):>10.4f}   {math.degrees(n):>14.4f}'
              f'   {math.degrees(b) * 60:>14.1f}')

    problems = []
    if abs(accel - GRAVITY) > ACCEL_TOLERANCE:
        problems.append(
            f'|accel| averaged {accel:.3f} m/s^2, not {GRAVITY:.3f}. Either the '
            'vehicle moved or the accelerometer calibration is off.')
    if moved > MOTION_LIMIT_DPS:
        problems.append(
            f'Gyro noise reached {moved:.2f} deg/s, above the {MOTION_LIMIT_DPS} '
            'deg/s stationary limit. Something was vibrating or being handled.')
    if node.temperatures and max(node.temperatures) - min(node.temperatures) > 2.0:
        problems.append(
            'Die temperature moved more than 2 C during the run. The board is '
            'still warming up; let it settle and measure again.')

    if problems:
        print('\nNot a clean measurement:')
        for problem in problems:
            print(f'  - {problem}')
        print('\nThe numbers below are printed anyway, but do not commit them.')

    if args.current:
        bias = [b + c for b, c in zip(bias, args.current)]
        print('\n(residual folded into the --current values you passed)')

    print('\nPaste into ros/src/materov/config/imu_calibration.yaml:\n')
    if node.temperatures:
        print(f'    # Measured on the vehicle at {mean(node.temperatures):.1f} C die '
              f'temperature,\n    # over {args.seconds:.0f} s stationary. '
              'Re-measure if it runs much warmer.')
    print(f'    gyro_bias: [{", ".join(fmt(b) for b in bias)}]')
    print(f'    gyro_variance: [{", ".join(fmt(n * n, 12) for n in noise)}]')

    node.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
