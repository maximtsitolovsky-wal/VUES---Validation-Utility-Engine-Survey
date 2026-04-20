"""Quick test: verify BigQuery data source is working for site 7162."""
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from src.siteowlqa.config import load_config
from src.siteowlqa.reference_data import fetch_reference_rows

cfg = load_config()
print(f'REFERENCE_SOURCE: {cfg.reference_source}', flush=True)
print(f'GCP Project: {cfg.gcp_project}', flush=True)
print(f'BQ Dataset: {cfg.bigquery_dataset}', flush=True)

# This will use BigQuery if configured
print('\nFetching reference data for site 7162...', flush=True)
df = fetch_reference_rows(cfg, '7162')
print(f'Fetched {len(df)} reference rows', flush=True)
print(f'Columns: {list(df.columns)}', flush=True)
if len(df) > 0:
    print('\nSample row:', flush=True)
    print(df.iloc[0].to_dict(), flush=True)
else:
    print('NO DATA FOUND!', flush=True)
