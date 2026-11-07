#!/bin/sh
# Isolation plane: give each agent task its own branch + worktree.
# Usage: scripts/new_task.sh TASK-001
set -eu
TASK_ID="$1"
ROOT="$(git rev-parse --show-toplevel)"
CONTRACT="$ROOT/.claude/contracts/$TASK_ID.json"

[ -f "$CONTRACT" ] || { echo "No contract at $CONTRACT. No contract, zero code written." >&2; exit 1; }

git -C "$ROOT" worktree add -b "agent/$TASK_ID" "$ROOT/.agent_worktrees/$TASK_ID"
echo "$TASK_ID" > "$ROOT/.agent_worktrees/$TASK_ID/.claude/contracts/ACTIVE"
git -C "$ROOT/.agent_worktrees/$TASK_ID" config core.hooksPath .githooks
echo "Worktree ready: .agent_worktrees/$TASK_ID (contract $TASK_ID active)"
echo "Start Claude Code there:  cd .agent_worktrees/$TASK_ID && claude"
