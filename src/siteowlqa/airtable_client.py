"""airtable_client.py — Airtable REST API integration.

Responsibilities:
 - Fetch pending records (status blank, NEW, or Pending)
 - Parse records into AirtableRecord domain objects
 - Download attachment files to disk
 - Update Processing Status field

Field name constants come from config.py — never hardcoded here.

Concurrency notes:
 - Uses stateless requests.get/patch (thread-safe, no shared Session).
 - All API calls go through _api_request() which retries on 429/5xx
   with exponential back-off. This handles Airtable's 5 req/sec limit
   when multiple workers call update_status() simultaneously.

Formula syntax:
 - Field names containing spaces MUST be wrapped in {curly braces} in
   Airtable filter formulas. e.g. {Processing Status} = 'PASS'
   Bare names without braces cause 422/400 errors on the Airtable side.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from siteowlqa.config import (
    ATAIRTABLE_FIELDS as FIELDS,
    STATUS_PASS,
    UNPROCESSED_STATUSES,
    AppConfig,
)
from siteowlqa.models import AirtableRecord
from siteowlqa.utils import sanitise_filename

log = logging.getLogger(__name__)

AIRTABLE_API_BASE = "https://api.airtable.com/v0"


@dataclass(frozen=True)
class TeamSourceConfig:
    team_key: str
    token: str
    base_id: str
    table_name: str
    view_id: str = ""
    vendor_email_field: str = "Surveyor Email"
    vendor_name_field: str = "Vendor Name"
    site_number_field: str = "Site Number"
    status_field: str = "Processing Status"
    submitted_at_field: str = "Date of Survey"
    submission_id_field: str = "Submission ID"


@dataclass(frozen=True)
class TeamDashboardRecord:
    team_key: str
    record_id: str
    submission_id: str
    vendor_email: str
    vendor_name: str
    site_number: str
    processing_status: str
    submitted_at: str
    created_time: str
    raw_fields: dict[str, Any]

# Retry settings for Airtable API calls
_MAX_RETRIES = 5
_RETRY_BACKOFF_BASE = 1.0   # seconds; doubles each retry
_RETRYABLE_CODES = {429, 500, 502, 503, 504}


def _field(name: str) -> str:
    """Wrap a field name in Airtable formula curly-brace syntax.

    Airtable requires {Field Name} (with braces) for any field name that
    contains spaces or special characters in filter formulas.
    Bare names without braces cause the API to misparse the expression.
    """
    return f"{{{name}}}"


def _api_request(
    method: str,
    url: str,
    headers: dict[str, str],
    **kwargs: Any,
) -> requests.Response:
    """Make one Airtable API call with retry on 429 / transient 5xx.

    Implements exponential back-off:
        attempt 1 → wait 1s
        attempt 2 → wait 2s
        attempt 3 → wait 4s
        attempt 4 → wait 8s
        attempt 5 → wait 16s → raise

    Also honours Retry-After header when Airtable provides it.
    """
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = requests.request(method, url, headers=headers, **kwargs)

            if resp.status_code not in _RETRYABLE_CODES:
                if not resp.ok:
                    # Log the FULL Airtable error body so we can see EXACTLY
                    # which field name or value is being rejected.
                    log.error(
                        "Airtable %s %s -> HTTP %d | body: %s",
                        method.upper(),
                        url.split("/")[-1],
                        resp.status_code,
                        resp.text[:1000],  # Airtable error bodies are short
                    )
                resp.raise_for_status()
                return resp

            # Rate-limited or transient error — respect Retry-After if given
            retry_after = float(
                resp.headers.get("Retry-After", _RETRY_BACKOFF_BASE * (2 ** (attempt - 1)))
            )
            log.warning(
                "Airtable %s %s → %d. Retry %d/%d in %.1fs.",
                method.upper(), url, resp.status_code,
                attempt, _MAX_RETRIES, retry_after,
            )
            time.sleep(retry_after)
            last_exc = requests.HTTPError(response=resp)

        except requests.exceptions.ConnectionError as exc:
            wait = _RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
            log.warning(
                "Airtable connection error (attempt %d/%d): %s. Retrying in %.1fs.",
                attempt, _MAX_RETRIES, exc, wait,
            )
            time.sleep(wait)
            last_exc = exc

    raise last_exc or RuntimeError("Airtable request failed after max retries.")


def _download_via_powershell(url: str, dest: Path) -> None:
    """Download a URL to *dest* using PowerShell Invoke-WebRequest.

    PowerShell uses WinInet under the hood, which transparently handles
    the corporate NTLM proxy (sysproxy.wal-mart.com:8080) using the
    current Windows login session — no explicit credentials needed.

    This is specifically needed for Airtable attachment CDN URLs
    (v5.airtableusercontent.com) which cannot be reached by Python's
    requests without NTLM proxy support.

    Raises RuntimeError if PowerShell exits non-zero.
    """
    import subprocess  # stdlib only — intentional local import

    # UseBasicParsing avoids IE engine dependency on Server SKUs.
    # -ErrorAction Stop turns all PS errors into terminating errors.
    ps_cmd = (
        f"Invoke-WebRequest -Uri '{url}' "
        f"-OutFile '{dest}' "
        f"-UseBasicParsing "
        f"-ErrorAction Stop"
    )
    result = subprocess.run(
        ["powershell", "-NonInteractive", "-Command", ps_cmd],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"PowerShell download failed (exit {result.returncode}): "
            f"{result.stderr.strip()}"
        )


class AirtableWriteVerificationError(RuntimeError):
    """Raised when Airtable accepted a PATCH but required fields did not persist."""


class AirtableClient:
    """Thread-safe wrapper around the Airtable REST API."""

    def __init__(self, cfg: AppConfig) -> None:
        self._base_url = (
            f"{AIRTABLE_API_BASE}/{cfg.airtable_base_id}/"
            f"{requests.utils.quote(cfg.airtable_table_name, safe='')}"
        )
        self._headers = {
            "Authorization": f"Bearer {cfg.airtable_token}",
            "Content-Type": "application/json",
        }
        self._temp_dir = cfg.temp_dir

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_pending_records(self) -> list[AirtableRecord]:
        """Fetch all records where Processing Status is unprocessed.

        Handles Airtable pagination automatically.
        Returns parsed AirtableRecord objects — not raw dicts.
        """
        raw_records = self._fetch_all_pages()
        parsed = []
        for raw in raw_records:
            record = self._parse_record(raw)
            if record is not None:
                parsed.append(record)
        log.info("Found %d pending submission(s).", len(parsed))
        return parsed

    def patch_score(self, record_id: str, value: str) -> None:
        """Write an explicit string value to the Score field.

        Separate from update_result() so PASS submissions can unconditionally
        write 'PASS' to Score without touching the fallback-candidate machinery.
        """
        url = f"{self._base_url}/{record_id}"
        _api_request(
            "PATCH", url, self._headers,
            json={"fields": {FIELDS.score: value}},
            timeout=30,
        )
        log.info("Record %s -> Score = '%s'", record_id, value)

    def patch_score_and_true_score(self, record_id: str, numeric_score: float) -> None:
        """Write Score (as '95.6%' string) + True Score (as float) in one PATCH.

        Used by the backfill script to fix historical records with blank scores
        WITHOUT overwriting Status, Notes, or Fail Summary.
        """
        url = f"{self._base_url}/{record_id}"
        score_str = f"{numeric_score:.1f}%"
        fields: dict[str, Any] = {
            FIELDS.score: score_str,
            FIELDS.true_score: numeric_score,
        }
        _api_request(
            "PATCH", url, self._headers,
            json={"fields": fields},
            timeout=30,
        )
        log.info(
            "Record %s -> Score = '%s', True Score = %s",
            record_id, score_str, numeric_score,
        )

    def update_result(
        self,
        record_id: str,
        status: str,
        score: float | None = None,
        fail_summary: str = "",
        notes_internal: str = "",
        true_score: float | None = None,
    ) -> None:
        """PATCH all grading result fields to Airtable in one call.

        REQUIREMENT: true_score and notes_internal MUST always be written.
        They must never be blank in Airtable after a submission is graded.

        Fallback ladder (tries each payload in order until one succeeds):
          T1: status + score + fail_summary + true_score + notes_internal  [full]
          T2: same without notes_internal
          T3: same without fail_summary
          T4: status + score + true_score (no summary, no notes)
          T5: status + true_score + notes_internal  (score dropped as last resort)
          T6: status + true_score
          T7: status only  (absolute safety net, guarantees status is written)

        true_score and notes_internal survive as long as possible through the
        ladder. They are only dropped at T7 (status-only) which is the last resort.
        """
        url = f"{self._base_url}/{record_id}"

        # Score field ALWAYS shows the numeric percentage derived from True Score.
        # Both PASS and FAIL display e.g. '95.6%'.  Status field carries PASS/FAIL.
        score_as_string = f"{score:.1f}%" if score is not None else None
        score_as_float = score

        internal = (notes_internal or "").strip()
        summary = (fail_summary or "").strip()

        # Notes for Internal must never be blank after processing.
        # If caller forgot to provide diagnostics, synthesize a minimal audit trail
        # instead of silently writing an empty field like a goblin.
        if not internal:
            score_display = f"{score:.1f}%" if score is not None else "N/A"
            true_score_display = (
                f"{true_score:.10f}".rstrip("0").rstrip(".")
                if true_score is not None else "N/A"
            )
            internal = (
                f"Auto-generated writeback note. Status={status} | "
                f"Score={score_display} | TrueScore={true_score_display}"
            )[:5000]

        # ---------------------------------------------------------------------------
        # Build the fallback ladder.
        # Rule: true_score and notes_internal must be present in every tier
        # except the absolute last-resort status-only payload.
        # ---------------------------------------------------------------------------
        def _fields(
            *,
            inc_score_str: bool = False,
            inc_score_float: bool = False,
            inc_summary: bool = False,
            inc_notes: bool = False,
            inc_true_score: bool = False,
        ) -> dict:
            f: dict = {FIELDS.status: status}
            if inc_score_str and score_as_string is not None:
                f[FIELDS.score] = score_as_string
            elif inc_score_float and score_as_float is not None:
                f[FIELDS.score] = score_as_float
            if inc_summary and summary:
                f[FIELDS.fail_summary] = summary
            if inc_notes and internal:
                f[FIELDS.notes_internal] = internal
            if inc_true_score and true_score is not None:
                f[FIELDS.true_score] = true_score
            return f

        candidate_payloads: list[tuple[str, dict]] = [
            # T1: full payload — string score
            ("T1:full(str-score)", _fields(
                inc_score_str=True, inc_summary=True,
                inc_notes=True, inc_true_score=True)),
            # T2: full payload — float score
            ("T2:full(float-score)", _fields(
                inc_score_float=True, inc_summary=True,
                inc_notes=True, inc_true_score=True)),
            # T3: no fail_summary — string score, keep notes
            ("T3:status+score(str)+true+notes", _fields(
                inc_score_str=True, inc_notes=True, inc_true_score=True)),
            # T4: no fail_summary — float score, keep notes
            ("T4:status+score(float)+true+notes", _fields(
                inc_score_float=True, inc_notes=True, inc_true_score=True)),
            # T5: no score — keep true_score + notes_internal
            ("T5:status+true+notes", _fields(
                inc_notes=True, inc_true_score=True)),
            # T6: true_score only — notes could not be accepted by Airtable
            ("T6:status+true", _fields(inc_true_score=True)),
            # T7: absolute last resort — status only
            ("T7:status-only", {FIELDS.status: status}),
        ]

        # Remove duplicate/empty payloads (e.g. T4/T5 are identical when score is None)
        seen: set[str] = set()
        deduped: list[tuple[str, dict]] = []
        for label, payload in candidate_payloads:
            key = str(sorted(payload.items()))
            if key not in seen:
                seen.add(key)
                deduped.append((label, payload))
        candidate_payloads = deduped

        last_exc: Exception | None = None
        for attempt_label, fields in candidate_payloads:
            try:
                log.debug(
                    "update_result attempt='%s' payload_keys=%s",
                    attempt_label, list(fields.keys()),
                )
                _api_request(
                    "PATCH", url, self._headers,
                    json={"fields": fields}, timeout=30,
                )
                log.info(
                    "Record %s -> Status=%s Score=%s TrueScore=%s (attempt='%s')",
                    record_id, status,
                    score_as_string if score is not None else "N/A",
                    true_score if true_score is not None else "N/A",
                    attempt_label,
                )
                first_label = candidate_payloads[0][0]
                self._verify_result_writeback(
                    record_id=record_id,
                    expected_status=status,
                    expected_true_score=true_score,
                    expected_notes=internal,
                    attempt_label=attempt_label,
                )
                if attempt_label != first_label:
                    log.warning(
                        "update_result used reduced payload '%s' for record %s. "
                        "Fields in payload: %s",
                        attempt_label, record_id, list(fields.keys()),
                    )
                return  # success
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                log.warning(
                    "update_result attempt='%s' failed for record %s: %s — "
                    "trying next fallback.",
                    attempt_label, record_id, exc,
                )

        raise RuntimeError(
            f"update_result: all fallback attempts failed for record {record_id}."
        ) from last_exc

    def _verify_result_writeback(
        self,
        *,
        record_id: str,
        expected_status: str,
        expected_true_score: float | None,
        expected_notes: str,
        attempt_label: str,
    ) -> None:
        """Read the record back and verify required grading fields persisted.

        This closes the nasty gap where Airtable can accept a PATCH request but
        the live record still ends up missing True Score or Notes for Internal.
        """
        fields = self.get_record_fields(record_id)
        actual_status = str(fields.get(FIELDS.status, "")).strip()
        actual_notes = str(fields.get(FIELDS.notes_internal, "")).strip()
        actual_true_score = fields.get(FIELDS.true_score)

        problems: list[str] = []
        if actual_status != expected_status:
            problems.append(
                f"status expected={expected_status!r} actual={actual_status!r}"
            )
        if expected_notes.strip() and not actual_notes:
            problems.append("Notes for Internal is blank after PATCH")
        if expected_true_score is not None and actual_true_score in (None, ""):
            problems.append("True Score is blank after PATCH")

        if problems:
            msg = (
                f"Airtable writeback verification failed for record {record_id} "
                f"after {attempt_label}: " + "; ".join(problems)
            )
            log.error(msg)
            raise AirtableWriteVerificationError(msg)

        log.info(
            "Verified Airtable writeback for record %s: status=%s true_score=%s notes_present=%s",
            record_id,
            actual_status,
            actual_true_score,
            bool(actual_notes),
        )

    def get_record_fields(self, record_id: str) -> dict[str, Any]:
        """Return the current Airtable fields for one record."""
        url = f"{self._base_url}/{record_id}"
        resp = _api_request("GET", url, self._headers, timeout=30)
        return resp.json().get("fields", {})

    def update_status(self, record_id: str, status: str) -> None:
        """PATCH only the Processing Status field. Used for ERROR/intermediate states."""
        url = f"{self._base_url}/{record_id}"
        _api_request(
            "PATCH",
            url,
            self._headers,
            json={"fields": {FIELDS.status: status}},
            timeout=30,
        )
        log.info("Record %s -> Processing Status = '%s'", record_id, status)

    def patch_vendor_email(self, record_id: str, email: str) -> None:
        """Overwrite the Surveyor/Vendor Email field for a record."""
        url = f"{self._base_url}/{record_id}"
        _api_request(
            "PATCH",
            url,
            self._headers,
            json={"fields": {FIELDS.vendor_email: email}},
            timeout=30,
        )
        log.info("Record %s -> %s = '%s'", record_id, FIELDS.vendor_email, email)

    def patch_submission_id(self, record_id: str, submission_id: str) -> None:
        """Persist the Submission ID field so the Airtable primary label is never blank."""
        clean_submission_id = str(submission_id).strip()
        if not clean_submission_id:
            clean_submission_id = record_id
        url = f"{self._base_url}/{record_id}"
        _api_request(
            "PATCH",
            url,
            self._headers,
            json={"fields": {FIELDS.submission_id: clean_submission_id}},
            timeout=30,
        )
        log.info("Record %s -> %s = '%s'", record_id, FIELDS.submission_id, clean_submission_id)

    def get_records_by_statuses(
        self, statuses: set[str]
    ) -> list[AirtableRecord]:
        """Fetch records whose Processing Status is one of *statuses*.

        Used on startup to find stuck QUEUED/PROCESSING records.
        """
        # {Field Name} braces are required for fields with spaces.
        conditions = ", ".join(
            f"{_field(FIELDS.status)} = '{s}'" for s in statuses
        )
        formula = f"OR({conditions})" if len(statuses) > 1 else conditions

        params: dict[str, Any] = {
            "filterByFormula": formula,
            "pageSize": 100,
        }
        all_records: list[dict[str, Any]] = []
        while True:
            resp = _api_request(
                "GET", self._base_url, self._headers,
                params=params, timeout=30,
            )
            data = resp.json()
            all_records.extend(data.get("records", []))
            offset = data.get("offset")
            if not offset:
                break
            params["offset"] = offset

        parsed = [
            r for raw in all_records
            if (r := self._parse_record(raw)) is not None
        ]
        log.info(
            "get_records_by_statuses(%s): found %d record(s).",
            statuses, len(parsed),
        )
        return parsed

    def get_pass_records_for_correction(
        self,
        *,
        min_true_score: float = 95.0,
    ) -> list[AirtableRecord]:
        """Fetch PASS records whose True Score meets the correction threshold.

        Airtable formula::
            AND({Processing Status} = 'PASS', {True Score} >= <threshold>)

        Used exclusively by CorrectionWorker to find qualifying historical
        and current records without running the grading pipeline again.
        This method is read-only — it never writes to Airtable.
        """
        # Airtable numeric comparison works directly on Number fields.
        # No quotes around the numeric value — Airtable treats quoted values
        # as strings in numeric comparisons and silently returns nothing.
        formula = (
            f"AND("
            f"{_field(FIELDS.status)} = '{STATUS_PASS}', "
            f"{_field(FIELDS.true_score)} >= {min_true_score}"
            f")"
        )
        params: dict[str, Any] = {
            "filterByFormula": formula,
            "pageSize": 100,
        }
        all_records: list[dict[str, Any]] = []
        while True:
            resp = _api_request(
                "GET", self._base_url, self._headers,
                params=params, timeout=30,
            )
            data = resp.json()
            all_records.extend(data.get("records", []))
            offset = data.get("offset")
            if not offset:
                break
            params["offset"] = offset

        parsed = [
            r for raw in all_records
            if (r := self._parse_record(raw)) is not None
        ]
        log.info(
            "get_pass_records_for_correction(min_true_score=%.1f): "
            "found %d qualifying record(s).",
            min_true_score, len(parsed),
        )
        return parsed

    def list_all_records(
        self,
        *,
        max_records: int = 0,
    ) -> list[AirtableRecord]:
        """Fetch all Airtable records (optionally capped).

        This is the correct tool for backfills / bulk regrading.
        No status filtering.

        Args:
            max_records: 0 means no cap (fetch everything).

        Returns:
            Parsed AirtableRecord objects.
        """
        params: dict[str, Any] = {"pageSize": 100}
        all_records: list[dict[str, Any]] = []
        while True:
            resp = _api_request(
                "GET", self._base_url, self._headers,
                params=params, timeout=30,
            )
            data = resp.json()
            all_records.extend(data.get("records", []))
            if max_records and len(all_records) >= max_records:
                all_records = all_records[:max_records]
                break
            offset = data.get("offset")
            if not offset:
                break
            params["offset"] = offset

        skipped_no_attachment = 0
        parsed: list[AirtableRecord] = []
        for raw in all_records:
            rec = self._parse_record(raw)
            if rec is None:
                skipped_no_attachment += 1
                continue
            parsed.append(rec)

        log.info(
            "list_all_records(max_records=%s): raw=%d parsed=%d skipped_no_attachment=%d",
            max_records or "<all>",
            len(all_records),
            len(parsed),
            skipped_no_attachment,
        )
        return parsed

    def list_all_raw_records(self) -> list[dict[str, Any]]:
        """Return ALL records as raw {id, fields} dicts — no filtering, no parsing.

        Used by backfill / audit scripts that need to inspect every field,
        including records that have no attachment or are in any status.
        """
        params: dict[str, Any] = {"pageSize": 100}
        raw: list[dict[str, Any]] = []
        while True:
            resp = _api_request(
                "GET", self._base_url, self._headers,
                params=params, timeout=30,
            )
            data = resp.json()
            raw.extend(data.get("records", []))
            offset = data.get("offset")
            if not offset:
                break
            params["offset"] = offset
        log.info("list_all_raw_records: fetched %d raw records", len(raw))
        return raw

    def list_dashboard_records(
        self,
        source: TeamSourceConfig,
        *,
        max_records: int = 10000,  # LIVE HOT RELOAD: default to all records
    ) -> list[TeamDashboardRecord]:
        """Return lightweight live records for executive dashboard snapshots.

        This is intentionally read-only and generic so we can support multiple
        Airtable sources (Survey + Scout) without changing the processing
        pipeline, which still uses the primary Survey Team config.
        """
        if not source.token or not source.base_id or not source.table_name:
            return []

        base_url = (
            f"{AIRTABLE_API_BASE}/{source.base_id}/"
            f"{requests.utils.quote(source.table_name, safe='')}"
        )
        headers = {
            "Authorization": f"Bearer {source.token}",
            "Content-Type": "application/json",
        }
        params: dict[str, Any] = {"pageSize": min(max_records, 100)}
        if source.view_id:
            params["view"] = source.view_id

        records: list[TeamDashboardRecord] = []
        while len(records) < max_records:
            resp = _api_request("GET", base_url, headers, params=params, timeout=30)
            data = resp.json()
            for raw in data.get("records", []):
                fields = raw.get("fields", {})
                email = str(fields.get(source.vendor_email_field, "")).strip()
                name = str(fields.get(source.vendor_name_field, "")).strip()
                records.append(
                    TeamDashboardRecord(
                        team_key=source.team_key,
                        record_id=str(raw.get("id", "")),
                        submission_id=str(fields.get(source.submission_id_field, raw.get("id", ""))).strip(),
                        vendor_email=email,
                        vendor_name=name or _derive_vendor_name(fields, source),
                        site_number=str(fields.get(source.site_number_field, "")).strip(),
                        processing_status=str(fields.get(source.status_field, "")).strip(),
                        submitted_at=str(fields.get(source.submitted_at_field, "")).strip(),
                        created_time=str(raw.get("createdTime", "")).strip(),
                        raw_fields={str(k): fields.get(k, "") for k in fields.keys()},
                    )
                )
                if len(records) >= max_records:
                    break
            if len(records) >= max_records:
                break
            offset = data.get("offset")
            if not offset:
                break
            params["offset"] = offset

        return records

    def list_records_for_testing(
        self,
        *,
        max_records: int = 25,
        statuses: set[str] | None = None,
    ) -> list[AirtableRecord]:
        """Return recent records for dry-run verification.

        Unlike get_pending_records(), this is intentionally broader and read-only:
        it supports arbitrary statuses so QA scripts can replay recent PASS/FAIL/
        ERROR submissions without mutating Airtable.
        """
        params: dict[str, Any] = {"pageSize": min(max_records, 100)}
        if statuses:
            field_ref = _field(FIELDS.status)
            ordered = sorted(statuses)
            conditions = ", ".join(
                f"{field_ref} = '{s}'" if s else f"{field_ref} = ''"
                for s in ordered
            )
            params["filterByFormula"] = (
                f"OR({conditions})" if len(ordered) > 1 else conditions
            )

        all_records: list[dict[str, Any]] = []
        while len(all_records) < max_records:
            resp = _api_request(
                "GET", self._base_url, self._headers,
                params=params, timeout=30,
            )
            data = resp.json()
            all_records.extend(data.get("records", []))
            if len(all_records) >= max_records:
                break
            offset = data.get("offset")
            if not offset:
                break
            params["offset"] = offset

        parsed = [
            rec for raw in all_records[:max_records]
            if (rec := self._parse_record(raw)) is not None
        ]
        log.info(
            "list_records_for_testing(statuses=%s): found %d record(s).",
            statuses or "<all>", len(parsed),
        )
        return parsed

    def download_attachment(self, record: AirtableRecord) -> Path:
        """Download the first attachment for a record to temp_dir.

        Airtable attachment CDN URLs (v5.airtableusercontent.com) require
        the corporate NTLM proxy which Python's requests cannot authenticate
        with natively. We delegate to PowerShell's Invoke-WebRequest, which
        uses WinInet and the Windows credential store automatically.

        Returns the local file path.
        Raises ValueError if no attachment is present.
        """
        if not record.attachment_url:
            raise ValueError(
                f"Record {record.record_id} has no attachment URL. "
                "Check the Airtable form configuration."
            )

        safe_name = sanitise_filename(record.attachment_filename)
        dest = self._temp_dir / f"{record.record_id}_{safe_name}"

        log.info("Downloading '%s' -> %s", record.attachment_filename, dest)

        _download_via_powershell(record.attachment_url, dest)

        log.info(
            "Attachment saved: %s (%d bytes)",
            dest.name, dest.stat().st_size,
        )
        return dest

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_all_pages(self) -> list[dict[str, Any]]:
        """Fetch all pages of pending records using a correctly formed formula.

        Formula example with 3 unprocessed statuses:
            OR({Processing Status} = '', {Processing Status} = 'NEW',
               {Processing Status} = 'Pending')

        The {curly brace} syntax is mandatory for field names with spaces.
        """
        field_ref = _field(FIELDS.status)   # -> "{Processing Status}"

        conditions = ", ".join(
            f"{field_ref} = '{s}'" if s else f"{field_ref} = ''"
            for s in UNPROCESSED_STATUSES
        )
        formula = f"OR({conditions})"

        params: dict[str, Any] = {
            "filterByFormula": formula,
            "pageSize": 100,
        }
        all_records: list[dict[str, Any]] = []

        while True:
            resp = _api_request(
                "GET", self._base_url, self._headers,
                params=params, timeout=30,
            )
            data = resp.json()
            all_records.extend(data.get("records", []))
            offset = data.get("offset")
            if not offset:
                break
            params["offset"] = offset

        return all_records

    def _parse_record(self, raw: dict[str, Any]) -> AirtableRecord | None:
        """Convert a raw Airtable API dict into an AirtableRecord.

        Returns None and logs a warning if critical fields are missing.
        """
        record_id: str = raw["id"]
        fields: dict[str, Any] = raw.get("fields", {})

        attachments = fields.get(FIELDS.attachment, [])
        if not attachments:
            log.warning(
                "Record %s has no attachment in field '%s' — skipping.",
                record_id, FIELDS.attachment,
            )
            return None

        first_attachment = attachments[0]
        attachment_url: str = first_attachment.get("url", "")
        attachment_filename: str = first_attachment.get("filename", "export.xlsx")

        submission_id = str(fields.get(FIELDS.submission_id, "")).strip() or record_id

        return AirtableRecord(
            record_id=record_id,
            submission_id=submission_id,
            vendor_email=str(fields.get(FIELDS.vendor_email, "")),
            vendor_name=_derive_vendor_name(fields, FIELDS),
            site_number=str(fields.get(FIELDS.site_number, "")),
            attachment_url=attachment_url,
            attachment_filename=attachment_filename,
            processing_status=str(fields.get(FIELDS.status, "")),
            submitted_at=str(fields.get(FIELDS.submitted_at, "")),
            team_key="survey",
            survey_type=str(fields.get(FIELDS.survey_type, "")).strip() or None,
        )


def _derive_vendor_name(fields: dict[str, Any], f: Any) -> str:
    """Return vendor name from field, or fall back to email domain."""
    vendor_name_field = getattr(f, "vendor_name_field", getattr(f, "vendor_name", "Vendor Name"))
    vendor_email_field = getattr(f, "vendor_email_field", getattr(f, "vendor_email", "Surveyor Email"))
    name = str(fields.get(vendor_name_field, "")).strip()
    if name:
        return name
    email = str(fields.get(vendor_email_field, "")).strip()
    if "@" in email:
        return email.split("@", 1)[1]
    return "Unknown Vendor"