# Memory and Token Optimization Redesign — SiteOwlQA

> Produced by: Memory and Token Optimization Engineer v1.0.0  
> Audited: 2026-04-14  
> Scope: `memory.py`, `archive.py`, `reviewer.py`, `poll_airtable.py`, `weekly_highlights.py`

---

## 1. Executive Verdict

**The current memory design is wired but disconnected. It is low-signal, token-unbudgeted, and produces zero LLM value today.**

Confirmed flaws:
- Memory is recalled on every submission with **hardcoded tags** — result is logged and discarded. Nothing reaches any LLM context.
- The reviewer enrichment hook (`surface_warnings_for_review()`) exists but is **called nowhere**.
- Lesson extraction produces **shallow generalized rules** (`"Avoid 'BusinessRule' class issues: ..."`) that are not reusable.
- The weekly report makes **two sequential LLM calls** with no `max_tokens` budget and creates a fresh HTTP client each time.
- The grammar-polish second LLM pass is **redundant** — it reruns the full report through the model after the first call already produces clean output.
- Full-file-system scan on every `recall()` call — O(N) reads, no index, no cache.
- The archive is currently **empty** — no lessons, executions, or reviews have been persisted yet, making all memory retrieval no-ops.

Likely flaws (structural):
- No eligibility gate — retrieval runs whether or not it could possibly help.
- No tier separation — lessons, executions, summaries all live flat in the same scan path.
- No deduplication — repeated failure patterns will generate redundant lesson records.
- No token budget on LLM context injection — context size is unbounded.

---

## 2. Improved Memory Architecture

Three tiers are sufficient for this system. Do not add a fourth without proving need.

### Tier 1 — Session (per-submission, in-memory only)
- **Purpose**: Hold state needed to process the current submission.
- **Allowed**: current record fields, step outputs, validation results, grading outcome.
- **Not for**: lessons, historical summaries, global facts.
- **Retention**: discarded when the submission worker exits. Never written to disk.

### Tier 2 — Working (active lessons and recent executions)
- **Purpose**: Fast-access retrieval for memory-enriched grading. Loaded at startup, refreshed periodically.
- **Allowed**: lessons with `confidence >= 0.75`, executions from the last 30 days, MEDIUM/HIGH/CRITICAL reviewer findings.
- **Not for**: resolved/INFO issues (RISK-001 is noise), executions older than 30 days, unvalidated hypotheses.
- **Retention**: in-memory dict, refreshed every N executions or on explicit archive write.

### Tier 3 — Archive (append-only flat files, current design)
- **Purpose**: Audit trail, cold recall, lesson backfill.
- **Allowed**: all executions, all reviews, all lessons, raw vendor files.
- **Not for**: routine prompt injection. Archive is cold storage.
- **Retention**: permanent, never deleted.

---

## 3. Note Schema Design

### Lesson Schema (current + additions needed)

Current fields in `Lesson` dataclass:
```
lesson_id, task_category, failed_pattern, root_cause,
fix_pattern, generalized_rule, confidence, tags
```

**Add these fields:**
```
source_execution_id   # provenance — which run produced this
issue_type            # maps to reviewer IssueType enum
dedupe_key            # hash(task_category + failed_pattern[:100])
times_retrieved       # hit counter for utility scoring
last_retrieved_at     # freshness tracking
status                # "active" | "archived" | "superseded"
superseded_by         # lesson_id if merged/replaced
```

**Fix `generalized_rule` generation** (see §6).

### ExecutionRecord Schema (current is sufficient)
No schema changes needed. Add one field:
```
memory_hit            # bool — did recall return ≥1 lesson?
memory_lesson_ids     # list[str] — which lessons were recalled
```
This gives the first real metric: recall hit rate.

### Review Schema (current is sufficient)
No schema changes needed. Add:
```
memory_enriched       # bool — was surface_warnings_for_review() used?
enrichment_rules      # list[str] — rules injected from memory
```

### Weekly Report Schema (new — currently not persisted)
Each weekly report generation should save a compact record:
```
report_id, generated_at, week_start, week_end,
llm_enabled, prompt_tokens_estimate, context_keys_used,
llm_call_count, grammar_pass_used
```
This is the only way to measure token spend over time.

---

