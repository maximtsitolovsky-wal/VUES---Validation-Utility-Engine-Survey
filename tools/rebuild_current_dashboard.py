"""Rebuild the current executive dashboard from archive + live Airtable snapshots."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC  = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from siteowlqa.airtable_client import AirtableClient
from siteowlqa.archive import Archive
from siteowlqa.config import load_config
from siteowlqa.dashboard import refresh_dashboards
from siteowlqa.metrics import refresh_all_metrics
from siteowlqa.realtime_metrics import refresh_realtime_metrics
from siteowlqa.team_dashboard_data import refresh_team_dashboard_data
from siteowlqa.utils import configure_logging


def main() -> None:
    logs_dir = ROOT / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    configure_logging(logs_dir)
    log = logging.getLogger(__name__)

    cfg = load_config()
    archive = Archive(cfg.archive_dir)
    airtable = AirtableClient(cfg)

    log.info("Rebuilding current dashboard artifacts in %s", cfg.output_dir)
    refresh_all_metrics(archive, cfg.output_dir)
    refresh_realtime_metrics(airtable=airtable, output_dir=cfg.output_dir)
    refresh_team_dashboard_data(airtable=airtable, cfg=cfg, output_dir=cfg.output_dir)
    refresh_dashboards(cfg.output_dir)
    log.info("Current dashboard rebuild completed.")
    
    # Bake fresh data into UI HTML files for viewer sync (follow-the-leader)
    log.info("Baking fresh data into UI HTML files for viewers...")
    import subprocess
    bake_script = ROOT / "tools" / "bake_data_into_html.py"
    if bake_script.exists():
        result = subprocess.run([sys.executable, str(bake_script)], capture_output=True, text=True)
        if result.returncode == 0:
            log.info("UI HTML files baked successfully - viewers will get fresh data")
        else:
            log.warning("Bake script failed: %s", result.stderr)
    else:
        log.warning("Bake script not found at %s", bake_script)


if __name__ == "__main__":
    main()
