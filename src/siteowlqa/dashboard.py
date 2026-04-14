"""dashboard.py — Single-page executive dashboard generation for SiteOwlQA.

This module intentionally generates ONE final HTML artifact only:
    output/executive_dashboard.html

Legacy split dashboards were removed in favor of a consolidated executive page.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

from siteowlqa.dashboard_exec import generate_executive_dashboard

log = logging.getLogger(__name__)

_EXEC_HTML = "executive_dashboard.html"
_EXEC_TEMPLATE = "ui/executive_dashboard.html"
_UI_ASSETS_DIR = "ui/assets"
_OUTPUT_ASSETS_DIR = "assets"
_SUBMISSION_HISTORY_CSV = "submission_history.csv"
_ARCH_MAP_SRC = "orchestration_map.html"  # in repo root


def refresh_dashboards(output_dir: Path) -> None:
    """Re-generate the single executive dashboard from current data."""
    _generate_executive_dashboard(output_dir)
    _copy_architecture_map(output_dir)


def _copy_architecture_map(output_dir: Path) -> None:
    """Copy orchestration_map.html from repo root into output/ so the local
    HTTP server can serve it alongside the dashboard.
    """
    import shutil
    root = Path(__file__).resolve().parents[2]  # repo root (src/siteowlqa/dashboard.py → ../../)
    src = root / _ARCH_MAP_SRC
    if not src.exists():
        log.warning("orchestration_map.html not found at %s — skipping copy", src)
        return
    dst = output_dir / _ARCH_MAP_SRC
    shutil.copy2(src, dst)
    log.debug("Architecture map copied to %s", dst)


def _generate_executive_dashboard(output_dir: Path) -> None:
    history_rows = _read_csv(output_dir / _SUBMISSION_HISTORY_CSV)
    generate_executive_dashboard(
        output_dir=output_dir,
        template_rel_path=_EXEC_TEMPLATE,
        ui_assets_rel_dir=_UI_ASSETS_DIR,
        output_assets_rel_dir=_OUTPUT_ASSETS_DIR,
        out_name=_EXEC_HTML,
        history_rows=history_rows,
    )


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))
