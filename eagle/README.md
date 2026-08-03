# EAGLE: Apollo 11 Lunar Descent Simulator

EAGLE is a browser-based simulator of the Apollo 11 lunar descent phase, running the original Luminary099 Apollo Guidance Computer (AGC) code on the yaAGC virtual machine. A Rust runtime bridges the AGC core to a web-based Lunar Module DSKY (display/keyboard), enabling interactive navigation and landing sequences with authentic period-correct computer behavior.

As of Phase 2 Wave 1 the loop is closed end to end — PIPA/CDU sensors feed the AGC, and its autopilot outputs (RCS jets, descent engine, THRUST DINC throttle) drive a 6-DoF rigid-body model whose telemetry an engineer board plots in real time. A run boots the AGC, uplinks the pad load, enters P63, reaches ENGINE ON, flips to ATT HOLD, and flies to ground contact.

> **Playable Alpha (2026-08-02): an assisted landing demo is available.**
> `make demo` keeps the real Luminary099 boot, DSKY, P63→P66 flow and ROD
> input, then uses an explicitly labelled Terminal Assist below 500 m to
> level the LM, remove horizontal speed and flare to a survivable contact.
> ENGR always shows `ASSISTED DEMO`, the assisted target and a transparent
> 100-point touchdown score. This is for getting the feel of the project;
> it is not evidence that the authentic landing acceptance passed. The
> existing authentic scenarios and thresholds below are unchanged. See the
> [Playable Alpha specification](docs/superpowers/specs/2026-08-02-playable-alpha.md).
> The first live validation completed `00→63→66` and landed Nominal at
> 2.20 m/s vertical, 0.16 m/s horizontal and 0.0° tilt (83/100), 91.8 s
> after ENGINE ON, with no alarm episode or PROG-lamp frame.

> **2026-08-03: the P65 altitude divergence is root-caused — no LR
> measurement was ever incorporated — and enabling incorporation exposed
> the next defect layer.** Offline forensics on Run 31's own recordings
> found `LRINH` (FLGWRD11 bit 8) clear in every flight ever flown:
> SERVICER computed DELTAH and discarded it at the `NOREASON`/`VUPDAT`
> gates, because **V57 — the astronaut action that permits LR
> incorporation — was never keyed**. The "navigation bias" is the item-3
> inertial drift (−0.86 m/s from the P64 pitchover), uncorrected; that is
> why three LR-presentation repairs (Runs 29-31) changed nothing. Two
> masked defects were fixed with it: the responder's ch33 bit-9 scale
> polarity was inverted against the rope's `SCALADJ`/`SCALECHK` (set =
> high scale), and the V01N01 erasable read-back killed the burn monitor.
> Run 32 proved V57 keyed in P00 is erased by V37's R00 flagword wipe (it
> must be keyed inside P63, as the crew did). With incorporation live and
> instrumented by a new core-dump sampler, `DELTAH` now stays inside
> ±50 m and `HCALC` tracks truth to ~25 m where Run 31 was −222 m out.
>
> **Run 34 then landed — Nominal, 1.14 m/s vertical, 0.50 m/s horizontal,
> 0.9° tilt, 640 kg of fuel left — and Run 35, same binary and scenario,
> crashed at 137.76 / 105.47 m/s.** The outcome is bimodal, so this is
> NOT a landing capability and nothing below is upgraded. Measured cause:
> at P64 entry the attitude loop wobbles, and past ~60° of tilt the H beam
> grazes the surface and returns a huge slant range that the responder
> still reports as data good — which the rope incorporates raw, because
> before HIGATE it runs no reasonableness test. A real landing radar
> cannot lock at those attitudes. Half of that gap is closed (the read
> path now applies the same 40,000 ft ceiling as the DATA GOOD discrete);
> the beam-pointing envelope still needs a sourced limit, and the P64
> wobble is the primary instability behind both crashes. Evidence:
> [2026-08-03-v57-lr-incorporation.md](docs/superpowers/notes/2026-08-03-v57-lr-incorporation.md) §9-12.

