#!/usr/bin/env python3
"""Display bounded raw document chunks; this does not mark a page READ_COMPLETE."""
import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("page_id")
parser.add_argument("--start", type=int, default=1)
parser.add_argument("--lines", type=int, default=200)
args = parser.parse_args()
base = (ROOT / ".cache/gdk/2.6.3/docs").resolve()
path = (base / args.page_id).resolve()
if not path.is_relative_to(base) or args.start < 1 or not 1 <= args.lines <= 500:
    parser.error("Invalid path or chunk bounds")
data = path.read_bytes()
lines = data.decode().splitlines()
end = min(len(lines), args.start - 1 + args.lines)
print("page=%s sha256=%s lines=%s-%s/%s" % (args.page_id, hashlib.sha256(data).hexdigest(), args.start, end, len(lines)))
for i in range(args.start - 1, end):
    print("%d: %s" % (i + 1, lines[i]))
print("READING STATUS UNCHANGED. Record actual review, API inventory, constraints and unresolved questions.")
