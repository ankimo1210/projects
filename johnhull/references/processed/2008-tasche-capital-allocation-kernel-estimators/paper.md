# 2008-tasche-capital-allocation-kernel-estimators

<!-- page: 1 -->

## Capital allocation for credit portfolios with kernel estimators

Dirk Tasche<sup>∗</sup>

May 2008

## Abstract

Determining contributions by sub-portfolios or single exposures to portfolio-wide economic capital for credit risk is an important risk measurement task. Often economic capital is measured as Valueat-Risk (VaR) of the portfolio loss distribution. For many of the credit portfolio risk models used in practice, the VaR contributions then have to be estimated from Monte Carlo samples. In the context of a partly continuous loss distribution (i.e. continuous except for a positive point mass on zero), we investigate how to combine kernel estimation methods with importance sampling to achieve more eficient (i.e. less volatile) estimation of VaR contributions.

## 1 Introduction

In many financial institutions, there is a well established practice of measuring the risk of their portfolios in terms of economic capital (cf., e.g. Dev, 2004). Measuring portfolio-wide economic capital, however, is only the first step towards active, portfolio-oriented risk management. For purposes like identification of risk concentrations, risk-sensitive pricing or portfolio optimisation it is also necessary to decompose portfolio-wide economic capital into a sum of risk contributions by sub-portfolios or single exposures (see, e.g., Litterman, 1996).

While already calculating or estimating economic capital is non-trivial in general, determining risk decompositions is even more demanding (see, e.g., Yamai and Yoshiba, 2002). For most of the economic capital models used in practice, no closed-form solutions for risk contributions are available<sup>1</sup>. As a consequence, for such models there is a need for simulation to create samples from which to estimate economic capital as well as risk contributions. These estimations often involve evaluations of very far tails of the risk return distributions, causing high variability of the estimates. Various variance reduction techniques have been proposed, one of the more popular being importance sampling (see Glasserman and Li, 2005; Merino and Nyfeler, 2004; Kalkbrener et al., 2004, for its application to credit risk). Glasserman (2005) suggests a two-step importance sampling approach to the estimation of contributions to Value-at-Risk (VaR), the most popular metric underlying economic capital methodologies.

Glasserman’s approach, however, does apply to discrete loss distributions only (i.e. to distributions such that each potential loss value has a positive probability to be assumed), which means a significant restriction as loss distributions based on continuous loss given default rate distributions seem to be more realistic in practical applications. According to Theorem 3.3 below such loss distributions have the property that each single potential positive loss has probability zero to be assumed but there is a positive probability of not observing any loss. The probability of not observing losses is significantly positive in particular for small and medium portfolio sizes (with 200 names or less) which occur, for instance, in typical securitisation deals.

arXiv:math/0612470v4 [math.ST] 11 May 2008

<sup>∗</sup>Lloyds TSB Corporate Markets, Red Lion Court, 46-48 Park Street, London SE1 9EQ, United Kingdom. E-mail: dirk.tasche@gmx.ne

The opinions expressed in this paper are those of the author and do not necessarily reflect views of Lloyds TSB.

<sup>1</sup>See Tasche (2004) or Tasche (2006) for notable exceptions.

<!-- page: 2 -->

To solve the problem of determining VaR contributions when positive losses have a continuous distribu-$\tan ^ { 2 }$ , in this paper we follow, where possible, the path used by Gouri´eroux et al. (2000), Epperlein and Smillie (2006), and Gouri´eroux and Liu (2006) who apply kernel estimation methods for estimating VaR contri butions and contributions to spectral risk measures in a market risk context with continuous distributions. Kernel estimators are a well-established concept (see, e.g., Pagan and Ullah, 1999) to deal with the issue of estimating non-elementary expectations as they occur in the context of capital allocation. Due to the rare event issue characteristic for credit risk, entailing rather volatile estimates when standard Monte Carlo simulation is used, we combine the kernel estimation technique with importance sampling (shifting the means of the systematic factors to be more specific) for reducing estimation variance. The paper is organized as follows:

Section 2 contains a review, in the necessary details, of the capital allocation problem and the specific issues with the estimation of risk contributions when the loss distribution is partly continuous.

Section 3 provides a brief review of kernel estimators for densities and conditional expectations as well as its application to credit loss distributions with a partly continuous distribution.

Section 4 introduces the model studied here and explains how to combine the kernel estimators from Section 3 with importance sampling for credit risk.

Application of the algorithms introduced is illustrated with a numerical example in Section 5.

We conclude with an assessment in Section 6 of what has been reached.

## 2 Capital allocation

In the following, we consider the following stochastic credit portfolio loss model:

$$
L \ = \ \sum _ { i = 1 } ^ { n } L _ { i } .\tag{2.1}
$$

$L _ { 1 } , \dots , L _ { n } \geq 0$ are random variables that represent the losses that a financial institution sufers on its exposures to borrowers $i = 1 , \ldots , n$ within a fixed time-period, e.g. one year. The random variable L then expresses the portfolio-wide loss. We denote by $\mathrm { P } [ \ldots ]$ the real-world probability distribution that underlies model (2.1). In other words, $\mathrm { P } [ \ldots ]$ is calibrated in such a way that it reflects as close as possible observed loss frequencies. $\mathrm { P } [ L \leq \ell ]$ , for instance, stands for the probability of observing portfolio-wide losses that do not exceed the amount ℓ. The operator $\mathrm { E } _ { \mathrm { P } } [ \dots \cdot ]$ is defined as mathematical expectation with respect to probability P. In particular, $\mathrm { E } _ { \mathrm { P } } [ L ]$ reflects the real-world probability weighted mean of the portfolio-wide loss.

As mentioned in the introduction, it is common practice for financial institutions to measure the risk inherent in their portfolios in terms of economic capital (EC). As credit risk, for most institutions, is considered to be most important, this is in particular relevant for credit portfolios. EC is commonly understood as a capital bufer intended to cover the losses of the lending financial institution with a high probability. This interpretation makes appear very natural the definition

$$
\begin{array} { r } { \mathrm { E C } \ = \ \mathrm { V a R } _ { \mathrm { P } , \alpha } ( L ) - \mathrm { E } _ { \mathrm { P } } [ L ] , } \end{array}\tag{2.2a}
$$

where the Value-at-Risk (VaR) is given as a high-level $( \mathrm { e . g . ~ } \alpha = 9 9 . 9 \% )$ quantile of the portfolio-wide loss:

$$
\operatorname { V a R } _ { \mathrm { P } , \alpha } ( L ) \ = \ \operatorname* { m i n } \{ \ell : \ \mathrm { P } [ L \leq \ell ] \geq \alpha \} .\tag{2.2b}
$$

<sup>2</sup>Instead of trying to determine VaR contributions in a continuous or semi-continuous setting, some risk managers use contributions to expected shortfall. This approach is very fruitful and has some other advantages (see Kalkbrener et al., 2004; Merino and Nyfeler, 2004).

<!-- page: 3 -->

Hence, if a financial institutions holds EC according to (2.2a) and charges the loans granted with upfront fees adding up to $\mathrm { E } _ { \mathrm { P } } [ L ]$ , the probability that it will lose all its EC is not higher than $1 - \alpha$ . Note that, despite its intuitive appeal, VaR as a risk measure is criticised, e.g. for its potential lack of rewarding diversification (see Acerbi and Tasche, 2002, and the references therein).

Active risk management involves more than just measuring portfolio-wide capital according to (2.2a). Additionally, it is of interest to identify which parts of the portfolio bind the largest portions of EC. The corresponding process of determining a risk-sensitive decomposition of EC is called capital allocation. While for the expectation part $\mathrm { E } _ { \mathrm { P } } [ L ]$ of EC on the right-hand side of (2.2a) there is the natural decomposition

$$
\operatorname { E } _ { \mathrm { P } } [ L ] = \sum _ { i = 1 } ^ { n } \operatorname { E } _ { \mathrm { P } } [ L _ { i } ] ,\tag{2.3a}
$$

there is no such obvious decomposition

