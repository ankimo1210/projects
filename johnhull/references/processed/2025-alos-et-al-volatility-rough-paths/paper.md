# 2025-alos-et-al-volatility-rough-paths

<!-- page: 1 -->

## Volatility Modeling in Markovian and Rough Regimes: Signature Methods and Analytical Expansions

Elisa Alòs<sup>\*</sup>, Òscar Burés<sup>†</sup> <sup>§</sup>, Rafael de Santiago<sup>§</sup> and Josep Vives<sup>†</sup> <sup>‡</sup>

May 11, 2026

## Abstract

We study two complementary methodologies for calibrating implied volatility surfaces: analytical approximations and data-driven models based on rough path theory. On the analytical side, we revisit a second-order asymptotic expansion for the Heston model, and we propose a new, VIX-based calibration scheme for the rough Bergomi model. Both methods yield highly accurate and computationally eficient calibration formulas when the underlying dynamics are well specified. In parallel, we develop a signature-based approach in which volatility is represented as a linear functional of the truncated signature of a primary stochastic process, providing a flexible and model-agnostic alternative.

Our numerical experiments compare the two approaches across both Markovian and non-Markovian settings. In the Heston case, signature-based models achieve a level of accuracy comparable to analytical expansions. In the rough Bergomi setting, using a fractional Brownian motion as the primary process, the signature approach continues to perform strongly and in some cases improves upon the Markovian specification, reflecting its ability to capture more complex temporal dependencies. Overall, the results illustrate that analytical methods are highly efective when the model is correctly specified, while signature-based methods ofer a robust and flexible framework for calibration across a wider range of volatility dynamics.

Keywords: Rough volatility, rough path theory, signatures, implied volatility calibration, VIX. JEL Classification: G13, C63, C58.

MSC 2020: 60L70, 60H10, 91G20, 91G60, 60G22.

## 1 Introduction

The realization that constant-volatility models could not account for efects like clustering, heavy tails, and smiles prompted the extension of the Black–Scholes framework to include stochastic volatility. Early models addressed these limitations by introducing a second (correlated) Brownian motion to govern the volatility, yielding more realistic asset price dynamics. This line of research, initiated by Hull and White (1987), Wiggins (1987), Stein and Stein (1991), and Heston (1993), has given rise to a broad and influential literature in mathematical finance.

A particularly influential part of the literature has focused on developing closed-form approximation formulas for implied volatility through asymptotic expansions and perturbation methods applied to parametric models, such as Heston and SABR. These approximations aim to facilitate the calibration of model parameters to market-observed implied volatility surfaces. Eficient calibration is a central task in financial practice, as option prices are typically quoted via implied volatilities, and model parameters must be inferred by inversion. Contributions to this area include, among others, Hagan et al. (2002), Fouque et al. (2003), Medvedev and Scaillet (2007), De Santiago et al. (2008), Antonelli and Scarlatti (2009), Benhamou et al. (2009, 2010a,b), Forde et al. (2010), Forde and Jacquier (2011), Forde et al. (2011), Alòs (2012), Lorig et al. (2013) and Alòs et al. (2015).

arXiv:2507.23392v4 [q-fin.MF] 8 May 2026

<sup>\*</sup>Department of Economics and Business, Universitat Pompeu Fabra and Barcelona School of Economics. Ramón Trias Fargas 25-27, 08005, Barcelona, Spain.

<sup>†</sup>Departament de Matemàtica Econòmica, Financera i Actuarial, Universitat de Barcelona. Diagonal 690–696, 08034 Barcelona, Spain.

<sup>§</sup>Department of Managerial Decision Sciences, IESE Business School. Av. Pearson 21, 08034 Barcelona, Spain. <sup>‡</sup>Institut de Matemàtiques, Universitat de Barcelona. Gran Via de les Corts, 585, 08007 Barcelona, Spain. Institut de Matemàtiques, Universitat de Barcelona. Gran Via de les Corts, 585, 08007 Barcelona, Spain.

Òscar Burés supported by program AGAUR-FI ajuts (2025 FI-1 00580) from the Department of Research and Universities of the Government of Catalonia and the co-funding of the European Social Fund Plus (ESF+).

<!-- page: 2 -->

While these parametric models and their expansions have proven theoretically elegant and computationally tractable, they also come with important limitations. Relying on a fixed model structure may restrict flexibility and hinder the model’s ability to capture certain stylized features observed in market data. In addition, the presence of multiple stochastic drivers often increases computational complexity, requiring the use of numerical tools such as Fourier transforms, Monte Carlo methods, or finite-diference PDE solvers. Moreover, a growing body of empirical evidence suggests that volatility exhibits rough, fractional-like behavior that traditional Markovian models struggle to reproduce. This has led to increased interest in fractional (rough) volatility models, such as those introduced in Comte and Renault (1998), Alòs et al. (2007), and Fukasawa (2017), which more accurately reflect the observed structure of the implied volatility surface and align with empirical evidence on the roughness of volatility paths (e.g., Bayer et al. (2016), Gatheral et al. (2018)).

In response to these challenges, a more recent line of research has embraced non-parametric, data-driven approaches that aim to learn volatility dynamics directly from observed paths, rather than specifying a rigid structural model. A prominent example of this paradigm is the use of rough path theory and signature methods, originally introduced in Chen (1957) and rigorously developed in Lyons (1998). The signature of a path (to be defined precisely below) consists of its iterated integrals and encodes its temporal features into a rich algebraic structure. Over the years, these ideas have found applications in machine learning, time series analysis, and mathematical finance (e.g., Bühler et al. (2020), Arribas et al. (2020), Cuchiero et al. (2023)). Because it relies on functional features rather than a parametric form, signature-based modeling is well suited for capturing behaviors observed in rough volatility models.

In this paper, we consider two complementary approaches to the calibration of implied volatility surfaces. On the one hand, we present analytical approximations for both the Heston and rough Bergomi models. For Heston, we revisit a second-order asymptotic expansion, while for rough Bergomi we introduce a new calibration scheme based on VIX-implied information. These methods yield highly accurate formulas when the underlying model is well specified. On the other hand, we study signature-based approximations in which the volatility is represented as a linear functional of the truncated signature of a primary stochastic process (taken to be, respectively, a Heston variance process and a fractional Brownian motion). This approach does not rely on a fixed parametric specification and provides a flexible framework capable of adapting to diferent volatility dynamics. Rather than contrasting the two methodologies, our aim is to highlight their respective strengths and to assess their performance across both Markovian (Heston) and non-Markovian (rough Bergomi) regimes.

To make the paper self-contained, Section 2 presents the analytical approximations for both models: we first review the second-order expansion technique for the Heston model introduced in Alòs et al. (2015), highlighting its mathematical structure and practical strengths, and then develop a new calibration scheme for the rough Bergomi model, based on VIX-implied volatility information. Section 3 introduces the core elements of rough path theory needed to define and compute path signatures. In Section 4, we develop the signature-based stochastic volatility model, describe its numerical implementation, and outline the training procedure. Section 5 reports numerical results for the Heston setting, including both uncorrelated and correlated dynamics as in Alòs et al. (2015), and compares them with the corresponding analytical approximation. Section 6 presents the results for the rough Bergomi model, using a fractional Brownian motion as the primary process, and provides the analogous comparison.

<!-- page: 3 -->

## 2 Analytic Calibration Methods

In this section we explore two alternative ways of calibrating analytically the implied volatility surface generated by the Heston model and the rough Bergomi model. For the Heston model, we follow the approach in Alòs et al. (2015), which calibrates the model parameters by solving a system of non-linear equations. For the rough Bergomi model, we introduce a new way to calibrate the implied volatility surface using short-maturity information.

## 2.1 A Second-Order Approximation to the Heston Implied Volatility

We provide here a concise overview of the second-order approximation derived in Alòs et al. (2015). For full proofs and theoretical justifications, we refer the reader to the original paper. Our purpose is to use the estimates obtained with this methodology as a benchmark for comparison with the signature-based models that are introduced later.

Assume that, for $t \in [ 0 , T ]$ , the stock price follows the dynamics

$$
d S _ { t } = r S _ { t } d t + \sigma _ { t } S _ { t } d ( \rho W _ { t } + \sqrt { 1 - \rho ^ { 2 } } B _ { t } )\tag{2.1}
$$

under a risk neutral probability P, where $r \geq 0$ is the constant instantaneous interest rate, W and B are independent standard Brownian motions defined in the complete probability space $( \Omega , \mathcal { F } , \mathbb { P } )$ and $\rho \in ( - 1 , 1 )$ . We also assume that the volatility process $\sigma _ { t }$ satisfies

$$
d \sigma _ { t } ^ { 2 } = \kappa ( \theta - \sigma _ { t } ^ { 2 } ) d t + \nu \sqrt { \sigma _ { t } ^ { 2 } } d W _ { t } ,\tag{2.2}
$$

with $2 \kappa \theta \geq \nu ^ { 2 }$ . We denote by $\mathcal { F } ^ { W } = \{ \mathcal { F } _ { t } ^ { W } ; t \in [ 0 , T ] \}$ and $\mathcal { F } ^ { B } = \{ \mathcal { F } _ { t } ^ { B } ; t \in [ 0 , T ] \}$ the filtrations generated, respectively, by W and $B ,$ and we define F as the collection of sigma algebras $\mathcal { F } _ { t } ^ { W } \vee \mathcal { F } _ { t } ^ { B }$ for each $t \in [ 0 , T ]$ , that is, $\mathcal { F } : = \mathcal { F } ^ { W } \vee \mathcal { F } ^ { B }$ . Equations (2.1) and (2.2) constitute what is known as the Heston model.

If we let $X _ { t } : = \ln S _ { t }$ , the price of a European call option at time t with strike K and maturity $T$ is given by

$$
V _ { t } = e ^ { - r ( T - t ) } E _ { t } [ ( e ^ { X _ { T } } - K ) ^ { + } ] ,
$$

where $E _ { t } [ \cdot ] : = E [ \cdot | \mathcal { F } _ { t } ]$ . For a constant volatility $\sigma$ , and letting $k = \ln K$ , the above general expression has the well-known analytical solution

$$
V _ { t } = \mathrm { B S } ( T , t , X _ { t } , k , \sigma ) = e ^ { X _ { t } } \Phi ( d _ { + } ) - e ^ { k - r ( T - t ) } \Phi ( d _ { - } ) ,
$$

where $\Phi$ is the cumulative distribution function of a standard Gaussian random variable, and

$$
d _ { \pm } = \frac { X _ { t } - k + r ( T - t ) } { \sigma \sqrt { T - t } } \pm \frac { \sigma } { 2 } \sqrt { T - t } .
$$

When volatility is stochastic, the Black-Scholes formula no longer provides an exact solution. However, we can define an implied volatility approximation by evaluating the Black-Scholes formula at

$$
V _ { t } \approx \mathrm { B S } ( T , t , X _ { t } , k , v _ { t } ) ,\tag{2.3}
$$

where

$$
v _ { t } = \sqrt { \frac { 1 } { T - t } \int _ { t } ^ { T } E _ { t } [ \sigma _ { s } ^ { 2 } ] d s }
$$

represents the square root of the expected average variance over the remaining life of the option.

Let $V _ { t } ^ { m k t }$ be the market price at time t of a European call option with maturity $T$ and strike K. As the BS function is invertible in the argument $v _ { t } ,$ we can define the implied volatility as the unique $I ( T , K )$ satisfying the equality

$$
\mathrm { B S } ( T , t , X _ { t } , k , I ( T , K ) ) = V _ { t } ^ { m k t } .
$$

<!-- page: 4 -->

Since even in the simplest stochastic volatility models it is generally not feasible to derive closed-form expressions for the implied volatility surface, a variety of approximation methods have been developed to estimate $I ( T , K )$

The method in Alòs et al. (2015) proceeds as follows. First, an approximation to the price of a European call is derived. Based on this, the following second-order expansion of the implied volatility is obtained:

$$
I ( K , T ) \approx v _ { 0 } + I _ { 1 } ( K , T ) + I _ { 2 } ( K , T )
$$

where

$$
\begin{array} { l } { { I _ { 1 } ( K , T ) = \displaystyle \frac { \rho } { 2 v _ { 0 } T } \left( 1 - \frac { d _ { + } ( K , T ) } { v _ { 0 } \sqrt { T } } \right) \mathbb { E } \left[ \int _ { 0 } ^ { T } \sigma _ { s } d \langle M , W \rangle _ { s } \right] } } \\ { { I _ { 2 } ( K , T ) = \displaystyle \frac { 1 } { 8 v _ { 0 } T } \left( \frac { d _ { + } ( K , T ) ^ { 2 } } { v _ { 0 } ^ { 2 } T } - \frac { d _ { + } ( K , T ) } { v _ { 0 } \sqrt { T } } - \frac { 1 } { v _ { 0 } ^ { 2 } T } \right) \mathbb { E } \left[ \int _ { 0 } ^ { T } d \langle M , M \rangle _ { s } \right] } } \end{array}
$$

and $\begin{array} { r } { M _ { t } = \int _ { 0 } ^ { T } E _ { t } ( \sigma _ { s } ^ { 2 } ) d s } \end{array}$ . Finally, using the above expressions together with the term structure of at-the-money (ATM) options, the following asymptotic results are derived:

• When the call is close to maturity $( T \to 0 )$ , the implied volatility can be approximated as:

$$
I ( 0 , K ) \approx \sigma _ { 0 } - \frac { \rho \nu } { 4 \sigma _ { 0 } } ( x - k ) + \frac { \nu ^ { 2 } } { 2 4 \sigma _ { 0 } ^ { 3 } } ( x - k ) ^ { 2 } .\tag{2.4}
$$

• When the European call is far away from maturity $( T \to \infty )$

$$
I ( T , K ) \approx \sqrt { \theta } \left( 1 + \frac { \nu \rho } { 4 \kappa } - \frac { \nu ^ { 2 } } { 3 2 \kappa ^ { 2 } } \right) + \left( \frac { \sigma _ { 0 } ^ { 2 } - \theta } { 2 \kappa \sqrt { \theta } } + \nu \rho \frac { \sigma _ { 0 } ^ { 2 } - 2 \theta } { 4 \kappa ^ { 2 } \sqrt { \theta } } - \nu ^ { 2 } \frac { \sigma _ { 0 } ^ { 2 } - \frac { 5 } { 2 } \theta + 4 \kappa } { 3 2 \sqrt { \theta } \kappa ^ { 3 } } \right) \frac { 1 } { T } .\tag{2.5}
$$

• When the option is at-the-money $( x = k - r T )$ , the expansion around $\sigma _ { 0 }$ is:

$$
I ( T , K ) \approx \sigma _ { 0 } + \frac { 3 \sigma _ { 0 } ^ { 2 } \rho \nu - 6 \kappa ( \sigma _ { 0 } ^ { 2 } - \theta ) - \nu ^ { 2 } } { 2 4 \sigma _ { 0 } } T .\tag{2.6}
$$

These approximations are then used as follows. By fitting a linear equation to the ATM implied volatilities for diferent values of $T ,$ the values of $\sigma _ { 0 }$ and

$$
\frac { 3 \sigma _ { 0 } ^ { 2 } \rho \nu - 6 \kappa ( \sigma _ { 0 } ^ { 2 } - \theta ) - \nu ^ { 2 } } { 2 4 \sigma _ { 0 } }
$$

are obtained from (2.6).

By fitting a linear equation to the implied volatilities for short maturities as a function of the log-moneyness $( x - k )$ , equation (2.4) provides the value of $\rho \nu$ . Notice that for strikes close to the money, the linear component is stronger than the curvature, making it dificult to estimate ν directly.

For large values of $T ,$ , an equation is fitted to the implied volatilities as a function of $1 / T$ , and the values of

$$
{ \sqrt { \theta } } \left( 1 + { \frac { \nu \rho } { 4 \kappa } } - { \frac { \nu ^ { 2 } } { 3 2 \kappa ^ { 2 } } } \right)
$$

and

$$
\left( \frac { \sigma _ { 0 } ^ { 2 } - \theta } { 2 \kappa \sqrt { \theta } } + \nu \rho \frac { \sigma _ { 0 } ^ { 2 } - 2 \theta } { 4 \kappa ^ { 2 } \sqrt { \theta } } - \nu ^ { 2 } \frac { \sigma _ { 0 } ^ { 2 } - \frac 5 2 \theta + 4 \kappa } { 3 2 \sqrt { \theta } \kappa ^ { 3 } } \right) .
$$

are obtained from (2.5).

The previous steps provide a system of three equations. By solving them, the full set of Heston parameters $( \sigma _ { 0 } , \nu , \kappa , \theta , \rho )$ is calibrated.

<!-- page: 5 -->

In particular, with market parameters $S _ { 0 } = 1 0 0 , \sigma _ { 0 } = 0 . 2 , \nu = 0 . 3 , \kappa = 3 , \theta = 0 . 0 9 \mathrm { a n d } \rho = 0 ,$ the parameters calibrated with the above algorithm are:

[Table source crop](assets/tables/2025-alos-et-al-volatility-rough-paths-p0005-block-0002-90be9894a1bd12b3.jpg)
Table 2.1: Calibrated parameters from Alòs et al. (2015) with $\rho = 0$

[Table source crop](assets/tables/2025-alos-et-al-volatility-rough-paths-p0005-block-0003-e57e478510a3b3bc.jpg)
In the correlated case, with $\rho = - 0 . 5$ , the calibrated parameters are: Table 2.2: Calibrated parameters from Alòs et al. (2015) with $\rho = - 0 . 5 .$

These accurate calibrations will serve as a benchmark in Section 5 for comparison with the signature-based model. A limitation of this method lies in the assumption of taking the Heston model as the underlying dynamics for the volatility process. As a result, its flexibility is constrained by the limitations of that specific model, which may not adequately capture roughness or other complex behaviors observed in real markets.

## 2.2 Closed-form calibration of the Rough Bergomi Model

Consider the rough Bergomi model

$$
\begin{array} { r l } & { d S _ { t } = r S _ { t } d t + \sigma _ { t } S _ { t } d \left( \rho W _ { t } + \sqrt { 1 - \rho ^ { 2 } } B _ { t } \right) } \\ & { \sigma _ { t } ^ { 2 } = \sigma _ { 0 } ^ { 2 } \exp \left( \eta W _ { t } ^ { H } - \cfrac { 1 } { 2 } \eta ^ { 2 } t ^ { 2 H } \right) , } \end{array}\tag{2.7}
$$

where $\eta > 0 , H \in ( 0 , 1 )$ and $W _ { t } ^ { H }$ is a Volterra-type fractional Brownian motion:

$$
W _ { t } ^ { H } : = \int _ { 0 } ^ { t } K _ { H } ( t , s ) d W _ { s } ,
$$

with $K _ { H } ( t , s ) = \sqrt { 2 H } ( t - s ) ^ { H - { \frac { 1 } { 2 } } }$ for $0 < s < t$ . Assume that the risk-free rate r is known (it is observable from the market) and that $\rho \neq 0$

In this section we propose a new closed-form calibration procedure for the rough Bergomi model that combines short-time asymptotic results for the implied volatility surface with information extracted from VIX-implied volatility, leading to an eficient and easily implementable estimation of the model parameters. In the same way as with the method for the Heston calibration, we assume that the whole implied volatility is available. By this, we mean that $I ( T , K )$ can be determined for every maturity $T$ and strike K.

Let $H \in ( 0 , 1 / 2 )$ . To estimate the set $( \sigma _ { 0 } , H , \eta , \rho )$ , we proceed as follows.

• Step 1 - Estimation of H. We take two reference strikes on either side of ATM, $K _ { T } ^ { + }$ and $K _ { T } ^ { - }$ , respectively defined by $d _ { + } = 0$ and $d _ { - } = 0$ . The diference $I ( T , K _ { T } ^ { + } ) - I ( T , K _ { T } ^ { - } )$

<!-- page: 6 -->

captures the skew of the implied volatility smile. For maturities $T _ { 1 }$ and $T _ { 2 }$ , Alòs et al. (2025) show that the Hurst index can be estimated as:

$$
\hat { H } = - \frac { 1 } { 2 } + \frac { \ln { \left( \frac { I ( T _ { 1 } , K _ { T _ { 1 } } ^ { + } ) - I ( T _ { 1 } , K _ { T _ { 1 } } ^ { - } ) } { I ( T _ { 2 } , K _ { T _ { 2 } } ^ { + } ) - I ( T _ { 2 } , K _ { T _ { 2 } } ^ { - } ) } \cdot \frac { I ^ { 2 } ( T _ { 2 } , K ^ { * } ) } { I ^ { 2 } ( T _ { 1 } , K ^ { * } ) } \right) } } { \ln { \left( \frac { T _ { 1 } } { T _ { 2 } } \right) } } ,
$$

where $K ^ { * }$ denotes the ATM log-strike. As this approximation does not depend on specific model parameters, it can be used without first calibrating a specific volatility model. With rough fractional volatility, $\hat { H }$ provides a quick way to estimate the Hurst parameter from the implied volatility surface.

• Step 2 - Estimation of $\eta .$ To estimate η, we use the short-time behavior of the implied volatility of VIX options. Let $\Delta$ be 30 trading days. The VIX index at time $T$ is defined as

$$
V I X _ { T } = \sqrt { \frac { 1 } { \Delta } E _ { T } \left[ \int _ { T } ^ { T + \Delta } \sigma _ { s } ^ { 2 } d s \right] } .
$$

Consider a European option with payof $( V I X _ { T } \textrm { -- } K ) _ { + }$ . Let the strike be $K \ : = \ : V I X _ { 0 }$ and denote by $I _ { T } ^ { \bar { V } I X } ( 0 )$ the implied volatility of such an option. That is, $I _ { T } ^ { V I X } ( 0 )$ is the ATM implied volatility (ATMI) of a European option on the VIX index with maturity $T .$ Theorem 8 in Alòs et al. (2022) proves a property of the short-time behavior of the ATMI in a general setting. Applying this result to the particular case of $I _ { T } ^ { V I X } ( 0 )$ under rough Bergomi dynamics, the following result is derived in Example 10.2.3 of Alòs and Garcia Lorite (2025):

$$
\operatorname * { l i m } _ { T \to 0 } I _ { T } ^ { V I X } ( 0 ) = \frac { \eta \sqrt { 2 H } \Delta ^ { H - 1 / 2 } } { 2 ( H + \frac { 1 } { 2 } ) } .
$$

Once we know $\hat { H }$ , the estimator $\hat { \eta }$ is thus computed as

$$
\hat { \eta } = \frac { I _ { T } ^ { V I X } ( 0 ) ( 2 \hat { H } + 1 ) } { \sqrt { 2 \hat { H } } \Delta ^ { \hat { H } - 1 / 2 } } , \mathrm { p r o v i d e d } T \approx 0 .
$$

• Step 3 - Estimation of $\rho .$ The main result in Alòs et al. (2024) deals with the short-time skew of the ATMI (Theorem 1). When applied to the rough Bergomi model (Section 5.2), the authors show that

$$
\operatorname * { l i m } _ { T \to 0 } T ^ { 1 / 2 - H } \partial _ { K } I ( 0 , K ^ { \star } ) = \frac { 2 \eta \rho \sqrt { 2 H } } { 3 + 4 H ( 2 + H ) } ,
$$

where $K ^ { \star }$ is the ATM strike at time 0. Given the estimates $\hat { H }$ and $\hat { \eta } .$ , and using a finite diference scheme to compute $\partial _ { k } I ( T , K ^ { \star } )$ , we obtain the estimator $\hat { \rho }$ as:

$$
\hat { \rho } = \frac { T ^ { 1 / 2 - \hat { H } } \partial _ { k } I ( 0 , K ^ { \star } ) ( 3 + 4 \hat { H } ( 2 + \hat { H } ) ) } { 2 \hat { \eta } \sqrt { 2 \hat { H } } } , \quad \mathrm { p r o v i d e d ~ } T \approx 0 .
$$

• Step 4 - Estimation of $\sigma _ { 0 }$ . For this step, only $\hat { H }$ is required. Theorem 6.5.5 in Alòs and Garcia Lorite (2025) shows that the ATM implied volatility of European options corresponding to a rough Bergomi model satisfies the following asymptotic relationship:

$$
I ( T , K ^ { \star } ) \approx \sigma _ { 0 } + c _ { 1 } T ^ { 2 H } + O ( T ^ { H + 1 / 2 } ) .
$$

Thus, considering several ATM options with diferent maturities, we can compute $I ( T , K ^ { \star } )$ and do a regression to obtain $\sigma _ { 0 }$ . This regression also provides $c _ { 1 }$ , but since all other parameters have been calibrated, its value is not relevant.

<!-- page: 7 -->

This algorithm provides an easy-to-implement calibration of the rough Bergomi model using only information on the short-term regime.

To test its accuracy, we let the market parameters be $\sigma _ { 0 } = 0 . 2$ $H = 0 . 1$ ， $\eta = 0 . 5$ and $\rho = - 0 . 7 $ which we consider as ground truth. The algorithm described above yields the following calibration, which will be used in Section 6 as the benchmark for comparison with the signature-based model.

