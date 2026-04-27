import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import String
import numpy as np
import cv2


class VisionNode(Node):
    def __init__(self):
        super().__init__('vision_node')

        self.sub_claw = self.create_subscription(
            CompressedImage,
            '/camera/image_compressed',
            self.claw_callback,
            10
        )

        self.sub_zed = self.create_subscription(
            CompressedImage,
            '/zed/zed_node/rgb/image_rect_color/compressed',
            self.zed_callback,
            10
        )

        self.command_publisher = self.create_publisher(String, 'commands', 10)

        # Pump the OpenCV event loop independently of camera frames so that
        # keyboard commands still work even if the camera feed drops.
        self.key_timer = self.create_timer(1.0 / 30.0, self._poll_keys)

        self.get_logger().info("Vision node started — main cam: /camera/image_compressed, ZED (optional): /zed/zed_node/rgb/image_rect_color/compressed")

    def claw_callback(self, msg):
        frame = self._decode(msg)
        if frame is None:
            return
        cv2.imshow("Main Camera (exploreHD)", frame)

    def zed_callback(self, msg):
        frame = self._decode(msg)
        if frame is None:
            return
        cv2.imshow("ZED Camera", frame)

    def _poll_keys(self):
        self._handle_keys(cv2.waitKey(1) & 0xFF)

    def _decode(self, msg):
        np_arr = np.frombuffer(msg.data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            self.get_logger().warn("Dropped a corrupt camera frame")
        return frame

    def _handle_keys(self, key):
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

    def destroy_node(self):
        cv2.destroyAllWindows()
        super().destroy_node()


def main():
    rclpy.init()
    node = VisionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
