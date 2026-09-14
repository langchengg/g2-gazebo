"""Pure-Python migration of all 29 legacy core gtests, plus Python boundaries.

Each old named behavior remains below; the old eight fault instantiations and
old numeric loops are explicit pytest parameters. All clocks are injected: no
test sleeps, imports ROS, loads an SDK, or communicates with hardware.
"""

import copy
import math
from dataclasses import FrozenInstanceError

import pytest

from agibot_g2_demo.backends.base import Observation
from agibot_g2_demo.backends.mock_backend import MockBackend
from agibot_g2_demo.motion import (
    Config, Engine, MotionState, SourceFreshness, mock_joint_names,
    valid_fault, validate_config, validate_observation,
)

pytestmark = pytest.mark.unit


def enabled(**overrides):
    return Config(enable_motion=True, **overrides)


def valid_observation():
    return Observation(names=mock_joint_names(), positions=[0.1] * 6, sequence=1)


class InputBackend:
    """Independent observed inputs; this is not a fabricated vendor SDK."""

    def __init__(self):
        self.next = valid_observation()
        self.polls = 0
        self.commands = 0
        self.holds = 0
        self.command_error = False
        self.hold_error = False
        self.last_command = []

    def poll(self, now):
        self.polls += 1
        self.next.sample_time = now
        self.next.sequence = self.polls
        return copy.deepcopy(self.next)

    def command_positions(self, positions, now):
        self.commands += 1
        if self.command_error:
            raise RuntimeError("test command rejected")
        self.last_command = list(positions)

    def hold(self, now):
        self.holds += 1
        if self.hold_error:
            raise RuntimeError("test hold rejected")

    def set_fault(self, fault):
        pass


def test_safe_defaults_and_unknown_backend():
    config = Config()
    assert config.enable_motion is False
    assert config.backend == "mock"
    validate_config(config)
    with pytest.raises(ValueError, match="backend must be"):
        Engine(enabled(backend="mystery"))


@pytest.mark.parametrize("field", [
    "duration", "publish_hz", "max_displacement", "max_velocity", "max_acceleration",
    "position_limit", "feedback_timeout", "watchdog_timeout", "motion_timeout",
    "position_tolerance", "velocity_tolerance", "stable_duration", "tracking_time_constant",
])
@pytest.mark.parametrize("bad", [0.0, -1.0, math.inf, math.nan, True, "1.0"])
def test_rejects_every_nonfinite_nonpositive_and_nonnumeric_bound(field, bad):
    with pytest.raises(ValueError, match="finite and positive"):
        Engine(enabled(**{field: bad}))


@pytest.mark.parametrize("bad", [0.0, 0.11, -0.11, math.inf, math.nan, True, "0.05"])
def test_rejects_invalid_displacement(bad):
    with pytest.raises(ValueError, match="displacement"):
        Engine(enabled(displacement=bad))


@pytest.mark.parametrize("overrides", [
    {"target_joint": "g2_joint_unverified"}, {"duration": 0.1}, {"max_velocity": 0.001},
    {"max_acceleration": 0.001}, {"motion_timeout": 4.0}, {"position_tolerance": 0.05},
    {"fault": "unknown"}, {"publish_hz": 51.0}, {"duration": 5e-324},
])
def test_rejects_invalid_motion_and_profile_limits(overrides):
    with pytest.raises(ValueError):
        Engine(enabled(**overrides))


@pytest.mark.parametrize("bad", ["true", 1, 0, None])
def test_motion_enable_requires_an_actual_boolean(bad):
    config = Config(enable_motion=bad)
    with pytest.raises(ValueError, match="boolean"):
        Engine(config)


def test_gdk_selection_fails_without_any_fallback():
    config = enabled(backend="gdk")
    with pytest.raises(RuntimeError, match="no mock fallback"):
        Engine(config)
    fixture = InputBackend()
    with pytest.raises(RuntimeError, match="no mock fallback"):
        Engine(config, fixture)
    assert fixture.polls == fixture.commands == fixture.holds == 0
    with pytest.raises(ValueError, match="backend=mock"):
        MockBackend(config)


