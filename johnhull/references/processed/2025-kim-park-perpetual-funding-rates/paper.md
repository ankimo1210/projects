# 2025-kim-park-perpetual-funding-rates

<!-- page: 1 -->

## Designing funding rates for perpetual futures in cryptocurrency markets

Jaehyun Kim<sup>∗</sup>and Hyungbin Park<sup>†</sup>

Department of Mathematical Sciences Seoul National University 1, Gwanak-ro, Gwanak-gu, Seoul, Republic of Korea

June 11, 2025

## Abstract

In cryptocurrency markets, a key challenge for perpetual future issuers is maintaining alignment between the perpetual future price and target value. This study addresses this challenge by exploring the relationship between funding rates and perpetual future prices. Our results demonstrate that by appropriately designing funding rates, the perpetual future price can remain aligned with the target value. We develop replicating portfolios for perpetual futures, ofering issuers an efective method to hedge their positions. Additionally, we provide path-dependent funding rates as a practical alternative and investigate the diference between the original and path-dependent funding rates. To achieve these results, our study employs path-dependent infinite-horizon BSDEs in conjunction with arbitrage pricing theory. Our main results are obtained by establishing the existence and uniqueness of solutions to these BSDEs and analyzing the large-time behavior of these solutions.

## 1 Introduction

## 1.1 Overview

Perpetual futures are among the most widely traded derivative securities in cryptocurrency markets. Since their introduction by BitMEX in 2016, they have gained immense popularity and achieved significant trading volume. Perpetual futures have accumulated over \$90 trillion in trading volume, surpassing the trading volumes of the underlying cryptocurrencies and now accounting for 93% of the cryptocurrency future markets (Ruan and Streltsov (2024)). A key aspect of perpetual futures is the funding mechanism, which operates efectively within the continuous 24/7 trading environment. This funding mechanism is more prevalent in cryptocurrency markets but is less frequently used in traditional markets due to higher transaction costs and stricter regulations. Despite the central role of funding mechanisms in perpetual futures, there has been relatively little research on this topic. Therefore, exploring its fundamentals is timely and essential to gain a better understanding of its operation.

arXiv:2506.08573v1 [q-fin.MF] 10 Jun 2025

<sup>∗</sup>jaehyun107@snu.ac.kr

<sup>†</sup>hyungbin@snu.ac.kr, hyungbin2015@gmail.com

<!-- page: 2 -->

A funding mechanism is designed to minimize price deviations between the future price and target value. Cash flows are exchanged periodically between long and short positions to ensure that the price of the perpetual future remains aligned with the target value. This cash flow, known as the funding fee, is determined by the target value and current price of the perpetual future. This study aims to construct theoretical fundamentals of perpetual futures by illuminating the relationship between funding rates and perpetual future prices. The structure of perpetual futures is similar to standard options, as the holder receives a payout in the form of a funding fee. This analogy prompts the adoption of the standard derivative pricing theory in this study.

However, compared to conventional derivatives, particularly standard European options, perpetual futures exhibit significant diferences. First, they have no expiration dates. This feature allows them to be bought or sold at any time without restrictions. Long positions in perpetual futures can be maintained for as long as desired without the concern of expiration. In contrast, standard options have a fixed expiry date, marking the last day the option contract remains valid. Second, the payment stream of perpetual futures occurs periodically throughout the contract period, whereas the payments for standard options are made only at the end of the contract. This periodic payment structure is feasible because the cryptocurrency market operates 24/7. Third, the payment stream of perpetual futures is influenced by both the underlying asset and perpetual future price, whereas standard options derive their payment solely from the underlying asset. These complexities make it challenging to apply the standard risk-neutral valuation to perpetual futures. This creates a significant distinction in pricing approaches between conventional options and perpetual futures.

This study has four contributions. First, we present a method for designing funding rates that ensures the perpetual future price remains anchored to the target values, including both tradable and non-tradable cases. This has posed a considerable challenge for perpetual future issuers due to the intricate nature of perpetual future structures. We address this problem using an arbitrage approach combined with the BSDE method. Although the problem is conceptually straightforward, providing formal and rigorous proof is complex and challenging. Notably, our study is the first to derive unique prices for perpetual futures anchored to non-tradable target values.

Second, we investigate a path-dependent funding rate for practical implementation. In most exchanges, the funding fee is calculated as the average of values over the past 8 hours rather than relying on the current spot value, making the funding rate inherently path-dependent in practice. While the instantaneous spot funding rate ideally guarantees that the perpetual future price perfectly aligns with the target values, the path-dependent version provides a more realistic and implementable approximation. Our analysis shows the perpetual future price is uniquely determined under path-dependent funding rates. Moreover, the price derived from the path dependent funding rate closely aligns with that obtained from the instantaneous spot funding rate, indicating that the practical version is an efective substitute. Notably, this specific form of path-dependent funding rate has not been studied before, making our study the first to explore this topic.

Third, this paper discusses the construction of replicating portfolios for perpetual futures. This is significant for two main reasons: practically, it provides issuers with a method to hedge perpetual futures, and theoretically, it demonstrates that the derived future price is arbitragefree. While replicating portfolios are well-established for traditional derivatives with finite horizons, the absence of a terminal date in perpetual futures complicates their construction. Our study shows that it is still possible to construct replicating portfolios even for derivatives without terminal dates.

Finally, this study employs a novel approach, an infinite-horizon BSDE method that provides new insights into perpetual futures. This methodology clarifies the funding mechanism by revealing how funding rates influence perpetual future prices. The relationship between the driver and the solution of the infinite-horizon BSDE mirrors the connection between funding rates and perpetual futures prices. Mathematically, this is achieved by proving the existence and uniqueness of solutions to the infinite-horizon BSDEs. Because such types of BSDEs have not been previously studied, this study develops new theoretical results to establish conditions for the existence and uniqueness of solutions in this context.

<!-- page: 3 -->

This study adopts a path-dependent approach for two main reasons. First, it enables working with path-dependent market models that extend beyond traditional Markovian frameworks to accommodate non-Markovian market dynamics. While most of the existing literature focuses on Markovian models, our results hold under a more general framework that includes non-Markovian settings. Second, this approach allows for the analysis of path-dependent funding rates, modeled as integrals over the past 8 hours. These observations lead to the formulation of path-dependent BSDEs, for which standard Markovian BSDE techniques are not applicable. Our analysis primarily builds upon the path-dependent framework developed by Ekren et al. (2014), Bally et al. (2016), Dupire (2019) and Viens and Zhang (2019).

The theoretical literature on the pricing of perpetual futures is scarce. He et al. (2022) considered proportional funding rates for perpetual futures anchored to a tradable asset price. They derived arbitrage-free prices for perpetual futures in frictionless markets and bounds in markets with trading costs. Angeris et al. (2023) analyzed perpetual future contracts in a continuous-time, arbitrage-free, and frictionless market, deriving model-free formulas for their funding rates, along with replication strategies, especially when asset prices are continuous and positive. They also extended these results to jump models, providing semi-robust expressions that depend on jump intensities and ofering explicit replication strategies when the volatility process is independent of the underlying risky asset. Ackerer et al. (2024) derived an arbitrage free price of various perpetual contracts, including linear, inverse, and quantos futures. The price is determined by the risk-neutral expectation of the spot, sampled at a random time that reflects the intensity of the price anchoring. Dai et al. (2025) investigated the tendency of perpetual futures prices to deviate from their underlying asset prices. They identified the clamping function in the funding mechanism as a key factor and derived model-free no-arbitrage bounds that hold even without transaction fees. Although the theoretical literature on perpetual futures is limited, several empirical studies have been conducted in this field. Refer to Alexander et al. (2020), Christin et al. (2022) and Wang and Zhang (2025).

## 1.2 Outline

A strategy for addressing this problem consists of several steps. First, we introduce the concept of funding portfolios and their associated wealth processes, establishing a fundamental theoretical framework for constructing replicating portfolios in subsequent discussions. Consider a complete market comprising multiple assets, denoted as $\boldsymbol { X } = ( X ( s ) ) _ { s \geq 0 }$ , along with a money market account. Let $\boldsymbol { F } = ( F ( s ) ) _ { s \geq 0 }$ be a given funding rate process. At this stage, we assume that F is a general stochastic process without imposing any specific structure. An F-funding portfolio consists of holdings in multiple assets and a money market account, which incurs a funding fee $F ( s )$ ds over time. The corresponding wealth process, denoted as $\boldsymbol { Y } = ( Y ( s ) ) _ { s \geq 0 }$ 2 represents the evolution of the value of the F-funding portfolio.

Second, we examine a specific type of funding rate that depends on both the wealth process and the underlying asset value. More precisely, consider a funding rate of the form $F ^ { \Phi } ( s ) : = $ $\Phi ( s , X _ { s } , Y ( s ) )$ , where Φ is a specified functional. For the meanings of $X _ { s } , Y _ { s }$ and $X ( s ) , Y ( s )$ , see Section 2. A fundamental question arises: does there exist a $F ^ { \Phi }$ -funding portfolio corresponding to the specified functional Φ? This problem is non-trivial, and to address this, we transform the problem into an infinite-horizon BSDE framework. We establish the existence and uniqueness of such $F ^ { \Phi }$ -funding portfolios by analyzing the associated infinite-horizon BSDEs. Furthermore, we characterize the wealth process of the $F ^ { \Phi }$ -funding portfolio through our BSDE analysis.

<!-- page: 4 -->

Third, we design funding rates ensuring that the perpetual future price remains aligned with the target value. Imagine an issuer seeking a perpetual future price to be aligned with $\varphi ( s , X _ { s } )$ for a given function $\varphi .$ . We verify that a specific form of funding rate $\Phi ( s , X _ { s } , Y ( s ) )$ presented in (4.1) induces a funding portfolio whose wealth process coincides with the target value $\varphi ( s , X _ { s } )$ Thus, this funding portfolio is the replicating portfolio for the perpetual future and its wealth process generates the desired prices. Consequently, this provides issuers with a solution on how to design funding rates for perpetual futures.

Fourth, we investigate a path-dependent funding rate, which ofers a practical alternative. The funding rate $\Phi ( s , X _ { s } , Y ( s ) )$ mentioned above provides the desired perpetual future prices; however, this is not practical. Instead, we consider the funding rate of the form

$$
\Phi ^ { \delta } ( s , X _ { s } , Y _ { s } ) : = \frac 1 \delta \int _ { s - \delta } ^ { s } \Phi ( u , X _ { u } , Y ( u ) ) d u
$$

for $\delta > 0$ . In practice, $\textstyle { \delta = { \frac { 1 } { 1 0 9 5 } } }$ , corresponding to 8 hours, is commonly used. We verify that there exists a $\Phi ^ { \delta } .$ -funding portfolio and derive the corresponding wealth process $Y ^ { \delta }$ . Additionally, we estimate the diference between $Y ^ { \delta }$ derived from this path-dependent funding rate and $Y$ derived from the original funding rate Φ.

To illustrate the core idea of this study, we examine the following simple example. Consider an uncorrelated m-dimensional Black-Scholes stock model with zero short rate. Under the risk-neutral measure, the stock price process $X = ( X _ { 1 } ( s ) , \ldots , X _ { m } ( s ) ) _ { s \geq 0 }$ evolves according to

$$
d X _ { i } ( s ) = \sigma _ { i } X _ { i } ( s ) d B _ { i } ( s ) , \quad i = 1 , 2 , \ldots , m ,
$$

where $\sigma _ { i } > 0$ for all $i = 1 , 2 , \dots , m$ , and $( B _ { 1 } ( s ) , \dots , B _ { m } ( s ) ) _ { s \geq 0 }$ is an m-dimensional Brownian motion with uncorrelated components. Suppose an issuer seeks to design funding rates for a perpetual future whose price process Y remains aligned with the square of the first stock’s price, i.e., $Y ( s ) = \varphi ( X ( s ) )$ for $s \geq 0$ , where $\varphi ( x ) = x _ { 1 } ^ { 2 }$ for $x = ( x _ { 1 } , \ldots , x _ { m } ) \in \mathbb { R } ^ { m }$ . For the moment, assume that the funding rate depends only on the current stock prices. Specifically, we set $F ( s ) = \Phi ( X ( s ) )$ for some function $\Phi \in C ^ { 2 } ( \mathbb { R } ^ { m } )$ . The wealth process from holding one perpetual future is

$$
Y ( s ) + \int _ { 0 } ^ { s } F ( u ) d u = \varphi ( X ( s ) ) + \int _ { 0 } ^ { s } \Phi ( X ( u ) ) d u = X _ { 1 } ^ { 2 } ( s ) + \int _ { 0 } ^ { s } \Phi ( X ( u ) ) d u , s \geq 0 .
$$

By the standard no-arbitrage principle, any wealth process must be a local martingale under the risk-neutral measure. Applying this principle, we obtain $\begin{array} { r } { \Phi ( x ) = - \frac { 1 } { 2 } \sigma _ { 1 } ^ { 2 } x _ { 1 } ^ { 2 } \partial _ { x _ { 1 } x _ { 1 } } \varphi = - \sigma _ { 1 } ^ { 2 } x _ { 1 } ^ { 2 } } \end{array}$ Therefore, the appropriate funding rate for the perpetual future $X _ { 1 } ^ { 2 }$ is $\Phi \bar { ( \cal X ( s ) ) } = - \sigma _ { 1 } ^ { 2 } { \cal X } _ { 1 } ^ { 2 } ( s )$ for $s \geq 0$

However, an important observation is that this funding rate does not uniquely determine the futures price. For instance, processes such as $Y = 2 X _ { 1 } + X _ { 1 } ^ { 2 }$ and $Y = X _ { 2 } + 2 X _ { m } + X _ { 1 } ^ { 2 }$ also serve as perpetual futures prices consistent with the same funding rate. This implies that the given rate allows for multiple arbitrage-free prices. To resolve this non-uniqueness, we introduce an additional term of the form $\ell ( X _ { 1 } ^ { 2 } ( s ) - Y ( s ) )$ for suficiently large $\ell > 0$ . The modified funding rate

$$
\Phi ( X ( s ) , Y ( s ) ) = \ell ( X _ { 1 } ^ { 2 } ( s ) - Y ( s ) ) - \sigma _ { 1 } ^ { 2 } X _ { 1 } ^ { 2 } ( s ) , s \geq 0
$$

enforces a unique perpetual futures price within a suitable class of admissible processes. Moreover, this unique price aligns with the target value $Y ( s ) = X _ { 1 } ^ { 2 } ( s )$ for $s \geq 0$ . This modification is the core idea of the approach developed in this paper. We later provide a rigorous justification for why the additional term guarantees the uniqueness of the perpetual futures price.

<!-- page: 5 -->

The remainder of this paper is organized as follows. Section 2 introduces the basic notations for path-dependent SDEs and PDEs as preliminary concepts. In Section 3, we analyze funding portfolios and their corresponding wealth processes. Section 4 presents instantaneous spot funding rates as well as path-dependent funding rates. Section 5 discusses several applications, and Section 6 concludes with a summary of the main findings. The proofs of the main results are presented in the appendices.

## 2 Preliminary

In this section, we introduce basic notations of path-dependent SDEs and PDEs as preliminaries. The reader may refer to Ekren et al. (2014), Bally et al. (2016), Dupire (2019) and Viens and Zhang (2019) for more details. Throughout this study, let $( \Omega , \mathcal { F } , \mathbb { P } )$ be a complete probability space having a m-dimensional Brownian motion W. The augmented σ-algebra generated by W is denoted as $( \mathcal { F } _ { s } ) _ { s \geq 0 }$ . Let $\mathbb { L } ^ { 0 } ( \mathbb { R } ^ { m } )$ be the space of all progressively measurable processes taking values in $\mathbb { R } ^ { m }$ . For $p > 0$ and $T > 0$ , we define

$L ^ { p } ( \mathcal { F } _ { s } ; \mathbb { R } ^ { m } ) = \{ \boldsymbol { \xi } : \Omega \mathbb { R } ^ { m } \mid \boldsymbol { \xi }$ is a $\mathcal { F } _ { s } .$ -measurable random variable and $\mathbb { E } [ | \xi | ^ { p } ] < \infty \}$

$\mathbb { S } ^ { p } ( 0 , T ; \mathbb { R } ^ { m } ) = \left\{ X \in \mathbb { L } ^ { 0 } ( \mathbb { R } ^ { m } ) | X \right.$ is continuous in time and $\mathbb { E } [ \| X \| _ { T } ^ { p } ] < \infty \}$

$$
\mathbb { H } ^ { p } ( 0 , T ; \mathbb { R } ^ { m } ) = \Bigl \{ Z \in \mathbb { L } ^ { 0 } ( \mathbb { R } ^ { m } ) \Big | \mathbb { E } \Big [ \Big ( \int _ { 0 } ^ { T } | Z ( u ) | ^ { 2 } d u \Big ) ^ { \frac { p } { 2 } } \Big ] < \infty \Bigr \} ,
$$

$$
\mathbb { S } ^ { p } ( 0 , \infty ; \mathbb { R } ^ { m } ) = \cap _ { T > 0 } \mathbb { S } ^ { p } ( 0 , T ; \mathbb { R } ^ { m } ) ,
$$

$$
\mathbb H ^ { p } ( 0 , \infty ; \mathbb R ^ { m } ) = \cap _ { T > 0 } \mathbb H ^ { p } ( 0 , T ; \mathbb R ^ { m } ) .
$$

The spaces $\mathbb { S } ^ { p } ( s , T ; \mathbb { R } ^ { m } ) , \mathbb { H } ^ { p } ( s , T ; \mathbb { R } ^ { m } ) , \mathbb { S } ^ { p } ( s , \infty ; \mathbb { R } ^ { m } )$ and $\mathbb { H } ^ { p } ( s , \infty ; \mathbb { R } ^ { m } )$ are similarly defined for $s \in [ 0 , T ]$

Let $\hat { \boldsymbol { \Lambda } } : = \mathbb { D } ( [ 0 , \infty ) , \mathbb { R } ^ { m } )$ be the space of all c´adl´ag functions from $[ 0 , \infty )$ to $\mathbb { R } ^ { m }$ . For $\gamma \in \hat { \Lambda }$ denote by $\gamma ( s )$ the value of $\gamma$ at time s and by $\gamma _ { s } = \gamma ( s \wedge \cdot )$ the path of $\gamma$ stopped at time s. Define a seminorm $\Vert \cdot \Vert _ { T }$ and norm $\| \cdot \|$ on $\hat { \Lambda }$ and a pseudometric d on $[ 0 , \infty ) \times \hat { \Lambda }$ as

$$
\begin{array} { r l } & { \| \gamma \| _ { T } = \operatorname* { s u p } \{ | \gamma ( s ) | : s \in [ 0 , T ] \} , T \geq 0 , } \\ & { \| \gamma \| = \displaystyle \sum _ { n = 1 } ^ { \infty } \frac { 1 } { 2 ^ { n } } ( \| \gamma \| _ { n } \wedge 1 ) , } \\ & { d ( ( s , \gamma ) , ( s ^ { \prime } , \gamma ^ { \prime } ) ) = | s - s ^ { \prime } | + \displaystyle \operatorname* { s u p } _ { r \in [ 0 , s \vee s ^ { \prime } ] } \left| \gamma ( r \wedge s ) - \gamma ^ { \prime } ( r \wedge s ^ { \prime } ) \right| . } \end{array}\tag{2.1}
$$

We write as $\| \gamma \| \leq \| \gamma ^ { \prime } \|$ for $\gamma , \gamma ^ { \prime } \in \hat { \Lambda }$ if $\| \gamma \| _ { T } \leq \| \gamma ^ { \prime } \| _ { T }$ for all $T \geq 0$ . For c´adl´ag processes $X$ and $X ^ { \prime } ,$ the meanings of $X ( s ) , X _ { s } , \| X \| _ { T } , \| X \| \leq \| X ^ { \prime } \|$ are straightforward.

A map $\varphi : [ 0 , \infty ) \times { \hat { \Lambda } } $ R is called a non-anticipative functional if $\varphi ( s , \gamma ) = \varphi ( s , \gamma _ { s } )$ for all $( s , \gamma ) \in [ 0 , \infty ) \times \hat { \Lambda }$ . A non-anticipative functional $\varphi$ is said to have polynomial growth of order $p$ at most if there exists a constant $L > 0$ such that $| \varphi ( s , \gamma ) | \leq L ( 1 + \| \gamma \| _ { s } ^ { p } )$ for all $( s , \gamma ) \in [ 0 , \infty ) \times \hat { \Lambda }$ The constant $p$ is referred to as the polynomial growth order of $\varphi$ . We say a non-anticipative functional $\varphi$ is horizontally diferentiable (vertically diferentiable, respectively) at $( s , \gamma )$ if the limit

$$
\partial _ { s } \varphi ( s , \gamma ) : = \operatorname* { l i m } _ { h \to 0 ^ { + } } { \frac { \varphi ( s + h , \gamma _ { s } ) - \varphi ( s , \gamma _ { s } ) } { h } }
$$

exists (if for $i = 1 , \cdots , m$ , the limit

$$
\partial _ { i } \varphi ( s , \gamma ) : = \operatorname* { l i m } _ { h \to 0 } \frac { \varphi ( s , \gamma _ { s } + h e _ { i } \mathbf { 1 } _ { [ s , \infty ) } ) - \varphi ( s , \gamma _ { s } ) } { h }
$$

<!-- page: 6 -->

exists where $( e _ { i } ) _ { 1 \leq i \leq m }$ represents the standard basis of $\mathbb { R } ^ { m }$ , respectively). We denote as $\partial _ { x } \varphi ( s , \gamma ) =$ $( \partial _ { i } \varphi ( s , \gamma ) ) _ { 1 \leq i \leq m }$ and $\partial _ { x x } ^ { 2 } \varphi ( s , \gamma ) = ( \partial _ { i } ( \partial _ { j } \varphi ) ( s , \gamma ) ) _ { 1 \leq i , j \leq m }$ . For $p \geq 1$ , we define the spaces

$\boldsymbol { A } ( [ 0 , \infty ) \times \hat { \boldsymbol { \Lambda } } ) = \{ \varphi : [ 0 , \infty ) \times \hat { \boldsymbol { \Lambda } } \to \mathbb { R } | \varphi$ is non-anticipative} ,

$C ( [ 0 , \infty ) \times \hat { \Lambda } ) = \{ \varphi \in \mathcal { A } ( [ 0 , \infty ) \times \hat { \Lambda } ) | \varphi$ is continuous with respect to $d \}$

$C _ { p } ( [ 0 , \infty ) \times \hat { \Lambda } ) = \{ \varphi \in C ( [ 0 , \infty ) \times \hat { \Lambda } ) | \varphi$ has polynomial growth of order $p \}$

$$
C _ { p } ^ { 1 , 2 } ( [ 0 , \infty ) \times \hat { \Lambda } ) = \left\{ \varphi \in C ( [ 0 , \infty ) \times \hat { \Lambda } ) | \partial _ { s } \varphi , \partial _ { x } \varphi , \partial _ { x x } ^ { 2 } \varphi \mathrm { ~ e x i s t ~ a n d ~ a r e ~ i n ~ } C _ { p } ( [ 0 , \infty ) \times \hat { \Lambda } ) \right\}\tag{2.2}
$$

Let $\Lambda : = C ( [ 0 , \infty ) ; \mathbb { R } ^ { m } )$ be the space of all continuous functions from $[ 0 , \infty )$ to $\mathbb { R } ^ { m }$ . Because $\Lambda \subset { \hat { \Lambda } }$ and $[ 0 , \infty ) \times \Lambda \subset [ 0 , \infty ) \times \hat { \Lambda }$ , the seminorm $\| \cdot \| _ { T } , \operatorname { n o r m } \| \cdot \|$ , and pseudometric d defined in $( 2 . 1 )$ are inherited. It can be easily checked that Λ and $[ 0 , \infty ) \times \Lambda$ are closed subspaces of $\hat { \Lambda }$ and $[ 0 , \infty ) \times \hat { \Lambda }$ , respectively. Three spaces $\mathcal { A } ( [ 0 , \infty ) \times \Lambda ) , C ( [ 0 , \infty ) \times \Lambda ) , C _ { p } ( [ 0 , \infty ) \times \Lambda )$ are defined similarly to (2.2) and $C _ { p } ^ { 1 , 2 } ( [ 0 , \infty ) \times \Lambda )$ is defined as the space of all processes $\varphi \in \mathcal { A } ( [ 0 , \infty ) \times \Lambda )$ such that there exists $\hat { \varphi } \in \mathring { C } _ { p } ^ { 1 , 2 } ( [ 0 , \infty ) \times \hat { \Lambda } )$ satisfying $\varphi ( s , \gamma ) = \hat { \varphi } ( s , \gamma )$ for all $( s , \gamma ) \in [ 0 , \infty ) \times \Lambda$ We denote $\partial _ { s } \varphi : = \partial _ { s } \hat { \varphi } , \partial _ { x } \varphi : = \partial _ { x } \hat { \varphi } , \partial _ { x x } ^ { 2 } \varphi : = \partial _ { x x } ^ { 2 } \hat { \varphi }$ . By Cont and Fourni´e (2013), the derivatives $\partial _ { s } \varphi , \partial _ { x } \varphi , \partial _ { x x } ^ { 2 } \varphi$ do not depend on the choice of $\hat { \varphi }$

## 3 Pricing perpetual futures

## 3.1 Funding portfolios

Consider a market with $m + 1$ assets consisting of m wealth processes, such as stocks, golds, cryptocurrencies and their linear combinations given as a solution to the path-dependent SDE

$$
X ( s ) = x + \int _ { 0 } ^ { s } \mu ( u , X _ { u } ) d u + \int _ { 0 } ^ { s } \sigma ( u , X _ { u } ) d W ( u ) \mathrm { f o r } s \geq 0\tag{3.1}
$$

for $x \in \mathbb { R } ^ { m }$ and non-anticipative functionals $\mu : [ 0 , \infty ) \times \Lambda \to \mathbb { R } ^ { m } , \sigma : [ 0 , \infty ) \times \Lambda \to \mathbb { R } ^ { m \times m }$ , and a money market account $G = ( e ^ { \int _ { 0 } ^ { s } r ( u , X _ { u } ) d u } ) _ { s \geq 0 }$ for a non-anticipative functional $r : [ 0 , \infty ) \times \Lambda $ R. Our wealth process model encompasses negative value scenarios, including short positions in certain assets, linear combinations of multiple assets, and the event of negative oil prices (Corbet et al. (2021)). In numerous asset market models, the short rate is typically assumed to be constant rather than a functional of asset values. However, this study models the short rate as a functional dependent on asset values to generalize the market framework.

Assumption 3.1. The non-anticipative functionals µ and σ satisfy the following conditions.

(i) There exists a constant $C _ { 1 } > 0$ such that $| \mu ( s , 0 ) | + | \sigma ( s , 0 ) | \le C _ { 1 } \ f o r \ s \in [ 0 , \infty )$

(ii) There exists constants $C _ { 2 } , C _ { 3 } > 0$ such that

$$
\begin{array} { r l } & { | \mu ( s , \gamma ) - \mu ( s ^ { \prime } , \gamma ^ { \prime } ) | \leq C _ { 2 } d ( ( s , \gamma ) , ( s ^ { \prime } , \gamma ^ { \prime } ) ) , } \\ & { | \sigma ( s , \gamma ) - \sigma ( s ^ { \prime } , \gamma ^ { \prime } ) | \leq C _ { 3 } d ( ( s , \gamma ) , ( s ^ { \prime } , \gamma ^ { \prime } ) ) } \end{array}
$$

$$
f o r \ ( s , \gamma ) , ( s ^ { \prime } \gamma ^ { \prime } ) \in [ 0 , \infty ) \times \Lambda .
$$

Assumption 3.2. The short rate functional $r : [ 0 , \infty ) \times \Lambda \to \mathbb { R }$ is bounded. More precisely, there exists a constant $C _ { r } > 0$ such that $| r ( s , \gamma ) | \leq C _ { r }$ for all $( s , \gamma ) \in [ 0 , \infty ) \times \Lambda$

The following theorem states the existence and uniqueness of solutions to the SDE (3.1). For the proof, refer to (Protter, 2005, Theorem 7, Chapter 5).

Theorem 3.1. Let Assumption 3.1 hold and $p \geq 1$ . Then, for any $x \in \mathbb { R } ^ { m }$ , there exists a unique solution X to the SDE (3.1) in $\mathbb { S } ^ { p } ( 0 , \infty ; \mathbb { R } ^ { m } )$

<!-- page: 7 -->

A portfolio is a $m + 1$ dimensional progressively measurable process $h = ( \phi ^ { 0 } ( s ) , \phi ( s ) ) _ { s \geq 0 } =$ $( \phi ^ { 0 } ( s ) , \cdot \cdot \cdot , \phi ^ { m } ( s ) ) _ { s \geq 0 }$ with its value process $V ^ { h } ( s ) : = \phi ^ { 0 } ( s ) G ( s ) + \phi ( s ) X ( s )$ for $s \geq 0$

Definition 3.1. Let $\boldsymbol { F } = ( F ( s ) ) _ { s \geq 0 }$ be a progressively measurable process.

(i) We say a portfolio $h = ( \phi ^ { 0 } ( s ) , \phi ( s ) ) _ { s \geq 0 }$ is a F-funding portfolio if $\phi ^ { 0 }$ and $F$ are locally integrable and ϕ is locally square-integrable with respect to the Lebesgue measure on $[ 0 , \infty )$ almost surely and if

$$
d { \cal V } ^ { h } ( s ) = \phi ^ { 0 } ( s ) d G ( s ) + \phi ( s ) d X ( s ) - F ( s ) d s .
$$

(ii) For $\rho \geq 1$ , we say a portfolio h is ρ-admissible if there exists a constant $L > 0$ such that $\| V ^ { h } \| _ { T } \leq L ( 1 + \| X \| _ { T } ^ { \rho } )$ for all $T \geq 0$

This definition is similar to the consumption portfolio in the standard investment-consumption portfolio theory. In particular, when $F = 0$ , this portfolio h is self-financing. The local integrability condition is a technical requirement that guarantees the well-definedness of Lebesgue integrals and Itˆo integrals. The ρ-admissibility indicates that the value process is bounded above by a positive constant multiple of the $\rho \mathrm { - t h }$ power of the underlying wealth process.

We now describe fundamental concepts of perpetual future prices and funding rate functionals.

Definition 3.2. Let $\boldsymbol { F } = ( F ( s ) ) _ { s \geq 0 }$ be a progressively measurable process.

(i) A perpetual future with funding rate F is a financial instrument where the short position pays the funding fee $F ( s )$ ds to the long position continuously until the contract is terminated. Denote the price of this perpetual future as $Y = ( Y ( s ) ) _ { s \geq 0 }$

(ii) A perpetual future Y with funding rate F is said to be replicable if there exists a F-funding portfolio h such that $Y = V ^ { h }$

In cases where the funding rate is negative, the short position pays $F ( s )$ ds to the long position, indicating that the short position receives − $- F ( s )$ ds from the long position.

We can express the value process of F-funding portfolio as an infinite-horizon BSDE for a given funding rate F. Observe that a F-funding portfolio $h = ( \phi ^ { 0 } ( s ) , \phi ( s ) ) _ { s \geq 0 }$ satisfies

$$
\begin{array} { l } { d V ^ { h } ( s ) = \phi ^ { 0 } ( s ) d G ( s ) + \phi ( s ) d X ( s ) - F ( s ) d s } \\ { = ( r ( s , X _ { s } ) ( V ^ { h } ( s ) - \phi ( s ) X ( s ) ) + \phi ( s ) \mu ( s , X _ { s } ) - F ( s ) ) d s + \phi ( s ) \sigma ( s , X _ { s } ) d W ( s ) } \\ { = ( r ( s , X _ { s } ) V ^ { h } ( s ) + Z ( s ) \theta ( X _ { s } ) - F ( s ) ) d s + Z ( s ) d W ( s ) } \end{array}
$$

where $\theta ( s , X _ { s } ) : = \sigma ^ { - 1 } ( s , X _ { s } ) ( \mu ( s , X _ { s } ) - X ( s ) r ( s , X _ { s } ) )$ and $Z ( s ) : = \phi ( s ) \sigma ( s , X _ { s } )$ for $s \geq 0$ Defining $Y ( s ) = V ^ { h } ( s )$ , we have

$$
Y ( s ) = Y _ { T } - \int _ { s } ^ { T } ( r ( u , X _ { u } ) Y ( u ) + Z ( u ) \theta ( u , X _ { u } ) - F ( u ) ) d u - \int _ { s } ^ { T } Z ( u ) d W ( u )\tag{3.2}
$$

for $0 \leq s \leq T <$ ∞ in the infinite-horizon BSDE form.

We mainly work with funding rates that depend on both the m wealth processes X and the perpetual future price Y. Typical funding rates traded in the cryptocurrency market follow this form.

Definition 3.3. If a funding rate is expressed as $F ( s ) \ : = \ : \Phi ( s , X _ { s } , Y ( s ) ) , s \geq 0$ for a nonanticipative functional $\Phi : [ 0 , \infty ) \times \Lambda \times \mathbb { R } \to \mathbb { R }$ , then we refer to Φ as the funding rate functional and denote the corresponding funding rate by $F ^ { \Phi }$

<!-- page: 8 -->

