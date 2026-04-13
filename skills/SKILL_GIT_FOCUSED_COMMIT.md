# SKILL: Git Focused Commit
**Last Used:** 2026-04-13
**Times Used:** 3

## Trigger
Any time changes are made that need to be committed.
Phrases: "commit this", "save to git", "push", "git commit", "version this".

## Context — Read First
- Always check `git status` before staging anything.
- Read the diff (`git diff --staged` after staging) to confirm no accidental files.
- Know the commit type: feat / fix / docs / refactor / test / chore / governance.

## Steps

1. `git status` — see what is modified/untracked.

2. Stage ONLY the intended files:
   ```bash
   git add <file1> <file2>
   # Never: git add .  (unless you've verified every file in status)
   ```

3. `git diff --staged` — verify the diff is clean. Check for:
   - No secrets / API keys
   - No generated outputs (*.csv, *.html in output/, logs/)
   - No temp files
   - No PII

4. `git commit -m "<type>: <short description>"`
   - `feat:` new feature
   - `fix:` bug fix
   - `docs:` documentation only
   - `refactor:` structural change, no behavior change
   - `test:` test additions
   - `chore:` maintenance (deps, gitignore, etc)
   - `governance:` CLAUDE.md / MEMORY.md / skills/

5. One concern per commit. If you changed two unrelated things, make two commits.

6. `git push` only when explicitly asked or when it's a complete feature.

## Notes / Gotchas
- NEVER `git push --force`. Roll forward, not back.
- Don't commit: `output/`, `logs/`, `temp/`, `archive/`, `.env`, `*.exe`
- If `.gitignore` is missing something, fix it in a separate `chore:` commit first.
- `git stash` if you need to switch context mid-work.
