class LaptopController:
    def __init__(self):
        import time
        import rclpy
        from rclpy.node import Node
        from std_msgs.msg import String
        from interfaces.srv import RunReconstruction

        self._time = time
        self._rclpy = rclpy
        rclpy.init()
        self.node = Node("laptop_controller")

        self.command_publisher = self.node.create_publisher(
            String,
            "commands",
            10
        )

        self.recon_client = self.node.create_client(
            RunReconstruction,
            "run_reconstruction"
        )

    def send_command(self, command: str):
        from std_msgs.msg import String

        deadline = self._time.monotonic() + 2.0
        while self.command_publisher.get_subscription_count() == 0 and self._time.monotonic() < deadline:
            self._rclpy.spin_once(self.node, timeout_sec=0.1)

        msg = String()
        msg.data = command

        # Short-lived CLI invocations need time for DDS discovery and delivery.
        for _ in range(3):
            self.command_publisher.publish(msg)
            self._rclpy.spin_once(self.node, timeout_sec=0.1)

        self.node.get_logger().info(f"Sent command: {command}")

    def close(self):
        self.node.destroy_node()
        self._rclpy.shutdown()
