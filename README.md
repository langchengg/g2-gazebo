# G2 Gazebo and RViz2 simulation

[中文逐步说明](README.zh-CN.md)

## Clone & quick verification entry

```bash
git clone https://github.com/langchengg/g2-gazebo.git
cd g2-gazebo
```

The repository root for this README is `g2-gazebo`.

## Introduction

This is an Agibot G2 **simulation** application. Gazebo Fortress runs the physics;
RViz2 displays the same robot description and measured joint state through TF.
Two Python/rclpy application nodes provide the original exercise:

| Requirement | Implementation |
|---|---|
| Source repository | Git clone from GitHub (`https://github.com/langchengg/g2-gazebo.git`) |
| Docker / ROS 2 / build | Ubuntu 22.04; native ARM64 validated, native x86_64/amd64 accepted by preflight but runtime not tested; ROS 2 Humble with a normal `colcon build` installation |
| `sayHello` | `/g2/sayHello` requests a small out-and-back simulated left-arm trajectory |
| `telemetry` | `/g2/telemetry` publishes Gazebo joint measurements on `/g2/joint_states` |
| Installation and execution guide | This README and the equivalent Chinese guide |

Real GDK binaries, real robot networking and physical robot motion are out of scope.
Historical results are in `docs/test_report_gazebo.md`; they are **not evidence for a
new archive**. A release acceptance receipt outside the archive identifies exactly
which archive, source tree, model and image were tested. Do not infer a release PASS
from this README or from the existence of a GUI process.

## 1. Public prerequisites and execution locations

Validation summary for this submission is kept in [docs/validation.md](docs/validation.md).


Use an **Ubuntu 22.04 Linux host** with Python 3.10, Docker Engine,
Docker Compose V2, Buildx, and GNU Make.

For **headless acceptance**, no X11 session is required:
`make doctor`, `make fetch-model`, `make prepare-model`, `make build-sim`, `make verify-sim` can all be used without `DISPLAY` and `XAUTHORITY`.

For **GUI visual checks**, an existing graphical session is needed:
an X11/Xorg login with `XDG_SESSION_TYPE=x11`, readable `XAUTHORITY` and `/tmp/.X11-unix`.
The project does not install a desktop.

The development VM has approximately 6 GiB RAM and had approximately 8 GiB free
at the start of this reproduction work. These are observations, not validated
minimum requirements. Allow **15 GiB free disk** for a first build where possible;
OpenUSD compilation and Docker cache need additional temporary space. Builds use
two compilation jobs. Keep other large builds stopped. Actual measured peaks and
elapsed times belong in the validation receipt. `doctor` checks prerequisites; it
does not grant runtime acceptance. Both architectures therefore report
`validation_status=NOT_TESTED` at preflight. The current ARM64 runtime result is
recorded separately in [docs/validation.md](docs/validation.md); native amd64 remains
**NOT TESTED**.

All project commands below run in the cloned or extracted
`g2-gazebo` directory. For GUI replay, use the Ubuntu graphical terminal and
preserve local Docker permissions; `sudo` is optional if your user is already in
the docker group.

If host utilities are missing, install only the prerequisites:

```bash
sudo apt-get update
sudo apt-get install -y make python3 xauth x11-xserver-utils ca-certificates curl
```

