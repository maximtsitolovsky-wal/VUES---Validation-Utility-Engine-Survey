import sys, time
sys.path.insert(0, 'src')
from siteowlqa.config import load_config
from siteowlqa.airtable_client import AirtableClient
from siteowlqa.file_processor import load_vendor_file_with_metadata
from siteowlqa.python_grader import grade_submission_in_python, status_from_score

RECORD_ID = 'recahLGG7asC00VZr'

cfg = load_config()
client = AirtableClient(cfg)

t0 = time.time()
records = [r for r in client.list_all_records(max_records=100) if r.record_id == RECORD_ID]
record = records[0]
print(f'[{time.time()-t0:.1f}s] Got record: Site {record.site_number} | {record.survey_type}')

t1 = time.time()
path = client.download_attachment(record)
print(f'[{time.time()-t1:.1f}s] Downloaded attachment')

t2 = time.time()
df = load_vendor_file_with_metadata(path, record.site_number).dataframe
print(f'[{time.time()-t2:.1f}s] Loaded {len(df)} rows')

t3 = time.time()
outcome = grade_submission_in_python(
    cfg=cfg, submission_df=df, submission_id=record.submission_id,
    site_number=record.site_number, survey_type=record.survey_type,
)
print(f'[{time.time()-t3:.1f}s] Graded: {outcome.submission_row_count}/{outcome.reference_row_count} rows')
print(f'         Score: {outcome.result.score} -> {outcome.result.status.value}')

t4 = time.time()
score = float(outcome.result.score or 0)
client.update_result(
    record_id=record.record_id, status=status_from_score(score).value,
    score=score, true_score=score,
    fail_summary=outcome.result.message[:1000] if outcome.result.message else '',
    notes_internal=outcome.notes_internal[:2000] if outcome.notes_internal else '',
)
print(f'[{time.time()-t4:.1f}s] Updated Airtable')
print(f'\nTOTAL: {time.time()-t0:.1f}s')
