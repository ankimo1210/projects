# johnhull「Hull の先」A5–A8 Implementation Plan

> 本文は当初の実装計画と完了条件の記録。2026-07-18 時点で vol 18–25 と
> G8 release gate は完了。最終 fresh 検証、`johnhull/VALIDATION.md`、
> strict tracked gate、明示承認後の専用 branch への push まで完了した。

**Goal:** `johnhull` に vol 18–25 を段階追加し、ML pricing、surface calibration、volatility dynamics、
SPX/VIX・0DTE、RFR、crypto、climate/energy を、再現可能な notebook/book/report と検証済みライブラリとして届ける。

**Architecture:** `hullkit` は torch-free の金融教師・hard validator、`deep_hedge_price` は PyTorch 学習基盤、
`johnhull` は小型 artifact を読む教材・可視化・統合層とする。接続は versioned JSON + NPZ だけで行う。

**Design:** `docs/superpowers/specs/2026-07-18-johnhull-beyond-hull-a5-design.md`

**Parent proposal:** `docs/superpowers/specs/2026-07-18-johnhull-beyond-hull-options.md`

**Planning baseline verified (2026-07-18, 実装前の歴史値):**

- `hullkit`: 184 tests collected
- `johnhull/report`: 3 tests collected（合計 187）
- `deep_hedge_price`: 20 tests collected
- Jupyter Book: vol 1–17 + legacy の 20 pages
- Offline portal: 7 themes / 38 figures

**Current implementation snapshot (2026-07-18):**

| Gate | Status | Evidence |
|---|---|---|
| G0 | done | Phase 1/2 owner 分離、versioned artifact/config、torch-free hard validator |
| G1 | integration PASS | vol 18 JSON/NPZ、executed notebook、巻別 `VALIDATION.md` |
| G2 | integration PASS | vol 19 actual numerical teachers/calibration/constraint artifacts |
| G3 | integration PASS | vol 20 purged walk-forward/end-to-end hedge artifacts；Phase 1 実 policy は `not_evaluated` |
| G4 | integration PASS | vol 21–22 joint SPX/VIX と 0DTE artifacts |
| G5 | integration PASS | vol 23 RFR convention/curve/SABR/hedge artifacts |
| G6 | integration PASS | vol 24 perpetual/liquidation/AMM identity artifacts |
| G7 | integration PASS | vol 25 carbon/weather/PPA artifacts |
| G8 | **done** | final fresh run、validation、tracked release gate、専用 branch への push を完了 |

`release_manifest.json` の現行契約は vol 18–25、portal **11 themes / 70 figures**、
Jupyter Book **28 pages**。巻別 PASS は `integration_and_reproducibility` の判定であり、
**model performance approved = no** とする。最終なテスト件数は G8 の fresh run 後に
`johnhull/VALIDATION.md` へ固定する。

---

## 0. 実行ルール

- root `/home/kazumasa/projects` から `uv` を使う。project 内で別 `.venv` を作らない。
- 当初は G0 → G1 → … → G7 の順に拡張した。現在の作業範囲は **G8 最終統合**。
- production dependency、公開 API、project 間の依存方向は G0 contract と release verifier で固定する。
- `hullkit` に torch を追加しない。notebook/book の既定経路でも torch を import しない。
- checkpoint、生 Monte Carlo paths、full dataset、市場データを commit しない。
- 小型 reference artifact は JSON + NPZ とし、生成コマンドと fingerprint を記録する。
- notebook build は既存 artifact のみを読み、学習・download・GPU 検出をしない。
- 市場データなしの結果を、市場予測力・収益性・production readiness と表現しない。
- 1 task = 1 coherent change。指定ファイルだけを stage し、commit/push はユーザーの明示指示後に行う。
- acceptance failure は最大 3 回まで最小修正を試し、解消しなければ gate report に blocker と縮小案を残す。

### 共通検証コマンド

