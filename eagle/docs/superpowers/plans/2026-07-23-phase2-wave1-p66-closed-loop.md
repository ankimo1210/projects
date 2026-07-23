# EAGLE Phase 2 Wave 1 — P66 Closed-Loop Descent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Real Luminary099 (in vendored yaAGC) flies a P66 rate-of-descent
landing to soft touchdown against our own 6-DoF physics: sensors (PIPA/CDU)
in, autopilot outputs (RCS jets, engine, THRUST DINC protocol) out, with a
scripted DSKY pad-load + P63-ignition entry and an engineer telemetry board.

**Architecture:** Two new pure crates (`eagle-dynamics`, `eagle-sensors`)
feed a dedicated non-tokio sim thread at 100 Hz wall-paced; the existing
`eagle-runtime` tokio loop keeps owning the yaAGC socket and WebSocket
server and forwards packets both ways. AGC entry is scripted over the DSKY
(V21N01 erasable loads with V01N01 read-back), then V37E63E ignition,
then a forced ATT-HOLD discrete flips GUILDENSTERN into P66. Two live
spike tasks retire the big unknowns (P63 acceptance, THRUST DINC strobe)
against a synthetic hover feed **before** the full physics is built.

**Tech Stack:** Rust (tokio only in eagle-runtime; sim thread is std),
serde + toml (scenario/pad-load manifests), rand_chacha (seeded error
models), React + TypeScript + uPlot (engineer board), vitest, yaAGC socket
protocol (4-byte packets).

## Global Constraints

Copied/derived from the spec (`docs/superpowers/specs/2026-07-22-eagle-phase2-closed-loop-design.md`) and Phase 1 conventions. Every task's requirements implicitly include this section.

- `vendor/` is READ-ONLY. Never patch vendor sources; all adaptations live in our code. Cite vendor paths+lines when semantics are taken from them.
- All AGC channel numbers and erasable addresses are written in octal (`0o…` in Rust, `0…` in docs). Decimal channel literals are a defect.
- yaAGC counter packets: **data field = IncType, NOT a count** — one ±1 pulse per 4-byte packet. IncTypes: 0=PINC, 1=PCDU slow, 2=MINC, 3=MCDU slow, 4=DINC, 0o21=PCDU fast, 0o23=MCDU fast (`vendor/virtualagc/yaAGC/agc_engine.c:1570-1623`).
- Channels 030–033 are **inverted** (0 = signal present) and initialize all-ones (`agc_engine_init.c:255-258`). Write them only via bitmask-then-value packet pairs touching our bits (Phase 1 `pro_key_packets` pattern).
- Integration tests run serially: `cargo test -- --ignored --test-threads=1`. Never start two yaAGC instances in one test binary in parallel. New live tests use AGC ports 19901–19904 (Phase 1 used 19897–19900); runtime default stays 19797, WS 8642.
- Physics step is **RK4, fixed 10 ms, fixed evaluation order**. Sensor error models are seeded (ChaCha) and **default OFF**; acceptance runs are errors-OFF.
- Sim/AGC unit conversion happens exactly once, at the counter codec boundary; SI units everywhere else. Update `docs/agc-channel-map.md` with citations whenever a task pins new channel/counter semantics.
- Scenario/pad-load values carry provenance comments: `historical` / `derived` / `assumed`.
- Freeze-until-engine-on: truth state is pinned (PIPA = pure hover support) until ch 011 bit 13 ENGINE ON is observed; then dynamics run free. (Keeps AVERAGE-G consistent with a hover start.)
- Commit after every green test cycle. Commit messages end with:
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` and
  `Claude-Session: https://claude.ai/code/session_01QUsz5BRQNg3Mey6wR7GrtZ`
- Never stage/commit anything outside `eagle/`.
- Tasks 6 and 7 are **live spikes**: their code/harness steps are binding, their numeric findings (pad-load values, ROD scale, alarm whitelist, timing parameters) are recorded as committed data files + ledger notes, not guessed in advance.

## Reference: vendor-verified I/O semantics

Every implementer MUST re-verify the rows they use (Step-0) against the cited vendor lines before locking tests.

### Counter registers (erasable, fed/read via t-bit packets; channel field = octal address)

| Register | Addr | Direction | Semantics |
|---|---|---|---|
| CDUX/Y/Z | 032/033/034 | in (PCDU/MCDU) | IMU gimbal angles, 360°/32768 per pulse; FIFO rate-limited ~400 cps slow / ~6400 cps fast, depth 128 (`agc_engine.c:1370-1560`) |
| OPTY/OPTX | 035/036 | in | RR trunnion/shaft (idle traffic seen in Phase 1) |
| PIPAX/Y/Z | 037/040/041 | in (PINC/MINC) | ΔV, 0.0585 m/s per pulse; unthrottled (`agc_engine.c:1580-1595`) |
| RHCP/Y/R | 042/043/044 | in | RHC counters via fictitious ch 0166/0167/0170 + ch 013 bits 8-9 latch (`SocketAPI.c:255-268`) |
| INLINK | 045 | in | digital uplink via fictitious ch 0173 (+UPRUPT) (`SocketAPI.c:242-249`) — Wave 2 |
| THRUST | 055 | out via our DINC strobe | `Luminary099/ERASABLE_ASSIGNMENTS.agc:149`; see protocol below |

### THRUST DINC-strobe protocol (we play the throttle-drive electronics)

1. Luminary THROT loads a signed pulse count into 055 and raises ch 014 bit 4 (THRUST DRIVE). We receive the ch 014 write.
2. While last-seen ch 014 bit 4 is set: send DINC packets (`Packet::counter(0o55, 4)`) at ≤ 3200 pps (≤ 32 per 10 ms tick).
3. yaAGC `CounterDINC` answers each DINC on counter channel 055 with data 0o15=POUT (+1 pulse), 0o16=MOUT (−1), 0o17=ZOUT (empty) (`agc_engine.c:1278-1305,1605`).
4. Throttle command accumulates: `cmd_pulses += (POUT − MOUT)`; on ZOUT pause strobing until the next ch 014 bit-4 write (tolerate ZOUT chatter).
5. Thrust scale: `THRUST_N_PER_PULSE = 12.0` N/pulse (assumed, ≈2.7 lbf; **Spike B calibrates and may amend — the committed constant wins**).

### Output channels (LM)

| Ch | Bits | Meaning |
|---|---|---|
| 005 PYJETS | 1-8 | RCS jets Q4U,Q4D,Q3U,Q3D,Q2U,Q2D,Q1U,Q1D (bit1→Q4U … bit8→Q1D) (`Contributed/LM_Simulator/lm_simulator.tcl:814-818`) |
| 006 ROLLJETS | 1-8 | RCS jets Q3A,Q4F,Q1F,Q2A,Q2L,Q3R,Q4R,Q1L (`lm_simulator.tcl:814-818`) |
| 011 | 13 / 14 | ENGINE ON / ENGINE OFF (`Luminary099/INPUT_OUTPUT_CHANNEL_BIT_DESCRIPTIONS.agc:74-75`) |
| 012 | 9,10,11,12 | −pitch, +pitch, −roll, +roll DPS trim gimbal (`…BIT_DESCRIPTIONS.agc:88-91`) |
| 014 | 4 | THRUST DRIVE activity (see protocol) |
| 0174/0175/0176 | — | fictitious: IMU CDU coarse-align drive X/Y/Z; data = `0o40000` dir bit \| delta pulses, 0.043948°/pulse (`agc_engine.c:2405-2422`) |
| 0177 | — | fictitious: gyro fine-align torquing, packed sign/axis+count, 0.617981/3600 °/pulse (`agc_engine.c:2354-2390`) |
| 034/035 | — | downlink words, ~50 wps continuous → our AGC-clock drift proxy (count only, no decode in Wave 1) |

### Input discretes (030–033 inverted, 0=asserted) and ROD

- ch 030: bit3 ENGINE ARMED, bit5 AUTO THROTTLE (clear→P66 path legal; set→P67), bit6 display inertial data, bit9 IMU OPERATE, bit10 LGC has control, bit15 SM temp OK.
- ch 031: bits1-6 RHC ±P/±Y/±R, bits7-12 THC; bit13 ATT-HOLD (assert→GUILDENSTERN starts P66), bit14 AUTO, bit15 out-of-detent. Modes: ATT-HOLD=(b13,b14)=(0,1); AUTO=(1,0); DAP off=(1,1).
- ch 032: bit9 descent engine NOT disabled when 1; bit14 PRO (Phase 1).
- ch 033: bit4 RR data good, bit5 LR range good, bit8 LR vel good (all left deasserted=1 in Wave 1 — no radar).
- LM_Simulator boot values (replicate first, then adjust per spike): wdata(30)=`011110011011001`, wdata(31)=`111111111111111`, wdata(32)=`010001111111111`, wdata(33)=`101111111111110` (`lm_simulator.tcl:570-577`).
- ROD switch: ch 016 bit6 = +1 click (slow descent), bit7 = −1 click; DESCBITS adds ±1 to RODCOUNT per click; RODCOUNT × RODSCAL1 adds to VDGVERT each servicer pass (`LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:958-963,1233-1238`). RODSCALE is a **pad-load** erasable (no in-rope writer).

### Physical constants (single source of truth: `eagle-dynamics/src/constants.rs`)

| Const | Value | Provenance |
|---|---|---|
| MU_MOON | 4.9028e12 m³/s² | historical |
| R_SITE | 1_737_400.0 m | assumed (mean radius) |
| OMEGA_MOON | 2.6617e-6 rad/s | historical |
| PIPA_INCR | 0.0585 m/s/pulse | LM_Simulator `lm_simulator.tcl:145` |
| CDU_INCR | 360/32768 ° /pulse | `lm_simulator.tcl:141-142` |
| COARSE_INCR | 0.043948 °/pulse | `lm_simulator.tcl:143` |
| GYRO_FINE_INCR | 0.617981/3600 °/pulse | `lm_simulator.tcl:144` |
| DPS_MAX_N / DPS_MIN_N | 45040 / 4560 | `lm_simulator.tcl:186-187` |
| DPS_FTP_N | 42500 | assumed (≈94%, cmd>60% snaps here) |
| DPS_VE | 3050 m/s | `lm_simulator.tcl:188` |
| DPS_TAU | 0.3 s (first-order lag) | assumed |
| RCS_THRUST_N / RCS_VE | 445 / 2840 m/s | `lm_simulator.tcl:182-183` |
| RCS_LEVER_M | 1.68 m | derived (LM_Simulator torque model) |
| TRIM_RATE / TRIM_MAX | 0.2 °/s / ±6° | assumed |
| THRUST_N_PER_PULSE | 12.0 N | assumed; Spike B calibrates |
| DINC_MAX_PER_TICK | 32 (=3200 pps) | `agc_engine.c` nominal counter rate |

### Known alarm codes (starter table for the spikes; extend empirically)

| Code (octal) | Meaning |
|---|---|
| 00210 | ISS/IMU not operating |
| 00220 | IMU not aligned — no REFSMMAT |
| 01520 | V37 request rejected |
| 00404 | targets unavailable / bad state (P63 ignition algorithm) |
| 01301 | arcsin/arccos argument out of range (bad state vector / targets) |
| 31201/31202 | executive overflow (1201/1202 — counter flood; must NOT appear) |

Read alarms via scripted `V05N09E` (R1-R3 show the three most recent codes, octal); clear with RSET.

## File structure (all under `eagle/`)

```
runtime/crates/eagle-agc-protocol/src/
  agc_io.rs        NEW  counter builders, output decoder, discrete/ROD builders
  words.rs         NEW  one's-complement SP/DP encode/decode + B-scaling + octal fmt
runtime/crates/eagle-dynamics/     NEW pure crate
  src/lib.rs, frames.rs, constants.rs, state.rs, forces.rs, rk4.rs, touchdown.rs
runtime/crates/eagle-sensors/      NEW pure crate
  src/lib.rs, pipa.rs, imu.rs, errors.rs
runtime/apps/eagle-runtime/src/
  script.rs        NEW  DSKY scripting engine (async, watch<DskyState>)
  padload.rs       NEW  symtab parse + manifest load + resolve
  bin/padload_gen.rs NEW  scenario→manifest generator CLI
  scenario.rs      NEW  TOML scenario loader
  sim.rs           NEW  SimCore (pure) + sim thread shell
  runner.rs        NEW  ScenarioRunner (productized spike choreography)
  main.rs          MOD  watch<DskyState>, --scenario mode
  server.rs        MOD  telemetry broadcast, ClientMsg::Rod
runtime/crates/eagle-schema/src/lib.rs  MOD  SCHEMA_VERSION=2, TelemetryMsg
scenarios/p66-gate.toml            NEW  + padload manifest TOML (spike-calibrated)
client/src/telemetry/              NEW  TelemetryPage, useTelemetryBuffer, charts
tests: live_spike_p63.rs, live_spike_p66.rs, live_p66_descent.rs (+ unit tests per crate)
docs/coordinate-frames.md          NEW
```

---

### Task 1: AGC I/O protocol extension (`agc_io.rs`)

**Files:**
- Create: `runtime/crates/eagle-agc-protocol/src/agc_io.rs`
- Modify: `runtime/crates/eagle-agc-protocol/src/lib.rs` (add `pub mod agc_io;`)

**Interfaces:**
- Consumes: `Packet`, `PacketKind` from `packet.rs` (existing).
- Produces (used by Tasks 6,7,10,13,14):
  - `pub enum PipaAxis { X, Y, Z }`, `pub enum CduAxis { X, Y, Z }`
  - `pub fn pipa_pulse(axis: PipaAxis, positive: bool) -> Packet`
  - `pub fn cdu_pulse(axis: CduAxis, positive: bool, fast: bool) -> Packet`
  - `pub fn thrust_dinc() -> Packet`
  - `pub fn rod_click(up: bool) -> (Packet, Packet)` — (press, release) for ch 016 bit6/bit7; caller sends release ≥1 tick later
  - `pub fn discrete_write(channel: u8, bits_high: u16, bits_low: u16) -> [Packet; 2]` — bitmask packet covering `bits_high|bits_low`, then value packet setting exactly `bits_high`
  - `pub enum AgcOutput { Jets5 { mask: u8 }, Jets6 { mask: u8 }, Engine { on: bool, off: bool }, Trim { minus_pitch: bool, plus_pitch: bool, minus_roll: bool, plus_roll: bool }, ThrustDrive(bool), ThrustPulse(ThrustPulse), CoarseAlign { axis: CduAxis, positive: bool, pulses: u16 }, Gyro { raw: u16 }, Downlink, Other(Packet) }`
  - `pub enum ThrustPulse { Pout, Mout, Zout }`
  - `pub fn decode_output(p: &Packet) -> AgcOutput`

**Step 0: Vendor verification (mandatory, no code yet).** Re-read and confirm, recording citations in the commit message:
- IncType dispatch and values: `vendor/virtualagc/yaAGC/agc_engine.c:1570-1623`; counter channel = 0x80|addr assembled from the packet: `yaAGC/SocketAPI.c:219-231`, `yaAGC/agc_utilities.c:144-147`. Confirm our `Packet::counter(ch, data)` t-bit encoding corresponds (t-bit in byte0 bit4 == the 0x80 of the 8-bit channel).
- POUT/MOUT/ZOUT emission values 0o15/0o16/0o17: `agc_engine.c:1278-1305`.
- Coarse-align data layout `0o40000 | delta`: `agc_engine.c:2405-2422`. Gyro packing: `agc_engine.c:2354-2390` (decode as raw u16 in Wave 1).
- Jet bit maps: `Contributed/LM_Simulator/lm_simulator.tcl:814-818`. Engine/trim bits: `Luminary099/INPUT_OUTPUT_CHANNEL_BIT_DESCRIPTIONS.agc:59-94`.

