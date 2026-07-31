# Road to Landing — Wave 2 completion plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **This is a decision-gated roadmap**: Tasks 1–2 are fully specified; later tasks depend on what the gates measure, and each gate states its decision rule *before* the measurement is seen.

**Goal:** `tests/live_pdi_descent.rs` — frozen since 2026-07-26 and never
green — measures a soft landing, and Wave 2 closes with the M2/M3
reassessment the spec still owes.

**Architecture:** Diagnose-then-fly, in the order the evidence points:
(1) name the MM64 nav-error mechanism from data already on disk, (2) fix
the seam (or document authentic-AGC behavior and route around it),
(3) answer the crewless-P66 horizontal-velocity question — the one
*design decision* in the way of a soft landing, (4) fly the acceptance,
(5) reassess M2/M3 per the Wave 2 spec. The landing radar (M3) is kept as
the historically-faithful fallback: the real LM landed on radar-corrected
navigation, and if inertial-only cannot be made clean, radar is the
correct fix rather than a workaround.

**Tech Stack:** Rust workspace (`runtime/`), the vendored Luminary099 as
citation authority, downlink forensics per
`scripts/downlink_nav_split.py`, `make test` / `make lint` gates,
~20 min live flights via `make descent-full`.

## Global Constraints

- `vendor/` is READ-ONLY; every scale/claim carries a `path:line` citation
  or a measured-artefact reference.
- **Do not relax `live_pdi_descent.rs` thresholds** (`Nominal`: v_vert
  < 3.0, v_horiz < 1.5, tilt < 12°; the acceptance gates on the scenario's
  `[acceptance]` block). A window/semantics fix with the threshold intact
  (as in `prog_lamp_frames`) requires the ledger-recorded justification
  pattern.
- Do not describe M1 as landing until the acceptance test measured it.
- Flights are expensive (~20 min): every flight needs a written purpose
  and a decision rule fixed before launch. Offline forensics first, always.
- Instrumented flights use ABSOLUTE `EAGLE_TELEM_OUT` paths;
  `make descent-full` records the packet trace unconditionally.
- `make test` and `make lint` green before every commit.
- Each task ends with its ledger entry
  (`docs/superpowers/notes/2026-07-31-m1b-rod-loop.md` §10 successor or a
  new dated note). Honest outcomes: a crash is written as a crash.

## Where this plan starts (measured state, 2026-07-31)

- Open item 1 (P66 rate loop) **closed**: `TAUROD` measured b=11,
  corrected; flight 9 flew the first controlled P66 descent (246 → 40 m,
  command never saturated).
- Open item 3 is the blocker: a **~3.5 m/s velocity error (−3.2 m/s
  downrange, −1.3 m/s radial) switches on at MM64**, integrates to
  −190 m altitude / −0.7 km downrange by P66 entry, and drives the AGC's
  nav divergent once the truth is near the ground. P63 nav is healthy
  (~1e-4 of distance flown).
- Prime suspect: the LR seam — MM64 is where the rope repositions the
  antenna and would start radar processing; `lrbypass` (FLAGWRD11 bit15)
  is verify-only in the scenario.
- Open items 1a (braking-gate residual), 2 (P65 alarm code — moot while
  the handover fires inside P64), 4 (crewless-P66 v_horiz) remain.
- `LAG/TAU`, `MINFORCE`, `MAXFORCE` remain `Unverified` in
  `P66_BSCALE_TABLE`; a proven frozen-plant step-test technique now
  exists to pin them cheaply.

---

## Task 1: Rust downlink decoder — name the MM64 mechanism

Zero flights. The decisive datum — does the AGC's `VN` **step** at one
PIPTIME near MM64 or **ramp** across the pitchover — is already in
`build/traces/pkt-descent-full.jsonl`.

**Files:**
- Create: `runtime/apps/eagle-runtime/src/bin/downlink_dump.rs`
- Modify: `scripts/downlink_nav_split.py` (point its header at the new tool)

**Interfaces:**
- Consumes: the pair stream (ch 034 hi / ch 035 lo), slot map and scalings
  already verified and recorded in `scripts/downlink_nav_split.py`'s
  docstring (LMDSASDL, 100 pairs/frame; RGU 66-68 b24, VGU 69-71 b10,
  LAND 72-74 b24, RN b27 / VN b7 / PIPTIME b28 snapshot at 51-57).
- Produces: a JSONL of per-frame decoded state
  `{t_ms, piptime_cs, rn: [f64;3], vn: [f64;3], rgu, vgu, land}` for
  downstream analysis.

