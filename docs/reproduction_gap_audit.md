# Source archive reproduction gap audit

## Scope and evidence boundary

This audit compares the historical recording-only delivery with the new source-only
Linux conversion and visible Gazebo/RViz desktop workflow. Implementation status
below is a code inspection result, not an execution PASS. Final acceptance belongs
in an external receipt bound to the final archive SHA-256. Historical simulation
results must not be reassigned to a new archive.

Inspected baseline archive: `g2-gazebo-simulation-source-20260913.tar.gz`,
264,470 bytes, 98 regular files, SHA-256
`aafdf0b43755e06cd5e785ee9485fb3210da83fbcb5a583875f24e37fd470c12`.
It contained no absolute/parent-traversal paths, symlinks/hardlinks, `.git`, model
cache or private transfer scripts. Shell entrypoint permissions were preserved.
It lacked a common top-level directory and depended on externally converted assets.

## Findings, fixes and required verification

| Finding | Implementation / location | Required evidence / current status |
|---|---|---|
| Mock repeat regression can falsely trip the acceleration guard after a long then short callback interval | `backends/mock_backend.py` and `test_motion.py`: integrate a continuous 20 ms input ramp in the synthetic first-order follower and report endpoint velocity; preserve the independent acceleration guard, threshold and fail-before-publication behavior | Candidate 46c passed its independent Gazebo motion check but failed 1 of 471 software tests. Deterministic 40 ms then 1 ms and 20 ms then 1 ms reproductions identify interval-average velocity timing and held-command discontinuities. The corrected source requires a new archive and complete regression; the failed receipt is retained. |
| The VM exhausted free disk during consecutive application builds | README recommends 15 GiB for first builds; external resource logs preserve both zero-free-space samples | Successful build exit codes do not prove adequate resource margins. Before another experiment, preserve evidence and reclaim only reviewed regenerable resources created in this task; record fresh free space and the full build peak. |
| A desktop standby capture contained 419 black frames despite valid action/TF data | `scripts/record_visual.py` checks every decoded frame's mean full-range luma with installed FFmpeg; an entirely near-black video fails and retains `capture-quality.json` | Actual VM FFmpeg 4.4.2 rejected the black recording and accepted the non-black gate for the earlier visible recording. Brightness is only a negative screen test: actual model, motion and user interaction remain separate mandatory evidence. |
| A22 falsely accepted RViz SIGSEGV; 4650 correctly rejected it; 2cc softpipe later hung at shutdown | Strict component exit checks remain. `src/agibot_g2_visual_tools` builds an attributed official-RViz entry-point adaptation with update timers stopped before Qt Close and application exit; `visual_session.py` uses its installed executable, with the same softpipe renderer | 2cc archive `e017886001a8219859c7839ff040bdc3daa541a1ee4f46464ccf43c4d4bc8ef4` passed software, visible motion and TF but required RViz SIGKILL after a roughly 19-minute session: overall FAIL. Three earlier short softpipe passes did not prove stability. First close-order diagnostic executed both hooks and shut down all components normally without GDB; long-session and final-archive checks remain external receipt requirements. Root cause is not fully established; old failures are retained. |
| A cached build after acceptance may change Docker OCI image identity despite matching source | `scripts/release.py` exercises documented `build-sim` before the no-cache `rebuild-sim`, then tests and records the resulting image | Final acceptance must retain the post-rebuild image identity; no extra build is run between automated and visual acceptance |
| Linux ARM64 preparation explicitly stopped and asked for Mac conversion | `Dockerfile.model-tools`, `scripts/prepare_model.py`: native official OpenUSD build, separate from ROS runtime; true import/primitive smoke; no Mac interpreter path | Implemented; build compatibility and cold Linux conversion require final receipt, not historical PASS |
| First-use instructions assumed an author checkout and fixed VM directory | `README.md`, `README.zh-CN.md`, `docs/quickstart.commands.sh`: archive-relative Linux procedure, public desktop/tool prerequisites | Both languages share identical shell blocks; end-to-end execution remains receipt-bound |
| No live user interface; Xvfb video was the only deliverable | `scripts/ui_manage.py`, `scripts/visual_session.py`: persistent existing-desktop session, return after READY, no automatic goal | Need actual visible desktop interaction, same-world recording and reconnect/reopen observation |
| RViz and installed default config absent | `Dockerfile.sim`, `src/agibot_g2_demo/config/g2_demo.rviz`, package/setup resource rules, `scripts/check_install.py` | Need installed config lookup, correct description QoS, real loaded G2 pixels and TF evidence |
| Intermittent missing-looking surfaces in the real Ogre 1 / Mesa Gazebo view while RViz displayed the same complete mesh | `src/agibot_g2_description/worlds/g2_demo.sdf`: disable scene and sunlight display shadows; retain lighting, meshes, gravity and collisions | Mitigation only; the light-toggle comparison did not establish the underlying cause. Fresh startup with shadows disabled requires final archive-bound GUI acceptance |
| No same-source TF/GUI correlation | `scripts/verify_visual.py`, `visual_geometry.py`, `record_visual.py` | Need raw/public identical samples, actual description hash, unique RSP/RViz and FK/TF matrices during the recorded run ID |
| UI state and explicit trigger unavailable | `scripts/visual_observer.py`: read-only clock/state subscribers plus existing Trigger client; installed Python apps unchanged | Need READY/state age/run ID, motion accepted then matching terminal status; no startup/reopen action |
| Image tag and ordinary Compose project were global to all copies | `scripts/sim_manage.py`, `scripts/ui_manage.py`: source-root-derived image/project identity and ownership label/receipt | Need independent extracted directory run without stopping/reusing the author's session |
| Packager omitted new top-level files | `scripts/source_manifest.py`: model-tools Dockerfile and Chinese README added to allowlist; runtime COPY must match | Need archive file manifest and installed image/source identity equality |
| Old archive had no deterministic top-level packaging or safe independent extraction tool | `scripts/release.py`: `g2-gazebo/` prefix, normalized tar owner/time, external checksum/manifest, entry/content validation | Need final package excluded-input scan and extraction into a fresh path containing spaces |
| No actual cold archive reproduction command | `make verify-release`: new extracted source plus model/XDG/HF/pip cache, two conversions, no-cache simulation build, regression and verification | Code implemented; `SOFTWARE_PASS_GUI_PENDING` is deliberately incomplete until visible acceptance is appended externally |
| Future recipient's model license acknowledgment was not explicit | `scripts/fetch_g2_model.py`: caller acknowledgment bound to lock; README license section | Need first fetch refusal without acknowledgment, explicit accepted fetch, no inherited author token/consent |
| Cache corruption could overwrite the old damaged object | Downloader isolates invalid cached files under `quarantine` and uses temporary/atomic replacement | Need corrupt-cache, HTML/LFS/error, checksum and immutable revision tests; real cold HTTPS download |
| Dependency closure was not tied strictly to the lock | Converter's used-layer/asset checks and pinned model lock; renderer-specific material simplification documented | Need every used input listed and hashed, no old cache/parent mount, actual no-network conversion and simulation |
| Generated output could contain stale files | Empty-output rule and `validate_generated` exact file-set/hash checks | Need two empty-output conversions, identical manifests or explained semantic differences, corruption rejection |
| No preserved copy of old operational instructions | `docs/README_gazebo_recording_historical.md` | Historical file preserved without overwriting a pre-existing copy |
| UI secrets could accidentally enter delivery | Single display cookie in ignored session evidence; source allowlist excludes artifacts; removal on `ui-down` | Need mode/limited-cookie mount review, package scan and actual cleanup; never print the cookie |

