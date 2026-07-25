# EAGLE Wave 1 Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every finding from the 2026-07-25 project review: make the
Wave 1 live acceptance actually green (or the docs actually honest), fix the
dead client wiring in `--scenario` mode, make touchdown physics
surface-relative, and put lint/CI guardrails around the fast test suite.

**Architecture:** No new crates. Small, ordered changes to the existing
`eagle-runtime` plumbing (server → headless channel wiring), `eagle-dynamics`
(surface co-rotation helper), and the acceptance test. Hygiene and formatting
land FIRST so every later diff is clean. The live re-flight is the LAST task
because every earlier task changes what it measures.

**Tech Stack:** Rust (tokio in eagle-runtime, std sim thread), serde/toml,
React + TypeScript + vitest (client), GitHub Actions (repo root workflows),
yaAGC 4-byte socket protocol.

## Global Constraints

Copied from the Wave 1 plan and eagle conventions — every task implicitly
includes these:

- `vendor/` is READ-ONLY and git-ignored. Never patch vendor sources.
- All AGC channel numbers and erasable addresses are octal (`0o…` in Rust,
  `0…` in docs). Decimal channel literals are a defect.
- Integration tests run serially: `cargo test -- --ignored --test-threads=1`.
  Live tests keep their existing ports (acceptance = 19904).
- Physics step is RK4, fixed 10 ms, fixed evaluation order. Error models
  seeded, default OFF; acceptance runs are errors-OFF.
- SI units everywhere except at the counter codec boundary.
- Scenario/pad-load values carry provenance comments:
  `historical` / `derived` / `assumed`.
- Fast suite must stay green after every task: `make test`
  (= `cd runtime && cargo test` + `cd client && npm test`).
- Work on a branch `eagle/wave1-review-fixes` cut from `main`. Never stage
  anything outside `eagle/` except the CI workflow file
  (`.github/workflows/eagle.yml`), which the CI task stages explicitly.
- Commit after every green test cycle. Commit messages end with:
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` and
  `Claude-Session: https://claude.ai/code/session_01WeYXpPxWfLXR3DG73gPmKc`
- Do not claim a soft landing in README/CLAUDE.md unless a live acceptance
  run measured it (Task 8 decides the final wording).

## File structure (all under `eagle/` unless noted)

| File | Change |
|---|---|
| `runtime/crates/eagle-sensors/src/errors.rs` | clippy `approx_constant` fix (Task 1) |
| `runtime/crates/eagle-agc-protocol/src/agc_io.rs` | clippy `manual_range_patterns` fix (Task 1) |
| `Makefile` | `lint`, `descent-p66-fast` targets (Tasks 1, 7) |
| `../.github/workflows/eagle.yml` (repo root) | new CI workflow (Task 2) |
| `runtime/apps/eagle-runtime/src/headless.rs` | dedupe via `agc_packet_to_simin`; client channels; `Summary::note`; error cleanup; alarms (Tasks 3, 4, 6) |
| `runtime/apps/eagle-runtime/src/main.rs` | stale comment; rod-click channel plumbing (Tasks 3, 4) |
| `runtime/apps/eagle-runtime/src/server.rs` | `route_client_msg` + `AppState.rod_click_tx` (Task 4) |
| `runtime/apps/eagle-runtime/src/scenario_mode.rs` | pass client channels through (Task 4) |
| `runtime/crates/eagle-dynamics/src/state.rs` | `surface_velocity` (Task 5) |
| `runtime/apps/eagle-runtime/src/scenario.rs` | co-rotating `initial_state` (Task 5) |
| `runtime/apps/eagle-runtime/src/sim.rs` | surface-relative kinematics, `TouchdownReport` + miss distance, `pacing_lost_ms` (Tasks 5, 6) |
| `runtime/apps/eagle-runtime/src/runner.rs` | `enter_p63_with_alarms`, `ScenarioReport`, `tland_offset_cs` wiring (Tasks 6, 7) |
| `runtime/apps/eagle-runtime/tests/live_p66_descent.rs` | updated asserts (Tasks 5, 6) |
| `scenarios/p66-gate.toml`, `p66-gate-imu-bias.toml` | `tland_offset_cs = 36000` (Task 7) |
| `scenarios/p66-gate-fast.toml` | new debug scenario (Task 7) |
| `docs/coordinate-frames.md` | co-rotation note (Task 5) |
| `README.md`, `CLAUDE.md`, Wave-1 plan checkboxes, ledger | truth pass (Task 8) |

---

### Task 1: Hygiene — clippy clean, rustfmt, `make lint`

**Files:**
- Modify: `runtime/crates/eagle-sensors/src/errors.rs:83`
- Modify: `runtime/crates/eagle-agc-protocol/src/agc_io.rs:98`
- Modify: `Makefile`
- Modify: every `.rs` file rustfmt touches (mechanical, separate commit)

**Interfaces:**
- Consumes: nothing.
- Produces: `make lint` — the gate every later task runs. Zero behavioral change.

- [ ] **Step 1: Fix the two clippy findings.**

`runtime/crates/eagle-sensors/src/errors.rs:83` — `3.14` trips
`clippy::approx_constant` (deny-by-default). The value is an arbitrary test
input, not π; change it to a value clippy cannot mistake for a constant:

```rust
let v = V3::<Sm>::new(0.001 * k as f64, -0.02, 3.5);
```

`runtime/crates/eagle-agc-protocol/src/agc_io.rs:98` — OR pattern → range:

```rust
0o174..=0o176 => AgcOutput::CoarseAlign {
```

- [ ] **Step 2: Verify clippy is clean.**

Run: `cd runtime && cargo clippy --workspace --all-targets -- -D warnings`
Expected: exit 0, no warnings. (If new findings surface, fix them in the same
spirit — mechanical only, no behavior change.)

- [ ] **Step 3: Run the fast suite.**

Run: `cd runtime && cargo test`
Expected: all PASS (123 tests at time of writing).

- [ ] **Step 4: Commit the clippy fixes.**

```bash
git add runtime/crates/eagle-sensors/src/errors.rs runtime/crates/eagle-agc-protocol/src/agc_io.rs
git commit -m "chore(runtime): fix clippy approx-constant and range-pattern findings"
```

- [ ] **Step 5: Run rustfmt over the workspace (mechanical commit, no manual edits).**

Run: `cd runtime && cargo fmt --all && cargo fmt --all --check && cargo test`
Expected: check passes, tests PASS.

- [ ] **Step 6: Commit the formatting separately.**

```bash
git add -u runtime
git commit -m "style(runtime): cargo fmt --all"
```

- [ ] **Step 7: Add a `lint` target to `Makefile`.**

