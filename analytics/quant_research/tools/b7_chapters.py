"""Deterministic cell definitions for the six B7 notebook builders."""

from __future__ import annotations

from nbkit import code, md
from stage2_nb import setup_cell, treasury_curve_cell

TIME_SERIES_SOURCES = """
- [Forecasting: Principles and Practice — Stationarity and differencing](https://otexts.com/fpp3/stationarity.html)
- [Forecasting: Principles and Practice — ARIMA models](https://otexts.com/fpp3/arima.html)
- [U.S. Treasury Yield Curve Methodology](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/treasury-yield-curve-methodology)
"""

STATE_SPACE_SOURCES = """
- [Kalman (1960), A New Approach to Linear Filtering and Prediction Problems](https://people.math.harvard.edu/archive/116_fall_03/handouts/Kalman1960.pdf)
- [Särkkä and Svensson, Bayesian Filtering and Smoothing, 2nd ed.](https://users.aalto.fi/~ssarkka/pub/bfs_book_2023_online.pdf)
- [Diebold and Li, Forecasting the Term Structure of Government Bond Yields](https://www.nber.org/papers/w10048.pdf)
"""


def overview_cells():
    return [
        md(r"""
# 36. B7 — 時系列・状態空間・動的金利モデル

> B7の対象は「日次」と呼ばれるカレンダー等間隔系列ではなく、Treasuryの公表観測日で進む曲線系列である。

## 学習目標

- stationarity、forecast origin、horizonをデータ契約として書ける
- AR/VAR、Kalman filter、Dynamic Nelson–Siegel、GARCHの役割を分けられる
- filtered estimateとsmoothed estimateの情報集合を区別できる
- B5/B6の外部テストを変更せず5公表日先の曲線予測を評価できる
- 統計的予測精度と取引可能な経済価値を区別できる

## 前提知識

- B1のleast squares、PCA、Nelson–Siegel
- B2のMarkov過程と条件付き期待値
- B3の時系列依存を考慮した推論
- B5/B6のpoint-in-time splitとlocked outer test
"""),
        setup_cell(36),
        treasury_curve_cell(),
        md(r"""
## 1. B7のevidence chain

| Week | Core | Treasury lab | 主な反証 |
|---|---|---|---|
| 25 | stationarity、AR、forecast evaluation | 10年CMTのlevel/change | random walkに勝たない |
| 26 | VAR、Granger、IRF、cointegration | NS factor dynamics | predictive contentをcausalityと誤読 |
| 27 | Kalman filter/smoother、missing data | Dynamic Nelson–Siegel | smoother leakage |
| 28 | GARCH、break、regime dependence | 10年変化のconditional variance | volatility proxyをrealized volatilityと呼ぶ |

Primary horizonは5 Treasury publication observations。1と20はsecondaryで、カレンダー日へ読み替えない。
"""),
        code("""
factor_panel = qt.extract_nelson_siegel_factors(curve_yields, maturity_years, 0.5)
factor_changes = np.diff(factor_panel, axis=0) * 100.0
summary = pd.DataFrame(
    {
        "factor": ["level", "slope", "curvature"],
        "mean_change_bp": factor_changes.mean(axis=0),
        "standard_deviation_bp": factor_changes.std(axis=0, ddof=1),
        "lag1_autocorrelation": [qt.autocorrelation(factor_changes[:, i], 1)[1] for i in range(3)],
    }
)
display(summary)

fig = go.Figure()
for index, name in enumerate(["level", "slope", "curvature"]):
    fig.add_scatter(x=change_dates, y=factor_changes[:, index], name=name, mode="lines")
fig.add_vline(x=pd.Timestamp(test_start_date).timestamp() * 1000, line_dash="dash", line_color="black")
fig.update_layout(
    title="Fixed-decay Nelson-Siegel factor changes and locked test boundary",
    xaxis_title="Treasury publication date",
    yaxis_title="Factor change (bp)",
    template="plotly_white",
)
fig.show()
"""),
        md(
            r"""
## 2. Project contract

Targetは5公表観測先の5 tenor曲線。forecast originではその日までの公表値だけを使う。B5/B6のtest開始日は固定し、B7で後ろへずらしたりmodel selectionへ再利用したりしない。公式CMTはpar yieldの公表系列であり、取引価格、zero curve、intraday quoteではない。

## 3. 失敗モード

- 不規則な休場間隔をカレンダー日等間隔と呼ぶ
- levelの高い自己相関を予測改善と混同する
- full sampleで次数、decay、state数を選ぶ
- smootherをforecast originの特徴量にする
- 公式公表yieldだけからPnLやhedge実現値を作る

## 4. 段階別演習

### 基礎

1. publication horizonとcalendar horizonの差を三連休の例で説明せよ。
2. level、change、factor changeのACFを比較せよ。

### 標準

3. validationだけでAR次数を選ぶprotocolを書け。
4. missing tenorを持つ日をKalman updateがどう扱うか式で示せ。

### 研究

5. 2007–2025拡張manifestを作る場合の構造変化auditを事前登録せよ。

## 5. Exit Criteria

- [ ] publication observationを時間単位として明記した
- [ ] primary 5、secondary 1/20のhorizonを固定した
- [ ] filteredとsmoothedの情報集合を区別した
- [ ] B5/B6 outer testを再利用し再選択に使わない
- [ ] pricing、PnL、causalityのunsupported claimを除外した

## 6. 出典

"""
            + TIME_SERIES_SOURCES
            + STATE_SPACE_SOURCES
        ),
    ]


