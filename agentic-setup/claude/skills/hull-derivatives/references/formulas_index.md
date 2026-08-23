# Formulas Index

Every formula listed across the Hull 11e chapter files, grouped by topic. Each entry links back to its source chapter.

> **How to read**: each line is `**<formula name>**: brief description → [chapter](path)`. Find a topic, scan the formulas, click through to the chapter for the LaTeX, symbols, and Python implementation.

## Forwards / Futures

- **Forward payoff (long)** $S_T - K$ → [ch01](chapters/ch01_introduction.md)
- **Forward payoff (short)** $K - S_T$ → [ch01](chapters/ch01_introduction.md)
- **Forward price (no income)** $F_0 = S_0 e^{rT}$ → [ch05](chapters/ch05_forward_futures_pricing.md)
- **Forward price (known cash income)** $F_0 = (S_0 - I)e^{rT}$ → [ch05](chapters/ch05_forward_futures_pricing.md)
- **Forward price (continuous yield $q$)** $F_0 = S_0 e^{(r-q)T}$ → [ch05](chapters/ch05_forward_futures_pricing.md), [ch17](chapters/ch17_index_currency_options.md)
- **Long forward value** $f = (F_0 - K)e^{-rT}$ → [ch05](chapters/ch05_forward_futures_pricing.md)
- **FX forward (covered interest parity)** $F_0 = S_0 e^{(r-r_f)T}$ → [ch05](chapters/ch05_forward_futures_pricing.md)
- **Commodity forward (storage cost $U$)** $F_0 = (S_0 + U)e^{rT}$ → [ch05](chapters/ch05_forward_futures_pricing.md)
- **Convenience yield** $F_0 = S_0 e^{(r+u-y)T}$ → [ch05](chapters/ch05_forward_futures_pricing.md), [ch35](chapters/ch35_commodity_energy.md)
- **Cost-of-carry (general)** $F_0 = S_0 e^{cT}$; consumption asset $F_0 = S_0 e^{(c-y)T}$ → [ch05](chapters/ch05_forward_futures_pricing.md)
- **Daily P&L (mark-to-market)** $\Delta V_t = (F_t - F_{t-1}) \times N$ → [ch02](chapters/ch02_futures_markets.md)
- **Margin call condition** $B_t < M_\text{maintenance}$; call = $M_\text{initial} - B_t$ → [ch02](chapters/ch02_futures_markets.md)
- **Futures SDE (risk-neutral)** $dF = \sigma F\,dz$ (zero drift) → [ch18](chapters/ch18_futures_options_black.md)

## Interest Rates

- **Compounding (m times/year)** $A(1 + R/m)^{mn}$ → [ch04](chapters/ch04_interest_rates.md)
- **Continuous compounding** $A e^{R_c n}$ → [ch04](chapters/ch04_interest_rates.md)
- **Rate conversion (m-freq ↔ continuous)** $R_c = m\ln(1 + R_m/m)$ → [ch04](chapters/ch04_interest_rates.md)
- **Bond price (zero rates)** $B = \sum c_i e^{-R(t_i)t_i}$ → [ch04](chapters/ch04_interest_rates.md)
- **Yield to maturity** $B = \sum c_i e^{-y t_i}$ (solve for $y$) → [ch04](chapters/ch04_interest_rates.md)
- **Par yield** $c = (100 - 100d)m / A$ → [ch04](chapters/ch04_interest_rates.md)
- **Forward rate** $R_F = (R_2 T_2 - R_1 T_1)/(T_2 - T_1)$ → [ch04](chapters/ch04_interest_rates.md)
- **FRA value (receive fixed)** $V_\text{FRA} = L(R_K - R_F)(T_2 - T_1)e^{-R_2 T_2}$ → [ch04](chapters/ch04_interest_rates.md)
- **Macaulay duration** $D = \sum t_i c_i e^{-y t_i}/B$ → [ch04](chapters/ch04_interest_rates.md)
- **Duration price sensitivity** $\Delta B \approx -BD\,\Delta y$ → [ch04](chapters/ch04_interest_rates.md)
- **Modified duration** $D^* = D/(1 + y/m)$; $\Delta B = -BD^*\Delta y$ → [ch04](chapters/ch04_interest_rates.md)
- **T-bond dirty price** Cash Price = Quoted Price + Accrued Interest → [ch06](chapters/ch06_ir_futures.md)
- **T-bill discount quote** $P = (360/n)(100 - Y)$ → [ch06](chapters/ch06_ir_futures.md)
- **T-bond futures invoice price** = Settlement price × CF + Accrued interest → [ch06](chapters/ch06_ir_futures.md)
- **CTD bond criterion** minimize: Quoted bond price − Settlement price × CF → [ch06](chapters/ch06_ir_futures.md)
- **T-bond futures price (CTD known)** $F_0 = (S_0 - I)e^{rT}$ → [ch06](chapters/ch06_ir_futures.md)
- **Eurodollar/SOFR DV01** $\$25$ per bp per contract → [ch06](chapters/ch06_ir_futures.md)
- **Convexity adjustment (futures → forward rate)** forward = futures $- \tfrac{1}{2}\sigma^2 t_1 t_2$ → [ch06](chapters/ch06_ir_futures.md), [ch30](chapters/ch30_convexity_timing_quanto.md)

