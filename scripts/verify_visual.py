#!/usr/bin/env python3
"""Correlate Gazebo source, public telemetry, description and actual TF.

No goal is sent. Run concurrently with an explicitly requested motion to capture
moving samples. This is numerical TF evidence, not a substitute for GUI review.
"""
import argparse
from collections import deque
import hashlib
import json
import math
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, qos_profile_parameters
from rclpy.time import Time
from rcl_interfaces.srv import GetParameters
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from tf2_ros import Buffer, TransformListener, TransformException


from agibot_g2_demo.visual_geometry import fk, transform_matrix


def sample(msg):
    return {'stamp_ns': msg.header.stamp.sec*10**9+msg.header.stamp.nanosec,
            'position': dict(zip(msg.name, msg.position))}


class VisualProbe(Node):
    """Correlate generated-model FK, shared telemetry, and timestamped TF.

    This numerical probe checks that RViz infrastructure follows the same joint
    source and description as Gazebo. It does not replace human inspection of a
    rendered window.
    """
    def __init__(self, urdf):
        super().__init__('visual_tf_verification', namespace='/g2/test',
                         parameter_overrides=[Parameter('use_sim_time', value=True)])
        self.urdf = urdf
        tree = ET.fromstring(urdf)
        self.frames = sorted(link.get('name') for link in tree.findall('link') if link.get('name') != 'world')
        conversion = json.loads(Path('/opt/g2-model/conversion.json').read_text())
        self.target = conversion['target_joint']
        self.names = conversion['controlled_joints']
        joints = list(tree.findall('joint'))
        tip_joint = next(j for j in joints if j.get('name') == self.names[-1])
        self.tip = tip_joint.find('child').get('link')
        by_child = {j.find('child').get('link'): j for j in joints}
        chain = []
        current = self.tip
        while current != 'world':
            joint = by_child[current]
            chain.append(joint)
            current = joint.find('parent').get('link')
        self.chain = list(reversed(chain))
        self.base = self.chain[0].find('child').get('link')
        self.raw = {}
        self.public = deque(maxlen=2000)
        self.description = None
        self.status = {}
        self.results = []
        self.checked = set()
        self.infrastructure = {}
        self.parameter_queries = {}
        for name in ['/g2/sayHello', '/g2/telemetry', '/g2/sim/robot_state_publisher',
                     '/g2/sim/controller_manager', '/g2/sim/arm_controller',
                     '/g2/sim/joint_state_broadcaster', '/g2/sim/clock_bridge',
                     '/g2/tools/rviz2', '/g2/tools/visual_observer']:
            self.parameter_queries[name] = {'client': self.create_client(
                GetParameters, name+'/get_parameters', qos_profile=qos_profile_parameters),
                'future': None, 'attempt': 0, 'started': 0., 'value': None}
        self.buffer = Buffer(node=self)
        self.listener = TransformListener(self.buffer, self, spin_thread=False)
        qos = QoSProfile(depth=1000, reliability=ReliabilityPolicy.BEST_EFFORT)
        retained = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                              durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(JointState, '/g2/sim/joint_states', self.on_raw, qos)
        self.create_subscription(JointState, '/g2/joint_states', lambda m: self.public.append(sample(m)), 1000)
        self.create_subscription(String, '/g2/sim/robot_description', self.on_description, retained)
        self.create_subscription(String, '/g2/hello_status', self.on_status, retained)

    def on_raw(self, msg):
        value = sample(msg)
        self.raw[value['stamp_ns']] = value
        if len(self.raw) > 10000:
            del self.raw[next(iter(self.raw))]

    def on_description(self, msg):
        self.description = msg.data

    def on_status(self, msg):
        self.status = json.loads(msg.data)

    def check(self):
        # Read-only parameter discovery runs concurrently with sample collection.
        # A lost DDS request gets at most three attempts; the outer wall deadline
        # still applies, including when a parameter service never appears.
        for name, query in self.parameter_queries.items():
            future = query['future']
            if query['value'] is not None:
                continue
            if future is not None and future.done():
                response = future.result()
                assert len(response.values) == 1 and response.values[0].type == 1, name+' has no boolean use_sim_time'
                query['value'] = response.values[0].bool_value
                assert query['value'] is True, name+' does not use simulation time'
            elif future is not None and time.monotonic()-query['started'] > 10.:
                query['client'].remove_pending_request(future)
                future.cancel()
                query['future'] = None
                assert query['attempt'] < 3, name+' parameter response timeout'
            elif future is None and query['client'].service_is_ready():
                request = GetParameters.Request()
                request.names = ['use_sim_time']
                query.update(future=query['client'].call_async(request),
                             started=time.monotonic(), attempt=query['attempt']+1)
        assert self.description in (None, self.urdf), 'RSP publishes a different URDF'
        for value in list(self.public):
            stamp = value['stamp_ns']
            if stamp in self.checked or stamp not in self.raw:
                continue
            assert value['position'] == self.raw[stamp]['position'], 'public telemetry differs from Gazebo source'
            try:
                observed = self.buffer.lookup_transform('world', self.tip, Time(nanoseconds=stamp))
                base = self.buffer.lookup_transform('world', self.base, Time())
            except TransformException:
                continue
            expected = fk(self.chain, value['position'])
            error = float(np.max(np.abs(expected-transform_matrix(observed))))
            # RSP throttles to 20 Hz; TF interpolation can straddle source samples.
            # 0.0005 matrix tolerance is far below the requested 0.05 rad motion.
            assert error < .0005, 'TF / same-stamp source FK mismatch: '+str(error)
            assert np.isfinite(transform_matrix(base)).all(), 'invalid world to fixed base TF'
            self.results.append({'stamp_ns': stamp, 'run_id': self.status.get('run_id'),
                'state': self.status.get('state', self.status.get('status')), 'target_joint': self.target,
                'position_rad': value['position'][self.target], 'tf_tip': self.tip,
                'fk_matrix_max_abs_error': error, 'raw_public_identical': True,
                'expected_matrix': expected.tolist(), 'observed_tf_matrix': transform_matrix(observed).tolist()})
            self.checked.add(stamp)

    def check_infrastructure(self):
        assert all(q['value'] is True for q in self.parameter_queries.values()), 'use_sim_time query incomplete'
        expected = {'/clock': '/g2/sim/clock_bridge', '/tf': '/g2/sim/robot_state_publisher',
                    '/tf_static': '/g2/sim/robot_state_publisher',
                    '/g2/sim/robot_description': '/g2/sim/robot_state_publisher',
                    '/g2/sim/joint_states': '/g2/sim/joint_state_broadcaster',
                    '/g2/joint_states': '/g2/telemetry'}
        endpoints = {}
        for topic, owner in expected.items():
            publishers = self.get_publishers_info_by_topic(topic)
            assert len(publishers) == 1, (topic, 'expected one publisher', len(publishers))
            endpoint = publishers[0]
            identity = endpoint.node_namespace.rstrip('/')+'/'+endpoint.node_name
            assert identity == owner, (topic, 'unexpected publisher', identity)
            if topic in ('/tf_static', '/g2/sim/robot_description'):
                assert endpoint.qos_profile.durability == DurabilityPolicy.TRANSIENT_LOCAL, topic+' is not retained'
                assert endpoint.qos_profile.reliability == ReliabilityPolicy.RELIABLE, topic+' is not reliable'
            endpoints[topic] = {'node': identity, 'durability': str(endpoint.qos_profile.durability),
                                'reliability': str(endpoint.qos_profile.reliability)}
        rviz = [p for p in self.get_subscriptions_info_by_topic('/g2/sim/robot_description')
                if (p.node_name, p.node_namespace) == ('rviz2', '/g2/tools')]
        assert len(rviz) == 1, 'configured RViz does not subscribe to this description'
        assert rviz[0].qos_profile.durability == DurabilityPolicy.TRANSIENT_LOCAL, 'RViz description subscription is not retained'
        assert rviz[0].qos_profile.reliability == ReliabilityPolicy.RELIABLE, 'RViz description subscription is not reliable'
        frame_evidence = {}
        for frame in self.frames:
            matrix = transform_matrix(self.buffer.lookup_transform('world', frame, Time()))
            assert np.isfinite(matrix).all(), 'invalid world TF for '+frame
            frame_evidence[frame] = matrix.tolist()
        self.infrastructure = {'publishers': endpoints, 'rviz_description_qos_checked': True,
            'use_sim_time': {name: q['value'] for name, q in self.parameter_queries.items()},
            'world_frame_count': len(frame_evidence), 'world_frame_matrices': frame_evidence}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration', type=float, default=15.)
    parser.add_argument('--timeout', type=float, default=90.)
    parser.add_argument('--output', type=Path, default=Path('/evidence/visual-tf.json'))
    parser.add_argument('--require-motion', action='store_true')
    parser.add_argument('--motion-result', type=Path, help='Wait for this independent motion receipt and its run_id to finish')
    args = parser.parse_args()
    if not 1 <= args.duration <= args.timeout <= 300:
        parser.error('require 1 <= duration <= timeout <= 300')
    rclpy.init()
    node = VisualProbe(Path('/opt/g2-model/g2.urdf').read_text())
    started = time.monotonic()
    ready_at = None
    terminal_at = None
    motion_run_id = None
    error = None
    succeeded = False
    try:
        while time.monotonic()-started < args.timeout:
            rclpy.spin_once(node, timeout_sec=.05)
            node.check()
            if node.description is not None and len(node.results) >= 5 and ready_at is None:
                ready_at = time.monotonic()
            if args.motion_result and args.motion_result.exists():
                try:
                    motion = json.loads(args.motion_result.read_text())
                except json.JSONDecodeError:
                    continue  # Writer has not closed its bounded final receipt yet.
                assert motion['status'] == 'PASS', 'independent motion verification failed'
                assert len(motion['run_ids']) == 1, 'expected exactly one explicitly recorded run'
                motion_run_id = motion['run_ids'][0]
                matching = [s for s in node.results if s['run_id'] == motion_run_id]
                if any(s['state'] == 'SUCCEEDED' for s in matching) and terminal_at is None:
                    terminal_at = time.monotonic()
            complete = not args.motion_result or (terminal_at is not None and time.monotonic()-terminal_at >= 2.)
            parameters_ready = all(q['value'] is True for q in node.parameter_queries.values())
            if ready_at is not None and time.monotonic()-ready_at >= args.duration and complete and parameters_ready:
                break
        assert ready_at is not None and len(node.results) >= 10, 'TF/source correlation readiness timeout'
        assert time.monotonic()-ready_at >= args.duration, 'TF observation duration exceeded total timeout'
        if args.motion_result:
            assert terminal_at is not None and time.monotonic()-terminal_at >= 2., 'motion terminal TF observation deadline'
        graph = node.get_node_names_and_namespaces()
        assert graph.count(('robot_state_publisher', '/g2/sim')) == 1, 'RSP must be unique'
        assert graph.count(('rviz2', '/g2/tools')) == 1, 'expected the configured RViz instance'
        sources = node.get_publishers_info_by_topic('/g2/sim/joint_states')
        assert sources and all(p.node_name == 'joint_state_broadcaster' for p in sources), 'unexpected source publisher'
        node.check_infrastructure()
        selected = [v for v in node.results if not args.motion_result or v['run_id'] == motion_run_id]
        target_values = [v['position_rad'] for v in selected]
        if args.require_motion:
            assert len(selected) >= 10, 'too few samples for the requested run_id'
            assert max(target_values)-min(target_values) > .04, 'no substantial movement during TF correlation'
            if args.motion_result:
                assert {'RUNNING', 'SUCCEEDED'} <= {v['state'] for v in selected}, 'missing motion or terminal TF samples'
        succeeded = True
    except BaseException as exc:
        error = type(exc).__name__+': '+str(exc)
        raise
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({'result': 'PASS' if succeeded else 'FAIL', 'error': error,
            'description_sha256': hashlib.sha256(node.urdf.encode()).hexdigest(),
            'description_topic': '/g2/sim/robot_description', 'fixed_frame': 'world',
            'sample_count': len(node.results), 'wall_seconds': time.monotonic()-started,
            'max_fk_matrix_error': max((s['fk_matrix_max_abs_error'] for s in node.results), default=None),
            'motion_run_id': motion_run_id, 'infrastructure': node.infrastructure,
            'samples': node.results}, indent=2))
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
