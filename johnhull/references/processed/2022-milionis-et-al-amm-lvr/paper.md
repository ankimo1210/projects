---
paper_id: "2022-milionis-et-al-amm-lvr"
title: "Automated Market Making and Loss-Versus-Rebalancing"
authors: "Jason Milionis et al."
year: "2022"
source_url: "https://arxiv.org/abs/2208.06046"
source_pdf: "references/papers/2022-milionis-et-al-amm-lvr.pdf"
source_sha256: "90c57c7785b696964ecaff0d0720cea79294713218c13e3f2b2b3cbad5295636"
converter: "PyMuPDF4LLM 1.28.0"
---

<!-- page: 1 -->

# **Automated Market Making and Loss-Versus-Rebalancing**<sup>∗</sup> 

Jason Milionis Department of Computer Science Columbia University `jm@cs.columbia.edu` 

Ciamac C. Moallemi Graduate School of Business Columbia University `ciamac@gsb.columbia.edu` 

Tim Roughgarden Department of Computer Science Columbia University a16z Crypto `tim.roughgarden@gmail.com` 

Anthony Lee Zhang Booth School of Business University of Chicago `anthony.zhang@chicagobooth.edu` 

Initial version: July 31, 2022 Current version: May 27, 2024 

##### **Abstract** 

We consider the market microstructure of automated market makers (AMMs) from the perspective of liquidity providers (LPs). Our central contribution is a “Black-Scholes formula for AMMs”. We identify the main adverse selection cost incurred by LPs, which we call “loss-versusrebalancing” (LVR, pronounced “lever”). LVR captures costs incurred by AMM LPs due to stale prices that are picked off by better informed arbitrageurs. We derive closed-form expressions for LVR applicable to all automated market makers. Our model is quantitatively realistic, matching actual LP returns empirically, and shows how CFMM protocols can be redesigned to reduce or eliminate LVR. 

## **1. Introduction** 

In recent years, automated market makers (AMMs) have emerged as the dominant mechanism for decentralized exchange on blockchains. Most (but not all) of the deployed AMMs have the form of a constant function market maker (CFMM) such as Uniswap [Adams et al., 2020, 2021]. Compared to electronic limit order books (LOBs), which are the dominant market structure for 

> ∗The second author thanks Richard Dewey, Craig Newbold, Guillermo Angeris, Tarun Chitra, and Alex Evans for helpful conversations on automated market making. We are also grateful to Austin Adams, Jun Aoyagi, Eric Budish, Larry Glosten, Gur Huberman, Mingxuan He, Thomas Rivera, Xin Wan, and Tianyi Zhang for helpful comments. The second author was supported by the Briger Family Digital Finance Lab at Columbia Business School and is an advisor to fintech companies. The third author is Head of Research at a16z Crypto, a venture capital firm with investments in automated market making protocols. The first author was supported in part by NSF award CNS2212745, and in part by an unrestricted gift from Gnosis, Ltd. The third author was supported in part by NSF awards CCF-2006737 and CNS-2212745.

<!-- page: 2 -->

traditional, centralized exchange-based electronic markets, CFMMs offer some advantages. First of all, they are efficient computationally. They have minimal storage needs, and matching computations can be done quickly, typically via constant-time closed-form algebraic computations. In an LOB, on the other hand, matching engine calculations may involve complex data structures and computations that scale with the number of orders. Thus, CFMMs are uniquely suited to the severely computation- and storage-constrained environment of the blockchain. Second, LOBs are not well-suited to a “long-tail” of illiquid assets. This is because they require the participation of active market makers. In contrast, AMMs mainly rely on passive liquidity providers (LPs). 

The goal of this paper is to understand the returns to providing liquidity in an AMM, in a manner which is inspired by the Black and Scholes [1973] model of option pricing. The Black-Scholes model builds on the insight that options can be replicated by dynamically trading the underlying stock. From this insight, the model can be used to analyze option returns both qualitatively and quantitatively. Qualitatively, the Black-Scholes model shows how option returns are related to the underlying stock’s return, volatility, and other parameters. Quantitatively, the model is realistic enough that it can be used to price options, by plugging in values for model parameters. 

Analogous to the Black-Scholes approach, we aim to construct a model of AMM LP returns, which both delivers qualitative insights about the factors that affect LP profitability, and is quantitatively realistic enough to bring to data. We begin with the idea of replicating the AMM’s trades by dynamically trading the underlying asset at market prices; we call this trading scheme the _rebalancing strategy_ . The AMM LP position systematically underperforms relative to the rebalancing strategy; we call the performance gap _loss-versus-rebalancing_ , (or LVR, pronounced “lever”). The source of underperformance is _price slippage_ : due to the passive nature of AMM liquidity provision, whenever risky asset prices move, AMMs trade at worse-than-market prices. The concept of lossversus-rebalancing, as we present it hereby, applies for _any AMM_ with mild regularity assumptions. Therefore, LVR does not only refer to and is not a quantity specific to CFMMs; LVR characterizes the behavior of general AMMs. We derive a simple expression for LVR on locally-smooth AMMs (of which CFMMs is only a special case), which depends only on two parameters: the volatility of the underlying asset, and the _marginal liquidity_ of the AMM’s demand curve. We then use our model to empirically analyze the Uniswap v2 WETH-USDC pair. Our model quantitatively performs well in matching LP returns. Our results have implications for measuring the returns to providing

<!-- page: 3 -->

liquidity for AMMs, as well as for redesigning AMMs to limit LVR and thus decrease the effective trading fees charged to AMM traders. 

We model trading between a risky asset and a numéraire. The two assets can be traded on an AMM and a centralized exchange (CEX). We assume the CEX is infinitely deep, so the risky asset can be traded on the CEX with no price impact. As in the Black-Scholes model, we assume the risky asset’s price follows a geometric Brownian motion with possibly stochastic volatility. There are two kinds of traders in the model. Noise traders trade with the AMM, contributing fees to AMM LPs. Arbitrageurs trade with the AMM and the CEX to maximize profits. We assume arbitrageurs pay no fees, implying that arbitrageurs ensure that the AMM’s price is always equal to the CEX price. In the case that the AMM is a CFMM, the CFMM is described by an invariant curve _f_ ( _x, y_ ) = _L_ ; the CFMM is willing to make any trade such that it stays on this level curve. 

We define the _rebalancing strategy_ as a trading strategy which holds whatever amount of the risky asset the AMM holds at any point in time, but adjusts its positions in the risky asset by trading at CEX prices, rather than AMM prices. Shorting the rebalancing strategy effectively _delta-hedges_ the AMM LP position. We show that, ignoring fees, AMM LPs always do worse than the rebalancing strategy. We define loss-versus-rebalancing, or LVR, as the gap between the rebalancing strategy’s performance, and the AMM LP’s performance. The intuition for this underperformance is related to the phenomenon of “sniping” in high-frequency trading settings. In the model of Budish et al. [2015], a market maker quotes prices to trade a risky asset. Whenever public information arrives causing the fair price of the risky asset to move, there is a “speed race” between the quoting market maker to cancel her order, and other traders to “snipe” the market maker’s stale quotes. 

AMMs can be thought of as quoting market makers who do not proactively update their price quotes; they only ever change prices in response to trades. Thus, whenever CEX prices move, AMM quotes become “stale”, giving arbitrageurs opportunities to profit by “sniping” the AMM, until the point where AMM prices are equal to CEX prices. AMMs thus lose money from _price slippage_ : every trade which the AMM makes is executed at slightly worse prices than the rebalancing strategy, which buys and sells at CEX prices. LVR consists of the aggregate losses incurred from such price slippage. 

Instantaneous LVR depends on only two parameters on locally-smooth AMMs: the instantaneous

<!-- page: 4 -->

variance of asset prices, and the marginal liquidity available — the slope of the AMM’s demand function for the risky asset — at the current price level in the pool. That is, AMM losses from price slippage are greater when prices move more, and when the AMM trades more aggressively in response to price movements. Asset price volatility is straightforward to measure, and marginal liquidity can be calculated based on the formula for the AMM’s demand curve (in the special subcase of CFMMs, this comes from the CFMM’s level sets), implying that our model can be used to measure LVR for any asset pair and AMM empirically. 

The Black-Scholes model also implies that options can be delta-hedged by trading the underlying stock; a delta-hedged call option is a pure bet on whether the volatility implied by option prices is greater than realized volatility. Analogously, the concept of LVR can be used the basis of a trading strategy involving delta-hedging LP positions. A portfolio which holds a long position in the AMM LP, and a short position in the rebalancing strategy, is always hedged to first-order at any point against directional movements in the risky asset’s prices. At any point in time, the position is thus a bet on whether accrued trading fees are large enough to compensate for LVR losses due to price slippage; the strategy profits if fees are large relative to the product of price volatility and marginal liquidity, and loses money otherwise. 

We use our model to empirically analyze the Uniswap v2 ETH-USDC trading pair. The analysis has two goals. First, we show that our model-predicted LVR is very close to the returns from _deltahedged LPing_ — a trading strategy which holds a long position in the CFMM LP, and a short position in the rebalancing strategy. Second, our analysis shows how “hedged LP” methodology can be used to improve the measurement of LP returns. Hedged LPing is much less risky than unhedged LPing: hedged LP P&L has a standard deviation of returns of around 1%–6% (depending on the hedging frequency) of the standard deviation of returns of unhedged LP P&L. This indicates that the vast majority of variation in unhedged LP returns is driven simply by the LP position’s exposure to market risk in the underlying assets, which can be easily eliminated by shorting the rebalancing strategy. Researchers analyzing the economic drivers of LP profitability should thus analyze hedged LP returns: by removing LP positions’ mechanical exposures to market risk, this methodology allows the researcher to focuses on the economic tradeoff of whether fees, pool token incentives, and other such benefits to LPs are large enough to outweigh losses from price slippage. Our procedure requires very little data to apply: the researcher simply needs a time series of the

<!-- page: 5 -->

asset holdings of the CFMM LP, as well as any mints and burns, and a time series of CEX prices of the risky asset. 

Next, we discuss connections between AMM LP positions and the three classical ways that volatility can be traded: static (European) options, dynamic trading strategies, and variance swaps [Carr and Madan, 2001]. We model the AMM reserves at the static payoff of a pool value function. This relates to Clark [2020], Fukasawa et al. [2022], and Deng et al. [2023], who show that AMM LP payoffs, over any finite time horizon, can be replicated by shorting a bundle of European options. These option positions, in turn, are equivalent to dynamic trading strategies which sells (buys) the asset when prices increase (decrease). In our setting, the rebalancing strategy plays the role of delta-hedging. Finally, an delta-hedged LP position can be thought of as a generalized variance swap, whose payoff over any given time period is equal to realized variance weighted by the marginal liquidity of the AMMs. 

A common benchmark used by practitioners to measure AMM LP losses is “impermanent loss”. Impermanent loss compares the performance of a AMM LP position to a portfolio which simply holds the LP’s initial bundle of assets; this differs from LVR, which compares LP performance to the rebalancing strategy. On the one hand, we show that the risk-neutral expectation of LVR and impermanent loss — and in fact with any other benchmark strategy which trades at market prices — is the same. On the other hand, LVR is the unique choice of benchmark which eliminates differences attributable to market risk. Mathematically, the loss of an AMM LP position relative to any other benchmark can be thought of as LVR, plus a noise term due to difference between the market risk exposures of the benchmark and the AMM LP. 

Our results have implications for AMM design. LVR can be used by AMM protocol designers for guidance to set fees. This is because in a competitive market for liquidity provision, there should be no excess profits for LPs, and hence fees should balance with LVR. For example, since LVR scales with variance, one might imagine fee mechanisms that also scale with variance. Or, alternatively, protocols could be constructed that compare LVR versus fee income in a backward looking window, increasing fees if they are below LVR, and decreasing fees if they are above LVR. More speculatively, our results suggest a potential approach to redesign AMMs to reduce or eliminate LVR: an AMM which has access to a reliable and high-frequency price oracle could in principle quote prices arbitrarily close to market prices for the risky asset, thus eliminating losses from price slippage,

<!-- page: 6 -->

and achieving payoffs arbitrarily close to that of the rebalancing strategy. Relatedly, AMMs could sell special rights to arbitrage LPs to special wallets, “capturing” expected LVR and redistributing the profits to AMM LPs. 

**Related literature.** We make a number of contributions relative to the literature. Theoretically, we are the first to propose, for CFMMs with general bonding functions, that LP positions’ losses should be measured relative to the rebalancing strategy. Our analysis shows that the losses of AMM LPs can be thought of as arising from _price slippage_ , due to systematically trading at worse-than-market prices. Quantitatively, our model shows how LVR can be calculated based on price volatility and bonding function curvature. The fact that LP losses are qualitatively related to these quantities is known in the literature,<sup>1</sup> but our quantification for general bonding functions is, to our knowledge, new.<sup>2</sup> Finally, our novel “delta-hedging” methodology for LVR measurement may also be useful for future empirical work on CFMM LP profitability. 

Since we introduced the concept, LVR has evolved into a centerpiece in practical applications and analyses, having had wide impact within decentralized finance. LVR and markouts have been used in practice to measure hedged LP returns of AMM pools, including those of concentrated liquidity market makers [Elsts, 2023, CrocSwap, 2022], and A number of industry groups are also working to build AMMs which utilize our insights to attempt to reduce or eliminate LVR [Canidio and Fritsch, 2023, Cata Labs, 2023, Fenbushi Capital, 2023, Algebra Protocol, 2023, Klages-Mundt and Schuldenzucker, 2022, Aori Protocol, 2023, Adams et al., 2024]. 

Our paper relates to a sizable recent literature on automated market makers. Lehar and Parlour [2021] compare liquidity provision in limit order books and AMMs. In their model, as in ours, liquidity providers make profits from liquidity traders, and lose when risky asset prices move and arbitrageurs “snipe” stale CFMM quotes. Lehar and Parlour [2021] show theoretically and empirically that equilibrium pool size is smaller when asset volatility is higher, and characterize a number of other stylized facts of Uniswap liquidity pools. In a similar setting, Capponi and Jia [2021] also show that CFMM LPs suffer losses when risky asset prices move, analyzing both 

> 1See, for example, Evans [2020], Lehar and Parlour [2021], and Capponi and Jia [2021] 

> 2Outside the financial economics literature, similar results to our decomposition have been derived for specific bonding functions. For example, Boueri [2021] also derives an explicit expression for impermanent loss, in the special case of geometric mean market makers; in this specific case, the impermanent loss is isomorphic to LVR. A number of subsequent papers have built on our approach [Hasbrouck et al., 2023], some using different terminology from LVR [Cartea et al., 2022, 2023].

<!-- page: 7 -->

the “rebalancing” arbitrage we study in this paper, as well as “reversal” arbitrage from exploiting noise traders. Capponi and Jia [2021] calculate the optimal convexity of the CFMM invariant, for trading off losses from arbitrage and increased price impact from investors. Lehar and Parlour [2021] and Capponi and Jia [2021] go beyond the present paper in that they are equilibrium models for liquidity provision. The intuition that LP losses are related to the size of price movements and the curvature of bonding functions has been made in many of these papers. These existing papers use stylized two-period models which are not amenable to quantification; these papers also generally focus on _expected_ losses of CFMM LPs. Our richer continuous-time framework allows us to conceptually distinguish “market risk” from LVR; moreover, our model can be used to empirically quantify CFMM LP losses, using either our analytical formula based on price volatility and bonding function curvature, or our simpler empirical “delta-hedging” methodology. 

More broadly, Lehar et al. [2022] and Hasbrouck et al. [2022] theoretically and empirically analyze CFMM fees, and their effects on trade volume and price efficiency. Barbon and Ranaldo [2021], Foley et al. [2023], Lehar and Parlour [2021], and Han et al. [2021] empirically compare price impact, price efficiency, and net trading fees on centralized and decentralized exchanges. Other papers analyzing CFMMs include Augustin et al. [2022], Brolley and Zoican [2023], Aoyagi [2020], Aoyagi and Ito [2021], Park [2021], Fang [2022], and Hasbrouck et al. [2023]. Arbitrage profits are a form of miner extractable value (MEV). Qin et al. [2022] empirically quantifies this and other types of CFMM related MEV, including “sandwich” attacks. Sandwich attacks are also considered by Zhou et al. [2021] empirically. Our results also show how CFMM LP losses are analogous to the “quote-sniping” losses of market makers in high-frequency trading models [Budish et al., 2015, Biais et al., 2015, Baldauf and Mollner, 2020, Aquilina et al., 2022]. 

