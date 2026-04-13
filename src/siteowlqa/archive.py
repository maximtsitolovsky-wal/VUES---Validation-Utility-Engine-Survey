"""archive.py — Structured archive for pipeline runs, reviews, lessons, and submissions.

Categories:
    archive/executions/            — one JSON per pipeline run
    archive/reviews/               — one JSON per reviewer output
    archive/lessons/               — extracted lessons from failures
    archive/prompts/               — prompt snapshots
    archive/code/                  — code snapshots
    archive/submissions/YYYY/MM/DD/ — raw vendor files + metadata JSON

Design: append-only. Nothing is deleted. Memory (memory.py) searches these files.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from siteowlqa.models import ExecutionRecord, Lesson, ReviewResult, SubmissionArchiveRecord


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SubmissionArchiveResult:
    """Return value from save_submission_archive().

    Carries both the metadata JSON path and the archived raw-file path so
    callers can surface the file location without re-deriving it.
    ``archived_file_path`` is None when no raw file was provided or the copy
    failed — callers must handle that case.
    """
    metadata_path: Path
    archived_file_path: Path | None

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Archive writer
# ---------------------------------------------------------------------------

class Archive:
    """Append-only JSON archive for the QA pipeline."""

    def __init__(self, archive_dir: Path) -> None:
        self._root = archive_dir
        self._executions_dir = archive_dir / "executions"
        self._reviews_dir = archive_dir / "reviews"
        self._lessons_dir = archive_dir / "lessons"
        self._prompts_dir = archive_dir / "prompts"
        self._code_dir = archive_dir / "code"
        self._submissions_dir = archive_dir / "submissions"

        for d in [
            self._executions_dir,
            self._reviews_dir,
            self._lessons_dir,
            self._prompts_dir,
            self._code_dir,
            self._submissions_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Writers
    # ------------------------------------------------------------------

    def save_execution(self, record: ExecutionRecord) -> Path:
        """Save an execution record to archive/executions/."""
        path = self._executions_dir / f"{record.execution_id}.json"
        _write_json(path, record.to_dict())
        log.info("Archived execution: %s", path.name)
        return path

    def save_review(self, execution_id: str, result: ReviewResult) -> Path:
        """Save a reviewer output to archive/reviews/."""
        filename = f"{execution_id}_review.json"
        path = self._reviews_dir / filename
        data = result.to_dict()
        data["execution_id"] = execution_id
        _write_json(path, data)
        log.info("Archived review: %s", path.name)
        return path

    def save_lesson(self, lesson: Lesson) -> Path:
        """Save a learned lesson to archive/lessons/."""
        path = self._lessons_dir / f"{lesson.lesson_id}.json"
        _write_json(path, lesson.to_dict())
        log.info("Archived lesson: %s", lesson.lesson_id)
        return path

    def save_prompt_snapshot(self, name: str, content: str) -> Path:
        """Save a prompt snapshot to archive/prompts/."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = self._prompts_dir / f"{ts}_{name}.md"
        path.write_text(content, encoding="utf-8")
        log.info("Archived prompt snapshot: %s", path.name)
        return path

    def save_code_snapshot(
        self, module_name: str, source_code: str
    ) -> Path:
        """Save a code snapshot to archive/code/."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_name = module_name.replace("/", "_").replace("\\", "_")
        path = self._code_dir / f"{ts}_{safe_name}"
        path.write_text(source_code, encoding="utf-8")
        log.info("Archived code snapshot: %s", path.name)
        return path

    def save_submission_archive(
        self,
        record: SubmissionArchiveRecord,
        raw_file_path: Path | None = None,
    ) -> SubmissionArchiveResult:
        """Archive a submission's metadata JSON and optionally copy the raw file.

        Files are stored under archive/submissions/YYYY/MM/DD/
        so the archive is naturally partitioned by date.

        Args:
            record:        The SubmissionArchiveRecord to persist.
            raw_file_path: Local path to the downloaded vendor file.
                           If provided, the file is copied into the date folder
                           so it is preserved independently of temp/ cleanup.

        Returns:
            Path to the saved metadata JSON file.
        """
        today = datetime.now(timezone.utc)
        date_dir = (
            self._submissions_dir
            / str(today.year)
            / f"{today.month:02d}"
            / f"{today.day:02d}"
        )
        date_dir.mkdir(parents=True, exist_ok=True)

        # Copy raw vendor file into the date folder
        archived_file_path_str = record.archived_file_path
        archived_file_dest: Path | None = None
        if raw_file_path and raw_file_path.exists():
            dest_file = date_dir / raw_file_path.name
            shutil.copy2(raw_file_path, dest_file)
            archived_file_path_str = str(dest_file)
            archived_file_dest = dest_file
            log.info("Raw file archived: %s", dest_file)

        # Save metadata JSON
        safe_id = record.submission_id.replace("/", "-").replace("\\", "-")
        meta_path = date_dir / f"{safe_id}_meta.json"
        data = record.to_dict()
        data["archived_file_path"] = archived_file_path_str
        _write_json(meta_path, data)
        log.info("Submission metadata archived: %s", meta_path.name)
        return SubmissionArchiveResult(
            metadata_path=meta_path,
            archived_file_path=archived_file_dest,
        )

    # ------------------------------------------------------------------
    # Readers
    # ------------------------------------------------------------------

    def load_all_submission_records(self) -> list[dict[str, Any]]:
        """Load all archived submission metadata records (all dates).

        Used by metrics.py to build submission_history.csv.
        Returns list sorted by date folder order (oldest first).
        """
        results = []
        for meta_file in sorted(self._submissions_dir.rglob("*_meta.json")):
            data = _read_json(meta_file)
            if data:
                results.append(data)
        return results

    def count_submissions(self) -> int:
        """Return total number of archived submission records."""
        return len(list(self._submissions_dir.rglob("*_meta.json")))

    def find_archived_file_by_record_id(self, record_id: str) -> Path | None:
        """Scan submission metadata to find the archived vendor file for a record.

        Used by CorrectionWorker to locate the vendor file locally before
        falling back to a network re-download from Airtable.

        Scans newest date folders first (most recent submissions are most
        likely to be corrected) so the common case is fast.

        Returns the Path if the archived file exists on disk, else None.
        """
        meta_files = sorted(
            self._submissions_dir.rglob("*_meta.json"),
            reverse=True,   # newest first
        )
        for meta_file in meta_files:
            try:
                with open(meta_file, encoding="utf-8") as fh:
                    data = json.load(fh)
            except (json.JSONDecodeError, OSError):
                continue

            if str(data.get("record_id", "")) != record_id:
                continue

            archived_path_str = data.get("archived_file_path", "")
            if not archived_path_str:
                return None

            archived_path = Path(archived_path_str)
            if archived_path.exists():
                return archived_path

            log.warning(
                "Archive metadata found for record=%s but file is missing: %s",
                record_id, archived_path,
            )
            return None

        log.debug(
            "No archive metadata found for record=%s — "
            "may be a historical record pre-dating the archive.",
            record_id,
        )
        return None

    def load_all_lessons(self) -> list[dict[str, Any]]:
        """Load all archived lessons for memory retrieval."""
        return [
            _read_json(p)
            for p in sorted(self._lessons_dir.glob("*.json"))
        ]

    def load_all_executions(self) -> list[dict[str, Any]]:
        """Load all archived execution records."""
        return [
            _read_json(p)
            for p in sorted(self._executions_dir.glob("*.json"))
        ]

    def load_all_reviews(self) -> list[dict[str, Any]]:
        """Load all archived reviews."""
        return [
            _read_json(p)
            for p in sorted(self._reviews_dir.glob("*.json"))
        ]

    def count_lessons(self) -> int:
        """Return number of lessons archived so far."""
        return len(list(self._lessons_dir.glob("*.json")))


# ---------------------------------------------------------------------------
# Lesson factory
# ---------------------------------------------------------------------------

def extract_lesson_from_failure(
    archive: Archive,
    execution_id: str,
    task_category: str,
    failed_pattern: str,
    root_cause: str,
    fix_pattern: str,
    generalized_rule: str,
    tags: list[str],
    confidence: float = 0.8,
) -> Lesson:
    """Create and archive a new lesson from a pipeline failure.

    This is the primary way the system learns. Call this whenever a
    failure reveals a new pattern worth avoiding in the future.

    Args:
        archive:           The Archive instance to save the lesson to.
        execution_id:      The execution this lesson was extracted from.
        task_category:     Category like 'sql_import', 'file_parse', 'email'.
        failed_pattern:    What went wrong (observable symptom).
        root_cause:        Why it went wrong (root cause).
        fix_pattern:       What was done to fix it.
        generalized_rule:  The rule that should be applied in future.
        tags:              Searchable tags for memory retrieval.
        confidence:        How confident we are this generalises (0-1).

    Returns:
        The Lesson object (also saved to disk).
    """
    from utils import new_lesson_id  # avoid circular import

    lesson_id = new_lesson_id(archive.count_lessons())
    lesson = Lesson(
        lesson_id=lesson_id,
        task_category=task_category,
        failed_pattern=failed_pattern,
        root_cause=root_cause,
        fix_pattern=fix_pattern,
        generalized_rule=generalized_rule,
        confidence=confidence,
        tags=tags,
    )
    archive.save_lesson(lesson)
    log.info(
        "New lesson extracted: %s | category=%s | confidence=%.2f",
        lesson_id, task_category, confidence,
    )
    return lesson


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, data: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, default=str)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Failed to read archive file %s: %s", path.name, exc)
        return {}
