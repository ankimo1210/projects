# eagle — Apollo 11 lunar descent simulator (Phase 2 Wave 1)

Original Luminary099 running in vendored yaAGC, bridged to a web DSKY, and —
as of Phase 2 Wave 1 — flying a closed-loop P66 rate-of-descent landing
against our own 6-DoF physics (crates `eagle-dynamics`, `eagle-sensors`;
sim thread in `eagle-runtime::sim`).

- Specs: docs/superpowers/specs/2026-07-21-eagle-roadmap-design.md,
  docs/superpowers/specs/2026-07-22-eagle-phase2-closed-loop-design.md
- Channel semantics: docs/agc-channel-map.md (octal; update with citations)
- Build AGC artifacts once: `make agc` (fetches vendor, builds yaYUL/yaAGC,
  assembles Luminary099, verifies hashes)
- Fast tests: `make test` (no AGC needed) — Rust unit + client vitest
- Live AGC tests: `make test-integration` (serial, `--test-threads=1`)
- Phase 1 run (DSKY only): `make dev-runtime` + `make dev-client`,
  open http://localhost:5173
- Closed-loop P66 descent: `make descent-p66` (real Luminary099 flies to
  soft touchdown); watch it live with `make dev-client` → ENGR tab
  (strip charts + ROD −/+ buttons)
- Scenarios: `scenarios/p66-gate.toml` (acceptance), `p66-padload.toml`
  (spike-calibrated pad-load), `p66-gate-imu-bias.toml` (error-model)
- Wave 1 acceptance test: `cargo test -p eagle-runtime --test
  live_p66_descent -- --ignored --test-threads=1` (~8-11 min: the TIG
  countdown is real-time; ENGINE ON is ~350 s after boot). The
  `EAGLE_SLOW=1`-gated error-model run in the same file is not part of
  default `make test-integration`.
- ROD without a vendor patch: stock yaAGC raises no interrupt for channel
  016, so a rate-of-descent click is issued as a direct RODCOUNT erasable
  load (`runner::rod_load`), never the ch016 switch discrete. vendor/ stays
  READ-ONLY. See docs/agc-channel-map.md ("Rod Switch Click").
- vendor/ is read-only and git-ignored; pins in vendor/manifest.json
- vendor pins: Apollo-11 transcription diverges from virtualagc's
  (proofreading drift, ~20 files); shipped binary is virtualagc's assembly;
  cross-check status recorded in build/agc/manifest.json
- prerequisite: jq (vendor pinning); gcc/make (vendor build); node 22+
  (client)