```make
.PHONY: vendor agc-tools agc test test-integration dev descent-p66 lint

lint:
	cd runtime && cargo clippy --workspace --all-targets -- -D warnings
	cd runtime && cargo fmt --all --check
	cd client && npm run lint
```

(Client `lint` script already exists: `oxlint`.)

- [ ] **Step 8: Verify and commit.**

Run: `make lint && make test`
Expected: both exit 0.

```bash
git add Makefile
git commit -m "chore(eagle): make lint target (clippy -D warnings, fmt check, oxlint)"
```

---

### Task 2: CI workflow for eagle fast tests

**Files:**
- Create: `.github/workflows/eagle.yml` (REPO ROOT — the one permitted file
  outside `eagle/`; model on the existing `.github/workflows/gto-ts.yml`)

**Interfaces:**
- Consumes: Task 1's `make lint` semantics (inlined as steps — CI does not
  call the Makefile so failures map to named steps).
- Produces: PR/push gate on `eagle/**`. No AGC build in CI (fast tests only).

- [ ] **Step 1: Write the workflow.**

```yaml
# Fast-lane CI for eagle: Rust unit tests + client vitest/build/lint.
# Live AGC integration tests need `make agc` artifacts and are NOT run here.
name: eagle

on:
  push:
    branches: [main]
    paths:
      - "eagle/runtime/**"
      - "eagle/client/**"
      - "eagle/scenarios/**"
      - "eagle/Makefile"
      - ".github/workflows/eagle.yml"
  pull_request:
    paths:
      - "eagle/runtime/**"
      - "eagle/client/**"
      - "eagle/scenarios/**"
      - "eagle/Makefile"
      - ".github/workflows/eagle.yml"

jobs:
  runtime:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: eagle/runtime
    steps:
      - uses: actions/checkout@v4
      - name: Test
        run: cargo test --workspace
      - name: Clippy
        run: cargo clippy --workspace --all-targets -- -D warnings
      - name: Format
        run: cargo fmt --all --check

  client:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: eagle/client
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - name: Install
        run: npm ci
      - name: Lint
        run: npm run lint
      - name: Test
        run: npm test
      - name: Build (tsc + vite)
        run: npm run build
```

- [ ] **Step 2: Sanity-check the workflow locally.**

Run each command the workflow runs, from the same working directories:
`cd runtime && cargo test --workspace && cargo clippy --workspace --all-targets -- -D warnings && cargo fmt --all --check`
then `cd client && npm ci && npm run lint && npm test && npm run build`.
Expected: all exit 0. (`npm ci` re-installs from the lockfile — this also
proves the lockfile is complete.)

- [ ] **Step 3: Commit.**

```bash
git add ../.github/workflows/eagle.yml
git commit -m "ci(eagle): fast-lane workflow (cargo test/clippy/fmt + client lint/test/build)"
```

---

### Task 3: Dedupe packet→SimIn decoding; retire stale main.rs comment

**Files:**
- Modify: `runtime/apps/eagle-runtime/src/headless.rs:76-100` (forwarder task)
- Modify: `runtime/apps/eagle-runtime/src/main.rs:44-47` (comment only)

**Interfaces:**
- Consumes: `sim::agc_packet_to_simin(p: &Packet, dsky: &mut DskyState) -> Vec<SimIn>`
  (exists, currently test-only).
- Produces: `headless.rs` forwarder uses the same decode path as the
  `sim_pipeline.rs` test. No signature changes.

- [ ] **Step 1: Refactor the forwarder loop in `run_headless`.**

Replace the hand-rolled decode+apply block (headless.rs lines 82-94) with:

```rust
Ok(pkt) => {
    if let Some(t) = trace.as_mut() {
        t.log("out", &pkt);
    }
    for ev in crate::sim::agc_packet_to_simin(&pkt, &mut dsky) {
        let dsky_changed = matches!(ev, SimIn::Dsky(_));
        let _ = fwd_in.send(ev);
        if dsky_changed {
            if let Ok(json) = serde_json::to_string(&to_msg(&dsky)) {
                if let Some(l) = &latest {
                    *l.lock().unwrap() = json.clone();
                }
                let _ = telem_tx.send(json);
            }
        }
    }
}
```

Remove the now-unused `decode_output` import and the
`DskyStateSnapshot::from_dsky` call site in this file (the helper builds the
snapshot itself). Semantics are identical: one `SimIn::Agc` per packet, plus
one `SimIn::Dsky` + JSON broadcast when the display changed.

- [ ] **Step 2: Fix the stale comment in `main.rs`.**

The `_keep = dsky_rx` binding IS load-bearing (a `watch::Sender` with zero
receivers errors on send) but the comment still says "Task 14 will consume".
Replace the comment (keep the binding):

```rust
// Kept alive so `dsky_tx.send` below always has a live receiver (watch
// send fails with no receivers). Only the Phase-1 DSKY-only loop below
// uses this channel; scenario mode gets its DSKY watch from `pump`.
let _keep = dsky_rx;
```

- [ ] **Step 3: Verify.**

Run: `cd runtime && cargo test && cargo clippy --workspace --all-targets -- -D warnings`
Expected: all PASS (the `sim_pipeline` test exercises the shared helper; the
live acceptance path now compiles against it too).

- [ ] **Step 4: Commit.**

```bash
git add runtime/apps/eagle-runtime/src/headless.rs runtime/apps/eagle-runtime/src/main.rs
git commit -m "refactor(runtime): headless forwarder reuses agc_packet_to_simin; fix stale dsky_rx comment"
```

---

### Task 4: Scenario-mode client wiring — DSKY keys reach the AGC, ROD buttons reach RODCOUNT

**Files:**
- Modify: `runtime/apps/eagle-runtime/src/server.rs` (AppState + extracted router + tests)
- Modify: `runtime/apps/eagle-runtime/src/main.rs` (channel plumbing)
- Modify: `runtime/apps/eagle-runtime/src/scenario_mode.rs` (Cfg fields)
- Modify: `runtime/apps/eagle-runtime/src/headless.rs` (HeadlessCfg fields, key forwarder, merged ROD loop)
- Modify: `runtime/apps/eagle-runtime/tests/live_p66_descent.rs` (two new `None` fields)

**Interfaces:**
- Consumes: `runner::rod_load(script: &mut DskyScript, clicks: i16) -> Result<()>`;
  `ClientMsg::{Key, Pro, Rod}` from `eagle-schema`;
  `agc_io::rod_click(up: bool) -> (Packet, Packet)`.
