"""Project fixtures only: these tests do NOT load or impersonate a vendor SDK.

unittest is used so the same cases run with stdlib locally and pytest/colcon in
ROS. The real-process case exercises the project datagram/deadline boundary;
its worker is explicitly a project fixture, not agibot_gdk.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import math
import multiprocessing
from pathlib import Path
import socket
import struct
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agibot_g2_demo.backends.gdk_backend import (
    GdkBackend, GdkDataError, GdkUnavailable, MAX_PACKET_BYTES,
    _send_packet, inspect_elf, map_joint_states, preflight_gdk,
)


PROJECT_NAMES = ["project_fixture_left", "project_fixture_right"]


def project_observation_fixture():
    return {"timestamp": 9876543210, "nums": 2, "states": [
        {"name": PROJECT_NAMES[1], "motor_position": -0.2, "motor_velocity": -0.3,
         "position": 99.0, "velocity": 98.0, "effort": 97.0, "error_code": 0},
        {"name": PROJECT_NAMES[0], "motor_position": 0.4, "motor_velocity": 0.5,
         "position": 96.0, "velocity": 95.0, "effort": 94.0, "error_code": 0},
    ]}


def project_packet(timestamp=10):
    return {"kind": "observation", "timestamp": timestamp, "names": PROJECT_NAMES,
            "positions": [0.4, -0.2], "velocities": []}


class ProjectProcessFixture:
    def __init__(self):
        self.alive = True
        self.terminated = False

    def is_alive(self):
        return self.alive

    def terminate(self):
        self.terminated = True
        self.alive = False

    def kill(self):
        self.alive = False

    def join(self, timeout=None):
        return None


def project_transport_worker(channel, hang=False):
    """An explicitly project-named fixture; contains zero vendor imports/calls."""
    _send_packet(channel, {"kind": "ready"})
    sequence = 0
    while True:
        command = json.loads(channel.recv(MAX_PACKET_BYTES))
        if hang:
            time.sleep(10)  # Parent must bound/terminate this fixture.
        if command["kind"] == "shutdown":
            _send_packet(channel, {"kind": "closed", "release_status": "PROJECT_FIXTURE_ACK"})
            channel.close()
            return
        sequence += 1
        _send_packet(channel, project_packet(sequence))


class MappingTests(unittest.TestCase):
    def test_documented_motor_fields_order_and_units(self):
        mapped = map_joint_states(project_observation_fixture(), PROJECT_NAMES)
        self.assertEqual(mapped.names, PROJECT_NAMES)
        self.assertEqual(mapped.positions, [0.4, -0.2])
        self.assertEqual(mapped.velocities, [0.5, -0.3])
        self.assertEqual(mapped.efforts, [])
        self.assertEqual(mapped.source_timestamp, 9876543210)

    def test_unknown_velocities_remain_empty(self):
        raw = project_observation_fixture()
        for state in raw["states"]:
            del state["motor_velocity"]
        self.assertEqual(map_joint_states(raw, PROJECT_NAMES).velocities, [])

    def test_reserved_fields_do_not_replace_missing_actual_position(self):
        raw = project_observation_fixture()
        del raw["states"][0]["motor_position"]
        with self.assertRaises(GdkDataError):
            map_joint_states(raw, PROJECT_NAMES)

    def test_reserved_fields_are_not_measured_values(self):
        raw = project_observation_fixture()
        for state in raw["states"]:
            state.update(position=math.nan, velocity=math.inf, effort=math.nan)
        self.assertEqual(map_joint_states(raw, PROJECT_NAMES).positions, [0.4, -0.2])
        self.assertEqual(map_joint_states(raw, PROJECT_NAMES).efforts, [])

    def test_bad_positions_and_velocities(self):
        for field in ("motor_position", "motor_velocity"):
            for value in (math.nan, math.inf, -math.inf, None, "0.1", True, []):
                with self.subTest(field=field, value=value):
                    raw = project_observation_fixture()
                    raw["states"][0][field] = value
                    with self.assertRaises(GdkDataError):
                        map_joint_states(raw, PROJECT_NAMES)

    def test_partial_velocity_is_rejected(self):
        raw = project_observation_fixture()
        del raw["states"][0]["motor_velocity"]
        with self.assertRaises(GdkDataError):
            map_joint_states(raw, PROJECT_NAMES)

    def test_bad_observation_structure(self):
        for raw in (None, [], {}, {"timestamp": 1, "nums": 0, "states": []}):
            with self.subTest(raw=raw), self.assertRaises(GdkDataError):
                map_joint_states(raw, PROJECT_NAMES)

    def test_bad_count_and_state_arrays(self):
        for count in (True, -1, 0, 1, 3, 2.0, None):
            raw = project_observation_fixture()
            raw["nums"] = count
            with self.subTest(count=count), self.assertRaises(GdkDataError):
                map_joint_states(raw, PROJECT_NAMES)
        for states in (None, {}, (), [None, None]):
            raw = project_observation_fixture()
            raw["states"] = states
            with self.subTest(states=states), self.assertRaises(GdkDataError):
                map_joint_states(raw, PROJECT_NAMES)

    def test_timestamp_types_and_bounds(self):
        for timestamp in (True, None, "100", 0, -1, 1.0, 2**64):
            raw = project_observation_fixture()
            raw["timestamp"] = timestamp
            with self.subTest(timestamp=timestamp), self.assertRaises(GdkDataError):
                map_joint_states(raw, PROJECT_NAMES)

    def test_unknown_and_duplicate_source_names(self):
        for name in (None, "another_project_fixture", PROJECT_NAMES[0]):
            raw = project_observation_fixture()
            raw["states"][0]["name"] = name
            with self.subTest(name=name), self.assertRaises(GdkDataError):
                map_joint_states(raw, PROJECT_NAMES)

    def test_invalid_expected_mapping(self):
        for names in ([], None, ["x", "x"], ["", "y"], ["x\ny", "z"],
                      ["x" * 129, "z"], [" x", "y"], [1, "y"]):
            with self.subTest(names=names), self.assertRaises(GdkDataError):
                map_joint_states(project_observation_fixture(), names)

    def test_error_codes_fail_closed(self):
        for code in (1, 12560, -1, None, False, "0", 0.0):
            raw = project_observation_fixture()
            raw["states"][0]["error_code"] = code
            with self.subTest(code=code), self.assertRaises(GdkDataError):
                map_joint_states(raw, PROJECT_NAMES)

    def test_input_is_not_modified(self):
        raw = project_observation_fixture()
        original = copy.deepcopy(raw)
        map_joint_states(raw, PROJECT_NAMES)
        self.assertEqual(raw, original)


class PreflightTests(unittest.TestCase):
    def test_import_and_missing_config_do_not_import_native_binding(self):
        with patch("builtins.__import__", side_effect=AssertionError("unexpected native import")):
            with self.assertRaisesRegex(GdkUnavailable, "sdk_config_path"):
                preflight_gdk()

    def test_version_override_is_not_adapter_verification(self):
        with self.assertRaisesRegex(GdkUnavailable, "VERSION_MISMATCH"):
            preflight_gdk(expected_sdk_version="2.4.2")

    def test_project_config_requires_explicit_read_only_authorization(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "project_config.json"
            path.write_text(json.dumps({"allow_read_only_connection": False}))
            with self.assertRaisesRegex(GdkUnavailable, "READ_ONLY_AUTHORIZATION_REQUIRED"):
                preflight_gdk(str(path))

    def test_project_config_requires_coordinate_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "project_config.json"
            path.write_text(json.dumps({"allow_read_only_connection": True}))
            with self.assertRaisesRegex(GdkUnavailable, "MAPPING_UNVERIFIED"):
                preflight_gdk(str(path))

    def test_missing_binding_fails_without_import_init_or_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "project_config.json"
            path.write_text(json.dumps({"allow_read_only_connection": True,
                                       "motor_position_mapping_confirmed": True,
                                       "sdk_root": directory, "joint_names": PROJECT_NAMES}))
            with patch.object(importlib.util, "find_spec", return_value=None):
                with self.assertRaisesRegex(GdkUnavailable, "actual agibot_gdk binding not found"):
                    preflight_gdk(str(path))

    def test_invalid_timeout_fails_before_starting_worker(self):
        for timeout in (-1, 0, True, math.nan, math.inf, 61):
            with self.subTest(timeout=timeout), self.assertRaises(GdkUnavailable):
                GdkBackend(sdk_config_path="", poll_timeout=timeout)

    def test_missing_distribution_metadata_fails_without_version_guess(self):
        self.check_project_metadata_fixture([], None, "VERSION_UNVERIFIED")

    def test_matching_distribution_version_does_not_prove_product_version(self):
        message = self.check_project_metadata_fixture(
            ["project_fixture_distribution"], "2.6.3", "VERSION_MAPPING_UNVERIFIED")
        self.assertIn("matching version text does not establish product compatibility", message)
        self.assertIn("'2.6.3'", message)

    def test_different_distribution_version_does_not_prove_incompatibility(self):
        message = self.check_project_metadata_fixture(
            ["project_fixture_distribution"], "2.4.2", "VERSION_MAPPING_UNVERIFIED")
        self.assertIn("different version text cannot determine product compatibility", message)
        self.assertIn("'2.4.2'", message)
        self.assertIn("'2.6.3'", message)

    def check_project_metadata_fixture(self, providers, version, expected_error):
        # Mock only standard-library metadata lookups. No vendor module is
        # created, imported or injected into sys.modules; no positive SDK claim.
        with tempfile.TemporaryDirectory() as directory:
            origin = Path(directory) / "project_location_fixture.txt"
            origin.write_text("project metadata test, not an SDK binding")
            path = Path(directory) / "project_config.json"
            path.write_text(json.dumps({"allow_read_only_connection": True,
                                       "motor_position_mapping_confirmed": True,
                                       "sdk_root": directory, "joint_names": PROJECT_NAMES}))
            real_import = __import__
            native_imports = []

            def reject_native_import(name, *args, **kwargs):
                if name == "agibot_gdk" or name.startswith("agibot_gdk."):
                    native_imports.append(name)
                    raise AssertionError("preflight must not import native SDK")
                return real_import(name, *args, **kwargs)

            with patch.object(importlib.util, "find_spec", return_value=SimpleNamespace(origin=str(origin))), \
                 patch("importlib.metadata.packages_distributions", return_value={"agibot_gdk": providers}), \
                 patch("importlib.metadata.version", return_value=version), \
                 patch("builtins.__import__", side_effect=reject_native_import), \
                 patch.object(multiprocessing, "get_context",
                              side_effect=AssertionError("must not start SDK worker")) as worker:
                for entry in (lambda: preflight_gdk(str(path)),
                              lambda: GdkBackend(sdk_config_path=str(path))):
                    with self.assertRaisesRegex(GdkUnavailable, expected_error) as caught:
                        entry()
                self.assertEqual(native_imports, [])
                worker.assert_not_called()
                return str(caught.exception)

    def test_project_elf_header_fixture_is_classification_not_sdk_load(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "project_header_fixture.data"
            for machine, arch in ((183, "aarch64"), (62, "x86_64")):
                header = bytearray(64)
                header[:6] = b"\x7fELF\x02\x01"
                header[18:20] = struct.pack("<H", machine)
                path.write_bytes(header)
                self.assertEqual(inspect_elf(path)["architecture"], arch)
                self.assertEqual(inspect_elf(path)["bits"], 64)
            path.write_text("not a vendor binary")
            with self.assertRaisesRegex(GdkUnavailable, "not an ELF"):
                inspect_elf(path)


class DatagramTests(unittest.TestCase):
    def setUp(self):
        self.backend = GdkBackend.__new__(GdkBackend)
        self.backend.metadata = {"joint_names": PROJECT_NAMES}
        self.backend._configure(0.5, 2.0, 10.0)
        self.backend._channel, self.peer = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.backend._channel.setblocking(False)
        self.peer.settimeout(0.1)
        self.backend._worker = ProjectProcessFixture()

    def tearDown(self):
        self.backend.shutdown(12.0)
        self.peer.close()

    def ready(self):
        _send_packet(self.peer, {"kind": "ready"})
        self.assertIsNone(self.backend.poll(10.0))
        self.assertEqual(json.loads(self.peer.recv(1024)), {"kind": "poll"})

    def observation(self, stamp=10, now=10.1):
        _send_packet(self.peer, project_packet(stamp))
        result = self.backend.poll(now)
        if not self.backend._fault:
            self.assertEqual(json.loads(self.peer.recv(1024)), {"kind": "poll"})
        return result

    def test_receive_clock_is_local_and_source_clock_is_preserved(self):
        self.ready()
        result = self.observation(stamp=999999999999999999)
        self.assertEqual(result.sample_time, 10.1)
        self.assertEqual(result.sequence, 1)
        self.assertEqual(self.backend.last_source_timestamp, 999999999999999999)
        self.assertEqual(result.efforts, [])
        self.assertTrue(self.backend.healthy(10.2))

    def test_repeated_cache_never_gets_new_time_or_sequence(self):
        self.ready()
        self.observation()
        self.assertIsNone(self.observation(stamp=10, now=10.2))
        self.assertEqual(self.backend._last_progress, 10.1)
        self.assertEqual(self.backend._sequence, 1)
        self.assertIsNone(self.observation(stamp=10, now=10.5))
        self.assertIsNone(self.backend.poll(10.61))
        self.assertIn("SOURCE_STALE", self.backend.health_reason(10.61))

    def test_backward_source_time_faults_without_restart(self):
        self.ready()
        self.observation(stamp=10)
        self.assertIsNone(self.observation(stamp=9, now=10.2))
        self.assertIn("timestamp moved backward", self.backend.health_reason(10.2))
        self.assertTrue(self.backend._worker.terminated)
        self.assertIsNone(self.backend.poll(10.3))

    def test_poll_timeout_rejects_even_a_queued_overdue_reply(self):
        self.ready()
        _send_packet(self.peer, project_packet())
        self.assertIsNone(self.backend.poll(10.51))
        self.assertIn("POLL_TIMEOUT", self.backend.health_reason(10.51))
        self.assertEqual(self.backend._sequence, 0)

    def test_startup_timeout(self):
        self.assertIsNone(self.backend.poll(12.01))
        self.assertIn("STARTUP_TIMEOUT", self.backend.health_reason(12.01))

    def test_only_one_pending_poll_no_queue(self):
        self.ready()
        for now in (10.01, 10.02, 10.03):
            self.assertIsNone(self.backend.poll(now))
        with self.assertRaises(socket.timeout):
            self.peer.recv(1024)

    def test_sdk_error_cannot_be_success(self):
        self.ready()
        _send_packet(self.peer, {"kind": "error", "reason": "project fixture failure"})
        self.assertIsNone(self.backend.poll(10.1))
        self.assertFalse(self.backend.healthy(10.1))
        self.assertIn("fixture failure", self.backend.health_reason(10.1))
        _send_packet(self.peer, {"kind": "closed", "release_status": "NOT_INITIALIZED: release not called"})
        self.backend.shutdown(10.1)
        self.assertEqual(self.backend.release_status, "NOT_INITIALIZED: release not called")

    def test_invalid_transport_data(self):
        self.ready()
        packet = project_packet()
        packet["positions"] = [math.nan, 0]
        # Test receiving nonconforming external JSON; normal sender forbids NaN.
        self.peer.send(json.dumps(packet).encode())
        self.assertIsNone(self.backend.poll(10.1))
        self.assertIn("invalid mapped", self.backend.health_reason(10.1))

    def test_motion_and_hold_are_never_vendor_commands(self):
        with self.assertRaisesRegex(GdkUnavailable, "UNIMPLEMENTED"):
            self.backend.command_positions([0, 0], 10.0)
        with self.assertRaisesRegex(GdkUnavailable, "no verified GDK hold/stop"):
            self.backend.hold(10.0)
        with self.assertRaises(socket.timeout):
            self.peer.recv(1024)

    def test_watchdog_invalid_clock(self):
        self.assertIsNone(self.backend.poll(math.nan))
        self.assertIn("WATCHDOG", self.backend.health_reason(10.1))

    def test_shutdown_is_bounded_and_idempotent(self):
        started = time.monotonic()
        self.backend.shutdown(10.0)
        self.backend.shutdown(10.0)
        self.assertLess(time.monotonic() - started, 0.1)
        self.assertTrue(self.backend._worker.terminated)
        self.assertIn("UNVERIFIED", self.backend.release_status)

    def test_unexpected_worker_exit(self):
        self.backend._worker.alive = False
        self.assertIsNone(self.backend.poll(10.1))
        self.assertIn("worker exited", self.backend.health_reason(10.1))


class SpawnTransportTests(unittest.TestCase):
    def test_real_spawn_datagram_and_graceful_cleanup_project_fixture(self):
        self.run_transport_fixture(hang=False)

    def test_real_spawn_stuck_worker_does_not_block_parent_project_fixture(self):
        self.run_transport_fixture(hang=True)

    def run_transport_fixture(self, hang):
        backend = GdkBackend.__new__(GdkBackend)
        backend.metadata = {"joint_names": PROJECT_NAMES}
        backend._configure(0.1, 3.0, time.monotonic())
        backend._channel, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
        backend._channel.setblocking(False)
        backend._worker = multiprocessing.get_context("spawn").Process(
            target=project_transport_worker, args=(child, hang), daemon=True)
        backend._worker.start()
        child.close()
        try:
            deadline = time.monotonic() + 3.5
            sample = None
            while time.monotonic() < deadline:
                before = time.monotonic()
                sample = backend.poll(before)
                # Container scheduling allowance; the fixture's native-style
                # hang lasts 10 s, so this still detects executor blocking.
                self.assertLess(time.monotonic() - before, 0.25)
                if sample is not None or backend._fault:
                    break
                time.sleep(0.002)
            if hang:
                self.assertIsNone(sample)
                self.assertIn("POLL_TIMEOUT", backend.health_reason(time.monotonic()))
            else:
                self.assertIsNotNone(sample)
                self.assertEqual(sample.names, PROJECT_NAMES)
        finally:
            before = time.monotonic()
            backend.shutdown(before)
            self.assertLess(time.monotonic() - before, 1.0)
            self.assertFalse(backend._worker.is_alive())
            if not hang:
                self.assertEqual(backend.release_status, "PROJECT_FIXTURE_ACK")


if __name__ == "__main__":
    unittest.main()
