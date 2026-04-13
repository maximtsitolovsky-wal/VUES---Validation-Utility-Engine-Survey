"""emailer.py — SMTP email sender for SiteOwlQA pipeline.

Responsibilities:
 - Send PASS notification (no score, per spec)
 - Send FAIL notification with score percentage and CSV attachment
 - Send ERROR notification so vendor is not left waiting silently

SMTP credentials come from AppConfig — never hardcoded here.
Email body wording is owned by this module for single-point editing.
"""

from __future__ import annotations

import logging
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import pandas as pd

from siteowlqa.config import AppConfig

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def send_pass_email(
    cfg: AppConfig,
    to_email: str,
    submission_id: str,
) -> None:
    """Send PASS result email.

    Per spec: subject must be 'SiteOwl QA Result - Pass'.
    Per spec: do NOT include score percentage in pass emails.
    """
    subject = "SiteOwl QA Result - Pass"
    body = _pass_body(submission_id)
    msg = _build_message(cfg.from_email, to_email, subject, body)
    _send(cfg, msg)
    log.info("PASS email sent → %s (submission=%s)", to_email, submission_id)


def send_fail_email(
    cfg: AppConfig,
    to_email: str,
    submission_id: str,
    score: float | None,
    error_df: pd.DataFrame | None,
    output_dir: Path,
) -> None:
    """Send FAIL result email with score and CSV error attachment.

    Per spec: subject must be 'SiteOwl QA Result - Fail'.
    Per spec: body must include 'Fail', score percentage, and attached mistake report.
    """
    subject = "SiteOwl QA Result - Fail"
    body = _fail_body(submission_id, score)
    msg = _build_message(cfg.from_email, to_email, subject, body)

    if error_df is not None and not error_df.empty:
        csv_path = _write_error_csv(error_df, submission_id, output_dir)
        _attach_file(msg, csv_path)
    else:
        log.warning(
            "FAIL email for submission '%s' has no error rows to attach.",
            submission_id,
        )

    _send(cfg, msg)
    log.info("FAIL email sent → %s (submission=%s score=%s)", to_email, submission_id, score)


def send_error_email(
    cfg: AppConfig,
    to_email: str,
    submission_id: str,
    error_message: str,
) -> None:
    """Notify vendor that a system error occurred during processing."""
    subject = "SiteOwl QA Result - Processing Error"
    body = _error_body(submission_id, error_message)
    msg = _build_message(cfg.from_email, to_email, subject, body)
    _send(cfg, msg)
    log.info("ERROR email sent → %s (submission=%s)", to_email, submission_id)


# ---------------------------------------------------------------------------
# Body builders
# ---------------------------------------------------------------------------

def _pass_body(submission_id: str) -> str:
    return (
        f"Dear Vendor,\n\n"
        f"Your SiteOwl device submission has passed QA review.\n\n"
        f"  Result       : Pass\n"
        f"  Submission ID: {submission_id}\n\n"
        f"No further action is required.\n\n"
        f"Thank you,\n"
        f"SiteOwl QA Team"
    )


def _fail_body(submission_id: str, score: float | None) -> str:
    score_str = f"{score:.1f}%" if score is not None else "N/A"
    return (
        f"Dear Vendor,\n\n"
        f"Your SiteOwl device submission did not pass QA review.\n\n"
        f"  Result       : Fail\n"
        f"  Score        : {score_str}\n"
        f"  Submission ID: {submission_id}\n\n"
        f"Please review the attached error report for details on rows that "
        f"failed validation. Correct the issues and resubmit.\n\n"
        f"Thank you,\n"
        f"SiteOwl QA Team"
    )


def _error_body(submission_id: str, error_message: str) -> str:
    return (
        f"Dear Vendor,\n\n"
        f"We encountered an error while processing your submission.\n\n"
        f"  Submission ID: {submission_id}\n"
        f"  Error Ref    : {error_message[:300]}\n\n"
        f"Our team has been notified and will follow up.\n\n"
        f"Thank you for your patience,\n"
        f"SiteOwl QA Team"
    )


# ---------------------------------------------------------------------------
# MIME helpers
# ---------------------------------------------------------------------------

def _build_message(
    from_email: str, to_email: str, subject: str, body: str
) -> MIMEMultipart:
    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))
    return msg


def _write_error_csv(
    error_df: pd.DataFrame, submission_id: str, output_dir: Path
) -> Path:
    """Write the QAResults error rows to a CSV in output_dir."""
    # Sanitise submission_id for use in filename
    safe_id = submission_id.replace("/", "-").replace("\\", "-")
    filename = f"QA_Errors_{safe_id}.csv"
    path = output_dir / filename
    error_df.to_csv(path, index=False, encoding="utf-8")
    log.info(
        "Error CSV written: %s (%d rows)", path.name, len(error_df)
    )
    return path


def _attach_file(msg: MIMEMultipart, file_path: Path) -> None:
    """Attach a file to a MIMEMultipart message as octet-stream."""
    with open(file_path, "rb") as fh:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(fh.read())
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f'attachment; filename="{file_path.name}"',
    )
    msg.attach(part)
    log.debug("Attached file: %s", file_path.name)


def _send(cfg: AppConfig, msg: MIMEMultipart) -> None:
    """Open SMTP connection and send the assembled message.

    Handles STARTTLS for port 587 / 465 and plain relay on port 25.
    """
    log.debug("SMTP connect → %s:%d", cfg.smtp_server, cfg.smtp_port)
    with smtplib.SMTP(cfg.smtp_server, cfg.smtp_port, timeout=30) as server:
        server.ehlo()
        if cfg.smtp_port not in (25,):
            server.starttls()
            server.ehlo()
        if cfg.smtp_user and cfg.smtp_pass:
            server.login(cfg.smtp_user, cfg.smtp_pass)
        server.sendmail(msg["From"], msg["To"], msg.as_string())
    log.debug("SMTP send complete.")
