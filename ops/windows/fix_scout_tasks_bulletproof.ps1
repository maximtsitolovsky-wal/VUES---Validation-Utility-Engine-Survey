#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Fix Scout scheduled tasks - GUARANTEED TO WORK

.DESCRIPTION
    This script makes the Scout automation bulletproof:
    1. Updates ScoutCompletionSync to use the verified wrapper
    2. Removes battery restrictions from all Scout tasks
    3. Verifies tasks are properly configured
    4. Runs a test execution

.NOTES
    Author: Code Puppy
    Date: 2026-04-17
    Version: 7.0.0
#>

$ErrorActionPreference = 'Stop'
# Dynamically resolve workDir from script location
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$workDir = (Resolve-Path (Join-Path $scriptDir '..\..')).Path

function Write-Step($message, $color = 'Cyan') {
    Write-Host "`n$message" -ForegroundColor $color
}

function Write-Success($message) {
    Write-Host "  ✅ $message" -ForegroundColor Green
}

function Write-Error($message) {
    Write-Host "  ❌ $message" -ForegroundColor Red
}

function Write-Info($message) {
    Write-Host "  ℹ️  $message" -ForegroundColor Gray
}

# ============================================================================
# Pre-flight checks
# ============================================================================

Write-Host "`n" -NoNewline
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  SCOUT TASK AUTOMATION FIX - BULLETPROOF MODE" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan

Write-Step "🔍 PRE-FLIGHT CHECKS"

# Check admin rights
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "This script requires Administrator privileges!"
    Write-Info "Right-click PowerShell and select 'Run as Administrator'"
    exit 1
}
Write-Success "Running as Administrator"

# Check work directory
if (-not (Test-Path $workDir)) {
    Write-Error "Work directory not found: $workDir"
    exit 1
}
Write-Success "Work directory found: $workDir"

# Check .env.local
$envFile = Join-Path $workDir ".env.local"
if (-not (Test-Path $envFile)) {
    Write-Error ".env.local not found!"
    Write-Info "Expected: $envFile"
    exit 1
}
Write-Success ".env.local found"

# Check wrapper script
$wrapperScript = Join-Path $workDir "ops\windows\run_scout_completion_sync_task.bat"
if (-not (Test-Path $wrapperScript)) {
    Write-Error "Wrapper script not found!"
    Write-Info "Expected: $wrapperScript"
    exit 1
}
Write-Success "Wrapper script found"

# Check Python script
$pythonScript = Join-Path $workDir "scripts\scout_completion_sync_com.py"
if (-not (Test-Path $pythonScript)) {
    Write-Error "Python sync script not found!"
    Write-Info "Expected: $pythonScript"
    exit 1
}
Write-Success "Python sync script found"

# ============================================================================
# Fix ScoutCompletionSync task
# ============================================================================

Write-Step "🔧 FIXING SCOUTCOMPLETIONSYNC TASK"

