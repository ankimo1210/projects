<!--
Provenance: external AI (ChatGPT) discussion shared by the user on 2026-07-12,
saved verbatim. This is a research/handoff note, not a validated result of this
lab. Bibliographic metadata and quantitative claims must be verified against the
original papers before any formal use. A short Japanese Q&A distilled from this
document is embedded in the standalone report (report-only section
"practical-qanda", Japanese edition).
-->

# Handoff: Rough Volatility — Hedging, Greeks, and Practical Adoption

## Purpose

This handoff is designed to start a new chat focused specifically on the practical implications of rough volatility for:

- hedging,
- Greeks,
- trader explainability,
- model risk,
- production architecture,
- calibration and risk infrastructure,
- and whether rough-volatility models are genuinely useful in a trading environment.

The discussion below preserves the logical flow of the prior conversation and expands the mathematics where useful.

---

# 1. Conversation context

The discussion began with a broad review of current hot topics in financial engineering, followed by deeper exploration of:

1. Deep Hedging / Neural Pricing
2. Rough Volatility / Volatility Microstructure
3. Market Microstructure / Optimal Execution

A synthetic visual-lab project for rough volatility was then designed and implemented. Its Japanese HTML report was reviewed.

The conversation then shifted from model construction to a more important practical question:

> If rough volatility makes the volatility state path-dependent and effectively infinite-dimensional, how can a trader hedge, explain, and manage the resulting Greeks?

This became the central topic.

---

# 2. Main discussion in dialogue form

## Topic A — What is roughness, and how is it related to \(H\)?

### User concern

What exactly is roughness? How is it related to the Hurst exponent \(H\)?

### Discussion

Roughness is a local regularity property of a stochastic path.

For a process \(X_t\), suppose short-time increments scale as

\[
\mathbb E\left[|X_{t+\Delta}-X_t|^q\right]
\propto
\Delta^{qH}.
\]

For \(q=2\),

\[
\mathbb E\left[
(X_{t+\Delta}-X_t)^2
\right]
\propto
\Delta^{2H},
\]

and therefore

\[
\operatorname{Std}
\left(
X_{t+\Delta}-X_t
\right)
\propto
\Delta^H.
\]

The smaller \(H\) is, the more slowly short-time increments shrink as the observation interval becomes finer.

For example, if the time interval is reduced by a factor of 100,

\[
\frac{
\operatorname{Std}(\Delta X_{\text{new}})
}{
\operatorname{Std}(\Delta X_{\text{old}})
}
=
100^{-H}.
\]

Hence,

\[
H=0.5
\quad\Rightarrow\quad
100^{-0.5}=0.1,
\]

while

\[
H=0.1
\quad\Rightarrow\quad
100^{-0.1}\approx 0.63.
\]

Thus, for \(H=0.1\), substantial variation remains even at much finer time scales.

This is what “rough” means.

### Hölder regularity

A path is locally \(\alpha\)-Hölder continuous if

\[
|X_t-X_s|
\le
C|t-s|^\alpha
\]

locally.

Fractional Brownian motion \(B_t^H\) is almost surely \(\alpha\)-Hölder continuous for every

\[
\alpha < H,
\]

but generally not for

\[
\alpha \ge H.
\]

Therefore, smaller \(H\) means lower path regularity and greater roughness.

### Key distinction

\[
\boxed{
\text{roughness}
\neq
\text{volatility amplitude}
}
\]

A process may have large variance but be relatively smooth, or small variance but be mathematically rough.

---

## Topic B — Does changing \(H\) mean changing Brownian motion itself?

### User concern

Many classical volatility models use Brownian motion as the basis of the volatility driver.

Does changing \(H\) mean replacing Brownian motion itself?

If so, connecting rough volatility to existing models seems difficult.

### Discussion

The important distinction is:

> In most practical rough-volatility models, the primitive noise remains standard Brownian motion. What changes is how Brownian shocks are transmitted into volatility through time.

A rough Gaussian process is typically constructed as a Volterra transform of Brownian motion:

\[
W_t^H
=
\int_0^t
K_H(t-s)\,dW_s,
\]

with a kernel of the form

\[
K_H(u)
\propto
u^{H-\frac12}.
\]

When

\[
H<\frac12,
\]

the exponent satisfies

\[
H-\frac12<0,
\]

and the kernel becomes singular near \(u=0\).

