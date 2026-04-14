# Agent: chiefmaxim
**Category:** Dev Agent  
**Type:** Code Puppy Sub-Agent  
**Display Name:** ChiefMaxim 📋

---

## What It Is
Constrained cross-project governance and repository-discipline sub-agent.
Operates across all of Maxim's projects — not scoped to SiteOwlQA alone.

## Role in This Project
- Cross-project governance decisions that affect SiteOwlQA
- Repository discipline enforcement (git hygiene, file naming, commit standards)
- Keeping SiteOwlQA aligned with standards set across the broader portfolio
- Invoked when a decision needs to be durable across multiple projects, not just this one

## When to Use It
- When a decision made here should also apply to other Maxim projects
- When the git/repo discipline needs an authoritative second opinion
- When something needs to be governed from above the project level

## How to Invoke
```
/agent chiefmaxim
```

## Relationship to This Project's Governance
SiteOwlQA has its own governance constitution in `CLAUDE.md` and `MEMORY.md`.
ChiefMaxim does not override these — it operates at the meta-level above them.
If ChiefMaxim and `CLAUDE.md` conflict, resolve explicitly, don't let one silently win.

## Relevant Project Files
| File | Relevance |
|---|---|
| `CLAUDE.md` | Project constitution — ChiefMaxim may inform updates here |
| `MEMORY.md` | Settled decisions — cross-project decisions get logged here too |
| `development.md` | Roadmap — ChiefMaxim may set or close roadmap items |
| `docs/git-truth-orchestration.md` | Anti-lie workflow — ChiefMaxim enforces this model |
