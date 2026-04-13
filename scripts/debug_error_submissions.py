"""Try to manually grade the ERROR submissions to find root cause."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from siteowlqa.airtable_client import AirtableClient
from siteowlqa.config import load_config
from siteowlqa.file_processor import load_vendor_file
from siteowlqa.python_grader import grade_submission_in_python


def main() -> int:
    cfg = load_config()
    airtable = AirtableClient(cfg)

    records = airtable.list_all_records(max_records=0)
    error_records = [r for r in records if r.processing_status == "ERROR"]

    for r in error_records:
        print(f"\n=== Attempting to grade: {r.record_id} (Site {r.site_number}) ===")
        print(f"Attachment: {r.attachment_filename}")
        
        try:
            # Download the file
            file_path = airtable.download_attachment(r)
            print(f"Downloaded: {file_path}")
            
            # Try to load it
            df = load_vendor_file(file_path, r.site_number)
            print(f"Loaded: {len(df)} rows × {len(df.columns)} cols")
            print(f"Columns: {list(df.columns)}")
            
            # Try to grade
            grade_outcome = grade_submission_in_python(
                cfg=cfg,
                submission_df=df,
                submission_id=r.record_id,
                site_number=r.site_number,
            )
            
            print(f"Status: {grade_outcome.result.status}")
            print(f"Score: {grade_outcome.result.score}")
            print(f"Message: {grade_outcome.result.message}")
            
        except Exception as e:
            print(f"EXCEPTION: {type(e).__name__}: {e}")
            traceback.print_exc()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
