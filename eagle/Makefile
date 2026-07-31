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
# ~20 min wall, measured (boot ~5.7 min to ENGINE ON at t ≈ 344 s, then
# ~865 s of descent, plus teardown; the AGC clock ran 0.944x real time on
# every M1 flight). Not in CI. Does NOT land — see the M1 status block in
# README.md. The earlier "~18-19 min / ~95.2%" here was the Wave 1 budget
# and Wave 1's clock figure, neither measured on this target.
#
# Always captures the raw packet trace. Flight 7 (2026-07-31) did not, and
# so the KEY REL / OPR ERR lamp state that would have confirmed a refused
# ROD load outright was unrecoverable after the fact — a 20-minute flight
# short of one answer for want of a flag. EAGLE_TELEM_OUT and
# EAGLE_ATT_DEBUG stay opt-in, but they need ABSOLUTE paths: the runtime's
# cwd is runtime/, and a relative path from here lands somewhere else.
descent-full: agc
	mkdir -p build/traces
	cd runtime && cargo run -p eagle-runtime -- \
	  --yaagc ../build/agc/yaAGC --core ../build/agc/Luminary099.bin \
	  --scenario ../scenarios/pdi-descent.toml --root .. \
	  --trace-out ../build/traces/pkt-descent-full.jsonl

lint:
	cd runtime && cargo clippy --workspace --all-targets -- -D warnings
	cd runtime && cargo fmt --all --check
	cd client && npm run lint
