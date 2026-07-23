# 2023-cuchiero-et-al-signature-spx-vix

<!-- page: 1 -->

## Joint calibration to SPX and VIX options with signature-based models

Christa Cuchiero<sup>∗</sup> Guido Gazzani<sup>†</sup> Janka M¨oller<sup>‡</sup> Sara Svaluto-Ferro<sup>§</sup>

July 24, 2024

## Abstract

We consider a stochastic volatility model where the dynamics of the volatility are described by a linear function of the (time extended) signature of a primary process which is supposed to be a polynomial difusion. We obtain closed form expressions for the VIX squared, exploiting the fact that the truncated signature of a polynomial difusion is again a polynomial difusion. Adding to such a primary process the Brownian motion driving the stock price, allows then to express both the log-price and the VIX squared as linear functions of the signature of the corresponding augmented process. This feature can then be eficiently used for pricing and calibration purposes. Indeed, as the signature samples can be easily precomputed, the calibration task can be split into an ofline sampling and a standard optimization. We also propose a Fourier pricing approach for both VIX and SPX options exploiting that the signature of the augmented primary process is an infinite dimensional afine process. For both the SPX and VIX options we obtain highly accurate calibration results, showing that this model class allows to solve the joint calibration problem without adding jumps or rough volatility.

Keywords: signature methods, calibration of financial models, afine and polynomial processes, S&P 500/VIX joint calibration MSC (2020) Classification: 91B70, 62P05, 65C20.

## Contents

1 Introduction 2 1.1 State of the art . . . 5 3 The model 9 4 Expected signature of polynomial difusion 12 5 VIX options with signatures 16 5.1 Explicit formulas for the VIX 16 5.2 Variance reduction for pricing VIX options 20 5.3 Calibration to VIX options 22 5.3.1 Numerical results . 23 5.4 The case of time-varying parameters 26 6 SPX as a signature-based model 27 6.1 Exploiting the afine nature of the signature: Fourier pricing of SPX and VIX options . 31 6.2 The case of time-varying parameters 33 7 Joint calibration of SPX and VIX options 34 7.1 Numerical results . 35 7.1.1 First approach 36 7.1.2 Second approach . 40 A Numerical results for the Brownian motion case 41 B On the stability of the calibrated parameters 43

arXiv:2301.13235v2 [q-fin.MF] 23 Jul 2024

<sup>∗</sup>Vienna University, Department of Statistics and Operations Research, Data Science Uni Vienna, Kolingasse 14-16 1, A-1090 Wien, Austria, christa.cuchiero@univie.ac.at

<sup>†</sup>University of Verona, Department of Economics, Via Cantarane 24, 37129 Verona, Italy, guido.gazzani@univr.it

<sup>‡</sup>Vienna University, Department of Statistics and Operations Research, Kolingasse 14-16 1, A-1090 Wien, Austria, janka.moeller@univie.ac.at

<sup>§</sup>University of Verona, Department of Economics, Via Cantarane 24, 37129 Verona, Italy, sara.svalutoferro@univr.it.

The first three authors gratefully acknowledge financial support through grant Y 1235 and grant I 3852 of the Austrian Science Fund. All authors acknowledge financial support through the OEAD WTZ project FR 02/2022. The present work was initiated when the second author was afiliated to the University of Vienna (ISOR)).

We also thank the anonymous referees and associated editor for their valuable comments and suggestions.

<!-- page: 2 -->

## 1 Introduction

The joint calibration of option pricing models to SPX and $\mathrm { V I X ^ { 1 } }$ options is a problem that has gained a lot of attention in quantitative finance since several years. One main reason for the increased interest is that the VIX index has become an important underlying for many derivatives. In fact, futures and options written on it are extensively used to hedge the volatility exposure of option portfolios, see $\mathrm { e . g . }$ , Rhoads (2011). We address the reader to the oficial website of CBOE<sup>2</sup> for details on the history of the VIX, how it is computed, traded and used as underlying for derivatives, which emphasizes in particular the need to jointly calibrate to both, the prices of options on the S&P 500 index and to prices of VIX derivatives. In this respect the main challenge is to reconcile the large negative skew of SPX options’ implied volatilities with relatively lower implied volatilities arising from the VIX options, especially for short maturities (see e.g., Guyon (2020a).

Inspired by Perez Arribas et al. (2020) and Cuchiero et al. (2023a), we consider here a new type of stochastic volatility model for the discounted, dividend-adjusted price process $S = ( S _ { t } ) _ { t \geq 0 }$ . It is given by

$$
\mathrm { d } S _ { t } ( \ell ) = S _ { t } ( \ell ) \sigma _ { t } ^ { S } ( \ell ) \mathrm { d } B _ { t } ,
$$

for an initial condition $S _ { 0 } \in \mathbb { R } _ { + }$ , a standard Brownian motion $B ,$ and a volatility process $\sigma ^ { S }$ satisfying

$$
\sigma _ { t } ^ { S } ( \ell ) : = \ell ( \widehat { \mathbb { X } } _ { t } ) ,\tag{1.1}
$$

<sup>1</sup>With SPX and VIX we refer to the index tickers of the S&P 500 and its volatility index, respectively. In the sequel we will use SPX and S&P 500 interchangeably.

<sup>2</sup>www.cboe.com/tradable products/vix/

<!-- page: 3 -->

where ℓ is a linear map of the signature $\widehat { \mathbb X } _ { t }$ of a process $\widehat { X }$ . Specifically, the main ingredient in this framework is a d-dimensional polynomial difusion process $X = ( X _ { t } ^ { 1 } , \ldots , X _ { t } ^ { d } ) _ { t \geq 0 }$ (see Cuchiero et al. (2012); Filipovi´c and Larsson (2016)), which we call here primary process and whose augmentation with time t is denoted by $( \widehat { X } _ { t } ) _ { t \geq 0 } = ( t , X _ { t } ^ { 1 } , \ldots , X _ { t } ^ { d } ) _ { t \geq 0 }$ . By modeling $\sigma ^ { S }$ via (1.1) we assume that the signature of $\widehat { X }$ , denoted by $\widehat { \mathbb X }$ (and rigorously introduced in Section 2), serves as a linear regression basis for the volatility process, while the parameters of the linear map ℓ have to be learned from (option price) data. Note that the parameters of X are prespecified beforehand and can thus be seen – in analogy to machine learning terminology – as hyperparameters (that of course can be optimized over some validation set). As outlined below this is one of the crucial features that allows for the split of the calibration task into precomputable samples and parameters ℓ to be optimized.

Let us now highlight the implications of this modeling approach and the novelty of the present work.

• The current framework can be seen as universal in a large class of continuous (nonrough) stochastic volatility models in the following sense: for a stochastic volatility model, whose volatility is given by a continuous path-functional depending on a polynomial difusion $( X _ { t } ) _ { t \geq 0 }$ , it follows from Proposition 2.3 that this path-functional can be approximated by a linear function of the signature of $( \widehat { X } _ { t } ) _ { t \geq 0 }$ . A concrete example for a volatility process of such a form is an Itˆo-difusion with suficiently regular coefficients, as in this case, the volatility is indeed given by a continuous path-functional of the time-augmented Brownian motion driving the difusion.

• Additionally, our model truly nests several classical models (see Remark 3.4) and for instance also the ‘quintic Ornstein-Uhlenbeck volatility model’, recently proposed by Abi Jaber et al. (2022b), which – with an additional input curve – is shown to fit SPX and VIX smiles well.

• By choosing the parameters of ℓ appropriately, the modeling framework incorporates both, Markovian (in (S, X)) and path-dependent models.

• Up to our knowledge, it is the first signature-based model that is employed for pricing and calibration of VIX options as well as joint calibration, together with SPX options.

• We illustrate that the joint calibration problem can be solved in this framework without jumps and rough volatility (compare also Rømer (2022); Abi Jaber et al. (2022b); Guyon and Lekeufack (2023)).

• By using time-varying parameters we can go beyond short maturities both for SPX and VIX options (as classically tackled in the literature) and achieve a joint calibration also for longer maturities.

In order to achieve the highly accurate calibration results, illustrated in Section 5.3 and Section 7, we exploit the following mathematical and numerical properties.

• Defining $Z : = ( X , B )$ , then not only $\sigma ^ { S } ( \ell )$ but also the log-price $\log ( S ( \ell ) )$ can be expressed as a linear function of the signature of $\widehat { Z }$ . The computational benefit is immediate, since no (Euler) simulation scheme is needed to sample from the marginals of the price process. In terms of the parameters $\ell , \log ( S ( \ell ) )$ is the sum of a quadratic function and a linear one, see Proposition 6.4.

<!-- page: 4 -->

• Since Xb is additionally assumed to be a polynomial difusion (see Cuchiero et al. (2012); Filipovi´c and Larsson (2016)), the VIX under our model can be computed analytically via matrix exponentials. Indeed, in this case the forward variance can be represented by a quadratic form in the parameters ℓ and the corresponding matrix can be computed by polynomial technology, i.e. via matrix exponentials, see Theorem 5.1. This tractability property is a consequence of the fact that the truncated signature of a polynomial difusion is again a polynomial difusion (see Section 4).

• We can eficiently apply a Monte Carlo approach (potentially with variance reduction) for option pricing and calibration, since the signature samples of Zb can be computed ofline and therefore the simulation and optimization step can be completely separated. Indeed, due to the representations of VIX and log(S(ℓ)) described above, the same samples can be used for every linear map ℓ. Therefore, the calibration task can be split into an ofline sampling and a standard optimization, as no simulation is needed during the latter. Moreover, due to the fact that we can obtain a closed-form expression for the VIX (thanks to the polynomial technology) we can avoid a nested Monte Carlo procedure to evaluate the conditional expectation.

• Alternatively, a Fourier pricing approach for both VIX and SPX options can be used. Indeed, by building on the fact that the signature of Zb is an afine process (with values in the extended tensor algebra) as proved in Cuchiero et al. (2023b), its Fourier-Laplace transform can be computed by solving an (extended tensor algebra valued) Riccati equation, which in turn can be used for Fourier pricing as outlined in Section 6.1.

The remainder of the paper is organized as follows. Section 1.1 gives a review over the different contributions in the literature concerning the joint calibration problem. In Section 2 we introduce the signature in the context of continuous semimartingales, its main properties as well as notation used throughout the paper. Section 3 is dedicated to the introduction of our signature-based model and the connections to classical and also recent stochastic volatility models in the literature. Section 4 is then devoted to the discussion and proof of the matrix exponential formula for the (conditional) truncated expected signature of a polynomial difusion. This result is at the core of Section 5, where we derive a tractable formula for the VIX, needed for pricing VIX options and VIX futures. Building on these formulas, our calibration results to VIX options are presented in Section 5.3.1. In Section 6, we then prove, similarly as for the VIX, a tractable expression for S. Additionally, we exploit in Section 6.1 the afine nature of the signature process (as proved in Cuchiero et al. (2023b)), to obtain a Fourier pricing approach within our modeling choice for both VIX and SPX options. We finally present the numerical results of the joint calibration problem in Section 7, both in the case of constant parameters and with time-varying parameters, where the latter are introduced in Section 5.4 and Section 6.2.

The data used in Section 5.3.1 and Section 7.1 were purchased from OptionMetrics<sup>3</sup>. An implementation of the model for the joint calibration can be found in GuidoGazzaniai/jointcalib sigsde or janka-moeller/joint calib SPX VIX.

<sup>3</sup>https://optionmetrics.com/

<!-- page: 5 -->

## 1.1 State of the art

This section is primarily dedicated to a literature review on the joint calibration problem and secondly, to a brief overview on signature methods in finance.

First attempts to solve the joint calibration problem appear in Gatheral (2008), with a double constant elasticity of variance model (CEV), which despite being rather flexible cannot fit accurately the implied volatilities of SPX and VIX options jointly. Later on, the introduction of models with jumps in the SPX (or additionally also in the volatility) led to diferent contributions, for instance the forward variance model of Cont and Kokholm (2013) described as an exponential of an afine process with L´evy jumps, the regime-switching enhancement of the classical Heston model by Papanicolaou and Sircar (2014), the 3/2 model with jumps in the asset price of Baldeaux and Badran (2014), in the volatility (Kokholm and Stisen (2015)), or with co-jumps and idiosyncratic jumps in the volatility (Pacati et al. (2018)).

Continuous stochastic volatility models based on Markovian semimartingales have also been employed to solve the joint calibration problem. For instance, in Fouque and Saporito (2018) a Heston model with stochastic vol-of-vol has been calibrated, however only for maturities above 4 months where VIX options are less liquid. More recently, Rømer (2022) considered a model where the volatility is driven by two Ornstein-Uhlenbeck (OU) processes using a non-standard transformation function. This choice of two OU-processes has been an inspiration for our concrete numerical implementations. We also point out that the (nonrough) model introduced in Abi Jaber et al. (2022a,b), where the volatility is described by a polynomial of order five in one single OU-process, falls (apart from the additional input curve) into this class of continuous Markovian models and is a particular instance of our framework. Let us also refer to the paper by Guyon and Mustapha (2023), where a neural SDE model has been successfully jointly calibrated. Within the class of continuous, however not necessarily Markovian models, Guyon and Lekeufack (2023) conduct an empirical and statistical analysis as well as a joint calibration for a family of models where the volatility depends on the paths of the asset. These models can be turned into Markovian ones by using exponential kernels instead of general ones, see also Gazzani and Guyon (2024) for their joint calibration.

Two further distinct lines of research are worth being mentioned as well: first, martingale optimal transport and second rough volatility.

The martingale optimal transport approach is used to calibrate discrete-time models as proposed in Guyon (2020b, 2023). These models are closely related to Schr¨odinger bridge problems, where the idea is to calibrate only the drift of the volatility while keeping the volatility of volatility unchanged, see e.g. Guo et al. (2022a) as well as the references therein regarding an optimal transport approach. Although the calibration within that setting is accurate, it is also computationally rather expensive and not amenable to calibrate to several maturities jointly. These computational challenges have been tackled recently in Bourgey and Guyon (2022).

In the area of rough volatility modeling, initiated by the seminal paper of Gatheral et al. (2018), the main idea is to replace the standard Brownian motion in the volatility process by a fractional Brownian motion. Even though the roughness of the trajectories found in Gatheral et al. (2018), can also be related to the estimation procedure as discussed e.g. in Cont and Das (2023), the non-Markovianity given by the fractional Brownian motion with Hurst parameter H < 0.5, is well-suited to reproduce certain stylized facts arising in financial data, e.g. volatility persistence or multiple scales of mean reversion; see Bayer et al. (2016). Several classical models have been enhanced with rougher noise, but for simplicity we here only mention those employed in the SPX/VIX calibration. One example is the quadratic rough Heston model introduced in Gatheral et al. (2020), which was in turn calibrated in Rosenbaum and Zhang (2021) by relying on neural networks approaches, also exploited in e.g. Bayer et al. (2019). In Rømer (2022) an exhaustive study of the flexibility of diferent rough and non-rough volatility models for the joint SPX/VIX calibration is carried out, including the rough Bergomi and the rough Heston model. Some of these, for instance the rough Heston model, have an afine structure i.e., can be embedded in the class of afine Volterra processes. In particular they allow for Fourier pricing after solving the related fractional Riccati equations. This underlying structure is the building block of an extension with jumps investigated in Bondi et al. (2024a,b). We refer additionally to Di Nunno et al. (2023); Gazzani and Guyon (2024) for a very recent literature review on volatility modeling.

<!-- page: 6 -->

Concerning our framework, signature-based methods provide a generic non-parametric way to extract characteristic features (linearly) and path-dependency from data, which is essential in (machine) learning and calibration tasks in finance. This explains why these techniques become more and more popular in mathematical finance, see e.g., Buehler et al. (2020); Kalsi et al. (2020); Perez Arribas et al. (2020); Lyons et al. (2020); Liao et al. (2023); Bayer et al. (2023); Min and Hu (2021); Cuchiero et al. (2024b); Cuchiero and M¨oller (2023); Akyildirim et al. (2023); Ning et al. (2023); Wiese et al. (2023); Cohen et al. (2023); Lemahieu et al. (2023) and the references therein.

## 2 Signature: definition and properties

We start by introducing basic notions related to the definition of the signature of an $\mathbb { R } ^ { d _ { - } }$ valued continuous semimartingale. This is similar as in Cuchiero et al. (2023a) or Bayer et al. (2023), but to keep the paper self-contained we recall the essential definitions and properties.

For each $n \in { \mathbb { N } } _ { 0 }$ we define recursively the n-fold tensor product of $\mathbb { R } ^ { d }$

$$
( \mathbb { R } ^ { d } ) ^ { \otimes 0 } : = \mathbb { R } , \qquad ( \mathbb { R } ^ { d } ) ^ { \otimes n } : = \underbrace { \mathbb { R } ^ { d } \otimes \dots \otimes \mathbb { R } ^ { d } } _ { n } .
$$

For d $\in \mathbb { N }$ , we define the extended tensor algebra on $\mathbb { R } ^ { d }$ as

$$
\begin{array} { r } { T ( ( \mathbb { R } ^ { d } ) ) : = \{ \mathbf { a } : = ( a _ { 0 } , \ldots , a _ { n } , \ldots ) : a _ { n } \in ( \mathbb { R } ^ { d } ) ^ { \otimes n } \} . } \end{array}
$$

Similarly we introduce the truncated tensor algebra of order $n \in \mathbb { N }$

$$
\begin{array} { r } { T ^ { ( n ) } ( \mathbb { R } ^ { d } ) : = \lbrace \mathbf { a } \in T ( ( \mathbb { R } ^ { d } ) ) : a _ { m } = 0 , \forall m > n \rbrace , } \end{array}
$$

and the tensor algebra $\begin{array} { r } { T ( \mathbb { R } ^ { d } ) : = \bigcup _ { n \in \mathbb { N } } T ^ { ( n ) } ( \mathbb { R } ^ { d } ) } \end{array}$ . Note that $T ^ { ( n ) } ( \mathbb { R } ^ { d } )$ has dimension

$$
d _ { n } : = ( d ^ { n + 1 } - 1 ) / ( d - 1 ) .\tag{2.1}
$$

For each a, b $\in T ( ( \mathbb { R } ^ { d } ) )$ and $\lambda \in \mathbb { R }$ we set

$$
\begin{array} { r l } & { \mathbf { a } + \mathbf { b } : = ( a _ { 0 } + b _ { 0 } , \ldots , a _ { n } + b _ { n } , \ldots ) , } \\ & { \quad \lambda \cdot \mathbf { a } : = ( \lambda a _ { 0 } , \ldots , \lambda a _ { n } , \ldots ) , } \\ & { \mathbf { a } \otimes \mathbf { b } : = ( c _ { 0 } , \ldots , c _ { n } , \ldots ) , } \end{array}
$$

<!-- page: 7 -->

where $\begin{array} { r } { c _ { n } : = \sum _ { k = 0 } ^ { n } a _ { k } \otimes b _ { n - k } } \end{array}$ . Observe that $( T ( ( \mathbb { R } ^ { d } ) ) , + , \cdot , \otimes )$ is a real non-commutative algebra.

For a multi-index $I : = ( i _ { 1 } , \ldots , i _ { n } )$ we set $| I | : = n$ . We also consider the empty index $I : = \emptyset$ and set $\vert I \vert : = 0$ . If $n \geq 1$ or $n \geq 2$ we set $I ^ { \prime } : = ( i _ { 1 } , \dots , i _ { n - 1 } )$ , and $I ^ { \prime \prime } : = ( i _ { 1 } , \dotsc , i _ { n - 2 } )$ respectively. We also use the notation

$$
\{ I \colon | I | = n \} : = \{ 1 , \ldots , d \} ^ { n } ,
$$

omitting the parameter d whenever this does not introduce ambiguity. Observe that multiindices can be identified with words, as it is done for instance in Lyons et al. (2020).

Next, for each $| I | \geq 1$ we set

$$
e _ { I } : = e _ { i _ { 1 } } \otimes \cdot \cdot \cdot \otimes e _ { i _ { n } } .
$$

Observe that the set $\{ e _ { I } \colon | I | = n \}$ is an orthonormal basis of $( \mathbb { R } ^ { d } ) ^ { \otimes n }$ . Denoting by $e _ { \emptyset }$ the basis element corresponding to $( \mathbb { R } ^ { d } ) ^ { \otimes 0 }$ , each element of $\mathbf { a } \in T ( ( \mathbb { R } ^ { d } ) )$ can thus be written as

$$
\mathbf { a } = \sum _ { | I | \geq 0 } \mathbf { a } _ { I } e _ { I } ,
$$

for some ${ \mathbf a } _ { I } \in \mathbb { R }$ . Note that if $a _ { n } \in ( \mathbb { R } ^ { d } ) ^ { \otimes n }$ we use non-bold notation whereas for the components $\mathbf { a } _ { I } \in \mathbb { R }$ we write them bold. Finally, for each $\mathbf { a } \in T ( { \mathbb { R } } ^ { d } )$ and each $ { \mathbf { b } } \in T ( ( { \mathbb { R } } ^ { d } ) )$ 1 we set

$$
\langle \mathbf { a } , \mathbf { b } \rangle : = \sum _ { | I | \geq 0 } \langle \mathbf { a } _ { I } , \mathbf { b } _ { I } \rangle .
$$

Observe in particular that $\mathbf { b } _ { I } = \langle e _ { I } , \mathbf { b } \rangle$

In the present work it will be useful to enumerate the elements of the truncated tensor algebra. To this extent we introduce the isomorphism vec : $T ^ { ( n ) } ( \mathbb { R } ^ { d } ) \mathbb { R } ^ { d _ { n } }$ and an injective labeling function $\mathcal { L } : \{ I : | I | \leq n \} \longrightarrow \{ 1 , \dots , d _ { n } \}$ , such that

$$
\mathbf { v e c } ( \mathbf { u } ) : = \sum _ { | I | \leq n } e _ { \mathcal { L } ( I ) } \mathbf { u } _ { I } ,\tag{2.2}
$$

where $d _ { n }$ is as in (2.1).

Throughout the paper we fix a filtered probability space $( \Omega , \mathcal { F } , ( \mathcal { F } _ { t } ) _ { t \geq 0 } , \mathbb { Q } )$ on which we consider the stochastic processes to be defined. We are now ready to introduce the signature of an $\mathbb { R } ^ { d } .$ -valued continuous semimartingale.

Definition 2.1. Let X be a continuous $\mathbb { R } ^ { d } .$ -valued semimartingale with $d \geq 1$ . The signature of X is the $T ( ( \mathbb { R } ^ { d } ) )$ )-valued process $( s , t ) \mapsto \mathbb { X } _ { s , t }$ whose components are recursively defined as

$$
\langle e _ { \emptyset } , { \mathbb X } _ { s , t } \rangle : = 1 , \qquad \langle e _ { I } , { \mathbb X } _ { s , t } \rangle : = \int _ { s } ^ { t } \langle e _ { I ^ { \prime } } , { \mathbb X } _ { s , r } \rangle \circ \mathrm { d } X _ { r } ^ { i _ { n } } ,
$$

for each $I = \left( i _ { 1 } , \ldots , i _ { n } \right) , I ^ { \prime } = \left( i _ { 1 } , \ldots , i _ { n - 1 } \right)$ and $0 \leq s \leq t$ , where ◦ denotes the Stratonovich integral. Its projection $\mathbb { X } ^ { n }$ on $T ^ { ( n ) } ( \mathbb { R } ^ { d } )$ is given by

$$
\mathbb { X } _ { s , t } ^ { n } = \sum _ { | I | \leq n } \langle e _ { I } , \mathbb { X } _ { s , t } \rangle e _ { I }
$$

and is called signature of X truncated at level n. If $s = 0$ , we use the notation $\mathbb { X } _ { t }$ and ${ \mathbb X } _ { t } ^ { n }$ respectively.

<!-- page: 8 -->

Observe that the signature of X and the signature of $X - c$ coincide for each $c \in \mathbb { R }$ Moreover, with an equivalent notation we can write

