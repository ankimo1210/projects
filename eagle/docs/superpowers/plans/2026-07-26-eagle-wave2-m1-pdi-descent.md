# EAGLE Wave 2 M1 — Truth at PDI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The real Luminary099 flies P63 braking → P64 approach → P66 landing
from the PDI point on pure inertial navigation (landing radar bypassed
in-rope), with sim truth and AGC nav agreeing by construction.

**Architecture:** No new crates. The pad-load generator (`padload.rs`)
becomes the single source of the initial state: a new `pdi_truth_state`
shares the ignition-point geometry `generate_state` already computes. The
scenario schema gains a `mode = "pdi"` gate, a `[handover]` altitude and an
`lrbypass` marker. `SimCore` keeps the freeze-until-ENGINE-ON mechanism
(it is what makes the AGC's clock-rate offset harmless) but in PDI mode the
frozen truth IS the ignition point and the freeze-phase PIPA feed is zero
(coast), not hover support. P64→P66 handover is sim-driven: `SimCore` arms
on MM64, fires on an altitude crossing, and the headless loop performs
ATT HOLD + the selection ROD click.

**Tech Stack:** Rust (tokio in eagle-runtime, std sim thread), serde/toml,
yaAGC socket protocol, existing DSKY script harness.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-26-eagle-wave2-real-descent-design.md`
  (§3 M1). Wave 1 conventions carry over verbatim:
- `vendor/` is READ-ONLY. Cite vendor paths+lines when semantics are taken
  from them.
- All AGC channel numbers and erasable addresses octal (`0o…` in Rust).
- Integration tests serial (`--ignored --test-threads=1`). New live test
  uses AGC port **19905** (Wave 1 used up to 19904).
- Physics: RK4, fixed 10 ms, fixed evaluation order. SI units everywhere
  except the counter codec. Errors OFF for acceptance.
- Scenario values carry provenance comments: `historical` / `derived` /
  `assumed` / `measured`.
- Do not claim a soft landing in any doc until a live run measured it
  (CLAUDE.md rule from Wave 1).
- Hover mode must stay bit-identical: every existing test keeps passing
  unchanged.
- Fast gate after every task: `make test && make lint`.
- Work on branch `eagle/wave2-m1` cut from `main`. Never stage outside
  `eagle/`.
- Commit after every green test cycle. Commit messages end with:
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` and
  `Claude-Session: https://claude.ai/code/session_01WeYXpPxWfLXR3DG73gPmKc`

## Verified vendor facts (checked while planning — implementers re-verify in Step 0 of the task that uses them)

| Fact | Source |
|---|---|
| `FLGWRD11 = STATE +11D`, ECADR **`0o107`** | `build/agc/Luminary099.log:3262` (`26,2022 0107 FLGWRD11 = STATE +11D`) |
| `LRBYPASS` = FLAGWRD11 **BIT 15** (`0o40000`): "BYPASS ALL LANDING RADAR UPDATES" | `FLAGWORD_ASSIGNMENTS.agc:1051-1052` |
| **Fresh start SETS LRBYPASS** — `SWINIT`'s FLGWRD11 word is `OCT 40000  # BIT 15 = LRBYPASS.` | `FRESH_START_AND_RESTART.agc:614` |
| Ullage fires at **TIG−7.5 s** (DPS) | `BURN_BABY_BURN--MASTER_IGNITION_ROUTINE.agc:347` (`ULLGTASK … THIS COMES AT TIG-7.5 OR TIG-3.5`) |
| GUILDENSTERN's P66 switch checks only "already MM66?" + ATT-HOLD + RODCOUNT ≠ 0 — it does not require MM63, so it works from P64 | `LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:194-217` (`STABL?`/`P66NOW?`) |
| N64 is a `FUNNYDSP` (mixed-format) noun — its register layout is NOT the simple HDOTDISP R2 of N60/N63. Do not extend `parse_agc_nav` to N64 without reading the FUNNYDSP decode first | `PINBALL_NOUN_TABLES.agc:726` |
| Wave 1 measured: the DAP recovers a ~125° attitude error in ~13 s after release, and Luminary throttles up at `FLATOUT` = TIG+26 s — so an attitude slew commanded against frozen truth resolves before throttle-up | re-flight note + `docs/superpowers/notes/2026-07-25-wave1-reflight.md` |

**Design consequence (release trigger):** the ignition-attitude maneuver
(IGNALG, ~TIG−276 s) fires RCS jets long before ullage, so "first jet
command" cannot distinguish ullage. The freeze therefore releases on
**ENGINE ON (ch 011 bit 13), exactly as in Wave 1**, with frozen truth = the
ignition point itself. At that moment the AGC's nav — which integrated the
same pad-loaded orbit to TIG — is at the same point by construction. Ullage
Δv (~0.9 m/s) is consistently absent from both sides (frozen truth moves
nothing; zero PIPA feed means nav sees nothing). No ullage-lead constant is
needed.

**LRBYPASS consequence:** M1 does not SET the flag — fresh start already
does. `lrbypass = true` in the scenario means "verify the flag is set after
init and abort if not" (a regression guard; M3 will *clear* it).

## File structure

| File | Change |
|---|---|
| `runtime/apps/eagle-runtime/src/padload.rs` | `IgnitionGeometry`, `ignition_geometry()`, `PdiMasses`, `pdi_truth_state()` (Task 1) |
| `runtime/apps/eagle-runtime/src/scenario.rs` | `GateMode`, `[handover]`, `agc.lrbypass`, PDI branch in `initial_state` (Task 2) |
| `scenarios/pdi-descent.toml` | new scenario (Task 2, tuned in Task 5) |
| `runtime/apps/eagle-runtime/src/sim.rs` | PDI freeze semantics, handover arm/fire, `SimEvent` (Task 3) |
| `runtime/apps/eagle-runtime/src/headless.rs` | `SimEvent` loop, handover action (Task 4) |
| `runtime/apps/eagle-runtime/src/runner.rs` | `FLGWRD11_ECADR`, `LRBYBIT`, verify-flag step, PDI choreography branch (Task 4) |
| `runtime/apps/eagle-runtime/tests/live_pdi_descent.rs` | frozen acceptance (Task 6) |
| `Makefile` | `descent-full` target (Task 5) |
| `docs/agc-channel-map.md`, `CLAUDE.md`, `README.md`, ledger note | docs (Tasks 5, 6) |

---

### Task 1: Single-source ignition geometry + PDI truth state

**Files:**
- Modify: `runtime/apps/eagle-runtime/src/padload.rs` (around `generate_state`, line ~741)

**Interfaces:**
- Consumes: `StateCfg` (exists), `eagle_dynamics::{state::LmState, state::gravity, rk4::step_rk4, frames::{Rot, V3, Mci, Body}, constants::{R_SITE, OMEGA_MOON, DT}}`.
- Produces:
  - `pub struct IgnitionGeometry { pub theta_rad: f64, pub r_orb_m: f64, pub v_inertial_ms: f64 }`
  - `pub fn ignition_geometry(cfg: &StateCfg) -> IgnitionGeometry`
  - `pub struct PdiMasses { pub dry_kg: f64, pub dps_kg: f64, pub rcs_kg: f64 }`
  - `pub fn pdi_truth_state(cfg: &StateCfg, m: &PdiMasses, epoch_s: f64) -> LmState`

- [ ] **Step 1: Write failing tests** in `padload.rs` `#[cfg(test)]`:

```rust
#[test]
fn ignition_geometry_matches_the_lum69r2_pdi_point() {
    let g = ignition_geometry(&StateCfg::default());
    // Values the generate_state comment block already documents:
    // θ ≈ 0.2539 rad, r ≈ 1752.6 km (h ≈ 15.2 km), v = VIGN + ω·r.
    assert!((g.theta_rad - 0.2539).abs() < 1e-3, "theta {}", g.theta_rad);
    assert!((g.r_orb_m - 1_752_600.0).abs() < 1_000.0, "r {}", g.r_orb_m);
    let expect_v = 1699.52182 + eagle_dynamics::constants::OMEGA_MOON * g.r_orb_m;
    assert!((g.v_inertial_ms - expect_v).abs() < 1e-6, "v {}", g.v_inertial_ms);
}

#[test]
fn generate_state_and_truth_state_share_the_geometry() {
    // The single-source property: the RN/VN words and the truth state must
    // come from the same θ/r/v. generate_state's own scaling test pins the
    // words; here we pin the truth state against ignition_geometry.
    let cfg = StateCfg::default();
    let g = ignition_geometry(&cfg);
    let m = PdiMasses { dry_kg: 7009.0, dps_kg: 7950.0, rcs_kg: 250.0 };
    let st = pdi_truth_state(&cfg, &m, 0.0);
    let (s, c) = g.theta_rad.sin_cos();
    let expect_pos = V3::<Mci>::new(g.r_orb_m * c, -g.r_orb_m * s, 0.0);
    assert!((st.pos - expect_pos).norm() < 1e-6, "pos {:?}", st.pos);
    let expect_vel = V3::<Mci>::new(g.v_inertial_ms * s, g.v_inertial_ms * c, 0.0);
    assert!((st.vel - expect_vel).norm() < 1e-6, "vel {:?}", st.vel);
    assert!((st.mass_kg - (7009.0 + 7950.0 + 250.0)).abs() < 1e-9);
    assert_eq!(st.fuel_dps_kg, 7950.0);
    assert_eq!(st.t, 0.0);
}

#[test]
fn pdi_truth_attitude_is_the_padloaded_refsmmat_frame() {
    // generate_state pad-loads REFSMMAT rows: SM X=(1,0,0), Y=(0,0,-1),
    // Z=(0,1,0) in MCI. sim::sm_from_initial defines SM ≡ initial BODY
    // attitude, so the truth's initial body axes must BE that frame — this
    // is what makes the REFSMMAT claim true instead of approximately true.
    let cfg = StateCfg::default();
    let m = PdiMasses { dry_kg: 7009.0, dps_kg: 7950.0, rcs_kg: 250.0 };
    let st = pdi_truth_state(&cfg, &m, 0.0);
    let bx = st.att.apply(V3::<Body>::new(1.0, 0.0, 0.0));
    let by = st.att.apply(V3::<Body>::new(0.0, 1.0, 0.0));
    let bz = st.att.apply(V3::<Body>::new(0.0, 0.0, 1.0));
    assert!((bx - V3::<Mci>::new(1.0, 0.0, 0.0)).norm() < 1e-12);
    assert!((by - V3::<Mci>::new(0.0, 0.0, -1.0)).norm() < 1e-12);
    assert!((bz - V3::<Mci>::new(0.0, 1.0, 0.0)).norm() < 1e-12);
    assert_eq!(st.omega, V3::<Body>::zero());
}
```

- [ ] **Step 2: Run, verify FAIL** — `cd runtime && cargo test -p eagle-runtime padload::` → compile errors (types missing).

- [ ] **Step 3: Implement.**

Extract the geometry block that `generate_state` computes inline
(padload.rs ~750-768) into:

```rust
/// The ignition-point geometry both the AGC pad-load AND the sim truth
/// derive from. Single source: cause C of the Wave 1 RED acceptance was
/// these two describing different vehicles (re-flight note 2026-07-25).
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct IgnitionGeometry {
    /// Uprange angle from the site radial, rad.
    pub theta_rad: f64,
    /// Orbit radius at ignition, m.
    pub r_orb_m: f64,
    /// INERTIAL speed at ignition, m/s: VIGN (surface-relative, the
    /// quantity IGNALG compares against |VGU|) plus the eastward
    /// co-rotation ω·r (see generate_state's VGU citation).
    pub v_inertial_ms: f64,
}

pub fn ignition_geometry(cfg: &StateCfg) -> IgnitionGeometry {
    let a = R_SITE + cfg.rign_x_m;
    let b = -cfg.rign_z_m; // rign_z < 0 => LM is uprange (short of site)
    let theta_rad = b.atan2(a);
    let r_orb_m = a.hypot(b);
    let v_inertial_ms = cfg.v_ign_ms + eagle_dynamics::constants::OMEGA_MOON * r_orb_m;
    IgnitionGeometry { theta_rad, r_orb_m, v_inertial_ms }
}
```

and make `generate_state` call it (delete the now-duplicated inline lines;
its `r_lm`/`v_lm` math consumes `g.theta_rad`/`g.r_orb_m`/
`g.v_inertial_ms / 100.0`). The existing
`generate_state_geometry_and_scaling` test must still pass — that is the
proof the refactor preserved the words.

```rust
/// Mass properties for the PDI truth state (scenario-supplied).
#[derive(Debug, Clone, Copy)]
pub struct PdiMasses {
    pub dry_kg: f64,
    pub dps_kg: f64,
    pub rcs_kg: f64,
}

/// Sim truth at the PDI ignition point, in the pad-load's MCI frame
/// (site radial = +X at TLAND, orbit plane = XY, motion +Y eastward).
/// The freeze releases on ENGINE ON ≈ TIG-0, at which moment the AGC's
/// own nav — integrating the SAME pad-loaded orbit — arrives at this
/// point by construction (design doc §3 M1; release-trigger note in the
/// M1 plan header). Attitude = the pad-loaded REFSMMAT frame exactly
/// (body X→MCI x̂, Y→−ẑ, Z→ŷ = Rx(−90°)), so SM ≡ initial body attitude
/// makes the REFSMMAT claim true and the CDUs correctly read zero.
pub fn pdi_truth_state(cfg: &StateCfg, m: &PdiMasses, epoch_s: f64) -> LmState {
    let g = ignition_geometry(cfg);
    let (s, c) = g.theta_rad.sin_cos();
    let att: Rot<Body, Mci> = eagle_dynamics::frames::retag(Rot::from_axis_angle(
        V3::<Mci>::new(1.0, 0.0, 0.0),
        -std::f64::consts::FRAC_PI_2,
    ));
    LmState {
        t: epoch_s,
        pos: V3::new(g.r_orb_m * c, -g.r_orb_m * s, 0.0),
        vel: V3::new(g.v_inertial_ms * s, g.v_inertial_ms * c, 0.0),
        att,
        omega: V3::zero(),
        mass_kg: m.dry_kg + m.dps_kg + m.rcs_kg,
        fuel_dps_kg: m.dps_kg,
        fuel_rcs_kg: m.rcs_kg,
    }
}
```

(Adjust the `Rot`/`retag` construction to the real frames.rs API — the
axis-angle-then-retag pattern is exactly what `scenario::body_x_to` uses.)

- [ ] **Step 4: Run, verify PASS** — `cargo test -p eagle-runtime padload::` and the full `cargo test`.

- [ ] **Step 5: Commit** — `git commit -m "feat(runtime): single-source ignition geometry + PDI truth state"` (+ trailers).

---

### Task 2: Scenario schema — PDI mode, handover, lrbypass + `pdi-descent.toml`

**Files:**
- Modify: `runtime/apps/eagle-runtime/src/scenario.rs`
- Create: `scenarios/pdi-descent.toml`

**Interfaces:**
- Consumes: `padload::{pdi_truth_state, PdiMasses, StateCfg}` (Task 1).
- Produces:
  - `pub enum GateMode { Hover, Pdi }` (serde lowercase; `Gate.mode: GateMode` with `#[serde(default)]` → `Hover`)
  - `pub struct Handover { pub alt_m: f64 }`; `Scenario.handover: Option<Handover>` (`#[serde(default)]`)
  - `Agc.lrbypass: bool` (`#[serde(default)]` → false)
  - `Scenario::initial_state` returns the PDI state when `mode = "pdi"`.

- [ ] **Step 1: Write failing tests** in `scenario.rs` tests:

```rust
#[test]
fn loads_pdi_descent_scenario() {
    let s = Scenario::load(&repo().join("scenarios/pdi-descent.toml")).unwrap();
    assert!(matches!(s.gate.mode, GateMode::Pdi));
    assert!(s.agc.lrbypass);
    assert!((s.handover.as_ref().unwrap().alt_m - 150.0).abs() < 1e-9);
    let st = s.initial_state(0.0);
    // PDI point: h ≈ 15.2 km, inertial speed ≈ 1704 m/s, attitude = REFSMMAT frame.
    let alt = st.pos.norm() - s.site.radius_m;
    assert!((14_000.0..16_000.0).contains(&alt), "alt {alt}");
    assert!((st.vel.norm() - 1704.0).abs() < 5.0, "v {}", st.vel.norm());
    let bx = st.att.apply(V3::<Body>::new(1.0, 0.0, 0.0));
    assert!((bx - V3::<Mci>::new(1.0, 0.0, 0.0)).norm() < 1e-9);
}

#[test]
fn hover_scenarios_do_not_need_the_new_fields() {
    // Back-compat: the committed Wave 1 files carry no mode/handover/lrbypass.
    let s = Scenario::load(&repo().join("scenarios/p66-gate.toml")).unwrap();
    assert!(matches!(s.gate.mode, GateMode::Hover));
    assert!(s.handover.is_none());
    assert!(!s.agc.lrbypass);
}
```

- [ ] **Step 2: Run, verify FAIL** — types/fields/file missing.

- [ ] **Step 3: Implement.** Schema additions (all `deny_unknown_fields`-safe
because they are new named fields with defaults):

```rust
#[derive(Debug, Clone, Copy, Default, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum GateMode {
    #[default]
    Hover,
    Pdi,
}
// Gate gains:  #[serde(default)] pub mode: GateMode,
// Agc gains:   #[serde(default)] pub lrbypass: bool,
// Scenario gains:  #[serde(default)] pub handover: Option<Handover>,

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Handover {
    /// Altitude (m AGL) at which, once MM64 has been observed, the sim
    /// commands ATT HOLD + the selection ROD click into P66. historical:
    /// the crew took over near 500 ft.
    pub alt_m: f64,
}
```

`initial_state` branches:

```rust
pub fn initial_state(&self, epoch_s: f64) -> LmState {
    match self.gate.mode {
        GateMode::Hover => self.hover_initial_state(epoch_s), // existing body, renamed
        GateMode::Pdi => crate::padload::pdi_truth_state(
            &crate::padload::StateCfg::default(),
            &crate::padload::PdiMasses {
                dry_kg: self.gate.mass_dry_kg,
                dps_kg: self.gate.fuel_dps_kg,
                rcs_kg: self.gate.fuel_rcs_kg,
            },
            epoch_s,
        ),
    }
}
```

`scenarios/pdi-descent.toml`:

```toml
schema = 1
name = "pdi-descent"
# Wave 2 M1: the real descent. Truth starts AT the pad-loaded PDI ignition
# point (padload::pdi_truth_state — single source with generate_state), in
# the pad-load's MCI frame: site radial = +X at TLAND, orbit plane = XY.
# [site] lat/lon are therefore NOT used for geometry in pdi mode; the site
# is MCI +X. miss_m carries a documented few-km frame/time-base caveat
# until measured (M1 plan Task 5).

[site]
lat_deg = 0.0            # unused in pdi mode (site ≡ MCI +X at TLAND)
lon_deg = 0.0            # unused in pdi mode
radius_m = 1737400.0     # assumed (mean lunar radius; same as p66-gate)

[gate]
mode = "pdi"
alt_m = 0.0              # unused in pdi mode (state comes from StateCfg)
vz_ms = 0.0              # unused in pdi mode
mass_dry_kg = 7009.0     # derived: descent dry 2339 + ascent stage wet 4670 (Wave 1)
fuel_dps_kg = 7950.0     # derived: LM-5 total at PDI ≈ 15.2 t minus dry+RCS
fuel_rcs_kg = 250.0      # derived: ~287 kg loaded minus separation/DOI usage
inertia_kgm2 = [23000.0, 25000.0, 24000.0]  # assumed (full LM order-of-magnitude; M1 measures)

[agc]
padload = "scenarios/p66-padload.toml"
lm_weight_lbs = 33530.0            # derived: (7009+7950+250) kg = 15209 kg → V48/N47
tland_offset_cs = 36000            # derived: proven burn lead from Wave 1 acceptance
flip_atthold_after_engine_on_s = 2.0   # unused in pdi mode (handover is sim-driven)
lrbypass = true                    # verify-only: fresh start already sets FLAGWRD11 bit15
                                   # (FRESH_START_AND_RESTART.agc:614); abort if missing

[handover]
alt_m = 150.0            # historical: crew takeover near 500 ft during P64

[rod]
steps = []               # set from Task 5's measured P66-entry sink rate — do not guess

[errors]                 # empty = all OFF (acceptance runs use this)

[acceptance]             # placeholders = Wave 1 values; Task 5 re-measures
v_vert_max = 3.0
v_horiz_max = 1.5
tilt_max_deg = 12.0
timeout_s = 800.0        # from ENGINE ON; P63 burn ~510 s + P64 + P66 + margin
```

- [ ] **Step 4: Run, verify PASS** — `cargo test -p eagle-runtime scenario::` then full `make test && make lint`.

- [ ] **Step 5: Commit** — `git commit -m "feat(runtime): PDI gate mode, handover altitude, lrbypass marker + pdi-descent scenario"` (+ trailers).

---

### Task 3: SimCore PDI semantics — coast freeze, handover, `SimEvent`

**Files:**
- Modify: `runtime/apps/eagle-runtime/src/sim.rs`

**Interfaces:**
- Consumes: `Scenario.gate.mode`, `Scenario.handover` (Task 2).
- Produces:
  - `pub enum SimEvent { RodClicks(i32), Handover }` — replaces the bare
    `i32` on the sim→headless channel. `spawn_sim`'s parameter becomes
    `event_tx: tokio::sync::mpsc::UnboundedSender<SimEvent>`.
  - `SimTickOut` gains `pub handover: bool`.
  - PDI freeze: `sf_body = 0` while frozen (coast), release on ENGINE ON
    (mechanism unchanged).

- [ ] **Step 1: Write failing tests** in `sim.rs` tests:

```rust
fn pdi_scenario() -> Scenario {
    Scenario::load(
        &PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../../scenarios/pdi-descent.toml"),
    )
    .unwrap()
}

#[test]
fn pdi_freeze_feeds_zero_pipa_and_releases_on_engine_on() {
    let sc = pdi_scenario();
    let mut core = SimCore::new(&sc, 0.0);
    let pos0 = core.st.pos;
    let mut pipa_packets = 0usize;
    for _ in 0..200 {
        let out = core.tick();
        pipa_packets += out.to_agc.iter().filter(|p| is_pipa(p)).count();
    }
    assert_eq!(core.st.pos, pos0, "frozen state must not move");
    assert_eq!(pipa_packets, 0, "coast freeze must feed ZERO specific force");
    engine_on(&mut core);
    for _ in 0..100 {
        core.tick();
    }
    assert_ne!(core.st.pos, pos0, "dynamics must run after ENGINE ON");
}

#[test]
fn hover_freeze_still_feeds_hover_support() {
    // Regression guard: hover mode is bit-identical to Wave 1.
    let sc = scenario(); // the existing p66-gate helper
    let mut core = SimCore::new(&sc, 0.0);
    let mut pipa = 0usize;
    for _ in 0..200 {
        pipa += core.tick().to_agc.iter().filter(|p| is_pipa(p)).count();
    }
    assert!(pipa > 0, "hover freeze feeds 1.62 m/s^2 support");
}

#[test]
fn handover_arms_on_mm64_and_fires_once_below_altitude() {
    let sc = pdi_scenario();
    let mut core = SimCore::new(&sc, 0.0);
    engine_on(&mut core);
    // Below the handover altitude but MM is still 63: must NOT fire.
    core.st.pos = core.st.pos.unit().scale(sc.site.radius_m + 100.0);
    core.ingest(SimIn::Dsky(DskyStateSnapshot { mm: "63".into(), nav: None }));
    assert!(!core.tick().handover, "not armed before MM64");
    // MM64 appears while below threshold: fires exactly once.
    core.ingest(SimIn::Dsky(DskyStateSnapshot { mm: "64".into(), nav: None }));
    assert!(core.tick().handover, "armed + below altitude => fire");
    assert!(!core.tick().handover, "fires once");
}

#[test]
fn handover_never_fires_in_hover_mode() {
    let sc = scenario();
    let mut core = SimCore::new(&sc, 0.0);
    engine_on(&mut core);
    core.st.pos = core.st.pos.unit().scale(sc.site.radius_m + 10.0);
    core.ingest(SimIn::Dsky(DskyStateSnapshot { mm: "64".into(), nav: None }));
    assert!(!core.tick().handover);
}
```

- [ ] **Step 2: Run, verify FAIL** — `handover` field missing, PDI PIPA test fails on hover-support pulses.

- [ ] **Step 3: Implement.**

`SimCore` gains fields set in `new` from the scenario:

```rust
pdi: bool,                       // gate.mode == Pdi
handover_alt_m: Option<f64>,     // scenario.handover (None in hover mode)
handover_armed: bool,
handover_fired: bool,
```

Freeze branch (`phase4_5_dynamics`): when `self.pdi`, the frozen
`sf_body` is `V3::zero()` (free coast — nav and truth agree that nothing
accelerates; the hover branch keeps `HOVER_ACCEL_MS2`). Comment must state
the release-trigger reasoning from the plan header (ENGINE ON ≈ TIG-0;
ignition-attitude jets fire earlier against the frozen attitude, recovered
in ~13 s, before FLATOUT at TIG+26 s — Wave 1 measured).

Handover (new phase step, after `phase8_rod`): arm when `self.mm == "64"`;
fire when armed, not yet fired, and `self.alt_agl() <= handover_alt_m`;
set `out.handover = true` and `self.handover_fired = true`.

`SimEvent`:

```rust
/// Sim → headless events that need the DSKY script or discrete writes.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum SimEvent {
    /// Signed ROD clicks to deliver via RODCOUNT (schedule + handover click
    /// are separate: the handover click is part of Handover).
    RodClicks(i32),
    /// P64→P66 handover: ATT HOLD discrete + the selection ROD click.
    Handover,
}
```

`spawn_sim` sends `SimEvent::RodClicks(out.rod_clicks)` /
`SimEvent::Handover` on the renamed `event_tx`. Update the thread-shell
test accordingly.

- [ ] **Step 4: Run, verify PASS** — `cargo test -p eagle-runtime sim::` then full suite (headless will not compile until Task 4 — do Tasks 3+4 on one branch state if needed, but keep the commits separate; it is acceptable for this task's commit to come after Task 4's compile fix ONLY if the suite cannot be made green here. Preferred: change `spawn_sim`'s signature and `headless.rs`'s call site minimally in this task (type rename only, mapping `SimEvent::RodClicks` to the existing behavior and ignoring `Handover` with a `// Task 4` comment), so `make test` is green at this commit.)

- [ ] **Step 5: Commit** — `git commit -m "feat(runtime): PDI coast freeze, sim-driven P64 handover, SimEvent channel"` (+ trailers).

---

### Task 4: Runner + headless — PDI choreography, LRBYPASS verify, handover action

**Files:**
- Modify: `runtime/apps/eagle-runtime/src/runner.rs`
- Modify: `runtime/apps/eagle-runtime/src/headless.rs`

**Interfaces:**
- Consumes: `SimEvent` (Task 3), `Scenario.gate.mode` / `agc.lrbypass`
  (Task 2), existing `att_hold`, `rod_load`, `set_flag_bits`, the V01N01
  read-back helper `apply_padload` already uses (it exists in runner.rs —
  find it by reading the `apply_padload` verification path; do NOT write a
  new reader).
- Produces:
  - `pub const FLGWRD11_ECADR: u16 = 0o107;` (citation: `Luminary099.log:3262`, `26,2022 0107 FLGWRD11 = STATE +11D`)
  - `pub const LRBYBIT: u16 = 0o40000;` (citation: `FLAGWORD_ASSIGNMENTS.agc:1051-1052`; default-set at fresh start per `FRESH_START_AND_RESTART.agc:614`)
  - `run_scenario` in PDI mode: verifies LRBYPASS after `init_discretes`/`dap_init`, skips the forced ATT-HOLD block, returns after `wait_engine_on`.
  - headless event loop: `RodClicks(n)` → `rod_load`; `Handover` → `att_hold(&cmd_tx)` then `rod_load(script, -1)`.

- [ ] **Step 1: Write failing tests.** Fast-testable pieces only (the
choreography itself is live):

```rust
// runner.rs tests: pin the constants against independent derivations.
#[test]
fn flgwrd11_constants() {
    // STATE = 0o74 (FLAGWRD3 = STATE+3 = 0o77 is already pinned above);
    // STATE + 11D = 0o74 + 11 = 0o107.
    assert_eq!(FLGWRD11_ECADR, 0o74 + 11);
    assert_eq!(LRBYBIT, 1 << 14); // BIT 15 in AGC 1-based numbering
}
```

In `headless.rs` tests, extend the `next_rod_click`-family coverage: rename
the helper to `next_sim_event` (same biased-select semantics, now yielding
`SimEvent`; the client channel still carries `i32` and is wrapped into
`SimEvent::RodClicks` inside the helper):

```rust
#[tokio::test]
async fn handover_event_passes_through_and_sim_close_still_terminates() {
    let (sim_tx, mut sim_rx_holder) = tokio::sync::mpsc::unbounded_channel();
    let mut client: Option<tokio::sync::mpsc::UnboundedReceiver<i32>> = None;
    sim_tx.send(SimEvent::Handover).unwrap();
    assert_eq!(
        next_sim_event(&mut sim_rx_holder, &mut client).await,
        Some(SimEvent::Handover)
    );
    drop(sim_tx);
    assert_eq!(next_sim_event(&mut sim_rx_holder, &mut client).await, None);
}
```

- [ ] **Step 2: Run, verify FAIL.**

- [ ] **Step 3: Implement.**

`runner.rs`:
- Add the two constants with citations (Step 0: re-verify both against
  `build/agc/Luminary099.log` and the vendor files before locking).
- After `dap_init` in `run_scenario`, when `sc.agc.lrbypass`: read
  `FLGWRD11_ECADR` with the existing V01N01 read-back helper and
  `ensure!(word & LRBYBIT != 0, "LRBYPASS not set after fresh start — radar-bypass precondition broken")`.
- Branch the tail on mode: `GateMode::Pdi` returns
  `Ok(ScenarioReport { alarms: episodes })` right after
  `wait_engine_on(...)`; the hover path keeps the existing forced
  `att_hold` + `rod_load(-1)` + `wait_prog("66")` block untouched.

`headless.rs` event loop (replacing the Task-3 shim):

```rust
while let Some(ev) = next_sim_event(&mut event_rx, &mut client_rod_rx).await {
    script_busy.store(true, Ordering::SeqCst);
    let r = match ev {
        SimEvent::RodClicks(n) => runner::rod_load(&mut script, n as i16).await,
        SimEvent::Handover => {
            // ATT HOLD flips GUILDENSTERN's mode check; the selection
            // click gives it a nonzero RODCOUNT (LLGE:194-217).
            match runner::att_hold(&cmd_tx).await {
                Ok(()) => runner::rod_load(&mut script, -1).await,
                Err(e) => Err(e),
            }
        }
    };
    script_busy.store(false, Ordering::SeqCst);
    if let Err(e) = r {
        eprintln!("headless: sim event failed: {e:#}");
    }
}
```

- [ ] **Step 4: Run, verify PASS** — full `make test && make lint`; also
`cargo test -p eagle-runtime --test live_p66_descent --no-run` and
`--test live_spike_p66 --no-run` (hover path must still compile and its
behavior is untouched).

- [ ] **Step 5: Commit** — `git commit -m "feat(runtime): PDI choreography branch, LRBYPASS verify, handover action"` (+ trailers).

---

### Task 5: Live flight — fly it, measure, tune (M1 flagship; live spike discipline)

**Files:**
- Modify: `Makefile` (add `descent-full`)
- Modify: `scenarios/pdi-descent.toml` (rod steps, acceptance values — measured)
- Create: `docs/superpowers/notes/2026-07-XX-m1-pdi-flight.md` (ledger)
- Modify: `docs/agc-channel-map.md` (FLGWRD11/LRBYPASS rows + citations)

**Interfaces:**
- Consumes: everything above; `build/agc` artifacts; `EAGLE_ATT_DEBUG`, `EAGLE_TELEM_OUT`.
- Produces: measured numbers later tasks assert on. **Numeric findings are
  recorded, not guessed** (Wave 1 spike rule).

- [ ] **Step 1: Makefile target.**

```make
# Wave 2 M1: the real descent — PDI → P63 → P64 → P66, radar bypassed.
# ~18-19 min wall (boot ~6 min + P63 burn ~8.5 min + P64/P66; AGC clock
# runs ~95.2% of real time on this host). Not in CI.
descent-full: agc
	cd runtime && cargo run -p eagle-runtime -- \
	  --yaagc ../build/agc/yaAGC --core ../build/agc/Luminary099.bin \
	  --scenario ../scenarios/pdi-descent.toml --root ..
```

(add to `.PHONY`.)

- [ ] **Step 2: First instrumented flight.**

```bash
cd runtime
EAGLE_ATT_DEBUG=../build/traces/att-m1-run1.log \
EAGLE_TELEM_OUT=../build/traces/telem-m1-run1.jsonl \
  cargo run -p eagle-runtime -- --yaagc ../build/agc/yaAGC \
  --core ../build/agc/Luminary099.bin \
  --scenario ../scenarios/pdi-descent.toml --root .. \
  2>&1 | tee ../build/traces/m1-run1.out
```

Record in the ledger note, per run: MM transition times (63/64/66 and any
65), ENGINE ON time, alt/vz at MM64 entry, alt/vz at handover fire, P66
entry sink rate (this sets the ROD schedule), touchdown report (class,
v_vert, v_horiz, tilt, miss_m), alarm episodes, `[accept] AGC clock` /
pacing lines, fuel remaining. Also record what P64 actually displays
(V06N64 register contents vs the DSKY log) — N64 is FUNNYDSP; do NOT
extend `parse_agc_nav` unless the recorded data plus
`PINBALL_NOUN_TABLES.agc` decode confirm R2 = HDOTDISP.

- [ ] **Step 3: Diagnose and iterate.** Expected first-flight risk points, in
order: (a) IGNALG rejects or slips TIG (FAILREG 01703/00404/01301 — same
alarm vocabulary as Wave 1 spike A); (b) P63 guidance diverges — check
`nav_err_hdot_ms` (now measurable via N63) and the attitude trace;
(c) MM64 never appears (HIGATE not reached — check DELTAH/alt profile);
(d) handover fires but P66 entry rate is too hot for a no-click landing.
Fix loop per the global rule: after 3 failed fix attempts on any one
blocker, STOP and write up. Hard budget for the task: **6 flights** (~2 h
wall) — if not stable by then, stop and summarize regardless.

- [ ] **Step 4: Tune the scenario from measurements.** Set `[rod] steps`
(breakpoints below the measured handover-entry altitude/rate),
`[acceptance]` values and `timeout_s` from the successful profile, each
with `measured:` provenance comments naming the run. Update
`docs/agc-channel-map.md` with the FLGWRD11/LRBYPASS rows (octal, cited).

- [ ] **Step 5: Repeat until one full nominal-profile flight completes** (not
yet the frozen 2×-consecutive bar — that is Task 6's).

- [ ] **Step 6: Commit** — code/scenario/docs + ledger note:
`git commit -m "feat(runtime): M1 PDI descent flies live; measured rod schedule + acceptance values"` (+ trailers).

---

### Task 6: Frozen acceptance test + docs truth pass

**Files:**
- Create: `runtime/apps/eagle-runtime/tests/live_pdi_descent.rs` (port 19905)
- Modify: `CLAUDE.md`, `README.md`
- Modify: `docs/superpowers/specs/2026-07-26-eagle-wave2-real-descent-design.md` (M1 status note)

**Interfaces:**
- Consumes: measured values from Task 5; `run_headless`, `HeadlessResult`
  (alarms, prog_lamp_frames, drift/final_t_s, mm_sequence), `TouchdownReport`.

- [ ] **Step 1: Write the test** (pattern: `live_p66_descent.rs`, updated):

```rust
//! Wave 2 M1 acceptance: the real Luminary099 flies PDI → P63 → P64 → P66
//! to touchdown against our physics, landing radar bypassed in-rope
//! (LRBYPASS, fresh-start default), errors OFF. ~18-19 min wall.
//! Run: cargo test -p eagle-runtime --test live_pdi_descent -- --ignored --test-threads=1
use eagle_runtime::agc_session::{AgcConfig, AgcSession};
use eagle_runtime::headless::{run_headless, HeadlessCfg};
use eagle_runtime::padload::{PadloadManifest, SymTab};
use eagle_runtime::scenario::Scenario;
use eagle_dynamics::touchdown::Touchdown;
use std::path::PathBuf;
use std::time::Duration;

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..")
}

const WALL_BUDGET_S: u64 = 1800;

#[tokio::test]
#[ignore = "needs make agc artifacts (live acceptance, ~18-19 min)"]
async fn pdi_full_descent_closed_loop() {
    let sc = Scenario::load(&root().join("scenarios/pdi-descent.toml")).unwrap();
    let symtab = SymTab::from_listing(
        &std::fs::read_to_string(root().join("build/agc/Luminary099.log")).unwrap(),
    )
    .unwrap();
    let manifest = PadloadManifest::load(&root().join(&sc.agc.padload)).unwrap();
    let session = AgcSession::start(AgcConfig {
        yaagc_bin: root().join("build/agc/yaAGC"),
        core_bin: root().join("build/agc/Luminary099.bin"),
        port: 19905,
    })
    .await
    .unwrap();
    let (telem_tx, _keep) = tokio::sync::broadcast::channel::<String>(4096);
    let acceptance = sc.acceptance.clone();
    let result = tokio::time::timeout(
        Duration::from_secs(WALL_BUDGET_S),
        run_headless(HeadlessCfg {
            session,
            scenario: sc,
            symtab,
            manifest,
            telem_tx,
            latest: None,
            trace_out: Some(root().join("build/traces/pdi-acceptance.jsonl")),
            client_rx: None,
            client_rod_rx: None,
        }),
    )
    .await
    .expect("exceeded wall budget")
    .expect("closed loop errored");

    // DIAGNOSTICS FIRST (Wave 1 final-review lesson: print before assert).
    eprintln!("[accept] MM {:?}", result.mm_sequence);
    eprintln!("[accept] touchdown {:?} descent {:?}s", result.sim.touchdown, result.descent_s);
    eprintln!("[accept] alarms {:?} prog_lamp {}", result.alarms, result.prog_lamp_frames);
    eprintln!(
        "[accept] AGC clock drift {:.0}ms over {:.0}s, downlink {:.1}wps, pacing lost {:.0}ms",
        result.drift_ms, result.final_t_s, result.mid_downlink_wps, result.sim.pacing_lost_ms
    );
    if result.mm_sequence.iter().any(|m| m == "65") {
        eprintln!("[accept] FINDING: MM65 appeared — handover altitude needs revisiting (spec §3 M1)");
    }

    // MM order 63 < 64 < 66.
    let idx = |mm: &str| result.mm_sequence.iter().position(|m| m == mm);
    let (i63, i64_, i66) = (idx("63"), idx("64"), idx("66"));
    assert!(
        matches!((i63, i64_, i66), (Some(a), Some(b), Some(c)) if a < b && b < c),
        "MM must contain 63 then 64 then 66: {:?}",
        result.mm_sequence
    );

    let td = result.sim.touchdown.expect("no touchdown");
    let descent = result.descent_s.expect("no descent time");
    assert!(descent <= acceptance.timeout_s, "descent {descent:.0}s > {}", acceptance.timeout_s);
    assert_eq!(td.class, Touchdown::Nominal, "not nominal: {:?}", td.class);
    assert!(td.v_vert_ms < acceptance.v_vert_max);
    assert!(td.v_horiz_ms < acceptance.v_horiz_max);
    assert!(td.tilt_deg < acceptance.tilt_max_deg);
    eprintln!("[accept] miss distance {:.1} m", td.miss_m);
    // miss_m: reported only until Task 5's runs show a stable value — the
    // PDI frame carries a documented few-km site/time-base caveat.

    assert!(result.alarms.is_empty(), "alarm episodes: {:?}", result.alarms);
    assert_eq!(result.prog_lamp_frames, 0, "PROG lamp lit during descent");

    // AGC clock-rate gate (scale-free; provisional tolerance measured on
    // this host in Wave 1 — update the numbers from Task 5's runs).
    assert!(result.final_t_s > 0.0, "no telemetry");
    let agc_rate = 1.0 + result.drift_ms / 1000.0 / result.final_t_s;
    assert!((agc_rate - 1.0).abs() < 0.10, "AGC clock rate {agc_rate}");
}
```

(Adjust field names against the real `HeadlessResult` — Wave 1's final fix
wave added `alarms`, `prog_lamp_frames`, `final_t_s`, `pacing_lost_ms`.)

- [ ] **Step 2: Compile gate** — `cargo test -p eagle-runtime --test live_pdi_descent --no-run`.

- [ ] **Step 3: Run live until green 2× consecutively** (the M1 bar; each run ~18-19 min):

```bash
cargo test -p eagle-runtime --test live_pdi_descent -- --ignored --test-threads=1
```

Record both runs' `[accept]` blocks in the Task 5 ledger note. If Task 5
ended without a stable profile (stop rule), this task instead records the
honest status and the test stays as the target.

- [ ] **Step 4: Docs truth pass.** `CLAUDE.md` + `README.md`: describe M1
per the measured outcome (never "soft touchdown" unless the acceptance is
the thing that measured it); add `make descent-full` and the pdi scenario
to the run docs; update the Wave 2 spec with an M1 status note (green date
+ commit, or the blocker). Update `make test-integration` docs if the new
test joins it (it does — it is `#[ignore]`d and serial like the others).

- [ ] **Step 5: Full fast gate + commit** —
`git commit -m "feat(eagle): M1 acceptance — real PDI descent to landing (radar bypassed)"` (+ trailers).

---

## Execution notes for the controller

- Tasks 1-4 are fast (no AGC) and safely reviewable per task. Task 5 is a
  live spike: findings are data, budget 6 flights, stop rule binding.
  Task 6 freezes what Task 5 measured.
- Task 5/6 wall-clock: each flight ~18-19 min. Schedule reviews of Tasks
  1-4 while flights run only if the reviewer does not touch the tree.
- If Task 5 hits its stop rule, Task 6 still runs (docs truth pass) — the
  wave then pauses for M2 (snapshots) design reassessment, since a red M1
  changes M2's value proposition.

## Self-review

- **Spec coverage (design doc §3 M1):** single-source state → Task 1;
  schema mode/handover/lrbypass → Task 2; freeze semantics + PDI PIPA →
  Task 3; sim-driven handover → Tasks 3+4; LRBYPASS handling → Task 4
  (verify-only per the fresh-start finding — a deviation from the spec's
  "set_flag_bits" wording, justified by `FRESH_START_AND_RESTART.agc:614`
  and recorded here); ROD-schedule-from-measurement → Task 5; MM65
  finding-not-assert → Task 6; miss-distance caveat → Tasks 2/6.
- **Deviation from spec worth flagging:** the spec sketches
  `set_flag_bits(FLAGWRD11, LRBYBIT)`; planning-time vendor verification
  showed fresh start already sets it, so M1 verifies instead of sets. M3
  must CLEAR it — noted for the M3 plan.
- **Placeholder scan:** `[rod] steps = []` and acceptance values are
  explicit measured-later fields per the spec's "not guessed" rule, each
  tagged with the task that fills them — not placeholders in the forbidden
  sense (the plan text says exactly who measures them and when).
- **Type consistency:** `SimEvent` defined in Task 3, consumed in Task 4;
  `PdiMasses`/`pdi_truth_state` defined in Task 1, consumed in Task 2;
  `GateMode` in Task 2, consumed in Tasks 3-4; port 19905 unique;
  `next_sim_event` naming consistent between Tasks 3 note and Task 4 code.
