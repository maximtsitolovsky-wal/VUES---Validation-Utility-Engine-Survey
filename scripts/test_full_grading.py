"""Full mock grading test with different survey types."""
import sys
sys.path.insert(0, 'src')
import pandas as pd
from unittest.mock import patch
from siteowlqa.python_grader import grade_submission_in_python
from siteowlqa.config import load_config, SURVEY_TYPE_CCTV, SURVEY_TYPE_FA_INTRUSION, SURVEY_TYPE_BOTH

cfg = load_config()

# Mock reference data - has all columns
MOCK_REFERENCE = pd.DataFrame({
    'Name': ['CAM-001', 'CAM-002', 'PANEL-01'],
    'Abbreviated Name': ['C1', 'C2', 'P1'],
    'Part Number': ['PN001', 'PN002', 'PN003'],
    'Manufacturer': ['Axis', 'Hikvision', 'Honeywell'],
    'IP Address': ['10.0.0.1', '10.0.0.2', '10.0.0.3'],
    'MAC Address': ['AA:BB:CC:DD:EE:01', 'AA:BB:CC:DD:EE:02', 'AA:BB:CC:DD:EE:03'],
    'IP / Analog': ['IP', 'IP', 'IP'],
    'Description': ['Front entrance', 'Back door', 'Main panel'],
})

# Submission that matches CCTV cols but NOT FA/Intrusion cols
SUBMISSION_CCTV_ONLY = pd.DataFrame({
    'Name': ['CAM-001', 'CAM-002', 'PANEL-01'],  # CORRECT
    'Abbreviated Name': ['WRONG', 'WRONG', 'WRONG'],  # WRONG
    'Part Number': ['PN001', 'PN002', 'PN003'],  # CORRECT
    'Manufacturer': ['Axis', 'Hikvision', 'Honeywell'],  # CORRECT
    'IP Address': ['10.0.0.1', '10.0.0.2', '10.0.0.3'],  # CORRECT
    'MAC Address': ['AA:BB:CC:DD:EE:01', 'AA:BB:CC:DD:EE:02', 'AA:BB:CC:DD:EE:03'],  # CORRECT
    'IP / Analog': ['IP', 'IP', 'IP'],  # CORRECT
    'Description': ['WRONG', 'WRONG', 'WRONG'],  # WRONG
})

results = []
results.append("=" * 70)
results.append("FULL MOCK GRADING TEST - SURVEY TYPE ROUTING")
results.append("=" * 70)
results.append("")
results.append("Submission has CORRECT values for CCTV columns only.")
results.append("Abbreviated Name and Description are intentionally WRONG.")
results.append("")

def mock_fetch(cfg, site_number):
    return MOCK_REFERENCE.copy()

with patch('siteowlqa.python_grader.fetch_reference_rows', mock_fetch):
    # Test 1: CCTV - should PASS (only checks CCTV columns)
    outcome_cctv = grade_submission_in_python(
        cfg=cfg,
        submission_df=SUBMISSION_CCTV_ONLY.copy(),
        submission_id='TEST-CCTV',
        site_number='9999',
        survey_type=SURVEY_TYPE_CCTV,
    )
    results.append(f"TEST 1: CCTV Survey Type")
    results.append(f"  Status: {outcome_cctv.result.status.value}")
    results.append(f"  Score: {outcome_cctv.result.score}")
    results.append(f"  Expected: PASS (CCTV cols are correct, ignores Abbreviated/Description)")
    results.append("")

    # Test 2: FA/Intrusion - should FAIL (checks Abbreviated/Description which are WRONG)
    outcome_fa = grade_submission_in_python(
        cfg=cfg,
        submission_df=SUBMISSION_CCTV_ONLY.copy(),
        submission_id='TEST-FA',
        site_number='9999',
        survey_type=SURVEY_TYPE_FA_INTRUSION,
    )
    results.append(f"TEST 2: FA/Intrusion Survey Type")
    results.append(f"  Status: {outcome_fa.result.status.value}")
    results.append(f"  Score: {outcome_fa.result.score}")
    results.append(f"  Expected: FAIL (Abbreviated Name and Description are WRONG)")
    results.append("")

    # Test 3: BOTH - should FAIL (checks ALL columns, some are WRONG)
    outcome_both = grade_submission_in_python(
        cfg=cfg,
        submission_df=SUBMISSION_CCTV_ONLY.copy(),
        submission_id='TEST-BOTH',
        site_number='9999',
        survey_type=SURVEY_TYPE_BOTH,
    )
    results.append(f"TEST 3: BOTH Survey Type")
    results.append(f"  Status: {outcome_both.result.status.value}")
    results.append(f"  Score: {outcome_both.result.score}")
    results.append(f"  Expected: FAIL (Abbreviated Name and Description are WRONG)")
    results.append("")

results.append("=" * 70)

# Validate results
cctv_pass = outcome_cctv.result.status.value == "PASS"
fa_fail = outcome_fa.result.status.value == "FAIL"
both_fail = outcome_both.result.status.value == "FAIL"

if cctv_pass and fa_fail and both_fail:
    results.append("[PASS] ALL TESTS PASSED - SURVEY TYPE ROUTING IS WORKING!")
else:
    results.append("[FAIL] TESTS FAILED:")
    if not cctv_pass:
        results.append(f"   - CCTV should be PASS but was {outcome_cctv.result.status.value}")
    if not fa_fail:
        results.append(f"   - FA/Intrusion should be FAIL but was {outcome_fa.result.status.value}")
    if not both_fail:
        results.append(f"   - BOTH should be FAIL but was {outcome_both.result.status.value}")

results.append("=" * 70)

output = '\n'.join(results)
print(output)
with open('test_grading_output.txt', 'w') as f:
    f.write(output)
