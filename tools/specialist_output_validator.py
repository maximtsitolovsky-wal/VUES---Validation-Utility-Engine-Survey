#!/usr/bin/env python3
"""Specialist Output Validator — quality-gate agent.

Reads the latest outputs from every specialist agent, validates them against
their required deliverables, and produces a structured pass/fail report.

Specialists reviewed:
  - System Bottleneck Auditor      (output/bottleneck_audit_*.md)
  - Docker & Multi-User Platform   (infra/ + output/docker_platform_*.html)
  - Memory & Token Optimization    (output/memory_token_*.md — when built)

LLM mode (Element Gateway configured): full rubric-driven AI validation.
Static mode (fallback): structural presence checks with explicit findings.

Usage:
    python tools/specialist_output_validator.py
    python tools/specialist_output_validator.py --no-llm
    python tools/specialist_output_validator.py --no-browser
"""
from __future__ import annotations

import argparse
import html as _html
import os
import re
import sys
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

_REPO   = Path(__file__).resolve().parents[1]
_OUTPUT = _REPO / "output"
_INFRA  = _REPO / "infra"

if str(_REPO / "src") not in sys.path:
    sys.path.insert(0, str(_REPO / "src"))

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
# Data model
# ---------------------------------------------------------------------------

@dataclass
class AgentEvidence:
    name: str
    files: dict[str, str]         # rel_path → content
    missing_files: list[str]      # paths that should exist but don't
    available: bool = True        # False = agent hasn't run yet


@dataclass
class ValidationResult:
    agent: str
    verdict: str                  # PASS / FAIL / NOT_RUN
    missing: list[str] = field(default_factory=list)
    weak: list[str]    = field(default_factory=list)
    drift: list[str]   = field(default_factory=list)
    revisions: list[str] = field(default_factory=list)
    status: str = ""              # Accepted / Rejected pending revision / Not run


# ---------------------------------------------------------------------------
# Evidence collection
# ---------------------------------------------------------------------------

def _latest(pattern: str) -> Path | None:
    matches = sorted(_OUTPUT.glob(pattern))
    return matches[-1] if matches else None


def _read(p: Path | None) -> str:
    if p is None or not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _collect_bottleneck() -> AgentEvidence:
    md_path = _latest("bottleneck_audit_*.md")
    html_path = _latest("bottleneck_audit_*.html")
    files, missing = {}, []
    if md_path:
        files[str(md_path.relative_to(_REPO))] = _read(md_path)
    else:
        missing.append("output/bottleneck_audit_*.md — no audit run found")
    if html_path:
        files[str(html_path.relative_to(_REPO))] = _read(html_path)
    return AgentEvidence(
        name="System Bottleneck Auditor",
        files=files,
        missing_files=missing,
        available=bool(files),
    )


def _collect_docker() -> AgentEvidence:
    html_path = _latest("docker_platform_*.html")
    required_infra = [
        "Dockerfile", "docker-compose.yml", "docker-compose.override.yml",
        "nginx/nginx.conf", ".env.example", "scripts/start.sh",
        ".dockerignore", "README.md",
    ]
    files, missing = {}, []
    if html_path:
        files[str(html_path.relative_to(_REPO))] = _read(html_path)
    else:
        missing.append("output/docker_platform_*.html — no report found")
    for rel in required_infra:
        p = _INFRA / rel
        if p.exists():
            files[f"infra/{rel}"] = _read(p)
        else:
            missing.append(f"infra/{rel}")
    return AgentEvidence(
        name="Docker and Multi-User Platform Engineer",
        files=files,
        missing_files=missing,
        available=bool(files),
    )


def _collect_memory() -> AgentEvidence:
    md_path = _latest("memory_token_*.md")
    files, missing = {}, []
    if md_path:
        files[str(md_path.relative_to(_REPO))] = _read(md_path)
    else:
        missing.append("output/memory_token_*.md — agent not yet built/run")
    return AgentEvidence(
        name="Memory and Token Optimization Engineer",
        files=files,
        missing_files=missing,
        available=bool(files),
    )


