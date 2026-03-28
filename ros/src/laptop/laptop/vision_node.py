import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import String
import numpy as np
import cv2

class VisionNode(Node):
    def __init__(self):
        super().__init__('vision_node')

        self.subscription = self.create_subscription(
            CompressedImage,
            '/camera/image_compressed',
            self.image_callback,
            10
        )
        
        # Publisher for sending commands to the Jetson
        self.command_publisher = self.create_publisher(
            String,
            'commands',
            10
        )
        
        self.get_logger().info("Vision node initialized - Camera feed and command control ready")

    def image_callback(self, msg):
        np_arr = np.frombuffer(msg.data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        cv2.imshow("Camera Feed", frame)
        key = cv2.waitKey(1) & 0xFF
        
        # Simple keyboard controls
        if key == ord('w'):
            self.send_command("forward")
        elif key == ord('s'):
            self.send_command("backward")
        elif key == ord('q'):
            self.send_command("stop")

    def send_command(self, command):
        msg = String()
        msg.data = command
        self.command_publisher.publish(msg)
        self.get_logger().info(f"Sent command: {command}")

def main():
    rclpy.init()
    node = VisionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()