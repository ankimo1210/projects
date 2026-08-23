---
name: hull-derivatives
description: Reference and implementation guide for John Hull's "Options, Futures, and Other Derivatives" (11e). Use when implementing or reasoning about derivatives pricing (Black-Scholes, binomial trees, Greeks), volatility models (smile/surface, local vol, Heston, SABR), interest rate derivatives (HJM, Hull-White, LMM), swaps, futures/forwards, credit/XVA, VaR/ES, or when looking up a derivatives concept/formula/algorithm.
---

# Hull Derivatives Skill

Paraphrased summaries, formulas, algorithms, and short Python reference implementations from Hull "Options, Futures, and Other Derivatives" 11th edition. For personal local use.

## When to use
- Implementing a pricing or risk model (BSM, binomial, MC, Greeks, vol models, IR models)
- Looking up a definition, formula, or algorithm
- Sanity-checking an approach against a textbook standard

## How to read this skill
- For a **concept lookup** → start at `references/topics/<topic>.md`
- For **chapter-level detail** → `references/chapters/chXX_*.md`
- For a **specific formula** → `references/formulas_index.md`
- For a **term definition** → `references/glossary.md`

## Topic index
- **Futures & forwards** — [topics/futures_forwards.md](references/topics/futures_forwards.md) (ch2, 5, 6)
- **Hedging** — [topics/hedging.md](references/topics/hedging.md) (ch3)
- **Interest rates** — [topics/interest_rates.md](references/topics/interest_rates.md) (ch4, 6)
- **Swaps** — [topics/swaps.md](references/topics/swaps.md) (ch7, 34)
- **Options basics** — [topics/options_basics.md](references/topics/options_basics.md) (ch10, 11, 12, 17, 18)
- **Binomial trees** — [topics/binomial.md](references/topics/binomial.md) (ch13, 21)
- **Stochastic calculus** — [topics/stochastic_calculus.md](references/topics/stochastic_calculus.md) (ch14, 28)
- **Black-Scholes-Merton** — [topics/bsm.md](references/topics/bsm.md) (ch15)
- **Employee stock options** — [topics/employee_stock_options.md](references/topics/employee_stock_options.md) (ch16)
- **Greeks** — [topics/greeks.md](references/topics/greeks.md) (ch19)
- **Vol smile & surface** — [topics/vol_smile_surface.md](references/topics/vol_smile_surface.md) (ch20)
- **Numerical methods** — [topics/numerical_methods.md](references/topics/numerical_methods.md) (ch21, 27)
- **Risk management** — [topics/risk_management.md](references/topics/risk_management.md) (ch22, 23)
- **Credit** — [topics/credit.md](references/topics/credit.md) (ch8, 9, 24, 25)
- **Exotics** — [topics/exotics.md](references/topics/exotics.md) (ch26)
- **IR derivatives** — [topics/ir_derivatives.md](references/topics/ir_derivatives.md) (ch29, 30, 31, 32, 33)
- **Commodity & energy** — [topics/commodity_energy.md](references/topics/commodity_energy.md) (ch35)
- **Real options** — [topics/real_options.md](references/topics/real_options.md) (ch36)

## Chapter index
- Ch.1 [Introduction](references/chapters/ch01_introduction.md)
- Ch.2 [Futures Markets & CCPs](references/chapters/ch02_futures_markets.md)
- Ch.3 [Hedging Strategies Using Futures](references/chapters/ch03_hedging.md)
- Ch.4 [Interest Rates](references/chapters/ch04_interest_rates.md)
- Ch.5 [Forward and Futures Prices](references/chapters/ch05_forward_futures_pricing.md)
- Ch.6 [Interest Rate Futures](references/chapters/ch06_ir_futures.md)
- Ch.7 [Swaps](references/chapters/ch07_swaps.md)
- Ch.8 [Securitization & the Financial Crisis](references/chapters/ch08_securitization.md)
- Ch.9 [XVAs](references/chapters/ch09_xvas.md)
- Ch.10 [Mechanics of Options Markets](references/chapters/ch10_options_mechanics.md)
- Ch.11 [Properties of Stock Options](references/chapters/ch11_option_properties.md)
- Ch.12 [Trading Strategies Involving Options](references/chapters/ch12_option_strategies.md)
- Ch.13 [Binomial Trees](references/chapters/ch13_binomial_trees.md)
- Ch.14 [Wiener Processes and Itô's Lemma](references/chapters/ch14_wiener_ito.md)
- Ch.15 [Black-Scholes-Merton](references/chapters/ch15_bsm.md)
- Ch.16 [Employee Stock Options](references/chapters/ch16_employee_stock_options.md)
- Ch.17 [Options on Stock Indices and Currencies](references/chapters/ch17_index_currency_options.md)
- Ch.18 [Futures Options and Black's Model](references/chapters/ch18_futures_options_black.md)
- Ch.19 [The Greek Letters](references/chapters/ch19_greeks.md)
- Ch.20 [Volatility Smiles and Surfaces](references/chapters/ch20_vol_smile.md)
- Ch.21 [Basic Numerical Procedures](references/chapters/ch21_basic_numerical.md)
- Ch.22 [Value at Risk and Expected Shortfall](references/chapters/ch22_var_es.md)
- Ch.23 [Estimating Volatilities and Correlations](references/chapters/ch23_vol_corr_estimation.md)
- Ch.24 [Credit Risk](references/chapters/ch24_credit_risk.md)
- Ch.25 [Credit Derivatives](references/chapters/ch25_credit_derivatives.md)
- Ch.26 [Exotic Options](references/chapters/ch26_exotics.md)
- Ch.27 [More on Models and Numerical Procedures](references/chapters/ch27_more_models_numerical.md)
- Ch.28 [Martingales and Measures](references/chapters/ch28_martingales_measures.md)
- Ch.29 [IR Derivatives: Standard Market Models](references/chapters/ch29_ir_std_models.md)
- Ch.30 [Convexity, Timing, Quanto Adjustments](references/chapters/ch30_convexity_timing_quanto.md)
- Ch.31 [Equilibrium Models of the Short Rate](references/chapters/ch31_equilibrium_short_rate.md)
- Ch.32 [No-Arbitrage Models of the Short Rate](references/chapters/ch32_noarb_short_rate.md)
- Ch.33 [Modeling Forward Rates](references/chapters/ch33_forward_rate_models.md)
- Ch.34 [Swaps Revisited](references/chapters/ch34_swaps_revisited.md)
- Ch.35 [Energy and Commodity Derivatives](references/chapters/ch35_commodity_energy.md)
- Ch.36 [Real Options](references/chapters/ch36_real_options.md)
- Ch.37 [Derivatives Mishaps](references/chapters/ch37_mishaps.md)

## Other references
- [Formulas index](references/formulas_index.md) — every formula, with chapter back-links
- [Glossary](references/glossary.md) — one-line term definitions
