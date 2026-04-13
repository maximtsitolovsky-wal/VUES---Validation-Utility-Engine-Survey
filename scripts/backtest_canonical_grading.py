"""Replay archived submissions through the Python-first grader and compare outcomes.

Usage:
    python backtest_canonical_grading.py
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean

from siteowlqa.config import load_config
from siteowlqa.file_processor import load_vendor_file_with_metadata
from siteowlqa.python_grader import grade_submission_in_python
from siteowlqa.site_validation import validate_submission_for_site

ARCHIVE_ROOT = Path("archive/submissions")
OUTPUT_JSON = Path("output/python_grader_backtest.json")
OUTPUT_HTML = Path("output/python_grader_backtest.html")


@dataclass(frozen=True, slots=True)
class ReplayRecord:
    submission_id: str
    site_number: str
    archived_status: str
    replay_status: str
    archived_score: float | None
    replay_score: float | None
    changed: bool
    reason: str
    issue_count: int



def main() -> None:
    cfg = load_config()
    records = [
        replay_one(cfg, meta_path)
        for meta_path in sorted(ARCHIVE_ROOT.rglob("*_meta.json"))
    ]
    records = [record for record in records if record is not None]
    summary = build_summary(records)
    write_json(records, summary)
    write_html(records, summary)
    print_summary(summary)



def replay_one(cfg, meta_path: Path) -> ReplayRecord | None:
    with open(meta_path, encoding="utf-8") as fh:
        meta = json.load(fh)

    submission_id = str(meta.get("submission_id") or "").strip()
    site_number = str(meta.get("site_number") or "").strip()
    archived_status = str(meta.get("status") or "").strip().upper()
    archived_score = normalize_score(meta.get("score"), archived_status)
    raw_file = Path(str(meta.get("archived_file_path") or "").strip())

    if not submission_id or not site_number or not raw_file.exists():
        return ReplayRecord(
            submission_id=submission_id or "<missing>",
            site_number=site_number or "<missing>",
            archived_status=archived_status or "<missing>",
            replay_status="ERROR",
            archived_score=archived_score,
            replay_score=None,
            changed=True,
            reason=f"Archived raw file missing: {raw_file}",
            issue_count=0,
        )

    try:
        load_result = load_vendor_file_with_metadata(raw_file, site_number)
        validation = validate_submission_for_site(cfg, site_number, load_result)
        if not validation.is_valid_for_grading:
            replay_status = "FAIL"
            replay_score = 0.0
            reason = "; ".join(validation.reason_codes)
            issue_count = 0
        else:
            outcome = grade_submission_in_python(
                cfg=cfg,
                submission_df=load_result.dataframe,
                submission_id=submission_id,
                site_number=site_number,
            )
            replay_status = outcome.result.status.value
            replay_score = normalize_score(outcome.result.score, replay_status)
            reason = outcome.result.message
            issue_count = 0 if outcome.error_df is None else len(outcome.error_df)
    except Exception as exc:  # noqa: BLE001
        replay_status = "FAIL"
        replay_score = 0.0
        reason = f"Replay load/grading failed: {exc}"
        issue_count = 0

    changed = archived_status != replay_status or archived_score != replay_score
    return ReplayRecord(
        submission_id=submission_id,
        site_number=site_number,
        archived_status=archived_status,
        replay_status=replay_status,
        archived_score=archived_score,
        replay_score=replay_score,
        changed=changed,
        reason=reason,
        issue_count=issue_count,
    )



def normalize_score(raw_score, status: str) -> float | None:
    if status == "PASS":
        return 100.0
    if raw_score in (None, ""):
        return None
    return round(float(raw_score), 2)



def build_summary(records: list[ReplayRecord]) -> dict[str, object]:
    changed = [record for record in records if record.changed]
    archived_pass = sum(1 for record in records if record.archived_status == "PASS")
    replay_pass = sum(1 for record in records if record.replay_status == "PASS")
    archived_fail = sum(1 for record in records if record.archived_status == "FAIL")
    replay_fail = sum(1 for record in records if record.replay_status == "FAIL")
    archived_error = sum(1 for record in records if record.archived_status == "ERROR")
    replay_error = sum(1 for record in records if record.replay_status == "ERROR")
    changed_scores = [
        abs((record.replay_score or 0.0) - (record.archived_score or 0.0))
        for record in changed
        if record.archived_score is not None or record.replay_score is not None
    ]
    return {
        "total_records": len(records),
        "changed_records": len(changed),
        "unchanged_records": len(records) - len(changed),
        "archived_pass": archived_pass,
        "replay_pass": replay_pass,
        "archived_fail": archived_fail,
        "replay_fail": replay_fail,
        "archived_error": archived_error,
        "replay_error": replay_error,
        "avg_score_delta": round(mean(changed_scores), 2) if changed_scores else 0.0,
    }



def write_json(records: list[ReplayRecord], summary: dict[str, object]) -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": summary,
        "records": [asdict(record) for record in records],
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")



def write_html(records: list[ReplayRecord], summary: dict[str, object]) -> None:
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    changed_rows = "\n".join(
        f"<tr><td>{escape(record.submission_id)}</td><td>{escape(record.site_number)}</td><td>{escape(record.archived_status)}</td><td>{escape(record.replay_status)}</td><td>{format_score(record.archived_score)}</td><td>{format_score(record.replay_score)}</td><td>{record.issue_count}</td><td>{escape(record.reason[:160])}</td></tr>"
        for record in records
        if record.changed
    ) or "<tr><td colspan='8'>No changed records. Miracles do happen.</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang='en'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>Python Grader Backtest</title>
  <script src='https://cdn.tailwindcss.com'></script>
</head>
<body class='bg-white text-slate-900'>
  <main class='max-w-7xl mx-auto p-6 space-y-6'>
    <header class='space-y-2'>
      <h1 class='text-3xl font-bold text-[#0053e2]'>Python Grader Backtest</h1>
      <p class='text-sm text-slate-700'>Archive replay comparing archived outcomes to the Python-first grader. Fancy words, same goal: catch grading nonsense.</p>
    </header>

    <section class='grid gap-4 md:grid-cols-4'>
      <div class='rounded-lg border border-slate-200 p-4 bg-slate-50'><div class='text-sm text-slate-600'>Total</div><div class='text-2xl font-bold'>{summary['total_records']}</div></div>
      <div class='rounded-lg border border-slate-200 p-4 bg-slate-50'><div class='text-sm text-slate-600'>Changed</div><div class='text-2xl font-bold text-[#ea1100]'>{summary['changed_records']}</div></div>
      <div class='rounded-lg border border-slate-200 p-4 bg-slate-50'><div class='text-sm text-slate-600'>Replay PASS</div><div class='text-2xl font-bold text-[#2a8703]'>{summary['replay_pass']}</div></div>
      <div class='rounded-lg border border-slate-200 p-4 bg-slate-50'><div class='text-sm text-slate-600'>Avg Score Delta</div><div class='text-2xl font-bold'>{summary['avg_score_delta']}</div></div>
    </section>

    <section class='rounded-lg border border-slate-200 overflow-hidden'>
      <div class='px-4 py-3 bg-[#0053e2] text-white font-semibold'>Changed Outcomes</div>
      <div class='overflow-x-auto'>
        <table class='min-w-full text-sm'>
          <thead class='bg-slate-100 text-left'>
            <tr>
              <th class='p-3'>Submission</th>
              <th class='p-3'>Site</th>
              <th class='p-3'>Archived</th>
              <th class='p-3'>Replay</th>
              <th class='p-3'>Old Score</th>
              <th class='p-3'>New Score</th>
              <th class='p-3'>Issues</th>
              <th class='p-3'>Reason</th>
            </tr>
          </thead>
          <tbody>{changed_rows}</tbody>
        </table>
      </div>
    </section>
  </main>
</body>
</html>
"""
    OUTPUT_HTML.write_text(html, encoding="utf-8")



def format_score(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"



def escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )



def print_summary(summary: dict[str, object]) -> None:
    print("=== Python Grader Archive Backtest ===")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print()
    print(f"JSON report: {OUTPUT_JSON}")
    print(f"HTML report: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