This gives very high weight to recent shocks and creates a locally rough process.

The structure is therefore:

```text
standard Brownian shocks
        ↓
singular Volterra kernel
        ↓
rough volatility factor
```

The Brownian motion itself still has

\[
H=\frac12.
\]

It is not “retuned” to \(H=0.1\). Instead, it is filtered through a memory kernel.

> **Notation correction:** the kernel should be read as \(K_H(u)\propto u^{H-1/2}\). The symbol \(u\) denotes lag.

---

## Topic C — Is the spot-price Brownian motion also replaced?

### Discussion

Usually, no.

In rough Bergomi, for example,

\[
\frac{dS_t}{S_t}
=
\sqrt{V_t}\,dB_t,
\]

where \(B_t\) remains standard Brownian motion.

The variance process is rough:

\[
V_t
=
\xi_0(t)
\exp
\left(
\eta W_t^H
-
\frac12\eta^2 t^{2H}
\right).
\]

The rough driver is

\[
W_t^H
=
\sqrt{2H}
\int_0^t
(t-s)^{H-\frac12}\,dW_s.
\]

The price and volatility shocks are correlated through

\[
d\langle B,W\rangle_t
=
\rho\,dt.
\]

Thus:

```text
primitive Brownian noise
     ├──→ spot Brownian driver B → spot
     └──→ Brownian driver W → Volterra transform → rough variance
```

This is crucial.

The spot process remains a semimartingale and standard no-arbitrage machinery remains much more manageable than if spot itself were directly driven by fractional Brownian motion.

---

# 3. Classical Heston versus rough Heston

## Classical Heston

\[
dS_t
=
S_t\sqrt{V_t}\,dB_t,
\]

\[
dV_t
=
\kappa(\theta-V_t)\,dt
+
\nu\sqrt{V_t}\,dW_t.
\]

The state is finite-dimensional:

\[
(S_t,V_t).
\]

Conditional on the current state, the future does not depend on the entire past.

Hence the model is Markovian.

---

## Rough Heston

A representative Volterra form is

\[
V_t
=
V_0
+
\int_0^t
K_H(t-s)\kappa(\theta-V_s)\,ds
+
\int_0^t
K_H(t-s)\nu\sqrt{V_s}\,dW_s.
\]

Now the current value \(V_t\) alone is not enough to summarize the future.

The model depends on the historical path

\[
\{V_s:0\le s\le t\}.
\]

Equivalently, it can often be represented through a forward-variance state.

### Structural difference

| Classical Heston | Rough Heston |
|---|---|
| Finite-dimensional SDE | Stochastic Volterra equation |
| Markovian | Non-Markovian |
| Current state is enough | History or forward curve is needed |
| Riccati ODE | Fractional Riccati equation |
| Low-dimensional PDE possible | Standard low-dimensional PDE unavailable |
| Standard state Greeks | Functional / curve Greeks |

---

# 4. Why this makes hedging harder

## User concern

If Greeks depend on the past path, hedging and trader explanation become difficult.

### Discussion

That concern is correct.

The main difficulty is that the natural state is no longer a scalar variance \(V_t\), but a whole curve or historical object.

For a rough-volatility derivative, the price can be written schematically as

\[
C_t
=
C
\left(
S_t,
\{\xi_t(u)\}_{u\ge t}
\right),
\]

where

\[
\xi_t(u)
=
\mathbb E_t[V_u]
\]

is the forward variance curve.

The state variable is therefore not just one volatility number.

It is a function of future maturity \(u\).

---

# 5. Functional Greeks

In a classical one-factor model, one may define a scalar volatility Greek such as

\[
\frac{\partial C}{\partial V_t}.
\]

In a rough model, the natural risk object is instead a functional derivative:

\[
\frac{\delta C_t}
{\delta \xi_t(u)}.
\]

This means:

> How much does the derivative value change if forward variance at future horizon \(u\) changes?

The first-order change is formally

\[
\Delta C_t
\approx
\Delta_t\,\Delta S_t
+
\int_t^\infty
\frac{\delta C_t}
{\delta \xi_t(u)}
\Delta \xi_t(u)\,du.
\]

This is mathematically natural, but not trader-friendly.

A trader does not want to explain:

> “The book has a large functional derivative at forward variance horizon \(u=0.137\).”

The risk must therefore be mapped into familiar market buckets.

---

