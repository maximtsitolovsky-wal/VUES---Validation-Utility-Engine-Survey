-- =============================================================================
-- Migration 04: Fix usp_LoadSubmissionFromRaw -- add WHERE SubmissionID filter
-- =============================================================================
-- ROOT CAUSE:
--   The original proc had TWO statements missing WHERE SubmissionID = @SubmissionID:
--
--   1. UPDATE dbo.SubmissionRaw SET [Project ID] = @SiteNumber
--      This rewrote the ProjectID for EVERY row in SubmissionRaw, corrupting
--      all other in-flight submissions' Project IDs.
--
--   2. INSERT INTO dbo.SubmissionStage ... FROM dbo.SubmissionRaw (no WHERE)
--      This loaded ALL rows from SubmissionRaw into SubmissionStage under the
--      current SubmissionID, causing row counts to grow by 310 with every new
--      submission. A submission processed when 7 others were in SubmissionRaw
--      would land 2,170 rows in staging instead of 310, making scoring wrong.
--
-- EFFECT:
--   - Same file passed when SubmissionRaw was clean, failed when rows accumulated
--   - Score degraded over time as staging rows multiplied
--   - ProjectID updates silently corrupted sibling submissions
--
-- FIX:
--   Both statements now scope to WHERE SubmissionID = @SubmissionID
-- =============================================================================

USE [SiteOwlQA];
GO

CREATE OR ALTER PROCEDURE dbo.usp_LoadSubmissionFromRaw
    @SubmissionID NVARCHAR(100),
    @VendorEmail  NVARCHAR(255),
    @SiteNumber   NVARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;

    -- Clear previous staging/results for this submission (idempotent re-run)
    DELETE FROM dbo.SubmissionStage WHERE SubmissionID = @SubmissionID;
    DELETE FROM dbo.QAResults       WHERE SubmissionID = @SubmissionID;
    DELETE FROM dbo.SubmissionLog   WHERE SubmissionID = @SubmissionID;

    -- FIX 1: Scope the ProjectID overwrite to THIS submission's rows only.
    -- Original had no WHERE clause -- it updated every row in SubmissionRaw.
    UPDATE dbo.SubmissionRaw
    SET    [Project ID] = @SiteNumber
    WHERE  SubmissionID = @SubmissionID;           -- <-- CRITICAL fix

    -- Write the initial SubmissionLog entry (StartTime/Score/PassFail filled by GradeSubmission)
    INSERT INTO dbo.SubmissionLog (SubmissionID, VendorEmail, ProjectID, ReceivedTime)
    VALUES (@SubmissionID, @VendorEmail, @SiteNumber, SYSDATETIME());

    -- FIX 2: Scope the staging insert to THIS submission's rows only.
    -- Original had no WHERE clause -- it copied the entire SubmissionRaw table.
    INSERT INTO dbo.SubmissionStage
    (
        SubmissionID,
        VendorEmail,
        ProjectID,
        Name,
        AbbreviatedName,
        Description,
        PartNumber,
        Manufacturer,
        IPAddress,
        MACAddress,
        IPAnalog
    )
    SELECT
        @SubmissionID,
        @VendorEmail,
        UPPER(LTRIM(RTRIM(ISNULL([Project ID],       '')))),
        UPPER(LTRIM(RTRIM(ISNULL([Name],             '')))),
        UPPER(LTRIM(RTRIM(ISNULL([Abbreviated Name], '')))),
        UPPER(LTRIM(RTRIM(ISNULL([Description],      '')))),
        UPPER(LTRIM(RTRIM(ISNULL([Part Number],      '')))),
        UPPER(LTRIM(RTRIM(ISNULL([Manufacturer],     '')))),
        UPPER(LTRIM(RTRIM(ISNULL([IP Address],       '')))),
        UPPER(LTRIM(RTRIM(ISNULL([MAC Address],      '')))),
        UPPER(LTRIM(RTRIM(ISNULL([IP / Analog],      ''))))
    FROM dbo.SubmissionRaw
    WHERE SubmissionID = @SubmissionID;             -- <-- CRITICAL fix

END;
GO

PRINT 'Migration 04 applied: usp_LoadSubmissionFromRaw WHERE clause fixed.';
GO
