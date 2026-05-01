#!/usr/bin/env python3
"""Direct regeneration without import caching."""
import sys
import json
from pathlib import Path
from datetime import datetime
from dataclasses import asdict

# Read the source file directly
exec(open("src/siteowlqa/survey_routing.py").read().replace("from __future__ import annotations", ""))

# Now run the build
import os
token = os.environ.get("SCOUT_AIRTABLE_API_KEY", os.environ.get("AIRTABLE_API_KEY", ""))
workbook = r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Documents\BaselinePrinter\2027 Survey Lab.xlsm"

print("Fetching data...")
data = build_survey_routing_data(token, workbook)

# Write output
output_dir = Path("output")
output_dir.mkdir(exist_ok=True)
with open(output_dir / "survey_routing_data.json", "w") as f:
    json.dump(data, f, indent=2)

# Print summary
summary = data.get("summary", {})
print("\n" + "=" * 50)
print(" ROUTING DATA SUMMARY (Direct)")
print("=" * 50)
print(f"  Total sites:      {summary.get('total_sites', 0)}")
print(f"  Surveys required: {summary.get('surveys_required', 0)}")
print(f"  Pending scout:    {summary.get('pending_scout', 0)}")
print(f"  No vendor:        {summary.get('no_vendor', 0)}")
print(f"  Not on tracking:  {summary.get('not_on_tracking', 0)}")
print("=" * 50)

# Verify no_vendor count directly
rows = data.get("rows", [])
actual_no_vendor = sum(1 for r in rows if not r.get("vendor") and r.get("survey_required") == "YES")
print(f"\nDirect count (no vendor + needs survey): {actual_no_vendor}")