$$
\begin{array} { r l } & { \mathbb { X } _ { t } = \bigg ( 1 , \displaystyle \int _ { 0 } ^ { t } 1 \circ \mathrm { d } X _ { s } ^ { 1 } , \ldots , \displaystyle \int _ { 0 } ^ { t } 1 \circ \mathrm { d } X _ { s } ^ { d } , \displaystyle \int _ { 0 } ^ { t } \left( \displaystyle \int _ { 0 } ^ { s } 1 \circ \mathrm { d } X _ { r } ^ { 1 } \right) \circ \mathrm { d } X _ { s } ^ { 1 } , } \\ & { \qquad \displaystyle \int _ { 0 } ^ { t } \left( \displaystyle \int _ { 0 } ^ { s } 1 \circ \mathrm { d } X _ { r } ^ { 1 } \right) \circ \mathrm { d } X _ { s } ^ { 2 } , \ldots , \displaystyle \int _ { 0 } ^ { t } \left( \displaystyle \int _ { 0 } ^ { s } 1 \circ \mathrm { d } X _ { r } ^ { d } \right) \circ \mathrm { d } X _ { s } ^ { d } , \ldots \bigg ) . } \end{array}
$$

A well-known and extremely useful property of the signature is that every polynomial function in the signature has a linear representation. For the precise statement we first need to introduce the following concept (see also Definition 2.4 in Lyons et al. (2020) or Section 2.2. in Bayer et al. (2023)).

Definition 2.2. For every two multi-indices I and J the shufle product is defined recursively as

$$
e _ { I } \sqcup e _ { J } : = ( e _ { I ^ { \prime } } \sqcup e _ { J } ) \otimes e _ { i _ { | I | } } + ( e _ { I } \sqcup e _ { J ^ { \prime } } ) \otimes e _ { j _ { | J | } } ,
$$

with $e _ { I } \sqcup e _ { \varnothing } : = e _ { \varnothing } \sqcup e _ { I } = e _ { I }$ . It extends to a, b $\in T ( \mathbb { R } ^ { d } )$ as

$$
\mathbf { a } \sqcup \mathbf { b } = \sum _ { | I | , | J | \geq 0 } \mathbf { a } _ { I } \mathbf { b } _ { J } ( e _ { I } \sqcup e _ { J } ) .
$$

Observe that $( T ( \mathbb { R } ^ { d } ) , + , \sqcup )$ is a commutative algebra, which in particular means that the shufle product is associative and commutative.

In the following proposition we summarize some useful properties of the signature. These results have been developed in the rough paths literature (see for instance Ree (1958) or Lyons et al. (2007) for the shufle property, Boedihardjo et al. (2016) for the uniqueness of the signature, and Chen (1957, 1977) for Chen’s identity) and have then been refined in the context of semimartingales (see e.g., Bayer et al. (2023); Cuchiero and M¨oller (2023)). For a more detailed exposition and proofs we refer to Cuchiero et al. (2023a).

Proposition 2.3. Let X and Y be two continuous $\mathbb { R } ^ { d } .$ -valued semimartingales with $X _ { 0 } =$ $Y _ { 0 } = 0$ . Then the following properties hold.

Shufle property For each two multi-indices $I , J$ and each $0 \leq s \leq t$ it holds

$$
\langle e _ { I } , \mathbb { X } _ { s , t } \rangle \langle e _ { J } , \mathbb { X } _ { s , t } \rangle = \langle e _ { I } \sqcup e _ { J } , \mathbb { X } _ { s , t } \rangle .\tag{2.3}
$$

Uniqueness of the signature Set $\widehat { X } _ { t } : = ( t , X _ { t } ) , \widehat { Y } _ { t } : = ( t , Y _ { t } )$ and let $\widehat { \mathbb X }$ and $\widehat { \mathbb Y }$ be the corresponding signature processes. Then the signature $\widehat { \mathbb { X } } _ { T } = \widehat { \mathbb { Y } } _ { T }$ if and only if $X _ { t } = Y _ { t }$ for each $t \in [ 0 , T ]$

Chen’s identity For each $0 \leq s \leq u \leq t$ it holds

$$
{ \mathbb X } _ { s , t } = { \mathbb X } _ { s , u } \otimes { \mathbb X } _ { u , t } .\tag{2.4}
$$

This can equivalently be written as

$$
\langle e _ { I } , \mathbb { X } _ { s , t } \rangle = \sum _ { e _ { I _ { 1 } } \otimes e _ { I _ { 2 } } = e _ { I } } \langle e _ { I _ { 1 } } , \mathbb { X } _ { s , u } \rangle \langle e _ { I _ { 2 } } , \mathbb { X } _ { u , t } \rangle ,\tag{2.5}
$$

for each multi-index I.

<!-- page: 9 -->

Universal approximation theorem For each $n \in \mathbb { N }$ consider the sets

$$
\mathcal { S } ^ { ( n ) } : = \{ ( \widehat { \mathbb { X } } _ { t } ^ { n } ) _ { t \in [ 0 , T ] } ( \omega ) : \omega \in \Omega \}
$$

and let $S ^ { ( n ) } : S ^ { ( 2 ) } \to S ^ { ( n ) }$ denote the corresponding Lyons lift. Then it holds that $S ^ { ( n ) } ( ( \widehat { \mathbb { X } } _ { t } ^ { 2 } ) _ { t \in [ 0 , T ] } ) \ = \ ( \widehat { \mathbb { X } } _ { t } ^ { n } ) _ { t \in [ 0 , T ] }$ almost surely. Consider then a generic distance $d _ { S ^ { ( 2 ) } }$ on the set of trajectories given by $S ^ { ( 2 ) }$ , with respect to which the map from $S ^ { ( 2 ) }$ to R given by

$$
\hat { \mathbf { x } } ^ { 2 } \mapsto \langle e _ { I } , S ^ { ( | I | ) } ( \hat { \mathbf { x } } ^ { 2 } ) _ { t } \rangle
$$

is continuous for each multi-index I and every $t \in [ 0 , T ]$ . Let K be a compact subset of $S ^ { ( 2 ) }$ and consider a continuous map $f : K \to \mathbb { R }$ . Then for every $\varepsilon > 0$ there exists some $\ell \in T ( { \mathbb { R } } ^ { d } )$ such that

$$
\operatorname* { s u p } _ { ( \widehat { \mathbb { X } } _ { t } ^ { 2 } ) _ { t \in [ 0 , T ] } \in K } | f ( ( \widehat { \mathbb { X } } _ { t } ^ { 2 } ) _ { t \in [ 0 , T ] } ) - \langle \ell , \widehat { \mathbb { X } } _ { T } \rangle | < \varepsilon ,
$$

almost surely.

## 3 The model

We start by introducing the concept of polynomial difusions (see Cuchiero et al. (2012); Filipovi´c and Larsson (2016)) which will play a key role for the computation of the conditional expected signature. Here we denote by $\sqrt { \cdot }$ the matrix square root.

Definition 3.1. Suppose that an $\mathbb { R } ^ { d } .$ -valued process $X = ( X _ { t } ) _ { t \geq 0 }$ is a weak solution of

$$
\mathrm d X _ { t } = b ( X _ { t } ) \mathrm d t + \sqrt { a ( X _ { t } ) } \mathrm d W _ { t } , \qquad X _ { 0 } = x _ { 0 }
$$

for some d-dimensional Brownian motion W and some maps $a : \mathbb { R } ^ { d } \mathbb { S } _ { + } ^ { d }$ and $b : \mathbb { R } ^ { d } \mathbb { R } ^ { d }$ such that $a _ { i j }$ is a polynomial of degree at most 2 and $b _ { j }$ is a polynomial of degree at most 1 for each $i , j \in \{ 1 , \ldots , d \}$ . Then we call X polynomial difusion.

We are now ready to introduce the model $( S _ { t } ) _ { t \geq 0 }$ for the discounted, dividend-adjusted dynamics of the S&P 500 index already outlined in the introduction. Its dynamics under a risk-neutral probability measure $\mathbb { Q }$ are given by

$$
\mathrm { d } S _ { t } = S _ { t } \sigma _ { t } ^ { S } \mathrm { d } B _ { t } ,\tag{3.1}
$$

where $S _ { 0 } \in \mathbb { R } ^ { + } , \sigma ^ { S } = ( \sigma _ { t } ^ { S } ) _ { t \geq 0 }$ is the volatility process to be specified and $B = ( B _ { t } ) _ { t \geq 0 }$ is a one-dimensional Brownian motion, correlated with $\sigma ^ { S }$ . We define additionally the instantaneous variance via $V _ { t } : = ( \sigma _ { t } ^ { S } ) ^ { 2 }$ for every $t \geq 0$ . Our modeling choice is to parametrize the volatility process $\sigma ^ { S }$ as a linear function of the time-extended signature of a primary process $X ,$ , namely

$$
\sigma _ { t } ^ { S } ( \ell ) : = \ell _ { \varnothing } + \sum _ { 0 < | I | \leq n } \ell _ { I } \langle e _ { I } , \widehat { \mathbb { X } } _ { t } \rangle ,\tag{3.2}
$$

where

$( X _ { t } ) _ { t \geq 0 }$ and thus also $\widehat { X } = ( t , X _ { t } ) _ { t \geq 0 }$ is a polynomial difusion (with values in $\mathbb { R } ^ { d }$ and $\mathbb { R } ^ { d + 1 }$ respectively) in the sense of Definition 3.1.

$\ell : = \{ \ell _ { I } \in \mathbb { R } : | I | \leq n \}$ denotes the collection of parameters of the model, $\mathrm { i . e . }$ $\boldsymbol { \ell } \in \mathbb { R } ^ { ( \bar { d } + 1 ) _ { n } }$

<!-- page: 10 -->

We then denote by $\rho$ the correlation matrix process between the components of X, i.e.

$$
\rho _ { i j } = \frac { [ X ^ { i } , X ^ { j } ] } { \sqrt { [ X ^ { i } ] } \sqrt { [ X ^ { j } ] } } \in [ - 1 , 1 ] ,
$$

for all $i , j = 1 , \ldots , d ,$ where $[ \cdot , \cdot ]$ denotes the quadratic covariation.

In order to simplify the notation we will drop the dependence on ℓ for the processes $S = ( S _ { t } ) _ { t \geq 0 }$ and $( \sigma _ { t } ^ { S } ) _ { t \geq 0 }$ as in (3.1), whenever this does not cause any confusion.

Remark 3.2. As an alternative definition for the volatility process $( \sigma _ { t } ^ { S } ) _ { t \geq 0 }$ one can set

$$
\sigma _ { t } ^ { S } ( \ell ) : = \ell _ { \varnothing } + \sum _ { 0 < | I | \leq n } \ell _ { I } \langle e _ { I } , \widehat { \mathbb { X } } _ { t - \varepsilon , t } \rangle ,
$$

for some fixed $\varepsilon > 0$ . In this case the value of the volatility process $\sigma ^ { S }$ at time t does not depend on the whole trajectory of the primary process X, but just on its evolution from $t - \varepsilon$ to t. For an economically reasonable choice for ε the lags used in Section 3.4 of Guyon and Lekeufack (2023) can be adapted to the current setting.

Remark 3.3 (Interest rates and dividends). In the model given by (3.1) we describe the discounted, dividend-adjusted prices and construct the VIX from them, in line with the definition of the CBOE for the computation of the VIX. However, contingent claims are often expressed in terms of undiscounted, unadjusted prices. If the dynamics of the discounted, dividend-adjusted price process are given by (3.1), the undiscounted, unadjusted one is denoted by $\tilde { S }$ and fulfills

$$
\mathrm { d } \tilde { S } _ { t } = ( r - q ) \tilde { S } _ { t } \mathrm { d } t + \tilde { S } _ { t } \sigma _ { t } ^ { S } ( \ell ) \mathrm { d } B _ { t } ,
$$

where here $r , q \in \mathbb { R }$ denote the interest rate and the dividend, respectively. Therefore $\tilde { S } _ { t } ( \ell ) = e ^ { ( r - q ) t } \bar { S } _ { t } ( \ell )$ and the price of a call option on the S&P 500 index under our model, reads

$$
C ( T , K ) = \mathbb { E } \left[ e ^ { - r T } ( \tilde { S } _ { T } ( \ell ) - K ) ^ { + } \right] = \mathbb { E } [ e ^ { - r T } ( e ^ { ( r - q ) T } S _ { T } ( \ell ) - K ) ^ { + } ]
$$

where $T > 0$ denotes the maturity time and $K \in \mathbb { R }$ the undiscounted strike price.

It is worth mentioning that the pool of eligible primary processes is rather wide, including for example correlated Brownian motions, geometric Brownian motions, OU processes, Cox-Ingersoll-Ross (CIR) processes, Jacobi processes, and all continuous afine processes.

The reason why we require the primary process to be a polynomial difusion is due to the tractability properties of the truncated signature ${ \widehat { \mathbb { X } } } ^ { n }$ under this assumption. We will indeed see in Section 4 that in this case the (conditional) truncated expected signature of $\widehat { X }$ can be computed by solving a finite-dimensional ODE, i.e., can be written in terms of a matrix exponential.

Remark 3.4. We illustrate here that several classical and also recently considered stochastic volatility models are nested within our modeling choice (3.2).

• Suppose that $( X _ { t } ) _ { t \geq 0 }$ is a 1-dimensional OU process and let the order of the signature be $n = 1$ , with $\ell _ { \varnothing } = \ell _ { ( 0 ) } = 0$ and $\ell _ { ( 1 ) } \neq 0$ . Then the process $S = ( S _ { t } ) _ { t \geq 0 }$ coincides with the Stein-Stein model, as introduced in Stein and Stein (1991).

<!-- page: 11 -->

• Suppose that $( X _ { t } ) _ { t \geq 0 }$ is a 1-dimensional geometric Brownian motion without drift and let the order of the signature be $n = 1$ , with $\ell _ { \varnothing } = \ell _ { ( 0 ) } = 0$ and $\ell _ { ( 1 ) } \neq 0$ . Then the process $S = ( S _ { t } ) _ { t \geq 0 }$ coincides with the SABR model, as introduced in initially in Hagan et al. (2002) with $\beta = 1$

• Suppose that $( X _ { t } ) _ { t \geq 0 }$ is a 1-dimensional OU process and let the order of the signature be $n = 5 .$ , with $\ell _ { \varnothing } , \ell _ { ( 1 ) } , \ell _ { ( 1 , 1 , 1 ) } , \ell _ { ( 1 , 1 , 1 , 1 , 1 ) }$ non-zero and $\ell _ { I } = 0$ otherwise. Then the process $S = ( S _ { t } ) _ { t \geq 0 }$ coincides with the model considered in Abi Jaber et al. $\mathrm { ( 2 0 2 2 a , b ) }$ with an exponential kernel (a part from the deterministic input curve considered there additionally). Going beyond the assumption of $\hat { X }$ being a polynomial difusion we may allow for $( X _ { t } ) _ { t \geq 0 }$ to be a one-dimensional fractional Brownian motion, thus leaving the semimartingale setting. And if we do not consider the time augmentation, we can also include fractional kernels and therefore the whole class of Gaussian polynomial volatility models introduced in Abi Jaber et al. (2022a) within our framework.

Remark 3.5. As indicated in the last point of the previous remark, our framework can be extended beyond the semimartingale case as long as the trajectories of the corresponding process can be enhanced to be almost surely a weakly geometric p-rough path. This holds for instance true for the case of time-augmented multidimensional fractional Brownian motion when $H \in ( 1 / 4 , 1 )$ , since for any $p \in ( 1 / H , 4 )$ there exists an almost surely weakly geometric p-rough path, such that the projection on the first component coincides with the process’ increments. For this result we refer to Coutin and Qian (2002), Theorem 2. Observe that the case considered in Abi Jaber et al. (2022a) is simpler since it is a one dimensional setting, meaning that the corresponding signature boils down to Taylor polynomials of fractional Brownian motion.

Note however, while our framework can be extended beyond the semimartingale case as long as signatures can be defined, our methodology to compute conditional truncated expected signatures via finite dimensional matrix exponentials only works in the polynomial difusion setting. The same applies to the linear representation of the log-price provided in Section 6.

Remark 3.6. Let X be a 1-dimensional OU-process, such that without loss of generality $X _ { 0 } = 0 , { \mathrm { i . e . } }$

$$
\mathrm { d } X _ { t } = \kappa ( \theta - X _ { t } ) \mathrm { d } t + \sigma \mathrm { d } W _ { t } .
$$

Then, for $n = 2$ the instantaneous dynamics of the volatility process are given by

$$
\begin{array} { r l } & { \mathrm { d } \sigma _ { t } = \ell _ { 0 } \mathrm { d } t + \ell _ { 1 } \mathrm { d } X _ { t } + \ell _ { 0 0 } t \mathrm { d } t + \ell _ { 0 1 } t \mathrm { d } X _ { t } + \ell _ { 1 0 } X _ { t } \mathrm { d } t + \ell _ { 1 1 } \mathrm { d } X _ { t } ^ { 2 } } \\ & { \qquad = ( \ell _ { 0 } + \ell _ { 0 0 } t + \ell _ { 1 } \kappa ( \theta - X _ { t } ) + \ell _ { 0 1 } t \kappa ( \theta - X _ { t } ) + \ell _ { 1 0 } X _ { t } + 2 \ell _ { 1 1 } X _ { t } \big ( \kappa ( \theta - X _ { t } ) + \sigma ^ { 2 } \big ) \big ) \mathrm { d } t } \\ & { \qquad + \big ( \ell _ { 1 } \sigma + \ell _ { 0 1 } t \sigma + 2 \ell _ { 1 1 } \sigma X _ { t } \big ) \mathrm { d } W _ { t } , } \end{array}
$$

which can be rewritten as

$$
\mathrm { d } \sigma _ { t } = \bigl ( f _ { 1 } ( t ) + c X _ { t } ( g ( t ) - X _ { t } ) \bigr ) \mathrm { d } t + ( f _ { 2 } ( t ) + \tilde { c } X _ { t } ) \mathrm { d } W _ { t } ,
$$

where $f _ { 1 } , f _ { 2 } , g$ are afine functions of time and $c , { \tilde { c } } \in \mathbb { R }$ , all depending on the model parameters $\{ \ell _ { I } , | I | \le n \}$ . The previous simple derivation implies:

• If $n = 1$ the instantaneous vol of vol is constant and given by $| \ell _ { 1 } \sigma |$

• If $n \geq 2$ the instantaneous vol of vol is stochastic, depending explicitly on $X _ { t }$ • For $n = 2$ , the instantaneous volatility exhibits a stochastic mean reversion rate given by the term $c X _ { t }$ , with a time-dependent long-run mean by the afine function $g ( t )$ We will see in the subsequent sections that this type of model with a 3-dimensional OU-process is flexible enough to solve the joint calibration problem.

<!-- page: 12 -->

• Notice that even for $n = 2$ , the choice $X = W$ , i.e. choosing just a Brownian motion (as for instance in Perez Arribas et al. (2020); Cuchiero et al. (2023a) for the price process), would lead to restrictive dynamics of the instantaneous volatility.

## 4 Expected signature of polynomial difusion

Let $( Y _ { t } ) _ { t \geq 0 }$ be a polynomial difusion in sense of Definition 3.1 whose dynamics are given by

$$
\mathrm { d } Y _ { t } = b ( Y _ { t } ) \mathrm { d } t + \sigma ( Y _ { t } ) \mathrm { d } W _ { t } , \qquad Y _ { 0 } = y _ { 0 } ,\tag{4.1}
$$

where $\sigma ( Y _ { t } )$ denotes the matrix square root of $a ( Y _ { t } )$ . Recall that in this case the components of $a : \mathbb { R } ^ { d } \mathbb { S } _ { + } ^ { d }$ are polynomials of degree at most 2, the components of $b : \mathbb { R } ^ { d } \mathbb { R } ^ { d }$ are polynomials of degree at most 1, and $W = ( W _ { t } ) _ { t \geq 0 }$ is a d-dimensional Brownian motion. Denote then by Y the corresponding signature.

We now explain how to employ the polynomial technology to compute the conditional truncated expected signature of $( Y _ { t } ) _ { t \geq 0 }$ . The corresponding code is available at sarasvaluto/AfPolySig. Several representations of related quantities in particular for the Brownian case can be found in the literature, see for instance Fawcett (2003), Lyons and Victoir (2004), Lyons and Ni (2015), Boedihardjo et al. (2021), Cass and Ferrucci (2024). Our approach follows Cuchiero et al. (2023b) and is based on the classical theory of polynomial processes (see Cuchiero et al. (2012) and Filipovi´c and Larsson (2016)). Even though results for the corresponding infinite dimensional stochastic processes (see for instance Cuchiero and Svaluto-Ferro (2021); Cuchiero et al. (2024a)) are needed in the case of general signature SDEs considered in Cuchiero et al. (2023b), the polynomial property of $( Y _ { t } ) _ { t \geq 0 }$ here permits to stay in the finite dimensional setting.

Lemma 4.1. Let $( Y _ { t } ) _ { t \geq 0 }$ be the polynomial difusion given by (4.1) and b and a be the corresponding drift and difusion coeficients. Then

$$
b _ { j } ( y ) = b _ { j } ^ { c } + \sum _ { k = 1 } ^ { d } b _ { j } ^ { k } y _ { k } \qquad { \mathrm { a n d } } \qquad a _ { i j } ( y ) = a _ { i j } ^ { c } + \sum _ { k = 1 } ^ { d } a _ { i j } ^ { k } y _ { k } + \sum _ { k , h = 1 } ^ { d } a _ { i j } ^ { k h } y _ { k } y _ { h } ,
$$

for some $b _ { j } ^ { c } , b _ { j } ^ { k } , a _ { i j } ^ { c } , a _ { i j } ^ { k } , a _ { i j } ^ { k h } = a _ { i j } ^ { h k } \in \mathbb { R }$ . Moreover, $b _ { j } ( Y _ { t } ) = \langle \mathbf { b } _ { j } , \mathbb { Y } _ { t } ^ { 1 } \rangle$ and $a _ { i j } ( Y _ { t } ) = \langle \mathbf { a } _ { i j } , \mathbb { Y } _ { t } ^ { 2 } \rangle$ for

$$
\begin{array} { l } { { \displaystyle { \bf b } _ { j } = \left( b _ { j } ^ { c } + \sum _ { k = 1 } ^ { d } b _ { j } ^ { k } Y _ { 0 } ^ { k } \right) e _ { \emptyset } + \sum _ { k = 1 } ^ { d } b _ { j } ^ { k } e _ { k } } \qquad \mathrm { a n d } }  \\ { { \displaystyle { \bf a } _ { i j } = \left( a _ { i j } ^ { c } + \sum _ { k = 1 } ^ { d } a _ { i j } ^ { k } Y _ { 0 } ^ { k } + \sum _ { k , h = 1 } ^ { d } a _ { i j } ^ { k h } Y _ { 0 } ^ { k } Y _ { 0 } ^ { h } \right) e _ { \emptyset } + \sum _ { k = 1 } ^ { d } \left( a _ { i j } ^ { k } + 2 \sum _ { h = 1 } ^ { d } a _ { i j } ^ { k h } Y _ { 0 } ^ { h } \right) e _ { k } + \sum _ { k , h = 1 } ^ { d } a _ { i j } ^ { k h } e _ { k } \shuffle { \bf a } _ { k } , } } \end{array}
$$

Observe that the upper index on $Y _ { 0 } ^ { k }$ and $Y _ { 0 } ^ { h }$ refers to $Y \mathrm { { } s }$ components and not to powers.

<!-- page: 13 -->

Proof. The first part follows by the observation that by definition of polynomial difusion b and a are polynomials of degree at most 1 and 2, respectively. For the second part it then sufices to note that $\left. e _ { \emptyset } , \mathbb { Y } _ { t } ^ { 1 } \right. = \left. e _ { \emptyset } , \mathbb { Y } _ { t } ^ { 2 } \right. = 1 , \ \left. e _ { k } , \mathbb { Y } _ { t } ^ { 1 } \right. = \left. e _ { k } , \mathbb { Y } _ { t } ^ { 2 } \right. = \left( Y _ { t } ^ { k } - Y _ { 0 } ^ { k } \right)$ , and $\langle e _ { k } \downarrow \sqcup e _ { h } , \mathbb { Y } _ { t } ^ { 2 } \rangle = ( Y _ { t } ^ { k } - Y _ { 0 } ^ { k } ) ( Y _ { t } ^ { h } - Y _ { 0 } ^ { h } )$ □

