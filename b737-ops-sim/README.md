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

> ## Current status — playable prototype; Milestone 5 acceptance re-opened
>
> The mock-backed trainer is runnable end to end and the Milestone 1–5 feature
> set is present. It is **not complete as an accepted Milestone 5 build**. The
> third review on 2026-08-02 re-opened the gate with 2 P1, 10 P2 and 3 P3
> findings. Both P1 integrity gaps — FlightGear ingress/freshness (V-01) and
> false-green asset verification (V-02) — were fixed on 2026-08-03 with
> negative regression coverage. Training-loop findings V-03, V-04 and V-07
> were fixed on 2026-08-04: a completed go-around is no longer scored as a
> failed landing, FO approach monitoring re-arms for the second approach, and
> one correct ATC correction clears the pending response. Failure lifecycle
> and engine-out findings V-05/V-06 were also fixed: injection is ack-checked,
> failures stay latched until a restoring clear, and asymmetric thrust plus
> airborne rudder now affect the flight path. V-08/V-09 now keep RTO manual
> takeover disarmed and make FlightGear time/diagnostic transitions exact.
> The latest recorded suite is green (238 unit/integration tests, 9 Playwright
> specs with verified built assets, typecheck, lint and build). Remaining P2/P3 findings and a live
> FlightGear run keep acceptance open; see
> [docs/REVIEW_RESPONSE_3.md](docs/REVIEW_RESPONSE_3.md).

## Current capabilities (Milestone 5)

**Phase 5 — advanced training (new):**

- **Route and LNAV**: a SID, an arrival and an approach transition
  ([NAVIGATION_DATA.md](NAVIGATION_DATA.md)) flown by the autopilot's LNAV mode,
  with an FMS panel (legs, direct-to) and the route drawn on the ND.
- **Weather**: wind aloft blended from the surface wind, seeded gusts,
  visibility and turbulence — per scenario, so a crosswind landing is just a
  scenario.
- **Failures**: engine flameout, generator and hydraulic failures, injected by
  scenario rules from real state (the V1 cut happens because the aeroplane
  reached V1) and expressed through the systems model. They remain latched
  until cleared; engine-out thrust produces approximate yaw/roll and can be
  countered with rudder.
- **Three more scenarios**: engine failure after V1, crosswind landing, and a
  SID/arrival flown on the route.
- **Voice readbacks** (optional, off by default): speak a readback instead of
  clicking. The recogniser only proposes; the deterministic grader still
  decides. See the privacy note below.

**Phase 4 — aircraft systems:**

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

## Milestone 1–4 capabilities

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

### First flight — beginner Guided mode

`Guided` is selected by default. The mission card in the upper-right always
shows one **NEXT ACTION / 次にやること**, the current phase, scenario progress
and the live values that matter. Use it as follows:

1. Do only the action shown on the card.
2. Press **◎ 場所を表示** if you cannot find the control; the relevant switch
   or panel opens and flashes.
3. Press **? なぜ？ / 完了条件** to see why the action matters and exactly what
   state advances the objective.
4. When the objective changes, `✓ OBJECTIVE COMPLETE` confirms progress.

Cold-and-dark startup is broken into individual switches; during flight the
coach prioritises an unanswered ATC readback, then the active checklist item,
then the current phase objective. `Assisted` keeps textual guidance without
control pulsing. `Evaluation` hides the coach entirely.

For **Flight controls**, click the 3D view and press `←`, `→`, `↑`, `↓`, `,`
and `.` once each. The mission card shows six live `✓ DONE` indicators; press
`Verify` only after all six are green. The keys move the control only while
pressed and return it to centre on release.

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

238 unit/integration tests across 7 packages, plus 9 Playwright specs when
assets are built. The 3D-cockpit spec skips itself when `assets/generated/`
has not been built.
In this WSL environment Playwright needs `TMPDIR=/tmp TEMP=/tmp TMP=/tmp`.

## Known limitations

- 3D display units (PFD/ND screens inside the 3D cockpit) are static — the
  2D instrument row is the live display; overhead switches are visual only
  (lights are operated from the DOM panel). Some upstream overhead textures
  are missing (see THIRD_PARTY_ASSETS.md).
