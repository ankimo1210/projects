# 2014-gatheral-jacquier-arbitrage-free-svi

<!-- page: 1 -->

## Arbitrage-free SVI volatility surfaces

Jim Gatheral<sup>∗</sup>, Antoine Jacquier<sup>†</sup>

November 27, 2024

## Abstract

In this article, we show how to calibrate the widely-used SVI parameterization of the implied volatility smile in such a way as to guarantee the absence of static arbitrage. In particular, we exhibit a large class of arbitrage-free SVI volatility surfaces with a simple closed-form representation. We demonstrate the high quality of typical SVI fits with a numerical example using recent SPX options data.

## 1 Introduction

The stochastic volatility inspired or SVI parameterization of the implied volatility smile was originally devised at Merrill Lynch in 1999 and subsequently publicly disseminated in [13]. This parameterization has two key properties that have led to its popularity with practitioners:

• For a fixed time to expiry t, the implied Black-Scholes variance $\sigma _ { \mathrm { B S } } ^ { 2 } ( k , t )$ is linear in the log-strike k as $| k | \to \infty$ consistent with Roger Lee’s moment formula [23].

• It is relatively easy to fit listed option prices whilst ensuring no calendar spread arbitrage.

The consistency of the SVI parameterization with arbitrage bounds for extreme strikes has also led to its use as an extrapolation formula [20]. Moreover, as shown in [15], the SVI parameterization is not arbitrary in the sense that the large-maturity limit of the Heston implied volatility smile is exactly SVI. However it is well-known that SVI smiles may be arbitrageable. Previous work has shown how to calibrate SVI to given implied volatility data (for example [27]). Other recent work [6] has been concerned with showing how to parameterize the volatility surface in such a way as to preclude dynamic arbitrage. There has been some work on arbitrage-free interpolation of implied volatilities or equivalently of option prices [1], [11], [16], [21]. Prior work has not successfully attempted to eliminate static arbitrage and indeed, eforts to find simple closed-form arbitrage-free parameterizations of the implied volatility surface are still widely considered to be futile.

arXiv:1204.0646v4 [q-fin.PR] 21 Mar 2013

<sup>∗</sup>Department of Mathematics, Baruch College, CUNY. jim.gatheral@baruch.cuny.edu

<sup>†</sup>Department of Mathematics, Imperial College, London. ajacquie@imperial.ac.uk

<!-- page: 2 -->

In this article, we exhibit a large class of SVI volatility surfaces with a simple closedform representation, for which absence of static arbitrage is guaranteed. Absence of static arbitrage—as defined by Cox and Hobson [8]—corresponds to the existence of a non-negative martingale on a filtered probability space such that European call option prices can be written as the expectation, under the risk-neutral measure, of their final payofs. This definition also implies (see [11]) that the corresponding total variance must be an increasing function of the maturity (absence of calendar spread arbitrage). Using some mathematics from the Renaissance, we show how to eliminate any calendar spread arbitrage resulting from a given set of SVI parameters. We also present a set of necessary conditions for the corresponding density to be non-negative (absence of butterfly arbitrage), which corresponds—from the definition of static arbitrage—to call prices being decreasing and convex functions of the strike. We go on to use the existence of such arbitrage-free surfaces to devise a new algorithm for eliminating butterfly arbitrage should it occur. With both types of arbitrage eliminated, we achieve a volatility surface that typically calibrates well to given implied volatility data and is guaranteed free of static arbitrage.

In Section 2.1, we present a necessary and suficient condition for the absence of calendar spread arbitrage. In Section 2.2, we present a necessary and suficient condition for the absence of butterfly arbitrage, or negative densities. In Section 3, we present various equivalent forms of the SVI parameterization. In Section 4, we exhibit a large and useful class of SVI volatility surfaces that are guaranteed to be free of static arbitrage. In Section 5, we show how to calibrate SVI to observed option prices, avoiding both butterfly and calendar spread arbitrages. We further show how to interpolate and extrapolate in such a way as to guarantee the absence of static arbitrage. Finally, in Section 6, we summarize and conclude.

Notations. In the foregoing, we consider a stock price process $\left( S _ { t } \right) _ { t > 0 }$ with natural filtration $\left( \mathcal { F } _ { t } \right) _ { t > 0 }$ , and we define the forward price process $\left( F _ { t } \right) _ { t \geq 0 }$ by $\bar { F _ { t } } : = \mathbb { E } \left( S _ { t } | \mathcal { F } _ { 0 } \right)$ For any $k \in \mathbb { R }$ and $t > 0 , C _ { \mathrm { B S } } ( k , \sigma ^ { 2 } t )$ denotes the Black-Scholes price of a European Call option on S with strike $F _ { t } \mathrm { e } ^ { k }$ , maturity t and volatility $\sigma > 0$ . We shall denote the Black-Scholes implied volatility by $\sigma _ { \mathrm { B S } } ( k , t )$ , and define the total implied variance by

$$
w ( k , t ) = \sigma _ { \mathrm { B S } } ^ { 2 } ( k , t ) t .
$$

The implied variance v shall be equivalently defined as $v ( k , t ) = \sigma _ { \mathrm { B S } } ^ { 2 } ( k , t ) = w ( k , t ) / t$ . We shall refer to the two-dimensional map $( k , t ) \mapsto w ( k , t )$ as the volatility surface, and for any fixed maturity $t > 0 ,$ , the function $k \mapsto w ( k , t )$ will represent a slice. We propose below three diferent—yet equivalent—slice parameterizations of the total implied variance, and give the exact correspondence between them. For a given maturity slice, we shall use the notation $w ( k ; \chi )$ where χ represents a set of parameters, and drop the t-dependence.

<!-- page: 3 -->

## 2 Characterisation of static arbitrage

In this section we provide model-independent definitions of (static) arbitrage and some preliminary results. We define static arbitrage for a given volatility surface in the following way, which is equivalent to the definition of static arbitrage for call options recalled in the introduction (see also [25]).

Definition 2.1. A volatility surface is free of static arbitrage if and only if the following conditions are satisfied:

(i) it is free of calendar spread arbitrage;

(ii) each time slice is free of butterfly arbitrage.

In particular, absence of butterfly arbitrage ensures the existence of a (non-negative) probability density, and absence of calendar spread arbitrage implies monotonicity of option prices with respect to the maturity. The following two subsections analyse in details each of these two types of arbitrage, in a model-independent way.

## 2.1 Calendar spread arbitrage

Calendar spread arbitrage is usually expressed as the monotonicity of European call option prices with respect to the maturity (see for example [5] or [9]). Since our main focus here is on the implied volatility, we translate this definition into a property of the implied volatility. Indeed, assuming proportional dividends, we establish a necessary and suficient condition for an implied volatility parameterization to be free of calendar spread arbitrage. This can also be found in [11] and [13] and we outline its proof for completeness.

Lemma 2.1. If dividends are proportional to the stock price, the volatility surface w is free of calendar spread arbitrage if and only if

$$
\partial _ { t } w ( k , t ) \geq 0 , \quad f o r \ a l l \ k \in \mathbb { R } \ a n d t > 0 .
$$

Proof. Let $\left( X _ { t } \right) _ { t \geq 0 }$ be a martingale, $L \geq 0$ and $0 \leq t _ { 1 } < t _ { 2 }$ . Then the inequality

$$
\mathbb { E } \left[ ( X _ { t _ { 2 } } - L ) ^ { + } \right] \geq \mathbb { E } \left[ ( X _ { t _ { 1 } } - L ) ^ { + } \right]
$$

is standard. For any $i = 1 , 2$ , let $C _ { i }$ be options with strikes $K _ { i }$ and expirations $t _ { i }$ . Suppose that the two options have the same moneyness, i.e.

$$
{ \frac { K _ { 1 } } { F _ { t _ { 1 } } } } = { \frac { K _ { 2 } } { F _ { t _ { 2 } } } } = : \operatorname { e } ^ { k }
$$

Then, if dividends are proportional, the process $( X _ { t } ) _ { t \geq 0 }$ defined by $X _ { t } : = { \cal S } _ { t } / F _ { t }$ for all $t \geq 0$ is a martingale and

$$
\frac { C _ { 2 } } { K _ { 2 } } = \mathrm { e } ^ { - k } \mathbb { E } \left[ \left( X _ { t _ { 2 } } - \mathrm { e } ^ { k } \right) ^ { + } \right] \geq \mathrm { e } ^ { - k } \mathbb { E } \left[ \left( X _ { t _ { 1 } } - \mathrm { e } ^ { k } \right) ^ { + } \right] = \frac { C _ { 1 } } { K _ { 1 } }
$$

<!-- page: 4 -->

So, if dividends are proportional, keeping the moneyness constant, option prices are nondecreasing in time to expiration. The Black-Scholes formula for the non-discounted value of an option may be expressed in the form $C _ { \mathrm { B S } } ( k , w ( k , t ) )$ with $C _ { \mathrm { B S } }$ strictly increasing in its second argument. It follows that for fixed k, the function $w ( k , \cdot )$ must be nondecreasing. □

Lemma 2.1 motivates the following definition.

Definition 2.2. A volatility surface w is free of calendar spread arbitrage if

$$
\partial _ { t } w ( k , t ) \geq 0 , \quad f o r \ a l l \ k \in \mathbb { R } \ a n d t > 0 .
$$

## 2.2 Butterfly arbitrage

In Section 2.1, we provided conditions under which a volatility surface could be guaranteed to be free of calendar spread arbitrage. We now consider a diferent type of arbitrage, namely butterfly arbitrage (Definition 2.3). Absence of this arbitrage corresponds to the existence of a risk-neutral martingale measure and the classical definition of no static arbitrage, as developed in [12] or [8]. In this section, we consider only one slice of the implied volatility surface, i.e. the map $k \mapsto w ( k , t )$ for a given fixed maturity $t > 0$ . For clarity we therefore drop—in this section only—the t-dependence of the smile and use the notation $w ( k )$ instead. Unless otherwise stated, we shall always assume that the map $k \mapsto w ( k , t )$ is at least of class ${ \mathcal { C } } ^ { 2 } ( \mathbb { R } )$ for all $t \geq 0$

Definition 2.3. A slice is said to be free of butterfly arbitrage if the corresponding density is non-negative.

Recall the Black-Scholes formula for a European call option price:

$$
C _ { \mathrm { B S } } ( k , w ( k ) ) = S \left( \mathcal { N } ( d _ { + } ( k ) ) - \mathrm { e } ^ { k } \mathcal { N } ( d _ { - } ( k ) ) \right) , \quad \mathrm { f o r ~ a l l ~ } k \in \mathbb { R } ,
$$

where $\mathcal { N }$ is the Gaussian cdf and $d _ { \pm } ( k ) : = - k / \sqrt { w ( k ) } \pm \sqrt { w ( k ) } / 2$ . Let us define the function $g : \mathbb { R } \mathbb { R }$ by

$$
g ( k ) : = \left( 1 - \frac { k w ^ { \prime } ( k ) } { 2 w ( k ) } \right) ^ { 2 } - \frac { w ^ { \prime } ( k ) ^ { 2 } } { 4 } \left( \frac { 1 } { w ( k ) } + \frac { 1 } { 4 } \right) + \frac { w ^ { \prime \prime } ( k ) } { 2 } .\tag{2.1}
$$

This function will be the main ingredient in the determination of butterfly arbitrage as stated in the following lemma.

Lemma 2.2. A slice is free of butterfly arbitrage if and only if $g ( k ) \geq 0$ for all $k \in \mathbb { R }$ and $\operatorname* { l i m } _ { k \to + \infty } d _ { + } ( k ) = - \infty$

<!-- page: 5 -->