## What was already reusable

The old source archive already included complete Python application code, ROS package
metadata, launch, controllers/world, model lock, downloader/converter and tests.
The converter had the substantive fixes for units, composed USD geometry, normal
seams, material subsets, six same-source fixed attachment transforms, collision and
inertia checks, and exact zero-area face filtering. These were not hidden manual Mac
steps. The platform-dependent OpenUSD execution path was the missing part.

The baseline lock listed 11 files totaling 59,390,249 bytes. All six used layers
reported by the prior conversion were members of that lock. The current cold run
must establish this again from fresh inputs. Constant diffuse colors intentionally
replace the unused OmniPBR/renderer material implementation; this is documented
simplification, not an implicit request to fetch an entire shader ecosystem.

Container paths `/opt/demo` and `/opt/g2-model` are defined internal install/mount
contracts, not author host paths. Runtime scripts derive their source root from
`__file__`; subprocess argument lists and Compose long bind syntax avoid shell
splitting of spaces. Actual relocation still needs execution evidence. Paths with
commas have additional Docker mount-syntax constraints and are not advertised as
part of the tested space-path requirement.

No build depends on Git HEAD or `git archive`. Dockerfile Git fetches refer to
explicit official integration commits during dependency build, not the application's
Git history. Host doctor may report missing Git metadata without invalidating a
source extraction. Source contents, not an unborn HEAD, identify the tested version.

## Network, desktop and permissions

The selected interactive delivery path requires an already working Ubuntu Xorg
login session. The first Wayland/XWayland attempt could create windows but failed
full-desktop X11 capture (`GetImage` denied); it is not a supported recording path.
This VM has a visible GNOME desktop and Parallels Tools; Mac
viewing uses the ordinary Parallels Ubuntu window. Other qualifying Linux hosts
use their local desktop. There is no required author-only command channel in the
archive. Development Parallels guest commands, private transfer endpoints, SSH
credentials and prior artifacts are not release inputs.

The UI shares only its selected display authentication cookie and X11 socket,
plus project model/evidence paths. The container has no external network and no
published ports. Do not replace this with `xhost +`, privileged mode, host networking,
HOME or Docker-socket mounts. The optional VNC code is not the tested public main
path; this audit does not label noVNC/browser access PASS.

## Final acceptance procedure

Follow-up inspection before release freezing additionally found and repaired:

- Whole-file download deadlines now include slow streaming and retry backoff;
  timeout tests interrupt stalled reads and retain damaged-cache evidence.
