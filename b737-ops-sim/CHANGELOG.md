# Changelog

Local-only project; versions track milestones rather than releases.

## Second review remediation — M5 re-opened and fixed (2026-08-02)

All 10 findings in [REVIEW_FEEDBACK_2.md](REVIEW_FEEDBACK_2.md) addressed;
per-finding detail in [docs/REVIEW_RESPONSE_2.md](docs/REVIEW_RESPONSE_2.md).

### Fixed

- **Failure injection reaches the aircraft in the browser** (F-01): the web app
  now passes the crew's command path into the training session; the browser V1
  test that was wrongly removed during M5 is restored.
- **Weather acts on the physics** (F-02): the aircraft drifts by the blended
  surface/aloft wind plus the seeded gust, and the scenario's turbulence
  setting scales the attitude perturbation — LNAV's crab and the actual drift
  now agree, so it converges in a crosswind.
- Injected failures no longer auto-FAIL the debrief (F-03); the route-deviation
  rule catches both sides of the course (F-04); airborne-start scenarios no
  longer carry a phantom "no liftoff" deduction (F-05).
- Cold-and-dark: inherited checklists remapped to reachable phases (F-06) and
  the taxi-without-clearance rule re-armed (F-10).
- Wind direction declared degrees TRUE in the schemas and converted to magnetic
  in ATC readouts (F-07); ND draws only the remaining route (F-09); duplicate
  react import removed (F-08).

## Milestone 5 — Advanced Training (2026-08-02)

Plan: [docs/milestones/MILESTONE_05.md](docs/milestones/MILESTONE_05.md),
verification: [docs/milestones/MILESTONE_05_DOD.md](docs/milestones/MILESTONE_05_DOD.md),
route data: [NAVIGATION_DATA.md](NAVIGATION_DATA.md).

### Added

- **Navigation data and route model**: waypoints, a SID, an arrival and an
  approach transition; leg construction, signed cross-track with a bounded
  intercept, waypoint sequencing (on the fix or once it is behind), and a
  wind-triangle heading.
- **LNAV** as an autopilot roll mode, annunciated on the FMA, with `load_route`,
  `direct_to` and `set_lnav` commands and an FMS panel; the ND draws the route.
- **Weather**: wind aloft blended from the surface wind, seeded gusts,
  visibility and turbulence in `ScenarioInitialState`, echoed in
  `AircraftState.weather`.
- **Failures**: `inject_failure` / `clear_failures`, and scenario rules that can
  declare a failure so it fires from real state (the V1 cut happens because the
  aeroplane reached V1). Failures are expressed through the systems model, so
  the annunciator and debrief see them without a second code path.
- **Three scenarios**: engine failure after V1, crosswind landing, SID and
  arrival on the route.
- **Optional voice readbacks**: deterministic token matching against the
  options ATC already produced; the existing grader decides correctness. Off by
  default with a privacy note.

### Known limitations

- Not a CDU: no VNAV, no constraint enforcement, no holds or airways.
- Route, weather and failure commands are mock-mode only.

## Milestone 4 — Aircraft Systems (2026-08-02)

Start the aeroplane. Plan: [docs/milestones/MILESTONE_04.md](docs/milestones/MILESTONE_04.md),
verification: [docs/milestones/MILESTONE_04_DOD.md](docs/milestones/MILESTONE_04_DOD.md),
what is and is not modelled: [SYSTEMS_MODEL.md](SYSTEMS_MODEL.md).

### Added

- **Systems state** in the shared schema: electrical buses, APU, pneumatics,
  fuel, hydraulics, ice protection, IRS, per-engine start state, plus derived
  annunciations and master caution/warning.
- **Systems model** in mock mode — a dependency graph evaluated every physics
  step. Interlocks fall out of it: no APU start without DC power, no generator
  without a running engine, no engine start without duct pressure, no start
  lever without fuel pressure, and the packs starve an APU-bleed start.
- **Engine start sequence**: starter motoring, light-off at 25 % N2, starter
  cut-out at 56 %, idle at 62 %, with the selector springing back to OFF.
- **Cold-and-dark scenario** with Preflight, Before Start (systems) and After
  Start checklists, every item validated against systems state, handing over to
  the gate-to-gate taxi flow.
- **Overhead panel, systems synoptic and annunciator strip** in the browser,
  including master caution/warning recall.
- `set_system_switch`, `set_engine_start` and `reset_master_caution` commands,
  validated at the bridge and mapped (as placeholders) in property map v4.

### Changed

- A shut-down engine windmills instead of idling and produces no thrust; with
  both hydraulic systems below 1500 psi the gear, flaps and spoilers stop.

### Known limitations

- Systems are procedure-depth only: no electrical loads, fuel burn, pack
  temperatures, crossfeed, standby hydraulics or failures (SYSTEMS_MODEL.md).
- FlightGear mode reports the engines-running baseline for systems; the new
  property-map entries are placeholders marked AIRCRAFT-MODEL-DEPENDENT.

## Milestone 3 — Operations (2026-08-02)

