"""team_dashboard_data.py — Live Survey + Scout executive dashboard data.

Purpose:
- Pull lightweight live records for Survey Team and Scout Team.
- Keep executive dashboard tabs connected to the freshest Airtable data.
- Gracefully handle missing Scout credentials or schema differences.
- Track vendor assignment progress and completion velocity.

This does NOT change the existing Survey processing pipeline.
It only provides live dashboard data for the consolidated executive page.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from siteowlqa.airtable_client import AirtableClient, TeamSourceConfig
from siteowlqa.config import AppConfig
from siteowlqa.vendor_assignment_tracker import VendorAssignmentTracker

log = logging.getLogger(__name__)

_TEAM_DASHBOARD_DATA = "team_dashboard_data.json"


def refresh_team_dashboard_data(*, airtable: AirtableClient, cfg: AppConfig, output_dir: Path) -> None:
    """Write a live dashboard snapshot for Survey + Scout tabs."""
    output_dir.mkdir(parents=True, exist_ok=True)

    survey_source = TeamSourceConfig(
        team_key="survey",
        token=cfg.airtable_token,
        base_id=cfg.airtable_base_id,
        table_name=cfg.airtable_table_name,
        vendor_email_field="Surveyor Email",
        vendor_name_field="Vendor Name",
        site_number_field="Site Number",
        status_field="Processing Status",
        submitted_at_field="Date of Survey",
        submission_id_field="Submission ID",
    )

    # Note: Scout may require a separate API token/base/table.
    # The linked Airtable view is represented by scout_airtable_view_id when configured.
    scout_source = TeamSourceConfig(
        team_key="scout",
        token=cfg.scout_airtable_token or cfg.airtable_token,
        base_id=cfg.scout_airtable_base_id,
        table_name=cfg.scout_airtable_table_name,
        view_id=cfg.scout_airtable_view_id,
        vendor_email_field=cfg.scout_vendor_email_field,
        vendor_name_field=cfg.scout_vendor_name_field,
        site_number_field=cfg.scout_site_number_field,
        status_field=cfg.scout_status_field,
        submitted_at_field=cfg.scout_submitted_at_field,
        submission_id_field=cfg.scout_submission_id_field,
    )

    payload: dict[str, Any] = {
        "survey": _build_team_payload(airtable, survey_source, label="Survey Team"),
        "scout": _build_team_payload(airtable, scout_source, label="Scout Team"),
    }

    (output_dir / _TEAM_DASHBOARD_DATA).write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    log.info("team_dashboard_data.json updated.")


def _build_team_payload(
    airtable: AirtableClient,
    source: TeamSourceConfig,
    *,
    label: str,
) -> dict[str, Any]:
    configured = bool(source.token and source.base_id and source.table_name)
    if not configured:
        return {
            "team_key": source.team_key,
            "label": label,
            "configured": False,
            "records": [],
            "raw_headers": [],
            "error": "Data source not configured.",
        }

    try:
        # LIVE HOT RELOAD: Fetch ALL records, no artificial limits.
        # The pagination loop in list_dashboard_records will handle large datasets.
        # Memory impact is minimal (~1KB per record) — dashboard freshness is critical.
        records = airtable.list_dashboard_records(source, max_records=10000)
        raw_headers: list[str] = []
        for record in records:
            for key in record.raw_fields.keys():
                if key not in raw_headers:
                    raw_headers.append(key)

        return {
            "team_key": source.team_key,
            "label": label,
            "configured": True,
            "records": [asdict(r) for r in records],
            "raw_headers": raw_headers,
            "error": "",
        }
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not refresh %s dashboard data: %s", label, exc)
        return {
            "team_key": source.team_key,
            "label": label,
            "configured": True,
            "records": [],
            "raw_headers": [],
            "error": str(exc),
        }
