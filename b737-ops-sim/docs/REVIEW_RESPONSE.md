# Response to REVIEW_FEEDBACK.md

> **Historical response, not current completion evidence.** The third review
> ([REVIEW_FEEDBACK_3.md](../REVIEW_FEEDBACK_3.md)) re-opened claims R-05,
> R-07, R-21 and R-22 as V-01, V-08, V-02/V-12 and V-09 respectively.
> V-01/V-02/V-08/V-09 are now closed in `REVIEW_RESPONSE_3.md`; V-12 remains
> open. Use that response and the current README completion gate for status; the details
> below preserve what was claimed and tested at this earlier checkpoint.

Review date 2026-08-02 (`REVIEW_FEEDBACK.md`), remediation the same day.
Every P0/P1 finding was independently reproduced against the code before it was
fixed, and every fix carries a regression test unless noted.

## Verification after remediation

Run from the project root on WSL2 (Ubuntu), Node v22.22.2, pnpm 11.1.0:

```bash
pnpm test        # 136 unit/integration tests, 7 packages
pnpm test:e2e    # 3 Playwright specs (needs TMPDIR=/tmp in this environment)
pnpm typecheck
pnpm lint
pnpm build
```

## Finding-by-finding

| ID   | Fix                                                                                                                                                                                                                           | Regression test                                                                                                                                       |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-01 | `b737-ops-sim` imported into the `~/projects` workspace repository with all 11 commits (git subtree-style merge), registered in the workspace README, nested `.git` retired to `~/.b737-ops-sim-git-backup`                   | `git log` in the workspace repo                                                                                                                       |
| R-02 | Vitest owns `test/**` only; Playwright specs are no longer collected                                                                                                                                                          | `pnpm test` is green                                                                                                                                  |
| R-03 | WebSocket upgrade requires an allowed `Origin` (`ALLOWED_ORIGINS`), commands are refused before `hello`, a version mismatch closes with 1002, pause/reset go through the rate limiter                                         | `bridge.test.ts`: foreign origin, no-Origin client, pre-hello command, version mismatch, pause flood                                                  |
| R-04 | The FlightGear backend owns reconnection: idempotent `connect()`, publish timer started regardless of the first attempt, per-socket generation guard; the bridge's competing retry loop removed                               | `flightgearBackend.test.ts`: late-start FlightGear, repeated connects keep one socket                                                                 |
| R-05 | Publishing is gated on socket-open + not stale + every non-optional mapped property present; the cache is dropped on close; the sample is schema-validated; `simTimeSec` comes from `/sim/time/elapsed-sec` (property map v2) | `flightgearBackend.test.ts`: partial cache, stale stream, cache dropped on close                                                                      |
| R-06 | `MockFlightModel.step()` carries the sub-step remainder instead of rounding                                                                                                                                                   | `flightModel.test.ts`: 25/30/40/50/60 Hz advance 1.0 s; equal speed after 20 s at different tick sizes                                                |
| R-07 | RTO autobrake state machine (arm on takeoff thrust, trigger on retard above 60 kt, disarm at liftoff) and no longer activates at touchdown                                                                                    | `flightModel.test.ts`: RTO vs OFF stopping, brake command during abort, no braking after liftoff                                                      |
| R-08 | `runwayPosition()` in `@b737/shared` gives along/cross/on-surface; `rollout` and `runway_exit` are separate phases; incursion = crossing onto the surface uncleared                                                           | `runwayGeometry.test.ts`, `scenarioEngine.test.ts` (occupancy, entry edge, start-on-runway, slow-on-centerline), golden circuit steers off the runway |
| R-09 | One `safety_critical` event fails the flight                                                                                                                                                                                  | `debrief.test.ts` asserts `FAIL`                                                                                                                      |
| R-10 | `ChecklistDefinition.allowedPhaseIds`, runtime refusal, read-only UI                                                                                                                                                          | `scenarioEngine.test.ts` out-of-phase checklist                                                                                                       |
| R-11 | FlightGear assembly rotations are applied (SimGear roll→pitch→heading, conjugated into the loader's content frame)                                                                                                            | `fgFrame.test.ts` (7 cases) + e2e assertion on the flightdesk/overhead tilt                                                                           |
| R-12 | "Positive rate" confirms a climb over elapsed time, not per-sample radio-altitude gain                                                                                                                                        | `firstOfficer.test.ts` at 5/30/60 Hz                                                                                                                  |
| R-13 | One shared control target for throttle/reverse, adopted from backend state when idle                                                                                                                                          | covered by `controlDrag.test.ts` + manual browser check                                                                                               |
| R-14 | Drags coalesce to 20 Hz and always deliver the released value; speed brake and reverse use the continuous bucket                                                                                                              | `controlDrag.test.ts`                                                                                                                                 |
| R-15 | Named pointer handlers removed in `dispose()`                                                                                                                                                                                 | reviewed; no automated StrictMode harness                                                                                                             |
| R-16 | Pause/reset commit on ack; sounds wait for acceptance                                                                                                                                                                         | `wsClient` ack plumbing; manual check                                                                                                                 |
| R-17 | The autopilot honours the sign of the selected MCP V/S until capture                                                                                                                                                          | `flightModel.test.ts`                                                                                                                                 |
| R-18 | Checklists/FO/debrief judge actual surfaces; the flight-control check requires rudder and counts accepted commands                                                                                                            | `firstOfficer.test.ts` (flaps in transit), debrief gate checks, golden circuit                                                                        |
| R-19 | FO safety callouts become scenario events the debrief scores; a tuned ILS with null deviations is not "stable"                                                                                                                | `firstOfficer.test.ts`                                                                                                                                |
| R-20 | "Negative — read back" is answerable, and an unanswered FO callout expires after 12 s                                                                                                                                         | reviewed; ATC suite still green                                                                                                                       |
| R-21 | Hash-verified skip, atomic staging, allowlisted sound copy, clean converter output, failure on missing required sounds                                                                                                        | `pnpm assets:build` re-verified end to end                                                                                                            |
| R-22 | `fg-diagnostic` derives every property from the property map                                                                                                                                                                  | ran against the map (FlightGear still not installed)                                                                                                  |

## Deliberately not done

- **Terrain-aware touchdown.** The mock model still touches down at field
  elevation anywhere, so an off-runway landing is not modelled. Scenario logic
  no longer depends on this (it uses runway geometry), but a grass landing is
  still treated as a normal touchdown.
- **Go-around / missed-approach flow.** The first officer can call for a go
  around; there is no phase to fly it. Following that call leaves the scenario
  without a completion path.
- **A single dispatcher for DOM/3D/keyboard controls.** `controlActions.ts`
  still switches on control id separately from `ControlsPanel.tsx`. The shared
  input target (R-13) removes the state divergence; unifying the dispatch is a
  refactor that needs its own review.
- **3D pointer coverage in e2e beyond the gear lever.** Only controls visible
  in the default captain view can be clicked by projection; the suite instead
  asserts that every registry mesh exists and is pickable.
