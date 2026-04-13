"""Refresh archive notes for FAIL submissions using current QAResults summaries.

Usage:
    python refresh_fail_notes.py
"""

from __future__ import annotations

import json
from pathlib import Path

from siteowlqa.config import load_config
from siteowlqa.poll_airtable import _summarize_fail_issues
from siteowlqa.sql import fetch_error_rows, get_connection

ARCHIVE_ROOT = Path("archive/submissions")



def main() -> None:
    cfg = load_config()
    updated = 0
    for meta_path in sorted(ARCHIVE_ROOT.rglob("*_meta.json")):
        with open(meta_path, encoding="utf-8") as fh:
            meta = json.load(fh)

        if str(meta.get("status") or "").strip().upper() != "FAIL":
            continue

        submission_id = str(meta.get("submission_id") or "").strip()
        if not submission_id:
            continue

        with get_connection(cfg, autocommit=False) as conn:
            cur = conn.cursor()
            error_df = fetch_error_rows(cur, submission_id)

        issue_lines = _summarize_fail_issues(error_df)
        if not issue_lines:
            continue

        note = " | ".join(line.strip() for line in issue_lines[:3])[:500]
        if meta.get("notes") == note:
            continue

        meta["notes"] = note
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        updated += 1
        print(f"UPDATED {submission_id}: {note}")

    print()
    print(f"FAIL note refresh complete. Updated: {updated}")


if __name__ == "__main__":
    main()
