from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():

    zed_launch_path = os.path.join(
        get_package_share_directory('zed_wrapper'),
        'launch',
        'zed_camera.launch.py'
    )
    
    zed_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(zed_launch_path),
        launch_arguments={
            'camera_model': 'zed2i',   # or zed, zed2, etc.
            'publish_tf': 'true'
        }.items()
    )

    # For now, just launch the jetson node (camera requires ZED SDK)
    jetson_node = Node(
        package='materov',
        executable='jetson_node',
        name='jetson_node'
    )

    imu_sensor_node = Node(
        package='materov',
        executable='imu_sensor_node',
        name='imu_sensor_node'
    )

    pressure_sensor_node = Node(
        package='materov',
        executable='pressure_sensor_node',
        name='pressure_sensor_node'
    )


    return LaunchDescription([
        jetson_node,
        imu_sensor_node,
        pressure_sensor_node,
        zed_launch
    ])