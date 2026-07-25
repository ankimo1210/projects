# EAGLE Phase 2 Wave 2 — Real Descent Design

**Date:** 2026-07-26
**Status:** approved (brainstorming session)
**Supersedes:** the Wave 2 sketch in
`docs/superpowers/specs/2026-07-22-eagle-phase2-closed-loop-design.md` §2,
which predates the Wave 1 re-flight findings.

## 1. Why this wave exists

Wave 1 built the whole closed loop and it runs end to end — boot → pad load
→ P63 → ENGINE ON → ATT HOLD → ground contact — but the acceptance is RED
and cannot be tuned green. The 2026-07-25 re-flight
(`docs/superpowers/notes/2026-07-25-wave1-reflight.md`) measured three
causes and eliminated the one the plan had assumed:

- **The attitude loop is not broken.** `EAGLE_ATT_DEBUG` shows the DAP
  slewing IGA −16.8° → +108.4° at its rate limit with every jet opposing
  the error, then holding 107.35° ± 1.7° for 13 s. That is capture of a
  *commanded* attitude, not divergence. Jet quantization, inertia/lever
  magnitudes and trim signs are all exonerated. **Do not spend time here.**
- **Cause A — DPS idle stop.** `dps_envelope` mapped below-band commands to
  zero thrust, but Luminary does not throttle up until `FLATOUT` at
  TIG+ZOOMTIME, so the engine produced nothing for the whole burn. Fixed in
  Wave 1's review branch (commit `c7513cb1`).
- **Cause B — ZOOMTIME gate.** `P63TABLE`'s `AVEGEXIT` is `2CADR SERVEXIT`
  until `P63ZOOM` swaps it to `LUNLAND`
  (`BURN,_BABY,_BURN...agc:143-144,573-575`), and GUILDENSTERN is R13 right
  behind `LUNLAND` (`LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:127-144`). No
  landing-guidance pass, therefore no P66, until TIG+26 s. A 500 m gate
  reaches the ground first. Tunable — `live_spike_p66.rs` already starts at
  3000 m for exactly this reason.
- **Cause C — no navigation loop closure.** The pad-loaded state vector is
  the historical PDI point (15.2 km, 1699.5 m/s) while the sim truth is a
  500 m hover. Measured: the AGC read V06N63 R2 = +00213…+00266, believing
  it was **climbing at +6.5…+8.2 m/s**, while the truth fell at up to
  43 m/s. And P66 *holds attitude and never re-orients*, so the vehicle
  arrives carrying `IGNALG`'s 1700 m/s braking attitude — 107-108° from
  local vertical, DPS aimed sideways and slightly down. **No gate altitude
  fixes this.**

Cause C is the subject of this wave. The fix chosen by the user is the only
variant where the AGC's navigation and the sim truth agree by construction:
**fly the real descent.** Initialise truth to the same PDI state the
pad-load describes and let P63 → P64 → P66 run for real.

## 2. Scope

**In:** truth-at-PDI, full P63 → P64 → P66 flight, landing radar, resume
snapshots, a snapshot-based acceptance test, a full-descent manual target.

**Out:** digital-uplink pad-load automation (INLINK ch 0173 + UPRUPT — the
existing DSKY-scripted V21N01 loader is proven and stays); terrain (the moon
stays spherical); P65/P67; the 3D client; Wave 1's carried-forward minor
findings.

**Definition of done:** the real Luminary099 flies from PDI through
P63 → P64 → P66 reading the landing radar, and soft-lands. The acceptance
test is green twice consecutively.

**One spec, three implementation plans.** Each milestone below produces
working, testable software on its own and depends on the previous one's
measured output, so each gets its own plan and SDD execution cycle rather
than one 18-task mega-plan. M1's plan is written first; M2's and M3's are
written after their predecessor's findings are recorded, because both
depend on numbers M1 measures.

## 3. Milestones (risk-first — this ordering is load-bearing)

The wave runs in three milestones. The ordering was chosen over
"LR first" and "snapshot first" for concrete reasons:

- **M1 must be first** because it decides whether cause C is really
  fixable. If P63 guidance will not converge from a PDI truth state, both
  other milestones are worthless and the wave needs redesigning. M1 changes
  the least to find out.
- **M1 before M3** because M1's recorded flight becomes the LR model's
  ground truth: at each logged altitude and velocity the beam values are
  recomputable offline, so LR unit tests come from a real trajectory rather
  than invented numbers.
- **Snapshot cannot be first** — a descent you cannot yet fly cannot be
  snapshotted.

### M1 — Truth at PDI, radar bypassed

Fly P63 → P64 → P66 to touchdown on pure inertial navigation, with the
landing radar bypassed in-rope.