def week25_cells():
    return [
        md(r"""
# 37. Week 25 — Stationarity, AR diagnostics, and forecast evaluation

## 学習目標

- weak stationarityとergodicityを区別できる
- levelとdifferenceのACF/PACF、Dickey–Fuller diagnosticを比較できる
- AR forecastをrandom-walk baselineと同じvalidation originで評価できる
- ordinary t critical valueをDF statisticへ使わない理由を説明できる

## 前提知識

- lag operator、least squares、autocorrelation
- B5のchronological validation
"""),
        setup_cell(37),
        treasury_curve_cell(),
        md(r"""
## 1. Stationarity contract

弱定常性は (E[y_t]=mu)、(operatorname{Cov}(y_t,y_{t-h})=gamma(h)) が時点に依存しないこと。ergodicityは一つの長いpathの時間平均が母集団量へ収束するための別条件である。

Dickey–Fuller回帰

$$
\Delta y_t=c+\gamma y_{t-1}+\varepsilon_t
$$

のt statisticは通常のStudent-t分布に従わない。本章APIは診断量だけを返し、未実装のcritical valueやp-valueを捏造しない。
"""),
        code("""
train_ten_year = curve_yields[train_mask, 3]
train_change = np.diff(train_ten_year) * 100.0
lag_limit = 20
diagnostic_table = pd.DataFrame(
    {
        "lag": np.arange(lag_limit + 1),
        "level_acf": qt.autocorrelation(train_ten_year, lag_limit),
        "change_acf": qt.autocorrelation(train_change, lag_limit),
        "level_pacf": qt.partial_autocorrelation(train_ten_year, lag_limit),
        "change_pacf": qt.partial_autocorrelation(train_change, lag_limit),
    }
)
display(diagnostic_table.head(8))
display(
    pd.DataFrame(
        [
            {"series": "10y level", **qt.dickey_fuller_diagnostic(train_ten_year).__dict__},
            {"series": "10y change", **qt.dickey_fuller_diagnostic(train_change).__dict__},
        ]
    )
)

fig = go.Figure()
fig.add_bar(x=diagnostic_table["lag"], y=diagnostic_table["level_acf"], name="level")
fig.add_bar(x=diagnostic_table["lag"], y=diagnostic_table["change_acf"], name="change")
fig.update_layout(
    title="10y Treasury ACF: level versus publication-to-publication change",
    xaxis_title="Lag (publication observations)",
    yaxis_title="Sample autocorrelation",
    barmode="group",
    template="plotly_white",
)
fig.show()
"""),
        md(r"""
## 2. Five-publication validation forecast

AR(1) parameterはtrainingで一度だけfitする。各validation originでは観察済みhistoryを更新するが、係数をvalidation outcomeへ合わせて再推定しない。
"""),
        code("""
horizon = 5
ar_level = qt.fit_ar(train_ten_year, 1)
validation_origins = np.flatnonzero(
    (curve_dates > train_end_date)
    & (curve_dates <= validation_end_date)
    & (np.arange(curve_dates.size) + horizon < curve_dates.size)
)
validation_origins = validation_origins[curve_dates[validation_origins + horizon] <= validation_end_date]
actual = curve_yields[validation_origins + horizon, 3]
ar_prediction = np.array(
    [qt.forecast_ar(ar_level, curve_yields[: origin + 1, 3], horizon)[-1] for origin in validation_origins]
)
random_walk = curve_yields[validation_origins, 3]
forecast_table = pd.DataFrame(
    [
        {"model": "random walk", "rmse_bp": 100.0 * np.sqrt(np.mean((actual - random_walk) ** 2))},
        {"model": "AR(1) level", "rmse_bp": 100.0 * np.sqrt(np.mean((actual - ar_prediction) ** 2))},
    ]
)
display(forecast_table)
"""),
        md(
            r"""
## 3. 失敗モード

- levelとdifferenceを同じestimandとして比べる
- ACFのconfidence bandを次数選択の唯一の規則にする
- DF statisticへ通常のt critical valueを使う
- validationの各originでorderを選び直す
- RMSE差を経済的価値と呼ぶ

## 4. 段階別演習

### 基礎

1. AR(1)のstationarity条件を導出せよ。
2. level/changeのACF差を記述せよ。

### 標準

3. AR(1)とAR(2)をtraining/validationだけで比較せよ。
4. horizon 1と20でrandom-walkとの差を測れ。

### 研究

5. rolling-origin loss差へHAC standard errorを付ける設計を書け。

## 5. Exit Criteria

- [ ] stationarityとergodicityを区別した
- [ ] DF diagnosticを通常のt testと呼ばない
- [ ] publication horizonを使った
- [ ] random walkをbaselineに残した
- [ ] validation outcomeをorder選択以外へ漏らしていない

## 6. 出典

"""
            + TIME_SERIES_SOURCES
        ),
    ]


