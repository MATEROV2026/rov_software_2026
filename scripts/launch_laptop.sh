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

export ROS_LOCALHOST_ONLY=0
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="file://$REPO_ROOT/ros/config/laptop/cyclonedds.xml"

exec ros2 launch laptop laptop.launch.py