"""Inspect a single Airtable record by record ID."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from siteowlqa.config import load_config
from siteowlqa.airtable_client import AirtableClient


def main():
    record_id = sys.argv[1] if len(sys.argv) > 1 else "recryYpfpuVlYKm1g"
    
    print(f"Loading config...")
    cfg = load_config()
    
    print(f"Fetching record {record_id}...")
    client = AirtableClient(cfg)
    fields = client.get_record_fields(record_id)
    
    print("=" * 60)
    print(f"Record ID: {record_id}")
    print("=" * 60)
    
    key_fields = [
        "Submission ID", "Site Number", "Vendor Name", "Survey Type",
        "Processing Status", "Score", "True Score", "Fail Summary",
        "Notes for Internal", "Date of Survey"
    ]
    
    for key in key_fields:
        val = fields.get(key, "(not set)")
        print(f"{key}: {val}")
    
    print("=" * 60)
    print("All fields (excluding attachments):")
    for k, v in sorted(fields.items()):
        if k not in ["SiteOwl Export File", "Upload File"]:
            val_str = str(v)[:100]
            print(f"  {k}: {val_str}")


if __name__ == "__main__":
    main()