@pytest.mark.parametrize("field,value", [
    ("names", []), ("positions", [0.0]), ("names", [""] * 6),
    ("names", ["duplicate"] * 6), ("velocities", [0.0]), ("efforts", [0.0]),
    ("positions", [math.nan] * 6), ("velocities", [math.inf] * 6),
    ("efforts", [math.inf] * 6), ("sample_time", math.nan), ("positions", None),
    ("names", "abcdef"), ("positions", [True] * 6), ("positions", ["0"] * 6),
    ("sequence", -1), ("sequence", True), ("sequence", 0.5),
])
def test_observation_dimensions_names_finite_values_and_types(field, value):
    observation = valid_observation()
    assert validate_observation(observation) == ""
    setattr(observation, field, value)
    assert validate_observation(observation)


def test_unknown_fields_stay_empty_and_observation_defaults_do_not_alias():
    observation = valid_observation()
    assert observation.velocities == observation.efforts == []
    assert validate_observation(observation) == ""
    assert validate_observation(Observation())
    assert validate_observation(None)
    first, second = Observation(), Observation()
    first.positions.append(1.0)
    assert second.positions == []


def test_freshness_separates_source_clock_from_monotonic_receive_clock():
    guard = SourceFreshness(0.5)
    assert not guard.healthy(0.0)
    assert guard.observe(1, 1900000000.0, 1.0)
    assert guard.healthy(1.1)
    assert guard.observe(2, 1900000000.1, 1.2)
    assert guard.healthy(1.6)
    assert not guard.healthy(1.8)
    assert "receive timeout" in guard.reason(1.8)


def test_repeated_old_samples_do_not_renew_source_freshness():
    guard = SourceFreshness(0.5)
    assert guard.observe(1, 1234.0, 0.0)
    receive_time = 0.0
    for index in range(1, 7):
        receive_time = index * 0.1
        assert not guard.observe(1, 1234.0, receive_time)
    # Preserve the repaired C++ test's exact injected instant (6*.1 != .6).
    assert not guard.healthy(receive_time)
    assert "stopped advancing" in guard.reason(receive_time)


def test_both_available_source_markers_must_advance():
    guard = SourceFreshness(0.5)
    assert guard.observe(1, 10.0, 0.0)
    assert not guard.observe(2, 10.0, 0.1)
    assert not guard.observe(1, 11.0, 0.2)
    assert guard.observe(2, 11.0, 0.3)
    assert not guard.observe(1, 12.0, 0.4)
    assert not guard.healthy(0.4)


def test_freshness_rejects_clock_and_marker_failures():
    guard = SourceFreshness(0.5)
    assert guard.observe(1, 10.0, 1.0)
    assert not guard.observe(2, 11.0, 0.9)
    assert not guard.healthy(1.0)
    assert not guard.observe(2, math.nan, 1.1)
    assert not guard.observe(None, 11.0, 1.2)
    assert not guard.observe(-1, 11.0, 1.3)
    unclocked = SourceFreshness(0.5)
    assert unclocked.observe(None, None, 0.0)
    assert "unverified" in unclocked.reason(0.1)
    assert not unclocked.healthy(math.inf)
    zero = SourceFreshness(0.5)
    assert zero.observe(0, 0.0, 0.0)
    assert zero.reason(0.0) == "healthy"


def test_command_and_observation_are_separate_and_effort_is_unknown():
    backend = MockBackend(enabled())
    first = backend.poll(0.0)
    command = first.positions.copy()
    command[0] += 0.05
    backend.command_positions(command, 0.0)
    second = backend.poll(0.02)
    assert first.positions[0] < second.positions[0] < command[0]
    assert second.efforts == []
    assert second.sequence > first.sequence
    assert second.sample_time == 0.02
    assert second.positions[1:] == first.positions[1:]
    backend.hold(0.02)
    assert backend.poll(0.04).positions == second.positions
    for invalid in ([], [math.nan] * 6, [2.0] * 6, [True] * 6, ["0"] * 6):
        with pytest.raises(ValueError):
            backend.command_positions(invalid, 0.04)


