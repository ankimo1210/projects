# quantkit モデル層強化 設計書 — 反証力 → 幅

2026-09-06。対象は `quantkit/`（`src/quantkit`）。Phase 3「レベルアップ」
（2026-08、commit 2b4f6e34 まで）の後続。

## 1. 目的

quantkit のモデル層を「**ベースラインに勝ったと言える根拠を出せる**」状態にし、
そのうえでモデルの幅（LightGBM・分類/meta-labeling・系列モデル・Tier4 接続）を
広げる。順序は **反証力 → 実データ検証 → 幅** で固定する。幅を先に広げても、
勝ち負けを判定する装置が無ければ候補が増えるだけで結論が出ないため。

到達点:

1. 任意のモデル比較に対して DSR・PBO・IC 差の信頼区間の 3 点で「勝ち／負け」を
   機械的に判定でき、負けも leaderboard に残る。
2. 実データ（米株 ETF/大型株・crypto）で Tier0–3 + 合成モデルを回した記録が
   fingerprint 付きでリポジトリに残る。
3. 上記の装置に LightGBM・分類器・meta-labeling・LSTM/TCN・Tier4 信号が
   同じ契約で乗る。

## 2. 点検で分かった事実（2026-09-06）

テストは 159 passed / 7 skipped（9.2s）。以下はコードと NB の出力で確認したもの。

| # | 箇所 | 事実 | 証拠 |
|---|---|---|---|
| 1 | `models/ensemble.py` `StackingModel.fit` | OOF ブロック分割に purge/embargo が無い。隣接ブロックのラベル（horizon 分）が被り meta 特徴がリークする | NB16: stacking の OOS rank IC −0.0265、メンバー ridge は +0.0147 |
| 2 | `models/uncertainty.py` `ConformalModel.fit` | train/calib 境界に purge が無い。横断パネルでは同一日の残差が相関し、時変ボラで exchangeability が崩れる | NB16: 被覆 0.822（目標 0.90） |
| 3 | `configs/model_config.yaml` | どこからも読まれていない。lightgbm/xgboost/lstm/tft/timesfm 等を列挙するが実装は ridge/lasso/EN/RF/GBR/MLP/AR/naive/chronos のみ | `grep model_config` が src/tests/notebooks で 0 件 |
| 4 | `models/foundation.py` | Tier4 `Forecaster` は横断ハーネス（`walk_forward_predict`/backtest）に未接続 | NB09 自身が「追加ステップが要る」と記載 |
| 5 | NB07/08/09 | 出力が保存されていない（README は「全実走」） | outputs=0。出力があるのは NB16 のみ |
| 6 | NB07/08/09/16 | モデル評価は全て合成データ。実データでモデル層を回した記録が無い | 全 NB が `rng.normal` で価格を生成 |

設計上の不足: モデル比較の統計検定が無い、fold 内 nested tuning が無い、
`fit` に `sample_weight` が無い、分類器/meta-labeling が無い（`labels` に
binary/ternary/triple_barrier はある）、目的変数変換が無い、実験記録が無い。

環境: torch 2.11+cu128 と RTX 5080 が使える。lightgbm/xgboost/optuna/shap は未導入。

## 3. 決定事項

| 論点 | 決定 |
|---|---|
| 主眼 | 反証力 → 幅の順 |
| 実データのユニバース | 米株 ETF/大型株（yfinance）+ crypto（Binance）。無キーで実証済みのソースのみ |
| 追加依存 | `lightgbm` を必須に、`torch` を optional extra `quantkit[deep]` に。xgboost/optuna/shap は入れない |
| 配置 | 検定は `backtest/stats.py`、モデルは `models/`、leaderboard と記録は新規 `experiments/`（案 A）。`evaluation/` への集約（案 B）は不採用 |
| 「勝ち」の定義 | DSR ≥ 0.95 かつ IC 差の bootstrap CI が 0 を跨がない かつ PBO < 0.5。3 条件すべて |
| 作業方法 | `~/projects` は複数セッションが index を共有するため、専用 worktree + ブランチで実装 |

