# 1996-broadie-glasserman-security-price-derivatives

<!-- page: 1 -->

## Estimating Security Price Derivatives Using Simulation

Mark Broadie<sup>∗</sup>

Paul Glasserman<sup>∗</sup>

October 20, 1993

Revised: July 8, 1994

## Abstract

Simulation has proved to be a valuable tool for estimating security prices for which simple closed form solutions do not exist. In this paper we present two direct methods, a pathwise method and a likelihood ratio method, for estimating derivatives of security prices using simulation. With the direct methods, the information from a single simulation can be used to estimate multiple derivatives along with a security’s price. The main advantage of the direct methods over re-simulation is increased computational speed. Another advantage is that the direct methods give unbiased estimates of derivatives, whereas the estimates obtained by resimulation are biased. Computational results are given for both direct methods and compar isons are made to the standard method of re-simulation to estimate derivatives. The methods are illustrated for a path independent model (European options), a path dependent model (Asian options), and a model with multiple state variables (options with stochastic volatility).

Keywords: Simulation, derivative estimation, security pricing, option pricing.

<sup>∗</sup>Both authors are at the Graduate School of Business, Columbia University, New York, NY, 10027, USA.

<!-- page: 2 -->

## 1. Introduction

In this paper two direct methods for estimating security price derivatives using Monte Carlo simulation are presented, a pathwise method and a likelihood ratio method. The standard indirect method of estimating a security price derivative is re-simulation. In this approach, an initial simulation is run to determine a base price, then the parameter of interest is perturbed and another simulation is run to determine a perturbed price. The estimate of the derivative is the diference in the simulated prices divided by the parameter perturbation. The direct methods proposed in this paper ofer increased computational speed, in that they avoid the need to run additional simulations. The output from the initial simulation contains considerable information that can be used to estimate security price derivatives directly. This advantage becomes more pronounced as the number of derivatives to be estimated increases. While the re-simulation approach requires one additional simulation run for each derivative to be estimated, the direct methods require information only from the initial simulation run. A second advantage of the direct methods is that they give unbiased estimates of derivatives, whereas the re-simulation estimates are generally biased.

Boyle (1977) proposed the use of Monte Carlo simulation for estimating security prices. Since that time, simulation has proved to be a valuable tool in many situations where other tools are not available or are not practical to implement. For example, simulation is useful for estimating security prices when there is no analytical expression for the terminal distribution of the security price, when there are multiple state variables, and when there are path dependent payofs. Simulation has been used to estimate prices of contingent claims, prices of mortgage backed securities, and to value swaps. Simulation is generally not appropriate for valuing American-style contingent claims, i.e., securities with opportunities for optimal early exercise. A complete survey of successful applications of the simulation approach would be too extensive to include here. However, for a brief sampling of the literature the reader is referred to Boyle (1977), Hull and White (1987), Johnson and Shanno (1987), Jones and Jacobs (1986), Kemna and Vorst (1990), Schwartz and Torous (1989), and Smith, Smithson, and Wilford (1990).

The focus of this paper is using simulation to estimate security price derivatives. Derivative information is of practical and theoretical importance. For practitioners, derivative information is important for hedging, i.e., for reducing the risk of a security or portfolio of securities, when closing the position is not practical or desirable. For example, the derivative of an option price with respect to the price of the underlying security (i.e., the delta) indicates the number of units of the security to hold in the hedge portfolio. The corresponding second derivative (i.e., the gamma) is related to the optimal time interval required for rebalancing a hedge under transactions costs. Other derivative information is useful for protecting against changes in the associated parameters, e.g., changes in volatility, time to maturity, or interest rates. On the theoretical side, Breeden and Litzenberger (1978) show that the second derivative with respect to the strike price can be interpreted as a state price density. Carr (1993) shows how first and higher order derivatives of an option’s price with respect to the initial price of the underlying security can be viewed as an expectation, under an appropriate change of measure, of the corresponding derivative at the terminal date.

<!-- page: 3 -->

To estimate derivatives via simulation, two direct methods are investigated. The pathwise method is based on the relationship between the security payof and the parameter of interest. Diferentiating this relationship leads, under appropriate conditions, to an unbiased estimator for the derivative of the security price. In contrast, the likelihood ratio method, is based on the relationship between the probability density of the price of the underlying security and the parameter of interest. These methods have been studied in the discrete-event simulation literature, but have not received much attention in financial applications. Fu and Hu (1993b) also derive pathwise derivative estimates in the case of a European call option on a single underlying asset and illustrate their use in optimization. For an overview of the pathwise method, see Glasserman (1991), and for the likelihood ratio method (also called the score function method) see Glynn (1987) and Rubinstein and Shapiro (1993).

The direct methods are described in detail through an example in Section 2. For ease of exposition, the example chosen in Section 2 is a European option on a dividend paying asset, an example for which simulation is not required. While both direct methods lead to unbiased estimators, they difer in their efectiveness and scope of applicability. Second derivative estimators are developed in Section 3. Computational comparisons of the two direct methods and the indirect re-simulation method are given in Section 4. To illustrate a range of applications, the examples in Section 4 include Asian options (path dependent payofs) and options in a stochastic volatility setting (multiple state variables). Concluding remarks are given in Section 5. Detailed formulas and technical results are given in the appendices.

## 2. Derivative Estimates for European Call Options

In this section, the pathwise and likelihood ratio methods are developed for estimating sensitivities of security prices through simulation. For expository purposes, the two methods are introduced through a simple example — one for which simulation is not required. Consider the price p of a European call option on a dividend paying asset that follows a lognormal difusion. In particular, assume that the risk neutralized price of the underlying asset, S<sub>t</sub>,

<!-- page: 4 -->

satisfies the stochastic diferential equation

$$
d S _ { t } = S _ { t } [ ( r - \delta ) d t + \sigma d B _ { t } ] ,\tag{1}
$$

where $B _ { t }$ is a standard Brownian motion process (see Hull (1992) for a general discussion of this model). In equation (1), r is the riskless interest rate, δ is the dividend rate, and $\sigma > 0$ is the volatility parameter. Under the risk neutral measure, ln $( S _ { T } / S _ { 0 } )$ is normally distributed with mean $( r - \delta - \sigma ^ { 2 } / 2 ) T$ and variance $\sigma ^ { 2 } T$ . The option has a strike price of K and matures at time $T > 0$ , with the current time taken to be $t = 0$ . In this “Black-Scholes world”, the option price is given by

$$
p = E [ e ^ { - r T } \operatorname* { m a x } ( S _ { T } - K , 0 ) ] .\tag{2}
$$

Throughout the paper, E denotes the expectation operator under the risk neutral measure. See Harrison and Kreps (1979) for a justification of this pricing formula.

## Pathwise Derivatives

To illustrate the application of the first method, we consider the problem of estimating vega, which is dp/dσ. We do this by defining the discounted payof

$$
P = e ^ { - r T } \operatorname* { m a x } ( S _ { T } - K , 0 ) ,\tag{3}
$$

(so that $p = E [ P ] )$ and examining how changes in σ determine changes in P. Since $\sigma$ afects P only through $S _ { T }$ , we begin by examining the dependence of $S _ { T }$ on $\sigma$

The lognormal random variable $S _ { T }$ can be represented as

$$
S _ { T } = S _ { 0 } e ^ { ( r - \delta - \frac { 1 } { 2 } \sigma ^ { 2 } ) T + \sigma \sqrt { T } Z } ,\tag{4}
$$

where $Z$ is a standard normal random variable. Consequently,

$$
\begin{array} { l } { \displaystyle { \frac { d S _ { T } } { d \sigma } = S _ { T } ( - \sigma T + \sqrt { T } Z ) } } \\ { \displaystyle { ~ = \frac { S _ { T } } { \sigma } [ \ln ( S _ { T } / S _ { 0 } ) - ( r - \delta + \frac { 1 } { 2 } \sigma ^ { 2 } ) T ] . } } \end{array}\tag{5}
$$

This tells us how a small change in σ afects $S _ { T }$ . Now consider the efect on P of a small change in $S _ { T }$ . If $S _ { T } \geq K$ , then the option is in the money and any increase $\Delta$ in $S _ { T }$ translates into an increase $e ^ { - r T } \Delta$ in P. If, however, $S _ { T } < K$ , then $P = 0$ , and P remains 0 for all suficiently small changes in $S _ { T }$ ∆<sub>. Thus, we arrive at the</sub> f<sub>ormal expression</sub>

$$
\frac { d P } { d S _ { T } } = e ^ { - r T } 1 _ { \{ S _ { T } \geq K \} } ,\tag{6}
$$

<!-- page: 5 -->

in which $1 _ { \{ \cdot \} }$ denotes the indicator of the event in braces.<sup>1</sup> Combining (5) and (6) gives

$$
\begin{array} { l } { \displaystyle { \frac { d P } { d \sigma } = \frac { d P } { d S _ { T } } \frac { d S _ { T } } { d \sigma } } } \\ { \displaystyle { \quad \quad = e ^ { - r T } 1 _ { \{ S _ { T } \geq K \} } \frac { S _ { T } } { \sigma } [ \ln ( S _ { T } / S _ { 0 } ) - ( r - \delta + \frac 1 2 \sigma ^ { 2 } ) T ] . } } \end{array}\tag{7}
$$

Each of the terms in this expression is easily evaluated in a simulation, making the estimator $d P / d \sigma$ easy to use. Moreover, it follows from Proposition 1 in Appendix A that this estimator is unbiased, i.e.,

$$
E [ { \frac { d P } { d \sigma } } ] = { \frac { d p } { d \sigma } } .
$$

A similar argument leads to an estimator of delta, the derivative of the option price with respect to the initial price of the underlying asset. Much as before, we have

$$
\begin{array} { l } { \displaystyle { \frac { d P } { d S _ { 0 } } = \frac { d P } { d S _ { T } } \frac { d S _ { T } } { d S _ { 0 } } } } \\ { \displaystyle { ~ = e ^ { - r T } 1 _ { \{ S _ { T } \geq K \} } \frac { d S _ { T } } { d S _ { 0 } } . } } \end{array}\tag{8}
$$

