import json

print('Reading temp file...')
with open('temp_zips.json', 'r', encoding='utf-8') as f:
    content = f.read()

print(f'File size: {len(content)} chars')
print(f'First 500 chars: {content[:500]}')

try:
    data = json.loads(content)
    print(f'Parsed {len(data)} records')
    if data:
        print(f'First record: {data[0]}')
except Exception as e:
    print(f'JSON parse error: {e}')
