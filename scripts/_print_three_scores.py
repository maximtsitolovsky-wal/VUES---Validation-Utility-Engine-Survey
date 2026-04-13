from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from siteowlqa.config import ATAIRTABLE_FIELDS as FIELDS, load_config
from siteowlqa.airtable_client import AirtableClient

IDS = [
    'recog54eAeF7hXtzE',
    'recparZPbgryMpINi',
    'rec68SeJ68akJRrUX',
]


def main() -> int:
    client = AirtableClient(load_config())
    for rid in IDS:
        f = client.get_record_fields(rid)
        print(
            rid,
            '| status=', f.get(FIELDS.status),
            '| score=', f.get(FIELDS.score),
            '| true=', f.get(FIELDS.true_score),
            '| summary=', str(f.get(FIELDS.fail_summary, ''))[:160],
        )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
