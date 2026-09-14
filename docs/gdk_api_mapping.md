# GDK 2.6.3 evidence and implementation boundary

Reviewed 2026-09-08 against the official 43-page version directory. The current Python/rclpy implementation now contains a document-derived **read-only** direct Python SDK adapter: `gdk_init()`, `Robot()`, `get_joint_states()`, and `gdk_release()`. It is **DOC_IMPLEMENTED / SDK_UNVERIFIED**; no real binding has been loaded and no robot has been contacted. See [current Python implementation mapping](#current-python-implementation-mapping) and [Python review](gdk_python_review.md).

The original C++ assessment below is retained as historical evidence; that implementation is archived under `legacy/cpp/agibot_g2_demo`. Statements below about an unimplemented `core.cpp` backend or `BUILD_GDK_BACKEND` describe that archived implementation, not the current Python package. The Python adapter does not make those historical SDK or hardware tests pass.

`RobotBackend`, `poll`, `command_positions`, `hold`, the `/g2/*` topics/services, and the run-ID status contract are **project interfaces**, not AGIBOT interfaces. In particular, the mock `hold()` behavior is not an assertion that GDK provides a corresponding stop function. The current mock command-stream interface cannot safely wrap an indefinitely blocking vendor planning call without an independently verified lifecycle/cancellation design.

Evidence hierarchy is versioned official docs, matching real SDK headers/bindings/types/examples, then same-version official repositories. No matching SDK was supplied or downloaded. Other-model SDKs, AimDK, GenieSim and other GDK versions are not implementation evidence.

## Independent verification states

“Documented” means a statement was read in the requested version, not that runtime semantics have been certified. Most C++ page headings omit arguments and do not reproduce full function declarations; the signatures below are explicitly **assembled from the documented return and parameter tables**, with qualifiers shown exactly where provided. SDK declarations, default arguments, ABI and overloads remain UNVERIFIED.

| Candidate | Document checked | SDK checked | Compiled/linked/loaded | Read-only device tested | Motion tested |
|---|---|---|---|---|---|
| GDKInit / GDKRelease | YES; lifecycle scope partly documented | NO — BLOCKED | NOT RUN | NOT RUN | NOT RUN |
| Robot construction | Example only; exact declaration UNVERIFIED | NO — BLOCKED | NOT RUN | NOT RUN | NOT RUN |
| GetJointStates | YES; timestamp/freshness/coordinate semantics PARTIAL | NO — BLOCKED | NOT RUN | NOT RUN | NOT RUN |
| GetWholeBodyStatus | YES; ownership/precondition interpretation PARTIAL | NO — BLOCKED | NOT RUN | NOT RUN | NOT RUN |
| GetMotionControlStatus | YES; no per-request completion contract | NO — BLOCKED | NOT RUN | NOT RUN | NOT RUN |
| JointControl / MoveArmJoint | YES; blocking planning documented, cancellation UNVERIFIED | NO — BLOCKED | NOT RUN | NOT RUN | NOT RUN |
| ROS2 `/hal/joint_state` bridge | YES; true message package/QoS UNVERIFIED | NO — BLOCKED | NOT RUN | NOT RUN | NOT RUN |
| Real stop/cancel/hold for this arm motion | NOT DOCUMENTED | NO — BLOCKED | NOT RUN | NOT RUN | NOT RUN |

## A. Installation, platform and redistribution

Sources: [deployment](https://support.agibot.com/?gdk_version=2.6.3#contents/howto/deploy.md), [C++ usage](https://support.agibot.com/?gdk_version=2.6.3#contents/howto/cpp.md), [Python usage](https://support.agibot.com/?gdk_version=2.6.3#contents/howto/python.md), [ROS2 usage](https://support.agibot.com/?gdk_version=2.6.3#contents/howto/ros2.md).

| Field | Evidence / unresolved boundary |
|---|---|
| Documented developer-machine requirement | Ubuntu 22.04, x86_64, Intel i9 or higher performance in deployment page. This is a documented deployment requirement, **not inspection of an actual package**. |
| Other architecture evidence | C++ CMake example selects `build_dep/cpp/x86_64` or `build_dep/cpp/aarch64`; Python build page names Linux x86_64/aarch64. Actual aarch64 files and supported robot/developer-machine combinations are UNVERIFIED. Do not conclude either universal ARM support or “x86 only.” |
| Current user platform | User-selected Ubuntu 22.04.5 ARM64 VM is the main execution environment. Mock compatibility and SDK compatibility are independent. A native ARM VM does not make an x86 ELF binary native-compatible. |
| SDK acquisition | Docs direct installation/examples retrieval to robot-local HTTP port 8849 endpoints, `install.sh` and `install_example.sh`. Historical review did not access these endpoints. The 2026-09-08 continuation actually attempted both from Mac and VM; all four curl transfers exited 28 with zero bytes (see gdk_acquisition.md). No public 2.6.3 SDK archive/wheel/apt repository was identified in the directory or focused official-source search. |
| SDK version selection | Required 2.6.3; package and firmware versions have not been inspected. The installer URL alone does not pin a version. |
| Header/library locations (documented, not present) | `GDK_HOME` defaults to `~/.cache/agibot`; C++ include: `app/gdk/build_dep/cpp/<arch>/include`; library: `app/gdk/build_dep/cpp/<arch>/lib/libgdk_adapter.so`; include example `gdk/gdk.h`. |
| Runtime path | Docs source `~/.cache/agibot/app/env.sh`. Exact variable contents, dependent libraries, loader paths and ABI are UNVERIFIED without the file/package. |
| Compiler/C++ ABI/glibc | NOT DOCUMENTED. Must inspect header requirements, ELF machine, dynamic dependencies and symbol versions before compiling/loading. |
| Version mismatch behavior | C++ usage says compile/runtime dynamic library versions must match and may log `Version mismatch`; no stable version-query API is documented here. |
| Python | Default 3.10; other versions use shipped pybind source. Page lists Python 3.8+, pybind11 >= 2.6.0, NumPy >= 1.19.0, protobuf >= 5.28.3. These requirements are not an instruction to install them for this C++ mock. |
| License/redistribution | SDK license and redistribution permission NOT DOCUMENTED. Full vendor documents and potential SDK packages remain gitignored; only authored summaries and necessary API facts are committed. |
| Firmware compatibility | NOT DOCUMENTED. Obtain exact G2 model/firmware and vendor-confirmed 2.6.3 support before any device access. |

When a permitted SDK is supplied, first inspect package metadata and every `.deb`/`.so`/executable architecture with platform tools before installing or executing it; inspect the official minimal example; then perform a real compiler/linker or binding load test. No generated substitute header or syntax-only check counts as SDK compatibility.

## B. Initialization and lifecycle

Source: [C++ Common](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/common.md), sections 1–2; cached source lines 11 and 47. Namespace evidence appears in the examples.

| Candidate documented form | Parameters, result and lifecycle | Project mapping / validation |
|---|---|---|
| `agibot::gdk::GDKRes agibot::gdk::GDKInit()` | No parameters. `GDKRes::kSuccess` is success; other values fail. Initializes global SDK/DDS/configuration before all other functionality; normally called once by one thread. | Future sole backend owner in `sayHello`; currently no call. No vendor initialization test run. |
| `agibot::gdk::GDKRes agibot::gdk::GDKRelease()` | No parameters. Success/non-success `GDKRes`; releases DDS/files/memory. Normally once on exit, including exception paths. Python Common explicitly closes specific objects first. | Future owned lifecycle cleanup; currently no call. SDK-specific object destruction ordering must be confirmed. |
| `agibot::gdk::Robot robot;` | Documented construction expression, **not a complete constructor signature**. Exact overloads, destructor, ownership and blocking behavior UNVERIFIED. Examples wait 1 s for DDS establishment. | Startup must test usable fresh observations rather than assume a fixed wait is readiness. |

Common lists `kSuccess`, `kInvalidInput`, `kInvalidOutput`, `kTimeout`, `kNotInitialized`, `kAlreadyInitialized`, `kInternalError`, without numeric values. Python Common/Types instead list `kRuntimeError` and `kUnknown`; the runtime enum must be inspected. No numeric return code is invented.

Documented transport is DDS with mixed deployment over a network. Exact network ports, configuration filenames for this module, domain, authentication, credential handling, connection-address argument, robot selection, init maximum duration, reconnect behavior, multi-process initialization compatibility and per-method thread safety are NOT DOCUMENTED. “One thread initializes the global system” does not prove concurrent SDK method calls are safe.

## C. Read-only joint and health observations

Source: [C++ Robot](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/robot.md), sections 1, 3 and 4, cached lines 13–68, 250–300 and 355–401. [Python Robot](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/robot.md) is a cross-check, not the selected binding.

Candidate documented form: `GDKRes Robot::GetJointStates(JointStates& joint_states)`. Return `kSuccess` means output available; other outcomes require rejection. The method has no documented input filter or timeout argument; maximum blocking time is UNVERIFIED.

| Structure/field | Documented type and unit | Mapping restriction |
|---|---|---|
| `JointStates.nums` | `size_t`, count | Require consistency with `states.size()`; expected hardware count UNVERIFIED. |
| `JointStates.states` | `std::vector<JointState>` | Resolve each name at runtime against approved device mapping; no assumed implicit order. |
| `JointStates.timestamp` | `uint64_t`, ns | Timestamp epoch, clock owner, hardware sampling vs sending time, wrap/restart behavior NOT DOCUMENTED. Do not call it ROS time without an established mapping. |
| `JointState.name` | `std::string` | Docs show `idx21_arm_l_joint1`…`idx27_arm_l_joint7` and `idx61_arm_r_joint1`…`idx67_arm_r_joint7`; these are source examples, not current device configuration. |
| `mode` | `uint32_t` | Per-joint SDK values not explained here; ROS2 comment says csp 0/cst 1, but SDK equivalence must be verified. |
| `position`, `velocity` | `double`, rad/rad·s⁻¹ | Robot page explicitly marks these as low-speed-motor reserved fields for this version. Do not publish them as actual feedback just because examples do. |
| `motor_position`, `motor_velocity` | `double`, rad/rad·s⁻¹ | Robot page explicitly directs use of these fields. Verify that their reference, sign, gearing and zero correspond to the approved physical joint mapping before mapping to ROS JointState. |
| `effort` | `double`, N·m | The table documents a field, but measurement validity/availability is not established. Publish empty effort unless real measurements are validated. |
| `motor_current` | `double`, A | Current is not effort and is not silently converted to torque. |
| `error_code` | `uint32_t`; C++ says 0 normal | Decode only using matching joint family/firmware; any unexplained nonzero code rejects motion. |

Requested/actual source frequency, zero/empty data behavior, cached-data behavior, sequence number, drop detection and stale thresholds are NOT DOCUMENTED. Repeated receipt alone is insufficient freshness. A future adapter must combine receive activity with a progressing source timestamp/sequence and explicitly identify its clock mapping. Until that is established, a local receive stamp is only a receive time; unavailable velocity/effort stay empty. The mock observation source and cadence cannot establish GDK sensor performance.

Additional candidates:

- `GDKRes Robot::GetWholeBodyStatus(WholeBodyStatus& whole_body_status)` has left/right `arm_error` (`uint32_t`), `arm_control` and `arm_estop` (`bool`), end errors/models, waist/lift/neck/chassis errors and a `uint64_t timestamp` in ns. A control boolean is not documented as a complete ownership-grant protocol. Requesting/releasing arm ownership and required transitions are NOT DOCUMENTED.
- `GDKRes Robot::GetMotionControlStatus(MotionControlStatus& status)` has names/poses, collision-pair vectors, `uint8_t mode`, `uint8_t error_code`, `std::string error_msg`, `std::vector<Twist> twists`, `std::vector<Wrench> wrenches`. C++/Python list mode 0 stop, 1 G1 servo, 2 planning, **5 G2 servo**; ROS2 Control lists only 0/1/2. There is no timestamp or run UUID in the C++ structure shown, and no per-command terminal-state rule. Collisions/error status can reject a request but cannot by itself prove a specific run completed.

Future project mapping: a GDK implementation of `RobotBackend::poll()` would produce validated `Observation` instances. No implementation/call location currently exists; `core.cpp::make_backend()` rejects `gdk`. The mock validator/tests establish project behavior only; vendor return, timestamp and stale-data semantics need separate SDK and device tests.

## D. Arm control candidates and rejected alternatives

Source: [C++ Robot](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/robot.md), section 7 cached line 790, section 10 line 1016; Python Robot sections 7–10 corroborate blocking planning descriptions.

Candidate form: `GDKRes Robot::JointControl(const JointControlReq& joint_control_req)`. It is described as path planning control that returns after reaching the target. This is not a nonblocking “command accepted” function.

| `JointControlReq` field | Documented type/unit | Required clarification |
|---|---|---|
| `life_time` | `double`, seconds | Exact valid range, whether lifetime bounds blocking, expiry action and relationship to trajectory duration NOT DOCUMENTED. Struct zero initialization is not a safe default. |
| `joint_names` | `std::vector<std::string>` | Name-addressed targets; example sends three left-arm names. Allowed subset semantics and nonlisted-joint behavior are not explicitly guaranteed. |
| `joint_positions` | `std::vector<double>`, rad | Target positions rather than increments. Must agree with current physical mapping and limits. |
| `joint_velocities` | `std::vector<double>`, rad/s | Semantics (limit/profile/direction), admissible zero, min/max and array rules not explicitly specified for this planning method. Do not copy the example's zero velocities. |
| `uuid` | `std::string`, unique request identifier | Appears in table and struct; some examples never assign it. Mandatory/optional/default and correlation contract UNVERIFIED. |
| `detail` | `std::string` | Descriptive metadata; mandatory/optional/default NOT DOCUMENTED. |

No acceleration, jerk, trajectory-duration or explicit absolute/relative flag is shown. No maximum blocking/cancellable-call guarantee is given. Non-target joints cannot be filled with zeros. Named-subset examples are insufficient to certify that unlisted joints are held or that a single target is collision-safe.

The page documents arm joint limit ranges (rad): joint 1 ±3.071796; joint 2 ±2.059505; joint 3 ±3.071796; joint 4 [-2.495838, 1.012308]; joint 5 ±3.071796; joint 6 ±1.012308; joint 7 ±1.535907, for each side. These are **versioned document values**, not approved limits for this user's as-yet unidentified firmware, load and pose. They are not inserted into `hardware.example.yaml` and are not a safe delta/velocity prescription.

Alternative planning form assembled from the table: `GDKRes Robot::MoveArmJoint(std::vector<double>& positions, const std::vector<double>& velocities, const int control_group)`. Group values are 0 left, 1 right, 2 both. The table lists 14 names in left-then-right order and the example uses group 2 with 14 positions/velocities. The documented **7-or-14 length check belongs to `MoveArmJointServo`**, a distinct method; single-arm planning-vector length and retention behavior cannot be imported from that page section. This unresolved requirement blocks a single-arm implementation.

Rejected for this demo:

- `JointServoControl`, `MoveHeadJointServo`, `MoveWaistJointServo`, `MoveArmJointServo`: 100 Hz continuous servo, with low-latency mode explicitly lacking collision protection. This task does not need a custom real-time servo. C++ generic velocity-array requirements conflict with the “reserved, may be empty” note.
- `EndEffectorPoseControl(const EndEffectorPose&)`: 50 Hz continuous interpolated pose commands in `base_link`, no collision detection; group values 4/8/12 differ from arm-joint group values. Not a high-level safe hello primitive.
- `MoveEEPos(const JointStates&)`: gripper/dexterous-hand opening/closing. It is not arm motion. Its same-named JointStates adds group/target_type not shown in the earlier status struct; this also requires the real header.

Future project mapping needs a distinct, bounded high-level motion request design rather than directly substituting blocking `JointControl` for mock `command_positions()`. No candidate is implemented or tested. Request validation and executor liveness tests of the mock do not resolve SDK concurrency.

## E. Completion and request correlation

The planning method descriptions say they return on target arrival, but do not specify tolerance, stable time, timeout guarantee, task handle, callback, cancellation or how failures during travel are reflected. The sample's “command sent successfully” log conflicts with the stronger prose description; it is not independent evidence.

The PNC page has task IDs and cancel/pause/resume for **navigation/chassis tasks**. These cannot be reused as arm cancellation or completion APIs. ROS2 control response has UUID and uint8 data, but no documented numeric meaning sufficient to certify motion completion.

The project's Trigger `success=true` therefore means acceptance only; project `run_id`/terminal status must be generated and correlated independently. Any future hardware SUCCEEDED state needs fresh, correctly mapped actual observations and a documented completion rule; no default mock tolerance/stable-time values are approved for hardware.

## F. Stop, failure and reconnect

No task-relevant arm stop/cancel/hold primitive with a verified 2.6.3 signature and bounded semantics was found in the complete directory. `GDKRelease()` documents resource cleanup, **not guaranteed stopping**. Quitting `mc_example.py` documents process exit, not emergency-stop semantics. PNC `CancelTask(uint32_t)` controls navigation, not arm planning.

A future real adapter remains blocked until the vendor clarifies stopping an in-flight planning call, call interruptibility, watchdog/expiry effects, disconnect handling, ownership loss, shutdown ordering and reinitialization. It must refuse new motion on invalid/old observations, errors or loss of connection, never issue an automatic return-to-start during an unknown failure, and never resume an old run on reconnect. Lost communication cannot provide a software guarantee that the hardware stopped. Hardware emergency-stop availability and on-site authorization are separate requirements.

## G. Official ROS2 forwarding

Sources: [ROS2 usage](https://support.agibot.com/?gdk_version=2.6.3#contents/howto/ros2.md), [ROS2 Control](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/ROS2/control_node.md).

| Item | Official evidence | Open issue |
|---|---|---|
| Bridge | Package `gdk_controller`, `controller.launch.py`, environment helper `ros_env.sh gdk_controller` | Actual executable/node name, package version, runtime DDS configuration uninspected. Must list as additional runtime if selected. |
| Feedback topic | `/hal/joint_state`, `genie_msgs::msg::JointState` | Custom vendor type, not sensor_msgs. True installed `.msg` and publication semantics must be checked. |
| Feedback fields | `header`; `string[] name`; `uint32[] mode`; float64 arrays `position`, `velocity`, `effort`, `motor_position`, `motor_velocity`, `motor_current`; `uint32[] error_code` | Match names/dimensions; reserved position note is on C++/Python Robot page; preserve actual source stamp after establishing its meaning. |
| Motion status | `/wbc/motion_control_status`, documented `genie_msgs::msg::MotionControlStatus.msg` | Header says base_link and sending time, not acquisition time; mode list differs from Robot API as above. |
| Request topic | `/MotionControlService/JointPosition/request` | Control page labels type `genie_msg::msg::CommonResponse.msg`, but howto uses `genie_msgs::msg::JointPositionRequst` and `joint_position_requst.hpp`. Do not silently correct spelling or create a substitute type. |
| Request fields | `header`, `lifetime`, `joint_names`, `joint_positions`, `joint_velocities`, `uuid`, `details` | Lifecycle spelling differs from C++ `life_time`, and details/detail differs. `.msg` package required. |
| Response topic | `/MotionControlService/JointPosition/response`, documented `genie_msg::msg::CommonResponse.msg`; header/data/uuid/detail | data success/acceptance/completion meaning NOT DOCUMENTED. These are topics despite Service in the path. |
| QoS/domain/rates | NOT DOCUMENTED for these five ROS2 reference pages | Inspect offered QoS using authorized read-only discovery and real package configuration; project mock QoS is not vendor QoS. |

The mock nodes/probes can stay in one container. A later hardware network configuration must be independent of mock's local-only DDS choices. ROS2 Humble or ARM image support cannot prove compatibility with the vendor bridge, its shared libraries or robot firmware.

## Evidence needed to unblock real integration

Obtain the officially provided GDK 2.6.3 package with redistribution/license terms, model/firmware compatibility confirmation, approved execution architecture/ABI, actual `gdk/gdk.h` and transitive headers, `libgdk_adapter.so` dependencies, `genie_msgs` definitions and vendor minimal example. Resolve the source clock/measurement mapping, single-arm planning vector, in-flight stop/timeout and concurrency questions. Then record real compilation/loading, authorized read-only telemetry, and finally one explicitly authorized small motion as separate evidence stages. None can be prefilled PASS.

## Current Python implementation mapping

This section supersedes the historical C++ implementation choices. One direct Python SDK route is selected; no vendor ROS bridge or invented `genie_msgs` package is added. The package uses `rclpy` and standard ROS messages. Its private SDK worker is an extra OS process owned by `sayHello`, not a third ROS node. Vendor DDS/runtime dependencies still have to be supplied and inspected.

| Actual call expression / documented form | Official source and exact signature evidence | Parameters, returns, constraints | Project location and test boundary |
|---|---|---|---|
| `sdk.gdk_init()`; documented `gdk_init() -> GDKRes` | [Python Common §1](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/common.md), cache lines 9–35 | No arguments. Compare the real `sdk.GDKRes.kSuccess`; do not invent numeric enum values. Initialize before module construction. Maximum blocking time NOT DOCUMENTED. | `backends/gdk_backend.py::_sdk_worker`, one call in one serial child process. Non-success/exception becomes fatal; startup deadline isolates a stuck native call. Actual SDK initialization NOT RUN. |
| `sdk.Robot()`; construction expression, complete binding declaration UNVERIFIED | [Python usage](https://support.agibot.com/?gdk_version=2.6.3#contents/howto/python.md), lines 56–63; [Python Robot §1 example](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/robot.md) | No arguments in the official example. Call only after successful init. Constructor overloads, readiness and destructor guarantees NOT DOCUMENTED. | `_sdk_worker`, unique owner. No fixed sleep is used as readiness proof: first valid sample must arrive before startup deadline. No undocumented `Robot.close()` call. Actual constructor/destructor NOT RUN. |
| `robot.get_joint_states()`; documented `get_joint_states() -> dict` | [Python Robot §1](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/robot.md), lines 13–38 | No arguments; `timestamp:int` ns, `nums:int`, `states:list[dict]`. No return-code tuple is documented. Malformed data, exceptions, per-joint nonzero error, non-advancing timestamp or deadline failure rejects data. Maximum duration/caching semantics NOT DOCUMENTED. | `_sdk_worker` calls the real method; `map_joint_states` validates/transforms; `GdkBackend.poll` checks IPC and source progression. Mapping/datagram fixture tests PASS; real call NOT RUN. |
| `sdk.gdk_release()`; documented `gdk_release() -> GDKRes` | [Python Common §2 and usage notes](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/common.md), lines 39–57 and 114–121 | No arguments; real `GDKRes.kSuccess` comparison. Release specific objects before global cleanup. No evidence that release stops motion. | Worker `finally` drops its sole Robot reference before one release after successful init. Release errors are reported. Forced process termination cannot guarantee cleanup; parent shutdown is bounded. Actual SDK release NOT RUN. |

Python annotations above assemble the official heading and return table; they are **not inspected pybind signatures**. No native version-query function, connection address parameter, joint-name query, stop/hold command, thread-safety guarantee, or success/error numeric enum is invented.

| Mapped input field | Type / unit / validation | Project output |
|---|---|---|
| `nums`, `states`, `name` | Integer count; exact approved full observation name set; unique nonempty names; dimensions match. No physical name/index is hardcoded. Input must be `dict` / `list[dict]`. | Name-addressed reorder to the operator-approved project configuration. Unknown/missing joints fail closed. |
| `motor_position` | Finite number, documented rad. Operator must first confirm actual motor-to-joint sign, gearing, zero and coordinate semantics. No guessed transformation is supplied. | `Observation.positions`, then `JointState.position`. Reserved `position` is not used. |
| `motor_velocity` | Finite number, documented rad/s. Either present for every mapped joint or absent for every joint; partial/invalid arrays fail. | `Observation.velocities` or empty array. Reserved `velocity` is not used. |
| `effort`, `motor_current` | Effort validity is unresolved; current is not torque. | Empty `Observation.efforts`; no zeros or current-to-torque conversion. |
| `error_code` | Integer, nonnegative; reject nonzero. Same-version C++ Robot table explicitly states zero is normal; Python table only says integer. Family-specific fault decoding remains separate. | Fatal read-only health; no reset/clear/estop/mode command is sent. |
| `timestamp` | Positive integer ns, bounded to uint64 as a project consistency rule using the C++ cross-check. Epoch, clock owner, sampling/sending interpretation and absolute hardware age remain UNVERIFIED. | Stored unchanged as `last_source_timestamp`. Equal values are discarded without new sequence or stamp; backward values fault and require explicit restart. It is never converted to ROS time. |

`Observation.sample_time` is local monotonic receive time. The ROS wrapper labels the header `gdk_local_receive_time_only`; this is not a hardware sample timestamp. The adapter's source progression check can detect repeated cache but cannot establish absolute hardware sample age or true production frequency from an opaque timestamp. Parent deadlines are checked **before** accepting queued replies so an overdue reply cannot be re-stamped as healthy. Project sequence increments only for accepted new source stamps.

The project `sdk_config_path` points to a JSON approval/mapping file containing `allow_read_only_connection: true`, `motor_position_mapping_confirmed: true`, an absolute inspected `sdk_root`, and approved full `joint_names`. This JSON is not passed to `gdk_init()` and does not configure vendor transport. Runtime configuration still comes from the inspected official deployment environment; do not guess IP/domain/auth fields. `telemetry` only runs pure preflight; it never constructs Robot or initializes the SDK.

Pure preflight inspects the binding's actual location and identifiable installed distribution metadata. It now fails VERSION_MAPPING_UNVERIFIED regardless of whether that distribution's version text equals `2.6.3`: the product/distribution relationship has no actual vendor evidence. Later Linux 64-bit ELF/Python 3.10 checks remain implemented for a future verified package route but cannot currently be reached past that gate. Unknown metadata, absent or mismatching native objects, and unsupported/unreviewed Python bindings produce explicit failure. Scanning is limited to the selected SDK tree, with project bounds of 20,000 entries, 2,048 shared objects and 10 seconds. These checks do not prove glibc/C++ ABI, transitive loader paths, firmware compatibility, vendor provenance or real import success. Those remain separate inspections and tests; the current session has no supplied SDK. `scripts/inspect_gdk.py` performs only local metadata/ELF reads and never imports a native SDK, installs a package or connects to a robot.

All SDK calls are serialized in one `multiprocessing` spawn worker. Parent IPC uses bounded, nonblocking AF_UNIX datagrams and only one pending poll. A fatal SDK error, startup/read deadline, invalid feedback, or stale/backward source timestamp terminates the worker and exposes project `failed`/`failure_reason`; the ROS owner exits nonzero. There is no automatic reconnection or mock fallback. Graceful shutdown requests worker release; after bounded waits it terminates/kills only its own child. A killed native call cannot be described as a successful vendor release or a hardware stop.

| Capability | Document verified | SDK checked | Real compile/link/load | Read-only device test | Motion device test |
|---|---|---|---|---|---|
| Python import/lifecycle expressions | YES; lifecycle/maximum blocking partly documented | NO — SDK_UNVERIFIED | NOT RUN | NOT RUN | NOT RUN |
| Python joint-state read and conversion | YES; motor fields and shape checked, device coordinate/time semantics UNVERIFIED | NO — SDK_UNVERIFIED | NOT RUN | NOT RUN | NOT RUN |
| Project preflight/conversion/nonblocking transport | DOC_IMPLEMENTED; project-specific, not a vendor API | No substitute SDK used | Project fixture tests only | NOT RUN | NOT RUN |
| Real arm motion/stop/completion | PARTIAL documentation; required cancellation/ownership semantics unresolved | NO — SDK_UNVERIFIED | NOT RUN | NOT RUN | NOT RUN |

`joint_control_request(JointControlReq) -> int` is documented as returning after reaching the target, with `0` success and exceptions on failure. That blocking motion method is **not called**. Its timeout/cancellation, shutdown during motion, control ownership, and per-request completion behavior remain insufficiently established. `command_positions()` and `hold()` explicitly raise UNIMPLEMENTED; the ROS hardware branch must reject `enable_motion=true` and all motion Trigger requests. No function name is inferred from a UI button, PNC navigation cancellation, or gripper control.

To advance the selected Python route, supply the authorized matching binding/deployment files and vendor minimal example, exact G2/firmware compatibility and supported ARM64 or x86_64 execution evidence. Inspect actual wheel/package metadata, `.so` dependencies/ABI and runtime environment; then perform a **separate** real binding load test and explicitly authorized read-only observation. A package without installed version metadata is VERSION_UNVERIFIED until a reliable vendor version source is reviewed. Motion still needs the unresolved safety semantics and one on-site authorization. Building the mock Python package and passing project fixture tests does not satisfy any of these hardware stages.

## 2026-09-08 acquisition continuation and motion contract

[Acquisition](gdk_acquisition.md) records actual Mac and VM installer downloads:
all timed out with zero bytes. No actual SDK file/symbol path can be supplied;
`SDK file = NOT OBTAINED` for every entry below. The direct Python route remains
the smallest documented route; no fake ROS vendor messages were added.

| Documented expression / exact fields | Source | Project implementation and verification |
|---|---|---|
| `agibot_gdk.JointControlReq()`; `joint_names: list[str]`, `joint_positions: list[float]` rad, `joint_velocities: list[float]` rad/s, `life_time: float` seconds, `detail: str` | Python Robot §7 and Types §JointControlReq | `backends/gdk_motion.py` builds these five documented fields through an injected actual type factory. Project-only validation tests; DOC_IMPLEMENTED / SDK_UNVERIFIED. No actual type constructed this run. |
| `Robot.joint_control_request(req: JointControlReq) -> int` (assembled from parameter/return tables) | Python Robot §7, cached lines 457–470; Types example compares GDKRes.kSuccess | Blocking until target per Robot text. Runtime dispatch remains unconditionally blocked, not waived by configuration. Exact pybind signature/return enum, GIL and concurrent read behavior need actual SDK. |
| `get_joint_states() -> dict`, `states[].motor_position`, optional `motor_velocity`, `error_code`, source `timestamp` | Python Robot state section | Existing read-only mapping and worker preserved; package-version gate corrected. Raw timestamp advancement and local receive freshness remain separate. Project fixture tests only. |
| `gdk_init()`, `Robot()`, `gdk_release()` | Python Common and Robot examples | Existing isolated read-only lifecycle source preserved. No import, construction, initialization or release called in this run. |

The planning request has no documented Python `uuid`, acceleration or trajectory
time field. `life_time` is a lifetime, not a verified cancellation deadline; its
start instant and expiry behavior are NOT DOCUMENTED. Unlisted-joint holding,
control ownership, legal velocity ranges, collision guarantees, maximum blocking
time, thread safety and safe handoff to concurrent observation remain UNVERIFIED.
The project requires explicit reviewed limits/mapping/authentication of the
specific request but those checks cannot prove missing vendor semantics.
`move_arm_joint` planning's single-arm length cannot be inferred from a separate
servo chapter's 7/14 rule. `MotionControlStatus.frame_names` are end-effector frame
names, not an approved full motor mapping; control-state flags do not prove this
process owns control.

No arm stop/cancel/hold symbol is documented sufficiently for use. Navigation
`cancel_task`, SDK release, worker termination, lifetime expiry and stopping
writes are not claimed arm stops. The serial SDK worker cannot poll while a
blocking planner executes; spawning another SDK owner or thread without GIL/
thread-safety evidence would introduce an unverified lifecycle. Therefore the
new contract can construct validated requests but never submit a real one or
report a real SUCCEEDED state. This is PARTIAL implementation, not a complete
motion backend. Acceptance UUID equality alone could not prove completion;
future execution needs an actual successful return plus fresh mapped observed
target error/stability and a verified failure/stop design.

Five independent statuses for all real calls: document checked PARTIAL;
actual SDK checked NO; installed/loaded NO; read-only device tested NO; motion
tested NO. No actual library architecture or distribution/product mapping is
known. Equal package version text is no longer accepted as product identity.