# 6. Practical risk compression

The path dependence is not usually shown directly to the trader.

Instead:

```text
entire past path
      ↓
forward variance curve
      ↓
finite maturity buckets
      ↓
standard trader risk
```

Suppose expiry buckets are

\[
[T_0,T_1],\,
[T_1,T_2],\,
\ldots,\,
[T_{n-1},T_n].
\]

Define bucketed forward-variance risk by

\[
\text{FVega}_i
=
\int_{T_i}^{T_{i+1}}
\frac{\delta C_t}
{\delta \xi_t(u)}
\,du.
\]

Alternatively, perturb the market implied-volatility surface directly and reprice.

For example:

\[
\Delta C
\approx
\Delta\cdot\Delta S
+
\sum_i
\text{Vega}_i\,\Delta\sigma_i
+
\text{Vanna}\,\Delta S\,\Delta\sigma
+
\frac12\text{Volga}\,(\Delta\sigma)^2.
\]

The production risk report may therefore show:

- spot Delta,
- expiry-bucketed Vega,
- skew exposure,
- convexity / Volga,
- Vanna,
- correlation exposure,
- fast/slow volatility-factor risk,
- model-parameter scenarios.

The infinite-dimensional state remains behind the scenes.

---

# 7. What happens to \(H\)-risk?

One can formally define

\[
\frac{\partial C}{\partial H}.
\]

However, \(H\) is not directly tradable.

There is no liquid instrument whose payoff is a clean exposure to the Hurst exponent.

Therefore, \(H\)-risk is better treated as:

- model-parameter risk,
- recalibration risk,
- short-end skew stress,
- model reserve,
- benchmark-model difference,
- or P&L under alternative model specifications.

For example:

\[
\Delta_H C
=
C(H+\Delta H)-C(H).
\]

A risk report might include scenarios such as

\[
H=0.07,\quad 0.10,\quad 0.15.
\]

But the actual hedge would use observable market instruments whose prices reflect the consequences of \(H\):

- short-dated vanilla options,
- skew packages,
- variance swaps,
- VIX products,
- calendar spreads,
- or other forward-variance instruments.

Thus:

\[
\boxed{
\text{H itself is not hedged directly.}
}
\]

Instead:

\[
\boxed{
\text{the market manifestations of H are hedged.}
}
\]

---

# 8. Why forward variance is the key state variable

Although rough volatility is path-dependent, the past need not be displayed literally.

The relevant information can often be summarized by the forward variance curve

\[
u\mapsto \xi_t(u).
\]

This is analogous to interest-rate modeling.

In an HJM framework, the state may be an entire forward-rate curve

\[
T\mapsto f(t,T),
\]

yet traders still manage the book using:

- tenor DV01,
- key-rate duration,
- curve factors,
- level/slope/curvature,
- and market instruments.

Rough volatility is conceptually similar:

| Interest-rate HJM | Rough volatility |
|---|---|
| Forward-rate curve | Forward-variance curve |
| Key-rate DV01 | Expiry-bucketed forward Vega |
| Curve factors | Fast/medium/slow volatility factors |
| Yield-curve shocks | Volatility-surface shocks |
| Curve model parameters | \(H,\eta,\rho\) and kernel parameters |

This analogy is important for practical adoption.

Infinite-dimensional state does not necessarily imply an infinite-dimensional trader interface.

---

# 9. Trader explainability

## User concern

Greeks that depend on the past path seem hard to explain to a trader or management.

### Discussion

A reasonable practical explanation would avoid pathwise language.

Instead of saying:

> “The option depends on all historical volatility shocks.”

one would say:

> “The model’s memory is summarized through the current forward-variance curve. The book is mainly exposed to 1M and 3M variance, short-dated skew, and spot-vol correlation.”

A trader-facing explanation could be:

```text
P&L driver
├─ spot Delta
├─ 1M forward-variance exposure
├─ 3M forward-variance exposure
├─ short-end skew exposure
├─ spot-vol correlation / Vanna
├─ convexity / Volga
└─ residual model recalibration
```

This is far more useful than reporting raw Volterra-kernel sensitivity.

---

# 10. Is rough volatility used directly as the daily hedging model?

## Practical conclusion

Usually, the most realistic architecture is not:

```text
exact rough model
        ↓
all trader Greeks
        ↓
daily hedge
```

A more plausible production architecture is:

```text
Exact rough benchmark model
        ↓
Markovian approximation / production proxy
        ↓
standard risk buckets and market shocks
        ↓
trader hedge
```

The exact rough model may be used for:

- benchmark pricing,
- smile-generation research,
- short-end skew structure,
- model validation,
- stress scenarios,
- reserve calculations,
- and comparison against classical models.

The daily risk engine may use a finite-dimensional approximation.

---

# 11. Markovian lift

The most important practical approximation is to replace the fractional kernel with a sum of exponentials:

\[
K_H(t)
\approx
\sum_{j=1}^{M}
w_j e^{-x_j t}.
\]

For each exponential component, define a Markov factor

\[
dY_t^{(j)}
=
-x_jY_t^{(j)}\,dt
+
dW_t.
\]

Then

\[
W_t^H
\approx
\sum_{j=1}^{M}
w_jY_t^{(j)}.
\]

The originally infinite-dimensional process becomes approximately finite-dimensional:

\[
(Y_t^{(1)},\ldots,Y_t^{(M)}).
\]

The factors may be interpreted as:

- very fast volatility factor,
- fast factor,
- medium factor,
- slow factor,
- very slow factor.

This makes both computation and explanation easier.

### Production advantages

- finite-dimensional state,
- easier Monte Carlo,
- possible PDE methods,
- easier scenario generation,
- interpretable factor Greeks,
- easier integration into existing infrastructure.

### Approximation cost

The model is no longer exact.

The key control variables become:

- number of factors \(M\),
- kernel approximation error,
- maturity range,
- stability under recalibration,
- and whether the approximation preserves short-end skew behavior.

---

# 12. Model hierarchy for practical use

A robust model stack could be:

## Layer 1 — Exact benchmark

Use:

- rough Bergomi,
- rough Heston,
- or another exact Volterra model.

Purpose:

- theoretical benchmark,
- research,
- model validation,
- pricing reference,
- stress generation.

## Layer 2 — Production approximation

Use:

- lifted Heston,
- multifactor exponential-kernel approximation,
- or another Markovian proxy.

Purpose:

- daily calibration,
- scenarios,
- Greeks,
- portfolio repricing,
- XVA / PFE integration.

## Layer 3 — Trader risk representation

Report:

- Delta,
- expiry-bucketed Vega,
- skew,
- Vanna,
- Volga,
- correlation,
- fast/slow vol factors,
- and model-risk scenarios.

The flow is:

```text
exact rough model
        ↓
finite-dimensional production proxy
        ↓
market-observable risk buckets
```

---

# 13. Why rough models may still improve hedging

The goal is not to produce elegant Greeks.

The goal is to generate more realistic volatility-surface dynamics.

A classical model may fit today’s surface, yet imply the wrong dynamics for tomorrow’s surface.

Hedging depends on dynamics, not only static fit.

A rough model may improve:

- short-dated skew behavior,
- forward-skew evolution,
- spot-volatility feedback,
- Vanna behavior,
- variance term-structure dynamics,
- and the interaction of short and long volatility factors.

Even if the displayed risk is conventional, a better underlying model may generate more accurate hedge ratios.

The practical test is therefore not:

> Is the model mathematically rough?

It is:

> Does the model reduce out-of-sample hedging error after transaction costs and recalibration?

---

# 14. Main limitations to practical adoption

## 14.1 Non-Markovian computation

Direct Volterra simulation is expensive.

A naive discretization has complexity approximately

\[
O(N^2)
\]

per path because every new time step depends on all previous shocks:

\[
W_{t_i}^H
\approx
\sum_{j<i}
K_H(t_i-t_j)\Delta W_j.
\]

This is problematic for:

- large books,
- real-time Greeks,
- XVA,
- PFE,
- stress grids,
- and intraday recalibration.

---

## 14.2 Functional risk

The natural risk object is a curve sensitivity, not one scalar Vega.

This increases:

- reporting complexity,
- hedge mapping complexity,
- basis risk,
- and model-risk governance burden.

---

## 14.3 Calibration instability

Parameters such as

\[
H,\eta,\rho,\xi_0
\]

may compensate for one another.

A stable surface fit does not necessarily imply stable parameter estimates.

If \(H\) jumps significantly day to day, its direct Greek is not economically useful.

---

## 14.4 Lack of directly tradable state variables

The forward variance curve is only imperfectly spanned by traded options.