## 4. Phase 1 — 反証力

### 4.1 `backtest/stats.py`（新規）

- `deflated_sharpe(returns, n_trials, sr_var, periods=252) -> float`
  Bailey & López de Prado (2014)。$N$ は leaderboard の候補数（試行数を隠さない）、
  `sr_var` は候補間の Sharpe の分散。
  $$\text{DSR}=\Phi\!\left[\frac{(\widehat{SR}-SR_0)\sqrt{T-1}}{\sqrt{1-\hat\gamma_3\widehat{SR}+\frac{\hat\gamma_4-1}{4}\widehat{SR}^2}}\right],\qquad
  SR_0=\sqrt{V[\widehat{SR}_n]}\Big[(1-\gamma)\Phi^{-1}(1-\tfrac1N)+\gamma\,\Phi^{-1}(1-\tfrac{1}{Ne})\Big]$$
  $\gamma$ はオイラー定数。`min_track_record_length(returns, target_sr, alpha)` も同梱。
- `pbo(is_scores, oos_scores) -> PBOResult(pbo, logits)`
  CSCV。`is_scores`/`oos_scores` は (combination × candidate) の DataFrame。
  各 combination で IS 最良候補の OOS 順位 $\bar\omega$ を取り
  $\lambda=\log\frac{\bar\omega}{1-\bar\omega}$、PBO $=P(\lambda\le 0)$。
  fold の生成は既存 `combinatorial_purged(n_groups, k_test=n_groups/2)` を使い、
  補集合を OOS とする（`backtest/split.py` に `pbo_folds(index, n_groups, horizon, embargo)`
  を追加し、`(is_fold, oos_fold)` の対を返す。両側とも purge+embargo 済み）。
- `bootstrap_ic(pred, label, *, n_boot=1000, block=21, ci=0.95) -> ICResult(mean, lo, hi, n_dates)`
  日次 rank IC 系列（`models.importance.rank_ic_by_date(pred, label) -> Series` を
  新設し、既存 `rank_ic` はその平均とする）の circular block bootstrap。
- `ic_difference(pred_a, pred_b, label, **bootstrap) -> ICResult`
  **対応のある**日次 IC 差（同じ日付の IC 同士を引く）の bootstrap CI。
- `sharpe_difference(returns_a, returns_b, **bootstrap) -> ICResult`
  同じ block bootstrap で Sharpe 差の CI。

`ICResult` は `beats_zero: bool`（CI が 0 を跨がない）を持つ。

### 4.2 `models/` のリーク修正

- `backtest/split.py`: `purged_block_folds(index, n_splits, horizon=0, embargo=0) -> list[Fold]`
  を公開。`index` を `n_splits` 個の連続ブロックに分け、各ブロックを test、
  二側 purge+embargo 後の残りを train とする（`_forbidden_positions` を再利用）。
- `StackingModel(base_models, meta_model, *, n_splits=5, horizon=0, embargo=0)`
  OOF を `purged_block_folds` で作る。既定 `horizon=0` は後方互換だが、docstring
  でラベル horizon を渡すよう明記。
- `ConformalModel(base, *, alpha, calib_fraction, horizon=0, scale=None)`
  train/calib 境界に `horizon` 本の purge。`scale="<feature name>"` で非適合度を
  $|y-\hat y|/X[\text{scale}]$ に正規化（locally weighted conformal）、区間幅も同じ
  列で伸縮。`coverage_by_date(X, y) -> Series` を追加し被覆の時系列を返す。

### 4.3 `models/tuning.py`（新規）

`TunedModel(factory, param_grid, *, n_inner=3, horizon=0, embargo=0, scorer=rank_ic, mode="grid", n_iter=None, random_state=0)`

