# GDK acquisition continuation: final Ubuntu VM software evidence

All times below are **UTC on 2026-09-08** (the final phase is after midnight on
2026-09-09 in Europe/London). This report records the new continuation, not the
historical 223-test or 47/48-sample results.

## Result and execution identity

**Final software acceptance PASS. GDK acquisition remains BLOCKED. No real SDK
was installed/imported and no real robot was initialized, connected or moved.**

Final acceptance run: `20260908T231444Z-415a96`, beginning 23:14:44 UTC. All 19
controller steps returned their asserted expected codes. The expected SDK guard
failures are not SDK PASS results. The controller completed and all app/test
containers were stopped; this is not an unattended ongoing run.

| Property | Observed evidence |
|---|---|
| VM directory | `/home/lang/projects/agibot-g2-ros2` |
| Mac authoritative delivery directory | `/Users/delaynomore/Downloads/test` |
| VM identity | hostname `lang`; Parallels VM UUID `{c50f53af-2f2f-4cd6-915b-11842281c67d}`; console user lang, authorized sudo execution |
| OS / CPU | Ubuntu 22.04.5 LTS, kernel 5.15.0-191-generic; uname aarch64 / dpkg arm64; 4 vCPUs |
| Docker | Engine 29.8.0, Compose v5.5.1, daemon name lang, Linux/aarch64 |
| Context / endpoint | default, `unix:///var/run/docker.sock`; no DOCKER_HOST/DOCKER_CONTEXT override |
| Daemon process | VM systemd Docker service MainPID 5378; `/proc/5378/comm` verified dockerd |
| Buildx | default builder, docker driver, default endpoint, BuildKit v0.33.0, linux/arm64 |
| ROS / Python | Humble, `/usr/bin/python3`, Python 3.10.12; `cpython-310-aarch64-linux-gnu`, glibc 2.35 |
| Wheel tags | 495 supported tags recorded, beginning cp310-cp310-manylinux_2_35_aarch64; no actual GDK wheel exists to compare |
| Final mock image | `sha256:e09ac606afa15c0f6420e717579e23fd92accaa427535232327892811e1c9180` (linux/arm64); this is a local image ID, not an official GDK image |
| Runtime source | 42 files, SHA-256 `73c3305dcdae3f2b862cc15462a4654b22597a2056d2be2f04590f2567f34aa1` |
| Tested delivery source | 71 files, SHA-256 `a9ac2b2fe2473b45a702278a06dece21389f87429056e79fd43b0b6f33dd777e`; final authored-report updates are synchronized separately without runtime changes |

The pinned ROS base index was checked again:
`sha256:75dd3aba34a3838dadbb31a9f7bef769bdfa8713e6cec686fc868db2981b0987`.
Its actual linux/arm64/v8 descriptor is
`sha256:bfa845027d9606fd8615a04110f768fd79c8ad94f3a75d6e1392860bca4db51b`.
No amd64 emulation, external builder, Mac Docker execution or ROS version switch
was used in this acceptance. VM NAT/security settings were unchanged.

## Evidence locations

VM raw acceptance controller logs:
`.artifacts/gdk-integration/20260908T231444Z-415a96/`.
Related VM application evidence remains under `.artifacts/test`, `verify`,
`demo-mock`, `runner-cleanup`, and `clean-build` with the run directories below.

Mac copied evidence root:
`/Users/delaynomore/Downloads/test/.artifacts/gdk-integration/20260908T231444Z-415a96/`.
Inside it the original `.artifacts/` prefix was removed while preserving the
relative application/controller evidence tree. `summary.json` is a compact,
non-hardware summary. `abi-environment.json` contains the separate no-network
container ABI probe. Full raw colcon/build logs are retained even where console
summaries are truncated.

- JUnit: `test/20260908T231509Z-d3506c/pytest.xml`.
- Test summary: `test/20260908T231509Z-d3506c/test-summary.json`.
- Full test logs: that directory's `colcon-0.log`, `colcon-1.log`, `colcon-log/`.
- E2E 1: `verify/20260908T231557Z-71eee5/clean-e2e-7678f0fb/`.
- E2E 2: `verify/20260908T231604Z-35a0ba/clean-e2e-842472bd/`.
- Lifecycle: `runner-cleanup/20260908T231611Z-08198bfe/result.json`.
- Controller command/exit records: `gdk-integration/20260908T231444Z-415a96/commands.json`.

