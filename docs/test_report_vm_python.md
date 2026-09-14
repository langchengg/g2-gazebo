# Ubuntu VM / Python acceptance report

**PASS: Python mock software acceptance in the actual Ubuntu VM.** Hardware
SDK loading and G2 tests remain unverified. This report contains new evidence,
not the historical C++ or Mac Docker results.

## Execution identity

- Final acceptance started **2026-09-08T22:00:38.367748+00:00**, completed through all 16
  command steps with the expected exit codes. Initial migration acceptance at
  21:56:38Z also passed; the final pass includes the corrected cleanup scope label.
- Mac source: `/Users/delaynomore/Downloads/test`, branch `test/g2-demo`.
  No commit or push was made. The pre-migration 40-file snapshot and historical
  C++ package are preserved; see `python_migration.md`.
- VM copy: `/home/lang/projects/agibot-g2-ros2`, native Linux filesystem.
  VM `Ubuntu Linux` / UUID `c50f53af-2f2f-4cd6-915b-11842281c67d`, hostname
  `lang`, user `lang` (UID1000); normal sudo used for Docker. No new group
  membership or NOPASSWD rule was created.
- OS: Ubuntu22.04.5, kernel5.15.0-191-generic, `aarch64` / dpkg `arm64`,
  Parallels. System/container Python **3.10.12**, ROS **Humble**,
  container pytest **6.2.5**. VM memory5.8GiB, root free18GiB before installation.
- Docker client/server **29.8.0**, Compose **5.5.1**, Buildx **0.37.0**,
  BuildKit **0.33.0**. Daemon `lang`, local
  `unix:///var/run/docker.sock`; systemd MainPID5378 matched `/proc/.../comm`
  `dockerd`. Buildx driver `docker`, endpoint `default`, native `linux/arm64`.
  `DOCKER_HOST` / `DOCKER_CONTEXT` were unset. No Mac Docker daemon or x86
  emulation was used for this acceptance.
- Base index: `sha256:75dd3aba34a3838dadbb31a9f7bef769bdfa8713e6cec686fc868db2981b0987`.
  VM-side registry inspection confirmed linux/arm64/v8 descriptor
  `sha256:bfa845027d9606fd8615a04110f768fd79c8ad94f3a75d6e1392860bca4db51b`.
- Final tested Docker image ID: `sha256:ded15ba091c79b1157068b0285a6f6a89356afae271874a78abdb57f1a1c36c0`.
- Runtime source manifest (37 files):
  `993e656266756908544da51e881a7d1582dab15f343dcdb30c961bdad224a7ab`.
  The same content manifest was checked on Mac, VM and in the image. The image
  is built using ordinary colcon installation, without symlink-install/source mounts.

## VM access and preservation of boundaries

OpenSSH was confirmed present; `sshd -t` succeeded and the service was started.
It reports active and listens on both IPv4/IPv6 port22. Host ED25519 fingerprint
was obtained from the VM itself:
`SHA256:FUG/+vI9ESZVzydkUpSPOxhga5DUiO3G9c+9ffJKs/A`.
Mac-initiated SSH still returned255, `No route to host`; no successful SSH
login is claimed. The existing UFW state was inactive and was not changed.
VM-to-Mac private ping/HTTP succeeded. NAT, router and VM NIC settings were unchanged.

The usable execution channel is the installed Parallels27 supported
`send-key-event` CLI, with CUA for console inspection. Guest Tools are absent;
this supported console-key path was verified without them. Initial CUA input
lost keys and clipboard attempts timed out; decimal scan-code/JSON-stdin input
worked. A temporary server bound only to Mac's private VM interface accepted
only this VM and allowlisted project files/evidence. It did not serve the
repository root, credentials, full vendor pages or SDK files. Source changes
were made on Mac, transferred with per-file hashes, and the VM was checked
against its previous manifest before each update. Evidence was copied back to
a new Mac directory; no historical artifacts were overwritten.

No passwords were written to commands, scripts, repository, environment files
or logs. Mac Remote Login, public port forwarding, root SSH, firewall rules,
Docker socket permissions and security settings were not changed.

## Commands and actual exits

The console invoked the acceptance script under normal Ubuntu sudo; all
commands below executed inside the VM. `make hello` exit2 is the expected
negative result for the disabled-motion default, verified from its JSON response.
All other listed exits are0.