## 4. Promotion, Deduplication, Pruning, and Archival Rules

### Promotion: Archive → Working Tier
Load into working tier at startup when ALL of:
- `lesson.confidence >= 0.75`
- `lesson.status == "active"`
- `lesson.issue_type != "Concurrency"` (RISK-001 is resolved — never inject)

Refresh working tier after every 10 new lessons written to archive.

### Deduplication
Before writing a new lesson to archive:
1. Compute `dedupe_key = hash(task_category + failed_pattern[:100])`.
2. Scan working-tier lessons for matching `dedupe_key`.
3. If match found with same `issue_type`:
   - Increment `times_retrieved` on existing lesson.
   - Raise `confidence` by 0.05 (capped at 0.95).
   - Do NOT write a new record.
4. If no match: write new lesson normally.

### Pruning
Prune from working tier (not archive) when:
- `confidence < 0.5` and `times_retrieved == 0` after 30 days.
- `status == "superseded"`.
- `issue_type == "Concurrency"` (RISK-001 is permanently resolved).

Never prune from archive. Mark as `status = "archived"` instead.

### Archival
- Executions: already append-only. No change needed.
- Reviews: already append-only. No change needed.
- Lessons: keep all in archive. Working tier filters by status/confidence.

---

## 5. Retrieval Pipeline Design — Fixed

### Current (broken)
```
recall(hardcoded_tags, hardcoded_query)  →  log summary  →  discard
```

### Redesigned (6 stages)

**Stage 0 — Eligibility Gate** *(currently absent — add this)*

Skip recall entirely when:
- Working-tier lesson count == 0 (archive is empty — saves O(N) scan).
- Record has no prior failures for this `site_number` (first-time site).

Proceed when:
- Working tier has ≥ 1 lesson.
- Record's `vendor_name` or `task_category` matches a known lesson tag.

```python
# In process_record(), before Step 2:
if memory.working_tier_count() == 0:
    log.debug("Memory: working tier empty — skipping recall.")
    mem_context = {"lessons": [], "failures": [], "rules": [], "summary": ""}
else:
    mem_context = memory.recall(tags=[record.vendor_name, "file_parse"], query=record.site_number)
```

**Stage 1 — Deterministic Lookup**

Before tag search: check if any lesson's `dedupe_key` matches the current
`(task_category, site_number)` pair directly. If yes, return that lesson
without running the full scored scan.

**Stage 2 — Scored Tag + Keyword Search** *(current logic — keep, with fix)*

Fix: replace hardcoded tags with dynamic tags derived from the record:
```python
tags = [record.vendor_name.lower(), record.site_number, "file_parse"]
query = f"site {record.site_number} vendor {record.vendor_name}"
```

**Stage 3 — Candidate Normalization**

Collapse near-duplicate lessons by `dedupe_key` before returning — return only
the highest-confidence record per key.

**Stage 4 — Top-K Enforcement** *(already present — tighten)*

Current: `max_lessons=5`. Reduce to `max_lessons=3` — if 3 lessons can't
help, 5 won't either. Enforce hard limit, never let caller override upward.

**Stage 5 — Injection Gate** *(currently absent — add this)*

After recall, inject memory into LLM context ONLY when:
- `len(mem_context["rules"]) > 0`
- At least one rule's `task_category` matches the current submission type

Otherwise: skip injection entirely, log it.

**Stage 6 — Context Assembly** *(currently absent — add this)*

When injecting memory into the weekly report LLM call:
```
max memory block = 300 tokens
format = key-value pairs, not full lesson JSON
inject: generalized_rule only (not failed_pattern, root_cause, fix_pattern)
```

---

## 6. Token Budget Strategy

### Weekly Report LLM Calls

**Current problem**: two sequential LLM calls, no `max_tokens`, full JSON dump.

**Fix 1: Merge into a single call**

The grammar polish pass is redundant. The main `_generate_llm_summary` system
prompt already specifies "clean executive tone" and "concise". Remove
`_grammar_fluency_polish` as a second LLM call. Keep the deterministic
`_polish_lines` / `_polish_sentence` pre-processing only.

Before:
```
_build_context()  →  LLM call 1 (generate)  →  LLM call 2 (grammar polish)
```

