"""Regrade a single record by record ID."""
import sys
sys.path.insert(0, 'src')

from siteowlqa.config import load_config, ATAIRTABLE_FIELDS as FIELDS
from siteowlqa.airtable_client import AirtableClient
from siteowlqa.archive import Archive
from siteowlqa.memory import Memory
from siteowlqa.poll_airtable import process_record
from siteowlqa.models import AirtableRecord
from siteowlqa.correction_state import CorrectionStateDB

RECORD_ID = 'rec4K3ukMKat6CBE0'

print(f"[REGRADE] Loading config...")
cfg = load_config()
airtable = AirtableClient(cfg)
archive = Archive(cfg.archive_dir)
memory = Memory(archive)
corrections_dir = cfg.correction_log_dir or (cfg.output_dir / "corrections")
correction_state = CorrectionStateDB(corrections_dir)

print(f"[FETCH] Getting record {RECORD_ID}...")
fields = airtable.get_record_fields(RECORD_ID)

print(f"Site Number: {fields.get('Site Number')}")
print(f"Vendor: {fields.get('Vendor Name')}")
print(f"Current Status: {fields.get('Processing Status')}")
print(f"Current Score: {fields.get('Score')}")

# Get attachment using the config field name
att_field = fields.get(FIELDS.attachment, [])
if not att_field:
    print(f"[ERROR] No attachment in field '{FIELDS.attachment}'!")
    sys.exit(1)

att = att_field[0]
print(f"Attachment: {att.get('filename')} ({att.get('size', 0)/1024:.1f} KB)")

record = AirtableRecord(
    record_id=RECORD_ID,
    submission_id=fields.get('Submission ID', ''),
    site_number=str(fields.get('Site Number', '')),
    vendor_name=fields.get('Vendor Name', ''),
    vendor_email=fields.get('Surveyor Email', ''),
    attachment_url=att.get('url', ''),
    attachment_filename=att.get('filename', ''),
    processing_status=fields.get('Processing Status', ''),
    submitted_at=fields.get('Date of Survey', ''),
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
updated = airtable.get_record_fields(RECORD_ID)
print(f"\n[RESULT] Updated Status: {updated.get('Processing Status')}")
print(f"[RESULT] Updated Score: {updated.get('Score')}")
print(f"[RESULT] Updated True Score: {updated.get('True Score')}")
