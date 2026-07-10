#!/usr/bin/env bash
set -euo pipefail

grep -q '^id: xgc2-scout-description$' .xgc2/product.yml
grep -q '^version: 0.4.10-8$' .xgc2/product.yml
grep -q '<name>scout_description</name>' package.xml
grep -q 'ros-noetic-lms1xx' .xgc2/product.yml
grep -q 'ros-noetic-xacro' .xgc2/product.yml
test -f meshes/scout_mini_base_link.dae
test -f meshes/wheel.dae
test -f urdf/scout_mini.xacro
test -f launch/mini_description.launch

echo "Package compliance checks passed."