- [ ] **Step 1: Write failing tests** in `agc_io.rs` `#[cfg(test)]`:

```rust
#[test]
fn pipa_pulse_packets() {
    // PINC to PIPAX (037): counter packet, channel field = octal address, data = IncType 0
    assert_eq!(pipa_pulse(PipaAxis::X, true),
               Packet::counter(0o37, 0).unwrap());
    // MINC to PIPAZ (041): IncType 2
    assert_eq!(pipa_pulse(PipaAxis::Z, false),
               Packet::counter(0o41, 2).unwrap());
}

#[test]
fn cdu_pulse_packets() {
    assert_eq!(cdu_pulse(CduAxis::X, true, false), Packet::counter(0o32, 1).unwrap());
    assert_eq!(cdu_pulse(CduAxis::Y, false, false), Packet::counter(0o33, 3).unwrap());
    assert_eq!(cdu_pulse(CduAxis::Z, true, true), Packet::counter(0o34, 0o21).unwrap());
    assert_eq!(cdu_pulse(CduAxis::Z, false, true), Packet::counter(0o34, 0o23).unwrap());
}

#[test]
fn thrust_dinc_packet() {
    assert_eq!(thrust_dinc(), Packet::counter(0o55, 4).unwrap());
}

#[test]
fn rod_click_press_release() {
    let (press, release) = rod_click(true);   // bit 6 = +1 click (slow descent)
    assert_eq!(press, Packet::io(0o16, 1 << 5).unwrap());
    assert_eq!(release, Packet::io(0o16, 0).unwrap());
    let (press, _) = rod_click(false);        // bit 7 = −1 click
    assert_eq!(press, Packet::io(0o16, 1 << 6).unwrap());
}

#[test]
fn discrete_write_bitmask_then_value() {
    // assert ch030 bit5 (write 0), deassert bit3 (write 1): mask covers both bits
    let [mask, value] = discrete_write(0o30, 1 << 2, 1 << 4);
    assert_eq!(mask, Packet::bitmask(0o30, (1 << 2) | (1 << 4)).unwrap());
    assert_eq!(value, Packet::io(0o30, 1 << 2).unwrap());
}

#[test]
fn decode_autopilot_outputs() {
    assert!(matches!(decode_output(&Packet::io(0o5, 0b1010_0001).unwrap()),
        AgcOutput::Jets5 { mask: 0b1010_0001 }));
    assert!(matches!(decode_output(&Packet::io(0o11, 1 << 12).unwrap()),
        AgcOutput::Engine { on: true, off: false }));
    assert!(matches!(decode_output(&Packet::io(0o12, 1 << 9).unwrap()),
        AgcOutput::Trim { plus_pitch: true, minus_pitch: false, .. }));
    assert!(matches!(decode_output(&Packet::io(0o14, 1 << 3).unwrap()),
        AgcOutput::ThrustDrive(true)));
    assert!(matches!(decode_output(&Packet::counter(0o55, 0o15).unwrap()),
        AgcOutput::ThrustPulse(ThrustPulse::Pout)));
    assert!(matches!(decode_output(&Packet::counter(0o55, 0o16).unwrap()),
        AgcOutput::ThrustPulse(ThrustPulse::Mout)));
    // coarse align X: fictitious channel 0174 (fits in 7 bits: 0o174 = 124),
    // direction bit 0o40000, 24 pulses — direction polarity pinned in Step 0
    assert!(matches!(decode_output(&Packet::io(0o174, 0o40000 | 24).unwrap()),
        AgcOutput::CoarseAlign { axis: CduAxis::X, pulses: 24, .. }));
    assert!(matches!(decode_output(&Packet::io(0o177, 0o1234).unwrap()),
        AgcOutput::Gyro { raw: 0o1234 }));
    assert!(matches!(decode_output(&Packet::io(0o34, 0).unwrap()), AgcOutput::Downlink));
}
```

- [ ] **Step 2: Run tests, verify failure** — `cd runtime && cargo test -p eagle-agc-protocol agc_io` → FAIL (module missing).

- [ ] **Step 3: Implement `agc_io.rs`:**

```rust
//! LM autopilot I/O: counter builders, output decoding, discrete writes.
//! Semantics cited from vendor sources — see docs/agc-channel-map.md.
use crate::packet::{Packet, PacketKind};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PipaAxis { X, Y, Z }
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CduAxis { X, Y, Z }
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ThrustPulse { Pout, Mout, Zout }

pub const INC_PINC: u16 = 0;
pub const INC_PCDU: u16 = 1;
pub const INC_MINC: u16 = 2;
pub const INC_MCDU: u16 = 3;
pub const INC_DINC: u16 = 4;
pub const INC_PCDU_FAST: u16 = 0o21;
pub const INC_MCDU_FAST: u16 = 0o23;

const PIPA_ADDR: [u8; 3] = [0o37, 0o40, 0o41];
const CDU_ADDR: [u8; 3] = [0o32, 0o33, 0o34];
pub const THRUST_ADDR: u8 = 0o55;

pub fn pipa_pulse(axis: PipaAxis, positive: bool) -> Packet {
    let inc = if positive { INC_PINC } else { INC_MINC };
    Packet::counter(PIPA_ADDR[axis as usize], inc).expect("static packet")
}

pub fn cdu_pulse(axis: CduAxis, positive: bool, fast: bool) -> Packet {
    let inc = match (positive, fast) {
        (true, false) => INC_PCDU,
        (false, false) => INC_MCDU,
        (true, true) => INC_PCDU_FAST,
        (false, true) => INC_MCDU_FAST,
    };
    Packet::counter(CDU_ADDR[axis as usize], inc).expect("static packet")
}

pub fn thrust_dinc() -> Packet {
    Packet::counter(THRUST_ADDR, INC_DINC).expect("static packet")
}

/// ROD switch click on ch 016: bit6 (+1, slow descent) / bit7 (−1).
/// Returns (press, release); send release at least one tick later so the
/// channel-change interrupt (MARKRUPT→DESCBITS) latches the click.
pub fn rod_click(up: bool) -> (Packet, Packet) {
    let bit = if up { 1 << 5 } else { 1 << 6 };
    (Packet::io(0o16, bit).expect("static"), Packet::io(0o16, 0).expect("static"))
}

/// Bitmask-then-value pair for (possibly inverted) discrete channels.
/// `bits_high` are driven to 1, `bits_low` to 0; untouched bits keep their
/// current value (that is what the bitmask packet guarantees).
pub fn discrete_write(channel: u8, bits_high: u16, bits_low: u16) -> [Packet; 2] {
    [
        Packet::bitmask(channel, bits_high | bits_low).expect("mask"),
        Packet::io(channel, bits_high).expect("value"),
    ]
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AgcOutput {
    Jets5 { mask: u8 },
    Jets6 { mask: u8 },
    Engine { on: bool, off: bool },
    Trim { minus_pitch: bool, plus_pitch: bool, minus_roll: bool, plus_roll: bool },
    ThrustDrive(bool),
    ThrustPulse(ThrustPulse),
    CoarseAlign { axis: CduAxis, positive: bool, pulses: u16 },
    Gyro { raw: u16 },
    Downlink,
    Other,
}

pub fn decode_output(p: &Packet) -> AgcOutput {
    if p.kind == PacketKind::Counter && p.channel == THRUST_ADDR {
        return match p.data {
            0o15 => AgcOutput::ThrustPulse(ThrustPulse::Pout),
            0o16 => AgcOutput::ThrustPulse(ThrustPulse::Mout),
            0o17 => AgcOutput::ThrustPulse(ThrustPulse::Zout),
            _ => AgcOutput::Other,
        };
    }
    match p.channel {
        0o5 => AgcOutput::Jets5 { mask: (p.data & 0xFF) as u8 },
        0o6 => AgcOutput::Jets6 { mask: (p.data & 0xFF) as u8 },
        0o11 => AgcOutput::Engine {
            on: p.data & (1 << 12) != 0,
            off: p.data & (1 << 13) != 0,
        },
        0o12 => AgcOutput::Trim {
            minus_pitch: p.data & (1 << 8) != 0,
            plus_pitch: p.data & (1 << 9) != 0,
            minus_roll: p.data & (1 << 10) != 0,
            plus_roll: p.data & (1 << 11) != 0,
        },
        0o14 => AgcOutput::ThrustDrive(p.data & (1 << 3) != 0),
        0o174 | 0o175 | 0o176 => AgcOutput::CoarseAlign {
            axis: match p.channel { 0o174 => CduAxis::X, 0o175 => CduAxis::Y, _ => CduAxis::Z },
            positive: p.data & 0o40000 == 0,
            pulses: p.data & 0o37777,
        },
        0o177 => AgcOutput::Gyro { raw: p.data },
        0o34 | 0o35 => AgcOutput::Downlink,
        _ => AgcOutput::Other,
    }
}
```

Note on `CoarseAlign.positive`: the direction encoding of bit 0o40000 (set = negative vs positive) must be pinned in Step 0 from `agc_engine.c:1667-1674` (`BurstOutput` Direction handling); fix the test to whatever the vendor source says and cite it in the commit.

- [ ] **Step 4: Run tests, verify pass** — `cargo test -p eagle-agc-protocol` → all PASS (existing packet tests still green).

- [ ] **Step 5: Update `docs/agc-channel-map.md`** — append a "Counters and autopilot outputs (Phase 2)" section: the two reference tables from this plan's header (counter registers, output channels, THRUST protocol), with the vendor citations. Keep octal formatting.

- [ ] **Step 6: Commit** — `git add runtime/crates/eagle-agc-protocol docs/agc-channel-map.md && git commit -m "feat(protocol): LM counter builders, autopilot output decoder, discrete writes"` (+ trailer).

---

### Task 2: AGC word encoding (`words.rs`)

**Files:**
- Create: `runtime/crates/eagle-agc-protocol/src/words.rs`
- Modify: `runtime/crates/eagle-agc-protocol/src/lib.rs` (add `pub mod words;`)

**Interfaces:**
- Produces (used by Tasks 5, 6):
  - `pub fn sp_encode(pulses: i16) -> u16` / `pub fn sp_decode(word: u16) -> i16` — 15-bit one's complement (−0 normalized to +0 on decode)
  - `pub fn dp_encode(pulses: i64) -> [u16; 2]` / `pub fn dp_decode(w: [u16; 2]) -> i64` — AGC double precision: value = hi·2^14 + lo, both words one's complement, same sign, |hi|<2^14, |lo|<2^14
  - `pub fn to_pulses(value: f64, b_scale: i32, dp: bool) -> i64` — pulses = round(value / 2^(b_scale − 14)) for SP, round(value / 2^(b_scale − 28)) for DP; b_scale is the AGC "B" exponent (value magnitude < 2^b_scale)
  - `pub fn octal5(word: u16) -> String` — 5-digit zero-padded octal for DSKY typing

**AGC number background for the implementer:** AGC words are 15-bit one's
complement. SP range ±(2^14−1). A variable "scaled B_n" stores
`value / 2^n` as a fraction of 2^14 (SP) or 2^28 (DP): one pulse (LSB) =
2^(n−14) (SP) or 2^(n−28) (DP) in physical units. DP = two consecutive
words: value = hi·2^14 + lo with both words carrying the value's sign
(canonical form; mixed signs are legal in the AGC but we never emit them).

- [ ] **Step 1: Write failing tests** (`#[cfg(test)]` in `words.rs`):

```rust
#[test]
fn sp_ones_complement() {
    assert_eq!(sp_encode(0), 0);
    assert_eq!(sp_encode(1), 1);
    assert_eq!(sp_encode(-1), 0o77776);
    assert_eq!(sp_encode(16383), 0o37777);
    assert_eq!(sp_encode(-16383), 0o40000);
    for v in [-16383i16, -1, 0, 1, 42, 16383] {
        assert_eq!(sp_decode(sp_encode(v)), v);
    }
    assert_eq!(sp_decode(0o77777), 0); // −0 → +0
}

#[test]
fn dp_split_and_sign() {
    assert_eq!(dp_encode(0), [0, 0]);
    assert_eq!(dp_encode(1), [0, 1]);
    assert_eq!(dp_encode(16384), [1, 0]);            // 2^14
    assert_eq!(dp_encode(16385), [1, 1]);
    assert_eq!(dp_encode(-16385), [0o77776, 0o77776]); // both words negative
    let max = (1i64 << 28) - 1;
    for v in [-max, -16385, -1, 0, 1, 16383, 16384, max] {
        assert_eq!(dp_decode(dp_encode(v)), v, "v={v}");
    }
}

#[test]
fn physical_to_pulses() {
    // SP scaled B14: 1 pulse = 1 unit
    assert_eq!(to_pulses(42.0, 14, false), 42);
    // SP scaled B0: value is a fraction of 1, pulse = 2^-14
    assert_eq!(to_pulses(0.5, 0, false), 8192);
    // DP scaled B28: 1 pulse = 1 unit
    assert_eq!(to_pulses(-123456.0, 28, true), -123456);
    // DP scaled B27 (e.g. lunar position in meters): pulse = 2^-1 m
    assert_eq!(to_pulses(1_000_000.0, 27, true), 2_000_000);
}

#[test]
fn octal_formatting() {
    assert_eq!(octal5(0), "00000");
    assert_eq!(octal5(0o77776), "77776");
    assert_eq!(octal5(0o1234), "01234");
}
```

- [ ] **Step 2: Run, verify FAIL** — `cargo test -p eagle-agc-protocol words` → module missing.

- [ ] **Step 3: Implement:**

```rust
//! AGC 15-bit one's-complement word encoding (SP/DP) and B-scaling.

pub fn sp_encode(pulses: i16) -> u16 {
    debug_assert!(pulses.unsigned_abs() < (1 << 14));
    if pulses >= 0 { pulses as u16 } else { (!((-pulses) as u16)) & 0o77777 }
}

pub fn sp_decode(word: u16) -> i16 {
    let word = word & 0o77777;
    if word & 0o40000 == 0 { word as i16 }
    else {
        let mag = (!word) & 0o37777;
        -(mag as i16)
    }
}

pub fn dp_encode(pulses: i64) -> [u16; 2] {
    debug_assert!(pulses.unsigned_abs() < (1 << 28));
    let neg = pulses < 0;
    let mag = pulses.unsigned_abs();
    let (hi, lo) = ((mag >> 14) as i16, (mag & 0x3FFF) as i16);
    let (hi, lo) = if neg { (-hi, -lo) } else { (hi, lo) };
    [sp_encode(hi), sp_encode(lo)]
}

pub fn dp_decode(w: [u16; 2]) -> i64 {
    (sp_decode(w[0]) as i64) * (1 << 14) + sp_decode(w[1]) as i64
}

/// value → integer pulses for a variable scaled B`b_scale`.
/// SP LSB = 2^(b−14), DP LSB = 2^(b−28) physical units.
pub fn to_pulses(value: f64, b_scale: i32, dp: bool) -> i64 {
    let lsb_exp = b_scale - if dp { 28 } else { 14 };
    (value / (lsb_exp as f64).exp2()).round() as i64
}

pub fn octal5(word: u16) -> String { format!("{:05o}", word & 0o77777) }
```