Furthermore, from (4) we find that

$$
\frac { d S _ { T } } { d S _ { 0 } } = e ^ { ( r - \delta - \frac { 1 } { 2 } \sigma ^ { 2 } ) T + \sigma \sqrt { T } Z } = \frac { S _ { T } } { S _ { 0 } } .
$$

Substituting this into (8), we arrive at the estimator

$$
{ \frac { d P } { d S _ { 0 } } } = e ^ { - r T } 1 _ { \{ S _ { T } \geq K \} } { \frac { S _ { T } } { S _ { 0 } } } .\tag{9}
$$

This estimator is also unbiased, i.e.,

$$
E [ \frac { d P } { d S _ { 0 } } ] = \frac { d p } { d S _ { 0 } } .
$$

Similar arguments can be used to develop derivative estimates for options with path dependencies, for which simulation is often the only available computational approach (see Section 4).

## Derivatives Based on Likelihood Ratios

The second method of estimating derivatives puts the dependence on the parameter of interest in an underlying probability density, rather than in a random variable. We continue with the European option example. It follows from (4) that under the risk neutral measure, the density of $S _ { T }$ is

$$
g ( x ) = \frac { 1 } { x \sigma \sqrt { T } } n ( d ( x ) ) , \quad x \geq 0 ,\tag{10}
$$

<sup>1</sup> Equation (6) is valid if interpreted as a righthand derivative or as the almost everywhere defined derivative of a Lipschitz function. Technical issues of this type are treated in Appendix A.

<!-- page: 6 -->

where $\begin{array} { r } { n ( z ) = \frac { 1 } { \sqrt { 2 \pi } } e ^ { - z ^ { 2 } / 2 } } \end{array}$ is the standard normal density and

$$
d ( x ) = { \frac { \ln ( x / S _ { 0 } ) - ( r - \delta - { \frac { 1 } { 2 } } \sigma ^ { 2 } ) T } { \sigma { \sqrt { T } } } } .\tag{11}
$$

Thus, we can write (2) as

$$
p = \int _ { 0 } ^ { \infty } e ^ { - r T } \operatorname* { m a x } ( x - K , 0 ) g ( x ) d x .\tag{12}
$$

We now use this representation of $p$ to derive derivative estimates. We begin by considering $d p / d \sigma$ . Notice that in (12), $\sigma$ appears only as an argument of $g .$ . Assuming we can interchange the derivative and integral, (12) implies that

$$
\frac { d p } { d \sigma } = \int _ { 0 } ^ { \infty } e ^ { - r T } \operatorname* { m a x } ( x - K , 0 ) \frac { \partial g ( x ) } { \partial \sigma } d x .\tag{13}
$$

Multiplying and dividing the integrand in (13) by $g ( x )$ and using the identity $( \partial g / \partial \sigma ) / g =$ ∂ ln $g / \partial \sigma$ , gives

$$
\begin{array} { l } { \displaystyle \frac { d p } { d \sigma } = \int _ { 0 } ^ { \infty } e ^ { - r T } \operatorname* { m a x } ( x - K , 0 ) \frac { \partial \ln ( g ( x ) ) } { \partial \sigma } g ( x ) d x } \\ { \displaystyle \qquad = E \big [ e ^ { - r T } \operatorname* { m a x } ( S _ { T } - K , 0 ) \frac { \partial \ln ( g ( S _ { T } ) ) } { \partial \sigma } \big ] . } \end{array}
$$

This indicates that the likelihood ratio estimator

$$
e ^ { - r T } \operatorname* { m a x } ( S _ { T } - K , 0 ) \frac { \partial \ln ( g ( S _ { T } ) ) } { \partial \sigma }\tag{14}
$$

is an unbiased estimator of $d p ,$ /dσ when $S _ { T }$ is simulated under the risk neutral measure. The estimator in (14) is easily implemented using the formula

$$
\frac { \partial \ln ( g ( x ) ) } { \partial \sigma } = - d \frac { \partial d } { \partial \sigma } - \frac { 1 } { \sigma } ,\tag{15}
$$

where d is given in (11) and

$$
\frac { \partial d } { \partial \sigma } = \frac { \ln ( S _ { 0 } / x ) + ( r - \delta + \frac { 1 } { 2 } \sigma ^ { 2 } ) T } { \sigma ^ { 2 } \sqrt { T } } .
$$

A similar argument provides an estimator of the derivative with respect to the initial asset price. Proceeding just as before, we arrive at the equation

$$
\frac { d p } { d S _ { 0 } } = E \big [ e ^ { - r T } \operatorname* { m a x } ( S _ { T } - K , 0 ) \frac { \partial \ln ( g ( S _ { T } ) ) } { \partial S _ { 0 } } \big ] ,
$$

and hence obtain the unbiased likelihood ratio estimator

$$
e ^ { - r T } \operatorname* { m a x } ( S _ { T } - K , 0 ) \frac { \partial \ln ( g ( S _ { T } ) ) } { \partial S _ { 0 } } ,\tag{16}
$$

where

$$
\begin{array} { l } { \displaystyle \frac { \partial \ln ( g ( x ) ) } { \partial S _ { 0 } } = \frac { d ( x ) } { S _ { 0 } \sigma \sqrt { T } } } \\ { \displaystyle = \frac { \ln ( x / S _ { 0 } ) - ( r - \delta - \frac { 1 } { 2 } \sigma ^ { 2 } ) T } { S _ { 0 } \sigma ^ { 2 } T } . } \end{array}
$$

The estimator in (16) is easily used in a simulation of $S _ { T }$

<!-- page: 7 -->

## Discussion

We have seen through the European call option example that it is sometimes possible to obtain estimates of derivatives of security prices without re-simulation. The same methods apply when closed form expressions are not available and simulation is necessary. In general, the estimators obtained through the pathwise method and the likelihood ratio method are not the same. Numerical comparisons are presented in Section 4. At this point, we make some general observations about direct methods compared with re-simulation and the scope of the methods discussed above.

Both pathwise derivative estimates and estimates based on likelihood ratios require an interchange of a derivative and an integral (expectation) for unbiasedness. It is largely this requirement that limits their scope, though the limitation is rarely an issue with standard pricing models. Classical conditions for this interchange require fairly strong smoothness conditions on the integrand; see, e.g., Franklin (1944), pp. 150–151. These conditions are typically satisfied by the probability densities arising in applications of the likelihood ratio method to pricing models. Indeed, the density in (10) is continuously diferentiable in each of its parameters on its domain. In contrast, the pathwise dependence of the payof of a derivative security may not be smooth. For example, the expression in (3) is continuous in $S _ { T }$ but fails to be diferentiable at the point $S _ { T } = K$ . As a consequence, somewhat greater care is required with this method in justifying the interchange of derivative and integral. As a rough rule of thumb, if the payof is continuous, the pathwise method is typically applicable; see Appendix A for a more precise discussion.

Since smoothness is rarely a problem for densities, the main limitation in the application of the likelihood ratio method is that the parameter of interest may not be a parameter of the density at all. This is the case with the strike price in (2); the likelihood ratio method does not apply to this parameter (except possibly through a change of variables). The pathwise method, however, easily covers this case.

It is important to note that the derivation of the likelihood ratio estimator (14) did not make use of any properties of the dependence of the option payof on the underlying asset price. That is, the particular form of (3) was not important, except for the fact that it displays no explicit dependence on $\sigma _ { \cdot }$ . As a consequence, essentially the same estimator applies to any derivative security. If the discounted payof associated with some security is $f ,$ meaning that its price is given by $p = E [ f ( S _ { T } ) ]$ , then its derivative with respect to $\sigma$ is given by

$$
\frac { d p } { d \sigma } = E \big [ f ( S _ { T } ) \frac { \partial \ln ( g ( S _ { T } ) ) } { \partial \sigma } \big ] ,
$$

subject only to the validity of the interchange of derivative and integral. This contrasts markedly with the pathwise method, which depends in an essential way on the form of the payof. Using the pathwise method, one must derive a diferent estimator for each payof function. On one hand, this distinction represents an implementation advantage for the likelihood ratio method; on the other hand, it suggests that the pathwise method is better able to exploit the structure of individual problems.

<!-- page: 8 -->

## 3. Second Derivatives

The gamma of an option, i.e., the second derivative with respect to the initial price of the underlying security, is related to the optimal time interval required for rebalancing a hedge under transactions costs. In this section the direct methods are extended to the estimation of second derivatives.

## Pathwise Second Derivative Estimators

We begin our discussion by considering the simple (if artificial) case of an exponential payof. Suppose that the payof of a contingent claim is $e ^ { - S _ { T } }$ when the final price of the underlying security is $S _ { T }$ . Then the value of this claim today is

$$
p = E [ e ^ { - r T } e ^ { - S _ { T } } ] .
$$

Consider the second derivative of $p$ with respect to the initial price $S _ { 0 }$ . Diferentiating twice inside the expectation gives

$$
\frac { d ^ { 2 } p } { d S _ { 0 } ^ { 2 } } = E \left[ e ^ { - r T } e ^ { - S _ { T } } \left\{ \left( \frac { d S _ { T } } { d S _ { 0 } } \right) ^ { 2 } - \frac { d ^ { 2 } S _ { T } } { d S _ { 0 } ^ { 2 } } \right\} \right] .
$$

From (4), we find that $d S _ { T } / d S _ { 0 } = S _ { T } / S _ { 0 }$ and $d ^ { 2 } S _ { T } / d S _ { 0 } ^ { 2 } = 0$ . Making these substitutions, we get

$$
\frac { d ^ { 2 } p } { d S _ { 0 } ^ { 2 } } = E \left[ e ^ { - r T } e ^ { - S _ { T } } \left( \frac { S _ { T } } { S _ { 0 } } \right) ^ { 2 } \right] .
$$

Now let $p$ once again be the European option price in (2). From (9) we have

$$
\frac { d p ( S _ { 0 } ) } { d S _ { 0 } } = E [ e ^ { - r T } \big ( \frac { S _ { T } ( S _ { 0 } ) } { S _ { 0 } } \big ) 1 _ { \{ S _ { T } ( S _ { 0 } ) \geq K \} } ] ,\tag{17}
$$

