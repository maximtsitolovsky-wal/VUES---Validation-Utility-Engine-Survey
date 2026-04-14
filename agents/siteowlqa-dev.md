# Agent: siteowlqa-dev
**Category:** Dev Agent  
**Type:** Code Puppy Sub-Agent  
**Display Name:** SiteOwlQA Dev 🦉

---

## What It Is
Project-specific coding assistant scoped entirely to `SiteOwlQA_App`.
Always reads `development.md` before acting, enforces git discipline,
and keeps the roadmap up to date.

## Role in This Project
This is the purpose-built agent for this codebase. Use it for anything
SiteOwlQA-specific where the project context matters more than general coding
knowledge — roadmap items, git receipts, module-ownership enforcement.

## When to Use It Over `code-puppy`
- Working the `development.md` roadmap
- Enforcing module ownership rules (sql.py, models.py, config.py boundaries)
- Anything requiring the full settled-architecture context from MEMORY.md
- When you want stricter SiteOwlQA rule enforcement baked in

## How to Invoke
```
/agent siteowlqa-dev
```
Or let `code-puppy` delegate when the task is project-specific.

## What It Always Does First
1. Reads `development.md`
2. Enforces git discipline — commit SHA + push verification on every task
3. Updates the roadmap when tasks complete

## Project Conventions It Enforces
| Rule | Source |
|---|---|
| `config.py` owns all `os.getenv` calls | `CLAUDE.md` |
| `sql.py` owns all SQL | `MEMORY.md` module ownership table |
| `models.py` owns all shared types | `MEMORY.md` module ownership table |
| Archive is append-only | `CLAUDE.md` + `MEMORY.md` |
| Poll loop never crashes | `MEMORY.md` non-negotiable rules |
| Files ≤ 600 lines | `CLAUDE.md` |
| Task not complete until git receipt verified | `development.md` git workflow |
