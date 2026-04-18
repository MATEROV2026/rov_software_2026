import rclpy
from rclpy.node import Node
from interfaces.srv import RunReconstruction


class ReconstructionService(Node):

    def __init__(self):
        super().__init__('reconstruction_service')

        self.srv = self.create_service(
            RunReconstruction,
            'run_reconstruction',
            self.handle_request
        )

        self.get_logger().info("Reconstruction service ready")

    def handle_request(self, request, response):
        self.get_logger().info(f"Received request: {request.image_folder}")

        # 🔧 FAKE processing for now (NO COLMAP yet)
        self.get_logger().info("Pretending to run reconstruction...")

        response.success = True
        response.model_path = "/fake/model.ply"

        return response


def main():
    rclpy.init()
    node = ReconstructionService()
    rclpy.spin(node)
    rclpy.shutdown()