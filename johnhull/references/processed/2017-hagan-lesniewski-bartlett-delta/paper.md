# 2017-hagan-lesniewski-bartlett-delta

<!-- page: 1 -->

## Bartlett’s delta in the SABR model

Patrick S. Hagan

Gorilla Science

PatHagan@GorillaSci.Com

Andrew Lesniewski

Department of Mathematics

Baruch College

One Bernard Baruch Way

New York, NY 10010

USA

First draft: April 14, 2016

This draft: May 6, 2020

arXiv:1704.03110v2 [q-fin.CP] 5 May 2020

<!-- page: 2 -->

## Abstract

The presence of stochastic volatility in an option model impacts the values of the hedge ratios (the “greeks”), and in particular the option delta. In the context of the SABR model, the greeks were calculated in [4] based on the asymptotic expression for the implied volatility derived there. In [2], the option delta of [4] was modified to take into account the effects of the correlation between the dynamics of the forward and the stochastic volatility. It was empirically observed there that the modified delta (“Bartlett’s delta”) provides a more accurate and robust hedging strategy than the original SABR delta. In this paper we refine the analysis of hedging strategies carried out in [2]. In particular, we provide a justification of the empirical observations regarding the robustness of the modified delta. This is done by means of an asymptotic analysis of the explicit expression for the implied volatility derived in [4]. In particular, we show that the modified option delta is practically insensitive to the choice of the the CEV parameter β.

<!-- page: 3 -->

## 1 Introduction

The key requirement of an option model, in addition to its utility as an accurate pricing tool, is its ability to produce reliable risk metrics. This allows the portfolio manager or market maker to confidently put on appropriate hedges on his options positions in a way that reflects his view or mandate.

The presence of stochastic volatility in an option model impacts the values of the the option greeks, and in particular the option delta. In this note we are concerned with hedging under the SABR model of volatility smile ([4], [7], [5]). Originally, the values of the greeks under the SABR model were calculated in [4] based on the asymptotic expression for the implied volatility. In $[ 2 ] ,$ , the option delta proposed in [4] was modified to take into account the effects of the correlation between the dynamics of the forward and the stochastic volatility. It was empirically observed there that the modified delta provides a more accurate and robust hedging strategy than the original SABR delta.

The results described below are a refinement of the work presented in [2]. The SABR model’s specification requires four parameters $\sigma , \alpha , \beta , \rho ,$ , whose values are calibrated to options market prices. According to the prevailing market practice, one of these parameters, the CEV exponent $\beta$ is usually set to a pre-specified value, while the remaining three parameters are optimized. This practice is justified by the fact that there is a degree of redundancy between the CEV exponent $\beta$ and the correlation parameter $\rho$ in the SABR parameterization of the smile curve. While this choice introduces a higher degree of stability of the model parameters, it brings up the question whether the resulting hedges are equally robust, i.e. whether the choice of $\beta$ made by the portfolio manager has a significant impact on the hedging strategy.

It was argued in [2] that the modified delta $\Delta ^ { \mathrm { m o d } }$ introduced there leads to more robust hedges than the classic SABR delta [4], namely, across a large range of strikes, it is nearly independent of the choice of $\beta .$ . This claim was supported there by empirical and numerical arguments, see also [1], [5], and [8]. The purpose of this note is to provide a theoretical justification of this claim. This is done by means of an asymptotic analysis of the explicit expression for the implied volatility derived in [4]. Furthermore, we show here that the modified delta of an at the money option is exactly independent of the choice of $\beta .$

The robustness of $\Delta ^ { \mathrm { m o d } }$ is of direct and measurable practical significance. Proper hedging allows the portfolio manager or market maker better implement his views, which may have an impact on his P&L. Accurate hedge ratios allow for reliable portfolio return attribution, which facilitates his communication with the management, clients, and auditors. Also, from the perspective of regulatory requirements and model risk management, the advantage of the modified SABR delta is clear. It provides a robust option delta, which is insensitive to possible model misspecification, and it thus is a model risk mitigant.

We consider a European call or put struck at $K$ and expiring in τ years from the current time, and let $F$ denote the current value of the underlying forward. The implied volatility curve is a function $\sigma ^ { \mathrm { i m p } } =$ $\sigma ^ { \operatorname { i m p } } ( \tau , F , K , \sigma )$ such that when combined with the Black-Scholes formula, it yields (close approximations to) the market option prices. Two market observable quantities are of particular interest to option traders: the at the money implied volatility,

