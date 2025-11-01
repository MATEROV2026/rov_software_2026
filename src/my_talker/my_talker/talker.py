# 1. Imports
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

# 2. The Class Definition
class TalkerNode(Node):
    # 3. The Constructor
    def __init__(self):
        super().__init__('talker_node_name') # The name ROS 2 sees
        
        # Create components (publishers, subscribers, timers, etc.)
        self.publisher_ = self.create_publisher(String, 'chatter', 10)
        self.timer = self.create_timer(1.0, self.timer_callback)
        self.i = 0

    # 4. Callback Functions
    def timer_callback(self):
        msg = String()
        msg.data = f'Hello World: {self.i}'
        self.publisher_.publish(msg)
        self.i += 1

# 5. The Main Function (Boilerplate)
def main(args=None):
    rclpy.init(args=args)
    talker_node = TalkerNode()
    rclpy.spin(talker_node)
    talker_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
