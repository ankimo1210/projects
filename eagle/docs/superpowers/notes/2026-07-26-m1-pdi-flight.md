# Wave 2 M1 — live PDI descent flights, 2026-07-26

Live flights of `scenarios/pdi-descent.toml` (`make descent-full`) on branch
`eagle/wave2-m1`: real Luminary099 in vendored yaAGC, truth started at the
pad-load's TIG state, landing radar bypassed in-rope, no crew.

Every run instrumented (`EAGLE_ATT_DEBUG`, `EAGLE_TELEM_OUT`, stdout tee'd,
`--trace-out` from flight 2 on) into `build/traces/` (git-ignored,
per-run filenames).

**Headline: M1 flies the real profile — PDI to P66 with the radar bypassed
and no alarms — and does not yet land. Two blockers were found and fixed
by flying, both unit/scale errors in our own vehicle model against the
rope; a third (P66's rate loop) is open and named.**

The first was a unit error in our own accelerometer model, and only a live
descent could have exposed it. `PIPA_INCR` was 0.0585 m/s per
pulse (LM_Simulator's constant); Luminary099 decodes PIPA counters at
**0.01 m/s per pulse**, so the AGC's navigation was integrating 1/5.85 of
the ΔV the sim delivered. Nothing downstream — guidance, DAP, the
handover, the ROD schedule — could work until that was fixed, and no
static test in this repo could have caught it: it only exists at the
seam between our physics and the rope's own scaling constants.

The same seam produced three more (found in review, flown as flight 6):
`THRUST_N_PER_PULSE` 12.0 → **12.531966** N/bit, DPS full throttle
46 706 → **48 145.4** N, `DPS_TAU` 0.3 → **0.2** s, all from four
consecutive lines of `CONTROLLED_CONSTANTS.agc`. **Every physical constant
in the propulsion and accelerometer chain is now the flown rope's own
number.** See "Fix round 1".

## Runs

| # | Build | ENGINE ON | MM seen | Outcome | v_vert | v_horiz | tilt | descent |
|---|---|---|---|---|---|---|---|---|
| 1 | HEAD (`b0f79774`) + descent-full | t=343.6 s | `00`,`63` | **Crash** | 222.62 m/s | 1223.88 m/s | 113.1° | 197.6 s |
| — | (diagnostic re-fly, cancelled 5 min in — the offline fit below had already answered it; no data) | | | | | | | |
| 2 | + `PIPA_INCR = 0.01` | t=343.6 s | `00`,`63`,`64`,`65` | **Crash** | 123.01 m/s | 411.61 m/s | 119.8° | 450.5 s |
| 3 | + `DPS_MAX_N/FTP = 46706` | t=343.6 s | `00`,`63`,`64`,`65`,`66` | **Crash** (out of DPS propellant) | 83.99 m/s | 38.77 m/s | 8.8° | 896.9 s |
| 4 | + handover 250 m, rod `[[245,-5.3],[50,-0.3],[12,0.7]]` | t=343.6 s | **`00`,`63`,`64`,`66`** | **Crash** (P66 rate loop bang-bang → climb-away → tank dry) | 44.09 m/s | 59.81 m/s | 11.2° | 866.9 s |
| 5 | + rod `[[240,-1.5],[40,0.2],[10,0.8]]` (gentler steps) | t=343.6 s | **`00`,`63`,`64`,`66`** | **Crash** (same limit cycle, smaller amplitude) | 13.58 m/s | 66.91 m/s | 12.0° | 848.6 s |

| 6 | + `THRUST_N_PER_PULSE = 12.531966`, `DPS_MAX_N/FTP = 48145.4`, `DPS_TAU = 0.2` (review round 1) | t=343.6 s | **`00`,`63`,`64`,`66`** | **Crash** (limit cycle survives) | 30.86 m/s | 60.04 m/s | 12.8° | 865.1 s |

**Flights used: 6 of 6** (plus one cancelled diagnostic re-fly that
produced no data). Budget exhausted.


## Flight 1 — the nav divergence, measured

Choreography was clean: no PROG alarms (`[accept] alarm episodes []`,
`PROG lamp frames after ignition 0`), LRBYPASS read back set on a fresh
start as predicted, ENGINE ON at t = 343.6 s (Wave 1 measured 342.8 s for
the same 36000 cs lead), `sim pacing lost 0 ms`, AGC clock 0.949× real
time, downlink 47.4 wps. The freeze/TIG design works: at ENGINE ON truth
was 15212.5 m / 1699.5 m/s with the AGC's own hdot within ~1.6 m/s of
truth.

Then the two states walked apart, monotonically, for the whole burn:

| TIG+ | truth alt | truth vz | AGC hdot (V06N63 R2) | `nav_err_hdot_ms` |
|---|---|---|---|---|
| 20 s | 15230.0 m | +1.65 m/s | −0.03 m/s | −1.68 |
| 60 s | 14978.2 m | −21.09 m/s | −1.58 m/s | +19.50 |
| 100 s | 13327.9 m | −63.68 m/s | −6.83 m/s | +56.85 |
| 140 s | 9706.9 m | −119.58 m/s | −14.11 m/s | +105.46 |
| 180 s | 3589.4 m | −188.43 m/s | −24.84 m/s | +163.59 |
| 197.6 s | 0 (contact) | −222.62 m/s | −29.7 m/s | +193 |

MM64 never appeared — HIGATE is an altitude/energy gate on the AGC's own
state, and by its books it was still at ~13 km when the vehicle hit the
ground. The attitude loop was healthy throughout: IGA slewed −16.9° →
119° in ~20 s and then held 118-120° ±1.5° in a normal deadband limit
cycle for 200 s (`build/traces/att-m1-run1.log`).

### Isolating it offline, before spending another flight

Everything in the frame chain checked out on inspection — the pad-loaded
REFSMMAT rows (`generate_state`: `[x̂, −ẑ, ŷ]`) are exactly the sim's
initial body attitude (`pdi_truth_state`: `Rx(−90°)`), so SM ≡ the AGC's
stable member and the PIPA components land on the right axes; `forces()`
and `phase6_sensors` divide the *same* `body_thrust_force` by the *same*
mass, so the ΔV the PIPAs report is the ΔV the truth integrates.

So the question became quantitative: *what fraction of our ΔV is the AGC
actually integrating?* Flight 1's telemetry has everything needed to
answer that offline — thrust, mass, tilt and the AGC's own displayed hdot,
100 samples per second. Integrating a two-body in-plane model driven by
`k · (T/m)` and fitting the single scalar `k` against the AGC's displayed
rate over the whole 198 s burn:

```
k = 1.000  (AGC sees all of it)     rms = 92.93 m/s
k = 0.250                            rms = 10.24 m/s
k = 0.171  ( = 0.01 / 0.0585)        rms =  1.44 m/s
k = 0.159  (best fit)                rms =  0.46 m/s
```

A one-parameter model reproducing a 200-second divergence to 0.46 m/s rms
is not a coincidence, and the fitted value is the ratio of two candidate
PIPA quanta.

### Root cause: `PIPA_INCR`

`eagle_dynamics::constants::PIPA_INCR` was `0.0585` m/s per pulse, cited
from `vendor/virtualagc/Contributed/LM_Simulator/lm_simulator.tcl:145`
(and it *is* metres there — `modules/AGC_IMU.tcl:293-297` displays the
integrated velocity raw and again × `MeterToFeet`). But LM_Simulator only
drives a DSKY; it never closes a navigation loop, so nothing there ever
tested the number against the rope.

The rope decodes its own counters like this:

- `vendor/virtualagc/Luminary099/SERVICER.agc:570-580` — PIPASR's
  REPIP1/REPIP3 read PIPAX/PIPAY/PIPAZ and store each raw count into the
  **high** word of `DELVX/DELVY/DELVZ`, so `DELV` as a DP fraction is
  `count · 2⁻¹⁴`. `IMU_COMPENSATION_PACKAGE.agc:58,65` says the same in
  words: "(PP) X 2(+14)", "FRACTIONAL PIPA PULSES SCALED 2(+14)".
- `vendor/virtualagc/Luminary099/CONTROLLED_CONSTANTS.agc:178-180` —
  `KPIP = .0512` ("SCALES DELV TO UNITS OF 2(5) M/CS"),
  `KPIP1 = .0128` (2(7) M/CS), `KPIP2 = .0064` (2(8) M/CS).

All three constants reduce to the same physical value:
`count · 2⁻¹⁴ · 0.0128 · 2⁷ = count · 1.0e-4 m/cs` = **1 cm/s per pulse**.
0.01 / 0.0585 = 0.171, i.e. the fitted `k`.

**Fix attempt 1:** `PIPA_INCR = 0.01`, provenance rewritten to the rope's
own constants with the LM_Simulator disagreement recorded rather than
deleted. `cargo test --workspace` green (32+21+90+1+4+10).

## Flight 2 — the nav loop closes, and a second blocker appears

With `PIPA_INCR = 0.01` the AGC and the truth flew the same vehicle. For
the whole braking phase the AGC's own displayed altitude rate stayed
within **0.6 m/s** of truth and its displayed altitude within ~100 m of
15 km — a nav loop that is genuinely closed, against 193 m/s of divergence
on the same trajectory one flight earlier:

| TIG+ | truth alt | truth vz | `nav_err_alt_m` | `nav_err_hdot_ms` |
|---|---|---|---|---|
| 60 s | 14997.4 m | −16.96 m/s | — | +1.14 |
| 120 s | 13314.4 m | −35.68 m/s | +107 m (at 123 s) | +0.26 |
| 180 s | 11041.7 m | −37.92 m/s | — | −0.21 |
| 240 s | 8940.4 m | −31.23 m/s | — | −0.43 |
| 300 s | 7330.4 m | −22.95 m/s | — | −0.46 |
| 340 s | 6458.1 m | −21.71 m/s | +13 m (at 334 s) | −0.17 |

And the AGC flew the real thing: **MM `00` → `63` → `64` → `65`**, the
full automatic braking → approach → terminal-descent sequence, which no
run in this project had ever reached. The P64 flashing V06N64 answered the
open question from the brief: it does **not** block. `P64DISPS` puts it up
through `REFLASHR` and then `TCF ENDOFJOB`
(`vendor/virtualagc/Luminary099/LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:866-880`),
so the display job ends and guidance keeps running from the Servicer with
nobody answering. 113 N64 frames were painted and `agc_hdot_ms` stayed
live through all of them.

**But the vehicle could not make the gate.** The pad-loaded braking target
is RBRFG = (2923.6 m up, −10084 m downrange) with VBRFG = (−48.4 m/s,
+171.8 m/s) — `scenarios/p66-padload.toml`, from
`LUM69R2/PADLOADS.agc:395-407`. Measured at the P63→P64 switch:

| | target (RBRFG/VBRFG) | measured at MM64 |
|---|---|---|
| altitude | 2923.6 m | **4052.5 m** |
| horizontal speed | 171.8 m/s | **435.4 m/s** |
| vertical speed | −48.4 m/s | **−74.4 m/s** |
| time from TIG | ~506 s (historical) | **408.6 s** |

Throttle was pinned at the model's ceiling (`throttle_cmd_pulses = 4096`,
i.e. the AGC asking for maximum) from FLATOUT to contact. So this is not a
guidance failure — the guidance flew its cubic correctly into an engine
that could not deliver the profile, arriving low AND fast, which is the
signature of too little thrust (less vertical support per unit of braking).
P64 then dove from 4052 m to 876 m in 34 s, P65 took over at TIG+442.5 s,
and the vehicle hit at 123.0 m/s vertical / 411.6 m/s horizontal.

A **PROG alarm lamp lit at t = 786.33 s = TIG+442.7 s** — the same second
as the MM64→MM65 switch — together with the ALT and VEL lamps (relay row
12 word `0o60424`). Its code is **unknown**: no responder runs after
ENGINE ON in PDI mode, so FAILREG was never read, and no V05N09 was ever
painted (the DSKY showed only V06N63 → V06N64 → V06N60 after ignition).
Recorded as an unidentified episode, in a state so far off nominal that it
is more likely a symptom than a cause. Closing that hole is a real gap —
see "Open".

### Root cause 2: DPS thrust

`DPS_FTP_N` was 42 500 N with provenance "assumed", under a `DPS_MAX_N` of
45 040 N from LM_Simulator. The rope's own pad-load states the number, and
twice:

- `vendor/virtualagc/LUM69R2/PADLOADS.agc:501-505` — `LOWCRIT 1OCT 04251`
  (= 2217 bits), *"(2.7 LBS/BIT) (57% NOMINAL MAX THRUST)"*
  → 2217 × 2.7 / 0.57 = **10 502 lbf**
- `vendor/virtualagc/LUM69R2/PADLOADS.agc:507-511` — `HIGHCRIT 1OCT 04622`
  (= 2450 bits), *"63% NOMINAL MAX THRUST"*
  → 2450 × 2.7 / 0.63 = **10 500 lbf**

Two independent words agreeing to 0.02 % on 10 500 lbf = **46 706 N**, and
both are already loaded into the AGC we fly (`scenarios/p66-padload.toml`).
The same annotation pins the throttle-counter scale — "2.7 LBS/BIT" =
12.010 N/bit — which upgrades `THRUST_N_PER_PULSE = 12.0` from "assumed"
to cited (0.08 % low; left alone, since every live spike was calibrated
against it). And because the criteria describe the throttle being *"SET TO
EITHER MAXIMUM OR TRUE VALUE"* outside the 57-63 % band, the AGC's
"maximum" is nominal max thrust — so FTP is not a lower fixed point.

**Fix attempt 2:** `DPS_MAX_N = 46706`, `DPS_FTP_N = DPS_MAX_N` (+9.9 % on
the saturated thrust). Arithmetic check against flight 2's own numbers:
over the measured 408 s of burn the old model delivered
`3050 · ln(15209 / (15209 − 5471)) = 1359 m/s` of ΔV (5471 kg burned,
measured); at 46 706 N the same 408 s burns 6246 kg for
`3050 · ln(15209 / 8963) = 1612 m/s` — **+253 m/s against a measured
shortfall of 263 m/s** at the gate. `cargo test --workspace` green.

## Flight 3 — P63 and P64 fly the real profile; P65 is where it dies

With the engine at 46 706 N the braking phase landed on the pad-loaded
gate almost exactly, and the approach phase that follows is textbook:

| | pad-load target | flight 2 (42 500 N) | flight 3 (46 706 N) |
|---|---|---|---|
| MM64 at | ~506 s (historical) | TIG+408.6 s | **TIG+480.6 s** |
| altitude | 2923.6 m | 4052.5 m | **3832.1 m** |
| horizontal | 171.8 m/s | 435.4 m/s | **217.6 m/s** |
| vertical | −48.4 m/s | −74.4 m/s | **−42.3 m/s** |
| `nav_err_alt_m` | — | +123 m | **+5.6 m** |

P64 then flew the approach the way the real one looks — throttle
modulating (2485 → 1177 counter bits, 43.8 → 14.1 kN), attitude coming
upright (64.9° → 12.4° from local vertical), and the vehicle arriving at
**248.9 m with vz = −1.66 m/s and v_horiz = 5.73 m/s**. That is a flown
lunar approach, from a real PDI state, on the real rope.

**It dies at the P64 → P65 switch.** At t = 996.11 s (TIG+652.5) MM65
appears; at t = 996.46 s — 0.35 s later — the PROG alarm lamp lights,
together with ALT and VEL (relay row 12 = `0o60424`), exactly as in flight
2. From that instant:

- the throttle counter **freezes at 1106 bits** (13 272 N) and never moves
  again for the remaining 240 s;
- HDOTDISP **freezes at +0.9754 m/s** (R2 `+00032`) while the truth rate
  runs from −0.4 m/s to +23.7 m/s;
- 13 272 N against a 12 640 N weight is a net +0.07 m/s², so the vehicle
  **climbs away**: 233.7 m → 2155 m over 180 s, burning the last 735 kg of
  DPS propellant, and then free-falls 2155 m onto the surface at 84 m/s.

MM66 *did* appear (t = 1240.2, the handover firing on the way down through
150 m), which is the first MM66 in this project that was not painted after
ground contact — but the engine had been dead for 56 s by then.

Two things are wrong here and only one is ours:

1. **The AGC's altitude runs out early.** By the end of P64 its own HCALC
   read 56 m against a truth of 249 m (`nav_err_alt_m` = −193 m), having
   been +5.6 m at the start of the phase. The rate error over that window
   is only ~1.1 m/s, which is what integrates to it. A plausible mechanism
   is geometric rather than a bias: HDOTDISP is `UNIT(R)·V`
   (`LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1027-1032`), so a downrange
   position difference θ between the AGC's R and the truth's turns
   horizontal speed into apparent vertical rate at v_h·θ — and this run's
   `miss_m` was 11.2 km, i.e. θ ≈ 6.4e-3 rad, which against the 170 m/s of
   the early approach is ≈1.1 m/s. **Not confirmed** — measuring it needs
   the AGC's downrange position, which no display gives us.
2. **P65's PROG alarm.** Code unknown for the same reason as flight 2: no
   responder runs after ENGINE ON in PDI mode, so FAILREG was never read
   and no V05N09 was painted. Whatever it is, it stops the guidance from
   modulating the throttle, and it is reproducible — same transition,
   both flights.

The consequence for M1 is a design one, and it points the same way the
plan already did: **do not go through P65.** P64 flies the approach; the
handover must fire inside P64.

## Flight 4 — tuning from flight 3's measurements

Fuel at the end of P64 in flight 3 was 824 kg, so the terminal phase has
~190 s of hover-equivalent propellant. Scenario tuned from that run:

- `[handover] alt_m = 150.0 → 250.0`. At 250 m truth altitude flight 3 was
  at TIG+639.5 s, still in MM64, vz −1.7 m/s, v_horiz 5.8 m/s, tilt
  12.5°. That is ~11 s before its P64→P65 switch (truth 236 m) and still
  above its lowest truth altitude (233.7 m), so the gate is crossed even
  if P65 starts first.
- `[rod] steps = [[245.0, -5.3], [50.0, -0.3], [12.0, 0.7]]`. **The values
  are VDGVERT deltas from the P66-entry rate, not absolute sink rates** —
  `SimCore::phase8_rod` starts its bookkeeping at 0 while `STARTP66` seeds
  VDGVERT from the current HDOTDISP (`LUNAR_LANDING_GUIDANCE_EQUATIONS
  .agc:155-157`), and the handover's own selection click adds a further
  −0.30 m/s. Against the measured −1.7 m/s entry that commands ≈ −7.3 /
  −2.3 / −1.3 m/s.

The reason for the aggressive first step is not fuel, it is the horizontal
axis: **P66 holds attitude and nothing nulls horizontal velocity without a
crew.** At the ~12° tilt P64 leaves behind, a hovering thrust puts
≈0.35 m/s² sideways into the vehicle for as long as P66 lasts, so every
extra second in P66 is horizontal velocity at touchdown. A crewless P66 is
structurally unable to be soft in both axes from 250 m; the schedule
trades vertical margin for a short P66.

### What flight 4 actually proved

**The M1 mode sequence flies.** `MM ["00", "63", "64", "66"]` — PDI →
braking → approach → crew-takeover rate-of-descent, radar bypassed in
rope, P65 never entered:

| event | measured (run 4) |
|---|---|
| ENGINE ON | t = 343.61 s |
| MM64 | TIG+480.6 s, alt 3820.1 m, vz −42.2 m/s, v_h 218.2 m/s, `nav_err_hdot` +0.43 m/s |
| handover fired | TIG+637.7 s, alt 249.9 m, vz −1.82 m/s, v_h 6.07 m/s, tilt 12.2°, DPS 824 kg, `nav_err_hdot` −0.89 m/s |
| MM66 | TIG+640.5 s, alt 245.4 m, **P66-entry sink rate −1.40 m/s** (AGC's own: −2.41 m/s) |
| alarms | **0 episodes, 0 PROG-lamp frames after ignition** |
| AGC clock | 0.944× real time; sim pacing lost 0 ms; downlink 47.3 wps |

Zero PROG-lamp frames, against 794 in flight 3, is itself the cleanest
evidence that the alarm belongs to P65 and not to the descent: same rope,
same trajectory to 245 m, the only difference being that P65 was never
entered.

### Blocker 3 (open): P66's rate loop goes bang-bang

The handover worked and P66 took the throttle — and then oscillated
violently instead of holding the commanded rate. Measured, run 4 (values
every 5 s from `build/traces/telem-m1-run4.jsonl`):

| TIG+ | alt | truth vz | AGC hdot | thrust |
|---|---|---|---|---|
| 645 s | 235.9 m | −3.89 m/s | −3.17 m/s | 4 576 N (idle) |
| 650 s | 203.3 m | −9.07 m/s | −9.17 m/s | 6 940 N |
| 655 s | 159.0 m | −6.59 m/s | −8.11 m/s | 26 833 N |
| 660 s | 161.8 m | **+5.25 m/s** | +3.90 m/s | 25 369 N |
| 665 s | 198.4 m | +7.38 m/s | +7.44 m/s | 6 594 N |
| 670 s | 222.9 m | +2.28 m/s | +2.29 m/s | 4 560 N (idle) |

Note what is **not** wrong: the AGC's own rate reading tracks the truth to
well under 1 m/s all through P66 (−9.07/−9.17, +5.25/+3.90, +2.28/+2.29).
The navigation is fine. It is the *control* that is unstable — the
throttle slams between the idle stop and full thrust with the sink rate
swinging −9.5 to +7.4 m/s about a −7.3 m/s command, and the vehicle
porpoises 245 → 7 → 580 m until the tank runs dry at TIG+840.

That 5 s sample under-reports the swing. Over the whole P66 segment run 4's
thrust ranges **0 N to 46 706 N** — the full stop-to-stop stroke — with the
sink rate spanning −47.3 to +26.0 m/s; run 5's, on the gentler schedule,
ranges 0 to 46 448 N and −16.8 to +10.2 m/s.

Not the actuator: between TIG+650 and +655 the throttle counter moved
678 → 2331 bits, i.e. 331 bits/s, comfortably under the 800 bits/s that
`DINC_MAX_PER_TICK = 8` allows. Nothing was rate-limited.

Prime suspect is the P66 force law's own scaling. `VERTGUID` computes
`(VDGVERT − HDOTDISP)/TAUROD`, adds gravity, multiplies by MASS and clamps
to [MINFORCE, MAXFORCE]
(`vendor/virtualagc/Luminary099/LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1042-1090`),
and **TAUROD, LAG/TAU, MINFORCE and MAXFORCE are the four pad words this
repo still carries as `BScaleStatus::Unverified`**
(`padload::P66_BSCALE_TABLE`) — every other word in the loop is verified.
Working the observed saturation backwards: idle at a −2 m/s error and full
thrust at a +2 m/s error implies an effective TAUROD of roughly 0.5-2 s
against a plant with a 0.3 s actuator lag, which is exactly the regime
where a rate loop rings. **This is a hypothesis, not a measurement** — the
scale is not pinned here and must not be guessed; pinning it is the next
task's job.

## Instrumentation added along the way

- **`agc_alt_m` is live.** R3 of V06N60/N63/N64 is HCALC/HCALC1 under the
  `COMP ALT` scale-factor code, and the rope's own scale-factor legend
  spells the units out: `PINBALL_NOUN_TABLES.agc:118`,
  `# 11000  COMPUTED ALTITUDE (XXXXX. FEET)`. So R3 is **whole feet**, and
  `agc_alt_m = R3 · 0.3048`. The three 5-bit fields of a `3COMP` format
  word are R3|R2|R1 from the top — provable from the pair `OCT 60512`
  (N60/N63) vs `OCT 60500` (N64) at `:473`/`:479`/`:481`, which differ
  only in the LOW field and only in R1. Same legend pins R2:
  `01010  VELOCITY3 (XXXX.X FT/SEC)` at `:95`, i.e. tenths of a foot per
  second — the scale Spike B had confirmed live but never cited.
  Arithmetic cross-check of the legend (`SFOUTAB`'s COMPUTED ALTITUDE DP
  constant `OCT 01046`/`OCT 15700` at `:650-651`, `DP1OUTSF`'s ×2¹⁴ at
  `PINBALL_GAME__BUTTONS_AND_LIGHTS.agc:1488-1492`, 5-digit display = ×10⁵,
  HCALC at 2²⁴ m per `SERVICER.agc:822-827`) gives
  `alt_m × 3.280839` — feet to seven figures; the same arithmetic on
  `WEIGHT2` returns kg × 2.2046, which is why the convention is trusted.
  `nav_err_alt_m` is like-for-like: HCALC is `ABVAL(R) − /LAND/`, the same
  datum as `SimCore::alt_agl()`.
- **`scenario_mode` now prints the acceptance diagnostics block** (class /
  v_vert / v_horiz / tilt / miss, alarm episodes, PROG lamp frames, AGC
  clock rate, sim pacing lost, downlink wps) so an interactive
  `make descent-full` records a run without re-deriving numbers from the
  telemetry dump afterwards — the exact gap the Wave 1 re-flight hit.
- **`make descent-full`** added.

## Flight 5 — the limit cycle is not a step-size artefact

Same build, only the ROD schedule changed: three ≤6-click steps
(`[[240,-1.5],[40,0.2],[10,0.8]]`, i.e. ~−3.5 / −1.8 / −1.2 m/s commanded)
instead of run 4's single −8-click jump to −7.3 m/s.

| | run 4 | run 5 |
|---|---|---|
| MM sequence | `00`,`63`,`64`,`66` | `00`,`63`,`64`,`66` |
| MM64 | TIG+480.6 s, 3820.1 m, 218.2 m/s | TIG+480.6 s, 3817.2 m, 218.2 m/s |
| handover | TIG+637.7 s, 249.9 m, v_h 6.07 m/s, tilt 12.2° | TIG+636.0 s, 249.9 m, v_h 6.68 m/s, tilt 14.4° |
| MM66 / P66-entry rate | TIG+640.5 s, −1.40 m/s | TIG+638.6 s, −1.67 m/s |
| touchdown v_vert | 44.09 m/s | **13.58 m/s** |
| touchdown v_horiz | 59.81 m/s | **66.91 m/s** |
| PROG-lamp frames | 0 | 21 |
| DPS at handover | 824 kg | 836 kg |

The braking and approach phases repeat to within a few metres across runs
3, 4 and 5 — this profile is reproducible. Smaller steps did halve the
vertical impact, but the loop still limit-cycles with a ~10 s period
(sink rate −5.6 to +9.2 m/s about a −3.5 m/s command, throttle
4.6 ↔ 26.7 kN), so **the oscillation is a property of the loop, not of the
step size**, and no ROD schedule fixes it. Horizontal velocity got worse
precisely because the gentler profile keeps the vehicle in P66 longer, at
the ~12° tilt nothing is flying.

That is where the flight budget stopped. The next change needed is a
number — TAUROD's scale — and this task's rule is that numbers are
measured or cited, never guessed.

## Fix round 1 (review) — three more constants the rope publishes itself

Review found that the DPS side had the *same* class of error as
`PIPA_INCR`, and in the same place: **`vendor/virtualagc/Luminary099/
CONTROLLED_CONSTANTS.agc:132-135` publishes the flown rope's own force
constants, in SI, on four consecutive lines**, and this task had gone to
LUM69R2's pad-load annotation instead.

```
FMAXODD   DEC  +3841                   # FSAT     +4.81454413 E+4
FMAXPOS   DEC  +3467                   # FMAX     +4.34546769 E+4
THROTLAG  DEC  +20                     # TAU (TH) +1.99999999 E-1
SCALEFAC  2DEC* +7.97959872 E+2 B-16*  # BITPERF  +7.97959872 E-2
```

Also, review strengthened the PIPA finding rather than weakening it:
`vendor/virtualagc/Comanche055/SERVICER207.agc:790` reads
`KPIP1 2DEC 0.074880  # 207 DELV SCALING.  1 PULSE = 5.85 CM/SEC.` —
5.85 cm/s is the **command module** quantum, and running the same
derivation on the CM constant reproduces the CM rope's own words exactly
(`0.074880 · 2⁷ / 2¹⁴ = 5.85e-4 m/cs`). LM_Simulator transcribed a CM
value into an LM simulator. The method is validated on two ropes.

Corrections applied:

| constant | was | now | source |
|---|---|---|---|
| `THRUST_N_PER_PULSE` | 12.0 (4.25 % low) | **12.531966 N/bit** | `SCALEFAC`/BITPERF, `:135`; = 1/0.0797959872 |
| `DPS_MAX_N` / `DPS_FTP_N` | 46 706 N | **48 145.4413 N** | `FMAXODD`/FSAT, `:132` |
| `DPS_TAU` | 0.3 s (assumed) | **0.2 s** | `THROTLAG`, `:134` |

The bit scale cross-checks four ways to within 0.03 %: BITPERF 12.5320,
FEXTRA 51 330.9/4096 = 12.5320
(`THROTTLE_CONTROL_ROUTINES.agc:226`), FSAT 48 145.4/3841 = 12.5346, FMAX
43 454.7/3467 = 12.5338. It matters in both directions because the AGC
converts desired thrust to bits through `SCALEFAC` (`MASSMULT`,
`THROTTLE_CONTROL_ROUTINES.agc:206-214`) and P66's force law divides by it
again (`LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1074-1076`) — at 12.0 the AGC
asked for N and got 0.9575·N across the whole modulated band.

Why the earlier 46 706 N was wrong even though its arithmetic was right:
LUM69R2's "(2.7 LBS/BIT)" is *that* rope's SCALEFAC (12.0325 N/bit), and
the two ropes differ by 4.16 %. Mixing LUM69R2's bit scale with
Luminary099's LOWCRIT/HIGHCRIT criteria mis-scaled the answer. Against
FSAT those same criteria land where they should: LOWCRIT 2217 bits =
57.7 % of 3841, HIGHCRIT 2450 = 63.8 %, matching the annotation's
"57 %/63 % NOMINAL MAX THRUST".

`FMAX` (43 454.7 N) is deliberately **not** the delivered thrust: it is
what the AGC writes into FCODD as its own estimate after a throttle-up
(`THROTTLE_CONTROL_ROUTINES.agc:105-106`), 90.3 % of FSAT. NOTE 2 at
`:114-118` names FMAXODD as *"the NUMBER OF BITS CORRESPONDING TO FULL
THROTTLE"*, so FSAT is the stop and FEXTRA's 4096 bits (51 330.9 N) is
drive-past, exactly like the zero-stop idiom at the other end.

### Flight 6 — the constants are right, and the limit cycle survives

| | run 3 (46 706 N, 12.0 N/bit, τ 0.3) | run 6 (48 145 N, 12.532 N/bit, τ 0.2) |
|---|---|---|
| time at full throttle | 333 s | **287 s** |
| MM64 | TIG+480.6 s | TIG+488.6 s |
| altitude at gate | 3832.1 m | 3835.0 m (target 2923.6) |
| horizontal at gate | 217.6 m/s | 219.3 m/s (target 171.8) |
| DPS at gate | 1861 kg | 1843 kg |
| handover | — | TIG+647.1 s, 249.9 m, v_h 5.66 m/s, tilt 11.7°, DPS 809 kg |
| MM66 / P66-entry rate | — | TIG+648.8 s, 247.3 m, **−1.42 m/s** |
| P66 duration / thrust span | (2 s, engine dead) | 218 s, **0 → 48 132 N** |
| P66 sink-rate span | — | −34.1 to +16.2 m/s |
| alarms | 794 lamp frames (P65) | **0 episodes, 0 lamp frames** |
| touchdown | 83.99 / 38.77 m/s | 30.86 / 60.04 m/s, tilt 12.8° |

Two things this settles.

**1. The braking-gate residual is NOT a thrust deficit.** The prediction
going in was that +3 % would close the remaining 900 m / 47 m/s. It did
not move it at all — the gate is within 3 m and 1.7 m/s of run 3's. What
did change is that the engine stopped being the constraint: 46 s less time
at full throttle, and the AGC now modulates in the throttleable band
(26-27 kN) through the second half of P63 instead of sitting on the stop.
At 42 500 N the engine was saturated and the gate was missed by 1128 m /
264 m/s; at 48 145 N there is margin and the gate is still missed by
911 m / 47 m/s. So whatever sets the residual is in the guidance's own
targeting or in the state it is targeting from — the same place the
−190 m altitude drift lives — not in the engine.

**2. The P66 limit cycle is not caused by any of the three constants.**
The corrected plant is 4.25 % stronger per bit, 3 % stronger at the stop,
and 50 % faster in response — every change in the direction that should
buy phase margin — and P66 still runs the throttle stop-to-stop
(0 → 48 132 N) with the sink rate spanning −34 to +16 m/s for 218 s. The
amplitude is smaller than run 4's (−47.3 to +26.0) and the vehicle
survived longer, but it is the same oscillation. `v_vert` at contact went
44.09 → 13.58 (run 5, gentler steps) → 30.86; `v_horiz` is 60 m/s and is
the un-flown attitude, not the loop.

The two candidate mechanisms both survive flight 6, and neither was
tested by it:

- **TAUROD's b-scale.** Still `Unverified`. Review points out it is
  statically derivable without flying: `STARTP66` DP-copies
  VDGVERT ← HDOTDISP (`LLGE:155-157`), fixing them to one scale, and
  `:1050`'s `DAD` forces `(VDGVERT − HDOTDISP)/TAUROD` to the same scale
  as `ABVAL(GDT/2)/GSCALE >> 2` with `GSCALE = 100 B-11` pinned at
  `LLGE:1477`. That is the next thing to do, and it costs no flights.
  (Circumstantial support that the current value is not the intended one:
  `scenarios/p66-padload.toml`'s `LAG/TAU` is derived as "lag 0.2 s /
  tau 1.5 s" — and 0.2 s is exactly THROTLAG, so whoever wrote it already
  had the right lag and a 1.5 s TAUROD in mind.)
- **`dps_envelope`'s discontinuity.** `forces.rs:180-188` jumps from
  0.6·MAX (28.9 kN) straight to full throttle with no hysteresis, so the
  plant has a ~19 kN step in the middle of the actuator's slew path. The
  rope's own throttle law never *rests* in the 57-63 % band
  (`THROTTLE_CONTROL_ROUTINES.agc:88-107`) but it does slew through it,
  and a real engine's thrust is continuous in actuator position. Changing
  the envelope shape needs a citation for what the engine actually does
  between 60 % and full; it was not attempted here because it is a plant
  change, not a constant, and there was one flight left.

## Open, in the order the next engineer should take them

1. **P66's rate loop (blocker 3).** Pin TAUROD / LAG/TAU / MINFORCE /
   MAXFORCE against the rope instead of the scale-chain hypotheses in
   `padload::P66_BSCALE_TABLE`, then re-fly. TAUROD is derivable
   statically — see the route in "Fix round 1" — so this costs no flights
   to attempt. Everything else in the loop already checks out live, the
   three engine constants are now the rope's own, and the AGC's rate
   reading is good to under 1 m/s: this is a scaling question, not a
   navigation one. Second candidate, needing a citation before it is
   touched: `dps_envelope`'s 19 kN discontinuity at 0.6·MAX.
1a. **The braking-gate residual (new, flight 6).** The gate is 911 m high
   and 47 m/s fast against RBRFG/VBRFG, and flight 6 proved that is *not*
   thrust — the engine now has margin and the number did not move. Look at
   the targeting and at the state it targets from; it is probably the same
   root as item 3.
2. **The P65 PROG alarm.** Reproducible at the MM64→MM65 transition in
   both flights that reached it, with ALT and VEL lamps alongside, and it
   stops the guidance modulating the throttle. Its code is unknown because
   nothing reads FAILREG after ENGINE ON in PDI mode. A post-ignition
   alarm watcher that reads V05N09 on the lamp — carefully, since the
   flight display owns the DSKY — would name it in one flight. Until then
   the handover must fire inside P64, which is why `[handover] alt_m` is
   250 m and not the historical 150.
3. **The −190 m altitude nav drift through P64.** Recorded, not
   diagnosed; the `UNIT(R)·V` geometry argument in the flight-3 section is
   a hypothesis. It costs the AGC its altitude margin before the terminal
   phase and is the reason P65 believes it has landed while the vehicle is
   still 240 m up.
4. **Horizontal velocity in a crewless P66.** Structural, not a bug: P66
   holds attitude and there is no crew on the RHC, so the ~12° tilt P64
   leaves behind pushes ≈0.35 m/s² sideways for the whole descent. Any
   acceptance that gates `v_horiz` has to say what flies the attitude.

## Artefacts

Under `build/traces/` (git-ignored; regenerate by re-running):

- `telem-m1-runN.jsonl` — per-frame telemetry
- `att-m1-runN.log` — attitude sign-chain trace
- `m1-runN.out` — stdout/stderr
- `pkt-m1-runN.jsonl` — full packet trace (flight 2 on)