where the dependence of $S _ { T }$ on $S _ { 0 }$ is made explicit. Consider a small increase h in $S _ { 0 }$ . Since the ratio $S _ { T } / S _ { 0 }$ does not depend on $S _ { 0 }$ , we get

$$
\begin{array} { l } { \displaystyle \frac { d p ( S _ { 0 } + h ) } { d S _ { 0 } } - \frac { d p ( S _ { 0 } ) } { d S _ { 0 } } = E [ e ^ { - r T } \big ( \frac { S _ { T } } { S _ { 0 } } \big ) ( 1 _ { \{ S _ { T } ( S _ { 0 } + h ) \geq K \} } - 1 _ { \{ S _ { T } ( S _ { 0 } ) \geq K \} } ) ] } \\ { \displaystyle \qquad = E [ e ^ { - r T } \big ( \frac { S _ { T } } { S _ { 0 } } \big ) 1 _ { \{ S _ { T } ( S _ { 0 } + h ) \geq K > S _ { T } ( S _ { 0 } ) \} } ] } \\ { \displaystyle \qquad = E [ e ^ { - r T } \big ( \frac { S _ { T } } { S _ { 0 } } \big ) 1 _ { \{ S _ { T } ( S _ { 0 } ) + \frac { d S _ { T } ( S _ { 0 } ) } { d S _ { 0 } } h \geq K > S _ { T } ( S _ { 0 } ) \} } ] . } \end{array}
$$

<!-- page: 9 -->

Dividing by h and letting h decrease to zero, the expectation becomes concentrated at $S _ { T } = K$ Using $d S _ { T } ( S _ { 0 } ) / d S _ { 0 } = S _ { T } / S _ { 0 }$ , this gives<sup>2</sup>

$$
\begin{array} { r } { \frac { d ^ { 2 } p } { d S _ { 0 } ^ { 2 } } = e ^ { - r T } \big ( \frac { K } { S _ { 0 } } \big ) ^ { 2 } g ( K ) } \\ { = e ^ { - \delta T } \frac { n ( d _ { 1 } ( K ) ) } { S _ { 0 } \sigma \sqrt { T } } , } \end{array}\tag{18}
$$

where $\begin{array} { r } { d _ { 1 } ( x ) = [ \ln ( S _ { 0 } / x ) + ( r - \delta + \frac { 1 } { 2 } \sigma ^ { 2 } ) T ] / ( \sigma \sqrt { T } ) = - d ( x ) + \sigma \sqrt { T } . ^ 3 } \end{array}$ Expression (18) involves no random quantities and thus requires no simulation. Indeed, the result is the well known formula for the gamma of an option, which is usually derived without reference to simulation (see, e.g., Hull (1992), p. 312). The efect of the expectation in (17) is to “smooth” the indicator function. We will see in Section 4 that similar smoothing arguments result in nontrivial second derivative estimators in settings where no closed form expression exists.

## Likelihood Ratio Second Derivative Estimators

Consider again the problem of estimating the second derivative of $p$ in (2) with respect to the initial asset price $S _ { 0 }$ . Starting from (12) and diferentiating twice under the integral gives

$$
\frac { d ^ { 2 } p } { d S _ { 0 } ^ { 2 } } = \int _ { 0 } ^ { \infty } e ^ { - r T } \mathrm { m a x } ( x - K , 0 ) \frac { \partial ^ { 2 } g ( x ) } { \partial S _ { 0 } ^ { 2 } } d x .
$$

Multiplying and dividing the integrand by $g ( x )$ turns the integral into an expectation and yields

$$
\frac { d ^ { 2 } p } { d S _ { 0 } ^ { 2 } } = E \big [ e ^ { - r T } \operatorname* { m a x } ( S _ { T } - K , 0 ) \frac { \partial ^ { 2 } g ( S _ { T } ) } { \partial S _ { 0 } ^ { 2 } } \frac { 1 } { g ( S _ { T } ) } \big ] .
$$

The expression

$$
e ^ { - r T } \operatorname* { m a x } ( S _ { T } - K , 0 ) \frac { \partial ^ { 2 } g ( S _ { T } ) } { \partial S _ { 0 } ^ { 2 } } \frac { 1 } { g ( S _ { T } ) }
$$

is thus an unbiased likelihood ratio estimator of the second derivative. The estimator can be written more explicitly using

$$
\frac { \partial ^ { 2 } g ( S _ { T } ) } { \partial S _ { 0 } ^ { 2 } } \frac { 1 } { g ( S _ { T } ) } = \frac { d ^ { 2 } - d \sigma \sqrt { T } - 1 } { S _ { 0 } ^ { 2 } \sigma ^ { 2 } T } ,
$$

where $d = d ( S _ { T } )$ is given in (11).

d<sup>2</sup>p dS<sup>2</sup><sub>0</sub> = E[e<sup>−rT</sup>  S<sub>T</sub> S<sub>0</sub>  ∂S<sub>0</sub> ∂ 1{ST(S0)≥K}] = e<sup>−rT</sup>  S<sub>0</sub> K 2 g(K).

<sup>2</sup> The same result can be derived in another way. Taking the derivative of (17) again with respect to S<sub>0</sub> gives

The second equality uses d1<sub>{ST(S )≥K}</sub>/dS<sub>0</sub> = δ(K)dS<sub>T</sub>/dS<sub>0</sub> = δ(K)S<sub>T</sub>/S<sub>0</sub>, where δ(·) represents the Dirac delta function. This type of argument is used in Carr (1993) in a diferent context.

<sup>3</sup> The last equality in equation (18) follows from the identity e<sup>−δT</sup> n(d<sub>1</sub>(K)) = e<sup>−rT</sup> (K/S<sub>0</sub>)n(d(K)).

<!-- page: 10 -->

## 4. Computational Results

This section presents computational comparisons of the two direct methods and the indirect re-simulation method through three examples. The first example involves path independent claims, in particular, European options on dividend paying assets. To illustrate the methods on path dependent claims, derivatives of Asian option prices (i.e., options based on an arithmetic average price) are computed in the second example. To illustrate the methods on a model with multiple state variables, derivatives for options with stochastic volatility are computed in the third example.

The re-simulation method is described next. Suppose that the security price p depends on a parameter θ and the goal is to estimate $d p / d \theta$ at $\theta = \theta _ { 0 }$ . Denote the simulation estimator of the price at $\theta \ : = \ : \theta _ { 0 }$ by $P ( \theta _ { 0 } )$ . The simulation estimate of the price is the sample average over independent outcomes of $P ( \theta _ { 0 } )$ . In the re-simulation method, the parameter is perturbed to $\theta _ { 1 } = \theta _ { 0 } + h$ and the new simulation price estimator $P ( \theta _ { 1 } )$ is computed. The re-simulation estimator of the derivative is the forward finite diference $( P ( \theta _ { 1 } ) - P ( \theta _ { 0 } ) ) / h$ The re-simulation estimate is the average over all trials of this estimator. The choice of h is discussed in Appendix B. The importance of using common random numbers for both estimators is also discussed in Appendix B. To estimate a second derivative, the parameter is perturbed to $\theta _ { - 1 } = \theta _ { 0 } - h$ and the new simulation price estimator $P ( \theta _ { - 1 } )$ is computed. The resimulation estimator of the second derivative $d ^ { 2 } p / d \theta ^ { 2 }$ at $\theta = \theta _ { 0 }$ is the central finite diference $( P ( \theta _ { - 1 } ) - 2 P ( \theta _ { 0 } ) + P ( \theta _ { 1 } ) ) / h ^ { 2 }$

An advantage of re-simulation compared with the direct methods is that it involves no programming efort beyond what is required for the pricing simulation itself. But this justification seems weak compared with the advantages of the direct estimators. The direct methods provide unbiased estimators whereas re-simulation inherits the bias that results from finite diference approximation to the derivative. Even more important is the fact that the computational savings with direct methods increases with the number of derivatives estimated. Estimating finite diferences with respect to n parameters requires $n + 1$ simulations. All n derivatives can be estimated from a single simulation using the direct methods. Thus, they ofer a potential $( n + 1 )$ -to-one computational advantage. Many simulation runs are needed to solve for the implied value of a parameter given a security price. In this case, the use of direct estimators of derivatives can lead to significant computational savings. The actual magnitude of the savings depends on the additional computational efort to use a derivative estimate compared to the cost of an additional simulation. Ordinarily, the cost of the former is small relative to the latter. In the first example, however, each trial of the simulation requires only one random number, so the computational savings are not as great.

<!-- page: 11 -->

Variance reduction techniques that apply to the original simulation estimator of a security price can often be used with the three simulation methods for estimating derivatives. In our examples, the control variate method was used to reduce the variance of the estimates. Further discussion of this technique is given at the end of this section.

## Example 1: European Options on Dividend Paying Assets

For European options on dividend paying assets, explicit expressions for all derivatives are available. For completeness these expressions are given in Proposition 2 in Appendix C. The pathwise estimators and the likelihood ratio estimators are summarized in Propositions 3 and 4, respectively, in Appendix C. These are derived using the arguments in Sections 2 and 3.

Table 1 contains simulation results for this example. Several points are noteworthy from Table 1. First, the simulation estimates are within two standard errors of the exact values. Second, the re-simulation method gives point estimates and standard errors that are almost identical to the pathwise method. One exception is the estimate of gamma, where the pathwise estimate gives an exact result in this case. The use of a small perturbation parameter h leads to biases in the re-simulation method that are too small to detect in the results. Third, the standard errors with the likelihood ratio method are typically 1.5 to 4 times greater than the pathwise and re-simulation standard errors. The larger standard errors are likely due to the likelihood ratio estimators not depending on the form of the security payof.

The efectiveness of control variates seems quite sensitive to the estimator with which they are used. With pathwise estimates, the reduction in the estimated standard error is roughly 30-50%, and is very close to the corresponding reduction for the re-simulation estimates. In most cases, the impact on the likelihood ratio estimates is somewhat less. However, it is possible that a diferent control variate would yield diferent results.

