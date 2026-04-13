"""One-shot: refresh team_dashboard_data.json + rebuild dashboard HTML now."""
import json
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from siteowlqa.config import load_config
from siteowlqa.airtable_client import AirtableClient
from siteowlqa.team_dashboard_data import refresh_team_dashboard_data
from siteowlqa.dashboard import refresh_dashboards

print("=== Force Refresh ===")
cfg = load_config()
airtable = AirtableClient(cfg)
output_dir = Path(cfg.output_dir)

print("Pulling Scout + Survey records from Airtable...")
refresh_team_dashboard_data(airtable=airtable, cfg=cfg, output_dir=output_dir)

data = json.loads((output_dir / "team_dashboard_data.json").read_text(encoding="utf-8"))
survey = data.get("survey", {})
scout  = data.get("scout",  {})

print(f"  Survey : {len(survey.get('records', []))} records  configured={survey.get('configured')}")
print(f"  Scout  : {len(scout.get('records',  []))} records  configured={scout.get('configured')}")

if scout.get("error"):
    print(f"  Scout error: {scout['error']}")

print("Rebuilding executive dashboard HTML...")
refresh_dashboards(output_dir)

url = "http://127.0.0.1:8765/executive_dashboard.html"
print(f"Opening {url}")
webbrowser.open(url)
print("Done.")