If Docker Engine, Compose or Buildx is absent, follow the official
[Ubuntu Docker installation instructions](https://docs.docker.com/engine/install/ubuntu/)
for Ubuntu 22.04 on the host architecture and install `docker-ce`, `docker-ce-cli`, `containerd.io`,
`docker-buildx-plugin` and `docker-compose-plugin` from the configured official
repository. Inspect existing installations before resolving package conflicts.
Host provisioning is a prerequisite, not an operation tested by extracting this
archive. ROS, RViz, Gazebo and OpenUSD are installed **inside project images**;
do not install `rclpy` with pip or replace the host/ROS Python interpreter.

For this Mac/Parallels setup, open **Parallels Desktop → Ubuntu Linux → Show** and
use the Ubuntu graphical terminal. Gazebo, RViz and the state window appear in that
same visible Ubuntu desktop. A normal Linux workstation uses its own desktop directly.
No browser URL, SSH tunnel, noVNC endpoint or TCP port is needed for this path.
The optional headless VNC implementation is **NOT TESTED as a delivery path** and
is not a substitute for the visible-desktop prerequisite.

## 2. Clone, verify and enter source tree

Primary path is Git clone. If a custom archived source package is supplied separately,
use its `.tar.gz`, `.tar.gz.sha256`, and `.tar.gz.manifest.json` together. No Release
asset is claimed by this guide.
The external SHA-256 proves consistency with the supplied checksum, not an independent
publisher signature. Replace the example archive path with the file you received:

```bash
ARCHIVE='/path/to/g2-gazebo-source-<source-id>.tar.gz'
cd "$(dirname "$ARCHIVE")"
sha256sum -c "$(basename "$ARCHIVE").sha256"
tar -tzf "$ARCHIVE"
mkdir -p "$HOME/g2 simulation workspace"
tar -xzf "$ARCHIVE" -C "$HOME/g2 simulation workspace"
cd "$HOME/g2 simulation workspace/g2-gazebo"
```

Use a **new, empty destination**. Entries should be regular files below `g2-gazebo/`,
with no absolute paths, links or `..` components. Do not overlay an unrelated project.
The automated `verify-release` additionally validates every entry and content hash
before extraction. Spaces in the parent path are supported and included in its test.
No `.git`, author HOME, preconverted model or project image is required.

## 3. Short complete Quick Start (headless + optional GUI)

Review the model license in section 4 before the `ACCEPT_MODEL_LICENSE=yes` line.
Run these commands **one at a time**. Model/toolchain/image
builds occupy that terminal until they finish.

```bash
# Headless path (recommended for default acceptance)
sudo make doctor
sudo make fetch-model ACCEPT_MODEL_LICENSE=yes
sudo make prepare-model
sudo make build-sim
sudo make verify-sim

# Optional GUI path
sudo make sim-doctor
sudo --preserve-env=DISPLAY,XAUTHORITY,XDG_SESSION_TYPE make demo-visual
sudo make ui-info
sudo make sim-hello
sudo make telemetry
sudo make check-visual
sudo make record-visual
sudo make ui-down
```

For headless environments, stop after `make verify-sim`.
In GUI mode, wait for READY and desktop windows before sending motion.

<!-- BEGIN QUICKSTART: docs/quickstart.commands.sh -->
```bash
# Command checklist, not an unattended demo. Run one line at a time.
# Working directory is the cloned or extracted g2-gazebo folder.
sudo make doctor
sudo make fetch-model ACCEPT_MODEL_LICENSE=yes
sudo make prepare-model
sudo make build-sim
sudo make verify-sim

# Optional visible desktop mode
sudo make sim-doctor
sudo --preserve-env=DISPLAY,XAUTHORITY,XDG_SESSION_TYPE make demo-visual
sudo make ui-info
# Look at the Ubuntu desktop first; startup has not sent any motion.
sudo make sim-hello
sudo make telemetry
sudo make check-visual
# Wait for this run_id to reach SUCCEEDED before recording another explicit motion.
sudo make record-visual
sudo make ui-down
```
<!-- END QUICKSTART -->

The same command block is stored in `docs/quickstart.commands.sh`; it is a checklist,
not an unattended animation. English and Chinese guides use the same block.
`verify-sim` is the full headless acceptance check. `record-visual` intentionally
requests **another** explicit motion; wait for the first one to finish. `ui-down` stops
only this extracted project's visual session.

## 4. Fetch the fixed model, with your own license acknowledgment

The selected official dataset is `agibot-world/GenieSimAssets`, repository type
`dataset`, revision **`a0813aad7c16165daffbe6c2737754e0344809ee`**. The variant is
`G2_omnipicker_fixed_dual.urdf`. The lock is `model_sources/g2.lock.json`.
It lists 11 input files totaling **59,390,249 bytes**: URDF/config, the composed
USD entry and referenced configuration layers, plus the source README and LICENSE.
This is a small fixed subset, not the full Genie Sim dataset. The GitHub G2 assets
with different restrictions are not used.

Read the [fixed source license](https://huggingface.co/datasets/agibot-world/GenieSimAssets/blob/a0813aad7c16165daffbe6c2737754e0344809ee/LICENSE)
and [CC BY-NC-SA 4.0 terms](https://creativecommons.org/licenses/by-nc-sa/4.0/).
**You**, as the recipient, must confirm that your use complies, including the
noncommercial condition; an earlier user's confirmation does not cover you.
`ACCEPT_MODEL_LICENSE=yes` records that acknowledgment for this lock in the local
cache. Preserve attribution and applicable ShareAlike requirements for adaptations.
Do not publish model-containing images without checking applicable terms.

```bash
sudo make fetch-model ACCEPT_MODEL_LICENSE=yes
```

Expected output includes `FETCHED` followed by each locked relative path. Raw files
are under `.artifacts/gazebo-model/raw/`; `acquisition.json` records file sizes/hashes.
Valid reruns report `CACHED`. Damaged cache files are quarantined before re-download;
size/hash errors, HTML/LFS pointers and authorization errors fail explicitly. Transport
retries are bounded. Normal public HTTPS requires no author token or browser session.
If the provider changes access requirements, follow the actual authorization prompt;
do not bypass it. First-run duration depends on connection/build speed and is not a
promised fixed number of minutes.

## 5. Convert and validate on Linux

```bash
sudo make prepare-model
python3 scripts/prepare_model.py --help
sudo python3 scripts/prepare_model.py --check-only
```

The preparation command builds a separate `Dockerfile.model-tools` image from fixed
official OpenUSD source, with its locked conversion dependencies; it does not require
a Linux ARM64 wheel or a Mac conversion host. Its image build checks actual Python
imports and an in-memory USD primitive. Conversion uses that tool image with no network,
read-only source/raw inputs and a writable new output directory. ROS remains on its
Humble Python interpreter. `make model-tools` can build the tool image independently;
there is no dependency on a prebuilt simulation image or generated model.

The default output is `.artifacts/gazebo-model/generated/`: `g2.urdf`, 106 OBJ meshes
and their MTL files, `joint_inventory.json`, `conversion.json`, source attribution,
and `generated_manifest.json`. The script checks file sets, hashes, converter/lock
identity, exact seven controlled left-arm joints, the connected world-rooted joint
tree, frozen non-task joints, and closed URDF/OBJ/MTL references. It retains source normals, inertias
and collision geometry, applies the documented same-source fixed-tool transforms,
and reduces the unused renderer-specific material system to diffuse MTL colors.

To test deterministic conversion into another empty directory:

```bash
sudo python3 scripts/prepare_model.py --output "$PWD/.artifacts/gazebo-model/generated-second"
sudo cmp .artifacts/gazebo-model/generated/generated_manifest.json \
  .artifacts/gazebo-model/generated-second/generated_manifest.json
```

A mismatch is an error to investigate, not a reason to ignore mesh differences.
For intentional source/converter changes, retain the old output and use `--output`
with a new directory. Never copy meshes out of an old image to satisfy a clean build.
Two conversion outputs may match byte-for-byte; this does not claim bit-for-bit
Docker images or physically identical floating-point trajectories on every host.

## 6. Build, installation checks and offline boundary

```bash
sudo make build-sim
sudo make sim-doctor
```

`Dockerfile.sim` fixes the Humble/Jammy base by digest, builds missing integration
components from the official fixed commits, and performs normal `colcon build`
plus installed console-script/share-resource checks. RViz2 and GUI dependencies
are installed during the image build. Package inventories and source hashes are
kept as evidence. The image name and persistent project identity are derived from
the extracted source directory to separate independent copies; a mismatched image
is rejected instead of silently running another version.

First fetch and image/tool builds need HTTPS to official dependency sources. Once
they and model conversion succeed, normal visual sessions and `verify-sim` use
Docker `--network none`, local installed world resources and a read-only model
mount at `/opt/g2-model`. They do not fetch from HF, Fuel or a private endpoint.
The model is not included in the source archive or publicly pushed in an image.
The build context is the extracted tree; no parent directory is copied.

A no-cache rebuild is `sudo make rebuild-sim`. It can consume substantial time and
disk. Do not prune other projects to free space. When troubleshooting raw Docker
commands, use the image shown by the build/session rather than an old fixed tag.

## 7. Open the real Gazebo/RViz/state desktop

Before startup in the **Ubuntu graphical terminal**:

```bash
printf 'DISPLAY=%s\nXAUTHORITY=%s\n' "$DISPLAY" "$XAUTHORITY"
test -r "$XAUTHORITY"
xauth -f "$XAUTHORITY" info
xrandr --current
sudo --preserve-env=DISPLAY,XAUTHORITY,XDG_SESSION_TYPE make demo-visual
sudo make ui-info
```

Use an existing desktop of at least 1280×800; 1600×900 is recommended. The launcher
copies only the selected display's authentication cookie to a mode-0600 session
file and mounts it plus the X11 socket. It does not print the cookie, disable X
access control, mount HOME, publish ports or change networking. That secret is
excluded from release archives and removed by `ui-down`.

You should see Gazebo on the left, RViz on the right, and **G2 Live State** below.
Gazebo should show the complete fixed-base G2. RViz's Fixed Frame is `world`, its
RobotModel listens to `/g2/sim/robot_description`, and the initial orbit view shows
the same model. Grid and TF displays are preconfigured; you need not add them.
The state window shows backend, sim time, source age, target joint, measured position,
run ID and terminal status. It is an observer/tool, not a third business controller.

On Mac, interact with these windows through the visible **Ubuntu Linux window in
Parallels Desktop**. On a local Linux desktop, interact directly. In Gazebo,
left-drag pans; Shift+left-drag or middle-button drag rotates; the scroll wheel
zooms. Right-button drag also zooms. In RViz's configured Orbit view, left-drag
rotates and the scroll wheel zooms. Place the pointer inside the scene before
dragging. See the [Gazebo camera controls](https://gazebosim.org/docs/fortress/gui/).
Do not use Gazebo object editing or teleport tools. A camera change must not change joint state. Closing/reopening
the Parallels display does not recreate the container or send an action. Close the
whole session with `ui-down`, not by individually closing a supervised GUI window.
Restarting the session restores the packaged camera/layout defaults and a fresh world.

A READY message establishes process/service readiness. Actual nonblank G2 rendering,
interaction and same-world synchronization require visual inspection and the
`check-visual`/recording evidence. No unattended one-shot motion is sent at startup.

## 8. Trigger motion and inspect measurements

Keep terminal 1 available, or open Ubuntu terminal 2 and `cd` to the **same extracted
directory**. Click **Say hello** in G2 Live State or run:

```bash
sudo make sim-hello
sudo make telemetry
sudo make check-visual
```

Do not use both triggers for the same intended action. The response contains
`accepted`/`run_id`; acceptance is not completion. Expect RUNNING and then SUCCEEDED
for that same ID, about **0.05 rad** excursion and return over **6 simulation seconds**.
Other controlled joints hold their measured baselines. A slow VM takes more wall time;
check the reported simulation/wall rates and real-time factor, not a stopwatch alone.
Repeated requests during motion are rejected and not queued.

`make telemetry` prints the current state snapshot plus one real public JointState,
then returns; the visible state window continues to update. `check-visual` is read-only:
it correlates raw/public same-stamp samples, the actual description and TF/FK. It does
not prove pixels are visible by itself. For a raw ROS inspection in this same container:

```bash
CONTAINER=$(sudo python3 -c 'import json; print(json.load(open(".artifacts/visual-session.json"))["container"])')
sudo docker exec "$CONTAINER" /opt/demo/docker/sim-entrypoint.sh ros2 topic info -v /g2/sim/joint_states
sudo docker exec "$CONTAINER" /opt/demo/docker/sim-entrypoint.sh ros2 topic echo /g2/sim/joint_states --once
sudo docker exec "$CONTAINER" /opt/demo/docker/sim-entrypoint.sh ros2 topic echo /g2/hello_status --once --qos-durability transient_local
```

`robot_state_publisher` is unique and reads the broadcaster, not a mock or
`joint_state_publisher_gui`. Both apps, RSP, controllers, RViz and observer use
`use_sim_time=true`. A single Gazebo→ROS clock bridge supplies `/clock`.

| Interface | Type / QoS / interpretation |
|---|---|
| `/g2/say_hello` | `std_srvs/srv/Trigger`; service acceptance only |
| `/g2/hello_status` | String JSON, reliable/transient-local; run_id, state, reason, actual command, result |
| `/g2/sim/arm_controller/follow_joint_trajectory` | `control_msgs/action/FollowJointTrajectory` |
| `/g2/sim/joint_states` | `sensor_msgs/msg/JointState`, actual broadcaster source; subscribers best-effort/volatile |
| `/g2/joint_states` | JointState, reliable/volatile; source stamps retained, target 10 Hz simulation time |
| `/g2/telemetry_health` | String JSON with source health, sim/wall rates and RTF |
| `/g2/sim/robot_description` | String, reliable/transient-local, same generated URDF |
| `/tf`, `/tf_static` | Dynamic and fixed transforms, connected to `world`; static TF transient-local |
| `/clock` | Simulation clock, one-way Gazebo source |

Angles are radians; velocities are rad/s. The target is `idx22_arm_l_joint2` among
seven left-arm joints. Do not assume its array index: resolve by JointState `name`.
Critical motion parameters are startup-only, not changed by `sim-hello`. Completion
requires the controller result plus measured excursion, return and stable feedback.
The 0.05-rad test requires 0.04–0.06-rad peak, endpoint/holding error below 0.002 rad,
and existing smoothness checks. GUI overhead does not relax these thresholds.

## 9. Recording, tests and independent release verification

```bash
sudo make record-visual
sudo make ui-down
sudo make test-sim
sudo make verify-sim
```

`record-visual` records the **existing** same-screen desktop at original wall speed,
explicitly triggers one additional motion through the existing service, and runs TF
and motion correlation. It does not spawn another simulator. Keep unrelated/private
windows off this desktop during capture. It returns after capture/checks; the visual
session remains until `ui-down`. Media are under the path reported by `ui-info`:
`record-*/gazebo-rviz-state.mp4`, screenshot, `media.json`, `tf-correlation.json`,
`motion/result.json`, source CSV, waypoint CSV, JUnit and recording/cleanup logs.
An entirely near-black video fails with `capture-quality.json`; wake/unlock the
Ubuntu desktop and record again in a new output directory. This check runs after
capture, so the requested motion may already have occurred. A non-black video
still requires actual model, motion and interaction inspection; it is not GUI PASS.

`test-sim` retains software regression and real physics fault checks. `verify-sim`
uses a new container, world state, transport partition and run ID, with no external
network; it does not commandeer the persistent UI. Evidence is under
`.artifacts/gazebo/<execution-id>/`. Stop the UI first when measuring headless
performance on a small VM. All waits have deadlines; failures preserve nonzero codes.
A Trigger rejection exits **2** for `sim-hello`; this is expected with ordinary
motion-disabled `sim-up`, and is not evidence of accepted motion.

To produce a source-only release and run the cold release experiment:

```bash
sudo make package-source
# Set ARCHIVE to the exact path printed above; keep its two sidecar files beside it.
ARCHIVE='/absolute/path/to/g2-gazebo-source-<source-id>.tar.gz'
sudo make verify-release ARCHIVE="$ARCHIVE" ACCEPT_MODEL_LICENSE=yes
```

Packaging includes uncommitted/untracked allowlisted source and both README files;
excludes `.git`, raw/generated assets, images, build outputs, credentials and old
artifacts; and creates an external checksum and manifest. It refuses to overwrite
an existing archive. `verify-release` extracts into a new `g2 release .../g2-gazebo`
directory under the system temporary directory, with a new HOME, Docker client
configuration and model/XDG/HF/pip caches. The verifier selects the local Unix
Docker daemon and system-installed CLI plugins; it does not copy author credentials.
It performs cold fetch, Linux conversion twice, a no-cache simulation image build,
regression and a new independent verify. Public Docker base/toolchain caches may
be reused; old model/output/project mounts are not inputs. This is isolation on an
existing Linux host, not a fresh OS installation.

The outside `acceptance/receipt.json` binds the archive hash and extracted source
hash. Its `SOFTWARE_PASS_GUI_PENDING` state is **not complete visual acceptance**.
Use the printed extracted directory, then repeat `demo-visual`, visible interaction,
`record-visual`, `ui-down`, and a cache-based restart there. Record those actual results
against the same archive hash outside the frozen source. If a code or README fix is
needed, package again and verify the affected flow on the new archive. Do not relabel
an old receipt as a new release. A separately supplied README must be byte-identical
to the copy in its archive.

## 10. Stop and restart

```bash
sudo make ui-down
sudo --preserve-env=DISPLAY,XAUTHORITY,XDG_SESSION_TYPE make demo-visual
sudo make ui-info
# No action has been sent by restart. Trigger explicitly when ready.
sudo make ui-down
```

`ui-down` stops/removes only the recorded project container, checks owned process
cleanup and deletes the display-cookie copy. It exposes no ports to leave open.
Abnormal component exits are errors even when no process remains; inspect
`cleanup.json` in the session evidence directory if stopping returns nonzero.
RViz starts from a session-local copy of the default configuration with window
geometry set before rendering. Gazebo uses Mesa `llvmpipe`; only RViz uses
Mesa `softpipe`. During development, llvmpipe crashed on exit, and softpipe alone
later failed to exit after a longer session despite passing short diagnostics.
The installed `agibot_g2_visual_tools/rviz2_close_order` entry point therefore stops
RViz update timers before processing a Qt Close event and before application exit.
It uses the official RViz application, displays, ROS signals and rendering libraries;
it does not replace joint data, animate the robot, or conceal abnormal exit codes.
The underlying Mesa/Xorg failure is not fully established; archive-bound acceptance
and shutdown results are recorded in the external receipt. The small entry-point
adaptation and upstream BSD attribution are included in `src/agibot_g2_visual_tools`.
On this VM, earlier dual-GUI measurements showed about 1 fps in RViz (visible pose
updates roughly every 1–1.6 s) and motion real-time factors of 0.81–0.89. Expect
visible display lag and interactive but unsmooth animation; consult the final
receipt for that archive's measurements. Control, TF and motion tolerances are unchanged.
Actual capabilities are recorded separately in `rviz-opengl.txt` and
`opengl.txt`; no OpenGL version override is used. The installed default
configuration is preserved, and restarting restores the default view.
It does not close the user's desktop or delete models/images/evidence. Validated
model/image caches are reused on daily startup. Do not rerun `ui-down` against a
missing session as a success test: a missing session is reported clearly.
Ordinary `make sim-up` still starts motion-disabled headless simulation; stop that
separate mode with `make sim-down`. Historical `make up`, `make test`, `make verify`
retain numerical mock meaning; mock success is not Gazebo evidence.

## 11. Troubleshooting

| Symptom | Check | Cause / correction |
|---|---|---|
| Download hash/size mismatch | Read acquisition error and lock; rerun `make fetch-model` | Inspect quarantined corruption; preserve lock and TLS verification; do not use main/latest |
| Download timeout / 403 | Check the named official URL's availability and actual HTTP error | Retry bounded transport failure; authorized access may require provider interaction; no token guessing |
| OpenUSD build/import/ABI error | `make model-tools`; read first build error and reported interpreter/module | Use the pinned native tool image; no wheel rename or Mac-only workaround; preserve failure log |
| Spaces in path / missing mount | Quote `"$ARCHIVE"`, `"$PWD/..."`; inspect image/model path from logs | Work inside extracted tree; do not manually split Docker mount arguments |
| Docker permission denied | `sudo docker version`; `sudo make doctor` | Use normal authorized sudo; do not make docker.sock world writable |
| Low memory/disk | `free -h`; `df -h .`; `sudo docker system df` | Stop this session/build; retain old artifacts; free only reviewed regenerable resources |
| Missing DISPLAY/XAUTHORITY | `printf '%s\n' "$DISPLAY" "$XAUTHORITY"`; `test -r "$XAUTHORITY"`; `xauth info` | Run inside the existing Ubuntu graphical terminal and preserve only these two variables with sudo |
| No clock/controller active | `make ui-info`; inspect `simulation.log` in its evidence directory | Check plugin/spawner errors and names; wait for genuine READY, not a fixed sleep |
| RViz blank / TF error | `make check-visual`; inspect `rviz2.log` and `/g2/sim/robot_description` | Use packaged RViz config, Fixed Frame world, correct description/QoS; do not add mock state publisher |
| Black or empty GUI | Inspect `opengl.txt`, `gazebo-gui.log`, `rviz2.log` | Check real Mesa/OpenGL context and X authorization; a window PID does not prove rendering |
| Slow movement | Compare sim time, source age, wall rate/RTF | Software rendering is slower; close unrelated loads without weakening motion tests |
| Service unavailable or duplicate request | `make ui-info`; wait for READY and terminal status | Do not start a second world or auto-retry an uncertain request |
| Existing/stopped visual session | `make ui-info`; then `make ui-down` | Cleanup recorded session before starting a replacement; ownership is checked |
| noVNC/WebSocket/localhost confusion | This main path publishes **no TCP ports** | Open the Ubuntu desktop in Parallels, not a browser localhost URL; VNC path is not validated here |
| Window closed individually | Inspect session/container log; run `make ui-down` | GUI processes are supervised; restart whole session to restore default layout |

## 12. Model assumptions and references

The base is fixed to `world` at 0.04 m; seven left-arm joints remain controlled.
Non-task movable joints are frozen in the recorded source pose. Original inertias
and collisions remain; same-source fixed attachments, normal seams and degenerate
faces have explicit conversion records. Diffuse materials replace renderer-specific
shaders. Standard Gazebo position control is a simulation approximation, not a
calibrated G2 motor model. No whole-body balance, navigation or grasp planning is
claimed, and no simulation result proves GDK compatibility or physical robot safety.

Gazebo scene and sunlight shadows are disabled to mitigate observed intermittent
surface rendering artifacts with Ogre 1 / Mesa. This display setting preserves
mesh geometry, lighting, gravity and collisions. The underlying rendering cause
has not been established; acceptance of this mitigation is recorded separately
against the final source archive.

See `docs/model_sources.md`, `docs/simulation_assumptions.md`, and
`docs/reproduction_gap_audit.md`. The old recording-only guide is preserved in
`docs/README_gazebo_recording_historical.md` and is not the new user's procedure.
Official references used for this incremental implementation:
[Humble/Fortress pairing](https://gazebosim.org/docs/fortress/ros_installation/),
[Fortress graphics troubleshooting](https://gazebosim.org/docs/fortress/troubleshooting/),
[Humble robot_state_publisher](https://github.com/ros/robot_state_publisher/blob/humble/README.md),
[OpenUSD source](https://github.com/PixarAnimationStudios/OpenUSD),
[Docker Ubuntu installation](https://docs.docker.com/engine/install/ubuntu/).
