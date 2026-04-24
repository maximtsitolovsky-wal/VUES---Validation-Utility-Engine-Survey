"""List recent FA/Intrusion submissions."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from siteowlqa.config import load_config
from siteowlqa.airtable_client import AirtableClient


def main():
    cfg = load_config()
    client = AirtableClient(cfg)
    
    records = client.list_all_raw_records()
    print(f"Total records: {len(records)}")
    print()
    
    fa_records = []
    for r in records:
        f = r.get("fields", {})
        st = f.get("Survey Type", "")
        if st == "FA/Intrusion":
            fa_records.append({
                "id": r["id"],
                "site": f.get("Site Number"),
                "status": f.get("Processing Status"),
                "score": f.get("Score"),
            })
    
    print(f"FA/Intrusion submissions: {len(fa_records)}")
    print()
    for rec in fa_records:
        print(f"  {rec['id']}: Site={rec['site']} Status={rec['status']} Score={rec['score']}")


if __name__ == "__main__":
    main()
