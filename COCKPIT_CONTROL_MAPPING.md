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
- `trainingHint` is surfaced as tooltip + guidance in *guided* mode only.
- `soundId` maps to `audioEngine.click(...)` categories.
- Guided-mode highlighting maps checklist items → control ids in
  `apps/web/src/cockpit/guidance.ts`.

## Current registry (M1)

| id | panel | interaction | command | state |
|----|-------|-------------|---------|-------|
| throttle | pedestal | lever | `set_throttle` | `engines.left.throttleLeverNorm` |
| reverse_thrust | pedestal | lever | `set_reverse_thrust` | `engines.left.reverserNorm` |
| flaps | pedestal | lever (detents) | `set_flaps` | `controls.flapHandleDetent` |
| speedbrake | pedestal | lever | `set_speedbrake` | `controls.speedbrakeLeverNorm` |
| speedbrake_arm | pedestal | toggle | `set_speedbrake_armed` | `controls.speedbrakeArmed` |
| gear | main | lever | `set_gear` | `controls.gearLeverDown` |
| parking_brake | pedestal | toggle | `set_parking_brake` | `controls.parkingBrakeSet` |
| autobrake | main | rotary | `set_autobrake` | `controls.autobrake` |
| light_landing/taxi/strobe/beacon | overhead | toggle | `set_light` | `lights.*` |

MCP knobs/buttons (IAS/HDG/ALT/VS, CMD A, F/D) are implemented directly in
`apps/web/src/instruments/Mcp.tsx` with the same display-from-state rule.

## Phase 2: 3D binding

When the real cockpit model is imported, tag interactive meshes with the
`meshNames` above (see ASSET_PIPELINE.md step 5). A Babylon picking layer
will resolve mesh → control id → same command path as the DOM controls; no
new per-switch logic.
