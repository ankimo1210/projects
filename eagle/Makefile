.PHONY: vendor agc-tools agc test test-integration dev demo descent-p66 descent-p66-fast descent-full descent-lr-alt-only descent-lr-pos1 descent-lr-full descent-lr-x-only descent-p65 lint

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

# Playable Alpha: real Luminary099/DSKY/P63→P66 with an explicitly labelled,
# scenario-local terminal safety layer. This is a game demo, NOT an authentic
# acceptance result. Start `make dev-client` in another terminal and open ENGR.
demo: agc
	@echo "ASSISTED DEMO — run 'make dev-client' separately, then open http://localhost:5173 → ENGR"
	mkdir -p build/traces
	cd runtime && cargo run -p eagle-runtime -- \
	  --yaagc ../build/agc/yaAGC --core ../build/agc/Luminary099.bin \
	  --scenario ../scenarios/playable-demo.toml --root .. \
	  --trace-out ../build/traces/pkt-playable-demo.jsonl

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

# M3 diagnostic bisection: keep LR altitude live, but report every LR
# velocity read as data NOT-good. The scenario records the decision rule
# against flight 11 before launch; this target is not an acceptance gate.
descent-lr-alt-only: agc
	mkdir -p build/traces
	cd runtime && cargo run -p eagle-runtime -- \
	  --yaagc ../build/agc/yaAGC --core ../build/agc/Luminary099.bin \
	  --scenario ../scenarios/pdi-descent-lr-alt-only.toml --root .. \
	  --trace-out ../build/traces/pkt-m1-lr-alt-only.jsonl

# M3 diagnostic: velocity data enabled with the simulator and rope both
# using antenna position 1 until Luminary explicitly commands position 2.
descent-lr-pos1: agc
	mkdir -p build/traces
	cd runtime && cargo run -p eagle-runtime -- \
	  --yaagc ../build/agc/yaAGC --core ../build/agc/Luminary099.bin \
	  --scenario ../scenarios/pdi-descent-lr-pos1.toml --root .. \
	  --trace-out ../build/traces/pkt-m1-lr-pos1.jsonl

# M3 integration: complete Apollo 11 LR/P65 pad block, five-sample radar
# transactions and commanded POS1->POS2 antenna motion all enabled.
descent-lr-full: agc
	mkdir -p build/traces
	cd runtime && cargo run -p eagle-runtime -- \
	  --yaagc ../build/agc/yaAGC --core ../build/agc/Luminary099.bin \
	  --scenario ../scenarios/pdi-descent-lr-full.toml --root .. \
	  --trace-out ../build/traces/pkt-m1-lr-full.jsonl

# M3 beam bisection: LR altitude + velocity X only; Y/Z report not-good.
descent-lr-x-only: agc
	mkdir -p build/traces
	cd runtime && cargo run -p eagle-runtime -- \
	  --yaagc ../build/agc/yaAGC --core ../build/agc/Luminary099.bin \
	  --scenario ../scenarios/pdi-descent-lr-x-only.toml --root .. \
	  --trace-out ../build/traces/pkt-m1-lr-x-only.jsonl

# M3 end-to-end diagnostic: full LR with no forced P64->P66 handover, so
# Luminary flies its automatic P65 vector-velocity law. Not the frozen gate.
descent-p65: agc
	mkdir -p build/traces
	cd runtime && cargo run -p eagle-runtime -- \
	  --yaagc ../build/agc/yaAGC --core ../build/agc/Luminary099.bin \
	  --scenario ../scenarios/pdi-descent-p65.toml --root .. \
	  --trace-out ../build/traces/pkt-m1-p65.jsonl

lint:
	cd runtime && cargo clippy --workspace --all-targets -- -D warnings
	cd runtime && cargo fmt --all --check
	cd client && npm run lint
