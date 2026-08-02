# B737-800 Web Flight Operations Trainer

A **local-only**, web-based Boeing 737-800-style flight _operations_ trainer:
takeoff → ATC vectors → ILS approach → landing → rollout → debrief, with a
deterministic first officer (Pilot Monitoring), text ATC with readbacks,
state-validated checklists, and a transparent scoring debrief.

> ## ⚠ NOT A CERTIFIED TRAINING DEVICE
>
> This is a hobby simulation for personal use. Procedures, speeds and
> checklists are **non-certified approximations** (marked
> `NON_CERTIFIED_APPROXIMATION` / `SOURCE_REQUIRED` in the code/data).
> Do not use it for real-world flight training.

## Current capabilities (Milestone 4)

**Phase 4 — aircraft systems (new):**

- **Cold and dark**: a scenario that starts with everything off — battery, APU
  start, generator on the bus, IRS alignment, fuel pumps, both engines started
  on APU bleed, then After Start and taxi.
- **Systems model**: electrical buses, APU, pneumatics, fuel, hydraulics,
  anti-ice, IRS and engine start as a dependency graph
  ([SYSTEMS_MODEL.md](SYSTEMS_MODEL.md)). Procedure errors are rejected by the
  aircraft, not by the UI: no APU start without DC power, no generator without
  a running engine, no engine start without duct pressure (packs off!).
- **Overhead panel + synoptic + annunciators** in the browser, with master
  caution/warning and a recall button.
- With both hydraulic systems unpressurised the gear, flaps and speed brake
  stop moving, and a shut-down engine produces no thrust.

**Phase 3 — operations:**

- **Taxi operations**: a KSFO ground layout (stand, taxiway A, runway entry and
  high-speed exit) that the scenario engine, ATC and the ND all read from.
  Runway entry, holding-position crossing, taxi speed and taxiing off the
  pavement are judged from geometry.
- **Ground control**: taxi clearance with a route, hold-short instruction,
  handover to the tower when the aircraft is really holding short, and
  `taxi to stand` after landing.
- **Autopilot modes**: HDG SEL / LOC ARM / LOC and V/S / ALT HOLD / G/S ARM /
  G/S with real capture from the ILS, annunciated on the PFD FMA; arm the
  approach and the autopilot flies it.
- **Go-around**: TO/GA gives go-around thrust and attitude, ATC re-sequences
  the aircraft onto the pattern, and the Landing checklist is re-armed.
- **Stabilisation gates**: the first officer calls 1000 ft and 500 ft "stable"
  or "not stable", plus minimums, gear/flap read-backs and "three green".
- **Three scenarios** in a picker: the original circuit, a gate-to-gate flight
  (stand → taxi → circuit → taxi in → shutdown) and a short approach drill that
  starts established on the ILS.

**Phase 2 — asset integration:**

- Real open-source **737-800YV cockpit** (GPL-2.0, provenance in
  [THIRD_PARTY_ASSETS.md](THIRD_PARTY_ASSETS.md)) imported through a fully
  scripted AC3D→glTF pipeline — `pnpm assets:build`, no Blender needed
  ([ASSET_PIPELINE.md](ASSET_PIPELINE.md)).
- Captain-seat view inside the imported cockpit: main panel, glareshield,
  pedestal with throttle quadrant, MCP, overhead, yokes, seats.
- **Interactive 3D controls**: throttle/reverse/flaps/speed brake levers
  (drag), gear lever, parking brake, autobrake (click) — hover outline +
  tooltip; every mesh moves from **backend state** using the pivots declared
  in the FlightGear model XMLs.
- Real GPL cockpit sounds when assets are built: CFM56 engine loops
  (N1 crossfade), wind, flap/gear lever sounds, GPWS altitude callouts —
  synthesized fallback otherwise.
- Without built assets the app runs exactly as Milestone 1 (temporary
  geometry) — `pnpm assets:build` is optional.

## Milestone 1–3 capabilities

- **Mock mode (default):** a deterministic 737-class point-mass flight model —
  no FlightGear needed. Fixed seed ⇒ reproducible flights.
- **FlightGear mode:** adapter for FlightGear's built-in httpd WebSocket
  property interface (`--httpd`), with a versioned property map and a
  connection diagnostic. Protocol-tested against an emulated FG server;
  live validation requires a local FlightGear install (see status note below).
