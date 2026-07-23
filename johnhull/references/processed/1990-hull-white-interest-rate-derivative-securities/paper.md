# 1990-hull-white-interest-rate-derivative-securities

<!-- page: 1 -->

## Pricing Interest-Rate-Derivative Securities

John Hull Alan White University of Toronto

This article shows that the one-state-variable interest-rate models of Vasicek (1977) and Cox, Ingersoll, and Ross (1985b) can be extended so that they are consistent with both the current term structure of interest rates and either the current volatilities of all spot interest rates or the current v o la t i l i t i e s of a l l for ward i n t er e s t ra t e s . Th e extended Vasicek model is shown to be very tractable analytically. The article compares option prices obtained using the extended Vasicek model with those obtained using a number of other models.

In recent years, interest-rate-contingent claims such as caps, swaptions, bond options, captions, and mortgage-backed securities have become increasingly popular. The valuation of these instruments is now a major concern of both practitioners and academics.

Practitioners have tended to use different models for valuing different interest-rate-derivative securities. For example, when valuing caps, they frequently assume that the forward interest rate is lognormal and use Black’s (1976) model for valuing options on commodity futures, The volatility of the forward rate is assumed to be a decreasing function of the time to maturity of the forward contract. When valuing European bond options and swaptions, practitioners often also use Black’s (1976) model. However, in this case, forward bond prices rather than forward interest rates are assumed to be lognormal.

This research was funded by the Social Sciences and Humanities Research Council of Canada. We would like to thank Michael Brennan, Emanuel Derman, Farshid Jamshidian, Cal Johnson, Mark Koenigsberg, John Rumsey, Armand Tatevossian, Yisong Tian, Stuart Turnbull, Ken Vetzel, and participants of finance workshops at Duke University, Queens University, and the University of Toronto for helpful comments on an earlier draft of this paper. Address reprint requests to John Hull, Faculty of Management, University of Toronto, 246 Bloor Street West, Toronto, Ontario, Canada M5S 1V4.

<!-- page: 2 -->

Using different models in different situations has a number of disadvantages. First, there is no easy way of making the volatility parameters in one model consistent with those in another model. Second, it is difficult to aggregate exposures across different interest-ratedependent securities. For example, it is difficult to determine the extent to which the volatility exposure of a swaption can be offset by a position in caps. Finally, it is difficult to value nonstandard securities.

Several models of the term structure have been proposed in the academic literature. Examples are Brennan and Schwartz (1979, 1982), Courtadon (1982), Cox, Ingersoll, and Ross (1985b), Dothan (1978), Langetieg (1980), Longstaff (1989), Richard (1979), and Vasicek (1977). All these models have the advantage that they can be used to value all interest-rate-contingent claims in a consistent way. Their major disadvantages are that they involve several unobservable parameters and do not provide a perfect fit to the initial term structure of interest rates.

Ho and Lee (1986) pioneered a new approach by showing how an interest-rate model can be designed so that it is automatically consistent with any specified initial term structure. Their work has been extended by a number of researchers, including Black, Derman, and Toy (1990), Dybvig (1988), and Milne and Turnbull (1989). Heath, Jarrow, and Morton (1987) present a general multifactor interest-rate model consistent with the existing term structure of interest rates and any specified volatility structure. Their model provides important theoretical insights, but in its most general form has the disadvantage that it is computationally quite time consuming.

In this paper, we present two one-state variable models of the shortterm interest rate. Both are consistent with both the current term structure of interest rates and the current volatilities of all interest rates. In addition, the volatility of the short-term interest rate can be a function of time. The user of the models. can specify either the current volatilities of spot Interest rates (which will be referred to as the term structure of spot rate volatilities) or the current volatilities of forward interest rates (which will be referred to as the term structure of forward rate volatilities). The first model is an extension of Vasicek (1977). The second model is an extension of Cox, Ingersoll, and Ross (1985b).

The main contribution of this paper is to show how the process followed by the short-term interest rate in the two models can be deduced from the term structure of interest rates and the term structure of spot or forward interest-rate volatilities. The parameters of the process can be determined analytically in the case of the extended Vasicek model, and numerically in the case of the extended Cox, Ingersoll, and Ross (CIR) model. Once the short-term interest rate process has been obtained, either model can be used to value any interest-rate contingent claim. European bond options can be valued analytically when the extended Vasicek model is used.

<!-- page: 3 -->

The analytic tractability of the extended Vasicek model makes it very appealing as a practical tool. It is therefore of interest to test whether the option prices given by this model are similar to those given by other models. In this paper we compare the extended Vasicek model with the one-factor CIR model and with two different twofactor models. The results are encouraging. They suggest that, if two models are fitted to the same initial term structure of interest rates, the same term structure of interest-rate volatilities, and the same data on the expected future instantaneous standard deviation of the short rate, the differences between the option prices produced by the models are small.

The rest of this paper is organized as follows. In Section 1, the properties of the Vasicek and CIR models are outlined. In Sections 2 and 3, extensions of the two models are developed. In Section 4, the way in which market data can be used to estimate the unknown functions in the models is discussed. In Section 5, the bond option and cap prices calculated using the extended Vasicek model are compared with their true values when interest rates are assumed to follow the one-factor CIR model. In Section 6, bond option prices calculated using the extended Vasicek model are compared with the true prices when interest rates are assumed to follow two different two-factor models. Conclusions are in Section 7.

## 1. The Vasicek and CIR Models

A number of authors have proposed one-state-variable models of the term structure in which the short-term interest rate, r, follows a meanreverting process of the form

$$
d r = a ( b - r ) d t + \sigma r ^ { \beta } d z ,\tag{1}
$$

where a, b, s, and b are positive constants and dz is a Wiener process. In these models, the interest rate, r, is pulled toward a level b at rate a. Superimposed upon this “pull” is a random term with variance $\sigma ^ { 2 } r ^ { 2 \beta }$ per unit time.

The situations where ${ \textrm { b } } = { \textrm { 0 } }$ and $\ b \ = \ 0 . 5$ are of particular interest because they lead to models that are analytically tractable. The $\flat =$ 0 case was first considered by Vasicek (1977), who derived an analytic solution for the price of a discount bond. Jamshidian (1989) showed that, for this value of b, it is also possible to derive relatively simple analytic solutions for the prices of European call and put options on both discount bonds and coupon-bearing bonds. One drawback of assuming $\boldsymbol { \mathsf { b } } = \boldsymbol { \mathsf { 0 } }$ is that the short-term interest rate, r, can become negative. CIR consider the alternative $\mathsf { b } = 0 . 5$ . In this case, r can, in some circumstances, become zero but it can never become negative. CIR derive analytic solutions for the prices of both discount bonds and European call options on discount bonds.

