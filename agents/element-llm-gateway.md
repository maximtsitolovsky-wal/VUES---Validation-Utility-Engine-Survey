# Agent: element-llm-gateway
**Category:** Runtime Agent  
**Type:** pydantic-ai `Agent` instance  
**LLM:** `element:gpt-4o` via Walmart Element LLM Gateway  
**Module:** `src/siteowlqa/weekly_highlights.py`

---

## What It Is
A pydantic-ai `Agent` that runs **inside the SiteOwlQA application** as part of the
weekly highlights pipeline. Not a conversational agent — it is invoked synchronously
as a function call and returns structured text output.

This is the only LLM in the application runtime. Everything else is deterministic.

## What It Does
Generates the weekly executive operations report for the SiteOwl Survey Program.
Takes a structured JSON context (KPIs, vendor leaderboard, rolling trend, insights)
and produces a 12-section polished executive report.

## Where It Runs
```
build_weekly_highlights_payload()
  └─ _generate_llm_summary(context, cfg)
       └─ Agent(model, instructions=...).run_sync(prompt, model_settings={"max_tokens": 1200})
```

## Token Budget (Post-P0 Optimization)
| Item | Value |
|---|---|
| Max output tokens | 1,200 |
| Context keys injected | 9 keys from `_LLM_CONTEXT_KEYS` (stripped of noise) |
| JSON serialization | Compact — `separators=(',', ':')`, no indent |
| LLM calls per report | **1** (grammar-polish second call eliminated 2026-04-14) |
| Client initialization | Cached — `_get_llm_client()` module-level dict, reused |

## Report Structure (12 Sections)
1. Title — SiteOwl Survey Program Weekly Executive Operations Report
2. Reporting Header
3. Executive KPI Dashboard
4. Program Health Indicators
5. Top 5 Operational Insights
6. Vendor Performance Leaderboard
7. Vendor Performance Scorecard
8. Survey Production Metrics
9. Survey Velocity Metrics
10. Rolling 4 Week Performance Trend
11. Dashboard Performance Metrics Summary
12. Operational Outlook

## Configuration (from `~/.siteowlqa/config.json`)
| Config Key | Purpose |
|---|---|
| `element_llm_gateway_url` | Direct URL override (takes priority) |
| `element_llm_gateway_project_id` | Project ID — builds URL automatically if no direct URL |
| `element_llm_gateway_api_key` | API key sent as `X-Api-Key` header |
| `element_llm_gateway_model` | Model name (default: `element:gpt-4o`) |
| `wmt_ca_path` | Walmart CA cert path for TLS verification |

## Fallback Behavior
If the LLM Gateway is unavailable or unconfigured, `_generate_llm_summary()`
returns `None` and `_format_report()` produces a fully deterministic report
from the same context dict. The dashboard still works — it just won't be LLM-polished.

## Gateway URL Pattern
```
https://ml.prod.walmart.com:31999/element/genai/project/{project_id}/openai/v1
```
Reference: https://wmlink.wal-mart.com/genai-access

## Post-Optimization History
| Date | Change |
|---|---|
| 2026-04-14 | P0-A: Grammar-polish second LLM call eliminated (~50% token savings) |
| 2026-04-14 | P0-B: `max_tokens=1200` added |
| 2026-04-14 | P0-C: Context filtered to `_LLM_CONTEXT_KEYS`, compact JSON serialization |
| 2026-04-14 | P0-D: Client cached in `_CLIENT_CACHE` module-level dict |

Full audit: [`docs/memory_token_optimization_report.md`](../docs/memory_token_optimization_report.md)
