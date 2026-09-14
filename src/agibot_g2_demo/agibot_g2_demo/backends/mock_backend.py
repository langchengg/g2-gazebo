"""Deterministic synthetic follower, implemented entirely with Python stdlib."""

from __future__ import annotations

import copy
import math
from dataclasses import replace
from typing import Optional, Sequence

from .base import Observation
from ..motion import Config, _MOCK_SOURCE_PERIOD, _finite_number, mock_joint_names, valid_fault, validate_config


class MockBackend:
    def __init__(self, config: Config):
        validate_config(config)
        if config.backend != "mock":
            raise ValueError("MockBackend requires backend=mock; no hardware fallback")
        self._config = replace(config)
        self._fault = config.fault
        scale = min(0.1, config.position_limit * 0.25)
        self._positions = [scale, -scale, 0.5 * scale, -0.5 * scale, 0.75 * scale, -0.75 * scale]
        self._commands = self._positions.copy()
        self._ramp_positions = self._commands.copy()
        self._ramp_started: Optional[float] = None
        self._last_time: Optional[float] = None
        self._integration_time: Optional[float] = None
        self._sequence = 0
        self._cached: Optional[Observation] = None

    def poll(self, now: float) -> Optional[Observation]:
        if not _finite_number(now):
            raise RuntimeError("invalid mock clock")
        if self._last_time is not None and now < self._last_time:
            raise RuntimeError("mock clock moved backward")
        if self._fault == "error":
            raise RuntimeError("injected mock backend error")
        if self._fault == "watchdog":
            raise RuntimeError("injected mock backend watchdog failure")
        if self._fault == "freeze":
            return None
        if self._fault == "repeat" and self._cached is not None:
            return copy.deepcopy(self._cached)
        if self._last_time is not None and now == self._last_time:
            return copy.deepcopy(self._cached)

        velocities = self._advance(now)
        self._last_time = now
        self._sequence += 1
        result = Observation(mock_joint_names(), self._positions.copy(), velocities, [], self._sequence, now)
        if self._fault == "nan":
            result.positions[0] = math.nan
        elif self._fault == "inf":
            result.positions[0] = math.inf
        elif self._fault == "invalid":
            result.positions.pop()
        self._cached = copy.deepcopy(result)
        return result

    def _advance(self, now: float) -> list[float]:
        if self._integration_time is not None and now < self._integration_time:
            raise RuntimeError("mock integration clock moved backward")
        velocities = [0.0] * len(self._positions)
        if self._integration_time is not None:
            elapsed = now - self._integration_time
            # Integrate the continuous command ramp, then its held endpoint.
            # No past commands or intermediate observations are replayed.
            ramp_end = (self._ramp_started + _MOCK_SOURCE_PERIOD
                        if self._ramp_started is not None else self._integration_time)
            ramp_dt = max(0.0, min(now, ramp_end) - self._integration_time)
            ramp_input = self._command_at(self._integration_time)
            tau = self._config.tracking_time_constant
            endpoint_input = self._command_at(now)
            for index, command in enumerate(self._commands):
                if self._fault != "timeout":
                    if ramp_dt > 0.0:
                        slope = (command - self._ramp_positions[index]) / _MOCK_SOURCE_PERIOD
                        alpha = -math.expm1(-ramp_dt / tau)
                        self._positions[index] += ((ramp_input[index] - self._positions[index]) * alpha
                                                   + slope * (ramp_dt - tau * alpha))
                    hold_dt = elapsed - ramp_dt
                    self._positions[index] += ((command - self._positions[index])
                                               * -math.expm1(-hold_dt / tau))
                    # Actual endpoint velocity of the first-order follower.
                    velocities[index] = (endpoint_input[index] - self._positions[index]) / tau
        self._integration_time = now
        return velocities

    def _command_at(self, now: float) -> list[float]:
        if self._ramp_started is None:
            return self._commands.copy()
        weight = min(1.0, max(0.0, (now - self._ramp_started) / _MOCK_SOURCE_PERIOD))
        return [start + weight * (end - start)
                for start, end in zip(self._ramp_positions, self._commands)]

    def command_positions(self, positions: Sequence[float], now: float) -> None:
        if (not _finite_number(now) or not isinstance(positions, (list, tuple))
                or len(positions) != len(self._positions)
                or any(not _finite_number(value) for value in positions)):
            raise ValueError("invalid mock command dimensions, clock or numbers")
        if any(abs(value) > self._config.position_limit for value in positions):
            raise ValueError("mock command exceeds position limit")
        # Integrate the previous input up to this event before replacing it.
        # This does not publish or fabricate a new source observation.
        self._advance(now)
        # Begin at the current ramp value if a short callback interrupts it.
        # This keeps command and follower velocity continuous without clamping
        # observed velocity/acceleration or changing the independent guards.
        self._ramp_positions = self._command_at(now)
        self._ramp_started = now
        self._commands = list(positions)

    def hold(self, now: float) -> None:
        # Stop at the actual simulated position; never schedule a return motion.
        self._ramp_started = None
        self._commands = self._positions.copy()

    def set_fault(self, fault: str) -> None:
        if not valid_fault(fault):
            raise ValueError(f"unknown mock fault: {fault}")
        self._fault = fault
