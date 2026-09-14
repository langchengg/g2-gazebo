#!/usr/bin/env python3
"""Submit without changing motion permission; rejected service responses fail."""
import json
import time
import rclpy
from std_srvs.srv import Trigger

rclpy.init()
node = rclpy.create_node('sim_hello_cli')
try:
    client = node.create_client(Trigger, '/g2/say_hello')
    if not client.wait_for_service(timeout_sec=10):
        raise RuntimeError('say_hello service unavailable')
    future = client.call_async(Trigger.Request())
    deadline = time.monotonic() + 10
    while not future.done() and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
    if not future.done():
        raise RuntimeError('service response timeout')
    response = future.result()
    print(json.dumps({'success': response.success, 'message': response.message}))
    code = 0 if response.success else 2
finally:
    node.destroy_node()
    rclpy.shutdown()
raise SystemExit(code)
