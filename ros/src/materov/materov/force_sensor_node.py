import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from std_msgs.msg import Float32
import math
import time


class ForceSensorNode(Node):
    def __init__(self):
        super().__init__('force_sensor_node')

        # TODO: Initialize force sensor

        self.pub = self.create_publisher(Imu, '/force/data_raw', 10)

        # 50 Hz
        self.timer = self.create_timer(0.02, self.publish_imu)

        self.get_logger().info("Force sensor node started...")

    def publish_imu(self):
        # TODO: 
        msg = Float32()

        
        self.pub.publish(msg)

        self.get_logger().info("Published IMU data")
    



def main(args=None):
    rclpy.init(args=args)
    node = ImuSensorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

