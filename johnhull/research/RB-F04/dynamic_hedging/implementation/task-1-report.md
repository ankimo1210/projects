# Task 1 implementation report

2026-10-09。Task 1 source/tests完了。commit、public API、__init__、依存、既存demo変更なし。索引・roadmap・統合はparent担当。

## Changed files

- `johnhull/hullkit/src/hullkit/_dynamic_hedging_core.py`: 正CIR、adapted old-v stock、absolute-calendar local recorder、Asian memory、独立gain付きcash会計。
- `johnhull/hullkit/tests/test_dynamic_hedging_core.py`: 29 scoped tests（parametrized件数を含む）。

## Exact interfaces

```python
cir_implicit_step(v: np.ndarray, z_v: np.ndarray, dt: float, parameters: HestonParameters) -> np.ndarray
moment_certificate(parameters: HestonParameters, horizon: float, p: int = 4, epsilon: float = .01) -> dict
heston_records(parameters: HestonParameters, normals: np.ndarray, times: np.ndarray, record_indices: np.ndarray, *, spot=None, variance=None) -> dict
local_records(parameters: HestonParameters, surface: LocalVarianceGrid, normals: np.ndarray, times: np.ndarray, record_indices: np.ndarray, *, spot=None, multiplier=1.) -> dict
asian_memory(record_spots: np.ndarray, record_times: np.ndarray, fixing_times: np.ndarray) -> dict
cash_account(times: np.ndarray, prices: np.ndarray, holdings: np.ndarray, payoff: np.ndarray, *, premium: float, rate: float, cashflows=None, cost_rates=None) -> dict
```

`HestonParameters` / `LocalVarianceGrid` は既存 `_heston_local_surface` からimportする。全normalはcaller所有、RNGなし。`LocalVarianceGrid.evaluate(calendar_t, spots)` の `variance` / `status` を使用する。

Recorders: `spot`, `variance` は(N,record dates)。`path_mask` は(N,) bool、`reasons` は(N,)文字列、`diagnostics.original_path_count` は原N、`failed_path_count` は失敗path数。local diagnosticsの`unsupported_count` / `wing_count` / `early_proxy_count` は全原始path×stepの実評価数、`local_status` は(N,record dates)。localの`variance` は左dateから出る区間のmidpoint/old-spot effective variance、terminalは最後の区間variance。内部stateは逐次更新し、指定recordだけ保存する。

Asian memory: `A` は(N,dates)、`n`/`m` は(dates,)でscheduled countを表す。fixing時刻を同じdateのdecision前に加算し、S0を含めない。過去fixingのrecord欠落はValueError、future fixingsはpending。欠損spotのAはNaNで保持する。

Cash: `cash` / `costs` は(N,m+1)、`pnl` / `discounted_pnl` / `discounted_gain_pnl` は(N,)、`path_mask` / `reasons` /原N diagnosticsを返す。cashは各trade後（terminalはclaim支払/一度のliquidation/fee後）。CF_iはh_(i-1)に支払う。CF_0の権利holdingは0。discount基準はtimes[0]。initial/interim/final feeを全て計算し、CFと終端call mid回収をcall payoffと重複しない。

Certificate: coefficient `(2*p**2-p)*(1+epsilon)*(xi/2)**2*horizon**2`、p4/T1.25=.99421875。`backward_mgf` は192/384/768/1536 per-yearのstep数、全denominator NumPy配列、min denominator、eta、log bound、各qualifiedを保持する。JSON化時はNumPy配列を通常のnon-object数値表現へ変換すること。

## TDD and validation evidence

WSL Ubuntuの共有Python/ruffを使用。WT=/home/kazumasa/worktrees/johnhull-research-roadmap。

```bash
export PYTHONPATH="$WT/johnhull/hullkit/src:$WT/deep_hedge_price/src"
cd "$WT"
/home/kazumasa/projects/.venv/bin/python -m pytest -q --confcutdir=johnhull/hullkit johnhull/hullkit/tests/test_dynamic_hedging_core.py
/home/kazumasa/projects/.venv/bin/ruff check johnhull/hullkit/src/hullkit/_dynamic_hedging_core.py johnhull/hullkit/tests/test_dynamic_hedging_core.py
/home/kazumasa/projects/.venv/bin/ruff format --check johnhull/hullkit/src/hullkit/_dynamic_hedging_core.py johnhull/hullkit/tests/test_dynamic_hedging_core.py
```

- Initial RED: production sourceなしでmissing module `hullkit._dynamic_hedging_core`、pytest exit2 / 1 collection error。
- Initial GREEN: 18 passed。
- Edge RED: finite extreme variance normalのnumerical-zero、discount overflow、single-state memoryで3 failed / 18 passed。その前のoverflow+single-state runは2 failed / 19 passed / 1 warning。
- Edge GREEN: 21 passed、overflow warningsなし。
- Memory refactor後のinteger initial spot RED: 1 failed / 21 passed。dtype拒絶でなく数学的に妥当な整数spotをfloat状態へ変換。
- Final GREEN: 29 passed in 0.60s、exit0。ruff check All checks passed、format --check 2 files already formatted。
- import sourceを独立確認: `$WT/johnhull/hullkit/src/hullkit/_dynamic_hedging_core.py`。root conftestが別package経由でbase moduleを先読みするため、scoped検証は`--confcutdir`付き。rootconftestは変更しない。

Testsはconstant deterministic varianceのexact GBM、xi0 nonconstant exact CIR transition、negative-normal quadratic identity、old-v/correlation、absolute calendar restart、local unsupported/wing/early proxy、path denominator、fixing-before-rebalance、手計算2asset/CF、独立discounted gain、配当total return、terminal全fee、failure保持を検証する。p2/3/4、T1/1.25、4levelsの全24 MGF cellsを確認し、CM2 lognormalのpositive exponential momentがGaussian tailで抑えられないcounterexampleも固定した。

## Limits / pending

- 正CIR schemeはxi>0で4*kappa*theta>xi**2を必要とする。xi0はexact deterministic transition。direct CIR rootの丸めunderflowはrecorderがfailureとして保持し、positive clipはしない。
- Certificateはuniform fixed finite gridsの十分条件。continuous Heston、uniform dt convergence、Greek moment、CF/PDE整合性、数値精度、NN性能は認証しない。
- Local fullfieldのglobal boundedness/wing妥当性、call martingale gap、candidate/pilotはこのtaskで実行していない。
- 全suite/heavy pilotは指示どおり未実行、最終統合gateへ残す。全失敗pathは元Nに残り、失敗後のcash/P&LはNaN。会計方策のhidden hold/zero修復なし。
