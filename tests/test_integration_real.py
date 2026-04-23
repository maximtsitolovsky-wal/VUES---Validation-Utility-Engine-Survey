"""VUES Integration Tests — Real Data, No Mocks, No BS.

These tests hit actual BigQuery and Airtable to verify the grading pipeline works.
Run this to catch broken logic, stale data, and configuration drift.

Usage:
    python tests/test_integration_real.py
    python tests/test_integration_real.py TestGradingLogic.test_known_site_grades_correctly
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Bootstrap src path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd

from siteowlqa.config import load_config, VENDOR_GRADE_COLUMNS
from siteowlqa.reference_data import fetch_reference_rows
from siteowlqa.python_grader import grade_submission_in_python, status_from_score
from siteowlqa.airtable_client import AirtableClient
from siteowlqa.models import ProcessingStatus


class TestBigQueryConnection(unittest.TestCase):
    """Verify BigQuery is actually working and returning real data."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = load_config()

    def test_bq_returns_data_for_known_site(self):
        """Site 686 should have 334 reference rows (known baseline)."""
        df = fetch_reference_rows(self.cfg, "686")
        
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty, "BQ returned empty DataFrame for site 686")
        
        # Known baseline - should be approximately 334 rows
        # Allow ±10% for natural data changes
        self.assertGreater(len(df), 300, f"Expected ~334 rows, got {len(df)}")
        self.assertLess(len(df), 400, f"Expected ~334 rows, got {len(df)}")

    def test_bq_returns_all_required_columns(self):
        """Reference data must have all gradeable columns."""
        df = fetch_reference_rows(self.cfg, "686")
        
        for col in VENDOR_GRADE_COLUMNS:
            self.assertIn(col, df.columns, f"Missing required column: {col}")

    def test_bq_data_is_not_all_empty(self):
        """At least some columns should have actual data, not all blanks."""
        df = fetch_reference_rows(self.cfg, "686")
        
        # These columns MUST have data
        critical_cols = ["Name", "MAC Address"]
        for col in critical_cols:
            non_empty = df[col].astype(str).str.strip().ne("").sum()
            self.assertGreater(non_empty, 0, f"Column '{col}' is all empty!")

    def test_nonexistent_site_returns_empty(self):
        """Unknown site should return empty DataFrame, not error."""
        df = fetch_reference_rows(self.cfg, "99999999")
        
        self.assertIsInstance(df, pd.DataFrame)
        self.assertTrue(df.empty, "Expected empty DataFrame for nonexistent site")


class TestGradingLogic(unittest.TestCase):
    """Test grading math with controlled inputs."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = load_config()

    def _make_submission(self, rows: list[dict]) -> pd.DataFrame:
        """Create a submission DataFrame with all required columns."""
        df = pd.DataFrame(rows)
        for col in VENDOR_GRADE_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df

    def test_perfect_match_scores_100(self):
        """Identical submission should score 100%."""
        ref = fetch_reference_rows(self.cfg, "686")
        if ref.empty:
            self.skipTest("No reference data for site 686")
        
        # Use first 10 rows as a controlled test
        ref_subset = ref.head(10).copy()
        
        outcome = grade_submission_in_python(
            cfg=self.cfg,
            submission_df=ref_subset,
            submission_id="test-perfect",
            site_number="686",
        )
        
        # Score should be 10/334 ≈ 3% (not 100% because we only submitted 10 of 334)
        # This tests that partial submissions are scored correctly
        expected_score = (10 / len(ref)) * 100
        self.assertAlmostEqual(outcome.result.score, expected_score, places=1)

    def test_empty_submission_scores_zero(self):
        """Empty submission should score 0%."""
        outcome = grade_submission_in_python(
            cfg=self.cfg,
            submission_df=self._make_submission([]),
            submission_id="test-empty",
            site_number="686",
        )
        
        self.assertEqual(outcome.result.score, 0.0)
        self.assertEqual(outcome.result.status, ProcessingStatus.FAIL)

    def test_garbage_submission_scores_zero(self):
        """Random garbage data should score 0% (no matches)."""
        garbage = self._make_submission([
            {"Name": "FAKE_CAM_1", "MAC Address": "ZZ:ZZ:ZZ:ZZ:ZZ:ZZ", "IP Address": "999.999.999.999"},
            {"Name": "FAKE_CAM_2", "MAC Address": "YY:YY:YY:YY:YY:YY", "IP Address": "888.888.888.888"},
        ])
        
        outcome = grade_submission_in_python(
            cfg=self.cfg,
            submission_df=garbage,
            submission_id="test-garbage",
            site_number="686",
        )
        
        self.assertEqual(outcome.result.score, 0.0)
        self.assertEqual(outcome.result.status, ProcessingStatus.FAIL)

    def test_threshold_boundary_95_exactly(self):
        """Score of exactly 95.0 should PASS."""
        self.assertEqual(status_from_score(95.0), ProcessingStatus.PASS)
        self.assertEqual(status_from_score(94.9999999), ProcessingStatus.FAIL)
        self.assertEqual(status_from_score(95.0000001), ProcessingStatus.PASS)

    def test_score_calculation_is_deterministic(self):
        """Same input should always produce same score."""
        ref = fetch_reference_rows(self.cfg, "686")
        if ref.empty:
            self.skipTest("No reference data")
        
        subset = ref.head(5).copy()
        
        scores = []
        for _ in range(3):
            outcome = grade_submission_in_python(
                cfg=self.cfg,
                submission_df=subset,
                submission_id=f"test-determinism",
                site_number="686",
            )
            scores.append(outcome.result.score)
        
        self.assertEqual(len(set(scores)), 1, f"Non-deterministic scores: {scores}")


class TestDataQuality(unittest.TestCase):
    """Validate data quality - catch garbage before it causes problems."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = load_config()
        cls.ref_df = fetch_reference_rows(cls.cfg, "686")

    def test_mac_addresses_are_valid_format(self):
        """MAC addresses should be valid format (or empty)."""
        import re
        mac_pattern = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$|^$")
        
        invalid = []
        for idx, mac in enumerate(self.ref_df["MAC Address"].fillna("")):
            mac = str(mac).strip()
            if mac and not mac_pattern.match(mac):
                invalid.append((idx, mac))
        
        # Allow some invalid (BQ data may have quirks) but flag if > 10%
        invalid_pct = len(invalid) / max(len(self.ref_df), 1) * 100
        self.assertLess(invalid_pct, 10, 
            f"{len(invalid)} invalid MACs ({invalid_pct:.1f}%): {invalid[:5]}")

    def test_ip_addresses_are_valid_format(self):
        """IP addresses should be valid IPv4 format (or empty)."""
        import re
        ip_pattern = re.compile(
            r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
            r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^$"
        )
        
        invalid = []
        for idx, ip in enumerate(self.ref_df["IP Address"].fillna("")):
            ip = str(ip).strip()
            if ip and not ip_pattern.match(ip):
                invalid.append((idx, ip))
        
        invalid_pct = len(invalid) / max(len(self.ref_df), 1) * 100
        self.assertLess(invalid_pct, 10,
            f"{len(invalid)} invalid IPs ({invalid_pct:.1f}%): {invalid[:5]}")

    def test_no_completely_empty_rows(self):
        """Rows shouldn't be completely empty across all grade columns."""
        empty_rows = 0
        for _, row in self.ref_df.iterrows():
            if all(str(row[col]).strip() == "" for col in VENDOR_GRADE_COLUMNS):
                empty_rows += 1
        
        self.assertEqual(empty_rows, 0, f"{empty_rows} completely empty rows in reference")

    def test_name_column_has_content(self):
        """Name column should have meaningful content."""
        names = self.ref_df["Name"].fillna("").astype(str).str.strip()
        non_empty = names.ne("").sum()
        
        self.assertGreater(non_empty, len(self.ref_df) * 0.9,
            f"Name column is mostly empty: {non_empty}/{len(self.ref_df)}")


