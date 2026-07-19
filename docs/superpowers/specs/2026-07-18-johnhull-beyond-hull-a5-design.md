# johnhull「Hull の先」A5–A8 実装設計

- 日付: 2026-07-18
- ステータス: 実装計画用の確定設計（コード未着手）
- 対象: `/home/kazumasa/projects/johnhull`
- 親提案: `docs/superpowers/specs/2026-07-18-johnhull-beyond-hull-options.md`
- 実装計画: `docs/superpowers/plans/2026-07-18-johnhull-beyond-hull-a5.md`

## 1. 結論

既存 vol 1–17 の「理論 → 数値検証 → 可視化 → notebook/book/report」を保ち、
次の 8 巻を stage gate 付きで追加する。

| Wave | Volume | 主題 | 中核 |
|---|---:|---|---|
| A5 | 18 | Theory-Guided Surrogates & Greeks | baseline、Differential ML、OOD、hard checks |
| A5 | 19 | Inverse Problems & Arbitrage-Aware Surfaces | two-step calibration、SSVI、joint variance calibration |
| A5 | 20 | Surface Dynamics & Hedging Decisions | Log-HAR、時系列モデル、下流 hedge 評価 |
| A6 | 21 | Joint SPX/VIX Models | 4-factor PDV、AFV/rough Heston、quintic OU |
| A6 | 22 | 0DTE Clocks, Jumps & Greeks | variance clock、scheduled events、SV+jump |
| A7 | 23 | RFR & Post-LIBOR Smiles | 離散複利、政策 jump、multi-curve、SABR model risk |
| A8a | 24 | Crypto Perpetuals, Liquidation & AMMs | funding、mark/oracle、insurance fund、ADL、LVR |
| A8b | 25 | Carbon, Weather & Renewable PPAs | carbon SV+jump、weather basis risk、PPA shape/volume risk |

一括実装は禁止する。まず G0（契約確定）と G1（vol 18）だけを実行し、各 gate の
acceptance を満たしてから次へ進む。

## 2. 設計原則

1. **単純な基準器を先に置く。** 解析解、既存数値法、線形・計量モデルを必須 baseline とする。
2. **正本を分ける。** 金融教師・hard validation は `hullkit`、PyTorch 学習・checkpoint・評価基盤は
   `deep_hedge_price`、教材・統合は `johnhull` が持つ。
3. **`hullkit` は torch-free のままにする。** `import hullkit` と既存 184 tests は PyTorch なしで成立させる。
4. **既定経路は synthetic、CPU、offline。** GPU、live training、市場データは optional target に分ける。
5. **研究トラックを本線と分離する。** preprint のモデルは mature baseline に勝ち、再現可能な場合だけ中核へ昇格する。
6. **予測精度だけで完了判定しない。** Greeks、無裁定、較正、hedging P&L、CVaR、turnover、計算時間を含める。
7. **negative result を成果として許す。** 複雑モデルが baseline に勝たなくても、検証が再現可能なら巻を完了できる。

## 3. システム境界

```text
hullkit (NumPy/SciPy; torch-free)
  ├─ analytic / COS / MC teacher
  ├─ Greeks and financial identities
  └─ hard validation
          │ JSON + NPZ (schema_version, fingerprints, uncertainty)
          ▼
deep_hedge_price (PyTorch)
  ├─ dataset loader and split audit
  ├─ price-only / multi-task / differential models
  ├─ checkpoint and experiment manifests
  └─ optional CUDA benchmark
          │ small committed reference metrics / slices only
          ▼
johnhull
  ├─ vol 18–25 notebook builders
  ├─ Jupyter Book integration
  └─ offline report figures and narrative
```

禁止事項:

- `hullkit` から `deep_hedge_price` または torch を import しない。
- `deep_hedge_price` の checkpoint を `johnhull` に複製しない。
- `rough_volatility` の 100k-path 級出力や市場データを repo にコピーしない。
- notebook build 中に training、web download、GPU 検出を行わない。

## 4. Artifact 契約

### 4.1 Dataset manifest

JSON manifest は最低限次を持つ。

```json
{
  "schema_version": 1,
  "artifact_kind": "pricing_dataset",
  "model": "black_scholes",
  "teacher_method": "analytic",
  "parameterization": "dimensionless_v1",
  "seed": 1210,
  "split_fingerprints": {
    "train": "sha256:...",
    "validation": "sha256:...",
    "test": "sha256:...",
    "ood": "sha256:..."
  },
  "overlap_count": 0,
  "arrays": "pricing_dataset.npz",
  "generator_version": "...",
  "git_sha": "...",
  "created_at_utc": "..."
}
```

NPZ は入力、price、Greek labels、standard error/CI、split id を保持する。配列名、shape、dtype、単位は
schema test で固定し、不足項目を loader が推測して補わない。

### 4.2 Evaluation manifest

- dataset/checkpoint/config fingerprint
- seed と device
- price/Greek error の bucket 集計
- hard-check の violation rate と最大量
- OOD shell 指標
- latency/throughput と warm-up 条件
- acceptance の pass/fail と理由

`arbitrage_free=true` は、適用対象の全 hard check が文書化した tolerance 内で通ったときだけ許す。

### 4.3 Committed reference artifact

`johnhull` に commit するのは quick profile から作る小型 JSON/NPZ のみとする。
checkpoint、生パス、full dataset は `deep_hedge_price/artifacts/` に置き、gitignore を維持する。