Ground operations, real autopilot modes and more than one scenario.
Plan: [docs/milestones/MILESTONE_03.md](docs/milestones/MILESTONE_03.md),
verification: [docs/milestones/MILESTONE_03_DOD.md](docs/milestones/MILESTONE_03_DOD.md).

### Added

- **Taxi operations**: a KSFO ground layout in `@b737/shared` (stand, taxiway
  A, runway entry, high-speed exit) with segment/offset queries and holding
  position helpers. The scenario engine exposes `derived.onTaxiSurface`,
  `taxiwayLabel`, `distanceToHoldShortM`, `pastHoldShort` and
  `distanceToStandM`; the ND draws the same network on the ground.
- **Ground control**: taxi clearance with a route read from the network,
  hold-short instruction, tower handover once the aircraft is really holding
  short, and `taxi to stand` after landing.
- **Autopilot modes**: HDG SEL / LOC ARM / LOC and V/S / ALT HOLD / G/S ARM /
  G/S captured from real deviations, plus TO/GA — exposed as
  `mcp.rollMode` / `mcp.pitchMode` / `mcp.approachArmed` and annunciated on the
  PFD FMA (armed white, active green).
- **Go-around**: a `go_around` phase reachable from final approach or the
  flare, ATC re-sequencing onto the downwind leg, and the Landing checklist
  re-armed on entry.
- **Stabilisation gates**: 1000 ft and 500 ft "stable / not stable" calls,
  minimums, gear and flap read-backs, and "gear down, three green" — all from
  one shared definition of stable.
- **Scenario catalogue and picker**: the original circuit, a gate-to-gate
  flight (stand → taxi → circuit → taxi in → shutdown) with Before Start,
  Before Taxi and Shutdown checklists, and a short approach drill that starts
  established on the ILS. Switching scenario resets through the backend.
- Scenarios can start at a stand or established on final approach; phases can
  re-arm checklists and set flags on entry.

### Fixed

- An armed approach now keeps flying the glidepath below 300 ft instead of
  reverting to the MCP altitude and climbing away at about 40 ft.
- The flight-control check is valid wherever the Before Takeoff checklist is
  allowed, not only in a phase named `before_takeoff`.
- The ND clamps its range to 0.5 NM on the ground, where the taxi layout is.

### Known limitations

- Mode annunciation and the new commands are mock-verified; the FlightGear
  property map entries for approach-armed and TO/GA are marked
  AIRCRAFT-MODEL-DEPENDENT and still need a live check.
- The taxi network is a plausible approximation for KSFO 28R only.

## Review remediation — M1/M2 re-opened and fixed (2026-08-02)

All 22 findings in [REVIEW_FEEDBACK.md](REVIEW_FEEDBACK.md) addressed;
per-finding detail and the deliberate exclusions are in
[docs/REVIEW_RESPONSE.md](docs/REVIEW_RESPONSE.md).

### Fixed

- **Security**: the control socket now requires an allowed `Origin`
  (`ALLOWED_ORIGINS`) and a completed `hello` before any command; a protocol
  version mismatch closes the socket; pause/reset are rate-limited.
- **FlightGear**: one connection state machine (idempotent connect, socket
  generation guard, no competing retry loop) and no stale or partially
  populated state — publishing waits for every required property, stops when
  the stream goes stale, drops its cache on close and validates each sample.
  `simTimeSec` comes from FlightGear's clock (property map v2).
- **Mock physics**: simulated time no longer scales with the state publish rate
  (25 Hz ran at 0.83×, 40 Hz at 1.33×); RTO autobrake works on a rejected
  takeoff and no longer fires at touchdown; the autopilot honours the sign of
  the selected MCP V/S.
- **Scenario/scoring**: runway entry, occupancy and exit are geometric
  (`runwayPosition()`); `rollout` and `runway_exit` are distinct phases; one
  safety-critical event fails the flight; checklists are gated on the flight
  phase and validate actual surfaces (flap travel, gear down-locked, spoilers
  stowed) rather than lever positions.
- **First officer**: "Positive rate" no longer depends on the sample rate; a
  tuned ILS with no deviation data counts as unstable; safety callouts reach
  the debrief as events; an unanswered callout expires.
- **3D cockpit**: FlightGear assembly rotations (flightdesk −15°, overhead
  90/90) are applied instead of being warned about and dropped; the control
  registry lists only meshes that exist in the model.
- **Interaction**: keyboard, gamepad, DOM panel and 3D drags share one control
  target; drags coalesce to 20 Hz and always deliver the released value;
  pause/reset and control sounds wait for the backend's acknowledgement;
  pointer listeners are removed on dispose.
- **Tooling**: `pnpm test` no longer collects Playwright specs (it was red);
  asset fetching verifies recorded hashes and stages atomically; the converter
  regenerates its output and copies an allowlist; `fg-diagnostic` derives every
  property from the property map.

### Changed

- The project now lives in the `~/projects` workspace repository (history
  preserved); it is no longer a nested repository without a remote.
