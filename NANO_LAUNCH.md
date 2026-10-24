# Nano Launch

## First-time setup (run once)

```bash
bash scripts/install_autostart.sh
```

This installs:
- A systemd service that auto-launches the ROV stack on every boot
- A udev rule so `/dev/ttyUSB*` is accessible without sudo

After this, the Nano is plug-and-play — no manual launch needed.

## Manual launch (if needed)

Stop the service first to avoid duplicate nodes:

```bash
sudo systemctl stop rov-launch
```

Then launch manually:

```bash
source ~/ros2_ws/install/setup.bash
source ~/materov_workspace/rov_software_2026/ros/install/setup.bash
export ROS_LOCALHOST_ONLY=0
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="file:///home/m8rov123/materov_workspace/rov_software_2026/ros/config/jetson/cyclonedds.xml"
ros2 launch materov materov.launch.py
```

## Monitoring

```bash
sudo systemctl status rov-launch      # check if running
journalctl -u rov-launch -f           # live logs
sudo systemctl restart rov-launch     # restart stack
```

## Nodes started

| Node | Topic(s) |
|---|---|
| `jetson_node` | sub: `commands`, `/imu/data_raw`; pub: `status` |
| `camera_node` | pub: `/camera/image_compressed`, `/camera/image_raw` |
| `signal_publisher_node` | sub: `/joy`; serial PWM → MCU at `/dev/ttyUSB0` |
| `imu_sensor_node` | pub: `/imu/data_raw` (I2C-7, addr 0x68) |
| `pressure_sensor_node` | pub: `/pressure/data_raw` (I2C-7, addr 0x76) |
| `zed_node` | pub: `/zed/zed_node/rgb/image_rect_color` + depth/IMU topics |

## Notes

- IMU and pressure nodes crash until sensors are physically wired — rest of stack unaffected
- ZED ROS2 wrapper lives in `~/ros2_ws` — must be sourced before launching
- `camera_node` retries for 30s on startup to wait out ZED SDK initialization
- `signal_publisher_node` retries serial every 5s — PCB can be plugged in after boot
- Laptop must run with `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` and `CYCLONEDDS_URI` pointing to `ros/config/laptop/cyclonedds.xml`