## Hedging

- **Basis** $b = S - F$ → [ch03](chapters/ch03_hedging.md)
- **Short hedge realized price** $S_2 + F_1 - F_2 = F_1 + b_2$ → [ch03](chapters/ch03_hedging.md)
- **Optimal hedge ratio** $h^* = \rho\,\sigma_S/\sigma_F$ → [ch03](chapters/ch03_hedging.md)
- **Hedge effectiveness** $= \rho^2$ → [ch03](chapters/ch03_hedging.md)
- **Optimal futures contracts (size-based)** $N^* = h^* Q_A / Q_F$ → [ch03](chapters/ch03_hedging.md)
- **Optimal futures contracts (value-based, tailing)** $N^* = \hat{h}\,V_A/V_F$ → [ch03](chapters/ch03_hedging.md)
- **Equity portfolio hedge (beta)** $N^* = \beta\,V_A/V_F$ → [ch03](chapters/ch03_hedging.md)
- **Portfolio insurance (number of contracts)** $N^* = V_A/V_F$ (index mirror) → [ch03](chapters/ch03_hedging.md), [ch17](chapters/ch17_index_currency_options.md)

## Swaps

- **IRS fixed cash flow** $CF_\text{fix} = -L s\tau_i$ → [ch07](chapters/ch07_swaps.md)
- **IRS floating cash flow** $CF_\text{fl} = L R_i n_i/360$ → [ch07](chapters/ch07_swaps.md)
- **Swap value (bond decomposition)** $V_\text{swap} = B_\text{fix} - B_\text{fl}$ → [ch07](chapters/ch07_swaps.md)
- **Floating leg value** $B_\text{fl} = (L + Lr^*\tau_1)P(0,t_1)$ (resets to par) → [ch07](chapters/ch07_swaps.md)
- **At-market swap rate** $s = (1 - P(0,t_n)) / \sum\tau_i P(0,t_i)$ → [ch07](chapters/ch07_swaps.md)
- **Currency swap value (bond approach)** $V_\text{swap} = B_D - S_0 B_F$ → [ch07](chapters/ch07_swaps.md)
- **LIBOR-in-arrears convexity adjustment** $\hat{F} = F + F^2\sigma^2\tau T/(1+F\tau)$ → [ch34](chapters/ch34_swaps_revisited.md)
- **CMS convexity adjustment** $\hat{s} = s_0 + \tfrac{1}{2}s_0^2\sigma^2 T\,G''(s_0)/G'(s_0)$ → [ch34](chapters/ch34_swaps_revisited.md)
- **Quanto (diff swap) adjustment** $\hat{F}_f = F_f - \rho\sigma_f\sigma_X T$ → [ch34](chapters/ch34_swaps_revisited.md)
- **Equity swap period value (receive equity)** $V = L(E - E_0)/E_0 - \text{PV(float)}$ → [ch34](chapters/ch34_swaps_revisited.md)

## Options — Payoffs & Bounds