Why do the re-simulation and pathwise methods give nearly identical results in this example? Consider, for instance, estimating $d p / d \sigma$ . The re-simulation estimator is $( P ( \sigma _ { 1 } ) \textrm { -- }$ $P ( \sigma _ { 0 } ) ) / h$ , which can be written as

$$
e ^ { - r T } \frac { \operatorname* { m a x } ( S _ { T } ( \sigma _ { 1 } ) - K , 0 ) - \operatorname* { m a x } ( S _ { T } ( \sigma _ { 0 } ) - K , 0 ) } { h } .
$$

The pathwise estimator is $e ^ { - r T } 1 _ { \{ S _ { T } ( \sigma _ { 0 } ) \geq K \} } d S _ { T } ( \sigma _ { 0 } ) / d \sigma$ . If common random numbers are used, these estimators difer in two respects. First, they difer when $S _ { T } ( \sigma _ { 0 } ) < K$ but $S _ { T } ( \sigma _ { 1 } ) \ge K$ In this case the pathwise estimator is exactly zero, but the re-simulation estimator can difer significantly from zero. However, for small h, the probability of this situation is also small. In all other cases, the estimators difer in the term $( \operatorname* { m a x } ( S _ { T } ( \sigma _ { 1 } ) - K , 0 ) - \operatorname* { m a x } ( S _ { T } ( \sigma _ { 0 } ) - K , 0 ) ) / h$ versus $d S _ { T } ( \sigma _ { 0 } ) / d \sigma$ . However, for small h, these terms are nearly equal. In other words, as h decreases to zero, the re-simulation estimator converges to the pathwise estimator. This, in fact, defines the pathwise estimator. Hence it is not surprising that for small h the results are nearly identical.

<!-- page: 12 -->

## Example 2: Asian Options

In this example derivatives are computed for Asian options, i.e., options on an arithmetic average price. The payof of these options is path dependent, that is, the payof depends not only on the terminal security price but on all the previous prices that enter into the average. Closed form expressions for the option price and derivatives are not available for this model. However, analytical approximations have been developed in Turnbull and Wakeman (1991) and Ritchken, Sankarasubramanian, and Vijh (1993). Additional analytical results are given in Geman and Yor (1993). We use this example merely to illustrate simulation results for a path dependent example. While analytical approaches are available for some Asian option models, if the stochastic process of the underlying asset is modified slightly, it is straightforward to modify the simulation estimators but the analytical approaches may not carry through.

We assume that the underlying asset satisfies the stochastic diferential equation (1). Let T be the maturity of the option written on the average of the last m daily closing prices. Thus, the average price can be written as $\begin{array} { r } { \bar { S } = \sum _ { i = 1 } ^ { m } S _ { i } / m } \end{array}$ , where (by a slight abuse of notation) $S _ { i }$ is the price at time $t _ { i } = T - ( m - i ) / 3 6 5 . 2 5$ . For convenience we assume that $T > m / 3 6 5 . 2 5 , \mathrm { i . e . }$ the maturity is greater than the averaging period. The derivative estimators do not change significantly if this is not the case. When Asian options are initiated, the time until the averaging period begins, $t _ { 1 }$ , is typically much larger than the increment between averaged prices (which is one day in this example).

The estimators for this example are summarized in Propositions 5 and 6 in Appendix C. Here theta is defined to be the negative of the derivative of the option price with respect to maturity for a fixed averaging increment. In other words, a change in T means a change in the time $t _ { 1 }$ until averaging begins. All estimators in Propositions 5 and 6 follow from the same reasoning as the previous ones, though the resulting expressions are more complicated. In particular, the pathwise estimator for gamma is no longer a constant. Results for this model are given in Table 2. The results are consistent with those in Example 1, e.g., the point estimates and standard errors are very close for the pathwise and re-simulation methods. An exception is gamma, where the standard errors for the pathwise method are smaller than the re-simulation method. This is due to using a larger value for h, which is necessary because of machine precision; smaller values of h can give unreliable results. For estimating gamma, a hybrid method was also tested, i.e., the pathwise estimate of delta was re-simulated.

<!-- page: 13 -->

[Table source crop](assets/tables/1996-broadie-glasserman-security-price-derivatives-p0013-block-0001-1b2b9998febe1400.jpg)
Table 1. European Call Options on Dividend Paying Assets

<!-- page: 14 -->

Example 3: Options with Stochastic Volatility

To illustrate the methods on a model with multiple state variables, derivatives for options with stochastic volatility are computed in this example. Following Johnson and Shanno (1987) and Hull and White (1987) we assume that S and $\sigma$ follow the risk neutralized stochastic processes:

$$
d S _ { t } = S _ { t } [ ( r - \delta ) d t + \sigma _ { t } d Z _ { t } ]\tag{19}
$$

$$
d \sigma _ { t } = \sigma _ { t } [ \mu d t + \xi d W _ { t } ]\tag{20}
$$

where Z and W are correlated Brownian motion processes with constant correlation $\rho .$ Johnson and Shanno (1987) present simulation results for this model and Hull and White (1987) give analytical results for certain special cases and simulation results for other cases. Additional analytical results for a similar model are given in Heston (1993) and Stein and Stein (1991). Our aim is to illustrate the simulation methods for derivative estimation on a model with multiple state variables. Closed form solutions, when available, are generally preferable to simulation methods because of their computational speed advantage. However, changes to the stochastic processes (19) and (20) are easily incorporated in the simulation methods, but the analytical solutions may not be so easily modified.

Our simulation results are based on the following discrete time version of (19)–(20):

$$
S _ { i + 1 } = S _ { i } ( 1 + ( r - \delta ) \Delta t + \sigma _ { i } \sqrt { \Delta t } Z _ { i } )\tag{21}
$$

$$
\sigma _ { i + 1 } = \sigma _ { i } ( 1 + \mu \Delta t + \xi \sqrt { \Delta t } W _ { i } ) .\tag{22}
$$

In (21)–(22), m is the number of time steps in the discretization, $\Delta t = T / m , t _ { i } = ( i / m ) T$ , and $S _ { i }$ and $\sigma _ { i }$ are the simulated asset prices and volatilities at time $t _ { i } ,$ respectively. Also, $Z _ { i }$ and $W _ { i }$ are correlated standard normal random variables. This is a first order Euler approximation to (19)-(20). See Dufie (1992) for a discussion of discrete approximations to continuous time models. See Dufie (1992) and Dufie and Glynn (1993) for related convergence issues.

Pathwise and re-simulation results for this example are given in Table 3. Likelihood ratio estimators are not used because the estimators are substantially more complicated in this example and because their performance in the earlier examples was not as promising. Pathwise derivative estimators for this model are given in Proposition 7 in Appendix C. In accordance with (21)–(22), theta is the negative of the derivative with respect to the maturity T with m held fixed; thus, $d ( \Delta t ) / d T = 1 / m$ . In addition to the usual derivatives, sensitivities with respect to $\xi$ and $\mu$ are also computed. Although the estimators are somewhat more complicated than in the previous example, the results given in Table 3 are similar.

<!-- page: 15 -->

[Table source crop](assets/tables/1996-broadie-glasserman-security-price-derivatives-p0015-block-0001-7bed5a4e8caf2b6f.jpg)
Table 2. Asian Call Options on Dividend Paying Assets

<!-- page: 16 -->

[Table source crop](assets/tables/1996-broadie-glasserman-security-price-derivatives-p0016-block-0001-069a58acd5c1a1da.jpg)
Table 3. Call Options on Dividend Paying Assets with Stochastic Volatility

<!-- page: 17 -->

As seen in all three examples, the bias in the re-simulation method is small enough that it is not an essential concern. Since the computational efort required by the pathwise and likelihood ratio methods are nearly identical, the diference in standard errors is a strong argument in favor of the pathwise method. Since the re-simulation method typically requires much more computational efort than the pathwise method, the nearly identical results for the two methods also favor the pathwise method.

## Control Variates

Variance reduction techniques that apply to the original simulation estimator of a security price can often be applied to derivative estimators. Among the most powerful tools is the control variate technique. For consistency we used the same control variate, the terminal security price, for each of the three examples.<sup>4</sup> Next we briefly summarize the control variate technique. Let D represent an unbiased simulation estimator of the derivative. That is, $d =$ $E [ D ]$ where d is the true value of the derivative to be estimated. Let $S _ { T }$ represent the simulated terminal price of the security. Since $E [ S _ { T } ] = e ^ { ( r - \delta ) T } S _ { 0 }$ , another unbiased estimator of the derivative is

$$
D ^ { \prime } = D + \beta ( S _ { T } - e ^ { ( r - \delta ) T } S _ { 0 } ) ,\tag{23}
$$

for any $\beta .$ The parameter $\beta$ can be chosen to minimize the variance of the estimator $D ^ { \prime }$ This problem is minβ $E [ D ^ { \prime } - d ] ^ { 2 }$ . An easy computational device for solving this problem is linear regression. Thus, if the estimators D are regressed on $S _ { T }$ , the slope of the regression line solves the minimization problem. The last step of optimizing over $\beta$ can significantly improve the efectiveness of the control variate technique.<sup>5</sup> The eficiency of the resulting estimator $D ^ { \prime }$ depends on the absolute value of the correlation between the original estimator, $D _ { \mathrm { { ; } } }$ , and the control variate, $S _ { T }$

## 5. Conclusions

In this paper two methods for estimating derivatives of security prices using simulation were presented. The first method uses the dependence of the security payof on the parameter of interest. Diferentiating this relationship leads, under appropriate conditions, to an unbiased estimator for the derivative of the security price. Since the dependence of the parameter is identified through the random security payof, this method is termed the pathwise method. The second method is based on likelihood ratios. Here the dependence of the underlying probability density on the parameter of interest is exploited to obtain derivative information.

<sup>4</sup> Note that there is always a simple control variable available, namely the random numbers themselves. We used the terminal security price because it led to a larger reduction in variance.

<sup>5</sup> Although this observation is standard in the simulation literature, e.g., §11.4 of Law and Kelton (1991), it has been substantially underutilized in the finance literature.

