# Cockpit Control Mapping

Interactive cockpit controls are **declared, not hardcoded**
(spec §9): `packages/cockpit-model/src/index.ts` holds one
`CockpitControlDefinition` per control; the web UI and (Phase 2) 3D meshes
bind through this registry.

```ts
{
  id: 'flaps',
  label: 'Flap lever',
  panel: 'pedestal',
  meshNames: ['flap_lever'],        // 3D meshes that will bind in Phase 2
  interaction: 'lever',
  command: 'set_flaps',             // AircraftCommand type emitted
  stateSelector: 'controls.flapHandleDetent',  // AircraftState dot path shown
  detents: [0, 1, 2, 5, 10, 15, 25, 30, 40],
  trainingHint: '...',
  soundId: 'flap_lever',
}
```

## Binding rules

- A control **displays** `stateSelector` from the backend state stream and
  **emits** `command`. It must never show a locally-flipped value while the
  backend rejects the command (spec §7) — the DOM controls re-render from
  state, so a rejected command simply doesn't move the control, and the
  rejection reason appears in the status bar.
- `trainingHint` is surfaced as tooltip + guidance in _guided_ mode only.
- `soundId` maps to `audioEngine.click(...)` categories.
- Guided-mode highlighting maps checklist items → control ids in
  `apps/web/src/cockpit/guidance.ts`.

## Current registry (M1)

| id                               | panel    | interaction     | command                | state                            |
| -------------------------------- | -------- | --------------- | ---------------------- | -------------------------------- |
| throttle                         | pedestal | lever           | `set_throttle`         | `engines.left.throttleLeverNorm` |
| reverse_thrust                   | pedestal | lever           | `set_reverse_thrust`   | `engines.left.reverserNorm`      |
| flaps                            | pedestal | lever (detents) | `set_flaps`            | `controls.flapHandleDetent`      |
| speedbrake                       | pedestal | lever           | `set_speedbrake`       | `controls.speedbrakeLeverNorm`   |
| speedbrake_arm                   | pedestal | toggle          | `set_speedbrake_armed` | `controls.speedbrakeArmed`       |
| gear                             | main     | lever           | `set_gear`             | `controls.gearLeverDown`         |
| parking_brake                    | pedestal | toggle          | `set_parking_brake`    | `controls.parkingBrakeSet`       |
| autobrake                        | main     | rotary          | `set_autobrake`        | `controls.autobrake`             |
| light_landing/taxi/strobe/beacon | overhead | toggle          | `set_light`            | `lights.*`                       |

MCP knobs/buttons (IAS/HDG/ALT/VS, CMD A, F/D) are implemented directly in
`apps/web/src/instruments/Mcp.tsx` with the same display-from-state rule.

Two M3 actions are not pedestal controls and live with the ATC/crew panel:

| action            | command                | effect                                                                                          |
| ----------------- | ---------------------- | ----------------------------------------------------------------------------------------------- |
| Arm the approach  | `set_ap_approach_mode` | the autopilot captures LOC then G/S; annunciated on the PFD FMA                                 |
| Go around (TO/GA) | `set_toga`             | go-around thrust and attitude, autopilot out of the approach; the crew also announces it to ATC |

## Phase 2: 3D binding

Interactive meshes are named in the registry's `meshNames`; a Babylon picking
layer resolves mesh → control id → the same command path as the DOM controls.

Mesh names must exist in the imported model. The e2e suite asserts that every
`meshNames` entry resolves to a node in the loaded cockpit and is pickable —
four entries (`no1thrarm`, `boxone`, `handle`, `sbhandle`, and the `sw_*`
light switches) referenced names the 737-800YV model does not contain and were
silently dead until that check was added. Overhead light switches currently
have no mesh binding and are operated from the DOM panel.

**Known gap:** the 3D dispatch lives in `apps/web/src/cockpit/controlActions.ts`
and switches on control id separately from `ControlsPanel.tsx`, so the
"no per-switch logic" rule holds for state display but not yet for dispatch.
Both paths share one input target (`apps/web/src/input/controlTargets.ts`), so
they cannot disagree about lever positions; unifying the dispatch into a
registry-driven table is open work (see docs/REVIEW_RESPONSE.md).
