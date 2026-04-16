"""Manually trigger metrics refresh."""
import logging
from pathlib import Path

from siteowlqa.archive import Archive
from siteowlqa.config import load_config
from siteowlqa.metrics import export_metrics_csvs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

log.info("Refreshing metrics from archive...")

cfg = load_config()
archive = Archive(Path("archive"))
output_dir = Path("output")
output_dir.mkdir(exist_ok=True)

# Load all submissions from archive
submissions = archive.load_all_submission_records()
log.info(f"Loaded {len(submissions)} submissions from archive")

# Export metrics CSVs
export_metrics_csvs(submissions, output_dir)

log.info("Metrics refresh complete!")
log.info("Check output/ directory for updated CSVs")
