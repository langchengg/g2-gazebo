# G2 RViz application entry point

`agibot_g2_visual_tools` installs `rviz2_close_order` under
`lib/agibot_g2_visual_tools`. Run it with the same RViz arguments, for example
`ros2 run agibot_g2_visual_tools rviz2_close_order -d /path/to/config.rviz`.
The project desktop supplies the shared simulation configuration and ROS arguments.

This entry point adapts the official ROS 2 Humble RViz
[`rviz2/src/main.cpp`](https://github.com/ros2/rviz/blob/4e2b27b7561da7eb03fbc7e92a74d4b3f1e0b054/rviz2/src/main.cpp)
at commit `4e2b27b7561da7eb03fbc7e92a74d4b3f1e0b054`.
The original Willow Garage and Open Source Robotics Foundation copyright notices
and BSD 3-clause terms are retained in the C++ source and [LICENSE](LICENSE).
The license and this attribution are also installed beside the package manifest.

The application still uses the installed official `rviz_common::VisualizerApp`,
RViz displays, plugins, rendering, configuration loading, TF processing, logging,
and ROS signal handling. It does not generate joint states or alter the robot.
Only the application entry point is adapted: a Close event filter stops the
VisualizationManager update timer before the official window close handler runs;
`aboutToQuit` stops it again. If the official close handler rejects the event
(for example, the user cancels a save prompt), updates resume after that handler
returns. The original event is delivered once, and `QPointer` tracks frame lifetime.
No custom signal handler or forced-success exit is introduced.

The package builds against the existing Humble `rclcpp`, `rviz_common`,
`rviz_ogre_vendor`, and Qt 5 development dependencies using `ament_cmake`.
No model or SDK is bundled. Build/install checks do not establish GUI shutdown
correctness: full simulation, camera interaction, cancellation, and lifecycle
acceptance belong to the release-specific evidence outside this package.