After:
```
_build_context()  →  _polish_context_language()  →  LLM call 1 (generate + polished)
```

Savings: **~50% of weekly report token spend eliminated**.

**Fix 2: Add `max_tokens` to the LLM call**

```python
# In agent = Agent(model, instructions=instructions)
# pydantic-ai: pass model_settings
result = agent.run_sync(prompt, model_settings={"max_tokens": 1200})
```

A well-structured 12-section executive report needs ~800-1000 tokens output.
Cap at 1200 to give headroom.

**Fix 3: Trim context before JSON dump**

Currently: `json.dumps(context, indent=2)` — full context, indented.
Replace with compact serialization and drop low-value keys:

```python
# Strip keys that don't need LLM attention:
_LLM_CONTEXT_KEYS = {
    "week_start", "week_end", "total_submissions",
    "pass_rate", "fail_rate", "vendor_leaderboard",
    "insights", "survey_velocity", "rolling_4wk",
    "operational_outlook", "dashboard_summary",
}
slim_context = {k: v for k, v in context.items() if k in _LLM_CONTEXT_KEYS}
prompt = f"...JSON context:\n{json.dumps(slim_context, separators=(',', ':'))}"
```

`separators=(',', ':')` removes all whitespace from JSON — saves 10-20%
tokens on the context block with zero information loss.

**Fix 4: Shared HTTP client**

Both LLM calls currently initialize a fresh `AsyncOpenAI` client. Extract
client construction into a module-level cached factory:

```python
@lru_cache(maxsize=1)
def _get_llm_client(base_url: str, api_key: str, verify: str | bool) -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=base_url,
        api_key="ignored",
        default_headers={"X-Api-Key": api_key},
        http_client=httpx.AsyncClient(verify=verify),
    )
```

### Per-Submission Memory Budget
Memory injection into submission processing is currently zero — but when
it is added, cap it:
```
max memory tokens injected per submission: 150
format: plain text rules only — no JSON
max_rules injected: 3
```

---

## 7. Summary Integrity Safeguards

The current system has no summarization layer — lessons are raw strings, not
derived summaries. This is actually the right call at this scale. Keep it.

**One rule to add now**: `generalized_rule` generation is currently a
template string with almost no information value:
```python
# Current (bad):
generalized_rule = f"Avoid '{issue.issue_type}' class issues: {issue.detail[:150]}"
```

This produces lessons like:
> "Avoid 'BusinessRule' class issues: Submission scored 97.1% but was marked FAIL..."

That is not a generalized rule — it is a paraphrase of the symptom.

**Fix — structured rule template per issue type:**

```python
_RULE_TEMPLATES = {
    "DataLoad":     "When rows_loaded == 0 for site {site}: check column mapping and file encoding before SQL insert.",
    "BusinessRule": "Score {score:.1f}% exceeds threshold but status={status}: verify stored proc pass threshold matches config.",
    "DataQuality":  "Blank columns from vendor {vendor} converted to NULL: confirm SubmissionRaw column nullability allows this.",
    "Reliability":  "Silent ERROR (no message) for {vendor}/{site}: add exception message capture at all try/except boundaries.",
    "SecretsExposure": "Secret pattern in {module}: move to AppConfig — never literal string.",
}

def _make_generalized_rule(issue: ReviewIssue, record: AirtableRecord, score: float | None) -> str:
    template = _RULE_TEMPLATES.get(issue.issue_type, "Review '{issue_type}' finding for {site}.")
    return template.format(
        site=record.site_number,
        vendor=record.vendor_name,
        status=record.status,
        score=score or 0.0,
        module="unknown",
        issue_type=issue.issue_type,
    )
```

This produces lessons that are actually retrievable and applicable.

---

## 8. Sync vs Async Recommendations

### Keep Synchronous
- Eligibility gate check (`working_tier_count() == 0` — instant dict len)
- Deterministic lookup (dict key lookup — instant)
- Scored tag+keyword search (in-memory, <5ms at current scale)
- `airtable.update_result()` — must complete before worker exits

### Move Async (or defer to post-processing)
- `archive.save_lesson()` — write to disk after worker returns result
- `archive.save_review()` — same
- `archive.save_execution()` — same
- Working-tier refresh after N new lessons — run in MetricsRefreshWorker cycle
- Weekly report LLM call — already isolated; ensure it doesn't block the poll loop
- `_grammar_fluency_polish` — eliminate entirely (see §6)

