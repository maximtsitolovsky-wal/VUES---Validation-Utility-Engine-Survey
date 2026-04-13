from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from siteowlqa.config import load_config
from siteowlqa.sql import get_connection


def _print_result(title: str, rows) -> None:
    print(f"## {title}")
    if not rows:
        print("<none>")
        print()
        return
    for row in rows:
        print(" | ".join("" if value is None else str(value) for value in row))
    print()


def main() -> None:
    cfg = load_config()
    with get_connection(cfg, autocommit=False) as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME LIKE '%Reference%'
               OR TABLE_NAME IN ('SubmissionRaw', 'ReferenceRaw')
            ORDER BY TABLE_SCHEMA, TABLE_NAME
            """
        )
        _print_result("TABLES", cur.fetchall())

        cur.execute(
            """
            SELECT TABLE_SCHEMA, TABLE_NAME
            FROM INFORMATION_SCHEMA.VIEWS
            WHERE TABLE_NAME LIKE '%Reference%'
            ORDER BY TABLE_SCHEMA, TABLE_NAME
            """
        )
        views = cur.fetchall()
        _print_result("VIEWS", views)

        objects_to_describe = [
            ("dbo", "ReferenceRaw"),
            ("dbo", "vw_ReferenceNormalized"),
        ]
        for schema_name, object_name in objects_to_describe:
            cur.execute(
                """
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
                ORDER BY ORDINAL_POSITION
                """,
                (schema_name, object_name),
            )
            _print_result(f"COLUMNS {schema_name}.{object_name}", cur.fetchall())

        cur.execute(
            """
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
            """,
            ("dbo", "ReferenceExport"),
        )
        _print_result("COLUMNS dbo.ReferenceExport", cur.fetchall())

        cur.execute("SELECT COUNT(*) FROM dbo.ReferenceRaw")
        _print_result("COUNT dbo.ReferenceRaw", cur.fetchall())

        cur.execute("SELECT COUNT(*) FROM dbo.ReferenceExport")
        _print_result("COUNT dbo.ReferenceExport", cur.fetchall())

        cur.execute("SELECT COUNT(*) FROM dbo.vw_ReferenceNormalized")
        _print_result("COUNT dbo.vw_ReferenceNormalized", cur.fetchall())

        cur.execute(
            """
            SELECT c.name, c.is_identity, dc.definition
            FROM sys.columns c
            LEFT JOIN sys.default_constraints dc
              ON c.default_object_id = dc.object_id
            WHERE c.object_id = OBJECT_ID('dbo.ReferenceExport')
            ORDER BY c.column_id
            """
        )
        _print_result("METADATA dbo.ReferenceExport", cur.fetchall())

        cur.execute(
            """
            SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.vw_ReferenceNormalized'))
            """
        )
        _print_result("VIEW DEF dbo.vw_ReferenceNormalized", cur.fetchall())

        cur.execute(
            """
            SELECT TOP 5 ProjectID, Name, PartNumber, Manufacturer
            FROM dbo.vw_ReferenceNormalized
            ORDER BY ProjectID, Name
            """
        )
        _print_result("SAMPLE_ROWS dbo.vw_ReferenceNormalized", cur.fetchall())


if __name__ == "__main__":
    main()
