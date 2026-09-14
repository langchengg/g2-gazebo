"""Document-derived GDK 2.6.3 request construction; runtime motion is BLOCKED.

Evidence: Python Robot section 7, ``joint_control_request``; Python Types,
``JointControlReq``. The documented call blocks until the target is reached,
returns integer 0 on success, and raises on failure. Return is not acceptance.

Only these SDK data fields are constructed: joint_names, joint_positions (rad),
joint_velocities (rad/s), life_time (seconds), detail. Everything else in this
module is a project contract. It imports no SDK and cannot send a motion.

Canonical sources:
https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/robot.md
https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/types.md
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any, Callable, Optional

from .gdk_backend import GdkDataError, MAX_JOINTS, MAX_NAME_BYTES, map_joint_states


CONTRACT_STATUS = "DOC_IMPLEMENTED / SDK_UNVERIFIED"
RUNTIME_BLOCKERS = (
    "actual GDK 2.6.3 request type, binding ABI and firmware compatibility unverified",
    "blocking call concurrency, GIL behavior and simultaneous feedback access not documented",
    "bounded cancellation/stop/hold behavior and disconnect behavior not documented",
    "command scope, velocity sign/zero semantics and life_time expiry behavior unverified",
    "device sampling-time mapping and on-site control/safety conditions unverified",
)


class MotionContractError(ValueError):
    """Project request inputs or observation evidence are incomplete/invalid."""


class GdkMotionBlocked(RuntimeError):
    """Runtime remains blocked independently of input authorization."""


@dataclass(frozen=True)
class ConfirmedJointMapping:
    """Explicit inspected mapping; there are no hardware joint defaults."""

    joint_names: tuple[str, ...]
    robot_model: str
    firmware_version: str
    evidence_reference: str
    command_scope_reference: str
    motor_position_mapping_confirmed: bool


@dataclass(frozen=True)
class HardwareMotionLimits:
    """Caller-supplied project constraints, never inferred vendor limits."""

    minimum_positions: tuple[float, ...]
    maximum_positions: tuple[float, ...]
    maximum_displacements: tuple[float, ...]
    maximum_absolute_velocities: tuple[float, ...]
    maximum_life_time: float
    feedback_timeout: float
    evidence_reference: str


@dataclass(frozen=True)
class JointMotionPlan:
    """One explicitly specified target; all vector values are supplied by caller.

    Non-target positions must equal fresh motor_position feedback. This module
    never fills missing values with zero or invents velocity/trajectory fields.
    ``run_id`` is exclusively a project identifier, not a vendor task ID.
    """

    run_id: str
    target_joint: str
    joint_positions: tuple[float, ...]
    joint_velocities: tuple[float, ...]
    life_time: float
    detail: str


@dataclass(frozen=True)
class PerMotionAuthorization:
    """Review evidence bound to one exact plan, mapping and limit set.

    Local monotonic validity times are project metadata. They are not written
    into the SDK request, and cannot waive runtime blockers.
    """

    run_id: str
    plan_digest: str
    operator_reference: str
    granted_at: float
    expires_at: float


@dataclass(frozen=True)
class MotorFeedbackEvidence:
    joint_names: tuple[str, ...]
    motor_positions: tuple[float, ...]
    source_timestamp: int
    received_at: float
    mapping_reference: str


@dataclass(frozen=True)
class PreparedJointControlRequest:
    run_id: str
    plan_digest: str
    sdk_request: Any
    feedback: MotorFeedbackEvidence
    contract_status: str = CONTRACT_STATUS


def _finite(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _text(value: Any, label: str) -> None:
    if not isinstance(value, str):
        raise MotionContractError(f"{label} must be explicit, bounded nonempty text")
    try:
        encoded_length = len(value.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise MotionContractError(f"{label} is not valid UTF-8 text") from error
    if (not value or value.strip() != value or encoded_length > 4096
            or any(ord(char) < 32 for char in value)):
        raise MotionContractError(f"{label} must be explicit, bounded nonempty text")


def _validate_mapping(mapping: ConfirmedJointMapping) -> None:
    if not isinstance(mapping, ConfirmedJointMapping):
        raise MotionContractError("confirmed mapping is required")
    names = mapping.joint_names
    if not isinstance(names, tuple) or not 1 <= len(names) <= MAX_JOINTS:
        raise MotionContractError("joint_names must be an explicit immutable mapping")
    for name in names:
        _text(name, "joint name")
        if len(name.encode("utf-8")) > MAX_NAME_BYTES or name.startswith("mock_"):
            raise MotionContractError("mock or oversized names cannot be hardware mapping evidence")
    if len(set(names)) != len(names):
        raise MotionContractError("duplicate mapped joint names")
    for field in ("robot_model", "firmware_version", "evidence_reference", "command_scope_reference"):
        _text(getattr(mapping, field), field)
    if mapping.motor_position_mapping_confirmed is not True:
        raise MotionContractError("motor_position coordinate mapping is unconfirmed")


def _vector(values: Any, count: int, label: str, positive: bool = False) -> None:
    if (not isinstance(values, tuple) or len(values) != count
            or any(not _finite(value) or (positive and value <= 0) for value in values)):
        raise MotionContractError(f"{label} requires {count} finite explicit values")


def _validate_plan(plan: JointMotionPlan, mapping: ConfirmedJointMapping,
                   limits: HardwareMotionLimits) -> None:
    _validate_mapping(mapping)
    if not isinstance(plan, JointMotionPlan) or not isinstance(limits, HardwareMotionLimits):
        raise MotionContractError("explicit plan and hardware limits are required")
    _text(plan.run_id, "project run_id")
    _text(plan.detail, "detail")
    if plan.target_joint not in mapping.joint_names:
        raise MotionContractError("target joint is outside the confirmed mapping")
    count = len(mapping.joint_names)
    _vector(plan.joint_positions, count, "joint_positions")
    _vector(plan.joint_velocities, count, "joint_velocities")
    _vector(limits.minimum_positions, count, "minimum_positions")
    _vector(limits.maximum_positions, count, "maximum_positions")
    _vector(limits.maximum_displacements, count, "maximum_displacements", positive=True)
    _vector(limits.maximum_absolute_velocities, count, "maximum_absolute_velocities", positive=True)
    _text(limits.evidence_reference, "limits evidence_reference")
    for label, value in (("life_time", plan.life_time), ("maximum_life_time", limits.maximum_life_time),
                         ("feedback_timeout", limits.feedback_timeout)):
        if not _finite(value) or value <= 0:
            raise MotionContractError(f"{label} must be explicitly finite and positive")
    if plan.life_time > limits.maximum_life_time:
        raise MotionContractError("life_time exceeds approved project limit")
    for index, position in enumerate(plan.joint_positions):
        lower, upper = limits.minimum_positions[index], limits.maximum_positions[index]
        if lower >= upper or not lower <= position <= upper:
            raise MotionContractError("invalid limits or target outside approved position range")
        if abs(plan.joint_velocities[index]) > limits.maximum_absolute_velocities[index]:
            raise MotionContractError("joint_velocities exceeds approved project limit")


def motion_plan_digest(plan: JointMotionPlan, mapping: ConfirmedJointMapping,
                       limits: HardwareMotionLimits) -> str:
    """Bind authorization to every submitted field and its reviewed constraints."""
    _validate_plan(plan, mapping, limits)
    payload = {"documented_version": "2.6.3", "plan": asdict(plan),
               "mapping": asdict(mapping), "project_limits": asdict(limits)}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class MotorFeedbackTracker:
    """Require two advancing validated motor-position observations.

    This establishes local receive freshness and source-marker progression
    only. The opaque device nanoseconds do NOT establish hardware sample age.
    Invalid, repeated or backward observations latch this evidence collector.
    """

    def __init__(self, mapping: ConfirmedJointMapping):
        _validate_mapping(mapping)
        self._mapping = mapping
        self._last: Optional[MotorFeedbackEvidence] = None
        self._advances = 0
        self._fault = ""

    @property
    def mapping(self) -> ConfirmedJointMapping:
        return self._mapping

    def observe(self, raw: Any, received_at: float) -> None:
        if self._fault:
            raise MotionContractError(self._fault)
        try:
            if not _finite(received_at):
                raise MotionContractError("invalid local receive time")
            mapped = map_joint_states(raw, list(self._mapping.joint_names))
            if self._last is not None:
                if received_at < self._last.received_at:
                    raise MotionContractError("local receive time moved backward")
                if mapped.source_timestamp <= self._last.source_timestamp:
                    raise MotionContractError("source timestamp did not advance")
            self._last = MotorFeedbackEvidence(tuple(mapped.names), tuple(mapped.positions),
                                              mapped.source_timestamp, received_at,
                                              self._mapping.evidence_reference)
            self._advances += 1
        except (GdkDataError, MotionContractError) as error:
            self._fault = str(error)
            raise MotionContractError(self._fault) from error

    def fresh(self, now: float, timeout: float) -> MotorFeedbackEvidence:
        if self._fault:
            raise MotionContractError(self._fault)
        if not _finite(timeout) or timeout <= 0 or not _finite(now):
            raise MotionContractError("invalid project freshness clock or timeout")
        if self._last is None or self._advances < 2:
            raise MotionContractError("two advancing motor_position observations are required")
        if now < self._last.received_at or now - self._last.received_at > timeout:
            raise MotionContractError("motor_position feedback is stale or local clock moved backward")
        return self._last


def build_joint_control_request(*, plan: JointMotionPlan, mapping: ConfirmedJointMapping,
                                limits: HardwareMotionLimits,
                                authorization: PerMotionAuthorization,
                                feedback: MotorFeedbackTracker, now: float,
                                request_factory: Callable[[], Any]) -> PreparedJointControlRequest:
    """Construct the five documented fields after validation; never dispatch.

    Supply the inspected real ``agibot_gdk.JointControlReq`` type as factory only
    in an authorized SDK environment. Project test records validate this module,
    not native SDK compatibility. No SDK field is invented for acceleration,
    run_id, control mode, cancellation, or trajectory duration.
    """
    digest = motion_plan_digest(plan, mapping, limits)
    if not isinstance(authorization, PerMotionAuthorization):
        raise MotionContractError("explicit per-motion authorization is required")
    _text(authorization.operator_reference, "operator_reference")
    if authorization.run_id != plan.run_id or authorization.plan_digest != digest:
        raise MotionContractError("authorization does not match this exact run/plan/mapping/limits")
    if (not _finite(now) or not _finite(authorization.granted_at) or not _finite(authorization.expires_at)
            or authorization.granted_at > now or now >= authorization.expires_at
            or authorization.expires_at <= authorization.granted_at):
        raise MotionContractError("per-motion authorization is expired or not yet valid")
    if not isinstance(feedback, MotorFeedbackTracker):
        raise MotionContractError("advancing motor_position feedback evidence is required")
    observed = feedback.fresh(now, limits.feedback_timeout)
    if (feedback.mapping != mapping or observed.joint_names != mapping.joint_names
            or observed.mapping_reference != mapping.evidence_reference):
        raise MotionContractError("feedback uses a different confirmed mapping")
    target_index = mapping.joint_names.index(plan.target_joint)
    for index, (actual, target) in enumerate(zip(observed.motor_positions, plan.joint_positions)):
        if not limits.minimum_positions[index] <= actual <= limits.maximum_positions[index]:
            raise MotionContractError("actual motor_position is outside approved limits")
        displacement = target - actual
        if not math.isfinite(displacement) or abs(displacement) > limits.maximum_displacements[index]:
            raise MotionContractError("target displacement exceeds approved project limit")
        if index != target_index and displacement != 0.0:
            raise MotionContractError("non-target positions must explicitly preserve fresh motor_position")
        if index == target_index and displacement == 0.0:
            raise MotionContractError("the authorized target joint must have a nonzero displacement")
    if not callable(request_factory):
        raise MotionContractError("an inspected SDK request type factory is required")
    try:
        request = request_factory()
        request.joint_names = list(mapping.joint_names)
        request.joint_positions = [float(value) for value in plan.joint_positions]
        request.joint_velocities = [float(value) for value in plan.joint_velocities]
        request.life_time = float(plan.life_time)
        request.detail = plan.detail
    except Exception as error:
        raise MotionContractError(f"SDK_UNVERIFIED: request type/fields could not be constructed: {error}") from error
    return PreparedJointControlRequest(plan.run_id, digest, request, observed)


def dispatch_joint_control_request(prepared: PreparedJointControlRequest,
                                   sender: Callable[[Any], int]) -> None:
    """Named integration seam that ALWAYS raises before any SDK sender call.

    There is deliberately no enable/waiver argument and no sender invocation.
    Resolving the documented blockers requires a reviewed implementation change,
    inspected SDK and on-site authorization; constructing a valid request is not it.
    No acceptance or SUCCEEDED result is manufactured by this module.
    """
    raise GdkMotionBlocked("RUNTIME_BLOCKED: " + "; ".join(RUNTIME_BLOCKERS))