A number of papers outside the financial economics literature apply tools from convex analysis to analyze CFMMs. Angeris et al. [2019] show analytically and through agent-based simulations that CPMMs are able to closely track the reference prices of underlying assets. In a manner related to this paper, Angeris and Chitra [2020] and Angeris et al. [2021a,b] apply tools from convex analysis (e.g., the pool reserve value function) to study the more general case of constant function market makers. Angeris et al. [2021b] also analyze LP profits, but do not relate them to the rebalancing strategy or express them in closed-form. Relative to these earlier papers, our contribution is to explicitly decompose LP losses into the returns on the rebalancing strategy and LVR for general

<!-- page: 8 -->

CFMMs, to show how the LVR component corresponds to arbitrageur profits, and to show how these ideas can be used to measure LP losses empirically.<sup>3</sup> 

Another group of papers draws analogies between CFMMs and options; we discuss the relationship between our results and these papers in detail in Section 7. Clark [2020] replicates the payoff of a constant product market over a finite time horizon in terms of a static portfolio of European put and call options. Tassy and White [2020] compute the growth rate of a constant product market maker with fees. Lambert [2022] considers a number of related issues. Boueri [2021] considers the profitability of geometric mean market makers under geometric Brownian motion dynamics; his (re-)definition of “impermanent loss” in that setting is equivalent to LVR. Boueri [2021] also does not show the relationship between LVR and arbitrageur profits. Subsequent to the first publicly available version of our paper, Cartea et al. [2022] and Cartea et al. [2023] discussed the concept of “predictable loss”; the “convexity cost” component of predictable loss in their setting is equivalent to LVR. 

**Outline.** The paper proceeds as follows. Section 2 describes some institutional details of AMMs. Section 3 describes our model. Section 4 contains our main results. Section 5 shows expressions for loss-versus-rebalancing for a number of CFMM invariants used in practice. Section 6 contains our empirical analysis. Section 7 discusses the relationship of AMM LPs to options and other ways to trade volatility. Section 8 discusses the relationship between LVR and other benchmarks, such as impermanent loss. We discuss practical implications of our results for AMM design in Section 9, and conclude in Section 10. Proofs and supplementary results are contained in the appendix. 

## **2. Institutional Background** 

Automated market makers have their origin in the classic literature on prediction markets and market scoring rules; see Pennock and Sami [2007] for a survey of this area. Constant function 

> 3In particular, a number of papers have characterized _expected_ losses of CFMM LPs – sometimes referred to as expected “impermanent loss” – in more or less general cases. To our knowledge, the _<u>σ</u>_ 8<sup>2</sup> formula for the constant product market maker first appeared in Evans [2020], and has appeared in many papers since. As we discuss in Section 8, the (risk-neutral) _expectations_ of “impermanent loss” and LVR are equal, but LVR does not contain market risk; we view this as an important conceptual distinction, and it also leads to cleaner empirical measures of LP losses. Moreover, the literature applying tools from convex analysis has not emphasized that convexity losses are equivalent to arbitrageur profits; as we discuss in Section 9, this insight is key to showing how AMMs could be redesigned to reduce or eliminate LVR.

<!-- page: 9 -->

market makers, which are characterized by a invariant or bonding function, build on the utilitybased market making framework of Chen and Pennock [2007]. In that framework, utility indifference conditions define a bonding function for binary payoff Arrow-Debreu securities. More recent interest in CFMMs has been prompted by an entirely new application: its functioning as a decentralized exchange mechanism, first proposed by Buterin [2016] and Lu and Köppelmann [2017]. 

An automated market maker (AMM) is a smart contract which allows market participants to trade one cryptoasset with another directly on the blockchain, rather than using a centralized exchange. Suppose, for example, that a market participant wanted to trade an asset such as ETH held in her blockchain wallet for another asset, such as USDC. She could do so on a custodial centralized exchange (CEX), such as Binance, by “depositing” her ETH by sending it to Binance on the blockchain; trading Binance-custodied ETH for custodied USDC; and then “withdrawing” the USDC, directing Binance to send USDC back into her personal blockchain wallet. This process has a number of costs. The market participant must give the CEX custody over her cryptoassets, exposing her to exchange credit risk. Market participants must have a CEX trading account; many CEXs impose jurisdictional and identification requirements, often imposed by national regulators to satisfy know-your-customer or anti-money-laundering laws, which market participants may be unwilling or unable to satisfy. The CEX must enable trading of the asset pair in question; many tokens with small market caps are simply not listed on CEXs for trade. Moreover, the rules for determining trade priority and prices on CEXs are not always transparent, and CEXs may impose deposit, withdrawal, and settlement fees or delays on their users. 

AMMs present an alternative to CEX trading which circumvents many of these costs. Technically, AMMs are “smart contract” wallets, meaning they are blockchain wallets which can hold cryptoassets, but whose behavior is determined fully by blockchain code rather than human discretion. In this example, the AMM wallet holds some inventory of ETH and USDC. When a trader submits a blockchain transaction to trade ETH for USDC, ETH is sent from the user to the AMM’s inventory, and USDC is sent from the AMM’s inventory to a user, in a single atomic transaction. We will discuss how the trade price is determined in Section 3 below. There are no barriers to access to AMMs: any individual can initiate a transaction with any AMM. There is no credit risk, since trades are completed in a single step, and it is not possible to lose the sold assets without gaining the purchased assets. The mechanisms through which trade prices are calculated is com-

<!-- page: 10 -->

paratively transparent: for example, the Uniswap v2 smart contract consists of under a thousand lines of publicly available code.<sup>4</sup> Once “deployed” to the blockchain, no one, not even the creator, can modify the code. AMMs thus present an attractive trading option for market participants who do not want exposure to exchange credit risk, who face barriers to accessing CEXs, or who value the transparency of AMM behavior. 

The asset inventory AMMs use to trade is provided in a decentralized manner: any market participant can become a “liquidity provider” (LP) in a ETH-USDC AMM, or any other pair of tokens,<sup>5</sup> by contributing ETH and USDC to the AMM’s inventory. The AMM pool then trades using these contributed assets as a part of its inventory, and any trading fees accrue proportionately to the liquidity inventory providers depending on her share. At any point, the liquidity providers can withdraw ETH and USDC corresponding to her share of the pool; however, the amounts of ETH and USDC withdrawn will generally differ from what the liquidity provider first contributed, as inventory adjusts with market participants’ trade requests and fees are collected. The economic problem facing LPs, which is the core focus of our paper, is how to evaluate the costs and benefits of providing liquidity to AMMs. 

## **3. Model** 

In what follows, we describe the frictionless, continuous-time Black-Scholes setting of our model. 

**Assets.** Fix a filtered probability space �Ω _, F, {Ft}t≥_ 0 _,_ Q� where Q is a risk-neutral or equivalent martingale measure, satisfying the usual assumptions. Suppose there are two assets,<sup>6</sup> a risky asset _x_ and a numéraire asset _y_ . Without loss of generality, assume that the risk-free rate is zero. There is an infinitely deep centralized exchange, where the risky asset can be traded with zero fees. The price on the centralized exchange is observable, and evolves exogenously according to a geometric Brownian motion that is a continuous Q-martingale, i.e., 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0010-05.png)


> 4See the Uniswap v2 repository. 

> 5In particular, a market participant can begin LPing a pair of assets even if no one else is providing liquidity for it, thus effectively listing the pair of assets for trade. 

> 6This assumption is without loss of generality, we describe the multi-dimensional case where there are _n ≥_ 2 assets, none of which need be the numéraire, in Appendix B.3.

<!-- page: 11 -->

with a stochastic volatility process<sup>7</sup> given by _σt >_ 0, and where _Bt_<sup>QisaQ-Brownianmotion.</sup> 

**CFMM pool.** The state of a constant function market maker (CFMM) pool is characterized by the reserves ( _x, y_ ) _∈_ R<sup>2</sup> +<sup>,whichdescribethecurrentholdingsofthepoolintermsoftheriskyasset</sup> and the numéraire, respectively. Define the feasible set of reserves _C_ according to 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0011-02.png)


where _f_ : R<sup>2</sup> +<sup>_→_Risreferredtoasthe</sup><sup>_bondingfunction_or</sup><sup>_invariant_,and</sup><sup>_L ∈_Risaconstant.In</sup> other words, the feasible set is a level set of the bonding function. The pool is defined by a smart contract which allows an agent to transition the pool reserves from the current state ( _x_ 0 _, y_ 0) _∈C_ to any other point ( _x_ 1 _, y_ 1) _∈C_ in the feasible set, so long as the agent contributes the difference ( _x_ 1 _− x_ 0 _, y_ 1 _− y_ 0) into the pool; see Figure 1a. 

**Example 1.** _The constant product market maker is defined by the invariant_<sup>_√_</sup> _<u>xy</u>_ = _L._ 

To simplify our analysis, we will also assume that, aside from trading with arriving liquidity demanding agents, the pool is static otherwise. In particular, we assume that the liquidity providers do not add (“mint”) or remove (“burn”) reserves over the time scale of our analysis. In other words, LPs are _passive_ . We also ignore the details of the underlying blockchain on which the pool operates. In particular, we assume away any blockchain transaction fees such as “gas” fees, and also ignore the discrete-time nature of block updates. 

Besides liquidity providers, there are two kinds of agents in the model: arbitrageurs and noise traders. 

**Arbitrageurs.** There is a population of arbitrageurs, able to frictionlessly trade at the external market price, continuously monitoring the CFMM pool. When an arbitrageur interacts with the pool, we assume they maximize their immediate profit by exploiting any deviation from the external market price. In other words, they transfer the pool to a point in the feasible set _C_ that allows them to extract maximum value assuming that they unwind their trade at the external market price _P_ . Geometrically, the presence of arbitrageurs implies that, if the price of the risky asset is 

> 7Volatility will be an important input in the analysis that follows. A natural question is how to calibrate volatility as a model parameter. As in the general application of Black-Scholes style models, for _ex ante_ analysis of a possible future LP position, an implied volatility is the appropriate input. On the other hand, for _ex post_ LP return performance analysis as in Section 6, a historical or realized volatility is appropriate.

<!-- page: 12 -->

![](assets/2022-milionis-et-al-amm-lvr.pdf-0012-00.png)


<!-- Start of picture text -->
y y<br>f ( x, y ) =  L f ( x, y ) =  L<br>( x 0 , y 0)<br>x 1  − x 0<br>y 0  − y 1 � x ∗ ( P ) , y ∗ ( P )�<br>( x 1 , y 1) slope =  −P<br>x x<br><!-- End of picture text -->

**(a)** Transitions between any two points on the bonding curve _f_ ( _x, y_ ) = _L_ are permitted, if an agent contributes the difference into the pool. 

**(b)** Arbitrageurs ensures that, when the price is _P_ , pool reserves shift to the point on the bonding curve where the slope is equal to _−P_ . 

**Figure 1:** Illustration of a CFMM. 

_P_ , pool reserves will move to the point on the curve _f_ ( _x, y_ ) = _L_ where the slope of the bonding curve is equal to _−P_ , as indicated in Figure 1b. 

**Noise traders.** There is also a population of DEX-specific noise traders. Noise traders trade only in the CFMM pool, and trade for totally idiosyncratic reasons. In most models of equilibrium liquidity provision on decentralized exchanges, it is important that there are at least some noise traders who strictly prefer trading on CFMMs to CEXs, since these traders are the source, since the equilibrium amount of CFMM liquidity is zero in the absence of noise traders [Lehar and Parlour, 2021]. There are many reasons in practice why certain market participants might prefer trading on CFMMs to CEXs. Market participants may not be able or willing to satisfy the know-yourcustomer requirements imposed by CEXs, or may not trust that centralized exchanges will safely custody their assets. Market participants may, due to jurisdictional restrictions, not have access to a CEX on which a particular asset trades, whereas DEXes have no jurisdictional restrictions; market participants may also value the ability to atomically combine DEX trades with other smart contract operations on blockchains.<sup>8</sup> 

Noise traders’ trades have an initial impact on CFMM pool prices, but these effects are immediately offset by arbitrageurs, who immediately move the CFMM back to the CEX price _P_ . Thus, from the LP’s perspective, noise traders simply contribute a flow of fees. Denote by FEE _T_ 

> 8There could also be noise trading on the CEX; however, since we have assumed the CEX is infinitely deep, these trades do not affect prices and can be ignored in our model. If there are noise traders who can trade on either the CEX or the DEX, in our model they will choose to trade on the infinitely deep CEX. For the purposes of our model, we only need that there are some noise traders who exogenously prefer to trade on the DEX, with strong enough preferences that they are willing to use the DEX despite higher fees and price impact.

<!-- page: 13 -->

the cumulative fees paid by noise traders up to time _T_ . For simplicity, we assume fees are paid in units of the numéraire; this simplifies the analysis, since fees do not affect the level curve that the CFMM trades on.<sup>9</sup> In practice, fees are sometimes (e.g., in Uniswap v2 but not in Uniswap v3) reinvested into the pool reserves; another way to think about this assumption is to assume LPs immediately withdraw any accrued fees from the CFMM. 

When discussing arbitrageurs, we will distinguish between two conceptually different forms of arbitrage activity. The first, which we call _rebalancing arbitrage_ , is arbitrage of a pool when mispricing arises due to movements of the CEX price. The second, which we call _reversion arbitrage_ , is arbitrage following the arrival of noise traders who move DEX prices away from _P_ — this type of arbitrage is sometimes called “back-running”. Our model allows us to quantify the magnitude of profits of rebalancing arbitrageurs, but not reversion arbitrageurs. 

### **3.1. Discussion of Assumptions** 

We assume the CEX is infinitely deep, so trades have no price impact; this is analogous to the assumption in the Black-Scholes model that trades of the underlying stock have no price impact. It is not entirely clear how true this is in practice, and for which assets this is true. On the one hand, Barbon and Ranaldo [2021] and Liao and Robinson [2022] argue that transaction fees are in fact lower on DEXs than CEXs at certain transaction sizes. Moreover, since the barriers to listing tokens on DEXs are so low, many less liquid tokens begin trading on DEXs before they are traded on large CEXs. On the other hand, a large majority of trade volume in the USD-ETH pair, around 90%, occurs on centralized exchanges relative to decentralized exchanges. Moreover, according to our conversations with industry participants, large orders are in practice often executed through OTC desks, so liquidity may be deeper than what is implied by CEX limit order books; the CEX in our model can be thought of as capturing limit order books, OTC desks, and any other sources of liquidity outside the DEX, including in fact other DEXes. Our model is a reasonable approximation so long as any individual DEX does not constitute more than a small fraction of total liquidity in the market available for an asset. Even in settings where this assumption does not hold, our model may still be a useful conceptual benchmark that is cross-sectionally consistent and arbitrage-free, analogous to the use of option pricing models to value options with illiquid underlying assets, such 

> 9The same assumption is made by Lehar and Parlour [2021].

<!-- page: 14 -->

as employee stock options in privately held companies, or as in real options valuation [Dixit and Pindyck, 1994]. 

A number of other papers, such as Lehar and Parlour [2021], Capponi and Jia [2021] Hasbrouck et al. [2022], Barbon and Ranaldo [2021], and Foley et al. [2023], argue that the equilibrium level of pool liquidity – _L_ in our model – should equating LPs’ gains from trading fees to their losses from “adverse selection.” We take _L_ as given, thinking of it as determined by such an equilibrium process. We will show that LVR only depends on price volatility, and the marginal liquidity of the CFMM level set, both of which are observable objects. Thus, given price volatility, any model of liquidity providers’ strategic behavior which leads the CFMM LP to reach a given level set implies the same level of LVR. The cost of not modeling strategic LP behavior is that our framework cannot make sharp predictions about how the level of CFMM liquidity provision responds to changes in market design. However, the benefit is that our quantification of CFMM LP losses is robust to different underlying models of strategic LP behavior. 

We assume away many frictions to trading which are present in practice: we assume arbitrageurs pay no trading fees on CEXs or DEXs, we ignore gas fees, and we ignore the discrete, block-based nature of trading on blockchain CFMMs. As in Black-Scholes, these approximations allow us to derive particularly simple expressions for model outcomes. Accounting for fees will imply that the profits arbitrageurs make will tend to be lower than our expressions. In particular, in practice, arbitrageurs tend to engage in “gas races”, bidding high gas fees so that block miners have an incentive to include their arbitrage trades in the blockchain first. These gas races will tend to redirect some of the profits from CEX-DEX arbitrage towards block miners.<sup>10</sup> We will show in our empirical analysis of Section 6 that our model appears to match the actual delta-hedged returns of LP positions from the data fairly closely, suggesting that the omission of fees from our model has a quantitatively small effect on estimated LP returns in the examples we analyze. Moreover, we note that the analysis of arbitrage profits in the presence of fees is the subject of follow-on work [Milionis et al., 2023a], and we defer a more careful discussion of the impact of fees to that work. We also assume noise trader fees are paid in the numéraire, and we assume away minting and burning of LP shares for simplicity. However, we relax both these assumptions in the empirical application in 

