# Matrov: ROV Software 2026

---

## Overview

Readme for the integration-testing branch. This branch mainly contains the finished networking work and the integration between Raneem's [Desktop Control System](https://github.com/MATEROV2026/rov_software_2026/tree/Desktop_control_system), Ahmad's ROS config, and Mingyue's [controller config and signal publisher](https://github.com/MATEROV2026/rov_software_2026/tree/mingyue).

---

## Repo Structure

```
rov_software_2026/
├── ros/
│   ├── config/
│   │   ├── laptop/
│   │   │   └── cyclonedds.xml        # Binds DDS to Ethernet (enp8s0)
│   │   └── jetson/
│   │       └── cyclonedds.xml        # Binds DDS to Ethernet (enP8p1s0)
│   └── src/
│       ├── interfaces/               # ROS 2 service definitions
│       ├── laptop/                   # Laptop-side nodes
│       │   ├── laptop/
│       │   │   ├── vision_node
│       │   │   ├── reconstruction_service
│       │   │   └── laptop_controller
│       │   └── launch/
│       │       └── laptop.launch
│       └── materov/                  # Jetson-side nodes
│           ├── materov/
│           │   ├── jetson_node
│           │   ├── camera_node
│           │   ├── signal_publisher_node
│           │   ├── imu_sensor_node
│           │   ├── pressure_sensor_node
│           │   └── force_sensor_node
│           └── launch/
│               └── materov.launch
├── mission_control/
│   ├── backend/                      # FastAPI REST server
│   │   ├── main
│   │   ├── tasks.json
│   │   └── routes/
│   ├── gui/                          # CustomTkinter desktop UI
│   │   ├── app
│   │   ├── controller
│   │   ├── api
│   │   └── screens/
│   └── shared/
│       └── robot_interface           # ROS ↔ API bridge
├── camera/                           # ZED camera test utilities
├── scripts/                          # Deploy & setup scripts
└── Dockerfile
```

---

## Setup

### Hardware

- **Jetson Nano** (Ubuntu 20.04, ROS 2 Humble), underwater vehicle controller
- **Laptop** (Ubuntu 22.04, ROS 2 Humble), mission control and vision
- Direct Ethernet cable between them (no WiFi, no router)
- ZED 2i stereo camera and exploreHD USB camera on the Nano
- Gamepad on the laptop
- ICM-20649 IMU and MS5837 pressure sensor on I2C-7
- STM32446RE6 MCU on `/dev/ttyUSB0` for thruster PWM

### Network

| Machine | Interface | Static IP |
|---|---|---|
| Laptop | `enp8s0` | `192.168.2.1/24` |
| Jetson | `enP8p1s0` | `192.168.2.2/24` |

ROS 2 uses CycloneDDS bound only to the Ethernet interface. See `ros/config/laptop/cyclonedds.xml` and `ros/config/jetson/cyclonedds.xml`. WiFi is intentionally never used for ROS traffic to avoid latency spikes.

---

### Laptop setup

**Install dependencies (once):**

```bash
sudo apt install -y \
  ros-humble-desktop \
  python3-colcon-common-extensions \
  ros-humble-rmw-cyclonedds-cpp
```

**Build the workspace:**

```bash
export PATH="/usr/bin:$PATH"
source /opt/ros/humble/setup.bash
cd ros
colcon build --packages-select interfaces laptop
```

**Launch the laptop stack:**

```bash
export PATH="/usr/bin:$PATH"
source ros/install/setup.bash
export ROS_LOCALHOST_ONLY=0
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="file://$PWD/ros/config/laptop/cyclonedds.xml"
ros2 launch laptop laptop.launch.py
```

This starts:

- `vision_node`, which opens two OpenCV windows (Main Camera and ZED). W/S/Q keys publish to `/commands`.
- `reconstruction_service`, the ROS service for 3D reconstruction.
- `joy_linux_node`, which reads the gamepad and publishes to `/joy`.

> **Python note:** if you have Conda installed, `export PATH="/usr/bin:$PATH"` is required so `python3` resolves to system 3.10. ROS Humble's C extensions will not load under 3.13.

---

### Jetson Nano setup

**First-time install (once):**

```bash
bash scripts/install_autostart.sh
```

