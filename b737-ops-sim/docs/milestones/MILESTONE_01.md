# Milestone 1 — Playable Vertical Slice

> **Goal:** Launch bridge + browser app locally, stream aircraft state (mock or
> FlightGear), fly a complete takeoff → pattern → ILS landing scenario with
> deterministic first-officer callouts, text ATC, checklists, and a structured
> debrief.

**Status:** Complete (see MILESTONE_01_DOD.md — FlightGear live validation pending local FG install)
**Environment (verified 2026-08-02):** WSL2 (Ubuntu), Node v22.22.2, pnpm 11.1.0,
git 2.43, 20 cores. FlightGear **not installed** on the Windows host — mock mode
is the primary development path; the FlightGear adapter is validated against a
protocol-level fake server (see Task 10) and documented in `FLIGHTGEAR_SETUP.md`.

## Key decisions (assumptions documented per spec §25)

| #   | Decision                                                                                                                             | Rationale                                                                                                                                                                |
| --- | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| D1  | Repo lives at `~/projects/b737-ops-sim` (WSL ext4), **not** `/mnt/c`                                                                 | node_modules over 9p is 10–50× slower; Windows access via `\\wsl.localhost\`                                                                                             |
| D2  | FlightGear integration uses the built-in **httpd WebSocket property interface** (`--httpd=5500`, `/PropertyListener`)                | Push-based property streaming + writes over one socket; no custom protocol XML to install into FG_ROOT; validated against a fake FG server until FlightGear is installed |
| D3  | Scenario airport is **KSFO 28R** (FlightGear's default airport)                                                                      | Mock and FlightGear backends share the same world; ILS geometry computed from configured threshold coordinates (`NON_CERTIFIED_APPROXIMATION`)                           |
| D4  | Scenario/FO/ATC/debrief logic runs **in the browser** as pure deterministic packages; the bridge stays a thin validated pipe         | Keeps simulation-of-record (FlightGear/mock) separate from training logic; trivially testable                                                                            |
| D5  | Workspace packages export TypeScript source directly (no build step in dev); `tsx` runs the bridge, Vite consumes packages as source | Fastest iteration; `tsc --noEmit` in CI-style script guards types                                                                                                        |
| D6  | M1 audio is **synthesized** (Web Audio oscillators/filtered noise)                                                                   | No third-party samples needed yet; THIRD_PARTY_ASSETS.md stays empty until Phase 2                                                                                       |
| D7  | V-speeds, flap detents, trim green band etc. are config data marked `NON_CERTIFIED_APPROXIMATION` / `SOURCE_REQUIRED`                | Spec §14 — no invented Boeing data presented as authoritative                                                                                                            |
| D8  | React 18 + Vite 6 + Babylon.js 7 + Zustand 5 + Fastify 5 + Zod 3 + Vitest 3 + Playwright                                             | Spec §4 defaults, pinned to stable majors                                                                                                                                |

## Architecture (summary — details in ARCHITECTURE.md)

```
apps/web (React/Vite/Babylon)
  ├─ net/            WebSocket client, reconnect, seq/ack, interpolation
  ├─ sim3d/          cockpit + runway world (temporary geometry)
  ├─ instruments/    PFD, ND, engine display, MCP (SVG/DOM, state-driven)
  ├─ cockpit/        interactive controls bound via control registry
  ├─ panels/         checklist, transcript, status bar, debrief, diagnostics
  └─ audio/          state-driven synthesized sound engine
