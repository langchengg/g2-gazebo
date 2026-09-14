# Validation summary (repository state)

This file links the README instructions to the exact source checked during this submission.

- Validation date (UTC): 2026-09-14
- Repository: `g2-gazebo`
- Checked local commit: `1bbe2d4` (clean working tree)
- Compared branch: `origin/main`
- Commit relation: `origin/main` is base; this branch is one commit ahead.

## Scope of this submission

- Focused cleanup for submission readiness (platform preflight, metadata cleanup, headless-first docs).
- Core simulation logic, conversion pipeline, and controllers are unchanged from provided baseline.

## Evidence-backed checks executed in this environment

Because the workspace currently runs on macOS and `pytest` is not installed in this Python runtime,
only parser-level and script-level checks are recorded here.

1. Doctor preflight logic (ARM64 host, Linux path)
   - Runner: `python3 -c` unit logic call to `scripts.doctor.validate_environment`
   - Input checks: Linux/arm64 + local context + local daemon + running Buildx + Ubuntu-like markers
   - Result: no errors, `preflight_result=PASS`, `validation_status=PASS`, no warnings

2. Platform behavior for x86_64/amd64 (preflight-only contract)
   - Runner: same mocked check with host and daemon set to amd64
   - Result: no errors, `preflight_result=PASS`, warnings present, `validation_status=NOT_TESTED`
   - Meaning: preflight allowed; native amd64 runtime still requires explicit revalidation

3. Unsupported host failure
   - Runner: Darwin host and Linux+riscv64 host cases
   - Result: errors produced for both unsupported host families (as expected)

4. Remote daemon/buildx override rejection
   - Runner: mocked `DOCKER_HOST`, `DOCKER_CONTEXT`, `BUILDX_BUILDER`, `BUILDKIT_HOST`
   - Result: hard-failed in validation when set

5. Package metadata checks
   - `src/agibot_g2_demo/setup.py`
   - `src/agibot_g2_demo/package.xml`
   - `src/agibot_g2_description/package.xml`
   - `src/agibot_g2_visual_tools/package.xml`
   - Result: maintainer/name/description fields updated to concrete project owner and scope.

## What is not yet validated in this round

- Full ARM64 Gazebo conversion/build/verify on this checkout was not run in this macOS session.
- Full amd64 native conversion/build/GUI verification was not run.
- The above require a Linux host that can execute Docker/ROS/Gazebo toolchain.

## How this README is validated against implementation

- `README.md` and `README.zh-CN.md` now share the same command checklist in `docs/quickstart.commands.sh`.
- The quick path in both languages is:
  `make doctor -> make fetch-model -> make prepare-model -> make build-sim -> make verify-sim`
- GUI path is clearly optional and uses existing desktop session (`demo-visual`).

## Artifact pointers for this source snapshot

- Modified files:
  - `scripts/doctor.py`
  - `src/agibot_g2_demo/test/test_doctor.py`
  - `src/agibot_g2_demo/package.xml`
  - `src/agibot_g2_demo/setup.py`
  - `src/agibot_g2_description/package.xml`
  - `src/agibot_g2_visual_tools/package.xml`
  - `README.md`
  - `README.zh-CN.md`
  - `docs/quickstart.commands.sh`
