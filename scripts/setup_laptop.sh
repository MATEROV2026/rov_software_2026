#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROS_WS="$REPO_ROOT/ros"
CYCLONE_CFG="$REPO_ROOT/ros/config/laptop/cyclonedds.xml"

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
  echo "Installing these may change system packages on this laptop."
  if ask_yes_no "Install missing apt packages now?"; then
    install_apt_packages "${missing[@]}"
  else
    warn "Skipped apt install. Install manually if later checks fail."
  fi
}

section "Laptop Setup"
ok "Repo root: $REPO_ROOT"

# ROS Humble requires Python 3.10. Miniconda/Conda can shadow it with a newer
# version that cannot load ROS C extensions. Prepend /usr/bin so python3 → 3.10.
export PATH="/usr/bin:$PATH"
if python3 --version 2>&1 | grep -q "3\.10"; then
  ok "python3 → $(python3 --version)"
else
  warn "python3 is $(python3 --version); expected 3.10 for ROS Humble. C extensions may fail."
fi

if [ ! -f /opt/ros/humble/setup.bash ]; then
  fail "ROS 2 Humble is not installed at /opt/ros/humble"
else
  set +u
  # shellcheck disable=SC1091
  source /opt/ros/humble/setup.bash
  set -u
  ok "Sourced ROS 2 Humble"
fi

export ROS_LOCALHOST_ONLY="${ROS_LOCALHOST_ONLY:-0}"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"
ok "ROS_LOCALHOST_ONLY=$ROS_LOCALHOST_ONLY"
ok "ROS_DOMAIN_ID=$ROS_DOMAIN_ID"

section "DDS / Network"
if dpkg -s ros-humble-rmw-cyclonedds-cpp >/dev/null 2>&1; then
  ok "ros-humble-rmw-cyclonedds-cpp installed"
  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
  ok "RMW_IMPLEMENTATION=rmw_cyclonedds_cpp"
else
  warn "ros-humble-rmw-cyclonedds-cpp not installed — using default FastDDS"
  warn "Install it: sudo apt install ros-humble-rmw-cyclonedds-cpp"
fi

if [ -f "$CYCLONE_CFG" ]; then
  export CYCLONEDDS_URI="file://$CYCLONE_CFG"
  ok "CYCLONEDDS_URI=$CYCLONEDDS_URI"
else
  warn "CycloneDDS config not found at $CYCLONE_CFG"
fi

section "Package Checks"
check_apt_packages \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-opencv \
  python3-numpy \
  ros-humble-cv-bridge \
  ros-humble-joy-linux \
  ros-humble-rmw-cyclonedds-cpp

section "Tool Checks"
command -v ros2 >/dev/null 2>&1 && ok "ros2 found" || fail "ros2 not found"
command -v colcon >/dev/null 2>&1 && ok "colcon found" || fail "colcon not found"
command -v rosdep >/dev/null 2>&1 && ok "rosdep found" || warn "rosdep not found"

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

section "Build Laptop Packages"
echo "Building writes to $ROS_WS/build, $ROS_WS/install, and $ROS_WS/log."
if ask_yes_no "Run colcon build for interfaces and laptop?"; then
  cd "$ROS_WS" || exit 1
  run_required colcon build --packages-select interfaces laptop
else
  warn "Skipped colcon build"
fi

if [ -f "$ROS_WS/install/setup.bash" ]; then
  set +u
  # shellcheck disable=SC1091
  source "$ROS_WS/install/setup.bash"
  set -u
  ok "Sourced workspace install"
else
  fail "Missing $ROS_WS/install/setup.bash"
fi

section "ROS Package Checks"
ros2 pkg prefix interfaces >/dev/null 2>&1 && ok "interfaces package found" || fail "interfaces package missing"
ros2 pkg prefix laptop >/dev/null 2>&1 && ok "laptop package found" || fail "laptop package missing"
ros2 pkg prefix joy_linux >/dev/null 2>&1 && ok "joy_linux package found" || fail "joy_linux package missing"

section "Joystick Checks"
if ls /dev/input/js* >/dev/null 2>&1; then
  ok "Joystick device(s): $(ls /dev/input/js* | tr '\n' ' ')"
else
  warn "No /dev/input/js* joystick device found. Plug in controller before launching."
fi

section "Launch Check"
run_optional ros2 launch laptop laptop.launch.py --show-args

section "Next Command"
echo "export PATH=\"/usr/bin:\$PATH\""
echo "source \"$ROS_WS/install/setup.bash\""
echo "export ROS_LOCALHOST_ONLY=0"
echo "export ROS_DOMAIN_ID=$ROS_DOMAIN_ID"
echo "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp"
echo "export CYCLONEDDS_URI=\"file://$CYCLONE_CFG\""
echo "ros2 launch laptop laptop.launch.py"

section "Summary"
if [ "$FAILURES" -eq 0 ]; then
  ok "Laptop setup completed with $WARNINGS warning(s)."
  exit 0
else
  fail "Laptop setup completed with $FAILURES failure(s) and $WARNINGS warning(s)."
  exit 1
fi
