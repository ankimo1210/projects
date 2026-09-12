@echo off
rem Daily mark-to-market P&L report: runs the WSL script and drops the HTML in Documents\pl-daily.
rem Registered by register_task.ps1; safe to run by hand.
setlocal
set OUTDIR=%USERPROFILE%\Documents\pl-daily
if not exist "%OUTDIR%" mkdir "%OUTDIR%"
echo [%date% %time%] start >> "%OUTDIR%\run.log"
wsl.exe -d Ubuntu -u kazumasa -- bash -lc "cd /home/kazumasa/projects && /home/kazumasa/.local/bin/uv run --no-sync python portfolio-analyzer/scripts/daily_pl_report.py --copy-to '/mnt/c/Users/%USERNAME%/Documents/pl-daily'" >> "%OUTDIR%\run.log" 2>&1
echo [%date% %time%] exit %ERRORLEVEL% >> "%OUTDIR%\run.log"
endlocal