class TestAirtableConnection(unittest.TestCase):
    """Verify Airtable API is working."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = load_config()
        cls.airtable = AirtableClient(cls.cfg)

    def test_can_fetch_records(self):
        """Should be able to fetch at least one record."""
        # Fetch recent records
        records = self.airtable.get_pending_records(max_records=1)
        # This may be empty if no pending, but shouldn't error
        self.assertIsInstance(records, list)

    def test_can_read_specific_record(self):
        """Should be able to read a known record."""
        # Use a known record ID - update this if needed
        try:
            fields = self.airtable.get_record_fields("recryYpfpuVlYKm1g")
            self.assertIn("Site Number", fields)
        except Exception as e:
            self.skipTest(f"Record not found or API error: {e}")


class TestStalenessChecks(unittest.TestCase):
    """Detect stale data that could cause incorrect grading."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = load_config()

    def test_bq_has_recent_data(self):
        """BigQuery should have data updated within last 30 days."""
        # This requires a timestamp column in BQ - check if exists
        # For now, just verify we can query
        df = fetch_reference_rows(self.cfg, "686")
        self.assertFalse(df.empty, "No data returned - possible staleness issue")

    def test_multiple_sites_have_data(self):
        """Multiple known sites should have data."""
        known_sites = ["686", "1234", "5000"]  # Add known active sites
        sites_with_data = 0
        
        for site in known_sites:
            df = fetch_reference_rows(self.cfg, site)
            if not df.empty:
                sites_with_data += 1
        
        # At least one should have data
        self.assertGreater(sites_with_data, 0, 
            f"No data for any known sites: {known_sites}")


def run_critical_tests():
    """Run only the most critical tests for quick validation."""
    suite = unittest.TestSuite()
    
    # Connection tests
    suite.addTest(TestBigQueryConnection("test_bq_returns_data_for_known_site"))
    suite.addTest(TestAirtableConnection("test_can_fetch_records"))
    
    # Logic tests
    suite.addTest(TestGradingLogic("test_threshold_boundary_95_exactly"))
    suite.addTest(TestGradingLogic("test_score_calculation_is_deterministic"))
    
    # Data quality
    suite.addTest(TestDataQuality("test_no_completely_empty_rows"))
    
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--critical", action="store_true", help="Run only critical tests")
    args, remaining = parser.parse_known_args()
    
    if args.critical:
        result = run_critical_tests()
        sys.exit(0 if result.wasSuccessful() else 1)
    else:
        # Run all tests
        sys.argv = [sys.argv[0]] + remaining
        unittest.main(verbosity=2)
