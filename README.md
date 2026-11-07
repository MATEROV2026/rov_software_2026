# Matrov: ROV Software 2026

---

## Overview

Readme for the integration-2.0 branch. This branch mainly contains the finished networking work and the integration between Raneem's [Desktop Control System](https://github.com/MATEROV2026/rov_software_2026/tree/Desktop_control_system), Ahmad's ROS config, and Mingyue's [controller config and signal publisher](https://github.com/MATEROV2026/rov_software_2026/tree/mingyue).

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

- **Jetson Nano** (Ubuntu 22.04, ROS 2 Humble), underwater vehicle controller
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
  ros-humble-rmw-cyclonedds-cpp \
  ros-humble-joy-linux ros-humble-cv-bridge \
  python3-venv python3-tk python3-numpy python3-opencv python3-serial
```

**Build the workspace:**

```bash
export PATH="/usr/bin:$PATH"
export PYTHONNOUSERSITE=1
source /opt/ros/humble/setup.bash
cd ros
colcon build --packages-select interfaces laptop
cd ..
```

**Launch the laptop stack (from the repository root):**

```bash
bash scripts/launch_laptop.sh
```

The script sets the ROS environment and selects the wired DDS configuration. If
Ethernet is disconnected, it starts in localhost-only mode; restart it after
connecting the Nano.

Before starting the nodes, the launcher checks live `/control/status` and prints
an uppercase **ACTUATION INHIBITED**, **ACTUATION NOT INHIBITED**, or **ACTUATION
STATUS UNKNOWN** message, including whether the vehicle is armed. The check waits
up to eight seconds for a valid status; it does not arm or disarm the vehicle.
UNKNOWN means the state could not be confirmed, not that the motors are inhibited.

This starts:

- `vision_node`, which opens two OpenCV windows (Main Camera and ZED). Q or Escape requests disarm.
- `reconstruction_service`, the ROS service for CPU COLMAP reconstruction (install COLMAP on the laptop).
- `joy_linux_node`, which reads the gamepad and publishes to `/joy`, with 20 Hz autorepeat.

> **Python note:** if you have Conda installed, `export PATH="/usr/bin:$PATH"` is required so `python3` resolves to system 3.10. ROS Humble's C extensions will not load under 3.13. Keep ROS on the system NumPy/OpenCV packages; the launch scripts disable user-site packages.

---

### Jetson Nano setup

**First-time install (once, from the Nano repository root):**

```bash
sudo apt install python3-smbus python3-numpy python3-opencv python3-serial
export PATH="/usr/bin:$PATH" PYTHONNOUSERSITE=1
source /opt/ros/humble/setup.bash
cd ros
colcon build --packages-select interfaces materov
cd ..
bash scripts/install_autostart.sh
```

This installs a systemd service that auto-launches the full ROV stack on every boot. It also adds a udev rule so `/dev/ttyUSB*` is accessible without sudo. After this, the Nano should be plug-and-play.

**Manual launch (if not using autostart):**

```bash
sudo systemctl stop rov-launch
export PATH="/usr/bin:$PATH" PYTHONNOUSERSITE=1
source /opt/ros/humble/setup.bash
# Optional ZED overlay, if installed:
# source ~/ros2_ws/install/setup.bash
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
- `signal_publisher_node`, which converts `/joy` into 4-DOF thruster allocation and claw commands over serial.
- `imu_sensor_node`, which publishes ICM-20649 data to `/imu/data_raw`.
- `pressure_sensor_node`, which publishes MS5837 data to `/pressure/data_raw`.
- `zed_node`, the ZED 2i stereo camera node. This is optional and included only if `zed_wrapper` is installed; use `enable_zed:=false` to disable it.

### IMU orientation and calibration view

#### Arduino on macOS (no ROS)

Install pySerial, list connected ports, then launch the standalone viewer:

```bash
python3 -m pip install pyserial
python3 scripts/imu_visualizer.py --list-ports
python3 scripts/imu_visualizer.py --port /dev/cu.usbserial-A5069RR4 \
  --baud 115200 --accel-unit g --gyro-unit deg/s
```