The first objective is to verify that for any appropriate funding rate functional $\Phi _ { ; }$ there exists a unique $F ^ { \Phi }$ -funding portfolio. If the funding rate functional $\Phi = \Phi ( s , X _ { s } )$ is independent of $Y$ proving the existence and uniqueness of $F ^ { \Phi }$ -funding portfolios becomes relatively straightforward. However, if Φ depends on $Y .$ , this is not immediately clear; the formal and rigorous proof is complex and challenging. We address this problem by formulating it as an infinite-horizon BSDE. With a funding rate functional $\Phi : [ 0 , \infty ) \times \Lambda \times \mathbb { R } \to \mathbb { R }$ , it follows that

$$
Y ( s ) = Y _ { T } - \int _ { s } ^ { T } ( r ( u , X _ { u } ) Y ( u ) + Z ( u ) \theta ( u , X _ { u } ) - \Phi ( u , X _ { u } , Y ( u ) ) ) d u - \int _ { s } ^ { T } Z ( u ) d W ( u )\tag{3.3}
$$

for $0 \leq s \leq T < \infty$ in the infinite-horizon BSDE form. Consequently, the existence and uniqueness of $F ^ { \Phi }$ -funding portfolios is equivalent to the existence and uniqueness of solutions to the infinite-horizon BSDE above.

## 3.2 Risk-neutral pricing BSDEs

We now introduce risk-neutral measures and demonstrate how funding portfolios are expressed using the risk-neutral measure.

Assumption 3.3. The matrix σ is invertible and the local martingale

$$
\begin{array} { r } { ( e ^ { - \int _ { 0 } ^ { s } \theta ( u , X _ { u } ) d W ( u ) - \frac { 1 } { 2 } \int _ { 0 } ^ { s } | \theta ( u , X _ { u } ) | ^ { 2 } d u } ) _ { s \geq 0 } } \end{array}
$$

is a martingale.

We define a risk-neutral measure by the Girsanov theorem under this assumption. For $s \geq 0$ let $\mathbb { Q } _ { s }$ be a probability measure on $\mathcal { F } _ { s }$ defined as

$$
\frac { d \mathbb { Q } _ { s } } { d \mathbb { P } } = e ^ { - \int _ { 0 } ^ { s } \theta ( X _ { u } ) d W ( u ) - \frac { 1 } { 2 } \int _ { 0 } ^ { s } \theta ^ { 2 } ( X _ { u } ) d u } .
$$

We can extend this to the sigma-algebra $\mathcal { F } = \sigma ( \cup F _ { s } , s \ge 0 )$ by (Deuschel and Stroock, 1989, Section 5.3). It is evident that $\mathbb { P }$ and $\mathbb { Q } _ { s }$ are equivalent for all $s \geq 0$ and $X ^ { i } / G$ is a martingale for all $i = 1 , 2 , \cdots , m$ . From the Girsanov theorem, the process

$$
B ( s ) = W ( s ) + \int _ { 0 } ^ { s } \theta ( u , X _ { u } ) d u , s \geq 0
$$

is a Brownian motion under the measure $\mathbb { Q } .$ Using this Brownian motion $B ,$ the Q-dynamics of the wealth processes X is expressed as

$$
X ( s ) = x + \int _ { 0 } ^ { s } r ( u , X _ { u } ) X ( u ) d u + \int _ { 0 } ^ { s } \sigma ( u , X _ { u } ) d B ( u ) , s \geq 0 .\tag{3.4}
$$

and the infinite-horizon BSDE (3.2) becomes

$$
Y ( s ) = Y _ { T } - \int _ { s } ^ { T } ( r ( u , X _ { u } ) Y ( u ) - F ( u ) ) d u - \int _ { s } ^ { T } Z ( u ) d B ( u )\tag{3.5}
$$

for $0 \leq s \leq T < \infty$ . For convenience, we use the notation E for $\mathbb { E } ^ { \mathbb { Q } }$ throughout this study without ambiguity.

Analyzing the infinite-horizon BSDE (3.3) becomes more straightforward when conducted under the risk-neutral measure. It follows that

$$
Y ( s ) = Y ( T ) - \int _ { s } ^ { T } ( r ( u , X _ { u } ) Y ( u ) - \Phi ( u , X _ { u } , Y ( u ) ) ) d u - \int _ { s } ^ { T } Z ( u ) d B ( u )\tag{3.6}
$$

<!-- page: 9 -->

for $0 \leq s \leq T < \infty$ . We refer to this as the risk-neutral pricing BSDE for the perpetual future. As mentioned above, the existence and uniqueness of $F ^ { \Phi }$ -funding portfolios is equivalent to the existence and uniqueness of solutions to this risk-neutral pricing BSDE. Theorem 3.2 states that under Assumptions $3 . 1 \textrm { - } 3 . 4 $ , this BSDE has a unique solution $( Y , Z ) = ( Y ( s ) , Z ( s ) ) _ { s \geq 0 }$ , thereby implying the existence and uniqueness of $F ^ { \Phi }$ -funding portfolios.

We state several conditions on the driver to guarantee the existence and uniqueness of solutions to the risk-neutral pricing BSDE. To precisely determine the constant $M _ { \rho \vee 2 }$ stated in Assumption 3.4 (v), we recall the BDG inequality. For any $q \geq 1$ , there exist positive constants $m _ { q }$ and $M _ { q }$ such that

$$
m _ { q } \mathbb { E } \Big [ \Big ( \int _ { 0 } ^ { T } | \eta ( u ) | ^ { 2 } d u \Big ) ^ { \frac { q } { 2 } } \Big ] \leq \mathbb { E } \Big [ \operatorname* { s u p } _ { 0 \leq s \leq T } \Big | \int _ { 0 } ^ { s } \eta ( u ) d B ( u ) \Big | ^ { q } \Big ] \leq M _ { q } \mathbb { E } \Big [ \Big ( \int _ { 0 } ^ { T } | \eta ( u ) | ^ { 2 } d u \Big ) ^ { \frac { q } { 2 } } \Big ]\tag{3.7}
$$

for all $T \geq 0$ and $\eta \in \mathbb { H } ^ { q } ( 0 , T ; \mathbb { R } ^ { m } )$

Assumption 3.4. Let $\Phi : [ 0 , \infty ) \times \Lambda \times \mathbb { R } \to \mathbb { R }$ be a non-anticipative functional and define $f ( s , \gamma , y ) : = - r ( s , \gamma ) y + \Phi ( s , \gamma , y )$ for $s \in [ 0 , \infty ) , \gamma \in \Lambda , y \in \mathbb { R }$ . Assume the function f satisfies the following conditions.

(i) The function f is continuous and non-anticipative.

(ii) There are constants $C _ { 4 } > 0$ and $\rho \geq 1$ such that

$$
| f ( s , \gamma , 0 ) | \leq C _ { 4 } ( 1 + \| \gamma \| _ { s } ^ { \rho } )
$$

for all $( s , \gamma ) \in [ 0 , \infty ) \times \Lambda$

(iii) The function f is Lipschitz in y, uniformly in $( s , \gamma )$

(iv) There exists a constant $\ell > 0$ such that

$$
( y - y ^ { \prime } ) ( f ( s , \gamma , y ) - f ( s , \gamma , y ^ { \prime } ) ) \leq - \ell | y - y ^ { \prime } | ^ { 2 }
$$

for all $\gamma \in \Lambda , \ : y , y ^ { \prime } \in \mathbb { R }$

(v) $\begin{array} { r } { \ell > \operatorname* { i n f } _ { K > 0 } ( K + \frac { 1 } { 2 } ( \frac { C _ { r } } { \sqrt { 2 K } } + M _ { \rho \vee 2 } C _ { 3 } ) ^ { 2 } ) \rho , } \end{array}$ where $M _ { \rho \vee 2 }$ represents the constant in the BDG inequality.

The following theorem indicates that if the function f meets certain conditions, then the perpetual future with funding rate $( \Phi ( s , X _ { s } , Y ( s ) ) _ { s \geq 0 }$ can be replicated, that is, there exists a unique $F ^ { \Phi } .$ -funding portfolio. The proof of the following theorem is stated in Appendix A.

Theorem 3.2. Let Assumptions $3 . 1 \textrm { - } 3 . 4 $ hold and ρ be the constant in Assumption $\ 3 . 4 \cdot$ Then, the BSDE (3.6) has a unique solution $( Y , Z )$ in $\mathbb { S } ^ { 2 } ( 0 , \infty ; \mathbb { R } ) \times \mathbb { H } ^ { 2 } ( 0 , \infty ; \mathbb { R } ^ { m } )$ such that $\| Y \| \leq$ $L ( 1 + \| X \| ^ { \rho } )$ for some constant $L > 0$

Note that our methodology difers from the standard derivative pricing framework. In the traditional approach, derivatives with a fixed terminal date are priced using a risk-neutral mea sure, with replicating portfolios derived via the martingale representation theorem. However, this standard method is not applicable to perpetual futures, which lack a fixed terminal date. Instead, we transform the problem into an infinite-horizon BSDE and establish the existence and uniqueness of its solutions. Notably, without introducing risk-neutral measures, the BSDE (3.3) can be analyzed directly under the physical measure; however, this involves more complex analysis and is valid under more restrictive conditions. The risk-neutral measure introduced here is employed to simplify the BSDE and facilitate the straightforward proofs of the existence and uniqueness of solutions.

We now examine the Feynman-Kac formula in the context of path-dependent infinite-horizon BSDEs and the corresponding path-dependent PDEs (PPDEs). Appendix B provides the definition of viscosity solutions for PPDEs and the proof of the following theorem.

<!-- page: 10 -->

Theorem 3.3. Let Assumptions 3.1-3.4 hold and let $\rho$ be the constant in Assumption $\ 3 . 4 \cdot$ Assume further that the mapping $( s , \gamma ) \mapsto r ( s , \gamma ) \gamma ( s )$ is Lipschitz continuous. For $( s , \gamma ) \in$ $[ 0 , \infty ) \times \Lambda$ , let $X ^ { s , \gamma }$ be a solution to

$$
X ^ { s , \gamma } ( v ) = \gamma ( s ) + \int _ { s } ^ { v } r ( u , X _ { u } ^ { t , \gamma } ) X ^ { t , \gamma } ( u ) d u + \int _ { s } ^ { v } \sigma ( u , X _ { u } ^ { t , \gamma } ) d B ( u ) , \quad v \geq s ,\tag{3.8}
$$

$$
X ^ { s , \gamma } ( v ) = \gamma ( v ) \ , \quad 0 \leq v \leq s .
$$

(i) The infinite-horizon BSDE

$$
\begin{array} { c } { { Y ^ { s , \gamma } ( v ) = Y ^ { s , \gamma } ( T ) + \displaystyle \int _ { v } ^ { T } f ( u , X _ { u } ^ { s , \gamma } , Y ^ { s , \gamma } ( u ) ) d u } } \\ { { - \displaystyle \int _ { v } ^ { T } Z ^ { s , \gamma } ( u ) d B ( u ) , s \le v \le T < \infty } } \end{array}\tag{3.9}
$$

has a unique solution $( Y ^ { s , \gamma } , Z ^ { s , \gamma } )$ in $\mathbb { S } ^ { 2 } ( s , \infty ; \mathbb { R } ) \times \mathbb { H } ^ { 2 } ( s , \infty ; \mathbb { R } ^ { m } )$ such that $\| Y ^ { s , \gamma } \| \leq L ( 1 +$ $\| X ^ { s , \gamma } \| ^ { \rho } )$ for some constant $L > 0$

(ii) Define a function $\varphi : [ 0 , \infty ) \times \Lambda \to \mathbb { R } \ a s \ \varphi ( s , \gamma ) = Y ^ { s , \gamma } ( s )$ , then $Y ^ { 0 , x } ( s ) = \varphi ( s , X _ { s } ^ { 0 , x } )$ for all $x \in \mathbb { R } ^ { m }$ . Then $\varphi$ is continuous and is a viscosity solution to the PPDE

$$
- \partial _ { s } \varphi ( s , \gamma ) - \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \varphi ) ( s , \gamma ) - r ( s , \gamma ) \partial _ { x } \varphi ( s , \gamma ) \gamma ( s ) - f ( s , \gamma , \varphi ( s , \gamma ) ) = 0 .\tag{3.10}
$$

(iii) Suppose $\varphi \in C _ { \rho } ^ { 1 , 2 } ( [ 0 , \infty ) \times \Lambda )$ is a solution to the PPDE

$$
- \partial _ { s } \varphi ( s , \gamma ) - \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \varphi ) ( s , \gamma ) - r ( s , \gamma ) \partial _ { x } \varphi ( s , \gamma ) \gamma ( s ) - f ( s , \gamma , \varphi ( s , \gamma ) ) = 0 .
$$

Then we have $( Y ^ { 0 , x } , Z ^ { 0 , x } ) = ( \varphi ( s , X _ { s } ^ { 0 , x } ) , \sigma ^ { \top } \partial _ { x } \varphi ( s , X _ { s } ^ { 0 , x } ) ) _ { s \geq 0 }$ for all $x \in \mathbb { R } ^ { m }$

## 4 Designing funding rates

In this section, we address key questions related to the funding mechanism. Consider an issuer seeking to maintain the perpetual future price in alignment with a target value $\varphi ( s , X _ { s } )$ . A common example is $\begin{array} { r } { \varphi ( s , \gamma ) = \varphi ( s , \gamma _ { 1 } , \cdot \cdot \cdot , \gamma _ { m } ) = c _ { 0 } + \sum _ { i = 1 } ^ { m } c _ { i } \gamma _ { i } ( s ) } \end{array}$ for $c _ { 0 } , c _ { 1 } , \cdots , c _ { m } \in \mathbb { R }$ , which represents an index of composite assets. Additional examples are provided in Section 5. We emphasize that the target value $\varphi ( s , X _ { s } )$ is not necessarily tradable. The central question is how to design the funding rate to ensure that the perpetual future price remains consistent with the desired process $\varphi ( s , X _ { s } )$ . In this section, we provide an answer to that question for any given $p \geq 1$ and $\varphi \in C _ { p } ^ { 1 , 2 } ( [ 0 , \infty ) \times \Lambda )$

## 4.1 Instantaneous spot funding rates

We analyze instantaneous spot funding rates, an ideal mechanism for keeping the perpetual future price aligned with the specified target values.

Assumption 4.1. Suppose that a function $H : \mathbb { R } ^ { 2 } \mathbb { R }$ satisfies the following conditions.

(i) $H ( y _ { 1 } , y _ { 2 } ) = 0 \ i f y _ { 1 } = y _ { 2 } ,$

(ii) The function H is Lipschitz in $y _ { 2 }$ , uniformly in $y _ { 1 }$ .

(iii) There exists a constant $\ell > 0$ such that

$$
( y _ { 2 } - y _ { 2 } ^ { \prime } ) ( H ( y _ { 1 } , y _ { 2 } ) - H ( y _ { 1 } , y _ { 2 } ^ { \prime } ) ) \leq - \ell | y _ { 2 } - y _ { 2 } ^ { \prime } | ^ { 2 }
$$

for all $y _ { 1 } , y _ { 2 } , y _ { 2 } ^ { \prime } \in \mathbb { R }$

<!-- page: 11 -->

For any $p \geq 1$ and $\varphi \in C _ { p } ^ { 1 , 2 } ( [ 0 , \infty ) \times \Lambda )$ , we present a method for designing funding rates that ensures the perpetual future price remains anchored to $\varphi ( s , X _ { s } )$ for $s \geq 0$ . The following theorem states that the risk-neutral pricing BSDE (3.6) with the funding rate functional Φ stated in (4.1) has a unique solution; moreover, the unique solution $( Y , Z )$ coincides with $( \varphi ( s , X _ { s } ) , ( \partial _ { x } \sigma \varphi ) ( s , X _ { s } ) ) _ { s \geq 0 }$ . Consequently, this funding rate functional Φ induces a perpetual future price aligned with $\varphi ( s , X _ { s } )$ for $s \geq 0$ . The constant $M _ { \rho \vee 2 }$ in the following theorem is the BDG inequality constant in (3.7). The proof of the following theorem is described in Appendix C.

Theorem 4.1. Let Assumptions 3.1-3.2 hold and $H : \mathbb { R } ^ { 2 } \mathbb { R }$ be a function satisfying Assumption 4.1. For any $p \geq 1$ and $\varphi \in C _ { p } ^ { 1 , 2 } ( [ 0 , \infty ) \times \Lambda )$ , consider the funding rate functional

$$
\Phi ( s , \gamma , y ) : = H ( \varphi ( s , \gamma ) , y ) - \partial _ { s } \varphi ( s , \gamma ) - \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \varphi ) ( s , \gamma ) - r ( s , \gamma ) \partial _ { x } \varphi ( s , \gamma ) \gamma ( s ) + r ( s , \gamma ) y\tag{4.1}
$$

for $( s , \gamma , y ) \in [ 0 , \infty ) \times \Lambda \times \mathbb { R }$ . Then, we have the following.

(i) The map $( s , \gamma ) \mapsto \Phi ( s , \gamma , 0 )$ has polynomial growth. Let $\rho \geq p$ and $C _ { \Phi } > 0$ be constants such that $| \Phi ( s , \gamma , 0 ) | \le C _ { \Phi } ( 1 + \| \gamma \| _ { s } ^ { \rho } )$ for all $( s , \gamma ) \in [ 0 , \infty ) \times \Lambda$

(ii) Let ℓ be the constant in Assumption 4.1. If

$$
\ell > \operatorname* { i n f } _ { K > 0 } { ( K + \frac { 1 } { 2 } ( \frac { C _ { r } } { \sqrt { 2 K } } + M _ { \rho \vee 2 } C _ { 3 } ) ^ { 2 } ) \rho } ,\tag{4.2}
$$

the risk-neutral pricing BSDE (3.6) has a unique solution $( Y , Z )$ in $\mathbb { S } ^ { 2 } ( 0 , \infty ; \mathbb { R } ) \times \mathbb { H } ^ { 2 } ( 0 , \infty ; \mathbb { R } ^ { m } )$ such that $\| Y \| \leq L ( 1 + \| X \| ^ { \rho } )$ for some constant $L > 0$ . Moreover, $Y ( s ) = \varphi ( s , X _ { s } )$ and $Z ( s ) = ( \partial _ { x } \varphi \sigma ) ( s , X _ { s } ) \ f o r \ s \geq 0$

For given $p \geq 1$ and $\varphi \in C _ { p } ^ { 1 , 2 } ( [ 0 , \infty ) \times \Lambda )$ , a funding portfolio is said to be admissible if it is p-admissible. In the above theorem, because the unique solution is given by $Y ( s ) = \varphi ( s , X _ { s } )$ and $\varphi$ has polynomial growth of order p with $p \leq \rho ,$ it follows that there exists a unique $F ^ { \Phi } .$ funding portfolio among all admissible funding portfolios. An important observation is that this uniqueness holds across a broad class of funding portfolios. Recall the concept of ρ-admissibility from Definition 3.1. The theorem guarantees the existence of a unique $F ^ { \Phi } – \mathrm { f u n d i n g }$ portfolio within the class of all ρ-admissible funding portfolios. As stated in (4.2), as ℓ increases, $\rho$ can be chosen larger. Therefore, the uniqueness result extends to a wider class of portfolios as ℓ grows. As ℓ is a constant selected by the issuer, the issuer can ensure the existence of a unique price and a unique replicating portfolio within a desired class of funding portfolios.

The following corollary presents a simpler method of designing funding rates that ensures the perpetual future price aligns with the target value $\varphi ( s , X _ { s } )$ for $s \geq 0$ . It is obtained by setting $\rho = p + 2$ in the above theorem. The detailed proof is provided in Appendix C.

Corollary 4.2. Let Assumptions 3.1-3.2 hold. For given $p \geq 1$ and $\varphi \in C _ { p } ^ { 1 , 2 } ( [ 0 , \infty ) \times \Lambda )$ ， choose any function H satisfying Assumption 4.1 for the constant ℓ such that

$$
\ell > \operatorname* { i n f } _ { K > 0 } ( K + \frac { 1 } { 2 } ( \frac { C _ { r } } { \sqrt { 2 K } } + M _ { p + 2 } C _ { 3 } ) ^ { 2 } ) ( p + 2 )
$$

and define the funding rate functional Φ as stated in (4.1). Then, the risk-neutral pricing BSDE (3.6) has a unique solution $( Y , Z )$ in $\mathbb { S } ^ { 2 } ( 0 , \infty ; \mathbb { R } ) \times \mathbb { H } ^ { 2 } ( 0 , \infty ; \mathbb { R } ^ { m } )$ such that $\| Y \| \leq L ( 1 + \| X \| ^ { p + 2 } )$ for some constant $L > 0$ . Moreover, $Y ( s ) = \varphi ( s , X _ { s } )$ and $Z ( s ) = ( \partial _ { x } \varphi \sigma ) ( s , X _ { s } ) \ f o r \ s \geq 0$

The funding rate Φ presented in (4.1) consists of three components: $H ( \varphi ( s , \gamma ) , y ) , - \mathcal { L } \varphi ( s , \gamma )$ and $r ( s , \gamma ) y$ , where

$$
\mathcal { L } \varphi ( s , \gamma ) : = \partial _ { s } \varphi ( s , \gamma ) + \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \varphi ) ( s , \gamma ) + r ( s , \gamma ) \partial _ { x } \varphi ( s , \gamma ) \gamma ( s ) .
$$

<!-- page: 12 -->

Each term plays a distinct role in the funding mechanism. The first term $H ( \varphi ( s , \gamma ) , y )$ plays a central role and will be discussed in more detail below. The second term $- \mathcal { L } \varphi ( s , \gamma )$ is associated with the no-arbitrage condition. Specifically, observe that the process

$$
Y ( s ) - \int _ { 0 } ^ { s } \left( r ( u , X _ { u } ) Y ( u ) - \Phi ( u , X _ { u } , Y ( u ) ) \right) d u = \varphi ( s , X _ { s } ) - \int _ { 0 } ^ { s } { \mathcal { L } } \varphi ( u , X _ { u } ) d u , \ s \geq 0
$$

is a local martingale under the risk-neutral measure because $\mathcal { L }$ is the infinitesimal generator of $\varphi .$ This implies that the perpetual futures price $Y _ { i }$ , when adjusted by the funding fee Φ, is arbitrage-free. More precisely, it satisfies the condition of no free lunch with vanishing risk (Delbaen and Schachermayer (1994)). The third term $r ( s , \gamma ) y$ reflects the interest rate cost or benefit from holding the perpetual future.

The first term $H ( \varphi ( s , \gamma ) , y )$ plays a crucial role in the funding mechanism. A remarkable phenomenon is that the transaction corresponding to $H ( \varphi ( s , \gamma ) , y )$ does not occur in practice, since Assumption 4.1 (i) implies $H ( \varphi ( s , X _ { s } ) , Y ( s ) ) = H ( Y ( s ) , Y ( s ) ) = 0 ;$ nevertheless, this term is essential for ensuring the uniqueness of perpetual futures prices. From a mathematical perspective, it ensures the uniqueness of solutions to the infinite-horizon BSDE (3.6). From an economic standpoint, it enforces uniqueness through the law of supply and demand. To illustrate this, assume for simplicity that the short rate is zero and consider the case where $\varphi ( s , \gamma ) = \varphi ( s , \gamma _ { 1 } , \ldots , \gamma _ { m } ) = \gamma _ { 1 } ( s )$ and $H ( y _ { 1 } , y _ { 2 } ) = \ell ( y _ { 1 } - y _ { 2 } )$ . Then the funding rate functional defined in (4.1) simplifies to $\Phi ( s , X _ { s } , Y ( s ) ) = \ell ( X _ { 1 } ( s ) - Y ( s ) )$ . If $Y ( s ) < X _ { 1 } ( s )$ at time $s ,$ indicating that the perpetual future price is below the first asset price, the long positions receive a positive amount $- \ell ( Y ( s ) - X _ { 1 } ( s ) )$ ds from the short positions. Consequently, investors are incentivized to purchase more futures, increasing its price. Conversely, if $Y ( s ) > X _ { 1 } ( s )$ at time s, the long positions must pay $\ell ( Y ( s ) - X _ { 1 } ( s ) )$ ds to the short positions. Consequently, they are likely to sell their futures, which drives the price down. This dynamic of supply and demand keeps the perpetual future price aligned with the first asset price.

In this context, the parameter ℓ must be chosen suficiently large to ensure the proper functioning of the law of supply and demand. Specifically, the condition stated in (4.2) needs to be satisfied. If this condition is not met, the uniqueness of funding portfolios cannot be guaranteed. To illustrate this, consider the two-dimensional uncorrelated Black-Scholes model $X = ( X _ { 1 } ( s ) , X _ { 2 } ( s ) ) _ { s \geq 0 }$ with a constant short rate $r = 1$ . The risk-neutral dynamics described in (3.4) simplify to

$$
X _ { i } ( s ) = X _ { i } ( 0 ) + \int _ { 0 } ^ { s } X _ { i } ( u ) d u + \int _ { 0 } ^ { s } \sigma _ { i } X _ { i } ( u ) d B _ { i } ( u ) , i = 1 , 2
$$

where $\sigma _ { 1 }$ and $\sigma _ { 2 }$ are volatility constants. Suppose we set $\varphi ( s , \gamma ) = \varphi ( s , \gamma _ { 1 } , \ldots , \gamma _ { m } ) = \gamma _ { 1 } ( s )$ and $H ( y _ { 1 } , y _ { 2 } ) = \ell ( y _ { 1 } - y _ { 2 } )$ with $\ell = 1$ . The parameter $\ell = 1$ does not satisfy the condition (4.2) because inf $\begin{array} { r } { \kappa { > } 0 ( K + \frac { 1 } { 2 } ( \frac { C _ { r } } { \sqrt { 2 K } } + M _ { \rho \vee 2 } C _ { 3 } ) ^ { 2 } ) \rho > \operatorname* { i n f } _ { K > 0 } ( K + \frac { 1 } { 4 K } ) p = 1 } \end{array}$ , where we have used $C _ { r } = 1$ 1 $M _ { \rho \lor 2 } > 0 , C _ { 3 } > 0$ , and $\rho \ge p = 1$ . The funding rate functional Φ defined in (4.1) is zero in this case. It is evident that a zero funding rate does not result in a unique future price. Indeed, the risk-neutral pricing BSDE

$$
Y ( s ) = Y ( T ) - \int _ { s } ^ { T } Y ( u ) d u - \int _ { s } ^ { T } Z _ { 1 } ( u ) d B _ { 1 } ( u ) - \int _ { s } ^ { T } Z _ { 2 } ( u ) d B _ { 2 } ( u )
$$

admits multiple solutions. For examples, $( Y , Z _ { 1 } , Z _ { 2 } ) = ( 2 X _ { 1 } , 2 \sigma _ { 1 } X _ { 1 } , 0 ) , ( X _ { 1 } + 2 X _ { 2 } , \sigma _ { 1 } X _ { 1 } , 2 \sigma _ { 2 } X _ { 2 } )$ $( X _ { 1 } ^ { - 2 / \sigma _ { 1 } ^ { 2 } } , \frac { 2 } { \sigma _ { 1 } } X _ { 1 } ^ { - 2 / \sigma _ { 1 } ^ { 2 } } , 0 )$ are solutions. This highlights that choosing ℓ suficiently large is essential to ensure the uniqueness of funding portfolios.

<!-- page: 13 -->

The funding rate stated in (4.1) can be expressed in the model-free form

$$
\begin{array} { r l } & { \Phi ( s , X _ { s } , Y ( s ) ) = H ( \varphi ( s , X _ { s } ) , Y ( s ) ) - \partial _ { s } \varphi ( s , X _ { s } ) - \cfrac { 1 } { 2 } \displaystyle \sum _ { 1 \leq i , j \leq m } \partial _ { i } ( \partial _ { j } \varphi ) ( s , X _ { s } ) \frac { d } { d s } \langle X _ { i } , X _ { j } \rangle _ { s } } \\ & { \qquad - \partial _ { x } \varphi ( s , X _ { s } ) X _ { s } \frac { d } { d s } \ln G _ { s } + Y ( s ) \frac { d } { d s } \ln G _ { s } . } \end{array}
$$

This is directly obtained by $\begin{array} { r } { r ( s , X _ { s } ) = \frac { d } { d s } \ln G _ { s } } \end{array}$ and $\begin{array} { r } { ( \sigma \sigma ^ { \top } ) _ { i , j } ( s , X _ { s } ) = \frac { d } { d s } \langle X _ { i } , X _ { j } \rangle _ { s } } \end{array}$ . Thus, the precise knowledge of the non-anticipative functionals $r , \mu ,$ and $\sigma$ is not needed to determine the funding rate Φ. This observation is from (Angeris et al., 2023, Remark 4).

Assumption 4.1 encompasses a broad range of funding rate functions. Typical examples include linear functions, such as $\ell ( y _ { 1 } - y _ { 2 } )$ , as well as piecewise linear functions, such as $\ell _ { 1 } ( y _ { 1 } - y _ { 2 } ) \mathbb { I } _ { \{ | y _ { 1 } - y _ { 2 } | \leq 1 \} } + \ell _ { 2 } ( y _ { 1 } - y _ { 2 } ) \mathbb { I } _ { \{ | y _ { 1 } - y _ { 2 } | > 1 \} }$ and $\ell _ { 1 } ( y _ { 1 } - y _ { 2 } ) \mathbb { I } _ { \{ y _ { 1 } > y _ { 2 } \} } + \ell _ { 2 } ( y _ { 1 } - y _ { 2 } ) \mathbb { I } _ { \{ y _ { 1 } \leq y _ { 2 } \} } .$ where $\ell , \ell _ { 1 } , \ell _ { 2 } > 0$ . Furthermore, instead of constant coeficients, the assumption allows these coeficients to be stochastic processes $( \ell ( s ) ) _ { s \geq 0 } , ( \ell _ { 1 } ( s ) ) _ { s \geq 0 }$ , and $( \ell _ { 2 } ( s ) ) _ { s \geq 0 }$ , which are bounded below by some positive constants. The most common form among these is the linear function $H ( y _ { 1 } , y _ { 2 } ) = \ell ( y _ { 1 } - y _ { 2 } )$ , in which case the funding rate Φ defined in (4.1) is referred to as a constant proportion funding rate. While most existing literature concentrates exclusively on constant proportion funding rates, our findings are applicable to a broad class of funding schemes. This is the first study to derive unique pricing and replicating portfolios for perpetual futures across a diverse range of funding rate structures.

## 4.2 Path-dependent funding rates

We examine the constant proportion funding rate and its path-dependent variant for practical applications. The short rate is assumed to be a constant r throughout this section. We begin by defining path-dependent funding rate functionals, which generalize the concept introduced in Definition 3.3. A key distinction is that they are dependent on the historical trajectory of $Y$

Definition 4.1. If a funding rate is expressed as $F ( s ) = \Phi ( s , X _ { s } , Y _ { s } )$ for a non-anticipative functional $\Phi : [ 0 , \infty ) \times \Lambda \times C ( [ 0 , \infty ) ; \mathbb { R } ) \to \mathbb { R }$ , then we refer to Φ as the path-dependent funding rate functional and denote the corresponding funding rate by $F ^ { \Phi }$

For any $p \ge 1 , \ell > 0 , \delta > 0$ and $\varphi \in C _ { p } ^ { 1 , 2 } ( [ 0 , \infty ) \times \Lambda )$ , we define two non-anticipative functionals $\Phi : [ 0 , \infty ) \times \Lambda \times \mathbb { R } \to \mathbb { R }$ and $\Phi ^ { \delta } : [ 0 , \infty ) \times \Lambda \times C ( [ 0 , \infty ) ; \mathbb { R } ) \to \mathbb { R }$ as

$$
\Phi ( s , \gamma , y ) = \ell ( \varphi ( s , \gamma ) - y ) - \partial _ { s } \varphi ( s , \gamma ) - \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \varphi ) ( s , \gamma ) - r \partial _ { x } \varphi ( s , \gamma ) \gamma ( s ) + r y\tag{4.3}
$$

and

$$
\Phi ^ { \delta } ( s , \gamma , \eta ) = \frac { 1 } { \delta } \int _ { s - \delta } ^ { s } \Phi ( u , \gamma , \eta ( u ) ) d u .\tag{4.4}
$$

The non-anticipative functional $\Phi$ represents a constant proportion funding rate based on current spot prices. However, on most exchanges, the funding fee is calculated as an average of values over the past 8 hours rather than relying on the current spot price. This can be mathematically modeled using the path-dependent functional $\Phi ^ { \delta }$ , where $\textstyle { \delta = { \frac { 1 } { 1 0 9 5 } } }$ , corresponding to an 8 hour averaging window. Because $\Phi ^ { \delta }$ is obtained by averaging over recent short periods, we consider $\Phi ^ { \delta }$ to be a practical approximation of Φ.

This path-dependent funding rate induces an infinite-horizon delayed BSDE. By setting $F ( s ) = \Phi ( s , X _ { s } , Y _ { s } )$ in (3.5), we obtain

$$
Y ^ { \delta } ( s ) = Y ^ { \delta } ( T ) - \int _ { s } ^ { T } ( r Y ^ { \delta } ( u ) - \Phi ^ { \delta } ( u , X _ { u } , Y _ { u } ^ { \delta } ) ) d u - \int _ { s } ^ { T } Z ^ { \delta } ( u ) d B ( u )\tag{4.5}
$$