- ATC reads the scenario's surface wind instead of always saying "wind calm".

## Milestone 2 — Asset Integration (2026-08-02)

Real open-source 737 cockpit imported through a fully scripted pipeline.
Details: [docs/milestones/MILESTONE_02.md](docs/milestones/MILESTONE_02.md),
verification: [docs/milestones/MILESTONE_02_DOD.md](docs/milestones/MILESTONE_02_DOD.md).

### Added

- `scripts/fetch-cockpit-assets.mjs` — SHA-pinned fetch of the 737-800YV
  (GPL-2.0) cockpit models, textures, FlightGear XMLs, LICENSE and sounds,
  writing a per-file sha256 manifest.
- `packages/asset-pipeline` — AC3D parser, FG-frame normalization, glTF 2.0
  writer preserving object names, and a FlightGear XML assembly/animation
  extractor producing `cockpit-bindings.json` (13 unit tests).
- Imported 3D cockpit in the browser: main panel, glareshield, pedestal with
  throttle quadrant, MCP, overhead, yokes, seats (~1,440 meshes).
- Interactive 3D controls (drag: throttle/reverse/flaps/speed brake; click:
  gear, parking brake, autobrake) with hover outline + tooltip; levers move
  from backend state using the pivots declared in the FlightGear XMLs.
- Real GPL sounds when assets are built: CFM56 engine loops crossfaded by N1,
  wind, flap/gear lever sounds, GPWS altitude callouts — synthesized
  fallback otherwise.
- `pnpm assets:fetch` / `pnpm assets:build`; Vite serves the generated assets.
- e2e test: 3D gear-lever pick → bridge → backend rejection round-trip,
  skipped cleanly when assets are absent.

### Fixed

- Converter now applies the proper rotation `(x, −z, y)` for AC3D→FlightGear
  frame conversion; a y/z swap mirrored all panel lettering.
- Babylon's glTF root transform is compensated at runtime (`W = L⁻¹·D`)
  instead of assuming the importer's handedness convention.
- `ResizeObserver` keeps the render backing store in sync with canvas CSS
  size — pointer picking drifted after panel collapse/expand.
- Cockpit loading aborts cleanly when the scene is disposed mid-load.

### Changed

- `packages/cockpit-model` mesh names now reference real 737-800YV objects.
- `assets/imported/` and `assets/generated/` are gitignored (re-fetchable;
  provenance in THIRD_PARTY_ASSETS.md + manifest).
- Docs updated: README, ASSET_PIPELINE.md, THIRD_PARTY_ASSETS.md.

### Known limitations

- 3D display units are static (the 2D instrument row is the live display).
- Overhead switches are visual only; lights are operated from the DOM panel.
- Five overhead textures are missing upstream (documented, renders untextured).

## Milestone 1 — Playable Vertical Slice (2026-08-02)

First complete, runnable flight: takeoff → ATC vectors → ILS → landing →
rollout → debrief in mock mode.
Details: [docs/milestones/MILESTONE_01.md](docs/milestones/MILESTONE_01.md),
verification: [docs/milestones/MILESTONE_01_DOD.md](docs/milestones/MILESTONE_01_DOD.md).

### Added

- pnpm monorepo, strict TypeScript, eslint/prettier, Vitest + Playwright.
- `packages/shared` — unit-explicit zod schemas (aircraft state, commands,
  wire protocol), geodesy, runway datum, V-speed table (approximations
  explicitly marked).
- `packages/flightgear-adapter` — `FlightBackend` interface, deterministic
  737-class point-mass mock model (fixed 60 Hz physics, seeded, ILS geometry,
  simple autopilot), and a FlightGear backend over the httpd WebSocket
  property interface with a versioned property map.
- `apps/bridge` — Fastify WebSocket server: zod validation, sequence numbers
  and acks, heartbeat, rate limiting, pause, status broadcast, `/health`,
  `/status`; `fg-diagnostic` connection probe; PowerShell/WSL launch scripts.
- `packages/scenario-engine` — condition DSL with trend/sustain support,
  phase machine, state-validated checklists, event log, MVP KSFO 28R scenario.
- `packages/training-engine` — deterministic first-officer callouts, ATC
  clearance state machine with readback grading, transparent debrief scoring,
  session orchestrator.
- `apps/web` — Babylon captain-seat view, PFD/ND/engine display/MCP, control
  registry-driven panel, checklist and transcript panels, debrief screen,
  synthesized audio, optional Web Speech voice, hidden diagnostics panel,
  reconnecting WebSocket client with render-time interpolation.
- Documentation set (README, ARCHITECTURE, FLIGHTGEAR_SETUP, ASSET_PIPELINE,
  THIRD_PARTY_ASSETS, SCENARIO_AUTHORING, COCKPIT_CONTROL_MAPPING,
  TROUBLESHOOTING).

### Known limitations

- FlightGear mode is protocol-verified against an emulated server only —
  FlightGear is not installed on this machine, so live validation is pending.
- No autothrottle, trim, FMC, or aircraft systems beyond the M1 scope.