<!-- page: 18 -->

The main advantage of the direct methods over re-simulation is increased computational speed. The estimation of n derivatives by the re-simulation method requires n + 1 simulation runs. With the direct methods, the information from a single simulation can be used to estimate all n derivatives. Solving for the implied value of a parameter given a security price typically requires many simulation runs. The use of direct methods for estimating derivatives can lead to significant computational savings in these cases. Another advantage is that the direct methods give unbiased estimates of derivatives, whereas the estimates obtained by re-simulation are generally biased.

To illustrate and compare the methods, derivatives were computed for a path independent model, a path dependent model, and a model with multiple state variables. The computational results indicate that the likelihood ratio method gives significantly larger standard errors than the pathwise method. The pathwise and re-simulation methods give nearly identical point estimates and standard errors. Hence, the bias in the re-simulation estimates is not a problem of practical significance in the examples we considered. Since the results for the pathwise and re-simulation methods are nearly identical, the computational speed advantage of the pathwise method is a strong argument in its favor.

## 6. References

[1] F. Black and M. Scholes, “The Pricing of Options and Corporate Liabilities,” Journal of Political Economy, Vol. 81, May–June 1973, pp. 637–654. [2] P. Boyle, “Options: A Monte Carlo Approach,” Journal of Financial Economics, Vol. 4, No. 3, 1977, 323–338. [3] D.T. Breeden and R.H. Litzenberger, “Prices of State-contingent Claims Implicit in Option Prices,” Journal of Business, Vol. 51, No. 4, 1978, 621–651. [4] M. Broadie, “Estimating Duration using Simulation,” Shearson Lehman Hutton research report, January, 1988. [5] P. Carr, “Deriving Derivatives of Derivative Securities,” Working paper, Cornell University, February 1993. [6] D. Dufie, Dynamic Asset Pricing Theory, Princeton University Press, Princeton, NJ, 1992. [7] D. Dufie and P. Glynn, “Eficient Monte Carlo Simulation of Security Prices,” Working

<!-- page: 19 -->

paper, Stanford University, March 1993. [8] P. Franklin, Methods of Advanced Calculus, McGraw-Hill, New York, 1944. [9] M.C. Fu and J. Hu, “Second Derivative Sample Path Estimators for the GI/G/m Queue,” Management Science, Vol. 39, No. 3, 1993a, 359–383. [10] M.C. Fu and J. Hu, “Sensitivity Analysis for Monte Carlo Simulation of Option Pricing,” Working paper, College of Business and Management, University of Maryland, November 1993b. [11] H. Geman and M. Yor, “Bessel Processes, Asian options, and perpetuities,” Mathematical Finance, Vol. 3, No. 4, 1993, 349–375. [12] P. Glasserman, Gradient Estimation Via Perturbation Analysis, Kluwer Academic Publishers, Norwell, Massachusetts, 1991. [13] P.W. Glynn, “Likelihood Ratio Estimation: An Overview,” in Proceedings ofthe 1987Winter Simulation Conference, The Society for Computer Simulation, San Diego, California, 1987, 366–375. [14] P.W. Glynn, “Optimization of Stochastic Systems via Simulation,” in Proceedings of the 1989 Winter Simulation Conference, The Society for Computer Simulation, San Diego, California, 1989, 90–105. [15] J.M. Harrison and D. Kreps, “Martingales and Arbitrage in Multiperiod Securities Markets,” Journal of Economic Theory, Vol. 20, 1979, pp. 381–408. [16] S.L. Heston, “A Closed-Form Solution for Options with Stochastic Volatility with Appli cations to Bond and Currency Options,” Review of Financial Studies, Vol. 6, No. 2, 1993, 327–343. [17] J. Hull, Options, Futures, and other Derivative Securities, 2<sup>nd</sup> edition, Prentice-Hall, Englewood Clifs, New Jersey, 1992. [18] J. Hull and A. White, “The Pricing of Options on Assets with Stochastic Volatilities,” Journal ofFinance, Vol. 42, No. 2, 1987, 281–300. [19] H. Johnson and D. Shanno, “Option Pricing when the Variance is Changing,” Journal of Financial and Quantitative Analysis, Vol. 22, No. 2, 1987, 143–151. [20] R.A. Jones and R.L. Jacobs, “History Dependent Financial Claims: Monte Carlo Valuation,” Working paper, Simon Fraser University, 1986.

<!-- page: 20 -->

[21] A.G.Z. Kemna and A.C.F. Vorst, “A Pricing Method for Options Based on Average Asset Values,” Journal ofBanking and Finance, Vol. 14, 1990, 113–129. [22] A.M. Law and W.D. Kelton, Simulation Modeling and Analysis, 2<sup>nd</sup> edition, McGraw-Hill, New York, 1991. [23] P. L’Ecuyer, “A Unified View of the IPA, SF, and LR Gradient Estimation Techniques,” Management Science, Vol. 36, No. 11, 1990, 1364–1383. [24] R.C. Merton, “Theory of Rational Option Pricing,” Bell Journal of Economics and Management Science, Vol. 4, 1973, 141–183. [25] P. Ritchken, L. Sankarasubramanian, and A. Vijh, “The Valuation of Path Dependent Contracts on the Average,” Management Science, Vol. 39, No. 10, 1993, 1202–1213. [26] R.Y. Rubinstein and A. Shapiro, Discrete EventSystems: SensitivityAnalysis and Stochastic Optimization by the Score Function Method, John Wiley & Sons, Chichester and New York, 1993. [27] E.S. Schwartz and W.N. Torous, “Prepayment and the Valuation of Mortgage-Backed Securities,” Journal of Finance, Vol. 44, No. 2, 1989, 375–392. [28] C.W. Smith, Jr., C.W. Smithson, and D.S. Wilford, Managing Financial Risk, Harper & Row, New York, 1990. [29] E.M. Stein and J.C. Stein, “Stock Price Distributions with Stochastic Volatility: An Analytic Approach,” Review of Financial Studies, Vol. 4, No. 4, 1991, 727–752. [30] S.M. Turnbull and L.M. Wakeman, “A Quick Algorithm for Pricing European Average Options,” Journal of Financial and Quantitative Analysis, Vol. 26, No. 3, 1991, 377–389. [31] M. Zazanis and R. Suri, “Convergence Rates of Finite-Diference Sensitivity Estimates for Stochastic Systems,” Operations Research, Vol. 41, No. 4, 1993, 694–703.

## Appendix A: General Conditions for Unbiased Estimators

In this appendix, we discuss general conditions for derivative estimators to be unbiased, giving particular attention to the more delicate case of pathwise estimators.

Let $\{ X _ { n } , n \geq 0 \}$ be a vector-valued state process recording, for example, the price of an underlying asset, the prevailing interest rate, and any other variables influencing the price of a derivative security. (Our vectors are column vectors.) The process $\{ X _ { n } \}$ may be a discretization of a continuous-time process. We take the discrete-time model as our starting point.

<!-- page: 21 -->

Suppose the discounted payof associated with a derivative security is given by $f ( X )$ , where $X = ( X _ { 1 } , \ldots , X _ { T } )$ , T is the maturity, and f is real-valued. Thus, the price of the security is $p = E [ f ( X ) ]$

Now suppose the state process is a function of a scalar parameter θ ranging over an open interval . In other words, each $X _ { n }$ is a random function on . For the existence of pathwise derivatives, we require the following conditions:

(A1) At each $\theta \in \Theta$

$$
X _ { n } ^ { \prime } ( \theta ) \equiv \operatorname* { l i m } _ { h  0 } \frac { X _ { n } ( \theta + h ) - X _ { n } ( \theta ) } { h }
$$

exists with probability 1.

(A2) If $D _ { f }$ denotes the set of points at which f is diferentiable, then

$$
P ( X ( \theta ) \in D _ { f } ) = 1 , { \mathrm { f o r ~ a l l ~ } } \theta \in \Theta .
$$

Under these conditions, the discounted payof has a pathwise derivative, given by

$$
\frac { d } { d \theta } f ( X ( \theta ) ) = \sum _ { n = 1 } ^ { T } [ \nabla _ { x _ { n } } f ( X ( \theta ) ) ] ^ { t } X _ { n } ^ { \prime } ( \theta ) ,\tag{24}
$$

where $\nabla _ { x _ { n } } f$ denotes the vector of partial derivatives of $f$ with respect to the components of $X _ { n }$ , and the superscript t denotes transpose. For this pathwise derivative to be an unbiased estimator of the derivative of $p ,$ , we require further conditions:

(A3) There exists a constant $k _ { f }$ such that $| f ( x ) - f ( y ) | \leq k _ { f } \| x - y \|$ , for all vectors $x , y$ in the domain of $f .$

(A4) There exist random variables $K _ { n } , \ n \ = \ 1 , 2 , . . . ,$ , such that $\parallel X _ { n } ( \theta _ { 2 } ) ~ -$ $X _ { n } ( \theta _ { 1 } ) \| \ \le K _ { n } | \theta _ { 2 } - \theta _ { 1 } |$ , for all n, and for all $\theta _ { 1 } , \theta _ { 2 } \in \Theta$ . For each $n ,$ $E [ K _ { n } ] < \infty .$

Condition (A3) states that f is Lipschitz continuous; condition (A4) states each $X _ { n }$ is almost surely Lipschitz with an integrable modulus $K _ { n }$ . We now have

Proposition 1: $I f ( A I ) – ( A 4 ) h o I d ,$ then at every $\theta \in \Theta , d p ( \theta ) / d \theta$ exists and equals $E [ d f ( X ) / d \theta ] .$

Proof of Proposition 1: Let $P ( \theta ) = f ( X ( \theta ) ) ;$ then, as already noted, $P ^ { \prime } ( \theta )$ exists with probability 1 if (A1) and (A2) hold. The Lipschitz property is preserved by composition. Hence,

<!-- page: 22 -->

under (A3) and the first part of (A4), P is almost surely Lipschitz continuous; that is, there exists a random variable $K _ { P }$ such that

