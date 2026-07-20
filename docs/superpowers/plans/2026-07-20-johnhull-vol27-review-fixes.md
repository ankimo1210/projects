# JohnHull Vol.27 レビュー指摘修正計画

**日付:** 2026-07-20  
**対象:** `johnhull`  
**起点:** `main`（Vol.26/27 統合後）  
**関連設計:** `docs/superpowers/specs/2026-07-20-johnhull-vol27-risk-desk-design.md`  
**方針:** 公開APIを増やさず、サイレント誤判定を先に止め、artifact-only と
`synthetic-offline` の契約を維持する。

## 1. 目的

コードレビューで確認した次の問題を、小さな互換修正として解消する。

1. 非有限P&L／VaR forecastが「非超過」に変換される。
2. Vol.27 Christoffersen acceptanceがJSON格納p値を信用する。
3. FHSが非有限returnを受け入れる。
4. `evt_var_es` が不正な `GPDFit` からNaNや実装例外を返す。
5. BSM価格関数が満期ゼロ／ボラゼロを含む混在ベクトルを扱えない。
6. バックテスト統計が小数カウントや二次元系列を受け入れる。
7. Vol.27 capstoneが承認済み設計の金利商品・明示的factor mappingを示していない。
8. portal READMEの対象巻表記がVol.18–25のまま残っている。

## 2. 非目標

- FRTB IMA、NMRF、liquidity-horizon ES、IMA/SA比較は追加しない。
- `hullkit.risk` と `hullkit.volatility` の既存数値規約は変更しない。
- 新規production dependencyやtorch依存は追加しない。
- VaR/ES、Christoffersen、GPDの数式・既存正常入力の結果は変更しない。
- `pnl_explain` の公開APIは増やさない。factor mappingは既存
  `aggregate_exposures` の行列契約をcapstoneで明示する。

## 3. 実装順序

### Phase 1 — VaRバックテスト入力契約を固定する

**対象ファイル**

- `johnhull/hullkit/src/hullkit/var_backtest.py`
- `johnhull/hullkit/tests/test_var_backtest.py`

**変更**

1. `exceedance_series` は `pnl` と `var_forecasts` を非空の一次元配列に限定する。
2. 両配列の全要素が有限であることを要求する。
3. VaR forecastはゼロ以上とする。ゼロリスク日を許容しつつ、負のrisk limitは拒否する。
4. `_validate_binary_exceedances` は一次元だけを受け入れ、0/1と有限性の既存検証を維持する。
5. `_validate_counts` はPython/NumPy整数を受け入れ、`bool`、小数、NaN、無限大を
   `ValueError` で拒否する。

**先に追加する回帰テスト**

- `pnl=[-100], var=[NaN]` と `pnl=[NaN], var=[1]` が `ValueError`。
- 負のVaR forecastが `ValueError`、ゼロforecastは有効。
- 二次元P&L／forecastと二次元exceedance系列が `ValueError`。
- `n_exceedances=0.5`、`n_obs=250.5`、`True` が `ValueError`。
- `np.int64` の正当なカウントは既存結果と一致する。

**完了条件**

- 欠損データが0のexceedanceへ変換されない。
- 正常な一次元系列の既存LR統計量とBasel zoneは不変。

### Phase 2 — Acceptance gateを格納済みp値から独立させる

**対象ファイル**

- `johnhull/scripts/frontier_acceptance.py`
- `johnhull/hullkit/tests/test_frontier_reference.py`

**変更**

1. `_volume27` のChristoffersen p値を、配列から再計算した `lr_clustered` から計算する。
   自由度1なので `erfc(sqrt(LR/2))` を使えば追加依存なしで
   `chi2.sf(LR, 1)` と一致する。
2. JSONの `christoffersen_ind_pvalue_clustered` は表示用metricとして残せるが、
   acceptance合否には使用しない。
3. 必要なら再計算値と格納値の一致を別の整合性チェックにする。

**回帰テスト**

- 真のp値が0.05以上の配列について、JSON格納p値だけを0へ改変してもFAILする。
- 現在のcommitted clustered系列は再計算p値でPASSする。
- 再計算p値が `scipy.stats.chi2.sf(..., 1)` と `1e-12` 以内で一致する。

