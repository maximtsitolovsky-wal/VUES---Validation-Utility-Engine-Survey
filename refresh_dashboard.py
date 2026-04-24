#!/usr/bin/env python
"""
refresh_dashboard.py — Refresh team_dashboard_data.json from Airtable.

Run this script periodically to keep the dashboard data fresh.
The HTML pages auto-refresh every 15 seconds to pick up changes.

Usage:
    python refresh_dashboard.py           # Run once
    python refresh_dashboard.py --watch   # Run continuously every 5 minutes
"""

import argparse
import logging
import time
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


def refresh_data() -> bool:
    """Refresh team_dashboard_data.json from Airtable."""
    try:
        from siteowlqa.config import load_config
        from siteowlqa.airtable_client import AirtableClient
        from siteowlqa.team_dashboard_data import refresh_team_dashboard_data
        
        cfg = load_config()
        airtable = AirtableClient(cfg)
        output_dir = Path("output")
        
        log.info("Fetching fresh data from Airtable...")
        refresh_team_dashboard_data(airtable=airtable, cfg=cfg, output_dir=output_dir)
        log.info(f"✅ Dashboard data refreshed at {datetime.now().strftime('%H:%M:%S')}")
        return True
        
    except Exception as e:
        log.error(f"❌ Failed to refresh: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Refresh dashboard data from Airtable")
    parser.add_argument("--watch", action="store_true", help="Run continuously every 5 minutes")
    parser.add_argument("--interval", type=int, default=300, help="Refresh interval in seconds (default: 300)")
    args = parser.parse_args()
    
    if args.watch:
        log.info(f"🔄 Starting continuous refresh (every {args.interval}s). Press Ctrl+C to stop.")
        while True:
            refresh_data()
            log.info(f"Next refresh in {args.interval} seconds...")
            time.sleep(args.interval)
    else:
        success = refresh_data()
        exit(0 if success else 1)


if __name__ == "__main__":
    main()
