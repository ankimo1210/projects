# GTO Wizard-Parity Product (iOS-first) — Design

Date: 2026-07-19
Status: **Approved design; P0a implementation plan finalized (rev 2),
implementation not started.** Brainstormed section-by-section with the user;
all four sections approved. P0a execution follows
`docs/superpowers/plans/2026-07-19-p0a-algorithm-audit.md`.
Project: `gto/` — turn the existing solver/API/web stack into a commercial
GTO Wizard-like product: **iOS app first (monetized), web freemium later**.
Relation to earlier specs:
- `2026-06-11-mode-matrix-roadmap-design.md` — still the engine-capability
  map. This spec **absorbs M3's variance-reduction + blueprint-quality work
  into launch phase P0** and re-prioritizes everything else around the iOS
  product.
- `2026-06-09-phase-e1-public-deploy-design.md` — auth/rate-limit design stays
  valid; its deploy target becomes the "thin cloud API" here. Stripe (web
  billing) is deferred; **Apple IAP is the only payment rail in v1.0**.

---

## 1. Product decisions (user-confirmed, 2026-07-19)

| Question | Decision |
|---|---|
| Pillars in v1 | **All four**: Study (学習), Practice (練習), Analyze (分析), Play vs AI (プレイ) |
| Game formats in v1 | **NLHE cash 6max + NLHE cash HU** (MTT/PLO deferred) |
| iOS technology | **Expo / React Native** (TypeScript shared with web) |
| Monetization | **Commercial on the Apple App Store only** (IAP subscription). Web = freemium (free with gated quotas), refreshed **after** iOS ships |
| Preflop content quality | **Hybrid**: HU = solver-derived (blueprint abstract-game equilibrium with exploitability attached), 6max = hand-authored charts labeled "GTO approximation" |
| Sequencing | **iOS first**; the existing Neon web UI stays as-is (dev/verification tool) until v1.x |
| Initial App Store build | **All four pillars** in v1.0 (no pillar deferred to v1.x) |
| Content-supply architecture | **Approach A: precomputed packs + minimal cloud API** (no solver in the serving path) |

---

## 2. Goal and success criteria

Ship a paid iOS app (with a functional free tier) that a serious NLHE cash
player would recognize as a GTO Wizard alternative: browse solutions, drill
hands with instant grading, play against a GTO bot, and analyze imported hand
histories — offline-capable, with honest quality labeling.

**Release gates (all must pass before App Store submission):**

1. Blueprint abstract-game exploitability ≤ **0.15 bb/hand** (measured, recorded
   in the pack manifest).
2. River grading differential: on ≥ 200 sampled river decision points, mean
   absolute EV-loss error of blueprint grading vs the exact gto-hu river solve
   ≤ **0.10 bb** (rivers are the one street where we can compare against exact).
3. 6max chart validator: **0 violations** across all shipped charts
   (target ~28–30 charts covering every position pair).
4. All four pillars function offline (except hand-history parsing) on a
   physical device from a clean install.
5. TestFlight beta: crash-free sessions ≥ **99.5%**.
6. App Store approval (17+ rating, "no real-money gambling" positioning).

Additionally, a **development gate** precedes everything heavy: the P0a
algorithm-optimization audit (§5.0) must pass (or be consciously
re-negotiated) before mass content generation and app phases P2+ begin.

---

## 3. System architecture

```
┌──────── Home RTX 5080 box (generation only, never serving) ────────┐
│ gto-hu: blueprint runs / per-flop exact solves / chart authoring    │
│ → pack build pipeline (quantize, compress, fingerprint, manifest)   │
└──────────────┬─────────────────────────────────────────────────────┘
               │ upload (rclone/R2 sync)
   ┌───────────▼──────────┐          ┌────────────────────────────┐
   │ CDN / Cloudflare R2  │          │ Thin cloud API (FastAPI)    │
   │ static pack files    │          │ Supabase auth (+ Apple)     │
   │ + versioned manifest │          │ IAP verify + entitlements   │
   └───────────┬──────────┘          │ hand-history parse          │
               │ HTTPS fetch/cache   └──────────────┬─────────────┘
   ┌───────────▼─────────────────────────────────────▼─────────────┐
   │ iOS app (Expo RN): Study reads packs; Practice / Play /       │
   │ Analyze grade on-device via the blueprint bundle              │
   └───────────────────────────────────────────────────────────────┘
```

