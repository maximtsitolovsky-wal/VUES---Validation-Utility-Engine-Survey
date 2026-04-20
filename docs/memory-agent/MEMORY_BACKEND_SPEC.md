# MEMORY_BACKEND_SPEC.md — SiteOwlQA Memory Backend Specification
> File-backed, Windows-first, Markdown + JSONL. No database. No Docker.

---

## Design Constraints

- Windows file system. No symlinks assumed.
- No external database or vector store.
- No Docker or cloud service.
- Must work offline on the same machine as the pipeline.
- Must survive Task Scheduler restarts without data loss.
- Git-committable at any time.
- No PII, no secrets, no credentials.

---

## Directory Structure

```
C:\VUES\
└── docs\
    └── memory-agent\
        ├── AGENT.md               ← behavior spec
        ├── MEMORY_POLICY.md       ← policy rules
        ├── MEMORY_SCHEMA.md       ← record formats
        ├── HANDOFF_SPEC.md        ← handoff format
        ├── MEMORY_BACKEND_SPEC.md ← this file
        └── store\
            ├── durable.jsonl      ← active durable memory records
            ├── handoff_index.md   ← fast-scan handoff log
            ├── session_YYYYMMDD.md← today's session notes (one file per day)
            ├── handoffs\
            │   └── handoff_YYYYMMDD_HHMM.md  ← full handoff blocks
            └── archive\
                └── YYYY\
                    └── archive_YYYY.jsonl     ← superseded/archived records
```

All paths are relative to `C:\VUES`.
Use `pathlib.Path` for all file operations — never hardcode `\` separators in code.

---

## MEMORY.md Integration

`MEMORY.md` is the **primary durable surface**. It has priority over `durable.jsonl`
for architectural decisions.

### How the two surfaces relate:

| Surface          | Best for                                                   | Format            |
|------------------|------------------------------------------------------------|-------------------|
| `MEMORY.md`      | Architectural decisions, governance rules, QUICK REF       | Structured Markdown|
| `durable.jsonl`  | Machine-searchable facts, open loops, bugfixes, preferences| JSONL             |

**Rule:** Any entry in `MEMORY.md` Session Log should have a corresponding summary
entry in `durable.jsonl`. The JSONL entry is the searchable index; `MEMORY.md` is
the human-readable canonical record.

### Sync procedure (manual, at session close):

1. Append decision to `MEMORY.md` Session Log (formatted block).
2. Update QUICK REF block if it affects stack, modules, risks, or last 3 decisions.
3. Write corresponding JSONL record to `durable.jsonl`.
4. Commit both files together: `chore: memory — <title>`

Do not let the two surfaces diverge. If they conflict, `MEMORY.md` wins.

---

## durable.jsonl — Format and Operations

One JSON object per line. UTF-8. No trailing commas.

### Read (retrieval)

```python
import json
from pathlib import Path

STORE = Path(r"C:\VUES\docs\memory-agent\store")