> 10CEX-DEX arbitrage is one form of “miner extractable value”, or MEV, a set of circumstances in which miners’ ability to determine the ordering of transactions allows them to extract monetary value; Daian et al. [2020] discusses MEV in detail.

<!-- page: 15 -->

## **4. Loss-Versus-Rebalancing** 

We proceed to analyze losses of AMM LPs in the context of our model. 

**The pool value function** _V_ ( _P_ ) **.** Figure 1b shows that the composition of the CFMM’s reserve pool depends only on the risky asset’s price: at any time _t_ , if the risky asset’s price is _Pt_ , arbitrageurs will move the pool’s reserves to the point on the _f_ ( _x, y_ ) curve where the slope is _−Pt_ . The markto-market value of the pool’s reserves at any point in time, _Ptxt_ + _yt_ , is thus also fully determined by the current price _Pt_ . A convenient way to analyze the monetary value of pool reserves at any given point in time is to define the the _pool value function V_ : R+ _→_ R+, as the solution to the optimization problem: 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0015-04.png)


The intuition behind (1) is that, at any point in time, arbitrageurs can access any point on the invariant curve _f_ ( _x, y_ ) = _L_ ; arbitrageur profits are maximized by minimizing the value of the pool’s reserves. The minimizing choice of _x, y_ is the tangency point illustrated in Figure 1b; _V_ ( _P_ ) measures the monetary value of reserves, _Px_ + _y_ , at this minimal point. If we denote by _Vt_ the value of pool reserves at time _t_ , the presence of arbitrageurs implies that at any point, _Vt_ is equal to _V_ ( _Pt_ ). Geometrically, the pool value function implicitly defines a reparameterization of the pool state from primal coordinates (reserves) to dual coordinates (prices). 

We assume that the pool value function satisfies: 

**Assumption 1.** _1. An optimal solution_ � _x∗_ ( _P_ ) _, y∗_ ( _P_ )� _to the pool value optimization_ (1) _exists for every P ≥_ 0 _._ 

_2. The pool value function V_ ( _·_ ) _is everywhere twice continuously differentiable._ 

_3. For all t ≥_ 0 _,_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0015-10.png)


Parts 1–2 are easily verified for many CFMMs, see Section 5 for examples. Part 3 is a square-

<!-- page: 16 -->

integrability condition that will be used in Section 4. Parts 1–2 are a sufficient condition for the following: 

**Lemma 1.** _For all prices P ≥_ 0 _, the pool value function satisfies:_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0016-02.png)


![](assets/2022-milionis-et-al-amm-lvr.pdf-0016-03.png)


![](assets/2022-milionis-et-al-amm-lvr.pdf-0016-04.png)


**Proof** _._ The first part follows from the fact that _C ⊂_ R<sup>2</sup> +<sup>and</sup><sup>_P≥_0.The second part is the envelope</sup> theorem or Danskin’s theorem [Bertsekas, 1971]. The third part follows from the concavity of _V_ ( _·_ ), as a pointwise minimum of a collection of affine functions. ■ 

Part 2 of Lemma 1 establishes that the slope of the pool value function is equal to the reserves in the risky asset. Part 3 establishes that the pool value function is concave. Note that this concavity does not depend on the nature of the feasible set _C_ or the bonding function _f_ ( _·_ ). This part also establishes that the second derivative of the pool value function is the marginal liquidity available at the price level. 

We call _x_<sup>_∗_</sup> ( _P_ ) the demand curve of the AMM. We remark that the concavity of the pool value function along with Part 3 of Lemma 1 establish that the demand curves of all CFMMs must be non-increasing functions of the implied pool price. This fact has deep economic roots, in that it is fundamentally implied by and equivalent to Myerson’s lemma when LPs exchanging a risky asset with traders is viewed as an auction for which incentive compatibility of traders reporting their true valuations for the asset is required; this has been the subject of later investigations by Milionis et al. [2024, 2023b], and the monotonicity of demand curves holds for and forms the basis of a broader class of AMMs that are more general than CFMMs, and also include limit order books. 

**Remark 1.** _The setting we accommodate and rely on is that of a locally-smooth demand curve x_<sup>_∗_</sup> ( _P_ ) _. It is neither important nor required that this format comes from a CFMM, i.e., it is not necessary for our results and_ LVR _in particular that there is an invariant curve. So long as for some (instantaneous) interval of time, the LP is committing to a fixed demand curve according to Assumption 1, the definition and characterization of_ LVR _in Theorem 1 carries through precisely asis with no modification. For one example, this remark means that the_ LVR _calculation of Theorem 1_

<!-- page: 17 -->

_can be applied with absolutely no adjustments in general concentrated liquidity AMMs, such as Uniswap v3 (in fact, see Example 4 and Example 5, where this is analyzed). This means that the concept of loss-versus-rebalancing, as we present it hereby, applies for_ any AMM _with a locallysmooth demand curve x_<sup>_∗_</sup> ( _P_ ) _. Therefore,_ LVR _does not only refer to and is not a quantity specific to CFMMs;_ LVR _characterizes the behavior of general AMMs; also refer to Footnote 18 for how to apply this to even more general, non-locally-smooth settings._ 

Note also that the optimization problem in (1) is isomorphic to the _expenditure minimization problem_ from classical demand theory: under price _P_ , a consumer minimizes total expenditures _Px_ + _y_ , subject to staying on the indifference curve _f_ ( _x, y_ ) = _L_ . The solution to this problem is to choose the point where the level curve of _f_ ( _x, y_ ) is tangent to the budget set. The envelope theorem thus gives that the first derivative of the expenditure function is the Hicksian demand function, which is isomorphic to _x_<sup>_∗_</sup> ( _P_ ), and the second derivative of the expenditure function is the slope of Hicksian demand. 

The pool value function allows us to write the profit and loss of an CFMM, from time 0 to time _t_ , as: 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0017-03.png)


In words, LP P&L _t_ is the monetary value of the pool reserves at time _t_ , minus the value at time 0, plus the cumulative fees collected until time _t_ . 

**Rebalancing strategy** _Rt_ **.** The key idea of our paper is to decompose the change in pool value _Vt − V_ 0 into the sum of the returns on a particular trading strategy, which we call the _rebalancing strategy_ , and a residual term. Informally, the rebalancing strategy aims to hold exactly the same amount of the risky asset as the CFMM at any point in time. Whenever prices move in a way which causes the CFMM to buy or sell, the rebalancing strategy makes exactly the same buys and sells; however, the rebalancing strategy executes these trades at CEX prices, rather than CFMM prices. An alternative way to think of the rebalancing strategy is that it aims to replicate the exposure of the CFMM to the risky asset at any point in time. Thus, taking a long position in the CFMM LP, and a short position in the rebalancing strategy, _delta-hedges_ the LP position, neutralizing first-order exposure to shifts in the risky asset’s price. 

We first define general trading strategies. A trading strategy is a process ( _xt, yt_ ) defining

<!-- page: 18 -->

holdings in the risky asset and numéraire at each time _t_ . For a trading strategy to be _admissible_ , we require that it be adapted, predictable, and satisfy 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0018-01.png)


We further restrict admissible trading strategies to be _self-financing_ , i.e., to satisfy 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0018-03.png)


Equation (4) states that the change in the profit of the strategy in a small period of time is equal to the holdings of the risky asset, _xs_ , times the change in price, _dPs_ . The total P&L of the strategy is just the integral of these instantaneous changes. Intuitively, a self-financing strategy executes all rebalancing trades at market prices; hence, trades do not affect the profit of the strategy, and no money needs to be injected into the trading strategy. In the special case where _Pt_ is a martingale, so the expected profit from holding the risky asset is zero, any self-financing strategy makes zero profits in expectation, since any strategy which dynamically trades a asset with zero expected returns also has zero expected returns.<sup>11</sup> 

The self-financing condition implies that, if we specify _y_ 0, the initial amount of the numéraire, and _{xt}t≥_ 0 the amount of the risky asset that is held in any possible future history, the future path of the numéraire _{yt}_ is implicitly determined through (4). The P&L of the resulting self-financing strategy can be directly expressed in terms of _{xt}_ , via the right side of (4). Intuitively, the right side of (4) is the integrated form of the envelope formula: if the trading strategy holds a position _xt_ in the risky asset, the change in profits in an instant _dt_ is _xtdPt_ , the amount of the risky asset held times the change in price. Note that, since _Pt_ is a Q-martingale, the P&L process given by (4) is also Q-martingale, and by (3) it is square-integrable. 

We then define the rebalancing strategy to be the self-financing trading that starts initially holding � _x∗_ ( _P_ 0) _, y∗_ ( _P_ 0)� (the same position as the CFMM), and continuously and frictionlessly rebalances to maintain a position in the risky asset given by _xt_ ≜ _x_<sup>_∗_</sup> ( _Pt_ ). Let _Rt_ denote the 

> 11In the general case, the risky asset may have positive expected returns due to risk premia; self-financing strategies may thus have positive expected profits, proportional to how much portfolio weight they put on the risky asset. However, the positive expected returns of the strategy derive only from the risk premia on the underlying asset: if the strategy is delta-hedged, it makes zero expected profits.

<!-- page: 19 -->

monetary value of the rebalancing strategy at time _t_ ; that is, if the rebalancing strategy holds _xt, yt_ at time _t_ , _Rt_ is _Ptxt_ + _yt_ . Applying the self-financing condition (4) the rebalancing portfolio has value: 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0019-01.png)


Because of Assumption 1 Part 3, the rebalancing strategy is admissible and _Rt_ is a square-integrable Q-martingale. In particular, being a self-financing strategy, the rebalancing strategy breaks even in expectation under the risk-neutral measure Q; it only makes expected returns to the extent that the underlying risky asset has nonzero risk premia. 

As a matter of accounting, we then express the change in pool value from time 0 to time _t_ as the sum of the rebalancing strategy’s profits, and a residual term which we will define as _loss-versus-rebalancing_ : 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0019-04.png)


LVR _t_ can also be thought of as the losses from a delta-hedged LP position, ignoring fees. In other words, a strategy which takes a long position in the CFMM LP position, and a short position in the rebalancing strategy, pays _Vt − Rt_ at time _t_ , disregarding any fees collected. The core contribution of our paper is the characterization of LVR _t_ in the following theorem. 

**Theorem 1.** _Loss-versus-rebalancing takes the form:_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0019-07.png)


_where we define, for P ≥_ 0 _, the instantaneous_ LVR _by:_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0019-09.png)


_ℓ_ ( _σ, P_ ) _is always positive, so_ LVR _is a non-negative, non-decreasing, and predictable process. Moreover, the cumulative profits of rebalancing arbitrageurs up to time t is equal to_ LVR _t._ 

**Comparative statics.** The core intuition behind Theorem 1, which we will demonstrate below,

<!-- page: 20 -->

is that the CFMM systematically loses money relative to the rebalancing strategy due to _price slippage_ : every trade made by the CFMM is made at slightly worse prices than the rebalancing strategy. Equation (8) of Theorem 1 characterizes these losses: LVR is large when volatility _σt_ is high, so price move more; and when _|x_<sup>_∗′_</sup> ( _Pt_ ) _|_ is large, so the CFMM trades more of the risky asset when prices move a given amount. We will refer to _|x_<sup>_∗′_</sup> ( _Pt_ ) _|_ as the _marginal liquidity_ of the CFMM at price _Pt_ . In Appendix A.2, we derive an expression for _|x_<sup>_∗′_</sup> ( _P_ ) _|_ in terms of the CFMM bonding function _f_ ( _·_ ), and show that _|x_<sup>_∗′_</sup> ( _P_ ) _|_ is related to the curvature of the level sets of _f_ ( _·_ ): CFMMs with “flatter” bonding curves have higher marginal liquidity.<sup>12</sup> 

The idea that the losses of CFMM LP positions are related to volatility and curvature are not new to the financial economics literature [Aoyagi, 2020, Aoyagi and Ito, 2021, Lehar and Parlour, 2021, Capponi and Jia, 2021, O’Neill, 2022]. Our contribution is to build a model which, like the Black-Scholes model for option prices, both delivers qualitative comparative statics, and is also quantitatively realistic enough to be used to measure CFMM losses in practice. 

**Intuition: price slippage.** A rigorous proof that LVR is equal to (12), and that rebalancing arbitrage profits are equal to LVR, is contained in Appendix A. Here, we present an intuitive derivation, based on Figure 2. 

Suppose the market price changes from _Pt_ to _Pt_ + _dPt_ . Arbitrageurs thus trade with the CFMM, moving from point _A_ to point _B_ on the CFMM invariant curve. Let _dxt_ denote the amount of the risky asset sold, indicated by the green horizontal line. When the price moves from _Pt_ to _Pt_ + _dPt_ , the rebalancing strategy sells exactly the same amount, _dxt_ , of the risky asset as the CFMM does. However, the rebalancing strategy trades at the CEX price, _Pt_ + _dPt_ ; it trades along the the brown line of slope _Pt_ + _dPt_ passing through _A_ , reaching point _B_<sup>_∗_</sup> , which is higher than point _B_ . Thus, after prices move, the LP position and the rebalancing strategy hold the same amount of the risky asset, but the rebalancing strategy holds more cash. The gap is equal to the height of the line connecting _B_ and _B_<sup>_∗_</sup> . 

To calculate the height of the _B − B_<sup>_∗_</sup> line, note that the rebalancing strategy trades at the slope of the brown line, which is _Pt_ + _dPt_ . The CFMM trades at the slope of the purple line — that is, 

> 12An interesting implication of these results for the design of CFMM invariants is that, in our model, under our assumptions, the only feature of CFMMs which matters for losses is the curvature of the CFMM bonding function, which determines _x_<sup>_∗′_</sup> ( _P_ ). Any two CFMM invariants for an asset pair which have the same local convexity at any given price have the same LVR.

<!-- page: 21 -->

![](assets/2022-milionis-et-al-amm-lvr.pdf-0021-00.png)


<!-- Start of picture text -->
B ∗<br>Pt  +  dPt B dxt<br>Pt<br>A<br><!-- End of picture text -->

**Figure 2:** LVR and a stylized depiction of CFMM LP price slippage. Suppose prices begin at _Pt_ , the slope of the red line; the CFMM reserves then begin at point _A_ . If prices increase to _Pt_ + _dPt_ , the slope of the brown line, the CFMM trades to point _B_ . The rebalancing strategy trades instead at the price _Pt_ + _dPt_ , to point _B_<sup>_∗_</sup> . LVR is the vertical gap between _B_ and _B_<sup>_∗_</sup> . 

the secant line connecting points _A_ and _B_ . Since the tangency lines at points _A_ and _B_ have slopes _Pt_ and _Pt_ + _dPt_ respectively, the secant line has slope _Pt_ +<sup>_<u>dP</u>_</sup> 2<sup>_<u>t</u>_.Thus,the</sup><sup>_B −B∗_linehasheight:</sup> 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0021-03.png)


This is thus the loss of the CFMM, relative to the rebalancing strategy. This is also exactly the profit extracted by arbitrageurs when prices move: arbitrageurs purchase quantity _dxt_ from the CFMM at price _Pt_ +<sup>_<u>dP</u>_</sup> 2<sup>_<u>t</u>_,andsellingtotheCEXatprice</sup><sup>_Pt_+</sup><sup>_dPt_,thusearningaprofitof</sup><sup>_<u>dxt</u>_</sup> 2<sup>_<u>dPt</u>_</sup> . Next, we write the amount traded _dxt_ as a function of _dPt_ : 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0021-05.png)


where _x_<sup>_∗_</sup> ( _Pt_ ) is the demand function of the CFMM. Expression (9) then becomes: 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0021-07.png)

<!-- page: 22 -->

