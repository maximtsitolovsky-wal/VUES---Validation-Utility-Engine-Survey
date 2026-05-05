"""Generate survey summary data from Airtable Submissions table.

Pulls from:
- Airtable Submissions (apptK6zNN0Hf3OuoJ/tblo5JLmY0XhigcMO) for completed surveys
- survey_routing_data.json for the full site list and routing decisions
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
log = logging.getLogger(__name__)

# Airtable Survey Submissions Table
SURVEY_BASE_ID = "apptK6zNN0Hf3OuoJ"
SURVEY_TABLE_ID = "tblo5JLmY0XhigcMO"

# Vendor colors for UI
VENDOR_COLORS = {
    "CEI": "#22d3ee",
    "Wachter": "#a78bfa", 
    "Everon": "#4ade80",
}


def fetch_survey_submissions(token: str) -> list[dict]:
    """Fetch all survey submissions from Airtable."""
    url = f"https://api.airtable.com/v0/{SURVEY_BASE_ID}/{SURVEY_TABLE_ID}"
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
            log.error(f"Failed to fetch survey submissions: {e}")
            break
            
        records = data.get("records", [])
        for rec in records:
            fields = rec.get("fields", {})
            site = str(fields.get("Site Number") or fields.get("Site") or fields.get("Site #") or "").strip()
            if site.endswith(".0"):
                site = site[:-2]
            site = site.lstrip("0") or "0"
            
            if not site:
                continue
                
            all_records.append({
                "record_id": rec.get("id"),
                "site": site,
                "vendor": fields.get("Vendor") or fields.get("Surveyor Parent Company") or "",
                "status": fields.get("Processing Status") or "",
                "score": fields.get("Score") or fields.get("True Score") or 0,
                "survey_type": fields.get("Survey Type") or "",
                "submitted_at": fields.get("Created") or fields.get("Submitted At") or "",
            })
        
        offset = data.get("offset")
        if not offset:
            break
    
    log.info(f"Fetched {len(all_records)} survey submissions from Airtable")
    return all_records


def load_routing_data(routing_path: Path) -> dict:
    """Load survey routing data."""
    with open(routing_path) as f:
        return json.load(f)


def generate_survey_summary(token: str, routing_path: Path, output_path: Path):
    """Generate survey summary data combining Airtable + routing."""
    
    # Load submissions from Airtable
    submissions = fetch_survey_submissions(token)
    
    # Load routing data
    routing = load_routing_data(routing_path)
    rows = routing.get("rows", [])
    
    # Build lookup of submitted sites
    submitted_sites = {}
    for sub in submissions:
        site = sub["site"]
        if site not in submitted_sites or sub["status"] == "PASS":
            submitted_sites[site] = sub
    
    # Count PASS submissions
    passed_sites = {s["site"] for s in submissions if s["status"] == "PASS"}
    log.info(f"Sites with PASS: {len(passed_sites)}")
    
    # Calculate stats per vendor
    vendor_stats = {}
    for row in rows:
        vendor = row.get("vendor") or "Unknown"
        site = str(row.get("site", ""))
        
        # Map TechWise/SAS to CEI for surveys
        if vendor.lower() in ("techwise", "sas"):
            vendor = "CEI"
        
        if vendor not in vendor_stats:
            vendor_stats[vendor] = {
                "total": 0,
                "no_survey": 0,
                "awaiting_scout": 0,
                "pending": 0,
                "complete": 0,
                "cctv": 0,
                "fa": 0,
                "both": 0,
                "sites": [],
            }
        
        stats = vendor_stats[vendor]
        stats["total"] += 1
        stats["sites"].append(site)
        
        survey_required = row.get("survey_required", "")
        survey_type = row.get("survey_type", "")
        scout_submitted = row.get("scout_submitted", False)
        
        # Check if completed via Airtable
        is_complete = site in passed_sites or row.get("survey_complete", False)
        
        if survey_required == "NO":
            stats["no_survey"] += 1
        elif not scout_submitted:
            stats["awaiting_scout"] += 1
        elif is_complete:
            stats["complete"] += 1
        else:
            stats["pending"] += 1
            
        # Survey type breakdown (only for required surveys)
        if survey_required == "YES":
            if survey_type == "CCTV":
                stats["cctv"] += 1
            elif survey_type == "FA/INTRUSION":
                stats["fa"] += 1
            elif survey_type == "BOTH":
                stats["both"] += 1
    
    # Calculate totals
    totals = {
        "total": sum(v["total"] for v in vendor_stats.values()),
        "no_survey": sum(v["no_survey"] for v in vendor_stats.values()),
        "awaiting_scout": sum(v["awaiting_scout"] for v in vendor_stats.values()),
        "pending": sum(v["pending"] for v in vendor_stats.values()),
        "complete": sum(v["complete"] for v in vendor_stats.values()),
        "cctv": sum(v["cctv"] for v in vendor_stats.values()),
        "fa": sum(v["fa"] for v in vendor_stats.values()),
        "both": sum(v["both"] for v in vendor_stats.values()),
    }
    
    # Calculate velocity (submissions per week)
    from collections import defaultdict
    weekly_submissions = defaultdict(lambda: defaultdict(int))
    for sub in submissions:
        if sub["status"] == "PASS" and sub["submitted_at"]:
            try:
                dt = datetime.fromisoformat(sub["submitted_at"].replace("Z", "+00:00"))
                week = dt.strftime("%Y-W%W")
                vendor = sub["vendor"] or "Unknown"
                if vendor.lower() in ("techwise", "sas"):
                    vendor = "CEI"
                weekly_submissions[week][vendor] += 1
            except:
                pass
    
    # Build output
    output = {
        "generated_at": datetime.now().isoformat(),
        "vendors": {v: {k: stats[k] for k in stats if k != "sites"} for v, stats in vendor_stats.items()},
        "totals": totals,
        "submissions": submissions,
        "passed_sites": list(passed_sites),
        "weekly_velocity": dict(weekly_submissions),
    }
    
    # Remove sites list from vendor stats (too verbose)
    for v in output["vendors"]:
        if "sites" in output["vendors"][v]:
            del output["vendors"][v]["sites"]
    
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    
    log.info(f"Generated survey summary: {totals['total']} sites, {totals['complete']} complete")
    return output


if __name__ == "__main__":
    from siteowlqa.config import load_config
    
    cfg = load_config()
    
    generate_survey_summary(
        token=cfg.airtable_token,
        routing_path=Path("ui/survey_routing_data.json"),
        output_path=Path("ui/survey_summary_data.json"),
    )