- Captain-seat 3D view (temporary geometry): KSFO 28R runway with markings,
  PAPI, approach lights; mouse-look; visual yoke.
- Instruments: PFD (speed/alt tapes, ADI, FD, ILS, VS, heading, RA,
  V-speed bugs), ND (rose, runway + extended centerline, range), N1/config
  display, MCP (IAS/HDG/ALT/VS + CMD A/FD).
- Interactive controls bound through a declarative registry: throttle,
  reverse, flaps (detents), speed brake + ARM, gear, autobrake, lights,
  parking brake — all displaying **backend** state.
- Keyboard / mouse / gamepad input with deadzone/sensitivity/inversion.
- One polished scenario: _Takeoff and ILS Landing — KSFO 28R_ with
  Before Takeoff / Landing / After Landing checklists, deterministic FO
  callouts (80 kt / V1 / Rotate / positive rate / approach altitudes /
  unstable-approach), ATC clearance + vector + landing workflow with
  readback grading, and a category-scored debrief with an event timeline.
- Synthesized audio (engine/wind/ground roll/touchdown/clicks/chimes) and
  optional offline Web Speech voice for FO/ATC.

**Status note:** FlightGear is not installed on this machine yet, so
FlightGear mode has been validated against a protocol-emulating test server
only (`packages/flightgear-adapter/test`). After installing FlightGear, run
the diagnostic below and file any property-map corrections in
`config/flightgear/737-800-property-map.json`.

## Required software

| What                  | Version | Where                                       |
| --------------------- | ------- | ------------------------------------------- |
| Node.js               | ≥ 20    | WSL2 or Windows                             |
| pnpm                  | ≥ 9     | `corepack enable` or `npm i -g pnpm`        |
| FlightGear (optional) | 2020.3+ | Windows native — only for `flightgear` mode |

The repo lives in the WSL2 filesystem (`~/projects/b737-ops-sim`) for
performance; access it from Windows at `\\wsl.localhost\<distro>\home\<user>\projects\b737-ops-sim`.

## Install

```bash
pnpm install
pnpm assets:build   # optional: fetch + convert the 3D cockpit + sounds (~23 MB download)
```

## Run — mock mode (no FlightGear)

```bash
pnpm dev
```

Then open **http://localhost:5173** in a Windows browser.
The bridge (mock backend) listens on `ws://127.0.0.1:8737/ws`.

## Run — FlightGear mode

1. **Windows:** install FlightGear + a 737 NG package (e.g. `737-800YV`),
   then launch it:
   ```powershell
   .\scripts\launch-flightgear.ps1              # defaults: KSFO 28R, --httpd=5500
   ```
2. **WSL2:** find the Windows-host IP and start the stack:
   ```bash
   FG_HOST=$(./scripts/fg-host-ip.sh) pnpm dev:fg
   ```
   (On Windows-native Node: `FG_HOST=127.0.0.1`.)
3. Verify connectivity first if unsure:
   ```bash
   FG_HOST=$(./scripts/fg-host-ip.sh) pnpm fg:diagnostic
   ```

Details + firewall notes: [FLIGHTGEAR_SETUP.md](FLIGHTGEAR_SETUP.md).

## Controls (default)

