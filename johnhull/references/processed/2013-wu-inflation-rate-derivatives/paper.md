# 2013-wu-inflation-rate-derivatives

<!-- page: 1 -->

## Inflation-rate Derivatives: From Market Model to Foreign Currency Analogy

Lixin Wu∗ Department of Mathematics University of Science and Technology Clear Water Bay, Kowloon Hong Kong

First version: August 1, 2008 This version: January 4, 2010

arXiv:1302.0574v1 [q-fin.PR] 4 Feb 2013

<sup>∗</sup>Part of the results have already been published in I want to thank participants of Financial Mathematics Seminar in Peking University in December 18, 2007, and BFS 2008 Congress, London, for their comments. All errors are ours. Email: malwu@ust.hk.

<!-- page: 2 -->

## Abstract

In this paper, we establish a market model for the term structure of forward inflation rates based on the risk-neutral dynamics of nominal and real zero-coupon bonds. Under the market model, we can price inflation caplets as well as inflation swaptions with a formula similar to the Black’s formula, thus justify the current market practice. We demonstrate how to further extend the market model to cope with volatility smiles. Moreover, we establish a consistency condition on the volatility of real zero-coupon bonds using arbitrage arguments, and with that re-derive the model of Jarrow and Yildirim (2003) with real forward rates based on “foreign currency analogy”, and thus interconnect the two modeling paradigms.

Key words: Consumer Price Index, inflation rates, market model, zerocoupon and year-on-year inflation swaps, inflation caps, inflation floors and inflation swaptions.

<!-- page: 3 -->

## 1 Introduction

“Foreign currency analogy” has been the standard technology for modeling inflation-linked derivatives (Barone and Castagna, 1997; Bezooyen et al. 1997; Hughston, 1998; Jarrow and Yildirim, 2003). In this approach, real interest rate, defined as the diference between nominal interest rate and inflation rate, is treated as the interest rate of a foreign currency, while the consumer price index (CPI) is treated as the exchange rate between domestic and the foreign currency. To price inflation derivatives, one needs to model nominal (domestic) interest rate, foreign (real) interest rate, and the exchange rate (CPI). A handy solution for modeling inflation derivatives is to adopt the Heath-Jarrow-Morton’s (1992) framework separately for both interest rates, and bridge them with a lognormal exchange-rate process. For a comprehensive yet succinct introduction of the pricing model under the so-called “HJM foreign currency analogy”, we refer readers to Manning and Jones (2003).

Although elegant in theory, a Heath-Jarrow-Morton type model is known to be inconvenient for derivatives pricing. The model takes unobservable instantaneous nominal and real forward rates as state variables, making it hard to be calibrated to most inflation derivatives, as their payofs are written on CPI or simple compounding inflation rates.

Aimed at more convenient pricing and hedging of inflation derivatives, a number of alternative models have been developed over the years. These models typically adopt lognormal dynamics for certain observable inflationrelated variables, for examples, CPI index (Belgrade and Benhamou, 2004; Belgrade et al., 2004) or forward price of real zero-coupon bonds (Kazziha, 1999; Mercurio, 2005). Recently extensions of models along this line have incorporated more sophisticated driving dynamics like stochastic volatility (Mercurio and Moreni, 2006 and 2009) and a jump-difusion (Hinnerich, 2008). Besides, there are also papers that address various issues in inflationrate modeling, like ensuring positive nominal interest rates by Cairns (2000), and estimating inflation risk premiums by Chen et al. (2006), among others. Although most of these models achieve closed-form pricing for certain derivatives, they carry various drawbacks, from complexity of pricing to not being a proper term structure model that describes the co-evolution of nominal interest rates and inflation rates. In the meantime, market practitioners have generally adopted a model of their own, the so-called market model based on displaced difusion dynamics for “forward inflation rates”<sup>1</sup>. The market model of practitioners, however, has not appeared in literature available to public.

<!-- page: 4 -->

In this paper, we put the market model in a rigorous footing. We take, in particular, nominal zero-coupon bonds and real zero-coupon bonds as model primitives, define the term structure of forward inflation rates, and rigorously establish the practitioners’ market model, where forward inflation rates follow displaced-difusion processes. Such displaced difusion processes lead naturally to a Black like formula for inflation caplets, and, after some light approximations, inflation swaptions. Owing to this closed-form formula, the market model can be calibrated to inflation caps, floors and swaptions using an existing technology for calibrating the LIBOR market model. For theoretical interests, we also establish a HJM type model for instantaneous inflation forward rates.

There are a number of important results arisen from our research. First, we define forward inflation rates based on arbitrage arguments, which is thus unique and thus should change the situation of the coexistence of multiple “forward inflation rates” in literature. Second, we establish that the martingale property of forward inflation rates under their own cash-flow measures<sup>2</sup>. Third and perhaps most importantly, we discover a so-called consistency condition, a necessary condition for the absence of arbitrage with the volatilities of nominal and real zero-coupon bonds, and show under this condition that the model we have developed with forward inflation rates is actually consistent with the model developed by Jarrow and Yildirim (2003) with forward real rates, in the sense that we can derive one model from the other. Fourth, the pricing of year-on-year inflation-index swaps becomes model free. Lastly, we have clarified that the volatility of the CPI index should be zero<sup>3</sup>, which somehow undermines the notion of “foreign currency analogy” for inflation derivatives.

The extended market model for inflation rates also serves as a platform for developing more comprehensive models. For instance, in order to capture volatility smiles or skews of inflation derivatives, one may adopt stochastic volatilities or jumps to the driving dynamics, in pretty much the same ways these random dynamics are incorporated into the standard LIBOR market model. We refer readers to Brigo and Mercurio (2006) for a comprehensive introductions of extensions to LIBOR market models.

<sup>1</sup>There exist various version of “forward inflation rates” in literature.

<sup>2</sup>A forward measure with delivery date equal to the maturity date of the forward inflation rate.

<sup>3</sup>Thanks for the comments of an anonymous referee.

<!-- page: 5 -->

The rest of the paper is organized as follows. In section 2, we introduce major inflation derivatives and highlight real zero-coupon bonds, part of our primitive state variables. In section 3, we define the notion of forward inflation rates and establish an extended market model. We then present pricing formulae of major inflation-rate derivatives under the extended market model. A Heath-Jarrow-Morton type model in terms of continuous compounding forward nominal and inflation rates is also established as a limiting case. Section 4 is devoted to the pricing of inflation-indexed swaption under the market model, where we produce a closed-form formula for swaption prices. In section 5, we will discuss the comprehensive calibration of the market model, and demonstrate calibration results with market data. In section 6, we demonstrate the construction of of smile models with in particular the SABR-type extension of the market model. Finally in section 7 we conclude the paper. The proofs of some propositions are put in the appendix.

## 2 CPI Index and Inflation Derivatives Market

Inflation-rate security markets have evolved steadily over the last decade, with the outstanding notional values growing from about 50 billion dollars in 1997 to over 1 trillion dollars in 2007. There are inflation-linked securities in most major currencies, including pound, Canadian dollar, yen and of course, Euro and U.S. dollar. The global daily turnover on average exceeded \$3 billions a day in 2007, which is largely dominated by Euro and dollar denominated securities. Nonetheless, by comparing to the sizes of LIBOR or credit markets, one has to conclude that the interest on inflation securities has been tepid in the past, but there are encouraging signs that the situation is changing (Jung, 2008).

The payof functions of inflation-linked securities depend on inflation rates, which are defined using Consumer Price Index (CPI). The CPI represents an average price of a basket of services and goods, the average price is compiled by oficial statistical agencies of central governments. The evolution of CPI indexes in both Europe and United States are displayed in Figure 1, which show a trend of steady increase. Since 2008 there has been a concern on the possible escalation of inflation in the near future.

<!-- page: 6 -->

![](assets/figures/2013-wu-inflation-rate-derivatives-p0006-block-0002-a6b95ac7bda5c34a.jpg)

![Figure 1 Consumer Price Indexes of United States and Euro zone](assets/figures/2013-wu-inflation-rate-derivatives-p0006-block-0003-1c44ad0c066bd1bb.jpg)

The inflation rate of a country is defined in terms of its CPI. Denote by $I ( t )$ the CPI of time t, then the inflation rate over the time period $[ t , T ]$ is defined as the percentage change of the index:

$$
\hat { i } ( t , T ) = \frac { I ( T ) } { I ( t ) } - 1 .
$$

For comparison purpose, we will more often use annualized inflation rate,

$$
i ( t , T ) = \frac { 1 } { T - t } \left( \frac { I ( T ) } { I ( t ) } - 1 \right) .
$$

Suppose the limit of the annualized inflation rate exists for $T t$ from above, we obtain the so-called instantaneous inflation rate, i(t), which will be used largely for mathematical and financial arguments instead of modeling. An important feature that distinguishes inflation rates from interest rates is that the former can be either positive or negative, while the latter have to be positive or otherwise we have a situation of arbitrage.

The dollar-denominated inflation-link securities have been predominately represented by Treasury Inflation Protected Securities (TIPS), followed by zero-coupon inflation-indexed swap (ZCIIS) and year-on-year inflation-indexed swap (YYIIS). In recent years, caps, floors and swaptions on inflation rates have been gaining popularity. The TIPS are issued by the Treasury Department of the United States and the governments of several major industrial nations, while other derivatives are ofered and traded in the OTC markets. We emphasize here that, unlike the market model currently in use, ZCIIS are taken as the underlying securities of the inflation derivatives markets and used for the construction of “inflation forward rates”.

<!-- page: 7 -->

To understand the roles of the basic securities in model building, we need set up the economy in mathematical terms. The uncertain economy is modeled by a filtered probability space $( \Omega , \mathcal { F } , \{ \mathcal { F } _ { t } \} _ { t \in [ 0 , \tau ] } , Q )$ for some $\tau > 0$ where $Q$ is the risk neutral probability measure under the uncertain economical environment, which can be defined in a usual way in an arbitragefree market (Harrison and Krep, 1979; Harrison and Pliska, 1981), and the filtration $\{ \mathcal { F } _ { t } \} _ { t \in [ 0 , \tau ] }$ is generated by a d-dimensional Q Brownian motion $Z = \{ Z _ { t } : t \geq 0 \}$

Next, we will spend some length to describe these inflation-linked securities.

## 2.1 TIPS

TIPS are coupon bonds with fixed coupon rates but floating principals, and the latter is adjusted according to the inflation rate over the accrual period of a coupon payment. Note that typically there is a floor on the principal value of a TIPS, which is often the initial principal value. The existence of floors, as a matter of fact, turns TIPS into coupon bonds with embedded options. So the rigorous pricing of TIPS needs a model.

