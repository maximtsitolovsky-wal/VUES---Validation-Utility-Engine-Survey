"""Check attachment fields for a record."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from siteowlqa.config import load_config, ATAIRTABLE_FIELDS as FIELDS
from siteowlqa.airtable_client import AirtableClient


def main():
    record_id = sys.argv[1] if len(sys.argv) > 1 else "recryYpfpuVlYKm1g"
    
    cfg = load_config()
    client = AirtableClient(cfg)
    fields = client.get_record_fields(record_id)
    
    print(f"Record: {record_id}")
    print(f"Attachment field name in config: '{FIELDS.attachment}'")
    print()
    
    # Check the configured attachment field
    att_value = fields.get(FIELDS.attachment)
    print(f"Value of '{FIELDS.attachment}': {att_value}")
    print()
    
    # Show all fields that are lists (potential attachments)
    print("All list-type fields:")
    for k, v in fields.items():
        if isinstance(v, list):
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
