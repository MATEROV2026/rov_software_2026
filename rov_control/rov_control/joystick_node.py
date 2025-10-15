import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
import random
import time
import pygame


    
class JoystickNode(Node):
    def __init__(self):
        super().__init__('joystick_node')
        pygame.init()
        pygame.joystick.init()
        print(pygame.joystick.get_count())
        self.joystick = pygame.joystick.Joystick(0) 
        self.joystick.init()
    
        super().__init__('joystick_node')
        self.publisher_ = self.create_publisher(Joy, 'joy', 10)
        self.timer = self.create_timer(0.5, self.timer_callback)
        self.get_logger().info('Joystick node started.')

    def timer_callback(self): 
        msg = Joy()
        msg.buttons=[self.joystick.get_buttons(i) for i in range(self.joystick.get_numbuttons())] 
        msg.axes = [self.joystick.get_axes(i) for i in range(self.joystick.get_numaxes())] 
        self.publisher_.publish(msg)
        self.get_logger().info(f'Published Joy message: {msg}')

def main(args=None):
    rclpy.init(args=args)
    node = JoystickNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()