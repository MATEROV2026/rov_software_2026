# Multi-Machine ROS 2 Network Setup

To run materov on Jetson and laptop on your workstation, you need to configure ROS 2 DDS discovery. 

## Network Requirements

- **Jetson** and **Laptop** must be on the same network (same WiFi or LAN)
- Both machines need to have ROS 2 installed
- Firewall ports must allow DDS communication (UDP ports typically 7400-7410)

## Setup Instructions

### Option 1: Using environment variables (Simpler)

On both machines, set these environment variables before launching ROS nodes:

```bash
export ROS_LOCALHOST_ONLY=0
export ROS_DOMAIN_ID=0
```

Then launch normally:

**On Jetson:**
```bash
cd ~/your_workspace
source install/setup.bash
export ROS_LOCALHOST_ONLY=0
export ROS_DOMAIN_ID=0
ros2 launch materov materov.launch.py
```

**On Laptop:**
```bash
cd ~/your_workspace
source install/setup.bash
export ROS_LOCALHOST_ONLY=0
export ROS_DOMAIN_ID=0
ros2 launch laptop laptop.launch.py
```

### Option 2: Using CycloneDDS configuration (More control)

Create a file `cyclonedds_config.xml` in your workspace:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CycloneDDS xmlns="https://cdds.io/config" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://cdds.io/config https://raw.githubusercontent.com/eclipse-cyclonedds/cyclonedds/master/etc/cyclonedds.xsd">
  <Domain>
    <General>
      <NetworkInterfaceAddress>all</NetworkInterfaceAddress>
	  <MulticastDefaultAddress>239.255.0.1</MulticastDefaultAddress>
    </General>
    <Partitioning>
      <NetworkInterface name="all" priority="default" multicast="true"/>
    </Partitioning>
  </Domain>
</CycloneDDS>
```

Then set environment variable:

```bash
export CYCLONEDDS_URI=file:///path/to/cyclonedds_config.xml
export ROS_DOMAIN_ID=0
```

## Debugging Multi-Machine Communication

Test if nodes can discover each other:

```bash
# List all nodes on the network
ros2 node list

# Monitor topics across the network
ros2 topic list

# Check camera feed is reaching laptop
ros2 topic echo /camera/image_compressed
```

## Keyboard Controls (on Laptop)

When running the vision_node:
- **W** - Forward
- **S** - Backward  
- **Q** - Stop

## Common Issues

1. **Nodes don't discover each other**
   - Check firewall settings (UDP ports 7400-7410)
   - Verify both machines are on same network
   - Try setting `ROS_LOCALHOST_ONLY=0`

2. **Image lag or dropout**
   - Check network bandwidth and latency
   - Verify ZED camera is properly connected to Jetson
   - Check CPU usage on both machines

3. **Commands not reaching Jetson**
   - Verify command topic `/commands` exists with `ros2 topic list`
   - Check Jetson nodes are properly subscribed