$$
\operatorname { V a R } _ { \mathrm { P } , \alpha } ( L ) \ = \ \sum _ { i = 1 } ^ { n } \operatorname { V a R } _ { \mathrm { P } , \alpha } ( L _ { i } \mid L )\tag{2.3b}
$$

for the VaR-part of EC into risk contributions<sup>3</sup>. Indeed, the choice of the decomposition method depends on the concept of risk sensitivity adopted. Interpreting risk sensitivity as compatibility with portfolio optimization, Tasche (1999) proved that the risk contributions $\operatorname { V a R } _ { \operatorname { P } , \alpha } ( L _ { i } | L )$ on the right-hand side of (2.3b) should be defined as directional derivatives, i.e.

$$
\mathrm { V a R } _ { \mathrm { P } , \alpha } ( L _ { i } | L ) \ = \ \frac { d \mathrm { V a R } _ { \mathrm { P } , \alpha } ( L + h L _ { i } ) } { d h } \vert _ { h = 0 } .\tag{2.4}
$$

As VaR is a positively homogeneous<sup>4</sup> risk measure, by Euler’s theorem, then (2.3b) holds. (2.4) displays the concept of risk contribution applied in this paper. Note however that in general, and in particular if the distribution of L has no density, the derivative on the right-hand side (2.4) need not exist. See, e.g., Tasche (1999, Assumption (S)) for conditions ensuring existence of the derivative. Depending on the objective of the portfolio analysis, other approaches to determining risk contributions are reasonable, see, e.g., Section 3.1 of Tasche (2006) for an account of these.

In general, no closed-form representations of $\operatorname { V a R } _ { \mathrm { P } , \alpha } ( L )$ and the risk contributions $\operatorname { V a R } _ { \operatorname { P } , \alpha } ( L _ { i } | L )$ are available. Therefore, often, these quantities can only be inferred from Monte-Carlo samples. This means essentially to generate a sample

$$
( L ^ { ( t ) } , L _ { 1 } ^ { ( t ) } , \dots , L _ { n } ^ { ( t ) } ) , \quad t = 1 , \dots , T ,\tag{2.5}
$$

and then to estimate the quantities under consideration on the basis of this sample. How to do this is quite obvious for VaR, but is much less clear for the risk contributions $\operatorname { V a R } _ { \operatorname { P } , \alpha } ( L _ { i } | L )$ as, in general, estimating derivatives of stochastic quantities without closed-form representation is a subtle issue.

Fortunately, it turns out (Gouri´eroux et al., 2000; Lemus, 1999; Tasche, 1999) that, under fairly general conditions on the joint distribution of $L$ and $L _ { i }$ , the derivative (2.4) coincides with an expectation of the loss related to borrower i conditional on the event of observing a portfolio-wide loss equal to VaR.

$$
{ \frac { d \mathrm { V a R } _ { \mathrm { P } , \alpha } ( L + h L _ { i } ) } { d h } } | _ { h = 0 } = \mathrm { E } _ { \mathrm { P } } [ L _ { i } | L = \mathrm { V a R } _ { \mathrm { P } , \alpha } ( L ) ]\tag{2.6}
$$

If $\mathrm { P } [ L = \mathrm { V a R } _ { \mathrm { P } , \alpha } ( L ) ]$ is positive, the conditional expectation on the right-hand side of (2.6) is given by

$$
\mathrm { E } _ { \mathrm { P } } [ L _ { i } | L = \mathrm { V a R } _ { \mathrm { P } , \alpha } ( L ) ] \ = \ \frac { \mathrm { E } _ { \mathrm { P } } [ L _ { i } \mathbf { 1 } _ { \{ L = \mathrm { V a R } _ { \mathrm { P } , \alpha } ( L ) \} } ] } { \mathrm { P } [ L = \mathrm { V a R } _ { \mathrm { P } , \alpha } ( L ) ] } .\tag{2.7}
$$

<sup>3</sup>Kalkbrener (2005) considers relation (2.3b) in a more general context. He calls it “linear aggregation”.

<sup>4</sup>I.e. VaR<sub>P,α</sub>(h L) = h VaR<sub>P,α</sub>(L) for positive h.

<!-- page: 4 -->

Even if $\mathrm { P } [ L = \mathrm { V a R } _ { \mathrm { P } , \alpha } ( L ) ]$ is positive, its magnitude will usually be very small, such as $1 - \alpha$ or less. Glasserman (2005) shows how to apply importance sampling in such a situation in order to eficiently estimate $\mathrm { E } _ { \mathrm { P } } [ L _ { i } \mid L = \mathrm { V a R } _ { \mathrm { P } , \alpha } ( L ) ]$

However, a crucial condition for (2.6) to hold exactly is the existence of a density of the distribution of L. The probability $\mathrm { P } [ L = \mathrm { V a R } _ { \mathrm { P } , \alpha } ( L ) ]$ then equals zero, and consequently the right-hand side of (2.7) is undefined<sup>5</sup>. In this situation, the conditional expectation $\mathrm { E } _ { \mathrm { P } } [ L _ { i } \mid L = \mathrm { V a R } _ { \mathrm { P } , \alpha } ( L ) ]$ ] is still well-defined (see, $\mathrm { e . g . }$ , Remark 5.4 of Tasche, 1999), but its estimation from a sample like (2.5) requires more elaborated nonparametric methods. Mausser and Rosen (2004) suggest using an estimation method based on weighted combinations of order-statistics. We follow here Gouri´eroux et al. (2000) who applied kernel estimation methods for VaR contributions when optimizing returns in a portfolio of stocks. The kernel estimation procedures, however, have to be adapted to the rare-event character of credit risk. Therefore, in the remainder of the paper we modify the approach by Gouri´eroux et al. in a way that can be described as a combination of kernel estimation and importance sampling.

## 3 Kernel estimators

In this section, we introduce the classical Rosenblatt-Parzen kernel estimator for densities and the Nadaraya-Watson kernel estimator for conditional expectations in a way that links naturally to the risk contribution concept of Section 2. The general reference for this section is Pagan and Ullah (1999, Chapters 2 and 3).

## 3.1 The Rosenblatt-Parzen kernel estimator for densities

Assume that $x _ { 1 } , \ldots , x _ { T }$ is a sample of independent realisations of a random variable X with density $f .$ The Rosenblatt-Parzen estimator $\hat { f } _ { h }$ with bandwidth $h > 0$ for f can be constructed as follows:

Let $X ^ { * }$ be a random variable whose distribution is given by the empirical distribution corresponding to the sample $x _ { 1 } , \ldots , x _ { T }$ , i.e. $\operatorname { P } [ X ^ { * } = x _ { t } ] = 1 / T , t = 1 , \dots , T$

Let $\xi$ a random variable with density (kernel) $\varphi .$

Assume that $X ^ { * }$ and ξ are independent.

Then the estimator $\hat { f } _ { h }$ is defined as the density of $X ^ { * } + h \xi$

$$
\begin{array} { r } { \hat { f } _ { h } ( x ) \ = \hat { f } _ { h , x _ { 1 } , \ldots , x _ { T } } ( x ) \ = \ \frac { 1 } { h T } \sum _ { t = 1 } ^ { T } \varphi \big ( \frac { x - x _ { t } } { h } \big ) . } \end{array}\tag{3.1}
$$

If $f$ and $\varphi$ are appropriately “smooth” (see Pagan and Ullah, 1999, Theorem 2.5 for details), it can be shown for $h = h _ { T } \xrightarrow { T \infty } 0 , h _ { T } T \xrightarrow { T \infty }$ that $\hat { f } _ { h _ { T } } ( x )$ is a pointwise mean-squared consistent estimator of $f ,$ i.e.

$$
\operatorname* { l i m } _ { T \to \infty } \operatorname { E } [ ( f ( x ) - \hat { f } _ { h _ { T } , X _ { 1 } , \ldots , X _ { T } } ( x ) ) ^ { 2 } ] = 0 , \quad x \in \mathbb { R } ,\tag{3.2}
$$

