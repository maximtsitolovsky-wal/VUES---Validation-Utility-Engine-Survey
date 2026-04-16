"""Regenerate the executive dashboard."""
import logging
from pathlib import Path

from siteowlqa.dashboard import refresh_dashboards

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

log.info("Regenerating executive dashboard...")

output_dir = Path("output")

refresh_dashboards(output_dir)

log.info("Dashboard regenerated!")
log.info(f"Open: {output_dir / 'executive_dashboard.html'}")
