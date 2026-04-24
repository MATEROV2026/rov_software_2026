#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROS_WS="$REPO_ROOT/ros"

FAILURES=0
WARNINGS=0

ok() { echo "[OK] $*"; }
warn() { echo "[WARN] $*"; WARNINGS=$((WARNINGS + 1)); }
fail() { echo "[FAIL] $*"; FAILURES=$((FAILURES + 1)); }
section() { echo; echo "== $* =="; }

run_required() {
  echo "+ $*"
  "$@"
  local code=$?
  if [ "$code" -ne 0 ]; then
    fail "Command failed: $*"
  fi
  return "$code"
}

run_optional() {
  echo "+ $*"
  "$@"
  local code=$?
  if [ "$code" -ne 0 ]; then
    warn "Command failed: $*"
  fi
  return 0
}

ask_yes_no() {
  local prompt="$1"
  local answer
  read -r -p "$prompt [y/N] " answer
  case "$answer" in
    y|Y|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

install_apt_packages() {
  local packages=("$@")
  if ! command -v apt-get >/dev/null 2>&1; then
    warn "apt-get not found; skipping package install"
    return 0
  fi

  if [ "$(id -u)" -eq 0 ]; then
    run_optional apt-get update
    run_optional apt-get install -y "${packages[@]}"
  elif command -v sudo >/dev/null 2>&1; then
    run_optional sudo apt-get update
    run_optional sudo apt-get install -y "${packages[@]}"
  else
    warn "sudo not found; install these manually: ${packages[*]}"
  fi
}

check_apt_packages() {
  local missing=()

  if ! command -v dpkg >/dev/null 2>&1; then
    warn "dpkg not found; cannot check apt packages"
    return 0
  fi

  for package in "$@"; do
    if dpkg -s "$package" >/dev/null 2>&1; then
      ok "$package installed"
    else
      warn "$package missing"
      missing+=("$package")
    fi
  done

  if [ "${#missing[@]}" -eq 0 ]; then
    return 0
  fi

  echo
  echo "Missing apt packages:"
  printf '  %s\n' "${missing[@]}"
  echo "Installing these may change system packages on this Nano."
  if ask_yes_no "Install missing apt packages now?"; then
    install_apt_packages "${missing[@]}"
  else
    warn "Skipped apt install. Install manually if later checks fail."
  fi
}

section "Nano Setup"
ok "Repo root: $REPO_ROOT"

if [ ! -f /opt/ros/humble/setup.bash ]; then
  fail "ROS 2 Humble is not installed at /opt/ros/humble"
else
  # shellcheck disable=SC1091
  source /opt/ros/humble/setup.bash
  ok "Sourced ROS 2 Humble"
fi

export ROS_LOCALHOST_ONLY="${ROS_LOCALHOST_ONLY:-0}"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"
ok "ROS_LOCALHOST_ONLY=$ROS_LOCALHOST_ONLY"
ok "ROS_DOMAIN_ID=$ROS_DOMAIN_ID"

section "Package Checks"
check_apt_packages \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-opencv \
  python3-numpy \
  python3-serial \
  python3-smbus \
  i2c-tools \
  ros-humble-cv-bridge

section "Tool Checks"
command -v ros2 >/dev/null 2>&1 && ok "ros2 found" || fail "ros2 not found"
command -v colcon >/dev/null 2>&1 && ok "colcon found" || fail "colcon not found"
command -v rosdep >/dev/null 2>&1 && ok "rosdep found" || warn "rosdep not found"

section "ZED Checks"
if [ -d /usr/local/zed ]; then
  ok "ZED SDK directory found at /usr/local/zed"
else
  warn "ZED SDK directory /usr/local/zed not found. If ZED is installed elsewhere, this may be okay."
fi

if command -v ZED_Diagnostic >/dev/null 2>&1; then
  ok "ZED_Diagnostic found"
elif [ -x /usr/local/zed/tools/ZED_Diagnostic ]; then
  ok "ZED_Diagnostic found at /usr/local/zed/tools/ZED_Diagnostic"
else
  warn "ZED_Diagnostic not found on PATH"
fi

section "Device Checks"
if ls /dev/ttyUSB* /dev/ttyACM* >/dev/null 2>&1; then
  ok "Serial device(s): $(ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | tr '\n' ' ')"
else
  warn "No /dev/ttyUSB* or /dev/ttyACM* device found for MCU"
fi

if [ -e /dev/i2c-7 ]; then
  ok "/dev/i2c-7 found"
else
  warn "/dev/i2c-7 not found. IMU and pressure nodes use smbus.SMBus(7)."
fi

if groups | tr ' ' '\n' | grep -qx dialout; then
  ok "Current user is in dialout group"
else
  warn "Current user is not in dialout group; serial open may fail without sudo"
fi

section "rosdep"
if command -v rosdep >/dev/null 2>&1; then
  echo "rosdep can install additional system packages."
  if ask_yes_no "Run rosdep update/install now?"; then
    run_optional rosdep update
    run_optional rosdep install --from-paths "$ROS_WS/src" --ignore-src -r -y
  else
    warn "Skipped rosdep install"
  fi
fi

section "Build Nano Packages"
echo "Building writes to $ROS_WS/build, $ROS_WS/install, and $ROS_WS/log."
if ask_yes_no "Run colcon build for interfaces and materov?"; then
  cd "$ROS_WS" || exit 1
  run_required colcon build --packages-select interfaces materov
else
  warn "Skipped colcon build"
fi

if [ -f "$ROS_WS/install/setup.bash" ]; then
  # shellcheck disable=SC1091
  source "$ROS_WS/install/setup.bash"
  ok "Sourced workspace install"
else
  fail "Missing $ROS_WS/install/setup.bash"
fi

section "ROS Package Checks"
ros2 pkg prefix interfaces >/dev/null 2>&1 && ok "interfaces package found" || fail "interfaces package missing"
ros2 pkg prefix materov >/dev/null 2>&1 && ok "materov package found" || fail "materov package missing"
ros2 pkg prefix zed_wrapper >/dev/null 2>&1 && ok "zed_wrapper package found" || warn "zed_wrapper package missing from ROS environment"

section "Executable Checks"
ros2 pkg executables materov | grep -q "signal_publisher_node" && ok "signal_publisher_node executable found" || fail "signal_publisher_node executable missing"
ros2 pkg executables materov | grep -q "jetson_node" && ok "jetson_node executable found" || fail "jetson_node executable missing"
ros2 pkg executables materov | grep -q "imu_sensor_node" && ok "imu_sensor_node executable found" || fail "imu_sensor_node executable missing"
ros2 pkg executables materov | grep -q "pressure_sensor_node" && ok "pressure_sensor_node executable found" || fail "pressure_sensor_node executable missing"

section "Launch Check"
run_optional ros2 launch materov materov.launch.py --show-args

section "Next Command"
echo "source \"$ROS_WS/install/setup.bash\""
echo "export ROS_LOCALHOST_ONLY=0"
echo "export ROS_DOMAIN_ID=$ROS_DOMAIN_ID"
echo "ros2 launch materov materov.launch.py"

section "Summary"
if [ "$FAILURES" -eq 0 ]; then
  ok "Nano setup completed with $WARNINGS warning(s)."
  exit 0
else
  fail "Nano setup completed with $FAILURES failure(s) and $WARNINGS warning(s)."
  exit 1
fi
