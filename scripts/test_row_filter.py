"""Test row filtering by survey type."""
import sys
sys.path.insert(0, 'src')
import pandas as pd
from siteowlqa.python_grader import _filter_rows_by_survey_type, _normalize_for_compare
from siteowlqa.config import SURVEY_TYPE_CCTV, SURVEY_TYPE_FA_INTRUSION, SURVEY_TYPE_BOTH, VENDOR_GRADE_COLUMNS

# Create mixed data - some CCTV rows, some FA/Intrusion rows
mixed_df = pd.DataFrame({
    'Name': ['CAM-001', 'CAM-002', 'PANEL-01', 'PANEL-02', 'CAM-003'],
    'Abbreviated Name': ['', '', 'P1', 'P2', ''],  # Empty = CCTV, Content = FA
    'Part Number': ['PN001', 'PN002', 'PN003', 'PN004', 'PN005'],
    'Manufacturer': ['Axis', 'Hikvision', 'Honeywell', 'Bosch', 'Dahua'],
    'IP Address': ['10.0.0.1', '10.0.0.2', '10.0.0.3', '10.0.0.4', '10.0.0.5'],
    'MAC Address': ['AA:BB:01', 'AA:BB:02', 'AA:BB:03', 'AA:BB:04', 'AA:BB:05'],
    'IP / Analog': ['IP', 'IP', 'IP', 'IP', 'IP'],
    'Description': ['', '', 'Main panel', 'Sub panel', ''],  # Empty = CCTV, Content = FA
})

print("=" * 60)
print("ROW FILTERING TEST")
print("=" * 60)
print()
print("Original data (5 rows):")
print("  - CAM-001, CAM-002, CAM-003: CCTV (no Abbreviated, no Description)")
print("  - PANEL-01, PANEL-02: FA/Intrusion (have Abbreviated and Description)")
print()

# Normalize first
norm_df = _normalize_for_compare(mixed_df, '9999', VENDOR_GRADE_COLUMNS, None)

# Test CCTV filtering
cctv_filtered = _filter_rows_by_survey_type(norm_df, SURVEY_TYPE_CCTV)
print(f"CCTV filter: {len(norm_df)} -> {len(cctv_filtered)} rows")
print(f"  Names: {list(cctv_filtered['Name'])}")
print(f"  Expected: 3 rows (CAM-001, CAM-002, CAM-003)")
print()

# Test FA/Intrusion filtering
fa_filtered = _filter_rows_by_survey_type(norm_df, SURVEY_TYPE_FA_INTRUSION)
print(f"FA/Intrusion filter: {len(norm_df)} -> {len(fa_filtered)} rows")
print(f"  Names: {list(fa_filtered['Name'])}")
print(f"  Expected: 2 rows (PANEL-01, PANEL-02)")
print()

# Test BOTH - no filtering
both_filtered = _filter_rows_by_survey_type(norm_df, SURVEY_TYPE_BOTH)
print(f"BOTH filter: {len(norm_df)} -> {len(both_filtered)} rows")
print(f"  Expected: 5 rows (all)")
print()

print("=" * 60)
cctv_ok = len(cctv_filtered) == 3
fa_ok = len(fa_filtered) == 2
both_ok = len(both_filtered) == 5

if cctv_ok and fa_ok and both_ok:
    print("[PASS] ROW FILTERING WORKS!")
else:
    print("[FAIL] Row filtering has issues")
    if not cctv_ok: print(f"  CCTV: expected 3, got {len(cctv_filtered)}")
    if not fa_ok: print(f"  FA: expected 2, got {len(fa_filtered)}")
    if not both_ok: print(f"  BOTH: expected 5, got {len(both_filtered)}")
print("=" * 60)
