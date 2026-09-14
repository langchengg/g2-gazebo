"""Pure Python mock motion and freshness logic, independent of ROS and GDK.

Migrated from this repository's reviewed C++ mock implementation. Callers inject
local monotonic seconds and serialize all operations; no method sleeps or starts
a worker. This module deliberately cannot operate a GDK backend.
"""

from __future__ import annotations

import copy
import math
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import Enum
from typing import Optional

from .backends.base import Observation, RobotBackend

_MOCK_SOURCE_PERIOD = 1.0 / 50.0


@dataclass
class Config:
    """Project mock parameters; these values are not G2 safety parameters."""

    backend: str = "mock"
    enable_motion: bool = False
    target_joint: str = "mock_left_arm_joint1"
    displacement: float = 0.05
    duration: float = 4.0
    publish_hz: float = 10.0
    max_displacement: float = 0.1
    max_velocity: float = 0.2
    max_acceleration: float = 0.5
    position_limit: float = 1.0
    feedback_timeout: float = 0.6
    watchdog_timeout: float = 0.5
    motion_timeout: float = 7.0
    position_tolerance: float = 0.002
    velocity_tolerance: float = 0.01
    stable_duration: float = 0.2
    tracking_time_constant: float = 0.08
    fault: str = "none"


class MotionState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class Status:
    state: MotionState = MotionState.IDLE
    run_id: str = ""
    reason: str = "ready; no automatic motion"


@dataclass(frozen=True)
class RequestResult:
    accepted: bool = False
    run_id: str = ""
    reason: str = ""


def mock_joint_names() -> list[str]:
    return [
        "mock_left_arm_joint1", "mock_left_arm_joint2", "mock_left_arm_joint3",
        "mock_right_arm_joint1", "mock_right_arm_joint2", "mock_right_arm_joint3",
    ]


def valid_fault(fault: str) -> bool:
    return fault in (
        "none", "freeze", "repeat", "error", "nan", "inf", "invalid", "timeout", "watchdog"
    )