Note: `(lsb_exp as f64).exp2()` — use `f64::powi(2.0, lsb_exp)` if exp2 reads awkwardly; either is fine, keep one.

- [ ] **Step 4: Run, verify PASS** — `cargo test -p eagle-agc-protocol` → PASS.

- [ ] **Step 5: Commit** — `git commit -m "feat(protocol): AGC one's-complement SP/DP words and B-scaling"` (+ trailer).

---

### Task 3: `eagle-dynamics` crate — typed frames and math

**Files:**
- Create: `runtime/crates/eagle-dynamics/Cargo.toml`, `src/lib.rs`, `src/frames.rs`, `src/constants.rs`
- Create: `docs/coordinate-frames.md`
- Modify: `runtime/Cargo.toml` (workspace members += `"crates/eagle-dynamics"`)

**Interfaces:**
- Produces (used by Tasks 5, 8-13):
  - Marker frames: `Mci`, `Mcmf`, `Lsite`, `Body`, `Sm` (zero-sized types implementing `pub trait Frame`)
  - `pub struct V3<F: Frame> { pub x: f64, pub y: f64, pub z: f64, _f: PhantomData<F> }` with `new`, Add/Sub/Neg, `scale(f64)`, `dot`, `cross`, `norm`, `unit`
  - `pub struct Rot<A: Frame, B: Frame>` (unit quaternion): `identity()`, `from_axis_angle(axis: V3<A>, rad: f64) -> Rot<A, A>` plus `retag::<B>()` escape hatch used only inside constructors, `apply(V3<A>) -> V3<B>`, `inverse() -> Rot<B, A>`, `then<C>(Rot<B, C>) -> Rot<A, C>`, `normalize()`, `pub fn raw(&self) -> [f64; 4]`
  - `pub fn mci_to_mcmf(t_s: f64) -> Rot<Mci, Mcmf>` (rotation about the lunar pole, OMEGA_MOON·t)
  - `pub fn mcmf_to_lsite(site_unit_mcmf: V3<Mcmf>) -> Rot<Mcmf, Lsite>` (ENU: x=East, y=North, z=Up)
  - `src/constants.rs`: every constant from the plan-header table, `pub const`, one per line, with the provenance comment.

Design rule (spec §3): no anonymous `[f64; 3]` vectors cross a function boundary in any crate; frames are enforced at compile time. Internal quaternion storage is a private `[f64; 4]`.

- [ ] **Step 1: Crate skeleton.** `runtime/crates/eagle-dynamics/Cargo.toml`:

```toml
[package]
name = "eagle-dynamics"
version = "0.1.0"
edition = "2021"

[dependencies]
```

Add to workspace members. `src/lib.rs`: `pub mod frames; pub mod constants;` (later tasks append modules).

- [ ] **Step 2: Write failing tests** in `frames.rs`:

```rust
#[cfg(test)]
mod tests {
    use super::*;
    fn close(a: f64, b: f64) -> bool { (a - b).abs() < 1e-12 }

    #[test]
    fn rotation_about_z_maps_x_to_y() {
        let q: Rot<Mci, Mci> =
            Rot::from_axis_angle(V3::new(0.0, 0.0, 1.0), std::f64::consts::FRAC_PI_2);
        let v = q.apply(V3::<Mci>::new(1.0, 0.0, 0.0));
        assert!(close(v.x, 0.0) && close(v.y, 1.0) && close(v.z, 0.0));
    }

    #[test]
    fn compose_and_inverse_round_trip() {
        let a: Rot<Mci, Mci> =
            Rot::from_axis_angle(V3::new(0.0, 1.0, 0.0), 0.7);
        let v = V3::<Mci>::new(1.0, 2.0, 3.0);
        let w = a.inverse().apply(a.apply(v));
        assert!(close(w.x, 1.0) && close(w.y, 2.0) && close(w.z, 3.0));
    }

    #[test]
    fn mcmf_rotates_with_moon() {
        use crate::constants::OMEGA_MOON;
        let t = 1000.0;
        let x_mcmf = mci_to_mcmf(t).apply(V3::<Mci>::new(1.0, 0.0, 0.0));
        assert!(close(x_mcmf.x, (OMEGA_MOON * t).cos()));
        assert!(close(x_mcmf.y, -(OMEGA_MOON * t).sin()));
    }

    #[test]
    fn lsite_enu_is_orthonormal_up_points_out() {
        let site = V3::<Mcmf>::new(0.6, 0.48, 0.64).unit();
        let r = mcmf_to_lsite(site);
        let up = r.apply(site); // site direction must map to +z (Up)
        assert!(close(up.x, 0.0) && close(up.y, 0.0) && close(up.z, 1.0));
    }

    #[test]
    fn cross_and_dot() {
        let x = V3::<Body>::new(1.0, 0.0, 0.0);
        let y = V3::<Body>::new(0.0, 1.0, 0.0);
        let z = x.cross(y);
        assert!(close(z.z, 1.0) && close(x.dot(y), 0.0));
    }
}
```

- [ ] **Step 3: Run, verify FAIL** — `cargo test -p eagle-dynamics` → compile error.

- [ ] **Step 4: Implement `frames.rs`** (complete):

```rust
//! Typed coordinate frames (spec §3). A `V3<F>` is a vector expressed in
//! frame F; a `Rot<A, B>` re-expresses A-frame coordinates in frame B.
use std::marker::PhantomData;
use std::ops::{Add, Neg, Sub};

pub trait Frame: Copy + 'static {}
macro_rules! frame { ($($n:ident),*) => { $(
    #[derive(Debug, Clone, Copy, PartialEq, Eq)] pub struct $n;
    impl Frame for $n {}
)* } }
frame!(Mci, Mcmf, Lsite, Body, Sm);

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct V3<F: Frame> { pub x: f64, pub y: f64, pub z: f64, _f: PhantomData<F> }

impl<F: Frame> V3<F> {
    pub fn new(x: f64, y: f64, z: f64) -> Self { Self { x, y, z, _f: PhantomData } }
    pub fn zero() -> Self { Self::new(0.0, 0.0, 0.0) }
    pub fn scale(self, k: f64) -> Self { Self::new(self.x * k, self.y * k, self.z * k) }
    pub fn dot(self, o: Self) -> f64 { self.x * o.x + self.y * o.y + self.z * o.z }
    pub fn cross(self, o: Self) -> Self {
        Self::new(self.y * o.z - self.z * o.y,
                  self.z * o.x - self.x * o.z,
                  self.x * o.y - self.y * o.x)
    }
    pub fn norm(self) -> f64 { self.dot(self).sqrt() }
    pub fn unit(self) -> Self { self.scale(1.0 / self.norm()) }
}
impl<F: Frame> Add for V3<F> { type Output = Self;
    fn add(self, o: Self) -> Self { Self::new(self.x + o.x, self.y + o.y, self.z + o.z) } }
impl<F: Frame> Sub for V3<F> { type Output = Self;
    fn sub(self, o: Self) -> Self { Self::new(self.x - o.x, self.y - o.y, self.z - o.z) } }
impl<F: Frame> Neg for V3<F> { type Output = Self;
    fn neg(self) -> Self { self.scale(-1.0) } }

/// Unit quaternion [w, x, y, z] taking A-frame coordinates to B-frame.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Rot<A: Frame, B: Frame> { q: [f64; 4], _f: PhantomData<(A, B)> }

fn qmul(a: [f64; 4], b: [f64; 4]) -> [f64; 4] {
    [a[0]*b[0] - a[1]*b[1] - a[2]*b[2] - a[3]*b[3],
     a[0]*b[1] + a[1]*b[0] + a[2]*b[3] - a[3]*b[2],
     a[0]*b[2] - a[1]*b[3] + a[2]*b[0] + a[3]*b[1],
     a[0]*b[3] + a[1]*b[2] - a[2]*b[1] + a[3]*b[0]]
}

impl<A: Frame, B: Frame> Rot<A, B> {
    pub fn from_raw(q: [f64; 4]) -> Self { Self { q, _f: PhantomData }.normalize() }
    pub fn raw(&self) -> [f64; 4] { self.q }
    pub fn identity() -> Self { Self { q: [1.0, 0.0, 0.0, 0.0], _f: PhantomData } }
    pub fn normalize(mut self) -> Self {
        let n = self.q.iter().map(|v| v * v).sum::<f64>().sqrt();
        for v in &mut self.q { *v /= n; }
        self
    }
    pub fn apply(&self, v: V3<A>) -> V3<B> {
        let p = [0.0, v.x, v.y, v.z];
        let qc = [self.q[0], -self.q[1], -self.q[2], -self.q[3]];
        let r = qmul(qmul(self.q, p), qc);
        V3::new(r[1], r[2], r[3])
    }
    pub fn inverse(&self) -> Rot<B, A> {
        Rot { q: [self.q[0], -self.q[1], -self.q[2], -self.q[3]], _f: PhantomData }
    }
    pub fn then<C: Frame>(&self, next: Rot<B, C>) -> Rot<A, C> {
        Rot { q: qmul(next.q, self.q), _f: PhantomData }.normalize()
    }
}

impl<A: Frame> Rot<A, A> {
    pub fn from_axis_angle(axis: V3<A>, rad: f64) -> Self {
        let u = axis.unit();
        let (s, c) = (rad / 2.0).sin_cos();
        Self { q: [c, u.x * s, u.y * s, u.z * s], _f: PhantomData }
    }
}

/// Retag an A→A rotation as A→B. Only for frame constructors in this module
/// and in eagle-sensors' REFSMMAT code — never in application logic.
pub fn retag<A: Frame, B: Frame, C: Frame, D: Frame>(r: Rot<A, B>) -> Rot<C, D> {
    Rot { q: r.q, _f: PhantomData }
}

pub fn mci_to_mcmf(t_s: f64) -> Rot<Mci, Mcmf> {
    let r: Rot<Mci, Mci> =
        Rot::from_axis_angle(V3::new(0.0, 0.0, 1.0), -crate::constants::OMEGA_MOON * t_s);
    retag(r)
}

/// ENU basis at a site: rows East, North, Up as a rotation matrix → quaternion.
pub fn mcmf_to_lsite(site_unit_mcmf: V3<Mcmf>) -> Rot<Mcmf, Lsite> {
    let up = site_unit_mcmf.unit();
    let pole = V3::<Mcmf>::new(0.0, 0.0, 1.0);
    let east = pole.cross(up).unit();
    let north = up.cross(east);
    // rotation matrix with rows east/north/up → quaternion (standard conversion)
    let m = [[east.x, east.y, east.z], [north.x, north.y, north.z], [up.x, up.y, up.z]];
    let tr = m[0][0] + m[1][1] + m[2][2];
    let q = if tr > 0.0 {
        let s = (tr + 1.0).sqrt() * 2.0;
        [0.25 * s, (m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s]
    } else if m[0][0] > m[1][1] && m[0][0] > m[2][2] {
        let s = (1.0 + m[0][0] - m[1][1] - m[2][2]).sqrt() * 2.0;
        [(m[2][1] - m[1][2]) / s, 0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s]
    } else if m[1][1] > m[2][2] {
        let s = (1.0 + m[1][1] - m[0][0] - m[2][2]).sqrt() * 2.0;
        [(m[0][2] - m[2][0]) / s, (m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s]
    } else {
        let s = (1.0 + m[2][2] - m[0][0] - m[1][1]).sqrt() * 2.0;
        [(m[1][0] - m[0][1]) / s, (m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s]
    };
    Rot::from_raw(q)
}
```

Caveat for the implementer: the ENU test asserts `apply(site) == +z`; if your matrix→quaternion convention lands transposed, the test catches it — fix the convention, not the test.

- [ ] **Step 5: `constants.rs`** — transcribe the plan-header constants table verbatim, e.g.:

```rust
/// Lunar gravitational parameter, m^3/s^2. Provenance: historical.
pub const MU_MOON: f64 = 4.9028e12;
/// Landing-site radius, m. Provenance: assumed (mean lunar radius).
pub const R_SITE: f64 = 1_737_400.0;
/// Lunar sidereal rotation rate, rad/s. Provenance: historical.
pub const OMEGA_MOON: f64 = 2.6617e-6;
/// PIPA ΔV per pulse, m/s. Provenance: LM_Simulator lm_simulator.tcl:145.
pub const PIPA_INCR: f64 = 0.0585;
/// CDU angle per pulse, degrees. Provenance: lm_simulator.tcl:141-142.
pub const CDU_INCR_DEG: f64 = 360.0 / 32768.0;
/// IMU coarse-align pulse, degrees. Provenance: lm_simulator.tcl:143.
pub const COARSE_INCR_DEG: f64 = 0.043948;
/// Gyro fine-align pulse, degrees. Provenance: lm_simulator.tcl:144.
pub const GYRO_FINE_INCR_DEG: f64 = 0.617981 / 3600.0;
pub const DPS_MAX_N: f64 = 45040.0;
pub const DPS_MIN_N: f64 = 4560.0;
/// Fixed throttle point: commands above 60% snap here. Provenance: assumed.
pub const DPS_FTP_N: f64 = 42500.0;
/// DPS effective exhaust velocity, m/s. Provenance: lm_simulator.tcl:188.
pub const DPS_VE: f64 = 3050.0;
/// DPS first-order throttle lag, s. Provenance: assumed.
pub const DPS_TAU: f64 = 0.3;
pub const RCS_THRUST_N: f64 = 445.0;
pub const RCS_VE: f64 = 2840.0;
/// RCS torque lever arm, m. Provenance: derived from LM_Simulator.
pub const RCS_LEVER_M: f64 = 1.68;
pub const TRIM_RATE_DEG_S: f64 = 0.2;
pub const TRIM_MAX_DEG: f64 = 6.0;
/// DPS thrust per THRUST-counter pulse, N. Provenance: assumed (≈2.7 lbf);
/// Spike B (Task 7) calibrates — update here if measurement disagrees.
pub const THRUST_N_PER_PULSE: f64 = 12.0;
/// Max DINC strobes per 10 ms tick (3200 pps nominal).
pub const DINC_MAX_PER_TICK: u32 = 32;
/// Physics step, seconds (spec: RK4 fixed 10 ms).
pub const DT: f64 = 0.010;
```

- [ ] **Step 6: Run, verify PASS** — `cargo test -p eagle-dynamics` → PASS.