**Design constraints learned the hard way (from the Python spike):**
- The pair stream has drops; index-from-ID extraction slips. Anchor each
  frame on physical signatures — `LAND` decodes to |v| = R_SITE ± 40 m at
  b=24 with the pole component rotation-invariant — and *validate every
  extracted frame* (|RN| within the mission envelope, |VN| < 2000 m/s,
  PIPTIME monotone). Emit only validated frames; report the drop count.
- One's-complement decode: `i15(w) = w if w < 0o40000 else −(w ^ 0o77777)`;
  DP = hi·2¹⁴ + lo (unlike signs legal).
- Tests: synthetic frame round-trip; a slipped-stream fixture that must be
  *rejected*, not mis-decoded — the Python spike's failure mode.

**Steps:**
- [ ] Failing tests: round-trip + slip-rejection fixtures
- [ ] Implement; run on run 9's trace; `make test && make lint`; commit
- [ ] **Analysis:** plot/tabulate `VN`(PIPTIME) across t = 800–900 s.
      Also re-derive the dD anchor sign rigorously (site-rotation
      correction ±3.2 km — flagged caveat in ledger §9b) from the decoded
      `LAND`(t) itself, which rotates in ref coords and therefore *is* the
      site-angle history.

**GATE 1 — decision rule, fixed now:**

| VN behaviour at MM64 | conclusion | next |
|---|---|---|
| step ≥ 2 m/s at one PIPTIME | discrete state update — LR seam or another incorporation event | Task 2A |
| ramp over the ~30 s pitchover | sensing seam during the maneuver | Task 2B |
| neither (error not in VN) | RGU/VGU-only error → guidance-frame (CG) seam, not navigation | Task 2C |

---

## Task 2: Close the MM64 seam (one of three shapes)

**2A — discrete update.** Find the writer: what incorporates a state
update at P64 entry with the radar bypassed? Candidates in-rope:
`UPDATCHK`/`VMEASCHK` (`SERVICER.agc:884+`) gated by FLGWRD11; the LR
position-2 repositioning handshake; `DELTAH` processing. Verify which
flags/discretes the sim presents at MM64 (ch 033 bits 4/5/8 data-good,
antenna-position bit 6) against what the rope requires before
incorporating. The fix will be on the sim side (present the discretes of
a radar that is *absent*, not one that is *lying*) — vendor stays
read-only. Add a regression test that replays the decoded frames and
asserts no VN step without a data-good discrete.

**2B — maneuver-window sensing seam.** The suspects, in evidence order:
PIPA emission timing vs CDU during high pitch rate (`sim.rs`
`phase6_sensors` projects the whole tick's ΔV through the end-of-tick
attitude), trim-gimbal thrust-direction lag, RCS-plume/impingement terms
present in truth but absent from PIPA feed (or vice versa). Reproduce
offline first: an AGC-twin reintegration of the decoded PIPA stream
against truth. Fix in the sim; the existing
`telemetry_every_100ms_and_determinism` pattern pins the regression.

**2C — CG-frame seam.** RGU/VGU are guidance-frame; if RN/VN are clean,
the error is in how `CGCALC` erects CG from `LAND` vs how the analysis
(and the guidance targets) assume it — re-audit against
`LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:671-691` and fix the *pad targets*
or the analysis, not the sim dynamics.

**Exit:** offline evidence that the mechanism is closed (replayed frames
show no onset), ledger entry, then **flight 10** with the standard
instrumentation. GATE 2: `|dH| < 30 m and |dD| < 300 m at P66 entry`
measured by the decoder → proceed. Larger → back to Task 1's data with
the new trace; do not fly again on hope.

---

## Task 3: The crewless-P66 design decision (open item 4)

With nav clean, the remaining structural gap: P66 holds attitude and
nobody flies the RHC, so residual tilt at handover pushes v_horiz
(~0.35 m/s² at 12°) toward the 1.5 m/s `Nominal` limit while the ROD
schedule manages only the vertical channel.

