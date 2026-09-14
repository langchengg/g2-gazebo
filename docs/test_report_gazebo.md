# G2 Gazebo simulation acceptance report

## Result and scope

**COMPLETE — SIMULATION.** Actual Ubuntu VM Docker execution verified the G2
Gazebo model, two Python applications, controlled arm movement and simulator telemetry.
Real GDK installation, SDK compatibility and physical robot tests are **OUT OF SCOPE**.
Historical C++/Mac/mock counts are not reused as this run's results.

| Requirement | Result | Evidence |
|---|---|---|
| Existing repository and uncommitted work preserved | PASS | Before-source archive and manifests; no commit, push, reset or clean |
| Docker / Humble / colcon normal installation | PASS | No-cache image build, subsequent clean application-layer builds, installed Python identity |
| G2 entity, meshes and advancing physics world | PASS | Actual Scene/state RPC, 53 visual assets, 106 native mesh imports, real joint feedback |
| Two Python application nodes and control chain | PASS | Installed modules/entry points, unique app instances and controller manager, actual Action/Trigger/topics |
| Small out-and-back arm movement | PASS | Action status 4 / error 0 plus independent measured excursion, holding and return |
| Telemetry from Gazebo | PASS | Sole broadcaster source, exact original sample stamps/values, pause/reset fault checks |
| GUI and actual recording | PASS | Ogre 1 + Mesa llvmpipe, original 1280x720 H.264 video and inspected frames |
| Regression and two independent verifications | PASS | 374 software tests + 29 real Gazebo cases; two further 6-case runs |
| README and delivery | See final consistency receipt | Source archive, model acquisition instructions and non-sensitive evidence copied to Mac |

The final source consistency receipt is saved outside the source hash to avoid a
self-referential report: `.artifacts/gazebo/final-source-consistency.json`.

## Execution identity

- UTC execution date: **2026-09-13**. Final accepted software/Gazebo suite started at
  run directory `20260913T145837Z-de67b9`; detailed per-command timing is retained.
- Source master: `/Users/delaynomore/Downloads/test`, branch `test/g2-demo`.
  This repository still has an unborn HEAD; there is no commit SHA to substitute for content hashes.
- Execution copy: `/home/lang/projects/agibot-g2-ros2`, native Linux filesystem.
- VM hostname `lang`, Ubuntu 22.04.5 LTS, `aarch64` / Debian `arm64`, Parallels virtualization.
- System/ROS Python: `/usr/bin/python3`, Python 3.10.12. The installed console scripts
  run actual `agibot_g2_demo` Python modules under `/opt/demo/install`; no C++ app wrapper.
- Docker Engine 29.8.0; Buildx 0.37.0 / BuildKit 0.33.0; default Docker driver,
  `unix:///var/run/docker.sock`, VM-local systemd Docker service and dockerd process.
  `DOCKER_HOST` and `DOCKER_CONTEXT` were unset. Builder advertises native `linux/arm64`.
- Final VM snapshot: 5.8 GiB RAM / 4.8 GiB available; 7.9 GiB disk available.
- Final simulation image: `agibot-g2-sim:fortress`, arm64, 2,878,666,510 bytes.
  Image ID and reported local repository digest:
  `sha256:509fde2117cc65502ee062dac9e237e6ff57be6ad1a9869b2f4afc86892f269b`.
- Final **65-file runtime source hash**, verified on Mac, VM and image:
  `a4a835eaea7fae18517873edffe7a0db4929ad66d5575c91f8bd170dfe04fc5f`.
  Documentation/legacy files are separately covered by the final delivery manifest.

The pinned ROS base manifest is
`sha256:75dd3aba34a3838dadbb31a9f7bef769bdfa8713e6cec686fc868db2981b0987`.
Installed versions: Fortress meta `1.0.3-2~jammy`, ignition-gazebo6 `6.18.0-1~jammy`,
ros_gz_bridge `0.244.25-1jammy.20260804.183426`, controller manager 2.54.0,
ros2_controllers 2.53.3. Missing ARM64 integrations were built from official commits:

- gz_ros2_control 0.7.21: `c88a5fd9170af120c263c1201f0744a40f93d673`.
- ros_gz_sim 0.244.26: `28e586a3d41f80f4a91e81902b8618c9d506022c`.

No x86 emulation, Mac Docker execution, robot network, privileged container or public
GUI port was used for these accepted runs. Mac was used for source editing, model
conversion and viewing/transferring evidence.

## Model identity and physical assumptions

