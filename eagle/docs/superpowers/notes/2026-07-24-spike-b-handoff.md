# Spike B handoff — 2026-07-24

Task 7 is paused before live acceptance. Commit `39f874d8` contains the
closed-loop descent probe, THRUST responder, bounded one-dimensional hover
model, ATT-HOLD/ROD controls, and diagnostics.

## Verified

- `cargo test -p eagle-runtime runner`: 9 passed.
- `cargo check -p eagle-runtime --bin descent_probe`: passed.
- The first diagnosed P63 throttle transaction was exactly MOUT 4096.
- Luminary uses that engine-off transaction to seek the zero throttle stop
  (`P40-P47.agc:490-494`), so the modeled actuator position must saturate at
  `0..4096`.
- DINC requests now use a maximum-32 outstanding-response credit window,
  preventing queued requests from producing excessive ZOUT chatter.
- GUILDENSTERN requires ATT HOLD and a non-zero RODCOUNT to enter P66 from
  MM63 (`LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:203-217`).

## yaAGC boundary fix

The pinned yaAGC Socket API updates channel 016 but does not request
interrupt 6, so KEYRUPT2/MARKRUPT/DESCBITS cannot observe a ROD click.
The fix is stored in
`scripts/patches/virtualagc-ch016-keyrupt2.patch` and applied idempotently
by `scripts/build-agc-tools.sh`.

## Live iteration ledger

1. Starting the responder after ENGINE ON missed the pre-ignition throttle
   burst. ATT HOLD alone remained in MM63.
2. Starting it before P63 exposed an unbounded `cmd=-8192`; the truth model
   fell, and the unpatched channel-016 path could not enter MM66.
3. Burst diagnostics confirmed MOUT 4096 and exposed excessive queued ZOUT
   responses. Actuator saturation and DINC credit limiting were added.
4. The corrected run was stopped during the state pad-load, before P63. It
   produced no acceptance result.

## Resume order

1. Run `descent_probe auto`.
2. Confirm engine-off MOUT 4096 leaves position 0, then FLATOUT POUT 4096
   reaches position 4096 without ZOUT flooding.
3. Confirm MM66 after ATT HOLD and the selection ROD click.
4. Send two further ROD− clicks and measure the vertical-velocity change
   within 15 seconds.
5. Read FAILREG and the navigation display; calibrate
   `THRUST_N_PER_PULSE` and RODSCALE.
6. Freeze `live_spike_p66.rs`, update channel-map/navigation documentation,
   and run regression tests.

Still open: MM66 live proof, steady-hover pulse-scale calibration, ROD
calibration, alarm verification, ignored live integration test, and final
Task 7 documentation.