def test_startup_never_moves_and_disabled_request_is_rejected():
    engine = Engine(Config())
    engine.tick(0.0)
    initial = engine.observation.positions
    assert any(value != 0.0 for value in initial)
    for index in range(1, 251):
        engine.tick(index * 0.02)
    assert engine.observation.positions == initial
    assert engine.status.state == MotionState.IDLE
    result = engine.request(5.0)
    assert not result.accepted
    assert "enable_motion=false" in result.reason
    engine.shutdown(5.0)


def test_fresh_feedback_is_required_before_any_request():
    engine = Engine(enabled())
    assert not engine.request(0.0).accepted
    engine.tick(0.0)
    for now in (1.0, math.nan, -1.0):
        assert not engine.request(now).accepted
    engine.shutdown(0.0)


def run_round_trip(config):
    engine = Engine(config)
    engine.tick(0.0)
    initial = engine.observation.positions
    target_index = mock_joint_names().index(config.target_joint)
    accepted = engine.request(0.0)
    assert accepted.accepted and accepted.run_id
    assert engine.status.state == MotionState.RUNNING
    duplicate = engine.request(0.0)
    assert not duplicate.accepted and duplicate.run_id == accepted.run_id
    peak = 0.0
    prior_velocity = 0.0
    completed_at = None
    direction = 1.0 if config.displacement > 0 else -1.0
    for index in range(1, 351):
        now = index * 0.02
        engine.tick(now)
        observation = engine.observation
        peak = max(peak, direction * (observation.positions[target_index] - initial[target_index]))
        assert abs(observation.velocities[target_index]) <= config.max_velocity
        acceleration = (observation.velocities[target_index] - prior_velocity) / 0.02
        assert abs(acceleration) <= config.max_acceleration
        prior_velocity = observation.velocities[target_index]
        for other in range(len(initial)):
            if other != target_index:
                assert observation.positions[other] == initial[other]
        assert engine.status.state != MotionState.FAILED, engine.status.reason
        if engine.status.state == MotionState.SUCCEEDED:
            completed_at = now
            break
    assert peak > abs(config.displacement) * 0.9
    assert peak <= abs(config.displacement)
    assert completed_at is not None
    assert completed_at >= config.duration + config.stable_duration
    assert abs(engine.observation.positions[target_index] - initial[target_index]) <= config.position_tolerance
    assert engine.status.run_id == accepted.run_id
    second = engine.request(completed_at)
    assert second.accepted and second.run_id != accepted.run_id
    engine.shutdown(completed_at)


def test_round_trip_uses_observed_excursion_and_stable_return_with_new_run_ids():
    run_round_trip(enabled())


def test_negative_displacement_and_alternate_joint_are_supported():
    run_round_trip(enabled(displacement=-0.05, target_joint="mock_right_arm_joint2"))


@pytest.mark.parametrize("displacement", [-0.1, 0.1])
def test_inclusive_displacement_bound_returns_to_nonzero_start(displacement):
    run_round_trip(enabled(displacement=displacement))


def test_different_engines_do_not_reuse_cached_run_ids():
    first, second = Engine(enabled()), Engine(enabled())
    first.tick(0.0)
    second.tick(0.0)
    assert first.request(0.0).run_id != second.request(0.0).run_id
    first.shutdown(0.0)
    second.shutdown(0.0)


def test_target_outside_synthetic_limits_is_rejected():
    engine = Engine(enabled(displacement=0.1, position_limit=0.11))
    engine.tick(0.0)
    assert not engine.request(0.0).accepted
    assert engine.status.state == MotionState.IDLE
    engine.shutdown(0.0)


@pytest.mark.parametrize("fault", ["freeze", "repeat", "error", "nan", "inf", "invalid", "timeout", "watchdog"])
def test_feedback_fault_never_succeeds_and_does_not_resume_after_recovery(fault):
    engine = Engine(enabled())
    engine.tick(0.0)
    accepted = engine.request(0.0)
    assert accepted.accepted
    for index in range(1, 21):
        engine.tick(index * 0.02)
    engine.set_fault(fault)
    for index in range(21, 401):
        engine.tick(index * 0.02)
        assert engine.status.state != MotionState.SUCCEEDED
        if engine.status.state == MotionState.FAILED:
            break
    assert engine.status.state == MotionState.FAILED
    assert engine.status.run_id == accepted.run_id
    engine.set_fault("none")
    engine.tick(9.0)
    assert not engine.request(9.0).accepted
    assert engine.status.state == MotionState.FAILED
    engine.shutdown(9.0)