<!-- page: 4 -->

It is reasonable to conjecture that in some situations the market’s expectations about future interest rates involve time-dependent parameters. In other words, the drift rates and volatility of r may be functions of time as well as being functions of r and other state variables. The time dependence can arise from the cyclical nature of the economy, expectations concerning the future impact of monetary policies, and expected trends in other macroeconomic variables.

In this article we extend the model in (1) to reflect this time dependence. We add a time-dependent drift, $\pmb \theta ( t )$ to the process for r, and allow both the reversion rate, a, and the volatility factor, s, to be functions of time. This leads to the following model for r:

$$
d r = \{ \theta ( t ) + a ( t ) ( b - r ) \} d t + \sigma ( t ) r ^ { \rho } d z .\tag{2}
$$

This can be regarded as a model in which a drift rate, $\pmb \theta ( t )$ is imposed on a variable that would otherwise tend to revert to a constant level b. Since (2) can be written as

$$
d r = a ( t ) [ \theta ( t ) / a ( t ) + b - r ] d t + \sigma ( { \dot { t } } ) r ^ { \beta } d z ,
$$

it can also be regarded as a model in which the reversion level is a function, $\theta ( t ) / a ( \tilde { t } ) + b ,$ of time. We will examine the situations where $\boldsymbol { \mathsf { b } } = 0$ and $\mathsf { b } = 0 . 5$ . The $\boldsymbol { \mathsf { b } } = 0$ case is an extension of Vasicek’s model; the $\mathsf { b } = 0 . 5$ case is an extension of the CIR model. We will show that when appropriate assumptions are made about the market price of interest-rate risk, the model can be fitted to the term structure of interest rates and the term structure of spot or forward rate volatilities.

As shown by Dybvig (1988) and Jamshidian (1988), the continuous time equivalent of the Ho and Lee (1986) model is

$$
d r = \theta ( t ) \ d t + \sigma \ d z .
$$

This is the particular case of (2), where ${ \sf b } = 0 , a ( t ) = 0$ , and $\textsf { S } \left( t \right)$ is constant. If the market price of interest-rate risk is a function of time, $\theta ( t )$ can be chosen so that the model fits the initial-term structure of interest rates. The model has the disadvantage that it incorporates no mean reversion; the instantaneous standard deviations of all spot and forward rates are the same.

<!-- page: 5 -->

The continuous time equivalent of the Black, Derman, and Toy (1990) model can be shown to be

$$
d ( \log { r } ) = [ \theta ( t ) + ( \sigma ^ { \prime } ( t ) / \sigma ( t ) ) \log { r } ] d t + \sigma ( t ) \ d z .
$$

In this model log r is mean reverting. The function s (t) is chosen to make the model consistent with the term structure of spot rate volatilities and may not give reasonable values for the future short rate volatility. The model has the disadvantage that neither bond prices nor European bond option prices can be determined analytically.

## 2. The Extended Vasicek Model

Our proposed extension of Vasicek’s model is given by (2) with b ${ \ o } = 0 ^ { \cdot }$

$$
d r = [ \theta ( t ) + a ( t ) ( b - r ) ] d t + \sigma ( t ) d z .\tag{3}
$$

We will assume that the market price of interest-rate risk is a function of time, X(t), that is bounded in any interval (0, t). From Cox, Ingersoll, and Ross (1985a), this means that the price, $f ,$ of any contingent claim dependent on r must satisfy

$$
\begin{array} { r } { f _ { t } + [ \phi ( t ) - a ( t ) r ] f _ { r } + \frac { 1 } { 2 } \sigma ( t ) ^ { 2 } f _ { r r } - r f = 0 , } \end{array}\tag{4}
$$

where

$$
\phi ( t ) = a ( t ) b + \theta ( t ) - \lambda ( t ) \sigma ( t ) .
$$

The price of a discount bond that pays off \$1 at time T is the solution to (4) that satisfies the boundary condition $f = 1$ when $t = T .$ . Consider the function

$$
f = A \left( t , T \right) e ^ { - B \left( t , T \right) r } .\tag{5}
$$

This satisfies (4) and the boundary condition when

$$
A _ { t } - \phi ( t ) A B + { \textstyle { \frac { 1 } { 2 } } } \sigma ( t ) ^ { 2 } A B ^ { 2 } = 0\tag{6}
$$

and

$$
B _ { \ell } - a ( \ell ) B + 1 = 0 ,\tag{7}
$$

with

$$
A ( T , T ) = 1 ; B ( T , T ) = 0 .\tag{8}
$$

<sup>1</sup> This corresponds to the assumption made by Vasicek. In fact, the same final model is obtained if the market price of interest-rate risk is set equal to or even if it is set equal is the market price of risk, Girsanov’s theorem shows that for no arbitrage the condition must hold. Duffie (1988, p. 229) provides a discussion of this. The function presents no problems as far as this condition is concerned if we assume are always bounded in any interval

<!-- page: 6 -->

It follows that if (6) and (7) are solved subject to the boundary conditions in (8), Equation (5) provides the price of a discount bond maturing at time T. Solving (6) and (7) for the situation where $a ( t )$ $\phi ( t )$ , and $\sigma ( t )$ are constant leads to the Vasicek bond-pricing formula:

$$
\begin{array} { l } { { B ( t , T ) = ( 1 - e ^ { - a ( T - t ) } ) / a , } } \\ { { A ( t , T ) = \mathrm { e x p } \Bigg [ \frac { ( B ( t , T ) - T + t ) ( a \phi - \sigma ^ { 2 } / 2 ) } { 4 a ^ { 2 } } - \frac { \sigma ^ { 2 } B ( t , T ) ^ { 2 } } { 4 a } \Bigg ] . } } \end{array}
$$

The function, s (t), in the extended model should be chosen to reflect the current and future volatilities of the short-term interest rate, r. As will be shown later, $A ( O , \ T )$ and $B ( O , \ T )$ are defined by ${ \textsf { \textsf { S } } } \left( 0 \right)$ , the current term structure of interest rates, and the current term structure of spot or forward interest-rate volatilities. The first step in the analysis is therefore to determine $a ( t ) , \phi ( t ) , A ( t , T )$ , and $B ( t , T )$ in terms of $A ( O , \ T )$ $B ( O , \ T )$ , and s (t).

Differentiating (6) and (7) with respect to T, we obtain

$$
A _ { t T } - \phi ( t ) [ A _ { T } B + A B _ { T } ] + \sigma ( t ) ^ { 2 } [ A _ { T } B ^ { 2 } + 2 A B B _ { T } ] / 2 = 0 ,\tag{9}
$$

