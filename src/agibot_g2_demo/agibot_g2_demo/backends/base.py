"""Project backend contract. None of these names are vendor GDK symbols."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, Sequence


@dataclass
class Observation:
    """One sample; empty velocity/effort arrays mean unavailable measurements.

    ``sample_time`` is injected local monotonic seconds for the mock backend.
    Hardware adapters must explicitly document their own clock mapping.
    """

    names: list[str] = field(default_factory=list)
    positions: list[float] = field(default_factory=list)
    velocities: list[float] = field(default_factory=list)
    efforts: list[float] = field(default_factory=list)
    sequence: int = 0
    sample_time: float = 0.0


class RobotBackend(Protocol):
    """Single-owner operations; wrappers serialize all calls.

    Implementations must bound each call. The pure mock performs no I/O, sleeps,
    worker threads, implicit reconnection, or hardware commands.
    """

    def poll(self, now: float) -> Optional[Observation]: ...

    def command_positions(self, positions: Sequence[float], now: float) -> None: ...

    def hold(self, now: float) -> None: ...

    def set_fault(self, fault: str) -> None: ...
