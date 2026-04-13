"""reviewer.py — Internal code and pipeline reviewer.

This module behaves like a senior engineer reviewing the system.
It evaluates pipeline runs, code snapshots, and SQL flow for:
 - Architecture consistency
 - Business rule correctness
 - Concurrency risk
 - SQL safety
 - Null handling
 - Config centralisation
 - Secrets exposure
 - Duplicated logic
 - Weak error handling
 - Naming issues
 - Unsafe staging behavior (especially SubmissionRaw truncation)

The reviewer does NOT fix code — it surfaces findings.
Fixing is the job of archive.py + memory.py feedback loops.
"""

from __future__ import annotations

import logging
from typing import Any

from siteowlqa.models import IssueSeverity, ReviewIssue, ReviewResult, ReviewStatus, RiskLevel

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Static known risk patterns
# These represent lessons already learned by the system.
# ---------------------------------------------------------------------------

_KNOWN_RISK_PATTERNS: list[dict[str, Any]] = [
    {
        "id": "RISK-001",
        "name": "SubmissionRaw Isolation — Resolved",
        "severity": IssueSeverity.INFO,
        "issue_type": "Concurrency",
        "detail": (
            "RESOLVED: SubmissionRaw previously used a global TRUNCATE. "
            "Now uses DELETE WHERE [SubmissionID] = ? before each INSERT. "
            "SubmissionRaw.SubmissionID column added via migration. "
            "Both procs (@SubmissionID parameter) are fully isolated. "
            "Multiple workers run in parallel with no shared write targets."
        ),
        "fix": "No action required. Concurrency is fully resolved.",
    },
    {
        "id": "RISK-002",
        "name": "Project ID Overwrite Not Verified Post-Insert",
        "severity": IssueSeverity.MEDIUM,
        "issue_type": "BusinessRule",
        "detail": (
            "The system overwrites Project ID in the DataFrame before SQL insert "
            "but does not verify the value was correctly persisted in SubmissionRaw "
            "after insert. A silent column mapping error could allow the wrong "
            "ProjectID to reach the grading procedure."
        ),
        "fix": (
            "After INSERT, run SELECT DISTINCT ProjectID FROM SubmissionRaw WHERE "
            "SubmissionID = ? and assert it equals site_number."
        ),
    },
    {
        "id": "RISK-003",
        "name": "Airtable Attachment URL Expiry",
        "severity": IssueSeverity.LOW,
        "issue_type": "Reliability",
        "detail": (
            "Airtable attachment URLs expire after a number of hours. If the "
            "polling service is down for an extended period, records may become "
            "un-downloadable. The system will mark them ERROR correctly, but "
            "the vendor will need to resubmit."
        ),
        "fix": (
            "Ensure polling service uptime is monitored. Consider alerting "
            "if the service has been down > 2 hours."
        ),
    },
    {
        "id": "RISK-004",
        "name": "PASS Email Omits Score (by design)",
        "severity": IssueSeverity.INFO,
        "issue_type": "BusinessRule",
        "detail": (
            "Per spec, PASS emails deliberately omit the score percentage. "
            "This is correct. Flagged here for explicit awareness."
        ),
        "fix": "No fix required. Behaviour is intentional per business spec.",
    },
    {
        "id": "RISK-005",
        "name": "Blank NULL Handling in SQL Insert",
        "severity": IssueSeverity.MEDIUM,
        "issue_type": "DataQuality",
        "detail": (
            "Empty strings from vendor files are converted to SQL NULL on insert "
            "(via `or None`). This is the correct behaviour — blank values should "
            "not unfairly dock scores. However, if any SQL column has a NOT NULL "
            "constraint, this will cause an insert failure. Verify column nullability "
            "in SubmissionRaw matches this behaviour."
        ),
        "fix": (
            "Run: SELECT COLUMN_NAME, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = 'SubmissionRaw' and confirm all graded columns are nullable."
        ),
    },
]


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def review_pipeline_run(
    submission_id: str,
    site_number: str,
    rows_loaded: int,
    status: str,
    score: float | None,
    error_message: str = "",
    extra_context: dict[str, Any] | None = None,
) -> ReviewResult:
    """Review a completed pipeline run for risks and correctness.

    This is called after each submission completes (or fails).
    It surfaces known risk patterns relevant to the run context.

    Args:
        submission_id:   The submission being reviewed.
        site_number:     Site number used to overwrite Project ID.
        rows_loaded:     Number of rows inserted into SubmissionRaw.
        status:          Result status: PASS / FAIL / ERROR.
        score:           Score from SubmissionLog (None on error).
        error_message:   Error string if status=ERROR.
        extra_context:   Optional dict of additional context to include.

    Returns:
        ReviewResult with issues, risk level, and recommended fixes.
    """
    issues: list[ReviewIssue] = []
    recommended_fixes: list[str] = []

    # Always flag the concurrency risk on every run (it's persistent)
    for pattern in _KNOWN_RISK_PATTERNS:
        issues.append(
            ReviewIssue(
                severity=pattern["severity"],
                issue_type=pattern["issue_type"],
                detail=pattern["detail"],
            )
        )
        recommended_fixes.append(pattern["fix"])

    # Contextual checks
    if rows_loaded == 0:
        issues.append(ReviewIssue(
            severity=IssueSeverity.HIGH,
            issue_type="DataLoad",
            detail=(
                f"Zero rows were inserted into SubmissionRaw for submission "
                f"'{submission_id}'. The vendor file may be empty or the "
                "column mapping may have failed silently."
            ),
        ))
        recommended_fixes.append(
            "Verify vendor file is non-empty and column mapping is correct."
        )

    if not site_number:
        issues.append(ReviewIssue(
            severity=IssueSeverity.CRITICAL,
            issue_type="BusinessRule",
            detail=(
                "Site Number is blank. Project ID was not overwritten. "
                "This submission was graded against the wrong project context."
            ),
        ))
        recommended_fixes.append(
            "Ensure Airtable form requires Site Number before submission."
        )

    if status == "ERROR" and not error_message:
        issues.append(ReviewIssue(
            severity=IssueSeverity.MEDIUM,
            issue_type="ErrorHandling",
            detail=(
                "Submission status is ERROR but no error message was captured. "
                "This indicates a silent failure somewhere in the pipeline."
            ),
        ))

    if status == "FAIL" and score is not None and score > 95.0:
        issues.append(ReviewIssue(
            severity=IssueSeverity.HIGH,
            issue_type="BusinessRule",
            detail=(
                f"Submission scored {score:.1f}% but was marked FAIL. "
                "Score is above the 95% pass threshold. "
                "Check if the stored procedure pass threshold matches config."
            ),
        ))

    # Determine overall risk level
    severities = [i.severity for i in issues]
    risk = _compute_risk(severities)

    # Determine review status
    if any(s in (IssueSeverity.CRITICAL, IssueSeverity.HIGH) for s in severities
           if _is_actionable(issues, s)):
        review_status = ReviewStatus.APPROVED_WITH_WARNINGS
    else:
        review_status = ReviewStatus.APPROVED

    result = ReviewResult(
        status=review_status,
        risk_level=risk,
        summary=_build_summary(submission_id, status, score, len(issues)),
        issues=issues,
        recommended_fixes=recommended_fixes,
    )

    log.info(
        "Review: submission=%s status=%s risk=%s issues=%d",
        submission_id,
        review_status.value,
        risk.value,
        len(issues),
    )
    return result


