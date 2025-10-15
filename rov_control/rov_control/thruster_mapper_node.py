# import rclpy
# from rclpy.node import Node
# from sensor_msgs.msg import Joy
# from std_msgs.msg import Float32MultiArray # Using a different message type

# class ThrusterMapperNode(Node):
#     def __init__(self):
#         super().__init__('thruster_mapper')
#         self.subscription = self.create_subscription(
#             Joy, 'joy', self.joy_callback, 10)
#         self.publisher_ = self.create_publisher(
#             Float32MultiArray, 'thruster_power', 10)
#         self.get_logger().info("Thruster Mapper Node Started")

#     def joy_callback(self, msg):
#         # A simple mapping from joystick axes to 4 thrusters
#         # Left stick up/down for forward/backward
#         forward_power = msg.axes[1]
#         # Left stick left/right for strafe
#         strafe_power = msg.axes[0]

#         # Create a message to publish
#         thruster_msg = Float32MultiArray()
#         thruster_msg.data = [forward_power, -forward_power, strafe_power, -strafe_power]

#         self.publisher_.publish(thruster_msg)
#         self.get_logger().info(f'Publishing Thruster Power: {thruster_msg.data}')

# def main(args=None):
#     rclpy.init(args=args)
#     node = ThrusterMapperNode()
#     rclpy.spin(node)
#     node.destroy_node()
#     rclpy.shutdown()

# if __name__ == '__main__':
#     main()

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
        self.get_logger().info(f'Publishing Power: {thruster_msg.power_values}')

def main(args=None):
    rclpy.init(args=args)
    node = ThrusterMapperNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

