import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
import math
import smbus
import time

bus = smbus.SMBus(7)
addr = 0x68

REG_BANK_SEL = 0x7F

# Bank 0
WHO_AM_I   = 0x00
USER_CTRL  = 0x03
LP_CONFIG  = 0x05
PWR_MGMT_1 = 0x06

# Raw data registers are in bank 0 on this device family
ACCEL_XOUT_H = 0x2D
ACCEL_XOUT_L = 0x2E
ACCEL_YOUT_H = 0x2F
ACCEL_YOUT_L = 0x30
ACCEL_ZOUT_H = 0x31
ACCEL_ZOUT_L = 0x32

GYRO_XOUT_H = 0x33
GYRO_XOUT_L = 0x34
GYRO_YOUT_H = 0x35
GYRO_YOUT_L = 0x36
GYRO_ZOUT_H = 0x37
GYRO_ZOUT_L = 0x38

# Bank 2 config registers
GYRO_SMPLRT_DIV   = 0x00
GYRO_CONFIG_1     = 0x01
ACCEL_SMPLRT_DIV_1 = 0x10
ACCEL_SMPLRT_DIV_2 = 0x11
ACCEL_CONFIG      = 0x14

class ImuSensorNode(Node):
    def __init__(self):
        super().__init__('imu_sensor_node')

        # Initialize IMU sensor
        self.select_bank(0)
        bus.write_byte_data(addr, LP_CONFIG, 0x00)
        bus.write_byte_data(addr, PWR_MGMT_1, 0x01)
        time.sleep(0.05)
        self.select_bank(2)
        # About 55Hz if divider = 19, based on SparkFun / InvenSense example formulas
        bus.write_byte_data(addr, GYRO_SMPLRT_DIV, 19)
        bus.write_byte_data(addr, ACCEL_SMPLRT_DIV_1, 0x00)
        bus.write_byte_data(addr, ACCEL_SMPLRT_DIV_2, 19)
        bus.write_byte_data(addr, GYRO_CONFIG_1, 0x01)   # low range starter config
        bus.write_byte_data(addr, ACCEL_CONFIG, 0x01)    # low range starter config
        time.sleep(0.05)
        self.select_bank(0)

        self.pub = self.create_publisher(Imu, '/imu/data_raw', 10)

        # 50 Hz
        self.timer = self.create_timer(0.02, self.publish_imu)

        self.get_logger().info("IMU publisher node started...")

    def publish_imu(self):
        msg = Imu()

        ax = self.read_word_2c(ACCEL_XOUT_H)  # Assuming a sensitivity of 16384 LSB/g for ±2g range
        ay = self.read_word_2c(ACCEL_YOUT_H)
        az = self.read_word_2c(ACCEL_ZOUT_H)

        gx = self.read_word_2c(GYRO_XOUT_H)
        gy = self.read_word_2c(GYRO_YOUT_H)
        gz = self.read_word_2c(GYRO_ZOUT_H)

        # Timestamp + frame
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "imu_link"

        # Example dummy data (replace with real sensor values)
        msg.linear_acceleration.x = ax
        msg.linear_acceleration.y = ay
        msg.linear_acceleration.z = az

        msg.angular_velocity.x = gx
        msg.angular_velocity.y = gy
        msg.angular_velocity.z = gz

        # No orientation
        msg.orientation_covariance[0] = -1

        # Covariances (recommended)
        msg.angular_velocity_covariance = [
            0.01,0,0,
            0,0.01,0,
            0,0,0.01
        ]

        msg.linear_acceleration_covariance = [
            0.1,0,0,
            0,0.1,0,
            0,0,0.1
        ]

        self.pub.publish(msg)

        self.get_logger().info("Published IMU data")
    
    def select_bank(bank):
        bus.write_byte_data(addr, REG_BANK_SEL, bank << 4)

    def read_word_2c(reg_h):
        high = bus.read_byte_data(addr, reg_h)
        low = bus.read_byte_data(addr, reg_h + 1)
        value = (high << 8) | low
        if value & 0x8000:
            value -= 65536
        return value


def main(args=None):
    rclpy.init(args=args)
    node = ImuSensorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

