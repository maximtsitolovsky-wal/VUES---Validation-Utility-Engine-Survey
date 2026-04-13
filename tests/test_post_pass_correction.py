"""Unit tests for post_pass_correction.py.

Verifies:
  - Module does nothing for True Score < 95.0
  - Module does nothing when archived file is missing
  - True Score is the grade identifier (Airtable "True Score" column value)
  - Corrected CSV preserves exact schema (columns, column order, row count, row order)
  - Original archived file is never modified
  - Raw file is copied untouched to the RAW directory
  - Correction log is generated with expected columns (incl. site_number, vendor_name)
  - Confidence thresholds (APPLY / APPLY+REVIEW / LOG_ONLY / REJECT) are honoured
  - Only supported fields are corrected
  - No rows added or removed
  - Files are labeled {site_number}_{vendor_name}
  - MAC identity match → confidence 1.0, no review flag
  - IP identity match  → confidence 0.99
  - Fuzzy name match 0.80-0.92 → logged, NOT applied
  - Fuzzy name match 0.93-0.98 → applied + review flag
  - Fuzzy name match >= 0.99   → applied, no review flag
  - Fuzzy name match < 0.80    → rejected entirely
"""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from siteowlqa.post_pass_correction import (
    CONF_APPLY,
    CONF_APPLY_REVIEW,
    CONF_LOG_ONLY,
    TRIGGER_TRUE_SCORE,
    CorrectionAttempt,
    CorrectionSummary,
    _apply_corrections,
    _build_correction_attempts,
    _match_row_to_reference,
    _resolve_correctable_fields,
    _safe_filename,
    _write_correction_log,
    run_post_pass_correction,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cfg(tmp_root: Path):
    """Minimal cfg stub with the three correction dirs pointing into tmp."""
    corrected_dir  = tmp_root / "CORRECTED"
    log_dir        = tmp_root / "CORRECTION LOG"
    raw_dir        = tmp_root / "RAW"
    for d in (corrected_dir, log_dir, raw_dir):
        d.mkdir(parents=True, exist_ok=True)
    return SimpleNamespace(
        output_dir=tmp_root / "output",
        correction_corrected_dir=corrected_dir,
        correction_log_dir=log_dir,
        correction_raw_dir=raw_dir,
        reference_source="excel",
        reference_workbook_path=None,
    )


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _ts() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _patch_ref(ref_df: pd.DataFrame):
    return patch(
        "siteowlqa.post_pass_correction.fetch_reference_rows",
        return_value=ref_df,
    )


# ---------------------------------------------------------------------------
# Trigger tests — True Score is the grade identifier
# ---------------------------------------------------------------------------

class TriggerTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._root = Path(self._tmp.name)
        self._vendor = self._root / "submission.csv"
        _write_csv(self._vendor, [
            {"Name": "CAM A", "MAC Address": "AA:BB:CC", "IP Address": "1.1.1.1",
             "Abbreviated Name": "A", "Manufacturer": "ACME", "Part Number": "PN1"},
        ])

    def tearDown(self):
        self._tmp.cleanup()

    def test_true_score_below_threshold_returns_none(self):
        """True Score < 95.0 → correction must not run."""
        cfg = _make_cfg(self._root)
        result = run_post_pass_correction(
            cfg=cfg,
            submission_id="sub-001",
            site_number="S1",
            vendor_name="ACME Corp",
            true_score=94.99,
            archived_file_path=self._vendor,
        )
        self.assertIsNone(result)

    def test_true_score_exactly_at_threshold_triggers(self):
        """True Score == 95.0 → correction must run (>= not >)."""
        ref_df = pd.DataFrame([{
            "Name": "CAM A", "MAC Address": "AA:BB:CC", "IP Address": "1.1.1.1",
            "Abbreviated Name": "A", "Manufacturer": "ACME", "Part Number": "PN1",
        }])
        cfg = _make_cfg(self._root)
        with _patch_ref(ref_df):
            result = run_post_pass_correction(
                cfg=cfg,
                submission_id="sub-095",
                site_number="S1",
                vendor_name="ACME Corp",
                true_score=95.0,
                archived_file_path=self._vendor,
            )
        self.assertIsNotNone(result)

    def test_true_score_above_threshold_triggers(self):
        """True Score > 95.0 → correction must run."""
        ref_df = pd.DataFrame([{
            "Name": "CAM A", "MAC Address": "AA:BB:CC", "IP Address": "1.1.1.1",
            "Abbreviated Name": "A", "Manufacturer": "ACME", "Part Number": "PN1",
        }])
        cfg = _make_cfg(self._root)
        with _patch_ref(ref_df):
            result = run_post_pass_correction(
                cfg=cfg,
                submission_id="sub-099",
                site_number="S1",
                vendor_name="ACME Corp",
                true_score=99.5,
                archived_file_path=self._vendor,
            )
        self.assertIsNotNone(result)

    def test_missing_archived_file_returns_none(self):
        """If archived file is not on disk → correction skips gracefully."""
        cfg = _make_cfg(self._root)
        result = run_post_pass_correction(
            cfg=cfg,
            submission_id="sub-missing",
            site_number="S1",
            vendor_name="ACME Corp",
            true_score=99.0,
            archived_file_path=Path(self._root) / "nonexistent.csv",
        )
        self.assertIsNone(result)

    def test_true_score_stored_in_summary_unchanged(self):
        """CorrectionSummary.true_score must equal the input — never modified."""
        ref_df = pd.DataFrame([{
            "Name": "CAM A", "MAC Address": "AA:BB:CC", "IP Address": "1.1.1.1",
            "Abbreviated Name": "A", "Manufacturer": "ACME", "Part Number": "PN1",
        }])
        cfg = _make_cfg(self._root)
        with _patch_ref(ref_df):
            result = run_post_pass_correction(
                cfg=cfg,
                submission_id="sub-ts",
                site_number="S1",
                vendor_name="ACME Corp",
                true_score=97.345,
                archived_file_path=self._vendor,
            )
        self.assertIsNotNone(result)
        self.assertEqual(result.true_score, 97.345)

    def test_trigger_constant_is_95(self):
        self.assertEqual(TRIGGER_TRUE_SCORE, 95.0)


# ---------------------------------------------------------------------------
# Output directory + file naming tests
# ---------------------------------------------------------------------------

class OutputDirectoryTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._root = Path(self._tmp.name)
        self._vendor = self._root / "submission.csv"
        self._rows = [
            {
                "Name": "CAM A", "Abbreviated Name": "A-WRONG",
                "Part Number": "PN1", "Manufacturer": "ACME",
                "IP Address": "1.1.1.1", "MAC Address": "AA:AA:AA",
                "IP / Analog": "IP",
            },
        ]
        _write_csv(self._vendor, self._rows)
        self._ref_df = pd.DataFrame([{
            "Name": "CAM A", "Abbreviated Name": "A-CORRECT",
            "Part Number": "PN1", "Manufacturer": "ACME",
            "IP Address": "1.1.1.1", "MAC Address": "AA:AA:AA",
            "IP / Analog": "IP",
        }])

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, site_number="S99", vendor_name="Site Owl Vendor") -> CorrectionSummary:
        cfg = _make_cfg(self._root)
        with _patch_ref(self._ref_df):
            return run_post_pass_correction(
                cfg=cfg,
                submission_id="sub-dirs",
                site_number=site_number,
                vendor_name=vendor_name,
                true_score=97.0,
                archived_file_path=self._vendor,
            )

    def test_corrected_file_goes_to_corrected_dir(self):
        result = self._run()
        self.assertIsNotNone(result)
        corrected_path = Path(result.corrected_csv_path)
        self.assertIn("CORRECTED", corrected_path.parts)
        self.assertTrue(corrected_path.exists())

    def test_log_file_goes_to_log_dir(self):
        result = self._run()
        log_path = Path(result.correction_log_path)
        self.assertIn("CORRECTION LOG", log_path.parts)
        self.assertTrue(log_path.exists())

    def test_raw_file_goes_to_raw_dir(self):
        result = self._run()
        raw_path = Path(result.raw_copy_path)
        self.assertIn("RAW", raw_path.parts)
        self.assertTrue(raw_path.exists())

    def test_filenames_contain_site_number(self):
        result = self._run(site_number="SITE123")
        for path_str in (
            result.corrected_csv_path,
            result.correction_log_path,
            result.raw_copy_path,
        ):
            self.assertIn("SITE123", Path(path_str).name)

    def test_filenames_contain_vendor_name(self):
        result = self._run(vendor_name="GlobalCam Inc")
        for path_str in (
            result.corrected_csv_path,
            result.correction_log_path,
            result.raw_copy_path,
        ):
            # Spaces are sanitized to underscores — check sanitized form
            self.assertIn("GlobalCam", Path(path_str).name)

    def test_raw_file_is_exact_copy_of_original(self):
        result = self._run()
        original_content = self._vendor.read_bytes()
        raw_content = Path(result.raw_copy_path).read_bytes()
        self.assertEqual(original_content, raw_content)

    def test_original_archived_file_unchanged(self):
        original_content = self._vendor.read_bytes()
        self._run()
        self.assertEqual(original_content, self._vendor.read_bytes())


