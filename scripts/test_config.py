import sys
sys.path.insert(0, 'src')

results = []
try:
    from siteowlqa.config import load_config
    cfg = load_config()
    results.append(f'sql_server: {cfg.sql_server}')
    results.append(f'sql_database: {cfg.sql_database}')
    results.append(f'airtable_base_id: {cfg.airtable_base_id}')
    results.append(f'airtable_table_name: {cfg.airtable_table_name}')
    results.append(f'reference_source: {cfg.reference_source}')
    results.append(f'reference_workbook_path: {cfg.reference_workbook_path}')
    results.append(f'reference_workbook_sheet: {cfg.reference_workbook_sheet}')
    results.append(f'poll_interval_seconds: {cfg.poll_interval_seconds}')
    results.append(f'worker_threads: {cfg.worker_threads}')
    results.append('LOAD SUCCESS')
except Exception as e:
    import traceback
    results.append(f'LOAD FAILED: {e}')
    results.append(traceback.format_exc())

with open('scripts/_config_test.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(results) + '\n')
