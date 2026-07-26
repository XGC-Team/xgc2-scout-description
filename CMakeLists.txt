cmake_minimum_required(VERSION 2.8.3)
project(scout_description)

find_package(catkin REQUIRED COMPONENTS roslaunch)

catkin_package()

if(CATKIN_ENABLE_TESTING)
  roslaunch_add_file_check(launch)
  find_package(PythonInterp REQUIRED)
  add_test(
    NAME scout_visual_assets
    COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/test/test_visual_assets.py
  )
endif()

install(
  DIRECTORY launch meshes urdf
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
