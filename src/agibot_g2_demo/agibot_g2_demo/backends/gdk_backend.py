"""Document-derived GDK 2.6.3 read-only adapter; SDK_UNVERIFIED.

Only the worker imports the real ``agibot_gdk`` binding. This file is not a
replacement SDK. See docs/gdk_python_review.md for evidence and remaining gates.
No vendor motion, mode-switch, fault-reset or stop symbol is called here.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.metadata
import importlib.util
import json
import math
import multiprocessing
from pathlib import Path
import platform
import socket
import struct
import sys
import time
from typing import Any, Optional

from .base import Observation


# These are project input/IPC bounds, NOT claimed GDK or robot limits.
MAX_JOINTS = 128
MAX_NAME_BYTES = 128
MAX_PACKET_BYTES = 65507
EXPECTED_VERSION = "2.6.3"


class GdkUnavailable(RuntimeError):
    """Preflight or isolated read-only runtime could not be verified."""


class GdkDataError(ValueError):
    """Documented fields are missing, malformed, inconsistent or faulted."""


def _finite(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _names(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)) or not 1 <= len(value) <= MAX_JOINTS:
        raise GdkDataError("joint_names must contain 1..128 approved names")
    result = list(value)
    if any(not isinstance(name, str) or not name or name.strip() != name
           or len(name.encode("utf-8")) > MAX_NAME_BYTES
           or any(ord(char) < 32 for char in name) for name in result):
        raise GdkDataError("joint_names contains an invalid name")
    if len(set(result)) != len(result):
        raise GdkDataError("joint_names contains duplicates")
    return result


@dataclass(frozen=True)
class MappedJointState:
    """Project representation; timestamp remains opaque vendor nanoseconds."""

    source_timestamp: int
    names: list[str]
    positions: list[float]
    velocities: list[float]
    efforts: list[float]


def map_joint_states(raw: Any, expected_joint_names: list[str]) -> MappedJointState:
    """Validate Python Robot.get_joint_states() without importing the SDK.

    The official Robot page explicitly chooses motor_position/motor_velocity.
    Reserved position/velocity and unverified effort are deliberately unused.
    All actual names must match the approved full observation mapping; data is
    reordered by that mapping, never by an assumed G2 index or source ordering.
    """
    expected = _names(expected_joint_names)
    if not isinstance(raw, dict):
        raise GdkDataError("get_joint_states must return dict")
    timestamp, count, states = raw.get("timestamp"), raw.get("nums"), raw.get("states")
    if type(timestamp) is not int or not 0 < timestamp < 2**64:
        raise GdkDataError("timestamp must be positive integer nanoseconds")
    if (type(count) is not int or count != len(expected)
            or not isinstance(states, list) or len(states) != count):
        raise GdkDataError("nums/states/approved joint count mismatch")
    by_name: dict[str, dict] = {}
    for state in states:
        if not isinstance(state, dict):
            raise GdkDataError("each states entry must be dict")
        name = state.get("name")
        if not isinstance(name, str) or name not in expected or name in by_name:
            raise GdkDataError("unexpected or duplicate observed joint name")
        code = state.get("error_code")
        if type(code) is not int or code < 0:
            raise GdkDataError("error_code missing or invalid")
        if code != 0:
            raise GdkDataError(f"joint reports nonzero error_code ({code})")
        if not _finite(state.get("motor_position")):
            raise GdkDataError("motor_position missing or non-finite")
        by_name[name] = state
    ordered = [by_name[name] for name in expected]
    velocity_presence = ["motor_velocity" in state for state in ordered]
    if any(velocity_presence) and not all(velocity_presence):
        raise GdkDataError("partial motor_velocity array")
    velocities: list[float] = []
    if all(velocity_presence):
        if any(not _finite(state["motor_velocity"]) for state in ordered):
            raise GdkDataError("motor_velocity is non-finite or invalid")
        velocities = [float(state["motor_velocity"]) for state in ordered]
    return MappedJointState(timestamp, expected,
                            [float(state["motor_position"]) for state in ordered],
                            velocities, [])


def inspect_elf(path: Path) -> dict[str, Any]:
    """Read only the ELF header; never load/execute the supplied file."""
    with path.open("rb") as stream:
        header = stream.read(64)
    if len(header) < 20 or header[:4] != b"\x7fELF":
        raise GdkUnavailable(f"ARCH_UNVERIFIED: not an ELF shared object: {path}")
    if header[4] not in (1, 2) or header[5] not in (1, 2):
        raise GdkUnavailable(f"ARCH_UNVERIFIED: invalid ELF header: {path}")
    machine = struct.unpack(("<" if header[5] == 1 else ">") + "H", header[18:20])[0]
    return {"path": str(path), "bits": 32 if header[4] == 1 else 64,
            "machine": machine, "architecture": {62: "x86_64", 183: "aarch64"}.get(
                machine, f"unknown-{machine}")}


def _verify_product_version_evidence(distribution: str, distribution_version: str,
                                     expected_sdk_version: str) -> None:
    """Reject compatibility claims until an official package/product mapping exists.

    importlib.metadata.version() identifies a Python distribution version. The
    reviewed GDK material does not establish its relationship to GDK releases.
    No configuration value can stand in for that missing official evidence.
    """
    relationship = ("matching version text does not establish product compatibility"
                    if distribution_version == expected_sdk_version else
                    "different version text cannot determine product compatibility")
    raise GdkUnavailable(
        f"VERSION_MAPPING_UNVERIFIED: Python distribution {distribution!r} has version "
        f"{distribution_version!r}; requested GDK product version {expected_sdk_version!r}; "
        f"{relationship} without an official distribution-to-product mapping")


def preflight_gdk(sdk_config_path: str = "", expected_sdk_version: str = EXPECTED_VERSION) -> dict:
    """Pure local preflight: no native import, SDK init, network, or robot access.

    sdk_config_path is a PROJECT JSON approval/mapping file, not a vendor config
    argument. gdk_init() has no documented arguments. Installed distribution
    metadata is evidence about the Python package, not proof of a GDK product
    version. The official package/product mapping is currently unavailable, so
    even matching distribution version text fails before native SDK startup.
    """
    if expected_sdk_version != EXPECTED_VERSION:
        raise GdkUnavailable("VERSION_MISMATCH: adapter documents only GDK 2.6.3")
    if not sdk_config_path:
        raise GdkUnavailable("GDK_UNAVAILABLE: sdk_config_path project JSON is required")
    path = Path(sdk_config_path).expanduser()
    if not path.is_file() or path.stat().st_size > 65536:
        raise GdkUnavailable("GDK_UNAVAILABLE: project config missing or exceeds 64 KiB")
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise GdkUnavailable("GDK_UNAVAILABLE: invalid project JSON config") from exc
    if not isinstance(config, dict):
        raise GdkUnavailable("GDK_UNAVAILABLE: project config must be a JSON object")
    if config.get("allow_read_only_connection") is not True:
        raise GdkUnavailable("READ_ONLY_AUTHORIZATION_REQUIRED: allow_read_only_connection=true")
    if config.get("motor_position_mapping_confirmed") is not True:
        raise GdkUnavailable("MAPPING_UNVERIFIED: confirm actual motor/joint coordinate mapping")
    try:
        names = _names(config.get("joint_names"))
    except GdkDataError as exc:
        raise GdkUnavailable(f"MAPPING_UNVERIFIED: {exc}") from exc
    root_value = config.get("sdk_root")
    if not isinstance(root_value, str) or not Path(root_value).is_absolute():
        raise GdkUnavailable("GDK_UNAVAILABLE: sdk_root must be an absolute actual SDK directory")
    sdk_root = Path(root_value).resolve()
    if not sdk_root.is_dir():
        raise GdkUnavailable("GDK_UNAVAILABLE: sdk_root does not exist")
    # This top-level lookup does not execute agibot_gdk. A native import happens
    # only in the isolated worker after all preflight gates have succeeded.
    spec = importlib.util.find_spec("agibot_gdk")
    if spec is None or not spec.origin or not Path(spec.origin).is_file():
        raise GdkUnavailable("GDK_UNAVAILABLE: actual agibot_gdk binding not found; no mock fallback")
    origin = Path(spec.origin).resolve()
    if not origin.is_relative_to(sdk_root):
        raise GdkUnavailable("GDK_UNAVAILABLE: binding is outside inspected sdk_root")
    providers = importlib.metadata.packages_distributions().get("agibot_gdk", [])
    if len(providers) != 1:
        raise GdkUnavailable("VERSION_UNVERIFIED: binding must have one identifiable distribution")
    try:
        distribution_version = importlib.metadata.version(providers[0])
    except importlib.metadata.PackageNotFoundError as exc:
        raise GdkUnavailable("VERSION_UNVERIFIED: actual package metadata unavailable") from exc
    _verify_product_version_evidence(providers[0], distribution_version, expected_sdk_version)
    # Intentionally unreachable while the official product-version gate above
    # remains unimplemented. Retain these independent platform/ABI inspections
    # for review against a real SDK; they cannot bypass the version evidence gate.
    host_machine = {"arm64": "aarch64", "amd64": "x86_64"}.get(
        platform.machine().lower(), platform.machine().lower())
    if platform.system() != "Linux" or host_machine not in ("aarch64", "x86_64"):
        raise GdkUnavailable("PLATFORM_UNVERIFIED: this adapter requires inspected Linux ARM64/x86_64 SDK")
    if sys.version_info[:2] != (3, 10):
        raise GdkUnavailable("PYTHON_ABI_UNVERIFIED: default documented binding is Python 3.10; rebuilt bindings need review")
    shared_objects: list[Path] = []
    # Inspect the selected deployment directory, not any global SDK archive.
    # A mixed-architecture deployment needs a reviewed narrower SDK selection.
    scan_start = time.monotonic()
    for index, candidate in enumerate(sdk_root.rglob("*")):
        if index >= 20000 or time.monotonic() - scan_start > 10.0:
            raise GdkUnavailable("ARCH_UNVERIFIED: selected SDK exceeds project scan time/file bound")
        if candidate.is_file() and ".so" in candidate.name:
            if not candidate.resolve().is_relative_to(sdk_root):
                raise GdkUnavailable("ARCH_UNVERIFIED: SDK shared-object symlink escapes sdk_root")
            shared_objects.append(candidate)
            if len(shared_objects) > 2048:
                raise GdkUnavailable("ARCH_UNVERIFIED: selected SDK exceeds project inspection bound")
    if not shared_objects:
        raise GdkUnavailable("ARCH_UNVERIFIED: no actual Linux shared objects in selected SDK")
    elf = [inspect_elf(candidate) for candidate in sorted(shared_objects)]
    if any(item["bits"] != 64 or item["architecture"] != host_machine for item in elf):
        raise GdkUnavailable("ARCH_MISMATCH: selected deployment contains incompatible ELF objects")
    return {"source": "gdk", "joint_names": names, "sdk_root": str(sdk_root),
            "binding_origin": str(origin), "distribution": providers[0],
            "distribution_version": distribution_version,
            "product_version": expected_sdk_version,
            "architecture": host_machine, "elf_objects": elf,
            "python_version": platform.python_version(),
            "abi_status": "UNVERIFIED until real binding load/dependency checks",
            "adapter_status": "DOC_IMPLEMENTED / SDK_UNVERIFIED",
            "clock_semantics": "local_receive_time_only; source timestamp is opaque nanoseconds"}


def _send_packet(channel: socket.socket, packet: dict) -> None:
    encoded = json.dumps(packet, allow_nan=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_PACKET_BYTES:
        raise GdkDataError("project IPC packet size exceeded")
    if channel.send(encoded) != len(encoded):
        raise GdkDataError("short datagram send")


def _sdk_worker(channel: socket.socket, names: list[str]) -> None:
    """One serial SDK owner; only four documented call expressions below.

    Terminating a stuck process is process isolation, not a vendor cancellation
    or a guarantee that gdk_release ran. The adapter never commands motion.
    """
    sdk = None
    robot = None
    initialized = False
    channel.settimeout(0.25)
    try:
        import agibot_gdk as sdk  # noqa: PLC0415 — intentional lazy native import
        if sdk.gdk_init() != sdk.GDKRes.kSuccess:
            raise GdkUnavailable("gdk_init returned non-success")
        initialized = True
        robot = sdk.Robot()
        _send_packet(channel, {"kind": "ready"})
        while True:
            try:
                message = channel.recv(MAX_PACKET_BYTES + 1)
            except socket.timeout:
                continue
            command = json.loads(message)
            if command == {"kind": "shutdown"}:
                break
            if command != {"kind": "poll"}:
                raise GdkDataError("unknown project worker command")
            mapped = map_joint_states(robot.get_joint_states(), names)
            _send_packet(channel, {"kind": "observation", "timestamp": mapped.source_timestamp,
                                   "names": mapped.names, "positions": mapped.positions,
                                   "velocities": mapped.velocities})
    except Exception as exc:  # The worker reports failure, never substitutes mock data.
        try:
            _send_packet(channel, {"kind": "error", "reason": f"{type(exc).__name__}: {str(exc)[:240]}"})
        except (OSError, ValueError):
            pass  # Parent timeout/worker-death check remains authoritative.
    finally:
        # Python Common: specific object before global release. Robot.close is
        # NOT documented. Dropping this sole reference is not a certified SDK
        # destructor contract; real package inspection is still required.
        robot = None
        release_status = "NOT_INITIALIZED: release not called"
        if initialized:
            try:
                release_status = ("SUCCESS" if sdk.gdk_release() == sdk.GDKRes.kSuccess else "FAILED")
            except Exception:
                release_status = "FAILED"
        try:
            _send_packet(channel, {"kind": "closed", "release_status": release_status})
        except (OSError, ValueError):
            pass
        channel.close()


class GdkBackend:
    """Read-only owner with nonblocking parent IPC and bounded SDK deadlines.

    poll/health use local monotonic time. They do not infer hardware sample age
    from opaque source timestamps. A source timestamp must strictly advance;
    repeated cached samples do not update either sample time or sequence.
    """

    source = "gdk"
    clock_semantics = "local_receive_time_only; source timestamp is opaque nanoseconds"
    motion_status = "UNIMPLEMENTED: blocking/cancel/stop semantics remain unverified"

    def __init__(self, *, sdk_config_path: str, expected_sdk_version: str = EXPECTED_VERSION,
                 poll_timeout: float = 0.5, startup_timeout: float = 5.0):
        if not _finite(poll_timeout) or not 0.01 <= poll_timeout <= 60.0:
            raise GdkUnavailable("poll_timeout must be finite and within project bounds 0.01..60 s")
        if not _finite(startup_timeout) or not 0.01 <= startup_timeout <= 60.0:
            raise GdkUnavailable("startup_timeout must be finite and within project bounds 0.01..60 s")
        self.metadata = preflight_gdk(sdk_config_path, expected_sdk_version)
        self._configure(poll_timeout, startup_timeout, time.monotonic())
        self._channel, worker_channel = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
        self._channel.setblocking(False)
        self._worker = multiprocessing.get_context("spawn").Process(
            target=_sdk_worker, args=(worker_channel, self.metadata["joint_names"]), daemon=True)
        try:
            self._worker.start()
        except Exception:
            self._channel.close()
            raise
        finally:
            worker_channel.close()

    def _configure(self, poll_timeout: float, startup_timeout: float, now: float) -> None:
        self._poll_timeout = poll_timeout
        self._startup_timeout = startup_timeout
        self._started = now
        self._last_now = now
        self._ready = False
        self._inflight: Optional[float] = None
        self._last_progress: Optional[float] = None
        self._sequence = 0
        self.last_source_timestamp: Optional[int] = None
        self._fault = ""
        self._closed = False
        self.release_status = "NOT_RUN"

    def _fail(self, reason: str) -> None:
        if not self._fault:
            self._fault = reason
        # No executor-thread join or SDK call. shutdown() later reaps the child
        # using a bounded grace period; no implicit restart/reconnection.
        if self._worker.is_alive():
            self._worker.terminate()

    def poll(self, now: float) -> Optional[Observation]:
        if self._closed or self._fault:
            return None
        if not _finite(now) or now < self._last_now:
            self._fail("WATCHDOG: invalid/backward local monotonic clock")
            return None
        self._last_now = now
        observation = None
        try:
            # Check before reading a queued reply. A severely delayed executor
            # must not re-stamp an already overdue result as a fresh success.
            if self._last_progress is None and now - self._started > self._startup_timeout:
                raise GdkUnavailable("STARTUP_TIMEOUT: no valid source observation")
            if self._inflight is not None and now - self._inflight > self._poll_timeout:
                raise GdkUnavailable("POLL_TIMEOUT: SDK read exceeded deadline")
            if self._last_progress is not None and now - self._last_progress > self._poll_timeout:
                raise GdkUnavailable("SOURCE_STALE: timestamp is not advancing")
            # Bounded packet count and nonblocking datagrams avoid Pipe.recv's
            # partial-frame blocking hazard. Only one request may be outstanding.
            for _ in range(4):
                try:
                    payload = self._channel.recv(MAX_PACKET_BYTES + 1)
                except BlockingIOError:
                    break
                if len(payload) > MAX_PACKET_BYTES:
                    raise GdkDataError("oversized worker datagram")
                packet = json.loads(payload)
                kind = packet.get("kind")
                if kind == "ready":
                    if self._ready:
                        raise GdkDataError("duplicate worker ready")
                    self._ready = True
                elif kind == "observation":
                    if not self._ready or self._inflight is None:
                        raise GdkDataError("unsolicited worker observation")
                    self._inflight = None
                    stamp = packet.get("timestamp")
                    names, positions, velocities = packet.get("names"), packet.get("positions"), packet.get("velocities")
                    if (type(stamp) is not int or not 0 < stamp < 2**64
                            or names != self.metadata["joint_names"]
                            or not isinstance(positions, list) or len(positions) != len(names)
                            or not isinstance(velocities, list) or len(velocities) not in (0, len(names))
                            or any(not _finite(x) for x in positions + velocities)):
                        raise GdkDataError("invalid mapped worker observation")
                    if self.last_source_timestamp is not None and stamp < self.last_source_timestamp:
                        raise GdkDataError("source timestamp moved backward; reconnect requires explicit restart")
                    if stamp != self.last_source_timestamp:
                        self.last_source_timestamp = stamp
                        self._last_progress = now
                        self._sequence += 1
                        observation = Observation(names.copy(), positions, velocities, [], self._sequence, now)
                elif kind == "error":
                    raise GdkUnavailable(str(packet.get("reason", "unknown SDK failure")))
                elif kind == "closed":
                    self.release_status = str(packet.get("release_status", "UNVERIFIED"))
                    raise GdkUnavailable("SDK worker closed unexpectedly")
                else:
                    raise GdkDataError("unknown worker packet")
            if not self._worker.is_alive():
                raise GdkUnavailable("SDK worker exited")
            if self._last_progress is None and now - self._started > self._startup_timeout:
                raise GdkUnavailable("STARTUP_TIMEOUT: no valid source observation")
            if self._inflight is not None and now - self._inflight > self._poll_timeout:
                raise GdkUnavailable("POLL_TIMEOUT: SDK read exceeded deadline")
            if self._last_progress is not None and now - self._last_progress > self._poll_timeout:
                raise GdkUnavailable("SOURCE_STALE: timestamp is not advancing")
            if self._ready and self._inflight is None:
                _send_packet(self._channel, {"kind": "poll"})
                self._inflight = now
        except (OSError, ValueError, AttributeError, GdkUnavailable) as exc:
            self._fail(f"{type(exc).__name__}: {exc}")
            return None
        return observation

    def healthy(self, now: float) -> bool:
        return (not self._fault and not self._closed and _finite(now)
                and self._last_progress is not None
                and 0 <= now - self._last_progress <= self._poll_timeout)

    @property
    def failed(self) -> bool:
        """Project fatal state; wrappers must exit nonzero instead of falling back."""
        return bool(self._fault)

    @property
    def failure_reason(self) -> str:
        return self._fault

    def health_reason(self, now: float) -> str:
        if self._fault:
            return self._fault
        if self._closed:
            return "CLOSED"
        if self._last_progress is None:
            return "STARTING: waiting for valid progressing source timestamp"
        if not self.healthy(now):
            return "SOURCE_STALE: no recent progressing source timestamp"
        return "READ_ONLY_OK: local receive activity/source progression; hardware sample age UNVERIFIED"

    def command_positions(self, positions: Any, now: float) -> None:
        raise GdkUnavailable(self.motion_status)

    def hold(self, now: float) -> None:
        raise GdkUnavailable("UNIMPLEMENTED: no verified GDK hold/stop operation; no command sent")

    def shutdown(self, now: float) -> None:
        """At most 0.6 s joins; a stuck SDK cannot block ROS teardown forever."""
        if self._closed:
            return
        self._closed = True
        try:
            if self._worker.is_alive():
                try:
                    _send_packet(self._channel, {"kind": "shutdown"})
                except (OSError, ValueError):
                    pass
                self._worker.join(timeout=0.2)
            if self._worker.is_alive():
                self.release_status = "UNVERIFIED: worker terminated after bounded shutdown"
                self._worker.terminate()
                self._worker.join(timeout=0.2)
            if self._worker.is_alive():
                self._worker.kill()
                self._worker.join(timeout=0.2)
            for _ in range(4):
                try:
                    packet = json.loads(self._channel.recv(MAX_PACKET_BYTES + 1))
                except (OSError, ValueError):
                    break
                if packet.get("kind") == "closed":
                    self.release_status = str(packet.get("release_status", "UNVERIFIED"))
            if self._worker.is_alive():
                self.release_status = "FAILED: worker did not exit after kill"
            elif self.release_status == "NOT_RUN":
                self.release_status = "UNVERIFIED: no release acknowledgement"
        finally:
            self._channel.close()
            if not self._worker.is_alive():
                self._worker.join(timeout=0)
