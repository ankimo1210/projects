# Coordinate Frames

Reference for the frame system defined in `eagle-dynamics` (spec §3,
`docs/superpowers/specs/2026-07-22-eagle-phase2-closed-loop-design.md`).
Frames are enforced at compile time: every vector is a `V3<F>` tagged with
its frame `F`, and every rotation is a `Rot<A, B>` that maps `A`-frame
coordinates to `B`-frame coordinates. No anonymous `[f64; 3]` crosses a
function boundary anywhere in the codebase (architecture spec §5.3) — a
function that needs a vector in a specific frame says so in its signature,
and the compiler rejects a vector from the wrong frame.

## Frame table

| Frame | Marker type | Role |
|---|---|---|
| MCI (moon-centered inertial) | `Mci` | physics integration frame |
| MCMF (moon-centered, moon-fixed) | `Mcmf` | terrain, landing site |
| LSITE (site-local, East-North-Up) | `Lsite` | telemetry, success criteria |
| BODY (LM structural) | `Body` | thrust, inertia |
| SM (IMU stable member) | `Sm` | REFSMMAT-related; CDU angles generated here |

All frames are right-handed. Internal state is SI units throughout
(meters, seconds, radians); see "AGC-unit conversion" below for the one
place this changes.

## Conventions

**MCI** — inertial frame fixed at scenario epoch. `+z` is the lunar pole
(north), matching the moon's spin axis at epoch. `x`/`y` span the
equatorial plane and do not rotate with the moon; this is the frame RK4
integrates the equations of motion in (`eagle-dynamics` §4).

**MCMF** — moon-fixed frame, related to MCI by a pure rotation about the
shared `+z` (pole) axis: `MCMF = R_z(-OMEGA_MOON * t) · MCI`, i.e.
`mci_to_mcmf(t_s)` in `frames.rs`. At `t = 0` the two frames coincide.
Terrain and the landing site are fixed in this frame; it is the frame the
site-relative LSITE basis is built from (`mcmf_to_lsite`).

**LSITE** — local East-North-Up (ENU) frame at a given surface site. `x` =
East, `y` = North, `z` = Up (radially outward through the site). Built from
a unit MCMF site vector: Up is the site direction itself, East is
`pole × Up` (normalized), North completes the right-handed set as
`Up × East`. This is the frame telemetry and landing success criteria
(touchdown velocity/tilt) are expressed in.

**BODY** — LM structural frame, origin at the vehicle center of mass.
`+X` is the thrust axis, pointing up through the overhead docking hatch
(nominal DPS thrust accelerates the vehicle along `+X`). `+Z` points
forward, out the commander's/LMP's windows. `+Y` completes the
right-handed frame. Dynamics (thrust, RCS torques, inertia tensor) are
expressed in this frame.

**SM** — the IMU's inertially-stabilized "stable member" frame, the frame
CDU gimbal angles are measured against. Defined once, at scenario start,
as **identical to the initial BODY attitude**: `SM ≡ BODY(t=0)`. This is
what makes yaAGC's zeroed CDU counters agree with our own attitude state
at `t = 0` — coarse-align sets the IMU's stable member to the vehicle's
current attitude, and by fixing SM to the t0 body pose we start both sides
of the simulation (physics and AGC) from the same zero. After `t = 0`, SM
stays fixed in inertial space while BODY rotates with the vehicle; the
angle between them is what the CDUs report.

## AGC-unit conversion

Every quantity inside `eagle-dynamics` and `eagle-sensors` dynamics state
is SI (meters, m/s, radians, seconds). The Apollo Guidance Computer talks
in pulse counts, not SI, and that conversion happens in **exactly one
place**: the counter codec boundary in `eagle-sensors`. The scale
constants that boundary uses are defined in `eagle-dynamics::constants`
with their provenance cited (historical measurement, a value derived from
another sourced constant, an engineering `assumed` value pending
calibration, or a direct `LM_Simulator` file:line citation):

- `PIPA_INCR` — PIPA ΔV per pulse (accelerometer counter codec).
- `CDU_INCR_DEG`, `COARSE_INCR_DEG`, `GYRO_FINE_INCR_DEG` — CDU/IMU angle
  per pulse (gimbal angle counter codec).
- `THRUST_N_PER_PULSE`, `DINC_MAX_PER_TICK` — DPS throttle counter codec.

No other module performs an AGC-unit conversion; if a future module needs
one, it should call into the codec rather than hardcoding a scale factor.
