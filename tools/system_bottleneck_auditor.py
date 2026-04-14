#!/usr/bin/env python3
"""System Bottleneck Auditor — auto-discovers and audits the SiteOwlQA architecture.

Scans the codebase, assembles structured evidence, then runs a ruthless
bottleneck audit via the Element LLM Gateway (pydantic-ai).
Falls back to a static structural scan when LLM is not configured.

Usage (from project root):
    python tools/system_bottleneck_auditor.py
    python tools/system_bottleneck_auditor.py --no-llm   # static scan only
    python tools/system_bottleneck_auditor.py --no-browser
"""
from __future__ import annotations

import argparse
import ast
import html as _html
import os
import re
import sys
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Ensure project src/ is importable regardless of invocation directory
_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "src") not in sys.path:
    sys.path.insert(0, str(_REPO / "src"))

# LLM deps — optional; agent degrades gracefully without them
try:
    import httpx
    from openai import AsyncOpenAI
    from pydantic_ai import Agent
    from pydantic_ai.models.openai import OpenAIModel
    from pydantic_ai.providers.openai import OpenAIProvider
    _LLM_DEPS = True
except ImportError:
    _LLM_DEPS = False

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SRC = _REPO / "src" / "siteowlqa"
_OUTPUT = _REPO / "output"
_ENV_EXAMPLE = _REPO / ".env.example"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ModuleScan:
    name: str
    lines: int
    docstring: str
    uses_threading: bool
    uses_queue: bool
    uses_sql: bool
    uses_airtable: bool
    uses_http: bool
    is_worker: bool


@dataclass
class SystemEvidence:
    scanned_at: str
    modules: list[ModuleScan]
    env_settings: dict[str, str]
    identified_stores: list[str]
    identified_integrations: list[str]
    key_facts: list[str]


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

def _extract_docstring(source: str) -> str:
    try:
        tree = ast.parse(source)
        return (ast.get_docstring(tree) or "")[:280]
    except SyntaxError:
        return ""


def _scan_module(path: Path) -> ModuleScan:
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        src = ""
    name = path.name
    return ModuleScan(
        name=name,
        lines=len(src.splitlines()),
        docstring=_extract_docstring(src),
        uses_threading="threading" in src,
        uses_queue="Queue" in src or "SubmissionQueue" in src,
        uses_sql="pyodbc" in src or "sql" in name.lower(),
        uses_airtable="airtable" in src.lower() or "airtable" in name.lower(),
        uses_http="requests" in src or "httpx" in src or "urlopen" in src,
        is_worker="worker" in name.lower() or "Worker" in src,
    )


def _read_env_settings() -> dict[str, str]:
    if not _ENV_EXAMPLE.exists():
        return {}
    settings: dict[str, str] = {}
    for line in _ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            settings[k.strip()] = v.strip()
    return settings