def week26_cells():
    return [
        md(r"""
# 38. Week 26 — VAR, predictive content, impulse responses, and cointegration

## 学習目標

- fixed-decay NS factorへVARをfitできる
- Granger predictive contentとstructural causalityを区別できる
- reduced-form IRFとorthogonalized IRFのordering依存を説明できる
- cointegrationを高いlevel correlationと区別できる

## 前提知識

- Week 25のstationarityとAR
- B1のNelson–Siegel loading
"""),
        setup_cell(38),
        treasury_curve_cell(),
        md(r"""
## 1. VAR and information set

$$
x_t=c+A_1x_{t-1}+\cdots+A_px_{t-p}+u_t.
$$

ここで (x_t) はlevel、slope、curvature factor。Granger検定の帰無仮説は「指定したlagと線形情報集合の中で追加の予測力がない」であり、政策的・構造的因果ではない。
"""),
        code("""
decay = 0.5
factors = qt.extract_nelson_siegel_factors(curve_yields, maturity_years, decay)
factor_names = ["level", "slope", "curvature"]
factor_model = qt.fit_var(factors[train_mask], 1)
granger_rows = []
for effect_index, effect_name in enumerate(factor_names):
    for cause_index, cause_name in enumerate(factor_names):
        if effect_index != cause_index:
            result = qt.granger_causality_test(
                np.diff(factors[train_mask, effect_index]),
                np.diff(factors[train_mask, cause_index]),
                lags=1,
            )
            granger_rows.append(
                {"effect": effect_name, "cause": cause_name, "f_statistic": result.f_statistic, "p_value": result.p_value}
            )
display(pd.DataFrame(granger_rows))
"""),
        code("""
responses = qt.impulse_response(factor_model, 20, orthogonalized=False)
fig = go.Figure()
for target_index, target_name in enumerate(factor_names):
    fig.add_scatter(
        x=np.arange(21),
        y=responses[:, target_index, 0],
        name=f"level shock to {target_name}",
        mode="lines+markers",
    )
fig.update_layout(
    title="Reduced-form VAR response to a unit level-factor innovation",
    xaxis_title="Publication horizon",
    yaxis_title="Factor response",
    template="plotly_white",
)
fig.show()
"""),
        md(r"""
## 2. Cointegration diagnostic

二つのlevel系列が非定常でも、ある (eta) について (y_t-\beta x_t) が定常ならcointegratedである。次のtwo-step diagnosticは正式なEngle–Granger critical valueを実装していないため、ordinary p-valueを出さない。
"""),
        code("""
level_design = np.column_stack([np.ones(np.sum(train_mask)), curve_yields[train_mask, 1]])
cointegration_beta = np.linalg.lstsq(level_design, curve_yields[train_mask, 3], rcond=None)[0]
cointegration_residual = curve_yields[train_mask, 3] - level_design @ cointegration_beta
cointegration_diagnostic = qt.dickey_fuller_diagnostic(cointegration_residual)
display(
    pd.DataFrame(
        [
            {
                "relationship": "10y on 2y",
                "intercept": cointegration_beta[0],
                "slope": cointegration_beta[1],
                "residual_df_t": cointegration_diagnostic.t_statistic,
                "calibrated_p_value_available": False,
            }
        ]
    )
)
"""),
        md(r"""
## 3. Validation forecast
"""),
        code("""
horizon = 5
origins = np.flatnonzero(
    (curve_dates > train_end_date)
    & (curve_dates <= validation_end_date)
    & (np.arange(curve_dates.size) + horizon < curve_dates.size)
)
origins = origins[curve_dates[origins + horizon] <= validation_end_date]
var_curve_predictions = np.vstack(
    [qt.forecast_var(factor_model, factors[: origin + 1], horizon)[-1] @ qt.nelson_siegel_loadings(maturity_years, decay).T for origin in origins]
)
random_walk_predictions = curve_yields[origins]
actual = curve_yields[origins + horizon]
display(
    pd.DataFrame(
        {
            "model": ["random walk", "factor VAR(1)"],
            "aggregate_rmse_bp": [
                100.0 * np.sqrt(np.mean((actual - random_walk_predictions) ** 2)),
                100.0 * np.sqrt(np.mean((actual - var_curve_predictions) ** 2)),
            ],
        }
    )
)
"""),
        md(
            r"""
## 4. 失敗モード

- Granger predictive contentを因果効果と呼ぶ
- level VARの高いfitだけを報告する
- Cholesky orderingを隠してorthogonalized IRFを構造shockと呼ぶ
- correlationだけでcointegrationと結論する
- factor extractionのdecayをouter testで選ぶ

## 5. 段階別演習

### 基礎

1. companion formでVAR(1)の安定性条件を書け。
2. reduced-formとorthogonalized IRFを比較せよ。

### 標準

3. factor orderingを変えてCholesky IRFの感応度を測れ。
4. VAR(1)とseparate AR(1)をvalidationで比較せよ。

### 研究

5. local projectionのestimandとHAC inference contractを設計せよ。

## 6. Exit Criteria

- [ ] VARへstationary transformationを検討した
- [ ] Grangerとcausalityを分離した
- [ ] IRFのshock normalizationを記録した
- [ ] cointegrationをresidual stationarityで定義した
- [ ] validation forecastをrandom walkと比較した

## 7. 出典

"""
            + TIME_SERIES_SOURCES
            + "\n- [Sims (1980), Macroeconomics and Reality](https://doi.org/10.2307/1912017)"
        ),
    ]


