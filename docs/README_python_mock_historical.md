# Agibot G2 demo — Python, ROS 2 Humble and Ubuntu 22.04

## Introduction

This repository provides two **Python/rclpy application nodes** in one ROS 2
Humble container. `sayHello` owns a deterministic mock backend and accepts a
small mock arm movement request. `telemetry` publishes the observations from
that same backend as real ROS `JointState` messages.

The original task also requires movement of an actual G2 arm. That hardware
requirement is **not yet verified**. The document-derived GDK 2.6.3 Python
adapter implements read-only integration logic; the proprietary binding,
firmware compatibility and robot tests remain separate requirements.

| Original requirement | Implementation |
| --- | --- |
| One repository | This Mac repository is the authoritative source; the VM receives a checked copy. |
| ROS 2 Humble Docker environment | Ubuntu Jammy ROS base, ordinary `colcon build` installation. |
| `sayHello` | Genuine Python node, Trigger service, bounded state machine and observed mock motion. |
| `telemetry` | Genuine Python node, validated joint observations from the same backend. |
| Actual G2 arm movement | Not implemented or tested until unresolved hardware motion semantics are verified. |

Current evidence: [VM/Python test report](docs/test_report_vm_python.md).
[C++/Mac results](docs/test_report.md) are historical and do not validate this
Python migration. The preserved C++ package is in `legacy/cpp/` with
`COLCON_IGNORE`; it is not copied into the default image or launched.

## Requirements

The primary target is an Ubuntu 22.04 ARM64 VM with native Linux storage,
Python 3.10, Docker Engine, Compose, Buildx, Git and Make. Keep normal NAT for
mock development. The selected base is
`ros:humble-ros-base-jammy`, pinned to the multi-platform digest in `Dockerfile`.
Do not force `linux/amd64` on this ARM64 VM.

Use Ubuntu's system Python and ROS's `rclpy` Debian package. Do not install
`rclpy` from PyPI, replace the system interpreter, or use a Conda environment.
No proprietary SDK, robot, host networking, privileged container, physical
device or Docker socket mount is needed for mock operation.

## Installation

Install Docker Engine using the [official Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/).
Inspect existing package sources and conflicting packages before changing them.
The required Docker components are `docker-ce`, `docker-ce-cli`, `containerd.io`,
`docker-buildx-plugin` and `docker-compose-plugin`. Install `git` and `make` if
missing. No distribution upgrade is required.

Confirm the actual daemon before using the project:

```bash
uname -m
cat /etc/os-release
dpkg --print-architecture
sudo docker version
sudo docker info
sudo docker context show
sudo docker context inspect
sudo docker compose version
sudo docker buildx inspect
```

The VM's daemon should identify this Ubuntu host and a local Unix socket.
Check only `DOCKER_HOST` and `DOCKER_CONTEXT` for overrides; a remote builder
or a Mac Docker Desktop daemon does not establish VM acceptance. This project
does not add users to the Docker group or weaken socket permissions. The
commands below use normal `sudo` authorization for a root-owned Docker Engine;
omit `sudo` when an already approved rootless/group setup is in use.

## Quick Start

On the Ubuntu VM, from a complete clone or a verified source copy:

```bash
cd ~/projects/agibot-g2-ros2
sudo make doctor
sudo make rebuild
sudo make test
sudo make verify
sudo make verify
```

There is no public remote URL configured by this delivery. To clone an
existing local Git repository, use `git clone /path/to/repository`; to transfer
this uncommitted delivery, include untracked files with the manifest workflow
below. Cloning an old commit alone will omit the current implementation.

Each `verify` run creates fresh processes, a unique Compose project, a new
`run_id` and its own evidence directory. It waits for valid baseline samples,
submits an enabled **mock** request, checks RUNNING and its matching terminal
state, and measures the excursion and return from sampled positions.

## Build, Run and Stop

```bash
sudo make build        # Cached image build; colcon runs in Dockerfile
sudo make rebuild      # --no-cache build; no unrelated images or data removed
sudo make up           # Two nodes; mock motion disabled
sudo make hello        # Expected rejection; never enables motion
sudo make logs
sudo make down         # Only this project's normal Compose resources
sudo make demo-mock    # Independent, explicitly enabled mock demonstration
```

`make hello` checks the service response's `success` field. Its disabled-motion
rejection returns exit 2 from the helper/manager; Make reports the failed target.
ROS CLI transport success alone does not mean the request was accepted.

Important equivalent commands:

```bash
sudo docker compose build --no-cache
sudo docker compose up -d --no-build
sudo docker compose exec -T demo /opt/demo/docker/entrypoint.sh ros2 node list
sudo docker compose exec -T demo /opt/demo/docker/entrypoint.sh \
  ros2 topic echo /g2/joint_states --once
sudo docker compose exec -T demo /opt/demo/docker/entrypoint.sh \
  ros2 service call /g2/say_hello std_srvs/srv/Trigger '{}'
sudo docker compose down --timeout 10
```

Every `compose exec` ROS command explicitly sources underlay and overlay via
the entrypoint. No bind mount hides the installed workspace. The entrypoint
uses `exec`; normal Compose stop sends SIGINT and has a bounded grace period.

## Python Architecture

The installed executables are:

```text
sayHello = agibot_g2_demo.say_hello_node:main
telemetry = agibot_g2_demo.telemetry_node:main
```

`/g2/sayHello` is the only backend owner. Its steady-clock timer advances the
mock model and publishes observations. `/g2/telemetry` validates that stream
and forwards fresh samples. There is no separate mock server. Both application
nodes use a single-thread executor; callbacks do not sleep or wait on an
executor-owned future. The pure motion core accepts injected monotonic times.

The optional read-only GDK path isolates native calls in one bounded worker
process. This worker is not a ROS node. It is never started by mock tests.

## ROS Interfaces

These names and JSON formats are **project interfaces**, not vendor APIs.

| Interface | Type | Meaning / QoS |
| --- | --- | --- |
| `/g2/say_hello` | `std_srvs/srv/Trigger` | Default reliable service QoS. `success=true` means accepted, not completed. `message` is JSON with `source`, `run_id`, `reason`. |
| `/g2/hello_status` | `std_msgs/msg/String` | JSON `source`, `state`, `run_id`, `reason`, `healthy`, `health_reason`; reliable, transient-local, depth 1. |
| `/g2/internal/joint_states` | `sensor_msgs/msg/JointState` | Backend observations; reliable, volatile, depth 10. |
| `/g2/joint_states` | `sensor_msgs/msg/JointState` | Validated public observations; same stream QoS. |
| `/g2/telemetry_health` | `std_msgs/msg/String` | JSON source, health/reason, measured source rate and timestamp semantics; reliable, transient-local, depth 1. |

Only `/g2/sayHello` and `/g2/telemetry` are normal application nodes. CLI and
test probes are temporary. Status follows IDLE → RUNNING → SUCCEEDED/FAILED.
Concurrent and repeated requests during RUNNING are rejected without queuing.
Consumers must match the accepted `run_id`; a retained previous SUCCEEDED
message is not evidence of the current request.

## Parameters and Observations

All critical configuration is validated at startup and is read-only. Restart
to change it. Installed configuration is in `config/mock.yaml` and
`config/hardware.example.yaml`; launch accepts `config_file`, `backend` and
`enable_motion` arguments. Defaults include:

| Parameter | Default / scope |
| --- | --- |
| `backend` | `mock`; never automatically falls back from `gdk` |
| `enable_motion` | `false`; startup never moves |
| `publish_hz` | 10 Hz mock target |
| `target_joint` | A synthetic `mock_` joint, never a claimed G2 joint name |
| `displacement`, `duration` | 0.05 rad, 4 seconds round trip; **mock only** |
| `feedback_timeout`, `watchdog_timeout` | 0.6 s, 0.5 s monotonic checks |
| `motion_timeout` | 7 s total monotonic deadline |
| `fault_mode`, `fault_after` | Test-only synthetic fault injection; default `none`, 0.5 s |

Positions are radians and available velocities are radians/second. Six mock
joints start from nonzero observations. A quintic command and a separate
tracking model produce the round trip; other joints hold their observed
initial values. Completion checks actual observed excursion, return tolerance
and stability. Scheduling delays limit phase advancement instead of sending a
burst of historical commands; the total deadline still uses wall elapsed
monotonic time. Invalid arrays/names, NaN/Inf, limits and nonpositive durations
are rejected.

Unknown velocity or effort stays empty. Mock ROS stamps represent local
observation time. GDK stamps are explicitly local reception time until a
hardware clock mapping is established; the raw vendor timestamp is kept
opaque in status. Repeated or backward source markers are rejected. Telemetry
preserves the original stamp, checks both reception activity and source
progress, and stops treating stale data as healthy. `use_sim_time=true` is
rejected because these wrappers do not implement a simulated clock mapping.

## Tests and Evidence

```bash
sudo make test
sudo make verify
sudo make verify
sudo python3 scripts/check_runner_cleanup.py --also-launch-checks
```

`make test` executes the following inside the installed image, retaining the
actual colcon JUnit result and rejecting missing/empty/skipped-only suites:

```bash
colcon build --event-handlers console_direct+
colcon test --event-handlers console_direct+ --return-code-on-test-failure
colcon test-result --verbose
```

Build runs during image creation; test and test-result run in the test container.
Pure logic uses pytest; ROS integration uses actual rclpy publishers,
subscriptions and service calls. It checks installed Python entrypoint/module
identity, exactly two application nodes, disabled startup, signed motion,
concurrent requests, stale retained status, fault injection, sample integrity,
frequency, immutable parameters and signal cleanup. Hardware tests are not
silently substituted with fake SDK modules.

Evidence goes to `.artifacts/<action>/<UTC>-<unique>/`: command exit codes,
environment/image/source identity, JUnit, statuses, raw samples and calculated
metrics. Frequency assertions allow 7–13 Hz for the 10 Hz mock target; inspect
the test/report for the actual measurement window and result. Stop/timeout
checks clean only their own uniquely named resources. Raw artifacts are local
and gitignored; authored reports remain in `docs/`.

## Source Copies and Reproducibility

Edit on the Mac; execute the checked copy on the VM's native Linux filesystem.
Do not edit both copies concurrently. Before transfer:

```bash
python3 scripts/source_manifest.py --scope delivery \
  --output .artifacts/delivery.json --bundle .artifacts/delivery.tar.gz
python3 scripts/source_manifest.py --scope runtime \
  --output .artifacts/runtime.json
```

Bundle creation is exclusive and fails if that archive already exists. Inspect
the target before extracting to a **new empty directory**. Transfer the
manifest alongside the archive, then run `source_manifest.py --scope delivery
--check /path/to/delivery.json` in the VM copy. Full vendor caches, SDK binaries,
credentials, Git metadata and build outputs are excluded. Preserve the Mac's
uncommitted/untracked files; a Git SHA alone is not the tested version.

`make build/up/test/verify/demo-mock` compares the image's embedded runtime
manifest with the current working files. A mismatch requires rebuilding.
Documentation and historical C++ are separately covered by the delivery
manifest; they are not runtime image inputs. Copy new test evidence back to a
new Mac artifact directory without overwriting historical reports.

## Hardware Integration

The selected route is the documented **`agibot_gdk` Python binding**. No fake
`genie_msgs` package or vendor module is shipped. The implemented call sequence
is `gdk_init()` → `Robot()` → `get_joint_states()` → `gdk_release()` in an
isolated worker. It maps documented `motor_position`/`motor_velocity`, validates
all approved joint names/counts/errors, and leaves effort empty.

See [exact API evidence and independent verification states](docs/gdk_api_mapping.md),
[selective Python rereading](docs/gdk_python_review.md), and the
[hardware checklist](docs/hardware_checklist.md). Status is
**DOC_IMPLEMENTED / SDK_UNVERIFIED**, read-only. Actual import, ABI, initialization
and device observations have not been validated. Arm motion remains unavailable
because stop/cancel and other safety semantics are incomplete.

Before installing or loading an actual package, inspect it:

```bash
dpkg-deb -f /path/to/actual-package.deb Version Architecture
file /path/to/actual-library.so
readelf -h /path/to/actual-library.so
file /path/to/actual-executable
uname -m
dpkg --print-architecture
```

ARM64 mock success and Python source compatibility do not prove native SDK
compatibility. If the actual package is x86_64-only, retain this ARM64 mock
setup and use a vendor-supported native x86_64 Ubuntu 22.04 machine for the
hardware phase. No x86 emulation is used for robot control.

Hardware dependencies are loaded only after explicit selection, local package
inspection and a project JSON config containing reviewed SDK root, joint
mapping and read-only authorization. `sdk_config_path` is this project's gate
file, not an undocumented argument to `gdk_init()`. Use
`python3 scripts/inspect_gdk.py --config /path/to/reviewed.json` for local
preflight only. The example deliberately contains no usable robot address,
real joint names, control mode, credentials or presumed safe limits.

The default Compose file restricts DDS to localhost and domain 42 solely for
mock isolation. Do not reuse it for hardware. Review official deployment,
interface, time synchronization and runtime requirements before creating a
separate hardware configuration; remove mock-only DDS restrictions there.
Keep NAT until the physical robot connection actually requires a reviewed
alternative. Never copy old sample IPs or DDS settings without verification.

## GDK Acquisition and SDK Stages

