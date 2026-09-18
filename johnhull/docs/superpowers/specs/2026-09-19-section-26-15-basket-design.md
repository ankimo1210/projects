# §26.15 Basket Options — M7 design

Date: 2026-09-19. User approved extending the section-quality workflow to the next section. Source: Hull 11e Global Edition §26.15, physical/printed pp.628–629. The section has no worked numerical example.

## Goal and contract

Complete the requirements, independent numerics, implementation, teaching, figures and real-screen verification for §26.15. The ledger row is currently `unreviewed` and vol10 §4.5 only repeats the formula. Do not claim other sections complete.

The European call/put pays `(B_T-K)^+` / `(K-B_T)^+`, with `B_T=sum_i w_i S_i(T)`. Prices, strike and basket are currency; weights are nonnegative unitless holdings; time is years; rates and yields are continuously compounded; volatilities are annualized. At least one weight is positive. Assume constant-parameter correlated risk-neutral GBM. A symmetric positive semidefinite correlation matrix with unit diagonal is required. Reject short holdings, nonfinite inputs, invalid lengths/correlation, nonpositive spot/strike/expiry and negative volatility. Cash dividends, time-varying parameters, rebalancing, expiry zero and all-domain numerical stability are outside this milestone.

Let `F_i=w_i S_i exp((r-q_i)T)`. Exact moments are `M1=sum_i F_i` and `M2=sum_ij F_i F_j exp(rho_ij sigma_i sigma_j T)`. Pricing **approximates** the basket as lognormal, with Black forward `M1` and volatility `sqrt(log(M2/M1^2)/T)`. Put-call parity is `C-P=exp(-rT)(M1-K)`. A single nonzero asset is an exact BSM anchor; proportional perfectly correlated assets give another exact lognormal anchor. Do not call the approximate price exact because its first two moments are exact.

Public `hullkit.exotics` functions: `basket_moments(spots, weights, rate, dividends, volatilities, correlations, expiry)` returns `(M1,M2)`; `basket_option_price(spots, weights, strike, rate, dividends, volatilities, correlations, expiry, kind="call")` returns a float. Aligned numerical sequences are required. Use existing dependencies only; keep hullkit torch-free.

## Reference and delivery

M7a freezes independent two-asset prices from conditioning on the first terminal lognormal and integrating out the second analytically, plus a separate correlated-GBM Monte Carlo with standard errors for two- and three-asset cases. Direct loops calculate moments independently of hullkit. Use at least six synthetic two-asset markets, three strikes and both kinds; two three-asset markets, one-asset anchors and singular-correlation anchors. Disclose empirically measured approximation errors with a price floor and MC uncertainty; no universal error bound. Write BSK01–BSK06 requirements and register `gaps_found` until full delivery. Historical accepted evidence stays immutable.

M7b implements the API with test-first development, six short subsections in vol10 §4.5 and four shared figures: basket payoff, correlation/moments, approximate versus independent price, and relative error with uncertainty. Both Book and portal consume saved JSON whose required source hashes are checked. Notebook and report builds must not rerun expensive MC or quadrature. Preserve all notebook content outside §4.5, including §4.4 and variance swaps. Verify the saved outputs against a fresh execution, inspect both surfaces at widths 1440 and 1000 across all menu states, check shown equations and numerical values independently, and capture screen evidence. Rerun affected §26.9–§26.14 tests/browser checks on the final shared assets. Update MODEL_INDEX, release manifest, ledger, roadmap, validation and volume progress. A fresh whole-johnhull suite, ledger artifact gate and independent review are required before `accepted`.

## Tradeoffs

Nonnegative weights let the lognormal proxy have a positive underlying; supporting short baskets requires a different price model. The two-asset conditional integral excludes degenerate correlation, which gets analytic anchors; a matrix-eigenvalue MC handles singular PSD cases. Four diagrams follow this repository's teaching contract and are not attributed to Hull. Synthetic MC has sampling error; a plotted sign is not established when the gap is smaller than its uncertainty.