- `Model` 契約。`fit(X, y)` の中で**学習日付だけ**に `walk_forward`（purge 付き、
  `n_inner` 個の test ブロック）を切り、各パラメータ集合を内側 OOS でスコア化、
  最良を全学習期間で再学習する。外側の `walk_forward_predict` は無変更のまま
  nested CV になる。
- `best_params_`、`inner_scores_`（DataFrame: params × inner fold）を保持。
- `mode="random"` は `n_iter` 個を `random_state` で抽出。
- コストは `|grid| × n_inner` fits / 外側 fold。docstring に明記。

### 4.4 sample_weight

- `Model.fit(self, X, y, sample_weight=None)`。`SklearnModel` は推定器が
  `sample_weight` を受けるときだけ渡す（`inspect.signature` で判定）。baseline は
  無視。`EnsembleModel`/`StackingModel`/`RankModel`/`TunedModel` は伝播。
- `walk_forward_predict(..., sample_weight=None)`、`mda_importance(..., sample_weight=None)`
  は fold ごとに切って渡す。
- `models/weights.py`（新規）: `time_decay_weights(index, halflife) -> Series`
  （日付 level で指数減衰、最新 = 1）、`uniqueness_weights(touch_offset) -> Series`
  （triple-barrier の平均ユニークネス。固定 horizon では定数になることを docstring に明記）。

### 4.5 `models/target.py`（新規）

- `vol_scaled_target(fwd, vol)` — `fwd / vol`。`vol` は t 時点の causal 値
  （`features.realized_volatility` 等）。
- `demeaned_target(fwd)` — 日次横断デミーン（市場中立）。

## 5. Phase 1 — 実データ leaderboard（`quantkit/experiments/`、新規）

### 5.1 `experiments/snapshot.py`

`build_snapshot(name, symbols, start, end, *, source, cache=None) -> SnapshotManifest`

- 既存コネクタ（`get_prices` / `BinanceConnector`）と `CacheManager` で取得し、
  `data/experiments/<name>/prices.parquet`（dates × assets の adj_close、前埋めなし）
  と `manifest.json`（銘柄・ソース・取得時刻・parquet の sha256・`quality.assess`
  要約・失敗銘柄）を書く。
- `load_snapshot(name) -> (prices, manifest)`。以後の NB は snapshot だけを読む。
- テストは fake connector でオフライン。

### 5.2 `experiments/leaderboard.py`

`run_leaderboard(prices, candidates, *, features, horizon, folds, cost, quantile=0.3, reference="persist", n_boot=1000, pbo_groups=8) -> LeaderboardResult`

候補ごとに:
1. `make_design(features, forward_return(prices, horizon))`
2. `walk_forward_predict` → OOS 予測
3. `bootstrap_ic` → 平均 IC と CI
4. `cross_sectional_zscore` → `long_short_quantile`（`horizon` 本ごとにリバランス）→
   `run_backtest`（同一 cost・lag=1）→ Sharpe / max DD / turnover

全体で:
- `deflated_sharpe`（$N$ = 候補数、`sr_var` = 候補間 Sharpe 分散）
- `ic_difference`（各候補 vs `reference` 候補）
- `pbo`（`pbo_folds` 上で全候補を再学習し IS/OOS の IC 行列）

`LeaderboardResult.table` は候補 × 指標の DataFrame で、列 `beats_baseline` は
DSR ≥ 0.95 ∧ IC 差 CI が 0 を跨がない ∧ PBO < 0.5。`equal_weight` ベンチも同表に並べる。

### 5.3 `experiments/record.py`

`ExperimentRecord`（dataclass）→ JSON。`fingerprint` = git sha・manifest sha256・
config の sha256・`quantkit`/`sklearn`/`lightgbm`/`torch` の版・実行時刻。
`save(record, path)` / `load(path)`。`reports/experiments/<name>.json` にコミット。

### 5.4 ユニバースと NB17

