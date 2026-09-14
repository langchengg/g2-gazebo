> HISTORICAL / SUPPLEMENTARY: This report records the earlier C++ and Mac Docker work. It is not Python or Ubuntu VM acceptance. See test_report_vm_python.md.

# Actual test report

Report date: **2026-09-08 UTC**. No result below is a real G2 hardware result.
The required primary environment is the user's Ubuntu ARM64 Parallels VM.
**VM acceptance remains BLOCKED / NOT RUN.** The successfully executed container
checks below are explicitly supplemental **Mac Docker Desktop ARM64** checks.

## Execution environments and evidence

| Environment | Observed facts | Status |
|---|---|---|
| Editing host | macOS26.3.2 build25D2150, arm64, Rosetta translation0, 24GiB RAM | Inspected |
| Required VM | Parallels `Ubuntu Linux`, 4 ARM CPUs, 6GiB, NAT; console `aarch64`, Ubuntu22.04.5, dpkg `arm64` | OS/CPU verified; Docker absent |
| VM execution channel | Parallels Tools not installed; guest exec failed255; SSH to VM-reported address failed255/no route; console keyboard delivery became unreliable | BLOCKED; OpenSSH installation approval pending |
| Supplemental daemon | Docker Desktop4.90.0, Engine29.7.2, Compose5.5.1, Buildx0.36.1, Linux/aarch64 | Used for compilation and test debugging only |
| Supplemental container | Ubuntu22.04.5, `aarch64`/`arm64`, `ROS_DISTRO=humble`, GCC11.4.0, Python3.10.12 | Actually executed |
| SDK / robot | No authorized SDK package or device supplied; no discovery/control attempted | Unavailable |

Raw platform record: `.artifacts/doctor/report.json` and
`.artifacts/platform/mac-docker-container.json`. The latter explicitly labels the
Docker Desktop location. Do not confuse a Linux Docker kernel with the user's VM.
The VM's six requested Docker/OS commands could not all complete as separate calls:
the three OS/architecture checks succeeded; Docker command discovery reported
`docker` missing. No VM Docker version/info/Compose result is claimed.

The inspected official base multiarch index is
`sha256:75dd3aba34a3838dadbb31a9f7bef769bdfa8713e6cec686fc868db2981b0987`;
ARM64 manifest is `sha256:bfa845027d9606fd8615a04110f768fd79c8ad94f3a75d6e1392860bca4db51b`.
The clean-built image used for the two post-rebuild runs was reported by Docker as
`sha256:dc200d161441ab80295cbe331c9f4a4b54d18d5efdcbd55ef94e84bdb58c1716`, architecture arm64.
Per-run `environment.json` records the selected context and image at command start;
build logs contain the resulting image identity.

## Commands actually executed — supplemental Mac Docker

Paths below are relative to the repository. Each command log is accompanied by
`commands.json` with underlying command, exit code and elapsed time.