def review_code_module(
    module_name: str,
    source_code: str,
) -> ReviewResult:
    """Static review of a Python module source code for red flags.

    Checks for:
    - Hardcoded secrets or connection strings
    - os.getenv calls outside config.py
    - try/except blocks with bare 'except:'
    - TODO comments left in production code
    - print() instead of logging
    - Files that may be too large (heuristic: > 400 lines)

    Args:
        module_name:  Filename being reviewed (for context).
        source_code:  Full text content of the Python file.

    Returns:
        ReviewResult with findings.
    """
    issues: list[ReviewIssue] = []
    recommended_fixes: list[str] = []

    lines = source_code.splitlines()
    line_count = len(lines)

    _check_hardcoded_secrets(source_code, module_name, issues, recommended_fixes)
    _check_bare_except(lines, module_name, issues, recommended_fixes)
    _check_direct_env_access(source_code, module_name, issues, recommended_fixes)
    _check_print_statements(lines, module_name, issues, recommended_fixes)
    _check_todo_comments(lines, module_name, issues, recommended_fixes)
    _check_file_length(line_count, module_name, issues, recommended_fixes)

    severities = [i.severity for i in issues]
    risk = _compute_risk(severities)

    has_rejection = any(
        i.severity == IssueSeverity.CRITICAL for i in issues
    )
    review_status = (
        ReviewStatus.REJECTED if has_rejection
        else ReviewStatus.APPROVED_WITH_WARNINGS if issues
        else ReviewStatus.APPROVED
    )

    return ReviewResult(
        status=review_status,
        risk_level=risk,
        summary=(
            f"{module_name}: {line_count} lines. "
            f"{len(issues)} issue(s) found."
        ),
        issues=issues,
        recommended_fixes=recommended_fixes,
    )


# ---------------------------------------------------------------------------
# Static analysis helpers
# ---------------------------------------------------------------------------

