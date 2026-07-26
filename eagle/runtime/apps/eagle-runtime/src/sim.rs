//! SimCore: the 100 Hz closed-loop sim (spec §6). A pure, deterministic
//! core (`SimCore`) plus a std-thread shell (`spawn_sim`) that wall-paces
//! it at 10 ms and bridges the tokio AGC socket via channels.
//!
//! The tick order below is FIXED and load-bearing for determinism — each
//! numbered phase is one private method, called in sequence from `tick`.
//!
//! ROD note (no-patch build): a rate-of-descent "click" is delivered as a
//! direct RODCOUNT load, not a channel-016 packet (which stock yaAGC never
//! turns into an interrupt — see docs/agc-channel-map.md). So the ROD
//! schedule emits a signed click COUNT in `SimTickOut::rod_clicks`; the
//! tokio side turns it into `runner::rod_load`. (The plan predates the
//! Spike-B RODCOUNT finding and specified ch016 press/release packets.)
use crate::scenario::{GateMode, Scenario};
use eagle_agc_protocol::agc_io::{decode_output, pipa_pulse, AgcOutput, PipaAxis};
use eagle_agc_protocol::dsky::DskyState;
use eagle_agc_protocol::Packet;
use eagle_dynamics::constants::{DT, THRUST_N_PER_PULSE, TRIM_MAX_DEG, TRIM_RATE_DEG_S};
use eagle_dynamics::forces::{actuator_step, body_thrust_force, forces, Actuators, V3Raw};
use eagle_dynamics::frames::{mci_to_mcmf, Body, Mci, Mcmf, Sm, V3};
use eagle_dynamics::rk4::step_rk4;
use eagle_dynamics::state::{surface_velocity, LmState};
use eagle_dynamics::touchdown::{classify_touchdown, Touchdown};
use eagle_schema::{TelemetryMsg, SCHEMA_VERSION};

/// Hover-support specific force during the freeze phase, m/s² (lunar g).
const HOVER_ACCEL_MS2: f64 = 1.62;
/// One ROD click changes the sink-rate target by 1 ft/s.
const ROD_CLICK_MS: f64 = 0.3048;

/// The AGC's own navigation readout, parsed from its flight display.
#[derive(Debug, Clone, Copy, Default, PartialEq)]
pub struct AgcNav {
    pub alt_m: Option<f64>,
    pub hdot_ms: Option<f64>,
}

/// A snapshot of the AGC display relevant to the sim: major mode and nav.
#[derive(Debug, Clone, Default, PartialEq)]
pub struct DskyStateSnapshot {
    pub mm: String,
    pub nav: Option<AgcNav>,
}

impl DskyStateSnapshot {
    pub fn from_dsky(d: &DskyState) -> Self {
        Self {
            mm: d.prog.iter().collect(),
            nav: parse_agc_nav(d),
        }
    }
}

/// Parse the AGC flight display: R2 = HDOTDISP in 0.1 ft/s and R3 =
/// HCALC/HCALC1 in whole feet.
///
/// V06N60, V06N63 AND V06N64 are all accepted, because those three ARE the
/// landing guidance flight displays, one per phase
/// (`vendor/virtualagc/Luminary099/LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1467-1469`:
/// `V06N63 # P63`, `V06N64 # P64`, `V06N60 # P65, P66, P67`). P64 puts
/// N64 up for the whole approach — `:875` (flashing, redesignation
/// available) and `:895` (`REDES-OK`) — which is precisely the window the
/// sim-driven P64→P66 handover fires in.
///
/// **R2 and R3 are the same words in all three**
/// (`vendor/virtualagc/Luminary099/PINBALL_NOUN_TABLES.agc:724-726` for
/// N60, `:733-735` for N63, `:736-738` for N64): R2 = HDOTDISP under the
/// `VEL3` scale-factor code, R3 = HCALC (N60/N64) or HCALC1 (N63) under
/// `COMP ALT`. Only R1 differs: N64 shows FUNNYDSP as a `2INT` pair where
/// N60/N63 show a `VEL3`, which the noun format words state exactly —
/// `:473` and `:479` are both `OCT 60512` (N60, N63) against `:481`'s
/// `OCT 60500` (N64), i.e. identical R2/R3 fields with only the R1 field
/// cleared.
///
/// **Both display scales come from the rope's own scale-factor legend**
/// (`vendor/virtualagc/Luminary099/PINBALL_NOUN_TABLES.agc:86-120`), which
/// lists each 5-bit SF code with the units it displays. The three 5-bit
/// fields of a `3COMP` format word are R3|R2|R1 from the top — provable
/// from the pair above, since N64 differs from N60/N63 only in the LOW
/// field (`0o12` → `0o00`) and only in R1. So:
///
/// * R2 field `01010` = `VELOCITY3 (XXXX.X FT/SEC)` (`:95`) → the display
///   integer is TENTHS of a foot per second. Independently confirmed live
///   in Spike B: R2 `+00756` against HDOTDISP = 0.2344 m/cs = 76.9 ft/s.
/// * R3 field `11000` = `COMPUTED ALTITUDE (XXXXX. FEET)` (`:118`) → the
///   display integer is WHOLE FEET.
///
/// The R3 datum is the same one `alt_agl()` uses: SERVICER computes
/// `HCALC = ABVAL(R) - /LAND/` — vehicle radius minus landing-site radius
/// — and stores it to both HCALC and HCALC1
/// (`vendor/virtualagc/Luminary099/SERVICER.agc:822-827`, `# NEW
/// HCALC*2(24)M.`). So `nav_err_alt_m` is a like-for-like AGC-vs-truth
/// comparison, not a datum difference.
///
/// (Cross-check of the legend, since the whole altitude nav-error signal
/// rests on it: `SFOUTAB`'s `COMPUTED ALTITUDE` constant is the DP pair
/// `OCT 01046` / `OCT 15700` (`:650-651`) = 0.033595327, the display
/// routine for an `ARITHDP1` noun is `DP1OUTSF`, which scales by that
/// constant and then by 2¹⁴
/// (`vendor/virtualagc/Luminary099/PINBALL_GAME__BUTTONS_AND_LIGHTS.agc:1488-1492`),
/// and a 5-digit decimal display is the result × 10⁵. With HCALC at
/// 2²⁴ m that gives `alt_m × 0.033595327 × 2¹⁴ × 10⁵ / 2²⁴ =
/// alt_m × 3.280839` — feet, to seven figures. The same arithmetic run on
/// `WEIGHT2` (`OCT 00001`/`OCT 16170`, N47's "XXXXX. LBS") returns
/// kg × 2.2046, which is why the convention is trusted rather than
/// assumed.)
///
/// Accepting only N60 meant `agc_hdot_ms` / `nav_err_hdot_ms` were `null`
/// in every frame of both 2026-07-25 re-flight telemetry dumps — the run
/// never leaves P63 before ground contact, so the display never reaches
/// N60 — and the AGC-vs-truth navigation error (the run's headline
/// finding) had to be recovered by hand-decoding the ch010 relay stream
/// after the fact. Adding N63 fixed that for P63; N64 closes the same hole
/// for P64, which no run had reached until Wave 2 M1.
/// See docs/superpowers/notes/2026-07-25-wave1-reflight.md.
pub fn parse_agc_nav(d: &DskyState) -> Option<AgcNav> {
    let verb: String = d.verb.iter().collect();
    let noun: String = d.noun.iter().collect();
    if verb != "06" || !matches!(noun.as_str(), "60" | "63" | "64") {
        return None;
    }
    let hdot_ms = parse_decimal_register(&d.r2).map(|v| v as f64 * 0.1 * 0.3048);
    let alt_m = parse_decimal_register(&d.r3).map(|v| v as f64 * 0.3048);
    Some(AgcNav { alt_m, hdot_ms })
}