def test_watchdog_stops_without_replaying_commands_or_returning_to_baseline():
    backend = InputBackend()
    engine = Engine(enabled(), backend)
    engine.tick(0.0)
    assert engine.request(0.0).accepted
    engine.tick(0.02)
    before = backend.commands
    engine.tick(1.0)
    assert engine.status.state == MotionState.FAILED
    assert backend.commands == before
    assert backend.polls == 2
    assert backend.holds == 1
    engine.shutdown(1.0)


@pytest.mark.parametrize("bad", [-0.1, math.nan, math.inf])
def test_monotonic_clock_failures_are_terminal(bad):
    engine = Engine(enabled())
    engine.tick(0.0)
    assert engine.request(0.0).accepted
    engine.tick(bad)
    assert engine.status.state == MotionState.FAILED
    engine.shutdown(0.0)


@pytest.mark.parametrize("fault", ["unknown_name", "wrong_order", "out_of_bounds"])
def test_changed_names_and_out_of_bounds_feedback_are_rejected(fault):
    backend = InputBackend()
    engine = Engine(enabled(), backend)
    engine.tick(0.0)
    assert engine.request(0.0).accepted
    if fault == "unknown_name":
        backend.next.names[0] = "unknown_joint"
    elif fault == "wrong_order":
        backend.next.names[:2] = reversed(backend.next.names[:2])
    else:
        backend.next.positions[0] = 1.1
    engine.tick(0.02)
    assert engine.status.state == MotionState.FAILED
    assert backend.commands == 0
    engine.shutdown(0.02)


def test_backend_command_and_hold_failures_are_reported():
    backend = InputBackend()
    engine = Engine(enabled(), backend)
    engine.tick(0.0)
    assert engine.request(0.0).accepted
    backend.command_error = backend.hold_error = True
    engine.tick(0.02)
    assert engine.status.state == MotionState.FAILED
    assert "command failure" in engine.status.reason
    assert "hold failed" in engine.status.reason
    engine.shutdown(0.02)


def test_shutdown_is_bounded_idempotent_and_does_not_command_return():
    backend = InputBackend()
    engine = Engine(enabled(), backend)
    engine.tick(0.0)
    assert engine.request(0.0).accepted
    engine.tick(0.02)
    before = backend.commands
    engine.shutdown(0.02)
    engine.shutdown(0.03)
    engine.tick(0.04)
    assert engine.status.state == MotionState.FAILED
    assert backend.commands == before
    assert backend.holds == 1
    assert not engine.request(0.04).accepted


def test_validation_and_feedback_cannot_be_bypassed_by_mutating_returned_objects():
    config = Config()
    engine = Engine(config)
    config.enable_motion = True
    engine.config.enable_motion = True
    engine.tick(0.0)
    sample = engine.observation
    sample.positions[0] = 99.0
    assert engine.observation.positions[0] != 99.0
    assert not engine.request(0.0).accepted
    with pytest.raises(FrozenInstanceError):
        engine.status.state = MotionState.SUCCEEDED
    engine.shutdown(0.0)


def test_mock_backend_observation_and_command_lists_do_not_alias():
    backend = MockBackend(enabled())
    sample = backend.poll(0.0)
    expected = sample.positions.copy()
    sample.positions[0] = 99.0
    assert backend.poll(0.0).positions == expected
    command = expected.copy()
    backend.command_positions(command, 0.0)
    command[0] = 99.0
    assert backend.poll(0.02).positions == expected
    assert valid_fault("none") and not valid_fault("other")
    with pytest.raises(ValueError, match="unknown mock fault"):
        backend.set_fault("other")