- **Long call payoff** $\max(S_T - K, 0)$ → [ch10](chapters/ch10_options_mechanics.md)
- **Long put payoff** $\max(K - S_T, 0)$ → [ch10](chapters/ch10_options_mechanics.md)
- **Naked call margin (CBOE)** $\max(\text{proceeds} + 0.20S - \text{OTM}, \text{proceeds} + 0.10S)$ → [ch10](chapters/ch10_options_mechanics.md)
- **Stock split adjustment** $K_\text{new} = K_\text{old} \times m/n$; $N_\text{new} = N_\text{old} \times n/m$ → [ch10](chapters/ch10_options_mechanics.md)
- **European call lower bound (no div)** $c \ge \max(S_0 - Ke^{-rT}, 0)$ → [ch11](chapters/ch11_option_properties.md)
- **European put lower bound (no div)** $p \ge \max(Ke^{-rT} - S_0, 0)$ → [ch11](chapters/ch11_option_properties.md)
- **Put-call parity (European, no div)** $c + Ke^{-rT} = p + S_0$ → [ch11](chapters/ch11_option_properties.md), [ch12](chapters/ch12_option_strategies.md)
- **Put-call parity (European, yield $q$)** $c + Ke^{-rT} = p + S_0 e^{-qT}$ → [ch11](chapters/ch11_option_properties.md), [ch17](chapters/ch17_index_currency_options.md)
- **Put-call parity (European, discrete div)** $c + D + Ke^{-rT} = p + S_0$ → [ch11](chapters/ch11_option_properties.md)
- **US put-call inequality (no div)** $S_0 - K \le C - P \le S_0 - Ke^{-rT}$ → [ch11](chapters/ch11_option_properties.md)
- **Bull call spread payoff** $\min(\max(S_T - K_1, 0), K_2 - K_1)$ → [ch12](chapters/ch12_option_strategies.md)
- **Bear put spread payoff** $\min(\max(K_2 - S_T, 0), K_2 - K_1)$ → [ch12](chapters/ch12_option_strategies.md)
- **Butterfly spread payoff** long $K_1$, 2×short $K_2$, long $K_3$ → [ch12](chapters/ch12_option_strategies.md)
- **Straddle payoff** $|S_T - K|$ → [ch12](chapters/ch12_option_strategies.md)
- **Strangle payoff** $\max(K_1 - S_T, 0) + \max(S_T - K_2, 0)$ ($K_1 < K_2$) → [ch12](chapters/ch12_option_strategies.md)
- **Box spread value** $(K_2 - K_1)e^{-rT}$ → [ch12](chapters/ch12_option_strategies.md)

## Black-Scholes-Merton

- **Geometric Brownian motion (GBM)** $dS = \mu S\,dt + \sigma S\,dz$ → [ch14](chapters/ch14_wiener_ito.md)
- **Log-normal stock price** $\ln S_T \sim N(\ln S_0 + (\mu - \sigma^2/2)T,\,\sigma^2 T)$ → [ch15](chapters/ch15_bsm.md)
- **Expected stock price** $E(S_T) = S_0 e^{\mu T}$ → [ch15](chapters/ch15_bsm.md)
- **BSM PDE** $\partial f/\partial t + rS\partial f/\partial S + \tfrac{1}{2}\sigma^2 S^2\partial^2 f/\partial S^2 = rf$ → [ch15](chapters/ch15_bsm.md)
- **BSM call (no div)** $c = S_0 N(d_1) - Ke^{-rT}N(d_2)$ → [ch15](chapters/ch15_bsm.md)
- **BSM put (no div)** $p = Ke^{-rT}N(-d_2) - S_0 N(-d_1)$ → [ch15](chapters/ch15_bsm.md)
- **$d_1$, $d_2$ (no div)** $d_1 = [\ln(S_0/K) + (r+\sigma^2/2)T]/(\sigma\sqrt{T})$; $d_2 = d_1 - \sigma\sqrt{T}$ → [ch15](chapters/ch15_bsm.md)
- **Merton extension (continuous yield $q$)** $c = S_0 e^{-qT}N(d_1) - Ke^{-rT}N(d_2)$ → [ch15](chapters/ch15_bsm.md), [ch17](chapters/ch17_index_currency_options.md)
- **$d_1$ with yield $q$** $d_1 = [\ln(S_0/K) + (r-q+\sigma^2/2)T]/(\sigma\sqrt{T})$ → [ch17](chapters/ch17_index_currency_options.md), [ch19](chapters/ch19_greeks.md)
- **BSM with discrete dividends** $S_0' = S_0 - \sum D_i e^{-rt_i}$ → [ch15](chapters/ch15_bsm.md)
- **Garman-Kohlhagen (FX option)** $c = S_0 e^{-r_f T}N(d_1) - Ke^{-rT}N(d_2)$; $d_1$ uses $r - r_f$ → [ch17](chapters/ch17_index_currency_options.md)
- **Forward-price form of BSM** $c = (F_0 N(d_1) - KN(d_2))e^{-rT}$; $d_1 = [\ln(F_0/K) + \sigma^2 T/2]/(\sigma\sqrt{T})$ → [ch17](chapters/ch17_index_currency_options.md)
- **Black's model (futures call)** $c = e^{-rT}[F_0 N(d_1) - KN(d_2)]$ → [ch18](chapters/ch18_futures_options_black.md)
- **Black's model (futures put)** $p = e^{-rT}[KN(-d_2) - F_0 N(-d_1)]$ → [ch18](chapters/ch18_futures_options_black.md)
- **Put-call parity (futures options)** $c + Ke^{-rT} = p + F_0 e^{-rT}$ → [ch18](chapters/ch18_futures_options_black.md)
- **ESO valuation (expected-life approx)** $V_\text{ESO} = \text{BSM}(S_0, K, r, \sigma, q, T_\text{exp})$ → [ch16](chapters/ch16_employee_stock_options.md)
- **ESO dilution adjustment** $V_\text{diluted} = N/(N+M) \cdot V_\text{BSM}$ → [ch16](chapters/ch16_employee_stock_options.md)