**Practical change**: wrap archive writes in the worker's finally block with
a `ThreadPoolExecutor` submit so they don't add to per-submission latency:

```python
# In process_record() finally block:
_ARCHIVE_POOL.submit(archive.save_execution, exec_record)
_ARCHIVE_POOL.submit(archive.save_review, exec_record.execution_id, review_result)
```

---

## 9. Metrics

None of these are currently measured. Add them in this order:

### Immediate (add now, zero infrastructure)
| Metric | Where to add |
|---|---|
| `memory_hit_rate` | Log `len(mem_context["lessons"]) > 0` per submission in ExecutionRecord |
| `lessons_in_working_tier` | Log on startup and after each refresh |
| `lesson_recall_tags_used` | Log tags passed to `recall()` per submission |
| `llm_calls_per_report` | Log count in `build_weekly_highlights_payload()` |
| `weekly_report_llm_enabled` | Already in payload — surface in dashboard |

### Short-term (add when archive has data)
| Metric | Definition |
|---|---|
| `lesson_reuse_rate` | `times_retrieved > 1` / total lessons |
| `duplicate_lesson_rate` | Dedupe collisions / total lesson writes |
| `working_tier_hit_rate` | Recall returns ≥1 result / total recalls |

### Token efficiency (add when LLM calls are active)
| Metric | Definition |
|---|---|
| `avg_context_tokens_per_report` | Estimate: `len(json.dumps(slim_context)) / 4` |
| `llm_calls_saved_by_merge` | Baseline 2 calls → 1 call = 50% saved |

---

## 10. Priority-Ordered Remediation Plan

Ordered by impact-to-effort ratio. Do not do all of these at once.

### P0 — Fix immediately (30 min each, zero risk)

**P0-A**: Remove the grammar polish LLM call (`_grammar_fluency_polish` second
call in `build_weekly_highlights_payload`). Keep `_polish_context_language`
deterministic pre-pass. Saves ~50% of weekly report token spend.

**P0-B**: Add `max_tokens=1200` to the weekly report LLM call.

**P0-C**: Replace `json.dumps(context, indent=2)` with compact serialization
using `_LLM_CONTEXT_KEYS` allowlist and `separators=(',', ':')`.

**P0-D**: Extract `AsyncOpenAI` client into a cached factory (`lru_cache`).

### P1 — Wire the existing memory loop (1–2 hours)

**P1-A**: Replace hardcoded `memory.recall(tags=["sql_import", ...])` with
dynamic tags from the record (`vendor_name`, `site_number`).

**P1-B**: Add eligibility gate — skip recall when `working_tier_count() == 0`.

**P1-C**: Wire `surface_warnings_for_review()` into `review_pipeline_run()` —
it's already written, just not called. Pass memory warnings as `extra_context`.

**P1-D**: Fix `generalized_rule` generation with structured templates (see §7).

### P2 — Add deduplication and working-tier cache (half day)

**P2-A**: Add `dedupe_key` field to `Lesson` dataclass and archive schema.

**P2-B**: Add working-tier in-memory dict to `Memory` class, loaded at startup,
refreshed every 10 new lessons. `recall()` scans working tier only (not full
archive scan).

**P2-C**: Implement pre-write dedup in `extract_lesson_from_failure()`.

### P3 — Metrics instrumentation (1 day)

**P3-A**: Add `memory_hit`, `memory_lesson_ids` to `ExecutionRecord`.

**P3-B**: Add `memory_enriched`, `enrichment_rules` to `ReviewResult`.

**P3-C**: Add weekly report token log record.

**P3-D**: Surface `lesson_count` and `memory_hit_rate` on the dashboard
Admin tab.

### P4 — Semantic search upgrade (only when lessons > 100)

Do not implement now. The skill spec's own guidance applies:
> "When the lesson library grows > 100 entries, consider upgrading to embedding-based semantic search."

The upgrade path is already documented in `memory.py`. Don't touch it until
the library grows. YAGNI.

---

*End of redesign. Implement P0 first — it's pure token savings with no
behaviour change. Then P1 to actually make the memory system do something.*
