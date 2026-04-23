"""Full grading test with row filtering."""
import sys
sys.path.insert(0, 'src')
import pandas as pd
from unittest.mock import patch
from siteowlqa.python_grader import grade_submission_in_python
from siteowlqa.config import load_config, SURVEY_TYPE_CCTV, SURVEY_TYPE_FA_INTRUSION, SURVEY_TYPE_BOTH

cfg = load_config()

# Reference data with mixed CCTV and FA/Intrusion devices
MOCK_REFERENCE = pd.DataFrame({
    'Name': ['CAM-001', 'CAM-002', 'PANEL-01', 'PANEL-02'],
    'Abbreviated Name': ['', '', 'P1', 'P2'],
    'Part Number': ['PN001', 'PN002', 'PN003', 'PN004'],
    'Manufacturer': ['Axis', 'Hikvision', 'Honeywell', 'Bosch'],
    'IP Address': ['10.0.0.1', '10.0.0.2', '10.0.0.3', '10.0.0.4'],
    'MAC Address': ['AA:BB:01', 'AA:BB:02', 'AA:BB:03', 'AA:BB:04'],
    'IP / Analog': ['IP', 'IP', 'IP', 'IP'],
    'Description': ['', '', 'Main panel', 'Sub panel'],
})

# Submission: CCTV columns are CORRECT, FA/Intrusion columns are WRONG
SUBMISSION = pd.DataFrame({
    'Name': ['CAM-001', 'CAM-002', 'PANEL-01', 'PANEL-02'],  # All correct
    'Abbreviated Name': ['', '', 'WRONG', 'WRONG'],  # FA cols wrong
    'Part Number': ['PN001', 'PN002', 'PN003', 'PN004'],  # All correct
    'Manufacturer': ['Axis', 'Hikvision', 'Honeywell', 'Bosch'],  # All correct
    'IP Address': ['10.0.0.1', '10.0.0.2', '10.0.0.3', '10.0.0.4'],  # All correct
    'MAC Address': ['AA:BB:01', 'AA:BB:02', 'AA:BB:03', 'AA:BB:04'],  # All correct
    'IP / Analog': ['IP', 'IP', 'IP', 'IP'],  # All correct
    'Description': ['', '', 'WRONG', 'WRONG'],  # FA cols wrong
})

print("=" * 70)
print("FULL GRADING TEST WITH ROW FILTERING")
print("=" * 70)
print()
print("Reference: 4 rows (2 CCTV cameras, 2 FA/Intrusion panels)")
print("Submission: CCTV columns correct, FA/Intrusion columns WRONG")
print()

def mock_fetch(cfg, site_number):
    return MOCK_REFERENCE.copy()

with patch('siteowlqa.python_grader.fetch_reference_rows', mock_fetch):
    # Test CCTV - should filter to 2 camera rows, all correct = PASS
    outcome_cctv = grade_submission_in_python(
        cfg=cfg,
        submission_df=SUBMISSION.copy(),
        submission_id='TEST-CCTV',
        site_number='9999',
        survey_type=SURVEY_TYPE_CCTV,
    )
    print(f"CCTV:")
    print(f"  Rows graded: {outcome_cctv.submission_row_count} / {outcome_cctv.reference_row_count}")
    print(f"  Status: {outcome_cctv.result.status.value}")
    print(f"  Score: {outcome_cctv.result.score}")
    print(f"  Expected: 2 rows, PASS (camera rows only, all correct)")
    print()

    # Test FA/Intrusion - should filter to 2 panel rows, wrong values = FAIL
    outcome_fa = grade_submission_in_python(
        cfg=cfg,
        submission_df=SUBMISSION.copy(),
        submission_id='TEST-FA',
        site_number='9999',
        survey_type=SURVEY_TYPE_FA_INTRUSION,
    )
    print(f"FA/Intrusion:")
    print(f"  Rows graded: {outcome_fa.submission_row_count} / {outcome_fa.reference_row_count}")
    print(f"  Status: {outcome_fa.result.status.value}")
    print(f"  Score: {outcome_fa.result.score}")
    print(f"  Expected: 2 rows, FAIL (panel rows only, Abbreviated/Description wrong)")
    print()

    # Test BOTH - all 4 rows, some wrong = FAIL
    outcome_both = grade_submission_in_python(
        cfg=cfg,
        submission_df=SUBMISSION.copy(),
        submission_id='TEST-BOTH',
        site_number='9999',
        survey_type=SURVEY_TYPE_BOTH,
    )
    print(f"BOTH:")
    print(f"  Rows graded: {outcome_both.submission_row_count} / {outcome_both.reference_row_count}")
    print(f"  Status: {outcome_both.result.status.value}")
    print(f"  Score: {outcome_both.result.score}")
    print(f"  Expected: 4 rows, FAIL (all rows, FA columns wrong)")
    print()

print("=" * 70)
cctv_ok = outcome_cctv.result.status.value == "PASS" and outcome_cctv.submission_row_count == 2
fa_ok = outcome_fa.result.status.value == "FAIL" and outcome_fa.submission_row_count == 2
both_ok = outcome_both.result.status.value == "FAIL" and outcome_both.submission_row_count == 4

if cctv_ok and fa_ok and both_ok:
    print("[PASS] ROW FILTERING + GRADING WORKS!")
else:
    print("[FAIL] Issues detected:")
    if not cctv_ok: print(f"  CCTV: expected PASS with 2 rows")
    if not fa_ok: print(f"  FA: expected FAIL with 2 rows")
    if not both_ok: print(f"  BOTH: expected FAIL with 4 rows")
print("=" * 70)
