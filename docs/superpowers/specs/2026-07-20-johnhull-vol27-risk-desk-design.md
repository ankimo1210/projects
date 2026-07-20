# johnhull vol 27 — 日次リスク管理デスク（VaR/ES 発展編）設計

- 日付: 2026-07-20
- ステータス: 承認済み設計（実装前）
- 対象: `/home/kazumasa/projects/johnhull`（hullkit 新規 4 モジュール + volumes/27_risk_desk）
- ブランチ: `codex/johnhull-inflation-jgbi` に積む（vol 26 の後続）
- 背景: vol 08（Hull 11e Ch.22）は VaR/ES の定義・分散共分散法・ヒストリカル・
  バックテスト概念・オプション VaR・FRTB への移行文脈までをカバー済み。一方、
  銀行デスクの日次実務で使う検定統計・テールモデリング・リスク分解・PnL explain は
  未実装。本巻はこのギャップのうち**日次リスク管理軸**を一巻で埋める。
  FRTB IMA（liquidity horizon 別 ES 集約・NMRF・P&L attribution・IMA/SA 比較）は
  スコープ外とし、将来巻（vol 28 候補）として ROADMAP に明記する。

## 1. 目的と成功基準

**目的:** 「そのVaRは信用できるか、外れたらどう直し、リスクは誰のものか」に
検証済みコードで答える教材巻を追加する。

**成功基準:**

1. hullkit に `var_backtest` / `tail_risk` / `risk_allocation` / `pnl_explain` の
   4 モジュールが追加され、公開 API docstring 100% と MODEL_INDEX 掲載 +
   参照解決を guard tests が保証する。
2. vol 27 notebook が artifact-only で実行でき、G8 式 acceptance check
   （§4 の 11 項目）を `frontier_acceptance.py` がコミット済み配列から再計算して
   全 PASS する。
3. 既存の全ゲート（hullkit suite・`make hull-artifacts-check` /
   `hull-notebooks-check` / `hull-release-check`・ruff）が引き続き通る。
4. 検証方針は vol 18–26 と同じ: **PASS = integration・数値恒等式・再現性のみ**。
   データは全て synthetic。モデル性能・市場予測力の承認ではない。

## 2. スコープ

含む（4 トピック群、いずれも承認済み）:

1. **バックテスト検定統計** — Kupiec POF・Christoffersen 独立性 / 条件付き
   カバレッジ・Basel traffic light の定量化（ゾーン確率と乗数）。
2. **FHS + EVT** — EWMA/GARCH フィルタリング付きヒストリカル・シミュレーション
   （既存 `hullkit.volatility` の EWMA/GARCH を再利用）、POT/GPD による
   テール VaR/ES、mean excess による閾値選択。
3. **分解・資本配賦** — Marginal/Component/Incremental VaR・ES、Euler 配賦の
   加法性、正規解析とシミュレーション両建て。
4. **デスクラン capstone** — 合成ブック（株・オプション・金利）の
   リスクファクターマッピング → 日次 PnL explain（delta-gamma-vega vs
   full revaluation）→ 限度管理 → 統合リスクレポート。

含まない:

- FRTB IMA 一式（LH 別 ES・stressed ES scaling・NMRF・P&L attribution・
  IMA eligibility・SA 比較）→ vol 28 候補。
- 市場・信用・流動性・オペレーショナルリスクの統合枠組み。
- 実データ・市場キャリブレーション（synthetic-offline を維持）。
- Hull RMFI の例題ピン（G8 式 acceptance のみで検証）。

## 3. 成果物

### 3.1 hullkit 新規モジュール（torch-free、numpy/scipy のみ）

既存 `risk.py`（vol 08 の Hull ピン付き）と `volatility.py` は**変更しない**。

| モジュール | 公開 API | 内容 |
|---|---|---|
| `var_backtest.py` | `exceedance_series`, `kupiec_pof`, `christoffersen_independence`, `christoffersen_cc`, `basel_traffic_light` | LR 統計量 + p 値、`LR_cc = LR_pof + LR_ind`、ゾーン判定（binomial 累積確率）と乗数 3.0→4.0 |
| `tail_risk.py` | `filtered_historical_var_es`, `fit_gpd_pot`, `evt_var_es`, `mean_excess` | devol→revol の FHS、GPD の MLE（POT）、GPD 閉形式 VaR/ES、閾値診断 |
| `risk_allocation.py` | `marginal_var_normal`, `component_var_normal`, `incremental_var`, `euler_es_components` | 正規解析の ∂VaR/∂w と Euler 成分、with/without の Incremental、シミュレーション版 Euler ES（テール条件付き期待値） |
| `pnl_explain.py` | `map_to_factors`, `delta_gamma_vega_pnl`, `pnl_attribution`, `limit_utilization`, `desk_report` | ファクターマッピング、Taylor P&L、explained/unexplained 分解、限度消化率、日次レポート組立 |

テスト: `test_var_backtest.py` / `test_tail_risk.py` / `test_risk_allocation.py` /
`test_pnl_explain.py`。

