# EAGLE: Apollo 11 Lunar Descent Simulator

EAGLE is a browser-based simulator of the Apollo 11 lunar descent phase, running the original Luminary099 Apollo Guidance Computer (AGC) code on the yaAGC virtual machine. A Rust runtime bridges the AGC core to a web-based Lunar Module DSKY (display/keyboard), enabling interactive navigation and landing sequences with authentic period-correct computer behavior.

As of Phase 2 Wave 1 the loop is closed end to end — PIPA/CDU sensors feed the AGC, and its autopilot outputs (RCS jets, descent engine, THRUST DINC throttle) drive a 6-DoF rigid-body model whose telemetry an engineer board plots in real time. A run boots the AGC, uplinks the pad load, enters P63, reaches ENGINE ON, flips to ATT HOLD, and flies to ground contact.

> **Wave 1 acceptance is RED — the landing is not soft, and P66 is not reached.**
> The last measured run (2026-07-25) crashes at 41.5 m/s vertical / 10.7 m/s
> horizontal after 26.0 s, and the AGC only leaves P63 for MM66 at TIG+26.6 s
> — *after* ground contact — because Luminary suspends the landing-guidance
> group for the 26 s ZOOMTIME burn-in. The attitude loop is healthy (it slews
> and captures cleanly); the blockers are the gate geometry and the fact that
> the pad-loaded AGC state vector is the historical 15 km / 1700 m/s PDI point
> rather than the sim's 500 m hover, so nothing closes the navigation loop.
> Full evidence, numbers and next steps:
> [docs/superpowers/notes/2026-07-25-wave1-reflight.md](docs/superpowers/notes/2026-07-25-wave1-reflight.md).

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

### Closed-loop descent (Phase 2)

```bash
# Fly the real Luminary099 against our physics (boot → P63 → ENGINE ON →
# ground contact). ~7 min: the TIG countdown is real time.
make descent-p66

# Same loop with a 1 min shorter TIG lead, for debug iteration only
# (scenarios/p66-gate-fast.toml — NOT the acceptance gate)
make descent-p66-fast

# Instrument either run:
#   EAGLE_ATT_DEBUG=<path>  attitude sign-chain trace (jets, gimbals, omega, torque)
#   EAGLE_TELEM_OUT=<path>  per-frame telemetry JSONL

# Watch it live: serve the client and open the ENGR tab
make dev-client        # http://localhost:5173 → ENGR
```

The ENGR tab shows altitude / descent-rate / thrust / fuel strip charts, a
numeric panel, the phase timeline, and `ROD −1 / +1 ft/s` buttons.

What the ROD buttons actually do:

- **Scenario mode** (`--scenario`, i.e. the `descent-p66*` targets): a click
  is delivered to the AGC as a signed `RODCOUNT` erasable load through the
  server → headless wiring, merged with the scenario's own ROD schedule.
  Stock yaAGC raises no interrupt for channel 016, so the switch discrete
  would be ignored — see `docs/agc-channel-map.md` ("Rod Switch Click").
  A click only changes anything once the AGC is in P66, which the current
  acceptance run does not reach before ground contact.
- **Phase-1 DSKY-only mode** (`make dev-runtime`): the click emits the ch016
  discrete, which stock yaAGC ignores. It is a no-op.

Web DSKY keys are forwarded to the AGC in scenario mode, but are **dropped
while a scripted DSKY sequence is running** (the boot choreography, or a
`rod_load` erasable write), with a `headless: client key dropped (script
busy)` line on stderr — a keystroke interleaved into a `V21N01E…E…E` load
would corrupt the erasable being written.

## Tests

```bash
make test              # cargo unit tests + vitest client tests (no AGC needed)
make lint              # clippy -D warnings, cargo fmt --check, client oxlint
make test-integration  # live AGC tests (golden + closed-loop; run `make agc` first)
```

The Wave 1 flagship is the closed-loop acceptance
(`tests/live_p66_descent.rs`): boot → P63 ignition → ENGINE ON → touchdown,
asserting a *nominal* landing. It runs ~8-11 minutes because the TIG
countdown is real-time, and it currently **fails** on the touchdown class —
see the re-flight ledger linked above.

## Specification

See [docs/agc-channel-map.md](docs/agc-channel-map.md) for AGC I/O channel mappings and DSKY interface specification.

## References

- [VirtualAGC](https://www.ibiblio.org/apollo/) — AGC emulation and Luminary source
- [Apollo-11 repository](https://github.com/chrislgarry/Apollo-11) — annotated source code