$$
\begin{array} { r } { B _ { t r } - \dot { a } ( t ) B _ { \tau } = 0 . } \end{array}\tag{10}
$$

Eliminating $a ( t )$ from (7) and (10) gives

$$
B , B _ { \tau } - B B _ { \tau \tau } + B _ { \tau } = 0 .\tag{11}
$$

Eliminating $\phi ( t )$ from (6) and (9) yields

$$
A B A _ { t T } - B A _ { t } A _ { T } - A A _ { t } B _ { T } + \sigma ( t ) ^ { 2 } A ^ { 2 } B ^ { 2 } B _ { T } / 2 = 0 .\tag{12}
$$

The boundary conditions for (11) and (12) are the known values of $A ( O , \ T )$ and $B ( O , \ T ) , \ A ( \ T , \ T ) \ = \ 1$ , and $B ( T , \ T ) \ = \ 0$ . The solutions to (11) and (12) that satisfy these boundary conditions are

$$
\begin{array} { l } { { \displaystyle { \cal B } ( t , T ) = \frac { { \cal B } ( 0 , T ) - { \cal B } ( 0 , t ) } { \displaystyle \partial { \cal B } ( 0 , t ) / \partial t } } , } \\ { { \displaystyle \hat { \cal A } ( t , T ) = \hat { \cal A } ( 0 , T ) - \hat { \cal A } ( 0 , t ) - { \cal B } ( t , T ) \frac { \partial \hat { \cal A } ( 0 , t ) } { \partial t } } } \\ { { \displaystyle ~ - \frac { 1 } { 2 } \biggl [ { \cal B } ( t , T ) \frac { \partial { \cal B } ( 0 , t ) } { \partial t } \biggr ] ^ { 2 } \int _ { 0 } ^ { t } \biggl [ \frac { \sigma ( \tau ) } { \partial { \cal B } ( 0 , \tau ) / \partial \tau } \biggr ] ^ { 2 } d \tau , } } \end{array}\tag{13}
$$

(14)

where $\hat { A } ( t , T ) = \log [ A ( t , T ) ]$ Substituting into (6) and (7), we obtain

$$
a ( t ) = - \frac { \partial ^ { 2 } B ( 0 , t ) / \partial t ^ { 2 } } { \partial \dot { B } ( 0 , t ) / \partial t } ,\tag{1 5}
$$

<!-- page: 7 -->

$$
\begin{array} { l } { \displaystyle \phi ( t ) = - \ a ( t ) \frac { \partial \hat { A } ( 0 , t ) } { \partial t } - \frac { \partial ^ { 2 } \hat { A } ( 0 , t ) } { \partial t ^ { 2 } } } \\ { \displaystyle \ + \left[ \frac { \partial B ( 0 , t ) } { \partial t } \right] ^ { 2 } \int _ { 0 } ^ { t } \left[ \frac { \sigma ( \tau ) } { \partial B ( 0 , \tau ) / \partial \tau } \right] ^ { 2 } d \tau . } \end{array}\tag{16}
$$

We now move on to discuss option valuation under the extended Vasicek model. Define $P ( r , \ t _ { I } , \ t _ { 2 } )$ as the price at time $t _ { l }$ of a discount bond maturing at time $t _ { 2 } .$ . From the above analysis,

$$
P ( r , t _ { 1 } , t _ { 2 } ) = A ( t _ { 1 } , t _ { 2 } ) e ^ { - B ( t _ { 1 } , t _ { 2 } ) r } .
$$

Using $\mathrm { I t o } ^ { \prime } \mathrm { s }$ lemma, the volatility of $P ( r , \ t _ { I } , \ t _ { 2 } )$ is $\textsf { s } ( t I ) B ( t I , \ t 2 )$ . Since this is independent of $r ,$ the distribution of a bond price at any given time conditional on its price at an earlier time must be lognormal.

Consider a European call option on a discount bond with exercise price X. Suppose that the current time is $t ,$ the option expires at time $T ,$ and the bond expires at time s $( s \ \geq T \geq t )$ . The call option can be regarded as an option to exchange X units of a discount bond maturing at time $T$ for one unit of a discount bond maturing at time $s .$ Define ${ \pmb { \alpha } } _ { 1 } ( { \pmb { \tau } } )$ and ${ \pmb { \alpha } } _ { 2 } ^ { \prime } ( \pmb { \tau } )$ as the volatilities at time $\pmb { \tau }$ of the prices of discount bonds maturing at times $T$ and $s ,$ respectively, and $\pmb { \rho } ( \pmb { \tau } )$ as the instantaneous correlation between the two bond prices. From the lognormal property mentioned above and the results in Merton (1973), it follows that the option price, $C ,$ is given by

$$
C = P ( r , \ t , s ) N ( b ) - X P ( r , \ t , T ) N ( b - \sigma _ { P } ) ,\tag{17}
$$

where

$$
\begin{array} { l } { { b = \displaystyle \frac { 1 } { \sigma _ { P } } \log \frac { P ( \boldsymbol { r } , \boldsymbol { t } , \boldsymbol { s } ) } { P ( \boldsymbol { r } , \boldsymbol { t } , T ) X } + \frac { \sigma _ { P } } { 2 } , } } \\ { { \sigma _ { P } ^ { 2 } = \displaystyle \int _ { \boldsymbol { t } } ^ { T } \left[ \alpha _ { 1 } ( \tau ) ^ { 2 } - 2 \rho ( \tau ) \alpha _ { 1 } ( \tau ) \alpha _ { 2 } ( \tau ) + \alpha _ { 2 } ( \tau ) ^ { 2 } \right] d \tau , } } \end{array}\tag{18}
$$

and $\mathbf { N } ( \mathbf { \partial } \cdot \mathbf { \partial } )$ is the cumulative normal distribution function. Since we are using a one-factor model, ${ \textsf { r } } = 1$ . Furthermore,

$$
\begin{array} { r } { \alpha _ { 1 } ( \tau ) = \sigma ( \tau ) B ( \tau , s ) , } \\ { \alpha _ { 2 } ( \tau ) = \sigma ( \tau ) B ( \tau , T ) . } \end{array}
$$

Hence,

$$
\sigma _ { P } ^ { 2 } = \int _ { t } ^ { T } \sigma ( \tau ) ^ { 2 } \big [ B ( \tau , s ) - B ( \tau , T ) \big ] ^ { 2 } ~ d \tau .
$$

<!-- page: 8 -->

From (13) this becomes

$$
\sigma _ { P } ^ { 2 } = \left[ B ( 0 , s ) - B ( 0 , T ) \right] ^ { 2 } \int _ { t } ^ { T } \left[ \frac { \sigma ( \tau ) } { \partial B ( 0 , \tau ) / \partial \tau } \right] ^ { 2 } d \tau .\tag{19}
$$

