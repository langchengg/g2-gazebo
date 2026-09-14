#!/usr/bin/env python3
"""Resume public GDK documentation acquisition; fetching never asserts reading."""
import argparse
import csv
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "2.6.3"
# Observed in normal browser Network.responseReceived on 2026-09-08.
ORIGIN = "https://genie-data-support-1347244451.oss-cn-shanghai.aliyuncs.com/gdk_api_docs/"
CONFIG_URL = ORIGIN + VERSION + "/config.json"
FIELDS = ["page_id", "title", "language", "navigation_path", "url", "resource_url",
          "requested_version", "observed_version_evidence", "fetched_at", "body_sha256",
          "cache_path", "reading_status", "failure_reason"]

def now():
    return datetime.now(timezone.utc).isoformat()

def digest(data):
    return hashlib.sha256(data).hexdigest()

def pages(nodes, prefix="", navigation=()):
    for node in nodes:
        name = str(node["name"])
        if name.startswith("/") or ".." in Path(name).parts:
            raise ValueError("Unsafe path in public configuration")
        path = prefix + name
        nav = navigation + (node["title"],)
        if node["type"] == "folder":
            yield from pages(node.get("children", []), path + "/", nav)
        elif node["type"] == "md":
            yield path, node["title"], nav

def fetch(url, target, refresh=False, offline=False):
    if target.exists() and not refresh:
        return target.read_bytes(), False
    if offline:
        raise RuntimeError("Cache missing in offline mode")
    # No credentials, cookies, browser profiles, headers or robot endpoints.
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GDK-documentation-review/1.0"})
            with urllib.request.urlopen(req, timeout=20) as response:
                final = response.geturl()
                if not final.startswith(ORIGIN):
                    raise RuntimeError("Unexpected redirect outside observed public documentation origin")
                data = response.read(8 * 1024 * 1024 + 1)
                if len(data) > 8 * 1024 * 1024:
                    raise RuntimeError("Document exceeds bounded download size")
            if not data.strip() or b"<!doctype html" in data[:200].lower():
                raise RuntimeError("Empty response or HTML shell, not document body")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            time.sleep(0.25)
            return data, True
        except urllib.error.HTTPError as error:
            if error.code in (401, 403, 429):
                raise RuntimeError("Access restricted HTTP %s; no bypass attempted" % error.code) from error
            if attempt:
                raise
        except (OSError, TimeoutError):
            if attempt:
                raise
        time.sleep(1)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    index = ROOT / "docs/gdk_page_index.csv"
    old = {}
    if index.exists():
        with index.open(newline="") as stream:
            old = {r["page_id"]: r for r in csv.DictReader(stream)}
    config_path = ROOT / ".cache/gdk" / VERSION / "config.json"
    try:
        raw, _ = fetch(CONFIG_URL, config_path, args.refresh, args.offline)
        config = json.loads(raw)
        if set(config["docs_paths"]) != {"zhCn"}:
            raise RuntimeError("Language catalog changed: manual browser discovery is required")
    except Exception as error:
        print("BLOCKED: directory retrieval: %s; total pages unknown unless prior index exists" % error, file=sys.stderr)
        return 2
    capture_file = ROOT / ".cache/gdk/browser_capture.json"
    capture = {}
    if capture_file.exists():
        capture = {r["cache_path"]: r for r in json.loads(capture_file.read_text())["records"]}
    rows, failed = [], 0
    last_progress = time.monotonic()
    stop_reason = None
    for path, title, nav in pages(config["docs_paths"]["zhCn"]):
        language = "Python" if "/Python/" in path or path.endswith("/python.md") else "C++" if "/cpp/" in path or path.endswith("/cpp.md") else "ROS2" if "/ROS2/" in path or path.endswith("/ros2.md") else "General"
        resource = ORIGIN + VERSION + "/docs/" + path
        cache_path = ".cache/gdk/" + VERSION + "/docs/" + path
        previous = old.get(path, {})
        row = dict(zip(FIELDS, [path, title, language, " > ".join(nav),
            "https://support.agibot.com/?gdk_version=" + VERSION + "#" + path,
            resource, VERSION, "Version-scoped official config and resource; browser evidence in gdk_access_report.md",
            "", "", cache_path, "DISCOVERED", ""]))
        try:
            if stop_reason:
                raise RuntimeError(stop_reason)
            if time.monotonic() - last_progress >= 600:
                stop_reason = "No new valid document for 10 minutes; acquisition paused; mock work is independent"
                raise RuntimeError(stop_reason)
            data, downloaded = fetch(resource, ROOT / cache_path, args.refresh, args.offline)
            sha = digest(data)
            last_progress = time.monotonic()
            row["body_sha256"] = sha
            row["fetched_at"] = now() if downloaded else capture.get(cache_path, {}).get("captured_at", previous.get("fetched_at", "CACHE_TIME_UNVERIFIED"))
            # Only unchanged evidence may retain the independently recorded reading state.
            row["reading_status"] = "READ_COMPLETE" if previous.get("body_sha256") == sha and previous.get("reading_status") == "READ_COMPLETE" else "FETCHED"
        except Exception as error:
            row["reading_status"] = "BLOCKED"
            row["failure_reason"] = str(error)
            if "Access restricted HTTP" in str(error):
                stop_reason = str(error) + "; remaining requests not attempted"
            failed += 1
        rows.append(row)
    index.parent.mkdir(parents=True, exist_ok=True)
    with index.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, FIELDS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"discovered": len(rows), "fetched": len(rows)-failed,
        "read_complete": sum(r["reading_status"] == "READ_COMPLETE" for r in rows), "blocked": failed,
        "notice": "Downloading does not constitute reading. Review bodies and update notes/inventory independently."}))
    return 2 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
