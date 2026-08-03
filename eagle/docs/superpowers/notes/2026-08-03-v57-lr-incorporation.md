# V57 — the LR data was measured and never incorporated, 2026-08-03

**Verdict: the P65 low-altitude "navigation bias" is not a navigation bias.
It is the pure inertial drift of a state vector that no landing-radar
measurement ever entered, because the astronaut action that permits
incorporation — V57 — was never keyed.** The handoff's "unresolved boundary
between correctly presented LR observations and Luminary's state update" is
the flag `LRINH` (FLGWRD11 bit 8), clear since fresh start in every flight
this project has flown.

The entire investigation was done offline from Run 31's recorded artifacts
and the vendored rope. No flight was spent.

## 1. The rope's gate

- `EXTENDED_VERBS.agc:81` — `TC LRON  # VB57 PERMIT LANDING RADAR UPDATES`;
  `:443-446` — `LRON  TC UPFLAG / ADRES LRINH`. V58 (`LROFF`) is the
  inverse.
- `FLAGWORD_ASSIGNMENTS.agc:1074-1076` — LRINH set = "LANDING RADAR
  UPDATES PERMITTED BY ASTRONAUT", reset = "LR UPDATES INHIBITED BY
  ASTRONAUT". Fresh start leaves it reset.
- `SERVICER.agc:1174-1178` (`NOREASON`) — with LRINH clear the **altitude
  position update is skipped**: `CS FLGWRD11 / MASK LRINHBIT / CCS A /
  TCF VMEASCHK  # UPDATE INHIBITED`.
- `SERVICER.agc:1320-1323` (`VUPDAT`) — the **velocity update is gated by
  the same flag**.
- Order matters: `POSUPDAT` computes and STOREs `DELTAH` (downlink slot),
  runs the post-HIGATE reasonableness test, and only THEN hits the LRINH
  gate. So the AGC measures, evaluates, and discards. `HFAIL`/`VFAIL`
  raise no PROG alarm and touch no FAILREG — they set `HFLSHFLG`/
  `VFLSHFLG`, which only flash the DSKY ALT/VEL lamps
  (`SERVICER.agc:1432-1460`).
- The runtime never keys V57 and never touches LRINH: `grep -rn
  "V57\|LRPERMIT\|LRINH\|NOLRR"` over `runtime/`, `scenarios/`, and the
  channel map returned nothing before this fix.

## 2. What Run 31's own recordings show

Artifacts: `telem/pkt/lr-m1-run31-p65-autoscale.*` (§21 of the M1b ledger).
Clock mapping: ENGINE ON (telemetry `thrust_n > 0` at t_s = 342.61) ↔ first
ch 055 THRUST packet (t_ms = 2277), so t_s ≈ t_ms/1000 + 340.33.

**2a. The divergence is a smooth inertial drift that starts at the P64
pitchover, not at any LR event.** DSKY-parsed `agc_alt_m` (V16N63/N64
monitor, `parse_agc_nav`) against truth:

| t_s | MM | truth m | AGC m | err m |
|---:|---|---:|---:|---:|
| 820.0 | 63 | 4285.7 | 4309.6 | +23.8 |
| 837.0 | 64 | 3592.7 | 3581.7 | −11.0 |
| 858.3 | 64 | 2725.8 | 2666.7 | −59.1 |
| 894.4 | 64 | 1513.2 | 1418.5 | −94.6 |
| 941.2 | 64 | 566.1 | 426.1 | −139.9 |
| 996.5 | 64 | 248.7 | 40.8 | −207.8 |
| 1043.3 | 65 | 232.9 | −6.4 | −239.3 |
| 1120.0 | 65 | 217.7 | −75.6 | −293.2 |
| 1183.9 | 65 | 207.4 | −130.5 | −337.8 |