- `configs/universe.yaml` に `experiments:` を追加。
  - `us`: 既存 `us_etfs` 21 本 + 大型株 約 40（手選び。サバイバーシップバイアスを
    manifest と NB に明記）。
  - `crypto`: Binance USDT 建て 約 20（snapshot 時点の出来高上位を手で列挙。同じく明記）。
- `notebooks/17_real_data_model_leaderboard.ipynb`
  2 ユニバース × horizon ∈ {5, 21} × 候補 {persist[mom], mean, ridge, RF, GBR, MLP,
  ensemble, stacking(purged), LTR, TunedModel(ridge), TunedModel(GBR)}。
  出力付きで保存。結論は「どれが 3 条件を満たしたか／満たさなかったか」の表。

## 6. Phase 2 — 幅

### 6.1 `models/tree.py`

`lightgbm_regressor(n_estimators=300, num_leaves=15, learning_rate=0.05, random_state=0, **kw)`。
`standardize=False`、`verbose=-1`、`n_jobs=-1`。

### 6.2 `models/classify.py`（新規）

- `ClassifierModel(SklearnModel)` — `predict` は二値なら $P(y=1)$、三値なら
  $\sum_k k\,P(y=k)$ を返す（スコアとして横断ハーネスに乗る）。
- `logistic(C=1.0)`, `lightgbm_classifier(**kw)`。
- `MetaLabelModel(primary, secondary)` — `primary` は `Model`（方向 = 予測の符号）。
  `fit` は `binary_label(y * sign(primary.predict(X)))` を `secondary` に学習させる。
  `predict` = sign × $P(\text{correct})$。primary は事前 fit 済みでも、`fit` 内で
  同じ X, y に fit してもよい（引数 `fit_primary: bool`）。

### 6.3 `models/sequence.py`（新規、`quantkit[deep]`）

- `make_sequence_design(features, label, window) -> (X3d, index, y, n_dropped)`
  資産ごとに直近 `window` 行の特徴量を積む。欠損を含む窓は drop（前埋めなし）。
  `index` は `(date, asset)`。
- `sequence_model(arch="lstm"|"gru"|"tcn", *, window, hidden=32, epochs=20, lr=1e-3, batch_size=256, device="auto", random_state=0)`
  `Model` 契約。`fit(X, y)` の X は `make_sequence_design` の出力を包む `SequenceDesign`
  で、`walk_forward_predict` がそのまま使えるよう `.index`（`(date, asset)` MultiIndex）と
  真偽値マスクによる `__getitem__` を持つ。
  学習末尾 10% の日付（`horizon` purge 付き）で early stopping。`device="auto"` は
  cuda があれば使う。`reduce_size_on_cpu` を `model_config.yaml` から読む。
- torch 不在時は `load_foundation` と同じ形の `ImportError`。

### 6.4 Tier4 接続: `models/foundation.py`

`forecaster_signal(prices, make_forecaster, horizon, *, every=21, min_history=252) -> DataFrame`

各資産・各再 fit 日 t で `prices[:t]` だけを使って fit し、次 `horizon` 本の
累積予測リターンを panel に書く。`every` 本ごとに再 fit、間は NaN（前埋めなし）。
出力は dates × assets の信号なので `make_design`（`PersistenceModel`）や
`long_short_quantile` にそのまま入る。Chronos も同じ経路。

### 6.5 `models/registry.py`（新規）と `configs/model_config.yaml` の書き直し

- `from_config(name, overrides=None, cfg=None) -> Model`。
- YAML を実装済みの名前とハイパラに書き直す:
  `tiers.baseline/linear/tree/neural/sequence/foundation`、`optional: [sequence, foundation]`、
  `device`、`cross_validation`（`tuning.n_inner` を追加）。
- 未実装名は利用可能名を列挙して `KeyError`。

### 6.6 NB18

