"""Test the per-row conditional Name grading logic."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from siteowlqa.config import (
    get_name_condition_column,
    get_base_grade_columns,
    SURVEY_TYPE_CCTV,
    SURVEY_TYPE_FA_INTRUSION,
)
from siteowlqa.site_validation import (
    _get_critical_columns_for_survey_type,
    _get_optional_columns_for_survey_type,
)


def main():
    print("=" * 60)
    print("PER-ROW CONDITIONAL NAME GRADING LOGIC")
    print("=" * 60)
    
    print("\n--- Grading Logic (config.py) ---")
    for st in [SURVEY_TYPE_CCTV, SURVEY_TYPE_FA_INTRUSION, "BOTH", None]:
        condition_col = get_name_condition_column(st)
        base_cols = get_base_grade_columns(st)
        print(f"\n{st!r}:")
        print(f"  Base columns (always checked): {base_cols}")
        print(f"  Name condition column: {condition_col}")
        if condition_col:
            print(f"  --> Name checked per-row IF {condition_col} has content")
        else:
            print(f"  --> Name always checked")
    
    print("\n\n--- Validation Logic (site_validation.py) ---")
    for st in [SURVEY_TYPE_CCTV, SURVEY_TYPE_FA_INTRUSION, "BOTH", None]:
        critical = _get_critical_columns_for_survey_type(st)
        optional = _get_optional_columns_for_survey_type(st)
        print(f"\n{st!r}:")
        print(f"  Critical (must exist in file): {critical}")
        print(f"  Optional (may be missing): {optional}")
    
    print("\n\n--- Verification ---")
    
    # CCTV: Name should NOT be in critical columns
    cctv_critical = _get_critical_columns_for_survey_type(SURVEY_TYPE_CCTV)
    if "Name" in cctv_critical:
        print("[FAIL] CCTV: Name should not be critical (it's per-row conditional)")
    else:
        print("[PASS] CCTV: Name is not in critical columns")
    
    # CCTV: Name condition should be MAC Address
    cctv_condition = get_name_condition_column(SURVEY_TYPE_CCTV)
    if cctv_condition == "MAC Address":
        print("[PASS] CCTV: Name is conditional on MAC Address")
    else:
        print(f"[FAIL] CCTV: Expected 'MAC Address', got {cctv_condition!r}")
    
    # FA/Intrusion: Name should NOT be in critical columns
    fa_critical = _get_critical_columns_for_survey_type(SURVEY_TYPE_FA_INTRUSION)
    if "Name" in fa_critical:
        print("[FAIL] FA/Intrusion: Name should not be critical (it's per-row conditional)")
    else:
        print("[PASS] FA/Intrusion: Name is not in critical columns")
    
    # FA/Intrusion: Name condition should be Abbreviated Name
    fa_condition = get_name_condition_column(SURVEY_TYPE_FA_INTRUSION)
    if fa_condition == "Abbreviated Name":
        print("[PASS] FA/Intrusion: Name is conditional on Abbreviated Name")
    else:
        print(f"[FAIL] FA/Intrusion: Expected 'Abbreviated Name', got {fa_condition!r}")
    
    # BOTH: Name should always be checked (no condition)
    both_condition = get_name_condition_column("BOTH")
    if both_condition is None:
        print("[PASS] BOTH: Name is always checked (no condition)")
    else:
        print(f"[FAIL] BOTH: Expected None, got {both_condition!r}")
    
    print()


if __name__ == "__main__":
    main()
