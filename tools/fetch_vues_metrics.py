"""Fetch comprehensive VUES metrics from Airtable for analytics dashboard.

Pulls live data from Survey and Scout tables and calculates:
- Total submissions, pass/fail/error rates
- Vendor performance breakdown
- Weekly/daily trends
- Scout completion progress
- Executive-level actionable metrics
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Any
import json
import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from siteowlqa.config import load_config
from siteowlqa.user_config import load_user_config

AIRTABLE_API_BASE = "https://api.airtable.com/v0"


def fetch_all_records(token: str, base_id: str, table_name: str) -> list[dict[str, Any]]:
    """Fetch all records from an Airtable table."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"{AIRTABLE_API_BASE}/{base_id}/{table_name}"
    all_records = []
    offset = None
    
    while True:
        params = {}
        if offset:
            params["offset"] = offset
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            records = data.get("records", [])
            all_records.extend(records)
            
            offset = data.get("offset")
            if not offset:
                break
                
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Fetching records: {e}")
            return all_records
    
    return all_records


def parse_date(date_str: str) -> datetime | None:
    """Parse date string to datetime."""
    if not date_str:
        return None
    
    for fmt in [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
    ]:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def extract_vendor_from_email(email: str) -> str:
    """Extract vendor name from email domain."""
    if not email:
        return "Unknown"
    
    email = email.lower().strip()
    
    # Known vendor patterns
    if "wachter" in email:
        return "Wachter"
    elif "everon" in email:
        return "Everon"
    elif "convergint" in email:
        return "Convergint"
    elif "walmart" in email:
        return "Walmart (Internal)"
    elif "johnson" in email or "jci" in email:
        return "JCI"
    elif "securitas" in email:
        return "Securitas"
    else:
        # Extract domain
        if "@" in email:
            domain = email.split("@")[1].split(".")[0]
            return domain.title()
        return "Unknown"


def analyze_records(records: list[dict[str, Any]], table_name: str) -> dict[str, Any]:
    """Analyze records and compute comprehensive metrics."""
    
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # Initialize counters
    stats = {
        "total_records": len(records),
        "by_status": defaultdict(int),
        "by_vendor": defaultdict(lambda: {"total": 0, "pass": 0, "fail": 0, "error": 0, "pending": 0}),
        "by_week": defaultdict(int),
        "by_day": defaultdict(int),
        "scores": [],
        "sites_submitted": set(),
        "recent_7_days": 0,
        "recent_30_days": 0,
        "emails_seen": set(),
    }
    
    for record in records:
        fields = record.get("fields", {})
        created_time = record.get("createdTime", "")
        
        # Get key fields (handle both tables)
        status = fields.get("Processing Status", "").upper() if fields.get("Processing Status") else "PENDING"
        email = fields.get("Surveyor Email", "") or fields.get("Email", "")
        site_number = fields.get("Site Number", "")
        score = fields.get("Score", "") or fields.get("Score Numeric", "")
        date_str = fields.get("Date of Survey", "") or created_time
        
        # Normalize status
        if not status or status in ("", "NEW", "PENDING"):
            status = "PENDING"
        elif status == "PASS":
            status = "PASS"
        elif status in ("FAIL", "FAILED"):
            status = "FAIL"
        elif "ERROR" in status:
            status = "ERROR"
        
        stats["by_status"][status] += 1
        
        # Vendor breakdown
        vendor = extract_vendor_from_email(email)
        stats["by_vendor"][vendor]["total"] += 1
        if status == "PASS":
            stats["by_vendor"][vendor]["pass"] += 1
        elif status == "FAIL":
            stats["by_vendor"][vendor]["fail"] += 1
        elif status == "ERROR":
            stats["by_vendor"][vendor]["error"] += 1
        else:
            stats["by_vendor"][vendor]["pending"] += 1
        
        # Track sites
        if site_number:
            stats["sites_submitted"].add(str(site_number))
        
        # Track emails
        if email:
            stats["emails_seen"].add(email.lower())
        
        # Parse score
        if score:
            try:
                score_val = float(str(score).replace("%", "").strip())
                stats["scores"].append(score_val)
            except (ValueError, TypeError):
                pass
        
        # Date analysis
        record_date = parse_date(date_str)
        if record_date:
            week_key = record_date.strftime("%Y-W%W")
            day_key = record_date.strftime("%Y-%m-%d")
            stats["by_week"][week_key] += 1
            stats["by_day"][day_key] += 1
            
            if record_date >= week_ago:
                stats["recent_7_days"] += 1
            if record_date >= month_ago:
                stats["recent_30_days"] += 1
    
    # Convert sets to counts
    stats["unique_sites"] = len(stats["sites_submitted"])
    stats["unique_surveyors"] = len(stats["emails_seen"])
    
    # Calculate derived metrics
    total = stats["total_records"]
    if total > 0:
        stats["pass_rate"] = round(stats["by_status"].get("PASS", 0) / total * 100, 1)
        stats["fail_rate"] = round(stats["by_status"].get("FAIL", 0) / total * 100, 1)
        stats["error_rate"] = round(stats["by_status"].get("ERROR", 0) / total * 100, 1)
        stats["pending_rate"] = round(stats["by_status"].get("PENDING", 0) / total * 100, 1)
    else:
        stats["pass_rate"] = stats["fail_rate"] = stats["error_rate"] = stats["pending_rate"] = 0
    
    # Score statistics
    if stats["scores"]:
        stats["avg_score"] = round(sum(stats["scores"]) / len(stats["scores"]), 1)
        stats["min_score"] = round(min(stats["scores"]), 1)
        stats["max_score"] = round(max(stats["scores"]), 1)
        stats["perfect_scores"] = sum(1 for s in stats["scores"] if s >= 100)
    else:
        stats["avg_score"] = stats["min_score"] = stats["max_score"] = 0
        stats["perfect_scores"] = 0
    
    # Weekly velocity (submissions per week)
    if stats["by_week"]:
        weekly_counts = list(stats["by_week"].values())
        stats["avg_weekly_submissions"] = round(sum(weekly_counts) / len(weekly_counts), 1)
        stats["peak_week"] = max(stats["by_week"].items(), key=lambda x: x[1])
    else:
        stats["avg_weekly_submissions"] = 0
        stats["peak_week"] = None
    
    # Clean up non-serializable data
    stats["by_status"] = dict(stats["by_status"])
    stats["by_vendor"] = {k: dict(v) for k, v in stats["by_vendor"].items()}
    stats["by_week"] = dict(stats["by_week"])
    stats["by_day"] = dict(stats["by_day"])
    del stats["sites_submitted"]
    del stats["emails_seen"]
    del stats["scores"]
    
    return stats