with independent copies $X _ { 1 } , \ldots , X _ { T }$ of X. While the Rosenblatt-Parzen density estimator is rather robust with respect to the choice of the kernel $\varphi ,$ it is quite sensitive to the choice of the bandwidth $h .$ For the univariate case we consider here, eficient techniques like cross validation for the choice of the bandwidth are available. However, such more elaborated techniques usually involve some optimisation procedures that can be very time-consuming for large samples. As a consequence, for the purpose of this paper we confine ourselves to applying a simple rule of thumb by Silverman (cf. Chapter 2 in Pagan and Ullah, 1999)

<sup>5</sup>This problem can be avoided by using the risk measure Expected Shortfall (see, e.g., Acerbi and Tasche, 2002) instead of VaR. With the definition of Expected Shortfall slightly simplified for practical purposes, (2.7) then reads E<sub>P</sub>[L<sub>i</sub> | L ≥ VaR<sub>P,α</sub>(L)] = (1 − α)<sup>−1</sup>E<sub>P</sub>[L<sub>i</sub> 1<sub>{L≥VaR (L)}</sub>].

<!-- page: 5 -->

$$
h \ = \ 1 . 0 6 \sigma T ^ { - 1 / 5 } ,\tag{3.3}
$$

where σ denotes the standard deviation of the sample $x _ { 1 } , \ldots , x _ { T }$ . Moreover, we choose the standard normal density as the kernel $\varphi$

## 3.2 The Nadaraya-Watson kernel estimator for conditional expectations

Assume that $( x _ { 1 } , y _ { 1 } ) , \dotsc , ( x _ { T } , y _ { T } )$ is a sample of realisations of a random vector $( X , Y )$ where X has a density $f .$ . The Nadaraya-Watson estimator ${ \hat { \operatorname { E } } } _ { h } [ Y \mid X = x ]$ with bandwidth h for $\operatorname { E } [ Y \mid X = x ]$ can be constructed as follows:

Let $( X ^ { * } , Y ^ { * } )$ a random vector whose distribution is given by the empirical distribution corresponding to the sample $( x _ { 1 } , y _ { 1 } ) , \dotsc , ( x _ { T } , y _ { T } )$ , i.e. $\mathrm { P } [ ( X ^ { \ast } , Y ^ { \ast } ) = ( x _ { t } , y _ { t } ) ] = 1 / T$

Let $\xi$ a random variable with density (kernel) $\varphi .$

Assume that $( X ^ { * } , Y ^ { * } )$ and $\xi$ are independent.

Then the estimator ${ \hat { \mathrm { E } } } _ { h } [ Y \mid X = x ]$ is defined as the expectation of $Y ^ { * }$ conditional on $X ^ { * } + h \xi = x \colon$

$$
\begin{array} { r } { \hat { \mathrm { E } } _ { h } [ { \cal Y } \vert { \cal X } = x ] ~ = ~ \hat { \mathrm { E } } _ { h , ( x _ { 1 } , y _ { 1 } ) , \ldots , ( x _ { T } , y _ { T } ) } [ { \cal Y } \vert { \cal X } = x ] ~ = ~ \frac { \sum _ { t = 1 } ^ { T } y _ { t } \varphi \left( \frac { x - x _ { t } } { h } \right) } { \sum _ { t = 1 } ^ { T } \varphi \left( \frac { x - x _ { t } } { h } \right) } . } \end{array}\tag{3.4}
$$

If $f$ and $\varphi$ are appropriately “smooth” (see Pagan and Ullah, 1999, Theorem 3.4 for details), it can be shown for $h = h _ { T } \xrightarrow { T \to \infty } 0 , h _ { T } T \xrightarrow { T \to \infty } \infty$ , and $f ( x ) > 0$ that ${ \hat { \operatorname { E } } } _ { h } [ Y \mid X = x ]$ is a pointwise consistent estimator of $\operatorname { E } [ Y \mid X = x ]$ , i.e.

$$
\operatorname* { l i m } _ { T \to \infty } \operatorname { P } \big [ \big | \operatorname { E } [ Y \mid X = x ] - \hat { \operatorname { E } } _ { h _ { T } , ( X _ { 1 } , X _ { 1 } ) , \ldots , ( X _ { T } , X _ { T } ) } [ Y \mid X = x ] \big | > \varepsilon \big ] = 0 , \varepsilon > 0 \mathrm { ~ a r b i t r a r y , }\tag{3.5}
$$

with independent copies $( X _ { 1 } , Y _ { 1 } ) , \dots , ( X _ { T } , Y _ { T } )$ of $( X , Y )$ . The construction of the Nadaraya-Watson estimator (3.4) as described above allows to interpret the conditional expectation estimation problem as an extended density estimation problem. This suggests to choose the same bandwidth h and the same kernel $\varphi$ for the estimators (3.1) and (3.4).

Remark 3.1 Assume that in the random vector $( X , Y )$ the X-component is a sum of random variables $X _ { 1 } , \ldots , X _ { n }$ and that we are interested in estimating $\operatorname { E } [ X _ { i } \mid X = x ] , i = 1 , \ldots , n$ . Define $( X _ { 1 } ^ { * } , \ldots , X _ { n } ^ { * } )$ analogously to $( X ^ { * } , Y ^ { * } )$ as the “empirical” version of $( X _ { 1 } , \ldots , X _ { n } )$ . According to (3.4), the Nadaraya-Watson estimator of $\operatorname { E } [ X _ { i } \mid X = x ]$ can then be specified as

$$
\hat { \operatorname { E } } _ { h } [ X _ { i } \mid X = x ] \ = \ \operatorname { E } [ X _ { i } ^ { * } \mid X ^ { * } + h \xi = x ] ,\tag{3.6a}
$$

with an appropriate auxiliary variable $\xi$ independent of $( X _ { 1 } ^ { * } , \ldots , X _ { n } ^ { * } )$ . If the same bandwidth h is applied for all $i ,$ then from representation (3.6a) follows

$$
\sum _ { i = 1 } ^ { n } \hat { \mathrm { E } } _ { h } [ X _ { i } \mid X = x ] ~ = ~ x - h \mathrm { E } [ \xi \mid X ^ { * } + h \xi = x ] .\tag{3.6b}
$$

As we will note in Section 5.2 when commenting on Table 6, the size of the diference of the $l e f t$ -hand side of (3.6b) and x can be regarded as providing additional information on the choice of the bandwidth h. We will apply the multiplicative adjustment suggested by Epperlein and Smillie (2006, Equation (7)) to force additivity in the sense of (2.3b) on the estimated contributions to VaR.

<!-- page: 6 -->

## 3.3 Application to credit losses

For every credit risk portfolio, there is some positive probability of observing no losses. While for large portfolios, this probability will usually be negligibly small, we will see by the example from Section 5 that the probability of zero loss can be of significant magnitude for smaller portfolios. As a consequence, we cannot assume that the loss variable L from model (2.1) has an unconditional density. For otherwise $\mathrm { P } [ L = 0 ]$ would be zero. Hence, at first glance, applying the estimators (3.1) and (3.4) seems not possible in the context of model (2.1). The following assumption, however, allows us to deal with this problem.

Assumption 3.2 There is a random vector $( S _ { 1 } , \ldots , S _ { k } )$ , (called systematic factors), with the following properties:

(i) The loss variables $L _ { i }$ in (2.1) are independent conditional on realisations of $( S _ { 1 } , \ldots , S _ { k } )$

(ii) For each $i = 1 , \ldots , n$ , there are probabilities $p _ { i } ( s _ { 1 } , \ldots , s _ { k } ) \in [ 0 , 1 ]$ and densities $0 \leq f _ { i } ( \ell , s _ { 1 } , \ldots , s _ { k } )$ such that the distribution function of $L _ { i }$ conditional on $( S _ { 1 } , \ldots , S _ { k } )$ is given for $\ell \geq 0$ by

$$
\begin{array} { r } { \mathrm { P } [ L _ { i } \leq \ell | ( S _ { 1 } , \ldots , S _ { k } ) = ( s _ { 1 } , \ldots , s _ { k } ) ] = } \end{array}
$$

