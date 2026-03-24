# materov/materov/camera_node.py
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')
        # Subscribe to the 'commands' topic
        self.subscription = self.create_subscription(
            String,
            'commands',
            self.command_callback,
            10  # QoS history depth
        )
        self.get_logger().info("Jetson node started and listening for commands...")

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
    node = CameraNode()
    try:
        rclpy.spin(node)  # Keep the node alive
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()