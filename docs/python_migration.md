# Python migration and behavior evidence

This document records the source migration and the tests actually executed for
the Python core and final Ubuntu VM acceptance on 2026-09-08. The active package is
`src/agibot_g2_demo`, declares `ament_python`, and installs these Python entry
points in `setup.py`:

- `sayHello = agibot_g2_demo.say_hello_node:main`
- `telemetry = agibot_g2_demo.telemetry_node:main`

The default mock path runs Python logic in `motion.py` and
`backends/mock_backend.py`. It does not wrap, launch, or load the historical C++
implementation. The core has no ROS import, SDK import, sleeps, worker threads,
or hardware I/O. The ROS wrappers import `rclpy` and call the Python core.

## Results and scope

| Check | Actual result | Evidence and boundary |
| --- | --- | --- |
| Initial migrated core, Mac Python 3.11 | 154 passed; exit 0 | Local pure-Python pytest, before the scheduling fix below; not ROS or VM acceptance. |
| Current core after scheduling fix, Mac Python 3.11 | **161 passed; exit 0** | `.artifacts/python-local/core-py311-junit.xml`: 161 tests, 0 failures, 0 errors, 0 skipped; 0.137 s; timestamp `2026-09-08T22:39:52.810963+01:00`, host `Pro.local`. |
| Python 3.10 syntax compatibility | PASS, 5 files | `ast.parse(..., feature_version=(3, 10))` on the current core, backend files and core test file; this is a syntax check, not a Python 3.10 runtime test. |
| Old/new configuration defaults | PASS, 18/18 fields | Parsed the legacy `Config` declarations and compared their values with `dataclasses.asdict(Config())`. |
| Backup integrity | PASS, 40/40 files | SHA-256 of every tar archive member matched `source_manifest.json`; no files were restored over the workspace. |
| Python ROS integration suite | **PASS: 26 cases, exit 0** | Actual VM Docker/rclpy service/topic tests; see `test_report_vm_python.md` and final JUnit. |
| Ubuntu 22.04 ARM64 VM Python/ROS/colcon build and test | **PASS** | Final ordinary installation and colcon tests: 197 unit +26 ROS integration, 0 failed/skipped, exit 0. |
| Two clean Python ROS end-to-end runs in the VM | **PASS** | Final independent runs at 22:01:41Z and 22:01:48Z; fresh run IDs, 47/48 action samples, raw evidence in the VM report. |
| Real SDK loading, G2 read-only telemetry, G2 motion | **NOT RUN in this core review** | These are separate acceptance tracks. Mock or fake-input tests cannot establish them. |

Earlier C++ build/run artifacts remain historical evidence and do not validate
the new Python executables. Likewise, Mac tests do not validate the Ubuntu VM,
ROS discovery, DDS, service behavior, launch, Docker or colcon packaging.

## Reversible source preservation

The pre-migration source backup is local and gitignored:

```text
.artifacts/migration-backup/20260908T211811Z/
  pre-python-source.tar.gz
  source_manifest.json
  git-diff.patch
  git-status.txt
```

