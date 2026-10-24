#!/usr/bin/env bash
# backup_nano.sh — pull everything off the Jetson that a reflash would destroy.
# Built by Raneem Mousa
#
# Usage:
#   bash scripts/backup_nano.sh                          # defaults to m8rov123@192.168.2.2
#   bash scripts/backup_nano.sh user@host /path/to/dest
#   bash scripts/backup_nano.sh --with-secrets           # also copy NetworkManager profiles
#
# Run this on the laptop while the Nano is reachable over Ethernet.
# Read-only on the Nano: it copies out, it never writes or deletes anything there.

set -uo pipefail

WITH_SECRETS=0
ARGS=()
for arg in "$@"; do
  case "$arg" in
    --with-secrets) WITH_SECRETS=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) ARGS+=("$arg") ;;
  esac
done

NANO="${ARGS[0]:-m8rov123@192.168.2.2}"
DEST="${ARGS[1]:-$HOME/nano_backup_$(date +%Y%m%d_%H%M%S)}"

mkdir -p "$DEST/system" "$DEST/git" "$DEST/files"
CTL="$DEST/.sshctl"
SSH=(ssh -o ControlMaster=auto -o ControlPath="$CTL" -o ControlPersist=600)

section() { echo; echo "== $* =="; }
note()    { echo "   $*"; }

cleanup() { ssh -O exit -o ControlPath="$CTL" "$NANO" 2>/dev/null; rm -f "$CTL"; }
trap cleanup EXIT

section "Connecting to $NANO"
note "You may be asked for the Nano password once; the connection is reused after that."
if ! "${SSH[@]}" "$NANO" true; then
  echo "[FAIL] Cannot reach $NANO. Check the Ethernet link and try: ping ${NANO#*@}"
  exit 1
fi
REMOTE_HOME="$("${SSH[@]}" "$NANO" 'echo $HOME')"
REPO="$REMOTE_HOME/materov_workspace/rov_software_2026"
note "Remote home: $REMOTE_HOME"
note "Backup dir:  $DEST"

# Record a remote command and its output.
cap() {
  local name="$1" cmd="$2"
  printf '$ %s\n\n' "$cmd" > "$DEST/system/$name.txt"
  "${SSH[@]}" "$NANO" "$cmd" >> "$DEST/system/$name.txt" 2>&1
  note "system/$name.txt"
}

# Copy a remote directory into $DEST/files, preserving its path. tar so we do
# not depend on rsync being installed on the Nano.
pull() {
  local path="$1"; shift
  # Quote each pattern for the remote shell so it is not glob-expanded there.
  local excludes=""
  for e in "$@"; do excludes+=" --exclude='$e'"; done
  if ! "${SSH[@]}" "$NANO" "[ -e '$path' ]"; then
    note "skipped (not present): $path"
    return
  fi
  local size
  size="$("${SSH[@]}" "$NANO" "du -sh '$path' 2>/dev/null | cut -f1")"
  note "pulling $path ($size)"
  "${SSH[@]}" "$NANO" "tar czf - -C /$excludes '${path#/}' 2>/dev/null" \
    | tar xzf - -C "$DEST/files" 2>/dev/null
}

section "Board and OS identity"
cap board       'cat /proc/device-tree/model 2>/dev/null; echo; cat /etc/nv_tegra_release 2>/dev/null'
cap jetpack     'apt-cache policy nvidia-jetpack 2>/dev/null; dpkg -l | grep -i nvidia-l4t-core'
cap os          'lsb_release -a 2>/dev/null; echo; uname -a; echo; cat /etc/os-release'
cap disk        'df -h; echo; lsblk'

section "Network"
cap ip_addr     'ip -o addr; echo; ip route'
cap nmcli       'nmcli -t connection show; echo; nmcli device status'
cap nm_ipv4     'for c in $(nmcli -t -f NAME connection show); do echo "--- $c"; nmcli -f ipv4,connection connection show "$c"; done'

