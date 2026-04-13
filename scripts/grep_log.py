import sys
import os

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

log_path = 'logs/siteowl_qa.log.1'
if not os.path.exists(log_path):
    print('Log file not found:', log_path)
    sys.exit(1)

with open(log_path, encoding='utf-8', errors='replace') as f:
    content = f.read()

print('File size:', len(content))
if not content.strip():
    print('LOG IS EMPTY')
    sys.exit(0)

lines = content.splitlines()
print('Total lines:', len(lines))

keywords = ['score', 'true_score', 'update_result', 'verify', '422',
            'T7', 'attempt=', 'writeback', 'all fallback', 'patch',
            'PASS', 'FAIL', 'submission=']

matched = [
    (i + 1, line)
    for i, line in enumerate(lines)
    if any(k.lower() in line.lower() for k in keywords)
]
print(f'Matched {len(matched)} lines')
print()
for num, line in matched[:80]:
    print(f'L{num}: {line[:250]}')
