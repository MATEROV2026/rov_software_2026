from setuptools import setup

package_name = 'controller'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    install_requires=['setuptools', 'pygame'],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    zip_safe=True,
    maintainer='you',
    maintainer_email='you@example.com',
    description='Controller package: joystick publisher and inspector nodes',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'joy_node = controller.joy_node:main',
            'joy_inspector = controller.joy_inspector_node:main',
        ],
    },
)
