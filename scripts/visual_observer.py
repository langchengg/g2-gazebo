#!/usr/bin/env python3
"""Read-only desktop observer; the button calls the existing Trigger service.

This is an optional visualization tool, not a third application controller.
Tk schedules ROS spin without blocking the executor or relying on sim timers.
"""
import argparse
import json
from pathlib import Path
import signal
import socket
import time
import tkinter as tk

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from std_srvs.srv import Trigger


class Observer(Node):
    def __init__(self, output):
        super().__init__('visual_observer', namespace='/g2/tools',
                         parameter_overrides=[Parameter('use_sim_time', value=True)])
        self.output = output
        self.status = {'state': 'WAITING', 'source': 'gazebo', 'run_id': ''}
        self.health = {}
        self.sample = None
        self.clock_ns = 0
        self.clock_changed = self.sample_changed = 0.
        self.response = 'This window has not submitted a request. State/run_id above also track external requests.'
        self.pending = None
        self.target = json.loads(Path('/opt/g2-model/conversion.json').read_text())['target_joint']
        source = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        state = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                           durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(Clock, '/clock', self.clock, source)
        self.create_subscription(JointState, '/g2/joint_states', self.joints, 10)
        self.create_subscription(String, '/g2/hello_status', self.on_status, state)
        self.create_subscription(String, '/g2/telemetry_health', self.on_health, state)
        self.trigger = self.create_client(Trigger, '/g2/say_hello')

    def clock(self, msg):
        ns = msg.clock.sec * 10**9 + msg.clock.nanosec
        if ns != self.clock_ns:
            self.clock_changed = time.monotonic()
        self.clock_ns = ns

    def joints(self, msg):
        ns = msg.header.stamp.sec * 10**9 + msg.header.stamp.nanosec
        if self.sample is None or ns != self.sample['stamp_ns']:
            self.sample_changed = time.monotonic()
        self.sample = {'stamp_ns': ns, 'names': list(msg.name), 'position': list(msg.position)}

    def on_status(self, msg):
        self.status = json.loads(msg.data)

    def on_health(self, msg):
        self.health = json.loads(msg.data)

    def ready(self):
        now = time.monotonic()
        return (self.clock_ns > 0 and now-self.clock_changed < 2. and self.sample and
                now-self.sample_changed < 2. and self.trigger.service_is_ready())

    def request(self):
        if not self.ready() or self.pending is not None:
            self.response = 'REJECTED locally: not READY or response pending.'
            return
        self.response = 'Waiting for existing /g2/say_hello response...'
        self.pending = self.trigger.call_async(Trigger.Request())
        self.pending_at = time.monotonic()

    def snapshot(self):
        now = time.monotonic()
        if self.pending is not None:
            if self.pending.done():
                try:
                    result = self.pending.result()
                    self.response = ('ACCEPTED: ' if result.success else 'REJECTED: ') + result.message
                except Exception as error:
                    self.response = 'SERVICE ERROR: ' + str(error)
                self.pending = None
            elif now-self.pending_at > 10.:
                self.pending.cancel()
                self.pending = None
                self.response = 'Service response timeout; no automatic retry.'
        value = {'ready': bool(self.ready()), 'backend': 'gazebo', 'sim_time_s': self.clock_ns/1e9,
                 'source_age_wall_s': now-self.sample_changed if self.sample else None,
                 'clock_age_wall_s': now-self.clock_changed if self.clock_ns else None,
                 'target_joint': self.target, 'status': self.status,
                 'health': self.health, 'sample': self.sample, 'service_response': self.response,
                 'wall_monotonic_s': now}
        if self.output:
            temporary = self.output.with_suffix('.tmp')
            temporary.write_text(json.dumps(value, indent=2))
            temporary.replace(self.output)
        return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/evidence/observer.json'))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = Observer(args.output)
    root = tk.Tk()
    root.wm_client(socket.gethostname())
    root.title('G2 Live State - Gazebo source - explicit motion only')
    root.geometry('1600x210+0+670')
    root.configure(bg='#142333')
    text = tk.StringVar()
    tk.Label(root, textvariable=text, font=('DejaVu Sans Mono', 12), justify='left',
             anchor='w', bg='#142333', fg='#e4f2ff').pack(side='left', fill='both', expand=True, padx=12)
    button = tk.Button(root, text='Say hello\n0.05 rad round trip', command=node.request,
                       font=('DejaVu Sans', 13), padx=12, pady=14)
    button.pack(side='right', padx=16)
    closed = False

    def close(*_):
        nonlocal closed
        if not closed:
            closed = True
            root.quit()

    def update():
        if closed:
            return
        for _ in range(10):
            rclpy.spin_once(node, timeout_sec=0.)
        data = node.snapshot()
        sample = data['sample']
        position = 'unavailable'
        if sample and node.target in sample['names']:
            position = f"{sample['position'][sample['names'].index(node.target)]:+.6f} rad"
        status = data['status']
        state = status.get('state', status.get('status', 'WAITING'))
        age = data['source_age_wall_s']
        age_text = f'{age:.2f} s' if age is not None else 'unavailable'
        text.set(f"{'READY' if data['ready'] else 'WAITING / PAUSED / STALE'}  |  backend=gazebo  |  sim={data['sim_time_s']:.3f} s  |  source age={age_text}\n"
                 f"State: {state}    run_id: {status.get('run_id', '')}\n"
                 f"{node.target}: {position}    Raw: /g2/sim/joint_states -> telemetry -> /g2/joint_states\n"
                 f"{data['service_response'][:175]}\n"
                 'Gazebo: left-drag pan; Shift+left/middle-drag orbit; wheel zoom. RViz: left-drag orbit; wheel zoom.')
        button.configure(state='normal' if data['ready'] and node.pending is None else 'disabled')
        root.after(100, update)

    root.protocol('WM_DELETE_WINDOW', close)
    signal.signal(signal.SIGTERM, close)
    signal.signal(signal.SIGINT, close)
    try:
        update()
        root.mainloop()
    finally:
        node.destroy_node()
        rclpy.shutdown()
        root.destroy()


if __name__ == '__main__':
    main()
