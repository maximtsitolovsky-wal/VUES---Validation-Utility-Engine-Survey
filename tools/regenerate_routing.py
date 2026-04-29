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

from src.siteowlqa.survey_routing import refresh_survey_routing
from src.siteowlqa.config import Config

def main():
    print("=" * 50)
    print(" Regenerating Survey Routing Data")
    print("=" * 50)
    
    config = Config()
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    print(f"Workbook: {config.workbook_path}")
    print(f"API key present: {bool(config.airtable_api_key)}")
    
    print("\nFetching data from Airtable and Excel...")
    refresh_survey_routing(config.airtable_api_key, output_dir, config.workbook_path)
    
    # Read and display summary
    with open(output_dir / 'survey_routing_data.json') as f:
        data = json.load(f)
    
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
    print("=" * 50)
    
    # Count REVIEW types in rows
    rows = data.get('rows', [])
    review_count = sum(1 for r in rows if r.get('survey_type') == 'REVIEW')
    print(f"\n  Rows with survey_type=REVIEW: {review_count}")
    
    print("\nDone! Now run: uv run python tools/bake_data_into_html.py")

if __name__ == "__main__":
    main()
