#!/usr/bin/env bash
# Usage: bash scripts/launch_laptop.sh
# One-command launch of the laptop ROS stack with the correct environment.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export PATH="/usr/bin:$PATH"

if [ ! -f "$REPO_ROOT/ros/install/setup.bash" ]; then
  echo "Workspace not built. Run: bash scripts/setup_laptop.sh" >&2
  exit 1
fi

# shellcheck disable=SC1091
source "$REPO_ROOT/ros/install/setup.bash"

export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# Only pin to enp8s0 when the Nano ethernet interface is actually up.
# Without this check CycloneDDS refuses to start if the cable isn't plugged in.
if ip link show enp8s0 2>/dev/null | grep -q "state UP"; then
  export ROS_LOCALHOST_ONLY=0
  export CYCLONEDDS_URI="file://$REPO_ROOT/ros/config/laptop/cyclonedds.xml"
  echo "[launch] enp8s0 up — using CycloneDDS with Nano config"
else
  export ROS_LOCALHOST_ONLY=1
  unset CYCLONEDDS_URI
  echo "[launch] enp8s0 not up — running localhost-only (no Nano)"
fi

exec ros2 launch laptop laptop.launch.py