/// Parse a DSKY register (sign + 5 digits) as a signed decimal integer.
fn parse_decimal_register(reg: &eagle_agc_protocol::dsky::RegisterDisplay) -> Option<i32> {
    let digits: String = reg.digits.iter().collect();
    let mag: i32 = digits.trim().parse().ok()?;
    Some(if reg.sign == '-' { -mag } else { mag })
}

/// One event ingested from the AGC side.
#[derive(Debug, Clone)]
pub enum SimIn {
    Agc(AgcOutput),
    Dsky(DskyStateSnapshot),
}

/// Turn one raw AGC packet into sim events: always its decoded autopilot
/// output, plus a fresh DSKY snapshot when the packet changed the display.
/// `dsky` is the caller's running display state (applied in place).
pub fn agc_packet_to_simin(p: &Packet, dsky: &mut DskyState) -> Vec<SimIn> {
    let mut evs = vec![SimIn::Agc(decode_output(p))];
    if dsky.apply(p) {
        evs.push(SimIn::Dsky(DskyStateSnapshot::from_dsky(dsky)));
    }
    evs
}

/// Result of one 10 ms tick.
#[derive(Debug, Default)]
pub struct SimTickOut {
    pub to_agc: Vec<Packet>,
    pub telemetry: Option<TelemetryMsg>,
    pub touchdown: Option<Touchdown>,
    /// Signed ROD clicks to deliver via RODCOUNT this tick (see module doc).
    pub rod_clicks: i32,
    /// Fires on exactly one tick: the P64→P66 handover point was reached.
    pub handover: bool,
}

/// Sim → headless events that need the DSKY script or discrete writes.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum SimEvent {
    /// Signed ROD clicks to deliver via RODCOUNT (schedule + handover click
    /// are separate: the handover click is part of Handover).
    RodClicks(i32),
    /// P64→P66 handover: ATT HOLD discrete + the selection ROD click.
    Handover,
}

/// Latched trim-gimbal drive bits (ch012).
#[derive(Debug, Default, Clone, Copy)]
struct TrimBits {
    minus_pitch: bool,
    plus_pitch: bool,
    minus_roll: bool,
    plus_roll: bool,
}

/// The deterministic closed-loop core.
pub struct SimCore {
    st: LmState,
    frozen: bool,
    act: Actuators,
    trim: TrimBits,
    thrust: crate::runner::ThrustResponder,
    imu: eagle_sensors::imu::Imu,
    pipa: eagle_sensors::pipa::Pipa,
    cdu: eagle_sensors::imu::Cdu,
    errors: eagle_sensors::errors::ImuErrors,
    inertia0: V3Raw,
    mass0_kg: f64,
    radius_m: f64,
    /// Landing-site radial unit vector, moon-fixed — the miss-distance datum.
    site_unit_mcmf: V3<Mcmf>,
    rod_steps: Vec<[f64; 2]>,
    rod_target_ms: f64,
    rod_step_idx: usize,
    downlink_words: u64,
    mm: String,
    agc_nav: Option<AgcNav>,
    ingest_drops: u64,
    tick_index: u64,
    touchdown: Option<Touchdown>,
    /// Body-frame specific force this tick (for the PIPA feed).
    sf_body: V3<Body>,
    /// `gate.mode == Pdi`: the freeze is a free coast, not a hover.
    pdi: bool,
    /// Altitude (m AGL) at which the P64→P66 handover fires once armed.
    /// `None` in hover mode — Wave 1 flips ATT HOLD on a wall clock instead.
    handover_alt_m: Option<f64>,
    /// MM64 has been observed at least once (arms the handover).
    handover_armed: bool,
    /// The handover has already fired (it is a one-shot).
    handover_fired: bool,
    queue: Vec<SimIn>,
}

impl SimCore {
    pub fn new(sc: &Scenario, epoch_s: f64) -> Self {
        let st = sc.initial_state(epoch_s);
        let mass0_kg = st.mass_kg;
        let imu = eagle_sensors::imu::Imu::new(sm_from_initial(&st));
        let errors = eagle_sensors::errors::ImuErrors::new(
            sc.errors.imu.as_ref().map(Into::into).unwrap_or_default(),
        );
        Self {
            st,
            frozen: true,
            act: Actuators {
                engine_on: false,
                throttle_cmd_n: 0.0,
                thrust_n: 0.0,
                trim_pitch_rad: 0.0,
                trim_roll_rad: 0.0,
                jets: 0,
            },
            trim: TrimBits::default(),
            thrust: crate::runner::ThrustResponder::default(),
            imu,
            pipa: eagle_sensors::pipa::Pipa::default(),
            cdu: eagle_sensors::imu::Cdu::default(),
            errors,
            inertia0: V3Raw(
                sc.gate.inertia_kgm2[0],
                sc.gate.inertia_kgm2[1],
                sc.gate.inertia_kgm2[2],
            ),
            mass0_kg,
            radius_m: sc.site.radius_m,
            site_unit_mcmf: sc.site_unit_mcmf(),
            rod_steps: sc.rod.steps.clone(),
            rod_target_ms: 0.0,
            rod_step_idx: 0,
            downlink_words: 0,
            mm: String::new(),
            agc_nav: None,
            ingest_drops: 0,
            tick_index: 0,
            touchdown: None,
            sf_body: V3::zero(),
            pdi: sc.gate.mode == GateMode::Pdi,
            // Hover mode stays bit-identical to Wave 1: no sim-driven
            // handover there, whatever the file says.
            handover_alt_m: match sc.gate.mode {
                GateMode::Pdi => sc.handover.as_ref().map(|h| h.alt_m),
                GateMode::Hover => None,
            },
            handover_armed: false,
            handover_fired: false,
            queue: Vec::new(),
        }
    }