エラー方針: α∈(0,1)・GPD fit の収束・閾値超過数下限などの入力検証で
`ValueError` を明示的に投げる。GPD の ξ≥1（ES 発散域）はガードして明示エラー。

### 3.2 ボリューム `volumes/27_risk_desk/`

- `build_27_risk_desk_notebook.py`（決定的 cell-id、ruff exclude 対象）
- `risk_desk.ipynb`（artifact-only 実行、教材文は日本語）
- `reference/metrics.json` + `reference/risk_desk_scenarios.npz`
  （固定 seed で `build_frontier_artifacts.py --volume 27` が生成、
  fingerprint 付き）
- `VALIDATION.md`（G8 様式）

Notebook セル構成:

| セル群 | 内容 |
|---|---|
| 00–02 | イントロ（vol 08 との接続・本巻の問い）・synthetic データ設定 |
| 03–07 | バックテスト検定（Kupiec / Christoffersen / traffic light、検定サイズと検出力の可視化） |
| 08–11 | FHS（ボラクラスタ下の plain HS 違反クラスタリング → FHS のカバレッジ改善） |
| 12–15 | EVT（mean excess → GPD fit → EVT VaR/ES vs 経験分位点） |
| 16–19 | 分解・配賦（Component/Incremental の使い分け、Euler 加法性、ポジション削減の意思決定例） |
| 20–24 | デスクラン capstone（マッピング → PnL explain → 限度チェック → 統合レポート表） |
| 25–27 | verification セル・演習・まとめ |

## 4. Acceptance checks（`frontier_acceptance.py` 追加分）

コミット済み配列から再計算（JSON のフラグを信用しない）。

| Check | 基準 |
|---|---|
| `kupiec_size_calibration` | iid 違反系列での棄却率が名目サイズと整合（binomial SE 基準 z < 3） |
| `christoffersen_detects_clustering` | Markov クラスタ違反系列の p 値が独立系列より有意に小さい |
| `fhs_constant_vol_identity` | 定数ボラの FHS ≡ plain HS（≤1e-12） |
| `fhs_coverage_improvement` | GARCH 生成リターンで FHS の違反率が plain HS より名目に近い |
| `gpd_parameter_recovery` | 合成 GPD テールから ξ, β を許容誤差内で回復 |
| `evt_var_es_identity` | GPD 閉形式 ES–VaR 恒等式 ES = (VaR + β − ξu)/(1−ξ)（≤1e-12） |
| `euler_additivity_normal` | 正規解析で Σ component = total VaR（≤1e-12） |
| `marginal_fd_consistency` | 解析 marginal と有限差分の一致 |
| `euler_es_additivity_sim` | シミュレーション Euler ES 成分の和 = total ES（構成上厳密） |
| `pnl_explain_taylor_ordering` | 小変動で delta-gamma-vega 残差 ≪ delta-only 残差 |
| `desk_report_reproducible` | capstone レポート数値の決定的再現 |

数値許容値（GPD 回復誤差など表中で明示していないもの）は、固定 seed の実測に
余裕を持たせて実装時に確定し acceptance 表へ記録する（vol 18–26 の慣行）。

## 5. 配線・ドキュメント

- `release_manifest.json` に vol 27 エントリ（vol 26 と同形式）:
  `portal_page` は**新規ページ `risk_management`**（既存 frontier ページに risk 系が
  ないため、`johnhull/report/report_builder/figures.py` に `BookMeta` を追加し
  既存パターンで配線）、`portal_figures` 4 点（traffic light・FHS vs HS
  カバレッジ・GPD テールフィット・component 配賦バー）、
  `semantic_sources` / `semantic_tests` に新規 4 モジュールと対応テスト、
  `references` に metrics.json + npz。
- `MODEL_INDEX.md` §6（Risk & credit）に 4 モジュール分の行を追加。
- `ROADMAP.md` に vol 27 追加 + FRTB IMA を vol 28 候補として明記。
- `README.md` 巻一覧更新。

## 6. 検証ゲート（完了条件、すべて repo root から）

1. `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests johnhull/report/tests`
2. `uv run --no-sync python johnhull/scripts/build_frontier_artifacts.py --volume 27`
3. `uv run --no-sync --package hullkit python johnhull/volumes/27_risk_desk/build_27_risk_desk_notebook.py`
4. `make hull-artifacts-check` / `make hull-notebooks-check` / `make hull-release-check`
5. ruff（johnhull スコープ）

## 7. リスク・留意点

- 検定の検出力チェックは確率的 → 固定 seed + 余裕のある閾値で flaky を回避
  （vol 18–26 の z < 3 方式を踏襲）。
- GPD MLE は小標本で不安定 → 合成データの超過数を十分確保（≥500）し、
  収束チェックを実装側でガード。
- notebook 実行中の重い計算は禁止 → 検出力シミュレーション等は builder ではなく
  `build_frontier_artifacts.py` 側で実行し、notebook は artifact を読むだけ。
- 並行セッションとのブランチ共有によるコミット混入に注意（johnhull 以外の
  ファイルをステージしない）。
