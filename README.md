# scout_description

AgileX Scout model shared by Melodic onboard TF, ROS visualizers, and simulation.

This branch targets ROS Melodic on Ubuntu Bionic and builds with `catkin`.

The ROS package name is permanently `scout_description`. Runtime files:

- `meshes/` — hashed viewer assets stay byte-identical; vehicle-only meshes
  (`base_link.dae`, `wheel_type1.dae`, `wheel_type2.dae`, …) are additive
- `urdf/scout_visual.urdf` — existing visualizers and Gazebo mesh URIs
- `urdf/scout_v2.xacro` — Xavier chassis TF used by the AgileX onboard stack

Bringup launch, RViz layouts, maps, and Gazebo physics stay out of this package.
The onboard compose launch lives in `agilex_onboard_autostart`. Gazebo Classic
owns its own xacro in `gazebo_sim_scout` and only resolves
`package://scout_description/meshes/...`.
