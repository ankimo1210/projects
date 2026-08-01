# Wave 2 M1b — close the P66 rate loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pin `TAUROD`'s b-scale against the flown rope and the six existing
flight traces, correct it if the traces say it is wrong, and re-fly
`make descent-full` to measure what the corrected rate loop does.

**Architecture:** Three zero-flight stages before any flight is spent.
(1) *Measure* the effective ROD time constant the AGC actually used, from
telemetry already on disk — the throttle command and `HDOTDISP` are both in
`build/traces/telem-m1-run{4,5,6}.jsonl`, and differencing them across a
display repaint yields `-1/τ` without needing `VDGVERT`. (2) *Derive* the
b-scale from the rope's own published scales and reconcile it with the
measurement. (3) *Guard* the result with an offline closed-loop model of
the P66 force law so future changes to the loop can be evaluated in
milliseconds instead of a 20-minute flight. Only then (4) fly.

**Tech Stack:** Rust 2021 (workspace at `runtime/`), `serde_json` for
trace parsing, the vendored Luminary099 source as the citation authority,
`make test` / `make lint` as the gates.

## Global Constraints

- `vendor/` is **READ-ONLY** and git-ignored. Never edit it; cite it.
- Every scale, constant, or claim added to a doc or a comment carries a
  `path:line` citation into `vendor/virtualagc/Luminary099/` or a measured
  artefact under `build/traces/`.
- **Do not relax the acceptance thresholds** in
  `runtime/apps/eagle-runtime/tests/live_pdi_descent.rs`. Task 4 changes
  *which frames a gate counts*, and only because the current window is a
  documented false-negative; it does not move a threshold.
- Do not describe M1 as landing anything until `live_pdi_descent.rs` is the
  thing that measured it.
- `make test` (fast, no AGC) and `make lint` (clippy `-D warnings`, fmt)
  must both pass before every commit.
- Numbers that appear in more than one place (`0.1875 s`, `b=11`) must be
  written once as a constant or cited to one source, never retyped.

---

## Why this plan exists — the review finding

The M1 ledger's open item 1 says to "pin TAUROD / LAG/TAU / MINFORCE /
MAXFORCE against the rope instead of the scale-chain hypotheses in
`padload::P66_BSCALE_TABLE`" and notes TAUROD "is derivable statically".
Reviewing that from scratch turned up a **contradiction already sitting in
the repo**, between two comment blocks 15 lines apart in
`scenarios/p66-padload.toml`:

- Lines 252-259 derive the P66 cluster's scales from a *global* premise:
  "velocities in this file are at 2^10 m/cs (VIGN literal, DDUM denominator
  comment)", giving `TAUROD = vel/acc -> b=14, CENTISECONDS`.
- Lines 265-274 — added **later**, from the spike-B live measurement, and
  marked `Verified` in `P66_BSCALE_TABLE` — pin the two words that actually
  appear in TAUROD's divide: "**VDGVERT and HDOTDISP are DP b=7 in m/cs**",
  read back raw (`hi=0o36` = 491520 pulses; `491520 · 2^-21 m/cs` =
  23.4 m/s) against an N63 R2 display of 75.6 ft/s.

TAUROD was never re-derived after that measurement landed. The rope's own
force law divides *those two words*, not `VBRFG`/`VIGN`:

```
:1041  STODL  HCALC1
:1042           HDOTDISP        <- b=7 m/cs (live-verified)
:1042  BDSU   DDV
:1043           VDGVERT         <- b=7 m/cs (live-verified)
:1044           TAUROD
```
(`vendor/virtualagc/Luminary099/LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1041-1044`)

Interpretive `DDV` subtracts b-scales (`b_result = b_num - b_den`), and the
quotient is an acceleration. The rope states the acceleration scale itself,
in SI, in a comment:

```
# MASSMULT SCALES ACCELERATION, ARRIVING IN A AND L IN UNITS OF 2(-4) M/CS/CS, TO FORCE IN PULSE UNITS.
```
(`vendor/virtualagc/Luminary099/THROTTLE_CONTROL_ROUTINES.agc:206`)

and the flown pad load agrees — `ABRFG` is annotated `B+04`, i.e. b=-4
m/cs² (`scenarios/p66-padload.toml:59-63`, from
`LUM69R2/PADLOADS.agc:409-414`). So

$$b_{\mathrm{TAUROD}} = b_{\text{vel}} - b_{\text{acc}} = 7 - (-4) = \mathbf{11}$$

not 14. Corroboration from the rope, four lines below, in the *identical*
syntactic role — a DP time constant dividing a velocity to make the
acceleration that is `DAD`ed to TAUROD's own term at `:1050`:

```
:1046           GDT/2
:1047  DDV    SR2
:1048           GSCALE
```
with `GSCALE  2DEC  100 B-11`
(`vendor/virtualagc/Luminary099/LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1477`)
— 100 centiseconds at **b=11**.

**Consequence if b=11 is right.** `scenarios/p66-padload.toml:282-286`
ships `TAUROD = { value = 150.0, b = 14, dp = true }`, i.e. DP pulses
= 150·2^14 = 2 457 600, intending 150 cs = 1.5 s. An AGC decoding those
pulses at b=11 reads

$$\tau_{\mathrm{eff}} = 2457600 \cdot 2^{11-28}\ \mathrm{cs} = 18.75\ \mathrm{cs} = \mathbf{0.1875\ s}$$

An 8× too-fast rate loop against a **0.2 s** engine lag (`THROTLAG`,
`CONTROLLED_CONSTANTS.agc:134`) is a textbook bang-bang oscillator, and it
predicts the flown symptom exactly. It is also quantitatively consistent
with the ledger's own back-calculation: run 4 saturated to idle at roughly
a −2 m/s rate error and to full thrust at roughly +2 m/s, and full thrust
needs `a_cmd ≥ 6.9 m/s²` at ~7000 kg, so
`2/τ + 1.62 ≥ 6.9 → τ ≤ 0.38 s` — already below the ledger's loose
"0.5–2 s" bracket, and consistent with 0.1875 s.

