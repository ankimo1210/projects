@echo off
rem Daily mark-to-market P&L report: runs the WSL script and drops the HTML in Documents\pl-daily.
rem Registered by register_task.ps1; safe to run by hand. Arguments go to the script (e.g. --edition tokyo).
rem Email is opt-in: put PL_MAIL_TO / PL_SMTP_USER / PL_SMTP_PASS in ~/.config/pl-daily.env (WSL side).
rem wsl.exe hands the command line to the default shell first, so $ is escaped to survive until the inner bash.
setlocal
set OUTDIR=%USERPROFILE%\Documents\pl-daily
set PRIVATE_WSL=/mnt/c/Users/%USERNAME%/.local/share/repo-private/projects/portfolio-analyzer
if not exist "%OUTDIR%" mkdir "%OUTDIR%"
echo [%date% %time%] start >> "%OUTDIR%\run.log"
rem Installed locally by the private-data setup; only shared input files are refreshed.
if exist "%USERPROFILE%\.local\bin\private-inputs-sync.cmd" (
  call "%USERPROFILE%\.local\bin\private-inputs-sync.cmd" >> "%OUTDIR%\run.log" 2>&1
  if errorlevel 1 exit /b 1
)
wsl.exe -d Ubuntu -u kazumasa -- bash -lc "cd /home/kazumasa/projects && if [ -f ~/.config/pl-daily.env ]; then set -a; . ~/.config/pl-daily.env; set +a; fi; /home/kazumasa/.local/bin/uv run --no-sync python portfolio-analyzer/scripts/daily_pl_report.py --copy-to '/mnt/c/Users/%USERNAME%/Documents/pl-daily' %* \${PL_MAIL_TO:+--email \$PL_MAIL_TO}" >> "%OUTDIR%\run.log" 2>&1
set REPORT_EXIT=%ERRORLEVEL%
if not "%REPORT_EXIT%"=="0" goto finish
if not exist "%USERPROFILE%\.local\bin\private-inputs-sync.cmd" goto finish
rem Refresh the allocation dashboard too; retain the original account snapshot.
wsl.exe -d Ubuntu -u kazumasa -- bash -lc "cd /home/kazumasa/projects && /home/kazumasa/.local/bin/uv run --no-sync python portfolio-analyzer/scripts/reprice_snapshot.py --output '%PRIVATE_WSL%/data/portfolio-repriced.private.json' && /home/kazumasa/.local/bin/uv run --no-sync python portfolio-analyzer/scripts/build_dashboard.py --input '%PRIVATE_WSL%/data/portfolio-repriced.private.json' --ledger '%PRIVATE_WSL%/data/ibkr-ledger.private.json' --output '%PRIVATE_WSL%/reports/portfolio-dashboard.html'" >> "%OUTDIR%\run.log" 2>&1
set REPORT_EXIT=%ERRORLEVEL%
if not "%REPORT_EXIT%"=="0" goto finish
call "%USERPROFILE%\.local\bin\private-inputs-sync.cmd" --reports >> "%OUTDIR%\run.log" 2>&1
set REPORT_EXIT=%ERRORLEVEL%
:finish
echo [%date% %time%] exit %REPORT_EXIT% >> "%OUTDIR%\run.log"
endlocal & exit /b %REPORT_EXIT%
