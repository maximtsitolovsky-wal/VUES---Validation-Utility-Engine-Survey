# SKILL: Git Truth Guard
**Last Used:** 2026-04-13
**Times Used:** 1

## Trigger
User asks for: "make sure it actually got pushed", "verify git", "prove the other agent posted to git",
"don't let the agent lie", "show me receipts", "verify remote has the commit".

## Context — Read First
- Read `development.md` for repo workflow expectations.
- Read `MEMORY.md` for staging/commit discipline decisions.
- Check `git status --short --branch` before doing anything.
- Never trust an agent claim like "pushed" without a receipt.

## Steps

1. **Capture baseline state**
   ```bash
   git status --short --branch
   git remote -v
   git rev-parse --abbrev-ref HEAD
   ```

2. **Stage only intended files**
   ```bash
   git add <specific files>
   git diff --staged
   ```

3. **Commit with one concern only**
   ```bash
   git commit -m "feat: add git truth guard"
   ```

4. **Push to the authoritative remote**
   - Prefer `walmart-origin` for this repo unless the user explicitly says otherwise.
   ```bash
   git push walmart-origin <branch>
   ```

5. **Generate a push receipt**
   ```bash
   python tools/git_truth_guard.py --remote walmart-origin --strict
   ```
   Or JSON if another agent/orchestrator needs machine-readable proof:
   ```bash
   python tools/git_truth_guard.py --remote walmart-origin --format json --strict
   ```

6. **Do not mark the task done** unless the receipt proves:
   - local `HEAD` == `remote/<branch>` `HEAD`
   - ahead count is `0`
   - command exited `0`

7. **Report the receipt**
   Include branch, local SHA, remote SHA, remote name, and whether the worktree is dirty.

## Template / Example

Human proof block:
```text
Push verified.
- remote: walmart-origin
- branch: main
- local_head: abc123...
- remote_head: abc123...
- ahead: 0
- behind: 0
- dirty_worktree: false
```

## Notes / Gotchas
- `git push` succeeding is not enough; verify the remote SHA after the push.
- If the repo is already ahead/dirty from unrelated work, say so explicitly. Don’t smear unrelated files into your commit like a goblin.
- `origin` and `walmart-origin` may diverge; verify against the remote the team actually cares about.
- Never force-push. Ever. We are not raccoons in a production dumpster.
