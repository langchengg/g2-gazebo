# GDK 2.6.3 access and provenance report

Python migration update: the existing43-page ledger is preserved. Selective current re-reading and the document-derived read-only adapter are recorded in [gdk_python_review.md](gdk_python_review.md); real SDK and hardware validation remain separate.

Collection/review date: 2026-09-08. Entry: [official support page](https://support.agibot.com/?gdk_version=2.6.3#index.md). Final browser URL initially remained exactly this URL; title was **机器人开发套件**. Direct HTTP returned **200**, **560 bytes**, containing the app mount and script/style references, with no API body. The successful HTTP status and title were therefore not treated as successful documentation reading.

## Browser acquisition and version proof

The already available `mcp__cua_repl` Chrome capability was used; no Playwright installation, external debugger workaround, browser profile access or security-setting change was required. Its `cdp` capability requires an HTTP(S) origin before the first CDP command. Accordingly the initial page was opened, then `Network.enable` and the event cursor were set **before reloading** the documentation navigation. `Network.requestWillBeSent`, `Network.responseReceived` and `Network.loadingFailed` were observed. Readiness was bounded by a visible actual-body text locator, not unlimited `networkidle`.

Observed version evidence included:

- Visible version selector **2.6.3** and menu title **GDK v2.6.3**.
- A normal fetch of [version configuration](https://genie-data-support-1347244451.oss-cn-shanghai.aliyuncs.com/gdk_api_docs/2.6.3/config.json), HTTP 200, containing the complete `docs_paths.zhCn` navigation tree.
- Normal fetches of all 43 Markdown bodies under the same `/gdk_api_docs/2.6.3/docs/` prefix, HTTP 200; these returned actual prose, tables, source code and warnings. Their hashes/local paths are recorded separately in `gdk_page_index.csv`.
- Global version configuration is a list of releases, not an API changelog. The observed 2.6.3 config contains only `zhCn`. No additional UI language tree, hidden interface tabs, release-notes entry or linked Markdown page beyond the 43 indexed pages was discovered.

The frontend eagerly fetches every configured page during ordinary navigation. The collector saved these **already issued** responses sequentially using read-only `Network.getResponseBody`; it did not create concurrent crawling requests. The app itself generated the eager network traffic. For subsequent offline reuse, `.cache/gdk/browser_capture.json` retains only origin-relevant resource URL/status/sequence/hash/size/timestamp; it contains no Cookie, Authorization, account data, unrelated extension/third-party traffic or robot control requests. Full documents/config remain under gitignored `.cache/gdk/`, with source directory paths preserved.

## Cross-version control

Using the actual visible selector, the page was switched to **2.4.2** and then restored to **2.6.3**. A significant UI pitfall was observed: after selecting 2.4.2, the query string still said `gdk_version=2.6.3`, while the visible menu and fetched config/body paths correctly changed to 2.4.2. The requested URL alone is therefore insufficient version evidence.

Both versions share identical homepage text, so homepage hash equality alone is inconclusive. The C++ Robot sample is different: 2.4.2 body **72,023 bytes**, SHA-256 `59d13a904d22f053d33bc288ac89d30319e42ea907c53936f55ec69741bb45e7`; 2.6.3 body **125,234 bytes**, with its independently recorded hash in the index. Thus navigation did not simply serve the same homepage under every hash/version. `.cache/gdk/version_comparison.json` and the old-version samples preserve this control; they are not implementation evidence for 2.6.3.

## Coverage and reading status

| Observed scope | Count |
|---|---:|
| Total pages in complete specified-version directory | 43 |
| Acquired real bodies | 43 |
| READ_COMPLETE using actual combined conversation review | 43 |
| BLOCKED | 0 |
| VERSION_MISMATCH among selected-version bodies | 0 |

Breakdown: home 1; quick start 4; concepts 2; how-to 5; tools 2; Python 12; C++ 11; ROS2 5; appendix 1. All three document hash links point to indexed quick-start language pages; no image-only body needed transcription. A full directory was actually obtained, so this denominator is known for the observed configuration, not a claim about unpublished vendor materials.

The 28 API pages were already read fully in this same conversation (main agent: Python; read-only agents: C++ and ROS2). This task retained their authored per-page notes, captured current raw evidence, checked method lists/key fields/warnings, re-read several interfaces, and fully read the 15 previously uncovered pages. `gdk_reading_notes.md` records this provenance rather than inventing a new full-body hash for an earlier read. Complete combined reading does not establish SDK declarations or device semantics.

## Acquisition tooling and limits

- `python3 scripts/gdk_docs.py fetch`: fetches the observed public version config and configured raw paths, reusing cache by default. A successful new download is only FETCHED. Existing READ_COMPLETE survives only when its body hash is unchanged.
- `python3 scripts/gdk_docs.py fetch --offline`: requires cache and does no network access.
- `python3 scripts/gdk_docs.py fetch --refresh`: bounded sequential HTTP refresh; changed bodies invalidate reading state until a reviewer revisits them.
- `python3 scripts/gdk_docs.py read PAGE --start N --lines N`: displays bounded complete-source chunks without changing reading status.
- `python3 scripts/gdk_docs.py audit`: reports coverage, source integrity, review attestations and independently unresolved API/SDK gaps. It explicitly does not certify semantic correctness from file size or nonempty notes.

Fetcher uses 20 s requests, at most one retry for transient failures, a short inter-request interval and no credentials. It refuses empty/HTML-shell bodies and unexpected origin redirects. Access restrictions are recorded rather than bypassed. Fetch/review/audit are independent of build/test/verify, so a temporary website failure cannot block mock validation.

Actual local validation: `make read-gdk`, `make audit-gdk`, `python3 -m py_compile scripts/gdk_*.py`, and a bounded `gdk_docs.py read` returned exit 0. Isolated temporary-copy checks confirmed that changing one raw-body hash reduces READ_COMPLETE from 43 to 42, and fetching into a new index marks all 43 bodies FETCHED rather than read. The original evidence was not altered. Logs: gitignored `.cache/gdk/script_validation.json`. These checks validate evidence tooling, not SDK correctness.

## SDK and supplementary material

[Deployment](https://support.agibot.com/?gdk_version=2.6.3#contents/howto/deploy.md) provides robot-local installer/example paths. They were not contacted. No robot address was configured, no scanner was run, no connection button/example/control endpoint was invoked, and no SDK or arbitrary executable was installed.

[Official G2 user manual](https://www.agibot.com/filepage/296.html), section 14, describes Developer Tools' offline local SDK documentation and online latest documentation. Its app-specific connection guide mentions robot connection, authorization and an insecure browser mode. Those actions were not followed. The manual is not the GDK 2.6.3 API source, and that guide does not override the direct observation that this public support site's 43 versioned documents were readable without connecting a robot or weakening browser security.

A focused official-domain/GitHub search for AGIBOT GDK 2.6.3 downloads and release notes did not identify a matching public SDK artifact or a same-version official source repository. Unrelated GTK/GDK results were rejected. This is “not found in this search,” not proof no privately supplied package exists. No third-party code was copied. The vendor C++ guide and examples were used only as references; ABI, package architecture, firmware compatibility, licensing and hard safety semantics require real materials. The user-selected Ubuntu 22.04.5 ARM64 VM does not change those unverified SDK states.

Capabilities used for this document track: CUA Chrome + documented CDP read-only network/body capture; local Python standard library for hashing, CSV/JSON and bounded public HTTP; `rg`/file reads for scope/signature comparison; web read/search for the manual and official-source lookup. No additional skill or plugin was needed beyond those installed capabilities.
