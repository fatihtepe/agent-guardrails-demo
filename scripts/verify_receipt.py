#!/usr/bin/env python3
"""Pre-commit gate: every staged file must appear in an APPROVED receipt
with a matching sha256 of the staged content. No receipt, no commit.

Files exempt from the gate: receipts themselves and anything listed in
EXEMPT (the harness's own bootstrap files, committed by a human).
"""
import fnmatch
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXEMPT = [".claude/receipts/*"]


def staged_files() -> list[str]:
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [f for f in out.splitlines() if f]


def staged_sha(path: str) -> str:
    blob = subprocess.run(["git", "show", f":{path}"], cwd=ROOT, capture_output=True, check=True).stdout
    return hashlib.sha256(blob).hexdigest()


def approved_hashes() -> dict[str, str]:
    hashes = {}
    for receipt in (ROOT / ".claude/receipts").glob("receipt-*.json"):
        data = json.loads(receipt.read_text())
        if data.get("status") == "APPROVED":
            hashes.update(data["files"])
    return hashes


def main() -> int:
    if os.environ.get("HARNESS_BOOTSTRAP") == "1":
        print("pre-commit: HARNESS_BOOTSTRAP=1, gate skipped (human bootstrap commit only)")
        return 0
    approved = approved_hashes()
    failures = []
    for f in staged_files():
        if any(fnmatch.fnmatch(f, p) for p in EXEMPT):
            continue
        if f not in approved:
            failures.append(f"{f}: no APPROVED receipt covers this file")
        elif approved[f] != staged_sha(f):
            failures.append(f"{f}: staged content differs from the approved receipt (changed after approval)")
    if failures:
        print("pre-commit BLOCKED: no receipt, no commit", file=sys.stderr)
        for line in failures:
            print(f"  - {line}", file=sys.stderr)
        print("Run: python3 scripts/make_receipt.py <TASK_ID>", file=sys.stderr)
        return 1
    print("pre-commit: all staged files covered by an APPROVED receipt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
