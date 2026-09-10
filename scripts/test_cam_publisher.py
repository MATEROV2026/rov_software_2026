#!/usr/bin/env python3
"""Publishes the laptop's local camera to /camera/image_compressed for GUI testing."""
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage


class TestCamPublisher(Node):
    def __init__(self):
        super().__init__('test_cam_publisher')
        self.pub = self.create_publisher(CompressedImage, '/camera/image_compressed', 10)
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.get_logger().error('Could not open /dev/video0')
            return
        self.timer = self.create_timer(1.0 / 30.0, self.publish_frame)
        self.get_logger().info('Publishing laptop camera → /camera/image_compressed at 30Hz')

    def publish_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return
        ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ok:
            return
        msg = CompressedImage()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'camera'
        msg.format = 'jpeg'
        msg.data = buf.tobytes()
        self.pub.publish(msg)

    def destroy_node(self):
        if self.cap.isOpened():
            self.cap.release()
        super().destroy_node()


def main():
    rclpy.init()
    node = TestCamPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
