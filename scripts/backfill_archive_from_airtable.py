"""Backfill archive from existing Airtable submissions.

When archive/ is empty but Airtable has processed submissions (PASS/FAIL/ERROR),
this script reconstructs the archive so metrics and dashboards show full history.

Usage:
    python scripts/backfill_archive_from_airtable.py

What it does:
    1. Fetches all processed submissions from Airtable (all statuses)
    2. Creates SubmissionArchiveRecord for each one
    3. Saves to archive/submissions/YYYY/MM/DD/
    4. Does NOT re-download vendor files (those are likely gone or in OneDrive)
    5. Logs what was backfilled

After running this:
    - Run metrics_worker manually or wait for next refresh
    - Dashboard will show all submissions
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from siteowlqa.archive import Archive
from siteowlqa.airtable_client import AirtableClient
from siteowlqa.config import load_config
from siteowlqa.models import SubmissionArchiveRecord

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def backfill_archive_from_airtable() -> None:
    """Backfill archive from all processed Airtable submissions."""
    
    log.info("=" * 70)
    log.info("ARCHIVE BACKFILL FROM AIRTABLE")
    log.info("=" * 70)
    
    cfg = load_config()
    airtable = AirtableClient(cfg)
    archive = Archive(Path("archive"))
    
    # Get ALL records from Airtable (not just pending)
    log.info("Fetching all submissions from Airtable...")
    all_records = airtable.list_all_records()
    log.info(f"Found {len(all_records)} total records in Airtable")
    
    # Filter to only processed ones (have a status)
    processed = [r for r in all_records if r.processing_status]
    log.info(f"  → {len(processed)} have been processed (have a status)")
    
    if not processed:
        log.warning("No processed submissions found in Airtable. Nothing to backfill.")
        return
    
    # Check current archive count
    current_count = archive.count_submissions()
    log.info(f"Current archive count: {current_count} submissions")
    
    if current_count >= len(processed):
        log.info("Archive already has same or more submissions than Airtable.")
        log.info("Nothing to backfill. If this seems wrong, check archive/ directory.")
        return
    
    # Backfill each processed submission
    log.info("")
    log.info("Starting backfill...")
    log.info("")
    
    backfilled = 0
    skipped = 0
    errors = 0
    
    for i, record in enumerate(processed, 1):
        status = record.processing_status
        
        # Try to parse a score from the Airtable record
        # (Airtable doesn't store score separately in our schema, so we'll set it to None)
        # If you have a score field, add it to AirtableRecord model and use it here
        score = None  # Could parse from error message or add Score field to Airtable
        
        # Determine processed_at timestamp
        # If submitted_at exists, use it; otherwise use current time
        if record.submitted_at:
            try:
                processed_at = record.submitted_at
            except Exception:
                processed_at = datetime.now(timezone.utc).isoformat()
        else:
            processed_at = datetime.now(timezone.utc).isoformat()
        
        # Create archive record
        archive_record = SubmissionArchiveRecord(
            record_id=record.record_id,
            submission_id=record.submission_id,
            vendor_email=record.vendor_email,
            vendor_name=record.vendor_name,
            site_number=record.site_number,
            attachment_filename=record.attachment_filename,
            archived_file_path="",  # No raw file - wasn't saved originally
            submitted_at=record.submitted_at or processed_at,
            processed_at=processed_at,
            status=status,
            score=score,
            error_count=0,  # Unknown - not tracked in Airtable
            output_report_path=None,
            sql_project_key=record.site_number,
            execution_id=f"backfill_{record.record_id}",
            notes=f"Backfilled from Airtable on {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            team_key=record.team_key,
        )
        
        try:
            # Save to archive (no raw file to copy)
            archive.save_submission_archive(archive_record, raw_file_path=None)
            backfilled += 1
            
            if i % 10 == 0:
                log.info(f"  [{i}/{len(processed)}] Backfilled {backfilled} submissions...")
            
        except Exception as exc:
            log.error(f"Failed to backfill {record.record_id}: {exc}")
            errors += 1
    
    # Summary
    log.info("")
    log.info("=" * 70)
    log.info("BACKFILL COMPLETE")
    log.info("=" * 70)
    log.info(f"Backfilled:  {backfilled}")
    log.info(f"Skipped:     {skipped}")
    log.info(f"Errors:      {errors}")
    log.info(f"Total:       {len(processed)}")
    log.info("")
    log.info(f"Archive now has {archive.count_submissions()} submissions")
    log.info("")
    log.info("Next steps:")
    log.info("  1. Metrics will auto-refresh on next cycle (or run metrics manually)")
    log.info("  2. Dashboard will show all submissions")
    log.info("  3. Check output/submission_history.csv to verify")


if __name__ == "__main__":
    backfill_archive_from_airtable()
