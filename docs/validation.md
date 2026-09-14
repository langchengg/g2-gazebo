# Current validation summary

This summary records what was executed for the submission-readiness branch. It
does not turn a prerequisite check into runtime acceptance and does not reuse the
historical Gazebo report as current evidence.

## Tested source identity

- Validation date (UTC): `2026-09-14`
- Executable source commit: `15495a9ad801dd74c6fd636db9934808f447e361`
- Public baseline at test time: `origin/main` at
  `7a276bfc7ddd7e6ec68c5c573a7e36b48869fe8c`
- Acquisition: `git archive` of the exact executable commit, extracted into a new
  VM-native directory. The extracted tree had no `.git`, generated model, build,
  install or log directories.
- Runtime manifest: 87 files, SHA-256
  `f42e0e196e9c161f890997c71e1deda135ca6b800f703166ed20ed95917ff93d`.
  The manifest matched on the Mac repository, the new VM directory and the built
  image.
- This report and its JSON receipt were added after the executable source was
  tested. They are delivery-only files excluded by the documented runtime manifest
  scope. The tested runtime hash above is unchanged. The report commit is the Git
  commit containing this file, so it is intentionally not self-referenced here.

The earlier dangling local commit `1bbe2d4` was not the public improvement commit
and did not contain the doctor correction. Its old validation text is superseded.
The public improvement commit before the correction was `ad21105`; the doctor fix
was then committed as `15495a9` and is the executable source tested below.

## Platform status

| Environment | Preflight | Build | Runtime | GUI |
|---|---:|---:|---:|---:|
| Ubuntu 22.04.5, native arm64 | PASS | PASS | PASS | Automated X11/render/TF PASS; fresh Mac-visible pixel check BLOCKED by Ubuntu lock screen |
| Ubuntu 22.04, native amd64 | Supported by preflight logic | NOT TESTED | NOT TESTED | NOT TESTED |
| Emulated cross-architecture execution | Classified by doctor | NOT TESTED | NOT TESTED | NOT TESTED |

`make doctor` reports `validation_status=NOT_TESTED` on every platform because it
checks prerequisites only. Runtime PASS is assigned here only from the actual test
run. ROS 2 Humble supports Ubuntu 22.04 arm64 and amd64, but that upstream platform
support does not by itself validate this project's amd64 model toolchain or simulator.

## ARM64 execution and results

The VM used Ubuntu 22.04.5 on a native `aarch64` kernel. Docker 29.8.0 used the
local `unix:///var/run/docker.sock` daemon; the daemon and running default Buildx
worker both reported `linux/arm64`. No remote Docker override was present.

The fixed model was fetched into the new source tree from
`agibot-world/GenieSimAssets` at revision
`a0813aad7c16165daffbe6c2737754e0344809ee`. The lock SHA-256 was
`a7567a2953c73c7c525d9fdbc8951a4c45ed53d0bd6dd82670f68aa0dd3223ab`:
11 files and 59,390,249 bytes were downloaded and verified. Linux conversion ran
against those files and produced 106 meshes and a 217-file generated manifest.
A previously built native ARM64 model-tools image was reused only after its source,
Dockerfile label and architecture matched; no generated model or simulation image
was reused as input.

Commands below were run from the new extracted directory:

| Command | Exit | Result |
|---|---:|---|
| `make doctor` | 0 | `preflight_result=PASS`, `validation_status=NOT_TESTED`, no errors or warnings |
| `make fetch-model ACCEPT_MODEL_LICENSE=yes` | 0 | 11 locked files fetched and hash-checked |
| `make prepare-model` | 0 | Linux conversion and generated-model validation passed |
| `make build-sim` | 0 | Three ROS packages built and installed with colcon |
| targeted doctor pytest in the simulation image | 0 | 18 passed |
| `make test-sim` | 0 | 484 colcon tests passed; 29 separate Gazebo acceptance/fault/cleanup cases passed |
| `make verify-sim` | 0 | Independent world and run ID; 6/6 acceptance cases passed |
| `make demo-visual` / `make check-visual` | 0 / 0 | Gazebo, RViz2 and observer windows; 147 TF/FK samples passed |
| `make sim-hello` / `make telemetry` | 0 / 0 | Explicit motion succeeded and live Gazebo telemetry was returned |
| `make ui-down` | 0 | All owned processes exited with code 0; no owned PID or container remained |

The new simulation image was `agibot-g2-sim:fortress-bbbfe50d83`, ID
`sha256:316bca2d34134d08744875acc33c634966a70664d46b1e79864f2aa8fa311055`,
and reported architecture `arm64`. Public Docker/base/toolchain layers were cached;
the application image itself was built from the exact extracted candidate and its
embedded runtime manifest matched the source.

The independent `verify-sim` run ID was
`f196d1028631430985dbc9122808f240`. The requested displacement was 0.05 rad;
measured peak displacement was 0.04996603245366015 rad, final maximum return error
was 0.000011127090840932436 rad, non-target error was
`1.7169649898651914e-11` rad, and measured real-time factor was
0.9998331966804614. All 68 public telemetry samples matched simulator samples by
joint name, source timestamp and position.

The GUI session did not send motion at startup. An explicit request used run ID
`c5ac1f66b2b14d05b2416abc6e0b3979`, reached `SUCCEEDED`, and reported a
0.04997027709300109 rad excursion. Gazebo and RViz2 rendered through Mesa software
drivers. The same description, `world` fixed frame, simulator joint state and TF
were checked across 147 samples; maximum FK matrix absolute error was
`5.551115123125783e-16`. Process, Xauthority-copy and container cleanup passed.
The first GUI preflight correctly rejected the desktop's 1024x768 mode; after the
existing 1600x900 Xorg mode was selected, the documented command reached READY.
The Parallels display was at the Ubuntu lock screen when a fresh host-side capture
was attempted, so this commit has no new claim of a human-inspected visible frame.

## Evidence and boundaries

The repository contains the compact machine-readable result at
[`docs/validation-evidence/arm64-20260914.json`](validation-evidence/arm64-20260914.json).
Full raw evidence was retained outside Git under five archives; their filenames and
SHA-256 values are recorded in that receipt. Those archives include command logs,
JUnit, motion CSV/JSON, source/telemetry correlation, TF/FK samples and cleanup
records. They contain no model mesh in the public branch.

Native amd64 runtime and GUI remain **NOT TESTED**. The current branch does not
claim a Release asset, does not contain the restricted model, and has not been
merged into `main` by this validation record.

Official compatibility references checked for this text:

- [ROS 2 Humble release platforms](https://docs.ros.org/en/humble/Releases/Release-Humble-Hawksbill.html)
- [ROS REP-2000 target platforms](https://www.ros.org/reps/rep-2000.html)
- [Docker multi-platform build modes](https://docs.docker.com/build/building/multi-platform/)
- [Docker Engine installation on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
