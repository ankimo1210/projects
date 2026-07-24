# EAGLE: Apollo 11 Lunar Descent Simulator

EAGLE is a browser-based simulator of the Apollo 11 lunar descent phase, running the original Luminary099 Apollo Guidance Computer (AGC) code on the yaAGC virtual machine. A Rust runtime bridges the AGC core to a web-based Lunar Module DSKY (display/keyboard), enabling interactive navigation and landing sequences with authentic period-correct computer behavior.

As of Phase 2 Wave 1, the real Luminary099 flies a **closed-loop P66 rate-of-descent landing** to soft touchdown against a 6-DoF physics model: PIPA/CDU sensors feed the AGC, its autopilot outputs (RCS jets, descent engine, THRUST DINC throttle) drive the dynamics, and an engineer telemetry board plots the descent in real time.

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

### Closed-loop P66 descent (Phase 2)

```bash
# Fly the real Luminary099 to a soft landing against our physics
make descent-p66

# Watch it live: serve the client and open the ENGR tab
make dev-client        # http://localhost:5173 → ENGR
```

The ENGR tab shows altitude / descent-rate / thrust / fuel strip charts, a
numeric panel, the P66 phase timeline, and `ROD −1 / +1 ft/s` buttons that
nudge the target sink rate.

## Tests

```bash
make test              # cargo unit tests + vitest client tests (no AGC needed)
make test-integration  # live AGC tests (golden + closed-loop; run `make agc` first)
```

The Wave 1 flagship is the closed-loop acceptance
(`tests/live_p66_descent.rs`): boot → P63 ignition → P66 → soft touchdown.
It runs ~8-11 minutes because the TIG countdown is real-time.

## Specification

See [docs/agc-channel-map.md](docs/agc-channel-map.md) for AGC I/O channel mappings and DSKY interface specification.

## References

- [VirtualAGC](https://www.ibiblio.org/apollo/) — AGC emulation and Luminary source
- [Apollo-11 repository](https://github.com/chrislgarry/Apollo-11) — annotated source code
