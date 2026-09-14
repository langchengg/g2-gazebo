# Native Linux model preparation

This is a conversion-only toolchain. It neither installs a GDK nor changes the
Python interpreter used by ROS 2 Humble. The generated model is a local external
dependency, not part of the source archive.

## Sources and architecture

`Dockerfile.model-tools` builds the official OpenUSD 26.08 source at commit
`ee47c679abde5b467a7b6a41f3b2285564a4222e` (the peeled `v26.08` tag). The official
26.8 `usd-core` release did not provide a Linux ARM64 wheel when checked. The
source route avoids wheel relabeling, emulation, and dependence on a Mac.

The build reuses the pinned Humble/Jammy base image. It uses Jammy Python 3.10,
oneTBB 2021.12.0 at commit
`9afd759b72c0c233cd5ea3c3c06b0894c9da9c54`, and the official CMake 3.31.10 binary wheel; OpenUSD requires CMake 3.27 or
newer, whereas Jammy's default is older. Imaging, USDView, GPU integration,
examples, tutorials, tests, validation, and execution libraries are disabled.
Usd, UsdGeom, UsdShade and their Python bindings remain enabled. Parallelism is
limited to two jobs. The oneTBB version follows the pinned OpenUSD
`build_usd.py`; the first VM attempt with Jammy oneTBB 2021.5 failed because its
`task_group` lacks the constructor used by USD 26.08. The source dependency is
installed under `/opt/tbb` and copied into the tool runtime, with explicit CMake
and loader paths. No USD source patch or system-wide TBB replacement is used. Source and temporary build files are removed in the same
Docker build step. The final stage contains only the installed USD libraries,
Python bindings, license/source information and runtime dependencies.

Build completion includes a real Python import, exact USD version check and an
in-memory stage/geometry smoke test. `/opt/usd/system-packages.txt` records the
actual resolved runtime Debian packages. This is a pinned source and tested
package strategy, not a claim of bit-for-bit Docker image reproducibility.

Official references (inspected before implementation):

- [OpenUSD source and build requirements](https://github.com/PixarAnimationStudios/OpenUSD/blob/ee47c679abde5b467a7b6a41f3b2285564a4222e/CMakeLists.txt)
- [Supported CMake options](https://github.com/PixarAnimationStudios/OpenUSD/blob/ee47c679abde5b467a7b6a41f3b2285564a4222e/cmake/defaults/Options.cmake)
- [Official oneTBB version selection](https://github.com/PixarAnimationStudios/OpenUSD/blob/ee47c679abde5b467a7b6a41f3b2285564a4222e/build_scripts/build_usd.py)
- [Required dependencies](https://github.com/PixarAnimationStudios/OpenUSD/blob/ee47c679abde5b467a7b6a41f3b2285564a4222e/cmake/defaults/Packages.cmake)
- [CMake 3.31.10 packages](https://pypi.org/project/cmake/3.31.10/#files)

## Direct commands

Run from the extracted source directory on Ubuntu with authorized Docker access.
These direct commands are the implementation behind the Make entry points:

```bash
python3 scripts/prepare_model.py --build-only
python3 scripts/fetch_g2_model.py --accept-noncommercial-license
python3 scripts/prepare_model.py
python3 scripts/prepare_model.py --check-only
```

Read the official license linked in `model_sources/g2.lock.json` before passing
the acknowledgment flag. Each recipient confirms their own noncommercial use;
the original author's confirmation does not grant commercial or redistribution
rights to someone else. The acknowledgment is local and tied to the source lock
hash. First-time fetching is public HTTPS and does not require an author token.

The default cache is `.artifacts/gazebo-model`. `--cache PATH` selects a different
raw input cache; `--output PATH` selects a generated output directory. Paths with
spaces are supported when shell-quoted. `--image TAG` chooses a local tool image
name. A matching Dockerfile content label allows a previously built tool image
to be reused. Input downloads are reused only after size and SHA-256 checks.
Corrupt cached inputs are moved to a unique `quarantine` directory before a
replacement is fetched; they are not silently overwritten or trusted.

To check deterministic conversion into two initially empty directories:

```bash
python3 scripts/prepare_model.py --output '.artifacts/model-check first'
python3 scripts/prepare_model.py --output '.artifacts/model-check second'
cmp '.artifacts/model-check first/generated_manifest.json' \
    '.artifacts/model-check second/generated_manifest.json'
```

Both output directories use the same validated raw input cache. The converter
refuses a nonempty output directory. An interrupted output can be kept for
inspection; select a new directory for retry. `--check-only` verifies the exact
file set and every output hash, converter hash, lock hash, runtime configuration,
revision and seven-joint inventory. Changing the converter or lock deliberately
invalidates old generated output; preserve it and convert into a new directory.

## Closed conversion inputs

The lock contains the URDF, same-revision USD layers, configuration and original
license/readme files. Every loaded composed layer must exist under the mounted
raw directory **and** appear in the lock. The converter rejects composition
errors, unreviewed external asset properties (including asset arrays), escaping
layers and unexpected coordinate conventions. `OmniPBR.mdl` is a named shader
implementation omitted by the deliberate constant diffuse material conversion;
it is not downloaded or executed. No textures are silently loaded elsewhere.

The conversion container has `--network none`, a read-only root filesystem,
read-only source/raw input mounts, a dedicated output mount and no devices or
host Docker socket. Its runtime does not read the prior generated model. The
existing geometry logic preserves source units, transforms, authored normals,
material subsets and same-source attachment repairs; only explicitly reported
zero-area faces are omitted. It writes joint inventory, conversion details,
original license attribution, OBJ/MTL resources and a sorted SHA-256 manifest.
Gazebo and RViz parsing/visual checks are separate runtime acceptance steps.

The generated URDF is shared by Gazebo and RViz. Its mesh resources use explicit
`file:///opt/g2-model/meshes/...obj` URIs, which RViz Humble's
`resource_retriever`/libcurl can load. The generated directory must be mounted at
`/opt/g2-model` in the runtime container. Validation decodes these file URIs and
checks that every referenced mesh and its relative OBJ/MTL materials exist within
the checked generated directory; bare absolute mesh paths are rejected.

Execution results, measured resource usage and any platform limitations belong
in the release reproduction receipt. Source availability or a Dockerfile alone
is not evidence that native compilation or model conversion passed.
