from setuptools import find_packages, setup

package_name = 'learning_ros'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='dingmingyue05@126.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'talker = learning_ros.talker_node:main',
            'listener = learning_ros.listener_node:main',
            'joy_inspector = learning_ros.joy_inspector_node:main',
            'calculator_client = learning_ros.calculator_client',
            'signal_publisher = learning_ros.signal_publisher_node:main',
        ],
    },
)
