"""metrics_worker.py — Dedicated background thread for metrics and dashboard refresh.

Why this exists:
    refresh_all_metrics() and refresh_dashboards() both overwrite shared
    output files (submission_history.csv, vendor_metrics.csv,
    processing_summary.csv, and two HTML files).  If multiple worker
    threads called these functions simultaneously, they would produce
    partially-written or corrupt files (a classic write-race).

    This module solves that by ensuring:
      1. Only ONE thread ever writes to the output files.
      2. Workers never block waiting for a metrics refresh to complete.
      3. Multiple rapid completions are batched into a single refresh.

Protocol:
    - Workers call metrics_worker.mark_dirty() when a submission finishes.
    - This thread wakes up, clears the flag, then runs the refresh.
    - If another submission finishes DURING a refresh, the flag is set
      again immediately and the next iteration picks it up.
    - A periodic backstop refresh runs every REFRESH_INTERVAL_SECONDS
      regardless, so the dashboard never goes stale.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from siteowlqa.archive import Archive
from siteowlqa.airtable_client import AirtableClient
from siteowlqa.config import AppConfig
from siteowlqa.dashboard import refresh_dashboards
from siteowlqa.metrics import refresh_all_metrics
from siteowlqa.realtime_metrics import refresh_realtime_metrics
from siteowlqa.team_dashboard_data import refresh_team_dashboard_data

log = logging.getLogger(__name__)

# Maximum time to wait between refreshes even if no submissions have finished.
# Acts as a heartbeat: keeps the dashboard current if the dirty-flag somehow
# gets missed (e.g. hard restart mid-flight).
_BACKSTOP_INTERVAL_SECONDS: float = 60.0


class MetricsRefreshWorker(threading.Thread):
    """Single-owner thread for all metrics + dashboard output writes.

    Only one instance of this should ever run.  Multiple submission
    workers share a reference to the same instance and call mark_dirty().

    Thread safety:
        mark_dirty()        — uses threading.Event (thread-safe).
        request_shutdown()  — uses threading.Event (thread-safe).
        All file I/O runs exclusively on this thread — no locking needed
        because no other thread ever touches the output files.
    """

    def __init__(
        self,
        archive: Archive,
        output_dir: Path,
        cfg: AppConfig,
        airtable: AirtableClient | None = None,
        backstop_interval: float = _BACKSTOP_INTERVAL_SECONDS,
    ) -> None:
        super().__init__(name="MetricsRefresher", daemon=True)
        self._archive = archive
        self._output_dir = output_dir
        self._cfg = cfg
        self._airtable = airtable
        self._backstop_interval = backstop_interval

        # Set when a worker finishes a submission and wants a refresh.
        # Cleared at the START of each refresh (not the end), so any
        # new completions during a refresh are captured on the next loop.
        self._dirty = threading.Event()

        # Set to request a clean exit from the run() loop.
        self._stop = threading.Event()

    # ------------------------------------------------------------------
    # Public API (called from worker threads)
    # ------------------------------------------------------------------

    def mark_dirty(self) -> None:
        """Signal that a submission has finished and metrics need refreshing.

        Safe to call from any thread.  Returns immediately.
        """
        self._dirty.set()
        log.debug("Metrics marked dirty — refresh will trigger shortly.")

    def request_shutdown(self) -> None:
        """Ask the thread to exit after finishing any in-progress refresh."""
        self._stop.set()
        self._dirty.set()  # wake the thread immediately if it is waiting
        log.info("MetricsRefreshWorker shutdown requested.")

    # ------------------------------------------------------------------
    # Thread entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Loop: wait for dirty flag or backstop timeout, then refresh."""
        log.info(
            "MetricsRefreshWorker started (backstop interval=%.0fs).",
            self._backstop_interval,
        )

        # Do one initial refresh on startup to catch any submissions that
        # arrived while the previous process was not running.
        self._refresh()

        while not self._stop.is_set():
            # Block until dirty-flag is set OR backstop interval expires.
            self._dirty.wait(timeout=self._backstop_interval)

            if self._stop.is_set():
                break

            # Clear the flag BEFORE refreshing.  Any new mark_dirty() call
            # that arrives during the refresh will set it again, ensuring
            # the next iteration catches those completions too.
            self._dirty.clear()
            self._refresh()

        # Final refresh on shutdown so the dashboard reflects the last run.
        log.info("MetricsRefreshWorker: final refresh on shutdown.")
        self._refresh()
        log.info("MetricsRefreshWorker stopped.")

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        """Run the full metrics + dashboard refresh.  Errors are non-fatal."""
        try:
            refresh_all_metrics(self._archive, self._output_dir)
            if self._airtable is not None:
                refresh_realtime_metrics(airtable=self._airtable, output_dir=self._output_dir)
                refresh_team_dashboard_data(airtable=self._airtable, cfg=self._cfg, output_dir=self._output_dir)
            refresh_dashboards(self._output_dir)
            log.info("Metrics and dashboards refreshed successfully.")
        except Exception as exc:  # noqa: BLE001
            log.error(
                "MetricsRefreshWorker: refresh failed (will retry on next cycle): %s",
                exc,
            )