def test_fresh_stationary_feedback_cannot_satisfy_outward_excursion():
    backend = InputBackend()
    engine = Engine(enabled(), backend)
    engine.tick(0.0)
    assert engine.request(0.0).accepted
    for index in range(1, 360):
        engine.tick(index * 0.02)
        assert engine.status.state != MotionState.SUCCEEDED
    assert engine.status.state == MotionState.FAILED
    assert "motion timeout" in engine.status.reason
    engine.shutdown(7.2)


@pytest.mark.parametrize("blocking_feedback", ["velocity", "other_joint"])
def test_completion_requires_all_observed_fields_to_stabilize(blocking_feedback):
    backend = InputBackend()
    engine = Engine(enabled(), backend)
    engine.tick(0.0)
    assert engine.request(0.0).accepted
    backend.next.positions[0] += 0.05
    engine.tick(0.02)
    backend.next.positions[0] -= 0.05
    if blocking_feedback == "velocity":
        backend.next.velocities = [0.1] * 6
    else:
        backend.next.positions[1] += 0.01
    for index in range(2, 220):
        engine.tick(index * 0.02)
        assert engine.status.state == MotionState.RUNNING
    backend.next.velocities = []  # Unknown is allowed; position stability still required.
    backend.next.positions[1] = 0.1
    engine.tick(4.4)
    assert engine.status.state == MotionState.RUNNING
    for index in range(221, 230):
        engine.tick(index * 0.02)
        assert engine.status.state == MotionState.RUNNING
    for index in range(230, 234):
        engine.tick(index * 0.02)
    assert engine.status.state == MotionState.SUCCEEDED
    engine.shutdown(4.66)


def test_repeated_final_sample_cannot_advance_stability_to_success():
    backend = MockBackend(enabled())
    engine = Engine(enabled(), backend)
    engine.tick(0.0)
    assert engine.request(0.0).accepted
    for index in range(1, 203):
        engine.tick(index * 0.02)
    assert engine.status.state == MotionState.RUNNING
    last = engine.observation
    engine.set_fault("repeat")
    for index in range(203, 240):
        engine.tick(index * 0.02)
        assert engine.status.state != MotionState.SUCCEEDED
    assert engine.status.state == MotionState.FAILED
    assert engine.observation.sequence == last.sequence
    assert engine.observation.sample_time == last.sample_time
    engine.shutdown(4.8)


@pytest.mark.parametrize("gap", [0.04, 0.1, 0.49])
def test_subwatchdog_delay_stretches_motion_without_velocity_or_acceleration_spike(gap):
    config = enabled()
    engine = Engine(config)
    engine.tick(0.0)
    baseline = engine.observation.positions
    assert engine.request(0.0).accepted
    times = [index * 0.02 for index in range(1, 41)]
    times += [0.8 + gap + index * 0.02 for index in range(350)]
    previous = engine.observation
    peak_displacement = 0.0
    completed_at = None
    for now in times:
        engine.tick(now)
        assert engine.status.state != MotionState.FAILED, engine.status.reason
        observation = engine.observation
        assert observation.sample_time > previous.sample_time
        interval = observation.sample_time - previous.sample_time
        assert abs(observation.velocities[0]) <= config.max_velocity
        assert abs(observation.velocities[0] - previous.velocities[0]) / interval <= config.max_acceleration
        assert observation.positions[1:] == baseline[1:]
        peak_displacement = max(peak_displacement, observation.positions[0] - baseline[0])
        previous = observation
        if engine.status.state == MotionState.SUCCEEDED:
            completed_at = now
            break
    assert completed_at is not None
    assert completed_at >= config.duration + config.stable_duration + gap - 0.02
    assert peak_displacement > config.displacement * 0.9
    assert abs(engine.observation.positions[0] - baseline[0]) <= config.position_tolerance
    engine.shutdown(completed_at)


