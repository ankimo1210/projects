# Changelog

Local-only project; versions track milestones rather than releases.

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
