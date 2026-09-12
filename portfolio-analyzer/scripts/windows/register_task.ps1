# Register (or refresh) the Windows scheduled task that runs the daily P&L report.
#   powershell.exe -ExecutionPolicy Bypass -File \\wsl$\Ubuntu\home\kazumasa\projects\portfolio-analyzer\scripts\windows\register_task.ps1
# Runs at 07:30 local time (after the US close, before the Tokyo open); if the PC was off,
# the task runs as soon as it is next on (StartWhenAvailable).
param(
    [string]$Time = "07:30",
    [string]$TaskName = "PortfolioDailyPL"
)
$src = Join-Path $PSScriptRoot "run_daily_pl.cmd"
$dir = Join-Path $env:USERPROFILE "Documents\pl-daily"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$cmd = Join-Path $dir "run_daily_pl.cmd"
Copy-Item -Force $src $cmd

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$cmd`"" -WorkingDirectory $dir
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 20) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName, State | Format-Table -AutoSize
Write-Host "report: $dir\latest.html"
