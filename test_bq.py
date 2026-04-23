import sys, time
sys.path.insert(0, 'src')
from siteowlqa.config import load_config
from siteowlqa.reference_data import fetch_reference_rows

cfg = load_config()
print('Fetching BQ reference for site 686...', flush=True)
t0 = time.time()
df = fetch_reference_rows(cfg, '686')
print(f'Done: {len(df)} rows in {time.time()-t0:.1f}s', flush=True)
