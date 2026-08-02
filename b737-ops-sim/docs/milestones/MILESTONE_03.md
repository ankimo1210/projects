# Milestone 3 — Operations (spec §22 Phase 3)

> **Goal:** operate the aeroplane on the ground as well as in the air. Taxi out
> under ground control, fly with real autopilot modes and an ILS the autopilot
> can capture, be monitored against stabilisation gates, fly a go-around when
> the approach is not stable, taxi in after landing — and do it in more than one
> scenario.

**Status:** in progress (started 2026-08-02)

Phase 3 items from the spec: taxi operations · more complete checklists · MCP
and autopilot · ILS behaviour · more realistic callouts · stable-approach
monitoring · multiple scenarios. The go-around flow is pulled forward from
Phase 5 because the first officer already calls for one and the aircraft
currently has nowhere to fly it (recorded as a gap in
[docs/REVIEW_RESPONSE.md](../REVIEW_RESPONSE.md)).

## Decisions

| #   | Decision | Rationale |
| --- | --- | --- |
| D1 | Ground layout is **data**, not geometry: a small taxiway graph (nodes + segments with width) in `@b737/shared`, marked `NON_CERTIFIED_APPROXIMATION — SOURCE_REQUIRED`, used by the scenario engine, the 3D world and ground ATC alike | One source of truth; the 3D world stops inventing its own taxiway |
| D2 | Autopilot gains **modes** (roll: HDG SEL / LOC, pitch: V/S / ALT HOLD / G/S) with an armed→captured transition, annunciated on the PFD FMA | "MCP and autopilot" + "ILS behaviour"; the scripted pilot currently fakes LOC tracking by dialling headings |
| D3 | Go-around is a **scenario phase** entered from a TO/GA action, with ATC re-vectoring back onto the approach; the FO's existing call becomes actionable | Removes the "instructed to do something unflyable" inconsistency |
| D4 | Stabilisation is judged at **1000 ft and 500 ft gates**, published as scenario events, and scored | Spec asks for stable-approach monitoring; events make it debriefable (same pattern as R-19) |
| D5 | Scenarios become a **catalogue** with a picker in the UI; the MVP circuit stays as-is and gains a full gate-to-gate variant and a short approach-only drill | "Multiple scenarios" without rewriting the existing one |
| D6 | Taxi speed/hold-short discipline is enforced by **rules on geometry** (`derived.*`), not by prompts | Consistent with R-08; no button-click gating |
| D7 | Mock-only for M3. FlightGear mode keeps working (property map already covers AP/nav), but live validation stays blocked on FlightGear not being installed | Same constraint as M1/M2 |

## Tasks

### T1 — Ground layout data (`@b737/shared`)

- `TaxiNetwork` for KSFO: stand, taxiway segments to the 28R holding point, and
  a high-speed exit + route to the stand after landing.
- `taxiPosition(network, lat, lon)` → nearest segment, lateral offset, whether
  the aircraft is on a paved taxi surface, and the id of the segment.
- `holdShortPosition(runway)` → the hold-short line for a runway, and a
  `crossedHoldShort` test in the runway frame.
- Unit tests for offsets, segment selection and hold-short crossing.

### T2 — Mock model: ground handling + autopilot modes

- Ground: nosewheel steering already exists; add differential braking feel
  (steering gain vs. speed is already there) and a documented taxi thrust band.
- `ApModes` in the model: roll (`HDG_SEL`, `LOC_ARM`, `LOC`), pitch (`VS`,
  `ALT_HOLD`, `GS_ARM`, `GS`), captured from real deviation and altitude error.
- New command `set_ap_approach_mode` (arms LOC/GS) and `set_toga` (go-around
  thrust + pitch target); both schema-validated in `@b737/shared`.
- State gains `mcp.rollMode` / `mcp.pitchMode` (enums) so the PFD annunciates
  what the aircraft is actually doing, and the FlightGear property map gets the
  corresponding entries (optional; annunciation degrades to `null`).
- Tests: LOC capture from an intercept heading, G/S capture from below, ALT
  HOLD at the selected altitude, TO/GA climb.

### T3 — Scenario engine: taxi and go-around

- Derived signals: `derived.onTaxiSurface`, `derived.taxiSegmentId`,
  `derived.distanceToHoldShortM`, `derived.crossedHoldShortUncleared`.
- Phases for the gate-to-gate scenario: `preflight` → `taxi_out` →
  `hold_short` → `before_takeoff` → … → `rollout` → `runway_exit` → `taxi_in` →
  `parked` → `debrief`.
- `go_around` phase reachable from `final_approach`/`landing`, returning to
  `approach_setup` once re-established.
- Rules: taxi overspeed (> 25 kt on a taxiway, > 10 kt in a turn), hold-short
  violation (safety-critical), stand overrun.
- Tests for each new rule and the go-around loop.

### T4 — ATC: ground control and go-around handling

- Ground controller phase set: pushback/taxi clearance with a route
  (`taxi to runway 28R via A, hold short of 28R`), hold-short instruction,
  handover to tower, and after landing `contact ground` → `taxi to stand`.
- Tower: `go around, fly runway heading, climb 3000` when the crew announces a
  go-around, then the existing vector pattern back to the ILS.
- Readback options for every new instruction; grading unchanged.

### T5 — Crew: fuller checklists and callouts

- Checklists added with `allowedPhaseIds`: Before Start, Before Taxi, After
  Landing (exists), Shutdown/Parking. Every item state-validated or carrying a
  `manualReason`.
- FO callouts: flap/gear selections read back, `1000` and `500` stabilisation
  gate calls ("stable" / "not stable"), `minimums` at DA, `go around` handoff.
- Stabilisation gate results emitted as scenario events and scored in the
  debrief (approach_stability category).

### T6 — Web: annunciation, taxi awareness, scenario picker

- PFD FMA shows the real roll/pitch modes and armed modes.
- ND shows the taxi network and the aircraft's position on it when on the
  ground, plus the hold-short line.
- Scenario picker in the status bar; changing scenario resets through the
  backend (ack-gated, as R-16 requires).
- A TO/GA control (button + key) that issues `set_toga`.

### T7 — Scenario catalogue

- `circuit_takeoff_ils_landing_01` — unchanged (regression guard).
- `gate_to_gate_ksfo_01` — the full M3 scenario (taxi out, circuit, taxi in).
- `approach_drill_ksfo_28r_01` — start on final at 2000 ft, land, exit. Short
  loop for practising the approach and the stabilisation gates.
- A golden test per scenario, all flown by a scripted pilot against the mock.

### T8 — Documentation and DoD

- `SCENARIO_AUTHORING.md`: taxi derived signals, new phases, scenario catalogue.
- `COCKPIT_CONTROL_MAPPING.md`: TO/GA and approach-mode controls.
- `README.md`: capabilities, controls, known limitations.
- `MILESTONE_03_DOD.md` with evidence per requirement, and the same five-command
  verification (`test`, `test:e2e`, `typecheck`, `lint`, `build`) with and
  without generated assets.

## Non-goals (Phase 4/5)

Systems modelling (electrical, hydraulic, bleed, APU, engine start), FMC/route
entry, SID/STAR, weather, failures, voice interaction. Terrain-aware touchdown
stays out of scope: the mock model still lands at field elevation anywhere, and
scenario logic keeps deciding from runway/taxiway geometry rather than terrain.