- Produces:
  - `AppState` gains `pub rod_click_tx: Option<mpsc::UnboundedSender<i32>>`.
  - `pub fn route_client_msg(msg: ClientMsg, app: &AppState)` in `server.rs`.
  - `HeadlessCfg` gains `pub client_rx: Option<mpsc::UnboundedReceiver<Packet>>`
    and `pub client_rod_rx: Option<mpsc::UnboundedReceiver<i32>>`.
  - `scenario_mode::Cfg` gains `pub client_rx: mpsc::UnboundedReceiver<Packet>`
    and `pub client_rod_rx: mpsc::UnboundedReceiver<i32>`.
  - Click convention: `+1` = one "slow descent" click (+1 ft/s on the sink
    target), `-1` = one "faster descent" click — same signed count
    `rod_load` already takes.

Background (the bug): in `--scenario` mode `main.rs` returns early and nobody
drains `agc_rx`, so every client key press is silently dropped; and
`ClientMsg::Rod` sends ch016 packets that stock yaAGC never turns into an
interrupt (documented no-op). Client input must route into the headless
loop's `cmd_tx`/`rod_load` instead.

- [ ] **Step 1: Write failing tests** in `server.rs` `#[cfg(test)]`:

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use eagle_schema::ClientMsg;
    use tokio::sync::{broadcast, mpsc};

    fn app(rod: Option<mpsc::UnboundedSender<i32>>) -> (AppState, mpsc::UnboundedReceiver<Packet>) {
        let (state_rx, _) = broadcast::channel(8);
        let (agc_tx, agc_rx) = mpsc::unbounded_channel();
        (
            AppState {
                state_rx,
                agc_tx,
                latest: Default::default(),
                rod_click_tx: rod,
            },
            agc_rx,
        )
    }

    #[tokio::test]
    async fn key_routes_to_agc_channel() {
        let (app, mut agc_rx) = app(None);
        route_client_msg(ClientMsg::Key { key: "VERB".into() }, &app);
        assert!(agc_rx.try_recv().is_ok(), "VERB key must produce a packet");
    }

    #[tokio::test]
    async fn rod_routes_to_click_channel_in_scenario_mode() {
        let (rod_tx, mut rod_rx) = mpsc::unbounded_channel();
        let (app, mut agc_rx) = app(Some(rod_tx));
        route_client_msg(ClientMsg::Rod { up: false }, &app);
        route_client_msg(ClientMsg::Rod { up: true }, &app);
        assert_eq!(rod_rx.recv().await, Some(-1));
        assert_eq!(rod_rx.recv().await, Some(1));
        assert!(agc_rx.try_recv().is_err(), "no ch016 packets in scenario mode");
    }

    #[tokio::test(start_paused = true)]
    async fn rod_falls_back_to_ch016_press_release_in_dsky_mode() {
        let (app, mut agc_rx) = app(None);
        route_client_msg(ClientMsg::Rod { up: true }, &app);
        let press = agc_rx.recv().await.unwrap();
        assert_eq!((press.channel, press.data), (0o16, 1 << 5));
        tokio::time::sleep(std::time::Duration::from_millis(150)).await;
        let release = agc_rx.recv().await.unwrap();
        assert_eq!((release.channel, release.data), (0o16, 0));
    }
}
```

(Adjust the `Packet` field access to the real struct — `packet.rs` exposes
`channel`/`data`; the live test file already matches on `p.channel`.)

- [ ] **Step 2: Run, verify FAIL.**

Run: `cd runtime && cargo test -p eagle-runtime server`
Expected: compile error — `rod_click_tx` field and `route_client_msg` missing.

- [ ] **Step 3: Implement `server.rs`.**

Add the field:

```rust
#[derive(Clone)]
pub struct AppState {
    pub state_rx: broadcast::Sender<String>, // serialized ServerMsg JSON
    pub agc_tx: mpsc::UnboundedSender<Packet>,
    pub latest: std::sync::Arc<std::sync::Mutex<String>>,
    /// Scenario mode: ROD clicks route here (+1 = slow descent 1 ft/s) and
    /// become `runner::rod_load` RODCOUNT loads. `None` in Phase-1
    /// DSKY-only mode → hardware-faithful ch016 discrete (a documented
    /// no-op on stock yaAGC — see docs/agc-channel-map.md "Rod Switch
    /// Click").
    pub rod_click_tx: Option<mpsc::UnboundedSender<i32>>,
}
```

Extract the routing (the body of the current inline match) into:

```rust
/// Route one parsed client message. Pure channel-pushes so it is unit
/// testable; the ws loop just parses JSON and delegates here.
pub fn route_client_msg(msg: ClientMsg, app: &AppState) {
    match msg {
        ClientMsg::Key { key } => {
            if let Some(k) = DskyKey::from_name(&key) {
                let _ = app.agc_tx.send(k.packet());
            }
        }
        ClientMsg::Pro { pressed } => {
            for p in pro_key_packets(pressed) {
                let _ = app.agc_tx.send(p);
            }
        }
        ClientMsg::Rod { up } => match &app.rod_click_tx {
            Some(tx) => {
                let _ = tx.send(if up { 1 } else { -1 });
            }
            None => {
                // Phase-1: press now, release after 100 ms (ch016).
                let (press, release) = eagle_agc_protocol::agc_io::rod_click(up);
                let _ = app.agc_tx.send(press);
                let tx = app.agc_tx.clone();
                tokio::spawn(async move {
                    tokio::time::sleep(std::time::Duration::from_millis(100)).await;
                    let _ = tx.send(release);
                });
            }
        },
    }
}
```

In `client_loop`, replace the inline match with
`route_client_msg(msg, &app);`.

- [ ] **Step 4: Run, verify the new tests PASS.**

Run: `cd runtime && cargo test -p eagle-runtime server`
Expected: 3 new tests PASS. (Other targets won't compile yet — `AppState`
literal in `main.rs` is missing the field; that is Step 5.)

- [ ] **Step 5: Plumb the channels through `main.rs` → `scenario_mode` → `run_headless`.**

`main.rs` (around the existing `AppState` construction):

```rust
let (rod_click_tx, rod_click_rx) = mpsc::unbounded_channel::<i32>();
let app = AppState {
    state_rx: state_tx.clone(),
    agc_tx: agc_tx.clone(),
    latest: latest.clone(),
    rod_click_tx: args.scenario.is_some().then_some(rod_click_tx),
};
```

and in the scenario branch, hand over the receivers (this is the fix for the
silently-dropped keys — `agc_rx` moves instead of leaking):

```rust
if let Some(path) = args.scenario.clone() {
    return scenario_mode::run(scenario_mode::Cfg {
        session,
        scenario: path,
        root: args.root.clone(),
        state_tx: state_tx.clone(),
        latest: latest.clone(),
        trace_out: args.trace_out.clone(),
        client_rx: agc_rx,
        client_rod_rx: rod_click_rx,
    })
    .await;
}
```

(The Phase-1 loop below keeps using `agc_rx` — in that branch the scenario
arm didn't move it. `rod_click_rx` is unused in Phase-1; bind it as
`let _ = rod_click_rx;` before the loop, with a one-line comment.)

`scenario_mode.rs`: add the two fields to `Cfg` and pass them into
`HeadlessCfg`:

```rust
pub client_rx: tokio::sync::mpsc::UnboundedReceiver<Packet>,
pub client_rod_rx: tokio::sync::mpsc::UnboundedReceiver<i32>,
...
client_rx: Some(cfg.client_rx),
client_rod_rx: Some(cfg.client_rod_rx),
```

`headless.rs`: add to `HeadlessCfg`:

```rust
/// Client → AGC packets from the WebSocket server (scenario mode);
/// forwarded into the pump so web DSKY keys work mid-run.
pub client_rx: Option<tokio::sync::mpsc::UnboundedReceiver<Packet>>,
/// Client ROD clicks (+1 = slow descent); merged with the sim's
/// scheduled clicks into the same RODCOUNT loader.
pub client_rod_rx: Option<tokio::sync::mpsc::UnboundedReceiver<i32>>,
```

In `run_headless`, after `pump`:

```rust
if let Some(mut rx) = cfg.client_rx {
    let tx = cmd_tx.clone();
    tokio::spawn(async move {
        while let Some(pkt) = rx.recv().await {
            if tx.send(pkt).is_err() {
                break;
            }
        }
    });
}
```

Replace the ROD delivery loop (`while let Some(n) = rod_rx.recv().await …`)
with a merged loop. Termination stays keyed to the SIM's sender dropping
(sim thread exit), never to the client channel:

```rust
// Deliver ROD clicks from both sources through the one DskyScript.
// Exit when the SIM's rod channel closes (sim thread exited on
// touchdown + 2 s); the client channel closing just stops that source.
let mut client_rod_rx = cfg.client_rod_rx;
loop {
    let n = tokio::select! {
        n = rod_rx.recv() => match n {
            Some(n) => n,
            None => break,
        },
        n = async {
            match client_rod_rx.as_mut() {
                Some(rx) => rx.recv().await,
                None => std::future::pending().await,
            }
        } => match n {
            Some(n) => n,
            None => {
                client_rod_rx = None;
                continue;
            }
        },
    };
    if let Err(e) = runner::rod_load(&mut script, n as i16).await {
        eprintln!("headless: ROD load failed: {e:#}");
    }
}
```

Update the two `HeadlessCfg` literals in
`tests/live_p66_descent.rs` with `client_rx: None, client_rod_rx: None`.

- [ ] **Step 6: Run the full fast suite + lint.**

Run: `make test && make lint`
Expected: all green.

- [ ] **Step 7: Commit.**

```bash
git add runtime/apps/eagle-runtime/src/server.rs runtime/apps/eagle-runtime/src/main.rs \
        runtime/apps/eagle-runtime/src/scenario_mode.rs runtime/apps/eagle-runtime/src/headless.rs \
        runtime/apps/eagle-runtime/tests/live_p66_descent.rs