`notebooks/18_model_breadth_lightgbm_sequence_meta.ipynb` — NB17 と同じ snapshot で
lightgbm / meta-label / LSTM・TCN / `forecaster_signal(AR)` を候補に加えて
`run_leaderboard` を再実行。$N$ が増えて DSR の閾値が上がるのをそのまま記録。

## 7. テストと検証

### 7.1 テスト（オフライン・合成、+50〜60 本 → 約 215）

| 対象 | 検証 |
|---|---|
| `deflated_sharpe` | 純ノイズ × N 候補の最良 Sharpe の DSR が低い（< 0.5）。N=1 で通常の PSR に一致 |
| `pbo` | ノイズ候補群で PBO ≈ 0.5（±0.15）。IS/OOS が完全一致なら 0 |
| `bootstrap_ic` / `ic_difference` | 既知 IC の合成で CI が真値を覆う。同一予測の差は CI が 0 を含む |
| `purged_block_folds` | 全 fold が `is_purged` を満たす |
| `StackingModel` | spy factory で OOF 学習行が forbidden zone に無いことを確認 |
| `ConformalModel` | purge で学習日付が calib と `horizon` 以上離れる。heteroskedastic 合成で `scale` 有りが被覆 0.9±0.03、無しが下回る |
| `TunedModel` | 内側 fold が `is_leakage_free`。合成で正しい α を選ぶ。`best_params_` が記録される |
| sample_weight | sklearn へ透過（fake estimator で受信を確認）。baseline は無視。`walk_forward_predict` が fold で切る |
| `weights` / `target` | 減衰の単調性・最新=1。uniqueness の定数性。vol scaling の causal 性 |
| `snapshot` | fake connector で manifest の sha256 が parquet と一致。失敗銘柄が記録される |
| `run_leaderboard` | fake 候補（1 つだけ真の信号）で `beats_baseline` がその候補だけ True |
| `record` | fingerprint に git sha・manifest hash が入る。round-trip |
| `registry` | 全実装名が構築できる。未実装名は `KeyError` に候補一覧 |
| `lightgbm_*` | 未導入なら skip。合成で信号を回収 |
| `classify` / `MetaLabelModel` | 確率が [0,1]。meta-label が誤り方向の確率を下げる |
| `sequence` | torch 無しなら skip。CPU 1 epoch smoke。`make_sequence_design` の窓が欠損を含まない |
| `forecaster_signal` | causal 性（`prices[:k]` だけで同じ値）。`every` 間が NaN |

### 7.2 検証コマンド

```bash
uv run --no-sync pytest quantkit/tests -q
make lint
uv sync --all-packages          # lightgbm 追加後
```

NB07–09 を出力付きで再実行（合成なので軽い）。NB17/18 は snapshot で実行し出力保存。

### 7.3 文書

- README: 状態/ロードマップに Phase 4（反証力）・Phase 5（幅）を追加。「全実走」を
  出力保存済みの事実に合わせる。leaderboard の結果（勝ち負け両方）を要約。
- `reports/experiments/*.json` をコミット。

## 8. 範囲外

- xgboost / optuna / shap の導入。
- J-Quants V2 移植、日本株ユニバース。
- Chronos の実行（アダプタ経路の接続のみ。重みの取得は任意）。
- ポートフォリオ最適化・税・可視化層の変更（既存を使う）。
- 実データでの「勝つモデルを見つけること」。装置と記録が成果物であり、全候補が負けても完了。

## 9. リスク

- 実データは取得時点で変わる。snapshot と manifest の sha256 で固定し、NB は
  snapshot のみを読む。
- 米株の手選びユニバースはサバイバーシップバイアスを持つ。結果の解釈で常に明記。
- `TunedModel` × leaderboard × PBO は fit 回数が積で増える。NB17 では grid を小さく
  （≤ 6 点）し、実行時間を記録する。
- torch の系列モデルは乱数・GPU 非決定性で再現が揺れる。seed 固定と
  `torch.use_deterministic_algorithms` を試み、揺れが残る場合は記録に幅として残す。
