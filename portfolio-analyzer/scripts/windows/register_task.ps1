# Register (or refresh) the Windows scheduled tasks that run the P&L report and mail it.
#   powershell.exe -ExecutionPolicy Bypass -File \\wsl$\Ubuntu\home\kazumasa\projects\portfolio-analyzer\scripts\windows\register_task.ps1
# Two runs a day:
#   PortfolioPLTokyo  Mon-Fri 16:30  after the Tokyo close; New York is still at its previous
#                                    close, so US holdings show only the move in USD/JPY.
#   PortfolioDailyPL  Tue-Sat 07:30  after the New York close: the previous day in full.
# The morning run catches up if the PC was off (StartWhenAvailable); a missed evening run is
# skipped, since the morning one supersedes it.
param(
    [string]$EveningTime = "16:30",
    [string]$MorningTime = "07:30"
)
$src = Join-Path $PSScriptRoot "run_daily_pl.cmd"
$dir = Join-Path $env:USERPROFILE "Documents\pl-daily"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$cmd = Join-Path $dir "run_daily_pl.cmd"
Copy-Item -Force $src $cmd

function Register-Run([string]$Name, [string]$Edition, [string]$At, [string[]]$Days, [bool]$CatchUp) {
    $action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$cmd`" --edition $Edition" -WorkingDirectory $dir
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Days -At $At
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable:$CatchUp -ExecutionTimeLimit (New-TimeSpan -Minutes 20) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
}

Register-Run "PortfolioPLTokyo" "tokyo" $EveningTime @("Monday", "Tuesday", "Wednesday", "Thursday", "Friday") $false
Register-Run "PortfolioDailyPL" "ny" $MorningTime @("Tuesday", "Wednesday", "Thursday", "Friday", "Saturday") $true
Get-ScheduledTask -TaskName "PortfolioPLTokyo", "PortfolioDailyPL" | Get-ScheduledTaskInfo | Select-Object TaskName, NextRunTime | Format-Table -AutoSize
Write-Host "report: $dir\latest.html"