```bash
cd /home/kazumasa/projects

# johnhull / hullkit / portal
uv run --no-sync --package hullkit pytest -s -q johnhull/hullkit/tests johnhull/report/tests

# PyTorch pricing engine
uv run --no-sync --package deep-hedge-price pytest -s -q deep_hedge_price/tests

# scoped lint
uv run --no-sync ruff check deep_hedge_price/src deep_hedge_price/tests deep_hedge_price/scripts \
  johnhull/hullkit/src johnhull/hullkit/tests johnhull/scripts \
  johnhull/report/report_builder johnhull/report/tests
uv run --no-sync ruff format --check deep_hedge_price/src deep_hedge_price/tests deep_hedge_price/scripts \
  johnhull/hullkit/src johnhull/hullkit/tests johnhull/scripts \
  johnhull/report/report_builder johnhull/report/tests

# deterministic artifacts / notebooks / delivery
make hull-artifacts-check
make hull-notebooks-check
make hull-report
make hull-book
make hull-release-check

# project-scoped tests/lint + all checks/builds above
make hull-release

# committed release のみ
make hull-release-check HULL_RELEASE_FLAGS=--require-tracked
```

pytest の package 指定を省くと、workspace root と同名 package directory の解決が衝突することがあるため、
上記の `--package` を維持する。

---

## G0 — Contract and Ownership Gate

### Task 1: Phase 2 roadmap を A5 の正本へ統合する

**Files:**

- Modify: `deep_hedge_price/docs/ROADMAP_DEEP_PRICING.md`
- Modify: `deep_hedge_price/README.md`
- Modify: `johnhull/ROADMAP.md`
- Reference: `docs/superpowers/specs/2026-07-18-johnhull-beyond-hull-a5-design.md`

- [x] `ROADMAP_DEEP_PRICING.md` の各項目を vol 18/G1 の task と対応付ける。
- [x] 「Phase 2 の学習 engine は `deep_hedge_price` が正本」「教材は `johnhull`」と明記する。
- [x] `hullkit` hard validation と `deep_hedge_price` differentiable soft loss を区別する。
- [x] Phase 1 deep hedging の config/checkpoint/manifest を Phase 2 と混ぜない方針を固定する。
- [x] A5–A8 の volume 番号 18–25 と gate/status を `johnhull/ROADMAP.md` に登録する。
- [x] 新しい production dependency は追加しない。

**Acceptance:** 同じ機能について二つの active roadmap が異なる owner/API を指していない。

### Task 2: versioned artifact contract と split audit を実装する

**Files:**

- Create: `deep_hedge_price/src/deep_hedge_price/pricing_artifacts.py`
- Create: `deep_hedge_price/src/deep_hedge_price/pricing_config.py`
- Create: `deep_hedge_price/tests/test_pricing_artifacts.py`
- Create: `deep_hedge_price/tests/test_pricing_config.py`
- Create: `deep_hedge_price/configs/pricing_quick.yaml`
- Create: `deep_hedge_price/configs/pricing_default.yaml`
- Create: `deep_hedge_price/configs/pricing_full.yaml`

**Required interfaces:**

```python
@dataclass(frozen=True)
class PricingDatasetManifest:
    schema_version: int
    artifact_kind: str
    model: str
    teacher_method: str
    parameterization: str
    seed: int
    split_fingerprints: dict[str, str]
    overlap_count: int
    arrays: str
    generator_version: str
    git_sha: str

def fingerprint_rows(array: np.ndarray) -> str: ...
def assert_disjoint_splits(split_rows: dict[str, np.ndarray]) -> None: ...
def save_pricing_dataset(..., output_dir: Path) -> tuple[Path, Path]: ...
def load_pricing_dataset(manifest_path: Path) -> tuple[PricingDatasetManifest, dict[str, np.ndarray]]: ...
```

- [x] TDD: valid JSON/NPZ round-trip、missing field、unknown schema、shape mismatch、digest mismatch をテストする。
- [x] train/validation/test/OOD の row fingerprint を作り、重複時は保存前に失敗させる。
- [x] price、Greek、standard error、CI の単位・shape・dtype を manifest に固定する。
- [x] Phase 1 `ProjectConfig` とは別の `PricingConfig` を作る。
- [x] quick/default/full で seed、sample size、epochs、device、output namespace を分離する。
- [x] checkpoint ではなく dataset manifest だけを読む loader が torch import なしで動くことをテストする。

**Acceptance:** 同じ seed/config で manifest と arrays の digest が一致し、1 行でも split を重複させるとテストが落ちる。

### Task 3: torch-free hard validation を hullkit に追加する

**Files:**