Proof. It is well known [2] that the probability density function p may be computed from the call price function C as

$$
p ( k ) = \left. \frac { \partial ^ { 2 } C ( k ) } { \partial K ^ { 2 } } \right| _ { K = F _ { \mathrm { f } } \mathrm { e } ^ { k } } = \left. \frac { \partial ^ { 2 } C _ { \mathrm { B S } } ( k , w ( k ) ) } { \partial K ^ { 2 } } \right| _ { K = F _ { \mathrm { f } } \mathrm { e } ^ { k } } , \quad \mathrm { f o r ~ a n y } \ k \in \mathbb { R } .
$$

Explicit diferentiation of the Black-Scholes formula then gives for any $k \in \mathbb { R }$

$$
p ( k ) = \frac { g ( k ) } { \sqrt { 2 \pi w ( k ) } } \exp \left( - \frac { d _ { - } ( k ) ^ { 2 } } { 2 } \right) .
$$

We have so far implicitly assumed that the function $p$ is a well-defined density, and in particular that it integrates to one. This may not always be the case though, and one needs to impose asymptotic boundary conditions. In particular, call prices must converge to 0 as k tends to infinity, which is equivalent to having $\begin{array} { r } { \operatorname* { l i m } _ { k \to + \infty } d _ { + } ( k ) = - \infty } \end{array}$ . We refer the reader to [24] for a proof of this equivalence. □

## 3 SVI formulations

We first recall here the original SVI formulation proposed in [13], and then present some alternative (but equivalent) ones. We emphasize in particular that even though the original $( ^ { 6 \cdot } \mathrm { r a w } ^ { \prime \prime } )$ formulation is very tractable and has become popular with practitioners, it is dificult—seemingly impossible—to find precise conditions on the parameters to prevent arbitrage.

## 3.1 The raw SVI parameterization

For a given parameter set $\chi _ { R } = \{ a , b , \rho , m , \sigma \}$ , the raw SVI parameterization of total implied variance reads:

$$
w ( k ; \chi _ { R } ) = a + b \left\{ \rho ( k - m ) + \sqrt { ( k - m ) ^ { 2 } + \sigma ^ { 2 } } \right\} ,\tag{3.1}
$$

where $a \in \mathbb { R } , b \geq 0 , | \rho | < 1 , m \in \mathbb { R } , \sigma > 0$ , and the obvious condition $a + b \sigma \sqrt { 1 - \rho ^ { 2 } } \ge 0$ which ensures that $w ( k ; \chi _ { R } ) ~ \geq ~ 0$ for all $k \in \mathbb { R }$ . This condition indeed ensures that the minimum of the function $w ( \cdot ; \chi _ { R } )$ is non-negative. Note further that the function $k \mapsto w ( k ; \chi _ { R } )$ is (strictly) convex on the whole real line. It follows immediately that changes in the parameters have the following efects:

• Increasing a increases the general level of variance, a vertical translation of the smile;

• Increasing b increases the slopes of both the put and call wings, tightening the smile;

• Increasing ρ decreases (increases) the slope of the left(right) wing, a counter-clockwise rotation of the smile;

<!-- page: 6 -->

• Increasing m translates the smile to the right;

• Increasing σ reduces the at-the-money (ATM) curvature of the smile.

We exclude the trivial cases $\rho = 1$ and $\rho = - 1$ , where the volatility smile is respectively strictly increasing and decreasing. We also exclude the case $\sigma = 0$ which corresponds to a linear smile.

## 3.2 The natural SVI parameterization

For a given parameter set $\chi _ { N } = \{ \Delta , \mu , \rho , \omega , \zeta \}$ , the natural SVI parameterization of total implied variance reads:

$$
w ( k ; \chi _ { N } ) = \Delta + \frac { \omega } { 2 } \left\{ 1 + \zeta \rho \left( k - \mu \right) + \sqrt { \left( \zeta ( k - \mu ) + \rho \right) ^ { 2 } + \left( 1 - \rho ^ { 2 } \right) } \right\} ,\tag{3.2}
$$

where $\omega \ge 0 , \Delta \in \mathbb { R } , \mu \in \mathbb { R } , | \rho | < 1$ and $\zeta > 0$ . It is straightforward to derive the following correspondence between the raw and natural SVI parameters:

Lemma 3.1. We have the following mapping of parameters between the raw and the natural SVI:

$$
\left( a , b , \rho , m , \sigma \right) = \left( \Delta + \frac { \omega } { 2 } \left( 1 - \rho ^ { 2 } \right) , \frac { \omega \zeta } { 2 } , \rho , \mu - \frac { \rho } { \zeta } , \frac { \sqrt { 1 - \rho ^ { 2 } } } { \zeta } \right) ,\tag{3.3}
$$

and its inverse transformation, between the natural and the raw SVI:

$$
\left( \Delta , \mu , \rho , \omega , \zeta \right) = \left( a - \frac { \omega } { 2 } \left( 1 - \rho ^ { 2 } \right) , m + \frac { \rho \sigma } { \sqrt { 1 - \rho ^ { 2 } } } , \rho , \frac { 2 b \sigma } { \sqrt { 1 - \rho ^ { 2 } } } , \frac { \sqrt { 1 - \rho ^ { 2 } } } { \sigma } \right) .\tag{3.4}
$$

## 3.3 The SVI Jump-Wings (SVI-JW) parameterization

Neither the raw SVI nor the natural SVI parameterizations are intuitive to traders in the sense that a trader cannot be expected to carry around the typical value of these parameters in his head. Moreover, there is no reason to expect these parameters to be particularly stable. The SVI-Jump-Wings (SVI-JW) parameterization of the implied variance v (rather than the implied total variance w) was inspired by a similar parameterization attributed to Tim Klassen, then at Goldman Sachs. For a given time to expiry $t > 0$ and a parameter set $\chi _ { J } = \{ v _ { t } , \psi _ { t } , p _ { t } , c _ { t } , \widetilde { v } _ { t } \}$ the SVI-JW parameters are defined from

<!-- page: 7 -->

the raw SVI parameters as follows:

$$
\begin{array} { r l } { v _ { t } } & { = \displaystyle \frac { a + b \left\{ - \rho m + \sqrt { m ^ { 2 } + \sigma ^ { 2 } } \right\} } { \sqrt { w _ { t } } } , } \\ { \psi _ { t } } & { = \displaystyle \frac { 1 } { \sqrt { w _ { t } } } \frac { b } { 2 } \left( - \frac { m } { \sqrt { m ^ { 2 } + \sigma ^ { 2 } } } + \rho \right) , } \\ { p _ { t } } & { = \displaystyle \frac { 1 } { \sqrt { w _ { t } } } b ( 1 - \rho ) , } \\ { c _ { t } } & { = \displaystyle \frac { 1 } { \sqrt { w _ { t } } } b ( 1 + \rho ) , } \\ { \widetilde v _ { t } } & { = \displaystyle \frac { 1 } { t } \left( a + b \sigma \sqrt { 1 - \rho ^ { 2 } } \right) , } \end{array}\tag{3.5}
$$

with $w _ { t } : = v _ { t } t$ . Note that this parameterization has an explicit dependence on the time to expiration t, and hence can be viewed as generalizing the raw (expiration-independent) SVI parameterization. The SVI-JW parameters have the following interpretations:

• $v _ { t }$ gives the ATM variance;

• $\psi _ { t }$ gives the ATM skew;

• $p _ { t }$ gives the slope of the left (put) wing;

• $c _ { t }$ gives the slope of the right (call) wing;

• $\widetilde { v } _ { t }$ is the minimum implied variance.

If smiles scaled perfectly as $1 / \sqrt { w _ { t } }$ (as is approximately the case empirically), these parameters would be constant, independent of the slice t. This makes it easy to extrapolate the SVI surface to expirations beyond the longest expiration in the data set. Also note that by definition, for any $t > 0$ we have

$$
\psi _ { t } = \left. \frac { \partial \sigma _ { \mathrm { B S } } ( k , t ) } { \partial k } \right| _ { k = 0 }
$$

The choice of volatility skew as the skew measure rather than variance skew for example, reflects the empirical observation that volatility is roughly lognormally distributed. Specifically, following the lines of [14, Chapter 7], assume that the instantaneous variance process satisfies the SDE

$$
d v _ { t } = \alpha ( v _ { t } ) d t + \eta \sqrt { v _ { t } } \beta ( v _ { t } ) d Z _ { t } , \quad \mathrm { f o r ~ a l l } \ t \geq 0
$$

where $\eta > 0 , ( Z _ { t } ) _ { t \geq 0 }$ is a standard Brownian motion and α and $\beta$ two functions on $\mathbb { R } _ { + }$ ensuring the existence of a unique strong solution to the SDE (see for instance [22] for exact conditions), then the ATM variance skew

$$
\operatorname* { l i m } _ { t  0 } \frac { \partial \sigma _ { \mathrm { B S } } ( k , t ) ^ { 2 } } { \partial k } \bigg | _ { k = 0 }
$$

<!-- page: 8 -->

exists and is proportional to $\beta ( v )$ . If the variance process is lognormal so that $\beta ( v )$ behaves like $\sqrt { v }$ , the limit of the at-the-money volatility skew as time to expiry tends to zero is constant and independent of the volatility level. This consistency of the SVI-JW parameterization with empirical volatility dynamics thus leads in practice to greater parameter stability over time. The following lemma provides the inverse representation of (3.5).

Lemma 3.2. Assume that m $\neq 0$ . For any $t > 0$ , define the (t-dependent) quantities:

$$
\beta : = \rho - \frac { 2 \psi _ { t } \sqrt { w _ { t } } } { b } a n d \alpha : = \mathrm { s i g n } ( \beta ) \sqrt { \frac { 1 } { \beta ^ { 2 } } - 1 } .
$$

where we have further assumed that $\beta \in [ - 1 , 1 ] ^ { 1 }$ . Then, the raw SVI and SVI-JW parameters are related as follows:

$$
\begin{array} { l l l } { { b } } & { { = } } & { { \displaystyle \frac { \sqrt { w _ { t } } } { 2 } \left( c _ { t } + p _ { t } \right) , } } \\ { { \rho } } & { { = } } & { { 1 - \displaystyle \frac { p _ { t } \sqrt { w _ { t } } } { b } , } } \\ { { a } } & { { = } } & { { \displaystyle \widetilde v _ { t } t - b \sigma \sqrt { 1 - \rho ^ { 2 } } , } } \\ { { m } } & { { = } } & { { \displaystyle \frac { \left( v _ { t } - \widetilde v _ { t } \right) t } { b \left\{ - \rho + \mathrm { s i g n } ( \alpha ) \sqrt { 1 + \alpha ^ { 2 } } - \alpha \sqrt { 1 - \rho ^ { 2 } } \right\} } , } } \\ { { \sigma } } & { { = } } & { { \alpha m . } } \end{array}
$$

If $m = 0$ , then the formulae above for $b , \rho$ and a still hold, but $\sigma = \left( v _ { t } t - a \right) / b$

Proof. The expressions for $b , \rho$ and a follow directly from (3.5). Assume that $m \neq 0$ and let $\beta : = \rho - 2 \psi _ { t } \sqrt { w _ { t } } / b$ and $\alpha : = \sigma / m \in \mathbb { R }$ . Then the expressions in (3.5) give

$$
\beta = \frac { \mathrm { s i g n } \left( \alpha \right) } { \sqrt { 1 + \alpha ^ { 2 } } } ,
$$

which implies that

$$
\alpha = \mathrm { s i g n } ( \beta ) \sqrt { \frac { 1 } { \beta ^ { 2 } } - 1 } .
$$

Using (3.5), we also have

