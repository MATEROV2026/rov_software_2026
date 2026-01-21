import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
import serial

info_dic = {0: 1500, 1: 1500, 2: 1500, 3: 1500,
            4: 1500, 5: 1500}

class SignalPublisherNode(Node):
    def __init__(self):
        super().__init__('signal_publisher')
        # Subscribe to the /joy topic published by your other package
        self.subscription = self.create_subscription(
            Joy,
            'joy',
            self.joy_callback,
            10)
        self.get_logger().info("Signal publisher node started. Move your controller to controll thrusters.")

    def joy_callback(self, msg):

        # Get the buttons and axes vector as a simple list
        buttons_list = list(msg.buttons)
        axes_list = list(msg.axes)

        self.get_logger().info(f"Type of axes_list: {type(axes_list)}")
        self.get_logger().info(f"Length of axes_list: {len(axes_list)}")
        self.get_logger().info(f"Type of buttons_list: {type(buttons_list)}")
        self.get_logger().info(f"Length of buttons_list: {len(buttons_list)}")

        # Log the formatted output
        self.get_logger().info(f"Axes:   {buttons_list}")
        self.get_logger().info(f"Buttons: {buttons_list}\n---")

        # Translate controller input into signals for thrusters
        # info_dic : { thruster_number : pulse }
        if axes_list[1] <= -0.8:         # move forward
            info_dic[0] = 1900
            info_dic[1] = 1900
            info_dic[2] = 1500
            info_dic[3] = 1500
            info_dic[4] = 1400
            info_dic[5] = 1400

        elif axes_list[1] >= 0.8:      # move backward
            info_dic[0] = 1400
            info_dic[1] = 1400
            info_dic[2] = 1500
            info_dic[3] = 1500
            info_dic[4] = 1900
            info_dic[5] = 1900

        elif axes_list[0] <= -0.8:       # move left
            info_dic[0] = 1400
            info_dic[1] = 1900
            info_dic[2] = 1500
            info_dic[3] = 1500
            info_dic[4] = 1400
            info_dic[5] = 1900

        elif axes_list[0] >= 0.8:      # move right  
            info_dic[0] = 1900
            info_dic[1] = 1400
            info_dic[2] = 1500
            info_dic[3] = 1500
            info_dic[4] = 1900
            info_dic[5] = 1400

        elif buttons_list[3] == 1:      # move up
            info_dic[0] = 1500
            info_dic[1] = 1500
            info_dic[2] = 1900
            info_dic[3] = 1900
            info_dic[4] = 1500
            info_dic[5] = 1500

        elif buttons_list[0] == 1:      # move down
            info_dic[0] = 1500
            info_dic[1] = 1500
            info_dic[2] = 1100
            info_dic[3] = 1100
            info_dic[4] = 1500
            info_dic[5] = 1500

        elif buttons_list[4] == 1:      # turn left
            info_dic[0] = 1400
            info_dic[1] = 1900
            info_dic[2] = 1500
            info_dic[3] = 1500
            info_dic[4] = 1900
            info_dic[5] = 1400

        elif buttons_list[5] == 1:      # turn right
            info_dic[0] = 1900
            info_dic[1] = 1400
            info_dic[2] = 1500
            info_dic[3] = 1500
            info_dic[4] = 1400
            info_dic[5] = 1900

        else:                           # idle state
            info_dic[0] = 1500
            info_dic[1] = 1500
            info_dic[2] = 1500
            info_dic[3] = 1500
            info_dic[4] = 1500
            info_dic[5] = 1500     

        print(info_dic)     
            
        # establish serial connection and write messages
        # ser = serial.Serial(port = "/dev/ttyACM0")
        # print(ser.name)

        # message = dic2message(info_dic)
        # ser.write(message)
        # ser.close()

def dic2message(dic):
    message = ""

    for key in list(dic.keys()):
        message += key + " " + dic[key] + "\n"

    return message


def main(args=None):
    rclpy.init(args=args)
    node = SignalPublisherNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
