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


def refresh_dashboards(output_dir: Path) -> None:
    """Re-generate the single executive dashboard from current data."""
    _generate_executive_dashboard(output_dir)


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
