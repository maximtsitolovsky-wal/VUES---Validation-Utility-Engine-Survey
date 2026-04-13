"""One-shot: reset a single Airtable record so the pipeline reprocesses it.

Usage:
    python scripts/_reprocess_record.py <record_id>

Resets Processing Status to NEW and clears stale score/result fields.
The running pipeline picks it up on the next poll cycle.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from siteowlqa.config import load_config, ATAIRTABLE_FIELDS as FIELDS
from siteowlqa.airtable_client import AirtableClient, _api_request


def reset_record(record_id: str) -> None:
    cfg = load_config()
    client = AirtableClient(cfg)

    # Show current state before touching anything
    fields = client.get_record_fields(record_id)
    print(f"BEFORE reset ({record_id}):")
    print(f"  Processing Status : {fields.get(FIELDS.status, '<empty>')}")
    print(f"  Score             : {fields.get(FIELDS.score, '<empty>')}")
    print(f"  True Score        : {fields.get(FIELDS.true_score, '<empty>')}")
    print(f"  Fail Summary      : {str(fields.get(FIELDS.fail_summary, '<empty>'))[:80]}")

    # PATCH: reset status to NEW + clear stale score/result fields in one call
    url = f"{client._base_url}/{record_id}"
    payload = {
        "fields": {
            FIELDS.status:         "NEW",
            FIELDS.score:          "",
            FIELDS.true_score:     None,  # numeric — null it out
            FIELDS.fail_summary:   "",
            FIELDS.notes_internal: "",
        }
    }
    _api_request("PATCH", url, client._headers, json=payload, timeout=30)
    print(f"\nPATCHED — status reset to NEW, stale scores cleared.")

    # Confirm
    after = client.get_record_fields(record_id)
    print(f"\nAFTER reset ({record_id}):")
    print(f"  Processing Status : {after.get(FIELDS.status, '<empty>')}")
    print(f"  Score             : {after.get(FIELDS.score, '<empty>')}")
    print(f"  True Score        : {after.get(FIELDS.true_score, '<empty>')}")
    print(f"\nDone. Pipeline will pick up {record_id} on the next poll cycle.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/_reprocess_record.py <record_id>")
        sys.exit(1)
    reset_record(sys.argv[1])
