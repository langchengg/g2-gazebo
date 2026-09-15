"""Orchestrate one fixed-base G2 world and the two project applications.

Gazebo, robot_state_publisher, and both applications share the generated URDF and
broadcaster feedback chain. Startup is ordered so applications cannot accept work
before controller activation completes.
"""
import hashlib
import json
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, IncludeLaunchDescription, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def setup(context):
    """Validate generated assets and construct the ordered process graph.

    Hashes prove consistency with the local generated manifest, not independent
    vendor authenticity. The inventory supplies complete joint names and limits
    to both applications instead of duplicating model facts in source code.
    """
    assets = Path(LaunchConfiguration('model_dir').perform(context))
    manifest = json.loads((assets / 'generated_manifest.json').read_text())
    for name, digest in manifest['files'].items():
        path = assets / name
        if not path.resolve().is_relative_to(assets.resolve()):
            raise ValueError('unsafe generated asset path')
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('model checksum mismatch: ' + name)
    inventory = json.loads((assets / 'joint_inventory.json').read_text())
    conversion = json.loads((assets / 'conversion.json').read_text())
    by_name = {j['name']: j for j in inventory['joints'] if j['controlled']}
    names = conversion['controlled_joints']
    if len(names) != 7 or set(names) != set(by_name):
        raise ValueError('expected the complete seven-joint model arm inventory')
    shared = {'backend': 'gazebo', 'use_sim_time': True,
              'sim_joint_names': names, 'target_joint': conversion['target_joint'],
              'sim_state_interfaces': ['position', 'velocity', 'effort']}
    for param, field in [('sim_joint_lower_limits', 'lower'), ('sim_joint_upper_limits', 'upper'),
                         ('sim_joint_velocity_limits', 'velocity')]:
        shared[param] = [float(by_name[name]['limit'][field]) for name in names]
    app_share = Path(get_package_share_directory('agibot_g2_demo'))
    description = Path(get_package_share_directory('agibot_g2_description'))
    world = description / 'worlds/g2_demo.sdf'
    # Gazebo owns physics. The one-way bridge exports its clock to ROS, while
    # robot_state_publisher consumes the same URDF and broadcaster joint states.
    server = IncludeLaunchDescription(PythonLaunchDescriptionSource(
        str(Path(get_package_share_directory('ros_gz_sim')) / 'launch/gz_sim.launch.py')),
        launch_arguments={'gz_args': '-r -s -v 3 ' + str(world), 'on_exit_shutdown': 'true'}.items())
    bridge = Node(package='ros_gz_bridge', executable='parameter_bridge',
        name='clock_bridge', namespace='g2/sim', output='screen',
        arguments=['/world/g2_demo/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock'],
        remappings=[('/world/g2_demo/clock', '/clock')], parameters=[{'use_sim_time': True}])
    rsp = Node(package='robot_state_publisher', executable='robot_state_publisher',
        name='robot_state_publisher', namespace='g2/sim', output='screen',
        parameters=[{'robot_description': (assets / 'g2.urdf').read_text(), 'use_sim_time': True}],
        remappings=[('joint_states', '/g2/sim/joint_states')])
    spawn = Node(package='ros_gz_sim', executable='create', output='screen',
        arguments=['-world', 'g2_demo', '-name', 'g2', '-file', str(assets / 'g2.urdf'),
                   '-allow_renaming', 'false'])
    broadcaster = Node(package='controller_manager', executable='spawner', output='screen',
        arguments=['joint_state_broadcaster', '--controller-manager', '/g2/sim/controller_manager',
                   '--controller-manager-timeout', '60'], parameters=[{'use_sim_time': True}])
    arm = Node(package='controller_manager', executable='spawner', output='screen',
        arguments=['arm_controller', '--controller-manager', '/g2/sim/controller_manager',
                   '--controller-manager-timeout', '60'], parameters=[{'use_sim_time': True}])
    enabled = LaunchConfiguration('enable_motion').perform(context).lower()
    if enabled not in ('true', 'false'):
        raise ValueError('enable_motion must be true or false')
    apps = [Node(package='agibot_g2_demo', executable=exe, name=exe, namespace='g2',
        parameters=[str(app_share / 'config/sim.yaml'), shared] +
                   ([{'enable_motion': enabled == 'true'}] if exe == 'sayHello' else []),
        output='screen') for exe in ['sayHello', 'telemetry']]

    def next_when_ok(next_actions):
        """Continue startup only after the preceding spawner exits successfully."""
        def callback(event, ctx):
            if ctx.is_shutdown:
                return []
            if event.returncode != 0:
                raise RuntimeError('simulation startup process failed: ' + str(event.returncode))
            return next_actions
        return callback

    def stop_on_exit(event, ctx):
        """Shut down the launch when a long-lived component exits normally."""
        if ctx.is_shutdown:
            return []
        if event.returncode != 0:
            raise RuntimeError('simulation component failed: ' + str(event.returncode))
        return [EmitEvent(event=Shutdown(reason='simulation component exited'))]

    def fail_on_process_error(event, ctx):
        """Promote any process failure to a launch-wide nonzero shutdown."""
        if event.returncode != 0 and not ctx.is_shutdown:
            raise RuntimeError('simulation process exited abnormally: ' + str(event.returncode))
        return []

    # Spawn the model, activate state broadcasting, activate trajectory control,
    # then start both applications. Runtime controller freshness remains checked
    # by the backend after the spawner activation step.
    handlers = [RegisterEventHandler(OnProcessExit(on_exit=fail_on_process_error)), RegisterEventHandler(OnProcessExit(target_action=spawn, on_exit=next_when_ok([broadcaster]))),
                RegisterEventHandler(OnProcessExit(target_action=broadcaster, on_exit=next_when_ok([arm]))),
                RegisterEventHandler(OnProcessExit(target_action=arm, on_exit=next_when_ok(apps)))]
    handlers += [RegisterEventHandler(OnProcessExit(target_action=n, on_exit=stop_on_exit))
                 for n in [bridge, rsp] + apps]
    return handlers + [server, bridge, rsp, spawn]


def generate_launch_description():
    """Declare generated assets and the explicit, false-by-default motion opt-in."""
    return LaunchDescription([
        DeclareLaunchArgument('model_dir', default_value='/opt/g2-model'),
        DeclareLaunchArgument('enable_motion', default_value='false'),
        OpaqueFunction(function=setup)])