<!-- page: 14 -->

for $0 \leq s \leq T < \infty$ , which is the risk-neutral pricing BSDE for the path-dependent funding rate $\Phi ^ { \delta }$ . A direct calculation yields

$$
\begin{array} { l } { { \displaystyle Y ^ { \delta } ( s ) = Y ^ { \delta } ( T ) - \int _ { s } ^ { T } ( r Y ^ { \delta } ( u ) - \frac { 1 } { \delta } \int _ { u - \delta } ^ { u } \Phi ( v , X _ { v } , Y ^ { \delta } ( v ) ) d v d u - \int _ { s } ^ { T } Z ^ { \delta } ( u ) d B ( u ) } } \\ { { \displaystyle \quad \quad = Y ^ { \delta } ( T ) + \int _ { s } ^ { T } g ( u , X _ { u } ) - r Y ^ { \delta } ( u ) - \frac { \ell - r } { \delta } \int _ { u - \delta } ^ { u } Y ^ { \delta } ( v ) d v d u - \int _ { s } ^ { T } Z ^ { \delta } ( u ) d B ( u ) } } \end{array}
$$

where $g : [ 0 , \infty ) \times \Lambda \to \mathbb { R }$ is a non-anticipative functional defined as

$$
g ( s , \gamma ) : = \frac { 1 } { \delta } \int _ { s - \delta } ^ { s } \ell \varphi ( v , \gamma ) - \partial _ { s } \varphi ( v , \gamma ) - \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \varphi ) ( v , \gamma ) - r \partial _ { x } \varphi ( v , \gamma ) \gamma ( v ) d v
$$

for $( s , \gamma ) \in [ 0 , \infty ) \times \Lambda$ . This BSDE is classified as a delayed BSDE due to the presence of an additional term $\int _ { u - \delta } ^ { u } Y ( v )$ dv. This extra component introduces additional complexity compared to the classical BSDE framework. The infinite-horizon delayed BSDE has not been studied before. To handle this delay term, we extend the domain of all processes $Y \in \mathbb { S } ^ { 2 } ( 0 , \infty ; \mathbb { R } )$ to include the interval $[ - \delta , 0 ]$ by defining $Y ( s ) = Y ( 0 )$ for $s \in [ - \delta , 0 ]$ . Despite this extension, we continue to denote the process space as $\mathbb { S } ^ { 2 } ( 0 , \infty ; \mathbb { R } )$ rather than $\mathbb { S } ^ { 2 } ( - \delta , \infty ; \mathbb { R } )$

We recall from Theorem 4.1 that for any $p \geq 1$ and $\varphi \in C _ { p } ^ { 1 , 2 } ( [ 0 , \infty ) \times \Lambda )$ , the non-anticipative functional $\Phi ( s , \gamma , 0 )$ has polynomial growth in $( s , \gamma )$ . There are constants $\rho \geq p$ and $C _ { \Phi } > 0$ such that $| \Phi ( s , \gamma , 0 ) | \le C _ { \Phi } ( 1 + \| \gamma \| _ { s } ^ { \rho } )$ for all $( s , \gamma ) \in [ 0 , \infty ) \times \Lambda$ . It can be easily shown that $| g ( s , \gamma ) | \leq C \Phi ( 1 + \| \gamma \| _ { s } ^ { \rho } )$ for all $( s , \gamma ) \in [ 0 , \infty ) \times \Lambda$

Assumption 4.2. Consider the funding rate functionals Φ and $\Phi ^ { \delta }$ defined in (4.3) and (4.4), respectively. Let $\rho \geq p$ and $C _ { \Phi } > 0$ be constants such that $| \Phi ( s , \gamma , 0 ) | \le C _ { \Phi } ( 1 + \| \gamma \| _ { s } ^ { \rho } )$ for all $( s , \gamma ) \in [ 0 , \infty ) \times \Lambda$ . Suppose $\ell \in \mathbb { R }$ and $0 < \delta < 1$ satisfy the following conditions.

$$
\begin{array} { r } { ( i ) \ \ell > 1 + \operatorname* { i n f } _ { K > 0 } ( K + \frac { 1 } { 2 } ( \frac { r } { \sqrt { 2 K } } + M _ { \rho \vee 2 } C _ { 3 } ) ^ { 2 } ) \rho . } \end{array}
$$

(ii) The constant δ satisfies

$$
\begin{array} { l } { \displaystyle \frac 1 3 \frac { e ^ { | 6 ( \ell - r ) ^ { 2 } - 2 \ell + 2 | \delta } - 1 } { | 6 ( \ell - r ) ^ { 2 } - 2 \ell + 2 | \delta } < 1 , } \\ { \displaystyle e ^ { \rho } ( ( \ell - r ) ^ { 2 } + \frac 1 2 | \ell - r | \ell + 2 | \ell - r | ) \delta < 1 . } \end{array}
$$

We primarily focus on two key topics related to path-dependent funding rate functionals. First, we examine the existence and uniqueness of $\Phi ^ { \delta } .$ -funding portfolios. Theorem 3.2 is not applicable as $\Phi ^ { \delta }$ depends on the historical trajectory of $Y$ . Second, we compare the values of the $\Phi ^ { \delta } .$ -funding portfolio and the Φ-funding portfolio. Specifically, we demonstrate that when $\delta$ is small, the funding rate functionals Φ and $\Phi ^ { \delta }$ produce similar perpetual future prices Y and $Y ^ { \delta }$ as well as similar replicating portfolios $Z$ and $Z ^ { \delta }$ . The main results on these topics are presented in Theorem 4.3, with detailed proofs provided in Appendix D. Although these topics are conceptually straightforward, establishing rigorous proofs is complex and challenging. The upper bounds $L _ { 1 } , L _ { 2 } , L _ { 3 } , L _ { 4 } , L _ { 5 }$ specified in the theorem can be explicitly calculated. More refined upper bounds are provided in Appendix D.2. The first inequality in (4.7) holds without taking expectations. Note that the following theorem holds in particular for $\rho = p + 2$ , similar to Corollary 4.2.

Theorem 4.3. Let Assumptions 3.1-3.3 hold. Suppose that the funding rate functionals Φ and $\Phi ^ { \delta }$ defined in (4.3) and (4.4), respectively, satisfy Assumption 4.2. Then, we have the followings.

(i) The BSDE (3.6) has a unique solution $( Y , Z )$ in $\mathbb { S } ^ { 2 } ( 0 , \infty ; \mathbb { R } ) \times \mathbb { H } ^ { 2 } ( 0 , \infty ; \mathbb { R } ^ { m } )$ such that $\| Y \| \leq L ( 1 + \| X \| ^ { \rho } )$ for some constant $L > 0$ . In addition, $Y ( s ) = \varphi ( s , X _ { s } )$ and $Z ( s ) =$ $( \partial _ { x } \varphi \sigma ) ( s , X _ { s } ) f o r s \geq 0$

<!-- page: 15 -->

(ii) The BSDE (4.5) has a unique solution $( Y ^ { \delta } , Z ^ { \delta } )$ in $\mathbb { S } ^ { 2 } ( 0 , \infty ; \mathbb { R } ) \times \mathbb { H } ^ { 2 } ( 0 , \infty ; \mathbb { R } ^ { m } )$ such that $\| Y ^ { \delta } \| \leq L ( 1 + \| X \| ^ { \rho } )$ for some constant $L > 0$

Moreover, we have

$$
\operatorname* { l i m } _ { \delta \to 0 } \mathbb { E } \bigl [ \| Y ^ { \delta } - Y \| _ { T } \bigr ] = 0 ,\tag{4.6}
$$

$$
\operatorname* { l i m } _ { \delta \to 0 } \mathbb { E } \Big [ \int _ { 0 } ^ { T } | Z ^ { \delta } ( u ) - Z ( u ) | ^ { 2 } d u \Big ] = 0
$$

for all $T \geq 0$ . In particular, if there is a constant $C _ { 5 } > 0$ such that $| \Phi ( s , \gamma , 0 ) - \Phi ( s ^ { \prime } , \gamma ^ { \prime } , 0 ) | \ \leq$ $C _ { 5 } ( 1 + \| \gamma _ { s } \| _ { s \vee s ^ { \prime } } ^ { \rho - 1 } + \| \gamma _ { s ^ { \prime } } ^ { \prime } \| _ { s \vee s ^ { \prime } } ^ { \rho - 1 } ) ( \sqrt { | s - s ^ { \prime } | } + \| \gamma _ { s } - \gamma _ { s ^ { \prime } } ^ { \prime } \| _ { s \vee s ^ { \prime } } ) ~ f o r$ all $( s , \gamma ) , ( s ^ { \prime } , \gamma ^ { \prime } ) \in [ 0 , \infty ) \times \Lambda$ , then $f o r$ some positive constants $L _ { 1 } , L _ { 2 } , L _ { 3 } , L _ { 4 } , L _ { 5 }$ , we have

$$
\begin{array} { r l } & { \| Y ^ { \delta } - Y \| _ { T } \leq ( L _ { 1 } + L _ { 2 } \| X \| _ { T } ^ { \rho } ) \sqrt { \delta } } \\ & { \mathbb { E } \Big [ \int _ { 0 } ^ { T } | Z ^ { \delta } ( u ) - Z ( u ) | ^ { 2 } d u \Big ] \leq ( 1 + T ) ( L _ { 3 } \mathbb { E } [ \| X \| _ { T } ^ { 2 \rho } ] + L _ { 4 } \mathbb { E } [ \| X \| _ { T } ^ { \rho } ] + L _ { 5 } ) \sqrt { \delta } } \end{array}\tag{4.7}
$$

for all $T \geq 0$

## 5 Applications

## 5.1 Perpetual power index futures

We study how to design funding rate functionals for perpetual power index futures. Consider a market with $m + 1$ assets consisting of a money market account with constant short rate $r \geq 0$ and m tradable assets given as a solution to the path-dependent SDE (3.1) for $x \in \mathbb { R } ^ { m }$ and non-anticipative functionals $\mu : [ 0 , \infty ) \times \Lambda \to \mathbb { R } ^ { m } , \sigma : [ 0 , \infty ) \times \Lambda \to \mathbb { R } ^ { m \times m }$ . We take Assumptions 3.1 and 3.3 to be valid.

We examine an issuer seeking to keep the perpetual future price aligned with the market’s power index. More precisely, the perpetual future price at time s is anchored to $\varphi ( s , X _ { s } )$ for all $s \geq 0$ where $\begin{array} { r } { \varphi ( s , \gamma ) = \varphi ( s , \gamma _ { 1 } , \cdot \cdot \cdot , \gamma _ { m } ) : = c _ { 0 } + \sum _ { i = 1 } ^ { m } c _ { i } \gamma _ { i } ^ { p _ { i } } ( s ) } \end{array}$ for given $c _ { 0 } , c _ { 1 } , \cdots , c _ { m } \in \mathbb { R }$ and $p _ { 1 } , \cdots , p _ { m } \in \mathbb { N }$ . By Theorem 4.1, a funding rate functional $\Phi : [ 0 , \infty ) \times \Lambda \times \mathbb { R } \to$ R defined as

$$
\Phi ( s , \gamma , y ) : = H ( \varphi ( s , \gamma ) , y ) - { \frac { 1 } { 2 } } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \varphi ) ( s , \gamma ) - r \gamma ( s ) ( c _ { 1 } p _ { 1 } \gamma _ { 1 } ^ { p _ { 1 } - 1 } ( s ) , \cdots , c _ { m } p _ { m } \gamma _ { m } ^ { p _ { m } - 1 } ( s ) ) + r y
$$

where the matrix $\partial _ { x x } \varphi ( s , \gamma )$ is

$$
\begin{array}{c} \binom { c _ { 1 } p _ { 1 } ( p _ { 1 } - 1 ) \gamma _ { 1 } ^ { p _ { 1 } - 2 } ( s ) } { \vdots } \quad \cdot \cdot \quad \quad 0 \eqno { \vdots } \\ { \therefore \quad } \quad \quad \quad \vdots \\\ { 0 \qquad \quad \cdot \cdot \quad c _ { m } p _ { m } ( p _ { m } - 1 ) \gamma _ { 1 } ^ { p _ { m } - 2 } ( s ) } \end{array}
$$

gives the desired perpetual future price if H satisfies Assumption 4.1 with the constant $\ell >$ inf $\kappa _ { > 0 } ( K + { \textstyle { \frac { 1 } { 2 } } } ( { \frac { r } { \sqrt { 2 K } } } + M _ { 2 \vee \rho } C _ { 3 } ) ^ { 2 } ) \rho$ for $\rho : = \operatorname* { m a x } _ { 1 \leq i \leq m } p _ { i }$ . The risk-neutral pricing BSDE (3.6) has a unique solution $( Y , Z )$ in $\mathbb { S } ^ { 2 } ( 0 , \infty ; \mathbb { R } ) \times \mathbb { H } ^ { 2 } ( 0 , \infty ; \mathbb { R } ^ { m } )$ such that $\| Y \| \leq L ( 1 + \| X \| ^ { \rho } )$ for some constant $L > 0$ and this unique solution is

$$
( Y , Z ) = ( \varphi ( s , X _ { s } ) , ( c _ { 1 } p _ { 1 } X _ { 1 } ( s ) , \cdots , c _ { m } p _ { m } X _ { m } ( s ) ) \sigma ( s , X _ { s } ) ) _ { s \geq 0 } .
$$

The perpetual future price Y with this funding rate functional Φ coincides with the market’s power index and the corresponding replicating portfolio is $\begin{array} { r } { \phi ( s ) : = Z ( s ) \sigma ^ { - 1 } ( s , X _ { s } ) } \end{array}$ for $s \geq 0$

We examine the constant proportion funding rate functional Φ and its path-dependent variant $\Phi ^ { \delta }$ defined in (4.3) and (4.4), respectively, with the constants ℓ and δ satisfying Assumption

<!-- page: 16 -->

4.2. According to Theorem 4.3, the path-dependent funding rate $\Phi ^ { \delta }$ generates uniquely the perpetual future price process $Y ^ { \delta }$ and the replicating portfolio $\phi ^ { \delta } ( s ) : = Z ^ { \delta } ( s ) \sigma ^ { - 1 } ( s , X _ { s } )$ . Furthermore, these are close to the original future price Y and replicating portfolio $\phi ,$ as described in (4.7).

As a special case, consider the traditional Black-Scholes model. Under the risk-neutral measure, the stock price follows $d X ( s ) = r X ( s ) d s + \sigma X ( s ) d B ( s )$ where $r \geq 0$ denotes the short rate. Suppose $m = 1 , r = 0 . 0 2 , \sigma = 0 . 3 , c _ { 0 } = 0 , c _ { 1 } = 1 , p _ { 1 } = 1$ , then (4.2) is satisfied for $\ell > 0 . 2 6 2 2 7$ . The original funding rate Φ with this constant ℓ yields the desired perpetual future price and the replicating portfolio. For the path-dependent funding rate $\Phi ^ { \delta }$ , we set $\delta =$ $\scriptstyle { \frac { 1 } { 1 , 0 9 5 } }$ , which corresponds to an 8 hour period, a commonly used time interval in cryptocurrency markets. We choose ℓ such that $1 . 2 6 2 2 7 < \ell < 1 5 . 7 5 1 2 5$ . Then these constants ℓ and δ satisfy Assumption 4.2. Let us compare the perpetual futures derived from the funding rate functionals Φ and $\Phi ^ { \delta }$ . According to (4.7) and (D.23), we have that for all $T \geq 0$

$$
\| Y ^ { \delta } - Y \| _ { T } \leq ( 3 . 6 8 4 3 2 \| X \| _ { T } + 0 . 8 4 2 1 6 ) \sqrt { \delta } \leq 0 . 1 1 1 3 4 \| X \| _ { T } + 0 . 0 2 5 4 5
$$

and

$$
\begin{array} { r l } & { \mathbb { E } \Big [ \displaystyle \int _ { 0 } ^ { T } | Z ^ { \delta } ( u ) - Z ( u ) | ^ { 2 } d u \Big ] } \\ & { \le \big ( ( 0 . 4 1 0 2 1 + 8 2 . 0 4 1 T ) \mathbb { E } [ \| X \| _ { T } ^ { 2 } ] + ( 0 . 0 6 2 2 7 + 3 1 . 9 7 9 8 3 T ) \mathbb { E } [ \| X \| _ { T } ] + 0 . 0 0 2 3 6 + 2 . 7 8 0 6 7 T ) \sqrt { \delta } } \\ & { \le ( 0 . 0 1 2 3 9 + 2 . 4 7 9 2 7 T ) \mathbb { E } [ \| X \| _ { T } ^ { 2 } ] + ( 0 . 0 0 1 8 8 + 0 . 9 6 6 4 2 T ) \mathbb { E } [ \| X \| _ { T } ] + 0 . 0 0 0 0 7 + 0 . 0 8 4 0 3 1 T . } \end{array}
$$

As an additional application, we consider an issuer seeking to keep the perpetual future price aligned with $X _ { 1 } ^ { p _ { 1 } } X _ { 2 } ^ { p _ { 2 } } \cdot \cdot \cdot X _ { m } ^ { p _ { m } }$ where $p _ { 1 } , p _ { 2 } , \dotsc , p _ { m } \in \mathbb { N }$ . Most of the results are analogous to those obtained for the previous power index futures. Define $\begin{array} { r } { \varphi ( s , \gamma ) : = \prod _ { i = 1 } ^ { m } \gamma _ { i } ^ { p _ { i } } ( s ) } \end{array}$ and $\textstyle \rho : = \sum _ { i = 1 } ^ { m } p _ { i }$ While our analysis holds for any $m \in \mathbb { N }$ , for simplicity, we focus on the case $m = 2$ in the following discussion. We introduce a funding rate functional $\Phi : [ 0 , \infty ) \times \Lambda \times \mathbb { R } $ R defined as $\begin{array} { r } { \Phi ( s , \gamma , y ) = H ( \varphi ( s , \gamma ) , y ) - \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \varphi ) ( s , \gamma ) - r \gamma ( s ) ( p _ { 1 } \gamma _ { 1 } ^ { p _ { 1 } - 1 } ( s ) \gamma _ { 2 } ^ { p _ { 2 } } ( s ) , p _ { 2 } \gamma _ { 1 } ^ { p _ { 1 } } ( s ) \gamma _ { 2 } ^ { p _ { 2 } - 1 } ( s ) ) + r y } \end{array}$ where the matrix $\partial _ { x x } \varphi ( s , \gamma )$ is

$$
\binom { p _ { 1 } ( p _ { 1 } - 1 ) \gamma _ { 1 } ^ { p _ { 1 } - 2 } ( s ) \gamma _ { 2 } ^ { p _ { 2 } } ( s ) } { p _ { 1 } p _ { 2 } \gamma _ { 1 } ^ { p _ { 1 } - 1 } ( s ) \gamma _ { 2 } ^ { p _ { 2 } - 1 } ( s ) p _ { 2 } ( p _ { 2 } - 1 ) \gamma _ { 1 } ^ { p _ { 1 } - 1 } ( s ) \gamma _ { 2 } ^ { p _ { 2 } - 2 } ( s ) }
$$

and H satisfies Assumption 4.1 with the constant $\ell > \operatorname * { i n f } _ { K > 0 } ( K + { \textstyle \frac { 1 } { 2 } } ( { \textstyle \frac { r } { \sqrt { 2 K } } } + M _ { 2 \vee \rho } C _ { 3 } ) ^ { 2 } ) \rho$ for $\rho : = p _ { 1 } + p _ { 2 }$ . The perpetual future price Y, associated with this funding rate Φ, coincides with $X _ { 1 } ^ { p _ { 1 } } X _ { 2 } ^ { p _ { 2 } }$ . The corresponding replicating portfolio is $\phi ( s ) = Z ( s ) \sigma ^ { - 1 } ( s , X _ { s } ) =$ $( p _ { 1 } X _ { 1 } ^ { p _ { 1 } - 1 } ( s ) X _ { 2 } ^ { p _ { 2 } } ( s ) , p _ { 2 } X _ { 1 } ^ { p _ { 1 } } ( s ) X _ { 2 } ^ { p _ { 2 } - 1 } ( s ) ) \sigma ^ { - 1 } ( s , X _ { s } )$ for $s \geq 0$ . As in the case of power index futures, the funding rate functionals Φ and $\Phi ^ { \delta }$ , with the parameters ℓ and δ satisfying Assumption 4.2, yield similar perpetual futures prices Y and $Y ^ { \delta }$ , as well as similar replicating portfolios Z and $Z ^ { \delta }$

## 5.2 Perpetual foreign exchange futures

One of the commonly traded futures in cryptocurrency markets is a perpetual foreign exchange future. We consider an issuer seeking to keep the perpetual future price aligned with the foreign exchange rate. Suppose $m = 1$ and let $r _ { d }$ and $r _ { f }$ be the domestic and foreign short rates, respectively, and $U = ( U ( s ) ) _ { s \geq 0 }$ be the exchange rate. We assume that U is a stochastic process satisfying $\begin{array} { r } { U ( s ) = U ( 0 ) \stackrel { - } { + } \int _ { 0 } ^ { s } b ( u , U _ { u } ) d u + \int _ { 0 } ^ { s } v ( u , U _ { u } ) d W ( u ) } \end{array}$ for $U ( 0 ) \in \mathbb { R }$ and non-anticipative functionals $b : [ 0 , \infty ) \times \bar { \Lambda } \to \mathbb { R } , \ v : [ 0 , \infty ) \times \Lambda \to \mathbb { R }$ . The process $X =$ $( U ( s ) e ^ { r _ { f } s } ) _ { s \geq 0 }$ is a wealth process and satisfies $\begin{array} { r } { X ( s ) = X ( 0 ) + \int _ { 0 } ^ { s } \mu ( u , X _ { u } ) d u + \int _ { 0 } ^ { s } \sigma ( u , X _ { u } ) d W ( u ) } \end{array}$ where $\mu ( s , \gamma ) : = r _ { f } \gamma ( s ) + e ^ { r _ { f } s } b ( s , e ^ { - r _ { f } ( \cdot \wedge s ) } \gamma _ { s } )$ and $\sigma ( s , \gamma ) : = e ^ { r _ { f } s } v ( s , e ^ { - r _ { f } ( \cdot \wedge s ) } \gamma _ { s } )$ . Assume that these non-anticipative functionals $\mu$ and $\sigma$ satisfy Assumptions 3.1 and 3.3. Define $\varphi ( s , \gamma ) : =$ $e ^ { - r _ { f } s } \gamma ( s )$ , then $U ( s ) = \varphi ( s , X _ { s } )$ for $s \geq 0$

<!-- page: 17 -->

We examine an issuer seeking to keep the perpetual future price aligned with the foreign exchange rate. By Theorem 4.1, a funding rate functional $\Phi : [ 0 , \infty ) \times \Lambda \times \mathbb { R } \to \mathbb { R }$ defined as $\Phi ( s , \gamma , y ) : = H ( \varphi ( s , \gamma ) , y ) - ( r _ { d } - r _ { f } ) \varphi ( s , \gamma ) \ : .$ + r y yields the desired perpetual future if H satisfies Assumption 4.1 for the constant $\begin{array} { r } { \ell > \operatorname* { i n f } _ { K > 0 } ( K + \frac { 1 } { 2 } ( \frac { r _ { d } } { \sqrt { 2 K } } + M _ { 2 } C _ { 3 } ) ^ { 2 } ) } \end{array}$ . The perpetual future price derived from this funding rate function Φ coincides with the foreign exchange rate $U$ and the replicating portfolio is $\phi ( s ) : = e ^ { - r _ { f } s }$ for $s \geq 0$

We compare the constant proportion funding rate functional Φ with its path-dependent variant $\Phi ^ { \delta }$ for the parameters ℓ and δ satisfying Assumption 4.2. The path-dependent funding rate $\Phi ^ { \delta }$ uniquely generates the perpetual future price process $Y ^ { \delta }$ and the associated replicating portfolio $\phi ^ { \delta }$ . Furthermore, these approximations are close to the original future price $Y = U$ and the replicating portfolio $\phi ( s ) = e ^ { - r _ { f } s } , s \geq 0$ as described in (4.7).

## 5.3 Geometric mean constant funds

Following Angeris and Chitra (2020), Evans (2020), and Angeris et al. (2023), we investigate a geometric mean constant function market maker (CFMM). Consider the multi-dimensional Black-Scholes model. Assume that the short rate is a constant $r \geq 0$ and m tradable assets are given as $d X ( s ) = D ( X ( s ) ) \mu d s + D ( X ( s ) ) \sigma d W ( s )$ where $\mu = ( \mu _ { 1 } \cdots \mu _ { m } ) ^ { \intercal } \in \mathbb { R } ^ { m \times 1 }$ and

$$
\sigma = \binom { \sigma _ { 1 } } { \vdots } = \binom { \sigma _ { 1 1 } } { \vdots } \cdot \cdot \cdot \cdot \sigma _ { 1 m } ) \in \mathbb { R } ^ { m \times m }
$$

and $\sigma$ is invertible. Here, for any $x = ( x _ { 1 } , \cdots , x _ { m } )$ , we denote by $D ( x )$ the diagonal matrix whose i-th diagonal entry is $x _ { i }$ . It is evident that Assumptions $3 . 1 \mathrm { - } 3 . 3$ are met. Under the risk-neutral measure, the process X satisfies $d X ( s ) = D ( X ( s ) ) r { \bf 1 } d s + D ( X ( s ) ) \sigma d B ( s )$ where 1 denotes the m dimensional column vector with all entries equal to 1.

If one deposits a unit amount into a geometric mean CFMM, then the value of this deposit at time $s \geq 0$ is

$$
Y ( s ) : = { \Big ( } { \frac { X _ { 1 } ( s ) } { X _ { 1 } ( 0 ) } } { \Big ) } ^ { p _ { 1 } } { \Big ( } { \frac { X _ { 2 } ( s ) } { X _ { 2 } ( 0 ) } } { \Big ) } ^ { p _ { 2 } } \cdots { \Big ( } { \frac { X _ { m } ( s ) } { X _ { m } ( 0 ) } } { \Big ) } ^ { p _ { m } }
$$

where $p _ { 1 } , \cdots , p _ { m }$ are positive constants with $\begin{array} { r } { \sum _ { i = 1 } ^ { m } p _ { i } = 1 } \end{array}$ . For simplicity, we assume $X _ { 1 } ( 0 ) =$ $\cdots = X _ { m } ( 0 ) = 1$ . Imagine that an issuer designs a funding rate to make the perpetual future price aligned with this value. Define $\varphi ( s , \gamma ) : = \gamma _ { 1 } ^ { p _ { 1 } } ( s ) \gamma _ { 2 } ^ { p _ { 2 } } ( s ) \cdot \cdot \cdot \gamma _ { m } ^ { p _ { m } } ( s )$ then the funding rate $\Phi ( s , \gamma , y ) : = H ( \varphi ( s , \gamma ) , y ) - ( r - \kappa ) \varphi ( s , \gamma ) + r y$ with $\begin{array} { r } { \hat { \kappa } : = \frac { 1 } { 2 } \bar { \sum _ { i = 1 } ^ { m } } p _ { i } | \sigma _ { i } | ^ { 2 } - \frac { 1 } { 2 } | \sum _ { i = 1 } ^ { m } p _ { i } \sigma _ { i } | ^ { 2 } } \end{array}$ yields the desired perpetual future if H satisfies Assumption 4.1 for the constant $\begin{array} { r } { \ell \stackrel { - } { > } \operatorname* { i n f } _ { K > 0 } ( K + \frac { 1 } { 2 } ( \frac { r } { \sqrt { 2 K } } + } \end{array}$ $M _ { 2 } C _ { 3 } ) ^ { 2 } )$ . The perpetual future price derived from this funding rate function Φ coincides with $Y$ and the replicating portfolio is $\bar { \boldsymbol { \phi } } = \bigl ( p _ { 1 } X _ { 1 } ^ { p _ { 1 } - 1 } X _ { 2 } ^ { p _ { 2 } } \cdot \cdot \cdot X _ { m } ^ { p _ { m } } , \cdot \cdot \cdot \bigr ) , p _ { m } X _ { 1 } ^ { p _ { 1 } } X _ { 2 } ^ { p _ { 2 } } \cdot \cdot \cdot X _ { m } ^ { p _ { m } - 1 } \bigr )$ . As in the previous sections, the funding rate functionals $\Phi$ and $\Phi ^ { \delta }$ , with the parameters ℓ and δ satisfying Assumption 4.2, yield similar perpetual futures prices $Y$ and $Y ^ { \delta }$ , as well as similar replicating portfolios Z and $Z ^ { \delta }$

Most results of our paper cannot be applied directly to prove these because the function $\varphi$ is not diferentiable at the origin nor the partial derivative has polynomial growth at the origin, thus $\varphi$ is not in $C _ { p } ^ { 1 , 2 } ( [ 0 , \infty ) \stackrel { \sim } { \times } \Lambda )$ . To avoid this, we detour the strategy. The main idea is to construct a wealth process useful for this analysis. Observe that $\begin{array} { r } { Y ( s ) \ = \ \prod _ { i = 1 } ^ { m } X _ { i } ^ { p _ { i } } ( s ) \ = } \end{array}$ $\begin{array} { r } { \prod _ { i = 1 } ^ { m } e ^ { ( r p _ { i } - \frac { 1 } { 2 } p _ { i } | \sigma _ { i } | ^ { 2 } ) s + p _ { i } \sigma _ { i } B _ { s } } = e ^ { - \kappa s } e ^ { r s - \frac { 1 } { 2 } | \Sigma | ^ { 2 } s + \Sigma B _ { s } } } \end{array}$ for $s \geq 0$ where $\begin{array} { r } { \Sigma ~ : = ~ p \sigma ~ = ~ \sum _ { i = 1 } ^ { m } p _ { i } \sigma _ { i } ~ \in \ S } \end{array}$ $\mathbb { R } ^ { 1 \times m }$ and $p : = ( p _ { 1 } , \cdot \cdot \cdot , p _ { m } ) \in \mathbb { R } ^ { 1 \times m }$ . Define $\begin{array} { r } { \hat { B } ( s ) : = \frac { \Sigma } { | \Sigma | } B ( s ) } \end{array}$ and ${ \hat { X } } ( s ) : = e ^ { r s - { \frac { 1 } { 2 } } | \Sigma | ^ { 2 } s + | \Sigma | { \hat { B } } ( s ) }$ then $Y ( s ) = e ^ { - \kappa s } { \hat { X } } ( s )$ , B<sup>ˆ</sup> is a one-dimensional Brownian motion and $d { \hat { X } } ( s ) = r { \hat { X } } ( s )$ ds + $| \Sigma | \hat { X } ( s ) d \hat { B } ( s )$ for $s \geq 0$ . It can be shown that the process $\hat { X }$ is the wealth process of the self-financing portfolio

<!-- page: 18 -->

$$
\begin{array} { l } { \hat { \pi } ( s ) : = \hat { X } ( s ) p D ^ { - 1 } ( X ( s ) ) = \hat { X } ( s ) D ^ { - 1 } ( X ( s ) ) p ^ { \top } } \\ { \quad \quad = e ^ { \kappa s } ( p _ { 1 } X _ { 1 } ^ { p _ { 1 } - 1 } ( s ) X _ { 2 } ^ { p _ { 2 } } ( s ) \cdot \cdot \cdot X _ { m } ^ { p _ { m } } ( s ) , \cdot \cdot \cdot , p _ { m } X _ { 1 } ^ { p _ { 1 } } ( s ) X _ { 2 } ^ { p _ { 2 } } ( s ) \cdot \cdot \cdot X _ { m } ^ { p _ { m } - 1 } ( s ) ) } \\ { \quad \quad = e ^ { \kappa s } \Big ( p _ { 1 } \frac { Y ( s ) } { X _ { 1 } ( s ) } , \cdot \cdot \cdot , p _ { m } \frac { Y ( s ) } { X _ { m } ( s ) } \Big ) . } \end{array}
$$

As mentioned in Section 3.1, the results of our paper are applicable to wealth process models. To design a funding rate to make the perpetual future price aligned with $Y ,$ , we define $\hat { \varphi } ( s , \hat { \gamma } ) : = e ^ { - \kappa s } \hat { \gamma } ( s )$ , then it is evident that $\hat { \varphi } \in C _ { 1 } ^ { 1 , 2 } ( [ 0 , \infty ) \times \Lambda )$ The funding rate functional $\hat { \Phi } ( s , \hat { \gamma } , y ) : = H ( \hat { \varphi } ( s , \hat { \gamma } ) , y ) - ( r - \kappa ) \hat { \varphi } ( s , \hat { \gamma } ) + r y$ gives the desired perpetual future price and its replicating portfolio is $\hat { \phi } ( s ) = e ^ { - \kappa s }$ for $s \geq 0$ . Because $\varphi ( s , X _ { s } ) = \hat { \varphi } ( s , \hat { X } _ { s } )$ and $\Phi ( s , X _ { s } , Y ( s ) ) = \hat { \Phi } ( s , \hat { X } _ { s } , Y ( s ) )$ for $s \geq 0$ , two infinite-horizon BSDEs derived from Φ and $\hat { \Phi }$ coincides, thus $\Phi$ and $\hat { \Phi }$ induce the same perpetual future prices. In addition, because $\hat { X }$ is the wealth process from ${ \hat { \pi } } ,$ holding $\hat { \phi }$ number of $\hat { X }$ indicates holding the portfolio $\hat { \phi } \hat { \pi }$ , which is equal to $\phi .$