Now, for a geometric Brownian motion, in a small amount of time _dt_ , the quadratic variation ( _dPt_ )<sup>2</sup> = _d_ [ _Pt_ ] is equal to _σt_<sup>2</sup><sup>_P_</sup> _t_<sup>2</sup><sup>_dt_,thatis,theinstantaneousvariance</sup><sup>_σ_</sup> _t_<sup>2</sup><sup>_dt_multipliedbythe</sup> square of the price. Hence, plugging in to (11), in any instant of time _dt_ , the CFMM LP position loses: 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0022-01.png)


This is (8) of Theorem 1. 

Figure 2 thus illustrates that LVR — that is, the losses CFMMs incur relative to the rebalancing strategy — arises entirely from _price slippage_ . The fact that CFMMs rebalance, selling when prices rise and buying when prices fall, is not in itself the source of losses. The rebalancing strategy makes exactly the same trades of the risky asset as the CFMM LP position, but does not lose money because it executes all trades at CEX prices. For that matter, _any_ trading strategy which executes all trades at CEX prices exactly breaks even under the risk-neutral measure. LVR arises from the fact that CFMMs execute all trades at worse-than-market prices. 

Price slippage is intrinsic to the design of CFMMs. CFMMs are fully passive liquidity providers, making markets for risky assets without access to external price feeds from centralized exchanges. CFMMs rely on arbitrage to “inform” them about current market prices: whenever CEX prices move, the CFMM’s quotes become “stale”, offering to trade some quantity of the risky asset at better-than-market prices. Arbitrageurs trade the CFMM against the CEX until the CFMM’s price is equal to the CEX price, and these profitable trades are exhausted. In other words, the slippage built into CFMM design is what gives arbitrageurs the incentive to align CFMM prices with CEX prices. 

**Relationship to high-frequency trading models.** Our work is related to models of “quote sniping” in high-frequency trading. Budish et al. [2015] analyzes a model in which, whenever prices move, bid-ask quotes become “stale”, creating a speed race between the quoting market maker to update her quotes, and arbitrageurs to “snipe” the stale quote. In these models, purely public information creates “informed-trader” risk, because arbitrageurs occasionally win speed races and are able to act on public information before the quoting market maker can. In relation to these models, CFMMs can be thought of like quoting market makers that, by design, never update prices proactively. An CFMM only ever increases its quoted price when it receives orders to buy the risky asset; in other

<!-- page: 23 -->

words, CFMMs’ price quotes only ever move when they are sniped. Thus, any movement in CEX prices causes CFMM quotes to become stale, creating a speed race to snipe the CFMM. CFMMs always lose these races, and loss-versus-rebalancing consists of the cumulative losses LPs suffer from getting “sniped” to trade at worse-than-market prices. One technical difference from the setting of Budish et al. [2015] is that, in the present paper, asset price innovations are purely diffusive, as opposed to arriving at discrete instances (i.e., jumps). 

**Volatility versus informed trading.** Our results are reminiscent of classic results in market microstructure, which state that market makers charge fees to make up for losses from adverse selection. However, the literature on AMMs have analyzed two slightly different narratives for the source of the adverse selection CFMM LPs face. The first, reminiscent of microstructure models such as Glosten and Milgrom [1985], is that LPs lose money when traders with knowledge of _future_ market prices trade with the CFMM, creating “wrong-way” risk. This channel is often called “informed trading”. The second, which we focus on in this paper, is that LPs lose money when traders with knowledge of _current_ market prices on the CEX snipe the CFMM LP. We will refer to this channel as “volatility” or “slippage”. 

In our model, the losses of CFMM LPs arise entirely from the latter “slippage” effect. Slippage is straightforwards to quantify, because it depends on easily measurable objects: the volatility of CEX price movements, and the CFMM’s marginal utility. A number of recent papers in the financial economics literature have pointed out qualitatively that CFMM losses are linked to the volatility of the underlying asset; our contribution relative to these papers is to is to show that this relationship can be quantified, under exactly the canonical Black-Scholes model of risky asset prices.<sup>13</sup> Informed trading is more difficult to quantify in practice, since it requires estimating the extent to which order flow tends to be informative about future price movements. In the context of our model, since we assumed the CEX is infinitely deep, informed traders would only trade on the CEX, since they have lower price impact. Thus, in our model, informed trading does not directly contribute to adverse selection losses to CFMM LPs. 

**Decomposing LP P&L.** Next, we plug the LVR expression into (2), to decompose the P&L of the 

> 13Outside of the finance literature, some earlier papers in the crypto literature have derived related quantification results, such as Angeris et al. [2020]. Our contribution relative to this literature is to construct a clean “rebalancing strategy” benchmark, and to link these results to ideas about adverse selection in market making.

<!-- page: 24 -->

LP position into three components, 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0024-01.png)


The right side of expression (13) decomposes the profit of an CFMM LP position, from time 0 to time _t_ , into three components. The first is “market risk”, which from (5) is exactly the P&L of the rebalancing strategy. The CFMM is long the risky asset; hence, at any given point in time, it accrues gains and losses when the risky asset’s price fluctuates. However, market risk contributes nothing to the CFMM’s profits under the risk-neutral measure; equivalently, the market risk component of the CFMM’s profits can be costlessly hedged, simply by shorting however much of the underlying asset the CFMM holds at any point in time, as the rebalancing strategy does. Besides market risk, CFMM LP positions attain positive returns from the strictly increasing process FEE _t_ , and negative returns from the strictly decreasing process _−_ LVR _t_ . 

The Black-Scholes framework for classic options indicates that the directional risk exposure of options can be hedged, simply by taking positions in the underlying asset. Option market makers use this principle in practice, delta-hedging the directional risk of their options portfolios, and profiting from collecting bid-ask spreads and betting on differences between realized volatility and the volatility implied by option prices. Analogous to this, the decomposition in (13) also corresponds to a tradable strategy: one can _delta-hedge_ CFMM LP positions, simply by combining a long position in the CFMM LP with a short position in the rebalancing strategy. The time- _t_ payoff of the long-LP, short-rebalancing-strategy position is: 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0024-04.png)


Intuitively, the delta-hedged LP position is always short as much ETH in the rebalancing strategy as it is long in the LP position, and is thus insulated against directional movements in ETH prices. This is thus a pure bet on whether fees are large enough to offset losses from slippage. Delta-hedging a CFMM LP position is particularly simple because it only requires shorting the amount of ETH held by the risky asset.<sup>14</sup> In particular, while we have framed our analysis from the perspective of a 

> 14In contrast, for example, standard European or American options cannot be delta-hedged in a model-free way:

<!-- page: 25 -->

single liquidity provider who holds the entire CFMM LP position, an individual liquidity provider can hedge her own LP position by shorting as much ETH as her individual position currently holds, that is, the amount of ETH she would receive if she burned her LP position, at any point in time. The individual does not need to keep track of any mints and burns by other LPs, since these events do not change the quantity of ETH held in her LP position. 

## **5. Examples** 

In this section, we calculate LVR for a number of specific CFMM examples. 

**Example 2** (Weighted Geometric Mean Market Maker / Balancer) **.** _Consider the bonding function f_ ( _x, y_ ) ≜ _x_<sup>_θ_</sup> _y_<sup>1</sup><sup>_−θ_</sup> _, for θ ∈_ (0 _,_ 1) _. Solving the pool value optimization_ (1) _allows us to obtain the closed-form optimal solutions_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0025-04.png)


_Then,_ 

_and_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0025-07.png)


The weighted geometric mean market maker generalizes the constant product market maker. For these market makers, the instantaneous LVR normalized per dollar of pool reserves is constant, i.e., 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0025-09.png)


In fact, with a minor caveat, weighted geometric market makers are the _only_ CFMMs for which this is true. We discuss this in Appendix B.2. Finally, observe that LVR is maximized when _θ_ = 1 _/_ 2, and goes to zero as _θ →{_ 0 _,_ 1 _}_ .<sup>15</sup> 

**Example 3** (Constant Product Market Maker / Uniswap v2) **.** _Taking θ_ = 1 _/_ 2 _in Example 2, we have_ 

> in the Black-Scholes framework, the delta of an option depends on volatility and other parameters. 

> 15See also Proposition 1 of Evans [2020], evaluating a weighted geometric mean market maker over a finite horizon using risk-neutral pricing.

<!-- page: 26 -->

_that_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0026-01.png)


This example shows that the constant product market maker admits particularly simple expressions for LVR: _ℓ_ ( _σ, P_ ) _/V_ ( _P_ ), the loss per unit time as a fraction of mark-to-market pool value, is simply 1 _/_ 8 times the instantaneous variance. This formula is straightforward to apply empirically: for example, if the ETH-USDC volatility is _σ_ = 5% (daily), this formula implies that the ETH-USDC LP pool loses approximately _σ_<sup>2</sup> _/_ 8 = 3 _._ 125 (bp) in pool value to LVR daily. 

**Example 4** (Uniswap v3 Range Order) **.** _Given liquidity parameter L ≥_ 0 _and prices in the given range_ [ _Pa, Pb_ ) _, consider the bonding function of the “range order” Adams et al. [2021],_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0026-04.png)


_Solving the pool value optimization_ (1) _,_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0026-06.png)


_Then, for P ∈_ ( _Pa, Pb_ ) _,_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0026-08.png)


_so that_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0026-10.png)


Observe that the instantaneous LVR is the same in Example 3. However, the pool value _V_ ( _P_ ) is lower. Indeed _V_ ( _P_ ) _→_ 0 if _Pa ↑ P_ and _Pb ↓ P_ , so 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0026-12.png)


i.e., the instantaneous LVR per dollar of pool reserves can be arbitrarily high in this case, if the liquidity range is sufficiently narrow. This is consistent with the idea that range orders “concentrate” liquidity.

<!-- page: 27 -->

~~voy ov~~ ~~<u>(o</u>~~ v) ~~(V~~ ov) ~~<u>vo (vv)</u> (Vo~~ v <u>)</u> 

¥ ¥ 

y

<!-- page: 28 -->

_in-range orders contribute to_ LVR _, i.e.,_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0028-01.png)


The quantity _L_<sup>¯</sup> ( _P_ ) is the _aggregate in-range liquidity_ , given the current price _P_ . From the perspective of the set of range orders which comprises the pool, this is a sufficient statistic for computing LVR. 

**Example 6** (Linear Market Maker / Limit Order) **.** _For K >_ 0 _, consider the linear bonding function f_ ( _x, y_ ) ≜ _Kx_ + _y. Solving the pool value optimization_ (1) _,_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0028-04.png)


_Hence, this pool can be viewed as similar to a resting limit order_<sup>17</sup> _that is, depending on the relative value of the price Pt versus limit price K, either an order to buy (if Pt ≥ K) or an order to sell (if Pt < K) up to L/K units of the risky asset at price K. In this case,_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0028-06.png)


_Observe that V_ ( _·_ ) _does not satisfy the smoothness requirement of Assumption 1 Part 2: the first derivative is discontinuous at the limit price P_ = _K. Thus, the characterization of Theorem 1 does not apply._<sup>18</sup> 

> 17While the linear market maker is _statically_ identical to a resting limit order, observe that they are _dynamically_ different. In particular, once the price level _K_ is crossed, in a traditional LOB, the limit order is filled and removed from the order book. With a linear market maker, the order remains in the pool at the same price and quantity, but with opposite direction. This merely refers to a superficial change of the _default strategy_ after a trade execution. 

> 18Note that the pool value function remains concave and the pool value process is a super-martingale. Hence, from the Doob-Meyer decomposition, a non-negative monotonic running cost process (analogous to LVR) exists. However, this process is not described by (7)–(8). Instead, it can be constructed using the concept of “local time” and the Itô-Tanaka-Meyer formula, but we will not pursue such a generalization here [see, e.g., Carr and Jarrow, 1990].

<!-- page: 29 -->

## **6. Empirical Analysis** 

Next, we bring our model to data. This section has two goals. First, we illustrate that our analytical expressions for LVR, in practice, are nearly equal to the returns from a “delta-hedged LPing strategy” which takes a long position in the CFMM LP, and a short position in the rebalancing strategy. Second, we show that hedged LPing is dramatically less risky than unhedged LPing: accounting for the rebalancing strategy’s profits decreases the standard deviation of daily LP returns by a factor of almost 20. 

Repeating (14), we have 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0029-03.png)


The left side of (21) can be thought of as the P&L from a delta-hedged LP position: the P&L of the LP position, minus that of the rebalancing strategy. This quantity can be estimated empirically under very weak assumptions. The profits of the rebalancing strategy are simply the returns on a portfolio which holds just as much of the risky asset as the LP position holds at any point in time, adjusting holdings always at market prices. This quantity is simple to calculate for any CFMM, at arbitrarily high frequency, since the entire history of the amount of each asset held by any CFMM is generally publicly available on the blockchain; moreover, since only asset holdings are needed, this procedure can be applied regardless of the specific bonding used by the CFMM. The P&L of an LP position over any period of time can be calculated simply as the mark-to-market value of pool reserves, at CEX prices at the start and end of the time period, accounting for mints, burns, swaps, and trading fees.<sup>19</sup> 

The right side of (21) can be thought of as our model’s prediction for the delta-hedged P&L, i.e., left side of (21). The first term on the right side corresponds to trading fees, which are observable. The second term is LVR, which we can measure as a function of realized volatility using expressions 

> (7) and (8) of Theorem 1. In this way, the degree to which the right side of (21) is close to the left 

> 19Note that delta-hedging an LP position does not incur any flow gas costs, since simply holding an LP position in a CFMM, without doing any minting or burning, does not require spending any gas. Thus, compared to executing this trading strategy in practice over a fixed time period, the only fees that the left side of (21) does not account for are the transaction fees from executing the rebalancing strategy on a CEX; any financing costs for maintaining a short position on a CEX; and two one-time gas costs, for minting an LP position at the start of the period and then burning it at the end of the period.

<!-- page: 30 -->

side measures the effectiveness of LVR in quantifying LP returns. 

We bring the model to data using the WETH-USDC trading pair<sup>20</sup> on Uniswap v2 for the period from August 1, 2021 to July 31, 2022. Details of the data sources we use, and how we measure various quantities, are described in Appendix C. Essentially, to measure the left side of (21), we measure the P&L of an LP position simply as the mark-to-market value of pool reserves, periodically valuing “mints” and “burns” — that is, tokens withdrawn or deposited from the LP position — at market prices. We measure the profits of the rebalancing strategy simply by rebalancing to match the CFMM LP holdings at a number of different discrete time frequencies. For example, suppose we rebalance each minute, and suppose we observe that the CFMM LP position holds 10,000 ETH at 12:01am on January 1st, 2022. The rebalancing strategy then holds 10,000 ETH at 12:01am, so the P&L of the rebalancing strategy from 12:01am to 12:02am is simply 10 _,_ 000 ( _P_ 12:02 _am − P_ 12:01 _am_ ), the amount of ETH held times the change in ETH prices over the next minute. In general, if the rebalancing strategy holds _x_<sup>_RB_</sup> _t_ of the risky asset at time _t_ until time _t_ + ∆ _t_ , then ∆RB P&L _t_ , the rebalancing strategy’s net profit from period _t_ to _t_ + ∆ _t_ , is: 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0030-02.png)


Expression (22) is the discrete-time analog of the envelope formula expression, (5), for the returns on any strategy which trades at market prices. Note that ∆RB P&L _t_ is not directly affected by rebalancing trades – changes in _x_<sup>_RB_</sup> _t_ over time – because these rebalancing trades are made at fair market prices on the CEX, and we assumed CEX trades have no price impact. We calculate total profits of the rebalancing strategy over any time period by summing the increments (22) over time. As we will show below, our results are relatively insensitive to the rebalancing horizon chosen. 

To measure the right side of (21), we observe FEE _t_ , fees paid into the LP pool over any given time period.<sup>21</sup> For LVR _t_ , since Uniswap v2 is a constant-product CFMM, percentage LVR has the particularly simple expression in (16) of Example 3, 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0030-05.png)


> 20“WETH”, or “wrapped ETH” is a variation of ETH that is compliant with the ERC-20 token standard. For our purposes, we will view ETH and WETH as equivalent. 

> 21Uniswap v2 also allows for assets to be borrowed for “flash loans” for a fee; however, in v2, these loans are accounted for as swaps, thus FEE _t_ contains revenue from flash loans. We discuss this briefly in Appendix C.1.

<!-- page: 31 -->

We measure LVR in each period simply by plugging in realized volatility and pool value to a version of equation (23) that is discretized over time. 

