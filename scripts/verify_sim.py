#!/usr/bin/env python3
"""Bounded real ROS/Gazebo probe. This script does not start a simulator.

Run inside the simulation container after sourcing the installed ROS workspace.
Observations come from ROS subscriptions and read-only Ignition world services.
No simulator types are replaced.
"""
import argparse
from collections import deque
from datetime import datetime, timezone
import csv
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET

import rclpy
from rclpy.action import ActionClient, get_action_names_and_types
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy, qos_profile_parameters
from action_msgs.msg import GoalStatus, GoalStatusArray
from action_msgs.srv import CancelGoal
from control_msgs.action import FollowJointTrajectory
from controller_manager_msgs.srv import ListControllers, SwitchController
from rcl_interfaces.srv import GetParameters
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from std_srvs.srv import Trigger
from trajectory_msgs.msg import JointTrajectoryPoint


SOURCE_QOS = QoSProfile(depth=1000, reliability=ReliabilityPolicy.BEST_EFFORT,
                        durability=DurabilityPolicy.VOLATILE)
STATE_QOS = QoSProfile(depth=1000, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL)
PUBLIC_QOS = QoSProfile(depth=1000, reliability=ReliabilityPolicy.RELIABLE,
                        durability=DurabilityPolicy.VOLATILE)


def utc():
    return datetime.now(timezone.utc).isoformat()


def serial_values(values):
    # Preserve unavailable raw measurements visibly; JSON NaN is not valid JSON.
    return [float(v) if math.isfinite(v) else str(v) for v in values]


def sample(message):
    return {'wall_monotonic_s': time.monotonic(),
            'stamp_ns': message.header.stamp.sec * 10**9 + message.header.stamp.nanosec,
            'frame_id': message.header.frame_id, 'names': list(message.name),
            'position': serial_values(message.position),
            'velocity': serial_values(message.velocity), 'effort': serial_values(message.effort)}


def validate_sample(value, names):
    assert set(value['names']) == set(names), 'unexpected joint names'
    assert len(value['names']) == len(names), 'duplicate/missing joint'
    assert value['stamp_ns'] > 0, 'unset source timestamp'
    for field in ('position', 'velocity', 'effort'):
        array = value[field]
        assert (len(array) == len(names) if field == 'position' else len(array) in (0, len(names))), field
        assert all(isinstance(v, (float, int)) and math.isfinite(v) for v in array), field + ' nonfinite'


def positions(value, names):
    return [value['position'][value['names'].index(name)] for name in names]


def protobuf_top_fields(text):
    """Read top-level scalars/blocks from protobuf text, treating strings atomically.

    This is only a bounded evidence parser for the CLI's protobuf text output;
    it neither constructs simulator messages nor interprets serialized components.
    """
    if len(text) > 16 * 1024 * 1024:
        raise ValueError('protobuf evidence exceeds the 16 MiB parser limit')
    tokens = list(re.finditer(r'"(?:\\.|[^"\\])*"|[A-Za-z_][A-Za-z_0-9]*|[{}:]|[-+]?[0-9]+(?:\.[0-9]+)?', text))
    result = {}
    i = 0
    while i + 1 < len(tokens):
        name = tokens[i].group()
        following = tokens[i + 1].group()
        if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', name):
            i += 1
            continue
        if following == '{':
            depth = 1; j = i + 2
            while j < len(tokens) and depth:
                depth += (tokens[j].group() == '{') - (tokens[j].group() == '}')
                j += 1
            if depth:
                raise ValueError('unterminated protobuf evidence block: ' + name)
            value = text[tokens[i+1].end():tokens[j-1].start()]
            result.setdefault(name, []).append(value)
            i = j
        elif following == ':' and i + 2 < len(tokens):
            value = tokens[i+2].group()
            result.setdefault(name, []).append(value)
            i += 3
        else:
            i += 1
    return result


