# EAGLE: Apollo 11 Lunar Descent Simulator

EAGLE is a browser-based simulator of the Apollo 11 lunar descent phase, running the original Luminary099 Apollo Guidance Computer (AGC) code on the yaAGC virtual machine. A Rust runtime bridges the AGC core to a web-based Lunar Module DSKY (display/keyboard), enabling interactive navigation and landing sequences with authentic period-correct computer behavior.

As of Phase 2 Wave 1 the loop is closed end to end — PIPA/CDU sensors feed the AGC, and its autopilot outputs (RCS jets, descent engine, THRUST DINC throttle) drive a 6-DoF rigid-body model whose telemetry an engineer board plots in real time. A run boots the AGC, uplinks the pad load, enters P63, reaches ENGINE ON, flips to ATT HOLD, and flies to ground contact.

> **Wave 1 acceptance is RED — the landing is not soft, and P66 never flew.**
> MM66 does light (the measured mode sequence is `["00","63","66"]`), but only
> 0.6-1.8 s *after* ground contact, so it controlled nothing.
> The last measured run (2026-07-25) crashes at 41.5 m/s vertical / 10.7 m/s
> horizontal after 26.0 s, and the AGC only leaves P63 for MM66 at TIG+26.6 s
> — *after* ground contact — because P63's `AVEGEXIT` vector points at
> `SERVEXIT` until `P63ZOOM` swaps it to `LUNLAND` at the end of the 26 s
> ZOOMTIME, and GUILDENSTERN (the only path to P66) sits behind that swap.
> The attitude loop is healthy (it slews and captures cleanly). Two blockers:
> the 500 m gate is too low to survive the burn-in (a scenario fix), and the
> vehicle would arrive in P66 carrying the braking attitude IGNALG computed
> for a 1700 m/s burn, because the pad-loaded AGC state vector is the
> historical 15 km / 1700 m/s PDI point rather than the sim's hover gate.
> Full evidence, numbers and next steps:
> [docs/superpowers/notes/2026-07-25-wave1-reflight.md](docs/superpowers/notes/2026-07-25-wave1-reflight.md)
> — whose measured numbers predate the 2026-07-26 vehicle-constant
> corrections and will not reproduce; the conclusions stand, the numbers do
> not.

> **Wave 2 M1 flies the real descent, and does not land.** Six instrumented
> flights on 2026-07-26 (`make descent-full`, `scenarios/pdi-descent.toml`)
> start the truth state at the pad-loaded PDI ignition point, and **the
> last three** fly `MM ["00","63","64","66"]` — PDI → P63 braking → P64
> approach → crew-takeover P66, landing radar bypassed in-rope — with the
> AGC's own altitude rate tracking truth to a median 0.4 m/s (90 % of
> frames under 1.1 m/s) through the braking phase. That is the thing
> Wave 2 existed to decide: the nav/truth split that made Wave 1
> unfixable (cause C) is closed. (Runs 1-3 got progressively further —
> run 1 diverged 193 m/s and never left P63; runs 2 and 3 went through
> P65, which raised an alarm and stopped the guidance modulating the
> throttle.)
>
> All six runs also reported **zero PROG alarm episodes**, and that
> metric is structurally always zero here: `HeadlessResult.alarms` only
> ever receives `enter_p63_with_alarms`'s return value, and in PDI mode
> `run_scenario` returns right after `wait_engine_on`
> (`runner.rs:1113-1115`), so nothing can add to it after ignition. Run 3
> counted 794 PROG-lamp frames and still reported zero episodes. Read it
> as **"no alarm episodes in the pre-ignition P63 dialog"** and nothing
> more; the post-ignition signal is `prog_lamp_frames`.
>
> Touchdown is still a **crash**. P66's rate loop limit-cycles — run 6 ran
> the throttle stop-to-stop (0 → 48 132 N) for 218 s with the sink rate
> spanning −34.1 to +16.2 m/s — and a crewless P66 holds attitude with
> nobody on the hand controller, so the ~12° tilt P64 leaves behind flies
> the vehicle sideways: contact at 30.86 m/s vertical, 60.04 m/s
> horizontal, 12.8° of tilt. Four vehicle constants were corrected against
> the flown rope's own SI values along the way (`PIPA_INCR` 0.0585 → 0.01
> m/s/pulse, `THRUST_N_PER_PULSE` → 12.5319585 N/bit, DPS full throttle →
> 48 145.4 N, `DPS_TAU` → 0.2 s) and none of them cured it.
>
> The acceptance test (`tests/live_pdi_descent.rs`) is frozen and **has
> never been run**: it was written after the flight budget was spent, so it
> records the target, not a result. On the last three flights its mode,
> alarm-episode and AGC-clock assertions would pass, its touchdown block
> would fail, and its `prog_lamp_frames == 0` gate would fail on run 5 —
> which counted 21 lamp frames, all raised *after* ground contact.
> Measured numbers, citations and the open items:
> [docs/superpowers/notes/2026-07-26-m1-pdi-flight.md](docs/superpowers/notes/2026-07-26-m1-pdi-flight.md).

