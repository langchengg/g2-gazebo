"""Launch the two project application nodes; no hardware API is invoked."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def stop_on_application_exit(event, context):
    if event.returncode != 0 and not context.is_shutdown:
        # Humble LaunchService converts a callback exception to exit code 1 and
        # shuts down remaining actions. A plain Shutdown would hide this error.
        raise RuntimeError(f"application node exited with code {event.returncode}")
    if not context.is_shutdown:
        return [EmitEvent(event=Shutdown(reason="application node exited"))]
    return []


def generate_launch_description():
    config_file = PathJoinSubstitution(
        [FindPackageShare("agibot_g2_demo"), "config", "mock.yaml"]
    )
    arguments = [
        DeclareLaunchArgument("namespace", default_value="g2"),
        DeclareLaunchArgument("backend", default_value="mock"),
        DeclareLaunchArgument("enable_motion", default_value="false"),
        DeclareLaunchArgument("publish_hz", default_value="10.0"),
        DeclareLaunchArgument("fault_mode", default_value="none"),
        DeclareLaunchArgument("fault_after", default_value="0.5"),
    ]
    shared = {
        "backend": ParameterValue(LaunchConfiguration("backend"), value_type=str),
        "publish_hz": ParameterValue(LaunchConfiguration("publish_hz"), value_type=float),
    }
    say_hello = Node(
        package="agibot_g2_demo",
        executable="sayHello",
        name="sayHello",
        namespace=LaunchConfiguration("namespace"),
        parameters=[config_file, shared, {
            "enable_motion": ParameterValue(LaunchConfiguration("enable_motion"), value_type=bool),
            "fault_mode": ParameterValue(LaunchConfiguration("fault_mode"), value_type=str),
            "fault_after": ParameterValue(LaunchConfiguration("fault_after"), value_type=float),
        }],
        output="screen",
    )
    telemetry = Node(
        package="agibot_g2_demo",
        executable="telemetry",
        name="telemetry",
        namespace=LaunchConfiguration("namespace"),
        parameters=[config_file, shared],
        output="screen",
    )
    # A surviving telemetry process must not hide a failed backend owner.
    handlers = [
        RegisterEventHandler(OnProcessExit(
            target_action=node,
            on_exit=stop_on_application_exit,
        ))
        for node in (say_hello, telemetry)
    ]
    return LaunchDescription(arguments + handlers + [say_hello, telemetry])
