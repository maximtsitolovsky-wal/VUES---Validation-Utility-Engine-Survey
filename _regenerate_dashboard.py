"""Regenerate the executive dashboard."""
import logging
from pathlib import Path

from siteowlqa.dashboard_exec import generate_executive_dashboard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

log.info("Regenerating executive dashboard...")

ui_dir = Path("ui")
output_dir = Path("output")

generate_executive_dashboard(
    ui_dir=ui_dir,
    output_dir=output_dir,
)

log.info("Dashboard regenerated!")
log.info(f"Open: {output_dir / 'executive_dashboard.html'}")
