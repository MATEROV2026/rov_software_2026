# materov/materov/jetson_node.py
from pathlib import Path
import shutil
import os
import cv2
import numpy as np
import rclpy
from interfaces.srv import RunReconstruction
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage, Imu
from std_msgs.msg import String


class JetsonNode(Node):
    def __init__(self):
        super().__init__('jetson_node')
        self.capture_dir = Path("/home/m8rov123/shared/images")
        os.makedirs(self.capture_dir, exist_ok=True)
        self.capture_target_count = 6
        self.capture_interval_s = 5.0
        self.capture_count = 0
        self.capture_in_progress = False
        self.capture_timer = None
        self.latest_camera_frame = None  # exploreHD frame (always present)

        self.command_subscription = self.create_subscription(
            String,
            'commands',
            self.command_callback,
            10,
        )
        # Primary camera (exploreHD) — used for streaming and reconstruction capture
        self.camera_subscription = self.create_subscription(
            CompressedImage,
            '/camera/image_compressed',
            self.camera_image_callback,
            10,
        )
        self.imu_subscription = self.create_subscription(
            Imu,
            '/imu/data_raw',
            self.imu_callback,
            10,
        )

        self.client = self.create_client(
            RunReconstruction,
            'run_reconstruction',
        )
        self.status_pub = self.create_publisher(String, 'status', 10)

        self.get_logger().info("Jetson node started and listening for commands...")

    def camera_image_callback(self, msg: CompressedImage):
        try:
            np_arr = np.frombuffer(msg.data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if frame is None:
                raise ValueError("OpenCV returned an empty frame")
            self.latest_camera_frame = frame
        except Exception as e:
            self.get_logger().error(f"Failed to decode camera image: {e}")

    def command_callback(self, msg: String):
        command = msg.data
        self.get_logger().info(f"Received command: {command}")

        if command == "run_reconstruction":
            self.start_reconstruction_capture()
        elif command == "forward":
            self.move_forward()
        elif command == "backward":
            self.move_backward()
        elif command == "stop":
            self.stop_motors()
        else:
            self.get_logger().warn(f"Unknown command: {command}")

    def move_forward(self):
        self.get_logger().info("Moving forward (placeholder)")

    def move_backward(self):
        self.get_logger().info("Moving backward (placeholder)")

    def stop_motors(self):
        self.get_logger().info("Stopping motors (placeholder)")

    def start_reconstruction_capture(self):
        if self.capture_in_progress:
            self.get_logger().warn("Capture already in progress")
            self.status_pub.publish(String(data="reconstruction_busy"))
            return

        self.capture_in_progress = True
        self.capture_count = 0

        if self.capture_timer is not None:
            self.capture_timer.cancel()
            self.destroy_timer(self.capture_timer)
            self.capture_timer = None

        if self.capture_dir.exists():
            try:
                shutil.rmtree(self.capture_dir)
            except OSError as e:
                self.get_logger().warn(f"Could not clear capture dir: {e}")
        self.capture_dir.mkdir(parents=True, exist_ok=True)

        self.status_pub.publish(String(data="reconstruction_started"))
        self.get_logger().info(
            f"Capturing {self.capture_target_count} images from exploreHD "
            f"with {self.capture_interval_s:.1f}s spacing"
        )

        self.capture_image_tick()
        if self.capture_in_progress:
            self.capture_timer = self.create_timer(
                self.capture_interval_s,
                self.capture_image_tick,
            )

    def capture_image_tick(self):
        if not self.capture_in_progress:
            return

        if self.latest_camera_frame is None:
            self.get_logger().warn("No camera frame available yet; waiting for the next tick")
            return

        image_path = self.capture_dir / f"capture_{self.capture_count:02d}.jpg"
        if not cv2.imwrite(str(image_path), self.latest_camera_frame):
            self.get_logger().error(f"Failed to save image to {image_path}")
            self.finish_capture("reconstruction_failed")
            return

        self.capture_count += 1
        self.get_logger().info(
            f"Saved image {self.capture_count}/{self.capture_target_count}: {image_path}"
        )

        if self.capture_count >= self.capture_target_count:
            self.finish_capture("capture_complete")
            self.send_reconstruction_request()

    def finish_capture(self, status: str):
        if self.capture_timer is not None:
            self.capture_timer.cancel()
            self.destroy_timer(self.capture_timer)
            self.capture_timer = None

        self.capture_in_progress = False
        self.status_pub.publish(String(data=status))

    def imu_callback(self, msg: Imu):
        ax = msg.linear_acceleration.x
        ay = msg.linear_acceleration.y
        az = msg.linear_acceleration.z
        gx = msg.angular_velocity.x
        gy = msg.angular_velocity.y
        gz = msg.angular_velocity.z
        self.get_logger().debug(
            f"IMU Accel: ({ax:.2f}, {ay:.2f}, {az:.2f}) | "
            f"Gyro: ({gx:.2f}, {gy:.2f}, {gz:.2f})"
        )

    def send_reconstruction_request(self):
        req = RunReconstruction.Request()
        req.image_folder = str(self.capture_dir)

        if not self.client.wait_for_service(timeout_sec=1.0):
            self.get_logger().error("Reconstruction service not available")
            self.status_pub.publish(String(data="reconstruction_failed"))
            return

        future = self.client.call_async(req)
        future.add_done_callback(self._on_reconstruction_response)

    def _on_reconstruction_response(self, future):
        try:
            response = future.result()
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f"Reconstruction call failed: {exc}")
            self.status_pub.publish(String(data="reconstruction_failed"))
            return

        self.get_logger().info(f"Success: {response.success}")
        self.get_logger().info(f"Path: {response.model_path}")

        status = "reconstruction_done" if response.success else "reconstruction_failed"
        self.status_pub.publish(String(data=status))


def main(args=None):
    rclpy.init(args=args)
    node = JetsonNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
