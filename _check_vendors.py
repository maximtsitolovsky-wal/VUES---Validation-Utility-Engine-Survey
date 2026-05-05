#!/usr/bin/env python
"""Check what vendors are in the Excel source data."""
import sys
sys.path.insert(0, 'src')
from siteowlqa.survey_routing import load_schedule_data, DEFAULT_WORKBOOK_PATH

print('Loading schedule data from Excel...')
records = load_schedule_data(DEFAULT_WORKBOOK_PATH)
print(f'Total records: {len(records)}')

# Get unique vendors
vendors = {}
for r in records:
    v = r.vendor or 'EMPTY'
    vendors[v] = vendors.get(v, 0) + 1

print()
print('Vendors in Excel (before normalization):')
for v, count in sorted(vendors.items(), key=lambda x: -x[1]):
    print(f'  {v:20s}: {count}')

# Save to file
with open('_vendor_check.txt', 'w') as f:
    f.write(f'Total records: {len(records)}\n\n')
    f.write('Vendors in Excel:\n')
    for v, count in sorted(vendors.items(), key=lambda x: -x[1]):
        f.write(f'  {v:20s}: {count}\n')

print('\nSaved to _vendor_check.txt')
