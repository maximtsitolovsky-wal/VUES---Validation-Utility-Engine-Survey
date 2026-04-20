# Agent: airtable
**Category:** Dev Agent  
**Type:** Code Puppy Sub-Agent  
**Display Name:** Airtable Agent 📋

---

## What It Is
Code Puppy sub-agent with full access to the Airtable API — reads, writes,
searches, and manages Airtable bases, tables, and records.

## Role in This Project
Airtable is the **primary intake layer** of VUES. Every vendor submission
arrives via Airtable. The entire poll loop exists to process Airtable records.

Use this agent when you need to:
- Inspect the live Airtable base (fields, record counts, current state)
- Debug record field mapping issues (see `docs/airtable-field-mismatch.md`)
- Verify that the app's `airtable_client.py` is hitting the right table/view
- Patch records manually for testing without running the full pipeline
- Audit what statuses are currently in the submission table

## How to Invoke
```
/agent airtable
```

## Airtable Integration in the App Codebase
| File | What It Does |
|---|---|
| `src/siteowlqa/airtable_client.py` | All Airtable API calls — single owner |
| `src/siteowlqa/poll_airtable.py` | Orchestrates per-record processing using `AirtableClient` |
| `src/siteowlqa/models.py` | `AirtableRecord` dataclass — maps Airtable fields to Python |
| `~/.siteowlqa/config.json` | Airtable API key, base ID, table name — never in `.env` |

## Key Fields in the Submission Table
| Field | Role |
|---|---|
| Submission ID | Primary label — backfilled by pipeline if blank |
| Site Number | Maps to `ProjectID` for grading — RISK-002 open |
| Vendor Email / Vendor Name | Identifies the submitting vendor |
| Attachment | The vendor file — URL expires after a few hours (RISK-003) |
| Status | blank/NEW → QUEUED → PROCESSING → PASS/FAIL/ERROR |

## Open Risks to Know Before Touching Airtable Config
| Risk | Detail |
|---|---|
| RISK-002 | Project ID overwrite not verified post-insert — see `reviewer.py` |
| RISK-003 | Attachment URLs expire — if pipeline is down >2h, records become un-downloadable |
