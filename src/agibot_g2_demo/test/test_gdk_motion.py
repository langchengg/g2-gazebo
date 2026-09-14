"""Project request-contract tests only; no SDK module or robot is impersonated."""

import ast
from dataclasses import replace
import inspect
import math
import sys
from unittest.mock import Mock

import pytest

from agibot_g2_demo.backends import gdk_motion
from agibot_g2_demo.backends.gdk_motion import (
    CONTRACT_STATUS, ConfirmedJointMapping, GdkMotionBlocked, HardwareMotionLimits,
    JointMotionPlan, MotionContractError, MotorFeedbackTracker, PerMotionAuthorization,
    build_joint_control_request, dispatch_joint_control_request, motion_plan_digest,
)

pytestmark = pytest.mark.unit

PROJECT_NAMES = ("project_motion_fixture_left", "project_motion_fixture_right")


class ProjectRequestRecord:
    """A strict project data record, not agibot_gdk.JointControlReq."""

    __slots__ = ("joint_names", "joint_positions", "joint_velocities", "life_time", "detail")


class ProjectRequestFactory:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return ProjectRequestRecord()


def project_mapping():
    return ConfirmedJointMapping(
        PROJECT_NAMES, "PROJECT_TEST_MODEL", "PROJECT_TEST_FIRMWARE",
        "project-fixture/motor-coordinate-review", "project-fixture/full-command-scope", True,
    )


def project_limits():
    return HardwareMotionLimits((-1.0, -1.0), (1.0, 1.0), (0.03, 0.03),
                                (0.1, 0.1), 2.0, 0.5, "project-fixture/limits-review")


def project_plan():
    return JointMotionPlan("project-run-unique", PROJECT_NAMES[0], (0.42, -0.2),
                           (0.02, 0.0), 1.0, "Project test only; no hardware")


def project_raw(timestamp):
    return {"timestamp": timestamp, "nums": 2, "states": [
        {"name": PROJECT_NAMES[1], "motor_position": -0.2, "position": 99.0, "error_code": 0},
        {"name": PROJECT_NAMES[0], "motor_position": 0.4, "position": 98.0, "error_code": 0},
    ]}


def project_authorization(plan, mapping, limits):
    return PerMotionAuthorization(plan.run_id, motion_plan_digest(plan, mapping, limits),
                                  "project-fixture/one-specific-motion-approval", 10.0, 11.0)


def project_inputs():
    mapping, limits, plan = project_mapping(), project_limits(), project_plan()
    feedback = MotorFeedbackTracker(mapping)
    feedback.observe(project_raw(1000), 10.0)
    feedback.observe(project_raw(2000), 10.1)
    return dict(plan=plan, mapping=mapping, limits=limits,
                authorization=project_authorization(plan, mapping, limits),
                feedback=feedback, now=10.2, request_factory=ProjectRequestFactory())


def test_constructs_exact_documented_fields_from_nonzero_actual_motor_mapping():
    inputs = project_inputs()
    already_loaded = "agibot_gdk" in sys.modules
    prepared = build_joint_control_request(**inputs)
    request = prepared.sdk_request
    assert inputs["request_factory"].calls == 1
    assert request.joint_names == list(PROJECT_NAMES)
    assert request.joint_positions == [0.42, -0.2]
    assert request.joint_velocities == [0.02, 0.0]
    assert request.life_time == 1.0 and type(request.life_time) is float
    assert request.detail == inputs["plan"].detail
    assert prepared.feedback.motor_positions == (0.4, -0.2)
    assert prepared.feedback.source_timestamp == 2000
    assert prepared.feedback.received_at == 10.1
    assert prepared.run_id == "project-run-unique"
    assert prepared.contract_status == CONTRACT_STATUS == "DOC_IMPLEMENTED / SDK_UNVERIFIED"
    assert ("agibot_gdk" in sys.modules) == already_loaded
    for undocumented in ("run_id", "acceleration", "duration", "control_mode", "cancel", "stop"):
        assert not hasattr(request, undocumented)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, True, "0.42"])
def test_nonnumeric_or_nonfinite_position_is_rejected_before_type_factory(bad):
    inputs = project_inputs()
    inputs["plan"] = replace(inputs["plan"], joint_positions=(bad, -0.2))
    with pytest.raises(MotionContractError):
        build_joint_control_request(**inputs)
    assert inputs["request_factory"].calls == 0