| Command | Exit | Elapsed seconds |
| --- | --- | --- |
| `docker context inspect --format {{json .Endpoints.docker}}` | 0 | 0.018 |
| `docker info --format {{json .}}` | 0 | 0.033 |
| `systemctl show docker -p MainPID --value` | 0 | 0.004 |
| `docker buildx imagetools inspect --raw ros:humble-ros-base-jammy@sha256:75dd3aba34a3838dadbb31a9f7bef769bdfa8713e6cec686fc868db2981b0987` | 0 | 0.934 |
| `make doctor` | 0 | 0.220 |
| `make rebuild` | 0 | 11.251 |
| `make build` | 0 | 0.416 |
| `make up` | 0 | 0.925 |
| `make hello` | 2 | 0.673 |
| `make logs` | 0 | 0.168 |
| `make down` | 0 | 0.725 |
| `make test` | 0 | 47.289 |
| `make verify` | 0 | 7.412 |
| `make verify` | 0 | 7.663 |
| `make demo-mock` | 0 | 7.508 |
| `python3 scripts/check_runner_cleanup.py --also-launch-checks` | 0 | 5.173 |

`make rebuild` actually passed `--no-cache` to Compose build. Dockerfile ran
`colcon build --event-handlers console_direct+` and installed entrypoint/resource
checks. The test container ran `colcon test --event-handlers console_direct+
--return-code-on-test-failure` and `colcon test-result --verbose`, both exit0.

## Test counts and Python identity

**223 pytest cases passed: 197 unit (161 motion +36 GDK mapping/IPC), 26 real ROS
integration. Zero failures, errors or skipped tests.** Colcon's summary agrees.
Lint/static checks are separate and are not counted as tests. Hardware tests
were not executed; they were not replaced by skipped mock tests.

The two process identities contain installed script paths, `module.__file__`,
interpreter version, `/proc` executable and command line. Both entrypoints use
`#!/usr/bin/python3`; actual process executable is `/usr/bin/python3.10`, and
modules load from `/opt/demo/install/agibot_g2_demo/lib/python3.10/site-packages/`.
The integration graph checks exactly `/g2/sayHello` and `/g2/telemetry`, excluding
temporary test probes. No legacy ELF or C++ subprocess wrapper is used.

Tests cover default rejection and unchanged observations, enabled service/topic
motion, current run_id/RUNNING/terminal correlation, concurrent rejection,
retained previous success, nonzero/signed/boundary initial conditions,
finite/name/array/config checks, observed target/other-joint behavior, source
freshness/repetition, all eight injected faults, unavailable GDK fail-closed,
read-only parameters, simulated-clock rejection, SIGINT/SIGTERM and partial
startup/runner cleanup. GDK tests use project fixtures only, never a fake
`agibot_gdk` module or vendor message package.

## Two independent final mock runs

These measurements were computed from the current service-triggered ROS
samples. They were not copied from historical results.

| Run | Accepted run_id | Action samples | Hz | Peak excursion rad | Final error rad | Observed window s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `a0b3204b443849579cd504d27e765d6f-1` | 47 | 10.010426 | 0.049947979 | 4.81765334e-07 | 4.595209 |
| 2 | `c7493c6ffb09499a98c572f44435b9f8-1` | 48 | 10.014926 | 0.049936633 | 2.70397504e-07 | 4.692995 |

Each run used a distinct Compose project and fresh backend state. Samples before
the request establish the baseline; only the accepted run_id can finish the
request. Test assertions require the target to move, all other joints to hold,
return within tolerance and a matching successful terminal state. Frequency is
computed as `(N-1)/(last_receive-first_receive)` with explicit 7–13 Hz tolerance
for the 10 Hz target; source stamps are separately checked for monotonic progress.
Raw JSON preserves positions, velocities, empty effort, names and timestamps.
Derived CSV files contain the same position samples for inspection.

## Stopping and fault evidence

The final cleanup suite passed. SIGTERM was delivered during observed RUNNING;
the manager exited143 as expected and both its container and network lists were
empty. Normal Compose stop returned a container ExitCode0, Running=false,
OOMKilled=false; its resources were removed. Explicit unavailable-GDK launch
returned1 and cleaned its resources. Node SIGINT/SIGTERM and the test-runner
signal paths also passed inside the26 ROS integration cases.

## Evidence locations

All paths below are under the Mac repository; the VM retains its original
`.artifacts/<action>/...` paths.

