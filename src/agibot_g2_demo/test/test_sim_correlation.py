"""Executor-order fixtures for the actual correlation method; no ROS simulation."""
import ast
from collections import deque
import math
from pathlib import Path
import time
from types import MethodType, SimpleNamespace

import pytest


SOURCE = Path(__file__).resolve().parents[3]/'scripts/verify_sim.py'


def measurement(stamp, position=.1):
    return {'stamp_ns': stamp, 'names': ['joint'], 'position': [position],
            'velocity': [0.], 'effort': [0.], 'frame_id': 'world'}


def probe(spin):
    tree = ast.parse(SOURCE.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Probe')
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name in ('validate_sample', 'positions')]
    functions += [n for n in cls.body if isinstance(n, ast.FunctionDef)
                  and n.name in ('wait', 'correlate')]
    scope = {'math': math, 'time': time, 'rclpy': SimpleNamespace(spin_once=spin)}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(SOURCE), 'exec'), scope)
    result = SimpleNamespace(raw=deque(measurement(i) for i in range(1, 6)),
        telemetry=deque(measurement(i) for i in range(1, 7)),
        names=['joint'], details={}, config={'sim_joint_topic': '/source'},
        deadline=time.monotonic()+.15, statuses=[], healths=[])
    result.wait = MethodType(scope['wait'], result)
    result.correlate = MethodType(scope['correlate'], result)
    return result


def test_tail_source_callback_is_drained_without_chasing_new_public_samples():
    def spin(node, **kwargs):
        node.raw.append(measurement(6))
        node.telemetry.append(measurement(7))
    node = probe(spin)
    node.correlate()
    receipt = node.details['source_correlation']
    assert receipt['initially_missing_source_stamps_ns'] == [6]
    assert receipt['missing_source_stamps_ns'] == []
    assert receipt['matched_public_samples'] == 6
    assert receipt['public_snapshot_last_stamp_ns'] == 6


def test_already_complete_sources_need_no_executor_wait():
    node = probe(lambda *a, **k: pytest.fail('unnecessary executor wait'))
    node.raw.append(measurement(6))
    node.correlate()
    assert node.details['source_correlation']['initially_missing_source_stamps_ns'] == []


@pytest.mark.parametrize('missing', [3, 6])
def test_real_missing_source_still_fails_at_global_deadline(missing):
    def spin(node, timeout_sec):
        time.sleep(min(.01, timeout_sec))
    node = probe(spin)
    node.raw = deque(measurement(i) for i in range(1, 8) if i != missing)
    started = time.monotonic()
    with pytest.raises(TimeoutError, match='fixed public snapshot'):
        node.correlate()
    assert time.monotonic()-started < .5
    assert node.details['source_correlation']['missing_source_stamps_ns'] == [missing]


def test_delayed_source_with_wrong_position_is_not_accepted():
    node = probe(lambda node, **kw: node.raw.append(measurement(6, .100000001)))
    with pytest.raises(AssertionError, match='positions are not source observations'):
        node.correlate()


def test_delayed_source_with_wrong_velocity_is_not_accepted():
    def spin(node, **kwargs):
        value = measurement(6)
        value['velocity'] = [.000000001]
        node.raw.append(value)
    node = probe(spin)
    with pytest.raises(AssertionError, match='velocity values changed'):
        node.correlate()
