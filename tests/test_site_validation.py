"""Regression tests for site-indexed validation policy."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from siteowlqa.reference_data import SiteReferenceProfile
from siteowlqa.site_validation import validate_submission_for_site


def _load_result(
    row_count: int,
    missing_required_columns: list[str] | None = None,
    extra_columns: list[str] | None = None,
):
    return SimpleNamespace(
        dataframe=pd.DataFrame([{"x": i} for i in range(row_count)]),
        missing_required_columns=missing_required_columns or [],
        extra_columns=extra_columns or [],
    )


class SiteValidationTests(unittest.TestCase):
    @patch("siteowlqa.site_validation.fetch_site_reference_profile")
    def test_row_count_mismatch_is_diagnostic_only(self, mock_profile) -> None:
        mock_profile.return_value = SiteReferenceProfile(
            site_number="3445",
            reference_row_count=10,
            has_reference_rows=True,
            optional_fields_populated={
                "Abbreviated Name": False,
                "Description": False,
            },
        )

        result = validate_submission_for_site(
            cfg=SimpleNamespace(),
            site_number="3445",
            load_result=_load_result(row_count=8),
        )

        self.assertEqual(result.status, "VALID")
        self.assertTrue(result.is_valid_for_grading)
        self.assertIn("ROW_COUNT_MISMATCH", result.reason_codes)
        self.assertEqual(result.normalized_row_count, 8)
        self.assertEqual(result.reference_row_count, 10)

    @patch("siteowlqa.site_validation.fetch_site_reference_profile")
    def test_missing_critical_columns_still_blocks_grading(self, mock_profile) -> None:
        mock_profile.return_value = SiteReferenceProfile(
            site_number="3445",
            reference_row_count=10,
            has_reference_rows=True,
            optional_fields_populated={
                "Abbreviated Name": False,
                "Description": False,
            },
        )

        result = validate_submission_for_site(
            cfg=SimpleNamespace(),
            site_number="3445",
            load_result=_load_result(
                row_count=10,
                missing_required_columns=["Name", "Manufacturer"],
            ),
        )

        self.assertEqual(result.status, "ERROR")
        self.assertFalse(result.is_valid_for_grading)
        self.assertIn("MISSING_CRITICAL_COLUMNS", result.reason_codes)

    @patch("siteowlqa.site_validation.fetch_site_reference_profile")
    def test_missing_optional_columns_used_by_reference_are_nonfatal(self, mock_profile) -> None:
        mock_profile.return_value = SiteReferenceProfile(
            site_number="3445",
            reference_row_count=5,
            has_reference_rows=True,
            optional_fields_populated={
                "Abbreviated Name": True,
                "Description": True,
            },
        )

        result = validate_submission_for_site(
            cfg=SimpleNamespace(),
            site_number="3445",
            load_result=_load_result(
                row_count=5,
                missing_required_columns=["Abbreviated Name", "Description"],
            ),
        )

        self.assertEqual(result.status, "VALID")
        self.assertTrue(result.is_valid_for_grading)
        self.assertIn(
            "OPTIONAL_COLUMN_MISSING_BUT_USED_BY_REFERENCE:Abbreviated Name",
            result.reason_codes,
        )
        self.assertIn(
            "OPTIONAL_COLUMN_MISSING_BUT_USED_BY_REFERENCE:Description",
            result.reason_codes,
        )

    @patch("siteowlqa.site_validation.fetch_site_reference_profile")
    def test_missing_reference_is_still_error(self, mock_profile) -> None:
        mock_profile.return_value = SiteReferenceProfile(
            site_number="9999",
            reference_row_count=0,
            has_reference_rows=False,
            optional_fields_populated={
                "Abbreviated Name": False,
                "Description": False,
            },
        )

        result = validate_submission_for_site(
            cfg=SimpleNamespace(),
            site_number="9999",
            load_result=_load_result(row_count=3),
        )

        self.assertEqual(result.status, "ERROR")
        self.assertFalse(result.is_valid_for_grading)
        self.assertIn("SITE_REFERENCE_NOT_FOUND", result.reason_codes)


if __name__ == "__main__":
    unittest.main()