Each E2E has `samples.json`, `states.json`, `health.json`, per-node identity,
`identity.json` and metrics linked to the specific accepted run_id. A lossless
numeric CSV projection `samples.csv` was derived **on Mac only** from each raw JSON; all 58 raw
samples are retained, including baseline/reuse checks. The metrics below use
only the 46 samples selected by the first-action assertion window. CSV source
stamps and monotonic receive times are separate columns and are not subtracted
across clock domains. Unknown effort remains absent.

## Actual tests

`colcon build --event-handlers console_direct+` ran in the Docker build with
ordinary ament_python installation. `colcon test --event-handlers
console_direct+ --return-code-on-test-failure` and `colcon test-result --verbose`
both returned **0** inside the VM Docker image. JUnit contains **330 tests**, no
failures/errors and no skipped tests:

| Group | Actual tests | Result / meaning |
|---|---:|---|
| Deterministic motion, feedback and fault logic | 161 | PASS, project mock logic |
| GDK field mapping, metadata gates and worker IPC | 37 | PASS, project fixtures only |
| Document-derived motion request validation | 74 | PASS, project request record/factory only; no vendor type/import/send |
| Acquisition/cache/archive/error tests | 32 | PASS, local project format/transport fixtures |
| Real rclpy service/topic integration | 26 | PASS, actual mock ROS nodes/communications |
| Lint suite | 0 | No lint suite claimed; git whitespace check separately passed |
| Real SDK/hardware tests | 0 | NOT RUN; not represented by skipped software tests |

The two actual installed application nodes are `/g2/sayHello` and
`/g2/telemetry`. Captured process arguments, interpreter, module `__file__` and
installed console scripts prove Python execution, not C++ wrappers. Paths are
`/opt/demo/install/agibot_g2_demo/lib/agibot_g2_demo/{sayHello,telemetry}` and
`/opt/demo/install/agibot_g2_demo/lib/python3.10/site-packages/agibot_g2_demo/`.
The application uses one backend owner and preserves observed timestamps.

Tests retain default no-motion refusal, invalid parameters/arrays/names/NaN/Inf,
positive/negative moves and nonzero initial positions, bounds, parallel request
rejection, stale/repeated feedback, errors, timeout/watchdog and cleanup. New
contract tests reject missing/expired/wrong-plan authorization, absent/faulted
or nonadvancing motor feedback and unsafe field inputs before the injected
request factory. Runtime dispatch always refuses and calls the supplied sender
zero times. No SDK UUID field is invented: the Python planning page has none.
No fake vendor module or message package is registered to pass an import test.

## Two independent final mock acceptance runs

| Run | Accepted project run_id | Action-window samples | Hz | Excursion rad | Final baseline error rad | Result |
|---|---|---:|---:|---:|---:|---|
| 1 | `1e920caf21574993a79f34a15d51ce14-1` | 46 | 9.997438 | 0.049947350 | 0.000000559 | PASS |
| 2 | `17307c2a3c55445abd264745f70f2328-1` | 46 | 10.039398 | 0.049947195 | 0.000000660 | PASS |

Each verification has a separate Compose project/container, fresh baseline,
RUNNING and terminal status matched to its own run_id. Non-target positions
remain within 1e-10 rad of baseline. The unchanged assertions require at least
25 samples, 7–13 Hz over the measured window, 0.04–0.051 rad excursion and return
error <=0.002 rad; these tolerate VM scheduling without removing meaningful
motion/data checks. Cached success from another request cannot satisfy them.
The extra demo-mock run also passed and is recorded separately.

Cleanup: SIGTERM interrupted an active mock acceptance manager and returned
143; its finally cleanup left no owned containers/networks. Normal Compose stop
returned container ExitCode 0, PID 0, Running false and no owned resources.
Selecting unavailable gdk via installed launch exited 1 with no mock fallback.
Application SIGINT/SIGTERM/fault shutdown assertions also ran in the 26 ROS tests.

## Exact command outcomes

Logs in this table are relative to the controller log directory above.
Exit 2 for `make hello` is the expected disabled-motion rejection, not a claim
that the ROS CLI's own exit status proves a successful service response. SDK
commands exit 2 because there is no actual payload. The network-none SDK command
only exercises that guard: **native import and S1/S2 did not run**.

