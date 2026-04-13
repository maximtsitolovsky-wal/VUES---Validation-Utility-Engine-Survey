"""correction_state.py — Thread-safe persistent tracker for post-pass corrections.

Stores which Airtable record_ids have already been corrected so neither
the inline Step 15 path nor the autonomous CorrectionWorker double-processes
any submission.

State file:  <output_dir>/corrections/.correction_state.json
Format:      { "record_id": {"corrected_at": ISO8601, "submission_id": ...,
                             "site_number": ..., "true_score": ...}, ... }

Thread safety: all public methods acquire a reentrant threading.Lock.
Persistence  : state is flushed to disk after every write so a process
               restart does not lose records.  Reads from disk are done
               only at construction time.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_STATE_FILENAME = ".correction_state.json"


class CorrectionStateDB:
    """Persistent, thread-safe set of corrected Airtable record IDs.

    Usage::
        state = CorrectionStateDB(output_dir / "corrections")

        if not state.is_corrected("recXXX"):
            run_post_pass_correction(...)
            state.mark_corrected("recXXX", submission_id="...",
                                 site_number="...", true_score=97.5)
    """

    def __init__(self, corrections_dir: Path) -> None:
        corrections_dir.mkdir(parents=True, exist_ok=True)
        self._path = corrections_dir / _STATE_FILENAME
        self._lock = threading.RLock()
        self._state: dict[str, dict[str, Any]] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_corrected(self, record_id: str) -> bool:
        """Return True if this record has already been corrected."""
        with self._lock:
            return record_id in self._state

    def mark_corrected(
        self,
        record_id: str,
        *,
        submission_id: str = "",
        site_number: str = "",
        vendor_name: str = "",
        true_score: float = 0.0,
        corrected_csv_path: str = "",
        correction_log_path: str = "",
    ) -> None:
        """Mark a record as corrected and persist to disk immediately."""
        with self._lock:
            self._state[record_id] = {
                "record_id":          record_id,
                "submission_id":      submission_id,
                "site_number":        site_number,
                "vendor_name":        vendor_name,
                "true_score":         true_score,
                "corrected_at":       datetime.now(timezone.utc).isoformat(),
                "corrected_csv_path": corrected_csv_path,
                "correction_log_path":correction_log_path,
            }
            self._flush()

    def corrected_count(self) -> int:
        """Return total number of records marked as corrected."""
        with self._lock:
            return len(self._state)

    def state_file_path(self) -> Path:
        return self._path

    # ------------------------------------------------------------------
    # Internal persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self._path.exists():
            log.debug("Correction state: no existing state file at %s.", self._path)
            return
        try:
            with open(self._path, encoding="utf-8") as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                self._state = loaded
                log.info(
                    "Correction state loaded: %d record(s) already corrected. (%s)",
                    len(self._state), self._path,
                )
            else:
                log.warning("Correction state file has unexpected format — resetting.")
                self._state = {}
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Could not load correction state (%s) — starting fresh: %s",
                        self._path, exc)
            self._state = {}

    def _flush(self) -> None:
        """Write current state to disk. Caller must hold _lock."""
        try:
            tmp = self._path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self._state, fh, indent=2, ensure_ascii=False, default=str)
            tmp.replace(self._path)  # atomic rename on Windows (same drive)
        except OSError as exc:
            log.error("Could not persist correction state to %s: %s", self._path, exc)