def _build_evidence() -> SystemEvidence:
    modules = [
        _scan_module(p)
        for p in sorted(_SRC.glob("*.py"))
        if p.name != "__init__.py"
    ]
    env = _read_env_settings()

    stores = [
        "SQL Server (pyodbc, Windows Auth) — SubmissionRaw, SubmissionLog, "
        "QAResults, SubmissionStage, ReferenceExport view",
        "Local filesystem — archive/ (JSON + raw vendor files), output/ (CSV + HTML), "
        "logs/ (rotating 10 MB), temp/ (transient, auto-cleaned)",
        "SQLite — CorrectionStateDB (idempotency guard for post-pass correction)",
        "In-process SubmissionQueue (dedup set + thread-safe queue.Queue)",
    ]

    integrations = [
        "Airtable REST API — 60-second poll, PATCH status/score/fields, file download",
        "Element LLM Gateway (OpenAI-compatible) — weekly highlights + grammar polish ONLY "
        "(NOT on the grading critical path)",
        "Localhost HTTP server (port 8765, dynamic) — serves output/ with no-cache headers; "
        "exposes /api/app/status|start|stop endpoints",
    ]

    facts = [
        "Main thread: poll loop only — enqueues records, never blocks on grading",
        "WORKER_THREADS (default 3) daemon threads consume SubmissionQueue concurrently",
        "Each worker runs the full 15-step pipeline: download → normalize → SQL load "
        "→ stored-proc grade → Airtable PATCH → archive → metrics signal",
        "MetricsRefreshWorker: single-owner writer for all CSV/HTML — prevents write races",
        "CorrectionWorker: independent daemon, polls Airtable for PASS records with "
        "True Score >= 95, applies post-pass field correction",
        "Crash recovery on startup: QUEUED/PROCESSING Airtable records reset to blank "
        "so they are re-picked up cleanly",
        "Reference data: SQL Server (ReferenceExport view) OR Excel workbook, "
        "selected by REFERENCE_SOURCE env var; pre-warmed in daemon thread at startup",
        "Email delivery: Airtable automation owns 100% of vendor email — zero SMTP in pipeline",
        "Grading: Python-side canonical-header comparison (python_grader.py), "
        "with SQL stored procs (usp_LoadSubmissionFromRaw, usp_GradeSubmission) for data staging",
        "All Airtable field names centralized in AirtableFields dataclass (config.py)",
        "SQL uses Windows Trusted Connection — no SQL password stored anywhere",
        "Archive is strictly append-only: submissions/, executions/, reviews/, lessons/",
        "LLM is optional — pipeline runs fully without Element Gateway credentials",
        "Dashboard server spawned as a subprocess; port written to output/dashboard.port "
        "for launcher coordination",
    ]

    return SystemEvidence(
        scanned_at=datetime.now().isoformat(),
        modules=modules,
        env_settings=env,
        identified_stores=stores,
        identified_integrations=integrations,
        key_facts=facts,
    )


# ---------------------------------------------------------------------------
# Evidence formatter
# ---------------------------------------------------------------------------

def _format_evidence(ev: SystemEvidence) -> str:
    total_lines = sum(m.lines for m in ev.modules)
    rows = "\n".join(
        f"| {m.name} | {m.lines} "
        f"| {'✓' if m.uses_threading else ''} "
        f"| {'✓' if m.uses_queue else ''} "
        f"| {'✓' if m.uses_sql else ''} "
        f"| {'✓' if m.uses_airtable else ''} "
        f"| {'✓' if m.uses_http else ''} "
        f"| {'✓' if m.is_worker else ''} |"
        for m in ev.modules
    )
    docstrings = "\n".join(
        f"\n**{m.name}**: {m.docstring}" for m in ev.modules if m.docstring
    )
    stores = "\n".join(f"- {s}" for s in ev.identified_stores)
    integrations = "\n".join(f"- {i}" for i in ev.identified_integrations)
    facts = "\n".join(f"- {f}" for f in ev.key_facts)
    env_block = "\n".join(f"- {k}={v}" for k, v in ev.env_settings.items())

    return f"""\
## Discovered System Evidence
Scanned: {ev.scanned_at}
Total source lines (siteowlqa package): {total_lines:,}

### Module Inventory
| Module | Lines | Threading | Queue | SQL | Airtable | HTTP | Worker |
|--------|-------|-----------|-------|-----|----------|------|--------|
{rows}

### Module Docstrings (Architecture Intent)
{docstrings}

### Data Stores
{stores}

### External Integrations
{integrations}

### Runtime Configuration (.env.example)
{env_block}

### Key Architecture Facts (from source inspection)
{facts}
"""


# ---------------------------------------------------------------------------
# LLM audit
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are System Bottleneck Auditor.

Audit the provided AI application architecture.

Required output:
- bottleneck title, severity, business impact, technical root cause,
  recommended fix, implementation priority, scope (single-user / multi-user / both)
- revised high-level architecture
- cleaner service boundary map

