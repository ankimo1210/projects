# Scenario Authoring

Scenarios are **data**: a `ScenarioDefinition` object (see
`packages/scenario-engine/src/types.ts`). The MVP scenario
(`src/scenarios/mvpCircuit.ts`) is the reference example.

## Structure

```ts
{
  id, title, aircraft, description,
  initialState: {           // honored by the backend on (re)start
    seed, airportIcao, runwayId, startAt, flapDetent,
    parkingBrakeSet, grossWeightLb, windDirDeg, windSpeedKt,
  },
  initialPhaseId, completionPhaseId,
  phases: [{ id, title, transitions: [{ to, when, eventId? }] }],
  rules:  [{ id, when, phases?, severity, message }],
  checklists: [{ id, title, items: [...] }],
}
```

## Condition DSL

Conditions evaluate against **live aircraft state** — a scenario must never
advance on button clicks alone (spec §11).

```ts
{ prop: 'speeds.iasKt', op: 'gte', value: 80 }
{ prop: 'weightOnWheels', op: 'eq', value: false }
{ prop: 'nav.locDeviationDots', op: 'between', min: -1, max: 1 }
{ prop: 'attitude.headingDegMag', op: 'withinDegOf', target: 284.4, toleranceDeg: 30 }
{ all: [...] } / { any: [...] } / { not: ... }
// must hold continuously for N seconds:
{ prop: 'speeds.iasKt', op: 'gt', value: 255, sustainedSec: 2 }
```

Property namespaces:

- `AircraftState` dot paths: `speeds.iasKt`, `controls.flapHandleDetent`, …
- `derived.radioAltitudeTrend` / `derived.altitudeTrend` / `derived.iasTrend`
- `derived.runwayAlongM` / `derived.runwayCrossM` — position in the scenario
  runway's frame (metres from the threshold along the centerline; + = right of
  the landing direction); `null` when the runway is unknown
- `derived.onRunwaySurface` — on the paved surface with weight on wheels
- `derived.enteredRunwaySurface` — true only on the sample that crossed onto
  the surface, so an aircraft positioned on the runway at scenario start is not
  reported as entering it
- `derived.onTaxiSurface` / `derived.taxiwayLabel` — on a paved taxi surface of
  the airport's taxi network, and which taxiway it is
- `derived.distanceToHoldShortM` — metres to the runway holding position;
  negative once inside the protected area
- `derived.pastHoldShort` — crossed the holding position (this is what a runway
  incursion rule should use in a taxi scenario)
- `derived.distanceToStandM` — metres to the scenario's stand, for parking
  → `'increasing' | 'decreasing' | 'flat'` over a 3 s window
- `flags.<name>` — host-set flags (ATC clearances, checklist completions,
  control-check done). ATC applies `takeoffClearanceReceived`,
  `atcTargetHeadingDeg`, `atcTargetAltitudeFt`, `approachClearanceReceived`,
  `landingClearanceReceived`, and the session sets
  `flightControlCheckDone`, `afterLandingChecklistComplete`.

## Checklist items

An item completes **only** when its `validation` condition holds at the
moment the crew answers it (spec §14). Items without a machine-checkable
state must carry `manualReason` explaining why. Never invent Boeing values:
use `NON_CERTIFIED_APPROXIMATION` / `SOURCE_REQUIRED` / `PLACEHOLDER_VALUE`
markers in `sourceReference`, and keep uncertain numbers in config, not code.

```ts
{
  id: 'flaps',
  challenge: 'Flaps',
  dynamicResponseProp: 'controls.flapHandleDetent',   // spoken response from state
  validation: { all: [ ... ] },
  responsibleCrew: 'first_officer',
  delegable: true,
  trainingHint: '...',            // shown in guided mode
  failureMessage: '...',
  sourceReference: 'NON_CERTIFIED_APPROXIMATION — SOURCE_REQUIRED',
}
```

### Phase entry actions

A phase may declare `resetChecklistIds` (re-arm those checklists on entry — the
Landing checklist after a go-around) and `setFlagsOnEnter` (set flags on entry —
clearing `goAroundAnnounced` once the approach is rejoined). Both keep procedure
repetition in the scenario data instead of in engine code.

### Scenario catalogue

`SCENARIOS` in `packages/scenario-engine/src/scenarios/catalogue.ts` is what the
UI picker offers:

| id                               | start                  | what it exercises                                                    |
| -------------------------------- | ---------------------- | -------------------------------------------------------------------- |
| `circuit_takeoff_ils_landing_01` | holding point          | takeoff, ATC pattern, ILS, landing, runway exit                      |
| `gate_to_gate_ksfo_01`           | stand                  | ground control, taxi out, hold short, the circuit, taxi in, shutdown |
| `approach_drill_ksfo_28r_01`     | established on the ILS | configuration, stabilisation gates, landing or go-around             |

Adding one is a data change: define the scenario, export it, add it to
`SCENARIOS`. The gate-to-gate and drill scenarios reuse the circuit's airborne
phases, rules and checklists rather than copying them.

### Checklist phases

`ChecklistDefinition.allowedPhaseIds` restricts when a checklist can be
actioned (omit = any phase). The runtime refuses out-of-phase items and emits a
`checklist_item_failed` event; the UI shows those checklists read-only. Without
it the crew can complete the Landing and After Landing checklists while still
holding short.

## Rules

Monitor rules fire (once, unless `once: false`) while their phase filter
matches: use severity `info` for milestones (e.g. `reverse_deployed` is
consumed by the debrief), `deviation` for procedure errors,
`safety_critical` for incidents. One `safety_critical` event fails the flight
in the debrief — do not use it for anything you would accept in a passing run.

Prefer geometry over proxies: use `derived.onRunwaySurface` /
`derived.enteredRunwaySurface` for runway occupancy instead of ground speed,
and validate configuration from actual surfaces (`controls.flapsActualNorm`,
`controls.gearPositionNorm`, `controls.spoilersDeployedNorm`) rather than lever
positions.

## Testing a scenario

1. Unit-test key transitions/rules like
   `packages/scenario-engine/test/scenarioEngine.test.ts`.
2. Add a scripted flight through the full scenario like the golden test in
   `packages/training-engine/test/fullCircuit.e2e.test.ts` — it exercises the
   scenario against the real mock physics, which catches unreachable
   transitions and bad geometry assumptions.
