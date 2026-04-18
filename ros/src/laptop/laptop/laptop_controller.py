class LaptopController:
    def __init__(self):
        import rclpy
        from rclpy.node import Node
        from std_msgs.msg import String
        from interfaces.srv import RunReconstruction

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

        msg = String()
        msg.data = command
        self.command_publisher.publish(msg)
        self.node.get_logger().info(f"Sent command: {command}")