Slope over 858→1184 s: **−0.86 m/s**, essentially constant through the
MM64→MM65 transition, the 2500-ft boundary crossing (~t=928), the antenna
POS2 move (t=1129), and every RGOOD window — i.e. insensitive to every LR
variable, exactly as it must be if no LR measurement is being incorporated.
Onset at pitchover is consistent with the known item-3 delta-V deficit
(§9h) rotating into the vertical as the thrust vector verticalizes. It also
explains why Runs 29/30/31 — three presentation-side repairs — changed
nothing: they repaired data that was being thrown away.

**2b. The ALT/VEL lamps prove the whole chain was live up to the gate.**
Row-12 relay words (ch 010, `dsky.rs` mapping: bit4 = ALT, bit2 = VEL):

- ALT lamp ON exactly over the RGOOD-absent windows the ch33 timeline
  shows (lamp 669.1–687.1 vs RGOOD asserted 685.4; lamp 697.0–737.0 vs
  RGOOD dropout 697.4–735.3; lamp 887.0–889.1 vs the 886.5–887.0
  dropout) — Luminary's radar lamp logic tracking our responder in real
  time.
- VEL lamp **flashing at the HFLSHFLG/VFLSHFLG 0.5 s cadence** at
  1169–1171 and 1221–1223 (pre/post contact), ALT lamp flashing from
  1261 — the reasonableness machinery firing. No PROG lamp, no alarm
  episode: exactly the silent signature §1 predicts. (Lamp silence
  elsewhere is uninformative: `NORLITE` only lights the lamp when
  LRLCTR−LRRCTR ≥ 4, `SERVICER.agc:1432-1440`.)

**2c. Correction to §21: the "required masked low-scale transition" did
NOT happen in flight.** The ch33 register timeline (the trace's 'out' 033
rows) shows bit 9 changed exactly twice in the whole run: 0→1 at t=342.70
(the runner's raw `INIT_CH33` write, 2.4 s into the run) and 1→0 at
t=1548.45 — 335 s **after** ground contact, when the crashed geometry made
`standing_range` return None. There was no transition at the 2500-ft
crossing. The unit tests added with Run 30/31 passed because they encoded
the same inverted polarity as the code (see §3).

**2d. The presented-count side of the handoff's three-point measurement is
not recoverable from Run 31**: headless-mode traces log only AGC→runtime
packets (`headless.rs:180`), so RNRAD counter loads and our ch33 writes
appear only as yaAGC's echoed register states. It turned out not to be
needed. (Follow-up if ever needed: an opt-in 'in'-direction trace in
headless mode.)

## 3. The second defect: ch33 bit 9 polarity is inverted in the responder

With V57 fixed, the scale interface becomes load-bearing, and it was
backwards. The rope's semantics, from the listing:

- `ASSEMBLY_AND_OPERATION_INFORMATION.agc:873-874`: ch33 bits are
  active-low ("BIT 6 = NOT POSIT. 1").
- `SCALECHK` (`P20-P25.agc:2941-2948`) keeps RADMODES bit 9 EQUAL to ch33
  bit 9 by direct RXOR — same sense on both.
- `SCALADJ` (`P20-P25.agc:3002-3011`): `CCS L / TCF +2  # ON HIGH SCALE`
  — **bit 9 nonzero IS the high-scale branch**, which multiplies the
  counter ×5 into HMEAS's fixed 1.079 ft/bit units (`LRHJOB` stores "LRH
  DATA 1.079 FT/BIT", `SERVICER.agc:1550`; `HSCAL` = 1.079 ft,
  `CONTROLLED_CONSTANTS.agc:168`).
- So: **bit 9 = 1 ⇒ high scale (5.395 ft/ct effective); bit 9 = 0 ⇒ the
  LOW SCALE discrete is present ⇒ 1.079 ft/ct.** The claim recorded in
  §19/§20 ("bit 9 set — LR RANGE LOW SCALE") and in
  `lr.rs`'s old comment ("this is not inverted") had it backwards.