## 6 Conclusion

This study focuses on analyzing the funding rate mechanism for perpetual future contracts traded in cryptocurrency markets. Our findings indicate that, through careful design of funding rates, the perpetual futures can be kept consistent with their target values. Furthermore, we construct replicating portfolios for perpetual futures, providing issuers with a robust strategy to hedge their exposures. In addition, we introduce path-dependent funding rates suitable for practical implementation and examine the discrepancies between the original and pathdependent funding rates.

There are several potential directions for extending this work. The parameter ℓ introduced in Assumption 4.1 (iii) must be suficiently large to ensure the uniqueness of perpetual future prices. In particular, the condition given in (4.2) is necessary. However, this condition does not represent the optimal lower bound, and the authors believe there is significant room for improvement. Since ℓ plays a crucial role in the funding mechanism, identifying tighter lower bounds would be a valuable contribution. Another possible extension is to explore a broader class of path-dependent funding rates. This paper focuses on a path-dependent version of the constant proportion funding rate, but in practice, a variety of funding rate structures may be employed. Analyzing more general forms of path-dependent funding rates would therefore be an important and relevant direction for future research.

## A Proof of Theorem 3.2

The following proposition is a variant of (Confortola et al., 2019, Lemma 2.1) tailored to our context. This proposition will be used to prove Theorem 3.2.

Proposition A.1. Let Assumptions 3.1-3.2 hold and X be a solution to (3.1). Then $X \in$ $\mathbb { S } ^ { p } ( 0 , \infty ; \mathbb { R } ^ { m } )$ for any $p \geq 1$ , and there exist positive constants $L _ { 6 }$ , which depends only on $p _ { ; }$ , and $L _ { 7 } , L _ { 8 } , L _ { 9 }$ , which depend only on $C _ { 1 } , C _ { r } , C _ { 3 } , p ,$ such that

$$
\mathbb { E } _ { s } [ \| X \| _ { T } ^ { p } ] \le ( L _ { 6 } \| X \| _ { s } ^ { p } + L _ { 7 } ) e ^ { L _ { 8 } ( T - s ) } ,\tag{A.1}
$$

$$
\begin{array} { r } { \mathbb { E } _ { s } [ \| X - X _ { s } \| _ { s + \delta } ^ { p } ] \le L _ { 9 } ( 1 + \mathbb { E } _ { s } [ \| X \| _ { s + \delta } ^ { p } ] \delta ^ { \frac { p } { 2 } } } \end{array}
$$

<!-- page: 19 -->

for all $T \in ( 0 , \infty ) , \delta \in ( 0 , 1 )$ and $s \in [ 0 , T ]$

Proof. We first prove that $X \in \mathbb { S } ^ { p } ( 0 , \infty ; \mathbb { R } ^ { m } )$ for any $p \geq 1$ . Observe that the SDE

$$
\tilde { X } ( s ) = x + \int _ { 0 } ^ { s } r ( u , X _ { u } ) \tilde { X } ( u ) d u + \int _ { 0 } ^ { s } \sigma ( u , \tilde { X } _ { u } ) d B ( u ) , s \geq 0\tag{A.2}
$$

has a solution $\tilde { X }$ in $\mathbb { S } ^ { p } ( 0 , \infty ; \mathbb { R } ^ { m } )$ by (Protter, 2005, Theorem $^ { 7 , }$ Chapter 5). By showing $X = { \tilde { X } }$ we conclude that $X \in \mathbb { S } ^ { p } ( 0 , \infty ; \mathbb { R } ^ { m } )$ . For each $n \in \mathbb { N } .$ , define a stopping time

$$
\tau _ { n } = \operatorname* { i n f } \{ s \geq 0 | | X ( s ) | \geq n \mathrm { o r } | \tilde { X } ( s ) | \geq n \} ,
$$

and let ${ \hat { X } } : = X - { \tilde { X } }$ . Because both X and $\tilde { X }$ are solutions to (A.2), we have

$$
\hat { X } ( s \wedge \tau _ { n } ) = \int _ { 0 } ^ { s \wedge \tau _ { n } } r ( u , X _ { u } ) \hat { X } ( u ) d u + \int _ { 0 } ^ { s \wedge \tau _ { n } } \sigma ( u , X _ { u } ) - \sigma ( u , \tilde { X } _ { u } ) d B ( u ) .
$$

From the BDG inequality and Jensen’s inequality, it follows that

$$
\begin{array} { r l } & { \quad \mathbb { E } [ \underset { 0 \leq r \leq s } { \operatorname* { s u p } } | \hat { X } ( r \wedge \tau _ { n } ) | ^ { 2 } ] } \\ & { \leq 2 \mathbb { E } \bigg [ \underset { 0 \leq r \leq s } { \operatorname* { s u p } } \bigg | \int _ { 0 } ^ { r \wedge \tau _ { n } } r ( u , X _ { u } ) \hat { X } ( u ) d u \bigg | ^ { 2 } + \underset { 0 \leq r \leq s } { \operatorname* { s u p } } \bigg | \int _ { 0 } ^ { r \wedge \tau _ { n } } \sigma ( u , \tilde { X } _ { u } ) - \sigma ( u , X _ { u } ) d B ( u ) \bigg | ^ { 2 } \bigg ] } \\ & { \leq L \Big ( \mathbb { E } \bigg [ \Big ( \int _ { 0 } ^ { s } \underset { 0 \leq r \leq u } { \operatorname* { s u p } } | \hat { X } ( r \wedge \tau _ { n } ) | d u \Big ) ^ { 2 } \bigg ] + \mathbb { E } \bigg [ \int _ { 0 } ^ { T } \underset { 0 \leq r \leq u } { \operatorname* { s u p } } | \hat { X } ( r \wedge \tau _ { n } ) | ^ { 2 } d u \bigg ] \Big ) } \\ & { \leq L ( 1 + s ) \mathbb { E } \bigg [ \int _ { 0 } ^ { s } \underset { 0 \leq r \leq u } { \operatorname* { s u p } } | \hat { X } ( r \wedge \tau _ { n } ) | ^ { 2 } d u \bigg ] } \end{array}
$$

for some positive constant L. Define a function $\Psi : [ 0 , \infty ) [ 0 , \infty )$ as

$$
\Psi ( s ) : = \mathbb { E } [ \operatorname* { s u p } _ { 0 \leq r \leq s } | \hat { X } ( r \wedge \tau _ { n } ) | ^ { 2 } ] , s \geq 0 .
$$

Applying Gr¨onwall’s inequality to $\Psi$ , we have $\Psi ( s ) = 0$ for all $s \geq 0$ , which implies $X ( s \wedge \tau _ { n } ) =$ $\tilde { X } ( s \wedge \tau _ { n } )$ for all $s \geq 0$ . Letting $n \to \infty$ , we obtain $X = { \tilde { X } }$ and thus $X \in \mathbb { S } ^ { p } ( 0 , \infty ; \mathbb { R } ^ { m } )$

For the first inequality in $( \mathrm { A . 1 } )$ , we prove it for $p \geq 2 .$ . The case with $0 < p < 2$ is directly obtained by Jensen’s inequality. Using

$$
X ( r ) = X ( s ) + \int _ { s } ^ { r } r ( u , X _ { u } ) X ( u ) d u + \int _ { s } ^ { r } \sigma ( u , X _ { u } ) d B ( u ) , 0 \le s \le r ,
$$

one can easily show that for $A \in { \mathcal { F } } _ { s }$ 2

$$
\| X \| _ { T } \mathbf { 1 } _ { A } \leq \| X \| _ { s } \mathbf { 1 } _ { A } + \ \operatorname* { s u p } _ { r \in [ s , T ] } { \Big | } \int _ { s } ^ { r } r ( u , X _ { u } ) X ( u ) d u { \Big | } \mathbf { 1 } _ { A } + \operatorname* { s u p } _ { r \in [ s , T ] } { \Big | } \int _ { s } ^ { r } \sigma ( u , X _ { u } ) d B ( u ) { \Big | } \mathbf { 1 } _ { A } .
$$

According to the Minkowski inequality and the BDG inequality, it follows that

$$
\begin{array} { r l } & { ( \mathbb { E } [ \| X \| _ { T } ^ { p } \mathbf { 1 } _ { A } ] ) ^ { \frac { 1 } { p } } \leq ( \mathbb { E } [ \| X \| _ { s } ^ { p } \mathbf { 1 } _ { A } ] ) ^ { \frac { 1 } { p } } + \Big ( \mathbb { E } \Big [ \Big ( \displaystyle \int _ { s } ^ { T } C _ { r } \| X \| _ { u } d u \mathbf { 1 } _ { A } \Big ) ^ { p } \Big ] \Big ) ^ { \frac { 1 } { p } } } \\ & { \qquad + M _ { p } \Big ( \mathbb { E } \Big [ \Big ( \displaystyle \int _ { s } ^ { T } ( C _ { 1 } + C _ { 3 } \| X \| _ { u } ) ^ { 2 } d u \Big ) ^ { \frac { p } { 2 } } \mathbf { 1 } _ { A } \Big ] \Big ) ^ { \frac { 1 } { p } } } \\ & { \qquad \leq ( \mathbb { E } [ \| X \| _ { s } ^ { p } \mathbf { 1 } _ { A } ] ) ^ { \frac { 1 } { p } } + C _ { 1 } ( \mathbb { E } [ \mathbf { 1 } _ { A } ] ) ^ { \frac { 1 } { p } } M _ { p } ( T - s ) ^ { \frac { 1 } { 2 } } } \\ & { \qquad + \displaystyle \int _ { s } ^ { T } ( \mathbb { E } [ ( C _ { r } \| X \| _ { u } \mathbf { 1 } _ { A } ) ^ { p } ] ) ^ { \frac { 1 } { p } } d u + M _ { p } \Big ( \displaystyle \int _ { s } ^ { T } ( \mathbb { E } [ ( C _ { 3 } \| X _ { u } \| _ { u } \mathbf { 1 } _ { A } ) ^ { p } ] ) ^ { \frac { 2 } { p } } d u \Big ) ^ { \frac { 1 } { 2 } } } \end{array}
$$

<!-- page: 20 -->

where $M _ { p }$ is the constant from the BDG inequality. For $K > 0$ , by multiplying $e ^ { - K ( T - s ) }$ , we have

$$
\begin{array} { r l } {  { e ^ { - K ( T - s ) } ( \mathbb { E } [ \| X \| _ { T } ^ { p } \mathbf { 1 } _ { A } ] ) ^ { \frac { 1 } { p } } \le ( \mathbb { E } [ \| X \| _ { s } ^ { p } \mathbf { 1 } _ { A } ] ) ^ { \frac { 1 } { p } } + C _ { 1 } ( \mathbb { E } [ \mathbf { 1 } _ { A } ] ) ^ { \frac { 1 } { p } } M _ { p } ( T - s ) ^ { \frac { 1 } { 2 } } } } \\ & { \quad \quad \quad \quad + \int _ { s } ^ { T } e ^ { - K ( T - s ) } ( \mathbb { E } [ ( C _ { r } \| X \| _ { u } \mathbf { 1 } _ { A } ) ^ { p } ] ) ^ { \frac { 1 } { p } } d u } \\ & { \quad \quad \quad \quad + M _ { p } \Big ( \int _ { s } ^ { T } e ^ { - 2 K ( T - s ) } ( \mathbb { E } [ ( C _ { 3 } \| X _ { u } \| _ { u } \mathbf { 1 } _ { A } ) ^ { p } ] ) ^ { \frac { 2 } { p } } d u \Big ) ^ { \frac { 1 } { 2 } } . } \end{array}
$$

Observe that

$$
\begin{array} { r l } & { \displaystyle \int _ { s } ^ { T } e ^ { - K ( T - s ) } ( \mathbb { E } [ ( \| X \| _ { u } \mathbf { 1 } _ { A } ) ^ { p } ] ) ^ { \frac { 1 } { p } } d u \leq \int _ { s } ^ { T } e ^ { - K ( T - u ) } e ^ { - K ( u - s ) } ( \mathbb { E } [ ( \| X \| _ { u } \mathbf { 1 } _ { A } ) ^ { p } ] ) ^ { \frac { 1 } { p } } d u } \\ & { \qquad \leq \frac { 1 } { \sqrt { 2 K } } \Big ( \displaystyle \int _ { s } ^ { T } ( e ^ { - K ( u - s ) } ( \mathbb { E } [ ( \| X \| _ { u } \mathbf { 1 } _ { A } ) ^ { p } ] ) ^ { \frac { 1 } { p } } ) ^ { 2 } d u \Big ) ^ { \frac { 1 } { 2 } } } \end{array}
$$

and

$$
\Big ( \int _ { s } ^ { T } e ^ { - 2 K ( T - s ) } ( \mathbb { E } [ ( \| X _ { u } \| _ { u } \mathbf { 1 } _ { A } ) ^ { p } ] ) ^ { \frac { 2 } { p } } d u \Big ) ^ { \frac { 1 } { 2 } } \leq \Big ( \int _ { s } ^ { T } ( e ^ { - K ( u - s ) } ( \mathbb { E } [ ( \| X _ { u } \| _ { u } \mathbf { 1 } _ { A } ) ^ { p } ] ) ^ { \frac { 1 } { p } } ) ^ { 2 } d u \Big ) ^ { \frac { 1 } { 2 } } .
$$

Thus,

$$
\begin{array} { r l r } {  { e ^ { - K ( T - s ) } ( \mathbb { E } [ \| X \| _ { T } ^ { p } \mathbf { 1 } _ { A } ] ) ^ { \frac { 1 } { p } } \leq ( \mathbb { E } [ \| X \| _ { s } ^ { p } \mathbf { 1 } _ { A } ] ) ^ { \frac { 1 } { p } } + C _ { 1 } ( \mathbb { E } [ \mathbf { 1 } _ { A } ] ) ^ { \frac { 1 } { p } } M _ { p } ( 1 + ( T - s ) ) } }  \\ & { } & { + ( \frac { C _ { r } } { \sqrt { 2 K } } + M _ { p } C _ { 3 } ) \Big ( \int _ { s } ^ { T } ( e ^ { - K ( u - s ) } ( \mathbb { E } [ ( \| X \| _ { u } \mathbf { 1 } _ { A } ) ^ { p } ] ) ^ { \frac { 1 } { p } } ) ^ { 2 } d u \Big ) ^ { \frac { 1 } { 2 } } . } \end{array}
$$

Then, (Butler and Rogers, 1971, Corollary 2) yields

$$
\begin{array} { r l } & { \quad e ^ { - K ( T - s ) } ( \mathbb { E } [ \| X \| _ { T } ^ { p } \mathbf { 1 } _ { A } ] ) ^ { \frac { 1 } { p } } } \\ & { \le \big ( ( \mathbb { E } [ \| X \| _ { s } ^ { p } \mathbf { 1 } _ { A } ] ) ^ { \frac { 1 } { p } } + C _ { 1 } ( \mathbb { E } [ \mathbf { 1 } _ { A } ] ) ^ { \frac { 1 } { p } } M _ { p } ( 1 + ( T - s ) ) \big ) e ^ { 1 + \frac { 1 } { 2 } ( \frac { C _ { r } } { \sqrt { 2 K } } + M _ { p } C _ { 3 } ) ^ { 2 } ( T - s ) } . } \end{array}
$$

Using the inequality $T - s \leq \frac { 1 } { \epsilon } e ^ { \epsilon ( T - s ) }$ for any $\epsilon > 0$ , we obtain

$$
( \mathbb { E } [ \| X \| _ { T } ^ { p } \mathbf { 1 } _ { A } ] ) ^ { \frac { 1 } { p } } \le \big ( ( \mathbb { E } [ \| X \| _ { s } ^ { p } \mathbf { 1 } _ { A } ] ) ^ { \frac { 1 } { p } } e + L ( \mathbb { E } [ \mathbf { 1 } _ { A } ] ) ^ { \frac { 1 } { p } } \big ) e ^ { ( \epsilon + K + \frac { 1 } { 2 } ( \frac { C _ { r } } { \sqrt { 2 K } } + M _ { p } C _ { 3 } ) ^ { 2 } ) ( T - s ) }\tag{A.3}
$$

for some positive constant L. Because this holds for all $A \in { \mathcal { F } } _ { s }$ , it follows that

$$
\mathbb { E } _ { s } [ \| X \| _ { T } ^ { p } ] \le ( L _ { 6 } \| X \| _ { s } ^ { p } + L _ { 7 } ) e ^ { L _ { 8 } ( T - s ) }
$$

for positive constants $L _ { 6 }$ , which depends only on $p ,$ and $L _ { 7 }$ and $L _ { 8 }$ , which depend only on $C _ { 1 } , C _ { r } , C _ { 3 } , p$

Now we prove the second inequality. From the BDG inequality and Jensen’s inequality, we have

$$
\begin{array} { r l } & { \mathbb { E } _ { s } [ \| X - X _ { s } \| _ { s + \delta } ^ { p } ] = \mathbb { E } _ { s } \bigg [ \underset { s \leq r \leq s + \delta } { \operatorname* { s u p } } \left| X ( r ) - X ( s ) \right| ^ { p } \bigg ] } \\ & { \leq L \mathbb { E } _ { s } \bigg [ \bigg ( \int _ { s } ^ { s + \delta } \vert r ( u , X _ { u } ) X ( u ) \vert d u \bigg ) ^ { p } + \underset { s \leq r \leq s + \delta } { \operatorname* { s u p } } \bigg \vert \int _ { s } ^ { r } \sigma ( u , X _ { u } ) d B ( u ) \bigg \vert ^ { p } \bigg ] } \\ & { \leq L \bigg ( \mathbb { E } _ { s } \bigg [ \bigg ( \int _ { s } ^ { s + \delta } \vert r ( u , X _ { u } ) X ( u ) \vert d u \bigg ) ^ { p } \bigg ] + \mathbb { E } _ { s } \bigg [ \underset { s \leq r \leq s + \delta } { \operatorname* { s u p } } \bigg ( \int _ { s } ^ { r } \vert \sigma ( u , X _ { u } ) \vert ^ { 2 } d u \bigg ) ^ { \frac { p } { 2 } } \bigg ] \bigg ) } \\ & { \leq L \mathbb { E } _ { s } \bigg [ \delta ^ { p - 1 } \int _ { s } ^ { s + \delta } \vert X ( u ) \vert ^ { p } d u + \delta ^ { \frac { p } { 2 } - 1 } \int _ { s } ^ { s + \delta } \vert \sigma ( u , X _ { u } ) \vert ^ { p } d u \bigg ] } \\ & { \leq L ( 1 + \mathbb { E } _ { s } \| X \| _ { s + \delta } ^ { p } ) ^ { \frac { p } { 2 } } } \end{array}
$$

for some positive constant $L ,$ which depends only on $C _ { 1 } , C _ { r } , C _ { 3 } , p$ and may change line by line. This completes the proof. □

<!-- page: 21 -->

We now prove Theorem 3.2.

Proof. In this proof, L denotes a generic constant depending only on $C _ { 1 } , C _ { r } , C _ { 3 } , C _ { 4 } , \ell , \rho$ and may difer line by line. We first prove the uniqueness of solutions. Suppose there are two solutions $( Y ^ { 1 } , Z ^ { 1 } )$ and $( Y ^ { 2 } , Z ^ { 2 } )$ to (3.6). Define three processes

$$
\begin{array} { r l } & { \hat { Y } ( s ) = Y ^ { 1 } ( s ) - Y ^ { 2 } ( s ) , } \\ & { \hat { Z } ( s ) = Z ^ { 1 } ( s ) - Z ^ { 2 } ( s ) , } \\ & { \alpha ( s ) = \frac { f ( s , X _ { s } , Y ^ { 1 } ( s ) ) - f ( s , X _ { s } , Y ^ { 2 } ( s ) ) } { \hat { Y } ( s ) } \mathbf { 1 } _ { \{ | \hat { Y } ( s ) | > 0 \} } - \ell \mathbf { 1 } _ { \{ | \hat { Y } ( s ) | = 0 \} } . } \end{array}
$$

It can be easily shown that $\alpha ( s ) \leq - \ell$ and

$$
\hat { Y } ( s ) = \hat { Y } ( T ) + \int _ { s } ^ { T } \alpha ( u ) \hat { Y } ( u ) d u - \int _ { s } ^ { T } \hat { Z } ( u ) d B ( u ) .
$$

$\mathrm { B y }$ Proposition $\mathrm { A . 1 }$ , there are constants $L _ { 6 }$ and $L _ { 7 }$ , depending only on $C _ { 1 } , C _ { r } , C _ { 3 } , \rho ,$ such that

$$
\begin{array} { r } { \mathbb { E } _ { s } [ \| X \| _ { T } ^ { \rho } ] \le ( L _ { 6 } \| X \| _ { s } ^ { \rho } + L _ { 7 } ) e ^ { ( \epsilon + K + \frac { 1 } { 2 } ( \frac { C _ { r } } { \sqrt { 2 K } } + M _ { \rho \vee 2 } C _ { 3 } ) ^ { 2 } ) \rho ( T - s ) } } \end{array}
$$

for any $\epsilon > 0 , K > 0 , T > 0$ and $s \in [ 0 , T ]$ . As $\begin{array} { r } { \ell > \operatorname* { i n f } _ { K > 0 } \{ ( K + \frac { 1 } { 2 } ( \frac { C _ { r } } { \sqrt { 2 K } } + M _ { \rho \vee 2 } C _ { 3 } ) ^ { 2 } ) \rho \} } \end{array}$ , for some constant $L _ { 8 }$ with $0 < L _ { 8 } < \ell .$ , we have

$$
\mathbb { E } _ { s } [ \| X \| _ { T } ^ { \rho } ] \le ( L _ { 6 } \| X \| _ { s } ^ { \rho } + L _ { 7 } ) e ^ { L _ { 8 } ( T - s ) }\tag{A.4}
$$

for any $T > 0$ and $s \in [ 0 , T ]$ . It follows that

$$
\begin{array} { r } { | \hat { Y } ( s ) | = \left| \mathbb { E } _ { s } \Big [ e ^ { \int _ { s } ^ { T } \alpha ( u ) d u } \hat { Y } ( T ) \Big ] \right| \leq \mathbb { E } _ { s } \Big [ e ^ { - \ell ( T - s ) } L ( 1 + \| X \| _ { T } ^ { \rho } ) \Big ] } \\ { \leq L e ^ { - ( \ell - L _ { 8 } ) ( T - s ) } ( \| X \| _ { s } ^ { \rho } + 1 ) . } \end{array}
$$

Letting $T \to \infty$ , we have $Y ^ { 1 } - Y ^ { 2 } = { \hat { Y } } = 0$ . Moreover, this directly yields $Z ^ { 1 } = Z ^ { 2 }$

Now we prove the existence of solutions. For each $n \in \mathbb N$ , there exists a unique solution $( Y ^ { n } ( s ) , Z ^ { n } ( s ) ) _ { 0 \leq s \leq n }$ to the BSDE

$$
Y ^ { n } ( s ) = \int _ { s } ^ { n } f ( u , X _ { u } , Y ^ { n } ( u ) ) d u - \int _ { s } ^ { n } Z ^ { n } ( u ) d B ( u ) .
$$

We extend this solution $( Y ^ { n } ( s ) , Z ^ { n } ( s ) ) _ { 0 \leq s \leq n } { \mathrm { ~ t o ~ } } ( Y ^ { n } ( s ) , Z ^ { n } ( s ) ) _ { 0 \leq s < \infty }$ by defining $Y ^ { n } ( s ) = Z ^ { n } ( s ) =$ 0 for all $s > n$ . Then

$$
Y ^ { n } ( s ) = Y ^ { n } ( T ) + \int _ { s } ^ { T } f ( u , X _ { u } , Y ^ { n } ( u ) ) - \mathbf 1 _ { \{ u > n \} } f ( u , X _ { u } , 0 ) d u - \int _ { s } ^ { T } Z ^ { n } ( u ) d B ( u ) .
$$

For $m > n$ , define three processes

$$
\begin{array} { r l } & { \tilde { Y } ( s ) = Y ^ { m } ( s ) - Y ^ { n } ( s ) , } \\ & { \tilde { Z } ( s ) = Z ^ { m } ( s ) - Z ^ { n } ( s ) , } \\ & { \tilde { \alpha } ( s ) = \frac { f ( s , X _ { s } , Y ^ { m } ( s ) ) - f ( s , X _ { s } , Y ^ { n } ( s ) ) } { \tilde { Y } ( s ) } \mathbf { 1 } _ { \{ | \tilde { Y } ( s ) | > 0 \} } - \ell \mathbf { 1 } _ { \{ | \tilde { Y } ( s ) | = 0 \} } . } \end{array}
$$

It can be easily checked that $\tilde { \alpha } \leq - \ell$ and

$$
\tilde { Y } ( s ) = \int _ { s } ^ { m } \tilde { \alpha } ( u ) \tilde { Y } ( u ) + { \bf 1 } _ { \{ u > n \} } f ( u , X _ { u } , 0 ) d u - \int _ { s } ^ { m } \tilde { Z } ( u ) d B ( u ) .
$$

<!-- page: 22 -->

Then Itˆo’s formula and (A.4) yield

$$
\begin{array} { r l r } {  { \vert \tilde { Y } ( s ) \vert = \mathbb { E } _ { s } \Big [ \int _ { s } ^ { m } e ^ { \int _ { s } ^ { u } \tilde { \alpha } ( v ) d v } \mathbf { 1 } _ { \{ u > n \} } f ( u , X _ { u } , 0 ) d u \Big ] } } \\ & { } & { \leq \mathbb { E } _ { s } \Big [ \int _ { n } ^ { m } C _ { 4 } e ^ { - \ell ( u - s ) } ( 1 + \| X \| _ { u } ^ { \rho } ) d u \Big ] } \\ & { } & { \leq L ( 1 + \| X \| _ { s } ^ { \rho } ) ( e ^ { - ( \ell - L _ { 8 } ) ( n - s ) } - e ^ { - ( \ell - L _ { 8 } ) ( m - s ) } ) . } \end{array}
$$

Therefore for $0 \leq T \leq n \leq m$

$$
\operatorname* { l i m } _ { n , m \to \infty } \operatorname { \mathbb { E } } [ \operatorname* { s u p } _ { 0 \leq s \leq T } | Y ^ { n } ( s ) - Y ^ { m } ( s ) | ^ { 2 } ] = 0 .
$$

The sequence $( Y ^ { n } ) _ { n \in \mathbb { N } }$ is a Cauchy sequence in $\mathbb { S } ^ { 2 } ( 0 , T ; \mathbb { R } )$ for each $T > 0$ . Because $\mathbb { S } ^ { 2 } ( 0 , T ; \mathbb { R } )$ is complete, the limit $Y : = \operatorname* { l i m } _ { n \to \infty } Y ^ { n }$ exists. Applying Itˆo’s formula, we have

$$
| \tilde { Y } ( 0 ) | ^ { 2 } + \mathbb { E } \Big [ \int _ { 0 } ^ { T } | \tilde { Z } ( u ) | ^ { 2 } d u \Big ] = \mathbb { E } \Big [ | \tilde { Y } ( T ) | ^ { 2 } + \int _ { 0 } ^ { T } 2 \tilde { \alpha } ( u ) | \tilde { Y } ( u ) | ^ { 2 } d u \Big ] .
$$

From the inequality $\tilde { \alpha } ( s ) \leq - \ell ,$

$$
\begin{array} { r l r } {  { \mathbb { E } \Big [ \int _ { 0 } ^ { T } | Z ^ { m } ( u ) - Z ^ { n } ( u ) | ^ { 2 } d u \Big ] = \mathbb { E } \Big [ \int _ { 0 } ^ { T } | \tilde { Z } ( u ) | ^ { 2 } d u \Big ] = \mathbb { E } [ | \tilde { Y } ( T ) | ^ { 2 } ] } } \\ & { } & { \leq L ( 1 + \mathbb { E } [ \| X \| _ { T } ^ { 2 \rho } ] ) ( e ^ { - ( \ell - L _ { 8 } ) ( n - s ) } - e ^ { - ( \ell - L _ { 8 } ) ( m - s ) } ) ^ { 2 } . } \end{array}
$$

Thus, $( Z ^ { n } ) _ { n \in \mathbb { N } }$ is a Cauchy sequence in $\mathbb { H } ^ { 2 } ( 0 , T ; \mathbb { R } ^ { m } )$ . The limit $Z : = \operatorname* { l i m } _ { n \to \infty } Z ^ { n }$ exists in $\mathbb { H } ^ { 2 } ( 0 , T ; \mathbb { R } ^ { m } )$ . Because $( Y ^ { n } ( s ) , Z ^ { n } ( s ) ) _ { 0 \leq s \leq n }$ satisfies

$$
Y ^ { n } ( s ) = Y ^ { n } ( T ) + \int _ { s } ^ { T } f ( u , X _ { u } , Y ^ { n } ( u ) ) d u - \int _ { s } ^ { T } Z ^ { n } ( u ) d B ( u ) , 0 \leq s \leq T ,
$$

the Lebesgue dominated convergence theorem implies that the pair $( Y , Z )$ is a solution to (3.6). Now we prove that there exists a constant $L > 0$ such that $\| Y \| \leq L ( 1 + \| X \| ^ { \rho } )$ . As $Y =$ $\scriptstyle \operatorname* { l i m } _ { n \to \infty } Y ^ { n }$ , it sufices to prove $\\| Y ^ { n } \| \leq L ( 1 + \| X \| ^ { \rho } )$ . Define

$$
\overline { { \alpha } } ( s ) : = \frac { f ( s , X _ { s } , Y ^ { n } ( s ) ) - f ( s , X _ { s } , 0 ) } { Y ^ { n } ( s ) } { \bf 1 } _ { \{ | Y ^ { n } ( s ) | > 0 \} } - \ell { \bf 1 } _ { \{ | Y ^ { n } ( s ) | = 0 \} } ,
$$

then

$$
Y ^ { n } ( s ) = \int _ { s } ^ { n } ( \overline { { \alpha } } ( u ) Y ^ { n } ( u ) + f ( u , X _ { u } , 0 ) ) d u - \int _ { s } ^ { n } Z ^ { n } ( u ) d B ( u ) , 0 \leq s \leq n .
$$

Using Itˆo’s formula, (A.4) and the inequality $\overline { { \alpha } } ( s ) < - \ell ,$ , we have

$$
| Y ^ { n } ( s ) | \leq \mathbb { E } _ { s } { \Big [ } \int _ { s } ^ { n } e ^ { - \ell ( u - s ) } | f ( u , X _ { u } , 0 ) | d u { \Big ] } \leq L ( 1 + \| X \| _ { s } ^ { \rho } ) .\tag{A.5}
$$

This completes the proof.

## B Feynman-Kac formula

We present the notions of path-dependent PDEs (PPDEs) and provide the proof of the Feynman-Kac formula stated in Theorem 3.3. For non-anticipative functionals $r : [ 0 , \infty ) \times \Lambda $ R, $\sigma : [ 0 , \infty ) \times \Lambda \to { \mathbb { R } } ^ { m \times m }$ and $f : [ 0 , \infty ) \times \Lambda \times \mathbb { R } \to$ R, consider the PPDE

$$
- \partial _ { s } \varphi ( s , \gamma ) - \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \varphi ) ( s , \gamma ) - r ( s , \gamma ) \partial _ { x } \varphi ( s , \gamma ) \gamma ( s ) - f ( s , \gamma , \varphi ( s , \gamma ) ) = 0\tag{B.1}
$$

for $( s , \gamma ) \in [ 0 , \infty ) \times \Lambda$ . The definition of classical solutions to PPDEs is as follows. Classical solutions are often referred to simply as solutions.

<!-- page: 23 -->

Definition B.1. Let $\varphi \in C _ { p } ^ { 1 , 2 } ( [ 0 , \infty ) \times \Lambda )$

(i) We say $\varphi$ is a classical subsolution (supersolution, respectively) to the PPDE (B.1) if

$$
- \partial _ { s } \varphi ( s , \gamma ) - \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \varphi ) ( s , \gamma ) - r ( s , \gamma ) \partial _ { x } \varphi ( s , \gamma ) \gamma ( s ) - f ( s , \gamma , \varphi ( s , \gamma ) ) \leq 0
$$

for all $( s , \gamma ) \in [ 0 , \infty ) \times \Lambda$

(ii) We say $\varphi$ is a classical solution to the PPDE (B.1) if φ is both a classical subsolution and classical supersolution.

For $s \geq 0$ , define $\Lambda _ { s } : = C ( [ 0 , s ] ; \mathbb { R } ^ { m } )$ and $\Lambda _ { s + 1 } ^ { s } : = C ( [ s , s + 1 ] ; \mathbb { R } ^ { m } )$ equipped with the supremum norm. Let $( \mathcal { F } _ { u } ^ { s } ) _ { u \geq 0 }$ be the filtration generated by $( ( B ( u ) - B ( s ) ) \mathbf { 1 } _ { u \geq s } ) _ { u \geq 0 }$ . Denote as $\mathcal { T } _ { s + 1 , + } ^ { s }$ the set of $( \mathcal { F } _ { u } ^ { s } ) _ { 0 \leq u \leq s + 1 }$ -stopping times such that $\tau > s$ . For $( s , \gamma ) \in [ 0 , \infty ) \times \Lambda$ and $\varphi \in \dot { C } _ { p } ( [ 0 , \infty ) \times \Lambda )$ , we define the spaces

