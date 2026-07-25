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
use crate::scenario::Scenario;
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

/// Parse the P66 flight display (V06N60): R2 = HDOTDISP, shown in 0.1 ft/s
/// units (Spike B: R2 "+00756" = 75.6 ft/s). Altitude is not exposed by
/// N60 in a pinned scaling, so `alt_m` stays `None` in Wave 1.
pub fn parse_agc_nav(d: &DskyState) -> Option<AgcNav> {
    let verb: String = d.verb.iter().collect();
    let noun: String = d.noun.iter().collect();
    if verb != "06" || noun != "60" {
        return None;
    }
    let hdot_ms = parse_decimal_register(&d.r2).map(|v| v as f64 * 0.1 * 0.3048);
    Some(AgcNav {
        alt_m: None,
        hdot_ms,
    })
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
    fn phase4_5_dynamics(&mut self) {
        if self.frozen {
            // Advance the clock even while pinned, so telemetry rates
            // (downlink_wps, drift) don't divide accumulated counts by a
            // near-zero t_s at engine-on.
            self.st.t += DT;
            self.sf_body = V3::new(HOVER_ACCEL_MS2, 0.0, 0.0);
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
    rod_tx: tokio::sync::mpsc::UnboundedSender<i32>,
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
                let _ = rod_tx.send(out.rod_clicks);
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

    fn engine_on(core: &mut SimCore) {
        core.ingest(SimIn::Agc(AgcOutput::Engine {
            on: true,
            off: false,
        }));
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
        let (rod_tx, _rod_rx) = tokio::sync::mpsc::unbounded_channel::<i32>();
        let handle = spawn_sim(core, in_rx, agc_tx, telem_tx, rod_tx);
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