- Create: `johnhull/hullkit/src/hullkit/surrogate_validation.py`
- Create: `johnhull/hullkit/tests/test_surrogate_validation.py`
- Modify: `johnhull/hullkit/src/hullkit/__init__.py`

**Required interfaces:**

```python
@dataclass(frozen=True)
class CheckResult:
    name: str
    n_checked: int
    n_violations: int
    violation_rate: float
    max_violation: float
    tolerance: float

def check_price_bounds(..., tolerance: float) -> CheckResult: ...
def check_put_call_parity(..., tolerance: float) -> CheckResult: ...
def check_strike_monotonicity(..., tolerance: float) -> CheckResult: ...
def check_strike_convexity(..., tolerance: float) -> CheckResult: ...
def check_calendar_monotonicity(..., tolerance: float) -> CheckResult: ...
def check_greek_consistency(..., tolerance: float) -> CheckResult: ...
```

- [x] BSM reference grid が全 check を通るテストを先に書く。
- [x] 意図的に quote を壊し、各 check が violation と最大量を検出するテストを書く。
- [x] strike/calendar grid の並びと単位を検証し、勝手に sort/補間しない。
- [x] `arbitrage_free` という aggregate flag は「適用対象の全 hard check passed」のときだけ true にする。
- [x] module import graph に torch/deep_hedge_price が含まれないことを package test で固定する。

**Acceptance:** `uv run --no-sync --package hullkit python -c "import hullkit"` が torch なしの依存集合で成功する。

### G0 review

- [x] artifact owner、public API、config namespace、依存方向をレビューする。
- [x] 既存 baseline を回帰 suite に保持する（現行の正確な件数は G8 fresh run 後に固定）。
- [x] G0 decision を `johnhull/ROADMAP.md` に記録する。
- [x] G0 contract が G1–G7 release candidate の前提として現在も成立している。

---

## G1 — vol 18「Theory-Guided Surrogates & Greeks」

### Task 4: dimensionless Black–Scholes dataset generator

**Files:**

- Create: `deep_hedge_price/src/deep_hedge_price/pricing_data.py`
- Modify: `deep_hedge_price/src/deep_hedge_price/black_scholes.py`
- Create: `deep_hedge_price/tests/test_pricing_data.py`
- Modify: `deep_hedge_price/tests/test_black_scholes.py`

**Parameterization:**

\[
x=S/K,\quad \tau=T,\quad \hat C=C/K,
\]

with inputs `(x, tau, r, q, sigma)` and labels `price, delta, gamma, vega, theta, rho`.

- [x] dividend yield `q` と全 analytic Greeks を scalar/vectorized API へ追加する。
- [x] expiry、zero-vol、deep ITM/OTM、small maturity の明示 branch をテストする。
- [x] Latin hypercube または stratified grid で train/validation/test を独立生成する。
- [x] OOD shell は in-domain box の各辺の外側に作り、interpolation test と混ぜない。
- [x] 同じ parameter tuple を split 間に流用しない。
- [x] dataset manifest に formula version、bounds、sampling design、seed を保存する。
- [x] 解析値を `hullkit.bsm` の reference points と相互照合する integration test を用意する。

**Acceptance:** analytic round-trip は machine precision、split overlap は 0、同じ seed の artifact は byte-stable。

### Task 5: polynomial baseline と price-only MLP

**Files:**

- Create: `deep_hedge_price/src/deep_hedge_price/pricing_policy.py`
- Create: `deep_hedge_price/src/deep_hedge_price/pricing_training.py`
- Create: `deep_hedge_price/tests/test_pricing_policy.py`
- Create: `deep_hedge_price/tests/test_pricing_training_smoke.py`

- [x] normalized polynomial/ridge baseline を先に実装し、fit/predict を保存可能にする。
- [x] small MLP は deterministic feature normalization を checkpoint に含める。
- [x] output は `C/K`。discounted intrinsic lower bound からの time value を学習する variant を用意する。
- [x] price-only model を基準にし、複雑な head/loss との比較基準にする。
- [x] train seed、validation seed、test seed を分離する。
- [x] early stopping と best checkpoint の再ロードを smoke test する。
- [x] Phase 1 hedge policy と checkpoint path/schema を完全に分ける。

**Acceptance:** pricing quick profile が CPU で完走し、in-domain `price MAE < 1e-3 * K`。達しない場合は G1 を止める。

### Task 6: Greeks multi-task、Differential ML、residual correction

