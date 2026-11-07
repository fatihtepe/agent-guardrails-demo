# agent-guardrails-demo

Guardrails and CI/CD gates around an AI coding agent (Claude Code), built with plain Python, git hooks and GitHub Actions. The agent can only change what a task contract allows. It cannot touch secrets. It cannot commit unless real tests pass and a receipt proves exactly which files were approved.

## The four planes

| Plane | What enforces it | File |
|---|---|---|
| **Contract** | Each task declares allowed paths, budget and acceptance commands before any code is written | `.claude/contracts/TASK-001.json` |
| **Isolation** | One git worktree and branch per task. A PreToolUse hook blocks writes outside the contract, to secrets, lockfiles, hooks or receipts, plus dangerous shell commands | `scripts/new_task.sh`, `scripts/guard_paths.py`, `.claude/settings.json` |
| **Verification** | Acceptance commands run for real. The receipt stores every changed file's sha256 and the test output | `scripts/make_receipt.py` |
| **Gate** | The pre-commit hook rejects staged files that aren't in an APPROVED receipt, or that changed after approval. CI re-checks on pull requests | `.githooks/pre-commit`, `scripts/verify_receipt.py`, `.github/workflows/ci.yml` |

## Try it

```sh
git config core.hooksPath .githooks        # enable the commit gate
python3 -m unittest discover -s tests -t . -v   # app tests + proof each barrier trips

scripts/new_task.sh TASK-001               # isolated worktree with the contract active
cd .agent_worktrees/TASK-001 && claude     # let the agent work inside the guardrails
python3 scripts/make_receipt.py TASK-001   # run acceptance tests -> receipt
git add -A && git commit -m "TASK-001"     # passes only with an APPROVED receipt
```

## What it proves (dry runs)

- Writing `.env`, a lockfile, a receipt or `/etc/hosts` → blocked (exit 2)
- Editing `README.md` while TASK-001 only allows `app/` + `tests/` → blocked
- `git commit --no-verify`, `cat .env`, `git push origin main`, `curl … | sh` → blocked
- Committing a file with no receipt, or editing it after approval → commit refused

## Honest limits

- Hooks guard Claude Code's tools; a human with shell access can still bypass them. CI is the backstop.
- The receipt is a sha256 record, not a cryptographic signature. Signing (e.g. Sigstore/cosign) is a natural next step.
- Budget fields (turns, $) are declared in the contract but not enforced by code here.