Equations (17) and (19) provide a simple analytic solution for European call option prices. European put option prices can be obtained using put-call parity. In the case where a and s are constant,

$$
\begin{array} { l } { { B ( \tau , s ) = \left( 1 - e ^ { - \alpha ( s - \tau ) } \right) / a , } } \\ { { B ( \tau , T ) = \left( 1 - e ^ { - \alpha ( T - \tau ) } \right) / a , } } \end{array}
$$

and (19) becomes

$$
\sigma _ { P } = v ( t , T ) ~ ( 1 - { e ^ { - a ( s - T ) } } ) / a ,
$$

where

$$
v ( t , \ T ) ^ { 2 } = \sigma ^ { 2 } ( 1 - e ^ { - 2 \alpha ( T - \delta ) } ) / 2 a .
$$

This is the result in Jamshidian (1989). It Is interesting to note that Jamshidian’s result does not depend on $\pmb \theta ( t )$ and being constant.

To value European options on coupon-bearing bonds, we note [similarly to Jamshidian (1989)] that since all bond prices are decreasing functions of $r ,$ an option on a portfolio of discount bonds is equivalent to a portfolio of options on the discount bonds with appropriate exercise prices? Consider a European call option with exercise price X and maturity Ton a coupon-bearing bond that pays off $c _ { i }$ at a time $s _ { i } > T \ ( 1 \ \pounds \ i \ \pounds \ n )$ . The option will be exercised when $r ( T )$ $< r ^ { * }$ , where $r ^ { * }$ is the solution to

$$
\sum _ { i = 1 } ^ { n } c _ { i } P ( r ^ { * } , T , s _ { i } ) = X .
$$

The payoff of the option is

$$
\mathrm { m a x } \Bigg [ 0 , \sum _ { i = 1 } ^ { n } c _ { i } P ( r , T , s _ { i } ) - X \Bigg ] .
$$

This is the same as

$$
\sum _ { i = 1 } ^ { n } c _ { i } \operatorname* { m a x } \bigl [ 0 , P ( r , T , s _ { i } ) - X _ { i } \bigr ] ,
$$

where

$$
X _ { i } = P ( r ^ { * } , T , s _ { i } ) .
$$

2 This argument can be used to value options on coupon-baring bonds in other one-state variable models. Later in this paper we will use it in conjunction with the CIR model.

<!-- page: 9 -->

The option on the coupon-bearing bond is therefore the sum of n options on discount bonds with the exercise price of the ith option being $X _ { i } .$

American bond options and other interest-rate-contingent claims can be valued by first calculating $a ( t )$ and $\phi ( t )$ from (15) and (16), and then using numerical procedures to solve the differential equation in (4) subject to the appropriate boundary conditions. One approach that can be used is described in Hull and White (1990).

## 3. The Extended CIR Model

Our proposed extension of the CIR model is given by (2) with ${ \textsf { b } } =$ 0.5:

$$
d r = [ \theta ( t ) + a ( t ) ( b - r ) ] d t + \sigma ( t ) \sqrt { r } d z .
$$

We assume that the market price of interest-rate risk is $\lambda ( t ) \sqrt { r }$ for some function l of time bounded in any interval $( 0 , \tau )$ .3

The ‘differential equation that must be satisfied by the price, $f ,$ of any claim contingent on r is

$$
\begin{array} { r } { f _ { t } + [ \phi ( t ) - \psi ( t ) r ] f _ { r } + \frac { 1 } { 2 } \sigma ( t ) ^ { 2 } r f _ { r } - r f { \bf { * } } \ 0 , } \end{array}\tag{20}
$$

where

$$
\dot { \mathbf { \rho } } _ { \ast } \mathbf { \dot { \mathbf { \rho } } } _ { \ast } \mathbf { \dot { \mathbf { \rho } } } _ { \ast } \mathbf { \dot { \mathbf { \rho } } } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \dot { \mathbf { \rho } } } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \dot { \mathbf { \rho } } } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast \ast } \mathbf { \rho } _ { \ast } \mathbf { \rho } _ { \ast \rho } _ { \ast \ast } \mathbf { \rho } _ { \rho } _ { \ast \mathbf { \rho } } _ { \mathbf { \rho } \mathbf { \rho } } _  \mathbf { \rho } \mathbf { \rho } _ { \rho } \mathbf { \rho } _ { \rho } \mathbf { \rho } \mathbf { \rho } _ { \rho \rho } \mathbf { \rho } \mathbf { \rho } \mathbf { \rho } \mathbf { \rho \rho } _ { \rho } \mathbf { \rho \rho } \mathbf { \rho \rho } \mathbf { \rho \rho \rho } { \rho \rho \rho } \mathbf { \rho \rho \rho \rho } \mathbf { \rho \rho \rho \rho \rho \mathbf } { \rho \rho \rho \rho \rho \rho \ c \ c }  \ c \ c \ c \ c \ c \ c \ c \ c
$$

and

$$
\psi ( t ) = a ( t ) + \lambda ( t ) \sigma ( t ) .
$$

Again, we consider the function

$$
f = A ( t , T ) e ^ { - B ( t , T ) r } .\tag{21}
$$

This satisfies (20) when

$$
A _ { t } - \phi ( t ) A B = 0\tag{22}
$$

and

$$
B _ { t } - \psi ( t ) B - { \textstyle \frac { 1 } { 2 } } \sigma ( t ) ^ { 2 } B ^ { 2 } + 1 = 0 .\tag{23}
$$

If A and B are the solutions to the ordinary differential equations (22) and (23) subject to the boundary conditions $A ( T , \ T ) \ = \ 1$ and $B ( T ,$ $T ) = 0 { \mathrm { : } }$ , Equation (21) gives the price at time t of a discount bond maturing at time T. Solving (22) and (23) for the situation where $\phi ( t ) , \psi ( t )$ , and $\sigma ( t )$ are constants leads to the CIR bond-pricing formula:

This corresponds to the assumption made by Cox, Ingersoll, and Ross. It is interesting to note that a market price of risk equal to appears to give rise to the same final model as However, It violates the no-arbitrage condition referred to in note 1.

<!-- page: 10 -->

$$
B ( t , T ) = \frac { 2 ( e ^ { \gamma ( T - t ) } - 1 ) } { ( \gamma + \psi ) ( e ^ { \gamma ( T - t ) } - 1 ) + 2 \gamma } ,\tag{24}
$$

$$
A ( t , T ) = \left[ \frac { 2 \gamma e ^ { ( \gamma + \psi ) ( T - t ) / 2 } } { ( \gamma + \psi ) ( e ^ { \gamma ( T - t ) } - 1 ) + 2 \gamma } \right] ^ { 2 + / { \sigma } ^ { 2 } } ,\tag{25}
$$

