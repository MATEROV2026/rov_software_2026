#!/usr/bin/env bash
# Usage: bash scripts/deploy_nano.sh [nano_host]
# Pulls latest code on the Nano, rebuilds materov, and restarts the service.

NANO="${1:-m8rov123@192.168.2.2}"
REPO="/home/m8rov123/materov_workspace/rov_software_2026"

echo "Deploying to $NANO ..."

ssh -t "$NANO" "
set -e
cd $REPO
git pull
export PATH=/usr/bin:\$PATH
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
cd ros
colcon build --packages-select interfaces materov
sudo systemctl restart rov-launch
echo 'Done — service restarted'
"
