"""Comprehensive lookup of a VUES submission record.

Fetches both:
1. Airtable fields (True Score, Status, Site Number, Vendor Name, etc.)
2. Archived file path from the local archive system
"""

import sys
import json
from pathlib import Path

# Add src to path so we can import siteowlqa modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from siteowlqa.config import load_config
from siteowlqa.airtable_client import AirtableClient
from siteowlqa.archive import Archive

def comprehensive_record_lookup(record_id: str):
    """Fetch and display all information for a specific submission record."""
    
    print(f"{'='*80}")
    print(f"VUES SUBMISSION COMPREHENSIVE LOOKUP")
    print(f"Record ID: {record_id}")
    print(f"{'='*80}\n")
    
    # Load configuration
    print("Loading configuration...")
    try:
        cfg = load_config()
    except Exception as e:
        print(f"ERROR: Failed to load configuration: {e}")
        print("\nMake sure you have run: python -m siteowlqa.setup_config")
        return
    
    # ========================================================================
    # PART 1: Airtable Fields
    # ========================================================================
    print("\n" + "="*80)
    print("PART 1: AIRTABLE RECORD FIELDS")
    print("="*80 + "\n")
    
    print("⏳ Connecting to Airtable...")
    client = AirtableClient(cfg)
    
    print(f"⏳ Fetching record from Airtable...")
    try:
        fields = client.get_record_fields(record_id)
    except Exception as e:
        print(f"❌ ERROR: Failed to fetch record: {e}")
        return
    
    if not fields:
        print(f"❌ No fields found for record {record_id}")
        return
    
    print(f"✅ Found {len(fields)} fields\n")
    
    # Display key fields first
    key_fields = [
        ("True Score", "The final numeric score (0-100)"),
        ("Processing Status", "PASS/FAIL/ERROR status"),
        ("Score", "Score as percentage string"),
        ("Score Numeric", "Score as number"),
        ("Site Number", "Walmart site identifier"),
        ("Vendor Name", "Survey vendor company"),
        ("Surveyor Email", "Email of surveyor"),
        ("Submission ID", "Unique submission identifier"),
        ("Date of Survey", "When survey was conducted"),
        ("Survey Type", "CCTV, FA/Intrusion, or BOTH"),
        ("Comments", "User comments"),
        ("Notes for Internal", "Internal processing notes"),
        ("Fail Summary", "Failure reasons if FAIL"),
    ]
    
    print("🔑 KEY FIELDS:")
    print("-" * 80)
    for field_name, description in key_fields:
        if field_name in fields:
            value = fields[field_name]
            if isinstance(value, str) and len(value) > 300:
                # Show first 300 chars for long text fields
                display_value = value[:300] + "..."
            else:
                display_value = value
            print(f"  {field_name:25s}: {display_value}")
            if field_name == "True Score" or field_name == "Processing Status":
                print(f"  {'':25s}  ({description})")
    
    # Display attachment details
    if "Upload File" in fields:
        print(f"\n📎 ATTACHMENT DETAILS:")
        print("-" * 80)
        attachments = fields["Upload File"]
        if isinstance(attachments, list):
            for i, att in enumerate(attachments):
                if isinstance(att, dict):
                    print(f"  Attachment {i}:")
                    print(f"    Filename: {att.get('filename', 'N/A')}")
                    print(f"    Size:     {att.get('size', 0):,} bytes")
                    print(f"    Type:     {att.get('type', 'N/A')}")
                    print(f"    ID:       {att.get('id', 'N/A')}")
                    # URL can be very long, show truncated
                    url = att.get('url', '')
                    if url:
                        print(f"    URL:      {url[:100]}...")
    
    # Display all other fields
    print(f"\n📋 ALL AIRTABLE FIELDS:")
    print("-" * 80)
    for field_name in sorted(fields.keys()):
        value = fields[field_name]
        if field_name == "Upload File":
            continue  # Already shown above
        
        if isinstance(value, list):
            print(f"  {field_name:30s}: [List with {len(value)} items]")
        elif isinstance(value, dict):
            print(f"  {field_name:30s}: {json.dumps(value)[:100]}...")
        elif isinstance(value, str) and len(value) > 200:
            print(f"  {field_name:30s}: {value[:200]}...")
        else:
            print(f"  {field_name:30s}: {value}")
    
    # ========================================================================
    # PART 2: Archive System
    # ========================================================================
    print("\n" + "="*80)
    print("PART 2: LOCAL ARCHIVE SYSTEM")
    print("="*80 + "\n")
    
    print("⏳ Searching local archive for this submission...")
    archive = Archive(cfg.archive_dir)
    
    archived_file_path = archive.find_archived_file_by_record_id(record_id)
    
    if archived_file_path:
        print(f"✅ FOUND ARCHIVED FILE!")
        print("-" * 80)
        print(f"  Path:     {archived_file_path}")
        print(f"  Exists:   {archived_file_path.exists()}")
        if archived_file_path.exists():
            size = archived_file_path.stat().st_size
            print(f"  Size:     {size:,} bytes ({size / 1024:.1f} KB)")
            print(f"  Modified: {archived_file_path.stat().st_mtime}")
    else:
        print("⚠️  NO ARCHIVED FILE FOUND in local archive")
        print("    This could mean:")
        print("    - The submission is new and hasn't been archived yet")
        print("    - The submission predates the archive system")
        print("    - The archive file was moved or deleted")
    
    # Search for metadata file
    print("\n⏳ Searching for submission metadata...")
    meta_files = list(cfg.archive_dir.rglob(f"{record_id}*_meta.json"))
    
    if meta_files:
        print(f"✅ FOUND METADATA FILE(S):")
        print("-" * 80)
        for meta_file in meta_files:
            print(f"  Metadata: {meta_file}")
            try:
                with open(meta_file, encoding='utf-8') as f:
                    meta_data = json.load(f)
                print(f"  Contains:")
                for key in sorted(meta_data.keys()):
                    val = meta_data[key]
                    if isinstance(val, str) and len(val) > 100:
                        print(f"    {key:25s}: {val[:100]}...")
                    else:
                        print(f"    {key:25s}: {val}")
            except Exception as e:
                print(f"  ⚠️  Could not read metadata: {e}")
    else:
        print("⚠️  NO METADATA FILE FOUND")
    
    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"  Record ID:        {record_id}")
    print(f"  True Score:       {fields.get('True Score', 'N/A')}")
    print(f"  Status:           {fields.get('Processing Status', 'N/A')}")
    print(f"  Site Number:      {fields.get('Site Number', 'N/A')}")
    print(f"  Vendor:           {fields.get('Vendor Name', 'N/A')}")
    print(f"  Survey Type:      {fields.get('Survey Type', 'N/A')}")
    print(f"  Archived File:    {archived_file_path if archived_file_path else 'Not found'}")
    print("="*80 + "\n")

if __name__ == "__main__":
    record_id = "rec4N9ehkQmRjMxnP"
    comprehensive_record_lookup(record_id)
