"""Regrade a single submission by Submission ID.

Usage:
    python scripts/regrade_single.py 686
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from siteowlqa.config import load_config, ATAIRTABLE_FIELDS as FIELDS
from siteowlqa.airtable_client import AirtableClient
from siteowlqa.archive import Archive
from siteowlqa.memory import Memory
from siteowlqa.poll_airtable import process_record
from siteowlqa.models import AirtableRecord
from siteowlqa.correction_state import CorrectionStateDB


def find_and_regrade(submission_id: str) -> None:
    print(f"🔍 Looking for Submission ID: {submission_id}")
    
    cfg = load_config()
    airtable = AirtableClient(cfg)
    archive = Archive(cfg.archive_dir)
    memory = Memory(archive)
    correction_state = CorrectionStateDB(cfg.correction_state_db_path)
    
    # Search for the submission
    formula = f"{{Submission ID}}='{submission_id}'"
    records = airtable.fetch_records(formula=formula)
    
    if not records:
        print(f"❌ No record found with Submission ID = {submission_id}")
        print("   Trying as Site Number instead...")
        formula = f"{{Site Number}}='{submission_id}'"
        records = airtable.fetch_records(formula=formula)
        
        if not records:
            print(f"❌ No record found with Site Number = {submission_id} either.")
            return
        print(f"✅ Found {len(records)} record(s) for Site Number {submission_id}")
    else:
        print(f"✅ Found {len(records)} record(s) for Submission ID {submission_id}")
    
    for rec in records:
        record_id = rec.record_id
        fields = airtable.get_record_fields(record_id)
        
        print(f"\n{'='*60}")
        print(f"Record ID: {record_id}")
        print(f"Site Number: {fields.get('Site Number', 'N/A')}")
        print(f"Vendor: {fields.get('Vendor Name', 'N/A')}")
        print(f"Current Status: {fields.get('Processing Status', 'N/A')}")
        print(f"Current Score: {fields.get('Score', 'N/A')}")
        print(f"Current True Score: {fields.get('True Score', 'N/A')}")
        
        # Check for attachment
        attachments = fields.get('SiteOwl Export File', [])
        if not attachments:
            print("⚠️  No attachment — skipping")
            continue
        
        att = attachments[0]
        record = AirtableRecord(
            record_id=record_id,
            submission_id=fields.get('Submission ID', ''),
            site_number=str(fields.get('Site Number', '')),
            vendor_name=fields.get('Vendor Name', ''),
            vendor_email=fields.get('Surveyor Email', ''),
            attachment_url=att.get('url', ''),
            attachment_filename=att.get('filename', ''),
            processing_status=fields.get('Processing Status', ''),
            created_time=fields.get('Created', ''),
        )
        
        print(f"\n🔄 Regrading...")
        try:
            process_record(
                record=record,
                cfg=cfg,
                airtable=airtable,
                archive=archive,
                memory=memory,
                correction_state=correction_state,
            )
            print("✅ Regrade complete!")
        except Exception as e:
            print(f"❌ Regrade failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Show updated status
        updated = airtable.get_record_fields(record_id)
        print(f"\n📊 Updated Status: {updated.get('Processing Status', 'N/A')}")
        print(f"📊 Updated Score: {updated.get('Score', 'N/A')}")
        print(f"📊 Updated True Score: {updated.get('True Score', 'N/A')}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/regrade_single.py <submission_id_or_site_number>")
        sys.exit(1)
    find_and_regrade(sys.argv[1])
