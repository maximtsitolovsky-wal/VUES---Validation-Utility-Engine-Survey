import json
from collections import Counter

d = json.load(open('ui/team_dashboard_data.json'))
records = d.get('scout', {}).get('records', [])

# Find duplicates (by site_number)
sites = {}
for r in records:
    site = r.get('site_number', 'UNKNOWN')
    if site not in sites:
        sites[site] = []
    sites[site].append(r)

duplicates = {s: recs for s, recs in sites.items() if len(recs) > 1}

with open('scout_detailed_analysis.txt', 'w') as f:
    f.write("=" * 70 + "\n")
    f.write(" SCOUT COMPLETION ANALYSIS\n")
    f.write("=" * 70 + "\n\n")
    
    f.write(f"Total Airtable records: {len(records)}\n")
    f.write(f"Unique site numbers: {len(sites)}\n")
    f.write(f"Sites with duplicates: {len(duplicates)}\n")
    f.write(f"Extra records (duplicates): {sum(len(r)-1 for r in duplicates.values())}\n\n")
    
    # Find incomplete submissions
    # Check what fields indicate completion
    f.write("-" * 70 + "\n")
    f.write(" CHECKING FOR INCOMPLETE SUBMISSIONS\n")
    f.write("-" * 70 + "\n\n")
    
    # Check raw_fields for Complete? field
    incomplete = []
    complete_count = 0
    for r in records:
        raw = r.get('raw_fields', {})
        # Try different field names
        is_complete = raw.get('Complete?') or raw.get('Complete') or raw.get('completed')
        if is_complete:
            complete_count += 1
        else:
            incomplete.append(r)
    
    f.write(f"Records with Complete? = True: {complete_count}\n")
    f.write(f"Records without Complete? = True: {len(incomplete)}\n\n")
    
    if incomplete:
        f.write("INCOMPLETE RECORDS:\n")
        for r in incomplete[:20]:  # Show first 20
            site = r.get('site_number', '?')
            vendor = r.get('vendor_name', '?')[:25]
            rec_id = r.get('record_id', '?')[:15]
            submitted = r.get('submitted_at', '?')
            raw = r.get('raw_fields', {})
            complete_val = raw.get('Complete?', raw.get('Complete', 'NOT FOUND'))
            f.write(f"  Site {site} | {vendor} | {submitted} | Complete?={complete_val}\n")
    
    f.write("\n" + "-" * 70 + "\n")
    f.write(" DUPLICATE SITES (multiple submissions)\n")
    f.write("-" * 70 + "\n\n")
    
    if duplicates:
        for site, recs in sorted(duplicates.items()):
            f.write(f"Site {site}: {len(recs)} submissions\n")
            for r in recs:
                vendor = r.get('vendor_name', '?')[:20]
                submitted = r.get('submitted_at', '?')
                rec_id = r.get('record_id', '?')[:12]
                raw = r.get('raw_fields', {})
                complete = raw.get('Complete?', '?')
                f.write(f"    {submitted} | {vendor} | {rec_id} | Complete?={complete}\n")
            f.write("\n")