Note that, empirically, we measure the total fees paid by all kinds of traders. This differs slightly from our model, where we assume arbitrage traders pay no fees. Practically, since fees are simply an increasing process which potentially compensates for LVR, whether fees arise from noise trade or arbitrage trade does not substantially impact the returns on LP positions. If we assumed arbitrage traders paid trading fees in the model, this would decrease the amount of arbitrage: instead of prices on the CFMM moving immediately to match CEX prices at all times, prices would have to move more than fees in order for arbitrage trade to have nonnegative payoffs. The analysis of arbitrage profits in the presence of fees is the subject of follow-on work [Milionis et al., 2023a]. 

**Markouts.** Industry participants have recently begun using a “markouts” approach to evaluate CFMM LP P&L [see, e.g., CrocSwap, 2022]. Markouts essentially attribute profits to trades by comparing the price of each trade to a future price, usually at some fixed time offset from the trade (e.g., 10 minutes) either from a CEX, or the CFMM itself. However, delta-hedging and the markout approach are in a sense closely related: the P&L of delta-hedged LPing, when rebalanced at discrete periods, turns out to be exactly equivalent to markout profits, marked to CEX prices at the end of discrete periods of the same frequency. In other words, the main difference between delta-hedging and markout analysis is whether the marking price is obtained in a fixed offset of time in the future after a trade, or based on the ending price of the interval the trade was contained in. These two are likely to be very close, especially when the markout offset or delta-hedging interval are short. Thus, delta-hedged LPing can be thought of as a microfoundation for markout-style analysis. 

### **6.1. Empirical Results** 

The daily realized volatility estimates are illustrated in Figure 3. Here, it is clear that, not only is the volatility of this asset pair high, but the volatility in turn is also highly volatile, varying by a factor of five over the observation interval. 

In Figure 4, we see the daily average aggregate value for this pool over the time period. The average pool value was $209 million, and the pool value ranged between $90 million and $310 million.

<!-- page: 32 -->

![](assets/2022-milionis-et-al-amm-lvr.pdf-0032-00.png)


<!-- Start of picture text -->
realized volatility (%, daily, 60min samples)<br>20.0%<br>realized volatility<br>17.5%<br>15.0%<br>12.5%<br>10.0%<br>7.5%<br>5.0%<br>2.5%<br>0.0%<br>2021-08 2021-09 2021-10 2021-11 2021-12 2022-01 2022-022022-03 2022-04 2022-05 2022-06 2022-07 2022-08<br><!-- End of picture text -->

**Figure 3:** Daily realized volatility for the ETH-USDC pair, computed from Binance minutely closing prices, sampled at 60 minute intervals. 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0032-02.png)


<!-- Start of picture text -->
total pool value (USDC, millions)<br>350M<br>pool_value<br>300M<br>250M<br>200M<br>150M<br>100M<br>50M<br>0M<br>2021-08 2021-09 2021-10 2021-11 2021-12 2022-01 2022-022022-03 2022-04 2022-05 2022-06 2022-07 2022-08<br><!-- End of picture text -->

**Figure 4:** The daily average pool value of the Uniswap v2 WETH-USDC pair.

<!-- page: 33 -->

Next, we show why it is important to account for the profits of the rebalancing strategy in analyzing LP returns. The `pool_pnl` series in Figure 5a shows the raw aggregate LP P&L _t_ (i.e., without delta-hedging by subtracting the rebalancing strategy). The pool P&L fluctuates wildly, and ultimately loses money. In particular, as shown in Table 1, the pool has an overall annualized return of _−_ 6 _._ 20%, and a Sharpe ratio of _−_ 0 _._ 15. 

However, these returns are largely driven by market risk: at any point in time, the pool maintains half of its value in ETH, and ETH prices varied significantly over this interval. The `hedged_pnl` series in Figure 5 illustrate hedged P&L, that is, LP P&L _t_ minus the profits of the rebalancing strategy, which is the left side of (21). This hedges directional exposure to ETH prices to first-order, and is just a bet on whether fees are greater than LVR. 

Visually, these lines are substantially less volatile than the raw LP P&L _t_ . This is quantified in Table 1, where we see that a delta-hedged LP position can achieve very low standard deviation of returns and high Sharpe ratios, and that, in general, standard deviations of returns decrease and Sharpe ratios increase with more frequent rebalancing. Moreover, the delta-hedged LP position actually makes positive returns, though this finding is specific to the setting we study here: in general, delta-hedged returns may be higher or lower than unhedged returns.<sup>22</sup> From the perspective of individual investors, suppose a hypothetical market participant minted a small LP position at the start of our sample period (ignoring gas fees), immediately delta-hedged the position on a CEX, and costlessly updated her delta-hedge at various time horizons. If we value the market participant’s position at the CEX price of ETH at any point in time, our results imply that the market participant would have attained a Sharpe ratios between 1.75 and 23.33, depending on the rebalancing frequency. 

**Accuracy of the model.** In Figure 6, we analyze the accuracy of our model, that is, the difference between the left and right sides of (21), for various choices of frequency of rebalancing. This analyzes how well our model is able to predict delta-hedged LP returns in the data. Fees minus LVR in our model tracks the pattern of hedged LP P&L: differences between the two seem to be stationary over the observed interval. Moreover, in general, as the frequency of rebalancing increases, the differences are smaller in magnitude. This is consistent with LVR as being a continuous rebalancing approximation. 

> 22Note that these returns assume no trading or financing costs for the rebalancing strategy.

<!-- page: 34 -->

![](assets/2022-milionis-et-al-amm-lvr.pdf-0034-00.png)


<!-- Start of picture text -->
cumulative P&L (USDC, millions)<br>pool_pnl<br>80M<br>hedged_pnl_1D<br>hedged_pnl_4H<br>60M<br>hedged_pnl_1H<br>hedged_pnl_5min<br>40M<br>hedged_pnl_1min<br>fees_minus_lvr_pnl<br>20M<br>0M<br>-20M<br>-40M<br>2021-08 2021-09 2021-10 2021-11 2021-12 2022-01 2022-022022-03 2022-04 2022-05 2022-06 2022-07 2022-08<br><!-- End of picture text -->

- **(a)** Including the aggregate pool P&L series. 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0034-02.png)


<!-- Start of picture text -->
cumulative P&L (USDC, millions)<br>20M hedged _ pnl _ 1D<br>hedged_pnl_4H<br>15M hedged_pnl_1H<br>hedged_pnl_5min<br>hedged_pnl_1min<br>10M fees _ minus _ lvr _ pnl<br>5M<br>0M<br>-5M<br>2021-08 2021-09 2021-10 2021-11 2021-12 2022-01 2022-022022-03 2022-04 2022-05 2022-06 2022-07 2022-08<br><!-- End of picture text -->

**(b)** Excluding the aggregate pool P&L series. 

**Figure 5:** Cumulative pool P&L, delta-hedged P&L, and predicted P&L from our expressions for LVR, for the Uniswap v2 WETH-USDC trading pair. In the first panel, the `pool_pnl` series shows the raw P&L of the LP position. In both panels, the various `hedged_pnl` series show delta-hedged LP P&L, that is, the P&L from a long position in the pool, and a short position in the rebalancing strategy, rebalanced at various frequencies (daily, every four hours, every hour, every five minutes). The `fees_minus_lvr_pnl` series shows fees minus LVR, this is the delta-hedged P&L predicted by our theory. The data source for prices is Binance, and LP P&L is calculated using data on Uniswap trades, mints, and burns from the Ethereum blockchain. Details of how we calculate these quantities are in Appendix C.

<!-- page: 35 -->

||**avg return**<br>(%, annual)|**stdev return**<br>(%, annual)|**Sharpe ratio**<br>(annual)|
|---|---|---|---|
|`pool_pnl`|-6.20|42.08|-0.15|
|`hedged_pnl_1D`|5.04|2.87|1.75|
|`hedged_pnl_4H`|8.21|1.50|5.47|
|`hedged_pnl_1H`|9.75|0.90|10.81|
|`hedged_pnl_5min`|8.45|0.57|18.16|
|`hedged_pnl_1min`|9.04|0.39|23.33|
|`fees_minus_lvr_pnl`|8.16|0.48|17.03|


**Table 1:** Overall return statistics for the cumulative P&L series of Figure 5. 

**Using delta-hedged LPing in other contexts.** Our procedure is easily generalizable: any researcher interested in analyzing the economic determinants of AMM LP returns can use our “hedged LPing” methodology to eliminate LP positions’ market risk exposures. The procedure has very low data requirements: to construct profits of the rebalancing strategy, (22), the researcher only needs _x_<sup>_RB_</sup> _t_ , the time series of risky asset holdings of the CFMM LP, and _Pt_ , the CEX price of the risky asset. Hedged LP P&L is then just the difference between raw pool PNL and the return on the rebalancing strategy. 

We believe our methodology is a substantial improvement over existing methods in the literature to remove market risk exposures from LP P&L. Some papers, such as Fang [2022], use risk factor models to account for the component of LP returns attributable to market risk. Our methodology is much simpler: since a CFMM holds risky assets, it has first-order exposure to risky asset prices at any point in time equal to whatever amount of the risky asset it holds. These risk exposures can be accounted for simply by shorting the risky asset itself: this does not require taking a stance on a risk factor model, and estimating factor loadings. 

Other papers, such as Lehar et al. [2022] and Augustin et al. [2022], decompose LP P&L by subtracting “impermanent loss” — loss versus a strategy which holds the initial asset position. “Impermanent loss” — which we will refer to as “loss versus holding” or LVH— compares LP performance to a benchmark which simply holds the initial bundle of risky assets. As we discuss in Section 8, this combines losses from price slippage, which are always greater than 0, with the returns from the rebalancing strategy, which can be thought of as a particular trading strategy that bets on mean reversion. Impermanent loss is always equal in expectation to LVR under risk-neutral measure, but will always be noisier than LVR. Subtracting “impermanent loss” from LP returns

<!-- page: 36 -->

![](assets/2022-milionis-et-al-amm-lvr.pdf-0036-00.png)


<!-- Start of picture text -->
cumulative P&L difference vs. fees_minus_lvr_pnl (USDC, millions)<br><!-- End of picture text -->


![](assets/2022-milionis-et-al-amm-lvr.pdf-0036-01.png)


<!-- Start of picture text -->
2M<br>0M<br>diff_pnl_1D<br>-2M diff_pnl_4H<br>diff_pnl_1H<br>-4M diff_pnl_5min<br>diff_pnl_1min<br>-6M<br>-8M<br>-10M<br>2021-08 2021-09 2021-10 2021-11 2021-12 2022-01 2022-022022-03 2022-04 2022-05 2022-06 2022-07 2022-08<br><!-- End of picture text -->

**Figure 6:** Cumulative differences between the delta-hedged P&L (various `hedged_pnl` series of Figure 5) and predicted P&L from our model ( `fees_minus_lvr_pnl` series of Figure 5). 

thus results in, at best, a much noisier measure of returns, relative to LVR, reducing the likelihood that the researcher can elucidate economic effects with high statistical power. 

Finally, note that delta-hedging in practice requires periodic rebalancing; these rebalancing trades, if executed on centralized exchanges, incur costs such as bid-ask spreads, trading fees, and possibly margin and asset borrowing costs. Transaction-based fees can be limited somewhat by rebalancing less frequently; this implies that the hedged LP position will accrue some market risk in intervals between rebalancing trades. Our analysis in Figure 6 suggests that, for the WETHUSDC pair, rebalancing every 4 hours produces similar results to higher frequencies, though this finding would vary depending on the volatility of the underlying asset’s price. 

## **7. Option Pricing** 

We have shown that CFMM LPs behave like a bet on volatility, in the sense that LVR is large when volatility is high. In this section, we briefly discuss the relationship of CFMM LPs to three classical and inter-related ways that volatility can be traded [Carr and Madan, 2001]: static (European) options positions, dynamic trading strategies, and variance swaps. In Appendix B.1, we also demonstrate the equivalences between CFMM LP positions and these concepts in a simple two-

<!-- page: 37 -->

step binomial tree model. 

### **7.1. Static Options Positions** 

Our results are related to Clark [2020], Fukasawa et al. [2022], and Deng et al. [2023], who show that, over any finite time horizon, an AMM LP position’s payoff, ignoring fees, can be replicated by shorting a bundle of European options. Technically, this follows from the facts that the CFMM’s asset position and value are both path-independent: if the price is _PT_ at time _T_ , the CFMM holds _x_<sup>_∗_</sup> ( _PT_ ) of the risky asset and has pool value _VT_ = _V_ ( _PT_ ) corresponding to the final “payoff function” _V_ ( _·_ ), regardless of the path that prices took to reach _PT_ . More intuitively, at any time _T_ , the CFMM simply offers a menu of quantities of the asset to buy or sell at any given price, identically to a portfolio of European options. Ignoring fees, the CFMM exactly breaks even if prices do not move, _PT_ = _P_ 0, and loses money otherwise; hence, the CFMM LP position is essentially equivalent to _giving away_ a bundle of European options. This intuition is consistent with the fact that the _V_ ( _·_ ) is a _concave_ function (cf. Lemma 1). 

Expected LVR until period _T_ can be thought of as the value of the European options given away. This analogy gives another intuition for the comparative statics of expected LVR. European options are worth more when volatility is higher, so LVR is increasing in the volatility of the underlying asset. When the marginal liquidity of the AMM bonding curve is greater, the replicating portfolio of European options is larger: AMMs that trade more aggressively essentially give away more European options, also increasing LVR. 

As previous papers have discussed, the European option replication result also implies that, over any finite time horizon, the exposure of the AMM LP position to underlying prices can be _totally_ hedged, by taking a long position in the replicating bundle of European options. This trade — a long position in the AMM LP, plus a short position in the replicating bundle of European options — is essentially a _trading fee swap_ , betting on whether accrued trading fees from time 0 to _T_ are greater than European option premia of the replicating portfolio at time 0. The trader enters an LP position, and pays a premium for buying the replicating bundle of European options upfront. The AMM LP position then loses no money from price movements; the total position profits if the accrued trading fees until time _T_ are greater than the European option premia paid upfront, and loses otherwise.

<!-- page: 38 -->

### **7.2. Dynamic Trading Strategies** 

Classic options theory implies that static option positions are equivalent to dynamically trading the underlying asset in a certain way. The static option position is a combination of short straddles and strangles, selling out-of-money calls and puts. This position is equivalent to a dynamic trading strategy which sells the asset when prices increase, and buys when prices decrease. This is exactly what the AMM LP position does: observe that, from Lemma 1 Part 3, _x_<sup>_∗_</sup> ( _·_ ) is non-increasing. If prices decrease slightly from _P_ 0 to _Pt < P_ 0, the rebalancing strategy responds by buying the risky asset. The rebalancing strategy thus makes a profit, relative to simply holding the initial position _x_<sup>_∗_</sup> ( _P_ 0), if prices increase back to _P_ 0, and makes a loss if prices decrease further from _Pt_ . This argument holds symmetrically for price decreases, implying that the rebalancing strategy makes losses if prices diverge from _P_ 0, and profits when prices make small movements away from _P_ 0 and back. In the special case where the risky asset’s price is a random walk, the rebalancing strategy thus breaks even on on average. In contrast, when prices move away from _P_ 0 and back, the CFMM reverts to the initial value _V_ ( _P_ 0), exactly breaking even: there is no profit from price convergence, to offset the losses the CFMM makes when prices diverge from _P_ 0. 

### **7.3. Variance Swaps** 

Finally, as discussed by Fukasawa et al. [2022], variance can be traded directly by trading swaps on realized variance. The VIX is such a contract, operating on a fixed finite time horizon. Applying Lemma 1 Part 3, the instantaneous LVR of (8) can be re-written as 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0038-04.png)


Here, the first component, ( _σP_ )<sup>2</sup> , is the instantaneous variance or quadratic variation of the price, i.e., for small ∆ _t_ , Var[ _Pt_ +∆ _t|Pt_ = _P_ ] _≈_ ( _σP_ )<sup>2</sup> ∆ _t_ . Recalling that _x_<sup>_∗_</sup> ( _P_ ) is the total quantity of risky asset held by the pool if the price is _P_ , the second component, _|x_<sup>_∗′_</sup> ( _P_ ) _|_ corresponds to the _marginal_ liquidity available from the pool at price level _P_ . Now, integrating over time, we have that 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0038-06.png)

<!-- page: 39 -->

This expression is the payoff of the floating leg of a continuously sampled generalized variance swap [Carr and Lee, 2009, see, e.g.,], specifically a price variance swap that is weighted by marginal liquidity. 

## **8. Other Benchmarks and “Impermanent Loss”** 

