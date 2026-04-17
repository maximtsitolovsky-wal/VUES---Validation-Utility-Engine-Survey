"""dashboard_exec.py — Executive dashboard generator (embedded tables).

This keeps `dashboard.py` from turning into a mega-file.

Responsibilities:
- Read the cinematic executive dashboard template from ui/executive_dashboard.html
- Inject two metric tables (vendor + processing) into the template
- Apply lightweight virtualization (virtual scrolling) for large datasets
- Copy ui/assets/* -> output/assets/* so images keep working

Design goals:
- Zero visual regressions: reuse existing exec dashboard styling.
- No external dependencies: pure Python + vanilla JS.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any

from siteowlqa.config import AppConfig, load_config
from siteowlqa.weekly_highlights import build_weekly_highlights_payload

log = logging.getLogger(__name__)


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not read json %s: %s", path.name, exc)
        return None


def _read_queue_trend_points(path: Path, *, n: int) -> list[dict[str, Any]]:
    """Return last N queue trend points as [{label,total}] for charting."""
    rows = _read_csv(path)
    tail = rows[-n:] if len(rows) > n else rows

    out: list[dict[str, Any]] = []
    for r in tail:
        ts = (r.get("ts_utc") or "").strip()
        label = ts[11:16] if len(ts) >= 16 else "—"
        try:
            total = int(float((r.get("total") or "0").strip() or 0))
        except ValueError:
            total = 0
        out.append({"label": label or "—", "total": total})

    return out


def generate_executive_dashboard(
    *,
    output_dir: Path,
    template_rel_path: str,
    ui_assets_rel_dir: str,
    output_assets_rel_dir: str,
    out_name: str,
    history_rows: list[dict[str, Any]],
) -> None:
    """Generate output/executive_dashboard.html by embedding metric tables."""
    template_path = output_dir.parent / template_rel_path
    if not template_path.exists():
        log.debug("Executive dashboard template not found (%s) — skipping.", template_path)
        return

    vendor_rows = _read_csv(output_dir / "vendor_metrics.csv")
    summary_rows = _read_csv(output_dir / "processing_summary.csv")

    # NOTE: The executive dashboard is usually opened as a local file (file://).
    # Browsers often block fetch() from local HTML -> local files.
    # So we embed realtime metrics directly into the HTML at generation time.
    realtime_snapshot = _read_json(output_dir / "realtime_snapshot.json")
    queue_trend_points = _read_queue_trend_points(output_dir / "queue_trend.csv", n=12)
    team_dashboard_data = _read_json(output_dir / "team_dashboard_data.json") or {}

    cfg = load_config()
    weekly_highlights_payload = build_weekly_highlights_payload(
        history_rows=history_rows,
        team_dashboard_data=team_dashboard_data,
        cfg=cfg,
    )

    # Slim correction-state entries for the dashboard pill.
    # Shape: [{"site_number": str, "corrected_at": ISO str}, ...]
    _raw_correction_state = _read_json(
        output_dir / "corrections" / ".correction_state.json"
    ) or {}
    correction_entries: list[dict[str, Any]] = [
        {
            "site_number": str(v.get("site_number") or "").strip(),
            "corrected_at": str(v.get("corrected_at") or "").strip(),
        }
        for v in _raw_correction_state.values()
        if isinstance(v, dict)
    ]

    injected = _exec_metrics_tabs_section_html(
        history_rows,
        vendor_rows,
        summary_rows,
        realtime_snapshot=realtime_snapshot,
        queue_trend_points=queue_trend_points,
        team_dashboard_data=team_dashboard_data,
        weekly_highlights_payload=weekly_highlights_payload,
        correction_entries=correction_entries,
    )

    template = template_path.read_text(encoding="utf-8")
    start = "<!-- METRICS_TABLES:START -->"
    end = "<!-- METRICS_TABLES:END -->"
    if start not in template or end not in template:
        raise ValueError("Executive dashboard template missing METRICS_TABLES markers.")

    before, rest = template.split(start, 1)
    _, after = rest.split(end, 1)
    html = before + start + "\n" + injected + "\n" + end + after

    # Do not inject meta refresh. Local file dashboards (`file://`) treat reloads as
    # cross-origin navigations in some browsers, which causes security errors and can
    # break script execution. Refresh is handled safely in JS for hosted contexts only.

    _copy_assets(
        ui_assets_dir=output_dir.parent / ui_assets_rel_dir,
        out_assets_dir=output_dir / output_assets_rel_dir,
    )

    out = output_dir / out_name
    out.write_text(html, encoding="utf-8")
    log.info("%s generated: %s", out_name, out)


def _copy_assets(*, ui_assets_dir: Path, out_assets_dir: Path) -> None:
    try:
        out_assets_dir.mkdir(parents=True, exist_ok=True)
        if not ui_assets_dir.exists():
            return
        for p in ui_assets_dir.glob("*"):
            if p.is_file():
                (out_assets_dir / p.name).write_bytes(p.read_bytes())
    except OSError as exc:
        log.warning("Could not copy executive dashboard assets: %s", exc)


def _exec_metrics_tabs_section_html(
    history_rows: list[dict[str, Any]],
    vendor_rows: list[dict[str, Any]],
    summary_rows: list[dict[str, Any]],
    *,
    realtime_snapshot: dict[str, Any] | None,
    queue_trend_points: list[dict[str, Any]],
    team_dashboard_data: dict[str, Any],
    weekly_highlights_payload: dict[str, Any],
    correction_entries: list[dict[str, Any]] | None = None,
) -> str:
    """Return a single Metrics section with window tabs + real rollups.

    Data source: submission_history.csv rows (pipeline truth).

    Also embeds realtime snapshot + queue trend points directly into the HTML
    so the dashboard works when opened as a local file.

    Rules:
    - include PASS + FAIL only
    - use processed_at for time windows
    - score numeric uses `score` when parseable
    """

    # Keep only the fields we need (smaller HTML payload).
    slim = []
    for r in history_rows:
        slim.append(
            {
                "vendor_email": (r.get("vendor_email") or "").strip(),
                "vendor_name": (r.get("vendor_name") or "").strip(),
                "site_number": (r.get("site_number") or "").strip(),
                "processed_at": (r.get("processed_at") or "").strip(),
                "status": (r.get("status") or "").strip(),
                "score": (r.get("score") or "").strip(),
                "turnaround_seconds": (r.get("turnaround_seconds") or "").strip(),
            }
        )

    data_json = json.dumps(slim)

    vendor_slim: list[dict[str, Any]] = []
    for r in vendor_rows:
        vendor_slim.append(
            {
                "vendor_email": (r.get("vendor_email") or "").strip(),
                "vendor_name": (r.get("vendor_name") or "").strip(),
                "total": (r.get("total_submissions") or "").strip(),
                "pass": (r.get("total_pass") or "").strip(),
                "fail": (r.get("total_fail") or "").strip(),
                "error": (r.get("total_error") or "").strip(),
                "pass_rate_pct": (r.get("pass_rate_pct") or "").strip(),
                "avg_turnaround_seconds": (r.get("avg_turnaround_seconds") or "").strip(),
                "latest_submission_at": (r.get("latest_submission_at") or "").strip(),
            }
        )

    summary_slim: list[dict[str, Any]] = []
    for r in summary_rows:
        summary_slim.append(
            {
                "date": (r.get("date") or "").strip(),
                "total": (r.get("total_submissions") or "").strip(),
                "pass": (r.get("total_pass") or "").strip(),
                "fail": (r.get("total_fail") or "").strip(),
                "error": (r.get("total_error") or "").strip(),
                "pass_rate_pct": (r.get("pass_rate_pct") or "").strip(),
                "unique_vendors": (r.get("unique_vendors") or "").strip(),
                "unique_sites": (r.get("unique_sites") or "").strip(),
            }
        )

    vendor_json = json.dumps(vendor_slim)
    summary_json = json.dumps(summary_slim)
    realtime_json = json.dumps(realtime_snapshot)
    queue_points_json = json.dumps(queue_trend_points)
    team_data_json = json.dumps(team_dashboard_data)
    weekly_highlights_json = json.dumps(weekly_highlights_payload)
    correction_data_json = json.dumps(correction_entries or [])

    # NOTE: Avoid Python f-strings for large JS blobs (brace escaping hell).
    # We use placeholders + .replace() instead.
    template = """
