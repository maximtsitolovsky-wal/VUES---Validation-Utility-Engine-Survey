"""dashboard.py — UI file deployment for VUES Command Center.

This module copies the UI pages from ui/ to output/ and handles any
data file updates needed for the dashboard to display current metrics.

UI Structure:
    - index.html          (Landing page / Command Center)
    - survey.html         (Survey Program)
    - scout.html          (Scout Program)
    - analytics.html      (Analytics Hub)
    - summary.html        (Executive Summary)
    - orchestration_map.html (Architecture)

All pages read live data from team_dashboard_data.json in output/.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

log = logging.getLogger(__name__)

_UI_DIR = "ui"
_UI_PAGES = [
    "index.html",
    "survey.html",
    "scout.html",
    "analytics.html",
    "summary.html",
    "orchestration_map.html",
    "howitworks.html",
]
_UI_ASSETS_DIR = "ui/assets"
_OUTPUT_ASSETS_DIR = "assets"


def refresh_dashboards(output_dir: Path) -> None:
    """Copy UI pages from ui/ to output/ for serving."""
    _copy_ui_pages(output_dir)
    _copy_assets(output_dir)


def _copy_ui_pages(output_dir: Path) -> None:
    """Copy all UI HTML pages to output directory."""
    root = Path(__file__).resolve().parents[2]  # repo root
    ui_dir = root / _UI_DIR
    
    for page in _UI_PAGES:
        src = ui_dir / page
        if not src.exists():
            log.warning("UI page not found: %s", src)
            continue
        dst = output_dir / page
        shutil.copy2(src, dst)
        log.debug("Copied %s to %s", page, dst)
    
    log.info("UI pages refreshed in %s", output_dir)


def _copy_assets(output_dir: Path) -> None:
    """Copy UI assets (images, etc.) to output directory."""
    root = Path(__file__).resolve().parents[2]
    src_assets = root / _UI_ASSETS_DIR
    dst_assets = output_dir / _OUTPUT_ASSETS_DIR
    
    if not src_assets.exists():
        log.debug("No UI assets directory found at %s", src_assets)
        return
    
    if dst_assets.exists():
        shutil.rmtree(dst_assets)
    
    shutil.copytree(src_assets, dst_assets)
    log.debug("Assets copied to %s", dst_assets)
