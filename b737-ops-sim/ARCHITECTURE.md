# Architecture

```
Browser (React + Babylon.js)
    │  WebSocket (typed, zod-validated, seq/ack, heartbeat)
    ▼
apps/bridge (Fastify)  ←  the ONLY process allowed to talk to a backend
    │  FlightBackend interface
    ▼
packages/flightgear-adapter
    ├─ MockBackend      deterministic 737-class point-mass model (default)
    └─ FlightGearBackend  FlightGear httpd WebSocket property interface
```

## Principles

- **The simulation of record is the backend.** The browser renders state and
  sends commands; UI state never pretends to be aircraft state (spec §24).
  Controls display backend values; the visual yoke is the one explicit
  "pending input" display.
- **Deterministic training logic.** Scenario phases, FO callouts, ATC
  clearances, checklist validation and scoring are pure rule evaluation over
  the state stream. No LLM decides safety or completion (spec §12/§13).
- **Unit-explicit boundaries.** All schema fields carry units in their names
  (`iasKt`, `altitudeFtMsl`, `verticalSpeedFpm`). Conversions happen only in
  adapters (`packages/flightgear-adapter`) and `shared/units.ts`.
- **No raw FlightGear property paths** outside
  `config/flightgear/737-800-property-map.json` + the adapter package.

## Packages

| Package | Responsibility | Key entry points |
|---------|----------------|------------------|
| `@b737/shared` | zod schemas (state/commands/wire protocol), units, geo, runway datum, V-speed table | `AircraftStateSchema`, `AircraftCommandSchema`, `ClientMessage`/`ServerMessage` |
| `@b737/flightgear-adapter` | `FlightBackend` interface + both backends + property map parsing | `MockFlightModel` (pure), `MockBackend`, `FlightGearBackend` |
| `@b737/scenario-engine` | condition DSL (+trends/sustain), phase machine, state-validated checklists, event log, MVP scenario data | `ScenarioRuntime`, `ChecklistRun`, `MVP_CIRCUIT_SCENARIO` |
| `@b737/training-engine` | FO (PM) rules, ATC state machine + readbacks, debrief scorer, session orchestrator | `TrainingSession`, `FirstOfficer`, `AtcController`, `generateDebrief` |
| `@b737/cockpit-model` | declarative `CockpitControlDefinition` registry | `COCKPIT_CONTROLS` |
| `@b737/bridge` | WS server, command validation + rate limiting, seq/ack, status broadcast, diagnostics endpoints | `buildBridge` |
| `@b737/web` | rendering + interaction only | `state/connection.ts` wiring |

## Data flow

1. Backend produces `AircraftState` at `STATE_RATE_HZ` (default 30 Hz).
2. Bridge stamps a per-connection `seq` and broadcasts `{t:'state', seq, state}`.
3. Browser `BridgeClient` feeds:
   - `StateInterpolator` (render-time interpolation, 120 ms behind newest —
     rendering is decoupled from simulation timing, spec §6);
   - `useSimStore` (React instruments re-render per sample);
   - `TrainingSession.update()` (scenario/FO/ATC evaluation, client-side);
   - `audioEngine.update()` (state-driven levels).
4. User input (keyboard/gamepad/UI) → typed `AircraftCommand` → bridge
   validates with zod + token-bucket rate limits → backend → `command_ack`
   with the echoed seq. Rejections surface in the status bar.

## Timing

| Loop | Rate |
|------|------|
| Mock physics substeps | fixed 60 Hz (deterministic, decoupled from timers) |
| State stream | 20–60 Hz (`STATE_RATE_HZ`) |
| Browser rendering | display refresh (interpolated) |
| Axis input send | ≤ 20 Hz coalesced |
| Backend status broadcast | 1 Hz |

## Failure handling

- Bridge ↔ browser: heartbeat ping/pong every 2 s; >3 s silence ⇒ socket
  recycled ⇒ full-screen "disconnected" overlay; auto-reconnect every 1.5 s.
- Bridge ↔ FlightGear: reconnect loop with backoff; `backend_status`
  broadcasts distinguish "socket open but stale" from "not connected".
- Malformed/unknown messages ⇒ `protocol_error` reply, never a crash
  (covered by bridge integration tests).

## Where training logic runs

Scenario/FO/ATC/debrief run **in the browser** (pure packages, no I/O).
Rationale: the bridge stays a thin, backend-agnostic pipe; the deterministic
engines are unit-testable and replayable (the golden circuit test drives the
same code against the mock model without any server).
