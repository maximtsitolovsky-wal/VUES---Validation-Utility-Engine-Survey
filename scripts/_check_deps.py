"""Verify all dependencies are installed."""
import sys
print(f'Python: {sys.version}')
print()

packages = [
    ('pandas', 'pandas'),
    ('openpyxl', 'openpyxl'),
    ('pywin32', 'win32api'),
    ('google-cloud-bigquery', 'google.cloud.bigquery'),
    ('google-cloud-bigquery-storage', 'google.cloud.bigquery_storage'),
    ('google-auth', 'google.auth'),
    ('db-dtypes', 'db_dtypes'),
    ('requests', 'requests'),
    ('httpx', 'httpx'),
    ('pydantic-ai', 'pydantic_ai'),
    ('openai', 'openai'),
    ('python-dotenv', 'dotenv'),
    ('pyairtable', 'pyairtable'),
    ('python-calamine', 'python_calamine'),
    ('pytest', 'pytest'),
]

print('Package Check:')
print('-' * 50)
ok_count = 0
missing_count = 0
for name, module in packages:
    try:
        m = __import__(module)
        ver = getattr(m, '__version__', 'OK')
        print(f'  [OK] {name}: {ver}')
        ok_count += 1
    except ImportError as e:
        print(f'  [MISSING] {name}: {e}')
        missing_count += 1

print('-' * 50)
print(f'Total: {ok_count} OK, {missing_count} MISSING')