[Table source crop](assets/tables/2025-alos-et-al-volatility-rough-paths-p0007-block-0003-cd4e54eeee087012.jpg)
Table 2.3: Calibrated parameters using the rough Bergomi calibration algorithm.

In Section 4 we will introduce a data-driven model based on path signatures, which does not assume any specific parametric form for the volatility process. This approach can learn directly from a primary noise, enabling it to adapt to a broader class of behaviors.

## 3 Path Signatures

A natural way to incorporate signatures into stochastic volatility modeling is through the framework proposed by Cuchiero et al. (2023), where the asset price is modeled as a linear functional of the signature of a driving noise process. Although this approach performs well under the assumption that the volatility process is a semimartingale, it is less suitable in settings characterized by rough volatility, where such regularity assumptions no longer hold.

To address this limitation, Cuchiero et al. (2025) propose an alternative formulation in which the volatility process itself is expressed as a linear functional of the signature of the primary noise. Although this approach is computationally more intensive, it does not require the volatility to satisfy any martingale or semimartingale condition, making it particularly well-suited to the modeling of rough or highly irregular volatility dynamics.

In this paper, we adopt a similar approach, that is, we assume that the volatility is a continuous function of a general underlying stochastic process, called the primary noise, which does not need to be of the Heston type. This continuous function is then approximated by a linear combination of the elements of the signature of the primary noise.

We now introduce the essential ideas from rough path theory that underpin the signaturebased approach. An insightful and clear exposition of rough paths is given in the Saint-Flour lecture notes by Lyons et al. (2007). Other good references are Chevyrev and Kormilitzin (2016), Cuchiero et al. (2023), and Lyons and Qian (2002). We follow Geng (2021) and Díaz (2023) in several places. We include some proofs to support intuition.

The need for signatures arises from the problem of defining integrals of the form

$$
\int _ { s } ^ { t } y _ { u } d x _ { u }\tag{3.1}
$$

when the integrand y and integrator x lack suficient regularity. If both x and y have bounded variation, the integral is defined in the Riemann–Stieltjes or Lebesgue–Stieltjes sense. If x and y are α-Hölder continuous with $\alpha > \frac { 1 } { 2 }$ , Young’s theory applies. However, when $\alpha \leq \textstyle { \frac { 1 } { 2 } }$ , classical constructions break down, and the Riemann sums

$$
\sum _ { t _ { i } \in \mathcal { D } } y _ { t _ { i - 1 } } ( x _ { t _ { i } } - x _ { t _ { i - 1 } } )
$$

may fail to converge as the mesh $| \mathcal { D } | 0$ . At best, these sums provide a first-order approximation to the integral, and additional structure is needed to make sense of the limit.

<!-- page: 8 -->

Note that these approximations depend only on the increments $\boldsymbol { x } _ { t } ~ - ~ \boldsymbol { x } _ { s }$ . In fact, the first level of the signature of a path x corresponds precisely to its increments. The signature can then be understood as an enhanced path that augments its first-order increments with higher-order information in the form of iterated integrals.

To illustrate why higher-order terms are essential, we borrow the following example from Geng (2021). Consider a smooth function $F$ and let $y _ { t } = F ( x _ { t } )$ . Then, formally, one can write:

$$
{ \begin{array} { r l } { \displaystyle \int _ { s } ^ { t } F ( x _ { u } ) d x _ { u } = F ( x _ { s } ) ( x _ { t } - x _ { s } ) + \int _ { s } ^ { t } ( F ( x _ { u } ) - F ( x _ { s } ) ) d x _ { u } } & { } \\ { \displaystyle = F ( x _ { s } ) ( x _ { t } - x _ { s } ) + \int _ { s } ^ { t } \int _ { s } ^ { u } D F ( x _ { v } ) d x _ { v } d x _ { u } } & { } \\ { \displaystyle = F ( x _ { s } ) ( x _ { t } - x _ { s } ) + D F ( x _ { s } ) \int _ { s } ^ { t } \int _ { s } ^ { u } d x _ { v } d x _ { u } } & { } \\ { \displaystyle } & { ~ + \int _ { s } ^ { t } \int _ { s } ^ { u } ( D F ( x _ { v } ) - D F ( x _ { s } ) ) d x _ { v } d x _ { u } . } \end{array} }
$$

Continuing recursively leads to the formal expansion

$$
\begin{array} { l } { \displaystyle \int _ { s } ^ { t } F ( x _ { u } ) d x _ { u } = F ( x _ { s } ) ( x _ { t } - x _ { s } ) + D F ( x _ { s } ) \int _ { s } ^ { t } \int _ { s } ^ { u } d x _ { v } d x _ { u } } \\ { \displaystyle + D ^ { 2 } F ( x _ { s } ) \int _ { s } ^ { t } \int _ { s } ^ { u } \int _ { s } ^ { v } d x _ { r } d x _ { v } d x _ { u } } \\ { \displaystyle + D ^ { 3 } F ( x _ { s } ) \int _ { s } ^ { t } \int _ { s } ^ { u } \int _ { s } ^ { v } \int _ { s } ^ { r } d x _ { z } d x _ { r } d x _ { v } d x _ { u } + \cdot \cdot . . } \end{array}
$$

That is, computing the integral $\textstyle \int _ { s } ^ { t } F ( x _ { u } ) d x _ { u }$ requires access to the full collection of iterated integrals of $x ,$ not just its increments.

Note that if x takes values in $\mathbb { R } ^ { d } .$ , then the second-level iterated integral

$$
\int _ { s } ^ { t } \int _ { s } ^ { u } d x _ { v } d x _ { u }
$$

is a tensor consisting of $d ^ { 2 }$ terms of the form $\textstyle \int _ { s } ^ { t } \int _ { s } ^ { u } d x _ { v } ^ { i } d x _ { u } ^ { j }$ . Higher-order levels live in higher tensor powers. Thus, the natural way to organize this structure is through the tensor algebra, introduced formally below.

In low regularity settings (like Brownian motion or rough volatility models), these higher-order iterated integrals are not well-defined. Rough path theory allows us to define them abstractly, thereby extending integration to paths of low regularity.

Informally, if x is α-Hölder continuous, we expect that

$$
\left| \int _ { s < t _ { 1 } < \cdots < t _ { n } < t } d x _ { t _ { 1 } } \cdot \cdot \cdot d x _ { t _ { n } } \right| \lesssim | t - s | ^ { n \alpha } ,
$$

so higher-order terms decay rapidly. This motivates approximating the integral of a function $F ( x _ { t } )$ against $d \boldsymbol { x } _ { t }$ as

$$
\int _ { s } ^ { t } F ( x _ { u } ) d x _ { u } \approx \sum _ { k = 1 } ^ { N } \mathrm { D F } ^ { ( k - 1 ) } ( x _ { s } ) \mathbf { X } _ { s , t } ^ { k } ,
$$

where $\begin{array} { r } { \mathbf { X } _ { s , t } ^ { k } = \int _ { s < t _ { 1 } < \dots < t _ { k } < t } d x _ { t _ { 1 } } \cdot \cdot \cdot d x _ { t _ { k } } } \end{array}$ will represent the k-th level of the signature of $x .$ The truncation level N will depend on the regularity of x.

As a result, to define pathwise integration in irregular settings, and to model functionals of paths (such as volatility), we must specify a family of tensors $( \mathbf { X } _ { s , t } ^ { k } ) _ { k = 1 } ^ { N }$ satisfying some algebraic and analytic constraints. These will form the signature of a rough path, which we now formalize by introducing the tensor algebra.

<!-- page: 9 -->

## 3.1 Tensor Algebras

Let V be a real-valued finite dimensional vector space. In practice, V will typically be $\mathbb { R } ^ { d }$ , for some $d \geq 1$ . For any non-negative integer n, we denote the n-th tensor power of V as

$$
V ^ { \otimes n } : = V \otimes \cdots \otimes V ,
$$

with $V ^ { \otimes 0 } = \mathbb { R }$ . The tensor power of a vector space is a vector space as well. Moreover, if $V$ is isomorphic to $\mathbb { R } ^ { d }$ for some $d \geq 1$ then $V ^ { \otimes n }$ is isomorphic to $\mathbb { R } ^ { d ^ { n } }$ . In particular, all tensor powers of R are isomorphic to R itself.

If $e _ { 1 } , \ldots , e _ { d }$ is a basis of V, then the elements $\{ e _ { i _ { 1 } } \otimes \cdot \cdot \cdot \otimes e _ { i _ { n } } ; ( i _ { 1 } , \ldots , i _ { n } ) \in \{ 1 , \ldots , d \} ^ { n } \}$ are a basis of $V ^ { \otimes n }$ , that is, every tensor $v \in V ^ { \otimes n }$ can be written uniquely as

$$
v = \sum _ { 1 \leq i _ { 1 } , \ldots , i _ { n } \leq d } \lambda _ { i _ { 1 } , \ldots , i _ { n } } e _ { i _ { 1 } } \otimes \cdot \cdot \cdot \otimes e _ { i _ { n } } ,
$$

for some coeficients $\{ \lambda _ { i _ { 1 } , \dots , i _ { n } } \in \mathbb { R } ; ( i _ { 1 } , \dots , i _ { n } ) \in \{ 1 , \dots , d \} ^ { n } \}$

Definition 3.1 (Extended Tensor Algebra). We define the extended tensor algebra $T ( ( V ) )$ over $V$ as the set

$$
T ( ( V ) ) = \{ \mathbf { a } = ( a _ { 0 } , a _ { 1 } , \ldots ) ; \ a _ { n } \in V ^ { \otimes n } \}
$$

equipped with the following element-wise addition and scalar product

$$
\mathbf { a } + \mathbf { b } = ( a _ { 0 } + b _ { 0 } , \ldots , a _ { n } + b _ { n } , \ldots ) , \quad \lambda \mathbf { a } = ( \lambda a _ { 0 } , \lambda a _ { 1 } , \ldots ) ,
$$

and endowed with the product ⊗ defined by

$$
\mathbf { a } \otimes \mathbf { b } = ( c _ { 0 } , c _ { 1 } , \ldots ) ,
$$

where

$$
c _ { n } = \sum _ { i + j = n } a _ { i } \otimes b _ { j } .
$$

In the same way that we can define a product in $T ( ( V ) )$ , we can characterize its invertible elements. Specifically, if $\mathbf { a } \in T ( ( V ) )$ and the zeroth level $a _ { 0 } \in \mathbb { R }$ is nonzero, then a admits a multiplicative inverse in $T ( ( V ) )$ , given by the formal series:

$$
{ \bf a } ^ { - 1 } = \sum _ { n \geq 0 } \frac { 1 } { a _ { 0 } } \left( { \bf 1 } - \frac { { \bf a } } { a _ { 0 } } \right) ^ { \otimes n } ,
$$

where $\mathbf { 1 } : = ( 1 , 0 , 0 , \dots )$ is the multiplicative identity in $T ( ( V ) )$ , and the powers are taken with respect to the tensor product. Finally, we define the tensor algebra over $V$ as the set

$$
T ( V ) = \{ \mathbf { a } \in T ( ( V ) ) ; \ \exists n \in \mathbb { N } { \mathrm { ~ s u c h ~ t h a t ~ } } a _ { k } = 0 \ \forall k \geq n \} .
$$

In other words, $T ( V )$ consists of all formal tensor series with only finitely many nonzero terms.

To make the notation more concise, define the multi-index $I = ( i _ { 1 } , \ldots , i _ { n } ) \in \{ 1 , \ldots , d \} ^ { n }$ . We then write $e _ { I } = e _ { i _ { 1 } } \otimes \cdot \cdot \cdot \otimes e _ { i _ { n } }$ , and we denote the length of I by $\left| I \right| = n$ . In order to write scalars, we set $\alpha = \alpha e _ { \emptyset }$ , with $| \emptyset | = 0$ . This notation allows us to write any tensor $v \in V ^ { \otimes n }$ as

$$
v = \sum _ { | I | = n } \lambda _ { I } e _ { I } ,
$$

for some coeficients $\{ \lambda _ { I } \in \mathbb { R } ; | I | = n \}$

Given an element of $T ( V )$ , we can naturally associate a linear map on $T ( ( V ) )$ , in a manner analogous to the Riesz representation Theorem.

<!-- page: 10 -->

Definition 3.2. For any $\begin{array} { r } { \ell = \sum _ { | I | \geq 0 } \ell _ { I } e _ { I } \in T ( V ) } \end{array}$ and $\begin{array} { r } { \mathbf { a } = \sum _ { | I | \geq 0 } a _ { I } e _ { I } \in T ( ( V ) ) } \end{array}$ , we define the map $\langle \cdot , \cdot \rangle : T ( V ) \times T ( ( V ) ) \to \mathbb { R } \ b \chi$

$$
\langle \ell , \mathbf { a } \rangle : = \sum _ { | I | \geq 0 } \ell _ { I } a _ { I } .\tag{3.2}
$$

This map is well defined because there are only finitely many nonzero elements $\ell _ { I }$ . Note that we can recover the coordinate $a _ { I }$ of a with $\langle e _ { I } , \mathbf { a } \rangle = a _ { I }$

We now introduce another important product on $T ( V )$ . The shufle product is a way to combine two tensors in $T ( V )$ by interweaving their entries in all possible ways, while preserving the relative order within each tensor. Its efect is usually compared to that of shufling cards from two decks while keeping each deck’s internal order intact. The shufle product is important in rough path theory because it encodes how products of iterated integrals combine.

Definition 3.3. For any multi-indices $I = ( i _ { 1 } , \dots , i _ { n } )$ and $J = \left( j _ { 1 } , \ldots , j _ { m } \right)$ , let $I ^ { \prime } = ( i _ { 1 } , \ldots , i _ { n - 1 } )$ and $J ^ { \prime } = ( j _ { 1 } , \ldots , j _ { m - 1 } )$ . The shufle product $e _ { I }$  $e _ { J }$ is defined recursively as

$$
e _ { I } \sqcup e _ { J } = ( e _ { I ^ { \prime } } \sqcup e _ { J } ) \otimes e _ { i _ { n } } + ( e _ { I } \sqcup e _ { J ^ { \prime } } ) \otimes e _ { j _ { m } } ,
$$

with the convention $e _ { I }$  $e _ { \varnothing } = e _ { \varnothing } \sqcup e _ { I } = e _ { I }$

Example 3.4. If we consider $e _ { 1 } \otimes e _ { 2 }$ and $e _ { 3 }$ we get

$$
\left( e _ { 1 } \otimes e _ { 2 } \right) \sqcup e _ { 3 } = e _ { 1 } \otimes e _ { 3 } \otimes e _ { 2 } + e _ { 3 } \otimes e _ { 1 } \otimes e _ { 2 } + e _ { 1 } \otimes e _ { 2 } \otimes e _ { 3 } .
$$

The shufle product of two tensors of lengths m and n has $\binom { m + n } { m }$ elements.

Example 3.5. Consider $I = \{ 1 , 2 , 3 \}$ and $J = \{ 2 , 1 \}$ . With a slight abuse of notation, we may write $e _ { I } = e _ { 1 } \otimes e _ { 2 } \otimes e _ { 3 } = e _ { 1 2 3 }$ and $e _ { J } = e _ { 2 } \otimes e _ { 1 } = e _ { 2 1 }$ . To better observe the shufling, in the expression below we underline the indexes corresponding to $e _ { 2 1 } { : }$

$$
\begin{array} { r l } & { e _ { 1 2 3 } \sqcup e _ { 2 1 } = e _ { 1 2 3 \underline { { 2 1 } } } + e _ { \underline { { 2 1 } } 2 3 \underline { { 1 } } } + e _ { \underline { { 2 1 } } 1 2 3 } + e _ { \underline { { 2 1 } } \underline { { 1 } } 2 3 } + e _ { \underline { { 2 1 } } \underline { { 2 1 } } 3 } } \\ & { \qquad + e _ { 1 \underline { { 2 } } 2 3 \underline { { 1 } } } + e _ { 1 \underline { { 2 } } \underline { { 2 1 } } 3 } + e _ { 1 \underline { { 2 1 } } 2 3 } + e _ { 1 2 \underline { { 2 3 } } \underline { { 1 } } } + e _ { 1 2 \underline { { 2 1 } } 3 } } \\ & { \qquad = e _ { 1 2 3 2 1 } + e _ { 1 2 1 2 3 } + 2 e _ { 1 2 2 1 3 } + 2 e _ { 1 2 2 3 1 } + 2 e _ { 2 1 1 2 3 } + e _ { 2 1 2 1 3 } + e _ { 2 1 2 3 1 } . } \end{array}
$$

While $e _ { 1 } \otimes e _ { 2 } \otimes e _ { 3 } \in V ^ { \otimes 3 }$ and $e _ { 2 } \otimes e _ { 1 } \in V ^ { \otimes 2 }$ , note that $e _ { 1 } \otimes e _ { 2 } \otimes e _ { 3 }$  $e _ { 2 } \otimes e _ { 1 } \in V ^ { \otimes 5 }$ . As we shall see in Section 4.1, the shufle product sharply increases the order of computations required to construct the signature-based approximation to the volatility.

Let $\ell ^ { 1 } , \ell ^ { 2 } \in T ( V )$ , with $\begin{array} { r } { \ell ^ { 1 } = \sum _ { | I | \geq 0 } \ell _ { I } ^ { 1 } e _ { I } } \end{array}$ and $\begin{array} { r } { \ell ^ { 2 } = \sum _ { | J | \geq 0 } \ell _ { J } ^ { 2 } e _ { J } } \end{array}$ . We then have:

$$
\ell ^ { 1 } \sqcup \ell ^ { 2 } = \sum _ { | I | , | J | \geq 0 } \ell _ { I } ^ { 1 } \ell _ { J } ^ { 2 } e _ { I } \sqcup e _ { J } .
$$

The collection $( T ( V ) , + , \cdot , \sqcup )$ is a commutative algebra.

## 3.2 Signature of Paths of Bounded Variation

We say that $\mathcal { D } _ { [ 0 , T ] } = \{ t _ { 0 } , t _ { 1 } , \dots , t _ { n } \}$ is a partition of the interval [0, T] if $0 = t _ { 0 } < t _ { 1 } < \cdot \cdot \cdot <$ $t _ { n } = T$ . If the interval is clear from the context, we will simply write D. Let V be a d-dimensional vector space.

Definition 3.6. Let $p \geq 1$ . A continuous path $X : [ 0 , T ] V$ has finite p-variation in [0, T] if

$$
| | X | | _ { p } = \left( \operatorname* { s u p } _ { \mathcal { D } } \sum _ { t _ { i } \in \mathcal { D } } | X _ { t _ { i + 1 } } - X _ { t _ { i } } | ^ { p } \right) ^ { 1 / p }
$$

is finite. We denote by $\mathcal { V } ^ { p } ( [ 0 , T ] )$ the set of continuous paths with finite p-variation in $[ 0 , T ]$

<!-- page: 11 -->

It is not dificult to show that if $1 < p < q$ , then

$$
\mathcal { V } ^ { 1 } ( [ 0 , T ] ) \subset \mathcal { V } ^ { p } ( [ 0 , T ] ) \subset \mathcal { V } ^ { q } ( [ 0 , T ] ) \subset \mathcal { C } ( [ 0 , T ] ) .
$$

If $X \in \mathcal { V } ^ { 1 } ( [ 0 , T ] )$ , we say that X is of bounded variation.

To define the signature of a continuous path of bounded variation, we need to define integrals with respect to paths. Notice that, since X has bounded variation, one can define the integral with respect to X using Young’s integration theory (see Young (1936)).

Definition 3.7 (Signature). Consider a d-dimensional vector space V and let $X : [ 0 , T ] V$ be a continuous path of bounded variation. Using the multi-index notation $I = ( i _ { 1 } , \ldots , i _ { n } ) \in$ $\{ 1 , \ldots , d \} ^ { n }$ , we define the signature of X on the interval [0, T] as

$$
S ( X ) _ { 0 , T } = \sum _ { | I | \geq 0 } S ( X ) _ { 0 , T } ^ { I } e _ { I } ,
$$

where the coeficients of the signature are defined recursively as

$$
\begin{array} { l } { { S ( X ) _ { 0 , T } ^ { 0 } = \langle e _ { \emptyset } , S ( X ) _ { 0 , T } \rangle : = 1 } } \\ { { S ( X ) _ { 0 , T } ^ { I } = \langle e _ { I } , S ( X ) _ { 0 , T } \rangle : = \displaystyle \int _ { 0 } ^ { T } \langle e _ { I ^ { \prime } } , S ( X ) _ { 0 , s } \rangle d X _ { s } ^ { i _ { n } } . } } \end{array}
$$

Recall that $I ^ { \prime } = ( i _ { 1 } , \cdots , i _ { n - 1 } )$ . The element of the signature corresponding to index I can be written as

$$
S ( X ) _ { 0 , T } ^ { i _ { 1 } , \dots , i _ { n } } = \int _ { 0 < s _ { 1 } < \cdots < s _ { n } < T } d X _ { s _ { 1 } } ^ { i _ { 1 } } \cdot \cdot \cdot d X _ { s _ { n } } ^ { i _ { n } } .
$$

To gain some insight into the structure of the signature, consider the following two examples from Chevyrev and Kormilitzin (2016).

Example 3.8. Let $X : [ 0 , t ] $ R be a one-dimensional path of bounded variation. Note that the multi-indexes are $I = ( i _ { 1 } , \cdot \cdot \cdot , i _ { n } ) \in \{ 1 \} ^ { n }$ . The signature of X is then given by

$$
\begin{array} { l } { { S ( X ) _ { 0 , t } ^ { 0 } = 1 } } \\ { { S ( X ) _ { 0 , t } ^ { 1 } = \displaystyle \int _ { 0 } ^ { t } d X _ { s } = X _ { t } - X _ { 0 } } } \\ { { S ( X ) _ { 0 , t } ^ { 1 1 } = \displaystyle \int _ { 0 } ^ { t } \int _ { 0 } ^ { s } d X _ { u } d X _ { s } = \displaystyle \frac { 1 } { 2 ! } ( X _ { t } - X _ { 0 } ) ^ { 2 } } } \\ { { S ( X ) _ { 0 , t } ^ { 1 1 1 } = \displaystyle \int _ { 0 } ^ { t } \int _ { 0 } ^ { s } \int _ { 0 } ^ { u } d X _ { r } d X _ { u } d X _ { s } = \displaystyle \frac { 1 } { 3 ! } ( X _ { t } - X _ { 0 } ) ^ { 3 } } } \end{array}
$$

and so on.

Example 3.9. Let $X : [ 0 , 5 ] \to \mathbb { R } ^ { 2 }$ be defined by $X _ { t } \ = \ ( X _ { t } ^ { 1 } , X _ { t } ^ { 2 } ) \ = \ ( 3 + t , ( 3 + t ) ^ { 2 } )$ . Being a two-dimensional path, the multi-indexes are $I = ( i _ { 1 } , \cdot \cdot \cdot , i _ { n } ) \in \{ 1 , 2 \} ^ { n }$ . The elements of the signature are

$$
S ( X ) _ { 0 , 5 } ^ { 0 } = 1
$$

$$
S ( X ) _ { 0 , 5 } ^ { 1 } = \int _ { 0 } ^ { 5 } d X _ { t } ^ { 1 } = \int _ { 0 } ^ { 5 } d t = X _ { 5 } ^ { 1 } - X _ { 0 } ^ { 1 } = 5
$$

$$
S ( X ) _ { 0 , 5 } ^ { 2 } = \int _ { 0 } ^ { 5 } d X _ { t } ^ { 2 } = \int _ { 0 } ^ { 5 } 2 ( 3 + t ) d t = X _ { 5 } ^ { 2 } - X _ { 0 } ^ { 2 } = 5 5
$$

$$
S ( X ) _ { 0 , 5 } ^ { 1 1 } = \int _ { 0 } ^ { 5 } \int _ { 0 } ^ { t } d X _ { s } ^ { 1 } d X _ { t } ^ { 1 } = \int _ { 0 } ^ { 5 } \left[ \int _ { 0 } ^ { t } d s \right] d t = { \frac { 2 5 } { 2 } } \quad
$$

$$
S ( X ) _ { 0 , 5 } ^ { 1 2 } = \int _ { 0 } ^ { 5 } \int _ { 0 } ^ { t } d X _ { s } ^ { 1 } d X _ { t } ^ { 2 } = \int _ { 0 } ^ { 5 } \left[ \int _ { 0 } ^ { t } d s \right] 2 ( 3 + t ) d t = \frac { 4 7 5 } { 3 }
$$

<!-- page: 12 -->

$$
S ( X ) _ { 0 , 5 } ^ { 2 1 } = \int _ { 0 } ^ { 5 } \int _ { 0 } ^ { t } d X _ { s } ^ { 2 } d X _ { t } ^ { 1 } = \int _ { 0 } ^ { 5 } \left[ \int _ { 0 } ^ { t } 2 ( 3 + s ) d s \right] d t = { \frac { 3 5 0 } { 3 } }
$$