$$
\mathcal { A } \varphi ( s , \gamma ) : = \{ \psi \in C _ { p } ^ { 1 , 2 } ( [ 0 , \infty ) \times \Lambda ) | \mathrm { t h e r e ~ e x i s t s ~ } \tau \in \mathcal { T } _ { s + 1 , + } ^ { s }
$$

$$
\mathrm { s u c h \ t h a t \ 0 } = \psi ( s , \gamma ) - \varphi ( s , \gamma ) = \operatorname* { m i n } _ { \tilde { \tau } \in \mathcal { T } _ { s + 1 } ^ { s } } \mathbb { E } [ ( \psi - \varphi ) ( \tau \wedge \tilde { \tau } , X ^ { s , \gamma } ) ] \} ,
$$

$$
\overline { { \mathscr { A } } } \varphi ( s , \gamma ) : = \{ \psi \in C _ { p } ^ { 1 , 2 } ( [ 0 , \infty ) \times \Lambda ) | \mathrm { t h e r e ~ e x i s t s ~ } \tau \in { \mathscr T } _ { s + 1 , + } ^ { s }
$$

$$
\mathrm { s u c h \ t h a t \ 0 } = \psi ( s , \gamma ) - \varphi ( s , \gamma ) = \operatorname* { m a x } _ { \tilde { \tau } \in \mathcal { T } _ { s + 1 } ^ { s } } \mathbb { E } [ ( \psi - \varphi ) ( \tau \wedge \tilde { \tau } , X ^ { s , \gamma } ) ] \} ,
$$

where $X ^ { s , \gamma }$ is a solution to the SDE (3.8).

Definition B.2. Let $\varphi \in C _ { p } ( [ 0 , \infty ) \times \Lambda )$

(i) We say $\varphi$ is a viscosity subsolution (superslution, respectively) to the PPDE (B.1) if

$$
- \partial _ { s } \psi ( s , \gamma ) - \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \psi ) ( s , \gamma ) - r ( s , \gamma ) \partial _ { x } \psi ( s , \gamma ) \gamma ( s ) - f ( s , \gamma , \psi ( s , \gamma ) ) \leq 0
$$

for all $( s , \gamma ) \in [ 0 , \infty ) \times \Lambda$ and $\psi \in \underline { { A } } \varphi ( s , \gamma ) ~ / \psi \in \overline { { A } } \varphi ( s , \gamma )$ , respectively).

(ii) We say $\varphi$ is a viscosity solution to the PPDE (B.1) $i f \varphi$ is both a viscosity subsolution and viscosity supersolution.

Theorem B.1. Suppose that the functionals $r , \sigma , f$ are continuous and $\varphi \in C _ { p } ^ { 1 , 2 } ( [ 0 , \infty ) \times \Lambda )$ Then $\varphi$ is a classical subsolution (supersolution, respectively) to the PPDE $\left( \mathrm { B . 1 } \right)$ if and only $i f$ $\varphi$ is a viscosity subsolution (supersolution, respectively) to the PPDE (B.1).

Proof. We only prove the subsolution property. Assume that $\varphi$ is a viscosity subsolution to (B.1). Since $\varphi \in \mathcal { A } \varphi ( s , \gamma )$ for $( s , \gamma ) \in [ 0 , \infty ) \times \Lambda$ , it follows that $\varphi$ is a classical subsolution.

Now we show that if $\varphi$ is a classical subsolution then $\varphi$ is a viscosity subsolution. Suppose $\varphi$ is not a viscosity subsolution. Then, there exists $( s , \gamma ) \in [ 0 , \infty ) \times \Lambda$ and $\psi \in \mathcal { A } \varphi ( s , \gamma )$ such that

$$
- M : = \partial _ { s } \psi ( s , \gamma ) + \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \psi ) ( s , \gamma ) + r ( s , \gamma ) \partial _ { x } \psi ( s , \gamma ) \gamma ( s ) + f ( s , \gamma , \psi ( s , \gamma ) ) < 0 .
$$

From the definition of $\underline { { { A } } } \varphi ( s , \gamma )$ , there exists $\tau \in \mathcal { T } _ { s + 1 , + } ^ { s }$ such that

$$
0 = \psi ( s , \gamma ) - \varphi ( s , \gamma ) = \operatorname* { m i n } _ { \tilde { \tau } \in \mathcal { T } _ { s + 1 } ^ { s } } \mathbb { E } [ ( \psi - \varphi ) ( \tau \wedge \tilde { \tau } , X ^ { s , \gamma } ) ] .
$$

<!-- page: 24 -->

Define six processes

$$
Y ^ { 1 } ( v ) = \psi ( v , X _ { v } ^ { s , \gamma } ) , ~ Z ^ { 1 } ( v ) = { \sigma } ^ { \top } ( v , X _ { v } ^ { s , \gamma } ) \partial _ { x } \psi ( v , X _ { v } ^ { s , \gamma } ) ,
$$

$$
Y ^ { 2 } ( v ) = \varphi ( v , X _ { v } ^ { s , \gamma } ) , \ Z ^ { 2 } ( v ) = \sigma ^ { \top } ( v , X _ { v } ^ { s , \gamma } ) \partial _ { x } \varphi ( v , X _ { v } ^ { s , \gamma } ) ,
$$

$$
\hat { Y } ( v ) = Y ^ { 1 } ( v ) - Y ^ { s , \gamma } ( v ) , \ \hat { Z } ( v ) = Z ^ { 1 } ( v ) - Z ^ { s , \gamma } ( v )
$$

for $s \leq v \leq s + 1$ and a stopping time

$$
\begin{array} { r l } & { \hat { \boldsymbol { \tau } } : = ( s + 1 ) \wedge \boldsymbol { \tau } \wedge \operatorname* { i n f } \Big \{ v > s \Big | \partial _ { v } \psi ( v , X _ { v } ^ { s , \gamma } ) + \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \psi ) ( v , X _ { v } ^ { s , \gamma } ) } \\ & { \qquad + r ( v , X _ { v } ^ { s , \gamma } ) \partial _ { x } \psi ( v , X _ { v } ^ { s , \gamma } ) X ^ { s , \gamma } ( v ) + f ( v , X _ { v } ^ { s , \gamma } , Y ^ { 2 } ( v ) ) > - \frac { M } { 2 } \Big \} . } \end{array}
$$

By definition, we have $\hat { \tau } \in \mathcal { T } _ { s + 1 , + } ^ { s }$ since $\varphi , \psi \in C _ { p } ^ { 1 , 2 } ( [ 0 , \infty ) \times \Lambda )$ . By Theorem C.1, we have

$$
\begin{array} { l } { { \displaystyle Y ^ { 1 } ( s ) = \psi ( s + 1 , X _ { s + 1 } ^ { s , \gamma } ) - \int _ { s } ^ { s + 1 } \partial _ { u } \psi ( u , X _ { u } ^ { s , \gamma } ) + \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \psi ) ( u , X _ { u } ^ { s , \gamma } ) \ ~ } } \\ { { \displaystyle \quad \qquad + r ( u , X _ { u } ^ { s , \gamma } ) \partial _ { x } \psi ( u , X _ { u } ^ { s , \gamma } ) X ^ { s , \gamma } ( u ) d u - \int _ { s } ^ { s + 1 } Z ^ { 1 } ( u ) d B ( u ) \ , } } \end{array}
$$

$$
\begin{array} { l } { { \displaystyle Y ^ { 2 } ( s ) = \varphi ( s + 1 , X _ { s + 1 } ^ { s , \gamma } ) - \int _ { s } ^ { s + 1 } \partial _ { u } \varphi ( u , X _ { u } ^ { s , \gamma } ) + \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \varphi ) ( u , X _ { u } ^ { s , \gamma } ) } \ ~ } \\ { { \displaystyle ~ + r ( u , X _ { u } ^ { s , \gamma } ) \partial _ { x } \varphi ( u , X _ { u } ^ { s , \gamma } ) X ^ { s , \gamma } ( u ) d u - \int _ { s } ^ { s + 1 } Z ^ { 2 } ( u ) d B ( u ) . } } \end{array}
$$

Then

$$
\begin{array} { l } { \displaystyle \hat { Y } ( \hat { \tau } ) = \int _ { s } ^ { \hat { \tau } } \partial _ { u } \psi ( u , X _ { u } ^ { s , \gamma } ) + \frac 1 { 2 } \mathrm { t r } \big ( \sigma \sigma ^ { \top } \partial _ { x x } \psi \big ) ( u , X _ { u } ^ { s , \gamma } ) + r \big ( u , X _ { u } ^ { s , \gamma } ) \partial _ { x } \psi ( u , X _ { u } ^ { s , \gamma } ) X ^ { s , \gamma } ( u ) d u } \\ { \displaystyle \qquad - \int _ { s } ^ { \hat { \tau } } \partial _ { u } \varphi ( u , X _ { u } ^ { s , \gamma } ) + \frac 1 { 2 } \mathrm { t r } \big ( \sigma \sigma ^ { \top } \partial _ { x x } \varphi \big ) ( u , X _ { u } ^ { s , \gamma } ) + r \big ( u , X _ { u } ^ { s , \gamma } ) \partial _ { x } \varphi ( u , X _ { u } ^ { s , \gamma } ) X ^ { s , \gamma } ( u ) d u } \\ { \displaystyle \qquad + \int _ { s } ^ { \hat { \tau } } \hat { Z } ( u ) d B ( u ) . } \end{array}
$$

We have

$$
\begin{array} { r l } & { \displaystyle \partial _ { v } \psi ( v , X _ { v } ^ { s , \gamma } ) + \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \psi ) ( v , X _ { v } ^ { s , \gamma } ) + r ( v , X _ { v } ^ { s , \gamma } ) \partial _ { x } \psi ( v , X _ { v } ^ { s , \gamma } ) X ^ { s , \gamma } ( v ) } \\ & { \displaystyle + f ( v , X _ { v } ^ { s , \gamma } , Y ^ { 2 } ( v ) ) \leq - \frac { M } { 2 } } \end{array}\tag{B.2}
$$

for $v \in [ s , \hat { \tau } ]$ from the definition of $\tilde { \tau } .$ . Since $\varphi$ is a classical solution to (B.1),

$$
\begin{array} { r l } & { \displaystyle \partial _ { v } \varphi ( v , X _ { v } ^ { s , \gamma } ) + \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \varphi ) ( v , X _ { v } ^ { s , \gamma } ) + r ( v , X _ { v } ^ { s , \gamma } ) \partial _ { x } \varphi ( v , X _ { v } ^ { s , \gamma } ) X ^ { s , \gamma } ( v ) } \\ & { \displaystyle + f ( v , X _ { v } ^ { s , \gamma } , \varphi ( v , X _ { v } ^ { s , \gamma } ) ) \geq 0 . } \end{array}\tag{B.3}
$$

Using (B.2) and (B.3), we obtain

$$
\hat { Y } ( \hat { \tau } ) \leq \int _ { s } ^ { \hat { \tau } } - \frac { M } { 2 } d u + \int _ { s } ^ { \hat { \tau } } \hat { Z } ( u ) d B ( u ) ,
$$

which implies that $\mathbb { E } [ \hat { Y } ( \hat { \tau } ) ] < 0$ . This is a contradiction since $\psi \in \mathcal { A } \varphi ( s , \gamma )$ yields that

$$
0 = \operatorname* { m i n } _ { \bar { \tau } \in \mathcal { T } ^ { s } } \mathbb { E } [ ( \psi - \varphi ) ( \tau \wedge \tilde { \tau } , X ^ { s , \gamma } ) ] \} \leq \mathbb { E } [ ( \psi - \varphi ) ( \tau \wedge \hat { \tau } , X ^ { s , \gamma } ) ] = \mathbb { E } [ \hat { Y } ( \hat { \tau } ) ] < 0 .
$$

<!-- page: 25 -->

We now provide the proof of Theorem 3.3.

Proof. First we show that (3.9) has a unique solution $( Y ^ { s , \gamma } ( v ) , Z ^ { s , \gamma } ( v ) ) _ { v \geq s }$ such that $\| Y ^ { s , \gamma } \| \leq$ $L ( 1 + \| X ^ { s , \gamma } \| ^ { \rho } )$ for some constant $L > 0$ . The proof follows a similar approach to that of Theorem 3.2, so we will only outline the main idea. For each $n \in \mathbb { N }$ , consider the BSDE

$$
Y ^ { n , s , \gamma } ( v ) = \int _ { v } ^ { n } f ( u , X _ { u } ^ { s , \gamma } , Y ^ { n , s , \gamma } ( u ) ) d u - \int _ { v } ^ { n } Z ^ { n , s , \gamma } ( u ) d B ( u ) , s \leq v \leq n .
$$

There exist positive constants $L _ { 6 } , L _ { 7 } , L _ { 8 } , L$ such that

$$
\begin{array} { r l } & { L _ { 8 } < \ell , } \\ & { \mathbb { E } _ { v } [ \| X ^ { s , \gamma } \| _ { T } ^ { \rho } ] \leq ( L _ { 6 } \| X ^ { s , \gamma } \| _ { v } ^ { \rho } + L _ { 7 } ) e ^ { L _ { 8 } ( T - v ) } , } \\ & { | Y ^ { n , s , \gamma } ( v ) - Y ^ { m , s , \gamma } ( v ) | \leq L ( 1 + \| X ^ { s , \gamma } \| _ { v } ^ { \rho } ) ( e ^ { - ( \ell - L _ { 8 } ) ( n - v ) } - e ^ { - ( \ell - L _ { 8 } ) ( m - v ) } ) } \end{array}\tag{B.4}
$$

for all $T > 0$ and $v \in [ s , T ]$ . Using these inequalities, one can verify that a sequence $( Y ^ { n , s , \gamma } ) _ { n \in \mathbb { N } }$ $( ( Z ^ { n , s , \gamma } ) _ { n \in \mathbb { N } } .$ , respectively) converges in $\mathbb { S } ^ { 2 } ( 0 , T ; \mathbb { R } ) ( \mathrm { i n } \mathbb { H } ^ { 2 } ( 0 , T ; \mathbb { R } ^ { d } )$ , respectively) for each $T > 0$ Then, $\begin{array} { r } { ( Y ^ { s , \gamma } , Z ^ { s , \gamma } ) : = \operatorname* { l i m } _ { n \infty } ( Y ^ { n , s , \gamma } , Z ^ { n , s , \gamma } ) } \end{array}$ is a unique solution to (3.9). This proves (i).

For (ii), we verify that $Y ^ { 0 , x } ( v ) = \varphi ( v , X _ { v } ^ { 0 , x } )$ and $\varphi = \varphi ( s , \gamma )$ is a viscosity solution to (3.10). For each $n \in \mathbb { N } ,$ define $\varphi ^ { n } ( s , \gamma ) : = Y ^ { n , s , \gamma } ( s )$ . By (Cordoni et al., 2020, Theorem 4.5, Theorem $4 . 7 ) , \ \varphi ^ { n }$ is a continuous function and $Y ^ { n , 0 , x } ( v ) = \varphi ^ { n } ( v , X _ { v } ^ { 0 , x } )$ . Since the sequence $( \varphi ^ { n } ) _ { n \in \mathbb { N } }$ converges locally uniformly on $[ 0 , \infty ) \times \Lambda$ by (B.4), the function $\varphi : [ 0 , \infty ) \times \Lambda \to \mathbb { R }$ given as $\begin{array} { r } { \varphi ( s , \gamma ) : = \operatorname* { l i m } _ { n \to \infty } \varphi ^ { n } ( s , \gamma ) } \end{array}$ for $( s , \gamma ) \in [ 0 , \infty ) \times \Lambda$ is also continuous. In addition, for $\omega \in \Omega$

$$
\varphi ( v , X _ { v } ^ { 0 , x } ( \omega ) ) = \operatorname* { l i m } _ { n \to \infty } \varphi ^ { n } ( v , X _ { v } ^ { 0 , x } ( \omega ) ) = \operatorname* { l i m } _ { n \to \infty } Y ^ { n , 0 , x } ( v , \omega ) = Y ^ { 0 , x } ( v , \omega ) .
$$

Now we will demonstrate that $\varphi$ is a viscosity solution to (3.10). For our purposes, we will focus on proving that $\varphi$ is a viscosity subsolution, as a similar argument will show that $\varphi$ is also a viscosity supersolution. Assume that $\varphi$ is not a viscosity subsolution. We will derive a contradiction from this assumption. There exist $( s , \gamma ) \in [ 0 , \infty ) \times \Lambda$ and $\psi \in \mathcal { A } \varphi ( s , \gamma )$ such that

$$
- M : = \partial _ { s } \psi ( s , \gamma ) + \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \psi ) ( s , \gamma ) + r ( s , \gamma ) \partial _ { x } \psi ( s , \gamma ) \gamma ( s ) + f ( s , \gamma , \psi ( s , \gamma ) ) < 0 .
$$

From the definition of $\underline { { { A } } } \varphi ( s , \gamma )$ , there exists $\tau \in \mathcal { T } _ { s + 1 , + } ^ { s }$ such that

$$
0 = \psi ( s , \gamma ) - \varphi ( s , \gamma ) = \operatorname* { m i n } _ { \tilde { \tau } \in \mathcal { T } _ { s + 1 } ^ { s } } \mathbb { E } [ ( \psi - \varphi ) ( \tau \wedge \tilde { \tau } , X ^ { s , \gamma } ) .\tag{B.5}
$$

Let $C _ { f }$ denote the Lipschitz constant of the function f presented in (iii), i.e.,

$$
| f ( v , \gamma , y ) - f ( v , \gamma , y ^ { \prime } ) | \leq C _ { f } | y - y ^ { \prime } |
$$

for all $( s , \gamma ) \in [ 0 , \infty ) \times \Lambda$ and $y , y ^ { \prime } \in \mathbb { R }$ . Define four processes

$$
\begin{array} { r l } & { Y ^ { 1 } ( v ) : = \psi ( v , X _ { v } ^ { s , \gamma } ) , \ Z ^ { 1 } ( v ) : = \sigma ^ { \top } ( v , X _ { v } ^ { s , \gamma } ) \partial _ { x } \psi ( v , X _ { v } ^ { s , \gamma } ) , } \\ & { \hat { Y } ( v ) : = Y ^ { 1 } ( v ) - Y ^ { s , \gamma } ( v ) , \ \hat { Z } ( v ) : = Z ^ { 1 } ( v ) - Z ^ { s , \gamma } ( v ) } \end{array}
$$

for $s \leq v \leq s + 1$ , and a stopping time

$$
\begin{array} { r l } & { \hat { \tau } : = ( s + 1 ) \wedge \tau \wedge \operatorname* { i n f } \Big \{ v > s \Big | \partial _ { v } \psi ( v , X _ { v } ^ { s , \gamma } ) + \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \psi ) ( v , X _ { v } ^ { s , \gamma } ) } \\ & { \qquad + r ( v , X _ { v } ^ { s , \gamma } ) \partial _ { x } \psi ( v , X _ { v } ^ { s , \gamma } ) X ^ { s , \gamma } ( v ) + f ( v , X _ { v } ^ { s , \gamma } , \psi ( v , X _ { v } ^ { s , \gamma } ) ) } \\ & { \qquad + C _ { f } | \dot { Y } ( v ) | > - \displaystyle \frac { M } { 2 } \Big \} . } \end{array}
$$

<!-- page: 26 -->

By definition, it is evident that $\hat { \tau } \in \mathcal { T } _ { s + 1 , + } ^ { s }$ . By Theorem C.1, $( Y ^ { 1 } ( v ) , Z ^ { 1 } ( v ) ) _ { s \leq v \leq s + 1 }$ satisfies

$$
\begin{array} { l } { { \displaystyle Y ^ { 1 } ( s ) = \psi ( s + 1 , X _ { s + 1 } ^ { s , \gamma } ) - \int _ { s } ^ { s + 1 } \partial _ { u } \psi ( u , X _ { u } ^ { s , \gamma } ) + \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \psi ) ( u , X _ { u } ^ { s , \gamma } ) \nonumber } } \\ { { \displaystyle \phantom { \frac { 1 } { 1 } } + r ( u , X _ { u } ^ { s , \gamma } ) \partial _ { x } \psi ( u , X _ { u } ^ { s , \gamma } ) X ^ { s , \gamma } ( u ) d u - \int _ { s } ^ { s + 1 } Z ^ { 1 } ( u ) d B ( u ) . } } \end{array}
$$

Then,

$$
\begin{array} { l } { \displaystyle \hat { Y } ( s ) = \hat { Y } ( \hat { \tau } ) - \int _ { s } ^ { \hat { \tau } } \partial _ { u } \psi ( u , X _ { u } ^ { s , \gamma } ) + \frac 1 2 \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \psi ) ( u , X _ { u } ^ { s , \gamma } ) + r ( u , X _ { u } ^ { s , \gamma } ) \partial _ { x } \psi ( u , X _ { u } ^ { s , \gamma } ) X ^ { s , \gamma } ( u ) } \\ { \displaystyle \qquad + f ( u , X _ { u } ^ { s , \gamma } , Y ^ { s , \gamma } ( u ) ) d u - \int _ { s } ^ { \hat { \tau } } \hat { Z } ( u ) d B ( u ) . } \end{array}
$$

Observe that $\hat { Y } ( s ) = 0$ and

$$
\begin{array} { r l } & { \displaystyle \partial _ { v } \psi ( v , X _ { v } ^ { s , \gamma } ) + \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \psi ) ( v , X _ { v } ^ { s , \gamma } ) + r ( v , X _ { v } ^ { s , \gamma } ) \partial _ { x } \psi ( v , X _ { v } ^ { s , \gamma } ) X ^ { s , \gamma } ( v ) } \\ & { \displaystyle + f ( v , X _ { v } ^ { s , \gamma } , \psi ( v , X _ { v } ^ { s , \gamma } ) ) + C _ { f } | \hat { Y } ( v ) | \leq - \frac M 2 \ \mathrm { f o r } \ v \in [ s , \hat { \tau } ] . } \end{array}
$$

Thus,

$$
\hat { Y } ( \hat { \tau } ) \leq \int _ { s } ^ { \hat { \tau } } - \frac { M } { 2 } - C _ { f } | \hat { Y } ( u ) | - f ( u , X _ { u } ^ { s , \gamma } , Y ^ { 1 } ( u ) ) + f ( u , X _ { u } ^ { s , \gamma } , Y ^ { 2 } ( u ) ) d u - \int _ { s } ^ { \hat { \tau } } \hat { Z } ( u ) d B ( u ) .
$$

Observe that $\mathbb { E } [ \hat { Y } ( \hat { \tau } ) ] = \mathbb { E } [ \psi ( \hat { \tau } , X _ { \hat { \tau } } ) - \varphi ( \hat { \tau } , X _ { \hat { \tau } } ) ) ] \geq 0$ , which is derived from (B.5), and

$$
- C _ { f } | \hat { Y } ( u ) | - f ( u , X _ { u } ^ { s , \gamma } , Y ^ { 1 } ( u ) ) + f ( u , X _ { u } ^ { s , \gamma } , Y ^ { 2 } ( u ) ) < 0 .
$$

This gives a contradiction.

For (iii), we suppose $\varphi \in C _ { \rho } ^ { 1 , 2 } ( [ 0 , \infty ) \times \Lambda )$ . Theorem C.1 and (3.10) imply

$$
\begin{array} { l } { \displaystyle \varphi ( v , X _ { v } ^ { 0 , x } ) = \varphi ( T , X _ { T } ^ { 0 , x } ) - \int _ { v } ^ { T } \partial _ { u } \varphi ( u , X _ { u } ^ { 0 , x } ) + \frac 1 { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \varphi ) ( u , X _ { u } ^ { 0 , x } ) } \\ { \displaystyle \qquad + r ( u , X _ { u } ^ { 0 , x } ) \partial _ { x } \varphi ( u , X _ { u } ^ { 0 , x } ) X ^ { 0 , x } ( u ) d u - \int _ { v } ^ { T } \sigma ^ { \top } \partial _ { x } \varphi ( u , X _ { u } ^ { 0 , x } ) d B ( u ) } \\ { \displaystyle \qquad = \varphi ( T , X _ { T } ^ { 0 , x } ) + \int _ { v } ^ { T } f ( u , X _ { u } ^ { 0 , x } , \varphi ( s , X _ { s } ^ { 0 , x } ) ) d u - \int _ { v } ^ { T } \sigma ^ { \top } \partial _ { x } \varphi ( u , X _ { u } ^ { 0 , x } ) d B ( u ) . } \end{array}
$$

It is evident that $| \varphi ( v , X _ { v } ^ { 0 , x } ) | \leq L ( 1 + \| X ^ { 0 , x } \| _ { v } ^ { \rho } )$ since $\varphi \in C _ { \rho } ^ { 1 , 2 } ( [ 0 , \infty ) \times \Lambda )$ . The uniqueness of Theorem 3.2 gives the desired result. □

## C Proofs of the main results in Section 4.1

We first state the functional Itˆo formula, which is used to show Theorem 4.1. The proof of this formula is in Bally et al. (2016).

Theorem C.1. Let X be a continuous semimartingale. Then for any $F \in C _ { p } ^ { 1 , 2 } ( [ 0 , \infty ) \times \Lambda )$ , we have

$$
F ( s , X _ { s } ) = F ( 0 , X _ { 0 } ) + \int _ { 0 } ^ { s } \partial _ { u } F ( u , X _ { u } ) d u + \int _ { 0 } ^ { s } \partial _ { x } F ( u , X _ { u } ) d X ( u ) + \frac { 1 } { 2 } \int _ { 0 } ^ { s } \mathrm { t r } \partial _ { x x } ^ { 2 } F ( u , X _ { u } ) d [ X ] ( u ) .
$$

<!-- page: 27 -->

The proof of Theorem 4.1 is as follows.

Proof. For (i), we first show that the map $y _ { 1 } \mapsto H ( y _ { 1 } , 0 )$ has linear growth. More precisely, there exists a constant $C > 0$ such that $| H ( y _ { 1 } , 0 ) | \le C | y _ { 1 } |$ for all $y _ { 1 } \in \mathbb { R }$ . From (i) in Assumption 4.1, the function H can be written as $H ( y _ { 1 } , y _ { 2 } ) = g ( y _ { 1 } , y _ { 2 } ) ( y _ { 1 } - y _ { 2 } )$ for some function $g : \mathbb { R } ^ { 2 } \mathbb { R }$ Thus, it sufices to show that the map $y _ { 1 } \mapsto g ( y _ { 1 } , 0 )$ is bounded. By (ii) in Assumption 4.1, there exists a constant $C _ { H } > 0$ such that

$$
| ( y _ { 1 } - y _ { 2 } ) g ( y _ { 1 } , y _ { 2 } ) - ( y _ { 1 } - y _ { 2 } ^ { \prime } ) g ( y _ { 1 } , y _ { 2 } ^ { \prime } ) | = | H ( y _ { 1 } , y _ { 2 } ) - H ( y _ { 1 } , y _ { 2 } ^ { \prime } ) | \leq C _ { H } | y _ { 2 } - y _ { 2 } ^ { \prime } |
$$

for all $y _ { 1 } , y _ { 2 } , y _ { 2 } ^ { \prime } \in \mathbb { R }$ . Setting $y _ { 1 } = y _ { 2 }$ and $y _ { 2 } ^ { \prime } = 0$ yields $| y _ { 1 } g ( y _ { 1 } , 0 ) | \le C _ { H } | y _ { 1 } |$ , which implies $| g ( y _ { 1 } , 0 ) | \le C _ { H }$ for $y _ { 1 } \neq 0$ . Hence, the map $y _ { 1 } \mapsto g ( y _ { 1 } , 0 )$ is bounded, and the desired linear growth condition for $H ( y _ { 1 } , 0 )$ follows.

Now observe that

$$
\Phi ( s , \gamma , 0 ) = H ( \varphi ( s , \gamma ) , 0 ) - \partial _ { s } \varphi ( s , \gamma ) - \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \varphi ) ( s , \gamma ) - r ( s , \gamma ) \partial _ { x } \varphi ( s , \gamma ) \gamma ( s ) .
$$

The terms $H ( \varphi ( s , \gamma ) , 0 ) , \partial _ { s } \varphi ( s , \gamma ) , \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \varphi ) ( s , \gamma ) , r ( s , \gamma ) \partial _ { x } \varphi ( s , \gamma ) \gamma ( s )$ have polynomial growth of orders $p , p , p + 2 , p + 1$ at most, respectively, in $( s , \gamma )$ . This implies that the map $( s , \gamma ) \mapsto$ $\Phi ( s , \gamma , 0 )$ has polynomial growth. There exist constants $\rho \geq 1$ and $C _ { \Phi } > 0$ be constants such that $| \Phi ( s , \gamma , 0 ) | \le C _ { \Phi } ( 1 + \| \gamma \| _ { s } ^ { \rho } )$ for all $( s , \gamma ) \in [ 0 , \infty ) \times \Lambda$ . One may choose $\rho \geq p$

We now show (ii). Recall the BSDE (3.6)

$$
Y ( s ) = Y ( T ) - \int _ { s } ^ { T } ( r ( u , X _ { u } ) Y ( u ) - \Phi ( u , X _ { u } , Y ( u ) ) ) d u - \int _ { s } ^ { T } Z ( u ) d B ( u ) .
$$

By Theorem 3.2, this BSDE has a unique solution $( Y , Z )$ in $\mathbb { S } ^ { 2 } ( 0 , \infty ; \mathbb { R } ) \times \mathbb { H } ^ { 2 } ( 0 , \infty ; \mathbb { R } ^ { m } )$ such that $\vert Y \vert \leq L ( 1 + \| X \| ^ { \rho } )$ for some positive constant L. Define

$$
( Y ^ { \prime } , Z ^ { \prime } ) = ( \varphi ( s , X _ { s } ) , ( \partial _ { x } \varphi \sigma ) ( s , X _ { s } ) ) _ { s \geq 0 } ,
$$

then $( Y ^ { \prime } , Z ^ { \prime } )$ is also a solution to the BSDE (3.6) because

$$
\begin{array} { l } { \displaystyle Y ^ { \prime } ( s ) = Y ^ { \prime } ( T ) + \int _ { s } ^ { T } - \partial _ { u } \varphi ( u , X _ { u } ) - \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \varphi ) ( u , X _ { u } ) - r ( u , X _ { u } ) \partial _ { x } \varphi ( u , X _ { u } ) X ( u ) d u } \\ { \displaystyle \qquad - \int _ { s } ^ { T } { Z ^ { \prime } ( u ) d B ( u ) } } \\ { = Y ^ { \prime } ( T ) + \int _ { s } ^ { T } { H ( \varphi ( u , X _ { u } ) , Y ^ { \prime } ( u ) ) - \partial _ { u } \varphi ( u , X _ { u } ) } } \\ { \displaystyle \qquad - \frac { 1 } { 2 } \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } \varphi ) ( u , X _ { u } ) - r ( u , X _ { u } ) \partial _ { x } \varphi ( u , X _ { u } ) { X ( u ) } d u - \int _ { s } ^ { T } { Z ^ { \prime } ( u ) d B ( u ) } } \\ { = Y ^ { \prime } ( T ) - \int _ { s } ^ { T } { r ( u , X _ { u } ) Y ^ { \prime } ( u ) - \Phi ( u , X _ { u } , Y ^ { \prime } ( u ) ) d u } - \int _ { s } ^ { T } { Z ^ { \prime } ( u ) d B ( u ) } . } \end{array}
$$

As $\varphi \in C _ { p } ^ { 1 , 2 } ( [ 0 , \infty ) \times \Lambda )$ , we know that $( Y ^ { \prime } , Z ^ { \prime } ) \in \mathbb { S } ^ { 2 } ( 0 , \infty ; \mathbb { R } ) \times \mathbb { H } ^ { 2 } ( 0 , \infty ; \mathbb { R } ^ { m } )$ and $| Y ^ { \prime } | ~ \leq$ $L ( 1 + \| X \| ^ { p } )$ for some positive constant $L .$ Since $p \leq \rho ,$ , by the uniqueness in Theorem 3.2, we have $Y = Y ^ { \prime }$ and $Z = Z ^ { \prime }$ □

The proof of Corollary 4.2 is as follows.

Proof. This is directly obtained by showing $| \Phi ( s , \gamma , 0 ) | \le C _ { \Phi } ( 1 + \| \gamma \| _ { s } ^ { p + 2 } )$ for all $( s , \gamma ) \in [ 0 , \infty ) \times \Lambda$ Because the terms $H ( \varphi ( s , \gamma ) , 0 ) , \partial _ { s } \varphi ( s , \gamma ) , \mathrm { t r } ( \sigma \sigma ^ { \top } \partial _ { x x } ) \varphi ( s , \gamma ) , r ( s , \gamma ) \partial _ { x } \varphi ( s , \gamma ) \gamma ( s )$ have polynomial growth of orders $p , p , p + 2 , p + 1$ at most, respectively, the map $\Phi ( s , \gamma , 0 )$ has polynomial growth of order $p + 2$ at most. □

<!-- page: 28 -->

## D Proofs of the main results in Section 4.2

## D.1 Finite-horizon delayed BSDEs

In this section, we study finite-horizon delayed BSDEs. The following proposition will be used to prove (ii) in Theorem 4.3.