$$
{ \frac { \left( v _ { t } - \widetilde v _ { t } \right) t } { b } } = m \left\{ - \rho + \mathrm { s i g n } ( \alpha ) \sqrt { 1 + \alpha ^ { 2 } } - \alpha \sqrt { 1 - \rho ^ { 2 } } \right\} ,
$$

from which we deduce $m$ in terms of $\alpha ,$ , and the expression of $\sigma$ is recovered from the equality $\sigma = \alpha m$ . The expression for $\sigma$ in the case $m = 0$ is straightforward from (3.5).

<sup>1</sup>The condition β ∈ [−1, 1] is equivalent to −p<sub>t</sub> ≤ 2ψ<sub>t</sub> ≤ c<sub>t</sub>, i.e. to the convexity of the smile.

<!-- page: 9 -->

## 3.4 Arbitrage and absence thereof in SVI parameterizations

Given a volatility surface, it is natural to wonder whether it is free of arbitrage. Since we can easily switch from any of the SVI formulations to either of the other two using Lemma 3.3 and Lemma 3.2, we shall state the following results only for the raw SVI parameterization (3.1). Referring to (3.1) as a volatility surface is a slight abuse of language since (3.1) is really an expiry-independent slice parameterization. A volatility surface is thus understood as a (discrete) collection of slices, with a diferent set of parameters for each expiry. Checking calendar arbitrage in the sense of Lemma 2.1 is then equivalent to checking for calendar arbitrage for any pair of expiries $t _ { 1 }$ and $t _ { 2 }$ . The following lemma establishes a suficient condition for the absence of calendar spread arbitrage.

Lemma 3.3. The raw SVI surface (3.1) is free of calendar spread arbitrage $i f$ a certain quartic polynomial (given in (3.7) below) has no real root.

Proof. By definition, there is no calendar arbitrage if for any two dates $t _ { 1 } \neq t _ { 2 }$ , the corresponding slices $w \left( \cdot , t _ { 1 } \right)$ and $w \left( \cdot , t _ { 2 } \right)$ do not intersect. Let these two slices be characterised by the sets of parameters $\chi _ { 1 } : = \{ a _ { 1 } , b _ { 1 } , \sigma _ { 1 } , \rho _ { 1 } , m _ { 1 } \}$ and $\chi _ { 2 } : = \{ a _ { 2 } , b _ { 2 } , \sigma _ { 2 } , \rho _ { 2 } , m _ { 2 } \}$ , and assume for convenience that $0 < t _ { 1 } < t _ { 2 }$ . We therefore need to determine the (real) roots of the equation w $\left( k , t _ { 1 } \right) = w \left( k , t _ { 2 } \right)$ . The latter is equivalent to

$$
a _ { 1 } + b _ { 1 } \left\{ \rho _ { 1 } \left( k - m _ { 1 } \right) + \sqrt { \left( k - m _ { 1 } \right) ^ { 2 } + \sigma _ { 1 } ^ { 2 } } \right\} = a _ { 2 } + b _ { 2 } \left\{ \rho _ { 2 } \left( k - m _ { 2 } \right) + \sqrt { \left( k - m _ { 2 } \right) ^ { 2 } + \sigma _ { 2 } ^ { 2 } } \right\} .\tag{3.6}
$$

Leaving $\sqrt { \left( k - m _ { 1 } \right) ^ { 2 } + \sigma _ { 1 } ^ { 2 } }$ on one side, squaring the equality and rearranging it leads to

$$
2 b _ { 2 } \left( \alpha + \beta k \right) \sqrt { \left( k - m _ { 2 } \right) ^ { 2 } + \sigma _ { 2 } ^ { 2 } = b _ { 1 } ^ { 2 } \left\{ \left( k - m _ { 1 } \right) ^ { 2 } + \sigma _ { 1 } ^ { 2 } \right\} - b _ { 2 } ^ { 2 } \left\{ \left( k - m _ { 2 } \right) ^ { 2 } + \sigma _ { 2 } ^ { 2 } \right\} - \left( \alpha + \beta k \right) ^ { 2 } } ,
$$

where $\alpha : = a _ { 2 } - a _ { 1 } + b _ { 1 } \rho _ { 1 } m _ { 1 } - b _ { 2 } \rho _ { 2 } m _ { 2 }$ and $\beta : = b _ { 2 } \rho _ { 2 } - b _ { 1 } \rho _ { 1 }$ . Squaring the last equation above gives a quartic polynomial equation of the form

$$
\alpha _ { 4 } k ^ { 4 } + \alpha _ { 3 } k ^ { 3 } + \alpha _ { 2 } k ^ { 2 } + \alpha _ { 1 } k + \alpha _ { 0 } = 0 ,\tag{3.7}
$$

where each of the coeficients lengthy yet explicit expressions<sup>2</sup> in terms of the parameters $\{ a _ { 1 } , b _ { 1 } , \rho _ { 1 } , \sigma _ { 1 } , m _ { 1 } \}$ and $\{ a _ { 2 } , b _ { 2 } , \rho _ { 2 } , \sigma _ { 2 } , m _ { 2 } \}$ . If this quartic polynomial has no real root, then the slices do not intersect and the lemma follows. Roots of a quartic polynomial are known in closed-form thanks to Ferrari and Cardano [3]. Thus there exist closed-form expressions in terms of $\chi _ { 1 }$ and $\chi _ { 2 }$ for the possible intersection points of the two SVI slices. □

Remark 3.1. If the quartic polynomial (3.7) has one or more real roots, we need to check whether the latter are indeed solutions of the original problem (3.6), or spurious solutions arising from the two squaring operations. The absence of real roots of the quartic polynomial is clearly a suficient—but not necessary—condition.

<sup>2</sup>Explicit expressions for these coeficients can be found in the R-code posted on http://faculty. baruch.cuny.edu/jgatheral.

<!-- page: 10 -->

Remark 3.2. By a careful study of the minima and the shapes of the two slices $w ( \cdot , t _ { 1 } )$ and $w ( \cdot , t _ { 2 } )$ , it is possible to determine a set of conditions on the parameters ensuring no calendar spread arbitrage. However these conditions involve tedious combinations of the parameters and will hence not match the computational simplicity of the lemma.

For a given slice, we now wish to determine conditions on the parameters of the raw SVI formulation (3.1) such that butterfly arbitrage is excluded. By Lemma 2.1, this is equivalent to showing (i) that the function $g$ defined in (2.1) is always positive and (ii) that call prices converge to zero as the strike tends to infinity. Sadly, the highly non-linear behaviour of $g$ makes it seemingly impossible to find general conditions on the parameters that would eliminate butterfly arbitrage. We provide below an example where butterfly arbitrage is violated. Notwithstanding our inability to find general conditions on the parameters that would preclude arbitrage, in Section 4, we will introduce a new sub-class of SVI volatility surface for which the absence of butterfly arbitrage is guaranteed for all expiries.

Example 3.1. (From Axel Vogt on wilmott.com) Consider the raw SVI parameters:

$$
( a , b , m , \rho , \sigma ) = \left( - 0 . 0 4 1 0 , 0 . 1 3 3 1 , 0 . 3 5 8 6 , 0 . 3 0 6 0 , 0 . 4 1 5 3 \right) ,\tag{3.8}
$$

with $t = 1$ . These parameters give rise to the total variance smile w and the function g (defined in (2.1)) on Figure $^ { 1 , }$ where the negative density is clearly visible.

![](assets/figures/2014-gatheral-jacquier-arbitrage-free-svi-p0010-block-0006-faed9aab90991617.jpg)

![Figure 1: Plots of the total variance smile w (left) and the function $g$ defined in (2.1) (right), using the parameters (3.8).](assets/figures/2014-gatheral-jacquier-arbitrage-free-svi-p0010-block-0007-8b870cec0f3e844a.jpg)

## 4 Surface SVI: A surface free of static arbitrage

We now introduce a class of SVI volatility surfaces—which we shall call SSVI (for ‘Surface SVI’)—as an extension of the natural parameterization (3.2). For any maturity $t \geq 0$

<!-- page: 11 -->

define the at-the-money (ATM) implied total variance $\theta _ { t } : = \sigma _ { \mathrm { B S } } ^ { 2 } ( 0 , t ) t$ . We shall assume that the function θ is at least of class $\mathcal { C } ^ { 1 }$ on $\mathbb { R } _ { + } ^ { * }$ . An ATM option with zero time to expiry has no value so $\begin{array} { r } { \theta _ { 0 } : = \operatorname* { l i m } _ { t 0 } \theta _ { t } = 0 } \end{array}$

Definition 4.1. Let $\varphi$ be a smooth function from $\mathbb { R } _ { + } ^ { * }$ to $\mathbb { R } _ { + } ^ { * }$ such that the limit lim $_ { 1 \ell \to 0 } \theta _ { t } \varphi ( \theta _ { t } )$ exists in R. We refer to as SSVI the surface defined $b y$

$$
w ( k , \theta _ { t } ) = \frac { \theta _ { t } } { 2 } \left\{ 1 + \rho \varphi ( \theta _ { t } ) k + \sqrt { \left( \varphi ( \theta _ { t } ) k + \rho \right) ^ { 2 } + ( 1 - \rho ^ { 2 } ) } \right\} .\tag{4.1}
$$

From Section 3, SSVI corresponds to the natural SVI volatility surface parameterization (3.2) with $\chi _ { N } ~ = ~ \{ 0 , 0 , \rho , \theta _ { t } , \varphi ( \theta _ { t } ) \}$ . Note that this representation amounts to considering the volatility surface in terms of ATM variance time, instead of standard calendar time, similar in spirit to the stochastic subordination of [7].

Remark 4.1. In the parameterization (4.1), the ATM variance curve $\theta _ { t }$ may be viewed as a (vector) parameter of the volatility surface. Moreover, this parameter is directly observable given market prices for a finite set of expiries, and can be considered wellknown to traders even for expiries which are not explicitly quoted. The explicit reference to $\theta _ { t }$ also emphasizes the importance of studies such as [10] of the ATM variance structure in classical models which may shed some light on how to impose dynamics on SSVI.

The ATM implied total variance is $\theta _ { t } = \sigma _ { \mathrm { B S } } ^ { 2 } ( 0 , t ) t$ and the ATM volatility skew is given by

$$
\partial _ { k } \sigma _ { \mathrm { B S } } ( k , t ) \vert _ { k = 0 } = \left. \frac { 1 } { 2 \sqrt { \theta _ { t } t } } \partial _ { k } w ( k , \theta _ { t } ) \right. _ { k = 0 } = \frac { \rho \sqrt { \theta _ { t } } } { 2 \sqrt { t } } \varphi ( \theta _ { t } ) .\tag{4.2}
$$

Furthermore the smile is symmetric around at-the-money if and only if $\rho = 0$ This is consistent with [4, Theorem 3.4] which states that in a standard stochastic volatility model, the smile is symmetric if and only if the correlation between the stock price and its instantaneous volatility is null. Since $\theta _ { 0 } = 0$ , we have at time $t = 0$

$$
w ( k , \theta _ { 0 } ) = \frac 1 2 \phi _ { 0 } \left( \rho k + \vert k \vert \right) , \quad \mathrm { f o r ~ a n y } \ k \in \mathbb { R } ,\tag{4.3}
$$

