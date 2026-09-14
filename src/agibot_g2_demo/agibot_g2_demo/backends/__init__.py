"""Backend contracts; importing this package does not load a vendor SDK."""

from .base import Observation, RobotBackend

__all__ = ["Observation", "RobotBackend"]