git commit -m "fix(runtime): scenario mode routes client DSKY keys and ROD clicks (RODCOUNT, not ch016)"
```

---

### Task 5: Physics — co-rotating hover gate, surface-relative touchdown, miss distance

**Files:**
- Modify: `runtime/crates/eagle-dynamics/src/state.rs` (+ tests)
- Modify: `runtime/apps/eagle-runtime/src/scenario.rs:120-136` (+ test)
- Modify: `runtime/apps/eagle-runtime/src/sim.rs` (kinematics, `TouchdownReport`, + tests)
- Modify: `runtime/apps/eagle-runtime/src/headless.rs` (`touchdown_class`)
- Modify: `runtime/apps/eagle-runtime/tests/live_p66_descent.rs` (struct access)
- Modify: `docs/coordinate-frames.md` (note)

**Interfaces:**
- Consumes: `constants::OMEGA_MOON`, `frames::{mci_to_mcmf, Mcmf}`,
  `Scenario::site_unit_mcmf()`.
- Produces:
  - `eagle_dynamics::state::surface_velocity(pos: V3<Mci>) -> V3<Mci>`.
  - `pub struct TouchdownReport { pub class: Touchdown, pub v_vert_ms: f64, pub v_horiz_ms: f64, pub tilt_deg: f64, pub miss_m: f64 }` in `sim.rs`.
  - `SimResult.touchdown: Option<TouchdownReport>` (replaces the 4-tuple).
  - `headless::touchdown_class` returns `r.sim.touchdown.map(|t| t.class)`.

Background (the bug): the AGC pad-load state carries the eastward
co-rotation term ω·r ≈ 4.67 m/s (see `padload.rs:761-769`), but the truth
gate starts with zero MCI horizontal velocity — physically that is a vehicle
the SURFACE is sliding under at 4.67 m/s, yet the touchdown classifier
measures horizontal speed in MCI and reports ≈ 0. A hover gate means
surface-stationary: MCI velocity must be ω×r, and the classifier must
measure surface-relative velocity. Nobody measures distance-to-site at all.

- [ ] **Step 1: Write failing tests.**

`state.rs` tests:

```rust
#[test]
fn surface_velocity_is_eastward_and_horizontal() {
    use crate::constants::OMEGA_MOON;
    let r = R_SITE;
    let v = surface_velocity(V3::<Mci>::new(r, 0.0, 0.0));
    assert!(v.x == 0.0 && v.z == 0.0);
    assert!((v.y - OMEGA_MOON * r).abs() < 1e-12, "eastward ω·r at the equator");
    // Perpendicular to the radial everywhere.
    let p = V3::<Mci>::new(0.3 * r, -0.5 * r, 0.8 * r);
    assert!(surface_velocity(p).dot(p).abs() < 1e-6);
}
```

`scenario.rs` — extend `initial_state_geometry`:

```rust
// Hover gate = stationary relative to the surface (vz_ms = 0 here):
// inertial velocity must be exactly the co-rotation term.
let v_rel = st.vel - eagle_dynamics::state::surface_velocity(st.pos);
assert!(v_rel.norm() < 1e-9, "gate not co-rotating: {v_rel:?}");
```

`sim.rs` tests:

```rust
#[test]
fn hover_gate_is_surface_stationary() {
    let sc = scenario();
    let core = SimCore::new(&sc, 0.0);
    let (vv, vh, _tilt) = core.landing_kinematics();
    assert!(vv < 1e-9, "vertical: {vv}");
    assert!(vh < 1e-9, "surface-relative horizontal must be ~0: {vh}");
}

