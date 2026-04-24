import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32


class ForceSensorNode(Node):
    def __init__(self):
        super().__init__('force_sensor_node')

        # TODO: Initialize force sensor

        self.pub = self.create_publisher(Float32, '/force/data_raw', 10)

        # 50 Hz
        self.timer = self.create_timer(0.02, self.publish_force)

        self.get_logger().info("Force sensor node started...")

    def publish_force(self):
        # TODO:
        msg = Float32()
        msg.data = 0.0
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = ForceSensorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
