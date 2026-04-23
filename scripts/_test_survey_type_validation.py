"""Test the survey type column routing in site_validation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from siteowlqa.site_validation import (
    _get_critical_columns_for_survey_type,
    _get_optional_columns_for_survey_type,
)

def main():
    print("=== Critical Columns by Survey Type ===")
    for st in ["CCTV", "FA/Intrusion", "BOTH", None]:
        cols = _get_critical_columns_for_survey_type(st)
        print(f"  {st!r}: {cols}")

    print()
    print("=== Optional Columns by Survey Type ===")
    for st in ["CCTV", "FA/Intrusion", "BOTH", None]:
        cols = _get_optional_columns_for_survey_type(st)
        print(f"  {st!r}: {cols}")

    print()
    print("=== Verification ===")
    
    # FA/Intrusion should NOT require Part Number, Manufacturer, etc.
    fa_critical = _get_critical_columns_for_survey_type("FA/Intrusion")
    cctv_cols = {"Part Number", "Manufacturer", "IP Address", "MAC Address", "IP / Analog"}
    
    bad_cols_in_fa = [c for c in cctv_cols if c in fa_critical]
    if bad_cols_in_fa:
        print(f"[FAIL] FA/Intrusion critical columns incorrectly include: {bad_cols_in_fa}")
    else:
        print("[PASS] FA/Intrusion does NOT require CCTV columns")
    
    # FA/Intrusion SHOULD require Abbreviated Name and Description
    fa_required = {"Abbreviated Name", "Description"}
    missing = [c for c in fa_required if c not in fa_critical]
    if missing:
        print(f"[FAIL] FA/Intrusion missing required columns: {missing}")
    else:
        print("[PASS] FA/Intrusion requires Abbreviated Name and Description")


if __name__ == "__main__":
    main()
