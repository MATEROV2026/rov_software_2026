"""ICM-20649 or ICM-20948 accel/gyro, published in ROS SI units.

Both parts are in service on different vehicles. They share a register layout
but report different WHO_AM_I values and, at the same FS_SEL, different
full-scale ranges - so the part is detected at init and its scale factors are
selected from that, rather than assumed.

Calibration is applied here rather than downstream, so every subscriber sees
corrected data and there is one place to look when the horizon is wrong. All
five parameters default to the identity transform, so a vehicle with no
calibration file behaves exactly as it did before this was added - it just
says so in the log instead of being silently uncalibrated.
"""
import time

import rclpy
from rclpy.executors import ExternalShutdownException
from sensor_msgs.msg import Imu

from materov.i2c_sensor import I2CSensorNode
from materov.sensor_math import (ICM20649_WHO_AM_I, ICM20948_WHO_AM_I,
                                 apply_accel_calibration, apply_gyro_bias,
                                 decode_icm)

_PART_NAMES = {ICM20649_WHO_AM_I: 'ICM-20649', ICM20948_WHO_AM_I: 'ICM-20948'}

_IDENTITY_BIAS = [0.0, 0.0, 0.0]
_IDENTITY_SCALE = [1.0, 1.0, 1.0]

# Covariance stand-ins for an uncharacterised sensor. Deliberately pessimistic:
# a filter that trusts the IMU too much is harder to debug than one that
# trusts it too little. Measure the real figures and put them in the YAML.
_DEFAULT_ACCEL_VARIANCE = [0.1, 0.1, 0.1]      # (m/s^2)^2
_DEFAULT_GYRO_VARIANCE = [0.01, 0.01, 0.01]    # (rad/s)^2

# sensor_msgs/Imu covariances are row-major 3x3; only the diagonal is known.
_DIAGONAL = (0, 4, 8)


class ImuSensorNode(I2CSensorNode):
    def __init__(self):
        super().__init__('imu_sensor_node', 0x68)
        self.who_am_i = None

        self.accel_bias = self._axis_parameter('accel_bias', _IDENTITY_BIAS)
        self.accel_scale = self._axis_parameter('accel_scale', _IDENTITY_SCALE)
        self.gyro_bias = self._axis_parameter('gyro_bias', _IDENTITY_BIAS)
        self.accel_variance = self._axis_parameter(
            'accel_variance', _DEFAULT_ACCEL_VARIANCE)
        self.gyro_variance = self._axis_parameter(
            'gyro_variance', _DEFAULT_GYRO_VARIANCE)

        if any(value == 0.0 for value in self.accel_scale):
            raise ValueError('accel_scale must be non-zero on every axis')
        if any(value < 0.0 for value in self.accel_variance + self.gyro_variance):
            raise ValueError('Variances cannot be negative')
        self._warn_if_uncalibrated()

        self.pub = self.create_publisher(Imu, '/imu/data_raw', 10)
        self.create_timer(0.02, self.sample)

    def _axis_parameter(self, name, default):
        """Declare a three-element double parameter and fail loudly if it is not.

        YAML quietly yields an int for an unsuffixed whole number, which ROS
        then refuses as a double_array, so the generator that writes this file
        must always emit a decimal point.
        """
        values = self.declare_parameter(name, default).value
        if values is None or len(values) != 3:
            raise ValueError(
                f'{name} must have exactly three elements; '
                f'got {values!r}')
        return [float(value) for value in values]

    def _warn_if_uncalibrated(self):
        if self.accel_bias == _IDENTITY_BIAS and self.accel_scale == _IDENTITY_SCALE:
            self.get_logger().warn(
                'Accelerometer running uncalibrated (identity bias and scale). '
                'Roll and pitch will carry a fixed offset.')
        if self.gyro_bias == _IDENTITY_BIAS:
            self.get_logger().warn(
                'Gyroscope bias is zero; heading will drift without bound.')

    def select_bank(self, bank):
        self.bus.write_byte_data(self.address, 0x7F, bank << 4)

    def initialize_sensor(self):
        self.select_bank(0)
        identity = self.bus.read_byte_data(self.address, 0x00)
        if identity not in _PART_NAMES:
            raise ValueError(
                'Expected ICM-20649 WHO_AM_I=0xe1 or ICM-20948 WHO_AM_I=0xea; '
                f'got 0x{identity:02x}')
        self.who_am_i = identity
        self.get_logger().info(f'{_PART_NAMES[identity]} detected at 0x{self.address:02x}')
        self.bus.write_byte_data(self.address, 0x05, 0)
        self.bus.write_byte_data(self.address, 0x06, 1)
        self.bus.write_byte_data(self.address, 0x07, 0)
        time.sleep(0.05)
        self.select_bank(2)
        for register, value in ((0x00, 19), (0x10, 0), (0x11, 19),
                                (0x01, 0x01), (0x14, 0x01)):
            self.bus.write_byte_data(self.address, register, value)
        self.select_bank(0)

    def publish_sample(self):
        block = self.bus.read_i2c_block_data(self.address, 0x2D, 12)
        acceleration, gyro = decode_icm(block, self.who_am_i)
        acceleration = apply_accel_calibration(
            acceleration, self.accel_bias, self.accel_scale)
        gyro = apply_gyro_bias(gyro, self.gyro_bias)

        msg = Imu()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'imu_link'
        msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z = acceleration
        msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z = gyro
        # No orientation is estimated here; -1 is the documented sentinel.
        msg.orientation_covariance[0] = -1.0
        for axis, cell in enumerate(_DIAGONAL):
            msg.linear_acceleration_covariance[cell] = self.accel_variance[axis]
            msg.angular_velocity_covariance[cell] = self.gyro_variance[axis]
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = ImuSensorNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
