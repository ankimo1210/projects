# Milestone 1 — Definition of Done verification

Verified 2026-08-02 on WSL2 (Ubuntu), Node v22.22.2, pnpm 11.1.0.
Evidence: test names refer to files in this repo; all suites green at the
commit that adds this file (`pnpm test`, `pnpm test:e2e`, `pnpm typecheck`).

| # | Requirement (spec §21) | Status | Evidence |
|---|------------------------|--------|----------|
| 1 | Monorepo installs with one documented command | ✅ | `pnpm install` (README) |
| 2 | Browser application launches locally | ✅ | `pnpm dev` → http://localhost:5173 (Playwright boots it headlessly; screenshot in session log) |
| 3 | Bridge launches locally | ✅ | `GET /health` → `{"ok":true}`; `/status` shows backend + clients |
| 4 | Mock mode works without FlightGear | ✅ | default `FLIGHT_BACKEND=mock`; entire e2e suite runs on it |
| 5 | FlightGear mode can connect to a running FlightGear instance | ⚠ protocol-verified | `flightgearBackend.test.ts` (subscribe/assemble/write/reconnect vs emulated FG server) + `pnpm fg:diagnostic` tool. **Live validation pending: FlightGear is not installed on this machine.** Follow FLIGHTGEAR_SETUP.md, run the diagnostic, and correct any `AIRCRAFT-MODEL-DEPENDENT` map entries |
| 6 | Browser receives live aircraft-state updates | ✅ | e2e `smoke.spec.ts`: sim-time advances; diagnostics shows state rate |
| 7 | Throttle, pitch, roll, flaps, gear, brakes controllable | ✅ | e2e flap round-trip via UI; axis/throttle/brake paths in `bridge.test.ts` + golden circuit test (all six used to fly a full pattern) |
| 8 | Cockpit forward view + basic interactive controls | ✅ | Babylon captain view + pedestal controls (screenshot); controls bound via registry |
| 9 | PFD reflects live airspeed, altitude, attitude, vertical speed | ✅ | `Pfd.tsx` renders only from `AircraftState`; visible live in e2e |
| 10 | FO produces deterministic takeoff callouts | ✅ | `firstOfficer.test.ts` (order + once-only) + golden test (80/V1/Rotate/positive-rate order asserted) |
| 11 | Simple ATC clearance workflow works | ✅ | e2e: request → clearance → readback graded; `atc.test.ts` full sequence |
| 12 | Scenario detects takeoff, climb, approach, touchdown, runway exit | ✅ | golden test asserts every phase transition from real (mock-)physics state |
| 13 | Debrief report generated | ✅ | `debrief.test.ts` + golden test + e2e debrief overlay |
| 14 | Connection loss handled without crashing | ✅ | browser: stale detection + overlay + auto-reconnect; bridge: malformed-input tests; FG adapter reconnect test |
| 15 | Clear run and troubleshooting instructions | ✅ | README, FLIGHTGEAR_SETUP.md, TROUBLESHOOTING.md |
| 16 | Automated tests cover core scenario rules and state transformations | ✅ | 80 tests across 6 packages incl. golden full-circuit e2e |

**Not declared from static screens:** the Playwright suite drives the real
bridge + real mock backend in a real browser (live streaming, command
round-trip, rejection path), and the golden test flies the full circuit
against the physics model.
