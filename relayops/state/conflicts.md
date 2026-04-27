# Conflicts

## CONFLICT-20260427-001

- id: CONFLICT-20260427-001
- detected_at: 2026-04-27T15:20:00Z
- detected_by: agent:relayops
- source_a: agent:code-puppy-473c30 claim (routing.html fixed, browser cache issue)
- source_b: human:maxim verification (routing page still shows all zeros after multiple hard refreshes)
- conflict_summary: Agent claims fix is complete, human reports problem persists
- severity: high
- proposed_resolution: Require live browser verification before claiming completion. Agent must not assume cache fix without visual confirmation from human.
- status: unresolved
- evidence:
  - Agent modified: ui/routing.html, output/routing.html (string mismatch fix 'complete' -> 'survey-completed')
  - Agent verified server response: curl shows fixed code being served
  - Human reports: "still reading all 0's" after hard refresh
  - Agent created diagnostic test: shows data loads correctly (774 sites)
  - Human reports: diagnostic test PASSES (data present), routing page FAILS (all zeros)
  - **Gap:** Agent verified server-side, did NOT verify client-side rendering in actual browser
- root_cause: Agent completed server-side fix but declared victory without end-to-end visual verification
- required_action: Agent must obtain screenshot or explicit "I see the data now" confirmation from human before closing task

## CONFLICT-20260427-002

- id: CONFLICT-20260427-002  
- detected_at: 2026-04-27T15:21:00Z
- detected_by: agent:relayops
- source_a: curl test (shows 'survey-completed' in served HTML)
- source_b: browser display (still shows zeros according to human)
- conflict_summary: Server serves correct code, browser displays incorrect result
- severity: high
- proposed_resolution: Persistent browser cache OR JavaScript execution error in browser context
- status: unresolved
- required_action: Human must open browser DevTools console (F12) and check for JavaScript errors
- alternative_action: Agent must create a cache-busting version with timestamp in filename
