# G2 Gazebo simulation

## Introduction

This project extends the existing two-node Python ROS 2 application with an
Agibot G2 **Gazebo Fortress simulation**. It is a simulation project, not an
installation of GDK 2.6.3 and not a demonstration on a physical robot.

| Original requirement | Simulation implementation |
|---|---|
| Repository | Python application, description resources, build files and verification scripts |
| Docker, ROS Humble, colcon | Ubuntu 22.04 / native ARM64 simulation image; normal colcon installation |
| `sayHello` | A small out-and-back trajectory on one simulated left-arm joint |
| `telemetry` | JointState measurements originating from the Gazebo controller plugin |
| Markdown documentation | Installation, model preparation, execution, recording, verification and shutdown below |

**COMPLETE — SIMULATION**, verified on the Ubuntu ARM64 VM on 2026-09-13.
The [acceptance report](docs/test_report_gazebo.md) records 374 software tests, 29 real
Gazebo cases, two independent six-case verifications and an actual GUI recording.
Model conversion, Python tests and compilation alone are not treated as physics/GUI evidence.
Earlier numerical mock results are historical and remain separately documented.

## Architecture

The two application nodes are Python/rclpy:

- `/g2/sayHello` owns the asynchronous FollowJointTrajectory client, checks readiness,
  submits a complete seven-joint arm vector, and correlates each request by `run_id`.
- `/g2/telemetry` validates and forwards new simulator measurements. It does not
  create a second model, echo commanded positions, or publish replacement feedback.

The additional nodes/processes are simulation infrastructure:

```text
sayHello -> arm_controller/FollowJointTrajectory -> gz_ros2_control -> Gazebo physics
Gazebo physics -> joint_state_broadcaster -> /g2/sim/joint_states
                                           |-> telemetry -> /g2/joint_states
                                           |-> robot_state_publisher -> TF
Gazebo world clock -> one directional ros_gz_bridge -> /clock
```

The Gazebo plugin creates the only controller manager. Broadcaster and trajectory
controller are activated before application startup. The application also requires
fresh controller, clock and measurement state before accepting motion.

## Requirements

The primary execution platform is the existing Ubuntu 22.04.5 ARM64 Parallels VM,
with its own Docker Engine, Compose and Buildx. macOS is the source master and model
conversion host. Keep the existing NAT configuration. No GPU, CUDA, desktop system,
privileged container, host networking, hardware device or proprietary SDK is needed.

ROS is Humble and Gazebo is Fortress. Native ARM64 Fortress and `ros_gz_bridge`
binaries are installed from the ROS/Ubuntu repositories. At the tested repository
state, `ros_gz_sim` and `gz_ros2_control` binaries were unavailable on ARM64; only
these integration packages and the official control demo are built from fixed
upstream Humble commits in `Dockerfile.sim`. The rest of ROS/Gazebo is not rebuilt.

Allow sufficient disk space for the development image and build cache. The inspected
VM had approximately 17 GB free before installation. Rendering uses Xvfb plus Mesa
software OpenGL, not Xvfb alone. Dependency installation requires network access;
verification containers have external networking disabled.

## Model source and license

The selected variant is the official Hugging Face `GenieSimAssets` G2 omnipicker
fixed dual-arm model, revision `a0813aad7c16165daffbe6c2737754e0344809ee`.
The source URDF and composed USD geometry are checked against `model_sources/g2.lock.json`.
The GitHub Genie Sim G2 model with more restrictive notices is not used.

The selected assets use **CC BY-NC-SA 4.0**. This project session is expressly for
noncommercial learning, research and demonstration. Preserve attribution, the source
license, conversion records and ShareAlike obligations when distributing adaptations.
Do not publish an asset-containing image without checking the intended use and terms.
Raw and converted models are kept outside version control in `.artifacts/gazebo-model`.
See [model sources](docs/model_sources.md) and [simulation assumptions](docs/simulation_assumptions.md).

## Installation and Quick Start

Use the existing source checkout; no remote repository has been created or pushed.
From a clean checkout on the Mac with a supported system Python 3.10+:

```bash
cd /path/to/checkout
make fetch-model
```

