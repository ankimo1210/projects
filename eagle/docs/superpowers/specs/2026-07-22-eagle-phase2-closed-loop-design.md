# EAGLE Phase 2 — Headless Closed Loop: P63→P66 Descent Design

**Date:** 2026-07-22
**Status:** Approved (brainstorming session "apollo")
**Parent docs:** roadmap spec `2026-07-21-eagle-roadmap-design.md` (Phase 2+3
guidance scope merged into this phase by user decision); architecture spec
v0.1 §5.3–5.4, §6 (authoritative reference for dynamics/sensor/time design)

---

## 1. Decisions made in this session

| Topic | Decision |
|---|---|
| Scope | Full descent **P63 (braking) → P64 (approach) → P66 (ROD) → touchdown**, pulled forward from the roadmap's Phase 3. Implemented in two waves (§2). |
| Sensor fidelity | Exact quantization/scaling/sign/timing semantics (non-negotiable correctness core) **plus** IMU bias/scale/noise and radar noise/dropout error models — config-gated per scenario, seeded (ChaCha), **default OFF**. Provenance tags per architecture spec §8.3. |
| Time synchronization | **Approach A — real-time coupling.** Stock yaAGC self-paced; Rust physics fixed-step 100 Hz pinned to wall clock; counter I/O over the existing socket session. Continuous AGC-vs-physics drift measurement telemetered. Lockstep rejected (F5 descoped; vendor read-only). |
| AGC initial state (P63 entry) | Build via **digital uplink pad-load** (historically authentic, automated over the socket), then freeze as a **yaAGC resume snapshot** per scenario for deterministic fast starts. Two-mechanism fallback is deliberate risk control. |
| Telemetry | **Engineer-board lite**: new web-client page (strip charts: altitude, descent rate, fuel, truth-vs-nav error; guidance phase timeline; numeric panel; drift meter) at 10 Hz over the existing WebSocket, new `{"type":"telemetry"}` frame. AGC-internal symbol readout (engineer mode proper) stays in Phase 4. |
| Initial conditions | Synthetic-but-plausible PDI state (~15 km altitude, orbital velocity), provenance `assumed`/`derived`. Historical calibration is Phase 4. |
| Success criteria (acceptance) | Errors OFF, real Luminary099 flies P63→P64→P66 to touchdown with vertical < 3 m/s, horizontal < 1.5 m/s, tilt < 12° (roadmap placeholders, now adopted), no unexpected AGC alarms. Judged on truth state. |
| Docs policy | Specs/plans are now **committed** (supersedes the Phase 1 "don't commit" decision — they became tracked on main via the parallel session; keeping them tracked is the consistent state). |

## 2. Two implementation waves

**Amended 2026-07-23** after vendor research (agc_engine.c, LM_Simulator,
Luminary099 source; citations in the Wave 1 plan). Three findings forced a
restructure, decided with the user (option: "keep P66 in Wave 1"):

1. P66 is **not V37-selectable** — the V37 table lists only P63 among
   descent programs (`FRESH_START_AND_RESTART.agc:1072-1102`). P66 is
   reached only via GUILDENSTERN (R13) while SERVICER/AVERAGE-G runs,
   i.e. after P63/BURNBABY ignition, and requires pad-loaded erasables
   with no in-rope writer (RODSCALE, TAUROD, LAG/TAU, MIN/MAXFORCE) plus
   REFSMMAT/state vector/mass.
2. yaAGC does **not emit the DPS throttle** on the socket (ch 014 bit 4
   unhandled). The sim must play the throttle-drive electronics: strobe
   DINC unprogrammed sequences at counter 055 and integrate the returned
   POUT/MOUT pulses. Grounded in `agc_engine.c` but unproven — needs an
   early live spike.
3. The vendor oracle LM_Simulator closes only the **P00 DAP attitude
   loop** (manual throttle slider, no erasable init) — it validates our
   sensor/RCS plumbing but not the throttle loop or descent entry.

- **Wave 1 — plumbing + forced-P66 descent:** dynamics, sensors
  (IMU/PIPA/CDU), DPS/RCS actuation, THRUST DINC-strobe protocol,
  DSKY-scripted erasable init (V21N01 pad-load harness + discretes +
  V48 DAP setup), P63 ignition spike, then forced ATT-HOLD → P66 descent
  from a hover-release gate (~500 m) to touchdown; scenario loader and
  telemetry board. Risk-first ordering: the ignition/P66/THRUST spike
  runs against a synthetic hover feed before the full physics lands.
- **Wave 2 — full descent:** landing radar (beams, gating, quantization,
  AGC read sequence), digital-uplink pad-load automation + resume
  snapshots, genuine P63/P64 guidance flight from PDI, mid-phase
  acceptance scenario, full-descent manual target, trace notebooks.

Each wave gets its own implementation plan (writing-plans → SDD execution).

## 3. Coordinate frames and units

Documented in `eagle/docs/coordinate-frames.md` (new, with this phase):

| Frame | Role |
|---|---|
| MCI (moon-centered inertial) | physics integration frame |
| MCMF (moon-fixed) | terrain, landing site |
| LSITE (site-local, East-North-Up) | telemetry, success criteria |
| BODY (LM structural) | thrust, inertia |
| SM (IMU stable member) | REFSMMAT-related; CDU angles generated here |

