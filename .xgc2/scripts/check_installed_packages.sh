#!/usr/bin/env bash
set -euo pipefail

ROS_DISTRO="${ROS_DISTRO:-noetic}"
source "/opt/ros/${ROS_DISTRO}/setup.bash"

dpkg -s ros-noetic-xgc2-scout-description >/dev/null
test "$(rospack find scout_description)" = "/opt/ros/${ROS_DISTRO}/share/scout_description"
test -f "/opt/ros/${ROS_DISTRO}/share/scout_description/meshes/scout_mini_base_link.dae"
test -f "/opt/ros/${ROS_DISTRO}/share/scout_description/meshes/wheel.dae"
test -f "/opt/ros/${ROS_DISTRO}/share/scout_description/urdf/scout_mini.xacro"
roslaunch --files scout_description mini_description.launch >/tmp/xgc2-scout-description-files.txt

echo "Installed package check passed"
