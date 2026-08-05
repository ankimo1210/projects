# Response to REVIEW_FEEDBACK_2.md

> **Historical response, superseded for completion status.** The third review
> ([REVIEW_FEEDBACK_3.md](../REVIEW_FEEDBACK_3.md)) found additional P1–P3
> gaps after this remediation. This file remains the evidence for F-01..F-10,
> but does not establish current Milestone 5 completion.

Review date 2026-08-02 (`REVIEW_FEEDBACK_2.md`, findings F-01..F-10),
remediation the same day. Every finding was fixed; each fix carries a
regression test unless noted.

## Verification after remediation

```bash
pnpm test        # 213 unit/integration tests, 7 packages
pnpm test:e2e    # 8 Playwright specs (7 + 1 skipped without built assets)
pnpm typecheck
pnpm lint
pnpm build
```

## Finding-by-finding

| ID   | Fix                                                                                                                                                            | Regression test                                                                                                                                                                                        |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| F-01 | The web app's `TrainingSession` constructions pass `sendCommand`, so scenario-injected failures reach the aircraft through the same command path the crew uses | e2e "V1 engine failure happens in the browser and the aircraft feels it": full thrust via the DOM throttle, failure at V1, hydraulic A collapse annunciated, master caution lit                        |
| F-02 | The physics wind is now `currentWind()` (surface blended to aloft) plus the seeded gust, and the scenario's `turbulence` scales the attitude perturbation      | `flightModel.test.ts` "weather acts on the physics": LNAV converges in a strong crosswind, drift matches the blended wind, gusts vary reproducibly per seed, turbulence measurably shakes the aircraft |
| F-03 | The debrief no longer auto-FAILs on safety-critical events carrying `data.injectFailure` — the injected failure is the exercise, not the crew's mistake        | `debrief.test.ts` "injected failures": injected event → not FAIL, real event → FAIL                                                                                                                    |
| F-04 | `route_deviation` fires on both sides of the course (`any` of `gt 2` / `lt -2`)                                                                                | `scenarioEngine.test.ts` "route deviation rule": right, left, and on-course                                                                                                                            |
| F-05 | `DebriefInput.expectTakeoff` (false for `startAt: 'final_approach'`) suppresses the "No liftoff detected" deduction for airborne starts                        | approach-drill golden test asserts no phantom takeoff finding and overall ≠ FAIL                                                                                                                       |
| F-06 | Cold-and-dark remaps the inherited gate-to-gate checklists' `allowedPhaseIds` to its own phase names, so `before_start` and `before_taxi` are reachable        | covered by typecheck + the cold-and-dark golden test still passing; no dedicated assertion                                                                                                             |
| F-07 | Wind direction is declared **degrees TRUE** in the schemas (scenario config and `AircraftState.weather`), and ATC converts to magnetic before reading it out   | reviewed; ATC suite green (the conversion is a one-line formula off the runway's declared variation)                                                                                                   |
| F-08 | The duplicate react import in `TranscriptPanel.tsx` merged                                                                                                     | lint/typecheck                                                                                                                                                                                         |
| F-09 | The ND draws the route from the active leg onward; passed fixes are dropped                                                                                    | reviewed (rendering only)                                                                                                                                                                              |
| F-10 | `taxi_without_clearance` re-declared for cold-and-dark's `ready_to_taxi` phase                                                                                 | reviewed; rule syntax identical to the tested gate-to-gate one                                                                                                                                         |

## Corrections to earlier records

- `MILESTONE_05_DOD.md` claimed T4 (failures) verified — that was true only for
  the mock-model path; the browser path was broken and untested. The DoD now
  carries a correction note, and the browser test that was removed during M5 is
  restored (the process failure is recorded in REVIEW_FEEDBACK_2.md F-01).
- `MILESTONE_05.md` T3 promised weather acting on airspeed/track/attitude; the
  implementation delivered display-only weather. Now the wind and gusts act on
  the track and the turbulence on attitude, as the plan said.
