import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
import serial


class SignalPublisherNode(Node):
    def __init__(self):
        super().__init__('signal_publisher')
        # Subscribe to the /joy topic published by your other package
        self.subscription = self.create_subscription(
            Joy,
            'joy',
            self.joy_callback,
            10)

        self.info_dic = [1500, 1500, 1500, 1500, 1500, 1500]

        self.ser = serial.Serial(
            port="/dev/ttyUSB0",
            baudrate=115200,
            timeout=0.01
        )

        # 100 Hz timer → 0.01 seconds
        self.timer = self.create_timer(0.01, self.serial_timer_callback)

        self.get_logger().info("Signal publisher node started. Move your controller to controll thrusters.")

    def serial_timer_callback(self):
        message = self.list2message(self.info_dic)
        self.ser.write(message)
        # message = self.info_dic[0]
        print(message)

    def list2message(self, list): # info_dic to serial message
        value = list[0] - 1500
        return value.to_bytes(2, byteorder="little", signed=True)


    def joy_callback(self, msg):

        # Get the buttons and axes vector as a simple list
        buttons_list = list(msg.buttons)
        axes_list = list(msg.axes)

        # Log the formatted output
        # self.get_logger().info(f"Axes:   {buttons_list}")
        # self.get_logger().info(f"Buttons: {buttons_list}\n---")

        # Translate controller input into signals for thrusters
        # info_dic : { thruster_number : pulse }
        if axes_list[1] <= -0.8:         # forward
            self.info_dic = [1900, 1900, 1500, 1500, 1400, 1400]

        elif axes_list[1] >= 0.8:        # backward
            self.info_dic = [1400, 1400, 1500, 1500, 1900, 1900]

        elif axes_list[0] <= -0.8:       # left
            self.info_dic = [1400, 1900, 1500, 1500, 1400, 1900]

        elif axes_list[0] >= 0.8:        # right
            self.info_dic = [1900, 1400, 1500, 1500, 1900, 1400]

        elif buttons_list[3] == 1:       # up
            self.info_dic = [1500, 1500, 1900, 1900, 1500, 1500]

        elif buttons_list[0] == 1:       # down
            self.info_dic = [1500, 1500, 1100, 1100, 1500, 1500]

        elif buttons_list[4] == 1:       # turn left
            self.info_dic = [1400, 1900, 1500, 1500, 1900, 1400]

        elif buttons_list[5] == 1:       # turn right
            self.info_dic = [1900, 1400, 1500, 1500, 1400, 1900]

        else:
            self.info_dic = [1500, 1500, 1500, 1500, 1500, 1500]

        # print(self.info_dic)     



def main(args=None):
    rclpy.init(args=args)
    node = SignalPublisherNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