def week27_cells():
    return [
        md(r"""
# 39. Week 27 — Kalman filtering, smoothing, missing data, and DNS

## 学習目標

- linear-Gaussian predict/update recursionを導出できる
- filteringとsmoothingの情報集合を区別できる
- missing tenorでupdate rowを落とす処理を検証できる
- fixed-decay Dynamic Nelson–Siegelをfitし5公表日先を予測できる

## 前提知識

- multivariate Gaussian conditioning
- Week 26のNelson–Siegel factorsとVAR
"""),
        setup_cell(39),
        treasury_curve_cell(),
        md(r"""
## 1. Linear-Gaussian state space

$$
x_t=c+Fx_{t-1}+\eta_t,\qquad y_t=Hx_t+\varepsilon_t,
$$

$$
K_t=P_{t|t-1}H^\top(HP_{t|t-1}H^\top+R)^{-1}.
$$

実装はinverseを作らずlinear solveを使う。filter (p(x_t\mid y_{1:t})) はforecast originで利用可能、smoother (p(x_t\mid y_{1:T})) はretrospective diagnostic専用である。
"""),
        code("""
training_change = np.diff(curve_yields[train_mask, 3])
level_q = np.var(training_change, ddof=1)
level_r = max(0.25 * level_q, 1e-8)
available = curve_dates <= validation_end_date
local_level = qt.kalman_filter(
    curve_yields[available, 3],
    [[1.0]],
    [[1.0]],
    [[level_q]],
    [[level_r]],
    [curve_yields[0, 3]],
    [[1.0]],
)
local_smoother = qt.kalman_smoother(local_level, [[1.0]])
assert np.allclose(local_smoother.smoothed_means[-1], local_level.filtered_means[-1])

fig = go.Figure()
fig.add_scatter(x=curve_dates[available], y=curve_yields[available, 3], name="observed 10y", mode="lines")
fig.add_scatter(x=curve_dates[available], y=local_level.filtered_means[:, 0], name="filtered", mode="lines")
fig.add_scatter(x=curve_dates[available], y=local_smoother.smoothed_means[:, 0], name="smoothed", mode="lines")
fig.update_layout(title="Filtering is online; smoothing is retrospective", yaxis_title="10y CMT (%)", template="plotly_white")
fig.show()
"""),
        md(r"""
## 2. Missing-observation audit

validationの10年tenorを規則的にblankへ置換する。これは市場値の擬似生成ではなく、欠測処理を既知マスクで検証するstress testである。
"""),
        code("""
missing_panel = curve_yields[available].copy()
validation_rows = np.flatnonzero((curve_dates[available] > train_end_date) & (curve_dates[available] <= validation_end_date))
missing_rows = validation_rows[::17]
missing_panel[missing_rows, 3] = np.nan

dns_model = qt.fit_dynamic_nelson_siegel(curve_yields[train_mask], maturity_years, decay=0.5)
complete_filter = qt.filter_dynamic_nelson_siegel(dns_model, curve_yields[available])
missing_filter = qt.filter_dynamic_nelson_siegel(dns_model, missing_panel)
assert not np.any(missing_filter.observed_mask[missing_rows, 3])
missing_audit = pd.DataFrame(
    {
        "metric": ["blanked 10y rows", "complete log likelihood", "missing-panel log likelihood", "mean filtered-state difference"],
        "value": [
            len(missing_rows),
            complete_filter.log_likelihood,
            missing_filter.log_likelihood,
            np.mean(np.linalg.norm(complete_filter.filtered_means - missing_filter.filtered_means, axis=1)),
        ],
    }
)
display(missing_audit)
"""),
        md(r"""
## 3. Five-publication DNS forecast
"""),
        code("""
last_validation_origin = np.flatnonzero(curve_dates <= validation_end_date)[-6]
origin_filter = qt.filter_dynamic_nelson_siegel(dns_model, curve_yields[: last_validation_origin + 1])
predictive = qt.forecast_dynamic_nelson_siegel(
    dns_model,
    origin_filter.filtered_means[-1],
    origin_filter.filtered_covariances[-1],
    5,
)
display(
    pd.DataFrame(
        {
            "tenor": qt.DEFAULT_TENORS,
            "forecast_percent": predictive.mean,
            "actual_percent": curve_yields[last_validation_origin + 5],
            "forecast_standard_deviation_bp": 100.0 * np.sqrt(np.diag(predictive.covariance)),
        }
    )
)
"""),
        md(
            r"""
## 4. 失敗モード

- smoothed stateをhistorical forecast originへ戻して使う
- missing値をzero yieldとしてupdateする
- (Q,R,F) をouter testで調整する
- covarianceのPSD、innovation、log likelihoodを監査しない
- fixed decayのtwo-step DNSをjoint maximum likelihoodと呼ぶ

## 5. 段階別演習

### 基礎

1. scalar local-level filterのgainを導出せよ。
2. 全tenor missingの日にpredictだけが行われることを確認せよ。

### 標準

3. missing率を1%、10%、30%へ変えfilter感応度を測れ。
4. decay 0.25/0.5/1.0をvalidation likelihoodで比較するprotocolを書け。

### 研究

5. EMで (Q,R) を推定するときのinitializationとlocal optimum監査を設計せよ。

## 6. Exit Criteria

- [ ] filterとsmootherの条件付け集合を書ける
- [ ] missing rowを観測方程式から除外した
- [ ] covarianceを対称PSDとして監査した
- [ ] forecast originではfiltered stateだけを使った
- [ ] DNS two-step estimationの限界を明記した

## 7. 出典

"""
            + STATE_SPACE_SOURCES
        ),
    ]