- [ ] **Step 7: Write `docs/coordinate-frames.md`** — the spec §3 frame table (MCI/MCMF/LSITE/BODY/SM roles), the conventions fixed here: MCI z = lunar pole; MCMF = MCI rotated by OMEGA_MOON·t; LSITE = ENU (x East, y North, z Up); BODY: +X = thrust axis (up through the overhead hatch), +Z forward out the windows, +Y completes right-handed; SM = stable member, defined at scenario start ≡ initial BODY attitude (so gimbal angles and yaAGC's zeroed CDU counters agree at t0); AGC-unit conversions happen only at the counter codec (PIPA/CDU/THRUST scale constants, cited).

- [ ] **Step 8: Commit** — `git commit -m "feat(dynamics): typed frames, vectors, rotations, physical constants"` (+ trailer).

---

### Task 4: DSKY scripting harness (`script.rs` + watch refactor)

**Files:**
- Create: `runtime/apps/eagle-runtime/src/script.rs`
- Modify: `runtime/apps/eagle-runtime/src/lib.rs` (add `pub mod script;`)
- Modify: `runtime/apps/eagle-runtime/src/main.rs` (publish `watch::Receiver<DskyState>`)
- Test: unit tests in `script.rs`; live smoke in `runtime/apps/eagle-runtime/tests/live_script.rs`

**Interfaces:**
- Consumes: `DskyKey` (has `from_name(&str)` and `packet()`), `pro_key_packets(bool)`, `DskyState` (+ `apply(&Packet) -> bool`), `Packet`.
- Produces (used by Tasks 6, 7, 14):
  - `pub struct DskyScript { … }` with `pub fn new(tx: mpsc::UnboundedSender<Packet>, rx: watch::Receiver<DskyState>) -> Self`
  - `pub async fn keys(&mut self, seq: &str) -> Result<()>` — token chars: `V`=VERB, `N`=NOUN, `E`=ENTR, `C`=CLR, `K`=KEY REL, `R`=RSET, `+`, `-`, `0`-`9`; 80 ms between keys
  - `pub async fn pro(&mut self)` — press+release with 150 ms hold
  - `pub async fn wait(&mut self, timeout: Duration, pred: impl Fn(&DskyState) -> bool) -> Result<DskyState>`
  - `pub async fn wait_flash(&mut self, verb: &str, noun: &str) -> Result<()>` / `pub async fn wait_prog(&mut self, mm: &str) -> Result<()>`
  - `pub async fn load_erasable(&mut self, ecadr: u16, word: u16) -> Result<()>` (V21N01, then read-back verify)
  - `pub async fn read_erasable(&mut self, ecadr: u16) -> Result<u16>` (V01N01)
  - `pub async fn alarm_codes(&mut self) -> Result<[u16; 3]>` (V05N09)
  - `pub fn parse_octal_register(display: &str) -> Option<u16>` (pure helper)
  - `pub fn pump(session: AgcSession) -> (watch::Receiver<DskyState>, mpsc::UnboundedSender<Packet>, tokio::task::JoinHandle<()>)` — test/runner helper: owns the session, applies packets to a `DskyState`, publishes watch updates, forwards commands.

- [ ] **Step 1: Unit tests first** (in `script.rs`; no live AGC — fabricate watch updates):

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn octal_register_parse() {
        assert_eq!(parse_octal_register(" 01234"), Some(0o1234));
        assert_eq!(parse_octal_register("+01234"), Some(0o1234));
        assert_eq!(parse_octal_register(" 77776"), Some(0o77776));
        assert_eq!(parse_octal_register("  12 4"), None); // blanks inside
        assert_eq!(parse_octal_register(" 91234"), None); // non-octal digit
    }

    #[tokio::test]
    async fn keys_emit_expected_packets() {
        let (tx, mut rx_pkts) = tokio::sync::mpsc::unbounded_channel();
        let (_wtx, wrx) = tokio::sync::watch::channel(Default::default());
        let mut s = DskyScript::new(tx, wrx);
        s.set_key_delay(std::time::Duration::ZERO); // speed up unit test
        s.keys("V21N01E").await.unwrap();
        let names = ["VERB", "2", "1", "NOUN", "0", "1", "ENTR"];
        for n in names {
            let expect = eagle_agc_protocol::keys::DskyKey::from_name(n).unwrap().packet();
            assert_eq!(rx_pkts.recv().await.unwrap(), expect);
        }
    }

    #[tokio::test]
    async fn wait_resolves_on_predicate_and_times_out() {
        let (tx, _r) = tokio::sync::mpsc::unbounded_channel();
        let (wtx, wrx) = tokio::sync::watch::channel(DskyState::default());
        let mut s = DskyScript::new(tx, wrx);
        let waiter = tokio::spawn(async move {
            s.wait(std::time::Duration::from_secs(1), |d| d.prog == ['6', '3']).await
        });
        let mut d = DskyState::default();
        d.prog = ['6', '3'];
        wtx.send(d).unwrap();
        assert!(waiter.await.unwrap().is_ok());
    }
}
```

(Adjust the `prog` field type to the real `DskyState` — Phase 1 stores display chars; read `dsky.rs` first and use its actual representation. The test intent is binding, the field spelling follows the code.)

- [ ] **Step 2: Run, verify FAIL.** `cargo test -p eagle-runtime script` → module missing.

- [ ] **Step 3: Implement `script.rs`:**

```rust
//! Scripted DSKY choreography over the live AGC: key sequences, display
//! waits, erasable load/verify. Used by the descent spikes and ScenarioRunner.
use anyhow::{anyhow, bail, Context, Result};
use eagle_agc_protocol::dsky::DskyState;
use eagle_agc_protocol::keys::{pro_key_packets, DskyKey};
use eagle_agc_protocol::Packet;
use std::time::Duration;
use tokio::sync::{mpsc, watch};

pub struct DskyScript {
    tx: mpsc::UnboundedSender<Packet>,
    rx: watch::Receiver<DskyState>,
    key_delay: Duration,
}

impl DskyScript {
    pub fn new(tx: mpsc::UnboundedSender<Packet>, rx: watch::Receiver<DskyState>) -> Self {
        Self { tx, rx, key_delay: Duration::from_millis(80) }
    }
    pub fn set_key_delay(&mut self, d: Duration) { self.key_delay = d; }

    pub async fn keys(&mut self, seq: &str) -> Result<()> {
        for ch in seq.chars() {
            let name = match ch {
                'V' => "VERB", 'N' => "NOUN", 'E' => "ENTR", 'C' => "CLR",
                'K' => "KEY REL", 'R' => "RSET", '+' => "+", '-' => "-",
                '0'..='9' => &ch.to_string(),
                other => bail!("unknown key token {other:?} in {seq:?}"),
            };
            let key = DskyKey::from_name(name)
                .ok_or_else(|| anyhow!("no DskyKey named {name:?}"))?;
            self.tx.send(key.packet()).context("agc tx closed")?;
            tokio::time::sleep(self.key_delay).await;
        }
        Ok(())
    }

    pub async fn pro(&mut self) -> Result<()> {
        for p in pro_key_packets(true) { self.tx.send(p)?; }
        tokio::time::sleep(Duration::from_millis(150)).await;
        for p in pro_key_packets(false) { self.tx.send(p)?; }
        tokio::time::sleep(self.key_delay).await;
        Ok(())
    }

    pub async fn wait(
        &mut self, timeout: Duration, pred: impl Fn(&DskyState) -> bool,
    ) -> Result<DskyState> {
        let deadline = tokio::time::Instant::now() + timeout;
        loop {
            {
                let d = self.rx.borrow();
                if pred(&d) { return Ok(d.clone()); }
            }
            tokio::select! {
                r = self.rx.changed() => { r.context("dsky watch closed")?; }
                _ = tokio::time::sleep_until(deadline) => {
                    bail!("timeout waiting for DSKY condition; last state: {:?}",
                          *self.rx.borrow());
                }
            }
        }
    }

    pub async fn wait_flash(&mut self, verb: &str, noun: &str) -> Result<()> {
        let (v, n) = (verb.to_string(), noun.to_string());
        self.wait(Duration::from_secs(15), move |d| {
            d.verb.iter().collect::<String>() == v
                && d.noun.iter().collect::<String>() == n
                && d.verb_noun_flash
        }).await.map(|_| ())
    }

    pub async fn wait_prog(&mut self, mm: &str) -> Result<()> {
        let mm = mm.to_string();
        self.wait(Duration::from_secs(30), move |d| {
            d.prog.iter().collect::<String>() == mm
        }).await.map(|_| ())
    }

    /// V21N01: load one erasable word, then verify via V01N01 read-back.
    pub async fn load_erasable(&mut self, ecadr: u16, word: u16) -> Result<()> {
        use eagle_agc_protocol::words::octal5;
        self.keys("V21N01E").await?;
        self.keys(&octal5(ecadr)).await?; self.keys("E").await?;
        self.keys(&octal5(word)).await?; self.keys("E").await?;
        tokio::time::sleep(Duration::from_millis(200)).await;
        let got = self.read_erasable(ecadr).await?;
        if got != word {
            bail!("erasable {:05o}: wrote {:05o}, read back {:05o}", ecadr, word, got);
        }
        Ok(())
    }

    /// V01N01: display octal contents of an erasable; parse R1.
    pub async fn read_erasable(&mut self, ecadr: u16) -> Result<u16> {
        use eagle_agc_protocol::words::octal5;
        self.keys("V01N01E").await?;
        self.keys(&octal5(ecadr)).await?; self.keys("E").await?;
        let d = self.wait(Duration::from_secs(5), |d| {
            parse_octal_register(&reg_string(&d.r1)).is_some()
        }).await?;
        parse_octal_register(&reg_string(&d.r1))
            .ok_or_else(|| anyhow!("unparseable R1 after V01N01"))
    }

    /// V05N09: three most recent alarm codes (octal), R1-R3.
    pub async fn alarm_codes(&mut self) -> Result<[u16; 3]> {
        self.keys("V05N09E").await?;
        let d = self.wait(Duration::from_secs(5), |d| {
            parse_octal_register(&reg_string(&d.r1)).is_some()
        }).await?;
        Ok([
            parse_octal_register(&reg_string(&d.r1)).unwrap_or(0),
            parse_octal_register(&reg_string(&d.r2)).unwrap_or(0),
            parse_octal_register(&reg_string(&d.r3)).unwrap_or(0),
        ])
    }
}

fn reg_string(r: &eagle_agc_protocol::dsky::RegisterDisplay) -> String {
    std::iter::once(r.sign).chain(r.digits).collect()
}

pub fn parse_octal_register(display: &str) -> Option<u16> {
    let s = display.trim_start_matches([' ', '+', '-']);
    if s.len() != 5 { return None; }
    u16::from_str_radix(s, 8).ok()
}
```

`pump()` (same file): spawn a task that loops `session.events().recv()`, applies to a local `DskyState`, and `watch::Sender::send_replace`s a clone on every visible change; forward an `mpsc::UnboundedReceiver<Packet>` into `session.send`. Return `(watch_rx, cmd_tx, join_handle)`. Reuse the loop shape from `main.rs` (events + commands select).

- [ ] **Step 4: Refactor `main.rs`** to use the same watch publication: add `let (dsky_tx, dsky_rx) = watch::channel(DskyState::default());` beside `latest`; in the `dsky.apply(&pkt)` branch also `let _ = dsky_tx.send(dsky.clone());`. Keep `dsky_rx` alive in scope (`let _keep = dsky_rx;` until Task 14 consumes it) — do not break existing behavior; `make test` must stay green.

- [ ] **Step 5: Run unit tests, verify PASS** — `cargo test -p eagle-runtime`.

- [ ] **Step 6: Live smoke test** `tests/live_script.rs` (pattern-match Phase 1 `live_agc.rs` for AGC boot + paths; port **19901**; `#[ignore]`):

```rust
// boot yaAGC, pump(), settle, then:
// 1) V35E lamp test observed (all-8s displays) — proves keys() path end to end
// 2) read_erasable(0o0) parses (register A, value arbitrary)
// 3) alarm_codes() returns without timeout
```

Copy the `settle_dsky` helper approach from `tests/golden_v35e.rs` (quiet-check scoped to {0o10, 0o11, 0o163}). Run: `cargo test -p eagle-runtime --test live_script -- --ignored --test-threads=1` → PASS.

- [ ] **Step 7: Commit** — `git commit -m "feat(runtime): scripted DSKY harness with erasable load/read-back"` (+ trailer).

---

### Task 5: Symbol table, pad-load manifest, generator CLI

**Files:**
- Create: `runtime/apps/eagle-runtime/src/padload.rs`, `runtime/apps/eagle-runtime/src/bin/padload_gen.rs`
- Modify: `runtime/apps/eagle-runtime/Cargo.toml` (deps += `toml = "0.8"`, `eagle-dynamics` path dep), `src/lib.rs` (`pub mod padload;`)
- Modify (if needed): `scripts/assemble-luminary.sh` — keep the yaYUL listing
- Test: unit tests in `padload.rs` with fixture at `runtime/apps/eagle-runtime/tests/fixtures/symtab_excerpt.txt`

**Interfaces:**
- Consumes: `eagle_agc_protocol::words::{to_pulses, dp_encode, sp_encode}`, `eagle_dynamics::frames`.
- Produces (used by Tasks 6, 7, 14):
  - `pub struct SymTab` with `pub fn from_listing(text: &str) -> Result<SymTab>` and `pub fn ecadr(&self, symbol: &str) -> Option<u16>`
  - `pub struct PadloadManifest` (serde) with `pub fn load(path: &Path) -> Result<Self>` and `pub fn resolve(&self, symtab: &SymTab) -> Result<Vec<PadWord>>`; `pub struct PadWord { pub ecadr: u16, pub word: u16 }`

**Step 0 (mandatory, before code):**
1. Inspect `build/agc/` and `scripts/assemble-luminary.sh`. If the yaYUL listing (symbol table text) is not preserved, extend the script to save yaYUL stdout as `build/agc/Luminary099.lst` (additive — must not change the shipped binary or its recorded hashes in `build/agc/manifest.json`; re-run `make agc` and `make test-integration` to prove it).
2. Extract 5-10 real symbol-table lines (must include RODSCALE, TLAND or RLS, and one unswitched-erasable symbol) into the fixture file, verbatim.
3. Pin the erasable-address notation: yaYUL prints banked erasable as `E<bank>,<offset>` (offset 1400-1777) and unswitched as plain octal. ECADR for V21N01 = `bank*0o400 + (offset − 0o1400)` for switched banks (E0-E7), plain address for unswitched (0000-1377). Verify against `Luminary099/ERASABLE_ASSIGNMENTS.agc` bank comments and record the rule + citation in `docs/agc-channel-map.md`.

- [ ] **Step 1: Failing tests** (against the real fixture lines — exact strings come from Step 0; shape:)

```rust
#[test]
fn symtab_parses_fixture() {
    let text = include_str!("../tests/fixtures/symtab_excerpt.txt");
    let st = SymTab::from_listing(text).unwrap();
    let rodscale = st.ecadr("RODSCALE").unwrap();
    assert!(rodscale <= 0o3777, "ECADR range");
    // MANDATORY: also assert the exact ECADR, computed BY HAND from the
    // fixture line using the Step-0 conversion rule, with the line cited in
    // a comment. A range check alone does not verify the bank arithmetic.
}

#[test]
fn manifest_resolves_physical_and_octal_words() {
    let toml_text = r#"
        [[word]]
        symbol = "RODSCALE"
        physical = { value = -0.3048, b = 7, dp = false }
        provenance = "derived"

        [[word]]
        addr = "01234"
        octal = "00042"
        provenance = "assumed"
    "#;
    let m: PadloadManifest = toml::from_str(toml_text).unwrap();
    let st = SymTab::from_listing(include_str!("../tests/fixtures/symtab_excerpt.txt")).unwrap();
    let words = m.resolve(&st).unwrap();
    assert_eq!(words.last().unwrap(), &PadWord { ecadr: 0o1234, word: 0o42 });
    // SP physical: pulses = round(-0.3048 / 2^(7-14)) = round(-39.01) = -39
    assert_eq!(words[0].word, eagle_agc_protocol::words::sp_encode(-39));
}

#[test]
fn manifest_dp_emits_two_consecutive_words() {
    let toml_text = r#"
        [[word]]
        addr = "02000"
        physical = { value = 1000000.0, b = 27, dp = true }
        provenance = "derived"
    "#;
    let m: PadloadManifest = toml::from_str(toml_text).unwrap();
    let st = SymTab::from_listing("").unwrap();
    let w = m.resolve(&st).unwrap();
    assert_eq!(w.len(), 2);
    assert_eq!((w[0].ecadr, w[1].ecadr), (0o2000, 0o2001));
    let pulses = eagle_agc_protocol::words::dp_decode([w[0].word, w[1].word]);
    assert_eq!(pulses, 2_000_000);
}
```

