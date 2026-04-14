"""memory.py — Retrieval-based memory for the QA pipeline agent.

This is the learning layer. Before generating or modifying any code,
the system should consult memory to:
 - Find relevant past failures
 - Surface previously learned rules
 - Avoid repeating known bad patterns
 - Recommend patterns that have worked before

Design: retrieval-first, no neural network.
Simple keyword/tag matching against archived lessons and executions.
This is intentionally simple — good enough for a production ops system.

When the lesson library grows > 100 entries, consider upgrading to
embedding-based semantic search. Document that decision in the archive.
"""

from __future__ import annotations

import logging
from typing import Any

from siteowlqa.archive import Archive

log = logging.getLogger(__name__)


class Memory:
    """Retrieval-first memory backed by the Archive.

    Usage:
        memory = Memory(archive)
        context = memory.recall(tags=["sql", "import"], query="truncate staging")
        # context is a dict with relevant lessons, warnings, and past failures
    """

    def __init__(self, archive: Archive) -> None:
        self._archive = archive

    def recall(
        self,
        tags: list[str] | None = None,
        query: str = "",
        max_lessons: int = 5,
        max_failures: int = 3,
    ) -> dict[str, Any]:
        """Retrieve relevant lessons and past failures from memory.

        Matching is tag-based + keyword-based substring search.
        Most recently archived items rank first.

        Args:
            tags:          List of tags to match against lesson tags.
            query:         Keyword string to match in lesson text fields.
            max_lessons:   Max number of lessons to return.
            max_failures:  Max number of past failure executions to return.

        Returns:
            Dict with:
                lessons     — matched Lesson dicts
                failures    — matched failed ExecutionRecord dicts
                rules       — extracted generalized_rule strings
                summary     — human-readable memory context string
        """
        all_lessons = self._archive.load_all_lessons()
        all_executions = self._archive.load_all_executions()

        matched_lessons = _match_lessons(
            all_lessons, tags or [], query, max_lessons
        )
        past_failures = _get_failures(all_executions, max_failures)
        rules = [l.get("generalized_rule", "") for l in matched_lessons if l.get("generalized_rule")]

        summary = _build_summary(matched_lessons, past_failures)

        log.info(
            "Memory recall: %d lessons matched | %d past failures surfaced",
            len(matched_lessons),
            len(past_failures),
        )

        return {
            "lessons": matched_lessons,
            "failures": past_failures,
            "rules": rules,
            "summary": summary,
        }

    def recall_for_task(self, task_category: str) -> dict[str, Any]:
        """Convenience method: retrieve all lessons for a task category.

        Args:
            task_category: e.g. 'sql_import', 'file_parse', 'email'

        Returns:
            Same shape as recall().
        """
        return self.recall(
            tags=[task_category],
            query=task_category,
        )

    def surface_warnings_for_review(self) -> list[str]:
        """Return a list of high-confidence generalized rules from memory.

        Used by the reviewer to enrich its findings with past lessons.
        """
        all_lessons = self._archive.load_all_lessons()
        high_confidence = [
            l for l in all_lessons
            if float(l.get("confidence", 0)) >= 0.85
        ]
        return [
            f"[{l['lesson_id']}] {l['generalized_rule']}"
            for l in high_confidence
            if l.get("generalized_rule")
        ]

    def has_seen_pattern(self, pattern_fragment: str) -> bool:
        """Return True if any archived lesson's failed_pattern contains this text.

        Use this to avoid repeating known bad patterns.
        """
        all_lessons = self._archive.load_all_lessons()
        fragment_lower = pattern_fragment.lower()
        return any(
            fragment_lower in l.get("failed_pattern", "").lower()
            for l in all_lessons
        )

    def has_lessons(self) -> bool:
        """Return True if any lessons exist in the archive.

        Use this as a fast eligibility gate before calling recall() —
        avoids a full O(N) file scan when the archive is empty.
        """
        return self._archive.count_lessons() > 0

    def execution_count(self) -> int:
        """Return total number of archived executions."""
        return len(self._archive.load_all_executions())

    def failure_rate(self) -> float:
        """Return fraction of executions that ended in FAIL or ERROR.

        Returns 0.0 if no executions archived yet.
        """
        executions = self._archive.load_all_executions()
        if not executions:
            return 0.0
        failures = sum(
            1 for e in executions
            if e.get("status") in ("FAIL", "ERROR")
        )
        return failures / len(executions)


# ---------------------------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------------------------

def _match_lessons(
    lessons: list[dict[str, Any]],
    tags: list[str],
    query: str,
    max_results: int,
) -> list[dict[str, Any]]:
    """Return lessons matching any tag or any query keyword."""
    if not lessons:
        return []

    query_lower = query.lower()
    tags_lower = {t.lower() for t in tags}

    scored: list[tuple[int, dict[str, Any]]] = []
    for lesson in lessons:
        score = 0

        # Tag match: +2 per matching tag
        lesson_tags = {t.lower() for t in lesson.get("tags", [])}
        score += 2 * len(tags_lower & lesson_tags)

        # Query keyword match in any text field: +1
        if query_lower:
            text_blob = " ".join([
                lesson.get("failed_pattern", ""),
                lesson.get("root_cause", ""),
                lesson.get("fix_pattern", ""),
                lesson.get("generalized_rule", ""),
                lesson.get("task_category", ""),
            ]).lower()
            if query_lower in text_blob:
                score += 1

        if score > 0:
            scored.append((score, lesson))

    # Sort by score descending, then take top N
    scored.sort(key=lambda x: x[0], reverse=True)
    return [lesson for _, lesson in scored[:max_results]]


def _get_failures(
    executions: list[dict[str, Any]],
    max_results: int,
) -> list[dict[str, Any]]:
    """Return the most recent failed/errored executions."""
    failures = [
        e for e in executions
        if e.get("status") in ("FAIL", "ERROR")
    ]
    # Most recent first (relies on execution_id being sortable by timestamp)
    failures.sort(key=lambda e: e.get("executed_at", ""), reverse=True)
    return failures[:max_results]


def _build_summary(
    lessons: list[dict[str, Any]],
    failures: list[dict[str, Any]],
) -> str:
    """Build a concise human-readable summary of recalled memory."""
    if not lessons and not failures:
        return "No relevant memory found. This may be a new pattern."

    parts = []
    if lessons:
        parts.append(
            f"{len(lessons)} relevant lesson(s) found: "
            + "; ".join(l.get("lesson_id", "?") for l in lessons)
        )
    if failures:
        parts.append(
            f"{len(failures)} recent failure(s) to be aware of."
        )
    return " | ".join(parts)