where

$$
\gamma = \sqrt { ( \psi ^ { 2 } + 2 \sigma ^ { 2 } ) } .
$$

The function $\textsf { S } \left( t \right)$ in the extended model should be chosen to reflect the current and future volatilities of the short-tern-interest rate. As in the case of the extended Vasicek model, $A ( O , \ T )$ and $B ( O , \ T )$ can be determined from s (0), the current term structure of interest rates and the current term structure of interest-rate volatilities. These, together with the conditions $A ( T , \quad T ) = 1$ and $B ( \textit { T } , \textit { T } ) \ : = \ : 0 .$ , are the boundary conditions for determining $A ( t , \ T )$ and $B ( t , \ T )$ from (22) and (23).

Differentiating (23) with respect to T and eliminating ${ \pmb \psi } ( t )$ w e obtain

$$
B _ { t } B _ { T } - B B _ { t T } + B _ { T } + \sigma ( t ) ^ { 2 } B ^ { 2 } B _ { T } / 2 = 0 .\tag{26}
$$

This equation can be solved using finite difference methods. The function ${ \pmb \psi } ( t )$ can then be obtained from (23). The solution to (22) is

$$
A ( t , T ) = A ( 0 , T ) \exp \left[ \int _ { 0 } ^ { t } \phi ( s ) B ( s , T ) \ d s \right] .\tag{27}
$$

Since $A ( T , \ T ) \ = 1 , \phi ( t )$ can be obtained iteratively from

$$
\int _ { 0 } ^ { \tau } \phi ( s ) B ( s , T ) \ d s = - \log A ( 0 , T ) .
$$

It does not appear to be possible to obtain European option prices analytically except when $\phi , \psi ,$ and $\pmb { \sigma }$ are constant. All option prices must therefore be computed using numerical procedures, such as those in Hull and White (1990).

## Fitting the Models to Market Data

In order to apply the models it is necessary to estimate the functions $A ( O , \ T )$ and $B ( O , \ T )$ . The Appendix derives results showing how the $B ( O , \ T )$ function is related to the term structure of spot and forward rate volatilities. Historical data can be used in conjunction with these results to estimate this function. $A ( O , \ T )$ can be calculated from $B ( O ,$ T) and the current term structure of interest rates using the bondpricing equation

<!-- page: 11 -->

$$
P ( r ( 0 ) , 0 , T ) = A ( 0 , T ) e ^ { - B ( 0 , T ) r ( 0 ) } ,
$$

where $r ( O )$ is the short-term interest rate at time zero.

An alternative approach to using historical data is to infer $A ( O , \ T )$ and B(0, T) from the term structure of interest rates and the prices of options. Caps are actively traded options that are particularly convenient for this purpose. In the case of the extended Vasicek model they allow B(0, T) to be implied directly in a relatively straightforward 4 way.

An interesting question is whether the functions $A ( t , \ T )$ and $B ( t ,$ T) estimated at some time $\pmb { \tau _ { 1 } }$ are the same as those estimated at another time $\tau _ { 2 } \left( \tau _ { 1 } , \tau _ { 2 } < t < T \right)$ In other words, does the same model describe the term structure of interest rates and the term structure of interestrate volatilities at two different times? This will be the subject of future empirical research. If it is found that the functions $A ( t , \ T )$ and $B ( t ,$ T) change significantly over time, it would be tempting to dismiss the model as being a “throw-away” of no practical value. However, this would be a mistake. It is important to distinguish between the goal of developing a model that adequately describes term-structure movements and the goal of developing a model that adequately values most of the interest-rate-contingent claims that are encountered in practice. it is quite possible that a two- or three-state variable model is necessary to achieve the first goal. Later in this paper we will present evidence supporting the argument that the extended Vasicek one-state-variable model achieves the second goal.

In this context it is useful to draw an analogy between the models used to describe stock-price behavior and our proposed model for interest rates. The usual model of stock-price behavior is the onefactor geometric Brownian motion model. This leads to the Black and Scholes (1973) stock-option-pricing model, which has stood the test of time and appears to be adequate for most purposes. Since stock-price volatilities are in practice stochastic, we cannot claim that a one-factor model perfectly represents stock-price behavior. Indeed, practitioners, when they use the Black-Scholes model, frequently adjust the value of the volatility parameter to reflect current market conditions. The justification for the Black-Scholes model is that, when fitted as well as possible to current market data, it gives similar option prices to more complicated two-state variable models.<sup>6</sup> Our justification of the one-factor models we have presented here will be simi l a r . <sup>7</sup>

4 As will be explained later, a cap is a portfolio of European put options on discount bonds. A matrix of cap prices can be used in conjunction with Equations (17) and (19) and put-call parity to obtain best-fit Values for points on the B(0, T) function.

<sup>5</sup> In fact, empirical research in Dybvig (1988) shows that a one-factor Vasicek-type model provides a surprisingly good fit to observed term structure movements.

<!-- page: 12 -->

Another interesting issue is whether the choice of the s (t) function affects the shape of the current term structure of interest-rate volatilities. Suppose that $R ( r , \ t , \ T )$ is the yield at time ton a discount bond maturing at time T. Ito’s lemma shows that the volatility of R in the general model of Equation (2) is $\sigma ( t ) \nearrow \bar { \sigma } R / \partial r .$ In the extended Vasicek model $( \textbf { b } = 0 ) \mathbf { , } \mathbf { \bar { \partial } } R / \partial r$ is independent of $\textsf { S } \left( t \right)$ . The function $\textsf { S } \left( t \right)$ therefore affects all discount-bond yield volatilities equally and has no effect on the shape of the term structure of volatilities. When b ¹ 0, the shape of the, term structure of volatilities is affected by $\textsf { S } \left( t \right)$ to the extent that $\partial R / \partial r$ is affected by the path followed by s between t and $T . ^ { \delta }$

## 5. Comparisons of One-Factor Models

Of the two models proposed in this article, the extended Vasicek model is particularly attractive because of its analytic tractability. A key question is whether it gives similar prices to other models when $A ( O , \ T )$ and $B ( O , \ T )$ are fitted to the initial-term structure of interest rates and the initial-term structure of interest-rate volatilities, and $\textsf { S } \left( t \right)$ is chosen to match the expected future instantaneous standard deviation of the short rate. In this section, we compare the bond-option prices and cap prices produced by the extended Vasicek model with those produced by the original one-factor CIR model. We also calculate volatilities implied by these prices when Black’s model is used.

Assume that are the parameters of the CIR model and that this model describes the true evolution of the term structure. This means that the $A ( O , \ T )$ and $B ( O , \ T )$ functions that would be estimated for the extended Vasicek model from historical data are

