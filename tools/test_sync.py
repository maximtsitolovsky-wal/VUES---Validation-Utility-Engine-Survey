#!/usr/bin/env python3
"""Test the Survey Routing sync."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

print("Starting test...")

from siteowlqa.config import load_config
from siteowlqa.survey_routing import refresh_survey_routing, DEFAULT_WORKBOOK_PATH

config = load_config()
token = config.scout_airtable_token or config.airtable_token

print(f"Token exists: {bool(token)}")
print(f"Workbook: {DEFAULT_WORKBOOK_PATH}")
print()

print("Calling refresh_survey_routing with sync_to_airtable=True...")
try:
    refresh_survey_routing(
        token=token,
        output_dir=Path("ui"),
        workbook_path=DEFAULT_WORKBOOK_PATH,
        sync_to_airtable=True
    )
    print("SUCCESS!")
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
