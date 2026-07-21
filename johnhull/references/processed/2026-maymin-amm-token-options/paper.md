---
paper_id: "2026-maymin-amm-token-options"
title: "Option Pricing on Automated Market Maker Tokens"
authors: "Philip Z. Maymin"
year: "2026"
source_url: "https://arxiv.org/abs/2603.29763"
source_pdf: "references/papers/2026-maymin-amm-token-options.pdf"
source_sha256: "2d17e064be4679314f81a1e2da1b8711eb1913afb1dc7cb8cd79bf13ae6a8edf"
converter: "PyMuPDF4LLM 1.28.0"
---

<!-- page: 1 -->

# **Option Pricing on Automated Market Maker Tokens** 

Philip Z. Maymin<sup>∗</sup> 

February 2026 

##### **Abstract** 

We derive the stochastic price process for tokens whose sole price discovery mechanism is a constant-product automated market maker (AMM). When the net flow into the pool follows a diffusion, the token price follows a constant elasticity of variance (CEV) process, nesting Black–Scholes as the limiting case of infinite liquidity. We obtain closed-form European option prices and introduce liquidityadjusted Greeks. The CEV structure generates a leverage effect—volatility rises as price falls—whose normalized implied volatility skew depends only on the pool’s weighting parameter, not on pool depth: Black–Scholes underprices 20%-out-of-themoney puts by roughly 6% in implied volatility terms at every pool depth, while the absolute pricing discrepancy vanishes as pools deepen. Empirically, after controlling for pool depth and flow volatility, realized return variance across 90 Bittensor subnets exhibits a strongly negative price elasticity, decisively rejecting geometric Brownian motion and consistent with the CEV prediction. A complementary delta-hedged backtest across 82 subnets confirms near-identical hedging errors at the money, consistent with the prediction that pricing differences are concentrated in the wings. 

**Keywords:** automated market makers, option pricing, constant elasticity of variance, Black–Scholes, Bittensor, decentralized finance, liquidity **JEL Classification:** G12, G13, G14 

> ∗ Fairfield University Dolan School of Business. Email: `pmaymin@fairfield.edu` .

<!-- page: 2 -->

## **1 Introduction** 

Automated market makers (AMMs) have become the dominant mechanism for token exchange in decentralized finance (DeFi), processing hundreds of billions of dollars in cumulative trading volume since the launch of Uniswap in 2018 [Adams et al., 2021]. Unlike traditional order-book exchanges where prices emerge from the interaction of discrete buy and sell orders, AMMs determine prices algorithmically from the ratio of token reserves held in liquidity pools. The most widely adopted design, the _constant-product_ AMM, maintains the invariant _x · y_ = _k_ across two token reserves _x_ and _y_ , with the marginal exchange rate given by the reserve ratio [Angeris et al., 2021]. 

A new class of AMM-native tokens has emerged in which the AMM is not merely a trading venue but the _sole price discovery mechanism_ . There is no order book, no offchain market, and no external price oracle; the bonding curve _is_ the market. The most prominent example is the Bittensor network’s Dynamic TAO (dTAO) system, launched in February 2025, which assigns each of its subnets an “alpha” token traded exclusively through a dedicated constant-product AMM against the network’s native TAO token [Bittensor Foundation, 2025]. With over 60 active subnets, a total staked value exceeding $3 billion, and a growing ecosystem of subnet operators seeking to hedge treasury exposure, pricing derivatives on these tokens is an increasingly practical concern. Bittensor’s setting also provides the cleanest possible test environment for AMM price dynamics: because there is no competing venue, the observed price process is entirely determined by the AMM mechanics, making it possible to test the theory without confounding effects from external price discovery. 

The Black–Scholes model [Black and Scholes, 1973] assumes the underlying follows geometric Brownian motion (GBM) with constant volatility, an assumption justified when price changes are driven by exogenous information arrival on a deep, frictionless market. For AMM-native tokens, the price is _endogenously determined_ by the bonding curve: every trade mechanically shifts the reserve ratio, and the resulting price dynamics inherit the nonlinear structure of the AMM itself. 

The central contribution of this paper is to derive the stochastic process governing AMM token prices from first principles and to develop the resulting option pricing framework. Our main result (Theorem 1) establishes a simple identity: when the net staking flow into an AMM pool follows a Brownian diffusion, the token price follows a _constant elasticity of variance_ (CEV) model [Cox, 1975, Cox and Ross, 1996] with exponent _β_ = _w_ , the weight of the numeraire token in the pool. For the standard constant-product AMM, _β_ = 1 _/_ 2. This is not an empirical estimate; it is a mathematical consequence of the bonding curve. 

This result has several important implications: 

1. **Black–Scholes as a limiting case.** As pool liquidity _k →∞_ , the CEV volatility

<!-- page: 3 -->

parameter vanishes and the price becomes deterministic. For large but finite _k_ , the process approximates GBM, and Black–Scholes applies with an effective volatility that is inversely proportional to the square root of pool depth. The result gives a precise characterization of when standard pricing models are adequate. 

2. **Liquidity-dependent volatility and the leverage effect.** The instantaneous volatility of the AMM token price is _σ_ ( _P_ ) = _δP_<sup>_β−_1</sup> , where _δ_ is proportional to the flow volatility and inversely proportional to pool depth. For _β_ = 1 _/_ 2, volatility decreases with the square root of price. This produces a structural leverage effect (negative correlation between price and volatility) that is a consequence of the bonding curve mechanics, not capital structure. 

3. **AMM-specific Greeks.** Beyond the standard sensitivities, we derive a “liquidity Greek” Λ = _∂V/∂k_ measuring option value sensitivity to pool depth, and an “emission Greek” _E_ = _∂V/∂e_ capturing sensitivity to the token emission rate. 

4. **Quantifiable pricing discrepancy.** We provide closed-form expressions for the pricing discrepancy relative to Black–Scholes as a function of pool depth and moneyness (Figures 3 and 4), enabling practitioners to assess when the standard model is inadequate and by how much. 

5. **Universal implied volatility skew.** We show that the normalized implied volatility skew depends only on _β_ , not on the volatility parameter _δ_ or pool depth _k_ (Theorem 5). For _β_ = 1 _/_ 2, Black–Scholes underprices 20%-out-of-the-money puts by roughly 6% in implied volatility terms at every pool depth. This is a structural, falsifiable prediction. 

6. **Empirical validation.** The CEV model predicts that, after controlling for pool depth and flow volatility, realized return variance should scale as _P_<sup>2(</sup><sup>_β−_1)</sup> = _P_<sup>_−_1</sup> for constant-product AMMs. A cross-sectional test across 90 Bittensor subnets yields a median variance elasticity of _−_ 0 _._ 86 (interquartile range [ _−_ 0 _._ 98 _, −_ 0 _._ 71]), strongly rejecting the GBM null of zero ( _p <_ 0 _._ 0001) and consistent with _β_ near 1 _/_ 2. 

Our work connects three strands of literature. The first is the financial theory of AMMs, including analyses of impermanent loss [Loesch et al., 2021], AMM design [Angeris et al., 2021, 2022], and the relationship between AMM liquidity provision and option payoffs [Clark, 2021, Guillaume and Schroers, 2024]. The second is the CEV option pricing literature initiated by Cox [1975], with closed-form solutions developed by Schroder [1989] and subsequent extensions [Davydov and Linetsky, 2003, Larguinho et al., 2013]. The third is the nascent literature on Bittensor’s tokenomics and decentralized AI markets [Bittensor Foundation, 2025]. 

The remainder of the paper is organized as follows. Section 2 surveys the related literature. Section 3 describes the institutional setting, with particular attention to Bittensor’s

<!-- page: 4 -->

dTAO mechanism. Section 4 derives the CEV price process from AMM fundamentals. Section 5 develops the option pricing framework, including closed-form solutions, Greeks, and emission extensions. Section 6 provides numerical analysis, Monte Carlo validation, calibration to Bittensor data, and empirical tests of the CEV variance elasticity. Section 7 discusses limitations and extensions. Section 8 concludes. 

## **2 Related Literature** 

**AMM theory.** The mathematical foundations of constant-function market makers were established by Angeris et al. [2021], who characterized the set of feasible trades and the connection between AMM prices and external market prices. Angeris et al. [2022] extended this to optimal routing across multiple pools. Milionis et al. [2022] introduced the loss-versus-rebalancing (LVR) framework, decomposing LP returns into market risk and a predictable adverse selection cost, providing what they term a “Black–Scholes formula for AMMs.” Park [2023] identifies conceptual flaws in constant-product pricing, including persistent arbitrage and front-running vulnerabilities. The welfare properties and fee structures of AMMs are analyzed by Roughgarden [2024], while Cartea et al. [2024] develop a continuous-time model of AMM dynamics incorporating arbitrageurs and informed traders. 

**AMMs and options.** Clark [2021] showed that a constant-product AMM liquidity provider is effectively writing a perpetual straddle, and Loesch et al. [2021] formalized impermanent loss as a variance-dependent cost. Hasbrouck et al. [2024] formalize concentrated liquidity positions as covered calls, showing that LPs forgo option time value in exchange for fees. Fukasawa et al. [2023] prove that impermanent loss can be hedged with weighted variance swaps, connecting AMM positions to gamma swaps. Guillaume and Schroers [2024] developed static hedging strategies using vanilla options, and The AMM Book [2022] used the Black–Scholes formula to estimate divergence loss magnitudes. Bichuch and Feinstein [2024] derive risk-neutral prices and Greeks for LP tokens themselves, treating the LP position as a derivative of the underlying asset prices under GBM. On-chain options protocols have motivated further pricing theory: Dave [2023] and Block Scholes and Panoptic [2025] analyze perpetual options in DeFi, while Singh [2025] survey the broader DeFi options ecosystem. 

**CEV models.** The constant elasticity of variance model was introduced by Cox [1975] and extended by Cox and Ross [1996]. Empirical estimation and testing of the CEV model against equity option data were provided by Beckers [1980] and Emanuel and MacBeth [1982]. Closed-form European option prices were derived by Schroder [1989] using the non-central chi-squared distribution. Davydov and Linetsky [2003] provided

