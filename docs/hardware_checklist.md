# Hardware acceptance checklist — NOT RUN

This checklist is a gate record, not authorization. No robot or proprietary SDK
has been supplied. All unchecked items remain UNVERIFIED. Mock settings are not
robot settings. Do not populate missing values from other models or releases.

- [ ] Record exact G2 model/variant, serial reference kept privately, firmware and controller build.
- [ ] Obtain authorized GDK2.6.3 documentation, release notes, SDK package and official examples.
- [ ] Inspect package Version/Architecture and ELF Machine with dpkg-deb, file and readelf before installation.
- [ ] Confirm Ubuntu22.04 execution CPU, compiler/ABI, dependencies and supported firmware against the actual package.
- [ ] Resolve conflicting signatures/types/semantics in the evidence mapping; import/load the real Python binding and run its official minimal example; inspect native ABI dependencies.
- [ ] Record SDK redistribution permission; keep proprietary files outside Git.
- [ ] Verify official runtime, initialization, process/thread constraints, lifecycle and configuration location.
- [ ] Inspect official network/deployment instructions before changing VM NIC mode. Record verified physical interface and route; do not reuse historic IPs by assumption.
- [ ] Establish read-only session with motion disabled. Record real errors and disconnect behavior.
- [ ] Confirm actual joint names/order, length, units, motor feedback versus command fields and validity markers.
- [ ] Confirm timestamp source/epoch and source update rate; detect unchanged cached samples independently of receipt activity.
- [ ] Compare read-only ROS samples with an authorized independent robot observation; unknown velocity/effort stay empty.
- [ ] Verify motion mode, control ownership, full/single-arm vector requirements, retained non-target joints, planning/collision protection and legal ranges.
- [ ] Verify acceptance versus completion, task/status identity, bounded asynchronous behavior and documented stop/cancel/hold semantics.
- [ ] Verify fresh feedback before every action. Reject missing configuration; never fill unknown joints with zero.
- [ ] On-site operator confirms pose, clearance, payload/tooling, joint limits, bystanders and emergency-stop readiness.
- [ ] Operator explicitly authorizes this one small arm motion with verified parameters; configuration alone is not authorization.
- [ ] Record accepted request and terminal result from actual feedback or official completion state. Do not infer success from acceptance or elapsed time.
- [ ] On timeout/disconnect request only documented failure handling. Record that communication loss may prevent delivery of stop; never send an uncertain return-home action.
- [ ] Verify shutdown, fault latch, reconnection without automatic resume, and controlled release of resources.

Hardware read-only telemetry: **NOT RUN**. Hardware motion: **NOT RUN**.
SDK compatibility and build: **BLOCKED** pending actual package and unresolved semantics.

## Python migration gates

- [ ] Inspect the actual Python 3.10 binding distribution/version, SDK provenance and every selected ELF architecture before native import.
- [ ] Confirm the documented motor positions are the intended joint coordinates and units for this exact G2 variant; do not infer from variable names alone.
- [ ] Supply a reviewed project JSON with explicit read-only authorization, actual SDK root and complete real joint mapping. Placeholder YAML is not authorization.
- [ ] Verify worker initialization, actual read results, source progression, timeout cleanup and release against the real SDK. Local IPC fixtures do not establish SDK compatibility.
- [ ] Resolve bounded stopping/cancellation and complete motion semantics before adding hardware movement. The current Python adapter is read-only.

The ARM64 VM is confirmed; the actual SDK architecture is still UNVERIFIED
because no package was supplied. If its binaries are x86_64-only, record
architecture compatibility BLOCKED and select a supported native x86_64 host.

## Acquisition continuation gates (2026-09-08)

- [ ] Obtain the authorized GDK **2.6.3** release from a verifiable official
  source; current robot-hosted installer GETs timed out on both Mac and VM.
- [ ] Inspect the installer before execution; confirm payload version selection,
  legal terms and side effects. An unversioned script URL is insufficient.
- [ ] Record actual package bytes/hash or image digest and vendor checksum if
  published; inspect wheel/deb/archive contents, Python tags and every relevant
  ELF component before installation. Do not infer ARM support from Python code.
- [ ] Establish the official product-version to distribution-version mapping;
  the current preflight deliberately rejects matching version text alone.
- [ ] Inspect real binding entrypoints for import side effects, then perform S1/S2
  under the VM ROS Python with no hardware network/devices/secrets. Preserve
  module `__file__`, real type signatures and actual linked libraries.
- [ ] Resolve `joint_control_request` return enum versus documented int0,
  unlisted joint behavior, velocity rules, lifetime start/expiry, GIL/concurrent
  read safety and a bounded official stop/fault strategy. Current serial worker
  cannot read feedback during the documented blocking motion call.
- [ ] Complete S4 authorized fresh read-only state and coordinate mapping before
  S5. Approve exactly one reviewed pose/target/limits plan on site. Request
  preparation or UUID equality never counts as completion or a safety waiver.

No navigation cancel API, process termination or `gdk_release()` is treated as
an arm stop. No SDK import, robot initialization, connection or movement occurred
in the acquisition continuation unless explicitly recorded in its new report.