The responder (`sim.rs` `phase6b_landing_radar`) drove bit 9 = 1 for low /
0 for high. Two accidents masked this: `INIT_CH33` (bit 9 = 1, correct
high) clobbered the responder's boot-time write, making the braking-phase
presentation rope-consistent by luck; and with LRINH clear nothing
downstream could notice. Un-fixed, the first V57 flight would have had
every altitude update below 2500 ft silently HFAILed: counts quantized at
1.079 ft/ct, converted by the rope ×5.395 ft/ct ⇒ ranges 5× actual ⇒
|DELTAH| far beyond the 50 ft + H/8 reasonableness bound
(`SERVICER.agc:1163-1171`) — a hover-high crash with a different cause and
the same symptom.

## 4. Changes made

1. `runner.rs run_scenario`: keys **V57E** — placement corrected by
   measurement, see §7: it must come AFTER P63 is selected, because **R00
   wipes the whole R12 flagword on every V37 program change**
   (`FRESH_START_AND_RESTART.agc:844-846`, `CAF LRBYBIT / TS FLGWRD11` —
   "CLEAN UP THE R12 FLAGWORD"). The final placement is right after
   ENGINE ON, followed by a FLGWRD11 read-back `ensure!` and a `V16N63E`
   to restore the burn monitor the read terminates. Gated on
   `!sc.agc.lrbypass`; the frozen radar-bypass acceptance choreography is
   byte-identical. Keyed as the verb (not `set_flag_bits`) because R12
   read-modify-writes other FLGWRD11 bits live; LRON runs under the
   rope's own interlocks.
2. `sim.rs`: scale-branch polarity swapped (low ⇒ drive bit 9 LOW);
   `LrState::range_low_scale_presented` doc rewritten.
3. `lr.rs`: the inverted comments corrected
   (`CH33_LR_RANGE_LOW_SCALE`, the quantum constants block).
4. `runner.rs` ALTSCBIT doc: "matching cleared channel bit" corrected to
   SET; new `LRINHBIT` constant with citations; const test extended.
5. Tests first: the two ch33-scale unit tests were flipped to the rope's
   polarity and failed against the old code (2 failed), then passed after
   the swap. Full gates after: `cargo test` workspace 194 passed /
   0 failed (131 runtime lib + 32 + 21 + 5 + 5 others), client vitest 24
   passed, `make lint` (clippy `-D warnings`, fmt, oxlint) clean.

## 5. What this does NOT claim

No landing. No thresholds touched, no scenario values changed, the frozen
M1 acceptance untouched. The next flight measures whether incorporation
now closes the −0.86 m/s drift; the item-3 inertial deficit is still there
underneath, and P66's scalar/vertical limitation (§17) is unchanged. If
the drift persists WITH incorporation confirmed (N68/DELTAH moving the
state), item 3 returns to the top of the list.

## 6. Next actions — superseded by §7's measured results; see §8

(Original plan retained for the record: one instrumented `descent-p65`
flight measuring `nav_err_alt_m`, the 2500-ft bit-9 flip, lamps, and the
SCALCHNG discard.)

## 7. Runs 32 and 33 — V57 measured: placement wrong, then incorporation live and RED

