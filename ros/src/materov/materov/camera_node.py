import cv2
import rclpy
from rclpy.node import Node
from pathlib import Path
from sensor_msgs.msg import CompressedImage, Image
from cv_bridge import CvBridge


def _find_explorehd() -> int:
    """Return the /dev/videoN index for the exploreHD by scanning sysfs.

    ZED cameras identify themselves with 'zed' in their V4L2 name; everything
    else is assumed to be the exploreHD.  Falls back to 2 if nothing is found.
    """
    for dev in range(10):
        name_file = Path(f'/sys/class/video4linux/video{dev}/name')
        if not name_file.exists():
            continue
        if 'zed' not in name_file.read_text().strip().lower():
            return dev
    return 2


class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')

        self.bridge = CvBridge()

        device = _find_explorehd()
        self.cap = cv2.VideoCapture(device)
        if not self.cap.isOpened():
            self.get_logger().fatal(f'Could not open /dev/video{device}')
            raise RuntimeError(f'Cannot open video{device}')

        w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.get_logger().info(f'exploreHD opened at /dev/video{device} — {w}x{h}')

        self.pub_compressed = self.create_publisher(
            CompressedImage, '/camera/image_compressed', 10
        )
        self.pub_raw = self.create_publisher(Image, '/camera/image_raw', 10)

        # 30 Hz
        self.timer = self.create_timer(1.0 / 30.0, self.publish_frame)

    def publish_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            self.get_logger().warn('exploreHD: failed to read frame')
            return

        now = self.get_clock().now().to_msg()

        ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ok:
            msg = CompressedImage()
            msg.header.stamp = now
            msg.header.frame_id = 'camera'
            msg.format = 'jpeg'
            msg.data = buf.tobytes()
            self.pub_compressed.publish(msg)

        raw_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        raw_msg.header.stamp = now
        raw_msg.header.frame_id = 'camera'
        self.pub_raw.publish(raw_msg)

    def destroy_node(self):
        if self.cap.isOpened():
            self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