**Files:**

- Create: `deep_hedge_price/src/deep_hedge_price/greeks.py`
- Create: `deep_hedge_price/src/deep_hedge_price/pricing_losses.py`
- Modify: `deep_hedge_price/src/deep_hedge_price/pricing_policy.py`
- Modify: `deep_hedge_price/src/deep_hedge_price/pricing_training.py`
- Create: `deep_hedge_price/tests/test_pricing_greeks.py`
- Create: `deep_hedge_price/tests/test_pricing_losses.py`

- [x] price head の autodiff Greeks を analytic values と照合する。
- [x] direct Greek heads と price-head autodiff の consistency error を定義する。
- [x] price-only、direct multi-task、Differential ML を同じ split/seed で比較する。
- [x] label ごとに scale-balanced normalization を行い、loss weight を manifest に保存する。
- [x] BS では lower-bound/time-value residual、Heston では BSM residual を比較する。
- [x] gamma のような 2 階微分は float64 evaluation と boundary masking を使い、学習 loss と hard check を混同しない。
- [x] 3 seeds の mean/dispersion を保存する。

**Acceptance:** delta MAE `< 2e-3`。joint/DML は価格を materially 悪化させず、少なくとも 1 Greek を改善する。
改善しなければ price-only を採用し、negative result として記録する。

### Task 7: differentiable soft penalties と hard-check adapter

**Files:**

- Create: `deep_hedge_price/src/deep_hedge_price/arbitrage.py`
- Create: `deep_hedge_price/tests/test_arbitrage.py`
- Create: `deep_hedge_price/tests/test_pricing_benchmark.py`（optional `hullkit` interop test を統合）
- Modify: `deep_hedge_price/src/deep_hedge_price/pricing_training.py`

- [x] structured mini-batch 上の price bounds、spot/strike monotonicity、strike convexity、calendar consistency penalty を実装する。
- [x] penalty 0 の reference surface と、違反を作る synthetic surface をテストする。
- [x] soft penalty weight 0/positive の ablation を行う。
- [x] evaluation 時は tensor を detach し、`hullkit.surrogate_validation` の hard report を正本として保存する。
- [x] `hullkit` が未導入の standalone deep_hedge_price では明確な optional-integration error を返す。
- [x] soft penalty が小さいことを理由に `arbitrage_free` としない。

**Acceptance:** hard report に check ごとの `n_checked/n_violations/max_violation/tolerance` が揃い、
unconstrained/constrained を同じ表で比較できる。

### Task 8: Monte Carlo labels と Heston/COS teacher

**Files:**

- Create: `johnhull/hullkit/src/hullkit/surrogate_data.py`
- Create: `johnhull/hullkit/tests/test_surrogate_data.py`
- Create: `deep_hedge_price/scripts/export_johnhull_pricing_reference.py`
- Modify: `johnhull/hullkit/src/hullkit/__init__.py`

- [x] analytic BS labels、Heston/COS labels、MC price/Greek estimates を共通 row schema へ変換する。
- [x] MC は seed-addressable、chunked、antithetic、control variate、common random numbers を使う。
- [x] estimate、SE、95% CI、path count、method、seed を保存する。
- [x] BS call の empirical CI coverage を複数 seed で検査する。
- [x] path 数を 4 倍にしたとき SE が概ね 1/2 になることを tolerance 付きで検査する。
- [x] Heston `xi -> 0, v0 = theta = sigma^2` が BSM へ戻ることを固定する。
- [x] quick reference は小型 JSON/NPZ、full artifact は ignored directory に書く。

**Acceptance:** teacher discrepancy が teacher CI と並べて報告され、学習誤差だけで teacher noise を下回ったと主張しない。

### Task 9: OOD、bucket metrics、speed/calibration benchmark

**Files:**

- Create: `deep_hedge_price/src/deep_hedge_price/pricing_evaluation.py`
- Create: `deep_hedge_price/src/deep_hedge_price/pricing_benchmark.py`
- Create: `deep_hedge_price/tests/test_pricing_evaluation.py`
- Create: `deep_hedge_price/tests/test_pricing_benchmark.py`
- Modify: `deep_hedge_price/src/deep_hedge_price/cli.py`

**CLI additions:**

```text
pricing-generate
pricing-train
pricing-evaluate
pricing-report
pricing-demo
```

