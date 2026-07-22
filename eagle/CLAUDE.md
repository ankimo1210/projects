# eagle — Apollo 11 lunar descent simulator (Phase 1)

Original Luminary099 running in vendored yaAGC, bridged to a web DSKY.

- Spec: docs/superpowers/specs/2026-07-21-eagle-roadmap-design.md
- Channel semantics: docs/agc-channel-map.md (octal; update with citations)
- Build AGC artifacts once: `make agc` (fetches vendor, builds yaYUL/yaAGC,
  assembles Luminary099, verifies hashes)
- Fast tests: `make test` (no AGC needed)
- Live AGC tests: `make test-integration`
- Run: `make dev-runtime` + `make dev-client`, open http://localhost:5173
- vendor/ is read-only and git-ignored; pins in vendor/manifest.json
- vendor pins: Apollo-11 transcription diverges from virtualagc's
  (proofreading drift, ~20 files); shipped binary is virtualagc's assembly;
  cross-check status recorded in build/agc/manifest.json
- prerequisite: jq (vendor pinning); gcc/make (vendor build); node 22+
  (client)