Theorem D.1. Let Assumptions 3.1,3.3 and 4.2 hold. Then for any $T > 0$ and $\xi \in L ^ { 2 } ( \mathcal { F } _ { T } ; \mathbb { R } )$ ， there exists a unique solution $( Y , Z )$ in $\mathbb { S } ^ { 2 } ( 0 , T ; \mathbb { R } ) \times \mathbb { H } ^ { 2 } ( 0 , T ; \mathbb { R } ^ { m } )$ to the BSDE

$$
\begin{array} { l } { { \displaystyle Y ( s ) = \xi + \int _ { s } ^ { T } g ( u , X _ { u } ) - r Y ( u ) - \frac { \ell - r } { \delta } \int _ { u - \delta } ^ { u } Y ( v ) d v d u } } \\ { { \displaystyle ~ - \int _ { s } ^ { T } Z ( u ) d B ( u ) , ~ 0 \le s \le T . } } \end{array}\tag{D.1}
$$

In particular, $i f \xi \equiv 0$ then there is a constant $L > 0$ depending only on $C _ { 1 } , C _ { 3 } , C _ { \Phi } , r , \ell$ such that $| Y ( s ) | \leq L ( 1 + \| X \| _ { s } ^ { \rho } )$ for all $s \in [ 0 , T ]$ where $\rho$ is the constant in Assumption $4 . 2 .$

Proof. We prove the existence and uniqueness of solutions to (D.1) through the Banach fixedpoint theorem. Define a map $\Gamma : \mathbb { S } ^ { 2 } ( 0 , T ; \mathbb { R } ) \to \mathbb { S } ^ { 2 } ( 0 , T ; \mathbb { R } )$ by $\Gamma ( U ) = Y$ that satisfies

$$
Y ( s ) = \mathbb { E } \Big [ \xi + \int _ { s } ^ { T } g ( u , X _ { u } ) - \ell Y ( u ) - \frac { \ell - r } { \delta } \int _ { u - \delta } ^ { u } U ( v ) - U ( u ) d v d u \Big | \mathcal { F } _ { s } \Big ] , 0 \le s \le T .
$$

To verify that this map Γ is well-defined, it sufices to check that the BSDE

$$
\begin{array} { c } { { Y ( s ) = \xi + \displaystyle \int _ { s } ^ { T } g ( u , X _ { u } ) - \ell Y ( u ) - \frac { \ell - r } { \delta } \displaystyle \int _ { u - \delta } ^ { u } U ( v ) - U ( u ) d v d u } } \\ { { - \displaystyle \int _ { s } ^ { T } Z ( u ) d B ( u ) , 0 \le s \le T } } \end{array}
$$

has a unique solution $( Y , Z )$ in $\mathbb { S } ^ { 2 } ( 0 , T ; \mathbb { R } ) \times \mathbb { H } ^ { 2 } ( 0 , T ; \mathbb { R } ^ { m } )$ . This is directly obtained from (Zhang, 2017, Theorem 4.2.1, Theorem 4.3.1) because the process

$$
\bigl ( g ( s , X _ { s } ) - { \frac { \ell - r } { \delta } } \int _ { s - \delta } ^ { s } U ( v ) - U ( u ) d v \bigr ) _ { 0 \leq s \leq T }
$$

is in $\mathbb { H } ^ { 2 } ( 0 , T ; \mathbb { R } )$ for $U \in \mathbb { S } ^ { 2 } ( 0 , T ; \mathbb { R } )$ , which is easily observed by

$$
\int _ { 0 } ^ { T } \int _ { u - \delta } ^ { u } | U ( v ) | ^ { 2 } d v d u \leq T \delta \| U \| _ { T } .
$$

Now we verify that Γ is a contraction map with respect to the norm

$$
\| Y \| : = \left( \mathbb { E } { \Big [ } | Y ( 0 ) | ^ { 2 } + \int _ { 0 } ^ { T } e ^ { M u } | Y ( u ) | ^ { 2 } d u { \Big ] } \right) ^ { \frac { 1 } { 2 } }
$$

where $M : = 2 - 2 \ell + 6 ( \ell - r ) ^ { 2 }$ . Let $U , U ^ { \prime } \in \mathbb { S } ^ { 2 } ( 0 , T ; \mathbb { R } )$ and $Y = \Gamma ( U ) , Y ^ { \prime } = \Gamma ( U ^ { \prime } )$ . For simplicity, we define

$$
{ \hat { U } } ( u ) = U ( u ) - U ^ { \prime } ( u ) , { \hat { Y } } ( u ) = Y ( u ) - Y ^ { \prime } ( u ) , { \hat { Z } } ( u ) = Z ( u ) - Z ^ { \prime } ( u ) .
$$

Applying Itˆo’s formula to $e ^ { M s } | \hat { Y } ( s ) | ^ { 2 }$ , we have

$$
\begin{array} { l } { { \displaystyle | \hat { \cal Y } ( 0 ) | ^ { 2 } + \int _ { 0 } ^ { T } ( M + 2 \ell ) e ^ { M u } | \hat { \cal Y } ( u ) | ^ { 2 } d u + \int _ { 0 } ^ { T } e ^ { M u } | \hat { \cal Z } ( u ) | ^ { 2 } d u } } \\ { { \displaystyle = - \int _ { 0 } ^ { T } \frac { 2 ( \ell - r ) } { \delta } e ^ { M u } \hat { \cal Y } ( u ) \int _ { u - \delta } ^ { u } \hat { \cal U } ( v ) - \hat { \cal U } ( u ) d v d u - \int _ { 0 } ^ { T } 2 e ^ { M u } \hat { \cal Y } ( u ) \hat { \cal Z } ( u ) d B ( u ) . } } \end{array}
$$

<!-- page: 29 -->

From the inequality $3 a b \leq 3 a ^ { 2 } + { \textstyle { \frac { 1 } { 3 } } } b ^ { 2 }$ for all $a , b > 0$ and the Jensen inequality, it follows that

$$
\begin{array} { l } { { \displaystyle | \hat { Y } ( 0 ) | ^ { 2 } + \int _ { 0 } ^ { T } 2 e ^ { M u } | \hat { Y } ( u ) | ^ { 2 } d u + \int _ { 0 } ^ { T } e ^ { M u } | \hat { Z } ( u ) | ^ { 2 } d u + \int _ { 0 } ^ { T } 2 e ^ { M u } \hat { Y } ( u ) \hat { Z } ( u ) d B ( u ) } } \\ { { \displaystyle \le \int _ { 0 } ^ { T } \frac { 1 } { 3 } e ^ { M u } | \hat { U } ( u ) | ^ { 2 } + \frac { e ^ { M u } } { 3 \delta } \int _ { u - \delta } ^ { u } | \hat { U } ( v ) | ^ { 2 } d v d u . } } \end{array}
$$

Observe that

$$
\begin{array} { r l } { \displaystyle \int _ { 0 } ^ { T } \frac { \epsilon ^ { M a } } { \delta } \int _ { u - \delta } ^ { u } | \hat { U } ( v ) | ^ { 2 } d v d u = \int _ { 0 } ^ { T } \frac { \epsilon ^ { M a } } { \delta } \int _ { - \delta } ^ { 0 } | \hat { U } ( v + u ) | ^ { 2 } d v d u } & { } \\ { \displaystyle } & { = \int _ { - \delta } ^ { 0 } \int _ { 0 } ^ { T } \frac { \epsilon ^ { M a } } { \delta } | \hat { U } ( v + u ) | ^ { 2 } d u d v } \\ & { = \displaystyle \int _ { - \delta } ^ { 0 } \int _ { v } ^ { T + 1 } \frac { e ^ { M ( u - v ) } } { \delta } | \hat { U } ( u ) | ^ { 2 } d u d v } \\ & { \leq \displaystyle \int _ { - \delta } ^ { 0 } e ^ { - M v } d v ( \int _ { - \delta } ^ { 0 } \frac { \epsilon ^ { M u } } { \delta } | \hat { U } ( 0 ) | ^ { 2 } d u + \int _ { 0 } ^ { T } \frac { e ^ { M u } } { \delta } | \hat { U } ( u ) | ^ { 2 } d u ) } \\ & { \leq \displaystyle \frac { e ^ { | M | \delta } - 1 } { | M | \delta } ( | \hat { U } ( 0 ) | ^ { 2 } + \int _ { 0 } ^ { T } \epsilon ^ { \hat { M } u } | \hat { U } ( u ) | ^ { 2 } d u ) . } \end{array}
$$

Then we obtain

$$
\begin{array} { r l } & { \mathbb { E } \Big [ | \hat { Y } ( 0 ) | ^ { 2 } + \int _ { 0 } ^ { T } 2 e ^ { M u } | \hat { Y } ( u ) | ^ { 2 } d u + \int _ { 0 } ^ { T } e ^ { M u } | \hat { Z } ( u ) | ^ { 2 } d u \Big ] } \\ & { \le \frac { 1 } { 3 } \mathbb { E } \Big [ \int _ { 0 } ^ { T } e ^ { M u } | \hat { U } ( u ) | ^ { 2 } d u \Big ] + \frac { e ^ { M \delta } - 1 } { 3 M \delta } \mathbb { E } \Big [ | \hat { U } ( 0 ) | ^ { 2 } + \int _ { 0 } ^ { T } e ^ { M u } | \hat { U } ( u ) | ^ { 2 } d u \Big ] } \\ & { \le \frac { e ^ { | M | \delta } - 1 } { 3 | M | \delta } \mathbb { E } \Big [ | \hat { U } ( 0 ) | ^ { 2 } + 2 \int _ { 0 } ^ { T } e ^ { M u } | \hat { U } ( u ) | ^ { 2 } d u \Big ] . } \end{array}
$$

Thus, the map Γ is a contraction map.

We now construct a solution $( Y , Z )$ to (D.1) in $\mathbb { S } ^ { 2 } ( 0 , T ; \mathbb { R } ) \times \mathbb { H } ^ { 2 } ( 0 , T ; \mathbb { R } ^ { m } )$ . Because Γ is a contraction map, by the Banach fixed point theorem, there exists a unique fixed point $Y$ in the completion of $\mathbb { S } ^ { 2 } ( 0 , T ; \mathbb { R } )$ with respect to the norm $\| \cdot \|$ . Then

$$
Y ( s ) = \mathbb { E } \Big [ \xi + \int _ { s } ^ { T } g ( u , X _ { u } ) - r Y ( u ) - \frac { \ell - r } { \delta } \int _ { u - \delta } ^ { u } Y ( v ) d v d u \Big | \mathcal { F } _ { s } \Big ] , 0 \le s \le T .
$$

It can be shown that the process inside the conditional expectation belongs to $\mathbb { H } ^ { 2 } ( 0 , T ; \mathbb { R } ^ { m } )$ using that

$$
\int _ { 0 } ^ { T } { \frac { 1 } { \delta } } \int _ { u - \delta } ^ { u } | Y ( v ) | ^ { 2 } d v d u \leq \int _ { 0 } ^ { T } { \frac { 1 } { \delta } } \int _ { - \delta } ^ { T } | Y ( v ) | ^ { 2 } d v d u \leq L ( 1 + T ) { \Big ( } | Y ( 0 ) | ^ { 2 } + \int _ { 0 } ^ { T } | Y ( u ) | ^ { 2 } d u { \Big ) }
$$

for some positive constant L. The martingale representation theorem yields that there exists a unique $Z \in \mathbb { H } ^ { 2 } ( 0 , T ; \mathbb { R } ^ { m } )$ such that

$$
Y ( s ) = \xi + \int _ { s } ^ { T } g ( u , X _ { u } ) - r Y ( u ) - \frac { \ell - r } { \delta } \int _ { u - \delta } ^ { u } Y ( v ) d v d u - \int _ { s } ^ { T } Z ( u ) d B ( u ) , 0 \le s \le T .
$$

Thus, (Y, Z) satisfies (D.1). By a simple calculation, we have

<!-- page: 30 -->

$$
\begin{array} { r l r } {  { \mathbb { E } [ \| Y \| _ { T } ^ { 2 } ] \le L \mathbb { E } \Big [ | \xi | ^ { 2 } + \int _ { 0 } ^ { T } | g ( u , X _ { u } ) | ^ { 2 } + | Y ( u ) | ^ { 2 } + \frac { 1 } { \delta } \int _ { u - \delta } ^ { u } | Y ( v ) | ^ { 2 } d v d u + \int _ { 0 } ^ { T } | Z ( u ) | ^ { 2 } d u \Big ] } } \\ & { } & { \le L ( 1 + T ) \mathbb { E } \Big [ | \xi | ^ { 2 } + | Y ( 0 ) | ^ { 2 } + \int _ { 0 } ^ { T } | g ( u , X _ { u } ) | ^ { 2 } + 2 | Y ( u ) | ^ { 2 } + | Z ( u ) | ^ { 2 } d u \Big ] ~ } \end{array}
$$

for some positive constant L. Therefore the solution : some $( Y , Z )$ belongs to belongs to $\mathbb { S } ^ { 2 } ( 0 , T ; \mathbb { R } ) \times \mathbb { H } ^ { 2 } ( 0 , T ; \mathbb { R } ^ { m } )$

We now prove that if $\xi \equiv 0$ then there is a constant $L > 0$ depending only on $C _ { 1 } , C _ { 3 } , C _ { \Phi } , r , \ell , \rho$ such that $| Y ( s ) | \leq L ( 1 + \| X \| _ { s } ^ { \rho } )$ for all $s \geq 0$ . We construct a sequence of processes $( Y ^ { k } , Z ^ { k } ) _ { k \in \mathbb { N } }$ inductively. Define $( Y ^ { 0 } , Z ^ { 0 } ) = ( 0 , 0 )$ and for $k \in \mathbb N$ let $( Y ^ { k } , Z ^ { k } )$ be a solution to

$$
\begin{array} { l } { { \displaystyle Y ^ { k } ( s ) = \int _ { s } ^ { T } g ( u , X _ { u } ) - \ell Y ^ { k } ( u ) - \frac { \ell - r } { \delta } \int _ { u - \delta } ^ { u } Y ^ { k - 1 } ( v ) - Y ^ { k - 1 } ( u ) d v d u } } \\ { { \displaystyle ~ - \int _ { s } ^ { T } Z ^ { k } ( u ) d B ( u ) . } } \end{array}\tag{D.2}
$$

Because $Y ^ { k } = \Gamma ( Y ^ { k - 1 } )$ and Y is a fixed point of Γ, we know Y is the limit of $Y ^ { k }$ . Thus it sufices to show that there exists a constant $L > 0$ , which is independent to $k ,$ , such that $| Y ^ { k } ( s ) | \leq L ( 1 + \| X \| _ { s } ^ { \rho } )$ for all $s \in [ 0 , T ]$

To prove this, we need the inequality (D.3) as a lemma. From (A.3), it follows that for any $\epsilon > 0$ and $K > 0$ there is a constant $L > 0$ satisfying

$$
\begin{array} { r } { ( \mathbb { E } [ \| X \| _ { T } ^ { \rho } \mathbf { 1 } _ { A } ] ) ^ { \frac { 1 } { \rho } } \leq \big ( e ( \mathbb { E } [ \| X \| _ { s } ^ { \rho } \mathbf { 1 } _ { A } ] ) ^ { \frac { 1 } { \rho } } + L \big ( \mathbb { E } [ \mathbf { 1 } _ { A } ] \big ) ^ { \frac { 1 } { \rho } } \big ) e ^ { ( \epsilon + K + \frac { 1 } { 2 } ( \frac { r } { \sqrt { 2 K } } + M _ { \rho \vee 2 } C _ { 3 } ) ^ { 2 } ) ( T - s ) } . } \end{array}
$$

Expanding the term $( e ( \mathbb { E } [ \| X \| _ { s } ^ { \rho } \mathbf { 1 } _ { A } ] ) ^ { \frac { 1 } { \rho } } + L ( \mathbb { E } [ \mathbf { 1 } _ { A } ] ) ^ { \frac { 1 } { \rho } } ) ^ { \rho }$ with Young’s inequality

$$
c a ^ { i } b ^ { \rho - i } = ( u a ^ { i } ) ( \frac { c b ^ { \rho - i } } u ) \leq \frac { i u ^ { \frac \rho { i } } } \rho a ^ { \rho } + \frac { ( \rho - i ) c ^ { \frac \rho { \rho - i } } } { \rho u ^ { \frac \rho { \rho - i } } } b ^ { \rho }
$$

for $a , b , c , u > 0$ and $i = 1 , \cdots , \rho - 1$ , we obtain that for any $\kappa > 0$ there is $C _ { \kappa } > 0$ such that