> **2026-07-31 (M1b) — flights 7 and 8 still crash, and the prime suspect
> is named.** 29.23/72.04 m/s and 36.81/64.18 m/s: the loop's gain was
> deliberately not changed. `TAUROD`'s b-scale is derived in
> `scenarios/p66-padload.toml` from a premise the repo's own spike-B
> measurement contradicts, so the AGC has been flying a rate loop **4× or
> 8× too fast** against the rope's 0.2 s `THROTLAG`. The direction is
> certain, the factor is **not** — two unpinned one-power-of-two shifts
> remain in the chain — so the pad load is deliberately unchanged.
>
> τ **cannot** be measured from a descent: a saturated relay limit cycle
> carries almost no information about the gain inside it. Three estimators
> gave r² = 0.088 / 0.042 / 0.63, and the last is a trap that fits the
> cycle's own quarter period (peak at 5.0 s lag against a 19.4 s period).
> The experiment that works is an open-loop step test.
>
> Fixed along the way: a refused ROD load was silent and blinded the whole
> run (flight 7 painted 6 `HDOTDISP` values in 222 s of P66 and raised 41
> PROG frames; flight 8, after the fix, painted 231 and raised 0), and
> `EAGLE_TELEM_OUT` swallowed a bad path silently — it needs an ABSOLUTE
> path, and now panics rather than costing a flight.
> [docs/superpowers/notes/2026-07-31-m1b-rod-loop.md](docs/superpowers/notes/2026-07-31-m1b-rod-loop.md).

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
# (scenarios/p66-gate-fast.toml — NOT the acceptance gate). UNTESTED LIVE:
# the next shorter lead (24000 cs) was measured too tight and aborts in P63
# entry with FAILREG 01703 "IGNITION TIME SLIPPED". If 01703 reappears here,
# fall back to 36000 cs, i.e. use `make descent-p66`.
make descent-p66-fast

# Wave 2 M1: the real descent — truth starts at the pad-loaded PDI ignition
# point and the AGC flies PDI → P63 → P64 → P66 with the landing radar
# bypassed in-rope (scenarios/pdi-descent.toml). ~20 min wall. It does NOT
# land — see the M1 status block above. Prints the same `[accept]`
# diagnostics block as the acceptance test, so the run records itself.
make descent-full

# Instrument any of these runs:
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
  A click only changes anything once the AGC is in P66: the Wave 1 gate
  never gets there before ground contact, while `make descent-full` does
  (~TIG+649 s, measured).
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

`make test-integration` runs every `#[ignore]`d test serially, which since
2026-07-26 includes the M1 acceptance — ~35 minutes end to end, and it goes
red there. Run one binary at a time with
`cargo test -p eagle-runtime --test <name> -- --ignored --test-threads=1`.

Two live acceptance tests, both currently **red**, for different reasons:

- **Wave 1** — `tests/live_p66_descent.rs` (port 19904, ~8-11 min): boot →
  P63 ignition → ENGINE ON → touchdown from a hover gate, asserting a
  *nominal* landing. Fails on the touchdown class; P66 never flies (see the
  re-flight ledger linked above).
- **Wave 2 M1** — `tests/live_pdi_descent.rs` (port 19905, ~20 min): the
  real profile from the PDI ignition point, radar bypassed. **Never run** —
  frozen after the flight budget was spent. On the six measured flights its
  mode-sequence, alarm and AGC-clock assertions would pass and its
  touchdown assertions would fail; the file's own header says which is
  which. Its thresholds are the scenario's design limits and are
  deliberately not relaxed to what was measured.

## Specification

See [docs/agc-channel-map.md](docs/agc-channel-map.md) for AGC I/O channel mappings and DSKY interface specification.

## References

- [VirtualAGC](https://www.ibiblio.org/apollo/) — AGC emulation and Luminary source
- [Apollo-11 repository](https://github.com/chrislgarry/Apollo-11) — annotated source code