$$
\begin{array} { l } { { \dot { A } ( 0 , T ) = \left[ \frac { 2 \gamma e ^ { ( \gamma + \psi ) T / 2 } } { ( \gamma + \psi ) ( e ^ { \gamma T } - 1 ) + 2 \gamma } \right] ^ { 2 \phi / \sigma ^ { 2 } } , } } \\ { { \dot { B } ( 0 , T ) = \frac { 2 ( e ^ { \gamma T } - 1 ) } { ( \gamma + \psi ) ( e ^ { \gamma T } - 1 ) + 2 \gamma } , } } \end{array}\tag{29}
$$

<sup>6</sup> See Hull and White (1987) for a comparison of Black-Scholes with a two-factor stock-option-pricing model that incorporates stochastic volatility.

When using Black-Scholes, practitioners monitor their exposure to changes in the volatility parameter even though the model assumes that the parameter is constant. Similarly, when using the models suggested here, practitioners should monitor their exposure to (a) all possible shifts in the term structure of interest rates (not just those that are consistent with the model) and (b) all possible shifts in the term structure of volatilities.

8 In most circumstances we can expect to be relatively insensitive to the path followed by a(t).

<!-- page: 13 -->

where $\begin{array} { r } { \gamma = \sqrt { \psi ^ { 2 } + 2 \sigma ^ { 2 } } . } \end{array}$ The complete A and B functions for the extended Vasicek model can be calculated from $A ( O , \ T )$ and $B ( O , \ T )$ using (13) and (14). Equations (17) and (19) can be used to value European options on discount bonds. The analytic results in Cox, Ingersoll, and Ross (1985b) can be used to obtain the true European option prices.

The parameter values chosen were $\mathsf { s } = 0 . 0 6$ $\phi = 0 . 0 2 ,$ and $\pmb { \psi } = 0 . 2$ The initial short-term interest rate was assumed to be 10% per annum. For the extended Vasicek model, s (t) was set equal to the constant This ensured that the initial short-term interest-rate volatility equaled that in the CIR model.

## 5.1 Bond options

Table 1 shows the prices given by the two models for European call options on a five-year bond that has a face value of \$100 and pays a coupon of 10% per annum semiannually. It can be seen that the models give very similar prices for a range of different exercise prices and maturity dates. The biggest percentage differences are for deepout-of-the money options. The extended Vasicek model gives higher prices than CIR for these options. This is because very low interest rates (and, therefore, very high bond prices) have a greater chance of occurring in the extended Vasicek model.

Since the Black’s model is frequently used by practitioners to value bond options, it is interesting to compare it with the two models.<sup>10</sup> The numbers in parentheses in Table 1 are the forward bond-price volatilities implied by the option prices when Blacks model is used. It will be noted that the implied volatilities decline dramatically as the time to expiration of the option increases. In the limit, when the expiration date of the option equals the maturity date of the bond, the implied volatility is zero. For the extended Vasicek model, implied volatilities are roughly constant across different exercise prices. This is because the bond-price distributions are approximately lognormal.<sup>11</sup> Under CIR, the implied volatilities are a decreasing function of the exercise price. If the same volatility is used in Black’s model for all bond options with a certain expiration date, there will be a tendency under a CIR-type economy for in-the-money options to be underpriced and out-of-the-money options to be overpriced.

9 For both models, the bond option was decomposed into discount-bond options using the approach described in Section 2.

<sup>10</sup> Black’s model assumes that forward bond prices are lognormal in the case of options on discount bonds, it is equivalent to the extended Vasicek model, but does not provide a framework within which the volatilities of different forward bond prices can be related to each other.

<sup>11</sup> For a discount bond, the bond-price distribution is exactly lognormal. For a coupon-beating bond, it is the sum of lognormal distributions.

<!-- page: 14 -->

[Table source crop](assets/tables/1990-hull-white-interest-rate-derivative-securities-p0014-block-0001-73619bb3a00d8917.jpg)
Table 1 Prices of call options on a 5-year bond

## 5.2 Interest-rate caps

Consider an option that caps the interest rate on \$1 at $R _ { x }$ between times $t _ { l }$ and $t _ { 2 } .$ . The payoff from the option at time $t _ { 2 }$ is

$$
\Delta t \operatorname* { m a x } ( R \div R _ { x } , 0 ) ,
$$

where $\Delta t = t _ { 2 } - t _ { 1 }$ and R is the actual interest rate at time $t _ { I }$ for the time period $\left( t _ { I } , \ t _ { 2 } \right)$ . (Both R and $R _ { x }$ are assumed to be compounded once during the time period.)

The discounted value of this payoff is equivalent to

$$
( 1 + R _ { x } \Delta t ) \mathrm { m a x } \Bigg [ \frac { 1 } { 1 + R _ { x } \Delta t } - \frac { 1 } { 1 + R \Delta t } , 0 \Bigg ] ,
$$

at time $t _ { I } .$ . Since $1 / ( 1 + { \tt R } { \sf D } { \sf t } )$ is the value at time $t _ { I }$ of a bond maturing at time $t _ { 2 } ,$ , this expression shows that the option can be regarded as $1 { \bf \alpha } + { \pmb R } _ { \pmb { x } } \Delta { t }$ European puts with exercise price $1 / ( 1 ~ + ~ R _ { x } \Delta t )$ and expiration date $t _ { I }$ on a \$1 face value discount bond maturing at time $t _ { 2 } .$ More generally, an interest rate cap is a portfolio of European puts on discount bonds.

Table 2 shows the prices given by the two models for caps on the risk-free interest rate when the principal is \$100. Again, we see that the prices are very close for a range of different cap rates and maturities. The percentage differences between the prices are greatest for deep-out-of-the-money caps. CIR gives higher prices than extended

<!-- page: 15 -->

[Table source crop](assets/tables/1990-hull-white-interest-rate-derivative-securities-p0015-block-0001-e029b1d163c4520a.jpg)
Table 2 Prices of caps on the risk-free interest rate

Vasicek for these caps. This is because very high interest rates have a greater chance of occurring under CIR.

Practitioners frequently use Black’s (1976) model for valuing caps. The numbers in parentheses in Table 2 show the forward rate volatilities implied by the cap prices when Black’s model is used. It can be seen that the implied volatilities decrease as the life of the cap increases for both the extended Vasicek and CIR models. This is a reflection of the fact that the mean reversion of interest rates causes the volatility of a forward rate to decrease as the maturity of the forward contract increases. Implied volatilities also decrease as the cap rate increases for both models. This means that, if the same volatility is used for all caps with a certain life, there will be a tendency for Black’s model to underprice in-the-money caps. and overprice out-of-themoney caps.