    /// Queue an event; applied at the start of the next `tick` (phase 1).
    pub fn ingest(&mut self, ev: SimIn) {
        self.queue.push(ev);
    }

    /// Record a dropped ingest (bounded-channel overflow on the thread side).
    pub fn note_drop(&mut self) {
        self.ingest_drops += 1;
    }

    /// Advance one fixed 10 ms tick.
    pub fn tick(&mut self) -> SimTickOut {
        let mut out = SimTickOut::default();
        self.phase1_apply_events();
        self.phase2_trim();
        self.phase3_throttle();
        self.phase4_5_dynamics();
        self.phase6_sensors(&mut out);
        self.phase7_thrust(&mut out);
        self.phase8_rod(&mut out);
        self.phase9_handover(&mut out);
        self.phase10_telemetry_and_touchdown(&mut out);
        self.debug_attitude_loop();
        self.tick_index += 1;
        out
    }

    /// Diagnostic: log the attitude-control loop signals (gimbals we send,
    /// jets the AGC fired, torque we produce) when EAGLE_ATT_DEBUG is set.
    /// One line per 10 ticks post-freeze — enough to read the sign chain.
    fn debug_attitude_loop(&self) {
        if self.frozen || !self.tick_index.is_multiple_of(10) {
            return;
        }
        thread_local! {
            static DBG: std::cell::RefCell<Option<std::fs::File>> =
                const { std::cell::RefCell::new(None) };
            static INIT: std::cell::Cell<bool> = const { std::cell::Cell::new(false) };
        }
        INIT.with(|i| {
            if !i.get() {
                i.set(true);
                if let Ok(p) = std::env::var("EAGLE_ATT_DEBUG") {
                    DBG.with(|d| *d.borrow_mut() = std::fs::File::create(p).ok());
                }
            }
        });
        DBG.with(|d| {
            if let Some(f) = d.borrow_mut().as_mut() {
                use std::io::Write;
                let g = self.imu.gimbals_deg(&self.st.att);
                let tau = eagle_dynamics::forces::jet_torque(self.act.jets);
                let w = self.st.omega;
                let _ = writeln!(
                    f,
                    "t={:.2} jets={} gimbal=[{:.2},{:.2},{:.2}] omega=[{:.4},{:.4},{:.4}] torque=[{:.1},{:.1},{:.1}]",
                    self.st.t, self.act.jets, g[0], g[1], g[2],
                    w.x, w.y, w.z, tau.x, tau.y, tau.z
                );
            }
        });
    }

    // 1. Apply queued discrete actuator changes from ingested events.
    fn phase1_apply_events(&mut self) {
        for ev in std::mem::take(&mut self.queue) {
            match ev {
                SimIn::Agc(o) => match o {
                    AgcOutput::Jets5 { mask } => {
                        self.act.jets = (self.act.jets & 0xFF00) | mask as u16;
                    }
                    AgcOutput::Jets6 { mask } => {
                        self.act.jets = (self.act.jets & 0x00FF) | ((mask as u16) << 8);
                    }
                    AgcOutput::Engine { on, off } => {
                        if on {
                            self.act.engine_on = true;
                            self.frozen = false;
                        }
                        if off {
                            self.act.engine_on = false;
                        }
                    }
                    AgcOutput::Trim {
                        minus_pitch,
                        plus_pitch,
                        minus_roll,
                        plus_roll,
                    } => {
                        self.trim = TrimBits {
                            minus_pitch,
                            plus_pitch,
                            minus_roll,
                            plus_roll,
                        };
                    }
                    AgcOutput::ThrustDrive(_) | AgcOutput::ThrustPulse(_) => {
                        self.thrust.on_output(&o);
                    }
                    AgcOutput::CoarseAlign {
                        axis,
                        positive,
                        pulses,
                    } => {
                        let signed = if positive {
                            pulses as i32
                        } else {
                            -(pulses as i32)
                        };
                        self.imu.apply_coarse(axis, signed);
                    }
                    AgcOutput::Gyro { raw } => self.imu.apply_gyro(raw),
                    AgcOutput::Downlink => self.downlink_words += 1,
                    AgcOutput::Other(_) => {}
                },
                SimIn::Dsky(snap) => {
                    self.mm = snap.mm;
                    if snap.nav.is_some() {
                        self.agc_nav = snap.nav;
                    }
                }
            }
        }
    }

    // 2. Trim integration under the latched ch012 bits.
    fn phase2_trim(&mut self) {
        let rate = TRIM_RATE_DEG_S.to_radians() * DT;
        let max = TRIM_MAX_DEG.to_radians();
        if self.trim.plus_pitch {
            self.act.trim_pitch_rad = (self.act.trim_pitch_rad + rate).min(max);
        }
        if self.trim.minus_pitch {
            self.act.trim_pitch_rad = (self.act.trim_pitch_rad - rate).max(-max);
        }
        if self.trim.plus_roll {
            self.act.trim_roll_rad = (self.act.trim_roll_rad + rate).min(max);
        }
        if self.trim.minus_roll {
            self.act.trim_roll_rad = (self.act.trim_roll_rad - rate).max(-max);
        }
    }

    // 3. Throttle command from the accumulated DINC pulses, then lag.
    fn phase3_throttle(&mut self) {
        self.act.throttle_cmd_n = self.thrust.cmd_pulses as f64 * THRUST_N_PER_PULSE;
        actuator_step(&mut self.act, DT);
        if !self.act.engine_on || self.st.fuel_dps_kg <= 0.0 {
            self.act.thrust_n = 0.0;
        }
    }

