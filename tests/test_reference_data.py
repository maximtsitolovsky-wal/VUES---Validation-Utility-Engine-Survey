"""Regression tests for workbook-backed reference data."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pandas as pd

from siteowlqa.reference_data import (
    clear_reference_workbook_cache,
    fetch_reference_rows,
    fetch_site_reference_profile,
    normalize_reference_dataframe,
    _resolve_reference_source,
)


class ReferenceDataTests(unittest.TestCase):
    def tearDown(self) -> None:
        clear_reference_workbook_cache()

    def test_normalize_reference_dataframe_maps_aliases(self) -> None:
        """normalize_reference_dataframe must map vendor-export alias headers to
        canonical VENDOR_GRADE_COLUMNS names and return ONLY those 8 columns.

        Project ID / Plan ID are intentionally excluded from the output:
        the function is designed to return the 8 comparable grade columns only.
        Aliases such as 'ProjectID' are renamed internally but dropped by the
        final VENDOR_GRADE_COLUMNS slice (pre-existing behaviour, not a bug).
        """
        raw_df = pd.DataFrame(
            [
                {
                    "ProjectID": "100",
                    "PlanID": "P1",
                    "Name": "Cam A",
                    "AbbreviatedName": "CA",
                    "PartNumber": "PN-1",
                    "Manufacturer": "Acme",
                    "IPAddress": "1.1.1.1",
                    "MACAddress": "AA",
                    "IPAnalog": "IP",
                    "Description": "Front",
                }
            ]
        )

        normalized = normalize_reference_dataframe(raw_df)

        # Output must be exactly the 8 VENDOR_GRADE_COLUMNS — no more, no less.
        self.assertEqual(
            list(normalized.columns),
            [
                "Name",
                "Abbreviated Name",
                "Part Number",
                "Manufacturer",
                "IP Address",
                "MAC Address",
                "IP / Analog",
                "Description",
            ],
        )
        # Verify alias rename worked correctly for key columns.
        self.assertEqual(normalized.iloc[0]["Name"], "Cam A")  # raw value, not uppercased
        self.assertEqual(normalized.iloc[0]["Part Number"], "PN-1")
        self.assertEqual(normalized.iloc[0]["IP Address"], "1.1.1.1")
        self.assertEqual(normalized.iloc[0]["MAC Address"], "AA")

    def test_fetch_reference_rows_uses_excel_site_id_groups(self) -> None:
        with TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "reference.xlsx"
            pd.DataFrame(
                [
                    {
                        "SelectedSiteID": "3445",
                        "Project ID": "AAA",
                        "Plan ID": "P-1",
                        "Name": "Cam A",
                        "Part Number": "PN-1",
                        "Manufacturer": "Acme",
                        "IP Address": "1.1.1.1",
                        "MAC Address": "AA",
                        "IP / Analog": "IP",
                        "Description": "Front",
                    },
                    {
                        "SelectedSiteID": "3445",
                        "Project ID": "BBB",
                        "Plan ID": "P-2",
                        "Name": "Cam B",
                        "Part Number": "PN-2",
                        "Manufacturer": "Acme",
                        "IP Address": "1.1.1.2",
                        "MAC Address": "BB",
                        "IP / Analog": "IP",
                        "Description": "Rear",
                    },
                    {
                        "SelectedSiteID": "9999",
                        "Project ID": "ZZZ",
                        "Plan ID": "P-9",
                        "Name": "Other",
                        "Part Number": "PN-9",
                        "Manufacturer": "OtherCo",
                        "IP Address": "9.9.9.9",
                        "MAC Address": "ZZ",
                        "IP / Analog": "IP",
                        "Description": "Elsewhere",
                    },
                ]
            ).to_excel(workbook_path, index=False)

            cfg = SimpleNamespace(
                reference_source="excel",
                reference_workbook_path=workbook_path,
                reference_workbook_sheet="",
                reference_workbook_site_id_column="SelectedSiteID",
            )

            rows_3445 = fetch_reference_rows(cfg, "3445")
            rows_9999 = fetch_reference_rows(cfg, "9999")
            rows_missing = fetch_reference_rows(cfg, "0000")

            self.assertEqual(len(rows_3445), 2)
            self.assertEqual(set(rows_3445["Name"].tolist()), {"Cam A", "Cam B"})
            self.assertEqual(len(rows_9999), 1)
            self.assertEqual(rows_9999.iloc[0]["Name"], "Other")
            self.assertTrue(rows_missing.empty)

    def test_fetch_site_reference_profile_from_excel_detects_optional_fields(self) -> None:
        with TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "reference.xlsx"
            pd.DataFrame(
                [
                    {
                        "Site ID": "3445",
                        "Project ID": "AAA",
                        "Name": "Cam A",
                        "Abbreviated Name": "A1",
                        "Part Number": "PN-1",
                        "Manufacturer": "Acme",
                        "IP Address": "1.1.1.1",
                        "MAC Address": "AA",
                        "IP / Analog": "IP",
                        "Description": "0",
                    },
                    {
                        "Site ID": "3445",
                        "Project ID": "AAA",
                        "Name": "Cam B",
                        "Abbreviated Name": "",
                        "Part Number": "PN-2",
                        "Manufacturer": "Acme",
                        "IP Address": "1.1.1.2",
                        "MAC Address": "BB",
                        "IP / Analog": "IP",
                        "Description": "Rear",
                    },
                ]
            ).to_excel(workbook_path, index=False)

            cfg = SimpleNamespace(
                reference_source="excel",
                reference_workbook_path=workbook_path,
                reference_workbook_sheet="",
                reference_workbook_site_id_column="Site ID",
            )

            profile = fetch_site_reference_profile(cfg, "3445")

            self.assertTrue(profile.has_reference_rows)
            self.assertEqual(profile.reference_row_count, 2)
            self.assertTrue(profile.optional_fields_populated["Abbreviated Name"])
            self.assertTrue(profile.optional_fields_populated["Description"])


if __name__ == "__main__":
    unittest.main()


class BigQueryFallbackTests(unittest.TestCase):
    """Tests for the bigquery_with_fallback reference source mode."""

    def setUp(self) -> None:
        self.temp_dir_ctx = TemporaryDirectory()
        self.temp_dir = self.temp_dir_ctx.__enter__()
        
        # Create a minimal reference workbook for fallback tests
        self.workbook_path = Path(self.temp_dir) / "reference.xlsx"
        pd.DataFrame(
            [
                {
                    "SelectedSiteID": "1234",
                    "Name": "Excel Cam",
                    "Part Number": "EXCEL-PN-1",
                    "Manufacturer": "FallbackCorp",
                    "IP Address": "10.0.0.1",
                    "MAC Address": "EXCEL:MAC",
                    "IP / Analog": "IP",
                    "Description": "From Excel fallback",
                },
            ]
        ).to_excel(self.workbook_path, index=False)
        
        self.fallback_cfg = SimpleNamespace(
            reference_source="bigquery_with_fallback",
            reference_workbook_path=self.workbook_path,
            reference_workbook_sheet="",
            reference_workbook_site_id_column="SelectedSiteID",
            gcp_project="test-project",
            bigquery_dataset="test_dataset",
            bigquery_location="US",
            gcp_credentials_path="",
        )

    def tearDown(self) -> None:
        clear_reference_workbook_cache()
        self.temp_dir_ctx.__exit__(None, None, None)

    def test_resolve_reference_source_accepts_fallback_mode(self) -> None:
        """bigquery_with_fallback should be a valid source option."""
        source = _resolve_reference_source(self.fallback_cfg)
        self.assertEqual(source, "bigquery_with_fallback")

    def test_fallback_mode_requires_workbook_path(self) -> None:
        """bigquery_with_fallback requires a workbook path for fallback."""
        cfg = SimpleNamespace(
            reference_source="bigquery_with_fallback",
            reference_workbook_path=None,  # No fallback target!
        )
        with self.assertRaises(ValueError) as ctx:
            _resolve_reference_source(cfg)
        self.assertIn("bigquery_with_fallback requires REFERENCE_WORKBOOK_PATH", str(ctx.exception))

    @patch("siteowlqa.reference_data.fetch_reference_rows_from_bigquery")
    def test_fallback_uses_bq_when_bq_succeeds(self, mock_bq_fetch: MagicMock) -> None:
        """When BQ succeeds, fallback mode should use BQ data, not Excel."""
        # BQ returns different data than Excel workbook
        bq_result = pd.DataFrame(
            [
                {
                    "Name": "BQ Camera",
                    "Abbreviated Name": "",
                    "Part Number": "BQ-PN-1",
                    "Manufacturer": "BigQueryCorp",
                    "IP Address": "192.168.1.1",
                    "MAC Address": "BQ:MAC:ADDR",
                    "IP / Analog": "IP",
                    "Description": "From BigQuery",
                }
            ]
        )
        mock_bq_fetch.return_value = bq_result

        result = fetch_reference_rows(self.fallback_cfg, "1234")

        mock_bq_fetch.assert_called_once()
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["Name"], "BQ Camera")
        self.assertEqual(result.iloc[0]["Manufacturer"], "BigQueryCorp")

    @patch("siteowlqa.reference_data.fetch_reference_rows_from_bigquery")
    def test_fallback_uses_excel_when_bq_fails(self, mock_bq_fetch: MagicMock) -> None:
        """When BQ throws an exception, fallback mode should use Excel data."""
        mock_bq_fetch.side_effect = RuntimeError("BQ quota exceeded — simulated failure")

        result = fetch_reference_rows(self.fallback_cfg, "1234")

        mock_bq_fetch.assert_called_once()
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["Name"], "Excel Cam")
        self.assertEqual(result.iloc[0]["Manufacturer"], "FallbackCorp")

    @patch("siteowlqa.reference_data.fetch_reference_rows_from_bigquery")
    def test_fallback_raises_when_both_fail(self, mock_bq_fetch: MagicMock) -> None:
        """When BOTH BQ and Excel fail, we should get a clear RuntimeError."""
        mock_bq_fetch.side_effect = RuntimeError("BQ is down")
        
        # Point to a non-existent workbook to make Excel fail too
        cfg = SimpleNamespace(
            reference_source="bigquery_with_fallback",
            reference_workbook_path=Path("/nonexistent/path/workbook.xlsx"),
            reference_workbook_sheet="",
            reference_workbook_site_id_column="SelectedSiteID",
            gcp_project="test-project",
            bigquery_dataset="test_dataset",
            bigquery_location="US",
            gcp_credentials_path="",
        )

        with self.assertRaises(RuntimeError) as ctx:
            fetch_reference_rows(cfg, "1234")
        
        self.assertIn("Both BigQuery AND Excel fallback failed", str(ctx.exception))
