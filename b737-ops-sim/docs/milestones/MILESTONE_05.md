# Milestone 5 — Advanced Training (spec §22 Phase 5)

> **Goal:** the things that make a procedure trainer worth repeating — a route
> to fly, weather to fly it in, failures to handle, and the option of speaking
> to ATC instead of clicking.

**Status:** in progress (started 2026-08-02)

Phase 5 items from the spec: FMC and route entry · SID and STAR · weather ·
failures · rejected takeoff · go-around · engine failure · crosswind
operations · voice ATC · voice crew interaction.

Two of those are already done and stay done: the **rejected takeoff** (RTO
autobrake, review finding R-07) and the **go-around** (M3). This milestone
covers the rest.

## Decisions

| # | Decision | Rationale |
| --- | --- | --- |
| D1 | Route and procedures are **data in `@b737/shared`** (waypoints, one SID, one STAR, approach transitions), marked `NON_CERTIFIED_APPROXIMATION — SOURCE_REQUIRED` | Same rule as the runway and taxi data: geometry lives in one place and the UI, autopilot and scenarios all read it |
| D2 | The FMC is a **route model, not a CDU emulation**: origin/destination/runway, a SID, an arrival, and a leg list with the cross-track and distance the autopilot needs | A faithful CDU is months of work and teaches typing, not flying; the training value is in following a route |
| D3 | The autopilot gains **LNAV** as a roll mode alongside HDG SEL and LOC, tracking the active leg | Consistent with M3's mode logic and annunciated the same way |
| D4 | Weather is **scenario configuration plus live state**: surface wind, wind aloft, gust, visibility and turbulence, applied by the flight model | Crosswind operations are then just a scenario, not a special mode |
| D5 | Failures are **injected as commands/scenario events and expressed through existing systems state** — an engine failure sets the systems model's engine to not running, a generator failure drops its bus | The annunciator, checklists and debrief already read that state, so nothing needs a second failure path |
| D6 | Voice input maps an utterance to **an existing readback option**; the deterministic grader still decides correctness | Spec §12/§13: a language/speech layer may phrase or recognise, never judge |
| D7 | Voice input is **opt-in and warns** that the browser's speech recognition may send audio off the machine; it degrades to buttons when unavailable | The project is local-only by design; the user decides |

## Tasks

### T1 — Navigation data and route model (`@b737/shared`)

- Waypoints around KSFO with lat/lon, one SID (runway 28R departure) and one
  STAR/approach transition that joins the existing ILS 28R.
- `RouteLeg` (waypoint, course, distance) and helpers: active-leg selection,
  cross-track error, distance/bearing to the next waypoint.
- Unit tests for cross-track sign, leg sequencing and route construction.

### T2 — FMS state, commands and LNAV

- `AircraftState.fms`: route id, leg list, active leg index, distance to the
  next waypoint, cross-track error, desired track, and whether LNAV is armed.
- Commands: `load_route` (origin/destination/SID/STAR), `direct_to`,
  `set_lnav`.
- Mock autopilot: `LNAV` roll mode tracking the active leg, sequencing legs at
  the waypoint, falling back to HDG SEL when the route runs out.

### T3 — Weather

- `ScenarioInitialState.weather`: surface wind (already there) plus wind aloft,
  gust, visibility and turbulence.
- Flight model: wind varies with altitude, gusts perturb the airspeed and the
  track, turbulence perturbs attitude — all seeded, so a scenario stays
  reproducible.
- `AircraftState.weather` echoes what the aircraft is experiencing.

### T4 — Failures

- `inject_failure { failure }` with an enum: engine 1/2 flameout, generator
  1/2, hydraulic A/B, and (already possible) fuel pump loss.
- Scenario support: a rule/phase can inject a failure at a condition, so a V1
  cut happens because the aeroplane reached V1, not because a timer fired.
- Failures show up in the annunciator, the systems synoptic and the debrief.

### T5 — Crosswind operations

- A crosswind scenario using T3's weather; the debrief already scores
  centerline offset at touchdown and drift.

### T6 — Voice ATC and crew interaction

- Optional speech input that matches an utterance against the pending
  readback's option texts (token overlap, deterministic); the existing
  deterministic grader decides right or wrong.
- Existing TTS output stays as-is; both are toggles in the transcript panel.

### T7 — Scenarios

- `engine_failure_v1_ksfo_01` — engine failure just after V1: continue, clean
  up, return for a single-engine ILS.
- `crosswind_landing_ksfo_01` — approach and landing with a strong crosswind.
- `route_sid_star_ksfo_01` — depart on the SID, fly the arrival, join the ILS
  under LNAV.

### T8 — Web

- Route/FMS panel: legs, active leg, distance/cross-track, direct-to.
- ND draws the route ahead of the aircraft.
- Weather readout; failure indications through the existing annunciator.

### T9 — Documentation and DoD

`NAVIGATION_DATA.md` (what the route data is and is not), README, CHANGELOG,
`MILESTONE_05_DOD.md`, and the five-command verification with and without
generated assets.

## Non-goals

A real CDU (scratchpad, pages, LEGS/PROG/PERF), VNAV, performance
initialisation, holding patterns, offline speech recognition, weather radar,
and any failure that needs systems depth this trainer does not have (bleed
duct rupture, cargo fire, cabin pressurisation).