# ---------------------------------------------------------------------------
# Schema preservation tests
# ---------------------------------------------------------------------------

class SchemaPreservationTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._root = Path(self._tmp.name)

        self._original_rows = [
            {
                "Project ID": "S2", "Plan ID": "P1",
                "Name": "CAM A", "Abbreviated Name": "A-WRONG",
                "Part Number": "PN1", "Manufacturer": "ACME",
                "IP Address": "1.1.1.1", "MAC Address": "AA:AA:AA",
                "IP / Analog": "IP", "Description": "Desc",
                "VendorExtra1": "val1", "VendorExtra2": "val2",
            },
            {
                "Project ID": "S2", "Plan ID": "P1",
                "Name": "CAM B", "Abbreviated Name": "B",
                "Part Number": "PN2", "Manufacturer": "ACME",
                "IP Address": "1.1.1.2", "MAC Address": "BB:BB:BB",
                "IP / Analog": "IP", "Description": "Desc2",
                "VendorExtra1": "val3", "VendorExtra2": "val4",
            },
        ]
        self._vendor = self._root / "submission.csv"
        _write_csv(self._vendor, self._original_rows)

        self._ref_df = pd.DataFrame([
            {
                "Name": "CAM A", "Abbreviated Name": "A-CORRECT",
                "Part Number": "PN1", "Manufacturer": "ACME",
                "IP Address": "1.1.1.1", "MAC Address": "AA:AA:AA",
                "IP / Analog": "IP",
            },
            {
                "Name": "CAM B", "Abbreviated Name": "B",
                "Part Number": "PN2", "Manufacturer": "ACME",
                "IP Address": "1.1.1.2", "MAC Address": "BB:BB:BB",
                "IP / Analog": "IP",
            },
        ])

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self) -> CorrectionSummary:
        cfg = _make_cfg(self._root)
        with _patch_ref(self._ref_df):
            return run_post_pass_correction(
                cfg=cfg,
                submission_id="sub-schema",
                site_number="S2",
                vendor_name="ACME Corp",
                true_score=97.0,
                archived_file_path=self._vendor,
            )

    def test_corrected_csv_same_columns_same_order(self):
        summary = self._run()
        corrected = pd.read_csv(summary.corrected_csv_path, dtype=str)
        expected_cols = list(pd.DataFrame(self._original_rows).columns)
        self.assertEqual(list(corrected.columns), expected_cols)

    def test_corrected_csv_same_row_count(self):
        summary = self._run()
        corrected = pd.read_csv(summary.corrected_csv_path, dtype=str)
        self.assertEqual(len(corrected), 2)

    def test_corrected_csv_same_row_order(self):
        summary = self._run()
        corrected = pd.read_csv(summary.corrected_csv_path, dtype=str)
        self.assertEqual(corrected.iloc[0]["Name"], "CAM A")
        self.assertEqual(corrected.iloc[1]["Name"], "CAM B")

    def test_corrected_csv_applies_correction_to_wrong_value(self):
        summary = self._run()
        corrected = pd.read_csv(summary.corrected_csv_path, dtype=str)
        # Row 0: MAC match → "A-WRONG" corrected to "A-CORRECT"
        self.assertEqual(corrected.iloc[0]["Abbreviated Name"], "A-CORRECT")

    def test_corrected_csv_leaves_correct_values_untouched(self):
        summary = self._run()
        corrected = pd.read_csv(summary.corrected_csv_path, dtype=str)
        self.assertEqual(corrected.iloc[1]["Abbreviated Name"], "B")

    def test_corrected_csv_preserves_extra_vendor_columns(self):
        summary = self._run()
        corrected = pd.read_csv(summary.corrected_csv_path, dtype=str)
        self.assertIn("VendorExtra1", corrected.columns)
        self.assertIn("VendorExtra2", corrected.columns)
        self.assertEqual(corrected.iloc[0]["VendorExtra1"], "val1")
        self.assertEqual(corrected.iloc[1]["VendorExtra2"], "val4")

    def test_corrected_csv_has_no_audit_columns(self):
        """Audit columns belong only in the log — not the corrected CSV."""
        summary = self._run()
        corrected = pd.read_csv(summary.corrected_csv_path, dtype=str)
        forbidden = {
            "original_value", "corrected_value", "confidence",
            "reason", "source", "applied", "requires_review",
        }
        overlap = forbidden & set(corrected.columns)
        self.assertEqual(overlap, set(), f"Audit columns in corrected CSV: {overlap}")