- Complete copied evidence: `.artifacts/vm-python/20260908T220038Z-a043be/`.
- Command/environment trace: `.artifacts/vm-python/20260908T220038Z-a043be/vm-acceptance/20260908T220038Z-a043be/`.
- JUnit and grouped summary: `.artifacts/vm-python/20260908T220038Z-a043be/test/20260908T220053Z-ae4638/pytest.xml`,
  `.artifacts/vm-python/20260908T220038Z-a043be/test/20260908T220053Z-ae4638/test-summary.json`; adjacent colcon logs retain build/test output.
- First run: `.artifacts/vm-python/20260908T220038Z-a043be/verify/20260908T220141Z-2f19c1/clean-e2e-4cca90b2/` (identity, states, health, samples.json,
  samples.csv, metrics JSON).
- Second run: `.artifacts/vm-python/20260908T220038Z-a043be/verify/20260908T220148Z-beaa6a/clean-e2e-864aebf3/` (same evidence files).
- Lifecycle result: `.artifacts/vm-python/20260908T220038Z-a043be/runner-cleanup/20260908T220203Z-9b959426/result.json`.
- VM initial identity/installation and transfer receipts:
  `.artifacts/vm-channel/incoming/`.
- `received-evidence-manifest.json` records archive SHA256 and hashes of every
  extracted regular file. Links/traversal/non-file archive members were rejected.

## Fixes and independent review

- Fixed an inherited scheduling jump: a 0.49 s sub-watchdog delay could exceed
  mock velocity/acceleration limits. Bounded phase advancement and observed
  limits now fail closed; seven new deterministic-clock regressions pass.
- Corrected colcon JUnit handling: overriding pytest's output path would leave
  colcon's placeholder result. The default result is now copied and inspected;
  empty/missing/failed suites cannot pass.
- Added pre-run image/source comparison and refreshed post-build image IDs,
  preventing a stale image from being reported with a newer working-tree hash.
- Test timeout/parse failures retain a structured error and available logs;
  child groups and uniquely owned Compose resources have bounded cleanup.
- Corrected a historical Mac-only scope label in the lifecycle report; final
  runtime rebuilt and the complete VM acceptance rerun, retaining earlier evidence.

## Documentation and hardware boundaries

The existing version-specific43-page ledger and282 API records were preserved.
This pass selectively reread relevant Python/control/state/deploy/ROS/time/error
sections; the integrity audit reports43 discovered,43 fetched,43 READ_COMPLETE,
0 blocked,0 version mismatch and no integrity issues. Full vendor bodies remain
in the ignored Mac cache. Downloaded files alone are not counted as new reads.

GDK interface status: **PARTIAL**. Direct Python read-only implementation:
**DOC_IMPLEMENTED / SDK_UNVERIFIED**. Actual calls are limited to documented
`gdk_init()`, `Robot()`, `get_joint_states()`, `gdk_release()`; exact sources,
fields and independent verification states are in `gdk_api_mapping.md`.
No real binding has been imported/loaded and no SDK package installed.
Actual SDK ARM64/ABI compatibility remains UNVERIFIED, not inferred from Python
or mock success. G2 read-only telemetry and arm movement are **NOT RUN**.
Arm movement remains UNIMPLEMENTED pending verified control/stop/completion
semantics, real mapping, supported package/firmware and on-site authorization.
Native Ubuntu without Docker and x86 platforms are also NOT RUN.

## Capabilities and external references

Used Git, Python standard-library tooling and uv/pytest for source preservation,
local checks and manifests; installed Parallels CLI/CUA for VM inspection/input;
Ubuntu apt/sudo, Docker Engine/Compose/Buildx and colcon/rclpy/pytest for actual
VM execution. Independent agents implemented/reviewed the core, ROS wrappers
and GDK evidence in separate file scopes. No unrelated connector, simulator,
VM installer or additional production Python dependency was needed.

Official ROS Humble examples/rclpy sources, colcon Python build/pytest sources,
Docker Ubuntu installation, Ubuntu OpenSSH, Parallels CLI/Packer references and
the existing official2.6.3 cache were checked. They were used as references;
application behavior was migrated from this repository. Full source URLs are
retained in README, WORK_LOG and the GDK review. No vendor implementation or
unlicensed external code was copied.

## Final read-only runtime inspection

At 2026-09-08T22:04:34Z the VM reported no remaining project containers,
SSH enabled and Docker active. All eight installed Python module files matched
the image source byte-for-byte; the runtime manifest still matched Mac.
Evidence: `.artifacts/vm-channel/incoming/final-runtime-check.json` (all exits0).
Final authored-document synchronization uses the same checked delivery manifest
workflow; it does not change the tested runtime source hash.
