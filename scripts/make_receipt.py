#!/usr/bin/env python3
"""Verification + gate plane: run the contract's acceptance commands and,
only if they all pass, write .claude/receipts/receipt-<task_id>.json.

Usage: python3 scripts/make_receipt.py TASK-001

The receipt records every changed file with its sha256, the test output,
and STATUS. The pre-commit hook refuses commits whose staged files don't
match an APPROVED receipt.
"""
import datetime
import fnmatch
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def changed_files() -> list[str]:
    out = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    files = [line[3:].strip() for line in out.splitlines() if line.strip()]
    return sorted(f for f in files if not f.startswith(".claude/receipts/") and (ROOT / f).is_file())


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    task_id = sys.argv[1]
    contract = json.loads((ROOT / f".claude/contracts/{task_id}.json").read_text())

    files = changed_files()
    outside = [f for f in files if not any(fnmatch.fnmatch(f, g) for g in contract["allowed_paths"])]

    results = []
    for cmd in contract["acceptance_commands"]:
        proc = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True,
                              timeout=contract["budget"]["timeout_seconds"])
        results.append({"command": cmd, "exit_code": proc.returncode,
                        "output_tail": (proc.stdout + proc.stderr)[-1500:]})

    passed = all(r["exit_code"] == 0 for r in results) and not outside
    receipt = {
        "task_id": task_id,
        "status": "APPROVED" if passed else "REJECTED",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "files": {f: sha256(ROOT / f) for f in files},
        "files_outside_contract": outside,
        "acceptance": results,
    }
    out = ROOT / f".claude/receipts/receipt-{task_id}.json"
    out.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"{receipt['status']}: wrote {out.relative_to(ROOT)}")
    if outside:
        print(f"  files outside contract: {outside}")
    for r in results:
        print(f"  [{r['exit_code']}] {r['command']}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
