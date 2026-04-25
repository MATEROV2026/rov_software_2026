#!/bin/bash
set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Installing udev rule (no-sudo serial access)..."
sudo cp "$REPO_ROOT/ros/config/jetson/99-rov-serial.rules" /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
echo "    Done — /dev/ttyUSB* will be world-writable on next plug-in."

echo "==> Installing systemd service (auto-launch on boot)..."
sudo cp "$REPO_ROOT/ros/config/jetson/rov-launch.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rov-launch.service
echo "    Done — ROV stack will start automatically on boot."

echo ""
echo "Useful commands:"
echo "  sudo systemctl start rov-launch      # start now"
echo "  sudo systemctl stop rov-launch       # stop"
echo "  sudo systemctl status rov-launch     # check status"
echo "  journalctl -u rov-launch -f          # live logs"