Hedges therefore leave:

- strike basis,
- expiry basis,
- smile basis,
- interpolation risk,
- and model mismatch.

---

## 14.5 Explainability and governance

Model-validation teams may ask:

- Why is \(H\) fixed?
- Is the process truly rough or only apparently rough?
- How does measurement noise affect calibration?
- Why does the model outperform a multifactor Markov model?
- How sensitive are reserves to the kernel approximation?
- What happens outside the calibration domain?

These are legitimate concerns.

---

# 15. Current practical interpretation

A balanced practical view is:

1. Rough volatility is a powerful structural explanation for short-time volatility behavior and short-expiry skew.
2. It is not automatically the best production model for every asset class.
3. Exact rough models are especially useful as research and benchmark models.
4. Production systems usually need finite-dimensional approximations.
5. Trader-facing risk should remain expressed in familiar, market-observable buckets.
6. \(H\) is better treated as a model-risk parameter than as a directly hedgeable Greek.
7. The decisive metric is out-of-sample hedging performance, not theoretical elegance.

---

# 16. Application to rates and swaptions

For rates, practical adoption would likely be even more conservative.

An exact rough-volatility model could be used to study:

- short-expiry swaption skew,
- expiry dependence of SABR parameters,
- forward-volatility dynamics,
- smile dynamics around central-bank events,
- and whether one common roughness parameter explains multiple expiries.

However, the daily risk report would probably remain:

- curve DV01,
- expiry × tenor Vega,
- SABR alpha/beta/rho/nu risk,
- smile shocks,
- correlation risk,
- sticky-strike versus sticky-delta scenarios,
- and P&L explain by market quote movement.

A practical rates architecture might be:

```text
rough-volatility research benchmark
        ↓
multifactor Markov approximation
        ↓
expiry × tenor volatility buckets
        ↓
standard swaption hedges
```

The key unresolved question is whether rough dynamics improve actual swaption hedging enough to justify additional complexity.

---

# 17. Important analogy with interest-rate curve models

This analogy should be developed further in the new chat.

In HJM, the state is an entire curve:

\[
T\mapsto f(t,T).
\]

Yet traders do not report an infinite-dimensional Greek.

They report:

\[
\text{DV01}_{2Y},
\text{DV01}_{5Y},
\text{DV01}_{10Y},
\ldots
\]

and factor shocks.

Likewise, rough volatility can be treated as:

\[
u\mapsto \xi_t(u),
\]

with bucketed risk:

\[
\text{FVega}_{1M},
\text{FVega}_{3M},
\text{FVega}_{6M},
\ldots
\]

This suggests that the real obstacle is not infinite dimensionality itself.

The real obstacles are:

- observability,
- hedge spanning,
- calibration stability,
- computational cost,
- and governance.

---

# 18. Key open questions for the next chat

The new conversation should focus on the following.

## A. How is the forward variance curve observed?

- Is it extracted from variance swaps?
- From the implied-volatility surface?
- Through model-dependent inversion?
- How stable is it intraday?

## B. How are functional Greeks mapped to traded options?

- Least-squares projection?
- Minimum-variance hedge?
- PCA basis?
- Expiry buckets?
- Static replication?

## C. How many Markovian factors are practically required?

- 3 factors?
- 5 factors?
- 10–20 factors?
- How does the answer depend on maturity range?

## D. What is the correct P&L attribution?

Can the daily change be decomposed as

\[
\Delta V
\approx
\Delta V_{\text{spot}}
+
\Delta V_{\text{forward variance}}
+
\Delta V_{\text{skew}}
+
\Delta V_{\text{recalibration}}
+
\Delta V_{\text{residual}}?
\]

How should each term be defined?

## E. Is \(H\) stable enough to calibrate daily?

- Should \(H\) be fixed?
- Should it be common across expiries?
- Should it be estimated from time series or options?
- Should it be treated as structural rather than recalibrated?

## F. Does rough volatility outperform simpler models in hedging?

Comparisons should include:

- Heston,
- Bergomi,
- lifted Heston,
- multifactor Markov models,
- path-dependent volatility,
- local stochastic volatility,
- rough Bergomi / rough Heston.

Metrics should include:

- mean hedge P&L,
- RMSE,
- tail loss,
- turnover,
- transaction costs,
- recalibration stability,
- and explainability.

## G. How does the answer differ by asset class?