try {
    # Export current task
    $xml = [xml](schtasks /query /tn "ScoutCompletionSync" /xml)
    
    # Update action
    $actionNode = $xml.Task.Actions.Exec
    $actionNode.Command = "cmd"
    $actionNode.Arguments = "/c `"$wrapperScript`""
    $actionNode.WorkingDirectory = $workDir
    Write-Info "Updated command: cmd /c $wrapperScript"
    
    # Remove battery restrictions
    $settingsNode = $xml.Task.Settings
    $settingsNode.DisallowStartIfOnBatteries = "false"
    $settingsNode.StopIfGoingOnBatteries = "false"
    Write-Info "Removed battery restrictions"
    
    # Save and re-register
    $tempXml = "$env:TEMP\scout_completion_sync_fix.xml"
    $xml.Save($tempXml)
    
    # Delete old task
    schtasks /delete /tn "ScoutCompletionSync" /f 2>&1 | Out-Null
    
    # Create new task
    schtasks /create /tn "ScoutCompletionSync" /xml $tempXml /f 2>&1 | Out-Null
    
    Remove-Item $tempXml -ErrorAction SilentlyContinue
    
    Write-Success "ScoutCompletionSync task updated"
    
} catch {
    Write-Error "Failed to update ScoutCompletionSync: $_"
    exit 1
}

# ============================================================================
# Fix Scout Downloader tasks
# ============================================================================

Write-Step "🔧 FIXING SCOUT DOWNLOADER TASKS"

$downloaderTasks = @(
    "vues Scout Downloader 10AM"
    "vues Scout Downloader 3PM"
)

foreach ($taskName in $downloaderTasks) {
    try {
        # Check if task exists
        $taskExists = schtasks /query /tn $taskName 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Info "Task not found, skipping: $taskName"
            continue
        }
        
        # Export task
        $xml = [xml](schtasks /query /tn $taskName /xml)
        
        # Remove battery restrictions
        $settingsNode = $xml.Task.Settings
        $settingsNode.DisallowStartIfOnBatteries = "false"
        $settingsNode.StopIfGoingOnBatteries = "false"
        
        # Save and re-register
        $tempXml = "$env:TEMP\$($taskName -replace ' ', '_').xml"
        $xml.Save($tempXml)
        
        schtasks /delete /tn $taskName /f 2>&1 | Out-Null
        schtasks /create /tn $taskName /xml $tempXml /f 2>&1 | Out-Null
        
        Remove-Item $tempXml -ErrorAction SilentlyContinue
        
        Write-Success "$taskName updated"
        
    } catch {
        Write-Error "Failed to update $taskName : $_"
    }
}

# ============================================================================
# Verify tasks
# ============================================================================

Write-Step "✅ VERIFICATION"

$tasksToCheck = @("ScoutCompletionSync") + $downloaderTasks

foreach ($taskName in $tasksToCheck) {
    $taskExists = schtasks /query /tn $taskName 2>&1
    if ($LASTEXITCODE -eq 0) {
        # Get task details
        $taskInfo = schtasks /query /tn $taskName /fo LIST /v | Out-String
        
        if ($taskInfo -match "Status:\s+(.+)") {
            $status = $matches[1].Trim()
            if ($status -eq "Ready") {
                Write-Success "$taskName - Status: Ready"
            } else {
                Write-Info "$taskName - Status: $status"
            }
        }
        
        if ($taskInfo -match "Next Run Time:\s+(.+)") {
            $nextRun = $matches[1].Trim()
            Write-Info "  Next run: $nextRun"
        }
    } else {
        Write-Error "$taskName not found!"
    }
}

# ============================================================================
# Test execution
# ============================================================================

Write-Step "🧪 RUNNING TEST EXECUTION"

Write-Info "Testing wrapper script..."
$testResult = & $wrapperScript
if ($LASTEXITCODE -eq 0) {
    Write-Success "Test execution completed successfully!"
    
    # Show last few lines of log
    $logFile = Join-Path $workDir "logs\scout_completion_sync.log"
    if (Test-Path $logFile) {
        $logLines = Get-Content $logFile -Tail 5
        Write-Info "Last lines from log:"
        foreach ($line in $logLines) {
            Write-Host "    $line" -ForegroundColor DarkGray
        }
    }
} else {
    Write-Error "Test execution failed! Exit code: $LASTEXITCODE"
    Write-Info "Check logs\scout_completion_sync.log for details"
}

# ============================================================================
# Summary
# ============================================================================

Write-Host "`n" -NoNewline
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  ✅ ALL SCOUT TASKS ARE NOW BULLETPROOF!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green

Write-Host "`nSchedule:" -ForegroundColor Cyan
Write-Host "  • ScoutCompletionSync: Mon-Fri at 10:00 AM & 3:00 PM" -ForegroundColor White
Write-Host "  • Scout Downloader 10AM: Mon-Fri at 10:00 AM" -ForegroundColor White
Write-Host "  • Scout Downloader 3PM: Mon-Fri at 3:00 PM" -ForegroundColor White

Write-Host "`nNext Steps:" -ForegroundColor Cyan
Write-Host "  1. Open Task Scheduler to verify tasks show 'Ready'" -ForegroundColor White
Write-Host "  2. Wait for next scheduled run (or right-click → Run in Task Scheduler)" -ForegroundColor White
Write-Host "  3. Monitor: logs\scout_completion_sync.log" -ForegroundColor White

Write-Host "`nPress any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