## Greeks

- **Delta (call)** $\Delta_c = e^{-qT}N(d_1)$ → [ch19](chapters/ch19_greeks.md)
- **Delta (put)** $\Delta_p = e^{-qT}(N(d_1) - 1)$ → [ch19](chapters/ch19_greeks.md)
- **Portfolio delta** $\Delta_\Pi = \sum w_i \Delta_i$ → [ch19](chapters/ch19_greeks.md)
- **Gamma** $\Gamma = e^{-qT}N'(d_1)/(S\sigma\sqrt{T})$ → [ch19](chapters/ch19_greeks.md)
- **Theta (call)** $\Theta_c = -Se^{-qT}N'(d_1)\sigma/(2\sqrt{T}) - rKe^{-rT}N(d_2) + qSe^{-qT}N(d_1)$ → [ch19](chapters/ch19_greeks.md)
- **Vega** $\mathcal{V} = Se^{-qT}N'(d_1)\sqrt{T}$ → [ch19](chapters/ch19_greeks.md)
- **Rho (call)** $\rho_c = KTe^{-rT}N(d_2)$ → [ch19](chapters/ch19_greeks.md)
- **Rho (put)** $\rho_p = -KTe^{-rT}N(-d_2)$ → [ch19](chapters/ch19_greeks.md)
- **Gamma-neutral add** $w_T = -\Gamma/\Gamma_T$ units of traded option → [ch19](chapters/ch19_greeks.md)
- **Vega-neutral add** $-\mathcal{V}/\mathcal{V}_T$ units of traded option → [ch19](chapters/ch19_greeks.md)
- **Delta of forward** $\Delta_\text{fwd} = e^{-qT}$ → [ch19](chapters/ch19_greeks.md)
- **BSM gamma-theta relationship** $\Theta + rS\Delta + \tfrac{1}{2}\sigma^2 S^2\Gamma = rf$ → [ch19](chapters/ch19_greeks.md)

## Binomial / Lattice

- **1-step option price** $f = e^{-rT}[pf_u + (1-p)f_d]$ → [ch13](chapters/ch13_binomial_trees.md)
- **Risk-neutral probability** $p = (e^{r\Delta t} - d)/(u - d)$ → [ch13](chapters/ch13_binomial_trees.md)
- **Delta from tree node** $\Delta = (f_u - f_d)/(S_0 u - S_0 d)$ → [ch13](chapters/ch13_binomial_trees.md)
- **CRR parameters** $u = e^{\sigma\sqrt{\Delta t}}$; $d = 1/u$ → [ch13](chapters/ch13_binomial_trees.md), [ch21](chapters/ch21_basic_numerical.md)
- **Risk-neutral prob (continuous yield $q$)** $p = (e^{(r-q)\Delta t} - d)/(u-d)$ → [ch13](chapters/ch13_binomial_trees.md), [ch21](chapters/ch21_basic_numerical.md)
- **Control variate correction** $f^* = f_\text{Am,tree} + (f_\text{Eu,BSM} - f_\text{Eu,tree})$ → [ch21](chapters/ch21_basic_numerical.md)
- **Trinomial tree probabilities** $p_u = \tfrac{1}{6} + \tfrac{1}{2}(\ldots)$; $p_m = \tfrac{2}{3}$; $p_d = \tfrac{1}{6} - \tfrac{1}{2}(\ldots)$ → [ch21](chapters/ch21_basic_numerical.md)
- **Time-varying rates** $a = e^{[f(t)-g(t)]\Delta t}$ → [ch21](chapters/ch21_basic_numerical.md)
- **American futures option risk-neutral prob** $p = (1-d)/(u-d)$ → [ch18](chapters/ch18_futures_options_black.md)

## Stochastic Calculus

