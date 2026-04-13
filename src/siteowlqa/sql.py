"""sql.py — SQL Server access for SiteOwlQA.

Python owns grading logic.
This module only handles:
- connection management
- fetching site-scoped reference rows from SQL Server

No stored-procedure grading orchestration lives here anymore.
That dead weight got taken behind the shed. Politely.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

import pandas as pd
import pyodbc

from siteowlqa.config import AppConfig, VENDOR_GRADE_COLUMNS
from siteowlqa.utils import canon_site_id

log = logging.getLogger(__name__)


@contextmanager
def get_connection(
    cfg: AppConfig,
    autocommit: bool = False,
) -> Generator[pyodbc.Connection, None, None]:
    """Yield a pyodbc connection with automatic commit/rollback."""
    conn = pyodbc.connect(cfg.sql_connection_string, autocommit=autocommit)
    log.debug("SQL connection opened (autocommit=%s)", autocommit)
    try:
        yield conn
        if not autocommit:
            conn.commit()
    except Exception:
        if not autocommit:
            conn.rollback()
        raise
    finally:
        conn.close()
        log.debug("SQL connection closed.")



def fetch_reference_rows_from_sql(
    cfg: AppConfig,
    site_number: str,
) -> pd.DataFrame:
    """Fetch normalized reference rows for one site from SQL Server.

    Returns only the canonical vendor-comparable columns so the Python grader
    can compare vendor files against a site-scoped reference dataset.
    """
    query = """
        SELECT
            ProjectID,
            [Name],
            AbbreviatedName,
            PartNumber,
            Manufacturer,
            IPAddress,
            MACAddress,
            IPAnalog,
            [Description]
        FROM dbo.vw_ReferenceNormalized
        WHERE ProjectID = ?
    """
    with get_connection(cfg, autocommit=False) as conn:
        cur = conn.cursor()
        cur.execute(query, (canon_site_id(site_number),))
        rows = cur.fetchall()
        columns = [col[0] for col in cur.description]

    df = pd.DataFrame.from_records(rows, columns=columns)
    sql_to_vendor = {
        "Name": "Name",
        "AbbreviatedName": "Abbreviated Name",
        "PartNumber": "Part Number",
        "Manufacturer": "Manufacturer",
        "IPAddress": "IP Address",
        "MACAddress": "MAC Address",
        "IPAnalog": "IP / Analog",
        "Description": "Description",
    }
    df = df.rename(columns=sql_to_vendor)
    for col in VENDOR_GRADE_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[list(VENDOR_GRADE_COLUMNS)].fillna("").astype(str)
