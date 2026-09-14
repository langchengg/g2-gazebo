#!/usr/bin/env python3
"""Check traceability and explicitly report semantic/API gaps; never certify hardware."""
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    index = ROOT / "docs/gdk_page_index.csv"
    if not index.exists():
        print("BLOCKED: no index; total pages unknown")
        return 2
    with index.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    notes_path = ROOT / "docs/gdk_reading_notes.md"
    notes = notes_path.read_text() if notes_path.exists() else ""
    issues = []
    if len({r["page_id"] for r in rows}) != len(rows):
        issues.append("Duplicate page IDs")
    config = ROOT / ".cache/gdk/2.6.3/config.json"
    if config.exists():
        from gdk_fetch import pages
        configured = {p for p, _, _ in pages(json.loads(config.read_text())["docs_paths"]["zhCn"])}
        if configured != {r["page_id"] for r in rows}:
            issues.append("Index does not match the actual version configuration")
    for row in rows:
        path = ROOT / row["cache_path"]
        if not path.exists():
            issues.append(row["page_id"] + ": raw local evidence missing; run make read-gdk")
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["body_sha256"]:
            issues.append(row["page_id"] + ": hash changed; review invalidated")
        if row["reading_status"] == "READ_COMPLETE" and (row["page_id"] not in notes or row["body_sha256"] not in notes):
            issues.append(row["page_id"] + ": missing page/hash review attestation")
    inventory_path = ROOT / "docs/gdk_api_inventory.csv"
    inventory = []
    if inventory_path.exists():
        with inventory_path.open(newline="") as stream:
            inventory = list(csv.DictReader(stream))
    if not inventory:
        issues.append("No independently reviewed API inventory")
    inventory_symbols = {(r["page_id"], r["symbol"]) for r in inventory}
    for row in rows:
        path = ROOT / row["cache_path"]
        if path.exists():
            for symbol in re.findall(r"^#{3,4} \d+\. `([\w]+)\(", path.read_text(), re.M):
                if (row["page_id"], symbol) not in inventory_symbols:
                    issues.append(row["page_id"] + ": API heading missing from inventory: " + symbol)
        if row["requested_version"] != "2.6.3" or "/gdk_api_docs/2.6.3/docs/" not in row["resource_url"]:
            issues.append(row["page_id"] + ": version evidence mismatch")
    counts = Counter(r["reading_status"] for r in rows)
    print(json.dumps({"discovered": len(rows), "fetched": sum(bool(r["body_sha256"]) for r in rows),
        "read_complete": counts["READ_COMPLETE"], "blocked": counts["BLOCKED"],
        "version_mismatch": counts["VERSION_MISMATCH"], "inventory_entries": len(inventory),
        "primary_documented_methods": sum(r.get("kind") == "method" for r in inventory),
        "sdk_unverified_entries": sum("UNVERIFIED" in r["verification_status"] for r in inventory),
        "evidence_integrity_issues": issues, "sdk_checked": False,
        "gdk_compiled": False, "read_only_hardware_tested": False, "motion_tested": False}, indent=2))
    print("This audit checks traceability, not semantic correctness. Review the per-page notes and field-level mapping.")
    print("OPEN GAPS: SDK headers/library/ABI, source clock/freshness, control completion, stop semantics, hardware authorization.")
    return 2 if issues or counts["READ_COMPLETE"] != len(rows) else 0

if __name__ == "__main__":
    sys.exit(main())