# ---------------------------------------------------------------------------
# Correction log tests
# ---------------------------------------------------------------------------

class CorrectionLogTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._root = Path(self._tmp.name)
        self._vendor = self._root / "submission.csv"
        _write_csv(self._vendor, [
            {"Name": "CAM A", "Abbreviated Name": "WRONG",
             "MAC Address": "AA:AA:AA", "IP Address": "1.1.1.1",
             "Manufacturer": "ACME", "Part Number": "PN1"},
        ])
        self._ref_df = pd.DataFrame([{
            "Name": "CAM A", "Abbreviated Name": "CORRECT",
            "MAC Address": "AA:AA:AA", "IP Address": "1.1.1.1",
            "Manufacturer": "ACME", "Part Number": "PN1",
        }])

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self) -> CorrectionSummary:
        cfg = _make_cfg(self._root)
        with _patch_ref(self._ref_df):
            return run_post_pass_correction(
                cfg=cfg,
                submission_id="sub-log",
                site_number="SITE99",
                vendor_name="Cam Vendor LLC",
                true_score=98.0,
                archived_file_path=self._vendor,
            )

    def test_log_has_required_columns(self):
        summary = self._run()
        log_df = pd.read_csv(summary.correction_log_path, dtype=str)
        required = {
            "submission_id", "site_number", "vendor_name",
            "row_number", "field", "original_value", "corrected_value",
            "reason", "source", "confidence", "applied",
            "requires_review", "timestamp",
        }
        self.assertTrue(required.issubset(set(log_df.columns)))

    def test_log_site_number_populated(self):
        summary = self._run()
        log_df = pd.read_csv(summary.correction_log_path, dtype=str)
        if not log_df.empty:
            self.assertTrue((log_df["site_number"] == "SITE99").all())

    def test_log_vendor_name_populated(self):
        summary = self._run()
        log_df = pd.read_csv(summary.correction_log_path, dtype=str)
        if not log_df.empty:
            self.assertTrue((log_df["vendor_name"] == "Cam Vendor LLC").all())

    def test_log_records_original_and_corrected_values(self):
        summary = self._run()
        log_df = pd.read_csv(summary.correction_log_path, dtype=str)
        applied_rows = log_df[log_df["applied"] == "True"]
        self.assertFalse(applied_rows.empty)
        abbrev_rows = applied_rows[applied_rows["field"] == "Abbreviated Name"]
        self.assertFalse(abbrev_rows.empty)
        self.assertEqual(abbrev_rows.iloc[0]["original_value"], "WRONG")
        self.assertEqual(abbrev_rows.iloc[0]["corrected_value"], "CORRECT")

    def test_summary_matches_log(self):
        summary = self._run()
        log_df = pd.read_csv(summary.correction_log_path, dtype=str)
        applied_count = (log_df["applied"] == "True").sum()
        self.assertEqual(summary.total_corrections, applied_count)


