
import math
import time

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import FluidPressure, Temperature
from std_msgs.msg import Float64
from std_srvs.srv import Trigger

import ms5837


WATER_DENSITY = 997.0
GRAVITY = 9.80665


class Bar02SensorNode(Node):

    def __init__(self):
        super().__init__('bar02_sensor_node')

        # I2C bus (same bus used by your IMU)
        self.declare_parameter('i2c_bus', 7)
        bus = self.get_parameter('i2c_bus').value

        # Initialize Blue Robotics Bar02
        self.sensor = ms5837.MS5837_02BA(bus=bus)

        if not self.sensor.init():
            raise RuntimeError(
                "Bar02 sensor initialization FAILED!"
            )

        self.sensor.setFluidDensity(WATER_DENSITY)

        self.get_logger().info(
            "Bar02 initialized successfully!"
        )

        # Surface pressure reference
        self.surface_pressure = None
        self.calibrated = False

        # ROS 2 publishers
        self.pressure_pub = self.create_publisher(
            FluidPressure,
            '/bar02/pressure',
            10
        )

        self.temperature_pub = self.create_publisher(
            Temperature,
            '/bar02/temperature',
            10
        )

        self.depth_pub = self.create_publisher(
            Float64,
            '/bar02/depth',
            10
        )

        # Service to reset surface depth to zero
        self.calibration_service = self.create_service(
            Trigger,
            '/bar02/calibrate_surface',
            self.calibration_callback
        )

        # Automatic calibration at startup
        self.calibrate_surface()

        # Publish at approximately 10 Hz
        self.timer = self.create_timer(
            0.1,
            self.publish_bar02
        )

        self.get_logger().info(
            "Bar02 ROS 2 publisher started!"
        )

    def valid_reading(self, pressure, temperature):
        return (
            math.isfinite(pressure)
            and math.isfinite(temperature)
            and 300 <= pressure <= 2000
            and -20 <= temperature <= 85
        )

    def calibrate_surface(self):
        self.get_logger().info(
            "Calibrating surface pressure..."
        )

        total_pressure = 0.0
        valid_samples = 0

        # Take 20 samples
        for i in range(20):

            try:
                if not self.sensor.read():
                    time.sleep(0.1)
                    continue

                pressure = self.sensor.pressure()
                temperature = self.sensor.temperature()

                if self.valid_reading(
                    pressure, temperature
                ):
                    total_pressure += pressure
                    valid_samples += 1

            except (OSError, IOError) as e:
                self.get_logger().warning(
                    f"Calibration read error: {e}"
                )

            time.sleep(0.1)

        if valid_samples < 10:
            self.get_logger().error(
                "Surface calibration FAILED!"
            )
            return False

        self.surface_pressure = (
            total_pressure / valid_samples
        )

        self.calibrated = True

        self.get_logger().info(
            f"Surface pressure: "
            f"{self.surface_pressure:.2f} mbar"
        )

        self.get_logger().info(
            "Calibration complete! Depth = 0 m"
        )

        return True

    def calibration_callback(
        self, request, response
    ):
        success = self.calibrate_surface()

        response.success = success

        if success:
            response.message = (
                "Surface calibration successful"
            )
        else:
            response.message = (
                "Surface calibration failed"
            )

        return response

    def publish_bar02(self):

        if not self.calibrated:
            return

        try:
            if not self.sensor.read():
                self.get_logger().warning(
                    "Bar02 sensor read failed!"
                )
                return

            pressure = self.sensor.pressure()
            temperature = self.sensor.temperature()

        except (OSError, IOError) as e:
            self.get_logger().warning(
                f"Bar02 I2C error: {e}"
            )
            return

        if not self.valid_reading(
            pressure, temperature
        ):
            self.get_logger().warning(
                "Invalid Bar02 reading!"
            )
            return

        # Calculate relative depth in meters
        depth = (
            (pressure - self.surface_pressure) * 100.0
        ) / (WATER_DENSITY * GRAVITY)

        timestamp = self.get_clock().now().to_msg()

        # Pressure message (Pascals)
        pressure_msg = FluidPressure()
        pressure_msg.header.stamp = timestamp
        pressure_msg.header.frame_id = "bar02_link"
        pressure_msg.fluid_pressure = pressure * 100.0
        pressure_msg.variance = 0.0

        # Temperature message (Celsius)
        temperature_msg = Temperature()
        temperature_msg.header.stamp = timestamp
        temperature_msg.header.frame_id = "bar02_link"
        temperature_msg.temperature = temperature
        temperature_msg.variance = 0.0

        # Depth message (meters)
        depth_msg = Float64()
        depth_msg.data = depth

        # Publish all measurements
        self.pressure_pub.publish(pressure_msg)
        self.temperature_pub.publish(temperature_msg)
        self.depth_pub.publish(depth_msg)


def main(args=None):
    rclpy.init(args=args)

    node = None

    try:
        node = Bar02SensorNode()
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        if node is not None:
            node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

