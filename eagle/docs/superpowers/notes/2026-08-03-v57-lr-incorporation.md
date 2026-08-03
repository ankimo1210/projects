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

## 8. Prescribed next measurement

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
