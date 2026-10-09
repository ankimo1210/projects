# Task 2 report — Conditional Asian / auxiliary GBM

2026-10-09。担当範囲の実装と scoped 検証を完了。独立レビューは root が実施する。
commit、共有 docs/index、public API、依存、既存会計コードは変更していない。

## 変更ファイル

- `johnhull/hullkit/src/hullkit/_dynamic_hedging_conditional.py`: last-stock-step 条件付き tail、実暦 GBM 幾何補助平均、金融原始値、beta=1 曲線／共有 16 IID block 共分散。
- `johnhull/hullkit/tests/test_dynamic_hedging_conditional.py`: 25 テスト。独立 quad、m1 Black、memory linear、非定数 local の価格／spot／state bump、保存原始値／block 共分散、atom／全ゼロ／支持外／invalid raw 微分診断。

## RED / GREEN

- 初回 RED: 17 failures、未実装 private module の ImportError。初回 `$PWD` 指定が Windows→WSL で cwd 変更より先に展開され、base checkout を import していた点を発見。以降は WT の絶対 PYTHONPATH と `--confcutdir=johnhull/hullkit` を使用し、`hullkit.__file__` が WT であることを確認した。
- 実装後: 16 passed / 1 failed。手書き fixing delay の完全一致 assertion が浮動小数の差 2.8e-17 を検出したため、数学量として 1e-15 の近似比較へ修正。
- 境界 RED: 19 passed / 2 failed。exact linear と保存 block 曲線の不一致、および最後の unused variance shock が claim を invalid にする不具合を検出。
- 境界 GREEN: 21 passed。
- underflow RED: 23 passed / 1 failed。解析 one-step の lognormal tail が underflow した全ゼロ価格を ready としていたことを検出。
- 最終 GREEN: **24 passed in 0.55s**。ruff check `All checks passed!`、ruff format check `2 files already formatted`。

```bash
cd /home/kazumasa/worktrees/johnhull-research-roadmap
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
PYTHONPATH=/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit/src \
/home/kazumasa/projects/.venv/bin/python -m pytest --confcutdir=johnhull/hullkit -q \
  johnhull/hullkit/tests/test_dynamic_hedging_conditional.py
/home/kazumasa/projects/.venv/bin/ruff check \
  johnhull/hullkit/src/hullkit/_dynamic_hedging_conditional.py \
  johnhull/hullkit/tests/test_dynamic_hedging_conditional.py
/home/kazumasa/projects/.venv/bin/ruff format --check \
  johnhull/hullkit/src/hullkit/_dynamic_hedging_conditional.py \
  johnhull/hullkit/tests/test_dynamic_hedging_conditional.py
```

whole suite、重い pilot／市場精度 gate は指示どおり未実施。

## Interface / units

承認された 4 signatures を維持:
`conditional_tail(b,c,mu,sigma,x)`、`auxiliary_geometric_mean(...)`、
`teacher_primitives(...)`、`primitive_labels(...,blocks=16)`。
Task1 の `cir_implicit_step(v,z_v,dt,parameters)` を import する。

