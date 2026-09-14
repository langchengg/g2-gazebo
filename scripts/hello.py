#!/usr/bin/env python3
"""Submit a request without changing enable_motion or backend."""
import argparse
import json
import time
import rclpy
from sensor_msgs.msg import JointState
from std_srvs.srv import Trigger

parser=argparse.ArgumentParser()
parser.add_argument('--ready-only',action='store_true')
args=parser.parse_args()
rclpy.init()
node=rclpy.create_node('g2_cli_probe')
client=node.create_client(Trigger,'/g2/say_hello')
samples=[]
sub=node.create_subscription(JointState,'/g2/joint_states',lambda m:samples.append(m),10)
deadline=time.monotonic()+20
try:
    while time.monotonic()<deadline and not (client.service_is_ready() and len(samples)>=2):
        rclpy.spin_once(node,timeout_sec=0.1)
    if not client.service_is_ready() or len(samples)<2:
        raise RuntimeError('Timed out waiting for service and telemetry')
    if args.ready_only:
        print('READY: service and live telemetry observed; no motion requested')
    else:
        future=client.call_async(Trigger.Request())
        while time.monotonic()<deadline and not future.done():
            rclpy.spin_once(node,timeout_sec=0.1)
        if not future.done():
            raise RuntimeError('Service response timed out')
        response=future.result()
        print(json.dumps({'accepted':response.success,'message':response.message}))
        if not response.success:
            raise SystemExit(2)
finally:
    node.destroy_node()
    rclpy.shutdown()
