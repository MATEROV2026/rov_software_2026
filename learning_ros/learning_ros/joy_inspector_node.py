import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
import serial

class JoyInspectorNode(Node):
    def __init__(self):
        super().__init__('joy_inspector')
        # Subscribe to the /joy topic published by your other package
        self.subscription = self.create_subscription(
            Joy,
            'joy',
            self.joy_callback,
            10)
        self.get_logger().info("Joy Inspector node started. Move your controller to see the data.")

    def joy_callback(self, msg):
        # Format the axes vector for clean printing, rounding to 2 decimal places
        axes_str = ", ".join([f"{val:.2f}" for val in msg.axes])

        # Get the buttons vector as a simple list
        buttons_list = list(msg.buttons)
        axes_list = list(msg.axes)

        # Log the formatted output
        self.get_logger().info(f"Axes:   [{axes_str}]")
        self.get_logger().info(f"Buttons: {buttons_list}\n---")

        # Construct message
        # message : <thruster_number> <pulse>
        message = ""

        for i, button in enumerate(buttons_list):
            if i < 8 and button == 1:
                message += i # use a button to represent which thruster to control
                message += " "
                message += 1500 - axes_list[1] * 400    # readin joystick movement and change to scale (1100, 1900)
                                                        # axes_list[1] is left stick vertical movement
                                                        # axes : -1 up, 1 down (inverted)
                message += "\n"
                break
            
        # establish serial connection and write messages
        ser = serial.Serial(port = "/dev/ttyACM0")
        print(ser.name)
        ser.write(message)
        ser.close()



def main(args=None):
    rclpy.init(args=args)
    node = JoyInspectorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
