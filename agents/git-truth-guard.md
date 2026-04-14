# Agent: git-truth-guard
**Category:** Session Role + CLI Tool  
**Type:** Prompt-defined verification persona + Python CLI tool  
**Prompt Source:** `prompts/git_truth_guard_prompt.md`  
**CLI Tool:** `tools/git_truth_guard.py`  
**LLM Agent:** ❌ No — pure git shell commands, no LLM

---

## What It Is
The Git Truth Guard prevents false completion claims in dev sessions.
"I pushed it" is not evidence. A SHA is.

It exists at two levels:
1. **Session persona** — Code Puppy adopts this role to verify every completion claim
   that involves code changes (guided by `prompts/git_truth_guard_prompt.md`)
2. **CLI tool** — `tools/git_truth_guard.py --strict` runs the verification pipeline
   automatically and returns a JSON verdict

## The Core Rule
A task involving code changes is **NOT complete** until git evidence proves:
1. The intended files were committed
2. The commit exists on the agreed remote
3. The orchestration report contains the exact commit SHA and remote

## Evidence Required for Every Completion Report
```
git status --short --branch
git rev-parse HEAD
git rev-parse --abbrev-ref HEAD
git remote -v
[push command output]
tools/git_truth_guard.py --strict
```

## What Gets Rejected
| Claim | Why It Gets Rejected |
|---|---|
| "I pushed it" | No SHA |
| "committed" | `git diff --staged` was never reviewed |
| "done" | Authoritative remote not named |
| "done" | local HEAD ≠ remote branch HEAD |
| "done" | Commit exists only on non-authoritative remote |

## Verification Output (JSON)
```json
{
  "status": "VERIFIED | UNVERIFIED | REJECTED",
  "summary": "one line",
  "branch": "main",
  "remote": "walmart-origin",
  "local_head": "sha",
  "remote_head": "sha",
  "ahead": 0,
  "behind": 0,
  "dirty_worktree": false,
  "issues": [],
  "required_next_steps": []
}
```

## Orchestration Contract (enforced by this agent)
Steps must happen in this order. No skipping:
1. **Planner** defines target files, branch, authoritative remote
2. **Generator** implements the change
3. **Reviewer** checks code quality and scope
4. **Git Truth Guard** verifies commit + push receipts ← this agent
5. Only then may the orchestrator mark the task complete

## Project-Specific Notes
- Prefer `walmart-origin` as the authoritative remote in this repo
- Never force-push
- Evidence beats eloquence — a lying agent can write poetry; a SHA cannot

## CLI Usage
```bash
python tools/git_truth_guard.py
python tools/git_truth_guard.py --strict   # fails with exit code 1 if unverified
```