**完了条件**

- `christoffersen_detects_clustering` の合否がNPZ配列だけで決まり、JSON改変で反転しない。

### Phase 3 — FHS／EVTの入力と出力不変条件を強化する

**対象ファイル**

- `johnhull/hullkit/src/hullkit/tail_risk.py`
- `johnhull/hullkit/tests/test_tail_risk.py`

**変更**

1. `filtered_historical_var_es` の `returns` と `sigma` を一次元・同形・有限に限定する。
2. `fit_gpd_pot` は一次元・非空・有限loss、有限threshold、正整数
   `min_exceedances` を検証する。
3. optimizer成功後にも `xi`／`beta` の有限性、`beta > 0`、GPD support、
   有限objectiveを検証し、失敗はすべて `ValueError` に統一する。
4. `evt_var_es` は以下の `GPDFit` 不変条件を計算前に検証する。
   - `xi`、`beta`、`threshold` が有限
   - `beta > 0`
   - `n_exceedances` と `n_total` がboolでない整数
   - `0 < n_exceedances <= n_total`
   - `xi < 1`
5. 戻り値のVaR／ESも有限であることを確認する。

**回帰テスト**

- NaN／Inf return、二次元return、NaN／Inf lossを拒否する。
- `GPDFit(xi=NaN, ...)`、負beta、ゼロexceedance、`N_u > n` を
  `ValueError` で拒否する。
- 無効入力から `RuntimeWarning`、`ZeroDivisionError`、`(NaN, NaN)` が漏れない。
- 定数sigma恒等式、GPD parameter recovery、EVT ES恒等式は既存許容誤差を維持する。

### Phase 4 — BSM価格の要素別境界処理

**対象ファイル**

- `johnhull/hullkit/src/hullkit/bsm.py`
- `johnhull/hullkit/tests/test_bsm.py`

**変更**

1. `S`、`K`、`r`、`sigma`、`T`、`q` を `np.broadcast_arrays` で共通shapeへ揃える。
2. `call_price`／`put_price` を次の排他的maskで評価する。
   - `T == 0`: intrinsic value
   - `T > 0 and sigma == 0`: discounted deterministic payoff
   - `T > 0 and sigma > 0`: 通常BSM式
3. 通常maskだけで `d1`／`d2` を計算し、ゼロ境界を通さない。
4. scalar入力の戻り値慣行と、Greeksでゼロ満期／ゼロボラを拒否する既存契約は維持する。

**回帰テスト**

- `T=[0, 1]` と `sigma=[0, 0.2]` のcall/putを要素別closed formと照合する。
- `S`、`K`、`T` のbroadcastを含むsurface入力を検証する。
- 全要素ゼロ境界と通常scalar価格の既存テストを維持する。
- 正常領域でput-call parityを確認する。

### Phase 5 — Cross-asset capstoneを設計どおりにする

**対象ファイル**

- `johnhull/hullkit/src/hullkit/frontier_reference.py`
- `johnhull/scripts/build_frontier_artifacts.py`
- `johnhull/scripts/frontier_acceptance.py`
- `johnhull/scripts/build_frontier_notebooks.py`
- `johnhull/hullkit/tests/test_frontier_reference.py`
- `johnhull/volumes/27_risk_desk/reference/metrics.json`
- `johnhull/volumes/27_risk_desk/reference/risk_desk_scenarios.npz`
- `johnhull/volumes/27_risk_desk/risk_desk.ipynb`
- `johnhull/book/notebooks/27_risk_desk.ipynb`
- `johnhull/volumes/27_risk_desk/VALIDATION.md`

**最小スコープ**

1. capstoneのpositionを少なくとも次の3種にする。
   - 株価指数call
   - single-name put
   - receive-fixed IRS（既存 `hullkit.swaps.irs_value_fras` を再利用）
2. factorを `index_spot`、`single_name_spot`、`parallel_zero_rate` と明示する。
3. position×factorのdelta/gamma/vega行列をartifactへ保存し、
   `aggregate_exposures` が「既にマップされた行列の集計」であることを教材上明示する。