- SPX options,
- VIX products,
- FX options,
- commodities,
- rates / swaptions,
- credit options.

---

# 19. Proposed next analytical project

A useful follow-up project would be:

## Project name

`rough_volatility_hedging`

## Objective

Compare classical and rough-volatility models using identical synthetic or market-calibrated scenarios.

## Candidate models

1. Black–Scholes
2. Heston
3. Bergomi
4. Rough Bergomi
5. Lifted Heston
6. Multifactor Markov volatility
7. Optional path-dependent volatility model

## Required hedging outputs

- spot Delta,
- expiry-bucketed Vega,
- Vanna,
- Volga,
- correlation risk,
- forward-variance curve sensitivity,
- \(H\)-scenario risk,
- model-residual P&L.

## Required experiments

1. Static surface fit
2. Dynamic surface evolution
3. One-day hedge P&L
4. Multi-day hedge P&L
5. Transaction-cost-adjusted hedge
6. Recalibration risk
7. Model misspecification
8. Factor-count sensitivity for Markovian lifts
9. Trader-friendly P&L attribution
10. Rates extension using swaption volatility cubes

---

# 20. Suggested first prompt for the new chat

Use the following opening message:

> We previously discussed rough volatility and concluded that the main practical challenge is not pricing but hedging and explainability. Please analyze how a rough-volatility model should be converted into a trader-facing risk framework. Start from the forward variance curve as the state variable, derive functional Greeks, explain how they can be projected into expiry-bucketed Vega and tradable option hedges, compare exact rough models with Markovian lifts, and propose a production architecture for pricing, risk, P&L explain, model validation, and hedging. Please use equations and discuss the analogy with HJM/key-rate DV01 in rates.

---

# 21. Provisional conclusions from the prior discussion

The most important conclusions are:

\[
\boxed{
\text{Changing }H
\text{ does not usually replace primitive Brownian noise.}
}
\]

Instead,

\[
\boxed{
\text{Brownian shocks are transmitted through a singular Volterra kernel.}
}
\]

The spot driver usually remains Brownian, while the volatility state becomes rough and non-Markovian.

The natural state is not the literal historical path shown to the trader, but the forward variance curve:

\[
\boxed{
C_t=C\left(S_t,\xi_t(\cdot)\right).
}
\]

The natural Greek is a functional derivative:

\[
\boxed{
\frac{\delta C_t}{\delta \xi_t(u)}.
}
\]

In practice, this must be projected into finite, market-observable buckets:

\[
\boxed{
\text{functional Vega}
\rightarrow
\text{expiry-bucketed Vega / skew / Vanna / Volga}.
}
\]

The Hurst exponent \(H\) is not directly hedgeable:

\[
\boxed{
H\text{-risk}
\approx
\text{model risk / short-end skew stress / recalibration risk}.
}
\]

The likely production solution is:

```text
exact rough benchmark
        ↓
Markovian lift / multifactor proxy
        ↓
standard trader risk buckets
        ↓
market hedging instruments
```

Finally, the practical criterion is:

\[
\boxed{
\text{Does the model improve out-of-sample hedging after costs?}
}
\]

not:

\[
\boxed{
\text{Is the model mathematically elegant or statistically rough?}
}
\]

---

# 22. Literature names worth carrying into the new discussion

The following works are relevant starting points:

- Gatheral, Jaisson, Rosenbaum — *Volatility is Rough*
- Bayer, Friz, Gatheral — *Pricing under Rough Volatility*
- El Euch, Rosenbaum — rough Heston and fractional Riccati representation
- Abi Jaber, El Euch — multifactor approximation / Markovian lift
- Fukasawa, Horvath, Tankov — hedging under rough volatility and forward variance
- Guyon, Lekeufack — path-dependent volatility as an alternative explanation
- Cont, Das — roughness as possible measurement artefact
- Horvath, Muguruza, Tomas — neural pricing and calibration surrogates

For any formal report or publication, verify exact bibliographic metadata and claims against the original papers.

---

# 23. Final handoff note

The next chat should not restart from “What is rough volatility?”

It should begin from the following advanced premise:

> Rough volatility is mathematically non-Markovian, but practical risk management does not need to expose the full path. The central problem is how to compress the forward-variance state and functional Greeks into finite, tradable, explainable risk factors without losing the dynamic advantages of the rough model.

That is the main research question going forward.