**Single source for the state.** Today `Scenario::initial_state` builds a
hover over the site while `padload::generate_state` independently computes
the LUM69R2 PDI point. Those two describing different vehicles *is* cause C.
Add to `padload.rs`:

```rust
pub fn truth_state(cfg: &StateCfg, epoch_s: f64) -> LmState
```

returning the same orbit-plane geometry `generate_state` already derives —
`a = R_SITE + rign_x`, `b = -rign_z`, `theta = b.atan2(a)`,
`r_orb = a.hypot(b)`, inertial speed `v_ign + ω·r_orb`. A unit test pins
that both functions report the same θ, r and v; fixing one without the
other must fail the suite.

**Scenario schema.** Every struct is `deny_unknown_fields`, so each field is
an explicit addition:

- `[gate] mode = "pdi" | "hover"`. `"hover"` is the existing path, kept so
  the p66-gate scenarios still load and Wave 1's tests keep passing.
  `"pdi"` ignores `alt_m`/`vz_ms` and takes its state from `StateCfg`.
- PDI masses: `fuel_dps_kg ≈ 8200` (LM-5 DPS propellant at PDI), total
  ≈ 15,100 kg. Provenance tags required (`historical` / `derived` /
  `assumed`) per project convention.
- `[agc] lrbypass = true`. `run_scenario` calls the existing
  `set_flag_bits(script, FLAGWRD11_ECADR, LRBYBIT)` — the same one-line
  shape as `REFSMBIT` and the moon flags. `LRBYPASS` is FLAGWRD11 bit 15
  (`FLAGWORD_ASSIGNMENTS.agc:1051-1052`, "BYPASS ALL LANDING RADAR
  UPDATES"). **The implementer must verify FLAGWRD11's ECADR against
  `build/agc/Luminary099.log`** — `STATE+11` suggests `0o107`, but this
  project's Step-0 rule forbids shipping a derived address unverified.
- `[handover] alt_m` — during P64, crossing this altitude triggers
  ATT HOLD + the selection ROD click into P66. Default ~150 m (500 ft),
  following the historical takeover. `historical` provenance. The watch is
  armed when MM64 is first observed and fires on the altitude crossing. If
  MM65 appears before the crossing, the run records it as a finding rather
  than silently handing over from a different mode — P65 is out of scope
  and its appearance means the handover altitude needs revisiting.

**Freeze is disabled in PDI mode.** `SimCore`'s freeze-until-engine-on
existed to keep AVERAGE-G consistent with a hover start. With truth already
on a correct orbital trajectory the freeze is not merely unnecessary but
wrong: a pinned position diverges from the AGC's integrating navigation
before ignition. PDI mode runs free from t=0. This also removes, on the PDI
path, the Wave 1 inconsistency where the freeze pinned attitude while CDU
pulses kept flowing.

**ROD schedule.** The committed `[[400,-3],[150,-1.5],[30,-1]]` assumes a
500 m gate. PDI mode hands over near 150 m, so the breakpoints move into the
post-handover altitude band. **Values are set from M1's measured P66-entry
descent rate, not guessed** — same discipline as Wave 1's spike findings.

### M2 — Resume snapshots

A live spike retires two unknowns before any design is committed:

1. **Can a dump be taken at a chosen moment?** yaAGC writes `core` on its
   own `DumpInterval` schedule (`agc_simulator.c:224-238`); this is already
   happening, which is why `AgcSession` pins the child's cwd to
   `build/agc/`. Candidates: (i) the debugger's `coredump <file>` command
   (`agc_debugger.c:1315`) — unknown whether it coexists with the socket
   API; (ii) shorten `DumpInterval` and seal our own state the moment the
   file's mtime changes; (iii) a dump on graceful exit. **(ii) is the
   favourite** — it needs no extra control path, and at a 10 ms sim tick the
   phase error is bounded by one tick.
2. **Is restore reliable?** `agc_engine_init.c:68` carries the author's 2009
   note: "about half the time, using `--resume` causes the DSKY to become
   non-responsive… there are extra state variables in the `agc_t` structure
   which aren't being saved or restored". Extra variables were added, but
   nothing records the problem as fixed. **The spike restores 10 times
   consecutively and requires V16N36E to answer every time.** One failure
   sends the wave to its fallback.

**Where the snapshot is taken** is a scenario field, not a hardcoded
constant: an altitude threshold during P63, chosen so the restored run
covers late braking through touchdown in 3-5 min. The value is set from
M1's measured trajectory.

**Snapshot contents:**

```
Snapshot {
    agc_core:      <yaAGC core file bytes>,
    sim:           <SimCore state, serde>,
    taken_at_sim_t: f64,
}
```

`SimCore` gains `Serialize`/`Deserialize` (`LmState`, `Actuators`, sensor
state, ROD schedule progress, `ThrustResponder`). `ImuErrors` holds a
ChaCha RNG; it is reproduced from seed plus a consumed-draw count rather
than by serializing RNG internals.

**Restore verification:** the 100 telemetry ticks following a restore must
match the original run's same interval. Determinism is already pinned by
`telemetry_every_100ms_and_determinism`; this extends the same technique.

**Fallback (user-ruled):** if the spike fails, drop snapshots from this wave
and make the acceptance a single ~17-18 min full descent. M1 stands on its
own, so nothing is wasted.

### M3 — Landing radar

`eagle-sensors` gains `lr.rs`:

- **Altitude beam** — range from a body-fixed boresight to the spherical
  lunar surface. No terrain, so the intersection is analytic.
- **Three velocity beams** — surface-relative velocity projected onto three
  body-fixed beam directions.
- **Gating** — attitude limits, altitude range, antenna position (ch 033
  bit 6, already asserted by `runner`); data-good discretes on ch 033 bit 4
  (RR), bit 5 (LR range), bit 8 (LR velocity).
- **Quantization and the AGC read sequence** — R12 (`P20-P25.agc`) and
  `RADAR_LEADIN_ROUTINES.agc`'s `LRVELX/Y/Z`. Step-0 verification against
  the cited vendor lines is mandatory before tests lock in.
- **Error models** — LR noise and dropouts, seeded, default OFF, following
  the existing `ImuErrors` pattern.

Unit tests are built from M1's recorded telemetry: for each logged altitude
and velocity the expected beam values are recomputed offline.

When M3 lands, `lrbypass` flips to `false` for the acceptance scenario. The
flag stays in the schema permanently — it is a legitimate in-rope switch, so
radar-on versus radar-off becomes a supported A/B comparison rather than
scaffolding to delete.

## 4. Testing

| Layer | Content | AGC |
|---|---|---|
| Fast unit | `truth_state`/`generate_state` geometry agreement; LR beam analytic geometry; gating boundaries; quantization round-trip; snapshot serde round-trip | no |
| Determinism | 100 post-restore ticks match the original interval | no |
| Live spikes | ① PDI descent with LRBYPASS ② snapshot save/restore ×10 ③ descent with LR on | yes |
| Acceptance | from a snapshot: late P63 → touchdown, 3-5 min, LR ON, errors OFF (falls back to the full descent if M2's spike fails) | yes |
| Full descent | `make descent-full` (~17-18 min), manual, not in CI | yes |

Acceptance judgment reuses the observation-based machinery built in Wave 1's
review branch: `Touchdown::Nominal`, surface-relative v_vert / v_horiz /
tilt, observed alarm episodes empty, `prog_lamp_frames == 0`, and the
scale-free AGC clock-rate gate.

**Miss distance becomes meaningful here.** In Wave 1 the reported figure was
100 % freeze artifact (1585 m ≈ ω·R·cosφ × 343 s of pinned position). PDI
mode has no freeze, so after one measured run a threshold with real
provenance can be set — the step Wave 1 explicitly deferred.

## 5. Risks

| Risk | Response |
|---|---|
| `--resume` unstable (author's known issue) | Fall back to a single full-descent acceptance (user-ruled). M1 is independently valuable. |
| P63 guidance will not converge from a PDI truth state (IGNALG aborted 1406 in Wave 1's spike history) | M1 decides this first. If it fails, the wave is redesigned before any LR or snapshot work — which is why M1 is first. |
| LR read sequence trips 1201/1202 executive overflow | Precedent exists: Wave 1 resolved the same alarm by dropping THRUST DINC from 3200 to 800 pps. Throttle the R12 read rate. |
| Mass roughly doubles (≈15.1 t); inertia and RCS authority change | Inertia currently scales linearly with total mass. M1 measures the attitude loop's behaviour at PDI mass. |
| Long runs make diagnosis slow | This is precisely M2's purpose; if it works the loop drops to 3-5 min. |

## 6. Host facts (measured, carry into planning)

- yaAGC runs ≈95.2 % of real time on this host (drift −17.9 s over ~600 s,
  `mid_downlink_wps` 47.6). Budget wall-clock accordingly.
- `make descent-p66-fast` uses `tland_offset_cs = 30000`; 24000 was measured
  too tight and aborts with FAILREG 01703 (IGNITION TIME SLIPPED). 30000 is
  interpolated and **not yet flown**.
- One live acceptance run costs 7-11 min today because the TIG countdown is
  real time.