The current acquisition result is **BLOCKED**: both documented robot-local
installer URLs were actually requested from Mac and the Ubuntu VM and timed
out with zero bytes. No GDK 2.6.3 payload or official image has been obtained.
See [acquisition evidence](docs/gdk_acquisition.md),
[non-sensitive manifest](docs/gdk_sdk_manifest.json), and
[this continuation's VM test report](docs/test_report_gdk_integration.md).
The older Python/VM report remains historical; it is not this run's result.

These are four separate execution paths:

1. **Mock software:** `make rebuild`, `make up`, `make hello` (refuses by default),
   `make down`, `make demo-mock`, `make verify-software`. The latter runs tests,
   two independent mock verifications and process cleanup checks. No SDK needed.
2. **Actual SDK acquisition/load:** `make sdk-fetch` attempts only the official
   installer resources and never executes them. `make sdk-inspect`,
   `make build-gdk`, and `make sdk-smoke` currently exit 2 with a precise missing
   payload gate; they are not completed SDK installation/load implementations.
   Static artifact inspection: `python3 scripts/sdk_tools.py inspect --file
   /path/to/artifact --sha256 EXPECTED_HASH` (put this on one shell line).
   An installer or a matching self-computed hash does not prove product version.
3. **Real read-only:** backend selection remains `gdk` with explicit project
   configuration, but execution currently fails closed before native import.
   The actual binding, product/distribution version mapping, architecture and
   license must first be inspected. Matching distribution text `2.6.3` alone
   is rejected as `VERSION_MAPPING_UNVERIFIED`; no configurable waiver exists.
   Future isolated import must use the same ROS Python in a separate SDK image,
   `--network none`, no devices/secrets, and a bounded timeout. No import/init
   smoke was run against a real binding in this continuation.
4. **Real arm movement:** unavailable. A document-derived `JointControlReq`
   constructor validates the five actual documented fields, reviewed mapping,
   fresh observations, explicit limits and per-request authorization. Project
   fixtures test this logic; no real SDK type is claimed. Runtime dispatch
   always refuses because blocking-call concurrency, lifetime expiry and arm
   stop semantics remain unverified. A local authorization cannot remove those
   vendor evidence gaps. No hardware command entry point is enabled.

The acquisition path is intentionally not part of `make test` or `make verify`:
website/device availability cannot break the offline mock acceptance. No new
proprietary dependency, vendor stub, x86 emulation, bridge runtime, system
Python replacement or robot network configuration is introduced.

## Safety

Mock motion values are synthetic test parameters, not G2 safety limits. Real
operation requires verified firmware, fresh actual feedback, joint mapping,
control ownership, safe pose/clearance, emergency-stop readiness and on-site
authorization for the specific action. The application does not clear faults,
release emergency stops, disable protection, fill unknown joints with zero,
automatically home, or resume failed motion after reconnection. Communication
loss does not guarantee a remote stop can be delivered. Acceptance does not
prove completion.

## Native Ubuntu Alternative

Native execution on Ubuntu 22.04 is documented but is not the Docker acceptance
path. Follow the [official Humble Ubuntu installation instructions](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html),
install `python3-colcon-common-extensions`, `python3-pytest`, `python3-setuptools`
and the ROS dependencies listed in `package.xml`, then:

```bash
source /opt/ros/humble/setup.bash
colcon build --event-handlers console_direct+
source install/setup.bash
colcon test --event-handlers console_direct+ --return-code-on-test-failure
colcon test-result --verbose
ros2 launch agibot_g2_demo demo.launch.py
```

Use another sourced terminal for the Trigger call. Ctrl-C stops the launch.
Native Ubuntu results remain NOT RUN unless separately recorded.

## Troubleshooting

- Docker CLI without an active local server is insufficient; run `make doctor`.
- `SOURCE MISMATCH`: rebuild from the same source, not an old image or checkout.
- Default Trigger rejection is expected. Use `make demo-mock` for an explicitly
  enabled isolated run.
- Missing executables/resources: inspect `setup.py/setup.cfg/package.xml`, build
  normally and source both ROS and install overlays.
- DDS discovery timeout: run nodes and probe inside the same container; inspect
  logs and compatible QoS before changing VM networking.
- `GDK_UNAVAILABLE`, `VERSION_UNVERIFIED` or architecture errors: inspect the
  actual package/config; no mock fallback occurs.
- Stale/invalid feedback: inspect `/g2/telemetry_health` and source progression.
  Do not restamp a repeated observation to silence the fault.
- Document retrieval failure does not block cached-source mock build/test.
  `make read-gdk` fetches/resumes; `make audit-gdk` reports ledger coverage and
  unresolved evidence. Downloads alone are not marked as read.

## Limitations

This is a deterministic software demonstration, not a collision simulator or
hard real-time controller. Official GDK bodies remain in the gitignored local
cache; authored summaries and source references are retained. No proprietary
SDK is redistributed. Actual SDK architecture/ABI, firmware support, G2
read-only telemetry and small arm movement require their own evidence.