Three structural commitments:

1. **No solver in the serving path.** All solution content is precomputed on
   the home GPU box and served as static files. The cloud API is a minimal
   FastAPI deployment (Fly.io or Cloud Run, smallest instance) reusing the E1
   auth/rate-limit stack. Operating cost is near-flat in user count.
2. **Two pack families.** A small preflop pack (bundled/downloaded at first
   launch) and per-flop postflop solution files (fetched on demand from CDN,
   cached, optionally bulk-downloaded for offline).
3. **On-device blueprint for instant grading.** Practice scoring, the Play
   bot, and Analyze deviation math all run on-device by strategy lookup into
   the blueprint bundle (abstract-game equilibrium over M representative
   flops + a real-flop → representative-flop mapping). Same structure as
   Libratus/Pluribus blueprints. No network round-trip per decision.

### 3.1 Development environment lanes

開発環境はハードウェア要件で明確に分離する。正本は
[`docs/development-environments.md`](../../development-environments.md)。

| Lane | Primary environment | Scope |
|---|---|---|
| **W: Solver / Content** | Windows 11 + WSL2 + RTX 5080 | P0a/P0b、solver、pack writer、content generation、FastAPI |
| **M: App / Release** | Mac + Xcode + physical iPhone | P1–P4のExpo/RN、iOS native、IAP、TestFlight、App Store |

P0aはWレーンだけで完結し、Macを必要としない。P1のnative作業はWindowsでは
検証しない。両レーンは同一commit SHA、versioned manifest、SHA-256、Rust
writer → TS readerの小さなgolden fixtureで接続する。Mac環境確認（H0）はP1の
native scaffold開始条件だが、P0aのblockerではない。

---

## 4. Content packs

### 4.1 Preflop pack (small; on-device)

- **HU**: root strategy extracted from the quality blueprint run. Labeled
  "abstract-game equilibrium", shipped with its measured exploitability.
- **6max**: hand-authored charts for all position pairs — 8 existing + ~20
  new covering the remaining ~14 pairs (M2/M3 estimate; the exact pair ×
  chart mapping is fixed during planning) — all passing the existing
  consistency validator (`src/gto/trainer/chart_validator.py`).
- Contents per spot: 13×13 grid frequencies per action, per-combo weights,
  action list with sizes. Quantized u8 frequencies.

### 4.2 Postflop solution files (per-flop; CDN)

- One file per (position pair, pot type, stack, flop): full strategy tree with
  bucketed turn/river strategies, per-combo frequencies and EVs.
- Format: u8 frequencies, f16 EVs, zstd-compressed, target **≤ 15 MB/file**.
- Solved by gto-hu flop solver (exact within the flop game; exploitability
  attached per file). `equilibrium_claim=true` only where an exploitability
  number is present — existing policy carried over unchanged.

### 4.3 Blueprint bundle (on-device)

- Abstract-game average strategy over **M ≥ 25 representative flops**
  (currently M=3 — expansion is P0 work), with K-bucketed turns/rivers.
- Real-flop → representative-flop mapping table (suit isomorphism + flop
  feature distance), shipped with the bundle so grading is deterministic and
  reproducible per bundle version.
- Target size **≤ 300 MB**, downloaded at first launch (not in the app
  binary), updatable OTA independently of app releases.

### 4.4 Manifest and integrity

