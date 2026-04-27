"""survey_routing.py — Survey Routing + Vendor Output Sheet logic.

Evaluates scout responses to determine:
- Whether each site needs a survey
- Survey type: CCTV, FA/INTRUSION, BOTH, NONE, or REVIEW
- Full upgrade scenarios
- Supplemental flags
- 165-day construction scheduling

Data Sources:
- Airtable Scout Table (source of truth for scout answers)
- Excel workbook (vendor ownership and timing)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

log = logging.getLogger(__name__)

# Airtable Scout Table
SCOUT_BASE_ID = "appAwgaX89x0JxG3Z"
SCOUT_TABLE_ID = "tblC4o9AvVulyxFMk"

# Excel workbook path
DEFAULT_WORKBOOK_PATH = (
    r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Documents\BaselinePrinter\2027 Survey Lab.xlsm"
)

# Scheduling threshold
CONSTRUCTION_DEADLINE_DAYS = 165

# Valid survey vendors (only these should appear in output)
VALID_SURVEY_VENDORS = {"Wachter", "CEI", "Everon"}

# Invalid values to filter out
INVALID_VALUES = {"#REF!", "#N/A", "#VALUE!", "#ERROR!", "MAXIM"}


@dataclass
class SurveyRoutingRow:
    """Final output row for vendor-ready table."""
    site: str
    vendor: str
    days_to_construction: str
    survey_required: str  # YES, NO, REVIEW
    survey_type: str  # CCTV, FA/INTRUSION, BOTH, NONE, REVIEW
    upgrade_decision: str
    reason_for_decision: str
    schedule_status: str  # NOT REQUIRED, ON TRACK, URGENT, REVIEW
    ready_to_assign: str  # YES, NO
    supplemental_flags: str
    vendor_instructions: str
    survey_complete: bool = False  # Column V from Excel


@dataclass
class ScoutAnswers:
    """Parsed scout answers from Airtable."""
    site: str
    record_id: str
    # FA/Intrusion fields
    one_notification_device: bool = False
    ceiling_mounted_devices: bool = False
    sales_floor_column_devices: bool = False
    emergency_exit_only_devices: bool = False
    fire_panel_type: str = ""
    # CCTV fields
    coax_siamese_cable: bool = False
    analog_baluns_present: bool = False
    rooftop_trimount_present: bool = False
    rooftop_trimount_count: int = 0
    cable_condition: str = ""
    homerun_cabling_present: bool = False
    ap_office_moving: str = ""  # YES, NO, or blank
    raw_fields: dict = field(default_factory=dict)


@dataclass
class ScheduleData:
    """Data from Excel workbook."""
    site: str
    vendor: str
    days_to_construction: int | None
    survey_complete: bool = False  # Column V from Excel
    

def _normalize_site(site: str | int | float | None) -> str:
    """Normalize site ID for consistent joining.
    
    Strips leading zeros so '0336' matches '336'.
    """
    if site is None:
        return ""
    site_str = str(site).strip()
    # Remove .0 from float conversion
    if site_str.endswith(".0"):
        site_str = site_str[:-2]
    # Strip leading zeros for consistent matching
    # But keep at least one digit (so "0" stays "0")
    site_str = site_str.lstrip("0") or "0"
    return site_str


def _is_yes(value: Any) -> bool:
    """Check if a value represents YES/True."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().upper() in ("YES", "TRUE", "1", "Y")
    return bool(value)


