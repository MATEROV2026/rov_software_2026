# Nano Launch

## Prerequisites

```bash
sudo apt install -y ros-humble-rmw-cyclonedds-cpp python3-serial
sudo usermod -a -G dialout $USER  # then re-login
```

## Launch sequence

```bash
source ~/ros2_ws/install/setup.bash
source ~/materov_workspace/rov_software_2026/ros/install/setup.bash
export ROS_LOCALHOST_ONLY=0
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="file:///home/m8rov123/materov_workspace/rov_software_2026/ros/config/jetson/cyclonedds.xml"
ros2 launch materov materov.launch.py
```

Or run the setup script first on a fresh machine (builds packages, checks deps):

```bash
bash scripts/setup_nano.sh
```

## Nodes started

| Node | Topic(s) |
|---|---|
| `jetson_node` | sub: `commands`, `camera`, `/imu/data_raw`; pub: `status` |
| `signal_publisher_node` | sub: `/joy`; serial PWM → MCU at `/dev/ttyUSB0` |
| `imu_sensor_node` | pub: `/imu/data_raw` (I2C-7, addr 0x68) |
| `pressure_sensor_node` | pub: `/pressure/data_raw` (I2C-7, addr 0x76) |
| `zed_node` | pub: `/zed/zed_node/rgb/image_rect_color` + depth/IMU topics |

## Notes

- ZED ROS2 wrapper lives in `~/ros2_ws` — must be sourced before launching
- IMU and pressure nodes crash if sensors are not physically wired (expected during bench testing)
- `signal_publisher_node` degrades gracefully if MCU is not connected
- Laptop must run with `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` and `CYCLONEDDS_URI` pointing to `ros/config/laptop/cyclonedds.xml` to discover Nano nodes over DDS
