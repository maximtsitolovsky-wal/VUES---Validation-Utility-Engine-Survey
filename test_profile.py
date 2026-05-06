#!/usr/bin/env python3
"""Test the survey-type-specific profile."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from siteowlqa.config import load_config, SURVEY_TYPE_FA_INTRUSION, SURVEY_TYPE_CCTV
from siteowlqa.reference_data import fetch_site_reference_profile

cfg = load_config()
print("Config loaded")

# Test without survey type (should return 311)
profile_all = fetch_site_reference_profile(cfg, '457')
print(f'Without survey type: reference_row_count={profile_all.reference_row_count}')

# Test with FA/Intrusion (should return ~140)
profile_fa = fetch_site_reference_profile(cfg, '457', survey_type=SURVEY_TYPE_FA_INTRUSION)
print(f'With FA/Intrusion: reference_row_count={profile_fa.reference_row_count}')
print(f'  cctv_row_count={profile_fa.cctv_row_count}')
print(f'  fa_intrusion_row_count={profile_fa.fa_intrusion_row_count}')

# Test with CCTV (should return ~171)
profile_cctv = fetch_site_reference_profile(cfg, '457', survey_type=SURVEY_TYPE_CCTV)
print(f'With CCTV: reference_row_count={profile_cctv.reference_row_count}')