$$
\begin{array} { r } { \sigma ^ { \mathrm { A T M } } = \sigma ^ { \mathrm { i m p } } ( \tau , F , F , \sigma ) , } \end{array}\tag{1}
$$

and the skew,

$$
\eta = \frac { \partial \sigma ^ { \mathrm { i m p } } ( \tau , F , K , \sigma ) } { \partial K } \Big | _ { K = F } .\tag{2}
$$

The latter is the slope of the volatility curve calculated at the money. These two quantities are model independent, and can be directly inferred from option prices. Any reasonable volatility smile model, regardless of its specification, can be calibrated so that these two quantities match the market values sufficiently closely.

Our main results is that, for each strike K, the modified SABR delta $\Delta ^ { \mathrm { m o d } }$ has approximately the following structure:

$$
\Delta ^ { \mathrm { m o d } } = \Delta ^ { \mathrm { B l a c k - S c h o l e s } } + \mathrm { V e g a } ^ { \mathrm { B l a c k - S c h o l e s } } \times \eta .\tag{3}
$$

In other words, other than the standard Black-Scholes greeks calculated for strike $K ,$ the modified SABR delta does not involve any details of the smile model specification. In contrast, the standard SABR delta has the structure

$$
\Delta = \Delta ^ { \mathrm { B l a c k - S c h o l e s } } + \mathrm { V e g a ^ { \mathrm { B l a c k - S c h o l e s } } } \times ( \eta + \mathrm { m o d e l ~ d e p e n d e n t ~ t e r m } ) .\tag{4}
$$

<!-- page: 4 -->

The last term in the expression above is responsible for potential mishedging in case of model miscalibration discussed in [2].

## 2 The SABR model

The dynamics of the SABR model of option implied volatility is specified in terms of two state variables: the forward $F _ { t }$ and the instantaneous volatility $\sigma _ { t }$ . Explicitly, the dynamics is given by the system of stochastic differential equations:

$$
\begin{array} { l } { { d F _ { t } = \sigma _ { t } C ( F _ { t } ) d W _ { t } , } } \\ { { d \sigma _ { t } = \alpha \sigma _ { t } d Z _ { t } , } } \end{array}\tag{5}
$$

where $W _ { t }$ and $Z _ { t }$ are two Brownian motions with

$$
d W _ { t } d Z _ { t } = \rho d t .\tag{6}
$$

The positive function $C ( F )$ determines the backbone of the volatility smile, and is usually assumed to be of the CEV form

$$
C ( F ) = F ^ { \beta } ,\tag{7}
$$

where $\beta \leq 1$ is the CEV parameter<sup>1</sup>. This will be our default choice in the following.

The normal implied volatility in the SABR model is given by the following asymptotic expression [4] in the (small) parameter $\varepsilon = \alpha ^ { 2 } \tau$

$$
\sigma ^ { \mathrm { i m p } } = \alpha \frac { F - K } { D ( \zeta ) } \Big \{ 1 + \Gamma \varepsilon + O ( \varepsilon ^ { 2 } ) \Big \} ,\tag{8}
$$

where $F$ denotes here the currently observed value of the forward. The distance function $D ( \zeta )$ entering the formula above is given by

$$
D ( \zeta ) = \log \Big ( \frac { I ( \zeta ) + \zeta - \rho } { 1 - \rho } \Big ) ,\tag{9}
$$

where

$$
\begin{array} { r } { I ( \zeta ) = \sqrt { 1 - 2 \rho \zeta + \zeta ^ { 2 } } , } \end{array}\tag{10}
$$

and where

$$
\begin{array} { l } { { \displaystyle \zeta = \frac { \alpha } { \sigma } \int _ { K } ^ { F } \frac { d x } { C ( x ) } } } \\ { { \displaystyle = \frac { \alpha } { \sigma } \frac { F ^ { 1 - \beta } - K ^ { 1 - \beta } } { 1 - \beta } . } } \end{array}\tag{11}
$$

The parameter $\sigma$ denotes the currently observed value of the instantaneous volatility.

