import random
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
import serial
import argparse
import numpy as np


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


def axis2command(x):
    factor = map2factor(x)
    if factor is None:
        return 0.0
    return float(factor)


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


THRUSTER_GEOMETRY = [
    {"type": "horizontal", "x": 0.225, "y": -0.185, "z": 0.00, "angle_deg": 45.0},
    {"type": "horizontal", "x": 0.225, "y": 0.185, "z": 0.00, "angle_deg": 315.0},
    {"type": "vertical",   "x": 0.000, "y": -0.185, "z": 0.00, "vertical_sign": 1.0},
    {"type": "vertical",   "x": 0.000, "y": 0.185, "z": 0.00, "vertical_sign": 1.0},
    {"type": "horizontal", "x": -0.225, "y": -0.185, "z": 0.00, "angle_deg": 135.0},
    {"type": "horizontal", "x": -0.225, "y": 0.185, "z": 0.00, "angle_deg": 225.0},
]


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
        self.seventh_value = 1500
        self._prev_buttons = []
        self.ramp_mode = ramp_mode
        if self.ramp_mode == "sync":
            self.ramp_steps = int(hz * 0.2)  # 3 second ramp
        elif self.ramp_mode == "async":
            self.ramp_steps = int(hz * 0.05)  # 3 second ramp
        self.active_thruster = 0
        self._async_queue = []
        self.wrench_gains = np.array([1.0, 1.0, 1.0, 1.0], dtype=float)
        self.B = self.build_tam(THRUSTER_GEOMETRY)
        self.B_pinv = np.linalg.pinv(self.B)

        self._port = port
        self._baudrate = baudrate
        self.ser = self._try_open_serial()

        # 100 Hz timer → 0.01 seconds
        self.timer = self.create_timer(1.0 / hz, self.serial_timer_callback)
        self._serial_retry_timer = self.create_timer(5.0, self._retry_serial)

        self.get_logger().info("Signal publisher node started. Move your controller to control thrusters.")
       
    def _try_open_serial(self):
        try:
            ser = serial.Serial(port=self._port, baudrate=self._baudrate, timeout=0.01)
            self.get_logger().info(f"Serial port {self._port} opened at {self._baudrate} baud.")
            return ser
        except serial.SerialException as e:
            self.get_logger().error(
                f"Could not open serial port {self._port}: {e} -- running without hardware; thruster signals will NOT be sent."
            )
            return None

    def _retry_serial(self):
        if self.ser is not None:
            self._serial_retry_timer.cancel()
            return
        self.ser = self._try_open_serial()
        if self.ser is not None:
            self._serial_retry_timer.cancel()

    def build_tam(self, thruster_geometry):
        columns = []

        for thruster in thruster_geometry:
            if thruster["type"] == "horizontal":
                columns.append(self.horizontal_column(thruster))
            elif thruster["type"] == "vertical":
                columns.append(self.vertical_column(thruster))
            else:
                raise ValueError(f"Unknown thruster type: {thruster['type']}")

        return np.column_stack(columns)

    def horizontal_column(self, thruster):
        x = float(thruster["x"])
        y = float(thruster["y"])
        angle_deg = float(thruster["angle_deg"])
        angle_rad = np.deg2rad(angle_deg)

        dx = np.cos(angle_rad)
        dy = np.sin(angle_rad)
        mz = x * dy - y * dx

        return np.array([dx, dy, 0.0, mz], dtype=float)

    def vertical_column(self, thruster):
        vertical_sign = float(thruster["vertical_sign"])
        return np.array([0.0, 0.0, vertical_sign, 0.0], dtype=float)

    def allocate_thrusters(self, tau):
        f = self.B_pinv @ tau

        max_abs = np.max(np.abs(f))
        if max_abs > 1.0:
            f = f / max_abs

        pwm = 1500.0 + 400.0 * f
        pwm = np.clip(pwm, 1100.0, 1900.0)

        return [int(round(v)) for v in pwm]

    def serial_timer_callback(self):

        header = bytes([0xAA, 0x55])
        length = bytes([0x0E])  # 14 bytes: 7 x int16

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
        m = self.list2message(self.current_values + [int(self.seventh_value)])
        crc_val = crc8(header + length + m)
        message = header + length + m + bytes([crc_val])
        if self.ser is not None:
            try:
                self.ser.write(message)
            except serial.SerialException:
                self.get_logger().warn("Serial port lost — will retry every 5s.")
                self.ser = None
                self._serial_retry_timer = self.create_timer(5.0, self._retry_serial)

            
    def list2message(self, values):
        message = b""
        for v in values:
            adjusted = max(-280, min(280, int(v - 1500)))  # 70% of T200 range (±400)
            message += adjusted.to_bytes(2, byteorder="little", signed=True)
        return message

    def destroy_node(self):
        if self.ser is not None and self.ser.is_open:
            self.ser.close()
        super().destroy_node()

    def joy_callback(self, msg):

        # Get the buttons and axes vector as a simple list
        buttons_list = list(msg.buttons)
        axes_list = list(msg.axes)

        # Log the formatted output
        # self.get_logger().info(f"Axes:   {buttons_list}")
        # self.get_logger().info(f"Buttons: {buttons_list}\n---")

        # Translate controller input into desired wrench and then into thruster signals
        # tau = [Fx, Fy, Fz, Mz]
        surge = -axis2command(axes_list[1])   # left stick Y  → +Fx forward
        sway = axis2command(axes_list[0])     # left stick X  → +Fy right
        heave = -axis2command(axes_list[4])   # right stick Y → +Fz up

        yaw = 0.0
        if buttons_list[4] == 1:       # LB → turn left
            yaw += 1.0
        if buttons_list[5] == 1:       # RB → turn right
            yaw -= 1.0

        tau = np.array([surge, sway, heave, yaw], dtype=float)
        tau = self.wrench_gains * tau

        if np.allclose(tau, 0.0):
            self.target_values = [1500, 1500, 1500, 1500, 1500, 1500]
        else:
            self.target_values = self.allocate_thrusters(tau)

        # 7th signal — X (buttons[2]) increments, B (buttons[1]) decrements (edge-triggered)
        if self._prev_buttons:
            if buttons_list[2] and not self._prev_buttons[2]:   # X pressed
                self.seventh_value = min(1900, self.seventh_value + 5)
            if buttons_list[1] and not self._prev_buttons[1]:   # B pressed
                self.seventh_value = max(1100, self.seventh_value - 5)
        self._prev_buttons = buttons_list

    




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