    // 4/5. Freeze until first ENGINE ON; then integrate the rigid body.
    //
    // The release trigger is ENGINE ON (ch 011 bit 13) in BOTH modes — the
    // Wave 1 mechanism, unchanged. What differs is the frozen specific
    // force fed to the PIPAs:
    //
    // * Hover: 1.62 m/s² support, so nav sees the vehicle standing on its
    //   engine at the gate.
    // * PDI: ZERO. The pre-ignition arc is a free coast, and truth is
    //   pinned, so nav must see nothing accelerate — anything else is a
    //   pure nav error injected before the burn even starts. Ullage starts
    //   at TIG−7.5 s (ULLGTASK,
    //   vendor/virtualagc/Luminary099/BURN,_BABY,_BURN_--_MASTER_IGNITION_ROUTINE.agc:356),
    //   so it falls inside this window and is therefore consistently
    //   absent from both sides. Its ΔV is ~0.9 m/s — derived, not
    //   measured: 4 jets × ~445 N × 7.5 s / 15.2 t = 0.88 m/s.
    //
    // Releasing at ENGINE ON ≈ TIG−0 is what makes truth and nav agree:
    // `DDUMGOOD` computes TIG = TDEC1 − ZOOMTIME
    // (vendor/virtualagc/Luminary099/THE_LUNAR_LANDING.agc:193-198), so the
    // pad load's geometric ignition point is where the AGC's nav sits at
    // FLATOUT = TIG+ZOOMTIME, NOT at ENGINE ON (≈44.31 km uprange of it).
    // `padload::pdi_truth_state` therefore back-propagates that point by
    // ZOOMTIME under gravity and hands us the TIG-time state, which this
    // release then unpins exactly where nav believes it is. The freeze also
    // absorbs the AGC's ~4.8 % clock-rate offset: nav advances on the AGC's
    // own clock while truth waits, so the two meet whenever ENGINE ON
    // actually arrives.
    //
    // Commanding an attitude against frozen truth is safe: Wave 1 measured
    // the DAP recovering a ~125° error in ~13 s after release, well before
    // Luminary throttles up at FLATOUT = TIG+26 s
    // (docs/superpowers/notes/2026-07-25-wave1-reflight.md).
    fn phase4_5_dynamics(&mut self) {
        if self.frozen {
            // Advance the clock even while pinned, so telemetry rates
            // (downlink_wps, drift) don't divide accumulated counts by a
            // near-zero t_s at engine-on.
            self.st.t += DT;
            self.sf_body = if self.pdi {
                V3::zero()
            } else {
                V3::new(HOVER_ACCEL_MS2, 0.0, 0.0)
            };
            return;
        }
        self.sf_body = body_thrust_force(&self.act).scale(1.0 / self.st.mass_kg);
        let inertia0 = self.inertia0;
        let mass0 = self.mass0_kg;
        let act = self.act.clone();
        let f = |s: &LmState| forces(s, &act, inertia0, mass0);
        self.st = step_rk4(&self.st, &f, DT);
    }

    // 6. Sensors: PIPA (SM ΔV → pulses) and CDU (gimbals → pulses).
    fn phase6_sensors(&mut self, out: &mut SimTickOut) {
        let dv_body = self.sf_body.scale(DT);
        // Body → SM: v_sm = (SM→MCI)⁻¹ · att · v_body.
        let dv_sm: V3<Sm> = self
            .imu
            .sm_to_mci()
            .inverse()
            .apply(self.st.att.apply(dv_body));
        let dv_sm = self.errors.corrupt(dv_sm, DT);
        let pulses = self.pipa.step(dv_sm);
        let axes = [PipaAxis::X, PipaAxis::Y, PipaAxis::Z];
        for (i, axis) in axes.into_iter().enumerate() {
            for _ in 0..pulses[i].abs() {
                out.to_agc.push(pipa_pulse(axis, pulses[i] > 0));
            }
        }
        for pk in self.cdu.step(self.imu.gimbals_deg(&self.st.att)) {
            out.to_agc.push(pk);
        }
    }

    // 7. THRUST DINC strobe.
    fn phase7_thrust(&mut self, out: &mut SimTickOut) {
        out.to_agc.extend(self.thrust.tick_packets());
    }

    // 8. ROD schedule: crossing an altitude threshold queues clicks.
    fn phase8_rod(&mut self, out: &mut SimTickOut) {
        let alt = self.alt_agl();
        while self.rod_step_idx < self.rod_steps.len()
            && alt <= self.rod_steps[self.rod_step_idx][0]
        {
            let new_target = self.rod_steps[self.rod_step_idx][1];
            let delta = new_target - self.rod_target_ms;
            out.rod_clicks += (delta / ROD_CLICK_MS).round() as i32;
            self.rod_target_ms = new_target;
            self.rod_step_idx += 1;
        }
    }

    // 9. P64→P66 handover: a one-shot, armed by MM64 and fired by altitude.
    //
    // Both conditions are load-bearing. GUILDENSTERN's P66 switch does not
    // require MM63, so it works from P64
    // (vendor/virtualagc/Luminary099/LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:203-217),
    // but it is only reached once landing guidance is running — hence the
    // MM64 arm. Altitude alone would fire during the braking phase, while
    // the vehicle is still below the gate on the way down from PDI.
    // `handover_alt_m` is `None` in hover mode, so this is inert there.
    //
    // The freeze and touchdown guards close the two windows where the
    // altitude test is trivially true and the handover is meaningless:
    // during the freeze truth is pinned (a scenario pinned below the gate
    // would fire before ENGINE ON), and after contact `alt_agl() <= 0`
    // holds forever while `spawn_sim` keeps ticking for 2 s — with Wave 1
    // measuring MM66, and so a late MM64, arriving 0.6-1.8 s AFTER contact
    // (docs/superpowers/notes/2026-07-25-wave1-reflight.md). Either would
    // flip ATT HOLD and load RODCOUNT into a vehicle that is not flying.
    fn phase9_handover(&mut self, out: &mut SimTickOut) {
        let Some(alt_gate) = self.handover_alt_m else {
            return;
        };
        if self.mm == "64" {
            self.handover_armed = true;
        }
        if self.handover_armed
            && !self.handover_fired
            && !self.frozen
            && self.touchdown.is_none()
            && self.alt_agl() <= alt_gate
        {
            self.handover_fired = true;
            out.handover = true;
        }
    }