- Versioned manifest at a fixed CDN path: pack list, SHA-256 fingerprints,
  solver config per artifact, exploitability numbers, generation dates,
  `min_app_version` (schema-compatibility gate).
- Same artifact/fingerprint discipline as `deep_hedge_price` JSON+NPZ
  artifacts.
- Pack schema is defined once and shared: Rust writer ↔ `@gto/packs` TS
  reader, with round-trip golden tests in CI.

---

## 5. Content generation pipeline (P0 — longest lead time)

### 5.0 Algorithm optimization audit (P0a — hard gate before mass generation)

User-mandated gate (2026-07-19): solver throughput is the make-or-break for
this product. Before any detailed implementation of §5.1–5.2 or the app
build-out beyond scaffolding, verify the algorithm is sufficiently
optimized — measured, not assumed.

1. **Benchmark harness**: standardized reference set (river / turn+river /
   flop spots + the WP2 3-flop blueprint config) with fixed seeds; measures
   iteration throughput, wall-clock to target expl, expl-vs-iteration curves,
   peak RSS. Reproducible CLI, JSON output, results committed as baseline
   artifacts (fingerprint discipline).
   Every run expected to exceed 15 minutes must additionally use a durable,
   versioned recovery snapshot. The snapshot must preserve the complete CFR
   training state (including RNG and lazy-discount state), be written by
   temp-file + fsync + atomic rename, retain at least two valid generations,
   and resume bit-identically. Default maximum lost compute is 30 minutes;
   snapshot time, size, and peak-memory overhead are measured in the audit.
   Recovery snapshots live under `_data/gto/checkpoints/` and are never
   committed; only their metadata and validation results enter the report.
2. **Profiling**: flamegraphs + hardware counters (cache misses, memory
   bandwidth) on the flop-solver and blueprint hot loops; classify each as
   compute-bound vs bandwidth-bound; rayon scaling curve (1→N cores) to find
   the parallel-efficiency ceiling.
3. **Algorithm-level review vs state of the art**: DCFR/CFR+ parameterization,
   sampling scheme (public-chance sampling vs external sampling vs turn
   enumeration), SIMD/vectorization over combo arrays, f32 numerical safety,
   dense-table layout, best-response evaluation cost. Sanity-check against
   comparable public CFR systems (open-source postflop solvers, published
   blueprint compute budgets): we should be within a small constant factor of
   what comparable implementations achieve, or know exactly why not.
4. **Quantified go/no-go targets** (these size the §5.2 grid):
   - **G-A1**: median per-flop artifact time (build + solve + final best
     response) reaching the **pre-registered** per-file exploitability
     threshold in **≤ 12 min** on the reference set (else Tier 1 is
     rescoped: fewer flops or configs). The threshold is fixed before the
     runs from the candidate set {0.5, 0.3, 0.15, 0.05} bb; if product
     quality cannot pin it beforehand, the audit reports the measured
     quality/time Pareto curve and the user selects the threshold before
     the G-A1 verdict is issued. Runs that time out are censored no-go
     evidence — the threshold is never relaxed to fit the budget.
   - **G-A2**: blueprint convergence slope restored to ~1/T (fitted exponent
     **≤ −0.85**) on the 3-flop reference after variance reduction (current
     baseline: −0.51). Protocol: pre-registered fit window (the latter
     convergence region), **≥ 3 independent seeds** per stochastic mode,
     median slope with a seed-level interval — the gate passes only if the
     whole interval is ≤ −0.85 — and wall-clock-to-quality compared
     alongside slope-per-iteration. If unmet, a different sampling scheme
     is required before any M expansion.
   - **G-A3** (renegotiated 2026-07-19 after plan review): the P0a gate is
     a **validated projection** — a component-level memory model (dense
     capacity vs allocated bytes, f32 halving applied only to numeric
     slabs), validated against real allocations and real peak RSS (WP2
     anchor: 23.95 GB dense / 27.8 GB RSS), must project the M=25
     blueprint with f32 + board bucketing to **≤ 48 GB**. The current
     engine caps M ≤ 8 (u8 board masks, 2^M zsum), so a real M=25 run
     requires P0b's data-structure work; therefore the **first P0b M=25
     run measuring real peak RSS ≤ 48 GB is a blocking P0b entry gate** —
     mass generation must not start before it passes.
