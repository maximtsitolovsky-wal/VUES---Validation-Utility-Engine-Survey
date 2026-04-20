# register_task.ps1 — registers VUES as a Windows Scheduled Task
# Requires admin. Launched automatically by INSTALL_TASK.bat via UAC elevation.
$ErrorActionPreference = 'Stop'

$taskName    = 'VUES Pipeline'
$taskUser    = 'HOMEOFFICE\vn59j7j'
$batPath     = 'C:\VUES\ops\windows\run_vues.bat'

Write-Host ''
Write-Host '================================================'
Write-Host '  VUES - Task Scheduler Setup'
Write-Host '================================================'
Write-Host ''
Write-Host "User:    $taskUser"
Write-Host "Task:    $taskName"
Write-Host "Trigger: At logon + 90s delay (OneDrive sync time)"
Write-Host ''

$action = New-ScheduledTaskAction `
    -Execute 'C:\Windows\System32\cmd.exe' `
    -Argument "/c $batPath" `
    -WorkingDirectory 'C:\VUES'

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $taskUser
$trigger.Delay = 'PT1M30S'

$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -RestartCount 10 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -DontStopOnIdleEnd

$principal = New-ScheduledTaskPrincipal `
    -UserId $taskUser `
    -LogonType Interactive `
    -RunLevel Highest

# Remove old task
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
Write-Host 'Removed old task (if any).'

$task = Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description 'VUES: auto-grades vendor submissions. Polls every 5s. Starts 90s after logon.'

Write-Host ''
Write-Host "SUCCESS: Task '$($task.TaskName)' registered!"
Write-Host "Status:  $($task.State)"
Write-Host ''
Write-Host 'The pipeline will auto-start 90 seconds after your next login.'
Write-Host ''
Read-Host 'Press ENTER to close'
