cmake_minimum_required(VERSION 3.8)
project(soarm101_description)

# C++ 标准
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# 查找依赖包
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)

# 编译 C++ 可执行文件
add_executable(pick_place_demo src/pick_place_demo.cpp)
ament_target_dependencies(pick_place_demo
  rclcpp
  sensor_msgs
)

# 安装 C++ 可执行文件
install(TARGETS
  pick_place_demo
  DESTINATION lib/${PROJECT_NAME}
)

# 安装其他文件
install(
  DIRECTORY urdf launch meshes
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS
    scripts/robot_description_publisher.py
    scripts/soarm101_real_bridge.py
    scripts/joint_state_publisher.py
    scripts/set_initial_pose.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()