In this section, we consider the possibility of alternative benchmarks aside from the rebalancing strategy. We first define a broad class of benchmark strategies: the only restrictions we impose on these strategies are that they begin holding the same position in the risky asset as the CFMM, and that they adjust holdings at CEX prices. Specifically, we define a benchmark as a self-financing trading strategy, described by a position _x_ ¯ _t_ in the risky asset. We assume that initial holdings match the pool, i.e., (¯ _x_ 0 _,_ ¯ _y_ 0) ≜ � _x∗_ ( _P_ 0) _, y∗_ ( _P_ 0)�. We assume that _x_ ¯ _t_ satisfies the square-integrability condition (3), so that the resulting trading strategy is admissible. Denote the value of that strategy by _R_<sup>¯</sup> _t_ , so that 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0039-03.png)


For any such benchmark, we can thus define the _loss-versus-benchmark_ according to LVB _t_ ≜ _R_<sup>¯</sup> _t −Vt_ . The following result characterizes the loss process LVB _t_ as a function of the underlying benchmark ¯ strategy _xt_ . 

**Corollary 1.** _For all t ≥_ 0 _,_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0039-06.png)


_and at the same time,_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0039-08.png)


_The loss process has quadratic variation_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0039-10.png)


_Therefore, among all benchmark strategies, the rebalancing strategy uniquely defines a loss process_

<!-- page: 40 -->

#### _with minimal (zero) quadratic variation._ 

**Proof** _._ The first part is an immediate corollary of Theorem 1 and (5). The second part is immediate by the definition of the risk-neutral measure. The third part follows from the Itô isometry. ■ 

There are two ways to interpret Corollary 1. On the one hand, in (24), the expected value of ∆(¯ _x_ ) _t_ is always 0 under the risk-neutral measure. Thus, the second part of Corollary 1 expresses that the risk-neutral expectation of LVB is the same for _any_ choice of benchmark, including LVR and the HODL benchmark. This is because CFMM LP losses arise from trading at off-market prices: _any_ benchmark which trades at market prices, in expectation, does equally well under the risk-neutral measure, and thus the gap between any market benchmark and LVR is equal in expectation. In this sense, the market price of the expected losses of CFMM LPs is invariant to the particular choice of market-based benchmark. 

On the other hand, LVR is the _unique_ choice of benchmark which eliminates differences in performance between the CFMM and the benchmark strategy due to market risk, and isolating losses due to price slippage. All benchmarks outperform the CFMM LP position by the same amount in expectation; however, on any given price path _Pt_ , any given benchmark may over- or underperform to the CFMM LP position, because the benchmark may adopt different holding strategies for the risky asset from the CFMM. As an example, we showed in Section 6 that the CFMM LP position underperforms a benchmark which sells all ETH and holds _x_ ¯ _t_ = 0 throughout, because of the fact that the CFMM LP holds a larger ETH position and ETH prices dropped over the time horizon we analyze, implying the misleading conclusion that the CFMM LP position underperformed a market-based benchmark. 

The LVR benchmark is useful because the rebalancing strategy exactly matches the risky asset holdings of the CFMM, removing differences in market risk exposure and isolates losses due to slippage. Theorem 1 showed that LVR is a strictly increasing process: it is _always_ positive, regardless of the path prices take. Expression (26) thus shows that the rebalancing strategy is the unique choice of benchmark which minimizes the quadratic variation of the loss process: that is, any other choice of benchmark can be thought of as LVR, plus a noise term which has mean 0 under risk-neutral measure, caused by differences in market risk exposures. Thus, in our view, benchmarks other than the rebalancing strategy confound two concepts: LVR, which captures losses of the CFMM

<!-- page: 41 -->

LP position due to trading at off-market prices, and ∆(¯ _x_ ), which captures differences between the risky asset holdings of the CFMM and the benchmark.<sup>23</sup> 

One benchmark of particular interest is a strategy that simply holds the initial position, i.e., _x_<sup>HODL</sup> _t_ ≜ _x_<sup>_∗_</sup> ( _P_ 0), with value 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0041-02.png)


Loss versus the HODL benchmark, introduced by Pintail [2019], is sometimes known by practitioners as “impermanent loss” or “divergence loss” [e.g., Engel and Herlihy, 2021]. Motivated by the aforementioned analysis, in our view this is more accurately described as “loss-versus-holding”: LVH _t_ ≜ _Rt_<sup>HODL</sup> _− Vt_ . Like LVR, LVH is LVH is always non-negative: **Proposition 1.** _For all t ≥_ 0 _,_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0041-04.png)


_i.e.,_ LVH _is a non-negative process._ 

**Proof** _._ We have that 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0041-07.png)


and, by the optimality of Equation (1) for _P_ = _Pt_ , this quantity is always non-negative. ■ 

While LVH is non-negative, it cannot be viewed as a true “running cost”: LVH, like any LVB for any non-rebalancing benchmark, contains a market risk component, and it can always revert. Indeed, from (24), the only permanent and non-reverting component of LVH is LVR. Beyond that, there are other disadvantages to LVH as a cost metric. First, LVH depends on the initial position at time _t_ = 0. This means that two different LPs investing in a pool will realize different LVH over the same interval of time, depending on the pool holdings at their respective initial times of investment. To contrast, LVR over the same interval of time is the same (up to proportionality of 

the investment size) for all LPs. Another disadvantage of LVH is that it is path independent: the 

> 23Examining (24), it is clear that LVB is a super-martingale and that, as per the Doob-Meyer decomposition, it must decompose uniquely into an increasing predictable process (the “compensator”) and a martingale. LVR is the compensator for LVB independent of the choice of benchmark, while ∆(¯ _x_ ) defines the martingale component and depends on the choice of benchmark.

<!-- page: 42 -->

value of LVH depends only on the asset price at the beginning and end of the observation interval. On the other hand, LVR is path dependent and depends on the entire sample path. This makes more sense for an adverse selection cost: intuitively, the profitability of market making should depend on quantities such as realized volatility or quadratic variation which measure the rate new information is incorporated into prices over the time interval, as LVR does. 

A common argument in the industry discourse for the benchmark of “impermanent loss” states that, as long as prices revert to their initial values, AMM holdings will also revert to their initial state, resulting in zero losses. We analyze this argument in Appendix B.1. In a slight departure from our baseline model, we assume prices evolve according to a two-step binomial tree. In the first step of the tree, the risky asset’s price either increases or decreases; in the second step, prices can either revert to their initial level, or diverge further. The basic trading strategy of an CFMM is to sell the risky asset when its price increases, and buy when its price decreases. Trading in this manner is a bet on mean reversion: when implemented trading at CEX prices, as the rebalancing strategy does, the strategy profits if prices mean-revert, and loses if prices diverge further, thus breaking even on average. The CFMM executes the same trades as the rebalancing strategy, but attains worse prices on each trade. Thus, the CFMM exactly breaks even if prices mean-revert, and loses more money than the rebalancing strategy if prices diverge, thus losing money on average. This example illustrates that, for an CFMM to perform well, it is not sufficient to break even when prices revert; a trading strategy which sells into price rises and buys into price decreases must actually make strictly positive profits when prices revert, in order to compensate for the losses it makes when prices diverge. An AMM’s performance should thus be benchmarked to the rebalancing strategy — making the same trades at CEX prices — rather than the intuitive but misleading benchmark that the CFMM should break even upon price reversion. 

## **9. Discussion and Implications** 

Besides their positive value for understanding and quantifying the losses from AMM LPing, our results also suggest ways that these losses could be reduced or eliminated. We showed that CFMM LPs lose money from price slippage: when CEX prices move, CFMM quotes become “stale” and are vulnerable to sniping by rebalancing arbitrageurs. This slippage can in principle be eliminated:

<!-- page: 43 -->

if an AMM had access to a high-frequency oracle for the CEX price _Pt_ , the AMM could in principle quote prices arbitrarily close to _Pt_ , up to the desired asset position _x_<sup>_∗_</sup> ( _Pt_ ).<sup>24</sup> Quoting prices this way would reduce arbitrageurs’ profits, allowing the AMM to achieve a payoff arbitrarily close to that of the rebalancing strategy. This design has a number of risks — it relies heavily on the accuracy of the oracle for _Pt_ , and leaves open the potential for oracle manipulation — but in principle an oracle-based AMM could substantially reduce or eliminate LVR. 

A related set of AMM designs revolve around selling the right to arbitrage the pool to certain special wallets, and redistributing profits to AMM LPs. This could be done in several ways. Suppose a particular crypto wallet address, which we call the “authorized participant” or AP, had the unique right for the first AMM trade in every block. This first execution right effectively conveys the right to arbitrage the pool [Josojo, 2022]. Alternatively, the AP could be provided the right to trade with the AMM paying zero fees [Jump Crypto, 2022]. The AP would then have a large advantage in arbitrage trading, since the AP could profitably trade against arbitrarily small price movements, whereas prices would have to move at least as much as the AMM’s percentage trading fees for nonAP wallets to profit from arbitrage trade. The AP would thus be able to capture a large fraction of fees from arbitrage trade. In either of these designs, an AMM protocol aiming to reduce LVR could thus run an AP wallet itself, doing CEX-DEX arbitrage, and redistributing arbitrage profits to LPs. Alternatively, AMM protocols could simply run periodic auctions — over longer periods, such as weeks or months — in which wallets can bid for the right to be authorized participants for some period of time. In principle, potential arbitrageurs should bid the _ex ante_ expectation of arbitrage profits, which includes LVR; the protocol can then redistribute these profits to LPs. Adams et al. [2024] analyzes this design in detail.<sup>25</sup> Both these methods capture either LVR or its expectation, and redistribute the profits to pool LPs. Another strand of work has argued that LVR would be reduced or eliminated if orders were sold in _batch auctions_ , rather than placed directly in mempools; this design is discussed in Ramseyer et al. [2022] and Canidio and Fritsch [2023], and related “request-for-quotes” mechanisms are now in use in a number of widely used protocols.<sup>26</sup> 

> 24A similar design is proposed in Krishnamachari et al. [2021b]. 

> 25Note that one subtlety about the zero fee design is that, in addition to rebalancing arbitrage profits, APs would be able to capture reversion arbitrage profits; hence, LVR provides a lower bound for how much revenue wallets could capture from having preferential access to arbitrage the pool. 

> 26“Batching” is used in CoWswap; a number of AMM protocols have also implemented related RFQ-like systems, such as Uniswap X, 1inch fusion, and Paraswap AugustusRFQ.

<!-- page: 44 -->

We believe that these are interesting directions for future AMM design research. 

An earlier line of work seeks to design specific CFMMs with good properties by identifying good bonding functions [Port and Tiruviluamala, 2022, Wu and McTighe, 2022, Forgy and Lau, 2021, Krishnamachari et al., 2021a]. Our work suggests that bonding functions only affect LVR insofar as they change the marginal liquidity of CFMMs. In certain cases, it may be desirable for marginal liquidity should vary with prices in a systematic way – this may be the case, for example, for stablecoin swap pairs. In other cases, different bonding functions, or “universal” AMM designs such as Uniswap v3, have equivalent infinitesimal LVR whenever they have equivalent amounts of marginal liquidity for an asset pair. 

## **10. Conclusion** 

In this paper, we constructed a model of AMM LP profits. We defined the losses suffered by LPs as “loss-versus-rebalancing”, or LVR; this is the gap between the profits of an AMM LP position, and the returns from a trading strategy which perfectly mimics the AMM’s position in the risky asset, but performs all trades at market prices. LVR arises from the fact that AMMs always trade at off-market prices, leaving money to arbitrageurs trading the AMM against a CEX. LVR is greater when prices are more volatile, and when the AMM’s “marginal liquidity” is greater, that is, it trades more aggressively in response to price movements. A delta-hedged AMM LP position — a position which is long the LP position, and short the rebalancing strategy — is profitable if the AMM collects more in fees than it loses in LVR. The model is quantitatively realistic enough to be brought to data; we show that our expressions for LVR predict AMM LP losses fairly accurately in practice. Our results have implications for how to measure AMM LP losses, and also how to redesign AMMs to reduce or eliminate LVR, which could lower the effective trading fees paid by market participants relying on AMMs for token pair liquidity. 

## **References** 

Austin Adams, Ciamac Moallemi, Sara Reynolds, and Dan Robinson. am-amm: An auction-managed automated market maker. _arXiv preprint arXiv:2403.03367_ , 2024. 

Hayden Adams, Noah Zinsmeister, and Dan Robinson. Uniswap v2 core, 2020. 

Hayden Adams, Noah Zinsmeister, Moody Salem, River Keefer, and Dan Robinson. Uniswap v3 core, 2021.

<!-- page: 45 -->

- Algebra Protocol. ALGEBRA Ecosystem: Decentralized exchange, 2023. URL `https://algebra.finance/ static/Algerbra%20Tech%20Paper-15411d15f8653a81d5f7f574bfe655ad.pdf` . 

- Guillermo Angeris and Tarun Chitra. Improved price oracles: Constant function market makers. In _Proceedings of the 2nd ACM Conference on Advances in Financial Technologies_ , pages 80–91, 2020. 

- Guillermo Angeris, Hsien-Tang Kao, Rei Chiang, Charlie Noyes, and Tarun Chitra. An analysis of uniswap markets. _arXiv preprint arXiv:1911.03380_ , 2019. 

- Guillermo Angeris, Alex Evans, and Tarun Chitra. When does the tail wag the dog? curvature and market making. _arXiv preprint arXiv:2012.08040_ , 2020. 

- Guillermo Angeris, Alex Evans, and Tarun Chitra. Replicating market makers. _arXiv preprint arXiv:2103.14769_ , 2021a. 

- Guillermo Angeris, Alex Evans, and Tarun Chitra. Replicating monotonic payoffs without oracles. _arXiv preprint arXiv:2111.13740_ , 2021b. 

- Aori Protocol. Trading on Aori, 2023. URL `https://www.aori.io/docs/trading` . 

- Jun Aoyagi. Liquidity provision by automated market makers. _SSRN 3674178_ , 2020. 

- Jun Aoyagi and Yuki Ito. Coexisting exchange platforms: Limit order books and automated market makers. _SSRN 3808755_ , 2021. 

- Matteo Aquilina, Eric Budish, and Peter O’neill. Quantifying the high-frequency trading “arms race”. _The Quarterly Journal of Economics_ , 137(1):493–564, 2022. 

- Patrick Augustin, Roy Chen-Zhang, and Donghwa Shin. Reaching for yield in decentralized financial markets. Working paper, 2022. 

- Markus Baldauf and Joshua Mollner. High-frequency trading and market performance. _The Journal of Finance_ , 75(3):1495–1526, 2020. 

- Andrea Barbon and Angelo Ranaldo. On the quality of cryptocurrency markets: Centralized versus decentralized exchanges. _arXiv preprint arXiv:2112.07386_ , 2021. 

- Dimitri P Bertsekas. _Control of uncertain systems with a set-membership description of the uncertainty._ PhD thesis, Massachusetts Institute of Technology, 1971. 

- Bruno Biais, Thierry Foucault, and Sophie Moinas. Equilibrium fast trading. _Journal of Financial economics_ , 116(2):292–313, 2015. 

- Fischer Black and Myron Scholes. The pricing of options and corporate liabilities. _Journal of political economy_ , 81(3):637–654, 1973. 

- Nassib Boueri. G3m impermanent loss dynamics. _arXiv preprint arXiv:2108.06593_ , 2021. 

- Michael Brolley and Marius Zoican. On-demand fast trading on decentralized exchanges. _Finance Research Letters_ , 51:103350, 2023. 

- Eric Budish, Peter Cramton, and John Shim. The high-frequency trading arms race: Frequent batch auctions as a market design response. _The Quarterly Journal of Economics_ , 130(4):1547–1621, 2015. 

- Vitalik Buterin. Let’s run on-chain decentralized exchanges the way we run prediction markets, October 2016. URL `www.reddit.com/r/ethereum/comments/55m04x/lets_run_onchain_decentralized_exchanges_ the_way/` . 

- Andrea Canidio and Robin Fritsch. Arbitrageurs’ profits, lvr, and sandwich attacks: batch trading as an amm design response. _arXiv preprint arXiv:2307.02074_ , 2023.

<!-- page: 46 -->

- Agostino Capponi and Ruizhe Jia. The adoption of blockchain-based decentralized exchanges. _arXiv preprint arXiv:2103.08842_ , 2021. 

- Peter Carr and Roger Lee. Volatility derivatives. _Annu. Rev. Financ. Econ._ , 1(1):319–339, 2009. 

