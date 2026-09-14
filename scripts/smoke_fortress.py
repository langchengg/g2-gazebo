#!/usr/bin/env python3
"""Run the pinned upstream cart demo before attempting the G2 model."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import rclpy
from rclpy.action import ActionClient
from rclpy.qos import qos_profile_sensor_data
from control_msgs.action import FollowJointTrajectory
from controller_manager_msgs.srv import ListControllers
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectoryPoint

out = Path(os.environ.get('EVIDENCE_DIR', '/evidence'))
out.mkdir(parents=True, exist_ok=True)
log = (out/'official-cart.log').open('w')
process = subprocess.Popen(['ros2', 'launch', 'gz_ros2_control_demos',
                            'cart_example_position.launch.py', 'gz_args:=-s'],
                           stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
rclpy.init()
node = rclpy.create_node('fortress_cart_probe')
samples = []
sub = node.create_subscription(JointState, '/joint_states', lambda m: samples.append(m), qos_profile_sensor_data)
client = ActionClient(node, FollowJointTrajectory, '/joint_trajectory_controller/follow_joint_trajectory')

def wait(predicate, timeout):
    end = time.monotonic()+timeout
    while not predicate():
        if process.poll() is not None:
            raise RuntimeError('upstream demo exited')
        if time.monotonic() > end:
            raise RuntimeError('official demo readiness/action timeout')
        rclpy.spin_once(node, timeout_sec=0.05)

try:
    wait(lambda: len(samples)>2 and client.server_is_ready(), 80)
    manager = node.create_client(ListControllers, '/controller_manager/list_controllers')
    wait(manager.service_is_ready, 20)
    deadline = time.monotonic()+20
    while True:
        states = manager.call_async(ListControllers.Request())
        wait(states.done, 5)
        if any(c.name == 'joint_trajectory_controller' and c.state == 'active' for c in states.result().controller):
            break
        if time.monotonic() > deadline:
            raise RuntimeError('trajectory controller did not activate')
        rclpy.spin_once(node, timeout_sec=0.05)
    baseline = samples[-1].position[samples[-1].name.index('slider_to_cart')]
    goal = FollowJointTrajectory.Goal()
    goal.trajectory.joint_names = ['slider_to_cart']
    point = JointTrajectoryPoint()
    point.positions = [baseline+0.1]
    point.time_from_start.sec = 2
    goal.trajectory.points = [point]
    future = client.send_goal_async(goal)
    wait(future.done, 10)
    handle = future.result()
    assert handle.accepted
    result = handle.get_result_async()
    wait(result.done, 40)
    assert result.result().status == 4 and result.result().result.error_code == 0
    observed = [m.position[m.name.index('slider_to_cart')] for m in samples]
    assert max(observed)-baseline > 0.08
    (out/'official-cart-result.json').write_text(json.dumps({'baseline': baseline,
        'observed_peak': max(observed), 'samples': len(observed), 'controller_status': result.result().status,
        'controller_error_code': result.result().result.error_code, 'result': 'PASS'}, indent=2))
finally:
    node.destroy_node()
    rclpy.shutdown()
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(20)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(10)
    log.close()