Note that the CPI index is measured with a two-month lag. Yet this lagged index plays the role of the current index for the principal adjustments of TIPS and the payof calculations of inflations derivatives. For pricing purpose, lagging or not makes no diference. With this understanding in mind, we will treat the lagged index as the current index throughout the paper.

## 2.2 ZCIIS

The zero-coupon inflation-indexed swap (ZCIIS) is a swap contract between two parties with a single exchange of payments. Suppose that the contract was initiated at time t and will be expired at $T$ , then the payment of one party equals to a notional value times to the inflation rate over the contract period, i.e.

$$
N o t . \times \hat { i } ( t , T ) ,
$$

while the counterparty makes a fixed payment in the amount

$$
N o t . \times \left( ( 1 + K ( t , T ) ) ^ { T - t } - 1 \right) .
$$

<!-- page: 8 -->

Here, Not. is the notional value of the contract and $K ( t , T )$ is the quote for the contract. Because the value of the ZCIIS is zero at initiation, ZCIIS directly renders the price of the so-called real zero-coupon bond which pays inflation adjusted principal:

$$
P _ { R } ( t , T ) = E ^ { Q } \left[ e ^ { - \int _ { t } ^ { T } r _ { s } d s } { \frac { I ( T ) } { I ( t ) } } \Bigg | { \mathcal { F } } _ { t } \right] = P ( t , T ) ( 1 + K ) ^ { T - t } .\tag{1}
$$

Here, $\textstyle P ( t , T )$ is the nominal discount factor from T back to t. For real zerocoupon bonds with the same maturity date T but an earlier issuance date, say, $T _ { 0 } < t .$ , the price is

$$
P _ { R } ( t , T _ { 0 } , T ) = E ^ { Q } \left[ e ^ { - \int _ { t } ^ { T } r _ { s } d s } \frac { I ( T ) } { I ( T _ { 0 } ) } \bigg | \mathcal { F } _ { t } \right] = \frac { I ( t ) } { I ( T _ { 0 } ) } P _ { R } ( t , T ) .\tag{2}
$$

We emphasize here that $P _ { R } ( t , T _ { 0 } , T )$ , but not $P _ { R } ( t , T )$ , is treated as the time t price of a traded security. The latter is merely the initial price of a new security.

For modeling inflation-rate derivatives, we will take the term structure of real zero-coupon bonds, $P _ { R } ( t , T _ { 0 } , T )$ , for a fixed $T _ { 0 } \leq t$ and for all $T \geq t ,$ , as model primitives. Let us explain why we use index R instead of I for real zero-coupon bond defined in (2). This price alone actually carries information on real interest rates instead of inflation rates in the future. In fact, let $i ( t )$ denote the instantaneous inflation rate, then it relates to CPI by

$$
\frac { I ( T ) } { I ( T _ { 0 } ) } = e ^ { \int _ { T _ { 0 } } ^ { T } i ( s ) d s } .\tag{3}
$$

Plugging (3) into (2) yields, by Fisher’s equation (Fisher, 1930; also see Cox, Ingersoll and Ross, 1985),

$$
r ( t ) = R ( t ) + i ( t ) ,\tag{4}
$$

where $R ( t )$ is the real interest rate, we have

$$
\begin{array} { l } { \displaystyle P _ { R } ( t , T _ { 0 } , T ) = \frac { I ( t ) } { I ( T _ { 0 } ) } E ^ { Q } \left[ e ^ { - \int _ { t } ^ { T } ( r _ { s } - i ( s ) ) d s } | \mathcal { F } _ { t } \right] } \\ { \displaystyle = \frac { I ( t ) } { I ( T _ { 0 } ) } E ^ { Q } \left[ e ^ { - \int _ { t } ^ { T } R _ { s } d s } | \mathcal { F } _ { t } \right] , } \end{array}\tag{5}
$$

<!-- page: 9 -->

According to (5), the real zero-coupon bond implies the discount factor associated to real interest rate. This is the reason why we use the subindex $^ { 6 6 }$ for the price.

We emphasize here that we do not need the real interest rate for modeling or pricing purpose, which is unobservable and thus is not a good candidate for state variables.

## 2.3 YYIIS

Year-on-year inflation-indexed swaps are contracts to swap an annuity against a sequence of floating payments indexed to inflation rates over future periods. The fixed-leg payments of a YYIIS are Not. $\Delta \phi _ { i } K , i = 1 , 2 , \ldots , N _ { x } ,$ where $\Delta \phi _ { i }$ is the year fractions between two consecutive payments, while the floating-leg payments are of the form

$$
N o t . \left( \frac { I ( T _ { j } ) } { I ( T _ { j - 1 } ) } - 1 \right) ,
$$

and are made at time $T _ { j } , j = 1 , 2 , . . . , N _ { f }$ . Note that the payment gaps $\Delta \phi _ { i } = \phi _ { i } - \phi _ { i - 1 }$ and $\Delta T _ { j } = T _ { j } - T _ { j - 1 }$ can be diferent, and the term for payment swaps are the same, i.e., $\begin{array} { r } { \sum _ { i = 1 } ^ { N _ { x } } \Delta \phi _ { i } = \sum _ { j = 1 } ^ { N _ { f } } \Delta T _ { j } } \end{array}$ . The price of the P PYYIIS equals to the diference in values of the fixed and floating legs. The former can be calculated by discounting, yet the later involves the evaluation of an expectation:

$$
V _ { f l o a t } ^ { ( j ) } ( t ) = N o t . E ^ { Q } [ e ^ { - \int _ { t } ^ { T _ { j } } r _ { s } d s } ( \frac { I ( T _ { j } ) } { I ( T _ { j - 1 } ) } - 1 ) | { \mathcal { F } } _ { t } ] .
$$

The valuation of the floating leg will again need a model.

## 2.4 Inflation Caps and Floors

An inflation cap is like a YYIIS with optionality: with the same payment frequency, payments are made only when a netted cash flow to the payer (of the fixed leg) is positive, corresponding to cash flows of the following form to the cap holder

$$
N o t . \Delta T _ { i } \left[ \frac { 1 } { \Delta T _ { i } } \left( \frac { I ( T _ { i } ) } { I ( T _ { i - 1 } ) } - 1 \right) - K \right] ^ { + } , i = 1 , \dots , N .
$$

<!-- page: 10 -->

Accordingly, the cash flows of an inflation floor is

$$
N o t . \Delta T _ { i } \left[ K - \frac { 1 } { \Delta T _ { i } } \left( \frac { I ( T _ { i } ) } { I ( T _ { i - 1 } ) } - 1 \right) \right] ^ { + } , i = 1 , \dots , N .
$$

Apparently, the pricing of both caps and floors requires a model as well.

## 2.5 Inflation Swaptions

An inflation swaption is an option to enter into a YYIIS swap in the future. At maturity of the option, the holder of the option should enter into the underlying YYIIS if the option is in-the-money. Up to now the pricing of the inflation swaps has been model dependent, but the situation should change with the establishment of the theory of this paper.

## 3 The Market Model

## 3.1 Inflation Discount Bonds

We construct models based on the dynamics of the term structures of nominal and real bonds, $\{ P ( t , T ) , \forall T \ \geq \ t \}$ and $\{ P _ { R } ( t , T _ { 0 } , T ) , \forall T \ge t \ge T _ { 0 } \}$ , two sequences of tradable securities. Under the risk neutral measure $Q , P ( t , T )$ is assumed to follow the lognormal process

$$
d P ( t , T ) = P ( t , T ) \left( r _ { t } d t + \Sigma ( t , T ) \cdot d \pmb { Z } _ { t } \right) ,\tag{6}
$$

where $r _ { t }$ is the risk-free nominal (stochastic) interest rate, $\Sigma ( t , T )$ is a $d -$ dimensional volatility vector of $\textstyle P ( t , T )$ and “ ” means scalar product. We shall assume that $\Sigma ( t , T )$ is a suficiently regular deterministic function on t so that the SDE (6) admits a unique strong solution. Note that $\Sigma ( t , T )$ can be an -adaptive (stochastic) function. Furthermore, we also assume $\begin{array} { r } { \Sigma _ { T } ( t , T ) = \frac { \partial \Sigma ( t , T ) } { \partial T } } \end{array}$ exists and $\begin{array} { r } { E ^ { Q } [ \int _ { 0 } ^ { T } \| \Sigma _ { T } ( s , T ) \| ^ { 2 } d s ] < \infty } \end{array}$

RBy using Ito’s lemma, we have the following process for ln $\textstyle P ( t , T )$

$$
d \ln P ( t , T ) = \left( r _ { t } - \frac { \| \Sigma ( t , T ) \| ^ { 2 } } { 2 } \right) d t + \Sigma ( t , T ) \cdot d Z _ { t } ,\tag{7}
$$

where $\| x \| ^ { 2 } = x \cdot x$ for $x \in \mathbb { R } ^ { d }$ . Diferentiating equation (7) with respect to the maturity $T$ , we have

$$
d f ( t , T ) = \Sigma _ { T } ( t , T ) \cdot \Sigma ( t , T ) d t - \Sigma _ { T } ( t , T ) \cdot d Z _ { t } ,\tag{8}
$$

<!-- page: 11 -->

where $\begin{array} { r } { f ( t , T ) = - \frac { \partial \ln P ( t , T ) } { \partial T } } \end{array}$ is the nominal instantaneous forward rate of maturity $T .$ . Equation (8) is the well-known Heath-Jarrow-Morton equation (Heath et al. 1992) for term structure of nominal interest rates, which states that, under the risk neutral measure $Q$ , the drift term of the forward rate is a function of its volatility.

The dynamics of $P _ { R } ( t , T _ { 0 } , T )$ under the risk neutral measure $Q$ , meanwhile, is also assumed to be lognormal:

$$
d P _ { R } ( t , T _ { 0 } , T ) = P _ { R } ( t , T _ { 0 } , T ) \left( r _ { t } d t + \Sigma _ { R } ( t , T ) \cdot d { \cal Z } _ { t } \right) ,\tag{9}
$$

where $\Sigma _ { R } ( t , T )$ is the d-dimensional volatility vector of $P _ { R } ( t , T _ { 0 } , T )$ and satisfies the similar regularity conditions as $\Sigma ( t , T )$ does. One can easily justifies that, using (1) and $( 2 ) , \Sigma _ { R } ( t , T )$ should be independent of $T _ { 0 }$

