import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
import random
import time

class JoystickNode(Node):
    def __init__(self):
        super().__init__('joystick_node')
        self.publisher_ = self.create_publisher(Joy, 'joy', 10)
        self.timer = self.create_timer(0.5, self.timer_callback)
        self.get_logger().info('Joystick node started.')

    def timer_callback(self):
        msg = Joy()
        msg.axes = [random.uniform(-1.0, 1.0) for _ in range(4)]
        msg.buttons = [random.choice([0, 1]) for _ in range(4)]
        self.publisher_.publish(msg)
        self.get_logger().info(f'Published Joy message: {msg}')

def main(args=None):
    rclpy.init(args=args)
    node = JoystickNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