Official HF `agibot-world/GenieSimAssets` revision
`a0813aad7c16165daffbe6c2737754e0344809ee`, variant
`G2_omnipicker_fixed_dual.urdf`, with geometry from its composed USD layers.
CC BY-NC-SA 4.0 applies; the user explicitly confirmed noncommercial learning,
research and demonstration. The more restricted GitHub G2 model was not used.

The 217-file generated manifest SHA-256 is
`34343986e44a0f6e43c868ac0b38f9d390107887385e49bbb9b83e05a2d41072`.
The generated URDF SHA-256 is
`ec6d943fb1266e63cef9b384f3fa1e86a84dc1ad67d159451c0de5b428113df1`.
Raw/generated assets remain ignored local dependencies, not source archive contents.

The base is fixed to world at z=0.04 m. Seven left-arm joints remain movable;
39 other originally movable joints are explicitly frozen at the source zero pose.
Original positive masses/inertias and same-source collision geometry are retained.
Six fixed helper/tool attachment transforms were repaired from the same USD.
Normals and material subsets are converted to OBJ/MTL; complex MDL shading is simplified.
Five exactly degenerate triangles were omitted, not entire collision objects.

Scene inspection identified G2 entity id 10 and all 53 expected visual meshes.
The Scene service omits `is_static` even for the static floor, so its absence is
recorded as NOT_REPORTED; it is not used to infer dynamics. Dynamic arm behavior is
proved by the actual controller/measurement loop, and world iteration/simulation-time
advancement is independently read from Gazebo state.

GUI frames show the complete model and the tested path without obvious severe
penetration, collapse or unrelated body movement. This is a limited visual check,
not an exhaustive self-collision analysis or calibrated real-robot safety claim.
See `model_sources.md` and `simulation_assumptions.md` for transformation/mesh details.

## Actual commands and test results

| Command / stage | Exit | Actual result / directory under VM `.artifacts/gazebo/` |
|---|---:|---|
| Official Fortress cart smoke | 0 | `20260913T131938Z-root/official-smoke-v2`; controller active, 2,281 samples; environment smoke only |
| `make rebuild-sim` (whole-image no cache) | 0 | `20260913T141720Z-e9bd7a`; dependencies/plugins and app rebuilt |
| `make build-sim` (final source; fresh application build/install layer) | 0 | `20260913T145358Z-1970cf` build receipt / root command-41 log; final image/hash above |
| `make sim-doctor` | 0 | `20260913T142132Z-e07f3c`; all 106 meshes imported and actual OpenGL context checked |
| `make sim-up` / `make sim-logs` / `make sim-down` | 0 / 0 / 0 | `entrypoints-20260913T1422` |
| `make sim-hello` in default mode | 2, expected | Explicit service refusal `simulation motion is disabled`; CLI exit alone was not accepted |
| `make test-sim` | 0 | `20260913T145837Z-de67b9`; 374 software + 29 real Gazebo cases |
| `colcon test --event-handlers console_direct+ --return-code-on-test-failure` | 0 | 348 unit + 26 real ROS integration, zero failed/skipped |
| `colcon test-result --verbose` | 0 | Actual pytest JUnit and colcon logs retained |
| `make verify-sim`, twice | 0 / 0 | Directories and independent run IDs below; 6/6 cases each |
| `make record-sim` | 0 | `20260913T150323Z-a7c40d`; 6/6 cases plus GUI/media checks |
| Forced runner timeout | 124, expected | `timeout-2d2857cd`; wrapper test 0, container exited124, no leftover processes |

The no-cache build had runtime hash
`c8df4795d05516e65214ad460ff110043a39f109d7c7a25643cd6e9a43751618`.
Later camera/probe corrections rebuilt the application layer normally from source;
its build directory was created within that fresh image layer. The earlier no-cache
image is not mislabeled as the final image hash. Final suite and both verification
runs all used the final image/hash listed above.

The real Gazebo cases cover default refusal, graph/types/QoS/source ownership,
G2 entity/assets and advancing updates, measured motion and source correlation,
invalid joint rejection by the actual controller, standard Action cancel, controller
inactivation/recovery, pause without fake telemetry, reset/old-run invalidation,
and SIGTERM during observed motion. Software tests additionally cover illegal
parameters, limits, NaN/Inf, faulty/stale observations and asynchronous state logic.
Fake SDK/control-flow tests in the retained software suite do not constitute SDK or hardware validation.

The initial upstream cart smoke initially failed because Action discovery preceded
controller activation. Waiting for the actual active state corrected that smoke;
cart measurements are never used as G2 movement evidence.

## Two independent verification runs and recording

