# Milestone 3 — Definition of Done verification

Verified 2026-08-02 on WSL2 (Ubuntu), Node v22.22.2, pnpm 11.1.0, in the same
commit as the code. Evidence below is automated unless it says otherwise.

```
pnpm test        PASS — 161 unit/integration tests, 7 packages
pnpm test:e2e    PASS — 4 Playwright specs (with built assets)
pnpm typecheck   PASS
pnpm lint        PASS
pnpm build       PASS
```

| #   | Requirement (MILESTONE_03.md)                                         | Status | Evidence                                                                                                                                                                                                                                                           |
| --- | --------------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| T1  | Ground layout data with segment/offset/hold-short queries             | ✅     | `packages/shared/src/taxi.ts` (+ `runwayPointToLatLon`, `isPastHoldShort`); `taxi.test.ts` 10 tests                                                                                                                                                                |
| T2  | Autopilot modes captured from real deviations, TO/GA, ground handling | ✅     | `flightModel.test.ts` "autopilot modes": HDG SEL/ALT HOLD annunciation, LOC/GS arm→capture from a final-approach start, TO/GA drops the AP and climbs. `mcp.rollMode`/`pitchMode`/`approachArmed` in the shared schema; property map v3                            |
| T3  | Taxi derived signals, taxi/go-around phases, geometric rules          | ✅     | `scenarioEngine.test.ts` "taxi geometry" (4) + "phases can re-arm a checklist"; `derived.onTaxiSurface`, `taxiwayLabel`, `distanceToHoldShortM`, `pastHoldShort`, `distanceToStandM`                                                                               |
| T4  | Ground control clearances, tower handover, go-around re-sequencing    | ✅     | `AtcController.requestTaxiClearance` / `announceGoAround` / taxi-in clearance; exercised by the gate-to-gate and go-around golden tests                                                                                                                            |
| T5  | Fuller checklists and stabilisation callouts                          | ✅     | Before Start / Before Taxi / Shutdown in the gate-to-gate scenario (state-validated, phase-gated); `firstOfficer.test.ts` gates/minimums/read-backs (4 new tests)                                                                                                  |
| T6  | FMA annunciation, taxi awareness, scenario picker, TO/GA control      | ✅     | PFD FMA shows real modes (armed white / active green) + APP; ND draws the taxi network and the holding position on the ground at 0.5 NM; status-bar picker; transcript-panel taxi request and TO/GA. e2e "switching scenario resets the aircraft into the new one" |
| T7  | Three scenarios, each flown by a golden test                          | ✅     | `scenarios.e2e.test.ts`: gate-to-gate taxi + hold short (no incursion, tower handover), approach drill flown to a full stop by LOC/GS capture, and a go-around; plus the existing `fullCircuit.e2e.test.ts`                                                        |
| T8  | Documentation and verification                                        | ✅     | This file, plus README, SCENARIO_AUTHORING, COCKPIT_CONTROL_MAPPING, CHANGELOG                                                                                                                                                                                     |

## What the golden tests actually prove

- **Ground:** the crew requests taxi, runs Before Start and Before Taxi, steers
  along the network to the holding position, stops, and is handed to the tower —
  and `runway_incursion` never fires, because the aircraft never crossed the
  holding position uncleared. Crossing it without a clearance is what the rule
  watches, not ground speed.
- **Air:** from an ILS-established start the autopilot captures LOC and then
  G/S, flies the path down, and the flight reaches `debrief` after landing and
  vacating. The stabilisation gates and minimums appear in the transcript.
- **Go-around:** TO/GA plus the crew's call re-sequences ATC, the aircraft
  climbs away, and the scenario records `go_around_established`.

## Notable engineering facts

- An armed approach keeps flying the glidepath below 300 ft even when the beam
  drops out. Without that latch the autopilot reverted to "climb to the MCP
  altitude" at about 40 ft and ballooned away from the runway — found by tracing
  the approach drill, not by inspection.
- The flight-control check is valid wherever the Before Takeoff checklist is
  allowed, not in a phase literally named `before_takeoff`; the gate-to-gate
  scenario runs it while holding short.
- Checklist completion sets `<camelCaseId>ChecklistComplete`, so a scenario can
  gate a phase on any checklist without engine changes.
- The ND clamps its range to 0.5 NM on the ground: at 10 NM the taxi layout is
  a few pixels and effectively invisible.

## Known limitations (unchanged or new)

- FlightGear mode is still protocol-verified only — FlightGear is not installed
  on this machine. The new `set_ap_approach_mode` / `set_toga` command mappings
  and the approach-armed state entry are marked AIRCRAFT-MODEL-DEPENDENT and
  need `pnpm fg:diagnostic` against a real installation.
- Mode annunciation (`rollMode`/`pitchMode`) is mock-only; FlightGear mode
  reports `null` until a property map supplies equivalents.
- The taxi network is a plausible approximation (NON_CERTIFIED_APPROXIMATION —
  SOURCE_REQUIRED) and only covers KSFO 28R.
- The mock model still touches down at field elevation anywhere; scenario logic
  does not depend on that, but an off-runway landing is not modelled.
- Phase 4 (aircraft systems) and Phase 5 (FMC, SID/STAR, weather, failures,
  voice) are untouched by design.