Behavior rules:
- be ruthless; do not preserve weak architecture for convenience
- simplify where possible; prefer clarity over impressive complexity
- treat every component as guilty until justified
- separate observed facts from inferred risks
- do not recommend additional services unless they remove a proven bottleneck
- call out fake optimization, orchestration theater, and redundant decomposition directly

Output format — use this exact markdown structure:
# Architecture Bottleneck Audit

## Executive Verdict
[Direct verdict: viable / fragile / overbuilt / underbuilt / misaligned]

## Bottleneck Summary
| Bottleneck | Severity | Business Impact | Root Cause | Recommended Fix | Priority | Affects |
|---|---|---|---|---|---|---|
| ... |

## Detailed Findings
### 1. [Title]
- Severity: ...
- Affects: ...
- Business impact: ...
- Technical root cause: ...
- Observed evidence: ...
- Why current design fails: ...
- What not to do: ...
- Recommended fix: ...
- Implementation priority: ...
- Classification: ...

## Synchronous vs Asynchronous Split
### Keep Synchronous
- ...
### Move Asynchronous
- ...

## Scaling and Concurrency Risks
- ...

## Reliability and Operational Risks
- ...

## Revised High-Level Architecture
```text
[simplified target]
```

## Cleaner Service Boundary Map
| Service | Responsibility | Owns Data | Depends On | Must Not Own |
|---|---|---|---|---|
| ... |

## Priority-Ordered Remediation Plan
1. ...
"""


def _build_llm_base_url(cfg: object) -> str:
    url = getattr(cfg, "element_llm_gateway_url", "")
    if url:
        return url
    pid = getattr(cfg, "element_llm_gateway_project_id", "")
    if pid:
        return f"https://ml.prod.walmart.com:31999/element/genai/project/{pid}/openai/v1"
    return ""


def _run_llm_audit(arch_context: str, cfg: object) -> str | None:
    if not _LLM_DEPS:
        print("[WARN] pydantic-ai / openai / httpx not installed — static scan only.")
        return None
    base_url = _build_llm_base_url(cfg)
    api_key = getattr(cfg, "element_llm_gateway_api_key", "")
    if not base_url or not api_key:
        print("[WARN] Element LLM Gateway not configured — static scan only.")
        return None

    ca = getattr(cfg, "wmt_ca_path", "") or os.getenv("WMT_CA_PATH", "") or True
    client = AsyncOpenAI(
        base_url=base_url,
        api_key="ignored",
        default_headers={"X-Api-Key": api_key},
        http_client=httpx.AsyncClient(verify=ca),
    )
    model_name = getattr(cfg, "element_llm_gateway_model", "") or "element:gpt-4o"
    model = OpenAIModel(model_name, provider=OpenAIProvider(openai_client=client))
    agent = Agent(model, instructions=_SYSTEM_PROMPT)

    user_prompt = (
        "Audit this AI application architecture. Produce the full "
        "Architecture Bottleneck Audit report in the exact required format.\n\n"
        + arch_context
    )
    print(f"[INFO] Calling {model_name} for bottleneck audit ...")
    try:
        result = agent.run_sync(user_prompt)
        text = getattr(result, "output", None) or getattr(result, "data", None) or str(result)
        return str(text).strip()
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] LLM audit failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Static fallback
# ---------------------------------------------------------------------------

def _static_audit(ev: SystemEvidence) -> str:
    total = sum(m.lines for m in ev.modules)
    heavy = [f"  - {m.name}: {m.lines} lines" for m in ev.modules if m.lines > 600]
    workers = [m.name for m in ev.modules if m.is_worker]
    threaded = [m.name for m in ev.modules if m.uses_threading]

    heavy_block = "\n".join(heavy) if heavy else "  - None detected"
    stores = "\n".join(f"  - {s}" for s in ev.identified_stores)
    integrations = "\n".join(f"  - {i}" for i in ev.identified_integrations)
    env_block = "\n".join(f"  - {k}={v}" for k, v in ev.env_settings.items())

    return f"""\