| UTC start / command | Actual result | Evidence directory |
|---|---|---|
| 20:37:39 `make build` equivalent (`python3 scripts/manage.py build`) | 0; one ROS package built with colcon | `.artifacts/build/20260908T203739Z-1c2452/` |
| 20:43:37 `make test` | make2; inner1; 29 gtest passed, 20/22 ROS tests passed | `.artifacts/test/20260908T204337Z-733b26/` |
| 20:44:39 rebuild after test parameter fix | 0 | `.artifacts/build/20260908T204439Z-687995/` |
| 20:46:03 `make test` | 0; 29 gtest + 22 ROS pytest passed | `.artifacts/test/20260908T204603Z-90b029/` |
| 20:46:13 first `make verify` | 0; fresh isolated service/topic round trip passed | `.artifacts/verify/20260908T204613Z-adfcc9/` |
| 20:46:50 `make up` | 0; default motion disabled, live service and telemetry ready | `.artifacts/up/20260908T204650Z-c36868/` |
| 20:47:04 `make hello` | 2, expected refusal `enable_motion=false`; no motion enabled | `.artifacts/hello/20260908T204704Z-4ac036/` |
| 20:47:17 `make logs` | 0; both application logs and IDLE state observed | `.artifacts/logs/20260908T204717Z-f32dfb/` |
| 20:47:18 `make down` | 0; default project container and network removed | `.artifacts/down/20260908T204718Z-4eb402/` |
| 20:47:18 `make clean-build` | 0; `--no-cache`, apt installation and colcon build actually rerun, 16.35s | `.artifacts/clean-build/20260908T204718Z-af282c/` |
| 20:48:24 post-rebuild `make verify` #1 | 0; fresh project, complete round trip | `.artifacts/verify/20260908T204824Z-3835e4/` |
| 20:48:54 post-rebuild `make verify` #2 | 0; independent fresh project and run ID | `.artifacts/verify/20260908T204854Z-cfb371/` |
| 20:50:04 `make demo-mock` | 0; independent explicitly enabled demonstration | `.artifacts/demo-mock/20260908T205004Z-e3baa7/` |
| 20:52:06 `python3 scripts/check_runner_cleanup.py --also-launch-checks` | 0; three lifecycle checks passed | `.artifacts/runner-cleanup/20260908T205206Z-d4aff9c5/` |
| 20:54:21 `make build` after stronger fresh-invalid-sample assertions | 0 | `.artifacts/build/20260908T205421Z-35c7b0/` |
| 20:54:52 final `make test` | 0; 29 gtest + 22 ROS pytest passed again | `.artifacts/test/20260908T205452Z-d2ffa3/` |

`make doctor` also exited0 on the **Mac**. This does not satisfy VM doctor.
The final colcon command sequence was actually accepted by the installed CLI:

```text
colcon build --event-handlers console_direct+ --cmake-args -DBUILD_GDK_BACKEND=OFF -DBUILD_TESTING=ON
colcon test --event-handlers console_direct+ --return-code-on-test-failure
colcon test-result --verbose
```

The successful suite reported `53 tests, 0 errors, 0 failures, 0 skipped` through
colcon: **51 actual cases (29 gtest + 22 pytest)** plus the two CTest wrapper
results. Do not count wrappers as extra behavioral cases. Pytest took44.36s;
CTest total44.64s. JUnit files are retained under the successful run's
`colcon-test-results/agibot_g2_demo/` along with per-scenario raw evidence.

The final rerun took44.44s for pytest /44.73s CTest and used image
`sha256:b9a086af8655351f90ba06ea01b5baa683c90e0bba9146c97fbd1be99a0f1c11`
(arm64). Runtime C++ was unchanged from the clean-built two-run image; the later
changes strengthened invalid-field test inputs, normalized authored document
formatting and packaged the additional lifecycle-check helper.

## Observed post-rebuild motion results

| Run | ID | Samples during action/settling | Mean Hz | Peak excursion rad | Final absolute error rad | Observed seconds |
|---|---|---:|---:|---:|---:|---:|
| #1 | `2271f54818103b32bc13e1cb1b7c8b3e-1` | 45 | 10.03874 | 0.04994122 | 0.0000003332 | 4.38302 |
| #2 | `a52184ab1812cafbbd3bc5b1cec5ba71-1` | 45 | 10.00091 | 0.04994163 | 0.0000003375 | 4.39960 |

Each `clean-e2e-*` evidence directory contains `samples.json`, `states.json`,
`health.json`, per-node logs and `metrics-<run_id>.json`. Baseline samples precede
the request. The tests observed RUNNING and the matching SUCCEEDED, rejected
concurrent/repeated requests, required increasing source stamps, preserved source
stamps through telemetry, and verified every non-target joint stayed unchanged.
The configured acceptance interval was 7–13Hz, 0.04–0.051rad excursion, return
within0.002rad and 3.5–8s completion; these are synthetic test tolerances only.

## Failure fixes and robustness coverage

