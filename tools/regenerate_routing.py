#!/usr/bin/env python3
"""Regenerate survey routing data with current logic."""
import sys
import json
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from siteowlqa.survey_routing import refresh_survey_routing, DEFAULT_WORKBOOK_PATH
from siteowlqa.config import load_config

def main():
    print("=" * 50)
    print(" Regenerating Survey Routing Data")
    print("=" * 50)
    
    config = load_config()
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Use the Survey Lab workbook for routing (has MAP DATA + Project Tracking)
    workbook_path = DEFAULT_WORKBOOK_PATH
    
    print(f"Workbook: {workbook_path}")
    print(f"API key present: {bool(config.airtable_token)}")
    
    print("\nFetching data from Airtable and Excel...")
    
    # Use refresh_survey_routing which now also syncs to Airtable
    refresh_survey_routing(
        token=config.scout_airtable_token or config.airtable_token,
        output_dir=output_dir,
        workbook_path=workbook_path,
        sync_to_airtable=True
    )
    
    # Load the generated data for summary display
    output_file = output_dir / 'survey_routing_data.json'
    with open(output_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"\nWrote {output_file}")
    
    summary = data.get('summary', {})
    print("\n" + "=" * 50)
    print(" ROUTING DATA SUMMARY")
    print("=" * 50)
    print(f"  Total sites:      {summary.get('total_sites', 0)}")
    print(f"  Surveys required: {summary.get('surveys_required', 0)}")
    print(f"  - CCTV:           {summary.get('cctv_surveys', 0)}")
    print(f"  - FA/Intrusion:   {summary.get('fa_surveys', 0)}")
    print(f"  - Both:           {summary.get('both_surveys', 0)}")
    print(f"  Full upgrades:    {summary.get('full_upgrades', 0)}")
    print(f"  Review required:  {summary.get('review_required', 0)}")
    print(f"  Surveys complete: {summary.get('surveys_complete', 0)}")
    print(f"  Pending scout:    {summary.get('pending_scout', 0)}")
    print(f"  No vendor:        {summary.get('no_vendor', 0)}")
    print(f"  Not on tracking:  {summary.get('not_on_tracking', 0)}")
    print("=" * 50)
    
    # Vendor breakdown
    vb = summary.get('vendor_breakdown', {})
    if vb:
        print("\n  VENDOR BREAKDOWN:")
        for vendor, counts in sorted(vb.items(), key=lambda x: x[1].get('total', 0), reverse=True):
            t = counts.get('total', 0)
            s = counts.get('survey_required', 0)
            c = counts.get('complete', 0)
            print(f"    {vendor:12} | Total: {t:3} | Surveys: {s:3} | Complete: {c:3}")
        print("=" * 50)
    
    # Count REVIEW types in rows
    rows = data.get('rows', [])
    review_count = sum(1 for r in rows if r.get('survey_type') == 'REVIEW')
    print(f"\n  Rows with survey_type=REVIEW: {review_count}")
    
    print("\nDone! Now run: uv run python tools/bake_data_into_html.py")

if __name__ == "__main__":
    main()