- [x] moneyness × maturity bucket の price/Greek MAE、relative error、worst case を出す。
- [x] in-domain と OOD shell を別表にする。
- [x] CPU timing は warm-up、batch size、repeat、median、dispersion を保存する。
- [x] CUDA timing は optional。device synchronization と hardware metadata を必須にする。
- [x] analytic BS、COS/MC teacher、polynomial、MLP の latency/throughput を同じ harness で測る。
- [x] synthetic implied-vol inversion または簡単な parameter recovery を行い、surrogate の break-even を報告する（quick profile では未観測）。
- [x] CLI が missing/incompatible artifact を暗黙再生成せず、次の明確な command とともに失敗する。

**Acceptance:** quick CPU profile の `generate -> train -> evaluate -> report` が 1 command で完走し、manifest から再現できる。

### Task 10: standalone pricing report と Notebook 02

**Files:**

- Create: `deep_hedge_price/src/deep_hedge_price/pricing_plotting.py`
- Create: `deep_hedge_price/src/deep_hedge_price/pricing_report.py`
- Create: `deep_hedge_price/src/deep_hedge_price/pricing_notebook.py`
- Create: `deep_hedge_price/notebooks/02_neural_pricing_surrogate.ipynb`
- Create: `deep_hedge_price/tests/test_pricing_report.py`
- Modify: `deep_hedge_price/Makefile`
- Modify: `deep_hedge_price/README.md`

- [x] label QA、baseline、learning curve、error surface、Greek slices、hard checks、OOD、calibration、speed を載せる。
- [x] price-only と DML の差がない/悪い場合も隠さず表示する。
- [x] standalone HTML は Plotly JS を inline にし、外部 URL を含めない。
- [x] Phase 1 report と Phase 2 report の manifest、file name、navigation を分ける。
- [x] `make pricing-demo` と `make pricing-report` を追加する。
- [x] notebook は既存 artifact を読み、セル内で training を起動しない。

**Acceptance:** report test が全 required section、fingerprint、limitations、offline 条件を検査する。

### Task 11: johnhull vol 18 notebook/book/report integration

**Files:**

- Create: `johnhull/volumes/18_ml_surrogates/build_18_ml_surrogates_notebook.py`
- Create: `johnhull/volumes/18_ml_surrogates/ml_surrogates.ipynb`
- Create: `johnhull/volumes/18_ml_surrogates/reference/pricing_metrics.json`
- Create: `johnhull/volumes/18_ml_surrogates/reference/pricing_slices.npz`
- Create: `johnhull/volumes/18_ml_surrogates/VALIDATION.md`
- Create: `johnhull/book/notebooks/18_ml_surrogates.ipynb` (symlink)
- Modify: `johnhull/book/_toc.yml`
- Modify: `johnhull/book/notebooks/00_overview.md`
- Modify: `johnhull/report/report_builder/figures.py`
- Create: `johnhull/report/report_builder/frontier_figures.py`（ML/A6–A8 figure を統合）
- Modify: `johnhull/report/tests/test_report_build.py`
- Modify: `johnhull/ROADMAP.md`

**Notebook story (約 16–20 cells):**

1. 問い・責務・data policy
2. dimensionless BS と analytic reference
3. split/OOD fingerprint audit
4. polynomial vs price-only MLP
5. price + Greek multi-task
6. Differential ML
7. residual correction
8. hard arbitrage diagnostics
9. Heston/COS/MC teacher uncertainty
10. CPU speed/break-even
11. limitations / negative results / research track

- [x] builder は versioned JSON/NPZ だけを読む。
- [x] release candidate の JSON/NPZ が追跡済み commit と一致する（G8 strict gate で確認）。
- [x] 核心/直感/実務 scaffold を各主要 section に使う。
- [x] reference artifact の schema/fingerprint を notebook 冒頭で検証する。
- [x] report に `ml_derivatives` theme と 4 figures（error surface、Greek error、hard violations、speed）を追加する。
- [x] report registry を現行 release contract の 11 themes / 70 figures に更新する。
- [x] book TOC と overview に vol 18 を追加する。
- [x] executed notebook を生成し、build 中の network/training を禁止する。
- [x] executed notebook を最終 release commit に含める。

**Acceptance:** vol 18 page、book、portal が reference artifact だけで再構築できる。