where $\begin{array} { r } { \phi _ { 0 } : = \operatorname* { l i m } _ { \theta \to 0 } \theta \varphi ( \theta ) . \ \phi _ { 0 } = 0 } \end{array}$ is characteristic of stochastic volatility models as in Example 4.1; $\phi _ { 0 } > 0$ as in Example 4.2 gives a V-shaped time zero smile which is characteristic of models with jumps and in particular, characteristic of empirically observed volatility surfaces. For notational convenience, we shall always assume that lim $_ { t \nearrow \infty } \theta _ { t } = \infty$ . As proved in [24], this is equivalent (assuming no interest rate) to the stock price (assumed to be a non-negative martingale) to converging to zero as t tends to infinity. Although this holds in many popular models (Black-Scholes, Heston, exponential L´evy), this is not always true, see [19] for counter-examples. If lim $1 _ { t \nearrow \infty } \theta _ { t }$ is finite, all our results remain valid, but only on the support of the function $t \mapsto \theta _ { t }$

The following theorem gives precise necessary and suficient conditions to ensure that the SSVI volatility surface (4.1) is free of calendar spread arbitrage (Lemma 2.1) and also matches the term structure of ATM volatility and the term structure of the ATM volatility skew.

<!-- page: 12 -->

Theorem 4.1. The SSVI surface (4.1) is free of calendar spread arbitrage if and only if

1. $\partial _ { t } \theta _ { t } \geq 0$ , for all $t \geq 0$

$$
\begin{array} { r } { 2 . \ 0 \leq \partial _ { \theta } ( \theta \varphi ( \theta ) ) \leq \frac { 1 } { \rho ^ { 2 } } \left( 1 + \sqrt { 1 - \rho ^ { 2 } } \right) \varphi ( \theta ) , \ f o r \ a l l \ \theta > 0 , } \end{array}
$$

where the upper bound is infinite when $\rho = 0$

In particular, this theorem implies that the SSVI surface (4.1) is free of calendar spread arbitrage if the skew in total variance terms is monotonically increasing in trading time and the skew in implied variance terms is monotonically decreasing in trading time. In practice, any reasonable skew term structure that a trader defines has these properties.

Proof. Since the definition of calendar spread arbitrage does not depend on the logmoneyness k, there is no loss of generality in assuming k fixed. First note that $\partial _ { t } w ( k , \theta _ { t } ) =$ $\partial _ { \theta } w ( k , \theta _ { t } ) \partial _ { t } \theta _ { t }$ so the SSVI volatility surface (4.1) is free of calendar spread arbitrage if $\partial _ { \theta } w ( k , \theta ) \geq 0$ for all $\theta > 0$

Consider first the case $| \rho | < 1$ . To proceed, we compute, for any $\theta > 0$

$$
2 \partial _ { \theta } w ( k , \theta ) = \psi _ { 0 } ( x , \rho ) + \gamma ( \theta ) \psi _ { 1 } ( x , \rho ) ,
$$

with $x : = k \varphi ( \theta ) , \gamma ( \theta ) : = \partial _ { \theta } ( \theta \varphi ( \theta ) ) / \varphi ( \theta )$

$$
\psi _ { 0 } ( x , \rho ) : = 1 + \frac { 1 + \rho x } { \sqrt { x ^ { 2 } + 2 \rho x + 1 } } \quad \mathrm { a n d } \quad \psi _ { 1 } ( x , \rho ) : = x \left\{ \frac { x + \rho } { \sqrt { x ^ { 2 } + 2 \rho x + 1 } } + \rho \right\} .
$$

For any $| \rho | < 1 , \psi _ { 0 } ( x , \rho )$ is strictly positive for all $x \in \mathbb { R }$ . Now define the set

