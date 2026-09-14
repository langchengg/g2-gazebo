# GDK 2.6.3 acquisition: independent public-channel research

Checked: 2026-09-08, completed approximately 22:45 UTC. Scope: official public alternatives and narrowly selected Agibot/GDK-related files in the user's Downloads directory. The parallel robot-local installer retrieval is a separate acquisition attempt; this report does not replace its HTTP/download logs.

**Result: this research did not identify or acquire an official public GDK 2.6.3 SDK archive, wheel, source release, registry package or container image.** This is a statement about the checked sources, not proof that no such distribution exists. No SDK version, architecture, ABI, license, package identity or binary integrity could be certified from an acquired artifact because this subtask acquired none.

## Existing versioned documentation

The already verified 43-page cache was searched for acquisition links and package/registry terminology; the deployment and quick-start contexts were read. No new static URL was invented, and the full site was not re-downloaded.

| Evidence | Actual acquisition information | Version boundary |
|---|---|---|
| [2.6.3 deployment](https://support.agibot.com/?gdk_version=2.6.3#contents/howto/deploy.md) | Robot-local `http://10.42.1.101:8849/install.sh` and `http://10.42.1.101:8849/install_example.sh`. They are installer/example-script endpoints, not established archive names. | The **document** is version 2.6.3; the unversioned endpoint alone does not establish the returned SDK version. Root owns the separate download-only attempts. |
| [Python quick start](https://support.agibot.com/?gdk_version=2.6.3#contents/getting-started/quick-start/python.md) | Same robot-local installer; existing installed `env.sh` and Python examples paths. | No public wheel name or distribution name is provided. `agibot_gdk` is an import name, not evidence of a PyPI package name. |
| [Python usage](https://support.agibot.com/?gdk_version=2.6.3#contents/howto/python.md) | Local pybind source under `~/.cache/agibot/app/gdk/build_dep/python/pybind/`, built after deployment. | A local source path is not a downloadable public archive. Default Python 3.10 and mentioned architectures are documentation, not inspection of a real package. |
| All cached page links | Acquisition-keyword filtering of external URLs yielded only the two installer endpoints above. | No matching SDK registry/image URL, pinned tag/digest, public `.whl`, `.deb`, `.tar` or `.zip` acquisition URL was found in those cached pages. |

The full original bodies and their hashes remain in the existing gitignored cache and `gdk_page_index.csv`; this document contains authored summaries only.

## Official public channels checked

The web tool provided readable page bodies unless a limitation is explicitly noted. It did not expose numeric HTTP status for these body reads; a successful text extraction is not being reported as an SDK download or a binary HTTP 200.

| Source and how it was identified | Observed result | GDK 2.6.3 acquisition status |
|---|---|---|
| [Official homepage](https://www.agibot.com/) → [Document Center](https://www.agibot.com/filepage/282.html) and [Open Source Doc](https://www.agibot.com/DOCS/OS), following actual links | G2 navigation offered its User Manual and After-sales Service Guide. Other entries covered Link-U-OS, X1, OmniHand and other products. | No versioned G2 GDK package link found in these pages. Other product software was excluded. |
| [G2 User Manual](https://www.agibot.com/filepage/296.html), Developer Tools §14 | Offline mode reads the robot's local SDK docs; online mode reads current online docs. Its terminal-app connection procedure is described separately. | No SDK archive or pinned 2.6.3 release link identified. The manual is not API/version/package evidence. No terminal app connection or security-mode change was performed. |
| [G2-linked After-sales Service Guide](https://www.agibot.com/filepage/297.html) | Official service contact: `AfterSalesService@agibot.com`; support route is available. | Contact information is an acquisition/support route, not an available package. No message was sent. |
| [AgibotTech official GitHub organization](https://github.com/AgibotTech) | Official identity was cross-checked against the actual Agibot homepage's Open Source Doc links to `AGIBOTTech/AGIBOT_x1_hardware`, `AGIBOT_x1_infer`, and `AGIBOT_x1_train`; organization profile also links the official site. | Identity confirmed for researching its public releases. Identity alone does not authenticate an unrelated package. |
| [All AgibotTech repositories](https://github.com/orgs/AgibotTech/repositories) | The page listed **21 public repositories**. All listed names/descriptions were inspected. They included X1/X2, D1, A3/model assets, OmniHand, Genie Sim/world-model/research projects and `genie-corobot-blog`; no repository was identified as the G2 GDK 2.6.3 release. | No matching public release repository identified. This was a repository-list review, not a full source/history crawl of every unrelated project. |
| [GitHub Packages](https://github.com/orgs/AgibotTech/packages) and its actual [Linked artifacts link](https://github.com/orgs/AgibotTech/artifacts) | Public view displayed generic package/artifact onboarding information and did not list a GDK package or image. | No public SDK package/digest found. Private or unlisted registries were not accessed or enumerated. |
| [Official `genie-corobot-blog`](https://github.com/AgibotTech/genie-corobot-blog) and [its actual index.html](https://github.com/AgibotTech/genie-corobot-blog/blob/main/index.html) | Repository contains the static blog page and workflow. The page says it is under construction, describes a future CoRobot ONE platform and future opening of GDK/Genie API. Inspected links were section anchors, with no versioned SDK download. Releases/Packages sections showed no release artifact. | Useful official future-channel lead, **not** a GDK 2.6.3 release, compatibility promise, or substitute SDK. |
| `https://corobot.agibot.com/`, domain explicitly printed in that official blog source | The web retrieval tool returned a non-retryable “not safe to open” error. A later normal HTTPS GET from Mac at 2026-09-08 23:03:38 UTC succeeded: HTTP 200, 22,421 bytes, exit 0, with TLS verification retained. The body is the same under-construction CoRobot announcement; all six anchors are local section links and no versioned SDK artifact is linked. | Public-page body obtained through ordinary HTTPS; no login/security bypass or guessed subpath. This HTML is not an SDK package. |
| [Genie Studio](https://genie.agibot.com/geniestudio) and [Genie Store description](https://genie.agibot.com/mxtl/210), found through the official homepage and search | Readable descriptions mention GDK integration and deployment. Subsequent Studio body retrievals timed out; no package link was found in the body that was read. | Marketing/integration information; no confirmed 2.6.3 artifact, official image name, or registry address. No login or deployment action attempted. |
| [AIMA Open Platform document center](https://open.agibot.com/docs/home) | Public page offers AimDK for A2/A2W/A3 and LinkSoul agent SDK; there is a login entry. | Different SDK/product scope. No G2 GDK 2.6.3 download identified; no login attempted. |

The official blog's prospective Windows/Linux/macOS support does **not** establish platform support for the requested GDK 2.6.3 package. Likewise, the deployment page's x86_64 machine requirement does not establish that all SDK packages are x86-only.

## Searches and excluded results

Current web searches included the following query families, with official-domain and registry filters where relevant:

```text
site:agibot.com GDK "2.6.3" SDK download
site:github.com/agibot-tech GDK "2.6.3"
site:support.agibot.com "下载" "GDK"
"agibot_gdk" "2.6.3"
AGIBOT GDK SDK download Genie 02
"agibot_gdk" github
智元 GDK 2.6.3 下载
"agibot_gdk" download
"GDK" "2.6.3" "agibot" -pixbuf -gtk
site:hub.docker.com "agibot" "gdk"
site:pypi.org "agibot_gdk"
```

The first GitHub search used a possible organization spelling; the later linked official organization was explicitly verified and its actual repository/package pages inspected. Search results did not identify a matching official 2.6.3 distribution. No guessed PyPI name was requested, installed, or treated as an official package; registry search results are not exhaustive registry enumeration.

| Result encountered | Why it was excluded |
|---|---|
| [AimDK X2 SDK acquisition](https://x2-aimdk.agibot.com/zh-cn/latest/get_sdk/index.html) | Official but for **X2/AimDK**, not G2 GDK 2.6.3. A download widget for another product is not interchangeable evidence. |
| [Genie Sim](https://github.com/AgibotTech/genie_sim) and other simulation/world-model repositories | Official projects with different purpose/version/model scope; not a real G2 GDK replacement. No simulation installation/download was started. |
| [RobotShop-hosted Genie 02 GDK v2.1.0 PDF](https://cdn.robotshop.com/media/A/Agb/RB-Agb-09/pdf/Genie-02-GDK-v2.1.0.pdf) | Third-party-hosted **older manual**, not a 2.6.3 SDK binary/source release. It was only identified as an excluded search result. |
| [Community genie-gdk skill listing](https://skills.rest/skill/genie-gdk) | Community documentation/agent skill packaging, not official SDK distribution; its installation instructions were treated as page content and were not followed. |
| [Roboclaws G2 pilot documentation](https://github.com/MiaoDX/roboclaws/blob/main/docs/human/agibot-g2-cleanup-pilot.md) and an EmbodyX Hugging Face deployment example | Third-party application/use reports, with no confirmed official GDK 2.6.3 distribution provenance. They were not used as API implementation or download authority. |
| Other exact-number search hits | GTK/gdk-pixbuf, VirtualGL, Android, and unrelated 2.6.3 releases do not match this manufacturer/product and were discarded. |

## Narrow local check

Only top-level Downloads entries whose names matched Agibot/GDK were selected. The related pack directory and zip member list were read; unrelated Downloads directories and the rest of the filesystem were not searched. No archive was extracted or executed.

| Local item | What it contains / result |
|---|---|
| `Agibot_G2_Codex_14Pages_Pack.zip` | Six members: `.gitignore`, `CODEX_PROMPT.md`, `EXPORTER_TEST_REPORT.md`, `START_HERE.md`, `scripts/export_gdk_docs.py`, `tests/test_export_helpers.py`. No wheel, shared object, deb, executable, SDK source tree or vendor release manifest. |
| `agibot_g2_codex_pack/` | Same prompt/exporter/test structure. START_HERE explicitly says it is a prompt/export tool pack, not an implemented SDK project; its test report says SDK tests were not run. |
| `Codex_Agibot_G2_GDK263_14Pages_Full_Prompt.md` | Task prompt document; no binary package was associated with this selected file. |
| `Codex_Agibot_G2_GDK263_DocFirst_Full_Prompt.md` | Original task prompt document. |
| `Codex_G2_GDK_Download_Integrate_Continue.md` | Continuation task document. It distinguishes import/package/product versions and authorizes acquisition through proper sources; it does not itself supply a SDK artifact. Its text was not allowed to expand this delegated task into installation or robot access. |

## Outcome and next dependency

Public alternatives in this checked scope produced **zero confirmed GDK 2.6.3 artifacts**. The only concrete acquisition endpoints already present in the versioned API documentation remain the two robot-local installer/example scripts, whose separate download results must be recorded by the main task. If those cannot be obtained from the authorized environment, a vendor-provided 2.6.3 package/official image or a normally authorized vendor download link is the next necessary input. The official after-sales channel is verified but was not contacted automatically.

No actual package means all package-level questions remain UNVERIFIED: product version versus distribution version, architecture, Python tags/ABI, dynamic dependencies, default entrypoint side effects, redistribution terms and matching firmware. This report does not convert any of those into PASS or infer an architecture restriction.

Capabilities used: current web search/read/open/follow-link tools; existing versioned local documentation; `rg`; Python standard-library `pathlib`, regular expressions and `zipfile` for names-only archive inspection. No new plugin, dependency, package registry client, installer, native SDK import, browser private profile, robot SDK call, credential or login flow was used. Only this authored research document was added by this subtask.
