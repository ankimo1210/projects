# eagle — Apollo 11 lunar descent simulator

> **Status lives in `README.md`, not here.** The dated blocks below are kept
> as the reasoning record for each milestone; they are not a current report.
> As of 2026-08-03 the P65 altitude divergence is root-caused: **no LR
> measurement was ever incorporated — V57 was never keyed** (LRINH clear
> in every flight; SERVICER discarded every DELTAH at the NOREASON/VUPDAT
> gates). V57 must be keyed INSIDE P63 — R00 wipes FLGWRD11 on every V37
> (Run 32 measured a P00-keyed V57 doing nothing). Navigation is now fixed:
> DELTAH inside ±50 m, HCALC within ~25 m of truth at 600 m. **Run 34
> landed Nominal (1.14/0.50 m/s) and Run 35, identical, crashed at
> 137.76/105.47 m/s — bimodal, so this is NOT a landing capability.**
> Measured cause: a marginal P64 attitude wobble plus an unphysical radar —
> past ~60° tilt the H beam grazes and returns 10-18 km of slant range that
> the responder still calls DATA GOOD, and the rope incorporates it raw
> (no reasonableness test before HIGATE). The beam-pointing envelope needs
> a SOURCED limit; do not invent one. Also fixed: ch33 bit-9 polarity
> (SCALADJ: set = high), the V01N01 read-back killing the burn monitor
> (V16N63E restored), and the read path now applies the same 40,000 ft
> ceiling as the DATA GOOD discrete. Instruments: `EAGLE_CORE_SAMPLE`
> (core-dump time series, the instrument of first resort — the downlink
> cannot reach DELTAH/RGU) and `EAGLE_LR_DEBUG` ALT rows. Evidence:
> `docs/superpowers/notes/2026-08-03-v57-lr-incorporation.md` §9-12.
> The frozen M1 acceptance bypasses the radar and is still RED. Read
> `README.md` before quoting any number from this file.

Original Luminary099 running in vendored yaAGC, bridged to a web DSKY, and —
as of Phase 2 Wave 1 — flying a closed loop against our own 6-DoF physics
(crates `eagle-dynamics`, `eagle-sensors`; sim thread in
`eagle-runtime::sim`): boot → pad load → P63 → ENGINE ON → ATT HOLD →
ground contact.

**Wave 1 acceptance is RED.** The landing is not soft and **P66 never
flew**: MM66 does light — the MM assert passes on the measured sequence
`["00","63","66"]` — but only 0.6-1.8 s AFTER ground contact, so it
controlled nothing. The last measured run (2026-07-25) crashes at 41.5 m/s
vertical / 10.7 m/s horizontal after 26.0 s, with MM66 first appearing at
TIG+26.6 s:
P63's `AVEGEXIT` points at `SERVEXIT` until `P63ZOOM` swaps it to
`LUNLAND` at the end of the 26 s ZOOMTIME, and GUILDENSTERN (R13, the only
path to P66) sits behind that swap. The attitude loop is fine. Two
blockers: (1) the 500 m gate is too low to survive the burn-in at the DPS
idle stop — a scenario fix, `live_spike_p66.rs` already starts at 3000 m
for exactly this reason; (2) the pad-loaded AGC state vector is the
historical 15 km / 1700 m/s PDI point, not the sim's hover gate, so the
vehicle would enter P66 holding the braking attitude IGNALG computed for a
1700 m/s burn (measured 107-108° tilt) — and P66 holds attitude, it does
not re-orient. Do not restate "soft touchdown" anywhere until it is
measured. Evidence, numbers and next steps:
`docs/superpowers/notes/2026-07-25-wave1-reflight.md` — **whose
measurements predate the 2026-07-26 vehicle-constant corrections
(`PIPA_INCR`, `THRUST_N_PER_PULSE`, DPS full throttle, `DPS_TAU`) and will
not reproduce**; the conclusions stand, the numbers do not.

