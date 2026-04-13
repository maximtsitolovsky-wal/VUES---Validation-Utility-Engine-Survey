"""Site-indexed submission validation.

The site number from Airtable is the authoritative anchor.
We validate a submission against the reference profile for that site before
Python grading runs so schema errors and structural mismatches are not
misreported as ordinary FAIL scores.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from siteowlqa.config import AppConfig
from siteowlqa.file_processor import VendorFileLoadResult
from siteowlqa.reference_data import SiteReferenceProfile, fetch_site_reference_profile

CRITICAL_VENDOR_COLUMNS: tuple[str, ...] = (
    "Name",
    "Part Number",
    "Manufacturer",
    "IP Address",
    "MAC Address",
    "IP / Analog",
)

OPTIONAL_VENDOR_COLUMNS: tuple[str, ...] = (
    "Abbreviated Name",
    "Description",
)


@dataclass(frozen=True)
class SiteValidationResult:
    site_number: str
    status: str
    reason_codes: list[str] = field(default_factory=list)
    missing_critical_columns: list[str] = field(default_factory=list)
    missing_optional_columns: list[str] = field(default_factory=list)
    extra_columns: list[str] = field(default_factory=list)
    normalized_row_count: int = 0
    reference_row_count: int = 0

    @property
    def is_valid_for_grading(self) -> bool:
        return self.status == "VALID"


def validate_submission_for_site(
    cfg: AppConfig,
    site_number: str,
    load_result: VendorFileLoadResult,
) -> SiteValidationResult:
    profile = fetch_site_reference_profile(cfg, site_number)
    missing_critical = [
        col for col in CRITICAL_VENDOR_COLUMNS
        if col in load_result.missing_required_columns
    ]
    missing_optional = [
        col for col in OPTIONAL_VENDOR_COLUMNS
        if col in load_result.missing_required_columns
    ]

    reason_codes: list[str] = []
    status = "VALID"

    if not profile.has_reference_rows:
        status = "ERROR"
        reason_codes.append("SITE_REFERENCE_NOT_FOUND")

    if missing_critical:
        status = "ERROR"
        reason_codes.append("MISSING_CRITICAL_COLUMNS")

    if load_result.dataframe.empty:
        status = "ERROR"
        reason_codes.append("NO_NORMALIZED_ROWS")

    normalized_row_count = len(load_result.dataframe)
    if profile.has_reference_rows and normalized_row_count != profile.reference_row_count:
        # Diagnostic only.
        # Row-count mismatch is useful evidence, but it is not by itself proof
        # that the submission is invalid. SiteNumber scopes the comparison set;
        # the Python grader should still decide whether the submitted rows for
        # that site PASS or FAIL against the site reference data.
        reason_codes.append("ROW_COUNT_MISMATCH")

    for col in missing_optional:
        if profile.optional_fields_populated.get(col, False):
            reason_codes.append(f"OPTIONAL_COLUMN_MISSING_BUT_USED_BY_REFERENCE:{col}")

    if status == "VALID" and not reason_codes:
        reason_codes.append("SITE_INDEXED_VALIDATION_OK")

    return SiteValidationResult(
        site_number=site_number,
        status=status,
        reason_codes=reason_codes,
        missing_critical_columns=missing_critical,
        missing_optional_columns=missing_optional,
        extra_columns=load_result.extra_columns,
        normalized_row_count=normalized_row_count,
        reference_row_count=profile.reference_row_count,
    )
