# Task

## Metadata

- id: TASK-20260427-routing-zeros
- title: Fix routing page showing all zeros (with VERIFIED browser confirmation)
- created_by: human:maxim
- owner: unclaimed
- status: open
- priority: urgent
- created_at: 2026-04-27T15:20:00Z
- updated_at: 2026-04-27T15:20:00Z
- expires_at: none

## Objective

User must see actual survey routing data (774 sites, 279 surveys, etc.) in browser at http://127.0.0.1:60630/routing.html instead of all zeros.

## Context

**History of attempts:**

1. Agent diagnosed as browser cache issue → created helper pages → user still sees zeros
2. Agent found actual bug: JavaScript string mismatch ('complete' vs 'survey-completed')
3. Agent fixed ui/routing.html and output/routing.html → recompiled → user STILL sees zeros
4. Agent verified server serves correct code via curl → user STILL sees zeros
5. Agent created diagnostic test → test PASSES (data loads), routing page FAILS (zeros displayed)

**Current state:**
- Server: Serving correct fixed code (verified via curl)
- Data: JSON file has 774 sites (verified)
- Diagnostic: routing_test.html loads data correctly (verified by user)
- Routing page: Still shows all zeros in user's browser

**Conflicting evidence:**
- curl shows fixed code
- diagnostic test shows data loads
- actual routing page shows zeros

**Unverified assumption:**
- Agent assumes browser cache is the issue
- Agent has NOT verified the actual browser display
- Agent has NOT checked browser DevTools console for errors

## Inputs

- Current routing page URL: http://127.0.0.1:60630/routing.html
- Fixed source files: ui/routing.html, output/routing.html
- Data file: output/survey_routing_data.json
- Diagnostic test: output/routing_test.html (PASSES)

## Output

**Required deliverable:**

1. User explicitly confirms: "I see the data now, not zeros"
2. Screenshot or visual verification showing non-zero values
3. Root cause documented in execution log
4. Prevention measure added to prevent future "fixed but not verified" loops

## Steps

1. **Agent claims this task**
2. **Agent asks human to open DevTools (F12) and check Console tab for errors**
3. **Agent waits for human response** (DO NOT PROCEED WITHOUT THIS)
4. If errors present:
   - Read error message
   - Fix actual JavaScript bug
   - Recompile
   - Ask human to verify again
5. If no errors:
   - Create cache-busting version with timestamp filename
   - Ask human to try that version
6. **Human confirms visual verification**: "I see non-zero data"
7. **Agent logs completion evidence**
8. **Agent moves task to done/ with screenshot or confirmation quote**

## Constraints

- **HARD RULE:** Agent must NOT claim "fixed" without explicit human visual confirmation
- **HARD RULE:** Agent must NOT assume cache clearing worked without verification
- **HARD RULE:** Agent must NOT close task until human says "I see the data"
- Agent may NOT skip step 2 (DevTools check)
- Agent may NOT skip step 6 (visual confirmation)

## Claim Rules

Only one actor may own the task at a time.

To claim:
1. Move file from /tasks/open/ to /tasks/claimed/
2. Set owner field
3. Set status: claimed
4. Add entry to /logs/execution_log.md

## Completion Rules

To complete:
1. Move file to /tasks/done/
2. Set status: done
3. Add final result with human's actual confirmation quote
4. Notify human through /outbox/human/

## Blocked Rules

If blocked:
1. Move file to /tasks/blocked/
2. Set status: blocked
3. State blocker explicitly
4. Create a message requesting resolution
