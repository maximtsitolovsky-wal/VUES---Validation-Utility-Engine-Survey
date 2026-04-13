"""weekly_highlights.py — Generate executive weekly operations reports for SiteOwl.

Uses Pydantic AI with the Element LLM Gateway when configured.
Falls back to a deterministic dashboard-driven report when AI is unavailable.
"""

from __future__ import annotations

import json
import logging
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from siteowlqa.config import AppConfig

log = logging.getLogger(__name__)

try:
    import httpx
    from openai import AsyncOpenAI
except Exception:  # noqa: BLE001
    AsyncOpenAI = None  # type: ignore[assignment]
    httpx = None  # type: ignore[assignment]

try:
    from pydantic_ai import Agent
    from pydantic_ai.models.openai import OpenAIModel
    from pydantic_ai.providers.openai import OpenAIProvider
except Exception:  # noqa: BLE001
    Agent = None  # type: ignore[assignment]
    OpenAIModel = None  # type: ignore[assignment]
    OpenAIProvider = None  # type: ignore[assignment]

_PLACEHOLDER = "[not available]"
_PROGRAM_OWNER = "Maxim Tsitolovsky"
_DASHBOARD_SOURCE = "SiteOwl Executive Dashboard"


def _polish_sentence(text: str) -> str:
    cleaned = " ".join(str(text or "").strip().split())
    replacements = {
        "week over week": "week-over-week",
        "Current throughput is": "Current throughput stands at",
        "while vendor productivity is": "and vendor productivity is",
        "with ongoing operational oversight on": "with continued operational oversight of",
        "moved": "shifted",
    }
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    if cleaned and cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned


def _polish_lines(lines: list[str]) -> list[str]:
    return [_polish_sentence(line) if line and not line.endswith(":") else line for line in lines]


def _parse_ts(value: str) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    for candidate in (raw, raw.replace("Z", "+00:00")):
        try:
            return datetime.fromisoformat(candidate).replace(tzinfo=None)
        except ValueError:
            continue
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _record_ts(record: dict[str, Any]) -> datetime | None:
    for key in ("processed_at", "submitted_at", "created_time"):
        dt = _parse_ts(str(record.get(key, "")))
        if dt is not None:
            return dt
    return None


