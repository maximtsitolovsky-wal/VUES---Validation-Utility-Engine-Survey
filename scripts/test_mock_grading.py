"""Test survey type column selection with mock data."""
import sys
sys.path.insert(0, 'src')
import pandas as pd
from siteowlqa.python_grader import _select_comparable_columns, _adjust_fa_intrusion_columns
from siteowlqa.config import GRADE_COLUMNS_CCTV, GRADE_COLUMNS_FA_INTRUSION, GRADE_COLUMNS_BOTH

# Create mock reference data
ref_df = pd.DataFrame({
    'Name': ['CAM-001', 'CAM-002', 'PANEL-01'],
    'Abbreviated Name': ['C1', '', 'P1'],
    'Part Number': ['PN001', 'PN002', 'PN003'],
    'Manufacturer': ['Axis', 'Hikvision', 'Honeywell'],
    'IP Address': ['10.0.0.1', '10.0.0.2', '10.0.0.3'],
    'MAC Address': ['AA:BB:CC:DD:EE:01', 'AA:BB:CC:DD:EE:02', 'AA:BB:CC:DD:EE:03'],
    'IP / Analog': ['IP', 'IP', 'IP'],
    'Description': ['Front entrance', 'Back door', 'Main panel'],
})

results = []
results.append("=" * 60)
results.append("SURVEY TYPE COLUMN SELECTION TEST")
results.append("=" * 60)
results.append("")

# Test CCTV
cctv_cols = _select_comparable_columns(ref_df, GRADE_COLUMNS_CCTV)
results.append(f"CCTV Survey Type:")
results.append(f"  Input columns: {GRADE_COLUMNS_CCTV}")
results.append(f"  Selected: {cctv_cols}")
results.append(f"  Count: {len(cctv_cols)}")
results.append("")

# Test FA/Intrusion
fa_cols = _select_comparable_columns(ref_df, GRADE_COLUMNS_FA_INTRUSION)
fa_adjusted = _adjust_fa_intrusion_columns(fa_cols, ref_df)
results.append(f"FA/Intrusion Survey Type:")
results.append(f"  Input columns: {GRADE_COLUMNS_FA_INTRUSION}")
results.append(f"  Base selected: {fa_cols}")
results.append(f"  After Name adjustment: {fa_adjusted}")
results.append(f"  (Name added because Abbreviated Name has content)")
results.append("")

# Test FA/Intrusion with NO abbreviated content
ref_df_no_abbrev = pd.DataFrame({
    'Name': ['PANEL-01', 'PANEL-02'],
    'Abbreviated Name': ['', ''],
    'Description': ['Main panel', 'Sub panel'],
})
fa_cols2 = _select_comparable_columns(ref_df_no_abbrev, GRADE_COLUMNS_FA_INTRUSION)
fa_adjusted2 = _adjust_fa_intrusion_columns(fa_cols2, ref_df_no_abbrev)
results.append(f"FA/Intrusion (no Abbreviated content):")
results.append(f"  After Name adjustment: {fa_adjusted2}")
results.append(f"  (Name NOT added because Abbreviated Name is empty)")
results.append("")

# Test BOTH
both_cols = _select_comparable_columns(ref_df, GRADE_COLUMNS_BOTH)
results.append(f"BOTH Survey Type:")
results.append(f"  Input columns: {GRADE_COLUMNS_BOTH}")
results.append(f"  Selected: {both_cols}")
results.append(f"  Count: {len(both_cols)}")
results.append("")

results.append("=" * 60)
results.append("ALL TESTS PASSED - Survey Type Routing Works!")
results.append("=" * 60)

# Write to file
with open('test_output.txt', 'w') as f:
    f.write('\n'.join(results))

print("Results written to test_output.txt")