class Probe(Node):
    """Collect and cross-check live ROS/Gazebo acceptance evidence.

    The probe owns read-only subscriptions and explicit test clients. It measures
    baseline, requests one motion, and proves excursion and return from raw source
    samples rather than log text or action result alone. All waits have monotonic
    wall deadlines so paused simulation time cannot deadlock verification.
    """
    def __init__(self, timeout, evidence):
        super().__init__('g2_sim_verification_probe', namespace='/g2/test',
                         parameter_overrides=[Parameter('use_sim_time', value=True)])
        self.deadline = time.monotonic() + timeout
        self.evidence = evidence
        self.telemetry = deque(maxlen=80000)
        self.raw = deque(maxlen=80000)
        self.statuses = []
        self.healths = []
        self.clock_ns = None
        self.clock_wall = None
        self.clock_progress = 0
        self.clock_resets = 0
        self.cases = []
        self.details = {}
        self.commands = []
        self.parse_errors = []
        self.run_ids = []
        self.action_statuses = []
        self.create_subscription(JointState, '/g2/joint_states',
                                 lambda msg: self.telemetry.append(sample(msg)), PUBLIC_QOS)
        self.create_subscription(String, '/g2/hello_status',
                                 lambda msg: self.status(msg, self.statuses), STATE_QOS)
        self.create_subscription(String, '/g2/telemetry_health',
                                 lambda msg: self.status(msg, self.healths), STATE_QOS)
        self.create_subscription(Clock, '/clock', self.clock, SOURCE_QOS)
        self.trigger = self.create_client(Trigger, '/g2/say_hello')
        self.source_sub = self.manager = self.action = None

    def clock(self, msg):
        ns = msg.clock.sec * 10**9 + msg.clock.nanosec
        if self.clock_ns is None or ns != self.clock_ns:
            self.clock_progress += 1
            self.clock_wall = time.monotonic()
        if self.clock_ns is not None and ns < self.clock_ns:
            self.clock_resets += 1
        self.clock_ns = ns

    def status(self, msg, destination):
        try:
            data = json.loads(msg.data)
            assert isinstance(data, dict)
            data = dict(data, probe_wall_monotonic_s=time.monotonic())
            destination.append(data)
        except (ValueError, AssertionError) as error:
            self.parse_errors.append(str(error))

    def wait(self, condition, description, timeout=30.):
        until = min(self.deadline, time.monotonic() + timeout)
        while time.monotonic() < until:
            if condition():
                return
            rclpy.spin_once(self, timeout_sec=min(.05, max(0., until - time.monotonic())))
        raise TimeoutError(description + '; latest status=' + str(self.statuses[-1:] or []) +
                           '; latest health=' + str(self.healths[-1:] or []))

    def observe_wall_interval(self, seconds):
        until = time.monotonic() + seconds
        assert until <= self.deadline, 'global verification budget exhausted'
        while time.monotonic() < until:
            rclpy.spin_once(self, timeout_sec=min(.05, until - time.monotonic()))

    def await_future(self, future, description, timeout=10.):
        self.wait(future.done, description, timeout)
        return future.result()

    def case(self, name, function):
        start = time.monotonic()
        try:
            result = function()
        except BaseException as error:
            self.cases.append({'name': name, 'status': 'FAIL', 'seconds': time.monotonic() - start,
                               'error': type(error).__name__ + ': ' + str(error)})
            raise
        self.cases.append({'name': name, 'status': 'PASS', 'seconds': time.monotonic() - start})
        return result

    def parameters(self, node, names):
        # Discovery availability does not prove a response has arrived. Parameter
        # reads are idempotent, unlike Trigger/action requests: retry ONLY this
        # read-only query, retaining one client so DDS matching can settle.
        service = node + '/get_parameters'
        client = self.create_client(GetParameters, service, qos_profile=qos_profile_parameters)
        deadline = min(self.deadline, time.monotonic() + 40.)
        attempts = self.details.setdefault('parameter_queries', [])
        pending = None
        try:
            self.wait(client.service_is_ready, node + ' parameter service',
                      max(0., deadline - time.monotonic()))
            for number in range(1, 4):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(service + ' read-only query wall budget exhausted')
                record = {'service': service, 'names': list(names), 'attempt': number,
                          'started_wall_monotonic_s': time.monotonic(), 'status': 'PENDING'}
                attempts.append(record)
                request = GetParameters.Request()
                request.names = list(names)
                try:
                    pending = client.call_async(request)
                    response = self.await_future(pending, service + ' response attempt ' + str(number),
                                                 min(10., remaining))
                except TimeoutError as error:
                    record.update(status='TIMEOUT', error=str(error),
                                  service_available=client.service_is_ready())
                    # Forget the old sequence before retry; a delayed response
                    # cannot complete a later attempt or accumulate futures.
                    if pending is not None:
                        client.remove_pending_request(pending)
                        pending.cancel()
                        pending = None
                    if number == 3 or time.monotonic() >= deadline:
                        raise
                    continue
                except Exception as error:
                    record.update(status='ERROR', error=type(error).__name__ + ': ' + str(error))
                    raise
                finally:
                    record['wall_seconds'] = time.monotonic() - record['started_wall_monotonic_s']
                pending = None
                if len(response.values) != len(names):
                    record['status'] = 'INVALID_RESPONSE'
                    raise ValueError(service + ' returned wrong number of parameter values')
                fields = {1: 'bool_value', 2: 'integer_value', 3: 'double_value', 4: 'string_value',
                          5: 'byte_array_value', 6: 'bool_array_value', 7: 'integer_array_value',
                          8: 'double_array_value', 9: 'string_array_value'}
                if any(value.type not in fields for value in response.values):
                    record['status'] = 'INVALID_RESPONSE'
                    raise ValueError(service + ' returned an unset or unknown parameter type')
                record['status'] = 'PASS'
                return {name: getattr(value, fields[value.type])
                        for name, value in zip(names, response.values)}
        finally:
            if pending is not None:
                client.remove_pending_request(pending)
                pending.cancel()
            self.destroy_client(client)

    def configure(self):
        self.config = self.parameters('/g2/sayHello', [
            'backend', 'use_sim_time', 'enable_motion', 'target_joint', 'displacement', 'duration',
            'sim_joint_names', 'sim_joint_topic', 'sim_controller', 'sim_controller_manager',
            'sim_action', 'position_tolerance', 'sim_pause_timeout', 'feedback_timeout'])
        self.telemetry_config = self.parameters('/g2/telemetry', [
            'backend', 'use_sim_time', 'sim_joint_topic', 'publish_hz'])
        assert self.config['backend'] == self.telemetry_config['backend'] == 'gazebo'
        assert self.config['use_sim_time'] is self.telemetry_config['use_sim_time'] is True
        assert self.config['sim_joint_topic'] == self.telemetry_config['sim_joint_topic']
        self.names = list(self.config['sim_joint_names'])
        assert self.names and self.config['target_joint'] in self.names
        self.source_sub = self.create_subscription(JointState, self.config['sim_joint_topic'],
                                                   lambda msg: self.raw.append(sample(msg)), SOURCE_QOS)
        self.manager = self.create_client(ListControllers,
            self.config['sim_controller_manager'] + '/list_controllers')
        self.action = ActionClient(self, FollowJointTrajectory, self.config['sim_action'])
        self.create_subscription(GoalStatusArray, self.config['sim_action'] + '/_action/status',
                                 self.action_status, STATE_QOS)
        self.details['application_parameters'] = self.config
        self.details['telemetry_parameters'] = self.telemetry_config

    def action_status(self, message):
        self.action_statuses.append({'wall_monotonic_s': time.monotonic(), 'goals': [
            {'id': [int(value) for value in item.goal_info.goal_id.uuid], 'status': item.status,
             'stamp_ns': item.goal_info.stamp.sec * 10**9 + item.goal_info.stamp.nanosec}
            for item in message.status_list]})

    def ready(self):
        self.wait(lambda: (self.clock_progress >= 3 and self.clock_ns and len(self.telemetry) >= 6 and
                           len(self.raw) >= 6 and self.trigger.service_is_ready() and
                           self.action.server_is_ready() and self.manager.service_is_ready() and
                           self.statuses and self.statuses[-1].get('healthy') and self.healths and
                           self.healths[-1].get('status') == 'HEALTHY'),
                  'simulation clock, controller, app and feedback readiness', 80.)
        self.wait(lambda: self.telemetry[-1]['stamp_ns'] - self.telemetry[-6]['stamp_ns'] >= 400_000_000,
                  'advancing baseline', 20.)
        for value in list(self.telemetry)[-6:]:
            validate_sample(value, self.names)
        assert not self.parse_errors, self.parse_errors

    def graph(self):
        manager_name = self.config['sim_controller_manager']
        namespace, name = manager_name.rsplit('/', 1)
        expected_nodes = [('sayHello', '/g2'), ('telemetry', '/g2'), (name, namespace)]
        discovery = self.details.setdefault('graph_discovery', [])

        def complete():
            graph = self.get_node_names_and_namespaces()
            snapshot = sorted(graph)
            if not discovery or discovery[-1]['nodes'] != snapshot:
                discovery.append({'wall_monotonic_s': time.monotonic(), 'nodes': snapshot})
            return all(graph.count(expected) == 1 for expected in expected_nodes)

        self.wait(complete, 'exactly one discovered app instance and controller manager', 10.)
        graph = self.get_node_names_and_namespaces()
        assert all(graph.count(expected) == 1 for expected in expected_nodes), graph
        assert not any(name == 'joint_state_publisher' or name.startswith('mock') for name, ns in graph), graph
        response = self.await_future(self.manager.call_async(ListControllers.Request()), 'controller list')
        controllers = {item.name: {'state': item.state, 'type': item.type,
                                   'claimed_interfaces': list(item.claimed_interfaces)}
                       for item in response.controller}
        assert controllers[self.config['sim_controller']]['state'] == 'active', controllers
        assert controllers['joint_state_broadcaster']['state'] == 'active', controllers
        assert self.action.server_is_ready()
        actions = dict(get_action_names_and_types(self))
        assert actions[self.config['sim_action']] == ['control_msgs/action/FollowJointTrajectory']
        services = dict(self.get_service_names_and_types())
        assert services['/g2/say_hello'] == ['std_srvs/srv/Trigger']
        topics = dict(self.get_topic_names_and_types())
        assert topics['/clock'] == ['rosgraph_msgs/msg/Clock']
        assert topics[self.config['sim_joint_topic']] == ['sensor_msgs/msg/JointState']
        assert topics['/g2/joint_states'] == ['sensor_msgs/msg/JointState']
        endpoints = {}
        for topic in ('/clock', self.config['sim_joint_topic'], '/g2/joint_states'):
            publishers = self.get_publishers_info_by_topic(topic)
            assert len(publishers) == 1, (topic, len(publishers))
            endpoints[topic] = [{'node': p.node_namespace.rstrip('/') + '/' + p.node_name,
                                 'type': p.topic_type, 'reliability': str(p.qos_profile.reliability),
                                 'durability': str(p.qos_profile.durability)} for p in publishers]
        assert endpoints[self.config['sim_joint_topic']][0]['node'].endswith('/joint_state_broadcaster')
        assert endpoints['/g2/joint_states'][0]['node'] == '/g2/telemetry'
        for record in self.statuses + self.healths:
            assert record.get('source') == 'gazebo', record
        self.details['ros_graph'] = {'nodes': graph, 'controllers': controllers, 'publishers': endpoints,
                                     'actions': actions, 'trigger_type': services['/g2/say_hello']}

    def simulator_scene(self, world):
        assert re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', world), 'invalid world name'
        help_text = self.command(['ign', 'service', '--help'])
        for flag in ('--reqtype', '--reptype', '--timeout', '--req'):
            assert flag in help_text, 'installed ign service CLI missing ' + flag
        listing = self.command(['ign', 'service', '-l']).split()
        inspected = {}

        def read(suffix, expected):
            service = '/world/' + world + '/' + suffix
            assert service in listing, ('read-only world service missing', service)
            if service not in inspected:
                info = self.command(['ign', 'service', '-i', '-s', service])
                request = re.search(r'(?:ignition|gz)\.msgs\.Empty', info)
                response = re.search(r'(?:ignition|gz)\.msgs\.' + expected + r'\b', info)
                assert request and response, ('installed read-only service types differ', service, info)
                inspected[service] = (request.group(), response.group())
            request_type, response_type = inspected[service]
            return self.command(['ign', 'service', '-s', service, '--reqtype', request_type,
                '--reptype', response_type, '--timeout', '5000', '--req', ''], 8.)

        scene_text = read('scene/info', 'Scene')
        scene = protobuf_top_fields(scene_text)
        g2_models = [protobuf_top_fields(model) for model in scene.get('model', [])
                     if protobuf_top_fields(model).get('name') == ['"g2"']]
        assert len(g2_models) == 1, ('Gazebo scene must contain exactly one G2 model entity', len(g2_models))
        model = g2_models[0]
        # SceneBroadcaster does not necessarily populate Model.is_static. A
        # missing proto3 scalar cannot prove that the entity is dynamic.
        reported_static = model.get('is_static')
        assert reported_static != ['true'], 'scene explicitly reports an entirely static G2'
        entity_id = int(model.get('id', ['0'])[0])
        assert entity_id > 0, 'G2 model entity has no simulator ID'
        model_body = next(body for body in scene['model']
                          if protobuf_top_fields(body).get('name') == ['"g2"'])
        installed_model = Path('/opt/g2-model/g2.urdf')
        urdf = ET.parse(installed_model).getroot()
        expected_meshes = {Path(item.get('filename')).name
                           for item in urdf.findall('./link/visual/geometry/mesh')}
        assert expected_meshes, 'model input contains no visual meshes'
        scene_meshes = {Path(value).name for value in re.findall(r'"([^"\n]*\.obj)"', model_body)}
        missing = sorted(expected_meshes - scene_meshes)
        assert not missing, ('G2 scene is missing model visual assets', missing)

        snapshots = []
        for _ in range(2):
            state = protobuf_top_fields(read('state', 'SerializedStepMap'))
            assert len(state.get('stats', [])) == 1, 'state service returned no WorldStatistics'
            stats = protobuf_top_fields(state['stats'][0])
            assert stats.get('paused', ['false']) == ['false'], 'simulator world is paused'
            stamp = protobuf_top_fields(stats.get('sim_time', [''])[0])
            ns = int(stamp.get('sec', ['0'])[0])*10**9 + int(stamp.get('nsec', ['0'])[0])
            snapshots.append({'iterations': int(stats.get('iterations', ['0'])[0]),
                              'simulation_time_ns': ns})
        assert snapshots[1]['iterations'] > snapshots[0]['iterations'] > 0, snapshots
        assert snapshots[1]['simulation_time_ns'] > snapshots[0]['simulation_time_ns'] > 0, snapshots
        self.details['simulator_scene'] = {'world': world, 'entity_name': 'g2', 'entity_id': entity_id,
            'scene_static_field': reported_static or 'NOT_REPORTED',
            'matched_visual_mesh_count': len(expected_meshes),
            'visual_mesh_names': sorted(expected_meshes), 'state_snapshots': snapshots,
            'evidence_boundary': 'Simulator entity, visual assets and advancing updates verified; '
                'physical joint movement is independently checked by the motion case.'}
        # CLI inspection intentionally precedes measurement. Drain callbacks past
        # its last independently observed sim stamp, then acquire a new baseline.
        # Otherwise queued samples receive late local callback times and distort
        # wall-rate measurements or overflow the raw subscription history.
        barrier = snapshots[-1]['simulation_time_ns']
        self.wait(lambda: self.clock_ns >= barrier and self.raw and self.telemetry and
                  self.raw[-1]['stamp_ns'] >= barrier and
                  self.telemetry[-1]['stamp_ns'] >= barrier,
                  'fresh ROS samples after simulator inspection', 15.)
        self.details['simulator_scene']['measurement_barrier'] = {
            'simulation_stamp_ns': barrier, 'wall_monotonic_s': time.monotonic(),
            'discarded_pre_measurement_raw_samples': len(self.raw),
            'discarded_pre_measurement_public_samples': len(self.telemetry)}
        self.raw.clear()
        self.telemetry.clear()
        self.ready()

    def baseline(self):
        """Capture fresh, stationary broadcaster state before requesting motion."""
        self.ready()
        recent = list(self.telemetry)[-6:]
        q0 = positions(recent[-1], self.names)
        assert all(max(abs(a-b) for a,b in zip(positions(s, self.names), q0)) <= .002
                   for s in recent), 'baseline not stable'
        return q0

    def request(self, accepted):
        wall = time.monotonic()
        response = self.await_future(self.trigger.call_async(Trigger.Request()), 'Trigger response', 5.)
        assert response.success is accepted, response.message
        data = json.loads(response.message)
        assert data['source'] == 'gazebo'
        if accepted:
            assert data['run_id'] and data['run_id'] not in self.run_ids
            self.run_ids.append(data['run_id'])
            self.wait(lambda: any(s.get('run_id') == data['run_id'] and s.get('state') == 'RUNNING'
                                  for s in self.statuses), 'matching RUNNING status', 5.)
        return data, wall

    def disabled(self):
        assert self.config['enable_motion'] is False, 'disabled test needs default motion-disabled launch'
        q0 = self.baseline()
        _, requested = self.request(False)
        start_ns = self.telemetry[-1]['stamp_ns']
        self.wait(lambda: self.telemetry[-1]['stamp_ns'] >= start_ns + 1_000_000_000,
                  'one simulated second after disabled request', 30.)
        samples = [s for s in self.telemetry if s['wall_monotonic_s'] >= requested]
        assert len(samples) >= 8
        assert max(abs(a-b) for s in samples for a,b in zip(positions(s, self.names), q0)) <= .002
        assert not any(s.get('state') == 'RUNNING' for s in self.statuses
                       if s['probe_wall_monotonic_s'] >= requested)
        self.details['disabled'] = {'samples': len(samples), 'baseline': q0, 'request_rejected': True}

    def motion(self):
        """Verify accepted service, physical excursion, stable return, and result."""
        assert self.config['enable_motion'] is True, 'motion test requires explicit enable_motion=true'
        assert abs(abs(self.config['displacement']) - .05) < 1e-10, 'acceptance profile must use 0.05 rad'
        q0 = self.baseline()
        request, started = self.request(True)
        run_id = request['run_id']
        duplicate = self.await_future(self.trigger.call_async(Trigger.Request()), 'duplicate request response', 5.)
        assert duplicate.success is False, 'duplicate accepted during running action'
        self.wait(lambda: any(s.get('run_id') == run_id and s.get('state') in ('SUCCEEDED', 'FAILED')
                              for s in self.statuses), 'matching terminal action status', 140.)
        terminal = next(s for s in self.statuses if s.get('run_id') == run_id and
                        s.get('state') in ('SUCCEEDED', 'FAILED'))
        assert terminal['state'] == 'SUCCEEDED', terminal
        assert terminal['controller_result']['status'] == 4, terminal
        assert terminal['controller_result']['error_code'] == 0, terminal
        commanded = terminal['command_trajectory']
        assert commanded['joint_names'] == self.names and commanded['header_stamp_ns'] == 0
        points = commanded['points']
        assert len(points) == 3 and [p['time_from_start_ns'] for p in points] == [
            0, round(self.config['duration'] * 0.5e9), round(self.config['duration'] * 1e9)]
        assert points[0]['position_rad'] == points[2]['position_rad']
        selected = self.names.index(self.config['target_joint'])
        for index in range(len(self.names)):
            change = points[1]['position_rad'][index] - points[0]['position_rad'][index]
            expected = self.config['displacement'] if index == selected else 0.
            assert abs(change - expected) < 1e-12, 'submitted command vector mismatch'
        for point in points:
            assert all(point[field] == [0.] * len(self.names) for field in
                       ('velocity_rad_s', 'acceleration_rad_s2')), 'waypoint derivatives must be zero'
        assert max(abs(a-b) for a,b in zip(points[0]['position_rad'], q0)) <= .002
        data = [s for s in self.telemetry if started <= s['wall_monotonic_s'] <= terminal['probe_wall_monotonic_s']]
        assert len(data) >= 30, 'not enough independent telemetry during trajectory'
        for value in data:
            validate_sample(value, self.names)
        stamps = [s['stamp_ns'] for s in data]
        assert all(a < b for a,b in zip(stamps, stamps[1:])), 'duplicate or reversed public timestamps'
        target = self.names.index(self.config['target_joint'])
        direction = math.copysign(1, self.config['displacement'])
        offset = [(positions(s, self.names)[target] - q0[target]) * direction for s in data]
        peak = max(offset)
        assert .04 <= peak <= .06, ('excursion', peak)
        assert min(offset) >= -.002, ('wrong direction', min(offset))
        other_error = max((abs(v-q0[i]) for s in data for i,v in enumerate(positions(s, self.names)) if i != target), default=0.)
        assert other_error <= .002, ('non-target movement', other_error)
        final_error = max(abs(a-b) for a,b in zip(positions(data[-1], self.names), q0))
        assert final_error <= .002, ('did not return', final_error)
        sim_duration = (stamps[-1] - stamps[0]) / 1e9
        wall_duration = data[-1]['wall_monotonic_s'] - data[0]['wall_monotonic_s']
        sim_hz = (len(data)-1) / sim_duration
        assert 8 <= sim_hz <= 11, ('simulation sample frequency', sim_hz)
        assert sim_duration >= self.config['duration'] - .5, ('trajectory too short', sim_duration)
        # Check observed smoothness, not just endpoint strings. The factor 1.5
        # allows discretized simulator/controller sampling while rejecting jumps.
        half = self.config['duration'] / 2.
        speed_bound = 1.5 * 1.875 * abs(self.config['displacement']) / half
        acceleration_bound = 1.5 * 10. / math.sqrt(3.) * abs(self.config['displacement']) / half**2
        velocities = [value['velocity'][value['names'].index(self.config['target_joint'])] for value in data]
        intervals = [(b-a)/1e9 for a,b in zip(stamps, stamps[1:])]
        measured_speed = max(abs(v) for v in velocities)
        position_speed = max(abs(b-a)/dt for a,b,dt in zip(offset, offset[1:], intervals))
        measured_acceleration = max(abs(b-a)/dt for a,b,dt in zip(velocities, velocities[1:], intervals))
        assert max(measured_speed, position_speed) <= speed_bound, ('observed speed/jump', measured_speed, position_speed, speed_bound)
        assert measured_acceleration <= acceleration_bound, ('observed acceleration', measured_acceleration, acceleration_bound)
        self.details['smoothness'] = {'measured_peak_speed_rad_s': measured_speed,
            'position_difference_peak_speed_rad_s': position_speed,
            'measured_peak_acceleration_rad_s2': measured_acceleration,
            'speed_bound_rad_s': speed_bound, 'acceleration_bound_rad_s2': acceleration_bound}
        self.details['command_trajectory'] = commanded
        self.details['motion'] = {'run_id': run_id, 'samples': len(data), 'baseline': q0,
            'target_joint': self.config['target_joint'], 'requested_delta_rad': self.config['displacement'],
            'peak_signed_excursion_rad': peak, 'final_max_error_rad': final_error,
            'non_target_max_error_rad': other_error, 'simulation_duration_s': sim_duration,
            'wall_duration_s': wall_duration, 'simulation_hz': sim_hz,
            'wall_hz': (len(data)-1)/wall_duration, 'real_time_factor': sim_duration/wall_duration,
            'terminal': terminal, 'started_wall_monotonic_s': started}

    def invalid_joint_rejection(self):
        q0 = self.baseline()
        started = time.monotonic()
        goal = FollowJointTrajectory.Goal()
        invalid_name = 'project_test_invalid_joint_not_in_g2'
        assert invalid_name not in self.names
        goal.trajectory.joint_names = [invalid_name]
        point = JointTrajectoryPoint()
        point.positions = [0.0]
        point.time_from_start.sec = 1
        goal.trajectory.points = [point]
        handle = self.await_future(self.action.send_goal_async(goal), 'invalid-joint goal response', 8.)
        result = {'goal_accepted': handle.accepted, 'joint_name': invalid_name}
        if handle.accepted:
            response = self.await_future(handle.get_result_async(), 'invalid-joint rejection result', 8.)
            result.update(status=response.status, error_code=response.result.error_code,
                          error_string=response.result.error_string)
            assert response.status == GoalStatus.STATUS_ABORTED, result
            assert response.result.error_code == FollowJointTrajectory.Result.INVALID_JOINTS, result
        start_stamp = self.telemetry[-1]['stamp_ns']
        self.wait(lambda: self.telemetry[-1]['stamp_ns'] >= start_stamp + 500_000_000,
                  'feedback after invalid joint rejection', 20.)
        observed = [value for value in self.telemetry if value['wall_monotonic_s'] >= started]
        assert observed
        assert max(abs(a-b) for value in observed for a,b in zip(positions(value, self.names), q0)) <= .002
        result['no_motion_max_error_rad'] = max(abs(a-b) for value in observed
            for a,b in zip(positions(value, self.names), q0))
        self.details['invalid_joint_rejection'] = result

    def cancel_active_action(self):
        assert self.config['enable_motion'] is True
        self.baseline()
        request, started = self.request(True)
        run_id = request['run_id']

        def live_goals():
            if not self.action_statuses or self.action_statuses[-1]['wall_monotonic_s'] < started:
                return []
            return [g for g in self.action_statuses[-1]['goals']
                    if g['status'] in (GoalStatus.STATUS_ACCEPTED, GoalStatus.STATUS_EXECUTING)]

        self.wait(lambda: bool(live_goals()), 'actual controller active goal UUID', 8.)
        self.wait(lambda: any(s.get('run_id') == run_id and s.get('state') == 'RUNNING' and
                              s.get('observed_excursion_rad', 0.) > .002 for s in self.statuses),
                  'measured motion before standard action cancel', 40.)
        active = live_goals()
        assert len(active) == 1, 'expected one active goal in isolated controller server'
        goal_id = active[0]['id']
        client = self.create_client(CancelGoal, self.config['sim_action'] + '/_action/cancel_goal')
        try:
            self.wait(client.service_is_ready, 'standard action cancellation service', 5.)
            cancellation = CancelGoal.Request()
            # Nonzero UUID plus ZERO timestamp requests this goal only, not all
            # older goals (CancelGoal.srv defines the timestamp selection rule).
            cancellation.goal_info.goal_id.uuid = goal_id
            response = self.await_future(client.call_async(cancellation), 'specific goal cancellation response', 8.)
            assert response.return_code == CancelGoal.Response.ERROR_NONE, response
            assert goal_id in [[int(value) for value in g.goal_id.uuid] for g in response.goals_canceling]
            self.wait(lambda: any(s.get('run_id') == run_id and s.get('state') == 'FAILED' and
                                  not s.get('pending_controller_goal') for s in self.statuses),
                      'app observes canceled goal as FAILED with terminal controller result', 15.)
            terminal = next(s for s in self.statuses if s.get('run_id') == run_id and
                            s.get('state') == 'FAILED' and not s.get('pending_controller_goal'))
            assert terminal['controller_result']['status'] == GoalStatus.STATUS_CANCELED, terminal
            assert not any(s.get('run_id') == run_id and s.get('state') == 'SUCCEEDED' for s in self.statuses)
            self.details['action_cancel'] = {'run_id': run_id, 'goal_uuid': goal_id,
                                            'return_code': response.return_code, 'terminal': terminal}
        finally:
            self.destroy_client(client)

    def inactive_controller_rejection(self):
        manager_name = self.config['sim_controller_manager']
        controller = self.config['sim_controller']
        client = self.create_client(SwitchController, manager_name + '/switch_controller')
        fields = SwitchController.Request.get_fields_and_field_types()
        required = {'activate_controllers', 'deactivate_controllers', 'strictness', 'activate_asap', 'timeout'}
        assert required.issubset(fields), ('installed Humble SwitchController fields incompatible', fields)
        self.details['switch_controller_type_fields'] = fields
        changed = False

        def switch(activate):
            request = SwitchController.Request()
            request.activate_controllers = [controller] if activate else []
            request.deactivate_controllers = [] if activate else [controller]
            request.strictness = SwitchController.Request.STRICT
            request.activate_asap = True
            request.timeout.sec = 3
            result = self.await_future(client.call_async(request), 'controller switch response', 8.)
            assert result.ok, ('controller switch rejected', activate)

        try:
            self.wait(client.service_is_ready, 'controller switch service', 8.)
            changed = True
            switch(False)
            self.wait(lambda: self.statuses and not self.statuses[-1].get('healthy') and
                      'controller' in self.statuses[-1].get('health_reason', ''),
                      'app observes controller inactivity', 8.)
            request, started = self.request(False)
            assert 'controller' in request['reason'], request
            controller_list = self.await_future(self.manager.call_async(ListControllers.Request()),
                                                 'inactive controller state confirmation', 5.)
            actual = [c.state for c in controller_list.controller if c.name == controller]
            assert actual == ['inactive'], actual
            self.details['inactive_controller_rejection'] = {'controller': controller,
                'observed_state': 'inactive', 'request_rejected': True, 'reason': request['reason']}
        finally:
            try:
                if changed:
                    switch(True)
                    self.wait(lambda: self.statuses[-1].get('healthy'), 'controller active recovery', 10.)
                    self.details.setdefault('inactive_controller_rejection', {})['reactivated'] = True
            finally:
                self.destroy_client(client)

    def interrupt_application(self):
        from ament_index_python.packages import get_package_prefix
        prefix = Path(get_package_prefix('agibot_g2_demo')).resolve()
        entrypoint = prefix / 'lib/agibot_g2_demo/sayHello'
        identity_root = Path(os.environ.get('EVIDENCE_DIR', str(self.evidence.parent)))
        candidates = []
        for path in identity_root.glob('identity-sayHello-*.json'):
            identity = json.loads(path.read_text())
            pid = identity.get('pid')
            if (type(pid) is not int or pid <= 1 or identity.get('node_name') != 'sayHello' or
                    identity.get('namespace') != '/g2' or identity.get('backend') != 'gazebo'):
                continue
            process = Path('/proc') / str(pid)
            if not process.exists():
                continue
            argv = [part.decode() for part in (process/'cmdline').read_bytes().split(b'\0') if part]
            if str(entrypoint) not in argv:
                continue
            executable = os.readlink(process/'exe')
            assert 'python' in Path(executable).name.lower(), executable
            assert Path(identity['module_loaded_file']).is_relative_to(prefix), identity
            started_ticks = (process/'stat').read_text().rsplit(')', 1)[1].split()[19]
            candidates.append((pid, process, argv, executable, started_ticks))
        assert len(candidates) == 1, ('expected one identified installed Gazebo sayHello process', len(candidates))
        pid, process, argv, executable, started_ticks = candidates[0]
        self.baseline()
        request, _ = self.request(True)
        run_id = request['run_id']
        self.wait(lambda: any(s.get('run_id') == run_id and s.get('state') == 'RUNNING' and
                              s.get('observed_excursion_rad', 0.) > .005 for s in self.statuses),
                  'measured motion before SIGTERM', 50.)
        assert (process/'stat').read_text().rsplit(')', 1)[1].split()[19] == started_ticks, 'process identity changed'
        sent = time.monotonic()
        os.kill(pid, signal.SIGTERM)
        self.wait(lambda: not process.exists() and ('sayHello', '/g2') not in self.get_node_names_and_namespaces(),
                  'SIGTERM process reaped and application removed from ROS graph', 15.)
        assert not any(s.get('run_id') == run_id and s.get('state') == 'SUCCEEDED' for s in self.statuses)
        self.details['interrupt'] = {'run_id': run_id, 'signal': 'SIGTERM', 'pid': pid,
            'verified_command_line': argv, 'python_executable': executable,
            'cleanup_wall_seconds': time.monotonic() - sent, 'process_reaped': True,
            'node_removed': True, 'no_false_success': True}

    def correlate(self):
        """Match raw and public samples by source stamp and joint-name mapping."""
        # Public positions must be exactly a reordered original broadcaster sample.
        # DDS subscriptions have independent callback queues: the final public
        # callback can wake the preceding wait before its source callback runs.
        # Freeze the public boundary, then drain only until those exact source
        # stamps arrive. New public samples must not move this boundary forever.
        raw = {s['stamp_ns']: s for s in self.raw}
        public = [s for s in self.telemetry if raw and s['stamp_ns'] >= min(raw)]
        assert len(public) >= 6
        expected_stamps = {s['stamp_ns'] for s in public}
        initially_missing = sorted(expected_stamps - raw.keys())
        started = time.monotonic()
        correlation = {'public_snapshot_samples': len(public),
            'public_snapshot_last_stamp_ns': public[-1]['stamp_ns'],
            'initially_missing_source_stamps_ns': initially_missing,
            'source_topic': self.config['sim_joint_topic']}
        self.details['source_correlation'] = correlation

        def source_callbacks_complete():
            raw.update((s['stamp_ns'], s) for s in self.raw)
            return expected_stamps <= raw.keys()

        try:
            if initially_missing:
                self.wait(source_callbacks_complete,
                    'original simulator callbacks for fixed public snapshot: '+str(initially_missing), 3.)
        finally:
            correlation.update(source_callback_wait_wall_seconds=time.monotonic()-started,
                missing_source_stamps_ns=sorted(expected_stamps - raw.keys()))
        for value in public:
            validate_sample(value, self.names)
            assert value['stamp_ns'] in raw, ('no original simulator sample', value['stamp_ns'])
            source = raw[value['stamp_ns']]
            assert positions(value, self.names) == positions(source, self.names), 'public positions are not source observations'
            assert value['frame_id'] == source['frame_id']
            for field in ('velocity', 'effort'):
                if value[field]:
                    expected = [source[field][source['names'].index(n)] for n in value['names']]
                    assert value[field] == expected, field + ' values changed'
        correlation.update({'matched_public_samples': len(public),
            'raw_samples': len(self.raw), 'position_comparison': 'exact by name and source stamp',
            'source_topic': self.config['sim_joint_topic']})

    def command(self, args, timeout=8.):
        started = utc()
        completed = subprocess.run(args, capture_output=True, text=True,
                                   timeout=min(timeout, max(.1, self.deadline-time.monotonic())))
        record = {'command': args, 'started_utc': started, 'exit_code': completed.returncode,
                  'stdout': completed.stdout, 'stderr': completed.stderr}
        self.commands.append(record)
        assert completed.returncode == 0, record
        return completed.stdout + completed.stderr

    def world_control(self, world):
        assert re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', world), 'invalid world name'
        help_text = self.command(['ign', 'service', '--help'])
        for flag in ('--reqtype', '--reptype', '--timeout', '--req'):
            assert flag in help_text, 'installed ign service CLI missing ' + flag
        service = '/world/' + world + '/control'
        listing = self.command(['ign', 'service', '-l'])
        assert service in listing.split(), ('world control service unavailable', service)
        info = self.command(['ign', 'service', '-i', '-s', service])
        request = re.search(r'(?:ignition|gz)\.msgs\.WorldControl', info)
        response = re.search(r'(?:ignition|gz)\.msgs\.Boolean', info)
        assert request and response, ('unsupported world control types', info)

        def control(body):
            result = self.command(['ign', 'service', '-s', service, '--reqtype', request.group(),
                '--reptype', response.group(), '--timeout', '5000', '--req', body])
            assert re.search(r'data:\s*true', result), ('world control rejected', result)
        return control

    def pause_reset(self, world):
        """Prove pause emits no new measurement and reset invalidates the old epoch."""
        assert self.config['enable_motion'] is True
        self.baseline()
        control = self.world_control(world)
        first, started = self.request(True)
        self.wait(lambda: any(s.get('run_id') == first['run_id'] and
                              s.get('observed_excursion_rad', 0.) > .005 for s in self.statuses),
                  'movement before simulator pause', 50.)
        paused = False
        try:
            control('pause: true'); paused = True
            self.wait(lambda: self.statuses[-1].get('run_id') == first['run_id'] and
                self.statuses[-1].get('state') == 'FAILED' and self.healths[-1].get('status') == 'STALE',
                'paused world failure and stale telemetry', 15.)
            frozen_stamp = self.telemetry[-1]['stamp_ns']; frozen_count = len(self.telemetry)
            self.observe_wall_interval(.7)
            assert self.telemetry[-1]['stamp_ns'] == frozen_stamp and len(self.telemetry) == frozen_count
            assert not any(s.get('run_id') == first['run_id'] and s.get('state') == 'SUCCEEDED' for s in self.statuses)
            self.request(False)
        finally:
            if paused:
                control('pause: false')
        self.wait(lambda: self.healths[-1].get('status') == 'HEALTHY' and
                  not self.statuses[-1].get('pending_controller_goal'),
                  'resumed feedback and canceled old action terminal', 30.)
        self.ready()
        second, _ = self.request(True)
        resets = self.clock_resets
        epoch = self.statuses[-1]['clock_epoch']
        control('reset: {all: true}')
        self.wait(lambda: self.clock_resets > resets and any(s.get('run_id') == second['run_id'] and
                    s.get('state') == 'FAILED' and s.get('clock_epoch', -1) > epoch for s in self.statuses),
                  'world reset invalidates active run and changes clock epoch', 30.)
        self.wait(lambda: self.healths[-1].get('status') == 'HEALTHY', 'valid post-reset feedback', 30.)
        assert not any(s.get('run_id') == second['run_id'] and s.get('state') == 'SUCCEEDED' for s in self.statuses)
        self.details['pause_reset'] = {'pause_run_id': first['run_id'], 'reset_run_id': second['run_id'],
            'paused_public_stamp_ns': frozen_stamp, 'no_public_updates_while_paused': True,
            'clock_resets_observed': self.clock_resets - resets,
            'post_reset_clock_epoch': self.statuses[-1].get('clock_epoch')}

    def save(self, outcome, error, started):
        self.evidence.mkdir(parents=True, exist_ok=True)
        for filename, value in [('raw_joint_states.json', list(self.raw)),
                                ('joint_states.json', list(self.telemetry)),
                                ('hello_status.json', self.statuses), ('telemetry_health.json', self.healths),
                                ('action_status.json', self.action_statuses),
                                ('commands.json', self.commands)]:
            (self.evidence/filename).write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')
        command_trace = self.details.get('command_trajectory')
        if command_trace:
            with (self.evidence/'command_waypoints.csv').open('w', newline='') as stream:
                writer = csv.writer(stream)
                writer.writerow(['relative_simulation_time_ns'] + [n + '_position_rad' for n in command_trace['joint_names']])
                for point in command_trace['points']:
                    writer.writerow([point['time_from_start_ns']] + point['position_rad'])
        with (self.evidence/'joint_states.csv').open('w', newline='') as stream:
            writer = csv.writer(stream)
            names = getattr(self, 'names', [])
            writer.writerow(['wall_monotonic_s', 'simulation_stamp_ns'] + [n + '_position_rad' for n in names])
            for value in self.telemetry:
                mapped = dict(zip(value['names'], value['position']))
                writer.writerow([value['wall_monotonic_s'], value['stamp_ns']] +
                                [mapped.get(name, '') for name in names])
        summary = {'status': outcome, 'started_utc': started, 'finished_utc': utc(),
            'execution_location': 'probe process inside caller simulation environment',
            'python': sys.version, 'interpreter': sys.executable, 'error': error,
            'tests': len(self.cases), 'passed': sum(c['status']=='PASS' for c in self.cases),
            'failed': sum(c['status']=='FAIL' for c in self.cases), 'skipped': 0,
            'cases': self.cases, 'run_ids': self.run_ids, 'details': self.details}
        (self.evidence/'result.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
        suite = ET.Element('testsuite', name='g2_real_gazebo_ros_probe', tests=str(len(self.cases)),
                          failures=str(summary['failed']), skipped='0')
        for case in self.cases:
            item = ET.SubElement(suite, 'testcase', name=case['name'], time=str(case['seconds']))
            if case['status'] == 'FAIL':
                ET.SubElement(item, 'failure', message=case['error']).text = case['error']
        ET.ElementTree(suite).write(self.evidence/'junit.xml', encoding='utf-8', xml_declaration=True)
        print(json.dumps(summary, indent=2, allow_nan=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['disabled', 'motion', 'pause-reset', 'action-faults', 'interrupt'], default='motion')
    parser.add_argument('--world', default='g2_demo')
    parser.add_argument('--timeout', type=float, default=180.)
    parser.add_argument('--evidence-dir', default=os.environ.get('EVIDENCE_DIR'))
    args = parser.parse_args()
    if not args.evidence_dir:
        parser.error('--evidence-dir or EVIDENCE_DIR is required')
    if not math.isfinite(args.timeout) or not 10 <= args.timeout <= 180:
        parser.error('timeout must be finite between 10 and 180 wall seconds')
    started = utc(); probe = None; outcome = 'FAIL'; error = ''
    rclpy.init()
    try:
        probe = Probe(args.timeout, Path(args.evidence_dir))
        probe.case('installed_application_parameters', probe.configure)
        probe.case('simulation_readiness', probe.ready)
        probe.case('controller_graph_and_source_ownership', probe.graph)
        probe.case('gazebo_G2_entity_assets_and_advancing_world', lambda: probe.simulator_scene(args.world))
        if args.mode == 'motion':
            probe.case('motion_action_and_independent_feedback', probe.motion)
        elif args.mode == 'disabled':
            probe.case('default_motion_disabled', probe.disabled)
        elif args.mode == 'interrupt':
            probe.case('SIGTERM_during_observed_simulation_motion', probe.interrupt_application)
        elif args.mode == 'action-faults':
            probe.case('real_controller_invalid_joint_rejection', probe.invalid_joint_rejection)
            probe.case('standard_action_cancel_reports_failure', probe.cancel_active_action)
            probe.case('inactive_controller_rejects_application_request', probe.inactive_controller_rejection)
        else:
            probe.case('pause_reset_no_fake_updates_or_old_success', lambda: probe.pause_reset(args.world))
        if args.mode in ('disabled', 'motion'):
            probe.case('source_stamp_and_measurement_correlation', probe.correlate)
        outcome = 'PASS'
    except BaseException as exc:
        error = type(exc).__name__ + ': ' + str(exc)
        traceback.print_exc()
    finally:
        if probe is not None:
            try:
                probe.save(outcome, error, started)
            finally:
                if probe.action is not None:
                    probe.action.destroy()
                probe.destroy_node()
        rclpy.try_shutdown()
    return 0 if outcome == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