- [ ] **Step 2: Run, verify FAIL.**

- [ ] **Step 3: Implement `padload.rs`** — `SymTab`: line-parser for the fixture format (regex-free: split_whitespace, detect `E<d>,<offset>` vs plain octal; store map name→ecadr). `PadloadManifest`:

```rust
#[derive(serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PadloadManifest { pub word: Vec<ManifestWord> }

#[derive(serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ManifestWord {
    pub symbol: Option<String>,
    pub addr: Option<String>,          // 5-digit octal ECADR
    pub octal: Option<String>,         // raw word, wins over physical
    pub physical: Option<Physical>,
    pub provenance: String,            // historical | derived | assumed
    pub comment: Option<String>,
}

#[derive(serde::Deserialize)]
pub struct Physical { pub value: f64, pub b: i32, pub dp: bool }
```

`resolve`: for each word: ecadr from `symbol` (symtab lookup) or `addr` (octal parse) — exactly one must be present; word(s) from `octal` (parse) or `physical` (`to_pulses` → `sp_encode`/`dp_encode`); DP pushes `[ecadr, ecadr+1]`. Errors name the entry.

- [ ] **Step 4: Run, verify PASS.**

- [ ] **Step 5: `padload_gen.rs` CLI** — generates the scenario pad-load manifest from first principles (all math via `eagle-dynamics`):

```
cargo run -p eagle-runtime --bin padload_gen -- \
  --site-lat-deg 0.674 --site-lon-deg 23.473 \
  --alt-m 500 --vz-ms 0.0 --epoch-cs 0 --out scenarios/p66-padload.toml
```

Emits `[[word]]` entries (all `provenance = "derived"` unless noted) for:
- `RLS` (3 × DP, MCMF site vector, meters, **b = 27**): site unit vector × R_SITE
- `RN`/`VN`+`PIPTIME` (state vector: position = site + alt·up in MCI at epoch, velocity = vz·up; **b = 27 / b = 7 (m/cs)** initial guesses), 
- `REFSMMAT` (6 × DP? — 3×3 rows, each element DP **b = 1**, row-major): SM ≡ initial BODY attitude (see Task 12 scenario: body +X up), expressed in MCI
- `TLAND` (DP, centiseconds, **b = 28**): epoch + 120 s
- `RODSCALE` (SP, m/cs per click? **initial: −0.3048 m/s ≡ 1 ft/s, b = 7**), `TAUROD = 1.5 s`, `LAG/TAU = 0.2 s`, `MINFORCE = 4560 N → pulses?`, `MAXFORCE = 42500 N` (b-scales: **Step-0 of Spike A extracts each variable's scaling from its in-rope usage** — `LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1044-1090,174` — and this CLI's constants table is corrected to match; the octal that ends up committed in `scenarios/p66-padload.toml` is what Spike A verified live).

The CLI hard-fails if any b-scale is marked `UNVERIFIED` in its table AND `--allow-unverified` is absent — the flag exists so Spike A can iterate.

**The b-scale guesses above are working hypotheses, not facts.** The empirical validation loop (display read-back, alarm-driven iteration) in Spike A is the authority; this task only has to produce plausible first-cut TOML + the machinery.

- [ ] **Step 6: Run full fast suite** — `cd runtime && cargo test` → PASS; `make test` → PASS.

- [ ] **Step 7: Commit** — `git commit -m "feat(runtime): yaYUL symtab parsing, pad-load manifest, generator CLI"` (+ trailer).

---

### Task 6: Live Spike A — boot → pad-load → P63 → ignition

**Nature:** exploratory live spike. The harness code below is binding; the
numeric findings (b-scales, pad-load values, alarm whitelist, timing) are
DATA discovered live, committed to `scenarios/p66-padload.toml` + ledger.
Expect several iterations; log each (alarm code → diagnosis → change) in
`.superpowers/sdd/progress.md`. Hard rule: the final committed test masks
no alarm with RSET-and-continue; non-whitelisted alarms fail it.

**Files:**
- Create: `runtime/apps/eagle-runtime/src/runner.rs` (`pub mod runner;` in lib.rs)
- Create: `runtime/apps/eagle-runtime/src/bin/descent_probe.rs` (interactive iteration aid)
- Create: `runtime/apps/eagle-runtime/tests/live_spike_p63.rs` (port **19902**, `#[ignore]`)
- Create: `scenarios/p66-padload.toml` (static pad-load words; grows during the spike)
- Modify: `runtime/apps/eagle-runtime/src/padload.rs` — move state-vector generation out of the CLI into `pub fn generate_state(cfg: &StateCfg) -> Vec<ManifestWord>` (CLI becomes a thin wrapper); runner regenerates time-dependent words live from the measured AGC clock.
- Modify: `runtime/apps/eagle-runtime/src/script.rs` — `pump` additionally returns `tokio::sync::broadcast::Receiver<Packet>` of all AGC packets (spike responders need the raw stream).

**Interfaces:**
- Consumes: `DskyScript`, `pump`, `padload::{PadloadManifest, SymTab, generate_state}`, `agc_io::{discrete_write, decode_output, AgcOutput, pipa_pulse}`, constants.
- Produces (used by Tasks 7, 14, 16):
  - `pub struct DescentInit { pub script: DskyScript, pub packets: broadcast::Receiver<Packet>, pub agc_tx: mpsc::UnboundedSender<Packet> }`
  - `pub async fn init_discretes(tx: &mpsc::UnboundedSender<Packet>) -> Result<()>`
  - `pub async fn apply_padload(script: &mut DskyScript, words: &[PadWord], verify_every: usize) -> Result<()>`
  - `pub async fn enter_p63(script: &mut DskyScript) -> Result<()>` (V37E63E + PRO-on-flash responder)
  - `pub struct SyntheticHover` (v1: constant hover PIPA feed; v2 in Task 7)
  - `pub const INIT_CH30/31/32/33: u16`, `pub const CH31_ATT_HOLD: u16`

**Key fixed values** (cite in code comments):

```rust
// LM_Simulator boot discretes (lm_simulator.tcl:570-577), inverted logic,
// with AUTO THROTTLE (ch30 bit5) additionally asserted (cleared) for P66:
pub const INIT_CH30: u16 = 0o36311; // LM_Sim 0o36331 & !0o20 (bit5 → computer throttle)
pub const INIT_CH31: u16 = 0o57777; // AUTO mode: bit14 (0o20000) asserted
pub const INIT_CH32: u16 = 0o21777;
pub const INIT_CH33: u16 = 0o57776;
pub const CH31_ATT_HOLD: u16 = 0o67777; // bit13 (0o10000) asserted, bit14 clear
```

(Derivation: wdata(30)=`011110011011001`₂=0o36331, wdata(31)=0o77777,
wdata(32)=`010001111111111`₂=0o21777, wdata(33)=`101111111111110`₂=0o57776.
The implementer re-derives these three conversions by hand in Step 0 and
fixes any arithmetic slip — the binary strings are the source of truth.)

**Choreography (best current knowledge — the spike refines and commits the truth):**

1. Boot yaAGC (Phase 1 pattern), `pump`, settle. Start `SyntheticHover` v1
   immediately: every 10 ms emit PIPA PINC/MINC for a constant specific
   force of +1.62 m/s² along SM +X (body +X up, SM ≡ body at t0):
   `pulses/s = 1.62 / PIPA_INCR ≈ 27.7` with carry-forward accumulator; no
   CDU pulses (attitude static, gimbals 0). Log-and-ignore CoarseAlign/Gyro
   outputs for now.
2. `init_discretes`: full-word `Packet::io` writes of INIT_CH30..33 (we own
   the whole word at init; later mutations use `discrete_write` pairs).
3. Read AGC clock (V16N36, Phase 1 pattern) → epoch_cs; `generate_state`
   with `tland_cs = epoch_cs + 12_000` (TIG target ≈ +120 s; refine live).
4. DAP init: `keys("V48E")` then respond: expect FL V04N46 → PRO, FL V06N47
   → set LM weight (V21E + value; N47 R1 units are lbs — verify the noun
   scaling in `Luminary099/PINBALL_NOUN_TABLES.agc` in Step 0) → PRO,
   FL V06N48 → PRO. Wrap as `dap_init(&mut script, lm_weight_lbs)`.
5. `apply_padload`: static manifest + generated state words. Key-delay
   budget: try 30 ms; if keys drop (read-back mismatch), raise until
   reliable and record the floor in the ledger. `verify_every: 1` while
   iterating; the committed test may use sparse verification (every 8th
   word + all words the spike ever saw fail) to fit the time budget.
6. Set REFSMFLG (IMU-aligned flag): read FLAGWRD3 via symtab symbol, OR the
   REFSMBIT (pin bit position from `ERASABLE_ASSIGNMENTS.agc` /
   `FLAGWORD` definitions in Step 0), write back. If P63 still complains
   00220, iterate here.
7. `enter_p63`: `keys("V37E63E")`, then responder loop until ENGINE ON or
   timeout 180 s:
   - flashing V50/V06/V04 display → wait 1 s → `pro()`
   - PROG lamp lit → `alarm_codes()` → return Err (iteration data)
   - `AgcOutput::Engine { on: true, .. }` observed → Ok
8. On success also assert: MM reached "63" at some point; downlink packets
   (ch 034/035) flowing (≥ 40/s averaged over 5 s — the drift-meter
   precondition).

**Iteration protocol (decision tree):**
- Alarm in table → follow its row (00210/00220 → discretes/flags; 00404,
  01301, 0060x → state-vector/target scaling: revisit b-scales; 01520 →
  V37 rejected: flags/mode).
- Unknown alarm → `grep -rn "<code octal>" vendor/virtualagc/Luminary099/`
  → read the emitting routine → classify → fix data, never code-around.
- Scaling validation: after pad-load, `keys("V06N43E")` — N43 displays
  lat/long/alt; check alt ≈ site + 500 m (pin N43's display scaling from
  PINBALL_NOUN_TABLES in Step 0). Iterate RN/VN b-scales until sane.
- Every iteration → one ledger line: `spike-A iter N: <alarm/observation> → <change>`.

- [ ] **Step 1:** Step-0 verifications listed above (N47/N43 noun scaling, REFSMBIT, discrete conversions, ECADR rule already pinned in Task 5).
- [ ] **Step 2:** Implement `runner.rs` pieces + `SyntheticHover` v1 + `descent_probe` bin (stdin commands: `pro`, `alarm`, `keys <SEQ>`, `att-hold`, `quit`; prints every decoded `AgcOutput` ≠ Downlink and every DSKY change line — reuse Phase 1 interpret vocabulary freely).
- [ ] **Step 3:** Unit-test the pure parts (no AGC): discrete constants round-trip the binary strings; `apply_padload` verification cadence logic against a scripted fake; PRO-on-flash responder classification table.
- [ ] **Step 4:** Iterate live with `descent_probe` until choreography completes. Record everything in the ledger; grow `scenarios/p66-padload.toml`.
- [ ] **Step 5:** Freeze the working choreography into `tests/live_spike_p63.rs` (port 19902): boots, runs init + pad-load + P63, asserts ENGINE ON within 180 s and alarms ⊆ `runner::SPIKE_A_ALARM_WHITELIST: &[u16]` (pub const in runner.rs — Task 16 imports it too — committed with a citation/justification comment per entry).
- [ ] **Step 6:** `cargo test -p eagle-runtime --test live_spike_p63 -- --ignored --test-threads=1` → PASS twice consecutively (flake check).
- [ ] **Step 7:** Commit (code + manifest + ledger) — `git commit -m "feat(runtime): scripted pad-load + P63 ignition spike (live)"` (+ trailer).

---

### Task 7: Live Spike B — ATT-HOLD → P66 + THRUST DINC proof + ROD calibration

**Nature:** exploratory live spike, same rules as Task 6. This task retires
the plan's two biggest unknowns: (1) GUILDENSTERN accepts our forced
ATT-HOLD entry into P66; (2) the THRUST DINC-strobe protocol closes a real
vertical channel. It flies a crude 1-D closed loop BEFORE the full 6-DoF
physics exists.

**Files:**
- Modify: `runtime/apps/eagle-runtime/src/runner.rs` (add `ThrustResponder`, `SyntheticHover` v2, `att_hold()`)
- Create: `runtime/apps/eagle-runtime/tests/live_spike_p66.rs` (port **19903**, `#[ignore]`)
- Modify: `scenarios/p66-padload.toml` (RODSCALE calibration), `eagle-dynamics/src/constants.rs` (THRUST_N_PER_PULSE if calibration disagrees)

**Interfaces:**
- Produces (used by Tasks 13, 16):
  - `pub struct ThrustResponder { pub cmd_pulses: i64, armed: bool }` with `pub fn on_output(&mut self, out: &AgcOutput)` and `pub fn tick_packets(&mut self) -> Vec<Packet>` (≤ DINC_MAX_PER_TICK thrust_dinc packets while armed)
  - `pub async fn att_hold(tx: &mpsc::UnboundedSender<Packet>) -> Result<()>` (ch 031 → CH31_ATT_HOLD via full-word write)
  - `SyntheticHover` v2: 1-D vertical truth `struct { alt_m: f64, vz_ms: f64, mass_kg: f64 }`, per 10 ms tick: `thrust = responder.cmd_pulses as f64 * THRUST_N_PER_PULSE` (clamped to DPS envelope, engine-on gated), `az = thrust/mass − 1.62`, integrate, PIPA pulses = specific force `thrust/mass` along SM +X with carry-forward; mass burn `thrust/DPS_VE · dt`.

**ThrustResponder semantics** (from the header protocol; re-verify Step 0):

```rust
pub fn on_output(&mut self, out: &AgcOutput) {
    match out {
        AgcOutput::ThrustDrive(true) => self.armed = true,
        AgcOutput::ThrustPulse(ThrustPulse::Pout) => self.cmd_pulses += 1,
        AgcOutput::ThrustPulse(ThrustPulse::Mout) => self.cmd_pulses -= 1,
        AgcOutput::ThrustPulse(ThrustPulse::Zout) => self.armed = false,
        _ => {}
    }
}
pub fn tick_packets(&mut self) -> Vec<Packet> {
    if !self.armed { return vec![]; }
    (0..DINC_MAX_PER_TICK).map(|_| thrust_dinc()).collect()
}
```

**Choreography:** run Task 6's sequence; then:
1. ~2 s after ENGINE ON (parameter `flip_delay_s`, sweep 0-10 s if needed): `att_hold()`.
2. `wait_prog("66")` within 20 s (GUILDENSTERN runs each 2 s servicer pass). If P67 appears instead → ch30 bit5 polarity is wrong → fix INIT_CH30, ledger note. If P64/P65 appears → note and re-diagnose (LM_Sim mode table `AGC_Crew_Inputs.tcl:118-124`).
3. Observe the vertical channel close: feeder v2 truth tracks P66. Send ROD clicks (`rod_click`, release next tick) and observe.

