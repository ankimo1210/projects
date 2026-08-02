# Troubleshooting

## The browser shows "Bridge disconnected"

- Is the bridge running? `curl http://127.0.0.1:8737/health` → `{"ok":true}`.
- Started via `pnpm dev`? Check the `bridge` colored output for errors.
- Port conflict: set `BRIDGE_PORT=8738` (and `VITE_BRIDGE_URL=ws://127.0.0.1:8738/ws`).
- The overlay auto-retries every 1.5 s — no reload needed once the bridge is up.

## Mock mode: aircraft won't move

- Parking brake is set at scenario start — release it (`P` or PARK button).
- The model holds position at idle thrust with the brake set by design.

## FlightGear mode: bridge log says "connect failed; retrying"

1. Is FlightGear running with `--httpd=5500`? Use `scripts/launch-flightgear.ps1`.
2. From WSL: `curl http://$(./scripts/fg-host-ip.sh):5500/json/position` —
   - connection refused → FlightGear not up yet, wrong port, or Windows
     firewall blocking (see FLIGHTGEAR_SETUP.md §3);
   - JSON → the interface is fine; re-check `FG_HOST` passed to the bridge.
3. Run `FG_HOST=... pnpm fg:diagnostic` for a guided check (reads + one
   harmless write).

## FlightGear connects but values look wrong / frozen

- `backend_status` in the diagnostics panel (`` ` `` key) distinguishes
  "socket open but no recent data" (FG paused? crashed?) from healthy.
- Wrong/blank MCP, autobrake, reverser values: those paths are
  aircraft-model-dependent — verify and fix
  `config/flightgear/737-800-property-map.json` (see FLIGHTGEAR_SETUP.md).
- Units look off by ×60 or ×0.3048: check the `scale` field of the map entry;
  never adjust units in UI code.

## Commands are ignored

- Status bar shows the last rejection (e.g. "gear lever locked on ground",
  "cannot set parking brake while moving", "rate limited") — most rejections
  are intentional physical interlocks.
- Rate limiting: axis streams are capped (~60/s) and discrete commands at
  ~10/s per connection.

## No sound

- Click the 🔇 button once — browsers require a user gesture to start audio.
- Voice (TTS) is a separate checkbox in the ATC/Crew panel header.

## Choppy rendering but smooth instruments (or vice versa)

- Rendering interpolates 120 ms behind the newest sample; if the diagnostics
  panel shows `state rate` well below the configured Hz, the bridge machine
  is starved — lower `STATE_RATE_HZ` or close other loads. Physics never
  couples to browser frame rate (spec §6).

## Playwright e2e fails to launch

- First run: `pnpm --filter @b737/web exec playwright install chromium`.
- Ports 5173/8737 must be free or already serving this app
  (`reuseExistingServer` is enabled).

## WSL specifics

- Keep the repo on the WSL filesystem (`~/projects/...`), not `/mnt/c` —
  pnpm/vite are drastically slower through 9p.
- Access from Windows: `\\wsl.localhost\<distro>\home\<user>\projects\b737-ops-sim`.
- The browser runs on Windows and reaches WSL servers via localhost
  forwarding automatically; the tricky direction is WSL→Windows (FG_HOST).