#[test]
fn miss_distance_zero_above_site_and_tracks_offset() {
    use eagle_dynamics::frames::{mci_to_mcmf, Mcmf, Rot};
    let sc = scenario();
    let mut core = SimCore::new(&sc, 0.0);
    assert!(core.miss_distance_m() < 1.0, "start is directly above the site");
    // Rotate the truth 1 mrad about an axis ⊥ site: expected arc = r·1e-3.
    let site = sc.site_unit_mcmf();
    let axis = site.cross(V3::<Mcmf>::new(0.0, 0.0, 1.0)).unit();
    let rot: Rot<Mcmf, Mcmf> = Rot::from_axis_angle(axis, 1e-3);
    let pos_mcmf = rot.apply(site).scale(sc.site.radius_m);
    core.st.pos = mci_to_mcmf(core.st.t).inverse().apply(pos_mcmf);
    let m = core.miss_distance_m();
    assert!((m - sc.site.radius_m * 1e-3).abs() < 1.0, "miss {m}");
}
```

(If `core.st` is not visible to the test, the existing tests already assign
`core.st.pos` — same module, private access is fine.)

- [ ] **Step 2: Run, verify FAIL** — `cd runtime && cargo test -p eagle-dynamics state; cargo test -p eagle-runtime sim scenario` → missing `surface_velocity` / `miss_distance_m`, and `hover_gate_is_surface_stationary` fails on the un-co-rotated gate.

- [ ] **Step 3: Implement.**

`state.rs` (next to `gravity`):

```rust
/// Inertial (MCI) velocity of the co-rotating lunar surface point at
/// `pos`: ω ẑ × pos (MCI z = lunar pole, docs/coordinate-frames.md). A
/// vehicle hovering — stationary relative to the ground — carries exactly
/// this velocity.
pub fn surface_velocity(pos: V3<Mci>) -> V3<Mci> {
    let w = crate::constants::OMEGA_MOON;
    V3::new(-w * pos.y, w * pos.x, 0.0)
}
```

`scenario.rs::initial_state` — one line:

```rust
let vel = up_mci.scale(self.gate.vz_ms) + eagle_dynamics::state::surface_velocity(pos);
```

`sim.rs`:

1. Add field `site_unit_mcmf: V3<Mcmf>` to `SimCore`, set from
   `sc.site_unit_mcmf()` in `new`. Import
   `eagle_dynamics::frames::{mci_to_mcmf, Mcmf}` and
   `eagle_dynamics::state::surface_velocity`.
2. Make kinematics surface-relative:

```rust
/// Surface-relative velocity split: (signed vertical, horizontal speed).
fn rel_velocity(&self) -> (f64, f64) {
    let up = self.st.pos.unit();
    let v_rel = self.st.vel - surface_velocity(self.st.pos);
    let vz = v_rel.dot(up);
    (vz, (v_rel - up.scale(vz)).norm())
}

/// (|vertical speed|, horizontal speed, tilt°), surface-relative.
fn landing_kinematics(&self) -> (f64, f64, f64) {
    let (vz, v_h) = self.rel_velocity();
    let up = self.st.pos.unit();
    let body_x = self.st.att.apply(V3::<Body>::new(1.0, 0.0, 0.0));
    let tilt = body_x.dot(up).clamp(-1.0, 1.0).acos().to_degrees();
    (vz.abs(), v_h, tilt)
}

/// Great-circle distance from the scenario landing site, m.
fn miss_distance_m(&self) -> f64 {
    let pos_mcmf = mci_to_mcmf(self.st.t).apply(self.st.pos);
    let c = pos_mcmf.unit().dot(self.site_unit_mcmf).clamp(-1.0, 1.0);
    self.radius_m * c.acos()
}
```

3. `telemetry()` uses `rel_velocity` for `vz_ms`/`v_horiz_ms` (signed `vz`
   as today; drop the ad-hoc `up`/`vz` recompute).
4. Replace the result tuple:

```rust
/// Touchdown summary measured at the latch instant, surface-relative.
#[derive(Debug, Clone, Copy)]
pub struct TouchdownReport {
    pub class: Touchdown,
    pub v_vert_ms: f64,
    pub v_horiz_ms: f64,
    pub tilt_deg: f64,
    /// Great-circle distance from the scenario landing site, m.
    pub miss_m: f64,
}

#[derive(Debug, Default, Clone)]
pub struct SimResult {
    pub touchdown: Option<TouchdownReport>,
}
```

and in `spawn_sim`:

```rust
if let Some(td) = out.touchdown {
    let (vv, vh, tilt) = core.landing_kinematics();
    result.touchdown = Some(TouchdownReport {
        class: td,
        v_vert_ms: vv,
        v_horiz_ms: vh,
        tilt_deg: tilt,
        miss_m: core.miss_distance_m(),
    });
    touchdown_at = Some(std::time::Instant::now());
}
```

`headless.rs`: `touchdown_class` becomes
`r.sim.touchdown.map(|t| t.class)`.

`tests/live_p66_descent.rs`: replace the destructuring with struct access:

```rust
let td = result.sim.touchdown.expect("no touchdown");
...
assert_eq!(td.class, Touchdown::Nominal, "not a nominal landing: {:?}", td.class);
assert!(td.v_vert_ms < acceptance.v_vert_max, "v_vert {} >= {}", td.v_vert_ms, acceptance.v_vert_max);
assert!(td.v_horiz_ms < acceptance.v_horiz_max, "v_horiz {} >= {}", td.v_horiz_ms, acceptance.v_horiz_max);
assert!(td.tilt_deg < acceptance.tilt_max_deg, "tilt {} >= {}", td.tilt_deg, acceptance.tilt_max_deg);
eprintln!("[accept] miss distance {:.1} m", td.miss_m);
```

Miss distance is REPORTED, not gated, in this wave — one measured live run
first, then a threshold with provenance (note this in a comment).

- [ ] **Step 4: Run, verify PASS.**

Run: `cd runtime && cargo test && cd ../client && npm test`
Expected: all PASS, including the untouched sim tests
(`frozen_until_engine_on_then_falls`, `closed_hover_with_thrust_pulses`,
`rod_schedule…`, `touchdown_terminates…` — all measure vertical components,
which co-rotation does not change; if `touchdown_terminates…` classification
shifts due to the ~1 mm/s horizontal residual from re-pinning `pos`, fix the
test by zeroing `core.st.vel` horizontally, not the model).

- [ ] **Step 5: Document.**

Append to `docs/coordinate-frames.md`:

```markdown
## Truth co-rotation (Wave 1 review fix, 2026-07-25)

