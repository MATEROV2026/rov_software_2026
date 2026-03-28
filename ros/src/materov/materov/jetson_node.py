# materov/materov/jetson_node.py
import rclpy
import cv2
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

class JetsonNode(Node):
    def __init__(self):
        super().__init__('jetson_node')
        self.bridge = CvBridge()
        # Subscribe to the 'commands' topic
        self.command_subscription = self.create_subscription(
            String,
            'commands',
            self.command_callback,
            10  # QoS history depth
        )
        # Subscribe to the 'camera' topic
        self.image_subscription = self.create_subscription(
            Image,
            'camera',
            self.image_callback,
            10  # QoS history depth
        )
        self.get_logger().info("Jetson node started and listening for commands...")

    def image_callback(self, msg: Image):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            h, w = cv_image.shape[:2]
            self.get_logger().info(f"Received image {w}x{h}")
            # Example: show or process frame (commented for headless)
            cv2.imshow("camera", cv_image); cv2.waitKey(1)
        except Exception as e:
            self.get_logger().error(f"Failed to convert image: {e}")

    def command_callback(self, msg):
        # This function is called whenever a message is received
        command = msg.data
        self.get_logger().info(f"Received command: {command}")

        # Here you would put your motor or ROV control code
        if command == "forward":
            self.move_forward()
        elif command == "backward":
            self.move_backward()
        elif command == "stop":
            self.stop_motors()
        else:
            self.get_logger().warn(f"Unknown command: {command}")

    # Example motor functions
    def move_forward(self):
        self.get_logger().info("Moving forward (placeholder)")

    def move_backward(self):
        self.get_logger().info("Moving backward (placeholder)")

    def stop_motors(self):
        self.get_logger().info("Stopping motors (placeholder)")


def main(args=None):
    rclpy.init(args=args)
    node = JetsonNode()
    try:
        rclpy.spin(node)  # Keep the node alive
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()