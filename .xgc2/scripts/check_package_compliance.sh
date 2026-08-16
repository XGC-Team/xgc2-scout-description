#!/usr/bin/env bash
set -euo pipefail

grep -q '^id: xgc2-ros-melodic-scout-description$' .xgc2/product.yml
grep -q '^version: 0.4.10-3$' .xgc2/product.yml
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
test ! -d launch
test ! -d rviz
python3 -m unittest discover -s test -v

grep -q 'xgc2-build-bionic-ros-melodic:1.0.0' \
  .xgc2/scripts/build_debs_in_docker.sh
if rg -n 'ros:melodic|apt-get[[:space:]]+(update|install)' \
  .xgc2/scripts/build_debs_in_docker.sh; then
  echo "stock ROS image or container dependency bootstrap remains" >&2
  exit 1
fi
for legacy_input in run_cpp_quality run_source_tests; do
  if rg -n "inputs\.${legacy_input}|^[[:space:]]+${legacy_input}:" \
    .github/workflows/release.yml; then
    echo "legacy release input remains: ${legacy_input}" >&2
    exit 1
  fi
done

echo "Package compliance checks passed."