$$
S ( X ) _ { 0 , 5 } ^ { 2 2 } = \int _ { 0 } ^ { 5 } \int _ { 0 } ^ { t } d X _ { s } ^ { 2 } d X _ { t } ^ { 2 } = \int _ { 0 } ^ { 5 } \left[ \int _ { 0 } ^ { t } 2 ( 3 + s ) d s \right] 2 ( 3 + t ) d t = { \frac { 3 0 2 5 } { 2 } }
$$

$$
S ( X ) _ { 0 , 5 } ^ { 1 1 1 } = \int _ { 0 } ^ { 5 } \int _ { 0 } ^ { t } \int _ { 0 } ^ { s } d X _ { u } ^ { 1 } d X _ { s } ^ { 1 } d X _ { t } ^ { 1 } = \int _ { 0 } ^ { 5 } \left[ \int _ { 0 } ^ { t } \left[ \int _ { 0 } ^ { s } d u \right] d s \right] d t = \frac { 1 2 5 } { 6 }
$$

and so on. The signature of X on [0, 5] can therefore be written as

$$
S ( X ) _ { 0 , 5 } = ( 1 , \ 5 , \ 5 5 , \ 1 2 . 5 , \ 1 5 8 . 3 3 , \ 1 1 6 . 6 6 , \ 1 5 1 2 . 5 , \ 2 0 . 8 3 , \ldots ) .
$$

The next result, known as Chen’s identity, shows that, even though a path’s signature is defined algebraically, it still captures the way the path evolves over time. In particular, it enables the reconstruction of the signature of X over the interval [0, T] provided that it is known on a collection of subintervals that cover $[ 0 , T ]$

Theorem 3.10 (Chen’s identity). Let $X : [ 0 , T ] V$ be a continuous path of bounded variation. Then, for all $t \in ( 0 , T )$ ,

$$
S ( X ) _ { 0 , T } = S ( X ) _ { 0 , t } \otimes S ( X ) _ { t , T } .\tag{3.3}
$$

Proof. We need to prove that, given $i _ { 1 } , \dots , i _ { n } ,$ then

$$
S ( X ) _ { 0 , T } ^ { i _ { 1 } , . . . , i _ { n } } = \sum _ { k = 0 } ^ { n } S ( X ) _ { 0 , t } ^ { i _ { 1 } , . . . , i _ { k } } S ( X ) _ { t , T } ^ { i _ { k + 1 } , . . . , i _ { n } }
$$

We use induction on the level of signature n. If $n = 0$ then (3.3) is simply

$$
1 = 1 \otimes 1 ,
$$

which holds trivially. Assume that (3.3) holds for all $n \geq 0$ . For $n + 1$ we have

$$
\begin{array} { l } { S ( X ) _ { 0 , T } ^ { i _ { 1 } , \dots , i _ { n + 1 } } = \displaystyle \int _ { 0 } ^ { T } S ( X ) _ { 0 , s } ^ { i _ { 1 } , \dots , i _ { n } } d X _ { s } ^ { i _ { n + 1 } } } \\ { \displaystyle \quad = \int _ { 0 } ^ { t } S ( X ) _ { 0 , s } ^ { i _ { 1 } , \dots , i _ { n } } d X _ { s } ^ { i _ { n + 1 } } + \int _ { t } ^ { T } S ( X ) _ { 0 , s } ^ { i _ { 1 } , \dots , i _ { n } } d X _ { s } ^ { i _ { n + 1 } } } \\ { \displaystyle \quad = S ( X ) _ { 0 , t } ^ { i _ { 1 } , \dots , i _ { n + 1 } } + \int _ { t } ^ { T } S ( X ) _ { 0 , s } ^ { i _ { 1 } , \dots , i _ { n } } d X _ { s } ^ { i _ { n + 1 } } } \\ { \displaystyle \quad = S ( X ) _ { 0 , t } ^ { i _ { 1 } , \dots , i _ { n + 1 } } + \int _ { t } ^ { T } \sum _ { k = 0 } ^ { n } S ( X ) _ { 0 , t } ^ { i _ { 1 } , \dots , i _ { k } } S ( X ) _ { t , s } ^ { i _ { k + 1 } , \dots , i _ { n } } d X _ { s } ^ { i _ { n + 1 } } , } \end{array}
$$

where the last equality follows from the induction step. Rearranging,

$$
\begin{array} { l } { S ( X ) _ { 0 , T } ^ { i _ { 1 } , \dots , i _ { n + 1 } } = S ( X ) _ { 0 , t } ^ { i _ { 1 } , \dots , i _ { n + 1 } } + \displaystyle \sum _ { k = 0 } ^ { n } S ( X ) _ { 0 , t } ^ { i _ { 1 } , \dots , i _ { k } } \int _ { t } ^ { T } S ( X ) _ { t , s } ^ { i _ { k + 1 } , \dots , i _ { n } } d X _ { s } ^ { i _ { n + 1 } } } \\ { \displaystyle \qquad = S ( X ) _ { 0 , t } ^ { i _ { 1 } , \dots , i _ { n + 1 } } + \sum _ { k = 0 } ^ { n } S ( X ) _ { 0 , t } ^ { i _ { 1 } , \dots , i _ { k } } S ( X ) _ { t , T } ^ { i _ { k + 1 } , \dots , i _ { n + 1 } } } \\ { \displaystyle \qquad = \sum _ { k = 0 } ^ { n + 1 } S ( X ) _ { 0 , t } ^ { i _ { 1 } , \dots , i _ { k } } S ( X ) _ { t , T } ^ { i _ { k + 1 } , \dots , i _ { n + 1 } } . } \end{array}
$$

which concludes the proof.

From the definition of the signature, it is clear that $S ( X ) _ { 0 , T } \in T ( ( V ) )$ . However, we can show that the signature of X lies in a smaller space.

<!-- page: 13 -->

Definition 3.11. An element $\mathbf { a } \in T ( ( V ) )$ is said to be group-like if for every pair $\ell ^ { 1 } , \ell ^ { 2 } \in T ( V )$ we have

$$
\langle \ell ^ { 1 } , \mathbf { a } \rangle \langle \ell ^ { 2 } , \mathbf { a } \rangle = \langle \ell ^ { 1 } \sqcup \ell ^ { 2 } , \mathbf { a } \rangle .
$$

We denote by $G ( V )$ the set of group-like elements of $T ( ( V ) )$

The group-like property is analogous to the behavior of exponentials: just as $e ^ { x + y } = e ^ { x } e ^ { y }$ transforms addition into multiplication, signatures can be thought of as “exponentials” of paths rather than numbers. The shufle product represents all the ways in which two tensors (say, $\ell _ { 1 }$ and $\ell _ { 2 } )$ can be combined while preserving their internal order. The group-like condition says that evaluating the shufle is equivalent to evaluating each tensor separately and multiplying the results. We now make this idea precise.

Proposition 3.12. Let $X : [ 0 , T ] V$ be a continuous path of bounded variation. Then, the signature of X satisfies the group-like property. That is, for every pair $\ell ^ { 1 } , \ell ^ { 2 } \in T ( V )$

$$
\langle \ell ^ { 1 } , S ( X ) _ { 0 , T } \rangle \langle \ell ^ { 2 } , S ( X ) _ { 0 , T } \rangle = \langle \ell ^ { 1 } \sqcup \ell ^ { 2 } , S ( X ) _ { 0 , T } \rangle .
$$

Proof. By linearity, it is enough to prove it for $\ell ^ { 1 } = e _ { I }$ and $\ell ^ { 2 } = e _ { J }$ . Let $n = \left| I \right| + \left| J \right|$ . We will prove the result by induction on n. For $n = 0 .$ , we have $I = J = \emptyset$ and the result holds trivially. Assume that it holds for $n ,$ and let $I = ( i _ { 1 } , \dots , i _ { n + 1 - m } )$ and $J = \left( j _ { 1 } , \ldots , j _ { m } \right)$ . Note first that $\langle \dot { e } _ { I } , S ( X ) _ { 0 , T } \rangle = S ( X ) _ { 0 , T } ^ { I }$ and $\langle \mathrm { e } _ { J } , S ( X ) _ { 0 , T } \rangle = S ( X ) _ { 0 , T } ^ { J }$ . Using integration by parts and the notation for I<sup>′</sup> and J<sup>′</sup> introduced in Definition 3.3, we have

$$
\begin{array} { r l } {  { \langle e _ { I } , S ( X ) _ { 0 , T } \rangle \langle e _ { J } , S ( X ) _ { 0 , T } \rangle } } \\ & { = \int _ { 0 } ^ { T } \langle e _ { J } , S ( X ) _ { 0 , s } \rangle d \langle e _ { I } , S ( X ) _ { 0 , s } \rangle + \int _ { 0 } ^ { T } \langle e _ { I } , S ( X ) _ { 0 , s } \rangle d \langle e _ { J } , S ( X ) _ { 0 , s } \rangle } \\ & { = \int _ { 0 } ^ { T } \langle e _ { I ^ { \prime } } , S ( X ) _ { 0 , s } \rangle \langle e _ { J } , S ( X ) _ { 0 , s } \rangle d X _ { s } ^ { i _ { n + 1 - m } } + \int _ { 0 } ^ { T } \langle e _ { I } , S ( X ) _ { 0 , s } \rangle \langle e _ { J ^ { \prime } } , S ( X ) _ { 0 , s } \rangle d X _ { s } ^ { j _ { m } } . } \end{array}
$$

Using the induction step, it follows that

$$
\begin{array} { l } { { \langle e _ { I } , S ( X ) _ { 0 , T } \rangle \langle e _ { J } , S ( X ) _ { 0 , T } \rangle } } \\ { { \ } } \\ { { \displaystyle = \int _ { 0 } ^ { T } \langle ( e _ { I ^ { \prime } } \shuffle e _ { J } ) , S ( X ) _ { 0 , s } \rangle d X _ { s } ^ { i _ { n + 1 - m } } + \int _ { 0 } ^ { T } \langle ( e _ { I } \shuffle e _ { J ^ { \prime } } ) , S ( X ) _ { 0 , s } \rangle d X _ { s } ^ { j _ { m } } } } \\ { { \displaystyle = \langle ( e _ { I ^ { \prime } } \shuffle e _ { J } ) \otimes e _ { n + 1 - m } , S ( X ) _ { 0 , T } \rangle + \langle ( e _ { I } \shuffle e _ { J ^ { \prime } } ) \otimes e _ { j _ { m } } , S ( X ) _ { 0 , T } \rangle } } \\ { { \displaystyle = \langle ( e _ { I } \shuffle e _ { J } ) , S ( X ) _ { 0 , T } \rangle , } } \end{array}
$$

which concludes the proof.

The function $\langle \cdot , \cdot \rangle$ defined in (3.2) allows us to interpret the elements ℓ of the tensor algebra $T ( V )$ as linear functionals when paired with a signature $S ( X ) _ { 0 , T }$ . If we evaluate two linear functionals $\ell _ { 1 }$ and $\ell _ { 2 }$ separately on the signature $S ( X ) _ { 0 , T }$ and then multiply those two scalar values, the product equals what we get by evaluating the single functional $\ell ^ { \bar { 1 } } \sqcup \ell ^ { 2 }$ on $S ( X ) _ { 0 , T }$

If we consider the path $X : [ 0 , 5 ] \mathbb { R } ^ { 2 }$ from Example 3.9, we have

$$
S ( X ) _ { 0 , 5 } ^ { 1 2 } = \int _ { 0 } ^ { 5 } \int _ { 0 } ^ { t } d X _ { s } ^ { 1 } d X _ { t } ^ { 2 } \quad \mathrm { a n d } \quad S ( X ) _ { 0 , 5 } ^ { 1 } = \int _ { 0 } ^ { 5 } d X _ { t } ^ { 1 } .
$$

The multiplication of these two iterated integrals would be a polynomial in the components of the signature $S ( X ) _ { 0 , 5 }$ . The above proposition says that such a nonlinear expression can still be treated in a linear way provided we use the shufle product. With the slight abuse of notation we used in Example 3.5, we see that $e _ { 1 2 }$  $e _ { 1 } = e _ { 1 2 1 } + 2 e _ { 1 1 2 }$ . Therefore, the product of the iterated integrals $S ( X ) _ { 0 , 5 } ^ { 1 2 }$ and $S ( X ) _ { 0 , 5 } ^ { 1 }$ can be expressed as a linear combination of

$$
S ( X ) _ { 0 , 5 } ^ { 1 2 1 } = \int _ { 0 } ^ { 5 } \int _ { 0 } ^ { t } \int _ { 0 } ^ { s } d X _ { u } ^ { 1 } d X _ { s } ^ { 2 } d X _ { t } ^ { 1 } \quad \mathrm { a n d } \quad S ( X ) _ { 0 , 5 } ^ { 1 1 2 } = \int _ { 0 } ^ { 5 } \int _ { 0 } ^ { t } \int _ { 0 } ^ { s } d X _ { u } ^ { 1 } d X _ { s } ^ { 1 } d X _ { t } ^ { 2 } .
$$

<!-- page: 14 -->

In other words, products of iterated integrals (polynomials in the elements of the signature) can be written as linear combinations of higher-order integrals. The fact that the space of polynomials on signatures can be linearly organized via the shufle product will be used in Section 4. The price to pay for linearity is the higher dimension of the tensor space in which the linear expression lives, which happens to be the space in which numerical computations will be carried out.

## 3.3 Rough Paths

So far we have developed the signature for continuous paths of bounded variation. By Young’s integration theory, this construction extends to continuous paths of finite p-variation for $p < 2$ However, the stochastic processes most commonly used in finance—such as Brownian motion or fractional Brownian motion with small Hurst indexes—do not satisfy this condition. We therefore need to find a way to extend the signature to a broader class of paths with more irregular behavior.

This extension is achieved by lifting the paths. Intuitively, lifting refers to the process of enriching a path with additional information (namely, its iterated integrals). For smooth paths this yields the signature, while for more irregular paths this is done abstractly.

Let $X : [ 0 , T ] V$ be a path of finite p-variation for some $p \geq 2$ , so that X may be too irregular for classical iterated integrals to exist. To overcome this dificulty, we define a new object called a rough path

$$
\mathbf { X } _ { s , t } = \left( \mathbb { X } _ { s , t } ^ { 1 } , \mathbb { X } _ { s , t } ^ { 2 } , \mathbb { X } _ { s , t } ^ { 3 } , \ldots , \mathbb { X } _ { s , t } ^ { \lfloor p \rfloor } \right) ,
$$

where $\mathbb { X } _ { s , t } ^ { 1 } = X _ { t } - X _ { s }$ is the increment of the original path and each $\mathbb { X } _ { s , t } ^ { k }$ is an approximation to the k-th order iterated integral

$$
\mathbb { X } _ { s , t } ^ { k } \approx \int _ { s < u _ { 1 } < \dots < u _ { k } < t } d X _ { u _ { 1 } } \otimes \dots \otimes d X _ { u _ { k } }
$$

At this level of intuition, approximation means that the $\mathbb { X } ^ { k }$ serve as proxies for the true iterated integrals, satisfying certain algebraic properties and appropriate p-variation bounds. This lifted structure enables us to define integration against X even when classical approaches such as Riemann–Stieltjes or Young integration break down. In the remainder of this section we formalize these ideas.

Definition 3.13 (Truncated Tensor Algebra). Let $N \in { \mathbb { N } }$ . We define the truncated tensor algebra of order N over V as

$$
\begin{array} { r } { T ^ { N } ( V ) = \{ \mathbf { a } = ( a _ { 0 } , a _ { 1 } , \dots ) \in T ( ( V ) ) ; \ a _ { k } = 0 \ \forall k > N \} . } \end{array}
$$

The projection map $\pi _ { \leq N } : T ( ( V ) ) \to T ^ { N } ( V )$ is defined as

$$
\pi _ { \leq N } ( ( a _ { i } ) _ { i = 0 } ^ { \infty } ) = ( a _ { i } ) _ { i = 0 } ^ { N } .
$$

For any $\mathbf { a } , \mathbf { b } \in T ^ { N } ( V )$ , we define the truncated tensor product in $T ^ { N } ( V )$ as

$$
{ \mathbf { a } } \otimes _ { \leq N } { \mathbf { b } } = \pi _ { \leq N } ( { \mathbf { a } } \otimes { \mathbf { b } } ) .
$$

When dealing with elements of $T ^ { N } ( V )$ , if there is no risk of confusion we will generally use $\otimes$ to denote $\bigotimes _ { \mathbf { \lambda } \leq N }$

Let $X : [ 0 , T ] V$ be a continuous path of bounded variation and $\Delta _ { T } = \{ ( s , t ) \in [ 0 , T ] ^ { 2 } ; s \leq t \}$ The truncated signature of order N of a path X can therefore be defined as

$$
\begin{array} { c } { { S ( X ) ^ { \leq N } : \Delta _ { T }  T ^ { N } ( V ) } } \\ { { ( s , t ) \mapsto \pi _ { \leq N } ( S ( X ) _ { s , t } ) . } } \end{array}
$$

We write $S ( X ) ^ { \leq N } ( s , t ) = S ( X ) { \overset { \leq N } { s , t } }$

<!-- page: 15 -->

A slight modification in the proof of Chen’s identity shows that, for all $0 \leq s < u < t \leq T$

$$
\begin{array} { r } { S ( X ) _ { s , t } ^ { \le N } = S ( X ) _ { s , u } ^ { \le N } \otimes S ( X ) _ { u , t } ^ { \le N } . } \end{array}\tag{3.4}
$$

We say that $S ( X ) ^ { \leq N }$ is multiplicative. The following definition extends the multiplicative property to a more general setting.

Definition 3.14 (Multiplicative functional). For $N \in \mathbb { N } _ { : }$ let $\mathbf { X } : \Delta _ { T } \to T ^ { N } ( V )$ be a continuous map and denote $\mathbf { X } ( s , t ) = \mathbf { X } _ { s , t } .$ . Since $\mathbf { X } _ { s , t } \in T ^ { N } ( V )$ , we can write $\mathbf { X } _ { s , t } = ( \mathbf { X } _ { s , t } ^ { 0 } , \mathbf { X } _ { s , t } ^ { 1 } , \ldots , \mathbf { X } _ { s , t } ^ { N } )$ where $\mathbf { X } _ { s , t } ^ { k } \in V ^ { \otimes k }$ for each k. We say that X is a multiplicative functional of degree N in V if, for every $( s , t ) \in \Delta _ { T }$ , we have $\mathbf { X } _ { s , t } ^ { 0 } : = 1$ and

$$
\mathbf { X } _ { s , t } = \mathbf { X } _ { s , u } \otimes \mathbf { X } _ { u , t }\tag{3.5}
$$

for all $s \leq u \leq t .$

By extension, we also refer to (3.5) as Chen’s identity. Consider the case when $N = 1$ . Chen’s identity says that

$$
\begin{array} { r } { ( 1 , \mathbf { X } _ { s , t } ^ { 1 } ) = ( 1 , \mathbf { X } _ { s , u } ^ { 1 } ) \otimes ( 1 , \mathbf { X } _ { u , t } ^ { 1 } ) = ( 1 , \mathbf { X } _ { s , u } ^ { 1 } + \mathbf { X } _ { u , t } ^ { 1 } ) , } \end{array}
$$

which implies $\mathbf { X } _ { s , t } ^ { 1 } = \mathbf { X } _ { s , u } ^ { 1 } + \mathbf { X } _ { u , t } ^ { 1 }$ . The type of functionals that satisfy this property are called additive functionals. Additivity provides an important step toward the definition of a rough path.

Select an arbitrary constant $v \in V$ and define a path $\psi : [ 0 , T ] \to V$ by

$$
\psi _ { t } : = v + \mathbf { X } _ { 0 , t } ^ { 1 } .
$$

Then, $\psi _ { t } - \psi _ { s } = \mathbf { X } _ { 0 , t } ^ { 1 } - \mathbf { X } _ { 0 , s } ^ { 1 }$ . By additivity (Chen’s identity at level 1), this equals $\mathbf { X } _ { s , t } ^ { 1 }$ . That is,

$$
\mathbf { X } _ { s , t } ^ { 1 } = { \psi } _ { t } - { \psi } _ { s } .
$$

In other words, a multiplicative functional of order 1 in V is equivalent to the increment map of a path $\psi : [ 0 , T ] \to V$ , unique up to an additive constant.

Up to now, we started from a continuous path of finite variation $X : [ 0 , T ] V$ and showed that its truncated signature—an element of the tensor algebra $T ^ { N } ( V )$ —satisfies the multiplicative identity (3.4). We now reverse this perspective: instead of constructing the signature from a classical path, we assume the algebraic structure of a signature and study its properties as a path taking values in the tensor algebra $T ^ { N } ( V )$

We have already seen that the first level of a multiplicative functional is given by the increments of a path in V , just as the first level of the signature of a path corresponds to its own increments. We can now generalize this.

Lemma 3.15. Let $\mathbf { X } , \mathbf { Y } : \Delta _ { T } T ^ { N } ( V )$ be two multiplicative functionals of order N that agree on the first $N - 1$ levels. Then, the function $\Psi : \Delta _ { T } V ^ { \otimes N }$ defined by $\Psi _ { s , t } = \mathbf { X } _ { s , t } ^ { N } - \mathbf { Y } _ { s , t } ^ { N }$ is additive, that is, $\Psi _ { s , t } = \Psi _ { s , u } + \Psi _ { u , t }$ , for all $s \leq u \leq t$

Proof. Due to the multiplicative property, $\mathbf { X } _ { s , t } = \mathbf { X } _ { s , u } \otimes \mathbf { X } _ { u , t }$ for all $s \leq u \leq t .$ . Consider the N-th level component of the functionals in each side of the last equality. In the case of the $N { \mathrm { - t h } }$ level component of $\mathbf { X } _ { s , u } \otimes \mathbf { X } _ { u , t }$ , we separate the summands that only include elements of $V ^ { \otimes N }$ from the rest:

$$
\mathbf { X } _ { s , t } ^ { N } = \mathbf { X } _ { s , u } ^ { N } + \mathbf { X } _ { u , t } ^ { N } + \sum _ { i + j = N - 1 } \mathbf { X } _ { s , u } ^ { i } \otimes \mathbf { X } _ { u , t } ^ { j } ,
$$

where the elements of the summation are tensor products of elements from lower levels $( i , j \geq 0 )$ An analogous expression holds for $\mathbf { Y } _ { s , t } ^ { N }$ . Then,

$$
\Psi _ { s , t } = \mathbf { X } _ { s , t } ^ { N } - \mathbf { Y } _ { s , t } ^ { N } = \Psi _ { s , u } + \Psi _ { u , t } + \sum _ { i + j = N - 1 } \left( \mathbf { X } _ { s , u } ^ { i } \otimes \mathbf { X } _ { u , t } ^ { j } - \mathbf { Y } _ { s , u } ^ { i } \otimes \mathbf { Y } _ { u , t } ^ { j } \right) .
$$

As X and Y agree on the first $N - 1$ levels, the last term on the right-hand side is zero, yielding $\Psi _ { s , t } = \Psi _ { s , u } + \Psi _ { u , t }$ , which is what we needed to prove. □

<!-- page: 16 -->

Lemma 3.16. Let $\mathbf { X } : \Delta _ { T } \to T ^ { N } ( V )$ be a multiplicative functional of order N in $V$ and let $\Psi : \Delta _ { T } \to V ^ { \otimes N }$ be an additive function. Then $\mathbf { X } + \boldsymbol { \Psi }$ is also a multiplicative functional.

Proof. We need to show that, for all $s \leq u \leq t .$

$$
{ \bf X } _ { s , t } + \Psi _ { s , t } = ( { \bf X } _ { s , u } + \Psi _ { s , u } ) \otimes ( { \bf X } _ { u , t } + \Psi _ { u , t } ) .
$$

The right hand side of the above expression can be expanded as

$$
\mathbf { X } _ { s , u } \otimes \mathbf { X } _ { u , t } + \mathbf { X } _ { s , u } \otimes \boldsymbol { \Psi } _ { u , t } + \boldsymbol { \Psi } _ { s , u } \otimes \mathbf { X } _ { u , t } + \boldsymbol { \Psi } _ { s , u } \otimes \boldsymbol { \Psi } _ { u , t } .
$$

As X is multiplicative, $\mathbf { X } _ { s , u } \otimes \mathbf { X } _ { u , t } = \mathbf { X } _ { s , t }$ . We now prove that

$$
{ \bf X } _ { s , u } \otimes \Psi _ { u , t } + \Psi _ { s , u } \otimes { \bf X } _ { u , t } + \Psi _ { s , u } \otimes \Psi _ { u , t } = \Psi _ { s , t } .\tag{3.6}
$$

Note that Ψ takes values in $V ^ { \otimes N }$ , which is the highest order component in the truncated tensor algebra $T ^ { N } ( V )$ Therefore, when tensoring $\mathbf { X } _ { s , u }$ with $\Psi _ { u , t }$ , the only element in $V ^ { \otimes N }$ will be precisely $\Psi _ { u , t }$ . That is, ${ \bf X } _ { s , u } \otimes _ { \leq N } \Psi _ { u , t } = \Psi _ { u , t } .$ . More formally, assume that $\begin{array} { r } { \mathbf { X } _ { s , u } = \sum _ { | J | \leq N } b _ { J } e _ { J } } \end{array}$ for some coeficients $b _ { J }$ , and let $I = ( 0 , \ldots , 0 , 1 )$ with $| I | = N$ . Then, as $b _ { \emptyset } = 1$

