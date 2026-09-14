# Work log

## 2026-09-08 — inspection and implementation

- Preserved the four existing GDK reading notes; initialized a local Git repository in the user's current directory. No remote, commit or push was created.
- Inspected Mac: macOS26.3.2, native ARM64, 24GiB RAM. This is the editing host, not the updated primary Linux target.
- Discovered running Parallels VM `Ubuntu Linux`: 4 ARM CPUs, 6GiB RAM, NAT. Console observations confirmed Ubuntu22.04.5, `aarch64`, `arm64`.
- Docker CLI absent in VM. Parallels Tools absent; guest exec unavailable. Existing VM SSH attempt returned no route to host. Console automation initially read OS facts but later failed to deliver input reliably. Requested approval to install/enable OpenSSH; no approval assumed from elapsed time.
- Verified official Humble Jammy multiarch image and ARM64 manifest. Existing Mac Docker ARM64 dependency image built successfully; this is supplemental, not VM acceptance.
- Implemented the pure C++ mock model/state machine, two ROS wrappers, launch/config, optional GDK failure boundary, Docker entrypoint and isolated execution scripts.
- Implemented injected-clock gtests and real ROS pytest probes for service/topic movement, concurrent requests, retained-status IDs, invalid/stale/repeated samples and failure/signal handling.
- GDK evidence work discovered 43 pages from actual versioned resources. Raw copies remain ignored; reading progress and API evidence are maintained separately.

## Capability and reuse decisions

- Used terminal/Git/Python/C++ tools for bounded local inspection and implementation; Docker/Compose/Buildx for native ARM64 container checks. These can modify project/build artifacts; no global cleanup is used.
- Used installed Parallels CLI read-only inventory and CUA for the VM console. Guest execution is unavailable without tools; VM settings were not changed.
- Used browser/network evidence and official web sources for GDK, ROS and Docker. No credentials, cookies or unrelated browser contents are saved to the project.
- Existing user-provided reading notes and exporter pack were inspected as references. No unlicensed external implementation or proprietary SDK was copied into source.
- Parallel agents handled independent core, ROS wrappers and documentation evidence. Independent review follows implementation. Unrelated connectors, heavy simulation systems and VM installers were unnecessary.

## Next steps

1. Establish the authorized Ubuntu execution channel and install Docker from its official Ubuntu repository.
2. Run doctor and verify ARM64 manifests in the VM; build and fix any real colcon errors.
3. Run the complete colcon suite, clean image rebuild and two independent fresh mock acceptance runs in VM Docker.
4. Record exact command exits, image identity, sample statistics and remaining hardware evidence gaps.

This log records current progress only. It does not promise continued background
work after the session stops.

## 2026-09-08 20:56 UTC — supplemental verification complete

