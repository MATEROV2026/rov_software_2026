import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
# Import your new custom message!
from rov_interfaces.msg import ThrusterPower 

class ThrusterMapperNode(Node):
    def __init__(self):
        super().__init__('thruster_mapper')
        self.subscription = self.create_subscription(
            Joy, 'joy', self.joy_callback, 10)
        self.publisher_ = self.create_publisher(
            ThrusterPower, 'thruster_power', 10)
        self.get_logger().info('ThrusterMapper node has been started')

    def joy_callback(self, msg):
        # Simple mapping from joystick axes to 6 thrusters
        # This logic will become much more complex for a real ROV
        forward = msg.axes[1]  # Left stick up/down
        strafe = msg.axes[0]   # Left stick left/right
        yaw = msg.axes[3]      # Right stick left/right
        vertical = msg.axes[4] # Right stick up/down

        # Create an instance of your custom message
        thruster_msg = ThrusterPower()
        # This is a placeholder mixing algorithm
        thruster_msg.power_values = [
            forward, forward, # Forward thrusters
            strafe, -strafe,  # Strafe thrusters
            vertical, vertical # Vertical thrusters
        ]
        self.publisher_.publish(thruster_msg)
        self.get_logger().debug(f'Published thruster powers: {thruster_msg.power_values}')

def main(args=None):
    print("Starting Thruster Mapper Node..." )
    rclpy.init(args=args)
    node = ThrusterMapperNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
