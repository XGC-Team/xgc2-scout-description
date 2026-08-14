#!/usr/bin/env bash
set -euo pipefail

grep -q '^id: xgc2-ros-melodic-scout-description$' .xgc2/product.yml
grep -q '^version: 0.4.10-2$' .xgc2/product.yml
grep -q '^kind: ros1-apt$' .xgc2/product.yml
grep -q '^  distro: melodic$' .xgc2/product.yml
grep -q '<name>scout_description</name>' package.xml
grep -q '<buildtool_depend>catkin</buildtool_depend>' package.xml
grep -q 'ros-melodic-urdf' .xgc2/product.yml
grep -q 'ros-melodic-xgc2-scout-description' .xgc2/product.yml
test -f LICENSE
test -f MODEL_ASSET_NOTICE.md
test -f meshes/scout_mini_base_link2.dae
test -f meshes/wheel.dae
test -f urdf/scout_visual.urdf
test -f urdf/scout_v2.xacro
test ! -d launch
test ! -d rviz
python3 -m unittest discover -s test -v

echo "Package compliance checks passed."