$$
1 - p _ { i } ( s _ { 1 } , \dots , s _ { k } ) + p _ { i } ( s _ { 1 } , \dots , s _ { k } ) \int _ { 0 } ^ { \ell } f _ { i } ( x , s _ { 1 } , \dots , s _ { k } ) d x .\tag{3.7}
$$

Under Assumption 3.2, it is easy to derive the following result on the representation of the unconditional distribution of the portfolio-wide loss L.

Theorem 3.3 Define $I _ { n } = \{ 1 , \ldots , n \}$ and write $\otimes$ for the multiple convolution of densities. Then, under assumption 3.2, for $\ell \geq 0$ the distribution function of the loss variable L from (2.1) can be written as

$$
\operatorname { P } [ L \leq \ell ] = p + ( 1 - p ) \int _ { 0 } ^ { \ell } f ( x ) d x ,\tag{3.8}
$$

with

$$
p = \mathrm { P } [ L _ { 1 } = 0 , \ldots , L _ { n } = 0 ] , \allowbreaks \qquad \quad \quad \quad \quad \quad \quad f ( x ) = \sum _ { \theta \neq I \subset I _ { n } } \mathrm { E } _ { \mathrm { P } } \Big [ \prod _ { i \in I } p _ { i } ( S _ { 1 } , \ldots , S _ { k } ) \prod _ { i \in I _ { n } \setminus I } \left( 1 - p _ { i } ( S _ { 1 } , \ldots , S _ { k } ) \right) \big ( \bigotimes _ { i \in I } f _ { i } ( \cdot , S _ { 1 } , \ldots , S _ { k } ) \big ) ( x ) \Big ] .
$$

Although, due to the involved multiple convolutions, (3.8) is not really useful for calculating the distribution of $L ,$ it allows us to assume that, conditional on being positive, the portfolio-wide loss has a density, i.e. for $\ell \geq 0$

$$
\operatorname { P } [ L \leq \ell | L > 0 ] \ = \ \int _ { 0 } ^ { \ell } f ( x ) d x .\tag{3.9}
$$

Define $\mathrm { P ^ { * } }$ by

$$
\mathrm { P } ^ { * } [ A ] \ = \ \mathrm { P } [ A | L > 0 ]\tag{3.10}
$$

for any relevant event A. The following lemma is then obvious.

Lemma 3.4 If the probability $\mathrm { P ^ { * } }$ is given by (3.10), then for $\ell > 0$ the expectations conditional on $L = \ell$ with respect to $\mathrm { P ^ { * } }$ and $\mathrm { P }$ are identical. In particular, in the context of model (2.1) for all $i = 1 , \ldots , n$ and $\ell > 0$ we have

$$
\mathrm { E } _ { \mathrm { P } } [ L _ { i } \ : | \ : L = \ell ] = \mathrm { E } _ { \mathrm { P } ^ { * } } [ L _ { i } \ : | \ : L = \ell ] .
$$

<!-- page: 7 -->

Note that a sample (2.5) generated under measure P becomes a sample generated under measure $\mathrm { P ^ { * } }$ when all (n + 1)-tuples $( L ^ { ( t ) } , L _ { 1 } ^ { ( t ) } , \ldots , L _ { n } ^ { ( t ) } )$ with $L ^ { ( t ) } = 0$ are eliminated. For this sub-sample then the preconditions for applying estimators (3.1) and (3.4) are satisfied. This observation leads to the following algorithm for estimating the risk contributions according to (2.6) for model (2.1) by Monte Carlo sampling.

## Algorithm 3.5

1. Generate a sample like (2.5) from the real-world probability measure $\mathrm { P } .$

2. Determine an estimate<sup>6</sup> <sup>ˆ</sup>ℓ $o f \operatorname { V a R } _ { \operatorname { P } , \alpha } ( L )$ from this sample.

3. Extract the sub-sample with $L ^ { ( t ) } > 0$ from the previous sample.

4. Calculate, on the basis of the sub-sample with $L ^ { ( t ) } > 0 .$ , the bandwidth $h ^ { * }$ according to (3.3).

5. Calculate the estimates for $\mathrm { E } _ { \mathrm { P } } [ L _ { i } \mid L = \mathrm { V a R } _ { \mathrm { P } , \alpha } ( L ) ] , i = 1 , \ldots , n $ , on the basis of the sub-sample with $L ^ { ( t ) } > 0$ , according to (3.4) as $\hat { \mathrm { E } } _ { h ^ { * } } [ L _ { i } | L = \hat { \ell } ]$ (cf. Remark 3.1).

In the following section, we will modify this algorithm by incorporating importance sampling for reducing the variances of the estimates.

## 4 Importance sampling for credit risk

McNeil et al. (2005), at the beginning of Chapter 8.5, write “A possible method for calculating risk measures and related quantities such as capital allocations is to use Monte Carlo (MC) simulation, although the problem of rare event simulation arises.” They then explain, in the context of risk contributions to Expected Shortfall, that “the standard MC estimator . . . will be unstable and subject to high variabil ity, unless the number of simulations is very large. The problem is of course that most simulations are ‘wasted’, in that they lead to a value of L which is smaller than $\mathrm { V a R } _ { \mathrm { P } , \alpha } ( L ) . ^ { , }$ What applies to contributions to expected shortfall applies even more to VaR contributions as these, according to (2.6), are related to events still more rare and actually in our case of probability zero. Thus, the key idea with importance sampling is to replace the real-world probability measure P by a probability measure $\mathrm { Q }$ which puts more mass on the interesting events.

Some technical assumptions are needed to guarantee that such a replacement of probabilities does really work.

## Assumption 4.1

The probability measures P and Q are defined on the same measurable space $( \Omega , { \mathcal { F } } )$

There is a measure $\mu$ on $( \Omega , { \mathcal { F } } )$ such that both P and Q are absolutely continuous with respect to $\mu .$ Denote by f the density of P and by g the density $o f \mathrm { Q }$

$f > 0$ implies $g > 0$ , i.e. P is absolutely continuous with respect to $\mathrm { Q }$

Under Assumption 4.1, the likelihood ratio

$$
R \ = \ { \frac { f } { g } }\tag{4.1}
$$

is Q-almost surely well-defined. This implies that any expectation with respect to P can be expressed as an expectation with respect to Q, i.e. for any integrable X holds

$$
\operatorname { E } _ { \mathrm { P } } [ X ] \ = \ \operatorname { E } _ { \mathrm { Q } } [ R X ] .\tag{4.2}
$$

<sup>6</sup>We may assume ℓ ><sup>ˆ</sup> 0 as for real-world portfolios the case ℓ<sup>ˆ</sup> = 0 seems very unlikely.

<!-- page: 8 -->

However, according to (2.6), for the purpose of this paper it is a conditional rather than an unconditional expectation we are interested in. The following proposition gives a result analogous to (4.2), for conditional expectations.

Proposition 4.2 Let P and Q be probability measures as in Assumption 4.1, with µ-densities f and g respectively. Define the likelihood ratio R by (4.1). Then we have for any sub-σ-algebra of and any integrable random variable X

$$
\operatorname { E } _ { \mathrm { P } } [ X \mid A ] \ = \ { \frac { \operatorname { E } _ { \mathrm { Q } } [ R X \mid A ] } { \operatorname { E } _ { \mathrm { Q } } [ R \mid A ] } } .\tag{4.3}
$$

Proof. See e.g. Klebaner (2005, Theorem 10.8).

The choice of an appropriate measure $\mathrm { Q }$ for use in (4.2) and (4.3) is not at all obvious. Inspecting (2.1) and (2.6), it becomes clear that, for the purpose of this paper, we are interested in events that result in losses close<sup>7</sup> to $\hat { \ell } = \mathrm { V a R } _ { \mathrm { P } , \alpha } ( L )$ , as defined by (2.2b).

In Section 5, we will specifically consider a numerical example that satisfies the following conditions which reflect assumptions commonly made for models in industry.

Assumption 4.3 The portfolio-wide loss L is given by (2.1). $L _ { 1 } , \ldots , L _ { n }$ are given as

$$
L _ { i } \ = \ A _ { i } { \bf 1 } _ { D _ { i } } .
$$

