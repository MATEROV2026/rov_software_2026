import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
import math
import smbus
import time

bus = smbus.SMBus(7)
addr = 0x76

# Commands
RESET = 0x1E
ADC_READ = 0x00
PROM_READ = 0xA0

CONVERT_D1 = 0x48  # pressure
CONVERT_D2 = 0x58  # temperature


class PressureSensorNode(Node):
    def __init__(self):
        super().__init__('pressure_sensor_node')

        bus.write_byte(addr, RESET)
        time.sleep(0.1)

        # Read calibration data
        self.C = []
        for i in range(7):
            data = bus.read_word_data(addr, PROM_READ + i*2)
            # swap bytes
            data = ((data & 0xFF) << 8) | (data >> 8)
            self.C.append(data)



        self.pub = self.create_publisher(Float32, '/pressure/data_raw', 10)

        # 50 Hz
        self.timer = self.create_timer(0.02, self.publish_pressure)

        self.get_logger().info("Pressure publisher node started...")

    def publish_pressure(self):
        msg = Float32()

        bus.write_byte(addr, CONVERT_D1)
        time.sleep(0.02)
        D1 = self.read_adc()

        bus.write_byte(addr, CONVERT_D2)
        time.sleep(0.02)
        D2 = self.read_adc()

        dT = D2 - self.C[5] * 256
        TEMP = 2000 + dT * self.C[6] / 8388608

        OFF = self.C[2] * 65536 + (self.C[4] * dT) / 128
        SENS = self.C[1] * 32768 + (self.C[3] * dT) / 256

        P = (D1 * SENS / 2097152 - OFF) / 8192

        pressure_mbar = P / 100.0

        msg.data = pressure_mbar  

        self.pub.publish(msg)

        self.get_logger().info(f"Pressure: {pressure_mbar:.2f} mbar")
    
    def read_adc(self):
        data = bus.read_i2c_block_data(addr, ADC_READ, 3)
        return data[0] << 16 | data[1] << 8 | data[2]
    


def main(args=None):
    rclpy.init(args=args)
    node = PressureSensorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()