| Input                    | Action                                                                |
| ------------------------ | --------------------------------------------------------------------- |
| Arrow keys               | Yoke (↓ = nose up)                                                    |
| `,` / `.`                | Rudder                                                                |
| `=` / `-` (or PgUp/PgDn) | Throttle up/down                                                      |
| Space (hold)             | Wheel brakes                                                          |
| `G`                      | Gear toggle · `[` `]` flaps up/down a detent                          |
| `B`                      | Speed brake toggle · `R` reverse toggle · `P` parking brake           |
| `A`                      | Autopilot toggle · `C` center view · `` ` `` diagnostics              |
| Mouse drag on 3D view    | Look around (double-click to center)                                  |
| Gamepad                  | Left stick = yoke, axis 3 = throttle (configurable in `localStorage`) |

Flying the scenario: complete the Before Takeoff checklist (guided hints show
in _Guided_ mode), request clearance in the ATC panel, read back, taxi onto
28R, full thrust, rotate at VR, gear up on "positive rate", follow ATC
headings/altitudes via the MCP (CMD A engages the autopilot), configure on
the vectors, capture the ILS, land, reverse + brake, exit, After Landing
checklist → debrief.

## Environment variables

| Var                        | Default                                       | Meaning                                                                                                                                                                                                                                    |
| -------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `FLIGHT_BACKEND`           | `mock`                                        | `mock` or `flightgear`                                                                                                                                                                                                                     |
| `BRIDGE_PORT`              | `8737`                                        | Bridge WS/HTTP port                                                                                                                                                                                                                        |
| `STATE_RATE_HZ`            | `30`                                          | State stream rate (5–60)                                                                                                                                                                                                                   |
| `FG_HOST` / `FG_HTTP_PORT` | `127.0.0.1` / `5500`                          | FlightGear httpd address                                                                                                                                                                                                                   |
| `VITE_BRIDGE_URL`          | `ws://127.0.0.1:8737/ws`                      | Browser → bridge URL                                                                                                                                                                                                                       |
| `ALLOWED_ORIGINS`          | `http://localhost:5173,http://127.0.0.1:5173` | Browser origins allowed to open the control socket. Any page you visit can reach a loopback port, so the bridge refuses the WebSocket upgrade from anything else; requests without an `Origin` header (tests, `fg:diagnostic`) are allowed |

## Tests

```bash
pnpm test         # unit + integration (all packages)
pnpm test:e2e     # Playwright browser smoke (first: pnpm --filter @b737/web exec playwright install chromium)
pnpm typecheck
pnpm lint
```

The golden test (`packages/training-engine/test/fullCircuit.e2e.test.ts`)
flies the complete circuit against the mock model and asserts phase
detection, callout order, ATC flow and debrief scoring — including steering
off the runway, since the exit is detected from runway geometry.

136 unit/integration tests across 7 packages, plus 3 Playwright specs. The
3D-cockpit spec skips itself when `assets/generated/` has not been built.
In this WSL environment Playwright needs `TMPDIR=/tmp TEMP=/tmp TMP=/tmp`.

## Known limitations

- 3D display units (PFD/ND screens inside the 3D cockpit) are static — the
  2D instrument row is the live display; overhead switches are visual only
  (lights are operated from the DOM panel). Some upstream overhead textures
  are missing (see THIRD_PARTY_ASSETS.md).
- No autothrottle, trim, FMC, or systems beyond spec §3 scope.
- FlightGear `resetScenario` is best-effort — restart FG for a clean start.
- Mock ILS/runway datum is an approximation (self-consistent, not nav data).
- ATC readbacks are option-buttons (voice input is a later phase).
- MCP/autobrake FlightGear property paths are aircraft-model-dependent and
  marked for verification in the property map.
- The mock model touches down at field elevation anywhere — an off-runway
  landing is not modelled (scenario logic uses runway geometry regardless).
- Systems are modelled to procedure depth only — no electrical loads, no fuel
  burn, no pack temperatures, no failures. See SYSTEMS_MODEL.md for the full
  list of simplifications.
- The FMC, SID/STAR, weather, failures and voice interaction are Phase 5.
- The taxi layout is a plausible approximation, not survey data; in FlightGear
  mode the scenery is FlightGear's and may not match it.

## Documentation

[ARCHITECTURE.md](ARCHITECTURE.md) ·
[FLIGHTGEAR_SETUP.md](FLIGHTGEAR_SETUP.md) ·
[ASSET_PIPELINE.md](ASSET_PIPELINE.md) ·
[THIRD_PARTY_ASSETS.md](THIRD_PARTY_ASSETS.md) ·
[SCENARIO_AUTHORING.md](SCENARIO_AUTHORING.md) ·
[COCKPIT_CONTROL_MAPPING.md](COCKPIT_CONTROL_MAPPING.md) ·
[SYSTEMS_MODEL.md](SYSTEMS_MODEL.md) ·
[docs/REVIEW_RESPONSE.md](docs/REVIEW_RESPONSE.md) ·
[TROUBLESHOOTING.md](TROUBLESHOOTING.md) ·
[docs/milestones/](docs/milestones/)