$D _ { 1 } , \ldots , D _ { n }$ are independent $( d e f a u l t )$ events, conditional on a set of systematic factors $( S _ { 1 } , \ldots , S _ { k } )$ , with $\mathrm { P } [ D _ { i } ] = p _ { i }$ . The loss severity variables $A _ { 1 } , \ldots , A _ { n }$ are positive and independent, as well as independent of the $D _ { 1 } , \ldots , D _ { n }$ and the $S _ { 1 } , \ldots , S _ { k }$ . The distribution of $A _ { i }$ is specified via its density $a _ { i } ( s ) \geq 0$

Note that, under the condition of the $A _ { i }$ having densities, Assumption 4.3 is a special case of Assumption 3.2. As a consequence of this, according to Theorem 3.3 the loss variable L from (2.1) has, in theory, a density for its positive realisations.

Merino and Nyfeler (2004) and Glasserman and Li (2005) suggest a nested simulation procedure where exponential twisting is applied for the estimation of expectations conditional on the systematic factors.The resulting conditional loss distribution then can essentially be described again by Assumption 4.3, with independence instead of conditional independence and modified probabilities of default. Unfortunately, this nested procedure cannot be applied for our problem of estimating $\operatorname { E p } [ L _ { i } \mid L = { \bf \cdot } ]$ as there is no independence conditional on L. In general, we have $\sigma ( L ) \not \subset \sigma ( S _ { 1 } , . . . , S _ { k } )$ and $\sigma ( S _ { 1 } , \ldots , S _ { k } ) \subset \sigma ( L )$ Therefore, no nesting of conditioning is applicable either. Exponential twisting can be applied nevertheless but does not yield satisfactory results as it is not clear how an optimal tilting parameter should be determined.

Approaches by Kalkbrener et al. (2004) and Glasserman and Li (2005) are promising alternatives to exponential twisting. In these approaches, the importance sampling measure Q is created by changing the means of the systematic factors from Assumption 4.3. Kalkbrener et al. (2004) suggest to determine the factor means appropriate for importance sampling by solving a minimisation problem for the variance of the estimator they consider. Glasserman and Li (2005) instead look for factor means that make the mode of the factor distribution coincide (approximately) with the mode of the “zero-variance importance sampling” distribution. However, these approaches are more complex compared to exponential twisting as they involve – in the case of a multi-factor model – choosing several parameters instead of only one as required by exponential twisting.

The approach we follow in this paper is close in spirit to the approach by Glasserman and Li (2005). Define the importance sampling probability measure $\mathrm { Q } = \mathrm { Q } _ { \mu }$ by Assumption 4.3, but replace the vector $( S _ { 1 } , \ldots , S _ { k } )$ of systematic factors by a vector $( S _ { 1 } ^ { * } , \ldots , S _ { k } ^ { * } )$ with

<sup>7</sup>In general, ℓ<sup>ˆ</sup> itself will have to be estimated. Thus, at first glance, it seems strange to choose it as a basis for finding Q. However, in a first step, for instance, it can be replaced by a rough estimate and be refined in further stages of the estimation procedure.

<!-- page: 9 -->

$$
S _ { i } ^ { * } ~ = ~ S _ { i } - \mathrm { E } _ { \mathrm { P } } [ S _ { i } ] + \mu _ { i }\tag{4.4a}
$$

where $\boldsymbol { \mu } = ( \mu _ { 1 } , \dots , \mu _ { k } )$ satisfies

$$
\mu _ { i } \approx \mathrm { E } _ { \mathrm { P } } [ S _ { i } | L = \mathrm { V a R } _ { \mathrm { P } , \alpha } ( L ) ] .\tag{4.4b}
$$

The conditional expectations in (4.4b) are estimated by applying the Nadaraya-Watson estimator (3.4).

Algorithm 3.5 for estimating the risk contributions according to (2.6) for model (2.1) by Monte Carlo sampling has to be modified as follows when importance sampling is applied.

## Algorithm 4.4

1. Generate a sample $( L ^ { ( t ) } , L _ { 1 } ^ { ( t ) } , \dots , L _ { n } ^ { ( t ) } ) , t = 1 , \dots , T _ { 1 }$ , from the original sampling probability measure P.

2. Determine an estimate $\hat { \ell } \ o f \operatorname { V a R } _ { \operatorname { P } , \alpha } ( L )$ from this sample.

3. Calculate, on the basis of the sub-sample with $L ^ { ( t ) } > 0$ , the standard MC simulation bandwidth $h ^ { * }$ according to (3.3).

4. Estimate the mean shift parameters $\mu _ { i }$ according to (4.4b) from the sample $( L ^ { ( t ) } , L _ { 1 } ^ { ( t ) } , \ldots , L _ { n } ^ { ( t ) } )$ $t = 1 , \dots , T _ { 1 }$ , for instance by applying the Nadaraya-Watson estimator.

5. Generate a sample<sup>8</sup> $( L ^ { ( t ) } , L _ { 1 } ^ { ( t ) } , \dots , L _ { n } ^ { ( t ) } , R ^ { ( t ) } ) , t = 1 , \dots , T _ { 2 }$ , from the importance sampling probability measure ${ \mathrm { Q } } _ { \mu } . \ R ^ { ( t ) }$ denotes realisations of the likelihood ratio as defined by (4.1).

6. (Optional) Determine a refined estimate<sup>9</sup> <sup>ˆ</sup>ℓ $o f \operatorname { V a R } _ { \operatorname { P } , \alpha } ( L )$ from this sample.

7. Calculate, on the basis of the sub-sample with $L ^ { ( t ) } > 0$ , the importance sampling bandwidth $h ^ { * }$ according to (3.3).

8. Estimate, on the basis of the sub-sample with $L ^ { ( t ) } > 0$ , the $\mathrm { Q } _ { \mu }$ -conditional expectations $\operatorname { E } _ { \mathrm { Q } _ { \mu } } [ R | L =$ $\hat { \ell } ]$ and $\operatorname { E } _ { \mathrm { Q } _ { \mu } } [ R L _ { i } | L = \hat { \ell } ] , i = 1 , \dots , n$ according to (3.4) with bandwidth $h ^ { * }$

9. Calculate the estimates for $\mathrm { E } _ { \mathrm { P } } [ L _ { i } \mid L = \mathrm { V a R } _ { \mathrm { P } , \alpha } ( L ) ] , i = 1 , \ldots , n$ according to (4.3), inserting the estimates from the previous step.

## 5 Numerical example

This section is divided into two parts. In Sub-section 5.1 we provide details of the portfolio model that is used for the simulation study and describe the numerical results we seek to obtain. In Sub-section 5.2 we comment on the results and point out their essential features.

## 5.1 Description of simulation study

We examine the performance of importance sampling estimation of VaR contributions under Assumption 4.3. Due to restriction in computational power, the portfolio we consider is relatively small, with 96 assets. Note that, with such a portfolio size, there may be a significant positive probability of not observing any losses, demonstrating that the issue tackled in Lemma 3.4 has some relevance.

<sup>8</sup>The new sample need not necessarily be generated by a new Monte Carlo simulation. Alternatively, as done in Section 5, the new sample can be created from the previous sample by substituting (S<sup>∗</sup>, . . . , S<sup>∗</sup>) from (4.4a) for (S<sub>1</sub>, . . . , S<sub>k</sub>). In this case T = T .

<sup>9</sup>For instance, by ordering the pairs (L<sup>(t)</sup>, R<sup>(t)</sup>) in descending order according to the L-component and selecting the

<!-- page: 10 -->

The dependence structure of the portfolio is determined by four correlated systematic factors $( S _ { 1 } , S _ { 2 } , S _ { 3 } , S _ { 4 } )$ which are each standard normal and are jointly normally distributed with correlation matrix

$$
\left( { \begin{array} { c c c c } { 1 } & { 0 . 7 5 } & { 0 . 0 5 } & { 0 . 0 5 } \\ { 0 . 7 5 } & { 1 } & { 0 . 0 5 } & { 0 . 0 5 } \\ { 0 . 0 5 } & { 0 . 0 5 } & { 1 } & { 0 . 2 5 } \\ { 0 . 0 5 } & { 0 . 0 5 } & { 0 . 2 5 } & { 1 } \end{array} } \right) .\tag{5.1}
$$

