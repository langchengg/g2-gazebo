cmake_minimum_required(VERSION 3.16)
project(agibot_g2_demo LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(BUILD_GDK_BACKEND "Build the verified, proprietary GDK 2.6.3 backend" OFF)
set(GDK_SDK_ROOT "" CACHE PATH "Local GDK 2.6.3 SDK directory; never downloaded by this project")
if(BUILD_GDK_BACKEND)
  if(NOT GDK_SDK_ROOT OR NOT IS_DIRECTORY "${GDK_SDK_ROOT}")
    message(FATAL_ERROR "BUILD_GDK_BACKEND=ON is BLOCKED: provide the official GDK 2.6.3 SDK with -DGDK_SDK_ROOT=/absolute/path. No SDK is bundled.")
  endif()
  message(FATAL_ERROR "GDK backend UNIMPLEMENTED: SDK headers, version/ABI and motion semantics must first be verified. Providing a directory does not enable a fabricated adapter. See docs/gdk_api_mapping.md.")
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rcl_interfaces REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(std_srvs REQUIRED)

add_library(mock_core src/core.cpp)
target_include_directories(mock_core PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
target_compile_options(mock_core PRIVATE -Wall -Wextra -Wpedantic)

add_executable(sayHello src/say_hello.cpp)
target_link_libraries(sayHello mock_core)
ament_target_dependencies(sayHello rclcpp rcl_interfaces sensor_msgs std_msgs std_srvs)
target_compile_options(sayHello PRIVATE -Wall -Wextra -Wpedantic)

add_executable(telemetry src/telemetry.cpp)
target_link_libraries(telemetry mock_core)
ament_target_dependencies(telemetry rclcpp rcl_interfaces sensor_msgs std_msgs)
target_compile_options(telemetry PRIVATE -Wall -Wextra -Wpedantic)

install(TARGETS mock_core sayHello telemetry
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY include/ DESTINATION include)
install(DIRECTORY launch config DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_gtest(test_core test/test_core.cpp TIMEOUT 30)
  target_link_libraries(test_core mock_core)
  ament_add_pytest_test(integration_test test/integration_test.py TIMEOUT 240
    ENV "ROS_LOCALHOST_ONLY=1")
endif()

ament_package()
