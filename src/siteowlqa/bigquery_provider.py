"""bigquery_provider.py — BigQuery reference data provider for SiteOwlQA.

One job: fetch site-scoped reference rows from BigQuery and return the exact
same DataFrame shape that fetch_reference_rows_from_sql returns.

Downstream business logic (python_grader, post_pass_correction) never sees
this module — it only sees the normalized DataFrame from reference_data.py.

Column mapping mirrors sql.py exactly so the output contract is identical:
    BQ column       →  VENDOR_GRADE_COLUMNS name
    Name            →  Name
    AbbreviatedName →  Abbreviated Name
    PartNumber      →  Part Number
    Manufacturer    →  Manufacturer
    IPAddress       →  IP Address
    MACAddress      →  MAC Address
    IPAnalog        →  IP / Analog
    Description     →  Description
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

from siteowlqa.config import AppConfig, VENDOR_GRADE_COLUMNS
from siteowlqa.utils import canon_site_id

log = logging.getLogger(__name__)

# BQ column name → canonical VENDOR_GRADE_COLUMNS name.
# Must stay in sync with sql.py's sql_to_vendor map.
_BQ_TO_VENDOR: dict[str, str] = {
    "Name":             "Name",
    "AbbreviatedName":  "Abbreviated Name",
    "PartNumber":       "Part Number",
    "Manufacturer":     "Manufacturer",
    "IPAddress":        "IP Address",
    "MACAddress":       "MAC Address",
    "IPAnalog":         "IP / Analog",
    "Description":      "Description",
}


@dataclass(frozen=True)
class BigQueryConfig:
    """Extracted BQ connection parameters — keeps provider signature clean."""
    project_id: str
    dataset: str
    location: str
    credentials_path: str  # empty string → use Application Default Credentials


def _require_bigquery_deps() -> None:
    """Raise a clear ImportError if google-cloud-bigquery isn't installed."""
    try:
        import google.cloud.bigquery  # noqa: F401
    except ImportError:
        raise ImportError(
            "google-cloud-bigquery is required for REFERENCE_SOURCE=bigquery. "
            "Install it with: pip install google-cloud-bigquery"
        )


def _build_bq_client(bq_cfg: BigQueryConfig) -> "google.cloud.bigquery.Client":
    """Initialize a BigQuery client from config.

    Uses a service account key file when gcp_credentials_path is set.
    Falls back to Application Default Credentials (ADC) when it is blank,
    which covers both local `gcloud auth` and Workload Identity on GCP.
    """
    from google.cloud import bigquery

    if bq_cfg.credentials_path:
        from google.oauth2 import service_account
        credentials = service_account.Credentials.from_service_account_file(
            bq_cfg.credentials_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        log.debug("BigQuery: using service account credentials from %s", bq_cfg.credentials_path)
        return bigquery.Client(project=bq_cfg.project_id, credentials=credentials)

    log.debug("BigQuery: using Application Default Credentials (ADC)")
    return bigquery.Client(project=bq_cfg.project_id)


def _extract_bq_config(cfg: AppConfig) -> BigQueryConfig:
    """Pull BigQuery connection settings out of AppConfig with clear error messages."""
    if not cfg.gcp_project:
        raise EnvironmentError(
            "SITEOWLQA_GCP_PROJECT is required when REFERENCE_SOURCE=bigquery. "
            "Add it to your .env file."
        )
    if not cfg.bigquery_dataset:
        raise EnvironmentError(
            "SITEOWLQA_BIGQUERY_DATASET is required when REFERENCE_SOURCE=bigquery. "
            "Add it to your .env file."
        )
    return BigQueryConfig(
        project_id=cfg.gcp_project,
        dataset=cfg.bigquery_dataset,
        location=cfg.bigquery_location or "US",
        credentials_path=cfg.gcp_credentials_path,
    )


def fetch_reference_rows_from_bigquery(
    cfg: AppConfig,
    site_number: str,
) -> pd.DataFrame:
    """Fetch normalized reference rows for one site from BigQuery.

    Returns a DataFrame with exactly VENDOR_GRADE_COLUMNS, all str, fillna("").
    This is the same contract as fetch_reference_rows_from_sql in sql.py.
    """
    _require_bigquery_deps()
    from google.cloud import bigquery

    bq_cfg = _extract_bq_config(cfg)
    client = _build_bq_client(bq_cfg)
    site_id = canon_site_id(site_number)

    # Parameterized query — same field set as dbo.vw_ReferenceNormalized in sql.py.
    # BigQuery source: device_survey_task_details (GSOC table)
    # Column mapping: BQ uses underscores/different names → alias to match SQL Server schema
    # Note: BQ table uses SelectedSiteID (INTEGER) instead of Project_ID for site filtering
    query = f"""
        SELECT
            CAST(SelectedSiteID AS STRING) AS ProjectID,
            Name,
            Abreviated_ AS AbbreviatedName,
            Part_Number AS PartNumber,
            Manufacturer,
            IP_Address AS IPAddress,
            MACAddress,
            IP___Analog AS IPAnalog,
            Description
        FROM `{bq_cfg.project_id}.{bq_cfg.dataset}.device_survey_task_details`
        WHERE SelectedSiteID = CAST(@project_id AS INT64)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("project_id", "STRING", site_id),
        ],
    )

    log.debug("BigQuery: fetching reference rows for site=%s", site_id)
    df = client.query(query, job_config=job_config, location=bq_cfg.location or None).to_dataframe()

    # Normalize to the exact same output contract as sql.py.
    df = df.rename(columns=_BQ_TO_VENDOR)
    for col in VENDOR_GRADE_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[list(VENDOR_GRADE_COLUMNS)].fillna("").astype(str)
