"""models.py — Shared data models for SiteOwlQA pipeline.

All domain objects live here. This is the single source of truth
for what a submission, review, lesson, or result looks like.
No business logic here — just typed containers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ProcessingStatus(str, Enum):
    NEW = "NEW"
    QUEUED = "QUEUED"          # accepted, sitting in local queue
    PROCESSING = "PROCESSING"  # worker has picked it up
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"


class ReviewStatus(str, Enum):
    APPROVED = "APPROVED"
    APPROVED_WITH_WARNINGS = "APPROVED_WITH_WARNINGS"
    REJECTED = "REJECTED"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IssueSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Submission models
# ---------------------------------------------------------------------------

@dataclass
class AirtableRecord:
    """Parsed Airtable record for one vendor submission."""
    record_id: str
    submission_id: str
    vendor_email: str
    vendor_name: str           # from field or derived from email domain
    site_number: str
    attachment_url: str
    attachment_filename: str
    processing_status: str     # raw string from Airtable field
    submitted_at: str          # ISO string or empty
    team_key: str = "survey"


@dataclass
class SubmissionResult:
    """Result read back from dbo.SubmissionLog after grading."""
    submission_id: str
    status: ProcessingStatus
    score: float | None
    message: str
    graded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Review models
# ---------------------------------------------------------------------------

@dataclass
class ReviewIssue:
    severity: IssueSeverity
    issue_type: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity.value,
            "type": self.issue_type,
            "detail": self.detail,
        }


@dataclass
class ReviewResult:
    """Structured output from the internal code reviewer."""
    status: ReviewStatus
    risk_level: RiskLevel
    summary: str
    issues: list[ReviewIssue] = field(default_factory=list)
    recommended_fixes: list[str] = field(default_factory=list)
    reviewed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "risk_level": self.risk_level.value,
            "summary": self.summary,
            "issues": [i.to_dict() for i in self.issues],
            "recommended_fixes": self.recommended_fixes,
            "reviewed_at": self.reviewed_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# Submission Archive models  (new in Stage 2)
# ---------------------------------------------------------------------------

@dataclass
class SubmissionArchiveRecord:
    """Complete archival record for one vendor submission.

    Stored in archive/submissions/YYYY/MM/DD/<submission_id>.json
    and accumulated in submission_history.csv via metrics.py.
    """
    record_id: str                    # Airtable record ID
    submission_id: str                # from Airtable Submission ID field
    vendor_email: str
    vendor_name: str                  # derived if not in Airtable
    site_number: str
    attachment_filename: str          # original uploaded filename
    archived_file_path: str           # local path of copied raw file
    submitted_at: str                 # ISO timestamp from Airtable / now
    processed_at: str                 # ISO timestamp when pipeline ran
    status: str                       # PASS / FAIL / ERROR
    score: float | None               # grading score (None on ERROR)
    error_count: int                  # rows in QAResults on FAIL
    output_report_path: str           # path to QA_Errors CSV (FAIL only)
    sql_project_key: str              # ProjectID used in SQL (= site_number)
    execution_id: str                 # cross-reference to execution archive
    notes: str                        # error message or empty
    team_key: str = "survey"

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "submission_id": self.submission_id,
            "vendor_email": self.vendor_email,
            "vendor_name": self.vendor_name,
            "site_number": self.site_number,
            "attachment_filename": self.attachment_filename,
            "archived_file_path": self.archived_file_path,
            "submitted_at": self.submitted_at,
            "processed_at": self.processed_at,
            "status": self.status,
            "score": self.score,
            "error_count": self.error_count,
            "output_report_path": self.output_report_path,
            "sql_project_key": self.sql_project_key,
            "execution_id": self.execution_id,
            "notes": self.notes,
            "team_key": self.team_key,
        }


@dataclass
class VendorMetric:
    """Aggregated per-vendor performance metrics."""
    vendor_email: str
    vendor_name: str
    total_submissions: int
    total_pass: int
    total_fail: int
    total_error: int
    pass_rate_pct: float
    fail_rate_pct: float
    avg_score_on_fail: float | None
    latest_submission_at: str
    avg_turnaround_seconds: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "vendor_email": self.vendor_email,
            "vendor_name": self.vendor_name,
            "total_submissions": self.total_submissions,
            "total_pass": self.total_pass,
            "total_fail": self.total_fail,
            "total_error": self.total_error,
            "pass_rate_pct": round(self.pass_rate_pct, 2),
            "fail_rate_pct": round(self.fail_rate_pct, 2),
            "avg_score_on_fail": (
                round(self.avg_score_on_fail, 2)
                if self.avg_score_on_fail is not None else None
            ),
            "latest_submission_at": self.latest_submission_at,
            "avg_turnaround_seconds": (
                round(self.avg_turnaround_seconds, 1)
                if self.avg_turnaround_seconds is not None else None
            ),
        }


# ---------------------------------------------------------------------------
# Archive / Memory models
# ---------------------------------------------------------------------------

@dataclass
class Lesson:
    """A single learned lesson extracted from a failure or review."""
    lesson_id: str
    task_category: str
    failed_pattern: str
    root_cause: str
    fix_pattern: str
    generalized_rule: str
    confidence: float
    tags: list[str]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "lesson_id": self.lesson_id,
            "task_category": self.task_category,
            "failed_pattern": self.failed_pattern,
            "root_cause": self.root_cause,
            "fix_pattern": self.fix_pattern,
            "generalized_rule": self.generalized_rule,
            "confidence": self.confidence,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ExecutionRecord:
    """Archive entry for one pipeline run."""
    execution_id: str
    submission_id: str
    record_id: str
    vendor_email: str
    site_number: str
    status: ProcessingStatus
    score: float | None
    error_message: str
    rows_loaded: int
    duration_seconds: float
    team_key: str = "survey"
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "submission_id": self.submission_id,
            "record_id": self.record_id,
            "vendor_email": self.vendor_email,
            "site_number": self.site_number,
            "status": self.status.value,
            "score": self.score,
            "error_message": self.error_message,
            "rows_loaded": self.rows_loaded,
            "duration_seconds": round(self.duration_seconds, 3),
            "team_key": self.team_key,
            "executed_at": self.executed_at.isoformat(),
        }