- 時間: `calendar_times` は絶対年、`fixing_delays` は restart からの年。local は calendar midpoint と左 spot で field を評価する。
- `f=E[(sum_future S_j/spot-x)+]`: normalized undiscounted。通貨 price は `exp(-r*expiry_delay)*spot*f/12`。
- `auxiliary_geometric_mean` の return: 通貨の discounted auxiliary payoff。memory_sum は通貨、strike は通貨、`total_fixings` は元 claim 分母。
- `normals`: `(original N, intervals, 2)`。stock は factor0、variance は rho*factor0+sqrt(1-rho²)*factor1。model と auxiliary は同一最後の factor0 で conditioning。最後の variance 更新は payoff に不要なため実行しない。
- Heston control_variance: expected average variance。local: `ell*base_variance(first_midpoint,spot)`。spot/state ごとに simulated auxiliary と既知平均を両方再計算する。
- primitive keys: `b,c,mu,sigma,last_z,last_left_spot,last_left_variance,last_left_coefficient,aux_logG_prefix,aux_last_loading,control_variance,control_status,aux_first_midpoint,path_mask,primitive_status,failure_reasons,local_step_status`。
- `aux_logG_prefix` は **log(G/spot)** の最後の normal を除いた部分。loading を加えて normalized auxiliary geometric mean を復元する。
- labels: `f,f_x,f_se,f_x_se,status,status_reasons` は `(thresholds,)`。`raw_samples,conditioned_samples,cv_samples,f_samples,f_x_samples` は `(N,thresholds)`。
- `block_means`: `(16,thresholds,3)`、component_order は raw/conditioned/cv。Task3 価格曲線は `block_means[:,:,2]`、微分は `f_x_block_means` `(16,thresholds)`。
- `block_covariance`: flatten(threshold,component) の mean-estimator covariance = sample covariance of 16 block means /16。`joint_block_covariance` は同じ順番の価格と微分を連結し、cross-risk error も保存する。
- `component_means/component_se` は同じ元 N の raw/conditioned/CV 個票比較。SE は個票 sample SD/sqrt(N)。共分散は block estimator のもの。
- `N` と `original_path_count` は元 N の alias。metadata の spot/state/memory_count/calendar/fixings/rate/q/expiry と `shared_driver_id` は labels に保持。date_index は caller 側で付ける。

## Qualification / evidence

- x<=0 は exact Q linear curve とし、price、derivative、primary CV 個票、保存 block curves を同じ exact branch にする。元 beta=1 算式の個票も `unreplaced_cv_samples/unreplaced_cv_x_samples` に保存する。
- positive-threshold CV 個票は負でも clip しない。beta=1 identity をテストし、負個票が実在する fixture で固定する。
- ordinary stochastic allzero／constant samples／SE0 は `unknown_underresolved`。one-step CE が完全解析でも tail underflow の全ゼロは unknown。exact linear、deterministic／settled branch は明示的に区別する。
- sigma0 atom は値を返すが x Greek を NaN、`unknown_atom` にする。
- unsupported field または非有限原始 path は N を維持し、whole label を `unknown_invalid_primitives` にする。silent drop/nearest/hold/zero repair はしない。
- independent nonconstant local one-step Black bumps と同一価格の spot/state bump が abs 1e-11 で一致し、homogeneity-only delta の欠落 chain が 0.002 より大きい fixture で検出される。

root の独立レビューと Task3 cache の接続を残す。scoped tiny fixtures の成功を正式 pilot precision／モデル性能の承認とは呼ばない。

## 独立レビュー Important finding の修正

- 指摘を N32／one invalid original path の fixture で再現。RED **24 passed / 1 failed**: `derivative_component_means` の raw channel が有限値 −0.59375／−0.3125 を残した。原因は `NaN > x` が False になり、raw derivative を 0 としていたこと。
- 最小修正: raw derivative は非有限 raw sum を NaN とし、raw／conditioned／CV 微分個票すべてに元 path_mask を適用する。sample 数／原始 N32 は保持し、block／cross-component／joint covariance と mean／SE は通常の NaN 伝播で unknown にする。path を drop せず、主価格／微分の unknown status を保持する。
- 保存診断に `raw_x_samples`、`conditioned_x_samples` を追加。既存 `f_x_samples` とともに `(N,thresholds)`、invalid row は全 NaN。既存 block interface／単位は不変。
- 修正後 GREEN **25 passed in 0.55s**。同じ scoped pytest、ruff check、ruff format check すべて成功。
- 修正後 SHA256 source: `37ebedfe935526fbf25d93f41b4e572b60f895efd88606aa26d93e07a519fbe5`。
- 修正後 SHA256 tests: `a1b5844de2077eef344e49af7627d4f280a67fdac70b490d5d85de91ee1fa9fb`。

共有 docs／Git／他担当 source は変更していない。root の review finding 再確認を残す。