- Peter Carr and Dilip Madan. Towards a theory of volatility trading. _Option pricing, interest rates and risk management, handbooks in mathematical finance_ , 22(7):458–476, 2001. 

- Peter P Carr and Robert A Jarrow. The stop-loss start-gain paradox and option valuation: A new decomposition into intrinsic and time value. _The review of financial studies_ , 3(3):469–492, 1990. 

- Álvaro Cartea, Fayçal Drissi, and Marcello Monga. Decentralised finance and automated market making: Predictable loss and optimal liquidity provision. _Available at SSRN 4273989_ , 2022. 

- Álvaro Cartea, Fayçal Drissi, and Marcello Monga. Predictable losses of liquidity provision in constant function markets and concentrated liquidity markets. _Applied Mathematical Finance_ , 30(2):69–93, 2023. 

- Cata Labs. Optimising lp performance part 2: Dynamic fees, Nov 2023. URL `https://blog.catalyst. exchange/optimising-lp-performance-part-2-dynamic-fees/` . 

- Y. Chen and D.M Pennock. A utility framework for bounded-loss market makers. In _Proceedings of the 23rd Conference on Uncertainty in Artificial Intelligence (UAI 2007_ , pages 49–56, Vancouver, BC, Canada, 2007. 

- Joseph Clark. The replicating portfolio of a constant product market. _Available at SSRN 3550601_ , 2020. 

- CrocSwap. Usage of markout to calculate lp profitability in uniswap v3, 2022. URL `https://crocswap. medium.com/usage-of-markout-to-calculate-lp-profitability-in-uniswap-v3-e32773b1a88e` . 

- Philip Daian, Steven Goldfeder, Tyler Kell, Yunqi Li, Xueyuan Zhao, Iddo Bentov, Lorenz Breidenbach, and Ari Juels. Flash boys 2.0: Frontrunning in decentralized exchanges, miner extractable value, and consensus instability. In _2020 IEEE Symposium on Security and Privacy (SP)_ , pages 910–927. IEEE, 2020. 

- Jun Deng, Hua Zong, and Yun Wang. Static replication of impermanent loss for concentrated liquidity provision in decentralised markets. _Operations Research Letters_ , 51(3):206–211, 2023. 

- Avinash K Dixit and Robert S Pindyck. _Investment under uncertainty_ . Princeton university press, 1994. 

- Atis Elsts. Conceptualizing Uniswap v3 LP profit and loss, January 2023. URL `https://atise.medium. com/conceptualizing-uniswap-v3-lp-profit-and-loss-ecbae6e09644` . 

- Daniel Engel and Maurice Herlihy. Presentation and publication: Loss and slippage in networks of automated market makers. _arXiv preprint arXiv:2110.09872_ , 2021. 

- Alex Evans. Liquidity provider returns in geometric mean markets. _arXiv preprint arXiv:2006.08806_ , 2020. 

- Chuck Fang. Liquidity misallocation on decentralized exchanges. _Available at SSRN 4281293_ , 2022. 

- Fenbushi Capital. Ending LP’s Losing Game: Exploring the Loss-Versus-Rebalancing (LVR) Problem and its Solutions, Oct 2023. URL `https://mirror.xyz/0xbdA5bCe76bF62d97D9C9dF0425CC10079Df1aD75/ bWOCccjVC7eoYKOzgmjXFdhWDc8rrUL6Yei-eugF52s` . 

- Sean Foley, Peter O’Neill, and T¯alis J Putni¸nš. A better market design? applying ‘automated market makers’ to traditional financial markets. _Available at SSRN 4459924_ , 2023. 

- Eric Forgy and Leo Lau. A family of multi-asset automated market makers. _arXiv preprint arXiv:2111.08115_ , 2021. 

- Masaaki Fukasawa, Basile Maire, and Marcus Wunsch. Weighted variance swaps hedge against impermanent loss. _Available at SSRN 4095029_ , 2022.

<!-- page: 47 -->

- Lawrence R Glosten and Paul R Milgrom. Bid, ask and transaction prices in a specialist market with heterogeneously informed traders. _Journal of financial economics_ , 14(1):71–100, 1985. 

- Jianlei Han, Shiyang Huang, and Zhuo Zhong. Trust in defi: an empirical study of the decentralized exchange. _Available at SSRN 3896461_ , 2021. 

- Joel Hasbrouck, Thomas J Rivera, and Fahad Saleh. The need for fees at a dex: How increases in fees can increase dex trading volume. _Available at SSRN_ , 2022. 

- Joel Hasbrouck, Thomas J Rivera, and Fahad Saleh. An economic model of a decentralized exchange with concentrated liquidity. _Available at SSRN 4529513_ , 2023. 

- Josojo. MEV capturing AMM (McAMM), 2022. URL `https://ethresear.ch/t/ mev-capturing-amm-mcamm/13336` . 

- Jump Crypto. Pyth Defender white paper draft. Working paper, September 2022. 

- Ariah Klages-Mundt and Steffen Schuldenzucker. Elliptic Concentrated Liquidity Pool (E-CLP): Technical Overview, 2022. 

- Bhaskar Krishnamachari, Qi Feng, and Eugenio Grippo. Dynamic automated market makers for decentralized cryptocurrency exchange. In _2021 IEEE International Conference on Blockchain and Cryptocurrency (ICBC)_ , pages 1–2, 2021a. doi: 10.1109/ICBC51069.2021.9461100. 

- Bhaskar Krishnamachari, Qi Feng, and Eugenio Grippo. Dynamic curves for decentralized autonomous cryptocurrency exchanges. _arXiv preprint arXiv:2101.02778_ , 2021b. 

Guillaume Lambert. Website at `https://lambert-guillaume.medium.com/` , 2022. 

- Alfred Lehar and Christine A Parlour. Decentralized exchanges. Technical report, Working paper, 2021. 

- Alfred Lehar, Christine A Parlour, and Marius Zoican. Liquidity fragmentation on decentralized exchanges. _Available at SSRN 4267429_ , 2022. 

- Gordon Liao and Dan Robinson. The dominance of uniswap v3 liquidity. `https://blog.uniswap.org/ uniswap-v3-dominance` , 2022. Accessed: 2024-05-01. 

- Alan Lu and Martin Köppelmann. Building a Decentralized Exchange in Ethereum, March 2017. URL `https://blog.gnosis.pm/building-a-decentralized-exchange-in-ethereum-eea4e7452d6e` . 

- Jason Milionis, Ciamac C. Moallemi, and Tim Roughgarden. Extended Abstract: The Effect of Trading Fees on Arbitrage Profits in Automated Market Makers. In _Financial Cryptography and Data Security. FC 2023 International Workshops_ . Springer International Publishing, 2023a. ISBN 978-3-031-48805-4. 

- Jason Milionis, Ciamac C. Moallemi, and Tim Roughgarden. Complexity-Approximation Trade-offs in Exchange Mechanisms: AMMs vs. LOBs. In _Financial Cryptography and Data Security_ . Springer International Publishing, 2023b. ISBN 978-3-031-47753-9. 

- Jason Milionis, Ciamac C. Moallemi, and Tim Roughgarden. A Myersonian Framework for Optimal Liquidity Provision in Automated Market Makers. In _15th Innovations in Theoretical Computer Science Conference (ITCS 2024)_ , Leibniz International Proceedings in Informatics (LIPIcs), Dagstuhl, Germany, 2024. Schloss Dagstuhl – Leibniz-Zentrum für Informatik. 

- Peter O’Neill. Can Markets be Fully Automated? Evidence From an “Automated Market Maker”, January 2022. URL `https://raw.githubusercontent.com/petero1111/website/gh-pages/ONeill_JMP_2022. pdf` . 

- Andreas Park. The conceptual flaws of constant product automated market making. _Available at SSRN 3805750_ , 2021.

<!-- page: 48 -->

- David M Pennock and Rahul Sami. Computational aspects of prediction markets. _Algorithmic game theory_ , pages 651–674, 2007. 

- Pintail. Uniswap: A good deal for liquidity providers?, 2019. URL `https://pintail.medium.com/ uniswap-a-good-deal-for-liquidity-providers-104c0b6816f2` . 

- Alexander Port and Neelesh Tiruviluamala. Mixing constant sum and constant product market makers. _arXiv preprint arXiv:2203.12123_ , 2022. 

- Kaihua Qin, Liyi Zhou, and Arthur Gervais. Quantifying blockchain extractable value: How dark is the forest? In _2022 IEEE Symposium on Security and Privacy (SP)_ , pages 198–214. IEEE, 2022. 

- Geoffrey Ramseyer, Mohak Goyal, Ashish Goel, and David Mazières. Augmenting batch exchanges with constant function market makers. _arXiv preprint arXiv:2210.04929_ , 2022. 

- Carl P Simon, Lawrence Blume, et al. _Mathematics for economists_ , volume 7. Norton New York, 1994. 

- Martin Tassy and David White. Growth rate of a liquidity provider’s wealth in _xy_ = _c_ automated market makers, 2020. 

- Mike Wu and Will McTighe. Constant power root market makers. _arXiv preprint arXiv:2205.07452_ , 2022. 

- Liyi Zhou, Kaihua Qin, Christof Ferreira Torres, Duc V Le, and Arthur Gervais. High-frequency trading on decentralized on-chain exchanges. In _2021 IEEE Symposium on Security and Privacy (SP)_ , pages 428–445. IEEE, 2021.

<!-- page: 49 -->

# Appendix 

## **A. Proofs** 

### **A.1. Proof of Theorem 1** 

First, we show that LVR _t_ is equal to expression (7). The smoothness condition of Assumption 1 Part 2 allows us to apply Itô’s lemma to _V_ ( _·_ ) to obtain 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0049-04.png)


where the last step follows from Lemma 1 Part 2. Comparing with (5), we obtain (7). Finally, the fact that _ℓ_ ( _σ, P_ ) _≥_ 0 follows from Lemma 1 Part 3. 

Next, we show that the cumulative profits of rebalancing arbitrageurs over the time interval [0 _, T_ ] is equal to LVR _T_ . We start with a discrete approximation to the arbitrage profit, indexed by _N ≥_ 1. Suppose arbitrageurs arrive sequentially, so that the _i_ th arbitrageur arrives at time _τi_ , for 1 _≤ i ≤ N_ . For convenience, set _τ_ 0 ≜ 0 and _τN_ +1 ≜ _T_ . For each 1 _≤ i ≤ N_ , at time _τi_ , the _i_ th arbitrageur observes the price _Pτi_ , rebalances the pool from � _x∗_ ( _Pτi−_ 1) _, y∗_ ( _Pτi−_ 1)� to _∗ ∗ ∗ ∗_ � _x_ ( _Pτi_ ) _, y_ ( _Pτi_ )�. In other words, the arbitrageur purchases _x_ ( _Pτi−_ 1) _− x_ ( _Pτi_ ) units of the risky asset from the CFMM at average price : 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0049-07.png)


The arbitrageur can then sell these units on the external market at price _Pτi_ and earn profits (in the numéraire) from the difference in price according to 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0049-09.png)


Denote by ARB<sup>(</sup> _T_<sup>_N_)</sup> the aggregate arbitrage profits. Summing over 1 _≤ i ≤ N_ , telescoping the sum,

<!-- page: 50 -->

and applying summation-by-parts yields 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0050-01.png)


Observe that the sum in the final expression is the discrete approximation of an Itô integral. Assume that the time partition mesh over [0 _, T_ ] shrinks to zero as _N →∞_ . Taking the limit as _N →∞_ and passing to continuous time, the sum converges to an Itô integral, which is welldefined under Assumption 1 Part 3. Further, _τN → T_ , so that _PτN → PT_ , and _x_<sup>_∗_</sup> ( _PτN_ ) _→ x_<sup>_∗_</sup> ( _PT_ ), _y_<sup>_∗_</sup> ( _PτN_ ) _→ y_<sup>_∗_</sup> ( _PT_ ). Thus, it holds that 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0050-03.png)


Hence, the cumulative profits of rebalancing arbitrageurs from time 0 to time _T_ are equal to LVR, defined in (6). 

### **A.2. LVR, Marginal Liquidity, and Bonding Function Curvature** 

For sufficiently smooth CFMM bonding functions, the marginal liquidity can be expressed in terms of derivatives of the CFMM bonding function: 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0050-07.png)


Qualitatively, (29) implies that marginal liquidity, _x_<sup>_′_</sup> ( _P_ ), is related to the curvature of the CFMM invariant curves. The denominator of (29) is equal to _P_<sup>2</sup> times the negative of the determinant of the bordered Hessian of _f_ . _f_ is strictly quasiconcave — that is, the upper level sets of _f_ are convex — if and only if this determinant is positive; moreover, the magnitude of the determinant is related to the curvature of the level curves of _f_ [Simon et al., 1994, p. 542]. Thus, CFMM invariants with “flatter”, more linear level curves will have greater marginal liquidity _dP_<sup>_<u>dx</u>_,andalso</sup>

<!-- page: 51 -->

greater LVR. 

(29) is also useful because it can be used to calculate _dP_<sup>_<u>dx</u>_usinganalyticexpressionsforbonding</sup> functions, which may be useful for computing LVR in practice. 

#### **A.2.1. Derivation of** (29) 

The Lagrangian of the pool expenditure minimization problem, (1), is: 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0051-04.png)


The optimal solution is characterized by the FOCs: 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0051-06.png)


![](assets/2022-milionis-et-al-amm-lvr.pdf-0051-07.png)


![](assets/2022-milionis-et-al-amm-lvr.pdf-0051-08.png)


Now, we will take _dP_<sup>_<u>dx</u>_byapplyingtheimplicitfunctiontheoremtothissystemoffirst-ordercon-</sup> ditions. The derivatives of the FOCs are: 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0051-10.png)


![](assets/2022-milionis-et-al-amm-lvr.pdf-0051-11.png)

<!-- page: 52 -->

![](assets/2022-milionis-et-al-amm-lvr.pdf-0052-00.png)


![](assets/2022-milionis-et-al-amm-lvr.pdf-0052-01.png)


Hence, we wish to solve the following system of equations for _dP_<sup>_<u>dx</u>_:</sup> 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0052-03.png)


Substituting, we have: 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0052-05.png)


![](assets/2022-milionis-et-al-amm-lvr.pdf-0052-06.png)


Now, applying (30) and (31), we have: 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0052-08.png)


Thus, we can simplify (35) to: 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0052-10.png)

<!-- page: 53 -->

![](assets/2022-milionis-et-al-amm-lvr.pdf-0053-00.png)


<!-- Start of picture text -->
_ ( ) a<br>ee —( —) a<br>[-<br>[— -)-<br>[)<br>eS<br>a<br><!-- End of picture text -->

<!-- page: 54 -->

the CFMM should not lose money if prices revert to their original state — is inappropriate. 

The binomial tree is a two-period discrete-time model, where prices can either go up or down in each time period. The tree is depicted in Panel A of Figure 7. The price begins at _P_ 0 = 1. In the first step of the tree, the price can then increase to _P_ 1<sup>_U_=1</sup><sup>_._4,ordecreaseto</sup><sup>_P D_</sup> 1 = 0 _._ 6. In the second step, from _P_ 1<sup>_U_,thepricecanincreaseto</sup><sup>_P UU_</sup> 2 = 1 _._ 8, or decrease to the original level _P_ 1<sup>_UD_</sup> = 1. From _P_ 1<sup>_D_,thepricecanincreasetotheoriginallevel</sup><sup>_P DU_</sup> 2 = 1, or decrease further to _P_ 2<sup>_DD_</sup> = 0 _._ 4. Note that the tree is set up so that, assuming 0 interest rates, the risk-neutral probabilities of up and down movements are all 0.5 — in other words, prices are martingales if the probabilities of up and down movements are equal, so no strategy trading at market prices should be able to make or lose money in expectation. 

We then calculate the asset positions and profits of three strategies in each tree state: the buyand-hold strategy, which simply holds the initial endowment ( _x_ 0 _, y_ 0) = 1 _,_ 1 forever; the CFMM; and the rebalancing strategy. To calculate these quantities, for the CFMM, we simply compute what ( _xt, yt_ ) is as a function of the tree price and the initial state ( _x_ 0 _, y_ 0). For the rebalancing strategy, in each tree state, if the CFMM trades from ( _xt, yt_ ) to ( _xt_ +1 _, yt_ +1), we assume the rebalancing strategy trades to _xt_ +1 at the price _Pt_ +1; hence, the rebalancing strategy’s cash position is: 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0054-03.png)