The scenario gate is a hover: stationary relative to the SURFACE. The truth
initial MCI velocity is therefore `vz·up + ω ẑ × r` (state::surface_velocity),
matching the ω·r term the AGC pad-load state already carries
(padload.rs generate_state). Touchdown kinematics (v_vert, v_horiz) and the
telemetry vz/v_horiz are measured surface-relative; miss distance is the
great-circle arc from the scenario site, computed in MCMF at touchdown time.
```

- [ ] **Step 6: Commit.**

```bash
git add runtime/crates/eagle-dynamics/src/state.rs runtime/apps/eagle-runtime/src/scenario.rs \
        runtime/apps/eagle-runtime/src/sim.rs runtime/apps/eagle-runtime/src/headless.rs \
        runtime/apps/eagle-runtime/tests/live_p66_descent.rs docs/coordinate-frames.md
git commit -m "feat(dynamics): co-rotating hover gate, surface-relative touchdown, miss distance"
```

---

### Task 6: Acceptance hardening — observed alarms, PROG-lamp watch, pacing visibility

**Files:**
- Modify: `runtime/apps/eagle-runtime/src/runner.rs` (`ScenarioReport`, `enter_p63_with_alarms`)
- Modify: `runtime/apps/eagle-runtime/src/headless.rs` (`Summary::note` + tests, alarms, error cleanup)
- Modify: `runtime/apps/eagle-runtime/src/sim.rs` (`pacing_lost_ms`)
- Modify: `runtime/apps/eagle-runtime/tests/live_p66_descent.rs` (direct asserts)

**Interfaces:**
- Consumes: `DskyScript::alarm_codes() -> Result<[u16; 3]>` (exists);
  `ServerMsg::{Telemetry, DskyState}` (lamps map key `"prog"`).
- Produces:
  - `pub struct ScenarioReport { pub alarms: Vec<u16> }` in `runner.rs`;
    `run_scenario` returns `Result<ScenarioReport>`.
  - `pub async fn enter_p63_with_alarms(script) -> Result<Vec<u16>>`;
    `enter_p63` stays as a thin `.map(|_| ())` wrapper (descent_probe and
    the two live spikes keep compiling unchanged).
  - `HeadlessResult` gains `pub alarms: Vec<u16>` and
    `pub prog_lamp_frames: u64`.
  - `SimResult` gains `pub pacing_lost_ms: f64`.

Background: the acceptance test currently asserts
`SPIKE_A_ALARM_WHITELIST.is_empty()` — a statement about a constant, not
about the run. And after MM66 nobody watches the PROG lamp at all. Finally,
`spawn_sim`'s `next = now` reset silently discards lost pacing time, which
then shows up as unexplained `drift_ms` (the 500 ms gate is 0.08 % of a
~600 s run — a flake source on WSL2).

- [ ] **Step 1: Write failing tests** — `Summary::note` in `headless.rs`
  (new `#[cfg(test)]` module; build msgs via `eagle_schema` types):

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use eagle_schema::{DskyStateMsg, ServerMsg, TelemetryMsg, SCHEMA_VERSION};

    fn telem(t_s: f64, mm: &str, frozen: bool) -> ServerMsg {
        ServerMsg::Telemetry(TelemetryMsg {
            schema_version: SCHEMA_VERSION,
            t_s,
            frozen,
            alt_m: 100.0, vz_ms: -1.0, v_horiz_ms: 0.0, tilt_deg: 0.0,
            mass_kg: 9000.0, fuel_dps_kg: 1000.0, fuel_rcs_kg: 100.0,
            thrust_n: 0.0, throttle_cmd_pulses: 0, jets: 0,
            mm: mm.into(),
            agc_alt_m: None, agc_hdot_ms: None,
            nav_err_alt_m: None, nav_err_hdot_ms: None,
            drift_ms: 0.0, downlink_wps: 50.0, ingest_drops: 0,
            touchdown: None,
        })
    }

    fn dsky(prog_lamp: bool) -> ServerMsg {
        let mut m = DskyStateMsg::default();
        m.lamps.insert("prog".into(), prog_lamp);
        ServerMsg::DskyState(m)
    }

    #[test]
    fn summary_tracks_mm_engine_on_and_prog_lamp() {
        let mut s = Summary::default();
        s.note(&telem(1.0, "63", true));
        s.note(&telem(2.0, "63", true));
        s.note(&dsky(true)); // pre-engine-on lamp: enter_p63 handles it
        assert_eq!(s.prog_lamp_frames, 0);
        s.note(&telem(3.0, "63", false)); // engine on
        assert_eq!(s.engine_on_t, Some(3.0));
        s.note(&telem(4.0, "66", false));
        assert_eq!(s.mm_sequence, vec!["63".to_string(), "66".to_string()]);
        s.note(&dsky(true)); // descent-phase PROG lamp must be counted
        s.note(&dsky(false));
        assert_eq!(s.prog_lamp_frames, 1);
    }
}
```

- [ ] **Step 2: Run, verify FAIL** — `cargo test -p eagle-runtime headless`
  → `note`/`prog_lamp_frames` missing.

- [ ] **Step 3: Implement.**

`headless.rs` — move the collector's per-frame logic into a method (the
async task keeps only recv + `EAGLE_TELEM_OUT` dump + lock):

```rust
impl Summary {
    fn note(&mut self, msg: &eagle_schema::ServerMsg) {
        match msg {
            eagle_schema::ServerMsg::Telemetry(t) => {
                if t.mm != self.last_mm && !t.mm.is_empty() {
                    self.mm_sequence.push(t.mm.clone());
                    self.last_mm = t.mm.clone();
                }
                self.drift_ms = t.drift_ms;
                if !t.frozen {
                    if self.engine_on_t.is_none() {
                        self.engine_on_t = Some(t.t_s);
                    }
                    if t.touchdown.is_none() {
                        self.downlink_samples.push(t.downlink_wps);
                    } else if self.touchdown_t.is_none() {
                        self.touchdown_t = Some(t.t_s);
                    }
                }
            }
            eagle_schema::ServerMsg::DskyState(d) => {
                // enter_p63 handles pre-ignition alarms (bails on
                // non-whitelisted). Post-engine-on, nobody else watches
                // the lamp — count lit frames here.
                if self.engine_on_t.is_some()
                    && d.lamps.get("prog").copied().unwrap_or(false)
                {
                    self.prog_lamp_frames += 1;
                }
            }
        }
    }
}
```

Collector body: `if let Ok(msg) = serde_json::from_str::<ServerMsg>(&json) { … sum.lock().unwrap().note(&msg); }` (keep the telemetry-only dump gating by matching on the parsed msg).

`runner.rs`:

```rust
/// What the choreography observed, for the acceptance run to assert on.
#[derive(Debug, Default, Clone)]
pub struct ScenarioReport {
    /// Whitelisted FAILREG codes acknowledged during P63 entry (a
    /// non-whitelisted code aborts instead of landing here). Empty in a
    /// clean run — the wave locked the whitelists to the empty set.
    pub alarms: Vec<u16>,
}
```

Rename the body of `enter_p63` to `enter_p63_with_alarms`, accumulating:

```rust
pub async fn enter_p63_with_alarms(script: &mut DskyScript) -> Result<Vec<u16>> {
    let mut acknowledged: Vec<u16> = Vec::new();
    // … existing body; in the whitelisted-alarm branch, before RSET:
    acknowledged.extend(codes.iter().copied().filter(|c| *c != 0));
    // … every `return Ok(())`/final Ok becomes `Ok(acknowledged)`.
}

