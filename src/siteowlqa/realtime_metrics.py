"""realtime_metrics.py — Lightweight live metrics pulled from Airtable.

Purpose:
- Provide leadership-facing operational signals that are not derivable from
  the historical archive alone (e.g. current queue depth).

Outputs (written to output_dir):
- realtime_snapshot.json  — current counts
- queue_trend.csv         — append-only time series for queue charting

Notes:
- Keep Airtable calls minimal to avoid rate limits.
- Treat failures as non-fatal: dashboards should still generate.
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from siteowlqa.airtable_client import AirtableClient
from siteowlqa.config import STATUS_PROCESSING, STATUS_QUEUED

log = logging.getLogger(__name__)

_SNAPSHOT_NAME = "realtime_snapshot.json"
_QUEUE_TREND_NAME = "queue_trend.csv"


@dataclass(frozen=True)
class RealtimeSnapshot:
    generated_at_utc: str
    queued_count: int
    processing_count: int

    @property
    def queue_total(self) -> int:
        return self.queued_count + self.processing_count


def refresh_realtime_metrics(*, airtable: AirtableClient, output_dir: Path) -> None:
    """Fetch realtime queue counts from Airtable and write snapshot + trend."""
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        queued = airtable.get_records_by_statuses({STATUS_QUEUED})
        processing = airtable.get_records_by_statuses({STATUS_PROCESSING})
        snap = RealtimeSnapshot(
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            queued_count=len(queued),
            processing_count=len(processing),
        )

        (output_dir / _SNAPSHOT_NAME).write_text(
            json.dumps(asdict(snap), indent=2),
            encoding="utf-8",
        )

        _append_queue_trend(output_dir, snap)
        log.info(
            "Realtime snapshot updated: queued=%d processing=%d",
            snap.queued_count,
            snap.processing_count,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("Realtime metrics refresh failed (non-fatal): %s", exc)


def _append_queue_trend(output_dir: Path, snap: RealtimeSnapshot) -> None:
    path = output_dir / _QUEUE_TREND_NAME
    new_file = not path.exists()

    with open(path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["ts_utc", "queued", "processing", "total"],
        )
        if new_file:
            writer.writeheader()

        writer.writerow(
            {
                "ts_utc": snap.generated_at_utc,
                "queued": snap.queued_count,
                "processing": snap.processing_count,
                "total": snap.queue_total,
            }
        )
