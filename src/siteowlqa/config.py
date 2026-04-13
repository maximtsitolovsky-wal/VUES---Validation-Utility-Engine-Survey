"""config.py — Centralized configuration for SiteOwlQA pipeline.

Configuration is loaded from two sources:

1. User Profile (~/.siteowlqa/config.json) - Sensitive data
   - Airtable tokens
   - SQL Server credentials
   - SMTP passwords
   - LLM API keys
   
2. .env file - Non-sensitive settings
   - Poll intervals
   - Folder paths
   - Reference data source
   - Feature flags

Sensitive data NEVER lives in the monorepo. It's stored in the user's
home directory where only that user can read it.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from siteowlqa.user_config import load_user_config, get_user_config_path

log = logging.getLogger(__name__)

# Load .env from repository root (for non-sensitive config only)
_ENV_PATH = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)  # always prefer .env over stale OS env vars


# ---------------------------------------------------------------------------
# Airtable field name constants
# Centralised here so a field rename is a one-line change.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AirtableFields:
    # These names must match the exact column headers in the Airtable base.
    submission_id: str = "Submission ID"
    vendor_email: str = "Surveyor Email"
    vendor_name: str = "Vendor Name"
    site_number: str = "Site Number"
    attachment: str = "Upload File"
    status: str = "Processing Status"
    submitted_at: str = "Date of Survey"
    score: str = "Score"
    true_score: str = "True Score"
    fail_summary: str = "Fail Summary"
    notes_internal: str = "Notes for Internal"


ATAIRTABLE_FIELDS = AirtableFields()

# Airtable status values
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_ERROR = "ERROR"
STATUS_QUEUED = "QUEUED"
STATUS_PROCESSING = "PROCESSING"
UNPROCESSED_STATUSES = {"", "NEW", "Pending"}
STUCK_STATUSES = {STATUS_QUEUED, STATUS_PROCESSING}


# ---------------------------------------------------------------------------
# Vendor file columns
# ---------------------------------------------------------------------------

VENDOR_GRADE_COLUMNS: tuple[str, ...] = (
    "Name",
    "Abbreviated Name",
    "Part Number",
    "Manufacturer",
    "IP Address",
    "MAC Address",
    "IP / Analog",
    "Description",
)

VENDOR_HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "Name": ("Name", "CameraName", "cameraname"),
    "Abbreviated Name": ("Abbreviated Name", "AbbreviatedName", "Abreviated", "Abreviated "),
    "Part Number": ("Part Number", "PartNumber"),
    "Manufacturer": ("Manufacturer",),
    "IP Address": ("IP Address", "IPAddress", "IP Address "),
    "MAC Address": ("MAC Address", "MACAddress"),
    "IP / Analog": ("IP / Analog", "IPAnalog", "IP/Analog"),
    "Description": ("Description",),
}

VENDOR_REQUIRED_COLUMNS: list[str] = ["Project ID", "Plan ID", *list(VENDOR_GRADE_COLUMNS)]
VENDOR_TO_SQL_COLUMNS: dict[str, str] = {
    "Project ID": "Project ID",
    "Plan ID": "Plan ID",
    "Name": "Name",
    "Abbreviated Name": "Abbreviated Name",
    "Part Number": "Part Number",
    "Manufacturer": "Manufacturer",
    "IP Address": "IP Address",
    "MAC Address": "MAC Address",
    "IP / Analog": "IP / Analog",
    "Description": "Description",
}

PASS_THRESHOLD: float = 95.0


# ---------------------------------------------------------------------------
# Application config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AppConfig:
    """Immutable application configuration.
    
    Sensitive values come from ~/.siteowlqa/config.json
    Non-sensitive values come from .env
    """

    # Required: SQL (from user config)
    sql_server: str
    sql_database: str
    sql_driver: str

    # Required: Airtable (from user config)
    airtable_token: str
    airtable_base_id: str
    airtable_table_name: str

    # Required: Paths (from .env or defaults)
    temp_dir: Path
    output_dir: Path
    log_dir: Path
    archive_dir: Path
    submissions_dir: Path

    # Optional: Behavior (from .env)
    reference_source: str = "sql"
    poll_interval_seconds: int = 60
    worker_threads: int = 3
    email_override_to: str = ""

    # Optional: Reference workbook (from user config or .env)
    reference_workbook_path: Path | None = None
    reference_workbook_sheet: str = ""
    reference_workbook_site_id_column: str = "SelectedSiteID"

    # Optional: SMTP (from user config)
    smtp_enabled: bool = False
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    from_email: str = ""

    # Optional: Element LLM Gateway (from user config)
    element_llm_gateway_url: str = ""
    element_llm_gateway_api_key: str = ""
    element_llm_gateway_model: str = "element:gpt-4o"
    element_llm_gateway_project_id: str = ""
    wmt_ca_path: str = ""

    # Optional: Post-pass correction output directories (from .env)
    # If not set, falls back to output_dir/corrections/ at runtime.
    correction_corrected_dir: Path | None = None
    correction_log_dir: Path | None = None
    correction_raw_dir: Path | None = None
    # How often the autonomous CorrectionWorker polls Airtable (seconds).
    # Default: 300 s (5 minutes). Set lower for faster backfill.
    correction_poll_interval_seconds: int = 300

    # Optional: Scout Airtable source (from .env SCOUT_* vars)
    scout_airtable_token: str = ""
    scout_airtable_base_id: str = ""
    scout_airtable_table_name: str = ""
    scout_airtable_view_id: str = ""
    scout_vendor_email_field: str = "Surveyor Email"
    scout_vendor_name_field: str = "Vendor Name"
    scout_site_number_field: str = "Site Number"
    scout_status_field: str = "Processing Status"
    scout_submitted_at_field: str = "Date of Survey"
    scout_submission_id_field: str = "Submission ID"

    @property
    def sql_connection_string(self) -> str:
        """Full pyodbc connection string using Windows trusted auth."""
        return (
            f"DRIVER={{{self.sql_driver}}};"
            f"SERVER={self.sql_server};"
            f"DATABASE={self.sql_database};"
            "Trusted_Connection=yes;"
            "Encrypt=yes;"
            "TrustServerCertificate=yes;"
        )


def _ensure_path(name: str, default: str) -> Path:
    """Return path from env var (or default) and create it if needed."""
    raw = os.getenv(name, default).strip()
    p = Path(raw)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _optional_path(name: str) -> Path | None:
    """Return path from env var only if set; never auto-creates the directory.

    Used for externally-managed directories (e.g. OneDrive folders) that must
    already exist before the pipeline writes to them.
    """
    raw = os.getenv(name, "").strip()
    return Path(raw) if raw else None


_config_singleton: AppConfig | None = None


def load_config() -> AppConfig:
    """Load and cache application configuration.
    
    Sensitive values come from ~/.siteowlqa/config.json
    Non-sensitive values come from .env
    
    Raises:
        EnvironmentError: if user config not found or required values missing
    """
    global _config_singleton
    if _config_singleton is not None:
        return _config_singleton

    # Load user profile config (sensitive data)
    user_cfg = load_user_config()
    if user_cfg is None:
        config_path = get_user_config_path()
        raise EnvironmentError(
            f"\n"
            f"User configuration not found at: {config_path}\n"
            f"\n"
            f"To set up your configuration, run:\n"
            f"  python -m siteowlqa.setup_config\n"
            f"\n"
            f"This will interactively create your configuration file\n"
            f"with your Airtable tokens, SQL credentials, and SMTP settings.\n"
        )

    # Build config with user profile + .env values
    base = Path(__file__).parent.parent.parent  # repo root
    
    # SMTP enabled if user provided server config
    smtp_enabled = bool(user_cfg.smtp_server and user_cfg.smtp_user)
    
    # Reference workbook path
    ref_workbook_path = None
    if user_cfg.reference_workbook_path:
        ref_workbook_path = Path(user_cfg.reference_workbook_path)

    cfg = AppConfig(
        # From user config (sensitive)
        sql_server=user_cfg.sql_server,
        sql_database=user_cfg.sql_database,
        sql_driver=user_cfg.sql_driver,
        airtable_token=user_cfg.airtable_token,
        airtable_base_id=user_cfg.airtable_base_id,
        airtable_table_name=user_cfg.airtable_table_name,
        # Paths (from .env or defaults)
        temp_dir=_ensure_path("TEMP_DIR", str(base / "temp")),
        output_dir=_ensure_path("OUTPUT_DIR", str(base / "output")),
        log_dir=_ensure_path("LOG_DIR", str(base / "logs")),
        archive_dir=_ensure_path("ARCHIVE_DIR", str(base / "archive")),
        submissions_dir=_ensure_path("SUBMISSIONS_DIR", str(base / "archive" / "submissions")),
        # Behavior (from .env)
        reference_source=os.getenv("REFERENCE_SOURCE", "sql").strip().lower() or "sql",
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "60")),
        worker_threads=int(os.getenv("WORKER_THREADS", "3")),
        email_override_to=os.getenv("EMAIL_OVERRIDE_TO", "").strip(),
        # Reference workbook (from user config or .env)
        reference_workbook_path=ref_workbook_path,
        reference_workbook_sheet=user_cfg.reference_workbook_sheet,
        reference_workbook_site_id_column=user_cfg.reference_workbook_site_id_column,
        # SMTP (from user config)
        smtp_enabled=smtp_enabled,
        smtp_server=user_cfg.smtp_server,
        smtp_port=user_cfg.smtp_port,
        smtp_user=user_cfg.smtp_user,
        smtp_pass=user_cfg.smtp_pass,
        from_email=user_cfg.from_email,
        # Element LLM Gateway (from user config)
        element_llm_gateway_url=user_cfg.element_llm_gateway_url,
        element_llm_gateway_api_key=user_cfg.element_llm_gateway_api_key,
        element_llm_gateway_model=user_cfg.element_llm_gateway_model,
        element_llm_gateway_project_id=user_cfg.element_llm_gateway_project_id,
        wmt_ca_path=user_cfg.wmt_ca_path,
        # Post-pass correction output directories (from .env)
        correction_corrected_dir=_optional_path("CORRECTION_CORRECTED_DIR"),
        correction_log_dir=_optional_path("CORRECTION_LOG_DIR"),
        correction_raw_dir=_optional_path("CORRECTION_RAW_DIR"),
        correction_poll_interval_seconds=int(
            os.getenv("CORRECTION_POLL_INTERVAL_SECONDS", "300")
        ),
        # Scout Airtable source (from .env SCOUT_* vars)
        scout_airtable_token=os.getenv("SCOUT_AIRTABLE_TOKEN", "").strip(),
        scout_airtable_base_id=os.getenv("SCOUT_AIRTABLE_BASE_ID", "").strip(),
        scout_airtable_table_name=os.getenv("SCOUT_AIRTABLE_TABLE_NAME", "").strip(),
        scout_airtable_view_id=os.getenv("SCOUT_AIRTABLE_VIEW_ID", "").strip(),
        scout_vendor_email_field=os.getenv("SCOUT_VENDOR_EMAIL_FIELD", "Surveyor Email").strip(),
        scout_vendor_name_field=os.getenv("SCOUT_VENDOR_NAME_FIELD", "Vendor Name").strip(),
        scout_site_number_field=os.getenv("SCOUT_SITE_NUMBER_FIELD", "Site Number").strip(),
        scout_status_field=os.getenv("SCOUT_STATUS_FIELD", "Processing Status").strip(),
        scout_submitted_at_field=os.getenv("SCOUT_SUBMITTED_AT_FIELD", "Date of Survey").strip(),
        scout_submission_id_field=os.getenv("SCOUT_SUBMISSION_ID_FIELD", "Submission ID").strip(),
    )

    _config_singleton = cfg
    log.info(
        "Config loaded from ~/.siteowlqa/config.json — server=%s db=%s table=%s poll=%ds workers=%d",
        cfg.sql_server,
        cfg.sql_database,
        cfg.airtable_table_name,
        cfg.poll_interval_seconds,
        cfg.worker_threads,
    )
    return cfg