def week28_cells():
    return [
        md(r"""
# 40. Week 28 — Conditional volatility, breaks, and regime-dependent evaluation

## 学習目標

- GARCH(1,1)のvariance recursionとstationarity条件を説明できる
- daily squared change proxyとintraday realized volatilityを区別できる
- methodology break前後のdiagnosticを分けられる
- conditional variance forecastをpoint forecastと別metricで評価できる

## 前提知識

- maximum likelihood、conditional expectation
- Treasury methodology break contract
"""),
        setup_cell(40),
        treasury_curve_cell(),
        md(r"""
## 1. GARCH contract

$$
h_t=\omega+\alpha\varepsilon_{t-1}^2+\beta h_{t-1},\qquad
\omega>0,\ \alpha,\beta\ge0,\ \alpha+\beta<1.
$$

本データは公表日ごとのyieldだけで、intraday returnを持たない。したがって ((\Delta y_t)^2) は日次変化のnoisy proxyであり、realized volatilityとは呼ばない。
"""),
        code("""
ten_year_change_bp = curve_changes_bp[:, 3]
training_changes = ten_year_change_bp[change_dates <= train_end_date]
garch = qt.fit_garch11(training_changes)
display(
    pd.DataFrame(
        [
            {
                "omega": garch.omega,
                "alpha": garch.alpha,
                "beta": garch.beta,
                "persistence": garch.alpha + garch.beta,
                "converged": garch.converged,
                "iterations": garch.n_iterations,
            }
        ]
    )
)
assert garch.alpha + garch.beta < 1.0
"""),
        code("""
audit_mask = change_dates <= validation_end_date
audit_changes = ten_year_change_bp[audit_mask]
conditional_variance = np.empty(audit_changes.size)
conditional_variance[0] = np.var(training_changes, ddof=1)
for index in range(1, audit_changes.size):
    conditional_variance[index] = (
        garch.omega
        + garch.alpha * audit_changes[index - 1] ** 2
        + garch.beta * conditional_variance[index - 1]
    )
rolling_proxy = pd.Series(audit_changes).rolling(20).std().to_numpy()

fig = go.Figure()
fig.add_scatter(x=change_dates[audit_mask], y=np.sqrt(conditional_variance), name="GARCH conditional sigma", mode="lines")
fig.add_scatter(x=change_dates[audit_mask], y=rolling_proxy, name="20-publication rolling sigma", mode="lines")
fig.add_vline(x=qt.TREASURY_METHOD_BREAK.timestamp() * 1000, line_dash="dash", line_color="black")
fig.update_layout(
    title="10y change volatility diagnostics through validation",
    xaxis_title="Treasury publication date",
    yaxis_title="Volatility proxy (bp)",
    template="plotly_white",
)
fig.show()
"""),
        md(r"""
## 2. Break-aware audit
"""),
        code("""
break_date = qt.TREASURY_METHOD_BREAK.to_datetime64()
period_rows = []
for period, mask in [
    ("pre-methodology-break", (change_dates <= train_end_date) & (change_dates < break_date)),
    ("post-methodology-break validation", (change_dates > train_end_date) & (change_dates <= validation_end_date) & (change_dates >= break_date)),
]:
    values = ten_year_change_bp[mask]
    period_rows.append(
        {
            "period": period,
            "observations": values.size,
            "mean_bp": values.mean(),
            "standard_deviation_bp": values.std(ddof=1),
            "mean_squared_change": np.mean(values**2),
        }
    )
display(pd.DataFrame(period_rows))
"""),
        md(
            r"""
## 3. 失敗モード

- squared daily yield changeをrealized volatilityと呼ぶ
- (alpha+\beta\ge1) のfitを無条件に長期varianceへ外挿する
- method change前後を同質と仮定する
- volatility forecastをdirection/level forecastと混ぜる
- stress periodを見てregime thresholdを後付けする

## 4. 段階別演習

### 基礎

1. GARCHのunconditional varianceを導出せよ。
2. rolling standard deviationとconditional sigmaを比較せよ。

### 標準

3. Gaussian QLIKEを定義しvalidationでconstant varianceと比較せよ。
4. methodology break前後でparameter stabilityを測れ。

### 研究

5. intraday dataを得た場合のmicrostructure-noise robust estimatorを調査せよ。

## 5. Exit Criteria

- [ ] GARCH parameter constraintを検査した
- [ ] volatility proxyの観測限界を明記した
- [ ] methodology breakを可視化した
- [ ] varianceとmean forecastの評価を分けた
- [ ] regimeを観測真値と呼んでいない

## 6. 出典

- [Engle (1982), ARCH](https://doi.org/10.2307/1912773)
- [Bollerslev (1986), Generalized ARCH](https://doi.org/10.1016/0304-4076(86)90063-1)
"""
            + TIME_SERIES_SOURCES
        ),
    ]