- Branch is `test/g2-demo`; files are reviewable with Git intent-to-add. No commit or push was made. Existing root reading notes remain intact.
- Mac Docker supplemental ARM64 build passed, including an actual no-cache rebuild. The required Ubuntu VM Docker build remains BLOCKED.
- Final colcon suite:29 gtest +22 ROS pytest passed, exit0 (colcon includes two wrappers in its displayed53 total). Raw JUnit/sample evidence: `.artifacts/test/20260908T205452Z-d2ffa3/`.
- Two fresh projects after the clean rebuild passed service/topic round trips at10.0387Hz and10.0009Hz,45 action samples each. Logs: `.artifacts/verify/20260908T204824Z-3835e4/` and `20260908T204854Z-cfb371/`.
- Fixed an injected test clock rounding mistake and CLI string quoting for nan/inf; strengthened validation against fresh malformed samples; added mock-only source-age checks and robust partial-start/SIGTERM cleanup.
- Outer manager interruption, unavailable-GDK launch and normal container stop passed with no owned resource leftovers. `.artifacts/runner-cleanup/20260908T205206Z-d4aff9c5/`.
- Documentation43/43 complete, inventory282 entries, audit exit0. Document/SDK semantic verification remains PARTIAL and real backend UNIMPLEMENTED.
- Docker had no running containers at final inspection. VM settings and robot endpoints were untouched; OpenSSH approval remains pending. Password was not written to project files or logs.
- Next required action remains establishing authorized VM access, followed by VM-native Docker doctor/build/test/two verify runs. Hardware phases separately need the actual2.6.3 package and device authorization.
- Official Ubuntu [OpenSSH documentation](https://ubuntu.com/server/docs/how-to/security/openssh-server/) confirms the `openssh-server` package. Installing/enabling it has not been performed or assumed authorized.

## 2026-09-08 — Python migration and Ubuntu VM continuation

- The user explicitly authorized Ubuntu-only SSH and required Docker packages; the earlier pending-authorization entry is historical.
- Preserved all 40 initial uncommitted/untracked source files in `.artifacts/migration-backup/20260908T211811Z/`, verified every member hash, and moved the original package to `legacy/cpp` with `COLCON_IGNORE`. Branch remains `test/g2-demo`; no commit/push.
- Implemented genuine ament_python/rclpy nodes, installed console entry points, unchanged ROS interfaces and mock defaults. Added read-only document-derived GDK worker using actual documented Python call expressions, not invented messages or a replacement SDK.
- Fixed inherited sub-watchdog scheduling jumps; added phase-step bounds and observed velocity/acceleration checks. Local combined pytest: 197 cases plus 60 subtests pass, exit 0, Mac Python 3.11; this is not VM acceptance.
- CUA sees the VM but ordinary key/clipboard input was unreliable. Installed Parallels 27 CLI help and official Parallels Packer implementation confirmed supported key-event delivery; a decimal Enter scan code and JSON stdin events work without Guest Tools. No credential is passed in CLI arguments or saved.
- Actual VM checks retrieved via a private, VM-only transfer endpoint: Ubuntu22.04.5 ARM64, Python3.10.12, /home/lang, Parallels, 5.8GiB RAM. SSH is active and listens IPv4/IPv6 22; firewall was already inactive (not changed). Mac outbound SSH gives No route to host, while VM→Mac ping/HTTP succeeds. NAT unchanged; no Mac Remote Login or public port forwarding.
- Docker Engine installation in VM completed 21:52:08Z, exit0. Local systemd daemon and Buildx worker identify lang/arm64. No Docker group changes or socket permission weakening.
- Mac is source master; source manifest/bundle includes new untracked Python tests and authored documentation while excluding credentials, full vendor cache, SDK and build artifacts. Runtime image identity is checked before tests/up, and build identity is refreshed after build.
- Fixed colcon JUnit handling to retain its default result file, reject empty tests and preserve timeout reports. VM no-cache build and formal acceptance are in progress; final results belong in test_report_vm_python.md.

Official implementation references checked: ROS Humble rclpy/examples and
rclpy node/clock/executor sources; colcon Python build/pytest task sources;
Docker Ubuntu installation documentation; Ubuntu OpenSSH documentation;
Parallels supported CLI/Packer key-event source. External code was used as
reference only; the application was migrated from this repository. Keycode
facts informed a task-local console helper kept outside the deliverable.

## 2026-09-08 22:04 UTC — final Python/VM acceptance complete

- Final VM Docker no-cache rebuild, normal installed ament_python package, two Python nodes and all Make entries passed. `make hello` correctly returns2 for disabled motion; no hidden enablement.
- Final colcon test/test-result both exit0:223 pytest cases (197 unit=161 motion+36 GDK mapping/IPC;26 actual ROS integration), zero failures/skips. Initial and final full VM passes are both retained.
- Final independent verify runs: `20260908T220141Z-2f19c1` (47 action samples,10.010426Hz) and `20260908T220148Z-beaa6a` (48 samples,10.014926Hz), current distinct IDs and matching terminal states. Demo-mock also passed.
- Final lifecycle suite PASS: RUNNING interrupted by SIGTERM→manager143, no remaining owned containers/networks; normal Compose stop0; explicit unavailable GDK launch1, no mock fallback.
- Mac evidence returned into `.artifacts/vm-python/20260908T220038Z-a043be/`, with raw samples, derived CSV, JUnit and archive/file hashes. A final read-only VM check found no project containers and verified eight installed Python modules byte-for-byte against image source.
- Runtime source hash `993e656266756908544da51e881a7d1582dab15f343dcdb30c961bdad224a7ab`, final Docker image `sha256:ded15ba091c79b1157068b0285a6f6a89356afae271874a78abdb57f1a1c36c0`. Mac/VM/image runtime hashes agree.
- SSH remains enabled/active for authorized continuing VM development; Mac outbound SSH itself is still blocked by No route to host. No successful SSH login is claimed. The confirmed usable channel was Parallels console plus restricted private source/evidence transfer.
- Hardware remains separate: direct Python read-only DOC_IMPLEMENTED / SDK_UNVERIFIED; real SDK loading/architecture, G2 telemetry and arm motion NOT RUN. Motion stop/control semantics remain unresolved.

## 2026-09-08 GDK acquisition continuation

- Protected all existing tracked/untracked authored sources before edits:
  `.artifacts/gdk-integration-backup/20260908T224013Z/` (66-file snapshot).
  Branch still `test/g2-demo`; no commit/push/reset/clean.
- Reread cached deployment, hybrid deployment and Python installation pages.
  Attempted both actual robot-hosted installer URLs from Mac and VM; four
  curl transfers exited 28 with zero bytes. Official public-channel research
  found no confirmed alternate 2.6.3 release. Requested a normal vendor entry
  once; software work continues without it.
- Added bounded installer acquisition/static artifact checks, motion request
  field validation with unconditional runtime block, and tests. Corrected the
  distribution-version/product-version equality assumption. No vendor stub,
  package install/import/init, network reconfiguration or hardware motion.
- Reused Parallels private console and source transfer. JSON stdin keyboard
  submission silently did nothing; verified individual key events work.
  Sudo credential entered only through the actual hidden VM prompt, never
  command arguments, scripts, logs, files or environment variables.
- VM container environment measured: native aarch64, Python 3.10.12,
  `cpython-310-aarch64-linux-gnu`, glibc 2.35. Docker default Unix socket and
  Buildx default endpoint are VM-local. Current regression results follow in
  `docs/test_report_gdk_integration.md`; older report retained unchanged.
- Preliminary VM pass `20260908T225858Z-613a4c`: clean rebuild exit 0;
  318 actual tests (292 unit, 26 ROS integration), two independent E2E runs and
  lifecycle cleanup passed. This is explicitly pre-fix evidence, not final.
- Review found hash/ZIP inspection deadline gaps, uncaught malformed archive/
  Content-Length errors, and shared temporary-file cleanup ownership. Fixed all
  three with bounded streamed inspection, sanitized failures and per-call temp
  ownership/no-clobber publication; 12 regression cases added. Acquisition's
  32 focused local tests pass. Final VM rebuild/regression follows these fixes.
- Final VM pass `20260908T231444Z-415a96`: clean no-cache build/install exit 0;
  330 tests (304 unit + 26 ROS integration), zero failures/skips. Two independent
  final E2Es each measured 46 action-window samples, 9.997438/10.039398 Hz,
  excursions 0.049947350/0.049947195 rad, and baseline errors below 0.000001 rad.
  Mock demo, disabled-motion refusal, normal stop and active-run SIGTERM cleanup
  passed. Actual SDK S0 remains BLOCKED; S1–S5 NOT RUN, not substituted by fixtures.
- Final runtime: 42 files, SHA-256
  `73c3305dcdae3f2b862cc15462a4654b22597a2056d2be2f04590f2567f34aa1`;
  image `sha256:e09ac606afa15c0f6420e717579e23fd92accaa427535232327892811e1c9180`.
  Captured evidence is under `.artifacts/gdk-integration/20260908T231444Z-415a96/`.
  The final runtime acceptance is separate from the later report-only
  synchronization, recorded in the September 11 continuation below.
- Remaining external inputs: authorized official 2.6.3 release/provenance/license
  and actual binding/architecture evidence; later G2 firmware/configuration,
  verified stop/concurrency/lifetime semantics and separate on-site motion
  authorization. No autonomous work is promised after this session ends.

- Historical September 8 closure exception: the Mac locked during the final
  report-sync step. Runtime files and tests were already synchronized, but two
  reports and derived CSV projections remained Mac-only. The private transfer
  listener was closed at 23:28:58 UTC; no v7 receipt was produced. This exception
  is resolved by the following continuation.

## 2026-09-11: report-only synchronization

- Preserved both report files and Git status before editing under
  `.artifacts/report-sync/20260911T001251Z/` on Mac; the VM updater separately
  preserved its earlier report bytes. Continued `test/g2-demo`; no commit/push.
- Resumed the identified suspended Ubuntu VM. Its console initially responded
  slowly; a graceful ACPI stop succeeded. No force reset, network change,
  guest-tools installation or security setting change was used.
- Reused Parallels CLI/capture and the VM-only private transfer. Corrected
  dropped/repeated visible command input before execution. GUI sudo input did
  not authenticate; credentials were never put in shell arguments or files.
  Report updates succeeded as the existing ordinary user (UID 1000).
- Initial VM receipt verified all previous source hashes and changed only
  `docs/WORK_LOG.md` and `docs/test_report_gdk_integration.md`. Preflight at
  00:27:43 UTC verified 71 delivery files and the unchanged 42 runtime files.
- Regenerated both CSV projections from VM raw JSON in a new user-owned evidence
  directory; each has 58 total rows and is byte-identical to its Mac projection.
  The earlier optional closure helper could not write its root-owned historical
  evidence path; no result from that attempt was accepted as PASS.
- Final report sync/exit evidence on Mac:
  `.artifacts/vm-channel/incoming/report-sync-final-20260911T001251Z.json` and
  `.artifacts/vm-channel/incoming/report-controller-20260911T001251Z.json`.
  Full delivery hash/status is recorded externally in
  `.artifacts/gdk-integration/final-delivery-status.json`.
  Private listener closure is recorded in
  `.artifacts/report-sync/20260911T001251Z/channel-closure.json`.
- No rebuild or repeat test run was needed for these two report edits. The
  September 8 total of 330 tests and both mock E2Es remain historical evidence,
  not newly executed September 11 results. SDK acquisition remains BLOCKED;
  actual SDK loading and G2 hardware tests remain NOT RUN.

## 2026-09-13 — G2 Gazebo simulation scope (in progress)

The user replaced hardware/SDK acquisition with a simulation-only acceptance target.
Mac remains the source master; Ubuntu 22.04.5 ARM64 VM is the Docker execution target.
Pre-change source archive and manifests are in `.artifacts/gazebo/20260913T131938Z`.
The branch has no HEAD commit; uncommitted and untracked project sources were included.
A bounded private Parallels-console execution channel was restored with normal sudo;
Docker daemon and Buildx use the VM's local Unix socket. No network/security policy changed.

Official model licensing was checked independently. GitHub's restricted G2 model is
not used. The pinned Hugging Face GenieSimAssets subset uses CC BY-NC-SA 4.0; the
user explicitly confirmed noncommercial learning/research/demonstration. USD assets
are converted on Mac with official usd-core 26.8; PyPI supplies no Linux ARM64 wheel
for that converter. This does not change native ARM64 simulation execution.

ARM64 package probes found Fortress and ros_gz_bridge binaries. ros_gz_sim and
 gz_ros2_control binaries are absent in the inspected Humble repository. Only these
integration packages and the official control demo are built from fixed official
commits. First dependency build failed because the plugin development package is
named `libignition-plugin-dev`, not `libignition-plugin1-dev`; actual apt metadata
identified the correction. The corrected VM dependency build is in progress.

Python ActionClient/feedback adapters and model resources were added. Local pure
logic regression: 347 passed (304 existing + 43 new), not Gazebo acceptance.
Real model loading, physics/control, GUI/video, VM regression and two independent
simulation runs remain pending. Hardware and proprietary SDK are OUT OF SCOPE.

### VM execution follow-up

- `sim-doctor`: actual Fortress 6.18.0, plugin and installed Python entry points found.
- Official cart smoke passed after waiting for controller active (not merely Action discovery).
- VM colcon regression passed 374 tests: 348 unit / 26 ROS, no skips, both commands exit 0.
- Actual Xvfb/Mesa context: llvmpipe, OpenGL 4.5; this alone is not G2 GUI acceptance.
- Initial G2 physics crashed (139) when the source-derived OBJ lacked normals. All 106
  meshes were regenerated with authored/transformed normals; 5 exactly zero-area source
  triangles are recorded as omitted, no collision object removed. The actual VM importer
  now accepts all meshes. Old generated resources were retained separately.
- A no-cache rebuild raced the controlled source sync and read the earlier iteration.
  This is recorded as an earlier-image build, not final-source acceptance. Source sync and
  subsequent builds are now strictly sequential, and the manager checks current hashes
  again after building. The current source image rebuilt successfully.
- G2 physics subsequently reached the requested arm excursion and stable return, but
  the probe failed to serialize NumPy UUID bytes. Explicit integer UUID serialization was
  added; a fresh complete evidence run is required before recording PASS.

- 2026-09-13: First complete real G2 verify passed (`20260913T140451Z-7db586`):
  63 motion samples, 10 Hz simulation time, 0.049966 rad peak, 0.000003880 rad return error.
  Source values/stamps matched the real broadcaster. GUI rendered the complete model,
  but first recording failed before motion on a GetParameters response timeout.
  Parameter probes now retry only idempotent reads with bounded budgets and retain attempts.
- Full test attempt `20260913T141201Z-517962`: 374 software tests and all 24 real Gazebo
  probe cases passed, but overall command failed its descendant-cleanup assertion.
  Fortress Ruby launcher exited while its server child remained after SIGTERM-triggered
  launch shutdown. The container subreaper now explicitly signals/waits on tracked owned
  descendants, records cleanup stages and still fails if bounded shutdown needs SIGKILL.
- Actual GUI screenshot showed valid G2 geometry, ground and shadows. Updated camera and
  compact plugin layout follow Fortress's official gui.config/MinimalScene source;
  motion amplitude remains 0.05 rad. GUI and cleanup fixes require new actual VM runs.

- No-cache VM build `20260913T141720Z-e9bd7a` passed (image arm64, runtime source
  c8df4795d05516e65214ad460ff110043a39f109d7c7a25643cd6e9a43751618).
  Subsequent camera/probe changes are rebuilt separately; this is not mislabeled as their hash.
- Ordinary VM entrypoints passed: sim-up 0, sim-hello expected refusal 2 with the explicit
  disabled reason, sim-logs 0, sim-down 0. Read-only Scene contains g2 entity id10 and all
  53 visual meshes. Scene does not report is_static even for the static floor; absent
  protobuf fields are not treated as evidence of dynamic behavior.
- Added actual Scene/state test passed in `20260913T142749Z-3121ea`; software374 also passed.
  Overall failed source correlation because blocking scene CLI reads accumulated probe
  callbacks. Fix separates scene inspection from a fresh timestamp-barrier measurement
  window; exact sample correlation and motion tolerances remain unchanged.

### Final simulation acceptance — 2026-09-13

- Final application image: sha256:509fde2117cc65502ee062dac9e237e6ff57be6ad1a9869b2f4afc86892f269b.
  Runtime source hash a4a835eaea7fae18517873edffe7a0db4929ad66d5575c91f8bd170dfe04fc5f,
  65 files; native Ubuntu VM Docker / ARM64. Fresh final application colcon layer passed.
- Final suite `20260913T145837Z-de67b9`: 348 unit +26 ROS integration +29 actual Gazebo
  cases passed, zero failures/skips, make/colcon exit0. Full no-cache dependency/application
  build was performed earlier in this session and separately identified above.
- Verified actual outgoing full-vector trajectory points and observed speed/acceleration
  against analytical quintic bounds; command_waypoints.csv now accompanies measurements.
- Iteration `20260913T145028Z-500c67` exposed early graph discovery checking and repeated
  stop signals interrupting Python destruction. Bounded exact-count discovery and
  idempotent shutdown repaired them. Final suite has no StopRequested traceback or residue.
- Independent final runs `20260913T150151Z-4eba42` and `20260913T150235Z-4975d1`: 6/6 each,
  62 motion samples each,10 Hz simulation frequency,0.049966032rad peak and0.000011127rad
  maximum return error. Controller status4/error0 and exact source-sample correlation.
- Actual GUI recording `20260913T150323Z-a7c40d`:6/6; Ogre1/Mesa llvmpipe,1280x720 H.264,
  254 frames/25.4s, RTF0.803579. Full-model and arm-detail frames visually inspected.
  Derived Mac crop is explicitly1x original wall time; original recording preserved.
- Strong15s timeout `timeout-2d2857cd`: running simulator/controller reached; expected124,
  wrapper0, no owned process residue. Normal stop and motion-time SIGTERM passed too.
- VM evidence export v2:1,906 files verified individually on Mac; archiveSHA256
  2fe19b31a72e63d1b1eccbdf1a9b5ca7bbd506634af950b277d21c1836db8abc.
  Copied into .artifacts/gazebo/vm-final-v2 without overwriting historical evidence.
- Source master remains Mac; final documentation is synchronized with hash verification.
  See .artifacts/gazebo/final-source-consistency.json and channel-closure.json for receipts.
  No commit/push. Proprietary SDK and real robot are OUT OF SCOPE.
