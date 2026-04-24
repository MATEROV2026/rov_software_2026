# Laptop Setup — Status & Launch Guide

## What is set up

### ROS 2 packages built (on `integration-test` branch)
- **`interfaces`** — CMake package defining `RunReconstruction.srv`; built via colcon
- **`laptop`** — Python package with `vision_node`, `reconstruction_service`, `laptop_controller`

### Nodes launched by `ros2 launch laptop laptop.launch.py`
| Node | Package | What it does |
|---|---|---|
| `vision_node` | `laptop` | Subscribes to `/zed/zed_node/rgb/image_rect_color/compressed`, displays camera feed in OpenCV window |
| `reconstruction_service` | `laptop` | ROS service server for `RunReconstruction`; stub for now |
| `joy_node` | `joy` | Reads joystick from `/dev/input/js0`, publishes `/joy` topic |

The `/joy` topic flows to the Nano automatically over DDS — no bridge node needed.

### Network
- **Laptop Ethernet** (`enp8s0`): `192.168.2.1/24` — static
- **Nano Ethernet**: `192.168.2.2` — reachable (ping confirmed)
- **DDS middleware**: CycloneDDS (`ros-humble-rmw-cyclonedds-cpp`), configured to use `enp8s0` only via `ros/config/laptop/cyclonedds.xml` (prevents the WiFi interface `192.168.1.201` from being advertised to the Nano)

### Python environment
The machine has both Miniconda (Python 3.13) and system Python 3.10. ROS Humble requires 3.10. The setup script and launch workflow prepend `/usr/bin` to `PATH` so `python3` resolves to 3.10 before Conda's version.

---

## System requirements installed

```bash
sudo apt install -y ros-humble-desktop python3-colcon-common-extensions ros-humble-rmw-cyclonedds-cpp
```

---

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

Run `scripts/setup_laptop.sh` first on a fresh machine — it checks all dependencies, offers to install missing ones, and prints the above launch block at the end.

---

## Nano side prerequisites (not set up here)

For the full minimal run (camera feed + joystick control) the Nano must be running with:

```bash
export PATH="/usr/bin:$PATH"   # or equivalent if Conda is present
source <ws>/install/setup.bash
export ROS_LOCALHOST_ONLY=0
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="file://<repo>/ros/config/jetson/cyclonedds.xml"
ros2 launch materov materov.launch.py
```

The Nano config (`ros/config/jetson/cyclonedds.xml`) is already in the repo and pins DDS to the Nano's Ethernet interface `enP8p1s0`.

---

## What still needs work (not blocking the minimal run)

| Item | Location | Status |
|---|---|---|
| `reconstruction_service` returns fake data | `ros/src/laptop/laptop/reconstruction_service.py` | Stub — COLMAP not wired yet |
| `move_forward/backward/stop` on Nano are placeholders | `ros/src/materov/materov/jetson_node.py` | Logs only; `signal_publisher_node` handles actual thruster control via `/joy` |
| `camera_node` is empty | `ros/src/materov/materov/camera_node.py` | No implementation |
| `force_sensor_node` publishes constant 0 | `ros/src/materov/materov/force_sensor_node.py` | Sensor not wired |
| Capture path hardcoded to `/home/m8rov123/` | `ros/src/materov/materov/jetson_node.py:19` | Should be a ROS parameter |
