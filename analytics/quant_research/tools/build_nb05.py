"""Builder for notebook 05: the B1 JGB-like curve fitter project."""

from nbkit import code, md

cells = [
    md(r"""
# 05. B1 Project — JGB Curve Fitter v0

> 採用するのは最も滑らかに見える曲線ではない。データ契約、目的関数、診断、限界を最も明確に説明できる曲線である。

## 学習目標

- Week 1–4の射影、conditioning、SVD、正則化を1つのprojectへ統合する
- zero yield教育モードとcoupon bond価格モードを分ける
- solver、basis、ridgeを共通の評価表で比較する
- bid–ask weighted pricing RMSE、LOO、solver disagreement、outlier感度を測る
- 再現可能な技術メモと採用／不採用判断を残す

## 前提知識

- Week 1–4のExit Criteria
- coupon、face value、maturity、dirty priceの初歩
- yieldとzero rateが同じとは限らないこと
"""),
    code("""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from quant_textbook import (
    CouponBondUniverse,
    fit_bond_price_curve,
    fit_curve,
    leave_one_bond_out_price_rmse,
    leave_one_out_rmse,
    make_synthetic_jgb_universe,
    predict_bond_prices,
    predict_curve,
    price_coupon_bond,
    weighted_rmse,
)

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260809
"""),
    md(r"""
## 1. Project charterとvalidation基準

### 問い

限られた満期のJGB-like coupon bondから、数値的に安定し、保留した債券にも妥当な価格を返すzero curve候補を比較できるか。

### v0の合格条件

1. 入力単位と価格規約が固定されている
2. rank、condition number、残差、LOOを保存する
3. yield誤差とprice誤差を別列にする
4. QR、SVD、ridgeの予測差を測る
5. 1点outlierで採用判断が反転しないか確認する
6. 合成データでだけ利用できるoracle情報を明示する

### v0で扱わないもの

settlement date、actual coupon calendar、day-count、holiday、clean price、経過利息、tax、special issue、liquidity premium、on/off-the-run差は実装しない。したがって本Notebookはproduction pricerではない。
"""),
    md(r"""
## 2. 直感と価格式 — 識別したい対象

bond $i$ のdirty priceを

$$
P_i=\sum_{j=1}^{m_i}C_{ij}D(t_{ij})+\epsilon_i
$$

とする。continuous compoundingのzero rate $z(t)$ なら

$$
D(t)=e^{-t z(t)}
$$

である。coupon bondのyield-to-maturity $y_i$ は

$$
P_i=\sum_{j=1}^{m_i}C_{ij}e^{-t_{ij}y_i}
$$

を満たす単一rateであり、各cash flow時点の $z(t_{ij})$ ではない。したがってmaturityに対するYTM curveを、そのままzero curveとして価格式へ入れるのは近似である。

本projectは2段階に分ける。

- **教育モード:** 合成generatorが公開するlatent zero rateをfitし、basisとsolverを学ぶ
- **債券モード:** 観測dirty priceからzero curveを直接calibrateし、全cash flowを再評価する

実データではlatent zero rateは観測できない。本章後半の債券モードはprice residualを直接最小化し、latent curveは合成実験の事後検証だけに使う。ただしsettlement dateやday-count等を省略しているためproduction calibrationではない。
"""),
    code("""
universe = make_synthetic_jgb_universe(
    maturities=np.array([0.5, 1, 2, 3, 5, 7, 10, 15, 20, 30], dtype=float),
    coupon_rates=np.array([0.001, 0.002, 0.003, 0.004, 0.006, 0.008, 0.010, 0.012, 0.014, 0.016]),
    frequency=2,
    face_value=100.0,
    price_noise_std=0.015,
    seed=RANDOM_SEED,
)

bonds = universe.bonds.copy()
cashflows = universe.cashflows.copy()

# A deterministic synthetic half-spread in price points per 100 face.
bonds["price_half_spread"] = 0.015 + 0.0015 * bonds["maturity_years"]
bonds["price_weight"] = 1.0 / bonds["price_half_spread"] ** 2
universe = CouponBondUniverse(bonds=bonds, cashflows=cashflows)

display(bonds.round(6))
print("cash-flow rows:", len(cashflows))
"""),
    md(r"""
単位は次のとおり。

| 列 | 単位 | 観測可能性 |
|---|---|---|
| `maturity_years` | 年 | 観測可能 |
| `coupon_rate` | decimal per year | 観測可能 |
| `dirty_price` | 額面100あたり | 観測可能という教材仮定 |
| `yield_to_maturity` | continuous decimal per year | 価格と規約から計算 |
| `zero_rate_at_maturity` | decimal per year | 合成generatorだけのoracle |
| `price_half_spread` | 価格point | 教材で作るproxy |

実市場でpriceとyieldのどちらがsourceか、timestampが揃っているか、bid/askかmidかを必ず記録する。
"""),
    code("""
fig = go.Figure()
fig.add_scatter(
    x=bonds["maturity_years"],
    y=100 * bonds["yield_to_maturity"],
    mode="lines+markers",
    name="Yield to maturity",
)
fig.add_scatter(
    x=bonds["maturity_years"],
    y=100 * bonds["zero_rate_at_maturity"],
    mode="lines+markers",
    name="Latent zero rate",
)
fig.update_layout(
    title="YTM and zero rate are different objects",
    xaxis_title="Maturity (years)",
    yaxis_title="Rate (%)",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 3. 共通評価harness

curve modelをcash-flow pricerへ渡すadapterを1つだけ作る。各modelが独自の価格計算を持つと、比較がpricing conventionの差になってしまう。
"""),
    code("""
def price_universe(curve_model, bond_universe):
    predicted_prices = []
    for bond_id in bond_universe.bonds["bond_id"]:
        bond_cashflows = bond_universe.cashflows.loc[
            bond_universe.cashflows["bond_id"] == bond_id
        ]
        zero_curve = lambda times: predict_curve(
            curve_model,
            np.asarray(times, dtype=float),
        )
        predicted_prices.append(
            price_coupon_bond(
                bond_cashflows["payment_time"].to_numpy(),
                bond_cashflows["cashflow"].to_numpy(),
                zero_curve,
                compounding="continuous",
            )
        )
    return np.asarray(predicted_prices)


def evaluate_candidate(name, model, loo_error, bond_table, bond_universe):
    maturities = bond_table["maturity_years"].to_numpy()
    observed_zero_rates = bond_table["zero_rate_at_maturity"].to_numpy()
    predicted_zero_rates = predict_curve(model, maturities)
    predicted_prices = price_universe(model, bond_universe)
    observed_prices = bond_table["dirty_price"].to_numpy()
    price_weights = bond_table["price_weight"].to_numpy()
    return {
        "name": name,
        "model": model,
        "yield_rmse_bp": 1e4
        * np.sqrt(np.mean((observed_zero_rates - predicted_zero_rates) ** 2)),
        "loo_yield_rmse_bp": 1e4 * loo_error,
        "price_rmse": np.sqrt(np.mean((observed_prices - predicted_prices) ** 2)),
        "weighted_price_rmse": weighted_rmse(
            observed_prices,
            predicted_prices,
            price_weights,
        ),
        "condition_number": model.diagnostics.condition_number,
        "rank": model.diagnostics.rank,
        "coefficient_norm": np.linalg.norm(model.coefficients),
        "predicted_prices": predicted_prices,
    }
"""),
    md(r"""
## 4. Basis・solver・ridgeを比較する

候補集合はデータを見る前に固定する。ここでは高自由度を競うのではなく、失敗の種類が異なる小さな集合を使う。
"""),
    code("""
maturities = bonds["maturity_years"].to_numpy()
oracle_zero_rates = bonds["zero_rate_at_maturity"].to_numpy()

candidate_specs = [
    (
        "Polynomial degree 3 / SVD",
        {"basis": "polynomial", "degree": 3, "method": "svd"},
    ),
    (
        "Spline ridge / SVD",
        {
            "basis": "spline",
            "knots": (2.0, 5.0, 10.0, 20.0),
            "ridge": 1e-5,
            "method": "svd",
        },
    ),
    (
        "Nelson-Siegel / QR",
        {"basis": "nelson_siegel", "decay": 0.45, "method": "qr"},
    ),
    (
        "Nelson-Siegel / SVD",
        {"basis": "nelson_siegel", "decay": 0.45, "method": "svd"},
    ),
    (
        "Nelson-Siegel ridge / SVD",
        {
            "basis": "nelson_siegel",
            "decay": 0.45,
            "ridge": 1e-5,
            "method": "svd",
        },
    ),
]

evaluations = []
for name, specification in candidate_specs:
    model = fit_curve(maturities, oracle_zero_rates, **specification)
    loo_error = leave_one_out_rmse(
        maturities,
        oracle_zero_rates,
        **specification,
    )
    evaluations.append(
        evaluate_candidate(name, model, loo_error, bonds, universe)
    )

evaluation_table = pd.DataFrame(
    [
        {key: value for key, value in evaluation.items() if key not in {"model", "predicted_prices"}}
        for evaluation in evaluations
    ]
).set_index("name")
display(evaluation_table.round(6))
"""),
    md(r"""
評価表の読み方は次のとおり。

- `yield_rmse_bp`: 合成oracle zero rateへの学習内誤差
- `loo_yield_rmse_bp`: 1満期を保留した補間・外挿誤差
- `price_rmse`: 全cash flowを割り引いたdirty price誤差
- `weighted_price_rmse`: 狭い合成spreadのbondを強く評価した価格誤差
- `condition_number`: basis designの数値感度
- `coefficient_norm`: 不安定化のsignalであり、単独の良否基準ではない

oracle zero rateをfitしているため、この表はproduction backtestではない。v0の数値教材としてのみ解釈する。
"""),
    code("""
evaluation_grid = np.linspace(0.25, 30.0, 300)
fig = go.Figure()
fig.add_scatter(
    x=maturities,
    y=100 * oracle_zero_rates,
    mode="markers",
    name="Latent zero-rate observations",
    marker={"size": 10, "color": "black"},
)
for evaluation in evaluations:
    fig.add_scatter(
        x=evaluation_grid,
        y=100 * predict_curve(evaluation["model"], evaluation_grid),
        mode="lines",
        name=evaluation["name"],
    )
fig.update_layout(
    title="Candidate zero curves",
    xaxis_title="Maturity (years)",
    yaxis_title="Zero rate (%)",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 5. 観測dirty priceからzero curveをcalibrateする

ここまでのoracle zero-rate fitは、basisと線形solverを監査する教育モードだった。債券モードではoracleを入力にしてはいけない。固定したbasis parameter $\eta$ と係数 $\beta$ に対し、直接

$$
\min_\beta \sum_i w_i\left[P_i^{obs}-\sum_j C_{ij}
\exp\left\{-t_{ij}B(t_{ij};\eta)^\top\beta\right\}\right]^2
+\lambda\lVert\beta\rVert_2^2
$$

を解く。zero rateは係数に線形でも、価格はdiscount factorを通じて非線形である。したがって、Jacobianのrankと条件数、solver成功、pricing residualを一緒に保存する。
"""),
    code("""
price_candidate_specs = [
    (
        "Polynomial degree 3",
        {"basis": "polynomial", "degree": 3, "ridge": 1e-8},
    ),
    (
        "Spline ridge",
        {
            "basis": "spline",
            "knots": (2.0, 5.0, 10.0, 20.0),
            "ridge": 1e-6,
        },
    ),
    (
        "Nelson-Siegel fixed decay",
        {"basis": "nelson_siegel", "decay": 0.45, "ridge": 1e-8},
    ),
]


def evaluate_price_candidates(bond_universe):
    bond_table = bond_universe.bonds
    price_weights = bond_table["price_weight"].to_numpy()
    rows = []
    models = {}
    for name, specification in price_candidate_specs:
        model = fit_bond_price_curve(
            bond_universe,
            weights=price_weights,
            **specification,
        )
        loo_error = leave_one_bond_out_price_rmse(
            bond_universe,
            weights=price_weights,
            **specification,
        )
        models[name] = model
        rows.append(
            {
                "name": name,
                "pricing_rmse": model.diagnostics.rmse,
                "weighted_pricing_rmse": model.diagnostics.weighted_rmse,
                "loo_price_rmse": loo_error,
                "jacobian_rank": model.diagnostics.rank,
                "condition_number": model.diagnostics.condition_number,
                "success": model.diagnostics.success,
                "nfev": model.diagnostics.nfev,
            }
        )
    return pd.DataFrame(rows).set_index("name"), models


price_calibration_table, price_models = evaluate_price_candidates(universe)
display(price_calibration_table.round(6))

eligible = price_calibration_table.loc[
    price_calibration_table["success"]
    & (price_calibration_table["condition_number"] < 1e10)
]
if eligible.empty:
    raise RuntimeError("no price calibration passed the numerical gate")

selected_name = eligible["loo_price_rmse"].idxmin()
selected_price_model = price_models[selected_name]
print("selected by the predeclared gate:", selected_name)
"""),
    md(r"""
選択規則は結果を見る前に固定する。ここでは `success`、Jacobian条件数 $<10^{10}$ を満たす候補のうち、leave-one-bond-out price RMSEが最小のものを選ぶ。閾値は普遍定数ではなく、この合成実験で極端な弱識別を除く監査用gateである。
"""),
    code("""
calibrated_prices = predict_bond_prices(selected_price_model, universe)
calibrated_zero_rates = selected_price_model.predict_zero_rates(evaluation_grid)

fig = go.Figure()
fig.add_scatter(
    x=maturities,
    y=100 * oracle_zero_rates,
    mode="markers",
    name="Latent zero rate (evaluation only)",
    marker={"size": 10, "color": "black"},
)
fig.add_scatter(
    x=evaluation_grid,
    y=100 * calibrated_zero_rates,
    mode="lines",
    name=f"Price-calibrated: {selected_name}",
)
fig.update_layout(
    title="Price-space calibration checked against the synthetic latent curve",
    xaxis_title="Maturity (years)",
    yaxis_title="Continuous zero rate (%)",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
latent zero rateは図の答え合わせにだけ使い、fitには渡していない。実データではこの線は存在しないため、価格残差、保留債券誤差、quote幅、parameter sensitivityで判断する。
"""),
    md(r"""
## 6. Solver disagreement

同じNelson–Siegel basisをQRとSVDで解いた予測差を測る。係数差だけでなく、採用対象であるcurveとpriceの差を見る。
"""),
    code("""
qr_evaluation = next(item for item in evaluations if item["name"] == "Nelson-Siegel / QR")
svd_evaluation = next(item for item in evaluations if item["name"] == "Nelson-Siegel / SVD")

qr_curve = predict_curve(qr_evaluation["model"], evaluation_grid)
svd_curve = predict_curve(svd_evaluation["model"], evaluation_grid)

print("maximum curve disagreement (bp):", 1e4 * np.max(np.abs(qr_curve - svd_curve)))
print(
    "maximum price disagreement:",
    np.max(np.abs(qr_evaluation["predicted_prices"] - svd_evaluation["predicted_prices"])),
)
"""),
    md(r"""
一致は「正しさ」の証明ではない。両solverが同じ誤ったdata contractを解くこともある。不一致は調査開始のsignal、一致は数値経路の限定的なcheckである。
"""),
    md(r"""
## 7. YTM curveをzero curveとして使う誤り

比較のため、YTMを満期へfitし、それをzero curveと誤ってprice adapterへ渡す。fitしたYTM curve自体が滑らかでも、coupon cash flowのdiscount rateとしては別の対象である。
"""),
    code("""
ytm_model = fit_curve(
    maturities,
    bonds["yield_to_maturity"].to_numpy(),
    basis="nelson_siegel",
    decay=0.45,
    method="svd",
)
wrong_prices = price_universe(ytm_model, universe)
zero_curve_prices = calibrated_prices

observed_prices = bonds["dirty_price"].to_numpy()
print(
    "YTM-as-zero pricing RMSE:",
    np.sqrt(np.mean((observed_prices - wrong_prices) ** 2)),
)
print(
    "Price-calibrated zero-curve RMSE:",
    np.sqrt(np.mean((observed_prices - zero_curve_prices) ** 2)),
)
"""),
    code("""
fig = go.Figure()
fig.add_scatter(
    x=bonds["maturity_years"],
    y=(observed_prices - zero_curve_prices) / bonds["price_half_spread"],
    mode="lines+markers",
    name="Zero-curve model",
)
fig.add_scatter(
    x=bonds["maturity_years"],
    y=(observed_prices - wrong_prices) / bonds["price_half_spread"],
    mode="lines+markers",
    name="YTM used as zero curve",
)
fig.add_hline(y=1.0, line_dash="dash", line_color="gray")
fig.add_hline(y=-1.0, line_dash="dash", line_color="gray")
fig.update_layout(
    title="Pricing residuals scaled by synthetic half-spread",
    xaxis_title="Maturity (years)",
    yaxis_title="Residual / half-spread",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 8. Outlier sensitivityと採用順位

20年bondの観測dirty priceを合成half-spreadの3倍だけ動かし、全候補を再calibrateする。1候補の係数変化だけでなく、事前に決めた採用規則が反転するかを検査する。
"""),
    code("""
outlier_bonds = bonds.copy()
outlier_mask = outlier_bonds["maturity_years"] == 20.0
outlier_bonds.loc[outlier_mask, "dirty_price"] += (
    3.0 * outlier_bonds.loc[outlier_mask, "price_half_spread"]
)
outlier_universe = CouponBondUniverse(
    bonds=outlier_bonds,
    cashflows=cashflows.copy(),
)

outlier_table, outlier_models = evaluate_price_candidates(outlier_universe)
outlier_eligible = outlier_table.loc[
    outlier_table["success"] & (outlier_table["condition_number"] < 1e10)
]
if outlier_eligible.empty:
    raise RuntimeError("no outlier calibration passed the numerical gate")

outlier_selected_name = outlier_eligible["loo_price_rmse"].idxmin()
ranking_comparison = pd.DataFrame(
    {
        "base_rank": price_calibration_table["loo_price_rmse"].rank(method="min"),
        "outlier_rank": outlier_table["loo_price_rmse"].rank(method="min"),
        "base_loo_price_rmse": price_calibration_table["loo_price_rmse"],
        "outlier_loo_price_rmse": outlier_table["loo_price_rmse"],
    }
).sort_values("base_rank")
display(ranking_comparison.round(6))

same_specification_outlier_model = outlier_models[selected_name]
curve_shift_bp = 1e4 * (
    same_specification_outlier_model.predict_zero_rates(evaluation_grid)
    - selected_price_model.predict_zero_rates(evaluation_grid)
)

fig = go.Figure(
    go.Scatter(x=evaluation_grid, y=curve_shift_bp, mode="lines", name="Curve shift")
)
fig.add_vline(x=20.0, line_dash="dash", line_color="red")
fig.update_layout(
    title="Price-quote outlier impact on the selected curve specification",
    xaxis_title="Maturity (years)",
    yaxis_title="Fitted curve shift (bp)",
    template="plotly_white",
)
fig.show()

print("maximum absolute curve shift (bp):", np.max(np.abs(curve_shift_bp)))
print("base selection:", selected_name)
print("outlier selection:", outlier_selected_name)
print("selection changed:", outlier_selected_name != selected_name)
"""),
    md(r"""
outlierが1点でも全満期へ影響するのはglobal basisの特徴である。順位が不変でもrobustnessの証明にはならず、順位が変われば選択規則の脆弱性が可視化されたことになる。除外前にsource、timestamp、spread、cash-flow conventionを調査する。
"""),
    md(r"""
## 9. 採用メモ

まず、計算結果から機械的に再生成できるdecision recordを残す。
"""),
    code("""
selected_row = price_calibration_table.loc[selected_name]
decision_record = pd.Series(
    {
        "decision": "adopt for the synthetic B1 MVP",
        "selected_model": selected_name,
        "selection_rule": "successful, condition < 1e10, minimum LOO price RMSE",
        "weighted_pricing_rmse": selected_row["weighted_pricing_rmse"],
        "loo_price_rmse": selected_row["loo_price_rmse"],
        "jacobian_condition_number": selected_row["condition_number"],
        "outlier_selected_model": outlier_selected_name,
        "selection_changed_under_outlier": outlier_selected_name != selected_name,
    },
    name="value",
)
display(decision_record.to_frame())
"""),
    md(r"""
文章の技術メモは次の構造でdecision recordを解釈する。

### Decision

採用候補、保留、不採用のいずれかを1行で書く。

### Evidence

- primary metricと単位
- LOOと学習内の差
- condition number、rank、solver disagreement
- half-spread単位のpricing residual
- outlier破壊実験

### Assumptions

- compoundingとprice type
- weighting rule
- fixed decay、degree、knots、ridge
- continuous compoundingと全cash flow価格式
- latent zero rateは事後評価だけに使ったこと

### Remaining risks

- JGB市場慣行未実装
- liquidity・tax・settlement未実装

数値が良いだけでは採用しない。第三者が同じ入力から同じ表を再生成でき、判断の境界を説明できることを合格条件とする。
"""),
    md(r"""
## 10. 失敗モード — 教材oracleを実データでも観測できると思う

`zero_rate_at_maturity` はgeneratorの内部curveから得た教師情報であり、市場quoteではない。実データに同じ列があるように見えても、それは別モデルが推定したcurveかもしれない。

- 推定済みzero rateをraw observationと呼ぶ
- 推定元に同じbond priceが入っているのにout-of-sampleと呼ぶ
- dirty priceとclean priceを混ぜる
- yieldのcompounding conventionを混ぜる
- cash flowの途中時点をmaturity YTMだけで割り引く
- 古い市場慣行資料を現在のpricing conventionとして無検証で使う

実データadapterを作る前に、field lineageとpoint-in-time availabilityを表にする。
"""),
    md(r"""
## 11. 段階別演習

### 基礎

1. 5年coupon bondの全cash flowを表にし、curveからdirty priceを手計算とコードで照合せよ。
2. yield RMSEをbp、price RMSEを額面100あたりで表示し、単位を混ぜない表を作れ。
3. QRとSVDのcurve disagreementを計算せよ。

### 標準

4. maturityを1本ずつ保留し、zero yield誤差とprice誤差の両方を記録せよ。
5. half-spreadの上限・下限を変え、weighted pricing RMSEの感度を調べよ。
6. 各候補へ同じoutlierを入れ、最大curve shiftと係数shiftを比較せよ。

### 研究

7. robust lossを加え、同じprice outlierに対する順位とcurve shiftを比較せよ。
8. JGB実データadapterのdata dictionaryを作り、settlement、coupon schedule、clean/dirty、accrued interest、timestamp、sourceを必須列にせよ。
9. 評価表から採用候補を1つ選び、反対意見を含む500–800字の技術メモを書け。
"""),
    md(r"""
## 12. Exit Criteria

- [ ] zero yield、YTM、discount factor、dirty priceを区別できる
- [ ] coupon cash flowを各時点のzero rateで価格評価できる
- [ ] latent zero rateを入力せず、観測dirty priceからzero curveをcalibrateできる
- [ ] basis、solver、ridgeを同一harnessで比較できる
- [ ] LOO、weighted pricing error、solver disagreement、outlier感度を報告できる
- [ ] synthetic oracleと実市場で観測可能なfieldを分けられる
- [ ] 採用／不採用の理由と残るriskを技術メモにできる
"""),
    md(r"""
## 13. 出典

- [BIS: Technical note on Japanese government securities](https://www.bis.org/publ/bppdf/bispap25h.pdf) — JGBをcoupon・principal cash flowへ分解するcurve推定資料。歴史的慣行を含むため現行規約とは別に検証する
- [BIS Papers No. 25: Zero-coupon yield curves](https://www.bis.org/publ/bppdf/bispap25.htm) — discount factor、spot/forward rate、中央銀行のcurve推定法
- [財務省 Interest Rate Q&A](https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/qa.htm) — JGB prevailing yield、constant maturity、yield curveの公式説明
- [財務省 About JGBs](https://www.mof.go.jp/english/policy/jgbs/debt_management/guide.htm) — coupon、購入価格、maturityとYTMの関係
- [NumPy `linalg.lstsq`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html) — rankと最小normを含む最小二乗仕様
- [SciPy `optimize.least_squares`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html) — price-space非線形最小二乗とJacobian診断の公式API

B1はここで完了する。次のblockへ進む前に、Notebookをclean environmentで上から再実行し、採用メモと評価表を保存する。
"""),
]
