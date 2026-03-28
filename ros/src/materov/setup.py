from setuptools import find_packages, setup

package_name = 'materov'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/materov.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='m8rov123',
    maintainer_email='a.h.hamzeh@wustl.edu',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'jetson_node = materov.jetson_node:main',
            'camera_node = materov.camera_node:main'
        ],
    },
)
