"""queue_worker.py — Background worker thread for async submission grading.

Each worker:
  1. Marks the Airtable record as PROCESSING (immediate UI feedback)
  2. Calls process_record() — the existing full 15-step pipeline
  3. Calls task_done() so the record_id is cleared from the seen-set

Multiple workers run simultaneously, each processing one submission.
They share only the SubmissionQueue plus the usual shared app dependencies.
No SQL grading mutex is needed because grading is Python-owned.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archive import Archive
    from airtable_client import AirtableClient
    from config import AppConfig
    from memory import Memory
    from metrics_worker import MetricsRefreshWorker
    from submission_queue import SubmissionQueue

from siteowlqa.config import STATUS_PROCESSING
from siteowlqa.correction_state import CorrectionStateDB
from siteowlqa.metrics_worker import MetricsRefreshWorker
from siteowlqa.models import AirtableRecord
from siteowlqa.poll_airtable import process_record
from siteowlqa.submission_queue import SubmissionQueue

log = logging.getLogger(__name__)


class SubmissionWorker(threading.Thread):
    """Daemon thread that drains one item at a time from *queue*.

    Workers are daemon threads — they die automatically when the main thread
    exits, which is the correct behaviour for a long-running service.
    Use run_forever() in main.py for orderly shutdown via Ctrl+C.
    """

    def __init__(
        self,
        worker_id: int,
        queue: SubmissionQueue,
        cfg: AppConfig,
        airtable: AirtableClient,
        archive: Archive,
        memory: Memory,
        metrics_worker: MetricsRefreshWorker,
        correction_state: CorrectionStateDB | None = None,
    ) -> None:
        super().__init__(
            name=f"Worker-{worker_id}",
            daemon=True,
        )
        self._id = worker_id
        self._queue = queue
        self._cfg = cfg
        self._airtable = airtable
        self._archive = archive
        self._memory = memory
        self._metrics_worker = metrics_worker
        self._correction_state = correction_state

    # ------------------------------------------------------------------
    # Thread entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Drain the queue forever (or until a shutdown sentinel arrives)."""
        log.info("Worker-%d started.", self._id)

        while True:
            item = self._queue.dequeue(timeout=5.0)

            if item is None:
                # Timeout — no items yet, loop and wait.
                continue

            if SubmissionQueue.is_shutdown(item):
                log.info("Worker-%d received shutdown signal. Exiting.", self._id)
                break

            record: AirtableRecord = item  # type: ignore[assignment]
            self._process(record)

        log.info("Worker-%d stopped.", self._id)

    # ------------------------------------------------------------------
    # Per-record logic
    # ------------------------------------------------------------------

    def _process(self, record: AirtableRecord) -> None:
        """Mark as PROCESSING then run the full 14-step pipeline.

        Errors here are caught and logged — a single bad record must
        never crash the worker thread.
        """
        try:
            # Immediately tell Airtable (and anyone watching) this is in work.
            self._mark_processing(record)

            process_record(
                record=record,
                cfg=self._cfg,
                airtable=self._airtable,
                archive=self._archive,
                memory=self._memory,
                correction_state=self._correction_state,
            )
        except Exception:  # noqa: BLE001
            log.exception(
                "Worker-%d: unhandled exception for record=%s submission=%s",
                self._id,
                record.record_id,
                record.submission_id,
            )
        finally:
            # Signal metrics worker regardless of pass/fail/error outcome.
            # This runs AFTER archive writes, so the new JSON files exist.
            self._metrics_worker.mark_dirty()
            # Always release the record from the in-flight set, even on crash.
            self._queue.task_done(record.record_id)

    def _mark_processing(self, record: AirtableRecord) -> None:
        """Best-effort Airtable status update to PROCESSING.

        Failure is non-fatal — the pipeline continues regardless.
        The status will eventually be overwritten by PASS / FAIL / ERROR.
        """
        try:
            self._airtable.update_status(record.record_id, STATUS_PROCESSING)
            log.info(
                "Worker-%d: record=%s → PROCESSING",
                self._id,
                record.record_id,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "Worker-%d: could not mark PROCESSING for record=%s: %s",
                self._id,
                record.record_id,
                exc,
            )