$$
| P ( \theta _ { 2 } ) - P ( \theta _ { 1 } ) | \leq K _ { P } | \theta _ { 2 } - \theta _ { 1 } | , \quad \forall \theta _ { 1 } , \theta _ { 2 } \in \Theta ,
$$

with probability 1. It follows that for any θ and $\theta + h$ in , we have

$$
{ \frac { | P ( \theta + h ) - P ( \theta ) | } { h } } \leq K _ { P } .
$$

Moreover, under the second part of (A4), the bound $K _ { P }$ has finite expectation (it is bounded by a linear combination of $K _ { 1 } , \ldots , K _ { T } )$ , so we may invoke the dominated convergence theorem to interchange an expectation and the limit as $h 0$ to conclude that $p ^ { \prime } ( \theta )$ exists and equals $E [ P ^ { \prime } ( \theta ) ]$ . ♦

The same considerations that arise in justifying the interchange of derivative and integral for the likelihood ratio method arise in maximum likelihood estimation. Consequently, these issues have been addressed in the statistical literature, and standard suficient conditions can be found in statistics texts. Generally speaking, if the density is a reasonably smooth function of the parameter in question, the interchange is permissible. For a more detailed examination of this interchange in the derivative estimation context, see L’Ecuyer (1990).

When a pathwise estimator of a first derivative is Lipschitz continuous, the argument in Proposition 1 can be applied to show that the pathwise second derivative is also unbiased. However, we have seen that first derivative estimators often involve indicator functions, making them discontinuous. As a result, pathwise estimators of second derivatives do not lend themselves to a simple, unified treatment along the lines of Proposition 1. The particular type of “smoothing” required to obtain an unbiased second derivative estimator is problem dependent. So, we justify our gamma estimators individually in Appendix C. Closely related approaches are used in other contexts in Fu and Hu (1993a) and in Chapter 7 of Glasserman (1991).

## Appendix B: Optimal Choice of the Parameter Increment in the Re-simulation Method

Let h denote the parameter increment in the re-simulation method. There is an apparent tradeof involved in the choice of h. If h is too small, then the variance in the estimates of the original and perturbed prices can cause a large variance in the estimate of the derivative. If h is too large, then the nonlinearity of the price as a function of the parameter of interest can cause a large bias in the derivative estimate. This tradeof is discussed next. For more extensive treatments of this topic, see Zazanis and Suri (1993) for the case of independent re-simulations, and Glynn (1989) for the case of common random numbers. See also Broadie (1988).

<!-- page: 23 -->

Suppose that the re-simulation method is used to estimate the derivative of the security price p with respect to a parameter θ. If the function $p ( \theta )$ is twice continuously diferentiable, Taylor’s theorem implies that the function can be approximated by

$$
p ( \theta ) = p _ { 0 } + a ( \theta - \theta _ { 0 } ) + b ( \theta - \theta _ { 0 } ) ^ { 2 } + o ( \theta - \theta _ { 0 } ) ^ { 2 } ,
$$

where $p _ { 0 } = p ( \theta _ { 0 } )$ and $a = d p / d \theta$ evaluated at $\theta = \theta _ { 0 }$ . Suppose that we wish to estimate a. Let h denote the size of the parameter perturbation and set $\theta _ { 1 } = \theta _ { 0 } + h$ . Let $P ( \theta _ { i } ) = p ( \theta _ { i } ) + \epsilon _ { i }$ for $i = 0 , 1$ , denote the simulation estimator of $p ( \theta _ { i } )$ . The re-simulation estimator of a is $\hat { a } = ( P ( \theta _ { 1 } ) - P ( \theta _ { 0 } ) ) / h . ^ { 6 }$

Suppose that the objective is to minimize the mean squared estimation error. Ignoring higher order terms,

$$
E [ \hat { a } - a ] ^ { 2 } = E [ ( b h + \frac { \epsilon _ { 1 } - \epsilon _ { 0 } } { h } ) ^ { 2 } ] .\tag{25}
$$

For simplicity, suppose that the variances of $\epsilon _ { 0 }$ and $\epsilon _ { 1 }$ are equal and denoted by $\nu ^ { 2 }$ . Also, let $\rho$ denote the correlation of $\epsilon _ { \mathrm { 0 } }$ and $\epsilon _ { 1 }$ and suppose it is independent of h.

With these assumptions, the parameter increment $h ^ { * }$ that minimizes the mean squared estimation error is

$$
h ^ { * } = \sqrt [ 4 ] { \frac { 2 \nu ^ { 2 } ( 1 - \rho ) } { b ^ { 2 } } } .\tag{26}
$$

This follows by expanding the terms in (25) and minimizing (25) over h. Equation (26) squares with intuition in several regards. As the accuracy of the estimators $P ( \theta _ { i } )$ increases $( \mathrm { i . e . }$ as $\nu ^ { 2 }$ decreases with additional trials in the simulation) the optimal increment $h ^ { * }$ decreases. $\mathrm { A s } b ^ { 2 }$ decreases (i.e., as $p ( \theta )$ becomes more nearly linear) the optimal increment $h ^ { * }$ increases. Finally, $h ^ { * }$ decreases as the correlation of the errors approaches one.

Evaluating (25) at $h ^ { * }$ gives $E [ \hat { a } - a ] ^ { 2 } = 2 | b \nu | \sqrt { 2 ( 1 - \rho ) }$ . This expression illustrates the importance of using common random numbers for the re-simulation. Using diferent random numbers gives a $\rho$ of zero, but using the same stream of random numbers typically gives a correlation near one, and hence a better derivative estimate.

In our examples, the assumption of equal variances for $\epsilon _ { \mathrm { 0 } }$ and $\epsilon _ { 1 }$ does not hold precisely, but more importantly, the assumption of a constant $\rho$ does not hold. In many simulation contexts, e.g., many discrete-event systems, the variance of $\epsilon _ { 1 } - \epsilon _ { 0 }$ can be written as $h \sigma _ { 1 } ^ { 2 } ( 1 -$ $\rho _ { 1 } ) + o ( h )$ . The optimal increment h in this case is typically smaller than indicated by (26); see Glynn (1989) for details. In our examples, the variance of $\epsilon _ { 1 } - \epsilon _ { 0 }$ can be written as $h ^ { 2 } \sigma _ { 1 } ^ { 2 } ( 1 -$ $\rho _ { 1 } ) + o ( h ^ { 2 } )$ ; this always holds under assumptions (A1)–(A4) of Appendix A. This suggests that the optimal increment in our examples is $h ^ { * } = 0 ^ { + }$ . In practice, we chose h as small as possible, but large enough that machine precision does not pose a problem in the computations. For this reason and after some experimentation, we took $h = 0 . 0 0 0 1$ to estimate all derivatives except gamma, for which $h = 0 . 0 5$ was used.

<sup>6</sup> In terms of derivative estimation alone, it would be better to use a symmetric interval for the finite diference. That is, estimate the derivative at θ using the estimators P(θ − h/2) and P(θ + h/2). However, this approach requires two additional simulations for each derivative estimate instead of one with the approach in the text.

<!-- page: 24 -->

## Appendix C: Summary of Estimators

The proofs of the following propositions are generally similar to the derivations in the text. Hence, most of the propositions are stated without proof. Where necessary, sketches of the derivation are given.

Proposition 2 (European call option derivatives):

$$
D e l t a ~ ( d p / d S _ { 0 } ) ; ~ e ^ { - \delta T } N ( d _ { 1 } ( K ) )\tag{27}
$$

$$
V e g a ~ ( d p / d \sigma ) : ~ \sqrt { T } e ^ { - \delta T } S _ { 0 } n ( d _ { 1 } ( K ) )\tag{28}
$$

$$
G a m m a ( d ^ { 2 } p / d S _ { 0 } ^ { 2 } ) ; ~ e ^ { - \delta T } \frac { n ( d _ { 1 } ( K ) ) } { S _ { 0 } \sigma \sqrt { T } }\tag{29}
$$

$$
R h o ( d p / d r ) \colon K T e ^ { - r T } N ( d _ { 2 } ( K ) )\tag{30}
$$

$$
T h e t a \left( - d p / d T \right) : \quad - \frac { \sigma e ^ { - \delta T } S _ { 0 } n ( d _ { 1 } ( K ) ) } { 2 \sqrt { T } } + \delta e ^ { - \delta T } S _ { 0 } N ( d _ { 1 } ( K ) ) - r K e ^ { - r T } N ( d _ { 2 } ( K ) )\tag{31}
$$

where $d _ { 1 } ( x ) = [ \ln ( S _ { 0 } / x ) + ( r - \delta + { \textstyle \frac { 1 } { 2 } } \sigma ^ { 2 } ) T ] / ( \sigma \sqrt { T } ) = - d ( x ) + \sigma \sqrt { T } ,$ and $d _ { 2 } ( x ) = - d ( x )$ Also, N(·) is the cumulative distribution function of a standard normal random variable.

Proof of Proposition 2: The European call option value is $p = S _ { 0 } e ^ { - \delta T } N ( d _ { 1 } ( K ) ) - e ^ { - r T } K N ( d _ { 2 } ( K ) )$ , see, e.g., Black and Scholes (1973) and Merton (1973). The results follow by diferentiation. ♦

Proposition 3 (European option pathwise derivative estimators): The following are unbiased pathwise estimators of the indicated derivatives of European option prices.

$$
D e l t a ~ ( d p / d S _ { 0 } ) ; ~ e ^ { - r T } 1 _ { \{ S _ { T } \geq K \} } \frac { S _ { T } } { S _ { 0 } }\tag{32}
$$

$$
V e g a ~ ( d p / d \sigma ) ; ~ e ^ { - r T } 1 _ { \{ S _ { T } \geq K \} } \frac { S _ { T } } { \sigma } \big ( \ln ( S _ { T } / S _ { 0 } ) - ( r - \delta - { \textstyle { \frac { 1 } { 2 } } } \sigma ^ { 2 } ) T \big )\tag{33}
$$

<!-- page: 25 -->