$$
\mathbf { X } _ { s , u } \otimes \Psi _ { u , t } = \left( \sum _ { | J | \leq N } b _ { J } e _ { J } \right) \otimes \Psi _ { u , t } e _ { I } = 1 \Psi _ { u , t } ( e _ { \theta } \otimes e _ { I } ) + \left( \sum _ { | J | > N } c _ { J } e _ { J } \right) ,
$$

for some coeficients $c _ { J } .$ , with $| J | > N$ . We therefore have ${ \bf X } _ { s , u } \otimes _ { \leq N } \Psi _ { u , t } = \Psi _ { u , t }$ . The same reasoning applies to show that $\Psi _ { s , u } \otimes _ { \leq N } \mathbf { X } _ { u , t } = \Psi _ { s , u }$ . For the last term in left-hand side of (3.6), let I be as above and $J = ( 0 , \ldots , 0 , 1 )$ with $| J | = N$ . Then,

$$
\Psi _ { s , u } e _ { I } \otimes \Psi _ { u , t } e _ { J } = \Psi _ { s , u } \Psi _ { u , t } e _ { I } \otimes e _ { J } .
$$

As $e _ { I } \otimes e _ { J } \in V ^ { \otimes 2 N }$ , we have $\Psi _ { s , u } \otimes _ { \leq N } \Psi _ { u , t } = 0$ . Writing ⊗ for $\bigotimes { } _ { < N }$ , it follows that

$$
\mathbf { X } _ { s , u } \otimes \boldsymbol { \Psi } _ { u , t } + \boldsymbol { \Psi } _ { s , u } \otimes \mathbf { X } _ { u , t } + \boldsymbol { \Psi } _ { s , u } \otimes \boldsymbol { \Psi } _ { u , t } = \boldsymbol { \Psi } _ { s , u } + \boldsymbol { \Psi } _ { u , t } = \boldsymbol { \Psi } _ { s , t } ,
$$

where the last equation follows from the additivity assumption. This completes the proof.

We now combine these results with the p-variation bounds on the functionals. Recall that a path $X : [ 0 , T ] V$ is α-Hölder continuous ${ \mathrm { i f } } ,$ for $s \leq t \in [ 0 , T ]$ and $0 < \alpha \leq 1$ 7

$$
| X _ { t } - X _ { s } | \leq C | t - s | ^ { \alpha }
$$

for some constant $C > 0$ . If X is α-Hölder continuous, then it has finite 1/α-variation. The converse does not generally hold. However, if X is a continuous path with finite p-variation, there exists a continuous, increasing reparametrization τ such that $X \circ \tau$ is $1 / p \ / -$ -Hölder continuous.

For a continuous functional $\mathbf { X } : \Delta _ { T } \to T ^ { N } ( V )$ , we define

$$
| | \mathbf { X } | | _ { p \cdot \mathrm { v a r } } : = \operatorname* { m a x } _ { 1 \leq k \leq N } \operatorname* { s u p } _ { \mathcal { D } } \left( \sum _ { t _ { i } \in \mathcal { D } } | | \pi _ { k } ( \mathbf { X } _ { t _ { i } , t _ { i + 1 } } ) | | _ { V ^ { \otimes k } } ^ { p / k } \right) ^ { k / p } ,\tag{3.7}
$$

where the sup is taken over all the partitions ${ \mathcal { D } } _ { [ 0 , T ] } . \ { \mathrm { ~ I f ~ } } \ | | { \mathbf { X } } | | _ { p \cdot { \mathrm { v a r } } } < \infty .$ , the functional X is said to have finite p-variation. The p-variation distance between two functionals X and Y of finite p-variation is defined as

$$
d _ { p \cdot \mathrm { v a r } } ( \mathbf { X } , \mathbf { Y } ) : = | | \mathbf { X } - \mathbf { Y } | | _ { p \cdot \mathrm { v a r } } .\tag{3.8}
$$

Assume that the multiplicative functionals $\mathbf { X } , \mathbf { Y } : \Delta _ { T } \to T ^ { N } ( V )$ have finite p-variation and agree on the first $N - 1$ levels. Then, by Lemma 3.15, the N-level diference,

$$
\Psi _ { s , t } = \mathbf { X } _ { s , t } ^ { N } - \mathbf { Y } _ { s , t } ^ { N }
$$

<!-- page: 17 -->

defines an additive function on $\Delta _ { T }$ . For a fixed $v \in V ^ { \otimes N }$ , Ψ induces a path $\psi : [ 0 , T ] \to V ^ { \otimes N }$ by

$$
\psi _ { t } = v + \Psi _ { 0 , t } .
$$

Then, by additivity of $\Psi$

$$
\Psi _ { s , t } = \psi _ { t } - \psi _ { s }
$$

for any $s \leq t .$ . Additivity implies that we can think of Ψ as a function that comes from the increments of a path.

As X and Y have finite p-variation, the diference $\Psi$ at level N inherits finite $p / N .$ -variation. This follows directly from the structure of the p-variation norm (3.7), where the N-th level contributes with exponent $p / N$

It follows that there exists a continuous and increasing reparametrization τ of $[ 0 , T ]$ such that the reparametrized path $\Psi \circ \tau$ (defined by $\Psi _ { \tau ( s ) , \tau ( t ) } = \psi _ { \tau ( t ) } - \psi _ { \tau ( s ) } )$ is $N / p$ -Hölder continuous. This means that ψ is regular enough to be treated as a genuine path in $V ^ { \otimes { \bar { N } } }$ , and that its increments $\Psi _ { s , t } = \psi _ { t } - \psi _ { s }$ , are well-behaved. Regularity allows us to reinterpret $\Psi$ as a “missing” top-level component that can be added to Y to produce a new functional

$$
\begin{array} { r } { \mathbf { Z } _ { s , t } : = \mathbf { Y } _ { s , t } + \boldsymbol { \Psi } _ { s , t } , } \end{array}
$$

which, by Lemma 3.16, is multiplicative (and of order N).

Now, suppose that $N / p > 1$ . Then, as $\psi \circ \tau$ is Hölder continuous with exponent greater than 1, it must be constant. This implies that $\Psi _ { s , t } = \psi _ { t } - \psi _ { s } = 0$ for all $s , t ,$ so the top level of X and Y must coincide:

$$
\mathbf { X } ^ { N } = \mathbf { Y } ^ { N } .
$$

Therefore, any two multiplicative functionals of finite p-variation that agree up to level $\lfloor p \rfloor$ must in fact agree entirely. This suggests that the levels up to $\lfloor p \rfloor$ determine the rest.

This observation raises the converse question: If a multiplicative functional X is defined only up to level N, with finite p-variation and $N \geq \lfloor p \rfloor$ , can we extend it to higher levels in a consistent way? That is, can we construct a full multiplicative functional $\mathbf { Y } : \Delta _ { T } \to T ^ { n } ( V )$ with $n > N$ 7 such that Y agrees with X up to level N, and has finite p-variation?

Unlike the previous argument (no two extensions can difer when $N > \lfloor p \rfloor )$ , this one is about existence and uniqueness of such an extension. The following result, proved in Lyons et al. (2007), answers the question afirmatively.

Theorem 3.17 (Extension Theorem). Let $p \geq 1$ be a real number, $N \geq 1$ an integer, and let $\mathbf { X } : \Delta _ { T } \to T ^ { N } ( \dot { V } )$ be a multiplicative functional of degree N with finite p-variation. Suppose that $N \geq \lfloor p \rfloor$ . Then, for every integer $n > N$ , there exists a unique continuous multiplicative functional

$$
\mathbf { Y } : \Delta _ { T } \to T ^ { n } ( V )
$$

such that

1. Y agrees with X up to level N; that is, $\pi _ { \leq N } ( \mathbf { Y } ) = \mathbf { X }$ ;

2. Y has finite p-variation.

Moreover, the map that sends X to its extension Y is continuous with respect to the p-variation metric.

This result highlights that, for a multiplicative functional with finite p-variation, the first ⌊p⌋ levels completely capture all of its information, leading naturally to the next definition.

Definition 3.18 (Rough Path). Let $p \geq 1$ . A p-rough path is a continuous multiplicative functional

$$
\mathbf { X } : \Delta _ { T }  T ^ { \lfloor p \rfloor } ( V )
$$

of degree $\lfloor p \rfloor$ with finite p-variation. The space of p-rough paths is denoted by $\Omega _ { T } ^ { p } ( V )$

<!-- page: 18 -->

What distinguishes rough paths from general multiplicative functionals is that they retain only the minimal number of components necessary to capture all relevant information. In this sense, a rough path can be viewed as a “compressed” version of a multiplicative functional: it contains exactly the levels up to ⌊p⌋, which fully determine the rest under finite p-variation.

So far, we have not explicitly relied on the theory of signatures of bounded variation paths, except to define objects that reflect some of their structural properties. Rough paths form a highly abstract class, while paths of bounded variation are concrete and familiar. It is therefore natura to examine the rough paths that are close to signatures of bounded variation paths, namely, those that arise as limits of such signatures. This leads us to the following definition.

Definition 3.19 (Geometric Rough Paths). A geometric p-rough path is a p-rough path X for which there exists a sequence of paths of bounded variation $( X _ { n } ) _ { n \geq 1 }$ such that

$$
\operatorname* { l i m } _ { n \to \infty } d _ { p \cdot \mathrm { v a r } } ( \mathbf { X } , S ( X _ { n } ) ^ { \leq \lfloor p \rfloor } ) = 0 .
$$

The space of geometric p-rough paths is denoted by $G \Omega _ { T } ^ { p } ( V )$

Recall from Proposition 3.12 that the signature of a bounded variation path satisfies the grouplike property. It follows that each truncated signature $S ( X _ { n } ) ^ { \leq \lfloor p \rfloor }$ takes values in $G ^ { \left\lfloor p \right\rfloor } ( V )$ , the set of group-like elements in the truncated tensor algebra $T ^ { \lfloor p \rfloor } ( V )$

Now, since the group-like property is algebraic and preserved under limits, and the geometric p-rough path X is defined as the limit of such signatures in the p-variation topology, it also takes values in $G ^ { \left\lfloor p \right\rfloor } ( V )$ . Hence, every geometric p-rough path takes values in $G ^ { \left\lfloor p \right\rfloor } ( V )$

Note, however, that the converse does not hold in general: not every p-rough path taking values in $G ^ { \left\lfloor p \right\rfloor } ( V )$ arises as the limit of signatures of bounded variation paths. This distinction motivates the following definition.

Definition 3.20 (Weakly Geometric Rough Paths). A weakly geometric p-rough path is a prough path taking values in $G ^ { \left\lfloor p \right\rfloor } ( V )$ . The space of weakly geometric p-rough paths is denoted by $W G \Omega _ { T } ^ { p } ( V )$

The diference between $G \Omega _ { T } ^ { p } ( V )$ and $W G \Omega _ { T } ^ { p } ( V )$ is subtle and becomes relevant especially when V is infinite-dimensional. It is always the case that

$$
G \Omega _ { T } ^ { p } ( V ) \subset W G \Omega _ { T } ^ { p } ( V ) \subset \Omega _ { T } ^ { p } ( V ) .
$$

Example 3.21 (Brownian Motion). As we often work with Brownian motion in the context of signature-based models, it is worth pausing to examine its signature and its interpretation as a rough path.

Let $B : [ 0 , T ] \mathbb { R }$ be a standard Brownian motion, and assume that stochastic integrals with respect to B are defined in the Itô sense. Since Brownian motion has finite $p \mathrm { - }$ -variation for any $p > 2$ , we can attempt to lift it to a p-rough path of degree $N = 2$ . The natural candidate for such a lift is the stochastic Itô signature:

$$
\begin{array} { l } { { S ^ { \mathrm { I t } \displaystyle \delta } ( B ) _ { s , t } ^ { \le 2 } = \left( 1 , \displaystyle \int _ { s } ^ { t } d B _ { u } , \displaystyle \int _ { s } ^ { t } \displaystyle \int _ { s } ^ { u } d B _ { r } d B _ { u } \right) } } \\ { { { } ~ = \left( 1 , B _ { t } - B _ { s } , \displaystyle \int _ { s } ^ { t } ( B _ { u } - B _ { s } ) d B _ { u } \right) } } \\ { { { } ~ = \left( 1 , B _ { t } - B _ { s } , \displaystyle \frac { 1 } { 2 } ( B _ { t } - B _ { s } ) ^ { 2 } - \displaystyle \frac { 1 } { 2 } ( t - s ) \right) , } } \end{array}
$$

