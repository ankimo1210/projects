# run_first_scan.ps1 — First-time scan helper for LINE backup exporter
# Usage: Right-click > Run with PowerShell, or: .\scripts\run_first_scan.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== LINE Backup Exporter — First Scan ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: list available backups
Write-Host "[1/3] Listing iPhone backups..." -ForegroundColor Yellow
python -m line_backup_exporter.cli list-backups
Write-Host ""

# Step 2: ask user for backup dir
$backupDir = Read-Host "Enter the full path of the backup directory to scan (copy from above)"
if (-not $backupDir) {
    Write-Host "No path entered. Exiting." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $backupDir)) {
    Write-Host "Path does not exist: $backupDir" -ForegroundColor Red
    exit 1
}

# Step 3: run scan-line
$outDir = "output"
Write-Host ""
Write-Host "[2/3] Running scan-line..." -ForegroundColor Yellow
python -m line_backup_exporter.cli scan-line --backup-dir "$backupDir" --out "$outDir"

Write-Host ""
Write-Host "[3/3] Done. Check the output\ directory for results." -ForegroundColor Green
Write-Host "Next step: run extract-candidates to copy SQLite files."
Write-Host "  python -m line_backup_exporter.cli extract-candidates --backup-dir `"$backupDir`" --manifest-csv output\manifest_line_files.csv --out output"
