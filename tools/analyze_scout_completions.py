#!/usr/bin/env python3
"""Analyze scout submissions to find why some aren't counted as complete."""
import json
from pathlib import Path
from collections import Counter

def main():
    # Load scout data
    with open(Path("ui/team_dashboard_data.json")) as f:
        data = json.load(f)
    
    scout = data.get("scout", {})
    records = scout.get("records", [])
    
    print("=" * 60)
    print(" SCOUT SUBMISSION ANALYSIS")
    print("=" * 60)
    print(f"\nTotal scout records in Airtable: {len(records)}")
    
    # Group by site
    sites = {}
    for r in records:
        site = r.get("site_number", "UNKNOWN")
        if site not in sites:
            sites[site] = []
        sites[site].append(r)
    
    unique_sites = len(sites)
    duplicates = {s: recs for s, recs in sites.items() if len(recs) > 1}
    extra_submissions = sum(len(recs) - 1 for recs in duplicates.values())
    
    print(f"Unique site numbers: {unique_sites}")
    print(f"Sites with multiple submissions: {len(duplicates)}")
    print(f"Extra submissions (duplicates): {extra_submissions}")
    
    if duplicates:
        print("\n" + "-" * 60)
        print(" DUPLICATE SITES (multiple submissions for same site)")
        print("-" * 60)
        for site, recs in sorted(duplicates.items(), key=lambda x: -len(x[1])):
            print(f"\n  Site {site}: {len(recs)} submissions")
            for r in recs:
                vendor = r.get("vendor_name", "?")[:20]
                status = r.get("processing_status", "?")
                date = r.get("submitted_at", "?")
                rec_id = r.get("record_id", "?")[:12]
                print(f"    [{status:6}] {date} | {vendor} | {rec_id}")
    
    # Processing status breakdown
    print("\n" + "-" * 60)
    print(" PROCESSING STATUS BREAKDOWN")
    print("-" * 60)
    statuses = Counter(r.get("processing_status", "UNKNOWN") for r in records)
    for status, count in statuses.most_common():
        print(f"  {status}: {count}")
    
    # Check for blank/invalid site numbers
    blank_sites = [r for r in records if not r.get("site_number") or r.get("site_number") == "UNKNOWN"]
    if blank_sites:
        print("\n" + "-" * 60)
        print(f" RECORDS WITH BLANK/INVALID SITE NUMBER: {len(blank_sites)}")
        print("-" * 60)
        for r in blank_sites[:10]:
            print(f"  ID={r.get('record_id', '?')[:15]} vendor={r.get('vendor_name', '?')}")
    
    # Summary
    print("\n" + "=" * 60)
    print(" SUMMARY")
    print("=" * 60)
    print(f"  Total records:      {len(records)}")
    print(f"  Unique sites:       {unique_sites}")
    print(f"  Duplicate entries:  {extra_submissions}")
    print(f"  ---------------------------")
    print(f"  Net unique sites:   {unique_sites}")
    print(f"  Difference:         {len(records) - unique_sites} (these are duplicates)")

if __name__ == "__main__":
    main()
