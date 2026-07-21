# EAGLE — Roadmap Decomposition and Phase 0–1 Design

**Date:** 2026-07-21
**Status:** Approved (brainstorming session "apollo")
**Parent document:** EAGLE Software Design and Architecture Specification v0.1
(uploaded as `eagle_apollo11_simulator_architecture.md`; treat as the reference
architecture — this document records how the personal-lab build adapts it)

---

## 1. Decisions made in this session

| Topic | Decision |
|---|---|
| Project positioning | Personal lab. Goal: the original `Luminary099` flying a real closed loop. Distribution and commercial art quality are out of scope. |
| 3D client | Web client with React Three Fiber (replaces Unreal Engine 5). WSL2-native workflow; reuses existing R3F experience. |
| Mission runtime | Rust, as in the parent spec (§5.1). Separate headless process, authoritative over all vehicle state. |
| AGC execution | `yaAGC` as a child process over its 4-byte socket protocol (spec §5.2 backend A). Lockstep backend (F5) is **not** built; the `AgcBackend` trait seam is kept so it remains possible. |
| Roadmap style | Risk-first order (AGC integration → headless closed loop → 3D), but every phase ships a small visible web deliverable. |
| Fidelity target | F3 (closed-loop dynamic). F4 claims only where provenance tags justify them. Bit-exact replay (F5) is explicitly abandoned. |

Scope removed relative to the parent spec: VR/HOTAS (M7), commercial art pass
(M4), GPL distribution engineering (§14 — personal use only; provenance/pinning
is kept), AI offline fallback (§5.7).

## 2. Repository layout

Location: `/home/kazumasa/projects/eagle/` (workspace-adjacent standalone
project like `gto`; not a uv workspace member — Python appears only in
validation notebooks).

```
eagle/
├── README.md / CLAUDE.md
├── Makefile                # make agc / make test / make dev
├── docs/
│   ├── agc-channel-map.md  # octal channel map + sources (primary risk control)
│   ├── coordinate-frames.md
│   ├── adr/
│   └── superpowers/specs/
├── vendor/
│   ├── virtualagc/         # pinned clone (yaYUL assembler + yaAGC emulator)
│   └── Apollo-11/          # pinned clone (Luminary099 source)
├── runtime/                # Rust workspace
│   ├── crates/
│   │   ├── eagle-agc-protocol   # 4-byte packet codec (pure library)
│   │   ├── eagle-dynamics       # Phase 2+
│   │   ├── eagle-sensors        # Phase 2+
│   │   ├── eagle-scenario       # Phase 2+
│   │   ├── eagle-replay         # Phase 4
│   │   └── eagle-schema         # WebSocket telemetry/command schema
│   └── apps/eagle-runtime/
├── client/                 # Vite + React + TypeScript (+ R3F from Phase 3)
├── missions/               # scenario packages (spec §8 format)
├── notebooks/              # trajectory validation, radar calibration
└── tests/
    ├── golden-agc/
    ├── closed-loop/
    └── replay/
```

## 3. Phase plan

| Phase | Content | Visible deliverable | Spec ref |
|---|---|---|---|
| 0 | Build yaYUL/yaAGC in WSL2, assemble `Luminary099`, pin SHAs + hashes | `Luminary099.bin` + one-shot build script | M0 (part) |
| 1 | Rust⇔yaAGC socket bridge + WebSocket + web DSKY (2D) | Key V16N36E in the browser, clock runs | M0 |
| 2 | 6-DoF, DPS/RCS, mass, IMU/PIPA/CDU, first landing radar, closed loop | Real AGC flies a P66 descent; 2D telemetry board | M1 |
| 3 | R3F 3D cockpit + lunar terrain, snapshot interpolation | Fly P63→P64→P66 vertical slice in 3D | M2+M3 |
| 4 | Event log, checkpoints, replay, engineer mode | Mission review screen; truth-vs-nav comparison | M6 (subset) |
| 5 | AI CAPCOM: observe/instructor modes + command validator | Alarm explanation, checklist guidance | M5 |

Each phase is a separate spec → plan → implementation cycle. Phases 0–1 are
designed below; later phases get their own design pass when reached.

## 4. Phase 0 — AGC feasibility spike

- Clone `virtualagc` and `chrislgarry/Apollo-11` into `vendor/` at fixed
  revisions; record SHAs in `vendor/manifest.json` (no submodules).
- Build **CLI targets only**: `yaYUL` (assembler) and `yaAGC` (CPU emulator).
  Do not build wxWidgets GUIs (yaDSKY2 etc.) — the DSKY will be our own web
  implementation.
