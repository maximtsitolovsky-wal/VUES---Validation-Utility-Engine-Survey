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
from siteowlqa.local_dashboard_server import ensure_dashboard_server, get_dashboard_url

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

print("Starting / verifying dashboard server...")
ensure_dashboard_server(output_dir)
url = get_dashboard_url(output_dir)
print(f"Opening {url}")
webbrowser.open(url)
print("Done.")
