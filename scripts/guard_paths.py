#!/usr/bin/env python3
"""Claude Code PreToolUse hook: the isolation/sensor plane.

Reads the hook event JSON on stdin. Exit 0 = allow, exit 2 = block
(stderr is shown to the agent so it knows why).

Rules:
  1. Never write to forbidden paths (.env*, lockfiles, .git/, .githooks/, receipts).
  2. If a contract is active (.claude/contracts/ACTIVE holds a task id),
     writes must match that contract's allowed_paths globs.
  3. Block dangerous shell commands (skipping hooks, reading secrets, rm -rf /).
"""
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path(__file__).resolve().parent.parent))

FORBIDDEN = [
    ".env", ".env.*", "*.lock", "package-lock.json", "poetry.lock",
    ".git/*", ".githooks/*", ".claude/receipts/*", ".claude/settings.json",
]

BAD_COMMANDS = [
    (r"--no-verify", "skipping git hooks is not allowed"),
    (r"\bgit\s+push\b.*\b(main|master)\b", "pushing to main is not allowed"),
    (r"(cat|less|head|tail|grep)\s+[^|;]*\.env\b", "reading secrets (.env) is not allowed"),
    (r"\brm\s+-rf\s+/(\s|$)", "rm -rf / is not allowed"),
    (r"\bcurl\b.*\|\s*(sh|bash)", "piping downloads into a shell is not allowed"),
]


def block(reason: str) -> None:
    print(f"BLOCKED by guard_paths: {reason}", file=sys.stderr)
    sys.exit(2)


def active_contract() -> dict | None:
    marker = ROOT / ".claude/contracts/ACTIVE"
    if not marker.exists():
        return None
    task_id = marker.read_text().strip()
    path = ROOT / f".claude/contracts/{task_id}.json"
    if not path.exists():
        block(f"ACTIVE points to missing contract {path.name}")
    return json.loads(path.read_text())


def rel(path_str: str) -> str:
    p = Path(path_str)
    if p.is_absolute():
        try:
            p = p.resolve().relative_to(ROOT.resolve())
        except ValueError:
            block(f"{path_str} is outside the repository")
    return p.as_posix()


def check_write(path_str: str) -> None:
    path = rel(path_str)
    for pattern in FORBIDDEN:
        if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(Path(path).name, pattern):
            block(f"{path} matches forbidden pattern {pattern}")
    contract = active_contract()
    if contract and not any(fnmatch.fnmatch(path, g) for g in contract["allowed_paths"]):
        block(f"{path} is not in contract {contract['task_id']} allowed_paths {contract['allowed_paths']}")


def check_command(cmd: str) -> None:
    for pattern, reason in BAD_COMMANDS:
        if re.search(pattern, cmd):
            block(reason)


def main() -> None:
    event = json.load(sys.stdin)
    tool = event.get("tool_name", "")
    args = event.get("tool_input", {})
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        check_write(args.get("file_path") or args.get("notebook_path", ""))
    elif tool == "Bash":
        check_command(args.get("command", ""))
    sys.exit(0)


if __name__ == "__main__":
    main()
