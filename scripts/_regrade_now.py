"""Regrade single record."""
import sys
sys.path.insert(0, 'src')
from siteowlqa.config import load_config, ATAIRTABLE_FIELDS as FIELDS
from siteowlqa.airtable_client import AirtableClient
from siteowlqa.archive import Archive
from siteowlqa.memory import Memory
from siteowlqa.poll_airtable import process_record
from siteowlqa.models import AirtableRecord
from siteowlqa.correction_state import CorrectionStateDB

RECORD_ID = 'recryYpfpuVlYKm1g'
cfg = load_config()
airtable = AirtableClient(cfg)
archive = Archive(cfg.archive_dir)
memory = Memory(archive)
corrections_dir = cfg.correction_log_dir or (cfg.output_dir / 'corrections')
correction_state = CorrectionStateDB(corrections_dir)

fields = airtable.get_record_fields(RECORD_ID)
print(f'Site: {fields.get("Site Number")} | Status: {fields.get("Processing Status")}')

att_field = fields.get(FIELDS.attachment, [])
if not att_field:
    print('NO ATTACHMENT!')
    sys.exit(1)

att = att_field[0]
print(f'Attachment: {att.get("filename")}')

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

print('Regrading...')
try:
    process_record(record=record, cfg=cfg, airtable=airtable, archive=archive, memory=memory, correction_state=correction_state)
    print('OK!')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()

updated = airtable.get_record_fields(RECORD_ID)
print(f'RESULT: {updated.get("Processing Status")} | Score: {updated.get("Score")} | True: {updated.get("True Score")}')