This installs a systemd service that auto-launches the full ROV stack on every boot. It also adds a udev rule so `/dev/ttyUSB*` is accessible without sudo. After this, the Nano should be plug-and-play.

**Manual launch (if not using autostart):**

```bash
sudo systemctl stop rov-launch
source ~/ros2_ws/install/setup.bash
source ~/materov_workspace/rov_software_2026/ros/install/setup.bash
export ROS_LOCALHOST_ONLY=0
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="file://$HOME/materov_workspace/rov_software_2026/ros/config/jetson/cyclonedds.xml"
ros2 launch materov materov.launch.py
```

**Monitoring the autostart service:**

```bash
sudo systemctl status rov-launch
journalctl -u rov-launch -f
sudo systemctl restart rov-launch
```

This starts:

- `jetson_node`, the mission orchestrator for commands and reconstruction capture.
- `camera_node`, which publishes the exploreHD USB camera to `/camera/image_compressed`.
- `signal_publisher_node`, which converts `/joy` into 6-DOF thruster PWM over serial.
- `imu_sensor_node`, which publishes ICM-20649 data to `/imu/data_raw`.
- `pressure_sensor_node`, which publishes MS5837 data to `/pressure/data_raw`.
- `zed_node`, the ZED 2i stereo camera node. This is optional and included only if `zed_wrapper` is installed.

---

### Mission Control GUI (Laptop)

```bash
cd mission_control
pip install -r requirements.txt
python run_backend.py
python gui/app.py
```

Run the backend in one terminal (FastAPI on port 8000) and the GUI in another.

For Linux/Windows joystick support in the GUI:

```bash
pip install -r requirements-joystick.txt
```

---

### Verifying the connection

With the Nano running, run this on the laptop:

```bash
ros2 node list
ros2 topic list
ros2 topic echo /camera/image_compressed --no-arr
```

You should see `/jetson_node`, `/signal_publisher`, `/vision_node`, and `/zed/zed_node` in the node list. You should also see `/camera/image_compressed`, `/joy`, `/commands`, and `/imu/data_raw` in the topic list.

---

### Deploying to the Nano

After pushing changes to GitHub, sync them to the Nano in one shot:

```bash
bash scripts/deploy_nano.sh
```

This SSHes into the Nano (`m8rov123@192.168.2.2` by default), pulls the latest commits, rebuilds the interfaces and materov ROS packages with colcon, and restarts the `rov-launch` systemd service so the new code is live immediately. No manual SSH or service juggling should be needed.

> Prerequisites: the Nano must be reachable over Ethernet, the autostart service must already be installed (see Jetson Nano setup), and your laptop must have SSH key access to the Nano. If not, be ready to type the password. The script uses `ssh -t`, so `sudo` can still prompt.

## The CycloneDDS config

The config files at [`ros/config/laptop/cyclonedds.xml`](ros/config/laptop/cyclonedds.xml) and [`ros/config/jetson/cyclonedds.xml`](ros/config/jetson/cyclonedds.xml) explicitly bind DDS to the Ethernet interface (`enp8s0` on laptop, `enP8p1s0` on Jetson). Without this, DDS might try to use WiFi or loopback, and the two machines would not discover each other.

## What flows over the wire

| Direction | Topic | Content |
|-----------|-------|---------|
| Jetson → Laptop | `/camera/image_compressed` | JPEG frames from exploreHD at ~30 Hz |
| Jetson → Laptop | `/zed/zed_node/rgb/image_rect_color/compressed` | ZED frames, if connected |
| Jetson → Laptop | `/imu/data_raw` | Accel and gyro at 50 Hz |
| Jetson → Laptop | `/pressure/data_raw` | Depth pressure at 10 Hz |
| Jetson → Laptop | `/status` | Reconstruction status strings |
| Laptop → Jetson | `/commands` | String commands, such as forward, run_reconstruction, etc. |
| Laptop → Jetson | `/joy` | Joystick axes/buttons at 100 Hz |

## What was changed from other branches

### Wiring and integration

- Replaced the GUI's `MockRobotInterface` with a real `RobotInterface` that calls into ROS 2 (`mission_control/shared/robot_interface.py`).
- Connected Mingyue's `signal_publisher_node` into the `materov` ROS package and registered it in `setup.py` and the launch file.
- Connected Daniel's joystick path by switching the launch file to `joy_linux_node` (system gamepad driver) instead of the pygame prototype.
- Wired Ahmad's `reconstruction_service` to `jetson_node`'s service client end-to-end.