$$
\mathcal { D } _ { \rho } = \left\{ \begin{array} { l l } { \left( - \infty , 0 \right) \cup \left( - 2 \rho , \infty \right) , } & { \quad \mathrm { i f ~ } \rho < 0 , } \\ { \left( - \infty , - 2 \rho \right) \cup \left( 0 , \infty \right) , } & { \quad \mathrm { i f ~ } \rho > 0 , } \\ { \mathbb { R } \setminus \left\{ 0 \right\} , } & { \quad \mathrm { i f ~ } \rho = 0 . } \end{array} \right.
$$

Then $\psi _ { 1 } ( \cdot , \rho ) > 0 \mathrm { ~ i f ~ } x \in { \mathcal { D } } _ { \rho }$ and $\psi _ { 1 } ( \cdot , \rho ) < 0$ if $x \in \mathbb { R } \setminus ( \mathcal { D } _ { \rho } \cup \{ 0 , - 2 \rho \} )$ . It follows that

$$
\partial _ { \theta } w ( k , \theta ) \geq 0 \mathrm { ~ i f ~ a n d ~ o n l y ~ i f ~ } \left\{ \begin{array} { l l } { \gamma ( \theta ) \geq - \displaystyle \frac { \psi _ { 0 } ( x , \rho ) } { \psi _ { 1 } ( x , \rho ) } , \mathrm { f o r ~ } x \in \mathcal { D } _ { \rho } , } \\ { \gamma ( \theta ) \leq - \displaystyle \frac { \psi _ { 0 } ( x , \rho ) } { \psi _ { 1 } ( x , \rho ) } , \mathrm { f o r ~ } x \in \mathbb { R } \setminus \left( \mathcal { D } _ { \rho } \cup \left\{ 0 , - 2 \rho \right\} \right) , } \end{array} \right.\tag{4.4}
$$

When $x \in \{ 0 , - 2 \rho \}$ , then $\psi _ { 1 } ( x , \rho ) = 0$ and so $\partial _ { \theta } w ( k , \theta ) \geq 0$ . The inequalities (4.4) thus give necessary and suficient conditions for absence of calendar spread arbitrage for any given $x \in \mathbb { R }$ . To determine the tightest possible bounds on $\gamma ( \theta )$ , we compute

$$
\operatorname* { s u p } _ { x \in \mathcal { D } _ { \rho } } - \frac { \psi _ { 0 } ( x , \rho ) } { \psi _ { 1 } ( x , \rho ) } = 0 \quad \mathrm { a n d } \quad \operatorname* { i n f } _ { x \in \mathbb { R } \backslash ( \mathcal { D } _ { \rho } \cup \{ 0 , - 2 \rho \} ) } - \frac { \psi _ { 0 } ( x , \rho ) } { \psi _ { 1 } ( x , \rho ) } = \frac { 1 + \sqrt { 1 - \rho ^ { 2 } } } { \rho ^ { 2 } } .
$$

<!-- page: 13 -->

The supremum in the first equality is never attained (the function increases to zero from below as |x| tends to infinity). However the infimum in the second equality is attained at $x = - \rho \notin \mathcal { D } _ { \rho }$ . It follows that

$$
\partial _ { \theta } w ( k , \theta ) \geq 0 { \mathrm { ~ i f ~ a n d ~ o n l y ~ i f ~ } } 0 \leq \gamma ( \theta ) \leq { \frac { 1 + { \sqrt { 1 - \rho ^ { 2 } } } } { \rho ^ { 2 } } } .
$$

Note that when $\rho = 0$ , the infimum above is taken over an empty set, and there is hence no upper bound.

When $\rho = 1$ , for any $( k , \theta ) \in \mathbb { R } \times ( 0 , \infty )$ , we have

$$
\partial _ { \theta } w ( k , \theta ) = \left( 1 + { \frac { 1 + x } { \sqrt { ( 1 + x ) ^ { 2 } } } } \right) \left( 1 + \gamma ( \theta ) x \right) = { \left\{ \begin{array} { l l } { 2 \left( 1 + \gamma ( \theta ) x \right) } & { { \mathrm { i f ~ } } x \geq - 1 , } \\ { 0 } & { { \mathrm { o t h e r w i s e . } } } \end{array} \right. }
$$

Obviously, $\partial _ { \theta } w ( k , \theta ) \geq 0 \mathrm { ~ i f ~ } x \geq 0$ . For $x > - 1$ , clearly $\partial _ { \theta } w ( k , \theta ) \geq 0$ if and only if $\gamma ( \theta ) \in [ 0 , 1 ]$ . Similarly, with $\rho = - 1$ , we have

$$
\partial _ { \theta } w ( k , \theta ) = \left( 1 + { \frac { 1 - x } { \sqrt { ( 1 - x ) ^ { 2 } } } } \right) \left( 1 - \gamma ( \theta ) x \right) = { \left\{ \begin{array} { l l } { 2 \left( 1 - \gamma ( \theta ) x \right) } & { { \mathrm { i f ~ } } x \leq 1 , } \\ { 0 } & { { \mathrm { o t h e r w i s e . } } } \end{array} \right. }
$$

Again $\partial _ { \theta } w ( k , \theta ) \geq 0 { \mathrm { ~ i f ~ } } x \leq 0$ , and for $x \leq 1 , \partial _ { \theta } w ( k , \theta ) \geq 0$ if and only if $\gamma ( \theta ) \in [ 0 , 1 ]$ .

The following lemma is a straightforward consequence of (3.3) and (3.5).

Lemma 4.1. The SVI-JW parameters associated with the SSVI surface (4.1) are

$$
\begin{array} { r c l } { { v _ { t } } } & { { = } } & { { \theta _ { t } / t , } } \end{array}
$$

$$
\psi _ { t } ~ = ~ { \frac { 1 } { 2 } } \rho \sqrt { \theta _ { t } } \varphi ( \theta _ { t } ) ,
$$

$$
p _ { t } ~ = ~ \frac { 1 } { 2 } \sqrt { \theta _ { t } } \varphi ( \theta _ { t } ) ( 1 - \rho ) ,
$$

$$
c _ { t } ~ = ~ \frac { 1 } { 2 } \sqrt { \theta _ { t } } \varphi ( \theta _ { t } ) ( 1 + \rho ) ,
$$

$$
\widetilde { v } _ { t } = \frac { \theta _ { t } } { t } ( 1 - \rho ^ { 2 } ) .
$$

We now give several examples of SSVI implied volatility surfaces (4.1).

## Example 4.1. A Heston-like parameterization

Consider the function $\varphi$ defined by

$$
\varphi ( \theta ) \equiv \frac { 1 } { \lambda \theta } \left\{ 1 - \frac { 1 - \mathrm { e } ^ { - \lambda \theta } } { \lambda \theta } \right\} ,
$$

with $\lambda > 0$ . Then for all $\theta > 0$ , we immediately obtain

$$
\partial _ { \theta } \left( \theta \varphi ( \theta ) \right) = \frac { \mathrm { e } ^ { - \lambda \theta } \left( \mathrm { e } ^ { \lambda \theta } - 1 - \lambda \theta \right) } { \lambda ^ { 2 } \theta ^ { 2 } } > 0 a n d \frac { \partial _ { \theta } \left( \theta \varphi ( \theta ) \right) } { \varphi ( \theta ) } = \frac { 1 - ( 1 + \lambda \theta ) \mathrm { e } ^ { - \lambda \theta } } { \mathrm { e } ^ { - \lambda \theta } + \lambda \theta - 1 } .
$$

<!-- page: 14 -->

For any $\lambda > 0 ,$ the map $\theta \mapsto \partial _ { \theta } \left( \theta \varphi ( \theta ) \right) / \varphi ( \theta )$ is strictly decreasing on $( 0 , \infty )$ with limit as θ tends to zero equal to one. Since the quantity $( 1 + \sqrt { 1 - \rho ^ { 2 } } ) / \rho ^ { 2 }$ is greater than one for any $\rho \in [ - 1 , 1 ]$ , the conditions of Theorem $\it 4 . 1$ are satisfied. This function is consistent with the implied variance skew in the Heston model as shown in $[ { 1 4 } ,$ , Equation 3.19].

## Example 4.2. Power-law parameterization

Consider $\varphi ( \theta ) = \eta \theta ^ { - \gamma }$ with $\eta > 0$ and $0 < \gamma < 1$ . Then ∂ $\left( \theta \varphi ( \theta ) \right) / \varphi ( \theta ) = 1 - \gamma \in ( 0 , 1 )$ holds for all $\theta > 0$ , and hence the conditions of Theorem 4.1 are satisfied. In particular $i f$ $\gamma = 1 / 2$ then Lemma 4.1 implies that the SVI-JW parameters $\psi _ { t } , p _ { t }$ , and $c _ { t }$ associated with the SSVI volatility surface (4.1) are constant and independent of the time to expiration t. Furthermore, Equation 4.2 implies that the ATM volatility skew is given by

$$
\partial _ { k } \sigma _ { \mathrm { B S } } ( k , t ) | _ { k = 0 } = \frac { \rho \eta } { 2 \sqrt { t } } .
$$

The following theorem provides suficient conditions for a SSVI surface (4.1) to be free of butterfly arbitrage.

Theorem 4.2. The SSVI volatility surface (4.1) is free of butterfly arbitrage if the following conditions are satisfied for all $\theta > 0 .$

$$
\begin{array} { r } { 1 . \ \theta \varphi ( \theta ) \left( 1 + | \rho | \right) < 4 ; } \end{array}
$$

2. $\theta \varphi ( \theta ) ^ { 2 } \left( 1 + | \rho | \right) \leq 4 .$

Proof. For ease of notation, we suppress the explicit dependence of $\theta$ and $\varphi$ on t. By symmetry, it is enough to prove the theorem for $0 \leq \rho < 1$ . We shall therefore assume so, and we define $z : = \varphi k$ . The function g defined in (2.1) reads

$$
g ( z ) = \frac { f ( z ) } { 6 4 \left( z ^ { 2 } + 2 z \rho + 1 \right) ^ { 3 / 2 } } ,
$$

where

$$
f ( z ) : = a - b \varphi ^ { 2 } \theta - \frac { c } { 1 6 } \varphi ^ { 2 } \theta ^ { 2 } ,
$$

and where a, b and c depend on z. In the following, we frequently use the inequality

$$
z ^ { 2 } + 2 z \rho + 1 = ( z + \rho ) ^ { 2 } + 1 - \rho ^ { 2 } \geq 0 .
$$

Computing the coeficient of $\varphi ^ { 2 } \theta ^ { 2 }$ in $f ( z )$ explicitly gives

$$
\begin{array} { r l } & { c = \sqrt { z ^ { 2 } + 2 z \rho + 1 } \left\{ \left( 1 + { \rho ^ { 2 } } \right) \left( z + \rho \right) ^ { 2 } + 2 \rho ( z + \rho ) \sqrt { z ^ { 2 } + 2 z \rho + 1 } + \left( 1 - { \rho ^ { 2 } } \right) { \rho ^ { 2 } } \right\} } \\ & { \geq \sqrt { z ^ { 2 } + 2 z \rho + 1 } \left\{ \left( 1 + { \rho ^ { 2 } } \right) \left( z + \rho \right) ^ { 2 } + 2 \rho ( z + \rho ) ^ { 2 } + \left( 1 - { \rho ^ { 2 } } \right) { \rho ^ { 2 } } \right\} } \\ & { = \sqrt { z ^ { 2 } + 2 z \rho + 1 } \left\{ \left( 1 + { \rho } \right) ^ { 2 } \left( z + \rho \right) ^ { 2 } + \left( 1 - { \rho ^ { 2 } } \right) { \rho ^ { 2 } } \right\} \geq 0 . } \end{array}
$$

<!-- page: 15 -->

Thus if

$$
0 \leq \theta \varphi \leq \frac { 4 } { 1 + \rho } \quad \mathrm { a n d } \quad 0 \leq \theta \varphi ^ { 2 } \leq \frac { 4 } { 1 + \rho } ,
$$

we have

$$
f ( z ) \geq { \left\{ \begin{array} { l l } { a - { \displaystyle { \frac { 4 b } { 1 + \varrho } } } - { \displaystyle { \frac { c } { ( 1 + \rho ) ^ { 2 } } } } = : f _ { 1 } ( z ) , } & { { \mathrm { i f ~ } } b \geq 0 , } \\ { a - { \displaystyle { \frac { c } { ( 1 + \rho ) ^ { 2 } } } } = : f _ { 2 } ( z ) , } & { { \mathrm { i f ~ } } b < 0 . } \end{array} \right. }
$$

It is then straightforward to verify that

$$
\begin{array} { r } { \frac { 2 f _ { 1 } \left( z \right) } { \left( 1 + \rho \right) ^ { 2 } } = \sqrt { z ^ { 2 } + 2 z \rho + 1 } \left\{ z ^ { 2 } \rho - z ( 1 - \rho ) \rho + 2 ( 1 + \rho ) \left( 1 - \rho ^ { 2 } \right) + \rho \right\} } \\ { + \rho \left( z + \rho \right) ^ { 2 } + 3 \rho \left( 1 - \rho ^ { 2 } \right) + 2 \left( 1 - \rho ^ { 2 } \right) - z \rho \left( z ^ { 2 } + 2 z \rho + 1 \right) , } \end{array}
$$

which is clearly positive for $z \ < \ 0$ . To see that $f _ { 1 } ( z )$ is also positive when $z > 0$ , we rewrite it as

$$
\begin{array} { r l } & { \frac { 2 f _ { 1 } ( z ) } { ( 1 + \rho ) ^ { 2 } } } \\ { = } & { \left\{ \sqrt { z ^ { 2 } + 2 z \rho + 1 } - ( z + \rho ) \right\} \Bigg \{ \rho \left( z - \frac { 1 - \rho } { 2 } \right) ^ { 2 } + 2 ( 1 + \rho ) \left( 1 - \rho ^ { 2 } \right) + \rho \left( 1 - \frac { ( 1 - \rho ) ^ { 2 } } { 4 } \right) \Bigg \} } \\ & { + ( 1 + \rho ) \left\{ z \left( 2 - \rho ^ { 2 } \right) + 2 \left( 1 + \rho \right) \left( 1 - \rho ^ { 2 } \right) + \rho \right\} . } \end{array}
$$

Consider now the function $f _ { 2 } ( z )$ . It is straightforward to verify that

$$
f _ { 2 } ( z ) = - \frac { 2 z ^ { 3 } \rho } { ( 1 + \rho ) ^ { 2 } } + { \left( z ^ { 2 } + 2 z \rho + 1 \right) } ^ { 3 / 2 } + 2 \left( z ^ { 2 } + 2 z \rho + 1 \right) + \sqrt { z ^ { 2 } + 2 z \rho + 1 }
$$

which is positive by inspection if $z < 0$ . To see that $f _ { 2 } ( z )$ is also positive when $z > 0$ , we rewrite it as

$$
\begin{array} { l } { { f _ { 2 } ( z ) = z ^ { 3 } \displaystyle \frac { 1 + \rho ^ { 2 } } { ( 1 + \rho ) ^ { 2 } } + 3 z ^ { 2 } \rho + 2 \left( z ^ { 2 } + 2 z \rho + 1 \right) } } \\ { { \mathrm { } + \left( z ^ { 2 } + 2 z \rho + 1 \right) \left\{ \sqrt { z ^ { 2 } + 2 z \rho + 1 } - ( z + \rho ) \right\} } } \\ { { \mathrm { } + \sqrt { z ^ { 2 } + 2 z \rho + 1 } + 2 z \rho ^ { 2 } + z + \rho . } } \end{array}
$$

Thus $f ( z ) \geq 0$ in all cases. From Lemma 2.2, we are left to prove that $\begin{array} { r } { \operatorname* { l i m } _ { k \to \infty } d _ { + } ( k ) = - \infty } \end{array}$ A straightforward computation shows that this is satisfied as soon as Condition 1 in Theorem 4.2 holds. □

Remark 4.2. A SSVI volatility surface (4.1) is free of butterfly arbitrage if

$$
\sqrt { v _ { t } t } \operatorname* { m a x } \left( p _ { t } , c _ { t } \right) < 2 , \quad a n d \quad ( p _ { t } + c _ { t } ) \operatorname* { m a x } \left( p _ { t } , c _ { t } \right) \leq 2 ,
$$

hold for all $t > 0$ . The proof follows from Lemma $\it 4 . 1$ by re-expressing Conditions 1 and 2 of Theorem $4 . 2$ in terms of SVI-JW parameters.

<!-- page: 16 -->

The following lemma shows that Theorem 4.2 is almost if-and-only-if.

Lemma 4.2. The SSVI volatility surface (4.1) is free of butterfly arbitrage only if

$$
\theta \varphi ( \theta ) \left( 1 + | \rho | \right) \leq 4 , \quad f o r \ a l l \ \theta > 0 .
$$

Moreover $i f \theta \varphi ( \theta ) \left( 1 + | \rho | \right) = 4$ , the SSVI surface is free of butterfly arbitrage only if

$$
\theta \varphi ( \theta ) ^ { 2 } \left( 1 + | \rho | \right) \leq 4 .
$$

Thus Condition 1 of Theorem $4 . 2$ is necessary and Condition 2 is tight.

Proof. Considering the SSVI surface (4.1) and the function g defined in (2.1), we have

$$
g ( k ) = \left\{ \begin{array} { l l } { \displaystyle \frac { 1 6 - \theta ^ { 2 } \varphi ( \theta ) ^ { 2 } \left( 1 + \rho \right) ^ { 2 } } { 6 4 } + \frac { 4 - \theta \varphi ( \theta ) ^ { 2 } \left( 1 + \rho \right) } { 8 \varphi ( \theta ) k } + \mathcal { O } \left( \frac { 1 } { k ^ { 2 } } \right) , } & { \mathrm { a s ~ } k \to + \infty , } \\ { \displaystyle \frac { 1 6 - \theta ^ { 2 } \varphi ( \theta ) ^ { 2 } \left( 1 - \rho \right) ^ { 2 } } { 6 4 } - \frac { 4 - \theta \varphi ( \theta ) ^ { 2 } \left( 1 - \rho \right) } { 8 \varphi ( \theta ) k } + \mathcal { O } \left( \frac { 1 } { k ^ { 2 } } \right) , } & { \mathrm { a s ~ } k \to - \infty . } \end{array} \right.
$$

The result follows by inspection.

Remark 4.3. The asymptotic behavior of SSVI (4.1) as $| k |$ tends to infinity is

$$
w ( k , \theta _ { t } ) = \frac { ( 1 \pm \rho ) \theta _ { t } } { 2 } \varphi ( \theta _ { t } ) \left| k \right| + { \mathcal O } ( 1 ) , \quad f o r \ a n y \ t > 0 .
$$

We thus observe that the condition $\theta \varphi ( \theta ) \left( 1 + | \rho | \right) \leq 4$ of Theorem $4 . 2$ corresponds to the upper bound $o f 2$ on the asymptotic slope established by Lee $\it { \Omega } \it { / 2 3 } \it { ] }$ and so again, Condition 1 of Theorem 4.2 is necessary.

The following corollary follows directly from Theorems 4.1 and 4.2.

Corollary 4.1. The SSVI surface (4.1) is free of static arbitrage if the following conditions are satisfied:

1. $\partial _ { t } \theta _ { t } \geq 0$ , for all $t > 0$

2. $\begin{array} { r } { 0 \leq \partial _ { \theta } ( \theta \varphi ( \theta ) ) \leq \frac { 1 } { \rho ^ { 2 } } \left( 1 + \sqrt { 1 - \rho ^ { 2 } } \right) \varphi ( \theta ) , \mathrm { ~ } f o r \mathrm { ~ } a l l \mathrm { ~ } \theta > 0 ; } \end{array}$

3. $\theta \varphi ( \theta ) \left( 1 + | \rho | \right) < 4 , f o r \ a l l \ \theta > 0 ;$

4. $\theta \varphi ( \theta ) ^ { 2 } \left( 1 + | \rho | \right) \leq 4$ , for all $\theta > 0$

Remark 4.4. Consider the function $\varphi ( \theta ) = \eta \theta ^ { - \gamma }$ with $\eta > 0$ from Example $4 . 2 ,$ then Condition 2 imposes $\gamma \in \mathsf { ( 0 , 1 ) }$ From Condition 3, such surfaces can be free of static arbitrage only up to some maximum expiry. Take for instance the simple case $\theta _ { t } : = \sigma ^ { 2 } t$ for some $\sigma > 0$ . Then the map $\psi : t \mapsto \theta _ { t } \varphi ( \theta _ { t } ) \left( 1 + | \rho | \right) - 4$ is clearly strictly increasing with $\psi ( 0 ) = - 4$ and $\begin{array} { r } { \operatorname* { l i m } _ { t \to \infty } \psi ( t ) = \infty } \end{array}$ . Therefore there exists $t _ { 0 } ^ { * } > 0$ such that $\psi ( t ) \leq 0$ for $t \leq t _ { 0 } ^ { * }$ . The map $\psi _ { 2 } : t \mapsto \theta _ { t } \varphi ( \theta _ { t } ) ^ { 2 } ( 1 + | \rho | ) - 4$ is

<!-- page: 17 -->

• strictly increasing if $\gamma \in ( 0 , 1 / 2 )$ with $\psi _ { 2 } ( 0 ) = - 4$ and $\operatorname* { l i m } _ { t \infty } \psi ( t ) = + \infty ,$ there exists $t _ { 1 } ^ { * } > 0$ such that $\psi _ { 2 } ( t ) \leq 0$ for $t \leq t _ { 1 } ^ { * }$

• strictly decreasing $i f \gamma \in ( 1 / 2 , 1 )$ with lim $\psi _ { 2 } ( 0 ) = + \infty$ and lim $\psi ( t ) = - 4 ,$ ; there t→0 t→∞ exists $t _ { 1 } ^ { * } > 0$ such that $\psi _ { 2 } ( t ) \leq 0 f o r t \geq t _ { 1 } ^ { * }$

• constant if $\alpha = 1 / 2$ with $\psi _ { 2 } \equiv - 4$

When $\gamma \in ( 0 , 1 / 2 )$ , the surface is guaranteed to be free ofstatic arbitrage only for $t \leq t _ { 0 } ^ { * } \wedge t _ { 1 } ^ { * }$ For $\gamma \in ( 1 / 2 , 1 )$ , this remains true only for $t \in ( 0 , t _ { 0 } ^ { * } ) \cap ( t _ { 1 } ^ { * } , \infty )$ (which may be empty). When $\gamma = 1 / 2$ , static arbitrage cannot occur for $t \leq t _ { 0 } ^ { * }$ . However, the behavior for large θ can be easily modified so as to ensure that the entire surface is free of static arbitrage. For example, the choice

$$
\varphi ( \theta ) = \frac { \eta } { \theta ^ { \gamma } ( 1 + \theta ) ^ { 1 - \gamma } }\tag{4.5}
$$

gives a surface that is completely free of static arbitrage provided that $\eta \left( 1 + | \rho | \right) \leq 2$

Remark 4.5. In the Heston-like parameterization of Example 4.1, note that

$$
\operatorname* { l i m } _ { \theta  + \infty } \theta \varphi ( \theta ) ( 1 + | \rho | ) = \frac { 1 + | \rho | } { \lambda } .
$$

Therefore Condition 3 of Corollary 4.1 imposes $\lambda \ge \left( 1 + | \rho | \right) / 4$

The following model-independent theorem provides a way to expand the class of volatility surfaces that are guaranteed to be free of static arbitrage by adding a suitable timedependent function.

Theorem 4.3. Let $( k , t ) \mapsto w ( k , t )$ be a SSVI volatility surface (4.1) satisfying the conditions of Corollary 4.1 (in particular free of static arbitrage), and $\alpha : \mathbb { R } _ { + } \to \mathbb { R } _ { + }$ a nonnegative and increasing function of time. Then the volatility surface $( k , t ) \mapsto w _ { \alpha } ( k , \theta _ { t } ) : =$ $w ( k , \theta _ { t } ) + \alpha _ { t }$ is also free of static arbitrage.

Proof. Since $\partial _ { t } w _ { \alpha } ( k , \theta _ { t } ) : = \partial _ { t } w ( k , \theta _ { t } ) + \partial _ { t } \alpha _ { t }$ , Lemma 2.1 implies that $w _ { \alpha }$ is free of calendar spread arbitrage if $\partial _ { t } \alpha _ { t } \geq 0$ and $\alpha _ { t } \geq 0$ . We now show that $w _ { \alpha }$ is also free of butterfly arbitrage. For clarity, since butterfly arbitrage does not depend on the time parameter t, we shall use the simplified notation $w ( k ) : = w ( k , \theta _ { t } )$ , and likewise $w _ { \alpha } ( k ) : = w _ { \alpha } ( k , \theta _ { t } )$ Similarly, in view of (2.1), we shall define the map $g _ { \alpha } ( k )$ , where the function w is replaced by $w _ { \alpha } .$ . We consider the case $\rho < 0$ since the case $\rho > 0$ follows by symmetry, and the result is obvious when $\rho = 0$ . Let us consider the function $G _ { \alpha } : \mathbb { R } \mathbb { R }$ defined by

$$
G _ { \alpha } ( k ) : = g ( k ) - g _ { \alpha } ( k ) , \quad \mathrm { f o r ~ a l l ~ } k \in \mathbb { R } ,
$$

and let $k ^ { * } : = - 2 \rho / \varphi ( \theta _ { t } ) > 0$ be the unique solution to the equation $w ^ { \prime } ( k ) = 0$ . We can compute explicitly the following:

$$
G _ { \alpha } ( k ) = \frac { w ^ { \prime } ( k ) } { 4 } \left( \frac { 1 } { w _ { \alpha } ( k ) } - \frac { 1 } { w ( k ) } \right) \left( 4 k + w ^ { \prime } ( k ) - w ^ { \prime } ( k ) k ^ { 2 } \left( \frac { 1 } { w _ { \alpha } ( k ) } + \frac { 1 } { w ( k ) } \right) \right) ,
$$

<!-- page: 18 -->

which implies

$$
\partial _ { \alpha } G _ { \alpha } ( k ) = - \frac { w ^ { \prime } ( k ) } { 4 } \frac { ( w ^ { \prime } ( k ) + 4 k ) w _ { \alpha } ( k ) - 2 k ^ { 2 } w ^ { \prime } ( k ) } { w _ { \alpha } ( k ) ^ { 3 } } .\tag{4.6}
$$

Since $w ^ { \prime } ( 0 ) = \rho \theta _ { t } \varphi ( \theta _ { t } ) < 0$ the equation $w ^ { \prime } ( k ) + 4 k = 0$ has a unique solution $k _ { * } > 0$ , and $w ^ { \prime } ( k ) +$ 4k is strictly positive for any $k > k _ { * }$ and strictly negative when $k < k _ { * }$ . By strict convexity of the function w it also follows that $k _ { * } < k ^ { * }$ . Therefore for any $k \in ( k _ { * } , k ^ { * } )$ the two inequalities $w ^ { \prime } ( k ) < 0$ and $w ^ { \prime } ( k ) + 4 k > 0$ hold, and therefore $\partial _ { \alpha } G _ { \alpha } ( k ) > 0$ . Since by construction $G _ { 0 } ( k ) = 0$ , we therefore conclude that $g ( k ) > g _ { \alpha } ( k )$ for any $k \in ( k _ { * } , k ^ { * } )$ For $k \not \in ( k _ { * } , k ^ { * } )$ , the inequality $g ( k ) < g _ { \alpha } ( k )$ holds as soon as $\partial _ { \alpha } G _ { \alpha } ( k ) < 0$ . Consider first the case $k > k ^ { * }$ . We can rewrite (4.6) as

$$
\partial _ { \alpha } G _ { \alpha } ( k ) = - \frac { w ^ { \prime } ( k ) } { 4 } \frac { 2 k \left[ 2 w _ { \alpha } ( k ) - k w ^ { \prime } ( k ) \right] + w _ { \alpha } ( k ) w ^ { \prime } ( k ) } { w _ { \alpha } ( k ) ^ { 3 } } .
$$

so that it sufices to prove the inequality $2 w _ { \alpha } ( k ) - k w ^ { \prime } ( k ) > 0$ for any $k > k ^ { * }$ . It sufices to prove $\partial _ { \alpha } G _ { \alpha } ( k ) < 0$ for then we have the inequality $g _ { \alpha } ( k ) > g ( k ) \geq 0$ and there is no butterfly arbitrage.

First consider the case $k > k ^ { * }$ , so that $w ^ { \prime } ( k ) > 0$ . Recall that a continuously diferentiable function f is convex on the interval $( a , b )$ if and only if $f ( x ) - f ( y ) \geq f ^ { \prime } ( x ) ( x - y )$ for all $( x , y ) \in ( a , b )$ . Setting $x = k$ and $y = 0$ , we conclude that $2 w _ { \alpha } ( k ) - k w ^ { \prime } ( k ) > 0$ since $w _ { \alpha } ( 0 ) \geq 0$ . It follows that $\partial _ { \alpha } G _ { \alpha } ( k ) < 0$ for any $k > k ^ { * }$

For any $k < 0$ , we always have $w ^ { \prime } ( k ) < 0$ , the inequality $2 w _ { \alpha } ( k ) - k w ^ { \prime } ( k ) > 0$ follows by convexity as above, and hence $\partial _ { \alpha } G _ { \alpha } ( k ) ~ < ~ 0$ for any $k \ < \ 0$ We prove here that $g _ { \alpha } ( k ) \geq g _ { \alpha } ( 0 )$ for all such k. Since we already showed that $g _ { \alpha } ( 0 ) > 0$ , the result follows. From the definition of $g _ { \alpha }$ and (2.1),

$$
\begin{array} { r c l } { { g _ { \alpha } ( k ) - g _ { \alpha } ( 0 ) } } & { { = } } & { { \displaystyle \left( 1 - \frac { k w ^ { \prime } ( k ) } { 2 \left( w ( k ) + \alpha \right) } \right) ^ { 2 } - 1 } } \\ { { } } & { { } } & { { \displaystyle - \frac { w ^ { \prime } ( k ) ^ { 2 } } { 4 } \left( \frac { 1 } { w ( k ) + \alpha } + \frac { 1 } { 4 } \right) + \frac { w ^ { \prime } ( 0 ) ^ { 2 } } { 4 } \left( \frac { 1 } { w ( 0 ) + \alpha } + \frac { 1 } { 4 } \right) } } \\ { { } } & { { } } & { { \displaystyle + \frac { w ^ { \prime \prime } ( k ) } { 2 } - \frac { w ^ { \prime \prime } ( 0 ) } { 2 } . } } \end{array}\tag{4.7}
$$

A straightforward analysis shows that the function $k \mapsto w ^ { \prime \prime } ( k )$ is strictly increasing on the interval $( 0 , k ^ { * } / 2 )$ and strictly decreasing on $( k ^ { * } / 2 , k ^ { * } )$ . The easy computation $w ^ { \prime \prime } ( 0 ) =$ $w ^ { \prime \prime } ( k ^ { * } )$ implies that $w ^ { \prime \prime } ( k ) \geq w ^ { \prime \prime } ( 0 )$ on $( 0 , k ^ { * } )$ . Also, $w ^ { \prime } ( 0 ) ^ { 2 } > w ^ { \prime } ( k ) ^ { 2 }$ on $( 0 , k ^ { * } )$ . Simplifying $( 4 . 7 )$ , it follows that

$$
\begin{array} { r c l } { \displaystyle g _ { \alpha } ( k ) - g _ { \alpha } ( 0 ) } & { \ge } & { \displaystyle \left( 1 - \frac { k w ^ { \prime } ( k ) } { 2 ( w ( k ) + \alpha ) } \right) ^ { 2 } - 1 + \frac { 1 } { 4 } \left( \frac { w ^ { \prime } ( 0 ) ^ { 2 } } { w ( 0 ) + \alpha } - \frac { w ^ { \prime } ( k ) ^ { 2 } } { w ( k ) + \alpha } \right) } \\ & { \ge } & { \displaystyle \frac { 1 } { 4 } \left( \frac { w ^ { \prime } ( 0 ) ^ { 2 } } { w ( 0 ) + \alpha } - \frac { w ^ { \prime } ( k ) ^ { 2 } } { w ( k ) + \alpha } \right) - \frac { k w ^ { \prime } ( k ) } { w ( k ) + \alpha } . } \end{array}
$$

<!-- page: 19 -->

Note that $w ^ { \prime } ( k ) ^ { 2 } \leq w ^ { \prime } ( 0 ) w ^ { \prime } ( k ) \leq w ^ { \prime } ( 0 ) ^ { 2 }$ on the interval $( 0 , k ^ { * } )$ so

$$
g _ { \alpha } ( k ) - g _ { \alpha } ( 0 ) \geq \frac { w ^ { \prime } ( 0 ) w ^ { \prime } ( k ) } { 4 } \left( \frac { 1 } { w ( 0 ) + \alpha } - \frac { 1 } { w ( k ) + \alpha } \right) - \frac { k w ^ { \prime } ( k ) } { w ( k ) + \alpha } .\tag{4.8}
$$

We now prove the following claim: $\begin{array} { r } { k w ( 0 ) - \frac { w ^ { \prime } ( 0 ) } { 4 } [ w ( k ) - w ( 0 ) ] \geq 0 } \end{array}$ for $k \in ( 0 , k ^ { * } )$ . Indeed,

$$
k w ( 0 ) - \frac { w ^ { \prime } ( 0 ) } { 4 } [ w ( k ) - w ( 0 ) ] = \left( 1 - \frac { \rho ^ { 2 } \theta \varphi ^ { 2 } } { 8 } \right) \theta k + \frac { \rho \varphi \theta ^ { 2 } } { 8 } - \frac { \rho \varphi \theta ^ { 2 } } { 8 } \sqrt { \varphi ^ { 2 } k ^ { 2 } + 2 \varphi \rho k + 1 } .
$$

Condition 2 of Theorem 4.2 implies that $\begin{array} { r } { 1 - \frac { \rho ^ { 2 } \theta \varphi ^ { 2 } } { 8 } \ge 0 } \end{array}$ . Then (recall that $\rho \le 0 )$ the right-hand side of the above equality represents an increasing function on $( 0 , k ^ { * } )$ which is equal to zero at the origin, and the claim holds. Then, from (4.8),

$$
\begin{array} { l l l } { \displaystyle g _ { \alpha } ( \boldsymbol { k } ) - g _ { \alpha } ( 0 ) } & { \geq } & { \displaystyle \frac { - w ^ { \prime } ( \boldsymbol { k } ) } { ( w ( 0 ) + \alpha ) ( w ( \boldsymbol { k } ) + \alpha ) } \left\{ \boldsymbol { k } \left( w ( 0 ) + \alpha \right) - \frac { w ^ { \prime } ( 0 ) } { 4 } \left[ w ( \boldsymbol { k } ) - w ( 0 ) \right] \right\} } \\ { \displaystyle } & { \geq } & { 0 . } \end{array}
$$

Remark 4.6. Given a set of expirations $0 < t _ { 1 } < . . . < t _ { n } ( n \geq 1 )$ and at-the-money implied total variances $0 < \theta _ { t _ { 1 } } < . . . < \theta _ { t _ { n } }$ , Corollary 4.1 gives us the freedom to match three features of one smile (level, skew, and curvature say) but only two features of all the other smiles (level and skew say), subject of course to the given smiles being themselves arbitrage-free. Theorem $4 . 3$ may allow us to match an additional feature of each smile through $\alpha _ { t }$

## 5 Numerics and calibration methodology

## 5.1 How to eliminate butterfly arbitrage

In Section 4, we showed how to define a volatility smile that is free of butterfly arbitrage. This smile is completely defined given three observables. The ATM volatility and ATM skew are obvious choices for two of them. The most obvious choice for the third observable in equity markets would be the asymptotic slope for k negative and in FX markets and interest rate markets, perhaps the ATM curvature of the smile might be more appropriate.

In view of Lemma 4.1, supposing we choose to fix the SVI-JW parameters $v _ { t } , \psi _ { t }$ and $p _ { t }$ of a given SVI smile, we may guarantee a smile with no butterfly arbitrage by choosing the remaining parameters $c _ { t } ^ { \prime }$ and $\widetilde { v } _ { t } ^ { \prime }$ as

$$
c _ { t } ^ { \prime } = p _ { t } + 2 \psi _ { t } , \quad \mathrm { a n d } \quad \widetilde { v } _ { t } ^ { \prime } = v _ { t } \frac { 4 p _ { t } c _ { t } ^ { \prime } } { \left( p _ { t } + c _ { t } ^ { \prime } \right) ^ { 2 } } .
$$

In other words, given a smile defined in terms of its SVI-JW parameters, we are guaranteed to be able to eliminate butterfly arbitrage by changing the call wing $c _ { t }$ and the minimum

<!-- page: 20 -->

variance $\widetilde { v } _ { t } .$ , both parameters that are hard to calibrate with available quotes in equity options markets.

Example 5.1. Consider again the arbitrageable smile from Example 3.1. The corresponding SVI-JW parameters read

$$
\left( v _ { t } , \psi _ { t } , p _ { t } , c _ { t } , \widetilde { v } _ { t } \right) = \left( 0 . 0 1 7 4 2 6 2 5 , - 0 . 1 7 5 2 1 1 1 , 0 . 6 9 9 7 3 8 1 , 1 . 3 1 6 7 9 8 , 0 . 0 1 1 6 2 4 9 \right) .
$$

We know then that choosing $( c _ { t } , \widetilde { v } _ { t } ) = ( c _ { t } ^ { o } , \widetilde { v } _ { t } ^ { o } ) : = ( 0 . 3 4 9 3 1 5 8 , 0 . 0 1 5 4 8 1 8 2 )$ gives a smile free of butterfly arbitrage. It follows by continuity of the parameterization in all of its parameters, that there must exist some pair of parameters $( c _ { t } ^ { * } , \widetilde { v } _ { t } ^ { * } )$ with $c _ { t } ^ { \ast } \in \left( c _ { t } ^ { o } , c _ { t } \right)$ and $\widetilde { v } _ { t } ^ { * } \ \in \ ( \widetilde { v } _ { t } , v _ { t } ^ { o } )$ such that the new smile is free of butterfly arbitrage and is as close as possible to the original one in some sense. In this particular case, choosing the objective function as the sum of squared option price diferences plus a large penalty for butterfly arbitrage, we arrive at the following “optimal” choices of the call wing and minimum variance parameters that still ensure no butterfly arbitrage:

$$
\left( c _ { t } ^ { \ast } , \widetilde { v } _ { t } ^ { \ast } \right) = \left( 0 . 8 5 6 4 7 6 3 , 0 . 0 1 1 6 2 4 9 \right) .
$$

Note that the optimizer has $l e f t \widetilde { v } _ { t }$ unchanged but has decreased the call wing. The resulting smiles and plots of the function g are shown in Figure 2.

![](assets/figures/2014-gatheral-jacquier-arbitrage-free-svi-p0020-block-0007-e53f517e6b2ed339.jpg)

![Figure 2: Plots of the total variance smile (left) and the function g defined in (2.1) (right), using the parameters (3.8). The graphs corresponding to the original Vogt parameters is solid, to the guaranteed butterfly-arbitrage-free parameters dashed, and to the “optimal” choice of parameters dotted.](assets/figures/2014-gatheral-jacquier-arbitrage-free-svi-p0020-block-0008-866b593c4103f09d.jpg)

Remark 5.1. The additional flexibility potentially aforded to us through the parameter $\alpha _ { t }$ of Theorem $4 . 3$ sadly does not help us with the Vogt smile of Example 5.1. For $\alpha _ { t }$ to help, we must have $\alpha _ { t } > 0 ,$ it is straightforward to verify that this translates to the condition $v _ { t } \left( 1 - \rho ^ { 2 } \right) < \tilde { v } _ { t }$ which is violated in the Vogt case.

<!-- page: 21 -->

## 5.2 Calibration of SVI parameters to implied volatility data

There are many possible ways of defining an objective function, the minimization of which would permit us to calibrate SVI to observed implied volatilities. Whichever calibration strategy we choose, we need an eficient fitting algorithm and a good choice of initial guess. The approach we will present here involves taking a square-root fit as the initial guess. We then fit SVI slice-by-slice with a heavy penalty for calendar spread arbitrage (i.e. crossed lines on a total variance plot). Consider two SVI slices with parameters $\chi _ { 1 }$ and $\chi _ { 2 }$ where $t _ { 2 } > t _ { 1 }$ . We first compute the points $k _ { i } \ ( i = 1 , \ldots , n )$ with $n \leq 4$ at which the slices cross, sorting them in increasing order. If $n > 0$ , we define the points $\widetilde { k } _ { i }$ as

$$
\begin{array} { r c l } { { \widetilde k _ { 1 } } } & { { : = } } & { { k _ { 1 } - 1 , } } \\ { { } } & { { } } & { { } } \\ { { \widetilde k _ { i } } } & { { : = } } & { { \displaystyle \frac { 1 } { 2 } \left( k _ { i - 1 } + k _ { i } \right) , \quad \mathrm { i f } \ 2 \leq i \leq n , } } \\ { { } } & { { } } & { { } } \\ { { \widetilde k _ { n + 1 } } } & { { : = } } & { { k _ { n } + 1 . } } \end{array}
$$

For each of the $n + 1$ points $\widetilde { k } _ { i }$ , we compute the amounts $c _ { i }$ by which the slices cross:

$$
c _ { i } = \operatorname* { m a x } \left[ 0 , w ( \widetilde { k } _ { i } ; \chi _ { 1 } ) - w ( \widetilde { k } _ { i } ; \chi _ { 2 } ) \right] .
$$

Definition 5.1. The crossedness of two SVI slices is defined as the maximum of the $c _ { i }$ $( i = 1 , \ldots , n ) . \ I f n = 0$ , the crossedness is null.

## An example SVI calibration recipe

• Given mid implied volatilities $\sigma _ { i j } = \sigma _ { \mathrm { B S } } ( k _ { i } , t _ { j } )$ , compute mid option prices using the Black-Scholes formula.

• Fit the square-root SVI surface by minimizing sum of squared distances between the fitted prices and the mid option prices. This is now the initial guess.

• Starting with the square-root SVI initial guess, change SVI parameters slice-by slice so as to minimize the sum of squared distances between the fitted prices and the mid option prices with a big penalty for crossing either the previous slice or the next slice (as quantified by the crossedness from Definition 5.1).

There are obviously many possible variations on this recipe. The objective function may be changed and when finally working to optimize the fit slice-by-slice, one can work from the shortest expiration to the longest expiration or in the reverse order. In practice, working forward or in reverse seems to make little diference. Changing the objective function on the other hand will make some diference especially for very short expirations.

## 5.3 Interpolation and extrapolation of calibrated slices

Suppose we follow the above recipe above to fit SVI to options with a discrete set of expiries. In particular, each of the resulting SVI smiles will be free of butterfly arbitrage.

<!-- page: 22 -->

It’s not immediately obvious that we can interpolate these smiles in such a way as to ensure the absence of static arbitrage in the interpolated surface. The following lemma shows that it is possible to achieve this.

Lemma 5.1. Given two volatility smiles $w ( k , t _ { 1 } )$ and $w ( k , t _ { 2 } )$ with $t _ { 1 } < t _ { 2 }$ where the two smiles are free of butterfly arbitrage and such that w $( k , \tau _ { 2 } ) \geq w ( k , \tau _ { 1 } )$ for all k, there exists an interpolation such that the interpolated volatility surface is free of static arbitrage for $t _ { 1 } < t < t _ { 2 }$

Proof. Given the two smiles $w ( k , t _ { 1 } )$ and $w ( k , t _ { 2 } )$ , we may compute the (undiscounted) prices $C ( F _ { i } , K _ { i } , t _ { i } ) = : C _ { i }$ of European calls with expirations $t _ { i } \ ( i = 1 , 2 )$ using the Black-Scholes formula. In particular, since the two smiles are free of butterfly arbitrage,

$$
\frac { \partial ^ { 2 } C _ { i } } { \partial K ^ { 2 } } \ge 0 , \mathrm { f o r } \ i = 1 , 2 .
$$

Consider any monotonic interpolation $\theta _ { t }$ of the at-the-money implied total variance $w ( 0 , t )$ Let $K _ { i } = F _ { i } \mathrm { e } ^ { k }$ and $K _ { t } = F _ { t } \mathrm { e } ^ { k }$ . Then for any $t _ { 1 } < t < t _ { 2 }$ , define the price $C _ { t } = C ( F _ { t } , K _ { t } , t )$ of a European call option to be

$$
\frac { C _ { t } } { K _ { t } } = \alpha _ { t } \frac { C _ { 1 } } { K _ { 1 } } + \left( 1 - \alpha _ { t } \right) \frac { C _ { 2 } } { K _ { 2 } } ,\tag{5.1}
$$

where for any $t \in ( t _ { 1 } , t _ { 2 } )$ , we define

$$
\alpha _ { t } : = \frac { \sqrt { \theta _ { t _ { 2 } } } - \sqrt { \theta _ { t } } } { \sqrt { \theta _ { t _ { 2 } } } - \sqrt { \theta _ { t _ { 1 } } } } \in \left[ 0 , 1 \right] .\tag{5.2}
$$

By construction, for fixed k, the inequality

$$
\frac { \partial } { { \partial \tau } } \frac { { C _ { t } } } { { K _ { t } } } \geq 0
$$

holds so that there is no calendar spread arbitrage. Also, because of the square-roots in the definition (5.2), the at-the-money interpolated option price will be almost perfectly consistent with the chosen implied total variance interpolation $\theta _ { t }$ . Moreover, if the two smiles $w ( k , t _ { 1 } )$ and $w ( k , t _ { 2 } )$ are free of butterfly arbitrage, we have $\partial _ { K , K } C ( k , t ) \geq 0$ . To see this, first note that because all the options have the same moneyness, the identity (5.1) is equivalent to

$$
{ \frac { C _ { t } } { F _ { t } } } = \alpha _ { t } { \frac { C _ { 1 } } { F _ { 1 } } } + \left( 1 - \alpha _ { t } \right) { \frac { C _ { 2 } } { F _ { 2 } } } .\tag{5.3}
$$

Then note that the ratio $C ( F , K , t ) / F$ is a function of F and K only through the logmoneyness k. Also, for $K = K _ { t } , K _ { 1 } , K _ { 2 }$ , we have

$$
K ^ { 2 } \frac { \partial ^ { 2 } f } { \partial K ^ { 2 } } = \frac { \partial ^ { 2 } f } { \partial k ^ { 2 } } - \frac { \partial f } { \partial k } .
$$

<!-- page: 23 -->

Applying this to (5.3), we obtain

$$
\frac { K _ { \tau } ^ { 2 } } { F _ { t } } \frac { \partial ^ { 2 } C _ { t } } { \partial K _ { t } ^ { 2 } } = \alpha _ { t } \frac { K _ { 1 } ^ { 2 } } { F _ { 1 } } \frac { \partial ^ { 2 } C _ { 1 } } { \partial K _ { 1 } ^ { 2 } } + \left( 1 - \alpha _ { t } \right) \frac { K _ { 2 } ^ { 2 } } { F _ { 2 } } \frac { \partial ^ { 2 } C _ { 2 } } { \partial K ^ { 2 } } .
$$

All the terms on the rhs are non-negative, so the lhs must also be non-negative. We conclude that there is no butterfly arbitrage in the interpolated slice and thus that there is no static arbitrage. The interpolated volatility surface may be retrieved by inversion of the Black-Scholes formula. □

We could conceive of a myriad of algorithms for extrapolating the volatility surface. For example, one way to extrapolate a given set of $n \geq 1$ (arbitrage-free) volatility smiles with expirations $0 < t _ { 1 } < . . . < t _ { n }$ would be as follows: At time $t _ { 0 } = 0$ , the value of a call option is just the intrinsic value. We may then interpolate between $t _ { 0 }$ and $t _ { 1 }$ using the algorithm presented in the proof of Lemma 5.1, thereby guaranteeing no static arbitrage. For extrapolation beyond the final slice, we suggest to first recalibrate the final slice using the SSVI form (4.1). Then fix a monotonic increasing extrapolation of $\theta _ { t }$ (asymptotically linear in time would seem to be reasonable) and extrapolate the smile for $t > t _ { n }$ according to

$$
w ( k , \theta _ { t } ) = w ( k , \theta _ { t _ { n } } ) + \theta _ { t } - \theta _ { t _ { n } } ,
$$

which is free of static arbitrage if $w ( k , \theta _ { t _ { n } } )$ is free of butterfly arbitrage by Theorem 4.3.

## 5.4 A calibration example

We take SPX option quotes as of 3pm on 15-Sep-2011 (the day before triple-witching) and compute implied volatilities for all 14 expirations. The result of fitting square-root SVI is shown in Figure 3. The result of fitting SVI following the recipe provided in Section 5.2 is shown in Figure 4. With the sole exception of the first expiration (options expiring at the market open on the following morning), the fit quality is almost perfect.

<!-- page: 24 -->

![Figure 3: Red dots are bid implied volatilities; blue dots are ofered implied volatilities; the orange solid line is the square-root SVI fit](assets/figures/2014-gatheral-jacquier-arbitrage-free-svi-p0024-block-0001-315321e83f451c6b.jpg)

## 6 Summary and conclusion

We have found and described a large class of arbitrage-free SVI volatility surfaces with a simple closed-form representation. Taking advantage of the existence of such surfaces, we showed how to eliminate both calendar spread and butterfly arbitrages when calibrating SVI to implied volatility data. We have also demonstrated the high quality of typical SVI fits with a numerical example using recent SPX options data. The potential applications of this work to modelling the dynamics of the implied volatility surface are left for future research.

## Acknowledgments

The first author is very grateful to his former colleagues at Bank of America Merrill Lynch for their work on SVI and its implementation, in particular Chrif Youssfi and Peter Friz. We also thank Richard Holowczak of the Subotnick Financial Services Center at Baruch College for supplying the SPX options data, Andrew Chang of the Baruch MFE program for helping with the data analysis, Julien Guyon and the participants of Global Derivatives, Barcelona 2012 for their feedback and comments. We are very grateful to the anonymous referees for their helpful comments and suggestions, and in particular to one of the referees who led us to tighten our results and correct an error in one proof.

<!-- page: 25 -->

![Figure 4: Red dots are bid implied volatilities; blue dots are ofered implied volatilities; the orange solid line is the SVI fit following recipe of Section 5.2](assets/figures/2014-gatheral-jacquier-arbitrage-free-svi-p0025-block-0001-a12a60a7484c23f5.jpg)

## References

[1] Andreasen J., Huge B. Volatility interpolation, Risk, 86–89, March 2011. [2] Breeden, D.T., Litzenberger, R.H. Prices of state-contingent claims implicit in option prices, The Journal of Business 51(4): 621-651, 1978. [3] Cardano, G., Ars magna or The Rules of Algebra, Dover, 1545. [4] Carr, P., Lee, R. Put-call symmetry: Extensions and applications, Mathematical Finance 19(4): 523–560, 2009. [5] Carr, P., Madan, D. A note on suficient conditions for no arbitrage, Finance Research Letters 2: 125–130, 2005. [6] Carr, P., Wu, L. A new simple approach for for constructing implied volatility surfaces, Preprint available at SSRN, 2010. [7] Clark, P.K. A subordinated stochastic process model with finite variance for speculative prices, Econometrica 41(1): 135–155, 1973. [8] Cox, A., Hobson, D. Local Martingales, Bubbles and Option Prices, Finance and Stochastics 9(4): 477–492, 2005.

<!-- page: 26 -->

[9] Cousot, L. Conditions on option prices for absence of arbitrage and exact calibration, Journal of Banking and Finance 31(11): 3377–3397, 2007. [10] De Marco, S., Martini, C. The Term Structure of Implied Volatility in Symmetric Models with Applications to Heston, IJTAF 15(4), 2012. [11] Fengler, M. Arbitrage-free smoothing of the implied volatility surface, Quantitative Finance 9(4): 417–428, 2009. [12] F¨ollmer, H., Schied, A. Stochastic Finance: An Introduction in Discrete Time, de Gruyter, 2002. [13] Gatheral, J., A parsimonious arbitrage-free implied volatility parameterization with application to the valuation of volatility derivatives, Presentation at Global Derivatives, 2004. [14] Gatheral, J., The Volatility Surface: A Practitioner’s Guide, Wiley Finance, 2006. [15] Gatheral, J., Jacquier, A., Convergence of Heston to SVI, Quantitative Finance 11(8): 1129–1132, 2011. [16] Glaser, J., Heider, P., Arbitrage-free approximation of call price surfaces and input data risk, Quantitative Finance 12(1): 61–73, 2012. [17] Harrison, J.M., Pliska, S.R., Martingales and stochastic integrals in the theory of continuous trading, Stochastic Processes and Applications 11: 251–260, 1981. [18] Harrison, J.M., Kreps, D.M., Martingales and arbitrage in multiperiod securities markets Journal of Economic Theory 20(3): 381–408, 1979. [19] Hobson, D. Comparison results for stochastic volatility models via coupling. Finance and Stochastics 14 (1): 129-152, 2010. [20] J¨ackel, P., Kahl, C. Hyp hyp hooray, Wilmott Magazine 70–81, March 2008. [21] Kahal´e, N. An arbitrage-free interpolation of volatilities, Risk 17:102–106, 2004. [22] Karatzas, I., Shreve, S. Brownian motion and stochastic calculus. Springer-Verlag, 1991. [23] Lee, R., The moment formula for implied volatility at extreme strikes, Mathematical Finance 14(3): 469–480, 2004. [24] Rogers, C. Tehranchi, M.. Can the implied volatility surface move by parallel shift? Finance & Stochastics 14 (2): 235-248, 2010. [25] Roper, M.P.V., Implied Volatility: General Properties and Asymptotics, PhD thesis, The University of New South Wales, 2009.

<!-- page: 27 -->

[26] Stineman, R. W., A consistently well-behaved method of interpolation, Creative Computing 54–57, 1980. [27] Zeliade Systems, Quasi-explicit calibration of Gatheral’s SVI model, Zeliade white paper, 2009.