def _start_of_week(dt: datetime) -> datetime:
    return (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


def _pct_change(current: float | None, previous: float | None) -> str:
    if current is None or previous is None:
        return _PLACEHOLDER
    if previous == 0:
        return "↑ 100.0%" if current > 0 else "→ 0.0%"
    change = ((current - previous) / previous) * 100
    arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
    return f"{arrow} {change:.1f}%"


def _fmt_num(value: float | int | None, decimals: int = 1) -> str:
    if value is None:
        return _PLACEHOLDER
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return f"{value:.{decimals}f}"


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return _PLACEHOLDER
    return f"{value:.1f}%"


def _fmt_seconds(value: float | None) -> str:
    if value is None:
        return _PLACEHOLDER
    return f"{value:.1f}s"


def _safe_div(numerator: float, denominator: float) -> float | None:
    if not denominator:
        return None
    return numerator / denominator


def _status_style(value: float | None, *, good: float, warn: float) -> tuple[str, str]:
    if value is None:
        return ("YELLOW", "→")
    if value >= good:
        return ("GREEN", "↑")
    if value >= warn:
        return ("YELLOW", "→")
    return ("RED", "↓")


def _window_rows(history_rows: list[dict[str, Any]], start: datetime, end: datetime) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in history_rows:
        dt = _record_ts(row)
        if dt is None:
            continue
        if start <= dt < end:
            enriched = dict(row)
            enriched["_dt"] = dt
            enriched["status"] = str(row.get("status") or "").upper()
            rows.append(enriched)
    return rows


def _turnaround_seconds(rows: list[dict[str, Any]], *, include_errors: bool = False) -> list[float]:
    vals: list[float] = []
    for row in rows:
        status = str(row.get("status") or "").upper()
        if not include_errors and status not in {"PASS", "FAIL"}:
            continue
        try:
            vals.append(float(row.get("turnaround_seconds") or 0))
        except (TypeError, ValueError):
            continue
    return vals


def _avg(nums: list[float]) -> float | None:
    return (sum(nums) / len(nums)) if nums else None


def _build_week_blocks(history_rows: list[dict[str, Any]], now: datetime) -> list[tuple[datetime, datetime, list[dict[str, Any]]]]:
    current_start = _start_of_week(now)
    blocks: list[tuple[datetime, datetime, list[dict[str, Any]]]] = []
    for offset in range(3, -1, -1):
        start = current_start - timedelta(days=7 * offset)
        end = start + timedelta(days=7)
        blocks.append((start, end, _window_rows(history_rows, start, end)))
    return blocks


def _metric_pack(current: float | None, previous: float | None, *, kind: str = "count") -> dict[str, str]:
    if kind == "pct":
        cur = _fmt_pct(current)
        prev = _fmt_pct(previous)
    elif kind == "seconds":
        cur = _fmt_seconds(current)
        prev = _fmt_seconds(previous)
    else:
        cur = _fmt_num(current, 1)
        prev = _fmt_num(previous, 1)
    return {
        "current": cur,
        "previous": prev,
        "change": _pct_change(current, previous),
    }


def _build_context(*, history_rows: list[dict[str, Any]], team_dashboard_data: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    week_blocks = _build_week_blocks(history_rows, now)
    current_start, current_end, current_rows = week_blocks[-1]
    _, _, previous_rows = week_blocks[-2]

    def counts(rows: list[dict[str, Any]]) -> dict[str, int]:
        c = Counter(str(r.get("status") or "").upper() for r in rows)
        return {
            "submitted": len(rows),
            "approved": c.get("PASS", 0),
            "pass": c.get("PASS", 0),
            "fail": c.get("FAIL", 0),
            "error": c.get("ERROR", 0),
            "evaluated": c.get("PASS", 0) + c.get("FAIL", 0),
        }

    current_counts = counts(current_rows)
    previous_counts = counts(previous_rows)

    current_vendors = {str(r.get("vendor_name") or r.get("vendor_email") or "Unknown").strip() or "Unknown" for r in current_rows}
    previous_vendors = {str(r.get("vendor_name") or r.get("vendor_email") or "Unknown").strip() or "Unknown" for r in previous_rows}

    current_active_vendors = len(current_vendors)
    previous_active_vendors = len(previous_vendors)

    current_completion_times = _turnaround_seconds(current_rows)
    previous_completion_times = _turnaround_seconds(previous_rows)

    current_submitted = current_counts["submitted"]
    current_approved = current_counts["approved"]
    current_evaluated = current_counts["evaluated"]
    previous_submitted = previous_counts["submitted"]
    previous_approved = previous_counts["approved"]
    previous_evaluated = previous_counts["evaluated"]

    current_completion_rate = (_safe_div(current_approved, current_submitted) or 0) * 100 if current_submitted else None
    previous_completion_rate = (_safe_div(previous_approved, previous_submitted) or 0) * 100 if previous_submitted else None

    current_pass_rate = (_safe_div(current_counts["pass"], current_evaluated) or 0) * 100 if current_evaluated else None
    previous_pass_rate = (_safe_div(previous_counts["pass"], previous_evaluated) or 0) * 100 if previous_evaluated else None

    current_accuracy = (_safe_div(current_counts["submitted"] - current_counts["error"], current_counts["submitted"]) or 0) * 100 if current_submitted else None
    previous_accuracy = (_safe_div(previous_counts["submitted"] - previous_counts["error"], previous_counts["submitted"]) or 0) * 100 if previous_submitted else None

    current_vendor_productivity = _safe_div(current_submitted, current_active_vendors)
    previous_vendor_productivity = _safe_div(previous_submitted, previous_active_vendors)

    current_avg_completion = _avg(current_completion_times)
    previous_avg_completion = _avg(previous_completion_times)

    vendor_rollups: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "submitted": 0,
        "approved": 0,
        "evaluated": 0,
        "pass": 0,
        "turnaround": [],
    })
    for row in current_rows:
        vendor = str(row.get("vendor_name") or row.get("vendor_email") or "Unknown").strip() or "Unknown"
        rec = vendor_rollups[vendor]
        rec["submitted"] += 1
        if row["status"] == "PASS":
            rec["approved"] += 1
            rec["pass"] += 1
            rec["evaluated"] += 1
        elif row["status"] == "FAIL":
            rec["evaluated"] += 1
        ta = _turnaround_seconds([row])
        if ta:
            rec["turnaround"].extend(ta)

    leaderboard: list[dict[str, str]] = []
    for vendor, rec in sorted(
        vendor_rollups.items(),
        key=lambda item: (-item[1]["approved"], _avg(item[1]["turnaround"]) or 999999, item[0].lower()),
    )[:5]:
        avg_time = _avg(rec["turnaround"])
        qa_pass = (_safe_div(rec["pass"], rec["evaluated"]) or 0) * 100 if rec["evaluated"] else None
        productivity_score = (rec["approved"] * 100) + (qa_pass or 0)
        leaderboard.append({
            "vendor": vendor,
            "surveys_completed": _fmt_num(rec["approved"], 0),
            "avg_completion_time": _fmt_seconds(avg_time),
            "qa_pass_rate": _fmt_pct(qa_pass),
            "vendor_score": _fmt_num(productivity_score, 1),
            "surveys_submitted": _fmt_num(rec["submitted"], 0),
            "approval_rate": _fmt_pct(((_safe_div(rec["approved"], rec["submitted"]) or 0) * 100) if rec["submitted"] else None),
            "productivity_score": _fmt_num(productivity_score, 1),
        })

    rolling_trend: list[dict[str, str]] = []
    for index, (start, _end, rows) in enumerate(week_blocks):
        c = counts(rows)
        vendors = len({str(r.get("vendor_name") or r.get("vendor_email") or "Unknown").strip() or "Unknown" for r in rows})
        eval_count = c["evaluated"]
        pass_rate = ((_safe_div(c["pass"], eval_count) or 0) * 100) if eval_count else None
        avg_completion = _avg(_turnaround_seconds(rows))
        productivity = _safe_div(c["submitted"], vendors)
        label = "Current Week" if index == 3 else f"Week -{3-index}"
        rolling_trend.append({
            "week": label,
            "submitted": _fmt_num(c["submitted"], 0),
            "approved": _fmt_num(c["approved"], 0),
            "vendor_productivity": _fmt_num(productivity, 1),
            "qa_pass_rate": _fmt_pct(pass_rate),
            "avg_completion_time": _fmt_seconds(avg_completion),
            "week_start": start.date().isoformat(),
        })

    throughput_status = _status_style((_safe_div(current_submitted, previous_submitted) or 0) * 100 if previous_submitted else 100.0 if current_submitted else 0.0, good=100, warn=85)
    productivity_status = _status_style((_safe_div(current_vendor_productivity or 0, previous_vendor_productivity or 0) or 0) * 100 if previous_vendor_productivity else 100.0 if current_vendor_productivity else 0.0, good=100, warn=85)
    qa_status = _status_style(current_pass_rate, good=95, warn=85)
    accuracy_status = _status_style(current_accuracy, good=98, warn=90)
    pipeline_status = _status_style((_safe_div(current_counts['error'], current_submitted) or 0) * 100 if current_submitted else None, good=0, warn=5)

    insights = [
        f"Survey throughput is {_pct_change(current_submitted, previous_submitted)} week over week with {current_submitted} total submissions in the current period.",
        f"Total surveys approved moved {_pct_change(current_approved, previous_approved)} to {current_approved} this week.",
        f"Vendor productivity is {_pct_change(current_vendor_productivity, previous_vendor_productivity)} with an average of {_fmt_num(current_vendor_productivity, 1)} surveys per active vendor.",
        f"QA pass rate is {_fmt_pct(current_pass_rate)} versus {_fmt_pct(previous_pass_rate)} last week, a change of {_pct_change(current_pass_rate, previous_pass_rate)}.",
        f"Average completion time is {_fmt_seconds(current_avg_completion)} versus {_fmt_seconds(previous_avg_completion)} last week, a change of {_pct_change(current_avg_completion, previous_avg_completion)}.",
    ]

    context = {
        "title": "SiteOwl Survey Program Weekly Executive Operations Report",
        "reporting_period": f"{current_start.date().isoformat()} to {(current_end - timedelta(days=1)).date().isoformat()}",
        "program_owner": _PROGRAM_OWNER,
        "dashboard_source": _DASHBOARD_SOURCE,
        "kpis": {
            "Total Surveys Submitted": _metric_pack(current_submitted, previous_submitted),
            "Total Surveys Approved": _metric_pack(current_approved, previous_approved),
            "Survey Completion Rate": _metric_pack(current_completion_rate, previous_completion_rate, kind="pct"),
            "QA Pass Rate": _metric_pack(current_pass_rate, previous_pass_rate, kind="pct"),
            "Submission Accuracy": _metric_pack(current_accuracy, previous_accuracy, kind="pct"),
            "Average Completion Time": _metric_pack(current_avg_completion, previous_avg_completion, kind="seconds"),
            "Vendor Productivity (Avg Surveys/Vendor)": _metric_pack(current_vendor_productivity, previous_vendor_productivity),
            "Total Active Surveys": _metric_pack(current_submitted, previous_submitted),
        },
        "health": {
            "Survey Throughput": {"status": throughput_status[0], "trend": throughput_status[1]},
            "Vendor Productivity": {"status": productivity_status[0], "trend": productivity_status[1]},
            "QA Efficiency": {"status": qa_status[0], "trend": qa_status[1]},
            "Submission Accuracy": {"status": accuracy_status[0], "trend": accuracy_status[1]},
            "Operational Pipeline": {"status": pipeline_status[0], "trend": pipeline_status[1]},
        },
        "insights": insights,
        "leaderboard": leaderboard,
        "scorecard": leaderboard,
        "production_metrics": {
            "Surveys Scheduled": {"count": _PLACEHOLDER, "distribution": _PLACEHOLDER},
            "Surveys In Progress": {"count": _PLACEHOLDER, "distribution": _PLACEHOLDER},
            "Surveys Submitted": {"count": _fmt_num(current_submitted, 0), "distribution": _fmt_pct(100.0 if current_submitted else 0.0)},
            "Surveys Under QA Review": {"count": _PLACEHOLDER, "distribution": _PLACEHOLDER},
            "Surveys Approved": {"count": _fmt_num(current_approved, 0), "distribution": _fmt_pct(((_safe_div(current_approved, current_submitted) or 0) * 100) if current_submitted else None)},
            "Surveys Requiring Revision": {"count": _fmt_num(current_counts['fail'], 0), "distribution": _fmt_pct(((_safe_div(current_counts['fail'], current_submitted) or 0) * 100) if current_submitted else None)},
        },
        "velocity_metrics": {
            "Average Field Completion Time": _metric_pack(current_avg_completion, previous_avg_completion, kind="seconds"),
            "Average QA Review Time": {"current": _PLACEHOLDER, "previous": _PLACEHOLDER, "change": _PLACEHOLDER},
            "Average Survey Lifecycle": _metric_pack(current_avg_completion, previous_avg_completion, kind="seconds"),
            "Submission Processing Time": _metric_pack(current_avg_completion, previous_avg_completion, kind="seconds"),
        },
        "rolling_trend": rolling_trend,
        "dashboard_summary": (
            "The dashboard tracks survey throughput volume, vendor productivity rankings, vendor completion cycle times, "
            "QA approval rates, submission accuracy percentages, survey lifecycle duration, vendor efficiency distribution, "
            "pipeline stage distribution, and weekly survey velocity trends."
        ),
        "operational_outlook": (
            f"Current throughput is {_pct_change(current_submitted, previous_submitted)} week over week while vendor productivity is {_pct_change(current_vendor_productivity, previous_vendor_productivity)}. "
            f"Lifecycle monitoring shows average completion time at {_fmt_seconds(current_avg_completion)}, and submission quality is running at {_fmt_pct(current_accuracy)} accuracy with ongoing operational oversight on approval and revision volume."
        ),
        "raw_context": {
            "current_counts": current_counts,
            "previous_counts": previous_counts,
            "current_vendors": current_active_vendors,
            "previous_vendors": previous_active_vendors,
            "scout": (team_dashboard_data.get("scout") or {}) if isinstance(team_dashboard_data, dict) else {},
        },
    }
    return _polish_context_language(context)