- **Wiener process increment** $\Delta z = \epsilon\sqrt{\Delta t}$; $\epsilon \sim N(0,1)$ → [ch14](chapters/ch14_wiener_ito.md)
- **Generalized Wiener process** $dx = a\,dt + b\,dz$ → [ch14](chapters/ch14_wiener_ito.md)
- **Itô process** $dx = a(x,t)\,dt + b(x,t)\,dz$ → [ch14](chapters/ch14_wiener_ito.md)
- **Itô's lemma** $dG = (\partial G/\partial x \cdot a + \partial G/\partial t + \tfrac{1}{2}\partial^2 G/\partial x^2 \cdot b^2)dt + \partial G/\partial x \cdot b\,dz$ → [ch14](chapters/ch14_wiener_ito.md)
- **Market price of risk (1-factor)** $\lambda = (\mu - r)/\sigma$ → [ch28](chapters/ch28_martingales_measures.md), [ch36](chapters/ch36_real_options.md)
- **Equivalent martingale measure result** $f_0 = g_0 E_g[f_T/g_T]$ → [ch28](chapters/ch28_martingales_measures.md)
- **Risk-neutral pricing** $f_0 = \hat{E}[e^{-\bar{r}T}f_T]$ → [ch28](chapters/ch28_martingales_measures.md)
- **$T$-forward measure pricing** $f_0 = P(0,T)E_T[f_T]$ → [ch28](chapters/ch28_martingales_measures.md)
- **Forward price = $T$-measure expectation** $F(t,T) = E_T[S_T]$ → [ch28](chapters/ch28_martingales_measures.md)

## Numerical Methods

- **Monte Carlo (log-normal)** $S_T = S_0\exp[(\mu-\sigma^2/2)T + \sigma\epsilon\sqrt{T}]$ → [ch21](chapters/ch21_basic_numerical.md)
- **Finite difference (explicit ≡ trinomial tree)** explicit FD = trinomial with specific parameters → [ch21](chapters/ch21_basic_numerical.md)
- **CEV SDE** $dS = (r-q)S\,dt + \sigma S^\beta dz$ → [ch27](chapters/ch27_more_models_numerical.md)
- **Merton jump-diffusion SDE** $dS/S = (r-q-\lambda k)\,dt + \sigma\,dz + dp$ → [ch27](chapters/ch27_more_models_numerical.md)
- **Merton jump series** $c = \sum_{n=0}^\infty e^{-\lambda' T}(\lambda' T)^n/n! \cdot c_\text{BSM}(r_n, \sigma_n)$ → [ch27](chapters/ch27_more_models_numerical.md)
- **Hull-White stochastic vol SDE** $dV = a(V_L - V)\,dt + \xi V^\alpha dz_V$ → [ch27](chapters/ch27_more_models_numerical.md)
- **LMM drift (rolling risk-neutral)** $dF_k/F_k = \sum_{i=m}^{k} \delta_i F_i \zeta_i \zeta_k/(1+\delta_i F_i)\,dt + \zeta_k dz$ → [ch33](chapters/ch33_forward_rate_models.md)

## Volatility Models / Smile

- **Breeden-Litzenberger (risk-neutral density)** $g(K) = e^{rT}\partial^2 c/\partial K^2$ → [ch20](chapters/ch20_vol_smile.md)
- **Risk-reversal (25Δ)** $\text{RR}_{25} = \sigma_{25\Delta C} - \sigma_{25\Delta P}$ → [ch20](chapters/ch20_vol_smile.md)
- **Butterfly spread (25Δ)** $\text{BF}_{25} = \tfrac{1}{2}(\sigma_{25\Delta C} + \sigma_{25\Delta P}) - \sigma_\text{ATM}$ → [ch20](chapters/ch20_vol_smile.md)
- **Put-call parity (BS pricing error parity)** $p_\text{BS} - p_\text{mkt} = c_\text{BS} - c_\text{mkt}$ → [ch20](chapters/ch20_vol_smile.md)
- **Volatility surface** $\sigma = \sigma(K, T)$ (2-D function) → [ch20](chapters/ch20_vol_smile.md)
- **EWMA vol update** $\sigma_n^2 = \lambda\sigma_{n-1}^2 + (1-\lambda)u_{n-1}^2$ → [ch23](chapters/ch23_vol_corr_estimation.md)
- **GARCH(1,1)** $\sigma_n^2 = \omega + \alpha u_{n-1}^2 + \beta\sigma_{n-1}^2$ → [ch23](chapters/ch23_vol_corr_estimation.md)
- **GARCH long-run variance** $V_L = \omega/(1-\alpha-\beta)$ → [ch23](chapters/ch23_vol_corr_estimation.md)
- **GARCH variance forecast** $E[\sigma_{n+t}^2] = V_L + (\alpha+\beta)^t(\sigma_n^2 - V_L)$ → [ch23](chapters/ch23_vol_corr_estimation.md)
- **GARCH MLE objective** $\max\sum[-\ln\sigma_i^2 - u_i^2/\sigma_i^2]$ → [ch23](chapters/ch23_vol_corr_estimation.md)
- **Covariance EWMA update** $\text{cov}_n = \lambda\,\text{cov}_{n-1} + (1-\lambda)x_{n-1}y_{n-1}$ → [ch23](chapters/ch23_vol_corr_estimation.md)
- **Cholesky simulation** $X = LZ$; $\Sigma = LL^\top$ → [ch23](chapters/ch23_vol_corr_estimation.md)
- **Vol term structure (GARCH)** $\sigma(T)^2 \propto V_L + (1-e^{-aT})/(aT)\,[V(0)-V_L]$ → [ch23](chapters/ch23_vol_corr_estimation.md)