4. IRSのrate delta/gammaは同じcurve bumpを使うcentral finite difference、full revaluationは
   base/shocked curveで既存swap pricerから計算する。rate vegaはゼロとする。
5. position名、factor名、weights、base/shocked position value、mapping行列をNPZへ追加する。
6. `pnl_explain_taylor_ordering` はcross-asset full revaluationから再計算する。
7. acceptanceに、全positionのfull P&L和とdesk full P&Lの一致、金利factorの存在、
   rate sensitivityの非ゼロを検証する `cross_asset_factor_mapping` を追加する。

**回帰テスト**

- IRSのcentral-difference rate delta/gammaが独立bump再計算と一致する。
- mapping行列のshapeが `(n_positions, n_factors)` で、factorラベルと一致する。
- delta-gamma-vega残差がdelta-only残差より小さく、move半減で縮小する。
- capstone再生成が同一seedで決定的。

**artifact方針**

- schema変更を意図的変更としてVol.27 JSON/NPZを再生成する。
- notebookは新artifactを読むだけとし、pricingやbump計算を実行時に行わない。
- portalの4 figure IDとページ数は変更しない。

### Phase 6 — ドキュメント同期と全ゲート

**対象ファイル**

- `johnhull/report/README.md`
- 必要に応じて `johnhull/MODEL_INDEX.md`
- `johnhull/VALIDATION.md`
- Vol.27設計・実装計画（実装との差異が残る箇所のみ）

**変更**

1. portal READMEの対象をVol.18–27へ更新する。
2. `map_to_factors` と記載する旧設計を、公開APIを増やさない決定と
   `aggregate_exposures` の明示的mapping行列へ同期する。
3. validation記録に今回の境界値テスト、cross-asset capstone、再生成結果を追記する。

## 4. 実行コマンド

すべてworkspace rootから実行する。

```bash
# Phase 1–4: focused regression
uv run --no-sync --package hullkit pytest -q -s \
  johnhull/hullkit/tests/test_var_backtest.py \
  johnhull/hullkit/tests/test_tail_risk.py \
  johnhull/hullkit/tests/test_bsm.py

# Phase 5: reference and notebook regeneration
uv run --no-sync python johnhull/scripts/build_frontier_artifacts.py --volume 27
uv run --no-sync --package hullkit python \
  johnhull/volumes/27_risk_desk/build_27_risk_desk_notebook.py

# Semantic and guard tests
uv run --no-sync --package hullkit pytest -q -s \
  johnhull/hullkit/tests \
  johnhull/report/tests
uv run --no-sync ruff check \
  johnhull/hullkit/src \
  johnhull/hullkit/tests \
  johnhull/scripts \
  johnhull/report/report_builder \
  johnhull/report/tests

# Reproducibility and publication gates
make hull-artifacts-check
make hull-notebooks-check
make hull-report
make hull-book
make hull-release-check

# 全releaseファイルをcommitした後だけ実行
make hull-release-check HULL_RELEASE_FLAGS=--require-tracked
```

## 5. 推奨コミット境界

1. `fix(hullkit): reject invalid VaR and tail-risk inputs`
2. `fix(hullkit): price mixed BSM boundary arrays`
3. `fix(johnhull): recompute vol 27 acceptance statistics`
4. `feat(johnhull): complete cross-asset risk desk capstone`
5. `docs(johnhull): sync vol 27 validation and portal scope`

各コミットで対応するfocused testsを通し、artifact更新はPhase 5のコミットだけに含める。

## 6. 完了基準

- レビュー指摘の再現入力がすべて明示的 `ValueError` または正しい有限値になる。
- JSON metricだけの改変でChristoffersen acceptanceをPASSにできない。
- 正常入力に対する既存VaR/ES、GPD、BSM結果が変わらない。
- Vol.27 capstoneに株式オプションと金利商品、明示的factor mappingが含まれる。
- Vol.27 artifactがsemantic一致かつ2回再生成でbyte-identical。
- Vol.18–27 notebookがfresh executionで全PASS。
- portal 12 themes／78 figures、Jupyter Book、tracked release contractがPASS。
- `hullkit` はtorch-free、新規production dependencyなし。

