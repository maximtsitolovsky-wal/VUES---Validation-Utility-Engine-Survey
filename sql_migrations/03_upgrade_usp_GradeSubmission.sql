-- =============================================================================
-- Migration 03: Upgrade dbo.usp_GradeSubmission to be SubmissionID-aware
-- =============================================================================
-- Purpose:
--   Add a mandatory @SubmissionID parameter.  The proc must:
--     1. Read ONLY rows from dbo.SubmissionStage WHERE SubmissionID = @SubmissionID
--     2. Compare against dbo.ReferenceExport (shared read — no isolation needed)
--     3. Write results to dbo.SubmissionLog and dbo.QAResults, always recording
--        SubmissionID so results can be read back by the correct worker thread.
--
-- BEFORE APPLYING:
--   Run migrations 01 and 02 first.
--
-- HOW TO USE THIS TEMPLATE:
--   Find every place marked  <<<  EDIT HERE  >>>
--   Replace placeholder logic with your actual grading proc body.
--   The WHERE SubmissionID = @SubmissionID filter on every SubmissionStage
--   read is the single most important change — do NOT remove it.
--
-- After applying, Python will call:
--   EXEC dbo.usp_GradeSubmission @SubmissionID = 'SUB-2026-001'
-- =============================================================================

USE [SiteOwlQA];  -- ← change if needed
GO

CREATE OR ALTER PROCEDURE dbo.usp_GradeSubmission
    @SubmissionID NVARCHAR(200)   -- NEW: scope all operations to this submission
AS
BEGIN
    SET NOCOUNT ON;

    -- -------------------------------------------------------------------------
    -- Safety guard
    -- -------------------------------------------------------------------------
    IF @SubmissionID IS NULL OR LTRIM(RTRIM(@SubmissionID)) = ''
    BEGIN
        RAISERROR(
            'usp_GradeSubmission: @SubmissionID is required.',
            16, 1
        );
        RETURN;
    END

    -- -------------------------------------------------------------------------
    -- Step 1: Clear previous grading results for this submission.
    -- Idempotent: safe to retry.
    -- -------------------------------------------------------------------------
    DELETE FROM dbo.QAResults
    WHERE  SubmissionID = @SubmissionID;

    DELETE FROM dbo.SubmissionLog
    WHERE  SubmissionID = @SubmissionID;

    -- -------------------------------------------------------------------------
    -- Step 2: QA comparison — staged rows vs reference data.
    --
    -- <<<  EDIT HERE  >>>
    -- Replace the INSERT below with your actual grading/comparison logic.
    -- CRITICAL: every read from SubmissionStage MUST include:
    --     WHERE SubmissionID = @SubmissionID
    -- Reads from ReferenceExport are shared across all submissions — that is
    -- safe because ReferenceExport is read-only during grading.
    -- -------------------------------------------------------------------------
    INSERT INTO dbo.QAResults (
        SubmissionID,
        RowNumber,
        -- <<<  EDIT HERE: your QAResults columns  >>>
        ProjectID,
        FieldName,
        SubmittedValue,
        ExpectedValue,
        ErrorDescription
    )
    SELECT
        s.SubmissionID,
        ROW_NUMBER() OVER (PARTITION BY s.SubmissionID ORDER BY s.ProjectID) AS RowNumber,
        -- <<<  EDIT HERE: your grading comparison logic  >>>
        s.ProjectID,
        'ExampleField'               AS FieldName,
        s.Name                       AS SubmittedValue,
        r.ExpectedName               AS ExpectedValue,
        'Value mismatch'             AS ErrorDescription
    FROM       dbo.SubmissionStage   AS s
    INNER JOIN dbo.ReferenceExport   AS r
           ON  s.ProjectID = r.ProjectID  -- <<<  EDIT HERE: your join key(s)  >>>
    WHERE  s.SubmissionID = @SubmissionID  -- ← MANDATORY isolation filter
      AND  s.Name <> r.ExpectedName;       -- <<<  EDIT HERE: your mismatch condition  >>>

    -- -------------------------------------------------------------------------
    -- Step 3: Compute the score and write to SubmissionLog.
    --
    -- Score = 100 - (error_rows / total_rows) * 100
    -- <<<  EDIT HERE  >>>  if your scoring formula is different.
    -- -------------------------------------------------------------------------
    DECLARE @TotalRows  INT;
    DECLARE @ErrorRows  INT;
    DECLARE @Score      FLOAT;
    DECLARE @Status     NVARCHAR(10);
    DECLARE @Message    NVARCHAR(500);

    SELECT @TotalRows = COUNT(*)
    FROM   dbo.SubmissionStage
    WHERE  SubmissionID = @SubmissionID;

    SELECT @ErrorRows = COUNT(*)
    FROM   dbo.QAResults
    WHERE  SubmissionID = @SubmissionID;

    IF @TotalRows = 0
    BEGIN
        SET @Score   = 0;
        SET @Status  = 'ERROR';
        SET @Message = 'No rows found in SubmissionStage for this SubmissionID.';
    END
    ELSE
    BEGIN
        SET @Score  = 100.0 - (CAST(@ErrorRows AS FLOAT) / @TotalRows * 100.0);
        SET @Status = CASE WHEN @Score >= 95.0 THEN 'PASS' ELSE 'FAIL' END;
        SET @Message = CONCAT(
            @Status, ': ', @Score, '% accuracy. ',
            @ErrorRows, ' error(s) out of ', @TotalRows, ' row(s).'
        );
    END

    INSERT INTO dbo.SubmissionLog (SubmissionID, Status, Score, Message, CreatedAt)
    VALUES (@SubmissionID, @Status, @Score, @Message, SYSUTCDATETIME());

    PRINT CONCAT(
        'usp_GradeSubmission: SubmissionID=', @SubmissionID,
        ' | Status=', @Status,
        ' | Score=', @Score,
        ' | Errors=', @ErrorRows, '/', @TotalRows
    );
END
GO

PRINT 'usp_GradeSubmission upgraded successfully.';
GO