### Task 12: G1 final verification and gate report

G1 の巻別 integration evidence は存在するが、以下は G8 で最終 fresh run する。

- [x] `uv run --no-sync --package hullkit pytest -s -q johnhull/hullkit/tests johnhull/report/tests`
- [x] `uv run --no-sync --package deep-hedge-price pytest -s -q deep_hedge_price/tests`
- [x] scoped ruff check/format check
- [x] pricing quick demo の CPU artifact/report を生成
- [x] notebook を artifact から execute
- [x] portal に vol 18 figures を統合
- [x] book に vol 18 を統合
- [x] 巻別 `VALIDATION.md` に metrics、negative results、limitations を固定
- [ ] checkpoint/large artifact/market data が staged files に無いことを確認
- [x] G1 巻別 acceptance table を pass/fail で埋める
- [x] G1 artifact/config/evaluation API を G2 へ再利用する

---

## G2 — vol 19「Inverse Problems & Arbitrage-Aware Surfaces」

G1 の artifact/config/evaluation API を変更せず再利用できることが着手条件。

### Task 13: forward surrogate と two-step calibration

**Candidate files:**

- `deep_hedge_price/src/deep_hedge_price/pricing_calibration.py`
- `deep_hedge_price/src/deep_hedge_price/surface_data.py`
- `deep_hedge_price/tests/test_pricing_calibration.py`
- `johnhull/hullkit/src/hullkit/vol_surface.py`
- `johnhull/hullkit/tests/test_vol_surface.py`

- [x] Heston/SABR/rBergomi の parameter → price/IV forward dataset を分離生成する。
- [x] analytic/numerical teacher と surrogate を同じ optimizer interface で呼ぶ。
- [x] multi-start、parameter bounds、initial-value sensitivity を保存する。
- [x] direct inverse map（quick profile は ridge）は ablation に限定する。
- [x] parameter error と repricing error を別に評価する。

### Task 14: SSVI/hard-constrained surface と joint variance calibration

- [x] SSVI または convex call-price parameterization を baseline として実装する。
- [x] unconstrained、soft penalty、hard-constrained decoder を同じ quote grid で比較する。
- [x] IV fit に variance term structure loss を追加する。
- [x] `lambda_var` sweep と Pareto frontier を出す。
- [x] IV が合っても variance term が外れる counterexample を unit/integration test にする。
- [x] hard check 全通過時だけ arbitrage-free と表記する。

### Task 15: vol 19 delivery

- [x] `johnhull/volumes/19_inverse_surfaces/` notebook + reference artifacts を作る。
- [x] book/report に calibration、identifiability、fit-vs-arbitrage、variance consistency の図を追加する。
- [x] VAE/diffusion/flow/SBI は `research` config からのみ実行可能にする。
- [x] G2 validation report と acceptance table を作る。

**G2 acceptance:** repricing、識別性、hard checks、variance term consistency、CPU calibration time を同時に報告できる。

---

## G3 — vol 20「Surface Dynamics, Forecasting & Hedging Decisions」

### Task 16: leakage-safe time-series dataset

**Candidate files:**

- `deep_hedge_price/src/deep_hedge_price/volatility_data.py`
- `deep_hedge_price/src/deep_hedge_price/walk_forward.py`
- `deep_hedge_price/tests/test_walk_forward.py`

- [x] target を `log(RV)` 1/5/21 日、surface latent、future RV に分ける。
- [x] purged expanding/rolling splits と horizon overlap audit を実装する。
- [x] scaler、PCA/sequence scaler は各 train window のみで fit する。
- [x] redistributable data が未確定でも synthetic/fixture だけで完了可能にする。

### Task 17: baseline → challenger → research track

- [x] persistence、EWMA/GARCH、Log-HAR、regularized linear を必須実装する。
- [x] HARNet/TCN、小型 LSTM、小型 encoder-only Transformer を同じ split で比較する。
- [x] QLIKE/RMSE/MAE と block-bootstrap CI を horizon/regime 別に出す。
- [x] foundation model は local/optional zero-shot adapter に限定し、download を既定経路へ入れない。
- [x] conditional diffusion は scenario diagnostics と hard surface check を通し、point forecast と混同しない。

### Task 18: hedge capstone と vol 20 delivery