<!-- page: 5 -->

eigenfunction-based pricing, and Larguinho et al. [2013] improved the numerical stability of the CEV formula. The CEV model generates implied volatility skew controlled by the elasticity parameter, making it a parsimonious alternative to stochastic volatility models [Heston, 1993]. In the CEV literature, the elasticity parameter _β_ is typically an empirical quantity estimated from data; our contribution is to show that for AMM tokens, _β_ is pinned by the pool design ( _β_ = _w_ ) rather than estimated. 

**Concurrent work.** In independent and concurrent work, Hitier [2025] models LP portfolio value in constant-product AMMs under GBM. That paper assumes the external asset price follows GBM and derives LP value dynamics, whereas we derive the _endogenous_ price process of a token that trades _only_ through the AMM. The approaches are complementary: Hitier’s applies when the AMM is one of many trading venues; ours applies when the AMM is the sole price discovery mechanism. 

**Our contribution.** The existing literature treats LP positions _as_ derivatives (of the underlying asset price) and prices them accordingly [Bichuch and Feinstein, 2024, Hasbrouck et al., 2024]. We work in the opposite direction: we derive the stochastic process governing the _token price itself_ from the bonding curve mechanics, and then price derivatives _on_ that token. The result, that AMM token prices follow a CEV process with exponent equal to the pool weight, provides this missing link and yields a complete option pricing framework. 

## **3 Institutional Background** 

### **3.1 Constant-Product Automated Market Makers** 

A constant-product AMM maintains two token reserves ( _x, y_ ) subject to the invariant 


![](assets/2026-maymin-amm-token-options.pdf-0005-06.png)


where _k >_ 0 is constant during any individual swap. A trader who deposits ∆ _x_ units of token _X_ receives ∆ _y_ units of token _Y_ , determined by 


![](assets/2026-maymin-amm-token-options.pdf-0005-08.png)


The marginal price of token _Y_ in terms of token _X_ is 


![](assets/2026-maymin-amm-token-options.pdf-0005-10.png)

<!-- page: 6 -->

obtained by differentiating the invariant. Equation (2) implies that the effective execution price for a trade of size ∆ _x_ exceeds the marginal price by a slippage term of order ∆ _x/x_ , making large trades progressively more expensive. The design was introduced by Buterin [2017] and formalized by Angeris et al. [2021]. 

**Example 1** (A simple constant-product AMM) **.** Suppose a pool holds _x_ = 1 _,_ 000 TAO and _y_ = 40 _,_ 000 ALPHA, so _k_ = _x · y_ = 4 _×_ 10<sup>7</sup> and the marginal price is _P_ = 1 _,_ 000 _/_ 40 _,_ 000 = 0 _._ 025 TAO per ALPHA. A trader who stakes 100 TAO receives 


![](assets/2026-maymin-amm-token-options.pdf-0006-02.png)


After the trade the reserves are _x_ = 1 _,_ 100 and _y_ = 36 _,_ 363 _._ 6, the invariant is still _k_ = 4 _×_ 10<sup>7</sup> , and the new price is _P_<sup>_′_</sup> = 1 _,_ 100 _/_ 36 _,_ 363 _._ 6 _≈_ 0 _._ 0302. A deposit equal to 10% of the TAO reserve moved the price by 21%. This amplification of flows into price changes is the mechanism that generates the CEV dynamics derived in Section 4. Note that a pool ten times deeper ( _k_ = 4 _×_ 10<sup>9</sup> ) would produce correspondingly smaller price impact from the same trade, foreshadowing the Black–Scholes limit of infinite pool depth. 

### **3.2 Generalized Constant-Function AMMs** 

The constant-product design is a special case of the _constant-weighted-product_ family: 


![](assets/2026-maymin-amm-token-options.pdf-0006-06.png)


where _w ∈_ (0 _,_ 1) is the weight of token _X_ (the numeraire) and _K >_ 0. For _w_ = 1 _/_ 2, this reduces to the constant-product AMM with _K_ = _√k_ . Platforms such as Balancer implement arbitrary weights, enabling asymmetric exposure [Martinelli and Mushegian, 2019]. The marginal price under (4) is 


![](assets/2026-maymin-amm-token-options.pdf-0006-08.png)


### **3.3 Bittensor and Dynamic TAO** 

Bittensor is a decentralized network for AI services organized into _subnets_ , each specializing in a particular machine learning task. Since February 2025, the network employs Dynamic TAO (dTAO), under which each subnet _i_ maintains an independent constantproduct AMM with reserves ( _xi, yi_ ), where _xi_ is the TAO (native currency) reserve and _yi_ is the subnet-specific “alpha” ( _αi_ ) reserve [Bittensor Foundation, 2025]. 

Users “stake” TAO into a subnet by swapping TAO for alpha through the AMM, and “unstake” by swapping alpha back for TAO. The alpha price in TAO is _Pi_ = _xi/yi_ . Three features distinguish this setting from standard AMMs:

<!-- page: 7 -->

1. **No external market.** Alpha tokens trade exclusively through the on-chain AMM. There is no order book, no off-chain market, and no external price oracle. The AMM is the sole price discovery mechanism. 

2. **Pool liquidity injection.** Each block (approximately every 12 seconds), the protocol injects TAO into the subnet’s AMM reserve. The TAO allocated to subnet _i_ is 


![](assets/2026-maymin-amm-token-options.pdf-0007-02.png)


where _E_ block is the total TAO block emission (currently 0.5 TAO per block, following the December 2025 halving from 1 TAO per block), _Si_ is the exponentially weighted moving average of net TAO flows into subnet _i_ , and _L_ is a lower threshold. Simultaneously, alpha is injected into the pool in proportion ∆ _αi_ = ∆ _τi/Pi_ , preserving the current spot price while deepening liquidity [Bittensor Foundation, 2025]. This grows the invariant _ki_ = _xi ·yi_ over time without changing the price, mechanically dampening price volatility. 

3. **Alpha participant emissions.** Independently of the pool injection, each subnet emits alpha to _participants_ at a base rate of approximately 1 alpha per block, subject to its own halving schedule (both TAO and each alpha are capped at 21 million). At the end of each tempo (360 blocks), this participant alpha is distributed: 41% to miners, 41% to validators and their stakers, and 18% to the subnet owner. This alpha does not enter the pool. It increases circulating supply outside the pool and can exert selling pressure if recipients swap their alpha back to TAO through the AMM. 

**Example 2** (Emission mechanics) **.** Suppose subnet _i_ has reserves _xi_ = 1 _,_ 000 TAO and _yi_ = 40 _,_ 000 ALPHA, so _Pi_ = 0 _._ 025 TAO per ALPHA. In a single block, the pool injection channel adds ∆ _τi_ = 0 _._ 01 TAO<sup>1</sup> and ∆ _αi_ = 0 _._ 01 _/_ 0 _._ 025 = 0 _._ 4 ALPHA to the reserves. The new reserves are _xi_ = 1 _,_ 000 _._ 01 and _yi_ = 40 _,_ 000 _._ 4, the invariant grows from _k_ = 4 _×_ 10<sup>7</sup> to _k_<sup>_′_</sup> _≈_ 4 _._ 0001 _×_ 10<sup>7</sup> , and the price is unchanged at _Pi_ = 0 _._ 025. Separately, the protocol emits 1 ALPHA to participants (0.41 to miners, 0.41 to validators and stakers, 0.18 to the subnet owner). This alpha does not enter the pool but increases circulating supply. If recipients sell it through the AMM, it exerts downward pressure on the alpha price. Over one tempo (360 blocks, roughly 72 minutes), the pool injection deepens reserves by 3.6 TAO and 144 ALPHA, while 360 ALPHA is distributed to participants. 

> 1The total emission is 0.5 TAO per block (post-halving). With roughly 60 active subnets competing via (6), 0.01 TAO per block is illustrative of an average subnet.

<!-- page: 8 -->

## **4 The Model** 

### **4.1 Setup and Notation** 

Consider a single AMM pool with reserves ( _x_ ( _t_ ) _, y_ ( _t_ )) satisfying the constant-weightedproduct invariant (4). Let _P_ ( _t_ ) =<sup><u>1</u></sup><sup>_−_</sup> _w_<sup>_<u>w</u>_</sup> _·_<sup>_x_</sup> _y_ (<sup><u>(</u></sup> _t_<sup>_t_</sup> )<sup><u>)</u>denotethemarginalpriceattime</sup><sup>_t_.Define</sup> the _net flow process F_ ( _t_ ) as the cumulative net TAO staked into the pool by time _t_ . 

**Definition 1** (Stochastic Flow Process) **.** The net flow process satisfies 


![](assets/2026-maymin-amm-token-options.pdf-0008-04.png)


where _µF ∈_ R is the drift (expected net inflow rate), _σF >_ 0 is the flow volatility, and _W_ ( _t_ ) is a standard Brownian motion on a filtered probability space (Ω _, F, {Ft},_ P). 

The assumption that flow follows a Brownian diffusion is a continuous-time approximation to discrete staking and unstaking events. When individual staking amounts are small relative to pool size (the standard “many small traders” assumption), this is justified by the functional central limit theorem. We relax this assumption in Section 7 by considering jump-diffusion flows. 

### **4.2 Reserve Dynamics** 

In the absence of emissions, the reserves evolve according to the AMM mechanics: 


![](assets/2026-maymin-amm-token-options.pdf-0008-09.png)


and the constant-weighted-product constraint (4) determines _y_ ( _t_ ) implicitly: 


![](assets/2026-maymin-amm-token-options.pdf-0008-11.png)


Differentiating via Itô’s lemma yields 


![](assets/2026-maymin-amm-token-options.pdf-0008-13.png)


### **4.3 Derivation of the Price Process** 

We now derive the central result: the stochastic differential equation governing the AMM token price. 

**Theorem 1** (AMM Token Price Process) **.** _Under the constant-weighted-product AMM_ (4) _with net flow process_ (7) _, the marginal token price P_ ( _t_ ) _satisfies the CEV stochastic_

<!-- page: 9 -->

