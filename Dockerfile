# Start from the official ROS 2 Humble Long-Term Support (LTS) image
FROM osrf/ros:humble-desktop-full

# Set the shell to bash for all subsequent commands
SHELL ["/bin/bash", "-c"]

# Avoid interactive prompts during package installation
ARG DEBIAN_FRONTEND=noninteractive

# Update package lists and install essential system dependencies in a single layer
RUN apt-get update && apt-get install -y \
    python3-pip \
    git \
    nano \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-opencv \
    ros-humble-v4l2-camera \
    ros-humble-joy-linux \
    python3-pygame \
    python3-serial \
    && rm -rf /var/lib/apt/lists/*

# Set up the ROS 2 workspace directory inside the container
WORKDIR /root/ros2_ws

# Add ROS setup to the bash profile to automatically source it in new terminals
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
RUN echo "if [ -f /root/ros2_ws/install/setup.bash ]; then source /root/ros2_ws/install/setup.bash; fi" >> ~/.bashrc