### New code that did not exist on any branch

- **Thrust allocation matrix (TAM)** with pseudo-inverse 6-DOF allocation.
- **`camera_node`**, which was an empty stub on `main`. It now has exploreHD USB capture, auto-detection of the video device (skipping the ZED), and a 30-second retry loop.
- **7th thruster control**, which adds X/B button mapping for the claw motor.
- **Async ramp queue**, which uses a stochastic shuffled queue so the thrusters do not all spike current at the same time.
- **Laptop dual-camera vision**, so `vision_node` now shows both the main camera and the ZED simultaneously.

---

## TODO

### Full 6-DOF thrust allocation

The current TAM in `signal_publisher_node.py` solves for **4 DOF**: surge (Fx), sway (Fy), heave (Fz), and yaw (Mz). To get true 6-DOF control, we also need **roll (Mx)** and **pitch (My)**. The allocation also needs precise thruster geometry relative to the ROV's center of mass.

**What we have** (estimated and uncalibrated):

| Thruster | Position (x, y, z) [m] | Orientation |
|---|---|---|
| Front-right horizontal | (+0.225, −0.185, 0.00) | 45° |
| Front-left horizontal | (+0.225, +0.185, 0.00) | 315° |
| Front-right vertical | (0.000, −0.185, 0.00) | up |
| Front-left vertical | (0.000, +0.185, 0.00) | up |
| Rear-right horizontal | (−0.225, −0.185, 0.00) | 135° |
| Rear-left horizontal | (−0.225, +0.185, 0.00) | 225° |

**What we need to measure:**

- The true position of each thruster relative to the **center of mass**, not the geometric center of the frame. Right now, all `z = 0` and the CoM is assumed to be at the origin.
- Thruster z-positions, meaning vertical offsets from the CoM plane. These are needed for roll/pitch moments.
- Verify the horizontal thruster angles against the actual mounted orientation.
- Once all six dimensions of the wrench are populated, expand `tau` from `[Fx, Fy, Fz, Mz]` to `[Fx, Fy, Fz, Mx, My, Mz]` and rebuild the TAM columns to include the missing moment terms.

### ZED

The ZED 2i is connected and streaming, but we are not actually using it for anything yet. Reconstruction was switched to the exploreHD because the ZED path was unreliable. Need to:

- Decide which feed goes into the COLMAP / underwater mapping pipeline, probably the ZED with depth.
- Wire `reconstruction_service` to actually run COLMAP. It currently returns fake success.
- Use ZED depth data for obstacle awareness or scale-correct reconstruction.

### GUI testing

The GUI was integrated, but it has not been seriously stress-tested yet. Needs:

- Full walkthrough of every screen and every task in `tasks.json`.
- Verify the image upload flow end-to-end (multipart → backend → disk).
- Verify that every command button actually reaches the Jetson.
- Test the joystick navigation path.
- Do a bug-fix pass on whatever falls out.

### One-command launch

Right now, the laptop and Jetson each need their own launch sequence, including environment exports and sourcing. Goal:

- Single launch file or shell script that brings up everything on the laptop side.
- The Nano is already plug-and-play through the `rov-launch` systemd service. Keep it that way.
- Ideally, one command on the laptop should also kick the Nano if it is not already up.

### Sensors

The IMU and pressure sensor publish raw data, but nothing closes the loop yet. Need to:

- Use the IMU to detect actual ROV orientation and compensate for yaw/roll drift.
- Use the pressure sensor to hold depth automatically.
- Calibrate per-thruster bias using sensor feedback, such as commanded yaw versus measured yaw rate.
- Automate basic maneuvers: hold depth, hold heading, and station-keep.

### Gamepad

The current button/axis mapping in `joy_callback` is a placeholder layout from early prototyping. It needs to be redesigned around:

- Which axes drive which DOF. Right now, left stick = surge/sway, right stick Y = heave, and LB/RB = yaw.
- Which buttons trigger the claw, mode switches, and emergency stop.
- A layout that makes intuitive sense for a pilot during a mission run.