@pytest.mark.parametrize("violation", ["velocity", "acceleration"])
def test_observed_motion_limit_violation_fails_before_command_or_healthy_sample(violation):
    backend = InputBackend()
    backend.next.velocities = [0.0] * 6
    config = enabled()
    engine = Engine(config, backend)
    engine.tick(0.0)
    accepted = engine.request(0.0)
    assert accepted.accepted
    baseline = engine.observation
    backend.next.velocities[0] = (config.max_velocity + 0.01 if violation == "velocity"
                                  else config.max_acceleration * 0.02 + 0.001)
    engine.tick(0.02)
    assert engine.status.state == MotionState.FAILED
    assert violation in engine.status.reason
    assert engine.status.run_id == accepted.run_id
    assert not engine.healthy(0.02)
    assert engine.observation == baseline
    assert backend.commands == 0
    assert backend.holds == 1
    assert not engine.request(0.02).accepted
    engine.shutdown(0.02)


def test_repeated_slow_callbacks_cannot_stretch_past_real_monotonic_motion_timeout():
    config = enabled()
    engine = Engine(config)
    engine.tick(0.0)
    assert engine.request(0.0).accepted
    for index in range(1, 30):
        now = index * 0.3  # Each gap remains below the scheduler watchdog.
        engine.tick(now)
        assert engine.status.state != MotionState.SUCCEEDED
        if engine.status.state == MotionState.FAILED:
            break
    assert engine.status.state == MotionState.FAILED
    assert "motion timeout" in engine.status.reason
    assert config.motion_timeout < now <= config.motion_timeout + 0.3
    engine.shutdown(now)


def test_tick_clock_cannot_move_back_before_an_accepted_request():
    engine = Engine(enabled())
    engine.tick(0.0)
    assert engine.request(0.1).accepted
    engine.tick(0.05)
    assert engine.status.state == MotionState.FAILED
    assert "clock moved backward after accepted request" in engine.status.reason
    engine.shutdown(0.1)


@pytest.mark.parametrize("cadence", [0.02, 0.0199])
@pytest.mark.parametrize("delayed_interval", [0.02, 0.04])
def test_repeated_motion_with_short_catchup_callbacks(cadence, delayed_interval):
    config = enabled()
    engine = Engine(config)
    now = 0.0
    engine.tick(now)
    run_ids = set()
    for _ in range(2):
        baseline = engine.observation.positions
        accepted = engine.request(now)
        assert accepted.accepted
        assert accepted.run_id not in run_ids
        run_ids.add(accepted.run_id)
        previous = engine.observation
        peak = 0.0
        started = now
        for index in range(400):
            interval = delayed_interval if index == 62 else 0.001 if index == 63 else cadence
            now += interval
            engine.tick(now)
            assert engine.status.state != MotionState.FAILED, engine.status.reason
            observed = engine.observation
            # Every callback, including the 1 ms callback, is a real sample.
            assert observed.sequence == previous.sequence + 1
            assert observed.sample_time == now
            assert observed.positions[1:] == baseline[1:]
            actual_interval = observed.sample_time - previous.sample_time
            for velocity, prior in zip(observed.velocities, previous.velocities):
                assert abs(velocity) <= config.max_velocity
                assert abs(velocity - prior) / actual_interval <= config.max_acceleration
            peak = max(peak, observed.positions[0] - baseline[0])
            previous = observed
            if engine.status.state == MotionState.SUCCEEDED:
                break
        assert engine.status.state == MotionState.SUCCEEDED
        assert now - started < config.motion_timeout
        assert peak > config.displacement * 0.9
        assert abs(observed.positions[0] - baseline[0]) <= config.position_tolerance
        for _ in range(15):
            now += cadence
            engine.tick(now)
    engine.shutdown(now)