## Risk Management (VaR, ES, Vol Estimation)

- **VaR definition** $\Pr(L > \text{VaR}_\alpha) = 1 - \alpha$ → [ch22](chapters/ch22_var_es.md)
- **ES definition** $\text{ES}_\alpha = E[L \mid L > \text{VaR}_\alpha]$ → [ch22](chapters/ch22_var_es.md)
- **$\sqrt{N}$ scaling (iid normal)** $\text{VaR}_{N\text{-day}} = \sqrt{N}\cdot\text{VaR}_{1\text{-day}}$ → [ch22](chapters/ch22_var_es.md)
- **Model-building VaR (normal portfolio)** $\text{VaR} = z_\alpha \sigma_P$; $\sigma_P = \sqrt{\alpha^\top C\alpha}$ → [ch22](chapters/ch22_var_es.md)
- **ES (normal distribution)** $\text{ES}_\alpha = \sigma_P\phi(z_\alpha)/(1-\alpha)$ → [ch22](chapters/ch22_var_es.md)
- **Delta-gamma approximation** $\Delta P \approx \delta\Delta S + \tfrac{1}{2}\gamma(\Delta S)^2$ → [ch22](chapters/ch22_var_es.md)
- **Sample variance (zero-mean)** $\sigma_n^2 = (1/m)\sum u_{n-i}^2$ → [ch23](chapters/ch23_vol_corr_estimation.md)

## Credit Risk & Derivatives

- **Hazard rate / survival probability** $S(t) = e^{-\int_0^t\lambda(\tau)\,d\tau}$ → [ch24](chapters/ch24_credit_risk.md)
- **Cumulative default probability** $Q(T) = 1 - e^{-\lambda T}$ (constant $\lambda$) → [ch24](chapters/ch24_credit_risk.md)
- **Hazard rate from spread** $\bar\lambda \approx s(T)/(1-R)$ → [ch24](chapters/ch24_credit_risk.md)
- **Merton equity value** $E_0 = V_0 N(d_1) - De^{-rT}N(d_2)$ → [ch24](chapters/ch24_credit_risk.md)
- **Merton risk-neutral default prob** $Q = N(-d_2)$ → [ch24](chapters/ch24_credit_risk.md)
- **Equity-asset vol link (Merton)** $\sigma_E E_0 = N(d_1)\sigma_V V_0$ → [ch24](chapters/ch24_credit_risk.md)
- **KMV distance to default** $\text{DD} = d_2$ → [ch24](chapters/ch24_credit_risk.md)
- **Gaussian copula (1-factor)** $x_i = a_i F + \sqrt{1-a_i^2}Z_i$ → [ch24](chapters/ch24_credit_risk.md), [ch25](chapters/ch25_credit_derivatives.md)
- **Credit VaR (Vasicek)** $V(X,T) = N[(N^{-1}[Q(T)] + \sqrt\rho\,N^{-1}(X))/\sqrt{1-\rho}]$ → [ch24](chapters/ch24_credit_risk.md)
- **CVA** $\text{CVA} = \sum q_i v_i$ → [ch09](chapters/ch09_xvas.md), [ch24](chapters/ch24_credit_risk.md)
- **DVA** $\text{DVA} = \sum q_i^* v_i^*$ → [ch09](chapters/ch09_xvas.md)
- **Portfolio value (CVA-DVA adjusted)** $f_\text{adj} = f_\text{nd} - \text{CVA} + \text{DVA}$ → [ch09](chapters/ch09_xvas.md)
- **FVA** $\text{FVA} = \text{FCA} - \text{FBA}$ → [ch09](chapters/ch09_xvas.md)
- **CDS par spread** $s = \text{PV(protection leg)}/\text{PV(risky annuity)}$ → [ch25](chapters/ch25_credit_derivatives.md)
- **CDS approx spread** $s \approx \lambda(1-R)$ → [ch25](chapters/ch25_credit_derivatives.md)
- **Fixed-coupon CDS price** $P = 100 - 100D(s-c)$ → [ch25](chapters/ch25_credit_derivatives.md)
- **ABS mezzanine tranche loss** $L_\text{mezz} = \max(L-0.05, 0)/0.15$ → [ch08](chapters/ch08_securitization.md)
- **ABS CDO senior tranche loss** $L_\text{senior} = \max(L_\text{mezz}-0.35, 0)/0.65$ → [ch08](chapters/ch08_securitization.md)

## Exotic Options