![](assets/2026-maymin-amm-token-options.pdf-0009-00.png)


<!-- Start of picture text -->
—(—)<br>—(—) —(—)<br>oe<br>~ 7<br>—(—) 0<br>a<br><!-- End of picture text -->

<!-- page: 10 -->

_process approximates GBM:_ 


![](assets/2026-maymin-amm-token-options.pdf-0010-01.png)


_and Black–Scholes applies with volatility σ_ = _σ_ eff _._ 

**Remark 1** (Elasticity spectrum) **.** The CEV exponent _β_ = _w_ reveals a fundamental connection between AMM design and price dynamics: 

- _w_ = 1 _/_ 2 (constant-product): _β_ = 1 _/_ 2, variance decreases with price. This is the standard Uniswap/Bittensor case. 

- _w →_ 1 (pool dominated by numeraire): _β →_ 1, approaching GBM and Black– Scholes. 

- _w →_ 0 (pool dominated by alpha): _β →_ 0, approaching the Bachelier (normal) model. 

AMM designers thus implicitly select a volatility structure through their choice of pool weights. 

### **4.4 Properties of the CEV Price Process** 

**Proposition 4** (Volatility structure) **.** _Under_ (11) _, the instantaneous return volatility is_ 


![](assets/2026-maymin-amm-token-options.pdf-0010-10.png)


_For the constant-product AMM (β_ = 1 _/_ 2 _), σ_ ret( _P_ ) = _δ/√P : volatility is inversely proportional to the square root of price._ 

This property has a natural economic interpretation. When the alpha token price is high, the TAO reserve _x_ is large (since _P ∝ x_<sup>2</sup> _/k_ ), meaning the pool is deep in TAO terms. A given staking flow d _F_ then produces a smaller proportional change in _x_ , hence a smaller proportional price impact. Conversely, when the price is low, the TAO reserve is shallow, and the same flow produces larger price swings. 

**Proposition 5** (Implied volatility skew) **.** _The CEV model with β <_ 1 _generates a negative implied volatility skew: out-of-the-money puts have higher Black–Scholes implied volatility than out-of-the-money calls. When implied volatilities are normalized by the ATM level, the skew shape depends only on β, not on the volatility parameter δ or pool depth k._ 

_Proof._ The negative skew is a standard property of the CEV model with _β <_ 1 [Cox and Ross, 1996, Davydov and Linetsky, 2003]. For the universality of the normalized skew, observe the following. First, _C_ ( _λP, λK_ str _, T_ ) = _λC_ ( _P, K_ str _, T_ ) for all _λ >_ 0 (homogeneity

<!-- page: 11 -->

of degree one in spot and strike), so implied volatility depends only on the moneyness ratio _K_ str _/P_ . Second, the parameters of the non-central chi-squared distribution are _κ_ = 2 _r/_ [ _δ_<sup>2</sup> (1 _− β_ )( _e_<sup>2</sup><sup>_r_(1</sup><sup>_−β_)</sup><sup>_T_</sup> _−_ 1)], _a_ = _κK_ str<sup>2(1</sup><sup>_−β_)</sup> , _c_ = _κP_<sup>2(1</sup><sup>_−β_)</sup> _e_<sup>2</sup><sup>_r_(1</sup><sup>_−β_)</sup><sup>_T_</sup> , and _b_ = 1 _/_ (1 _− β_ ). Since _κ ∝ δ_<sup>_−_2</sup> , changing _δ_ (equivalently, changing pool depth _k_ ) rescales both _a_ and _c_ by the same multiplicative factor, while the ratio _a/c_ = ( _K_ str _/P_ )<sup>2(1</sup><sup>_−β_)</sup> _e_<sup>_−_2</sup><sup>_r_(1</sup><sup>_−β_)</sup><sup>_T_</sup> depends only on moneyness, _β_ , and calendar parameters. The degrees of freedom _b_ depend only on _β_ . The CEV call price, and hence the implied volatility at each moneyness, is therefore determined by _β_ once the ATM level is fixed. It follows that the _normalized_ skew _σ_ IV( _K_ ) _/σ_ ATM is invariant to _δ_ and _k_ . 

**Proposition 6** (Boundary behavior at zero) **.** _For β_ = 1 _/_ 2 _, the CEV process_ (11) _has P_ = 0 _as a boundary point. The classification depends on the drift:_ 

_1. Under the risk-neutral measure_ Q _(drift rP with r >_ 0 _), the Feller test shows that the scale function s_ ( _P_ ) = � _P_ exp( _−_ 2 _r/_ ( _δ_ 2 _u_ )) d _u diverges as P →_ 0+ _, so zero is an_ inaccessible _(entrance) boundary: the process cannot reach zero in finite time, and the pricing formula_ (22) _is well-defined without boundary correction._ 

_2. Under the physical measure_ P _, when the drift µ_ ( _P_ ) _is small relative to δ_<sup>2</sup> _(i.e.,_ 2 _µF /_ ( _σF_<sup>2</sup> _√k_ ) _<_ 1 _), the speed measure is integrable near zero and the boundary is_ attainable _: a sufficiently unfavorable sequence of outflows can drain the TAO reserve to zero._ 

_Economically, P_ = 0 _corresponds to a fully drained TAO reserve (x_ = 0 _), at which point the AMM cannot quote a price. Once the TAO reserve is exhausted, no further trades are possible without external injection (e.g., emissions). For option pricing, the inaccessibility of zero under_ Q _ensures that the non-central chi-squared formula accounts correctly for the boundary._ 

**Remark 2** (Leverage effect) **.** The CEV structure with _β <_ 1 generates a negative correlation between the price level and return volatility: as _P_ falls, _σ_ ret( _P_ ) = _δP_<sup>_β−_1</sup> rises. In equity markets, this “leverage effect” is typically attributed to increased financial leverage as firm value declines [Black and Scholes, 1973]. For AMM tokens, the mechanism is purely structural. When the alpha price falls, the TAO reserve _x_ = _√kP_ decreases, making the pool shallower in TAO terms. The same dollar-equivalent staking flow then moves the price proportionally more. The AMM bonding curve thus provides a first-principles derivation of the leverage effect, grounded in market microstructure rather than capital structure.

<!-- page: 12 -->

## **5 Option Pricing** 

### **5.1 Risk-Neutral Dynamics** 

Under the risk-neutral measure Q, the CEV price process becomes 


![](assets/2026-maymin-amm-token-options.pdf-0012-03.png)


where _r_ is the risk-free rate and _W_<sup>Q</sup> is a Q-Brownian motion. The change of measure from P to Q is effected via the Girsanov kernel _θ_ ( _P_ ) = [ _µ_ ( _P_ ) _− rP_ ] _/_ ( _δP_<sup>_β_</sup> ), which is bounded whenever _P_ is bounded away from zero. A standard localization argument establishes Q: define stopping times _τn_ = inf _{t_ : _P_ ( _t_ ) _<_ 1 _/n}_ and apply Girsanov’s theorem on each [0 _, τn ∧ T_ ], where _θ_ is bounded. Since _P_ (0) _>_ 0 and zero is inaccessible under the resulting risk-neutral dynamics (Theorem 6), _τn →∞_ a.s. under Q, yielding the global measure change. The existence of the equivalent martingale measure for CEV processes with _β ∈_ (0 _,_ 1) is established rigorously by Davydov and Linetsky [2003] (see their §3). 

The risk-neutral pricing argument requires approximate replicability of contingent claims by dynamic trading in the underlying. For AMM tokens, this is imperfect due to slippage: a trade of size ∆ _x_ incurs a price impact of order ∆ _x/x_ . When individual hedge trades are small relative to the TAO reserve (i.e., _|_ ∆ _x| ≪ x_ ), the slippage cost is second-order and the replication error is bounded. We quantify this error in Section 5.5 and show it scales as _k_<sup>_−_2</sup> , becoming negligible for deep pools. 

### **5.2 European Option Pricing Formula** 

The European call price under the CEV model was derived by Cox [1975] and refined by Schroder [1989]. For _β <_ 1 (which includes the constant-product case _β_ = 1 _/_ 2), zero is inaccessible under the risk-neutral measure (Theorem 6), so the non-central chi-squared representation is well-defined and no boundary correction is required. The price of a European call with strike _K_ str and maturity _T_ is: 

**Theorem 7** (CEV Call Price) **.** 


![](assets/2026-maymin-amm-token-options.pdf-0012-09.png)

<!-- page: 13 -->

_where χ_<sup>2</sup> ( _x_ ; _n, λ_ ) _denotes the cumulative distribution function of the non-central chisquared distribution with n degrees of freedom and non-centrality parameter λ, and_ 


![](assets/2026-maymin-amm-token-options.pdf-0013-01.png)


![](assets/2026-maymin-amm-token-options.pdf-0013-02.png)


![](assets/2026-maymin-amm-token-options.pdf-0013-03.png)


For the constant-product AMM ( _β_ = 1 _/_ 2), these simplify to _b_ = 2 and 


![](assets/2026-maymin-amm-token-options.pdf-0013-05.png)


The European put price follows from put-call parity: 


![](assets/2026-maymin-amm-token-options.pdf-0013-07.png)


**Remark 3** (Convergence to Black–Scholes) **.** As _β →_ 1 with _δP_ 0<sup>_β−_1</sup> = _σ_ held fixed, the CEV call price (22) converges to the Black–Scholes formula 


![](assets/2026-maymin-amm-token-options.pdf-0013-09.png)


where _d_ 1 _,_ 2 =<sup>ln(</sup><sup>_P/K_str</sup> _σ_<sup><u>)+(</u></sup> _~~√~~ T_<sup>_r±σ_2</sup><sup>_<u>/</u>_2)</sup><sup>_T_</sup> . The CEV formula thus formally justifies using Black– Scholes when AMM liquidity is large. 

### **5.3 The Liquidity-Adjusted Black–Scholes Formula** 

To make the connection to Black–Scholes explicit, we decompose the CEV call price as 


![](assets/2026-maymin-amm-token-options.pdf-0013-13.png)


where _σ_ eff = _δP_<sup>_w−_1</sup> is the effective volatility at the current price, and Λ _C_ is the _liquidity correction_ , i.e., the residual difference due to the price-dependent volatility structure. 

