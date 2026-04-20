"""Quick test: grade submission rec68SeJ68akJRrUX using BigQuery data source."""
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from src.siteowlqa.config import load_config
from src.siteowlqa.airtable_client import AirtableClient
from src.siteowlqa.python_grader import grade_submission_in_python

cfg = load_config()
print(f'Config loaded - REFERENCE_SOURCE: {cfg.reference_source}', flush=True)
print(f'GCP Project: {cfg.gcp_project}', flush=True)
print(f'BQ Dataset: {cfg.bigquery_dataset}', flush=True)

client = AirtableClient(cfg)
pending = client.get_pending_records()
print(f'Found {len(pending)} pending records', flush=True)

if not pending:
    print('No pending records!', flush=True)
    sys.exit(1)

rec = pending[0]
print(f'Processing: {rec.record_id} - Site {rec.site_number}', flush=True)

# Download the file
print('Downloading attachment...', flush=True)
file_path = client.download_attachment(rec)
print(f'Downloaded to: {file_path}', flush=True)

# Grade it
print('Grading submission with BigQuery reference data...', flush=True)
result = grade_submission_in_python(cfg, rec, file_path)
print(f'Status: {result.status}', flush=True)
print(f'Score: {result.score}', flush=True)
print(f'Issues: {len(result.issues) if result.issues else 0}', flush=True)
if result.issues:
    for issue in result.issues[:5]:
        print(f'  - {issue}', flush=True)
