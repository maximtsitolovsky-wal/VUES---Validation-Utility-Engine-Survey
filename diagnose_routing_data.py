"""Diagnostic script to compare routing data files and identify issues."""
import json
from pathlib import Path
from collections import Counter

REPO_ROOT = Path(__file__).parent
UI_FILE = REPO_ROOT / "ui" / "survey_routing_data.json"
OUTPUT_FILE = REPO_ROOT / "output" / "survey_routing_data.json"

def analyze_file(file_path):
    """Analyze a routing data JSON file."""
    print(f"\n{'='*80}")
    print(f"ANALYZING: {file_path.name}")
    print(f"Path: {file_path}")
    print(f"{'='*80}")
    
    if not file_path.exists():
        print(f"  [ERROR] File does not exist!")
        return None
    
    data = json.loads(file_path.read_text(encoding='utf-8'))
    
    # Summary
    print(f"\nGenerated at: {data.get('generated_at', 'UNKNOWN')}")
    print(f"\nSUMMARY:")
    summary = data.get('summary', {})
    for key, val in summary.items():
        if isinstance(val, dict):
            print(f"  {key}:")
            for k, v in val.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {val}")
    
    # Row analysis
    rows = data.get('rows', [])
    print(f"\nROW ANALYSIS:")
    print(f"  Total rows: {len(rows)}")
    
    # Count survey_required values
    survey_req_counts = Counter(r.get('survey_required', 'MISSING') for r in rows)
    print(f"\n  survey_required breakdown:")
    for val, count in sorted(survey_req_counts.items()):
        print(f"    {val}: {count}")
    
    # Count ready_to_assign values
    ready_counts = Counter(r.get('ready_to_assign', 'MISSING') for r in rows)
    print(f"\n  ready_to_assign breakdown:")
    for val, count in sorted(ready_counts.items()):
        print(f"    {val}: {count}")
    
    # Count scout_submitted values
    scout_counts = Counter(str(r.get('scout_submitted', 'MISSING')) for r in rows)
    print(f"\n  scout_submitted breakdown:")
    for val, count in sorted(scout_counts.items()):
        print(f"    {val}: {count}")
    
    # Sample PENDING sites
    pending_sites = [r for r in rows if r.get('survey_required') == 'PENDING']
    if pending_sites:
        print(f"\n  Sample PENDING site (first of {len(pending_sites)}):")
        sample = pending_sites[0]
        print(f"    Site: {sample.get('site')}")
        print(f"    Vendor: {sample.get('vendor')}")
        print(f"    survey_required: {sample.get('survey_required')}")
        print(f"    survey_type: {sample.get('survey_type')}")
        print(f"    ready_to_assign: {sample.get('ready_to_assign')}")
        print(f"    scout_submitted: {sample.get('scout_submitted')}")
        print(f"    upgrade_decision: {sample.get('upgrade_decision')}")
    else:
        print(f"\n  [INFO] No PENDING sites found in this file")
    
    # Sample REVIEW sites
    review_sites = [r for r in rows if r.get('survey_required') == 'REVIEW']
    if review_sites:
        print(f"\n  Sample REVIEW site (first of {len(review_sites)}):")
        sample = review_sites[0]
        print(f"    Site: {sample.get('site')}")
        print(f"    Vendor: {sample.get('vendor')}")
        print(f"    survey_required: {sample.get('survey_required')}")
        print(f"    survey_type: {sample.get('survey_type')}")
        print(f"    ready_to_assign: {sample.get('ready_to_assign')}")
        print(f"    scout_submitted: {sample.get('scout_submitted')}")
        print(f"    upgrade_decision: {sample.get('upgrade_decision')}")
    else:
        print(f"\n  [INFO] No REVIEW sites found in this file")
    
    # Check for field differences
    if rows:
        sample_row = rows[0]
        print(f"\n  Fields in first row ({len(sample_row)} fields):")
        for key in sorted(sample_row.keys()):
            print(f"    - {key}")
    
    return data

def main():
    print("\n" + "="*80)
    print("VUES ROUTING DATA DIAGNOSTIC")
    print("="*80)
    
    ui_data = analyze_file(UI_FILE)
    output_data = analyze_file(OUTPUT_FILE)
    
    # Compare files
    print(f"\n{'='*80}")
    print("COMPARISON:")
    print(f"{'='*80}")
    
    if ui_data and output_data:
        ui_rows = ui_data.get('rows', [])
        output_rows = output_data.get('rows', [])
        
        print(f"\nRow count comparison:")
        print(f"  ui/: {len(ui_rows)}")
        print(f"  output/: {len(output_rows)}")
        
        # Field comparison
        if ui_rows and output_rows:
            ui_fields = set(ui_rows[0].keys())
            output_fields = set(output_rows[0].keys())
            
            print(f"\nField comparison:")
            print(f"  ui/ has {len(ui_fields)} fields")
            print(f"  output/ has {len(output_fields)} fields")
            
            only_ui = ui_fields - output_fields
            if only_ui:
                print(f"\n  Fields ONLY in ui/:")
                for f in sorted(only_ui):
                    print(f"    - {f}")
            
            only_output = output_fields - ui_fields
            if only_output:
                print(f"\n  Fields ONLY in output/:")
                for f in sorted(only_output):
                    print(f"    - {f}")
        
        # Summary comparison
        ui_summary = ui_data.get('summary', {})
        output_summary = output_data.get('summary', {})
        
        print(f"\n  Key summary differences:")
        keys_to_compare = ['total_sites', 'ready_to_assign', 'review_required', 'pending_scout']
        for key in keys_to_compare:
            ui_val = ui_summary.get(key, 'MISSING')
            output_val = output_summary.get(key, 'MISSING')
            if ui_val != output_val:
                print(f"    {key}: ui={ui_val}, output={output_val}")
    
    print(f"\n{'='*80}")
    print("DIAGNOSIS COMPLETE")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