def load_durable(tags=None, scope=None, status="active"):
    records = []
    with open(STORE / "durable.jsonl", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("status") != status:
                continue
            if tags and not any(t in r.get("tags", []) for t in tags):
                continue
            if scope and r.get("scope") != scope:
                continue
            records.append(r)
    return records
```

### Write (append new record)

```python
def append_durable(record: dict):
    """Append one record to durable.jsonl. Never overwrite existing lines."""
    with open(STORE / "durable.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
```

### Update (supersede existing record)

JSONL is append-only. To supersede:

1. Mark old record `status: superseded` by rewriting the file
   (read all, update the target line, write all back — acceptable since file is small).
2. Write new record with `"supersedes": "<old-id>"`.
3. Commit both changes.

```python
def supersede(old_id: str, new_record: dict):
    path = STORE / "durable.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    updated = []
    for line in lines:
        r = json.loads(line)
        if r["id"] == old_id:
            r["status"] = "superseded"
        updated.append(json.dumps(r, ensure_ascii=False))
    path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    append_durable(new_record)
```

### Archive

Move records to archive when they are superseded and no longer need active scanning.

```python
def archive_record(record_id: str, year: str):
    path = STORE / "durable.jsonl"
    archive_path = STORE / "archive" / year / f"archive_{year}.jsonl"
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    lines = path.read_text(encoding="utf-8").splitlines()
    remaining, to_archive = [], []
    for line in lines:
        r = json.loads(line)
        if r["id"] == record_id:
            r["status"] = "archived"
            to_archive.append(json.dumps(r, ensure_ascii=False))
        else:
            remaining.append(json.dumps(r, ensure_ascii=False))

    path.write_text("\n".join(remaining) + "\n", encoding="utf-8")
    with open(archive_path, "a", encoding="utf-8") as f:
        for line in to_archive:
            f.write(line + "\n")
```

---

## Session Notes — Format and Lifecycle

### File naming
One file per calendar day: `store/session_YYYYMMDD.md`

### Lifecycle

```
Session starts
  → Open (or create) today's session file
  → Append notes as work progresses

Milestone or task boundary reached
  → Review notes in today's file
  → Compress redundant entries in-place

Session ends
  → Run end-of-task emission sequence (HANDOFF_SPEC.md)
  → Notes marked Promote:yes → promoted to MEMORY.md + durable.jsonl
  → Notes marked Promote:no → left in session file (low cost, not injected)
  → Write handoff block

Next day
  → Yesterday's session file is not injected automatically
  → Only retrieved if tags match a relevant query
```

### Session file header

```markdown
# Session Notes — YYYY-MM-DD
> Subsystem focus: <area>
> Retrieval tags pre-loaded: <tags>
> Prior handoff loaded: yes (handoff_YYYYMMDD_HHMM.md) | no

---
```

---

## Retrieval Implementation

Simple tag + keyword scan. No vector DB needed at current scale.

```python
def retrieve(tags: list[str], scope: str = None, max_results: int = 5) -> list[dict]:
    """
    Retrieve top durable memory records for a given query.
    Returns ranked list, highest relevance first.
    Token budget: caller must enforce ≤ 800 tokens across returned summaries.
    """
    candidates = load_durable(tags=tags, scope=scope, status="active")

    def rank(r):
        tag_hits = sum(1 for t in tags if t in r.get("tags", []))
        freshness_score = {"stable": 2, "semi-stable": 1, "volatile": 0}[r["freshness"]]
        confidence_score = {"high": 2, "medium": 1, "low": 0}[r["confidence"]]
        return tag_hits * 3 + freshness_score + confidence_score

    candidates.sort(key=rank, reverse=True)
    return candidates[:max_results]
```

**Token estimation:** Each `summary` + `why_it_matters` pair averages ~80–120 tokens.
5 expanded records ≈ 400–600 tokens. Well within the 800-token default budget.

When budget is tight, return only `id`, `title`, `summary` — skip `why_it_matters`.

---

## Git Commit Rules for Memory Files

Memory commits are `chore:` type. Keep them scoped.

| Change                                  | Commit message                                        |
|-----------------------------------------|-------------------------------------------------------|
| Session note → durable promotion        | `chore: memory — promote <title>`                     |
| Handoff written                         | `chore: memory emission — <session objective>`         |
| MEMORY.md decision appended             | `docs: memory — <decision title>`                     |
| durable.jsonl record superseded         | `chore: memory — supersede MEM-ID (<reason>)`         |
| Archive record moved                    | `chore: memory — archive MEM-ID`                      |

**Never force-push memory commits.**
Memory files are part of the repo's history. Treat them like code.

---

## `memory.py` Integration

The existing `src/siteowlqa/memory.py` module handles **lesson retrieval**
(tag + keyword search over the operational lesson archive).

This backend spec does **not** replace `memory.py`.
They serve different scopes:

| Module / Surface        | Scope                                              |
|-------------------------|----------------------------------------------------|
| `memory.py`             | Operational lessons from pipeline runs (runtime)   |
| `docs/memory-agent/store/durable.jsonl` | Agent decisions, architecture, workflow |

Future upgrade path: when lessons in either surface exceed ~100 records,
consider semantic search via embedding. This is **upgrade path #3** in MEMORY.md.
Do not build it now. YAGNI.