This downloads only the pinned G2 subset and converts it with an isolated official
`usd-core==26.8` wheel. It does not install Genie Sim. There is no Linux ARM64 wheel
for this particular conversion tool release: run conversion on the Mac, then copy
its generated resource directory to the VM. The simulation itself remains native ARM64.
Alternatively, `USD_PYTHON` may name an existing official OpenUSD 26.8 interpreter;
the preparation script checks `Usd.GetVersion()` is exactly `(0, 26, 8)` before
conversion. It does not replace the ROS system interpreter.


If the converter, source lock, runtime paths or generated files no longer match,
inspect the mismatch first. On the **Mac conversion host**, preserve the old generated
cache in a new directory before regenerating; do not delete it or the raw downloads:

```bash
python3 - <<'PYTHON'
from pathlib import Path
import tempfile
cache = Path('.artifacts/gazebo-model')
backup = Path(tempfile.mkdtemp(prefix='generated-backup-', dir=cache))
(cache / 'generated').rename(backup / 'generated')
print('Preserved generated model:', backup / 'generated')
PYTHON
make fetch-model
```

Then transfer the newly verified generated directory to the VM after inspecting the
target, retaining its old cache separately. This recovery does not install USD on ARM Linux.

Transfer the complete source checkout and `.artifacts/gazebo-model/generated/` through
your existing private VM channel to `/home/lang/projects/agibot-g2-ros2`. Do not replace
unreviewed user files or delete the target tree. The generated manifest verifies every
asset; `scripts/source_manifest.py --scope delivery` identifies uncommitted source too.

Inside the Ubuntu VM, with an already authorized Docker execution method:

```bash
cd /home/lang/projects/agibot-g2-ros2
make fetch-model       # verifies the transferred model cache
make build-sim
make sim-doctor
make verify-sim        # fresh world; one explicitly enabled out-and-back request
```

Do not add the user to a privileged group, change docker.sock permissions or install
passwordless sudo merely to run these commands. If your account requires sudo, use
normal interactive `sudo make ...` authorization in the VM.

## Build, Run and Stop

```bash
make build-sim
make rebuild-sim       # explicit no-cache simulation rebuild
make sim-up            # backend=gazebo, motion DISABLED
make sim-hello         # submits only; expected refusal exits 2 while disabled
make sim-logs
make sim-down
```

Equivalent build and ordinary launch commands:

```bash
docker build -f Dockerfile.sim --target simulation -t agibot-g2-sim:fortress .
docker compose -p agibot-g2-sim -f compose.sim.yaml up -d --no-build
docker compose -p agibot-g2-sim -f compose.sim.yaml exec -T sim \
  /opt/demo/docker/sim-entrypoint.sh ros2 node list
docker compose -p agibot-g2-sim -f compose.sim.yaml down --timeout 20
```

`G2_MODEL_DIR` can override the generated model directory. Its container path is
`/opt/g2-model`; source files and install directories are not covered by bind mounts.
Every `docker compose exec` ROS command must explicitly use the simulation entrypoint
(or source ROS, `/opt/sim_vendor/install/setup.bash`, and `/opt/demo/install/setup.bash`).

## Demonstration and GUI Recording

```bash
make demo-sim
make record-sim
```

Each command creates an independent container, transport partition, evidence directory,
and world. It enables only simulated motion, starts the actual Gazebo GUI on an isolated
Xvfb display with Mesa software rendering, triggers one action and records the GUI.
Output is under `.artifacts/gazebo/<run>/`: `g2-gazebo.mp4`, `g2-gazebo.png`,
`opengl.txt`, Gazebo/recording logs and the associated motion evidence.

No remote desktop port is exposed. Copy the resulting video/image through the private
VM channel to view them on the Mac. Recordings use their actual wall-clock speed;
slow VM simulation must not be described as real-time motion. A parseable video alone
is not sufficient: the acceptance report also records visual inspection of the G2.

For an existing graphical session inside a suitably configured simulation container,
the actual Fortress GUI command is `ign gazebo -g --render-engine ogre` with the same
Gazebo Transport partition as the server. Do not use `xhost +`.

## ROS Interfaces and Parameters

All following names are **project simulation interfaces**, not GDK APIs.

