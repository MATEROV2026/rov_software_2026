
import rclpy
from rclpy.node import Node

from sensor_msgs.msg import FluidPressure, Temperature
from std_msgs.msg import Float64

import ms5837
import math


class Bar02SensorNode(Node):
    def __init__(self):
        super().__init__('bar02_sensor_node')

        # Bar02 on Jetson I2C bus 7
        self.sensor = ms5837.MS5837_02BA(bus=7)

        if not self.sensor.init():
            raise RuntimeError(
                "Bar02 initialization failed"
            )

        # Freshwater density in kg/m^3
        self.density = 997.0
        self.sensor.setFluidDensity(self.density)

        # Atmospheric pressure reference
        self.surface_pressure = None

        # ROS 2 publishers
        self.pressure_pub = self.create_publisher(
            FluidPressure, '/bar02/pressure', 10
        )

        self.temperature_pub = self.create_publisher(
            Temperature, '/bar02/temperature', 10
        )

        self.depth_pub = self.create_publisher(
            Float64, '/bar02/depth', 10
        )

        # Read at approximately 10 Hz
        self.timer = self.create_timer(
            0.1, self.publish_bar02
        )

        self.get_logger().info(
            "Bar02 pressure sensor node started"
        )

    def publish_bar02(self):
        # Read sensor over I2C
        if not self.sensor.read():
            self.get_logger().warning(
                "Failed to read Bar02 sensor"
            )
            return

        pressure = self.sensor.pressure()  # mbar
        temperature = self.sensor.temperature()  # C

        # Check for invalid data
        if not (
            math.isfinite(pressure)
            and math.isfinite(temperature)
            and 300 <= pressure <= 2000
            and -20 <= temperature <= 85
        ):
            self.get_logger().warning(
                "Invalid Bar02 measurement"
            )
            return

        # Zero depth at startup.
        # Start the node while sensor is in air.
        if self.surface_pressure is None:
            self.surface_pressure = pressure

        # Pressure difference gives depth
        depth = (
            (pressure - self.surface_pressure) * 100.0
        ) / (self.density * 9.80665)

        stamp = self.get_clock().now().to_msg()

        # Pressure in Pascals
        pressure_msg = FluidPressure()
        pressure_msg.header.stamp = stamp
        pressure_msg.header.frame_id = "bar02_link"
        pressure_msg.fluid_pressure = pressure * 100.0
        pressure_msg.variance = 0.0

        # Temperature in Celsius
        temperature_msg = Temperature()
        temperature_msg.header.stamp = stamp
        temperature_msg.header.frame_id = "bar02_link"
        temperature_msg.temperature = temperature
        temperature_msg.variance = 0.0

        # Relative depth in meters
        depth_msg = Float64()
        depth_msg.data = depth

        # Publish
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