def _table(headers: list[str], rows: list[list[str]]) -> str:
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    def fmt_row(items: list[str]) -> str:
        return " | ".join(item.ljust(col_widths[i]) for i, item in enumerate(items))

    sep = "-+-".join("-" * w for w in col_widths)
    lines = [fmt_row(headers), sep]
    lines.extend(fmt_row(row) for row in rows)
    return "\n".join(lines)


def _format_report(context: dict[str, Any]) -> str:
    kpi_rows = [
        [name, vals["current"], vals["previous"], vals["change"]]
        for name, vals in context["kpis"].items()
    ]
    health_rows = [
        [name, item["status"], item["trend"]]
        for name, item in context["health"].items()
    ]
    leaderboard_rows = [
        [str(i + 1), row["vendor"], row["surveys_completed"], row["avg_completion_time"], row["qa_pass_rate"], row["vendor_score"]]
        for i, row in enumerate(context["leaderboard"])
    ] or [["[rank]", "[vendor]", _PLACEHOLDER, _PLACEHOLDER, _PLACEHOLDER, _PLACEHOLDER]]
    scorecard_rows = [
        [row["vendor"], row["surveys_submitted"], row["approval_rate"], row["avg_completion_time"], row["productivity_score"]]
        for row in context["scorecard"]
    ] or [["[vendor]", _PLACEHOLDER, _PLACEHOLDER, _PLACEHOLDER, _PLACEHOLDER]]
    production_rows = [
        [name, item["count"], item["distribution"]]
        for name, item in context["production_metrics"].items()
    ]
    velocity_rows = [
        [name, item["current"], item["previous"], item["change"]]
        for name, item in context["velocity_metrics"].items()
    ]
    rolling_rows = [
        [row["week"], row["submitted"], row["approved"], row["vendor_productivity"], row["qa_pass_rate"], row["avg_completion_time"]]
        for row in context["rolling_trend"]
    ]

    sections = [
        context["title"],
        "",
        "Reporting Header",
        f"- Reporting Period: {context['reporting_period']}",
        f"- Program Owner: {context['program_owner']}",
        f"- Dashboard Source: {context['dashboard_source']}",
        "",
        "Executive KPI Dashboard",
        _table(["Metric", "Current", "Previous", "WoW Change"], kpi_rows),
        "",
        "Program Health Indicators",
        _table(["Indicator", "Status", "Trend"], health_rows),
        "",
        "Top 5 Operational Insights",
        *[f"{idx}. {insight}" for idx, insight in enumerate(context["insights"], start=1)],
        "",
        "Vendor Performance Leaderboard",
        _table(["Rank", "Vendor", "Surveys Completed", "Avg Completion Time", "QA Pass Rate", "Vendor Score"], leaderboard_rows),
        "",
        "Vendor Performance Scorecard",
        _table(["Vendor", "Surveys Submitted", "Approval Rate", "Avg Completion Time", "Productivity Score"], scorecard_rows),
        "",
        "Survey Production Metrics",
        _table(["Metric", "Count", "Distribution"], production_rows),
        "",
        "Survey Velocity Metrics",
        _table(["Metric", "Current", "Previous", "Change %"], velocity_rows),
        "",
        "Rolling 4 Week Performance Trend",
        _table(["Week", "Total Surveys Submitted", "Total Surveys Approved", "Vendor Productivity", "QA Pass Rate", "Average Completion Time"], rolling_rows),
        "",
        "Dashboard Performance Metrics Summary",
        context["dashboard_summary"],
        "",
        "Operational Outlook",
        context["operational_outlook"],
    ]
    return "\n".join(sections)


