from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch_ros.actions import Node
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():

    zed_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('zed_wrapper'),
                'launch',
                'zed_camera.launch.py'
            )
        ),
        launch_arguments={
            'camera_model': 'zed2',
        }.items()
    )

    # Optional: republish compressed if needed
    republisher = Node(
        package='image_transport',
        executable='republish',
        name='image_republisher',
        arguments=[
            'raw', 'compressed'
        ],
        remappings=[
            ('in', '/zed/zed_node/rgb/image_rect_color'),
            ('out', '/camera/image_compressed')
        ]
    )

    return LaunchDescription([
        zed_launch,
        republisher
    ])