- **Gap call** $c_\text{gap} = S_0 e^{-qT}N(d_1) - K_1 e^{-rT}N(d_2)$ ($d_1$, $d_2$ use trigger $K_2$) → [ch26](chapters/ch26_exotics.md)
- **Forward start option (ATM)** $V_0 = c\,e^{-qT_1}$ → [ch26](chapters/ch26_exotics.md)
- **Compound option (call on call, Geske)** $V_{cc} = S_0 e^{-qT_2}M(a_1,b_1;\sqrt{T_1/T_2}) - K_2 e^{-rT_2}M(a_2,b_2;\sqrt{T_1/T_2}) - K_1 e^{-rT_1}N(a_2)$ → [ch26](chapters/ch26_exotics.md)
- **Chooser option** $V_\text{ch} = c(K,T_2) + e^{-q(T_2-T_1)}p(Ke^{-(r-q)(T_2-T_1)}, T_1)$ → [ch26](chapters/ch26_exotics.md)
- **Barrier (down-and-in call, $H \le K$)** $c_\text{di} = S_0 e^{-qT}(H/S_0)^{2\lambda}N(y) - Ke^{-rT}(H/S_0)^{2\lambda-2}N(y-\sigma\sqrt{T})$ → [ch26](chapters/ch26_exotics.md)
- **Cash-or-nothing call** $c_\text{con} = Qe^{-rT}N(d_2)$ → [ch26](chapters/ch26_exotics.md)
- **Asset-or-nothing call** $c_\text{aon} = S_0 e^{-qT}N(d_1)$ → [ch26](chapters/ch26_exotics.md)
- **Floating lookback call (closed form)** involves $N(a_1)$, $N(a_2)$, $N(a_3)$, $S_\text{min}$ → [ch26](chapters/ch26_exotics.md)

## Interest-Rate Derivatives & Models