The other three words are *not* implicated by the velocity scale:
`LAG/TAU` is dimensionless (b=0 regardless), and `MINFORCE`/`MAXFORCE` are
`b = b_MASS + b_acc` — `MASS` at b=16 kg per
`ERASABLE_ASSIGNMENTS.agc:1698` ("`# (1) MASS AFTER STAGING, SCALE AT B16
KG`").

> ### REVISED 2026-07-31, after executing Tasks 1 and 3
>
> **`b=11` is not established, and the zero-flight test failed.** What
> execution actually settled:
>
> 1. **The defect in the b=14 premise is real and stands.** Its stated
>    basis — "velocities in this file are at 2^10 m/cs"
>    (`scenarios/p66-padload.toml:252-259`) — is contradicted, for the two
>    words in TAUROD's own divide, by the spike-B measurement recorded 15
>    lines below it. Nobody re-derived TAUROD after that measurement
>    landed. Whatever the right answer is, the shipped one rests on a
>    premise the repo itself has already disproved.
> 2. **`b=11` vs `b=12` is NOT resolved.** The step from the acceleration
>    scale to TAUROD passes through the `BDDV` by `22D` at
>    `LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1051-1058` — a divide by a
>    direction cosine produced by `DOT`, whose interpretive scaling
>    (`DOT` of two unit vectors carries an inherent factor of two; note
>    the explicit `SL1` after `DOT` at `:928`) is exactly one power of
>    two, and is the difference between the two answers. The `SR2` on the
>    gravity path at `:1047` is a second unresolved shift of the same
>    kind. **Neither is pinned, so neither b is derivable yet.**
>    `b=11 → 0.1875 s`; `b=12 → 0.375 s`. The loop is 4× or 8× too fast;
>    the direction is certain, the factor is not.
> 3. **The traces cannot answer it.** `rod_fit`'s differencing method
>    measured r² = 0.15 / 0.05 / 0.04 on runs 4/5/6 — no usable fit. Cause
>    identified: the method needs `VDGVERT` constant across a difference,
>    and `pdi-descent.toml` drives a ROD *schedule*, so the sim clicks
>    `VDGVERT` throughout the entire P66 window.
> 4. **A discarded inference, recorded so it is not re-derived.** The
>    command floor looked like a MINFORCE clamp at half its loaded value
>    (run 4 bottoms at 178 bits = 2231 N against a pad-loaded 4560 N),
>    which would have pinned the force words — and hence TAUROD — without
>    any of the above. It is **not** a clamp: histogramming run 4's low
>    tail shows a smooth distribution, ~10 frames (one guidance cycle at
>    10 Hz) at each of ~40 consecutive bit values, with no spike anywhere.
>    Separately, `throttle_cmd_pulses` is an accumulation of the DINC
>    stream and the rope's `PIFPSET` drive-past bookkeeping offsets it
>    from `FC`, so its absolute level cannot measure a force word at all.
>    The ceiling *is* meaningful: runs 4 and 6 hit exactly 4096 bits =
>    `FEXTRA` (`THROTTLE_CONTROL_ROUTINES.agc:226`), which validates the
>    bit→newton mapping and therefore the telemetry chain.
>
> **Consequence: the fork is settled by measurement, not derivation, and
> the measurement needs one instrumented flight.** `VDGVERT` is now
> telemetered as `rod_clicks_cum` (commit `24d81e56`) and `rod_fit` grew a
> click-aware level regression (commit `3eaed239`) that recovers τ at
> 0.1875 / 0.375 / 1.5 s to within 0.01 s *through* a VDGVERT change. Task
> order is therefore **fly first, then correct** — the risk-first ordering
> this project already uses. See the revised Task 1' / 2' below; original
> Tasks 1-3 are superseded.

### What this plan does NOT touch

- Ledger open **1a** (braking-gate residual, 911 m / 47 m/s), **2** (the
  P65 PROG alarm code), **3** (the −190 m P64 nav drift), **4** (horizontal
  velocity in a crewless P66). Each needs its own investigation; 4 is
  structural and needs a design decision about what flies the attitude.
- `DPS_MIN_N` / `DPS_VE` / `RCS_THRUST_N` / `RCS_VE` — still
  `lm_simulator.tcl` values, still on the suspect list per
  `eagle/CLAUDE.md:61-67`. If Task 5's flight still limit-cycles with the
  corrected `TAUROD`, `DPS_MIN_N` is the next suspect, not this plan's
  problem.
- M2 (resume snapshots) and M3 (landing radar). The Wave 2 spec pauses the
  wave for an M2/M3 reassessment; that reassessment is still owed and is
  still not made here.

---

## File Structure

| File | Responsibility |
|---|---|
| `runtime/apps/eagle-runtime/src/bin/rod_fit.rs` | **Create.** Offline estimator: reads a telemetry JSONL, isolates the P66 segment, and fits `-1/τ` from throttle-command vs `HDOTDISP` changes across display repaints. Reports per-run τ with R² and sample count. |
| `runtime/crates/eagle-dynamics/src/rod_loop.rs` | **Create.** Offline closed-loop model of the rope's P66 force law against our own DPS plant (first-order lag + envelope). Pure function of τ, lag, mass, initial state; used by regression tests to answer "does this τ limit-cycle?" in microseconds. |
| `runtime/crates/eagle-dynamics/src/lib.rs` | **Modify.** `pub mod rod_loop;` |
| `scenarios/p66-padload.toml` | **Modify.** `TAUROD` b-scale; replace the stale "velocities are b=10" derivation block with the measured one; revisit the `MAXFORCE` 42500 N note now that its b-scale is pinned. |
| `runtime/apps/eagle-runtime/src/padload.rs` | **Modify.** `P66_BSCALE_TABLE` — TAUROD/LAG/TAU/MINFORCE/MAXFORCE status and notes. |
| `runtime/apps/eagle-runtime/src/headless.rs` | **Modify.** Split `prog_lamp_frames` into pre- and post-contact counters. |
| `runtime/apps/eagle-runtime/tests/live_pdi_descent.rs` | **Modify.** Gate on the pre-contact counter; assert the post-contact one is *recorded*, not zero. |
| `runtime/apps/eagle-runtime/src/scenario_mode.rs` | **Modify.** Print both counters in the `[accept]` block. |
| `docs/superpowers/notes/2026-07-31-m1b-rod-loop.md` | **Create.** The measurement ledger for this plan: what was fitted, from which traces, what was changed, what flight 7 measured. |
| `eagle/CLAUDE.md`, `eagle/README.md`, `docs/superpowers/notes/2026-07-26-m1-pdi-flight.md` | **Modify.** Status blocks, after the flight, reflecting whatever it actually measured. |

---

## Task 1' (REVISED): Measure the flown TAUROD from an instrumented flight

Supersedes original Tasks 1 and 3. `rod_fit` and the `rod_clicks_cum`
telemetry field are **done** (commits `4c55466d`, `24d81e56`, `3eaed239`);
what remains is the flight that feeds them.

- [x] **Step 1: Build the estimator** — `src/bin/rod_fit.rs`, 5 tests.
- [x] **Step 2: Run it on runs 4/5/6** — r² = 0.15/0.05/0.04, no fit.
      Recorded in the module doc and in the REVISED block above.
- [x] **Step 3: Telemeter `rod_clicks_cum`** so VDGVERT is recoverable.
- [x] **Step 4: Click-aware level regression** — separates 0.1875 /
      0.375 / 1.5 s to within 0.01 s.
- [ ] **Step 5: Fly, unchanged.**

```bash
cd /home/kazumasa/projects/eagle && \
EAGLE_TELEM_OUT=build/traces/telem-m1-run7.jsonl \
EAGLE_ATT_DEBUG=build/traces/att-m1-run7.log \
make descent-full 2>&1 | tee build/traces/m1-run7.out
```

**The pad load is deliberately NOT corrected first.** Flight 7's job is to
measure τ, and it can only do that while the AGC is still flying the word
whose scale is in question. Correcting first would spend the flight on an
unverified guess and leave the scale just as unpinned.

- [ ] **Step 6: Fit it.**

```bash
cargo run --release --manifest-path runtime/Cargo.toml -p eagle-runtime \
  --bin rod_fit -- build/traces/telem-m1-run7.jsonl
```

Decision rule, fixed before the result is seen — the shipped word is
150 cs at b=14, so the AGC's decoded τ names the true b directly:

| fitted τ (r² ≥ 0.7) | true b-scale | corrected `b =` |
|---|---|---|
| 0.17–0.21 s | 11 | 11 |
| 0.34–0.42 s | 12 | 12 |
| 1.3–1.7 s | 14 — **shipped value is right** | no change; re-plan |
| other, or r² < 0.7 | unresolved | **stop; do not guess** |

Sanity gate: the intercept recovers `VDGVERT_0`, which must land near the
AGC's own displayed rate at P66 entry. If it does not, the fit is
describing something other than the force law and its τ is void.

---

## Task 2' (REVISED): Correct the pad load and re-fly

Gated on Task 1' Step 6 naming a b-scale. Otherwise this task does not run.

**Edit `scenarios/p66-padload.toml` DIRECTLY. Do not regenerate it.**
`scenarios/pdi-descent.toml:25` points the flight at that committed file,
and `padload_gen` is a first-cut generator whose output was hand-curated
into it — regenerating would clobber every provenance comment, including
the spike-B calibration that this whole investigation rests on.

- [ ] **Step 1:** Set `TAUROD`'s `b =` in `scenarios/p66-padload.toml` to
      the measured value; provenance = "measured, flight 7, rod_fit".
- [ ] **Step 2:** Replace the stale derivation block at `:252-263` (the
      "velocities are b=10" premise) with the anchors that survived —
      `VDGVERT`/`HDOTDISP` b=7 from spike B, and the *measured* TAUROD
      scale. Do **not** restate the b=-4 acceleration chain as if it
      derived the answer; it did not.
- [ ] **Step 3:** `P66_BSCALE_TABLE`: `TAUROD` → `Verified` citing the
      flight. `LAG/TAU`/`MINFORCE`/`MAXFORCE` stay `Unverified` — nothing
      in this plan pinned them, and the discarded clamp inference is
      exactly why. Update the table's doc comment to say so.
- [ ] **Step 4:** `LAG/TAU`'s *value* is `THROTLAG / TAUROD` = 0.2/1.5 =
      0.1333, unchanged, but say in the comment that it is only right
      while TAUROD's value stays 150 cs.
- [ ] **Step 5:** `make test && make lint`, commit.
- [ ] **Step 6:** Re-fly (flight 8) and re-fit. τ must now read ≈1.5 s —
      that is the check that the correction reached the AGC.
- [ ] **Step 7:** Update `scenarios/pdi-descent.toml:73-79`, which still
      asserts "TAUROD's scale is derivable statically (LLGE:155-157 +
      :1050 + GSCALE at :1477), costing no flights". That route is the one
      this plan took, and it has two unpinned one-power-of-two shifts in
      it (§2 of the ledger note) — say what actually settled the scale.

---

## Task 3' (REVISED): Offline closed-loop model — DEFERRED

Original Task 3 built `eagle-dynamics::rod_loop` as a regression guard.
**Deferred, not dropped.** It was written to encode "0.1875 s rings,
1.5 s does not" as a test, and that pair of numbers is precisely what is
not yet established. Building it now would bake the unverified answer into
a test. Build it after Task 1' names the τ, so its constants are measured
ones.

---

## Task 1 (SUPERSEDED): Measure the flown TAUROD from the existing traces

No flights. The answer is already in `build/traces/`.

**Method.** In P66 the rope commands

$$a_{\mathrm{cmd}} = \frac{1}{\cos\theta}\left[\frac{V_{\mathrm{DGVERT}} - H_{\mathrm{DOTDISP}}}{\tau} + g_{\mathrm{term}}\right]$$

and our telemetry carries `throttle_cmd_pulses` (absolute commanded
throttle in bits — `runner.rs:786,790` increments it per DINC, and
`sim.rs:427` turns it into newtons), `mass_kg`, `tilt_deg`, and
`agc_hdot_ms` (= `HDOTDISP`, parsed from N63 R2 at `sim.rs:122`).

`VDGVERT` is **not** in the telemetry, but it is piecewise-constant between
ROD clicks. Differencing across a single `HDOTDISP` repaint therefore
cancels it *and* the gravity term:

$$\Delta\!\left(a_{\mathrm{cmd}}\cos\theta\right) = -\frac{1}{\tau}\,\Delta H_{\mathrm{DOTDISP}}$$

so an ordinary least-squares fit of `Δ(a_cmd·cosθ)` on `ΔHDOTDISP` over
repaint events has slope `-1/τ`. The two candidate answers are 8× apart —
`b=14 → τ=0.1875 s → slope ≈ -5.33 s⁻¹` versus
`b=11 → τ=1.5 s → slope ≈ -0.667 s⁻¹` — so this is not a close call.

**Why differencing and not a level regression.** `agc_hdot_ms` comes from
the DSKY display, which repaints about once a second (median gap 0.90 s,
measured over run 4's 134 P66 updates — ledger "Blocker 3"), while
telemetry is 10 Hz. Regressing 10 Hz `a_cmd` on a ~1 Hz staircase is
errors-in-variables and **attenuates the slope toward zero** — i.e. it
would make a true b=14 look like b=11. Differencing at the repaint instant
compares two quantities sampled at the same event and does not have that
bias. The level regression is still computed, as a cross-check that must be
reported but must **not** be used to decide.

**Known residual.** `FWEIGHT` (the engine-lag compensation,
`LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1069-1076`) also enters `a_cmd` and
does change across a repaint, so the fit will not be perfect. Report R²; if
R² < 0.5 the method has failed and the task must say so rather than quote a
τ.

**Files:**
- Create: `runtime/apps/eagle-runtime/src/bin/rod_fit.rs`
- Test: `runtime/apps/eagle-runtime/src/bin/rod_fit.rs` (`#[cfg(test)]` module)

**Interfaces:**
- Produces: `rod_fit::Fit { tau_s: f64, slope: f64, r2: f64, n: usize }`
  and `rod_fit::fit_tau(samples: &[Sample]) -> Option<Fit>`, where
  `Sample { t_s: f64, a_cmd_cos: f64, hdot_ms: f64 }`.
- Consumes: nothing from other tasks. Task 2 consumes this task's measured
  τ; Task 3 consumes nothing but is validated against it.

- [ ] **Step 1: Write the failing test for the fitter's arithmetic**

Put this in `runtime/apps/eagle-runtime/src/bin/rod_fit.rs`. It builds a
synthetic P66 segment with a known τ and a piecewise-constant `VDGVERT`,
and asserts the fit recovers τ. The `VDGVERT` step is deliberately placed
mid-segment: a fitter that forgot to difference would be thrown by it.

```rust
#[cfg(test)]
mod tests {
    use super::*;

    /// Synthesize `a_cmd·cosθ` from the rope's law with a known tau and a
    /// VDGVERT step partway through, sampled only at repaint instants.
    fn synth(tau_s: f64) -> Vec<Sample> {
        const G: f64 = 1.62;
        let mut out = Vec::new();
        for i in 0..60 {
            let t_s = i as f64 * 0.9;
            // A limit-cycle-ish rate history: swings tens of m/s.
            let hdot_ms = -7.0 + 12.0 * (t_s * 0.6).sin();
            // VDGVERT steps once, at the halfway point.
            let vdg = if i < 30 { -3.0 } else { -4.0 };
            let a_cmd_cos = (vdg - hdot_ms) / tau_s + G;
            out.push(Sample { t_s, a_cmd_cos, hdot_ms });
        }
        out
    }

    #[test]
    fn fit_recovers_a_known_tau() {
        let fit = fit_tau(&synth(1.5)).expect("enough samples");
        assert!(
            (fit.tau_s - 1.5).abs() < 0.05,
            "recovered tau {} from a synthetic 1.5 s segment",
            fit.tau_s
        );
        assert!(fit.r2 > 0.99, "r2 {}", fit.r2);
    }

    #[test]
    fn fit_separates_the_two_candidate_scales() {
        let fast = fit_tau(&synth(0.1875)).expect("enough samples");
        let slow = fit_tau(&synth(1.5)).expect("enough samples");
        assert!(
            fast.tau_s < 0.4 && slow.tau_s > 0.8,
            "the b=14 and b=11 hypotheses must not be confusable: {} vs {}",
            fast.tau_s,
            slow.tau_s
        );
    }

    #[test]
    fn fit_needs_samples() {
        assert!(fit_tau(&[]).is_none());
    }
}
```

- [ ] **Step 2: Run it and watch it fail to compile**

```bash
cd runtime && cargo test -p eagle-runtime --bin rod_fit
```
Expected: FAIL — `cannot find function fit_tau`, `cannot find type Sample`.

- [ ] **Step 3: Implement the fitter**

Full contents of `runtime/apps/eagle-runtime/src/bin/rod_fit.rs`, above the
test module:

```rust
//! Offline estimator for the effective P66 ROD time constant.
//!
//! Reads a telemetry JSONL written by `EAGLE_TELEM_OUT` and fits the
//! slope of the rope's P66 force law
//! (`vendor/virtualagc/Luminary099/LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1041-1050`)
//!
//! ```text
//!   a_cmd = [ (VDGVERT - HDOTDISP) / TAUROD + g ] / cos(tilt)
//! ```
//!
//! VDGVERT is not telemetered, but it is piecewise-constant between ROD
//! clicks, so differencing across one HDOTDISP repaint cancels it and the
//! gravity term, leaving `d(a_cmd·cosθ) = -(1/tau)·d(HDOTDISP)`.
//!
//! Usage: `cargo run -p eagle-runtime --bin rod_fit -- <telem.jsonl>...`

use std::env;
use std::fs::File;
use std::io::{BufRead, BufReader};

use anyhow::{Context, Result, bail};
use eagle_dynamics::constants::{DPS_MIN_N, THRUST_N_PER_PULSE};

/// One repaint-instant observation.
#[derive(Debug, Clone, Copy)]
pub struct Sample {
    pub t_s: f64,
    /// Commanded acceleration projected back onto the vertical, m/s².
    pub a_cmd_cos: f64,
    /// The AGC's own displayed altitude rate, m/s.
    pub hdot_ms: f64,
}

#[derive(Debug, Clone, Copy)]
pub struct Fit {
    pub tau_s: f64,
    pub slope: f64,
    pub r2: f64,
    pub n: usize,
}

/// OLS of `Δ(a_cmd·cosθ)` on `ΔHDOTDISP` between consecutive samples.
/// Returns `None` if fewer than 8 usable differences survive.
pub fn fit_tau(samples: &[Sample]) -> Option<Fit> {
    // Only differences across a real rate change carry signal; a repaint
    // that did not move the display is all noise and no leverage.
    const MIN_DHDOT_MS: f64 = 0.5;
    let mut dx = Vec::new();
    let mut dy = Vec::new();
    for w in samples.windows(2) {
        let d_h = w[1].hdot_ms - w[0].hdot_ms;
        if d_h.abs() < MIN_DHDOT_MS {
            continue;
        }
        dx.push(d_h);
        dy.push(w[1].a_cmd_cos - w[0].a_cmd_cos);
    }
    if dx.len() < 8 {
        return None;
    }
    let n = dx.len() as f64;
    let mx = dx.iter().sum::<f64>() / n;
    let my = dy.iter().sum::<f64>() / n;
    let sxx: f64 = dx.iter().map(|x| (x - mx) * (x - mx)).sum();
    let sxy: f64 = dx
        .iter()
        .zip(&dy)
        .map(|(x, y)| (x - mx) * (y - my))
        .sum();
    if sxx <= 0.0 {
        return None;
    }
    let slope = sxy / sxx;
    if slope >= 0.0 {
        // A rate loop must push back: a non-negative slope means the model
        // does not describe this data, and a "tau" from it is meaningless.
        return None;
    }
    let intercept = my - slope * mx;
    let ss_tot: f64 = dy.iter().map(|y| (y - my) * (y - my)).sum();
    let ss_res: f64 = dx
        .iter()
        .zip(&dy)
        .map(|(x, y)| {
            let e = y - (slope * x + intercept);
            e * e
        })
        .sum();
    let r2 = if ss_tot > 0.0 { 1.0 - ss_res / ss_tot } else { 0.0 };
    Some(Fit { tau_s: -1.0 / slope, slope, r2, n: dx.len() })
}

/// Pull the P66 segment out of a telemetry JSONL, keeping only frames
/// where the throttle is off both stops (the law is linear only there)
/// and only the first frame after each `HDOTDISP` change (a repaint).
fn load(path: &str, max_force_n: f64) -> Result<Vec<Sample>> {
    let file = File::open(path).with_context(|| format!("open {path}"))?;
    let mut out = Vec::new();
    let mut last_hdot: Option<f64> = None;
    let mut in_p66 = false;
    for line in BufReader::new(file).lines() {
        let line = line?;
        let v: serde_json::Value = match serde_json::from_str(&line) {
            Ok(v) => v,
            Err(_) => continue,
        };
        if v.get("type").and_then(|t| t.as_str()) != Some("telemetry") {
            continue;
        }
        if v.get("mm").and_then(|m| m.as_str()) == Some("66") {
            in_p66 = true;
        }
        if !in_p66 || v.get("touchdown").map(|t| !t.is_null()).unwrap_or(false) {
            continue;
        }
        let (Some(hdot), Some(pulses), Some(mass), Some(tilt)) = (
            v.get("agc_hdot_ms").and_then(|x| x.as_f64()),
            v.get("throttle_cmd_pulses").and_then(|x| x.as_i64()),
            v.get("mass_kg").and_then(|x| x.as_f64()),
            v.get("tilt_deg").and_then(|x| x.as_f64()),
        ) else {
            continue;
        };
        // Repaint detector: the display only moves when the AGC repaints.
        if last_hdot == Some(hdot) {
            continue;
        }
        last_hdot = Some(hdot);
        let force_n = pulses as f64 * THRUST_N_PER_PULSE;
        // Off both stops: at either stop the command is clipped and the
        // slope carries no information about tau.
        if force_n <= DPS_MIN_N * 1.02 || force_n >= max_force_n * 0.98 {
            continue;
        }
        if mass <= 0.0 {
            continue;
        }
        let cos = tilt.to_radians().cos();
        out.push(Sample {
            t_s: v.get("t_s").and_then(|x| x.as_f64()).unwrap_or(0.0),
            a_cmd_cos: force_n / mass * cos,
            hdot_ms: hdot,
        });
    }
    Ok(out)
}

fn main() -> Result<()> {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.is_empty() {
        bail!("usage: rod_fit <telem.jsonl>...");
    }
    // MAXFORCE as the runs actually flew it: the committed pad load's
    // 42500 N (scenarios/p66-padload.toml MAXFORCE), not DPS_FTP_N.
    const FLOWN_MAXFORCE_N: f64 = 42_500.0;
    for path in &args {
        let samples = load(path, FLOWN_MAXFORCE_N)?;
        match fit_tau(&samples) {
            Some(f) => println!(
                "{path}: tau = {:.4} s  (slope {:.4} 1/s, r2 {:.3}, n {}, \
                 {} unsaturated repaints)",
                f.tau_s,
                f.slope,
                f.r2,
                f.n,
                samples.len()
            ),
            None => println!("{path}: no fit ({} usable samples)", samples.len()),
        }
    }
    Ok(())
}
```

Add to `runtime/apps/eagle-runtime/Cargo.toml` only if not already present
(check first — `serde_json` and `anyhow` are almost certainly there):

```bash
grep -E "^serde_json|^anyhow" runtime/apps/eagle-runtime/Cargo.toml
```

- [ ] **Step 4: Run the tests to green**

```bash
cd runtime && cargo test -p eagle-runtime --bin rod_fit
```
Expected: 3 passed.

- [ ] **Step 5: Run it on the three flights that reached P66**

```bash
cd runtime && cargo run --release -p eagle-runtime --bin rod_fit -- \
  ../build/traces/telem-m1-run4.jsonl \
  ../build/traces/telem-m1-run5.jsonl \
  ../build/traces/telem-m1-run6.jsonl
```

**Record the exact stdout.** This is the measurement the whole plan turns
on. Interpretation, decided *before* looking:

| measured τ | verdict |
|---|---|
| 0.13–0.28 s on ≥2 runs, R² ≥ 0.5 | b=14 is wrong; the rope reads TAUROD at **b=11**. Proceed to Task 2. |
| 1.1–2.0 s on ≥2 runs, R² ≥ 0.5 | b=14 is right; the limit cycle has another cause. **Stop and re-plan** — do not change the pad load. Write the finding to the ledger and hand back. |
| anything else, or R² < 0.5, or `no fit` | The method did not resolve it. **Stop and re-plan.** Do not guess. |

- [ ] **Step 6: Commit**

```bash
git add runtime/apps/eagle-runtime/src/bin/rod_fit.rs runtime/apps/eagle-runtime/Cargo.toml
git commit -m "feat(runtime): rod_fit measures the flown P66 time constant from telemetry"
```

---

## Task 2: Pin the four b-scales and correct the pad load

Gated on Task 1 returning the "b=14 is wrong" verdict. If it did not, this
task does not run.

**Files:**
- Modify: `scenarios/p66-padload.toml:250-310`
- Modify: `runtime/apps/eagle-runtime/src/padload.rs:296-385` (`P66_BSCALE_TABLE`)
- Test: `runtime/apps/eagle-runtime/src/padload.rs` (`#[cfg(test)]` module)

**Interfaces:**
- Consumes: Task 1's measured τ (for the provenance string only).
- Produces: `padload::check_bscales(false)` now succeeds — every P66 word
  is `Verified`. Task 5's flight depends on the corrected `TAUROD`.

- [ ] **Step 1: Write the failing test**

Append to the `#[cfg(test)]` module in
`runtime/apps/eagle-runtime/src/padload.rs`:

```rust
#[test]
fn p66_bscales_are_all_pinned() {
    // Every word in the P66 cluster is now derived from the rope's own
    // published scales; check_bscales must pass without the escape hatch.
    check_bscales(false).expect("no Unverified b-scales remain");
}

#[test]
fn taurod_scale_is_the_velocity_scale_minus_the_acceleration_scale() {
    // HDOTDISP/VDGVERT are b=7 m/cs (spike-B live read-back), the P66
    // acceleration is b=-4 m/cs^2 (THROTTLE_CONTROL_ROUTINES.agc:206),
    // and interpretive DDV subtracts b-scales.
    assert_eq!(HDOT_B_SCALE - ACCEL_B_SCALE, TAUROD_B_SCALE);
    // GSCALE (2DEC 100 B-11) sits in the identical role four lines later
    // and must therefore carry the same scale.
    assert_eq!(TAUROD_B_SCALE, GSCALE_B_SCALE);
    // Force words: MASS (b=16 kg) times acceleration.
    assert_eq!(MASS_B_SCALE + ACCEL_B_SCALE, FORCE_B_SCALE);
}
```

- [ ] **Step 2: Run it and watch it fail**

```bash
cd runtime && cargo test -p eagle-runtime --lib padload
```
Expected: FAIL — `cannot find value HDOT_B_SCALE` (and the four siblings),
plus `p66_bscales_are_all_pinned` failing on the four `Unverified` entries.

- [ ] **Step 3: Add the scale constants**

Insert above `P66_BSCALE_TABLE` in
`runtime/apps/eagle-runtime/src/padload.rs`:

```rust
/// The b-scale of `HDOTDISP`/`VDGVERT`: DP b=7 in m/cs. Measured live
/// (spike B) — `HDOTDISP` read back as `hi=0o36` = 491520 DP pulses while
/// N63 R2 displayed +00756 (75.6 ft/s), and `491520 · 2^-21 m/cs` =
/// 0.2344 m/cs = 76.9 ft/s. See the RODSCALE entry below.
pub const HDOT_B_SCALE: i32 = 7;

/// The b-scale of a P66 acceleration: b=-4 in m/cs². The rope states it
/// in SI: `vendor/virtualagc/Luminary099/THROTTLE_CONTROL_ROUTINES.agc:206`,
/// "MASSMULT SCALES ACCELERATION, ARRIVING IN A AND L IN UNITS OF
/// 2(-4) M/CS/CS, TO FORCE IN PULSE UNITS." The flown pad load agrees —
/// `ABRFG` is annotated `B+04` (LUM69R2/PADLOADS.agc:409-414).
pub const ACCEL_B_SCALE: i32 = -4;

/// The b-scale of `MASS`: b=16 in kg.
/// `vendor/virtualagc/Luminary099/ERASABLE_ASSIGNMENTS.agc:1698`,
/// "# (1) MASS AFTER STAGING, SCALE AT B16 KG".
pub const MASS_B_SCALE: i32 = 16;

/// `GSCALE  2DEC  100 B-11`
/// (`vendor/virtualagc/Luminary099/LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1477`)
/// — 100 centiseconds at b=11. It divides `GDT/2` to make the gravity term
/// that is `DAD`ed to TAUROD's own term at `:1050`, so it is the same kind
/// of quantity in the same place: a DP time in centiseconds.
pub const GSCALE_B_SCALE: i32 = 11;

/// `TAUROD`, centiseconds, b=11 — interpretive `DDV` subtracts b-scales,
/// so `b = HDOT_B_SCALE - ACCEL_B_SCALE`. **This corrects a b=14
/// hypothesis** that assumed the divide's numerator was at the
/// `VBRFG`/`VIGN` velocity scale (b=10); the numerator is
/// `VDGVERT - HDOTDISP`, which spike B measured at b=7.
pub const TAUROD_B_SCALE: i32 = HDOT_B_SCALE - ACCEL_B_SCALE;

/// `MINFORCE`/`MAXFORCE`, kg·m/cs² (1 kg·m/cs² = 1e4 N), b=12: the rope
/// divides them by `MASS` to bound `/AFC/`
/// (`LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1086-1091`), so
/// `b = MASS_B_SCALE + ACCEL_B_SCALE`.
pub const FORCE_B_SCALE: i32 = MASS_B_SCALE + ACCEL_B_SCALE;
```

- [ ] **Step 4: Rewrite the four table entries**

Replace the `TAUROD`, `LAG/TAU`, `MINFORCE`, `MAXFORCE` entries in
`P66_BSCALE_TABLE` with:

```rust
    BScaleEntry {
        symbol: "TAUROD",
        status: BScaleStatus::Verified,
        note: "b=11, CENTISECONDS. LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1041-1044 divides \
               (VDGVERT - HDOTDISP) by TAUROD to make a P66 acceleration. Interpretive DDV \
               subtracts b-scales: b = 7 - (-4) = 11, with the numerator's b=7 m/cs measured \
               live in spike B (see RODSCALE) and the acceleration's b=-4 m/cs^2 stated by \
               THROTTLE_CONTROL_ROUTINES.agc:206. Corroborated in-rope by GSCALE (2DEC 100 \
               B-11, :1477), the same kind of divisor four lines later at :1046-1048 whose \
               quotient is DAD'ed to this one at :1050. SUPERSEDES a b=14 hypothesis that \
               used the VBRFG/VIGN velocity scale (b=10) for a numerator that is not at it; \
               at b=14 the AGC read the committed 150 cs word as 18.75 cs = 0.1875 s.",
    },
    BScaleEntry {
        symbol: "LAG/TAU",
        status: BScaleStatus::Verified,
        note: "b=0, DIMENSIONLESS -- the symtab calls it \"LAG TIME DIVIDED BY TAUROD\" \
               (ERASABLE_ASSIGNMENTS.agc:1409) and LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1083-1085 \
               DMPs it into a quantity that is then DAD'ed to /AFC/, so it cannot carry units \
               and its b-scale is independent of the velocity scale that moved TAUROD. Its \
               VALUE does depend on TAUROD: lag/TAUROD = THROTLAG (0.2 s, \
               CONTROLLED_CONSTANTS.agc:134) / 1.5 s = 0.1333.",
    },
    BScaleEntry {
        symbol: "MINFORCE",
        status: BScaleStatus::Verified,
        note: "b=12, kg*m/cs^2 (1 kg*m/cs^2 = 1e4 N). LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1089-1091 \
               divides MINFORCE by MASS to bound /AFC/, so b = b(MASS) + b(accel) = 16 + (-4), \
               with MASS at b=16 kg per ERASABLE_ASSIGNMENTS.agc:1698 and the acceleration at \
               b=-4 per THROTTLE_CONTROL_ROUTINES.agc:206. The VALUE, 4560 N, is still \
               eagle_dynamics::constants::DPS_MIN_N -- an lm_simulator.tcl number, NOT the \
               rope's, and still on the suspect list (eagle/CLAUDE.md).",
    },
    BScaleEntry {
        symbol: "MAXFORCE",
        status: BScaleStatus::Verified,
        note: "b=12, kg*m/cs^2, same derivation as MINFORCE from \
               LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1086-1088. The committed VALUE is a \
               separate question from the scale -- see scenarios/p66-padload.toml's MAXFORCE \
               comment.",
    },
```

Update the `P66_BSCALE_TABLE` doc comment: it currently says all four
"are marked `Unverified` per the brief's explicit escape hatch". Replace
that sentence with a statement that all four are now derived from the
rope's published scales, and that `--allow-unverified` remains only for a
future word that is not yet pinned.

- [ ] **Step 5: Run the tests to green**

```bash
cd runtime && cargo test -p eagle-runtime --lib padload
```
Expected: PASS, including the two new tests.

- [ ] **Step 6: Correct the pad load**

In `scenarios/p66-padload.toml`, change the `TAUROD` word:

```toml
[[word]]
symbol = "TAUROD"
physical = { value = 150.0, b = 11, dp = true }
provenance = "derived: b = b(VDGVERT-HDOTDISP) - b(accel) = 7 - (-4); LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1041-1044, THROTTLE_CONTROL_ROUTINES.agc:206"
comment = "ROD time constant, 150 cs = 1.5 s, CENTISECONDS at b=11 (was b=14 -> AGC read 0.1875 s)"
```

Replace the stale derivation block at lines 252-263 (the one whose premise
is "velocities in this file are at 2^10 m/cs") with:

```toml
# ---- P66 rate-of-descent cluster --------------------------------------
# b-scales below are derived from the rope's own published scales, not
# from a global "velocities are b=10" premise -- that premise is true for
# VBRFG/VIGN but NOT for the two words the P66 force law actually divides.
# Anchors:
#   VDGVERT/HDOTDISP  b=7   m/cs      spike-B live read-back (below)
#   P66 acceleration  b=-4  m/cs^2    THROTTLE_CONTROL_ROUTINES.agc:206
#                                     ("2(-4) M/CS/CS"); ABRFG "B+04"
#   MASS              b=16  kg        ERASABLE_ASSIGNMENTS.agc:1698
# Interpreter DDV subtracts b-scales and DMP adds them, so:
#   TAUROD  = vel/acc     -> b = 7 - (-4) = 11, CENTISECONDS
#   LAG/TAU = ratio       -> b = 0,  dimensionless
#   FORCE   = MASS * acc  -> b = 16 + (-4) = 12, kg*m/cs^2 (= 1e4 N)
# TAUROD was b=14 here until 2026-07-31, from the VBRFG velocity scale.
# At b=14 the AGC decoded this word's 150 cs as 18.75 cs = 0.1875 s -- an
# 8x too-fast rate loop against a 0.2 s engine lag (THROTLAG,
# CONTROLLED_CONSTANTS.agc:134), which is what runs 4-6 flew. Measured
# back out of those runs' own telemetry by `rod_fit`; see
# docs/superpowers/notes/2026-07-31-m1b-rod-loop.md.
```

- [ ] **Step 7: Settle MAXFORCE's value**

The existing comment defers 42500 N vs `DPS_FTP_N` (48145.4 N) on three
grounds, the first of which was "this word's b-scale is still UNVERIFIED".
That ground is now gone. Read the whole comment
(`scenarios/p66-padload.toml:300-330`), and:

- If the remaining grounds still hold, **leave the value at 42500 N** and
  edit only the first ground to say the scale is now pinned and the value
  is deferred for the other reasons. Changing two things at once would make
  flight 7 uninterpretable.
- If they do not, still leave it — flight 7 must isolate `TAUROD`. Record
  the decision either way in the change note.

**This step changes at most a comment.** If you find yourself editing a
`value =`, stop.

- [ ] **Step 8: Regenerate and diff the pad load**

```bash
cd runtime && cargo run -p eagle-runtime --bin padload_gen -- --help 2>&1 | head -20
```
Then run it the way the Makefile does (check `grep -n padload_gen ../Makefile`)
and confirm it now runs **without** `--allow-unverified`.

- [ ] **Step 9: Full fast gate**

```bash
cd /home/kazumasa/projects/eagle && make test && make lint
```
Expected: both green.

- [ ] **Step 10: Commit**

```bash
git add scenarios/p66-padload.toml runtime/apps/eagle-runtime/src/padload.rs
git commit -m "fix(padload): TAUROD is b=11 cs, not b=14 -- the AGC was flying a 0.1875 s rate loop"
```

---

## Task 3: An offline closed-loop model of the P66 rate law

The regression guard. It answers "does this τ limit-cycle?" without an AGC
and without a flight, so the next person to touch `TAUROD`, `DPS_TAU`,
`DPS_MIN_N` or `MAXFORCE` gets an answer in microseconds.

**Files:**
- Create: `runtime/crates/eagle-dynamics/src/rod_loop.rs`
- Modify: `runtime/crates/eagle-dynamics/src/lib.rs`

**Interfaces:**
- Consumes: `eagle_dynamics::constants::{DPS_MIN_N, DPS_FTP_N, DPS_TAU, THRUST_N_PER_PULSE}`.
- Produces: `rod_loop::simulate(cfg: &RodLoopCfg) -> RodLoopResult`, with
  `RodLoopCfg { tau_rod_s, lag_over_tau, dps_tau_s, min_force_n, max_force_n, mass_kg, alt_m, vz_ms, vdg_ms, dt_s, duration_s }`
  and `RodLoopResult { thrust_min_n, thrust_max_n, vz_min_ms, vz_max_ms, stop_to_stop_cycles: usize, settled: bool }`.

- [ ] **Step 1: Write the failing tests**

In `runtime/crates/eagle-dynamics/src/rod_loop.rs`:

```rust
#[cfg(test)]
mod tests {
    use super::*;

    fn cfg(tau_rod_s: f64) -> RodLoopCfg {
        RodLoopCfg {
            tau_rod_s,
            lag_over_tau: 0.2 / tau_rod_s,
            dps_tau_s: crate::constants::DPS_TAU,
            min_force_n: crate::constants::DPS_MIN_N,
            max_force_n: 42_500.0,
            mass_kg: 7_000.0,
            alt_m: 240.0,
            vz_ms: -3.0,
            vdg_ms: -1.5,
            dt_s: 0.01,
            duration_s: 120.0,
        }
    }

    #[test]
    fn the_flown_time_constant_limit_cycles() {
        // 0.1875 s is what a b=14 TAUROD word decoded to at b=11.
        let r = simulate(&cfg(0.1875));
        assert!(
            r.stop_to_stop_cycles >= 3,
            "expected a bang-bang limit cycle, got {r:?}"
        );
        assert!(!r.settled, "{r:?}");
    }

    #[test]
    fn the_corrected_time_constant_settles() {
        let r = simulate(&cfg(1.5));
        assert_eq!(r.stop_to_stop_cycles, 0, "{r:?}");
        assert!(r.settled, "{r:?}");
        // It should track the commanded rate, not just avoid ringing.
        assert!(
            (r.vz_final_ms - cfg(1.5).vdg_ms).abs() < 0.5,
            "settled at {} against a {} m/s command",
            r.vz_final_ms,
            cfg(1.5).vdg_ms
        );
    }

    #[test]
    fn the_engine_lag_is_what_makes_a_fast_loop_ring() {
        // Same fast tau with an instantaneous engine does not ring: this
        // pins the mechanism, so a future DPS_TAU change is evaluable.
        let mut c = cfg(0.1875);
        c.dps_tau_s = 1e-6;
        assert_eq!(simulate(&c).stop_to_stop_cycles, 0);
    }
}
```

- [ ] **Step 2: Run and watch it fail**

```bash
cd runtime && cargo test -p eagle-dynamics rod_loop
```
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement**

```rust
//! Offline model of the rope's P66 rate-of-descent loop.
//!
//! This is **not** the flight path — the flight path is the real
//! Luminary099 in yaAGC. It is a model of the published force law
//! (`vendor/virtualagc/Luminary099/LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1041-1104`)
//!
//! ```text
//!   a_cmd = (VDGVERT - hdot)/TAUROD + g + (LAG/TAU)·a_cmd_prev
//!   F_cmd = clamp(MASS·a_cmd, MINFORCE, MAXFORCE)
//! ```
//!
//! against our own DPS plant (first-order lag, `DPS_TAU`), so that a
//! candidate time constant can be judged without spending a 20-minute
//! flight. Its job is to answer one question — does this loop ring? — and
//! the tests below encode both known answers.

use crate::constants::LUNAR_G;

#[derive(Debug, Clone, Copy)]
pub struct RodLoopCfg {
    /// P66 rate time constant, seconds.
    pub tau_rod_s: f64,
    /// The rope's `LAG/TAU` word: engine lag divided by `tau_rod_s`.
    pub lag_over_tau: f64,
    /// Plant: first-order DPS response time constant, seconds.
    pub dps_tau_s: f64,
    pub min_force_n: f64,
    pub max_force_n: f64,
    pub mass_kg: f64,
    pub alt_m: f64,
    pub vz_ms: f64,
    /// Commanded descent rate (negative = descending), m/s.
    pub vdg_ms: f64,
    pub dt_s: f64,
    pub duration_s: f64,
}

#[derive(Debug, Clone, Copy)]
pub struct RodLoopResult {
    pub thrust_min_n: f64,
    pub thrust_max_n: f64,
    pub vz_min_ms: f64,
    pub vz_max_ms: f64,
    pub vz_final_ms: f64,
    /// Times the commanded force went from one stop to the other. Any
    /// value above 2 is a bang-bang limit cycle.
    pub stop_to_stop_cycles: usize,
    /// True when the last 20 % of the run stayed off both stops and the
    /// rate held within 0.5 m/s of the command.
    pub settled: bool,
}

/// Guidance runs at 1 s in P66 ("PGUID IS EITHER 1 OR 2 SECONDS",
/// `vendor/virtualagc/Luminary099/THROTTLE_CONTROL_ROUTINES.agc:141`;
/// P66VERTA re-arms RODTASK on a `1SEC` TWIDDLE at `:938-941`).
const GUIDANCE_PERIOD_S: f64 = 1.0;

pub fn simulate(cfg: &RodLoopCfg) -> RodLoopResult {
    let mut alt = cfg.alt_m;
    let mut vz = cfg.vz_ms;
    let mut thrust = cfg.min_force_n;
    let mut f_cmd = cfg.min_force_n;
    let mut a_prev = 0.0_f64;
    let mut since_guidance = GUIDANCE_PERIOD_S;

    let (mut t_min, mut t_max) = (f64::MAX, f64::MIN);
    let (mut v_min, mut v_max) = (f64::MAX, f64::MIN);
    let mut cycles = 0usize;
    // -1 at the low stop, +1 at the high stop, 0 in between.
    let mut last_stop = 0i8;

    let steps = (cfg.duration_s / cfg.dt_s).round() as usize;
    let settle_from = steps * 8 / 10;
    let mut settled = true;

    for i in 0..steps {
        since_guidance += cfg.dt_s;
        if since_guidance >= GUIDANCE_PERIOD_S {
            since_guidance = 0.0;
            let a_cmd = (cfg.vdg_ms - vz) / cfg.tau_rod_s + LUNAR_G + cfg.lag_over_tau * a_prev;
            a_prev = a_cmd;
            f_cmd = (cfg.mass_kg * a_cmd).clamp(cfg.min_force_n, cfg.max_force_n);
        }

        // Plant: first-order lag toward the commanded force.
        let alpha = cfg.dt_s / cfg.dps_tau_s.max(cfg.dt_s);
        thrust += (f_cmd - thrust) * alpha.min(1.0);

        vz += (thrust / cfg.mass_kg - LUNAR_G) * cfg.dt_s;
        alt += vz * cfg.dt_s;
        if alt <= 0.0 {
            alt = 0.0;
        }

        let stop = if f_cmd <= cfg.min_force_n * 1.0001 {
            -1
        } else if f_cmd >= cfg.max_force_n * 0.9999 {
            1
        } else {
            0
        };
        if stop != 0 && last_stop != 0 && stop != last_stop {
            cycles += 1;
        }
        if stop != 0 {
            last_stop = stop;
        }

        t_min = t_min.min(thrust);
        t_max = t_max.max(thrust);
        v_min = v_min.min(vz);
        v_max = v_max.max(vz);
        if i >= settle_from && (stop != 0 || (vz - cfg.vdg_ms).abs() > 0.5) {
            settled = false;
        }
    }

    RodLoopResult {
        thrust_min_n: t_min,
        thrust_max_n: t_max,
        vz_min_ms: v_min,
        vz_max_ms: v_max,
        vz_final_ms: vz,
        stop_to_stop_cycles: cycles,
        settled,
    }
}
```

Add `pub mod rod_loop;` to `runtime/crates/eagle-dynamics/src/lib.rs`. If
`LUNAR_G` is not the name in `constants.rs`, use whatever is
(`grep -n "G_MOON\|LUNAR_G\|MOON_G" runtime/crates/eagle-dynamics/src/constants.rs`)
— do not add a second gravity constant.

- [ ] **Step 4: Run to green**

```bash
cd runtime && cargo test -p eagle-dynamics rod_loop
```
Expected: 3 passed. If `the_corrected_time_constant_settles` fails, **do
not tune the thresholds to make it pass** — a 1.5 s loop that does not
settle against a 0.2 s lag would mean the model is wrong, and that is a
finding, not a test-tuning problem.

- [ ] **Step 5: Cross-check against Task 1's measurement**

Run `simulate` at Task 1's *measured* τ and confirm it reproduces the
flown symptom qualitatively — the ledger recorded run 4 sweeping
0 → 46 706 N with `vz` spanning −47.3 to +26.0 m/s. It will not match
numerically (no attitude, no mass depletion, no FWEIGHT), and it is not
supposed to. Record the comparison in the change note as corroboration
only.

- [ ] **Step 6: Commit**

```bash
git add runtime/crates/eagle-dynamics/src/rod_loop.rs runtime/crates/eagle-dynamics/src/lib.rs
git commit -m "test(dynamics): offline P66 rate-loop model pins why 0.1875 s rings and 1.5 s does not"
```

---

## Task 4: Fix the acceptance's known false negative

Ledger open item 2a: `prog_lamp_frames` keeps counting through the sim's
~2 s post-touchdown tail, so an alarm raised *after* a landing the vehicle
already survived would fail `prog_lamp_frames == 0` and red a run that
deserved to pass. The ledger explicitly refused to fix this by loosening
the gate. The fix is to **count both windows** and gate on the one that
means something, so no evidence is discarded.

**Files:**
- Modify: `runtime/apps/eagle-runtime/src/headless.rs:55-110,272`
- Modify: `runtime/apps/eagle-runtime/src/scenario_mode.rs:72`
- Modify: `runtime/apps/eagle-runtime/tests/live_pdi_descent.rs:26,129,235-252`
- Modify: `runtime/apps/eagle-runtime/tests/live_p66_descent.rs:106,174`

**Interfaces:**
- Produces: `HeadlessResult.prog_lamp_frames` (unchanged name, now
  **pre-contact only**) and `HeadlessResult.prog_lamp_frames_post_contact`.

- [ ] **Step 1: Write the failing test**

In `runtime/apps/eagle-runtime/src/headless.rs`'s `#[cfg(test)]` module,
next to the existing `prog_lamp_frames` assertions at `:419,426`:

```rust
#[test]
fn prog_lamp_frames_split_at_touchdown() {
    let mut s = Summary::default();
    // Engine on.
    s.note(&telemetry_msg(/* t_s */ 1.0, /* frozen */ false, /* touchdown */ None));
    s.note(&dsky_msg_with_prog_lamp(true));
    assert_eq!(s.prog_lamp_frames, 1);
    assert_eq!(s.prog_lamp_frames_post_contact, 0);

    // Ground contact latched.
    s.note(&telemetry_msg(2.0, false, Some("hard")));
    s.note(&dsky_msg_with_prog_lamp(true));
    assert_eq!(
        s.prog_lamp_frames, 1,
        "the pre-contact counter must not move after touchdown"
    );
    assert_eq!(s.prog_lamp_frames_post_contact, 1);
}
```

Reuse whatever helpers the existing tests at `:419,426` already use to
build `ServerMsg` values; if they build them inline, build them inline the
same way rather than inventing `telemetry_msg`/`dsky_msg_with_prog_lamp`.
**Read those tests first.**

- [ ] **Step 2: Run and watch it fail**

```bash
cd runtime && cargo test -p eagle-runtime --lib headless
```
Expected: FAIL — no field `prog_lamp_frames_post_contact`.

- [ ] **Step 3: Implement the split**

In `struct Summary` add `prog_lamp_frames_post_contact: u64`, and in
`Summary::note`'s `DskyState` arm:

```rust
            eagle_schema::ServerMsg::DskyState(d) => {
                // enter_p63 handles pre-ignition alarms (bails on
                // non-whitelisted). Post-engine-on, nobody else watches
                // the lamp — count lit frames here.
                //
                // Split at ground contact: the sim runs ~2 s past
                // touchdown with the AGC still flying a vehicle it has
                // latched as landed, and an alarm raised in that tail
                // says nothing about whether the landing was good. Runs
                // 4/5/6 of the M1 ledger measured exactly that (run 5's
                // 21 frames were ALL post-contact). Both windows are
                // kept — the acceptance gates on the pre-contact count,
                // and the post-contact count stays visible because it is
                // the only evidence this project has that the alarm
                // exists at all.
                if self.engine_on_t.is_some() && d.lamps.get("prog").copied().unwrap_or(false) {
                    if self.touchdown_t.is_some() {
                        self.prog_lamp_frames_post_contact += 1;
                    } else {
                        self.prog_lamp_frames += 1;
                    }
                }
            }
```

Add the field to `HeadlessResult` (doc-comment it as post-contact) and to
the construction at `:272`.

- [ ] **Step 4: Run to green**

```bash
cd runtime && cargo test -p eagle-runtime --lib headless
```

- [ ] **Step 5: Surface both counters**

In `runtime/apps/eagle-runtime/src/scenario_mode.rs:72` and the two live
tests' `[accept]` prints, print both, e.g.
`prog lamp frames: {} pre-contact, {} post-contact`.

- [ ] **Step 6: Retarget the acceptance gate**

In `runtime/apps/eagle-runtime/tests/live_pdi_descent.rs:249`, keep
`assert_eq!(result.prog_lamp_frames, 0, ...)` — the field is now
pre-contact only, so the assertion is unchanged in text and correct in
meaning. Update its message and the file-header note at `:26` to say what
window it covers and that the post-contact count is reported, not gated.
Do the same at `live_p66_descent.rs:174`.

**Do not add an assertion on the post-contact counter.** Its expected value
is unknown; asserting anything about it would be inventing a threshold.

- [ ] **Step 7: Fast gate and commit**

```bash
cd /home/kazumasa/projects/eagle && make test && make lint
git add runtime/apps/eagle-runtime/src/headless.rs runtime/apps/eagle-runtime/src/scenario_mode.rs runtime/apps/eagle-runtime/tests/live_pdi_descent.rs runtime/apps/eagle-runtime/tests/live_p66_descent.rs
git commit -m "fix(runtime): split prog_lamp_frames at ground contact; the gate was a known false negative"
```

---

## Task 5: Fly it

**Files:**
- Create: `docs/superpowers/notes/2026-07-31-m1b-rod-loop.md`
- Modify: `eagle/CLAUDE.md`, `eagle/README.md`,
  `docs/superpowers/notes/2026-07-26-m1-pdi-flight.md`

- [ ] **Step 1: Check the AGC artifacts are built**

```bash
cd /home/kazumasa/projects/eagle && ls build/agc/Luminary099.bin build/agc/Luminary099.log 2>&1
```
If missing: `make agc` (fetches vendor, assembles, verifies hashes).

- [ ] **Step 2: Fly**

```bash
cd /home/kazumasa/projects/eagle && \
EAGLE_TELEM_OUT=build/traces/telem-m1-run7.jsonl \
EAGLE_ATT_DEBUG=build/traces/att-m1-run7.log \
make descent-full 2>&1 | tee build/traces/m1-run7.out
```

~20 minutes wall clock (boot ~5.7 min, ENGINE ON at t ≈ 344 s, MM64 at
TIG+489 s, handover at TIG+647 s). It prints the `[accept]` diagnostics
block itself.

- [ ] **Step 3: Fit the new run**

```bash
cd runtime && cargo run --release -p eagle-runtime --bin rod_fit -- \
  ../build/traces/telem-m1-run7.jsonl
```

This closes the loop on Task 1: the fitted τ should now be ≈1.5 s. **If it
is still ≈0.19 s, the pad-load change did not reach the AGC** — check that
the run used the regenerated pad load — and the flight is void, not a
disproof.

- [ ] **Step 4: Write the change note**

`docs/superpowers/notes/2026-07-31-m1b-rod-loop.md`, following the M1
ledger's format: what was measured before, what the derivation says, what
changed, what flight 7 did. Sections:

- **Headline** — one paragraph, and it must state the outcome plainly. If
  it still crashes, say it crashes.
- **The measurement** — Task 1's stdout for runs 4/5/6, verbatim.
- **The derivation** — the b=11 chain with its citations.
- **Flight 7** — a row in the ledger's run-table format (build, ENGINE ON,
  MM seen, outcome, v_vert, v_horiz, tilt, descent), plus the `[accept]`
  block verbatim, plus the re-fitted τ.
