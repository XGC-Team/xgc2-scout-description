cmake_minimum_required(VERSION 3.0.2)
project(scout_description)

find_package(catkin REQUIRED)

catkin_package()

if(CATKIN_ENABLE_TESTING)
  find_package(PythonInterp REQUIRED)
  add_test(
    NAME scout_visual_assets
    COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/test/test_visual_assets.py
  )
endif()

install(
  DIRECTORY meshes urdf
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)

install(
  FILES LICENSE MODEL_ASSET_NOTICE.md README.md CHANGELOG.rst
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