<section class=\"section\" id=\"metrics\">
  <div class=\"section__head fade-up visible\">
    <div>
      <div class=\"eyebrow\">Survey performance</div>
      <h2>Survey Performance</h2>
    </div>
    <p>
      Data is refreshed by the pipeline and reflects PASS/FAIL outcomes only (ERROR excluded).\
      Time windows filter by <strong>processed_at</strong>.
    </p>
  </div>

  <div class=\"panel fade-up visible\">
    <div class=\"panel__inner\">
      <div class=\"panel__title\">
        <h3>Time window</h3>
        <span style=\"display:flex;align-items:center;gap:10px\">
          <span id=\"windowLabel\">Today</span>
          <span
            id=\"postPassPill\"
            hidden
            title=\"Unique sites where post-pass correction logic ran in this time window\"
            style=\"display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:999px;background:#ffc220;color:#1a0c00;font-size:0.75rem;font-weight:700;line-height:1;\"
            role=\"status\"
            aria-live=\"polite\"
          >✱ <span id=\"postPassPillCount\">0</span> post-pass site(s)</span>
          <button class=\"btn btn--secondary\" id=\"refreshNowBtn\" type=\"button\">Refresh now</button>
        </span>
      </div>

      <div style=\"display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between\">\n        <div style=\"display:flex;flex-direction:column;gap:10px\">\n          <div style=\"display:flex;flex-wrap:wrap;gap:10px\" role=\"tablist\" aria-label=\"Time window\">\n            <button class=\"btn btn--secondary\" data-window=\"today\" role=\"tab\">Today</button>\n            <button class=\"btn btn--secondary\" data-window=\"3d\" role=\"tab\">3 days</button>\n            <button class=\"btn btn--secondary\" data-window=\"7d\" role=\"tab\">7 days</button>\n            <button class=\"btn btn--secondary\" data-window=\"1m\" role=\"tab\">1 month</button>\n            <button class=\"btn btn--secondary\" data-window=\"3m\" role=\"tab\">3 months</button>\n            <button class=\"btn btn--secondary\" data-window=\"1y\" role=\"tab\">1 year</button>\n          </div>\n          <div style=\"display:flex;flex-wrap:wrap;gap:10px\" role=\"tablist\" aria-label=\"Vendor dimension\">\n            <button class=\"btn btn--primary\" data-dimension=\"vendor_name\" role=\"tab\" aria-selected=\"true\">Vendor</button>\n            <button class=\"btn btn--secondary\" data-dimension=\"vendor_email\" role=\"tab\" aria-selected=\"false\">Vendor email</button>\n          </div>\n        </div>\n\n        <div style=\"display:flex;flex-wrap:wrap;gap:10px\">\n          <label style=\"display:flex;align-items:center;gap:8px;color:var(--muted);font-size:0.85rem\">\n            <span id=\"vendorFilterLabel\">Vendor</span>\n            <select id=\"vendorFilter\" style=\"background:#000000;color:#ffffff;border:1px solid rgba(255,255,255,0.18);border-radius:999px;padding:8px 12px;min-width:220px;color-scheme:dark;\"></select>\n          </label>\n          <label style=\"display:flex;align-items:center;gap:8px;color:var(--muted);font-size:0.85rem\">\n            Site\n            <input id=\"siteSearch\" type=\"search\" placeholder=\"Search site #\" style=\"background:#000000;color:#ffffff;border:1px solid rgba(255,255,255,0.18);border-radius:999px;padding:8px 12px;min-width:220px;color-scheme:dark;\" />\n          </label>\n        </div>\n      </div>\n\n      <div class=\"mini-stats\" style=\"margin-top:16px\">
        <div class=\"mini-stat\"><span>All submissions</span><strong id=\"kpiAllSubmissions\">0</strong></div>
        <div class=\"mini-stat\"><span>Evaluated submissions</span><strong id=\"kpiEvaluated\">0</strong></div>
        <div class=\"mini-stat\"><span>PASS</span><strong id=\"kpiPass\">0</strong></div>
        <div class=\"mini-stat\"><span>FAIL</span><strong id=\"kpiFail\">0</strong></div>
        <div class=\"mini-stat\"><span>ERROR</span><strong id=\"kpiError\">0</strong></div>
        <div class=\"mini-stat\"><span>Overall pass rate</span><strong id=\"kpiPassRate\">0%</strong></div>
        <div class=\"mini-stat\"><span>Time study (avg / p95)</span><strong id=\"kpiTimeStudy\">—</strong></div>
      </div>
    </div>
  </div>

  <div class=\"ops-grid\" style=\"margin-top:18px\">
    <div class=\"panel fade-up visible\">
      <div class=\"panel__inner\">
        <div class=\"panel__title\">
          <h3>Vendor rollup</h3>
          <span>PASS/FAIL counts + pass rate + avg score</span>
        </div>
        <div style=\"border-radius:22px;border:1px solid rgba(255,255,255,0.06);background:linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));overflow:hidden\">
          <div id=\"vendorScroll\" style=\"max-height:520px;overflow:auto\" aria-label=\"Vendor rollup table\">
            <table style=\"width:100%;border-collapse:collapse\">
              <thead>
                <tr>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:left;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Vendor</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:left;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Email</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Total</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Pass</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Fail</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Pass %</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Avg score</th>
                </tr>
              </thead>
              <tbody id=\"vendorBody\"></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <div class=\"panel fade-up visible\">
      <div class=\"panel__inner\">
        <div class=\"panel__title\">
          <h3>Vendor + site rollup</h3>
          <span>Where issues cluster</span>
        </div>
        <div style=\"border-radius:22px;border:1px solid rgba(255,255,255,0.06);background:linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));overflow:hidden\">
          <div id=\"siteScroll\" style=\"max-height:520px;overflow:auto\" aria-label=\"Vendor site rollup table\">
            <table style=\"width:100%;border-collapse:collapse\">
              <thead>
                <tr>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:left;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Vendor</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:left;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Site</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Total</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Pass</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Fail</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Pass %</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Avg score</th>
                </tr>
              </thead>
              <tbody id=\"siteBody\"></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class=\"ops-grid\" style=\"margin-top:18px\"> 
    <div class=\"panel fade-up visible\"> 
      <div class=\"panel__inner\"> 
        <div class=\"panel__title\"> 
          <h3>Vendor metrics (detail)</h3>
          <span>Matches vendor_metrics.html (embedded)</span>
        </div>
        <div style=\"border-radius:22px;border:1px solid rgba(255,255,255,0.06);background:linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));overflow:hidden\"> 
          <div id=\"vendorDetailScroll\" style=\"max-height:520px;overflow:auto\" aria-label=\"Vendor detail table\"> 
            <table style=\"width:100%;border-collapse:collapse\"> 
              <thead>
                <tr>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:left;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Vendor</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:left;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Email</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Total</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Pass</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Fail</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Error</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Pass %</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Avg TA (s)</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:left;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Latest</th>
                </tr>
              </thead>
              <tbody id=\"vendorDetailBody\"></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <div class=\"panel fade-up visible\"> 
      <div class=\"panel__inner\"> 
        <div class=\"panel__title\"> 
          <h3>Processing summary (daily)</h3>
          <div class=\"panel-meta\">
            <span class=\"section-chip\">Embedded rollup</span>
            <span>Matches processing_summary.html (embedded)</span>
          </div>
        </div>
        <div style=\"border-radius:22px;border:1px solid rgba(255,255,255,0.06);background:linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));overflow:hidden\"> 
          <div id=\"dailySummaryScroll\" style=\"max-height:520px;overflow:auto\" aria-label=\"Daily summary table\"> 
            <table style=\"width:100%;border-collapse:collapse\"> 
              <thead>
                <tr>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:left;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Date</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Total</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Pass</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Fail</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Error</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Pass %</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Unique vendors</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Unique sites</th>
                </tr>
              </thead>
              <tbody id=\"dailySummaryBody\"></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<section class=\"section\" id=\"scout\">
  <div class=\"section__head fade-up visible\">
    <div>
      <div class=\"eyebrow\">Independent field operations</div>
      <h2>Scout</h2>
      <div style=\"margin-top:10px\">
        <span class=\"section-chip\" id=\"scoutTopPerformerPill\">Top performer: —</span>
      </div>
    </div>
    <p>
      Scout is rendered after leadership metrics so navigation order matches page order.
      It has independent cards, weekly production tracking, and a schema-authentic table.
    </p>
  </div>

  <div class=\"summary-grid\">
    <div class=\"summary-card fade-up visible\">
      <span>Scout total records</span>
      <strong id=\"scoutTotalRecords\">0</strong>
      <small>Live records returned from the Scout Airtable view.</small>
    </div>
    <div class=\"summary-card fade-up visible\">
      <span>Queued + processing</span>
      <strong id=\"scoutQueueCount\">0</strong>
      <small>Records currently in-flight by Scout status field.</small>
    </div>
    <div class=\"summary-card fade-up visible\">
      <span>Submitted today</span>
      <strong id=\"scoutSubmittedToday\">0</strong>
      <small>Based on Scout submitted date or Airtable created time fallback.</small>
    </div>
    <div class=\"summary-card fade-up visible\">
      <span>Configured</span>
      <strong id=\"scoutConfigured\">No</strong>
      <small>Confirms dedicated Scout Airtable connectivity.</small>
    </div>
    <div class=\"summary-card fade-up visible\">
      <span>Unique sites</span>
      <strong id=\"scoutUniqueSites\">0</strong>
      <small>Distinct Scout site values detected in live data.</small>
    </div>
  </div>

  <div class=\"ops-grid\" style=\"margin-top:18px\">
    <div class=\"panel fade-up visible\">
      <div class=\"panel__inner\">
        <div class=\"panel__title\">
          <h3>Scout weekly production</h3>
          <span>Submissions per Surveyor Parent Company by week</span>
        </div>
        <div id=\"scoutWeeklyMessage\" style=\"margin-bottom:16px;color:var(--muted);line-height:1.7\"></div>
        <div style=\"border-radius:22px;border:1px solid rgba(255,255,255,0.06);background:linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));overflow:hidden\">
          <div id=\"scoutWeeklyScroll\" style=\"max-height:420px;overflow:auto\" aria-label=\"Scout weekly production table\">
            <table style=\"width:100%;border-collapse:collapse\">
              <thead>
                <tr>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:left;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Week</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:left;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Surveyor Parent Company</th>
                  <th style=\"padding:8px 12px;background:rgba(255,255,255,0.04);color:var(--muted);text-align:right;position:sticky;top:0;z-index:2;border-bottom:1px solid rgba(255,255,255,0.08)\">Submissions</th>
                </tr>
              </thead>
              <tbody id=\"scoutWeeklyBody\"></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <div class=\"panel fade-up visible\">
      <div class=\"panel__inner\">
        <div class=\"panel__title\">
          <h3>Scout</h3>
          <span>Independent live Airtable feed</span>
        </div>
        <div id=\"scoutMessage\" style=\"margin-bottom:16px;color:var(--muted);line-height:1.7\"></div>
        <div style=\"border-radius:22px;border:1px solid rgba(255,255,255,0.06);background:linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));overflow:hidden\">
          <div id=\"scoutTableScroll\" style=\"max-height:520px;overflow:auto\" aria-label=\"Scout Airtable table\">
            <table style=\"width:100%;border-collapse:collapse\">
              <thead>
                <tr id=\"scoutTableHead\"></tr>
              </thead>
              <tbody id=\"scoutTableBody\"></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<section class=\"section\" id=\"weekly-highlights\">
  <div class=\"section__head fade-up visible\">
    <div>
      <div class=\"eyebrow\">Executive wrap-up</div>
      <h2>Weekly Highlights</h2>
    </div>
    <p>
      AI-style weekly highlights combine the Survey and Scout programs into one leadership-ready summary.
      This section is intentionally the final block on the page and includes a downloadable report.
    </p>
  </div>

  <div class=\"panel fade-up visible\">
    <div class=\"panel__inner\">
      <div class=\"panel__title\">
        <h3>Weekly Highlights</h3>
        <div class=\"panel-meta\">
          <span class=\"section-chip\">Leadership-ready handoff</span>
          <span>Combined Survey + Scout insight summary</span>
        </div>
      </div>
      <div style=\"display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:16px\">
        <div class=\"panel-meta\">
          <span class=\"section-chip\">Executive narrative</span>
          <span class=\"section-chip\">CSV export</span>
        </div>
        <button class=\"btn btn--secondary\" id=\"downloadWeeklyHighlightsBtn\" type=\"button\">Download CSV</button>
      </div>
      <div id=\"weeklyHighlightsContent\" style=\"color:var(--text);line-height:1.8\"></div>
    </div>
  </div>