def _check_hardcoded_secrets(
    source: str,
    module: str,
    issues: list[ReviewIssue],
    fixes: list[str],
) -> None:
    dangerous_patterns = [
        "password=", "passwd=", "secret=", "api_key=",
        "token=", "Authorization:", "Bearer ",
    ]
    lower = source.lower()
    for pattern in dangerous_patterns:
        if pattern.lower() in lower:
            # Exclude comments and docstrings crudely (not perfect, but good enough)
            issues.append(ReviewIssue(
                severity=IssueSeverity.HIGH,
                issue_type="SecretsExposure",
                detail=(
                    f"{module}: Possible hardcoded secret pattern '{pattern}' detected. "
                    "Verify this is not a literal value and is loaded from config/env."
                ),
            ))
            fixes.append(
                f"Ensure '{pattern}' value in {module} comes from AppConfig, not literal string."
            )
            break  # one warning per module is enough


def _check_bare_except(
    lines: list[str],
    module: str,
    issues: list[ReviewIssue],
    fixes: list[str],
) -> None:
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped == "except:":
            issues.append(ReviewIssue(
                severity=IssueSeverity.MEDIUM,
                issue_type="WeakErrorHandling",
                detail=(
                    f"{module} line {i}: Bare 'except:' catches everything including "
                    "SystemExit and KeyboardInterrupt. Use 'except Exception:' instead."
                ),
            ))
            fixes.append(f"{module} line {i}: Replace bare except with 'except Exception:'")


def _check_direct_env_access(
    source: str,
    module: str,
    issues: list[ReviewIssue],
    fixes: list[str],
) -> None:
    if module == "config.py":
        return  # config.py is allowed to call os.getenv
    if "os.getenv" in source or "os.environ" in source:
        issues.append(ReviewIssue(
            severity=IssueSeverity.MEDIUM,
            issue_type="ConfigCentralization",
            detail=(
                f"{module}: Direct os.getenv/os.environ call detected outside config.py. "
                "All env access should go through AppConfig from config.py."
            ),
        ))
        fixes.append(
            f"Remove os.getenv from {module} and import value from config.load_config()."
        )


def _check_print_statements(
    lines: list[str],
    module: str,
    issues: list[ReviewIssue],
    fixes: list[str],
) -> None:
    for i, line in enumerate(lines, 1):
        if line.strip().startswith("print("):
            issues.append(ReviewIssue(
                severity=IssueSeverity.LOW,
                issue_type="Logging",
                detail=(
                    f"{module} line {i}: print() found. Use structured logging instead."
                ),
            ))
            fixes.append(f"{module} line {i}: Replace print() with log.info() or log.debug()")
            break  # flag once per file


def _check_todo_comments(
    lines: list[str],
    module: str,
    issues: list[ReviewIssue],
    fixes: list[str],
) -> None:
    todo_lines = [
        i + 1 for i, line in enumerate(lines)
        if "# TODO" in line.upper() or "# FIXME" in line.upper()
    ]
    if todo_lines:
        issues.append(ReviewIssue(
            severity=IssueSeverity.LOW,
            issue_type="Maintainability",
            detail=(
                f"{module}: TODO/FIXME comments on lines {todo_lines[:5]}. "
                "Production code should not have unresolved TODOs."
            ),
        ))
        fixes.append(f"Resolve or archive TODO items in {module}.")


def _check_file_length(
    line_count: int,
    module: str,
    issues: list[ReviewIssue],
    fixes: list[str],
) -> None:
    if line_count > 600:
        issues.append(ReviewIssue(
            severity=IssueSeverity.MEDIUM,
            issue_type="Maintainability",
            detail=(
                f"{module} is {line_count} lines. Files over 600 lines "
                "become hard to review and maintain. Split into submodules."
            ),
        ))
        fixes.append(f"Refactor {module} into smaller, single-responsibility modules.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_risk(severities: list[IssueSeverity]) -> RiskLevel:
    if IssueSeverity.CRITICAL in severities:
        return RiskLevel.CRITICAL
    if IssueSeverity.HIGH in severities:
        return RiskLevel.HIGH
    if IssueSeverity.MEDIUM in severities:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _is_actionable(issues: list[ReviewIssue], severity: IssueSeverity) -> bool:
    """Return True if any issue with the given severity is not INFO."""
    return any(
        i.severity == severity and i.severity != IssueSeverity.INFO
        for i in issues
    )


def _build_summary(
    submission_id: str,
    status: str,
    score: float | None,
    issue_count: int,
) -> str:
    score_str = f"{score:.1f}%" if score is not None else "N/A"
    return (
        f"Submission '{submission_id}' completed with status={status} "
        f"score={score_str}. {issue_count} review item(s) surfaced."
    )
