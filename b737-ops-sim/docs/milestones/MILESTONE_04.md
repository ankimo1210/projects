# Milestone 4 — Aircraft Systems (spec §22 Phase 4)

> **Goal:** start the aeroplane. From cold and dark: battery, APU, generators,
> IRS alignment, fuel, engine start on APU bleed, hydraulics and packs — with a
> warning system that tells the crew when a system is not where the procedure
> says it should be.

**Status:** Complete (2026-08-02) — see [MILESTONE_04_DOD.md](MILESTONE_04_DOD.md).

Phase 4 items from the spec: cold and dark · APU · engine start · electrical ·
fuel · hydraulic · pneumatic and bleed air · anti-ice · IRS · more complete
warning systems.

## Decisions

| #   | Decision                                                                                                                                                                                                                  | Rationale                                                                                             |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| D1  | Systems are **state in the shared schema** (`AircraftState.systems`), modelled in the mock backend and mapped (optionally) in the FlightGear property map                                                                 | Same contract as every other signal; the UI and scenarios never read a private model                  |
| D2  | The model is a **dependency graph evaluated every physics step**: sources (battery, APU gen, engine gens) → buses → consumers (pumps, packs, avionics). Nothing is scripted; each system asks "am I powered/pressurised?" | Deterministic, testable, and interlocks fall out of the graph instead of being special-cased          |
| D3  | Engine start is a **sequence with real preconditions**: duct pressure from the APU (or external air), start switch to GND, N2 rotation, fuel introduced at ~25 % N2, light-off, idle, start valve closes                  | "Engine start" as a procedure the crew can get wrong is the point of the milestone                    |
| D4  | Switches are one command — `set_system_switch { switch, position }` with an enum of switch ids — plus `set_engine_start { engine, mode }`                                                                                 | Twenty command types would not be more explicit; the enum is the contract and the bridge validates it |
| D5  | The warning system is **derived** from systems state each tick (annunciation list + master caution/warning latch), not stored ad hoc                                                                                      | Spec §12/§16: everything the crew is told must be reproducible from state                             |
| D6  | Systems couple back into the flight model only where it is honest: engines produce thrust only when running; with both hydraulic systems unpressurised the gear/flaps/speed brake do not move                             | Enough to make the procedure matter without pretending to model alternate/standby systems             |
| D7  | Numbers (spool times, alignment time, pressures) are `NON_CERTIFIED_APPROXIMATION`, marked in code                                                                                                                        | Same standard as the flight model                                                                     |
| D8  | Mock-only again: FlightGear systems properties are aircraft-package specific, so the map entries are optional and FG mode reports what it can                                                                             | FlightGear is still not installed here                                                                |

## Tasks

### T1 — Systems schema (`@b737/shared`)

`AircraftState.systems` with: electrical (battery switch/voltage, APU gen,
engine gens 1/2, external power, transfer bus 1/2 powered, standby power),
apu (off/starting/running/shutting-down, N1 %, EGT), pneumatic (duct pressure,
engine bleeds, APU bleed, isolation valve, packs), fuel (pumps per tank,
quantity per tank), hydraulic (A/B pressure, engine-driven and electric pumps),
ice protection (engine/wing anti-ice), irs (off/aligning/aligned + progress),
engines (running, N2, start valve, start switch position, oil pressure),
and `annunciations` + `masterCaution` / `masterWarning`.

### T2 — Mock systems model

`packages/flightgear-adapter/src/mock/systemsModel.ts`, stepped from the flight
model at the same fixed rate:

- electrical sources and bus logic (battery → standby; APU gen or engine gens →
  transfer buses; external power on the ground)
- APU start/run/shutdown with spool times, drawing from the battery
- engine start sequence with duct-pressure and start-switch preconditions
- fuel pumps requiring AC power; engines needing fuel pressure to run
- hydraulics: engine-driven pumps with the engine running, electric pumps with
  AC power; pressure builds/decays
- pneumatics: APU bleed or engine bleeds → duct pressure → packs
- IRS alignment timer (fast alignment for training, marked as such)
- anti-ice consuming bleed air

### T3 — Commands, bridge and property map

`set_system_switch` (enum of switch ids) and `set_engine_start`, validated in
`@b737/shared`, applied by the mock with interlocks that reject impossible
requests, added to the FlightGear property map as optional entries.

### T4 — Warning system

Derived annunciations with severity (advisory / caution / warning), master
caution and master warning latches with a recall/reset command, and the
existing GPWS-style callouts left alone. Exposed as data so the debrief and the
UI both read the same list.

### T5 — Web: overhead panel, synoptic, annunciators

- Overhead panel (DOM) driven by the control registry: electrical, APU, fuel,
  hydraulic, bleed, anti-ice, IRS groups — every switch displays backend state.
- A systems synoptic panel (buses, pressures, quantities) for training.
- Annunciator strip with master caution/warning and the active list.

### T6 — Cold-and-dark scenario

`cold_and_dark_ksfo_01`: battery on → APU start → generators on → IRS align →
fuel pumps → engine start (both) → after-start items → hand over to the
gate-to-gate flow. Checklists: Preflight, Before Start, After Start, with every
item validated against systems state.

### T7 — Tests

Unit tests for the systems model (bus transfer, APU start, both engine start
paths, hydraulic loss, annunciation latching), a golden test that brings the
aeroplane from cold and dark to both engines running and taxi-ready, and an
e2e that operates the overhead panel in the browser.

### T8 — Documentation and DoD

`SYSTEMS_MODEL.md` (what is modelled, what is not, and the approximations),
README capabilities, CHANGELOG, `MILESTONE_04_DOD.md`, and the same five-command
verification with and without generated assets.

## Non-goals

FMC/route entry, SID/STAR, weather, failures beyond what the interlocks
naturally produce, voice interaction (Phase 5). No attempt at real electrical
load numbers, fuel burn per tank, or certified system logic — this is a
procedure trainer, not a systems simulator.