**Wave 2 M1 (`scenarios/pdi-descent.toml`, `make descent-full`) flies the
real profile and does not land yet.** Six instrumented flights on
2026-07-26; **the last three** fly PDI → P63 → P64 → P66 with the radar
bypassed in-rope (runs 1-3 did not reach that sequence), AGC-vs-truth
altitude-rate error a median 0.4 m/s through the braking phase (p90
1.1 m/s — not "under 1 m/s"), MM64 at TIG+488.6 s and the sim-driven
handover at 250 m. **That closes cause C**, the Wave 1 blocker: the
pad-loaded AGC state vector and the sim truth described different
vehicles. M1 starts truth at the pad's own TIG state, so navigation and
truth agree by construction — the thing Wave 2 existed to decide.

`alarm episodes []` on all six runs carries almost no information:
`HeadlessResult.alarms` only ever receives `enter_p63_with_alarms`'s
return value, and in PDI mode `run_scenario` returns right after
`wait_engine_on` (`runner.rs:1113-1115`), so nothing can add to it after
ignition — run 3 counted 794 PROG-lamp frames and still reported zero
episodes. Quote the metric only with its window: **no alarm episodes in
the pre-ignition P63 dialog**. The post-ignition signal is
`prog_lamp_frames`: 0 on runs 4 and 6, 21 on run 5 — all after ground
contact, unexplained, ledger "Open" 2a.

Touchdown is still a crash: P66's rate loop limit-cycles (throttle
slamming idle ↔ full) and nothing flies the attitude, so v_horiz runs
away. **The throttle-command and accelerometer chain is now the flown
rope's own numbers**, four constants corrected by flying: `PIPA_INCR`
0.0585 → **0.01** m/s/pulse (Luminary's KPIP — 0.0585 is the *command
module* quantum, `vendor/virtualagc/Comanche055/SERVICER207.agc:790`),
`THRUST_N_PER_PULSE` 12.0 → **12.5319585** N/bit, DPS full throttle
42 500 → **48 145.4** N, `DPS_TAU` 0.3 → **0.2** s — the last three from
`vendor/virtualagc/Luminary099/CONTROLLED_CONSTANTS.agc:132-135`.
**The DPS/RCS force magnitudes are NOT.** `DPS_MIN_N` 4560.0, `DPS_VE`
3050.0, `RCS_THRUST_N` 445.0 and `RCS_VE` 2840.0 are still
`lm_simulator.tcl` numbers (`constants.rs:104,112,125,127`) — the same
file that carried a Command Module PIPA quantum into an LM simulator.
`DPS_MIN_N` is load-bearing: it is the lower stop of the very limit
cycle ledger "Open" 1 is chasing, and the low end of `dps_envelope`'s
19.26 kN discontinuity. Do not strike it off the suspect list. Flight 6
proved the remaining braking-gate error (911 m / 47 m/s) is *not*
thrust. Numbers, citations and the open blockers:
`docs/superpowers/notes/2026-07-26-m1-pdi-flight.md`.

