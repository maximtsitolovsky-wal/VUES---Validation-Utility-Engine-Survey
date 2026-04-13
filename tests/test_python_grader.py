"""Regression tests for Python-first site-scoped grading."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from siteowlqa.models import ProcessingStatus
from siteowlqa.python_grader import grade_submission_in_python


VENDOR_COLS = [
    "Project ID",
    "Plan ID",
    "Name",
    "Abbreviated Name",
    "Part Number",
    "Manufacturer",
    "IP Address",
    "MAC Address",
    "IP / Analog",
    "Description",
]



def make_df(rows: list[dict[str, str]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for col in VENDOR_COLS:
        if col not in df.columns:
            df[col] = ""
    return df[VENDOR_COLS]


class PythonGraderTests(unittest.TestCase):
    @patch("siteowlqa.python_grader.fetch_reference_rows")
    def test_pass_when_matching_rows_parallel_after_sort(self, mock_fetch) -> None:
        mock_fetch.return_value = make_df([
            {"Project ID": "9", "Name": "B", "Part Number": "2", "Manufacturer": "ACME", "IP Address": "2", "MAC Address": "BB", "IP / Analog": "IP"},
            {"Project ID": "9", "Name": "A", "Part Number": "1", "Manufacturer": "ACME", "IP Address": "1", "MAC Address": "AA", "IP / Analog": "IP"},
        ])
        submission_df = make_df([
            {"Project ID": "WRONG", "Name": "A", "Part Number": "1", "Manufacturer": "ACME", "IP Address": "1", "MAC Address": "AA", "IP / Analog": "IP", "Extra": "ignored"},
            {"Project ID": "ALSO WRONG", "Name": "B", "Part Number": "2", "Manufacturer": "ACME", "IP Address": "2", "MAC Address": "BB", "IP / Analog": "IP"},
        ])

        outcome = grade_submission_in_python(
            cfg=SimpleNamespace(),
            submission_df=submission_df,
            submission_id="sub-1",
            site_number="9",
        )

        self.assertEqual(outcome.result.status, ProcessingStatus.PASS)
        self.assertEqual(outcome.result.score, 100.0)
        self.assertIsNone(outcome.error_df)

    @patch("siteowlqa.python_grader.fetch_reference_rows")
    def test_fail_when_parallel_row_values_differ(self, mock_fetch) -> None:
        mock_fetch.return_value = make_df([
            {"Project ID": "10", "Name": "CAM 1", "Part Number": "PN1", "Manufacturer": "ACME", "IP Address": "1.1.1.1", "MAC Address": "AA", "IP / Analog": "IP"},
            {"Project ID": "10", "Name": "CAM 2", "Part Number": "PN2", "Manufacturer": "ACME", "IP Address": "1.1.1.2", "MAC Address": "BB", "IP / Analog": "IP"},
        ])
        submission_df = make_df([
            {"Project ID": "10", "Name": "CAM 1", "Part Number": "PN1", "Manufacturer": "ACME", "IP Address": "1.1.1.1", "MAC Address": "AA", "IP / Analog": "IP"},
            {"Project ID": "10", "Name": "CAM X", "Part Number": "PN2", "Manufacturer": "ACME", "IP Address": "1.1.1.2", "MAC Address": "BB", "IP / Analog": "IP"},
        ])

        outcome = grade_submission_in_python(
            cfg=SimpleNamespace(),
            submission_df=submission_df,
            submission_id="sub-2",
            site_number="10",
        )

        self.assertEqual(outcome.result.status, ProcessingStatus.FAIL)
        self.assertEqual(outcome.result.score, 50.0)
        self.assertIsNotNone(outcome.error_df)
        self.assertEqual(len(outcome.error_df), 1)
        self.assertEqual(outcome.error_df.iloc[0]["IssueType"], "ROW_MISMATCH")

    @patch("siteowlqa.python_grader.fetch_reference_rows")
    def test_row_count_mismatch_is_fail_not_error(self, mock_fetch) -> None:
        mock_fetch.return_value = make_df([
            {"Project ID": "11", "Name": "A", "Part Number": "1", "Manufacturer": "ACME", "IP Address": "1", "MAC Address": "AA", "IP / Analog": "IP"},
            {"Project ID": "11", "Name": "B", "Part Number": "2", "Manufacturer": "ACME", "IP Address": "2", "MAC Address": "BB", "IP / Analog": "IP"},
        ])
        submission_df = make_df([
            {"Project ID": "11", "Name": "A", "Part Number": "1", "Manufacturer": "ACME", "IP Address": "1", "MAC Address": "AA", "IP / Analog": "IP"},
        ])

        outcome = grade_submission_in_python(
            cfg=SimpleNamespace(),
            submission_df=submission_df,
            submission_id="sub-3",
            site_number="11",
        )

        # Subset grading: a submission with fewer rows than the reference simply
        # scores proportionally. Missing rows are NOT emitted as issues — the
        # grader only flags EXTRA_ROW (rows submitted that have no reference match)
        # and ROW_MISMATCH (wrong field values). Score = matched/reference = 1/2 = 50%.
        self.assertEqual(outcome.result.status, ProcessingStatus.FAIL)
        self.assertEqual(outcome.result.score, 50.0)
        self.assertIsNotNone(outcome.error_df)

    @patch("siteowlqa.python_grader.fetch_reference_rows")
    def test_duplicate_rows_match_even_when_order_changes(self, mock_fetch) -> None:
        mock_fetch.return_value = make_df([
            {"Project ID": "13", "Name": "CAM", "Abbreviated Name": "ONE", "Part Number": "PN1", "Manufacturer": "ACME", "IP Address": "1", "MAC Address": "AA", "IP / Analog": "IP", "Description": "LEFT"},
            {"Project ID": "13", "Name": "CAM", "Abbreviated Name": "TWO", "Part Number": "PN1", "Manufacturer": "ACME", "IP Address": "1", "MAC Address": "AA", "IP / Analog": "IP", "Description": "RIGHT"},
        ])
        submission_df = make_df([
            {"Project ID": "999", "Name": "CAM", "Abbreviated Name": "TWO", "Part Number": "PN1", "Manufacturer": "ACME", "IP Address": "1", "MAC Address": "AA", "IP / Analog": "IP", "Description": "RIGHT"},
            {"Project ID": "999", "Name": "CAM", "Abbreviated Name": "ONE", "Part Number": "PN1", "Manufacturer": "ACME", "IP Address": "1", "MAC Address": "AA", "IP / Analog": "IP", "Description": "LEFT"},
        ])

        outcome = grade_submission_in_python(
            cfg=SimpleNamespace(),
            submission_df=submission_df,
            submission_id="sub-dup",
            site_number="13",
        )

        self.assertEqual(outcome.result.status, ProcessingStatus.PASS)
        self.assertEqual(outcome.result.score, 100.0)
        self.assertIsNone(outcome.error_df)

    @patch("siteowlqa.python_grader.fetch_reference_rows")
    def test_identity_match_reports_field_mismatch_not_fake_missing_extra(self, mock_fetch) -> None:
        mock_fetch.return_value = make_df([
            {"Project ID": "14", "Name": "CAM", "Abbreviated Name": "OLD", "Part Number": "PN1", "Manufacturer": "ACME", "IP Address": "1", "MAC Address": "AA", "IP / Analog": "IP", "Description": "DESC"},
        ])
        submission_df = make_df([
            {"Project ID": "14", "Name": "CAM", "Abbreviated Name": "NEW", "Part Number": "PN1", "Manufacturer": "ACME", "IP Address": "1", "MAC Address": "AA", "IP / Analog": "IP", "Description": "DESC"},
        ])

        outcome = grade_submission_in_python(
            cfg=SimpleNamespace(),
            submission_df=submission_df,
            submission_id="sub-identity",
            site_number="14",
        )

        self.assertEqual(outcome.result.status, ProcessingStatus.FAIL)
        self.assertIsNotNone(outcome.error_df)
        self.assertEqual(outcome.error_df.iloc[0]["IssueType"], "ROW_MISMATCH")
        self.assertNotIn("MISSING_ROW", set(outcome.error_df["IssueType"].tolist()))
        self.assertNotIn("EXTRA_ROW", set(outcome.error_df["IssueType"].tolist()))

    @patch("siteowlqa.python_grader.fetch_reference_rows")
    def test_missing_reference_is_fail_with_zero_score(self, mock_fetch) -> None:
        mock_fetch.return_value = make_df([])
        submission_df = make_df([
            {"Project ID": "12", "Name": "A", "Part Number": "1", "Manufacturer": "ACME", "IP Address": "1", "MAC Address": "AA", "IP / Analog": "IP"},
        ])

        outcome = grade_submission_in_python(
            cfg=SimpleNamespace(),
            submission_df=submission_df,
            submission_id="sub-4",
            site_number="12",
        )

        self.assertEqual(outcome.result.status, ProcessingStatus.FAIL)
        self.assertEqual(outcome.result.score, 0.0)
        self.assertIn("SITE_REFERENCE_NOT_FOUND", outcome.result.message)

    @patch("siteowlqa.python_grader.fetch_reference_rows")
    def test_threshold_is_pass_at_exactly_95(self, mock_fetch) -> None:
        mock_fetch.return_value = make_df([
            {"Project ID": "15", "Name": f"CAM {i}", "Part Number": f"PN{i}", "Manufacturer": "ACME", "IP Address": f"10.0.0.{i}", "MAC Address": f"MAC{i}", "IP / Analog": "IP"}
            for i in range(1, 21)
        ])
        submission_df = make_df([
            {"Project ID": "15", "Name": f"CAM {i}", "Part Number": f"PN{i}", "Manufacturer": "ACME", "IP Address": f"10.0.0.{i}", "MAC Address": f"MAC{i}", "IP / Analog": "IP"}
            for i in range(1, 20)
        ])

        outcome = grade_submission_in_python(
            cfg=SimpleNamespace(),
            submission_df=submission_df,
            submission_id="sub-95-pass",
            site_number="15",
        )

        self.assertEqual(outcome.result.score, 95.0)
        self.assertEqual(outcome.result.status, ProcessingStatus.PASS)

    @patch("siteowlqa.python_grader.fetch_reference_rows")
    def test_threshold_below_95_is_fail(self, mock_fetch) -> None:
        # 1899 / 2000 = 94.95% → FAIL (< 95.0)
        # 1900 / 2000 = 95.00% → PASS, so we must use 1899 rows.
        mock_fetch.return_value = make_df([
            {"Project ID": "16", "Name": f"CAM {i}", "Part Number": f"PN{i}", "Manufacturer": "ACME", "IP Address": f"10.0.1.{i}", "MAC Address": f"MAC{i}", "IP / Analog": "IP"}
            for i in range(1, 2001)
        ])
        submission_df = make_df([
            {"Project ID": "16", "Name": f"CAM {i}", "Part Number": f"PN{i}", "Manufacturer": "ACME", "IP Address": f"10.0.1.{i}", "MAC Address": f"MAC{i}", "IP / Analog": "IP"}
            for i in range(1, 1900)
        ])

        outcome = grade_submission_in_python(
            cfg=SimpleNamespace(),
            submission_df=submission_df,
            submission_id="sub-94-9999-fail",
            site_number="16",
        )

        self.assertLess(outcome.result.score, 95.0)
        self.assertEqual(outcome.result.status, ProcessingStatus.FAIL)

    @patch("siteowlqa.python_grader.fetch_reference_rows")
    def test_threshold_above_95_is_pass(self, mock_fetch) -> None:
        # 43 / 45 = 95.555...% → PASS (>= 95.0)
        # 44 / 45 = 97.777...% → also PASS (we want a score strictly above 95)
        mock_fetch.return_value = make_df([
            {"Project ID": "17", "Name": f"CAM {i}", "Part Number": f"PN{i}", "Manufacturer": "ACME", "IP Address": f"10.0.2.{i}", "MAC Address": f"MAC{i}", "IP / Analog": "IP"}
            for i in range(1, 46)
        ])
        submission_df = make_df([
            {"Project ID": "17", "Name": f"CAM {i}", "Part Number": f"PN{i}", "Manufacturer": "ACME", "IP Address": f"10.0.2.{i}", "MAC Address": f"MAC{i}", "IP / Analog": "IP"}
            for i in range(1, 44)
        ])

        outcome = grade_submission_in_python(
            cfg=SimpleNamespace(),
            submission_df=submission_df,
            submission_id="sub-95-6-pass",
            site_number="17",
        )

        # 43/45 = 95.555...% — score must be above 95 and status must be PASS
        self.assertGreater(outcome.result.score or 0.0, 95.0)
        self.assertEqual(outcome.result.status, ProcessingStatus.PASS)


if __name__ == "__main__":
    unittest.main()