# ---------------------------------------------------------------------------
# Confidence threshold tests
# ---------------------------------------------------------------------------

class ConfidenceThresholdTests(unittest.TestCase):

    def _sub(self, **kw) -> pd.Series:
        d = {"Name": "CAM X", "Abbreviated Name": "WRONG",
             "Part Number": "PN1", "Manufacturer": "ACME",
             "IP Address": "1.2.3.4", "MAC Address": "XX:XX:XX"}
        d.update(kw)
        return pd.Series(d)

    def _ref(self, **kw) -> pd.Series:
        d = {"Name": "CAM X", "Abbreviated Name": "CORRECT",
             "Part Number": "PN1", "Manufacturer": "ACME",
             "IP Address": "1.2.3.4", "MAC Address": "XX:XX:XX"}
        d.update(kw)
        return pd.Series(d)

    def test_conf_ge_099_applied_no_review(self):
        """confidence >= 0.99 → applied=True, requires_review=False."""
        attempts = _build_correction_attempts(
            submission_id="s", row_number=1,
            sub_row=self._sub(), ref_row=self._ref(),
            correctable_fields=("Abbreviated Name",),
            match_confidence=1.0, match_source="MAC", timestamp=_ts(),
        )
        self.assertTrue(all(a.applied for a in attempts))
        self.assertTrue(all(not a.requires_review for a in attempts))

    def test_conf_093_to_098_applied_with_review(self):
        """0.93 <= confidence < 0.99 → applied=True, requires_review=True."""
        attempts = _build_correction_attempts(
            submission_id="s", row_number=1,
            sub_row=self._sub(), ref_row=self._ref(),
            correctable_fields=("Abbreviated Name",),
            match_confidence=0.95, match_source="fuzzy", timestamp=_ts(),
        )
        self.assertTrue(all(a.applied for a in attempts))
        self.assertTrue(all(a.requires_review for a in attempts))

    def test_conf_080_to_092_log_only_not_applied(self):
        """0.80 <= confidence < 0.93 → applied=False, requires_review=True."""
        attempts = _build_correction_attempts(
            submission_id="s", row_number=1,
            sub_row=self._sub(), ref_row=self._ref(),
            correctable_fields=("Abbreviated Name",),
            match_confidence=0.85, match_source="fuzzy", timestamp=_ts(),
        )
        self.assertTrue(all(not a.applied for a in attempts))
        self.assertTrue(all(a.requires_review for a in attempts))

    def test_conf_below_080_match_rejected(self):
        """confidence < 0.80 → _match_row_to_reference returns confidence below threshold."""
        ref_df = pd.DataFrame([{"Name": "ZZZZZZZZZZZZ", "MAC Address": "", "IP Address": ""}])
        sub = pd.Series({"Name": "AAAA", "MAC Address": "", "IP Address": ""})
        _, confidence, _ = _match_row_to_reference(sub, ref_df)
        self.assertLess(confidence, CONF_LOG_ONLY)

    def test_no_correction_when_ref_blank(self):
        """Reference blank → never invent a correction."""
        attempts = _build_correction_attempts(
            submission_id="s", row_number=1,
            sub_row=self._sub(**{"Abbreviated Name": "SOMETHING"}),
            ref_row=self._ref(**{"Abbreviated Name": ""}),
            correctable_fields=("Abbreviated Name",),
            match_confidence=1.0, match_source="MAC", timestamp=_ts(),
        )
        self.assertEqual(len(attempts), 0)

    def test_no_correction_when_values_match(self):
        """Values already agree → no attempt generated."""
        attempts = _build_correction_attempts(
            submission_id="s", row_number=1,
            sub_row=self._sub(**{"Abbreviated Name": "CORRECT"}),
            ref_row=self._ref(**{"Abbreviated Name": "CORRECT"}),
            correctable_fields=("Abbreviated Name",),
            match_confidence=1.0, match_source="MAC", timestamp=_ts(),
        )
        self.assertEqual(len(attempts), 0)

    def test_fuzzy_match_does_not_fill_blank_sub_field(self):
        """Fuzzy match (confidence < 0.99) must not fill a blank submission field."""
        attempts = _build_correction_attempts(
            submission_id="s", row_number=1,
            sub_row=self._sub(**{"Abbreviated Name": ""}),
            ref_row=self._ref(**{"Abbreviated Name": "CORRECT"}),
            correctable_fields=("Abbreviated Name",),
            match_confidence=0.90, match_source="fuzzy", timestamp=_ts(),
        )
        # blank sub + fuzzy match → no correction
        self.assertEqual(len(attempts), 0)

    def test_identity_match_fills_blank_sub_field(self):
        """MAC/IP match (confidence >= 0.99) may fill a blank submission field."""
        attempts = _build_correction_attempts(
            submission_id="s", row_number=1,
            sub_row=self._sub(**{"Abbreviated Name": ""}),
            ref_row=self._ref(**{"Abbreviated Name": "CORRECT"}),
            correctable_fields=("Abbreviated Name",),
            match_confidence=1.0, match_source="exact MAC", timestamp=_ts(),
        )
        applied = [a for a in attempts if a.applied]
        self.assertEqual(len(applied), 1)
        self.assertEqual(applied[0].corrected_value, "CORRECT")


