"""Manually trigger metrics refresh."""
import logging
from pathlib import Path

from siteowlqa.archive import Archive
from siteowlqa.config import load_config
from siteowlqa.metrics import refresh_all_metrics

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

# Refresh all metrics
refresh_all_metrics(archive, output_dir)

log.info("Metrics refresh complete!")
log.info("Check output/ directory for updated CSVs")