def _polish_context_language(context: dict[str, Any]) -> dict[str, Any]:
    context = dict(context)
    context["insights"] = _polish_lines(list(context.get("insights", [])))
    context["dashboard_summary"] = _polish_sentence(str(context.get("dashboard_summary", "")))
    context["operational_outlook"] = _polish_sentence(str(context.get("operational_outlook", "")))
    return context


def _grammar_fluency_polish(text: str, cfg: AppConfig) -> str:
    cleaned = "\n".join(_polish_lines(str(text).splitlines()))
    base_url = _build_llm_base_url(cfg)
    api_key = cfg.element_llm_gateway_api_key
    if not cleaned or not base_url or not api_key:
        return cleaned
    if (
        Agent is None
        or OpenAIModel is None
        or OpenAIProvider is None
        or AsyncOpenAI is None
        or httpx is None
    ):
        return cleaned

    verify: str | bool = cfg.wmt_ca_path or os.getenv("WMT_CA_PATH", "") or True
    client = AsyncOpenAI(
        base_url=base_url,
        api_key="ignored",
        default_headers={"X-Api-Key": api_key},
        http_client=httpx.AsyncClient(verify=verify),
    )
    model_name = cfg.element_llm_gateway_model or "element:gpt-4o"
    model = OpenAIModel(model_name, provider=OpenAIProvider(openai_client=client))
    instructions = (
        "Polish the provided executive operations report for grammar, fluency, and professional wording only. "
        "Do not change metrics, calculations, placeholders, table structure, headings, or factual meaning. "
        "Keep the tone concise, executive, and metric-driven."
    )
    prompt = f"Polish this report without changing factual content:\n\n{cleaned}"
    agent = Agent(model, instructions=instructions)
    try:
        result = agent.run_sync(prompt)
        text_out = getattr(result, "output", None) or getattr(result, "data", None) or str(result)
        polished = str(text_out).strip()
        return polished or cleaned
    except Exception as exc:  # noqa: BLE001
        log.warning("Grammar/fluency polish failed: %s", exc)
        return cleaned