Lemma 4.2. Let $( Y _ { t } ) _ { t \geq 0 }$ be the polynomial difusion given by (4.1) and let b and a as in Lemma 4.1. The truncated signature $( \mathbb { Y } _ { t } ^ { n } ) _ { t \geq 0 }$ is a polynomial difusion in the sense of Definition 3.1 and for each $| I | \le n$ it holds that

$$
\langle e _ { I } , \mathbb { Y } _ { t } ^ { n } \rangle = \int _ { 0 } ^ { t } \langle L e _ { I } , \mathbb { Y } _ { s } ^ { n } \rangle \mathrm { d } s + \int _ { 0 } ^ { t } \langle e _ { I ^ { \prime } } , \mathbb { Y } _ { s } ^ { n } \rangle { \sigma _ { i _ { | I | } } } ( Y _ { s } ) \mathrm { d } W _ { s } ,
$$

where the operator $L : T ( ( \mathbb { R } ^ { d } ) ) \to T ( ( \mathbb { R } ^ { d } ) )$ satisfies $L ( T ^ { ( n ) } ( \mathbb { R } ^ { d } ) ) \subseteq T ^ { ( n ) } ( \mathbb { R } ^ { d } )$ and is given by

$$
L e _ { I } = e _ { I ^ { \prime } } \sqcup \mathbf { b } _ { i _ { | I | } } + { \frac { 1 } { 2 } } e _ { I ^ { \prime \prime } } \sqcup \mathbf { a } _ { i _ { | I | - 1 } i _ { | I | } } .\tag{4.2}
$$

Proof. Let $\sigma _ { j } ( Y _ { t } )$ denote the j-th row of $\sigma ( Y _ { t } )$ . By definition of the signature, Stratonovich integral and by the shufle property we can compute

$$
\begin{array} { r l } { \langle \epsilon _ { I I } , \Psi _ { i I } ^ { * } \rangle = \int _ { 0 } ^ { t } \langle \epsilon _ { I I } , \Psi _ { i I } \rangle = } & { \int _ { 0 } ^ { t } \langle \epsilon _ { I I } , \Psi _ { i I } \rangle = } \\ & { = \int _ { 0 } ^ { t } \langle \epsilon _ { I I } , \Psi _ { i I } \rangle \mathrm { d } \hat { \epsilon } _ { i I I } \langle \epsilon _ { I I } , \Psi _ { i I } \rangle + \frac { 1 } { 2 } \left[ \langle \epsilon _ { I I } , \Psi _ { i I } \rangle , \langle \epsilon _ { I I } , \Psi _ { i I } , \Psi _ { i I } \rangle \right] , } \\ & { = \int _ { 0 } ^ { t } \langle \epsilon _ { I I } , \Psi _ { i I } \rangle \mathrm { d } \hat { \epsilon } _ { i I I } \langle \epsilon _ { I I } , \Psi _ { i I } \rangle = + \frac { 1 } { 2 } \int _ { 0 } ^ { t } \langle \epsilon _ { I I } , \Psi _ { i I } , \Phi _ { i I } \rangle \mathrm { d } \hat { \epsilon } _ { i I I } \langle \epsilon _ { i I } , \dots , \Psi _ { i I } , \hat { \epsilon } _ { i I I } , \Psi _ { i I } \rangle , } \\ & { = \int _ { 0 } ^ { t } \langle \epsilon _ { I I } , \Psi _ { i I } , \Psi _ { i I } \rangle = \epsilon _ { I I } \int _ { 0 } ^ { t } \langle \epsilon _ { I I } , \Psi _ { i I } \rangle \mathrm { d } \hat { \epsilon } _ { i I I } ( \hat { \epsilon } _ { i I I } , \dots , \Psi _ { i I } ) \mathrm { d } \hat { \epsilon } _ { i I I } \langle \epsilon _ { i I I } , \Psi _ { i I } \rangle , } \\ & { \quad + \frac { 1 } { 2 } \int _ { 0 } ^ { t } \langle \epsilon _ { I I } , \Psi _ { i I } , \Psi _ { i I } \rangle \mathrm { d } \hat { \epsilon } _ { i I I } \dots \mathrm { d } \hat { \epsilon } _ { i I I } \langle \epsilon _ { i I I } , \Psi _ { i I } \rangle = } \\ &  = \int _ { 0 } ^ { t } \langle \epsilon _ { I I }  \end{array}
$$

for each $| I | \geq 0$ . Since $| I \sqcup J | = | I | + | J |$ it holds that $L ( T ^ { ( n ) } ( \mathbb { R } ^ { d } ) ) \subseteq T ^ { ( n ) } ( \mathbb { R } ^ { d } )$ . For $| I | \le n$ we thus get that the corresponding drift’s components are linear maps in $\mathbb { Y } ^ { n }$ . Similarly, since $\begin{array} { l } { { \bf { a } } _ { i j } = \sum _ { | I | , | J | \leq 1 } \lambda _ { i j } ^ { I J } e _ { I } } \end{array}$  $e _ { J }$ for some $\lambda _ { i j } ^ { I J } \in \mathbb { R }$ and for $| I | \le n$ we can compute

$$
\begin{array} { r l } { \langle e _ { I ^ { \prime } } , { \mathbb Y } _ { s } \rangle \sigma _ { i _ { | I | } } ( Y _ { t } ) \big ( \langle e _ { J ^ { \prime } } , { \mathbb Y } _ { s } \rangle \sigma _ { i _ { | J | } } ( Y _ { t } ) \big ) ^ { \top } = \langle e _ { I ^ { \prime } } , { \mathbb Y } _ { s } \rangle \langle e _ { J ^ { \prime } } , { \mathbb Y } _ { s } \rangle \langle { \mathbf a } _ { i _ { | I | } j _ { | J | } } , { \mathbb Y } _ { s } \rangle } & { } \\ { = \displaystyle \sum _ { | H _ { 1 } | , | H _ { 2 } | \leq 1 } \lambda _ { i _ { | I | } j _ { | J | } } ^ { H _ { 1 } H _ { 2 } } \langle e _ { I ^ { \prime } } \shuffle e _ { I } , { \mathbb Y } _ { s } \rangle \langle e _ { J ^ { \prime } } \shuffle e _ { H _ { 2 } } , { \mathbb Y } _ { s } \rangle , } & { } \end{array}
$$

we also have that the components of the corresponding difusion matrix are polynomials of degree 2 in $\mathbb { Y } ^ { n }$ . Lemma 2.2 in Filipovi´c and Larsson (2016) yields the polynomial property.

Since the linear operator $L$ maps the finite dimensional vector space $T ^ { ( n ) } ( \mathbb { R } ^ { d } )$ to itself, it admits a matrix representation.

<!-- page: 14 -->

Definition 4.3. We call the operator L defined in (4.2) dual operator corresponding to $\mathbb { Y } .$ For each $\left. I \right. \le n$ set then $\eta _ { I J } \in \mathbb { R }$ such that

$$
L e _ { I } = \sum _ { | J | \leq n } \eta _ { I J } e _ { J } ,
$$

and fix a labelling injective function $\mathcal { L } : \{ I \colon | I | \leq n \} \to \{ 1 , \ldots , d _ { n } \}$ as introduced before (2.2). We then call the matrix $G \in \mathbb { R } ^ { d _ { n } \times d _ { n } }$ given by

$$
G _ { \mathcal { L } ( I ) \mathcal { L } ( J ) } : = \eta _ { I J } ,\tag{4.3}
$$

the $d _ { n }$ -dimensional matrix representative of $L$

Observe that using the notation of (2.2), for each $\mathbf { u } \in T ^ { ( n ) } ( \mathbb { R } ^ { d } )$ the matrix representative G of L satisfies

$$
\mathbf { v e c } ( L \mathbf { u } ) = G \mathbf { v e c } ( \mathbf { u } ) .
$$

Theorem 4.4. Let $( Y _ { t } ) _ { t \geq 0 }$ be the polynomial difusion given by (4.1), $( \mathcal { F } _ { t } ) _ { t \geq 0 }$ be the filtration generated by $( Y _ { t } ) _ { t \geq 0 }$ and let G be the $d _ { n }$ -dimensional matrix representative of the dual operator corresponding to Y. Then for each $T , t \geq 0$ and each $| I | \le n$ it holds

$$
\mathbb { E } [ \mathbf { v e c } ( \mathbb { Y } _ { T + t } ^ { n } ) | \mathcal { F } _ { T } ] = e ^ { t G ^ { \top } } \mathbf { v e c } ( \mathbb { Y } _ { T } ^ { n } ) ,
$$

or equivalently,

$$
\mathbb { E } [ \langle e _ { I } , \mathbb { Y } _ { T + t } ^ { n } \rangle | \mathcal { F } _ { T } ] = \sum _ { | J | \leq n } ( e ^ { t G ^ { \top } } ) \mathcal { L } ( I ) \mathcal { L } ( J ) \langle e _ { J } , \mathbb { Y } _ { T } ^ { n } \rangle ,
$$

where $e ^ { ( \cdot ) }$ denotes the matrix exponential.

Proof. By Lemma 4.2 we know that $\mathbf { v e c } ( \mathbb { Y } ^ { n } )$ is a polynomial difusion and Theorem 3.1 in Filipovi´c and Larsson (2016) for polynomials of degree 1 yields the claim. □

Example 4.5. For the present paper a crucial role is played by the polynomial difusion given by time, a d-dimensional OU process, and a Brownian motion. Specifically, we consider the process $\widehat { Z } _ { t } : = ( \widehat { X } _ { t } , B _ { t } )$ where B is a Brownian motion and $\widehat { X } _ { t } = \left( t , X _ { t } \right)$ with

$$
\mathrm { d } X _ { t } ^ { j } = \kappa ^ { j } ( \theta ^ { j } - X _ { t } ^ { j } ) \mathrm { d } t + \sqrt { a ( X _ { t } ) } \mathrm { d } W _ { t } , \qquad X _ { 0 } = x _ { 0 } ,
$$

for $a _ { i j } ( X _ { t } ) = \sigma ^ { i } \sigma ^ { j } \rho _ { i j }$ , and W being a d-dimensional Brownian motion. We denote by $\rho _ { j ( d + 1 ) }$ the correlation between $X ^ { j }$ and B. Setting $\kappa ^ { d + 1 } : = 0$ and $\sigma ^ { d + 1 } : = 1$ we can see that $\widehat { Z }$ satisfies (4.1) in $d + 2$ dimensions for

$$
b _ { j } ( \widehat { Z } _ { t } ) = 1 _ { \{ j = 0 \} } + \kappa ^ { j } ( \theta ^ { j } - \widehat { Z } _ { t } ^ { j } ) 1 _ { \{ j \neq 0 \} } \qquad \mathrm { a n d } \qquad a _ { i j } ( \widehat { Z } _ { t } ) = \sigma ^ { i } \sigma ^ { j } \rho _ { i j } 1 _ { \{ i , j \neq 0 \} } .
$$

The corresponding b and a are given by $\mathbf { b } _ { j } = e _ { \emptyset } ( 1 _ { \{ j = 0 \} } + \kappa ^ { j } ( \theta ^ { j } - \widehat { Z } _ { 0 } ^ { j } ) 1 _ { \{ j \neq 0 \} } ) - e _ { j } \kappa ^ { j } 1 _ { \{ j \neq 0 \} }$ and $\mathbf { a } _ { i j } = e _ { \emptyset } \sigma ^ { i } \sigma ^ { j } \rho _ { i j } 1 _ { \{ i , j \neq 0 \} }$ and we thus get

