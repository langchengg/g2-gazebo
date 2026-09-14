#!/usr/bin/env python3
"""Stable entry point: fetch (acquire only), audit (traceability), read (bounded body)."""
import runpy
import sys
from pathlib import Path

commands = {"fetch": "gdk_fetch.py", "audit": "gdk_audit.py", "read": "gdk_review.py"}
if len(sys.argv) < 2 or sys.argv[1] not in commands:
    print("usage: gdk_docs.py {fetch [--offline|--refresh] | audit | read PAGE [--start N --lines N]}", file=sys.stderr)
    sys.exit(2)
command = commands[sys.argv.pop(1)]
runpy.run_path(str(Path(__file__).with_name(command)), run_name="__main__")