def _is_blank(value: Any) -> bool:
    """Check if a value is blank/empty."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def fetch_scout_data(token: str) -> list[ScoutAnswers]:
    """Fetch scout responses from Airtable."""
    url = f"https://api.airtable.com/v0/{SCOUT_BASE_ID}/{SCOUT_TABLE_ID}"
    headers = {"Authorization": f"Bearer {token}"}
    
    all_records = []
    offset = None
    
    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset
            
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            log.error(f"Failed to fetch scout data from Airtable: {e}")
            break
            
        records = data.get("records", [])
        all_records.extend(records)
        
        offset = data.get("offset")
        if not offset:
            break
    
    log.info(f"Fetched {len(all_records)} scout records from Airtable")
    
    # Parse into ScoutAnswers objects
    parsed = []
    for rec in all_records:
        fields = rec.get("fields", {})
        site = _normalize_site(fields.get("Site Number") or fields.get("Site") or fields.get("site"))
        
        if not site:
            continue
            
        # Map Airtable field names to our structure
        # These field names need to match the actual Airtable schema EXACTLY
        answers = ScoutAnswers(
            site=site,
            record_id=rec.get("id", ""),
            # FA/Intrusion
            one_notification_device=_is_yes(fields.get("Does this site only have one notification device located in the store? (Usually at the Service Desk)")),
            ceiling_mounted_devices=_is_yes(fields.get("Are any notification devices ceiling mounted?")),
            sales_floor_column_devices=_is_yes(fields.get("Are any notification devices mounted on sales floor columns?")),
            emergency_exit_only_devices=_is_yes(fields.get("Are notification devices installed only above emergency exits?")),
            fire_panel_type=str(fields.get("Fire Panel Type", "") or ""),
            # CCTV
            coax_siamese_cable=_is_yes(fields.get("Coax or Siamese Cable")),
            analog_baluns_present=_is_yes(fields.get("Analog CCTV Baluns Present?")),
            rooftop_trimount_present=_is_yes(fields.get("Rooftop Tri-Mount Present")),
            rooftop_trimount_count=int(fields.get("Rooftop Tri-Mount Count") or 0) if fields.get("Rooftop Tri-Mount Count") else 0,
            cable_condition=str(fields.get("Cable Condition", "") or ""),
            homerun_cabling_present=_is_yes(fields.get("Homerun Cabling Present")),
            ap_office_moving=str(fields.get("AP Office Moving", "") or "").strip().upper(),
            raw_fields=fields,
        )
        parsed.append(answers)
    
    return parsed


def load_schedule_data(workbook_path: str | Path) -> list[ScheduleData]:
    """Load vendor and timing data from Excel workbook.
    
    Only includes rows with valid survey vendors (Wachter, CEI, Everon).
    Filters out #REF!, MAXIM, and other invalid values.
    """
    try:
        import openpyxl
    except ImportError:
        log.error("openpyxl not installed - cannot read Excel workbook")
        return []
    
    path = Path(workbook_path)
    if not path.exists():
        log.warning(f"Workbook not found: {path}")
        return []
    
    try:
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    except Exception as e:
        log.error(f"Failed to open workbook {path}: {e}")
        return []
    
    if "Project Tracking" not in wb.sheetnames:
        log.warning(f"Sheet 'Project Tracking' not found in {path}")
        wb.close()
        return []
    
    ws = wb["Project Tracking"]
    data = []
    skipped = 0
    
    # Column A = Site, Column V = Survey Complete, Column X = Days to Construction, Column Y = Vendor
    # openpyxl is 1-indexed, so A=1, V=22, X=24, Y=25
    for row in ws.iter_rows(min_row=2, values_only=True):  # Skip header
        if not row or len(row) < 25:
            continue
            
        site = _normalize_site(row[0])  # Column A
        if not site:
            continue
        
        # Skip invalid site values
        if site in INVALID_VALUES or site.startswith("#"):
            skipped += 1
            continue
        
        # Column V (0-indexed: 21) = Survey Complete checkbox
        survey_complete_raw = row[21] if len(row) > 21 else None
        survey_complete = _is_yes(survey_complete_raw)
            
        days_raw = row[23]  # Column X (0-indexed: 23)
        vendor = str(row[24] or "").strip()  # Column Y (0-indexed: 24)
        
        # Skip invalid vendor values and non-survey vendors
        if vendor in INVALID_VALUES or vendor.startswith("#"):
            vendor = ""  # Clear invalid vendor
        elif vendor and vendor not in VALID_SURVEY_VENDORS:
            vendor = ""  # Not a survey vendor - clear it
        
        days = None
        if days_raw is not None:
            try:
                days = int(float(days_raw))
            except (ValueError, TypeError):
                pass
        
        data.append(ScheduleData(site=site, vendor=vendor, days_to_construction=days, survey_complete=survey_complete))
    
    wb.close()
    if skipped > 0:
        log.info(f"Skipped {skipped} invalid rows from Excel")
    log.info(f"Loaded {len(data)} schedule rows from {path}")
    return data


def evaluate_site(scout: ScoutAnswers | None, schedule: ScheduleData | None) -> SurveyRoutingRow:
    """Apply all routing logic to determine survey requirements.
    
    Logic order:
    1. Full upgrade triggers (override survey need for that category)
    2. Survey triggers (for categories without full upgrade)
    3. Supplemental flags (informational)
    4. Scheduling logic
    5. Vendor instructions
    """
    
    # Determine site ID
    site = scout.site if scout else (schedule.site if schedule else "UNKNOWN")
    
    # Get schedule data
    vendor = schedule.vendor if schedule else ""
    days = schedule.days_to_construction if schedule else None
    days_str = str(days) if days is not None else ""
    survey_complete = schedule.survey_complete if schedule else False
    
    # Handle missing scout data
    if scout is None:
        return SurveyRoutingRow(
            site=site,
            vendor=vendor,
            days_to_construction=days_str,
            survey_required="REVIEW",
            survey_type="REVIEW",
            upgrade_decision="REVIEW REQUIRED",
            reason_for_decision="No scout submission found.",
            schedule_status="REVIEW",
            ready_to_assign="NO",
            supplemental_flags="",
            vendor_instructions="Do not assign survey until internal review is completed.",
            survey_complete=survey_complete,
        )
    
    if schedule is None:
        vendor = ""
        days_str = ""
    
    supplemental_flags_list = []
    reasons = []
    needs_review = False
    
    # === STEP 1: Check Full Upgrade Triggers ===
    # These determine if a survey is NOT needed for that category
    
    # FA/Intrusion Full Upgrade: only one notification device = YES
    fa_full_upgrade = scout.one_notification_device
    
    # CCTV Full Upgrade: coax/siamese cable = YES
    cctv_full_upgrade = scout.coax_siamese_cable
    
    # Conditional CCTV Full Upgrade: homerun + AP office moving = YES
    if scout.homerun_cabling_present and not cctv_full_upgrade:
        if scout.ap_office_moving == "YES":
            cctv_full_upgrade = True
        elif _is_blank(scout.ap_office_moving):
            # Homerun present but AP office status unknown - needs review
            needs_review = True
            supplemental_flags_list.append("AP office move status missing — internal review required.")
    
    # === STEP 2: Check Survey Triggers for categories WITHOUT full upgrade ===
    fa_survey_needed = False
    cctv_survey_needed = False
    
    # FA/Intrusion survey triggers (only check if no FA full upgrade)
    if not fa_full_upgrade:
        if scout.ceiling_mounted_devices:
            fa_survey_needed = True
            supplemental_flags_list.append("Ceiling mounted notification devices")
        if scout.sales_floor_column_devices:
            fa_survey_needed = True
            supplemental_flags_list.append("Notification devices on sales floor columns")
        if scout.emergency_exit_only_devices:
            fa_survey_needed = True
            supplemental_flags_list.append("Notification devices only above emergency exits")
        if scout.fire_panel_type:
            fa_survey_needed = True
            supplemental_flags_list.append(f"Fire panel type: {scout.fire_panel_type}")
    
    # CCTV survey triggers (only check if no CCTV full upgrade)
    if not cctv_full_upgrade:
        if scout.analog_baluns_present:
            cctv_survey_needed = True
            supplemental_flags_list.append("Analog CCTV baluns present")
        if scout.rooftop_trimount_present:
            cctv_survey_needed = True
            supplemental_flags_list.append("Rooftop tri-mount present")
        if scout.rooftop_trimount_count > 0:
            cctv_survey_needed = True
            supplemental_flags_list.append(f"Rooftop tri-mount count: {scout.rooftop_trimount_count}")
        if scout.cable_condition:
            cctv_survey_needed = True
            supplemental_flags_list.append(f"Cable condition: {scout.cable_condition}")
        if scout.homerun_cabling_present and not needs_review:
            # Only add as trigger if not already flagged for review
            cctv_survey_needed = True
            supplemental_flags_list.append("Homerun cabling present")
    
    # === STEP 3: Determine Final Survey Type and Decision ===
    
    # Handle review case first
    if needs_review:
        survey_required = "REVIEW"
        survey_type = "REVIEW"
        upgrade_decision = "REVIEW REQUIRED"
        reason = "Homerun cabling is present, but AP office move status is unknown."
    
    # Both full upgrades - no survey at all
    elif fa_full_upgrade and cctv_full_upgrade:
        survey_required = "NO"
        survey_type = "NONE"
        upgrade_decision = "FULL BOTH UPGRADE"
        reason = "Both FA/Intrusion and CCTV full upgrade triggers present. No survey needed."
    
    # FA full upgrade only - check if CCTV survey still needed
    elif fa_full_upgrade and not cctv_full_upgrade:
        if cctv_survey_needed:
            survey_required = "YES"
            survey_type = "CCTV"
            upgrade_decision = "FULL FA/INTRUSION UPGRADE + CCTV SURVEY"
            reason = "FA/Intrusion full upgrade (one notification device). CCTV survey still required."
        else:
            survey_required = "NO"
            survey_type = "NONE"
            upgrade_decision = "FULL FA/INTRUSION UPGRADE"
            reason = "Site has only one notification device. Full FA/Intrusion upgrade required. No survey needed."
    
    # CCTV full upgrade only - check if FA survey still needed
    elif cctv_full_upgrade and not fa_full_upgrade:
        if fa_survey_needed:
            survey_required = "YES"
            survey_type = "FA/INTRUSION"
            upgrade_decision = "FULL CCTV UPGRADE + FA/INTRUSION SURVEY"
            reason = "CCTV full upgrade (coax/siamese cable). FA/Intrusion survey still required."
        else:
            survey_required = "NO"
            survey_type = "NONE"
            upgrade_decision = "FULL CCTV UPGRADE"
            reason = "Coax or Siamese cabling present. Full CCTV upgrade required. No survey needed."
    
    # No full upgrades - check survey triggers
    elif fa_survey_needed and cctv_survey_needed:
        survey_required = "YES"
        survey_type = "BOTH"
        upgrade_decision = "SURVEY REQUIRED"
        reason = "Both FA/Intrusion and CCTV survey triggers present."
    elif fa_survey_needed:
        survey_required = "YES"
        survey_type = "FA/INTRUSION"
        upgrade_decision = "SURVEY REQUIRED"
        reason = "FA/Intrusion survey triggers present."
    elif cctv_survey_needed:
        survey_required = "YES"
        survey_type = "CCTV"
        upgrade_decision = "SURVEY REQUIRED"
        reason = "CCTV survey triggers present."
    else:
        # No triggers at all
        survey_required = "REVIEW"
        survey_type = "REVIEW"
        upgrade_decision = "REVIEW REQUIRED"
        reason = "No clear survey or upgrade triggers found. Manual review required."
    
    # === STEP 4: Scheduling Logic ===
    if survey_required == "NO":
        schedule_status = "NOT REQUIRED"
    elif days is None:
        schedule_status = "REVIEW"
    elif days > CONSTRUCTION_DEADLINE_DAYS:
        schedule_status = "ON TRACK"
    else:
        schedule_status = "URGENT"
    
    # === STEP 5: Ready to Assign ===
    # If scout data exists and a decision is made (not REVIEW), ready to assign
    if survey_required in ("YES", "NO"):
        ready_to_assign = "YES"
    else:
        ready_to_assign = "NO"
    
    # Handle missing schedule data
    if schedule is None:
        schedule_status = "REVIEW"
        ready_to_assign = "NO"
    
    # === STEP 6: Vendor Instructions ===
    if survey_type == "CCTV":
        vendor_instructions = "Complete CCTV mapped survey with GPS. Review supplemental CCTV flags before submission."
    elif survey_type == "FA/INTRUSION":
        vendor_instructions = "Complete FA/Intrusion mapped survey without GPS. Review supplemental fire alarm flags before submission."
    elif survey_type == "BOTH":
        vendor_instructions = "Complete CCTV mapped survey with GPS and FA/Intrusion mapped survey without GPS. Review all supplemental flags before submission."
    elif survey_required == "NO":
        vendor_instructions = "No survey required. Site is routed to full upgrade based on scout trigger."
    else:
        vendor_instructions = "Do not assign survey until internal review is completed."
    
    return SurveyRoutingRow(
        site=site,
        vendor=vendor,
        days_to_construction=days_str,
        survey_required=survey_required,
        survey_type=survey_type,
        upgrade_decision=upgrade_decision,
        reason_for_decision=reason,
        schedule_status=schedule_status,
        ready_to_assign=ready_to_assign,
        supplemental_flags="; ".join(supplemental_flags_list),
        vendor_instructions=vendor_instructions,
        survey_complete=survey_complete,
    )


def build_survey_routing_data(
    token: str,
    workbook_path: str | Path = DEFAULT_WORKBOOK_PATH,
) -> dict[str, Any]:
    """Build complete survey routing dataset."""
    
    # Fetch data from both sources
    scout_records = fetch_scout_data(token)
    schedule_records = load_schedule_data(workbook_path)
    
    # Index by site
    scout_by_site = {s.site: s for s in scout_records}
    schedule_by_site = {s.site: s for s in schedule_records}
    
    # Get all unique sites
    all_sites = set(scout_by_site.keys()) | set(schedule_by_site.keys())
    
    # Evaluate each site
    rows = []
    for site in sorted(all_sites):
        scout = scout_by_site.get(site)
        schedule = schedule_by_site.get(site)
        row = evaluate_site(scout, schedule)
        rows.append(asdict(row))
    
    # Calculate summary stats
    total = len(rows)
    surveys_required = sum(1 for r in rows if r["survey_required"] == "YES")
    surveys_complete = sum(1 for r in rows if r["survey_complete"])
    full_upgrades = sum(1 for r in rows if "FULL" in r["upgrade_decision"])
    review_required = sum(1 for r in rows if r["survey_required"] == "REVIEW")
    urgent_sites = sum(1 for r in rows if r["schedule_status"] == "URGENT")
    ready_to_assign = sum(1 for r in rows if r["ready_to_assign"] == "YES")
    
    # Survey type breakdown (only for sites that need surveys)
    cctv_surveys = sum(1 for r in rows if r["survey_type"] == "CCTV")
    fa_surveys = sum(1 for r in rows if r["survey_type"] == "FA/INTRUSION")
    both_surveys = sum(1 for r in rows if r["survey_type"] == "BOTH")
    
    # Full upgrade breakdown
    # CCTV full upgrade = no CCTV survey needed (coax/siamese cable)
    full_cctv = sum(1 for r in rows if "FULL CCTV" in r["upgrade_decision"] or "FULL BOTH" in r["upgrade_decision"])
    # FA full upgrade = no FA survey needed (one notification device)
    full_fa = sum(1 for r in rows if "FULL FA" in r["upgrade_decision"] or "FULL BOTH" in r["upgrade_decision"])
    # Both full upgrade = no survey at all
    full_both = sum(1 for r in rows if "FULL BOTH" in r["upgrade_decision"])
    
    return {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_sites": total,
            "surveys_required": surveys_required,
            "surveys_complete": surveys_complete,
            "cctv_surveys": cctv_surveys,
            "fa_surveys": fa_surveys,
            "both_surveys": both_surveys,
            "full_upgrades": full_upgrades,
            "full_cctv": full_cctv,
            "full_fa": full_fa,
            "full_both": full_both,
            "review_required": review_required,
            "urgent_sites": urgent_sites,
            "ready_to_assign": ready_to_assign,
        },
        "rows": rows,
    }


def refresh_survey_routing(token: str, output_dir: Path | str, workbook_path: str | Path = DEFAULT_WORKBOOK_PATH) -> None:
    """Refresh survey routing data and write to JSON."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    data = build_survey_routing_data(token, workbook_path)
    
    output_file = output_dir / "survey_routing_data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    log.info(
        f"Survey routing data updated: {data['summary']['total_sites']} sites, "
        f"{data['summary']['surveys_required']} surveys required, "
        f"{data['summary']['full_upgrades']} full upgrades"
    )
