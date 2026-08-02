# Navigation Data

The route data this trainer flies, and what it is not.

**NON_CERTIFIED_APPROXIMATION — SOURCE_REQUIRED.** Every fix and procedure
below was invented for this project around the KSFO 28R datum in
`packages/shared/src/airports.ts`. The names resemble nothing real, the
coordinates are derived from the runway rather than surveyed, and none of it may
be used for navigation. It exists so there is a route to fly in the mock world.

Source: `packages/shared/src/navigation.ts`.

## Fixes

Authored in runway coordinates (`along` = NM from the 28R threshold along the
runway course, `cross` = NM right of it), then converted to lat/lon so they line
up exactly with the runway and ILS geometry.

| Fix   | Along | Cross | Altitude | Speed | Used by             |
| ----- | ----: | ----: | -------: | ----: | ------------------- |
| SFOUT |     4 |     0 |    2,000 |   210 | SID                 |
| BAYNE |     8 |     5 |    4,000 |   250 | SID                 |
| WESTB |    10 |    14 |    6,000 |     — | SID                 |
| SOUTA |    −2 |    16 |    5,000 |   250 | arrival             |
| MIDBA |    −8 |    10 |    3,000 |   210 | arrival             |
| FINAL |   −12 |     0 |    2,000 |   180 | arrival             |
| FAFXX |    −6 |     0 |    1,900 |   160 | approach transition |

## Procedures

| Id       | Kind                | Fixes                 | Description                                        |
| -------- | ------------------- | --------------------- | -------------------------------------------------- |
| `SFOUT1` | SID                 | SFOUT → BAYNE → WESTB | Runway heading, then right toward the bay          |
| `BAYIN1` | STAR                | SOUTA → MIDBA → FINAL | From the south-east onto the final approach course |
| `ILS28R` | approach transition | FAFXX                 | Final approach fix for the ILS                     |

## Route model

`buildRoute()` turns a fix list into legs, computing each course and distance
from the geometry (nothing is authored twice). `trackLeg()` returns distance to
the fix, signed cross-track error (positive = right of course) and a desired
track with a bounded intercept angle — 35° at 1.5 NM off, proportionally less
closer in. A leg sequences when the fix is inside 0.6 NM **or** behind the
aircraft, so passing wide of a waypoint does not leave the autopilot chasing it.

`headingForTrack()` is the wind triangle: given a desired track, true airspeed
and the wind, it returns the heading that makes the track good. LNAV uses it, so
the aeroplane crabs in a crosswind instead of being blown off the leg.

## Autopilot integration

LNAV is a roll mode alongside HDG SEL and LOC (see the PFD's FMA). Arming the
approach still wins: LOC capture takes the aeroplane off the route and onto the
localizer, which is what the procedure expects.

## Not modelled

A real CDU (pages, scratchpad, LEGS/PROG/PERF), VNAV and altitude/speed
constraint flying (the constraints are displayed, not enforced), holding
patterns, missed-approach procedures as route data, airways, alternate routing,
performance initialisation, and any navaid other than the ILS the mock model
already provides.

## FlightGear mode

The route model is trainer-side. In FlightGear mode the sim owns navigation, so
`load_route`, `direct_to`, `set_lnav` and the failure commands are rejected with
a message pointing here, and `AircraftState.fms` is reported empty. Wiring the
trainer's route to a FlightGear route manager is future work and needs a real
installation to verify against.
