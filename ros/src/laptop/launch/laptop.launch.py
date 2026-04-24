from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    vision_node = Node(
        package="laptop",
        executable="vision_node",
        name="vision_node",
        output="screen",
    )

    reconstruction_service = Node(
        package="laptop",
        executable="reconstruction_service",
        name="reconstruction_service",
        output="screen",
    )

    joy_node = Node(
        package="joy_linux",
        executable="joy_linux_node",
        name="joy_linux_node",
        output="screen",
    )

    return LaunchDescription([
        vision_node,
        reconstruction_service,
        joy_node,
    ])