def _build_llm_base_url(cfg: AppConfig) -> str:
    if cfg.element_llm_gateway_url:
        return cfg.element_llm_gateway_url
    if cfg.element_llm_gateway_project_id:
        return (
            "https://ml.prod.walmart.com:31999/element/genai/project/"
            f"{cfg.element_llm_gateway_project_id}/openai/v1"
        )
    return ""


def _generate_llm_summary(context: dict[str, Any], cfg: AppConfig) -> str | None:
    if (
        Agent is None
        or OpenAIModel is None
        or OpenAIProvider is None
        or AsyncOpenAI is None
        or httpx is None
    ):
        return None

    base_url = _build_llm_base_url(cfg)
    api_key = cfg.element_llm_gateway_api_key
    if not base_url or not api_key:
        return None

    verify: str | bool = cfg.wmt_ca_path or os.getenv("WMT_CA_PATH", "") or True
    client = AsyncOpenAI(
        base_url=base_url,
        api_key="ignored",
        default_headers={"X-Api-Key": api_key},
        http_client=httpx.AsyncClient(verify=verify),
    )
    model_name = cfg.element_llm_gateway_model or "element:gpt-4o"
    model = OpenAIModel(model_name, provider=OpenAIProvider(openai_client=client))

    instructions = (
        "You are creating a polished executive-style weekly operations report for the SiteOwl Survey Program. "
        "Use only dashboard-style operational metrics, vendor metrics, percentage changes, survey throughput data, leaderboard performance, and program health indicators from the provided JSON. "
        "Do not include unrelated commentary. Do not add project workstreams, development updates, design updates, training notes, or non-dashboard narrative unless explicitly provided. "
        "Write in a clean executive tone. Make it read like a leadership operations report. Keep the language concise, performance-focused, and metric-driven. Emphasize week-over-week changes in percent format. Prioritize operational visibility, vendor performance, survey pipeline, and turnaround metrics. "
        "Use professional report formatting with headings and tables where useful. If a metric value is not supplied, leave a clear placeholder in brackets. Do not invent business context."
    )
    prompt = (
        "Generate the report with this exact structure:\n"
        "1. Title - SiteOwl Survey Program Weekly Executive Operations Report\n"
        "2. Reporting Header\n"
        "3. Executive KPI Dashboard\n"
        "4. Program Health Indicators\n"
        "5. Top 5 Operational Insights\n"
        "6. Vendor Performance Leaderboard\n"
        "7. Vendor Performance Scorecard\n"
        "8. Survey Production Metrics\n"
        "9. Survey Velocity Metrics\n"
        "10. Rolling 4 Week Performance Trend\n"
        "11. Dashboard Performance Metrics Summary\n"
        "12. Operational Outlook\n\n"
        "Use only this JSON context:\n"
        f"{json.dumps(context, indent=2)}"
    )

    agent = Agent(model, instructions=instructions)
    try:
        result = agent.run_sync(prompt)
        text = getattr(result, "output", None) or getattr(result, "data", None) or str(result)
        cleaned = str(text).strip()
        return cleaned or None
    except Exception as exc:  # noqa: BLE001
        log.warning("Element LLM weekly highlights generation failed: %s", exc)
        return None


def build_weekly_highlights_payload(*, history_rows: list[dict[str, Any]], team_dashboard_data: dict[str, Any], cfg: AppConfig) -> dict[str, Any]:
    context = _build_context(history_rows=history_rows, team_dashboard_data=team_dashboard_data)
    llm = _generate_llm_summary(context, cfg)
    report_text = llm or _format_report(context)
    polished_report_text = _grammar_fluency_polish(report_text, cfg)
    return {
        "report_text": polished_report_text,
        "report_data": context,
        "llm_enabled": bool(llm),
        "grammar_polished": True,
    }


def generate_weekly_highlights(*, history_rows: list[dict[str, Any]], team_dashboard_data: dict[str, Any], cfg: AppConfig) -> str:
    payload = build_weekly_highlights_payload(
        history_rows=history_rows,
        team_dashboard_data=team_dashboard_data,
        cfg=cfg,
    )
    return str(payload["report_text"])