    // 10. Telemetry every 10th tick; touchdown latch.
    fn phase10_telemetry_and_touchdown(&mut self, out: &mut SimTickOut) {
        let alt = self.alt_agl();
        if self.touchdown.is_none() && !self.frozen && alt <= 0.0 {
            let (vv, vh, tilt) = self.landing_kinematics();
            let td = classify_touchdown(vv, vh, tilt);
            self.touchdown = Some(td);
            out.touchdown = Some(td);
        }
        if self.tick_index.is_multiple_of(10) {
            out.telemetry = Some(self.telemetry());
        }
    }

    fn alt_agl(&self) -> f64 {
        self.st.pos.norm() - self.radius_m
    }

    /// Surface-relative velocity split: (signed vertical, horizontal speed).
    fn rel_velocity(&self) -> (f64, f64) {
        let up = self.st.pos.unit();
        let v_rel = self.st.vel - surface_velocity(self.st.pos);
        let vz = v_rel.dot(up);
        (vz, (v_rel - up.scale(vz)).norm())
    }

    /// (|vertical speed|, horizontal speed, tilt°), surface-relative.
    fn landing_kinematics(&self) -> (f64, f64, f64) {
        let (vz, v_h) = self.rel_velocity();
        let up = self.st.pos.unit();
        let body_x = self.st.att.apply(V3::<Body>::new(1.0, 0.0, 0.0));
        let tilt = body_x.dot(up).clamp(-1.0, 1.0).acos().to_degrees();
        (vz.abs(), v_h, tilt)
    }

    /// Great-circle distance from the scenario landing site, m.
    ///
    /// NOT a guidance-error metric today. `phase4_5_dynamics` pins the truth
    /// position in MCI for the whole pre-ignition freeze while the clock —
    /// and therefore MCMF — keeps turning, so this arc includes
    /// ω·R·cos φ × (freeze duration) of pure bookkeeping: a live acceptance
    /// run measured 1585.2 m over a 342.8 s freeze, which is the artifact
    /// alone to within a metre — the descent contributed nothing visible.
    /// Report it; do not gate on it until the freeze phase co-rotates
    /// (docs/coordinate-frames.md "Truth co-rotation").
    fn miss_distance_m(&self) -> f64 {
        let pos_mcmf = mci_to_mcmf(self.st.t).apply(self.st.pos);
        let c = pos_mcmf.unit().dot(self.site_unit_mcmf).clamp(-1.0, 1.0);
        self.radius_m * c.acos()
    }

    fn telemetry(&self) -> TelemetryMsg {
        let (_vv, _vh, tilt) = self.landing_kinematics();
        let (vz, v_h) = self.rel_velocity();
        let t = self.st.t;
        // ch034 + ch035 are the low/high halves of each downlink word, so
        // two packets per word.
        let downlink_wps = if t > 0.0 {
            self.downlink_words as f64 / 2.0 / t
        } else {
            0.0
        };
        let drift_ms =
            (self.downlink_words as f64 / 2.0 / 50.0 - self.tick_index as f64 * DT) * 1000.0;
        let agc_alt_m = self.agc_nav.and_then(|n| n.alt_m);
        let agc_hdot_ms = self.agc_nav.and_then(|n| n.hdot_ms);
        TelemetryMsg {
            schema_version: SCHEMA_VERSION,
            t_s: t,
            frozen: self.frozen,
            alt_m: self.alt_agl(),
            vz_ms: vz,
            v_horiz_ms: v_h,
            tilt_deg: tilt,
            mass_kg: self.st.mass_kg,
            fuel_dps_kg: self.st.fuel_dps_kg,
            fuel_rcs_kg: self.st.fuel_rcs_kg,
            thrust_n: self.act.thrust_n,
            throttle_cmd_pulses: self.thrust.cmd_pulses,
            jets: self.act.jets,
            mm: self.mm.clone(),
            agc_alt_m,
            agc_hdot_ms,
            nav_err_alt_m: agc_alt_m.map(|a| a - self.alt_agl()),
            nav_err_hdot_ms: agc_hdot_ms.map(|h| h - vz),
            drift_ms,
            downlink_wps,
            ingest_drops: self.ingest_drops,
            touchdown: self.touchdown.map(|t| format!("{t:?}")),
            handover: self.handover_fired,
        }
    }
}

/// The IMU stable-member reference for a fresh scenario: SM ≡ initial BODY
/// attitude, so gimbals read zero at t0 (spec §3 / coordinate-frames.md).
fn sm_from_initial(st: &LmState) -> eagle_dynamics::frames::Rot<Sm, Mci> {
    eagle_dynamics::frames::retag(st.att)
}

// ---------------------------------------------------------------------
// Thread shell.
// ---------------------------------------------------------------------

/// Handle to a running sim thread.
pub struct SimHandle {
    pub join: std::thread::JoinHandle<SimResult>,
    pub stop: std::sync::mpsc::Sender<()>,
}

/// Touchdown summary measured at the latch instant, surface-relative.
#[derive(Debug, Clone, Copy)]
pub struct TouchdownReport {
    pub class: Touchdown,
    pub v_vert_ms: f64,
    pub v_horiz_ms: f64,
    pub tilt_deg: f64,
    /// Great-circle distance from the scenario landing site, m. Dominated
    /// by the pre-ignition freeze artifact (ω·R·cos φ × freeze duration;
    /// measured 1585.2 m for a 342.8 s freeze), so it is NOT a
    /// guidance-error metric — see `SimCore::miss_distance_m`.
    pub miss_m: f64,
}

/// Outcome once the sim thread exits.
#[derive(Debug, Default, Clone)]
pub struct SimResult {
    pub touchdown: Option<TouchdownReport>,
    /// Wall time the pacing loop fell behind and then DISCARDED by
    /// resetting its cadence, summed over the run (ms). It is the sim-side
    /// component of telemetry `drift_ms`: without it, an overrun is
    /// indistinguishable from an AGC clock that runs slow.
    pub pacing_lost_ms: f64,
}

