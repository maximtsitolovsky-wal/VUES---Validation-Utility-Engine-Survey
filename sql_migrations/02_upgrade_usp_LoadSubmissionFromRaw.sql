-- =============================================================================
-- Migration 02: Upgrade dbo.usp_LoadSubmissionFromRaw to be SubmissionID-aware
-- =============================================================================
-- Purpose:
--   Add a mandatory @SubmissionID parameter.  The proc must:
--     1. Read ONLY rows from dbo.SubmissionRaw WHERE SubmissionID = @SubmissionID
--     2. Write those rows into dbo.SubmissionStage, populating SubmissionID
--
-- BEFORE APPLYING:
--   Run migration 01 first so dbo.SubmissionStage has the SubmissionID column.
--
-- HOW TO USE THIS TEMPLATE:
--   Find every place marked  <<<  EDIT HERE  >>>
--   Replace the placeholder SELECT/INSERT with your actual proc body,
--   adding WHERE SubmissionID = @SubmissionID to every read from SubmissionRaw
--   and writing @SubmissionID into SubmissionStage.
--
-- After applying, Python will call:
--   EXEC dbo.usp_LoadSubmissionFromRaw @SubmissionID = 'SUB-2026-001'
-- =============================================================================

USE [SiteOwlQA];  -- ← change if needed
GO

CREATE OR ALTER PROCEDURE dbo.usp_LoadSubmissionFromRaw
    @SubmissionID NVARCHAR(200)   -- NEW: scope all operations to this submission
AS
BEGIN
    SET NOCOUNT ON;

    -- -------------------------------------------------------------------------
    -- Safety guard: reject empty SubmissionID to prevent accidental bulk ops.
    -- -------------------------------------------------------------------------
    IF @SubmissionID IS NULL OR LTRIM(RTRIM(@SubmissionID)) = ''
    BEGIN
        RAISERROR(
            'usp_LoadSubmissionFromRaw: @SubmissionID is required.',
            16, 1
        );
        RETURN;
    END

    -- -------------------------------------------------------------------------
    -- Step 1: Clear any existing staging rows for this submission.
    -- This makes the proc idempotent — safe to retry without duplicates.
    -- -------------------------------------------------------------------------
    DELETE FROM dbo.SubmissionStage
    WHERE  SubmissionID = @SubmissionID;

    -- -------------------------------------------------------------------------
    -- Step 2: Load from SubmissionRaw into SubmissionStage.
    --
    -- <<<  EDIT HERE  >>>
    -- Replace this INSERT with your actual column mapping.
    -- The WHERE clause below is mandatory — do NOT remove it.
    -- Make sure SubmissionID is propagated into SubmissionStage.
    -- -------------------------------------------------------------------------
    INSERT INTO dbo.SubmissionStage (
        -- <<<  EDIT HERE: list your SubmissionStage columns  >>>
        ProjectID,
        PlanID,
        Name,
        AbbreviatedName,
        PartNumber,
        Manufacturer,
        IPAddress,
        MACAddress,
        IPAnalog,
        Description,
        SubmissionID   -- carry forward for downstream filtering
    )
    SELECT
        -- <<<  EDIT HERE: map columns from SubmissionRaw  >>>
        r.ProjectID,
        r.PlanID,
        r.Name,
        r.AbbreviatedName,
        r.PartNumber,
        r.Manufacturer,
        r.IPAddress,
        r.MACAddress,
        r.IPAnalog,
        r.Description,
        r.SubmissionID
    FROM   dbo.SubmissionRaw AS r
    WHERE  r.SubmissionID = @SubmissionID;   -- ← MANDATORY isolation filter

    -- -------------------------------------------------------------------------
    -- Step 3: Any additional transformation logic your original proc had.
    --
    -- <<<  EDIT HERE  >>>
    -- Add UPDATE / computed columns / business rule fixes here.
    -- Remember to scope every table access to WHERE SubmissionID = @SubmissionID.
    -- -------------------------------------------------------------------------

    PRINT CONCAT(
        'usp_LoadSubmissionFromRaw: loaded ',
        @@ROWCOUNT,
        ' row(s) for SubmissionID=', @SubmissionID
    );
END
GO

PRINT 'usp_LoadSubmissionFromRaw upgraded successfully.';
GO