**Run 32** (V57E keyed in P00, verified set;
`telem-m1-run32-p65-v57.jsonl`): Crash 25.85 / 1.76 m/s at 865.9 s —
**byte-for-byte Run 31's profile**, same −0.86 m/s drift (MM64 +5.0 m →
t=1191 −342.4 m), same late POS2 command (ch12 bit13 at t=1129.27 vs
Run 31's 1129.25). Diagnosis: **R00 wipes FLGWRD11 to LRBYPASS-only on
every V37** (`FRESH_START_AND_RESTART.agc:844-846`), so V37E63E erased
the P00-keyed LRINH. This is why Apollo 11's crew keyed V57 inside P63
(~102:38 GET). P63's own FLAGORGY (`THE_LUNAR_LANDING.agc:71-78`) then
clears LRBYPASS — the wipe-then-enable sequence is authentic.

Run 32 also pinned the reposition machinery: `HIGATCHK`
(`SERVICER.agc:760-776`) triggers `HIGATASK` on a TTF-vs-`RPCRTIME`
criterion plus the `RPCRTQSW` attitude test — **PSTHIBIT (reasonableness
enable) and the NOLRREAD update-inhibit are set there, not at P64
entry** — and `HIGATJOB` clears NOLRREAD when the POS2 discrete arrives
(`SERVICER.agc:1632-1645`), a ~10 s authentic inhibit window. With the
drifted state, TTF satisfied the criterion only at t≈1123; the ch12
bit13 command followed at 1129.

**Run 33** (V57E keyed after ENGINE ON, verified set;
`telem-m1-run33-p65-v57ign.jsonl`): **incorporation went live and the
descent got radically worse** — MM `["00","63","64"]`, violent attitude
excursion at P64 entry (tilt 24.9° at t=840 → 139.9° at 850), full-power
dive, Crash at t=880.2, 126.95 / 215.71 m/s, 109.2° tilt, TIG+537.6 s.
Measured boundaries:

- Truth trajectory matches Run 32 closely until ~838 (LR lock at ~685,
  ALT reads ~0.8 Hz, only ALT — first velocity selects at t=1019, after
  contact).
- The downlink navigation **velocity** state stayed healthy to at least
  t=864: VGU rows match Run 31's to a few m/s (e.g. 123.9 vs 121.6 m/s
  at t≈857). The +419 m/s "hdot" both runs show at t≈690 is the
  guidance-frame convention (VGU_X is radial-at-SITE; at 16° central
  angle that projects ~460 m/s of horizontal velocity), not an error.
- The **position/altitude state is not observable in Run 33**: the
  V01N01 read-back at ENGINE ON+0.3 s TERMINATED the N63 burn monitor (a
  V16 monitor dies on the next verb) and nothing restarted it —
  telemetry `agc_alt_m` froze at 15207.7 m from t≈343 for the whole
  flight. Harness defect, now fixed (`V16N63E` re-keyed after the
  read-back).
- Working hypothesis, NOT yet measured: with LRINH finally set, the
  pre-PSTHIBIT braking/P64 phase incorporates raw DELTAH (no
  reasonableness until the reposition criterion), and the incorporated
  altitude measurement is wrong enough at P64 geometry to bend guidance
  into the ground. The measurement that decides it is the AGC's own
  DELTAH/RGU — not yet decodable (offsets unresolved; see §8).

**Score-keeping per the three-attempt rule: Runs 32 and 33 are two
flights on this defect chain. No further flight until the DELTAH/RGU
instrument exists.**

## 8. Prescribed next measurement — DONE, see §9-11

(Plan as written: pin DELTAH/RGU, add range rows, then judge where the
incorporated altitude goes wrong. What follows is what it measured.)

1. Pin `DELTAH` (control-list slot 21 by hand count, LAND−49±2 after the
   known +2 slot shift) and ideally `RGU` in the LAND-anchored decoder,
   validated the way `downlink_dump` pinned TIME2/VGU/VN — against
   Run 33, where DELTAH must be nonzero from LR lock (~685 s) and its
   incorporation visible in the state. Extend `downlink_dump` rather
   than the Python spike.
