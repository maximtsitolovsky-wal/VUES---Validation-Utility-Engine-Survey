"""Audit grading consistency across archive metadata and output CSVs.

Checks hard invariants so grading/reporting bugs surface immediately:
- Score must be within 0..100 when present
- PASS implies normalized score >= 95
- FAIL implies normalized score < 95
- ERROR should not carry a score in archive/output
- output/submission_history.csv should match archived metadata records
- error_count should be 0 for PASS and non-negative for all rows

Usage:
    python audit_grading.py
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PASS_THRESHOLD = 95.0
ARCHIVE_DIR = Path("archive/submissions")
HISTORY_CSV = Path("output/submission_history.csv")


@dataclass(slots=True)
class Finding:
    severity: str
    source: str
    submission_id: str
    message: str

    def render(self) -> str:
        return (
            f"[{self.severity}] {self.source} | "
            f"submission={self.submission_id} | {self.message}"
        )


def main() -> None:
    archive_rows = load_archive_rows()
    history_rows = load_history_rows()

    findings: list[Finding] = []
    findings.extend(audit_archive_rows(archive_rows))
    findings.extend(audit_history_rows(history_rows))
    findings.extend(audit_cross_source_consistency(archive_rows, history_rows))

    print("=== Grading Audit ===")
    print(f"Archive rows: {len(archive_rows)}")
    print(f"History rows: {len(history_rows)}")
    print(f"Findings: {len(findings)}")
    print()

    if not findings:
        print("No findings. Miracles do happen.")
        return

    for finding in findings:
        print(finding.render())


def load_archive_rows() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    if not ARCHIVE_DIR.exists():
        return rows

    for path in sorted(ARCHIVE_DIR.rglob("*_meta.json")):
        with open(path, encoding="utf-8") as fh:
            row = json.load(fh)
        submission_id = str(row.get("submission_id") or "").strip()
        if submission_id:
            rows[submission_id] = row
    return rows


def load_history_rows() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    if not HISTORY_CSV.exists():
        return rows

    with open(HISTORY_CSV, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            submission_id = str(row.get("submission_id") or "").strip()
            if submission_id:
                rows[submission_id] = row
    return rows


def audit_archive_rows(rows: dict[str, dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    for submission_id, row in rows.items():
        findings.extend(audit_row("archive", submission_id, row))
    return findings


def audit_history_rows(rows: dict[str, dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    for submission_id, row in rows.items():
        findings.extend(audit_row("history", submission_id, row))
    return findings


def audit_cross_source_consistency(
    archive_rows: dict[str, dict[str, Any]],
    history_rows: dict[str, dict[str, Any]],
) -> list[Finding]:
    findings: list[Finding] = []

    archive_ids = set(archive_rows)
    history_ids = set(history_rows)

    for submission_id in sorted(archive_ids - history_ids):
        findings.append(Finding(
            severity="ERROR",
            source="cross-check",
            submission_id=submission_id,
            message="Present in archive but missing from submission_history.csv",
        ))

    for submission_id in sorted(history_ids - archive_ids):
        findings.append(Finding(
            severity="ERROR",
            source="cross-check",
            submission_id=submission_id,
            message="Present in submission_history.csv but missing from archive",
        ))

    for submission_id in sorted(archive_ids & history_ids):
        archive_row = archive_rows[submission_id]
        history_row = history_rows[submission_id]

        for field in ("status", "site_number", "error_count"):
            a = normalized_text(archive_row.get(field))
            h = normalized_text(history_row.get(field))
            if a != h:
                findings.append(Finding(
                    severity="ERROR",
                    source="cross-check",
                    submission_id=submission_id,
                    message=f"Field mismatch for {field}: archive={a!r} history={h!r}",
                ))

        a_score = normalized_score(archive_row.get("status"), archive_row.get("score"))
        h_score = normalized_score(history_row.get("status"), history_row.get("score"))
        if a_score != h_score:
            findings.append(Finding(
                severity="ERROR",
                source="cross-check",
                submission_id=submission_id,
                message=f"Normalized score mismatch: archive={a_score!r} history={h_score!r}",
            ))

    return findings


def audit_row(source: str, submission_id: str, row: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []

    status = normalized_text(row.get("status")).upper()
    score = normalized_score(status, row.get("score"))
    raw_score = row.get("score")
    error_count = normalized_int(row.get("error_count"))

    if status not in {"PASS", "FAIL", "ERROR"}:
        findings.append(Finding(
            severity="ERROR",
            source=source,
            submission_id=submission_id,
            message=f"Unknown status: {status!r}",
        ))
        return findings

    if error_count is None or error_count < 0:
        findings.append(Finding(
            severity="ERROR",
            source=source,
            submission_id=submission_id,
            message=f"Invalid error_count: {row.get('error_count')!r}",
        ))

    if score is not None and not (0.0 <= score <= 100.0):
        findings.append(Finding(
            severity="ERROR",
            source=source,
            submission_id=submission_id,
            message=f"Score out of range 0..100: raw={raw_score!r} normalized={score}",
        ))

    if status == "PASS":
        if score is None:
            findings.append(Finding(
                severity="WARN",
                source=source,
                submission_id=submission_id,
                message="PASS has no score; normalized reporting will assume 100.0",
            ))
        elif score < PASS_THRESHOLD:
            findings.append(Finding(
                severity="ERROR",
                source=source,
                submission_id=submission_id,
                message=f"PASS below threshold {PASS_THRESHOLD}: {score}",
            ))
        if error_count not in (0, None):
            findings.append(Finding(
                severity="ERROR",
                source=source,
                submission_id=submission_id,
                message=f"PASS should have error_count=0, got {error_count}",
            ))

    if status == "FAIL":
        if score is None:
            findings.append(Finding(
                severity="ERROR",
                source=source,
                submission_id=submission_id,
                message="FAIL is missing score",
            ))
        elif score >= PASS_THRESHOLD:
            findings.append(Finding(
                severity="ERROR",
                source=source,
                submission_id=submission_id,
                message=f"FAIL at/above threshold {PASS_THRESHOLD}: {score}",
            ))

    if status == "ERROR" and score is not None:
        findings.append(Finding(
            severity="ERROR",
            source=source,
            submission_id=submission_id,
            message=f"ERROR should not carry score, got raw={raw_score!r} normalized={score}",
        ))

    return findings


def normalized_score(status: Any, raw_score: Any) -> float | None:
    normalized_status = normalized_text(status).upper()
    raw_text = normalized_text(raw_score).upper()

    if normalized_status == "PASS" and raw_text in {"", "PASS"}:
        return 100.0
    if normalized_status == "ERROR":
        return None
    if raw_text == "":
        return None

    try:
        return round(float(raw_text), 2)
    except ValueError:
        return None


def normalized_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalized_int(value: Any) -> int | None:
    text = normalized_text(value)
    if text == "":
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


if __name__ == "__main__":
    main()
