# scout_description

Visual-only AgileX Scout model shared by ROS visualizers and simulation packages.

The ROS package name is permanently `scout_description`. Its public runtime
contract is limited to:

- `meshes/`
- `urdf/scout_visual.urdf`

Gazebo plugins, transmissions, inertial/collision geometry, launch files, sensor
configuration, and RViz scenario layouts belong to their consuming packages.
The XGC2 Gazebo Classic consumer owns those files in `gazebo_sim_scout` while
continuing to resolve visual meshes through
`package://scout_description/meshes/...`.

`urdf/scout_visual.urdf` uses the reduced, embedded-material meshes in
`meshes/lod10k/`. `urdf/scout_visual_detail.urdf` retains the close-range visual;
upstream CAD remains under `meshes/`. Resource variants are listed in
`modeling/visual_variants.json`.