According to (5.1), factors $S _ { 1 }$ and $S _ { 2 }$ are strongly correlated, factors $S _ { 3 }$ and $S _ { 4 }$ are moderately correlated, and the pairs $( S _ { 1 } , S _ { 2 } )$ and $( S _ { 3 } , S _ { 4 } )$ are weakly dependent.

Each factor corresponds to one sector that includes 24 assets. In each of the four sectors, the risk characteristics of the 24 assets are specified as shown in Table 1. According to Table 1, each of the four sectors in the portfolio includes 12 high (2%) PD (probability of default) assets and 12 low (0.5%) PD assets. In both of these two sub-sectors there are 4 high exposure (25\$), 4 medium-size exposure (5\$), and 4 low exposure (1\$) assets. Of the 4 high exposure assets, all have equal LGD (loss given default) mean 50% but 2 assets have high LGD variance (12.5%) and 2 assets have low LGD variance (3.125%). Similarly, among the 4 medium-size (low) exposure assets of equal LGD mean, there are 2 high LGD variance and 2 low LGD variance assets. Note that for each combination of sector, PD, exposure, and LGD variance there are two assets with identical risk characteristics. This feature of the portfolio composition is intended to deliver a rough assessment of estimation uncertainty due to the Monte Carlo simulation. For, by symmetry, risk contributions for assets with identical risk characteristics should be equal but will not be when estimated by Monte Carlo simulation.

Assumption 5.1 For any asset $i \in \{ 1 , 2 , \dots , 9 6 \}$ in the portfolio, its individual loss variable $\boldsymbol { L } _ { i }$ in the sense of Assumption 4.3 is specified by the asset’s sector $k ( i ) \in \{ 1 , 2 , 3 , 4 \}$ , probability of default $P D _ { i }$ exposure $v _ { i } ,$ , mean loss given default $L G D _ { i }$ , and $L G D$ variance varLGD (as shown in Table 1) as follows:

The default event of the asset is given by $D _ { i } = \{ \sqrt { r } S _ { k ( i ) } + \sqrt { 1 - r } \xi _ { i } \leq \Phi ^ { - 1 } ( P D _ { i } ) \}$ where Φ denotes the standard normal distribution function, $r = 0 . 1 8$ (equal for all i), and $\xi _ { 1 } , \xi _ { 2 } , \ldots , \xi _ { 9 6 }$ are i.i.d. standard normal.

The loss severity variable is given by $A _ { i } ~ = ~ v _ { i } B _ { i }$ where $B _ { 1 } , B _ { 2 } , \ldots , B _ { 9 6 }$ are independent betadistributed random variables with $\operatorname { E } [ B _ { i } ] = L G D _ { i }$ and var $[ B _ { i } ] = v a r L G D _ { i }$

The constant r in the definition of the default events is the loading of the systematic risk in this model. Its value was chosen with a view on the asset correlations in the Basel II corporate risk weight formula which have a range from 0.12 to 0.24 (BCBS, 2006, paragraph 272). The loss severity distributions of the high LGD variance assets in Assumption 5.1 are U-shaped (beta parameters $a = 0 . 5$ and $b = 0 . 5 )$ , the severity distributions of the low LGD variance assets are bell-shaped (beta parameters $a = 3 . 5$ and $b = 3 . 5 )$ .

By portfolio construction, on the one hand Sectors 1 and 2 are identical with respect to their composition and risk characteristics. On the other hand, this holds also for Sectors 3 and 4. As Sectors 1 and 2 are, however, stronger correlated than Sectors 3 and 4, one should expect that due to this concentration the risk contributions of assets in Sectors 1 or 2 are higher than the risk contributions of the corresponding assets in Sectors 3 or 4.

The simulation exercise<sup>10</sup> we conduct is structured as follows:

1. We run 25 times a Monte Carlo simulation with 50,000 joint realisations of the losses of all the assets in the portfolio.

2. In each simulation run, the following quantities are estimated:

<sup>10</sup>The R-script for the calculations can be down-loaded at http://www-m4.ma.tum.de/pers/tasche/.

<!-- page: 11 -->

Portfolio-wide VaR at 99.9% level (by standard MC and importance sampling MC, see Table 2 for the results).

For each factor, the conditional expectation $\mathrm { E } _ { \mathrm { P } } [ S _ { i } \mid L = \mathrm { V a R } _ { \mathrm { P } , \alpha } ( L ) ]$ of the factor conditional on $L = \operatorname { V a R } _ { \mathrm { P } , \alpha } ( L )$ (by standard MC, Table 3).

For each sector, sector-stand-alone VaR at 99.9% level (by standard MC and importance sampling MC, Table 5).

For each asset, the contribution of the asset to portfolio-wide VaR at 99.9% level (by standard MC and importance sampling MC, Table 7). Additionally, for each asset, the contribution of the asset to portfolio-wide VaR at 99.9% level by importance sampling MC with reduced and enlarged respectively bandwidth for the conditional expectation, Table 8).

3. Based on the estimates of step 2, in each simulation run the following quantities are calculated:

The portfolio-wide mean of the loss, standard deviation of the loss, and the probability of observing a loss<sup>11</sup> (Table 4).

The ratio of the sum of the VaR contributions of all assets and portfolio-wide VaR (Table 6).

For each sector, the contribution of the sector to portfolio-wide VaR at 99.9% level (as the sum of the VaR contributions of the assets in the sector, Table 9).

The portfolio-wide diversification index<sup>12</sup> (Table 10)

$$
\mathrm { I } ( L ) \ = \ { \frac { \mathrm { V a R } _ { \mathrm { P } , \alpha } ( L ) - \mathrm { E } [ L ] } { \sum _ { i = 1 } ^ { n } ( \mathrm { V a R } _ { \mathrm { P } , \alpha } ( L _ { i } ) - \mathrm { E } [ L _ { i } ] ) } } .\tag{5.2a}
$$

For each asset i, the marginal diversification index (Table 11)

$$
\operatorname { I } ( L _ { i } \mid L ) \ = \ { \frac { \operatorname { V a R } _ { \mathrm { P } , \alpha } ( L _ { i } \mid L ) - \operatorname { E } [ L _ { i } ] } { \operatorname { V a R } _ { \mathrm { P } , \alpha } ( L _ { i } ) - \operatorname { E } [ L _ { i } ] } } .\tag{5.2b}
$$

For each sector, its marginal diversification index (defined as the sum of the VaR contributions of the assets in the sector divided by the VaR of the sector, Table 12).

Marginal diversification indices as defined by (5.2b) represent a direct application of risk contri butions for risk concentration analysis. By construction, $\operatorname { I } ( L _ { i } \mid L ) > \operatorname { I } ( L )$ implies that reduction of the exposure to asset i will improve portfolio diversification (Tasche, 2006, Section 4). Here, “diversification” is understood in a relative sense, namely comparing the actual economic capital assigned to the portfolio under consideration to the economic capital assigned to a worst case portfolio composed of co-monotonic loss variables.

4. We report three results for each of the values that is estimated or calculated from estimates:

The result of the first simulation run.

The mean of the results of all 25 simulation runs (as approximation of the true value).

The coeficients of variation<sup>13</sup> of the results of all 25 simulation runs (as measure of estimation uncertainty).

<sup>11</sup>For further reduction of the estimation variance, the standard deviation and sample size of the positive losses for the bandwidth (both for standard MC as well as for importance sampling) according to (3.3) are not estimated but numerically calculated. Under Assumption 5.1 this can be done exactly for the standard deviation of the positive losses and approximately for the sample size of the positive losses, by approximating the distribution of the number of defaults via moment matching by a negative binomial distribution.

