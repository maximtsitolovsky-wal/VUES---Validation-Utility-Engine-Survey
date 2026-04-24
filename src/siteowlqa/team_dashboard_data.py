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

# Default path to Scout completion reference Excel
_DEFAULT_SCOUT_REFERENCE_FILE = (
    r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Documents\BaselinePrinter\ScoutSurveyLab.xlsm"
)


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
    # The linked Airtable view is represented by scoairtable_view_id when configured.
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

    scout_payload = _build_team_payload(airtable, scout_source, label="Scout Team")
    
    # Add scout completion stats (Total/Unique/Completed vs Excel reference)
    scout_stats = _compute_scout_completion_stats(scout_payload)
    scout_payload.update(scout_stats)
    
    # Load vendor assignment tracking (if configured)
    vendor_assignments_payload = _build_vendor_assignments_payload(scout_payload)
    
    payload: dict[str, Any] = {
        "survey": _build_team_payload(airtable, survey_source, label="Survey Team"),
        "scout": scout_payload,
        "vendor_assignments": vendor_assignments_payload,
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


def _build_vendor_assignments_payload(scout_payload: dict[str, Any]) -> dict[str, Any]:
    """
    Build vendor assignment tracking payload.
    
    Reads vendor assignments from Excel and compares with Scout completions
    to calculate remaining assignments and completion velocity.
    
    Args:
        scout_payload: Scout team payload containing completed submissions
    
    Returns:
        Dictionary containing vendor assignment stats
    """
    log.info("[VENDOR_ASSIGN] Starting vendor assignment tracking...")
    # Path to vendor assignment file (from environment or default)
    assignment_file = os.getenv(
        "VENDOR_ASSIGNMENT_FILE",
        r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Documents\BaselinePrinter\Excel\Vendor ASSIGN. 4.2.26.xlsx"
    )
    
    log.info("[VENDOR_ASSIGN] Assignment file path: %s", assignment_file)
    
    # Check if configured and file exists
    if not assignment_file or not Path(assignment_file).exists():
        log.warning("[VENDOR_ASSIGN] Vendor assignment file not found or not configured: %s", assignment_file)
        return {
            "configured": False,
            "vendors": [],
            "error": "Vendor assignment file not found or not configured."
        }
    
    try:
        # Initialize tracker and load assignments
        log.info("[VENDOR_ASSIGN] Initializing VendorAssignmentTracker...")
        tracker = VendorAssignmentTracker(assignment_file)
        if not tracker.load_assignments():
            log.warning("[VENDOR_ASSIGN] Failed to load vendor assignments from Excel file.")
            return {
                "configured": False,
                "vendors": [],
                "error": "Failed to load vendor assignments from Excel file."
            }
        
        log.info("[VENDOR_ASSIGN] Loaded %d assignments from Excel", len(tracker.assignments))
        
        # Extract completed submissions from Scout payload
        completed_submissions = []
        if scout_payload.get("configured") and scout_payload.get("records"):
            for record in scout_payload["records"]:
                # Scout uses raw_fields['Complete?'] = 1 to indicate completion
                raw_fields = record.get("raw_fields", {})
                is_complete = raw_fields.get("Complete?") == 1
                
                if is_complete:
                    # Get vendor from 'Surveyor Parent Company' in raw_fields
                    vendor = raw_fields.get("Surveyor Parent Company", "").strip()
                    site = raw_fields.get("Site Number", "").strip()
                    scout_date = raw_fields.get("Scout Date", "")
                    
                    if site and vendor:
                        completed_submissions.append({
                            "site_number": site,
                            "vendor_name": vendor,
                            "submitted_at": scout_date,
                        })
        
        log.info("[VENDOR_ASSIGN] Found %d completed submissions from Scout", len(completed_submissions))
        
        # Calculate vendor stats
        vendor_stats = tracker.calculate_vendor_stats(completed_submissions)
        log.info("[VENDOR_ASSIGN] Calculated stats for %d vendors", len(vendor_stats))
        
        # Convert to list for JSON serialization
        vendors_list = [
            stats.to_dict()
            for stats in vendor_stats.values()
        ]
        
        # Sort by remaining assignments (descending) to show vendors with most work first
        vendors_list.sort(key=lambda x: x["remaining"], reverse=True)
        
        result = {
            "configured": True,
            "vendors": vendors_list,
            "error": "",
            "total_assignments": sum(v["total_assigned"] for v in vendors_list),
            "total_completed": sum(v["completed"] for v in vendors_list),
            "total_remaining": sum(v["remaining"] for v in vendors_list),
        }
        
        log.info("[VENDOR_ASSIGN] Total: %d assigned, %d completed, %d remaining", 
                 result["total_assignments"], result["total_completed"], result["total_remaining"])
        
        return result
        
    except Exception as exc:  # noqa: BLE001
        log.error("[VENDOR_ASSIGN] Error building vendor assignments payload: %s", exc, exc_info=True)
        return {
            "configured": False,
            "vendors": [],
            "error": f"Error loading vendor assignments: {exc}"
        }
