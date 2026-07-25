.PHONY: vendor agc-tools agc test test-integration dev descent-p66 lint

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

# Closed-loop P66 descent: real Luminary099 flies to soft touchdown against
# our 6-DoF physics. Open the ENGR tab in the client to watch telemetry.
descent-p66: agc
	cd runtime && cargo run -p eagle-runtime -- \
	  --yaagc ../build/agc/yaAGC --core ../build/agc/Luminary099.bin \
	  --scenario ../scenarios/p66-gate.toml --root ..

lint:
	cd runtime && cargo clippy --workspace --all-targets -- -D warnings
	cd runtime && cargo fmt --all --check
	cd client && npm run lint