**Calibrations (all committed):**
- RODSCALE: after P66 stabilizes, read displayed HDOT (P66 flight display — expected V16N60-family; pin the actual noun + register + scaling live and record it: this becomes Task 14's `agc_nav` parser spec). One down-click must change the target by 1 ft/s = 0.3048 m/s ±5%; iterate the manifest value until true.
- THRUST_N_PER_PULSE: at steady hover (ROD target ≈ 0), `cmd_pulses · scale ≈ mass · 1.62`; solve for scale. If outside 12.0 ± 20%, update the constant (one place) and re-run.
- Whitelist: extend `SPIKE_B_ALARM_WHITELIST` with any steady-state P66-without-radar codes observed (e.g. ALT/VEL lamps are expected — record which).

- [ ] **Step 1:** Step-0: re-read `agc_engine.c:1278-1305` (POUT/MOUT/ZOUT) + `:1570-1623` (DINC dispatch); pin GUILDENSTERN's exact discrete reads (`LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:144-225`).
- [ ] **Step 2:** Unit tests for `ThrustResponder` (arm/disarm/count over a scripted AgcOutput sequence; tick_packets bounded and empty when disarmed) and `SyntheticHover` v2 (hover equilibrium: with cmd_pulses = mass·1.62/scale, vz stays within ±0.05 m/s over 60 s of ticks).
- [ ] **Step 3:** Run failing → implement → pass (`cargo test -p eagle-runtime runner`).
- [ ] **Step 4:** Live iteration via `descent_probe` (add `rod +`/`rod -` stdin commands). Achieve: MM66, ROD tracking (truth vz settles within 0.3 m/s of clicked target inside 15 s), calibrations done.
- [ ] **Step 5:** Freeze into `tests/live_spike_p66.rs` (port 19903) asserting: MM66 reached; `cmd_pulses` nonzero; after scripted "2 down-clicks", feeder truth vz changes by −0.6 ± 0.15 m/s within 15 s; alarms ⊆ whitelist. PASS twice consecutively.
- [ ] **Step 6:** Update `docs/agc-channel-map.md`: THRUST protocol "verified live" note + measured pulse scale + the P66 nav-display (noun/register/scaling) finding.
- [ ] **Step 7:** Commit — `git commit -m "feat(runtime): P66 entry + THRUST DINC protocol proven live (spike B)"` (+ trailer).

**Escalation rule (both spikes):** if after ~10 documented iterations a
wall remains (e.g. GUILDENSTERN never leaves P63, or DINC yields no
POUT/MOUT), STOP; write the evidence to the ledger and report BLOCKED to
the controller — the fallback (retreat to the DAP-attitude Wave 1, option
A of the 2026-07-23 decision) is the human's call, not the implementer's.

---

### Task 8: `eagle-dynamics` — state, gravity, RK4

**Files:**
- Create: `runtime/crates/eagle-dynamics/src/state.rs`, `src/rk4.rs` (lib.rs: `pub mod state; pub mod rk4;`)

**Interfaces:**
- Produces (used by Tasks 9, 13):
  - `pub struct LmState { pub t: f64, pub pos: V3<Mci>, pub vel: V3<Mci>, pub att: Rot<Body, Mci>, pub omega: V3<Body>, pub mass_kg: f64, pub fuel_dps_kg: f64, pub fuel_rcs_kg: f64 }`
  - `pub struct Derivs { pub acc: V3<Mci>, pub alpha: V3<Body>, pub mdot_total: f64, pub mdot_dps: f64, pub mdot_rcs: f64 }`
  - `pub fn gravity(pos: V3<Mci>) -> V3<Mci>` — point mass: `-pos.unit().scale(MU_MOON / r²)`
  - `pub fn step_rk4(s: &LmState, f: &impl Fn(&LmState) -> Derivs, dt: f64) -> LmState` — classic RK4, FIXED evaluation order k1..k4, quaternion components integrated linearly then `normalize()`d once at the end; fuel fields clamped ≥ 0 after the step.

- [ ] **Step 1: Failing tests** (`state.rs`/`rk4.rs` cfg(test)):

```rust
#[test]
fn circular_orbit_energy_stable() {
    let r0 = 1_837_400.0; // 100 km altitude
    let v0 = (MU_MOON / r0).sqrt();
    let mut s = LmState {
        t: 0.0, pos: V3::new(r0, 0.0, 0.0), vel: V3::new(0.0, v0, 0.0),
        att: Rot::identity(), omega: V3::zero(),
        mass_kg: 9000.0, fuel_dps_kg: 2000.0, fuel_rcs_kg: 150.0,
    };
    let f = |s: &LmState| Derivs {
        acc: gravity(s.pos), alpha: V3::zero(),
        mdot_total: 0.0, mdot_dps: 0.0, mdot_rcs: 0.0,
    };
    let e = |s: &LmState| 0.5 * s.vel.dot(s.vel) - MU_MOON / s.pos.norm();
    let e0 = e(&s);
    for _ in 0..6000 { s = step_rk4(&s, &f, DT); } // 60 s
    assert!(((e(&s) - e0) / e0).abs() < 1e-10, "energy drift");
    assert!((s.pos.norm() - r0).abs() / r0 < 1e-6, "radius drift");
}

#[test]
fn rk4_fourth_order_convergence() {
    // free rotation about a principal axis has analytic solution; halving dt
    // must shrink attitude error by ~2^4 (accept ≥ 8× to be robust)
    let s0 = LmState { omega: V3::new(0.0, 0.0, 0.5), ..hover_state() };
    let f = |_: &LmState| Derivs { acc: V3::zero(), alpha: V3::zero(),
                                   mdot_total: 0.0, mdot_dps: 0.0, mdot_rcs: 0.0 };
    let run = |dt: f64| {
        let mut s = s0.clone();
        let n = (10.0 / dt) as usize;
        for _ in 0..n { s = step_rk4(&s, &f, dt); }
        // analytic: rotation angle 0.5 rad/s * 10 s about z
        let v = s.att.apply(V3::<Body>::new(1.0, 0.0, 0.0));
        let expect = 5.0f64;
        ((v.y.atan2(v.x) - expect).sin()).abs() // angle error, wrap-safe
    };
    let (e1, e2) = (run(0.02), run(0.01));
    assert!(e1 / e2 > 8.0, "convergence order too low: {e1} / {e2}");
}

#[test]
fn quaternion_stays_normalized_and_fuel_clamps() {
    let mut s = hover_state();
    s.omega = V3::new(0.3, -0.2, 0.1);
    s.fuel_dps_kg = 0.001;
    let f = |_: &LmState| Derivs { acc: V3::zero(), alpha: V3::new(0.01, 0.0, 0.0),
                                   mdot_total: -1.0, mdot_dps: -1.0, mdot_rcs: 0.0 };
    for _ in 0..1000 { s = step_rk4(&s, &f, DT); }
    let n: f64 = s.att.raw().iter().map(|v| v * v).sum::<f64>().sqrt();
    assert!((n - 1.0).abs() < 1e-12);
    assert_eq!(s.fuel_dps_kg, 0.0); // clamped, never negative
}

#[test]
fn determinism_bit_exact() {
    let f = |s: &LmState| Derivs { acc: gravity(s.pos), alpha: V3::zero(),
                                   mdot_total: 0.0, mdot_dps: 0.0, mdot_rcs: 0.0 };
    let run = || { let mut s = hover_state();
        for _ in 0..500 { s = step_rk4(&s, &f, DT); } s };
    let (a, b) = (run(), run());
    assert_eq!(a.pos, b.pos); assert_eq!(a.att.raw(), b.att.raw());
}
```

`hover_state()` test helper: 500 m above R_SITE on the x-axis, zero velocity, identity attitude, mass 9159/fuel 2000/150. Define it once in `lib.rs` as `#[cfg(test)] pub(crate) mod testutil { pub fn hover_state() -> crate::state::LmState { … } }` so Task 9's tests reuse it (`use crate::testutil::hover_state;`).

- [ ] **Step 2: FAIL** → **Step 3: implement**:

```rust
// state.rs
pub fn gravity(pos: V3<Mci>) -> V3<Mci> {
    let r2 = pos.dot(pos);
    pos.unit().scale(-crate::constants::MU_MOON / r2)
}

// rk4.rs — classic RK4 over the 14-dim state; fixed k1..k4 order.
pub fn step_rk4(s: &LmState, f: &impl Fn(&LmState) -> Derivs, dt: f64) -> LmState {
    let k1 = eval(s, f);
    let k2 = eval(&advance(s, &k1, dt / 2.0), f);
    let k3 = eval(&advance(s, &k2, dt / 2.0), f);
    let k4 = eval(&advance(s, &k3, dt), f);
    let mut out = combine(s, &[k1, k2, k3, k4], dt);
    out.att = out.att.normalize();
    out.fuel_dps_kg = out.fuel_dps_kg.max(0.0);
    out.fuel_rcs_kg = out.fuel_rcs_kg.max(0.0);
    out.t = s.t + dt;
    out
}
```

where `eval` packs `(vel, acc, qdot, alpha, mdots)` — `qdot = ½ q ⊗ [0, ω_body]`
(implement `qdot(q_raw: [f64;4], w: V3<Body>) -> [f64;4]` beside `qmul`, make
`qmul` `pub(crate)` in frames.rs) — and `advance`/`combine` do the standard
weighted sums (attitude components summed linearly; single normalize at the
end of `step_rk4` only). Keep all three helpers private to `rk4.rs`.

- [ ] **Step 4: PASS** — `cargo test -p eagle-dynamics`.
- [ ] **Step 5: Commit** — `"feat(dynamics): rigid-body state, lunar gravity, fixed-step RK4"` (+ trailer).

---

### Task 9: `eagle-dynamics` — DPS, RCS, trim, touchdown

**Files:**
- Create: `runtime/crates/eagle-dynamics/src/forces.rs`, `src/touchdown.rs`

**Interfaces:**
- Produces (used by Task 13):
  - `pub struct Actuators { pub engine_on: bool, pub throttle_cmd_n: f64, pub thrust_n: f64, pub trim_pitch_rad: f64, pub trim_roll_rad: f64, pub jets: u16 }` (jets bit i = JET_TABLE[i] firing; bits 0-7 ← ch005 bits 1-8, bits 8-15 ← ch006 bits 1-8)
  - `pub fn dps_envelope(cmd_n: f64) -> f64` — 0 below MIN; [MIN, 0.6·MAX] passthrough; above → FTP
  - `pub fn actuator_step(a: &mut Actuators, dt: f64)` — first-order lag `thrust += (env(cmd) − thrust)·(1 − exp(−dt/DPS_TAU))`, zero when `!engine_on` or fuel empty (caller gates). `Actuators` derives `Clone` (tests need it).
  - `pub struct V3Raw(pub f64, pub f64, pub f64);` — const-friendly plain triple; converted to `V3<Body>` only inside `forces`
  - `pub fn forces(s: &LmState, a: &Actuators, inertia0: V3Raw /*diag kg·m² at mass0*/, mass0_kg: f64) -> Derivs` — inertia used = `inertia0 · (s.mass_kg / mass0_kg)` (spec §4: mass AND inertia updated from flow; linear scaling is the Wave 1 model, provenance assumed)
  - `pub const JET_TABLE: [Jet; 16]` with `pub struct Jet { pub name: &'static str, pub pos: V3Raw, pub dir: V3Raw }`
  - Min-impulse note: the AGC times sub-tick jet pulses internally (T6RUPT, 14 ms minimum); our 10 ms tick applies the latest jet word for a whole tick — worst-case ~10 ms timing quantization, documented in `forces.rs` and accepted for Wave 1.
  - `pub const ENGINE_MOUNT_M: f64 = -1.7;` (DPS gimbal below CG on −X; assumed)
  - `pub fn classify_touchdown(v_vert: f64, v_horiz: f64, tilt_deg: f64) -> Touchdown` — `Nominal` (<3, <1.5, <12), `Hard` (<6, <3, <20), else `Crash`

**Jet geometry:** quads 1-4 at Y-Z-plane azimuths, radius `RCS_LEVER_M`.
Quad positions (BODY, meters): Q1 = (0, +L·cos45, +L·sin45)… fix the exact
azimuth assignment in Step 0 so that the resulting torque signs reproduce
LM_Simulator's axis mapping (`AGC_Simulation_Monitor_Control.tcl:231-305`):
`nv` = (Q2D + Q4U) − (Q2U + Q4D) drives one 45° axis, `nu` = (Q1D + Q3U) −
(Q1U + Q3D) the other, yaw `np` = (Q1F + Q2L + Q3A + Q4R) − (Q1L + Q2A +
Q3R + Q4F). U/D jets: nozzle up/down → force along −X/+X respectively;
F/A/L/R jets: horizontal, tangential. The unit tests below are written
against the tcl outcomes — if your azimuth guess breaks them, fix the
table, not the tests, and cite the tcl lines.

- [ ] **Step 1: Failing tests:**

```rust
#[test]
fn envelope_clamps_and_ftp_snaps() {
    assert_eq!(dps_envelope(0.0), 0.0);
    assert_eq!(dps_envelope(3000.0), 0.0);           // below MIN → no thrust band
    assert_eq!(dps_envelope(10_000.0), 10_000.0);    // throttleable band
    assert_eq!(dps_envelope(0.6 * DPS_MAX_N), 0.6 * DPS_MAX_N);
    assert_eq!(dps_envelope(0.61 * DPS_MAX_N), DPS_FTP_N); // FTP snap
}

#[test]
fn throttle_lag_first_order() {
    let mut a = Actuators { engine_on: true, throttle_cmd_n: 20_000.0,
                            thrust_n: 0.0, trim_pitch_rad: 0.0,
                            trim_roll_rad: 0.0, jets: 0 };
    actuator_step(&mut a, DPS_TAU); // one time constant
    assert!((a.thrust_n / 20_000.0 - 0.632).abs() < 0.01);
}

#[test]
fn dps_thrust_along_body_x_and_trim_torques() {
    let s = hover_state();
    let a = Actuators { engine_on: true, throttle_cmd_n: 20_000.0,
                        thrust_n: 20_000.0, trim_pitch_rad: 0.01,
                        trim_roll_rad: 0.0, jets: 0 };
    let d = forces(&s, &a, V3Raw(12_000.0, 13_500.0, 13_000.0), 9159.0);
    // thrust ~ +X body = +x MCI (identity attitude), minus gravity pull
    assert!(d.acc.x > 0.0);
    // pitch trim tilts thrust → torque about the trim axis, sign per geometry
    assert!(d.alpha.y.abs() > 0.0 && d.alpha.z.abs() < 1e-12);
}

#[test]
fn rcs_axis_mapping_matches_lm_simulator() {
    let s = hover_state();
    let base = Actuators { engine_on: false, throttle_cmd_n: 0.0, thrust_n: 0.0,
                           trim_pitch_rad: 0.0, trim_roll_rad: 0.0, jets: 0 };
    let jet = |name: &str| JET_TABLE.iter().position(|j| j.name == name).unwrap();
    // Q2D + Q4U together: pure "V-axis" rotation, no net force couple errors
    let mut a = base.clone();
    a.jets = (1 << jet("Q2D")) | (1 << jet("Q4U"));
    let d = forces(&s, &a, V3Raw(12_000.0, 13_500.0, 13_000.0), 9159.0);
    let (ay, az) = (d.alpha.y, d.alpha.z);
    // couple: same-magnitude rotation about the 45° axis, zero X torque
    assert!(d.alpha.x.abs() < 1e-9);
    assert!((ay.abs() - az.abs()).abs() < 1e-9 && ay.hypot(az) > 0.0);
    // yaw quartet: pure X torque
    let mut a = base.clone();
    a.jets = ["Q1F", "Q2L", "Q3A", "Q4R"].iter().fold(0, |m, n| m | 1 << jet(n));
    let d = forces(&s, &a, V3Raw(12_000.0, 13_500.0, 13_000.0), 9159.0);
    assert!(d.alpha.x.abs() > 0.0 && d.alpha.y.abs() < 1e-9 && d.alpha.z.abs() < 1e-9);
}

#[test]
fn fuel_burn_rates() {
    let s = hover_state();
    let mut a = Actuators { engine_on: true, throttle_cmd_n: 30_000.0,
        thrust_n: 30_000.0, trim_pitch_rad: 0.0, trim_roll_rad: 0.0, jets: 1 };
    let d = forces(&s, &a, V3Raw(12_000.0, 13_500.0, 13_000.0), 9159.0);
    assert!((d.mdot_dps - (-30_000.0 / DPS_VE)).abs() < 1e-9);
    assert!((d.mdot_rcs - (-RCS_THRUST_N / RCS_VE)).abs() < 1e-9);
    a.jets = 0b11; // two jets
    let d = forces(&s, &a, V3Raw(12_000.0, 13_500.0, 13_000.0), 9159.0);
    assert!((d.mdot_rcs - (-2.0 * RCS_THRUST_N / RCS_VE)).abs() < 1e-9);
}

#[test]
fn touchdown_classification() {
    assert_eq!(classify_touchdown(2.9, 1.4, 11.9), Touchdown::Nominal);
    assert_eq!(classify_touchdown(3.1, 0.0, 0.0), Touchdown::Hard);
    assert_eq!(classify_touchdown(6.1, 0.0, 0.0), Touchdown::Crash);
    assert_eq!(classify_touchdown(0.5, 3.5, 0.0), Touchdown::Crash);
    assert_eq!(classify_touchdown(0.5, 0.1, 25.0), Touchdown::Crash);
}
```

- [ ] **Step 2: FAIL** → **Step 3: implement** `forces.rs`: build the jet
table per the geometry rule; `forces()` sums DPS force (thrust · trimmed
+X dir, applied at `(ENGINE_MOUNT_M, 0, 0)` → torque via cross), each
firing jet's force/torque, rotates net body force into MCI via `s.att`,
adds `gravity(s.pos)`, `alpha = (τ − ω×(I∘ω)) / I` componentwise for the
diagonal inertia. `touchdown.rs`: threshold ladder. Trim angle integration
(`TRIM_RATE` under ch012 bits, clamp ±TRIM_MAX) lives in Task 13's SimCore
(discrete actuator, not part of `forces`).

- [ ] **Step 4: PASS** → **Step 5: Commit** — `"feat(dynamics): DPS/RCS force model, jet table, touchdown classifier"` (+ trailer).

---

### Task 10: `eagle-sensors` — PIPA, IMU gimbals, CDU

**Files:**
- Create: `runtime/crates/eagle-sensors/Cargo.toml` (deps: `eagle-dynamics`, `eagle-agc-protocol`, both `path`), `src/lib.rs`, `src/pipa.rs`, `src/imu.rs`
- Modify: `runtime/Cargo.toml` (members += eagle-sensors)

**Interfaces:**
- Produces (used by Task 13):
  - `pub struct Pipa { … }` — `pub fn step(&mut self, dv_sm: V3<Sm>) -> [i32; 3]` (signed pulse counts this tick; carry-forward remainder, zero accumulation error)
  - `pub struct Imu { … }` — `pub fn new(sm_to_mci: Rot<Sm, Mci>) -> Self`; `pub fn gimbals_deg(&self, att: &Rot<Body, Mci>) -> [f64; 3]`; `pub fn apply_coarse(&mut self, axis: CduAxis, signed_pulses: i32)`; `pub fn apply_gyro(&mut self, raw: u16)`; `pub fn sm_to_mci(&self) -> Rot<Sm, Mci>`
  - `pub struct Cdu { … }` — `pub fn step(&mut self, gimbals_deg: [f64; 3]) -> Vec<Packet>` (fast PCDU/MCDU, ≤ 64 pulses/axis/tick, fixed X→Y→Z order, carry-forward)

**Step 0:** transcribe the gimbal transform from
`Contributed/LM_Simulator/modules/AGC_IMU.tcl:614-627`
(`Transform_BodyAxes_StableMember`) — that matrix defines which CDU axis is
which gimbal and the angle sequence; cite the lines in `imu.rs`. Pin the
gyro-word packing from `agc_engine.c:2354-2390` for `apply_gyro`.

- [ ] **Step 1: Failing tests:**

```rust
#[test]
fn pipa_zero_accumulation_error() {
    let mut p = Pipa::default();
    let mut emitted = [0i64; 3];
    let mut total = 0.0f64;
    for i in 0..10_000 {
        let dv = 0.001 + 0.0001 * (i % 7) as f64; // awkward fractions of PIPA_INCR
        total += dv;
        let out = p.step(V3::new(dv, -dv / 3.0, 0.0));
        for (e, o) in emitted.iter_mut().zip(out) { *e += o as i64; }
    }
    let err = (emitted[0] as f64 * PIPA_INCR - total).abs();
    assert!(err < PIPA_INCR, "carry lost: {err}");
    assert!(p.residual_x().abs() < PIPA_INCR);
    assert_eq!(emitted[2], 0);
}

#[test]
fn gimbals_zero_when_body_equals_sm() {
    let sm: Rot<Sm, Mci> = retag(Rot::<Sm, Sm>::identity()); // frames::retag
    let imu = Imu::new(sm);
    let g = imu.gimbals_deg(&Rot::identity());
    assert!(g.iter().all(|a| a.abs() < 1e-12));
}

#[test]
fn single_axis_rotation_hits_single_gimbal() {
    // exact axis↔gimbal pairing comes from the AGC_IMU.tcl transform (Step 0);
    // write one test per axis: rotate body 10° about the axis, assert exactly
    // one gimbal reads ±10° and the others ~0. Pin signs from the tcl.
}

#[test]
fn cdu_budget_and_convergence() {
    let mut c = Cdu::default();
    // 5° step on X: 5 / (360/32768) ≈ 455 pulses → 8 ticks at 64/axis
    let mut sent = 0usize;
    for tick in 0..20 {
        let pk = c.step([5.0, 0.0, 0.0]);
        assert!(pk.len() <= 64 * 3, "budget");
        sent += pk.len();
        if pk.is_empty() { assert!(tick >= 7, "converged too fast?"); break; }
    }
    assert_eq!(sent, (5.0 / CDU_INCR_DEG).round() as usize);
    // all packets are fast-mode PCDU on CDUX
    // (spot-check first packet equals cdu_pulse(CduAxis::X, true, true))
}

#[test]
fn coarse_align_shifts_gimbal_reference() {
    let mut imu = Imu::new(Rot::identity_retagged());
    imu.apply_coarse(CduAxis::X, 100); // 100 × 0.043948°
    let g = imu.gimbals_deg(&Rot::identity());
    assert!((g[0] - (-100.0 * COARSE_INCR_DEG)).abs() < 1e-9
         || (g[0] - 100.0 * COARSE_INCR_DEG).abs() < 1e-9); // sign pinned in Step 0
}
```

- [ ] **Step 2: FAIL** → **Step 3: implement**. `Pipa`: per-axis f64
residual accumulator, truncate-toward-zero to pulses (LM_Simulator
algorithm, `AGC_IMU.tcl:635-653`). `Imu`: store `sm_to_mci` + gimbal
offsets; `gimbals_deg` computes `Rot<Sm, Body> = sm_to_mci.then(att.inverse())`,
extracts the tcl's gimbal sequence angles, adds offsets. `Cdu`: per-axis
emitted-pulse i64, target = round(angle/CDU_INCR_DEG), delta capped ±64,
`cdu_pulse(axis, positive, /*fast=*/true)` repeated |delta| times.

- [ ] **Step 4: PASS** (`cargo test -p eagle-sensors`) → **Step 5: Commit** — `"feat(sensors): PIPA quantizer, IMU gimbal model, CDU pulse feed"` (+ trailer).

---

### Task 11: `eagle-sensors` — seeded error models (default OFF)

**Files:**
- Create: `runtime/crates/eagle-sensors/src/errors.rs`; deps += `rand = "0.8"`, `rand_chacha = "0.3"`

**Interfaces:**
- Produces (used by Tasks 12, 13):
  - `#[derive(serde? no — plain)] pub struct ImuErrorCfg { pub accel_bias_mps2: [f64; 3], pub accel_scale_ppm: [f64; 3], pub accel_noise_sigma_mps2: f64, pub seed: u64 }` with `Default` = all zeros (OFF)
  - `pub struct ImuErrors { … }` — `pub fn new(cfg: ImuErrorCfg) -> Self`; `pub fn corrupt(&mut self, dv_sm: V3<Sm>, dt: f64) -> V3<Sm>`

- [ ] **Step 1: Failing tests:** OFF config is bit-exact identity (`corrupt(v, dt) == v` for a range of inputs); same seed → identical sequences across two instances; bias integrates: with bias = 0.01 m/s² on X and 1000 × 10 ms ticks of zero true ΔV, accumulated ΔV ≈ 0.1 m/s ± 1e-9; noise with sigma > 0 changes outputs but stays zero-mean-ish over 10⁴ samples (|mean| < 5 sigma/√n).
- [ ] **Step 2: FAIL** → **Step 3: implement** (`ChaCha8Rng::seed_from_u64`; `corrupt = (dv + bias·dt) ∘ (1 + scale·1e-6) + N(0, sigma·√dt)` per axis; the OFF path must short-circuit before touching the RNG so it is bit-exact and RNG-state-free).
- [ ] **Step 4: PASS** → **Step 5: Commit** — `"feat(sensors): seeded IMU error models, default off"` (+ trailer).

---

### Task 12: Scenario loader + `p66-gate.toml`

**Files:**
- Create: `runtime/apps/eagle-runtime/src/scenario.rs` (`pub mod scenario;`), `scenarios/p66-gate.toml`

**Interfaces:**
- Produces (used by Tasks 13, 14, 16): `pub struct Scenario` (serde, `deny_unknown_fields` on every struct) mirroring this file exactly:

```toml
schema = 1
name = "p66-gate"

[site]
lat_deg = 0.674          # Tranquility Base; historical
lon_deg = 23.473         # historical
radius_m = 1737400.0     # assumed (mean lunar radius)

[gate]
alt_m = 500.0            # assumed
vz_ms = 0.0              # hover release (freeze-until-engine-on)
mass_dry_kg = 7009.0     # derived: descent dry 2339 + ascent stage wet 4670 (LM_Simulator masses)
fuel_dps_kg = 2000.0     # derived (partial descent load at the gate)
fuel_rcs_kg = 150.0      # derived
inertia_kgm2 = [12000.0, 13500.0, 13000.0]  # assumed (order-of-magnitude from LM_Sim alpha model)

[agc]
padload = "scenarios/p66-padload.toml"
lm_weight_lbs = 20200.0            # derived: (7009+2000+150) kg ≈ 20190 lbs → V48/N47
tland_offset_cs = 12000            # TIG target ≈ boot+120 s; spike-A calibrated
flip_atthold_after_engine_on_s = 2.0   # spike-B calibrated

[rod]
steps = [[400.0, -3.0], [150.0, -1.5], [30.0, -1.0]]  # alt_m → target sink rate m/s

[errors]                 # empty table = all OFF (acceptance runs use this)

[acceptance]
v_vert_max = 3.0
v_horiz_max = 1.5
tilt_max_deg = 12.0
timeout_s = 300.0
```

`[errors]` optionally contains `[errors.imu]` mapping 1:1 onto `ImuErrorCfg` (Task 11). `pub fn load(path: &Path) -> Result<Scenario>`; helper `pub fn site_unit_mcmf(&self) -> V3<Mcmf>` (from lat/lon); `pub fn initial_state(&self, epoch_s: f64) -> LmState` (site + alt·up in MCI at epoch, velocity vz·up, attitude body+X = up, omega 0).

- [ ] **Step 1: Failing tests:** parse the committed file (`include_str!` relative to the repo — use a path constant + `CARGO_MANIFEST_DIR`); unknown field anywhere → error (fixture string with a typo field); `[errors]` empty → `None`/default OFF; `initial_state` altitude: `pos.norm() == radius_m + alt_m` ±1e-6, velocity vertical, `att.apply(body_x)` parallel to `pos.unit()`.
- [ ] **Step 2: FAIL** → **Step 3: implement** (plain serde structs + the two geometry helpers via `eagle-dynamics::frames`).
- [ ] **Step 4: PASS** → **Step 5: Commit** — `"feat(runtime): TOML scenario loader + p66-gate scenario"` (+ trailer).

---

### Task 13: SimCore + dedicated sim thread

**Files:**
- Create: `runtime/apps/eagle-runtime/src/sim.rs` (`pub mod sim;`)
- Modify: `runtime/apps/eagle-runtime/Cargo.toml` (deps += `eagle-sensors` path)

**Interfaces:**
- Consumes: everything above (dynamics, sensors, agc_io, scenario, `ThrustResponder` from runner.rs — move it into `sim.rs` and re-export from runner for the spike tests, or leave and import; keep ONE definition).
- Produces (used by Tasks 14, 16):
  - `pub enum SimIn { Agc(AgcOutput), Dsky(DskyStateSnapshot) }` where `DskyStateSnapshot` carries `mm: String` and the P66 nav display fields (noun + R-registers as parsed strings — the exact noun/registers/scaling were pinned in Spike B; implement the parser here as `fn parse_agc_nav(d: &DskyState) -> Option<AgcNav>` with `pub struct AgcNav { pub alt_m: Option<f64>, pub hdot_ms: Option<f64> }`)
  - `pub struct SimCore { … }` — `pub fn new(sc: &Scenario, epoch_s: f64) -> Self`; `pub fn ingest(&mut self, ev: SimIn)`; `pub fn tick(&mut self) -> SimTickOut`
  - `pub struct SimTickOut { pub to_agc: Vec<Packet>, pub telemetry: Option<TelemetryMsg>, pub touchdown: Option<Touchdown> }`
  - `pub fn spawn_sim(core: SimCore, in_rx: std::sync::mpsc::Receiver<SimIn>, agc_tx: tokio::sync::mpsc::UnboundedSender<Packet>, telem_tx: tokio::sync::broadcast::Sender<String>) -> SimHandle` — `in_rx` comes from `std::sync::mpsc::sync_channel(4096)` (spec §6: bounded); the tokio side uses `try_send` and counts drops (drop count goes into telemetry as `ingest_drops`, add the field to TelemetryMsg in Task 14) — std::thread, 10 ms wall-paced (`next += DT; sleep(next − now)`, no drift accumulation), drains `in_rx` each tick (`try_recv` loop), sends `to_agc` packets, serializes telemetry to JSON on the shared broadcast; `SimHandle { pub join: JoinHandle<SimResult>, pub stop: std::sync::mpsc::Sender<()> }`; thread exits on stop signal, channel close, or touchdown+2 s, returning `SimResult { pub touchdown: Option<(Touchdown, f64 /*v_vert*/, f64 /*v_horiz*/, f64 /*tilt_deg*/)> }`.

**SimCore tick order (FIXED, document in code):**
1. apply queued discrete actuator changes from ingested events: jets mask (ch5/6), engine on/off, trim bit states, ThrustResponder bookkeeping, coarse/gyro → Imu.
2. trim integration: active trim bits move `trim_pitch/roll` at TRIM_RATE_DEG_S, clamp ±TRIM_MAX.
3. throttle: `throttle_cmd_n = cmd_pulses · THRUST_N_PER_PULSE`; `actuator_step` (lag+envelope); zero if `!engine_on || fuel_dps == 0`.
4. **frozen?** until first `Engine { on: true }`: state pinned; specific force = hover support `+1.62 m/s²` body +X.
5. else `step_rk4` with `forces()`.
6. sensors: `dv_sm = (specific_force_body · dt)` rotated Body→SM via `imu`; `errors.corrupt`; `pipa.step` → PIPA packets; `cdu.step(imu.gimbals_deg(att))` → CDU packets.
7. `ThrustResponder::tick_packets()` (DINC strobe).
8. ROD schedule: crossing an alt threshold queues `round(Δtarget / 0.3048)` clicks; emit one press per tick with its release the following tick.
9. drift: downlink events counted; `drift_ms = (downlink_words/2/50 − t_sim)·1000`.
10. every 10th tick → TelemetryMsg; touchdown check (alt_agl ≤ 0 → classify from LSITE velocity + tilt, then hold state).

- [ ] **Step 1: Failing tests** (pure, no AGC, no threads — drive `SimCore` directly):

```rust
#[test] fn frozen_until_engine_on_then_falls() { /* 100 ticks: pos unchanged, PIPA≈hover
    pulses; ingest Engine{on}; 100 ticks at zero thrust cmd: vz goes negative */ }
#[test] fn closed_hover_with_thrust_pulses() { /* ingest ThrustDrive + feed Pout pulses
    ≈ mass·g/scale: after 3000 ticks |vz| < 0.2 m/s — the 1-D loop from Spike B,
    now through the full 6-DoF core */ }
#[test] fn cdu_and_pipa_packets_flow_and_are_bounded() { /* per-tick to_agc counts:
    PIPA ≤ ~5, CDU ≤ 192, DINC ≤ 32 */ }
#[test] fn rod_schedule_emits_click_trains_at_thresholds() { /* run descent past 400 m:
    presses+releases alternate; total clicks = Δtarget/0.3048 rounded */ }
#[test] fn telemetry_every_100ms_and_determinism() { /* two identical runs → byte-identical
    serialized telemetry sequences */ }
#[test] fn touchdown_terminates_with_classification() { /* start at 2 m, no thrust →
    Crash/Hard depending on impact speed; SimTickOut.touchdown set once */ }
```

- [ ] **Step 2: FAIL** → **Step 3: implement `SimCore`** exactly in the tick order above (each numbered phase = one private method, called in sequence from `tick` — the order is load-bearing for determinism).
- [ ] **Step 4:** thread-shell test: `spawn_sim` against dummy channels for ~50 real ms → ≥ 3 ticks happened, stop() joins cleanly within 100 ms.
- [ ] **Step 5: PASS all** → **Step 6: Commit** — `"feat(runtime): SimCore 100 Hz closed-loop core + sim thread shell"` (+ trailer).

---

### Task 14: Schema v2, server plumbing, `--scenario` mode

**Files:**
- Modify: `runtime/crates/eagle-schema/src/lib.rs`, `runtime/apps/eagle-runtime/src/server.rs`, `src/main.rs`, `src/runner.rs`
- Test: schema unit tests; `runtime/apps/eagle-runtime/tests/sim_pipeline.rs` (stub-AGC pipeline test, NOT live)

**Interfaces:**
- `eagle-schema`: `pub const SCHEMA_VERSION: u32 = 2;`

```rust
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TelemetryMsg {
    pub schema_version: u32,
    pub t_s: f64,
    pub frozen: bool,
    pub alt_m: f64, pub vz_ms: f64, pub v_horiz_ms: f64, pub tilt_deg: f64,
    pub mass_kg: f64, pub fuel_dps_kg: f64, pub fuel_rcs_kg: f64,
    pub thrust_n: f64, pub throttle_cmd_pulses: i64, pub jets: u16,
    pub mm: String,
    pub agc_alt_m: Option<f64>, pub agc_hdot_ms: Option<f64>,
    pub nav_err_alt_m: Option<f64>, pub nav_err_hdot_ms: Option<f64>,
    pub drift_ms: f64, pub downlink_wps: f64, pub ingest_drops: u64,
    pub touchdown: Option<String>,
}
pub enum ServerMsg { DskyState(DskyStateMsg), Telemetry(TelemetryMsg) }   // same tag style
pub enum ClientMsg { Key { key: String }, Pro { pressed: bool }, Rod { up: bool } }
```

- `server.rs`: `ClientMsg::Rod` → send `rod_click(up)` press, `tokio::spawn` the release after 100 ms. Everything else unchanged (telemetry rides the existing `broadcast<String>` — every frame is already a self-describing tagged JSON).
- `main.rs`: `--scenario <path>` arg (optional). When present: load scenario + symtab + pad-load; construct `pump`-style plumbing; spawn sim thread; spawn `runner::run_scenario(script, scenario, sim_in_tx)` (the productized Task 6+7 choreography: discretes → clock read → generate_state → pad-load → dap_init → V37E63E → responder → att_hold at +`flip_atthold_after_engine_on_s`); forward every AGC packet to: trace, DSKY apply (→ watch + JSON broadcast), `decode_output` → `SimIn::Agc` (and DSKY changes → `SimIn::Dsky`). Without `--scenario`, behavior is exactly Phase 1 (DSKY-only) — `make test-integration`'s Phase 1 tests must stay green.
- Schema-version bump ripples: `DskyStateMsg.schema_version` now 2 — update the Phase 1 tests' expected value and the client reducer's tolerance (client accepts both 1 and 2 during this wave; log-warn on mismatch instead of dropping).

- [ ] **Step 1:** schema tests (serde shape of `ServerMsg::Telemetry` → `{"type":"telemetry", …}`, `ClientMsg::Rod` parse) — FAIL → implement → PASS.
- [ ] **Step 2:** `sim_pipeline.rs` (fast, not `#[ignore]`): spawn the full plumbing with a **stub AGC** (a tokio task that: emits `Engine{on}` after 200 ms, then answers every DINC burst with hover-consistent Pout counts, echoes nothing else). Assert: ≥ 8 telemetry JSON frames per second arrive on the broadcast; frames parse as `ServerMsg::Telemetry`; `frozen` flips false after the stub engine-on; clean shutdown.
- [ ] **Step 3:** run `make test` + Phase 1 `make test-integration` → all green.
- [ ] **Step 4: Commit** — `"feat(runtime): schema v2 telemetry, ROD client input, --scenario mode"` (+ trailer).

---

### Task 15: Client engineer board (uPlot)

**Files:**
- Create: `client/src/telemetry/types.ts`, `useTelemetryBuffer.ts`, `TelemetryPage.tsx`, `StripChart.tsx`, `useTelemetryBuffer.test.ts`
- Modify: `client/src/App.tsx` (tab bar DSKY | ENGR), `client/src/App.css`, `client/src/dsky/useDskySocket.ts` (message dispatch by type), `client/package.json` (deps += `uplot`; the ONE charting dependency allowed by the spec)

**Interfaces:**
- Consumes: WS frames `{"type":"telemetry", …}` (schema v2, Task 14) on the existing socket; `{"type":"rod","up":bool}` client message.
- Produces:
  - `types.ts`: `export interface TelemetryFrame { …mirror TelemetryMsg field-for-field, snake_case… }`
  - `useTelemetryBuffer.ts`: `export function useTelemetryBuffer(): { frames: RingView; latest: TelemetryFrame | null; phases: PhaseChange[]; push: (f: TelemetryFrame) => void }` — ring buffer capacity 3000 (5 min @ 10 Hz) held in a ref; consumers get a monotonically-versioned view; `PhaseChange = { t_s: number; mm: string }` derived on push when `mm` changes.
  - `useDskySocket.ts` gains an optional `onTelemetry?: (f: TelemetryFrame) => void` parameter; dispatch: `msg.type === "dsky_state"` → existing reducer; `"telemetry"` → callback; unknown → ignore (and keep the existing behavior when the callback is absent). Add a `sendRod(up: boolean)` sender beside `sendKey`/`sendPro`.

**TelemetryPage layout** (single column, `side`-panel width rules don't apply — it replaces the whole page content when the ENGR tab is active):
- 4 strip charts (uPlot, 260 px tall each): Altitude (m) | Descent rate (m/s: truth `vz_ms` + AGC `agc_hdot_ms` as second series) | Thrust (N) + jets-active count | Fuel DPS (kg) + drift (ms, right axis)
- numeric panel: mm, t, alt, vz, v_horiz, tilt, mass, thrust, cmd pulses, nav err (alt/hdot), drift, downlink wps, touchdown badge
- phase timeline: `PhaseChange` list (newest first, like the interpreter log)
- ROD buttons: `ROD −1 ft/s` / `ROD +1 ft/s` → `sendRod(false/true)` (labels: − = descend faster; pin the mapping to ch016 bit semantics from Task 1 and say it in a tooltip)

- [ ] **Step 1: vitest first** (`useTelemetryBuffer.test.ts`): push 3100 frames → length capped 3000, oldest dropped; `latest` tracks; `phases` records mm transitions only (63→63 no entry, 63→66 one entry); version increments per push. Also a dispatch test for the socket hook refactor: fabricated `MessageEvent` with a telemetry frame reaches the callback and does NOT disturb DSKY state; unknown type is silently ignored (guard `JSON.parse` in try/catch while here — it is the pending Phase 1 minor).
- [ ] **Step 2: FAIL** (`cd client && npm test`) → **Step 3: implement** buffer + dispatch refactor.
- [ ] **Step 4:** `npm install uplot` (lockfile committed); implement `StripChart.tsx` (thin uPlot wrapper: props `{ title, series: {label, get: (f)=>number|null, color}[], frames }`, `setData` on version change, `overflow-x` safe, dark background consistent with App.css palette) and `TelemetryPage.tsx`; tab state in `App.tsx` (`useState<"dsky"|"engr">`, plain buttons styled like `.panel h2`).
- [ ] **Step 5:** `npm test` PASS + `npm run build` clean (type errors are failures).
- [ ] **Step 6:** Manual check (documented in the task report, needs Task 14 running with `--scenario` or the stub pipeline): both tabs render, charts scroll, ROD buttons emit WS messages (browser devtools).
- [ ] **Step 7: Commit** — `"feat(client): engineer telemetry board with strip charts and ROD input"` (+ trailer).

---

### Task 16: Closed-loop acceptance, make targets, docs

**Files:**
- Create: `runtime/apps/eagle-runtime/tests/live_p66_descent.rs` (port **19904**, `#[ignore]`)
- Modify: `Makefile`, `README.md` (if present under eagle/), `CLAUDE.md`, `docs/agc-channel-map.md`

**Acceptance test** (the Wave 1 DoD; errors OFF):
1. Boot yaAGC + pump + sim thread + `run_scenario` with `scenarios/p66-gate.toml` — the same code path as `--scenario` mode (factor a `pub async fn run_headless(scenario: &Path, agc_port: u16, trace: Option<PathBuf>) -> Result<SimResult>` into `runner.rs` in this task; `main.rs --scenario` becomes a caller of it).
2. Collect: DSKY MM transitions, alarm episodes (PROG lamp + `alarm_codes` on each episode), `SimResult`.
3. Assert, in order:
   - MM sequence contains `"63"` then `"66"` (intervening MMs allowed but logged);
   - touchdown occurred before `acceptance.timeout_s` and classified `Nominal` with the spec numbers (v_vert < 3.0, v_horiz < 1.5, tilt < 12.0 — read the thresholds FROM the scenario file, don't restate them);
   - alarm episodes ⊆ `SPIKE_A_ALARM_WHITELIST ∪ SPIKE_B_ALARM_WHITELIST`;
   - |drift_ms| < 500 at touchdown; downlink_wps in [40, 60] mid-run;
   - wall time of the whole test < 300 s (budget guard).
4. Write the JSONL trace to `build/traces/p66-acceptance.jsonl` (git-ignored) — the raw material for Wave 2 notebooks.

**Error-model scenario run (spec §8, "graceful behavior only"):** add
`scenarios/p66-gate-imu-bias.toml` (same gate, `[errors.imu]` with
`accel_bias_mps2 = [0.0005, 0.0002, 0.0]`, `seed = 42` — derived, mild) and
a second live test in the same file gated behind `EAGLE_SLOW=1`: the run
must complete without panic, without non-whitelisted alarms, and reach
touchdown (any classification — graceful degradation, not accuracy). Not
part of default `make test-integration` (CI budget); documented in CLAUDE.md.

- [ ] **Step 1:** implement `run_headless` refactor + the test; run `cargo test -p eagle-runtime --test live_p66_descent -- --ignored --test-threads=1` until green **3 consecutive times** (this is the flake bar for the wave's flagship test).
- [ ] **Step 2:** Makefile:

```make
descent-p66: agc
	cd runtime && cargo run -p eagle-runtime -- \
	  --yaagc ../build/agc/yaAGC --core ../build/agc/Luminary099.bin \
	  --scenario ../scenarios/p66-gate.toml
```

(`test-integration` needs no change — it already sweeps `--ignored` serially; confirm the new tests are included and the TOTAL integration wall time stays ≤ 10 min; if over, gate the two spike tests behind `EAGLE_SPIKES=1` env and document.)
- [ ] **Step 3:** Docs: CLAUDE.md run/verify additions (`make descent-p66`, scenario/pad-load file locations, spike env var if introduced); `docs/agc-channel-map.md` final pass (every channel/counter this wave touched, with citations and "verified live" markers); README quickstart (play: dev-runtime with --scenario + dev-client, ENGR tab, ROD buttons).
- [ ] **Step 4:** Full DoD run: `make test` AND `make test-integration` both green, recorded in the task report.
- [ ] **Step 5: Commit** — `"feat(eagle): wave 1 acceptance — Luminary099 P66 soft landing closed loop"` (+ trailer).

---

## Execution notes for the controller

- Task order is risk-first and MUST be respected: 1→2→3→4→5→6→7 before any
  of 8-16 (the spikes gate the wave; their BLOCKED outcome changes the plan).
  8-11 are independent of each other after 3; 12 needs 11; 13 needs 8-12;
  14 needs 13; 15 needs 14; 16 needs everything.
- Model policy (per subagent-driven-development): transcription-heavy tasks
  (1, 2, 8, 9, 11, 12) → cheapest tier; integration tasks (3, 4, 5, 10, 13,
  14, 15) → mid tier; spikes 6, 7 and final review → most capable tier.
  Spikes are long-running interactive tasks — dispatch them with explicit
  permission to iterate live and to write ledger entries.
- The two spikes may amend earlier constants (THRUST_N_PER_PULSE, RODSCALE,
  INIT_CH30) — such amendments are in-scope for their review, not scope creep.
- Phase 1 regression: `make test` + Phase 1 integration tests must stay green
  after every task; a task that breaks them is not done.
