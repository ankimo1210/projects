# Wave 1 re-flight — 2026-07-25

Live re-flight of the Phase 2 Wave 1 closed-loop acceptance
(`tests/live_p66_descent.rs::p66_soft_landing_closed_loop`) on branch
`eagle/wave1-review-fixes`, with `EAGLE_ATT_DEBUG` / `EAGLE_TELEM_OUT`
instrumentation.

**Status: RED.** The acceptance does not pass, and the failure is not the
attitude-loop sign error everyone (including this task's brief) assumed. The
diagnosis below is supported by packet-level and DSKY-level evidence from a
full instrumented run. Of the three causes, two are cheap (a model constant
— fixed here — and a scenario constant) and the third is design-level:
the AGC's pad-loaded state vector and the sim truth describe different
vehicles, so P66 would hold the wrong rate at the wrong attitude no matter
how the other two are tuned.

## Runs

| # | Scenario | Build | Class | v_vert | v_horiz | tilt | descent | MM |
|---|---|---|---|---|---|---|---|---|
| 0a | p66-gate | `34a7bec4` (earlier reviewer) | Crash | 40.30 m/s | — | 108.4° | 24.8 s | — |
| 0b | p66-gate | `fd39a65a` (earlier reviewer) | Crash | 40.30 m/s | — | 108.4° | 24.8 s | — |
| 1 | p66-gate | `ff71ff3b` (HEAD at task start) | Crash | 40.297 m/s | 0.0027 m/s | 108.196° | 24.80 s | `["  ","00","63","66"]` |
| 2 | p66-gate-fast | run 1 + idle-stop fix | **aborted in P63 entry**, FAILREG 01703 — never ignited | — | — | — | — | `["  ","00","63"]` |
| 3 | p66-gate | run 1 + idle-stop fix | Crash | 41.525 m/s | 10.739 m/s | 107.155° | 26.00 s | `["  ","00","63","66"]` |

Run 1 full summary line:

```
[accept] MM ["  ", "00", "63", "66"]
[accept] touchdown Some(TouchdownReport { class: Crash, v_vert_ms: 40.29734284950267,
         v_horiz_ms: 0.0026621251647267743, tilt_deg: 108.19567806491013,
         miss_m: 1585.1717405747422 }) descent Some(24.799999999977445)s
         drift -17900ms downlink 47.6wps
```

Run 1 aborted at the `td.class == Nominal` assert, so the `[accept] AGC
clock …` line never printed. Recomputed from the final telemetry frame in
`build/traces/telem-run1.jsonl` with the same formula the test uses:

- final frame `drift_ms = -17 900.0`, `t_s = 369.61`
- **`agc_rate = 1 + drift/1000/t_s = 0.952`** (4.8 % slow)
- `mid_downlink_wps = 47.59`, `pacing lost` not printed (same abort)

That is the first real measurement of the quantity the Task 6 rate gate
actually reads. It sits well inside the ±10 % bound with ~2× margin, so the
`PROVISIONAL` marker on that comment in `live_p66_descent.rs` has been
replaced with the measured number.

Free-fall check: 500 m at lunar g = 1.62 m/s² gives t = 24.85 s and
v = 40.25 m/s. Run 1 measured 24.80 s / 40.297 m/s — **zero thrust for the
entire descent**, to within the integrator's resolution.

## What actually happened (run 1, instrumented)

### 1. The attitude loop is healthy. It is NOT the bug.

`build/traces/att-debug-run1.log` (one line per 10 ticks, post-freeze):

```
t=342.91 jets=150 gimbal=[0.18,-16.83,0.00] omega=[0.0000,0.0157,0.0000] torque=[0.0,2114.5,0.0]
t=344.01 jets=150 gimbal=[0.18,-10.41,0.00] omega=[0.0000,0.1880,0.0000] torque=[0.0,2114.5,0.0]
...
t=356.21 jets=0   gimbal=[-0.34,108.72,0.47] omega=[0.0000,0.0031,0.0065] torque=[0.0,0.0,0.0]
t=367.91 jets=72  gimbal=[-0.26,108.43,1.05] omega=[0.0002,-0.0047,-0.0309] torque=[0.0,-1057.3,-1057.3]
```

Read the sign chain end to end: IGA starts at **−16.8°**, the DAP fires the
quad producing **+2114.5 N·m about body Y**, ω_y builds to +0.19 rad/s (the
DAP's rate limit), the gimbal slews monotonically −16.8° → +108.4° at
≈9.6°/s, and at t = 356.2 s ω_y collapses to +0.003 rad/s and the DAP
**captures and holds 107.35° ± 1.7° for the remaining 13 s** in a normal
deadband limit cycle (alternating `jets=105` / `jets=0`, torque −2114.5 /
0). Every firing opposes the standing gimbal error. (Band measured, not
eyeballed: the 137 samples at t ≥ 356 span 105.69°–109.02°.)

That is textbook negative feedback. All three suspects in the brief's list —
jet min-impulse quantization, `inertia_kgm2` / `RCS_LEVER_M` magnitudes,
trim-gimbal drive signs — are **exonerated**: a loop with the wrong sign
cannot capture, and one with the wrong plant gain cannot hold a bounded
3.3° limit cycle for 13 s. (The
trim bits are moot anyway: ch012 bits 9-12 were written exactly once, at
t = 179 ms, all zero — Luminary never drove the trim gimbal in this run.)

The 108° "tilt" is a **commanded** attitude, not a divergence. It is where
P63's braking guidance wants the thrust axis pointed given the AGC's state
vector (see cause 3).

### 2. Fatal cause A — the DPS idle stop was modelled as zero thrust.

`ch055` counter totals for the whole run: **MOUT 12 288, ZOUT 5 400, POUT
310**. Time-sliced around ENGINE ON (t = 342.799 s):

| window | pulses |
|---|---|
| TIG−30…0 s | ZOUT 1 193 |
| TIG+0…5 s | ZOUT 327 |
| TIG+5…15 s | ZOUT 632 |
| TIG+15…30 s | ZOUT 709, **POUT 310** |

The 12 288 MOUTs are pre-ignition: Luminary's `ENGINOF3` pre-engine-arm step
drives the THRUST counter to the actuator's zero stop three times
(`P40-P47.agc:490-494`). After ignition the AGC asks for **+310 pulses ≈
3.7 kN** and nothing more — the idle stop, which is where Luminary parks the
throttle for the whole ZOOMTIME trim phase.

`dps_envelope` returned **0 N** for anything below `DPS_MIN_N` (4560 N), so
3.7 kN became zero. `docs/agc-channel-map.md` ("Thrust Pulse Emissions")
already warned in as many words: *"a model that maps command 0 to zero
thrust free-falls through the burn-in."* It did.

Luminary itself noticed. Decoding the ch010 relay stream shows the DSKY
alternating **V06N63 ↔ V97** from t = 354.06 s (TIG+11 s) to touchdown —
V97 is DVMON's engine-fail annunciation. The AGC was telling us the engine
was not performing for the last 14 seconds of the fall and nothing was
watching.

Qualifier, so this is not over-read: **V97 still fires after the fix.**
Run 3 (idle stop live, 4560 N from ignition) raises it at TIG+11.3 s and
cycles it 19 times before contact — the same behaviour. DVMON's threshold
sits above the specific force an idling DPS produces, so V97 is evidence of
**too little thrust**, not of *zero* thrust. It corroborates cause A, it
does not by itself diagnose it; the 310-pulse ch055 count and
`thrust_n == 0` do.

**Fix applied (attempt 1):** `dps_envelope` now returns `DPS_MIN_N` below the
throttleable band instead of 0. Engine-off / out-of-fuel are unaffected —
`actuator_step` and `SimCore::phase3_throttle` zero the thrust outright, so
this branch only ever applies to a burning engine.

This was an *inconsistency between two models in this repo*, not a new
assumption: `runner.rs`'s `SyntheticHoverModel` (the Spike-B 1-D truth) has
always clamped to `DPS_MIN_N` at zero command, with a test named
`ignition_at_zero_command_holds_minimum_dps_thrust` whose comment cites the
same free-fall-through-the-burn-in failure (*"spike-B iter 6: −42 m/s by
MM66"*). The 6-DoF `forces.rs` model simply never got the same treatment.

### 3. Cause B — the gate is below Luminary's own burn-in. (Tunable.)

MM stayed **`63` for the entire descent**. `66` first appears at
t = 369.41 s = **TIG + 26.6 s**, i.e. 1.8 s *after* the vehicle had already
hit the ground at TIG + 24.8 s (0.6 s after, in run 3).

This is not slow scripting, and the mechanism is **`AVEGEXIT`, not
`PHASCHNG`**. P63TABLE's `AVEGEXIT` entry is `2CADR SERVEXIT`
(`BURN,_BABY,_BURN:143-144`); only `P63ZOOM` swaps it to `LUNLAND`
(`:573-575`, via `LUNLANAD`) at the end of the ZOOMTIME delay
(`ZOOMTIME = 2600 cs = 26 s`). GUILDENSTERN is R13, sitting immediately
after `LUNLAND` (`LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:127-144`), so the
only thing that can move an active landing program to P66 cannot run until
that swap happens. The choreography flips ATT HOLD at TIG+2 s and then
simply waits.

(`P40ZOOMA`'s `PHASCHNG OCT 3` is restart-table bookkeeping that tears down
the ZOOM restart entry at the *end* of `P63ZOOM`; `LUNLAND` immediately
re-establishes group 3 with `PHASCHNG OCT 05023`. An earlier draft of this
note blamed it. It is not the gate.)

Consequence: **P66 never flew.** Every "closed-loop P66 landing" claim in
the repo describes a phase the acceptance run has never reached.

**This one is a scenario fix, not a redesign.** The repo already knew:
`tests/live_spike_p66.rs:23-26` starts its truth at **3000 m** with the
comment *"High enough to survive the ~26 s ZOOMTIME trim phase at the DPS
idle stop (~450 m of altitude) before P66 can take over."* The acceptance
scenario's `alt_m = 500.0` simply ignored that known reason. Arithmetic at
9159 kg: idle net accel = 4560/9159 − 1.62 = **−1.12 m/s²**, so the burn-in
costs **379 m** and gains **29 m/s**, and arresting 29 m/s at FTP
(42 500 N ⇒ +3.02 m/s² net) needs a further **~140 m**. A gate around
**1000 m** clears B with margin; 3000 m clears it comfortably. One line in
`scenarios/p66-gate.toml`.

### 4. Cause C — no navigation loop closure. (The real blocker.)

`padload::generate_state` pad-loads the **historical PDI state**: r ≈
1752.6 km (15.2 km altitude), |v| = 1699.5 m/s. That is required for
`IGNALG`/`BURNBABY` to converge and ignite at all. The sim truth, meanwhile,
is a 500 m hover directly over the site. Nothing reconciles them: the only
shared channel is specific force through the PIPAs, which is consistent with
*both* stories during a coast.

Measured directly off the DSKY. V06N63 R2 is HDOTDISP in 0.1 ft/s:

```
t=343.5 s  P63  V06 N63  R2 = +00213      truth vz =  −0.9 m/s
t=353.5 s  P63  V06 N63  R2 = +00234      truth vz = −17.0 m/s
t=365.5 s  P63  V06 N63  R2 = +00266      truth vz = −36.5 m/s
```

The AGC believed it was **climbing at +21…+27 ft/s ≈ +6.5…+8.2 m/s** while
the truth fell at up to 43 m/s. P66's rate loop holds *the AGC's* believed
altitude rate (`VDGVERT` is seeded from `HDOTDISP` at `STARTP66`, and ROD
clicks move it from there), so even a perfect actuator model and an
arbitrarily high gate cannot produce a soft landing while the pad-loaded
state vector describes a different vehicle 15 km away doing 1700 m/s.

And the attitude compounds it. **P66 holds attitude; it does not
re-orient.** Whatever the vehicle is pointing at when GUILDENSTERN switches
it is what it keeps pointing at. What it is pointing at is the ignition
attitude `IGNALG` computed for a 1700 m/s braking burn — measured at
**107-108° from local vertical** in both runs, i.e. the DPS aimed almost
horizontally, with a *downward* thrust component. Raising the gate buys
time to arrive in P66 sideways. That, not gate altitude, is why no tuning
saves the acceptance.

## Fix attempts

**Attempt 1 — DPS idle stop (`dps_envelope`).** Rationale: cause A above,
directly measured (310 POUT vs a 4560 N floor) and already documented as a
known trap in `docs/agc-channel-map.md`. Change: below-band commands map to
`DPS_MIN_N`, not 0, with the Luminary citations in the doc comment. Unit
test updated to pin the new floor. `cargo test --workspace` green
(32+21+70+4+10 passed, 0 failed).

Result: run 3 in the table above (run 2, the intended fast validation, never
reached ignition — see below). The fix does exactly what it should and
nothing more:

```
[accept] MM ["  ", "00", "63", "66"]
[accept] touchdown Some(TouchdownReport { class: Crash, v_vert_ms: 41.5249803523929,
         v_horiz_ms: 10.739459714119823, tilt_deg: 107.15535477284625,
         miss_m: 1589.8432821954025 }) descent Some(25.999999999976353)s
         drift -17880ms downlink 47.6wps
```

- Thrust is now live from ignition: 1293 N on the first frame (the `DPS_TAU`
  ramp), then a flat **4560 N = `DPS_MIN_N`** for the whole descent.
- `ch055` POUT rose 310 → 751 — **but do not read that as the AGC trimming
  against a real acceleration.** Every one of run 3's POUTs arrives at
  t ≥ 368.799 s = TIG+26.0 s, i.e. at `FLATOUT` when ZOOMTIME ends, which
  is *at/after ground contact*; the sim only keeps running for the
  touchdown + 2 s tail. The difference between 310 and 751 is a longer
  trace, not better control. (An earlier draft of this note claimed
  otherwise.)
- Descent stretched 24.80 s → **26.00 s**, and MM66 still lands at
  **TIG+26.6 s** — the vehicle now misses P66 by 0.6 s instead of 1.8 s.
- `v_horiz` jumped 0.003 → **10.74 m/s** and `v_vert` rose 40.30 → 41.52.
  Both are correct: at the commanded 107° tilt the idle thrust has a
  −0.29 cos component (it pushes *down*) and a large sideways component.
  A crash that is now 4.5 t of engine pointed the wrong way, rather than an
  engine that silently does not exist.
- Clock: final-frame drift −17 880 ms over t_s = 370.81 ⇒ `agc_rate =
  0.952`, `mid_downlink_wps = 47.60` — reproducing run 1 to three decimals.

So the fix is validated as correct model behaviour, and it cannot make the
acceptance green on its own: causes B and C are untouched and both are fatal
by themselves.

**Attempt 2 — none.** Stopped deliberately, short of the 3-attempt budget.
Cause C is not a tunable constant and cause B, though it *is* a one-line
scenario change (raise `alt_m`), only buys the run enough life to arrive in
P66 sideways at the wrong rate — so no combination available in the
remaining budget could have turned the acceptance green, and each attempt
cost 7 minutes of flight. See "For the next engineer" for the order to do
them in.

## Incidental finding: `p66-gate-fast` could not ignite

Run 2 (`make descent-p66-fast`) aborted during P63 entry:

```
Error: scenario choreography
Caused by:
    0: P63 dialog
    1: PROG alarm during P63 entry: FAILREG = 01703 00000 00000
```

01703 is "IGNITION TIME SLIPPED" (`P40-P47.agc:101`: *TIG LESS THAN 45 SECS
AWAY*; set by `INTEGRATION_INITIALIZATION.agc:1029`). The scenario's
`tland_offset_cs = 24000` (240 s) does not leave BURNBABY its 45 s pre-TIG
margin once the pad-load, flag-set and P63 dialog have run on this host —
the very risk its own comment flagged. Raised to **30000** (300 s), which
splits the two measured points evenly: 60 s saved against the acceptance
gate's 36000 (known good), 60 s of clearance above 24000 (known bad). Not
flown — if 01703 reappears, fall back to 36000. The debug loop is only
useful if it ignites.

## Incidental bug found and fixed

`make dev-runtime`, `make descent-p66` and `make descent-p66-fast` were all
**broken**: they run `cargo run -p eagle-runtime`, which is ambiguous
because the package auto-discovers three binaries (`eagle-runtime`,
`descent_probe`, `padload_gen`). Every invocation died with

```
error: `cargo run` could not determine which binary to run.
```

Fixed by adding `default-run = "eagle-runtime"` to
`runtime/apps/eagle-runtime/Cargo.toml`. Broken since the SECOND binary
landed, which was `padload_gen` in `ef728d99` (Wave-1 **Task 5**) — not
`descent_probe` (`7a01841b`, Task 6), as an earlier draft of this note
said. Either way the "run it and watch the ENGR tab" workflow in
README/CLAUDE.md has never worked as written.

## Incidental fix: the telemetry could not see cause C

`sim.rs`'s `parse_agc_nav` accepted **only V06N60**. N60 is P66's own
display, and this run never reaches P66 — so `agc_hdot_ms` and
`nav_err_hdot_ms` were `null` in **every frame of both telemetry dumps**,
and the single most important measurement in this whole investigation (the
AGC believing it was climbing) had to be recovered by hand-decoding the
ch010 relay stream after the fact.

N63's R2 is the same HDOTDISP word — `docs/agc-channel-map.md` says so
explicitly ("N63's R2 is also HDOTDISP", `PINBALL_NOUN_TABLES.agc:724-726`)
— so `parse_agc_nav` now accepts N60 **and** N63, with a unit test
(`agc_nav_parses_hdot_from_both_n60_and_n63`) pinning the scaling, the sign
and the rejection of other displays. The next live run measures cause C
automatically, in `nav_err_hdot_ms`, without a decoder.

## ENGR manual check (Wave-1 Task 15 Step 6)

**Not performed; still open.** Two reasons, both honest: this session has no
browser to open `http://localhost:5173` with, and the check as specified
("clicking `ROD −1 ft/s` twice visibly steepens the descent-rate trace") is
not observable on the current build — the ROD schedule only becomes
meaningful in P66, which the run never reaches before ground contact. The
strip charts themselves would render for the ~30 s of descent. Task 15
Step 6 is deliberately left unchecked.

## For the next engineer

**Cause B is cheap; cause C is the one that needs design work.** An earlier
draft of this note called both design-level. That was wrong about B: raise
`alt_m` in `scenarios/p66-gate.toml` from 500 to ~1000-3000 m and the
vehicle survives the burn-in (see cause B's arithmetic, and
`live_spike_p66.rs`, which already does exactly this at 3000 m). Do that
first — it is one line and it makes every subsequent run actually reach
P66, which is the only way to observe C directly.

Then C bites, in two ways at once, and neither is tunable:

- **Rate.** P66 holds the AGC's believed `HDOTDISP`, which is +7 m/s
  climbing against a truth that is falling.
- **Attitude.** P66 holds attitude and does not re-orient, so the vehicle
  enters P66 carrying `IGNALG`'s 1700 m/s braking attitude — 107-108° from
  vertical, DPS pointed sideways and slightly down.

Both follow from the same root: the pad-loaded state vector and the sim
truth describe different vehicles. Ranked options for fixing that:

1. **Fly the real descent.** Initialise the sim truth to the same PDI state
   `generate_state` pad-loads (15.2 km, 1699.5 m/s) and let P63 → P64 → P66
   run for real. This is the only variant where the AGC's nav and the truth
   agree by construction. Costs: ~11 min of *descent* sim time on top of the
   boot choreography; the DPS fuel load (`fuel_dps_kg = 2000`) is nowhere
   near a braking phase and would need the real ~8 t; landing-radar
   behaviour would need review (no LR model today).
2. **Pad-load a gate-consistent state.** Keep the 500 m gate but generate
   RN/VN (and TLAND) from it, and find another way into P66 that does not
   need `IGNALG` to converge on an orbital ignition point. Cheaper, but it
   means the run no longer exercises the historical P63 entry, and
   GUILDENSTERN still only switches an *active* landing program.
3. **Independently of the choice, raise the gate** so it clears the 26 s
   ZOOMTIME burn-in with margin: at the idle stop the vehicle loses ≈379 m
   and gains ≈29 m/s before the first guidance pass can run, plus ≈140 m to
   arrest that at FTP. Do this one first; it is free and it unblocks
   measurement of everything else.

Do not spend more time on the attitude loop. It works.

## Artefacts

All under `build/traces/` (git-ignored, regenerate by re-running):

- `p66-acceptance.jsonl` — full packet trace, run 1 (81 447 rows, 373.5 s)
- `telem-run1.jsonl` — per-frame telemetry, run 1
- `att-debug-run1.log` — attitude sign-chain trace, run 1 (268 lines)
- `run1.out` — test stdout/stderr
- `telem-run2.jsonl`, `run2.out` — run 2 (aborted pre-ignition; no
  `att-debug-run2.log`, the freeze never released)
- `telem-run3.jsonl`, `att-debug-run3.log`, `run3.out` — run 3
  (`p66-acceptance.jsonl` is overwritten by each acceptance run and now
  holds run 3)