$$
\begin{array} { l } { { L e _ { I } = e _ { I ^ { \prime } } \bigl ( 1 _ { \{ i _ { | I | } = 0 \} } + \kappa ^ { i _ { | I | } } \bigl ( \theta ^ { i _ { | I | } } - \widehat { Z } _ { 0 } ^ { i _ { | I | } } \bigr ) 1 _ { \{ i _ { | I | } \neq 0 \} } \bigr ) - \bigl ( e _ { I ^ { \prime } } \ \{ \amalg \ e _ { i _ { | I | } } \bigr ) \kappa ^ { i _ { | I | } } 1 _ { \{ i _ { | I | } \neq 0 \} } } } \\ { { \qquad + \displaystyle \frac { 1 } { 2 } e _ { I ^ { \prime \prime } } \sigma ^ { i _ { | I | } - 1 } \sigma ^ { i _ { | I | } } \rho _ { i _ { | I | - 1 } i _ { | I | } } 1 _ { \{ i _ { | I | - 1 } , i _ { | I | } \neq 0 \} } . } } \end{array}
$$

An application of L to the first basis elements yields the following results:

<!-- page: 15 -->

$L ( e _ { 1 } ) = e _ { \emptyset } \kappa ^ { 1 } ( \theta ^ { 1 } - X _ { 0 } ^ { 1 } ) - e _ { 1 } \kappa ^ { 1 } \mathrm { , }$

$$
\begin{array} { r } { \bullet L ( e _ { I } \otimes e _ { 0 } ) = e _ { I } \sqcup \mathbf { b } _ { 0 } + \frac { 1 } { 2 } e _ { I ^ { \prime } } \sqcup \mathbf { a } _ { i _ { | I | } 0 } = e _ { I } ; } \end{array}
$$

$$
\begin{array} { r } { \bullet \ L ( e _ { 0 } \otimes e _ { 1 } \otimes e _ { 2 } ) = e _ { 0 } \otimes e _ { 1 } \kappa ^ { 2 } ( \theta ^ { 2 } - X _ { 0 } ^ { 2 } ) - ( e _ { 0 } \otimes e _ { 1 } ) \sqcup e _ { 2 } \kappa ^ { 2 } + \frac { 1 } { 2 } e _ { 0 } \sigma ^ { 1 } \sigma ^ { 2 } \rho _ { 1 2 } . } \end{array}
$$

Letting $( \mathcal { F } _ { t } ) _ { t \geq 0 }$ be the filtration generated by $( \widehat { Z } _ { t } ) _ { t \geq 0 }$ by Theorem 4.4 we can conclude that

$$
\mathbb { E } [ \mathbf { v e c } ( \widehat { \mathbb { Z } } _ { T + t } ^ { n } ) | \mathcal { F } _ { T } ] = e ^ { t G ^ { \top } } \mathbf { v e c } ( \widehat { \mathbb { Z } } _ { T } ^ { n } ) ,\tag{4.4}
$$

or equivalently,

$$
\mathbb { E } [ \langle e _ { I } , \widehat { \mathbb { Z } } _ { T + t } ^ { n } \rangle | \mathcal { F } _ { T } ] = \sum _ { | J | \leq n } ( e ^ { t G ^ { \top } } ) \mathcal { L } ( I ) \mathcal { L } ( J ) \langle e _ { J } , \widehat { \mathbb { Z } } _ { T } ^ { n } \rangle ,\tag{4.5}
$$

where G denotes the $( d + 2 ) _ { r }$ -dimensional matrix representative of L. In order to work with the VIX it will be convenient to restrict our attention to the signature components of $( \widehat { \mathbb { Z } } _ { t } ) _ { t \geq 0 }$ not involving B. The following remark will be useful.

Remark 4.6. Observe that given a subset $E \subseteq \{ 0 , \ldots , d + 1 \}$ , setting $\mathcal { T } _ { E } : = \{ I : i _ { j } \in E \}$ it holds $L ( \mathcal { T } _ { E } ) \subseteq \mathcal { T } _ { E }$ . This in particular implies that

$$
L e _ { I } = \sum _ { I \in \mathcal { I } _ { E } } \eta _ { I J } e _ { J }
$$

for each $I \in \mathcal { T } _ { E }$ . Choosing $E = \{ 0 , \ldots , d \}$ , letting $\mathcal { L } _ { E } : \mathcal { T } _ { E } \{ 1 , \ldots , ( d + 1 ) _ { n } \}$ be a labelling injective function, and setting $G _ { \mathcal { L } _ { E } ( I ) \mathcal { L } _ { E } ( J ) } ^ { E } : = \eta _ { I J }$ we can see that (4.5) reduces to

$$
\mathbb { E } [ \langle e _ { I } , \widehat { \mathbb { X } } _ { T + t } ^ { n } \rangle | \mathcal { F } _ { T } ] = \sum _ { | J | \leq n } ( e ^ { t ( G ^ { E } ) ^ { \top } } ) \mathcal { L } _ { E } ( I ) \mathcal { L } _ { E } ( J ) \langle e _ { J } , \widehat { \mathbb { X } } _ { T } ^ { n } \rangle .
$$

To simplify the notation we often drop the E from $G ^ { E }$ whenever this does not introduce any confusion.

Remark 4.7. Let $( Y _ { t } ) _ { t \geq 0 }$ be a polynomial difusion and let $\mathbb { Y } ^ { - 1 }$ be defined via $e _ { \varnothing } = \mathbb { Y } _ { s } ^ { - 1 } \otimes$ $\mathbb { Y } _ { s } , \mathrm { i . e . ~ } \langle e _ { \varnothing } , \mathbb { Y } _ { s } ^ { - 1 } \rangle = 1$ and

$$
\sum _ { e _ { I _ { 1 } } \otimes e _ { I _ { 2 } } = e _ { I } } \langle e _ { I _ { 1 } } , \mathbb { Y } _ { s } ^ { - 1 } \rangle \langle e _ { I _ { 2 } } , \mathbb { Y } _ { s } \rangle = 0 ,
$$

for each $\vert I \vert > 0$ . Observe that it can be defined recursively on $| I |$ and each component of $\mathbb { Y } _ { s } ^ { - 1 }$ corresponds to a linear combination of components of $\mathbb { Y } _ { s }$ of the same length or shorter.

Since by Chen’s identity (see (2.4) or (2.5)) we have $\mathbb { Y } _ { s } \otimes \mathbb { Y } _ { s , t } = \mathbb { Y } _ { t }$ , for each $s \leq u \leq t$ and $| I | \le n$ we then get

$$
\begin{array} { l } { \displaystyle \mathbb { E } [ \langle e _ { I } , { \mathbb Y } _ { s , t } \rangle | { \mathcal F } _ { u } ] = \mathbb { E } [ \langle e _ { I } , { \mathbb Y } _ { s } ^ { - 1 } \otimes { \mathbb Y } _ { t } \rangle | { \mathcal F } _ { u } ] = \sum _ { e _ { I _ { 1 } } \otimes e _ { I _ { 2 } } = e _ { I } } \langle e _ { I _ { 1 } } , { \mathbb Y } _ { s } ^ { - 1 } \rangle \mathbb { E } [ \langle e _ { I _ { 2 } } , { \mathbb Y } _ { t } \rangle | { \mathcal F } _ { u } ] } \\ { = \displaystyle \sum _ { e _ { I _ { 1 } } \otimes e _ { I _ { 2 } } = e _ { I } } \langle e _ { I _ { 1 } } , { \mathbb Y } _ { s } ^ { - 1 } \rangle { \mathbf v e c } ( e _ { I _ { 2 } } ) ^ { \top } e ^ { ( t - u ) G ^ { \top } } { \mathbf v e c } ( { \mathbb Y } _ { u } ^ { n } ) , } \end{array}
$$

where $G$ denotes the $d _ { n }$ -dimensional matrix representative of the dual operator of $\mathbb { Y } .$

<!-- page: 16 -->

## 5 VIX options with signatures

In this section we discuss the implication on pricing VIX options under the model (3.1)-(3.2). The VIX index is a popular measure of the market’s expected volatility of the S&P 500, calculated and published by the Chicago Board Options Exchange (CBOE). The current VIX value quotes the expected annualized change in the S&P 500 over the following 30 days, based on options-based theory and current options-market data. As stylized definition we consider

$$
\mathrm { V I X } _ { T } ^ { 2 } = \mathrm { P r i c e } _ { T } \left[ - \frac { 2 } { \Delta } \log \left( \frac { S _ { T + \Delta } } { F _ { T } ^ { T + \Delta } } \right) \right] ,\tag{5.1}
$$

where $\Delta = 3 0$ days, $F _ { T } ^ { T + \Delta }$ denotes the price at time $T$ of the SPX future with maturity $T + \Delta$ and with Price<sub>T</sub> we refer to the market price at time $T$ of the log-contract, i.e. the payof in (5.1). Hence, under a given model we define the VIX,

$$
\mathrm { V I X } _ { T } = \sqrt { \mathbb { E } \left[ - \frac { 2 } { \Delta } \log \left( \frac { S _ { T + \Delta } } { S _ { T } } \right) | \mathcal { F } _ { T } \right] } ,\tag{5.2}
$$

where $\Delta = 3 0$ days and $S _ { T }$ denotes the price process at time $T > 0$ . Recall that under a difusion model, the previous expression is equivalent to

$$
\mathrm { V I X } _ { T } = \sqrt { \frac { 1 } { \Delta } \mathbb { E } \left[ \int _ { T } ^ { T + \Delta } V _ { t } \mathrm { d } t | \mathcal { F } _ { T } \right] } ,\tag{5.3}
$$

as long as $\begin{array} { r } { { \mathbb E } [ \int _ { 0 } ^ { t } V _ { s } d s ] < \infty } \end{array}$ for all $t \geq 0$ , see e.g. Neuberger (1994); Gatheral (2011). With VIX options we here usually refer to either put or calls written on VIX. In the present work we will consider without loss of generality only call options.

## 5.1 Explicit formulas for the VIX

This section is dedicated to one of the main implication of our modeling framework, namely an explicit formula for the VIX expression (5.2) for S following (3.1)-(3.2). In particular we show in the next theorem that the computation of the VIX squared reduces to a quadratic form in the parameters ℓ. The entries of the corresponding positive semidefinite matrix can be computed by polynomial technology, i.e. by matrix exponential as proved in Section 4.

Theorem 5.1. Let $S = ( S _ { t } ) _ { t \geq 0 }$ be a price process described $b y$

$$
\mathrm { d } S _ { t } = S _ { t } \sigma _ { t } ^ { S } \mathrm { d } B _ { t } ,
$$

where $\sigma ^ { S } = ( \sigma _ { t } ^ { S } ) _ { t \geq 0 }$ denotes the volatility process, $B = ( B _ { t } ) _ { t \geq 0 }$ a one-dimensional Brownian motion. Assume that $\sigma ^ { S }$ satisfies (3.2). Following (2.2), fix an injective labeling function $\mathcal { L } : \{ I : | I | \leq n \} \to \{ 1 , \dots , ( d + 1 ) _ { 2 n + 1 } \}$ and let G be the $( d + 1 ) _ { ( 2 n + 1 ) }$ - dimensional matrix representative of the dual operator corresponding to $\widehat { \mathbb X }$ . Then,

$$
\mathbb { E } \left[ \int _ { 0 } ^ { t } V _ { s } \mathrm { d } s \right] < \infty\tag{5.4}
$$

holds for every $t \geq 0$ and

$$
V I X _ { T } ( \ell ) = \sqrt { \frac { 1 } { \Delta } \ell ^ { \top } Q ( T , \Delta ) \ell } ,\tag{5.5}
$$

<!-- page: 17 -->

where

$$
{ \cal Q } _ { \mathcal { L } ( I ) \mathcal { L } ( J ) } ( T , \Delta ) = \mathbf { v e c } ( ( e _ { I } \sqcup e _ { J } ) \otimes e _ { 0 } ) ^ { \top } ( e ^ { \Delta G ^ { \top } } - \mathrm { I d } ) \mathbf { v e c } ( \widehat { \mathbb { X } } _ { T } ^ { 2 n + 1 } ) ,\tag{5.6}
$$

and Id $\in \mathbb { R } ^ { ( d + 1 ) _ { 2 n + 1 } \times ( d + 1 ) _ { 2 n + 1 } }$ denotes the identity matrix. More explicitly without the vectorisation this reads

$$
Q _ { \mathcal { L } ( I ) , \mathcal { L } ( J ) } ( T , \Delta ) = \sum _ { \substack { e _ { K } = ( e _ { I } \sqcup e _ { J } ) \otimes e _ { 0 } | H | \leq 2 n + 1 } } ( e ^ { \Delta G ^ { \top } } - \operatorname { I d } ) _ { \mathcal { L } ( K ) , \mathcal { L } ( H ) } \langle e _ { H } , \widehat { \mathbb { X } } _ { T } \rangle .
$$

Proof. Observe that

$$
V _ { t } ( \ell ) = \bigg ( \sum _ { | I | \le n } \ell _ { I } \langle e _ { I } , \widehat { \mathbb { X } } _ { t } \rangle \bigg ) ^ { 2 } = \sum _ { | I | , | J | \le n } \ell _ { I } \ell _ { J } \langle e _ { I } \shuffle e _ { J } , \widehat { \mathbb { X } } _ { t } \rangle .
$$

Since continuous polynomial difusions have finite moments of every degree, (5.4) is satisfied due to Lemma 4.2. Under (5.3), the expression for $V _ { t } ( \ell )$ yields then

$$
\begin{array} { l } { { \mathrm { V I X } _ { T } ^ { 2 } ( \ell ) = \displaystyle \frac { 1 } { \Delta } \sum _ { | I | , | J | \leq n } \ell _ { I } \ell _ { J } \mathbb { E } \biggl [ \int _ { T } ^ { T + \Delta } \langle e _ { I } \shuffle e _ { I } , \widehat { \mathbb { X } } _ { t } \rangle { \mathrm { d } } t | \mathcal { F } _ { T } \biggr ] } } \\ { { \mathrm { ~ } = \displaystyle \frac { 1 } { \Delta } \ell ^ { \top } Q ( T , \Delta ) \ell , } } \end{array}
$$

where for each $T > 0$ the matrix $Q$ is given by

$$
\begin{array} { r l } & { \displaystyle Q _ { \mathcal { L } ( I ) \mathcal { L } ( J ) } ( T , \Delta ) : = \mathbb { E } \biggl [ \int _ { T } ^ { T + \Delta } \langle e _ { I } \shuffle e _ { J } , \widehat { \mathbb { X } } _ { t } \rangle \mathrm { d } t \lvert \mathcal { F } _ { T } \biggr ] } \\ & { \qquad = \mathbb { E } \biggl [ \int _ { 0 } ^ { T + \Delta } \langle e _ { I } \shuffle e _ { J } , \widehat { \mathbb { X } } _ { t } \rangle { \mathrm { d } } t - \int _ { 0 } ^ { T } \langle e _ { I } \shuffle e _ { J } , \widehat { \mathbb { X } } _ { t } \rangle { \mathrm { d } } t \lvert \mathcal { F } _ { T } \biggr ] } \\ & { \qquad = \mathbb { E } \bigl [ \langle ( e _ { I } \shuffle e _ { J } ) \otimes e _ { 0 } , \widehat { \mathbb { X } } _ { T + \Delta } \rangle - \langle ( e _ { I } \shuffle e _ { J } ) \otimes e _ { 0 } , \widehat { \mathbb { X } } _ { T } \rangle \lvert \mathcal { F } _ { T } \bigr ] } \\ & { \qquad = \mathbb { E } \bigl [ \langle ( e _ { I } \shuffle e _ { J } ) \otimes e _ { 0 } , \widehat { \mathbb { X } } _ { T + \Delta } \rangle \lvert \mathcal { F } _ { T } \bigr ] - \langle ( e _ { I } \shuffle e _ { J } ) \otimes e _ { 0 } , \widehat { \mathbb { X } } _ { T } \rangle . } \end{array}
$$

By Theorem 4.4 we can rewrite the matrix $Q$ as

$$
\begin{array} { r l } & { Q _ { \mathcal { L } ( I ) \mathcal { L } ( J ) } ( T , \Delta ) = \mathbf { v e c } ( ( e _ { I } \sqcup e _ { J } ) \otimes e _ { 0 } ) ^ { \top } e ^ { \Delta G ^ { \top } } \mathbf { v e c } ( \widehat { \mathbb { X } } _ { T } ^ { 2 n + 1 } ) } \\ & { \qquad - \mathbf { v e c } ( ( e _ { I } \sqcup e _ { J } ) \otimes e _ { 0 } ) ^ { \top } \mathbf { v e c } ( \widehat { \mathbb { X } } _ { T } ^ { 2 n + 1 } ) } \\ & { \qquad = \mathbf { v e c } ( ( e _ { I } \sqcup e _ { J } ) \otimes e _ { 0 } ) ^ { \top } ( e ^ { \Delta G ^ { \top } } - \mathrm { I d } ) \mathbf { v e c } ( \widehat { \mathbb { X } } _ { T } ^ { 2 n + 1 } ) , } \end{array}
$$

and the claim follows.

Remark 5.2. Consider now the model described in Remark 3.2 and set for simplicity $\varepsilon \ge \Delta$ . Then the results of Theorem 5.1 still hold however with

$$
Q _ { \mathcal { L } ( I ) . \mathcal { L } ( J ) } ( T , \Delta ) = \sum _ { e _ { I _ { 1 } } \otimes e _ { I _ { 2 } } = e _ { I } \sqcup e _ { J } } \int _ { T } ^ { T + \Delta } \langle e _ { I _ { 1 } } , \widehat { \mathbb { X } } _ { t - \varepsilon } ^ { - 1 } \rangle \mathbf { v e c } ( e _ { I _ { 2 } } ) ^ { \top } e ^ { ( t - T ) G ^ { \top } } \mathbf { v e c } ( \widehat { \mathbb { X } } _ { T } ) \mathrm { d } t ,
$$

where G denotes the $( d + 1 ) _ { 2 n + 1 }$ -dimensional matrix representative of the dual operator corresponding to $\widehat { \mathbb X }$ . To adapt the proof we just need to note that for each $t \in [ T , T + \Delta ]$ Remark 4.7 yields

$$
\mathbb { E } [ \langle e _ { I } \sqcup e _ { J } , \widehat { \mathbb { X } } _ { t - \varepsilon , t } \rangle | \mathcal { F } _ { T } ] = \sum _ { e _ { I _ { 1 } } \otimes e _ { I _ { 2 } } = e _ { I } \sqcup \mathfrak { e } _ { J } } \langle e _ { I _ { 1 } } , \widehat { \mathbb { X } } _ { t - \varepsilon } ^ { - 1 } \rangle \mathbf { v e c } ( e _ { I _ { 2 } } ) ^ { \top } e ^ { ( t - T ) G ^ { \top } } \mathbf { v e c } ( \widehat { \mathbb { X } } _ { T } ) .
$$

<!-- page: 18 -->

Note that since the integration’s variable t appears twice in this expression the time integral cannot be incorporated in the signature.

Remark 5.3. Observe that accounting for the scaling factor of 100, conventionally introduced by CBOE, the VIX index squared can equivalently be redefined (see e.g., Rosenbaum and Zhang (2021); Rømer (2022)) as

$$
\mathrm { V I X } _ { T } ^ { 2 } = \frac { 1 0 0 ^ { 2 } } { \Delta } \mathbb { E } \left[ \int _ { T } ^ { T + \Delta } V _ { t } \mathrm { d } t | \mathcal { F } _ { T } \right] ,\tag{5.7}
$$

where $T , t > 0$ and $\textstyle \Delta = { \frac { 1 } { 1 2 } } , { \mathrm { i . e . } }$ ., approximately 30 days. Notice that since the expressions (5.3) and (5.7) difer only by a scaling factor, all the theoretical results of the present work hold true disregarding this scaling. For sake of simplicity we will always use (5.3). We address the reader to Chapter 11 in Gatheral (2011) for further details about the conventions of CBOE and its link with (5.2).

We observe that the expression (5.6) is computationally appealing as we can unpack the computation in three parts: compute the coordinate vector vec $( ( e _ { I } \sqcup e _ { J } ) \otimes e _ { 0 } )$ , which depends just on $d > 0$ and $n > 0 .$ , calculate the matrix exponential of $G ^ { \top }$ which depends on the choice of the primary process $X$ , and finally sample $\widehat { \mathbb { X } } _ { T } ^ { 2 n + 1 }$ which is the only part that depends on the chosen maturity time $T .$ In order to compute the matrix exponential we rely on Bader et al. (2019) who developed a Pad´e-insipired approximation to reduce the matrix multiplications, see also Moler and Van Loan (2003) for further possible methods. For the implementation of the signature samples and its computational complexity we refer to Reizenstein and Graham (2018); Kidger and Lyons (2020).

Remark 5.4. In general the computation of $G \in \mathbb { R } ^ { ( d + 1 ) _ { 2 n + 1 } \times ( d + 1 ) _ { 2 n + 1 } }$ , even if done only once, can be costly. For this reason it can sometimes be interesting to avoid the last time integral and to consider the following equivalent expression of the matrix Q, for $| I | , | J | \leq n \colon$

$$
Q _ { \mathcal { L } ( I ) , \mathcal { L } ( J ) } ( T , \Delta ) = \left( \int _ { T } ^ { T + \Delta } \mathbf { v e c } ( e _ { I } \sqcup e _ { J } ) ^ { \top } e ^ { ( t - T ) G ^ { \top } } \mathrm { d } t \right) \mathbf { v e c } ( \widehat { \mathbb { X } } _ { T } ^ { 2 n } ) ,\tag{5.8}
$$

where now $G \in \mathbb { R } ^ { ( d + 1 ) _ { 2 n } \times ( d + 1 ) _ { 2 n } }$ and where we use the fact that we can interchange the conditional expectation with the time-integral by dominated convergence. As G is singular, this time integral has to be computed numerically, in general. We propose here two possible methods that can be used in order to compute it eficiently.

(i) Approximation of the time integral: $\mathrm { e . g . }$ , via the trapezoidal rule also applied for $\mathrm { { V I X ^ { 2 } } }$ in Bourgey and De Marco (2022). Hence if we consider the shufled coordinates vec $( e _ { I } \sqcup e _ { J } )$ of the exponential matrix we can use the symmetry of the shufle to reduce the number of integrals to be solved from $( ( d + 1 ) _ { 2 n } ) ^ { 2 } \ \mathrm { t o } \ { \frac { ( d + 1 ) _ { n } ( ( d + 1 ) _ { n } + 1 ) } { 2 } } \cdot ( d + 1 ) _ { 2 n }$ instead of $( d _ { 2 n } ) ^ { 2 }$ . Observe that for our integral the error of such an approximation is given by

$$
\mathrm { E r r } ( N ) = - \frac { \Delta ^ { 2 } } { 1 2 N ^ { 2 } } G ^ { \top } ( e ^ { G ^ { \top } \Delta } - I ) + \mathcal { O } ( N ^ { - 3 } ) ,
$$

as $N \to + \infty$ . As a further dimension reduction one can exploit the polynomial nature of $\mathring { \mathbb { X } } ^ { n }$ to obtain a matrix representation of its second order moments. Without entering into details, the matrix G would then be the matrix corresponding to the linear operator acting on coeficients of polynomials of degree 2 in ${ \widehat { \mathbb { X } } } ^ { n }$ . Its dimension would thus be $\frac { ( d + 1 ) _ { n } ( ( d + 1 ) _ { n } + 1 ) } { 2 }$

<!-- page: 19 -->

(ii) Approximation of the matrix exponential: we can avoid to approximate the integral by approximating the matrix exponential. Assuming that

$$
\operatorname* { l i m } _ { N  + \infty } ( G ^ { \top } \Delta ) ^ { N } = 0 ,\tag{5.9}
$$

this can for instance be done via its Taylor expansion:

$$
\int _ { T } ^ { T + \Delta } e ^ { t G ^ { \top } } \mathrm { d } t = \Delta \left( I + \frac { G ^ { \top } \Delta } { 2 ! } + \cdot \cdot \cdot + \frac { ( G ^ { \top } \Delta ) ^ { N } } { N + 1 ! } + \mathcal { O } ( ( G ^ { \top } \Delta ) ^ { N + 1 } ) \right) .
$$

Observe that (5.9) holds true whenever the spectral radius, i.e., the maximal eigenvalue in absolute value, of the matrix $G ^ { \top } \Delta$ is less than 1 (see for instance Theorem 1.5 in Quarteroni et al. (2010)). This requirement suggests that for numerical purposes the parameters of the primary process have to be chosen accordingly.

An interesting example is given by the case where X is a d-dimensional correlated Brownian motion, as considered for instance in Cuchiero et al. (2023a). In this case the process has no linear drift and the corresponding matrix G is nilpotent, meaning that $G ^ { n } = 0$ , for each n big enough.

In general, this Taylor approach permits to avoid a numerical integration and produces an accurate approximation, allocating as few memory as possible.

Remark 5.5. A further step in the direction of a fast evaluation of $\mathrm { V I X } _ { T } ( \ell )$ can be taken by noticing that the matrix $Q$ in (5.6) admits a Cholesky decomposition. Indeed since $Q$ is positive semidefinite and symmetric by the shufle property, we know that there exists an upper triangular matrix $\bar { U _ { T } } \in \mathbb { R } ^ { ( d + 1 ) _ { n } \times ( d + 1 ) _ { r } }$ , with possible zero elements on the diagonal, such that

$$
Q ( T , \Delta ) = U _ { T } U _ { T } ^ { \top } ,
$$

where for sake of simplicity we drop the dependence on $\Delta$ of $U _ { T }$ . Hence the evaluation of the $\mathrm { V I X } _ { T } ( \ell )$ reduces to

$$
\operatorname { V I X } _ { T } ( \ell ) = \sqrt { \frac { 1 } { \Delta } \ell ^ { \top } U _ { T } U _ { T } ^ { \top } \ell } = \frac { 1 } { \sqrt { \Delta } } \sqrt { ( U _ { T } ^ { \top } \ell ) ^ { 2 } } = \frac { 1 } { \sqrt { \Delta } } \| U _ { T } ^ { \top } \ell \| ,
$$

where here $\| \cdot \|$ denotes the Euclidean norm. We stress the fact that the Cholesky decomposition can be carried out ofline, and the computational benefit is immediate if several samples of the signature are considered.

In the following remark we discuss a possible dimension reduction technique from which one can benefit computationally. Inspired by the approach of Cuchiero et al. (2022); Compagnoni et al. (2023), we employ the Johnson-Lindenstrauss Lemma and consider a random projection of the signature. A first way to use this tool is the following.

Remark 5.6. Let $d _ { < } \in \mathbb { N }$ be the dimension of the space to which we would like to project the signature of order $n > 0$ , such that $d _ { < } \ll ( d + 1 ) _ { n }$ . Consider $A = ( \alpha _ { i j } ) \in \mathbb { R } ^ { d < \times ( d + 1 ) _ { n } }$ , such that $\alpha _ { i j } \sim \mathcal { N } ( 0 , 1 / d _ { < } )$ . Then a possible way to employ the randomised signature is to parametrize the volatility process as follows,

$$
\sigma _ { t } ^ { S } ( \ell ) : = \widetilde { \ell } ^ { \top } A \cdot \mathbf { v e c } ( \widehat { \mathbb { X } } _ { t } ^ { n } )
$$

<!-- page: 20 -->

where with $\tilde { \ell } = \ell \cdot A ^ { \top } \in \mathbb { R } ^ { d _ { < } }$ we denote the randomised parameters. Due to the linearity of integral and conditional expectation in (5.3) this modeling choice is equivalent to consider the randomised matrix $\mathcal { \widetilde { Q } } \in \mathbb { R } ^ { d < \times d _ { < } }$ given by

$$
\widetilde { Q } _ { \mathcal { L } ( I ) \mathcal { L } ( J ) } ( T , \Delta ) : = A Q _ { \mathcal { L } ( I ) \mathcal { L } ( J ) } ( T , \Delta ) A ^ { \top } ,
$$

which leads to the following representation of $\mathrm { V I X } _ { T } ( \ell )$

$$
\mathrm { V I X } _ { T } ( \ell ) = \sqrt { \frac { 1 } { \Delta } \tilde { \ell } ^ { \top } \tilde { Q } ( T , \Delta ) \tilde { \ell } } .
$$

Observe that even if this procedure does not reduce the number iterated integrals to be computed ofline, it reduces the number of parameters to calibrate, yielding in general to a faster evaluation of $\mathrm { V I X } _ { T } ( \ell )$

Remark 5.7 (Options on VIX). Note that VIX options are written on VIX futures. The price process of a VIX future contract with maturity $T > 0$ , is given by

$$
F _ { t } ( T ) : = \mathbb { E } \left[ \mathrm { V I X } _ { T } | \mathcal { F } _ { t } \right] ,\tag{5.10}
$$

and we write in particular $F ( T ) : = F _ { 0 } ( T )$ to simplify notation. We point out that the VIX index does not pay dividends. The correct implied volatility for VIX options can then be obtained by inverting the Black-Scholes formula with interest rate $r > 0$ and $e ^ { - r ( T - t ) } F _ { t } ( T )$ as underlying. When calibrating to VIX options, we stress that we additionally calibrate to VIX futures’ prices, see Section 5.3. This is important since futures prices under the calibrated model are employed to compute its implied volatility surface. Including VIX futures in the calibration leads to a consistent model, both for VIX options and VIX futures, see e.g. Pacati et al. (2018); Guo et al. (2022a); Guyon (2020a, 2023). Using market prices of the VIX futures to invert the implied volatility surface could lead to inconsistencies if one would like to price further derivatives with the calibrated model.

## 5.2 Variance reduction for pricing VIX options

We here discuss variance reduction techniques (see e.g. Glasserman (2004)) that can speed up the calibration in the subsequently applied Monte Carlo approach further. The key idea is to introduce a control variate, namely an easy to evaluate random variable $\Phi ^ { c v }$ such that given $T > 0$ and $K > 0$

$$
\begin{array} { r } { \mathbb { E } [ \Phi ^ { c v } ] = 0 , \mathrm { V a r } \big ( ( \mathrm { V I X } _ { T } ( \ell ) - K ) ^ { + } - \Phi ^ { c v } \big ) < \mathrm { V a r } \big ( ( \mathrm { V I X } _ { T } ( \ell ) - K ) ^ { + } \big ) . } \end{array}
$$

A well-working example of control variates used for pricing and calibrating neural SDE models can be found in Gierjatowicz et al. (2022), where $\Phi ^ { c v }$ is constructed from hedging strategies.

In the following we describe two possible choices of control variates, which consist of polynomials on VIX futures. We stress the fact that these can be seen as linear functions of the signature of the primary process $\widehat { X }$ , hence they belong to the class of sig-payofs, see Lyons et al. (2020); Perez Arribas et al. (2020) and Section 4.2.2 in Cuchiero et al. (2023a).

• The first example is to employ the VIX squared as main ingredient, see for instance Bourgey and De Marco (2022); Guerreiro and Guerra (2023) for a similar choice within a rough Bergomi model for pricing VIX options. This is particularly easy to treat in our set up, as for any given maturity $T > 0$ we have

<!-- page: 21 -->

$$
\mathbb { E } [ \mathrm { V I X } _ { T } ^ { 2 } ( \ell ) ] = \frac { 1 } { \Delta } \ell ^ { \top } Q ^ { c v } ( T , \Delta ) \ell ,
$$

with $Q ^ { c v } ( T , \Delta ) : = \mathbb { E } [ Q _ { \mathcal { L } ( I ) \mathcal { L } ( J ) } ( T , \Delta ) ]$ . By Theorem 5.1 and Theorem 4.4 we indeed have

$$
\begin{array} { r l } & { Q _ { \mathcal { L } ( I ) \mathcal { L } ( J ) } ^ { c v } ( T , \Delta ) = \mathbf { v e c } ( ( e _ { I } \sqcup e _ { J } ) \otimes e _ { 0 } ) ^ { \top } ( e ^ { \Delta G ^ { \top } } - \operatorname { I d } ) \mathbb { E } [ \mathbf { v e c } ( \widehat { \mathbb { X } } _ { T } ^ { 2 n + 1 } ) ] } \\ & { \qquad = \mathbf { v e c } ( ( e _ { I } \operatorname { U d } e _ { J } ) \otimes e _ { 0 } ) ^ { \top } ( e ^ { \Delta G ^ { \top } } - \operatorname { I d } ) e ^ { T G ^ { \top } } \mathbf { v e c } ( \widehat { \mathbb { X } } _ { 0 } ^ { 2 n + 1 } ) } \\ & { \qquad = \mathbf { v e c } ( ( e _ { I } \operatorname { U d } e _ { J } ) \otimes e _ { 0 } ) ^ { \top } ( e ^ { ( T + \Delta ) G ^ { \top } } - e ^ { T G ^ { \top } } ) \mathbf { v e c } ( \widehat { \mathbb { X } } _ { 0 } ^ { 2 n + 1 } ) } \end{array}
$$

where G denotes the $( d { + } 1 ) _ { 2 n + 1 }$ -dimensional matrix representative of the dual operator corresponding to $\widehat { \mathbb X }$ and vec $( \widehat { \mathbb { X } } _ { 0 } ^ { 2 n + 1 } ) = e _ { \varnothing } \in \mathbb { R } ^ { ( d + 1 ) _ { 2 n + 1 } }$

Observe that $Q ^ { c v }$ can again be computed ofline similarly to the matrix $Q$ . Thus to compute the expectation of $\mathrm { V I X } _ { T } ^ { 2 } ( \ell )$ we only have to evaluate the previous quadratic form. To apply this now for pricing a call option with maturity $T > 0$ and strike $K > 0$ , we set

$$
\begin{array} { r } { \Phi ^ { c v } ( \ell , T , K ) : = c _ { T , K } ( \Delta \mathrm { V I X } _ { T } ^ { 2 } ( \ell ) - \ell ^ { \top } Q ^ { c v } ( T , \Delta ) \ell ) , } \\ { = c _ { T , K } ( \ell ^ { \top } ( Q ( T , \Delta ) - Q ^ { c v } ( T , \Delta ) ) \ell ) , } \end{array}
$$

where the constant $c _ { T , K }$ maximizing the variance reduction is given by:

$$
c _ { T , K } ^ { * } = \frac { \mathrm { C o v } ( ( \mathrm { V I X } _ { T } ( \ell ) - K ) ^ { + } , \ell ^ { \top } Q ( T , \Delta ) \ell ) } { \mathrm { V a r } ( \ell ^ { \top } Q ( T , \Delta ) \ell ) } .
$$

Notice that also in this case both $Q$ and $Q ^ { c v }$ satisfy the condition for applying the Cholesky decomposition, leading to a faster evaluation of the control variate as discussed in Remark 5.5. Note that the Cholesky decomposition cannot be applied to $Q - Q ^ { c v }$ , as this is in general an indefinite matrix.

• As a second example we consider a generic polynomial in $\mathrm { { V I X ^ { 2 } } }$ as control variate by defining

$$
Y _ { m } ^ { c v } ( \ell , T , K ) = \sum _ { i = 0 } ^ { m } \alpha _ { i } ( T , K ) ( \mathrm { V I X } _ { T } ^ { 2 } ( \ell ) ) ^ { i }\tag{5.11}
$$

where $\alpha _ { i } ( T , K )$ are chosen to approximate the payof $( \mathrm { V I X } _ { T } - K ) ^ { + }$ with strike price $K$ for some $m \geq 1$ . The corresponding control-variate is then defined as $\Phi ^ { c v } ( \ell , T , K ) : =$ $c _ { T , K } \left( Y _ { m } ^ { c v } ( \ell , T , K ) - \mathbb { E } [ Y _ { m } ^ { c v } ( \ell , T , K ) ] \right)$ . Regarding the computational efort, let us remark the following.

(i) $\mathrm { V I X } _ { T } ^ { 2 }$ is computed anyway for every realisation and is hence already available, therefore the computation of $Y _ { m } ^ { c v } ( \ell , T , K )$ is not expensive.

(ii) It is possible to calculate $\mathbb { E } [ Y _ { m } ^ { c v } ( \ell , T , K ) ]$ analytically relying on the moment formula, see Theorem 4.4.

<!-- page: 22 -->

(iii) The choice of $c _ { T , K } \in \mathbb { R }$ is important and the optimal one, i.e., the one leading the highest variance reduction, is given by the following expression

$$
c _ { T , K } ^ { * } = \frac { \mathrm { C o v } ( ( \mathrm { V I X } _ { T } ( \ell ) - K ) ^ { + } , Y _ { m } ^ { c v } ( \ell , T , K ) ) } { \mathrm { V a r } ( Y _ { m } ^ { c v } ( \ell , T , K ) ) } ,
$$

see for instance Section 4.1.1 in Glasserman (2004).

We stress the fact that for $m = 1$ the two control variates introduced coincide.

## 5.3 Calibration to VIX options

In this section we focus on the calibration to VIX options only. Let $\tau$ be a set of maturities and K a collection of strikes. Consider the model given by (3.1) and (3.2).

Using Monte Carlo compute an approximation of option and futures’ prices with $N _ { M C } >$ 0 samples, i.e.

$$
\pi _ { \mathrm { V I X } } ^ { \mathrm { m o d e l } } ( \ell , T , K ) \approx \frac { e ^ { - r T } } { N _ { M C } } \sum _ { i = 1 } ^ { N _ { M C } } \left( \mathrm { V I X } _ { T } ( \ell , \omega _ { i } ) - K \right) ^ { + } , \qquad F _ { \mathrm { V I X } } ^ { \mathrm { m o d e l } } ( \ell , T ) \approx \frac { 1 } { N _ { M C } } \sum _ { i = 1 } ^ { N _ { M C } } \mathrm { V I X } _ { T } ( \ell , \omega _ { i } ) ,\tag{5.12}
$$

where

$$
\operatorname { V I X } _ { T } ( \ell , \omega ) = \sqrt { \frac { 1 } { \Delta } \ell ^ { \top } Q ( T , \Delta ) ( \omega ) \ell } = \frac { 1 } { \sqrt { \Delta } } \| U _ { T } ^ { \top } ( \omega ) \ell \| .
$$

It is crucial to note that in this framework a Monte Carlo approach is tractable since for every ℓ the same samples can be used. This means that we do not need to carry out any simulation during the optimization task. Indeed, the matrix $Q$ can be simulated ofline while only the products with $\boldsymbol { \ell } \in \mathbb { R } ^ { ( d + 1 ) _ { n } }$ enter in the calibration step.

Observe that an auxiliary randomization can be employed in every optimisation step as discussed in Remark 5.6. Moreover, if we want to use control variates to reduce the variance of the Monte Carlo estimator as described in the previous section, we would consider

$$
\pi _ { \mathrm { V I X } } ^ { \mathrm { m o d e l } } ( \ell , T , K ) \approx \frac { e ^ { - r T } } { N _ { V R } } \sum _ { i = 1 } ^ { N _ { V R } } ( \mathrm { V I X } _ { T } ( \ell , \omega _ { i } ) - K ) ^ { + } - \Phi ^ { c v } ( \ell , T , K ) ( \omega _ { i } ) .
$$

Due to the variance reduction the number of samples needed is $N _ { V R } \ll N _ { M C }$ and $\Phi ^ { c v }$ is as in Section 5.2

The calibration to VIX call options and the corresponding futures on $\tau$ and K consists in minimizing the functional

$$
L _ { \mathrm { V I X } } ( \ell ) : = \sum _ { T \in { \cal T } , K \in K } \mathcal { L } \left( \pi _ { \mathrm { V I X } } ^ { \mathrm { m o d e l } } ( \ell , T , K ) , \pi _ { \mathrm { V I X } } ^ { b , a } ( T , K ) , \sigma _ { \mathrm { V I X } } ^ { b , a } ( T , K ) , F _ { \mathrm { V I X } } ^ { \mathrm { m o d e l } } ( \ell , T ) , F _ { \mathrm { V I X } } ^ { m k t } ( T ) \right) ,\tag{5.13}
$$

where L denotes a real-valued loss function, $F _ { \mathrm { V I X } } ^ { m k t } ( T )$ the market’s futures’ prices and

$$
\pi _ { \mathrm { V I X } } ^ { b , a } ( T , K ) : = \{ \pi _ { \mathrm { V I X } } ^ { m k t , b } ( T , K ) , \pi _ { \mathrm { V I X } } ^ { m k t , a } ( T , K ) \} , \quad \sigma _ { \mathrm { V I X } } ^ { b , a } ( T , K ) : = \{ \sigma _ { \mathrm { V I X } } ^ { m k t , b } ( T , K ) , \sigma _ { \mathrm { V I X } } ^ { m k t , a } ( T , K ) \} ,
$$

the market’s option bid/ask prices $\pi _ { \mathrm { V I X } } ^ { m k t , b } ( T , K ) , \pi _ { \mathrm { V I X } } ^ { m k t , a } ( T , K )$ , and bid/ask implied volatilities $\sigma _ { \mathrm { V I X } } ^ { m k t , b } ( T , K ) , \sigma _ { \mathrm { V I X } } ^ { m k t , a } ( T , K )$ , respectively. We will specify the choice of the function $\mathcal { L }$ in Section 5.3.1 and Section 7.1. In both sections we employ the same optimizer, i.e. BFGS with default parameters in scipy.optimize.

<!-- page: 23 -->

Remark 5.8 (Initial guess search). Since within our model choice we are $\mathrm { g i }$ ven a quadratic function in ℓ to be minimized, a stochastic optimization with an initial guess is employed. In order to achieve faster convergence we consider an hyperparameter search to choose the starting parameters. The steps are outlined as follows.

• Find the magnitude of the coeficients returning Monte Carlo prices of the VIX options close to the one observable on the market. To this extent we sample $N _ { \ell } > 0$ times parameters $\ell \in J _ { i } = [ - 1 0 ^ { - i } , 1 0 ^ { - i } ] ^ { ( d + 1 ) _ { n } }$ , for $i = 1 , \dots$ , m with $m > 0$

• Select $J ^ { * } \in ( J _ { i } ) _ { i = 1 } ^ { m }$ such that

$$
\begin{array} { r } { J ^ { * } \in \mathrm { a r g m i n } _ { i : \ell \in J _ { i } } L _ { \mathrm { V I X } } ( \ell ) . } \end{array}
$$

• Choose the initial guess to be

$$
\begin{array} { r } { \ell _ { \mathrm { i n i t i a l } } \in \mathrm { a r g m i n } _ { \ell \in J ^ { * } } L _ { \mathrm { V I X } } ( \ell ) . } \end{array}
$$

## 5.3.1 Numerical results

In the present section we report the results of the calibration to VIX options only. Here we consider call options written on the VIX on the trading day $0 2 / 0 6 / 2 0 2 1$ , the same as in Guyon and Lekeufack (2023). We stress that for such recent dates the bid-ask spreads for VIX options are rather tight with respect to older dated options as considered for instance in Gatheral et al. (2020); Bondi et al. (2024b). The maturities are reported in the following table with the corresponding range of strikes (in percentage) with respect to the market’s futures prices.

[Table source crop](assets/tables/2023-cuchiero-et-al-signature-spx-vix-p0023-block-0009-1b481f2e6dd71339.jpg)


We underline that the shortest maturity considered is 14 days. Regarding our modeling choice we fix $d = 2 , n = 3$ , which means to calibrate 40 parameters. For X we choose a 2-dimensional Ornstein-Uhlenbeck processes, see Example 4.5, with the following (hyperparameter) configuration:

$$
\kappa = ( 0 . 1 , 2 5 ) ^ { \top } , \qquad \theta = ( 0 . 1 , 4 ) ^ { \top } , \qquad \sigma = ( 0 . 7 , 1 0 ) ^ { \top } , \qquad \rho = \left( { \begin{array} { r r r } { 1 } & { - 0 . 5 7 7 } & { 0 . 3 } \\ { . } & { - 0 . 6 } \\ { . } & { . } & { 1 } \end{array} } \right) ,
$$

where we slightly abuse notation and denote by $\rho$ the correlation matrix of $( X , B )$ . This implies that its last column describes the correlations of X with the Brownian motion B driving the price process S.

These hyperparameters are chosen randomly. Indeed, in spirit of reservoir computing, the idea is to view the OU-process’ signature as (randomly chosen) reservoir, while a simple readout mechanism is trained, i.e. the linear function defined by $\left\{ \ell _ { I } : | I | \leq n \right\}$ , to map the state of the reservoir to the desired output (in our case instantaneous volatilities). However, it is of course possible to perform a hyperparameter optimization or to add expert knowledge, e.g. that a high mean reversion rate is important. We tried the latter by mimicking a rough or strong mean-reverting model as suggested in Rogers (2023); Rømer (2022).

<!-- page: 24 -->

We also refer to Appendix A for numerical results where we use only a correlated 2- dimensional Brownian motion as primary process, which yields significantly worse results. Note that the second simplest choice after Brownian motion within the family of polynomial difusions (also with exact simulation) is the Ornstein-Uhlenbeck process which we thus applied.

Before stating the loss function L that we employed in the calibration task, let us make the following remark.

Remark 5.9. Let $f : \mathbb { R } ^ { + } \times \mathbb { R } ^ { + } \to \mathbb { R } ^ { + }$ be the call pricing functional in the Black-Scholes model, depending on the volatility $\sigma ^ { \mathrm { B S } }$ and the spot price $\xi , \mathrm { i . e . , } f : ( \sigma ^ { \mathrm { B S } } , \xi ) \mapsto f ( \sigma ^ { \mathrm { B S } } , \xi )$ By Taylor expansion in an appropriate neighbourhood of $( \sigma ^ { m k t } , \xi ^ { m k t } )$ we obtain

$$
f ( \sigma ^ { \mathrm { B S } } , \xi ) \approx f ( \sigma ^ { m k t } , \xi ^ { m k t } ) + \frac { \partial f } { \partial \sigma } ( \sigma ^ { m k t } , \xi ^ { m k t } ) ( \sigma ^ { \mathrm { B S } } - \sigma ^ { m k t } ) + \frac { \partial f } { \partial \xi } ( \sigma ^ { m k t } , \xi ^ { m k t } ) ( \xi - \xi ^ { m k t } ) ,
$$

which equivalently gives

$$
( \sigma ^ { \mathrm { B S } } - \sigma ^ { m k t } ) \approx \frac { 1 } { \frac { \partial f } { \partial \sigma } ( \sigma ^ { m k t } , \xi ^ { m k t } ) } \big ( f ( \sigma ^ { \mathrm { B S } } , \xi ) - f ( \sigma ^ { m k t } , \xi ^ { m k t } ) \big ) - \frac { \frac { \partial f } { \partial \xi } ( \sigma ^ { m k t } , \xi ^ { m k t } ) } { \frac { \partial f } { \partial \sigma } ( \sigma ^ { m k t } , \xi ^ { m k t } ) } ( \xi - \xi ^ { m k t } ) ,\tag{5.14}
$$

where we recognize for the derivatives with respect to $\sigma$ and $\xi ,$ the Greeks Vega and Delta, respectively.

Motivated by Remark 5.9 we propose, for a fixed maturity and strike price, the following loss-function for $\beta \in \{ 0 , 1 \}$

$$
\begin{array} { r l r } {  { \mathcal { L } ^ { \beta } ( \pi , \pi ^ { m k t , b , a } , \sigma ^ { m k t , b , a } , F , F ^ { m k t } ) = } } & { ( 5 . 1 5 ) } \\ & { } & { ( \frac { ( \beta \tilde { 1 } _ { \{ \pi \notin [ \pi ^ { m k t , b } , \pi ^ { m k t , a } ] \} } + ( 1 - \beta ) ) | \pi - ( \pi ^ { m k t , a } + \pi ^ { m k t , b } ) / 2 | + | \delta ^ { m k t } e ^ { - r T } ( F - F ^ { m k t } ) | } { { v ^ { m k t } ( \sigma ^ { m k t , a } - \sigma ^ { m k t , b } ) } } ) ^ { 2 } , } \end{array}
$$

where

$\upsilon ^ { m k t }$ and $\delta ^ { m k t }$ denote the Vega and Delta of the option under the Black-Scholes model which depend on the maturity and on the strike price;

$F$ and $F ^ { m k t }$ denote futures with maturity $T$ such that the variables $\xi , \xi ^ { m k t }$ appearing in Remark 5.9 are $\xi = e ^ { - r T } F$ and $\xi ^ { m k t } = e ^ { - r T } F ^ { m k t }$ , respectively;

$\begin{array} { r } { \widetilde { 1 } _ { \{ x \notin [ y ^ { b } , y ^ { a } ] \} } : = s ( y ^ { b } - x ) + s ( x - y ^ { a } ) \mathrm { ~ f o r ~ } s ( x ) : = \frac { 1 } { 2 } \operatorname { t a n h } ( 1 0 0 x ) + \frac { 1 } { 2 } } \end{array}$ a smooth version of the indicator function.

Remark 5.10. (i) We observe that by Remark 5.9 minimizing $\mathcal { L } ^ { 0 }$ is equivalent to minimizing an upper bound of the square of the right-hand side of (5.14) normalized by the bid-ask spread of the implied volatilities. Note that we slightly abused notation, since $\boldsymbol { v } ^ { m k t }$ and $\delta ^ { m k t }$ of course depend on the strike and the maturity.

(ii) Note that as $\begin{array} { r } { \ell \mapsto \mathrm { V I X } _ { T } ( \ell , \omega ) = \frac { 1 } { \sqrt { \Delta } } \| U _ { T } ^ { \top } \ell \| } \end{array}$ is convex and the call payof is convex and increasing, the model option and futures prices are convex in ℓ. If $\beta = 0$ and the initialization of ℓ is such that both the model and futures prices are higher than the market ones, then we actually deal with a convex optimization problem.

<!-- page: 25 -->

(iii) If our aim does not consist in calibrating to the mid-price or mid-implied-volatility precisely, but we merely want to be within the bid-ask spreads we can set $\beta = 1$

For the next calibration result we minimize $\mathcal { L } ^ { 1 }$ as introduced above with $N _ { M C } = 8 0 0 0 0$ Monte Carlo samples for the previous maturities and strikes.

![Implied Volatilities VIX 02-06-2021 Figure 1: The red crosses denote the bid-ask spreads (of the implied volatilities) for each maturity, while the azure dots denote the calibrated implied volatilities of the model. On the x-axis we find the strikes and on the y-axis we find the maturities.](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0025-block-0003-51fd87a8fc589a58.jpg)

We observe that the calibrated VIX smiles fall systematically in the bid-ask interval for all the maturities considered. We report additionally in the next tables the relative error between the market futures prices and the calibrated ones for each maturity, i.e.,

$$
\varepsilon _ { T } : = \frac { | F ^ { m k t } ( T ) - F _ { \mathrm { V I X } } ^ { \mathrm { m o d e l } } ( \ell ^ { * } , T ) | } { F ^ { m k t } ( T ) } ,\tag{5.16}
$$

where $\ell ^ { * } \in \mathbb { R } ^ { 4 0 }$ denotes the calibrated parameters and here $F _ { \mathrm { V I X } } ^ { \mathrm { m o d e l } } ( \ell ^ { * } , T )$ stands for the calibrated future model price. In Figure 2 we can find an illustration of the calibrated and the market futures’ term structure.

[Table source crop](assets/tables/2023-cuchiero-et-al-signature-spx-vix-p0025-block-0007-10ac387044cb4228.jpg)


[Table source crop](assets/tables/2023-cuchiero-et-al-signature-spx-vix-p0025-block-0008-ca2e2f99033cd8da.jpg)


<!-- page: 26 -->

![Figure 2: The blue circles denote the calibrated futures prices and the red crosses the futures prices on the market, in between a linear interpolation is reported.](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0026-block-0001-52d96dde6a97aa8e.jpg)

## 5.4 The case of time-varying parameters

We now consider the case of maturity dependent parameters as for instance employed in Gierjatowicz et al. (2022); Cuchiero et al. (2023a). Since it will be important later on to distinguish maturities of options written on the VIX index from maturities of options written on the SPX index, we introduce the two sets $\mathcal { T } ^ { \mathrm { V I X } }$ and $\tau ^ { \mathrm { S P X } }$ . Let us fix here $\mathcal { T } ^ { \mathrm { V I X } } = \{ T _ { 1 } , \dots , T _ { N } \}$ , where $T _ { i } < T _ { i + 1 }$ for any in $i = 1 , \ldots , N - 1$ and denote by $\ell ( T _ { i } ) \in \mathbb { R } ^ { d _ { n } }$ the parameters depending on the maturity $T _ { i } > 0$ . We set $T _ { 0 } = 0$ and $T _ { N + 1 } = + \infty$ . Then, we consider for any $t \geq 0$ the volatility process to be

$$
\sigma _ { t } ^ { S } ( \ell ) = \sum _ { i = 0 } ^ { N } \sum _ { | I | \leq n } \ell _ { I } ( T _ { i } ) 1 _ { [ T _ { i } , T _ { i + 1 } ) } ( t ) \langle e _ { I } , \widehat { \mathbb { X } } _ { t } \rangle .\tag{5.17}
$$

Therefore the variance process reads as follows,

$$
V _ { t } ( \ell ) = \sum _ { i = 0 } ^ { N } \sum _ { | J | , | I | \leq n } \ell _ { I } ( T _ { i } ) \ell _ { J } ( T _ { i } ) 1 _ { [ T _ { i } , T _ { i + 1 } ) } ( t ) \langle e _ { I } \shuffle e _ { J } , \widehat { \mathbb { X } } _ { t } \rangle .\tag{5.18}
$$

Assumption 5.11. Assume that for a set of maturities $\tau ^ { V I X }$ it holds that $| T _ { i } - T _ { j } | \geq \Delta$ for all $i \neq j$

Proposition 5.12. Let $\mathcal { T } ^ { \mathrm { V I X } }$ be a set of maturities on the VIX index and let $Q ( T , \tau )$ be the matrix as defined in (5.6) (here for general $\tau > 0$ instead of $\Delta )$ . Then, under (5.18) the VIX squared at time $T _ { i } \in \mathcal { T } ^ { \mathrm { V I X } }$ is given by

$$
\mathrm { V I X } _ { T _ { i } } ^ { 2 } ( \ell ) = \frac { 1 } { \Delta } \Big ( \sum _ { j = i } ^ { N } \ell ( T _ { j } ) ^ { \top } \left( Q ( T _ { i } , ( T _ { j + 1 } - T _ { i } ) \wedge \Delta ) - Q ( T _ { i } , ( T _ { j } - T _ { i } ) \wedge \Delta ) \right) \ell ( T _ { j } ) \Big ) .
$$

Note that, if $T _ { i + 1 } - T _ { i } > \Delta$ (which is in particular holds under Assumption 5.11) then,

$$
\mathrm { V I X } _ { T _ { i } } ^ { 2 } ( \ell ) = \frac { 1 } { \Delta } \ell ( T _ { i } ) ^ { \top } Q ( T _ { i } , \Delta ) \ell ( T _ { i } ) .
$$

<!-- page: 27 -->

Proof. By the definition of the VIX, it holds that

$$
\begin{array} { r l } {  { \mathrm { V I X } _ { T _ { i } } ^ { 2 } ( \ell ) - \frac { 1 } { \Delta } \mathbb { E } \Bigg [ \int _ { T _ { i } } ^ { T _ { i } + \Delta } \sum _ { j = i } ^ { N } \underset { | j | , | I | \leq n } { \sum } \ell _ { I } ( T _ { j } ) \ell _ { J } ( T _ { j } ) 1 _ { | I | , | X _ { j + 1 } | } ( t ) \langle e _ { I } \shuffle e _ { j } , \widehat { \mathbb { X } } _ { \ell } \rangle \mathrm { d } t \Bigg | \mathcal { F } _ { T _ { i } } \Bigg ] } \Bigg | } \\ & { = - \frac { 1 } { \Delta } \sum _ { j = i } ^ { N } \underset { | J | , | I | \leq n } { \sum } \ \epsilon _ { I } ( T _ { j } ) \ell _ { J } ( T _ { j } ) \mathbb { E } \Bigg [ \int _ { T _ { j } \land ( T _ { i } + \Delta ) } ^ { T _ { j + 1 } \land ( T _ { i } + \Delta ) } \langle e _ { I } \shuffle e _ { j } , \widehat { \mathbb { X } } _ { \ell } \rangle \mathrm { d } t \Bigg | \mathcal { F } _ { T _ { i } } \Bigg ] } \\ & { = \frac { 1 } { \Delta } \sum _ { j = i } ^ { N } \underset { | J | , | I | \leq n } { \sum } \ \ell _ { I } ( T _ { j } ) \ell _ { J } ( T _ { j } ) \Bigg ( \mathbb { E } \Bigg [ \int _ { T _ { i } } ^ { T _ { j + 1 } \land ( T _ { i } + \Delta ) } \langle e _ { I } \shuffle e _ { j } , \widehat { \mathbb { X } } _ { \ell } \rangle \mathrm { d } t \Bigg | \mathcal { F } _ { T _ { i } } \Bigg ] } \\ & { \qquad - \mathbb { E } \Bigg [ \int _ { T _ { j } } ^ { T _ { j } \land ( T _ { j } + \Delta ) } \langle e _ { I } \shuffle e _ { j } , \widehat { \mathbb { X } } _ { \ell } \rangle \mathrm { d } t \Bigg | \mathcal { F } _ { T _ { i } } \Bigg ] \Bigg ) } \end{array}
$$

and hence the first statement follows by the definition of $Q$ in (5.6).

Notice that also in the case of Proposition 5.12, Remark 5.5 applies.

## 6 SPX as a signature-based model

The goal of this section is to express the discounted, dividend-adjusted price of the SPX, modeled via (3.1)-(3.2)

$$
\mathrm { d } S _ { t } ( \ell ) = S _ { t } ( \ell ) \sigma _ { t } ^ { S } ( \ell ) \mathrm { d } B _ { t } ,
$$

in terms of the signature of $( t , X _ { t } , B _ { t } ) _ { t \geq 0 }$ , allowing again to precompute its samples and use the same ones for every ℓ. This is in the same spirit as in Cuchiero et al. (2023a), even though there the asset price was directly modeled as linear function of the signature of some primary process.

Recall that by (3.2) $\sigma ^ { S }$ is parametrized as follows

$$
\sigma _ { t } ^ { S } ( \ell ) : = \ell _ { \varnothing } + \sum _ { 0 < | I | \leq n } \ell _ { I } \langle e _ { I } , \widehat { \mathbb { X } } _ { t } \rangle ,
$$

where $\widehat { X } _ { t } = \left( t , X _ { t } \right)$ with X a d-dimensional polynomial difusion X in the sense of Definition 3.1. Before addressing a more tractable expression for S, that allows to avoid (Euler) simulation schemes, we recall the following well-known integrability result.

Lemma 6.1. Assume that $\mathbb { E } [ S _ { 0 } ] < \infty$ . Then, the process $( S _ { t } ) _ { t \geq 0 }$ is a (non-negative) supermartingale and in particular $\mathbb { E } [ S _ { t } ] <$ ∞ for each $t \geq 0$

Proof. Note that $\begin{array} { r } { S _ { t } = S _ { 0 } \mathcal { E } \left( \int _ { 0 } ^ { \cdot } \sigma _ { s } ^ { S } \mathrm { d } B _ { s } \right) } \end{array}$  for all $t \geq 0$ . Moreover $\textstyle { \bigl ( } \int _ { 0 } ^ { t } \sigma _ { s } ^ { S } \mathrm { d } B _ { s } { \bigr ) } _ { t \geq 0 }$ is a local martingale and hence, by the properties of the stochastic exponential, $S _ { t }$ is a non-negative local martingale. It follows from Fatou’s Lemma that non-negative local martingales are supermartingales. □

In the following we suppose without loss of generality that $S _ { 0 } = 1$

Remark 6.2. Recall that if Novikov’s condition is satisfied, then a stochastic exponential of the form $\begin{array} { r } { S _ { t } = \mathcal { E } \left( \int _ { 0 } ^ { \cdot } \sigma _ { s } ^ { S } \mathrm { d } B _ { s } \right) } \end{array}$ for $t \in [ 0 , T ]$ is a true martingale. For $\sigma _ { s } ^ { S }$ as in (3.2), such t condition reads

$$
\mathbb { E } \left[ \exp \left\{ \frac { 1 } { 2 } \int _ { 0 } ^ { T } V _ { t } ( \ell ) \mathrm { d } t \right\} \right] < + \infty .
$$

<!-- page: 28 -->

Observe that

$$
\begin{array} { r l } { \mathbb { E } \left[ \exp \left\{ \displaystyle \frac { 1 } { 2 } \int _ { 0 } ^ { T } V _ { t } ( \ell ) \mathrm { d } t \right\} \right] } & { = \mathbb { E } \left[ \exp \left\{ \displaystyle \frac { 1 } { 2 } \sum _ { | I | , | J | \leq n } \ell _ { I } \ell _ { J } \int _ { 0 } ^ { T } \langle e _ { I } \shuffle e _ { J } , \widehat { \mathbb { X } } _ { t } \rangle \mathrm { d } t \right\} \right] } \\ & { = \mathbb { E } \left[ \exp \left\{ \displaystyle \frac { 1 } { 2 } \ell ^ { \top } Q ^ { 0 } ( T ) \ell \right\} \right] , } \end{array}\tag{6.1}
$$

where for $\mathcal { L } : \{ I : | I | \leq n \} \to \{ 1 , \ldots , ( d + 1 ) _ { n } \}$ 2

$$
Q _ { \mathcal { L } ( I ) \mathcal { L } ( J ) } ^ { 0 } ( T ) : = \langle ( e _ { I } \sqcup e _ { J } ) \otimes e _ { 0 } , \widehat { \mathbb { X } } _ { T } \rangle .
$$

We point out that the previous condition is not necessarily satisfied for all $\ell \in \mathbb { R } ^ { ( d + 1 ) n }$ Indeed, let us consider $X$ to be a one-dimensional Brownian motion and choose ℓ such that the only non trivial component is the last one, i.e.,

$$
\ell _ { I } : = \left\{ \begin{array} { l l } { { c \in \mathbb { R } , } } & { { \mathrm { i f ~ } I = ( 1 , \ldots , 1 ) , ~ | I | = n , } } \\ { { 0 , } } & { { \mathrm { o t h e r w i s e } . } } \end{array} \right.\tag{6.2}
$$

Then, (6.1) translates into

$$
\mathbb { E } \biggl [ \exp \biggl \{ \frac { c ^ { 2 } } { 2 } \int _ { 0 } ^ { T } \frac { 2 n \mathrm { ! } } { n \mathrm { ! } n \mathrm { ! } } \frac { X _ { t } ^ { 2 n } } { 2 n \mathrm { ! } } \mathrm { d } t \biggr \} \biggr ] = \mathbb { E } \biggl [ \exp \biggl \{ \frac { c ^ { 2 } } { 2 ( n \mathrm { ! } ) ^ { 2 } } \int _ { 0 } ^ { T } X _ { t } ^ { 2 n } \mathrm { d } t \biggr \} \biggr ] ,
$$

which is not finite in general, e.g. if $n = 2 , c = \sqrt { 2 } ( n ! )$ then by Jensen’s inequality it follows

$$
\mathbb { E } \bigg [ \exp \bigg \{ \int _ { 0 } ^ { T } X _ { t } ^ { 4 } \mathrm { d } t \bigg \} \bigg ] \geq \mathbb { E } \bigg [ \frac { 1 } { T } \int _ { 0 } ^ { T } e ^ { T X _ { t } ^ { 4 } } \mathrm { d } t \bigg ] = \frac { 1 } { T } \int _ { 0 } ^ { T } \mathbb { E } [ e ^ { T X _ { t } ^ { 4 } } ] \mathrm { d } t = + \infty .
$$

Remark 6.3. As well known from the results of Delbaen and Schachermayer (1994) the existence of an equivalent local martingale measure is suficient for NFLVR, and risk neutral pricing works, too. This is important when the process $S ( \ell )$ is a non-negative true local martingale such that E $[ S _ { T } ( \ell ) ] < S _ { 0 }$ . If one could go short in the asset, and thus gets $S _ { 0 } ( \ell )$ 2 and long in the ‘call option with strike $0 ^ { \prime }$ (corresponding to the payof $S _ { T } ( \ell ) )$ with price $\mathbb { E } [ S _ { T } ( \ell ) ] < S _ { 0 } ( \ell )$ , an arbitrage would be created. But the latter is simply not allowed as trading strategy under NFLVR. We address the reader to Kardaras et al. (2015) for further details.

The key idea is to rewrite (3.1) as a type of signature-based model in sense of Cuchiero et al. (2023a) including $B = ( B _ { t } ) _ { t \geq 0 }$ as part of the primary process. This is possible since Itˆo integrals with respect to primary process’ components can be rewritten as linear functions of the signature of the primary process itself. Before stating the result we need to introduce some auxiliary notation. We denote by $( Z _ { t } ) _ { t \geq 0 }$ the $( d + 1 )$ -dimensional process given by

$$
Z _ { t } = ( X _ { t } , B _ { t } ) ,\tag{6.3}
$$

by $( \widehat { Z } _ { t } ) _ { t \geq 0 }$ its time extension, and by $( \widehat { \mathbb { Z } } _ { t } ) _ { t \geq 0 }$ the signature of $( \widehat { Z } _ { t } ) _ { t \geq 0 }$ . With a slight abuse of notation we again denote by $\rho$ the correlation matrix process between the components of $Z .$ . Observe that $\rho$ encodes in particular the correlation between X and B. Finally, we let $a _ { i j } ^ { J } \in \mathbb { R }$ denote the coeficients satisfying

$$
\mathrm { d } [ Z ^ { i } , Z ^ { j } ] _ { t } = \sum _ { | J | \leq 2 } a _ { i j } ^ { J } \langle e _ { J } , \widehat { \mathbb { Z } } _ { t } \rangle \mathrm { d } t ,
$$

for each $i , j \in \{ 1 , \ldots , d + 1 \}$

<!-- page: 29 -->

Proposition 6.4. Let $S = ( S _ { t } ) _ { t \geq 0 }$ satisfy (3.1) with $S _ { 0 } = 1$ , and $\sigma ^ { S } = ( \sigma _ { t } ^ { S } ) _ { t \geq 0 }$ satisfy (3.2). Then,

$$
\log ( S _ { t } ( \ell ) ) = - \frac { 1 } { 2 } \ell ^ { \top } Q ^ { 0 } ( t ) \ell + \sum _ { | I | \leq n } \ell _ { I } \langle \widetilde { e } _ { I } ^ { B } , \widehat { \mathbb { Z } } _ { t } \rangle ,\tag{6.4}
$$

where

$$
\tilde { e } _ { \emptyset } ^ { B } : = e _ { d + 1 } , \qquad \tilde { e } _ { I } ^ { B } : = e _ { I } \otimes e _ { d + 1 } - \sum _ { | J | \leq 2 } \frac { a _ { i _ { | I | } ( d + 1 ) } ^ { J } } { 2 } ( e _ { I ^ { \prime } } \sqcup e _ { J } ) \otimes e _ { 0 } ,
$$

for each $| I | > 0$ , and the components of the matrix $Q ^ { 0 } ( t ) \in \mathbb { R } ^ { ( d + 1 ) _ { n } \times ( d + 1 ) _ { n } }$ are given by

$$
\begin{array} { r } { Q _ { \mathcal { L } ( I ) \mathcal { L } ( J ) } ^ { 0 } ( t ) = \langle ( e _ { I } \sqcup e _ { J } ) \otimes e _ { 0 } , \widehat { \mathbb { X } } _ { t } \rangle , } \end{array}
$$

for a labeling function $\mathcal { L } : \{ I : | I | \leq n \} \to \{ 1 , \ldots , ( d + 1 ) _ { n } \}$

Proof. We can compute

$$
\begin{array} { r l } { \log ( S _ { t } ( \ell ) ) = - \displaystyle \frac { 1 } { 2 } \int _ { 0 } ^ { t } V _ { s } ( \ell ) \mathrm { d } s + \int _ { 0 } ^ { t } \sigma _ { s } ^ { S } ( \ell ) \mathrm { d } B _ { s } } & { } \\ { = - \displaystyle \frac { 1 } { 2 } \sum _ { | I | , | J | \leq n } \ell _ { I } \ell _ { J } \int _ { 0 } ^ { t } \langle e _ { I } \shuffle e _ { J } , \widehat { \mathbb { X } } _ { s } \rangle \mathrm { d } s + \displaystyle \sum _ { | I | \leq n } \ell _ { I } \int _ { 0 } ^ { t } \langle e _ { I } , \widehat { \mathbb { X } } _ { s } \rangle \mathrm { d } B _ { s } } & { } \\ { \displaystyle \stackrel { ( * ) } { = } - \displaystyle \frac { 1 } { 2 } \sum _ { | I | , | J | \leq n } \ell _ { I } \ell _ { J } \langle ( e _ { I } \shuffle e _ { J } ) \otimes e _ { 0 } , \widehat { \mathbb { X } } _ { t } \rangle + \displaystyle \sum _ { | I | \leq n } \ell _ { I } \langle \tilde { e } _ { I } ^ { B } , \widehat { \mathbb { Z } } _ { t } \rangle } & { } \\ { = - \displaystyle \frac { 1 } { 2 } \ell ^ { 7 } Q ^ { 0 } ( t ) \ell + \displaystyle \sum _ { | I | < n } \ell _ { I } \langle \tilde { e } _ { I } ^ { B } , \widehat { \mathbb { Z } } _ { t } \rangle , } & { } \end{array}
$$

where for (∗) we used that $\begin{array} { r } { \int _ { 0 } ^ { t } \langle e _ { I } , \widehat { \mathbb { X } } _ { s } \rangle \mathrm { d } B _ { s } = \langle \widetilde { e } _ { I } ^ { B } , \widehat { \mathbb { Z } } _ { t } \rangle } \end{array}$ by Lemma 3.10 in Cuchiero et al. (2023a). □

Remark 6.5. Consider again the model described in Remark 3.2. Then the results of Proposition 6.4 still hold with

$$
Q _ { \mathcal { L } ( I ) \mathcal { L } ( J ) } ^ { 0 } ( t ) : = \int _ { 0 } ^ { t } \langle e _ { I } \shuffle e _ { J } , \widehat { \mathbb { X } } _ { s - \varepsilon , s } \rangle { \mathrm { d } } s ,
$$

and $\begin{array} { r } { \int _ { 0 } ^ { t } \langle e _ { I } , \widehat { \mathbb { X } } _ { s - \varepsilon , s } \rangle \mathrm { d } B _ { s } } \end{array}$ instead of $\langle \tilde { e } _ { I } ^ { B } , \widehat { \mathbb { Z } } _ { t } \rangle$ . Since the proof follows closely the proof of the original result, we omit it.

Remark 6.6. • Observe that since the matrix $( \langle e _ { I } \sqcup e _ { J } , \widehat { \mathbb { X } } _ { t } \rangle ) _ { | I | , | J | \leq n }$ is positive semidefinite, by monotonicity of the time integral on [0, t] for some $t > 0$ , we also have

$$
\ell ^ { \top } Q ^ { 0 } ( t ) \ell \geq 0 ,
$$

for all $\boldsymbol { \ell } \in \mathbb { R } ^ { ( d + 1 ) _ { n } }$ . This means that for any $t > 0$ , we can rewrite the log-price as

$$
\log ( S _ { t } ) = - \frac { 1 } { 2 } \| ( U _ { t } ^ { 0 } ) ^ { \top } \ell \| ^ { 2 } + \sum _ { | I | \leq n } \ell _ { I } \langle \widetilde { e } _ { I } ^ { B } , \widehat { \mathbb { Z } } _ { t } \rangle ,
$$

where $U _ { t } ^ { 0 }$ is the upper-triangular matrix of the Cholesky decomposition of $Q ^ { 0 } ( t )$

<!-- page: 30 -->

• Notice that the log-price model in (6.4), it is not exactly a signature-based model in the sense of Cuchiero et al. (2023a), as here it is given by a linear part in the parameters ℓ and an additional quadratic part. It can also be rewritten as

$$
\mathrm { d } \log ( S _ { t } ) = - \frac { 1 } { 2 } \ell ^ { \top } \tilde { Q } ( t ) \ell \mathrm { d } t + \ell ^ { \top } { \mathbf { v e c } ( \widehat { \mathbb { X } } _ { t } ^ { n } ) } \mathrm { d } B _ { t } ,
$$

where $\tilde { Q }$ is given by

$$
\tilde { Q } _ { \mathcal { L } ( I ) \mathcal { L } ( J ) } ( t ) : = \langle e _ { I } \shuffle \sqcup e _ { J } , \widehat { \mathbb { X } } _ { t } \rangle .
$$

Hence, the relevant factors entering in the dynamics of log S and $\sigma ^ { S }$ are the components of ${ \widehat { \mathbb { X } } } ^ { 2 n }$ . Note also that $( \log S , \widehat { \mathbb { X } } ^ { 2 n } )$ is a $1 + ( d + 1 ) _ { 2 n }$ dimensional polynomial diffusion (see (2.1)), whence in particular Markovian. This is in spirit of path-dependent factor model, for instance also considered in Guyon and Lekeufack (2023), with the additional tractability feature that $( \log S , \widehat { \mathbb { X } } ^ { 2 n } )$ is a polynomial difusion. Therefore all techniques for polynomial processes in view of pricing and hedging can be applied.

• In order to sample the log-price at maturity, consistently with the VIX, we follow the following road map. We simulate $\widehat { \mathbb { Z } }$ and compute $\langle \tilde { e } _ { I } ^ { B } , \widehat { \mathbb { Z } } \rangle$ for each I as specified above. Next, we drop from the samples of $\widehat { \mathbb { Z } }$ the terms where B appears, i.e. the components corresponding to indices containing the letter d + 1. The result coincides with a sampling of $\widehat { \mathbb X }$ and is then used to work with both $Q$ and $Q ^ { 0 }$

This is equivalent to sampling $\widehat { \mathbb X }$ for the variance process and to compute an additional Itˆo integral as in (3.1).

In the following corollary we state the form of $\tilde { e } _ { I } ^ { B }$ when X is d-dimensional OU-process. We omit the proof for sake of brevity.

Corollary 6.7. Let X be a d-dimensional OU-process as in Example 4.5 driven by a ddimensional Brownian motion with correlation matrix $\rho .$ Then $\tilde { e } _ { I } ^ { B }$ is given by

$$
\tilde { e } _ { I } ^ { B } = e _ { I } \otimes e _ { d + 1 } - \frac { 1 } { 2 } 1 _ { \{ i _ { | I | } \neq 0 \} } \big ( \sigma ^ { i _ { | I | } } \rho _ { i _ { | I | } d + 1 } \big ) e _ { I ^ { \prime } } \otimes e _ { 0 } ,
$$

for any multi-index $I \neq \emptyset$

Remark 6.8 (Variance reduction for pricing SPX options). Observe that a possible control variate for reducing the variance of the Monte Carlo estimator for pricing SPX options is the value at maturity of the log-price process. This means,

$$
\Phi ^ { c v } ( \ell , T , K ) : = c _ { T , K } \Big ( \log ( S _ { T } ( \ell ) ) + \frac { 1 } { 2 } \ell ^ { \top } Q ^ { 0 , c v } ( T ) \ell \Big ) ,
$$

where, using that the linear part (in ℓ) of $\log ( S _ { T } ( \ell ) )$ vanishes under the risk-neutral expectation, we have

$$
\begin{array} { r } { Q _ { \mathcal { L } ( I ) \mathcal { L } ( J ) } ^ { 0 , c v } ( T ) = \mathbf { v e c } ( ( e _ { I } \sqcup e _ { J } ) \otimes e _ { 0 } ) ^ { \top } e ^ { T G ^ { \top } } \mathbf { v e c } ( \widehat { \mathbb { X } } _ { 0 } ^ { 2 n + 1 } ) , } \end{array}
$$

for $G \in \mathbb { R } ^ { ( d + 1 ) _ { 2 n + 1 } \times ( d + 1 ) _ { 2 n + 1 } }$ denoting the $( d + 1 ) _ { 2 n + 1 }$ -dimensional matrix representative of the dual operator corresponding to $\succnapprox$ . We choose the optimal $c _ { T , K } ^ { * } \in \mathbb { R }$ as

$$
c _ { T , K } ^ { * } = \frac { \mathrm { C o v } ( ( S _ { T } ( \ell ) - K ) ^ { + } , \log ( S _ { T } ( \ell ) ) ) } { \mathrm { V a r } ( \log ( S _ { T } ( \ell ) ) ) } .
$$

<!-- page: 31 -->

## 6.1 Exploiting the afine nature of the signature: Fourier pricing of SPX and VIX options

This section is dedicated to outline how the linear parametrizations of the log-price and the volatility process in $\widehat { \mathbb { Z } }$ can be used for Fourier pricing. Assume that

$$
\mathrm { d } Z _ { t } ^ { j } = \kappa ^ { j } ( \theta ^ { j } - Z _ { t } ^ { j } ) \mathrm { d } t + \sigma ^ { j } \mathrm { d } W _ { t } ^ { j } , \qquad Z _ { 0 } ^ { j } = 0 ,
$$

for each $j = 1 , \ldots , d + 1$ , where W denotes a $( d + 1 )$ -dimensional Brownian motion with $W ^ { d + 1 } = B$ . All parameters $\kappa ^ { j } , \theta ^ { j } , \sigma ^ { j }$ are in R with $\kappa ^ { \dot { d } + 1 } = \theta ^ { d + 1 } = 0$ and $\sigma ^ { d + 1 } = 1$ so that $\begin{array} { r } { Z ^ { d + 1 } = W ^ { d + 1 } = B } \end{array}$ . Note that we do not account for correlations.

We illustrate now how to apply the results of Cuchiero et al. (2023b) in the present setting. Since $( \widehat { Z } _ { t } ) _ { t > 0 }$ is a polynomial difusion, by Lemma 4.1 there are b $\in ( T ( ( \mathbb { R } ^ { d + 2 } ) ) ) ^ { d + 2 }$ and $\mathbf { a } \in ( T ( ( \mathbb { R } ^ { d + 2 } ) ) ) ^ { \overline { { ( d + 2 ) \times ( d + 2 ) } } }$ such that

$$
\mathrm { d } \widehat { Z } _ { t } ^ { j } = \langle \mathbf { b } _ { j } , \widehat { \mathbb { Z } } _ { t } \rangle \mathrm { d } t + \sqrt { \langle \mathbf { a } _ { j j } , \widehat { \mathbb { Z } } _ { t } \rangle } \mathrm { d } W _ { t } ^ { j } ,
$$

where ${ \bf b } _ { j } = \kappa ^ { j } \theta ^ { j } e _ { \varnothing } - \kappa _ { j } e _ { j }$ and ${ \bf a } _ { j j } = ( \sigma ^ { j } ) ^ { 2 } e _ { \emptyset }$ , using that (with a small abuse of notation) $\kappa ^ { 0 } \theta ^ { 0 } : = \bar { 1 } , \kappa ^ { j } : = 0$ and $\sigma ^ { 0 } : = 0$ . Consider then the Riccati operator R given by

$$
\mathcal { R } ( \mathbf { u } ) = \sum _ { j = 0 } ^ { d + 1 } \sum _ { | I | \geq 0 } \Big ( \kappa ^ { j } \theta ^ { j } \mathbf { u } _ { ( I j ) } e _ { I } + \kappa ^ { j } \mathbf { u } _ { ( I j ) } e _ { j } \operatorname { l d } e _ { I } + \frac { 1 } { 2 } ( \sigma ^ { j } ) ^ { 2 } \big ( \mathbf { u } _ { ( I j j ) } e _ { I } + \mathbf { u } _ { ( I j ) } ^ { 2 } e _ { I } \operatorname { l d } e _ { I } \big ) \Big ) .
$$

By Theorem 4.23 in Cuchiero et al. (2023b), we expect that

$$
\mathbb { E } [ \exp ( \langle \mathbf { u } , \widehat { \mathbb { Z } } _ { T } \rangle ) ] = \exp ( \psi ( T ) _ { \emptyset } ) ,
$$

where $\psi$ is a solution of the extended tensor algebra valued Riccati equation<sup>4</sup>

$$
\partial _ { t } \boldsymbol { \psi } ( t ) = \mathcal { R } ( \boldsymbol { \psi } ( t ) ) , \quad \boldsymbol { \psi } ( 0 ) = { \bf u } .\tag{6.5}
$$

Choosing u as

$$
\mathbf { u } ( \ell ) : = - \frac 1 2 ( \ell \sqcup \ell ) \otimes e _ { 0 } + \tilde { \ell }
$$

where $\begin{array} { r } { \tilde { \ell } : = \sum _ { | I | \leq n } \ell _ { I } \tilde { e } _ { I } ^ { B } } \end{array}$ , by Proposition 6.4 we get

$$
\log ( S _ { t } ( \ell ) ) = \langle \mathbf { u } ( \ell ) , \widehat { \mathbb { Z } } _ { t } \rangle .
$$

The representation of the Fourier-Laplace transform described above can then be used for Fourier pricing. We dedicate the remaining part of this section to illustrate how this can be done.

From Fourier analysis we know that for $K > 0$ and $C < 0$ it holds

$$
( K - e ^ { y } ) ^ { + } = \frac { 1 } { 2 \pi } \int _ { \mathbb { R } } e ^ { ( i \lambda + C ) y } \frac { K ^ { - C + 1 - i \lambda } } { ( i \lambda + C ) ( i \lambda + C - 1 ) } \mathrm { d } \lambda .
$$

<sup>4</sup>We refer to Cuchiero et al. (2023b) for the appropriate solution concept and to a numerical treatment in the one dimensional case where (6.5) reduces to a sequence-valued Riccati equation.

<!-- page: 32 -->

This in particular implies that

$$
\begin{array} { l } { \displaystyle \mathbb { E } [ ( K - S _ { T } ( \ell ) ) ^ { + } ] = \frac { 1 } { 2 \pi } \int _ { \mathbb { R } } \mathbb { E } [ e ^ { ( i \lambda + C ) \log ( S _ { T } ( \ell ) ) } ] \frac { K ^ { - C + 1 - i \lambda } } { ( i \lambda + C ) ( i \lambda + C - 1 ) } \mathrm { d } \lambda } \\ { \displaystyle \qquad = \frac { 1 } { 2 \pi } \int _ { \mathbb { R } } \mathbb { E } [ e ^ { \langle \mathbf { u } _ { \lambda } , \widehat { \mathbb { Z } } _ { T } \rangle } ] \frac { K ^ { - C + 1 - i \lambda } } { ( i \lambda + C ) ( i \lambda + C - 1 ) } \mathrm { d } \lambda } \\ { \displaystyle \qquad = \frac { 1 } { 2 \pi } \int _ { \mathbb { R } } e ^ { \psi _ { \lambda } ( T ) _ { \varnothing } } \frac { K ^ { - C + 1 - i \lambda } } { ( i \lambda + C ) ( i \lambda + C - 1 ) } \mathrm { d } \lambda , } \end{array}
$$

where $\mathbf { u } _ { \lambda } : = ( i \lambda + C ) \mathbf { u } ( \ell )$ and $\psi _ { \lambda }$ is a solution of the Riccati equation with initial condition $\psi _ { \lambda } ( 0 ) = { \bf u } _ { \lambda }$

Let us now consider the case of VIX options where Fourier pricing can be applied by computing the Fourier-Laplace transform of VIX squared, see also Sepp (2008); Papanicolaou and Sircar (2014); Bondi et al. (2024b) and references therein for a Fourier-based approach to pricing VIX options. Fix a labelling injective function $\mathcal { L } : \{ I \colon | I | \leq n \} \to$ $\left\{ 1 , \ldots , ( d + 1 ) _ { ( 2 n + 1 ) } \right\}$ as introduced before (2.2) and recall that by Theorem 5.1 it holds

$$
\mathrm { V I X } _ { T } ^ { 2 } ( \ell ) = \frac { 1 } { \Delta } \ell ^ { \top } Q ( T , \Delta ) \ell
$$

for

$$
Q _ { \mathcal { L } ( I ) \mathcal { L } ( J ) } ( T , \Delta ) = \sum _ { e _ { K } = ( e _ { I } \sqcup e _ { J } ) \otimes e _ { 0 } } \sum _ { | H | \leq 2 n + 1 } ( e ^ { \Delta G ^ { \top } } - \operatorname { I d } ) _ { \mathcal { L } ( K ) \mathcal { L } ( H ) } \langle e _ { H } , \widehat { \mathbb { X } } _ { T } \rangle .
$$

where G denotes the $( d + 1 ) _ { ( 2 n + 1 ) }$ -dimensional matrix representative of the dual operator corresponding to $\widehat { \mathbb X }$

Setting for $| I | , | J | \leq n$

$$
I ( \Delta ) \mathbf { u } : = \sum _ { | K | , | H | \leq 2 n + 1 } ( e ^ { \Delta G ^ { \top } } - \operatorname { I d } ) \mathcal { L } ( K ) \mathcal { L } ( H ) \mathbf { u } _ { K } e _ { H }
$$

we can write

$$
\begin{array} { r l } & { \mathrm { V I X } _ { T } ^ { 2 } ( \ell ) = \displaystyle \frac { 1 } { \Delta } \sum _ { | I | , | J | \leq n } \ell _ { I } \ell _ { J } \sum _ { \substack { e _ { K } = ( e _ { I } \sqcup | e _ { J } ) \otimes e _ { 0 } | H | \leq 2 n + 1 } } ( e ^ { \Delta G ^ { \top } } - \mathrm { I d } ) _ { \mathscr { L } ( K ) \mathscr { L } ( H ) } \langle e _ { H } , \widehat { \mathbb { X } } _ { T } \rangle } \\ & { \quad \quad \quad = \displaystyle \frac { 1 } { \Delta } \sum _ { | K | , | H | \leq 2 n + 1 } ( e ^ { \Delta G ^ { \top } } - \mathrm { I d } ) _ { \mathscr { L } ( K ) \mathscr { L } ( H ) } \langle e _ { K } , ( \ell \sqcup \ell ) \otimes e _ { 0 } \rangle \langle e _ { H } , \widehat { \mathbb { X } } _ { t } \rangle } \\ & { \quad \quad \quad = \displaystyle \frac { 1 } { \Delta } \langle I ( \Delta ) ( ( \ell \sqcup \ell ) \otimes e _ { 0 } ) , \widehat { \mathbb { X } } _ { T } \rangle . } \end{array}
$$

Also in this case since $\begin{array} { r } { \frac { 1 } { \sqrt { 2 \pi } } \int _ { \mathbb { R } } e ^ { i \lambda y } ( K - \sqrt { | y | } ) ^ { + } \mathrm { d } y = \frac { \sqrt { \frac { 2 } { \pi } } F _ { S } ( K \sqrt { | \lambda | } ) } { | \lambda | ^ { 3 / 2 } } } \end{array}$ is integrable for $F _ { S } ( u ) =$ $\begin{array} { r } { \int _ { 0 } ^ { u } \sin ( z ^ { 2 } ) \mathrm { d } z } \end{array}$ , Fourier analysis yields

$$
( K - \sqrt { y } ) ^ { + } = \frac { 1 } { \pi } \int _ { \mathbb { R } } e ^ { - i \lambda y } \frac { F _ { S } ( K \sqrt { | \lambda | } ) } { | \lambda | ^ { 3 / 2 } } \mathrm { d } \lambda ,
$$

for each $y \geq 0$ . This in particular implies that

$$
\mathbb { E } [ ( K - \mathrm { V I X } _ { T } ( \ell ) ) ^ { + } ] = \frac { 1 } { \pi } \int _ { \mathbb { R } } \mathbb { E } [ e ^ { - i \lambda \mathrm { V I X } _ { T } ^ { 2 } ( \ell ) } ] \frac { F _ { S } ( K \sqrt { | \lambda | } ) } { | \lambda | ^ { 3 / 2 } } \mathrm { d } \lambda = \frac { 1 } { \pi } \int _ { \mathbb { R } } e ^ { \psi _ { \lambda } ( T ) _ { \mathfrak { g } } } \frac { F _ { S } ( K \sqrt { | \lambda | } ) } { | \lambda | ^ { 3 / 2 } } \mathrm { d } \lambda ,
$$

<!-- page: 33 -->

where $\psi _ { \lambda }$ is a solution of the Riccati equation with initial condition $\psi _ { \lambda } ( 0 ) = - i \lambda \mathbf { v } ( \boldsymbol { \ell } )$ for $\mathbf { v } ( \ell ) : = { \frac { 1 } { \Delta } } I ( \Delta ) ( ( \ell \sqcup \ell ) \otimes e _ { 0 } )$

Analogous formulations in terms of the error function are also possible, see for instance Bondi et al. (2024b). In the same spirit one can also obtain a representation of futures prices. We here do not provide an implementation of this Fourier pricing approach but numerical experiments can be found in Cuchiero et al. (2023b).

## 6.2 The case of time-varying parameters

Analogously to Section 5.4, we now further enhance Proposition 6.4 by allowing the parameters ℓ to depend on the maturity.

Proposition 6.9. Let $S = ( S _ { t } ) _ { t \geq 0 }$ satisfy (3.1) with $S _ { 0 } = 1$ , and $( \sigma _ { t } ^ { S } ) _ { t \geq 0 }$ satisfy (5.17) for a set of maturities $\mathcal { T } ^ { \mathrm { V I X } } = \{ T _ { 1 } , \ldots , T _ { N } \}$ . Recall that in this case $V = ( V _ { t } ) _ { t \geq 0 }$ satisfy

$$
V _ { t } ( \ell ) = \sum _ { i = 0 } ^ { N } \sum _ { | J | , | I | \leq n } \ell _ { I } ( T _ { i } ) \ell _ { J } ( T _ { i } ) 1 _ { [ T _ { i } , T _ { i + 1 } ) } ( t ) \langle e _ { I } \shuffle e _ { J } , \widehat { \mathbb { X } } _ { t } \rangle .
$$

Then, with the notation of Proposition 6.4 we write the following recursion for the log-price process

$$
\begin{array} { l } { { \displaystyle \log \bigl ( S _ { t } ( { \ell ^ { < m + 1 } } ) \bigr ) = \sum _ { i = 0 } ^ { N } \bigg [ - \frac { 1 } { 2 } \ell ( T _ { i } ) ^ { \top } \bigl ( Q ^ { 0 } ( t \wedge T _ { i + 1 } ) - Q ^ { 0 } ( t \wedge T _ { i } ) \bigr ) \ell ( T _ { i } ) } } \\ { { \displaystyle \qquad + \sum _ { | I | \leq n } \ell _ { I } ( T _ { i } ) \langle \tilde { e } _ { I } ^ { B } , \widehat { \mathbb { Z } } _ { t \wedge T _ { i + 1 } } - \widehat { \mathbb { Z } } _ { t \wedge T _ { i } } \rangle \bigg ] } } \end{array}
$$

for each $t \geq 0$ , where $T _ { 0 } : = 0 , \ell ^ { < m + 1 } : = \{ \ell ( 0 ) , \ldots , \ell ( T _ { m } ) \} , m = \operatorname* { m a x } \{ j : T _ { j } < t \}$ , and

$$
\begin{array} { r } { Q _ { \mathcal { L } ( I ) \mathcal { L } ( J ) } ^ { 0 } ( t ) = \langle ( e _ { I } \sqcup e _ { J } ) \otimes e _ { 0 } , \widehat { \mathbb { X } } _ { t } \rangle , } \end{array}
$$

for a labeling function $\mathcal { L } : \{ I : | I | \leq n \} \to \{ 1 , \dots , ( d + 1 ) _ { 2 n + 1 } \}$

Proof. We know that

$$
\log ( S _ { t } ( \ell ) ) = - \frac { 1 } { 2 } \int _ { 0 } ^ { t } V _ { s } ( \ell ) \mathrm { d } s + \int _ { 0 } ^ { t } \sigma _ { s } ^ { S } ( \ell ) \mathrm { d } B _ { s }
$$

<!-- page: 34 -->

and we will calculate each integral separately. We start with the first one.

$$
\begin{array} { r l } { \displaystyle \int _ { 0 } ^ { t } V _ { \alpha } ( \hat { \varepsilon } ) \mathrm { d } s = \int _ { 0 } ^ { t } \displaystyle \sum _ { i = 0 } ^ { N } \displaystyle \sum _ { \lbrace i , j \geq 1 } \sum _ { \ell = 1 } ^ { N } \xi _ { \ell } ( T _ { i } ) \ell _ { \ell } ( T _ { i } ) { \mathrm { l } _ { \ell } } _ { \ell } \chi _ { \ell + 1 } ( \hat { \varepsilon } _ { f } ) { \mathrm { l } _ { \ell } } _ { \ell } \chi _ { \ell + 1 } ( e _ { f } , \hat { \mathbb { Z } } _ { \varepsilon } ) \mathrm { d } s } \\ { \displaystyle } & { = \displaystyle \sum _ { i = 0 } ^ { N } \displaystyle \sum _ { \lbrace i , j \geq 1 } \xi _ { \ell } ( T _ { i } ) \ell _ { f } ( T _ { i } ) \int _ { \ell \in \Omega _ { f } } ^ { t \wedge T _ { i - 1 } } \{ { \ell _ { f } \mathrm { d } \mathrm { i n } \ell _ { f } , \hat { \mathbb { Z } } _ { \varepsilon } } \} \mathrm { d } s } \\ { \displaystyle } & { = \displaystyle \sum _ { i = 0 } ^ { N } \displaystyle \sum _ { \lbrace i , j \geq 1 , \ell \rbrace \in T _ { i } }  f _ { i } ( T _ { i } ) \ell _ { f } ( T _ { i } ) ( \int _ { 0 } ^ { t \wedge T _ { i - 1 } } \{ { \ell _ { f } \mathrm { l } _ { i } \mathrm { L } \ell _ { f } , \hat { \mathbb { Z } } _ { \varepsilon } } \} \mathrm { d } s - \int _ { 0 } ^ { t \wedge T _ { i } } \{ { \ell _ { f } \mathrm { l } _ { i } \mathrm { L } \ell _ { f } , \hat { \mathbb { Z } } _ { \varepsilon } } \} \mathrm { d } s ) } \\ { \displaystyle } &  = \displaystyle \sum _ { i = 0 } ^ { N } \sum _ { \lbrace i , j \geq 1 , \ell \rbrace \in T _ { i } } \xi _ { \ell } ( T _ { i } ) \ell _ { f } ( T _ { i } ) ( \{  \ell _ { f } \end{array}
$$

Using similar arguments and Lemma 3.10 in Cuchiero et al. (2023a), the second integral yields

$$
\begin{array} { r l } { \displaystyle \int _ { 0 } ^ { t } \sigma _ { s } ^ { S } ( \boldsymbol { \ell } ) \mathrm { d } B _ { s } = \int _ { 0 } ^ { t } \sum _ { i = 0 } ^ { N } \sum _ { | I | \le n } \ell _ { i } ( T _ { i } ) ^ { 1 } | T _ { i } , T _ { i + 1 } \rangle \langle e _ { I } , \widehat { \mathbb { X } } _ { s } \rangle \mathrm { d } B _ { s } } & { } \\ { \displaystyle } & { - \sum _ { s = 0 } ^ { N } \sum _ { | I | \le n } \xi _ { I } ( T _ { i } ) \int _ { t , N _ { i } ^ { 1 } } ^ { t \wedge T _ { i + 1 } } \langle e _ { I } , \widehat { \mathbb { X } } _ { s } \rangle \mathrm { d } B _ { s } } \\ { \displaystyle } & { = \sum _ { i = 0 } ^ { N } \sum _ { | I | \le n } \ell _ { I } ( T _ { i } ) \left( \int _ { 0 } ^ { t \wedge T _ { i + 1 } } \langle e _ { I } , \widehat { \mathbb { X } } _ { s } \rangle \mathrm { d } B _ { s } - \int _ { 0 } ^ { t \wedge T _ { i } } \langle e _ { I } , \widehat { \mathbb { X } } _ { s } \rangle \mathrm { d } B _ { s } \right) } \\ { \displaystyle } & { - \sum _ { s = 0 } ^ { N } \sum _ { | I | \le n } \xi _ { I } ( T _ { i } ) \langle \widetilde { e } _ { I } ^ { B } , \widehat { \mathbb { Z } } _ { t \wedge T _ { i + 1 } } - \widehat { \mathbb { Z } } _ { t \wedge T _ { i } } \rangle , } \end{array}
$$

and the claim follows.

## 7 Joint calibration of SPX and VIX options

We here consider again the model introduced in (3.1)-(3.2). Note that we just work with call options, but the setup can easily be extended also to other liquid options on the market. Again we denote by $\mathcal { T } ^ { \mathrm { V I X } }$ and $\mathcal { T } ^ { \mathrm { S P X } }$ the maturities set for options written on VIX and SPX, respectively. Similarly we use the notation ${ \cal K } ^ { \mathrm { V I X } }$ and ${ \mathcal { K } } ^ { \mathrm { S P \bar { X } } }$ for the corresponding strikes. The functional to be minimized in order to achieve a joint calibration of the SPX/VIX options reads as follows:

$$
\begin{array} { r } { L _ { \mathrm { j o i n t } } ( \ell , \lambda ) : = \lambda L _ { \mathrm { S P X } } ( \ell ) + ( 1 - \lambda ) L _ { \mathrm { V I X } } ( \ell ) , } \end{array}\tag{7.1}
$$

where $\lambda \in ( 0 , 1 )$ and

<!-- page: 35 -->

$L _ { \mathrm { V I X } } ( \ell )$ is as in (5.13), i.e.

$$
\sum _ { T \in T ^ { \mathrm { V I X } } , K \in K ^ { \mathrm { V I X } } } \mathcal { L } \left( \pi _ { \mathrm { V I X } } ^ { \mathrm { m o d e l } } ( \ell , T , K ) , \pi _ { \mathrm { V I X } } ^ { b , a } ( T , K ) , \sigma _ { \mathrm { V I X } } ^ { b , a } ( T , K ) , F _ { \mathrm { V I X } } ^ { \mathrm { m o d e l } } ( \ell , T ) , F _ { \mathrm { V I X } } ^ { m k t } ( T ) \right) ,
$$

with $\pi _ { \mathrm { V I X } } ^ { m o d e l }$ and $F _ { \mathrm { V I X } } ^ { m o d e l }$ as in (5.12) for $\mathrm { V I X } _ { T } ( \boldsymbol { \ell } , \omega _ { i } )$ defined as in (5.5);

$L _ { \mathrm { S P X } } ( \ell )$ is the SPX loss function given by

$$
L _ { \mathrm { S P X } } ( \ell ) : = \sum _ { T \in { \cal T } ^ { \mathrm { S P X } } , { \cal K } \in { \cal K } ^ { \mathrm { S P X } } } \mathcal { L } ( \pi _ { \mathrm { S P X } } ^ { \mathrm { m o d e l } } ( \ell , T , K ) , \pi _ { \mathrm { S P X } } ^ { b , a } ( T , K ) , \sigma _ { \mathrm { S P X } } ^ { b , a } ( T , K ) ) ,
$$

for a real-valued function $\mathcal { L } .$ Observe that with a slight abuse of notation we denote this function as the one for L<sub>VIX</sub>, but for SPX options we do not have to calibrate to futures, hence the last term of (5.15) vanishes.

By Proposition 6.4 the SPX call option payof with maturity $T > 0$ and a strike price $K > 0$ reads in our model as follows

$$
e ^ { - r T } ( \tilde { S } _ { T } ( \ell ) - K ) ^ { + } = e ^ { - r T } \biggl ( \exp \biggl \{ ( r - q ) T - \frac { 1 } { 2 } \ell ^ { \top } Q ^ { 0 } ( t ) \ell + \sum _ { | I | \leq n } \ell _ { I } \langle \tilde { e } _ { I } ^ { B } , \widehat { \mathbb { Z } } _ { T } \rangle \biggr \} - K \biggr ) ^ { + } ,
$$

where $\tilde { S }$ denotes the undiscounted, unadjusted process as discussed in Remark 3.3 and $r , q > 0$ the interest rate and the dividends, respectively. Recall also that the call option payof written on the VIX is given by

$$
e ^ { - r T } ( \mathrm { V I X } _ { T } ( \ell ) - K ) ^ { + } = e ^ { - r T } \bigg ( \sqrt { \frac { 1 } { \Delta } \ell ^ { \top } Q ( T , \Delta ) \ell } - K \bigg ) ^ { + } = e ^ { - r T } \left( \frac { 1 } { \sqrt { \Delta } } \| U _ { T } ^ { \top } \ell \| - K \right) ^ { + } ,
$$

where $U _ { T }$ denotes the upper-triangular matrix of the Cholesky decomposition of the symmetric positive semidefinite matrix $Q ( T , \Delta )$

Remark 7.1. We report in the table below the (average over $1 0 ^ { 3 }$ trials) timings of evaluating $\mathrm { V I X } _ { T } ( \ell )$ and $S _ { T } ( \ell )$ for $\ell \in \mathbb { R } ^ { 8 5 }$ , a fixed $T > 0$ and $N _ { M C } = 8 \cdot 1 0 ^ { 5 }$ samples on both CPU (on the left) and GPU (on the right) with $\mathrm { P y }$ Torch, respectively:

[Table source crop](assets/tables/2023-cuchiero-et-al-signature-spx-vix-p0035-block-0013-f3dbdf70c6cc95fd.jpg)


This evaluations are the relevant operations in the Monte Carlo pricing and in turn in the calibration procedure. Note again that both the sampling of the signature components and the matrix exponential, are achieved ofline, as they do not depend on $\ell .$

## 7.1 Numerical results

Before presenting our numerical results, let us discuss two diferent ways of approaching the joint calibration problem that can be found in the recent literature.

(i) The first approach consists in choosing for instance the first maturity of SPX and VIX to coincide (or difer up to two days), i.e., $T _ { 1 } ^ { \mathrm { S P X } } = T _ { 1 } ^ { \mathrm { V I X } }$ and then for $j \geq 2$ $T _ { j } ^ { \mathrm { S P X } } = T _ { j - 1 } ^ { \mathrm { V I X } } + \dot { \Delta }$ , see for instance Guyon (2023); Guo et al. (2022b); Guyon and Lekeufack (2023).

<!-- page: 36 -->

(ii) The second approach is to consider $\mathcal { T } ^ { \mathrm { S P X } } = \mathcal { T } ^ { \mathrm { V I X } }$ , i.e., to choose the same (or close together) maturities both for SPX and VIX options. This perspective has been adopted for instance by Gatheral et al. (2018); Rosenbaum and Zhang (2021); Grzelak (2022); Bondi et al. (2024b).

![](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0036-block-0002-b3a63aa75536f5af.jpg)

![Figure 3: The blue lines denote the time interval where the dynamics of the variance process influence the SPX option up to the maturity time. For instance the shortest blue line denotes the time interval where the dynamics of the variance process enter up to maturity $T _ { 1 }$ . Similarly the red lines denote the corresponding ones for the VIX, as for instance the variance process enters here in the time integral on $[ T _ { 1 } , T _ { 1 } + \Delta ]$ , see (5.3). On the upper graph a representation of the joint calibration approach (i) is given where we notice that the maturities of the VIX are chosen so that there is a maximal overlap with the ones of the SPX. On the lower graph a representation of approach (ii) is given where the maturities $\mathcal { T } = \{ T _ { 1 } , T _ { 2 } , T _ { 3 } \}$ are considered. We observe that there is less overlap between the maturities of the SPX and VIX than in approach (i).](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0036-block-0003-65f6b0051842fa61.jpg)

Both approaches deal with the joint modeling of SPX and VIX options and in order to be consistent with both viewpoints taken in the literature, we show how our signature-based model solves the joint calibration within both settings. For this reason we split the rest of the section in two subsection and discuss them separately.

## 7.1.1 First approach

Here we consider call options for both indices on the trading day $0 2 / 0 6 / 2 0 2 1$ , as in Guyon and Lekeufack (2023). Maturities are reported in the following tables with the corresponding range of strikes (in percentage) with respect to the spot and the market’s futures prices.

[Table source crop](assets/tables/2023-cuchiero-et-al-signature-spx-vix-p0036-block-0007-a0e48b2949d6ad7e.jpg)


[Table source crop](assets/tables/2023-cuchiero-et-al-signature-spx-vix-p0036-block-0008-5aedfedda96e1037.jpg)


<!-- page: 37 -->

We stress that the shortest maturity considered is of 14 days for both SPX and VIX, then the second and third maturity of the SPX are 44 days and 58 days, respectively, and the second one for the VIX is 28 days. Moreover, we consider a high moneyness level (up to 220%) for VIX options, usually rather dificult to fit. Regarding our modeling choice we fix $d = 3 , n = 3$ and choose the primary process $X$ to be a three dimensional Ornstein-Uhlenbeck process (see Example 4.5) with parameters

$$
\begin{array} { r l } & { \kappa = ( 0 . 1 , 2 5 , 1 0 ) ^ { \top } , \qquad \theta = ( 0 . 1 , 4 , 0 . 0 8 ) ^ { \top } , \qquad \sigma = ( 0 . 7 , 1 0 , 5 ) ^ { \top } , } \\ & { } \\ & { \rho = \left( \begin{array} { c c c } { 1 } & { 0 . 2 1 3 } & { - 0 . 5 7 6 } & { 0 . 3 2 9 } \\ { . } & { 1 } & { - 0 . 0 4 4 } & { - 0 . 5 4 9 } \\ { . } & { . } & { 1 } & { - 0 . 5 3 9 } \\ { . } & { . } & { . } & { 1 } \end{array} \right) , \qquad X _ { 0 } = ( 1 , 0 . 0 8 , 2 ) ^ { \top } . } \end{array}
$$

Note that with this configuration we need to calibrate 85 parameters, i.e., $\ell \in \mathbb { R } ^ { 8 5 }$ . Concerning the calibration task, we solve (7.1) with $\lambda = 0 . 3 5$ with $N _ { M C } = 8 0 0 0 0$ Monte Carlo samples for the previous maturities and strikes. Furthermore we specify the loss function $\mathcal { L }$ as in (5.15) for $\beta = 1$ both for SPX and VIX.

![](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0037-block-0004-8a8e8adce117970c.jpg)

![](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0037-block-0005-e1e51d3da23ac27f.jpg)

![](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0037-block-0006-fed9ba2e689b832e.jpg)

![](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0037-block-0007-ff46104e366ae76e.jpg)

![Figure 4: In blue the calibrated implied volatility smiles from top-left at maturities $T _ { 1 } ^ { \mathrm { S P X } } , T _ { 1 } ^ { \mathrm { V I X } } , T _ { 2 } ^ { \mathrm { S P X } } , T _ { 3 } ^ { \mathrm { S P X } } , T _ { 2 } ^ { \mathrm { V I X } }$ . In red the corresponding bid-ask spreads. In the graphs of the VIX smiles the red dashed line indicates the market future price at maturity and the blue dashed line the calibrated one.](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0037-block-0008-745ba2fccf992fd1.jpg)

We report also the relative error between the market futures prices and the calibrated ones as defined in (5.16):

<!-- page: 38 -->

[Table source crop](assets/tables/2023-cuchiero-et-al-signature-spx-vix-p0038-block-0001-69fbd7ad9b734189.jpg)


Simulation of time-series of SPX and VIX Let $\ell ^ { \star } \in \mathbb { R } ^ { 8 5 }$ be the calibrated parameters already used for Figure 4. We then fix $T = 6 0$ days the longest considered maturity for the SPX and sample a trajectory for $( V _ { t } ( \ell ^ { \star } ) ) _ { t \in [ 0 , T ] } , \ ( \mathrm { V I X } _ { t } ( \ell ^ { \star } ) ) _ { t \in [ 0 , T ] } , \ ( S _ { t } ( \ell ^ { \star } ) ) _ { t \in [ 0 , T ] }$ . Precisely, we sample 12 grid points per day, i.e. we consider a 2 hours sampling per calendar day, for a total of $N = 7 2 0$ grid points. The results of this simulation are reported in Figure 5.

![](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0038-block-0003-b129f9634bbe02ba.jpg)

![Figure 5: On the top: one realization of the calibrated model $S ( \ell ^ { \star } )$ for the SPX (in blue) and the corresponding calibrated VIX (in red). On the bottom: the corresponding realization of the calibrated variance process $V ( \ell ^ { \star } )$](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0038-block-0004-646253a57ea4fb05.jpg)

Observe that even though $\ell ^ { * }$ was only calibrated to option prices, the trajectories produced by the model are economically reasonable and also in line with several stylized facts, such as negative correlation between SPX and VIX or volatility clustering. To obtain the dynamics under the physical measure, these trajectories could still be adjusted by an appropriate market price of risk, but the quantities which are invariant under equivalent measure changes like the volatility of volatility or the correlation stay the same.

<!-- page: 39 -->

The case of time-varying parameters Next, we consider again the case of time-varying parameters as introduced in Section 5.4 and Section 6.2 for VIX and SPX, respectively. Although the joint calibration is mainly considered for short-dated options in the literature as VIX options are then more liquid, it is even more challenging to provide an accurate fit for both, short and long maturities. Allowing the parameters ℓ of our model to depend on time, in particular on the maturities, we are able to calibrate additionally to longer maturities than the ones considered in Figure 4. We consider for the choice of the primary process the same configuration as we used for Figure 4. The procedure of our time-varying calibration routine is as follows:

1. Calibrate jointly $T _ { 1 } ^ { \mathrm { S P X } } , T _ { 1 } ^ { \mathrm { V I X } }$ and $T _ { 2 } ^ { \mathrm { S P X } }$

2. Use the parameters from the calibration of $T _ { j } ^ { \mathrm { S P X } }$ and $T _ { j - 1 } ^ { \mathrm { V I X } }$ to fit jointly the maturities $T _ { j + 1 } ^ { \mathrm { S P X } }$ and $T _ { j } ^ { \mathrm { V I X } }$ for $j = 2 , \dots , J$

We consider $J = 4 ,$ where the last maturity for the SPX is 170 days, and the last maturity for the VIX is 77 days. For the first two maturities of the SPX and the first of the VIX we consider the same moneyness ranges as in Figure 4, hence we specify here only the ranges for the longer maturities:

[Table source crop](assets/tables/2023-cuchiero-et-al-signature-spx-vix-p0039-block-0005-b3c7f07c5fb78ba5.jpg)


We observe that for this choice of maturities Assumption 5.11 is satisfied. Hence the second expression for the time-varying VIX is used from Proposition (5.12). On the other hand in order to compute the price of the SPX options in the time-varying case we use the representation of the log-price provided in Proposition 6.9. In (7.1), we employ $\lambda = 0 . 2 5$ for each calibration within the rolling procedure and we consider always as loss function $\mathcal { L } ^ { \beta }$ as introduced in (5.15) for $\beta = 0$ . It is worth mentioning that the initial parameter search discussed in Remark 5.8, has been employed for calibrating jointly $T _ { 1 } ^ { \mathrm { S P X } } , T _ { 1 } ^ { \mathrm { V I X } }$ and $T _ { 2 } ^ { \mathrm { S P X } }$ , whereas for the next slices we have considered the previously calibrated parameters as starting point of the optimization.

<!-- page: 40 -->

![](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0040-block-0001-fb753432a4aebdca.jpg)

![Figure 6: On the left-hand side: SPX smiles, in blue the calibrated implied volatilities and in red the bid-ask spreads. On the right-hand side: VIX smiles, in blue the calibrated implied volatilities and in red the bid-ask spreads.](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0040-block-0002-e3b1e179e4ab7f9c.jpg)

[Table source crop](assets/tables/2023-cuchiero-et-al-signature-spx-vix-p0040-block-0003-c430cad7a5fe2ddf.jpg)
Finally we report the absolute relative error on the VIX futures’ prices:

## 7.1.2 Second approach

Let us now consider the second approach described at the beginning of Section 7.1. Specifically, we consider a unique set of maturities for both SPX and VIX on the trading day of $0 2 / 0 6 / 2 0 2 1$ . For this study, we do not consider time-varying parameters. In the following table we report the moneyness ranges for SPX options in the second row and on the last row the ones for VIX options:

[Table source crop](assets/tables/2023-cuchiero-et-al-signature-spx-vix-p0040-block-0006-001312cf256586ef.jpg)


We consider $\lambda = 0 . 5$ and as loss function L we employ (5.15) with $\beta = 1$ for VIX options and the same (without futures) for SPX options.

<!-- page: 41 -->

![](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0041-block-0001-0f945c6e5775b112.jpg)

![Figure 7: On the left-hand side: SPX smiles, in blue the calibrated implied volatilities and in red the bid-ask spreads. On the right-hand side: VIX smiles, in blue the calibrated implied volatilities and in red the bid-ask spreads.](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0041-block-0002-cfbc2cd16d9a7b2e.jpg)

[Table source crop](assets/tables/2023-cuchiero-et-al-signature-spx-vix-p0041-block-0003-b7cf052951cf08bb.jpg)
We additionally report the relative error of the calibrated VIX futures:

## A Numerical results for the Brownian motion case

This appendix is dedicated to the calibration to VIX options only, similarly as in Section 5.3.1, however with the primary process $( X _ { t } ) _ { t \geq 0 }$ being simply correlated Brownian motions (similarly as in Cuchiero et al. (2023a)) instead of OU-processes.

To be precise, we here model given by (3.1)-(3.2), where $( X _ { t } ) _ { t \geq 0 }$ is 2-dimensional Brownian motion. The correlation matrix of $Z = ( X , B )$ is specified, as in Section 5.3.1, namely by

$$
\rho = \left( \begin{array} { c c c } { { 1 } } & { { - 0 . 5 7 7 } } & { { 0 . 3 } } \\ { { . } } & { { 1 } } & { { - 0 . 6 } } \\ { { . } } & { { . } } & { { 1 } } \end{array} \right) .
$$

For the other parameters we consider a truncation’s level $n = 3$ , we sample $N _ { M C } = 8 0 0 0 0$ trajectories for Monte Carlo pricing, and we minimize the loss function (5.15) with $\beta = 1$ to fit the same data-set as in Section 5.3.1.

<!-- page: 42 -->

![Figure 8: The red crosses denote the bid-ask spreads (of the implied volatilities) for each maturity, while the azure dots denote the calibrated implied volatilities of the model.](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0042-block-0001-9ac91649aa537255.jpg)

We observe that with this specification the model is neither able to calibrate to all future market prices (see Figure 9 below) nor to fit the market implied volatilites accurately. One can indeed see that the model implied volatilities often do not lie within the bid-ask spreads, in particular for high strikes and short maturities.

[Table source crop](assets/tables/2023-cuchiero-et-al-signature-spx-vix-p0042-block-0003-9deabc0fb0ebdded.jpg)


![Figure 9: The blue circles denote the calibrated futures prices and the red crosses the market futures prices, in between a linear interpolation is applied.](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0042-block-0004-059de14caa86ff85.jpg)

<!-- page: 43 -->

## B On the stability of the calibrated parameters

We report here an analysis of the stability of the calibrated parameters, which is for example essential for hedging since unstable parameters can lead to oscillating hedge ratios and high transaction cost.

For this purpose we have considered call options with the same time to maturity every trading week in the month of June 2021, i.e. we take the following five dates: June 2, 2021; June 9, 2021; June 16, 2021; June 23, 2021 and June 30, 2021. The times to maturity are on one hand $T _ { 1 } ^ { \mathrm { S P X } } = 1 4$ days and $T _ { 2 } ^ { \mathrm { S P X } } = 4 4 ~ \mathrm { d a y s }$ for SPX options and on the other hand $T _ { 1 } ^ { \mathrm { V I X } } { = } 1 4$ days for VIX (weekly) options. We employ the same primary process as of Section 7.1.1 for all 5 trading days. The goodness of fit of the respective implied volatilities is reported in Figures 13–16, omitting June 2, 2021 as it is already presented in Section 7.1. The obtained parameters are reported in Figures 10–12. The labels of the x-axis refer to the signature’s index I and on the y-axis we have the corresponding coeficients $\ell _ { I }$

Although no regularization on the model parameters has been enforced during the calibration, we observe from Figures 10–12 that most of the parameters which are close to zero in the first trading day, are kept in a neighbourhood of zero in the subsequent trading days. Likewise the more relevant parameters are mostly stable over the trading days or just slightly and continuously adjusted to fit the corresponding smiles, leading to an inherently stable calibration procedure. This experiment also indicates that – even though we consider on purpose an overparametrized model – it does not sufer from overfitting (which would be the case if the parameters were highly oscillatory).

![Figure 10: First subset of calibrated parameters $\ell _ { I } .$](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0043-block-0005-2fc36832bfa538ea.jpg)

<!-- page: 44 -->

![Figure 11: Second subset of calibrated parameters $\ell _ { I }$](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0044-block-0001-38ac81f79cff1b91.jpg)

![Figure 12: Third subset of calibrated parameters $\ell _ { I }$](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0044-block-0002-72746b8345b8a415.jpg)

<!-- page: 45 -->

![](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0045-block-0001-eb0246b0ad1526d8.jpg)

![](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0045-block-0002-3bbe3a732ae49a7d.jpg)

![Figure 13: Implied volatilities as of June 9, 2021. In blue the calibrated implied volatility smiles from top-left at maturities $T _ { 1 } ^ { \mathrm { S P X } } , T _ { 1 } ^ { \mathrm { V I X } } , T _ { 2 } ^ { \mathrm { S P X } }$ . In red the corresponding bid-ask spreads. In the graphs of the VIX smile the red dashed line indicates the market future price at maturity and the blue dashed line the calibrated one.](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0045-block-0003-c670e77035fb3929.jpg)

![Figure 14: Implied volatilities as of June 16, 2021](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0045-block-0004-54b17ad502b9cc1a.jpg)

<!-- page: 46 -->

![](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0046-block-0001-e3bf187de138c5a8.jpg)

![](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0046-block-0002-d35d7293ca1e1c40.jpg)

![Figure 15: Implied volatilities as of June 23, 2021](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0046-block-0003-ece7b0e6834a08ac.jpg)

![](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0046-block-0004-1df1c0962708139b.jpg)

![](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0046-block-0005-6bed0f473fa0e14c.jpg)

![Figure 16: Implied volatilities as of June 30, 2021](assets/figures/2023-cuchiero-et-al-signature-spx-vix-p0046-block-0006-88d0982b52d286ac.jpg)

## References

E. Abi Jaber, C. Illand, and S. Li. Joint SPX-VIX calibration with Gaussian polynomial volatility models: deep pricing with quantization hints. Preprint arXiv:2212.08297, 2022a. E. Abi Jaber, C. Illand, and S. Li. The quintic Ornstein-Uhlenbeck volatility model that jointly calibrates SPX & VIX smiles. Preprint arXiv:2212.10917, 2022b.

<!-- page: 47 -->

E. Akyildirim, M. Gambara, J. Teichmann, and S. Zhou. Randomized signature methods in optimal portfolio selection. Preprint arXiv:2312.16448, 2023. P. Bader, S. Blanes, and F. Casas. Computing the matrix exponential with an optimized taylor polynomial approximation. Mathematics, 7(12):1174, 2019. J. Baldeaux and A. Badran. Consistent modelling of VIX and equity derivatives using a 3/2 plus jumps model. Applied Mathematical Finance, 21(4):299–312, 2014. C. Bayer, P. Friz, and J. Gatheral. Pricing under rough volatility. Quantitative Finance, 16(6):887–904, 2016. C. Bayer, B. Horvath, A. Muguruza, B. Stemper, and M. Tomas. On deep calibration of (rough) stochastic volatility models. Preprint arXiv:1908.08806, 2019. C. Bayer, P. P. Hager, S. Riedel, and J. Schoenmakers. Optimal stopping with signatures. The Annals of Applied Probability, 33(1):238–273, 2023. H. Boedihardjo, X. Geng, T. Lyons, and D. Yang. The signature of a rough path: uniqueness. Advances in Mathematics, 293:720–737, 2016. H. Boedihardjo, J. Diehl, M. Mezzarobba, and H. Ni. The expected signature of Brownian motion stopped on the boundary of a circle has finite radius of convergence. Bulletin of the London Mathematical Society, 53(1):285–299, 2021. A. Bondi, G. Livieri, and S. Pulido. Afine volterra processes with jumps. Stochastic Processes and their Applications, 168:104264, 2024a. A. Bondi, S. Pulido, and S. Scotti. The rough Hawkes Heston stochastic volatility model. Mathematical Finance, 1–45, 2024b. F. Bourgey and S. De Marco. Multilevel Monte Carlo simulation for VIX options in the rough Bergomi model. Journal of Computational Finance, 26(2):53–82, 2022. H. Buehler, B. Horvath, T. Lyons, I. Perez Arribas, and B. Wood. A data-driven market simulator for small data environments. Preprint arXiv:2006.14498, 2020. T. Cass and E. Ferrucci. On the Wiener chaos expansion of the signature of a Gaussian process. Probability Theory and Related Fields, 189:909-947, 2024. K. T. Chen. Integration of paths, geometric invariants and a generalized Baker-Hausdorf formula. Annals of Mathematics, 65(1):163–178, 1957. K. T. Chen. Iterated path integrals. Bulletin of the American Mathematical Society, 83: 831-879, 1977. S. N. Cohen, S. Lui, W. Malpass, G. Mantoan, L. Nesheim, A. de Paula, A. Reeves, C. Scott, E. Small, and L. Yang. Nowcasting with signature methods. Preprint arXiv:2305.10256, 2023. E. M. Compagnoni, A. Scampicchio, L. Biggio, A. Orvieto, T. Hofmann, and J. Teichmann. On the efectiveness of Randomized Signatures as Reservoir for Learning Rough Dynamics. In 2023 International Joint Conference on Neural Networks (IJCNN), 1–8, 2023. doi: 10.1109/IJCNN54540.2023.10191624.

<!-- page: 48 -->

R. Cont and P. Das. Quadratic variation and quadratic roughness. Bernoulli, 29(1):496–522, 2023. R. Cont and T. Kokholm. A consistent pricing model for index options and volatility derivatives. Mathematical Finance, 23(2):248–274, 2013. L. Coutin and Z. Qian. Stochastic analysis, rough path analysis and fractional brownian motions. Probability theory and related fields, 122(1):108–140, 2002. C. Cuchiero and J. M¨oller. Signature Methods in Stochastic Portfolio Theory. Preprint arXiv:2310.02322, 2023. C. Cuchiero and S. Svaluto-Ferro. Infinite-dimensional polynomial processes. Finance and Stochastics, 25(2):383–426, 2021. C. Cuchiero, M. Keller-Ressel, and J. Teichmann. Polynomial processes and their applications to mathematical finance. Finance and Stochastics, 16:711–740, 2012. C. Cuchiero, L. Gonon, L. Grigoryeva, J.-P. Ortega, and J. Teichmann. Discrete-time signatures and randomness in reservoir computing. IEEE Transactions on Neural Networks and Learning Systems, 33(11):6321–6330, 2022. C. Cuchiero, G. Gazzani, and S. Svaluto-Ferro. Signature-based models: Theory and calibration. SIAM Journal on Financial Mathematics, 14(3):910–957, 2023a. C. Cuchiero, S. Svaluto-Ferro, and J. Teichmann. Signature SDEs from an afine and polynomial perspective. Preprint arXiv:2302.01362, 2023b. C. Cuchiero, L. Di Persio, F. Guida, and S. Svaluto-Ferro. Measure-valued afine and polynomial difusions. Stochastic Processes and their Applications, page 104392, 2024a. C. Cuchiero, F. Primavera, and S. Svaluto-Ferro. Universal approximation theorems for continuous functions of c\`adl\`ag paths and L´evy-type signature models. Forthcoming in Finance and Stochastics, 2024b. F. Delbaen and W. Schachermayer. A general version of the fundamental theorem of asset pricing. Mathematische annalen, 300(1):463–520, 1994. G. Di Nunno, K. Kubilius, Y. Mishura, and A. Yurchenko-Tytarenko. From constant to rough: A survey of continuous volatility modeling. Mathematics, 11(19):4201, 2023. T. Fawcett. Problems in stochastic analysis. Connections between rough paths and noncommutative harmonic analysis. PhD Thesis, Univ. Oxford, 2003. D. Filipovi´c and M. Larsson. Polynomial difusions and applications in finance. Finance and Stochastics, 20(4):931–972, 2016. J.-P. Fouque and Y. Saporito. Heston stochastic vol-of-vol model for joint calibration of VIX and S&P 500 options. Quantitative Finance, 18(6):1003–1016, 2018. J. Gatheral. Consistent modeling of SPX and VIX options. Bachelier Congress, 2008. J. Gatheral. The volatility surface: a practitioner’s guide. John Wiley & Sons, 2011.

<!-- page: 49 -->

J. Gatheral, T. Jaisson, and M. Rosenbaum. Volatility is rough. Quantitative Finance, 18 (6):933–949, 2018. J. Gatheral, P. Jusselin, and M. Rosenbaum. The quadratic rough Heston model and the joint S&P 500/VIX smile calibration problem. Risk, May 2020. G. Gazzani and J. Guyon. Pricing and calibration in the 4-factor path-dependent volatility model. Preprint arXiv:2406.02319, 2024. P. Gierjatowicz, M. Sabate-Vidales, D. Siska, L. Szpruch, and Z. Zuric. Robust pricing and hedging via neural SDEs. Journal of Computational Finance, 26(3):1–32, 2023. P. Glasserman. Monte Carlo methods in financial engineering, volume 53. Springer, 2004. L. A. Grzelak. On Randomization of Afine Difusion Processes with Application to Pricing of Options on VIX and S&P 500. Preprint arXiv:2208.12518, 2022. H. Guerreiro and J. Guerra. VIX pricing in the rBergomi model under a regime switching change of measure. Quantitative Finance, 23(5):721–738, 2023. I. Guo, G. Loeper, J. Ob l´oj, and S. Wang. Joint modeling and calibration of SPX and VIX by optimal transport. SIAM Journal on Financial Mathematics, 13(1):1–31, 2022a. I. Guo, G. Loeper, and S. Wang. Calibration of local-stochastic volatility models by optimal transport. Mathematical Finance, 32(1):46–77, 2022b. J. Guyon. Inversion of convex ordering in the VIX market. Quantitative Finance, 20(10): 1597–1623, 2020a. J. Guyon. The joint S&P 500/VIX smile calibration puzzle solved. Risk, April, 2020b. J. Guyon. Dispersion-constrained martingale Schr¨odinger problems and the exact joint S&P 500/VIX smile calibration puzzle. Finance and Stochastics, 28:27-79, 2023. F. Bourgey and J. Guyon. Fast exact joint S&P 500/VIX smile calibration in discrete and continuous time. Risk, February, 2024. J. Guyon and J. Lekeufack. Volatility is (mostly) path-dependent. Quantitative Finance, pages 1–38, 2023. J. Guyon and S. Mustapha. Neural joint S&P 500/VIX smile calibration. Risk, December, 2023. P. S. Hagan, D. Kumar, A. S. Lesniewski, and D. Woodward. Managing smile risk. The Best of Wilmott, 1:249–296, 2002. J. Kalsi, T. Lyons, and P.-A. I. Optimal execution with rough path signatures. SIAM Journal on Financial Mathematics, 11(2):470–493, 2020. C. Kardaras, D. Kreher, and A. Nikeghbali. Strict local martingales and bubbles. The Annals of Applied Probability, 25(4):1827–1867, 2015. P. Kidger and T. Lyons. Signatory: diferentiable computations of the signature and logsignature transforms, on both CPU and GPU. In International Conference on Learning Representations, 2020.

<!-- page: 50 -->

T. Kokholm and M. Stisen. Joint pricing of VIX and SPX options with stochastic volatility and jump models. The Journal of Risk Finance, 16(1):27-48, 2015. E. Lemahieu, K. Boudt, and M. Wyns. Generating drawdown-realistic financial price paths using path signatures. Preprint arXiv:2309.04507, 2023. T. Lyons and H. Ni. Expected signature of Brownian motion up to the first exit time from a bounded domain. The Annals of Probability, 43(5):2729–2762, 2015. T. Lyons and N. Victoir. Cubature on Wiener space. Proceedings of the Royal Society of London. Series A: Mathematical, Physical and Engineering Sciences, 460(2041):169–198, 2004. T. Lyons, M. Caruana, and T. L´evy. Diferential equations driven by rough paths. Springer, 2007. T. Lyons, S. Nejad, and I. Perez Arribas. Non-parametric pricing and hedging of exotic derivatives. Applied Mathematical Finance, 27(6):457–494, 2020. M. Min and R. Hu. Signatured deep fictitious play for mean field games with common noise. In International Conference on Machine Learning, pages 7736–7747. PMLR, 2021. C. Moler and C. Van Loan. Nineteen dubious ways to compute the exponential of a matrix, twenty-five years later. SIAM review, 45(1):3–49, 2003. A. Neuberger. The log contract. Journal of portfolio management, 20:74–74, 1994. S. Liao, H. Ni, M. Sabate-Vidales, L. Szpruch, M. Wiese, and B. Xiao. Sig-Wasserstein GANs for conditional time series generation. Mathematical Finance, Special Issue on Machine Learning in Finance, 34(2):622–670, 2023. B. Ning, P. Chakraborty, and K. Lee. Optimal Entry and Exit with Signature in Statistical Arbitrage. Preprint arXiv:2309.16008, 2023. C. Pacati, G. Pompa, and R. Ren\`o. Smiling twice: the Heston++ model. Journal of Banking & Finance, 96:185–206, 2018. A. Papanicolaou and R. Sircar. A regime-switching Heston model for VIX and S&P 500 implied volatilities. Quantitative Finance, 14(10):1811–1827, 2014. I. Perez Arribas, C. Salvi, and L. Szpruch. Sig-SDEs model for quantitative finance. In Proceedings of the First ACM International Conference on AI in Finance, pages 1–8, 2020. A. Quarteroni, R. Sacco, and F. Saleri. Numerical mathematics, volume 37. Springer Science & Business Media, 2010. R. Ree. Lie elements and an algebra associated with shufles. Annals of Mathematics, 68 (2):210-220, 1958. J. Reizenstein and B. Graham. The iisignature library: eficient calculation of iteratedintegral signatures and log signatures. Preprint arXiv:2006.00218, 2018.

<!-- page: 51 -->

R. Rhoads. Trading VIX derivatives: trading and hedging strategies using VIX futures, options, and exchange-traded notes, volume 503. John Wiley & Sons, 2011. L. Rogers. Things we think we know. In Options — 45 Years since the Publication of the Black–Scholes–Merton Model, chapter 9, pages 173–184. 2023. S. Rømer. Empirical analysis of rough and classical stochastic volatility models to the SPX and VIX markets. Quantitative Finance, 22(10):1805-1838, 2022. M. Rosenbaum and J. Zhang. Deep calibration of the quadratic rough Heston model. Risk, September, 2022. A. Sepp. VIX option pricing in a jump-difusion model. Risk, April, 2008. E. M. Stein and J. C. Stein. Stock price distributions with stochastic volatility: an analytic approach. The review of financial studies, 4(4):727–752, 1991. M. Wiese, P. Murray, and R. Korn. Sig-Splines: universal approximation and convex calibration of time series generative models. Preprint arXiv:2307.09767, 2023.
