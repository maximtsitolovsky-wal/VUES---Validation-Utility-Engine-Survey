"""main.py — Entry point and polling loop for SiteOwlQA pipeline.

This is the ONLY file you run:
    python main.py

Architecture (async queue model):
 ┌─────────────┐   enqueue()    ┌──────────────────┐
 │ Poll thread │ ─────────────▶ │ SubmissionQueue  │
 │ (main)      │                └────────┬─────────┘
 └─────────────┘                         │  dequeue()
                                ┌────────▼─────────────────┐
                                │  Worker-1  Worker-2  ...  │
                                │  (daemon threads)         │
                                │  QUEUED→PROCESSING→result │
                                └───────────────────────────┘

The poll loop never blocks on grading.  It marks each new record QUEUED,
drops it in the queue, and goes back to sleep.  Workers pick items up
asynchronously and run the full 15-step pipeline.

Crash recovery:
  On startup the app resets any QUEUED or PROCESSING records in Airtable
  back to empty so they are re-picked up by the next poll cycle.  This
  prevents records from getting permanently stuck after a hard crash.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from pathlib import Path

from siteowlqa.local_dashboard_server import ensure_dashboard_server

_LOG_DIR = Path(__file__).parent / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

from siteowlqa.utils import configure_logging  # noqa: E402
configure_logging(_LOG_DIR)

log = logging.getLogger(__name__)

from siteowlqa.archive import Archive
from siteowlqa.airtable_client import AirtableClient
from siteowlqa.config import (
    load_config,
    STATUS_QUEUED,
    STUCK_STATUSES,
)
from siteowlqa.correction_state import CorrectionStateDB
from siteowlqa.correction_worker import CorrectionWorker
from siteowlqa.instance_lock import check_single_instance, generate_instance_id
from siteowlqa.memory import Memory
from siteowlqa.scout_sync_worker import ScoutSyncWorker
from siteowlqa.scout_completion_sync_worker import ScoutCompletionSyncWorker
from siteowlqa.metrics_worker import MetricsRefreshWorker
from siteowlqa.queue_worker import SubmissionWorker
from siteowlqa.reference_data import prewarm_reference_cache
from siteowlqa.submission_queue import SubmissionQueue


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

def _build_banner(version: str = "7.0.0") -> str:
    return (
        "\n"
        "=========================================\n"
        "  VUES - Validation Utility Engine Survey \n"
        f"  Version : {version}                   \n"
        "  Mode    : Full Parallel Python Grading  \n"
        "  Stage   : 1 (Core) + 2 (Governance)   \n"
        "========================================="
    )


# ---------------------------------------------------------------------------
# Dashboard launcher
# ---------------------------------------------------------------------------

_DASHBOARD_DATA_SIGNATURE = "const raw = ["


def _is_generated_dashboard_ready(path: Path, min_mtime: float | None = None) -> bool:
    """Return True only when the generated dashboard exists and is fresh.

    Why so picky?
    A mere exists() check is not enough: a stale or partially-written file can
    still exist, and the raw ui/ template is visually valid but data-empty.
    We only open the dashboard when the generated output contains the embedded
    data signature injected by dashboard_exec.py and, when requested, has been
    regenerated after the current startup.
    """
    if not path.exists() or path.stat().st_size == 0:
        return False

    try:
        stat = path.stat()
        head = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False

    if min_mtime is not None and stat.st_mtime < min_mtime:
        return False

    return _DASHBOARD_DATA_SIGNATURE in head


def _open_dashboards(output_dir: Path, initial_delay: float = 2.0, timeout: float = 30.0) -> None:
    """Open the canonical localhost dashboard after startup.

    Why localhost instead of file:// ?
    - file snapshots are easy to copy, stale, and confuse everyone
    - hosted dashboards can refresh safely without browser file-origin weirdness
    - one canonical URL gives us a single source of truth
    """
    dashboard_name = "executive_dashboard.html"

    def _open() -> None:
        startup_time = time.time()
        time.sleep(initial_delay)
        path = output_dir / dashboard_name
        deadline = time.time() + timeout

        while time.time() < deadline and not _is_generated_dashboard_ready(path, min_mtime=startup_time):
            time.sleep(0.5)

        if not _is_generated_dashboard_ready(path, min_mtime=startup_time):
            log.warning(
                "Fresh dashboard was not ready before timeout; not opening stale dashboard: %s",
                path,
            )
            return

        try:
            server_url = ensure_dashboard_server(output_dir)
            dashboard_url = f"{server_url}/{dashboard_name}"
            os.startfile(dashboard_url)
            log.info("Dashboard opened in browser: %s", dashboard_url)
        except Exception as exc:
            log.warning("Could not open hosted dashboard %s: %s", dashboard_name, exc)

    threading.Thread(target=_open, daemon=True, name="dashboard-opener").start()


# ---------------------------------------------------------------------------
# Crash recovery
# ---------------------------------------------------------------------------

def _recover_stuck_records(airtable: AirtableClient) -> None:
    """Reset QUEUED/PROCESSING records left over from a previous crash.

    After a hard kill or unexpected restart those records would be stuck
    in a non-terminal status and never re-queued (because UNPROCESSED_STATUSES
    does not include QUEUED or PROCESSING).  Resetting them to empty lets the
    next poll cycle pick them up cleanly.
    """
    try:
        stuck = airtable.get_records_by_statuses(STUCK_STATUSES)
        if not stuck:
            log.info("Crash recovery: no stuck records found.")
            return
        log.warning(
            "Crash recovery: resetting %d stuck record(s): %s",
            len(stuck),
            [r.record_id for r in stuck],
        )
        for record in stuck:
            try:
                airtable.update_status(record.record_id, "")
            except Exception as exc:  # noqa: BLE001
                log.error(
                    "Could not reset stuck record %s: %s",
                    record.record_id, exc,
                )
    except Exception as exc:  # noqa: BLE001
        log.warning("Crash recovery query failed (non-fatal): %s", exc)


# ---------------------------------------------------------------------------
# Poll cycle
# ---------------------------------------------------------------------------

def poll_once(
    airtable: AirtableClient,
    queue: SubmissionQueue,
) -> int:
    """Fetch pending Airtable records and drop them in the queue.

    Returns the count of records newly enqueued this cycle.
    Records already in-flight (QUEUED/PROCESSING) are excluded from the
    Airtable query by UNPROCESSED_STATUSES, so no duplicate guard is needed
    at the Airtable level.  The queue's dedup-set covers any edge cases where
    the Airtable write hasn't propagated yet.
    """
    records = airtable.get_pending_records()
    enqueued = 0

    for record in records:
        # Mark QUEUED in Airtable immediately so subsequent poll cycles
        # do not re-fetch this record while it waits in the local queue.
        try:
            airtable.update_status(record.record_id, STATUS_QUEUED)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "Could not mark record %s as QUEUED (will still enqueue): %s",
                record.record_id, exc,
            )

        if queue.enqueue(record):
            enqueued += 1

    return enqueued


# ---------------------------------------------------------------------------
# Worker lifecycle
# ---------------------------------------------------------------------------

def _start_workers(
    cfg,
    airtable: AirtableClient,
    archive: Archive,
    memory: Memory,
    queue: SubmissionQueue,
    metrics_worker: MetricsRefreshWorker,
    correction_state: CorrectionStateDB,
) -> list[SubmissionWorker]:
    """Spawn *cfg.worker_threads* worker threads and return them."""
    workers = [
        SubmissionWorker(
            worker_id=i + 1,
            queue=queue,
            cfg=cfg,
            airtable=airtable,
            archive=archive,
            memory=memory,
            metrics_worker=metrics_worker,
            correction_state=correction_state,
        )
        for i in range(cfg.worker_threads)
    ]
    for w in workers:
        w.start()
    log.info("Started %d worker thread(s).", len(workers))
    return workers


def _shutdown_workers(
    queue: SubmissionQueue,
    workers: list[SubmissionWorker],
    timeout: float = 30.0,
) -> None:
    """Signal all workers to stop and wait for them to finish."""
    log.info("Sending shutdown signals to %d worker(s)...", len(workers))
    queue.request_shutdown(len(workers))
    for w in workers:
        w.join(timeout=timeout)
        if w.is_alive():
            log.warning("%s did not stop within %.0fs.", w.name, timeout)
        else:
            log.info("%s stopped cleanly.", w.name)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_forever() -> None:
    """Main polling loop. Runs until killed."""
    log.info(_build_banner())

    cfg = load_config()
    
    # Single-instance lock — prevents duplicate polling
    # If another instance is running, this will print an error and exit.
    import os
    force_lock = os.getenv("VUES_FORCE_LOCK", "").strip().lower() in ("1", "true")
    if force_lock:
        log.warning("VUES_FORCE_LOCK=1 — forcing lock acquisition (dangerous!)")
    
    from siteowlqa.instance_lock import InstanceLock
    lock = InstanceLock(cfg.log_dir)
    if not lock.acquire(force=force_lock):
        owner = lock.owner_info()
        log.error(
            "Another instance is running! instance=%s pid=%s started=%s",
            owner.get("instance_id") if owner else "unknown",
            owner.get("pid") if owner else "unknown",
            owner.get("started_at") if owner else "unknown",
        )
        print(
            f"\n\u274c Another VUES instance is already running!\n"
            f"   Instance: {owner.get('instance_id') if owner else 'unknown'}\n"
            f"   PID:      {owner.get('pid') if owner else 'unknown'}\n"
            f"   Lock:     {lock.lock_file}\n\n"
            f"   To force: set SITEOWLQA_FORCE_LOCK=1\n"
        )
        import sys
        sys.exit(1)
    
    log.info("Instance ID: %s", lock.instance_id)
    
    airtable = AirtableClient(cfg)
    archive = Archive(cfg.archive_dir)
    memory = Memory(archive)

    # Correction state DB — shared between inline Step 15 and CorrectionWorker
    # so neither ever double-processes the same record.
    corrections_dir = (
        cfg.correction_log_dir
        or cfg.output_dir / "corrections"
    )
    correction_state = CorrectionStateDB(corrections_dir)
    log.info(
        "CorrectionStateDB: %d record(s) already corrected. State file: %s",
        correction_state.corrected_count(),
        correction_state.state_file_path(),
    )

    # Reset any records that were in-flight when the process last died.
    _recover_stuck_records(airtable)

    # Pre-warm the reference workbook cache in a background thread so the
    # first real submission doesn't pay a 35s cold-start penalty.
    # The thread is daemon so it never blocks shutdown.
    threading.Thread(
        target=prewarm_reference_cache,
        args=(cfg,),
        daemon=True,
        name="cache-prewarm",
    ).start()

    # Start the single-owner metrics/dashboard writer BEFORE submission workers.
    # Workers call mark_dirty() on it; it owns all CSV/HTML output writes.
    metrics_worker = MetricsRefreshWorker(archive, cfg.output_dir, cfg, airtable=airtable)
    metrics_worker.start()
    log.info("MetricsRefreshWorker started.")

    queue: SubmissionQueue = SubmissionQueue()
    workers = _start_workers(cfg, airtable, archive, memory, queue, metrics_worker, correction_state)

    # Autonomous correction worker — polls Airtable every
    # CORRECTION_POLL_INTERVAL_SECONDS for PASS records with True Score >= 95.
    # Runs independently of the grading pipeline.
    # Catches historical records + acts as safety net for inline Step 15.
    correction_worker = CorrectionWorker(
        cfg=cfg,
        airtable=airtable,
        archive=archive,
        state_db=correction_state,
    )
    correction_worker.start()
    log.info(
        "CorrectionWorker started. Poll interval: %ds.",
        cfg.correction_poll_interval_seconds,
    )

    scout_sync = ScoutSyncWorker()
    scout_sync.start()
    log.info("ScoutSyncWorker started. Will sync Scout images 60s after startup, then every 6h.")

    scout_completion_sync = ScoutCompletionSyncWorker()
    scout_completion_sync.start()
    log.info("ScoutCompletionSyncWorker started. Will sync completion status 60s after startup, then every 6h.")

    log.info(
        "Startup: executions_archived=%d failure_rate=%.1f%%",
        memory.execution_count(),
        memory.failure_rate() * 100,
    )
    log.info(
        "Polling Airtable every %ds with %d worker(s). Press Ctrl+C to stop.",
        cfg.poll_interval_seconds,
        cfg.worker_threads,
    )

    # Open dashboards in the browser once the first metrics refresh completes.
    _open_dashboards(cfg.output_dir)

    while True:
        try:
            count = poll_once(airtable, queue)
            if count == 0:
                log.debug(
                    "No pending submissions. Queue depth=%d.",
                    queue.size(),
                )
            else:
                log.info(
                    "Poll: %d new submission(s) queued. Queue depth=%d.",
                    count,
                    queue.size(),
                )

        except KeyboardInterrupt:
            log.info("Shutdown requested via Ctrl+C.")
            _shutdown_workers(queue, workers)
            metrics_worker.request_shutdown()
            metrics_worker.join(timeout=30.0)
            correction_worker.request_shutdown()
            correction_worker.join(timeout=30.0)
            scout_sync.request_shutdown()
            scout_sync.join(timeout=10.0)
            scout_completion_sync.request_shutdown()
            scout_completion_sync.join(timeout=10.0)
            log.info("Exiting cleanly.")
            sys.exit(0)

        except Exception as exc:  # noqa: BLE001
            log.exception(
                "Unhandled exception in poll cycle (will retry in %ds): %s",
                cfg.poll_interval_seconds,
                exc,
            )

        time.sleep(cfg.poll_interval_seconds)


if __name__ == "__main__":
    run_forever()