packages/shared              zod schemas: AircraftState, AircraftCommand, wire protocol, units
packages/flightgear-adapter  FlightBackend interface, MockBackend (deterministic), FlightGearBackend (httpd WS), property map loader
packages/scenario-engine     data-driven phase machine + condition evaluator + checklists
packages/training-engine     FO monitor rules, ATC state machine, debrief scorer
packages/cockpit-model       declarative CockpitControlDefinition registry
apps/bridge (Fastify)        WS server, command validation/rate limit, state broadcast, diagnostics
config/flightgear/737-800-property-map.json   versioned FG property mapping
```

## Tasks

- [x] T0 Phase 0: environment inspection (Node/pnpm/FG/WSL networking) — findings above
- [x] T1 Monorepo scaffold: pnpm workspaces, strict TS base config, eslint+prettier, .gitignore (private/ etc.), root scripts
- [x] T2 `packages/shared`: unit-explicit zod schemas (AircraftState, AircraftCommand, wire messages, BackendStatus) + tests
- [x] T3 `packages/flightgear-adapter`: `FlightBackend` interface + **MockBackend** — deterministic point-mass 737-class model (seeded), ground roll, rotation, climb, turns, ILS geometry vs KSFO 28R, landing, reversers/braking, simple MCP hold modes + tests (determinism, liftoff physics sanity, ILS convergence)
- [x] T4 `apps/bridge`: Fastify + WS, backend selection via `FLIGHT_BACKEND`, zod-validated commands, seq/ack, heartbeat, input rate limiting, stale detection, `/health` + `/status`, structured logs + integration test (real WS client ↔ mock backend)
- [x] T5 `packages/scenario-engine`: condition DSL, phase machine, checklist runtime (state-validated items), event log + tests for spec §11 rules (positive rate, clearance gating, checklist auto-complete)
- [x] T6 `packages/training-engine`: FO deterministic callouts (80kt/V1/Rotate/positive rate/approach alts/unstable-approach), ATC clearance state machine with readback tracking, debrief scorer with transparent per-category rules + tests
- [x] T7 `apps/web` core: WS client with reconnect + interpolation, Zustand stores, layout per spec §19, status bar, diagnostics panel (hidden by default)
- [x] T8 Instruments: PFD (speed/alt tapes, attitude, VS, RA, FD, ILS dev, AP annunciation, speed bugs), ND (rose, heading bug, runway/approach line, range), N1 gauges, MCP panel
- [x] T9 Cockpit 3D + controls: captain-seat camera with mouse-look, windshield + runway world, yoke/throttle/flaps/gear/speedbrake/autobrake/lights bound through `cockpit-model` registry; keyboard/mouse/gamepad input abstraction (deadzone/sensitivity/invert, localStorage bindings)
- [x] T10 `FlightGearBackend` over httpd WS + property map JSON + fake-FG-server test + `scripts/fg-diagnostic.ts` connection probe + launch scripts (PowerShell + WSL)
- [x] T11 MVP scenario data: before-takeoff/landing/after-landing checklists, phases per spec §20, ATC script, FO rules wiring, V-speed table (marked approximations)
- [x] T12 Audio: synthesized engine/wind/ground-roll/touchdown/click/warning sounds, state-driven gains; optional Web Speech TTS for FO/ATC
- [x] T13 Debrief screen: per-category scores + event timeline per spec §16
- [x] T14 Docs: README, ARCHITECTURE, FLIGHTGEAR_SETUP, ASSET_PIPELINE, THIRD_PARTY_ASSETS, SCENARIO_AUTHORING, COCKPIT_CONTROL_MAPPING, TROUBLESHOOTING
- [x] T15 Playwright smoke test (app boots in mock mode, PFD updates, scenario starts) + full `pnpm test` green + typecheck green
- [x] T16 End-to-end verification: golden full-circuit test (scripted pilot flies takeoff→ILS→landing→exit against mock physics) + Playwright command round-trips

## Definition of Done

Spec §21 verbatim; tracked in `docs/milestones/MILESTONE_01_DOD.md` with
verification evidence when complete. FlightGear-mode live connection is
documented + protocol-tested; live validation against a real FlightGear install
is recorded as **pending user install** (FlightGear absent on this machine).

## Out of scope for M1 (per spec §3)

FMC, electrical/hydraulic/pneumatic systems, cold & dark, full taxi network,
voice ATC input, real 3D cockpit asset import (Phase 2), multiple scenarios.
