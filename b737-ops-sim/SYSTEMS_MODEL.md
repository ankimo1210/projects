# Systems Model

What the aircraft systems do in this trainer, and — just as important — what
they do not. Everything here is `NON_CERTIFIED_APPROXIMATION`: the structure
follows 737-class systems at the depth a procedure trainer needs, with round
numbers chosen for plausible behaviour. None of it is FCOM data and none of it
may be used for real-world operations.

Implementation: `packages/flightgear-adapter/src/mock/systemsModel.ts`
(mock mode). Schema: `packages/shared/src/systems.ts` — the browser and the
scenario engine only ever read `AircraftState.systems`.

## How it works

The model is a dependency graph evaluated every physics step (60 Hz):

```
battery / external / APU gen / engine gens ──► DC bus, AC transfer buses
                                                │
                          ┌─────────────────────┼────────────────────┐
                          ▼                     ▼                    ▼
                   fuel pumps            electric hyd pumps      IRS align
                          │                     │
APU bleed / engine bleeds ─┴──► duct pressure ──┴──► packs, anti-ice, starters
```

Interlocks are consequences of the graph rather than special cases:

| Procedure error                          | What the model does                                       |
| ---------------------------------------- | --------------------------------------------------------- |
| APU start with the battery off           | command rejected: "no DC power for the APU starter"       |
| Generator on with its engine stopped     | command rejected: "engine 1 is not running"               |
| Engine start with no APU bleed           | command rejected: "not enough duct pressure"              |
| Engine start with the packs on APU bleed | duct pressure falls below 25 psi → the start is refused   |
| Start lever raised with no fuel pressure | command rejected: "no fuel pressure"                      |
| Taxi with both hydraulic systems down    | gear, flaps and spoilers stop moving; scenario rule fires |

## Timings and thresholds (all approximations)

| Quantity           | Value                             | Note                                              |
| ------------------ | --------------------------------- | ------------------------------------------------- |
| APU start          | 25 s to 100 % N1                  | EGT peaks partway through                         |
| APU shutdown       | 12 s                              | generator drops immediately                       |
| Starter motoring   | ~4.5 % N2/s to 30 %               | needs ≥ 25 psi duct                               |
| Light-off          | 25 % N2 with the start lever open |                                                   |
| Starter cut-out    | 56 % N2                           | valve closes, selector springs back to OFF        |
| Idle               | 62 % N2                           | engine counted as running above 50 %              |
| Hydraulic build-up | 900 psi/s to 3000 psi             | decay 600 psi/s                                   |
| Hydraulics usable  | ≥ 1500 psi in system A or B       | below that the surfaces stop                      |
| APU bleed          | 35 psi                            | engine bleed 32 psi                               |
| Pack demand        | 8 psi each                        | anti-ice 3 psi (wing 6)                           |
| IRS alignment      | 60 s                              | **compressed**: real alignment is several minutes |

## Warning system

Annunciations are derived from systems state every tick — nothing is stored
except which ones the crew has acknowledged. Master caution/warning lights when
an unacknowledged caution/warning condition exists; the recall button
acknowledges everything currently displayed, and a condition that clears and
returns lights the master again.

Current list: `NO AC POWER`, `GEN 1/2 OFF BUS`, `FUEL LOW PRESSURE`,
`HYD SYS A/B LOW PRESSURE`, `ENG 1/2 LOW OIL PRESSURE`,
`ENG 1/2 START VALVE OPEN`, `IRS ALIGN`, `IRS OFF`.

## Deliberate simplifications

- **Bus structure**: any AC source powers both transfer buses. Real bus tie /
  transfer logic, load shedding and the standby inverter are not modelled.
- **Fuel**: quantities are static; there is no burn, no crossfeed and no tank
  sequencing. `pressurised` is a single boolean for the whole engine feed.
- **Hydraulics**: system A is fed by engine pump 1 and electric pump 2, system B
  by engine pump 2 and electric pump 1. No standby system, no PTU, no reservoir
  quantity, no brake accumulator.
- **Pneumatics**: one duct pressure for the whole aeroplane; the isolation valve
  is state but does not split the duct. No pack temperature or pressurisation.
- **Engines**: N2 and oil pressure only; no EGT limit, no hot/hung start, no
  N1 spool interaction with the flight model beyond "running or not".
- **IRS**: a single alignment timer; no position entry, no drift, no attitude
  loss when it is off.
- **Anti-ice**: consumes duct pressure; it has no effect on performance or on
  any icing model (there is no weather).
- **Electrical loads**: nothing has a load. A bus is powered or it is not.

## FlightGear mode

Systems properties are aircraft-package specific. `config/flightgear/737-800-property-map.json`
carries the command mappings (`set_system_switch.*`, `set_engine_start.*`) as
`AIRCRAFT-MODEL-DEPENDENT`, and FlightGear mode currently reports the
engines-running baseline for `AircraftState.systems` rather than inventing
values. Verify with `pnpm fg:diagnostic` once FlightGear is installed, then map
the real properties.
