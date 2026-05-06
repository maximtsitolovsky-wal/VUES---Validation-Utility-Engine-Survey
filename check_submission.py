#!/usr/bin/env python3
"""Check the submission file columns."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

path = r'archive\submissions\2026\05\06\recBBZ5oqgJUjXZ4U_SiteOwl-Projects-Devices-Walmart_Retail-20260506-104406.csv'
df = pd.read_csv(path, dtype=str)

print(f"Total rows: {len(df)}")
print(f"Total columns: {len(df.columns)}")
print()

# Check for Description column
desc_cols = [c for c in df.columns if 'desc' in c.lower()]
print(f"Columns with 'desc': {desc_cols}")

if 'Description' in df.columns:
    non_empty = df['Description'].fillna('').str.strip().ne('').sum()
    print(f"Description column: {non_empty} non-empty values out of {len(df)}")
    print(f"Sample values: {df['Description'].dropna().head(5).tolist()}")
else:
    print("Description column NOT found!")
    
# Check Abbreviated Name
if 'Abbreviated Name' in df.columns:
    non_empty = df['Abbreviated Name'].fillna('').str.strip().ne('').sum()
    print(f"Abbreviated Name column: {non_empty} non-empty values out of {len(df)}")
