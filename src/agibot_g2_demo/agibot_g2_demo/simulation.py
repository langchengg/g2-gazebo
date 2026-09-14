"""Simulation-only validation and clocks, independent of ROS and simulator I/O.

All positions below must come from simulator feedback. This module never creates
observations or advances a synthetic robot. The caller injects both time domains.
"""
from dataclasses import dataclass
import math
import uuid


def finite(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


@dataclass(frozen=True)
class SimConfig:
    names: tuple
    lower: tuple
    upper: tuple
    velocity_limits: tuple
    target: str
    delta: float = 0.05
    duration: float = 6.0
    max_acceleration: float = 0.5
    position_tolerance: float = 0.002
    velocity_tolerance: float = 0.01
    stable_duration: float = 0.2
    feedback_timeout: float = 3.0
    source_timeout: float = 1.0
    pause_timeout: float = 3.0
    wall_budget: float = 180.0

    def validate(self):
        n = len(self.names)
        if not n or any(not isinstance(v, str) or not v for v in self.names) or len(set(self.names)) != n:
            raise ValueError('sim_joint_names must contain distinct nonempty model joint names')
        if self.target not in self.names:
            raise ValueError('target_joint is not in the model controlled joint group')
        if any(len(v) != n for v in (self.lower, self.upper, self.velocity_limits)):
            raise ValueError('model joint limit arrays must match sim_joint_names')
        if any(not finite(v) for values in (self.lower, self.upper, self.velocity_limits) for v in values):
            raise ValueError('model joint limits must be finite')
        if any(lo >= hi or vel <= 0 for lo, hi, vel in zip(self.lower, self.upper, self.velocity_limits)):
            raise ValueError('model joint bounds must be ordered and velocities positive')
        if not finite(self.delta) or not 0 < abs(self.delta) <= 0.1:
            raise ValueError('simulation displacement must be finite, nonzero and at most 0.1 rad')
        for key in ('duration', 'max_acceleration', 'position_tolerance', 'velocity_tolerance',
                    'stable_duration', 'feedback_timeout', 'source_timeout', 'pause_timeout', 'wall_budget'):
            if not finite(getattr(self, key)) or getattr(self, key) <= 0:
                raise ValueError(key + ' must be finite and positive')
        if self.duration < 0.1 or self.duration > 60:
            raise ValueError('simulation duration must be within [0.1,60] seconds')
        half = self.duration / 2
        peak_velocity = 1.875 * abs(self.delta) / half
        peak_acceleration = 10 / math.sqrt(3) * abs(self.delta) / half / half
        if peak_velocity > self.velocity_limits[self.names.index(self.target)]:
            raise ValueError('quintic trajectory exceeds model velocity limit')
        if peak_acceleration > self.max_acceleration:
            raise ValueError('quintic trajectory exceeds simulation acceleration bound')
        if self.position_tolerance >= abs(self.delta) * 0.2:
            raise ValueError('position_tolerance must be smaller than 20 percent of displacement')
        if self.wall_budget <= self.duration + self.stable_duration:
            raise ValueError('wall motion budget must exceed nominal simulation motion duration')
        return self


def ordered_sample(names, positions, velocities, efforts, config, state_interfaces=('position', 'velocity')):
    """Validate broadcaster input and map by names; preserve unknown optional fields.

    Some Humble broadcasters fill an unsupported optional interface with NaNs.
    Only an entirely unavailable optional field explicitly absent from the model
    interface inventory can become an empty array. Mixed NaNs are corruption.
    """
    names = list(names)
    if len(names) != len(config.names) or len(set(names)) != len(names) or set(names) != set(config.names):
        raise ValueError('feedback joint names differ from model controlled joint group')
    arrays = []
    for field, values in (('position', positions), ('velocity', velocities), ('effort', efforts)):
        values = list(values)
        if field != 'position' and not values:
            arrays.append([])
            continue
        if len(values) != len(names):
            raise ValueError(field + ' array length differs from joint names')
        if (field != 'position' and field not in state_interfaces and
                all(isinstance(v, float) and math.isnan(v) for v in values)):
            arrays.append([])
            continue
        if any(not finite(v) for v in values):
            raise ValueError(field + ' feedback contains non-finite values')
        arrays.append([values[names.index(name)] for name in config.names])
    if any(v < lo - config.position_tolerance or v > hi + config.position_tolerance
           for v, lo, hi in zip(arrays[0], config.lower, config.upper)):
        raise ValueError('observed position outside model joint limits')
    return tuple(arrays)


def trajectory_points(config, baseline):
    config.validate()
    if len(baseline) != len(config.names) or any(not finite(v) for v in baseline):
        raise ValueError('baseline must contain finite feedback for every controlled joint')
    destination = list(baseline)
    destination[config.names.index(config.target)] += config.delta
    for values in (baseline, destination):
        if any(v < lo or v > hi for v, lo, hi in zip(values, config.lower, config.upper)):
            raise ValueError('trajectory crosses model joint position limit')
    zeros = [0.0] * len(baseline)
    # Supplying all three derivatives selects the controller's quintic spline.
    return [(0.0, list(baseline), list(zeros), list(zeros)),
            (config.duration / 2, destination, list(zeros), list(zeros)),
            (config.duration, list(baseline), list(zeros), list(zeros))]


class SimFeedback:
    """Observe /clock and measured joint state, with a new epoch after reset."""
    def __init__(self, config):
        self.config = config
        self.epoch = 0
        self.clock_ns = None
        self.clock_progress_wall = None
        self.clock_advances = 0
        self.stamp_ns = None
        self.sample_wall = None
        self.positions = self.velocities = self.efforts = None
        self.error = ''

    def clock(self, ns, wall):
        if not isinstance(ns, int) or ns < 0 or not finite(wall):
            self.error = 'invalid simulation clock'
            return False
        reset = self.clock_ns is not None and ns < self.clock_ns
        if reset:
            self.epoch += 1
            self.stamp_ns = self.sample_wall = None
            self.positions = self.velocities = self.efforts = None
            self.clock_advances = 0
            self.error = 'simulation clock reset; waiting for new feedback'
        if self.clock_ns is None or ns != self.clock_ns:
            self.clock_progress_wall = wall
            self.clock_advances += 1
        self.clock_ns = ns
        return reset

    def observe(self, ns, wall, positions, velocities=(), efforts=()):
        if not isinstance(ns, int) or ns <= 0 or self.clock_ns is None:
            self.error = 'waiting for valid simulator clock and sample timestamp'
            return False
        if self.stamp_ns is not None and ns <= self.stamp_ns:
            self.error = 'source timestamp did not advance'
            return False
        # DDS may deliver source state slightly ahead of the independently bridged clock.
        age = (self.clock_ns - ns) / 1e9
        if age < -0.1 or age > self.config.source_timeout:
            self.error = 'source timestamp is outside the current simulation clock window'
            return False
        self.stamp_ns, self.sample_wall = ns, wall
        self.positions, self.velocities, self.efforts = list(positions), list(velocities), list(efforts)
        self.error = ''
        return True

    def reason(self, wall):
        if self.error:
            return self.error
        if self.clock_advances < 2 or not self.clock_ns:
            return 'waiting for advancing simulation clock'
        if self.clock_progress_wall is None or wall - self.clock_progress_wall > self.config.pause_timeout:
            return 'simulation clock paused or unavailable'
        if self.sample_wall is None or self.positions is None:
            return 'waiting for simulator joint feedback'
        if wall < self.sample_wall or wall - self.sample_wall > self.config.feedback_timeout:
            return 'simulator feedback wall timeout'
        if (self.clock_ns - self.stamp_ns) / 1e9 > self.config.source_timeout:
            return 'simulator feedback expired in simulation time'
        return ''


class SimRun:
    """Action result and independently observed motion must agree on completion."""
    def __init__(self, config):
        self.config = config
        self.run_id = ''
        self.state = 'IDLE'
        self.reason = 'ready; startup does not request motion'
        self.epoch = None
        self.baseline = None
        self.start_ns = self.start_wall = None
        self.result_ok = False
        self.result_stamp_ns = None
        self.peak = 0.0
        self.minimum = 0.0
        self.stable_since = None
        self.last_observed_ns = None

    def begin(self, feedback, wall):
        if self.state == 'RUNNING':
            raise ValueError('a motion request is already running')
        error = feedback.reason(wall)
        if error:
            raise ValueError(error)
        if not feedback.velocities or any(abs(v) > self.config.velocity_tolerance for v in feedback.velocities):
            raise ValueError('controlled joints must have measured near-zero velocity before motion')
        points = trajectory_points(self.config, feedback.positions)
        self.run_id = uuid.uuid4().hex
        self.state, self.reason = 'RUNNING', 'request accepted; awaiting controller acceptance'
        self.epoch = feedback.epoch
        self.baseline = list(feedback.positions)
        self.start_ns, self.start_wall = feedback.stamp_ns, wall
        self.result_ok = False
        self.result_stamp_ns = self.stable_since = self.last_observed_ns = None
        self.peak = self.minimum = 0.0
        return points

    def fail(self, reason):
        if self.state == 'RUNNING':
            self.state, self.reason = 'FAILED', str(reason)

    def result(self, successful, reason, feedback):
        if self.state != 'RUNNING':
            return
        if not successful:
            self.fail(reason)
        else:
            self.result_ok = True
            self.result_stamp_ns = feedback.stamp_ns
            self.reason = 'controller succeeded; waiting for independent fresh stable feedback'

    def update(self, feedback, wall):
        if self.state != 'RUNNING':
            return
        if feedback.epoch != self.epoch:
            self.fail('simulation clock reset during motion')
            return
        error = feedback.reason(wall)
        if error:
            self.fail(error)
            return
        if wall - self.start_wall > self.config.wall_budget:
            self.fail('motion wall budget exceeded')
            return
        if feedback.stamp_ns <= self.start_ns or feedback.stamp_ns == self.last_observed_ns:
            return
        self.last_observed_ns = feedback.stamp_ns
        i = self.config.names.index(self.config.target)
        signed = (feedback.positions[i] - self.baseline[i]) * math.copysign(1, self.config.delta)
        self.peak = max(self.peak, signed)
        self.minimum = min(self.minimum, signed)
        if feedback.velocities and any(abs(v) > limit * 1.2 + self.config.velocity_tolerance
                for v, limit in zip(feedback.velocities, self.config.velocity_limits)):
            self.fail('observed velocity exceeds model velocity limit')
            return
        if self.peak > abs(self.config.delta) * 1.2 or self.minimum < -self.config.position_tolerance:
            self.fail('observed wrong direction or excessive target overshoot')
            return
        if any(abs(v - q) > self.config.position_tolerance for j, (v, q) in
               enumerate(zip(feedback.positions, self.baseline)) if j != i):
            self.fail('non-target controlled joint moved beyond tolerance')
            return
        if not self.result_ok or self.result_stamp_ns is None or feedback.stamp_ns <= self.result_stamp_ns:
            return
        near = all(abs(v - q) <= self.config.position_tolerance for v, q in
                   zip(feedback.positions, self.baseline))
        slow = bool(feedback.velocities) and all(abs(v) <= self.config.velocity_tolerance for v in feedback.velocities)
        if near and slow and self.peak >= abs(self.config.delta) * 0.8:
            if self.stable_since is None:
                self.stable_since = feedback.stamp_ns
            if (feedback.stamp_ns - self.stable_since) / 1e9 >= self.config.stable_duration:
                self.state, self.reason = 'SUCCEEDED', 'controller succeeded and new simulator feedback verified excursion and stable return'
        else:
            self.stable_since = None
