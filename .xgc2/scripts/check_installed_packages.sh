#!/usr/bin/env bash
set -euo pipefail

ROS_DISTRO="${ROS_DISTRO:-noetic}"
source "/opt/ros/${ROS_DISTRO}/setup.bash"

dpkg -s ros-noetic-xgc2-scout-description >/dev/null
test "$(rospack find scout_description)" = "/opt/ros/${ROS_DISTRO}/share/scout_description"
test -f "/opt/ros/${ROS_DISTRO}/share/scout_description/meshes/scout_mini_base_link2.dae"
test -f "/opt/ros/${ROS_DISTRO}/share/scout_description/meshes/wheel.dae"
test -f "/opt/ros/${ROS_DISTRO}/share/scout_description/urdf/scout_visual.urdf"
test ! -d "/opt/ros/${ROS_DISTRO}/share/scout_description/launch"
test ! -d "/opt/ros/${ROS_DISTRO}/share/scout_description/rviz"
test "$(find "/opt/ros/${ROS_DISTRO}/share/scout_description/urdf" -maxdepth 1 -type f | wc -l)" -eq 1

echo "Installed package check passed"