# ---------------------------------------------------------------------------
# Row matching tests
# ---------------------------------------------------------------------------

class RowMatchingTests(unittest.TestCase):

    def _ref(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"Name": "CAM A", "MAC Address": "AA:AA:AA", "IP Address": "1.1.1.1",
             "Abbreviated Name": "A", "Manufacturer": "ACME", "Part Number": "PN1"},
            {"Name": "CAM B", "MAC Address": "BB:BB:BB", "IP Address": "1.1.1.2",
             "Abbreviated Name": "B", "Manufacturer": "ACME", "Part Number": "PN2"},
        ])

    def test_mac_match_confidence_is_1(self):
        sub = pd.Series({"Name": "OTHER", "MAC Address": "AA:AA:AA", "IP Address": ""})
        _, conf, src = _match_row_to_reference(sub, self._ref())
        self.assertEqual(conf, 1.0)
        self.assertIn("MAC", src)

    def test_ip_match_confidence_is_099(self):
        sub = pd.Series({"Name": "OTHER", "MAC Address": "", "IP Address": "1.1.1.2"})
        _, conf, src = _match_row_to_reference(sub, self._ref())
        self.assertEqual(conf, 0.99)
        self.assertIn("IP", src)

    def test_mac_takes_priority_over_ip(self):
        """MAC match wins even when IP would also match a different row."""
        sub = pd.Series({"Name": "X", "MAC Address": "AA:AA:AA", "IP Address": "1.1.1.2"})
        _, conf, src = _match_row_to_reference(sub, self._ref())
        self.assertEqual(conf, 1.0)
        self.assertIn("MAC", src)

    def test_fuzzy_name_match_above_threshold(self):
        sub = pd.Series({"Name": "CAM A", "MAC Address": "", "IP Address": ""})
        ref, conf, _ = _match_row_to_reference(sub, self._ref())
        self.assertIsNotNone(ref)
        self.assertGreaterEqual(conf, CONF_LOG_ONLY)

    def test_no_match_for_completely_different_name(self):
        sub = pd.Series({"Name": "ZZZZZZZZZZ", "MAC Address": "FF:FF:FF", "IP Address": "9.9.9.9"})
        ref_df = pd.DataFrame([
            {"Name": "CAM A", "MAC Address": "AA:AA:AA", "IP Address": "1.1.1.1"},
        ])
        _, conf, _ = _match_row_to_reference(sub, ref_df)
        # MAC/IP don't match; name similarity should be below threshold
        self.assertLess(conf, CONF_LOG_ONLY)


