import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
try:
    from ament_index_python.packages import PackageNotFoundError
except ImportError:
    from ament_index_python.packages import PackageNotFoundError


def generate_launch_description():
    nodes = [
        Node(
            package='materov',
            executable='jetson_node',
            name='jetson_node'
        ),
        Node(
            package='materov',
            executable='camera_node',
            name='camera_node'
        ),
        Node(
            package='materov',
            executable='imu_sensor_node',
            name='imu_sensor_node'
        ),
        Node(
            package='materov',
            executable='pressure_sensor_node',
            name='pressure_sensor_node'
        ),
        Node(
            package='materov',
            executable='signal_publisher_node',
            name='signal_publisher'
        ),
    ]

    try:
        zed_launch_path = os.path.join(
            get_package_share_directory('zed_wrapper'),
            'launch',
            'zed_camera.launch.py'
        )
        zed_launch = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(zed_launch_path),
            launch_arguments={
                'camera_model': 'zed2i',
                'publish_tf': 'true'
            }.items()
        )
        nodes.append(zed_launch)
    except PackageNotFoundError:
        print(
            '[WARN] zed_wrapper not found in AMENT_PREFIX_PATH; skipping ZED launch.\n'
            '       Source ~/ros2_ws/install/setup.bash before launching to enable ZED.'
        )

    return LaunchDescription(nodes)
