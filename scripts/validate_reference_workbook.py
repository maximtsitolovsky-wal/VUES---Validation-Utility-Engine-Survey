from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from siteowlqa.config import load_config
from siteowlqa.reference_data import _load_reference_workbook


def main() -> None:
    cfg = load_config()
    workbook_path = cfg.reference_workbook_path
    if workbook_path is None:
        raise SystemExit("No reference workbook configured.")

    path = Path(workbook_path)
    if not path.exists():
        raise SystemExit(f"Reference workbook not found: {path}")

    grouped = _load_reference_workbook(
        str(path),
        cfg.reference_workbook_sheet,
        cfg.reference_workbook_site_id_column,
    )
    total_rows = sum(len(df) for df in grouped.values())

    print(f"WORKBOOK={path}")
    print(f"SHEET={cfg.reference_workbook_sheet or '<first>'}")
    print(f"SITE_ID_COLUMN={cfg.reference_workbook_site_id_column}")
    print(f"SITE_GROUPS={len(grouped)}")
    print(f"TOTAL_ROWS={total_rows}")
    print("SAMPLE_SITE_KEYS=" + ", ".join(list(grouped.keys())[:10]))


if __name__ == "__main__":
    main()