The Arduino should print one six-value CSV row per sample in this order:
`ax,ay,az,gx,gy,gz`. The defaults match common Arduino output (`g` and
`deg/s`). The visualizer uses Tkinter, which is included with many Python
installations on macOS.

For the ICM-20948, open `arduino/imu_icm20948_streamer/imu_icm20948_streamer.ino`
in Arduino IDE and install **SparkFun ICM-20948 Arduino Library** from Library
Manager. Wire I²C SDA to Uno A4, SCL to A5, and connect ground. Check that the
IMU breakout accepts 5V Uno logic; the bare ICM-20948 chip needs level shifting.
The sketch tries I²C addresses 0x69 and 0x68 and streams at 115200 baud. Close
Arduino IDE's Serial Monitor before starting the Mac viewer.

#### ROS 2 laptop package

Build the laptop package after sourcing ROS 2:

```bash
cd ros
colcon build --packages-select laptop
source install/setup.bash
ros2 run laptop imu_visualizer
```

The viewer subscribes to `/imu/data_raw` and draws body-frame X/Y/Z axes with
roll, pitch, and relative yaw. For an Arduino serial stream, print one CSV row
per sample as `ax,ay,az,gx,gy,gz`, with no labels. Units default to acceleration
in m/s² and angular velocity in rad/s; specify other common units explicitly:

```bash
ros2 run laptop imu_visualizer -- --serial-port /dev/ttyACM0 --baud 115200 \
  --accel-unit g --gyro-unit deg/s
```

Press **C** while the sensor is motionless to estimate gyro bias for this run;
the viewer rejects samples whose gyro variation suggests movement. Press **[**
or **]** to lower or raise the complementary filter's gyro weight, **R** to
reset relative yaw, and **Q** to close. A filter weight nearer 1 follows the
gyro more strongly and is smoother short term, but lets drift last longer.
Acceleration magnitude near 9.81 m/s² is a useful stationary sanity check; it
does not prove axis alignment or accelerometer calibration. This viewer can
correct gyro zero-rate bias only, and it does not save calibration across runs.

The current ICM-20649/ICM-20948 path publishes acceleration and gyro only.
Pitch and roll use gravity plus gyro fusion. Yaw integrates gyro Z and will
drift; stable absolute heading needs a calibrated magnetometer or another
heading reference. Mounting orientation and axis signs should also be checked
by rotating one axis at a time before using these readings for vehicle control.

---

### Mission Control GUI (Laptop)

From the repository root, create the environment once:

```bash
/usr/bin/python3 -m venv mission_control/.venv
mission_control/.venv/bin/python -m pip install -r mission_control/requirements.txt
```

For joystick navigation in the GUI:

```bash
mission_control/.venv/bin/python -m pip install -r mission_control/requirements-joystick.txt
```

With the laptop ROS stack running in another terminal, launch the backend and GUI:

```bash
bash scripts/launch_mission_control.sh
```

The launcher configures ROS and starts FastAPI on port 8000, or connects to the
existing backend on that port. Arrows/Enter/Escape provide keyboard navigation.
Gamepad menu navigation is disabled while armed or vehicle state is unknown.
Leaving the thruster screen or closing the GUI requests disarm.

### Vehicle control

The vehicle starts disarmed. Arming requires a connected serial port and fresh,
neutral joystick input. Loss of joystick input for 0.5 seconds or a serial fault
disarms the vehicle; recovery requires a new arming request. Xbox View/Back,
`stop`, and `disable_thrusters` request an immediate stop. The GUI displays the
vehicle's acknowledged state and reports UNKNOWN when its heartbeat expires.

`ROV_INHIBIT_ACTUATION=1` prevents both thruster and claw arming. The Nano's
persistent setting is in `/etc/systemd/system/rov-launch.service.d/nonmotion-test.conf`:

```ini
[Service]
Environment=ROV_INHIBIT_ACTUATION=1
```

To change it, SSH into the Nano and edit the override:

```bash
ssh m8rov123@192.168.2.2
sudoedit /etc/systemd/system/rov-launch.service.d/nonmotion-test.conf
sudo systemctl daemon-reload
sudo systemctl restart rov-launch
```

Use `1` for inhibited testing and `0` to permit arming. This setting survives
reboots. Change it only with the vehicle disarmed; for powered tests, use an
approved setup with props/claw clear and someone at the physical power cutoff.
The restarted service still begins **DISARMED**. Release all controller inputs,
open **Thruster Control** in the GUI, select **Arm thrusters** with the keyboard,
and press Enter. Wait for **ARMED** before moving the sticks. Xbox View/Back or
Escape on the thruster screen requests disarm. Restore `1` and restart the service
when returning to inhibited testing. The legacy `--direct_control`
automatic-arming option is no longer supported.

### Capture and reconstruction

Task **1.2** captures six exploreHD images, five seconds apart, into a new Nano
folder under `~/shared/captures/`. The images are sent to the laptop through
`RunReconstruction`; a shared filesystem is not required. Rebuild `interfaces`
and restart both stacks when updating this service definition.

COLMAP produces a sparse `model.ply` under `~/rov-reconstructions/<job>/`, alongside
images and logs. Capture/reconstruction progress and failures appear in the GUI.
Images need overlapping views from different positions; repeated stationary
views may not reconstruct. Only one capture/reconstruction job runs at a time.

GUI uploads store images separately on the laptop; they do not feed the live
capture workflow. Uploads accept JPEG/PNG/BMP/GIF files (20 files maximum,
10 MiB per file, 50 MiB total) and use unique stored filenames. Other task catalog
entries provide operator instructions; automated `run_task` and `send_images`
actions are not implemented.

---

### Verifying the connection

With the Nano running, run this on the laptop:

```bash
ros2 node list
ros2 topic list
ros2 topic echo /camera/image_compressed --no-arr
```

You should see `/jetson_node`, `/signal_publisher`, and `/vision_node` in the node list, plus `/zed/zed_node` when ZED is enabled. You should also see `/camera/image_compressed`, `/joy`, `/commands`, and `/imu/data_raw` in the topic list.

---

### Deploying to the Nano

To deploy commits already available on the Nano's tracked upstream branch:

```bash
bash scripts/deploy_nano.sh
```

This SSHes into the Nano (`m8rov123@192.168.2.2` by default), performs a fast-forward pull, requests disarm, stops the service, rebuilds the interfaces and materov ROS packages with colcon, and restarts `rov-launch`. It refuses deployment if tracked Nano files have local modifications and does not push. Rebuild the laptop interfaces too when service definitions change.

> Prerequisites: the Nano must be reachable over Ethernet, the autostart service must already be installed (see Jetson Nano setup), and your laptop must have SSH key access to the Nano. If not, be ready to type the password. The script uses `ssh -t`, so `sudo` can still prompt.

## The CycloneDDS config

The config files at [`ros/config/laptop/cyclonedds.xml`](ros/config/laptop/cyclonedds.xml) and [`ros/config/jetson/cyclonedds.xml`](ros/config/jetson/cyclonedds.xml) explicitly bind DDS to the Ethernet interface (`enp8s0` on laptop, `enP8p1s0` on Jetson). Without this, DDS might try to use WiFi or loopback, and the two machines would not discover each other.

## What flows over the wire

| Direction | Topic | Content |
|-----------|-------|---------|
| Jetson → Laptop | `/camera/image_compressed` | JPEG frames from exploreHD (30 Hz target; actual rate depends on capture) |
| Jetson → Laptop | `/zed/zed_node/rgb/image_rect_color/compressed` | ZED frames, if connected |
| Jetson → Laptop | `/imu/data_raw` | Acceleration (m/s²) and angular velocity (rad/s) at 50 Hz |
| Jetson → Laptop | `/pressure/data_raw` | Absolute pressure in mbar at 10 Hz |
| Jetson → Laptop | `/pressure/temperature` | Temperature in °C at 10 Hz |
| Jetson → Laptop | `/status` | Capture/reconstruction status and model path |
| Jetson → Laptop | `/control/status` | Arming, serial and joystick state at 5 Hz |
| Laptop → Jetson | `/commands` | Control and capture commands; control requests can include acknowledgment IDs |
| Laptop → Jetson | `/joy` | Joystick axes/buttons on change and at 20 Hz autorepeat |