## 6. Comparison with Two-Factor Models

In this section we test how well the extended Vasicek model can duplicate the bond option prices given by a two-factor model. We consider two different models. The first is a two-factor Vasicek model where the risk-neutral process for r is

$$
r = x _ { 1 } + x _ { 2 } , d x _ { i } = ( \phi _ { t } - a , x _ { i } ) d t + \sigma _ { i } d z _ { i } , i = 1 , 2 .\tag{30}
$$

We choose $\phi _ { 2 } = a _ { 2 } = 0$ This means that $\textsf { s } _ { 2 }$ equals the long-term rate’s instantaneous standard deviation. The second model is a two-factor

<!-- page: 16 -->

CIR model where the risk-neutral process for r is

$$
r = x _ { 1 } + x _ { 2 } , d x _ { i } = ( \phi _ { i } - \psi _ { i } x _ { i } ) d t + \sigma _ { i } \sqrt { x _ { i } } d z _ { i } , i = 1 , 2 .\tag{31}
$$

These types of models were analyzed by Langetieg (1980). In both cases we assume zero correlation between $d z _ { I }$ and $d z _ { 2 } .$

Discount bond prices for both models are given by

$$
P ( r , \ t , \ T ) = P _ { 1 } ( x _ { 1 } , \ t , \ T ) P _ { 2 } ( x _ { 2 } , \ t , \ T ) ,
$$

where

$$
P _ { \ell } ( x _ { t } , \ t , \ T ) = A _ { \ell } ( t , \ T ) e ^ { - B _ { i } ( t , \ T ) x _ { t } }
$$

denotes the price of a bond under the corresponding constant parameter one-factor model when the short-term rate is $x _ { I } .$ . When the extended Vasicek model is fitted to the two-factor Vasicek model

$$
\sigma ( 0 ) = \sqrt { \left( \sigma _ { 1 } ^ { 2 } + \sigma _ { 2 } ^ { 2 } \right) }
$$

and

$$
\sigma ( 0 ) B ( 0 , T ) = \sqrt { [ \sigma _ { 1 } ^ { 2 } B _ { 1 } ( 0 , T ) ^ { 2 } + \sigma _ { 2 } ^ { 2 } B _ { 2 } ( 0 , T ) ^ { 2 } ] } .
$$

When it is fitted to the two-factor CIR model

$$
\sigma ( 0 ) = \sqrt { \left( \sigma _ { 1 } ^ { 2 } x _ { 1 } + \sigma _ { 2 } ^ { 2 } x _ { 2 } \right) } .
$$

and

$$
\sigma ( 0 ) B ( 0 , T ) = \sqrt { [ \sigma _ { 1 } ^ { 2 } x _ { 1 } B _ { 1 } ( 0 , T ) ^ { 2 } + \sigma _ { 2 } ^ { 2 } x _ { 2 } B _ { 2 } ( 0 , T ) ^ { 2 } ] } .
$$

In both cases the prices of European call options on discount bonds can be calculated using (17) and (19). We assume that $\textsf { S } ( t )$ is constant.

For the two-factor Vasicek model the prices of European call options on discount bonds are given by (17) with<sup>12</sup>

$$
\sigma _ { P } ^ { 2 } = \Bigg [ v _ { 1 } ( t , T ) \frac { 1 - e ^ { - a _ { 1 } ( s - T ) } } { a _ { 1 } } \Bigg ] ^ { 2 } + \Bigg [ v _ { 2 } ( t , T ) \frac { 1 - e ^ { - a _ { 2 } ( s - T ) } } { a _ { 2 } } \Bigg ] ^ { 2 } ,
$$

where

$$
v _ { i } ( t , T ) \stackrel { _ { 2 } } { = } \frac { \sigma _ { i } ^ { 2 } ( 1 - e ^ { - 2 a _ { i } ( T - t ) } ) } { 2 a _ { i } } , \qquad i = 1 , 2 .
$$

To compute option prices under the two-factor CIR model, we used Monte Carlo simulation in conjunction with the antithetic variable technique. Each price was based on a total of 40,000 runs and the maximum standard error was 0.0043.

12 Note that an options on a coupon-bearing bond cannot be decomposed into a portfolio of options on discount bonds in the case of the two-factor models considered here.

<!-- page: 17 -->

[Table source crop](assets/tables/1990-hull-white-interest-rate-derivative-securities-p0017-block-0001-d5500385c98beed7.jpg)
Table 3 Values of European call options on a five-year discount bond with a face value of \$100

The results are shown in Tables 3 and 4. The extended Vasicek model produces prices that are very close to those of the other models. Other tests similar to those reported here have been carried out. In all cases we find that the extended Vasicek model provides a good analytic approximation to other more complicated models.

## 7. Conclusions

This paper has shown that the Vasicek and CIR interest-rate models can be extended so that they are consistent with both the currentterm structure of spot or forward interest rates and the current-term structure of interest-rate volatilities. In the case. of the extension to Vasicek’s model, the parameters of the process followed by the shortterm interest rate and European bond option prices can be determined analytically. This makes the model very attractive as a practical tool.

[Table source crop](assets/tables/1990-hull-white-interest-rate-derivative-securities-p0017-block-0006-59da6731619a7c91.jpg)
Values of European call options on a five-year discount bond with a face value of \$100

<!-- page: 18 -->

The extended Vasicek model can be compared to another interestrate model by fitting it to the initial term structure of interest rates, the initial term structure of interest-rate volatilities, and the expected future instantaneous standard deviation of short rate volatilities given by the other model, and then testing to see whether the interest-rate option prices it gives are significantly different from those of the other model. We have tested it against a variety of different one- and twofactor models in this way. Our conclusion is that it provides a good analytic approximation to the European option prices given by these other models.

## Appendix

In this appendix we derive the relationship between $B ( t , \ T )$ and the current-term structure of spot rate and forward rate volatilities. As is the usual convention, the term “volatility” will be used to refer to the standard deviation of proportional changes, not actual changes, in the value of a variable.

Define

$P ( r , t , T )$ price at time t of a discount bond maturing at time $T ;$

$R ( r , t , T )$ continuously compounded interest rate at time t applicable to period $\mathit { \Omega } ( t , \textit { T } )$

$\pmb { F } ( \pmb { r } , \pmb { t } , \pmb { T } _ { 1 } , \pmb { T } _ { 2 } )$ forward rate at time t corresponding at the time period $( T _ { I } , \ T _ { 2 } ) ;$

$\sigma , ( r , t )$ volatility of r at time $t ;$

$\sigma _ { R } ( r , t , T )$ volatility of $R ( r , \ t , \ T )$

