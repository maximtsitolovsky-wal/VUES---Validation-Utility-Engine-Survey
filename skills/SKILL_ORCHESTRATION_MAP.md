# SKILL: Orchestration Map / Visual Pipeline
**Last Used:** 2026-04-13
**Times Used:** 1

## Trigger
User asks: "show me the flow", "how does the app think", "visualise the pipeline",
"draw the architecture", "orchestration diagram", "visual map of X", "how is it orchestrated".

## Context — Read First
- Read the main orchestrator file (e.g. `poll_airtable.py`, `main.py`).
- Read the module map from `README.md` or `MEMORY.md`.
- Read `prompts/architect_prompt.md` if present.
- Identify: entry point → steps → branches (PASS/FAIL/ERROR) → learning loop → async workers.

## Steps

1. **Extract pipeline steps** from the orchestrator source. Count them. Map their owners.

2. **Identify module boundaries** — which module owns what. Hard boundaries = important to show.

3. **Identify learning loop** — memory → execute → review → lesson → memory cycle.

4. **Design layout:**
   - Col 1: Linear pipeline flow (top to bottom)
   - Col 2: Module ownership cards
   - Col 3: Thinking model + skill library + special gates (email, async, etc.)

5. **Create `orchestration_map.html`** using Tailwind + custom CSS.
   - Walmart colors: blue.100=#0053e2, spark.100=#ffc220, green.100=#2a8703, red.100=#ea1100
   - `pipe-step` divs with color-coded left borders per step type
   - Arrow connectors between steps (CSS `::after` triangles)
   - `loop-node` circles for the learning loop diagram
   - Module cards with hard-boundary callouts

6. **Open in browser**: `start orchestration_map.html` (Windows) / `open orchestration_map.html` (Mac)

7. **Commit**: `docs: add orchestration map visual`

## Color Coding Convention
- 🔵 Blue border = core processing step
- 🟡 Yellow border = memory/learning step
- 🟢 Green border = PASS outcome / success
- 🔴 Red border = FAIL/ERROR outcome
- 🟣 Purple border = review/introspection step
- ⬜ Gray border = infrastructure/async step

## Notes / Gotchas
- Read the actual source code, not just the README — steps drift from docs over time.
- Branch nodes (PASS/FAIL) should be shown as a flex-row split, not inline.
- The learning loop is circular by design — show it as circles connected with arrows, not a linear list.
- Always include the async workers (metrics, dashboard) as a separate path, not in the main flow.
