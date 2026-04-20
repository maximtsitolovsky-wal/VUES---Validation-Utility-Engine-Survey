"""Retest a specific Airtable submission."""
import sys
sys.path.insert(0, 'src')

from siteowlqa.config import load_config
from siteowlqa.airtable_client import AirtableClient
from siteowlqa.archive import Archive
from siteowlqa.memory import Memory
from siteowlqa.poll_airtable import process_record
from siteowlqa.models import AirtableRecord
from siteowlqa.config import ATAIRTABLE_FIELDS as FIELDS

def main():
    record_id = 'recparZPbgryMpINi'
    
    print("Loading config...")
    cfg = load_config()
    airtable = AirtableClient(cfg)
    archive = Archive(cfg.archive_dir)
    memory = Memory(archive)
    
    print(f"\nFetching record: {record_id}")
    fields = airtable.get_record_fields(record_id)
    
    print("\n=== Record Info ===")
    print(f"Site Number: {fields.get('Site Number', 'N/A')}")
    print(f"Vendor: {fields.get('Vendor Name', 'N/A')}")
    print(f"Current Status: {fields.get('Processing Status', 'N/A')}")
    print(f"Score: {fields.get('Score', 'N/A')}")
    print(f"True Score: {fields.get('True Score', 'N/A')}")
    print(f"Submission ID: {fields.get('Submission ID', 'N/A')}")
    
    # Check for attachment
    attachments = fields.get('SiteOwl Export File', [])
    has_attachment = len(attachments) > 0 if attachments else False
    print(f"Has Attachment: {has_attachment}")
    if has_attachment:
        att = attachments[0]
        print(f"  Filename: {att.get('filename', 'N/A')}")
        print(f"  Size: {att.get('size', 0) / 1024:.1f} KB")
        print(f"  URL: {att.get('url', 'N/A')[:80]}...")
    
    # Create AirtableRecord for processing
    if not has_attachment:
        print("\nERROR: No attachment found. Cannot retest.")
        return
    
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
    
    print("\n=== Starting Retest ===")
    print(f"Processing record {record_id}...")
    
    try:
        process_record(
            record=record,
            cfg=cfg,
            airtable=airtable,
            archive=archive,
            memory=memory,
            correction_state=None,
        )
        print("\n✓ Retest completed successfully!")
    except Exception as e:
        print(f"\n✗ Retest failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Fetch updated status
    print("\n=== Updated Record ===")
    updated_fields = airtable.get_record_fields(record_id)
    print(f"New Status: {updated_fields.get('Processing Status', 'N/A')}")
    print(f"New Score: {updated_fields.get('Score', 'N/A')}")
    print(f"New True Score: {updated_fields.get('True Score', 'N/A')}")

if __name__ == "__main__":
    main()