Predeclared acceptance: positive peak 0.04–0.06 rad for requested 0.05 rad; endpoint
and non-target holding errors <=0.002 rad; public sim-time frequency 8–11 Hz;
new source stamps, matching current run_id, controller status4/error0 and observed
stable return. Actual submitted waypoint arrays are recorded in command_waypoints.csv.
Measured velocity, position-difference velocity and acceleration are bounded by 1.5
times the analytical quintic peaks: 0.046875 rad/s and 0.0481125224 rad/s².
All three final runs measured 0.0309987355 rad/s peak velocity and 0.0314475 rad/s²
peak acceleration; independent position differences peaked at 0.0309361080 rad/s. Every wait has a wall deadline. Motion uses simulation time.

| Run | Directory | Motion samples | Peak rad | Final max error rad | Sim Hz / wall Hz | RTF |
|---|---|---:|---:|---:|---:|---:|
| Independent verify 1 | `20260913T150151Z-4eba42` | 62 | 0.049966032 | 0.000011127 | 10.000 / 9.922 | 0.992192 |
| Independent verify 2 | `20260913T150235Z-4975d1` | 62 | 0.049966032 | 0.000011127 | 10.000 / 9.926 | 0.992567 |
| GUI recording | `20260913T150323Z-a7c40d` | 62 | 0.049966032 | 0.000011127 | 10.000 / 8.036 | 0.803579 |

- Independent verify 1: `0ed2daabb844458c951b7e48fc915c3b`; UTC 2026-09-13T15:01:54.623145+00:00 to 2026-09-13T15:02:16.836546+00:00; controller status 4 / error 0.
- Independent verify 2: `57758df2e5b8417ba0e42b6333828052`; UTC 2026-09-13T15:02:38.428996+00:00 to 2026-09-13T15:03:02.028757+00:00; controller status 4 / error 0.
- GUI recording: `1b53d81f4ba945cf80848a86619bef54`; UTC 2026-09-13T15:03:27.193651+00:00 to 2026-09-13T15:03:51.960046+00:00; controller status 4 / error 0.

Non-target holding error was at most 1.72e-11 rad in these three runs. Baselines
were acquired from actual feedback and include nonzero startup values. Each run
used a new container, transport partition and simulator world. Public positions,
velocities and efforts matched original broadcaster samples exactly by name/stamp;
unknown fields are not replaced by invented measurements.

Scene CLI reads occur before the measurement window. The probe drains callbacks
past a simulator timestamp barrier, then obtains fresh baseline samples. This
prevents old queued callbacks from contaminating wall-rate statistics.

## GUI and media

Actual renderer: Fortress Ogre 1, Xvfb, Mesa llvmpipe LLVM15.0.7 / Mesa23.2.1,
OpenGL4.5, `LIBGL_ALWAYS_SOFTWARE=1`. Xvfb was verified with glxinfo; it was not
mistaken for a renderer. No large desktop, NVIDIA GPU, noVNC or public port is required.

Accepted recording: `20260913T150323Z-a7c40d/g2-gazebo.mp4`, H.264/yuv420p,
1280x720, 10 fps, 254 frames, 25.4 seconds at original wall-clock speed.
`g2-gazebo.png` is the actual GUI screenshot. Frames extracted at16/21/25 seconds
show baseline, excursion and return with the complete base/body/head/arms visible.
The recorded run_id is `1b53d81f4ba945cf80848a86619bef54`.

An optional Mac-derived arm detail clip is `.artifacts/gazebo/g2-gazebo-arm-detail-final-1x.mp4`:
original frames16–25.4s cropped spatially to (x540,y235,w340,h160), enlarged4x to
1360x640. It preserves 1x wall time and is explicitly a crop of the same real GUI
recording, not another simulation or generated animation. Original media remain unchanged.

## Failures found and repaired

1. Wrong apt package spelling (`libignition-plugin1-dev`): metadata identified
   `libignition-plugin-dev`; corrected dependency build passed.
2. Namespaced plugin parameter lookup duplicated an absolute node path: use the
   verified relative `robot_state_publisher` parameter node.
3. Original URDF/USD fixed tool transforms disagreed: preserve source evidence and
   use same-source USD transforms for six fixed attachments.
4. Initial OBJ export omitted normals, causing DART collision mesh rejection and
   a server segfault139. Normals/submesh transformations were fixed; no gravity or
   collisions were removed. All106 actual Ignition mesh loads then passed.
5. A source sync/build race was detected by image/hash review. That earlier image
   was not counted as final-source evidence; build now also rechecks current source.
6. Native UUID byte values were not JSON serializable in the probe. Explicit integer
   conversion repaired evidence saving without changing controller behavior.
7. First GUI parameter request timed out despite healthy clock/telemetry. Only
   read-only parameter queries received bounded retries with pending-request cleanup.