def test_mock_ramp_matches_first_order_solution_and_is_continuous_when_interrupted():
    config = enabled()
    backend = MockBackend(config)
    baseline = backend.poll(0.0)
    target = baseline.positions.copy()
    target[0] += 0.001
    backend.command_positions(target, 0.0)
    now = 0.01  # Halfway through the 20 ms ramp.
    observed = backend.poll(now)
    slope = 0.001 / 0.02
    alpha = -math.expm1(-now / config.tracking_time_constant)
    expected_position = baseline.positions[0] + slope * (now - config.tracking_time_constant * alpha)
    ramp_value = baseline.positions[0] + slope * now
    expected_velocity = (ramp_value - expected_position) / config.tracking_time_constant
    assert observed.positions[0] == pytest.approx(expected_position, abs=1e-14)
    assert observed.velocities[0] == pytest.approx(expected_velocity, abs=1e-14)

    target[0] += 0.001
    backend.command_positions(target, now)
    # The interrupted ramp starts from its current value, not either endpoint.
    dt = 0.001
    new_slope = (target[0] - ramp_value) / 0.02
    alpha = -math.expm1(-dt / config.tracking_time_constant)
    expected_position += ((ramp_value - expected_position) * alpha
                          + new_slope * (dt - config.tracking_time_constant * alpha))
    expected_velocity = (ramp_value + new_slope * dt - expected_position) / config.tracking_time_constant
    observed = backend.poll(now + dt)
    assert observed.positions[0] == pytest.approx(expected_position, abs=1e-14)
    assert observed.velocities[0] == pytest.approx(expected_velocity, abs=1e-14)

    backend.hold(now + dt)
    held = backend.poll(now + dt + 0.01)
    assert held.positions == observed.positions
    assert held.velocities == [0.0] * 6


@pytest.mark.parametrize("interval", [0.001, 0.02, 0.04])
def test_mock_acceleration_guard_uses_actual_interval_and_rejects_first_bad_sample(interval):
    backend = InputBackend()
    backend.next.velocities = [0.0] * 6
    config = enabled()
    engine = Engine(config, backend)
    engine.tick(0.0)
    accepted = engine.request(0.0)
    assert accepted.accepted
    engine.tick(0.04)
    previous = engine.observation
    commands = backend.commands
    backend.next.velocities[0] = config.max_acceleration * interval * 1.01
    now = 0.04 + interval
    engine.tick(now)
    assert engine.status.state == MotionState.FAILED
    assert "observed mock acceleration" in engine.status.reason
    assert engine.status.run_id == accepted.run_id
    assert engine.observation == previous
    assert backend.commands == commands
    assert backend.holds == 1
    assert not engine.healthy(now)
    assert not engine.request(now).accepted
    engine.shutdown(now)


def test_command_between_polls_integrates_previous_ramp_without_fabricating_samples():
    config = enabled()
    continuous = MockBackend(config)
    sampled = MockBackend(config)
    initial = continuous.poll(0.0)
    sampled.poll(0.0)
    target = initial.positions.copy()
    target[0] += 0.001
    continuous.command_positions(target, 0.0)
    sampled.command_positions(target, 0.0)
    # Only the reference backend exposes the intermediate physical state.
    sampled.poll(0.01)
    target[0] += 0.001
    continuous.command_positions(target, 0.01)
    sampled.command_positions(target, 0.01)
    actual = continuous.poll(0.025)
    expected = sampled.poll(0.025)
    assert actual.sequence == initial.sequence + 1
    assert expected.sequence == initial.sequence + 2
    assert actual.sample_time == expected.sample_time == 0.025
    assert actual.positions == pytest.approx(expected.positions, abs=1e-14)
    assert actual.velocities == pytest.approx(expected.velocities, abs=1e-14)


def test_first_command_before_first_poll_has_the_same_physical_result():
    config = enabled()
    unsampled = MockBackend(config)
    sampled = MockBackend(config)
    target = sampled.poll(0.0).positions
    target[0] += 0.001
    unsampled.command_positions(target, 0.0)
    sampled.command_positions(target, 0.0)
    actual = unsampled.poll(0.01)
    expected = sampled.poll(0.01)
    assert actual.sequence == 1
    assert expected.sequence == 2
    assert actual.positions == expected.positions
    assert actual.velocities == expected.velocities


def test_mock_follower_does_not_clip_observed_limits_to_hide_abrupt_commands():
    config = enabled()
    backend = MockBackend(config)
    initial = backend.poll(0.0)
    target = initial.positions.copy()
    target[0] += config.displacement
    backend.command_positions(target, 0.0)
    observed = backend.poll(0.02)
    assert observed.velocities[0] > config.max_velocity
    assert (observed.velocities[0] - initial.velocities[0]) / 0.02 > config.max_acceleration
    assert observed.velocities[0] == pytest.approx(
        (target[0] - observed.positions[0]) / config.tracking_time_constant, abs=1e-14)