def project_cells():
    return [
        md(r"""
# 41. B7 Project — Dynamic Treasury Curve Forecasting Audit

> 外部テストの役割はwinnerを作ることではなく、事前固定した動学modelがrandom walkを超えるかを一度だけ反証することである。

## 学習目標

- B5/B6と同じouter-test境界で5公表日先のcurve forecastを作れる
- random walk、static NS、factor AR、factor VAR、Kalman DNSを比較できる
- maturity別RMSEとDNS coverageを別々に評価できる
- filtered/smoothed、missing、parameter stability、methodology breakを監査できる
- price/hedge/PnL claimをデータ境界から除外できる

## 前提知識

- Week 25–28の全Exit Criteria
- B5/B6のlocked test discipline
"""),
        setup_cell(41),
        treasury_curve_cell(),
        md(r"""
## 1. Locked Project contract

| Field | Value |
|---|---|
| Target | five-tenor curve at (t+5), observed minus predicted in bp |
| Time unit | Treasury publication observations |
| Parameters | fit before B5 outer-test start |
| Online state | filtered only |
| Primary metrics | maturity-level and aggregate RMSE |
| Distribution metric | marginal 90% coverage and width for DNS |
| Secondary horizons | 1 and 20 publication observations |
| Prohibited | test-driven tuning, smoothed-state forecast, bond hedge/PnL claim |
"""),
        code("""
decay = 0.5
loadings = qt.nelson_siegel_loadings(maturity_years, decay)
pretest_mask = curve_dates < test_start_date
pretest_yields = curve_yields[pretest_mask]
pretest_factors = qt.extract_nelson_siegel_factors(pretest_yields, maturity_years, decay)
all_factors = qt.extract_nelson_siegel_factors(curve_yields, maturity_years, decay)

dns = qt.fit_dynamic_nelson_siegel(pretest_yields, maturity_years, decay=decay)
dns_filter = qt.filter_dynamic_nelson_siegel(dns, curve_yields)
factor_var = qt.fit_var(pretest_factors, 1)
factor_ar = [qt.fit_ar(pretest_factors[:, index], 1) for index in range(3)]

stability_rows = []
for label, mask in [
    ("pre-methodology-break", curve_dates < qt.TREASURY_METHOD_BREAK.to_datetime64()),
    ("post-break pretest", (curve_dates >= qt.TREASURY_METHOD_BREAK.to_datetime64()) & pretest_mask),
]:
    if np.sum(mask) >= 30:
        fitted = qt.fit_dynamic_nelson_siegel(curve_yields[mask], maturity_years, decay=decay)
        stability_rows.append(
            {"period": label, "observations": int(np.sum(mask)), "transition_spectral_radius": np.max(np.abs(np.linalg.eigvals(fitted.transition)))}
        )
display(pd.DataFrame(stability_rows))
"""),
        md(r"""
## 2. One-use outer test

test中も日々の公式curveはforecast originで観察できるためfilter updateとlag historyへ追加できる。一方、transition、variance、decayはpretestで固定する。
"""),
        code("""
primary_horizon = 5
origins = np.flatnonzero(
    (curve_dates >= test_start_date)
    & (np.arange(curve_dates.size) + primary_horizon < curve_dates.size)
)
actual = curve_yields[origins + primary_horizon]
predictions = {
    "random walk": curve_yields[origins],
    "static NS": all_factors[origins] @ loadings.T,
    "factor VAR(1)": np.vstack(
        [qt.forecast_var(factor_var, all_factors[: origin + 1], primary_horizon)[-1] @ loadings.T for origin in origins]
    ),
    "factor AR(1)": np.vstack(
        [
            np.array(
                [qt.forecast_ar(factor_ar[index], all_factors[: origin + 1, index], primary_horizon)[-1] for index in range(3)]
            ) @ loadings.T
            for origin in origins
        ]
    ),
}

dns_predictives = [
    qt.forecast_dynamic_nelson_siegel(
        dns,
        dns_filter.filtered_means[origin],
        dns_filter.filtered_covariances[origin],
        primary_horizon,
    )
    for origin in origins
]
predictions["Kalman DNS"] = np.vstack([item.mean for item in dns_predictives])
dns_standard_deviation = np.vstack([np.sqrt(np.diag(item.covariance)) for item in dns_predictives])

metric_rows = []
for model_name, prediction in predictions.items():
    for tenor_index, tenor in enumerate(qt.DEFAULT_TENORS):
        metric_rows.append(
            {
                "model": model_name,
                "tenor": tenor,
                "rmse_bp": 100.0 * np.sqrt(np.mean((actual[:, tenor_index] - prediction[:, tenor_index]) ** 2)),
                "mae_bp": 100.0 * np.mean(np.abs(actual[:, tenor_index] - prediction[:, tenor_index])),
            }
        )
metric_table = pd.DataFrame(metric_rows)
display(metric_table.pivot(index="model", columns="tenor", values="rmse_bp"))
random_walk_rmse = metric_table.loc[metric_table["model"] == "random walk", "rmse_bp"].to_numpy()
candidate_gate = {}
for model_name in [name for name in predictions if name != "random walk"]:
    candidate_rmse = metric_table.loc[metric_table["model"] == model_name, "rmse_bp"].to_numpy()
    candidate_gate[model_name] = bool(np.all(candidate_rmse < random_walk_rmse))
selected_candidates = [name for name, passed in candidate_gate.items() if passed]
print("candidate gate by model:", candidate_gate)
print("project conclusion:", "no model selected" if not selected_candidates else selected_candidates)
"""),
        code("""
fig = go.Figure()
for model_name in predictions:
    rows = metric_table[metric_table["model"] == model_name]
    fig.add_scatter(x=rows["tenor"], y=rows["rmse_bp"], name=model_name, mode="lines+markers")
fig.update_layout(
    title="Locked-test five-publication curve RMSE by maturity",
    xaxis_title="Treasury tenor",
    yaxis_title="RMSE (bp)",
    template="plotly_white",
)
fig.show()
"""),
        md(r"""
## 3. Distribution, horizon, and information-set audits
"""),
        code("""
z90 = 1.6448536269514722
dns_error = actual - predictions["Kalman DNS"]
coverage_rows = []
for tenor_index, tenor in enumerate(qt.DEFAULT_TENORS):
    covered = np.abs(dns_error[:, tenor_index]) <= z90 * dns_standard_deviation[:, tenor_index]
    coverage_rows.append(
        {
            "tenor": tenor,
            "coverage_90": covered.mean(),
            "mean_width_bp": 200.0 * z90 * dns_standard_deviation[:, tenor_index].mean(),
        }
    )
display(pd.DataFrame(coverage_rows))

secondary_rows = []
for horizon in [1, 20]:
    horizon_origins = np.flatnonzero((curve_dates >= test_start_date) & (np.arange(curve_dates.size) + horizon < curve_dates.size))
    horizon_actual = curve_yields[horizon_origins + horizon]
    horizon_dns = np.vstack(
        [
            qt.forecast_dynamic_nelson_siegel(
                dns,
                dns_filter.filtered_means[origin],
                dns_filter.filtered_covariances[origin],
                horizon,
            ).mean
            for origin in horizon_origins
        ]
    )
    secondary_rows.extend(
        [
            {"horizon": horizon, "model": "random walk", "aggregate_rmse_bp": 100.0 * np.sqrt(np.mean((horizon_actual - curve_yields[horizon_origins]) ** 2))},
            {"horizon": horizon, "model": "Kalman DNS", "aggregate_rmse_bp": 100.0 * np.sqrt(np.mean((horizon_actual - horizon_dns) ** 2))},
        ]
    )
display(pd.DataFrame(secondary_rows))

pretest_filter = qt.filter_dynamic_nelson_siegel(dns, pretest_yields)
pretest_smoother = qt.kalman_smoother(pretest_filter, dns.transition)
retrospective_difference = np.mean(
    np.linalg.norm(pretest_filter.filtered_means - pretest_smoother.smoothed_means, axis=1)
)
print("retrospective filtered-smoothed factor difference:", retrospective_difference)
print("forecast inputs are filtered only:", True)
"""),
        md(
            r"""
## 4. Claim audit and unavailable economic evidence

本snapshotにはcoupon cash flows、tradable prices、bid–ask、funding、duration hedge instrumentがない。したがって原カリキュラムのhedge errorは本Core projectでは識別できず、作らない。maturity別yield RMSEは統計的予測精度であり、経済価値ではない。

Project結論は「predeclared modelのhistorical outer-test比較」に限定する。outer testを見た後のwinner採用やdecay再調整は次の新しいholdoutが必要である。

## 5. 失敗モード

- outer testでdecayやstate equationを選ぶ
- full-sample smootherをforecastへ使う
- same-date curve fitをfuture forecastと数える
- marginal 90% intervalをjoint curve coverageと呼ぶ
- yield RMSEをhedge/PnLへ換算する
- 1/20 horizonをprimary結果にすり替える

## 6. 段階別演習

### 基礎

1. model別・tenor別error tableを再現せよ。
2. filteredとsmoothed stateの差をplotせよ。

### 標準

3. validationだけでdecay候補を選ぶ将来protocolを書け。
4. artificial missingnessの率別stress testを追加せよ。

### 研究

5. tradable cash instrumentを合法に取得できる場合のhedge-error estimandを定義せよ。
6. block-aware uncertaintyでRMSE差を評価せよ。

## 7. Exit Criteria

- [ ] B5/B6と同じouter-test開始日を使用した
- [ ] 5公表日先をprimaryとした
- [ ] random walk、static NS、AR、VAR、Kalman DNSを比較した
- [ ] maturity別RMSEとcoverage/widthを分離した
- [ ] forecastにはfiltered stateだけを使った
- [ ] missing、parameter stability、methodology breakを監査した
- [ ] hedge/PnL claimをデータ不足として除外した

## 8. 出典

"""
            + TIME_SERIES_SOURCES
            + STATE_SPACE_SOURCES
        ),
    ]


__all__ = [
    "overview_cells",
    "project_cells",
    "week25_cells",
    "week26_cells",
    "week27_cells",
    "week28_cells",
]