<sup>12</sup>See Tasche (2006, Section 4) for a motivation of this definition and the definition of marginal diversification indices. The diversification indices are calculated on an unexpected loss (UL) basis, in accordance with definition (2.2a) of economic capital. Note that the value of the portfolio-wide diversification index depends upon whether the portfolio is decomposed into assets or into sectors since in the latter case the diversification potential is larger.

<sup>13</sup>The coeficient of variation of a sample is defined as the ratio of the sample standard deviation and the sample mean.

<!-- page: 12 -->

## 5.2 Comments on the results

Table 2. With respect to the estimation of portfolio-wide VaR, according to the results displayed in Table 2, there is a minor advantage in using importance sampling. With multi-step importance sampling as suggested for instance by Glasserman and Li (2005) this advantage could be increased. However, the purpose of this paper is to deal with the estimation of VaR contributions. Therefore, here we need not look into the details of eficient estimation of VaR itself. As indicated by the relatively small sample variation coeficients both for standard as well as importance Monte Carlo sampling, the estimates in the first simulation run do not difer much from the means of 25 simulation runs.

Table 3. Table 3 shows that the estimates for the shift constants of the distribution of the systematic factors according to (4.4a) and (4.4b) are not very stable. This is indicated both by the high sample variation coeficients as well as by the 1st run estimate of the constant for the fourth factor which difers much from the sample mean. As the strongly correlated factors 1 and 2 might contribute more to portfolio risk as measured by VaR than the factors 3 and 4, it is no surprise that the indicated shifts of factors 1 and 2 are larger than the ones of factors 3 and 4.

Table 4. The diference between the loss distribution under the original probability measure P and the importance sampling measures is demonstrated by Table 4. The mean loss grows by more than ten times and then slightly overshoots the portfolio VaR under the original probability measure P. The loss standard deviation increases by four times. The proportion of portfolio loss realisations with positive losses grows from 60% to almost 100%. Hence the proportion of the sample that can be used for kernel estimation is much greater in the case of importance sampling. Note that the characteristics of the shift loss distribution do not seem to vary much in the 25 simulation runs.

Table 5. By construction, from a risk perspective the four portfolio sectors are identical when considered stand-alone. This is confirmed by the estimates of stand-alone sector VaR as displayed in Table 5. The significantly higher sample variation coeficients of sectors 3 and 4 in the case of importance sampling show that the shift factor distribution according to (4.4a) and (4.4b) is not very well suited for the estimation of stand-alone sector characteristics.

Table 6. As indicated in Remark 3.1, although in theory the sum of the VaR contributions according to (2.6) equals VaR, a sum of VaR contribution estimates made by kernel estimation can difer from VaR. Table 6 displays for diferent estimation approaches how large the diference can be. In general, it is larger for importance sampling and increases with the kernel estimation bandwidth. As we will see, the choice of the importance sampling bandwidth according to Silverman’s rule of thumb (3.3) seems to be a reasonable compromise between reduction of sample variation by oversmoothing and unbiasedness as measured by the diference between the sum of VaR contributions and VaR. Note that, to make comparable the VaR contribution estimates by diferent approaches, the contributions as displayed in Tables 7, 8, and 9 are normalised such that their sum equals portfolio VaR.

Tables 7 and 8. As by symmetry results for sectors 2 and 4 are not essentially diferent from the results for sectors 1 and 3 respectively, Tables 7 and 8 display the results of VaR contribution estimates at asset level only for sectors 1 and 3. The tables allow to compare the estimation performance as yielded by four diferent approaches: kernel estimation based on standard Monte Carlo sampling, kernel estimation based on importance sampling with bandwidth chosen according to Silverman’s rule of thumb, kernel estimation based on importance sampling with reduced bandwidth, and kernel estimation based on importance sampling with enlarged bandwidth. The average results of all the approaches do not difer too much – which is also a consequence of the normalising applied to have the sum of the contributions equal to portfolio VaR. The variation of the estimates, as indicated by their coeficients of variation, is clearly highest for standard Monte Carlo, followed by importance sampling with 50% of Silverman’s bandwidth. Importance sampling with 200% of Silverman’s bandwidth has lower sample variation than importance sampling with 100% of Silverman’s bandwidth. As noticed above, the latter, however, need not be so much adjusted as the former. For this reason, importance sampling with bandwidth according to Silverman’s rule might be considered the best estimation method for VaR contributions among the four approaches discussed here.

<!-- page: 13 -->

Taking into account that the values in Tables 7 and 8 were calculated on the basis of 25 simulation runs each with 50,000 loss realisations, the results are somewhat disappointing as the sample variation is still large in particular for small exposures with low probability of default. As demonstrated by Figure 1, there is nevertheless a clear gain in estimation eficiency by the application of importance sampling. Additionally, in contrast to the standard Monte Carlo approach, the importance sampling approaches have no problem with seeming zero VaR contributions of some assets (compare the first run results).

Note that the correlation structure of the portfolio is clearly reflected in the VaR contributions as the contributions by assets in sector 1 are significantly higher than the contributions by the assets with similar risk characteristics in sector 3. Note also that LGD variance has a strong impact on an asset’s VaR contribution, in particular for those assets with the high exposures. The greater the LGD variance, the greater the VaR contribution.

Table 9. Table 9 displays at sector level what Table 7 shows at asset level. Compared to the asset level, sample variation at sector level is slightly less. Again, by importance sampling there is some gain in estimation eficiency compared to standard sampling. Note in particular for sector 1 the misleading first run standard estimate of the VaR contribution which seems to indicate that sector 1 is less correlated to the rest of the portfolio than sectors 2, 3, or 4.

Table 10. As demonstrated in Table 10, estimates of portfolio-wide diversification indices in asset and sector context are fairly stable, and there is not much diference in eficiency between standard and importance sampling. The specification of the context in which the diversification indices are calculated indicates the scope of possible actions for a reduction of portfolio concentration. Sector context means that only the relative weights of the sectors may be changed but not relative weights of single assets. Superficially, the sector diversification index looks worse. This is caused by the fact that its denominator

– compared to the asset context – is less because the sector VaR figures already incorporate a lot of diversification. In general, it does not make sense to compare diversification indices that were calculated in diferent contexts. Portfolio-wide diversification indices should rather be compared to the corresponding asset or sector diversification indices because this way guidance can be provided on how to change the portfolio for better diversification.

Table 11. Not surprisingly, as Table 11 shows importance sampling estimates are more eficient than standard sampling estimates also for the estimation of asset-level marginal diversification indices. In particular, importance sampling avoids observing negative diversification indices even in the first run estimates where estimation is much more uncertain than in the “mean of all runs” columns. Note however, that also the importance sampling first run estimates are misleading in so far as they seem to indicate that asset 4 (with low LGD variance) in sector 1 is the most dangerous in the portfolio. In fact, assets 1 and 2 in this sector with same exposure size, PD, and mean LGD are more dangerous – as is correctly shown in columns 4 and 7 of Table 11 – because they have got higher LGD variance. Note also that exposure concentration can “override” concentration caused by correlation. This is illustrated by assets 1 to 4 of sector 3 whose diversification indices are higher than the portfolio-wide index although sector 3 clearly has less correlation to the rest of the portfolio than sectors 1 or 2.

Table 12. Also at sector level the importance sampling estimates of the marginal diversification indices display less variation than the standard sampling estimates. In particular, the standard sampling first run estimate of the index for sector 1 is lower than the portfolio-wide diversification index. The misleading conclusion could be that shifting weight to sector 1 contributes to portfolio diversification, in spite of the strong correlation between sectors 1 and 2. In contrast, the importance sampling first run estimate of the diversification index for sector 1 correctly indicates that the index is larger than the portfolio-wide index. However, it also indicates erroneously that sector 1 is worse for portfolio diversification than sector 2.

<!-- page: 14 -->

## 6 Conclusions

In general, determining VaR contributions in a credit portfolio risk model that involves continuous loss given default rate distributions is a non-trivial task. In the context of the common approach by means of Monte-Carlo simulation, we have discussed how to adapt kernel estimation methods for this problem and how to combine them with importance sampling. Importance sampling, in the form of a shift of the distribution of the systematic factors, is applied here since the variability of the estimates is quite strong, as a consequence of the rare-event character of credit risk realisations.