# ---------------------------------------------------------------------------
# Correctable fields resolution
# ---------------------------------------------------------------------------

class CorrectableFieldsTests(unittest.TestCase):

    def test_only_allowed_fields_returned(self):
        sub_df = pd.DataFrame(columns=["Name", "Manufacturer", "Random Column"])
        ref_df = pd.DataFrame(columns=["Name", "Manufacturer", "Random Column"])
        fields = _resolve_correctable_fields(sub_df, ref_df)
        self.assertIn("Name", fields)
        self.assertIn("Manufacturer", fields)
        self.assertNotIn("Random Column", fields)

    def test_field_missing_from_ref_excluded(self):
        sub_df = pd.DataFrame(columns=["Name", "Part Number"])
        ref_df = pd.DataFrame(columns=["Name"])
        fields = _resolve_correctable_fields(sub_df, ref_df)
        self.assertIn("Name", fields)
        self.assertNotIn("Part Number", fields)

    def test_empty_when_no_overlap_in_allowed_set(self):
        sub_df = pd.DataFrame(columns=["VendorOnlyCol"])
        ref_df = pd.DataFrame(columns=["RefOnlyCol"])
        self.assertEqual(_resolve_correctable_fields(sub_df, ref_df), ())


# ---------------------------------------------------------------------------
# Apply corrections integrity
# ---------------------------------------------------------------------------

