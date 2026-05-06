#!/usr/bin/env python3
"""Check embedded scout data in scout.html."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import re
import json

print("Reading scout.html...")
with open('ui/scout.html', 'r', encoding='utf-8') as f:
    content = f.read()

print(f"File size: {len(content):,} chars")

# Look for the embedded data pattern
pattern = r'window\.TEAM_DASHBOARD_DATA_FALLBACK\s*=\s*(\{.*?\});\s*\n'
matches = list(re.finditer(pattern, content, re.DOTALL))
print(f"Found {len(matches)} matches for TEAM_DASHBOARD_DATA_FALLBACK")

if matches:
    match = matches[0]
    json_str = match.group(1)
    print(f"JSON string length: {len(json_str):,} chars")
    
    try:
        data = json.loads(json_str)
        scout = data.get('scout', {})
        print("\nEmbedded scout stats:")
        print(f"  total_submissions: {scout.get('total_submissions')}")
        print(f"  unique_submissions: {scout.get('unique_submissions')}")
        print(f"  completed: {scout.get('completed')}")
        print(f"  excel_total: {scout.get('excel_total')}")
        print(f"  remaining: {scout.get('remaining')}")
        print(f"  records count: {len(scout.get('records', []))}")
    except json.JSONDecodeError as e:
        print(f"JSON parse error at pos {e.pos}: {e.msg}")
        # Show context around error
        start = max(0, e.pos - 50)
        end = min(len(json_str), e.pos + 50)
        print(f"Context: ...{json_str[start:end]}...")