Various forms of the first order correction Γ have been derived in the literature, see [6] for discussion and recent results. The original version [4] is explicitly given by

$$
\Gamma = \frac { 2 \gamma _ { 2 } - \gamma _ { 1 } ^ { 2 } } { 2 4 } \left( \frac { \sigma C ( F _ { \mathrm { m i d } } ) } { \alpha } \right) ^ { 2 } + \frac { \rho \gamma _ { 1 } } { 4 } \frac { \sigma C ( F _ { \mathrm { m i d } } ) } { \alpha } + \frac { 2 - 3 \rho ^ { 2 } } { 2 4 } ,\tag{12}
$$

where

$$
\begin{array} { c } { \gamma _ { 1 } = \displaystyle \frac { C ^ { \prime } ( F _ { \mathrm { m i d } } ) } { C ( F _ { \mathrm { m i d } } ) } } \\ { = \displaystyle \frac { \beta } { F _ { \mathrm { m i d } } } \ , } \end{array}\tag{13}
$$

<sup>1</sup>In order to handle negative forward rates in interest rate markets, some practitioners choose C(F) = (F + θ)<sup>β</sup>, with θ > 0.

<!-- page: 5 -->

and

$$
\begin{array} { c } { { \gamma _ { 2 } = \displaystyle \frac { C ^ { \prime \prime } ( F _ { \mathrm { m i d } } ) } { C ( F _ { \mathrm { m i d } } ) } } } \\ { { = \displaystyle - \frac { \beta ( 1 - \beta ) } { F _ { \mathrm { m i d } } ^ { 2 } } . } } \end{array}\tag{14}
$$

The value $F _ { \mathrm { m i d } }$ denotes a conveniently chosen midpoint between $F$ and K (such as the arithmetic average $( F + K ) / 2 )$

It follows from (8) that the at the money volatility in the SABR model is given by

$$
\begin{array} { c } { { \sigma ^ { \mathrm { A T M } } = \sigma C ( F ) + { \cal O } ( \varepsilon ) } } \\ { { = \sigma F ^ { \beta } + { \cal O } ( \varepsilon ) , } } \end{array}\tag{15}
$$

while the skew is

$$
\begin{array} { c } { { \eta = \sigma C ^ { \prime } ( F ) + O ( \varepsilon ) } } \\ { { { } } } \\ { { = \beta \sigma F ^ { \beta - 1 } + O ( \varepsilon ) . } } \end{array}\tag{16}
$$

## 3 SABR greeks

In this section we derive explicit expressions for the greeks in the SABR model, and in particular we obtain the modified delta and vega of [2]. To focus attention we use the normal Black-Scholes model as the basis for option pricing, and assume that the discounting interest rate is zero. We let $T$ denote the date on which the option expires and denote by $\tau = T - t$ the time to expiration.

Let $\boldsymbol { B }$ denote the standard Black-Scholes pricing function in the normal model, i.e.