@pytest.mark.parametrize("changes", [
    {"joint_positions": ()}, {"joint_positions": (0.42,)},
    {"joint_velocities": (0.1,)}, {"joint_velocities": (math.nan, 0.0)},
    {"joint_velocities": (math.inf, 0.0)}, {"joint_velocities": (0.11, 0.0)},
    {"life_time": 0.0}, {"life_time": -1.0}, {"life_time": math.nan},
    {"life_time": math.inf}, {"life_time": True}, {"life_time": 2.1},
    {"detail": ""}, {"detail": "bad\ntext"}, {"target_joint": "NOT_A_CONFIRMED_JOINT"},
    {"run_id": ""}, {"joint_positions": (1.1, -0.2)},
])
def test_malformed_fields_or_limits_are_rejected_before_factory(changes):
    inputs = project_inputs()
    inputs["plan"] = replace(inputs["plan"], **changes)
    with pytest.raises(MotionContractError):
        build_joint_control_request(**inputs)
    assert inputs["request_factory"].calls == 0


@pytest.mark.parametrize("changes", [
    {"motor_position_mapping_confirmed": False}, {"motor_position_mapping_confirmed": 1},
    {"joint_names": ("mock_left_arm_joint1", "mock_right_arm_joint1")},
    {"joint_names": ("same", "same")}, {"joint_names": ()},
    {"evidence_reference": ""}, {"command_scope_reference": ""},
    {"robot_model": ""}, {"firmware_version": ""},
])
def test_incomplete_or_synthetic_mapping_is_rejected(changes):
    inputs = project_inputs()
    inputs["mapping"] = replace(inputs["mapping"], **changes)
    with pytest.raises(MotionContractError):
        build_joint_control_request(**inputs)
    assert inputs["request_factory"].calls == 0


@pytest.mark.parametrize("changes", [
    {"minimum_positions": (1.0, -1.0)}, {"maximum_positions": (math.inf, 1.0)},
    {"maximum_displacements": (0.0, 0.03)}, {"maximum_absolute_velocities": (-0.1, 0.1)},
    {"maximum_life_time": math.nan}, {"feedback_timeout": 0.0}, {"evidence_reference": ""},
])
def test_explicit_hardware_limits_are_required(changes):
    inputs = project_inputs()
    inputs["limits"] = replace(inputs["limits"], **changes)
    with pytest.raises(MotionContractError):
        build_joint_control_request(**inputs)
    assert inputs["request_factory"].calls == 0


@pytest.mark.parametrize("positions,reason", [
    ((0.4, -0.2), "nonzero displacement"),
    ((0.42, -0.19), "non-target positions"),
    ((0.44, -0.2), "displacement exceeds"),
    ((0.0, 0.0), "displacement exceeds"),
])
def test_motion_is_checked_against_fresh_nonzero_feedback(positions, reason):
    inputs = project_inputs()
    inputs["plan"] = replace(inputs["plan"], joint_positions=positions)
    inputs["authorization"] = project_authorization(inputs["plan"], inputs["mapping"], inputs["limits"])
    with pytest.raises(MotionContractError, match=reason):
        build_joint_control_request(**inputs)
    assert inputs["request_factory"].calls == 0


def test_explicit_negative_small_displacement_is_not_converted_to_zero_or_home():
    inputs = project_inputs()
    inputs["plan"] = replace(inputs["plan"], joint_positions=(0.38, -0.2))
    inputs["authorization"] = project_authorization(inputs["plan"], inputs["mapping"], inputs["limits"])
    assert build_joint_control_request(**inputs).sdk_request.joint_positions == [0.38, -0.2]


@pytest.mark.parametrize("authorization", [None, False, True])
def test_no_boolean_authorization_or_missing_authorization_can_construct_request(authorization):
    inputs = project_inputs()
    inputs["authorization"] = authorization
    with pytest.raises(MotionContractError, match="per-motion authorization"):
        build_joint_control_request(**inputs)
    assert inputs["request_factory"].calls == 0


@pytest.mark.parametrize("changes", [
    {"run_id": "different-run"}, {"plan_digest": "different-plan"},
    {"operator_reference": ""}, {"granted_at": 10.3}, {"expires_at": 10.2},
    {"expires_at": math.inf}, {"granted_at": math.nan},
])
def test_authorization_is_specific_and_time_bounded(changes):
    inputs = project_inputs()
    inputs["authorization"] = replace(inputs["authorization"], **changes)
    with pytest.raises(MotionContractError):
        build_joint_control_request(**inputs)
    assert inputs["request_factory"].calls == 0


@pytest.mark.parametrize("field,value", [
    ("joint_positions", (0.41, -0.2)), ("joint_velocities", (0.03, 0.0)),
    ("life_time", 1.1), ("detail", "changed request"), ("run_id", "next-project-run"),
])
def test_previous_authorization_does_not_cover_modified_plan(field, value):
    inputs = project_inputs()
    inputs["plan"] = replace(inputs["plan"], **{field: value})
    with pytest.raises(MotionContractError, match="authorization does not match"):
        build_joint_control_request(**inputs)
    assert inputs["request_factory"].calls == 0


