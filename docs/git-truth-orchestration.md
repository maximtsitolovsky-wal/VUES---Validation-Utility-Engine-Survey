# Git Truth Orchestration

This document defines the anti-fib workflow for repo changes.
If an agent says work is complete, this process decides whether that statement deserves to live.

> Status and roadmap still belong in [`development.md`](../development.md).

## Goal

Make completion claims auditable.
A coding task is only complete when both code quality and git publication are verified.

## Roles

| Role | Responsibility |
|---|---|
| Planner | Define scope, target files, branch, remote, and acceptance criteria |
| Worker | Make the smallest viable change |
| Reviewer | Verify code quality, scope, and architectural fit |
| Git Truth Guard | Verify commit + push with receipts |
| Orchestrator | Enforce ordering and reject incomplete evidence |

## Flawless Orchestration Contract

1. **Plan first**
   - Name the target branch.
   - Name the authoritative remote.
   - List the exact files expected to change.

2. **Implement second**
   - Make the smallest reasonable change.
   - Avoid unrelated file churn.

3. **Review third**
   - Confirm the code matches scope.
   - Confirm architecture and repo rules are respected.

4. **Commit fourth**
   - Stage only intended files.
   - Review staged diff.
   - Create a focused commit.

5. **Push fifth**
   - Push to the authoritative remote.
   - Capture command output.

6. **Verify sixth**
   - Run `python tools/git_truth_guard.py --remote walmart-origin --strict`
   - Record branch, local SHA, remote SHA, ahead/behind counts, and dirty state.

7. **Only then close the task**
   - The orchestrator must reject any report missing git proof.

## Minimum Receipt Bundle

Every completed task should surface this bundle:

```text
git status --short --branch
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
git remote -v
git push <remote> <branch>
python tools/git_truth_guard.py --remote <remote> --strict
```

If any line is missing, the report is incomplete.

## Bottlenecks in the Overall Process

### 1. Single-point trust in agent narration
If one worker both implements and self-certifies, you get theater instead of verification.
**Fix:** Separate worker completion from Git Truth Guard verification.

### 2. Ambiguous authoritative remote
This repo has both `origin` and `walmart-origin`.
A push to the wrong remote can still sound successful.
**Fix:** Planner must name the authoritative remote up front.

### 3. Dirty repo state before the task starts
Unrelated modified files make it easy to accidentally stage junk or misreport scope.
**Fix:** Record baseline `git status --short --branch` before changes and keep commits scoped.

### 4. "Push succeeded" is weaker than remote verification
Network/proxy weirdness, branch mismatch, or remote confusion can leave local and remote SHAs different.
**Fix:** Verify post-push SHA equality, not just command success.

### 5. Missing machine-readable receipts
Human summaries are easy to embellish.
**Fix:** Use `tools/git_truth_guard.py --format json` when another orchestrator or report consumer needs proof.

### 6. Overloaded orchestrator role
If the orchestrator plans, reviews, verifies, and summarizes, it becomes a bottleneck and a bias source.
**Fix:** Keep roles narrow. Planner plans. Reviewer reviews. Git Truth Guard verifies publication.

### 7. Unclear completion criteria
Without explicit acceptance criteria, agents will declare victory after code compiles.
**Fix:** Define done as: code changed, tests/sanity checks passed, commit created, push verified.

## Recommended Operating Pattern

Use this short checklist for every non-trivial coding task:

- [ ] Scope named
- [ ] Files listed
- [ ] Review performed
- [ ] Commit created
- [ ] Push executed to named remote
- [ ] Push receipt verified
- [ ] Final report includes SHA + remote

## Example Final Report

```text
Status: VERIFIED
Remote: walmart-origin
Branch: main
Commit: 0123abcd4567ef...
Push receipt: local HEAD matches remote HEAD
Dirty worktree after push: false
```

If the status is not `VERIFIED`, the task is not done. Shocking, I know.
