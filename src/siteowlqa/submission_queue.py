"""submission_queue.py — Thread-safe submission queue with deduplication.

Dropped between the poll loop and the worker threads.
Prevents the same Airtable record_id from being processed twice while it
is still in flight (QUEUED or PROCESSING). Once task_done() is called the
record_id is cleared from the seen-set, so resubmissions are allowed.

No external dependencies — stdlib queue + threading only.
"""

from __future__ import annotations

import logging
import queue
import threading

from siteowlqa.models import AirtableRecord

log = logging.getLogger(__name__)

# Unique object — never equals an AirtableRecord.  Sending this into the
# queue tells a worker to exit its run() loop cleanly.
_SHUTDOWN = object()


class SubmissionQueue:
    """FIFO queue for AirtableRecord objects with record-level deduplication.

    Thread-safety guarantees:
      - enqueue() / task_done() guard the seen-set with a Lock.
      - dequeue() delegates to queue.Queue which is natively thread-safe.
      - Multiple concurrent callers of enqueue() will never insert the same
        record_id twice.

    Typical lifecycle:
      poll thread  →  enqueue(record)            # returns True
      poll thread  →  enqueue(same record again)  # returns False (dup guard)
      worker thread → dequeue()                  # receives the record
      worker thread → task_done(record_id)       # clears from seen-set
    """

    def __init__(self, maxsize: int = 0) -> None:
        # maxsize=0 → unbounded (safe for our expected volumes)
        self._q: queue.Queue = queue.Queue(maxsize=maxsize)
        self._seen: set[str] = set()    # record_ids currently in-flight
        self._lock = threading.Lock()   # guards _seen only

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enqueue(self, record: AirtableRecord) -> bool:
        """Add *record* to the queue.

        Returns True if enqueued, False if that record_id is already
        in-flight (duplicate guard).
        """
        with self._lock:
            if record.record_id in self._seen:
                log.debug(
                    "Duplicate skip — record %s is already in flight.",
                    record.record_id,
                )
                return False
            self._seen.add(record.record_id)

        self._q.put(record)
        log.info(
            "Queued: record=%s submission=%s site=%s  (queue depth=%d)",
            record.record_id,
            record.submission_id,
            record.site_number,
            self._q.qsize(),
        )
        return True

    def dequeue(self, timeout: float = 5.0) -> AirtableRecord | object | None:
        """Pull the next item from the queue.

        Returns:
          - AirtableRecord  — normal submission to process
          - _SHUTDOWN       — worker should stop (check with is_shutdown)
          - None            — timeout, nothing available (loop and retry)
        """
        try:
            return self._q.get(timeout=timeout)
        except queue.Empty:
            return None

    def task_done(self, record_id: str) -> None:
        """Mark one record as fully processed.

        Removes record_id from the seen-set so a genuine resubmission of
        the same Airtable record can be processed again in the future.
        Also signals queue.Queue.task_done() for join() support.
        """
        self._q.task_done()
        with self._lock:
            self._seen.discard(record_id)
        log.debug("task_done: record %s cleared from in-flight set.", record_id)

    def request_shutdown(self, num_workers: int) -> None:
        """Push N shutdown sentinels — one per worker — so every worker exits."""
        for _ in range(num_workers):
            self._q.put(_SHUTDOWN)
        log.info(
            "Shutdown sentinels sent to %d worker(s).", num_workers
        )

    def size(self) -> int:
        """Approximate number of pending items (not including in-progress)."""
        return self._q.qsize()

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def is_shutdown(item: object) -> bool:
        """True when *item* is the shutdown sentinel (not a real record)."""
        return item is _SHUTDOWN