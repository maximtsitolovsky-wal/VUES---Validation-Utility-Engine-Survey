"""utils.py — Shared utilities for SiteOwlQA pipeline.

Logging setup, ID generation, file cleanup, and other cross-cutting
concerns that don't belong to any single domain module.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

_LOG_FORMAT = logging.Formatter(
    fmt="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def configure_logging(log_dir: Path, level: int = logging.INFO) -> None:
    """Configure root logger with rotating file handler + console handler.

    Call this ONCE at process startup before any module logs anything.
    5 MB per file, 10 backup files = max 50 MB disk usage.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "siteowl_qa.log"

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setFormatter(_LOG_FORMAT)

    # Console handler: safe for both interactive terminals and Windows service
    # context where sys.stdout may be None or a cp1252-limited pipe.
    # PYTHONIOENCODING=utf-8 is set in SiteOwlQA.xml for the service case.
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(file_handler)
    if sys.stdout is not None:
        try:
            # Python 3.9+: pass encoding so unicode chars don't crash cp1252
            console_handler = logging.StreamHandler(
                stream=open(sys.stdout.fileno(), mode='w',
                            encoding='utf-8', buffering=1,
                            closefd=False)
            )
        except Exception:
            # Fallback: plain StreamHandler (service log, no terminal)
            console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(_LOG_FORMAT)
        root.addHandler(console_handler)

    # Silence noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------

def new_execution_id() -> str:
    """Generate a short, sortable unique execution ID.

    Format: EXEC-YYYYMMDD-HHMMSS-<4 hex chars>
    Example: EXEC-20250601-143022-a3f2
    """
    now = datetime.now(timezone.utc)
    suffix = uuid.uuid4().hex[:4]
    return f"EXEC-{now:%Y%m%d-%H%M%S}-{suffix}"


def new_lesson_id(existing_count: int) -> str:
    """Generate a sequential lesson ID.

    Format: LESSON-NNN
    Example: LESSON-014
    """
    return f"LESSON-{existing_count + 1:03d}"


# ---------------------------------------------------------------------------
# Canonicalization helpers
# ---------------------------------------------------------------------------


def canon_site_id(value: object) -> str:
    """Canonicalize site IDs used as lookup keys.

    Goal: Airtable `Site Number` == workbook `SelectedSiteID` == SQL `ProjectID`.

    Handles common drift:
    - None / NaN-ish -> ""
    - whitespace
    - Excel numeric IDs like "3445.0" / "3445.00" -> "3445"

    We intentionally keep non-numeric IDs as-is (after strip).
    """
    if value is None:
        return ""

    text = str(value).strip()
    if not text:
        return ""

    lower = text.lower()
    if lower in {"nan", "none", "null"}:
        return ""

    # Normalize decimal-like numeric strings if they are mathematically integers.
    # Examples: "3445.0", "3445.00" -> "3445".
    if "." in text:
        left, right = text.split(".", 1)
        if left.isdigit() and right.isdigit() and set(right) <= {"0"}:
            return left

    return text


# ---------------------------------------------------------------------------
# File utilities
# ---------------------------------------------------------------------------

def safe_delete(path: Path | None) -> None:
    """Delete a file silently, logging a warning ."""
    if path is None or not path.exists():
        return
    try:
        path.unlink()
        logging.getLogger(__name__).debug("Deleted temp file: %s", path)
    except OSError as exc:
        logging.getLogger(__name__).warning(
            "Could not delete temp file %s: %s", path, exc
        )


def sanitise_filename(name: str) -> str:
    """Strip path components and dangerous characters from a filename."""
    # Take only the final component to prevent path traversal
    safe = Path(name).name
    # Replace characters not safe for Windows filenames
    for ch in r'<>:"/\|?*':
        safe = safe.replace(ch, "_")
    return safe or "unnamed_file"
