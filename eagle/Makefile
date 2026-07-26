.PHONY: vendor agc-tools agc test test-integration dev descent-p66 descent-p66-fast descent-full lint

vendor:
	bash scripts/fetch-vendor.sh

agc-tools: vendor
	bash scripts/build-agc-tools.sh

agc: agc-tools
	bash scripts/assemble-luminary.sh

test:
	cd runtime && cargo test
	cd client && npm test

test-integration: agc
	cd runtime && cargo test -- --ignored --test-threads=1

dev:
	@echo "run 'make dev-runtime' and 'make dev-client' in two terminals"

dev-runtime: agc
	cd runtime && cargo run -p eagle-runtime -- \
	  --yaagc ../build/agc/yaAGC --core ../build/agc/Luminary099.bin

dev-client:
	cd client && npm run dev

# Closed-loop descent: real Luminary099 against our 6-DoF physics, boot →
# P63 → ENGINE ON → ATT HOLD → ground contact. NOT a soft landing today —
# see docs/superpowers/notes/2026-07-25-wave1-reflight.md. Open the ENGR
# tab in the client to watch telemetry.
descent-p66: agc
	cd runtime && cargo run -p eagle-runtime -- \
	  --yaagc ../build/agc/yaAGC --core ../build/agc/Luminary099.bin \
	  --scenario ../scenarios/p66-gate.toml --root ..

# Debug iteration: same closed loop, 60 s shorter TIG lead (30000 cs).
# UNTESTED LIVE: 24000 cs was measured too tight on this host and aborts in
# P63 entry with FAILREG 01703 ("IGNITION TIME SLIPPED"); 30000 splits the
# difference against the acceptance gate's 36000. If 01703 reappears, fall
# back to 36000 (i.e. use `descent-p66`). Debug only — NOT the acceptance
# gate. See scenarios/p66-gate-fast.toml.
descent-p66-fast: agc
	cd runtime && cargo run -p eagle-runtime -- \
	  --yaagc ../build/agc/yaAGC --core ../build/agc/Luminary099.bin \
	  --scenario ../scenarios/p66-gate-fast.toml --root ..

# Wave 2 M1: the real descent — PDI → P63 → P64 → P66, radar bypassed.
# ~18-19 min wall (boot ~6 min + P63 burn ~8.5 min + P64/P66; the AGC clock
# runs ~95.2% of real time on this host). Not in CI.
descent-full: agc
	cd runtime && cargo run -p eagle-runtime -- \
	  --yaagc ../build/agc/yaAGC --core ../build/agc/Luminary099.bin \
	  --scenario ../scenarios/pdi-descent.toml --root ..

lint:
	cd runtime && cargo clippy --workspace --all-targets -- -D warnings
	cd runtime && cargo fmt --all --check
	cd client && npm run lint