- [x] surrogate → calibration → forecast → hedge の共通 scenario を作る。
- [x] Phase 1 positions を common paths/premium/cost で評価する adapter contract を実装する。
- [ ] 実 Phase 1 policy と delta、delta-gamma、no-hedge を比較する（positions 未供給のため `not_evaluated`）。
- [x] P&L、hedging error、VaR/CVaR、turnover、no-trade region を報告する。
- [x] attention は diagnostic とし、permutation/occlusion/Integrated Gradients と安定性を照合する。
- [x] `johnhull/volumes/20_surface_dynamics/`、book/report、G3 validation report を作る。

**G3 acceptance:** 複雑モデルが Log-HAR に勝たなくても、leakage-free な統計・経済比較が再現できる。

---

## G4 — A6: vol 21 SPX/VIX + vol 22 0DTE

G3 完了後に公開 API と data policy を再確認し、torch-free `hullkit` の公開モジュールと
synthetic-offline reference artifact として実装した。

### vol 21 scope

- [x] owner audit: `rough_volatility` の既存 rBergomi/Heston/Hawkes と重複しない境界を決める。
- [x] 主モデルを 4-factor PDV、比較を AFV/rough Heston と quintic OU に固定する。
- [x] SPX IV、VIX futures/options、variance term structure の joint objective を作る。
- [x] nested MC teacher と learned surrogate の差・速度を測る。
- [x] signature model、perturbed optimal transport は research-only とし、core 経路から分離する。

### vol 22 scope

- [x] trading calendar、session、holiday、timestamp、settlement convention を先に実装する。
- [x] variance clock `dτ = w(t) dt` と隣接 expiry の total variance consistency を検査する。
- [x] FOMC/CPI 等 scheduled jump を event/non-event split で評価する。
- [x] open/midday/close の時刻依存 jump intensity と SV+jump teacher を実装する。
- [x] DML/PIDE surrogate は teacher 完成後の research track とする。
- [x] dealer-flow の因果を pricing model から主張しない。

**G4 acceptance:** joint SPX/VIX と 0DTE の双方で price/Greek/time-of-day/OOD が再現可能。

---

## G5 — A7: vol 23 RFR & Post-LIBOR Smiles

**Implemented public modules:** `hullkit.rfr`, `hullkit.rfr_options`, `hullkit.sabr_normal`。

- [x] exact daily compounding、lookback、lockout、observation shift、in-advance/in-arrears payoff を TDD 実装する。
- [x] zero-vol と continuous-limit の hand-check を固定する。
- [x] SOFR/TONA curve、futures-forward convexity、multi-curve/basis を追加する。
- [x] scheduled policy jump と collateral currency を scenario として分離する。
- [x] Bachelier → shifted/free-boundary SABR → MC/quadrature teacher の model ladder を作る。
- [x] Hagan 近似の long maturity/high vol/wing error と裁定診断を grid で報告する。
- [x] Bartlett delta と sticky-strike delta を hedge test で比較する。
- [x] Deep XVA/SIMM/MVA は既存 `hullkit.xva` への handoff に留める。
- [x] `johnhull/volumes/23_rfr_post_libor/`、book/report、G5 validation report を作る。

**G5 acceptance:** market convention、離散複利、curve、smile の各層を独立検証できる。

---

## G6 — A8a: vol 24 Crypto Perpetuals, Liquidation & AMMs

**Implemented public modules:** `hullkit.perpetuals`, `hullkit.liquidation`, `hullkit.amm`。

- [x] linear/inverse/quanto の payoff と P&L sign convention を hand-check する。
- [x] index/mark/last price と funding cash flow を別 state として持つ。
- [x] basis-feedback、funding cap/clamp、settlement interval を deterministic baseline で検証する。
- [x] initial/maintenance margin、liquidation fee、insurance fund、bankruptcy price を ledger 化する。
- [x] forced sale、auction、socialized loss、ADL の waterfall を同じ stress path で比較する。
- [x] oracle age、mark-index dislocation、latency/manipulation shock を入れる。
- [x] CPMM/concentrated liquidity、fees、LVR を rebalancing baseline と比較する。
- [x] dynamic fee は LVR reduction と fee compensation を別指標にする。
- [x] October 2025 型 cascade は synthetic fixture とし、実市場再現と表現しない。
- [x] `johnhull/volumes/24_crypto_market_structure/`、book/report、G6 validation report を作る。