**Proposition 8** (Liquidity correction) **.** _The liquidity correction_ Λ _C_ = _C_ CEV _− C_ BS( _σ_ eff) _at the money satisfies_ Λ _C_ = _O_ ( _δ_<sup>2</sup> ) _as δ →_ 0 _(equivalently, k →∞). For general moneyness,_ Λ _C is positive for in-the-money calls (and out-of-the-money puts) and negative for outof-the-money calls (and in-the-money puts), consistent with the negative skew generated by β <_ 1 _. At the money, the correction is positive but very small: the CEV call price slightly exceeds Black–Scholes._

<!-- page: 14 -->

The magnitude of the liquidity correction scales with _δ_<sup>2</sup> _∝ K_<sup>_−_2</sup> , confirming that it vanishes rapidly as pool depth increases. 

### **5.4 Liquidity-Adjusted Greeks** 

The standard option Greeks are modified by the CEV structure. We also introduce two new sensitivities specific to AMM tokens. 

**Definition 2** (AMM Greeks) **.** The _CEV delta_ and _CEV gamma_ of a European call are 


![](assets/2026-maymin-amm-token-options.pdf-0014-04.png)


The _liquidity Greek_ is 


![](assets/2026-maymin-amm-token-options.pdf-0014-06.png)


measuring the sensitivity of the option price to changes in pool depth. For the constantproduct AMM, _δ_ = 2 _σF /√k_ , so _∂δ/∂k_ = _−σF /k_<sup>3</sup><sup>_/_2</sup> , and Λ _<_ 0: deeper pools reduce option value by compressing volatility. 

#### The _emission Greek_ is 


![](assets/2026-maymin-amm-token-options.pdf-0014-09.png)


measuring sensitivity to the emission rate _e_ that governs the growth of _k_ over time (see Section 5.6). Using the integrated variance (41), _E_ can be computed via the chain rule: _E_ = ( _∂C/∂v_ ¯<sup>2</sup> )( _∂v_ ¯<sup>2</sup> _/∂k_<sup>˙</sup> )( _∂k/∂e_<sup>˙</sup> ). Since _∂v_ ¯<sup>2</sup> _/∂k_<sup>˙</sup> _<_ 0 and _∂C/∂v_ ¯<sup>2</sup> _>_ 0 (option prices increase with variance), the emission Greek is negative: higher emissions reduce option value by deepening the pool over the option’s lifetime. 

### **5.5 Hedging Error from AMM Friction** 

Delta-hedging an option on an AMM token requires trading through the AMM, incurring slippage. For a hedge trade of ∆ _P_ units of alpha, the slippage cost in a constant-product AMM is approximately 


![](assets/2026-maymin-amm-token-options.pdf-0014-13.png)


Over a hedging interval ∆ _t_ with rebalancing, the cumulative expected hedging cost is 


![](assets/2026-maymin-amm-token-options.pdf-0014-15.png)

<!-- page: 15 -->

which scales as _k_<sup>_−_2</sup> , an additional friction cost beyond the standard model. This cost should be added to the option price as a _replication premium_ . 

**Proposition 9** (Replication premium) **.** _The replication premium for a European call on a constant-product AMM token is bounded by_ 


![](assets/2026-maymin-amm-token-options.pdf-0015-02.png)


_As k →∞, R →_ 0 _and exact replication is recovered._ 

**Remark 4** (Replication–relevance tension) **.** A conceptual tension arises: the CEV correction to Black–Scholes is largest for shallow pools (small _k_ ), but the replication premium is also largest for small _k_ since it scales as _k_<sup>_−_2</sup> . For the shallowest pool in our sample (SN58, _k_ = 7 _._ 4 _×_ 10<sup>9</sup> ), the bound (37) evaluates to less than 10<sup>_−_6</sup> % of the option price, – confirming that the CEV-BS pricing discrepancy (of order 1 6% of implied volatility) dominates the replication friction by many orders of magnitude. The _k_<sup>_−_2</sup> scaling of the friction versus the _k_<sup>_−_1</sup> scaling of the pricing discrepancy means the replication argument holds in precisely the regime where the CEV correction matters. For very shallow pools not represented in our data (e.g., _k <_ 10<sup>5</sup> ), the replication premium could become material, and CEV prices should be interpreted as fair value benchmarks rather than strict arbitrage-free prices. 

### **5.6 Extension: Token Emissions** 

When emissions inject TAO and alpha into the pool at rates _e_ TAO and _eα_ per unit time, the pool invariant grows deterministically: 


![](assets/2026-maymin-amm-token-options.pdf-0015-07.png)


At equilibrium with _P_ near _P_ 0, reserves grow approximately in proportion (∆ _x/x ≈_ ∆ _y/y_ ), maintaining roughly constant price while deepening the pool. For option horizons short relative to the emission timescale ( _T ≪ k_ 0 _/k_<sup>˙</sup> ), this simplifies to 


![](assets/2026-maymin-amm-token-options.pdf-0015-09.png)


The CEV volatility parameter becomes time-dependent: 


![](assets/2026-maymin-amm-token-options.pdf-0015-11.png)


**Proposition 10** (Option pricing with emissions) **.** _Under deterministically time-varying δ_ ( _t_ ) _and the assumption that k_ ( _t_ ) _evolves slowly relative to the option horizon (so that the_

<!-- page: 16 -->

_time-change from calendar time to “variance time” is approximately deterministic), the CEV call price formula_ (22) _remains valid with δ_<sup>2</sup> _T replaced by the integrated variance:_ 


![](assets/2026-maymin-amm-token-options.pdf-0016-01.png)


¯ _As k_<sup>˙</sup> _→_ 0 _(no emissions), v_<sup>2</sup> _→_ 4 _σF_<sup>2</sup><sup>_T/k_0=</sup><sup>_δ_</sup> 0<sup>2</sup><sup>_T,recoveringtheconstantcase._</sup> 

¯ Emissions have a dampening effect: higher emission rates increase _k_<sup>˙</sup> , reducing _v_<sup>2</sup> and hence option prices. Intuitively, growing liquidity compresses the range of possible price outcomes. 

**Remark 5** (Emissions as a dividend yield) **.** The emission effect can be interpreted as an effective continuous dividend yield. Expanding _v_ ¯<sup>2</sup> for small _kT/k_<sup>˙</sup> 0: 


![](assets/2026-maymin-amm-token-options.pdf-0016-05.png)


so the integrated variance is reduced by a factor that is first-order in _k/k_<sup>˙</sup> 0. Defining an effective dividend yield _q_ eff = _k/_<sup>˙</sup> (2 _k_ 0), the emission-adjusted CEV price approximately equals the zero-emission price on an underlying with continuous yield _q_ eff. In practice, one can estimate _k_<sup>˙</sup> from the emission schedule and discount the option value accordingly. 

Bittensor’s emission allocation (6) introduces a feedback loop: high staking flows raise _Si_ , increasing the subnet’s emission share, deepening the pool, and compressing volatility. Modeling this endogenous _k_<sup>˙</sup> coupled to the flow process is left for future work. 

## **6 Numerical Analysis** 

### **6.1 Parameter Calibration** 

We calibrate the model to Bittensor subnet data as of February 2026, retrieved from the Taostats API. We select three representative subnets spanning the range of pool depths observed across the network: 

Table 1: Representative Bittensor subnet parameters (median values over the sample period August 8, 2025 to February 23, 2026). Reserves are in native token units; _σ_ ˆ _F_ is the annualized standard deviation of daily TAO reserve changes. 

|Subnet|_x_0 (TAO)|_y_0 (_α_)|_k_ (_×_10<sup>9</sup>)|_P_0 (TAO/_α_)|ˆ_σF_|
|---|---|---|---|---|---|
|Shallow (SN58)|4,019|1,835,800|7.4|0.0022|2,293|
|Medium (SN1)|22,568|2,340,831|52.8|0.0096|3,571|
|Deep (SN3)|54,445|2,151,385|117.1|0.0253|8,250|

<!-- page: 17 -->

The flow volatility _σ_ ˆ _F_ is estimated from the standard deviation of daily net TAO ˆ ˆ reserve changes, annualized ( _σF_ = _s_ ∆ _F ·√_ 365, where ˆ _s_ ∆ _F_ is the sample standard deviation of daily flow changes). This estimator is consistent under the diffusion assumption and can be computed directly from on-chain reserve data. The risk-free rate is set to _r_ = 5% (approximate stablecoin lending rate in DeFi). 

**Remark 6** (Distributional properties of staking flows) **.** Shapiro–Wilk tests reject the normality of daily TAO reserve changes at the 5% level for all 98 subnets in our sample. The median excess kurtosis is 10.7 (range [0 _._ 6 _,_ 189 _._ 6]) and the median skewness is _−_ 0 _._ 62, indicating heavy-tailed, left-skewed flow distributions. The Brownian diffusion assumption (Definition 1) is thus an approximation, as is standard for continuous-time models applied to discrete financial data. The heavy tails are consistent with occasional large staking events (“whale” trades) and support the jump-diffusion extension discussed in Section 7. That the cross-sectional backtest (Section 6.5) produces reasonable hedging errors (median MAE _≈_ 3% of spot) despite these departures suggests the CEV framework is robust to moderate violations of the diffusion assumption. 

**Remark 7** (Testable predictions) **.** Even in the absence of traded options, the CEV model generates testable predictions about the physical price process. The return variance should be proportional to _P_<sup>2(</sup><sup>_β−_1)</sup> = _P_<sup>_−_1</sup> for the constant-product case, a relationship that can be estimated from realized variance regressions on price levels using on-chain data. 

### **6.2 Monte Carlo Validation** 

To validate the closed-form formula, we simulate _N_ = 100 _,_ 000 paths of the flow process d _F_ = _µF_ d _t_ + _σF_ d _W_ using Euler–Maruyama discretization with hourly time steps. At each step, the TAO reserve updates as _xt_ +∆ _t_ = _xt_ + ∆ _Ft_ , the alpha reserve follows from the invariant _y_ = _k/x_ , and the terminal price is _PT_ = _x_<sup>2</sup> _T_<sup>_/k_.TheMonteCarlocallprice</sup> is _C_ MC = _e_<sup>_−rT_</sup> E[max( _PT − K_ str _,_ 0)]. 

