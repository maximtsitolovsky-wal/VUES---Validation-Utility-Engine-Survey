"""Quick diagnostic: Check what's in Survey vs what's displayed."""
from siteowlqa.config import load_config
from siteowlqa.airtable_client import AirtableClient
from pathlib import Path
import json

cfg = load_config()

print("=" * 60)
print("VUE SURVEY AIRTABLE")
print("=" * 60)
print(f"Base ID: {cfg.airtable_base_id}")
print(f"Table: {cfg.airtable_table_name}")
print()

at = AirtableClient(cfg)
all_records = at.list_all_records()
print(f"Total records in Airtable: {len(all_records)}")
print()

# Status breakdown
statuses = {}
for r in all_records:
    st = r.processing_status if r.processing_status else "(empty)"
    statuses[st] = statuses.get(st, 0) + 1

print("Status breakdown:")
for status, count in sorted(statuses.items()):
    print(f"  {status}: {count}")
print()

# Show first 10
print("First 10 records:")
for i, r in enumerate(all_records[:10], 1):
    status = r.processing_status if r.processing_status else "(empty)"
    print(f"{i:2d}. {r.record_id} | Site: {r.site_number:6s} | {status:10s} | {r.vendor_email}")
print()

# Check archive
archive_dir = Path("archive")
if archive_dir.exists():
    print("=" * 60)
    print("ARCHIVE CHECK")
    print("=" * 60)
    
    submissions_file = archive_dir / "submissions.jsonl"
    if submissions_file.exists():
        with open(submissions_file, 'r') as f:
            archive_records = [json.loads(line) for line in f]
        print(f"Total archived submissions: {len(archive_records)}")
        
        # Count by source
        sources = {}
        for rec in archive_records:
            src = rec.get('source', 'unknown')
            sources[src] = sources.get(src, 0) + 1
        
        print("\nArchived by source:")
        for src, count in sorted(sources.items()):
            print(f"  {src}: {count}")
    else:
        print("No submissions.jsonl found in archive/")
print()

# Check output CSVs
output_dir = Path("output")
if output_dir.exists():
    print("=" * 60)
    print("OUTPUT CSV CHECK")
    print("=" * 60)
    
    csv_files = list(output_dir.glob("*.csv"))
    print(f"Found {len(csv_files)} CSV files in output/:")
    for csv in sorted(csv_files):
        print(f"  - {csv.name} ({csv.stat().st_size / 1024:.1f} KB)")
    
    # Check metrics_by_vendor.csv specifically
    vendor_csv = output_dir / "metrics_by_vendor.csv"
    if vendor_csv.exists():
        import pandas as pd
        df = pd.read_csv(vendor_csv)
        print(f"\nmetrics_by_vendor.csv has {len(df)} rows")
        print("Vendors:")
        for i, row in df.iterrows():
            print(f"  - {row['Vendor']}: {row.get('Total Submissions', 'N/A')} submissions")

print("\n" + "=" * 60)
print("DONE")
print("=" * 60)
