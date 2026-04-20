"""Analyze what Airtable fields the pipeline is configured to write."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from siteowlqa.config import ATAIRTABLE_FIELDS

print("="*70)
print("AIRTABLE FIELDS CURRENTLY CONFIGURED IN SITEOWLQA")
print("="*70)
print()
print("The pipeline writes to these Airtable fields:")
print()
fields_written = {
    "submission_id": ATAIRTABLE_FIELDS.submission_id,
    "vendor_email": ATAIRTABLE_FIELDS.vendor_email,
    "vendor_name": ATAIRTABLE_FIELDS.vendor_name,
    "site_number": ATAIRTABLE_FIELDS.site_number,
    "attachment": ATAIRTABLE_FIELDS.attachment,
    "status": ATAIRTABLE_FIELDS.status,
    "submitted_at": ATAIRTABLE_FIELDS.submitted_at,
    "score": ATAIRTABLE_FIELDS.score,
    "fail_summary": ATAIRTABLE_FIELDS.fail_summary,
    "notes_internal": ATAIRTABLE_FIELDS.notes_internal,
    "true_score": ATAIRTABLE_FIELDS.true_score,
}

for i, (key, field_name) in enumerate(fields_written.items(), 1):
    print(f"  {i:2}. {field_name:30} (filled on: submit + grading)")

print()
print("="*70)
print("FIELDS WRITTEN DURING GRADING (Step 10 in poll_airtable.py)")
print("="*70)
print()
fields_on_grade = {
    "Processing Status": ATAIRTABLE_FIELDS.status,
    "Score": ATAIRTABLE_FIELDS.score,
    "Fail Summary": ATAIRTABLE_FIELDS.fail_summary,
    "Notes for Internal": ATAIRTABLE_FIELDS.notes_internal,
    "True Score": ATAIRTABLE_FIELDS.true_score,
}

for field_key, field_name in fields_on_grade.items():
    print(f"  [OK] {field_name:30} (from: {field_key})")

print()
print("="*70)
print("ISSUE DIAGNOSIS")
print("="*70)
print()
print("You mentioned: 'Missing columns Comments to True Score'")
print()
print("This suggests your Airtable base has:")
print("  - A field called 'Comments' that isn't in our config")
print("  - Possibly other fields between 'Comments' and 'True Score'")
print()
print("SOLUTION:")
print()
print("1. Check your Airtable base schema by looking at all column headers")
print()
print("2. If 'Comments' is a field that should be filled by the pipeline:")
print("   - Add it to AirtableFields in src/siteowlqa/config.py")
print("   - Update poll_airtable.py to write to it")
print("   - Restart the pipeline")
print()
print("3. If 'Comments' should NOT be filled by pipeline:")
print("   - Check why rows 46-47 are blank")
print("   - Might be a submission that failed to process")
print("   - Check logs: C:\\VUES\\logs\\vues.stdout.log")
print()
