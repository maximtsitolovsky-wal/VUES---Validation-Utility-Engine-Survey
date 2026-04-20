#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Fix Scout scheduled tasks: update wrapper script and remove battery restrictions

.DESCRIPTION
    This script fixes two issues with the Scout automation tasks:
    1. Updates ScoutCompletionSync to use the new wrapper that loads .env.local
    2. Removes "Stop On Battery Mode" from all Scout tasks so they run on battery
#>

$ErrorActionPreference = 'Stop'

# Dynamically resolve workDir from script location
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$workDir = (Resolve-Path (Join-Path $scriptDir '..\..')).Path

Write-Host "=== Fixing Scout Scheduled Tasks ===" -ForegroundColor Cyan
Write-Host ""

# Define tasks to fix
$tasks = @(
    "ScoutCompletionSync"
    "vues Scout Downloader 10AM"
    "vues Scout Downloader 3PM"
)

# Get current user
$currentUser = "$env:USERDOMAIN\$env:USERNAME"

# Fix ScoutCompletionSync wrapper
Write-Host "[1/2] Updating ScoutCompletionSync wrapper..." -ForegroundColor Yellow
$xml = [xml](schtasks /query /tn "ScoutCompletionSync" /xml)

# Update the command
$actionNode = $xml.Task.Actions.Exec
$actionNode.Command = "cmd"
$actionNode.Arguments = "/c `"$workDir\ops\windows\run_scout_completion_sync_task.bat`""
$actionNode.WorkingDirectory = $workDir

# Remove battery restrictions
$settingsNode = $xml.Task.Settings
$settingsNode.DisallowStartIfOnBatteries = "false"
$settingsNode.StopIfGoingOnBatteries = "false"

# Save to temp file and re-register
$tempXml = "$env:TEMP\scout_completion_sync.xml"
$xml.Save($tempXml)

Write-Host "  Re-registering task..." -ForegroundColor Gray
schtasks /delete /tn "ScoutCompletionSync" /f | Out-Null
schtasks /create /tn "ScoutCompletionSync" /xml $tempXml /ru $currentUser | Out-Null
Remove-Item $tempXml

Write-Host "  [OK] ScoutCompletionSync updated" -ForegroundColor Green

# Fix Scout Downloader tasks (just remove battery restrictions)
Write-Host ""
Write-Host "[2/2] Removing battery restrictions from Scout Downloaders..." -ForegroundColor Yellow

foreach ($taskName in $tasks[1..2]) {
    Write-Host "  Processing: $taskName" -ForegroundColor Gray
    
    $xml = [xml](schtasks /query /tn $taskName /xml)
    
    # Remove battery restrictions
    $settingsNode = $xml.Task.Settings
    $settingsNode.DisallowStartIfOnBatteries = "false"
    $settingsNode.StopIfGoingOnBatteries = "false"
    
    # Save and re-register
    $tempXml = "$env:TEMP\$($taskName -replace ' ', '_').xml"
    $xml.Save($tempXml)
    
    schtasks /delete /tn $taskName /f | Out-Null
    schtasks /create /tn $taskName /xml $tempXml /ru $currentUser | Out-Null
    Remove-Item $tempXml
    
    Write-Host "    [OK] $taskName updated" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== All tasks fixed! ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Verify .env.local exists with your Scout API key"
Write-Host "  2. Run a manual test: ops\windows\run_scout_completion_sync.bat"
Write-Host "  3. Check Task Scheduler to verify tasks show 'Ready'"
Write-Host ""
