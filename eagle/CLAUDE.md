# eagle — Apollo 11 lunar descent simulator (Phase 2 Wave 1)

Original Luminary099 running in vendored yaAGC, bridged to a web DSKY, and —
as of Phase 2 Wave 1 — flying a closed loop against our own 6-DoF physics
(crates `eagle-dynamics`, `eagle-sensors`; sim thread in
`eagle-runtime::sim`): boot → pad load → P63 → ENGINE ON → ATT HOLD →
ground contact.

**Wave 1 acceptance is RED.** The landing is not soft and **P66 never
flew**: MM66 does light — the MM assert passes on the measured sequence
`["00","63","66"]` — but only 0.6-1.8 s AFTER ground contact, so it
controlled nothing. The last measured run (2026-07-25) crashes at 41.5 m/s
vertical / 10.7 m/s horizontal after 26.0 s, with MM66 first appearing at
TIG+26.6 s:
P63's `AVEGEXIT` points at `SERVEXIT` until `P63ZOOM` swaps it to
`LUNLAND` at the end of the 26 s ZOOMTIME, and GUILDENSTERN (R13, the only
path to P66) sits behind that swap. The attitude loop is fine. Two
blockers: (1) the 500 m gate is too low to survive the burn-in at the DPS
idle stop — a scenario fix, `live_spike_p66.rs` already starts at 3000 m
for exactly this reason; (2) the pad-loaded AGC state vector is the
historical 15 km / 1700 m/s PDI point, not the sim's hover gate, so the
vehicle would enter P66 holding the braking attitude IGNALG computed for a
1700 m/s burn (measured 107-108° tilt) — and P66 holds attitude, it does
not re-orient. Do not restate "soft touchdown" anywhere until it is
measured. Evidence, numbers and next steps:
`docs/superpowers/notes/2026-07-25-wave1-reflight.md` — **whose
measurements predate the 2026-07-26 vehicle-constant corrections
(`PIPA_INCR`, `THRUST_N_PER_PULSE`, DPS full throttle, `DPS_TAU`) and will
not reproduce**; the conclusions stand, the numbers do not.

**Wave 2 M1 (`scenarios/pdi-descent.toml`, `make descent-full`) flies the
real profile and does not land yet.** Six instrumented flights on
2026-07-26; **the last three** fly PDI → P63 → P64 → P66 with the radar
bypassed in-rope and **zero PROG alarm episodes** (runs 1-3 did not reach
that sequence), AGC-vs-truth altitude-rate error a median 0.4 m/s through
the braking phase (p90 1.1 m/s — not "under 1 m/s"), MM64 at TIG+488.6 s
and the sim-driven handover at 250 m. Run 5 counted 21 PROG-lamp frames,
all after ground contact — unexplained, ledger "Open" 2a. Touchdown is still a crash: P66's rate loop limit-cycles (throttle
slamming idle ↔ full) and nothing flies the attitude, so v_horiz runs
away. **Every physical constant in the accelerometer and propulsion chain
is now the flown rope's own number**, four of them corrected by flying:
`PIPA_INCR` 0.0585 → **0.01** m/s/pulse (Luminary's KPIP — 0.0585 is the
*command module* quantum, `Comanche055/SERVICER207.agc:790`),
`THRUST_N_PER_PULSE` 12.0 → **12.5319585** N/bit, DPS full throttle
42 500 → **48 145.4** N, `DPS_TAU` 0.3 → **0.2** s — the last three from
`CONTROLLED_CONSTANTS.agc:132-135`. Flight 6 proved the remaining
braking-gate error (911 m / 47 m/s) is *not* thrust. Numbers, citations
and the open blockers:
`docs/superpowers/notes/2026-07-26-m1-pdi-flight.md`.