5. **Output**: a benchmark/audit report in `docs/reviews/` with an explicit
   go/no-go decision per target. Mass generation (§5.2) and app phases P2+
   do not start until this gate passes or the targets/grid are consciously
   re-negotiated with the user.

### 5.1 Blueprint quality foundation (absorbs old M3)

Priority order, per the WP2 30k-probe verdict (convergence-limited, not
abstraction-limited):

1. **Variance reduction** in the blueprint trainer (turn enumeration /
   multi-sampling / external sampling) to restore ~1/T convergence from the
   current ~1/√T (public-chance sampling noise dominates).
2. **f32 storage + board bucketing** to cut dense memory so M can grow.
3. **M expansion to ≥ 25 representative flops** (frequency-weighted diverse
   sampling via existing `sample_flops`; `diverse` mode — `frequency`
   degenerates on ties).
4. **Real-flop mapping** (new): suit-isomorphism reduction + nearest
   representative by flop features (high-card structure, pairedness,
   suitedness, connectivity).

Operational lessons carried over: monitor by PID (`while kill -0 $PID`), no
double-backgrounding, SIGSTOP/SIGCONT for pausing, run heavy jobs solo (WP2
first attempt OOM'd under concurrent dev load), and write rotating recovery
snapshots at safe iteration boundaries. A restart must reconstruct the same
solver configuration, reject incompatible/corrupt snapshots, and continue
without changing the final numerical result relative to an uninterrupted run.

### 5.2 Postflop grid (tiered; OTA-expandable)

Representative flop subset: **~95 canonical flops** (stratified sample of the
1,755 canonical flops, frequency-weighted). Per-flop solve time is the
budget driver (~49 min/flop at current settings; variance reduction +
tuned iteration counts target ~10 min/flop — to be re-estimated in P0).

| Tier | Contents | Approx. solves | When |
|---|---|---|---|
| 1 (launch-blocking) | HU {SRP, 3bet} × 100bb; 6max opener-vs-BB 5 pairs × {SRP, 3bet} × 100bb | ~1,140 | Before TestFlight |
| 2 (pre-submission, budget-permitting) | Remaining ~14 6max pairs × SRP × 100bb; HU SRP × {50, 200}bb | ~1,520 | Before App Store submission if GPU budget allows |
| 3 (post-launch OTA) | Remaining 3bet configs, more stacks, grid densification | open-ended | Continuous |

Packs are content, not code: the launch decision is gated on Tier 1 only;
coverage grows continuously after launch without app updates.

### 5.3 Quality labeling (uniform across app)

| Badge | Meaning | Applies to |
|---|---|---|
| EXACT | gto-hu solve with exploitability attached | Postflop solution files |
| BLUEPRINT | Abstract-game equilibrium, expl attached, flop-mapping approximation | Practice/Play/Analyze grading, HU preflop |
| CHART | Hand-authored, validator-checked, not a solver output | 6max preflop |

The existing rule — "equilibrium" may only be claimed with an exploitability
number attached — is binding in all UI copy.

---

## 6. iOS app (Expo React Native)

### 6.1 Repo layout and shared code

```
gto/
  mobile/            # Expo RN app (EAS Build)
  packages/
    domain/          # @gto/domain: cards, hands, ranges, flop canonicalization
                     #   (moves web/lib/flop-canon.ts here), TS 7-card evaluator
    packs/           # @gto/packs: pack schema, loader, fingerprint check,
                     #   blueprint lookup + real-flop mapping
    api-client/      # @gto/api-client: thin API + auth + entitlements
  web/               # existing Next.js app — consumes packages/* in v1.x
```

State: zustand + React Query. Rendering: react-native-svg + Skia for the
range grid and table (an early performance spike on a physical device is a
P1 task — 13×13 grid × per-cell action bars is the risk area).

### 6.2 Tabs (GTO Wizard parity)

| Tab | v1.0 behavior | Data source |
|---|---|---|
| Study | Spot selector (format / stack / pair / pot type) → preflop 13×13 grid + action-frequency bars → postflop: flop picker → node navigation, per-combo strategy + EV | Preflop pack + per-flop CDN files |
| Practice | Table UI deals a random spot (filterable); user acts street by street; per-decision grading (best / correct / inaccuracy / mistake / blunder + EV loss); session score like the GTOW score screen | On-device blueprint |
| Play | Same table UI; continuous hands vs blueprint bot (HU, or 6max with bots in other seats); optional score tracking | On-device blueprint |
| Analyze | Import PokerStars-format hand-history text → server parse → per-hand deviation list, per-street EV loss, aggregates | API parse + on-device grading |
| Settings | Sign in with Apple / email (Supabase), IAP purchase/restore, pack management (download/delete/update), free-quota display | Thin API |

### 6.3 Offline behavior

Preflop pack, blueprint bundle, and any downloaded flop files work fully
offline (Study over downloaded content, Practice, Play). Analyze parsing
requires the network in v1.0 (Python parser stays server-side).

### 6.4 Free tier (freemium)

| Pillar | Free | Subscribed |
|---|---|---|
| Study | Curated free spot set (e.g. BTN-vs-BB SRP 100bb) + one rotating daily free spot | All spots |
| Practice / Play | 10 hands/day | Unlimited |
| Analyze | 10 hands/month | Unlimited |

Quotas enforced client-side backed by server entitlements; premium flop files
served via entitlement-signed R2 URLs. We explicitly accept that a
jailbroken device can extract bundled content — protection deters casual
scraping only (see §11).

---

## 7. Thin cloud API and billing

- **Auth**: Supabase — Sign in with Apple (App Store requirement when any
  third-party login exists) + email. The FastAPI layer verifies Supabase JWTs;
  the E1 HS256/rate-limit stack (30/min, 500/day) stays.
- **IAP**: App Store Server API v2 for transaction verification + App Store
  Server Notifications v2 webhook → subscription state in Supabase →
  short-lived entitlement token issued to the device (cached, refreshed
  opportunistically; grace-period aware).
- **SKUs**: one subscription group, two SKUs — monthly **¥1,500**, annual
  **¥9,000** (provisional; final pricing set in App Store Connect before
  submission; not a code change).
- **Endpoints**: `/api/review/parse` (existing), entitlement issue/refresh,
  signed-URL issue for premium packs, health. Nothing else. No solve
  endpoints are exposed to the app in v1.0.
- **Deploy**: Fly.io or Cloud Run smallest instance; 3-stage Dockerfile
  already exists.

---

## 8. Error handling

- **Pack downloads**: resumable, SHA-verified, atomic install (temp file →
  rename); corrupted file → re-fetch; manifest `min_app_version` mismatch →
  prompt app update instead of loading incompatible packs.
- **Grading**: if a spot falls outside blueprint coverage (e.g. limped pot,
  unsupported line), the app says "not covered" explicitly rather than
  guessing; Practice only deals from covered spot families, so this path is
  Analyze-only.
- **IAP**: restore purchases, billing grace period honored, receipt-verify
  outages fall back to last-known entitlement with a bounded validity window.
- **API down**: everything except Analyze parsing keeps working offline;
  Analyze queues the import and retries.
- **Version skew**: pack schema version embedded per file; readers reject
  unknown majors (fail-loud, mirroring the solver's memory-guard philosophy).

## 9. Testing

- **Rust**: existing suites stay green; new pack-writer round-trip golden
  tests (write → read → bit-compare via TS reader fixtures).
- **TS `@gto/domain`**: 7-card evaluator differential-tested against the Rust
  evaluator on Rust-generated fixtures (both random and adversarial boards);
  flop canonicalization property tests (extends existing
  `web/lib/flop-canon.test.mjs`).
- **TS `@gto/packs`**: blueprint lookup determinism, mapping stability,
  fingerprint rejection tests.
- **Grading quality**: the §2 river-differential gate, automated as a
  releasable report; regenerated whenever the blueprint bundle changes.
- **RN**: component tests (Jest + RN Testing Library) + Maestro E2E for the
  five core flows + IAP sandbox testing on TestFlight.
- **Content**: chart validator (0 violations), exploitability gates in the
  pack build pipeline (build fails if a pack misses its gate).

## 10. Phases (iOS-first; P0 runs concurrently with P1–P3)

| Phase | Primary environment | Deliverable | Depends on |
|---|---|---|---|
| **P0a** | **W** | Algorithm optimization audit (§5.0): benchmark harness, profiling, algorithm review, G-A1..3 go/no-go report | — (first; hard gate for P0b mass generation and P2+) |
| **P0b** | **W**; M validates contract | Quality foundation: variance reduction, f32 + board bucketing, M-cap lift (u8 masks / 2^M zsum → M ≥ 25), M ≥ 25 blueprint quality run (**entry gate: first real M=25 run peak RSS ≤ 48 GB — G-A3 confirmation**), real-flop mapping, pack format + build CLI + R2 upload | P0a gate passed |
| **P1** | **M** | Expo scaffold, `@gto/domain` / `@gto/packs` / `@gto/api-client`, Study tab (preflop first, postflop when Tier-1 grid lands), Skia perf spike | H0 Mac ready; P0b preflop pack (scaffold may start during P0a with fixtures) |
| **P2** | **M** | Practice + Play: table UI, grading engine, session scoring, bot | P0a gate passed; P0b blueprint bundle |
| **P3** | **M** + W/cloud backend | Analyze: parse integration + on-device grading + aggregates | P2 grading engine |
| **P4** | **M** + cloud | Commercialization: Supabase auth, IAP + entitlements, gating, pack management UI, TestFlight beta → **App Store submission** | P1–P3; H1–H4 |
| v1.x | Per feature | See §12 (future roadmap) | — |

TestFlight beta can start after P2 (Study + Practice + Play working) while
P3/P4 complete — earliest real-user signal.

---

## 11. Out of scope for v1.0, and known limitations

### 11.1 Explicitly out of scope (deferred, not forgotten)

| Item | Why deferred | Where it lands |
|---|---|---|
| Web app refresh (freemium web) | iOS-first decision; existing Neon UI stays as an internal dev/verification tool | v1.1 |
| Custom solves from the app (approach C: async queue to a cloud worker) | Extra moving parts delay submission; M1b job subsystem makes this a bounded add later | v1.1 |
| Stripe / web billing | Commercial = Apple App only (user decision) | With web refresh |
| MTT / ICM | Engine has HU chip-EV tournament folding only; real ICM is new modeling work | v1.2 |
| PLO | Engine not implemented (old M4); large research risk | v2 |
| 9max | Chart authoring + validation effort; 6max is the priority market | v2 |
| Android | Expo makes it cheap later; one store at a time | v1.x after iOS stabilizes |
| True-solve 6max preflop (MCCFR) | Months of work; charts + validator are an honest interim | v1.x/v2 (replaces CHART badge with solver output) |
| Multiway (3+ player) postflop | Engine non-goal pending research; postflop pots in scope are heads-up | Research track |
| GTOW power features: nodelocking, aggregate reports, runout explorer, dynamic/AI sizing, range vs range equity charts, Spin&Go / HU SnG formats | Each is a product in itself; v1.0 ships the four-pillar core | Backlog, prioritized by user feedback |
| Push notifications, study reminders, spaced repetition | Nice-to-have engagement layer | v1.x |
| In-app hand-history auto-import from poker clients | v1.0 is paste/file-import of PokerStars text only | v1.x (more room formats too) |

### 11.2 Known limitations shipping in v1.0 (documented honestly, in-app)

1. **Grading is a blueprint approximation.** Practice/Play/Analyze scores come
   from an abstract-game equilibrium over M representative flops with a
   flop-mapping step. Edge flops (odd suit textures, rare pairings) map with
   more distortion. Mitigations: M ≥ 25 gate, river differential gate (§2),
   BLUEPRINT badge on every score, per-bundle expl number shown in Settings.
2. **6max preflop is chart-based**, validator-checked but hand-authored — not
   solver output. CHART badge; no equilibrium claim.
3. **Postflop coverage is a subset** (~95 flops × Tier grid, not 1,755 × all
   configs). Study shows the nearest solved flop with an explicit "nearest
   flop" disclosure when the requested flop isn't solved. Coverage grows OTA.
4. **Postflop packs are rakeless (chip EV).** The gto-hu flop rake path is
   not implemented (river/turn have it; flop doesn't). v1.0 postflop = cEV;
   rake-aware postflop packs are future work. 6max charts are NL50-calibrated
   by authoring. This mirrors how many solver products started and is
   disclosed in-app.
5. **Practice/Play deal only covered spot families** (heads-up pots from the
   supported pair × pot-type grid; no limped pots, no multiway, no 4bet+ pots
   in v1.0 practice dealing).
6. **Analyze skips what it can't grade** (multiway streets, unsupported lines,
   non-PokerStars formats) — counted and reported as "skipped", never silently
   dropped.
7. **Content is extractable** from a jailbroken device / MITM'd CDN fetch.
   Signed URLs + fingerprinting deter casual scraping only. Accepted risk;
   revisit only if it becomes a real business problem.
8. **Single home GPU is the generation plant** (SPOF). Mitigation: artifacts +
   configs + manifests backed up off-box; every pack reproducible from config
   (fingerprint discipline); no serving dependency on the box.
9. **App Store category risk**: poker training apps are permitted (17+, no
   real-money gambling), but review outcomes vary. Mitigation: no real-money
   language, training positioning, IAP-only payments, working free tier at
   review time.

### 11.3 Retired from the product path

- The 19,305-spot **gto-cuda preview library** (uniform ranges, single-street
  approximation, `equilibrium_claim=false`) does **not** ship in the iOS app.
  It remains in the web dev tool until the v1.x web refresh decides its fate.
- The `simulation` page's role is covered by Study postflop node navigation
  in the app.

---

## 12. Future roadmap (post-v1.0, indicative order)

1. **v1.1** — Web freemium refresh on the same packs (`@gto/packs` in
   Next.js), custom-solve queue (approach C; premium differentiator, reuses
   M1b job subsystem), aggregate reports (per-flop-class frequency tables are
   cheap to derive from packs).
2. **v1.2** — MTT/ICM (HU ICM first), more stacks/rake variants in the grid,
   Android via Expo, richer Analyze (more room formats, auto-import).
3. **v2** — true-solve 6max preflop (MCCFR), PLO river prototype → PLO
   product track, 9max charts, nodelocking-class study tools.

Each item gets its own spec + plan cycle; nothing above is committed by this
document.

## 13. Open questions intentionally deferred to implementation planning

- Exact per-flop solver settings after variance reduction (iterations, K_r,
  K_t) — needs P0 measurements; grid tiers in §5.2 are sized conservatively.
- Blueprint bundle exact size/quantization trade-off (≤ 300 MB target may
  tighten after M-expansion measurements).
- Fly.io vs Cloud Run (both fit; pick during P4 based on Supabase region
  latency).
- Final free-tier quota numbers (start from §6.4; tune in TestFlight).
