"""Backfill Airtable records that are missing Score / True Score.

How it works:
  1. Fetches ALL Airtable records (all statuses)
  2. Finds records where Score OR True Score is blank
  3. If Processing Status is PASS  -> backfill Score=100.0%, True Score=100.0
  4. If Processing Status is FAIL  -> check archive CSV for saved score,
     then patch it back. If archive has no score, patch Score=0.0%, True Score=0.0.
  5. If Processing Status is neither (still QUEUED/PROCESSING/blank) -> skip.

Run: python scripts/backfill_scores.py           (live mode)
     python scripts/backfill_scores.py --dry-run  (preview only)
"""

from __future__ import annotations

import csv
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from siteowlqa.airtable_client import AirtableClient
from siteowlqa.config import (
    AppConfig,
    STATUS_PASS,
    STATUS_FAIL,
    ATAIRTABLE_FIELDS as FIELDS,
    load_config,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("backfill_scores")


def _load_archive_scores(cfg: AppConfig) -> dict[str, float]:
    """Return mapping of submission_id -> score from the local archive CSV."""
    archive_csv = cfg.archive_dir / "submission_history.csv"
    scores: dict[str, float] = {}
    if not archive_csv.exists():
        log.warning("Archive CSV not found at %s — no fallback scores", archive_csv)
        return scores

    with open(archive_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = (row.get("submission_id") or row.get("record_id") or "").strip()
            raw_score = (row.get("score") or "").strip()
            if sid and raw_score and raw_score not in ("None", "null", ""):
                try:
                    scores[sid] = float(raw_score)
                except ValueError:
                    pass
    log.info("Loaded %d archive scores from %s", len(scores), archive_csv)
    return scores


def run_backfill(cfg: AppConfig, dry_run: bool = False) -> None:
    """Main backfill routine."""
    airtable = AirtableClient(cfg)
    archive_scores = _load_archive_scores(cfg)

    log.info("Fetching ALL Airtable records (raw, no filter)...")
    all_records = airtable.list_all_raw_records()  # raw dicts: {id, fields}
    log.info("Fetched %d records from Airtable.", len(all_records))

    candidates: list[dict] = []
    for rec in all_records:
        fields = rec.get("fields", {})
        score_val = fields.get(FIELDS.score)
        true_score_val = fields.get(FIELDS.true_score)
        status_val = (fields.get(FIELDS.status) or "").strip()

        score_blank = score_val is None or str(score_val).strip() == ""
        true_blank = true_score_val is None or str(true_score_val).strip() == ""

        if (score_blank or true_blank) and status_val in (STATUS_PASS, STATUS_FAIL):
            candidates.append({
                "record_id": rec["id"],
                "submission_id": (fields.get(FIELDS.submission_id) or rec["id"]).strip(),
                "status": status_val,
                "score_blank": score_blank,
                "true_blank": true_blank,
            })

    log.info(
        "Found %d records with blank Score or True Score (PASS or FAIL only).",
        len(candidates),
    )

    if not candidates:
        log.info("Nothing to backfill. All done!")
        return

    patched = 0
    skipped = 0

    for rec in candidates:
        record_id = rec["record_id"]
        submission_id = rec["submission_id"]
        status = rec["status"]

        if status == STATUS_PASS:
            backfill_score = 100.0
            log.info(
                "[PASS] %s -> backfill Score=100.0%%, True Score=100.0",
                submission_id,
            )
        else:  # FAIL
            # Try to get score from archive
            backfill_score = archive_scores.get(
                submission_id,
                archive_scores.get(record_id, 0.0),
            )
            log.info(
                "[FAIL] %s -> backfill Score=%.2f%% (from archive=%s)",
                submission_id,
                backfill_score,
                backfill_score in archive_scores.values(),
            )

        if dry_run:
            log.info("  [DRY RUN] Would patch record=%s score=%.2f", record_id, backfill_score)
            skipped += 1
            continue

        try:
            # Use targeted patch: ONLY writes Score + True Score.
            # Does NOT touch Status, Notes for Internal, or Fail Summary.
            # This preserves all other data on the record.
            airtable.patch_score_and_true_score(record_id, backfill_score)
            log.info("  [OK] Patched record=%s", record_id)
            patched += 1
        except Exception as exc:  # noqa: BLE001
            log.error("  [FAIL] Could not patch record=%s: %s", record_id, exc)
            skipped += 1

    log.info(
        "Backfill complete: %d patched, %d skipped (dry_run=%s).",
        patched, skipped, dry_run,
    )


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv or "-n" in sys.argv
    if dry:
        log.info("=== DRY RUN MODE — no changes will be written ===")

    try:
        cfg = load_config()
    except Exception as e:
        log.error("Config load failed: %s", e)
        log.error("Run `python -m siteowlqa.setup_config` first.")
        sys.exit(1)

    run_backfill(cfg, dry_run=dry)