**The M1 acceptance (`tests/live_pdi_descent.rs`) is frozen and has never
been run.** It was written after the 6-flight budget was spent, so it is a
target, not a result: on the last three flights its mode, alarm-episode and
AGC-clock blocks would pass, its touchdown block would fail, and its
`prog_lamp_frames == 0` gate would fail on run 5. Do not relax its
thresholds (they are the scenario's design limits) and do not describe M1
as landing anything until that test is the thing that measured it.

- Specs: docs/superpowers/specs/2026-07-21-eagle-roadmap-design.md,
  docs/superpowers/specs/2026-07-22-eagle-phase2-closed-loop-design.md
- Channel semantics: docs/agc-channel-map.md (octal; update with citations)
- Build AGC artifacts once: `make agc` (fetches vendor, builds yaYUL/yaAGC,
  assembles Luminary099, verifies hashes)
- Fast tests: `make test` (no AGC needed) — Rust unit + client vitest
- Lint gate: `make lint` (clippy `-D warnings`, `cargo fmt --check`,
  client oxlint) — same set the CI fast lane runs
- Live AGC tests: `make test-integration` (serial, `--test-threads=1`).
  It runs every `#[ignore]`d test in the runtime, so since 2026-07-26 it
  includes the ~20 min M1 acceptance below and takes ~35 min end to end.
  It is RED on **both** acceptance tests — Wave 1's on the touchdown class,
  M1's on the touchdown block — so the useful command is usually a single
  binary: `cargo test -p eagle-runtime --test <name> -- --ignored
  --test-threads=1`.
- Phase 1 run (DSKY only): `make dev-runtime` + `make dev-client`,
  open http://localhost:5173
- Closed-loop descent: `make descent-p66` (real Luminary099 against our
  physics, to ground contact); `make descent-p66-fast` for debug iteration
  (same loop, TIG lead 30000 cs instead of 36000 — `p66-gate-fast.toml`,
  debug only, NOT the acceptance gate; 24000 was measured too tight and
  aborts with FAILREG 01703 "IGNITION TIME SLIPPED"). **30000 is untested
  live** — if 01703 reappears, fall back to 36000 (`make descent-p66`).
  Watch either live with
  `make dev-client` → ENGR tab (strip charts + ROD −/+ buttons)
- Wave 2 M1 descent: `make descent-full` (`scenarios/pdi-descent.toml` —
  PDI → P63 → P64 → P66, radar bypassed). ~20 min wall: boot ~5.7 min,
  ENGINE ON at t ≈ 344 s, MM64 at TIG+489 s, handover at TIG+647 s. Not in
  CI. It prints the same `[accept]` diagnostics block as the acceptance
  test, so an interactive flight records itself.
- Debug env vars for a live run: `EAGLE_ATT_DEBUG=<path>` (attitude
  sign-chain trace: t, jet bitmask, gimbals, omega, torque — one line per
  10 ticks post-freeze), `EAGLE_TELEM_OUT=<path>` (per-frame telemetry
  JSONL)
- Scenarios: `scenarios/pdi-descent.toml` (Wave 2 M1 acceptance),
  `p66-gate.toml` (Wave 1 acceptance), `p66-padload.toml`
  (spike-calibrated pad-load, shared by both), `p66-gate-imu-bias.toml`
  (error-model)
- Wave 1 acceptance test: `cargo test -p eagle-runtime --test
  live_p66_descent -- --ignored --test-threads=1` (~8-11 min: the TIG
  countdown is real-time; ENGINE ON is ~350 s after boot). The
  `EAGLE_SLOW=1`-gated error-model run in the same file is not part of
  default `make test-integration`.
- Wave 2 M1 acceptance test: `cargo test -p eagle-runtime --test
  live_pdi_descent -- --ignored --test-threads=1` (port 19905, ~20 min).
  Frozen 2026-07-26 and **never run** — see the status block at the top of
  the file for which of its assertions the six flights met and which they
  did not.
- ROD without a vendor patch: stock yaAGC raises no interrupt for channel
  016, so in **scenario mode** a rate-of-descent click — from the client's
  ENGR buttons or the scenario's own schedule — is issued as a direct
  RODCOUNT erasable load (`runner::rod_load`), never the ch016 switch
  discrete. In **Phase-1 DSKY-only mode** (`make dev-runtime`) the button
  still emits the ch016 discrete, which yaAGC ignores: a no-op. vendor/
  stays READ-ONLY. See docs/agc-channel-map.md ("Rod Switch Click").
- Client DSKY keys are forwarded into the same pump the choreography uses,
  but are DROPPED while a `DskyScript` sequence is in flight (boot
  choreography or a `rod_load` erasable write), logging
  `headless: client key dropped (script busy)`. A stray keystroke inside a
  `V21N01E…E…E` load would corrupt the word being written.
- vendor/ is read-only and git-ignored; pins in vendor/manifest.json
- vendor pins: Apollo-11 transcription diverges from virtualagc's
  (proofreading drift, ~20 files); shipped binary is virtualagc's assembly;
  cross-check status recorded in build/agc/manifest.json
- prerequisite: jq (vendor pinning); gcc/make (vendor build); node 22+
  (client)
