from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():

    ui_node = Node(
        package="laptop",
        executable="vision_node",
        name="vision_node"
    )
    
    return LaunchDescription(
        ui_node
    )