| Command | Exit | Seconds | Controller log |
|---|---:|---:|---|
| `docker context inspect --format {{json .Endpoints.docker}}` | 0 | 0.02 | `00.log` |
| `docker info --format {{json .}}` | 0 | 0.03 | `01.log` |
| `systemctl show docker -p MainPID --value` | 0 | 0.0 | `02.log` |
| `docker buildx imagetools inspect --raw ros:humble-ros-base-jammy@sha256:75dd3aba34a3838dadbb31a9f7bef769bdfa8713e6cec686fc868db2981b0987` | 0 | 1.01 | `03.log` |
| `make doctor` | 0 | 0.22 | `04.log` |
| `make rebuild` | 0 | 12.7 | `05.log` |
| `make up` | 0 | 0.92 | `06.log` |
| `make hello` | 2 | 0.62 | `07.log` |
| `make logs` | 0 | 0.22 | `08.log` |
| `make down` | 0 | 0.77 | `09.log` |
| `make sdk-inspect` | 2 | 0.07 | `10.log` |
| `make build-gdk` | 2 | 0.03 | `11.log` |
| `make sdk-smoke` | 2 | 0.03 | `12.log` |
| `make sdk-fetch` | 2 | 8.05 | `13.log` |
| `docker run --rm --network none --read-only --tmpfs /opt/demo/.artifacts:rw,size=16m --memory 256m --pids-limit 64 --entrypoint /usr/bin/python3 agibot-g2-demo:humble /opt/demo/scripts/sdk_tools.py smoke` | 2 | 0.22 | `14.log` |
| `make verify-software` | 0 | 67.15 | `15.log` |
| `make demo-mock` | 0 | 7.38 | `16.log` |
| `docker image inspect agibot-g2-demo:humble --format {{json .}}` | 0 | 0.03 | `17.log` |
| `python3 scripts/source_manifest.py --scope delivery --check .artifacts/received-delivery.json` | 0 | 0.03 | `18.log` |

`make verify-software` executes `make test`'s same manager path, two independent
verify manager paths, then `check_runner_cleanup.py --also-launch-checks`.
Each nested command has its own preserved JSON/exit/log record. The final clean
build used `docker compose ... build --no-cache` and performed colcon installation.

## Defects, corrections and preservation

- Backed up 66 existing tracked/untracked authored files before modifications:
  `.artifacts/gdk-integration-backup/20260908T224013Z/source.tar.gz`, SHA-256
  `9becba7ae44a91dd737ff75de1ba913c8bb46ca58277ac317806b620966608b7`.
  Legacy C++ files and both historical test reports are byte-identical to this
  snapshot. No commit, push, reset, clean, dependency downgrade or test removal.
- Corrected the assumption that Python distribution version equals GDK product
  version. Matching and differing strings now both require official mapping
  evidence before any native import. No configuration waiver was introduced.
- A preliminary VM pass `20260908T225858Z-613a4c` passed 318 tests and two E2Es
  (46/47 samples). Its raw evidence is preserved separately and is **not** the
  final acceptance above.
- Review found incomplete archive/hash deadlines, unclassified decompression/
  header errors, and temporary-file ownership races. Replaced unbounded ZIP
  testzip with bounded streamed CRC, normalized errors, and used unique temp
  ownership plus non-overwriting publication. Added 12 regression cases, then
  reran the entire final clean build/test/two-E2E/cleanup sequence. Deadlines
  are cooperative filesystem/stream checks, not hard real-time guarantees.
- Console input initially lost/repeated characters, causing 404 or command-not-
  found before the controller started. Corrected input was visually verified;
  those attempts are not counted as VM test executions. Password entry occurred
  only at verified hidden Ubuntu sudo/login prompts; no credential was logged.
- CSV editing briefly introduced CRLF; `git diff --check` caught it and LF was
  restored before the final delivery snapshot. No CSV content assertion changed.

## Report synchronization completed on 2026-09-11

The earlier Mac lock interrupted only the final authored reports. On September
11, the resumed Ubuntu VM verified its previous 71-file receipt before updating
`docs/WORK_LOG.md` and this report. Mac and VM report snapshots were retained
under `.artifacts/report-sync/20260911T001251Z/before/` on their respective hosts.
No source file was removed, and no Git commit or push was made.