The results are shown in Figure 7. Panel B considers the profits of the buy-and-hold strategy, which simply holds the initial endowment ( _x_ 0 _, y_ 0) = 1 _,_ 1 forever. This strategy is exposed to market risk, making mark-to-market profits if prices rise and losing if prices fall. 

Panel C shows the performance of the rebalancing strategy. Since this strategy trades at market prices, it does not make or lose money in expectation under the risk-neutral measure. In period 1, the rebalancing strategy has exactly the same profits as the buy-and-hold strategy in each state. However, the rebalancing strategy sells the risky asset when prices increase to _P_ 1<sup>_U_=1</sup><sup>_._4.Thisis</sup> essentially a bet that prices will decrease; indeed, if prices decrease to _P_ 2<sup>_UD_</sup> = 1, the rebalancing strategy makes Π _t_ = 2 _._ 062, which is slightly higher than the buy-and-hold’s final inventory value of Π _t_ = 2 _._ 000. Conversely, if prices increase further to _P_ 2<sup>_UU_</sup> = 1 _._ 8, the rebalancing strategy makes 2 _._ 738, slightly lower than the buy-and-hold strategy’s value 2 _._ 800. On average, the rebalancing

<!-- page: 55 -->

strategy makes 2 _._ 400 conditional on reaching _P_ 1<sup>_U_,likethebuy-and-holdstrategy,oranyother</sup> strategy trading at market prices. 

Analogously, if prices first decrease to _P_ 1<sup>_D_= 0</sup><sup>_._6,therebalancingstrategybuystheriskyasset;</sup> it profits relative to buy-and-hold when prices increase to _P_ 2<sup>_DU_</sup> = 1, and loses if prices decrease further to _P_ 2<sup>_DD_</sup> = 0 _._ 2. This example shows that the rebalancing strategy is essentially a bet on price convergence. The rebalancing strategy sells into price increases and buys into price decreases; this pays off if prices mean-revert, and loses money if prices diverge further. However, the rebalancing strategy does not make or lose money on average. 

The performance of the CFMM is shown in Panel D. The CFMM makes the same trades as the rebalancing strategy; thus, _xt_ is the same in each tree state in panels _C_ and _D_ . However, the CFMM always trades at worse-than-market prices; as a result, _yt_ is higher state-by-state on the rebalancing strategy compared to the CFMM. A natural definition of loss-versus-rebalancing in discrete time would be the gap between the CFMM’s _yt_ -position, and the rebalancing strategy’s _yt_ -position, in each state. 

Note that the CFMM strategy has the elegant feature that, if prices revert to 1 — as in states _P_ 2<sup>_UD_</sup> and _P_ 2<sup>_DU_</sup> — the CFMM always holds exactly the same position as the buy-and-hold strategy. This is the basis of the colloquially popular idea that CFMM losses are “impermanent”. However, the CFMM loses money in expectation: the average profit of the CFMM, across states, is lower than the buy-and-hold strategy in both periods 1 and 2. Essentially, the CFMM bets on convergence, like the rebalancing strategy, but does so in a very inefficient way. The CFMM exactly breaks even if prices revert to their initial state, and loses money — even relative to the rebalancing strategy — if prices diverge. The CFMM strategy thus cannot break even without fees, because there is no state of the world where the CFMM strategy makes positive amounts. Using the options analogy, an CFMM LP position is a dynamic trading strategy which performs like giving away a straddle without collecting premia: the position loses money whenever prices move, and exactly breaks even when prices end where they started. 

This example also shows that the gap between the simple CFMM strategy and the buy-andhold strategy can be decomposed into two distinct components: the performance of the rebalancing strategy relative to buy-and-hold, and the performance of the CFMM relative to the rebalancing strategy. The gap between the rebalancing strategy and buy-and-hold is a bet on convergence: the

<!-- page: 56 -->

rebalancing strategy makes money if prices converge, and loses if prices diverge. The gap between the CFMM and the rebalancing strategy, which is the discrete-time version of LVR, is a systematic loss from slippage which accrues whenever prices move. 

**Relationships to option strategies.** The binomial tree example also helps illustrate the analogy between CFMM LP payoffs and European options. The time-2 difference between the payoffs of the rebalancing strategy and the buy-and-hold strategy is positive when prices mean-revert, and negative when prices diverge. Hence, payoffs are similar to those of a short European straddle or strangle position, which involves selling calls and puts which expire after two periods. The positive payoff when prices revert can be thought of as the option premia collected from selling the straddle, and the negative payoffs when prices diverge can be thought of as the payouts to the option buyer, which are made if either the call or the put sold expire in-the-money. The CFMM LP position has a similar pattern of payoffs, but makes 0 profits if prices end where they started. An CFMM LP position, ignoring fees, can thus be thought of like giving away a straddle position, without collecting any upfront option premia. Viewed this way, the equivalence between the rebalancing strategy and the static European strangle on the binomial tree reflects the classic idea that static option positions can be replicated by dynamically trading the underlying asset; in this case, European straddles and strangles are replicated by a strategy which sells the risky asset when prices increase and buys when prices decrease. 

### **B.2. Weighted Geometric Mean Market Makers** 

Weighted geometric mean market makers have the special property that the instantaneous LVR per dollar of pool value, i.e., _ℓ_ ( _σ, P_ ) _/V_ ( _P_ ), is a constant. The following theorem establishes that these are essentially the only CFMMs for which this is true: 

**Theorem 2.** _Suppose a CFMM satisfies_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0056-05.png)


_Then, we have_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0056-07.png)

<!-- page: 57 -->

**Panel A: Binomial Tree** 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0057-01.png)


###### **Panel B: Buy and Hold Strategy** 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0057-03.png)


###### **Panel C: Rebalancing Strategy** 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0057-05.png)


###### **Panel D: CFMM LP** 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0057-07.png)


**Figure 7:** The performance of buy-and-hold, a constant-product CFMM, and the rebalancing strategy, on a two-step binomial tree. Panel A depicts the binomial tree. The performance of the buy-and-hold strategy is shown in Panel B; the rebalancing strategy is shown in panel C, and the constant product CFMM is shown in panel D. In each panel, _xt, yt_ are the holdings of the strategy, and Π _t_ is the pool value, _yt_ + _Ptxt_ .

<!-- page: 58 -->

_for free constants L_ 1 _, L_ 2 _≥_ 0 _, where_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0058-01.png)


Comparing with Example 2, observe that (41) states that is the pool can only be the “sum” of _θ_ and 1 _− θ_ weighted geometric mean market makers. The two degrees of freedom are intuitive, since _θ_ and 1 _− θ_ are exchangeable in (15). 

**Proof of Theorem 2.** We construct the following ODE from the (40) along with (8), 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0058-04.png)


with constant _c_ ¯ ≜ 2 _c/σ_<sup>2</sup> . Make the substitution _P_ = _e_<sup>_z_</sup> , to arrive at the equivalent ODE, 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0058-06.png)


which when solved, along with the known limit condition from (1) that _V_ ( _z_ ) _→_ 0 as _z →−∞_ , by the usual method of linear ODEs results in the generic solution, 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0058-08.png)


Note that the above calculation is allowed because the quantity under the root is necessarily nonnegative, as if it were not, then _V_ ( _P_ ) would not be everywhere concave, which must be the case by Lemma 1. ■ 

### **B.3. Multi-Dimensional Generalization** 

In this section, we describe the multi-dimensional generalization of our results. Specifically, denote by vectors _x ∈_ R<sup>_n_</sup> +<sup>the reserves in</sup><sup>_n ≥_2 assets (none of which need be the numéraire), and</sup><sup>_Pt∈_R</sup><sup>_n_</sup> + a vector of prices (in terms of the numéraire). We assume that the price vector evolves according to geometric Brownian motion, i.e., 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0058-12.png)

<!-- page: 59 -->

with covariance matrix of returns Σ _t ∈_ R<sup>_n×n_</sup> , Σ _t ⪰_ 0, and where _Bt_<sup>QisastandardQ-Brownian</sup> motion on R<sup>_n_</sup> . 

Given a bonding function _f_ : R<sup>_n_</sup> +<sup>_→_R,definethepoolvaluefunction</sup><sup>_V_:R</sup><sup>_n_</sup> +<sup>_→_R+according</sup> to 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0059-02.png)


Analogous to Assumption 1, we will assume that an optimal solution _x_<sup>_∗_</sup> ( _P_ ) exists for all _P ∈_ R<sup>_n_</sup> +<sup>,</sup> that _V_ ( _·_ ) is twice continuously differentiable, and a suitable square-integrability condition on _x_<sup>_∗_</sup> ( _·_ ). Analogous to Lemma 1, we have 

**Lemma 2.** _For all prices P ∈_ R<sup>_n_</sup> +<sup>_,thepoolvaluefunctionsatisfies:_</sup> 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0059-05.png)


![](assets/2022-milionis-et-al-amm-lvr.pdf-0059-06.png)


![](assets/2022-milionis-et-al-amm-lvr.pdf-0059-07.png)


Define the rebalancing strategy by _xt_ = _x_<sup>_∗_</sup> ( _Pt_ ), with value 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0059-09.png)


Then, we have the following multi-dimensional analog of Theorem 1: 

**Theorem 3.** _Loss-versus-rebalancing takes the form_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0059-12.png)


_where we define, for P ≥_ 0 _, the instantaneous_ LVR 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0059-14.png)


_where we have applied Lemma 2. In the case where_ Σ = _σ_<sup>2</sup> _I, i.e., i.i.d. assets, we have that_ 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0059-16.png)

<!-- page: 60 -->

_In particular,_ LVR _is a non-negative, non-decreasing, and predictable process._ 

**Proof** _._ Applying Itô’s lemma to _Vt_ = _V_ ( _P_ ), 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0060-02.png)


The rest of the result follows as in the proof of Theorem 1. 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0060-04.png)


## **C. Data and Measurement** 

### **C.1. Data** 

**Prices.** We download minute-level USDC-ETH prices from the Binance API. We use close prices at the end of each minute for _Pt_ . 

**Uniswap.** We download data on the Uniswap v2 WETH-USDC pool from Dune Analytics, a data provider which aggregates data from the Ethereum blockchain into SQL databases. The queries we use to extract this data are included in Appendix C.2. 

**Mints and burns.** In each minute, we observe the gross amounts of each asset in which are withdrawn through “burns”, and deposited through “mints”. Let ( _x_<sup>mint</sup> _t , yt_<sup>mint</sup> ) and ( _x_<sup>burn</sup> _t , yt_<sup>burn</sup> ) be the total amounts of each asset _x_ and _y_ which are minted and burned respectively, between time _t −_ 1 and time _t_ . We will value minted and burned assets at the time- _t_ closing price _Pt_ . Thus, the monetary value of mints and burns respectively are: 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0060-10.png)


Let ( _xt, yt_ ) be the total asset holdings of the pool at time _t_ . As in the model, define the pool value at time _t_ by 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0060-12.png)

<!-- page: 61 -->

We can calculate ∆LP P&L _t_ , the change in P&L of the pool, from period _t −_ 1 to _t_ , as 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0061-01.png)


In words, this is the value of pool reserves at time _t_ valued at price _Pt_ , plus burned assets and minus minted assets valued at _Pt_ , minus the value of pool reserves at time _t −_ 1 valued at _Pt−_ 1. Note that, in contrast to our simplifying assumption in the model that fees are paid in the numéraire, in practice in Uniswap v2 fees are paid directly into the pool reserves; hence, the pool P&L includes transaction fees paid into the pool. 

**Rebalancing strategy** . We rebalance the pool at different time frequencies. For each rebalancing frequency, we compute the returns of a strategy which at any point in time holds as much ETH as the pool holds at the start of the period. For example, if the rebalancing frequency is daily, we set _x_<sup>_RB_</sup> _t_ at any minute _t_ equal to the LP pool reserves at the start of the day containing the minute _t_ . We then calculate the returns on the rebalancing strategy using expression (22), that is: 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0061-04.png)


**Fees.** In each minute, we compute the gross amount of each asset in the pair bought and sold. The Uniswap v2 pool has a fixed fee rate of 30bps on the contributed asset; we thus calculate fees in each asset by multiplying the gross amount contributed of each asset by 0.003. Call these fees _x_<sup>_fee_</sup> _t_ and _yt_<sup>_fee_</sup> in period _t_ . We value fees at the period _t_ price; thus, the monetary value of fees in period _t_ , which we will call ∆FEE _t_ , is: 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0061-06.png)


Note also that Uniswap v2 allows for “flash loans”, in which assets are withdrawn and returned within a single transaction. Flash loans which are accounted for simply as swaps in Uniswap v2; thus, the calculation in (44) also correctly accounts for flash loans revenues.<sup>27</sup> 

**LVR.** We compute a realized daily volatility using USDC-ETH prices from the Binance API sampled at 60 minute intervals. Let ∆LVR _t_ be the increment of LVR in period _t_ . As in Example 3, we then 

> 27See the Uniswap v2 documentation of flash swaps.

<!-- page: 62 -->

calculate ∆LVR _t_ simply as 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0062-01.png)


ˆ where _σt_ denotes the realized daily volatilty estimate for the day containing period _t_ , and ∆ _t_ = 1 _/_ (24 _×_ 60) corresponds to a one minute period. This is a discrete approximation of (23). 

**Adding everything up.** We then calculate the cumulative returns, the left side of (21), as: 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0062-04.png)


using the definitions of ∆LP P&L _t_ and ∆RB P&L _t_ in (42) and (43) respectively. Note that different rebalancing frequencies give slightly different values of for ∆RB P&L _t_ . We calculate the right side of (21) as: 


![](assets/2022-milionis-et-al-amm-lvr.pdf-0062-06.png)


using the definitions of ∆FEE _t_ and ∆LVR _t_ in (44) and (45) respectively. 

### **C.2. Dune SQL Queries** 

This appendix contains the SQL queries we use on Dune to extract Uniswap v2 WETH-USDC data. 

#### **Mints.** 

- 1 **`SELECT`** `to_char(evt_block_time , ’YYYY -MM -DD"T"HH24:MI:SSOF ’)` **`AS`** `ts , *` 2 **`FROM`** `uniswap_v2."Pair_evt_Mint"` 

- 3 **`WHERE`** `contract_address = ’\ xb4e16d0168e52d35cacd2c6185b44281ec28c9dc ’` 4 **`ORDER BY`** `evt_block_number , evt_index` **`ASC`** 

#### **Burns.** 

- 1 **`SELECT`** `to_char(evt_block_time , ’YYYY -MM -DD"T"HH24:MI:SSOF ’)` **`AS`** `ts , *` 2 **`FROM`** `uniswap_v2."Pair_evt_Burn"` 3 **`WHERE`** `contract_address = ’\ xb4e16d0168e52d35cacd2c6185b44281ec28c9dc ’` 4 **`ORDER BY`** `evt_block_number , evt_index` **`ASC`** 

#### **Trades.** 

- 1 **`SELECT`** 

- 2 `date_trunc(’minute ’, evt_block_time)` **`AS minute`** `,`

<!-- page: 63 -->

3 **`SUM`** `("amount0In")` **`as`** `"amount0In",` 4 **`SUM`** `("amount1In")` **`as`** `"amount1In",` 5 **`SUM`** `("amount0Out")` **`as`** `"amount0Out",` 6 **`SUM`** `("amount1Out")` **`as`** `"amount1Out"` 7 **`FROM`** `uniswap_v2."Pair_evt_Swap"` 8 **`WHERE`** `contract_address = ’\ xb4e16d0168e52d35cacd2c6185b44281ec28c9dc ’` 9 **`GROUP BY`** `1` 10 **`ORDER BY`** `1` **`ASC`** 

**Pool reserves.** 

1 **`SELECT`** 2 **`minute`** `,` 3 `latest_reserves [3]` **`AS`** `reserve0 ,` 4 `latest_reserves [4]` **`AS`** `reserve1` 5 **`FROM`** 6 `(` **`SELECT`** `date_trunc(’minute ’, evt_block_time)` **`AS minute`** `,` 7 `(` **`SELECT MAX`** `(ARRAY[evt_block_number , evt_index , reserve0 , reserve1 ]))` 8 **`AS`** `latest_reserves` 9 **`FROM`** `uniswap_v2."Pair_evt_Sync"` 10 **`WHERE`** `contract_address = ’\ xb4e16d0168e52d35cacd2c6185b44281ec28c9dc ’` 11 **`GROUP BY`** `1)` **`AS`** `day_reserves` 12 **`ORDER BY`** `1` **`ASC`**
