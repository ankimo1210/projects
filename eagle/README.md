# EAGLE: Apollo 11 Lunar Descent Simulator

EAGLE is a browser-based simulator of the Apollo 11 lunar descent phase, running the original Luminary099 Apollo Guidance Computer (AGC) code on the yaAGC virtual machine. A Rust runtime bridges the AGC core to a web-based Lunar Module DSKY (display/keyboard), enabling interactive navigation and landing sequences with authentic period-correct computer behavior.

## Prerequisites

- `jq`, `gcc`, `make` — vendor fetch/build (`make agc`)
- Rust toolchain (`cargo`) — runtime
- Node.js 22+ (`npm`) — web client

## Quickstart

```bash
# Build AGC tools and assemble Luminary099 binary (once)
make agc

# In one terminal: run AGC runtime
make dev-runtime

# In another terminal: serve the web client
make dev-client
```

Browse to `http://localhost:5173` to interact with the DSKY.

## Tests

Phase 1 definition of done requires both of these to pass:

```bash
make test              # cargo unit tests + vitest client tests (no AGC needed)
make test-integration  # live AGC tests (golden traces; run `make agc` first)
```

## Specification

See [docs/agc-channel-map.md](docs/agc-channel-map.md) for AGC I/O channel mappings and DSKY interface specification.

## References

- [VirtualAGC](https://www.ibiblio.org/apollo/) — AGC emulation and Luminary source
- [Apollo-11 repository](https://github.com/chrislgarry/Apollo-11) — annotated source code