- Assemble `Luminary099.agc` with yaYUL; verify the produced binary against the
  known-good binary shipped in the virtualagc repository by hash.
- Smoke test: launch `yaAGC` with the binary, connect to its TCP socket,
  confirm channel traffic flows.

**Definition of done:** `make agc` builds and hash-verifies in one shot;
`yaAGC` boots and responds on its socket.

## 5. Phase 1 — Rust bridge + web DSKY (spec M0)

```
Browser (React DSKY, 2D)
   ↕ WebSocket (JSON)
eagle-runtime (Rust: tokio + axum)
   ↕ TCP (yaAGC 4-byte packets)
yaAGC child process (running Luminary099)
```

Components:

- **`eagle-agc-protocol`**: encode/decode of the 4-byte packet format,
  signature-bit validation, channel masks. Pure library with unit tests; octal
  Debug formatting.
- **`eagle-runtime` v0**: spawns yaAGC as a child process; TCP client;
  decodes DSKY output channels (ch 010 digit relays → seven-segment → digits,
  ch 011 lamps, yaAGC extended flashing state); sends DSKY keycodes (ch 015;
  PRO key on its separate channel); broadcasts DSKY state as JSON over
  WebSocket; records all AGC I/O to a timestamped JSONL trace.
- **`client/` v0**: Vite + React **2D DSKY** — PROG/VERB/NOUN, R1–R3, lamps,
  keypad. Clicking keys sends WebSocket commands. No R3F until Phase 3.
- **Golden tests**: headless replay of scripted key sequences (V35E lamp test,
  V16N36E mission-clock display) with captured output-channel sequences
  compared against recorded golden traces. Comparison is **event-order based**,
  not timestamp-exact — the process backend is not bit-exact (spec §6.3).

Explicit simplification: the spec §7.1 requirement that reconnects must never
reset the AGC is relaxed in Phase 1 to "reconnect = restart the session".

**Definition of done:** V35E and V16N36E work from the browser DSKY; both
`make test` (unit, no AGC needed) and `make test-integration` (live yaAGC +
golden traces, run serially) pass.

All channel semantics learned along the way are recorded in
`docs/agc-channel-map.md` (octal, with sources). This is the standing
mitigation for the project's top risk (spec §18: misunderstood channel
semantics).

## 6. Validation strategy (spec §12, personal-lab scale)

1. **Unit tests** (Rust): packet codec, octal conversions, 15-bit word
   handling, seven-segment decode (Phase 1); frame transforms, PIPA/CDU
   quantization, throttle/fuel equations (Phase 2+).
2. **Golden AGC traces**: known key sequences → recorded output-channel
   sequences, versioned under `tests/golden-agc/`.
3. **Property tests** (Phase 2+): fuel never negative; mass monotonically
   decreases; quaternion norm within tolerance; zero thrust when engines off;
   client disconnect cannot alter flight state.
4. **Closed-loop scenario tests** (Phase 2+): nominal P66 descent; from
   Phase 3: full P63→P66, delayed radar acquisition, low fuel.
5. **Notebook validation**: trajectory/descent-rate/fuel time series compared
   visually against Apollo 11 records, in `notebooks/`.

## 7. Definition of done per phase

| Phase | DoD |
|---|---|
| 0 | `make agc` builds + hash-verifies; yaAGC responds on socket |
| 1 | Web DSKY drives V35E / V16N36E; `make test` and `make test-integration` (golden traces) both pass |
| 2 | Real Luminary099 P66 control descends stably to soft touchdown; property tests green; 2D telemetry board live |
| 3 | P63→P64→P66 completed in the 3D cockpit; graded touchdown classification shown |
| 4 | Replay reproduces a run from the event log; engineer board shows truth vs AGC nav |
| 5 | Observe/instructor modes explain alarms and guide checklists; command validator screens all AI proposals |

## 8. Risks and mitigations (inherited from spec §18)

| Risk | Mitigation |
|---|---|
| Misunderstood AGC channel semantics (top risk) | `docs/agc-channel-map.md` with sources; golden traces; behavior comparison against VirtualAGC's contributed LM simulator |
| yaAGC process timing nondeterminism | Do not chase bit-exact replay (F5 abandoned); compare at event-order level |
| Landing radar oversimplified | Phase 2 model is first-pass; parameters carry provenance tags (`assumed` etc.) for later calibration |
| Cockpit scope explosion | Only controls needed for descent; 1201/1202 reproduction is a Phase 3 optional |