The numerical example presented in Section 5 illustrates that the gain in estimation eficiency by these methods is significant. It also reveals, however, that the results yielded with these methods are not yet too satisfactory in so far as in particular the variability of estimates of VaR contributions for exposures with very small PDs remains still quite large. It seems worthwhile to analyse in more detail how multistep approaches e.g. by Glasserman et al. (2005) have to be modified for successful application on the estimation of VaR contributions as studied here. Further research on this issue could be useful.

## References

C. Acerbi and D. Tasche. On the coherence of expected shortfall. Journal of Banking & Finance, 26(7): 1487–1503, 2002. BCBS. International Convergence of Capital Measurement and Capital Standards. A Revised Framework, Comprehensive Version. Basel Committee of Banking Supervision, June 2006. A. Dev, editor. Economic Capital: A Practitioner Guide, 2004. Risk Books. E. Epperlein and A. Smillie. Cracking VAR with kernels. RISK, 19(8):70–74, August 2006. P. Glasserman. Measuring Marginal Risk Contributions in Credit Portfolios. Journal of Computational Finance, 9:1–41, 2005. P. Glasserman, W. Kang, and P. Shahabuddin. Fast simulation of multifactor portfolio credit risk. Working paper, Columbia University, 2005. P. Glasserman and J. Li. Importance sampling for portfolio credit risk. Management Science, 51(11): 1643–1656, 2005. C. Gouri´eroux, J. P. Laurent, and O. Scaillet. Sensitivity analysis of values at risk. Journal of Empirical Finance, 7:225–245, 2000. C. Gouri´eroux and W. Liu. Eficient portfolio analysis using distortion risk measures. Les Cahiers du CREF 06-35, 2006. M. Kalkbrener. An axiomatic approach to capital allocation. Mathematical Finance, 15(3):425–437, 2005. M. Kalkbrener, H. Lotter, and L. Overbeck. Sensible and eficient allocation for credit portfolios. RISK, 17:S19–S24, January 2004. F. C. Klebaner. Introduction to Stochastic Calculus with Applications. Imperial College Press, second edition, 2005.

<!-- page: 15 -->

G. Lemus. Portfolio Optimization with Quantile-based Risk Measures. PhD thesis, Sloan School of Management, MIT, 1999. R. Litterman. Hot spots<sup>TM</sup> and hedges. The Journal of Portfolio Management, 22:52–75, 1996. H. Mausser and D. Rosen. Allocating credit capital with var contributions. Working paper, Algorithmics Inc., 2004. A. McNeil, R. Frey, and P. Embrechts. Quantitative Risk Management. Princeton University Press, 2005. S. Merino and M. A. Nyfeler. Applying importance sampling for estimating coherent credit risk contri butions. Quantitative Finance, 4:199–207, 2004. A. Pagan and A. Ullah. Nonparametric econometrics. Cambridge University Press, 1999. D. Tasche. Risk contributions and performance measurement. Working paper, Technische Universit¨at M¨unchen, 1999. D. Tasche. Capital Allocation with CreditRisk<sup>+</sup>. In V. M. Gundlach and F. B. Lehrbass, editors, CreditRisk<sup>+</sup> in the Banking Industry, pages 25–44. Springer, 2004. D. Tasche. Measuring sectoral diversification in an asymptotic multifactor framework. Journal of Credit Risk, 2(3):33–55, 2006. Y. Yamai and T. Yoshiba. Comparative Analyses of Expected Shortfall and VaR: their estimation error, decomposition, and optimization. Monetary and economic studies 20(1), Bank of Japan, 2002.

[Table source crop](assets/tables/2008-tasche-capital-allocation-kernel-estimators-p0015-block-0002-0ac4b6bd274160cf.jpg)
Table 1: Risk characteristics of assets. Identical for all four sectors.

<!-- page: 16 -->

[Table source crop](assets/tables/2008-tasche-capital-allocation-kernel-estimators-p0016-block-0001-4df9c9805a6c6e3f.jpg)
Table 2: Standard Monte Carlo and importance sampling estimates of portfolio VaR at 99.9% level and coeficients of variation of estimates.

[Table source crop](assets/tables/2008-tasche-capital-allocation-kernel-estimators-p0016-block-0002-8ba165de13f98736.jpg)
Table 3: Standard Monte Carlo estimates of conditional expectations of systematic factors conditional on “Loss equals portfolio VaR at 99.9% level” and coeficients of variation of estimates.

[Table source crop](assets/tables/2008-tasche-capital-allocation-kernel-estimators-p0016-block-0003-4bbd447e3abfdab9.jpg)
Table 4: Portfolio loss distribution characteristics mean of loss, standard deviation of loss, and probability of observing positive losses for original and importance sampling distribution. Characteristics for original distribution are calculated without simulation only once before the 1st simulation run.

[Table source crop](assets/tables/2008-tasche-capital-allocation-kernel-estimators-p0016-block-0004-72dce52218f65a43.jpg)
Table 5: Standard Monte Carlo and importance sampling estimates of stand-alone sector-VaR at 99.9% level and coeficients of variation of estimates.

[Table source crop](assets/tables/2008-tasche-capital-allocation-kernel-estimators-p0016-block-0005-6a1e76cb4d4ad88b.jpg)
Table 6: Ratio of sum of asset VaR contributions and portfolio-wide VaR (at 99.9% level) for Standard Monte Carlo, importance sampling, importance sampling with 50% of bandwidth, and importance sampling with 200% of bandwidth.

<!-- page: 17 -->

[Table source crop](assets/tables/2008-tasche-capital-allocation-kernel-estimators-p0017-block-0001-95014c34614b1301.jpg)
Table 7: Standard Monte Carlo and importance sampling estimates of asset contributions to portfolio-wide VaR at 99.9% level and coeficients of variation of estimates. Only sectors 1 and 3. See Figure 1 for a graphical comparison of the coeficients of variation.

<!-- page: 18 -->

![Sector 1: Coefficients of variation of VaR contribution estimates](assets/figures/2008-tasche-capital-allocation-kernel-estimators-p0018-block-0001-fdbff527edb4c521.jpg)

![Sector 3: Coefficients of variation of VaR contribution estimates](assets/figures/2008-tasche-capital-allocation-kernel-estimators-p0018-block-0002-8d40df491b4e7e72.jpg)

<!-- page: 19 -->

[Table source crop](assets/tables/2008-tasche-capital-allocation-kernel-estimators-p0019-block-0001-c175ee10f79531b0.jpg)
Table 8: Importance sampling estimates with half and double of bandwidth according to (3.3) for asset contributions to portfolio-wide VaR at 99.9% level and coeficients of variation of estimates. Only sectors 1 and 3.

<!-- page: 20 -->

[Table source crop](assets/tables/2008-tasche-capital-allocation-kernel-estimators-p0020-block-0001-6507d1823f5b75e4.jpg)
Table 9: Standard Monte Carlo and importance sampling estimates of sector contributions to VaR at 99.9% level and coeficients of variation of estimates.

[Table source crop](assets/tables/2008-tasche-capital-allocation-kernel-estimators-p0020-block-0002-45198346079862c4.jpg)
Table 10: Standard Monte Carlo and importance sampling estimates of portfolio-wide diversification index with respect to VaR at 99.9% level, in asset-level and sector-level context, and coeficients of variation of estimates.

<!-- page: 21 -->

[Table source crop](assets/tables/2008-tasche-capital-allocation-kernel-estimators-p0021-block-0001-7137a19225363e17.jpg)
Table 11: Standard Monte Carlo and importance sampling estimates of marginal diversification indices at asset-level with respect to portfolio-wide VaR at 99.9% level and coeficients of variation of estimates. Only sectors 1 and 3.

<!-- page: 22 -->

[Table source crop](assets/tables/2008-tasche-capital-allocation-kernel-estimators-p0022-block-0001-0480e12eb8d4795b.jpg)
Table 12: Standard Monte Carlo and importance sampling estimates of diversification indices at sector-level with respect to portfolio-wide VaR at 99.9% level and coeficients of variation of estimates.