**G6 acceptance:** 全 cash flow が conservation/solvency identity と一致し、stress 後の fund/ADL 状態を追跡できる。

---

## G7 — A8b: vol 25 Carbon, Weather & Renewable PPAs

**Implemented public modules:** `hullkit.carbon`, `hullkit.weather`, `hullkit.ppa`。

- [x] carbon futures option の GBM/Heston baseline と SV+jump challenger を作る。
- [x] return/variance/jump risk premium の感度を分ける。
- [x] temperature の trend/seasonality、OU、fOU long memory を比較する。
- [x] non-traded weather index の premium principle を明示する。
- [x] location/station/index mismatch の basis risk を測る。
- [x] fixed、pay-as-produced、floor/collar PPA payoff を形式化する。
- [x] electricity price × wind/solar generation の相関、shape/volume/profile risk を scenario 化する。
- [x] fair value、cash-flow-at-risk/CVaR、hedge residual を別に報告する。
- [x] storage real option は research track とし、PPA core を遅延させない。
- [x] `johnhull/volumes/25_climate_energy/`、book/report、G7 validation report を作る。

**G7 acceptance:** 非完備市場の仮定と basis risk を隠さず、premium/hedge sensitivity が再現できる。

---

## G8 — Full Integration and Release Gate

- [x] vol 18–25 の notebook は committed reference artifact だけで表示できる。
- [x] `johnhull/ROADMAP.md` の各 volume status と実ファイルが一致する。
- [x] book TOC、overview、cross-links、citations、limitations を release contract に登録する。
- [x] portal registry/page/count と全 figure builder の検査を release verifier に実装する。
- [x] 生成された全 release portal HTML が外部 URL を含まないことを検査する。
- [x] vol 18–25 に新しい CDN/remote data dependency を追加せず、RequireJS を vendoring する。
- [x] legacy book の既存 MathJax CDN 例外を manifest に限定・明示する。
- [x] hullkit は torch-free、deep_hedge checkpoint は ignored、market data license は明示済み。
- [x] project-scoped tests、lint、notebook execution、book/report build を全て fresh run する。
- [x] full-workspace test は最後に一度だけ実行し、無関係な既存 failure は分離して報告する。
- [x] research track を既定無効・core gate 非依存にする。
- [x] final validation matrix、残存 model risk、未査読研究の扱いを文書化する。
- [x] release files を commit し、`make hull-release-check HULL_RELEASE_FLAGS=--require-tracked` を通す。
- [x] 明示承認後に remote push する。

---

## Deliverable Matrix

| Volume | Core code | Notebook | Portal | Gate artifact |
|---:|---|---|---|---|
| 18 | pricing data/model/Greeks/hard checks | ML surrogate | error/Greek/no-arb/speed | G1 `VALIDATION.md` |
| 19 | calibration/SSVI/joint variance | inverse & surfaces | fit/identifiability/variance | G2 validation |
| 20 | walk-forward/baselines/challengers | dynamics & hedge | forecast/economic metrics | G3 validation |
| 21 | PDV/AFV/quintic comparison | SPX/VIX | joint fit/risk/speed | G4 validation |
| 22 | clock/events/SV+jump | 0DTE | intraday/expiry/Greek | G4 validation |
| 23 | RFR payoff/curve/SABR | post-LIBOR | convention/convexity/model risk | G5 validation |
| 24 | perpetual/liquidation/AMM | crypto structure | funding/solvency/LVR | G6 validation |
| 25 | carbon/weather/PPA | climate & energy | premium/basis/PPA risk | G7 validation |

## Suggested Commit Boundaries

実装時に commit が許可された場合、task を跨いでまとめない。

```text
docs(johnhull): formalize beyond-Hull ownership and gates
feat(deep_hedge_price): add versioned pricing artifact contract
feat(hullkit): add surrogate hard-validation checks
feat(deep_hedge_price): add Black-Scholes pricing datasets and baseline model
feat(deep_hedge_price): add differential pricing and Greek evaluation
feat(hullkit): add uncertainty-aware surrogate teachers
feat(deep_hedge_price): add pricing diagnostics and offline report
docs(johnhull): add volume 18 ML surrogates
```

G2 以降も volume/gate 単位で同じ規則を使う。G8 の remote push は明示承認後に実施した。
