import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
import serial
import argparse


# TODO 1. documentation for the code
# TODO 2. single output to six serial output
# TODO 3. input parameters from command line (like hz)


class SignalPublisherNode(Node):

    def __init__(self, port, baudrate, hz):
        super().__init__('signal_publisher')
        # Subscribe to the /joy topic published by your other package
        self.subscription = self.create_subscription(
            Joy,
            'joy',
            self.joy_callback,
            10)

        self.values_list = [1500, 1500, 1500, 1500, 1500, 1500]

        self.ser = serial.Serial(
            port = port,
            baudrate = baudrate,
            timeout = 0.01
        )

        # 100 Hz timer → 0.01 seconds
        self.timer = self.create_timer(1.0 / hz, self.serial_timer_callback)

        self.get_logger().info("Signal publisher node started. Move your controller to controll thrusters.")

    def serial_timer_callback(self):
        message = self.list2message(self.values_list)
        self.ser.write(message)
        # message = self.values_list[0]
        print(message)

    def list2message(self, values): # values_list to serial message
        
        message = b""

        for v in values:
            adjusted = v - 1500
            message += adjusted.to_bytes(2, byteorder="little", signed=True)

        return message


    def joy_callback(self, msg):

        # Get the buttons and axes vector as a simple list
        buttons_list = list(msg.buttons)
        axes_list = list(msg.axes)

        # Log the formatted output
        # self.get_logger().info(f"Axes:   {buttons_list}")
        # self.get_logger().info(f"Buttons: {buttons_list}\n---")

        # Translate controller input into signals for thrusters
        # values_list : { thruster_number : pulse }
        full_speed = [1500, 1500, 1500, 1500, 1500, 1500]

        if axes_list[1] <= -0.4:         # forward
            full_speed = [1900, 1900, 1500, 1500, 1100, 1100]
            factor = (axes_list[1] * 5 / 3) + (2 /3)
            # print(factor)
            self.values_list =  [int(factor * float(x)) for x in full_speed]
            # print(self.values_list)
        elif axes_list[1] >= 0.8:        # backward
            self.values_list = [1100, 1100, 1500, 1500, 1900, 1900]

        elif axes_list[0] <= -0.8:       # left
            self.values_list = [1100, 1900, 1500, 1500, 1100, 1900]

        elif axes_list[0] >= 0.8:        # right
            self.values_list = [1900, 1100, 1500, 1500, 1900, 1100]

        elif buttons_list[3] == 1:       # up
            self.values_list = [1500, 1500, 1900, 1900, 1500, 1500]

        elif buttons_list[0] == 1:       # down
            self.values_list = [1500, 1500, 1100, 1100, 1500, 1500]

        elif buttons_list[4] == 1:       # turn left
            self.values_list = [1100, 1900, 1500, 1500, 1900, 1100]

        elif buttons_list[5] == 1:       # turn right
            self.values_list = [1900, 1100, 1500, 1500, 1100, 1900]

        else:
            self.values_list = [1500, 1500, 1500, 1500, 1500, 1500]

        # print(self.values_list)     



def main(args=None):
    parser = argparse.ArgumentParser(description="Signal Publisher Node")

    parser.add_argument(
        "--port",
        type=str,
        default="/dev/ttyUSB0",
        help="Serial port (default: /dev/ttyUSB0)"
    )

    parser.add_argument(
        "--baudrate",
        type=int,
        default=115200,
        help="Serial baudrate (default: 115200)"
    )

    parser.add_argument(
        "--hz",
        type=float,
        default=100.0,
        help="Timer frequency in Hz (default: 100)"
    )

    parsed_args, remaining = parser.parse_known_args(args=args)

    rclpy.init(args=remaining)
    node = SignalPublisherNode(
        port=parsed_args.port,
        baudrate=parsed_args.baudrate,
        hz=parsed_args.hz
    )

    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