| Interface | Type / meaning |
|---|---|
| `/g2/say_hello` | `std_srvs/srv/Trigger`; success means request accepted, not completed |
| `/g2/hello_status` | `std_msgs/msg/String` JSON; source, run_id, state, reason, actual command waypoints and controller result |
| `/g2/sim/arm_controller/follow_joint_trajectory` | `control_msgs/action/FollowJointTrajectory` |
| `/g2/sim/joint_states` | `sensor_msgs/msg/JointState` from joint_state_broadcaster |
| `/g2/joint_states` | validated simulator measurements with original sample stamps |
| `/g2/telemetry_health` | JSON source, health, clock domain, measured sim/wall frequency and RTF |
| `/clock` | `rosgraph_msgs/msg/Clock`, one Gazebo-to-ROS bridge |

Simulation defaults: displacement `0.05 rad`, duration `6 s` in simulation time,
10 Hz public telemetry in simulation time, return/holding tolerance `0.002 rad`,
velocity tolerance `0.01 rad/s`, stable feedback duration `0.2 s`, and a 180-second
wall-clock execution budget. Model names, order and limits come from the generated
inventory; the selected joint is `idx22_arm_l_joint2`. All seven left-arm commands
start from fresh observed positions; other commanded joints hold their baselines.

Critical parameters are read-only after startup. Ordinary startup never enables motion.
Both applications, controller manager/controllers and robot_state_publisher use
`use_sim_time=true`. Clock reset invalidates the old execution epoch. Pause/staleness
checks and process deadlines use a monotonic wall clock, so paused simulation cannot
make shutdown wait forever.

Source subscriptions use best-effort/volatile QoS compatible with the broadcaster;
public telemetry is reliable/volatile. Status is reliable/transient-local. Tests match
new run IDs and fresh sample stamps, never a cached old success. Unsupported optional
measurements remain empty, and invalid or repeated source samples are not relabeled
with a new time. Radians and rad/s refer to simulated revolute joints.

## Tests

```bash
make test-sim           # existing Python/ROS regression plus real simulation cases
make verify-sim
make verify-sim         # another new world and new run_id
```

Builds perform normal `colcon build --event-handlers console_direct+`. The software
suite executes `colcon test --event-handlers console_direct+ --return-code-on-test-failure`
and `colcon test-result --verbose`; empty or failed suites are errors. Real simulation
probes additionally subscribe to both broadcaster and public telemetry, call Trigger,
check controller activation/action type, correlate source stamps and values, and verify
excursion, holding and return. Pause/reset checks are separate from mock fault tests.

Reports preserve JSON/CSV/JUnit, command exit codes, image identity and source hashes.
`command_waypoints.csv` retains the actual submitted full-arm target vectors at
relative simulation times 0/3/6 seconds; `joint_states.csv` contains independently
observed positions with source timestamps. A zero trajectory header means start on
controller receipt, so these are not falsely treated as a shared absolute start time.
Measured velocity, finite-difference position speed and measured acceleration are
checked against 1.5 times the analytical quintic-profile peaks; endpoint tests alone
cannot hide an instantaneous jump. The raw observations and numeric bounds are retained.
The expected positive excursion is 0.04–0.06 rad for a 0.05 rad request. Endpoint and
non-target holding error must remain below 0.002 rad. Simulation-time telemetry rate
and wall-clock rate are measured separately; no claim of hard-real-time behavior is made.

The old commands `make up`, `make demo-mock`, `make test` and `make verify` retain their
numerical mock meaning. Rebuild the corresponding mock image before testing updated
sources. Mock success is regression evidence, not Gazebo acceptance.

## Safety, Troubleshooting and Limitations

The model is fixed to world at its base. Seven left-arm degrees of freedom remain
mobile; other original movable joints are frozen at a documented pose. The simulator
uses standard position servos and original source inertia/collision data, with recorded
same-source fixed-tool transform repairs. It does not reproduce calibrated motor drives,
whole-body balance, navigation, manipulation planning or physical robot safety.

A source/manifest mismatch requires inspection and rebuilding; do not bypass it. Missing
model files require `make fetch-model` or a verified transfer of generated resources.
Controller unavailable errors require checking `sim-logs`, namespace, spawner status
and plugin libraries. An action server appearing is insufficient until its controller
is active. For graphical failures inspect `opengl.txt`, `gazebo-gui.log` and Ogre logs;
a black window is not a passing GUI demonstration.

**Real GDK binaries, SDK ABI compatibility and all physical robot tests are OUT OF SCOPE.**
This project does not establish compatibility with GDK 2.6.3 or prove real-robot
collision safety. The historical Python/mock README is preserved in
[docs/README_python_mock_historical.md](docs/README_python_mock_historical.md).