# Architecture Bottleneck Audit — Static Scan
## (Configure Element LLM Gateway for the full AI-powered audit)

Scanned: {ev.scanned_at}

## Component Summary
- Python modules: {len(ev.modules)}
- Total source lines (siteowlqa package): {total:,}
- Modules using threading: {', '.join(threaded) or 'none'}
- Identified workers: {', '.join(workers) or 'none'}

## Oversized Modules (>600 lines — maintainability risk)
{heavy_block}

## Data Stores
{stores}

## External Integrations
{integrations}

## Runtime Configuration
{env_block}

## Next Step
Run `python -m siteowlqa.setup_config` to configure Element LLM Gateway,
then re-run this auditor for the full bottleneck analysis.
"""


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

def _to_html(md: str) -> str:
    css = """\
body{font-family:system-ui,sans-serif;max-width:1080px;margin:2rem auto;
  padding:0 1.5rem;color:#1a1a1a;background:#fff;line-height:1.6}
h1{font-size:1.75rem;color:#0053e2;border-bottom:3px solid #0053e2;padding-bottom:.5rem;margin-top:0}
h2{font-size:1.25rem;color:#0053e2;margin-top:2rem}
h3{font-size:1.05rem;color:#222;margin-top:1.4rem}
h4{font-size:.95rem;color:#333;margin-top:1rem}
table{width:100%;border-collapse:collapse;font-size:.85rem;margin:1rem 0}
th{background:#0053e2;color:#fff;padding:.45rem .7rem;text-align:left;font-weight:600}
td{padding:.4rem .7rem;border-bottom:1px solid #e5e7f0;vertical-align:top}
tr:nth-child(even) td{background:#f5f8ff}
code{background:#f0f0f0;padding:.1rem .35rem;border-radius:3px;font-size:.83rem}
pre{background:#f4f4f4;padding:.9rem 1rem;border-radius:6px;overflow-x:auto;
  font-size:.82rem;white-space:pre-wrap;border-left:4px solid #0053e2}
ul,ol{padding-left:1.4rem}li{margin:.25rem 0}
blockquote{border-left:4px solid #ffc220;margin:1rem 0;padding:.5rem 1rem;
  background:#fffbf0;border-radius:0 6px 6px 0}
hr{border:none;border-top:1px solid #e0e0e0;margin:1.5rem 0}
.banner{background:#0053e2;color:#fff;padding:1.25rem 1.5rem;border-radius:10px;
  margin-bottom:1.75rem}
.banner h1{color:#fff;border:none;margin:0;font-size:1.5rem}
.banner p{margin:.3rem 0 0;opacity:.8;font-size:.88rem}"""

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parts = [
        "<!DOCTYPE html><html lang='en'><head>",
        "<meta charset='UTF-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<title>System Bottleneck Audit — SiteOwlQA</title>",
        f"<style>{css}</style></head><body>",
        "<div class='banner'>",
        "<h1>&#128269; System Bottleneck Audit — SiteOwlQA</h1>",
        f"<p>Generated: {_html.escape(now)}</p></div>",
    ]

    in_pre = False
    in_table = False
    in_list = False
    pre_buf: list[str] = []

    for raw in md.splitlines():
        esc = _html.escape(raw)

        # --- code fences ---
        if raw.startswith("```"):
            if in_pre:
                parts.append(_html.escape("\n".join(pre_buf)) + "</pre>")
                pre_buf = []
                in_pre = False
            else:
                if in_list:
                    parts.append("</ul>")
                    in_list = False
                lang = raw[3:].strip()
                parts.append(f"<pre data-lang='{_html.escape(lang)}'>")
                in_pre = True
            continue

        if in_pre:
            pre_buf.append(raw)
            continue

        # --- table rows ---
        if raw.strip().startswith("|") and "|" in raw:
            cells = [c.strip() for c in raw.strip().strip("|").split("|")]
            if all(re.fullmatch(r"[-: ]+", c) for c in cells):
                continue  # separator row
            if not in_table:
                if in_list:
                    parts.append("</ul>")
                    in_list = False
                parts.append("<table>")
                in_table = True
                parts.append("<tr>" + "".join(f"<th>{_html.escape(c)}</th>" for c in cells) + "</tr>")
            else:
                parts.append("<tr>" + "".join(f"<td>{_html.escape(c)}</td>" for c in cells) + "</tr>")
            continue
        elif in_table:
            parts.append("</table>")
            in_table = False

        # --- list items ---
        if raw.startswith(("- ", "* ")) or re.match(r"^\d+\. ", raw):
            if not in_list:
                parts.append("<ul>")
                in_list = True
            text = re.sub(r"^[-*] |^\d+\. ", "", raw)
            parts.append(f"<li>{_html.escape(text)}</li>")
            continue
        elif in_list and raw.strip():
            parts.append("</ul>")
            in_list = False

        # --- headings, hr, blockquote, paragraphs ---
        if raw.startswith("# "):
            parts.append(f"<h1>{_html.escape(raw[2:])}</h1>")
        elif raw.startswith("## "):
            parts.append(f"<h2>{_html.escape(raw[3:])}</h2>")
        elif raw.startswith("### "):
            parts.append(f"<h3>{_html.escape(raw[4:])}</h3>")
        elif raw.startswith("#### "):
            parts.append(f"<h4>{_html.escape(raw[5:])}</h4>")
        elif raw.strip() == "---":
            parts.append("<hr>")
        elif raw.startswith("> "):
            parts.append(f"<blockquote>{_html.escape(raw[2:])}</blockquote>")
        elif raw.strip() == "":
            if in_list:
                parts.append("</ul>")
                in_list = False
        else:
            parts.append(f"<p>{esc}</p>")

    if in_list:
        parts.append("</ul>")
    if in_table:
        parts.append("</table>")
    if in_pre:
        parts.append(_html.escape("\n".join(pre_buf)) + "</pre>")

    parts.append("</body></html>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Save + open
# ---------------------------------------------------------------------------

def _save(report_md: str, stem: str) -> tuple[Path, Path]:
    _OUTPUT.mkdir(parents=True, exist_ok=True)
    md_path = _OUTPUT / f"{stem}.md"
    html_path = _OUTPUT / f"{stem}.html"
    md_path.write_text(report_md, encoding="utf-8")
    html_path.write_text(_to_html(report_md), encoding="utf-8")
    return md_path, html_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-llm", action="store_true", help="Static structural scan only (skip LLM)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser when done")
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"bottleneck_audit_{stamp}"

    print("[INFO] Scanning codebase ...")
    ev = _build_evidence()
    total_lines = sum(m.lines for m in ev.modules)
    print(f"[INFO] Found {len(ev.modules)} modules — {total_lines:,} total lines")

    arch_context = _format_evidence(ev)
    report_md: str

    if args.no_llm:
        print("[INFO] --no-llm: generating static scan.")
        report_md = _static_audit(ev)
    else:
        cfg = None
        try:
            from siteowlqa.config import load_config  # noqa: PLC0415
            cfg = load_config()
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] Could not load app config ({exc}) — static scan only.")

        if cfg is not None:
            report_md = _run_llm_audit(arch_context, cfg) or _static_audit(ev)
        else:
            report_md = _static_audit(ev)

    md_path, html_path = _save(report_md, stem)
    print(f"[OK] Markdown : {md_path}")
    print(f"[OK] HTML     : {html_path}")

    if not args.no_browser:
        webbrowser.open(html_path.as_uri())
        print(f"[OK] Opened in browser.")


if __name__ == "__main__":
    main()