@pytest.mark.parametrize("count", [0, 1])
def test_two_advancing_motor_samples_are_required(count):
    inputs = project_inputs()
    tracker = MotorFeedbackTracker(inputs["mapping"])
    if count:
        tracker.observe(project_raw(1000), 10.1)
    inputs["feedback"] = tracker
    with pytest.raises(MotionContractError, match="two advancing"):
        build_joint_control_request(**inputs)
    assert inputs["request_factory"].calls == 0


@pytest.mark.parametrize("timestamp", [1000, 2000])
def test_old_or_repeated_source_timestamp_latches_failure(timestamp):
    inputs = project_inputs()
    with pytest.raises(MotionContractError, match="did not advance"):
        inputs["feedback"].observe(project_raw(timestamp), 10.15)
    with pytest.raises(MotionContractError):
        inputs["feedback"].observe(project_raw(3000), 10.16)
    with pytest.raises(MotionContractError):
        build_joint_control_request(**inputs)
    assert inputs["request_factory"].calls == 0


@pytest.mark.parametrize("now", [10.0, 10.7, math.nan, math.inf])
def test_stale_or_invalid_local_time_rejects_without_factory(now):
    inputs = project_inputs()
    inputs["now"] = now
    with pytest.raises(MotionContractError):
        build_joint_control_request(**inputs)
    assert inputs["request_factory"].calls == 0


def test_reserved_position_cannot_replace_missing_motor_position():
    inputs = project_inputs()
    raw = project_raw(3000)
    del raw["states"][0]["motor_position"]
    with pytest.raises(MotionContractError, match="motor_position"):
        inputs["feedback"].observe(raw, 10.15)
    with pytest.raises(MotionContractError):
        build_joint_control_request(**inputs)
    assert inputs["request_factory"].calls == 0


def test_different_robot_mapping_cannot_reuse_feedback_evidence():
    inputs = project_inputs()
    inputs["mapping"] = replace(inputs["mapping"], robot_model="ANOTHER_PROJECT_TEST_MODEL")
    inputs["authorization"] = project_authorization(inputs["plan"], inputs["mapping"], inputs["limits"])
    with pytest.raises(MotionContractError, match="different confirmed mapping"):
        build_joint_control_request(**inputs)
    assert inputs["request_factory"].calls == 0


def test_actual_motor_position_outside_limits_rejects_request():
    inputs = project_inputs()
    raw = project_raw(3000)
    raw["states"][1]["motor_position"] = 1.1
    inputs["feedback"].observe(raw, 10.15)
    with pytest.raises(MotionContractError, match="actual motor_position"):
        build_joint_control_request(**inputs)
    assert inputs["request_factory"].calls == 0


def test_native_type_construction_failure_is_not_disguised_as_sdk_compatibility():
    inputs = project_inputs()
    inputs["request_factory"] = Mock(side_effect=TypeError("project fixture rejects construction"))
    with pytest.raises(MotionContractError, match="SDK_UNVERIFIED"):
        build_joint_control_request(**inputs)
    assert inputs["request_factory"].call_count == 1


def test_fully_authorized_prepared_request_still_cannot_dispatch():
    prepared = build_joint_control_request(**project_inputs())
    sender = Mock(return_value=0)
    with pytest.raises(GdkMotionBlocked, match="RUNTIME_BLOCKED"):
        dispatch_joint_control_request(prepared, sender)
    sender.assert_not_called()


def test_status_metadata_is_not_a_runtime_waiver(monkeypatch):
    prepared = build_joint_control_request(**project_inputs())
    sender = Mock(return_value=0)
    monkeypatch.setattr(gdk_motion, "CONTRACT_STATUS", "VERIFIED")
    monkeypatch.setattr(gdk_motion, "RUNTIME_BLOCKERS", ())
    with pytest.raises(GdkMotionBlocked):
        dispatch_joint_control_request(prepared, sender)
    with pytest.raises(TypeError):
        dispatch_joint_control_request(prepared, sender, enable_motion=True)
    sender.assert_not_called()


def test_dispatch_seam_contains_no_callable_send_path():
    tree = ast.parse(inspect.getsource(dispatch_joint_control_request))
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    assert not any(isinstance(call.func, ast.Name) and call.func.id == "sender" for call in calls)
    assert not any(isinstance(node, ast.Return) for node in ast.walk(tree))
    assert "Return is not acceptance" in gdk_motion.__doc__