8. Launch shutdown left a Fortress server child after the Ruby launcher exited.
   The scoped subreaper now stops tracked descendants and records signals. Final
   SIGTERM test required one descendant SIGINT; no SIGKILL or leftover process.
9. Synchronous Scene reads accumulated probe callbacks and broke source correlation.
   A timestamp barrier and fresh measurement window fixed this, retaining exact
   correlation assertions and all motion thresholds.
10. Initial GUI camera framing was too distant, then cropped the head. Final framing
    shows the full model; original failed/cropped recordings remain historical evidence.
11. A final-suite iteration checked node counts before DDS graph discovery settled.
    The probe now waits at most10s for exact application/manager counts and records
    discovery snapshots; persistent duplicates still fail. That failed iteration did
    not log the count, so it is not described as a proven duplicate manager.
12. Repeated stop signals interrupted Python node destruction in that iteration.
    Signal handling is now idempotent during shutdown. The final full suite showed
    clean Python exits with no StopRequested traceback.
13. The first forced-timeout check expired during mesh preflight. A stronger15s
    timeout reached the running simulator/controller, returned expected124, and
    cleaned up with no remaining processes.

Failed iterations, including `20260913T134622Z-a5f05c`, `20260913T140602Z-ee9984`,
`20260913T141201Z-517962`, `20260913T142749Z-3121ea` and `20260913T145028Z-500c67`, remain in the evidence export.
No failing test was deleted or relabeled PASS.

## Evidence locations and preservation

VM originals: `/home/lang/projects/agibot-g2-ros2/.artifacts/gazebo/<directory>`.
Mac verified copies: `/Users/delaynomore/Downloads/test/.artifacts/gazebo/vm-final-v2/<directory>`.
The transfer archive and per-file checksum manifest are under `.artifacts/vm-channel/incoming/`;
all extracted files are checked before acceptance. Per-run `environment.json`,
`commands.json`, `run-commands.json`, `cleanup.json`, `motion/result.json`,
`joint_states.csv`, `command_waypoints.csv`, raw JSON samples and JUnit contain actual outputs.
The ffmpeg recorder exits255 on the intentional stop signal after writing its trailer;
ffprobe, duration/frame validation and visual inspection independently verify the saved video.
This expected recorder stop is not represented as an unqualified process exit0.
`final-environment-v2/` records daemon location, platform, image and absence of project containers.

Before-edit Mac snapshot: `.artifacts/gazebo/20260913T131938Z/before-source.tar.gz`,
75 files including uncommitted/untracked sources and retained notes, SHA-256
`6d5ac64d60d87ec3470e74bb5e8c836ebf6e2d7fe9978d9db5e617cd453e6a4a`.
VM pre-simulation source snapshot is also retained. Old C++ and previous reports are
preserved; neither the repository nor any asset-containing image was published.

## Capabilities, references and reuse

Used local Git/Python hashing and reviewed project utilities, Parallels console plus
bounded private transfer/execution channels, VM Docker/Buildx/colcon/pytest/rclpy,
Ignition CLI/services, native mesh loader, OpenUSD, Xvfb/Mesa/Ogre and ffmpeg/ffprobe.
Two bounded agents independently audited model licensing/conversion and ROS control
interfaces, then reviewed focused fixes. No unrelated connector or new plugin was installed.

Official references were checked, and installed metadata/help plus actual runtime
responses determined supported names and behavior:

- [Fortress ROS installation](https://gazebosim.org/docs/fortress/ros_installation/).
- [Humble gz_ros2_control](https://control.ros.org/humble/doc/gz_ros2_control/doc/index.html).
- [Humble trajectory controller](https://control.ros.org/humble/doc/ros2_controllers/joint_trajectory_controller/doc/userdoc.html).
- [Fortress graphics troubleshooting](https://gazebosim.org/docs/fortress/troubleshooting/).
- [Official G2 assets](https://huggingface.co/datasets/agibot-world/GenieSimAssets).
- [Fortress GUI configuration](https://github.com/gazebosim/gz-sim/blob/ign-gazebo6/src/gui/gui.config).
- [Fortress state message schema](https://github.com/gazebosim/gz-msgs/blob/ign-msgs8/proto/ignition/msgs/serialized_map.proto).
- [OpenUSD distribution](https://pypi.org/project/usd-core/26.8/).

Official integration source components are built with their original Apache-2.0
notices; upstream examples are environment smoke references. Model transformations
are derived under their separate CC BY-NC-SA terms. Application, orchestration and
probe code are project implementations against verified standard ROS/Gazebo interfaces.
