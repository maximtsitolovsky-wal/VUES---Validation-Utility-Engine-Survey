-- =============================================================================
-- Migration 08: Widen AbbreviatedName in ReferenceRaw and ReferenceExport
-- =============================================================================
-- Why:
--   The CDFD1 P1 / CDFD1 P2 dataset (Camera&Alarm Ref Data.xlsx, 2026-03-30)
--   contains 1,014 rows where AbbreviatedName exceeds 255 characters (max 302).
--   The old schema used NVARCHAR(255) which caused a right-truncation error
--   during bulk insert.  Widening to NVARCHAR(512) accommodates current data
--   with room for future growth.
--
-- Tables affected:
--   dbo.ReferenceRaw    -- AbbreviatedName NVARCHAR(255) -> NVARCHAR(512)
--   dbo.ReferenceExport -- AbbreviatedName NVARCHAR(255) -> NVARCHAR(512)
--
-- Notes:
--   - dbo.vw_ReferenceNormalized is a view and requires no changes.
--   - No existing data is lost; widening a column is always safe in SQL Server.
--   - Run this BEFORE reload_reference_from_two_sheets.py.
-- =============================================================================

USE [SiteOwlQA];
GO

ALTER TABLE dbo.ReferenceRaw
    ALTER COLUMN AbbreviatedName NVARCHAR(512);
GO

ALTER TABLE dbo.ReferenceExport
    ALTER COLUMN AbbreviatedName NVARCHAR(512);
GO

PRINT 'Migration 08 complete: AbbreviatedName widened to NVARCHAR(512) in ReferenceRaw and ReferenceExport.';
GO
