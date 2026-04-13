-- =============================================================================
-- Migration 07: Treat row-count mismatch as graded mismatch, not processing ERROR
-- =============================================================================
-- Why:
--   Site Number scopes the comparison set, but a row-count mismatch alone does
--   not prove the submission is structurally invalid. If reference rows exist
--   and staging rows exist, grading should produce PASS/FAIL based on actual
--   mismatches instead of short-circuiting to ERROR.
--
-- Policy:
--   - Keep true processing failures as ERROR:
--       * missing @SubmissionID
--       * no stage rows
--       * missing ProjectID in stage
--       * no reference rows for ProjectID
--       * impossible score ranges
--   - Treat stage/reference row-count differences as comparison evidence.
--   - Add a QAResults diagnostic row for row-count mismatch so reporting keeps
--     visibility into the discrepancy.
-- =============================================================================

USE [SiteOwlQA];
GO

CREATE OR ALTER PROCEDURE dbo.usp_GradeSubmission
    @SubmissionID NVARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @ProjectID NVARCHAR(100);
    DECLARE @VendorEmail NVARCHAR(255);
    DECLARE @ExpectedRows INT = 0;
    DECLARE @StageRows INT = 0;
    DECLARE @MismatchRows INT = 0;
    DECLARE @MatchedRows INT = 0;
    DECLARE @Score DECIMAL(6,2) = NULL;
    DECLARE @PassFail NVARCHAR(10) = NULL;
    DECLARE @ErrorMessage NVARCHAR(1000) = NULL;

    IF @SubmissionID IS NULL OR LTRIM(RTRIM(@SubmissionID)) = ''
    BEGIN
        RAISERROR('usp_GradeSubmission: @SubmissionID is required.', 16, 1);
        RETURN;
    END

    SELECT TOP 1
        @ProjectID = ProjectID,
        @VendorEmail = VendorEmail
    FROM dbo.SubmissionStage
    WHERE SubmissionID = @SubmissionID;

    UPDATE dbo.SubmissionLog
    SET StartTime = SYSDATETIME(),
        ErrorMessage = NULL,
        PassFail = NULL,
        Score = NULL,
        EndTime = NULL
    WHERE SubmissionID = @SubmissionID;

    DELETE FROM dbo.QAResults
    WHERE SubmissionID = @SubmissionID;

    SELECT @StageRows = COUNT(*)
    FROM dbo.SubmissionStage
    WHERE SubmissionID = @SubmissionID;

    IF @StageRows = 0
    BEGIN
        SET @PassFail = 'ERROR';
        SET @ErrorMessage = 'No rows found in SubmissionStage for this submission.';
        GOTO Finalize;
    END

    IF @ProjectID IS NULL OR LTRIM(RTRIM(@ProjectID)) = ''
    BEGIN
        SET @PassFail = 'ERROR';
        SET @ErrorMessage = 'SubmissionStage rows are missing ProjectID.';
        GOTO Finalize;
    END

    ;WITH RefRows AS (
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
            *
        FROM dbo.vw_ReferenceNormalized
        WHERE ProjectID = @ProjectID
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
            *
        FROM dbo.vw_SubmissionNormalized
        WHERE SubmissionID = @SubmissionID
    ),
    CompareRows AS (
        SELECT
            COALESCE(r.ProjectID, s.ProjectID) AS ProjectID,
            COALESCE(r.RN, s.RN) AS RN,
            r.[Name] AS RefName,
            s.[Name] AS SubName,
            r.AbbreviatedName AS RefAbbrev,
            s.AbbreviatedName AS SubAbbrev,
            r.[Description] AS RefDesc,
            s.[Description] AS SubDesc,
            r.PartNumber AS RefPart,
            s.PartNumber AS SubPart,
            r.Manufacturer AS RefMan,
            s.Manufacturer AS SubMan,
            r.IPAddress AS RefIP,
            s.IPAddress AS SubIP,
            r.MACAddress AS RefMAC,
            s.MACAddress AS SubMAC,
            r.IPAnalog AS RefAnalog,
            s.IPAnalog AS SubAnalog
        FROM RefRows r
        FULL OUTER JOIN SubRows s
            ON r.ProjectID = s.ProjectID
           AND r.RN = s.RN
    )
    INSERT INTO dbo.QAResults
    (
        SubmissionID,
        ProjectID,
        IssueType,
        Detail
    )
    SELECT
        @SubmissionID,
        ProjectID,
        'ROW_MISMATCH',
        CONCAT(
            'Row ', RN,
            ' REF Name=', ISNULL(RefName, '<blank>'),
            ' | SUB Name=', ISNULL(SubName, '<blank>')
        )
    FROM CompareRows
    WHERE
        ISNULL(RefName, '') <> ISNULL(SubName, '')
        OR ISNULL(NULLIF(RefAbbrev, '0'), '') <> ISNULL(NULLIF(SubAbbrev, '0'), '')
        OR ISNULL(NULLIF(RefDesc, '0'), '') <> ISNULL(NULLIF(SubDesc, '0'), '')
        OR ISNULL(RefPart, '') <> ISNULL(SubPart, '')
        OR ISNULL(RefMan, '') <> ISNULL(SubMan, '')
        OR ISNULL(RefIP, '') <> ISNULL(SubIP, '')
        OR ISNULL(RefMAC, '') <> ISNULL(SubMAC, '')
        OR ISNULL(RefAnalog, '') <> ISNULL(SubAnalog, '');

    SELECT @ExpectedRows = COUNT(*)
    FROM dbo.vw_ReferenceNormalized
    WHERE ProjectID = @ProjectID;

    IF @ExpectedRows = 0
    BEGIN
        SET @PassFail = 'ERROR';
        SET @ErrorMessage = CONCAT('No reference rows found for ProjectID=', @ProjectID, '.');
        GOTO Finalize;
    END

    IF @StageRows <> @ExpectedRows
    BEGIN
        INSERT INTO dbo.QAResults
        (
            SubmissionID,
            ProjectID,
            IssueType,
            Detail
        )
        VALUES
        (
            @SubmissionID,
            @ProjectID,
            'ROW_COUNT_MISMATCH',
            CONCAT(
                'Row-count mismatch for ProjectID=', @ProjectID,
                ' (stage=', @StageRows,
                ', reference=', @ExpectedRows,
                ').'
            )
        );
    END

    SELECT @MismatchRows = COUNT(*)
    FROM dbo.QAResults
    WHERE SubmissionID = @SubmissionID
      AND IssueType = 'ROW_MISMATCH';

    IF @MismatchRows > CASE WHEN @ExpectedRows > @StageRows THEN @ExpectedRows ELSE @StageRows END
    BEGIN
        SET @PassFail = 'ERROR';
        SET @ErrorMessage = CONCAT(
            'Row mismatch count exceeds comparison bounds for ProjectID=', @ProjectID,
            ' (mismatches=', @MismatchRows,
            ', stage=', @StageRows,
            ', reference=', @ExpectedRows,
            ').'
        );
        GOTO Finalize;
    END

    SET @MatchedRows = @ExpectedRows - @MismatchRows;
    IF @MatchedRows < 0
        SET @MatchedRows = 0;

    SET @Score = CAST((@MatchedRows * 100.0) / @ExpectedRows AS DECIMAL(6,2));

    IF @Score < 0 OR @Score > 100
    BEGIN
        SET @PassFail = 'ERROR';
        SET @ErrorMessage = CONCAT('Computed score out of range: ', @Score, '.');
        SET @Score = NULL;
        GOTO Finalize;
    END

    IF @Score >= 95
        SET @PassFail = 'PASS';
    ELSE
        SET @PassFail = 'FAIL';

Finalize:
    UPDATE dbo.SubmissionLog
    SET
        Score = CASE WHEN @PassFail = 'FAIL' THEN @Score ELSE NULL END,
        PassFail = @PassFail,
        ErrorMessage = @ErrorMessage,
        EndTime = SYSDATETIME()
    WHERE SubmissionID = @SubmissionID;
END;
GO

PRINT 'Migration 07 applied: row-count mismatch is now graded, not fatal.';
GO