def _finite_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _positive(value: float, name: str) -> None:
    if not _finite_number(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and positive")


def validate_config(config: Config) -> None:
    """Raise ValueError before any backend activity for invalid project inputs."""
    if config.backend not in ("mock", "gdk"):
        raise ValueError("backend must be mock or gdk")
    if not isinstance(config.enable_motion, bool):
        raise ValueError("enable_motion must be a boolean")
    if config.backend == "mock" and config.target_joint not in mock_joint_names():
        raise ValueError("target_joint is not a synthetic mock joint")
    if not valid_fault(config.fault):
        raise ValueError(f"unknown mock fault: {config.fault}")
    for name in (
        "duration", "publish_hz", "max_displacement", "max_velocity", "max_acceleration",
        "position_limit", "feedback_timeout", "watchdog_timeout", "motion_timeout",
        "position_tolerance", "velocity_tolerance", "stable_duration", "tracking_time_constant",
    ):
        _positive(getattr(config, name), name)
    if config.publish_hz > 50.0:
        raise ValueError("publish_hz cannot exceed the 50 Hz mock source tick")
    if (not _finite_number(config.displacement) or config.displacement == 0.0
            or abs(config.displacement) > config.max_displacement):
        raise ValueError("displacement must be finite, nonzero and within max_displacement")
    half = config.duration * 0.5
    # Exact maxima of q(u)=10u^3-15u^4+6u^5, independently bounded per leg.
    if half == 0.0:
        raise ValueError("duration is too small to represent a mock profile")
    peak_velocity = 1.875 * abs(config.displacement) / half
    if not math.isfinite(peak_velocity) or peak_velocity > config.max_velocity:
        raise ValueError("quintic mock profile exceeds max_velocity")
    # Divide sequentially rather than square half: avoid overflow/underflow
    # exceptions while retaining the mathematically identical bound.
    peak_acceleration = (10.0 / math.sqrt(3.0)) * (abs(config.displacement) / half) / half
    if not math.isfinite(peak_acceleration) or peak_acceleration > config.max_acceleration:
        raise ValueError("quintic mock profile exceeds max_acceleration")
    if config.position_tolerance >= abs(config.displacement) * 0.25:
        raise ValueError("position_tolerance must be less than one quarter of displacement magnitude")
    minimum_timeout = config.duration + config.stable_duration
    if not math.isfinite(minimum_timeout) or config.motion_timeout <= minimum_timeout:
        raise ValueError("motion_timeout must exceed duration plus stable_duration")


def validate_observation(observation: Observation) -> str:
    """Return an error string, or an empty string for valid measured fields."""
    if not isinstance(observation, Observation):
        return "invalid observation type"
    arrays = (observation.names, observation.positions, observation.velocities, observation.efforts)
    if any(not isinstance(array, Sequence) or isinstance(array, (str, bytes)) for array in arrays):
        return "invalid joint array type"
    if not observation.names:
        return "empty joint names"
    if len(observation.positions) != len(observation.names):
        return "position/name dimension mismatch"
    if any(array and len(array) != len(observation.names)
           for array in (observation.velocities, observation.efforts)):
        return "optional array dimension mismatch"
    unique = set()
    for name in observation.names:
        if not isinstance(name, str) or not name or name in unique:
            return "invalid, empty or duplicate joint name"
        unique.add(name)
    if any(not _finite_number(value) for array in arrays[1:] for value in array):
        return "non-finite or nonnumeric joint value"
    if not _finite_number(observation.sample_time):
        return "non-finite source timestamp"
    if (isinstance(observation.sequence, bool) or not isinstance(observation.sequence, int)
            or observation.sequence < 0):
        return "invalid source sequence"
    return ""


class SourceFreshness:
    """Compare source markers for progression, never against the local clock."""

    def __init__(self, timeout: float):
        _positive(timeout, "freshness timeout")
        self._timeout = timeout
        self._seen = False
        self._valid = False
        self._sequence: Optional[int] = None
        self._source_time: Optional[float] = None
        self._last_receive = 0.0
        self._last_progress = 0.0
        self._invalid_reason = ""

    def _invalidate(self, reason: str) -> bool:
        self._valid = False
        self._invalid_reason = reason
        return False

    def observe(self, sequence: Optional[int], source_time: Optional[float],
                receive_time: float) -> bool:
        if not _finite_number(receive_time) or (source_time is not None and not _finite_number(source_time)):
            return self._invalidate("non-finite freshness timestamp")
        if sequence is not None and (isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0):
            return self._invalidate("invalid source sequence")
        if self._seen and receive_time < self._last_receive:
            return self._invalidate("local monotonic clock moved backward")
        if self._seen and ((sequence is None) != (self._sequence is None)
                           or (source_time is None) != (self._source_time is None)):
            return self._invalidate("source marker availability changed")
        self._last_receive = receive_time
        if self._seen:
            if ((sequence is not None and sequence < self._sequence)
                    or (source_time is not None and source_time < self._source_time)):
                return self._invalidate("source marker moved backward")
            if ((sequence is not None and sequence == self._sequence)
                    or (source_time is not None and source_time == self._source_time)):
                return False
        self._sequence = sequence
        self._source_time = source_time
        self._last_progress = receive_time
        self._seen = True
        self._valid = True
        self._invalid_reason = ""
        return True

    def healthy(self, now: float) -> bool:
        return (self._seen and self._valid and _finite_number(now) and now >= self._last_receive
                and now - self._last_receive <= self._timeout
                and now - self._last_progress <= self._timeout)

    def reason(self, now: float) -> str:
        if not _finite_number(now):
            return "non-finite local clock"
        if not self._seen:
            return self._invalid_reason or "waiting for first observation"
        if not self._valid:
            return self._invalid_reason
        if now < self._last_receive:
            return "local monotonic clock moved backward"
        if now - self._last_receive > self._timeout:
            return "feedback receive timeout"
        if now - self._last_progress > self._timeout:
            return "source sequence/timestamp stopped advancing"
        if self._sequence is not None or self._source_time is not None:
            return "healthy"
        return "receive active; source sample age unverified"


def _smoothstep(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * value * (10.0 + value * (-15.0 + 6.0 * value))


class Engine:
    """Nonblocking mock state machine. The wrapper must call shutdown explicitly.

    ``config``, ``status`` and ``observation`` are snapshots: callers cannot mutate
    a validated configuration or observed feedback through a returned object.
    GDK read-only adapters belong to the separate hardware path, never this
    synthetic joint trajectory engine.
    """

    def __init__(self, config: Config, backend: Optional[RobotBackend] = None):
        validate_config(config)
        if config.backend != "mock":
            raise RuntimeError("GDK backend BLOCKED in mock Engine; use the separately verified read-only adapter; no mock fallback")
        self._config = replace(config)
        if backend is None:
            from .backends.mock_backend import MockBackend
            backend = MockBackend(self._config)
        self._backend = backend
        self._freshness = SourceFreshness(self._config.feedback_timeout)
        self._observation: Optional[Observation] = None
        self._status = Status()
        self._process_id = uuid.uuid4().hex
        self._request_count = 0
        self._stopped = False
        self._backend_ok = True
        self._fault_latched = False
        self._backend_error = ""
        self._last_tick: Optional[float] = None
        self._started = 0.0
        self._motion_elapsed = 0.0
        self._motion_updated_at = 0.0
        self._stable_since: Optional[float] = None
        self._baseline: list[float] = []
        self._target_index = 0
        self._observed_excursion = False

    @property
    def config(self) -> Config:
        return replace(self._config)

    @property
    def observation(self) -> Optional[Observation]:
        return copy.deepcopy(self._observation)

    @property
    def status(self) -> Status:
        return self._status

    def _fail(self, reason: str, now: float) -> None:
        self._fault_latched = True
        self._backend_ok = False
        self._backend_error = reason
        self._status = replace(self._status, state=MotionState.FAILED, reason=reason)
        self._stable_since = None
        try:
            self._backend.hold(now)
        except Exception as error:
            self._backend_error += f"; hold failed: {error}"
            self._status = replace(self._status, reason=self._backend_error)

    def tick(self, now: float) -> None:
        if self._stopped or self._fault_latched:
            return
        if not _finite_number(now):
            self._fail("non-finite monotonic clock", self._last_tick if self._last_tick is not None else 0.0)
            return
        if self._last_tick is not None:
            if now < self._last_tick:
                self._fail("monotonic clock moved backward", now)
                return
            if now - self._last_tick > self._config.watchdog_timeout:
                self._fail("scheduler watchdog exceeded; historical commands were not replayed", now)
                return
        self._last_tick = now
        new_observation = False
        try:
            incoming = self._backend.poll(now)
            if incoming is not None:
                error = validate_observation(incoming)
                if error:
                    self._fail(f"invalid feedback: {error}", now)
                    return
                if list(incoming.names) != mock_joint_names():
                    self._fail("unexpected mock joint names or order", now)
                    return
                if incoming.sample_time > now or now - incoming.sample_time > self._config.feedback_timeout:
                    self._fail("mock feedback sample time is future or stale", now)
                    return
                if any(abs(value) > self._config.position_limit for value in incoming.positions):
                    self._fail("feedback exceeds synthetic position limit", now)
                    return
                if any(abs(value) > self._config.max_velocity for value in incoming.velocities):
                    self._fail("observed mock velocity exceeds max_velocity", now)
                    return
                previous = self._observation
                if (previous is not None and previous.velocities and incoming.velocities
                        and incoming.sample_time > previous.sample_time):
                    sample_interval = incoming.sample_time - previous.sample_time
                    if any(abs(current - prior) / sample_interval > self._config.max_acceleration
                           for current, prior in zip(incoming.velocities, previous.velocities)):
                        self._fail("observed mock acceleration exceeds max_acceleration", now)
                        return
                new_observation = self._freshness.observe(incoming.sequence, incoming.sample_time, now)
                if new_observation:
                    self._observation = copy.deepcopy(incoming)
                if not self._freshness.healthy(now):
                    self._fail(self._freshness.reason(now), now)
                    return
        except Exception as error:
            self._fail(f"backend failure: {error}", now)
            return
        if self._observation is not None and not self._freshness.healthy(now):
            self._fail(self._freshness.reason(now), now)
            return
        if self._status.state != MotionState.RUNNING:
            return
        if self._observation is None:
            self._fail("missing feedback during motion", now)
            return
        elapsed = now - self._started
        if now < self._motion_updated_at:
            self._fail("monotonic clock moved backward after accepted request", now)
            return
        if elapsed > self._config.motion_timeout:
            self._fail("motion timeout; completion not observed", now)
            return
        # A late callback must not jump to a later trajectory command. Advance
        # at most one normal source period; real monotonic time still governs
        # watchdogs and the overall timeout. No historical command is replayed.
        self._motion_elapsed += min(now - self._motion_updated_at, _MOCK_SOURCE_PERIOD)
        self._motion_updated_at = now
        excursion = (self._observation.positions[self._target_index] - self._baseline[self._target_index])
        excursion *= 1.0 if self._config.displacement > 0.0 else -1.0
        if new_observation and excursion >= abs(self._config.displacement) * 0.8:
            self._observed_excursion = True
        settled = (new_observation and self._observed_excursion
                   and self._motion_elapsed >= self._config.duration)
        for index, baseline in enumerate(self._baseline):
            settled = settled and abs(self._observation.positions[index] - baseline) <= self._config.position_tolerance
            if self._observation.velocities:
                settled = settled and abs(self._observation.velocities[index]) <= self._config.velocity_tolerance
        if new_observation:
            if not settled:
                self._stable_since = None
            elif self._stable_since is None:
                self._stable_since = now
            elif now - self._stable_since >= self._config.stable_duration:
                self._status = replace(self._status, state=MotionState.SUCCEEDED,
                                       reason="observed outward excursion and stable return to baseline")
                return
        half = self._config.duration * 0.5
        weight = (_smoothstep(self._motion_elapsed / half) if self._motion_elapsed <= half
                  else 1.0 - _smoothstep((self._motion_elapsed - half) / half))
        command = self._baseline.copy()
        command[self._target_index] += self._config.displacement * weight
        try:
            self._backend.command_positions(command, now)
        except Exception as error:
            self._fail(f"command failure: {error}", now)

    def request(self, now: float) -> RequestResult:
        if self._stopped:
            return RequestResult(reason="node is stopping")
        if self._status.state == MotionState.RUNNING:
            return RequestResult(run_id=self._status.run_id, reason="another motion is RUNNING; no queue")
        if not self._config.enable_motion:
            return RequestResult(reason="enable_motion=false")
        if not self.healthy(now):
            return RequestResult(reason=self.health_reason(now))
        if self._config.target_joint not in self._observation.names:
            return RequestResult(reason="target joint missing from feedback")
        self._target_index = self._observation.names.index(self._config.target_joint)
        target = self._observation.positions[self._target_index] + self._config.displacement
        if not math.isfinite(target) or abs(target) > self._config.position_limit:
            return RequestResult(reason="requested target exceeds synthetic position limit")
        self._baseline = list(self._observation.positions)
        self._started = now
        self._motion_elapsed = 0.0
        self._motion_updated_at = now
        self._stable_since = None
        self._observed_excursion = False
        self._request_count += 1
        self._status = Status(MotionState.RUNNING, f"{self._process_id}-{self._request_count}",
                              "request accepted; completion requires feedback")
        return RequestResult(True, self._status.run_id, self._status.reason)

    def healthy(self, now: float) -> bool:
        return (not self._stopped and not self._fault_latched and self._backend_ok
                and self._observation is not None and self._freshness.healthy(now)
                and self._last_tick is not None and _finite_number(now)
                and now >= self._last_tick and now - self._last_tick <= self._config.watchdog_timeout)

    def health_reason(self, now: float) -> str:
        if self._stopped:
            return "stopped"
        if self._fault_latched or not self._backend_ok:
            return "fault latched; restart required: " + self._backend_error
        if not self._freshness.healthy(now):
            return self._freshness.reason(now)
        if self._last_tick is None or now < self._last_tick or now - self._last_tick > self._config.watchdog_timeout:
            return "scheduler heartbeat is stale or invalid"
        return "healthy mock observation; local simulation sampling clock"

    def shutdown(self, now: float) -> None:
        if self._stopped:
            return
        if self._status.state == MotionState.RUNNING:
            self._fail("shutdown cancelled active motion; no return motion commanded", now)
        else:
            try:
                self._backend.hold(now)
            except Exception as error:
                self._fail(f"shutdown hold failed: {error}", now)
        self._stopped = True

    def set_fault(self, fault: str) -> None:
        self._backend.set_fault(fault)