$$
G a m m a ( d ^ { 2 } p / d S _ { 0 } ^ { 2 } ) ; ~ e ^ { - \delta T } \frac { n ( d _ { 1 } ( K ) ) } { S _ { 0 } \sigma \sqrt { T } }\tag{34}
$$

$$
R h o ( d p / d r ) \colon K T e ^ { - r T } 1 _ { \{ S _ { T } \geq K \} }\tag{35}
$$

$$
T h e t a \left( - d p / d T \right) : r e ^ { - r T } \operatorname* { m a x } ( S _ { T } - K , 0 ) - 1 _ { \{ S _ { T } \geq K \} } e ^ { - r T } \frac { S _ { T } } { 2 T } \big ( \ln ( S _ { T } / S _ { 0 } ) + ( r - \delta - \textstyle \frac 1 2 \sigma ^ { 2 } ) T | \beta 6 \big )
$$

Proof of Proposition 3: For each case other than (34), diferentiability with probability 1, as required by conditions (A1)–(A2) of Appendix A follows from (3) and (4): equation (4) shows that $S _ { T }$ is a smooth function of its parameters, and equation (3) shows that P is diferentiable in $S _ { T }$ except when $S _ { T } = K$ , which occurs with probability 0. For conditions (A3)–(A4), notice that addition, multiplication by a constant, and the max operation are all Lipschitz functions. Exponentiation is Lipschitz on bounded intervals and the square root function is Lipschitz away from the origin. In particular, the discounted payof P is Lipschitz in a neighborhood of each of its arguments (since $\sigma > 0$ and $T > 0 )$ . Integrability of the corresponding moduli is easily verified in each case. The derivation and justification of the gamma estimator are given in Section 3. ♦

Proposition 4 (European option likelihood ratio derivative estimators): The following are unbiased likelihood ratio estimators of the indicated derivatives of European option prices.

$$
D e l t a ( d p / d S _ { 0 } ) \colon e ^ { - r T } \operatorname* { m a x } ( S _ { T } - K , 0 ) \frac { 1 } { S _ { 0 } \sigma ^ { 2 } T } \big ( \ln ( S _ { T } / S _ { 0 } ) - ( r - \delta - \textstyle { \frac { 1 } { 2 } } \sigma ^ { 2 } ) T \big )\tag{37}
$$

$$
V e g a \left( { d p / d \sigma } \right) : e ^ { - r T } \mathrm { m a x } ( S _ { T } - K , 0 ) \big ( - { d \frac { \partial d } { \partial \sigma } } - \frac { 1 } { \sigma } \big )\tag{38}
$$

$$
G a m m a ( d ^ { 2 } p / d S _ { 0 } ^ { 2 } ) : ~ e ^ { - r T } \operatorname* { m a x } ( S _ { T } - K , 0 ) { \frac { d ^ { 2 } - d \sigma { \sqrt { T } } - 1 } { S _ { 0 } ^ { 2 } \sigma ^ { 2 } T } }\tag{39}
$$

$$
R h o ( d p / d r ) : ~ e ^ { - r T } \operatorname* { m a x } ( S _ { T } - K , 0 ) ( - T + \frac { d \sqrt { T } } { \sigma } )\tag{40}
$$

$$
T h e t a \left( - d p / d T \right) : e ^ { - r T } \operatorname* { m a x } ( S _ { T } - K , 0 ) \left( r + d \frac { \partial d } { \partial T } + \frac { 1 } { 2 T } \right)\tag{41}
$$

where in $( 3 8 ) - ( 4 I ) ~ d ~ = ~ d ( S _ { T } ) ~ = ~ ( \ln ( S _ { T } / S _ { 0 } ) ~ - ~ ( r ~ - ~ \delta ~ - ~ { \textstyle { \frac { 1 } { 2 } } } \sigma ^ { 2 } ) T ) / ( \sigma \sqrt { T } )$ , in (38) ∂d/∂σ = $\begin{array} { r } { ( \ln ( S _ { 0 } / S _ { T } ) + ( r - \delta + \frac { 1 } { 2 } \sigma ^ { 2 } ) T ) / ( \sigma ^ { 2 } \sqrt { T } ) a n d i n ( 4 l ) \partial d / \partial T = ( - \ln ( S _ { T } / S _ { 0 } ) - ( r - \delta - \frac { 1 } { 2 } \sigma ^ { 2 } ) T ) / ( 2 \sigma T ^ { 3 / 2 } ) . } \end{array}$

Proposition 5 (Asian option pathwise derivative estimators): The following are unbiased pathwise estimators of the indicated derivatives of Asian option prices.

$$
D e l t a ~ ( d p / d S _ { 0 } ) ; ~ e ^ { - r T } 1 _ { \{ \bar { S } \geq K \} } \frac { \bar { S } } { S _ { 0 } }\tag{42}
$$

<!-- page: 26 -->

$$
V e g a \left( d p / d \sigma \right) : e ^ { - r T } 1 _ { \{ \bar { S } \geq K } \} \frac { 1 } { m \sigma } \sum _ { i = 1 } ^ { m } S _ { i } \big ( \ln ( S _ { i } / S _ { 0 } ) - ( r - \delta + \textstyle { \frac { 1 } { 2 } } \sigma ^ { 2 } ) t _ { i } \big )\tag{43}
$$

$$
G a m m a ~ ( d ^ { 2 } p / d S _ { 0 } ^ { 2 } ) : ~ e ^ { - r T } \bigl ( { \frac { K } { S _ { 0 } } } \bigr ) ^ { 2 } m g ( S _ { m - 1 } , w _ { m } , \Delta t _ { m } )\tag{44}
$$

$$
R h o ~ ( d p / d r ) : ~ 1 _ { \{ \bar { S } \geq K \} } e ^ { - r T } \bigl ( \frac { 1 } { m } \sum _ { i = 1 } ^ { m } S _ { i } t _ { i } - T \bigr )\tag{45}
$$

$$
T h e t a \left( - d p / d T \right) : \quad r e ^ { - r T } \operatorname* { m a x } ( \bar { S } - K , 0 ) - 1 _ { \{ \bar { S } \geq K \} } e ^ { - r T } \frac { \bar { S } } { 2 t _ { 1 } } \big ( \ln ( S _ { 1 } / S _ { 0 } ) + ( r - \delta - \frac { 1 } { 2 } \sigma ^ { 2 } ) t _ { 1 } \big ) ( \ln ( | S _ { 1 } | / S _ { 0 } ) + ( r - \delta - \frac { 1 } { 2 } \sigma ^ { 2 } ) t _ { 1 } ) ,\tag{46}
$$

where in (44) $\Delta t _ { i } = t _ { i } - t _ { i - 1 } , w _ { m } = m ( K - \bar { S } ) + S _ { m } , g ( u , \nu , t ) = n ( d ( u , \nu , t ) ) / ( \nu \sigma \sqrt { t } )$ , and $\begin{array} { r } { d ( u , \nu , t ) = ( \ln ( \nu / u ) - ( r - \delta - \frac { 1 } { 2 } \sigma ^ { 2 } ) t ) / ( \sigma \sqrt { t } ) } \end{array}$

In Table 2 in the text, a hybrid (biased) estimator of gamma is also used. This hybrid estimator, based on a re-simulation of the pathwise delta estimator, is defined by

$$
G a m m a \left( d ^ { 2 } p / d S _ { 0 } ^ { 2 } \right) : \frac { 1 } { h } ( e ^ { - r T } 1 _ { \{ \bar { S } ( S _ { 0 } + h ) \geq K \} } \frac { \bar { S } ( S _ { 0 } + h ) } { S _ { 0 } + h } - e ^ { - r T } 1 _ { \{ \bar { S } ( S _ { 0 } ) \geq K \} } \frac { \bar { S } ( S _ { 0 } ) } { S _ { 0 } } ) .\tag{47}
$$

Proof of Proposition 5: The derivations of vega, theta and gamma are sketched. Note that $S _ { i }$ can be written as $\textstyle S _ { 0 } \prod _ { j = 1 } ^ { i } X _ { j }$ where ln $( X _ { j } )$ is normally distributed with mean $( r - \delta - \textstyle \frac { 1 } { 2 } \sigma ^ { 2 } ) \Delta t _ { j }$ and variance $\sigma ^ { 2 } \Delta t _ { j }$ . To compute $d \bar { S } / d \sigma$ , the intermediate terms $d S _ { i } / d \sigma$ ∆<sub>are needed. Using</sub>

$$
\frac { d ( \prod _ { j = 1 } ^ { i } X _ { j } ) } { d \sigma } = \sum _ { j = 1 } ^ { i } ( \prod _ { k \neq j } X _ { k } ) \frac { d X _ { j } } { d \sigma } ,
$$

$d S _ { i } / d \sigma$ can be written as $( S _ { i } / \sigma ) ( \ln ( S _ { i } / S _ { 0 } ) - ( r - \delta + { \textstyle { \frac { 1 } { 2 } } } \sigma ^ { 2 } ) t _ { i } )$ . The formula for vega now follows from arguments similar to those in the text.

For theta, recall that the derivative with respect to the maturity means the derivative with respect to $t _ { 1 }$ , the time until averaging begins. With this understanding, the derivation is essentially the same as in the European case.

By the same argument used in Section 3 for the European option, gamma can be written as the product of $e ^ { - r T } ( K / S _ { 0 } ) ^ { 2 }$ and the density of $\bar { S }$ at $\bar { S } = K$ . There is no closed form expression for this density, but it can be estimated in the simulation. Conditioning on $S _ { 1 } , \ldots , S _ { m - 1 }$ , we $\mathrm { g e t }$ , for any $x ,$ ,

$$
P ( \bar { S } \le x ) = E [ P ( \bar { S } \le x | S _ { 1 } , \dots , S _ { m - 1 } ) ] = E [ G ( m x - \sum _ { j = 1 } ^ { m - 1 } S _ { j } ) ] ,
$$

<!-- page: 27 -->

where G is the cumulative lognormal distribution of $S _ { m } / S _ { m - 1 }$ . Diferentiating both sides and setting $x \ = \ K$ , we find that an unbiased estimator of the required density value is $m g ( S _ { m - 1 } , w _ { m } , \Delta t _ { m } )$ . ♦