/// Back-compat wrapper (descent_probe, live spikes).
pub async fn enter_p63(script: &mut DskyScript) -> Result<()> {
    enter_p63_with_alarms(script).await.map(|_| ())
}
```

`run_scenario` → `Result<ScenarioReport>`: capture
`let alarms = enter_p63_with_alarms(script).await.context("P63 dialog")?;`
and end with `Ok(ScenarioReport { alarms })`.

`headless.rs` — `HeadlessResult` gains `pub alarms: Vec<u16>` and
`pub prog_lamp_frames: u64`; wrap the choreography call with cleanup on
failure (today it early-returns and leaves the sim thread running):

```rust
let report = match runner::run_scenario(
    &mut script, &cfg.scenario, &cfg.symtab, &cfg.manifest, &cmd_tx, &mut responder,
)
.await
.context("scenario choreography")
{
    Ok(r) => r,
    Err(e) => {
        let _ = sim.stop.send(());
        drop(sim_in_tx);
        let _ = tokio::task::spawn_blocking(move || sim.join.join()).await;
        collector.abort();
        return Err(e);
    }
};
```

and populate the result: `alarms: report.alarms`,
`prog_lamp_frames: s.prog_lamp_frames`.

`sim.rs` — pacing visibility. `SimResult` gains
`pub pacing_lost_ms: f64`; in the pacing branch:

```rust
if next > now {
    std::thread::sleep(next - now);
} else {
    // Falling behind: reset the cadence but RECORD the discarded time —
    // it is the sim-side component of telemetry drift_ms.
    result.pacing_lost_ms += (now - next).as_secs_f64() * 1000.0;
    next = now;
}
```

`tests/live_p66_descent.rs` — replace the whitelist meta-assert (and its
now-unused import) with direct observations, and de-flake drift:

```rust
assert!(result.alarms.is_empty(), "alarms acknowledged during entry: {:?}", result.alarms);
assert_eq!(result.prog_lamp_frames, 0, "PROG alarm lamp lit during descent");

// Drift: AGC-clock proxy vs sim clock. 1 s over a ~600 s run; the sim-side
// pacing loss is printed alongside so an overrun is attributable.
eprintln!("[accept] pacing lost {:.0} ms", result.sim.pacing_lost_ms);
assert!(result.drift_ms.abs() < 1000.0, "drift {} ms", result.drift_ms);
```

- [ ] **Step 4: Run, verify PASS** — `make test && make lint`
  (the `Summary::note` tests pass; live spikes/descent_probe still compile
  against the `enter_p63` wrapper).

- [ ] **Step 5: Commit.**

```bash
git add runtime/apps/eagle-runtime/src/runner.rs runtime/apps/eagle-runtime/src/headless.rs \
        runtime/apps/eagle-runtime/src/sim.rs runtime/apps/eagle-runtime/tests/live_p66_descent.rs
git commit -m "feat(runtime): acceptance asserts observed alarms and PROG lamp; pacing-loss visibility"
```

---

### Task 7: Fast-iteration scenario — wire `tland_offset_cs`, add `p66-gate-fast`

**Files:**
- Modify: `runtime/apps/eagle-runtime/src/runner.rs:929` (one line)
- Modify: `scenarios/p66-gate.toml`, `scenarios/p66-gate-imu-bias.toml`
- Create: `scenarios/p66-gate-fast.toml`
- Modify: `runtime/apps/eagle-runtime/src/scenario.rs` (one test)
- Modify: `Makefile`

**Interfaces:**
- Consumes: `Scenario.agc.tland_offset_cs: i64` (exists, currently DEAD —
  `run_scenario` hardcodes `burn_lead_cs: 36_000.0`);
  `StateCfg.burn_lead_cs: f64`.
- Produces: `run_scenario` honors the scenario's TIG lead; a committed
  debug scenario with a ~2 min shorter run.

Background (review finding): the TOML says `tland_offset_cs = 12000  # TIG
target ≈ boot+120 s; spike-A calibrated` but `run_scenario` ignores it and
hardcodes 36 000 cs (360 s) — the field is dead and its comment is wrong.
Live-debug iterations currently cost ~10 min each, most of it TIG countdown.

- [ ] **Step 1: Write the failing test** in `scenario.rs` tests:

```rust
#[test]
fn loads_fast_debug_scenario() {
    let s = Scenario::load(&repo().join("scenarios/p66-gate-fast.toml")).unwrap();
    assert_eq!(s.name, "p66-gate-fast");
    assert!(
        s.agc.tland_offset_cs < 36_000,
        "fast scenario must shorten the TIG lead"
    );
}
```

- [ ] **Step 2: Run, verify FAIL** — file does not exist.

- [ ] **Step 3: Implement.**

`runner.rs` `run_scenario` — honor the field:

```rust
        word: generate_state(&StateCfg {
            epoch_now_cs: epoch_cs,
            burn_lead_cs: sc.agc.tland_offset_cs as f64,
            ..StateCfg::default()
        }),