The tar archive contains 40 original source files. Its 40 content hashes were
checked against the manifest during this review. The original C++ package also
remains readable at `legacy/cpp/agibot_g2_demo/`. The marker
`legacy/cpp/COLCON_IGNORE` excludes that historical subtree from recursive
colcon discovery; it does not delete the package. This use of the marker follows
the [official colcon discovery documentation](https://colcon.readthedocs.io/en/released/reference/discovery-arguments.html).

To inspect a restored copy, extract into a newly created directory instead of
overwriting the active Python package. These recovery commands are documented,
not executed as part of migration:

```bash
restore_dir=$(mktemp -d /tmp/agibot-pre-python.XXXXXX)
tar -xzf .artifacts/migration-backup/20260908T211811Z/pre-python-source.tar.gz \
  -C "$restore_dir"
```

## Stable project API

All symbols below are project interfaces, not vendor API names.

| Component | Current API and behavior |
| --- | --- |
| `motion.Config` | Dataclass with the same 18 names/defaults as legacy C++; default `backend="mock"`, `enable_motion=False`. |
| `backends.base.Observation` | Dataclass: `names`, `positions`, `velocities`, `efforts`, `sequence`, `sample_time`. List defaults are independent. Unknown velocity/effort remain empty. |
| `backends.base.RobotBackend` | Protocol with `poll(now)`, `command_positions(positions, now)`, `hold(now)`, `set_fault(fault)`. The mock implements these directly in Python. |
| `motion.Engine(config, backend=None)` | Owns one mock backend; `tick(now)`, `request(now)`, `shutdown(now)`, `set_fault(fault)`, `healthy(now)`, `health_reason(now)`; snapshot properties `config`, `observation`, `status`. Wrapper calls must remain serialized. |
| `MotionState`, `Status`, `RequestResult` | String enum with IDLE/RUNNING/SUCCEEDED/FAILED; immutable status/result dataclasses. Accepted requests carry a process-unique prefix and incrementing run number. Acceptance is not completion. |
| `SourceFreshness(timeout)` | `observe(sequence, source_time, receive_time)`, `healthy(now)`, `reason(now)`. Both supplied source markers must advance. Source time is never subtracted from local receive time. |
| Validation helpers | `mock_joint_names()`, `valid_fault(fault)`, `validate_config(config)` raises `ValueError`; `validate_observation(observation)` returns an error string or an empty string. |
| Hardware separation | `Engine(Config(backend="gdk"))` raises, even with an injected backend. Hardware wrappers must use the separate explicitly selected GDK path; the core cannot fall back to mock. |

The core retains six clearly synthetic joint names and nonzero initial
positions. Commands follow a quintic round trip. A separate first-order follower
produces observations. Completion requires an observed outward excursion of at
least 80% of the configured displacement, completion of the trajectory phase,
and return of all positions within tolerance for the configured stable duration.
Available velocities must also settle. The standard and signed-boundary tests
require an actual peak displacement above 90% of the configured magnitude.
These are mock behavior criteria, not G2 arrival or safety semantics.

## Old behavior to current implementation and test mapping

The legacy test file contains 21 ordinary `TEST` definitions plus one
parameterized definition instantiated with eight faults: **29 old cases**.
Every behavior is mapped below. `M1` refers to the current 161-case Mac JUnit
report above; it means local core PASS only. All new tests in this table are in
`src/agibot_g2_demo/test/test_motion.py`.

| Old behavior / legacy gtest | New implementation | New pytest name(s) | Evidence |
| --- | --- | --- | --- |
| `Configuration.SafeDefaultsAndUnknownBackend` | `Config`, `validate_config` | `test_safe_defaults_and_unknown_backend` | M1 |
| `Configuration.RejectsEveryNonFiniteAndNonPositiveBound` | `validate_config`, `_positive` | `test_rejects_every_nonfinite_nonpositive_and_nonnumeric_bound` | M1; original numeric loop is parameterized and extended with Python type errors. |
| `Configuration.RejectsInvalidMotionAndProfileLimits` | `validate_config`, analytic quintic limits | `test_rejects_invalid_displacement`, `test_rejects_invalid_motion_and_profile_limits` | M1 |
| `Configuration.GdkSelectionFailsWithoutAnyFallback` | `Engine.__init__`, `MockBackend.__init__` | `test_gdk_selection_fails_without_any_fallback` | M1; factory path is now explicit Python construction, including rejection of injected fallback. |
| `Observations.DimensionsNamesFiniteValuesAndUnknownFields` | `validate_observation`, `Observation` | `test_observation_dimensions_names_finite_values_and_types`, `test_unknown_fields_stay_empty_and_observation_defaults_do_not_alias` | M1 |
| `Freshness.SeparatesSourceClockFromMonotonicReceiveClock` | `SourceFreshness` | `test_freshness_separates_source_clock_from_monotonic_receive_clock` | M1 |
| `Freshness.RepeatedOldSamplesDoNotRenewSourceFreshness` | `SourceFreshness.observe` | `test_repeated_old_samples_do_not_renew_source_freshness` | M1; preserves the repaired exact injected-time assertion. |
| `Freshness.BothAvailableMarkersMustAdvance` | `SourceFreshness.observe` | `test_both_available_source_markers_must_advance` | M1 |
| `Freshness.RejectsClockAndMarkerFailures` | `SourceFreshness` | `test_freshness_rejects_clock_and_marker_failures` | M1 |
| `MockBackend.CommandAndObservedStateAreSeparateAndEffortIsUnknown` | Held command plus independently integrated follower | `test_command_and_observation_are_separate_and_effort_is_unknown` | M1 |
| `Engine.StartupNeverMovesAndDisabledRequestIsRejected` | `Engine.tick`, `Engine.request` | `test_startup_never_moves_and_disabled_request_is_rejected` | M1 |
| `Engine.RequiresFreshFeedbackBeforeAcceptingAnyRequest` | `Engine.healthy`, `Engine.request` | `test_fresh_feedback_is_required_before_any_request` | M1 |
| `Engine.RoundTripUsesObservedExcursionAndStableReturnWithNewRunIds` | Phase progression, observed excursion, settling, request ID | `test_round_trip_uses_observed_excursion_and_stable_return_with_new_run_ids` | M1 |
| `Engine.DifferentEnginesDoNotReuseCachedRunIds` | UUID prefix plus request counter | `test_different_engines_do_not_reuse_cached_run_ids` | M1 |
| `Engine.NegativeDisplacementAndAlternateJointAreSupported` | Signed displacement and named target index | `test_negative_displacement_and_alternate_joint_are_supported` | M1 |
| `Engine.RejectsTargetOutsideSyntheticLimits` | Current observed position plus requested displacement | `test_target_outside_synthetic_limits_is_rejected` | M1 |
| `FeedbackFault.NeverReportsSuccessAndDoesNotResumeAfterRecovery[freeze]` | No samples; receive timeout and fault latch | `test_feedback_fault_never_succeeds_and_does_not_resume_after_recovery[freeze]` | M1 |
| Same legacy fault behavior: `repeat` | Preserved old sample markers; stale failure | Same new test, `[repeat]` | M1 |
| Same legacy fault behavior: `error` | Backend exception; FAILED and hold | Same new test, `[error]` | M1 |
| Same legacy fault behavior: `nan` | Invalid observation rejected | Same new test, `[nan]` | M1 |
| Same legacy fault behavior: `inf` | Invalid observation rejected | Same new test, `[inf]` | M1 |
| Same legacy fault behavior: `invalid` | Invalid dimensions rejected | Same new test, `[invalid]` | M1 |
| Same legacy fault behavior: `timeout` | Fresh stationary feedback cannot imply success; observed limit failure or completion timeout | Same new test, `[timeout]` | M1 |
| Same legacy fault behavior: `watchdog` | Injected backend watchdog error | Same new test, `[watchdog]` | M1 |
| `Engine.WatchdogStopsWithoutReplayingCommandsOrReturningToBaseline` | Scheduling-gap check before polling or command | `test_watchdog_stops_without_replaying_commands_or_returning_to_baseline` | M1 |
| `Engine.MonotonicClockFailuresAreTerminal` | Clock finite/order checks | `test_monotonic_clock_failures_are_terminal` | M1 |
| `Engine.RejectsChangedJointNamesAndOutOfBoundsFeedback` | Exact mock name/order and position limits | `test_changed_names_and_out_of_bounds_feedback_are_rejected` | M1 |
| `Engine.BackendCommandAndHoldFailuresAreReported` | `_fail`, exception reasons and hold failure reporting | `test_backend_command_and_hold_failures_are_reported` | M1 |
| `Engine.ShutdownIsBoundedIdempotentAndDoesNotCommandReturn` | `Engine.shutdown`; explicit wrapper lifecycle | `test_shutdown_is_bounded_idempotent_and_does_not_command_return` | M1 |

Python-specific additions cover boolean/string rejection, non-aliased mutable
lists, immutable status and copied configuration/observation snapshots, positive
and negative displacement boundaries, unchanged feedback without outward motion,
non-target drift, available velocity stabilization, and repeated final samples.
No critical old assertion was deleted to obtain a passing count.

## Review finding and correction: delayed callback command jump

The first 154 tests passed but did not cover a scheduling gap smaller than the
watchdog limit. A separate injected-clock review reproduced an inherited C++
problem: tick every 0.02 s through 0.8 s, then at 1.29 and 1.31 s. The 0.49 s gap
was below the 0.5 s watchdog, so the old wall-time profile jumped to a later
command. The next observed sample had velocity `0.2431711204 rad/s` and finite
difference acceleration `11.7957905653 rad/s^2`, above the existing limits of
`0.2` and `0.5`, while still RUNNING.

The correction preserves the normal quintic shape and original limits:

1. Trajectory phase advances by at most one 50 Hz source period per callback.
   Delayed callbacks extend the motion rather than jumping to a future target;
   no backlog of commands is replayed.
2. The scheduler watchdog and total motion timeout still use actual injected
   monotonic elapsed time. Repeated delay cannot extend a run indefinitely.
3. Available simulated velocity and adjacent-sample velocity differences are
   checked against the configured bounds. A violation fails the run, requests
   hold, retains the last valid observation, and cannot publish the bad sample
   as healthy telemetry.
4. A tick cannot move backward past an already accepted request time.

Seven new test instances cover gaps of 0.04, 0.1 and 0.49 s, observed velocity and
acceleration rejection, repeated-delay total timeout, and request/tick ordering.
The complete **161-case** test suite passed after this change. In the separate
0.49 s reproduction, the corrected run succeeded at 4.71 s with peak velocity
`0.0462923 rad/s` and peak finite difference acceleration `0.381378 rad/s^2`,
inside the unchanged bounds.

The current reviewed `motion.py` SHA-256 is
`364367f25d15f5b978317965186f7dafde4ff3c88a7104094f55fe7b8d21cada`.

## Reproduce the local core check

The actual successful local invocation was:

```bash
PYTHONPATH=/Users/delaynomore/Downloads/test/src/agibot_g2_demo \
uv run --no-project --python /opt/homebrew/bin/python3.11 --with pytest \
  python -m pytest src/agibot_g2_demo/test/test_motion.py -q \
  -o cache_dir=/Users/delaynomore/Downloads/test/.cache/pytest-motion \
  --junitxml=/Users/delaynomore/Downloads/test/.artifacts/python-local/core-py311-junit.xml
```

`uv` provided an isolated test-only environment because the inspected local
Python interpreters had no pytest installation. This did not add an SDK or a
production dependency. An initial collection attempt with a relative pytest
`pythonpath` failed with exit 2 because pytest selected the package directory as
its root; an absolute `PYTHONPATH` corrected that harness issue. No source test
was removed. The subsequent initial run passed 154 tests; the post-fix run above
passed 161 and saved JUnit.

The final ROS suite has 26 passing cases: default disabled operation (1), movement and
concurrent requests/cached status (1), fault injection (8), telemetry rejection
(1), signal shutdown (2), invalid startup (6), GDK dependency guard (1), Python
entry-point metadata (1), partial startup cleanup (1), runner cleanup (1),
simulated-clock startup rejection (2), and immutable parameters (1).
All passed in the final VM colcon run. Temporary ROS probes and process
checks complement the independent core tests.

## Remaining verification and limitations

- Python package build, all core/ROS tests and two independent clean end-to-end
  runs are complete in the Ubuntu ARM64 VM. Exact identities, samples and exits
  are in `test_report_vm_python.md`. Hardware verification remains separate.
- The mock is not a hard real-time controller. Its synthetic derivative checks
  are numerical checks on available samples, not hardware acceleration sensing.
- `Engine` calls must stay serialized and its wrapper must call `shutdown`.
  Explicit bounded cleanup replaces reliance on the old C++ destructor; Python
  garbage collection is not used as a stop mechanism.
- Unavailable velocity/effort fields stay empty. Stable position samples do not
  prove any unmeasured hardware quantity. The core is not used for GDK motion.
- No unresolved defect was reproduced in the revised normal mock and covered
  failure paths during this review. The core tests alone do not establish ROS runtime, SDK ABI,
  device time mapping, collision safety or G2 behavior.

## References and reuse decision

The implementation was adapted from this repository's preserved
`legacy/cpp/agibot_g2_demo/{include/agibot_g2_demo/core.hpp,src/core.cpp,test/test_core.cpp}`.
It was rewritten as Python logic, with the scheduling correction above.
No external code was copied. The official Python 3.10
[dataclass documentation](https://docs.python.org/3.10/library/dataclasses.html),
[monotonic clock documentation](https://docs.python.org/3.10/library/time.html#time.monotonic),
and [Protocol documentation](https://docs.python.org/3.10/library/typing.html#typing.Protocol)
were used only to check language behavior and compatibility. ROS field handling
follows the official Humble
[JointState definition](https://github.com/ros2/common_interfaces/blob/humble/sensor_msgs/msg/JointState.msg).
These are language/message references, not GDK 2.6.3 interface evidence.

Capabilities used for this migration review: local `rg`/file reads, Python 3.11,
stdlib AST/XML/hash/tar inspection, isolated `uv`/pytest for the core, and read-only
official documentation browsing. No robot connection, vendor package, native
compiler, C++ subprocess or VM execution was used by this review.

## Final VM integration evidence

The final source runtime hash is
`993e656266756908544da51e881a7d1582dab15f343dcdb30c961bdad224a7ab`.
The final VM suite passed all 223 tests on system Python3.10.12 / ROS Humble:
161 motion tests,36 GDK mapping/IPC tests and26 ROS integration tests.
Installed Python source bytes match the image's original package source;
identity checks also establish actual Python interpreter/module paths.
`docs/test_report_vm_python.md` records exact commands, image ID, source hash,
JUnit, samples, two independent results and normal/interrupted cleanup.
The original22 ROS cases were retained; added checks cover installed metadata,
two simulated-clock startup cases and immutable runtime parameters.
