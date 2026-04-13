"""Inspect field-level mismatch counts for specific submissions/sites."""

from config import load_config
from sql import get_connection

cfg = load_config()

SITE9_SUBMISSION = "rec2Z5F7PsflUVJ9v"
OLD_SITE = "3445"

SITE9_SQL = """
WITH RefRows AS (
    SELECT
        ROW_NUMBER() OVER (
            PARTITION BY ProjectID
            ORDER BY
                ISNULL([Name], ''),
                ISNULL(AbbreviatedName, ''),
                ISNULL([Description], ''),
                ISNULL(PartNumber, ''),
                ISNULL(Manufacturer, ''),
                ISNULL(IPAddress, ''),
                ISNULL(MACAddress, ''),
                ISNULL(IPAnalog, '')
        ) AS RN,
        ProjectID, [Name], AbbreviatedName, [Description],
        PartNumber, Manufacturer, IPAddress, MACAddress, IPAnalog
    FROM dbo.vw_ReferenceNormalized
    WHERE ProjectID = '9'
),
SubRows AS (
    SELECT
        ROW_NUMBER() OVER (
            PARTITION BY ProjectID
            ORDER BY
                ISNULL([Name], ''),
                ISNULL(AbbreviatedName, ''),
                ISNULL([Description], ''),
                ISNULL(PartNumber, ''),
                ISNULL(Manufacturer, ''),
                ISNULL(IPAddress, ''),
                ISNULL(MACAddress, ''),
                ISNULL(IPAnalog, '')
        ) AS RN,
        ProjectID, [Name], AbbreviatedName, [Description],
        PartNumber, Manufacturer, IPAddress, MACAddress, IPAnalog
    FROM dbo.vw_SubmissionNormalized
    WHERE SubmissionID = ?
)
SELECT
    SUM(CASE WHEN ISNULL(r.[Name], '') <> ISNULL(s.[Name], '') THEN 1 ELSE 0 END) AS name_mm,
    SUM(CASE WHEN ISNULL(r.AbbreviatedName, '') <> ISNULL(s.AbbreviatedName, '') THEN 1 ELSE 0 END) AS abbrev_mm,
    SUM(CASE WHEN ISNULL(r.[Description], '') <> ISNULL(s.[Description], '') THEN 1 ELSE 0 END) AS desc_mm,
    SUM(CASE WHEN ISNULL(r.PartNumber, '') <> ISNULL(s.PartNumber, '') THEN 1 ELSE 0 END) AS part_mm,
    SUM(CASE WHEN ISNULL(r.Manufacturer, '') <> ISNULL(s.Manufacturer, '') THEN 1 ELSE 0 END) AS man_mm,
    SUM(CASE WHEN ISNULL(r.IPAddress, '') <> ISNULL(s.IPAddress, '') THEN 1 ELSE 0 END) AS ip_mm,
    SUM(CASE WHEN ISNULL(r.MACAddress, '') <> ISNULL(s.MACAddress, '') THEN 1 ELSE 0 END) AS mac_mm,
    SUM(CASE WHEN ISNULL(r.IPAnalog, '') <> ISNULL(s.IPAnalog, '') THEN 1 ELSE 0 END) AS analog_mm
FROM RefRows r
FULL OUTER JOIN SubRows s
    ON r.ProjectID = s.ProjectID
   AND r.RN = s.RN;
"""

OLD_SITE_SQL = """
SELECT
    (SELECT COUNT(*) FROM dbo.vw_ReferenceNormalized WHERE ProjectID = ?) AS ref_rows,
    (SELECT COUNT(*) FROM dbo.SubmissionStage WHERE SubmissionID = ?) AS stage_rows,
    (SELECT COUNT(*) FROM dbo.vw_SubmissionNormalized WHERE SubmissionID = ?) AS normalized_rows;
"""

with get_connection(cfg, autocommit=False) as conn:
    cur = conn.cursor()

    print("=== Site 9 field-level mismatch counts ===")
    cur.execute(SITE9_SQL, (SITE9_SUBMISSION,))
    row = cur.fetchone()
    print({
        "name_mm": row[0],
        "abbrev_mm": row[1],
        "desc_mm": row[2],
        "part_mm": row[3],
        "man_mm": row[4],
        "ip_mm": row[5],
        "mac_mm": row[6],
        "analog_mm": row[7],
    })

    print()
    print("=== Old site structural counts (3445 / recLErw4KnAkusCqm) ===")
    cur.execute(OLD_SITE_SQL, (OLD_SITE, "recLErw4KnAkusCqm", "recLErw4KnAkusCqm"))
    old = cur.fetchone()
    print({
        "ref_rows": old[0],
        "stage_rows": old[1],
        "normalized_rows": old[2],
    })