- **What is still open** — ledger items 1a, 2, 3, 4 carry forward
  regardless; add anything flight 7 turned up.

- [ ] **Step 5: Update the status blocks — honestly**

`eagle/CLAUDE.md:52-70` and `eagle/README.md:26-65` both currently say
"Touchdown is still a crash: P66's rate loop limit-cycles". Update to what
flight 7 measured. Three cases:

- **Soft landing, acceptance passes.** Then and only then may the docs say
  M1 lands — and the sentence must name the test that measured it. Run the
  frozen acceptance for real:
  `cargo test -p eagle-runtime --test live_pdi_descent -- --ignored --test-threads=1`
- **Better but still a crash.** Say so, with the numbers, and say which
  blocker is now on top. Do not describe the loop as "fixed".
- **No change.** Say the correction was right and insufficient, and move
  `DPS_MIN_N` (`eagle/CLAUDE.md:61-67`) to the top of the suspect list.

Also append a `## 2026-07-31 update` to
`docs/superpowers/notes/2026-07-26-m1-pdi-flight.md`'s "Open" section
recording that item 1 was closed (or not) and pointing at the new note.
**Do not rewrite the M1 ledger's history** — its numbers are the record of
what six flights measured.

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/notes/ CLAUDE.md README.md
git commit -m "docs(eagle): flight 7 — the corrected TAUROD, measured"
```

---

## Self-Review

**Spec coverage.** The plan's "spec" is the M1 ledger's open-item list.
Item 1 (P66 rate loop) → Tasks 1-3, 5. Item 2a (`prog_lamp_frames` false
negative) → Task 4. Items 1a, 2, 3, 4 are explicitly declared out of scope
above, with reasons. Nothing in the ledger's list is silently dropped.

**Placeholder scan.** Every code step carries the code. The three places
that legitimately cannot be pre-written are the *measured outputs* (Task 1
Step 5, Task 3 Step 5, Task 5 Steps 2-3) — and each of those specifies the
exact command, the artefact it writes, and the decision rule applied to the
result *before* it is seen. Task 2 Step 7 and Task 4 Step 1 direct the
implementer to read existing code first rather than guessing its shape;
both name the file and line range.

**Type consistency.** `Sample`/`Fit`/`fit_tau` (Task 1) are used only
inside `rod_fit.rs`. `RodLoopCfg`/`RodLoopResult`/`simulate` (Task 3) are
used only by their own tests. `prog_lamp_frames_post_contact` (Task 4) is
added in `Summary`, mirrored in `HeadlessResult`, and read in three call
sites, all enumerated. `TAUROD_B_SCALE` and siblings (Task 2) are consumed
only by Task 2's own test.

**Kill criteria.** Task 1 Step 5 can stop the whole plan, and says so.
Task 3 Step 4 and Task 5 Step 3 each name a failure mode that must be
reported rather than tuned around.