- Rust enforces frames with typed newtypes (`Vec3<Mci>`, quaternion types
  tagged with from/to frames). No anonymous vectors (architecture spec §5.3).
- SI units internally. **AGC-unit conversion happens exactly once, at the
  counter codec boundary** (PIPA cm/s-per-pulse, CDU arcsec-per-pulse, radar
  scalings) — exact values fixed at implementation time from vendor sources
  with citations in `docs/agc-channel-map.md` (Phase 1 Step-0 protocol).
- AGC clock set from scenario epoch at start; drift measured continuously.

## 4. Dynamics (`eagle-dynamics`, pure crate)

- Rigid-body 6-DoF; **RK4, fixed 10 ms step, fixed evaluation order**.
- Point-mass lunar gravity (harmonics Phase 4; `assumed`).
- DPS: first-order throttle lag; real thrust envelope (10–60% throttleable
  band + fixed FTP); constant Isp; mass/inertia updated from flow.
- RCS: 16 on/off jets, minimum impulse width, jet selection driven directly
  by AGC channel output.
- Touchdown: no gear model in Phase 2 — classify at surface contact from
  velocity/tilt into nominal / hard / crash (gear stroke Phase 4).
- Error models live in `eagle-sensors`, not here; dynamics is deterministic.

## 5. Sensors and AGC I/O (`eagle-sensors` + runtime)

- **PIPA**: body-frame accumulated ΔV → pulse counts with carry-forward
  remainder (zero accumulation error), PINC/MINC counter packets.
- **IMU/CDU**: stable-member gimbal simulation from REFSMMAT; gimbal angles →
  CDU counter pulses.
- **Actuation decode**: RCS jet channels, engine on/off, throttle
  increment counter, trim gimbal — semantics confirmed against
  `vendor/virtualagc/yaAGC/agc_engine.c` **and the Contributed/LM_Simulator
  reference implementation in the vendor tree** before tests lock in
  (mandatory Step-0 per task; vendor source wins; citations recorded).
- **Landing radar (Wave 2)**: altitude beam + 3 velocity beams derived from
  truth; attitude/altitude validity gating; quantization; data-good
  discretes; responds to the AGC's radar read sequence.
- **Error models**: IMU bias/scale-factor/noise, radar noise/dropouts —
  scenario-configured, seeded, default OFF.

## 6. Runtime and threading

- Dedicated **sim thread** (not tokio): 10 ms tick loop — ingest AGC output
  events, integrate, quantize sensors, emit counter inputs, publish
  telemetry — bounded channels to the AGC session and WS broadcaster
  (architecture spec §5.1 thread model, minus recorder thread which reuses
  Phase 1 tracing).
- Scenario runner: loads YAML (initial state, error config, success
  criteria), prepares/loads the AGC resume snapshot, arms the run.

## 7. Telemetry board (client) and schema v2

- `eagle-schema` v2 adds `{"type":"telemetry"}` frames (10 Hz): truth
  pos/vel/attitude/mass/fuel, AGC-observable nav values (no internal-symbol
  reads until Phase 4), guidance phase, radar state, throttle/RCS activity,
  clock drift. DSKY messages unchanged.
- Client gains a telemetry page: strip charts (altitude, descent rate, fuel,
  truth-vs-nav error), phase timeline, numeric panel. One charting
  dependency maximum, chosen at implementation with dataviz guidance.

## 8. Test strategy

- **Unit/property (fast, no AGC):** integrator convergence + energy sanity;
  PIPA/CDU quantization round-trip with zero carry loss; throttle envelope
  clamp; fuel non-negative; mass monotone; quaternion norm; radar gating.
- **Closed-loop acceptance (live, serial, errors OFF):** Wave 1 = P66-only
  descent (~2 min); Wave 2 = mid-descent start (late P63 → touchdown,
  ~3–5 min). Deterministic event-order judgment on truth state + AGC health
  (no unexpected alarms).
- **Full descent** (~12 min real time): manual `make descent-full` target
  with trace capture; not in CI.
- **Error-model scenarios (seeded):** one radar-dropout and one IMU-bias
  run asserting graceful behavior only.
- **Notebooks:** trajectory/guidance-error/fuel post-analysis from JSONL
  traces.

## 9. Risks

| Risk | Mitigation |
|---|---|
| P63-entry erasable initialization deeper than expected | **(2026-07-23: risk confirmed — P66 needs P63 ignition + pad load.)** Wave 1 uses DSKY V21N01 scripted loads with V01N01 read-back verification and an alarm-driven iteration protocol; digital uplink + resume snapshots remain Wave 2 |
| THRUST DINC-strobe protocol unproven (yaAGC never exercised this path in a closed throttle loop) | Dedicated early live spike (synthetic hover feed, before full physics); protocol semantics cited from agc_engine.c |
| Throttle/radar channel semantics misread | LM_Simulator in the vendor tree is a working oracle for jets/IMU/discretes (NOT throttle); mandatory per-task Step-0 verification with citations |
| Real-time test duration | Mid-phase acceptance scenarios keep CI ≤ 5 min; full run manual |
| AGC nav divergence hard to debug | truth-vs-nav error on the telemetry board from day one; drift meter |
| Noise vs determinism | Error models seeded and OFF by default; acceptance runs errors-OFF |
