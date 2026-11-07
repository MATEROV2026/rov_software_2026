"""ICM-20649 or ICM-20948 accel/gyro/temperature, published in ROS SI units.

Both parts are in service on different vehicles. They share a register layout
but report different WHO_AM_I values and, at the same FS_SEL, different
full-scale ranges - so the part is detected at init and its scale factors are
selected from that, rather than assumed.

Calibration is applied here rather than downstream, so every subscriber sees
corrected data and there is one place to look when the horizon is wrong. All
five parameters default to the identity transform, so a vehicle with no
calibration file behaves exactly as it did before this was added - it just
says so in the log instead of being silently uncalibrated.

Die temperature is published on /imu/temperature. It is not the water
temperature - it reads well above ambient once the board has been running -
but gyro bias moves with it at roughly 0.05 deg/s per degree C, so a bias
measured on a cool bench does not describe a warm vehicle. Logging the
temperature alongside the data is what makes that correctable later.
"""
import time

import rclpy
from rclpy.executors import ExternalShutdownException
from sensor_msgs.msg import Imu, Temperature

from materov.i2c_sensor import I2CSensorNode
from materov.sensor_math import (ICM_BURST_WITH_TEMPERATURE, ICM20649_WHO_AM_I,
                                 ICM20948_WHO_AM_I, apply_accel_calibration,
                                 apply_gyro_bias, decode_icm,
                                 decode_icm_temperature)

_PART_NAMES = {ICM20649_WHO_AM_I: 'ICM-20649', ICM20948_WHO_AM_I: 'ICM-20948'}

# AD0 selects between these two. Breakouts ship strapped either way, so the
# part is looked for at both rather than assumed at the declared address.
_CANDIDATE_ADDRESSES = (0x68, 0x69)

_SAMPLE_PERIOD = 0.02   # seconds; the timer below runs at this rate

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

        # Die temperature changes over minutes, so publishing it at the IMU's
        # own rate is traffic for nothing. Decimate instead of adding a second
        # timer, which would mean a second I2C transaction.
        period = self.declare_parameter('temperature_period', 1.0).value
        if period <= 0.0:
            raise ValueError('temperature_period must be positive')
        self._samples_per_temperature = max(1, round(period / _SAMPLE_PERIOD))
        self._sample_count = 0

        self.pub = self.create_publisher(Imu, '/imu/data_raw', 10)
        self.temperature_pub = self.create_publisher(
            Temperature, '/imu/temperature', 10)
        self.create_timer(_SAMPLE_PERIOD, self.sample)

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

    def _detect_part(self):
        """Find the IMU at 0x68 or 0x69 and return its WHO_AM_I.

        The declared ``i2c_address`` is tried first, so setting it explicitly
        still wins; the other is a fallback rather than a guess. Reporting
        every address tried and what it said turns "sensor unavailable" into
        something actionable - a wrong strap reads differently from an
        unpowered bus.
        """
        candidates = [self.address] + [address for address in _CANDIDATE_ADDRESSES
                                       if address != self.address]
        attempts = []
        for address in candidates:
            try:
                self.bus.write_byte_data(address, 0x7F, 0)      # select bank 0
                identity = self.bus.read_byte_data(address, 0x00)
            except OSError as exc:
                attempts.append(f'0x{address:02x}: {exc.strerror or exc}')
                continue
            if identity in _PART_NAMES:
                if address != self.address:
                    self.get_logger().warn(
                        f'IMU answered at 0x{address:02x}, not the configured '
                        f'0x{self.address:02x}. Using 0x{address:02x}; set '
                        'i2c_address to silence this.')
                    self.address = address
                return identity
            attempts.append(f'0x{address:02x}: WHO_AM_I 0x{identity:02x}')
        raise ValueError(
            'No ICM-20649 (WHO_AM_I 0xe1) or ICM-20948 (0xea) on '
            f'I2C-{self.bus_id}. Tried ' + '; '.join(attempts))

    def initialize_sensor(self):
        identity = self._detect_part()
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
        # One burst from ACCEL_XOUT_H covers accel, gyro and TEMP_OUT, so the
        # temperature always belongs to the sample it is published beside.
        block = self.bus.read_i2c_block_data(
            self.address, 0x2D, ICM_BURST_WITH_TEMPERATURE)
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

        self._sample_count += 1
        if self._sample_count >= self._samples_per_temperature:
            self._sample_count = 0
            temperature = Temperature()
            temperature.header = msg.header
            temperature.temperature = decode_icm_temperature(block, self.who_am_i)
            temperature.variance = 0.0      # 0 is the documented "unknown"
            self.temperature_pub.publish(temperature)


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
