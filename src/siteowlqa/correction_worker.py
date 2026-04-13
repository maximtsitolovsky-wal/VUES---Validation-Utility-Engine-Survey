"""correction_worker.py — Autonomous post-pass correction daemon thread.

Runs independently of the grading pipeline.  Polls Airtable on its own
schedule for PASS records with True Score >= 95.0 and applies corrections
to any that have not already been corrected.

Responsibilities:
  - Own polling loop (CORRECTION_POLL_INTERVAL_SECONDS, default 300 s)
  - Query Airtable: Processing Status = 'PASS' AND True Score >= 95.0
  - Skip records already in CorrectionStateDB (catches both inline Step 15
    successes and any prior worker runs)
  - Resolve vendor file: archive lookup first, re-download fallback
  - Call run_post_pass_correction() for qualifying, uncorrected records
  - Mark corrected records in CorrectionStateDB
  - Never re-grade. Never change pass/fail. Never touch Airtable scores.

This complements the inline Step 15 in poll_airtable.py:
  Step 15 = fast path for submissions graded right now
  CorrectionWorker = catches historical records + safety net for all records

Why two paths?
  A record graded before this feature existed will never re-enter the
  grading pipeline, so Step 15 will never fire for it.  The worker polls
  Airtable continuously and backfills those records automatically.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from siteowlqa.airtable_client import AirtableClient
from siteowlqa.archive import Archive
from siteowlqa.config import AppConfig
from siteowlqa.correction_state import CorrectionStateDB
from siteowlqa.post_pass_correction import TRIGGER_TRUE_SCORE, run_post_pass_correction

log = logging.getLogger(__name__)


class CorrectionWorker(threading.Thread):
    """Daemon thread that autonomously corrects qualifying PASS submissions.

    Start alongside the submission workers in main.py::

        correction_worker = CorrectionWorker(cfg, airtable, archive, state_db)
        correction_worker.start()

    Shutdown::

        correction_worker.request_shutdown()
        correction_worker.join(timeout=30)
    """

    def __init__(
        self,
        cfg: AppConfig,
        airtable: AirtableClient,
        archive: Archive,
        state_db: CorrectionStateDB,
    ) -> None:
        super().__init__(name="CorrectionWorker", daemon=True)
        self._cfg = cfg
        self._airtable = airtable
        self._archive = archive
        self._state_db = state_db
        self._stop = threading.Event()

    # ------------------------------------------------------------------
    # Thread lifecycle
    # ------------------------------------------------------------------

    def request_shutdown(self) -> None:
        log.info("CorrectionWorker: shutdown requested.")
        self._stop.set()

    def run(self) -> None:
        log.info(
            "CorrectionWorker started. Polling every %ds for PASS records "
            "with True Score >= %.1f.",
            self._cfg.correction_poll_interval_seconds,
            TRIGGER_TRUE_SCORE,
        )
        # Run first cycle immediately — don't wait on startup
        self._cycle()
        while not self._stop.wait(timeout=self._cfg.correction_poll_interval_seconds):
            self._cycle()
        log.info("CorrectionWorker stopped.")

    # ------------------------------------------------------------------
    # Poll cycle
    # ------------------------------------------------------------------

    def _cycle(self) -> None:
        """One correction poll cycle. All exceptions are caught — never crashes."""
        try:
            self._do_cycle()
        except Exception as exc:  # noqa: BLE001
            log.exception(
                "CorrectionWorker: unhandled exception in poll cycle (non-fatal): %s", exc
            )

    def _do_cycle(self) -> None:
        log.debug("CorrectionWorker: starting correction poll cycle.")

        # 1. Fetch PASS records with True Score >= threshold from Airtable
        try:
            candidates = self._airtable.get_pass_records_for_correction(
                min_true_score=TRIGGER_TRUE_SCORE,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("CorrectionWorker: Airtable query failed: %s", exc)
            return

        if not candidates:
            log.debug("CorrectionWorker: no qualifying records found this cycle.")
            return

        # 2. Filter out already-corrected records
        new_records = [
            r for r in candidates
            if not self._state_db.is_corrected(r.record_id)
        ]
        log.info(
            "CorrectionWorker: %d qualifying record(s) found, %d already corrected, "
            "%d to process.",
            len(candidates), len(candidates) - len(new_records), len(new_records),
        )

        # 3. Process each uncorrected qualifying record
        for record in new_records:
            if self._stop.is_set():
                log.info("CorrectionWorker: shutdown mid-cycle — stopping.")
                break
            self._correct_one(record)

    # ------------------------------------------------------------------
    # Single-record correction
    # ------------------------------------------------------------------

    def _correct_one(self, record) -> None:  # record: AirtableRecord
        """Apply post-pass correction to one qualifying record."""
        # Read the True Score the grader already posted to Airtable
        true_score = self._resolve_true_score(record)
        if true_score is None:
            log.warning(
                "CorrectionWorker: could not resolve True Score for "
                "record=%s submission=%s — skipping.",
                record.record_id, record.submission_id,
            )
            return

        if true_score < TRIGGER_TRUE_SCORE:
            # Shouldn't happen (Airtable filter should have caught it)
            # but be defensive — never correct a submission that doesn't qualify
            log.debug(
                "CorrectionWorker: record=%s true_score=%.4f < %.1f — skipping.",
                record.record_id, true_score, TRIGGER_TRUE_SCORE,
            )
            return

        log.info(
            "CorrectionWorker: processing record=%s submission=%s site=%s "
            "vendor=%s true_score=%.4f",
            record.record_id, record.submission_id,
            record.site_number, record.vendor_name, true_score,
        )

        # Resolve the vendor file — archive first, re-download as fallback
        vendor_file = self._resolve_vendor_file(record)
        if vendor_file is None:
            log.warning(
                "CorrectionWorker: no vendor file for record=%s — skipping.",
                record.record_id,
            )
            return

        # Run the correction
        try:
            summary = run_post_pass_correction(
                cfg=self._cfg,
                submission_id=record.submission_id,
                site_number=record.site_number,
                vendor_name=record.vendor_name,
                true_score=true_score,
                archived_file_path=vendor_file,
            )
        except Exception as exc:  # noqa: BLE001
            log.exception(
                "CorrectionWorker: correction raised for record=%s: %s",
                record.record_id, exc,
            )
            return

        if summary is None:
            # run_post_pass_correction already logged the reason
            return

        # Mark as corrected so neither this worker nor Step 15 re-runs it
        self._state_db.mark_corrected(
            record.record_id,
            submission_id=record.submission_id,
            site_number=record.site_number,
            vendor_name=record.vendor_name,
            true_score=true_score,
            corrected_csv_path=summary.corrected_csv_path,
            correction_log_path=summary.correction_log_path,
        )
        log.info(
            "CorrectionWorker: ✓ corrected record=%s corrections=%d "
            "review_flags=%d",
            record.record_id,
            summary.total_corrections,
            summary.total_review_flags,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_true_score(self, record) -> float | None:
        """Get the True Score that Airtable currently holds for this record.

        Airtable is the source of truth — use the live field value, not
        anything locally cached, since the worker may process historical
        records where no local grading context exists.
        """
        try:
            fields = self._airtable.get_record_fields(record.record_id)
            raw = fields.get("True Score", None)
            if raw is None or raw == "":
                return None
            return float(raw)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "CorrectionWorker: could not fetch True Score for "
                "record=%s: %s",
                record.record_id, exc,
            )
            return None

    def _resolve_vendor_file(self, record) -> Path | None:
        """Return the local vendor file path for this record.

        Priority:
          1. Local archive (fast, no network call)
          2. Re-download from Airtable attachment URL (fallback)
        """
        # Try archive first
        archived = self._archive.find_archived_file_by_record_id(record.record_id)
        if archived is not None and archived.exists():
            log.debug(
                "CorrectionWorker: using archived file for record=%s: %s",
                record.record_id, archived,
            )
            return archived

        # Fallback: re-download from Airtable (historical records)
        if not record.attachment_url:
            log.warning(
                "CorrectionWorker: record=%s has no attachment URL and no "
                "archived file — cannot correct.",
                record.record_id,
            )
            return None

        log.info(
            "CorrectionWorker: archived file not found for record=%s — "
            "re-downloading from Airtable.",
            record.record_id,
        )
        try:
            downloaded = self._airtable.download_attachment(record)
            return downloaded
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "CorrectionWorker: re-download failed for record=%s: %s",
                record.record_id, exc,
            )
            return None