</section>

  <script>
    (function () {{
      const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

      const raw = __DATA_JSON__;
      const vendorDetail = __VENDOR_DETAIL_JSON__;
      const dailySummary = __DAILY_SUMMARY_JSON__;
      const realtimeSnapshot = __REALTIME_SNAPSHOT_JSON__;
      const queueTrendPoints = __QUEUE_TREND_POINTS_JSON__;
      const teamDashboardData = __TEAM_DASHBOARD_DATA_JSON__;
      const weeklyHighlightsPayload = __WEEKLY_HIGHLIGHTS_JSON__;
      const correctionData = __CORRECTION_DATA_JSON__;

      function normalizeSurveyRecord(record) {
        const status = String(record && record.processing_status || '').trim().toUpperCase();
        return {
          vendor_email: String(record && record.vendor_email || '').trim(),
          vendor_name: String(record && record.vendor_name || '').trim(),
          site_number: String(record && record.site_number || '').trim(),
          processed_at: String(record && (record.submitted_at || record.created_time) || '').trim(),
          status,
          score: '',
          turnaround_seconds: '',
        };
      }

      const surveyPayload = teamDashboardData && teamDashboardData.survey ? teamDashboardData.survey : null;
      const surveyLiveRows = surveyPayload && Array.isArray(surveyPayload.records)
        ? surveyPayload.records.map(normalizeSurveyRecord).filter(r => ['PASS', 'FAIL', 'ERROR'].includes(r.status))
        : [];
      // Prefer live Survey data over archive when archive is empty/minimal
      const surveyPerformanceRows = surveyLiveRows.length > 0 ? surveyLiveRows : (Array.isArray(raw) ? raw : []);

      function parseIso(s) {{
        // processed_at is ISO with timezone. Date.parse handles it.
        const t = Date.parse(s);
        return Number.isFinite(t) ? t : null;
      }}

      function nowMs() {{ return Date.now(); }}

      function windowStartMs(key) {{
        const now = new Date();
        const n = nowMs();
        if (key === 'today') {{
          const start = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
          return start;
        }}
        if (key === '3d') return n - 3 * 24 * 60 * 60 * 1000;
        if (key === '7d') return n - 7 * 24 * 60 * 60 * 1000;
        if (key === '1m') {{ const d = new Date(now); d.setMonth(d.getMonth() - 1); return d.getTime(); }}
        if (key === '3m') {{ const d = new Date(now); d.setMonth(d.getMonth() - 3); return d.getTime(); }}
        if (key === '1y') {{ const d = new Date(now); d.setFullYear(d.getFullYear() - 1); return d.getTime(); }}
        return 0;
      }}

      let currentWindowKey = 'today';
      let currentDimensionKey = 'vendor_name';

      const vendorSelect = document.getElementById('vendorFilter');
      const vendorFilterLabel = document.getElementById('vendorFilterLabel');
      const siteSearch = document.getElementById('siteSearch');

      function activeDimensionKey() {
        return currentDimensionKey;
      }

      function dimensionDisplayName() {
        return activeDimensionKey() === 'vendor_email' ? 'Vendor email' : 'Vendor';
      }

      function dimensionValue(row) {
        if (activeDimensionKey() === 'vendor_email') {
          return (row.vendor_email || '').trim();
        }
        return (row.vendor_name || row.vendor_email || '').trim();
      }

      function selectedVendor() {{
        if (!vendorSelect) return '';
        return vendorSelect.value || '';
      }}

      function siteQuery() {{
        if (!siteSearch) return '';
        return (siteSearch.value || '').trim();
      }}

      function cleanRows(key) {{
        const start = windowStartMs(key);
        const vendor = selectedVendor();
        const q = siteQuery();

        const out = [];
        for (const r of surveyPerformanceRows) {{
          const status = String(r.status || '').toUpperCase();
          if (!['PASS', 'FAIL', 'ERROR'].includes(status)) continue;
          const t = parseIso(r.processed_at);
          if (t === null || t < start) continue;

          if (vendor && dimensionValue(r) !== vendor) continue;
          if (q && String(r.site_number || '').indexOf(q) === -1) continue;

          out.push({{
            vendor_email: r.vendor_email,
            vendor_name: r.vendor_name || r.vendor_email,
            site_number: r.site_number,
            status,
            score: r.score,
            turnaround_seconds: r.turnaround_seconds,
            t,
          }});
        }}
        return out;
      }}

      function toNum(x) {{
        const n = Number(x);
        return Number.isFinite(n) ? n : null;
      }}

      function normalizedScore(row) {{
        const status = String(row.status || '').toUpperCase();
        const rawScore = String(row.score ?? '').trim().toUpperCase();
        if (status === 'PASS' && (rawScore === '' || rawScore === 'PASS')) return 100;
        return toNum(row.score);
      }}

      function rollupVendor(rows) {{
        const m = new Map();
        for (const r of rows) {{
          const key = dimensionValue(r) || 'Unknown';
          const cur = m.get(key) || {{
            dimension_value: key,
            vendor_email: r.vendor_email,
            vendor_name: r.vendor_name,
            display_label: key,
            total: 0,
            pass: 0,
            fail: 0,
            scoreSum: 0,
            scoreN: 0,
          }};
          cur.total++;
          if (r.status === 'PASS') cur.pass++;
          else if (r.status === 'FAIL') cur.fail++;
          const sn = normalizedScore(r);
          if (sn !== null) {{ cur.scoreSum += sn; cur.scoreN++; }}
          m.set(key, cur);
        }}
        return [...m.values()].map(x => ({{
          ...x,
          passRate: x.total ? (x.pass / x.total) * 100 : 0,
          avgScore: x.scoreN ? (x.scoreSum / x.scoreN) : null,
        }})).sort((a,b) => (b.fail - a.fail) || (b.total - a.total));
      }}

      function rollupVendorSite(rows) {{
        const m = new Map();
        for (const r of rows) {{
          const dimension = dimensionValue(r) || 'Unknown';
          const k = dimension + '|' + (r.site_number || '');
          const cur = m.get(k) || {{
            dimension_value: dimension,
            vendor_name: r.vendor_name,
            vendor_email: r.vendor_email,
            display_label: dimension,
            site_number: r.site_number,
            total: 0,
            pass: 0,
            fail: 0,
            scoreSum: 0,
            scoreN: 0,
          }};
          cur.total++;
          if (r.status === 'PASS') cur.pass++;
          else if (r.status === 'FAIL') cur.fail++;
          const sn = normalizedScore(r);
          if (sn !== null) {{ cur.scoreSum += sn; cur.scoreN++; }}
          m.set(k, cur);
        }}
        return [...m.values()].map(x => ({{
          ...x,
          passRate: x.total ? (x.pass / x.total) * 100 : 0,
          avgScore: x.scoreN ? (x.scoreSum / x.scoreN) : null,
        }})).sort((a,b) => (b.fail - a.fail) || (b.total - a.total));
      }}

      function fmtPct(x) {{ return (Math.round(x * 10) / 10).toFixed(1) + '%'; }}
      function fmtScore(x) {{ return x === null ? '—' : (Math.round(x * 100) / 100).toFixed(2); }}

      function percentile(sorted, p) {{
        if (!sorted.length) return null;
        const idx = (sorted.length - 1) * p;
        const lo = Math.floor(idx);
        const hi = Math.ceil(idx);
        if (lo === hi) return sorted[lo];
        const w = idx - lo;
        return sorted[lo] * (1 - w) + sorted[hi] * w;
      }}

      function fmtSeconds(sec) {{
        if (sec === null) return '—';
        if (sec < 60) return Math.round(sec) + 's';
        if (sec < 3600) return (sec / 60).toFixed(1) + 'm';
        return (sec / 3600).toFixed(2) + 'h';
      }}

      function setText(id, text) {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
      }

      function topPerformingVendorLabel(rows) {
        const by = rollupVendor(rows).filter(r => r.total >= 5);
        if (!by.length) return '—';
        by.sort((a,b) => (b.passRate - a.passRate) || (b.total - a.total));
        return by[0].display_label || by[0].vendor_name || by[0].vendor_email;
      }

      function setKpis(rows) {
        const total = rows.length;
        const pass = rows.filter(r => r.status === 'PASS').length;
        const passRate = total ? (pass / total) * 100 : 0;

        const fail = rows.filter(r => r.status === 'FAIL').length;
        const error = rows.filter(r => r.status === 'ERROR').length;
        const evaluated = pass + fail;
        const tas = rows
          .filter(r => r.status === 'PASS' || r.status === 'FAIL')
          .map(r => toNum(r.turnaround_seconds))
          .filter(x => x !== null)
          .sort((a,b) => a - b);

        const avgTa = tas.length ? (tas.reduce((a,b)=>a+b,0) / tas.length) : null;
        const p95 = percentile(tas, 0.95);
        const timeStudy = avgTa === null ? '—' : (fmtSeconds(avgTa) + ' / ' + fmtSeconds(p95));

        setText('kpiAllSubmissions', String(total));
        setText('kpiEvaluated', String(evaluated));
        setText('kpiPass', String(pass));
        setText('kpiFail', String(fail));
        setText('kpiError', String(error));
        setText('kpiPassRate', fmtPct(passRate));
        setText('kpiTimeStudy', timeStudy);

        // Update hero KPIs in the executive template.
        setText('heroPassRate', fmtPct(passRate));
        setText('heroTimeStudy', timeStudy);
        setText('heroTopVendor', topPerformingVendorLabel(rows));

        // Executive summary cards still reflect evaluated records for top-level performance.
        setText('summaryTotal', String(evaluated));
        setText('summaryPass', String(pass));
        setText('summaryFail', String(fail));

        const sites = new Set(rows.map(r => String(r.site_number || '')).filter(Boolean));
        setText('summarySites', String(sites.size));
      }

      function rowStyleFromPassRate(passRate) {{
        if (passRate >= 95) return 'background: rgba(82,209,140,0.18)';
        if (passRate >= 80) return 'background: rgba(255,209,102,0.16)';
        return 'background: rgba(255,123,123,0.16)';
      }}

      function sumDailyInWindow(key) {
        const start = windowStartMs(key);
        let total = 0, pass = 0, fail = 0, error = 0;
        for (const r of dailySummary) {
          // dailySummary.date is YYYY-MM-DD
          const t = Date.parse(r.date + 'T00:00:00');
          if (!Number.isFinite(t) || t < start) continue;
          total += toNum(r.total) || 0;
          pass += toNum(r.pass) || 0;
          fail += toNum(r.fail) || 0;
          error += toNum(r.error) || 0;
        }
        return { total, pass, fail, error };
      }

      let runtimeAppState = {
        running: null,
        lastAction: '',
        polling: false,
        snapshot: null,
        snapshotAgeMinutes: null,
        rebuildInProgress: false,
        staleAfterMinutes: 15,
      };

      function setAppControlMessage(text) {
        const el = document.getElementById('appControlMessage');
        if (el) el.textContent = text;
      }

      function setAppControlBusy(isBusy) {
        const startBtn = document.getElementById('appStartBtn');
        const stopBtn = document.getElementById('appStopBtn');
        const rebuildBtn = document.getElementById('appRebuildBtn');
        if (startBtn) startBtn.dataset.busy = isBusy ? 'true' : 'false';
        if (stopBtn) stopBtn.dataset.busy = isBusy ? 'true' : 'false';
        if (rebuildBtn) rebuildBtn.dataset.busy = isBusy ? 'true' : 'false';
      }

      function syncAppControlButtons() {
        const startBtn = document.getElementById('appStartBtn');
        const stopBtn = document.getElementById('appStopBtn');
        const rebuildBtn = document.getElementById('appRebuildBtn');
        if (!startBtn || !stopBtn || !rebuildBtn) return;

        const running = runtimeAppState.running;
        const isBusy = runtimeAppState.polling === true;
        const isUnknown = running === null;
        const rebuildInProgress = runtimeAppState.rebuildInProgress === true;

        startBtn.disabled = isBusy || running === true;
        stopBtn.disabled = isBusy || running === false;
        rebuildBtn.disabled = isBusy || rebuildInProgress;

        startBtn.setAttribute('aria-pressed', running === true ? 'true' : 'false');
        stopBtn.setAttribute('aria-pressed', running === false ? 'true' : 'false');

        if (isUnknown) {
          startBtn.dataset.state = 'pending';
          stopBtn.dataset.state = 'pending';
          rebuildBtn.dataset.state = 'pending';
          startBtn.textContent = 'Checking status';
          stopBtn.textContent = 'Checking status';
          rebuildBtn.textContent = 'Checking rebuild';
          return;
        }

        delete startBtn.dataset.state;
        delete stopBtn.dataset.state;
        if (rebuildInProgress) {
          rebuildBtn.dataset.state = 'pending';
        } else {
          delete rebuildBtn.dataset.state;
        }
        startBtn.textContent = running === true ? 'App is on' : 'Turn app on';
        stopBtn.textContent = running === false ? 'App is off' : 'Turn app off';
        rebuildBtn.textContent = rebuildInProgress ? 'Reconnect / rebuild running' : 'Reconnect / rebuild now';
      }

      function updateAppStatusLight() {
        const light = document.getElementById('appStatusLight');
        const label = document.getElementById('appStatusLabel');
        const age = document.getElementById('appStatusAge');
        if (!light || !label || !age) return;

        const running = runtimeAppState.running;
        const snap = runtimeAppState.snapshot || realtimeSnapshot;
        const ageMinutes = Number.isFinite(runtimeAppState.snapshotAgeMinutes) ? runtimeAppState.snapshotAgeMinutes : null;

        if (running === false) {
          light.className = 'status-light status-light--offline';
          label.textContent = 'Off';
          age.textContent = runtimeAppState.lastAction || 'Process is not running';
          return;
        }

        if (running === true) {
          light.className = 'status-light status-light--online';
          label.textContent = 'On';

          if (!snap || !snap.generated_at_utc) {
            age.textContent = 'App is on. Waiting for live realtime snapshot.';
            return;
          }

          if (ageMinutes === null) {
            age.textContent = 'App is on. Realtime snapshot timestamp invalid.';
            return;
          }

          age.textContent = ageMinutes === 0
            ? 'Realtime snapshot just updated'
            : `App is on. Realtime snapshot ${ageMinutes} min ago`;
          return;
        }

        light.className = 'status-light status-light--stale';
        label.textContent = 'Checking';

        if (!snap || !snap.generated_at_utc) {
          age.textContent = 'Waiting for live realtime snapshot';
          return;
        }

        if (ageMinutes === null) {
          age.textContent = 'Realtime snapshot timestamp invalid';
          return;
        }

        age.textContent = ageMinutes === 0
          ? 'Realtime snapshot just updated'
          : `Realtime snapshot ${ageMinutes} min ago`;
      }

      function updateLastSyncInfo() {
        const el = document.getElementById('appLastSyncValue');
        if (!el) return;

        const snap = runtimeAppState.snapshot || realtimeSnapshot;
        const ageMinutes = Number.isFinite(runtimeAppState.snapshotAgeMinutes) ? runtimeAppState.snapshotAgeMinutes : null;
        const staleAfter = Number.isFinite(runtimeAppState.staleAfterMinutes) ? runtimeAppState.staleAfterMinutes : 15;

        if (!snap || !snap.generated_at_utc) {
          el.textContent = 'Waiting for first successful sync';
          return;
        }
        if (ageMinutes === null) {
          el.textContent = 'Timestamp unavailable';
          return;
        }
        if (runtimeAppState.rebuildInProgress === true) {
          el.textContent = ageMinutes === 0
            ? `Just now • reconnecting live data`
            : `${ageMinutes} min ago • reconnecting live data`;
          return;
        }
        if (ageMinutes >= staleAfter) {
          el.textContent = `${ageMinutes} min ago • stale threshold ${staleAfter} min`;
          return;
        }
        el.textContent = ageMinutes === 0 ? 'Just now' : `${ageMinutes} min ago`;
      }

      function renderAdminHealth() {
        const cards = document.getElementById('adminHealthCards');
        const warnings = document.getElementById('adminWarningList');
        if (!cards || !warnings) return;

        const running = runtimeAppState.running;
        const ageMinutes = Number.isFinite(runtimeAppState.snapshotAgeMinutes) ? runtimeAppState.snapshotAgeMinutes : null;
        const staleAfter = Number.isFinite(runtimeAppState.staleAfterMinutes) ? runtimeAppState.staleAfterMinutes : 15;
        const rebuildInProgress = runtimeAppState.rebuildInProgress === true;

        let runtimeLabel = 'Checking';
        let runtimeNote = 'Waiting for runtime state from localhost control service.';
        if (running === true) {
          runtimeLabel = 'Running';
          runtimeNote = 'The background process is on and controllable from this dashboard.';
        } else if (running === false) {
          runtimeLabel = 'Stopped';
          runtimeNote = 'The background process is off. Turn it on before expecting fresh Airtable syncs.';
        }

        let syncLabel = 'Unknown';
        let syncNote = 'No valid Airtable sync timestamp is available yet.';
        if (ageMinutes !== null) {
          syncLabel = ageMinutes >= staleAfter ? 'Stale' : 'Fresh';
          syncNote = ageMinutes === 0
            ? 'Last Airtable sync landed just now.'
            : `Last Airtable sync landed ${ageMinutes} minute${ageMinutes === 1 ? '' : 's'} ago.`;
        }
        if (rebuildInProgress) {
          syncLabel = 'Recovering';
          syncNote = 'Reconnect / rebuild is in progress right now.';
        }

        let actionLabel = 'Monitor';
        let actionNote = 'No immediate operator action is recommended.';
        if (running === false) {
          actionLabel = 'Turn app on';
          actionNote = 'Runtime is off, so nothing upstream will refresh until the app is started.';
        } else if (rebuildInProgress) {
          actionLabel = 'Wait for rebuild';
          actionNote = 'Avoid hammering the reconnect button while a rebuild is already running.';
        } else if (ageMinutes === null) {
          actionLabel = 'Reconnect / rebuild';
          actionNote = 'Airtable sync timestamp is missing or invalid, so force a reconnect and watch for fresh data.';
        } else if (ageMinutes >= staleAfter) {
          actionLabel = 'Reconnect / rebuild';
          actionNote = `Sync age has crossed the ${staleAfter}-minute stale threshold.`;
        }

        cards.innerHTML = [
          `<div class="admin-health-card"><span>Runtime</span><strong>${runtimeLabel}</strong><small>${runtimeNote}</small></div>`,
          `<div class="admin-health-card"><span>Live sync</span><strong>${syncLabel}</strong><small>${syncNote}</small></div>`,
          `<div class="admin-health-card"><span>Recommended action</span><strong>${actionLabel}</strong><small>${actionNote}</small></div>`,
        ].join('');

        const warningItems = [];
        if (running === false) {
          warningItems.push({ tone: 'bad', title: 'App is off', body: 'Turn the app on from this Admin tab before expecting queue intake, scoring, or Airtable freshness.' });
        }
        if (rebuildInProgress) {
          warningItems.push({ tone: 'warn', title: 'Reconnect / rebuild in progress', body: 'Freshness maintenance is already running. Let it finish before mashing buttons like a raccoon on espresso.' });
        }
        if (ageMinutes === null) {
          warningItems.push({ tone: running === true ? 'warn' : 'bad', title: 'Airtable sync timestamp unavailable', body: 'The dashboard cannot confirm the most recent successful Airtable sync yet. Use reconnect / rebuild when the app is running.' });
        } else if (ageMinutes >= staleAfter) {
          warningItems.push({ tone: 'warn', title: 'Airtable sync is stale', body: `Latest successful Airtable sync is ${ageMinutes} minutes old, which exceeds the ${staleAfter}-minute threshold.` });
        } else {
          warningItems.push({ tone: 'good', title: 'Health is within recommended range', body: 'Runtime is controllable and the latest Airtable sync is still within the recommended freshness window.' });
        }

        warnings.innerHTML = warningItems.map((item) => (
          `<div class="admin-warning-item admin-warning-item--${item.tone}"><strong>${item.title}</strong><span>${item.body}</span></div>`
        )).join('');
      }

      async function refreshRuntimeAppStatus() {
        runtimeAppState.polling = true;
        syncAppControlButtons();
        try {
          const resp = await fetch('/api/app/status', { cache: 'no-store' });
          if (!resp.ok) throw new Error(`status ${resp.status}`);
          const data = await resp.json();
          runtimeAppState.running = data.running === true;
          runtimeAppState.snapshot = data.snapshot || null;
          runtimeAppState.snapshotAgeMinutes = Number.isFinite(data.snapshot_age_minutes) ? data.snapshot_age_minutes : null;
          runtimeAppState.rebuildInProgress = data.rebuild_in_progress === true;
          runtimeAppState.staleAfterMinutes = Number.isFinite(data.stale_after_minutes) ? data.stale_after_minutes : 15;
          syncAppControlButtons();
          updateAppStatusLight();
          updateLastSyncInfo();
          renderAdminHealth();
          return data;
        } catch (err) {
          runtimeAppState.running = null;
          runtimeAppState.snapshot = null;
          runtimeAppState.snapshotAgeMinutes = null;
          runtimeAppState.rebuildInProgress = false;
          syncAppControlButtons();
          updateAppStatusLight();
          updateLastSyncInfo();
          renderAdminHealth();
          setAppControlMessage('Dashboard control status unavailable right now.');
          return null;
        } finally {
          runtimeAppState.polling = false;
          syncAppControlButtons();
        }
      }

      async function requestReconnectRebuild() {
        runtimeAppState.polling = true;
        setAppControlBusy(true);
        syncAppControlButtons();
        setAppControlMessage('Requesting Airtable reconnect and dashboard rebuild…');
        try {
          const resp = await fetch('/api/app/rebuild', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: '{}',
          });
          const data = await resp.json();
          if (!resp.ok || data.ok === false) {
            throw new Error(data.stderr || data.error || 'rebuild failed');
          }
          runtimeAppState.rebuildInProgress = data.rebuild_in_progress === true;
          runtimeAppState.snapshot = data.snapshot || runtimeAppState.snapshot;
          runtimeAppState.snapshotAgeMinutes = Number.isFinite(data.snapshot_age_minutes) ? data.snapshot_age_minutes : runtimeAppState.snapshotAgeMinutes;
          runtimeAppState.staleAfterMinutes = Number.isFinite(data.stale_after_minutes) ? data.stale_after_minutes : runtimeAppState.staleAfterMinutes;
          syncAppControlButtons();
          updateAppStatusLight();
          updateLastSyncInfo();
          renderAdminHealth();
          setAppControlMessage('Reconnect / rebuild requested. The dashboard will keep polling until fresh data lands.');
          return data;
        } catch (err) {
          setAppControlMessage(`Could not rebuild live data: ${err.message}`);
          throw err;
        } finally {
          setAppControlBusy(false);
          runtimeAppState.polling = false;
          syncAppControlButtons();
          await refreshRuntimeAppStatus();
        }
      }

      async function postAppControl(action) {
        const verb = action === 'start' ? 'Starting' : 'Stopping';
        runtimeAppState.polling = true;
        setAppControlBusy(true);
        syncAppControlButtons();
        setAppControlMessage(`${verb} app…`);
        try {
          const resp = await fetch(`/api/app/${action}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: '{}',
          });
          const data = await resp.json();
          if (!resp.ok || data.ok === false) {
            throw new Error(data.stderr || data.error || `${action} failed`);
          }
          runtimeAppState.running = data.running === true;
          runtimeAppState.snapshot = data.snapshot || null;
          runtimeAppState.snapshotAgeMinutes = Number.isFinite(data.snapshot_age_minutes) ? data.snapshot_age_minutes : null;
          runtimeAppState.rebuildInProgress = data.rebuild_in_progress === true;
          runtimeAppState.staleAfterMinutes = Number.isFinite(data.stale_after_minutes) ? data.stale_after_minutes : runtimeAppState.staleAfterMinutes;
          runtimeAppState.lastAction = action === 'start' ? 'Start requested from dashboard' : 'Stop requested from dashboard';
          syncAppControlButtons();
          updateAppStatusLight();
          updateLastSyncInfo();
          renderAdminHealth();
          setAppControlMessage(action === 'start' ? 'App power on requested. Live data refresh kicked off.' : 'App power off requested.');
          return data;
        } catch (err) {
          setAppControlMessage(`Could not ${action} app: ${err.message}`);
          throw err;
        } finally {
          setAppControlBusy(false);
          runtimeAppState.polling = false;
          syncAppControlButtons();
          await refreshRuntimeAppStatus();
        }
      }

      function wireAppControls() {
        const startBtn = document.getElementById('appStartBtn');
        const stopBtn = document.getElementById('appStopBtn');
        const rebuildBtn = document.getElementById('appRebuildBtn');
        if (startBtn) {
          startBtn.addEventListener('click', () => { void postAppControl('start'); });
        }
        if (stopBtn) {
          stopBtn.addEventListener('click', () => { void postAppControl('stop'); });
        }
        if (rebuildBtn) {
          rebuildBtn.addEventListener('click', () => { void requestReconnectRebuild(); });
        }
        syncAppControlButtons();
        updateLastSyncInfo();
        renderAdminHealth();
        // On page load: check status and auto-start the pipeline if it is off.
        // This ensures the app is always on when the dashboard opens via the launcher.
        void (async () => {
          const data = await refreshRuntimeAppStatus();
          if (data && data.running === false) {
            setAppControlMessage('App was off — starting automatically…');
            void postAppControl('start');
          }
        })();
        window.setInterval(() => { void refreshRuntimeAppStatus(); }, 15000);
      }

      function initRealtimeSnapshot() {
        const snap = realtimeSnapshot;
        if (!snap) {
          setText('heroQueued', '—');
          setText('queueActive', '—');
          updateAppStatusLight();
          return;
        }
        const queued = (snap.queued_count || 0) + (snap.processing_count || 0);
        setText('heroQueued', String(queued));
        setText('queueActive', String(snap.processing_count || 0));
        updateAppStatusLight();
      }

      function renderQueueSvg(points) {
        // points: [{label, total}]
        const svg = document.getElementById('queueSvg');
        const line = document.getElementById('queueLinePath');
        const fill = document.getElementById('queueFillPath');
        const dots = document.getElementById('queueDots');
        const labels = document.getElementById('queueLabels');
        if (!svg || !line || !fill || !dots || !labels) return;

        const w = 480, h = 240;
        const padTop = 24;
        const padBot = 24;
        const max = Math.max(...points.map(p => p.total), 1);
        const step = points.length > 1 ? (w / (points.length - 1)) : w;

        const coords = points.map((p, i) => {
          const x = i * step;
          const y = padTop + (h - padTop - padBot) * (1 - (p.total / max));
          return { x, y, total: p.total };
        });

        const dLine = coords.map((c, i) => (i === 0 ? 'M' : 'L') + c.x.toFixed(1) + ' ' + c.y.toFixed(1)).join(' ');
        const dFill = dLine + ' L' + w + ' ' + h + ' L0 ' + h + ' Z';

        line.setAttribute('d', dLine);
        fill.setAttribute('d', dFill);

        dots.textContent = '';
        for (const c of coords) {
          const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
          circle.setAttribute('cx', String(c.x));
          circle.setAttribute('cy', String(c.y));
          circle.setAttribute('r', '4');
          dots.appendChild(circle);
        }

        labels.textContent = '';
        for (const p of points) {
          const span = document.createElement('span');
          span.textContent = p.label;
          labels.appendChild(span);
        }

        setText('queuePeak', String(Math.max(...points.map(p => p.total), 0)));
      }

      function initQueueTrend() {
        const points = Array.isArray(queueTrendPoints) ? queueTrendPoints : [];
        if (!points.length) {
          setText('queuePeak', '—');
          return;
        }
        renderQueueSvg(points);
      }

      function teamPayload(teamKey) {
        return teamDashboardData && teamDashboardData[teamKey] ? teamDashboardData[teamKey] : null;
      }

      function scoutTimestampMs(record) {
        const candidates = [record && record.submitted_at, record && record.created_time];
        for (const value of candidates) {
          const t = Date.parse(String(value || ''));
          if (Number.isFinite(t)) return t;
        }
        return null;
      }

      function startOfWeekMs(ts) {
        const d = new Date(ts);
        const day = d.getDay();
        const diff = day === 0 ? -6 : 1 - day;
        d.setHours(0, 0, 0, 0);
        d.setDate(d.getDate() + diff);
        return d.getTime();
      }

      function fmtDateShort(ts) {
        return new Date(ts).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
      }

      function weekLabelFromTs(ts) {
        const start = startOfWeekMs(ts);
        const end = start + 6 * 24 * 60 * 60 * 1000;
        return fmtDateShort(start) + ' - ' + fmtDateShort(end);
      }

      function scoutParentCompany(record) {
        const raw = record && record.raw_fields ? record.raw_fields : {};
        return String(raw['Surveyor Parent Company'] || raw['Parent Company'] || raw['Surveyor Company'] || 'Unknown').trim() || 'Unknown';
      }

      function buildScoutWeeklyRows(records) {
        const rollups = new Map();
        for (const record of records) {
          const ts = scoutTimestampMs(record);
          if (ts === null) continue;
          const weekStart = startOfWeekMs(ts);
          const company = scoutParentCompany(record);
          const key = weekStart + '|' + company;
          const cur = rollups.get(key) || { weekStart, company, submissions: 0 };
          cur.submissions += 1;
          rollups.set(key, cur);
        }
        return [...rollups.values()].sort((a, b) => b.weekStart - a.weekStart || b.submissions - a.submissions || a.company.localeCompare(b.company));
      }

      function scoutTopPerformer(records) {
        const rollups = new Map();
        for (const record of records) {
          const company = scoutParentCompany(record);
          const ts = scoutTimestampMs(record);
          const cur = rollups.get(company) || { company, submissions: 0, latestTs: 0 };
          cur.submissions += 1;
          if (ts !== null) cur.latestTs = Math.max(cur.latestTs, ts);
          rollups.set(company, cur);
        }

        const ranked = [...rollups.values()].sort((a, b) =>
          (b.submissions - a.submissions) ||
          (b.latestTs - a.latestTs) ||
          a.company.localeCompare(b.company)
        );

        return ranked.length ? ranked[0] : null;
      }

      function renderScoutTopPerformer(records, configured) {
        const el = document.getElementById('scoutTopPerformerPill');
        if (!el) return;

        if (!configured) {
          el.textContent = 'Top performer: Not configured';
          return;
        }

        const top = scoutTopPerformer(records);
        if (!top) {
          el.textContent = 'Top performer: —';
          return;
        }

        const submissionLabel = top.submissions === 1 ? 'submission' : 'submissions';
        el.textContent = `Top performer: ${top.company} (${top.submissions} ${submissionLabel})`;
      }

      function renderScoutWeeklyProduction(records, configured) {
        const body = document.getElementById('scoutWeeklyBody');
        const msg = document.getElementById('scoutWeeklyMessage');
        if (!body || !msg) return;

        body.textContent = '';
        const rows = buildScoutWeeklyRows(records);

        if (!configured) {
          msg.textContent = 'Scout is not configured, so weekly production by Surveyor Parent Company is unavailable.';
        } else if (!rows.length) {
          msg.textContent = 'Scout is configured, but there are no weekly production rows yet.';
        } else {
          msg.textContent = 'Weekly submission volume grouped by Surveyor Parent Company so you can see who is actually carrying load instead of just attending meetings.';
        }

        const frag = document.createDocumentFragment();
        for (const row of rows) {
          const tr = document.createElement('tr');
          for (const cell of [weekLabelFromTs(row.weekStart), row.company, String(row.submissions)]) {
            const td = document.createElement('td');
            td.textContent = cell;
            td.style.padding = '6px 12px';
            td.style.borderBottom = '1px solid rgba(255,255,255,0.08)';
            td.style.color = 'var(--text)';
            td.style.textAlign = /^[0-9]+$/.test(cell) ? 'right' : 'left';
            tr.appendChild(td);
          }
          frag.appendChild(tr);
        }

        if (!rows.length) {
          const tr = document.createElement('tr');
          const td = document.createElement('td');
          td.colSpan = 3;
          td.textContent = configured ? 'No weekly Scout production data available.' : 'Not configured.';
          td.style.padding = '14px 12px';
          td.style.color = 'var(--muted)';
          tr.appendChild(td);
          frag.appendChild(tr);
        }

        body.appendChild(frag);
      }

      function escapeHtml(value) {
        return String(value ?? '')
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;')
          .replace(/'/g, '&#39;');
      }

      function weeklyTable(headers, rows, opts = {}) {
        const alignRight = new Set(opts.alignRight || []);
        const dense = opts.dense ? 'font-size:0.86rem;' : '';
        return `
          <div style="border-radius:18px;border:1px solid rgba(255,255,255,0.08);overflow:hidden;background:rgba(255,255,255,0.02)">
            <div style="overflow:auto">
              <table style="width:100%;border-collapse:collapse;${dense}">
                <thead>
                  <tr>
                    ${headers.map((h, i) => `<th style="padding:12px 14px;background:rgba(0,83,226,0.14);color:#ffffff;text-align:${alignRight.has(i) ? 'right' : 'left'};border-bottom:1px solid rgba(255,255,255,0.08);font-weight:700">${escapeHtml(h)}</th>`).join('')}
                  </tr>
                </thead>
                <tbody>
                  ${rows.map(row => `
                    <tr>
                      ${row.map((cell, i) => `<td style="padding:11px 14px;border-bottom:1px solid rgba(255,255,255,0.06);text-align:${alignRight.has(i) ? 'right' : 'left'};color:var(--text)">${escapeHtml(cell)}</td>`).join('')}
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>
        `;
      }

      function weeklyStatusBadge(status, trend) {
        const map = {
          GREEN: { bg: 'rgba(42,135,3,0.16)', border: 'rgba(42,135,3,0.45)', text: '#8fdb76' },
          YELLOW: { bg: 'rgba(255,194,32,0.14)', border: 'rgba(255,194,32,0.45)', text: '#ffd86b' },
          RED: { bg: 'rgba(234,17,0,0.14)', border: 'rgba(234,17,0,0.45)', text: '#ff8f85' },
        };
        const tone = map[status] || map.YELLOW;
        return `<span style="display:inline-flex;align-items:center;gap:8px;padding:6px 10px;border-radius:999px;border:1px solid ${tone.border};background:${tone.bg};color:${tone.text};font-weight:700;font-size:0.82rem">${escapeHtml(trend)} ${escapeHtml(status)}</span>`;
      }

      function weeklyKpiCards(kpis) {
        return `
          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px">
            ${Object.entries(kpis || {}).map(([name, vals]) => `
              <div style="padding:16px;border-radius:18px;border:1px solid rgba(255,255,255,0.08);background:linear-gradient(180deg, rgba(0,83,226,0.12), rgba(255,255,255,0.03))">
                <div style="font-size:0.82rem;color:var(--muted);margin-bottom:8px">${escapeHtml(name)}</div>
                <div style="display:flex;align-items:baseline;justify-content:space-between;gap:12px">
                  <strong style="font-size:1.45rem;color:#ffffff">${escapeHtml(vals.current)}</strong>
                  <span style="color:var(--muted);font-size:0.82rem">${escapeHtml(vals.change)}</span>
                </div>
                <div style="margin-top:8px;color:var(--muted);font-size:0.82rem">Prev: ${escapeHtml(vals.previous)}</div>
              </div>
            `).join('')}
          </div>
        `;
      }

      function reportSection(title, body) {
        return `
          <section style="display:flex;flex-direction:column;gap:12px;margin-top:22px">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:12px">
              <h4 style="margin:0;font-size:1.02rem;color:#ffffff">${escapeHtml(title)}</h4>
            </div>
            ${body}
          </section>
        `;
      }

      function buildWeeklyHighlightsMarkup(reportData, reportText, llmEnabled) {
        const headerRows = [
          ['Reporting Period', reportData.reporting_period || '[not available]'],
          ['Program Owner', reportData.program_owner || '[not available]'],
          ['Dashboard Source', reportData.dashboard_source || '[not available]'],
          ['Generation Mode', llmEnabled ? 'Element LLM generated' : 'Structured dashboard fallback'],
        ];

        const healthRows = Object.entries(reportData.health || {}).map(([name, item]) => [
          name,
          item.status || '[not available]',
          item.trend || '[not available]'
        ]);

        const leaderboardRows = (reportData.leaderboard || []).map((row, idx) => [
          String(idx + 1),
          row.vendor || '[vendor]',
          row.surveys_completed || '[not available]',
          row.avg_completion_time || '[not available]',
          row.qa_pass_rate || '[not available]',
          row.vendor_score || '[not available]',
        ]);

        const scorecardRows = (reportData.scorecard || []).map((row) => [
          row.vendor || '[vendor]',
          row.surveys_submitted || '[not available]',
          row.approval_rate || '[not available]',
          row.avg_completion_time || '[not available]',
          row.productivity_score || '[not available]',
        ]);

        const productionRows = Object.entries(reportData.production_metrics || {}).map(([name, item]) => [
          name,
          item.count || '[not available]',
          item.distribution || '[not available]',
        ]);

        const velocityRows = Object.entries(reportData.velocity_metrics || {}).map(([name, item]) => [
          name,
          item.current || '[not available]',
          item.previous || '[not available]',
          item.change || '[not available]',
        ]);

        const trendRows = (reportData.rolling_trend || []).map((row) => [
          row.week || '[week]',
          row.submitted || '[not available]',
          row.approved || '[not available]',
          row.vendor_productivity || '[not available]',
          row.qa_pass_rate || '[not available]',
          row.avg_completion_time || '[not available]',
        ]);

        const insights = (reportData.insights || []).map((item, idx) => `
          <li style="margin:0;padding:0;color:var(--text)"><strong style="color:#ffffff">${idx + 1}.</strong> ${escapeHtml(item)}</li>
        `).join('');

        const healthCards = Object.entries(reportData.health || {}).map(([name, item]) => `
          <div style="padding:16px;border-radius:18px;border:1px solid rgba(255,255,255,0.08);background:rgba(255,255,255,0.02)">
            <div style="font-size:0.82rem;color:var(--muted);margin-bottom:10px">${escapeHtml(name)}</div>
            ${weeklyStatusBadge(item.status, item.trend)}
          </div>
        `).join('');

        return `
          <div id="weeklyHighlightsReport" style="display:flex;flex-direction:column;gap:20px">
            <div style="padding:22px;border-radius:22px;border:1px solid rgba(255,255,255,0.08);background:linear-gradient(135deg, rgba(0,83,226,0.16), rgba(255,194,32,0.08) 70%, rgba(255,255,255,0.03))">
              <div style="display:flex;flex-wrap:wrap;align-items:flex-start;justify-content:space-between;gap:18px">
                <div>
                  <div style="font-size:0.8rem;letter-spacing:0.18em;text-transform:uppercase;color:var(--muted);margin-bottom:10px">Executive operations report</div>
                  <h3 style="margin:0 0 10px 0;font-size:1.45rem;color:#ffffff">${escapeHtml(reportData.title || 'Weekly Highlights')}</h3>
                  <p style="margin:0;color:var(--text);max-width:760px">Leadership-ready weekly operating view across survey throughput, vendor performance, quality, and cycle time signals.</p>
                </div>
                <div style="padding:12px 14px;border-radius:16px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);min-width:220px">
                  <div style="font-size:0.78rem;color:var(--muted);margin-bottom:4px">Report mode</div>
                  <strong style="color:#ffffff">${llmEnabled ? 'Element LLM' : 'Dashboard fallback'}</strong>
                </div>
              </div>
            </div>

            ${reportSection('Reporting Header', weeklyTable(['Field', 'Value'], headerRows))}
            ${reportSection('Executive KPI Dashboard', weeklyKpiCards(reportData.kpis || {}))}
            ${reportSection('Program Health Indicators', `
              <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px">${healthCards}</div>
              <div style="margin-top:8px">${weeklyTable(['Indicator', 'Status', 'Trend'], healthRows)}</div>
            `)}
            ${reportSection('Top 5 Operational Insights', `<ol style="margin:0;padding-left:20px;display:flex;flex-direction:column;gap:10px">${insights}</ol>`)}
            ${reportSection('Vendor Performance Leaderboard', weeklyTable(['Rank', 'Vendor', 'Surveys Completed', 'Avg Completion Time', 'QA Pass Rate', 'Vendor Score'], leaderboardRows.length ? leaderboardRows : [['[rank]','[vendor]','[not available]','[not available]','[not available]','[not available]']], { alignRight: [0,2,5] }))}
            ${reportSection('Vendor Performance Scorecard', weeklyTable(['Vendor', 'Surveys Submitted', 'Approval Rate', 'Avg Completion Time', 'Productivity Score'], scorecardRows.length ? scorecardRows : [['[vendor]','[not available]','[not available]','[not available]','[not available]']], { alignRight: [1,4] }))}
            ${reportSection('Survey Production Metrics', weeklyTable(['Metric', 'Count', 'Distribution'], productionRows, { alignRight: [1,2] }))}
            ${reportSection('Survey Velocity Metrics', weeklyTable(['Metric', 'Current', 'Previous', 'Change %'], velocityRows, { alignRight: [1,2,3] }))}
            ${reportSection('Rolling 4 Week Performance Trend', weeklyTable(['Week', 'Total Surveys Submitted', 'Total Surveys Approved', 'Vendor Productivity', 'QA Pass Rate', 'Average Completion Time'], trendRows, { alignRight: [1,2,3,4,5], dense: true }))}
            ${reportSection('Dashboard Performance Metrics Summary', `<div style="padding:16px;border-radius:18px;border:1px solid rgba(255,255,255,0.08);background:rgba(255,255,255,0.02);color:var(--text)">${escapeHtml(reportData.dashboard_summary || reportText || 'Weekly Highlights unavailable.')}</div>`)}
            ${reportSection('Operational Outlook', `<div style="padding:16px;border-radius:18px;border:1px solid rgba(255,255,255,0.08);background:rgba(255,255,255,0.02);color:var(--text)">${escapeHtml(reportData.operational_outlook || reportText || 'Weekly Highlights unavailable.')}</div>`)}
          </div>
        `;
      }

      function csvEscape(value) {
        const text = String(value ?? '');
        return '"' + text.replace(/"/g, '""') + '"';
      }

      function csvSection(lines, title, headers, rows) {
        lines.push([title]);
        if (headers && headers.length) lines.push(headers);
        rows.forEach(row => lines.push(row));
        lines.push([]);
      }

      function buildWeeklyHighlightsCsv(reportData, reportText, llmEnabled) {
        const lines = [];
        const generatedAt = new Date().toLocaleString();
        lines.push(['Leadership Handoff']);
        lines.push([reportData.title || 'Weekly Highlights']);
        lines.push([]);
        lines.push(['Report Field', 'Value']);
        lines.push(['Generated At', generatedAt]);
        lines.push(['Reporting Period', reportData.reporting_period || '[not available]']);
        lines.push(['Program Owner', reportData.program_owner || '[not available]']);
        lines.push(['Dashboard Source', reportData.dashboard_source || '[not available]']);
        lines.push(['Generation Mode', llmEnabled ? 'Element LLM generated' : 'Structured dashboard fallback']);
        lines.push([]);
        lines.push(['Executive Handoff Summary']);
        lines.push(['Summary', reportData.dashboard_summary || reportText || 'Weekly Highlights unavailable.']);
        lines.push(['Operational Outlook', reportData.operational_outlook || reportText || 'Weekly Highlights unavailable.']);
        lines.push([]);

        csvSection(lines, 'Reporting Header', ['Field', 'Value'], [
          ['Reporting Period', reportData.reporting_period || '[not available]'],
          ['Program Owner', reportData.program_owner || '[not available]'],
          ['Dashboard Source', reportData.dashboard_source || '[not available]'],
          ['Generation Mode', llmEnabled ? 'Element LLM generated' : 'Structured dashboard fallback'],
        ]);

        csvSection(lines, 'Executive KPI Dashboard', ['Metric', 'Current', 'Previous', 'WoW Change'],
          Object.entries(reportData.kpis || {}).map(([name, vals]) => [name, vals.current || '[not available]', vals.previous || '[not available]', vals.change || '[not available]'])
        );

        csvSection(lines, 'Program Health Indicators', ['Indicator', 'Status', 'Trend'],
          Object.entries(reportData.health || {}).map(([name, item]) => [name, item.status || '[not available]', item.trend || '[not available]'])
        );

        csvSection(lines, 'Top 5 Operational Insights', ['#', 'Insight'],
          (reportData.insights || []).map((item, idx) => [String(idx + 1), item])
        );

        csvSection(lines, 'Vendor Performance Leaderboard', ['Rank', 'Vendor', 'Surveys Completed', 'Avg Completion Time', 'QA Pass Rate', 'Vendor Score'],
          (reportData.leaderboard || []).map((row, idx) => [String(idx + 1), row.vendor || '[vendor]', row.surveys_completed || '[not available]', row.avg_completion_time || '[not available]', row.qa_pass_rate || '[not available]', row.vendor_score || '[not available]'])
        );

        csvSection(lines, 'Vendor Performance Scorecard', ['Vendor', 'Surveys Submitted', 'Approval Rate', 'Avg Completion Time', 'Productivity Score'],
          (reportData.scorecard || []).map((row) => [row.vendor || '[vendor]', row.surveys_submitted || '[not available]', row.approval_rate || '[not available]', row.avg_completion_time || '[not available]', row.productivity_score || '[not available]'])
        );

        csvSection(lines, 'Survey Production Metrics', ['Metric', 'Count', 'Distribution'],
          Object.entries(reportData.production_metrics || {}).map(([name, item]) => [name, item.count || '[not available]', item.distribution || '[not available]'])
        );

        csvSection(lines, 'Survey Velocity Metrics', ['Metric', 'Current', 'Previous', 'Change %'],
          Object.entries(reportData.velocity_metrics || {}).map(([name, item]) => [name, item.current || '[not available]', item.previous || '[not available]', item.change || '[not available]'])
        );

        csvSection(lines, 'Rolling 4 Week Performance Trend', ['Week', 'Total Surveys Submitted', 'Total Surveys Approved', 'Vendor Productivity', 'QA Pass Rate', 'Average Completion Time'],
          (reportData.rolling_trend || []).map((row) => [row.week || '[week]', row.submitted || '[not available]', row.approved || '[not available]', row.vendor_productivity || '[not available]', row.qa_pass_rate || '[not available]', row.avg_completion_time || '[not available]'])
        );

        csvSection(lines, 'Dashboard Performance Metrics Summary', ['Summary'], [[reportData.dashboard_summary || reportText || 'Weekly Highlights unavailable.']]);
        csvSection(lines, 'Operational Outlook', ['Outlook'], [[reportData.operational_outlook || reportText || 'Weekly Highlights unavailable.']]);

        const CSV_NL = String.fromCharCode(13, 10);
        return lines.map(row => row.map(csvEscape).join(',')).join(CSV_NL + CSV_NL);
      }

      function downloadWeeklyHighlightsCsv(csvText, title) {
        const blob = new Blob([csvText], { type: 'text/csv;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = (title || 'weekly-highlights').toLowerCase().replace(/[^a-z0-9]+/g, '-') + '.csv';
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      }

      function renderWeeklyHighlights() {
        const container = document.getElementById('weeklyHighlightsContent');
        const downloadBtn = document.getElementById('downloadWeeklyHighlightsBtn');
        if (!container || !downloadBtn) return;

        const payload = weeklyHighlightsPayload || {};
        const reportData = payload.report_data || {};
        const reportText = String(payload.report_text || '').trim() || 'Weekly Highlights unavailable.';
        const llmEnabled = !!payload.llm_enabled;
        const markup = buildWeeklyHighlightsMarkup(reportData, reportText, llmEnabled);
        container.innerHTML = markup;

        downloadBtn.onclick = () => {
          const csvText = buildWeeklyHighlightsCsv(reportData, reportText, llmEnabled);
          downloadWeeklyHighlightsCsv(csvText, reportData.title || 'Weekly Highlights');
        };
      }

      function renderTeamRawTable({ head, body, headers, records, configured, emptyLabel }) {
        if (!head || !body) return;
        head.textContent = '';
        body.textContent = '';

        if (!headers.length) {
          const tr = document.createElement('tr');
          const td = document.createElement('td');
          td.textContent = configured ? emptyLabel : 'Not configured.';
          td.style.padding = '14px 12px';
          td.style.color = 'var(--muted)';
          tr.appendChild(td);
          body.appendChild(tr);
          return;
        }

        for (const header of headers) {
          const th = document.createElement('th');
          th.textContent = header;
          th.style.padding = '8px 12px';
          th.style.background = 'rgba(255,255,255,0.04)';
          th.style.color = 'var(--muted)';
          th.style.textAlign = 'left';
          th.style.position = 'sticky';
          th.style.top = '0';
          th.style.zIndex = '2';
          th.style.borderBottom = '1px solid rgba(255,255,255,0.08)';
          head.appendChild(th);
        }

        const frag = document.createDocumentFragment();
        for (const record of records) {
          const tr = document.createElement('tr');
          const rawFields = record && record.raw_fields ? record.raw_fields : {};
          for (const header of headers) {
            const td = document.createElement('td');
            const value = rawFields[header];
            td.textContent = Array.isArray(value)
              ? value.map(v => (v && typeof v === 'object' && 'url' in v) ? (v.filename || v.url || 'attachment') : String(v)).join(', ')
              : (value === null || value === undefined || value === '' ? '—' : String(value));
            td.style.padding = '6px 12px';
            td.style.borderBottom = '1px solid rgba(255,255,255,0.08)';
            td.style.color = 'var(--text)';
            tr.appendChild(td);
          }
          frag.appendChild(tr);
        }
        body.appendChild(frag);
      }

      function renderScoutSection() {
        const payload = teamPayload('scout');
        const head = document.getElementById('scoutTableHead');
        const body = document.getElementById('scoutTableBody');
        const msg = document.getElementById('scoutMessage');
        if (!head || !body || !msg) return;

        const configured = !!(payload && payload.configured);
        const headers = payload && Array.isArray(payload.raw_headers) ? payload.raw_headers : [];
        const records = payload && Array.isArray(payload.records) ? payload.records : [];
        const queueCount = records.filter(r => ['QUEUED', 'PROCESSING'].includes(String(r.processing_status || '').toUpperCase())).length;
        const uniqueSites = new Set(records.map(r => String(r.site_number || '').trim()).filter(Boolean)).size;
        const todayStart = new Date(new Date().getFullYear(), new Date().getMonth(), new Date().getDate()).getTime();
        const submittedToday = records.filter(r => {
          const t = scoutTimestampMs(r);
          return t !== null && t >= todayStart;
        }).length;

        setText('scoutTotalRecords', String(records.length));
        setText('scoutQueueCount', String(queueCount));
        setText('scoutSubmittedToday', String(submittedToday));
        setText('scoutConfigured', configured ? 'Yes' : 'No');
        setText('scoutUniqueSites', String(uniqueSites));
        renderScoutTopPerformer(records, configured);
        renderScoutWeeklyProduction(records, configured);

        if (payload && payload.error) {
          msg.textContent = payload.error;
        } else if (!configured) {
          msg.textContent = 'Scout data source is not configured yet.';
        } else if (!headers.length) {
          msg.textContent = 'Scout is configured, but no table headers were returned yet.';
        } else {
          msg.textContent = 'Scout is a fully independent section with its own live metrics and its own raw Airtable table. Revolutionary, I know.';
        }

        renderTeamRawTable({
          head,
          body,
          headers,
          records,
          configured,
          emptyLabel: 'No Scout data available.',
        });
      }

      function heatClass(passRate) {
        if (passRate === null) return 'heat-mid';
        if (passRate >= 95) return 'heat-good';
        if (passRate >= 80) return 'heat-mid';
        return 'heat-bad';
      }

      function buildHeatmap() {
        const container = document.getElementById('vendorHeatmap');
        if (!container) return;

        const rows = cleanRows('7d');
        const vendor = selectedVendor();
        const base = vendor ? rows.filter(r => dimensionValue(r) === vendor) : rows;

        // Pick top vendors by volume (up to 6).
        const byVendor = new Map();
        for (const r of base) {
          const v = dimensionValue(r) || 'Unknown';
          const cur = byVendor.get(v) || { display_label: v, totals: Array(7).fill(0), pass: Array(7).fill(0) };
          const day = new Date(r.t).getDay(); // 0 Sun .. 6 Sat
          cur.totals[day] += 1;
          if (r.status === 'PASS') cur.pass[day] += 1;
          byVendor.set(v, cur);
        }

        const vendors = [...byVendor.values()]
          .sort((a,b) => (b.totals.reduce((x,y)=>x+y,0) - a.totals.reduce((x,y)=>x+y,0)))
          .slice(0, 6);

        const days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
        container.textContent = '';

        // Header row
        const headBlank = document.createElement('div');
        headBlank.className = 'heatmap-head';
        headBlank.textContent = '';
        container.appendChild(headBlank);
        for (const d of days) {
          const el = document.createElement('div');
          el.className = 'heatmap-head';
          el.textContent = d;
          container.appendChild(el);
        }

        if (!vendors.length) {
          const emptyVendor = document.createElement('div');
          emptyVendor.className = 'heatmap-vendor';
          emptyVendor.textContent = 'No data';
          container.appendChild(emptyVendor);

          for (let i = 0; i < 7; i++) {
            const cell = document.createElement('div');
            cell.className = 'heat-cell ' + heatClass(null);
            cell.textContent = '—';
            container.appendChild(cell);
          }
          return;
        }

        for (const v of vendors) {
          const vEl = document.createElement('div');
          vEl.className = 'heatmap-vendor';
          vEl.textContent = v.display_label;
          container.appendChild(vEl);

          for (let i = 0; i < 7; i++) {
            const total = v.totals[i];
            const pr = total ? (v.pass[i] / total) * 100 : null;
            const cell = document.createElement('div');
            cell.className = 'heat-cell ' + heatClass(pr);
            if (pr === null) {
              cell.textContent = '—';
            } else {
              cell.innerHTML = Math.round(pr) + '<small>%</small>';
            }
            container.appendChild(cell);
          }
        }
      }

      function buildRowsVendor(rollups) {{
        const rows = [];
        const styles = [];
        for (const r of rollups) {{
          rows.push([
            r.display_label,
            activeDimensionKey() === 'vendor_email' ? (r.vendor_name || '—') : (r.vendor_email || '—'),
            String(r.total),
            String(r.pass),
            String(r.fail),
            fmtPct(r.passRate),
            fmtScore(r.avgScore),
          ]);
          styles.push(rowStyleFromPassRate(r.passRate));
        }}
        return {{ rows, styles }};
      }}

      function buildRowsSite(rollups) {{
        const rows = [];
        const styles = [];
        for (const r of rollups) {{
          rows.push([
            r.display_label,
            String(r.site_number || ''),
            String(r.total),
            String(r.pass),
            String(r.fail),
            fmtPct(r.passRate),
            fmtScore(r.avgScore),
          ]);
          styles.push(rowStyleFromPassRate(r.passRate));
        }}
        return {{ rows, styles }};
      }}

      function mountVirtualTable(scrollerId, bodyId, colCount, dataRows, dataStyles) {{
        const scroller = document.getElementById(scrollerId);
        const tbody = document.getElementById(bodyId);
        if (!scroller || !tbody) return;

        // small datasets -> render all
        if (dataRows.length <= 200 || reduceMotion) {{
          const frag = document.createDocumentFragment();
          for (let i = 0; i < dataRows.length; i++) {{
            const tr = document.createElement('tr');
            if (dataStyles[i]) tr.setAttribute('style', dataStyles[i]);
            for (const cell of dataRows[i]) {{
              const td = document.createElement('td');
              td.textContent = cell;
              td.style.padding = '6px 12px';
              td.style.borderBottom = '1px solid rgba(255,255,255,0.08)';
              td.style.color = 'var(--text)';
              td.style.textAlign = (cell.match(/^[0-9]/) ? 'right' : 'left');
              tr.appendChild(td);
            }}
            frag.appendChild(tr);
          }}
          tbody.textContent = '';
          tbody.appendChild(frag);
          return;
        }}

        let ROW_HEIGHT = 29;
        (function measure() {{
          const tr = document.createElement('tr');
          if (dataStyles[0]) tr.setAttribute('style', dataStyles[0]);
          for (const cell of (dataRows[0] || [])) {{
            const td = document.createElement('td');
            td.textContent = cell;
            td.style.padding = '6px 12px';
            td.style.borderBottom = '1px solid rgba(255,255,255,0.08)';
            td.style.color = 'var(--text)';
            tr.appendChild(td);
          }}
          tbody.appendChild(tr);
          ROW_HEIGHT = Math.max(1, Math.round(tr.getBoundingClientRect().height));
          tbody.textContent = '';
        }})();

        const topSpacer = document.createElement('tr');
        const topTd = document.createElement('td');
        topTd.colSpan = colCount;
        topTd.style.padding = '0';
        topTd.style.border = 'none';
        topSpacer.appendChild(topTd);

        const bottomSpacer = document.createElement('tr');
        const bottomTd = document.createElement('td');
        bottomTd.colSpan = colCount;
        bottomTd.style.padding = '0';
        bottomTd.style.border = 'none';
        bottomSpacer.appendChild(bottomTd);

        let renderedStart = 0;
        let renderedEnd = 0;

        function render() {{
          const scrollTop = scroller.scrollTop;
          const viewportHeight = scroller.clientHeight;

          const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
          const visibleCount = Math.ceil(viewportHeight / ROW_HEIGHT) + OVERSCAN * 2;
          const endIndex = Math.min(dataRows.length, startIndex + visibleCount);

          if (startIndex === renderedStart && endIndex === renderedEnd) return;
          renderedStart = startIndex;
          renderedEnd = endIndex;

          tbody.textContent = '';
          topTd.style.height = (startIndex * ROW_HEIGHT) + 'px';
          bottomTd.style.height = ((dataRows.length - endIndex) * ROW_HEIGHT) + 'px';

          tbody.appendChild(topSpacer);
          const frag = document.createDocumentFragment();
          for (let i = startIndex; i < endIndex; i++) {{
            const tr = document.createElement('tr');
            if (dataStyles[i]) tr.setAttribute('style', dataStyles[i]);
            for (const cell of dataRows[i]) {{
              const td = document.createElement('td');
              td.textContent = cell;
              td.style.padding = '6px 12px';
              td.style.borderBottom = '1px solid rgba(255,255,255,0.08)';
              td.style.color = 'var(--text)';
              td.style.textAlign = (cell.match(/^[0-9]/) ? 'right' : 'left');
              tr.appendChild(td);
            }}
            frag.appendChild(tr);
          }}
          tbody.appendChild(frag);
          tbody.appendChild(bottomSpacer);
        }}

        scroller.addEventListener('scroll', render, {{ passive: true }});
        window.addEventListener('resize', render);
        render();
      }}

      function updatePostPassPill(key) {
        const pill = document.getElementById('postPassPill');
        const countEl = document.getElementById('postPassPillCount');
        if (!pill || !countEl) return;
        const start = windowStartMs(key);
        const uniqueSites = new Set();
        for (const entry of correctionData) {
          if (!entry.corrected_at) continue;
          const t = Date.parse(entry.corrected_at);
          if (Number.isFinite(t) && t >= start) {
            uniqueSites.add(String(entry.site_number || '').trim());
          }
        }
        const count = uniqueSites.size;
        countEl.textContent = String(count);
        if (count > 0) {
          pill.removeAttribute('hidden');
          pill.style.display = 'inline-flex';
        } else {
          pill.setAttribute('hidden', '');
          pill.style.display = 'none';
        }
      }

      function syncDimensionButtons() {
        document.querySelectorAll('[data-dimension]').forEach(btn => {
          const active = btn.getAttribute('data-dimension') === activeDimensionKey();
          btn.classList.toggle('btn--primary', active);
          btn.classList.toggle('btn--secondary', !active);
          btn.setAttribute('aria-selected', active ? 'true' : 'false');
        });
      }

      function applyWindow(key) {
        currentWindowKey = key;
        const labelMap = { today: 'Today', '3d': 'Last 3 days', '7d': 'Last 7 days', '1m': 'Last month', '3m': 'Last 3 months', '1y': 'Last year' };
        document.getElementById('windowLabel').textContent = labelMap[key] || key;

        const rows = cleanRows(key);
        setKpis(rows);
        updatePostPassPill(key);

        const daily = sumDailyInWindow(key);
        setText('summaryError', String(daily.error));

        // Queue 'completed today' = PASS+FAIL rows today (respects current vendor/site filters)
        const completedToday = cleanRows('today').length;
        setText('queueCompletedToday', String(completedToday));

        const vend = buildRowsVendor(rollupVendor(rows));
        const site = buildRowsSite(rollupVendorSite(rows));

        mountVirtualTable('vendorScroll', 'vendorBody', 7, vend.rows, vend.styles);
        mountVirtualTable('siteScroll', 'siteBody', 7, site.rows, site.styles);

        buildHeatmap();

        // button state
        document.querySelectorAll('[data-window]').forEach(btn => {
          const active = btn.getAttribute('data-window') === key;
          btn.classList.toggle('btn--primary', active);
          btn.classList.toggle('btn--secondary', !active);
          btn.setAttribute('aria-selected', active ? 'true' : 'false');
        });
        syncDimensionButtons();
      }

      document.querySelectorAll('[data-window]').forEach(btn => {{
        btn.addEventListener('click', () => applyWindow(btn.getAttribute('data-window')));
      }});

      document.querySelectorAll('[data-dimension]').forEach(btn => {
        btn.addEventListener('click', () => {
          const next = btn.getAttribute('data-dimension') || 'vendor_name';
          if (next === currentDimensionKey) return;
          currentDimensionKey = next;
          populateVendors();
          applyWindow(currentWindowKey);
          renderDetailTables();
        });
      });


      function buildVendorDetailRows() {
        const vendor = selectedVendor();
        const rows = [];
        const styles = [];

        const filtered = vendor ? vendorDetail.filter(r => dimensionValue(r) === vendor) : vendorDetail;

        for (const r of filtered) {
          const pr = toNum(r.pass_rate_pct);
          styles.push(pr === null ? '' : rowStyleFromPassRate(pr));
          rows.push([
            activeDimensionKey() === 'vendor_email' ? (r.vendor_email || '—') : (r.vendor_name || r.vendor_email || '—'),
            activeDimensionKey() === 'vendor_email' ? (r.vendor_name || '—') : (r.vendor_email || '—'),
            String(r.total || ''),
            String(r.pass || ''),
            String(r.fail || ''),
            String(r.error || ''),
            (r.pass_rate_pct ? String(r.pass_rate_pct) + '%' : ''),
            String(r.avg_turnaround_seconds || ''),
            String(r.latest_submission_at || ''),
          ]);
        }
        return { rows, styles };
      }

      function buildDailySummaryRows() {
        const rows = [];
        const styles = [];
        for (const r of dailySummary) {
          rows.push([
            r.date,
            String(r.total || ''),
            String(r.pass || ''),
            String(r.fail || ''),
            String(r.error || ''),
            (r.pass_rate_pct ? String(r.pass_rate_pct) + '%' : ''),
            String(r.unique_vendors || ''),
            String(r.unique_sites || ''),
          ]);
          styles.push('');
        }
        return { rows, styles };
      }

      function renderDetailTables() {
        const vd = buildVendorDetailRows();
        mountVirtualTable('vendorDetailScroll', 'vendorDetailBody', 9, vd.rows, vd.styles);
        const ds = buildDailySummaryRows();
        mountVirtualTable('dailySummaryScroll', 'dailySummaryBody', 8, ds.rows, ds.styles);
      }

      function populateVendors() {
        if (!vendorSelect) return;
        const previousValue = vendorSelect.value || '';
        const seen = new Map();
        for (const r of surveyPerformanceRows) {
          const value = dimensionValue(r);
          if (!value) continue;
          const companion = activeDimensionKey() === 'vendor_email'
            ? ((r.vendor_name || '').trim() || '—')
            : ((r.vendor_email || '').trim() || '—');
          if (!seen.has(value)) seen.set(value, companion);
        }

        const entries = [...seen.entries()].sort((a,b) => a[0].localeCompare(b[0]));
        vendorSelect.textContent = '';
        if (vendorFilterLabel) vendorFilterLabel.textContent = dimensionDisplayName();
        const all = document.createElement('option');
        all.value = '';
        all.textContent = 'All ' + dimensionDisplayName().toLowerCase() + 's';
        vendorSelect.appendChild(all);

        for (const [value, companion] of entries) {
          const opt = document.createElement('option');
          opt.value = value;
          opt.textContent = activeDimensionKey() === 'vendor_email'
            ? (value + ' (' + companion + ')')
            : (value + ' (' + companion + ')');
          vendorSelect.appendChild(opt);
        }

        vendorSelect.value = [...seen.keys()].includes(previousValue) ? previousValue : '';
      }

      populateVendors();
      renderDetailTables();

      if (vendorSelect) vendorSelect.addEventListener('change', () => { applyWindow(currentWindowKey); renderDetailTables(); initRealtimeSnapshot(); });
      if (siteSearch) siteSearch.addEventListener('input', () => applyWindow(currentWindowKey));

      function isLocalFileDashboard() {
        return window.location.protocol === 'file:';
      }

      function safeRefreshDashboard() {
        if (isLocalFileDashboard()) {
          // Browsers treat `file:` URLs as unique origins, so `reload()`/self-navigation
          // can trigger security errors. Re-open the exact file path without mutating the URL.
          window.location.href = window.location.pathname;
          return;
        }
        window.location.reload();
      }

      // Manual refresh (on-demand).
      const refreshBtn = document.getElementById('refreshNowBtn');
      if (refreshBtn) refreshBtn.addEventListener('click', safeRefreshDashboard);

      // Hosted dashboards should keep themselves fresh automatically.
      // The metrics writer can regenerate the HTML every ~60s, so refresh often
      // enough to track that output without forcing users to mash F5 like cavemen.
      // LIVE HOT RELOAD: 15-second frontend refresh for near-realtime updates
const HOSTED_REFRESH_INTERVAL_MS = 15 * 1000;

      if (!isLocalFileDashboard()) {{
        window.setInterval(safeRefreshDashboard, HOSTED_REFRESH_INTERVAL_MS);
      }}

      applyWindow('today');
      initRealtimeSnapshot();
      wireAppControls();
      initQueueTrend();
      renderScoutSection();
      renderWeeklyHighlights();
    })();
  </script>
</section>
"""

    template = template.replace("{{", "{").replace("}}", "}")
    return (
        template
        .replace("__DATA_JSON__", data_json)
        .replace("__VENDOR_DETAIL_JSON__", vendor_json)
        .replace("__DAILY_SUMMARY_JSON__", summary_json)
        .replace("__REALTIME_SNAPSHOT_JSON__", realtime_json)
        .replace("__QUEUE_TREND_POINTS_JSON__", queue_points_json)
        .replace("__TEAM_DASHBOARD_DATA_JSON__", team_data_json)
        .replace("__WEEKLY_HIGHLIGHTS_JSON__", weekly_highlights_json)
        .replace("__CORRECTION_DATA_JSON__", correction_data_json)
    )
