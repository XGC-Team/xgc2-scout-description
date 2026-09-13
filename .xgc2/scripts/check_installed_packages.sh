#!/usr/bin/env bash
set -euo pipefail

ROS_DISTRO="${ROS_DISTRO:-noetic}"
source "/opt/ros/${ROS_DISTRO}/setup.bash"

dpkg -s ros-noetic-xgc2-scout-description >/dev/null
test -f "/opt/ros/${ROS_DISTRO}/share/scout_description/meshes/scout_mini_base_link2.dae"
test -f "/opt/ros/${ROS_DISTRO}/share/scout_description/meshes/wheel.dae"
test -f "/opt/ros/${ROS_DISTRO}/share/scout_description/urdf/scout_visual.urdf"
test ! -d "/opt/ros/${ROS_DISTRO}/share/scout_description/launch"
test ! -d "/opt/ros/${ROS_DISTRO}/share/scout_description/rviz"

echo "Installed package check passed"
