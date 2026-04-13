-- =============================================================================
-- Migration 01: Add SubmissionID column to dbo.SubmissionStage
-- =============================================================================
-- Purpose:
--   usp_LoadSubmissionFromRaw reads from SubmissionRaw and populates
--   SubmissionStage.  For concurrent per-submission isolation, SubmissionStage
--   must carry the SubmissionID so that usp_GradeSubmission can filter to
--   only grade the rows belonging to one submission at a time.
--
-- Run this ONCE before running migration 02 or 03.
-- Safe to run on a live database — ALTER TABLE ADD COLUMN is online in SQL Server.
-- =============================================================================

USE [SiteOwlQA];  -- ← change if your database name is different
GO

-- Only add the column if it does not already exist.
IF NOT EXISTS (
    SELECT 1
    FROM   sys.columns
    WHERE  object_id = OBJECT_ID('dbo.SubmissionStage')
      AND  name      = 'SubmissionID'
)
BEGIN
    ALTER TABLE dbo.SubmissionStage
        ADD SubmissionID NVARCHAR(200) NULL;

    PRINT 'Column SubmissionID added to dbo.SubmissionStage.';
END
ELSE
BEGIN
    PRINT 'Column SubmissionID already exists on dbo.SubmissionStage — skipped.';
END
GO

-- Create an index so the WHERE SubmissionID = ? filter is fast.
IF NOT EXISTS (
    SELECT 1
    FROM   sys.indexes
    WHERE  object_id = OBJECT_ID('dbo.SubmissionStage')
      AND  name      = 'IX_SubmissionStage_SubmissionID'
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_SubmissionStage_SubmissionID
        ON dbo.SubmissionStage (SubmissionID);

    PRINT 'Index IX_SubmissionStage_SubmissionID created.';
END
GO