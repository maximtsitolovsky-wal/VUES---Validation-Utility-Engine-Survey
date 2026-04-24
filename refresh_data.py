import sys
sys.path.insert(0, 'src')
import json
from pathlib import Path

from siteowlqa.team_dashboard_data import generate_team_dashboard_data

# Generate fresh data
print("Generating team dashboard data...")
data = generate_team_dashboard_data()

# Write to JSON
output_path = Path('output/team_dashboard_data.json')
with open(output_path, 'w') as f:
    json.dump(data, f, indent=2)

print(f"Wrote to {output_path}")

# Verify
print("\n=== VENDOR ASSIGNMENTS ===")
for v in data.get('vendor_assignments', {}).get('vendors', []):
    print(f"{v['vendor_name']}: {v['completed']}/{v['total_assigned']}")
