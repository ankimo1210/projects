# FlightGear Setup (Windows 11 + WSL2)

FlightGear runs **natively on Windows** (do not attempt desktop FlightGear
inside WSL). The bridge (Node) can run in WSL2 or on Windows.

## 1. Install FlightGear (Windows)

1. Download from <https://www.flightgear.org/download/> (2020.3 LTS or newer).
2. Install a 737 NG aircraft package, e.g. **737-800YV** (FlightGear
   launcher → Aircraft → search "737", or clone into
   `%USERPROFILE%\FlightGear\Aircraft`). Any FG 737 NG model works; the
   property map targets standard FG properties where possible.
3. First run may download KSFO scenery via TerraSync — allow it.

## 2. Launch with the bridge interface enabled

```powershell
cd \\wsl.localhost\<distro>\home\<user>\projects\b737-ops-sim   # or a Windows checkout
.\scripts\launch-flightgear.ps1
# custom install path / aircraft:
.\scripts\launch-flightgear.ps1 -FgfsPath "D:\Games\FlightGear\bin\fgfs.exe" -Aircraft 737-800YV
```

The script starts FlightGear at **KSFO 28R**, engines running, with:
- `--httpd=5500` — the WebSocket property interface the bridge uses
  (`ws://<host>:5500/PropertyListener`)
- `--telnet=...5401` — fallback/diagnostic interface

## 3. Networking: WSL2 → Windows

WSL2 **NAT mode** (this machine, verified 2026-08-02): the Windows host is
the default gateway as seen from WSL:

```bash
./scripts/fg-host-ip.sh        # prints e.g. 192.168.16.1
```

Two Windows-side requirements:

1. **FlightGear must listen beyond localhost.** FlightGear's httpd binds all
   interfaces by default; if you cannot connect, verify with
   `curl http://<windows-ip>:5500/json/position` from WSL.
2. **Windows Defender Firewall** must allow inbound TCP 5500 for fgfs.exe
   (accept the prompt on first launch, or add a rule:
   `New-NetFirewallRule -DisplayName "FlightGear httpd" -Direction Inbound -Protocol TCP -LocalPort 5500 -Action Allow`).

If you use **mirrored networking** (`.wslconfig` → `networkingMode=mirrored`),
`FG_HOST=127.0.0.1` works directly.

## 4. Verify the connection (Phase-0 diagnostic)

```bash
FG_HOST=$(./scripts/fg-host-ip.sh) pnpm fg:diagnostic
```

Expected output: property reads (aircraft, position, airspeed) and a
confirmed harmless write (taxi light toggled and restored). Exit code 0.

## 5. Run the app against FlightGear

```bash
FG_HOST=$(./scripts/fg-host-ip.sh) pnpm dev:fg
```

The bridge retries every 3 s until FlightGear is up, and reconnects if
FlightGear restarts. The browser shows the backend mode in the status bar.

## Property map verification

`config/flightgear/737-800-property-map.json` is the single source of truth
for FG property paths. Core FG paths (position/velocities/controls) are
standard; entries marked `AIRCRAFT-MODEL-DEPENDENT` (MCP, autobrake,
speedbrake-armed, reverser, FD) must be verified against your installed 737
package:

1. Open FlightGear's internal property browser (menu → Debug → Browse
   Internal Properties) or `http://localhost:5500/props/`.
2. Find the actual path (e.g. the model's CMD A property).
3. Update the JSON map — no code changes needed. Bump `version`.

## Known limitations

- `resetScenario` over the property interface is best-effort; restart
  FlightGear with the launch script for a clean scenario start.
- The FG httpd WebSocket message shapes were implemented against FlightGear's
  documented Phi interface and validated with an emulating test server; if a
  specific FG build differs, `pnpm fg:diagnostic` will show it — adapter code
  lives in `packages/flightgear-adapter/src/flightgear/`.
