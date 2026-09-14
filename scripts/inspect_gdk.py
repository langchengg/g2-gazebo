#!/usr/bin/env python3
"""Inspect local SDK evidence without installation, native import or connection."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "agibot_g2_demo"))
from agibot_g2_demo.backends.gdk_backend import GdkUnavailable, inspect_elf, preflight_gdk


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--config", help="project read-only JSON config; inspection does NOT connect")
    group.add_argument("--elf", type=Path, help="inspect an already supplied ELF header only")
    args = parser.parse_args()
    try:
        result = (inspect_elf(args.elf) if args.elf else preflight_gdk(args.config))
    except (GdkUnavailable, OSError, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc),
                          "sdk_loaded": False, "robot_connected": False}, indent=2))
        return 2
    print(json.dumps({"status": "LOCAL_METADATA_CHECKED", "evidence": result,
                      "sdk_loaded": False, "robot_connected": False,
                      "real_sdk_validation": "NOT RUN"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