```

`scenarios/p66-gate.toml` — preserve current behavior EXACTLY and fix the
lying comment:

```toml
tland_offset_cs = 36000            # derived: matches the burn lead run_scenario previously hardcoded (TIG ≈ clock-read + 360 s; ENGINE ON ~350 s after boot)
```

Apply the same value+comment in `scenarios/p66-gate-imu-bias.toml` (check
its current value first; it must also keep flying the acceptance timing).

`scenarios/p66-gate-fast.toml` — byte-for-byte copy of `p66-gate.toml`
except:

```toml
schema = 1
name = "p66-gate-fast"
# Debug-iteration variant of p66-gate: shorter TIG lead only. NOT the
# acceptance gate — use p66-gate.toml for acceptance runs.
```

and

```toml
tland_offset_cs = 24000            # assumed: StateCfg default burn lead; if too tight BURNBABY slips TIG (+29.9 s, BURN,_BABY,_BURN:64) — debug only
```

`Makefile`:

```make
# Debug iteration: same closed loop, ~2 min shorter TIG lead.
descent-p66-fast: agc
	cd runtime && cargo run -p eagle-runtime -- \
	  --yaagc ../build/agc/yaAGC --core ../build/agc/Luminary099.bin \
	  --scenario ../scenarios/p66-gate-fast.toml --root ..
```

(add `descent-p66-fast` to `.PHONY`.)

- [ ] **Step 4: Run, verify PASS** — `make test && make lint`.

- [ ] **Step 5: Commit.**

```bash
git add runtime/apps/eagle-runtime/src/runner.rs runtime/apps/eagle-runtime/src/scenario.rs \
        scenarios/ Makefile
git commit -m "feat(runtime): honor scenario tland_offset_cs; p66-gate-fast debug scenario"
```

---

### Task 8: Live re-flight, ENGR manual check, docs truth pass

**Files:**
- Modify: `README.md`, `CLAUDE.md`
- Modify: `docs/superpowers/plans/2026-07-23-phase2-wave1-p66-closed-loop.md` (checkboxes)
- Create/append: `docs/superpowers/notes/` ledger entry for the re-flight

**Interfaces:**
- Consumes: everything above; `make agc` artifacts;
  `EAGLE_ATT_DEBUG=<path>` (attitude sign-chain trace),
  `EAGLE_TELEM_OUT=<path>` (per-frame telemetry dump).
- Produces: a recorded, honest Wave 1 status. This task decides the final
  wording of every "soft touchdown" claim.

This is live work; each acceptance run is ~10 min wall time (ENGINE ON at
~350 s is real-time TIG countdown). Prerequisite: `make agc` artifacts
present (they are, under `build/agc/`).

- [ ] **Step 1: Re-fly the acceptance with instrumentation.**

```bash
cd runtime
EAGLE_ATT_DEBUG=../build/traces/att-debug.log \
EAGLE_TELEM_OUT=../build/traces/telem-accept.jsonl \
  cargo test -p eagle-runtime --test live_p66_descent -- --ignored --test-threads=1 p66_soft_landing_closed_loop
```

Record: pass/fail, `[accept]` summary lines (MM sequence, touchdown class,
v_vert/v_horiz/tilt, miss distance, descent s, drift, pacing lost).

- [ ] **Step 2 (if GREEN): confirm once more.**

Re-run the same command. Two consecutive passes = accept. Then write the
ledger note (`docs/superpowers/notes/2026-07-25-wave1-reflight.md`) with
both runs' numbers.

- [ ] **Step 2' (if RED): bounded diagnosis loop.**

Iterate with `make descent-p66-fast` + `EAGLE_ATT_DEBUG`, reading the sign
chain (gimbals we send → jets the AGC fires → torque we produce → omega
response; negative feedback = jets oppose omega error). Suspect list, in
order (all on the attitude-critical path, all `assumed`):
1. Jet min-impulse quantization: our 10 ms tick stretches sub-tick T6RUPT
   pulses (~14 ms minimum) to a full tick — check the duty cycle of jet
   bits in the trace; if single-tick pulses dominate, implement per-tick
   pulse-width accounting (scale each jet's force/torque by its fraction
   of the tick, using the latest two jet words).
2. `inertia_kgm2 = [12000, 13500, 13000]` and `RCS_LEVER_M = 1.68`
   magnitudes (torque-to-inertia ratio sets the DAP's plant gain).
3. Trim-gimbal drive signs (ch012 bits 9-12 → `phase2_trim` directions)
   under thrust: DPS mount torque must also be negative feedback.

STOP RULE: after 3 failed fix attempts, stop, write the ledger note with
each attempt + data, and leave the docs stating the true status.

- [ ] **Step 3: ENGR tab manual check (closes Wave-1 Task 15 Step 6).**

Run `make descent-p66-fast` in one terminal, `make dev-client` in another,
open `http://localhost:5173` → ENGR. Verify: both tabs render; strip
charts scroll during descent; clicking `ROD −1 ft/s` twice visibly steepens
the descent-rate trace (the Task 4 wiring made these real). Note the result
in the ledger entry.

- [ ] **Step 4: Docs truth pass.**

- `README.md` + `CLAUDE.md`: keep the closed-loop claims only if Step 1/2
  measured them; otherwise state the actual status ("flies the full loop
  to touchdown; soft-landing acceptance not yet green — see ledger").
  Either way, describe the ROD buttons accurately (they now issue RODCOUNT
  loads in scenario mode) and mention `make descent-p66-fast` and
  `make lint`.
- Wave-1 plan checkboxes: mark Tasks 1-6 steps `[x]` (implemented and
  committed long ago), and Task 16 steps per the measured outcome — never
  check an unmet acceptance step.

- [ ] **Step 5: Commit.**

```bash
git add README.md CLAUDE.md docs/
git commit -m "docs(eagle): wave 1 re-flight results; align claims with measured status"
```

---

## Self-review

- **Coverage vs review findings:** A (re-flight + docs) → Task 8; B-1/B-2
  (wiring) → Task 4; B-3 (dedupe + stale comment) → Task 3; C-1/C-2
  (co-rotation, surface-relative, miss) → Task 5; C-3 (suspect list) →
  Task 8 Step 2'; D (clippy/fmt/lint/CI/checkboxes/manual check) → Tasks
  1, 2, 8; E (alarm assert, drift flake, cleanup-on-error) → Task 6. The
  dead `tland_offset_cs` found while planning → Task 7.
- **Ordering:** hygiene/fmt first so every later diff is clean; all
  fast-test tasks before the live re-flight so the expensive run measures
  the final code; Task 5 (struct shape) before Task 6 (same files/tests).
- **Type consistency:** `TouchdownReport` fields used in Task 5's test
  edits match its definition; `route_client_msg(msg, &app)` signature
  consistent between Task 4 steps; `enter_p63` wrapper keeps
  descent_probe/live-spike call sites compiling; `HeadlessCfg` gains
  exactly `client_rx`/`client_rod_rx` and both `None`s are added to the
  acceptance test in the same task.
- **Known judgment calls:** miss distance reported-not-gated (one measured
  run before choosing a threshold); drift gate 500→1000 ms with pacing
  loss printed for attribution; client keys forwarded even during
  choreography (user-owned lab; documented).