To define the term structure of inflation rates, we first introduce the notion of discount bond or discount factor associated to inflation rate, using $\textstyle P ( t , T )$ and $P _ { R } ( t , T )$ , the nominal and real discount bond prices or factors.

Definition 1: The discount bond associated to inflation rate is defined by

$$
P _ { I } ( t , T ) \triangleq \frac { P ( t , T ) } { P _ { R } ( t , T ) } .\tag{10}
$$

Here, ${ \mathfrak { s o } } { \underline { { \underline { { \triangle } } } } } , { \mathfrak { s } }$ means “being defined $\mathrm { b y } ^ { \mathrm { y } }$

Alternatively, with $\textstyle P _ { I } ( t , T )$ and $P _ { R } ( t , T )$ , we efectively factorize the nominal discount factor into real and inflation discount factors:

$$
P ( t , T ) = P _ { R } ( t , T ) P _ { I } ( t , T ) .\tag{11}
$$

Note that neither $\textstyle P _ { I } ( t , T )$ nor $P _ { R } ( t , T )$ is a price of a tradable security<sup>4</sup>, but they both are observable. For later uses, we denote

$$
P _ { I } ( t , T _ { 0 } , T ) = \frac { P ( t , T ) } { P _ { R } ( t , T _ { 0 } , T ) } ,\tag{12}
$$

so there is

$$
P _ { I } ( t , T ) = \frac { I ( t ) } { I ( T _ { 0 } ) } P _ { I } ( t , T _ { 0 } , T ) .\tag{13}
$$

<sup>4</sup>P<sub>R</sub>(t, T ) is treated as the price of a zero-coupon bond of a virtue “foreign currency” by Jarrow and Yildirim (2003).

<!-- page: 12 -->

Note that $P _ { I } ( t , T _ { 0 } , T )$ as well as $\textstyle P _ { I } ( t , T )$ are defined for $t > T$ as well, through a constant extrapolation:

$$
P _ { I } ( t , T _ { 0 } , T ) = P _ { I } ( T , T _ { 0 } , T ) , \quad \forall t \geq T .\tag{14}
$$

This is because that $P _ { I } ( t , T _ { 0 } , T )$ is the ratio between $\textstyle P ( t , T )$ and $P _ { R } ( t , T _ { 0 } , T )$ At time $T$ , both securities mature into money market account, and the ratio stays unchange since then.

## 3.2 Market Model for Inflation Derivatives

It can be seen that the cash flows of several major inflation-indexed instruments, including YYIIS, inflation caplets and floorlets, are expressed in terms of forward inflation term rates (or simple inflation rates). We define a inflation forward rate as the return implied by the inflation discount factor.

Definition 2: The inflation forward rate for a future period $[ T _ { 1 } , T _ { 2 } ]$ seen at time $t \leq T _ { 2 }$ is defined by

$$
f ^ { ( I ) } ( t , T _ { 1 } , T _ { 2 } ) = \frac { 1 } { ( T _ { 2 } - T _ { 1 } ) } \left( \frac { P _ { I } ( t , T _ { 1 } ) } { P _ { I } ( t , T _ { 2 } ) } - 1 \right) .\tag{15}
$$

It can be seen easily that 1) the definition for the inflation forward rates is equivalent to

$$
f ^ { ( I ) } ( t , T _ { 1 } , T _ { 2 } ) = \frac { 1 } { ( T _ { 2 } - T _ { 1 } ) } \left( \frac { P _ { I } ( t , T _ { 0 } , T _ { 1 } ) } { P _ { I } ( t , T _ { 0 } , T _ { 2 } ) } - 1 \right) ,\tag{16}
$$

and 2) at $T _ { 2 }$ , the fixing date, we will have the convergence of the inflation forward rate to the spot inflation rate:

$$
f ^ { ( I ) } ( T _ { 2 } , T _ { 1 } , T _ { 2 } ) = \frac { 1 } { T _ { 2 } - T _ { 1 } } \left( \frac { I ( T _ { 2 } ) } { I ( T _ { 1 } ) } - 1 \right) .\tag{17}
$$

As a result, the payof functions of several major derivatives can now be written in terms of inflation forward rates. Derivatives pricing can be made convenient provided we have a simple and analytical tractable model for the inflation forward rates.

We make a remark that, through straightforward derivations, one will see that the definition of inflation forward rates by (15) is actually the same as one of the definitions, $Y _ { i } ( t )$ , in Mercurio and Moreni (2009). We emphasize here that the inflation forward rate so defined is the unique fair rate seen at the time t for a $T _ { 1 }$ -expiry forward contract on the inflation rate over the future period $[ T _ { 1 } , T _ { 2 } ]$ ]. The justification of the next proposition is given in the appendix.

<!-- page: 13 -->

Proposition 1: The time-t forward price to purchase a real bond with maturity $T _ { 2 }$ at time $T _ { 1 }$ such that $t \leq T _ { 1 } \leq T _ { 2 }$ is

$$
F _ { R } ( t , T _ { 1 } , T _ { 2 } ) \triangleq { \frac { P _ { R } ( t , T _ { 0 } , T _ { 2 } ) } { P _ { R } ( t , T _ { 0 } , T _ { 1 } ) } } .\tag{18}
$$

Based on the above proposition, we can show that the inflation forward rate defined in (15) is the only arbitrage-free rate for forward contracts. Let $f$ be the no-arbitrage strike rate for a $T _ { 2 } .$ -expiry forward contract on the inflation rate over $[ T _ { 1 } , T _ { 2 } ]$ that pays $( T _ { 2 } - T _ { 1 } ) ( f ^ { ( I ) } ( T _ { 2 } , T _ { 1 } , T _ { 2 } ) - f )$ . We will do the following sequence of transactions.

## 1. At time $t ,$

(a) Short the $T _ { 1 }$ -expiry forward contract on $f ^ { ( I ) } ( T _ { 2 } , T _ { 1 } , T _ { 2 } )$ ;

(b) Long a $T _ { 1 }$ -expiry forward contract with strike price $F _ { R } ( t , T _ { 1 } , T _ { 2 } )$ on one unit of the real bond with tenor $T _ { 2 } > T _ { 1 }$ ;

(c) Short the $T _ { \mathrm { 2 ^ { - } m a t u r i t y } }$ Treasury discount bond and long the $T _ { 1 ^ { - } }$ maturity Treasury discount bond with an equal dollar value of $F _ { R } ( t , T _ { 1 } , T _ { 2 } ) P ( t , T _ { 1 } )$

2. At time $T _ { 1 }$ , exercise the $T _ { 1 }$ -expiry forward contract by purchasing the real bond for $F _ { R } ( t , T _ { 1 } , T _ { 2 } )$ dollars, the proceed from the $T _ { 1 }$ -maturity Treasury discount bond.

3. At time $T _ { 2 }$ , close out all positions.

At $T _ { 2 }$ , we end up with the following net value of the sequence of zero-net transactions:

$$
\begin{array} { l } { { P \& L = ( T _ { 2 } - T _ { 1 } ) [ f - f ^ { ( I ) } ( T _ { 2 } , T _ { 1 } , T _ { 2 } ) ] + \displaystyle \frac { I ( T _ { 2 } ) } { I ( T _ { 1 } ) } - \frac { F _ { R } ( t , T _ { 1 } , T _ { 2 } ) P ( t , T _ { 1 } ) } { P ( t , T _ { 2 } ) } } } \\ { { \displaystyle \qquad = ( T _ { 2 } - T _ { 1 } ) [ f - f ^ { ( I ) } ( T _ { 2 } , T _ { 1 } , T _ { 2 } ) ] + \displaystyle \frac { I ( T _ { 2 } ) } { I ( T _ { 1 } ) } - \frac { P _ { I } ( t , T _ { 0 } , T _ { 1 } ) } { P _ { I } ( t , T _ { 0 } , T _ { 2 } ) } } } \\ { { \displaystyle \qquad = ( T _ { 2 } - T _ { 1 } ) [ f - f ^ { ( I ) } ( t , T _ { 1 } , T _ { 2 } ) ] . } } \end{array}
$$

<!-- page: 14 -->

Apparently, arbitrage occurs if $f \neq f ^ { ( I ) } ( t , T _ { 1 } , T _ { 2 } )$

Being a $T _ { 1 } { \mathrm { - f o r w a r d } }$ price of a tradable security, $F ( t , T _ { 1 } , T _ { 2 } )$ should be a lognormal martingale under the $T _ { 1 }$ -forward measure whose volatility is the diference of those of $P _ { R } ( t , T _ { 0 } , T _ { 2 } )$ and $P _ { R } ( t , T _ { 0 } , T _ { 1 } )$ , i.e.,

$$
\frac { d F _ { R } ( t , T _ { 1 } , T _ { 2 } ) } { F _ { R } ( t , T _ { 1 } , T _ { 2 } ) } = \left( \Sigma _ { R } ( t , T _ { 2 } ) - \Sigma _ { R } ( t , T _ { 1 } ) \right) ^ { T } ( d { \bf Z } _ { t } - \Sigma ( t , T _ { 1 } ) d t ) .\tag{19}
$$

Note that, in general, $\mathcal { d } \boldsymbol { Z } _ { t } - \Sigma ( t , T ) \boldsymbol { d t }$ is (the diferential of) a Brownian motion under the so-called T-forward measure, $Q _ { T }$ , which is defined by the Radon-Nikodym derivative

$$
\left. \frac { d Q _ { T } } { d Q } \right| _ { \mathcal { F } _ { t } } = \frac { P ( t , T ) } { B ( t ) P ( 0 , T ) } ,
$$

where $\begin{array} { r } { B ( t ) = e x p ( \int _ { 0 } ^ { t } r _ { s } d s ) } \end{array}$ is the unit price of money market account.

RThere is an important implication by (19). Based on the risk neutral dynamics of $P _ { R } ( t , T _ { 0 } , T )$ , there is also

$$
\frac { d F _ { R } ( t , T _ { 1 } , T _ { 2 } ) } { F _ { R } ( t , T _ { 1 } , T _ { 2 } ) } = \left( \Sigma _ { R } ( t , T _ { 2 } ) - \Sigma _ { R } ( t , T _ { 1 } ) \right) ^ { T } ( d \mathbf { Z } _ { t } - \Sigma _ { R } ( t , T _ { 1 } ) d t ) .\tag{20}
$$

The coexistence of equations (19) and (20) poses a constraint on the volatility functions on the real bonds.

Proposition 2 (Consistency condition): For arbitrage pricing, the volatility functions of the real bonds must satisfy the following condition:

$$
( \Sigma _ { R } ( t , T _ { 2 } ) - \Sigma _ { R } ( t , T _ { 1 } ) ) \cdot ( \Sigma ( t , T _ { 1 } ) - \Sigma _ { R } ( t , T _ { 1 } ) ) = 0 .\tag{21}
$$

Literally, the consistency condition is equivalent to say that

$$
C o v \left( d \left( \frac { P _ { R } ( t , T _ { 0 } , T _ { 2 } ) } { P _ { R } ( t , T _ { 0 } , T _ { 1 } ) } \right) , d \left( \frac { P ( t , T _ { 1 } ) } { P _ { R } ( t , T _ { 0 } , T _ { 1 } ) } \right) \right) = 0 .
$$

While an intuitive interpretation is not available at this point, we can at least show that the consistency condition holds provided that the real forward rate and the inflation rate are uncorrelated, because then there will be

$$
\frac { P ( t , T _ { 1 } ) } { P _ { R } ( t , T _ { 0 } , T _ { 1 } ) } = E _ { t } ^ { Q } \left[ e ^ { - \int _ { t } ^ { T _ { 1 } } i _ { s } d s } \right] ,
$$

<!-- page: 15 -->

while

$$
f _ { R } ( t , T _ { 1 } , T _ { 2 } ) = \frac { 1 } { \Delta T } \left( \frac { P _ { R } ( t , T _ { 0 } , T _ { 1 } ) } { P _ { R } ( t , T _ { 0 } , T _ { 2 } ) } - 1 \right)
$$

is the real forward rate. Let

$$
\Sigma _ { I } ( t , T ) = \Sigma ( t , T ) - \Sigma _ { R } ( t , T )
$$

denote the volatility of $P _ { I } ( t , T _ { 0 } , T )$ . Divide (21) by $( T _ { 2 } - T _ { 1 } )$ and let $T _ { 2 } $ $T _ { 1 } = T$ , we then end up with

$$
\dot { \Sigma } _ { R } ( t , T ) \cdot \Sigma _ { I } ( t , T ) = 0 .\tag{22}
$$

This version of consistency of consistency condition will be use later to derive a Heath-Jarrow-Morton type model with instantaneous inflation rates.

Using (6) and (19), we can derive the dynamics of the inflation forward rate $f ^ { ( I ) } ( t , T _ { 1 } , T _ { 2 } )$ . For generality, we let $T = T _ { 2 } , \Delta T = T _ { 2 } - T _ { 1 }$ , we then can cast (15) into

$$
f ^ { ( I ) } ( t , T - \Delta T , T ) + \frac { 1 } { \Delta T } = \frac { 1 } { \Delta T } \frac { F _ { R } ( t , T - \Delta T , T ) P ( t , T - \Delta T ) } { P ( t , T ) } .
$$

The dynamics of $f ^ { ( I ) } ( t , T - \Delta T , T )$ follows from those of $F _ { R }$ and $P \mathrm { { ^ { * } s } }$ (and thus is left to readers).

Proposition 3. Under the risk neutral measure, the governing equation for the simple inflation forward rate is

$$
\begin{array} { l } { { \displaystyle d \left( f ^ { ( I ) } ( t , T - \Delta T , T ) + \frac { 1 } { \Delta T } \right) } } \\ { { \displaystyle = \left( f ^ { ( I ) } ( t , T - \Delta T , T ) + \frac { 1 } { \Delta T } \right) \left\{ \gamma ^ { ( I ) } ( t , T ) \cdot ( d Z _ { t } - \Sigma ( t , T ) d t ) \right\} , } } \end{array}\tag{23}
$$

where

$$
\gamma ^ { ( I ) } ( t , T ) = \Sigma _ { I } ( t , T - \Delta T ) - \Sigma _ { I } ( t , T )
$$

is the percentage volatility of the displaced inflation forward rate.

The displaced difusion dynamics (23) for the simple inflation rates has at least two desirable features. First, it allows the inflation rates to take both positive and negative values, reflecting the economical environment of either inflation or deflation. There is a lower bound, $- 1 / \Delta T$ , on the inflation rate, which efectively prevents the prices of goods from becoming negative. Second, it is analytical tractable for derivatives pricing. For the purpose of derivatives pricing, we will use (23) in conjunction with a term structure model for nominal interest rates, preferably a model with simple compounding nominal forward rates. As such, the choice for a term structure model with simple nominal forward rates points to the LIBOR market model (Brace et. al, 1997; Jamshidian, 1997; Miltersen and Sandmann, 1997), which is the benchmark model for nominal interest rates and has has a number of desirable features for a term structure model.

<!-- page: 16 -->

We are now ready to propose a comprehensive market model for inflation rates. The state variables consist of two streams of spanning forward rates and inflation forward rates, $f _ { j } ( t ) \ { \stackrel { \triangle } { = } } \ f ( t , T _ { j } , T _ { j + 1 } )$ and $f _ { j } ^ { ( I ) } ( t ) \stackrel { \triangle } { = }$ $f ^ { ( I ) } ( t , T _ { j - 1 } , T _ { j } ) , j = 1 , 2 , . . . , N$ , that follow the following dynamics:

$$
\left\{ \begin{array} { c } { d f _ { j } ( t ) = f _ { j } ( t ) \gamma _ { j } ( t ) \cdot ( d \mathbf { Z } _ { t } - \Sigma _ { j + 1 } ( t ) d t ) , } \\ { d \left( f _ { j } ^ { ( I ) } ( t ) + \displaystyle \frac { 1 } { \Delta T _ { j } } \right) = \left( f _ { j } ^ { ( I ) } ( t ) + \displaystyle \frac { 1 } { \Delta T _ { j } } \right) \gamma _ { j } ^ { ( I ) } ( t ) \cdot ( d \mathbf { Z } _ { t } - \Sigma _ { j } ( t ) d t ) , } \end{array} \right.\tag{24}
$$

where

$$
\Sigma _ { j + 1 } ( t ) = - \sum _ { k = \eta _ { t } } ^ { j } \frac { \Delta T _ { k + 1 } f _ { k } ( t ) } { 1 + \Delta T _ { k + 1 } f _ { k } ( t ) } \gamma _ { k } ( t ) ,
$$

and

$$
\eta _ { t } = \mathrm { m i n } \{ i | T _ { i } > t \} .
$$

As we shall see shortly, with the lognormal processes for nominal and inflation forward rates, the pricing of major inflation derivatives can be made very convenient.

The market model just developed lends itself for further extensions. In its current form, the model cannot accommodate implied volatility smiles or skews. For these ends, we may incorporate additional risk factors like jumps and/or stochastic volatilities into the equations. In section 6, we will make a brief discussion on possible extensions of the market model.

<!-- page: 17 -->

## 3.3 The Extended Heath-Jarrow-Morton Model

Analogously to the introduction to nominal forward rates, we now introduce the instantaneous inflation forward rates, $f ^ { ( I ) } ( t , T )$ , through

$$
f ^ { ( I ) } ( t , T ) = - \frac { \partial \ln P _ { I } ( t , T ) } { \partial T } , \quad \forall T \geq t ,\tag{25}
$$

or

$$
P _ { I } ( t , T ) = e ^ { - \int _ { t } ^ { T } f ^ { ( I ) } ( t , s ) d s } .
$$

According to (12), we can express the instantaneous forward rate as

$$
f ^ { ( I ) } ( t , T ) = - \frac { \partial \ln P _ { I } ( t , T _ { 0 } , T ) } { \partial T } = \frac { \partial \ln \left( \frac { P _ { R } ( t , T _ { 0 } , T ) } { P ( t , T ) } \right) } { \partial T } , \quad \forall T \geq t .
$$

The dynamics of $f ^ { ( I ) } ( t , T )$ , therefore, follows from those of $\textstyle P ( t , T )$ and $P _ { R } ( t , T _ { 0 } , T )$ . By the Ito’s lemma, we have

$$
\begin{array} { l } { \displaystyle - d \ln P _ { I } ( t , T _ { 0 } , T ) = d \ln \left( \frac { P _ { R } ( t , T _ { 0 } , T ) } { P ( t , T ) } \right) } \\ { \displaystyle \qquad = - \frac { 1 } { 2 } \| \Sigma _ { I } ( t , T ) \| ^ { 2 } d t - \Sigma _ { I } ^ { T } ( t , T ) \left( d \mathbf { W } _ { t } - \Sigma ( t , T ) d t \right) . } \end{array}\tag{26}
$$

Diferentiating the above equation with respect to $T$ and making use of the consistency condition (22), we then have

$$
d f ^ { ( I ) } ( t , T ) = - \dot { \Sigma } _ { I } \cdot \left( d { \bf Z } _ { t } - \Sigma ( t , T ) d t \right) ,\tag{27}
$$

where the overhead dots mean partial derivatives with respect to $T _ { \ast }$ the maturity. Equation (27) shows that $f ^ { ( I ) } ( t , T )$ is a martingale and its dynamics is fully specified by the volatilities of the nominal and inflation forward rates. The joint equations of (8) and (27) constitute the so-called extended Heath-Jarrow-Morton framework (or model) for nominal interest rates and inflation rates.

For applications of the model, we will instead first prescribe the volatilities of forward rates and inflation forward rates, defined by

$$
\begin{array} { l } { { \sigma ( t , T ) = - \dot { \Sigma } ( t , T ) , } } \\ { { \sigma ^ { ( I ) } ( t , T ) = - \dot { \Sigma } _ { I } ( t , T ) . } } \end{array}
$$

<!-- page: 18 -->

In terms of $\sigma ( t , T )$ and $\sigma ^ { ( I ) } ( t , T )$ , we can expresses the volatilities of nominal zero-coupon bonds as

$$
\Sigma ( t , T ) = - \int _ { t } ^ { T } \sigma ( t , s ) d s ,
$$

and then cast our extended HJM model in joint equations with the forward rates and inflation forward rates:

$$
\left\{ \begin{array} { l l } { \displaystyle d f ( t , T ) = \sigma ( t , T ) \cdot d \mathbf { Z } _ { t } + \sigma ( t , T ) \cdot \left( \int _ { t } ^ { T } \sigma ( t , s ) d s \right) d t , } \\ { d f ^ { ( I ) } ( t , T ) = \sigma ^ { ( I ) } ( t , T ) \cdot d \mathbf { Z } _ { t } + \sigma ^ { ( I ) } ( t , T ) \cdot \left( \int _ { t } ^ { T } \sigma ( t , s ) d s \right) d t . } \end{array} \right.\tag{28}
$$

The initial term structures of forward rates and inflation forward rates serve as inputs to the these equations.

Let us establish the connection between our model and that of Jarrow and Yildirim (2003) based on “foreign currency analogy”. The instantaneous real forward rate satisfies

$$
f _ { R } ( t , T ) = f ( t , T ) - f ^ { ( I ) } ( t , T ) .
$$

Let

$$
\sigma _ { R } ( t , T ) = - \dot { \Sigma } _ { R } ( t , T ) = \sigma ( t , T ) - \sigma ^ { ( I ) } ( t , T ) .
$$

Then

$$
\Sigma _ { R } ( t , T ) = - \int _ { t } ^ { T } \sigma _ { R } ( t , s ) d s + \sigma _ { I } ( t ) ,
$$

where $\sigma _ { I } ( t )$ is the volatility of the CPI index I(t). Subtracting the two equations of (28) and applying the consistency condition, (22), we will arrive at

$$
d f _ { R } ( t , T ) = \sigma _ { R } ( t , T ) \cdot d { \bf Z } _ { t } + \sigma _ { R } ( t , T ) \cdot \left( \int _ { t } ^ { T } \sigma _ { R } ( t , s ) d s - \sigma _ { I } ( t ) \right) d t ,\tag{29}
$$

which is identical to the dynamics the real forward rate established by Jarrow and Yildirim (2003) (page 342, equation (12))! Hence, our model is consistent with the model of Jarrow and Yildirim, established using “foreign currency analogy”, a very diferent approach. With the above results, we claim that our model and the model of Jarrow and Yildirim are two variants of the same model for inflation-rate derivatives.

<!-- page: 19 -->

We are, however, reluctant to accept “foreign currency analogy” for the reason that we actually have $\sigma _ { I } ( t ) = 0$ . The dynamics of the CPI index follows from the definition of of the CPI index, (3), and the Fisher’s equation:

$$
d I ( t ) = i ( t ) I ( t ) d t = ( r _ { t } - R _ { t } ) I ( t ) d t ,\tag{30}
$$

and this simple fact has long been overlooked in the literature on inflationrate modeling. The implication is that CPI index cannot be treated as an exchange rate between the nominal and real (or virtue) economies, unless it is completely determined by the interest rates of the two economies as in (30).

## 3.4 Pricing of YYIIS

The price of a YYIIS is the diference in value of the fixed leg and floating leg. While the fixed leg is priced as an annuity, the floating leg is priced by discounting the expectation of each piece of payment as

$$
\begin{array} { l } { { V _ { f l o a t } ^ { ( j ) } ( t ) = N o t . P ( t , T _ { j } ) E _ { t } ^ { Q _ { T _ { j } } } \left[ \left( \frac { I ( T _ { j } ) } { I ( T _ { j - 1 } ) } - 1 \right) \right] } } \\ { { \mathrm { ~ } = N o t . \Delta T _ { j } P ( t , T _ { j } ) E _ { t } ^ { Q _ { T _ { j } } } \left[ f _ { j } ^ { ( I ) } ( T _ { j } ) \right] } } \\ { { \mathrm { ~ } = N o t . \Delta T _ { j } P ( t , T _ { j } ) f _ { j } ^ { ( I ) } ( t ) , } } \end{array}
$$

followed by a summation:

$$
V _ { f l o a t } ( t ) = N o t . \sum _ { j = 1 } ^ { n _ { f } } \Delta T _ { j } P ( t , T _ { j } ) f _ { j } ^ { ( I ) } ( t ) .
$$

We result we have here difers greatly from the current practice of the market, where the pricing of YYIIS makes no use of the inflation forward rates implied by ZCIIS. In existing literatures, the pricing of YYIIS based on ZCIIS goes through a procedure of “convexity adjustment”, which is model dependent. With our result, we realize that YYIIS can and should be priced consistently with XCIIS, otherwise arbitrage opportunities will occur.

<!-- page: 20 -->

## 3.5 Pricing of Inflation Caplets

In view of the displaced difusion processes for simple inflation forward rates, we can price a caplet with \$1 notional value straightforwardly as follows:

$$
\begin{array} { l } { { \displaystyle \Delta T _ { j } E _ { t } ^ { Q } \left[ e ^ { - \int _ { t } ^ { T _ { j } } r _ { s } d s } ( f _ { j } ^ { ( I ) } ( T _ { j } ) - K ) ^ { + } \right] } } \\ { { \displaystyle = \Delta T _ { j } P ( t , T _ { j } ) E _ { t } ^ { Q _ { T _ { j } } } \left[ \left( \left( f _ { j } ^ { ( I ) } ( T _ { j } ) + \frac 1 { \Delta T _ { j } } \right) - \left( K + \frac 1 { \Delta T _ { j } } \right) \right) ^ { + } \right] } } \\ { { \displaystyle = \Delta T _ { j } P ( t , T _ { j } ) \{ \mu _ { j } \Phi ( d _ { 1 } ^ { ( j ) } ( t ) ) - \tilde { K } _ { j } \Phi ( d _ { 2 } ^ { ( j ) } ( t ) ) \} \} , } } \end{array}\tag{31}
$$

where $\Phi ( \cdot )$ is the standard normal accumulative distribution function, and

$$
\begin{array} { r l } & { \mu _ { j } = f _ { j } ^ { ( I ) } + 1 / \Delta T _ { j } , \quad \tilde { K } _ { j } = K + 1 / \Delta T _ { j } , } \\ & { d _ { 1 } ^ { ( j ) } ( t ) = \frac { \ln \mu _ { j } / \tilde { K } _ { j } + \frac { 1 } { 2 } \sigma _ { j } ^ { 2 } ( t ) ( T _ { j } - t ) } { \sigma _ { j } ( t ) \sqrt { T _ { j } - t } } , } \\ & { d _ { 2 } ^ { ( j ) } ( t ) = d _ { 1 } ^ { ( j ) } ( t ) - \sigma _ { j } ( t ) \sqrt { T _ { j } - t } , } \end{array}
$$

with $\sigma _ { j }$ to be the volatility of ln $\begin{array} { r } { ( f _ { j } ^ { ( I ) } ( t ) + \frac { 1 } { \Delta T _ { j } } ) } \end{array}$

$$
\sigma _ { j } ^ { 2 } ( t ) = \frac { 1 } { T _ { j } - t } \int _ { t } ^ { T _ { j } } \| \gamma _ { j } ^ { ( I ) } ( s ) \| ^ { 2 } d s .\tag{32}
$$

The inflation-indexed cap with maturity $T _ { N }$ and strike K is the sum of a series of inflation-indexed caplets with the cash flows at $T _ { j }$ for $j = 1 , \cdots , N$ We denote by $\mathrm { I I C a p } ( t ; N , K )$ the price of the inflation-indexed cap at time t, where $T _ { 0 } < t \le T _ { 1 }$ , with cash flow dates $T _ { j } , j = 1 , \ldots , N$ , and strike K. Based on (31), we have

$$
\begin{array} { l } { { \mathrm { I I C a p } ( t ; N , K ) } } \\ { { \displaystyle = \sum _ { j = 1 } ^ { N } \Delta T _ { j } P ( t , T _ { j } ) \{ \mu _ { j } \Phi ( d _ { 1 } ^ { ( j ) } ( t ) ) - \tilde { K } _ { j } \Phi ( d _ { 2 } ^ { ( j ) } ( t ) ) \} . } } \end{array}\tag{33}
$$

Given inflation caps of various maturities, we can consecutively bootstrap $\sigma _ { j } ( t )$ , the “implied caplet volatilities”, in either a parametric or a non-parametric way. With additional information on correlations between inflation rates of various maturities, we can determine $\gamma _ { j } ^ { ( I ) }$ , the volatility of inflation rates and thus fully specify the displace-difusion dynamics for inflation forward rates. We may also include inflation swaption prices to the input set to specify $\gamma _ { j } ^ { ( I ) } \mathrm { { ^ { * } s } }$

<!-- page: 21 -->

## 4 Pricing of Inflation-Indexed Swaptions

The Year-on-Year Inflation-Indexed Swaption (YYIISO) is an option to enter into a YYIIS at the option’s maturity. Base on our market model (24), we will show that a forward inflation swap rate with a displacement is a martingale under a usual nominal forward swap measure. Instead of assuming lognormality for the inflation swap rate as in Hinnerich (2008), we justify that the displaced inflation swap rate is a Gaussian martingale and for which we produce a lognormal dynamics by “freezing coeficients”. The closed-form pricing of the swaptions then follows.

Next, let us derive the expression for inflation swap rate. Without loss of generality, we assume the same cash flow frequency for both fixed and floating legs. The value of a payer’s YYIIS over the period $[ T _ { m } , T _ { n } ]$ at time $t \leq T _ { m }$ for a swap rate K is given by

$$
\begin{array} { l } { { \displaystyle Y _ { m , n } ( t , K ) = \sum _ { i = m + 1 } ^ { n } \Delta T _ { i } P ( t , T _ { i } ) E _ { t } ^ { Q _ { T _ { i } } } \left[ \frac { 1 } { \Delta T _ { i } } \left( \frac { I ( T _ { i } ) } { I ( T _ { i - 1 } ) } - 1 \right) - K \right] } } \\ { ~ = \displaystyle \sum _ { i = m + 1 } ^ { n } \Delta T _ { i } P ( t , T _ { i } ) E _ { t } ^ { Q _ { T _ { i } } } \left[ f _ { i } ^ { ( I ) } ( T _ { i } ) - K \right] }  \\ { { \displaystyle ~ = \sum _ { i = m + 1 } ^ { n } \Delta T _ { i } P ( t , T _ { i } ) \left[ f _ { i } ^ { ( I ) } ( t ) - K \right] } . } \end{array}\tag{34}
$$

The forward swap rate at t, denoted by $S _ { m , n } ( t )$ , is defined as the value of K which makes the value of the swap, $Y _ { m , n } ( t , K )$ , equal to 0. So,

$$
S _ { m , n } ( t ) ~ = ~ \frac { \sum _ { i = m + 1 } ^ { n } \Delta T _ { i } P ( t , T _ { i } ) f _ { i } ^ { ( I ) } ( t ) } { \sum _ { i = m + 1 } ^ { n } \Delta T _ { i } P ( t , T _ { i } ) } ,\tag{35}
$$

or, more preferably,

$$
\begin{array} { r l r } {  { S _ { m , n } ( t ) + \frac { 1 } { \Delta T _ { m , n } } } } \\ & { } & { \quad = \frac { \sum _ { i = m + 1 } ^ { n } \Delta T _ { i } P ( t , T _ { i } ) [ f _ { i } ^ { ( I ) } ( t ) + \frac { 1 } { \Delta T _ { i } } ] } { \sum _ { i = m + 1 } ^ { n } \Delta T _ { i } P ( t , T _ { i } ) } } \\ & { } & { \quad = \sum _ { i = m + 1 } ^ { n } \omega _ { i } ( t ) \mu _ { i } ( t ) , } \end{array}\tag{36}
$$

<!-- page: 22 -->

where

$$
\omega _ { i } ( t ) = \frac { \Delta T _ { i } P ( t , T _ { i } ) } { A _ { m , n } ( t ) } \quad \mathrm { ~ a n d ~ } \quad A _ { m , n } ( t ) = \sum _ { i = m + 1 } ^ { n } \Delta T _ { i } P ( t , T _ { i } ) ,
$$

and

$$
\frac { 1 } { \Delta T _ { m , n } } = \sum _ { i = m + 1 } ^ { n } \omega _ { i } ( t ) \frac { 1 } { \Delta T _ { i } } .
$$

We have the following results on the dynamics of the swap rate.

Proposition 5. The displaced forward swap rate $\begin{array} { r } { S _ { m , n } ( t ) + \frac { 1 } { \Delta T _ { m , n } } } \end{array}$ is a martingale under the measure $Q _ { m , n }$ corresponding to the numeraire $A _ { m , n } ( t )$ Moreover,

$$
\begin{array} { l } { \displaystyle \ d { \ d } d \left( S _ { m , n } ( t ) + \frac { 1 } { \Delta T _ { m , n } } \right) = \left( S _ { m , n } ( t ) + \frac { 1 } { \Delta T _ { m , n } } \right) } \\ { \displaystyle \times \sum _ { i = m + 1 } ^ { n } \left[ \alpha _ { i } ( t ) \gamma _ { i } ^ { ( I ) } ( t ) + ( \alpha _ { i } ( t ) - w _ { i } ( t ) ) \Sigma _ { i } ( t ) \right] \cdot d \mathbf { Z } _ { t } ^ { ( m , n ) } , } \end{array}\tag{37}
$$

where $d Z _ { t } ^ { ( m , n ) }$ is a $Q _ { m , n }$ -Brownian motion, and

$$
\alpha _ { i } ( t ) = \frac { \omega _ { i } ( t ) \mu _ { i } ( t ) } { \sum _ { j = m + 1 } ^ { n } \omega _ { j } ( t ) \mu _ { j } ( t ) } . \quad \varTheta
$$

The martingale property is easy to see because it is the relative value between its floating leg and an annuity, both are tradable. The proof of (37) is supplemented in the appendix.

By freezing coeficients of appropriately, we can turn (37) into a lognormal process. We proceed as follows. Conditional on $\mathcal { F } _ { t }$ , we cast (37) for $s \geq t$ into

$$
d \left( S _ { m , n } ( s ) + \frac { 1 } { \Delta T _ { m , n } } \right) = \left( S _ { m , n } ( s ) + \frac { 1 } { \Delta T _ { m , n } } \right) \gamma _ { m , n } ^ { ( I ) } ( s ) \cdot d Z _ { s } ^ { ( m , n ) } ,\tag{38}
$$

where

$$
\gamma _ { m , n } ^ { ( I ) } ( s ) = \sum _ { i = m + 1 } ^ { n } \left[ \alpha _ { i } ( t ) \gamma _ { i } ^ { ( I ) } ( s ) + ( \alpha _ { i } ( t ) - w _ { i } ( t ) ) \Sigma _ { i } ( s ) \right] ,
$$

$$
\Sigma _ { j } ( s ) = - \sum _ { k = \eta _ { t } } ^ { j } \frac { \Delta T _ { k + 1 } f _ { k } ( t ) } { 1 + \Delta T _ { k + 1 } f _ { k } ( t ) } \gamma _ { k } ( s ) .
$$

<!-- page: 23 -->

As a result of freezing coeficients selectively, the volatility function $\gamma _ { m , n } ^ { ( I ) } ( s )$ is now deterministic, which paves the way for closed-form pricing of swaptions.

Now we are ready to price swaptions. Consider a $T _ { m } \mathrm { { - e x p i r y } }$ YYIISO with underlying YYIIS over the period $[ T _ { m } , T _ { n } ]$ and strike $K$ , its value, denoted the price by $\mathrm { Y Y I I S O } ( t , T _ { m } , T _ { n } , K )$ at time $t \leq T _ { m }$ , then,

$$
\begin{array} { r l } & { \quad \mathrm { Y Y I I S O } ( t , T _ { m } , T _ { n } ) } \\ & { = E _ { t } ^ { Q } [ e ^ { - \int _ { t } ^ { T _ { m } } r _ { s } d s } A _ { m , n } ( T _ { m } ) ( S _ { m , n } ( T _ { m } ) - K ) ^ { + } ] } \\ & { = A _ { m , n } ( t ) E _ { t } ^ { Q _ { m , n } } [ ( S _ { m , n } ( T _ { m } ) - K ) ^ { + } ] } \\ & { = A _ { m , n } ( t ) E _ { t } ^ { Q _ { m , n } } \left[ \left[ \left( S _ { m , n } ( T _ { m } ) + \frac { 1 } { \Delta T _ { m , n } } \right) - \left( K + \frac { 1 } { \Delta T _ { m , n } } \right) \right] ^ { + } \right] } \\ & { = A _ { m , n } ( t ) \left[ \left( S _ { m , n } ( t ) + \frac { 1 } { \Delta T _ { m , n } } \right) \Phi ( d _ { 1 } ^ { ( m , n ) } ) - \tilde { K } _ { m , n } \Phi ( d _ { 2 } ^ { ( m , n ) } ) \right] , } \end{array}\tag{39}
$$

where

$$
\begin{array} { r l } & { \quad \tilde { K } _ { m , n } = K + \cfrac { 1 } { \Delta T _ { m , n } } , } \\ & { \quad d _ { 1 } ^ { ( m , n ) } = \cfrac { \ln { \left( S _ { m , n } ( t ) + 1 / \Delta T _ { m , n } \right) / \tilde { K } _ { m , n } + \frac { 1 } { 2 } \sigma _ { m , n } ^ { 2 } ( t ) \left( T _ { m } - t \right) } } { \sigma _ { m , n } ( t ) \sqrt { T _ { m } - t } } , } \\ & { \quad d _ { 2 } ^ { ( m , n ) } = d _ { 1 } ^ { ( m , n ) } - \sigma _ { m , n } ( t ) \sqrt { T _ { m } - t } , } \\ & { \quad \sigma _ { m , n } ( t ) = \cfrac { 1 } { T _ { m } - t } \int _ { t } ^ { T _ { m } } \| \gamma _ { m , n } ^ { ( I ) } ( s ) \| ^ { 2 } d s . } \end{array}
$$

In (39), we freeze $\omega _ { i } ( s )$ at $s = t$ for evaluating $\frac { 1 } { \Delta T _ { m , n } }$ . Because $\alpha _ { j } \mathrm { ^ { * } s }$ are in terms of $\mu _ { j } ( t ) \mathrm { { ^ { * } s } }$ , we must have already obtained $\mu _ { j } ( t ) \mathrm { { ^ { * } s } }$ before applying the pricing formula.

Treatments of freezing coeficients similar to what we did to (37) are popular in the industry, and they are often very accurate in many applications. A rigorous analysis on the error estimation of such approximations, however, is still pending. For some insights about the magnitude of errors, we refer to Brigo et al. (2004).

Finally in this section we emphasize that the price formula (39) implies a hedging strategy for the swaption. At ant time t, the hedger should long $\Phi ( d _ { 1 } ^ { ( m , n ) } )$ units of the underlying inflation swap for hedging. Proceeds from buying or selling the swap may go in or go out of a money market account.

<!-- page: 24 -->

## 5 Calibration of the Market Model

A comprehensive calibration of the inflation-rate model (24) means simultaneous determination of volatility vectors for nominal and inflation forward rates, based on inputs of term structures and prices of benchmark derivatives. This task, luckily, can be achieved by divide-and-conquer: the LIBOR model for nominal interest rates can be calibrated in advance using only the LIBOR data, then the market model for inflation rates can be calibrated separately in a similar way, making use of the data of inflation derivatives.

Before calibration, we need to build the spot term structure of inflation rates, using (15). For a comprehensive calibration of the market model for inflation rates, we may need to match the market prices of a set inflation caps/floors and inflation-rate swpations. That is, the input set consists of

$$
\{ \sigma _ { j } \} \quad \mathrm { a n d } \quad \{ \sigma _ { m , n } \} .
$$

In addition, we may need to input the correlations amongst inflations rates and between inflation rates and interest rates. Mathematically, a comprehensive calibration amounts to solving the following joint equations

$$
\begin{array} { l } { \displaystyle \sigma _ { j } ^ { 2 } ( T _ { j } - t ) = \int _ { t } ^ { T _ { j } } \| \gamma _ { j } ^ { ( I ) } ( s ) \| ^ { 2 } d s , } \\ { \displaystyle \sigma _ { m , n } ^ { 2 } ( T _ { m } - t ) = \int _ { t } ^ { T _ { m } } \left\| \sum _ { i = m + 1 } ^ { n } \left[ \alpha _ { i } ( t ) \gamma _ { i } ^ { ( I ) } ( s ) + ( \alpha _ { i } ( t ) - w _ { i } ( t ) ) \Sigma _ { i } ( s ) \right] \right\| ^ { 2 } d s , } \end{array}\tag{40}
$$

for some index $k , j$ , and pairs of indexes m and n in the input set.

We can take either a parametric or a non-parametric approach for calibration. In the non-parametric approach, the volatilities of inflation rates, $\gamma _ { j } ^ { ( I ) } ( t )$ , are assumed piece-wise functions of t. The number of unknowns is usually big and thus equations (40) will often be under-determined and thus ill-posed. Regularization is usually needed in order to achieve uniqueness and smoothness of solution. An eficient technique is to impose a quadratic objective function for both uniqueness and smoothness (Wu, 2003). When both objective function and constraints, listed in (40), are quadratic functions, the constrained optimization problem can be solved with a Hessian-based descending search algorithm, where each step of iterations only requires solving a symmetric eigenvalue problem, and is thus very eficient. For the details of such a methodology, we refer to Wu (2003).

<!-- page: 25 -->

For demonstrations, we consider calibrating a two-factor model where the inflation rates are driven by one factor while the nominal rates are driven by another factor. Let $\rho$ be the correlation between the nominal rate and inflation rate, then (40) becomes,

$$
\begin{array} { r l } & { \sigma _ { j } ^ { 2 } ( T _ { j } - t ) = \displaystyle \int _ { t } ^ { T _ { j } } | \gamma _ { j } ^ { ( I ) } ( s ) | ^ { 2 } d s , } \\ & { \sigma _ { m , n } ^ { 2 } ( T _ { m } - t ) = \displaystyle \int _ { t } ^ { T _ { m } } \sum _ { i , j = m + 1 } ^ { n } \Big [ \alpha _ { i } ( t ) \alpha _ { j } ( t ) \gamma _ { i } ^ { ( I ) } ( s ) \gamma _ { j } ^ { ( I ) } ( s ) } \\ & { \qquad + 2 \alpha _ { i } ( t ) ( \alpha _ { j } ( t ) - w _ { j } ( t ) ) \gamma _ { i } ^ { ( I ) } ( s ) \Sigma _ { j } ( s ) \rho } \\ & { \qquad + ( \alpha _ { i } ( t ) - w _ { i } ( t ) ) ( \alpha _ { j } ( t ) - w _ { j } ( t ) ) \Sigma _ { i } ( s ) \Sigma _ { j } ( s ) \big ] d s , } \end{array}\tag{41}
$$

where $\gamma ^ { ( I ) } ( s )$ are scalar functions, and $\Sigma _ { i } ( s )$ is a known function such that

$$
\Sigma _ { i } ( s ) = - \sum _ { l = \eta _ { t } } ^ { i } \frac { \Delta T _ { l + 1 } f _ { l } ( t ) } { 1 + \Delta T _ { l + 1 } f _ { l } ( t ) } \gamma _ { l } ( s ) .
$$

If we take the approach of non-parametric calibration by assuming piecewise constant function for $\gamma _ { j } ^ { ( I ) }$ , we then have a set of linear or quadratic functions to solve. By adding a quadratic objective function, say,

$$
O ( \{ \gamma _ { j } ^ { ( I ) } \} ) = \alpha \sum ( \gamma _ { j } ^ { ( I ) } - \gamma _ { j - 1 } ^ { ( I ) } ) ^ { 2 } ,
$$

we make the problem well-posed and easy to solve numerically. Here $\alpha > 0$ is a weight parameter.

We can also back out the implied correlation. To do so, we may assume piece-wise correlation, $\rho ( t ) ~ = ~ \rho _ { i }$ for $T _ { i - 1 } \ \leq \ t \ < \ T _ { i }$ , and use instead the following objective function:

$$
{ \cal O } ( \{ \gamma _ { j } ^ { ( I ) } \} ) = \alpha \sum ( \gamma _ { j } ^ { ( I ) } - \gamma _ { j - 1 } ^ { ( I ) } ) ^ { 2 } + \beta \sum ( \rho _ { i } - \rho _ { i - 1 } ) ^ { 2 } , \quad \alpha > 0 , \beta > 0 .\tag{42}
$$

In addition, we need to impose $- 1 \le \rho _ { i } \le 1$ . Given that both the objective function (42) and constraints (41) are quadratic functions, the method developed by Wu (2003) should work well.

As an example, we calibrate the two-factor market model to price data of Euro ZCIIS and inflation caps as of April 7, $2 0 0 8 ^ { 5 }$ , tabulated in Table 1 and 2, respectively. The payment frequency for both types of instruments is annual $( \mathrm { i . e . } ~ \Delta T _ { j } = \Delta T = 1 )$ , and the cap prices are given in basis points (bps). The input correlation between the nominal and the inflation rates is estimated using data of the last three years, from January 2005 to February 2008, and the numbers is $\rho = - 5 . 3 5 \%$ . For simplicity we have taken a flat volatility for all nominal forward rates, at the level of 15%. The calibration also makes use of the LIBOR data, including LIBOR rates, swap rates and prices of at-the-money (ATM) caps, which are not included in the paper for brevity<sup>6</sup>.

<sup>5</sup>We do not have the data of YYIIS or swaptions.

<!-- page: 26 -->

[Table source crop](assets/tables/2013-wu-inflation-rate-derivatives-p0026-block-0002-8277b02a259c3ec4.jpg)
Table 1. Swap rates for ZCIIS for 2008/4/7

[Table source crop](assets/tables/2013-wu-inflation-rate-derivatives-p0026-block-0003-65d315af239903aa.jpg)
Table 2. Prices (in bps) of inflation caps in 2008/4/7

<!-- page: 27 -->

We first construct the term structure of inflation rates, using nominal and inflation discount factors. The term structure is displayed in Figure 2, together with the term structure of nominal forward rates. One can see that the magnitude of the inflation forward rates is consistent with that of ZCIIS rates, and the two curves show a low degree of negative correlation.

![Figure 2 Term structure of the nominal forward rates and inflation forward rates.](assets/figures/2013-wu-inflation-rate-derivatives-p0027-block-0002-1540546825cd4550.jpg)

We then proceed to backing out the implied volatilities of the displaced inflation forward rates, $\sigma _ { j } \mathrm { ^ { * } s } ,$ and set $\gamma _ { j } ^ { ( I ) } ( t ) = \sigma _ { j } , \forall t \leq T _ { j }$ . The procedure consists of two steps. First we need to bootstrap the caplet prices, then we solve for $\sigma _ { j }$ ’s through a root-finding procedure using formulae (31) and (32). Note that in its current form the market cannot price volatility smiles or skews<sup>7</sup>, so we have only tried to calibrate to caps for strike $K = 2 \%$ . The results are displayed in Figure 3. One can see that the local volatility varies around 0.5%, which is the magnitude of implied volatilities often observed in the market.

<sup>7</sup>To calibrate to more strikes we will need a smile model.

<!-- page: 28 -->

![Figure 3 Calibrated local volatility surface, $\gamma _ { i } ^ { ( I ) } ( t )$](assets/figures/2013-wu-inflation-rate-derivatives-p0028-block-0001-a860dd4ad415f07b.jpg)

Next, we price inflation swaptions using the calibrated model. The spot swap-rate curve is displayed in Figure 4, which is also slightly upward sloping.

![Figure 4 Term structure of the inflation swap rates.](assets/figures/2013-wu-inflation-rate-derivatives-p0028-block-0003-8aa20c26e7942ae7.jpg)

For various maturities, tenors and strikes, we calculate prices of inflation swaption by (39). The results are presented in dollar prices in Figure $5 \textrm { -- } 8 .$ One can see that the prices vary in a reasonable and robust way according to maturities, tenors and strikes.

<!-- page: 29 -->

![Figure 5 Price surface of swaptions for $K = 1 \%$](assets/figures/2013-wu-inflation-rate-derivatives-p0029-block-0002-b8ef18037223f444.jpg)

![Figure 6 Price surface of swaptions for $K = 2 \%$](assets/figures/2013-wu-inflation-rate-derivatives-p0029-block-0003-c758b1bfd4fa3a32.jpg)

<!-- page: 30 -->

![Figure 7 Price surface of swaptions for $K = 3 \%$](assets/figures/2013-wu-inflation-rate-derivatives-p0030-block-0001-2bba43da657ad2dc.jpg)

![Figure 8 Price surface of swaptions for $K = 4 \%$](assets/figures/2013-wu-inflation-rate-derivatives-p0030-block-0002-bdc4fc09ffafe8ab.jpg)

<!-- page: 31 -->

## 6 Smile Modeling Based on the Market Model

It is well known that inflation caps and floors demonstrate so-called the implied volatility smiles. Having developed the market models, we can proceed to cope with volatility smiles in ways similar to smile modeling for interestrate derivatives based on LIBOR market model, which, routinely, involve with adopting additional risk factors like stochastic volatilities or jumps, or taking level-dependent volatilities. For example, we may adopt the SABR dynamics for the expected displaced inflation forward rates, $\mu _ { i } ( t )$ , and develop the following model:

$$
\left\{ \begin{array} { l l } { d \mu _ { j } ( t ) = \mu _ { j } ^ { \beta _ { j } } ( t ) \alpha _ { j } ( t ) d Z _ { t } ^ { j } , } \\ { d \alpha _ { j } ( t ) = \nu _ { j } \alpha _ { j } ( t ) d W _ { t } ^ { j } , } \end{array} \right.\tag{43}
$$

where $\beta _ { j }$ and $\nu _ { j }$ are constants, both $Z _ { t } ^ { j }$ and $W _ { t } ^ { j }$ are one-dimensional Brownian motions under the $T _ { j }$ -forward measure, which can be correlated,

$$
d Z _ { t } ^ { j } d W _ { t } ^ { j } = \rho _ { j } d t .
$$

Mecurio and Mereni (2009) proposed and studied the above model with $\beta _ { j } =$ 1, and demonstrate a very quality fitting of implied volatility smiles with the model.

We can also consider other extensions of the market model for smile modeling yet, given the rich literature on smile modeling of interest-rate derivatives, the extensions may become some sort of routine exercises. We refer readers to Brigo and Mercurio (2006) and for an introduction of major smile models for interest-rate derivatives based on the LIBOR market model. Of course, empirical study with various smile models for inflation rates should be an interesting as well as challenging issue.

## 7 Conclusion

Using prices of real zero-coupon bonds as model primitives that are tradable through ZCIIS, we define the term structure of inflation rates, and then construct a market model as well as a HJM type model for the term structure of inflation rates. We show that the HJM type model with inflation forward rates is consistent with the HJM model with real forward rates developed through “foreign currency analogy”. The market can be used to price inflation caplets/floorlets and swaptions in closed form, and can be calibrated eficiently. Finally, the current model serves as a platform for further extensions using risk dynamics in addition to difusions.

<!-- page: 32 -->

## References

[1] Barone, E., and Castagna, A. (1997). The information content of TIPS. Internal Report. SanPaolo IMI, Turin and Banca IMI, Milan. [2] Belgrade, N., and Benhamou, E. (2004). Reconciling Year on Year and Zero Coupon Inflation Swap: A Market Model Approach. Preprint, CDC Ixis Capital Markets. Downloadable at: http://papers.ssrn.com/sol3/papers.cfm?abstract-id=583641. [3] Belgrade, N., Benhamou, E., and Koehler, E. (2004). A Market Model for Inflation. Preprint, CDC Ixis Capital Markets. Downloadable at: http://papers.ssrn.com/sol3/papers.cfm?abstract-id=576081. [4] Brace, A., Gatarek, D., and Musiela, M. (1997). The Market model of interest rate dynamics. Mathematical Finance, 7(2), 127-155. [5] Brigo, D., Liinev, J., Mercurio, F., and Rapisarda, F. (2004). On the distributional distance between the lognormal LIBOR and Swap market models. Working paper, Banca IMI, Italy. [6] Brigo, D., and Mercurio, F. (2006). Interest rate models : theory and practice : with smile, inflation and credit, 2nd edition. Springer Finance, Berlin. [7] Cairns, A.J.G. (2000). A multifactor model for the term structure and inflation for long-term risk management with an extension to the equities market. Preprint. Heriot-Watt University, Edinburgh. [8] Chen, R.-R., Liu, B., and Cheng, X. (2006). Pricing the Term Structure of Inflation Risk Premia: Theory and Evidence from TIPS. Working paper, Rutgers Business School. [9] Cox, J., Ingersoll, J., and Ross, S. A. (1985). A Theory of the Term Structure of Interest Rates. Econometrica, 53(2), 385-408.

<!-- page: 33 -->

[10] Fisher, I. (1930). The Theory of interest. The Macmillan Company. ISBN13 978-0879918644. [11] Heath, D., Jarrow, R., and Morton, A. (1992). Bond pricing and the term structure of Interest rates: A new methodology for contingent claims valuation. Econometrica, 60, 77-105. [12] Harrison, J.M., and Krep, S. (1979). Martingales and arbitrage in multiperiod securities markets. Journal of Economic Theory, 20, 381-408. [13] Harrison, J.M., and Pliska, S. (1981). Martingales and stochastic integrals in the theory of continuous trading. Stoch. Proc. and Their Appl., 11, 215-260. [14] Hinnerich, M. (2008). Inflation indexed swaps and swaptions. Journal of banking and Finance, forthcoming. [15] Hughston, L.P. (1998). Inflation Derivatives. Working paper. Merrill Lynch. [16] Jamshidian, F. (1997). LIBOR and swap market models and measures. Finance and Stochastic, 1, 293-330. [17] Jarrow, R., and Yildirim, Y. (2003). Pricing treasury inflation protected securities and related derivatives using an HJM model. Journal of Financial and Quantitative Analysis, 38(2), 409-430. [18] Jung J. (2008). Real Growth. RISK, February. [19] Kazziha, S. (1999). Interest Rate Models, Inflation-based Derivatives, Trigger Notes And Cross-Currency Swaptions. PhD Thesis, Imperial College of Science, Technology and Medicine. London. [20] Manning, S., and Jones, M. (2003). Modeling inflation derivatives - a review. The Royal Bank of Scotland Guide to Inflation-Linked Products. Risk. [21] Mercurio, F. (2005). Pricing inflation-indexed derivatives. Quantitative Finance, 5(3), 289-302. [22] Mercurio, F., and Moreni, N. (2006). Inflation with a smile. Risk March, Vol. 19(3), 70-75.

<!-- page: 34 -->

[23] Mercurio, F., and Moreni, N. (2009). Inflation modelling with SABR dynamics. Risk June, 106-111. [24] Miltersen, K., Sandmann, K., and Sondermann, D. (1997). Closed-form solutions for term structure derivatives with lognormal interest rates. Journal of Finance, 409-430. [25] van Bezooyen, J.T.S., Exley, C.J., and Smith, A.D. (1997) A market-based approach to valuing LPI liabilities. Downloadable at: http://www.gemstudy.com/DefinedBenefitPensionsDownloads. [26] Wu, L. (2003). Fast at-the-money calibration of LIBOR market model through Lagrange multipliers. J. of Comput. Fin. 6(2), 39-77.

## A Proofs of Propositions

Proof of Proposition 1 :

Do the following zero-net transactions.

1. At time t,

(a) Long the forward contract to buy $\frac { I ( T _ { 1 } ) } { I ( T _ { 0 } ) }$ dollar worth of $T _ { 2 } \cdot$ -maturity real bond deliverable at $T _ { 1 }$ at the unit price $F _ { R } ( t , T _ { 1 } , T _ { 2 } )$ (i.e., to buy $\frac { I ( T _ { 1 } ) } { I ( T _ { 0 } ) F _ { R } ( t , T _ { 1 } , T _ { 2 } ) }$ units);

(b) long one unit of $T _ { 1 }$ -maturity real bond at the price of $P _ { R } ( t , T _ { 0 } , T _ { 1 } )$

(c) short $\frac { P _ { R } ( t , T _ { 0 } , T _ { 1 } ) } { P _ { R } ( t , T _ { 0 } , T _ { 2 } ) }$ unit(s) of $T _ { 2 }$ -maturity real bond at the price of $P _ { R } ( t , T _ { 0 } , T _ { 2 } )$

2. At time $T _ { 1 }$ , exercise the forward contract to buy the $T _ { 2 }$ -maturity real bond (that pays $I ( T _ { 2 } ) / I ( T _ { 1 } ) )$ at the price $F _ { R } ( t , T _ { 1 } , T _ { 2 } )$ , applying all proceed from the $T _ { 1 }$ -maturity real bond.

3. At Time $T _ { 2 } ,$ settle all transactions.

The profit or loss from the transactions is

$$
\mathit { P } \& \mathit { L } = \left( \frac { 1 } { F _ { R } ( t , T _ { 1 } , T _ { 2 } ) } - \frac { P _ { R } ( t , T _ { 0 } , T _ { 1 } ) } { P _ { R } ( t , T _ { 0 } , T _ { 2 } ) } \right) \frac { I ( T _ { 2 } ) } { I ( T _ { 0 } ) } .\tag{44}
$$

<!-- page: 35 -->

For the absense of arbitrage, the forward price must be equal to (18) 

Proof of Proposition $\it 5$

According to (36),

$$
S _ { m , n } ( t ) + \frac { 1 } { \Delta T _ { m , n } } = \sum _ { i = m + 1 } ^ { n } \omega _ { i } ( t ) \mu _ { i } ( t ) ,\tag{45}
$$

so the dynamics of the displaced swap rate will arise from, by Ito’s lemma,

$$
d \left( S _ { m , n } ( t ) + \frac { 1 } { \Delta T _ { m , n } } \right) = \sum _ { i = m + 1 } ^ { n } \mu _ { i } ( t ) d \omega _ { i } ( t ) + \omega _ { i } ( t ) d \mu _ { i } ( t ) + d \omega _ { i } ( t ) d \mu _ { i } ( t ) .\tag{46}
$$

One can easily show that

$$
\begin{array} { r } { d \omega _ { i } ( t ) = \omega _ { i } ( t ) ( \Sigma _ { i } ( t ) - \Sigma _ { A } ( t ) ) \cdot ( d \mathbf { Z } _ { t } - \Sigma _ { A } ( t ) d t ) , } \end{array}\tag{47}
$$

where $\begin{array} { r } { \Sigma _ { A } ( t ) = \sum _ { i = m + 1 } ^ { n } \omega _ { i } \Sigma _ { i } ( t ) } \end{array}$ . Making use of (24) and (47), we have

$$
\begin{array} { r l } & { d \left( \displaystyle \sum _ { i = m + 1 } ^ { n } \omega _ { i } ( t ) \rho _ { i } ( t ) \right) = \displaystyle \sum _ { i = m + 1 } ^ { n } \omega _ { i } ( t ) \mu _ { i } ( t ) \left[ \left( \Sigma _ { i } ( t ) - \Sigma _ { A } ( t ) \right) \cdot ( d \mathbb { Z } _ { t } - \Sigma _ { A } ( t ) ) d t \right] } \\ & { \qquad + \displaystyle \gamma _ { i } ^ { ( j ) } ( t ) \cdot ( d \mathbb { Z } _ { t } - \Sigma _ { A } ( t ) d t ) + \displaystyle \gamma _ { i } ^ { ( I ) } ( t ) \cdot ( \Sigma _ { i } ( t ) - \Sigma _ { A } ( t ) ) d t \Big ] } \\ & { = \displaystyle \sum _ { i = m + 1 } ^ { n } \omega _ { i } ( t ) \mu _ { i } ( t ) \left( \Sigma _ { i } ( t ) - \Sigma _ { A } ( t ) + \gamma _ { i } ^ { ( I ) } ( t ) \right) \cdot ( d \mathbb { Z } _ { t } - \Sigma _ { A } ( t ) d t ) } \\ & { = \displaystyle \left( \displaystyle \sum _ { i = m + 1 } ^ { n } \omega _ { i } ( t ) \mu _ { i } ( t ) \right) } \\ & { \qquad \times \displaystyle \left[ \displaystyle \sum _ { i = m + 1 } ^ { n } \omega _ { i } ( t ) \left( \gamma _ { i } ^ { ( I ) } ( t ) + \Sigma _ { i } ( t ) \right) - \Sigma _ { A } ( t ) \right] \cdot ( d \mathbb { Z } _ { t } - \Sigma _ { A } ( t ) d t ) } \end{array}
$$

which is (37).

Finally, we point out that $d \mathbf { Z } _ { t } - \Sigma _ { A } ( t ) d t$ is a Brownian motion under the martingale measure corresponding to the numeraire $A _ { m , n } ( t )$ . Let $Q _ { m , n }$ denote this measure, then it is defined by the Radon-Nikodym derivative with the risk neutral measure by Q

$$
\frac { d Q _ { m , n } } { d Q } \bigg | _ { \mathcal { F } _ { t } } = \frac { A _ { m , n } ( t ) } { A _ { m , n } ( 0 ) B ( t ) } = m _ { s } ( t ) \quad \mathrm { f o r } \quad t \leq T _ { n } ,
$$

<!-- page: 36 -->

where $B ( t )$ be the money market account under discrete compounding:

$$
B ( t ) = \left( \prod _ { j = 0 } ^ { \eta _ { t } - 2 } ( 1 + f _ { j } ( T _ { j } ) \Delta T _ { j } ) \right) ( 1 + f _ { \eta _ { t } - 1 } ( T _ { \eta _ { t } - 1 } ) ( t - T _ { \eta _ { t } - 1 } ) ) .
$$

By Ito’s lemma,

$$
d m _ { s } ( t ) = m _ { s } ( t ) \Sigma _ { A } ( t ) \cdot d Z _ { t } .\tag{48}
$$

$$
\begin{array} { r l r } { d \pmb { Z } _ { t } ^ { ( m , n ) } } & { = } & { d \pmb { Z } _ { t } - \left. d \pmb { Z } _ { t } , \frac { d m _ { s } ( t ) } { m _ { s } ( t ) } \right. } \\ & { = } & { d \pmb { Z } _ { t } - \Sigma _ { A } ( t ) d t \quad \bigsqcup } \end{array}
$$

The $Q _ { m , n }$ Brownian motion corresponding to $\boldsymbol { Z } _ { t }$ is defined by

(49)
