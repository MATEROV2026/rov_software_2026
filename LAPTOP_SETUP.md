# Laptop Setup — Status & Launch Guide

## Prerequisites

```bash
sudo apt install -y ros-humble-desktop python3-colcon-common-extensions ros-humble-rmw-cyclonedds-cpp
```

Then build the ROS workspace (only needed once, or after source changes):

```bash
export PATH="/usr/bin:$PATH"
source /opt/ros/humble/setup.bash
cd /home/materov/ahmad/rov_software_2026/ros
colcon build --packages-select interfaces laptop
```

## Launch sequence

```bash
export PATH="/usr/bin:$PATH"
source /home/materov/ahmad/rov_software_2026/ros/install/setup.bash
export ROS_LOCALHOST_ONLY=0
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="file:///home/materov/ahmad/rov_software_2026/ros/config/laptop/cyclonedds.xml"
ros2 launch laptop laptop.launch.py
```

Or run the setup script first on a fresh machine (checks deps, offers to build):

```bash
bash scripts/setup_laptop.sh
```

## Nodes started

| Node | Package | What it does |
|---|---|---|
| `vision_node` | `laptop` | Subscribes to both camera feeds and displays two OpenCV windows: `"Claw / Movement Camera (exploreHD)"` from `/camera/image_compressed` and `"ZED Camera"` from `/zed/zed_node/rgb/image_rect_color/compressed`. W/S/Q keys in the claw window publish to `commands`. |
| `reconstruction_service` | `laptop` | ROS service server for `RunReconstruction`; stub for now |
| `joy_linux_node` | `joy_linux` | Reads joystick from `/dev/input/js0`, publishes `/joy` — DDS carries this to the Nano's `signal_publisher_node` automatically |

## Network

- **Laptop Ethernet** (`enp8s0`): `192.168.2.1/24` — static
- **Nano Ethernet** (`enP8p1s0`): `192.168.2.2` — reachable over direct Ethernet link
- **DDS**: CycloneDDS (`rmw_cyclonedds_cpp`), laptop config pins to `enp8s0` only so the WiFi interface (`192.168.1.x`) is never advertised to the Nano

## Python environment note

The machine has Miniconda (Python 3.13) alongside system Python 3.10. ROS Humble requires 3.10 — its C extensions will not load under 3.13. The `export PATH="/usr/bin:$PATH"` line above ensures `python3` resolves to 3.10 before Conda's version. This must be set in every terminal before sourcing ROS or running `ros2`.

## Viewing the Nano camera

```bash
export PATH="/usr/bin:$PATH"
source /home/materov/ahmad/rov_software_2026/ros/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="file:///home/materov/ahmad/rov_software_2026/ros/config/laptop/cyclonedds.xml"
ros2 run rqt_image_view rqt_image_view
```

Select `/camera/image_compressed` from the dropdown.

## Verifying the connection

With the Nano running (`ros2 launch materov materov.launch.py`), check from the laptop:

```bash
ros2 node list   # should show /jetson_node, /signal_publisher, /zed/zed_node, etc.
ros2 topic list  # should show /zed/zed_node/rgb/image_rect_color/compressed, /joy, /commands, etc.
```

## What still needs work (not blocking the minimal run)

| Item | Location | Status |
|---|---|---|
| `reconstruction_service` returns fake data | `ros/src/laptop/laptop/reconstruction_service.py` | Stub — COLMAP not wired yet |
| `move_forward/backward/stop` on Nano are placeholders | `ros/src/materov/materov/jetson_node.py` | Logs only; thruster control handled by `signal_publisher_node` via `/joy` |
| `force_sensor_node` publishes constant 0 | `ros/src/materov/materov/force_sensor_node.py` | Sensor not wired |
| Capture path hardcoded to `/home/m8rov123/` | `ros/src/materov/materov/jetson_node.py:19` | Should be a ROS parameter |