- No autothrottle, trim, full CDU, VNAV or performance-initialisation model.
- FlightGear `resetScenario` is best-effort — restart FG for a clean start.
- Mock ILS/runway datum is an approximation (self-consistent, not nav data).
- ATC readback buttons are always available; optional browser speech
  recognition can propose the same deterministic choices.
- MCP/autobrake FlightGear property paths are aircraft-model-dependent and
  marked for verification in the property map.
- The mock model touches down at field elevation anywhere — an off-runway
  landing is not modelled (scenario logic uses runway geometry regardless).
- Systems are modelled to procedure depth only — no electrical loads, fuel
  burn or pack temperatures. Failure latching/restoration and engine-out
  yaw/rudder are training approximations, not detailed fault or aerodynamic
  models. See SYSTEMS_MODEL.md for the simplifications.
- The route model is not a CDU: no VNAV, no constraint enforcement, no holds,
  no airways (NAVIGATION_DATA.md).
- **Voice input privacy**: the browser's speech recognition may send audio to a
  cloud service (Chrome does). It is off by default, asks before starting, and
  everything works without it.
- Route, weather and failure commands are mock-mode features; FlightGear owns
  those in FlightGear mode and rejects them with that message.
- The taxi layout is a plausible approximation, not survey data; in FlightGear
  mode the scenery is FlightGear's and may not match it.

## Completion gate and next steps

Work in this order; every item can be developed against the mock model, fake
FlightGear server or isolated asset fixtures except the final live check.

1. **P1 safety/integrity gaps — completed 2026-08-03:** mapped FlightGear
   values now pass strict ingress typing and per-property freshness (V-01);
   empty/incomplete manifests and missing required outputs fail (V-02).
2. **Training-loop integrity — completed 2026-08-04:** normal
   go-arounds score correctly, FO approach callouts re-arm, and one correct
   ATC correction clears the pending response (V-03/V-04/V-07). Scenario
   failures are ack-checked, latched and restoring, with approximate
   asymmetric-thrust yaw and airborne rudder authority (V-05/V-06).
3. **State transitions — completed 2026-08-04:** manual brake takeover now
   inhibits RTO until explicit reselection; FlightGear time is required and
   the diagnostic confirms write/read-back/exact restore (V-08/V-09).
4. **Close remaining fidelity and robustness findings:** gust/visibility
   effects, edge-triggered repeatable rules, atomic asset swap, pointer cancel
   handling, cold-and-dark beacon state and stale evidence (V-10–V-15).
5. **Re-run the gate:** `pnpm test`, `pnpm test:e2e` with required assets,
   `pnpm typecheck`, `pnpm lint`, and `pnpm build`; then install FlightGear and
   complete the live property-map diagnostic and one end-to-end flight.

The concrete regression requirements and evidence for each item are in
[REVIEW_FEEDBACK_3.md](REVIEW_FEEDBACK_3.md#完了判定).

## Documentation

[ARCHITECTURE.md](ARCHITECTURE.md) ·
[FLIGHTGEAR_SETUP.md](FLIGHTGEAR_SETUP.md) ·
[ASSET_PIPELINE.md](ASSET_PIPELINE.md) ·
[THIRD_PARTY_ASSETS.md](THIRD_PARTY_ASSETS.md) ·
[SCENARIO_AUTHORING.md](SCENARIO_AUTHORING.md) ·
[COCKPIT_CONTROL_MAPPING.md](COCKPIT_CONTROL_MAPPING.md) ·
[SYSTEMS_MODEL.md](SYSTEMS_MODEL.md) ·
[NAVIGATION_DATA.md](NAVIGATION_DATA.md) ·
[docs/REVIEW_RESPONSE.md](docs/REVIEW_RESPONSE.md) ·
[docs/REVIEW_RESPONSE_3.md](docs/REVIEW_RESPONSE_3.md) ·
[TROUBLESHOOTING.md](TROUBLESHOOTING.md) ·
[docs/milestones/](docs/milestones/)
