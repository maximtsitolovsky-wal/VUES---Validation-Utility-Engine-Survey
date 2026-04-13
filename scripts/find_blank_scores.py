import sys
import os

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

log_path = 'logs/siteowl_qa.log.1'

with open(log_path, encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

# Find all END lines to see score=None records
print("=== ALL PIPELINE END LINES (showing score and status) ===")
end_lines = [(i+1, l.rstrip()) for i, l in enumerate(lines) if '=== END' in l]
for num, line in end_lines[:60]:
    print(f'  L{num}: {line}')

print()
print("=== RECORDS WITH score=None ===")
none_score = [(i+1, l.rstrip()) for i, l in enumerate(lines)
              if '=== END' in l and 'score=None' in l]
print(f'Found {len(none_score)} records with score=None')
for num, line in none_score:
    print(f'  L{num}: {line}')