Alternative estimators of gamma are obtained through the argument above by conditioning on $\{ S _ { j } , j \neq i \} , i = 1 , \dots , m - 1$ . The $i ^ { \mathrm { { t h } } }$ such estimator of the density of $\bar { S }$ at K is

$$
m \frac { g ( S _ { i - 1 } , w _ { i } , \Delta t _ { i } ) g ( w _ { i } , S _ { i + 1 } , \Delta t _ { i + 1 } ) } { g ( S _ { i - 1 } , S _ { i + 1 } , \Delta t _ { i } + \Delta t _ { i + 1 } ) } .
$$

Averaging these m unbiased estimators gives another estimator of gamma:

$$
e ^ { - r T } \big ( \frac { K } { S _ { 0 } } \big ) ^ { 2 } \sum _ { i = 1 } ^ { m - 1 } \frac { g ( S _ { i - 1 } , w _ { i } , \Delta t _ { i } ) g ( w _ { i } , S _ { i + 1 } , \Delta t _ { i + 1 } ) } { g ( S _ { i - 1 } , S _ { i + 1 } , \Delta t _ { i } + \Delta t _ { i + 1 } ) } + g ( S _ { m - 1 } , w _ { m } , \Delta t _ { m } ) .
$$

Though theoretically this estimator should have smaller standard error than (44), empirically we found no significant diference.

Proposition 6 (Asian option likelihood ratio derivative estimators): The following are unbiased likelihood ratio estimators of the indicated derivatives of Asian option prices.

$$
D e l t a ~ ( d p / d S _ { 0 } ) \colon ~ e ^ { - r T } \operatorname * { m a x } ( \bar { S } - K , 0 ) \frac { 1 } { S _ { 0 } \sigma ^ { 2 } \Delta t _ { 1 } } \big ( \ln ( S _ { 1 } / S _ { 0 } ) - ( r - \delta - \frac { 1 } { 2 } \sigma ^ { 2 } ) \Delta t _ { 1 } \big )\tag{48}
$$

$$
V e g a \left( d p / d \sigma \right) : e ^ { - r T } \mathrm { m a x } ( \bar { S } - K , 0 ) \sum _ { i = 1 } ^ { m } \big ( - d _ { i } \frac { \partial d _ { i } } { \partial \sigma } - \frac { 1 } { \sigma } \big )\tag{49}
$$

$$
G a m m a ~ ( d ^ { 2 } p / d S _ { 0 } ^ { 2 } ) : ~ e ^ { - r T } \operatorname * { m a x } ( \bar { S } - K , 0 ) { \frac { d _ { 1 } ^ { 2 } - d _ { 1 } \sigma \sqrt { \Delta t _ { 1 } } - 1 } { S _ { 0 } ^ { 2 } \sigma ^ { 2 } \Delta t _ { 1 } } }\tag{50}
$$

$$
R h o \ : ( d p / d r ) : ~ e ^ { - r T } \operatorname* { m a x } ( \bar { S } - K , 0 ) \big ( - T + \sum _ { i = 1 } ^ { m } \frac { d _ { i } \sqrt { \Delta t _ { i } } } { \sigma } \big )\tag{51}
$$

$$
T h e t a \left( - d p / d T \right) : e ^ { - r T } \operatorname* { m a x } ( \bar { S } - K , 0 ) \big ( r + d _ { 1 } \frac { \partial d _ { 1 } } { \partial T } + \frac { 1 } { 2 \Delta t _ { 1 } } \big )\tag{52}
$$

where $\Delta t _ { i } = t _ { i } - t _ { i - 1 } , i n \ ( 4 9 ) - ( 5 2 ) \ d _ { i } = ( \ln ( S _ { i } / S _ { i - 1 } ) - ( r - \delta - \frac { 1 } { 2 } \sigma ^ { 2 } ) \Delta t _ { i } ) / ( \sigma \sqrt { \Delta t _ { i } } )$ , in (49) $\partial d _ { i } / \partial \sigma = ( \ln ( S _ { i - 1 } / S _ { i } ) + ( r - \delta + \frac { 1 } { 2 } \sigma ^ { 2 } ) \Delta t _ { i } ) / ( \sigma ^ { 2 } \sqrt { \Delta t _ { i } } )$ , and in $( 5 2 ) \partial d _ { 1 } / \partial T$ is given by $( - \ln ( S _ { 1 } / S _ { 0 } ) - |$ $( r - \delta - { \textstyle \frac { 1 } { 2 } } \sigma ^ { 2 } ) \Delta t _ { 1 } ) / ( 2 \sigma \Delta t _ { 1 } ^ { { \scriptsize 3 } / 2 } )$

Proposition 7 (Pathwise derivative estimators of option derivatives with stochastic volatility): Let $t _ { i } = ( i / m ) T$ and let $S _ { i } , \sigma _ { i }$ represent the simulated asset price and volatility, respectively,

<!-- page: 28 -->

at time $t _ { i } .$ . In this discrete time model, the following are unbiased pathwise estimators of the indicated derivatives of Asian option prices.

$$
D e l t a ~ ( d p / d S _ { 0 } ) ; ~ e ^ { - r T } 1 _ { \{ S _ { T } \geq K \} } \frac { S _ { T } } { S _ { 0 } }\tag{53}
$$

$$
V e g a ~ ( d p / d \sigma _ { 0 } ) : ~ e ^ { - r T } 1 _ { \{ S _ { T } \geq K \} } \frac { S _ { T } } { \sigma _ { 0 } } \sum _ { i = 1 } ^ { m } \big ( 1 - \frac { ( 1 + ( r - \delta ) d t ) S _ { i - 1 } } { S _ { i } } \big )\tag{54}
$$

$$
V e g a l ~ ( d p / d \xi ) ; ~ e ^ { - r T } 1 _ { \{ S _ { T } \geq K \} } \frac { S _ { T } } { \xi } \sum _ { i = 1 } ^ { m } \big ( 1 - \frac { ( 1 + ( r - \delta ) d t ) S _ { i - 1 } } { S _ { i } } \big ) \big ( \sum _ { k = 1 } ^ { i - 1 } \big [ 1 - \frac { ( 1 + \mu d t ) \sigma _ { k - 1 } } { \sigma _ { k } } \big ] \big ) \big ( \sum _ { k = 1 } ^ { m } \big ( \frac { \sigma _ { k - 1 } } { \sigma _ { k } } \big ) ^ { k - 1 } \big )\tag{<sup>(</sup>55<sup>)</sup>}
$$

$$
V e g a 2 ( d p / d \mu ) : e ^ { - r T } 1 _ { \{ S _ { T } \geq K \} } S _ { T } d t \sum _ { i = 2 } ^ { m } \big ( 1 - \frac { ( 1 + ( r - \delta ) d t ) S _ { i - 1 } } { S _ { i } } \big ) \big ( \sum _ { k = 1 } ^ { i - 1 } \frac { \sigma _ { k - 1 } } { \sigma _ { k } } \big )\tag{56}
$$

$$
G a m m a ~ ( d ^ { 2 } p / d S _ { 0 } ^ { 2 } ) : ~ e ^ { - r T } ( { \frac { K } { S _ { 0 } } } ) ^ { 2 } n ( { \frac { \frac { K S _ { m } } { S _ { T } S _ { m - 1 } } - ( 1 + ( r - \delta ) d t ) } { \sigma _ { m - 1 } \sqrt { d t } } } )\tag{57}
$$

$$
R h o \left( d p / d r \right) : e ^ { - r T } 1 _ { \{ S _ { T } \geq K \} } \big ( - T ( S _ { T } - K ) + S _ { T } d t \sum _ { i = 1 } ^ { m } \frac { S _ { i - 1 } } { S _ { i } } \big )\tag{58}
$$

$$
T h e t a \left( - d p / d T \right) : e ^ { - r T } 1 _ { \{ S _ { T } \geq K \} } { \left( r ( S _ { T } - K ) - \frac { d S _ { T } } { d T } \right) }\tag{59}
$$

where dt $\mathit { \Pi } : \ = \ T / m$ and $n ( \cdot )$ represents the standard normal density function. In (59) the derivative $d S _ { T } / d T$ can be evaluated recursively using

$$
{ \frac { d S _ { i } } { d T } } = { \frac { d S _ { i - 1 } } { d T } } { \bigl ( } { \frac { S _ { i } } { S _ { i - 1 } } } { \bigr ) } + S _ { i - 1 } { \bigl ( } { \frac { r - \delta } { m } } + { \frac { d \sigma _ { i - 1 } } { d T } } Z _ { i } { \sqrt { d t } } + { \frac { \sigma _ { i - 1 } Z _ { i } } { 2 { \sqrt { m T } } } } { \bigr ) }\tag{60}
$$

and

$$
\frac { d \sigma _ { i } } { d T } = \frac { d \sigma _ { i - 1 } } { d T } \big ( \frac { \sigma _ { i } } { \sigma _ { i - 1 } } \big ) + \sigma _ { i - 1 } \big ( \frac { \mu } { m } + \frac { \xi W _ { i } } { 2 \sqrt { m T } } \big )\tag{61}
$$

with $d S _ { 0 } / d T = 0$ and $d \sigma _ { 0 } / d T = 0$ . In (60) and (61) $Z _ { i }$ and $W _ { i }$ are the correlated standard normal random variables used in the simulation.

In Table 3 in the text, a hybrid (biased) estimator of gamma is also used. This hybrid estimator, based on a re-simulation of the pathwise delta estimator, is defined by

$$
G a m m a ( d ^ { 2 } p / d S _ { 0 } ^ { 2 } ) ; \frac { 1 } { h } ( e ^ { - r T } 1 _ { \{ \bar { S } ( S _ { 0 } + h ) \geq K \} } \frac { S _ { T } ( S _ { 0 } + h ) } { S _ { 0 } + h } - e ^ { - r T } 1 _ { \{ \bar { S } ( S _ { 0 } ) \geq K \} } \frac { S _ { T } ( S _ { 0 } ) } { S _ { 0 } } ) .\tag{62}
$$