$$
\mathcal { B } ( \tau , F , K , \sigma ) = \left\{ \begin{array} { l l } { \sigma \sqrt { \tau } \big ( d _ { + } N ( d _ { + } ) + N ^ { \prime } ( d _ { + } ) \big ) , } & { \quad \mathrm { ~ f o r ~ a ~ c a l l ~ o p t i o n } , } \\ { \sigma \sqrt { \tau } \big ( d _ { - } N ( d _ { - } ) + N ^ { \prime } ( d _ { - } ) \big ) , } & { \quad \mathrm { ~ f o r ~ a ~ p u t ~ o p t i o n } , } \end{array} \right.\tag{17}
$$

where $N ( x )$ denotes the cumulative normal distribution, and where

$$
d _ { \pm } = \pm \frac { F - K } { \sigma \sqrt { \tau } } .\tag{18}
$$

Then the current time t price $P _ { t }$ of an option expiring at time $T$ under the SABR model is then given by

$$
P _ { t } = \mathcal { B } ( \tau , F _ { t } , K , \sigma ^ { \mathrm { i m p } } ( \tau , F _ { t } , K , \sigma _ { t } ) ) ,\tag{19}
$$

where $\sigma ^ { \mathrm { i m p } }$ is given by (8). We should emphasize that this expression is only an approximation to the true SABR option price, to the degree to which the asymptotic implied formula (8) represents an accurate approximation to the true, analytically unknown expression for the SABR implied volatility (see [5] for an extensive discussion).

We decompose the Brownian motion $Z _ { t }$ into $W _ { t }$ and a Brownian motion $W _ { t } ^ { \perp }$ , independent of $W _ { t } \colon Z _ { t } =$ $\rho W _ { t } + \sqrt { 1 - \rho ^ { 2 } } W _ { t } ^ { \perp }$ . Then, dσ can be written as a sum of $\rho \alpha / C ( F _ { t } ) d F _ { t }$ and a contribution $d \sigma _ { t } ^ { \perp }$ uncorrelated with $d F _ { t }$ , namely $d \sigma _ { t } ^ { \perp } = \alpha \sigma _ { t } d W _ { t } ^ { \perp }$ . From Ito’s lemma we obtain:

$$
\begin{array} { l } { \displaystyle d \sigma _ { t } ^ { \mathrm { i m p } } = - \frac { \partial \sigma ^ { \mathrm { i m p } } } { \partial \tau } d t + \Big ( \frac { \partial \sigma ^ { \mathrm { i m p } } } { \partial F } + \frac { \partial \sigma ^ { \mathrm { i m p } } } { \partial \sigma } \frac { \rho \alpha } { C ( F _ { t } ) } \Big ) d F _ { t } + \frac { \partial \sigma ^ { \mathrm { i m p } } } { \partial \sigma } d \sigma _ { t } ^ { \bot } } \\ { \displaystyle + \frac { 1 } { 2 } \sigma _ { t } ^ { 2 } \Big ( C ( F _ { t } ) ^ { 2 } \frac { \partial ^ { 2 } \sigma ^ { \mathrm { i m p } } } { \partial ^ { 2 } F } + 2 \rho C ( F _ { t } ) \frac { \partial ^ { 2 } \sigma ^ { \mathrm { i m p } } } { \partial F \partial \sigma } + \alpha ^ { 2 } \frac { \partial ^ { 2 } \sigma ^ { \mathrm { i m p } } } { \partial ^ { 2 } \sigma } \Big ) d t . } \end{array}
$$

This yields the following risk decomposition:

$$
d P _ { t } = \Big \{ - \Theta _ { t } + \frac { 1 } { 2 } \sigma _ { t } ^ { 2 } \big ( C ( F _ { t } ) ^ { 2 } \Gamma _ { t } + 2 C ( F _ { t } ) \mathrm { V a n n a } _ { t } + \alpha ^ { 2 } \mathrm { V o l g a } _ { t } \big ) \Big \} d t + \Delta _ { t } ^ { \mathrm { m o d } } d F _ { t } + \mathrm { V e g a } _ { t } d \sigma _ { t } ^ { \perp } ,\tag{20}
$$

<!-- page: 6 -->

where the first and second order greeks are defined as follows:

$$
\Delta _ { t } ^ { \mathrm { m o d } } = \frac { \partial \mathcal { B } } { \partial \boldsymbol { F } } + \frac { \partial \mathcal { B } } { \partial \sigma } \Big ( \frac { \partial \sigma ^ { \mathrm { i m p } } } { \partial \boldsymbol { F } } + \frac { \partial \sigma ^ { \mathrm { i m p } } } { \partial \sigma } \frac { \rho \alpha } { C ( F _ { t } ) } \Big )\tag{21}
$$

is the modified SABR delta,

$$
\mathrm { \ V e g a } _ { t } = \frac { \partial \boldsymbol { B } } { \partial \sigma } \frac { \partial \sigma ^ { \mathrm { i m p } } } { \partial \sigma }\tag{22}
$$

is the SABR vega,

$$
\Theta _ { t } = \frac { \partial \mathcal { B } } { \partial \tau } + \frac { \partial \mathcal { B } } { \partial \sigma } \frac { \partial \sigma ^ { \mathrm { i m p } } } { \partial \tau }\tag{23}
$$

is the SABR time decay,

$$
\Gamma _ { t } = \frac { \partial ^ { 2 } B } { \partial ^ { 2 } F } + \frac { \partial B } { \partial \sigma } \frac { \partial ^ { 2 } \sigma ^ { \mathrm { i m p } } } { \partial F ^ { 2 } }\tag{24}
$$

is the SABR gamma,

$$
\mathrm {  ~ \ V a n n a } _ { t } = \frac { \partial ^ { 2 } \cal B } { \partial { \cal F } \partial \sigma } + \frac { \partial \cal B } { \partial \sigma } \frac { \partial ^ { 2 } \sigma ^ { \mathrm { i m p } } } { \partial { \cal F } \partial \sigma }\tag{25}
$$

is the SABR vanna, and

$$
\mathrm { \ V o l g a } _ { t } = \frac { \partial ^ { 2 } \mathcal { B } } { \partial ^ { 2 } \sigma } + \frac { \partial \mathcal { B } } { \partial \sigma } \frac { \partial ^ { 2 } \sigma ^ { \mathrm { i m p } } } { \partial \sigma ^ { 2 } }\tag{26}
$$

is the SABR volga. Formula (20) represents a risk decomposition of an option in terms of independent risk factors dF and $d \sigma ^ { \perp }$ , time decay, and second order greeks.

Alternatively, we can represent $W _ { t }$ in terms of $Z _ { t }$ and its independent complement $Z _ { t } ^ { \perp }$ as $W _ { t } = \rho Z _ { t }$ + $\sqrt { 1 - \rho ^ { 2 } } d Z _ { t } ^ { \perp }$ , and arrive at the following risk decomposition:

$$
d P _ { t } = \Big \{ - \Theta _ { t } + \frac { 1 } { 2 } \sigma _ { t } ^ { 2 } \big ( C ( F _ { t } ) ^ { 2 } \Gamma _ { t } + 2 C ( F _ { t } ) \mathrm { V a n n a } _ { t } + \alpha ^ { 2 } \mathrm { V o l g a } _ { t } \big ) \Big \} d t + \Delta _ { t } d F _ { t } ^ { \perp } + \mathrm { V e g a } _ { t } ^ { \mathrm { m o d } } d \sigma _ { t } .\tag{27}
$$

Here, the meaning of the greeks is as follows:

$$
\Delta _ { t } = \frac { \partial B } { \partial F } + \frac { \partial B } { \partial \sigma } \frac { \partial \sigma ^ { \mathrm { i m p } } } { \partial F }\tag{28}
$$

is the standard SABR delta, and

$$
\mathrm { V e g a } _ { t } ^ { \mathrm { m o d } } = \frac { \partial \mathcal { B } } { \partial \sigma } \frac { \partial \sigma ^ { \mathrm { i m p } } } { \partial \sigma } + \Bigl ( \frac { \partial \mathcal { B } } { \partial \sigma } \frac { \partial \sigma ^ { \mathrm { i m p } } } { \partial F } + \frac { \partial \mathcal { B } } { \partial F } \Bigr ) \frac { \rho C ( F _ { t } ) } { \alpha }\tag{29}
$$

is the modified SABR vega. Formula (27) is a decomposition of an option’s risk in terms of an alternative basis of independent risk factors, namely $d F ^ { \perp }$ and $d \sigma$

The two decompositions show that part of the option’s volatility sensitivity can be viewed as a component of its delta or its vega, depending on risk management approach. We take the view that it should be allocated to the delta risk, as monitoring and executing delta hedges are generally easier than vega hedges. Note also that the second order greeks do not contain any correlation dependent correction terms, and retain their form under both decompositions.

## 4 Robustness of the modified SABR delta

We will now turn to the main point of this note and derive an explicit asymptotic expression for the modified SABR delta. Taking derivatives of (8) we find that, to within the leading order in $\varepsilon ,$

$$
\frac { \partial \sigma ^ { \mathrm { i m p } } } { \partial F } = \frac { \alpha } { D ( \zeta ) } \Bigl \{ 1 - \frac { \sigma ^ { \mathrm { i m p } } } { \sigma C ( F ) I ( \zeta ) } \Bigr \} + O ( \varepsilon ) ,\tag{30}
$$

<!-- page: 7 -->

and

$$
\frac { \partial \sigma ^ { \mathrm { i m p } } } { \partial \sigma } = \frac { \sigma ^ { \mathrm { i m p } } \zeta } { \sigma D ( \zeta ) I ( \zeta ) } + O ( \varepsilon ) .
$$

In the following, in order not to overburden the formulas, we will be suppressing the terms $O ( \varepsilon )$ . It should be understood though that all formulas stated below are accurate to within $O ( \varepsilon )$

Now note that, for $\zeta$ small, we have

$$
I ( \zeta ) = 1 - \rho \zeta + O ( \zeta ^ { 2 } ) .\tag{31}
$$

As a consequence, the factor entering the modified delta (21) can be written as

$$
\begin{array} { r l } { \displaystyle \frac { \partial \sigma ^ { \mathrm { i m p } } } { \partial F } + \frac { \partial \sigma ^ { \mathrm { i m p } } } { \partial \sigma } \frac { \rho \alpha } { C ( F ) } = \frac { \alpha } { D ( \zeta ) } \Big \{ 1 - \frac { \sigma ^ { \mathrm { i m p } } } { \sigma C ( F ) } \frac { 1 - \rho \zeta } { I ( \zeta ) } \Big \} } & { } \\ { = \frac { \alpha } { D ( \zeta ) } \Big \{ 1 - \frac { \sigma ^ { \mathrm { i m p } } } { \sigma C ( F ) } + O ( \zeta ^ { 2 } ) \Big \} } & { } \\ { = \frac { \sigma ^ { \mathrm { i m p } } } { F - K } \Big \{ 1 - \frac { \sigma ^ { \mathrm { i m p } } } { \sigma C ( F ) } + O ( \zeta ^ { 2 } ) \Big \} } & { } \\ { = \frac { \sigma ^ { \mathrm { i m p } } } { \sigma C ( F ) } \frac { \sigma C ( F ) - \sigma ^ { \mathrm { i m p } } } { F - K } + O ( \zeta ) . } \end{array}
$$

In the limit $K F ,$ we have $\sigma ^ { \mathrm { i m p } } \sigma C ( { \cal F } )$ , and hence

$$
\frac { \partial \sigma ^ { \mathrm { i m p } } } { \partial { \cal F } } + \frac { \partial \sigma ^ { \mathrm { i m p } } } { \partial \sigma } \frac { \rho \alpha } { C ( { \cal F } ) } = \sigma C ^ { \prime } ( { \cal F } ) + { \cal O } ( { \cal F } - { \cal K } ) .
$$

As a result of these calculations, the modified SABR delta is given by

$$
\Delta ^ { \mathrm { m o d } } = \frac { \partial \mathcal { B } } { \partial F } + \frac { \partial \mathcal { B } } { \partial \sigma } \eta + O ( F - K ) ,\tag{32}
$$

as claimed in the Introduction. Note that, to the leading order in the option moneyness, this expression is independent of the details of the backbone function $C ( F )$ , it only depends on the implied volatility for the strike $K$ and the skew $\eta .$ Both of these quantities are market observable, and the calibrated model fits them. This explains the empirical observation made in [2] that the modified SABR delta is practically insensitive to the choice of the parameter $\beta ,$ once the remaining parameters have been optimized. In particular, the expression above shows that the modified delta of an at the money option, $K = F .$ , is independent of the choice of $\beta .$

This is to be contrasted with the behavior of the classic SABR delta. Indeed, we have

$$
\begin{array} { l } { \displaystyle \frac { \partial \sigma ^ { \mathrm { i m p } } } { \partial F } = \frac { \alpha } { D ( \zeta ) } \Big \{ 1 - \frac { \sigma ^ { \mathrm { i m p } } } { \sigma C ( F ) } \frac { 1 } { I ( \zeta ) } \Big \} } \\ { \displaystyle = \frac { \alpha } { D ( \zeta ) } \Big \{ 1 - \frac { \sigma ^ { \mathrm { i m p } } } { \sigma C ( F ) } \big ( 1 + \rho \zeta \big ) + O ( \zeta ^ { 2 } ) \Big \} } \\ { \displaystyle = \frac { \sigma ^ { \mathrm { i m p } } } { \sigma C ( F ) } \Big \{ \frac { \sigma C ( F ) - \sigma ^ { \mathrm { i m p } } } { F - K } + \frac { \rho \sigma ^ { \mathrm { i m p } } \zeta } { \sigma C ( F ) ( F - K ) } \Big \} + O ( \zeta ) } \\ { \displaystyle = \sigma C ^ { \prime } ( F ) + \frac { \rho \alpha } { C ( F ) } + O ( F - K ) , } \end{array}
$$

and therefore

$$
\Delta = \frac { \partial \mathcal { B } } { \partial F } + \frac { \partial \mathcal { B } } { \partial \sigma } \Bigl ( \eta + \frac { \rho \alpha } { C ( F ) } \Bigr ) + O ( F - K ) .\tag{33}
$$

In other words, the classic SABR delta, and thus the corresponding hedging strategy, depends on the choice of the backbone function $C ( F )$

<!-- page: 8 -->

## 5 Empirical analysis

We will now discuss some numerical and empirical data supporting the arguments presented above. More evidence is described in [2], [1], [5] (for interest rate options), and in [8], [3] (for equity options).

Figure 1 shows the classic SABR delta corresponding to three different calibrations of the same smile curve: $\beta = 0$ (black line), $\beta = 0 . 5$ (red line), and $\beta = 1$ (green line). For each of these choices of $\beta ,$ the three remaining SABR parameters are optimized to yield the best fit to the options prices corresponding to all available strikes K. Even though all three sets of parameters closely match the market smile, they lead to different delta hedges, especially for near the money strikes. Choosing the incorrect beta can lead to good fits of the smile, but may still produce relatively poor delta hedges.

![Figure 1: Classic SABR delta for different values of $\beta .$](assets/figures/2017-hagan-lesniewski-bartlett-delta-p0008-block-0004-61f5a36cedbcb690.jpg)

On the other hand, Figure 2 shows the modified deltas for the same three sets of parameters. Confirming the conclusions presented above, the modified SABR delta is nearly independent of $\beta ,$ even for way out of the money strikes. It depends mainly on the actual market smile, and not on how the smile is parameterized. Modified deltas tends to provide more robust hedges.

![Figure 2: Bartlett’s SABR delta for different values of $\beta .$](assets/figures/2017-hagan-lesniewski-bartlett-delta-p0008-block-0006-6e1bdfe0d11d07d3.jpg)

<!-- page: 9 -->

Figures 3 and 4 (both taken from [1]) present empirical data illustrating the historical relationship between the daily changes δσ in the volatility parameters σ and the daily changes in the forward swap rate $\delta F ,$ , in the 1Y into 10Y and 5Y into 5Y swaption deltas, respectively. Specifically, the graphs represent the corresponding regressions of δσ on $\rho \alpha / F ^ { \beta } \delta F$ . The underlying data are historical closes from the period 2003 - 2010.

![Figure 3: Regression of δσ against $\rho \alpha / F ^ { \beta } \delta F$ for the 1Y into 10Y swaption $( \beta = 0 . 5 )$](assets/figures/2017-hagan-lesniewski-bartlett-delta-p0009-block-0002-5e6c356026243edf.jpg)

![Figure 4: Regression of δσ against $\rho \alpha / F ^ { \beta } \delta F$ for the 5Y into 5Y swaption $( \beta = 0 . 7 5 )$](assets/figures/2017-hagan-lesniewski-bartlett-delta-p0009-block-0003-a2449a0b305cdba2.jpg)

## References

[1] Agarwal, N., and McWilliams, G. 2010. Evolution of volatility surface under SABR model. Courant Institute of Mathematical Sciences, NYU. [2] Bartlett, B. 2006: Hedging under SABR model, Wilmott Magazine. July/August, 2 - 4. [3] Cao, J., Chen, J., Hull, J., and Poulos, Z.: Deep Hedging of Derivatives Using Reinforcement Learning, preprint (2019).

<!-- page: 10 -->

[4] Hagan, P., Kumar, D., Lesniewski, A., and Woodward, D. 2002. Managing smile risk, Wilmott Magazine, September, 84 - 108. [5] Hagan, P., Kumar, D., Lesniewski, A., and Woodward, D. 2014. Arbitrage free SABR, Wilmott Magazine, January, 60 - 75. [6] Hagan, P., Kumar, D., Lesniewski, A., and Woodward, D. 2016. Universal smiles, Wilmott Magazine, July, 40 - 55. [7] Hagan, P., Lesniewski, A., and Woodward, D. 2005. Probability distribution in the SABR model of stochastic volatility, preprint. [8] Hull, J., and White, J. 2016: Optimal delta hedging for options, preprint (2016).