## 5. A5 の実装設計

### 5.1 vol 18 — Surrogates & Greeks

必須比較:

1. analytic Black–Scholes
2. polynomial または spline
3. small price-only MLP
4. price + direct Greek heads
5. Differential ML
6. analytic baseline に対する residual correction

Heston/COS と Monte Carlo labels は teacher uncertainty を持つ第 2 段階とする。Deep BSDE、PINN、
DeepONet/FNO は研究トラックであり、G1 の完了条件にしない。

### 5.2 vol 19 — Calibration & Surfaces

- 主方式: forward surrogate + 既存 optimizer の two-step calibration
- baseline: Heston/SABR/rBergomi teacher、SSVI または凸な call-price surface
- ablation: direct inverse map
- 必須追加: IV surface と variance term structure の共同目的

目的関数は概念的に次とする。

\[
L(\theta)=L_{\mathrm{IV}}(\theta)+\lambda_{\mathrm{var}}L_{\mathrm{variance}}(\theta)
+\lambda_{\mathrm{reg}}R(\theta).
\]

`lambda_var` の感度と fit/variance consistency の Pareto frontier を報告する。diffusion、VAE、flow、
simulation-based inference は research profile に隔離する。

### 5.3 vol 20 — Dynamics & Hedging

- 必須 baseline: persistence、EWMA/GARCH、Log-HAR、regularized linear
- challenger: TCN/HARNet、小型 LSTM、小型 encoder-only Transformer
- research: time-series foundation model、conditional diffusion
- split: purged expanding/rolling walk-forward。PCA/標準化を各 train window 内で fit する。
- 最終判断: QLIKE/RMSE ではなく、共通 test path・premium・cost 下の hedging P&L/CVaR/turnover

foundation model は Log-HAR に対する challenger とし、必須依存・既定 download にしない。

## 6. A6–A8 の実装設計

### 6.1 vol 21 — SPX/VIX

- 主モデル候補: 4-factor PDV
- 比較 1: AFV/rough Heston
- 比較 2: quintic OU / Gaussian polynomial
- signature model と perturbed optimal transport は研究トラック
- IV surface に加え VIX futures/options と variance term structure を共同検証する。

モデル owner は A6 設計 gate で `hullkit` と `rough_volatility` の既存責務を比較して決め、二重実装しない。

### 6.2 vol 22 — 0DTE

実装順は calendar convention → intraday variance clock → scheduled event → SV+jump teacher → DML surrogate。
open/midday/close、event/non-event、隣接満期を分けて評価する。dealer-flow の実証結果は背景説明とし、
価格モデルから市場因果を主張しない。

### 6.3 vol 23 — RFR

離散日次複利を正本にし、continuous approximation は比較対象にする。compounded-in-arrears、lookback、lockout、
observation shift、FOMC/ECB scheduled jump、multi-curve、担保通貨を順に追加する。

smile 層は Bachelier → shifted/free-boundary SABR → high-precision MC/quadrature teacher の順にし、
Hagan 近似の長期・高 vol・wing 誤差と裁定違反を明示する。Deep XVA は vol 23 の必須範囲外とする。

### 6.4 vol 24 — Crypto

契約 payoff（linear/inverse/quanto）、index/mark/last price、funding、margin、liquidation、insurance fund、ADL、
oracle latency/manipulation、AMM/LVR を一つの solvency ledger で結ぶ。

中核は決定論的 cash-flow identity と stress simulator。無限期間 BSDE、risk-based ADL、dynamic AMM fee、
AMM-token option は研究トラックとする。

### 6.5 vol 25 — Climate & Energy

1. carbon allowance futures options: stochastic volatility + jumps
2. weather contracts: seasonality、OU/fOU、非完備市場、basis risk
3. renewable PPA: fixed/pay-as-produced/floor/collar、shape/volume/profile risk

非取引可能 underlying では一意な risk-neutral price を仮定せず、market price of risk、utility/actuarial premium、
price-generation correlation に対する感度を必須で示す。

## 7. Stage Gates

| Gate | 完了条件 | 停止条件 |
|---|---|---|
| G0 | owner、artifact schema、依存、公開 API、data policy を承認 | owner または dependency が未確定 |
| G1 | vol 18 の baseline/DML/OOD/no-arb/CPU report | 3 回修復後も dataset/評価契約が不安定 |
| G2 | vol 19 の two-step、joint variance、surface hard checks | repricing と variance consistency を両立不能 |
| G3 | vol 20 の leakage-safe forecast と hedge 比較 | split audit または economic evaluation 不成立 |
| G4 | vol 21–22 の共同較正と 0DTE clock/jump | データ/teacher の再現性不足 |
| G5 | vol 23 の離散 RFR と SABR diagnostics | convention test または極限 test 不成立 |
| G6 | vol 24 の cash-flow/solvency invariants | oracle/liquidation accounting が未定義 |
| G7 | vol 25 の incomplete-market sensitivity | premium principle と basis risk が未定義 |
| G8 | vol 18–25 の book/report/offline integration | 必須 artifact が live training/download に依存 |

各 gate は失敗も記録する。3 回修復しても acceptance を満たせない場合は、問題、試行、縮小案を残して停止する。

## 8. 既定の非対象

- 市場収益性や alpha の主張
- 有料・再配布不可データの同梱
- production trading、execution、order routing
- GPU 必須化
- すべての最新 preprint の実装
- A5 完了前の A6–A8 一括着工
