# Launch FlightGear on Windows configured for the B737 Ops Trainer bridge.
# Run from PowerShell:  .\scripts\launch-flightgear.ps1
# Prereq: FlightGear 2020.3+ installed (https://www.flightgear.org/download/)
#         and a 737-800 aircraft package (e.g. 737-800YV) installed via the
#         built-in launcher or into %USERPROFILE%\FlightGear\Aircraft.
# See docs/FLIGHTGEAR_SETUP.md for details, including WSL2 networking.

param(
    # Path to fgfs.exe — adjust if FlightGear is installed elsewhere
    [string]$FgfsPath = "C:\Program Files\FlightGear 2024.1\bin\fgfs.exe",
    # Aircraft id: use one installed 737 NG package; fallback c172p proves the pipe
    [string]$Aircraft = "737-800YV",
    [int]$HttpPort = 5500,
    [string]$Airport = "KSFO",
    [string]$Runway = "28R"
)

if (-not (Test-Path $FgfsPath)) {
    Write-Host "fgfs.exe not found at: $FgfsPath" -ForegroundColor Red
    Write-Host "Pass -FgfsPath 'C:\path\to\fgfs.exe' or edit this script." -ForegroundColor Yellow
    exit 1
}

# --httpd exposes the property WebSocket the bridge connects to.
# --telnet is a fallback/diagnostic interface.
$fgArgs = @(
    "--aircraft=$Aircraft",
    "--airport=$Airport",
    "--runway=$Runway",
    "--httpd=$HttpPort",
    "--telnet=socket,bi,20,localhost,5401,tcp",
    "--timeofday=noon",
    "--disable-random-objects",
    "--prop:/engines/engine[0]/running=true",
    "--prop:/engines/engine[1]/running=true"
)

Write-Host "Launching FlightGear: $Aircraft at $Airport $Runway (httpd :$HttpPort)" -ForegroundColor Green
Write-Host "Bridge (WSL2): set FG_HOST to the Windows host IP, FG_HTTP_PORT=$HttpPort"
Write-Host "Bridge (Windows): FG_HOST=127.0.0.1"

& $FgfsPath @fgArgs