section "ROV service and devices"
cap service     'systemctl status rov-launch --no-pager -l; echo; systemctl is-enabled rov-launch'
cap journal     'journalctl -u rov-launch -n 300 --no-pager'
cap devices     'ls -l /dev/ttyUSB* /dev/ttyACM* /dev/i2c-* 2>&1; echo; lsusb'
cap i2c         'i2cdetect -y -r 7 2>&1'
cap groups      'id; echo; groups'

section "Installed software"
cap apt_manual  'apt-mark showmanual'
cap dpkg_all    'dpkg -l'
cap pip         'pip3 freeze 2>/dev/null'
cap ros_pkgs    'source /opt/ros/humble/setup.bash 2>/dev/null; source ~/ros2_ws/install/setup.bash 2>/dev/null; ros2 pkg list'
cap zed         'ls -la /usr/local/zed 2>&1; echo; cat /usr/local/zed/zed-config-version.cmake 2>/dev/null'

section "Git state of the ROV repo"
if "${SSH[@]}" "$NANO" "[ -d '$REPO/.git' ]"; then
  g() {
    local name="$1" cmd="$2"
    printf '$ %s\n\n' "$cmd" > "$DEST/git/$name.txt"
    "${SSH[@]}" "$NANO" "cd '$REPO' && $cmd" >> "$DEST/git/$name.txt" 2>&1
    note "git/$name.txt"
  }
  g status    'git status -uall'
  g diff      'git diff'
  g staged    'git diff --cached'
  g untracked 'git ls-files --others --exclude-standard'
  g branches  'git branch -vv; echo; git remote -v'
  g log       'git log --oneline -30'
  g stashes   'git stash list; for s in $(git stash list --format=%gd); do echo "=== $s"; git stash show -p "$s"; done'
else
  note "no git repo at $REPO"
fi

section "File trees"
pull "$REPO" '*/ros/build' '*/ros/install' '*/ros/log' '*/__pycache__' '*.pyc'
pull "$REMOTE_HOME/ros2_ws/src"
pull "$REMOTE_HOME/.bashrc"
pull "$REMOTE_HOME/.profile"
pull "$REMOTE_HOME/.ssh/authorized_keys"
pull "$REMOTE_HOME/.ssh/config"
pull /etc/systemd/system/rov-launch.service
pull /etc/udev/rules.d/99-rov-serial.rules
pull /etc/hosts
pull /etc/hostname
pull /etc/fstab

if [ "$WITH_SECRETS" -eq 1 ]; then
  section "NetworkManager profiles (contains WiFi passwords)"
  note "This needs sudo on the Nano and copies plaintext credentials to your laptop."
  "${SSH[@]}" -t "$NANO" "sudo tar czf - -C / etc/NetworkManager/system-connections 2>/dev/null" \
    | tar xzf - -C "$DEST/files" 2>/dev/null
  chmod -R go-rwx "$DEST/files/etc/NetworkManager" 2>/dev/null
  note "saved to files/etc/NetworkManager/system-connections (permissions locked down)"
else
  note "NetworkManager profiles skipped. Re-run with --with-secrets to include them."
fi

section "Manifest"
{
  echo "Nano backup"
  echo "  host:    $NANO"
  echo "  taken:   $(date)"
  echo "  by:      $(whoami)@$(hostname)"
  echo "  secrets: $([ "$WITH_SECRETS" -eq 1 ] && echo included || echo excluded)"
  echo
  echo "Contents:"
  echo "  system/  command output: board, OS, network, packages, service, devices"
  echo "  git/     uncommitted work in $REPO"
  echo "  files/   copied file trees, laid out by their path on the Nano"
  echo
  echo "Sizes:"
  du -sh "$DEST"/system "$DEST"/git "$DEST"/files 2>/dev/null
} > "$DEST/MANIFEST.txt"
cat "$DEST/MANIFEST.txt"

section "Done"
echo "Backup written to: $DEST"
echo
echo "Check these before wiping anything:"
echo "  cat $DEST/git/status.txt        # uncommitted work that is not in GitHub"
echo "  cat $DEST/git/untracked.txt     # files git never tracked"
echo "  cat $DEST/system/board.txt      # which Jetson this actually is"