- **Bond option (Black's model)** $c = P(0,T)[F_B N(d_1) - KN(d_2)]$ → [ch29](chapters/ch29_ir_std_models.md)
- **Yield-price vol conversion** $\sigma_B \approx D y_0 \sigma_y$ → [ch29](chapters/ch29_ir_std_models.md)
- **Caplet (Black's model)** caplet $= L\delta_k P(0,t_{k+1})[F_k N(d_1) - R_K N(d_2)]$ → [ch29](chapters/ch29_ir_std_models.md)
- **Cap-floor parity** cap $-$ floor $=$ IRS (pay fixed $R_K$) → [ch29](chapters/ch29_ir_std_models.md)
- **Swaption payer (Black's model)** $V_\text{pay} = LA(0)[s_F N(d_1) - s_K N(d_2)]$ → [ch29](chapters/ch29_ir_std_models.md)
- **HJM drift constraint (1-factor)** $m(t,T) = s(t,T)\int_t^T s(t,\tau)\,d\tau$ → [ch33](chapters/ch33_forward_rate_models.md)
- **HJM forward rate SDE** $dF(t,T) = v v_T\,dt - v_T\,dz$ → [ch33](chapters/ch33_forward_rate_models.md)
- **LMM forward rate SDE (T-measure)** $dF_k = \zeta_k F_k\,dz$ → [ch33](chapters/ch33_forward_rate_models.md)
- **LMM caplet vol calibration** $\sigma_k^2 t_k = \sum_i \Lambda_{k-i}^2\,\delta_{i-1}$ → [ch33](chapters/ch33_forward_rate_models.md)

## Equilibrium & No-Arb Short-Rate Models

- **Rendleman-Bartter** $dr = \mu r\,dt + \sigma r\,dz$ → [ch31](chapters/ch31_equilibrium_short_rate.md)
- **Vasicek SDE** $dr = a(b-r)\,dt + \sigma\,dz$ → [ch31](chapters/ch31_equilibrium_short_rate.md)
- **Vasicek bond price** $P(t,T) = A(t,T)e^{-B(t,T)r(t)}$; $B = (1-e^{-a(T-t)})/a$ → [ch31](chapters/ch31_equilibrium_short_rate.md)
- **CIR SDE** $dr = a(b-r)\,dt + \sigma\sqrt{r}\,dz$ → [ch31](chapters/ch31_equilibrium_short_rate.md)
- **CIR bond price** $P = A e^{-Br}$; $B = 2(e^{\gamma\tau}-1)/((\gamma+a)(e^{\gamma\tau}-1)+2\gamma)$; $\gamma=\sqrt{a^2+2\sigma^2}$ → [ch31](chapters/ch31_equilibrium_short_rate.md)
- **IR derivatives PDE** $\partial f/\partial t + m\partial f/\partial r + \tfrac{1}{2}s^2\partial^2 f/\partial r^2 = rf$ → [ch31](chapters/ch31_equilibrium_short_rate.md)
- **Ho-Lee SDE** $dr = \theta(t)\,dt + \sigma\,dz$; $\theta(t) = F_t(0,t) + \sigma^2 t$ → [ch32](chapters/ch32_noarb_short_rate.md)
- **Hull-White SDE** $dr = [\theta(t) - ar]\,dt + \sigma\,dz$ → [ch32](chapters/ch32_noarb_short_rate.md)
- **Hull-White bond price** $P(t,T) = A(t,T)e^{-B(t,T)r(t)}$; $B = (1-e^{-a(T-t)})/a$ → [ch32](chapters/ch32_noarb_short_rate.md)
- **Black-Karasinski SDE** $d\ln r = [\theta(t) - a\ln r]\,dt + \sigma\,dz$ → [ch32](chapters/ch32_noarb_short_rate.md)
- **European option on zero-coupon bond (HW)** call $= LP(0,s)N(h) - KP(0,T)N(h-\sigma_P)$ → [ch32](chapters/ch32_noarb_short_rate.md)
- **HW forward rate vol structure** $\sigma_f(t,T) = \sigma e^{-a(T-t)}$ → [ch32](chapters/ch32_noarb_short_rate.md)
- **HW trinomial probabilities** $p_u = \tfrac{1}{6}+\tfrac{1}{2}(a^2j^2\Delta t^2 - aj\Delta t)$; $p_m = \tfrac{2}{3} - a^2j^2\Delta t^2$ → [ch32](chapters/ch32_noarb_short_rate.md)

## Convexity / Timing / Quanto Adjustments

- **Convexity adjustment (forward bond yield)** $E_T(y_T) = y_F - \tfrac{1}{2}y_F^2\sigma_y^2 T\,G''(y_F)/G'(y_F)$ → [ch30](chapters/ch30_convexity_timing_quanto.md)
- **Timing adjustment (measure change $T \to T^*$)** $E_{T^*}(V_T) = E_T(V_T)\exp[-\rho_{VR}\sigma_V\sigma_R R_F(T^*-T)/(1+R_F/m)\cdot T]$ → [ch30](chapters/ch30_convexity_timing_quanto.md)
- **Quanto adjustment (forward measure)** $E_X(V_T) = E_Y(V_T)e^{\rho_{VW}\sigma_V\sigma_W T}$ → [ch30](chapters/ch30_convexity_timing_quanto.md)
- **Quanto drift correction (risk-neutral)** $\Delta\mu_V = \rho\sigma_V\sigma_S$ → [ch30](chapters/ch30_convexity_timing_quanto.md)
- **Annuity numeraire (swap measure)** $A(t) = \sum_{i=0}^{N-1}(T_{i+1}-T_i)P(t,T_{i+1})$ → [ch28](chapters/ch28_martingales_measures.md)

## Commodity / Energy

- **Cost-of-carry (commodity)** $F_0 = S_0 e^{(r+u-y)T}$ → [ch35](chapters/ch35_commodity_energy.md)
- **Electricity forward (non-storable)** $F_T = \hat{E}[S_T]$ → [ch35](chapters/ch35_commodity_energy.md)
- **Mean-reverting log-price SDE (Schwartz 1-factor)** $d\ln S = [\theta(t) - a\ln S]\,dt + \sigma\,dz$ → [ch35](chapters/ch35_commodity_energy.md), [ch36](chapters/ch36_real_options.md)
- **Jump process (energy prices)** $d\ln S = [\theta(t) - a\ln S]\,dt + \sigma\,dz + dp$ → [ch35](chapters/ch35_commodity_energy.md)
- **Gibson-Schwartz 2-factor** $dS/S = (r-y)\,dt + \sigma_1 dz_1$; $dy = k(\alpha-y)\,dt + \sigma_2 dz_2$ → [ch35](chapters/ch35_commodity_energy.md)

## Real Options

- **Static NPV** $\text{NPV} = \sum CF_t/(1+r_\text{adj})^t$ → [ch36](chapters/ch36_real_options.md)
- **CAPM market price of risk** $\lambda = \rho(\mu_m - r)/\sigma_m$ → [ch36](chapters/ch36_real_options.md)
- **Risk-neutral drift correction** $d\theta/\theta = (m - \lambda s)\,dt + s\,dz$ → [ch36](chapters/ch36_real_options.md)
- **Bellman equation (real option DP)** $V_t = \max(\text{exercise now},\;e^{-r\Delta t}E[V_{t+1}])$ → [ch36](chapters/ch36_real_options.md)

## Mishaps / Governance

- (none; conceptual chapter — Ch. 37 contains case studies and governance principles, no quantitative formulas)
