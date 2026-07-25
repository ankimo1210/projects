# eagle — Apollo 11 lunar descent simulator (Phase 2 Wave 1)

Original Luminary099 running in vendored yaAGC, bridged to a web DSKY, and —
as of Phase 2 Wave 1 — flying a closed loop against our own 6-DoF physics
(crates `eagle-dynamics`, `eagle-sensors`; sim thread in
`eagle-runtime::sim`): boot → pad load → P63 → ENGINE ON → ATT HOLD →
ground contact.

**Wave 1 acceptance is RED.** The landing is not soft and P66 is never
reached: the last measured run (2026-07-25) crashes at 41.5 m/s vertical /
10.7 m/s horizontal after 26.0 s, while MM66 first appears at TIG+26.6 s
(Luminary suspends the landing-guidance group for the 26 s ZOOMTIME
burn-in). The attitude loop is fine — the blockers
are the 500 m gate geometry and the pad-loaded AGC state vector (the
historical 15 km / 1700 m/s PDI point, not the sim's hover gate), so there
is no navigation loop closure. Do not restate "soft touchdown" anywhere
until it is measured. Evidence, numbers and next steps:
`docs/superpowers/notes/2026-07-25-wave1-reflight.md`.

- Specs: docs/superpowers/specs/2026-07-21-eagle-roadmap-design.md,
  docs/superpowers/specs/2026-07-22-eagle-phase2-closed-loop-design.md
- Channel semantics: docs/agc-channel-map.md (octal; update with citations)
- Build AGC artifacts once: `make agc` (fetches vendor, builds yaYUL/yaAGC,
  assembles Luminary099, verifies hashes)
- Fast tests: `make test` (no AGC needed) — Rust unit + client vitest
- Lint gate: `make lint` (clippy `-D warnings`, `cargo fmt --check`,
  client oxlint) — same set the CI fast lane runs
- Live AGC tests: `make test-integration` (serial, `--test-threads=1`)
- Phase 1 run (DSKY only): `make dev-runtime` + `make dev-client`,
  open http://localhost:5173
- Closed-loop descent: `make descent-p66` (real Luminary099 against our
  physics, to ground contact); `make descent-p66-fast` for debug iteration
  (same loop, TIG lead 30000 cs instead of 36000 — `p66-gate-fast.toml`,
  debug only, NOT the acceptance gate; 24000 was measured too tight and
  aborts with FAILREG 01703 "IGNITION TIME SLIPPED"). Watch either live with
  `make dev-client` → ENGR tab (strip charts + ROD −/+ buttons)
- Debug env vars for a live run: `EAGLE_ATT_DEBUG=<path>` (attitude
  sign-chain trace: t, jet bitmask, gimbals, omega, torque — one line per
  10 ticks post-freeze), `EAGLE_TELEM_OUT=<path>` (per-frame telemetry
  JSONL)
- Scenarios: `scenarios/p66-gate.toml` (acceptance), `p66-padload.toml`
  (spike-calibrated pad-load), `p66-gate-imu-bias.toml` (error-model)
- Wave 1 acceptance test: `cargo test -p eagle-runtime --test
  live_p66_descent -- --ignored --test-threads=1` (~8-11 min: the TIG
  countdown is real-time; ENGINE ON is ~350 s after boot). The
  `EAGLE_SLOW=1`-gated error-model run in the same file is not part of
  default `make test-integration`.
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
