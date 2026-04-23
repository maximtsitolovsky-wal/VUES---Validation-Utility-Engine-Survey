"""Real end-to-end test of survey type grading."""
import sys
sys.path.insert(0, 'src')

from siteowlqa.config import load_config, get_grade_columns_for_survey_type
from siteowlqa.airtable_client import AirtableClient
from siteowlqa.file_processor import load_vendor_file_with_metadata
from siteowlqa.python_grader import grade_submission_in_python
from pathlib import Path

def main():
    print("=" * 60)
    print("REAL END-TO-END SURVEY TYPE GRADING TEST")
    print("=" * 60)
    print()

    cfg = load_config()
    client = AirtableClient(cfg)

    # Get records
    all_recs = client.list_all_records(max_records=20)
    print(f"Fetched {len(all_recs)} records from Airtable\n")

    # Group by survey type
    by_type = {}
    for r in all_recs:
        t = r.survey_type or '(not set)'
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(r)

    print("Records by Survey Type:")
    for t, recs in by_type.items():
        print(f"  {t}: {len(recs)} records")
    print()

    # Pick one record to actually grade
    test_record = all_recs[0] if all_recs else None
    if not test_record:
        print("No records to test!")
        return

    print("-" * 60)
    print(f"TEST GRADING: {test_record.submission_id}")
    print(f"  Site: {test_record.site_number}")
    print(f"  Survey Type: {test_record.survey_type or '(not set)'}")
    print(f"  Expected columns: {get_grade_columns_for_survey_type(test_record.survey_type)}")
    print("-" * 60)
    print()

    # Download the attachment
    try:
        attachment_path = client.download_attachment(test_record)
        print(f"Downloaded: {attachment_path}")
    except Exception as e:
        print(f"Download failed: {e}")
        return

    # Load the file
    try:
        load_result = load_vendor_file_with_metadata(attachment_path)
        df = load_result.dataframe
        print(f"Loaded {len(df)} rows, columns: {list(df.columns)}")
    except Exception as e:
        print(f"Load failed: {e}")
        return

    # Grade it
    print()
    print("GRADING...")
    try:
        outcome = grade_submission_in_python(
            cfg=cfg,
            submission_df=df,
            submission_id=test_record.submission_id,
            site_number=test_record.site_number,
            survey_type=test_record.survey_type,  # <-- THE KEY PARAMETER
        )
        print(f"  Status: {outcome.result.status.value}")
        print(f"  Score: {outcome.result.score}")
        print(f"  Rows: {outcome.submission_row_count} submitted / {outcome.reference_row_count} reference")
        if outcome.notes_internal:
            print(f"  Notes: {outcome.notes_internal[:200]}...")
    except Exception as e:
        print(f"Grading failed: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
