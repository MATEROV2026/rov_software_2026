import random
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
import serial
import argparse


# DONE 1. documentation for the code
# DONE 2. single output to six serial output
# DONE 3. input parameters from command line (like hz)
# DONE 3.: (added by martin) This is not an urgent change but needs to be made when we decide to fully deploy!
# make serial messages framed so MCU can resync if bytes get dropped
# What we currently have is just raw 6x int16 values - that can desync in case of noise
# Example:
#   [0xAA][0x55][len=12][payload (6 int16 little-endian)][crc8]
# keep payload exactly same values as now (v - 1500), just wrap it in a frame
# update serial_timer_callback() to send the full frame instead of raw payload
#
# So it would look like:
#   AA 55 0C <12 payload bytes> <crc>

# DONE 5.: Whenever you go from one value to another in the interval force it to slowly ramp up/down over a second. 
# So if you send a signal of 100 it should take a second to search it and can ramp in periodic fragments {0, 25, 50, 75, 100}.
# Make the steps a higher number tho - maybe 10 or 15? We are doing this because we want to keep the difference in current low
# every time we throttle up or down. 
#### ramp up takes 2-3 seconds

# DONE 6.: Make an option to run is as a scattered ramp up - we do not want all 6 thrusters to synchronously ramp up or down (or any group of thrusters).
# So whenever you set any given group of thrusters to 100, they should reach that throttle asynchronously from each other. 
# IMPORTANT: That should not be noticeable in practice! So keep the gaps between them small
# There is most likely some stochastic approach to doing this efficiently, no need to overthink it.

# DONE 7.: For now cap your signal to be slightly above neutral! So map at maximum the equivalent of 1700 (if 1500 is neutral). 
# This is so that we avoid maxing out which would spike the difference in current



# maps [-1.0, 0.4] to [0.1, 1]
def map2factor(x):
    if -1 <= x <= -0.4:
        return 1.5 * x + 0.5
    elif 0.4 <= x <= 1:
        return 1.5 * x - 0.5


def crc8(data):
    crc = 0x00
    poly = 0x07

    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:  # if MSB is set
                crc = ((crc << 1) ^ poly) & 0xFF
            else:
                crc = (crc << 1) & 0xFF

    return crc

class SignalPublisherNode(Node):

    def __init__(self, port, baudrate, hz, ramp_mode):
        super().__init__('signal_publisher')
        # Subscribe to the /joy topic published by your other package
        self.subscription = self.create_subscription(
            Joy,
            'joy',
            self.joy_callback,
            10)

        self.current_values = [1500, 1500, 1500, 1500, 1500, 1500]
        self.target_values = [1500, 1500, 1500, 1500, 1500, 1500]
        self.ramp_mode = ramp_mode
        if self.ramp_mode == "sync":
            self.ramp_steps = int(hz * 0.2)  # 3 second ramp
        elif self.ramp_mode == "async":
            self.ramp_steps = int(hz * 0.05)  # 3 second ramp
        self.active_thruster = 0
        self._async_queue = []

        try:
            self.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=0.01
            )
            self.get_logger().info(f"Serial port {port} opened at {baudrate} baud.")
        except serial.SerialException as e:
            self.get_logger().fatal(f"Could not open serial port {port}: {e}")
            raise

        # 100 Hz timer → 0.01 seconds
        self.timer = self.create_timer(1.0 / hz, self.serial_timer_callback)

        self.get_logger().info("Signal publisher node started. Move your controller to controll thrusters.")
       

    def serial_timer_callback(self):

        header = bytes([0xAA, 0x55])
        length = bytes([0x0C])

        if self.ramp_mode == "sync":
            for i in range(6):
                diff = self.target_values[i] - self.current_values[i]
            
                if abs(diff) < 1:
                    self.current_values[i] = self.target_values[i]
                else:
                    self.current_values[i] += diff / self.ramp_steps

        elif self.ramp_mode == "async":
            if not self._async_queue:
                self._async_queue = list(range(6))
                random.shuffle(self._async_queue)

            i = self._async_queue.pop(0)

            diff = self.target_values[i] - self.current_values[i]

            if abs(diff) < 1:
                self.current_values[i] = self.target_values[i]
            else:
                self.current_values[i] += diff / self.ramp_steps

        self.get_logger().debug(f"current_values: {self.current_values}")
        m = self.list2message(self.current_values)
        crc_val = crc8(header + length + m)
        message = header + length + m + bytes([crc_val])
        self.ser.write(message)

            
    def list2message(self, values): # values_list to serial message
        
        message = b""

        for v in values:
            adjusted = int((v - 1500) * 0.5)   # make the max and min closer to neutral
            adjusted = max(-100, min(100, adjusted))
            message += adjusted.to_bytes(2, byteorder="little", signed=True)

        return message

    def destroy_node(self):
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()
        super().destroy_node()

    def joy_callback(self, msg):

        # Get the buttons and axes vector as a simple list
        buttons_list = list(msg.buttons)
        axes_list = list(msg.axes)

        # Log the formatted output
        # self.get_logger().info(f"Axes:   {buttons_list}")
        # self.get_logger().info(f"Buttons: {buttons_list}\n---")

        # Translate controller input into signals for thrusters
        # values_list : { thruster_number : pulse }
        base = 1500

        if (axes_list[1] <= -0.4 or     # forward
            axes_list[1] >= 0.4 or      # backward
            axes_list[0] <= -0.4 or     # left
            axes_list[0] >= 0.4):       # right

            count = 0
            temp = []

            # forward or backward
            if (axes_list[1] <= -0.4 or axes_list[1] >= 0.4):
                count += 1
                factor = map2factor(axes_list[1])
                deviation = [-400, -400, 0, 0, 400, 400]
                temp.append([factor * float(x) + base for x in deviation])
            
            # right or left
            if (axes_list[0] <= -0.4 or axes_list[0] >= 0.4):
                count += 1
                factor = map2factor(axes_list[0])
                deviation = [400, -400, 0, 0, 400, -400]
                temp.append([factor * float(x) + base for x in deviation])

            if count == 1:
                self.target_values = temp[0]
            else:
                self.target_values = [int((temp[0][i] + temp[1][i]) / 2) for i in range(6)]

        elif buttons_list[3] == 1:       # up
            self.target_values = [1500, 1500, 1900, 1900, 1500, 1500]

        elif buttons_list[0] == 1:       # down
            self.target_values = [1500, 1500, 1100, 1100, 1500, 1500]

        elif buttons_list[4] == 1:       # turn left
            self.target_values = [1100, 1900, 1500, 1500, 1900, 1100]

        elif buttons_list[5] == 1:       # turn right
            self.target_values = [1900, 1100, 1500, 1500, 1100, 1900]

        else:
            self.target_values = [1500, 1500, 1500, 1500, 1500, 1500]


        # print(self.target_values)

    




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

    parser.add_argument(
        "--ramp_mode",
        type=str,
        default="sync",
        choices=["sync", "async"],
        help="Ramp mode: sync (default) or async"
    )

    parsed_args, remaining = parser.parse_known_args(args=args)

    rclpy.init(args=remaining)
    node = SignalPublisherNode(
        port=parsed_args.port,
        baudrate=parsed_args.baudrate,
        hz=parsed_args.hz,
        ramp_mode=parsed_args.ramp_mode
    )

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