- Generated-model validation checks exact joint names, a unique connected world
  root, fixed non-task joints and URDF/OBJ/MTL reference closure independently of
  the output checksum manifest.
- `docs/model_sources.md` now identifies the Mac-only procedure as historical;
  the current procedure uses Linux model-tools.
- Desktop window selection must exclude pre-existing windows and check process
  ownership. Slow-motion recording must retain the matching terminal TF samples.
- Release command timeouts must retain exit code and elapsed time. Release HOME,
  client configuration and download caches are isolated; daemon checks reject
  nonlocal/non-ARM64 execution. Final receipt includes model lock and image identity.
- Packaging rejects model/media binaries and private environment files accidentally
  placed under the source directories, in addition to excluding artifact caches.
- Actual GUI startup exposed a successful finite installation probe being treated
  as a failed persistent component. Readiness now tracks only persistent components;
  finite probe results remain in the command and cleanup receipts.
- Actual RViz loading rejected bare absolute mesh filenames accepted by Gazebo.
  The converter now produces explicit local `file:///opt/g2-model/...` URIs in the
  single shared URDF; the new converter hash requires fresh conversion and separate
  Gazebo/RViz loading checks. This follows Humble RViz's resource_retriever contract.

These changes require execution against the newly frozen archive; passing unit
tests and earlier candidate conversions are not reassigned to that archive.

1. Freeze source and both READMEs; create the source-only archive and sidecars.
2. Verify archive structure/hash, extract to a new Linux path with spaces, and
   confirm no `.git`, model cache or old generated data exists there.
3. Use only the extracted source plus permitted public system/base/toolchain caches.
   Cold-fetch the pinned inputs and convert twice on native Linux ARM64.
4. Build the simulation image from this archive without old project build layers;
   save normal colcon results, image identity, source and model manifests.
5. Run regression and an independent network-isolated physics verification.
6. Open the persistent visible desktop from that extracted directory. Inspect real
   Gazebo/RViz G2 rendering, camera interaction, source/TF/state correlation, explicit
   motion, pause/resume and display disconnect/reopen behavior.
7. Record the same-screen run at original wall speed, stop and verify cleanup;
   restart using validated caches without fetching or recompiling.
8. Keep the acceptance receipt outside the frozen source. If code/docs change,
   create a new archive and revalidate affected flows against its new hash.

## References checked

Additional execution findings before source freeze:

- In diagnostic session `20260914T054313Z-abe094`, Gazebo showed missing-looking
  chest surfaces while RViz showed the complete model. Disabling sunlight shadows
  coincided with recovery, but enabling them again did not reproduce the defect.
  A subsequent fresh startup of the original configuration showed a different
  affected body region. This is insufficient evidence to attribute the defect to
  a specific shadow algorithm or converter fault. The new world disables scene
  and sunlight shadows as a display mitigation, pending fresh-start GUI testing;
  no geometry or physics setting was changed. External diagnostic command records
  are `light-shadows-off-diagnostic.json` and `light-shadows-on-diagnostic.json`;
  screenshots and final acceptance belong in the external release evidence.

- The disabled-motion probe could finish after a telemetry callback but before its
  corresponding raw callback (observed final stamps 15.470 s and 15.460 s).
  `verify_sim.py` now freezes the public sample set and waits at most three wall
  seconds, within the overall deadline, for every corresponding raw stamp. Missing
  middle/tail samples still fail; numerical tolerances are unchanged. Focused tests
  cover delayed callbacks, permanent loss and mismatched measurements.
- `verify_visual.py` and `record_visual.py` only mark success after all checks;
  interruption writes FAIL. Recording requires an actual FFmpeg progress block
  reporting at least one frame before starting the explicit motion probe.
- An isolated rendering diagnostic loaded both models with RViz RobotModel Status
  OK after the file URI correction. This is not evidence of Mac desktop access.
  Final interactive acceptance remains a separate user-visible test.

Local source and archive contents were primary evidence. Official references were
used for compatible APIs and installation behavior, not as execution proof:

- [Humble/Fortress pairing](https://gazebosim.org/docs/fortress/ros_installation/).
- [Docker Ubuntu installation](https://docs.docker.com/engine/install/ubuntu/).
- [Docker port publishing](https://docs.docker.com/engine/network/port-publishing/):
  an unspecified host bind is not a localhost-only bind; the selected desktop path
  publishes no TCP ports at all.
- [Humble robot_state_publisher](https://github.com/ros/robot_state_publisher/blob/humble/README.md):
  transient-local description/static TF, movable TF from JointState.
- [noVNC official README](https://github.com/novnc/noVNC): websockify can be downloaded
  by its convenience proxy; any future validated VNC path must install dependencies
  during build rather than silently fetch them at runtime.
- [OpenUSD official source](https://github.com/PixarAnimationStudios/OpenUSD).
- [Fixed model license](https://huggingface.co/datasets/agibot-world/GenieSimAssets/blob/a0813aad7c16165daffbe6c2737754e0344809ee/LICENSE).

The ROS-hosted RViz guide returned a site challenge during the initial web audit;
no bypass was attempted. Actual installed Humble RViz configuration and rendering
remain the relevant acceptance checks.