$\sigma _ { p } ( r , t , T _ { 1 } , T _ { 2 } )$ volatility of $F ( r , \ t , \ T _ { I } , \ T _ { 2 } )$

In both models, P has the functional form

$$
P ( r , \ t , \ r ) = A ( t , \ T ) e ^ { - B ( t , \ r ) r } .\tag{A1}
$$

Since

$$
R ( r , t , T ) = - \frac { 1 } { T - t } \ln P ( r , t , T ) ,
$$

it follows that

$$
R ( r , t , \vec { T } ) = - \frac { 1 } { \vec { T } - t } \Big [ \ln A ( t , T ) - r B ( t , T ) \Big ]
$$

<!-- page: 19 -->

and

$$
\frac { \partial R ( r , \ell , T ) } { \partial r } = \frac { B ( t , T ) } { T - t } .
$$

From Ito’s lemma,

$$
R ( r , t , T ) \sigma _ { R } ( r , t , T ) = r \sigma _ { r } ( r , t ) \frac { \partial R ( r , t , T ) } { \partial r } .
$$

Hence,

$$
B ( t , T ) = \frac { R ( r , t , T ) \sigma _ { R } ( r , t , T ) ( T - t ) } { r \sigma _ { r } ( r , t ) } .\tag{A2}
$$

The forward rate, F, is related to spot rates by

$$
F ( r , \ t , \ T _ { 1 } , \ T _ { 2 } ) = \frac { R ( r , \ t , \ T _ { 2 } ) ( T _ { 2 } - \ t ) - R ( r , \ t , \ T _ { 1 } ) ( T _ { 1 } - \ t ) } { T _ { 2 } - \ T _ { 1 } } .
$$

Since $R ( r , \ t , \ T _ { I } )$ and $R ( r , \ t , \ T _ { 2 } )$ are instantaneously perfectly correlated in a one-state variable model, it follows from (A2) that

$$
F ( r , \ t , \ T _ { 1 } , \ T _ { 2 } ) \sigma _ { r } ( \dot { r } , \ t , \ T _ { 1 } , \ T _ { 2 } ) = \frac { B ( t , \ T _ { 2 } ) - B ( t , \ T _ { 1 } ) } { T _ { 2 } - T _ { 1 } } r \sigma _ { r } ( r , \ t )
$$

or

$$
B ( t , T _ { 2 } ) \ : - \ : B ( t , T _ { 1 } ) = \frac { F ( r , t , T _ { 1 } , T _ { 2 } ) \sigma _ { p } ( r , t , T _ { 1 } , T _ { 2 } ) ( T _ { 2 } - T _ { 1 } ) } { r \sigma _ { r } ( r , t ) } .\tag{A3}
$$

Equation (A2) enables $B ( O , \ T )$ be determined for all T from the current term structure of spot rate volatilities. Equation (A3) enables $B ( O , \ T )$ to be determined from the current term structure of forward rate volatilities. $A ( O , \ T )$ can be determined from $B ( O , \ T )$ and the current term structure of interest rates using (A1). Thus, A(0, T) and $B ( O , \ T )$ can be determined for all T from the current-term structure of interest rates and the current-term structure of spot rate or forward rate volatilities.

## References

Black, F., 1976, “The Pricing of Commodity Contracts,” Journal Financial Economics, 3, 167- 179. Black, F., and M. Scholes, 1973, “The Pricing of Options and Corporate Liabilities,” Journal of Political Economy, 81, 637-659. Black, F., E. Derman, and W. Toy, 1990, “A One-Factor Model of Interest Rates and Its Application to Treasury Bond Options,” Financial Analysts Journal, Jan-Feb. 33-39. Brennan, M. J., and E. S. Schwartz, 1979, “A Continuous Time Approach to the Pricing of Bonds,” Journal of Banking and Finance, 3, 133-155.

<!-- page: 20 -->

Brennan, M. J., and E. S. Schwartz, 1982, “An Equilibrium Model of Bond Pricing and a Test of Market Efficiency,” Journal of Financial and Quantitative Analysis, 17, 301-329. Courtadon, G., 1982, “The Pricing of Options on Default-Free Bonds,” Journal of Financial and Quantitative Analysis, 17, 75-100. Cox, J. C., J. E. Ingersoll, and S. A. Ross, 1985a, “An Intertemporal General Equilibrium Model of Asset Prices,” Econometrica, 53, 363-384. Cox, J. C., J. E. Ingersoll, and S. A. Ross, 1985b, “A Theory of the Term Structure of Interest Rates,” Econometrica, 53, 385-467. Dothan, L. U., 1978, “On the Term Structure of Interest Rates,” Journal of Financial Economics, 6, 59-69. Duffie, D., 1988, Security Markets: Stochastic Models, Academic, Boston, MA. Dybvig, P. H., 1988, “Bond and Bond Option Pricing Based on the Current Term Structure,” working paper, Olin School of Business, University of Washington. Heath, D., R. Jarrow, and A. Morton, 1987, “Bond Pricing and the Term Structure of Interest Rates: A New Methodology for Contingent Claims Evaluation,” working paper, Cornell University. Ho, T. S. Y., and S.-B. Lee, 1986, ‘Term Structure Movements and Pricing of Interest Rate Claims,” Journal of Finance, 41, 1011-1029. Hull, J., and A. White, 1987, “The Pricing of Options on Assets with Stochastic Volatilities,” Journal of Finance, 42, 281-300. Hull, J., and A. White, 1990, “Valuing Derivative Securities Using the Explicit Finite Difference Method,” Journal of Financial and Quantitative Analysis, 25, 87-100. Jamshidian, F., 1988, “The One-Factor Gaussian Interest Rate Model: Theory and Implementation,” working paper, Financial Strategies Group, Merrill Lynch Capital Markets, New York. Jamshidian, F., 1989, “An Exact Bond Option Formula,” Journal of Finance, 44, 205-209. Langetieg, T. C., 1980, “A Multivariate Model of the Term Structure,” Journal of Finance, 35, 71-97. Longstaff, F. A., 1989, “A Nonlinear General Equilibrium Model of the Term Structure of Interest Rates,” Journal of Financial Economics, 23,195-224. Merton, R. C., 1973, “Theory of Rational Option Pricing,” Bell Journal of Economics and Management Science, 4, 141-183. Milne, F., and S. Turnbull, 1989, “‘A Simple Approach to Interest Rate Option Pricing,” working paper, Australian National University. Richard, S., 1979, “An Arbitrage Model of the Term Structure of Interest Rates,” Journal of Financial Economics, 6, 33-57. Vasicek, O. A., 1977, “An Equilibrium Characterization of the Term Structure,” Journal of Financial Economics, 5, 177-188.