Figure 1 illustrates the qualitative difference between CEV and GBM dynamics. The left panel overlays paths from both models driven by the same Brownian increments: the paths visibly diverge as price moves away from _P_ 0, with CEV producing wider swings at low prices and narrower swings at high prices. The right panel shows the terminal price distribution from 50,000 Monte Carlo paths, revealing the CEV model’s heavier left tail, a direct consequence of the leverage effect.

<!-- page: 18 -->

![](assets/2026-maymin-amm-token-options.pdf-0018-00.png)


<!-- Start of picture text -->
Sample paths: CEV (solid) vs GBM (dashed) Terminal distribution at T = 90 days<br>CEV CEV<br>GBM GBM<br>0.05 40<br>0.04 30<br>0.03<br>20<br>0.02<br>10<br>0.01<br>0<br>0 10 20 30 40 50 60 70 80 90 0.00 0.01 0.02 0.03 0.04 0.05 0.06<br>Days Terminal price PT<br>)<br>Price (TAO/ Density<br><!-- End of picture text -->

Figure 1: Left: simulated price paths under CEV (solid) and GBM (dashed) driven by identical Brownian increments, with volatilities matched at _P_ 0. The paths visibly diverge as price moves away from _P_ 0: CEV produces wider swings at low prices (leverage effect) and narrower swings at high prices. Right: terminal price distribution from 50,000 Monte Carlo paths at _T_ = 90 days. The CEV distribution exhibits a heavier left tail and positive skew relative to GBM, consistent with the structural leverage effect. Parameters: _P_ 0 = 0 _._ 025, _k_ = 5 _×_ 10<sup>5</sup> , _σF_ = 48 _._ 7. 

Figure 2 compares the Monte Carlo prices with the CEV closed-form formula across strikes for two pool depths ( _T_ = 30 days). For the deep pool ( _k_ = 10<sup>9</sup> ), the maximum deviation is less than 0.5% of spot. For the shallow pool ( _k_ = 10<sup>6</sup> ), MC prices exceed the CEV formula by 1–3% of spot: when _σF_ is large relative to the reserve _x_ 0 =<sup>_√_</sup> _kP_ 0, a single hourly flow shock can represent several percent of the reserve, violating the diffusion limit’s small-increment assumption. The positive bias reflects truncation of large negative flow shocks at the reflecting boundary _x >_ 0. The Monte Carlo standard error is below 0.2% of spot for all strikes and pool depths.

<!-- page: 19 -->

![](assets/2026-maymin-amm-token-options.pdf-0019-00.png)


<!-- Start of picture text -->
Shallow Pool (k = 10 6 ) Deep Pool (k = 10 9 )<br>40 CEV (closed-form) Monte Carlo (100K paths) 40 CEV Monte Carlo (100K paths)(closed-form)<br>35 35<br>30 30<br>25 25<br>20 20<br>15 15<br>10 10<br>5 5<br>0 0<br>0.6 0.7 0.8 0.9 1.0 1.1 1.2 1.3 1.4 0.6 0.7 0.8 0.9 1.0 1.1 1.2 1.3 1.4<br>Pricing Error Pricing Error<br>0.0<br>0.4 0.1<br>0.2<br>0.2<br>0.3<br>0.4<br>0.0<br>0.6 0.8 1.0 1.2 1.4 0.6 0.8 1.0 1.2 1.4<br>Moneyness (K/P0) Moneyness (K/P0)<br>Call Price (% of spot) Call Price (% of spot)<br> CEV (% of spot)  CEV (% of spot)<br>MC  MC<br><!-- End of picture text -->

Figure 2: Monte Carlo validation of the CEV pricing formula for a shallow pool ( _k_ = 10<sup>6</sup> , left) and a deep pool ( _k_ = 10<sup>9</sup> , right). Top: closed-form CEV call prices (line) vs. Monte Carlo estimates with 95% confidence intervals (points). Bottom: pricing error (MC minus CEV) as a percentage of spot. The shallow pool shows a systematic positive bias of 1–3% of spot, reflecting the Euler–Maruyama discretization error that is amplified when flow volatility is large relative to the reserve. The deep pool shows near-perfect agreement (errors _<_ 0 _._ 5%). Illustrative parameters: _P_ 0 = 0 _._ 025, _σF_ = 48 _._ 7, _T_ = 30 days, 100,000 paths. 

### **6.3 Comparative Statics** 

Figure 3 illustrates the relationship between option prices and pool depth. The left panel shows that CEV and Black–Scholes ATM call prices are visually indistinguishable. The right panel plots _|C_ CEV _− C_ BS _|_ on a log-log scale: OTM discrepancies dominate ATM by orders of magnitude, and all curves decline approximately as _O_ ( _k_<sup>_−_1</sup> ), confirming the scaling predicted by Theorem 8.

<!-- page: 20 -->

![](assets/2026-maymin-amm-token-options.pdf-0020-00.png)


<!-- Start of picture text -->
ATM Option Price vs. Pool Depth Absolute Pricing Discrepancy<br>10 1<br>80 10 1<br>10 3<br>60<br>10 5<br>40 10 7<br>10 9<br>10% OTM put<br>20 10 11 5% OTM put<br>ATM<br>5% OTM call<br>CEV ( = 1/2) SN58 SN1SN3 10 13 10% OTM call<br>0 Black Scholes O(k 1)<br>10 4 10 5 10 6 10 7 10 8 10 9 10 10 10 11 10 12 10 4 10 5 10 6 10 7 10 8 10 9 10 10<br>Pool Depth k (log scale) Pool Depth k (log scale)<br>| (% of spot)BS<br>C<br>CEV<br>|C<br>ATM Call Price (% of spot)<br><!-- End of picture text -->

Figure 3: Left: ATM call price (as % of spot) vs. pool depth _k_ . The CEV (solid blue) and Black–Scholes (dashed red) curves overlap, confirming that the models agree at the _−_ money. Right: absolute pricing discrepancy _|C_ CEV _C_ BS _|_ (as % of spot) on a log-log scale, for five moneyness levels. OTM options (puts in green/cyan, calls in orange/red) show discrepancies orders of magnitude larger than ATM (blue), reflecting the leverage-induced skew. All curves decline approximately as _O_ ( _k_<sup>_−_1</sup> ) (dotted reference line). Illustrative parameters: _P_ 0 = 0 _._ 025, _σF_ = 48 _._ 7, _T_ = 90 days, _r_ = 5%. 

Figure 4 plots implied volatility as a function of moneyness. Absolute implied volatility is higher for shallower pools ( _σ_ ATM _∝ k_<sup>_−_1</sup><sup>_/_2</sup> ), but the normalized curves overlap almost exactly, confirming the universal-skew result of Theorem 5: the skew depends on _β_ alone, not on pool depth. 


![](assets/2026-maymin-amm-token-options.pdf-0020-03.png)


<!-- Start of picture text -->
Absolute Implied Volatility Normalized Skew<br>1.06<br>Shallow (k = 5 × 10 5 )<br>Medium (k = 5 × 10 6 )<br>80 1.04 Deep (k = 5 × 10 7 )<br>1.02<br>60<br>1.00<br>40<br>0.98<br>20 Shallow (k = 5 × 10 5 )<br>Medium (k = 5 × 10 6 ) 0.96<br>Deep (k = 5 × 10 7 )<br>0.80 0.85 0.90 0.95 1.00 1.05 1.10 1.15 1.20 0.80 0.85 0.90 0.95 1.00 1.05 1.10 1.15 1.20<br>Moneyness (K/P0) Moneyness (K/P0)<br>ATM<br>IV / IV<br>Implied Volatility (%)<br><!-- End of picture text -->

Figure 4: Left: absolute Black–Scholes implied volatility extracted from CEV prices. Shallower pools produce higher absolute volatility due to larger _δ_ . Right: implied volatility normalized by the at-the-money level, isolating the skew shape. The three normalized curves overlap, confirming that the skew depends only on _β_ = 1 _/_ 2, not on pool depth. Illustrative parameters: _P_ 0 = 0 _._ 025, _σF_ = 48 _._ 7, _T_ = 90 days. 

Figure 5 compares the CEV and Black–Scholes delta and gamma. The CEV delta is steeper for low prices and flatter for high prices, reflecting the price-dependent volatility. Both gammas peak below the strike, but the CEV gamma is sharper and peaks further below, concentrating risk in the high-volatility (low-price) region.

<!-- page: 21 -->

![](assets/2026-maymin-amm-token-options.pdf-0021-00.png)


<!-- Start of picture text -->
Delta Comparison Gamma Comparison<br>1.0 CEV ( = 1/2) CEV ( = 1/2)<br>Black--Scholes Black--Scholes<br>40<br>0.8<br>30<br>0.6<br>0.4 20<br>0.2 10<br>0.0<br>10 15 20 25 30 35 40 45 50 10 15 20 25 30 35 40 45 50<br>Price (TAO/ × 1000) Price (TAO/ × 1000)<br>Delta<br>Gamma<br><!-- End of picture text -->

Figure 5: Comparison of CEV ( _β_ = 1 _/_ 2) and Black–Scholes Greeks for an ATM European call ( _K_ = 0 _._ 025) on a shallow pool. Left: delta. Right: gamma. Both gammas peak below the strike, but the CEV gamma is sharper and peaks further below, reflecting its concentration in the high-volatility (low-price) region. Illustrative parameters: _k_ = 5 _×_ 10<sup>5</sup> , _σF_ = 48 _._ 7, _T_ = 90 days. 

### **6.4 Effect of Emissions** 

Figure 6 shows that higher emissions compress option prices, particularly at longer maturities where cumulative liquidity deepening is greatest. Figure 7 plots the liquidity Greek Λ = _∂C/∂k_ : it is negative throughout and decays rapidly, confirming that liquidity sensitivity is primarily a concern for shallow pools. 

### **6.5 Empirical Backtest** 

We conduct a cross-sectional backtest across all active Bittensor subnets to test whether the theoretical divergence between CEV and Black–Scholes pricing varies systematically with pool depth. Our sample construction proceeds as follows: of the 128 subnets in the network, 98 have sufficient on-chain history (at least 42 daily observations, covering a 14day calibration window plus 14-day option horizon) for the backtest; of these 98, a subset of 90 additionally pass the stricter data-quality screens required for the variance elasticity test in Section 6.6. The two samples overlap but are not nested, since the variance test applies different filters (degenerate price paths, minimum rolling-window observations) than the backtest’s MAE filter. Using daily data from the 98 backtest-eligible subnets retrieved via the Taostats API (August 8, 2025 to February 23, 2026), we execute the following procedure for each subnet and each rolling start date _t_ : 

1. Estimate _σ_ ˆ _F_ from the trailing 14-day standard deviation of daily TAO reserve changes, annualized. 

2. Compute the pool invariant _kt_ = _xt · yt_ from observed reserves.

<!-- page: 22 -->

![](assets/2026-maymin-amm-token-options.pdf-0022-00.png)


<!-- Start of picture text -->
Effect of Token Emissions on Option Prices<br>No emissions<br>35<br>Low (k = k0/yr)<br>30 Medium (k = 5k 0 /yr)<br>High (k = 20k0/yr)<br>25<br>20<br>15<br>10<br>5<br>0 50 100 150 200 250 300 350<br>Maturity (days)<br>ATM Call Price (% of spot)<br><!-- End of picture text -->

Figure 6: ATM call option price (as % of spot) vs. maturity under different emission rates, expressed as multiples of the initial pool invariant per year. Higher emissions deepen the pool over time, compressing volatility and reducing option prices at longer maturities. The effect is most pronounced for shallow pools with high emission-to-liquidity ratios. Illustrative parameters: _P_ 0 = _K_ = 0 _._ 025, _k_ 0 = 5 _×_ 10<sup>5</sup> , _σF_ = 48 _._ 7. 


![](assets/2026-maymin-amm-token-options.pdf-0022-02.png)


<!-- Start of picture text -->
Liquidity Greek  = C/ k<br>0.0<br>0.2<br>0.4<br>0.6<br>0.8<br>10 6 10 7 10 8 10 9 10 10<br>Pool Depth k (log scale)<br>)<br>9<br>10<br> (×<br><!-- End of picture text -->

Figure 7: The liquidity Greek Λ = _∂C/∂k_ for an ATM call as a function of pool depth. Negative values indicate that increasing pool depth reduces option value. The sensitivity is concentrated in shallow pools and becomes negligible for _k >_ 10<sup>9</sup> . Illustrative parameters: _P_ 0 = _K_ = 0 _._ 025, _σF_ = 48 _._ 7, _T_ = 30 days.

<!-- page: 23 -->

3. Sell a 14-day ATM European call ( _K_ = _Pt_ ) at the model price under both the CEV model ( _β_ = 1 _/_ 2, _δt_ = 2ˆ _σF /_<sup>_√_</sup> _kt_ ) and Black–Scholes with matched ATM volatility ( _σ_ eff = _δtPt_<sup>_−_1</sup><sup>_/_2</sup> ). 

4. Delta-hedge daily for 14 days using each model’s delta, updating _k_ and recomputing deltas from observed reserves at each rebalance. 

5. At expiry, compute the hedged P&L: premium collected plus cumulative hedge gains minus the realized payoff max( _Pt_ +14 _− K,_ 0). 

We aggregate each subnet’s trades into a single mean absolute hedging error (MAE, as % of spot) for each model. Because the 14-day option windows overlap, per-subnet MAE estimates exhibit serial correlation; we address this by using the cross-sectional regression (one observation per subnet), which is free of this overlap bias. After filtering 16 subnets with degenerate price paths (MAE _>_ 50%, typically from near-zero reserves or extreme price dislocations), 82 subnets remain. 

Figure 8 presents the cross-sectional results. The left panel plots each subnet’s CEV hedging error against its BS hedging error, with color indicating pool depth log10( _k_ ). Points cluster tightly along the 45-degree line. The right panel quantifies the relationship between relative hedging performance and pool depth. An OLS regression of the CEV/BS error ratio on log10( _k_ ) yields 


![](assets/2026-maymin-amm-token-options.pdf-0023-05.png)


The slope is not statistically significant. This is consistent with the theory: because the normalized implied volatility smile is universal for _β_ = 1 _/_ 2 (Theorem 5), the CEV and BS ATM call prices are nearly identical at every pool depth, yielding near-identical deltas and hedging errors. The backtest confirms that for ATM options, the two models are empirically indistinguishable. The CEV correction matters most for out-of-the-money options, where the implied volatility skew generates meaningful pricing differences (Figure 3), but this effect cannot be tested without active OTM option markets on AMM tokens. 

Only 17 of 82 subnets (21%) show lower hedging error under CEV. At each rebalance, the BS hedge uses _σ_ eff = _δPt_<sup>_−_1</sup><sup>_/_2</sup> (the CEV local volatility), ensuring a fair ATM comparison but mechanically limiting scope for divergence. Both models produce modest hedging errors (median MAE _≈_ 3% of spot), confirming the diffusion approximation is reasonable for most subnets. 

The MAE _>_ 50% filter could introduce selection bias if it disproportionately removes shallow pools, where CEV–BS divergence should be largest. The 16 excluded subnets are indeed shallower on average (median log10( _k_ ) = 9 _._ 20 vs. 9 _._ 93 for the included subnets; see

<!-- page: 24 -->

Table 2 in the appendix). However, re-running the regression on all 98 subnets without any MAE filter yields a qualitatively identical result: 


![](assets/2026-maymin-amm-token-options.pdf-0024-01.png)


The slope remains negative and insignificant, confirming that the main finding—nearidentical ATM hedging performance regardless of pool depth—is robust to the inclusion of degenerate subnets (Section B). 


![](assets/2026-maymin-amm-token-options.pdf-0024-03.png)


<!-- Start of picture text -->
Hedging Error: CEV vs. BS (82 subnets) Relative Hedging Performance vs. Pool Depth<br>CEV = BS 1.10 CEV = BS<br>20 OLS: slope=-0.002<br>12 Unfiltered (N=98): slope=-0.003<br>1.08<br>15 11 1.06<br>10 1.04<br>10<br>1.02<br>9<br>1.00<br>5<br>8<br>0.98<br>7<br>0<br>0.96<br>0 5 10 15 20 7 8 9 10 11 12<br>BS Mean Abs. Hedging Error (% of spot) log10 (k) (pool depth)<br>k)<br> (<br>10<br>log<br>CEV / BS Hedging Error Ratio<br>CEV Mean Abs. Hedging Error (% of spot)<br><!-- End of picture text -->

Figure 8: Cross-sectional delta-hedged backtest of 14-day ATM calls across 82 Bittensor subnets (August 8, 2025 to February 23, 2026). Left: each subnet’s mean absolute hedging error under CEV ( _y_ -axis) vs. BS ( _x_ -axis), colored by pool depth log10( _k_ ). Points cluster tightly along the 45-degree line, confirming that the two models produce nearidentical hedging errors at the money. Right: the CEV/BS error ratio shows no significant dependence on pool depth (OLS slope = _−_ 0 _._ 002, _p_ = 0 _._ 60). Data source: Taostats API, daily pool snapshots. 

### **6.6 Variance Elasticity Test** 

The hedging backtest in Section 6.5 compares CEV and Black–Scholes at the money, where both models agree by construction. We now test a prediction that distinguishes the two models at all strikes: the CEV variance elasticity. 

Under the CEV model, the instantaneous return variance is _σ_ ret<sup>2(</sup><sup>_P_)=</sup><sup>_δ_2</sup><sup>_P_2(</sup><sup>_β−_1).</sup> Substituting _δ_ = 2 _σF /√k_ : 


![](assets/2026-maymin-amm-token-options.pdf-0024-08.png)


Taking logarithms and rearranging: 


![](assets/2026-maymin-amm-token-options.pdf-0024-10.png)


where RV<sup>�</sup> is the annualized realized variance of daily log returns in a rolling 14-day

<!-- page: 25 -->

window (the sum of squared daily log returns multiplied by 365 _/_ 14). For _β_ = 1 _/_ 2, the slope is _−_ 1; for GBM ( _β_ = 1), the slope is 0. The left-hand side of (43) controls for both pool depth _k_ and flow volatility _σ_ ˆ _F_<sup>2(the annualized sample variance of daily TAO reserve</sup> changes within the same window), isolating the pure price-variance relationship. 

We estimate (43) within each subnet that passes additional data-quality screens beyond the history requirement of Section 6.5: no degenerate price paths (price range exceeding 10<sup>4</sup> _×_ , zero price variance, or non-positive reserves), and at least 10 valid 14-day rolling-window observations after removing 3 _σ_ outliers. The 3 _σ_ filter removes rollingwindow observations whose log-adjusted realized variance lies more than three standard deviations from the subnet mean, reducing the influence of extreme jump days on the slope estimate. Of the 98 subnets with sufficient history, 90 survive these screens; the eight additional exclusions have extreme price-to-reserve ratios or insufficient intra-window variation to estimate the controlled regression reliably. The resulting 90 within-subnet slope estimates form a distribution. Figure 9 presents the results. The median slope is _−_ 0 _._ 86 (interquartile range [ _−_ 0 _._ 98 _, −_ 0 _._ 71]), with 94% of subnets showing negative slopes. We conduct two pre-specified one-sample _t_ -tests: against the GBM null (slope = 0), which rejects decisively ( _t_ = _−_ 11 _._ 3, _p <_ 10<sup>_−_4</sup> ); and against the exact CEV prediction (slope = _−_ 1; _t_ = 3 _._ 7, _p <_ 0 _._ 001). Both rejections survive Bonferroni correction for two hypotheses (adjusted _α_ = 0 _._ 025). The implied variance elasticity corresponds to ˆ _β ≈_ 0 _._ 57, modestly above the theoretical 1 _/_ 2 for constant-product AMMs. Three factors may contribute to this attenuation: (i) the discrete, jump-like nature of large staking events attenuates measured elasticity relative to the continuous-time prediction; (ii) measurement noise from overlapping 14-day rolling windows biases slope estimates toward zero; and (iii) some Bittensor pools may operate with effective weights slightly above 1 _/_ 2 due to the recent introduction of concentrated liquidity features. Disentangling these factors requires per-subnet estimation of effective pool weights, which we leave for future work. 

The key finding is that the data strongly favor the CEV structure over GBM: the variance-price elasticity is robustly negative across subnets, as predicted by _β <_ 1, and the magnitude is close to the _−_ 1 predicted by _β_ = 1 _/_ 2.

<!-- page: 26 -->

![](assets/2026-maymin-amm-token-options.pdf-0026-00.png)


<!-- Start of picture text -->
Subnet 52 (representative)<br>7.5<br>CEV ( =1/2):  1<br>1.75 Median: -0.86<br>GBM: 0<br>1.50 7.0<br>1.25<br>6.5<br>1.00<br>0.75 6.0<br>0.50<br>5.5<br>0.25 OLS: slope = 0.63, R 2 = 0.08<br>CEV: slope = 1<br>GBM: slope = 0<br>0.00<br>2 1 0 1 2 3 5.0 4.9 4.8 4.7 4.6<br>Slope of log(RV k / 2F ) on log P log P<br>2)F<br>k /<br>Density<br>log(RV<br><!-- End of picture text -->

Figure 9: Cross-sectional test of the CEV variance elasticity. Left: distribution of withinˆ subnet slopes of log(RV<sup>�</sup> _· k/σF_<sup>2) on log</sup><sup>_P_across 90 Bittensor subnets.The median slope is</sup> _−_ 0 _._ 86, close to the CEV prediction of _−_ 1 (dashed red) and far from the GBM prediction of 0 (dotted gray). Right: scatter plot for a representative subnet (SN52), illustrating the negative relationship between the controlled realized variance measure and price. Data source: Taostats API, August 8, 2025 to February 23, 2026. 

## **7 Discussion** 

### **7.1 Limitations** 

First, most AMMs charge a swap fee (e.g., 0.3% on Uniswap). Fees modify the effective invariant: a trade of ∆ _x_ yields ∆ _y_ = _y_ (1 _− ϕ_ )∆ _x/_ ( _x_ + (1 _− ϕ_ )∆ _x_ ), where _ϕ_ is the fee rate. This introduces a bid-ask spread but does not alter the qualitative CEV structure; the main effect is to reduce the effective _σF_ by a factor of (1 _− ϕ_ ) in the diffusion limit. Bittensor’s dTAO pools currently charge no explicit swap fee, making our zero-fee model directly applicable. 

Second, the diffusion assumption for staking flows is an approximation. In practice, large staking events (“whale” transactions) can produce jump-like price movements. Across the 98 subnets in our sample, we identify jump days as those where the absolute daily TAO reserve change exceeds 3ˆ _σF_ of the trailing 14-day window. Such events occur on approximately 7.7% of trading days (1,394 of 18,130 total subnet-days), but account for a median of 47% of the total realized variance of reserve flows across subnets (interquartile range 31–65%). Despite their outsized variance contribution, the cross-sectional hedging errors (Figure 8) remain modest (median MAE _≈_ 3% of spot), suggesting that most jumps are small relative to the cumulative diffusive variation over a 14-day hedging horizon. A Merton-type jump-diffusion extension [Merton, 1976] would augment the flow process with a compound Poisson component _Jt_ d _Nt_ , leading to a jump-diffusion CEV model whose option pricing formula involves a weighted sum of CEV prices across pos-

<!-- page: 27 -->

sible jump scenarios. For subnets with frequent large staking events, such an extension may yield tighter hedging bounds, particularly for short-dated options where a single jump can dominate the realized path. 

Third, the risk-neutral pricing argument requires the ability to delta-hedge, which is imperfect due to AMM slippage. Our replication premium (Theorem 9) provides a bound on this friction, but a more rigorous treatment would employ the utility-based framework of Davis et al. [1993] for markets with transaction costs. 

Fourth, the model treats flow volatility _σF_ as constant. In practice, staking activity exhibits time-of-day effects, momentum, and regime changes. A stochastic volatility extension that layers Heston-type dynamics [Heston, 1993] onto the flow process would capture these features at the cost of analytical tractability. 

Fifth, staking flows may respond to the TAO/USD exchange rate, since TAO trades on centralized exchanges. For TAO-denominated derivatives, the CEV dynamics describe the alpha/TAO price conditional on a given flow process, so the framework remains valid. For USD-denominated derivatives, one would need to jointly model the TAO/USD price and the flow process, likely introducing stochastic correlation. 

Sixth, AMM token prices are vulnerable to manipulation near option expiry. The cost of moving the price by a fraction _ϵ_ is approximately _ϵ · x_ (the TAO reserve), which for shallow pools may be small relative to the option payoff gained. Practical implementations should incorporate safeguards such as time-weighted average prices (TWAPs) for settlement or oracle-based price feeds aggregated over multiple blocks. 

### **7.2 Extensions** 

_Concentrated liquidity._ Uniswap V3 restricts the constant-product invariant to a bounded price range [ _Pa, Pb_ ]. Within this range, local dynamics are equivalent to a constantproduct AMM with effective invariant _k_ eff, so our CEV result applies locally; the framework of Cartea et al. [2024] provides a natural starting point for this extension. At the range boundaries, the position becomes single-sided, which could be modeled as an absorbing or reflecting barrier. _Cross-subnet options._ Correlating the Brownian motions across subnet staking flows enables pricing of basket or spread options on multiple alpha tokens. _American and perpetual options._ American options can be priced via the freeboundary CEV formulation [Detemple and Tian, 2002]; perpetual options [Dave, 2023] fit naturally through the stationary solution of the pricing PDE. 

### **7.3 Practical Implications** 

The central practical implication is that Black–Scholes _underprices_ downside protection on AMM tokens at every pool depth. The leverage effect (Remark 2) elevates implied

<!-- page: 28 -->

volatility for OTM puts: as the token price falls toward the strike, the bonding curve amplifies volatility, making further declines more likely than the lognormal model predicts. Because the normalized skew depends on _β_ rather than _k_ (Figure 4), this is a structural feature, not a small-pool artifact. Conversely, Black–Scholes overprices OTM calls. 

As a concrete example, consider 90-day 20%-out-of-the-money puts on three representative Bittensor subnets (Table 1). The CEV model prices these puts 10–28% higher than Black–Scholes (with matched ATM volatility): 12.1% vs. 11.1% of spot for the shallow pool, 0.52% vs. 0.41% for the medium pool, and 0.43% vs. 0.34% for the deep pool. A subnet treasury holding 100,000 TAO worth of alpha tokens and seeking downside protection would pay 95–1,070 TAO more under the CEV model than Black–Scholes suggests, depending on pool depth. A market maker using Black–Scholes to sell these puts would systematically underprice the risk. 

## **8 Conclusion** 

We have shown that the price of a token traded on a constant-weighted-product automated market maker follows a constant elasticity of variance process, with the CEV exponent equal to the numeraire weight. This result is derived from first principles: given a diffusion model for staking flows, the AMM’s bonding curve mechanics fully determine the price dynamics, with the CEV exponent pinned by pool design rather than estimated from data. The Black–Scholes model emerges as the limiting case of infinite pool depth, providing a precise characterization of when standard pricing tools are adequate and when they are not. 

The framework yields closed-form European option prices via the non-central chisquared distribution, AMM-specific liquidity and emission Greeks, and a quantitative decomposition of the pricing discrepancy relative to Black–Scholes as a function of pool depth and moneyness. The CEV structure also provides a first-principles derivation of the leverage effect for AMM tokens: the negative correlation between price and volatility arises directly from the bonding curve, making it a structural prediction rather than an empirical regularity. 

A cross-sectional variance elasticity test across 90 subnets provides direct evidence for the CEV structure: after controlling for pool depth and flow volatility, realized return variance scales as _P_<sup>_−_0</sup><sup>_._86</sup> , strongly rejecting the GBM null of _P_<sup>0</sup> ( _p <_ 10<sup>_−_4</sup> ) and broadly consistent with the _P_<sup>_−_1</sup> predicted by _β_ = 1 _/_ 2. A complementary delta-hedged backtest of ATM calls across 82 subnets confirms near-identical hedging errors at the money ( _p_ = 0 _._ 60), consistent with the prediction that the CEV and Black–Scholes pricing discrepancy is concentrated in the wings. The backtest validates the diffusion approximation for most subnets (median hedging error _≈_ 3% of spot), and the variance elasticity test validates the CEV price-volatility relationship that drives the skew.

<!-- page: 29 -->

AMM-native tokens are proliferating across decentralized protocols, creating demand for derivative pricing tools tailored to these instruments. The CEV framework developed here provides a foundation for pricing, hedging, and risk management that respects the structural constraints of the underlying market mechanism. 

**Disclosure.** The author has no financial interest in Bittensor, TAO tokens, or any DeFi protocol discussed herein. Data were obtained from publicly available on-chain sources via the Taostats API. The author declares no conflicts of interest. 

## **References** 

- Hayden Adams, Noah Zinsmeister, Moody Salem, River Keefer, and Dan Robinson. Uniswap v3 core. _Uniswap Labs Technical Report_ , 2021. 

- Guillermo Angeris, Hsien-Tang Kao, Rei Chiang, Charlie Noyes, and Tarun Chitra. An analysis of Uniswap markets. _Cryptoeconomic Systems_ , 1(1), 2021. 

- Guillermo Angeris, Akshay Agrawal, Alex Evans, Tarun Chitra, and Stephen Boyd. Optimal routing for constant function market makers. In _Proceedings of the 2022 ACM CCS Workshop on Decentralized Finance and Security (DeFi)_ , New York, NY, 2022. 

- Stan Beckers. The constant elasticity of variance model and its implications for option pricing. _Journal of Finance_ , 35(3):661–673, 1980. 

- Maxim Bichuch and Zachary Feinstein. A derivative pricing perspective on liquidity tokens in constant product market makers. _arXiv preprint arXiv:2409.11339_ , 2024. 

- Bittensor Foundation. Dynamic TAO whitepaper. `https://bittensor.com/ dtao-whitepaper` , 2025. Accessed February 2026. 

- Fischer Black and Myron Scholes. The pricing of options and corporate liabilities. _Journal of Political Economy_ , 81(3):637–654, 1973. 

- 

- Block Scholes and Panoptic. Perpetual options a research report. Block Scholes Research, 2025. Published August 2025. 

- Vitalik Buterin. On path independence. Blog post, 2017. `https://vitalik.ca/ general/2017/06/22/marketmakers.html` . 

- Álvaro Cartea, Fayçal Drissi, and Marcello Monga. Decentralised finance and automated market making: Predictable loss and optimal liquidity provision. _SIAM Journal on Financial Mathematics_ , 15(3):931–961, 2024.

<!-- page: 30 -->

Joseph Clark. Replicating market makers. arXiv preprint arXiv:2103.14769, 2021. 

- John C. Cox. Notes on option pricing I: Constant elasticity of variance diffusions. _Working Paper, Stanford University_ , 1975. Reprinted in Journal of Portfolio Management, 1996. 

- John C. Cox and Stephen A. Ross. The constant elasticity of variance option pricing model. _Journal of Portfolio Management_ , 22:15–17, 1996. Special Issue. 

- Sachin Dave. Perpetual options in decentralized finance. Panoptic Research Report, 2023. 

- Mark H. A. Davis, Vassilios G. Panas, and Thaleia Zariphopoulou. European option pricing with transaction costs. _SIAM Journal on Control and Optimization_ , 31(2): 470–493, 1993. 

- Dmitry Davydov and Vadim Linetsky. Pricing options on scalar diffusions: An eigenfunction expansion approach. _Operations Research_ , 51(2):185–209, 2003. 

- Jérôme Detemple and Weidong Tian. The valuation of American options for a class of diffusion processes. _Management Science_ , 48(7):917–937, 2002. 

- David C. Emanuel and James D. MacBeth. Further results on the constant elasticity of variance call option pricing model. _Journal of Financial and Quantitative Analysis_ , 17 (4):533–554, 1982. 

- Masaaki Fukasawa, Basile Maire, and Marcus Wunsch. Weighted variance swaps hedge against impermanent loss. _Quantitative Finance_ , 23(6):901–911, 2023. 

- Florence Guillaume and Dennis Schroers. A unified approach for hedging impermanent loss of liquidity provision. arXiv preprint arXiv:2407.05146, 2024. 

- Joel Hasbrouck, Thomas J. Rivera, and Fahad Saleh. An economic model of a decentralized exchange with concentrated liquidity. _Management Science_ , 2024. DOI: 10.1287/mnsc.2024.04510. 

- Steven L. Heston. A closed-form solution for options with stochastic volatility with applications to bond and currency options. _Review of Financial Studies_ , 6(2):327–343, 1993. 

- Sébastien Hitier. The dynamics of constant product market makers: A geometric Brownian motion approach. SSRN Working Paper 5404433, 2025. 

- Manuela Larguinho, José Carlos Dias, and Carlos A. Braumann. A note on the computation of the CEV option pricing formula. _Quantitative Finance_ , 13(6):877–886, 2013.

<!-- page: 31 -->

- Stefan Loesch, Nate Hindman, Mark B. Richardson, and Nicholas Welber. Impermanent loss in Uniswap v3. _arXiv preprint arXiv:2111.09192_ , 2021. 

- Fernando Martinelli and Nikolai Mushegian. A non-custodial portfolio manager, liquidity provider, and price sensor. _Balancer Labs Technical Report_ , 2019. 

- Robert C. Merton. Option pricing when underlying stock returns are discontinuous. _Journal of Financial Economics_ , 3(1–2):125–144, 1976. 

- Jason Milionis, Ciamac C. Moallemi, Tim Roughgarden, and Anthony Lee Zhang. Automated market making and loss-versus-rebalancing. _arXiv preprint arXiv:2208.06046_ , 2022. Conference version in ACM DeFi’22. 

- Andreas Park. The conceptual flaws of decentralized automated market making. _Management Science_ , 69(11):6731–6751, 2023. 

- Tim Roughgarden. Transaction fee mechanism design in a post-MEV world. _ACM SIGecom Exchanges_ , 21(1):2–18, 2024. 

- Mark Schroder. Computing the constant elasticity of variance option pricing formula. _Journal of Finance_ , 44(1):211–219, 1989. 

- Fateh Singh. Option contracts in the DeFi ecosystem: Opportunities, solutions, and technical challenges. _International Journal of Network Management_ , 35(2):e70005, 2025. 

- The AMM Book. Using Black–Scholes to estimate the size of divergence loss for AMMs. Blog post, The AMM Book, 2022. `https://theammbook.org` .

<!-- page: 32 -->

## **A Proofs** 

### **A.1 Proof of Theorem 8** 

Write the CEV call price (22) as _C_ ( _β_ ), treating _δ_ as a function of _β_ through the constraint _σ_ eff = _δP_<sup>_β−_1</sup> = const. Then _C_ (1) = _C_ BS( _σ_ eff). 

The parameters _a_ , _b_ , _c_ depend on _β_ through the exponents 2(1 _− β_ ) and _b_ = 1 _/_ (1 _− β_ ). As _β →_ 1, _b →∞_ and the non-central chi-squared distribution converges to a normal. The convergence rate is _O_ (1 _/b_ ) = _O_ (1 _− β_ ), yielding _C_ ( _β_ ) _− C_ (1) = _O_ (1 _− β_ ) = _O_ ( _δ_<sup>2</sup> ), since _δ ∝_ (1 _− β_ )<sup>1</sup><sup>_/_2</sup> when _σ_ eff is held fixed. 

To determine the sign at the money, note that the CEV model’s conditional variance E[ _PT_<sup>2</sup><sup>_|P_0]</sup><sup>_−_(E[</sup><sup>_PT|P_0])2exceedstheGBMvariance(byJensen’sinequalityappliedtothe</sup> convex function _P �→ P_<sup>2(</sup><sup>_β−_1)</sup> when _β <_ 1). Since call prices are increasing in variance, _C_ CEV _≥ C_ BS( _σ_ eff) at the money, with equality only when _β_ = 1. For OTM calls, the sign reverses due to the skew: the CEV model assigns less probability mass to large upward moves, so _C_ CEV _< C_ BS for sufficiently high strikes. This is consistent with the negative implied volatility skew (Theorem 5). 

### **A.2 Proof of Theorem 9** 

The hedging error over [ _t, t_ + ∆ _t_ ] from trading ∆CEV _·_ ∆ _P_ units through the AMM with price impact (35) is 


![](assets/2026-maymin-amm-token-options.pdf-0032-07.png)


using (∆ _P_ )<sup>2</sup> _≈ δ_<sup>2</sup> _P_<sup>2</sup><sup>_β_</sup> ∆ _t_ . Integrating and taking expectations under Q gives (37). 

### **A.3 Proof of Theorem 10** 

For time-dependent _δ_ ( _t_ ), the CEV transition density depends on the total integrated ¯ _T_ variance _v_<sup>2</sup> = <u>�0</u><sup>_δ_(</sup><sup>_t_)2d</sup><sup>_t_whenthetime-changetechniqueisapplied.Substituting</sup><sup>_δ_(</sup><sup>_t_) =</sup> 2 _σF /_ ~~�~~ _k_ 0 + _kt_<sup><u>˙</u></sup> and evaluating the integral yields (41). 

## **B Robustness of the MAE Filter** 

The cross-sectional backtest in Section 6.5 excludes 16 subnets with mean absolute hedging error exceeding 50% of spot. Because this filter could introduce selection bias— particularly if shallow pools are disproportionately excluded—we report the characteristics of the dropped subnets and a robustness check without any post-hoc filtering.

<!-- page: 33 -->

Table 2 lists the 16 excluded subnets. All have extremely high MAE values (typically 1,000–20,000% of spot), indicating degenerate price dynamics—most commonly a nearcollapse to zero reserves followed by recovery, or an extreme price dislocation early in the sample. The excluded subnets are systematically shallower than the included ones: their median pool depth is log10( _k_ ) = 9 _._ 20, compared with 9 _._ 93 for the 82 included subnets. This is expected, since shallow pools are more susceptible to the reserve depletions and extreme dislocations that generate degenerate hedging outcomes. 

Re-running the OLS regression of the CEV/BS hedging error ratio on log10( _k_ ) using all 98 subnets (without the MAE filter) yields: 


![](assets/2026-maymin-amm-token-options.pdf-0033-02.png)


The slope remains negative and statistically insignificant, confirming that the main finding—near-identical ATM hedging performance regardless of pool depth—is not an artifact of the sample restriction. 

Table 2: Characteristics of the 16 subnets excluded by the MAE _>_ 50% filter. All exhibit extremely high hedging errors indicative of degenerate price paths. The excluded subnets are systematically shallower than the 82 included subnets (median log10( _k_ ) = 9 _._ 20 vs. 9 _._ 93). 

|Subnet|log10(_k_)|CEV MAE (%)|BS MAE (%)|CEV/BS Ratio|
|---|---|---|---|---|
|86|8.89|3,757|3,684|1.020|
|126|8.98|7,456|7,145|1.044|
|109|8.99|2,336|2,299|1.016|
|108|9.01|1,019|993|1.026|
|94|9.06|2,214|2,174|1.018|
|49|9.07|3,957|3,796|1.042|
|113|9.09|1,779|1,713|1.038|
|99|9.19|2,342|2,321|1.009|
|87|9.21|20,072|19,490|1.030|
|114|9.23|2,081|2,050|1.015|
|107|9.31|2,647|2,602|1.017|
|80|9.37|5,620|5,439|1.033|
|47|9.72|4,213|4,111|1.025|
|38|9.75|4,363|4,299|1.015|
|76|9.76|433,198|433,194|1.000|
|15|9.82|4,228|4,193|1.008|
