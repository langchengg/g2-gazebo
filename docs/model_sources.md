# G2 model source and asset handling

This project uses a G2 Omnipicker dual-arm model from the official AgiBot World
`GenieSimAssets` dataset for **noncommercial learning, research and demonstration**,
as explicitly confirmed by the user. This is a Gazebo conversion, not an official
GDK simulator or a model matched to a particular physical G2 / firmware revision.

## Pinned source

- Repository: https://huggingface.co/datasets/agibot-world/GenieSimAssets
- Revision: `a0813aad7c16165daffbe6c2737754e0344809ee`
- Variant: `robot/curobo_robot/assets/robot/G2/G2_omnipicker_fixed_dual.urdf`
- Original URDF: 67,256 bytes; SHA-256
  `eb782de0b6f1faf1fcddfb5e2f7004a39e350c4f297ca51a56003ce8f9ad8319`.
- Mesh source: the same directory's `configuration/robot_base.usd`,
  57,619,915 bytes; SHA-256
  `6abf3888859bc2385bd084bcdeec8fe464891110d61d3fa9ef1c7efd5a690488`.
- `model_sources/g2.lock.json` fixes every input path, byte count and SHA-256.
  The nine G2 files total 59,365,944 bytes; LICENSE and README add 24,305 bytes.

The actual dataset LICENSE is **CC BY-NC-SA 4.0**. Its README explicitly applies
that license to all data and code in that repository. No narrower asset license
was found in its recursive robot tree. The license permits adaptation subject to
attribution, noncommercial use and ShareAlike conditions. The project does not
infer permission for commercial use. Preserve the source notices and identify
conversions if distributing derived assets under those terms.

Original and generated assets stay in the ignored `.artifacts/gazebo-model/`
cache. Project-owned wrapper code does not relicense model data. Images containing
these assets are local development images, not publicly published images.

The alternative GitHub G2 descriptions were inspected but not used. In revision
`6ca11c7593ecf6b7dae58c28fd19f4a789a0dd46`, the model package's
[THIRD_PARTY_NOTICES](https://github.com/AgibotTech/genie_sim/blob/6ca11c7593ecf6b7dae58c28fd19f4a789a0dd46/source/geniesim_ros/src/ros_ws/src/genie_sim_robot_model/THIRD_PARTY_NOTICES)
contains specific proprietary G2 restrictions despite MPL files elsewhere. No
GitHub G2 mesh was used to fill the HF URDF's missing paths.

## Acquisition and conversion

The current receiver workflow uses native Linux Docker model tools; see
[Native Linux model preparation](linux_model_tools.md). From the extracted source
root on Ubuntu, read the pinned license and confirm your own noncommercial use:

```bash
python3 scripts/prepare_model.py --build-only
python3 scripts/fetch_g2_model.py --accept-noncommercial-license
python3 scripts/prepare_model.py
python3 scripts/prepare_model.py --check-only
```

The tool image builds official OpenUSD 26.08 and oneTBB from the commits in the
lock using Jammy Python 3.10. It is independent of the ROS runtime image and
requires no preconverted mesh or Mac interpreter. Generated assets remain local
external dependencies. See the release receipt for actual Linux execution results.

The downloader uses pinned HTTPS URLs, a 600-second monotonic deadline per file
including retries, finite socket timeouts, size/hash verification and atomic
replacement. It reuses only checked cached files, quarantines damaged inputs,
and rejects error pages, LFS pointers and changed content. No author token is
required for the currently public subset.

Historical baseline only: the earlier conversion ran on Mac ARM64 CPython 3.11
using the official OpenUSD 26.8 universal2 wheel, and generated files were
transferred to the VM. That historical route is not a receiver prerequisite or
evidence of this release's Linux conversion. PyPI currently has no Linux ARM64
usd-core 26.8 wheel; the current tool image therefore builds official source.

The original URDF's external FBX/STL/DAE references are not available in this HF
subset. The converter instead composes the included USD layers, then extracts
actual per-link visual and collision geometry. It bakes every mesh's transform
relative to its owning link into metric OBJ vertices. Authored material subsets
retain their constant diffuse colors through MTL; vendor MDL shader behavior is
replaced with basic diffuse rendering. Authored cylinder/box collision primitives
are tessellated with their exact dimensions/transforms (32 cylinder sides).
No file extension is merely renamed. The composed stage contains 106 exported visual/collision geometry objects. Every external asset-valued attribute is checked: the selected stage references only `OmniPBR.mdl` shader implementations, with no missing external texture file. The converter rejects an unreviewed texture/shader asset instead of silently dropping it.

Generated `conversion.json` records every USD prim, output path, transform,
bounds, material colors and mesh SHA-256. `joint_inventory.json` records original
joint limits, axes and transforms. `generated_manifest.json` hashes the generated
asset set. `/opt/g2-model` is the default container asset location and must contain
the whole checked generated directory. Mesh references in the shared Gazebo/RViz
URDF use explicit `file:///opt/g2-model/meshes/...obj` URIs. RViz Humble loads
resources through `resource_retriever`/libcurl, so a bare absolute filesystem path
is not a valid replacement. OBJ material-library references remain relative to
each OBJ and are checked for local closure. The URDF's controller YAML location is
an explicit converter option; it must match the installed description package.

## Verification boundary

The historical source acquisition, full USD composition, hash verification and
source inertia checks were executed on Mac. Current Linux cold acquisition and
conversion results must be read from the separate release reproduction receipt. Gazebo loading, controller tracking,
collision behavior and visual acceptance are recorded separately in the actual
VM simulation report; a successfully converted file alone is not a physics or
GUI acceptance result.

References: [pinned license](https://huggingface.co/datasets/agibot-world/GenieSimAssets/blob/a0813aad7c16165daffbe6c2737754e0344809ee/LICENSE),
[CC terms](https://creativecommons.org/licenses/by-nc-sa/4.0/),
[OpenUSD transform documentation](https://openusd.org/release/api/class_usd_geom_xform_cache.html),
[official USD Python distribution](https://pypi.org/project/usd-core/).

## Normal export correction from actual Fortress execution

The first VM physics run exposed an OBJ conversion defect: exported meshes had
positions/faces but no normals. Fortress/DART reported normal/vertex count
mismatches and subsequently crashed in the collision backend (exit 139). This
was a failed run, not a model-loading PASS. The converter now preserves USD
face-varying normals, transforms them with the inverse transpose into each link
frame, and splits vertices at normal seams. OBJ faces reference matched `v//vn`
indices, giving every imported vertex a finite unit normal. Box/cylinder
primitives receive geometric flat normals. Exact zero-area triangles carry no
surface/volume and are removed with per-object counts in `conversion.json`; no
collision object or physical link is removed. The corrected full asset set must
pass both an independent OBJ validator and the actual Ignition mesh importer
before the VM physics regression can be considered fixed.

The corrected export contains 2,797,310 paired vertices/normals and 1,410,916
nondegenerate triangles across 106 objects. The independent OBJ parser checked
every normal is finite and unit length, every face indexes its matching normal,
and every exported triangle has positive area: 106 passed, zero failed/skipped.
Five exact zero-area source triangles were recorded and omitted; all collision
objects remain. The generated manifest also records converter SHA-256, source
lock SHA-256 and runtime path/plugin arguments so an older converter cache cannot
be reused silently. This static result still needs the actual VM importer and
physics rerun recorded in the simulation test report.
