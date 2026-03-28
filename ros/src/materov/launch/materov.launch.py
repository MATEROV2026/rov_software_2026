from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():

    # For now, just launch the jetson node (camera requires ZED SDK)
    jetson_node = Node(
        package='materov',
        executable='jetson_node',
        name='jetson_node'
    )

    return LaunchDescription([
        jetson_node
    ])