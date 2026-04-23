import sys
sys.path.insert(0, 'src')
from siteowlqa.config import load_config
from siteowlqa.airtable_client import AirtableClient
from siteowlqa.file_processor import load_vendor_file_with_metadata
from siteowlqa.python_grader import grade_submission_in_python, status_from_score

cfg = load_config()
client = AirtableClient(cfg)

# Get record
records = [r for r in client.list_all_records(max_records=100) if r.record_id == 'rec3xU9VQlIgkxKKH']
record = records[0]
print(f'Site: {record.site_number} | Survey Type: {record.survey_type}')

# Download & load
path = client.download_attachment(record)
df = load_vendor_file_with_metadata(path, record.site_number).dataframe
print(f'Loaded {len(df)} rows')

# Grade
outcome = grade_submission_in_python(
    cfg=cfg, submission_df=df, submission_id=record.submission_id,
    site_number=record.site_number, survey_type=record.survey_type,
)
print(f'Filtered rows: {outcome.submission_row_count} / {outcome.reference_row_count}')
print(f'Score: {outcome.result.score} -> {outcome.result.status.value}')

# Update Airtable
score = float(outcome.result.score or 0)
client.update_result(
    record_id=record.record_id, status=status_from_score(score).value,
    score=score, true_score=score,
    fail_summary=outcome.result.message[:1000] if outcome.result.message else '',
    notes_internal=outcome.notes_internal[:2000] if outcome.notes_internal else '',
)
print('Airtable updated!')
