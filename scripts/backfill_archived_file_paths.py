"""Backfill archived_file_path in historical submission metadata.

Strategy:
- For each *_meta.json, look in the same folder for a sibling file whose name
  starts with '<submission_id>_' and is not the meta file itself.
- Only update when there is exactly one unambiguous match.
- Skip rows that already have archived_file_path.

Usage:
    python backfill_archived_file_paths.py
"""

from __future__ import annotations

import json
from pathlib import Path

ARCHIVE_ROOT = Path("archive/submissions")


def main() -> None:
    updated = 0
    skipped = 0
    ambiguous = 0

    for meta_path in sorted(ARCHIVE_ROOT.rglob("*_meta.json")):
        with open(meta_path, encoding="utf-8") as fh:
            data = json.load(fh)

        current = str(data.get("archived_file_path") or "").strip()
        if current:
            skipped += 1
            continue

        submission_id = str(data.get("submission_id") or "").strip()
        if not submission_id:
            skipped += 1
            continue

        matches = [
            p for p in meta_path.parent.iterdir()
            if p.is_file()
            and p.name != meta_path.name
            and p.name.startswith(f"{submission_id}_")
        ]

        if len(matches) != 1:
            ambiguous += 1
            print(f"SKIP {meta_path.name}: expected 1 sibling raw file, found {len(matches)}")
            continue

        data["archived_file_path"] = str(matches[0])
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        updated += 1
        print(f"UPDATED {meta_path.name} -> {matches[0]}")

    print()
    print("=== Backfill complete ===")
    print(f"Updated : {updated}")
    print(f"Skipped : {skipped}")
    print(f"Ambiguous/none : {ambiguous}")


if __name__ == "__main__":
    main()
