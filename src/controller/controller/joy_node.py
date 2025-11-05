import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
import pygame


class JoystickNode(Node):
    """ROS2 node that publishes joystick input from pygame to the /joy topic.

    Improvements:
    - checks for joystick presence
    - configurable joystick index, publish rate and topic name
    - graceful pygame shutdown
    """

    def __init__(self):
        # Initialize node first
        super().__init__('joystick_node')

        # Parameters (can be overridden via ros2 param set or launch)
        self.declare_parameter('joystick_index', 0)
        self.declare_parameter('publish_rate_hz', 20.0)
        self.declare_parameter('topic', 'joy')

        self.joystick_index = self.get_parameter('joystick_index').value
        publish_rate = float(self.get_parameter('publish_rate_hz').value)
        self.topic_name = self.get_parameter('topic').value

        # Initialize pygame joystick subsystem
        pygame.init()
        pygame.joystick.init()

        joystick_count = pygame.joystick.get_count()
        if joystick_count <= 0:
            self.get_logger().error('No joystick found (pygame reports 0). Connect a joystick and try again.')
            raise RuntimeError('No joystick present')

        if self.joystick_index >= joystick_count:
            self.get_logger().error(f'Requested joystick_index={self.joystick_index} but only {joystick_count} attached.')
            raise RuntimeError('Invalid joystick_index')

        # Create joystick object
        try:
            self.joystick = pygame.joystick.Joystick(self.joystick_index)
            self.joystick.init()
        except Exception as e:
            self.get_logger().error(f'Failed to initialize joystick {self.joystick_index}: {e}')
            raise

        # Publisher and timer
        self.publisher_ = self.create_publisher(Joy, self.topic_name, 10)
        timer_period = 1.0 / max(1.0, publish_rate)
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.get_logger().info(f'Joystick node started on topic "{self.topic_name}" at {publish_rate} Hz (index {self.joystick_index}).')

    def timer_callback(self):
        try:
            # Pump pygame events to update joystick state
            pygame.event.pump()

            msg = Joy()
            msg.buttons = [self.joystick.get_button(i) for i in range(self.joystick.get_numbuttons())]
            msg.axes = [self.joystick.get_axis(i) for i in range(self.joystick.get_numaxes())]

            self.publisher_.publish(msg)
            # Use debug level for frequent messages to avoid log spam
            self.get_logger().debug(f'Published Joy message: axes={msg.axes}, buttons={msg.buttons}')
        except Exception as e:
            self.get_logger().error(f'Error reading joystick state: {e}')

    def destroy_node(self):
        # Cleanup pygame on shutdown
        try:
            pygame.joystick.quit()
            pygame.quit()
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    try:
        node = JoystickNode()
    except Exception as e:
        # Initialization failed (e.g., no joystick); log and exit
        print(f'Joystick node failed to start: {e}')
        rclpy.shutdown()
        return

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