## What was changed from other branches

### Wiring and integration

- Replaced the GUI's `MockRobotInterface` with a real `RobotInterface` that calls into ROS 2 (`mission_control/shared/robot_interface.py`).
- Connected Mingyue's `signal_publisher_node` into the `materov` ROS package and registered it in `setup.py` and the launch file.
- Connected Daniel's joystick path by switching the launch file to `joy_linux_node` (system gamepad driver) instead of the pygame prototype.
- Wired Ahmad's `reconstruction_service` to `jetson_node`'s service client end-to-end.

### New code that did not exist on any branch

- **Thrust allocation matrix (TAM)** with pseudo-inverse 4-DOF allocation.
- **`camera_node`**, which was an empty stub on `main`. It now has exploreHD USB capture, auto-detection of the video device (skipping the ZED), and periodic device discovery.
- **7th thruster control**, which adds X/B button mapping for the claw motor.
- **Async ramp queue**, which uses a stochastic shuffled queue so the thrusters do not all spike current at the same time.
- **Laptop dual-camera vision**, so `vision_node` now shows both the main camera and the ZED simultaneously.

---

## TODO

### Full 6-DOF thrust allocation

The current TAM in `control.py` solves for **4 DOF**: surge (Fx), sway (Fy), heave (Fz), and yaw (Mz). To get true 6-DOF control, we also need **roll (Mx)** and **pitch (My)**. The allocation also needs precise thruster geometry relative to the ROV's center of mass.

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

The optional ZED feed is displayed when available. Reconstruction currently uses exploreHD images. Need to:

- Decide which feed goes into the COLMAP / underwater mapping pipeline, probably the ZED with depth.
- Use ZED depth data for obstacle awareness or scale-correct reconstruction.

### One-command launch

The laptop ROS stack and mission desktop have separate launch scripts (see setup
above). A combined launcher could bring up both and check that the Nano service
is running. The Nano already starts through the `rov-launch` systemd service.

### Sensors

## IMU Sensor- ICM-20948:
I2C Connect through address `0x69` . arduino/imu_live.html for further calibration. runs a quaternion filter (roll, pitch, heading, angles or rotation). Acceleration model = scale* true + bias. 6 positions, each measure up then down. where the truth is +g and -g. So bias = (up+down)/2 / scale= (up-down)/2. Node applies (measured-bias) / scale. Gyro biaso is the mean reading while stationary. Measured
X	Y	Z
accel bias (g)	−0.061	−0.056	−0.004
accel scale	1.008	1.005	1.004
gyro bias	—	—	—

where the calibartion can be found: ros/src/materov/config/imu_calibration.yaml, in SI to match sensor_msgs/Imu — so −0.598206 m/s² where the bench read −0.061 g. 
imu_sensor_node declares five parameters and applies them in publish_sample. Maths sits in sensor_math.apply_accel_calibration and apply_gyro_bias


- Use the IMU to detect actual ROV orientation and compensate for yaw/roll drift.
- Use the pressure sensor to hold depth automatically.
- Calibrate per-thruster bias using sensor feedback, such as commanded yaw versus measured yaw rate.
- Automate basic maneuvers: hold depth, hold heading, and station-keep.

### Gamepad

The current layout uses left stick for surge/sway, right stick Y for heave, LB/RB for yaw, X/B for the claw, and View/Back for stop. Refine the layout around pilot feedback:

- Which axes drive which DOF. Right now, left stick = surge/sway, right stick Y = heave, and LB/RB = yaw.
- Placement of claw, mode-switch and stop controls.
- A layout that makes intuitive sense for a pilot during a mission run.
