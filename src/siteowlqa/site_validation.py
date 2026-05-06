"""Site-indexed submission validation.

The site number from Airtable is the authoritative anchor.
We validate a submission against the reference profile for that site before
Python grading runs so schema errors and structural mismatches are not
misreported as ordinary FAIL scores.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from siteowlqa.config import (
    AppConfig,
    get_grade_columns_for_survey_type,
    get_base_grade_columns,
    SURVEY_TYPE_CCTV,
    SURVEY_TYPE_FA_INTRUSION,
    SURVEY_TYPE_BOTH,
)
from siteowlqa.file_processor import VendorFileLoadResult
from siteowlqa.reference_data import SiteReferenceProfile, fetch_site_reference_profile

# ---------------------------------------------------------------------------
# Critical columns per survey type (must be present in file)
# NOTE: Name is NOT critical because it's checked PER-ROW conditionally.
#       - CCTV: Name checked only if row has MAC Address
#       - FA/Intrusion: Name checked only if row has Abbreviated Name
# ---------------------------------------------------------------------------

# CCTV base columns (always required, Name is per-row conditional)
CRITICAL_VENDOR_COLUMNS_CCTV: tuple[str, ...] = (
    "Part Number",
    "Manufacturer",
    "IP Address",
    "MAC Address",
    "IP / Analog",
)

# FA/Intrusion base columns (always required, Name is per-row conditional)
CRITICAL_VENDOR_COLUMNS_FA_INTRUSION: tuple[str, ...] = (
    "Abbreviated Name",
    "Description",
)

# Backward compat alias
CRITICAL_VENDOR_COLUMNS: tuple[str, ...] = CRITICAL_VENDOR_COLUMNS_CCTV

# Name is always optional at the file level (checked per-row in grader)
OPTIONAL_VENDOR_COLUMNS: tuple[str, ...] = (
    "Name",
    "Abbreviated Name",
    "Description",
)


def _get_critical_columns_for_survey_type(survey_type: str | None) -> tuple[str, ...]:
    """Return critical columns that MUST be present for a given survey type.
    
    NOTE: Name is NOT included because it's checked per-row conditionally in the grader.
    
    For CCTV: Part Number, Manufacturer, IP Address, MAC Address, IP / Analog
    For FA/Intrusion: Abbreviated Name, Description
    For BOTH or None: All base columns (union)
    """
    if survey_type == SURVEY_TYPE_CCTV:
        return CRITICAL_VENDOR_COLUMNS_CCTV
    elif survey_type == SURVEY_TYPE_FA_INTRUSION:
        return CRITICAL_VENDOR_COLUMNS_FA_INTRUSION
    else:
        # BOTH or None — need all base columns
        return CRITICAL_VENDOR_COLUMNS_CCTV + CRITICAL_VENDOR_COLUMNS_FA_INTRUSION


def _get_optional_columns_for_survey_type(survey_type: str | None) -> tuple[str, ...]:
    """Return optional columns for a given survey type.
    
    Name is always optional at file level (per-row conditional in grader).
    
    For CCTV: Name, Abbreviated Name, Description are optional
    For FA/Intrusion: Name, CCTV columns are optional
    For BOTH or None: Only Name is optional
    """
    if survey_type == SURVEY_TYPE_CCTV:
        return ("Name", "Abbreviated Name", "Description")
    elif survey_type == SURVEY_TYPE_FA_INTRUSION:
        return ("Name", "Part Number", "Manufacturer", "IP Address", "MAC Address", "IP / Analog")
    else:
        # BOTH or None — only Name is optional
        return ("Name",)


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
    survey_type: str | None = None,
) -> SiteValidationResult:
    """Validate a submission against the reference profile for a site.
    
    Args:
        cfg: Application config.
        site_number: The site number (from Airtable).
        load_result: The loaded vendor file result.
        survey_type: One of 'CCTV', 'FA/Intrusion', 'BOTH', or None.
                     Determines which columns are critical vs optional.
    """
    profile = fetch_site_reference_profile(cfg, site_number, survey_type=survey_type)
    
    # Get critical/optional columns based on survey type
    critical_columns = _get_critical_columns_for_survey_type(survey_type)
    optional_columns = _get_optional_columns_for_survey_type(survey_type)
    
    missing_critical = [
        col for col in critical_columns
        if col in load_result.missing_required_columns
    ]
    missing_optional = [
        col for col in optional_columns
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
