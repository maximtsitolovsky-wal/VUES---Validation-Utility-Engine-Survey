"""
Check Excel file for Techwise and SAS vendors
"""
import pandas as pd
import sys

xl_path = r'C:\Users\vn59j7j\OneDrive - Walmart Inc\Documents\BaselinePrinter\2027 Survey Lab.xlsm'

print("Loading Excel file...", flush=True)
xl = pd.ExcelFile(xl_path)
print(f"Sheets: {xl.sheet_names}", flush=True)

# Check Project Tracking
print("\n" + "="*70, flush=True)
print("PROJECT TRACKING - VENDOR ANALYSIS", flush=True)
print("="*70, flush=True)

df = pd.read_excel(xl, 'Project Tracking')
print(f"Total rows: {len(df)}", flush=True)
print(f"Columns: {list(df.columns)[:20]}", flush=True)

# Look for vendor-related columns
for col in df.columns:
    if 'vendor' in str(col).lower():
        print(f"\nVendor column: {col}", flush=True)
        print(df[col].value_counts(), flush=True)

# Also check if there's a column that might contain Techwise/SAS
print("\n" + "="*70, flush=True)
print("SEARCHING FOR TECHWISE/SAS IN DATA", flush=True)
print("="*70, flush=True)

# Search across all string columns
for col in df.columns:
    try:
        col_str = df[col].astype(str)
        techwise_count = col_str.str.contains('Techwise', case=False, na=False).sum()
        sas_count = col_str.str.contains('SAS', case=False, na=False).sum()
        if techwise_count > 0:
            print(f"Column '{col}' has {techwise_count} Techwise mentions", flush=True)
        if sas_count > 0:
            print(f"Column '{col}' has {sas_count} SAS mentions", flush=True)
    except:
        pass

# Check MAP DATA sheet
print("\n" + "="*70, flush=True)
print("MAP DATA SHEET", flush=True)
print("="*70, flush=True)

df_map = pd.read_excel(xl, 'MAP DATA')
print(f"Total rows: {len(df_map)}", flush=True)
print(f"Columns: {list(df_map.columns)[:15]}", flush=True)

for col in df_map.columns:
    if 'vendor' in str(col).lower():
        print(f"\nVendor column: {col}", flush=True)
        print(df_map[col].value_counts(), flush=True)

# Search for Techwise/SAS in MAP DATA
for col in df_map.columns:
    try:
        col_str = df_map[col].astype(str)
        techwise_count = col_str.str.contains('Techwise', case=False, na=False).sum()
        sas_count = col_str.str.contains('SAS', case=False, na=False).sum()
        if techwise_count > 0:
            print(f"MAP DATA Column '{col}' has {techwise_count} Techwise mentions", flush=True)
        if sas_count > 0:
            print(f"MAP DATA Column '{col}' has {sas_count} SAS mentions", flush=True)
    except:
        pass

print("\nDone!", flush=True)