> **Current status (2026-08-02): LR integration passes; landing acceptance is
> RED.** Run 27 closed the LR velocity split and former LR alarms with the
> complete Apollo 11 pad block, five-sample beam reads and bounded 28-packet
> absolute `RNRAD` loads. Run 31 then flew Luminary's automatic P65 route
> (`00→63→64→65`) with the correct H-beam slant range and automatic 2,500 ft
> channel-33 scale transition. P65 controlled horizontal velocity and attitude
> but believed it was at the surface while still about 200 m high, hovered to
> fuel exhaustion and crashed at 25.90 m/s vertical / 1.72 m/s horizontal.
>
> The frozen M1 acceptance was also executed unchanged. Its forced-P66 path
> crashed at 20.70 m/s vertical / 62.40 m/s horizontal after 856.5 s, failing
> the 800 s limit before the later touchdown assertions. Thresholds remain
> 3.0 m/s vertical, 1.5 m/s horizontal and 12° tilt. See the current
> [handoff](docs/superpowers/notes/2026-08-01-handoff.md) and the measured
> [flight ledger](docs/superpowers/notes/2026-07-31-m1b-rod-loop.md#22-frozen-m1-acceptance-executed-unchanged--red).

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
> The acceptance test (`tests/live_pdi_descent.rs`) is frozen and was first
> executed unchanged on 2026-08-02. It failed at the first touchdown-block
> assertion: 856.5 s from ENGINE ON exceeded the 800 s limit. The measured
> result was Crash at 20.70 m/s vertical, 62.40 m/s horizontal and 11.67°,
> with 1,353 pre-contact PROG-lamp frames. Its limits were not relaxed.
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

### Playable Alpha (recommended)

```bash
# Terminal 1: real AGC + assisted demo scenario
make demo

# Terminal 2: browser client
make dev-client
```

Open `http://localhost:5173`, select **ENGR**, and watch the real startup and
descent. The first Alpha retains the real AGC pad-load/TIG wait (typically
about 5–7 minutes before ENGINE ON). Once P66 appears, `ROD −1 ft/s` descends
faster and `ROD +1 ft/s` descends slower. Each accepted click changes both
Luminary's `VDGVERT` and the assisted target by 0.3048 m/s; the target is
guarded to 0.4–8.0 m/s downward. Contact shows the existing
Nominal/Hard/Crash class plus a 0–100 score.

The Terminal Assist exists only in
[`scenarios/playable-demo.toml`](scenarios/playable-demo.toml). Running any
other scenario remains unassisted.

### Development runtime

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

# Final landing-radar path with the diagnostic forced P66 handover
make descent-lr-full

# Final landing-radar path with Luminary's automatic P64 → P65 transition
make descent-p65

# Instrument any of these runs:
#   EAGLE_ATT_DEBUG=<path>   attitude sign-chain trace (jets, gimbals, omega, torque)
#   EAGLE_TELEM_OUT=<path>   per-frame telemetry JSONL
#   EAGLE_LR_DEBUG=<path>    landing-radar CSV: velocity transactions AND
#                            range reads (true/measured slant, scale, counts)
#   EAGLE_CORE_SAMPLE=<path> R12 working set as a time series, read by symbol
#                            out of yaAGC's periodic core dump: HMEAS, HCALC,
#                            DELTAH, RGU, VGU, RNRAD, FLGWRD11, RADMODES,
#                            ch33, the LR reasonableness counters, FAILREG.
#                            This is the instrument of first resort for any
#                            question about what the AGC believes — the
#                            downlink cannot reach DELTAH or RGU at all.
#                            `cargo run --bin agc_state -- <core> <log>
#                            --sample-row` prints the same row for one dump.
# All four need ABSOLUTE paths (the runtime's cwd is `runtime/`).

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
  real profile from the PDI ignition point, radar bypassed. Executed unchanged
  on 2026-08-02: `00→63→64→66`, Crash at 20.70/62.40 m/s after 856.5 s,
  failing the frozen 800 s timeout first. Its scenario design limits remain
  unchanged and deliberately are not relaxed to what was measured.

## Specification

See [docs/agc-channel-map.md](docs/agc-channel-map.md) for AGC I/O channel mappings and DSKY interface specification.

## References

- [VirtualAGC](https://www.ibiblio.org/apollo/) — AGC emulation and Luminary source
- [Apollo-11 repository](https://github.com/chrislgarry/Apollo-11) — annotated source code