2. Only then judge WHERE the incorporated altitude goes wrong:
   presented count vs slant (add range-read rows to `EAGLE_LR_DEBUG` —
   today it logs only velocity transactions), rope conversion
   (SCALADJ ×5, HSCAL), or projection (`HBEAMNB`·UNIT/R vs the
   responder's POS1/POS2 beam geometry — compare pad `LRALPHA/LRBETA1/
   LRALPHA2/LRBETA2` against `LR_ANTENNA_POS1_DEG/POS2_DEG` conventions).
3. The V57 keying and the ch33 polarity fix stay: both are rope-proven
   prerequisites. Run 33's regression is the next defect layer becoming
   visible, not a reason to re-inhibit the radar.

## 9. The instrument that was built instead of the downlink decoder

**The downlink cannot reach DELTAH or RGU, and the note's plan above was
wrong about why.** A brute-force scan over every offset in LAND−60..+10 at
b=23/24/25 finds no word matching the AGC's own painted altitude better
than ~300 m median — and the premise was broken anyway: `RGU = CG (R −
LAND)` (`LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:430`) is **site-relative**,
so the "|RGU| ≈ lunar radius" test used to search for it could never
succeed. This matches `downlink_dump`'s own recorded failure to resolve
RGU.

The repo already documents the right instrument and this investigation
ignored it for a second time: `coredump.rs` — "the instrument of first
resort for any question about what the AGC believes". Built:

- `EAGLE_CORE_SAMPLE=<abs path>` samples yaAGC's periodic core dump into a
  CSV time series of R12's working set — `HMEAS`, `HCALC`, `DELTAH`,
  `RGU`, `VGU`, `RNRAD`, `FLGWRD11`, `RADMODES`, channel 33, the
  `LRLCTR/LRRCTR/LRSCTR/LRMCTR` reasonableness counters and `FAILREG` —
  every field by symbol. Symbols resolve before the flight starts, so a
  bad name costs a second rather than 20 minutes. `TIME2` and `RNRAD` are
  hardware counters with no listing address and come from pinned
  constants cross-checked against `runner`/`sim`.
  It does NOT shorten `EAGLE_DUMP_TIME`, so the flight-12 boot hazard is
  not incurred; the default 10 s interval yields ~100 samples per descent.
- `EAGLE_LR_DEBUG` gained `ALT` rows (true slant, measured slant, scale
  branch, quantum, counts). It had only ever logged velocity
  transactions — the presented-count side of an altitude investigation
  was simply not being recorded.
- `agc_state --sample-row` prints the same row for one dump, so the
  columns can be checked without a flight.

One defect found by using it: the sampler's first row came from the
PREVIOUS flight's dump file (`--no-resume` stops the AGC reading it, not
yaAGC writing it). Run 34's first row is Run 33's crashed state. Fixed —
dumps older than sampler start are ignored — and confirmed in Run 35,
whose first row is t=30 s.

## 10. Runs 34 and 35 — a Nominal landing that does NOT reproduce

**Run 34 (`00→63→64→65`) landed: Nominal, 1.14 m/s vertical, 0.50 m/s
horizontal, 0.9° tilt, 687.2 s after ENGINE ON, 640 kg of DPS fuel
remaining, no alarm episode, no PROG-lamp frame.** P64 flew it to 21 m at
0.94 m/s and P65 took over at TIG+661 s. It is the first authentic soft
touchdown this project has measured. It missed the target site by
5,256.7 m.

**Run 35, same binary and same scenario, crashed: 137.76 / 105.47 m/s at
136.7° of tilt, `00→63→64`, 537.1 s.** Run 33 failed the same way. The
outcome is bimodal, so **nothing in this project's status may be
upgraded to "lands" on Run 34** — one landing in three flights of the
same configuration is a coin toss, not a capability.

The instruments explain the split, and it is not the LR incorporation
itself. Through braking both runs are healthy: `DELTAH` stays inside
±50 m, `HCALC` tracks truth to ~25 m at 600 m altitude (Run 31's
equivalent error was −222 m), and the channel-33 HIGH→LOW transition
fires in flight at the 762 m slant crossing, exactly as the rope's
SCALADJ expects. Run 34's HMEAS/presented-count ratio holds at 0.96-0.98
for the whole descent.

## 11. ROOT CAUSE of the crashes: a grazing beam reported as good

Run 35's core samples show the state break at one instant: at TIG+507 s
`HMEAS` jumps to **21 556 m** with the vehicle at 2 989 m, `DELTAH` to
**12 117 m**, and `HCALC` never recovers (2 001 m at truth 1 234 m,
1 117 m at truth −64 m). The new `ALT` rows say where that came from —
the responder's own geometry:

| t_s | true slant | counts | truth alt | tilt |
|---:|---:|---:|---:|---:|
| 838.5 | 3 465.9 | 2 107 | 3 427.0 | 28.0° |
| 846.5 | **10 497.5** | 6 383 | 3 158.4 | **86.3°** |
| 856.5 | 5 962.7 | 3 626 | 2 551.7 | 81.8° |
| 872.5 | **17 957.2** | 10 920 | 913.4 | **78.7°** |

At P64 entry the attitude loop wobbles (Run 35: 67.8° → 38.6° → 28.0° →
50.9° → 86.3° in 16 s; Run 34 over the same seconds: 64° → 51° → 50°,
smooth). Once tilt passes ~60° the H beam grazes the surface and the
spherical intersection returns a legitimately huge slant range — which
the responder presents as DATA GOOD. **Before HIGATE the rope runs no
reasonableness test** (`SERVICER.agc:1157-1161`, PSTHIBIT), so it
incorporates the reading raw, the altitude state jumps, guidance
commands a worse attitude, the beam grazes further: a runaway. Run 34
never wobbled far enough to enter it.

So the bimodality is a marginal P64 attitude loop **coupled through an
unphysical radar**: the sim reports altitude data good at attitudes where
no real landing radar could lock.

Fixed now (unit-gated, NOT flown): the read path applies the same 40,000 ft
operating ceiling (`alt_in_counter_range`) the standing DATA GOOD discrete
already applied. The two disagreed — the load path only rejected counts
overflowing 14 bits, i.e. 26.9 km at the high scale — and Run 35 flew
straight through the gap. That kills the 17 957 m reading. **It does NOT
kill the 10 497 m one**, which is inside the ceiling: a beam-pointing
envelope is still missing, and picking its limit needs a source, not a
guess. That is the open decision.

## 12a. The P64 instability, narrowed — RCS authority is EXONERATED by the rope

The rope publishes its own model of the vehicle's rotational authority, and
this project had never compared against it. `AOSTASK_AND_AOSJOB.agc:425-455`:

```
# 1JACC = A/(MASS + C) + B
# A IS SCALED AT PI/4 RAD/SEC**2 B+16KG, B AT PI/4 RAD/SEC**2, C AT B+16 KG
INERCONA  2DEC +.0059347674   # 1JACCP A  DESCENT   (roll)
          2DEC +.0014979264   # 1JACCQ A  DESCENT   (pitch)
          2DEC +.0010451889   # 1JACCR A  DESCENT   (yaw)
INERCONB  DEC  +.002989 / .018791 / .021345      # P / Q / R  B
INERCONC  DEC  +.008721 / -.068163 / -.066027    # P / Q / R  C
```

Evaluated at the flown PDI mass (15 209 kg) this gives **one-jet angular
accelerations of 1.244° / 1.257° / 1.244°/s²** in roll / pitch / yaw. Our
plant delivers `RCS_THRUST_N × RCS_LEVER_M/√2 / I` = 529 N·m / 25 000 kg·m²
= **1.212°/s²** in pitch (and 1.32° in roll at I=23 000). **The plant and
the DAP's own model agree to 4-6 %** — so RCS authority, `RCS_THRUST_N`,
`RCS_LEVER_M` and the scenario's assumed inertia are NOT the instability,
and the hypothesis that they were is dead.

What survives is the other torque source, and the arithmetic is stark:

| source | torque | α at I = 25 000 |
|---|---:|---:|
| one RCS jet | 529 N·m | 1.21°/s² |
| trim gimbal, 1°, at Run 34's ~25 kN | 742 N·m | 1.70°/s² |
| trim gimbal, 1°, at full 48.1 kN | 1 428 N·m | 3.27°/s² |
| trim gimbal, 6° stop, at full thrust | 8 555 N·m | 19.6°/s² |

**One degree of trim at full throttle outweighs 2.7 RCS jets; the stop
outweighs sixteen.** And Run 35's throttle went to FULL at MM64 (t=833,
48 145 N) and stayed there for the rest of the flight, while Run 34's
modulated between 17 and 27 kN — the trim-gimbal torque gain in the
crashed run was roughly double the landed one, in the exact seconds the
attitude diverged (Run 35 tilt: 69.4° → 27.8° at −13°/s, then +10, +19,
+30, +42°/s into a tumble; Run 34 over the same interval: 68.9° → 49.3°,
caught and held).

There is a modelling defect behind this, not yet confirmed in flight:
**our plant has no CG offset.** `forces` puts the thrust through
`ENGINE_MOUNT_M` (−1.7 m, provenance "assumed") with the trim deflection
applied to its direction, so zero trim gives zero torque. On the real
vehicle the trim gimbal exists to point thrust THROUGH a CG that migrates
as propellant burns — the trim angle CANCELS an offset torque. Here it can
only CREATE one. If that is what happens, every degree the AGC trims is a
pure disturbance whose gain rises with throttle, which is exactly the
observed signature.

`EAGLE_ATT_DEBUG` could not settle this: it logged only the RCS jet torque.
It now also records the trim angles, the thrust, and the DPS gimbal torque
(`forces::dps_torque`), so one instrumented flight separates the two
authorities directly instead of by inference.

## 12b. MEASURED (Run 36): the trim gimbal runs to its rate limit, and its arm was invented

Run 36 flew with the extended attitude trace. It crashed like 33 and 35 —
101.42 / 198.35 m/s, 88.9° tilt, `00→63→64`, TIG+547.0 s — and the trace
names the mechanism. From TIG+493 s (MM64 at 833.4):

| t_s | trim pitch | trim roll | thrust | \|RCS τ\| | \|DPS τ\| | ω_y |
|---:|---:|---:|---:|---:|---:|---:|
| 835 | 0.266° | −0.082° | 25 934 | 2 114 | 205 | −0.07 |
| 840 | 1.246° | −0.068° | 26 091 | 1 057 | 964 | −0.98 |
| 845 | 2.246° | −0.070° | 26 167 | 2 114 | 1 743 | −1.25 |
| 855 | 0.298° | −2.044° | 26 192 | 2 114 | 1 588 | +0.32 |
| 865 | −1.702° | −3.914° | 26 192 | 2 114 | 3 038 | +2.15 |

**The trim ramps monotonically at exactly 0.2°/s — the actuator's rate
limit — for eleven seconds at a time, reverses, and ramps again.** It is
saturated, not regulating. Its torque passes the RCS jets' at t≈858 and
reaches 1.4× by t=865, while ω grows monotonically in the sign the trim
sets. Full throttle is NOT required: Run 36 crashed at 26 kN, where
Run 35 had pegged at 48 kN.

Over the whole post-freeze trace (5 490 samples): the trim sits at its
0.2°/s rate limit in **57 %** of samples, reaches **4.33°** (the stop is
6°), and its torque peaks at **3 363 N·m — 3.18× the RCS torque** in the
same sample. Final |ω| is 5.58 rad/s, a flat tumble.

**The arm that sets that torque was invented, and the rope publishes the
real one.** `ENGINE_MOUNT_M = -1.7 m` carried the provenance "assumed".
The same table that gives `1JACC` gives the pivot-to-CG distance:

```
2DEC +.0410511917   # L  A  DESCENT      A at 8 FT B+16 KG
DEC  +.155044       # L  B  DESCENT      B at 8 FT
DEC  -.025233       # L  C  DESCENT      C at B+16 KG
```

`L = A/(MASS + C) + B` gives **0.862 m at the flown PDI mass**, growing to
1.08 m at 11 000 kg as the CG walks toward the pivot. The assumed value was
**1.97× too long at PDI and 1.57× at landing mass** — so the trim gimbal
carried roughly double the torque it should, in the one authority that
already outweighs the RCS.

Corrected (test first): `forces::pvt_cg_arm_m(mass_kg)` implements the
rope's curve fit, recomputed independently in its test from the listing's
decimals; `dps_torque` takes mass and uses it; `ENGINE_MOUNT_M` is
deprecated and unused. At 26 kN one degree of trim now makes 394 N·m
against a jet's 529 N·m — the DAP can win — where before it made 777 N·m.
This is the fifth vehicle constant this project has replaced with the flown
rope's own number, after `PIPA_INCR`, `THRUST_N_PER_PULSE`, DPS full
throttle and `DPS_TAU`.

## 12c. Run 37 — the arm correction is NOT curative, and the runaway axis is one the gimbal cannot touch

Run 37 flew the corrected arm and was **worse**: it never reached P64.
`00→63`, Crash 180.19 / 427.87 m/s at 96.1° tilt, TIG+458.2 s, 23.7 km
miss. Trim saturation went UP (67 % of samples at the rate limit, and it
reached the 6° stop).

The trace says why the arm was never the whole story: **the runaway is
about body X — the thrust axis — and `dps_torque` has identically zero X
component**, because the pivot lies on that axis (`mount × f` with
`mount ∥ x̂`). Whatever the gimbal arm is, it cannot torque or damp this
axis. Only the ch006 jets can.

The decisive fifteen seconds (`att-m1-run37-p65-arm.txt`):

| t_s | jet word | RCS τ_x | DPS τ_x | ω_x |
|---:|---:|---:|---:|---:|
| 750 | 21925 | +2 990 | 0.0 | +0.06 |
| 755 | 21793 | +2 990 | 0.0 | +1.13 |
| 760 | 21865 | +2 990 | 0.0 | +2.23 |
| 765 | 21925 | +2 990 | 0.0 | **+3.31** |

**The AGC held a fixed four-jet mask for fifteen consecutive seconds,
producing a constant +2 990 N·m, while the rate it should have been
nulling grew from 0.06 to 3.31 rad/s in the same direction.** Over the
whole divergence the yaw torque reinforces ω_x as often as it opposes it
(252 / 252) — the loop carries no net damping at all. A correctly-signed
attitude loop cannot do that; a sign-inverted feedback path does exactly
this. The 2026-07 sign work pinned the ch005 couples ("couples torqued Z
where the DAP expected Y"); **the body-X chain — ch006 `ROLLJETS`, and
the CDU/gimbal angle that feeds it back — was never verified the same
way**, and it is now the prime suspect.

The arm correction is kept, on the same principle as the four vehicle
constants before it: its provenance is the flown rope where the value it
replaced was invented. It is **not** credited with curing anything, and
it is not exonerated either — one flight cannot separate it from the
body-X defect that dominates. Do not tune it further until the sign chain
is settled.

**Score-keeping: six flights this session (32-37).** Runs 33, 35, 36 and
37 all crashed; Run 34 landed. Stop changing the vehicle model here.

## 12. Open, in order

1. **The LR needs a beam-validity envelope with a citation.** A real LR
   does not report altitude data good with the vehicle 86° off vertical.
   Candidate rule: require the beam's surface incidence within the
   radar's design cone, sourced from the LR spec or NASSP's
   implementation, rather than a number chosen to make a flight work.
2. **The attitude loop is the primary instability**, independent of the
   radar, and §12c localizes it: the divergence is about **body X**, the
   thrust axis, which the DPS gimbal cannot torque at all. The AGC holds a
   fixed four-jet mask for fifteen seconds while the rate it should null
   grows to 3.31 rad/s, and over the whole event the yaw torque reinforces
   the rotation as often as it opposes it. **Verify the body-X sign chain
   — ch006 `ROLLJETS` geometry and the CDU/gimbal angle feeding it back —
   the way the ch005 couples were verified in 2026-07.** That is a
   bench/unit question first: drive a known rate, check the commanded jets
   oppose it. No more vehicle-constant tuning until it is settled.
3. Only then re-fly, and judge reproducibility over several flights, not
   one. Run 34 is evidence the chain CAN land, not that it does.
4. Unaffected and still RED: the frozen M1 acceptance
   (`live_pdi_descent`) bypasses the radar entirely and never keys V57.
