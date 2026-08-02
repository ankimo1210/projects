# Milestone 5 — Definition of Done verification

Verified 2026-08-02 on WSL2 (Ubuntu), Node v22.22.2, pnpm 11.1.0, at the commit
that contains the code.

```
pnpm test        PASS — 204 unit/integration tests, 7 packages
pnpm test:e2e    PASS — 7 Playwright specs (with built assets)
pnpm typecheck   PASS
pnpm lint        PASS
pnpm build       PASS
```

| #   | Requirement (MILESTONE_05.md)   | Status | Evidence                                                                                                                                                                                                             |
| --- | ------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T1  | Navigation data and route model | ✅     | `packages/shared/src/navigation.ts`; `navigation.test.ts` (9 tests: procedures reference real fixes, courses/distances computed, cross-track sign, intercept direction, sequencing, wind triangle)                   |
| T2  | FMS state, commands and LNAV    | ✅     | `AircraftState.fms`; `load_route` / `direct_to` / `set_lnav`; `flightModel.test.ts` "LNAV, weather and failures": LNAV refused without a route, route followed and legs sequenced, direct-to a fix outside the route |
| T3  | Weather                         | ✅     | `ScenarioInitialState.weather` + `AircraftState.weather`; test asserts the wind blends from surface toward aloft with altitude; gusts are seeded so runs reproduce                                                   |
| T4  | Failures                        | ✅     | `inject_failure` / `clear_failures`, `ScenarioRule.injectFailure`; tests: engine failure stops that engine and cuts thrust, a scenario-armed failure is active from the first sample                                 |
| T5  | Crosswind operations            | ✅     | `crosswind_landing_ksfo_01`; golden test proves the aeroplane drifts off the localizer when the crosswind is not corrected                                                                                           |
| T6  | Voice ATC / crew                | ✅     | `voiceInput.ts` + `voiceInput.test.ts` (5 tests: faithful readback, the other option, ambiguity refused, noise refused, punctuation ignored); opt-in toggle with a privacy note                                      |
| T7  | Scenarios                       | ✅     | Three added to the catalogue; golden tests for the V1 cut, the crosswind drift and the SID flown under LNAV                                                                                                          |
| T8  | Web                             | ✅     | FMS panel (legs, direct-to, LNAV, weather/failure readout), route drawn on the ND, e2e "FMS panel loads a route and arms LNAV" and "weather readout reflects the scenario weather"                                   |
| T9  | Documentation                   | ✅     | NAVIGATION_DATA.md, README, CHANGELOG, this file                                                                                                                                                                     |

## What the golden tests actually prove

- **V1 cut**: with the scenario wired to the same command path the crew uses,
  engine 1 stops at 145 kt — measured from the state, not scheduled — the rule
  is recorded, the other engine keeps running, and the aeroplane rotates and
  climbs away on one engine.
- **Crosswind**: flying runway heading with a 22 kt gusting crosswind moves the
  localizer needle by more than a third of a dot in a minute, so drift is real
  and the crew has to correct it.
- **Route**: with SFOUT1/BAYIN1 loaded, LNAV holds the aircraft within 2 NM of
  the route and sequences past at least one fix.

## Notable engineering facts

- The first leg's start must be the position the route was **built** from, not
  the live position. Using the live position made the cross-track identically
  zero and the leg impossible to sequence — the aeroplane flew past the fix and
  kept going with "0.00 NM off course".
- A leg has to sequence when the fix is behind the aircraft, not only when it is
  within 0.6 NM: passing wide of a waypoint otherwise leaves LNAV chasing it.
- Weather is reported at the aircraft's altitude, so a readout on approach shows
  the blended wind (240/29), not the surface wind (245/22). The e2e asserts the
  blend, not the configuration.

## Deviations from the plan

- The crosswind scenario reuses the approach drill's phases rather than adding
  its own; only the weather differs, which is the point.
- The browser test for the V1 cut was replaced by a weather-readout test:
  flying to V1 through the UI took over a minute of wall clock per run. The
  injection path is covered by the golden test.

## Known limitations

- Not a CDU: no VNAV, no constraint enforcement (constraints are displayed),
  no holds, no airways, no performance initialisation (NAVIGATION_DATA.md).
- Route, weather and failure commands are mock-mode features; in FlightGear mode
  they are rejected with a message pointing at the documentation, and
  `AircraftState.fms` is reported empty.
- Voice input depends on the browser's `SpeechRecognition`, which in Chrome is a
  cloud service. It is off by default and the UI says so; everything works
  without it.
- Turbulence and gusts perturb the wind the aircraft flies in; they do not model
  wind shear, microbursts or icing.
