#!/usr/bin/env python3
"""Test the Survey Routing sync with verbose output."""
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Enable logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

print("=" * 60)
print("  TESTING SURVEY ROUTING SYNC")
print("=" * 60)

from siteowlqa.config import load_config
from siteowlqa.survey_routing import (
    refresh_survey_routing, 
    sync_routing_to_airtable,
    build_survey_routing_data,
    DEFAULT_WORKBOOK_PATH
)

config = load_config()
token = config.scout_airtable_token or config.airtable_token

print(f"\nToken exists: {bool(token)}")
print(f"Workbook: {DEFAULT_WORKBOOK_PATH}")

# Test sync directly first
print("\n" + "=" * 60)
print("  STEP 1: Build routing data")
print("=" * 60)

data = build_survey_routing_data(token, DEFAULT_WORKBOOK_PATH)
print(f"Built {len(data['rows'])} rows")

print("\n" + "=" * 60)
print("  STEP 2: Call sync_routing_to_airtable directly")
print("=" * 60)

updated, errors = sync_routing_to_airtable(token, data['rows'])
print(f"Result: {updated} updated, {errors} errors")

print("\n" + "=" * 60)
print("  DONE!")
print("=" * 60)