$$
\begin{array} { r } { \mathbb { E } [ \| X \| _ { T } ^ { \rho } \mathbf { 1 } _ { A } ] \le \big ( ( 1 + \kappa ) e ^ { \rho } ( \mathbb { E } [ \| X \| _ { s } ^ { \rho } \mathbf { 1 } _ { A } ] + C _ { \kappa } \mathbb { E } [ \mathbf { 1 } _ { A } ] ) e ^ { ( \epsilon + K + \frac { 1 } { 2 } ( \frac { r } { \sqrt { 2 \kappa } } + M _ { \rho \vee 2 } C _ { 3 } ) ^ { 2 } ) \rho ( T - s ) } . } \end{array}
$$

Since $\textstyle \ell > 1 + \operatorname* { i n f } _ { K > 0 } ( K + \frac { 1 } { 2 } ( \frac { r } { \sqrt { 2 K } } + M _ { \rho \vee 2 } C _ { 3 } ) ^ { 2 } ) \rho$ and $\begin{array} { r } { e ^ { \rho } ( ( \ell - r ) ^ { 2 } + \frac { 1 } { 2 } | \ell - r | \ell + 2 | \ell - r | ) \delta < 1 } \end{array}$ , for some positive constants $L _ { 6 } , L _ { 7 } , L _ { 8 }$ satisfying $L _ { 8 } < \ell - 1$ and $L _ { 6 } ( ( \ell - r ) ^ { 2 } + { \textstyle { \frac { 1 } { 2 } } } | \ell - r | \ell + 2 | \ell - r | ) \delta < 1$ 2 we have

$$
\mathbb { E } _ { s } [ \| X \| _ { T } ^ { \rho } ] \le \bigl ( L _ { 6 } \| X \| _ { s } ^ { \rho } + L _ { 7 } \bigr ) e ^ { L _ { 8 } ( T - s ) } .\tag{D.3}
$$

We construct four sequences $( a _ { k } ) _ { k \geq 0 } , ( b _ { k } ) _ { k \geq 0 } , ( \tilde { a } _ { k } ) _ { k \geq 0 } , ( \tilde { b } _ { k } ) _ { k \geq 0 }$ that satisfy

$$
\begin{array} { r l } & { | Y ^ { k } ( s ) | \leq a _ { k } \| X \| _ { s } ^ { \rho } + b _ { k } , } \\ & { | \mathbb { E } _ { s } [ Y ^ { k } ( s _ { 1 } ) - Y ^ { k } ( s _ { 2 } ) ] \leq ( s _ { 2 } - s _ { 1 } ) ( \tilde { a } _ { k } \mathbb { E } _ { s } [ \| X \| _ { s _ { 2 } } ^ { \rho } ] + \tilde { b } _ { k } ) | } \end{array}\tag{D.4}
$$

for all $0 \leq s \leq s _ { 1 } \leq s _ { 2 }$ . Define $a _ { 0 } = b _ { 0 } = \tilde { a } _ { 0 } = \tilde { b } _ { 0 } = 0$ then (D.4) is satisfied with $Y ^ { 0 } = 0$ From $\left( \mathrm { { A . 5 } } \right)$ , there are positive constants $a _ { 1 }$ and $b _ { 1 } .$ , depending only on $C _ { 1 } , C _ { 3 } , C _ { \Phi } , r , \ell , \rho ,$ such that $| Y ^ { 1 } ( s ) | \leq a _ { 1 } \| X \| _ { s } ^ { \rho } + b _ { 1 }$ . Given $a _ { 0 } , b _ { 0 } , \tilde { a } _ { 0 } , \tilde { b } _ { 0 } , a _ { 1 } , b _ { 1 }$ , we define inductively

$$
a _ { k + 1 } = a _ { 1 } + 2 | \ell - r | L _ { 6 } \delta a _ { k } + \frac 1 2 | \ell - r | L _ { 6 } \delta \tilde { a } _ { k } ,\tag{D.5}
$$

$$
b _ { k + 1 } = b _ { 1 } + 2 | \ell - r | L _ { 7 } \delta a _ { k } + 2 | \ell - r | \delta b _ { k } + \frac { 1 } { 2 } | \ell - r | L _ { 7 } \delta \tilde { a } _ { k } + \frac { 1 } { 2 } | \ell - r | \delta \tilde { b } _ { k } ,
$$

<!-- page: 31 -->

and

$$
\begin{array} { r l } & { \tilde { a } _ { k + 1 } = C _ { \Phi } + \ell a _ { k + 1 } + 2 | \ell - r | a _ { k } , } \\ & { \tilde { b } _ { k + 1 } = C _ { \Phi } + \ell b _ { k + 1 } + 2 | \ell - r | b _ { k } . } \end{array}\tag{D.6}
$$

Applying Itˆo’s formula, we have

$$
Y ^ { k + 1 } ( s ) = \mathbb { E } _ { s } \Big [ \int _ { s } ^ { T } e ^ { - \ell ( u - s ) } g ( u , X _ { u } ) - \frac { ( \ell - r ) e ^ { - \ell ( u - s ) } } { \delta } \int _ { u - \delta } ^ { u } Y ^ { k } ( v ) - Y ^ { k } ( u ) d v d u \Big ] .
$$

Using (D.3), each term inside the conditional expectation of the above equation can be estimated as

$$
\begin{array} { r l } & { \mathbb { E } _ { 1 } \bigg [ \int _ { c } ^ { \infty } \mathrm { e } ^ { - \mathrm { i } \omega c } x _ { j ( 0 ) } X _ { \omega _ { 1 } } \bigg ] } \\ & { \le \mathbb { E } _ { 1 } \bigg [ \int _ { c } ^ { \infty } \mathrm { e } ^ { - \mathrm { i } \omega c } x _ { j ( 0 ) } ( 1 - | X _ { \omega _ { 1 } } | ) \le \alpha _ { 1 } | X | ^ { \zeta } + \delta _ { 1 , \zeta } } \\ & { \mathrm { E } _ { 1 } \bigg [ \int _ { c } ^ { \infty } \mathrm { e } ^ { - \mathrm { i } \omega c } x _ { j ( 0 ) } ^ { \zeta - \kappa - \kappa } \bigg ] \int _ { c } ^ { \infty } { x _ { 0 } ^ { \zeta } ( 0 ) } - { x _ { 0 } ^ { \zeta } ( \omega ) } d \omega d \bigg ] } \\ & { \le \mathbb { E } _ { 1 } \bigg [ \int _ { c } ^ { \infty } \eta _ { 1 } ^ { \zeta } ( 1 - \nu ) ^ { \zeta - \kappa } d s ( | X | ) \prod _ { i = 1 } ^ { \nu } ( | X | ^ { \zeta } + \delta _ { 1 , \zeta } ) d s \bigg ] } \\ & { \le 2 \| \delta _ { 1 } - \eta _ { 1 } ^ { \zeta } ( 1 - \nu ) ^ { \zeta - \kappa } d s ( | X | ) \prod _ { i = 1 } ^ { \nu } ( | X | ^ { \zeta } + \delta _ { 1 , \zeta } ) \| \int _ { c } ^ { 1 } \eta _ { 1 } ^ { \zeta } ( 1 - \nu ) ^ { \zeta - \kappa } d s ( + 2 \bar { \ell } - \nu ) \frac { 1 - \sigma ^ { \zeta } } { \delta } w _ { 1 , i } } \\ &  \le 2 \| \delta _ { 1 } - \eta _ { 1 } ^ { \zeta } ( \frac { 1 - \sigma ^ { \zeta } } { \delta } - \frac { \delta _ { 1 , \zeta } } { \delta } - \frac { \delta _ { 1 , \zeta } } { \delta } ) \| X | ^ { \zeta } + 2 \| \delta _ { 1 } - \eta _ { 1 } ^ { \zeta - \kappa } \| \end{array}
$$

Observe that $\ell - L _ { 8 } > 1$ and $\frac { 1 - e ^ { a \delta } } { a } \leq \delta$ for any $a > 0$ . Thus, we have

$$
\begin{array} { r } { | Y ^ { k + 1 } ( s ) | \leq a _ { k + 1 } \| X \| _ { s } ^ { \rho } + b _ { k + 1 } . } \end{array}
$$

By (D.2),

$$
\begin{array} { r l } & { \quad \left| \mathbb { E } _ { s } [ Y ^ { k + 1 } ( s _ { 1 } ) - Y ^ { k + 1 } ( s _ { 2 } ) ] \right| } \\ & { = \left| \mathbb { E } _ { s } \left[ \displaystyle \int _ { s _ { 1 } } ^ { s _ { 2 } } g ( u , X _ { u } ) - \ell Y ^ { k + 1 } ( u ) - \frac { \ell - r } { \delta } \displaystyle \int _ { u - \delta } ^ { u } Y ^ { k } ( v ) - Y ^ { k } ( u ) d v d u \right] \right| } \\ & { \le ( s _ { 2 } - s _ { 1 } ) ( ( C _ { \Phi } + \ell a _ { k + 1 } + 2 | \ell - r | a _ { k } ) \mathbb { E } _ { s } [ \| X \| _ { s _ { 2 } } ^ { \rho } ] + C _ { \Phi } + \ell b _ { k + 1 } + 2 | \ell - r | b _ { k } ) . } \end{array}
$$

Thus, we obtain

$$
\begin{array} { r } { | \mathbb { E } _ { s } [ Y ^ { k + 1 } ( s _ { 1 } ) - Y ^ { k + 1 } ( s _ { 2 } ) ] \leq ( s _ { 2 } - s _ { 1 } ) ( \widetilde { a } _ { k + 1 } \mathbb { E } _ { s } [ \| X \| _ { s _ { 2 } } ^ { \rho } ] + \widetilde { b } _ { k + 1 } ) . } \end{array}
$$

By substituting (D.6) into (D.5), we have

$$
\begin{array} { l } { { a _ { k + 1 } = a _ { 1 } + \displaystyle \frac { 1 } { 2 } | \ell - r | L _ { 6 } C _ { \Phi } \delta + L _ { 6 } ( \frac { 1 } { 2 } | \ell - r | \ell + 2 | \ell - r | ) \delta a _ { k } + L _ { 6 } ( \ell - r ) ^ { 2 } \delta a _ { k - 1 } \ : , } } \\ { { \mathrm { } } } \\ { { b _ { k + 1 } = b _ { 1 } + \displaystyle \frac { 1 } { 2 } | \ell - r | C _ { \Phi } \delta + 2 | \ell - r | L _ { 7 } \delta a _ { k } + \displaystyle \frac { 1 } { 2 } | \ell - r | L _ { 7 } \delta \tilde { a } _ { k } + 2 | \ell - r | \delta b _ { k } + \displaystyle \frac { 1 } { 2 } | \ell - r | \ell \delta b _ { k } + \displaystyle \frac { 1 } { 2 } | \ell - r | \ell \delta b _ { k } - \displaystyle \frac { 1 } { 2 } | \ell | ^ { 2 } } } \\ { { \mathrm { } } } \\ { { \displaystyle \quad \qquad + | \ell - r | ^ { 2 } \delta b _ { k - 1 } \ : . } } \end{array}\tag{D.7}
$$

<!-- page: 32 -->

Now we prove the convergence of the sequence $( a _ { k } ) _ { k \geq 0 }$ by verifying that it is increasing and bounded above. From the initial condition $0 = a _ { 0 } < a _ { 1 }$ and the recursive relation, it follows that $a _ { 0 } < a _ { 1 } < a _ { 2 }$ and

$$
a _ { k + 2 } - a _ { k + 1 } = L _ { 6 } { \left( \frac { 1 } { 2 } | \ell - r | \ell + 2 | \ell - r | \right) } \delta ( a _ { k + 1 } - a _ { k } ) + L _ { 6 } { \left( \ell - r \right) } ^ { 2 } \delta ( a _ { k } - a _ { k - 1 } ) , \mathrm { f o r } k \geq 1 .
$$

This equation implies that $a _ { k + 2 } - a _ { k + 1 } > 0$ whenever $a _ { k - 1 } < a _ { k } < a _ { k + 1 }$ . Therefore by mathematical induction, the sequence $( a _ { k } ) _ { k \geq 0 }$ is increasing. To show that this sequence is bounded above, recall the condition $L _ { 6 } ( ( \ell - r ) ^ { 2 } + { \textstyle \frac { 1 } { 2 } } | \ell - r | \ell + 2 | \ell - r | ) \delta < 1$ . Define

$$
a : = \frac { a _ { 1 } + \frac { 1 } { 2 } | \ell - r | L _ { 6 } C _ { \Phi } \delta } { 1 - L _ { 6 } ( ( \ell - r ) ^ { 2 } + \frac { 1 } { 2 } | \ell - r | \ell + 2 | \ell - r | ) \delta }
$$

then $a > 0$ and $a _ { 0 } , a _ { 1 } \leq a _ { }$ . By (D.7), if $a _ { k - 1 } , a _ { k } \leq a$ then

$$
\begin{array} { r l } & { a _ { k + 1 } = a _ { 1 } + \displaystyle \frac { 1 } { 2 } | \ell - r | L _ { 6 } C _ { \Phi } \delta + L _ { 6 } ( \frac { 1 } { 2 } | \ell - r | \ell + 2 | \ell - r | ) \delta a _ { k } + L _ { 6 } ( \ell - r ) ^ { 2 } \delta a _ { k - 1 } } \\ & { \qquad \le a _ { 1 } + \displaystyle \frac { 1 } { 2 } | \ell - r | L _ { 6 } C _ { \Phi } \delta + L _ { 6 } ( \frac { 1 } { 2 } | \ell - r | \ell + 2 | \ell - r | + ( \ell - r ) ^ { 2 } ) \delta a } \\ & { \qquad \le a . } \end{array}
$$

By induction, $a _ { k } \leq a$ for all $k \geq 0$ , thus the sequence $( a _ { k } ) _ { k \geq 0 }$ is bounded above by a. Since $( a _ { k } ) _ { k \geq 0 }$ is increasing and bounded above, it converges to a positive constant. Moreover, by the recursive relation in (D.7), it can be shown that lim $\iota _ { k \to \infty } a _ { k } = a$ . Similarly, the sequences $( b _ { k } ) _ { k \geq 0 }$ and $( \tilde { a } _ { k } ) _ { k \geq 0 }$ also converge to positive constants. We have

$$
\operatorname* { l i m } _ { k  \infty } \tilde { a } _ { k } = C _ { \Phi } + ( \ell + 2 | \ell - r | ) \frac { a _ { 1 } + \frac { 1 } { 2 } | \ell - r | L _ { 6 } C _ { \Phi } \delta } { 1 - L _ { 6 } ( ( \ell - r ) ^ { 2 } + \frac { 1 } { 2 } | \ell - r | \ell + 2 | \ell - r | ) \delta }
$$

and

$$
\operatorname* { l i m } _ { k \to \infty } b _ { k } = \frac { b _ { 1 } + \frac { 1 } { 2 } | \ell - r | C _ { \Phi } \delta + 2 | \ell - r | L _ { 7 } \delta a + \frac { 1 } { 2 } | \ell - r | L _ { 7 } \delta ( C _ { \phi } + ( \ell + 2 | \ell - r | ) a } { 1 - ( ( \ell - r ) ^ { 2 } + \frac { 1 } { 2 } | \ell - r | \ell + 2 | \ell - r | ) \delta } .
$$

Taking $k \infty$ to the first inequality in (D.4), we obtain the desired results.

The above proof verifies the convergence of the Picard iteration $( Y ^ { k } ) _ { k \in \mathbb { N } }$ to the unique solution $Y$ of the BSDE (D.1) through the Banach fixed point theorem. It can also be shown that the sequence $( Z ^ { k } ) _ { k \in \mathbb { N } }$ converges to the unique solution $Z$ of the BSDE. However, we omit the convergence of the sequence $( Z ^ { k } ) _ { k \in \mathbb { N } }$ in the following corollary, as it is not required for our purposes.

Corollary D.2. Let $( Y ^ { k } , Z ^ { k } ) _ { k \in \mathbb { N } }$ be the Picard iteration for the BSDE (D.1). More precisely, define $( Y ^ { 0 } , Z ^ { 0 } ) = ( 0 , 0 )$ and for $k \in \mathbb N$ let $( Y ^ { k } , Z ^ { k } )$ be a solution to

$$
Y ^ { k } ( s ) = \int _ { s } ^ { T } g ( u , X _ { u } ) - \ell Y ^ { k } ( u ) - { \frac { \ell - r } { \delta } } \int _ { u - \delta } ^ { u } Y ^ { k - 1 } ( v ) - Y ^ { k - 1 } ( u ) d v d u - \int _ { s } ^ { T } Z ^ { k } ( u ) d B ( u ) .
$$

Then $( Y ^ { k } ) _ { k \in \mathbb { N } }$ converges to the unique solution Y of the BSDE (D.1) $\mathbb { Q } \otimes$ ds-almost surely.

<!-- page: 33 -->

## D.2 Proof of Theorem 4.3

We now prove (i) and (ii) in Theorem 4.3. Part (i) is directly obtained by Theorem 4.1. The proof of (ii) is as follows.

Proof. In this proof, L denotes a generic constant that depends only on $C _ { 1 } , C _ { 3 } , C _ { \Phi } , r , \ell , \rho$ and may difer line by line and $L _ { 6 } , L _ { 7 } , L _ { 8 }$ are positive constants satisfying

$$
\begin{array} { r l } & { L _ { 8 } < \ell - 1 , } \\ & { L _ { 6 } ( ( \ell - r ) ^ { 2 } + \displaystyle \frac { 1 } { 2 } | \ell - r | \ell + 2 | \ell - r | ) \delta < 1 , } \\ & { \mathbb { E } _ { s } [ \| X \| _ { T } ^ { \rho } ] \leq ( L _ { 6 } \| X \| _ { s } ^ { \rho } + L _ { 7 } ) e ^ { L _ { 8 } ( T - s ) } . } \end{array}\tag{D.8}
$$

We first prove the uniqueness of solutions. Let $( Y ^ { 1 } , Z ^ { 1 } )$ and $( Y ^ { 2 } , Z ^ { 2 } )$ be two solutions to (4.5) such that $| Y ^ { i } ( s ) | \leq L ( 1 + \| X \| _ { s } ^ { \rho } )$ for $i = 1 , 2$ . Define $\hat { Y } = Y ^ { 1 } - Y ^ { 2 }$ and $\hat { Z } = Z ^ { 1 } ( s ) - Z ^ { 2 } ( s )$ . Then we have

$$
\hat { Y } ( s ) = \hat { Y } ( T ) + \int _ { s } ^ { T } - r \hat { Y } ( u ) - \frac { \ell - r } { \delta } \int _ { u - \delta } ^ { u } \hat { Y } ( v ) d v d u - \int _ { s } ^ { T } \hat { Z } ( u ) d B ( u ) , 0 \le s \le T < \infty .
$$

Let $( \hat { Y } ^ { k } , \hat { Z } ^ { k } )$ denote the Picard iteration of this BSDE. More precisely, define $( \hat { Y } ^ { 0 } , \hat { Z } ^ { 0 } ) = ( 0 , 0 )$ and for each $k \in \mathbb N$ , let $( \hat { Y } ^ { k } , \hat { Z } ^ { k } )$ be a solution to

$$
\hat { Y } ^ { k } ( s ) = \hat { Y } ( T ) + \int _ { s } ^ { T } - \ell \hat { Y } ^ { k } ( u ) - \frac { \ell - r } { \delta } \int _ { u - \delta } ^ { u } \hat { Y } ^ { k - 1 } ( v ) - \hat { Y } ^ { k - 1 } ( u ) d v d u - \int _ { s } ^ { T } \hat { Z } ^ { k } ( u ) d B ( u ) .
$$

We construct four sequences $( a _ { k } ) _ { k \geq 0 } , ( b _ { k } ) _ { k \geq 0 } , ( \tilde { a } _ { k } ) _ { k \geq 0 } , ( \tilde { b } _ { k } ) _ { k \geq 0 }$ that satisfy

$$
\begin{array} { l } { { \displaystyle | \hat { Y } ^ { k } ( s ) | \le e ^ { - ( \ell - L _ { 8 } ) ( T - s ) } ( \sum _ { j = 0 } ^ { k - 1 } \frac { ( T - s ) ^ { j } } { j ! } ) ( a _ { k } \| X \| _ { s } ^ { \rho } + b _ { k } ) , \hfill } } \\ { { \displaystyle | \mathbb { E } _ { s } [ \hat { Y } ^ { k } ( s _ { 1 } ) - \hat { Y } ^ { k } ( s _ { 2 } ) ] | \le ( s _ { 2 } - s _ { 1 } ) e ^ { - ( \ell - L _ { 8 } ) ( T - s _ { 2 } ) } \Big ( \sum _ { j = 0 } ^ { k - 1 } \frac { ( T - s _ { 2 } ) ^ { j } } { j ! } \Big ) ( \tilde { a } _ { k } \mathbb { E } _ { s } [ \| X \| _ { s _ { 2 } } ^ { \rho } ] + \tilde { b } _ { k } ) } } \end{array}\tag{D.9}
$$

for all $0 \leq s \leq s _ { 1 } \leq s _ { 2 }$ . Define $a _ { 0 } = b _ { 0 } = \tilde { a } _ { 0 } = \tilde { b } _ { 0 } = 0$ then (D.9) is satisfied with $\hat { Y } ^ { 0 } = 0$ . It can be easily checked that there are constants $a _ { 1 }$ and $b _ { 1 }$ , depending on $C _ { 1 } , C _ { 3 } , C _ { \Phi } , r , \ell , \rho .$ such that

$$
| \hat { Y } ^ { 1 } ( s ) | = | \mathbb { E } _ { s } [ e ^ { - \ell ( T - s ) } \hat { Y } ( T ) ] | \le e ^ { - ( \ell - L _ { 8 } ) ( T - s ) } ( a _ { 1 } \| X \| _ { s } ^ { \rho } + b _ { 1 } ) .
$$

Given $a _ { 0 } , b _ { 0 } , \tilde { a } _ { 0 } , \tilde { b } _ { 0 } , a _ { 1 } , b _ { 1 }$ , we define inductively

$$
\begin{array} { l } { \displaystyle a _ { k + 1 } = a _ { 1 } + 2 | \ell - r | L _ { 6 } \delta a _ { k } + \frac { 1 } { 2 } | \ell - r | L _ { 6 } \delta \tilde { a } _ { k } , } \\ { \displaystyle b _ { k + 1 } = b _ { 1 } + 2 | \ell - r | L _ { 7 } \delta a _ { k } + 2 | \ell - r | \delta b _ { k } + \frac { 1 } { 2 } | \ell - r | L _ { 7 } \delta \tilde { a } _ { k } + \frac { 1 } { 2 } | \ell - r | \delta \tilde { b } _ { k } , } \end{array}
$$

and

$$
\begin{array} { r l } & { \tilde { a } _ { k + 1 } = \ell a _ { k + 1 } + 2 | \ell - r | a _ { k } , } \\ & { } \\ & { \tilde { b } _ { k + 1 } = \ell b _ { k + 1 } + 2 | \ell - r | b _ { k } . } \end{array}
$$

According to Itˆo’s formula,

$$
\hat { Y } ^ { k + 1 } ( s ) = \mathbb { E } _ { s } \left[ e ^ { - \ell ( T - s ) } \hat { Y } ( T ) - \int _ { s } ^ { T } \frac { ( \ell - r ) e ^ { - \ell ( u - s ) } } { \delta } \int _ { u - \delta } ^ { u } \hat { Y } ^ { k } ( v ) - \hat { Y } ^ { k } ( u ) d v d u \right] .
$$

<!-- page: 34 -->

Decompose the right hand side of the above equation into

$$
\begin{array} { r l } & { \mathbb { E } _ { s } [ e ^ { - \ell ( T - s ) } \hat { Y } ( T ) ] + \mathbb { E } _ { s } \Big [ \displaystyle \int _ { s } ^ { s + \delta } - \frac { ( \ell - r ) e ^ { - \ell ( u - s ) } } { \delta } \int _ { u - \delta } ^ { u } \hat { Y } ^ { k } ( v ) - \hat { Y } ^ { k } ( u ) d v d u \Big ] } \\ & { + \mathbb { E } _ { s } \Big [ \displaystyle \int _ { s + \delta } ^ { T } - \frac { ( \ell - r ) e ^ { - \ell ( u - s ) } } { \delta } \int _ { u - \delta } ^ { u } \hat { Y } ^ { k } ( v ) - \hat { Y } ^ { k } ( u ) d v d u \Big ] . } \end{array}
$$

Observe that

$$
\begin{array} { r l } & { \mathrm { S e } ^ { - \mathrm { i } \omega \cdot \mathbf { x } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { z } \cdot \mathbf { \sigma } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { k } \cdot \mathbf { F } \cdot \mathbf { y } \cdot \mathbf { z } \cdot \mathbf { z } \cdot \mathbf { y } } } \\ & { \mathrm { S e } [ \int _ { 0 } ^ { + \infty } { \mathbf { f } \cdot \mathbf { y } \cdot \mathbf { u } \cdot \mathbf { e } ^ { - \mathrm { i } \omega \cdot \mathbf { m } \cdot \mathbf { j } } } \int _ { 0 } ^ { \infty } { \mathbf { f } \cdot \mathbf { y } \cdot \mathbf { u } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { u } \cdot \mathbf { f } \cdot \mathbf { y } \cdot \mathbf { \sigma } \mathrm { i } \cdot \mathbf { y } \cdot \mathbf { k } \cdot \mathbf { \sigma } \mathrm { k } \cdot \mathbf { \sigma } \mathrm { k } \cdot \mathbf { \sigma } \mathrm { k } ] } } \\ &  \leq \mathrm { S e } [ \int _ { 0 } ^ { + \infty }  \mathbf { f } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { z } \cdot \mathbf { y } \cdot \frac { \mathbf { x } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { z } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { y } \cdot \mathbf { z } \cdot \mathbf { y } \mathrm { \sigma } \cdot \mathrm { i } \cdot \mathbf { b } \cdot \mathbf { \sigma } \mathrm { k } \cdot \mathbf { y } \mathrm { \sigma } \mathrm { k } \cdot \mathbf { y } \mathrm { \sigma } \cdot \mathrm { \sigma } } \\ &  \leq \mathrm { F e } ^  - \mathrm  \end{array}
$$

where we have used that $\begin{array} { r } { e ^ { ( \ell - L _ { 8 } ) ( T - s ) } \sum _ { j = 0 } ^ { k } \frac { ( T - s ) ^ { j } } { j ! } } \end{array}$ is an increasing function in s. Thus we have

$$
| \hat { Y } ^ { k + 1 } ( s ) | \leq e ^ { - ( \ell - L _ { 8 } ) ( T - s ) } \Bigl ( \sum _ { j = 0 } ^ { k } \frac { ( T - s ) ^ { j } } { j ! } \Bigr ) ( a _ { k + 1 } \| X \| _ { s } ^ { \rho } + b _ { k + 1 } ) .
$$

For $s \leq s _ { 1 } \leq s _ { 2 } \leq T$

$$
\begin{array} { r l } & { \quad \bigl | \mathbb { E } _ { s } [ \hat { Y } ^ { k + 1 } ( s _ { 1 } ) - \hat { Y } ^ { k + 1 } ( s _ { 2 } ) ] \bigr | } \\ & { = \Bigl | \mathbb { E } \Bigl [ \displaystyle \int _ { s _ { 1 } } ^ { s _ { 2 } } - \ell \hat { Y } ^ { k + 1 } ( u ) - \frac { \ell - r } { \delta } \int _ { u - \delta } ^ { u } \hat { Y } ^ { k } ( v ) - \hat { Y } ^ { k } ( u ) d v d u \Bigr ] \Bigr | } \\ & { \le ( s _ { 2 } - s _ { 1 } ) e ^ { - ( \ell - L _ { 8 } ) ( T - s _ { 2 } ) } \Bigl ( \displaystyle \sum _ { j = 0 } ^ { k } \frac { ( T - s _ { 2 } ) ^ { j } } { j ! } \Bigr ) ( ( \ell a _ { k + 1 } + 2 | \ell - r | a _ { k } ) \mathbb { E } _ { s } [ \| X \| _ { s _ { 2 } } ^ { \rho } ] + \ell b _ { k + 1 } + 2 | \ell - r | b _ { k } ) } \end{array}
$$

$$
= \bigl ( s _ { 2 } - s _ { 1 } \bigr ) e ^ { - ( \ell - L _ { 8 } ) ( T - s _ { 2 } ) } \Bigl ( \sum _ { j = 0 } ^ { k } \frac { ( T - s _ { 2 } ) ^ { j } } { j ! } \Bigr ) ( \tilde { a } _ { k + 1 } \mathbb { E } _ { s } [ \| X \| _ { s _ { 2 } } ^ { \rho } ] + \tilde { b } _ { k + 1 } ) .
$$

We now verify $Y ^ { 1 } = Y ^ { 2 }$ by taking $k \infty$ to (D.9). Following the arguments in (D.7) and

<!-- page: 35 -->

using the inequalities in (D.8), the limits

$$
\begin{array} { l } { { a : = \displaystyle \operatorname* { l i m } _ { k \to \infty } a _ { k } = \frac { a _ { 1 } } { 1 - L _ { 6 } ( ( \ell - r ) ^ { 2 } + \frac 1 2 | \ell - r | \ell + 2 | \ell - r | ) \delta } , } } \\ { { b : = \displaystyle \operatorname* { l i m } _ { k \to \infty } b _ { k } = \frac { b _ { 1 } + a L _ { 7 } ( ( \ell - r ) ^ { 2 } + \frac 1 2 | \ell - r | \ell + 2 | \ell - r | ) \delta } { 1 - ( ( \ell - r ) ^ { 2 } + \frac 1 2 | \ell - r | \ell + 2 | \ell - r | ) \delta } } } \end{array}
$$

exist and are positive. By Corollary D.2, the sequence $( \hat { Y } ^ { k } ( s ) ) _ { k \geq 0 }$ converge to $\hat { Y } ( s )$ , thus we obtain

$$
| \hat { Y } ( s ) | \le L e ^ { - ( \ell - L _ { 8 } - 1 ) ( T - s ) } ( \| X \| _ { s } ^ { \rho } + 1 ) , s \ge 0
$$

By letting $T \to \infty .$ , we have $Y ^ { 1 } = Y ^ { 2 }$ . This induces $Z ^ { 1 } = Z ^ { 2 }$

Now we prove the existence of solutions. For each $n \in \mathbb { N } .$ , consider the BSDE

$$
Y ^ { n } ( s ) = \int _ { s } ^ { n } g ( u , X _ { u } ) - r Y ^ { n } ( u ) - { \frac { \ell - r } { \delta } } \int _ { u - \delta } ^ { u } Y ^ { n } ( v ) d v d u - \int _ { s } ^ { n } Z ( u ) d B ( u ) , 0 \leq s \leq n .
$$

For $n \leq m$ , let $\tilde { Y } ( s ) : = Y ^ { m } ( s ) - Y ^ { n } ( s )$ and $\tilde { Z } ( s ) : = Z ^ { m } ( s ) - Z ^ { n } ( s )$ . Then for $s \leq n$

$$
\tilde { Y } ( s ) = Y ^ { m } ( n ) + \int _ { s } ^ { n } - r \tilde { Y } ( u ) - \frac { \ell - r } { \delta } \int _ { u - \delta } ^ { u } \tilde { Y } ( v ) d v d u - \int _ { s } ^ { u } \tilde { Z } ( u ) d B ( u ) .
$$

Observe that $| Y ^ { m } ( n ) | \leq L ( \| X \| _ { n } ^ { \rho } + 1 )$ by Theorem D.1. By a similar argument as above, it follows that

$$
| \tilde { Y } ( s ) | = | Y ^ { m } ( s ) - Y ^ { n } ( s ) | \leq L e ^ { - ( \ell - L _ { 8 } - 1 ) ( n - s ) } ( \| X \| _ { s } ^ { \rho } + 1 ) .
$$

Therefore, for $0 \leq T \leq n \leq m$ , we have

$$
\begin{array} { r } { \mathbb { E } [ \| Y ^ { n } - Y ^ { m } \| _ { T } ^ { 2 } ] \le L e ^ { - 2 ( \ell - L _ { 8 } - 1 ) ( n - T ) } ( \| X \| _ { T } ^ { 2 \rho } + 1 ) . } \end{array}
$$

This indicates that $( Y ^ { n } ) _ { n \in \mathbb { N } }$ is a Cauchy sequence in $\mathbb { S } ^ { 2 } ( 0 , T ; \mathbb { R } )$ for each $T \geq 0$ and we denote as $Y ^ { \delta }$ the limit of $Y ^ { n }$ . Moreover, by Theorem D.1, there exists a constant $L > 0$ such that $| Y ^ { \delta } | \leq L ( 1 + \| X \| ^ { \rho } )$ . The sequence $( Z ^ { n } ) _ { n \in \mathbb { N } }$ is a Cauchy sequence in $\mathbb { H } ^ { 2 } ( 0 , T ; \mathbb { R } ^ { m } )$ for each $T \geq 0$ because

$$
\begin{array} { l } { \displaystyle \mathbb { E } \Big [ \int _ { 0 } ^ { T } | \tilde { Z } ( u ) | ^ { 2 } d u \Big ] \leq L \Big ( \mathbb { E } \Big [ | \tilde { Y } ( T ) | ^ { 2 } + \int _ { 0 } ^ { T } | \tilde { Y } ( u ) | ^ { 2 } + \frac { 1 } { \delta } \int _ { u - \delta } ^ { u } | \tilde { Y } ( v ) | ^ { 2 } d v d u \Big ] \Big ) } \\ { \leq L ( 1 + T ) ( \mathbb { E } [ \| X \| _ { T } ^ { 2 \rho } ] + 1 ) e ^ { - 2 ( \ell - L _ { 8 } - 1 ) ( n - T ) } . } \end{array}
$$

which is obtained from Itˆo’s formula and the inequality $2 a b \leq a ^ { 2 } + b ^ { 2 }$ for $a , b > 0$ . Denote as $Z ^ { \delta }$ the limit of $Z ^ { n }$ . Because $( Y ^ { n } ( s ) , Z ^ { n } ( s ) ) _ { 0 \leq s \leq n }$ satisfies

$$
\begin{array} { r l } & { Y ^ { n } ( s ) = Y ^ { n } ( T ) + \displaystyle \int _ { s } ^ { T } g ( u , X _ { u } ) - r Y ^ { n } ( u ) - \frac { \ell - r } { \delta } \int _ { u - \delta } ^ { u } Y ^ { n } ( v ) d v d u } \\ & { \qquad \quad - \displaystyle \int _ { s } ^ { T } Z ^ { n } ( u ) d B ( u ) , 0 \le s \le T , } \end{array}
$$

the Lebesgue dominated convergence theorem implies that the pair $( Y ^ { \delta } , Z ^ { \delta } )$ is a solution to (4.5). □

We now prove (4.6) in Theorem 4.3.

<!-- page: 36 -->

Proof. We recall that L denotes a generic constant that depends only on $C _ { 1 } , C _ { 3 } , C _ { \Phi } , r , \ell , \rho$ and may difer line by line, and $L _ { 6 } , L _ { 7 } , L _ { 8 }$ are constants satisfying (D.8). By Theorems 3.2 and (ii) in Theorem 4.3, there exists a unique solution $( Y , Z )$ to (3.6) and $( Y ^ { \delta } , Z ^ { \delta } )$ to (4.5) in $\mathbb { S } ^ { 2 } ( 0 , \infty ; \mathbb { R } ) \times \mathbb { H } ^ { 2 } ( 0 , \infty ; \mathbb { R } ^ { m } )$ . For each $n \in \mathbb { N }$ , consider the finite-horizon BSDEs

$$
\begin{array} { c l c r } { { } } & { { } } & { { Y ^ { n } ( s ) = \displaystyle \int _ { s } ^ { n } \Phi ( u , X _ { u } , 0 ) - \ell Y ^ { n } ( u ) d u - \displaystyle \int _ { s } ^ { n } Z ^ { n } ( u ) d B ( u ) , } } \\ { { } } & { { } } & { { Y ^ { n , \delta } ( s ) = \displaystyle \int _ { s } ^ { n } \frac { 1 } { \delta } \int _ { u - \delta } ^ { u } \Phi ( v , X _ { v } , 0 ) d v - r Y ^ { n , \delta } ( u ) - \displaystyle \frac { \ell - r } { \delta } \int _ { u - \delta } ^ { u } Y ^ { n , \delta } ( v ) d v d u } } \\ { { } } & { { } } & { { - \displaystyle \int _ { s } ^ { n } Z ^ { n , \delta } ( u ) d B ( u ) . } } \end{array}\tag{D.10}
$$

Proposition D.1 guarantees the existence and uniqueness of solutions to this BSDE. One can easily prove

$$
\begin{array} { r l } & { \displaystyle \operatorname* { l i m } _ { \delta \to 0 } \mathbb { E } [ \| Y ^ { n } - Y \| _ { T } ^ { 2 } ] \leq L ( 1 + \| X \| _ { T } ^ { 2 \rho } ) e ^ { - 2 ( \ell - L _ { 8 } ) ( n - T ) } , } \\ & { \displaystyle \operatorname* { l i m } _ { \delta \to 0 } \mathbb { E } [ \| Y ^ { n , \delta } - Y ^ { \delta } \| _ { T } ^ { 2 } ] \leq L ( 1 + \| X \| _ { T } ^ { 2 \rho } ) e ^ { - 2 ( \ell - L _ { 8 } - 1 ) ( n - T ) } . } \end{array}
$$

Observe that

$$
\begin{array} { r l } & { \| Y ^ { \delta } - Y \| _ { T } \leq \| Y ^ { \delta } - Y ^ { n , \delta } \| _ { T } + \| Y ^ { n , \delta } - Y ^ { n } \| _ { T } + \| Y ^ { n } - Y \| _ { T } } \\ & { \qquad \leq L ( 1 + \| X \| _ { T } ^ { \rho } ) e ^ { - ( \ell - L _ { 8 } ) ( n - T ) } + \| Y ^ { n , \delta } - Y ^ { n } \| _ { T } + L ( 1 + \| X \| _ { T } ^ { \rho } ) e ^ { - ( \ell - L _ { 8 } - 1 ) ( n - T ) } . } \end{array}\tag{D.11}
$$

Then

$$
\begin{array} { r l } & { \mathbb { E } [ \| Y ^ { \delta } - Y \| _ { T } ] \le \big ( \mathbb { E } [ \| Y ^ { \delta } - Y \| _ { T } ^ { 2 } ] \big ) ^ { \frac { 1 } { 2 } } } \\ & { \qquad \le L ( 1 + \big ( \mathbb { E } [ \| X \| _ { T } ^ { 2 \rho } ] \big ) ^ { \frac { 1 } { 2 } } \big ) e ^ { - ( \ell - L _ { 8 } ) ( n - T ) } + \big ( \mathbb { E } [ \| Y ^ { n , \delta } - Y ^ { n } \| _ { T } ^ { 2 } ] \big ) ^ { \frac { 1 } { 2 } } } \\ & { \qquad + L \big ( 1 + \big ( \mathbb { E } [ \| X \| _ { T } ^ { 2 \rho } ] \big ) ^ { \frac { 1 } { 2 } } \big ) e ^ { - ( \ell - L _ { 8 } - 1 ) ( n - T ) } . } \end{array}\tag{D.12}
$$

We now show that

$$
\operatorname* { l i m } _ { \delta \to 0 } \mathbb { E } [ \| Y ^ { n , \delta } - Y ^ { n } \| _ { T } ^ { 2 } ] = 0 { \mathrm { ~ f o r ~ } } n \in \mathbb { N } .\tag{D.13}
$$

Once this is proven, by taking $\delta 0$ and $n \infty$ to (D.12), we obtain the first inequality in (4.6). Let ${ \hat { Y } } ( s ) = Y ^ { n , \delta } ( s ) - Y ^ { n } ( s )$ and $\hat { Z } ( s ) = Z ^ { n , \delta } ( s ) - Z ^ { n } ( s )$ . Then we have

$$
\begin{array} { l } { \displaystyle \hat { Y } ( s ) = \int _ { s } ^ { n } \frac 1 { \delta } \int _ { u - \delta } ^ { u } \Phi ( v , X _ { v } , 0 ) - \Phi ( u , X _ { u } , 0 ) d v - \frac { \ell - r } { \delta } \int _ { u - \delta } ^ { u } Y ^ { n } ( v ) - Y ^ { n } ( u ) d v - r \hat { Y } ( u ) } \\ { \displaystyle \qquad - \frac { \ell - r } { \delta } \int _ { u - \delta } ^ { u } \hat { Y } ( v ) d v d u - \int _ { s } ^ { n } \hat { Z } ( u ) d B ( u ) , \ 0 \le s \le n . } \end{array}
$$

Let $( \hat { Y } ^ { k } , \hat { Z } ^ { k } )$ denote the Picard iteration of this BSDE. More precisely, define $( \hat { Y } ^ { 0 } , \hat { Z } ^ { 0 } ) = ( 0 , 0 )$ and for each $k \in \mathbb N$ , let $( \hat { Y } ^ { k } , \hat { Z } ^ { k } )$ be a solution to

$$
\begin{array} { l } { { \displaystyle \hat { Y } ^ { k } ( s ) = \int _ { s } ^ { n } \frac { 1 } { \delta } \int _ { u - \delta } ^ { u } \Phi ( v , X _ { v } , 0 ) - \Phi ( u , X _ { u } , 0 ) d v - \frac { \ell - r } { \delta } \int _ { u - \delta } ^ { u } Y ^ { n } ( v ) - Y ^ { n } ( u ) d v } } \\ { { \displaystyle ~ - \ell \hat { Y } ^ { k } ( u ) - \frac { \ell - r } { \delta } \int _ { u - \delta } ^ { u } \hat { Y } ^ { k - 1 } ( v ) - \hat { Y } ^ { k - 1 } ( u ) d v d u - \int _ { s } ^ { n } \hat { Z } ^ { k } ( u ) d B ( u ) , } } \end{array}\tag{D.14}
$$

and we define

$$
\hat { G } ^ { \delta } ( s ) : = \mathbb { E } _ { s } \Big [ \int _ { s } ^ { n } \frac { e ^ { - \ell ( u - s ) } } { \delta } \int _ { u - \delta } ^ { u } \vert \Phi ( v , X _ { v } , 0 ) - \Phi ( u , X _ { u } , 0 ) \vert d v d u \Big ]
$$

<!-- page: 37 -->

for $0 \leq s \leq n$

We construct four sequences $( a _ { k } ) _ { k \geq 0 } , ( b _ { k } ) _ { k \geq 0 } , ( \tilde { a } _ { k } ) _ { k \geq 0 } , ( \tilde { b } _ { k } ) _ { k \geq 0 }$ that satisfy

$$
\begin{array} { r l } & { | \hat { Y } ^ { k } ( s ) | \leq \hat { G } ^ { \delta } ( s ) + a _ { k } \| X \| _ { s } ^ { \rho } + b _ { k } , } \\ & { | \mathbb { E } _ { s } [ \hat { Y } ^ { k } ( s _ { 1 } ) - \hat { Y } ^ { k } ( s _ { 2 } ) ] \leq ( s _ { 2 } - s _ { 1 } ) \big ( \tilde { a } _ { k } \mathbb { E } _ { s } [ \| X \| _ { s _ { 2 } } ^ { \rho } ] + \tilde { b } _ { k } \big ) } \end{array}\tag{D.15}
$$

for all $0 \leq s \leq s _ { 1 } \leq s _ { 2 }$ . Let $a _ { 0 } = b _ { 0 } = \tilde { a } _ { 0 } = \tilde { b } _ { 0 } = 0$ then (D.15) is satisfied with $\hat { Y } ^ { 0 } = 0$ . Observe that

$$
\begin{array} { r l r } & { \vert Y ^ { n } ( s ) \vert \le L ( 1 + \Vert X \Vert _ { s } ^ { \varrho } ) , } & \\ & { \vert \mathbb { E } _ { s } [ Y ^ { n } ( s _ { 1 } ) - Y ^ { n } ( s _ { 2 } ) ] \vert \le \left. \mathbb { E } _ { s } \left[ \int _ { s _ { 1 } } ^ { s _ { 2 } } \Phi ( u , X _ { u } , 0 ) - \ell Y ^ { n } ( u ) d u \right] \right. \le L ( 1 + \mathbb { E } _ { s } [ \Vert X \Vert _ { s _ { 2 } } ^ { \varrho } ] ) ( s _ { 2 } - s _ { 1 } ) } & \end{array}
$$

for $0 \leq s \leq s _ { 1 } \leq s _ { 2 } \leq n$ . Then we obtain

$$
\begin{array} { r l } & { | \hat { Y } ^ { 1 } ( s ) | = | \mathbb { E } _ { s } [ \int _ { s } ^ { n } \frac { e ^ { - \ell ( u - s ) } } { \delta } \int _ { u - \delta } ^ { u } \Phi ( \sigma , X _ { u } , 0 ) - \Phi ( u , X _ { u } , 0 ) d v d u    } \\ & { \qquad  - \int _ { s } ^ { n } c ^ { - \ell ( u - s ) } \frac { \ell - T } { \delta } \int _ { u - \delta } ^ { u } \Gamma _ { ( v ) } ^ { \alpha } - Y ^ { n } ( u ) d v d u ] | } \\ & { \qquad \le \hat { C } ^ { \delta } ( s ) + | \mathbb { E } _ { s } [ \int _ { s } ^ { u + \delta } e ^ { - \ell ( u - s ) } \frac { \ell } { \delta } \int _ { u - \delta } ^ { u } \nabla ^ { n } ( v ) - Y ^ { n } ( u ) d v d u ] | } \\ & { \qquad + \mathbb { E } [ \int _ { s + \delta } ^ { n } e ^ { - \ell ( u - s ) } \frac { | \ell - T | } { \delta } \int _ { u - \delta } ^ { u } | \mathbb { E } _ { s } | Y ^ { n } ( v ) - Y ^ { n } ( u ) | d v d u ] | } \\ & { \qquad \le \hat { C } ^ { \delta } ( s ) + \mathbb { E } _ { s } [ \int _ { s } ^ { u + \delta } I _ { s } e ^ { - \ell ( u - s ) } ( 1 + | X | _ { u } ) d u ] + \mathbb { R } _ { s } [ \int _ { s } ^ { u } L \hat { H } _ { v } - \bar { e } ^ { - \ell ( u - s ) } ( 1 + | X | _ { u } ) d u ] } \\ & { \qquad \le \hat { C } ^ { \delta } ( s ) + L ( 1 + | X | _ { u } ^ { \delta } ) \delta } \\ & { \qquad \le \hat { C } ^ { \delta } ( s ) + a _ { 1 } | X | _ { v } ^ { \beta } + b _ { 1 } } \end{array}
$$

for $a _ { 1 } : = L \delta$ and $b _ { 1 } : = L \delta$ . Given $a _ { 0 } , b _ { 0 } , \tilde { a } _ { 0 } , \tilde { b } _ { 0 } , a _ { 1 } , b _ { 1 }$ , we define inductively

$$
\begin{array} { r l } & { a _ { k + 1 } = L \delta + 2 | \ell - r | L _ { 6 } \delta a _ { k } + \displaystyle \frac { 1 } { 2 } | \ell - r | L _ { 6 } \delta \tilde { a } _ { k } , } \\ & { b _ { k + 1 } = L \delta + 2 | \ell - r | L _ { 7 } \delta a _ { k } + 2 | \ell - r | \delta b _ { k } + \displaystyle \frac { 1 } { 2 } | \ell - r | L _ { 7 } \delta \tilde { a } _ { k } + \displaystyle \frac { 1 } { 2 } | \ell - r | \delta \tilde { b } _ { k } , } \\ & { \tilde { a } _ { k + 1 } = L + \ell a _ { k + 1 } + 2 | \ell - r | a _ { k } , } \\ & { \tilde { b } _ { k + 1 } = L + \ell b _ { k + 1 } + 2 | \ell - r | b _ { k } . } \end{array}
$$

Observe that

$$
\begin{array} { r l } & { | Y ^ { k } ( s ) | \le \hat { G } ^ { \delta } ( s ) + a _ { k } \| X \| _ { s } ^ { \rho } + b _ { k } ( s ) } \\ & { \qquad = \mathbb { E } _ { s } \Big [ \displaystyle \int _ { s } ^ { n } \frac { e ^ { - \ell ( u - s ) } } { \delta } \displaystyle \int _ { u - \delta } ^ { u } \left| \Phi ( v , X _ { v } , 0 ) - \Phi ( u , X _ { u } , 0 ) \right| d v d u \Big ] + a _ { k } \| X \| _ { s } ^ { \rho } + b _ { k } } \\ & { \qquad \le \mathbb { E } _ { s } \Big [ \displaystyle \int _ { s } ^ { n } e ^ { - \ell ( u - s ) } 2 C _ { \Phi } ( 1 + \| X \| _ { u } ^ { \rho } ) d u \Big ] + a _ { k } \| X \| _ { s } ^ { \rho } + b _ { k } } \\ & { \qquad \le ( a _ { k } + L ) \| X \| _ { s } ^ { \rho } + b _ { k } + L . } \end{array}
$$

<!-- page: 38 -->

Applying Iˆo’s formula, we have

$$
\begin{array} { r l } & { \hat { Y } ^ { k + 1 } ( s ) = \mathbb { E } _ { s } \Big [ \displaystyle \int _ { s } ^ { n } \frac { e ^ { - \ell ( u - s ) } } { \delta } \int _ { u - \delta } ^ { u } \Phi ( v , X _ { v } , 0 ) - \Phi ( u , X _ { u } , 0 ) d v } \\ & { \quad \quad \quad - \frac { ( \ell - r ) e ^ { - \ell ( u - s ) } } { \delta } \int _ { u - \delta } ^ { u } Y ^ { n } ( v ) - Y ^ { n } ( u ) d v - \frac { ( \ell - r ) e ^ { - \ell ( u - s ) } } { \delta } \int _ { u - \delta } ^ { u } \hat { Y } ^ { k } ( v ) - \hat { Y } ^ { k } ( u ) d v d u \Big ] } \\ & { \quad \quad \quad \leq \hat { G } ^ { \delta } ( s ) + a _ { 1 } \| X \| _ { s } ^ { \rho } + b _ { 1 } + \mathbb { E } _ { s } \Big [ \displaystyle \int _ { s } ^ { s + \delta } \frac { | \ell - r | e ^ { - \ell ( u - s ) } } { \delta } \int _ { u - \delta } ^ { u } \hat { Y } ^ { k } ( v ) - \hat { Y } ^ { k } ( u ) d v d u \Big ] } \\ & { \quad \quad \quad + \mathbb { E } _ { s } \Big [ \displaystyle \int _ { s + \delta } ^ { n } \frac { | \ell - r | e ^ { - \ell ( u - s ) } } { \delta } \int _ { u } ^ { u } \hat { Y } ^ { k } ( v ) - \hat { Y } ^ { k } ( u ) d v d u \Big ] } \\ & { \quad \quad \quad \leq \hat { G } ^ { \delta } ( s ) + a _ { k + 1 } \| X \| _ { s } ^ { \rho } + b _ { k + 1 } . } \end{array}
$$

For $s \leq s _ { 1 } \leq s _ { 2 } \leq n$

$$
\begin{array} { r l } & { | \mathbb { E } _ { s } [ \hat { Y } ^ { k + 1 } ( s _ { 1 } ) - \hat { Y } ^ { k + 1 } ( s _ { 2 } ) ] | = \Big | \mathbb { E } _ { s } \Big [ \displaystyle \int _ { s _ { 1 } } ^ { s _ { 2 } } \frac { 1 } { \delta } \int _ { u - \delta } ^ { u } \Phi ( v , X _ { v } , 0 ) - \Phi ( u , X _ { u } , 0 ) d v } \\ & { \qquad - \displaystyle \frac { \ell } { \delta } \int _ { u - \delta } ^ { u } Y ^ { n } ( v ) - Y ^ { n } ( u ) d v } \\ & { \qquad - \ell \hat { Y } ^ { k + 1 } ( u ) - \displaystyle \frac { \ell - r } { \delta } \int _ { u - \delta } ^ { u } \hat { Y } ^ { k } ( v ) - \hat { Y } ^ { k } ( u ) d v d u \Big ] \Big | } \\ & { \leq \big ( s _ { 2 } - s _ { 1 } \big ) \big ( \tilde { a } _ { k + 1 } \mathbb { E } _ { s } \big [ \big \| X \big \| _ { s } ^ { \rho } \big ] + \tilde { b } _ { k + 1 } \big ) . } \end{array}
$$

We now prove the equality (D.13). Following the argument in (D.7), the sequence $( a _ { k } ) _ { k \geq 0 }$ converges to a positive constant and the limit

$$
a : = \operatorname* { l i m } _ { k \to \infty } a _ { k } = \frac { L \delta + \frac { 1 } { 2 } | \ell - r | L _ { 6 } C _ { \Phi } \delta } { 1 - L _ { 6 } ( ( \ell - r ) ^ { 2 } + \frac { 1 } { 2 } | \ell - r | \ell + 2 | \ell - r | ) \delta }
$$

is bounded by Lδ for some $L > 0$ . Similarly, the sequence $\left( b _ { k } \right) _ { k \geq 0 }$ also converges to a positive constant, which is bounded by Lδ. We recall that L is a generic constant and may difer line by line. Corollary D.2 yields that ${ \hat { Y } } ^ { k } ( s ) { \hat { Y } } ( s ) = Y ^ { n , \delta } ( s ) - Y ^ { n } ( s )$ as $k \infty$ . Thus, by (D.15) we have

$$
| Y ^ { n , \delta } ( s ) - Y ^ { n } ( s ) | \leq \hat { G } ^ { \delta } ( s ) + L ( 1 + \| X \| _ { s } ^ { \rho } ) \delta .\tag{D.16}
$$

By Doob’s inequality and Jensen’s inequality, we have

$$
\begin{array} { r l } & { \quad ( \mathbb { E } [ \big ( \underset { 0 \leq s \leq T } { \operatorname* { s u p } } \hat { C } ^ { \delta } ( s ) \big ) ^ { 2 } ] ) ^ { 1 + r } } \\ & { = \Big ( \mathbb { E } \Big [ \Big ( \underset { 0 \leq s \leq T } { \operatorname* { s u p } } \mathbb { E } _ { s } \Big [ \int _ { s } ^ { n } \frac { e ^ { - \zeta ( u - s ) } } { \delta } \int _ { u } ^ { u } \big | \Phi ( v , X _ { v } , 0 ) - \Phi ( u , X _ { u } , 0 ) \big | d v d u \Big ] \Big ) ^ { 2 } \Big ] \Big ) ^ { 1 + r } } \\ & { \leq e ^ { 2 \ell ( 1 + r ) T } \mathbb { E } \Big [ \Big ( \underset { 0 \leq s \leq T } { \operatorname* { s u p } } \mathbb { E } _ { s } \Big [ \int _ { 0 } ^ { n } \frac { e ^ { - \ell u } } { \delta } \int _ { u - \delta } ^ { u } \int _ { v } ^ { u } \big | \Phi ( v , X _ { v } , 0 ) - \Phi ( u , X _ { u } , 0 ) \big | d v d u \Big ] \Big ) ^ { 2 + 2 r } \Big ] } \\ & { \leq e ^ { 2 \ell ( 1 + r ) T } ( \frac { 2 + 2 r } { 1 + 2 r } ) ^ { 2 + 2 r } \underset { 0 \leq s \leq T } { \operatorname* { s u p } } \mathbb { E } \Big [ \Big ( \mathbb { E } _ { s } \Big [ \int _ { 0 } ^ { n } \frac { e ^ { - \ell u } } { \delta } \int _ { u - \delta } ^ { u } \int _ { u - \delta } ^ { u } \big | \Phi ( v , X _ { v } , 0 ) - \Phi ( u , X _ { u } , 0 ) \big | d v d u \Big ] \Big ) ^ { 2 + 2 r } \Big ] } \\ &  \leq e ^ { 2 \ell ( 1 + r ) T } ( \frac { 2 + 2 r ) } { 1 + 2 r } ) ^ { 2 + r } \mathbb { E } \Big [ \Big ( \int _ { 0 } ^ { n } \frac { e ^ { - \ell u } } { \delta } \int _ { u , \delta } ^ { u } \big | \Phi ( v , X _ { v } , 0 \end{array}
$$

for some constant $r \ > \ 0$ . Applying the dominated convergence theorem and the Lebesgue diferentiation theorem to the right-hand side of the above inequality,

$$
\operatorname* { l i m } _ { \delta \to 0 } \mathbb { E } [ ( \operatorname* { s u p } _ { 0 \leq s \leq T } \hat { G } ^ { \delta } ( s ) ) ^ { 2 } ] = 0 .\tag{D.17}
$$

<!-- page: 39 -->

Therefore by (D.16) and (D.17), we obtain the first equality in (4.6).

For the second equality in (4.6), applying Itˆo’s formula to $( Y ^ { \delta } - Y ) ^ { 2 }$ , we have

$$
\begin{array} { r l } {  { \int _ { 0 } ^ { T } | Z ^ { \delta } ( u ) - Z ( u ) | ^ { 2 } d u } \quad } & { \mathrm { ( } \quad \int _ { 0 } ^ { T } | Y ^ { \delta } ( u ) - Y ( u ) | ^ { 2 } d u } \\ & { \le L \Big ( | Y ^ { \delta } ( T ) - Y ( T ) | ^ { 2 } + \int _ { 0 } ^ { T } \frac { 2 | Y ^ { \delta } ( u ) - Y ( u ) | } { \delta } \int _ { u - \delta } ^ { u } | \Phi ( u , X _ { u } , 0 ) - \Phi ( v , X _ { v } , 0 ) | d v d u } \\ & { + \int _ { 0 } ^ { T } \frac { 2 | Y ^ { \delta } ( u ) - Y ( u ) | } { \delta } \Big ( \int _ { u - \delta } ^ { u } | Y ( u ) - Y ( v ) | d v + \int _ { u - \delta } ^ { u } | Y ^ { \delta } ( v ) - Y ( v ) | d v d u \Big ) \Big ) . } \end{array}\tag{D.18}
$$

Recall from Theorem 3.2 and (ii) in Theorem 4.3 that $| Y ( s ) | \leq L ( 1 + \| X \| _ { s } ^ { \rho } )$ and $| Y ^ { \delta } ( s ) | \leq$ $L ( 1 + \| X \| _ { s } ^ { \rho } )$ . Taking the expectation of both sides of (D.18), we obtain

$$
\begin{array} { r l } & { \mathbb { E } \Big [ \displaystyle \int _ { 0 } ^ { T } | Z ^ { \delta } ( u ) - Z ( u ) | ^ { 2 } d u \Big ] } \\ & { \le L \Big ( \mathbb { E } [ | Y ^ { \delta } ( T ) - Y ( T ) | ^ { 2 } ] + \mathbb { E } \Big [ \displaystyle \int _ { 0 } ^ { T } \frac { 2 | Y ^ { \delta } ( u ) - Y ( u ) | } { \delta } \int _ { u - \delta } ^ { u } | \Phi ( u , X _ { u } , 0 ) - \Phi ( v , X _ { v } , 0 ) | d v d u \Big ] } \\ & { \quad + \mathbb { E } \Big [ \displaystyle \int _ { 0 } ^ { T } \frac { 2 | Y ^ { \delta } ( u ) - Y ( u ) | } { \delta } \Big ( \displaystyle \int _ { u - \delta } ^ { u } | Y ( u ) - Y ( v ) | d v + \displaystyle \int _ { u - \delta } ^ { u } | Y ^ { \delta } ( v ) - Y ( v ) | d v d u \Big ) \Big ) \Big ] \Big ) } \\ & { \le L ( 1 + T ) ( \mathbb { E } [ \| Y ^ { \delta } - Y \| _ { T } ^ { 2 } ] ) ^ { \frac { 1 } { 2 } } ( \mathbb { E } [ 1 + \| X \| _ { T } ^ { 2 \rho } ] ) ^ { \frac { 1 } { 2 } } . } \end{array}\tag{19}
$$

From (D.12) and (D.13), we have

$$
\operatorname* { l i m } _ { \delta \to 0 } \mathbb { E } [ \| Y ^ { \delta } - Y \| _ { T } ^ { 2 } ] = 0 .
$$

Therefore by letting $\delta \to 0$ to (D.19), we obtain the second equality in (4.6) .

Finally we prove (4.7) in Theorem 4.3.

Proof. Recall that L denotes a generic constant that depends only on $C _ { 1 } , C _ { 3 } , C _ { \Phi } , r , \ell , \rho$ and may difer line by line, and $L _ { 6 } , L _ { 7 } , L _ { 8 }$ are constants satisfying (D.8). We first consider the case with $\rho > 1$ . To prove the first inequality in (4.7), we recall that $Y ^ { n }$ and $Y ^ { n , \delta }$ are solutions to the finitehorizon BSDEs (D.10). Consider the Picard iteration $( \hat { Y } ^ { k } , \hat { Z } ^ { k } )$ in (D.14) for $( { \hat { Y } } ( s ) , { \hat { Z } } ( s ) ) : =$ $( Y ^ { n , \delta } ( s ) - Y ^ { n } ( s ) , Z ^ { n , \delta } ( s ) - Z ^ { n } ( s ) )$ . Corollary D.2 yields that ${ \hat { Y } } ^ { k } ( s ) { \hat { Y } } ( s ) = Y ^ { n , \delta } ( s ) - Y ^ { n } ( s )$ as $k \infty$

We construct four sequences $( a _ { k } ) _ { k \geq 0 } , ( b _ { k } ) _ { k \geq 0 } , ( \tilde { a } _ { k } ) _ { k \geq 0 } , ( \tilde { b } _ { k } ) _ { k \geq 0 }$ that satisfy

$$
\begin{array} { r l } & { | \hat { Y } ^ { k } ( s ) | \leq a _ { k } \| X \| _ { s } ^ { \rho } + b _ { k } , } \\ & { | \mathbb { E } _ { s } [ \hat { Y } ^ { k } ( s _ { 1 } ) - \hat { Y } ^ { k } ( s _ { 2 } ) ] \leq ( s _ { 2 } - s _ { 1 } ) ( \tilde { a } _ { k } \mathbb { E } _ { s } [ \| X \| _ { s _ { 2 } } ^ { \rho } ] + \tilde { b } _ { k } ) } \end{array}\tag{D.20}
$$

for all $0 \leq s \leq s _ { 1 } \leq s _ { 2 }$ . Let $a _ { 0 } = b _ { 0 } = \tilde { a } _ { 0 } = \tilde { b } _ { 0 } = 0$ then (D.20) is satisfied with ${ \hat { Y } } ^ { 0 } = 0$ . Now

<!-- page: 40 -->

we define $a _ { 1 }$ and $b _ { 1 }$ . A direct calculation and (D.8) yield

$$
\begin{array} { r l } { \displaystyle ( \mathbb { E } _ { s } \big [ \big ] X - X _ { s _ { 1 } } \big | _ { s _ { 2 } } ^ { p } \big ] ^ { \frac { 1 } { p } } = \big ( \mathbb { E } _ { s } \big [ \operatorname* { s u p } _ { s \in \mathcal { S } ^ { s } \mid X } \big ( r ) - X \big ( s _ { 2 } \big ) \big | ^ { p } \big ] \big ) ^ { \frac { 1 } { p } } } & { } \\ { \leq C _ { 1 } M _ { \rho } \big ( s _ { 2 } - s _ { 1 } \big ) ^ { \frac { 1 } { 2 } } + \big ( r \big ( s _ { 2 } - s _ { 1 } \big ) + C _ { 3 } M _ { \rho } \big ( s _ { 2 } - s _ { 1 } \big ) ^ { \frac { 1 } { 2 } } \big ) ( \mathbb { E } _ { s } \big [ \big | X \big | _ { s _ { 2 } } ^ { p } \big ] \big ) ^ { \frac { 1 } { p } } , } & { } \\ { \displaystyle \big | Y ^ { n } \big ( s \big ) \big | \leq \mathbb { E } _ { s } \bigg [ \int _ { s } ^ { n } e ^ { - \ell ( n - s ) } \big | \Phi \big ( u , X _ { u } , 0 \big ) \big | d u \bigg ] } & { } \\ { \leq \mathbb { R } \bigg [ \int _ { s } ^ { n } e ^ { - \ell ( n - s ) } C _ { \Phi } \big ( \big | X \big | _ { u } ^ { p } + 1 \big ) d u \bigg ] } & { } \\ { \leq \int _ { s } ^ { n } e ^ { - ( \ell - L s ) ( u - s ) } C _ { \Phi } \big ( T _ { \Phi } \big | X \big | _ { s } + L _ { 7 } \big ) + \int _ { s } ^ { n } e ^ { - \ell ( u - s ) } C _ { \Phi } d u } & { } \\  \leq \frac { C _ { 9 } L _ { \Phi } } { \ell - L _ { \Phi } } \big | \mathbb { X } \big | _ { s } ^ { p } + \frac { C _ { 9 } L _ { \mathcal { T } } } { \ell - L _ { \Phi } } + \frac { C _ { \Phi } } { \ell }  \end{array}\tag{D.21}
$$

and

$$
\begin{array} { r l r } {  { \vert \mathbb { E } _ { s } [ Y ^ { n } ( s _ { 1 } ) - Y ^ { n } ( s _ { 2 } ) ] \vert \le \mathbb { E } _ { s } \bigg [ \int _ { s _ { 1 } } ^ { s _ { 2 } } \vert \Phi ( u , X _ { u } , 0 ) \vert + \ell \vert Y ^ { n } ( u ) \vert d u \bigg ] } } \\ & { } & { \le ( s _ { 2 } - s _ { 1 } ) \bigg ( \bigg ( C _ { \Phi } + \frac { \ell C _ { \Phi } L _ { 6 } } { \ell - L _ { 8 } } \bigg ) \| X \| _ { s } ^ { \rho } + 2 C _ { \Phi } + \frac { \ell C _ { \Phi } L _ { 7 } } { \ell - L _ { 8 } } \bigg ) . } \end{array}
$$

Then, using the above inequalities and Itˆo’s formula, we obtain

$$
\begin{array} { r l } & { \dot { Y } ^ { 1 } ( s ) | \le \mathbb { E } _ { s } \Big [ \displaystyle \int _ { s } ^ { s + \delta } \frac { c ^ { - \ell ( u - s ) } } { \delta } \int _ { u - \delta } ^ { u } \big | \Phi ( v , X _ { v } , 0 ) - \Phi ( u , X _ { u } , 0 ) \big | d v d u \Big ] } \\ & { \qquad + \mathbb { E } _ { s } \Big [ \displaystyle \int _ { s + \delta } ^ { n } \frac { e ^ { - \ell ( u - s ) } } { \delta } \int _ { u - \delta } ^ { u } \big | \Phi ( v , X _ { v } , 0 ) - \Phi ( u , X _ { u } , 0 ) \big | d v d u \Big ] } \\ & { \qquad + \Big | \mathbb { E } _ { s } \Big [ \displaystyle \int _ { s } ^ { s + \delta } \frac { ( \ell - r ) e ^ { - \ell ( u - s ) } } { \delta } \int _ { u - \delta } ^ { u } Y ^ { n } ( v ) - Y ^ { n } ( u ) d v \Big ] \Big | } \\ & { \qquad + \Big | \mathbb { E } _ { s } \Big [ \displaystyle \int _ { s + \delta } ^ { n } \frac { ( \ell - r ) e ^ { - \ell ( u - s ) } } { \delta } \int _ { u - \delta } ^ { u } Y ^ { n } ( v ) - Y ^ { n } ( u ) d v \Big ] \Big | } \\ & { \qquad \le a ( \rho ) \sqrt { \delta } \big | X _ { \vert } \big | _ { s } + b ( \rho ) \sqrt { \delta } } \end{array}
$$

where

$$
\begin{array} { r l } & { a ( \rho ) = 2 C _ { \Phi } L _ { \ 6 } \sqrt { \delta } + \frac { L _ { 6 } C _ { 5 } } { \ell - L _ { 8 } } \Big ( \frac { 3 r \sqrt { \delta } } { 2 } + 2 M _ { \rho } C _ { 3 } + \frac { 4 ( 1 + M _ { \rho } C _ { 1 } ) } { 3 } \Big ) } \\ & { \qquad + \frac { \vert \ell - r \vert C _ { \Phi } L _ { 6 } \sqrt { \delta } } { \ell - L _ { 8 } } \Big ( 2 L _ { 6 } + \frac { \ell - L _ { 8 } + \ell L _ { 6 } } { 2 ( \ell - L _ { 8 } ) } \Big ) , } \\ & { b ( \rho ) = C _ { \Phi } \sqrt { \delta } \Big ( 2 \Big ( L _ { 7 } + 1 + \frac { \vert \ell - r \vert L _ { 7 } ( 1 + L _ { 6 } ) } { \ell - L _ { 8 } } + \frac { \vert \ell - r \vert } { \ell } \Big ) + \vert \ell - r \vert \Big ( \frac { L _ { 7 } } { \ell - L _ { 8 } } + \frac { \ell L _ { 6 } L _ { 7 } } { 2 ( \ell - L _ { 8 } ) ^ { 2 } } + \frac { 1 } { \ell } \Big ) \Big ) } \\ & { \qquad + C _ { 5 } \Big ( 2 ( 1 + M _ { \rho } C _ { 1 } ) + \frac { r \sqrt { \delta } } { 2 } + \frac { 2 M _ { \rho } C _ { 3 } ( \ell - L _ { 8 } + L _ { 7 } ) } { 3 ( \ell - L _ { 8 } ) } + \frac { L _ { 7 } ( 9 r \sqrt { \delta } + 8 ( 1 + M \rho C _ { 1 } ) ) } { 6 ( \ell - L _ { 8 } ) } \Big ) . } \end{array}
$$

Thus, $a _ { 1 } = a ( \rho ) \sqrt { \delta }$ and $b _ { 1 } = b ( \rho ) \sqrt { \delta }$ yields the desired ones. Given $a _ { 0 } , b _ { 0 } , \tilde { a } _ { 0 } , \tilde { b } _ { 0 } , a _ { 1 } , b _ { 1 }$ , we define

<!-- page: 41 -->

inductively

$$
a _ { k + 1 } = a ( \rho ) \sqrt { \delta } + 2 \vert \ell - r \vert L _ { 6 } \delta a _ { k } + \frac { 1 } { 2 } \vert \ell - r \vert L _ { 6 } \delta \tilde { a } _ { k } ,
$$

$$
b _ { k + 1 } = b ( \rho ) \sqrt { \delta } + 2 | \ell - r | L _ { 7 } \delta a _ { k } + 2 | \ell - r | \delta b _ { k } + \frac { 1 } { 2 } | \ell - r | L _ { 7 } \delta \tilde { a } _ { k } + \frac { 1 } { 2 } | \ell - r | \delta \tilde { b } _ { k } ,
$$

$$
\tilde { a } _ { k + 1 } = 2 C _ { \Phi } + \frac { 2 | \ell - r | C _ { \Phi } L _ { 6 } } { \ell - L _ { 8 } } + \ell a _ { k + 1 } + 2 | \ell - r | a _ { k } ,
$$

$$
\tilde { b } _ { k + 1 } = 2 C _ { \Phi } + \frac { 2 | \ell - r | C _ { \Phi } L _ { 7 } } { \ell - L _ { 8 } } + \frac { 2 | \ell - r | C _ { \Phi } } { \ell } + \ell b _ { k + 1 } + 2 | \ell - r | b _ { k } .
$$

This construction yields the desired four sequences $( a _ { k } ) _ { k \geq 0 } , ( b _ { k } ) _ { k \geq 0 } , ( \tilde { a } _ { k } ) _ { k \geq 0 }$ and $( \tilde { b } _ { k } ) _ { k \geq 0 }$

Following the argument in (D.7), the sequences $( a _ { k } ) _ { k \geq 0 }$ and $( b _ { k } ) _ { k \geq 0 }$ converge to positive constants. A direct calculation yields

$$
a _ { k + 1 } = a ( \rho ) \sqrt { \delta } + | \ell - r | L _ { 6 } \delta C _ { \Phi } ( 1 + \frac { | \ell - r | L _ { 6 } } { \ell - L _ { 8 } } ) + L _ { 6 } ( \frac 1 2 | \ell - r | \ell + 2 | \ell - r | ) \delta a _ { k } + L _ { 6 } ( \ell - r ) ^ { 2 } \delta a _ { k - 1 }
$$

and this recursive relation implies that lim $\iota _ { k \to \infty } a _ { k } = L _ { 2 } \sqrt { \delta }$ where

$$
L _ { 2 } : = \frac { a ( \rho ) + | \ell - r | L _ { 6 } C _ { \Phi } ( 1 + \frac { | \ell - r | L _ { 6 } } { \ell - L _ { 8 } } ) \sqrt { \delta } } { 1 - L _ { 6 } \delta ( ( \ell - r ) ^ { 2 } + \frac { | \ell - r | \ell } { 2 } + 2 | \ell - r | ) } .
$$

Similarly, the sequence $( b _ { k } ) _ { k \geq 0 }$ converges to $L _ { 1 } \sqrt { \delta }$ where $L _ { 1 }$ is a constant defined as

$$
L _ { 1 } = \frac { b ( \rho ) + a ( \rho ) | \ell - r | L \tau \delta ( 2 + \frac { \ell } { 2 } + | \ell - r | ) + | \ell - r | C _ { \Phi } ( L _ { 7 } + 1 + \frac { L _ { 6 } L _ { 7 } | \ell - r | } { \ell - L _ { 8 } } + \frac { L _ { 7 } | \ell - r | } { \ell - L _ { 8 } } + \frac { | \ell - r | } { \ell } ) \sqrt { \delta } } { 1 - \delta \big ( ( \ell - r ) ^ { 2 } + \frac { | \ell - r | \ell } { 2 } + 2 | \ell - r | \big ) } .
$$

Since $\begin{array} { r } { L _ { 6 } ( ( \ell - r ) ^ { 2 } + \frac { 1 } { 2 } | \ell - r | \ell + 2 | \ell - r | ) \delta < 1 } \end{array}$ , the constants $L _ { 1 }$ and $L _ { 2 }$ are positive. Letting $k \infty$ in (D.20), we obtain

$$
| Y ^ { n , \delta } ( s ) - Y ^ { n } ( s ) | = | \hat { Y } ( s ) | \leq ( L _ { 1 } + L _ { 2 } \| X \| _ { s } ^ { \rho } ) \sqrt { \delta } .
$$

Similar to (D.11), letting $n \to \infty$ , we deduce $| Y ^ { \delta } ( s ) - Y ( s ) | \leq ( L _ { 1 } + L _ { 2 } \| X \| _ { s } ^ { \rho } ) \sqrt { \delta }$ . This yields

$$
\| Y ^ { \delta } - Y \| _ { T } \leq ( L _ { 1 } + L _ { 2 } \| X \| _ { T } ^ { \rho } ) \sqrt { \delta } ,\tag{D.22}
$$

which corresponds to the first inequality in (4.7). From (D.18) and (D.21), we obtain

$$
\mathbb { E } \Big [ \int _ { 0 } ^ { T } | Z ^ { \delta } ( u ) - Z ( u ) | ^ { 2 } d u \Big ] \leq ( L _ { 3 } ( T ) \mathbb { E } [ \| X \| _ { T } ^ { 2 \rho } ] + L _ { 4 } ( T ) \mathbb { E } [ \| X \| _ { T } ^ { \rho } ] + L _ { 5 } ( T ) ) \sqrt { \delta }\tag{D.23}
$$

where

$$
\begin{array} { l } { { { \cal L } _ { 3 } ( T ) = \sqrt { \delta } L _ { 2 } ^ { 2 } + 2 L _ { 2 } \Big ( 2 C _ { \Phi } + | \ell - r | \Big ( \frac { 2 C _ { \Phi } L _ { 6 } } { \ell - L _ { 8 } } + \sqrt { \delta } L _ { 2 } \Big ) \Big ) T , } } \\ { { { \cal L } _ { 4 } ( T ) = 2 \sqrt { \delta } L _ { 1 } L _ { 2 } ( 1 + 2 | \ell - r | T ) } } \\ { { \phantom { \frac { 1 } { 2 } } + 2 \Big ( 2 C _ { \Phi } ( L _ { 2 } + L _ { 1 } ) + \frac { 2 | \ell - r | C _ { \Phi } ( L _ { 2 } L _ { 7 } + L _ { 1 } L _ { 6 } ) } { \ell - L _ { 8 } } + \frac { L _ { 2 } C _ { \Phi } } { \ell } \Big ) T , } } \\ { { \phantom { \frac { 1 } { 2 } } L _ { 5 } ( T ) = \sqrt { \delta } L _ { 1 } ^ { 2 } ( 1 + 2 | \ell - r | T ) + 4 L _ { 1 } C _ { \Phi } \Big ( 1 + | \ell - r | \Big ( \frac { L _ { 7 } } { \ell - L _ { 8 } } + \frac { 1 } { \ell } \Big ) \Big ) T . } } \end{array}
$$

This yields more refined upper bounds than the second inequality in (4.7).

<!-- page: 42 -->

The case with $\rho = 1$ can be proven similarly with $a ( \rho )$ and $b ( \rho )$ replaced by $a ( 1 )$ and $b ( 1 )$ respectively, where

$$
\begin{array} { r l } & { a ( 1 ) = 2 C _ { \Phi } L _ { 6 } \sqrt { \delta } + \displaystyle \frac { L _ { 6 } C _ { 5 } } { \ell - L _ { 8 } } \Big ( \displaystyle \frac { r \sqrt { \delta } } { 2 } + \displaystyle \frac { 2 M _ { 1 } C _ { 3 } } { 3 } \Big ) + \displaystyle \frac { | \ell - r | C _ { \Phi } L _ { 6 } \sqrt { \delta } } { \ell - L _ { 8 } } \Big ( 2 L _ { 6 } + \displaystyle \frac { \ell - L _ { 8 } + \ell L _ { 6 } } { 2 ( \ell - L _ { 8 } ) } \Big ) , } \\ & { b ( 1 ) = C _ { \Phi } \sqrt { \delta } \Big ( 2 \Big ( L _ { 7 } + 1 + \displaystyle \frac { | \ell - r | L _ { 7 } ( 1 + L _ { 6 } ) } { \ell - L _ { 8 } } + \displaystyle \frac { | \ell - r | } { \ell } \Big ) + | \ell - r | \Big ( \displaystyle \frac { L _ { 7 } } { \ell - L _ { 8 } } + \displaystyle \frac { \ell L _ { 6 } L _ { 7 } } { 2 ( \ell - L _ { 8 } ) ^ { 2 } } + \displaystyle \frac { 1 } { \ell } \Big ) \Big ) } \\ & { \qquad + C _ { 5 } \Big ( \displaystyle \frac { r L _ { 7 } \sqrt { \delta } } { 2 ( \ell - L _ { 8 } ) } + \displaystyle \frac { 2 L _ { 7 } M _ { 1 } C _ { 3 } } { 3 ( \ell - L _ { 8 } ) } + \displaystyle \frac { 2 ( 1 + M _ { 1 } C _ { 1 } ) } { 3 \ell } \Big ) . } \end{array}
$$

The same inequalities (D.22) and (D.23) hold with the constants $L _ { 1 } , L _ { 2 } , L _ { 3 } ( T ) , L _ { 4 } ( T ) , L _ { 5 } ( T )$ ， where $a ( \rho )$ and $b ( \rho )$ are replaced by a(1) and $b ( 1 )$ , respectively.

## References

Ackerer, D., Hugonnier, J., and Jermann, U. (2024). Perpetual futures pricing. Technical report, National Bureau of Economic Research. Alexander, C., Choi, J., Park, H., and Sohn, S. (2020). BitMEX bitcoin derivatives: Price discovery, informational eficiency, and hedging efectiveness. Journal of Futures Markets, 40(1):23–43. Angeris, G. and Chitra, T. (2020). Improved price oracles: Constant function market makers. In Proceedings of the 2nd ACM Conference on Advances in Financial Technologies, pages 80–91. Angeris, G., Chitra, T., Evans, A., and Lorig, M. (2023). A primer on perpetuals. SIAM Journal on Financial Mathematics, 14(1):SC17–SC30. Bally, V., Caramellino, L., Cont, R., Utzet, F., and Vives, J. (2016). Stochastic integration by parts and functional Itˆo calculus. Springer. Butler, G. and Rogers, T. (1971). A generalization of a lemma of Bihari and applications to pointwise estimates for integral equations. J. Math. Anal. Appl, 33(1):77–81. Christin, N., Routledge, B., Soska, K., and Zetlin-Jones, A. (2022). The crypto carry trade. Preprint at http://gerbil. life/papers/CarryTrade. v1, 2. Confortola, F., Cosso, A., and Fuhrman, M. (2019). Backward SDEs and infinite horizon stochastic optimal control. ESAIM: Control, Optimisation and Calculus of Variations, 25:31. Cont, R. and Fourni´e, D.-A. (2013). Functional Itˆo calculus and stochastic integral representation of martingales. The Annals of Probability, pages 109–133. Corbet, S., Hou, Y. G., Hu, Y., and Oxley, L. (2021). Volatility spillovers during market supply shocks: The case of negative oil prices. Resources Policy, 74:102357. Cordoni, F., Di Persio, L., Maticiuc, L., and Z˘alinescu, A. (2020). A stochastic approach to path-dependent nonlinear Kolmogorov equations via BSDEs with time-delayed generators and applications to finance. Stochastic Processes and their Applications, 130(3):1669–1712. Dai, M., Li, L., and Yang, C. (2025). Arbitrage in perpetual contracts. Available at SSRN 5262988.

<!-- page: 43 -->

Delbaen, F. and Schachermayer, W. (1994). A general version of the fundamental theorem of asset pricing. Mathematische annalen, 300(1):463–520. Deuschel, J.-D. and Stroock, D. W. (1989). Large Deviations, volume 137. Academic Press. Dupire, B. (2019). Functional Itˆo calculus. Quantitative Finance, 19(5):721–729. Ekren, I., Keller, C., Touzi, N., and Zhang, J. (2014). On viscosity solutions of path dependent PDEs. The Annals of Probability, 42(1):204–236. Evans, A. (2020). Liquidity provider returns in geometric mean markets. arXiv preprint arXiv:2006.08806. He, S., Manela, A., Ross, O., and von Wachter, V. (2022). Fundamentals of perpetual futures. arXiv:2212.06888. Protter, P. E. (2005). Stochastic integration and diferential equations, volume 21 of Stochastic Modelling and Applied Probability. Springer-Verlag, Berlin, second edition. Corrected third printing. Ruan, Q. and Streltsov, A. (2024). Perpetual futures contracts and cryptocurrency market quality. SSRN:4218907. Viens, F. and Zhang, J. (2019). A martingale approach for fractional Brownian motions and related path dependent PDEs. The Annals of Applied Probability, 29(6):3489–3540. Wang, S. and Zhang, T. (2025). Spot-futures manipulations in cryptocurrency markets. SSRN: 5125326. Zhang, J. (2017). Backward Stochastic Diferential Equations: From Linear to Fully Nonlinear Theory, volume 86. Springer.