**The M1 acceptance (`tests/live_pdi_descent.rs`) is frozen.** It was written
after the 6-flight budget was spent, so at the time of this block it was a
target, not a result: on the last three flights its mode, alarm-episode and
AGC-clock blocks would pass, its touchdown block would fail, and its
`prog_lamp_frames == 0` gate would fail on run 5. Do not relax its
thresholds (they are the scenario's design limits) and do not describe M1
as landing anything until that test is the thing that measured it.
**It has since been executed unchanged (2026-08-02) and is RED**: the
forced-P66 path crashed at 20.70 m/s vertical / 62.40 m/s horizontal and hit
the 800 s limit at 856.5 s before the touchdown assertions. See `README.md`.

## 2026-07-31 — M1b: the TAUROD scale, and two more flights

Flights 7 and 8 (`build/traces/telem-m1-run{7,8}.jsonl`). **Both still
crash** — 29.23/72.04 m/s and 36.81/64.18 m/s — because the loop's gain
was deliberately NOT changed. Full ledger:
`docs/superpowers/notes/2026-07-31-m1b-rod-loop.md`.

**The prime suspect for the limit cycle is now named: `TAUROD`'s
b-scale.** `scenarios/p66-padload.toml` derives it at b=14 from a premise
("velocities in this file are at 2^10 m/cs", `:252-259`) that the
spike-B live measurement fifteen lines below contradicts for the two
words the force law actually divides — `VDGVERT`/`HDOTDISP` are b=7
(`:265-274`, the one `Verified` entry in `P66_BSCALE_TABLE`). **Nobody
re-derived TAUROD after that measurement landed.** At b=11 the AGC reads
the committed 150 cs word as 0.1875 s, at b=12 as 0.375 s — a 4× or 8×
too-fast rate loop against the rope's own 0.2 s `THROTLAG`. **The
direction is certain; the factor is NOT.** Two unpinned one-power-of-two
shifts sit in the chain (the `BDDV` by the `DOT`-built cosine at
`:1051-1058`, the `SR2` at `:1047`). **Do not change the pad load until
one of them is measured.**

**τ cannot be measured from a descent, and this is structural.** Three
estimators on flight 8's good data give r² = 0.088 / 0.042 / 0.63. The
last is a trap: sweeping the assumed command lag makes r² a *periodic*
function of lag, peaking at 5.0 s against a measured limit-cycle period
of 19.4 s (quarter period 4.9 s). It aligns phase, it does not measure
gain. A saturated relay limit cycle carries almost no information about
the linear gain inside it. The experiment that will work is an open-loop
step test off `live_spike_p66` — see the ledger's §7.

**A refused ROD load used to be silent, and blinded the run.** An entry
typed into P66's VERTDISP repaint stream is rejected with OPR ERR / KEY
REL, leaving RODCOUNT unwritten; nothing checked, and nothing handed the
display back. Flight 7 painted **6** distinct `HDOTDISP` values in 222 s
of P66 (against 206/230 on runs 5/6) and counted 41 PROG lamp frames.
Fixed (`a984c46a`): `rod_load` samples the lamps and returns an
`EntryStatus`, then always releases the display; `headless` retries once
and reports; **`rod_clicks_cum` counts only clicks the AGC confirmed**,
because a refused click never moved VDGVERT. Flight 8: 231 repaints
(1.07/s, best of any run), 0 rejections, 0 PROG frames. Never RSET in
these paths — it clears FAILREG, and the P65 alarm's code is still
unknown.

`EAGLE_TELEM_OUT` / `EAGLE_ATT_DEBUG` need **absolute** paths: the
runtime's cwd is `runtime/`. They used to swallow a bad path silently and
cost a whole flight; they now panic. `make descent-full` always writes
`build/traces/pkt-descent-full.jsonl`.

One correction to the block above: `DPS_MIN_N` is the **plant's** lower
stop (`runner.rs` clamps delivered thrust), not a clamp on the AGC's
command — the commanded throttle roams smoothly down to ~178 bits with no
mode anywhere, so the command floor cannot be used to read `MINFORCE`'s
scale (ledger §3b). It stays on the suspect list.

- Specs: docs/superpowers/specs/2026-07-21-eagle-roadmap-design.md,
  docs/superpowers/specs/2026-07-22-eagle-phase2-closed-loop-design.md
- Channel semantics: docs/agc-channel-map.md (octal; update with citations)
- Build AGC artifacts once: `make agc` (fetches vendor, builds yaYUL/yaAGC,
  assembles Luminary099, verifies hashes)
- Fast tests: `make test` (no AGC needed) — Rust unit + client vitest
- Lint gate: `make lint` (clippy `-D warnings`, `cargo fmt --check`,
  client oxlint) — same set the CI fast lane runs
- Live AGC tests: `make test-integration` (serial, `--test-threads=1`).
  It runs every `#[ignore]`d test in the runtime, so since 2026-07-26 it
  includes the ~20 min M1 acceptance below and takes ~35 min end to end.
  It is RED on **both** acceptance tests — Wave 1's on the touchdown class,
  M1's on the touchdown block — so the useful command is usually a single
  binary: `cargo test -p eagle-runtime --test <name> -- --ignored
  --test-threads=1`.
- Phase 1 run (DSKY only): `make dev-runtime` + `make dev-client`,
  open http://localhost:5173
- Closed-loop descent: `make descent-p66` (real Luminary099 against our
  physics, to ground contact); `make descent-p66-fast` for debug iteration
  (same loop, TIG lead 30000 cs instead of 36000 — `p66-gate-fast.toml`,
  debug only, NOT the acceptance gate; 24000 was measured too tight and
  aborts with FAILREG 01703 "IGNITION TIME SLIPPED"). **30000 is untested
  live** — if 01703 reappears, fall back to 36000 (`make descent-p66`).
  Watch either live with
  `make dev-client` → ENGR tab (strip charts + ROD −/+ buttons)
- Wave 2 M1 descent: `make descent-full` (`scenarios/pdi-descent.toml` —
  PDI → P63 → P64 → P66, radar bypassed). ~20 min wall: boot ~5.7 min,
  ENGINE ON at t ≈ 344 s, MM64 at TIG+489 s, handover at TIG+647 s. Not in
  CI. It prints the same `[accept]` diagnostics block as the acceptance
  test, so an interactive flight records itself.
- Debug env vars for a live run: `EAGLE_ATT_DEBUG=<path>` (attitude
  sign-chain trace: t, jet bitmask, gimbals, omega, torque — one line per
  10 ticks post-freeze), `EAGLE_TELEM_OUT=<path>` (per-frame telemetry
  JSONL)
- Scenarios: `scenarios/pdi-descent.toml` (Wave 2 M1 acceptance),
  `p66-gate.toml` (Wave 1 acceptance), `p66-padload.toml`
  (spike-calibrated pad-load, shared by both), `p66-gate-imu-bias.toml`
  (error-model)
- Wave 1 acceptance test: `cargo test -p eagle-runtime --test
  live_p66_descent -- --ignored --test-threads=1` (~8-11 min: the TIG
  countdown is real-time; ENGINE ON is ~350 s after boot). The
  `EAGLE_SLOW=1`-gated error-model run in the same file is not part of
  default `make test-integration`.
- Wave 2 M1 acceptance test: `cargo test -p eagle-runtime --test
  live_pdi_descent -- --ignored --test-threads=1` (port 19905, ~20 min).
  Frozen 2026-07-26; first executed unchanged 2026-08-02 and **RED** (800 s
  limit hit at 856.5 s). See `README.md` for the current result.
- ROD without a vendor patch: stock yaAGC raises no interrupt for channel
  016, so in **scenario mode** a rate-of-descent click — from the client's
  ENGR buttons or the scenario's own schedule — is issued as a direct
  RODCOUNT erasable load (`runner::rod_load`), never the ch016 switch
  discrete. In **Phase-1 DSKY-only mode** (`make dev-runtime`) the button
  still emits the ch016 discrete, which yaAGC ignores: a no-op. vendor/
  stays READ-ONLY. See docs/agc-channel-map.md ("Rod Switch Click").
- Client DSKY keys are forwarded into the same pump the choreography uses,
  but are DROPPED while a `DskyScript` sequence is in flight (boot
  choreography or a `rod_load` erasable write), logging
  `headless: client key dropped (script busy)`. A stray keystroke inside a
  `V21N01E…E…E` load would corrupt the word being written.
- vendor/ is read-only and git-ignored; pins in vendor/manifest.json
- vendor pins: Apollo-11 transcription diverges from virtualagc's
  (proofreading drift, ~20 files); shipped binary is virtualagc's assembly;
  cross-check status recorded in build/agc/manifest.json
- prerequisite: jq (vendor pinning); gcc/make (vendor build); node 22+
  (client)
