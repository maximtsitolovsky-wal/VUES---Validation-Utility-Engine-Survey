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
    print(f"[SEARCH] Looking for Submission ID: {submission_id}")
    
    cfg = load_config()
    airtable = AirtableClient(cfg)
    archive = Archive(cfg.archive_dir)
    memory = Memory(archive)
    
    # CorrectionStateDB lives in corrections subfolder of output_dir
    corrections_dir = cfg.correction_log_dir or (cfg.output_dir / "corrections")
    correction_state = CorrectionStateDB(corrections_dir)
    
    # Fetch all raw records and filter client-side
    print("[FETCH] Loading all raw records from Airtable...")
    all_records = airtable.list_all_raw_records()
    
    # Find by Submission ID first, then by Site Number
    matches = [
        r for r in all_records
        if str(r.get("fields", {}).get("Submission ID", "")) == submission_id
    ]
    
    if not matches:
        print(f"[INFO] No match for Submission ID = {submission_id}, trying Site Number...")
        matches = [
            r for r in all_records
            if str(r.get("fields", {}).get("Site Number", "")) == submission_id
        ]
    
    if not matches:
        print(f"[X] No record found for '{submission_id}' as Submission ID or Site Number.")
        return
    
    print(f"[OK] Found {len(matches)} record(s)")
    
    for raw in matches:
        record_id = raw["id"]
        fields = raw.get("fields", {})
        
        print(f"\n{'='*60}")
        print(f"Record ID: {record_id}")
        print(f"Site Number: {fields.get('Site Number', 'N/A')}")
        print(f"Vendor: {fields.get('Vendor Name', 'N/A')}")
        print(f"Current Status: {fields.get('Processing Status', 'N/A')}")
        print(f"Current Score: {fields.get('Score', 'N/A')}")
        print(f"Current True Score: {fields.get('True Score', 'N/A')}")
        
        # Check for attachment (use the configured field name)
        attachments = fields.get(FIELDS.attachment, [])
        if not attachments:
            print(f"[WARN] No attachment in '{FIELDS.attachment}' -- skipping")
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
        
        print(f"\n[REGRADE] Processing...")
        try:
            process_record(
                record=record,
                cfg=cfg,
                airtable=airtable,
                archive=archive,
                memory=memory,
                correction_state=correction_state,
            )
            print("[OK] Regrade complete!")
        except Exception as e:
            print(f"[FAIL] Regrade failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Show updated status
        updated = airtable.get_record_fields(record_id)
        print(f"\n[RESULT] Updated Status: {updated.get('Processing Status', 'N/A')}")
        print(f"[RESULT] Updated Score: {updated.get('Score', 'N/A')}")
        print(f"[RESULT] Updated True Score: {updated.get('True Score', 'N/A')}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/regrade_single.py <submission_id_or_site_number>")
        sys.exit(1)
    find_and_regrade(sys.argv[1])