def _build_evidence_block(ev: AgentEvidence) -> str:
    parts = [f"## {ev.name}"]
    if not ev.available:
        parts.append("STATUS: Not yet run — no output files found.")
        parts += [f"  Missing: {m}" for m in ev.missing_files]
        return "\n".join(parts)
    if ev.missing_files:
        parts.append("MISSING FILES:")
        parts += [f"  - {m}" for m in ev.missing_files]
    for rel, content in ev.files.items():
        # Trim very large files — LLM context budget
        preview = content[:6000] + "\n[...truncated...]" if len(content) > 6000 else content
        parts.append(f"\n### {rel}\n{preview}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# LLM validation
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are Specialist Output Validator.

Review the output from specialist agents and apply the rubric below.
Be strict. Do not confuse verbosity with quality. Reject fluff.

For each agent produce exactly this markdown block:

## Agent Reviewed
[name]

## Pass or Fail
[PASS/FAIL/NOT_RUN]

## Missing Items
- ...

## Weak Items
- ...

## Scope Drift Detected
- none
OR
- [description]

## Required Revisions
1. ...

## Final Acceptance Status
[Accepted / Rejected pending revision / Not run — agent not yet built]

---

Then after all agents, produce:

# Specialist Validation Report

## Summary
| Agent | Result | Acceptance Status |
|---|---|---|
| ... | ... | ... |

## Overall Decision
[Which outputs are accepted and which must be revised]

Rubric per agent:

### System Bottleneck Auditor — required deliverables
bottleneck list, severity ranking, business impact, technical root cause,
recommended fix, implementation priority, revised architecture/service boundary.
Reject if: bottlenecks generic, no ranking, root causes missing, fixes vague,
architecture criticized but not improved.

### Memory and Token Optimization Engineer — required deliverables
tiered memory model, schema separation, deduplication rules, pruning/archival
policy, retrieval pipeline improvement, token budget logic, summary integrity
safeguards, measurable optimization metrics.
Reject if: memory vague, retrieval not improved, token reduction claimed but
undefined, summaries compressed without truthfulness safeguards.

### Docker and Multi-User Platform Engineer — required deliverables
service boundary design, Dockerfiles/templates, docker-compose plan, environment
strategy, persistent storage strategy, user/session isolation plan, health
checks, scaling guidance, stateful vs stateless explanation.
Reject if: Docker superficial, services split without justification, multi-user
safety not addressed, stores not persisted, deployment not reproducible.

General rejection criteria: vague, repetitive, not implementation-ready,
contradictory, fake optimization, over-engineered without justification,
missing required sections.
"""


def _build_llm_base_url(cfg: object) -> str:
    url = getattr(cfg, "element_llm_gateway_url", "")
    if url:
        return url
    pid = getattr(cfg, "element_llm_gateway_project_id", "")
    if pid:
        return f"https://ml.prod.walmart.com:31999/element/genai/project/{pid}/openai/v1"
    return ""


def _run_llm_validation(evidences: list[AgentEvidence], cfg: object) -> str | None:
    if not _LLM_DEPS:
        print("[WARN] pydantic-ai/openai not installed — using static validation.")
        return None
    base_url = _build_llm_base_url(cfg)
    api_key  = getattr(cfg, "element_llm_gateway_api_key", "")
    if not base_url or not api_key:
        print("[WARN] Element LLM Gateway not configured — using static validation.")
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

    prompt = "Validate the following specialist agent outputs.\n\n" + "\n\n".join(
        _build_evidence_block(ev) for ev in evidences
    )
    print(f"[INFO] Calling {model_name} for specialist validation ...")
    try:
        result = agent.run_sync(prompt)
        text = getattr(result, "output", None) or getattr(result, "data", None) or str(result)
        return str(text).strip() or None
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] LLM validation failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Static structural validation (fallback)
# ---------------------------------------------------------------------------

def _contains(text: str, *terms: str) -> bool:
    low = text.lower()
    return all(t.lower() in low for t in terms)


def _static_validate_bottleneck(ev: AgentEvidence) -> ValidationResult:
    r = ValidationResult(agent=ev.name, verdict="FAIL")

    if not ev.available:
        r.verdict = "NOT_RUN"
        r.missing = list(ev.missing_files)
        r.status  = "Not run — agent not yet built or no output found"
        return r

    body = "\n".join(ev.files.values())

    required = {
        "bottleneck list / oversized modules": _contains(body, "bottleneck") or _contains(body, "oversized"),
        "severity ranking":    _contains(body, "severity") or _contains(body, "critical") or _contains(body, "risk"),
        "business impact":     _contains(body, "business impact") or _contains(body, "maintainability"),
        "technical root cause":_contains(body, "root cause") or _contains(body, "why"),
        "recommended fix":     _contains(body, "fix") or _contains(body, "remediat") or _contains(body, "recommend"),
        "implementation priority": _contains(body, "priority") or _contains(body, "next step"),
        "revised architecture or service boundary": _contains(body, "architect") or _contains(body, "boundary") or _contains(body, "service"),
    }

    for label, present in required.items():
        if not present:
            r.missing.append(label)

    # Static scan mode lacks LLM content — flag known limitations
    if _contains(body, "static scan") or _contains(body, "configure element"):
        r.weak.append(
            "Output is static scan only — no LLM bottleneck analysis, severity ranking, "
            "root cause identification, or revised architecture. Configure Element LLM Gateway "
            "and re-run for a full audit."
        )
        r.missing += [
            "severity ranking (requires LLM run)",
            "business impact per bottleneck (requires LLM run)",
            "technical root cause (requires LLM run)",
            "revised architecture proposal (requires LLM run)",
        ]

    if r.missing:
        r.verdict = "FAIL"
        r.revisions = [
            f"Add missing section: '{m}'." for m in r.missing
        ]
        r.status = "Rejected pending revision"
    else:
        r.verdict = "PASS"
        r.status  = "Accepted"
    return r


def _static_validate_docker(ev: AgentEvidence) -> ValidationResult:
    r = ValidationResult(agent=ev.name, verdict="FAIL")

    if not ev.available:
        r.verdict = "NOT_RUN"
        r.missing = list(ev.missing_files)
        r.status  = "Not run — agent not yet built or no output found"
        return r

    body = "\n".join(ev.files.values())

    # Structural file presence
    for mf in ev.missing_files:
        r.missing.append(f"File not generated: {mf}")

    # Content checks
    checks = {
        "service boundary design":          _contains(body, "service") and _contains(body, "boundary"),
        "Dockerfile present":               "infra/Dockerfile" in ev.files,
        "docker-compose.yml present":       "infra/docker-compose.yml" in ev.files,
        "environment strategy (.env.example)": "infra/.env.example" in ev.files,
        "persistent storage (named volumes)": _contains(body, "volume"),
        "user/session isolation":           _contains(body, "isolation") or _contains(body, "multi-user") or _contains(body, "tenant"),
        "health checks":                    _contains(body, "healthcheck") or _contains(body, "health check"),
        "scaling guidance":                 _contains(body, "scal") or _contains(body, "horizontal"),
        "stateful vs stateless map":        _contains(body, "stateful") and _contains(body, "stateless"),
        "network strategy":                 _contains(body, "network") or _contains(body, "backend") or _contains(body, "edge"),
        "startup dependency logic":         _contains(body, "depends_on") or _contains(body, "wait") or _contains(body, "readiness"),
    }
    for label, ok in checks.items():
        if not ok:
            r.missing.append(label)

    # Weakness: SQL auth migration documented?
    if not _contains(body, "sql auth") and not _contains(body, "trusted_connection") and not _contains(body, "db_user"):
        r.weak.append(
            "SQL Server Windows Auth → SQL Auth migration is not documented or is insufficiently specific."
        )

    if r.missing or r.weak:
        r.verdict = "FAIL" if r.missing else "PASS"
        r.revisions = [f"Add missing deliverable: '{m}'." for m in r.missing]
        if r.weak:
            r.revisions.append(
                "Document SQL Auth migration: provide before/after connection string, "
                "DB_USER/DB_PASSWORD env vars, and SQL Server login creation script."
            )
        r.status = "Rejected pending revision" if r.missing else "Accepted (with warnings)"
    else:
        r.verdict = "PASS"
        r.status  = "Accepted"
    return r


def _static_validate_memory(ev: AgentEvidence) -> ValidationResult:
    r = ValidationResult(agent=ev.name, verdict="NOT_RUN")
    r.missing = list(ev.missing_files)
    r.status  = "Not run — Memory and Token Optimization Engineer not yet built"
    return r


def _run_static_validation(evidences: list[AgentEvidence]) -> list[ValidationResult]:
    dispatch = {
        "System Bottleneck Auditor":                _static_validate_bottleneck,
        "Docker and Multi-User Platform Engineer":  _static_validate_docker,
        "Memory and Token Optimization Engineer":   _static_validate_memory,
    }
    return [dispatch[ev.name](ev) for ev in evidences]


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

_VERDICT_COLOR = {"PASS": "#2a8703", "FAIL": "#ea1100", "NOT_RUN": "#995213"}
_STATUS_BG     = {
    "Accepted":                     "#f0faf0",
    "Accepted (with warnings)":     "#fffbf0",
    "Rejected pending revision":    "#fff0f0",
    "Not run — agent not yet built":"#f5f5f5",
    "Not run — agent not yet built or no output found": "#f5f5f5",
}


def _result_card_html(r: ValidationResult) -> str:
    vc   = _verdict_color = _VERDICT_COLOR.get(r.verdict, "#555")
    sbg  = _STATUS_BG.get(r.status, "#fff")

    def _ul(items: list[str], empty: str = "None") -> str:
        if not items:
            return f"<em style='color:#888'>{empty}</em>"
        return "<ul>" + "".join(f"<li>{_html.escape(i)}</li>" for i in items) + "</ul>"

    def _ol(items: list[str], empty: str = "None required") -> str:
        if not items:
            return f"<em style='color:#888'>{empty}</em>"
        return "<ol>" + "".join(f"<li>{_html.escape(i)}</li>" for i in items) + "</ol>"

    return f"""
<div style='border:1px solid #d0d5e8;border-radius:8px;margin:1.5rem 0;overflow:hidden'>
  <div style='background:#0053e2;color:#fff;padding:.75rem 1.25rem;display:flex;justify-content:space-between;align-items:center'>
    <strong style='font-size:1.05rem'>{_html.escape(r.agent)}</strong>
    <span style='font-size:1.1rem;font-weight:700;color:{vc};background:#fff;padding:.2rem .65rem;border-radius:20px'>{r.verdict}</span>
  </div>
  <div style='padding:1rem 1.25rem;background:{sbg}'>
    <p style='margin:.25rem 0'><strong>Final Acceptance Status:</strong> {_html.escape(r.status)}</p>
  </div>
  <div style='padding:1rem 1.25rem'>
    <h4 style='margin:.5rem 0 .25rem;color:#ea1100'>Missing Items</h4>{_ul(r.missing)}
    <h4 style='margin:1rem 0 .25rem;color:#995213'>Weak Items</h4>{_ul(r.weak)}
    <h4 style='margin:1rem 0 .25rem;color:#555'>Scope Drift</h4>{_ul(r.drift, "None detected")}
    <h4 style='margin:1rem 0 .25rem;color:#0053e2'>Required Revisions</h4>{_ol(r.revisions)}
  </div>
</div>"""


def _report_html(results: list[ValidationResult], stamp: str, llm_used: bool) -> str:
    css = ("body{font-family:system-ui,sans-serif;max-width:1020px;margin:2rem auto;"
           "padding:0 1.5rem;color:#1a1a1a;line-height:1.6}"
           "h1,h2,h3,h4{color:#0053e2} h2{margin-top:2rem;border-bottom:2px solid #e5e7f0;padding-bottom:.3rem}"
           "table{width:100%;border-collapse:collapse;margin:.75rem 0;font-size:.87rem}"
           "th{background:#0053e2;color:#fff;padding:.4rem .7rem;text-align:left}"
           "td{padding:.35rem .7rem;border-bottom:1px solid #e5e7f0;vertical-align:top}"
           "tr:nth-child(even) td{background:#f5f8ff}"
           ".banner{background:#0053e2;color:#fff;padding:1.25rem 1.5rem;border-radius:10px;margin-bottom:1.75rem}"
           ".banner h1{color:#fff;margin:0;font-size:1.4rem}"
           ".banner p{margin:.25rem 0 0;opacity:.8;font-size:.85rem}"
           ".warn{background:#fffbf0;border-left:4px solid #ffc220;padding:.7rem 1rem;border-radius:0 6px 6px 0;margin:1rem 0}"
           "em{color:#888}")

    mode_note = ("Full LLM validation via Element Gateway."
                 if llm_used else
                 "⚠️ Static structural validation only — configure Element LLM Gateway for full rubric-driven analysis.")

    def _vrow(r: ValidationResult) -> str:
        vc = _VERDICT_COLOR.get(r.verdict, "#555")
        return (
            f"<tr><td>{_html.escape(r.agent)}</td>"
            f"<td style='color:{vc};font-weight:700'>{r.verdict}</td>"
            f"<td>{_html.escape(r.status)}</td></tr>"
        )
    verdict_rows = "".join(_vrow(r) for r in results)

    cards = "".join(_result_card_html(r) for r in results)

    return (
        f"<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'>"
        f"<title>Specialist Validation Report — SiteOwlQA</title><style>{css}</style></head><body>"
        f"<div class='banner'><h1>&#128270; Specialist Output Validator</h1>"
        f"<p>Generated: {_html.escape(stamp)} &nbsp;|&nbsp; {_html.escape(mode_note)}</p></div>"
        f"<h2>Summary</h2>"
        f"<table><tr><th>Agent</th><th>Result</th><th>Acceptance Status</th></tr>"
        f"{verdict_rows}</table>"
        f"<h2>Validation Details</h2>{cards}"
        f"<div class='warn'>&#128161; <strong>Static mode note:</strong> "
        f"Structural checks verify file presence and keyword coverage only. "
        f"Configure Element LLM Gateway and re-run for full rubric enforcement, "
        f"contradiction detection, and severity grading.</div>"
        f"</body></html>"
    )


def _report_md(results: list[ValidationResult], stamp: str, llm_used: bool) -> str:
    lines = [
        "# Specialist Validation Report",
        f"\nGenerated: {stamp}  \nMode: {'LLM (Element Gateway)' if llm_used else 'Static structural checks only'}",
        "\n## Summary",
        "| Agent | Result | Acceptance Status |",
        "|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r.agent} | {r.verdict} | {r.status} |")

    for r in results:
        lines += [
            f"\n---\n## Agent Reviewed\n{r.agent}",
            f"\n## Pass or Fail\n{r.verdict}",
            "\n## Missing Items",
        ]
        lines += [f"- {m}" for m in r.missing] or ["- None"]
        lines.append("\n## Weak Items")
        lines += [f"- {w}" for w in r.weak] or ["- None"]
        lines.append("\n## Scope Drift Detected")
        lines += [f"- {d}" for d in r.drift] or ["- None"]
        lines.append("\n## Required Revisions")
        lines += [f"{i+1}. {rev}" for i, rev in enumerate(r.revisions)] or ["None required"]
        lines.append(f"\n## Final Acceptance Status\n{r.status}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-llm",     action="store_true", help="Static validation only")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser when done")
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("[INFO] Collecting specialist outputs ...")
    evidences = [_collect_bottleneck(), _collect_docker(), _collect_memory()]
    for ev in evidences:
        print(f"  {'OK' if ev.available else 'MISSING'} {ev.name} — "
              f"{len(ev.files)} file(s), {len(ev.missing_files)} missing")

    llm_used = False
    llm_md   = None

    if not args.no_llm:
        cfg = None
        try:
            from siteowlqa.config import load_config  # noqa: PLC0415
            cfg = load_config()
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] Could not load app config ({exc}) — static validation.")
        if cfg is not None:
            llm_md = _run_llm_validation(evidences, cfg)
            llm_used = llm_md is not None

    if llm_md:
        # LLM produced a full markdown report — save it directly + wrap in HTML
        results = []   # no structured results needed; use raw LLM report
        _OUTPUT.mkdir(parents=True, exist_ok=True)
        md_path   = _OUTPUT / f"specialist_validation_{stamp}.md"
        html_path = _OUTPUT / f"specialist_validation_{stamp}.html"
        md_path.write_text(llm_md, encoding="utf-8")
        print(f"[OK] Markdown : {md_path}")

        # Wrap LLM markdown in the same HTML chrome
        import html as _h  # noqa: PLC0415
        css = ("body{font-family:system-ui,sans-serif;max-width:1020px;margin:2rem auto;"
               "padding:0 1.5rem;color:#1a1a1a;line-height:1.6}"
               "h1,h2,h3,h4{color:#0053e2} h2{margin-top:2rem}"
               "table{width:100%;border-collapse:collapse} "
               "th{background:#0053e2;color:#fff;padding:.35rem .6rem}"
               "td{padding:.3rem .6rem;border-bottom:1px solid #e5e7f0}"
               ".banner{background:#0053e2;color:#fff;padding:1.25rem 1.5rem;border-radius:10px;margin-bottom:1.5rem}"
               ".banner h1{color:#fff;margin:0} .banner p{margin:.2rem 0 0;opacity:.8;font-size:.85rem}"
               "pre{background:#f4f4f4;padding:.8rem;border-radius:6px;font-size:.82rem;overflow-x:auto}"
               "code{background:#f0f0f0;padding:.1rem .3rem;border-radius:3px}")
        escaped = _h.escape(llm_md)
        # very lightweight markdown → HTML: convert headings and newlines
        def _md_to_html(md: str) -> str:
            md = re.sub(r"^#### (.+)$", r"<h4>\1</h4>", md, flags=re.M)
            md = re.sub(r"^### (.+)$",  r"<h3>\1</h3>", md, flags=re.M)
            md = re.sub(r"^## (.+)$",   r"<h2>\1</h2>", md, flags=re.M)
            md = re.sub(r"^# (.+)$",    r"<h1>\1</h1>", md, flags=re.M)
            md = re.sub(r"^- (.+)$",    r"<li>\1</li>", md, flags=re.M)
            md = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", md)
            md = md.replace("\n", "<br>")
            return md
        body_html = _md_to_html(_h.escape(llm_md))
        html_path.write_text(
            f"<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'>"
            f"<title>Specialist Validation Report</title><style>{css}</style></head><body>"
            f"<div class='banner'><h1>&#128270; Specialist Output Validator</h1>"
            f"<p>Generated: {stamp} &nbsp;|&nbsp; LLM validation via Element Gateway</p></div>"
            f"{body_html}</body></html>",
            encoding="utf-8",
        )
    else:
        # Static structural validation
        print("[INFO] Running static structural validation ...")
        results = _run_static_validation(evidences)
        for r in results:
            print(f"  [{r.verdict:7s}] {r.agent}")

        _OUTPUT.mkdir(parents=True, exist_ok=True)
        md_path   = _OUTPUT / f"specialist_validation_{stamp}.md"
        html_path = _OUTPUT / f"specialist_validation_{stamp}.html"
        md_path.write_text(_report_md(results, stamp, llm_used=False), encoding="utf-8")
        html_path.write_text(_report_html(results, stamp, llm_used=False), encoding="utf-8")

    print(f"[OK] Markdown : {md_path}")
    print(f"[OK] HTML     : {html_path}")

    if not args.no_browser:
        webbrowser.open(html_path.as_uri())
        print("[OK] Opened in browser.")


if __name__ == "__main__":
    main()
