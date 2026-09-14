"""Simulation control-flow tests; these are not Gazebo execution evidence."""
from dataclasses import replace
import math

import pytest

from agibot_g2_demo.simulation import (
    SimConfig, SimFeedback, SimRun, ordered_sample, trajectory_points,
)

pytestmark = pytest.mark.unit


def config(**changes):
    # Explicit project test joints, never passed off as model or vendor symbols.
    return replace(SimConfig(('test_arm_a', 'test_arm_b'), (-1., -1.), (1., 1.),
                             (1., 1.), 'test_arm_a'), **changes).validate()


def sample(state, seconds, wall, positions=(0.2, -0.3), velocities=(0., 0.)):
    ns = round(seconds * 1e9)
    state.clock(ns, wall)
    return state.observe(ns, wall, positions, velocities)


def ready(c=None):
    state = SimFeedback(c or config())
    sample(state, 1., 10.)
    sample(state, 1.1, 10.1)
    assert not state.reason(10.1)
    return state


@pytest.mark.parametrize('delta', [.05, -.05])
def test_nonzero_baseline_full_vector_quintic_endpoints(delta):
    c = config(delta=delta)
    points = trajectory_points(c, [.2, -.3])
    assert [p[0] for p in points] == [0., 3., 6.]
    assert points[1][1] == pytest.approx([.2 + delta, -.3])
    assert points[0][1] == points[-1][1] == [.2, -.3]
    assert all(p[2] == p[3] == [0., 0.] for p in points)
    assert all(p[1][1] == -.3 for p in points)


@pytest.mark.parametrize('change', [
    {'names': ()}, {'names': ('a', 'a')}, {'target': 'unknown'},
    {'lower': (-1.,)}, {'upper': (math.inf, 1.)},
    {'velocity_limits': (0., 1.)}, {'lower': (2., -1.)},
    {'delta': math.nan}, {'delta': math.inf}, {'delta': 0.}, {'delta': .11},
    {'duration': -.1}, {'duration': .1}, {'duration': math.nan},
    {'position_tolerance': .02}, {'wall_budget': 5.}, {'pause_timeout': 0.},
])
def test_bad_model_or_motion_configuration_rejected(change):
    with pytest.raises(ValueError):
        config(**change)


@pytest.mark.parametrize('q', [[.99, -.3], [math.nan, -.3], [0.], [2., 0.]])
def test_outbound_limit_or_invalid_baseline_rejected(q):
    with pytest.raises(ValueError):
        trajectory_points(config(), q)


def test_joint_mapping_and_missing_optional_effort():
    c = config()
    values = ordered_sample(['test_arm_b', 'test_arm_a'], [-.3, .2], [0., 0.],
                            [math.nan, math.nan], c)
    assert values == ([.2, -.3], [0., 0.], [])
    with pytest.raises(ValueError, match='non-finite'):
        ordered_sample(c.names, [.2, -.3], [0., 0.], [math.nan, .1], c)
    with pytest.raises(ValueError, match='non-finite'):
        ordered_sample(c.names, [.2, -.3], [0., 0.], [math.nan, math.nan], c,
                       ('position', 'velocity', 'effort'))


@pytest.mark.parametrize('names,q,v', [
    (['test_arm_a', 'unknown'], [.2, -.3], [0., 0.]),
    (['test_arm_a', 'test_arm_a'], [.2, -.3], [0., 0.]),
    (['test_arm_a', 'test_arm_b'], [math.nan, 0.], [0., 0.]),
    (['test_arm_a', 'test_arm_b'], [math.inf, 0.], [0., 0.]),
    (['test_arm_a', 'test_arm_b'], [0.], [0., 0.]),
    (['test_arm_a', 'test_arm_b'], [2., 0.], [0., 0.]),
    (['test_arm_a', 'test_arm_b'], [0., 0.], [0.]),
])
def test_corrupt_observation_is_rejected(names, q, v):
    with pytest.raises(ValueError):
        ordered_sample(names, q, v, [], config())


def test_clock_pause_repeat_source_and_new_reset_epoch():
    f = ready()
    assert 'paused' in f.reason(14.)
    assert not f.observe(f.stamp_ns, 10.2, [.2, -.3], [0., 0.])
    assert 'did not advance' in f.reason(10.2)
    old_epoch = f.epoch
    assert f.clock(0, 10.3)
    assert f.epoch == old_epoch + 1 and f.positions is None
    sample(f, .1, 10.4)
    assert not f.reason(10.4)


def test_new_stamp_without_advancing_clock_is_not_healthy_forever():
    f = ready()
    assert not f.observe(9_000_000_000, 10.2, [.2, -.3], [0., 0.])
    assert 'clock window' in f.reason(10.2)


@pytest.mark.parametrize('delta', [.05, -.05])
def test_success_needs_action_and_new_independent_excursion_return_stability(delta):
    c = config(delta=delta)
    f = ready(c)
    run = SimRun(c)
    run.begin(f, 10.1)
    with pytest.raises(ValueError, match='already running'):
        run.begin(f, 10.1)
    sample(f, 4.1, 11., [.2 + delta, -.3]); run.update(f, 11.)
    sample(f, 7.1, 12.); run.update(f, 12.)
    assert run.state == 'RUNNING'
    run.result(True, '', f)
    run.update(f, 12.)
    assert run.state == 'RUNNING'
    sample(f, 7.2, 12.1); run.update(f, 12.1)
    sample(f, 7.5, 12.2); run.update(f, 12.2)
    assert run.state == 'SUCCEEDED'
    first_id = run.run_id
    run.begin(f, 12.2)
    assert run.run_id != first_id and not run.result_ok and run.peak == 0.
    assert run.state == 'RUNNING'


def test_controller_success_without_motion_does_not_succeed():
    f = ready(); run = SimRun(f.config); run.begin(f, 10.1)
    run.result(True, '', f)
    for t in (7.2, 7.5, 8.):
        sample(f, t, 12.); run.update(f, 12.)
    assert run.state == 'RUNNING' and run.peak == 0.


@pytest.mark.parametrize('fault', ['pause', 'reset', 'budget', 'wrong_direction', 'other_joint', 'overshoot', 'abort'])
def test_faults_cannot_report_success(fault):
    f = ready(); run = SimRun(f.config); run.begin(f, 10.1)
    if fault == 'pause':
        run.update(f, 14.)
    elif fault == 'reset':
        f.clock(0, 10.2); run.update(f, 10.2)
    elif fault == 'budget':
        sample(f, 1.2, 200.); run.update(f, 200.)
    elif fault == 'abort':
        run.result(False, 'controller aborted', f)
    else:
        q = {'wrong_direction': [.19, -.3], 'other_joint': [.22, -.2], 'overshoot': [.27, -.3]}[fault]
        sample(f, 2., 10.2, q); run.update(f, 10.2)
    assert run.state == 'FAILED'
    run.result(True, 'late success', f)
    assert run.state == 'FAILED'


def test_motion_requires_stationary_measured_start():
    f = ready(); run = SimRun(f.config)
    sample(f, 1.2, 10.2, velocities=(.1, 0.))
    with pytest.raises(ValueError, match='near-zero velocity'):
        run.begin(f, 10.2)
    assert run.state == 'IDLE' and run.run_id == ''