where the last identity follows from $\mathrm { I t } \hat { \mathrm { O } } ^ { \ ' } \mathrm { s }$ formula, using $\begin{array} { r } { B _ { t } ^ { 2 } - B _ { s } ^ { 2 } = 2 \int _ { s } ^ { t } B _ { u } d B _ { u } + ( t - s ) } \end{array}$

Now consider the shufle identity. Since $\boldsymbol { e } _ { 1 } \sqcup \boldsymbol { e } _ { 1 } = 2 \boldsymbol { e } _ { 1 } \otimes \boldsymbol { e } _ { 1 }$ , we have:

$$
\langle e _ { 1 } , S ^ { \mathrm { I t } \hat { \sigma } } ( B ) _ { s , t } ^ { \le 2 } \rangle ^ { 2 } = ( B _ { t } - B _ { s } ) ^ { 2 } ,
$$

<!-- page: 19 -->

but

$$
\langle e _ { 1 } \sqcup e _ { 1 } , S ^ { \mathrm { I t } \delta } ( B ) _ { s , t } ^ { \leq 2 } \rangle = 2 \cdot \left( \frac { 1 } { 2 } ( B _ { t } - B _ { s } ) ^ { 2 } - \frac { 1 } { 2 } ( t - s ) \right) = ( B _ { t } - B _ { s } ) ^ { 2 } - ( t - s ) .
$$

It follows that $S ^ { \mathrm { I t } \hat { \mathrm { o } } } ( B ) _ { s , t } ^ { \leq 2 }$ is not group-like, which means that Itô integrals do not lead to weakly geometric rough paths. However, if we use Stratonovich integration, we obtain:

$$
\begin{array} { c } { { S ^ { \circ } ( B ) _ { s , t } ^ { \leq 2 } = \left( 1 , \displaystyle \int _ { s } ^ { t } \circ d B _ { u } , \displaystyle \int _ { s } ^ { t } \int _ { s } ^ { u } \circ d B _ { r } \circ d B _ { u } \right) } } \\ { { = \left( 1 , B _ { t } - B _ { s } , \displaystyle \frac { 1 } { 2 } ( B _ { t } - B _ { s } ) ^ { 2 } \right) . } } \end{array}
$$

As $\langle e _ { 1 } , S ^ { \circ } ( B ) _ { s , t } ^ { \leq 2 } \rangle ^ { 2 }$ matches

$$
\big \langle e _ { 1 } \sqcup e _ { 1 } , S ^ { \circ } ( B ) _ { s , t } ^ { \leq 2 } \big \rangle = 2 \cdot \frac { 1 } { 2 } ( B _ { t } - B _ { s } ) ^ { 2 } = ( B _ { t } - B _ { s } ) ^ { 2 } ,
$$

the Stratonovich signature is group-like and defines a weakly geometric p-rough path for any $p > 2$

Even though the Itô signature is not group-like, we are not at a dead end. There are at least two standard approaches. One is to construct a weakly geometric rough path lift of Brownian motion by defining the second level as the Stratonovich iterated integral, i.e., work with

$$
\mathbf { B } _ { s , t } : = \left( 1 , B _ { t } - B _ { s } , \int _ { s } ^ { t } ( B _ { u } - B _ { s } ) \circ d B _ { u } \right) ,
$$

which is group-like. This is known as the Stratonovich lift of Brownian motion and is the standard choice in rough path theory.

Alternatively, one could define a non-geometric rough path using the Itô integral, but the path would lie outside the standard tensor algebra and would need to incorporate Itô correction terms. This gives rise to branched or generalized rough paths (see Bruned et al. (2019)).

In general, the Stratonovich lift is preferred because it aligns with the algebraic structure of signatures (the group-like property) and allows for a direct interpretation of rough integrals as limits of classical Riemann–Stieltjes approximations. For one-dimensional paths, the following result shows that the situation is simpler.

Lemma 3.22. Let $p \geq 1$ and let $X : [ 0 , T ] \mathbb { R }$ be a continuous path of finite p-variation. Then there exists a canonical lift to a weakly geometric p-rough path, given by

$$
\mathbf { X } _ { s , t } = \left( 1 , X _ { t } - X _ { s } , { \frac { ( X _ { t } - X _ { s } ) ^ { 2 } } { 2 ! } } , \ldots , { \frac { ( X _ { t } - X _ { s } ) ^ { \lfloor p \rfloor } } { \lfloor p \rfloor ! } } \right) .
$$

To show that this expression defines a valid lift, note first that the right-hand side is the truncated exponential in the tensor algebra

$$
\mathrm { e x p } _ { \mathbb { S } } ^ { \leq \lfloor p \rfloor } ( X _ { t } - X _ { s } ) = \left( 1 , X _ { t } - X _ { s } , { \frac { ( X _ { t } - X _ { s } ) ^ { 2 } } { 2 ! } } , \ldots , { \frac { ( X _ { t } - X _ { s } ) ^ { \lfloor p \rfloor } } { \lfloor p \rfloor ! } } \right) ,
$$

which is known to satisfy the Chen identity. We use the notation $\exp _ { \otimes }$ to indicate that the exponential is taken in the tensor algebra.

Since X has finite p-variation and each level k is a smooth function of the increment $X _ { t } - X _ { s } ,$ the k-th level has finite p/k-variation. Hence, the full lift X has finite p-variation in the sense of (3.7), and defines a weakly geometric p-rough path.

In particular, for a one-dimensional Brownian motion $B : [ 0 , T ] \mathbb { R }$ , the path

$$
\mathbf { B } _ { s , t } : = \left( 1 , B _ { t } - B _ { s } , \frac { 1 } { 2 } ( B _ { t } - B _ { s } ) ^ { 2 } \right)
$$

defines a weakly geometric p-rough path for any $p > 2$ . This Stratonovich lift of Brownian motion corresponds to the first two levels of the Stratonovich signature.

<!-- page: 20 -->

Remark 3.23. More generally, any continuous semimartingale $S = A + M$ , where M is a continuous local martingale and A is a continuous path of bounded variation on compact intervals, admits a canonical weakly geometric rough path lift (in the Stratonovich sense); see Chapter 14 of Friz and Victoir (2010). The intuition is that the roughness of S is driven by the martingale component M, while the bounded variation part A can be handled using classical integration. The construction of the lift relies on probabilistic estimates, in particular the Burkholder-Davis-Gundy inequality and properties of the quadratic variation.

## 3.4 Time-Augmented Rough Paths

Recall that a lifted path refers to extending a base path $X : [ 0 , T ] V$ to a rough path $\mathbf { X } : \Delta _ { T } \to T ^ { N } ( V )$ . We now proceed to augment X with a time coordinate. Specifically, we define ${ \hat { X } } : [ 0 , T ] \to \mathbb { R } \oplus V$ by

$$
{ \hat { X } } _ { t } : = ( t , X _ { t } ) .
$$

At first glance, this change may appear superficial, but it has important consequences that we discuss at the end of this section. The following proposition says that time augmentation preserves important analytic and algebraic properties, such as admitting a lift to a weakly geometric p-rough path.

Proposition 3.24. Let $X : [ 0 , T ] V$ be a continuous path that admits a weakly geometric p-rough path lift $\mathbf { X } \in W G \Omega _ { T } ^ { p } ( \dot { V } )$ . Define the time-augmented path ${ \hat { X } } : [ 0 , T ] \to \mathbb { R } \oplus V$ by

$$
{ \hat { X } } _ { t } : = ( t , X _ { t } ) .
$$

Then $\hat { X }$ also admits a weakly geometric p-rough path lift $\hat { \mathbf { X } } \in W G \Omega _ { T } ^ { p } ( \mathbb { R } \oplus V )$

Proof. We treat $\hat { X }$ as a path in $\mathbb { R } ^ { d + 1 }$ , where the first coordinate is time and the remaining ones are given by X. We define the lifted path $\hat { \bf X }$ inductively over multi-indices $I = ( i _ { 1 } , \ldots , i _ { n } )$ ∈ $\{ 0 , 1 , \ldots , d \} ^ { n }$ , where $i _ { k } = 0$ refers to the time component.

For $| I | = 1$ , we set:

$$
\hat { \mathbf { X } } _ { s , t } ^ { ( i ) } : = \left\{ { t - s \atop X _ { t } ^ { i } - X _ { s } ^ { i } } \right. \mathrm { i f } \ i = \{ 1 , \ldots , d \} .
$$

Assume that all levels up to length $\vert I \vert = n - 1$ have been well defined. We now denote by I the n-th level multi-index, $I = ( i _ { 1 } , \ldots , i _ { n } ) \in \{ 0 , 1 , \ldots , d \} ^ { n }$ . The n-level components of the signature are

$$
\langle e _ { I } , \hat { \mathbf { X } } _ { s , t } \rangle = \hat { \mathbf { X } } _ { s , t } ^ { I } .
$$

If all elements of I are nonzero $( i _ { k } \neq 0 , \ \mathrm { f o r } \ i = 1 , \ldots , n )$ , we set

$$
\hat { \mathbf { X } } _ { s , t } ^ { I } : = \mathbf { X } _ { s , t } ^ { I } ,
$$

which is already defined in the original lift. Assume now that not all $i _ { k } \neq 0$ . Using the shufle product introduced in Definition 3.3, we have

$$
e _ { I } = e _ { I ^ { \prime } } \sqcup e _ { i _ { n } } - ( e _ { I ^ { \prime \prime } } \sqcup e _ { i _ { n } } ) \otimes e _ { i _ { n - 1 } } ,
$$

where $I ^ { \prime }$ has the same meaning as in Definition 3.3, and $I ^ { \prime \prime }$ is defined in an analogous way. We then have

$$
\begin{array} { r l } & { \langle e _ { I } , \hat { \mathbf { X } } _ { s , t } \rangle = \langle e _ { I ^ { \prime } } \sqcup e _ { i _ { n } } - \left( e _ { I ^ { \prime \prime } } \sqcup e _ { i _ { n } } \right) \otimes e _ { i _ { n - 1 } } , \hat { \mathbf { X } } _ { s , t } \rangle } \\ & { \qquad = \langle e _ { I ^ { \prime } } \sqcup e _ { i _ { n } } , \hat { \mathbf { X } } _ { s , t } \rangle - \langle \left( e _ { I ^ { \prime \prime } } \sqcup e _ { i _ { n } } \right) \otimes e _ { i _ { n - 1 } } , \hat { \mathbf { X } } _ { s , t } \rangle } \\ & { \qquad = \langle e _ { I ^ { \prime } } , \hat { \mathbf { X } } _ { s , t } \rangle \langle e _ { i _ { n } } , \hat { \mathbf { X } } _ { s , t } \rangle - \langle \left( e _ { I ^ { \prime \prime } } \sqcup e _ { i _ { n } } \right) \otimes e _ { i _ { n - 1 } } , \hat { \mathbf { X } } _ { s , t } \rangle . } \end{array}\tag{3.9}
$$

<!-- page: 21 -->

As $| I ^ { \prime } | = n - 1$ and $| ( i _ { n } ) | = 1$ , it follows from the induction step that the terms $\langle e _ { I ^ { \prime } } , \hat { \mathbf { X } } _ { s , t } \rangle$ and $\langle e _ { i _ { n } } , \hat { \mathbf { X } } _ { s , t } \rangle$ are well defined. If $i _ { n - 1 } = 0$ , define

$$
\langle \left( e _ { I ^ { \prime \prime } } \shuffle \sqcup e _ { i _ { n } } \right) \otimes e _ { i _ { n - 1 } } , \hat { \mathbf { X } } _ { s , t } \rangle : = \int _ { s } ^ { t } \langle e _ { I ^ { \prime \prime } } \shuffle \sqcup e _ { i _ { n } } , \hat { \mathbf { X } } _ { s , u } \rangle d u ,
$$

where the integral is well-defined as a Young integral because X is a p-rough path and $q = 1$ for time, so that $1 / p + 1 / q > 1$ is always satisfied. $\mathrm { ~ I f ~ } i _ { n - 1 } \neq 0$ , using the shufle product again we get:

$$
\left( e _ { I ^ { \prime \prime } } \shuffle \sqcup e _ { i _ { n } } \right) \otimes e _ { i _ { n - 1 } } = e _ { I ^ { \prime \prime } } \shuffle \sqcup \left( e _ { i _ { n } } \otimes e _ { i _ { n - 1 } } \right) - \left( e _ { I ^ { \prime \prime \prime } } \shuffle \sqcup \left( e _ { i _ { n } } \otimes e _ { i _ { n - 1 } } \right) \right) \otimes e _ { i _ { n - 2 } } .
$$

Therefore,

$$
\begin{array} { r l } & { \langle \left( e _ { I ^ { \prime \prime } } \shuffle e _ { i _ { n } } \right) \otimes e _ { i _ { n - 1 } } , \hat { \mathbf { X } } _ { s , t } \rangle } \\ & { = \langle e _ { I ^ { \prime \prime } } , \hat { \mathbf { X } } _ { s , t } \rangle \langle e _ { i _ { n } } \otimes e _ { i _ { n - 1 } } , \hat { \mathbf { X } } _ { s , t } \rangle - \langle \left( e _ { I ^ { \prime \prime \prime } } \shuffle \amalg \left( e _ { i _ { n } } \otimes e _ { i _ { n - 1 } } \right) \right) \otimes e _ { i _ { n - 2 } } , \hat { \mathbf { X } } _ { s , t } \rangle , } \end{array}\tag{3.10}
$$

where the first term on the right hand side is well defined because of the induction step. If $i _ { n - 2 } = 0$ , we define the second term on the right hand side as

$$
\langle ( e _ { I ^ { \prime \prime \prime } } \sqcup ( e _ { i _ { n } } \otimes e _ { i _ { n - 1 } } ) ) \otimes e _ { i _ { n - 2 } } , \hat { \mathbf { X } } _ { s , t } \rangle : = \int _ { s } ^ { t } \langle e _ { I ^ { \prime \prime \prime } } \sqcup ( e _ { i _ { n } } \otimes e _ { i _ { n - 1 } } ) , \hat { \mathbf { X } } _ { s , t } \rangle d u ,
$$

where, as above, the integral is well-defined as a Young integral. If $i _ { n - 2 } \neq 0$ , we apply shufle product identity again to the second term on the right hand side of $\left( 3 . 1 0 \right)$ to obtain a term involving $i _ { n - 3 }$ . We then repeat the process iteratively. □

Remark 3.25. As a way of illustrating the construction above, let $I = \{ i _ { 1 } , i _ { 2 } \} = \{ 0 , 1 \}$ . Since $I ^ { \prime } = \{ 0 \}$ and $I ^ { \prime \prime } = \varnothing$ , we have

$$
\left( e _ { I ^ { \prime \prime } } \sqcup e _ { i _ { n } } \right) \otimes e _ { i _ { n - 1 } } = \left( e _ { \emptyset } \sqcup e _ { i _ { 2 } } \right) \otimes e _ { i _ { 1 } } = e _ { i _ { 2 } } \otimes e _ { i _ { 1 } } = e _ { 1 } \otimes e _ { 0 } .
$$

It follows from (3.9) that

$$
\begin{array} { r } { \langle e _ { \{ 0 , 1 \} } , \hat { \mathbf { X } } _ { s , t } \rangle : = \langle e _ { 0 } , \hat { \mathbf { X } } _ { s , t } \rangle \langle e _ { 1 } , \hat { \mathbf { X } } _ { s , t } \rangle - \langle e _ { 1 } \otimes e _ { 0 } , \hat { \mathbf { X } } _ { s , t } \rangle } \end{array}\tag{3.11}
$$

The left hand side of the above expression is:

$$
\langle e _ { \{ 0 , 1 \} } , \hat { \mathbf { X } } _ { s , t } \rangle = \int _ { s } ^ { t } \int _ { s } ^ { u } d r d X _ { u } = \int _ { s } ^ { t } ( u - s ) d X _ { u } ,
$$

which, integrating by parts, yields

$$
\langle e _ { \{ 0 , 1 \} } , \hat { \mathbf { X } } _ { s , t } \rangle = ( t - s ) ( X _ { t } - X _ { s } ) - \int _ { s } ^ { t } ( X _ { u } - X _ { s } ) d u .\tag{3.12}
$$

The elements of the signature with indexes of length 1 were defined as $\langle e _ { 0 } , \hat { \mathbf { X } } _ { s , t } \rangle : = t - s$ and $\langle e _ { 1 } , \hat { \mathbf { X } } _ { s , t } \rangle : = X _ { t } - X _ { s }$ . Therefore, the right hand side of (3.11) is:

$$
\begin{array} { l } { { \displaystyle \langle e _ { 0 } , \hat { \mathbf { X } } _ { s , t } \rangle \langle e _ { 1 } , \hat { \mathbf { X } } _ { s , t } \rangle - \langle e _ { 1 } \otimes e _ { 0 } , \hat { \mathbf { X } } _ { s , t } \rangle = ( t - s ) ( X _ { t } - X _ { s } ) - \int _ { s } ^ { t } \int _ { s } ^ { u } d X _ { r } d u } } \\ { { \displaystyle \qquad = ( t - s ) ( X _ { t } - X _ { s } ) - \int _ { s } ^ { t } ( X _ { u } - X _ { s } ) d u , } } \end{array}
$$

which is the same as (3.12).

Now that we know that there exists a lift for the time-augmented path $\hat { X } .$ , we define the corresponding space.

Definition 3.26 (Time-Augmented Weakly Geometric Rough Path). A time-augmented weakly geometric p-rough path is a weakly geometric p-rough path $\mathbf { X } \in W G \Omega _ { T } ^ { p } ( \mathbb { R } \oplus V )$ such that

<!-- page: 22 -->

(i) the first level satisfies $\pi _ { 1 } ( { \bf X } _ { s , t } ) = \hat { X } _ { t } - \hat { X } _ { s }$ , where $\hat { X } _ { t } ~ = ~ ( t , X _ { t } )$ for some continuous path $X : [ 0 , T ] V$ that admits a weakly geometric p-rough path $l i f t ;$

(ii) for any I with $\left| I \right| \leq \left\lfloor p \right\rfloor$

$$
\langle e _ { I 0 } , { \bf X } _ { s , t } \rangle = \int _ { s } ^ { t } \langle e _ { I } , { \bf X } _ { s , u } \rangle d u ,
$$

where the integral is a Young integral, and where the notation $e _ { I 0 }$ means appending a 0 (the time component) to the multi-index I.

We denote the space of such paths by $W G \hat { \Omega } _ { T } ^ { p } ( V )$

Remark 3.27. A rough path in $W G \hat { \Omega } _ { T } ^ { p } ( V )$ presupposes the existence of a path $X : [ 0 , T ] \to V ,$ which is augmented to ${ \hat { X } } : [ 0 , T ] \to \mathbb { R } \oplus V$ . This contrasts with the rough paths in $W G \Omega _ { T } ^ { p } ( V )$ which are defined independent of any base path.

Remark 3.28. Being a weakly geometric rough path in R ⊕ V with the correct first level does not automatically guarantee that the component $\langle e _ { I 0 } , { \bf X } _ { s , t } \rangle$ should equal the integral of $\langle e _ { I } , { \bf X } _ { s , u } \rangle$ against the time increment du. This why we need to include condition (ii). The Young integral is well defined since time has bounded variation.

We now briefly discuss the relevance of lifting the augmented path $( t , X _ { t } )$ instead of lifting $X _ { t }$ alone. Let $S ( X )$ denote the signature of a path $X : [ 0 , T ] V$ . It is well known that the map $X \mapsto S ( X )$ is not injective: diferent paths can share the same signature—for example, if they trace out the same image at diferent speeds. Thus, the signature loses information about the timing or parametrization of the path.

Augmenting the path by adding time, that is, lifting $\hat { X } _ { t } : = ( t , X _ { t } ) \in \mathbb { R } \oplus V$ , recovers injectivity. Theorem 3.30 below shows that the time-augmented signature uniquely determines the path, making it more expressive.

Time augmentation allows the signature to distinguish between paths that follow the same geometric shape but evolve at diferent speeds. This distinction is crucial in the context of the universal approximation theorems discussed below: time augmentation ensures that the signature map separates paths in a suficiently rich way to apply approximation results such as the Stone– Weierstrass theorem.

As we will also see below, time augmentation is essential for learning path-dependent functionals in an adapted way. In models where $Y _ { t }$ depends on the past trajectory $( X _ { s } ) _ { s \leq t }$ , incorporating time allows the signature to detect when events occur. Without time, the signature treats two paths with the same shape but diferent timing as indistinguishable—an undesirable feature in many stochastic or temporally sensitive learning tasks.

## 3.5 Signatures of Rough Paths

Let $\mathbf { X } \in \Omega _ { T } ^ { p } ( V )$ be a p-rough path. By the extension theorem, for every integer $N \geq \lfloor p \rfloor$ there exists a unique multiplicative extension of X to degree N with finite p-variation. Since this extension process can be carried out to arbitrarily high degrees, it is natural to define the signature of a p-rough path as its formal infinite extension. This motivates the following definition.

Definition 3.29 (Signature of a Rough Path). Let $\mathbf { X } \in \Omega _ { T } ^ { p } ( V )$ be a p-rough path. The truncated signature of order $N \geq \lfloor p \rfloor$ is defined as the unique extension ofX to level N with finite p-variation, denoted by:

$$
S ( \mathbf { X } ) ^ { \leq N } : = \left( 1 , S ( \mathbf { X } ) ^ { 1 } , \ldots , S ( \mathbf { X } ) ^ { N } \right) \in T ^ { N } ( V ) .
$$

The (full) signature of X is the formal series

$$
S ( \mathbf { X } ) : \Delta _ { T }  T ( ( V ) )
$$

$$
( s , t ) \mapsto S ( \mathbf { X } ) _ { s , t } : = ( 1 , S ( \mathbf { X } ) _ { s , t } ^ { 1 } , \ldots , S ( \mathbf { X } ) _ { s , t } ^ { n } , \ldots ) ,
$$

where $S ( \mathbf { X } ) _ { s , t } ^ { n } \in V ^ { \otimes n }$ denotes the n-th level of the extension.

<!-- page: 23 -->

Let $\mathbf { X } \in W G \Omega _ { T } ^ { p } ( V )$ and $1 < p < q$ . In Friz and Victoir (2010) it is proved that

$$
W G \Omega _ { T } ^ { p } ( V ) \subset G \Omega _ { T } ^ { q } ( V ) .
$$

Therefore, there exists a sequence of bounded variation paths $X ^ { ( n ) }$ such that their truncated signatures of order $\lfloor q \rfloor$ converge to X in the q-variation topology. By Theorem 3.17, the extension map $\mathbf { X } \mapsto S ( \mathbf { X } ) ^ { \leq \lfloor q \rfloor }$ is continuous in the q-variation topology. Since each $S ( X ^ { ( n ) } ) { \overset { < } { = } } \lfloor q \rfloor$ is grouplike, it follows that $S ( \mathbf { X } ) { \stackrel { < } { = } } \lfloor { q } \rfloor$ is group-like as well. Letting $q \to \infty$ , we obtain that the full signature $S ( \mathbf { X } ) \in T ( ( V ) )$ is group-like. That is, for any $\ell ^ { 1 } , \ell ^ { 2 } \in T ( V )$ , we have:

$$
\langle \ell ^ { 1 } , S ( \mathbf { X } ) _ { s , t } \rangle \langle \ell ^ { 2 } , S ( \mathbf { X } ) _ { s , t } \rangle = \langle \ell ^ { 1 } \sqcup \ell ^ { 2 } , S ( \mathbf { X } ) _ { s , t } \rangle .
$$

Note the slight shift in notation that has taken place here. In Section 3.2, we began with a path $X : [ 0 , T ] V$ and constructed its signature, denoted by $S ( X ) : \Delta _ { T } T ( ( V ) )$ . In contrast, we now start with a multiplicative functional $\mathbf { X } : \Delta _ { T } T ^ { \lfloor p \rfloor } ( V )$ , which satisfies specific algebraic and analytic properties (multiplicativity and finite p-variation) that allow it to be uniquely extended to higher levels $N \geq \lfloor p \rfloor$ . We can describe this extension using the diagram:

$$
\begin{array} { c c c c c } { { \mathbf { X } ^ { \lfloor p \rfloor } ( V ) } } & { { \longrightarrow } } & { { \mathbf { X } ^ { N } ( V ) } } & { { \longrightarrow } } & { { \mathbf { X } ^ { \infty } } } \\ { { ( 1 , \mathbf { X } _ { s , t } ^ { 1 } , \ldots , \mathbf { X } _ { s , t } ^ { \lfloor p \rfloor } ) } } & { { \longrightarrow } } & { { ( 1 , \mathbf { X } _ { s , t } ^ { 1 } , \ldots , \mathbf { X } _ { s , t } ^ { N } ) } } & { { \longrightarrow } } & { { ( 1 , \mathbf { X } _ { s , t } ^ { 1 } , \ldots , \mathbf { X } _ { s , t } ^ { n } , \ldots ) } } \end{array}
$$

where we slightly abuse notation in referring to $\mathbf { X } ^ { \infty }$ as the infinite extension of the rough path.

In Definition 3.29, however, we formalized this extension using the signature notation:

$$
\begin{array} { c c c c c } { { \mathbf { X } ^ { \lfloor p \rfloor } ( V ) } } & { { \longrightarrow } } & { { S ( { \mathbf { X } } ) ^ { \leq N } ( V ) } } & { { \longrightarrow } } & { { S ( { \mathbf { X } } ) } } \\ { { ( 1 , { \mathbf { X } } _ { s , t } ^ { 1 } , \dots , { \mathbf { X } } _ { s , t } ^ { \lfloor p \rfloor } ) } } & { { \longrightarrow } } & { { ( 1 , S ( { \mathbf { X } } ) _ { s , t } ^ { 1 } , \dots , S ( { \mathbf { X } } ) _ { s , t } ^ { N } ) } } & { { \longrightarrow } } & { { ( 1 , S ( { \mathbf { X } } ) _ { s , t } ^ { 1 } , \dots , S ( { \mathbf { X } } ) _ { s , t } ^ { n } , \dots ) } } \end{array}
$$

Note carefully that we have not constructed a signature from X. Rather, we started with a multiplicative functional satisfying the group-like property and finite p-variation (a p-rough path), and we uniquely extended it from level $\lfloor p \rfloor$ to higher levels in the (truncated) tensor algebra. This extension is granted by Theorem 3.17. In Definition 3.29, we have simply relabeled this extended functional using the signature notation previously introduced for bounded variation paths.

Although this notation may initially appear inconsistent, it aligns naturally with the classical case where the signature is defined via iterated integrals. This unification of notation allows both settings—bounded variation and rough paths—to be treated within a common framework.

## 3.6 Universal Approximation Theorems

Since the primary role of a rough path X is to serve as a driver for integrals (or diferential equations), the key object of interest is the increment ${ \bf X } _ { s , t }$ rather than the individual value $\mathbf { X } _ { t }$ at a fixed time. But the two viewpoints are equivalent. Given the increments $\mathbf { X } _ { s , t }$ , one can reconstruct a path by defining $\mathbf { X } _ { t } : = \mathbf { X } _ { 0 , t }$ . If the path $\mathbf { X } _ { t } \in T ^ { N } ( V )$ is given, the increments can be recovered by making use of the multiplicative property, namely, $\mathbf { X } _ { s , t } : = \mathbf { X } _ { s } ^ { - 1 } \otimes \mathbf { X } _ { t } .$

In this section, we present three fundamental theorems that enable the application of signatures to the calibration problem. The first one states that the signature (as defined in Definition 3.29) of a time-augmented weakly geometric p-rough path X, evaluated at time $T _ { : }$ uniquely determines X. We use the simplified notation $\mathbf { X } _ { t } : = \mathbf { X } _ { 0 , t }$

Theorem 3.30 (Uniqueness of the Signature). Let X, $\mathbf { Y } \in W G \hat { \Omega } _ { T } ^ { p } ( V )$ . Then,

$$
S ( \mathbf { X } ) _ { T } = S ( \mathbf { Y } ) _ { T } \iff \forall t \in [ 0 , T ] , \ \mathbf { X } _ { t } = \mathbf { Y } _ { t } .
$$

Proof. Note first that $\mathbf { X } : \Delta _ { T } \to T ^ { \lfloor p \rfloor } ( \mathbb { R } \oplus V )$ , while $S ( \mathbf { X } ) : \Delta _ { T } \to T ( ( \mathbb { R } \oplus V ) )$ . If $\mathbf X _ { t } = \mathbf Y _ { t }$ for all $t \in [ 0 , T ]$ , it must be that ${ \bf X } _ { T } = { \bf Y } _ { T }$ . By the extension theorem, $S ( \mathbf { X } ) _ { T } = S ( \mathbf { Y } ) _ { T }$

<!-- page: 24 -->

Reciprocally, assume $S ( \mathbf { X } ) _ { T } = S ( \mathbf { Y } ) _ { T }$ . Since X, $\mathbf { Y } \in W G \hat { \Omega } _ { T } ^ { p } ( V )$ and both coincide with their signatures up to level $\lfloor p \rfloor$ , it sufices to show that for any multi-index I with $\left| I \right| \leq \left\lfloor p \right\rfloor$

$$
\langle e _ { I } , \mathbf { X } _ { t } \rangle = \langle e _ { I } , \mathbf { Y } _ { t } \rangle \quad { \mathrm { f o r ~ a l l ~ } } t \in [ 0 , T ] .
$$

To extract these values from the full signature $S ( \mathbf { X } ) _ { T }$ , we face the dificulty that $\left. { e _ { I } , { \mathbf { X } } _ { t } } \right.$ is a function of time, not a coeficient in the signature at time T. However, we can recover such functions by integrating them against powers of time. To do this, we first prove that:

$$
\langle e _ { 0 } ^ { \otimes k } , { \bf X } _ { t } \rangle = \frac { t ^ { k } } { k ! } \quad \mathrm { f o r ~ a l l ~ } k \geq 0 .
$$

We proceed by induction. For $k = 0 ,$ the claim is trivial. For $k = 1$ , we have $\langle e _ { 0 } , { \bf X } _ { t } \rangle = t$ by the definition of time augmentation. Assuming the identity holds for $k - 1$ , we get:

$$
\langle e _ { 0 } ^ { \otimes k } , \mathbf { X } _ { t } \rangle = \int _ { 0 } ^ { t } \langle e _ { 0 } ^ { \otimes ( k - 1 ) } , \mathbf { X } _ { u } \rangle d u = \int _ { 0 } ^ { t } { \frac { u ^ { k - 1 } } { ( k - 1 ) ! } } d u = { \frac { t ^ { k } } { k ! } } .
$$

Note that while condition (ii) in Definition 3.26 applies to $k \leq \lfloor p \rfloor$ , the relation extends to al $k \geq 0$ due to the bounded variation of the time component, the way $\mathbf { X } \in W G \hat { \Omega } _ { T } ^ { p } ( V )$ is constructed (Proposition 3.24) and the uniqueness of the signature extension.

Now fix any multi-index I with $\left| I \right| \leq \left\lfloor p \right\rfloor$ . Since $\mathbf { X } _ { t }$ and $S ( \mathbf { X } )$ <sub>t</sub> agree up to level $\lfloor p \rfloor$ , we have

$$
\langle e _ { I } , S ( { \mathbf { X } } ) _ { t } \rangle = \langle e _ { I } , { \mathbf { X } } _ { t } \rangle .
$$

Using the group-like property and the shufle product identity, we have

$$
\begin{array} { l } { { \displaystyle \langle ( e _ { I } \sqcup e _ { 0 } ^ { \otimes k } ) \otimes e _ { 0 } , S ( \mathbf { X } ) _ { T } \rangle = \int _ { 0 } ^ { T } \langle e _ { I } \sqcup e _ { 0 } ^ { \otimes k } , S ( \mathbf { X } ) _ { u } \rangle d u } \ ~ } \\ { { \displaystyle = \int _ { 0 } ^ { T } \langle e _ { I } , S ( \mathbf { X } ) _ { u } \rangle \langle e _ { 0 } ^ { \otimes k } , S ( \mathbf { X } ) _ { u } \rangle d u } \ ~ } \\ { { \displaystyle = \int _ { 0 } ^ { T } \langle e _ { I } , \mathbf { X } _ { u } \rangle \frac { u ^ { k } } { k ! } d u } . } \end{array}
$$

Applying the same reasoning to Y, and using the assumption $S ( \mathbf { X } ) _ { T } = S ( \mathbf { Y } ) _ { T }$ , we conclude that:

$$
\int _ { 0 } ^ { T } \left( \left. e _ { I } , \mathbf { X } _ { u } \right. - \left. e _ { I } , \mathbf { Y } _ { u } \right. \right) \frac { u ^ { k } } { k ! } d u = 0 .
$$

Since the functions $u \mapsto { \frac { u ^ { k } } { k ! } }$ (for $k \geq 0 )$ form a basis for the space of polynomials, and polynomials are dense in $C ( [ 0 , T ] )$ by the Stone–Weierstrass theorem, it follows that any continuous function whose integral against every such monomial vanishes must be identically zero. As $\mathbf { X } _ { u }$ and $\mathbf { Y } _ { u }$ are continuous, it follows that

$$
\langle e _ { I } , \mathbf { X } _ { u } \rangle = \langle e _ { I } , \mathbf { Y } _ { u } \rangle \quad { \mathrm { ~ f o r ~ a l l ~ } } u \in [ 0 , T ] ,
$$

which completes the proof.

Before proceeding, note that $W G \hat { \Omega } _ { T } ^ { p } ( V )$ , equipped with the p-variation distance, becomes a topological space whose topology is induced by the p-variation metric.

Theorem 3.31 (First Universal Approximation Theorem). Let $K \subset W G \hat { \Omega } _ { T } ^ { p } ( V )$ be compact, and let $f : W G \hat { \Omega } _ { T } ^ { p } ( V ) \to$ R be continuous with respect to the p-variation topology. Then, for every $\varepsilon > 0$ , there exists $\ell \in T ( \mathbb { R } \oplus V )$ such that

$$
\underset { \mathbf { X } \in K } { \operatorname* { s u p } } \left| f ( \mathbf { X } ) - \langle \ell , S ( \mathbf { X } ) _ { T } \rangle \right| < \varepsilon .
$$

<!-- page: 25 -->

Proof. We apply the Stone–Weierstrass theorem to a suitable subalgebra of continuous functions on the compact set $K \subset W G \hat { \Omega } _ { T } ^ { p } ( V )$ . Define

$$
A : = \operatorname { s p a n } { \big \{ } \mathbf { X } \mapsto \langle e _ { I } , S ( \mathbf { X } ) _ { T } \rangle ; I { \mathrm { ~ m u l t i - i n d e x ~ i n ~ } } \mathbb { R } \oplus V { \big \} } \subset C ( K ) .
$$

That is, A is the collection of all finite linear combinations of coordinate functionals on the signature evaluated at time T.

To show that A is a subalgebra of $C ( K )$ that satisfies the conditions of the Stone–Weierstrass theorem, consider first that A is closed under multiplication. As the group-like property

$$
\langle \ell _ { 1 } \sqcup \ell _ { 2 } , S ( { \mathbf { X } } ) _ { T } \rangle = \langle \ell _ { 1 } , S ( { \mathbf { X } } ) _ { T } \rangle \langle \ell _ { 2 } , S ( { \mathbf { X } } ) _ { T } \rangle
$$

corresponds to multiplication of linear functionals on the signature, the span of such functionals is closed under multiplication.

Second, A separates points in K due to the uniqueness of the signature of time-augmented weakly geometric rough paths: in particular, Theorem 3.30 guarantees that if $\mathbf { X } \neq \mathbf { Y }$ in $K$ , then $S ( \mathbf { X } ) _ { T } \neq S ( \mathbf { Y } ) _ { T } .$ , so there exists $\ell \in T ( \mathbb { R } \oplus V )$ such that $\langle \ell , S ( \mathbf { X } ) _ { T } \rangle \neq \langle \ell , S ( \mathbf { Y } ) _ { T } \rangle$

And third, A contains the constant functions, as can be seen by choosing $I = \varnothing .$ , for which $\langle e _ { I } , S ( { \bf X } ) _ { T } \rangle = 1$ . Therefore, by the Stone–Weierstrass theorem, A is dense in $C ( K )$ . In particular, for any $\varepsilon > 0$ , there exists $\ell \in T ( \mathbb { R } \oplus V )$ such that

$$
\underset { \mathbf { X } \in K } { \operatorname* { s u p } } \left| f ( \mathbf { X } ) - \langle \ell , S ( \mathbf { X } ) _ { T } \rangle \right| < \varepsilon .
$$

This result is important. The signature $S ( \mathbf { X } )$ , evaluated at time $T ,$ serves as a feature map that transforms a path into an infinite sequence of coordinates capturing all relevant information. Theorem 3.30 ensures that this representation is injective for time-augmented paths. It is then natural to ask whether signatures are rich enough to approximate functionals defined on paths. The First Universal Approximation Theorem answers this question afirmatively.

It specifically states that continuous functionals on compact subsets of the rough path space can be approximated arbitrarily well by linear functionals on the signature—that is, by finite linear combinations of iterated integrals. This makes signatures a powerful tool for representing and learning functionals on paths, especially in contexts such as calibration or supervised learning.

Our goal is to model one-dimensional stochastic processes of the form

$$
Y _ { t } = f \big ( ( \mathbf { X } _ { s } ) _ { s \in [ 0 , t ] } \big ) ,
$$

where $( \mathbf { X } _ { s } ) _ { s \in [ 0 , t ] }$ is a stochastic process, with each $\mathbf { X } _ { s } \in W G \hat { \Omega } _ { t } ^ { p } ( V )$ . Denote this stochastic process by $\mathcal { X } \colon$

$$
\begin{array} { c c c c } { \mathcal { X } : } & { [ 0 , t ] } & { \longrightarrow } & { W G \hat { \Omega } _ { t } ^ { p } ( V ) } \\ & { s } & { \longmapsto } & { \mathbf { X } _ { s } . } \end{array}
$$

Think of $Y _ { t }$ as a volatility process driven by a rough signal X. The function $f ,$ which encodes this dependence, is typically unknown.

Note that, as time increases, the domain of f changes: for each $t , \ ( \mathbf { X } _ { s } ) _ { s \in [ 0 , t ] }$ represents a collection of rough paths defined on a diferent time interval. To deal with this, we need a consistent way to interpret a rough path in $W G \hat { \Omega } _ { u } ^ { p } ( V )$ as an element of $W G \hat { \Omega } _ { t } ^ { p } ( V )$ for all $t \geq u .$ so that f can act on a common space.

Given the potential complexity of the notation, we begin with a simple case and build up from there. Let the weakly geometric p-rough path $\mathbf { X } \in W G \hat { \Omega } _ { T } ^ { p } ( V )$ be represented by the diagram:

$$
\begin{array} { l r c l } { \Delta _ { T } } & { \longrightarrow } & { T ^ { \lfloor p \rfloor } ( \mathbb { R } \oplus V ) } \\ { ( s , t ) } & { \longmapsto } & { \mathbf { X } _ { s , t } = \left( 1 , \mathbf { X } _ { s , t } ^ { 1 } , \dots , \mathbf { X } _ { s , t } ^ { \lfloor p \rfloor } \right) , } \end{array}
$$

<!-- page: 26 -->

for $0 \leq s \leq t \leq T$ . Fixing $s = 0$ , we write $\mathbf { X } _ { t } : = \mathbf { X } _ { 0 , t }$

$\mathrm { B y }$ Proposition 3.24, a rough path in $W G \hat { \Omega } _ { s } ^ { p } ( V )$ originates from a base path $X : [ 0 , s ] \to V$ that admits a lift $\mathbf { X } \in W G \Omega _ { s } ^ { p } ( V )$ . To emphasize that this rough path lives on [0, s], we denote it by ${ \bf \tau } _ { \left[ s \right] } \mathbf { X }$ , and it is represented by

$$
\begin{array} { r c l } { \Delta _ { s } } & { \longrightarrow } & { T ^ { \lfloor p \rfloor } ( V ) } \\ { ( r , u ) } & { \longmapsto } & { _ { [ s ] } \mathbf { X } _ { r , u } = \left( 1 , _ { [ s ] } \mathbf { X } _ { r , u } ^ { 1 } , \dots , _ { [ s ] } \mathbf { X } _ { r , u } ^ { \lfloor p \rfloor } \right) . } \end{array}
$$

For $u \in [ 0 , s ]$ , we write ${ \bf \{ s \} X } _ { u } : = { \bf \{ s \} X } _ { 0 , u }$

The time-augmented path is $\hat { X } _ { u } : = ( u , X _ { u } ) , u \in [ 0 , s ] . \mathrm { ~ B y }$ Proposition 3.24, $\hat { X }$ admits a weakly geometric p-rough path lift ${ \bf \Pi } _ { [ s ] } \hat { \mathbf { X } } \in W G \hat { \Omega } _ { s } ^ { p } ( V )$ . We refer to ${ \bf \tau } _ { [ s ] } \hat { \bf X }$ as the stopped path at time s.

To extend this construction from [0, s] to [0, t], with $s < t ,$ we define $_ { [ \mathrm { t } ] } \mathbf { X } \in W G \Omega _ { t } ^ { p } ( V )$ by:

$$
{ \bf \Gamma } _ { [ \mathfrak { t } ] } \mathbf { X } _ { u } : = \left\{ \begin{array} { l l } { _ { [ \mathfrak { s } ] } \mathbf { X } _ { u } } & { \mathrm { f o r } \ u \in [ 0 , s ] } \\ { _ { [ \mathfrak { s } ] } \mathbf { X } _ { s } } & { \mathrm { f o r } \ u \in [ s , t ] . } \end{array} \right.\tag{3.13}
$$

We then apply the construction from the proof of Proposition 3.24 to obtain a time-augmented rough path ${ \bf \Pi } _ { [ { \bf t } ] } \hat { \mathbf { X } } \in W G \hat { \Omega } _ { t } ^ { p } ( V )$ . By construction, $[ \mathbf { t } ] ^ { \hat { \mathbf { X } } }$ agrees with ${ \bf \tau } _ { [ s ] } \hat { \bf X }$ on $[ 0 , s ]$

This provides a consistent way to extend truncated rough paths defined on $[ 0 , s ]$ to the full interval $[ 0 , t ]$ , thus allowing $f$ to act on a unified space. The ability to extend time-augmented paths motivates the following definition.

Definition 3.32 (Stopped Rough Path). Let $p \geq 1$ . We define the space of weakly geometric stopped p-rough paths as

$$
\Lambda _ { T } ^ { p } ( V ) : = \bigcup _ { t \in [ 0 , T ] } W G \hat { \Omega } _ { t } ^ { p } ( V ) .
$$

Given $\mathbf { \Psi } _ { [ \mathsf { s } ] } \mathbf { X } \in W G \hat { \Omega } _ { s } ^ { p } ( V )$ and $\mathbf { \Psi } _ { [ \mathbf { t } ] } \mathbf { Y } \in W G \hat { \Omega } _ { t } ^ { p } ( V )$ , with $s \leq t _ { : }$ we define a metric on $\Lambda _ { T } ^ { p } ( V )$ by

$$
d ( _ { [ \mathsf { s } ] } \mathbf { X } , _ { [ \mathsf { t } ] } \mathbf { Y } ) : = d _ { p \cdot \mathrm { v a r } } ( _ { [ \mathsf { t } ] } \mathbf { X } , _ { [ \mathsf { t } ] } \mathbf { Y } ) + | t - s | ,
$$

where ${ \bf \tau } _ { [ \mathbf { t } ] } \mathbf { X }$ denotes the extension $o f _ { \ [ \mathsf { s } ] } \mathbf { X }$ from [0, s] to [0, t] as in $\left( \ 3 . 1 3 \right)$ , and $d _ { p \cdot \mathrm { v a r } }$ denotes the p-variation distance on $W G \hat { \Omega } _ { t } ^ { p } ( V )$

For further details on the topology of this space, see Kalsi et al. (2020) and Bayer et al. (2023). The concept of stopped rough paths provides a useful framework for handling adaptedness in stochastic settings. The Second Universal Approximation Theorem below is formulated in this space.

Theorem 3.33 (Second Universal Approximation Theorem). Let $K \subset W G \hat { \Omega } _ { T } ^ { p } ( V )$ be a compact subset, and let $f : \Lambda _ { T } ^ { p } ( V ) \to \mathbb { R }$ be a continuous function. Then, for every $\varepsilon > 0$ , there exists $\ell \in T ( \mathbb { R } \oplus V )$ such that

$$
\underset { \mathbf { X } \in K , \ t \in [ 0 , T ] } { \operatorname* { s u p } } \left| f ( _ { [ \ t ] } \mathbf { X } ) - \langle \ell , S ( _ { \lceil \ t \rceil } \mathbf { X } ) _ { t } \rangle \right| < \varepsilon ,
$$

where ${ \bf \tau } _ { [ \mathbf { t } ] } \mathbf { X }$ denotes the restriction of X to $[ 0 , t ] _ { i }$ , and $S ( \mathbf { \mathbf { \mathbf { \rho } } } _ { [ \ t ] } \mathbf { X } ) _ { t } : = S ( \mathbf { \mathbf { \mathbf { \rho } } } _ { [ \ t ] } \mathbf { X } ) _ { 0 , t }$ is the signature of the stopped rough path up to time t.

Proof. The proof is also based on the Stone-Weierstrass theorem, but is somewhat more technical. See Kalsi et al. (2020), Lemma B.3. □

This result shows that any continuous functional of a stopped rough path can be uniformly approximated, over all truncating times $t \in [ 0 , T ]$ and all paths in a compact set, by a linear functional on the signature. The approximation is uniform both in path space and in time.

<!-- page: 27 -->

## 4 Signature-Based Volatility Models

Assume, for simplicity, that $r = 0$ , and let $( S _ { t } ) _ { t \in [ 0 , T ] }$ denote the price process of a risky asset. We work under a risk-neutral measure, and model the discounted stock price $\tilde { S } _ { t } : = S _ { t }$ as

$$
d { \tilde { S } } _ { t } = { \tilde { S } } _ { t } \sigma _ { t } d B _ { t } ,
$$

where $\sigma _ { t }$ is the volatility and B is a standard Brownian motion.

Let $f : \Lambda _ { T } ^ { p } ( V ) \to \mathbb { R }$ be a continuous function and suppose that volatility can be expressed as

$$
\sigma _ { t } = f \big ( ( \mathbf { X } _ { s } ) _ { s \in [ 0 , t ] } \big ) ,
$$

where the stochastic process $\mathbf { X } \in \Lambda _ { T } ^ { p } ( V )$ is referred to as the primary process. This process represents the underlying source of noise driving the volatility and is assumed to take values in the space of stopped, time-augmented weakly geometric p-rough paths.

Fix an integer $N \geq 1$ and define the space

$$
\begin{array} { r } { A _ { N } : = \mathrm { s p a n } \left\{ \mathbf { X } \mapsto \langle e _ { I } , S ( \mathbf { X } ) _ { T } \rangle ; I \ \mathrm { m u l t i - i n d e x } \ \mathrm { i n } \ \mathbb { R } \oplus V , 0 \leq | I | \leq N \right\} , } \end{array}
$$

where $S ( \mathbf { X } ) _ { t } : = S ( \mathbf { \Gamma } _ { [ \mathbf { t } ] } \mathbf { X } ) _ { 0 , t }$ denotes the signature of the stopped path ${ \bf \tau } _ { [ \mathbf { t } ] } \mathbf { X }$

For a given $N \geq 1$ , our goal is to find the coeficients $\ell = \{ \ell _ { I } ; 0 \leq | I | \leq N \}$ that yield the best linear approximation $\langle \ell , S ( \mathbf { X } ) _ { t } ^ { \leq N } \rangle$ of the volatility $\sigma _ { t }$ , where

$$
\langle \ell , S ( \mathbf { X } ) _ { t } ^ { \leq N } \rangle = \sum _ { | I | \leq N } \ell _ { I } \langle e _ { I } , S ( \mathbf { X } ) _ { t } ^ { \leq N } \rangle
$$

with $S ( \mathbf { X } ) _ { t } ^ { \le N } \ \in \ T ^ { N } ( \mathbb { R } \oplus V )$ . This leads to the following signature-based stochastic volatility model:

$$
\begin{array} { r l } & { d \tilde { S } _ { t } ( \ell ) = \tilde { S } _ { t } ( \ell ) \sigma _ { t } ( \ell ) d B _ { t } , } \\ & { ~ \sigma _ { t } ( \ell ) = \displaystyle \sum _ { | I | \le N } \ell _ { I } \langle e _ { I } , S ( { \mathbf { X } } ) _ { t } ^ { \le N } \rangle . } \end{array}\tag{4.1}
$$

Since X is a stochastic process, the signature $S ( \mathbf { X } ) ^ { \leq N }$ is itself a stochastic process taking values in the truncated tensor algebra $T ^ { N } ( { \mathbb { R } } \oplus V )$

Example 4.1. Assume that the dynamics of $( S _ { t } ) _ { t \geq 0 }$ are given by

$$
d S _ { t } = r S _ { t } d t + \sigma _ { t } S _ { t } d ( \rho W _ { t } + \sqrt { 1 - \rho ^ { 2 } } B _ { t } ) ,
$$

where W and $B$ are independent standard Brownian motions. As the primary process $( X _ { t } ) _ { t \geq 0 }$ with dynamics

$$
d X _ { t } = \kappa ( \theta - X _ { t } ) d t + \nu \sqrt { X _ { t } } d W _ { t }\tag{4.2}
$$

is a continuous semimartingale, it admits a canonical weakly geometric rough path lift (see Remark 3.23). By Proposition 3.24, the time-augmented process also admits a weakly geometric p-rough path lift $\mathbf { X } \in W G \Omega _ { T } ^ { p } ( \mathbb { R } \oplus \mathbb { R } )$ , where time corresponds to coordinate 0 and $X _ { t }$ to coordinate 1. Note that the Feller condition 2κθ $\geq \nu ^ { 2 }$ ensures positivity of $X _ { t } ,$ but is not required for the existence of the rough path lift.

We model the volatility as a linear function of the truncated time-augmented signature up to level 2 of the primary process $X { : }$

$$
\sigma _ { t } ( \ell ) : = \sum _ { | I | \leq 2 } \ell _ { I } \langle e _ { I } , S ( \mathbf { X } ) _ { t } ^ { \leq 2 } \rangle .
$$

The truncated signature has the form

$$
\begin{array} { r } { S ( { \bf X } ) _ { t } ^ { \le 2 } = \left( 1 , ( t , X _ { t } ) , \left( \int _ { 0 } ^ { t } s d s \mathrm { ~  ~ \ } \int _ { 0 } ^ { t } s d X _ { s } \right) \right) . } \end{array}
$$

<!-- page: 28 -->

If we let

$$
\ell = \left( \ell _ { \varnothing } , \ell _ { 0 } , \ell _ { 1 } , \ell _ { 0 0 } , \ell _ { 0 1 } , \ell _ { 1 0 } , \ell _ { 1 1 } \right) ,
$$

we then have

$$
\sigma _ { t } ( \ell ) = \ell _ { \theta } + \ell _ { 0 } t + \ell _ { 1 } X _ { t } + \ell _ { 0 0 } \frac { t ^ { 2 } } { 2 } + \ell _ { 0 1 } \int _ { 0 } ^ { t } s d X _ { s } + \ell _ { 1 0 } \int _ { 0 } ^ { t } X _ { s } d s + \ell _ { 1 1 } \int _ { 0 } ^ { t } X _ { s } d X _ { s } .
$$

Diferentiating with respect to t and using (4.2) yields

$$
\begin{array} { r l } & { d \sigma _ { t } ( \ell ) = \left( \ell _ { 0 } + \ell _ { 0 0 } t + \ell _ { 1 0 } X _ { t } + \left( \ell _ { 1 } + \ell _ { 0 1 } t + \ell _ { 1 1 } X _ { t } \right) \kappa ( \theta - X _ { t } ) \right) d t } \\ & { \qquad + \nu \sqrt { X _ { t } } \left( \ell _ { 1 } + \ell _ { 0 1 } t + \ell _ { 1 1 } X _ { t } \right) d W _ { t } . } \end{array}
$$

This expression shows how a linear signature model recovers a volatility process consistent with the Heston variance dynamics.

Continuing with the example, the third level of the time-augmented signature, $S ( \mathbf { X } ) _ { t } ^ { 3 }$ , consists of iterated integrals over $0 < u _ { 1 } < u _ { 2 } < u _ { 3 } < t ,$ indexed by $I = ( i _ { 1 } , i _ { 2 } , i _ { 3 } ) \in \{ 0 , 1 \} ^ { 3 }$ . A few representative terms are:

$$
\langle e _ { 0 0 0 } , S ( { \bf X } ) _ { t } \rangle = \int _ { 0 } ^ { t } \int _ { 0 } ^ { u _ { 2 } } \int _ { 0 } ^ { u _ { 1 } } d u _ { 0 } d u _ { 1 } d u _ { 2 } = \frac { t ^ { 3 } } { 6 } ,
$$

$$
\left. e _ { 0 0 1 } , S ( { \bf X } ) _ { t } \right. = \int _ { 0 } ^ { t } \int _ { 0 } ^ { u _ { 2 } } \int _ { 0 } ^ { u _ { 1 } } d u _ { 0 } d u _ { 1 } d X _ { u _ { 2 } } ,
$$

$$
\left. e _ { 0 1 1 } , S ( { \mathbf { X } } ) _ { t } \right. = \int _ { 0 } ^ { t } \int _ { 0 } ^ { u _ { 2 } } \int _ { 0 } ^ { u _ { 1 } } d u _ { 0 } d X _ { u _ { 1 } } d X _ { u _ { 2 } } ,
$$

$$
\langle e _ { 1 1 1 } , S ( { \bf X } ) _ { t } \rangle = \int _ { 0 } ^ { t } \int _ { 0 } ^ { u _ { 2 } } \int _ { 0 } ^ { u _ { 1 } } d X _ { u _ { 0 } } d X _ { u _ { 1 } } d X _ { u _ { 2 } } .
$$

In total, the third level of the time-augmented signature includes $2 ^ { 3 } = 8$ terms:

$$
{ ( \begin{array} { l l } { \langle e _ { 0 0 0 } , S ( \mathbf { X } ) _ { t } \rangle } & { \langle e _ { 0 0 1 } , S ( \mathbf { X } ) _ { t } \rangle } \\ { \langle e _ { 0 1 0 } , S ( \mathbf { X } ) _ { t } \rangle } & { \langle e _ { 0 1 1 } , S ( \mathbf { X } ) _ { t } \rangle } \\ { \langle e _ { 1 0 0 } , S ( \mathbf { X } ) _ { t } \rangle } & { \langle e _ { 1 0 1 } , S ( \mathbf { X } ) _ { t } \rangle } \\ { \langle e _ { 1 1 0 } , S ( \mathbf { X } ) _ { t } \rangle } & { \langle e _ { 1 1 1 } , S ( \mathbf { X } ) _ { t } \rangle } \end{array} ) } =  ( \begin{array} { l l } { \int _ { 0 } ^ { t } \int _ { 0 } ^ { u _ { 2 } } \int _ { 0 } ^ { u _ { 1 } } d u _ { 0 } d u _ { 1 } d u _ { 2 } } & { \int _ { 0 } ^ { t } \int _ { 0 } ^ { u _ { 2 } } \int _ { 0 } ^ { u _ { 1 } } d u _ { 0 } d u _ { 1 } d X _ { u _ { 2 } } } \\ { \int _ { 0 } ^ { t } \int _ { 0 } ^ { u _ { 2 } } \int _ { 0 } ^ { u _ { 1 } } d u _ { 0 } d X _ { u _ { 1 } } d u _ { 2 } } & { \int _ { 0 } ^ { t } \int _ { 0 } ^ { u _ { 2 } } \int _ { 0 } ^ { u _ { 1 } } d u _ { 0 } d X _ { u _ { 1 } } d X _ { u _ { 2 } } } \\ { \int _ { 0 } ^ { t } \int _ { 0 } ^ { u _ { 2 } } \int _ { 0 } ^ { u _ { 1 } } d X _ { u _ { 0 } } d u _ { 1 } d u _ { 2 } } & { \int _ { 0 } ^ { t } \int _ { 0 } ^ { u _ { 2 } } \int _ { 0 } ^ { u _ { 1 } } d X _ { u _ { 0 } } d u _ { 1 } d X _ { u _ { 2 } } } \\  \int _ { 0 } ^ { t } \int _ { 0 } ^  u _  2  \end{array}
$$

In Sections 5 and 6 we will work with the truncated signature $S ( \mathbf { X } ) _ { t } ^ { \leq 3 }$

## 4.1 The Signature Approximation to Volatility

If V has dimension $d ,$ let $\textstyle d _ { N } : = \sum _ { k = 0 } ^ { N } d ^ { k }$ denote the dimension of the truncated tensor algebra $T ^ { N } ( V )$ . The following notation allows us to represent elements of $T ^ { N } ( V )$ as vectors in $\mathbb { R } ^ { d _ { N } }$ . Let

$$
\mathcal { L } : \{ I ; ~ \lvert I \rvert \le N \} ~ \to ~ \{ 1 , \ldots , d _ { N } \}
$$

be a labeling function, that is, a bijection that assigns a unique index to each multi-index I of length at most N. For any $\begin{array} { r } { \ell = \sum _ { | I | \le N } \ell _ { I } e _ { I } \in T ^ { N } ( V ) } \end{array}$ , the map

$$
\begin{array} { r c l l } { \mathbf { v e c } \colon } & { T ^ { N } ( V ) } & { \to } & { { \mathbb R } ^ { d _ { N } } } \\ & & { \ell } & { \mapsto } & { \left( { \ell _ { \mathcal { L } } } \mathrm { - } ^ { 1 } ( 1 ) , \dots , { \ell _ { \mathcal { L } } } \mathrm { - } ^ { 1 } ( d _ { N } ) \right) } \end{array}
$$

flattens the elements of $T ^ { N } ( V )$ , making it possible to identify tensors with vectors in $\mathbb { R } ^ { d _ { N } }$ . This makes the use of signature data in numerical algorithms quite convenient. We now apply this to the truncated signature $\tilde { S } _ { t } ( \ell )$

<!-- page: 29 -->

Assume that the primary process $\mathbf { X } \in \Lambda _ { T } ^ { p } ( V )$ is obtained as the rough path lift of a stochastic process $( t , X _ { t } )$ , where $X _ { t }$ solves an SDE driven by a Brownian motion $W _ { t }$ . In particular, X is measurable with respect to W and adapted to its natural filtration.

As above, let $f : \Lambda _ { T } ^ { p } ( V ) \to$ R be a continuous function and let $\sigma _ { t } = f \big ( ( \mathbf { X } _ { s } ) _ { s \in [ 0 , t ] } \big )$ . Define the process $Z _ { t } : = \rho W _ { t } + \sqrt { 1 - \rho ^ { 2 } } B _ { t }$ , where B is another Brownian motion, independent of $W$ . Our model is then

$$
\begin{array} { r l } & { d \tilde { S } _ { t } ( \ell ) = \tilde { S } _ { t } ( \ell ) \sigma _ { t } ( \ell ) d Z _ { t } } \\ & { ~ \sigma _ { t } ( \ell ) \approx \displaystyle \sum _ { | I | \le N } \ell _ { I } \langle e _ { I } , S ( { \mathbf { X } } ) _ { t } ^ { \le N } \rangle , } \end{array}\tag{4.3}
$$

where (4.3) is a well-defined Itô integral, since $\sigma _ { t } ( \ell )$ is a predictable process adapted to the filtration of $W ,$ and Z is a Brownian motion correlated with W. Recall that $S ( \mathbf { X } ) _ { t } = S ( \mathbf { \Gamma } _ { [ \mathbf { t } ] } \mathbf { X } ) _ { 0 , t }$ is the signature of the stopped path $\mathbf { \tau } _ { [ \mathbf { t } ] } \mathbf { X }$ . The solution of (4.3) can be expressed in terms of the signature as follows.

Proposition 4.2. Let $\tilde { S } _ { t } ( \ell )$ be the discounted price process defined by (4.3), and assume that $\mathbf { X } \in W G \hat { \Omega } _ { T } ^ { p } ( V )$ is the time-augmented weakly geometric p-rough path lift of a stochastic process $( t , X _ { t } )$ adapted to a Brownian motion W. Let $Z _ { t } = \rho W _ { t } + \sqrt { 1 - \rho ^ { 2 } } B _ { t }$ , where B is a Brownian motion independent of W. Then, for a given $N \geq 1$ , the discounted price process $\tilde { S } _ { t } ( \ell )$ admits the representation

$$
\tilde { S } _ { t } ( \ell ) = S _ { 0 } \exp \left( \ell ^ { T } Q ( t ) \ell + \ell ^ { T } \int _ { 0 } ^ { t } { \mathbf { v e c } } ( S ( { \mathbf { X } } ) _ { s } ^ { \leq N } ) d Z _ { s } \right) ,
$$

where $\ell ^ { T }$ denotes the transpose of ℓ, and $Q ( t )$ is the symmetric matrix defined by

$$
{ \cal Q } ( t ) _ { \mathcal { L } ( I ) , \mathcal { L } ( J ) } : = - \frac { 1 } { 2 } \left. \left( e _ { I } \sqcup e _ { J } \right) \otimes e _ { 0 } , \ S ( { \bf X } ) _ { t } ^ { \le 2 N + 1 } \right. .
$$

Proof. Rewrite (4.3) as

$$
\frac { d \tilde { S } _ { t } ( \ell ) } { \tilde { S } _ { t } ( \ell ) } = \sigma _ { t } ( \ell ) d Z _ { t } .
$$

Applying Itô’s formula, we have

$$
\begin{array} { l } { { d \log ( \widetilde { S } _ { t } ( \ell ) ) = \displaystyle \frac { d \widetilde { S } _ { t } ( \ell ) } { \widetilde { S } _ { t } ( \ell ) } + \frac { 1 } { 2 } \left( \frac { - 1 } { \widetilde { S } _ { t } ( \ell ) ^ { 2 } } \right) \sigma _ { t } ( \ell ) ^ { 2 } \widetilde { S } _ { t } ( \ell ) ^ { 2 } d t } } \\ { { \mathrm { } = - \displaystyle \frac { 1 } { 2 } \sigma _ { t } ( \ell ) ^ { 2 } d t + \sigma _ { t } ( \ell ) d Z _ { t } . } } \end{array}
$$

Integrating and rearranging we get

$$
\tilde { S } _ { t } ( \ell ) = S _ { 0 } \exp \left( - \frac { 1 } { 2 } \int _ { 0 } ^ { t } \sigma _ { s } ( \ell ) ^ { 2 } d s + \int _ { 0 } ^ { t } \sigma _ { s } ( \ell ) d Z _ { s } \right) .\tag{4.4}
$$

With the notation introduced above, we can express the linear approximation of order $N$ to the volatility as

$$
\begin{array} { r } { \sigma _ { t } ( \ell ) = \ell ^ { T } \mathbf { v e c } \left( S ( \mathbf { X } ) _ { t } ^ { \leq N } \right) . } \end{array}
$$

It follows that

$$
\begin{array} { r } { \sigma _ { t } ( \ell ) ^ { 2 } = ( \ell ^ { T } \mathbf { v e c } ( S ( \mathbf { X } ) _ { t } ^ { \leq N } ) ) ( \ell ^ { T } \mathbf { v e c } ( S ( \mathbf { X } ) _ { t } ^ { \leq N } ) ) ^ { T } = \ell ^ { T } \mathbf { v e c } ( S ( \mathbf { X } ) _ { t } ^ { \leq N } ) \mathbf { v e c } ( S ( \mathbf { X } ) _ { t } ^ { \leq N } ) ) ^ { T } \ell . } \end{array}
$$

Define $\tilde { Q } ( t ) : = \mathbf { v e c } \left( S ( \mathbf { X } ) _ { t } ^ { \leq N } \right) \mathbf { v e c } \left( S ( \mathbf { X } ) _ { t } ^ { \leq N } \right) ^ { T }$ , which is a symmetric positive semi-definite matrix representing the outer product of the truncated signature vector with itself. We then have

$$
\sigma _ { t } ( \ell ) ^ { 2 } = \ell ^ { T } \tilde { Q } ( t ) \ell .
$$

<!-- page: 30 -->

Note that the elements of $\tilde { Q } ( t )$ are

$$
\tilde { Q } ( t ) _ { \mathcal { L } ( I ) \mathcal { L } ( J ) } = \langle e _ { I } , S ( \mathbf { X } ) _ { t } ^ { \leq N } \rangle \langle e _ { J } , S ( \mathbf { X } ) _ { t } ^ { \leq N } \rangle = \langle e _ { I } \shuffle e _ { J } , S ( \mathbf { X } ) _ { t } ^ { \leq 2 N } \rangle .
$$

It follows that

$$
\begin{array} { r l r } {  { \int _ { 0 } ^ { t } \tilde { Q } ( s ) _ { \mathcal { L } ( I ) \mathcal { L } ( J ) } d s = \int _ { 0 } ^ { t } \langle e _ { I } \shuffle e _ { J } , S ( \mathbf { X } ) _ { s } ^ { \leq 2 N } \rangle d s } } \\ & { } & { = \langle ( e _ { I } \shuffle e _ { J } ) \otimes e _ { 0 } , S ( \mathbf { X } ) _ { t } ^ { \leq 2 N + 1 } \rangle . } \end{array}\tag{4.5}
$$

If we define the matrix Q(t) by

$$
{ \cal Q } ( t ) _ { \mathcal { L } ( I ) \mathcal { L } ( J ) } : = - \frac { 1 } { 2 } \langle \left( e _ { I } \sqcup e _ { J } \right) \otimes e _ { 0 } , S ( { \bf X } ) _ { t } ^ { \le 2 N + 1 } \rangle ,\tag{4.6}
$$

then the first term in the exponential of (4.4) can be written as

$$
- \frac { 1 } { 2 } \int _ { 0 } ^ { t } \sigma _ { s } ( \ell ) ^ { 2 } d s = \ell ^ { T } \left( - \frac { 1 } { 2 } \int _ { 0 } ^ { t } \tilde { Q } ( s ) d s \right) \ell = \ell ^ { T } Q ( t ) \ell .
$$

The second term in the exponential is

$$
\int _ { 0 } ^ { t } \sigma _ { s } ( \ell ) d Z _ { s } = \ell ^ { T } \int _ { 0 } ^ { t } \mathbf { v e c } \left( S ( \mathbf { X } ) { \boldsymbol { \frac { \leq N } { s } } } \right) d Z _ { s } ,
$$

which concludes the proof.

Since $\tilde { Q } ( t )$ is positive semi-definite by construction, it follows that $Q ( t )$ is negative semi-definite. That is, for every $\boldsymbol { \ell } \in \mathbb { R } ^ { d _ { N } }$

$$
\ell ^ { T } Q ( t ) \ell \leq 0 .
$$

As the Cholesky decomposition applies to positive semi-definite matrices, $- Q ( t )$ admits a Cholesky decomposition $U ( t ) ^ { T } U ( t )$ . We can therefore write

$$
\ell ^ { T } Q ( t ) \ell = - | | U ( t ) \ell | | _ { 2 } ^ { 2 } .
$$

Note that it is cheaper to compute $| | U ( t ) \ell | | _ { 2 } ^ { 2 }$ than $\ell ^ { T } Q ( t ) \ell$

Remark 4.3. In the case of a one-dimensional primary process, we see from (4.6) that $Q ( t )$ depends on the signature $S ( \mathbf { X } ) _ { i }$ <sub>t</sub> up to level $2 N + 1$

If the signature is truncated at level $N = 3$ , then $\tilde { Q } ( t )$ is a $1 5 \times 1 5$ -matrix, whose elements are of the type $\langle e _ { I } , S ( { \mathbf { X } } ) _ { t } ^ { \leq 3 } \rangle$ , where the 15 basis elements are

$$
\{ 1 , e _ { 0 } , e _ { 1 } , e _ { 0 0 } , e _ { 0 1 } , e _ { 1 0 } , e _ { 1 1 } , e _ { 0 0 0 } , e _ { 0 0 1 } , e _ { 0 1 0 } , e _ { 0 1 1 } , e _ { 1 0 0 } , e _ { 1 0 1 } , e _ { 1 1 0 } , e _ { 1 1 1 } \} .
$$

With the above ordering, $\mathcal { L } ( e _ { 0 1 } ) ~ = ~ 5$ and $\mathcal { L } ( e _ { 1 1 1 } ) \ : = \ : 1 5$ . The (15, 5)-entry of matrix $\tilde { Q } ( t )$ is therefore

$$
\tilde { Q } ( t ) _ { 1 5 , 5 } = \langle e _ { 1 1 1 } , S ( { \mathbf { X } } ) _ { t } ^ { \leq 3 } \rangle \langle e _ { 0 1 } , S ( { \mathbf { X } } ) _ { t } ^ { \leq 3 } \rangle .
$$

By (4.5),

$$
\int _ { 0 } ^ { t } \tilde { Q } ( s ) _ { 1 5 , 5 } d s = \langle \left( e _ { 1 1 1 } \sqcup e _ { 0 1 } \right) \otimes e _ { 0 } , S ( \mathbf { X } ) _ { t } ^ { \leq 7 } \rangle ,
$$

where

$$
\begin{array} { r } { \left( e _ { 1 1 1 } \sqcup e _ { 0 1 } \right) \otimes e _ { 0 } = \left( e _ { 1 1 1 0 1 } + 2 e _ { 1 1 0 1 1 } + 3 e _ { 1 0 1 1 1 } + 4 e _ { 0 1 1 1 1 } \right) \otimes e _ { 0 } } \\ { = e _ { 1 1 1 0 1 0 } + 2 e _ { 1 1 0 1 1 0 } + 3 e _ { 1 0 1 1 1 0 } + 4 e _ { 0 1 1 1 1 0 } , \qquad } \end{array}
$$

which includes basis elements of tensor spaces of higher dimensions. In particular, to compute the matrix $Q ( t )$ , we see from (4.6) that its entries $\langle ( e _ { I } \sqcup e _ { J } ) \otimes e _ { 0 } , S ( { \mathbf { X } } ) _ { t } ^ { \leq \hat { 2 } N + 1 } \rangle$ live in a space of dimension $2 ^ { ( 2 N + 1 ) + 1 } - 1$

In our particular case, $2 N + 1 = 7$ , so $Q ( t )$ depends on signature entries in $T ^ { \leq 7 } ( \mathbb { R } \oplus V )$ , a space of dimension $2 ^ { 8 } - 1 = 2 5 5$ . To populate a $1 5 \times 1 5$ matrix we need to fetch its elements from the entries of a $2 5 5 \times 2 5 5$ matrix.

<!-- page: 31 -->

## 4.2 Calibration

Consider the following model of a discounted asset price, parameterized by $\theta \colon$

$$
d \tilde { S } _ { t } ^ { \theta } = \tilde { S } _ { t } ^ { \theta } \sigma _ { t } ^ { \theta } d Z _ { t } ,
$$

where $\sigma _ { t } ^ { \theta }$ is the volatility process associated with the parameter $\theta ,$ and $Z _ { t }$ is as in (4.3). For a given $\theta ,$ we can compute the price of a European call option with strike K and maturity $T$ as

$$
C ( K , T , \theta ) = e ^ { - r T } \mathbb { E } [ ( S _ { T } ^ { \theta } - K ) _ { + } ] = \mathbb { E } [ ( \tilde { S } _ { T } ^ { \theta } - e ^ { - r T } K ) _ { + } ] .
$$

Let $\{ C ^ { \mathrm { m k t } } ( K _ { i } , T _ { i } ) \} _ { i = 1 } ^ { N }$ denote the observed market prices for varying strikes and maturities. If there exists a parameter $\theta ^ { * }$ such that the model perfectly describes the real dynamics of the asset, then

$$
C ^ { \mathsf { m k t } } ( K _ { i } , T _ { i } ) = C ( K _ { i } , T _ { i } , \theta ^ { * } ) \quad \mathrm { f o r ~ a l l ~ } i .
$$

While this exact match is unlikely in practice, our goal is to find a parameter configuration θ that minimizes the discrepancy between the model and market prices. We thus consider the least squares loss function

$$
L ( \theta ) = \sum _ { i = 1 } ^ { N } \gamma _ { i } \left( C ^ { \mathsf { m k t } } ( K _ { i } , T _ { i } ) - C ( K _ { i } , T _ { i } , \theta ) \right) ^ { 2 } ,
$$

where $\gamma _ { i } > 0$ are user-specified weights.

In the case of signature-based models, the role of the parameter θ is played by a vector $\boldsymbol { \ell } \in \mathbb { R } ^ { d _ { N } }$ where $d _ { N }$ is the dimension of the truncated signature space. The corresponding loss function becomes

$$
L ( \ell ) = \sum _ { i = 1 } ^ { N } \gamma _ { i } \left( C ^ { \mathsf { m k t } } ( K _ { i } , T _ { i } ) - C ( K _ { i } , T _ { i } , \ell ) \right) ^ { 2 } .\tag{4.7}
$$

Recall that the value of the signature-driven price process $\tilde { S } _ { t } ( \ell )$ at maturity $t = T$ is given by

$$
\tilde { S } _ { T } ( \ell ) ( \omega ) = S _ { 0 } \exp \left( - \| U ( T ) ( \omega ) \ell \| _ { 2 } ^ { 2 } + \ell ^ { T } \int _ { 0 } ^ { T } \mathbf { v e c } \left( S ( \mathbf { X } ) _ { t } ^ { \leq N } ( \omega ) \right) d Z _ { t } \right) ,\tag{4.8}
$$

where $U ( T ) ( \omega )$ is the Cholesky factor associated with $- Q ( T )$ on sample path $\omega ,$ and $S ( { \mathbf { X } } ) _ { t } ^ { \le N }$ is the truncated signature of the primary process X up to level $N$

## 4.3 The Algorithm

We start by simulating the discounted stock prices $\tilde { S } _ { T }$ at maturities $T \in \{ 0 . 1 , \ 0 . 6 , \ 1 . 1 , \ 1 . 6 \}$ For each $T _ { \mathrm { : } }$ , we need to compute the matrix $U ( T )$ and the stochastic integrals $\begin{array} { r } { \int _ { 0 } ^ { T } \mathbf { v e c } ( S ( \mathbf { X } ) _ { t } ^ { \leq N } ) d Z _ { t } } \end{array}$ that appear in (4.8). Let $n _ { \mathrm { M C } }$ be the number of Monte Carlo samples; for each maturity, we compute the call prices corresponding to strikes $K \in \{ 9 0 , \ 9 5 , \ 1 0 0 , \ 1 0 5 , \ 1 1 0 \}$ , which yields the following 20 values:

$$
C ( K _ { i } , T _ { i } , \ell ) \approx \frac { 1 } { n _ { \mathrm { M C } } } \sum _ { j = 1 } ^ { n _ { \mathrm { M C } } } \Big ( \tilde { S } _ { T _ { i } } ( \ell ) ( \omega _ { j } ) - e ^ { - r T _ { i } } K _ { i } \Big ) _ { + } ,
$$

$i = 1 , \ldots , 2 0$ , where each $\omega _ { j }$ denotes a sample path.

For calibration, we use as ground truth the synthetic market prices $\{ C ^ { \mathsf { m k t } } ( K _ { i } , T _ { i } ) \} _ { i = } ^ { 2 0 }$ generated under the assumption that the market follows either Heston (Section 5) or rough Bergomi dynamics (Section 6).

<!-- page: 32 -->

The signature approach seeks to minimize the discrepancy between market option prices and signature-generated prices, which is achieved by minimizing

$$
L ( \ell ) = \sum _ { i = 1 } ^ { 2 0 } { \gamma _ { i } \left( C ^ { \mathrm { m k t } } ( K _ { i } , T _ { i } ) - C ( K _ { i } , T _ { i } , \ell ) \right) ^ { 2 } } ,
$$

where the weights $\gamma _ { i }$ are proportional to the inverse Vega of each option.

Once the optimal coeficient vector $\ell ^ { * }$ is obtained, we can generate three sets of option prices. We describe here the Heston case:<sup>1</sup>:

$\{ C ^ { \mathsf { m k t } } ( K _ { i } , T _ { i } ) \}$ , the synthetic "market" prices,

$\{ C ( K _ { i } , T _ { i } , \ell ^ { * } ) \}$ , the signature model prices,

$\{ C ^ { A S V } ( K _ { i } , T _ { i } ) \}$ , the prices using the second-order approximation in Alòs et al. (2015).

Using these prices, we compute the three implied volatility surfaces from the Black-Scholes formula:

$\{ \mathrm { I V } ^ { \mathsf { m k t } } ( K _ { i } , T _ { i } ) \}$ , from the "market" prices,

$\{ \mathrm { I V } ^ { S I G } ( K _ { i } , T _ { i } , \ell ^ { * } ) \}$ }, from the signature model prices,

$\{ \mathrm { I V } ^ { A S V } ( K _ { i } , T _ { i } ) \}$ , from the second-order approximation prices.

These surfaces are compared in Section 5. We now describe the algorithm in detail.

1. Simulate sample paths. Generate $n _ { \mathrm { M C } }$ Monte Carlo paths for the Brownian motions W and B using Gaussian increments. Construct $Z = \rho W + \sqrt { 1 - \rho ^ { 2 } } B$ , and simulate the process X using an Euler scheme. Construct the augmented process $\mathbf { X } ,$ and for each path:

• compute the truncated signature $S ( \mathbf { X } ) _ { T } ^ { \le 2 N + 1 }$ ，

• evaluate the stochastic integral $\begin{array} { r } { \int _ { 0 } ^ { T } \mathbf { v e c } ( S ( \mathbf { X } ) _ { t } ^ { \leq N } ) d Z _ { t } } \end{array}$

2. Assemble the matrix $Q ( T )$ . For each sample path, compute the symmetric matrix

$$
Q ( T ) _ { \mathcal { L } ( I ) , \mathcal { L } ( J ) } = - \frac { 1 } { 2 } \left. ( e _ { I } \sqcup e _ { J } ) \otimes e _ { 0 } , \ S ( \mathbf { X } ) _ { T } ^ { \leq 2 N + 1 } \right. ,
$$

and perform a Cholesky decomposition of $- Q ( T )$ to obtain $U ( T )$

3. Optimize the loss. Initialize $\ell \in \mathbb { R } ^ { d _ { N } }$ and iterate the following steps until convergence:

(a) For each path $\omega _ { j } .$ , evaluate

$$
\tilde { S } _ { T } ( \ell ) ( \omega _ { j } ) = S _ { 0 } \exp \left( - \| U ( T ) ( \omega _ { j } ) \ell \| _ { 2 } ^ { 2 } + \ell ^ { T } \int _ { 0 } ^ { T } \mathbf { v e c } ( S ( \mathbf { X } ) _ { t } ^ { \le N } ( \omega _ { j } ) ) d Z _ { t } \right) .
$$

(b) Compute $C ( K _ { i } , T _ { i } , \ell )$ as the Monte Carlo average over $\omega _ { j }$

(c) Evaluate $L ( \ell )$ and update ℓ using a numerical optimizer.

Note that the signatures are computed once $( o f f i n e )$ and reused when updating ℓ, making cali bration significantly faster.

Before presenting the results, we highlight an important structural property of signatures that will serve as a diagnostic for numerical approximation quality.

<sup>1</sup>The superscript SIG refers to results from the signature-based approach. In the case of the Heston approximation of Alòs et al. (2015), we use the superscript ASV (from the authors’ surnames). In Section 6, the prices obtained with the analytical approximation described in Section 2.2 will be denoted by superscript VIX.

<!-- page: 33 -->

Proposition 4.4 (Factorial Decay). Let $X : [ 0 , T ] \mathbb { R } ^ { d }$ be a path of finite p-variation for some $p \geq 1$ , and let $\mathbf { X } \in \overset { \cdot } { W } G \hat { \Omega } _ { T } ^ { p } ( \mathbb { R } ^ { d } )$ denote its time-augmented weakly geometric rough path $l i f t .$ . Then for all $k \geq 1$ , the k-th level satisfies

$$
\| \mathbf { X } _ { s , t } ^ { k } \| \leq \frac { C ( X ) ^ { k } } { k ! } ,
$$

for some constant $C ( X ) > 0$ depending on X, uniformly over all $( s , t ) \in \Delta _ { T }$ , and $f o r$ any tensor norm on $( \mathbb { R } ^ { d } ) ^ { \otimes k }$

This factorial decay follows from the multiplicative (group-like) structure and the control provided by the p-variation norm. In practice, it serves as a valuable check: the magnitudes of the iterated integrals should decay rapidly with $k ,$ and deviations from this pattern can signal numerical instability or truncation issues. See Lyons (1998) and (Friz and Victoir, 2010, Thm. 10.35) for proofs and generalizations.

For paths of bounded variation, a stronger estimate holds:

$$
\| \mathbf { X } _ { s , t } ^ { k } \| \leq \frac { 1 } { k ! } \| \mathbf { X } \| _ { 1 \cdot \mathrm { v a r } } ^ { k } ,
$$

as noted in Fermanian (2021). This bound is exact for signatures of bounded variation paths. Although it does not hold for arbitrary p-rough paths, it remains relevant numerically, since signature approximations are typically based on interpolated (and hence BV) paths.

Implementation details. Results in the following sections correspond to $n _ { \mathrm { M C } } = 8 0 0 { , } 0 0 0$ Monte Carlo paths and signature truncation level $N = 3$ . Brownian increments are generated via standard Gaussian sampling, and X is simulated using an Euler discretization.

Signatures are computed using a vectorized version of Peter Foster’s code<sup>2</sup>, adapted for GPU acceleration. Optimization of $L ( \ell )$ is done using $\operatorname { S c i P y } { \mathrm { ? s } }$ minimize function with the L-BFGS-B method (tolerance $1 0 ^ { - 8 } )$ , and with box constraints on $\ell$ to accelerate convergence.

Issa et al. (2023) note that the choice of interpolation method typically has little impact and that simple linear interpolation is often suficient to compute signature approximations. We did experiment with higher-order interpolation schemes (such as cubic splines), but the marginal gains in accuracy were negligible, so we kept it linear.

All computations were carried out on a consumer desktop with 128 GB RAM and an NVIDIA RTX 3080 Ti GPU, without access to specialized computing clusters.

## 5 Calibration with a Heston Primary Process

In this section, we compare the performance of the signature-based method introduced in Section 4 with the parametric approach presented in Section 2.1.

As the signature-based approach learns volatility directly from a primary noise, we first tested this learning mechanism using an Ornstein–Uhlenbeck process. However, to compare fairly with the parametric calibration in Alòs et al. (2015), which is derived under Heston dynamics, we use a Heston variance primary process.

## 5.1 Calibration Setup. The Uncorrelated Case.

Recall that the market model in Alòs et al. (2015) is given by:

$$
\begin{array} { l } { d S _ { t } = r S _ { t } d t + \sigma _ { t } S _ { t } d \big ( \rho W _ { t } + \sqrt { 1 - \rho ^ { 2 } } B _ { t } \big ) , } \\ { d \sigma _ { t } ^ { 2 } = \kappa ( \theta - \sigma _ { t } ^ { 2 } ) d t + \nu \sqrt { \sigma _ { t } ^ { 2 } } d W _ { t } . } \end{array}
$$

<sup>2</sup>https://github.com/pafoster/path\_signatures\_introduction

<!-- page: 34 -->

Using the calibrated parameters from Table 2.1, we compute option prices and invert the Black-Scholes formula to obtain the implied volatility surface, which we denote by $\mathrm { I V } ^ { \mathsf { A S V } }$

To calibrate the signature-based model, we consider 20 option prices $\begin{array} { r } { C ( K _ { i } , T _ { i } ) } \end{array}$ at maturities {0.1, 0.6, 1.1, 1.6} and strikes {90, 95, 100, 105, 110}. The primary process X follows a Heston variance SDE with parameters $X _ { 0 } = 0 . 1 , \nu = 0 . 2 , \kappa = 2$ , and $\theta = 0 . 1 5$

Volatility is modeled as:

$$
\sigma _ { t } ( \ell ) \approx \langle \ell , S ( { \mathbf { X } } ) _ { t } ^ { \le 3 } \rangle ,
$$

where $S ( \mathbf { X } ) _ { t } ^ { \leq 3 }$ is the truncated signature of the time-augmented path $\hat { X } _ { t } ~ = ~ ( t , X _ { t } )$ . The loss function to minimize is:

$$
L ( \ell ) = \sum _ { i = 1 } ^ { 2 0 } { \gamma _ { i } \left( C ^ { m \ k t } ( K _ { i } , T _ { i } ) - C ( K _ { i } , T _ { i } , \ell ) \right) ^ { 2 } } ,\tag{5.1}
$$

where $\gamma _ { i }$ is set as the inverse Vega of the i-th option.

As mentioned above, the number of Monte Carlo samples is $n _ { \mathrm { M C } } = 8 0 0 { , } 0 0 0$ . Since computing the matrix $Q ( T )$ involves terms up to level $2 N + 1 = 7$ this requires evaluating signatures in a $2 ^ { 8 } - 1 = 2 5 5 .$ -dimensional space. That is, each $1 5 \times 1 5$ matrix $Q ( T )$ depends on a corresponding $2 5 5 \times 2 5 5$ matrix, making this step computationally intensive.

Calibration Results. The optimal coeficient vector minimizing $L ( \ell )$ is:

$$
\ell ^ { * } = ( 0 . 2 0 1 2 0 2 1 3 3 , \ 0 . 1 4 2 6 6 0 9 9 7 , \ 1 . 0 8 4 7 1 2 9 0 , \ - 0 . 2 9 7 3 1 2 3 7 8 , \ - 0 . 0 2 9 3 4 3 5 3 2 5 , \ - 0 . 0 4 2 2 3 1 7 1 8 7 , \ 0 . 0 2 2 2 1 2 7 1 8 7 2 8 )
$$

$$
9 . 2 5 0 9 0 1 6 2 \times 1 0 ^ { - 4 } , \ 0 . 2 9 3 1 0 3 6 8 7 , \ - 0 . 0 1 4 3 4 3 5 5 7 3 , \ - 0 . 0 1 3 4 2 8 5 6 5 2 , \ - 1 . 6 4 7 3 7 0 8 3 \times 1 0 ^ { - 3 } ,
$$

$$
- 2 . 8 9 8 8 3 0 9 2 \times 1 0 ^ { - 3 } , - 5 . 7 2 7 9 8 0 0 6 \times 1 0 ^ { - 4 } , - 1 . 9 3 0 4 5 4 2 0 \times 1 0 ^ { - 3 } , - 1 . 8 4 4 0 6 8 0 3 \times 1 0 ^ { - 4 } ) .
$$

Recall that

$$
\sigma _ { t } ( \ell ) = \ell _ { 0 } + \ell _ { 0 } t + \ell _ { 1 } X _ { t } + \ell _ { 0 0 } { \frac { t ^ { 2 } } { 2 } } + \ell _ { 0 1 } \int _ { 0 } ^ { t } s d X _ { s } + \ell _ { 1 0 } \int _ { 0 } ^ { t } X _ { s } d s + \ell _ { 1 1 } \int _ { 0 } ^ { t } X _ { s } d X _ { s } + \ell _ { 0 0 0 } { \frac { t ^ { 3 } } { 6 } } + \cdots .
$$

The coeficient $\ell _ { 1 } \approx 1$ .085 confirms that the model has learned a strong linear dependence on $X _ { t } ,$ consistent with the Heston structure. Likewise, $\ell _ { \varnothing } \approx 0 . 2 0 1$ is close to the initial volatility $\sigma _ { 0 } = 0 . 2$

The minimum value of the loss function $L ( \ell )$ obtained during calibration was $1 . 0 5 \times 1 0 ^ { - 4 }$ indicating a good fit to market prices. From the simulated option prices we compute the implied volatilities, which we denote by $\mathrm { \bar { I V } } ^ { \mathsf { S I G } }$ . Figure 5.1 shows a comparison between the two surfaces.

![Figure 5.1: Heston implied volatility surfaces: signature-based (SIG) and analytical approximation (ASV).](assets/figures/2025-alos-et-al-volatility-rough-paths-p0034-block-0017-667f515c3fb4a8b4.jpg)

<!-- page: 35 -->

To evaluate the quality of the calibration methods, we computed, for each of the 20 option contracts $( K _ { i } , T _ { i } )$ , the errors

$$
\begin{array} { r l } & { e _ { i } ^ { \mathsf { S I G } } = \Bigl | \mathrm { I V } ^ { \mathsf { S I G } } ( K _ { i } , T _ { i } ) - \mathrm { I V } ^ { \mathsf { m k t } } ( K _ { i } , T _ { i } ) \Bigr | } \\ & { e _ { i } ^ { \mathsf { A S V } } = \Bigl | \mathrm { I V } ^ { \mathsf { A S V } } ( K _ { i } , T _ { i } ) - \mathrm { I V } ^ { \mathsf { m k t } } ( K _ { i } , T _ { i } ) \Bigr | . } \end{array}
$$

A detailed breakdown is reported in Table 5.1, where entries marked with (∗) correspond to the cases in which $e ^ { \mathsf { S l G } } < e ^ { \mathsf { A S V } }$

[Table source crop](assets/tables/2025-alos-et-al-volatility-rough-paths-p0035-block-0004-0042106f3d9ce343.jpg)
Table 5.1: Calibration errors for the uncorrelated Heston model $( \rho = 0 )$

Both methods exhibit a high level of calibration accuracy, with most errors lying in the range of $1 0 ^ { - 4 } \ \mathrm { t o } \ 1 0 ^ { - 5 }$ , indicating that their performance is broadly comparable. While the analytica approach generally yields slightly smaller errors, there are several instances in which the signaturebased method performs better, as highlighted in the table. This confirms that the signaturebased approach is able to capture the structure of the implied volatility surface with a degree of accuracy comparable to model-based expansions, while maintaining its flexibility and modelagnostic nature.

## 5.2 The Correlated Case

We now consider the case when the asset price and the volatility process are correlated. Using the calibrated parameters from Table 2.2, we obtain the option prices and compute the implied volatility surface.

We let the primary Heston variance process X be initialized with parameters $X _ { 0 } ~ = ~ 0 . 2 5$ $\nu = 0 . 3 5 , \kappa = 3 . 3 , \theta = 0 . 1 5$ and $\rho = - 0 . 5$ , and we approximate the volatility by the truncated signature

$$
\sigma _ { t } ( \ell ) \approx \langle \ell , S ( { \mathbf { X } } ) _ { t } ^ { \le 3 } \rangle .
$$

The loss function remains as in (5.1). The optimal coeficient vector is

$$
\begin{array} { r l } & { \ell ^ { * } = \big ( - 0 . 1 9 5 1 5 8 2 1 2 , \ - 0 . 2 5 0 8 6 7 1 3 0 , \ - 0 . 1 2 5 1 9 5 7 8 5 , \ 0 . 6 0 6 1 1 3 8 4 7 , \ - 0 . 3 0 3 7 4 0 0 4 7 , } \\ & { \phantom { 2 . 2 5 0 } 0 . 3 4 7 5 8 0 9 2 6 , \ 0 . 1 3 6 8 1 6 3 8 2 , \ - 0 . 6 6 4 7 4 6 0 8 7 , \ 0 . 5 6 3 1 7 2 3 0 8 , \ 0 . 0 3 3 2 4 1 8 4 1 , } \\ & { \phantom { 2 . 2 5 0 } 0 . 0 2 9 3 7 6 9 8 2 , \ 0 . 0 1 9 2 4 0 5 9 3 , \ - 0 . 0 6 5 1 0 4 5 2 2 , \ 3 . 6 7 \times 1 0 ^ { - 5 } , \ - 8 . 9 4 \times 1 0 ^ { - 3 } \big ) . } \end{array}
$$

Whereas in the uncorrelated setting, the optimizer happened to find a parameterization close to the true process, in the correlated case it settled on a diferent (but still efective) minimizer.

<!-- page: 36 -->

The minimum value of the loss function L(ℓ) was $1 . 4 6 \times 1 0 ^ { - 3 }$ , slightly less precise than in the uncorrelated case. Figure 5.2 provides a visual comparison of the two calibrated surfaces.

![Figure 5.2: Implied volatility surfaces for the Heston model with correlation.](assets/figures/2025-alos-et-al-volatility-rough-paths-p0036-block-0002-f423a7407513cd74.jpg)

To assess calibration accuracy, we compute the absolute errors $e _ { i } ^ { \mathsf { S I G } }$ and $e _ { i } ^ { \mathsf { A S V } }$ for each of the 20 contracts $( K _ { i } , T _ { i } )$ . A detailed breakdown is provided in Table 5.2, where entries marked with (∗) correspond to the cases in which $e ^ { \mathsf { S I G } } < e ^ { \mathsf { A S V } }$

[Table source crop](assets/tables/2025-alos-et-al-volatility-rough-paths-p0036-block-0004-cb824209313b0e8b.jpg)
Table 5.2: Calibration errors for the Heston case $( \rho = - 0 . 5 )$

Both methods continue to exhibit a comparable level of accuracy, although the overall precision is slightly reduced in the presence of correlation, with most errors lying in the range of $1 0 ^ { - 4 }$ to $1 0 ^ { - 3 }$ . The analytical approach generally achieves smaller errors, with only a limited number of instances in which the signature-based method performs better. One possible explanation for this behavior is that the efect of negative correlation is encoded in higher-order interactions, which are only partially captured at the chosen truncation level of the signature (see Issa et al. (2023)). Increasing the truncation level to $N = 4$ yields only marginal improvements, suggesting that substantially higher-order terms may be required to fully capture the dependence structure, although at a significantly higher computational cost.

<!-- page: 37 -->

## 6 Calibration with a Rough Bergomi Primary Process

The signature-based method makes no structural assumptions about the market volatility, ofering greater flexibility and robustness. To demonstrate this flexibility, in this section we assume that the market is rough Bergomi and we use a fractional Brownian motion as primary process.

The asymptotic method in Section 2.1 is not suitable anymore because the information in the long-term maturities is not relevant for the rough Bergomi case. Instead, we rely on the algorithm described in Section 2.2, which exploits the short-maturity behavior of European options.

We first compute the market option prices and the option prices obtained with the calibrated parameters from Table 2.3. For the numerical techniques, see Bennedsen et al. (2017) and Mc-Crickerd and Pakkanen $( 2 0 1 8 ) . ^ { 3 }$ We then invert both set of prices to obtain the implied volatility surfaces, which we denote respectively by $\mathrm { I V } ^ { \mathsf { m k t } }$ and $\mathrm { I V } ^ { \mathsf { V I X } }$

We now compare the parametric calibration $\mathrm { I V } ^ { \mathsf { V I X } }$ with the one obtained via the signature method. Let $Z _ { t } = \rho W _ { t } + \sqrt { 1 - \rho ^ { 2 } } B _ { t }$ , where B is a Brownian motion independent of W. The model is:

$$
\begin{array} { r l } & { d \tilde { S } _ { t } ( \ell ) = \tilde { S } _ { t } ( \ell ) \sigma _ { t } ( \ell ) d Z _ { t } } \\ & { ~ \sigma _ { t } ( \ell ) \approx \langle \ell , S ( { \mathbf { X } } ) _ { t } ^ { \le 3 } \rangle , } \end{array}
$$

with primary process:

$$
X _ { t } = \sqrt { 2 H } \int _ { 0 } ^ { t } ( t - s ) ^ { H - { \frac { 1 } { 2 } } } d W _ { s } .\tag{6.1}
$$

Unlike the case of continuous semimartingales, where the Stratonovich integral naturally provides the rough path structure, the rough path lift of fractional Brownian motion must be constructed using techniques from Gaussian process theory. (See Friz and Hairer (2024), Chapter 10). In particular, Coutin and Qian (2002) show that fractional Brownian motion admits a canonica geometric rough path lift for any Hurst parameter $H > 1 / 4$

Remark 6.1. In Section 2.2, the market values are generated from a rough Bergomi model with $H = 0 . 1$ , while in the calibration below we use a primary process (6.1) with $H = 0 . 2$ . Both values lie below the theoretical threshold $H > 1 / 4$ . This does not pose a problem in practice: on the one hand, we work with the time-augmented path $\hat { X } _ { t } = ( t , X _ { t } )$ , where the bounded variation time component provides additional structure; on the other hand, signatures are computed from discrete samples of the path, which are interpolated linearly (see Section 4.3), and such piecewise linear approximations always admit a rough path lift.

With these considerations in mind, we first calibrate the model using (6.1) as the primary process, with parameters $H = 0 . 2$ and $\rho = - 0 . 6$ . Using a fractional Brownian motion directly as the primary process yields accurate results, but the calibration is computationally demanding, as the model must implicitly learn to enforce positivity of the variance.

Next, we consider the geometric transformation

$$
X _ { t } = \exp \left( \sqrt { 2 H } \int _ { 0 } ^ { t } ( t - s ) ^ { H - \frac { 1 } { 2 } } d W _ { s } \right) ,
$$

with the same values of H and $\rho .$ Although this smooth transformation does not remove the theoretical roughness constraint discussed in Remark 6.1, it improves the numerical performance and leads to more regular signature behavior. The total computation time (signature evaluation and parameter optimization) decreases from approximately 3 hours to 39 minutes, while achieving a comparable minimum value of the loss function (around $9 \times 1 0 ^ { - 4 } )$ .

As a third alternative, we consider a shifted exponential transformation

$$
X _ { t } = X _ { 0 } \exp \left( \sqrt { 2 H } \int _ { 0 } ^ { t } ( t - s ) ^ { H - \frac { 1 } { 2 } } d W _ { s } \right) ,
$$

<sup>3</sup>The code is available at https://github.com/ryanmccrickerd/rough\_bergomi

<!-- page: 38 -->

with an arbitrary initial value $X _ { 0 } = 0 . 1$ and the same values of H and $\rho .$ This specification ofers a further improvement in computational eficiency, with the full calibration procedure requiring only 17-19 minutes, and achieving a lower minimum value of the loss function $( 3 . 5 \times 1 0 ^ { - 4 } )$ , which indicates a better fit to market prices than the correlated Heston case. The corresponding optimal parameter vector is:

$$
\begin{array} { r l } & { \ell ^ { * } = ( 0 . 1 7 2 7 3 5 8 6 , \ : - 0 . 2 9 5 7 8 9 6 4 , \ : - 0 . 0 8 0 7 1 3 4 8 , \ : 0 . 4 0 1 0 1 5 7 3 , \ : - 0 . 2 9 7 4 6 4 7 , \ : 0 . 3 1 9 8 8 9 5 3 , \ : 1 . 4 0 1 5 8 4 1 1 , \ : } \\ & { 0 . 1 5 0 1 6 9 3 6 , \ : - 0 . 0 5 7 6 9 9 8 9 , \ : 0 . 0 0 9 9 9 1 7 3 , \ : 0 . 2 5 0 2 1 4 4 2 , \ : 0 . 0 2 9 9 8 3 3 2 , \ : - 0 . 0 0 7 8 9 5 6 2 , \ : 0 . 1 2 0 1 2 2 4 2 , \ : } \\ & { 0 . 2 7 1 0 2 2 5 2 ) . } \end{array}
$$

From the simulated option prices we compute the implied volatilities, which we now denote by $\mathrm { I V } ^ { \mathsf { V I X } }$ . Figure 6.1 shows the two surfaces

![Figure 6.1: Implied volatility surfaces for the rough Bergomi model.](assets/figures/2025-alos-et-al-volatility-rough-paths-p0038-block-0004-4a0880343a7d7ed0.jpg)

For all 20 option contracts $( K _ { i } , T _ { i } )$ , we compute the errors

$$
\begin{array} { r l } & { e _ { i } ^ { 5 | \mathsf { G } } = \Bigl | \mathrm { I V } ^ { 5 | \mathsf { G } } ( K _ { i } , T _ { i } ) - \mathrm { I V } ^ { \mathsf { m k t } } ( K _ { i } , T _ { i } ) \Bigr | } \\ & { e _ { i } ^ { \vee { 1 } \mathsf { X } } = \Bigl | \mathrm { I V } ^ { \vee { \mathrm { I X } } } ( K _ { i } , T _ { i } ) - \mathrm { I V } ^ { \mathsf { m k t } } ( K _ { i } , T _ { i } ) \Bigr | . } \end{array}
$$

A breakdown of the errors is provided in Table 6.1, where entries marked with (∗) correspond to the cases in which $e ^ { \mathsf { S I G } } < e ^ { \mathsf { V I X } }$

Both methods achieve a high level of calibration accuracy, with errors typically of order $1 0 ^ { - 4 } .$ indicating that the two approaches are broadly comparable in terms of precision. Note how the signature-based method outperforms the analytical approximation in a number of instances, as highlighted in the table, suggesting a slight advantage in this setting.

As in Section 5.2, we also increased the truncation level of the signature to $N = 4$ , but observed only marginal improvements, despite the additional computational cost. This indicates that the chosen truncation level already captures most of the relevant structure of the volatility surface.

A possible explanation for the improved performance of the signature-based approach with respect to the Heston case is the non-Markovian nature of the rough Bergomi model, driven by fractional Brownian motion. While analytical approximations rely on specific structural assumptions, the signature framework is naturally designed to encode temporal interactions, which may allow it to better represent such efects. Overall, these results further illustrate the robustness and adaptability of the signature-based approach in complex, non-Markovian volatility regimes.

<!-- page: 39 -->

[Table source crop](assets/tables/2025-alos-et-al-volatility-rough-paths-p0039-block-0001-809e3ad0661cf3bc.jpg)
Table 6.1: Calibration errors for the rough Bergomi case.

## 7 Conclusions

This paper provides a detailed comparison between two complementary approaches to the calibration of implied volatility surfaces: analytical approximations and data-driven models based on signatures of rough paths. Rather than viewing these methodologies in opposition, our analysis highlights how they address the calibration problem from diferent but compatible perspectives, each with its own strengths in terms of structure, flexibility, and computational cost.

The analytical approach builds on model-specific frameworks (namely, the Heston and rough Bergomi models) and derives explicit calibration formulas: asymptotic expansions for Heston, and a new VIX-based calibration scheme for rough Bergomi introduced in this paper. When the underlying dynamics are known, these methods provide highly accurate calibration in a lowdimensional setting at minimal computational cost.

The signature-based methodology does not rely on a fixed parametric specification. Volatility is modeled as a linear functional of the signature of a primary process, which can be chosen to reflect diferent features of the data. This flexibility allows the method to adapt to a wide range of dynamics, including non-Markovian settings. In the Heston case, the signature-based model achieves a calibration accuracy comparable to the analytical approach, with the globa optimization error over the whole implied volatility surface typically below 10<sup>−3</sup>.

When using a fractional Brownian motion as the primary process in a rough Bergomi setting, the calibration remains highly accurate, with global implied volatility errors consistently of order 10<sup>−4</sup>. The performance is slightly improved compared to the Heston-based specification, which may be attributed to the non-Markovian nature of fractional Brownian motion and the ability of signatures to capture such temporal dependencies efectively. These results further illustrate the robustness and adaptability of the signature-based approach in complex volatility regimes.

From a computational perspective, the analytical approximations are essentially instantaneous once derived, making them particularly attractive when the underlying model is specified. The signature-based approach, while more computationally demanding, remains practical. With 100,000 simulated paths, the full calibration (including signature computation and optimization) takes approximately 15 minutes. Increasing the number of paths to 800,000 improves accuracy at the cost of longer runtimes, between 45 and 90 minutes, depending on the model. This reflects a natural trade-of between precision and computational efort, and the method can be tuned according to the desired level of accuracy.

In summary, analytical methods provide an optimal solution when the model is correctly specified, combining precision and eficiency. Signature-based models, on the other hand, ofer a robust and flexible alternative that performs well across diferent dynamics, particularly in non-

<!-- page: 40 -->

Markovian settings. Together, these approaches balance model-driven insights with data-driven adaptability, opening promising directions for future research.

## References

Alòs, E., De Santiago, R., and Vives, J. (2015). Calibration of stochastic volatility models via second-order approximation: The Heston case. International Journal of Theoretical and Applied Finance, 18(06):1550036. Alòs, E. and Garcia Lorite, D. (2025). Malliavin calculus in finance—theory and practice. Chapman & Hall/CRC Financial Mathematics Series. CRC Press, Boca Raton, FL. Second edition [of 4701113], With a foreword by Dariusz Gatarek. Alòs, E., García-Lorite, D., and Muguruza, A. (2022). On smile properties of volatility derivatives: Understanding the vix skew. SIAM Journal on Financial Mathematics, 13(1):32–69. Alòs, E., León, J., and Vives, J. (2007). On the short-time behavior of the implied volatility for jump-difusion models with stochastic volatility. Finance and Stochastics, 11:571–589. Alòs, E., Nualart, E., and Pravosud, M. (2024). On the implied volatility of european and asian call options under the stochastic volatility bachelier model. International Journal of Theoretical and Applied Finance, 27(7-8):1–28. Alòs, E. (2012). A decomposition formula for option prices in the Heston model and applications to option pricing approximation. Finance and Stochastics, 16(3):403–422. Antonelli, F. and Scarlatti, S. (2009). Pricing options under stochastic volatility: A power series approach. Finance and Stochastics, 13(2):269–303. Arribas, I. P., Salvi, C., and Szpruch, L. (2020). Sig-SDEs model for quantitative finance. https: //arxiv.org/abs/2006.00218. Bayer, C., Friz, P., and Gatheral, J. (2016). Pricing under rough volatility. Quantitative Finance, 16(6):887–904. Bayer, C., Hager, P. P., Riedel, S., and Schoenmakers, J. (2023). Optimal stopping with signatures. The Annals of Applied Probability, 33(1):238–273. Benhamou, E., Gobet, E., and Miri, M. (2009). Smart expansion and fast calibration for jump difusion. Finance and Stochastics, 13(4):563–589. Benhamou, E., Gobet, E., and Miri, M. (2010a). Expansion formulas for European options in a local volatility model. International Journal of Theoretical and Applied Finance, 13(4):603–634. Benhamou, E., Gobet, E., and Miri, M. (2010b). Time dependent Heston model. SIAM Journal on Financial Mathematics, 1:289–325. Bennedsen, M., Lunde, A., and Pakkanen, M. S. (2017). Hybrid scheme for brownian semistationary processes. Finance and Stochastics, 21(4):931–965. Bruned, Y., Hairer, M., and Zambotti, L. (2019). Algebraic renormalisation of regularity structures. Inventiones mathematicae, 215(3):1039–1156. Bühler, H., Horvath, B., Lyons, T., Arribas, I. P., and Wood, B. (2020). Generating financial markets with signatures. SSRN Electronic Journal. Available at SSRN: https://ssrn.com/ abstract=3657366. Chen, K.-T. (1957). Integration of paths, geometric invariants and a generalized Baker–Hausdorf formula. Annals of Mathematics, 65(1):163–178.

<!-- page: 41 -->

Chevyrev, I. and Kormilitzin, A. (2016). A primer on the signature method in machine learning. https://arxiv.org/abs/1603.03788. Comte, F. and Renault, E. (1998). Long memory in continuous-time stochastic volatility models. Mathematical Finance, 8(04):291–323. Coutin, L. and Qian, Z. (2002). Stochastic analysis, rough path analysis and fractional brownian motions. Probability Theory and Related Fields, 122(1):108–140. Cuchiero, C., Gazzani, G., Möller, J., and Svaluto-Ferro, S. (2025). Joint calibration to SPX and VIX options with signature-based models. Mathematical Finance, 35(1):161–213. Cuchiero, C., Gazzani, G., and Svaluto-Ferro, S. (2023). Signature-based models: Theory and calibration. SIAM Journal on Financial Mathematics, 14(3):910–957. De Santiago, R., Fouque, J. P., and Sølna, K. (2008). Bond markets with stochastic volatility. Advances in Econometrics, 22:215–242. Díaz, P. (2023). Rough volatility models using the signature transform: Theory and calibration. Master’s dissertation, Universitat de Barcelona. Supervisor: J. Vives. Fermanian, A. (2021). Learning Time-Dependent Data with the Signature Transform. Thèse de doctorat, Sorbonne Université. Discipline: Mathématiques appliquées, Spécialité: Statistique. Forde, M. and Jacquier, A. (2011). The large-maturity smile for the Heston model. Finance and Stochastics, 15(4):775–780. Forde, M., Jacquier, A., and Lee, R. (2011). The small-time smile and term structure of implied volatility under the Heston model. SIAM Journal on Financial Mathematics, 3(1):690–708. Forde, M., Jacquier, A., and Mijatović, A. (2010). Asymptotic formulae for implied volatility in the Heston model. Proceedings of the Royal Society A, 466(2124):3593–3620. Fouque, J. P., Papanicolaou, G., Sircar, K. R., and Sølna, K. (2003). Singular perturbations in option pricing. SIAM Journal of Applied Mathematics, 63(5):1648–1665. Friz, P. K. and Hairer, M. (2024). A Course on Rough Paths: With an Introduction to Regularity Structures. Universitext. Springer, 2nd, updated march 2024 edition. Last update: March 3, 2024. Friz, P. K. and Victoir, N. B. (2010). Multidimensional Stochastic Processes as Rough Paths: Theory and Applications, volume 120 of Cambridge Studies in Advanced Mathematics. Cambridge University Press, Cambridge. Fukasawa, M. (2017). Short-time at-the-money skew and rough fractional volatility. Quantitative Finance, 17(02):189–198. Gatheral, J., Jaisson, T., and Rosenbaum, M. (2018). Volatility is rough. Quantitative Finance, 18(6):933–949. Geng, X. (2021). An introduction to the theory of rough paths. Lecture notes, University of Melbourne, August 2021. Available at Xi Geng’s website. Hagan, P. S., Kumar, D., Lesniewski, A., and Woodward, D. E. (2002). Managing smile risk. Willmot Magazine, 15:84–108. Heston, S. L. (1993). A closed-form solution for options with stochastic volatility with applications to bond and currency options. Review of Financial Studies, 6(2):327–343. Hull, J. and White, A. (1987). The pricing of options on assets with stochastic volatilities. Journal of Finance, 42:281–300.

<!-- page: 42 -->

Issa, Z., Horvath, B., Lemercier, M., and Salvi, C. (2023). Non-adversarial training of Neural SDEs with signature kernel scores. In Advances in Neural Information Processing Systems (NeurIPS), volume 37, pages 11102–11126. Curran Associates, Inc. Kalsi, J., Lyons, T., and Perez Arribas, I. (2020). Optimal execution with rough path signatures. SIAM Journal on Financial Mathematics, 11(2):470–493. Lorig, M., Pagliarani, S., and Pascucci, A. (2013). Explicit implied volatilities for multifactor local-stochastic volatility models. SSRN Electronic Journal. Available at SSRN: https:// ssrn.com/abstract=2283874. Lyons, T. and Qian, Z. (2002). System control and rough paths. Oxford University Press. Lyons, T. J. (1998). Diferential equations driven by rough signals. Revista Matemática Iberoamericana, 14(2):215–310. Lyons, T. J., Caruana, M., and Lévy, T. (2007). Diferential Equations Driven by Rough Paths, volume 1908 of Lecture Notes in Mathematics. Springer. Ecole d’Eté de Probabilités de Saint-Flour XXXIV-2004. McCrickerd, R. and Pakkanen, M. S. (2018). Turbocharging monte carlo pricing for the rough bergomi model. Quantitative Finance, 18(11):1877–1886. Medvedev, A. and Scaillet, O. (2007). Approximation and calibration of short-term implied volatilities under jump-difusion stochastic volatility. Review of Financial Studies, 20(02):427–459. Stein, E. M. and Stein, J. C. (1991). Stock price distributions with stochastic volatility: An analytic approach. The Review of Financial Studies, 4:727–752. Wiggins, J. (1987). Option values under stochastic volatilities. Journal of Financial Economics, 19:351–372. Young, L. C. (1936). An inequality of the Hölder type, connected with Stieltjes integration. Acta Mathematica, 67:251 – 282.