- The first standalone gtest run failed one diagnostic-string assertion: the test
  injected `6*0.1` then checked literal `0.6`, introducing floating-point time
  regression. The production guard correctly reported a backward clock. The test
  now checks the exact injected final time and retains the strict stale-cache
  assertions. Rebuilt gtest:29/29 passed.
- The first ROS suite exposed `fault_mode:=nan`/`inf` being parsed as floating-point
  CLI parameters before startup. String parameters now receive explicit YAML/JSON
  quoting. The actual injected NaN/Inf observation cases subsequently passed.
- Independent review found queued advancing but expired samples could appear
  fresh. Telemetry now checks age only in its explicitly known mock local ROS
  system time domain and rejects future/expired samples. No GDK clock mapping is
  inferred. `use_sim_time=true` is refused.
- Harness partial startup now closes the first process if the second launch fails.
  Cleanup is idempotent. Runner SIGTERM enters controlled cleanup and is exercised
  with real child process sessions; both direct node SIGINT/SIGTERM are tested.
- Eight injected backend faults (freeze/repeat/error/NaN/Inf/invalid/timeout/watchdog)
  produce FAILED and reject further work. Injected-clock unit tests exercise
  scheduling gaps, stable observed completion, shutdown and command/hold errors.
- Runtime `backend=gdk` and `BUILD_GDK_BACKEND=ON` both fail explicitly without a
  substitute SDK header or mock fallback. They are negative tests, not GDK builds.

The outer lifecycle helper confirmed two application nodes,11 valid samples and
the current RUNNING ID before sending SIGTERM to `manage.py`. The manager returned
143 and its own container/network were absent afterward; emergency cleanup was
not needed. The separate unavailable-GDK launch returned1. Normal Compose stop
returned0, with container ExitCode0 and OOMKilled=false. All three isolated projects
ended with no containers/networks. The intentionally interrupted verify is a
cleanup test and is not counted as a successful full end-to-end run.

## Documentation tests

`make read-gdk`, offline cached fetch, `make audit-gdk`, bounded source reader and
Python syntax checks all exited0. The observed directory is43 pages, fetched43,
fully read43, blocked0, version mismatch0. Inventory contains282 entries, including
166 main methods; all real SDK checks remain UNVERIFIED.

An isolated-copy script test modified a body hash and correctly reduced retained
READ_COMPLETE to42. Starting without a previous reading index left all43 pages
FETCHED rather than falsely marking them read. Evidence:
`.cache/gdk/script_validation.json`. Raw vendor pages and network captures remain
ignored, while authored summaries/source references are part of the repository.

## Separate acceptance status

| Required item | Primary Ubuntu VM status | Supplemental result / reason |
|---|---|---|
| Documentation directory and per-page reading | COMPLETE |43/43 |
| GDK2.6.3 interface verification | PARTIAL | Document tables read; real SDK, exact ABI and critical semantics unavailable |
| Docker/colcon build | BLOCKED | PASS on Mac Docker ARM64 only |
| Two ROS nodes and communication | NOT RUN | PASS on Mac Docker ARM64 only |
| Mock motion/telemetry end-to-end | NOT RUN | PASS twice after clean rebuild on Mac Docker only |
| Real GDK compile/link/load | BLOCKED | No matching package; adapter intentionally unimplemented |
| GDK architecture compatibility | BLOCKED | Actual package architecture UNVERIFIED; ARM support not inferred |
| G2 read-only telemetry | NOT RUN | No device/configuration/authorization |
| G2 small arm motion | NOT RUN | No device, validated stop semantics or on-site authorization |

The original hardware task is **not complete**. The minimum immediate missing
input is an authorized working VM execution channel (approval to install/enable
OpenSSH, or an existing SSH connection). Thereafter repeat doctor, clean build,
colcon test and two fresh verify runs **inside that VM**. The later hardware phase
additionally needs the authorized2.6.3 SDK, exact robot/firmware and official
clarifications listed in `gdk_api_mapping.md`, followed by separate on-site gates.
