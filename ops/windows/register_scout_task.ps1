# register_scout_task.ps1
# Registers the Scout Downloader as a Windows Scheduled Task.
# Runs Mon-Fri at 10:00 AM and 3:00 PM.
# Requires admin. Run this once — re-run to update.
#
# RISK-003 mitigation: keeps local image copies so Airtable CDN expiry
# never causes data loss.

$ErrorActionPreference = 'Stop'

$taskName = 'SiteOwlQA Scout Downloader'
$taskUser = 'HOMEOFFICE\vn59j7j'
$batPath  = 'C:\SiteOwlQA_App\ops\windows\run_scout_downloader.bat'

Write-Host ''
Write-Host '================================================'
Write-Host '  Scout Downloader - Task Scheduler Setup'
Write-Host '================================================'
Write-Host ''
Write-Host "User:     $taskUser"
Write-Host "Task:     $taskName"
Write-Host "Triggers: Mon-Fri 10:00 AM  |  Mon-Fri 3:00 PM"
Write-Host ''

$action = New-ScheduledTaskAction `
    -Execute 'C:\Windows\System32\cmd.exe' `
    -Argument "/c $batPath" `
    -WorkingDirectory 'C:\SiteOwlQA_App'

# Two triggers: 10 AM and 3 PM, both Mon-Fri
$trigger10am = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday `
    -At '10:00AM'

$trigger3pm = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday `
    -At '3:00PM'

$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -DontStopOnIdleEnd `
    -RunOnlyIfNetworkAvailable

$principal = New-ScheduledTaskPrincipal `
    -UserId $taskUser `
    -LogonType Interactive `
    -RunLevel Highest

# Remove old version if it exists
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
Write-Host 'Removed old task (if any).'

$task = Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger10am, $trigger3pm `
    -Settings $settings `
    -Principal $principal `
    -Description 'Scout Downloader: saves Scout Airtable images locally Mon-Fri 10AM+3PM. RISK-003 mitigation.'

Write-Host ''
Write-Host "SUCCESS: Task '$($task.TaskName)' registered!"
Write-Host "Status:  $($task.State)"
Write-Host ''
Write-Host 'Next runs:'
$info = Get-ScheduledTaskInfo -TaskName $taskName
Write-Host "  Next run time: $($info.NextRunTime)"
Write-Host ''
Read-Host 'Press ENTER to close'
