# Milestone 4 — Definition of Done verification

Verified 2026-08-02 on WSL2 (Ubuntu), Node v22.22.2, pnpm 11.1.0, at the commit
that contains the code.

```
pnpm test        PASS — 181 unit/integration tests, 7 packages
pnpm test:e2e    PASS — 5 Playwright specs (with built assets)
pnpm typecheck   PASS
pnpm lint        PASS
pnpm build       PASS
```

| #   | Requirement (MILESTONE_04.md)             | Status | Evidence                                                                                                                                                                                                               |
| --- | ----------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T1  | Systems in the shared schema              | ✅     | `packages/shared/src/systems.ts`: electrical, APU, pneumatic, fuel, hydraulic, ice protection, IRS, per-engine start state, annunciations, master caution/warning + `coldAndDarkSystems()` / `enginesRunningSystems()` |
| T2  | Systems model as a dependency graph       | ✅     | `systemsModel.ts` stepped from the flight model at 60 Hz; `systemsModel.test.ts` 17 tests (electrical, APU, engine start, hydraulics, IRS, annunciations)                                                              |
| T3  | Commands, bridge validation, property map | ✅     | `set_system_switch` (28 ids), `set_engine_start`, `reset_master_caution` in the shared schema, applied by the mock with interlocks; property map v4 carries placeholder mappings marked AIRCRAFT-MODEL-DEPENDENT       |
| T4  | Warning system                            | ✅     | Annunciations derived every tick with severity; master caution/warning latch, recall acknowledges, a cleared-and-returned condition lights again (`annunciations` tests)                                               |
| T5  | Overhead panel, synoptic, annunciators    | ✅     | `OverheadPanel.tsx` (8 switch groups + start selectors), synoptic rows, annunciator strip; `overheadPanel.test.ts` asserts every schema switch is reachable; e2e drives it                                             |
| T6  | Cold-and-dark scenario                    | ✅     | `coldAndDark.ts`: phases gated on systems facts, Preflight / Before Start (systems) / After Start checklists validated against `systems.*`, then the gate-to-gate taxi flow                                            |
| T7  | Tests                                     | ✅     | 17 systems unit tests; golden test "brings the aeroplane from cold and dark to both engines running"; e2e "overhead panel powers the aircraft up from cold and dark"                                                   |
| T8  | Documentation                             | ✅     | SYSTEMS_MODEL.md, README, CHANGELOG, this file                                                                                                                                                                         |

## What the golden test actually proves

Starting from every system off, the scripted crew: switches the battery on (DC
bus comes up, `NO AC POWER` annunciates), starts the IRS aligning, starts the
APU on the battery, puts its generator on the bus, sets fuel pumps and APU
bleed, completes the Before Start checklist (which is what clears the start),
motors each engine to ~25 % N2, raises each start lever, sees both engines
reach idle with the starter cutting out, puts the generators on, swaps to
engine bleeds and packs on, pressurises both hydraulic systems, completes After
Start with no caution-or-worse annunciations left, releases the parking brake
and moves. Every one of those steps is judged from `AircraftState.systems`.

The e2e proves the same path through the real browser and bridge for the first
half (battery → APU running → generator → refused engine start without bleed).

## Notable engineering facts

- Switch interlocks must see the world the previous switch created: buses,
  duct pressure and fuel pressure are recomputed immediately on every switch,
  not on the next physics tick. Without that, "battery on, then APU start" in
  the same tick failed with "no DC power".
- Starter cut-out has to be independent of whether the engine has lit, or a
  successful start leaves the selector stuck at GND.
- The packs-off-for-start rule is not a special case: two packs take 16 psi off
  a 35 psi APU bleed, which is below the 25 psi the starter needs.

## Known limitations

- Procedure depth only: no electrical loads, fuel burn, crossfeed, pack
  temperatures, standby hydraulics, EGT limits, hot/hung starts or failures.
  The full list is in SYSTEMS_MODEL.md.
- FlightGear mode reports the engines-running baseline for `systems` and its
  command mappings are placeholders — they need `pnpm fg:diagnostic` against a
  real installation (FlightGear is still not installed here).
- IRS alignment is compressed to 60 s so a training session can proceed.
- The 3D overhead switches remain visual only; systems are operated from the
  DOM overhead panel (unchanged since M2).
