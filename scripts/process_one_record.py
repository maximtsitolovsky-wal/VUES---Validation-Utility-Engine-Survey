"""Process a single Airtable record by ID."""
import sys
sys.path.insert(0, 'src')

from siteowlqa.config import load_config
from siteowlqa.airtable_client import AirtableClient
from siteowlqa.file_processor import load_vendor_file_with_metadata
from siteowlqa.python_grader import grade_submission_in_python, status_from_score
from siteowlqa.site_validation import validate_submission_for_site
from pathlib import Path

RECORD_ID = 'rec3xU9VQlIgkxKKH'

cfg = load_config()
client = AirtableClient(cfg)

# Get the record
records = [r for r in client.list_all_records(max_records=100) if r.record_id == RECORD_ID]
if not records:
    print(f"Record {RECORD_ID} not found!")
    sys.exit(1)

record = records[0]
print(f"Processing: {record.submission_id}")
print(f"  Site: {record.site_number}")
print(f"  Survey Type: {record.survey_type}")

# Download
print("Downloading attachment...")
attachment_path = client.download_attachment(record)
print(f"  Downloaded: {attachment_path}")

# Load
print("Loading file...")
load_result = load_vendor_file_with_metadata(attachment_path, record.site_number)
df = load_result.dataframe
print(f"  Loaded {len(df)} rows")

# Grade (skip validation for quick test)
print("Grading...")
try:
    outcome = grade_submission_in_python(
        cfg=cfg,
        submission_df=df,
        submission_id=record.submission_id,
        site_number=record.site_number,
        survey_type=record.survey_type,
    )
    print(f"  Status: {outcome.result.status.value}")
    print(f"  Score: {outcome.result.score}")
    
    # Update Airtable
    final_status = status_from_score(outcome.result.score or 0)
    true_score = float(outcome.result.score or 0)
    client.update_result(
        record_id=record.record_id,
        status=final_status.value,
        score=true_score,
        true_score=true_score,
        fail_summary=outcome.result.message[:1000] if outcome.result.message else "",
        notes_internal=outcome.notes_internal[:2000] if outcome.notes_internal else "",
    )
    print(f"\nDONE! Updated Airtable with status={final_status.value}")
    
except Exception as e:
    print(f"  GRADING ERROR: {e}")
    import traceback
    traceback.print_exc()