def main():
    """Main execution."""
    print("=" * 80)
    print("VUES COMPREHENSIVE METRICS REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    # Load configuration
    try:
        user_cfg = load_user_config()
    except Exception as e:
        print(f"[ERROR] Failed to load configuration: {e}")
        return 1
    
    # Extract configs
    survey_token = user_cfg.airtable_token
    survey_base_id = user_cfg.airtable_base_id
    survey_table_name = user_cfg.airtable_table_name
    
    scout_token = user_cfg.scout_airtable_token or user_cfg.airtable_token
    scout_base_id = user_cfg.scout_airtable_base_id
    scout_table_name = user_cfg.scout_airtable_table_name
    
    results = {}
    
    # ========================================================================
    # SURVEY TABLE
    # ========================================================================
    print("[SURVEY TABLE METRICS]")
    print("-" * 80)
    
    print("Fetching Survey records...")
    survey_records = fetch_all_records(survey_token, survey_base_id, survey_table_name)
    print(f"Retrieved {len(survey_records)} Survey records")
    print()
    
    survey_stats = analyze_records(survey_records, "Survey")
    results["survey"] = survey_stats
    
    print(f"  Total Submissions:     {survey_stats['total_records']}")
    print(f"  Unique Sites:          {survey_stats['unique_sites']}")
    print(f"  Unique Surveyors:      {survey_stats['unique_surveyors']}")
    print()
    print(f"  Status Breakdown:")
    print(f"    [PASS]:             {survey_stats['by_status'].get('PASS', 0):>5} ({survey_stats['pass_rate']}%)")
    print(f"    [FAIL]:             {survey_stats['by_status'].get('FAIL', 0):>5} ({survey_stats['fail_rate']}%)")
    print(f"    [ERROR]:            {survey_stats['by_status'].get('ERROR', 0):>5} ({survey_stats['error_rate']}%)")
    print(f"    [PENDING]:          {survey_stats['by_status'].get('PENDING', 0):>5} ({survey_stats['pending_rate']}%)")
    print()
    print(f"  Score Statistics:")
    print(f"    Average Score:       {survey_stats['avg_score']}%")
    print(f"    Min Score:           {survey_stats['min_score']}%")
    print(f"    Max Score:           {survey_stats['max_score']}%")
    print(f"    Perfect Scores (100): {survey_stats['perfect_scores']}")
    print()
    print(f"  Recent Activity:")
    print(f"    Last 7 Days:         {survey_stats['recent_7_days']}")
    print(f"    Last 30 Days:        {survey_stats['recent_30_days']}")
    print(f"    Avg Weekly:          {survey_stats['avg_weekly_submissions']}")
    print()
    
    print("  Top Vendors by Volume:")
    sorted_vendors = sorted(survey_stats["by_vendor"].items(), key=lambda x: x[1]["total"], reverse=True)[:5]
    for vendor, data in sorted_vendors:
        pass_pct = round(data["pass"] / data["total"] * 100, 1) if data["total"] > 0 else 0
        print(f"    {vendor:25s}: {data['total']:>4} submissions ({pass_pct}% pass)")
    print()
    
    # ========================================================================
    # SCOUT TABLE
    # ========================================================================
    if scout_base_id and scout_table_name:
        print()
        print("[SCOUT TABLE METRICS]")
        print("-" * 80)
        
        print("Fetching Scout records...")
        scout_records = fetch_all_records(scout_token, scout_base_id, scout_table_name)
        print(f"Retrieved {len(scout_records)} Scout records")
        print()
        
        scout_stats = analyze_records(scout_records, "Scout")
        results["scout"] = scout_stats
        
        print(f"  Total Submissions:     {scout_stats['total_records']}")
        print(f"  Unique Sites:          {scout_stats['unique_sites']}")
        print(f"  Unique Surveyors:      {scout_stats['unique_surveyors']}")
        print()
        print(f"  Status Breakdown:")
        print(f"    [PASS]:             {scout_stats['by_status'].get('PASS', 0):>5} ({scout_stats['pass_rate']}%)")
        print(f"    [FAIL]:             {scout_stats['by_status'].get('FAIL', 0):>5} ({scout_stats['fail_rate']}%)")
        print(f"    [ERROR]:            {scout_stats['by_status'].get('ERROR', 0):>5} ({scout_stats['error_rate']}%)")
        print(f"    [PENDING]:          {scout_stats['by_status'].get('PENDING', 0):>5} ({scout_stats['pending_rate']}%)")
        print()
        print(f"  Recent Activity:")
        print(f"    Last 7 Days:         {scout_stats['recent_7_days']}")
        print(f"    Last 30 Days:        {scout_stats['recent_30_days']}")
        print(f"    Avg Weekly:          {scout_stats['avg_weekly_submissions']}")
        print()
        
        print("  Top Vendors by Volume:")
        sorted_vendors = sorted(scout_stats["by_vendor"].items(), key=lambda x: x[1]["total"], reverse=True)[:5]
        for vendor, data in sorted_vendors:
            print(f"    {vendor:25s}: {data['total']:>4} submissions")
        print()
    
    # ========================================================================
    # COMBINED EXECUTIVE SUMMARY
    # ========================================================================
    print()
    print("=" * 80)
    print("[EXECUTIVE SUMMARY]")
    print("=" * 80)
    print()
    
    total_submissions = results["survey"]["total_records"] + results.get("scout", {}).get("total_records", 0)
    total_sites = results["survey"]["unique_sites"] + results.get("scout", {}).get("unique_sites", 0)
    
    print(f"  COMBINED TOTAL SUBMISSIONS:  {total_submissions}")
    print(f"    - Survey:                  {results['survey']['total_records']}")
    print(f"    - Scout:                   {results.get('scout', {}).get('total_records', 'N/A')}")
    print()
    print(f"  COMBINED UNIQUE SITES:       {total_sites}")
    print()
    
    # Overall pass rate
    survey_pass = results["survey"]["by_status"].get("PASS", 0)
    scout_pass = results.get("scout", {}).get("by_status", {}).get("PASS", 0)
    overall_pass_rate = round((survey_pass + scout_pass) / total_submissions * 100, 1) if total_submissions > 0 else 0
    print(f"  OVERALL PASS RATE:           {overall_pass_rate}%")
    print()
    
    # Save to JSON for dashboard consumption
    output_file = Path(__file__).parent.parent / "ui" / "vues_metrics_current.json"
    results["generated_at"] = datetime.now().isoformat()
    results["executive_summary"] = {
        "total_submissions": total_submissions,
        "survey_submissions": results["survey"]["total_records"],
        "scout_submissions": results.get("scout", {}).get("total_records", 0),
        "overall_pass_rate": overall_pass_rate,
        "unique_sites": total_sites,
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"Metrics saved to: {output_file}")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
