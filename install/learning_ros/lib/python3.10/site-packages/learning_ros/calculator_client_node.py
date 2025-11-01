import sys
from rov_interfaces.srv import AddTwoInts
import rclpy
from rclpy.node import Node

class CalculatorClient(Node):
    def __init__(self):
        super().__init__('calculator_client')
        self.cli = self.create_client(AddTwoInts, 'add_two_ints')
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('service not available, waiting again...')
        self.req = AddTwoInts.Request()

    def send_request(self, a, b):
        self.req.a = a
        self.req.b = b
        return self.cli.call(self.req)

def main(args=None):
    rclpy.init(args=args)
    client = CalculatorClient()
    response = client.send_request(int(sys.argv[1]), int(sys.argv[2]))
    client.get_logger().info(f'Result of add_two_ints: {response.sum}')
    client.destroy_node()
    rclpy.shutdown()
