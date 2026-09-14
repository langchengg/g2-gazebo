# Python migration: GDK 2.6.3 review and implementation evidence

Review date: 2026-09-08. Selected route: direct `agibot_gdk` Python binding, read-only. Status: **DOC_IMPLEMENTED / SDK_UNVERIFIED**. This records actual adapter code, not a claim that a proprietary SDK was obtained, imported, installed or tested. Motion remains UNIMPLEMENTED.

## Reading provenance and source selection

The existing version-scoped cache and complete 43-page reading ledger were reused. This pass did not re-download the site, count identical pages again, or lower the scope to an attachment's smaller page list. The original 43/43 READ_COMPLETE status comes from the earlier full reading recorded in `gdk_reading_notes.md`; this migration pass selectively re-read the relevant text and checked its signatures and warnings against implementation. Exact full URLs, observed resource URLs, capture time, hashes and cache locations remain in `gdk_page_index.csv`.

| Page rechecked | Scope of this migration pass | Concrete conclusion |
|---|---|---|
| [Python Common](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/common.md) | Full page, including examples and all usage notes | No-argument init/release return `GDKRes`; compare actual `kSuccess`. Initialize before module construction; close/drop module ownership before global release. No documented Robot.close. |
| [Python Robot](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/robot.md) | State section 1, whole-body section 2, control status section 3 and planning section 7, with field tables and examples; earlier full-page read retained | Readout is a dict, not a guessed tuple. Explicit motor_position/motor_velocity guidance takes precedence over example prints of reserved fields. Planning blocks; its lifetime is not a proven call timeout or cancellation mechanism. |
| [Python usage](https://support.agibot.com/?gdk_version=2.6.3#contents/howto/python.md) | Full page | Default binding Python 3.10; alternate versions need shipped pybind rebuild. Linux x86_64/aarch64 is mentioned, but actual package support is uninspected. Use actual environment after inspection, not invented transport arguments. |
| [Python quick start](https://support.agibot.com/?gdk_version=2.6.3#contents/getting-started/quick-start/python.md) | Full page | Installer/example comes from robot-local endpoints. Keyboard motion commands are not SDK signatures. Historical review: no endpoint was contacted then. This continuation attempted installer GETs from Mac and VM (both timed out); no motion example was run. |
| [Deployment](https://support.agibot.com/?gdk_version=2.6.3#contents/howto/deploy.md) | Full page | Developer-machine requirement names Ubuntu 22.04/x86_64; this does not establish all package architectures. No public pinned SDK package was acquired. |
| [Time synchronization](https://support.agibot.com/?gdk_version=2.6.3#contents/howto/ptp.md) | Full page | Optional vendor PTP scripts require hardware/network/root conditions and the client runs outside the container. Their description does not identify this joint timestamp's epoch or prove synchronization. Nothing was run. |
| [ROS2 usage](https://support.agibot.com/?gdk_version=2.6.3#contents/howto/ros2.md) and [Control](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/ROS2/control_node.md) | Full usage and Control pages | Vendor DDS needs a bridge for ROS topics. Real genie_msgs definitions are absent, and request type spelling/descriptions conflict. Direct Python avoids inventing a message package or quietly adding a vendor bridge. |
| [Joint errors](https://support.agibot.com/?gdk_version=2.6.3#contents/appendices/joint_error_code.md) | Family split, applicable-joint lists and representative code rows rechecked; earlier full-page read retained | Head/waist and arm decoding differs. This read-only adapter rejects any nonzero code instead of guessing a decoder, clearing faults or changing modes. |
| [C++ Robot](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/robot.md) | JointState table only as same-version cross-check | It explicitly identifies error code zero as normal and uint64 source timestamp. No C++ API is mixed into the Python call path. |

The Python Common cache hash is `86af0f7f25ef3d7a11721eca151fd1870895e62093a56783c6e6ae4f06decb79`; Python Robot is `4a5d40568491e6d1c36a7e8f3f268380365ceb0c231dcf234c7dd6cda9704c0a`. The version was established previously by actual UI/config/resource evidence and cross-version body comparison, not merely the query string. Complete vendor bodies remain gitignored.

For the implementation mechanism, current official [Python 3.10 multiprocessing documentation](https://docs.python.org/3.10/library/multiprocessing.html), [metadata documentation](https://docs.python.org/3.10/library/importlib.metadata.html) and [socket documentation](https://docs.python.org/3.10/library/socket.html) were checked. They support spawn context, installed distribution metadata and local socket use. They are not GDK evidence. Existing project Observation/ROS architecture was reused. No external SDK implementation, third-party code, vendor module stub or vendor message package was copied.

## What was implemented

`src/agibot_g2_demo/agibot_g2_demo/backends/gdk_backend.py` contains three independently testable layers:

1. `map_joint_states()` validates the documented dictionary and converts only actual motor position/velocity. It verifies names, count, arrays, finite values and errors. It reorders by the approved mapping, leaves unavailable velocity and unverified effort empty, and preserves the opaque source timestamp.
2. `preflight_gdk()` reads only local project JSON, actual import location, installed distribution version and ELF headers. It never imports the native binding or connects. Missing/unknown evidence fails explicitly. Python 3.10 is required for the currently selected binding route; other rebuilt bindings remain unreviewed. Local metadata success is not SDK ABI/load success.
3. `GdkBackend` owns one serial SDK worker process. Only that worker imports `agibot_gdk` and contains the four documented call expressions. Nonblocking datagrams, single outstanding request, monotonic deadlines and fatal-state propagation keep native calls out of the ROS executor. The worker is an OS process, not a ROS node. No reconnect, mode change, motor command, reset or fallback is implemented.

This is substantive document-derived read-only implementation even while dependencies are absent. The implementation status does not change real binding checks or device tests from NOT RUN. The project JSON fields are not official vendor configuration; `gdk_init()` receives no parameters.

## Read-only gates and time semantics

The project JSON must include explicit read-only connection permission, approved complete actual joint names, confirmed motor-to-joint coordinate equivalence, and the selected actual SDK tree. None is filled with a guessed IP, real joint name, safe angle or control mode. Package metadata must identify the actual distribution for `agibot_gdk`; absence produces VERSION_UNVERIFIED. Distribution version is not product version. The continuation now rejects VERSION_MAPPING_UNVERIFIED, even when the strings match, until actual vendor release evidence establishes the relationship. There is no configurable bypass. All selected shared objects must have compatible Linux 64-bit ELF headers. Runtime loader paths, glibc/C++ ABI, firmware compatibility, SDK licensing/provenance and actual native import still require inspection and separate tests.

The SDK's raw nanoseconds are retained as opaque source data. Local `Observation.sample_time` is monotonic receive time; ROS output is labeled `gdk_local_receive_time_only`. It is never presented as a mapped hardware sampling clock. Equal source stamps produce no publication/update; backward stamps or missing progress fault. A progressing cached timestamp cannot prove absolute sample age, so the health text explicitly says hardware sample age is UNVERIFIED. No PTP setup or latency claim is made.

`poll_timeout` and `startup_timeout` are project watchdog settings, not vendor API arguments or real-time guarantees. Read deadlines are checked before consuming queued responses. No historical command backlog is sent. `failed` and `failure_reason` are project properties used by the owner to exit nonzero on native import/init/read failures or source faults.

Shutdown first asks the worker to finish/drop its Robot reference and call release. After bounded waits, it terminates/kills its own child and records missing release acknowledgement as UNVERIFIED. A native destructor/release can still hang and be terminated. This isolation does not prove vendor lifecycle semantics, guarantee hardware stopping, or authorize motion. Normal OS scheduling delays can extend wall time beyond individual join timeout arguments.

## Why motion remains unavailable

The reviewed planning method returns after reaching its target, so it cannot be treated as nonblocking acceptance. Cancellation/stop under interruption, maximum blocking time, lifetime expiry behavior, control ownership, and safe non-target-joint holding remain unresolved. Navigation cancel is not arm cancel and gripper opening is not arm movement. No guessed SDK symbol was added for any of these operations.

The current adapter rejects both project `command_positions()` and `hold()`. The ROS hardware branch rejects enabled motion and Trigger requests. No automatic fault reset, stop-mode switch, emergency-stop release, zero pose, return-to-start, or reconnection is performed. Device read-only and motion authorization remain separate.

## Validation evidence

Initial focused command on the Mac host, Darwin ARM64, Python 3.14.6:

```sh
PYTHONPATH=src/agibot_g2_demo python3 -m unittest discover \
  -s src/agibot_g2_demo/test -p test_gdk_mapping.py -v
```

The initial run passed 34 tests; the completed focused suite runs **36 tests, exit 0**, including actual local spawn/datagram communication with an explicitly named project fixture worker and termination of a deliberately stuck fixture. Final local evidence is in `.artifacts/gdk-python/report.json` and `check-1.log`; `check-2.log` records Python syntax compilation exit 0, and `check-3.log` records the expected inspector rejection exit 2 for an absent project config. These stdlib tests also run under pytest/colcon; the Mac run is not a ROS integration or Python 3.10 SDK compatibility claim. The root project test report records later Ubuntu/container/colcon runs separately.

Coverage includes reserved-versus-actual fields, missing/NaN/Inf values, dimensions/names/count, unknown velocity, empty effort, nonzero errors, missing SDK/config gates, raw source repetition/backward progression, delayed replies, source/read/startup timeouts, nonblocking parent polling, single pending request, explicit motion refusal, and bounded/idempotent cleanup. The tiny ELF-header fixture only tests parsing; it is not a loadable library and is never used as vendor SDK evidence. No `agibot_gdk` module or `genie_msgs` namespace is fabricated by tests.

`scripts/inspect_gdk.py --config PATH` can inspect a supplied project JSON without connecting; `--elf PATH` only reads an already supplied ELF header. It returns exit 2 on unavailable evidence. No SDK has yet been supplied, so real package architecture/ABI, binding import, init/read/release, G2 read-only telemetry, and G2 motion are **NOT RUN / BLOCKED where prerequisites are missing**.

## Remaining material

Supply the authorized GDK 2.6.3 deployment/binding package and its version/license evidence, vendor minimal Python example and supported execution platform, exact G2 model/firmware compatibility, reviewed runtime environment, and approved motor/joint/time mapping. Do not install `.deb` files or load `.so` files before architecture/ABI inspection. The user's Ubuntu 22.04.5 ARM64 VM is the primary target; neither its working mock nor a document mentioning aarch64 proves this particular SDK package supports it. After inspection, record real binding load and one authorized read-only session separately. Motion additionally requires the unresolved vendor safety semantics and an explicit on-site small-motion authorization.
