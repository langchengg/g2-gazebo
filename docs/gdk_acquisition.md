# GDK 2.6.3 acquisition: actual attempts and remaining dependency

UTC date: 2026-09-08. Result: **BLOCKED — zero SDK files/images obtained**.
No installer, payload, wheel, deb or official SDK image was downloaded. SDK size,
SHA-256/digest, internal product version, license, architecture and ABI are
therefore **unavailable**, not zero-valued successful package metadata.
[Machine-readable manifest](gdk_sdk_manifest.json) deliberately has an empty
`artifacts` array. A self-computed hash would only establish local consistency,
not vendor identity.

## Actual official acquisition method

The already cached [2.6.3 deployment page](https://support.agibot.com/?gdk_version=2.6.3#contents/howto/deploy.md),
[mixed deployment](https://support.agibot.com/?gdk_version=2.6.3#contents/concepts/hybrid_deploy.md),
[Python quick start](https://support.agibot.com/?gdk_version=2.6.3#contents/getting-started/quick-start/python.md)
and [Python usage](https://support.agibot.com/?gdk_version=2.6.3#contents/howto/python.md)
were reread in full in this continuation. Their local paths are under
`.cache/gdk/2.6.3/docs/`; existing index hashes preserve the versioned body evidence.
The 43-page directory was not downloaded or reread wholesale.

The deployment instructions require the G2 Debug Ethernet connection and fetch
`http://10.42.1.101:8849/install.sh`; `install_example.sh` retrieves examples from
the G2. These are the actual documented addresses, not a guessed repository or
package name. They are **acquisition evidence only**, not hard-coded hardware
configuration in the application. The URLs themselves are unversioned: even a
successful installer download would not establish that its payload is 2.6.3.
The installer could not be obtained, so its payload URLs, version selector,
download-only options, installation side effects and license remain unknown.
No installer was piped to a shell or executed.

| Execution location | UTC attempt start | Resource | curl exit | HTTP response | Bytes |
|---|---|---|---|---|---|
| Mac | 22:40:28 | install.sh | 28 | None; connect timeout | 0 |
| Mac | 22:40:32 | install_example.sh | 28 | None; connect timeout | 0 |
| Ubuntu VM `lang`, aarch64 | 22:49:47 | install.sh | 28 | None; connect timeout | 0 |
| Ubuntu VM `lang`, aarch64 | 22:49:51 | install_example.sh | 28 | None; connect timeout | 0 |

The requests used a 4-second connection deadline, 12-second transfer deadline,
TLS verification where applicable, HTTP failure handling and output-to-file.
They were GET requests to documented installer resources only. No robot control,
scan, network change, login bypass or script execution occurred. The documented
resource uses HTTP; no TLS identity or signed checksum was obtained.

Private evidence locations (logs only; **not SDK package paths**):

- Mac: `/Users/delaynomore/Downloads/test/.artifacts/gdk/2.6.3/acquisition/`
- VM: `/home/lang/projects/agibot-g2-ros2/.artifacts/gdk/2.6.3/acquisition/`
- Files: `mac-attempts.json` (Mac), `vm-attempts.json` (VM and copied to Mac).

The current reproducible `make sdk-fetch` implementation was also run separately.
It fetches only those two documented scripts, preserves HTTP/transport failures,
rejects HTML/error bodies, checks bounded complete transfer, and reuses only a
hash-matching local installer receipt. It never executes the result. A fetched
script is labelled `INSTALLER_FETCHED_REVIEW_REQUIRED`, never SDK success.
It does not guess a package format, mirror, PyPI name or downstream URL.

## Alternative routes actually checked

See [bounded official-channel research](gdk_acquisition_research.md) for source
links and exclusions. Official website/document center, the linked official
AgibotTech organization's 21 public repositories, Packages/Artifacts, Genie
Studio, CoRobot and AIMA pages produced no confirmed G2 GDK 2.6.3 artifact in
this search scope. Related local Downloads files contain task/exporter material,
not the SDK. AimDK/X2, Genie Sim, third-party examples and older manual PDFs were
excluded. A later ordinary HTTPS GET of the official CoRobot announcement page
succeeded (HTTP 200, 22,421 bytes); its content only announces future GDK access
and contains no versioned SDK download. That HTML is not an SDK artifact. This does **not** prove that a private or unlisted vendor release does
not exist. No account was guessed and no external message was sent.

## Platform and stage boundary

The deployment page specifies an x86_64 developer machine; the Python binding
build page also mentions Linux aarch64, Python 3.10 by default and shipped pybind
source. These statements do not establish the architecture of a missing package.
Do not label the SDK x86-only or ARM-compatible. Product 2.6.3, installer version,
Python distribution version, wheel tags and ROS Python ABI require separate
verification. The project now rejects the previous package-version equality
assumption with `VERSION_MAPPING_UNVERIFIED`.

S0 acquisition/static package validation is BLOCKED. S1 real installation/import
and S2 real symbol/type checks are NOT RUN. S3 no-device initialization is NOT RUN:
no verified no-device contract exists. S4 read-only hardware and S5 motion are
NOT RUN. Project-owned field/validation fixtures are software tests, not S2.

`make sdk-inspect`, `make build-gdk` and `make sdk-smoke` currently return exit 2
with explicit missing-payload stage evidence. They are honest gates, **not
implemented installer or successful smoke commands**. Static inspection of a
separately supplied artifact is available as:

```bash
python3 scripts/sdk_tools.py inspect --file /path/to/actual/artifact --sha256 EXPECTED_HASH
```

This lists safe archive entries without extraction and rejects partial/error
files, malformed archives, unsafe paths/links and checksum mismatches. It does
not authenticate a supplied hash or validate the product by filename.

The minimum external input is a normally authorized official GDK **2.6.3**
download portal/link or an authorized vendor release package with version and
license evidence. This was requested once while software work continued. No
change to VM NAT, security policy, system Python or mock platform is needed.
