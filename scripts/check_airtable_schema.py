#!/usr/bin/env python3
"""Diagnostic: Check Airtable field schema and compare with config."""

import json
import sys
from pathlib import Path

# Add src/ to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from siteowlqa.airtable_client import AirtableClient
from siteowlqa.config import load_config, ATAIRTABLE_FIELDS


def main():
    try:
        cfg = load_config()
    except Exception as e:
        print(f"ERROR loading config: {e}")
        print("Run: python -m siteowlqa.setup_config")
        return 1
    
    print("="*70)
    print("AIRTABLE SCHEMA DIAGNOSTIC")
    print("="*70)
    print(f"\nBase ID:      {cfg.airtable_base_id}")
    print(f"Table:        {cfg.airtable_table_name}")
    print()
    
    # Get Airtable schema via API
    client = AirtableClient(cfg)
    
    print("\n[1] Fetching Airtable schema...")
    try:
        import requests
        from siteowlqa.airtable_client import AIRTABLE_API_BASE
        
        # Get table metadata (requires Airtable's Tables API)
        # https://airtable.com/api/meta
        headers = {
            "Authorization": f"Bearer {cfg.airtable_token}",
        }
        
        # Tables API endpoint
        meta_url = f"{AIRTABLE_API_BASE}/meta/bases/{cfg.airtable_base_id}/tables"
        resp = requests.get(meta_url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        # Find our table
        our_table = None
        for table in data.get("tables", []):
            if table["name"] == cfg.airtable_table_name:
                our_table = table
                break
        
        if not our_table:
            print(f"ERROR: Table '{cfg.airtable_table_name}' not found in base")
            print("\nAvailable tables:")
            for table in data.get("tables", []):
                print(f"  - {table['name']}")
            return 1
        
        print(f"✓ Found table: {our_table['name']}\n")
        
        # List all fields
        print("[2] Fields in your Airtable base:")
        print("-" * 70)
        airtable_fields = {}
        for field in our_table.get("fields", []):
            field_id = field["id"]
            field_name = field["name"]
            field_type = field.get("type", "unknown")
            airtable_fields[field_name] = field
            print(f"  {field_name:40} ({field_type})")
        
        print()
        print("[3] Fields configured in SiteOwlQA (src/siteowlqa/config.py):")
        print("-" * 70)
        configured_fields = {
            "submission_id": ATAIRTABLE_FIELDS.submission_id,
            "vendor_email": ATAIRTABLE_FIELDS.vendor_email,
            "vendor_name": ATAIRTABLE_FIELDS.vendor_name,
            "site_number": ATAIRTABLE_FIELDS.site_number,
            "attachment": ATAIRTABLE_FIELDS.attachment,
            "status": ATAIRTABLE_FIELDS.status,
            "submitted_at": ATAIRTABLE_FIELDS.submitted_at,
            "score": ATAIRTABLE_FIELDS.score,
            "true_score": ATAIRTABLE_FIELDS.true_score,
            "fail_summary": ATAIRTABLE_FIELDS.fail_summary,
            "notes_internal": ATAIRTABLE_FIELDS.notes_internal,
        }
        
        for key, field_name in configured_fields.items():
            exists = "✓" if field_name in airtable_fields else "✗"
            print(f"  {exists} {key:25} → '{field_name}'")
        
        # Check for mismatch
        print()
        print("[4] Mismatches:")
        print("-" * 70)
        
        missing = []
        for key, field_name in configured_fields.items():
            if field_name not in airtable_fields:
                missing.append((key, field_name))
        
        if missing:
            print("\n⚠ MISSING FIELDS (configured but not in Airtable):")
            for key, field_name in missing:
                print(f"  - {key}: '{field_name}'")
            print()
            print("  ACTION: Add these fields to your Airtable base, or")
            print("          update src/siteowlqa/config.py AirtableFields")
        else:
            print("✓ No missing fields")
        
        # Check for extra fields
        extra = []
        for field_name in airtable_fields:
            if field_name not in [v for v in configured_fields.values()]:
                extra.append(field_name)
        
        if extra:
            print("\n⚠ EXTRA FIELDS (in Airtable but not configured):")
            for field_name in sorted(extra):
                print(f"  - '{field_name}'")
            print()
            print("  These fields won't be written to by the pipeline.")
            print("  If they should be filled out, add them to AirtableFields")
            print("  in src/siteowlqa/config.py and update poll_airtable.py")
        else:
            print("\n✓ No extra fields")
        
        print()
        print("="*70)
        print("SUMMARY")
        print("="*70)
        if not missing and not extra:
            print("✓ Your Airtable schema matches the configured fields perfectly!")
            return 0
        else:
            if missing:
                print(f"✗ {len(missing)} field(s) missing in Airtable")
            if extra:
                print(f"⚠ {len(extra)} field(s) in Airtable not configured")
            return 1
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