/// Spawn the sim on its own std thread, wall-paced at 10 ms with no drift
/// accumulation. Drains `in_rx` each tick, forwards `to_agc` packets, and
/// broadcasts telemetry JSON. Exits on stop, channel close, or
/// touchdown + 2 s.
pub fn spawn_sim(
    mut core: SimCore,
    in_rx: std::sync::mpsc::Receiver<SimIn>,
    agc_tx: tokio::sync::mpsc::UnboundedSender<Packet>,
    telem_tx: tokio::sync::broadcast::Sender<String>,
    event_tx: tokio::sync::mpsc::UnboundedSender<SimEvent>,
) -> SimHandle {
    let (stop_tx, stop_rx) = std::sync::mpsc::channel::<()>();
    let join = std::thread::spawn(move || {
        let start = std::time::Instant::now();
        let mut next = start;
        let mut result = SimResult::default();
        let mut touchdown_at: Option<std::time::Instant> = None;
        loop {
            if stop_rx.try_recv().is_ok() {
                break;
            }
            // Drain all pending ingest events for this tick.
            let mut closed = false;
            loop {
                match in_rx.try_recv() {
                    Ok(ev) => core.ingest(ev),
                    Err(std::sync::mpsc::TryRecvError::Empty) => break,
                    Err(std::sync::mpsc::TryRecvError::Disconnected) => {
                        closed = true;
                        break;
                    }
                }
            }
            let out = core.tick();
            for pkt in out.to_agc {
                if agc_tx.send(pkt).is_err() {
                    closed = true;
                }
            }
            if let Some(t) = out.telemetry {
                if let Ok(j) = serde_json::to_string(&eagle_schema::ServerMsg::Telemetry(t)) {
                    let _ = telem_tx.send(j);
                }
            }
            if out.rod_clicks != 0 {
                let _ = event_tx.send(SimEvent::RodClicks(out.rod_clicks));
            }
            if out.handover {
                let _ = event_tx.send(SimEvent::Handover);
            }
            if let Some(td) = out.touchdown {
                let (vv, vh, tilt) = core.landing_kinematics();
                result.touchdown = Some(TouchdownReport {
                    class: td,
                    v_vert_ms: vv,
                    v_horiz_ms: vh,
                    tilt_deg: tilt,
                    miss_m: core.miss_distance_m(),
                });
                touchdown_at = Some(std::time::Instant::now());
            }
            if closed {
                break;
            }
            if let Some(td_at) = touchdown_at {
                if td_at.elapsed() >= std::time::Duration::from_secs(2) {
                    break;
                }
            }
            // Fixed-cadence pacing without drift.
            next += std::time::Duration::from_secs_f64(DT);
            let now = std::time::Instant::now();
            if next > now {
                std::thread::sleep(next - now);
            } else {
                // Falling behind: reset the cadence but RECORD the
                // discarded time — it is the sim-side component of
                // telemetry drift_ms.
                result.pacing_lost_ms += (now - next).as_secs_f64() * 1000.0;
                next = now;
            }
        }
        result
    });
    SimHandle {
        join,
        stop: stop_tx,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use eagle_agc_protocol::agc_io::ThrustPulse;
    use std::path::PathBuf;

    fn scenario() -> Scenario {
        Scenario::load(
            &PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../../scenarios/p66-gate.toml"),
        )
        .unwrap()
    }

    fn pdi_scenario() -> Scenario {
        Scenario::load(
            &PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../../scenarios/pdi-descent.toml"),
        )
        .unwrap()
    }

    fn engine_on(core: &mut SimCore) {
        core.ingest(SimIn::Agc(AgcOutput::Engine {
            on: true,
            off: false,
        }));
    }

    #[test]
    fn agc_nav_parses_hdot_from_n60_n63_and_n64() {
        // R2 is HDOTDISP on ALL THREE landing-guidance nouns, in 0.1 ft/s
        // (PINBALL_NOUN_TABLES.agc:724-726 / :733-735 / :736-738; only R1
        // differs). The 2026-07-25 re-flight never left P63 (so never
        // reached N60) and lost the AGC-vs-truth rate error from every
        // telemetry frame because this accepted only N60. N64 is the same
        // hole one phase later: P64 displays it for the whole approach
        // (LLGE:875, :895), which is the window the handover fires in.
        let dsky = |noun: [char; 2], sign: char, digits: [char; 5]| {
            let mut d = DskyState::default();
            d.verb = ['0', '6'];
            d.noun = noun;
            d.r2 = eagle_agc_protocol::dsky::RegisterDisplay { sign, digits };
            d
        };
        // Spike B's live sample: "+00756" = 75.6 ft/s = 23.04 m/s.
        let want = 756.0 * 0.1 * 0.3048;
        for noun in [['6', '0'], ['6', '3'], ['6', '4']] {
            let nav = parse_agc_nav(&dsky(noun, '+', ['0', '0', '7', '5', '6']))
                .unwrap_or_else(|| panic!("N{noun:?} must parse"));
            assert!((nav.hdot_ms.unwrap() - want).abs() < 1e-9, "{noun:?}");
            // A blank R3 (the DSKY paints nothing there before the first
            // repaint) must not decode as an altitude of zero.
            assert_eq!(nav.alt_m, None, "blank R3 is not 0 ft");
        }
        // R3 = COMPUTED ALTITUDE in WHOLE FEET
        // (PINBALL_NOUN_TABLES.agc:118, the SF-code legend), on all three
        // nouns. 49911 ft = 15212.6 m — the PDI ignition altitude, i.e.
        // exactly what the AGC should be showing at ENGINE ON in M1.
        for noun in [['6', '0'], ['6', '3'], ['6', '4']] {
            let mut d = dsky(noun, '-', ['0', '0', '2', '1', '3']);
            d.r3 = eagle_agc_protocol::dsky::RegisterDisplay {
                sign: '+',
                digits: ['4', '9', '9', '1', '1'],
            };
            let nav = parse_agc_nav(&d).unwrap();
            assert!(
                (nav.alt_m.unwrap() - 49911.0 * 0.3048).abs() < 1e-9,
                "N{noun:?} altitude: {:?}",
                nav.alt_m
            );
        }
        // N64's R1 is a 2INT pair where N60/N63 carry a VEL3 — irrelevant
        // to us, since only R2 is read, but pin that it does not disturb
        // the parse.
        let mut n64 = dsky(['6', '4'], '+', ['0', '0', '7', '5', '6']);
        n64.r1 = eagle_agc_protocol::dsky::RegisterDisplay {
            sign: ' ',
            digits: ['1', '2', '3', '4', '5'],
        };
        let nav = parse_agc_nav(&n64).expect("N64 must parse regardless of R1");
        assert!((nav.hdot_ms.unwrap() - want).abs() < 1e-9);
        // Sign is honoured: the re-flight's AGC read POSITIVE (climbing)
        // while the truth was falling — a sign drop would have hidden it.
        let neg = parse_agc_nav(&dsky(['6', '3'], '-', ['0', '0', '2', '1', '3'])).unwrap();
        assert!(neg.hdot_ms.unwrap() < 0.0);
        // Any other display is not a nav frame.
        assert!(parse_agc_nav(&dsky(['6', '2'], '+', ['0', '0', '0', '0', '1'])).is_none());
        let mut wrong_verb = dsky(['6', '0'], '+', ['0', '0', '7', '5', '6']);
        wrong_verb.verb = ['1', '6'];
        assert!(parse_agc_nav(&wrong_verb).is_none());
    }

    #[test]
    fn agc_packet_decodes_to_simin_events() {
        let mut dsky = DskyState::default();
        // An engine-on IO write decodes to Engine{on} and does not touch the
        // relay-driven DSKY display, so no Dsky snapshot.
        let evs = agc_packet_to_simin(&Packet::io(0o11, 1 << 12).unwrap(), &mut dsky);
        assert_eq!(evs.len(), 1);
        assert!(matches!(
            evs[0],
            SimIn::Agc(AgcOutput::Engine { on: true, .. })
        ));
        // A relay write (ch010) updates the display → a Dsky snapshot too.
        let relay = Packet::io(0o10, (10 << 11) | (0b10101 << 5) | 0b00011).unwrap();
        let evs = agc_packet_to_simin(&relay, &mut dsky);
        assert!(evs.iter().any(|e| matches!(e, SimIn::Dsky(_))));
    }

    #[test]
    fn frozen_until_engine_on_then_falls() {
        let sc = scenario();
        let mut core = SimCore::new(&sc, 0.0);
        let pos0 = core.st.pos;
        for _ in 0..100 {
            core.tick();
        }
        assert_eq!(core.st.pos, pos0, "frozen state must not move");
        engine_on(&mut core);
        for _ in 0..100 {
            core.tick();
        }
        let up = core.st.pos.unit();
        assert!(
            core.st.vel.dot(up) < 0.0,
            "should be falling after engine on"
        );
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
        assert_eq!(
            pipa_packets, 0,
            "coast freeze must feed ZERO specific force"
        );
        engine_on(&mut core);
        for _ in 0..100 {
            core.tick();
        }
        assert_ne!(core.st.pos, pos0, "dynamics must run after ENGINE ON");
    }

    #[test]
    fn hover_freeze_still_feeds_hover_support() {
        // Regression guard: hover mode is bit-identical to Wave 1.
        let sc = scenario();
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
        core.ingest(SimIn::Dsky(DskyStateSnapshot {
            mm: "63".into(),
            nav: None,
        }));
        assert!(!core.tick().handover, "not armed before MM64");
        // MM64 appears while below threshold: fires exactly once.
        core.ingest(SimIn::Dsky(DskyStateSnapshot {
            mm: "64".into(),
            nav: None,
        }));
        assert!(core.tick().handover, "armed + below altitude => fire");
        assert!(!core.tick().handover, "fires once");
    }

    #[test]
    fn handover_never_fires_after_touchdown() {
        // `alt_agl() <= 0 <= handover_alt_m` holds forever once the vehicle
        // is down, and `spawn_sim` keeps ticking for 2 s past contact —
        // while Wave 1 measured MM66 (and therefore a late MM64) lighting
        // 0.6-1.8 s AFTER contact. Arming post-touchdown must not flip ATT
        // HOLD and load RODCOUNT into a landed vehicle.
        let sc = pdi_scenario();
        let mut core = SimCore::new(&sc, 0.0);
        engine_on(&mut core);
        core.st.pos = core.st.pos.unit().scale(sc.site.radius_m - 1.0);
        assert!(core.tick().touchdown.is_some(), "touchdown must latch");
        core.ingest(SimIn::Dsky(DskyStateSnapshot {
            mm: "64".into(),
            nav: None,
        }));
        assert!(!core.tick().handover, "handover fired after touchdown");
    }

    #[test]
    fn handover_never_fires_while_frozen() {
        // The freeze pins truth at the PDI point, but nothing structurally
        // stops a scenario whose pinned altitude is already below the gate
        // from firing a handover before ENGINE ON.
        let sc = pdi_scenario();
        let mut core = SimCore::new(&sc, 0.0);
        core.st.pos = core.st.pos.unit().scale(sc.site.radius_m + 10.0);
        core.ingest(SimIn::Dsky(DskyStateSnapshot {
            mm: "64".into(),
            nav: None,
        }));
        assert!(!core.tick().handover, "handover fired during the freeze");
    }

    #[test]
    fn telemetry_reports_the_handover_latch() {
        // Wave 1 lost an investigation to an unobservable value; the
        // handover must be visible in the telemetry stream.
        let sc = pdi_scenario();
        let mut core = SimCore::new(&sc, 0.0);
        engine_on(&mut core);
        core.st.pos = core.st.pos.unit().scale(sc.site.radius_m + 100.0);
        core.ingest(SimIn::Dsky(DskyStateSnapshot {
            mm: "64".into(),
            nav: None,
        }));
        assert!(!core.telemetry().handover, "not fired yet");
        assert!(core.tick().handover);
        assert!(core.telemetry().handover, "latch must reach telemetry");
    }

    #[test]
    fn handover_never_fires_in_hover_mode() {
        let sc = scenario();
        let mut core = SimCore::new(&sc, 0.0);
        engine_on(&mut core);
        core.st.pos = core.st.pos.unit().scale(sc.site.radius_m + 10.0);
        core.ingest(SimIn::Dsky(DskyStateSnapshot {
            mm: "64".into(),
            nav: None,
        }));
        assert!(!core.tick().handover);
    }

    #[test]
    fn closed_hover_with_thrust_pulses() {
        // The Spike-B vertical loop, now through the full 6-DoF core: a
        // proportional controller feeds THRUST DINC Pout/Mout to null the
        // sink rate. (An open-loop fixed command cannot hold hover — fuel
        // burn alone drifts vz ~0.3 m/s over 30 s — so the loop must
        // actually close, which is the point.)
        let sc = scenario();
        let mut core = SimCore::new(&sc, 0.0);
        engine_on(&mut core);
        core.ingest(SimIn::Agc(AgcOutput::ThrustDrive(true)));
        for _ in 0..3000 {
            let up = core.st.pos.unit();
            let vz = core.st.vel.dot(up);
            let grav = eagle_dynamics::state::gravity(core.st.pos).norm();
            // Proportional throttle command: hover thrust minus a term that
            // opposes the sink rate (setting cmd, not accumulating — an
            // accumulating feed would be integral action and oscillate).
            let hover = core.st.mass_kg * grav / THRUST_N_PER_PULSE;
            let target = (hover - 300.0 * vz).round() as i64;
            let delta = target - core.thrust.cmd_pulses;
            let pulse = if delta > 0 {
                ThrustPulse::Pout
            } else {
                ThrustPulse::Mout
            };
            for _ in 0..delta.abs() {
                core.ingest(SimIn::Agc(AgcOutput::ThrustPulse(pulse)));
            }
            core.tick();
        }
        let up = core.st.pos.unit();
        assert!(
            core.st.vel.dot(up).abs() < 0.2,
            "loop failed to hold hover: vz = {}",
            core.st.vel.dot(up)
        );
    }

    #[test]
    fn cdu_and_pipa_packets_flow_and_are_bounded() {
        let sc = scenario();
        let mut core = SimCore::new(&sc, 0.0);
        engine_on(&mut core);
        core.ingest(SimIn::Agc(AgcOutput::ThrustDrive(true)));
        for _ in 0..50 {
            let out = core.tick();
            let pipa = out.to_agc.iter().filter(|p| is_pipa(p)).count();
            assert!(pipa <= 10, "pipa flood: {pipa}");
            assert!(out.to_agc.len() <= 192 + 32 + 10, "packet flood");
        }
    }

    #[test]
    fn rod_schedule_emits_click_trains_at_thresholds() {
        let sc = scenario();
        let mut core = SimCore::new(&sc, 0.0);
        // Drop the truth just above the 400 m step, engine on, no thrust.
        core.st.pos = core.st.pos.unit().scale(sc.site.radius_m + 402.0);
        engine_on(&mut core);
        let mut clicks = 0;
        for _ in 0..4000 {
            let out = core.tick();
            clicks += out.rod_clicks;
            if core.rod_step_idx >= 1 {
                break;
            }
        }
        // 0 → −3 m/s target: round(−3 / 0.3048) = −10 clicks.
        assert_eq!(clicks, -10);
    }

    #[test]
    fn telemetry_every_100ms_and_determinism() {
        let run = || {
            let sc = scenario();
            let mut core = SimCore::new(&sc, 0.0);
            engine_on(&mut core);
            let mut frames = Vec::new();
            for _ in 0..500 {
                if let Some(t) = core.tick().telemetry {
                    frames.push(serde_json::to_string(&t).unwrap());
                }
            }
            frames
        };
        let a = run();
        let b = run();
        assert_eq!(a.len(), 50, "one frame per 10 ticks over 500 ticks");
        assert_eq!(a, b, "telemetry must be deterministic");
    }

    #[test]
    fn hover_gate_is_surface_stationary() {
        let sc = scenario();
        let core = SimCore::new(&sc, 0.0);
        let (vv, vh, _tilt) = core.landing_kinematics();
        assert!(vv < 1e-9, "vertical: {vv}");
        assert!(vh < 1e-9, "surface-relative horizontal must be ~0: {vh}");
    }

    #[test]
    fn miss_distance_zero_above_site_and_tracks_offset() {
        use eagle_dynamics::frames::Rot;
        let sc = scenario();
        let mut core = SimCore::new(&sc, 0.0);
        assert!(
            core.miss_distance_m() < 1.0,
            "start is directly above the site"
        );
        // Same at a nonzero epoch, where mci_to_mcmf is NOT the identity:
        // catches a miss distance computed off the wrong clock, which epoch
        // 0.0 alone cannot see.
        let off_epoch = SimCore::new(&sc, 1234.0);
        assert!(
            off_epoch.miss_distance_m() < 1.0,
            "site datum must track the epoch: {}",
            off_epoch.miss_distance_m()
        );
        // Rotate the truth 1 mrad about an axis ⊥ site: expected arc = r·1e-3.
        let site = sc.site_unit_mcmf();
        let axis = site.cross(V3::<Mcmf>::new(0.0, 0.0, 1.0)).unit();
        let rot: Rot<Mcmf, Mcmf> = Rot::from_axis_angle(axis, 1e-3);
        let pos_mcmf = rot.apply(site).scale(sc.site.radius_m);
        core.st.pos = mci_to_mcmf(core.st.t).inverse().apply(pos_mcmf);
        let m = core.miss_distance_m();
        assert!((m - sc.site.radius_m * 1e-3).abs() < 1.0, "miss {m}");
    }

    #[test]
    fn touchdown_terminates_with_classification() {
        let sc = scenario();
        let mut core = SimCore::new(&sc, 0.0);
        // Start 2 m up, engine on, no thrust → hard/crash impact.
        core.st.pos = core.st.pos.unit().scale(sc.site.radius_m + 2.0);
        engine_on(&mut core);
        let mut td = None;
        for _ in 0..2000 {
            if let Some(t) = core.tick().touchdown {
                td = Some(t);
                break;
            }
        }
        assert!(td.is_some(), "touchdown never latched");
        // Second tick after touchdown must not re-fire.
        let again = core.tick().touchdown;
        assert!(again.is_none(), "touchdown fired twice");
    }

    fn is_pipa(p: &Packet) -> bool {
        // PIPA counter packets are on 037/040/041.
        matches!(p.channel, 0o37..=0o41)
    }

    #[test]
    fn sim_thread_ticks_and_stops_cleanly() {
        let sc = scenario();
        let core = SimCore::new(&sc, 0.0);
        let (_in_tx, in_rx) = std::sync::mpsc::channel::<SimIn>();
        let (agc_tx, _agc_rx) = tokio::sync::mpsc::unbounded_channel::<Packet>();
        let (telem_tx, mut telem_rx) = tokio::sync::broadcast::channel::<String>(256);
        let (event_tx, _event_rx) = tokio::sync::mpsc::unbounded_channel::<SimEvent>();
        let handle = spawn_sim(core, in_rx, agc_tx, telem_tx, event_tx);
        // ~150 ms of 10 ms ticks → ≥ 10 ticks → ≥ 1 telemetry frame.
        std::thread::sleep(std::time::Duration::from_millis(150));
        handle.stop.send(()).unwrap();
        let joined = std::thread::spawn(move || handle.join.join());
        std::thread::sleep(std::time::Duration::from_millis(100));
        assert!(joined.is_finished(), "thread did not join within 100 ms");
        let mut frames = 0;
        while telem_rx.try_recv().is_ok() {
            frames += 1;
        }
        assert!(frames >= 1, "expected >= 1 telemetry frame, got {frames}");
    }
}
