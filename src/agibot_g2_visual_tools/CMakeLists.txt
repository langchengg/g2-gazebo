cmake_minimum_required(VERSION 3.16)
project(agibot_g2_visual_tools LANGUAGES CXX)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rviz_common REQUIRED)
find_package(rviz_ogre_vendor REQUIRED)
find_package(Qt5 REQUIRED COMPONENTS Widgets)

add_executable(rviz2_close_order src/rviz2_close_order.cpp)
target_compile_features(rviz2_close_order PRIVATE cxx_std_17)
target_compile_options(rviz2_close_order PRIVATE -Wall -Wextra -Wpedantic)
target_link_libraries(rviz2_close_order
  rclcpp::rclcpp
  rviz_common::rviz_common
  rviz_ogre_vendor::OgreMain
  rviz_ogre_vendor::OgreOverlay
  Qt5::Widgets)

install(TARGETS rviz2_close_order RUNTIME DESTINATION lib/${PROJECT_NAME})
install(FILES README.md LICENSE DESTINATION share/${PROJECT_NAME})
ament_package()