The final 71-file delivery receipt is
`.artifacts/vm-channel/incoming/report-sync-final-20260911T001251Z.json` on Mac.
The matching VM manifest is `.artifacts/received-delivery.json`. The complete
final delivery hash is recorded outside the hashed reports in
`.artifacts/gdk-integration/final-delivery-status.json`, avoiding a self-referential
report hash. These records supersede the earlier v6/pending synchronization state.

The VM preflight at **2026-09-11 00:27:43 UTC**, running as ordinary user UID 1000,
verified all 71 delivered files and the unchanged 42-file runtime hash above.
Both CSV projections were regenerated from the existing VM raw JSON and matched
the Mac CSV hashes exactly (58 total rows each, including baseline/reuse checks;
the historical motion metrics still use 46 action-window samples). VM CSV copies
are under `.artifacts/report-sync/20260911T001251Z/verify/`; their exact paths and
hashes are in the Mac receipt
`.artifacts/vm-channel/incoming/report-preflight-20260911T001251Z.json`.

This was a report/evidence synchronization, not a new software acceptance run.
The 330 tests, two E2Es, tested image identity and lifecycle results above remain
September 8 evidence. No SDK or hardware validation was added. An optional old
closure helper failed while writing a root-owned historical evidence directory;
that attempt is not counted as PASS. The successful synchronization used a new,
user-owned evidence directory without changing privileges or historical results.

The bounded controller's exit code and final manifest check are recorded in
`.artifacts/vm-channel/incoming/report-controller-20260911T001251Z.json`.
The private transfer listener is closed after verification; its closure record
is `.artifacts/report-sync/20260911T001251Z/channel-closure.json` on Mac.
NAT and firewall configuration are unchanged. No unattended task is left running.

## SDK layers and remaining input

| Layer | Status | Evidence / dependency |
|---|---|---|
| S0 official SDK acquisition/static inspection | BLOCKED | Actual documented installer GETs timed out; no package/image or vendor checksum obtained |
| Target VM ARM/Python environment | PASS | Native ARM64 ROS container environment inspected; not an SDK compatibility conclusion |
| Actual SDK ARM64/ABI compatibility | BLOCKED / UNVERIFIED | No real native objects, wheel tags or vendor platform manifest to compare |
| S1 real SDK installation/import | NOT RUN | No verified payload/license/install layout; build/load commands explicitly fail closed |
| S2 real SDK symbol/type contract | NOT RUN | 74 motion tests and 37 mapping tests are project fixtures, not real binding tests |
| S3 permitted no-device initialization | NOT RUN | No verified package or supported no-device initialization semantics |
| State / motion implementation | PARTIAL | Existing document-derived read-only worker plus request construction; dispatch blocked by unresolved SDK/safety semantics |
| S4 G2 read-only telemetry | NOT RUN | No device/configuration/connection authorization |
| S5 G2 arm motion | NOT RUN | No device or separate on-site motion authorization; stop/concurrency/lifetime semantics unresolved |

See [actual acquisition attempts](gdk_acquisition.md), [public-source research](gdk_acquisition_research.md),
[SDK manifest](gdk_sdk_manifest.json), [API mapping](gdk_api_mapping.md) and
[hardware checklist](hardware_checklist.md). The next external input is a normal
authorized official 2.6.3 release link/portal or package with provenance/version/
license evidence. A robot and on-site configuration/authorization are subsequent,
separate S4/S5 prerequisites. No architecture replacement is recommended before
inspecting the actual package. No hardware test was prefilled PASS.

## Capabilities and references

Reused the existing Python/rclpy implementation, Docker/colcon manager, ROS
integration probes, source manifest and Parallels console/private transfer.
Used Git/rg, Python standard-library inspection/tests, Docker/Compose/Buildx
inside the VM, CUA for verified UI input, current official web references and
three bounded agents for acquisition research, motion contract and review.
No new plugin, proprietary dependency, third-party SDK implementation or vendor
stub was installed/copied. External documentation was used as evidence only:
versioned GDK pages; official AGIBOT/AgibotTech public pages; Python 3.10
urllib/importlib.metadata and Python Packaging wheel-tag specifications.