class ApplyCorrectionsTests(unittest.TestCase):

    def _df(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"Name": "A", "Abbreviated Name": "WRONG", "Extra": "keep"},
            {"Name": "B", "Abbreviated Name": "OK",    "Extra": "also"},
        ])

    def test_only_targeted_cell_changes(self):
        df = self._df()
        attempt = CorrectionAttempt(
            submission_id="s", row_number=1, field="Abbreviated Name",
            original_value="WRONG", corrected_value="RIGHT",
            reason="test", source="test", confidence=1.0,
            applied=True, requires_review=False, timestamp=_ts(),
        )
        result = _apply_corrections(df.copy(), [attempt])
        self.assertEqual(result.iloc[0]["Abbreviated Name"], "RIGHT")
        self.assertEqual(result.iloc[0]["Name"], "A")
        self.assertEqual(result.iloc[0]["Extra"], "keep")
        self.assertEqual(result.iloc[1]["Abbreviated Name"], "OK")

    def test_row_count_unchanged(self):
        df = self._df()
        self.assertEqual(len(_apply_corrections(df.copy(), [])), 2)

    def test_column_order_unchanged(self):
        df = self._df()
        result = _apply_corrections(df.copy(), [])
        self.assertEqual(list(result.columns), list(df.columns))

    def test_out_of_range_row_skipped_gracefully(self):
        df = self._df()
        attempt = CorrectionAttempt(
            submission_id="s", row_number=999, field="Name",
            original_value="X", corrected_value="Y",
            reason="t", source="t", confidence=1.0,
            applied=True, requires_review=False, timestamp=_ts(),
        )
        result = _apply_corrections(df.copy(), [attempt])
        self.assertEqual(list(result["Name"]), ["A", "B"])


# ---------------------------------------------------------------------------
# Filename sanitization
# ---------------------------------------------------------------------------

class SafeFilenameTests(unittest.TestCase):

    def test_spaces_become_underscores(self):
        self.assertNotIn(" ", _safe_filename("hello world"))

    def test_slashes_sanitized(self):
        result = _safe_filename("site/123\\vendor")
        self.assertNotIn("/", result)
        self.assertNotIn("\\", result)

    def test_colon_sanitized(self):
        self.assertNotIn(":", _safe_filename("S1:Vendor"))

    def test_normal_text_preserved(self):
        result = _safe_filename("S99_ACME_Corp")
        self.assertIn("S99", result)
        self.assertIn("ACME", result)

    def test_max_length_respected(self):
        long_str = "A" * 200
        self.assertLessEqual(len(_safe_filename(long_str)), 80)


if __name__ == "__main__":
    unittest.main()