Flight 9 measured the post-TAUROD-fix behavior only down to the nav
blow-up; **flight 10 (Task 2's exit flight) measures the real v_horiz
budget** — possibly the existing handover attitude is already good
enough, since P64's final tilt was ~12° largely *because* guidance was
chasing a nav error.

**GATE 3, on flight 10's numbers:**
- v_horiz at touchdown < 1.5 m/s → nothing to build; item 4 closes as
  "P64 leaves a small enough tilt when nav is clean."
- Otherwise → **AskUserQuestion**: (a) model a minimal crew — an
  attitude-nulling RHC input at handover (historically faithful: the
  crew leveled the vehicle in P66); (b) fire the handover later/lower
  with a steeper ROD schedule; (c) accept `Hard` (v_horiz < 3.0) as the
  acceptance class and record why. This is a product decision about what
  the sim claims to be, not an engineering call.

---

## Task 4: The acceptance, for real

- [ ] `cargo test -p eagle-runtime --test live_pdi_descent -- --ignored
      --test-threads=1` (port 19905, ~20 min) — **the first run ever** of
      the frozen test.
- [ ] If RED: the failing block tells which task above leaked; fix there,
      never here. The known-false-negative note (post-contact lamp
      frames) is already fixed; thresholds stay.
- [ ] If GREEN: update `CLAUDE.md` / `README.md` — the sentence "M1 lands"
      must name this test as the thing that measured it. Wave 1's
      `live_p66_descent` acceptance stays RED-documented unless re-run.
- [ ] Ledger: flight table row, `[accept]` block verbatim, and close
      items 3 (and 4 if Gate 3 closed it) in the M1 ledger's Open list.

---

## Task 5: Sweep the debt while the technique is hot

Cheap, each independently committable, none blocking the acceptance:

- [ ] **Pin `LAG/TAU`, `MINFORCE`, `MAXFORCE`** with frozen-plant step
      tests (the Task-7c technique): MINFORCE/MAXFORCE bound the command
      at known mass — drive the rate error past each bound and read the
      clamp; LAG/TAU shapes the transient — two steps of different size
      separate it. Flip the last `Unverified` entries in
      `P66_BSCALE_TABLE`; `check_bscales(false)` then passes and
      `--allow-unverified` retires.
- [ ] **Item 1a (braking-gate residual, 911 m / 47 m/s):** re-measure on
      the post-fix trace with the decoder (dD anchor now rigorous). If it
      persists with clean nav, it is a *targeting* residual —
      `p66-padload.toml` RBRFG/VBRFG vs `TENDBRAK` switch criterion — and
      gets its own note; it does not block a landing (P64 absorbs it).
- [ ] **Item 2 (P65 alarm code):** one instrumented flight with a
      post-ignition V05N09 alarm reader *only if* P65 is ever re-entered
      by design; otherwise close as "route stays P64 → P66, alarm
      documented unread."
- [ ] `probe.py:42,61` unconditional-chmod cleanup (health-project
      pattern, noted 2026-07-25).

---

## Task 6: Wave 2 close-out — the M2/M3 reassessment the spec owes

The spec (`2026-07-26-eagle-wave2-real-descent-design.md:144-147`) paused
the wave pending reassessment "not made by this note." Make it, as a
short decision document:

- **M3 (landing radar)** — reassess FIRST, not M2. Evidence shifted its
  value: the real LM never landed inertial-only, ΔH at LR acquisition was
  expected and handled (`DELTAH` is on the downlist we now decode), and
  Task 2 will have shown exactly what the radar seam looks like. If
  Task 2A found the bypass seam, M3 is *also* the principled fix: a
  radar that exists and agrees with truth beats discretes that say
  "absent". Spec section §M3 stands: `lr.rs` beams are analytic against
  the sphere; unit tests from recorded telemetry; `lrbypass=false` flips
  in the acceptance when it lands; radar-on vs radar-off becomes a
  supported A/B.
- **M2 (resume snapshots)** — value dropped: the debug loop it shortens
  is no longer the bottleneck (offline forensics replaced re-flying).
  Recommend: defer unless M3's development needs the 3–5 min loop; the
  yaAGC `--resume` spike (10 consecutive restores, V16N36E each time)
  remains the go/no-go if revived.
- **AskUserQuestion** with the recommendation; the wave's end state is
  the user's call.

**Definition of "the end" for this plan:** `live_pdi_descent.rs` GREEN on
an unmodified-threshold run, all M1-ledger Open items closed or
explicitly dispositioned, the M2/M3 reassessment decided and recorded,
and `main` pushed.

---

## Self-Review

**Coverage vs the outstanding record:** M1 ledger Open items — 1 closed
before this plan; 1a → Task 5; 2 → Task 5; 2a closed before this plan;
3 → Tasks 1–2; 4 → Task 3. Wave 2 spec obligations — acceptance → Task 4;
M2/M3 reassessment → Task 6. `P66_BSCALE_TABLE` debt → Task 5. Nothing
in the ledger's list is silently dropped.

**Gates before guesses:** every flight (10, acceptance, optional item-2
flight) has a purpose and a pre-stated decision rule; Tasks 2 and 3
branch on measurements, and the branch tables are written before the
data. The two known traps are fenced: no threshold relaxation (Task 4),
no vendor edits (Task 2A fixes the sim side).

**User decision points:** exactly two — Gate 3 (what flies the attitude)
and Task 6 (wave end state). Both are product calls, both use
AskUserQuestion, everything else proceeds on stated rules.
