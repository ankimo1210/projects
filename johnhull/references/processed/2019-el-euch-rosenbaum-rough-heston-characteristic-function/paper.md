# 2019-el-euch-rosenbaum-rough-heston-characteristic-function

<!-- page: 1 -->

## The characteristic function of rough Heston models

Omar El Euch CMAP, Ecole Polytechnique Paris <sup>´</sup> omar.el-euch@polytechnique.edu

Mathieu Rosenbaum CMAP, Ecole Polytechnique Paris <sup>´</sup> mathieu.rosenbaum@polytechnique.edu

September 8, 2016

## Abstract

It has been recently shown that rough volatility models, where the volatility is driven by a fractional Brownian motion with small Hurst parameter, provide very relevant dynamics in order to reproduce the behavior of both historical and implied volatilities. However, due to the non-Markovian nature of the fractional Brownian motion, they raise new issues when it comes to derivatives pricing. Using an original link between nearly unstable Hawkes processes and fractional volatility models, we compute the characteristic function of the log-price in rough Heston models. In the classical Heston model, the characteristic function is expressed in terms of the solution of a Riccati equation. Here we show that rough Heston models exhibit quite a similar structure, the Riccati equation being replaced by a fractional Riccati equation.

Keywords: Rough volatility models, rough Heston models, Hawkes processes, fractional Brownian motion, fractional Riccati equation, limit theorems.

## 1 Introduction

The celebrated Heston model is a one-dimensional stochastic volatility model where the asset price S follows the following dynamic:

$$
\begin{array} { c } { d S _ { t } = S _ { t } \sqrt { V _ { t } } d W _ { t } } \\ { d V _ { t } = \lambda ( \theta - V _ { t } ) d t + \lambda \nu \sqrt { V _ { t } } d B _ { t } . } \end{array}\tag{1}
$$

Here the parameters $\lambda , \theta , V _ { 0 }$ and ν are positive, and W and B are two Brownian motions with correlation coeficient $\rho ,$ that is $\langle d W _ { t } , d B _ { t } \rangle = \rho d t$

The popularity of this model is probably due to three main reasons:

• It reproduces well several important stylized facts of low frequency price data, namely leverage efect, time-varying volatility and fat tails, see [7, 9, 13, 35].

arXiv:1609.02108v1 [q-fin.MF] 7 Sep 2016

<!-- page: 2 -->

• It generates very reasonable shapes and dynamics for the implied volatility surface. Indeed, the “volatility of volatility” parameter ν enables us to control the smile, the correlation parameter $\rho$ to deal with the skew, and the initial volatility $V _ { 0 }$ to fix the at-the-money volatility level, see [15, 17, 30, 38]. Furthermore, as observed in markets and in contrast to local volatility models, in Heston model, the volatility smile moves in the same direction as the underlying and the forward smile does not flatten with time, see [17, 26, 27, 37].

• There is an explicit formula for the characteristic function of the asset log-price, see [23]. From this formula, eficient numerical methods have been developed, allowing for instantaneous model calibration and pricing of derivatives, see [1, 8, 31, 32].

In the classical Heston model, the volatility follows a Brownian semi-martingale. However, it is shown in [18] that for a very wide range of assets, historical volatility time-series exhibit a behavior which is much rougher than that of a Brownian motion. More precisely, dynamics of log-volatility are very well modeled by a fractional Brownian motion with Hurst parameter of order 0.1. Furthermore, using a fractional Brownian motion with small Hurst index also enables us to reproduce very accurately the features of the volatility surface, see [5, 18]. Finally, convincing microstructural foundations for rough volatility models are provided in [14, 28], see also Section 2.

Hence, in this paper, we are interested in the fractional versions of Heston model. Our main goal is to design an eficient pricing methodology for such models, in the spirit of the one introduced by Heston in the classical case. This is particularly important in fractional volatility models where the use of Monte-Carlo methods can be quite intricate due to the non-Markovian nature of the fractional Brownian motion, see [6].

We now define our so-called rough Heston model. Let us recall that a fractional Brownian motion $W ^ { H }$ with Hurst parameter $H \in ( 0 , 1 )$ can be built through the Mandelbrot-van Ness representation:

$$
W _ { t } ^ { H } = \frac { 1 } { \Gamma ( H + 1 / 2 ) } \int _ { - \infty } ^ { 0 } \big ( ( t - s ) ^ { H - \frac { 1 } { 2 } } - ( - s ) ^ { H - \frac { 1 } { 2 } } \big ) d W _ { s } + \frac { 1 } { \Gamma ( H + 1 / 2 ) } \int _ { 0 } ^ { t } ( t - s ) ^ { H - \frac { 1 } { 2 } } d W _ { s } .\tag{2}
$$

The kernel $( t - s ) ^ { H - { \frac { 1 } { 2 } } }$ in (2) plays a central role in the rough dynamic of the fractional Brownian motion for $H < 1 / 2$ . In particular, one can show that the process

$$
\int _ { 0 } ^ { t } ( t - s ) ^ { H - \frac { 1 } { 2 } } d W _ { s }
$$

has H¨older regularity $H - \varepsilon$ for any $\varepsilon > 0$ . In order to allow for a rough behavior of the volatility in a Heston-type model, we naturally introduce the kernel $( t - s ) ^ { \alpha - 1 }$ in a Hestonlike stochastic volatility process as follows:

$$
d S _ { t } = S _ { t } \sqrt { V _ { t } } d W _ { t }
$$

$$
V _ { t } = V _ { 0 } + \frac { 1 } { \Gamma ( \alpha ) } \int _ { 0 } ^ { t } ( t - s ) ^ { \alpha - 1 } \lambda ( \theta - V _ { s } ) d s + \frac { 1 } { \Gamma ( \alpha ) } \int _ { 0 } ^ { t } ( t - s ) ^ { \alpha - 1 } \lambda \nu \sqrt { V _ { s } } d B _ { s } .\tag{3}
$$

<!-- page: 3 -->

The parameters λ, θ, V<sub>0</sub> and ν in (3) are positive and play the same role as in (1), and here also W and B are two Brownian motions with correlation $\rho .$ The additional parameter α belongs to $( 1 / 2 , 1 )$ and governs the smoothness of the volatility sample paths. More precisely, we show in this paper that the model is well-defined and that the volatility trajectories have almost surely H¨older regularity $\alpha - 1 / 2 - \varepsilon$ , for any $\varepsilon > 0$ . When $\alpha = 1$ , Models (3) and (1) coincide, and we retrieve the classical Heston model. Therefore it is natural to view (3) as a rough version of Heston model and to call it rough Heston model. Nevertheless, note that other definitions of rough Heston models can make sense, see [19] for an alternative definition and some asymptotic results.

Our aim in this work is to derive a Heston-type formula for the characteristic function of the log-price in Model (3). In the classical case $( \alpha = 1$ , Model (1)), this formula is proved in [23]. It is obtained using the fact that Model (1) is Markovian and time-homogeneous, and applying Itˆo’s formula to the function

$$
L ( t , a , V _ { t } , S _ { t } ) = \mathbb { E } [ e ^ { i a \log ( S _ { T } ) } | \mathcal { F } _ { t } ] , \mathcal { F } _ { t } = \sigma ( W _ { s } , B _ { s } ; s \le t ) , a \in \mathbb { R } .
$$

The process L being a martingale, the following Feynman-Kac partial diferential equation for $L$ is easily obtained:

$$
- \partial _ { t } L ( t , a , S , V ) = \bigl ( \lambda ( \theta - V ) \partial _ { v } + \frac { 1 } { 2 } ( \lambda \nu ) ^ { 2 } V \partial _ { v v } ^ { 2 } + \frac { 1 } { 2 } S ^ { 2 } V \partial _ { s s } ^ { 2 } + \rho \nu \lambda S V \partial _ { s v } ^ { 2 } \bigr ) L ( t , a , S , V ) ,
$$

with boundary condition $L ( T , a , S , V ) = e ^ { i a \log ( S ) }$ . From this PDE, it can be checked that the characteristic function of the log-price $X _ { t } = \log ( S _ { t } / S _ { 0 } )$ satisfies

$$
\mathbb { E } [ e ^ { i a X _ { t } } ] = \exp { \big ( g ( a , t ) + V _ { 0 } h ( a , t ) \big ) } ,
$$

where h is solution of the following Riccati equation:

$$
\partial _ { t } h = \frac { 1 } { 2 } ( - a ^ { 2 } - i a ) + \lambda ( i a \rho \nu - 1 ) h ( a , s ) + \frac { ( \lambda \nu ) ^ { 2 } } { 2 } h ^ { 2 } ( a , s ) , h ( a , 0 ) = 0 ,\tag{4}
$$

and

$$
g ( a , t ) = \theta \lambda \int _ { 0 } ^ { t } h ( a , s ) d s .
$$

Solving this Riccati equation leads to the closed-form formula for the characteristic function of the log-price given in [23].

In the case $\alpha < 1$ , the rough Heston model (3) is neither Markovian nor a semi-martingale. Hence the strategy initially used by Heston presented above seems very hard to adapt to our setting. Here we resort to a completely diferent and original approach based on point processes. Indeed, our methodology finds its root in the works [14, 28] which provide microstructural foundations to rough volatility models. In these papers, it is shown that some well-designed microstructure models, reproducing the stylized facts of modern financial markets at high frequency, give rise in the long run to rough volatility models. These microstructure models that we describe in more details in Section 2 are based on so-called nearly unstable Hawkes processes. In this paper, inspired by these results and using again Hawkes processes, we design a suitable sequence of point processes which converges to Model (3). Exploiting the specific structure of our point processes, we derive their characteristic function, which leads us in the limit to that of the log-price in the rough Heston model (3).

<!-- page: 4 -->

Our main result is that, quite surprisingly, the characteristic function of the log-price in rough Heston models exhibits the same structure as the one obtained in the classical Heston model. The diference is that the Riccati equation (4) is replaced by a fractional Riccati equation, where a fractional derivative appears instead of a classical derivative. More precisely, we obtain

$$
\mathbb { E } [ e ^ { i a X _ { t } } ] = \exp { \big ( g _ { 1 } ( a , t ) + V _ { 0 } g _ { 2 } ( a , t ) \big ) } ,
$$

where

$$
g _ { 1 } ( a , t ) = \theta \lambda \int _ { 0 } ^ { t } h ( a , s ) d s , \quad g _ { 2 } ( a , t ) = I ^ { 1 - \alpha } h ( a , t ) ,
$$

and $h$ is a solution of the following fractional Riccati equation:

$$
D ^ { \alpha } h = \frac { 1 } { 2 } ( - a ^ { 2 } - i a ) + \lambda ( i a \rho \nu - 1 ) h ( a , s ) + \frac { ( \lambda \nu ) ^ { 2 } } { 2 } h ^ { 2 } ( a , s ) , I ^ { 1 - \alpha } h ( a , 0 ) = 0 ,
$$

with $D ^ { \alpha }$ and $I ^ { 1 - \alpha }$ the fractional derivative and integral operators defined in (21) and (22). Remark that when $\alpha = 1$ , this result indeed coincides with the classical Heston’s result. However, note that for $\alpha < 1$ , the solutions of such Riccati equations are no longer explicit. Nevertheless, they are easily solved numerically, see Section 5.

The paper is organized as follows. In Section 2, we build a sequence of Hawkes-type processes which converges to the rough Heston model (3). Then we study in Section 3 the characteristic function of these processes and show in Section 4 that it enables us to derive the characteristic function of the log-price in Model (3). One numerical illustration is given in Section 5 and some proofs are relegated to Section 6. Finally, some useful technical results are given in an appendix.

## 2 From Hawkes processes to rough Heston models

We build in this section a sequence of Hawkes-type processes which converges to the rough Heston model (3). This construction is inspired by the paper [14]. In this work, microstructural foundations for rough Heston models are provided. This is done designing suitable sequences of ultra high frequency price models which reproduce the stylized facts of modern markets microstructure and converge in the long run to rough Heston models. These microscopic price models are based on Hawkes processes. So that the reader can well understand the genesis of our original methodology to compute the characteristic function in rough Heston models, we recall here the main ideas and results in [14].

## 2.1 Microstructural foundations for rough Heston models

In [14], we consider a sequence of bi-dimensional Hawkes processes $( N ^ { T , + } , N ^ { T , - } )$ indexed by $T > 0$ going to infinity<sup>1</sup> and with intensity

$$
\lambda _ { t } ^ { T } = \binom { \lambda _ { t } ^ { T , + } } { \lambda _ { t } ^ { T , - } } = \mu _ { T } \binom { 1 } { 1 } + \int _ { 0 } ^ { t } a _ { T } \phi ( t - s ) . \left( \begin{array} { l } { { d N _ { s } ^ { T , + } } } \\ { { d N _ { s } ^ { T , - } } } \end{array} \right) ,\tag{5}
$$

<sup>1</sup>Of course by T we implicitly mean T<sub>n</sub> with n ∈ N tending to infinity.

<!-- page: 5 -->

with

$$
\phi = \left( { \begin{array} { c c } { \varphi _ { 1 } } & { \varphi _ { 3 } } \\ { \varphi _ { 2 } } & { \varphi _ { 4 } } \end{array} } \right) .
$$

Here the $\varphi _ { i }$ are measurable non-negative deterministic functions and $\mu _ { T }$ and $0 < a _ { T } < 1$ are some deterministic sequences of positive real numbers, see [3] and the references therein for more details about the definition of Hawkes processes. Then in [14], inspired by [2, 3, 29], we consider the following ultra high frequency tick-by-tick model for the transaction price $P _ { t } ^ { T }$ :

$$
P _ { t } ^ { T } = N _ { t } ^ { T , + } - N _ { t } ^ { T , - } .
$$

Hence $N _ { t } ^ { T , + }$ represents the number of upward jumps of one tick of the transaction price over the period [0, t] and $N _ { t } ^ { T , }$ <sup>−</sup> the number of downward jumps. The relevance of this Hawkesbased modeling is that it enables us to encode very easily the most important stylized facts of high frequency markets in term of the parameters of the Hawkes process. We now give these stylized facts and their translation in term of the model parameters, referring to [14] for more details.

• Markets are highly endogenous: In the high frequency trading context, most orders have no real economic motivation. They are rather sent by algorithms as reaction to other orders. In the Hawkes framework, this amounts to work with so-called nearly unstable Hawkes processes. This means that the stability condition

$$
\mathcal { S } \big ( \int _ { 0 } ^ { \infty } a _ { T } \phi ( s ) d s \big ) < 1 ,
$$

where $s$ denotes the spectral radius operator, should almost be saturated and that the intensity of exogenous orders, namely $\mu _ { T }$ , should be small, see [14, 20, 28, 29]. In term of model parameters, suitable constraints are therefore

$$
a _ { T } \to 1 , ~ S \bigl ( \int _ { 0 } ^ { \infty } \phi ( s ) d s \bigr ) = 1 , ~ \mu _ { T } \to 0 .
$$

• It is not an easy task to make money with high frequency strategies on highly liquid electronic markets. Hence some “no statistical arbitrage” mechanisms should be in force. We translate this assuming that in the long run, there are on average as many upward than downward jumps. This corresponds to the assumption

$$
\varphi _ { 1 } + \varphi _ { 3 } = \varphi _ { 2 } + \varphi _ { 4 } .
$$

• Buying is not the same action as selling. This means that buy market orders and sell limit orders are not symmetric orders. To see this, consider for example a market maker, with an inventory which is typically positive. He is likely to raise the price by less following a buy order than to lower the price following the same size sell order. Indeed, its inventory becomes smaller after a buy order, which is a good thing for him, whereas it increases after a sell order. This creates a liquidity asymmetry on the bid and ask sides of the order book. This can be modeled in the Hawkes framework assuming that

$$
\varphi _ { 3 } = \beta \varphi _ { 2 } ,
$$

<!-- page: 6 -->

for some $\beta > 1$ . Hence, the matrix $\phi$ finally takes the form

$$
\phi = { \binom { \varphi _ { 1 } } { \varphi _ { 2 } } } \quad \qquad \beta \varphi _ { 2 } \quad \quad \quad \quad \quad \quad \quad \quad \quad \quad \quad \quad
$$

• A significant amount of transactions is part of metaorders, which are large orders whose execution is split in time by trading algorithms. This is translated into a heavy tail assumption on the functions $\varphi _ { 1 }$ and $\varphi _ { 2 }$ , namely that there exists $1 / 2 < \alpha < 1$ (typically around 0.6 in practice, see [4, 20]) and $C > 0$ such that

$$
\alpha x ^ { \alpha } \int _ { x } ^ { \infty } \varphi _ { 1 } ( s ) + \beta \varphi _ { 2 } ( s ) d s \operatorname * { \lrcorner } _ { x \mathrm { \scriptsize {  } } \infty } C .
$$

Furthermore, it is shown in [28] that for a given $\alpha ,$ there is only one way to make $\mu _ { T }$ tends to zero and $a _ { T }$ tends to one so that the limit of the price is not degenerate. More precisely,

$$
( 1 - a _ { T } ) T ^ { \alpha } { } _ { T  \infty } \lambda ^ { * } , \mu _ { T } T ^ { 1 - \alpha } { } _ { T  \infty } \mu ,
$$

for some positive $\lambda ^ { * }$ and $\mu .$

Under the above assumptions, it is proved in [14] that the properly rescaled microscopic price process

$$
\sqrt { \frac { 1 - a _ { T } } { \mu T ^ { \alpha } } } P _ { t T } ^ { T } , t \in [ 0 , 1 ]
$$

converges in law as $T$ tends to infinity to the following macroscopic price dynamic $P _ { t }$

$$
P _ { t } = \frac { \sqrt { 2 } } { 1 - \int _ { 0 } ^ { \infty } ( \varphi _ { 1 } - \varphi _ { 2 } ) } \int _ { 0 } ^ { t } \sigma _ { s } d W _ { s } ,
$$

$$
\sigma _ { t } ^ { 2 } = \frac { 1 } { \Gamma ( \alpha ) } \int _ { 0 } ^ { t } ( t - s ) ^ { \alpha - 1 } \lambda ( 1 - \sigma _ { s } ^ { 2 } ) d s + \frac { 1 } { \Gamma ( \alpha ) } \lambda \nu \int _ { 0 } ^ { t } ( t - s ) ^ { \alpha - 1 } \sigma _ { s } d B _ { s } ,\tag{6}
$$

where $( W , B )$ is a bi-dimensional correlated Brownian motion with correlation

$$
\rho = \frac { 1 - \beta } { \sqrt { 2 ( 1 + \beta ^ { 2 } ) } }
$$

and

$$
\nu = \sqrt { \frac { 2 ( 1 + \beta ^ { 2 } ) } { \lambda ^ { * } \mu ( 1 + \beta ) ^ { 2 } } } , \lambda = \lambda ^ { * } \frac { \alpha } { C \Gamma ( 1 - \alpha ) } .
$$

Hence this result shows that the main stylized facts of modern electronic markets naturally give rise to a very rough behavior of the volatility. Indeed, recall that the Hurst parameter corresponds to $\alpha - 1 / 2$

Inspired by this result, our idea is to study the characteristic function of some kind of microscopic price processes in order to deduce that of our rough Heston macroscopic price of interest (3). However, the developments presented above cannot be directly applied and need to be adapted. Indeed, remark that in (6), $\sigma _ { 0 } = 0$ . This does not correspond to the case of (3), where having a non-zero initial volatility is of course crucial for the model to be relevant in practice. Thus we need to modify the sequence of Hawkes-type processes to obtain a non-degenerate initial volatility in the limit. This is actually a non-trivial issue. However, this can be achieved replacing $\mu _ { T }$ in (5) by an inhomogeneous Poisson intensity ${ \hat { \mu } } _ { T } ( t )$ . We explain how such ${ \hat { \mu } } _ { T } ( t )$ can be found in the next section.

<!-- page: 7 -->

## 2.2 Finding the right Poisson rate

We work on a sequence of probability spaces $( \Omega ^ { T } , \mathcal { F } ^ { T } , \mathbb { P } ^ { T } )$ , indexed by $T > 1$ , on which $N ^ { T } = ( N ^ { T , + } , N ^ { T , - } )$ is a bi-dimensional Hawkes process with intensity:

$$
\lambda _ { t } ^ { T } = { \binom { \lambda _ { t } ^ { T , + } } { \lambda _ { t } ^ { T , - } } } = \hat { \mu } _ { T } ( t ) \binom { 1 } { 1 } + \int _ { 0 } ^ { t } \phi ^ { T } ( t - s ) . d N _ { s } ^ { T } .\tag{7}
$$

For a given $T _ { i }$ the probability space is equipped with the filtration $( \mathcal { F } _ { t } ^ { T } ) _ { t \geq 0 }$ , where $\mathbf { \mathcal { F } } _ { t } ^ { T }$ is the σ-algebra generated by $( N _ { s } ^ { T } ) _ { s \leq t }$ . Since our goal is to design a sequence of processes leading in the limit to a rough Heston dynamic, we consider the same kind of assumptions on the matrix $\phi ^ { T }$ as those described in the previous section. However, here we can be very specific since we just need to find one convenient sequence of processes. That is why we make a particular choice for the heavy-tailed functions defining $\phi ^ { T }$ , using Mittag-Lefler functions, see Section $\mathrm { A . 1 }$ in Appendix for definition and some properties. Indeed, these functions are very convenient in order to carry out computations. More precisely, our assumptions on $\phi ^ { T }$ are as follows.

Assumption 2.1. There exist $\beta \ge 0 , 1 / 2 < \alpha < 1$ and $\lambda > 0$ such that

$$
a _ { T } = 1 - \lambda T ^ { - \alpha } , ~ \phi ^ { T } = \varphi ^ { T } \chi ,
$$

where

$$
\chi = \frac { 1 } { \beta + 1 } \left( { 1 \atop 1 } \begin{array} { l } { { \beta } } \\ { { \beta } } \end{array} \right) , \varphi ^ { T } = a _ { T } \varphi , \varphi = f ^ { \alpha , 1 } ,
$$

with $f ^ { \alpha , 1 }$ the Mittag-Lefler density function defined in Appendix.

Remark 2.1. As in the previous section, we are working in the nearly unstable heavy tail case since

$$
\int _ { 0 } ^ { \infty } \varphi ( s ) d s = 1
$$

and

$$
\alpha x ^ { \alpha } \int _ { x } ^ { \infty } \varphi ( t ) d t \underset { x  \infty } { \longrightarrow } \frac { \alpha } { \Gamma ( 1 - \alpha ) } .
$$

We now give intuitions on how to find a suitable Poisson intensity ${ \hat { \mu } } _ { T } ( t )$ . The developments here are not very rigorous. They just aim at helping the reader to understand how our point processes sequence is designed. First, note that under Assumption 2.1,

$$
\lambda _ { t } ^ { T , + } = \lambda _ { t } ^ { T , - } .
$$

The asymptotic behavior of the renormalized intensity processes $\lambda _ { t } ^ { T , + }$ and $\lambda _ { t } ^ { T , - }$ will give us that of the volatility in our limiting macroscopic price model. Thus, we need to understand the long term limit of $\lambda _ { t } ^ { T , + }$ . Let us write

$$
M _ { t } ^ { T } = ( M _ { t } ^ { T , + } , M _ { t } ^ { T , - } ) = N _ { t } ^ { T } - \int _ { 0 } ^ { t } \lambda _ { s } ^ { T } d s
$$

for the martingale associated to the point process $N _ { t } ^ { T }$ . We easily obtain

$$
\lambda _ { t } ^ { T , + } = \hat { \mu } _ { T } ( t ) + \int _ { 0 } ^ { t } \varphi ^ { T } ( t - s ) \lambda _ { s } ^ { T , + } d s + \frac { 1 } { 1 + \beta } \int _ { 0 } ^ { t } \varphi ^ { T } ( t - s ) ( d M _ { s } ^ { T , + } + \beta d M _ { s } ^ { T , - } ) .
$$

<!-- page: 8 -->

Now let

$$
\psi ^ { T } = \sum _ { k \geq 1 } ( \varphi ^ { T } ) ^ { * k } ,
$$

where $( \varphi ^ { T } ) ^ { * 1 } = \varphi ^ { T }$ and for $\begin{array} { r } { k > 1 , ( \varphi ^ { T } ) ^ { * k } ( t ) = \int _ { 0 } ^ { t } \varphi ^ { T } ( s ) ( \varphi ^ { T } ) ^ { * ( k - 1 ) } ( t - s ) d s } \end{array}$ . Using Lemma A.1 in Appendix together with Fubini theorem and the fact that $\psi ^ { T } * \varphi ^ { T } = \psi ^ { T } - \varphi ^ { \bar { T } }$ , we get

$$
\lambda _ { t } ^ { T , + } = \hat { \mu } _ { T } ( t ) + \int _ { 0 } ^ { t } \psi ^ { T } ( t - s ) \hat { \mu } _ { T } ( s ) d s + \frac { 1 } { 1 + \beta } \int _ { 0 } ^ { t } \psi ^ { T } ( t - s ) ( d M _ { s } ^ { T , + } + \beta d M _ { s } ^ { T , - } ) .\tag{8}
$$

Following [14], the inhomogeneous intensity ${ \hat { \mu } } _ { T } ( t )$ should be of order $\mu _ { T }$ with

$$
\mu _ { T } = \mu T ^ { \alpha - 1 } ,
$$

where $\mu$ is some positive constant. In [14], it is shown that the right normalization for the intensity in order to get a non-degenerate limit is to consider $( 1 - a _ { T } ) \lambda _ { t T } ^ { T , + } / \mu _ { T }$ . The same applies here and thus we define the renormalized intensity

$$
C _ { t } ^ { T } = \frac { 1 - a _ { T } } { \mu _ { T } } \lambda _ { t T } ^ { T , + } .
$$

After obvious computations, this can be written

$$
C _ { t } ^ { T } = \frac { 1 - a _ { T } } { \mu _ { T } } \hat { \mu } _ { T } ( t T ) + \int _ { 0 } ^ { t } T ( 1 - a _ { T } ) \psi ^ { T } \big ( T ( t - s ) \big ) \frac { \hat { \mu } _ { T } ( T s ) } { \mu _ { T } } d s + \nu \int _ { 0 } ^ { t } T ( 1 - a _ { T } ) \psi ^ { T } \big ( T ( t - s ) \big ) \sqrt { C _ { s } ^ { T } } d B _ { s } ^ { T } ,
$$

where

$$
B _ { t } ^ { T } = \int _ { 0 } ^ { t T } \frac { d M _ { s } ^ { T , + } + \beta d M _ { s } ^ { T , - } } { \sqrt { T ( \lambda _ { s } ^ { T , + } + \beta ^ { 2 } \lambda _ { s } ^ { T , - } ) } } , ~ \nu = \sqrt { \frac { 1 + \beta ^ { 2 } } { \lambda \mu ( 1 + \beta ) ^ { 2 } } } .
$$

Using the fact that the Laplace transform $\hat { f } ^ { \alpha , \lambda }$ of the Mittag-Lefler density function $f ^ { \alpha , \lambda }$ is given by

$$
\hat { f } ^ { \alpha , \lambda } ( z ) = \frac { \lambda } { \lambda + z ^ { \alpha } } ,
$$

we easily obtain that

$$
( 1 - a _ { T } ) T \psi ^ { T } ( T . ) = a _ { T } f ^ { \alpha , \lambda } ,\tag{9}
$$

see Section A.1 in Appendix. This leads to the following expression for $C ^ { T }$ :

$$
C _ { t } ^ { T } = \frac { 1 - a _ { T } } { \mu _ { T } } \hat { \mu } _ { T } ( t T ) + \int _ { 0 } ^ { t } a _ { T } f ^ { \alpha , \lambda } ( t - s ) \frac { \hat { \mu } _ { T } ( T s ) } { \mu _ { T } } d s + \nu \int _ { 0 } ^ { t } a _ { T } f ^ { \alpha , \lambda } ( t - s ) \sqrt { C _ { s } ^ { T } } d B _ { s } ^ { T } .
$$

Computing the quadratic variation of $B ^ { T }$ , it is easy to see that it converges to a Brownian motion B. Now, if as in [14] we take $\hat { \mu } _ { T } ( t ) = \mu _ { T } , C ^ { T }$ should then give in the limit a process $\sigma ^ { 2 }$ satisfying

$$
\sigma _ { t } ^ { 2 } = F ^ { \alpha , \lambda } ( t ) + \nu \int _ { 0 } ^ { t } f ^ { \alpha , \lambda } ( t - s ) \sigma _ { s } d B _ { s } ,
$$

where

$$
F ^ { \alpha , \lambda } ( t ) = \int _ { 0 } ^ { t } f ^ { \alpha , \lambda } ( u ) d u .
$$

<!-- page: 9 -->

From Proposition 6.3 in Section 6, this is equivalent to

$$
\sigma _ { t } ^ { 2 } = \frac { 1 } { \Gamma ( \alpha ) } \int _ { 0 } ^ { t } ( t - s ) ^ { \alpha - 1 } \lambda ( 1 - \sigma _ { s } ^ { 2 } ) d s + \frac { 1 } { \Gamma ( \alpha ) } \lambda \nu \int _ { 0 } ^ { t } ( t - s ) ^ { \alpha - 1 } \sigma _ { s } d B _ { s } ,
$$

which corresponds to (6). However, recall that we wish to obtain a limit where the initial volatility does not vanish, that is a process of the form

$$
\sigma _ { t } ^ { 2 } = \xi + \frac { 1 } { \Gamma ( \alpha ) } \int _ { 0 } ^ { t } ( t - s ) ^ { \alpha - 1 } \lambda ( 1 - \sigma _ { s } ^ { 2 } ) d s + \frac { 1 } { \Gamma ( \alpha ) } \lambda \nu \int _ { 0 } ^ { t } ( t - s ) ^ { \alpha - 1 } \sigma _ { s } d B _ { s } ,\tag{10}
$$

with $\xi > 0$ . Again from Proposition 6.3 in Section 6, the dynamic (10) is equivalent to

$$
\sigma _ { t } ^ { 2 } = \xi \big ( 1 - F ^ { \alpha , \lambda } ( t ) \big ) + F ^ { \alpha , \lambda } ( t ) + \nu \int _ { 0 } ^ { t } f ^ { \alpha , \lambda } ( t - s ) \sigma _ { s } d B _ { s } .
$$

Using the same heuristic arguments as above, we see that we should obtain this dynamic in the limit provided we work with a process $C _ { t } ^ { T }$ having the following expression:

$$
C _ { t } ^ { T } = ( 1 - a _ { T } ) + \xi + ( 1 - \xi ) \int _ { 0 } ^ { t } T ( 1 - a _ { T } ) \psi \big ( T ( t - s ) \big ) d s + \nu \int _ { 0 } ^ { t } T ( 1 - a _ { T } ) \psi \big ( T ( t - s ) \big ) \sqrt { C _ { s } ^ { T } } d B _ { s } ^ { T } .
$$

This is equivalent to

$$
\lambda _ { t } ^ { T , + } = \mu _ { T } + \xi \mu _ { T } \frac { 1 } { 1 - a _ { T } } + \mu _ { T } ( 1 - \xi ) \int _ { 0 } ^ { t } \psi ^ { T } ( t - s ) d s + \frac { 1 } { 1 + \beta } \int _ { 0 } ^ { t } \psi ^ { T } ( t - s ) ( d M _ { s } ^ { T , + } + \beta d M _ { s } ^ { T , - } ) .\tag{11}
$$

Therefore, identifying parameters in (8) and (11), this indicates that we should take $\hat { \mu } _ { T }$ such that

$$
\hat { \mu } _ { T } ( t ) + \int _ { 0 } ^ { t } \psi ^ { T } ( t - s ) \hat { \mu } _ { T } ( s ) d s = \mu _ { T } + \xi \mu _ { T } \frac { 1 } { 1 - a _ { T } } + \mu _ { T } ( 1 - \xi ) \int _ { 0 } ^ { t } \psi ^ { T } ( t - s ) d s .\tag{12}
$$

Using convolution by $\varphi ^ { T }$ together with the fact that $\psi ^ { T } * \varphi ^ { T } = \psi ^ { T } - \varphi ^ { T }$ , we obtain from the left-hand side of (12):

$$
\begin{array} { r l } & { \displaystyle \int _ { 0 } ^ { t } \hat { \mu } _ { T } ( s ) \varphi ^ { T } ( t - s ) d s + \int _ { 0 } ^ { t } \int _ { 0 } ^ { s } \psi ^ { T } ( s - u ) \hat { \mu } _ { T } ( u ) d u \varphi ^ { T } ( t - s ) d s } \\ & { = \displaystyle \int _ { 0 } ^ { t } \hat { \mu } _ { T } ( s ) \varphi ^ { T } ( t - s ) d s + \int _ { 0 } ^ { t } \int _ { 0 } ^ { t - u } \psi ^ { T } ( s ) \varphi ^ { T } ( t - u - s ) d s \hat { \mu } _ { T } ( u ) d u } \\ & { = \displaystyle \int _ { 0 } ^ { t } \hat { \mu } _ { T } ( s ) \varphi ^ { T } ( t - s ) d s + \int _ { 0 } ^ { t } \big ( \psi ^ { T } ( t - u ) - \varphi ^ { T } ( t - u ) \big ) \hat { \mu } _ { T } ( u ) d u } \\ & { = \displaystyle \int _ { 0 } ^ { t } \psi ^ { T } ( t - s ) \hat { \mu } _ { T } ( s ) d s . } \end{array}
$$

From the right-hand side of (12), we get:

$$
\begin{array} { l l l } { \displaystyle \int _ { 0 } ^ { t } \varphi ^ { T } ( t - s ) \big ( \mu _ { T } + \xi \mu _ { T } \frac { 1 } { 1 - a _ { T } } \big ) d s + \mu _ { T } ( 1 - \xi ) \int _ { 0 } ^ { t } \varphi ^ { T } ( t - s ) \int _ { 0 } ^ { s } \psi ^ { T } ( s - u ) d u d s } \\ { \displaystyle = \mu _ { T } ( 1 + \xi \frac { 1 } { 1 - a _ { T } } ) \int _ { 0 } ^ { t } \varphi ^ { T } ( t - s ) d s + \mu _ { T } ( 1 - \xi ) \int _ { 0 } ^ { t } \int _ { 0 } ^ { t - u } \psi ^ { T } ( s ) \varphi ^ { T } ( t - u - s ) d s d u } \\ { \displaystyle = \mu _ { T } ( 1 + \xi \frac { 1 } { 1 - a _ { T } } ) \int _ { 0 } ^ { t } \varphi ^ { T } ( t - s ) d s + \mu _ { T } ( 1 - \xi ) \int _ { 0 } ^ { t } \big ( \psi ^ { T } ( t - u ) - \varphi ^ { T } ( t - u ) \big ) d u . } \end{array}
$$

<!-- page: 10 -->

Consequently, the following equality should hold for a well-chosen $\hat { \mu } _ { T } ( s )$

$$
\int _ { 0 } ^ { t } \psi ^ { T } ( t - s ) \hat { \mu } _ { T } ( s ) d s = \mu _ { T } \xi \big ( \frac { 1 } { 1 - a _ { T } } + 1 \big ) \int _ { 0 } ^ { t } \varphi ^ { T } ( t - s ) d s + \mu _ { T } ( 1 - \xi ) \int _ { 0 } ^ { t } \psi ^ { T } ( t - s ) d s .
$$

This last equation together with (12) gives

$$
\hat { \mu } _ { T } ( t ) = \mu _ { T } + \xi \mu _ { T } \frac { 1 } { 1 - a _ { T } } \big ( 1 - \int _ { 0 } ^ { t } \varphi ^ { T } ( t - s ) d s \big ) - \mu _ { T } \xi \int _ { 0 } ^ { t } \varphi ^ { T } ( t - s ) d s .\tag{13}
$$

Therefore, we should choose a non-homogenous baseline intensity ˆµ<sub>T</sub> satisfying (13). In that case, we should recover the process (10) for the limiting behavior of $C _ { t } ^ { T }$

In light of the preceding computations, we consider from now on the following assumption.

Assumption 2.2. The baseline intensity µˆ<sub>T</sub> is given by

$$
\hat { \mu } _ { T } ( t ) = \mu _ { T } + \xi \mu _ { T } \big ( \frac { 1 } { 1 - a _ { T } } ( 1 - \int _ { 0 } ^ { t } \varphi ^ { T } ( s ) d s ) - \int _ { 0 } ^ { t } \varphi ^ { T } ( s ) d s \big ) ,
$$

with $\xi > 0$ and $\mu _ { T } = \mu T ^ { \alpha - 1 }$ for some $\mu > 0$

Remark 2.2. Note that $\hat { \mu } _ { T }$ can also be written as follows:

$$
\hat { \mu } _ { T } ( t ) = \mu _ { T } + \xi \mu _ { T } \big ( \frac { T ^ { \alpha } } { \lambda } \int _ { t } ^ { \infty } \varphi ( s ) d s + \lambda T ^ { - \alpha } \int _ { 0 } ^ { t } \varphi ( s ) d s \big ) .
$$

This shows that $\hat { \mu } _ { T }$ is a positive function and thus that the intensity process $\lambda _ { t } ^ { T }$ in (7) is well-defined.

## 2.3 The rough limits of Hawkes processes

We now give a rigorous statement about the limiting behavior of our specific sequence of bi-dimensional nearly unstable Hawkes processes with heavy tails. For $t \in [ 0 , 1 ]$ , we define

$$
X _ { t } ^ { T } = \frac { 1 - a _ { T } } { T ^ { \alpha } \mu } N _ { t T } ^ { T } , ~ \Lambda _ { t } ^ { T } = \frac { 1 - a _ { T } } { T ^ { \alpha } \mu } \int _ { 0 } ^ { t T } \lambda _ { s } ^ { T } d s , ~ Z _ { t } ^ { T } = \sqrt { \frac { T ^ { \alpha } \mu } { 1 - a _ { T } } } ( X _ { t } ^ { T } - \Lambda _ { t } ^ { T } ) .
$$

Using a similar approach as that in [14], we obtain the following result whose proof is given in Section 6.

Theorem 2.1. As $T \to \infty$ , under Assumptions 2.1 and 2.2, the process $\left( \Lambda _ { t } ^ { T } , X _ { t } ^ { T } , Z _ { t } ^ { T } \right) _ { t \in [ 0 , 1 ] }$ converges in law for the Skorokhod topology to $( \Lambda , X , Z )$ where

$$
\Lambda _ { t } = X _ { t } = \int _ { 0 } ^ { t } Y _ { s } d s \left( 1 \atop 1 \right) , Z _ { t } = \int _ { 0 } ^ { t } \sqrt { Y _ { s } } \left( { d B _ { s } ^ { 1 } } \atop { d B _ { s } ^ { 2 } } \right) ,
$$

and Y is the unique solution of the rough stochastic diferential equation

$$
Y _ { t } = \xi + \frac { 1 } { \Gamma ( \alpha ) } \int _ { 0 } ^ { t } ( t - s ) ^ { \alpha - 1 } \lambda ( 1 - Y _ { s } ) d s + \lambda \sqrt { \frac { 1 + \beta ^ { 2 } } { \lambda \mu ( 1 + \beta ^ { 2 } ) } } \frac { 1 } { \Gamma ( \alpha ) } \int _ { 0 } ^ { t } ( t - s ) ^ { \alpha - 1 } \sqrt { Y _ { s } } d B _ { s } ,
$$

<!-- page: 11 -->

where

$$
B = \frac { B ^ { 1 } + \beta B ^ { 2 } } { \sqrt { 1 + \beta ^ { 2 } } }
$$

and $( B ^ { 1 } , B ^ { 2 } )$ is a bi-dimensional Brownian motion. Furthermore, for any $\varepsilon > 0$ , Y has H¨older regularity $\alpha - 1 / 2 - \varepsilon$

Hence Theorem 2.1 shows that designing our sequence of bi-dimensional Hawkes processes in a suitable way, its limit is diferentiable and its derivative exhibits a rough Cox-Ingersoll-Ross like behavior, with non-zero initial value. This is exactly what we need for the limiting volatility of our microscopic price processes. Indeed, thanks to Theorem 2.1, we are now able to build such microscopic processes converging to the log-price in (3). More precisely, for $\theta > 0$ , let us define

$$
P ^ { T } = \sqrt { \frac { \theta } { 2 } } \sqrt { \frac { 1 - a _ { T } } { T ^ { \alpha } \mu } } ( N _ { . T } ^ { T , + } - N _ { . T } ^ { T , - } ) - \frac { \theta } { 2 } \frac { 1 - a _ { T } } { T ^ { \alpha } \mu } N _ { . T } ^ { T , + } = \sqrt { \frac { \theta } { 2 } } ( Z ^ { T , + } - Z ^ { T , - } ) - \frac { \theta } { 2 } X ^ { T , + } .\tag{14}
$$

We have the following corollary of Theorem 2.1.

Corollary 2.1. As $T \infty$ , under Assumptions 2.1 and ${ \it 2 . 2 , }$ the sequence of processes $( P _ { t } ^ { T } ) _ { t \in [ 0 , 1 ] }$ converges in law for the Skorokhod topology to

$$
P _ { t } = \int _ { 0 } ^ { t } \sqrt { V _ { s } } d W _ { s } - \frac { 1 } { 2 } \int _ { 0 } ^ { t } V _ { s } d s ,
$$

where V is the unique solution of the rough stochastic diferential equation

$$
V _ { t } = \theta \xi + \frac { 1 } { \Gamma ( \alpha ) } \int _ { 0 } ^ { t } ( t - s ) ^ { \alpha - 1 } \lambda ( \theta - V _ { s } ) d s + \lambda \sqrt { \frac { \theta ( 1 + \beta ^ { 2 } ) } { \lambda \mu ( 1 + \beta ) ^ { 2 } } } \frac { 1 } { \Gamma ( \alpha ) } \int _ { 0 } ^ { t } ( t - s ) ^ { \alpha - 1 } \sqrt { V _ { s } } d B _ { s } ,
$$

with (W, B) a correlated bi-dimensional Brownian motion whose bracket satisfies

$$
d \langle W , B \rangle _ { t } = \frac { 1 - \beta } { \sqrt { 2 ( 1 + \beta ^ { 2 } ) } } d t .
$$

Thus, we have succeeded in building a sequence of microscopic processes $P ^ { T }$ , defined by (14), which converges to (the logarithm of) our rough Heston process of interest (3). Now our goal is to use the result of Corollary 2.1 to compute the characteristic function of the log-price in the rough Heston model (3). This is done in the next two sections.

## 3 The characteristic function of multivariate Hawkes processes

We have seen in the previous section that our sequence of Hawkes-based microscopic price processes converges to the log-price in the rough Heston model (3). Therefore, if we are able to compute the characteristic function for the microscopic price, its limit will give us that of the log-price in a rough Heston model. We actually provide a more general result here, deriving the characteristic function of a multivariate Hawkes process (recall that a bidimensional Hawkes process is the building block for our microscopic price process (14)). Hence we extend here some results already proved in [22] in the one-dimensional case.

<!-- page: 12 -->

## 3.1 Cluster-based representation

To derive our characteristic function, the representation of Hawkes processes in term of clusters, see [22], is very useful. We recall it now. Let us consider a d-dimensional Hawkes process $N = ( N ^ { 1 } , . . . , N ^ { d } )$ with intensity

$$
\lambda _ { t } = \binom { \lambda _ { t } ^ { 1 } } { \vdots } = \mu ( t ) + \int _ { 0 } ^ { t } \phi ( t - s ) . d N _ { s } ,\tag{15}
$$

where $\mu : \mathbb { R } _ { + } \to \mathbb { R } _ { + } ^ { d }$ is locally integrable and $\phi : \mathbb { R } _ { + } \to \mathcal { M } ^ { \mathbf { d } } ( \mathbb { R } _ { + } )$ has integrable components such that

$$
S ( \int _ { 0 } ^ { \infty } \phi ( s ) d s ) < 1 .
$$

The law of such process can be described through a population approach. Consider that there are d types of individuals and for a given type, an individual can be either a migrant or the descendant of a migrant. Then the dynamic goes as follows from time $t = 0 \colon$

• Migrants of type $k \in \{ 1 , . . , d \}$ arrive as a non-homogenous Poisson process with rate $\mu _ { k } ( t )$

• Each migrant of type $k \in \{ 1 , . . , d \}$ gives birth to children of type $j \in \{ 1 , . . , d \}$ following a non-homogenous Poisson process with rate $\phi _ { j , k } ( t )$

• Each child of type $k \in \{ 1 , . . , d \}$ also gives birth to other children of type $j \in \{ 1 , . . , d \}$ following a non-homogenous Poisson process with rate $\phi _ { j , k } ( t )$

Then, for $k \in \{ 1 , . . , d \} , N _ { t } ^ { k }$ can be taken as the number up to time t of migrants and children born with type k. Indeed, the population approach above and the theoretical characterization (15) define the same point process law.

## 3.2 The result

Let $L ( \boldsymbol { a } , t )$ be the characteristic function of the Hawkes process $N$

$$
L ( a , t ) = \mathbb { E } [ \exp ( i a . N _ { t } ) ] , t \geq 0 , a \in \mathbb { R } ^ { d } ,
$$

where $a . N _ { t }$ stands for the scalar product of a and $N _ { t }$ . The cluster-based representation of multivariate Hawkes processes enables us to show the following result, proved in Section 3.3, for their characteristic function.

Theorem 3.1. We have

$$
L ( a , t ) = \exp \big ( \int _ { 0 } ^ { t } \big ( C ( a , t - s ) - \mathbf 1 \big ) . \mu ( s ) d s \big ) ,
$$

where $C : \mathbb { R } ^ { d } \times \mathbb { R } _ { + } \to \mathbb { C } ^ { d }$ is solution of the following integral equation:

$$
C ( { a } , t ) = \exp \big ( i a + \int _ { 0 } ^ { t } \phi ^ { * } ( s ) . ( C ( { a } , t - s ) - 1 ) d s \big ) ,
$$

with $\phi ^ { * } ( s )$ the transpose of $\phi ( s )$

From Theorem 3.1, we are able to derive in Section 4 the characteristic function of rough Heston models.

<!-- page: 13 -->

## 3.3 Proof of Theorem 3.1

We now give the proof of Theorem 3.1, exploiting the population construction presented in Section 3.1. We start by defining d auxiliary independent d-dimensional point processes $( \tilde { N } ^ { k , j } ) _ { 1 \leq j \leq d } , k \in \{ 1 , . . . , d \}$ , defined as follows for each given $k \in \{ 1 , . . , d \}$

• Migrants of type $j \in \{ 1 , . . . , d \}$ arrive as a non-homogenous Poisson process with rate $\phi _ { j , k } ( t )$

• Each migrant of type $j \in \{ 1 , . . , d \}$ gives birth to children of type $l \in \{ 1 , . . , d \}$ following a non-homogenous Poisson process with rate $\phi _ { l , j } ( t )$

• Each child of type $j \in \{ 1 , . . , d \}$ also gives birth to other children of type $l \in \{ 1 , . . , d \}$ following a non-homogenous Poisson process with rate $\phi _ { l , j } ( t )$

For a given $k \in \{ 1 , . . , d \} , \tilde { N } _ { t } ^ { k , j }$ corresponds to the number, up to time $t ,$ of migrants and children with type $j . \mathrm { ~ \ r ~ { ~ A ~ } ~ }$ simple but crucial remark is that $( \tilde { N } ^ { k , j } ) _ { 1 \leq j \leq d }$ is actually also a multivariate Hawkes process with migrant rate $\left( \phi _ { j , k } \right) _ { 1 \leq j \leq d }$ and kernel matrix $\phi .$ . We write $L _ { k } ( \boldsymbol { a } , t )$ for its characteristic function

$$
L _ { k } ( a , t ) = \mathbb { E } \big [ \exp ( i a . ( \tilde { N } _ { t } ^ { k , j } ) _ { 1 \leq j \leq d } ) \big ] , t \geq 0 , a \in \mathbb { R } ^ { d } .
$$

Now let us come back to the initial Hawkes process of interest N defined by (15). For each $k \in \{ 1 , . . . , d \}$ and $t \geq 0$ , let $N _ { t } ^ { 0 , k }$ be the number of its migrants of type k arrived up to time t. Recall that the $N ^ { 0 , k } , 1 \leq k \leq d .$ , are independent Poisson processes with rates $\mu _ { k } ( t )$ . We also define $T _ { 1 } ^ { k } < . . . < T _ { N _ { \cdot } ^ { 0 , k } } ^ { k } \in [ 0 , t ]$ the arrival times of migrants of type k of the Hawkes process $N$ , up to time t. Using the population approach presented in Section 3.1, it is clear that at time $t ,$ the number of descendants of diferent types of a migrant of type k arrived at time $T _ { u } ^ { k }$ has the same law as $( \tilde { N } _ { t - T _ { u } ^ { k } } ^ { k , j } ) _ { 1 \leq j \leq d }$ , where $\tilde { N }$ is taken independent from N. Consequently,

$$
N _ { t } ^ { k } \mathop { = } _ { l a w } N _ { t } ^ { 0 , k } + \sum _ { 1 \leq j \leq d } \sum _ { 1 \leq l \leq N _ { t } ^ { 0 , j } } \tilde { N } _ { t - T _ { l } ^ { j } } ^ { j , k , ( l ) } ,\tag{16}
$$

where the $( \tilde { N } ^ { j , k , ( l ) } ) _ { 1 < k < d } , 1 \le j \le d , l \in \mathbb { N }$ are independent copies of $( \tilde { N } ^ { j , k } ) _ { 1 \leq k \leq d } , 1 \leq j \leq d .$ also independent of $N ^ { 0 } = ( N ^ { 0 , k } ) \mathbb { 1 } { \leq } k { \leq } d .$

From (16), we derive that conditional on $N ^ { 0 }$

$$
\begin{array} { r l } & { \mathbb { E } \big [ \exp ( i a . N _ { t } ) | N ^ { 0 } \big ] = \exp ( i a . N _ { t } ^ { 0 } ) \prod _ { 1 \leq j \leq d } \prod _ { 1 \leq l \leq N _ { t } ^ { 0 , j } } \mathbb { E } \big [ \exp ( i a . ( \tilde { N } _ { t - T _ { l } ^ { j } } ^ { j , k , ( l ) } ) _ { 1 \leq k \leq d } | N ^ { 0 } ) \big ] } \\ & { = \exp ( i a . N _ { t } ^ { 0 } ) \prod _ { 1 \leq j \leq d } \prod _ { 1 \leq l \leq N _ { t } ^ { 0 , j } } L _ { j } ( a , t - T _ { l } ^ { j } ) . } \end{array}
$$

Now, for a given $k \in \{ 1 , . . . , d \}$ , conditional on $N _ { t } ^ { 0 , k }$ , it is well-known that $( T _ { 1 } ^ { k } , . . . , T _ { N _ { \ast } ^ { 0 , k } } ^ { k } )$ has the same law as $( X _ { ( 1 ) } , . . . , X _ { ( N _ { t } ^ { 0 , k } ) } )$ the order statistics built from iid variables $( X _ { 1 } , . . , X _ { N _ { t } ^ { 0 , k } } )$ with density $\frac { \mu _ { k } ( s ) 1 _ { s \leq t } } { \int _ { 0 } ^ { t } \mu _ { k } ( s ) d s }$ . Thus we get

$$
\mathbb { E } \big [ \exp ( i a . N _ { t } ) | N _ { t } ^ { 0 } \big ] = \exp ( i a . N _ { t } ^ { 0 } ) \prod _ { 1 \leq j \leq d } \big ( \int _ { 0 } ^ { t } L _ { j } ( a , t - s ) \frac { \mu _ { j } ( s ) } { \int _ { 0 } ^ { t } \mu _ { j } ( s ) d s } d s \big ) ^ { N _ { t } ^ { 0 , j } } .
$$

<!-- page: 14 -->

Therefore,

$$
L ( a , t ) = \prod _ { 1 \leq j \leq d } \exp \big ( ( \int _ { 0 } ^ { t } e ^ { i a _ { j } } L _ { j } ( a , t - s ) \frac { \mu _ { j } ( s ) } { \int _ { 0 } ^ { t } \mu _ { j } ( s ) d s } d s - 1 ) \int _ { 0 } ^ { t } \mu _ { j } ( s ) d s \big ) .
$$

Thus we finally obtain

$$
L ( a , t ) = \exp \big ( \sum _ { 1 \leq j \leq d } \int _ { 0 } ^ { t } ( e ^ { i a _ { j } } L _ { j } ( a , t - s ) - 1 ) \mu _ { j } ( s ) d s \big ) .\tag{17}
$$

In the same way, since $( \tilde { N } ^ { k , j } ) _ { 1 \leq j \leq d }$ is a multivariate Hawkes process with migrant rate $\left( \phi _ { j , k } \right) _ { 1 \leq j \leq d }$ and kernel matrix $\phi _ { ; }$ , we get

$$
L _ { k } ( a , t ) = \exp \big ( \sum _ { 1 \leq j \leq d } \int _ { 0 } ^ { t } ( e ^ { i a _ { j } } L _ { j } ( a , t - s ) - 1 ) \phi _ { j , k } ( s ) d s \big ) .\tag{18}
$$

Let us define

$$
C ( a , t ) = \left( e ^ { i a _ { j } } L _ { j } ( a , t ) \right) _ { 1 \leq j \leq d } .
$$

From (17), we have that

$$
L ( a , t ) = \exp \big ( \int _ { 0 } ^ { t } ( C ( a , t - s ) - \mathbf { 1 } ) . \mu ( s ) d s \big )
$$

and from (18), we deduce that C is solution of the following integral equation

$$
C ( { a } , t ) = \exp \big ( i a + \int _ { 0 } ^ { t } \phi ^ { * } ( s ) . ( C ( { a } , t - s ) - 1 ) d s \big ) .
$$

This ends the proof of Theorem 3.1.

## 4 The characteristic function of rough Heston models

We give in this section our main theorem, that is the characteristic function for the log-price in rough Heston models (3). It is obtained combining the convergence result for Hawkes processes stated in Corollary 2.1 together with the characteristic function for multivariate Hawkes processes derived in Theorem 3.1. We start with some intuitions about the result.

## 4.1 Intuition about the result

We consider the rough Heston model (3). The parameters of the dynamic in (3) are here given in term of those of the sequence of processes $P ^ { T }$ defined in (14). More precisely, we set

$$
V _ { 0 } = \xi \theta , \rho = \frac { 1 - \beta } { \sqrt { 2 ( 1 + \beta ^ { 2 } ) } } , \nu = \sqrt { \frac { \theta ( 1 + \beta ^ { 2 } ) } { \lambda \mu ( 1 + \beta ) ^ { 2 } } } ,
$$

and $\lambda$ and $\theta$ are the same as those in the dynamic of $P ^ { T }$ . Remark that this implies that $\rho \in ( - 1 / \sqrt { 2 } , 1 / \sqrt { 2 } ]$ . We also write $P _ { t } = \log ( S _ { t } / S _ { 0 } )$ . From Corollary 2.1, we know that

$$
P ^ { T } = \sqrt { \frac { \lambda \theta } { 2 \mu } } T ^ { - \alpha } ( N _ { . T } ^ { { T } , + } - N _ { . T } ^ { { T } , - } ) - \frac { \lambda \theta } { 2 \mu } T ^ { - 2 \alpha } N _ { . T } ^ { { T } , + }
$$

<!-- page: 15 -->

converges in law to $P$ as $T$ tends to infinity, where $N ^ { T } = ( N ^ { T , + } , N ^ { T , - } )$ is a sequence of bidimensional Hawkes processes satisfying Assumptions 2.1 and 2.2. Let us write $L ^ { T } ( ( a , b ) , t )$ for the characteristic function of the process $N ^ { T }$ at time t at point $( a , b )$ and $L _ { p }$ for the characteristic function of $P .$ The convergence in law implies that of $L ^ { T } ( ( a _ { T } ^ { + } , a _ { T } ^ { - } ) , t T )$ towards $L _ { p } ( a , t )$ , where

$$
a _ { T } ^ { + } = a \sqrt { \frac { \lambda \theta } { 2 \mu } } T ^ { - \alpha } - a \frac { \lambda \theta } { 2 \mu } T ^ { - 2 \alpha } , ~ a _ { T } ^ { - } = - a \sqrt { \frac { \lambda \theta } { 2 \mu } } T ^ { - \alpha } .
$$

From Theorem 3.1, we know that

$$
L ^ { T } \big ( ( a _ { T } ^ { + } , a _ { T } ^ { - } ) , t T \big ) = \exp \Big ( \int _ { 0 } ^ { t T } \hat { \mu } _ { T } ( s ) \big ( ( C ^ { T , + } ( ( a _ { T } ^ { + } , a _ { T } ^ { - } ) , t T - s ) - 1 ) + ( C ^ { T , - } ( ( a _ { T } ^ { + } , a _ { T } ^ { - } ) , t T - s ) - 1 ) \big ) d s \Big ) ,
$$

where $C ^ { T } ( ( a _ { T } ^ { + } , a _ { T } ^ { - } ) , t ) = \big ( C ^ { T , + } ( ( a _ { T } ^ { + } , a _ { T } ^ { - } ) , t ) , C ^ { T , - } ( ( a _ { T } ^ { + } , a _ { T } ^ { - } ) , t ) \big ) \in \mathcal { M } ^ { 1 \times 2 } ( \mathbb { C } )$ is solution of

$$
C ^ { T } \big ( ( a _ { T } ^ { + } , a _ { T } ^ { - } ) , t \big ) = \exp \big ( i ( a _ { T } ^ { + } , a _ { T } ^ { - } ) + \int _ { 0 } ^ { t } \big ( C ^ { T } ( ( a _ { T } ^ { + } , a _ { T } ^ { - } ) , t - s ) - ( 1 , 1 ) \big ) . \phi ^ { T } ( s ) d s \big ) .
$$

Now let

$$
\begin{array} { r } { Y ^ { T } ( a , . ) = \left( Y ^ { T , + } ( a , . ) , Y ^ { T , - } ( a , . ) \right) = C ^ { T } \big ( ( a _ { T } ^ { + } , a _ { T } ^ { - } ) , T \big ) : [ 0 , 1 ] \to \mathcal { M } ^ { 1 \times 2 } ( \mathbb { C } ) . } \end{array}
$$

Using a change of variables, we easily get that $Y ^ { T } ( a , . )$ is solution of the equation

$$
Y ^ { T } ( a , t ) = \exp \left( i ( a _ { T } ^ { + } , a _ { T } ^ { - } ) + T \int _ { 0 } ^ { t } \left( Y ^ { T } ( a , t - s ) - ( 1 , 1 ) \right) . \phi ^ { T } ( T s ) d s \right)\tag{19}
$$

and that

$$
L ^ { T } ( a _ { T } ^ { + } , a _ { T } ^ { - } , t T ) = \exp \Big ( \int _ { 0 } ^ { t } \big ( T ^ { \alpha } ( Y ^ { T , + } ( a , t - s ) - 1 ) + T ^ { \alpha } ( Y ^ { T , - } ( a , t - s ) - 1 ) \big ) \big ( T ^ { 1 - \alpha } \hat { \mu } ( s T ) \big ) d s \Big ) .\tag{20}
$$

Thanks to Remarks 2.1 and 2.2, it is easy to see that

$$
\begin{array} { l } { { \displaystyle T ^ { 1 - \alpha } \hat { \mu } ( s T ) = T ^ { 1 - \alpha } \mu _ { T } + \xi T ^ { 1 - \alpha } \mu _ { T } \big ( \frac { T ^ { \alpha } } { \lambda } \int _ { s T } ^ { \infty } \varphi ( u ) d u + \lambda T ^ { - \alpha } \int _ { 0 } ^ { s T } \varphi ( u ) d u \big ) } } \\ { { \displaystyle \qquad = \mu \big ( 1 + \frac { \xi } { \lambda } s ^ { - \alpha } ( s T ) ^ { \alpha } \int _ { s T } ^ { \infty } \varphi ( u ) d u \big ) + \mu \xi \lambda T ^ { - \alpha } \int _ { 0 } ^ { s T } \varphi ( u ) d u } } \\ { { \displaystyle \qquad \longrightarrow \mu \big ( 1 + \frac { \xi } { \lambda \Gamma ( 1 - \alpha ) } s ^ { - \alpha } \big ) } . } \end{array}
$$

Now, the convergence of $L ^ { T } ( a _ { T } ^ { + } , a _ { T } ^ { - } , t T )$ as $T$ goes to infinity implies that of

$$
\int _ { 0 } ^ { t } \left( T ^ { \alpha } ( Y ^ { T , + } ( a , t - s ) - 1 ) + T ^ { \alpha } ( Y ^ { T , - } ( a , t - s ) - 1 ) \right) \left( T ^ { 1 - \alpha } \hat { \mu } ( s T ) \right) d s .
$$

Thus, we can expect that as $T$ goes to infinity, $T ^ { \alpha } ( Y ^ { T } ( a , t ) - ( 1 , 1 ) )$ converges to some function $( c ( a , t ) , d ( a , t ) )$ (recall that the developments in this section are not rigourous and just aim at

<!-- page: 16 -->

giving intuitions for the main theorem). Furthermore, using that $( Y ^ { T } ( a , t ) - ( 1 , 1 ) ) = { \mathcal { O } } ( T ^ { - \alpha } )$ together with (20), we get

$$
\begin{array} { l } { { \displaystyle Y ^ { T } ( a , t ) - ( 1 , 1 ) = \log \left( Y ^ { T } ( a , t ) \right) + \frac { 1 } { 2 } \big ( Y ^ { T } ( a , t ) - ( 1 , 1 ) \big ) ^ { 2 } + o ( T ^ { - 2 \alpha } ) ( t ) } } \\ { { \displaystyle \qquad = i a \sqrt { \frac { \lambda \theta } { 2 \mu } } ( 1 , - 1 ) T ^ { - \alpha } - i a \frac { \lambda \theta } { 2 \mu } ( 1 , 0 ) T ^ { - 2 \alpha } + T \int _ { 0 } ^ { t } \big ( Y ^ { T } ( a , t - s ) - ( 1 , 1 ) \big ) . \phi ^ { T } ( T s ) d s } } \\ { { \displaystyle \qquad + \frac { 1 } { 2 } \big ( Y ^ { T } ( a , t ) - ( 1 , 1 ) \big ) ^ { 2 } + o ( T ^ { - 2 \alpha } ) ( t ) , } } \end{array}
$$

where the logarithm<sup>2</sup> function is applied on each component of $Y ^ { T } ( a , t )$ . Then, remarking that $\chi ^ { 2 } = \chi$ and using a change of variables, we get

$$
\sum _ { k \geq 1 } \big ( T \phi ^ { T } ( T . ) \big ) ^ { * k } = \sum _ { k \geq 1 } T ( \phi ^ { T } ) ^ { * k } ( T . ) = T \sum _ { k \geq 1 } ( \varphi ^ { T } ) ^ { * k } ( T . ) \chi ^ { k } = T \psi ^ { T } ( T . ) \chi .
$$

From (9), we finally deduce that

$$
\sum _ { k \geq 1 } \left( T \phi ^ { T } ( T . ) \right) ^ { * k } = a _ { T } { \frac { T ^ { \alpha } } { \lambda } } f ^ { \alpha , \lambda } \chi = a _ { T } { \frac { T ^ { \alpha } } { \lambda ( \beta + 1 ) } } f ^ { \alpha , \lambda } \left( 1 \begin{array} { c c } { { 1 } } & { { \beta } } \\ { { 1 } } & { { \beta } } \end{array} \right) .
$$

Since $( 1 , - 1 ) . \chi = 0$ , using Lemma A.1 in Appendix we obtain

$$
\begin{array} { c } { { Y ^ { T } ( a , t ) - ( 1 , 1 ) = i a \sqrt { \displaystyle \frac { \lambda \theta } { 2 \mu } } ( 1 , - 1 ) T ^ { - \alpha } - i a \frac { a _ { T } \theta } { 2 \mu ( \beta + 1 ) } F ^ { \alpha , \lambda } ( t ) ( 1 , \beta ) T ^ { - \alpha } } } \\ { { + \displaystyle \frac { a _ { T } T ^ { \alpha } } { 2 \lambda ( \beta + 1 ) } \displaystyle \int _ { 0 } ^ { t } f ^ { \alpha , \lambda } ( s ) \big ( Y ^ { T } ( a , t - s ) - ( 1 , 1 ) \big ) ^ { 2 } . \left( \displaystyle \frac { 1 } { 1 } \shuffle \displaystyle \beta \right) d s + o ( T ^ { - \alpha } ) ( t ) . } } \end{array}
$$

Therefore, we can expect that

$$
c ( a , t ) = i a \sqrt { \frac { \lambda \theta } { 2 \mu } } - i a \frac { \theta } { 2 \mu ( \beta + 1 ) } F ^ { \alpha , \lambda } ( t ) + \frac { 1 } { 2 \lambda ( \beta + 1 ) } \int _ { 0 } ^ { t } f ^ { \alpha , \lambda } ( s ) \big ( c ^ { 2 } ( a , t - s ) + d ^ { 2 } ( a , t - s ) \big ) d s ,
$$

$$
d ( a , t ) = - i a \sqrt { \frac { \lambda \theta } { 2 \mu } } - i a \frac { \beta \theta } { 2 \mu ( \beta + 1 ) } F ^ { \alpha , \lambda } ( t ) + \frac { \beta } { 2 \lambda ( \beta + 1 ) } \int _ { 0 } ^ { t } f ^ { \alpha , \lambda } ( s ) \big ( c ^ { 2 } ( a , t - s ) + d ^ { 2 } ( a , t - s ) \big ) d s
$$

and

$$
L _ { p } ( a , t ) = \exp \big ( \int _ { 0 } ^ { t } g ( a , s ) d s + \frac { V _ { 0 } } { \theta \lambda } \frac { 1 } { \Gamma ( 1 - \alpha ) } \int _ { 0 } ^ { t } g ( a , s ) ( t - s ) ^ { - \alpha } d s \big ) ,
$$

with $g = \mu ( c + d )$ . We give in the next section a rigorous statement for this result.

## 4.2 Main result

We define the fractional integral of order $r \in ( 0 , 1 ]$ of a function f as

$$
I ^ { r } f ( t ) = \frac { 1 } { \Gamma ( r ) } \int _ { 0 } ^ { t } ( t - s ) ^ { r - 1 } f ( s ) d s ,\tag{21}
$$

<sup>2</sup>The complex logarithm is defined on C/R<sup>−</sup> by log(z) = log(|z|) + i arg(z), with arg(z) ∈ (−π, π].

<!-- page: 17 -->

whenever the integral exists, and the fractional derivative of order $r \in [ 0 , 1 )$ as

$$
D ^ { r } f ( t ) = \frac { 1 } { \Gamma ( 1 - r ) } \frac { d } { d t } \int _ { 0 } ^ { t } ( t - s ) ^ { - r } f ( s ) d s ,\tag{22}
$$

whenever it exists. The following theorem, proved in Section 6, is the main result of the paper.

Theorem 4.1. Consider the rough Heston model (3) with a correlation between the two Brownian motions ρ satisfying $\rho \in ( - 1 / \sqrt { 2 } , 1 / \sqrt { 2 } ]$ . For all $t \geq 0$ , we have

$$
L _ { p } ( a , t ) = \exp \big ( \theta \lambda I ^ { 1 } h ( a , t ) + V _ { 0 } I ^ { 1 - \alpha } h ( a , t ) \big ) ,\tag{23}
$$

where h is solution of the fractional Riccati equation

$$
D ^ { \alpha } h ( a , t ) = \frac 1 2 ( - a ^ { 2 } - i a ) + \lambda ( i a \rho \nu - 1 ) h ( a , s ) + \frac { ( \lambda \nu ) ^ { 2 } } { 2 } h ^ { 2 } ( a , s ) , I ^ { 1 - \alpha } h ( a , 0 ) = 0 ,\tag{24}
$$

which admits a unique continuous solution.

Thus we have been able to obtain a semi-closed formula for the characteristic function in rough Heston models. This means that pricing of European options becomes an easy task in this model, see Section 5. For $\alpha = 1$ , we retrieve the classical Heston formula. For $\alpha < 1$ the formula is almost the same. The diference is essentially only in that in the Riccat equation, the classical derivative is replaced by a fractional derivative. The drawback is that such fractional Riccati equations do not have explicit solutions. However, they can be solved numerically almost instantaneously, see Section 5. Finally, note that this strong link between Hawkes processes and (rough) Heston models is probably natural since both of them exhibit some kind of afine structure (although infinite-dimensional).

## 5 Numerical application

## 5.1 Numerical scheme

We explain in this section how to compute numerically the characteristic function of the log-price in a rough Heston model. By Theorem 4.1, $L _ { p } ( a , t )$ is entirely defined through the fractional Riccati equation (24)

$$
D ^ { \alpha } h ( a , t ) = F { \big ( } a , h ( a , t ) { \big ) } , I ^ { 1 - \alpha } h ( a , 0 ) = 0 ,
$$

where

$$
F ( a , x ) = { \frac { 1 } { 2 } } ( - a ^ { 2 } - i a ) + \lambda ( i a \rho \nu - 1 ) x + { \frac { ( \lambda \nu ) ^ { 2 } } { 2 } } x ^ { 2 } .
$$

Several schemes for solving numerically (24) can be found in the literature. Most of them are based on the idea that (24) implies the following Volterra equation:

$$
h ( a , t ) = \frac { 1 } { \Gamma ( \alpha ) } \int _ { 0 } ^ { t } ( t - s ) ^ { \alpha - 1 } F \big ( a , h ( a , s ) \big ) d s .\tag{25}
$$

<!-- page: 18 -->

Then one develops numerical schemes for (25). Here we choose the well-known fractional Adams method investigated in [10, 11, 12]. The idea goes as follows. Let us write $g ( a , t ) =$ $F \big ( a , h ( a , t ) \big )$ . Over a regular discrete time-grid $( t _ { k } ) _ { k \in \mathbb { N } }$ with mesh $\Delta \ ( t _ { k } = k \Delta )$ , we estimate

$$
h ( a , t _ { k + 1 } ) = \frac { 1 } { \Gamma ( \alpha ) } \int _ { 0 } ^ { t _ { k + 1 } } ( t _ { k + 1 } - s ) ^ { \alpha - 1 } g ( a , s ) d s
$$

by

$$
\frac { 1 } { \Gamma ( \alpha ) } \int _ { 0 } ^ { t _ { k + 1 } } ( t _ { k + 1 } - s ) ^ { \alpha - 1 } \hat { g } ( a , s ) d s ,
$$

where

$$
\hat { g } ( a , t ) = \frac { t _ { j + 1 } - t } { t _ { j + 1 } - t _ { j } } \hat { g } ( a , t _ { j } ) + \frac { t - t _ { j } } { t _ { j + 1 } - t _ { j } } \hat { g } ( a , t _ { j + 1 } ) , t \in [ t _ { j } , t _ { j + 1 } ) , 0 \le j \le k .
$$

This corresponds to a trapezoidal discretization of the fractional integral and leads to the following scheme:

$$
\hat { h } ( a , t _ { k + 1 } ) = \sum _ { 0 \leq j \leq k } a _ { j , k + 1 } F \big ( a , \hat { h } ( a , t _ { j } ) \big ) + a _ { k + 1 , k + 1 } F \big ( a , \hat { h } ( a , t _ { k + 1 } ) \big ) ,\tag{26}
$$

with

$$
a _ { 0 , k + 1 } = \frac { \Delta ^ { \alpha } } { \Gamma ( \alpha + 2 ) } \big ( k ^ { \alpha + 1 } - ( k - \alpha ) ( k + 1 ) ^ { \alpha } \big ) ,
$$

$$
a _ { j , k + 1 } = \frac { \Delta ^ { \alpha } } { \Gamma ( \alpha + 2 ) } \big ( ( k - j + 2 ) ^ { \alpha + 1 } + ( k - j ) ^ { \alpha + 1 } - 2 ( k - j + 1 ) ^ { \alpha + 1 } \big ) , ~ 1 \le j \le k ,\tag{27}
$$

and

$$
a _ { k + 1 , k + 1 } = \frac { \Delta ^ { \alpha } } { \Gamma ( \alpha + 2 ) } .
$$

However, $\hat { h } ( a , t _ { k + 1 } )$ being on both sides of (26), this scheme is implicit. Thus, in a first step, we compute a pre-estimation of $\hat { h } ( a , t _ { k + 1 } )$ based on a Riemann sum that we then plug into the trapezoidal quadrature. This pre-estimation, called predictor and that we denote by $\hat { h } ^ { P } ( a , t _ { k + 1 } )$ is defined by

$$
\hat { h } ^ { P } ( a , t _ { k + 1 } ) = \frac { 1 } { \Gamma ( \alpha ) } \int _ { 0 } ^ { t } ( t - s ) ^ { \alpha - 1 } \tilde { g } ( a , s ) d s ,
$$

with

$$
\tilde { g } ( a , t ) = \hat { g } ( a , t _ { j } ) , t \in [ t _ { j } , t _ { j + 1 } ) , 0 \leq j \leq k .
$$

Therefore,

$$
\hat { h } ^ { P } ( a , t _ { k + 1 } ) = \sum _ { 0 \leq j \leq k } b _ { j , k + 1 } F \big ( a , \hat { h } ( a , t _ { j } ) \big ) ,
$$

where

$$
b _ { j , k + 1 } = \frac { \Delta ^ { \alpha } } { \Gamma ( \alpha + 1 ) } \big ( ( k - j + 1 ) ^ { \alpha } - ( k - j ) ^ { \alpha } \big ) , ~ 0 \le j \le k .
$$

Thus, the final explicit numerical scheme is given by

$$
\hat { h } ( a , t _ { k + 1 } ) = \sum _ { 0 \leq j \leq k } a _ { j , k + 1 } F \big ( a , \hat { h } ( a , t _ { j } ) \big ) + a _ { k + 1 , k + 1 } F \big ( a , \hat { h } ^ { P } ( a , t _ { j } ) \big ) , \hat { h } ( a , 0 ) = 0 ,
$$

<!-- page: 19 -->

where the weights $\boldsymbol { a } _ { j , \boldsymbol { k } + 1 }$ are defined in (27). Theoretical guarantees for the convergence of this scheme are provided in [33]. In particular, it is shown that for given $t > 0$ and $a \in \mathbb { R }$ 2

$$
\operatorname* { m a x } _ { t _ { j } \in [ 0 , t ] } | \hat { h } ( a , t _ { j } ) - h ( a , t _ { j } ) | = o ( \Delta )
$$

and

$$
\operatorname* { m a x } _ { t _ { j } \in [ \varepsilon , t ] } | \hat { h } ( a , t _ { j } ) - h ( a , t _ { j } ) | = o ( \Delta ^ { 2 - \alpha } ) ,
$$

for any $\varepsilon > 0$

## 5.2 One numerical illustration

We consider the rough Heston model (3) with the following parameters:

$$
\lambda = 2 , ~ \rho = - 0 . 5 , ~ V _ { 0 } = 0 . 4 , ~ \nu = 0 . 0 5 , ~ \theta = 0 . 0 4 .
$$

To compute $L _ { p } ( a , t )$ , we use the numerical scheme presented above to solve Riccati equation and then plug the numerical solution into (23). Once the characteristic function is obtained, classical methods are available to obtain call prices

$$
C ( K , T ) = \mathbb { E } [ S _ { T } - K ] _ { + } ,
$$

see [8, 24, 32] and the survey [41]. In our case, we use Lewis method, see [32]. Here we display the term structure of the at-the-money skew, that is the derivative of the implied volatility with respect to log-strike for at-the-money calls. We compute it for $\alpha = 1$ (classical Heston) and $\alpha = 0 . 6$ (rough Heston with Hurst parameter equal to 0.1).

![Figure 1: At-the-money skew as a function of maturity for $\alpha = 1$ and $\alpha = 0 . 6$](assets/figures/2019-el-euch-rosenbaum-rough-heston-characteristic-function-p0019-block-0012-074bc044ee3d5cab.jpg)

<!-- page: 20 -->

We see that in the rough case, the skew explodes when maturity goes to zero, whereas it remains flat in the classical Heston case. This is a remarkable feature of rough-volatility models, very important for practical applications, see [5, 16, 28].

## 6 Proofs

In the sequel, c denotes a constant that may vary from line to line.

## 6.1 Proof of Theorem 2.1

The proof of Theorem 2.1 is close to the one given in $\left[ 1 4 \right]$ for the convergence of a microscopic price model to a Heston-like dynamic. The main diference is that we have to deal here with a time-varying baseline intensity $\hat { \mu } _ { T }$ , which we have introduced to get a non-zero initial volatility in the limit. As in [14], we start by showing the C-tightness of $( \Lambda ^ { T } , X ^ { T } , Z ^ { T } )$

## 6.1.1 C-tightness of $( \Lambda ^ { T } , X ^ { T } , Z ^ { T } )$

We have the following proposition.

Proposition 6.1. Under Assumptions 2.1 and 2.2, the sequence $( \Lambda ^ { T } , X ^ { T } , Z ^ { T } )$ is C-tight and

$$
\operatorname* { s u p } _ { t \in [ 0 , 1 ] } \Vert \Lambda _ { t } ^ { T } - X _ { t } ^ { T } \Vert \underset { T \to \infty } { \longrightarrow } 0
$$

in probability. Moreover, $i f \left( X , Z \right)$ is a possible limit point o $f ( X ^ { T } , Z ^ { T } )$ , then $Z$ is a continuous martingale with $[ Z , Z ] = d i a g ( X )$

Proof:

C-tightness of $X ^ { T }$ and $\Lambda ^ { T }$ Recall that as in (8), we can write

$$
\lambda _ { t } ^ { T , + } = \lambda _ { t } ^ { T , - } = \hat { \mu } _ { T } ( t ) + \int _ { 0 } ^ { t } \psi ^ { T } ( t - s ) \hat { \mu } _ { T } ( s ) d s + \frac { 1 } { \beta + 1 } \int _ { 0 } ^ { t } \psi ^ { T } ( t - s ) \big ( d M _ { s } ^ { T , + } + \beta d M _ { s } ^ { T , - } \big ) ,
$$

where

$$
M _ { t } ^ { T } = ( M _ { t } ^ { T , + } , M _ { t } ^ { T , - } ) = N _ { t } ^ { T } - \int _ { 0 } ^ { t } \lambda _ { s } ^ { T } d s
$$

is a martingale. Using that $\int _ { 0 } ^ { . } ( f * g ) = ( \int _ { 0 } ^ { . } f ) * g .$ , we get

$$
\mathbb E [ N _ { T } ^ { T , + } ] = \mathbb E [ N _ { T } ^ { T , - } ] = \mathbb E [ \int _ { 0 } ^ { T } \lambda _ { s } ^ { T , + } d s ] = \int _ { 0 } ^ { T } \hat { \mu } _ { T } ( s ) d s + \int _ { 0 } ^ { T } \psi ^ { T } ( T - s ) \big ( \int _ { 0 } ^ { s } \hat { \mu } _ { T } ( u ) d u \big ) d s .
$$

Consequently, ˆµ being a positive function and using that

$$
1 + \int _ { 0 } ^ { \infty } \psi ^ { T } ( s ) d s = 1 + \sum _ { k \geq 1 } \int _ { 0 } ^ { \infty } ( \varphi ^ { T } ) ^ { * k } = \sum _ { k \geq 0 } ( a _ { T } ) ^ { k } = { \frac { T ^ { \alpha } } { \lambda } } ,
$$

we obtain

$$
\mathbb { E } [ N _ { T } ^ { T , + } ] \leq \int _ { 0 } ^ { T } \hat { \mu } _ { T } ( s ) d s \big ( 1 + \int _ { 0 } ^ { \infty } \psi ^ { T } ( s ) d s \big ) \leq \frac { 1 } { \lambda } T ^ { \alpha + 1 } \int _ { 0 } ^ { 1 } \hat { \mu } _ { T } ( T s ) d s .
$$

<!-- page: 21 -->

Moreover, from the definition of $\hat { \mu }$ and Remark 2.1, we have

$$
\int _ { 0 } ^ { 1 } { \hat { \mu } } _ { T } ( T s ) d s = \mu T ^ { \alpha - 1 } { \big ( } 1 + \xi \int _ { 0 } ^ { 1 } s ^ { - \alpha } { \frac { ( s T ) ^ { \alpha } } { \lambda } } \int _ { s T } ^ { \infty } \varphi ( u ) d u d s + \lambda T ^ { - \alpha } \int _ { 0 } ^ { 1 } \int _ { 0 } ^ { s T } \varphi ( u ) d u d s { \big ) } \leq c T ^ { \alpha - 1 } .
$$

Hence $\mathbb { E } [ N _ { T } ^ { T , + } ] \le c T ^ { 2 \alpha }$ and therefore

$$
\mathbb { E } [ X _ { 1 } ^ { T } ] = \mathbb { E } [ \Lambda _ { 1 } ^ { T } ] \leq c ,
$$

for each component. Each component of $X ^ { T }$ and $\Lambda ^ { T }$ being increasing, we deduce the tightness of each component of $( X ^ { T } , \Lambda ^ { T } )$ . Furthermore, the maximum jump size of $X ^ { T }$ and $\Lambda ^ { \hat { T } }$ being $\frac { 1 - a _ { T } } { T ^ { \alpha } \mu }$ which goes to zero, the C-tightness of $( X ^ { T } , \Lambda ^ { T } )$ is obtained from Prop.VI-3.26 in [25].

C-tightness of $Z ^ { T }$ It is easy to check that

$$
\langle Z ^ { T } , Z ^ { T } \rangle = d i a g ( \Lambda ^ { T } ) ,
$$

which is C-tight. From Theorem VI-4.13 in [25], this gives the tightness of $Z ^ { T }$ . The maximum jump size of Z<sup>T</sup> vanishing as $Z ^ { T }$ $T$ goes to infinity, we obtain that Z<sup>T</sup> is C-tight. $Z ^ { T }$

Convergence of $X ^ { T } - \Lambda ^ { T }$ We have

$$
X _ { t } ^ { T } - \Lambda _ { t } ^ { T } = \frac { 1 - a _ { T } } { T ^ { \alpha } \mu } M _ { t T } ^ { T } .
$$

From Doob’s inequality, we get that for each component

$$
\mathbb { E } \big [ \operatorname* { s u p } _ { t \in [ 0 , 1 ] } | \Lambda _ { t } ^ { T } - X _ { t } ^ { T } | ^ { 2 } \big ] \leq c T ^ { - 4 \alpha } \mathbb { E } [ M _ { T } ^ { T } ] ^ { 2 } .
$$

Since $[ M ^ { T } , M ^ { T } ] = N ^ { T }$ , we deduce

$$
\mathbb { E } \big [ \operatorname* { s u p } _ { t \in [ 0 , 1 ] } | \Lambda _ { t } ^ { T } - X _ { t } ^ { T } | ^ { 2 } \big ] \leq c T ^ { - 4 \alpha } \mathbb { E } [ N _ { T } ^ { T } ] \leq c T ^ { - 2 \alpha } .
$$

This gives the uniform convergence to zero in probability of $X ^ { T } - \Lambda ^ { T }$

Limit of $Z ^ { T }$ Let $( X , Z )$ be a limit point of $( X ^ { T } , Z ^ { T } )$ . We know that $( X , Z )$ is continuous and from Corollary IX-1.19 in [25], Z is a local martingale. Moreover, since

$$
[ Z ^ { T } , Z ^ { T } ] = d i a g ( X ^ { T } ) ,
$$

using Theorem VI-6.26 in [25], we get that $[ Z , Z ]$ is the limit of $[ Z ^ { T } , Z ^ { T } ]$ and $[ Z , Z ] = d i a g ( X )$ By Fatou’s lemma, the expectation of $[ Z , Z ]$ is finite and therefore Z is a martingale. □

<!-- page: 22 -->

## 6.1.2 Convergence of $X ^ { T }$ and $Z ^ { T }$

First remark that since

$$
\operatorname* { s u p } _ { t \in [ 0 , 1 ] } | \Lambda _ { t } ^ { T } - X _ { t } ^ { T } | \xrightarrow [ T \to \infty ] { } 0
$$

and

$$
\Lambda _ { t } ^ { T , + } = \Lambda _ { t } ^ { T , - } ,
$$

we get

$$
\operatorname* { s u p } _ { t \in [ 0 , 1 ] } | X _ { t } ^ { T , + } - X _ { t } ^ { T , - } | \xrightarrow [ T  \infty ] { } 0 .
$$

Therefore, if a subsequence of $X _ { t } ^ { T , + }$ converges to some $X$ , then the associated subsequence of $X _ { t } ^ { T , - }$ converges to the same $X$ . We have the following proposition for the limit points of $X _ { t } ^ { T , + }$ and $X _ { t } ^ { T , - }$

Proposition 6.2. If $( X , X , Z ^ { + } , Z ^ { - } )$ is a possible limit point for $( X ^ { T , + } , X ^ { T , - } , Z ^ { T , + } , Z ^ { T , - } )$ then $( X _ { t } , Z _ { t } ^ { + } , Z _ { t } ^ { - } )$ can be written

$$
X _ { t } = \int _ { 0 } ^ { t } Y _ { s } d s , Z _ { t } ^ { + } = \int _ { 0 } ^ { t } \sqrt { Y _ { s } } d B _ { s } ^ { 1 } , Z _ { t } ^ { - } = \int _ { 0 } ^ { t } \sqrt { Y _ { s } } d B _ { s } ^ { 2 } ,
$$

where $( B _ { 1 } , B _ { 2 } )$ is a bi-dimensional Brownian motion and Y is solution of

$$
Y _ { t } = \xi { \left( 1 - F ^ { \alpha , \lambda } ( t ) \right) } + F ^ { \alpha , \lambda } ( t ) + { \sqrt { \frac { 1 + \beta ^ { 2 } } { \lambda \mu ( 1 + \beta ) ^ { 2 } } } } \int _ { 0 } ^ { t } f ^ { \alpha , \lambda } ( t - s ) { \sqrt { Y _ { s } } } d B _ { s } ,\tag{28}
$$

with

$$
B = \frac { B ^ { 1 } + \beta B ^ { 2 } } { \sqrt { 1 + \beta ^ { 2 } } } .
$$

Furthermore, for any $\varepsilon > 0$ , Y has H¨older regularity $\alpha - 1 / 2 - \varepsilon$

Proof:

First recall that $\begin{array} { r } { \lambda _ { t } ^ { T , + } = \lambda _ { t } ^ { T , } } \end{array}$ and note that using similar computations as in Section 2.2, we can write

$$
\lambda _ { t } ^ { T , + } = \mu _ { T } + \mu _ { T } \int _ { 0 } ^ { t } \psi ^ { T } ( t - s ) d s + \xi \mu _ { T } \big ( \frac { 1 } { 1 - a _ { T } } - \int _ { 0 } ^ { t } \psi ^ { T } ( t - s ) d s \big ) + \frac { 1 } { \beta + 1 } \int _ { 0 } ^ { t } \psi ^ { T } ( t - s ) \big ( d M _ { s } ^ { T , + } + \beta d M _ { s } ^ { T , - } \big ) .
$$

Then using Fubini theorem together with the fact that $\int _ { 0 } ^ { . } ( f * g ) = ( \int _ { 0 } ^ { . } f ) * g \ d g$ , we get

$$
\begin{array} { l } { \displaystyle \int _ { 0 } ^ { t } \lambda _ { s } ^ { T , + } d s = \mu _ { T } t + \mu _ { T } \int _ { 0 } ^ { t } \psi ^ { T } ( t - s ) s d s + \xi \mu _ { T } \big ( \frac { t } { 1 - a _ { T } } - \int _ { 0 } ^ { t } \psi ^ { T } ( t - s ) s d s \big ) } \\ { + \displaystyle \frac { 1 } { \beta + 1 } \int _ { 0 } ^ { t } \psi ^ { T } ( t - s ) ( M _ { s } ^ { T , + } + \beta M _ { s } ^ { T , - } ) d s . } \end{array}
$$

Therefore, for $t \in [ 0 , 1 ]$ , we have the decomposition

$$
\Lambda _ { t } ^ { T , + } = \Lambda _ { t } ^ { T , - } = T _ { 1 } + T _ { 2 } + T _ { 3 } ,\tag{29}
$$

<!-- page: 23 -->

with

$$
\begin{array} { c } { { T _ { 1 } = ( 1 - a _ { T } ) t , } } \\ { { { } } } \\ { { T _ { 2 } = T ( 1 - a _ { T } ) \displaystyle \int _ { 0 } ^ { t } \psi ^ { T } \big ( T ( t - s ) \big ) s d s + \xi \big ( t - T ( 1 - a _ { T } ) \int _ { 0 } ^ { t } \psi ^ { T } \big ( T ( t - s ) \big ) s d s \big ) , } } \\ { { T _ { 3 } = \displaystyle \frac { 1 } { \sqrt { \lambda \mu ( 1 + \beta ) ^ { 2 } } } \displaystyle \int _ { 0 } ^ { t } T ( 1 - a _ { T } ) \psi ^ { T } \big ( T ( t - s ) \big ) ( Z _ { s } ^ { T , + } + \beta Z _ { s } ^ { T , - } ) d s . } } \end{array}
$$

Now recall that we have shown in (9) that

$$
T ( 1 - a _ { T } ) \psi ( T . ) = a _ { T } f ^ { \alpha , \lambda } .
$$

Thus

$$
T _ { 2 } \underset { T  \infty } { \longrightarrow } \int _ { 0 } ^ { t } f ^ { \alpha , \lambda } ( t - s ) s d s + \xi \big ( t - \int _ { 0 } ^ { t } f ^ { \alpha , \lambda } ( t - s ) s d s \big )
$$

and

$$
T _ { 3 } \underset { T  \infty } { \longrightarrow } \frac { 1 } { \sqrt { \lambda \mu ( 1 + \beta ) ^ { 2 } } } \int _ { 0 } ^ { t } f ^ { \alpha , \lambda } ( t - s ) ( Z _ { s } ^ { + } + \beta Z _ { s } ^ { - } ) d s .
$$

Therefore, letting T go to infinity in (29), we obtain using Proposition 6.1 that X satisfies

$$
X _ { t } = \int _ { 0 } ^ { t } f ^ { \alpha , \lambda } ( t - s ) s d s + \xi \big ( t - \int _ { 0 } ^ { t } f ^ { \alpha , \lambda } ( t - s ) s d s \big ) + \frac { 1 } { \sqrt { \lambda \mu ( 1 + \beta ) ^ { 2 } } } \int _ { 0 } ^ { t } f ^ { \alpha , \lambda } ( t - s ) ( Z _ { s } ^ { + } + \beta Z _ { s } ^ { - } ) d s .
$$

In the same way as for the proof of Theorem 3.2 in [28], we show that

$$
X _ { t } = \int _ { 0 } ^ { t } Y _ { s } d s ,
$$

where Y satisfies

$$
Y _ { t } = F ^ { \alpha , \lambda } ( t ) + \xi \big ( 1 - F ^ { \alpha , \lambda } ( t ) \big ) + \frac { 1 } { \sqrt { \lambda \mu ( 1 + \beta ) ^ { 2 } } } \int _ { 0 } ^ { t } f ^ { \alpha , \lambda } ( t - s ) ( d Z _ { s } ^ { + } + \beta d Z _ { s } ^ { - } ) .
$$

Since, by Proposition 6.1,

$$
[ Z , Z ] = \int _ { 0 } ^ { t } Y _ { s } d s \left( \begin{array} { c c } { { 1 } } & { { 0 } } \\ { { 0 } } & { { 1 } } \end{array} \right) ,
$$

we can apply Theorem V-3.9 in [39] to show the existence of a bi-dimensional Brownian motion $( B ^ { 1 } , B ^ { 2 } )$ such that

$$
Z _ { t } ^ { + } = \int _ { 0 } ^ { t } \sqrt { Y _ { s } } d B _ { s } ^ { 1 } , Z _ { t } ^ { - } = \int _ { 0 } ^ { t } \sqrt { Y _ { s } } d B _ { s } ^ { 2 } .
$$

Finally, we define the following Brownian motion:

$$
B = \frac { B ^ { 1 } + \beta B ^ { 2 } } { \sqrt { 1 + \beta ^ { 2 } } } .
$$

Then, in the same way as for the proof of Theorem 3.2 in [28], we get that Y satisfies

$$
Y _ { t } = F ^ { \alpha , \lambda } ( t ) + \xi { \left( 1 - F ^ { \alpha , \lambda } ( t ) \right) } + \sqrt { \frac { 1 + \beta ^ { 2 } } { \lambda \mu ( 1 + \beta ) ^ { 2 } } } \int _ { 0 } ^ { t } f ^ { \alpha , \lambda } ( t - s ) \sqrt { Y _ { s } } d B _ { s } ,
$$

and has H¨older regularity $\alpha - 1 / 2 - \varepsilon$ for any $\varepsilon > 0$

<!-- page: 24 -->

## 6.1.3 End of the proof of Theorem 2.1

We now recall the following proposition stating that the process Y is uniquely defined by Equation (28) and that this equation is equivalent to that given in Theorem 2.1. The proof of this result can be found in [14]. Theorem 2.1 is readily obtained from this proposition together with Proposition 6.1 and 6.2.

Proposition 6.3. Let $\lambda , \nu , \theta$ and V<sub>0</sub> be positive constants, $\alpha \in ( 1 / 2 , 1 )$ and B be a Brownian motion. The process V is solution of the following fractional stochastic diferential equation

$$
V _ { t } = V _ { 0 } \big ( 1 - F ^ { \alpha , \lambda } ( t ) \big ) + \theta F ^ { \alpha , \lambda } ( t ) + \nu \int _ { 0 } ^ { t } f ^ { \alpha , \lambda } ( t - s ) \sqrt { V _ { s } } d B _ { s }
$$

if and only if it is solution of

$$
V _ { t } = V _ { 0 } + \frac { 1 } { \Gamma ( \alpha ) } \int _ { 0 } ^ { t } ( t - s ) ^ { \alpha - 1 } \lambda ( \theta - V _ { s } ) d s + \frac { \lambda \nu } { \Gamma ( \alpha ) } \int _ { 0 } ^ { t } ( t - s ) ^ { \alpha - 1 } \sqrt { V _ { s } } d B _ { s } .
$$

Furthermore, both equations admit a unique strong solution.

## 6.1.4 Proof of Corollary 2.1

From Theorem 2.1, we know that $P ^ { T }$ converges in law for the Skorokhod topology to the process P given by

$$
P _ { t } = \sqrt { \frac { \theta } { 2 } } \int _ { 0 } ^ { t } \sqrt { Y _ { s } } ( d B _ { s } ^ { 1 } - d B _ { s } ^ { 2 } ) - \frac { \theta } { 2 } \int _ { 0 } ^ { t } Y _ { s } d s .
$$

Let $V _ { t } = \theta Y _ { t }$ and $\begin{array} { r } { W _ { t } = \frac { 1 } { \sqrt { 2 } } ( B _ { t } ^ { 1 } - B _ { t } ^ { 2 } ) } \end{array}$ . Then

$$
P _ { t } = \int _ { 0 } ^ { t } \sqrt { V _ { s } } d W _ { s } - \frac { 1 } { 2 } \int _ { 0 } ^ { t } V _ { s } d s ,
$$

where

$$
V _ { t } = \xi \theta + \frac { 1 } { \Gamma ( \alpha ) } \int _ { 0 } ^ { t } ( t - s ) ^ { \alpha - 1 } \lambda ( \theta - V _ { s } ) d s + \lambda \sqrt { \frac { \theta ( 1 + \beta ^ { 2 } ) } { \lambda \mu ( 1 + \beta ) ^ { 2 } } } \frac { 1 } { \Gamma ( \alpha ) } \int _ { 0 } ^ { t } ( t - s ) ^ { \alpha - 1 } \sqrt { V _ { s } } d W _ { s } ^ { \prime }
$$

and (W, B) is a correlated bi-dimensional Brownian motion with

$$
d \langle W , B \rangle _ { t } = \frac { 1 - \beta } { \sqrt { 2 ( 1 + \beta ^ { 2 } ) } } d t .
$$

## 6.2 Proof of Theorem 4.1

We now give the proof of Theorem 4.1. We do it for $t \in [ 0 , 1 ]$ but the proof can obviously be extended for any $t \geq 0$ . We start by controlling the process $Y ^ { T } ( a , t ) - ( 1 , 1 )$ . In the sequel, $c ( a )$ denotes a positive constant independent of t and $T$ that may vary from line to line.

<!-- page: 25 -->

## 6.2.1 Control of $Y ^ { T } ( a , t ) - ( 1 , 1 )$

We have the following proposition.

Proposition 6.4. For any $t \in [ 0 , 1 ]$

$$
\begin{array} { r } { T ^ { \alpha } \| Y ^ { T } ( a , t ) - ( 1 , 1 ) \| \leq c ( a ) . } \end{array}
$$

Proof:

Let us show that

$$
\begin{array} { r } { T ^ { \alpha } | Y ^ { T , + } ( a , t ) - 1 | \leq c ( a ) . } \end{array}
$$

Recall that $Y ^ { T } ( a , t )$ is defined in Section 4.1 for $a \in \mathbb { R }$ by

$$
\begin{array} { r } { Y ^ { T } ( a , t ) = \big ( Y ^ { T , + } ( a , t ) , Y ^ { T , - } ( a , t ) \big ) = \big ( C ^ { T , + } ( ( a _ { T } ^ { + } , a _ { T } ^ { - } ) , t T ) , C ^ { T , - } ( ( a _ { T } ^ { + } , a _ { T } ^ { - } ) , t T ) \big ) , } \end{array}
$$

with

$$
a _ { T } ^ { + } = a \sqrt { \frac { \lambda \theta } { 2 \mu } } T ^ { - \alpha } - a \frac { \lambda \theta } { 2 \mu } T ^ { - 2 \alpha } , ~ a _ { T } ^ { - } = - a \sqrt { \frac { \lambda \theta } { 2 \mu } } T ^ { - \alpha } .
$$

Using the elements in the proof of Theorem 3.1 in Section 3.3, we get that

$$
C ^ { T , + } \bigl ( ( a , b ) , t \bigr ) = \mathbb { E } \bigl [ \exp ( i a + i a \tilde { N } _ { t } ^ { T , + } + i b \tilde { N } _ { t } ^ { T , - } ) \bigr ] ,
$$

where $\tilde { N } ^ { T , - } = ( \tilde { N } ^ { T , + } , \tilde { N } ^ { T , - } )$ is a bi-dimensional Hawkes process with intensity $( \tilde { \lambda } ^ { T } , \tilde { \lambda } ^ { T } )$ given by

$$
\tilde { \lambda } _ { t } ^ { T } = \frac { 1 } { \beta + 1 } \varphi ^ { T } ( t ) + \frac { 1 } { \beta + 1 } \int _ { 0 } ^ { t } \varphi ^ { T } ( t - s ) ( d \tilde { N } _ { s } ^ { T , + } + \beta d \tilde { N } _ { s } ^ { T , - } ) .
$$

As already seen, using Lemma A.1, we can rewrite the intensity under the following form:

$$
\tilde { \lambda } _ { t } ^ { T } = \frac { 1 } { \beta + 1 } \boldsymbol { \psi } ^ { T } ( t ) + \frac { 1 } { \beta + 1 } \int _ { 0 } ^ { t } \boldsymbol { \psi } ^ { T } ( t - s ) ( d \tilde { M } _ { s } ^ { T , + } + \beta d \tilde { M } _ { s } ^ { T , - } ) ,
$$

where $\tilde { M } ^ { T } = ( \tilde { M } ^ { T , + } , \tilde { M } ^ { T , - } ) = \tilde { N } ^ { T } - \int _ { 0 } ^ { \cdot } \tilde { \lambda } ^ { T } ( s ) d s ( 1 , 1 )$ is a martingale. Using Fubini theorem, we get

$$
\int _ { 0 } ^ { t T } \tilde { \lambda } _ { s } ^ { T } d s = \frac { 1 } { \beta + 1 } T \int _ { 0 } ^ { t } \psi ^ { T } ( T s ) d s + \frac { 1 } { \beta + 1 } \int _ { 0 } ^ { t } T \psi ^ { T } \big ( T ( t - s ) \big ) \big ( \tilde { M } _ { s T } ^ { T , + } + \beta \tilde { M } _ { s T } ^ { T , - } \big ) d s .
$$

Then, from (9), we derive

$$
\int _ { 0 } ^ { t T } \tilde { \lambda } _ { s } ^ { T } d s = \frac { 1 } { \lambda ( \beta + 1 ) } a _ { T } T ^ { \alpha } F ^ { \alpha , \lambda } ( t ) + \frac { 1 } { \lambda ( \beta + 1 ) } a _ { T } T ^ { \alpha } \int _ { 0 } ^ { t } f ^ { \alpha , \lambda } ( t - s ) ( \tilde { M } _ { s T } ^ { T , + } + \beta \tilde { M } _ { s T } ^ { T , - } ) d s .\tag{30}
$$

Consequently,

$$
\mathbb { E } \big [ \int _ { 0 } ^ { t T } \tilde { \lambda } _ { s } ^ { T } d s \big ] \leq \frac { 1 } { \lambda ( \beta + 1 ) } F ^ { \alpha , \lambda } ( 1 ) T ^ { \alpha } .
$$

Let us now set $\tilde { X } _ { t } ^ { T } = a _ { T } ^ { + } \tilde { N } _ { t T } ^ { T , + } + a _ { T } ^ { - } \tilde { N } _ { t T } ^ { T , + }$ <sup>−</sup>. Using the last inequality, we deduce

$$
| \mathbb { E } \tilde { X } _ { t } ^ { T } | \leq c | a | T ^ { - \alpha } F ^ { \alpha , \lambda } ( 1 ) .
$$

<!-- page: 26 -->

Now recall that

$$
T ^ { \alpha } ( Y ^ { T , + } ( a , t ) - 1 ) = T ^ { \alpha } \big ( \mathbb { E } \big [ \exp ( i a _ { T } ^ { + } + i a _ { T } ^ { + } \tilde { N } _ { t T } ^ { T , + } + i a _ { T } ^ { - } \tilde { N } _ { t T } ^ { T , - } ) \big ] - 1 \big ) .
$$

Using the fact that there exists $c > 0$ such that for any $x \in \mathbb { R }$ 2

$$
| \exp ( i x ) - 1 - i x | \leq c | x | ^ { 2 } ,
$$

we obtain

$$
\begin{array} { r l } & { T ^ { \alpha } | Y ^ { T , + } ( a , t ) - 1 | = T ^ { \alpha } \big | \mathbb { E } \big [ \exp ( i a _ { T } ^ { + } + i \tilde { X } _ { t } ^ { T } ) - 1 - i \tilde { X } _ { t } ^ { T } - i a _ { T } ^ { + } + i \tilde { X } _ { t } ^ { T } + i a _ { T } ^ { + } \big ] \big | } \\ & { \qquad \leq T ^ { \alpha } \big | \mathbb { E } [ \tilde { X } _ { t } ^ { T } ] \big | + T ^ { \alpha } | a _ { T } ^ { + } \big | + T ^ { \alpha } \mathbb { E } \big [ | \exp ( i a _ { T } ^ { + } + i \tilde { X } _ { t } ^ { T } ) - 1 - i \tilde { X } _ { t } ^ { T } - i a _ { T } ^ { + } | \big ] } \\ & { \qquad \leq c ( a ) \big ( 1 + T ^ { \alpha } ( a _ { T } ^ { + } ) ^ { 2 } + T ^ { \alpha } \mathbb { E } [ ( \tilde { X } _ { t } ^ { T } ) ^ { 2 } ] \big ) } \\ & { \qquad \leq c ( a ) \big ( 1 + T ^ { \alpha } \mathbb { E } [ ( \tilde { X } _ { t } ^ { T } ) ^ { 2 } ] \big ) . } \end{array}
$$

Then, using that

$$
\tilde { X } _ { t } ^ { T } = a \sqrt { \frac { \lambda \theta } { 2 \mu } } T ^ { - \alpha } ( \tilde { N } _ { t T } ^ { T , + } - \tilde { N } _ { t T } ^ { T , - } ) - a \frac { \lambda \theta } { 2 \mu } T ^ { - 2 \alpha } \tilde { N } _ { t T } ^ { T , + }
$$

together with the fact that $\tilde { N } ^ { T , + } - \tilde { N } ^ { T , - } = \tilde { M } ^ { T , + } - \tilde { M } ^ { T , }$ <sup>−</sup>, we deduce

$$
T ^ { \alpha } \mathbb { E } [ ( \tilde { X } _ { t } ^ { T } ) ^ { 2 } ] \leq c a ^ { 2 } T ^ { - \alpha } \mathbb { E } [ ( \tilde { M } _ { t T } ^ { T , + } - \tilde { M } _ { t T } ^ { T , - } ) ^ { 2 } ] + c a ^ { 2 } T ^ { - 3 \alpha } \mathbb { E } [ ( \tilde { N } _ { t T } ^ { T , + } ) ^ { 2 } ] .
$$

Since $[ \tilde { M } ^ { T , + } - \tilde { M } ^ { T , - } , \tilde { M } ^ { T , + } - \tilde { M } ^ { T , - } ] = \tilde { N } ^ { T , + } + \tilde { N } ^ { T , - }$ , we get

$$
\begin{array} { r l } & { T ^ { \alpha } \mathbb { E } [ ( \tilde { X } _ { t } ^ { T } ) ^ { 2 } ] \leq c a ^ { 2 } T ^ { - \alpha } \mathbb { E } [ \tilde { N } _ { t T } ^ { T , + } + \tilde { N } _ { t T } ^ { T , - } ] + c a ^ { 2 } T ^ { - 3 \alpha } \mathbb { E } [ ( \tilde { N } _ { t T } ^ { T , + } ) ^ { 2 } ] } \\ & { \qquad \leq c a ^ { 2 } \big ( T ^ { - \alpha } \mathbb { E } [ \displaystyle \int _ { 0 } ^ { t T } \tilde { \lambda } _ { s } ^ { T } d s ] + T ^ { - 3 \alpha } \mathbb { E } [ ( \tilde { N } _ { t T } ^ { T , + } ) ^ { 2 } ] \big ) . } \\ & { \qquad \leq c a ^ { 2 } \big ( 1 + T ^ { - 3 \alpha } \mathbb { E } [ ( \tilde { N } _ { t T } ^ { T , + } ) ^ { 2 } ] \big ) . } \end{array}
$$

In order to control the term $\mathbb { E } [ ( \tilde { N } _ { t T } ^ { T , + } ) ^ { 2 } ]$ , we now compute a bound for $\mathbb { E } \big [ ( \int _ { 0 } ^ { t T } \tilde { \lambda } _ { s } ^ { T } d s ) ^ { 2 } \big ]$ . Using (30), this last quantity is equal to

$$
\frac { 1 } { \lambda ^ { 2 } ( \beta + 1 ) ^ { 2 } } a _ { T } ^ { 2 } T ^ { 2 \alpha } \big ( F ^ { \alpha , \lambda } ( t ) \big ) ^ { 2 } + \frac { 1 } { \lambda ^ { 2 } ( \beta + 1 ) ^ { 2 } } a _ { T } ^ { 2 } T ^ { 2 \alpha } \mathbb { E } \Big [ \Big ( \int _ { 0 } ^ { t } f ^ { \alpha , \lambda } ( t - s ) ( \tilde { M } _ { s T } ^ { T , + } + \beta \tilde { M } _ { s T } ^ { T , - } ) d s \Big ) ^ { 2 } \Big ] ,
$$

which is smaller than

$$
c ( a ) T ^ { 2 \alpha } \Big ( 1 + \mathbb { E } \big [ \int _ { 0 } ^ { t } \big ( f ^ { \alpha , \lambda } ( t - s ) \big ) ^ { 2 } ( \tilde { M } _ { s T } ^ { T , + } + \beta \tilde { M } _ { s T } ^ { T , - } ) ^ { 2 } d s \big ] \Big ) .
$$

Since $[ \tilde { M } ^ { T , + } + \beta \tilde { M } ^ { T , - } , \tilde { M } ^ { T , + } + \beta \tilde { M } ^ { T , - } ] = \tilde { N } ^ { T , + } + \beta ^ { 2 } \tilde { N } ^ { T , }$ <sup>−</sup>, we obtain

$$
\begin{array} { r l } & { \mathbb { E } \big [ ( \int _ { 0 } ^ { t T } \tilde { \lambda } _ { s } ^ { T } d s ) ^ { 2 } \big ] \leq c ( a ) T ^ { 2 \alpha } \Big ( 1 + \displaystyle \int _ { 0 } ^ { t } \big ( f ^ { \alpha , \lambda } ( t - s ) \big ) ^ { 2 } \mathbb { E } [ \tilde { N } _ { s } ^ { T , + } + \beta ^ { 2 } \tilde { N } _ { s T } ^ { T , - } ] d s \Big ) } \\ & { \qquad \leq c ( a ) T ^ { 2 \alpha } \Big ( 1 + \displaystyle \int _ { 0 } ^ { t } \big ( f ^ { \alpha , \lambda } ( t - s ) \big ) ^ { 2 } \mathbb { E } \big [ \int _ { 0 } ^ { s T } \tilde { \lambda } _ { u } ^ { T } d u \big ] d s \Big ) } \\ & { \qquad \leq c ( a ) T ^ { 2 \alpha } \Big ( 1 + T ^ { \alpha } \displaystyle \int _ { 0 } ^ { 1 } \big ( f ^ { \alpha , \lambda } ( s ) \big ) ^ { 2 } d s \Big ) } \\ & { \qquad \leq c ( a ) T ^ { 3 \alpha } . } \end{array}
$$

<!-- page: 27 -->

Thus

$$
\mathbb { E } \big [ ( \tilde { N } _ { t T } ^ { T , + } ) ^ { 2 } \big ] \leq 2 \mathbb { E } \big [ ( \tilde { M } _ { t T } ^ { T , + } ) ^ { 2 } \big ] + 2 \mathbb { E } \big [ \big ( \int _ { 0 } ^ { t T } \tilde { \lambda } _ { s } ^ { T } d s \big ) ^ { 2 } \big ] \leq c ( a ) T ^ { 3 \alpha } .
$$

Finally, $T ^ { \alpha } \mathbb { E } [ ( \tilde { X } _ { t } ^ { T } ) ^ { 2 } ] \leq c ( a )$ and therefore

$$
\begin{array} { r } { T ^ { \alpha } | Y ^ { T , + } ( a , t ) - 1 | \leq c ( a ) . } \end{array}
$$

The fact that

$$
{ \cal T } ^ { \alpha } | { \cal Y } ^ { T , - } ( a , t ) - 1 | \leq c ( a )
$$

is proved similarly.

## 6.2.2 Convergence of $T ^ { \alpha } ( Y ^ { T } - ( 1 , 1 ) )$

Let $\kappa = \lambda \theta / ( 2 \mu )$ . We have the following proposition.

Proposition 6.5. The sequence $T ^ { \alpha } ( Y ^ { T } ( a , t ) - ( 1 , 1 ) )$ converges uniformly in $t \in [ 0 , 1 ]$ to $\left( c ( a , t ) , d ( a , t ) \right)$ , where $( c , d )$ are solutions of

$$
\begin{array} { c } { { c ( a , t ) = i a \sqrt { \kappa } - i a \displaystyle \frac { \kappa } { \lambda ( \beta + 1 ) } F ^ { \alpha , \lambda } ( t ) + \displaystyle \frac { 1 } { 2 \lambda ( \beta + 1 ) } \int _ { 0 } ^ { t } \left( c ^ { 2 } ( a , t - s ) + d ^ { 2 } ( a , t - s ) \right) f ^ { \alpha , \lambda } ( s ) d s } } \\ { { { } } } \\ { { d ( a , t ) = - i a \sqrt { \kappa } - i a \displaystyle \frac { \beta \kappa } { \lambda ( \beta + 1 ) } F ^ { \alpha , \lambda } ( t ) + \displaystyle \frac { \beta } { 2 \lambda ( \beta + 1 ) } \int _ { 0 } ^ { t } \left( c ^ { 2 } ( a , t - s ) + d ^ { 2 } ( a , t - s ) \right) f ^ { \alpha , \lambda } ( s ) d s . } } \end{array}
$$

Proof:

Convenient rewriting of $T ^ { \alpha } ( Y ^ { T } - ( 1 , 1 ) )$ Using the fact that the complex logarithm is analytic on the set $\mathbb { C } / \mathbb { R } ^ { - }$ , we can show that there exists $c > 0$ such that for any $x \in \mathbb { C }$ with $| x | < 1 / 2$

$$
| \log ( 1 + x ) - x + \frac { 1 } { 2 } x ^ { 2 } | \leq c | x | ^ { 3 } .
$$

Thus we can write

$$
\log \left( Y ^ { T } ( a , t ) \right) = Y ^ { T } ( a , t ) - ( 1 , 1 ) - \frac { 1 } { 2 } \big ( Y ^ { T } ( a , t ) - ( 1 , 1 ) \big ) ^ { 2 } - \varepsilon ^ { T } ( a , t ) ,
$$

with $| \varepsilon ^ { T } ( a , t ) | \leq c ( a ) T ^ { - 3 \alpha }$ . Indeed, for large enough $T _ { \ast }$ , we have from Proposition 6.4 that $| Y ^ { T , + } ( a , t ) - 1 | \leq 1 / 2$ and $| Y ^ { T , - } ( a , t ) - 1 | \leq 1 / 2$ , uniformly in t. Now, again from Proposition 6.4, it is easy to see that

$$
\left\| i ( a _ { T } ^ { + } , a _ { T } ^ { - } ) + \int _ { 0 } ^ { t } T \bigl ( Y ^ { T } ( a , t - s ) - ( 1 , 1 ) \bigr ) . \phi ^ { T } ( T s ) d s \right\| \leq c ( a ) T ^ { - \alpha } \underset { T \to \infty } { \longrightarrow } 0 .
$$

Hence, for large enough $T$ , the imaginary part of

$$
i ( a _ { T } ^ { + } , a _ { T } ^ { - } ) + \int _ { 0 } ^ { t } T ( Y ^ { T } ( a , t - s ) - ( 1 , 1 ) ) . \phi ^ { T } ( T s ) d s
$$

has a norm which is smaller than π. Therefore

$$
\log \Big ( \exp \big ( i ( a _ { T } ^ { + } , a _ { T } ^ { - } ) + \int _ { 0 } ^ { t } T \big ( Y ^ { T } ( a , t - s ) - ( 1 , 1 ) \big ) . \phi ^ { T } ( T s ) d s \big ) \Big )
$$

<!-- page: 28 -->

is equal to

$$
i ( a _ { T } ^ { + } , a _ { T } ^ { - } ) + \int _ { 0 } ^ { t } T \bigl ( Y ^ { T } ( a , t - s ) - ( 1 , 1 ) \bigr ) . \phi ^ { T } ( T s ) d s .
$$

Then, using Equation (19), we get

$$
\begin{array} { c } { { \displaystyle Y ^ { T } ( a , t ) - ( 1 , 1 ) = \frac { 1 } { 2 } \big ( Y ^ { T } ( a , t ) - ( 1 , 1 ) \big ) ^ { 2 } + \varepsilon ^ { T } ( a , t ) + i a \sqrt { \kappa } T ^ { - \alpha } ( 1 , - 1 ) } } \\ { { \displaystyle - i a \kappa T ^ { - 2 \alpha } ( 1 , 0 ) + T \int _ { 0 } ^ { t } \big ( Y ^ { T } ( a , t - s ) - ( 1 , 1 ) \big ) . \phi ^ { T } ( T s ) d s . } } \end{array}
$$

Using again the fact that

$$
\sum _ { k \geq 1 } \left( T \phi ^ { T } ( T . ) \right) ^ { * k } = a _ { T } { \frac { T ^ { \alpha } } { \lambda } } f ^ { \alpha , \lambda } \chi ,
$$

together with Lemma A.1, we derive

$$
\begin{array} { l } { { \displaystyle Y ^ { T } ( a , t ) - ( 1 , 1 ) = \frac { 1 } { 2 } \big ( Y ^ { T } ( a , t ) - ( 1 , 1 ) \big ) ^ { 2 } + \varepsilon ^ { T } ( a , t ) + i a \sqrt \kappa T ^ { - \alpha } ( 1 , - 1 ) - i a \kappa T ^ { - 2 \alpha } ( 1 , 0 ) } \ ~ } \\ { { \displaystyle ~ + \frac { a \gamma } { 2 } \frac { T ^ { \alpha } } { \lambda } \int _ { 0 } ^ { t } \big ( Y ^ { T } ( a , t - s ) - ( 1 , 1 ) \big ) ^ { 2 } \chi f ^ { \alpha , \lambda } ( s ) d s + \frac { a \gamma } { \lambda } T ^ { \alpha } \int _ { 0 } ^ { t } \varepsilon ^ { T } ( a , t - s ) \cdot \chi f ^ { \alpha , \lambda } ( s ) d s } \ ~ } \\ { { \displaystyle ~ + i a \sqrt \kappa \frac { a \gamma } { \lambda } ( 1 , - 1 ) \cdot \chi F ^ { \alpha , \lambda } ( t ) - i a \kappa T ^ { - \alpha } \frac { a \gamma } { \lambda } ( 1 , 0 ) \cdot \chi F ^ { \alpha , \lambda } ( t ) } . } \end{array}
$$

Let

$$
\varepsilon _ { 1 } ^ { T } ( a , t ) = \frac { 1 } { 2 } \big ( Y ^ { T } ( a , t ) - ( 1 , 1 ) \big ) ^ { 2 } + \varepsilon ^ { T } ( a , t ) - i a \kappa T ^ { - 2 \alpha } ( 1 , 0 ) + \frac { a _ { T } } { \lambda } T ^ { \alpha } \int _ { 0 } ^ { t } \varepsilon ^ { T } ( a , t - s ) . \chi f ^ { \alpha , \lambda } ( s ) d s .
$$

We have

$$
\begin{array} { c } { { Y ^ { T } ( a , t ) - ( 1 , 1 ) = \varepsilon _ { 1 } ^ { T } ( a , t ) + i a \sqrt { \kappa } T ^ { - \alpha } ( 1 , - 1 ) + \displaystyle \frac { a _ { T } } { 2 } \displaystyle \frac { T ^ { \alpha } } { \lambda } \int _ { 0 } ^ { t } \left( Y ^ { T } ( a , t - s ) - ( 1 , 1 ) \right) ^ { 2 } \cdot \chi f ^ { \alpha , \lambda } ( s ) d s } } \\ { { - i a _ { T } a \displaystyle \frac { \kappa } { \lambda ( \beta + 1 ) } T ^ { - \alpha } F ^ { \alpha , \lambda } ( t ) ( 1 , \beta ) . } } \end{array}
$$

Let now

$$
\varepsilon _ { 2 } ^ { T } ( a , t ) = - \frac { 1 } { 2 } \int _ { 0 } ^ { t } \left( Y ^ { T } ( a , t - s ) - ( 1 , 1 ) \right) ^ { 2 } \chi f ^ { \alpha , \lambda } ( s ) d s + i a \frac { \kappa } { ( \beta + 1 ) } T ^ { - 2 \alpha } F ^ { \alpha , \lambda } ( t ) ( 1 , \beta ) .
$$

We obtain

$$
\begin{array} { l } { { \displaystyle Y ^ { T } ( a , t ) - ( 1 , 1 ) = \bar { \varepsilon } _ { 1 } ^ { T } ( a , t ) + \bar { \varepsilon } _ { 2 } ^ { T } ( a , t ) + i a \sqrt { \kappa } T ^ { - \alpha } ( 1 , - 1 ) + \displaystyle \frac { 1 } { 2 \lambda } T ^ { \alpha } \int _ { 0 } ^ { t } \left( Y ^ { T } ( a , t - s ) - ( 1 , 1 ) \right) ^ { 2 } \cdot \chi f ^ { \alpha , \lambda } ( s ) d s } } \\ { { \displaystyle \qquad - i a \frac { \kappa } { \lambda ( \beta + 1 ) } T ^ { - \alpha } F ^ { \alpha , \lambda } ( t ) ( 1 , \beta ) . } } \end{array}
$$

Using Proposition 6.4, we easily see that $T ^ { 2 \alpha } \varepsilon _ { 1 } ^ { T }$ and $T ^ { 2 \alpha } \varepsilon _ { 2 } ^ { T }$ are uniformly bounded in t and T. We now set

$$
\theta ^ { T } ( a , t ) = \big ( \theta ^ { T , + } ( a , t ) , \theta ^ { T , - } ( a , t ) \big ) = T ^ { \alpha } \big ( Y ^ { T } ( a , t ) - ( 1 , 1 ) \big )
$$

and

$$
\boldsymbol { r } ^ { T } ( \boldsymbol { a } , t ) = T ^ { \alpha } \big ( \varepsilon _ { 1 } ^ { T } ( \boldsymbol { a } , t ) + \varepsilon _ { 2 } ^ { T } ( \boldsymbol { a } , t ) \big ) .
$$

We have that $T ^ { \alpha } r ^ { T }$ is uniformly bounded in t and T and

$$
\theta ^ { T } ( a , t ) = r ^ { T } ( a , t ) + i a \sqrt { \kappa } ( 1 , - 1 ) - i a \frac { \kappa } { \lambda ( \beta + 1 ) } F ^ { \alpha , \lambda } ( t ) ( 1 , \beta ) + \frac { 1 } { 2 \lambda } \int _ { 0 } ^ { t } \left( \theta ^ { T } ( a , t - s ) \right) ^ { 2 } \cdot \chi f ^ { \alpha , \lambda } ( s ) d s .
$$

<!-- page: 29 -->

Convergence of $\theta ^ { T }$ For fixed a, we now show that $t \to \theta ^ { T } ( a , t )$ is a Cauchy sequence in the space of continuous functions $C ( [ 0 , 1 ] , \mathbb { R } ^ { 2 } )$ equipped with the sup-norm. Let $\delta > 0$ and $T _ { 0 } > 1$ such that for $\begin{array} { r } { T > T _ { 0 } \mathrm { ~ , ~ } \| r ^ { T } ( a , t ) \| _ { \infty } \leq \frac { \delta } { 2 } } \end{array}$ for any $t \in [ 0 , 1 ]$ . Then for $T > T _ { 0 } , T ^ { \prime } > T _ { 0 }$ and $t \in [ 0 , 1 ]$ ，

$$
\| \theta ^ { T } ( a , t ) - \theta ^ { T ^ { \prime } } ( a , t ) \| \leq \delta + \frac { 1 } { 2 \lambda } \int _ { 0 } ^ { t } \left\| \big ( \theta ^ { T } ( a , t - s ) \big ) ^ { 2 } \cdot \chi - \big ( \theta ^ { T ^ { \prime } } ( a , t - s ) \big ) ^ { 2 } \cdot \chi \right\| f ^ { \alpha , \lambda } ( s ) d s .
$$

Since $\theta ^ { T }$ is uniformly bounded in t and T, we get

$$
\| \theta ^ { T } ( a , t ) - \theta ^ { T ^ { \prime } } ( a , t ) \| \leq \delta + C ( a ) \int _ { 0 } ^ { t } \| \theta ^ { T } ( a , t - s ) - \theta ^ { T ^ { \prime } } ( a , t - s ) \| f ^ { \alpha , \lambda } ( s ) d s .
$$

Using Lemma A.3 in Appendix, this enables us to show that $\theta ^ { T }$ is a Cauchy sequence. Consequently, $\theta ^ { T } ( a , t )$ converges uniformly in t to $\left( c ( a , t ) , d ( a , t ) \right)$ , where $( c , d )$ is solution to the following equation:

$$
c ( a , t ) = i a \sqrt { \kappa } - i a \frac { \kappa } { \lambda ( \beta + 1 ) } F ^ { \alpha , \lambda } ( t ) + \frac { 1 } { 2 \lambda ( \beta + 1 ) } \int _ { 0 } ^ { t } \left( c ^ { 2 } ( a , t - s ) + d ^ { 2 } ( a , t - s ) \right) f ^ { \alpha , \lambda } ( s ) d s
$$

$$
d ( a , t ) = - i a \sqrt { \kappa } - i a \frac { \beta \kappa } { \lambda ( \beta + 1 ) } F ^ { \alpha , \lambda } ( t ) + \frac { \beta } { 2 \lambda ( \beta + 1 ) } \int _ { 0 } ^ { t } \left( c ^ { 2 } ( a , t - s ) + d ^ { 2 } ( a , t - s ) \right) f ^ { \alpha , \lambda } ( s ) d s .
$$

## 6.2.3 End of the proof of Theorem 4.1

Deriving the characteristic function Let $a \in \mathbb { R }$ . Recall that from Section 4.1, we have

$$
L ^ { T } ( a _ { T } ^ { + } , a _ { T } ^ { - } , t T ) = \exp \Big ( \int _ { 0 } ^ { t } \big ( T ^ { \alpha } ( Y ^ { T , + } ( a , t - s ) - 1 ) + T ^ { \alpha } ( Y ^ { T , - } ( a , t - s ) - 1 ) \big ) \big ( T ^ { 1 - \alpha } \hat { \mu } ( s T ) \big ) d s \Big )
$$

and furthermore, from Proposition 6.5,

$$
T ^ { \alpha } ( Y ^ { T , + } ( a , t ) - 1 ) + T ^ { \alpha } ( Y ^ { T , - } ( a , t ) - 1 )
$$

converges uniformly in t to $c ( a , t ) + d ( a , t )$ . Also, using Remark 2.2, we have

$$
T ^ { 1 - \alpha } \hat { \mu } ( t T ) = \mu + \mu \xi \bigl ( \frac { t ^ { - \alpha } } { \lambda } ( T t ) ^ { \alpha } \int _ { t T } ^ { \infty } \varphi ( s ) d s + \lambda T ^ { - \alpha } \int _ { 0 } ^ { t T } \varphi ( s ) d s \bigr )
$$

and therefore $T ^ { 1 - \alpha } \hat { \mu } ( t T )$ converges towards

$$
\mu \big ( 1 + \xi \frac { t ^ { - \alpha } } { \lambda \Gamma ( 1 - \alpha ) } \big ) .
$$

In addition, using Proposition 6.4, we get that for given $t \in [ 0 , 1 ]$ and for any $s \in [ 0 , t ]$

$$
\big | T ^ { \alpha } ( Y ^ { T , + } ( a , t - s ) - 1 ) + T ^ { \alpha } ( Y ^ { T , - } ( a , t - s ) - 1 ) \big | \big ( T ^ { 1 - \alpha } \hat { \mu } ( s T ) \big ) \leq c ( a ) ( 1 + s ^ { - \alpha } ) .
$$

The right hand side of the last inequality is integrable over $[ 0 , t ]$ . Therefore, using the convergence of $L ^ { T } ( a _ { T } ^ { + } , a _ { T } ^ { - } , t T )$ towards $L _ { p } ( a , t )$ and applying the dominated convergence theorem, we obtain

$$
L _ { p } ( a , t ) = \exp \big ( \int _ { 0 } ^ { t } g ( a , s ) ( 1 + \xi \frac { ( t - s ) ^ { - \alpha } } { \lambda \Gamma ( 1 - \alpha ) } ) d s \big ) ,
$$

<!-- page: 30 -->

where $g ( a , t ) = \mu { \bigl ( } c ( a , t ) + d ( a , t ) { \bigr ) }$ . Thus, we have shown that

$$
L _ { p } ( a , t ) = \exp \big ( \int _ { 0 } ^ { t } g ( a , s ) d s + \frac { V _ { 0 } } { \theta \lambda } I ^ { 1 - \alpha } g ( a , t ) \big ) .
$$

Integral equation for $g$ We now prove that $g$ is solution of an integral equation. First remark that

$$
d ( a , t ) = \beta c ( a , t ) - i a ( 1 + \beta ) \sqrt { \kappa } .
$$

Hence $g ( a , t ) = \mu ( \beta + 1 ) ( c ( a , t ) - i a \sqrt { \kappa } )$ , which can be written

$$
- i a \frac { \mu \kappa } { \lambda } F ^ { \alpha , \lambda } ( t ) + \frac { \mu } { 2 \lambda } \int _ { 0 } ^ { t } \Big ( ( c ( a , s ) - i a \sqrt { \kappa } + i a \sqrt { \kappa } ) ^ { 2 } + \big ( \beta ( c ( a , s ) - i a \sqrt { \kappa } ) - i a \sqrt { \kappa } \big ) ^ { 2 } \Big ) f ^ { \alpha , \lambda } ( t - s ) d s .
$$

Thus,

$$
\begin{array} { l } { { g ( a , t ) = \displaystyle { - i a \frac { \mu \kappa } { \lambda } } F ^ { \alpha , \lambda } ( t ) + \frac { 1 + \beta ^ { 2 } } { 2 \mu \lambda ( 1 + \beta ) ^ { 2 } } \int _ { 0 } ^ { t } \left( g ( a , s ) \right) ^ { 2 } f ^ { \alpha , \lambda } ( t - s ) d s - a ^ { 2 } \frac { \mu \kappa } { \lambda } F ^ { \alpha , \lambda } ( t ) } } \\ { { \displaystyle { ~ + i a \frac { \sqrt { \kappa } ( 1 - \beta ) } { \lambda ( \beta + 1 ) } \int _ { 0 } ^ { t } g ( a , s ) f ^ { \alpha , \lambda } ( t - s ) d s } . } } \end{array}
$$

Using the definition of κ in Section 6.2, we deduce

$$
\begin{array} { l } { { g ( a , t ) = { \displaystyle { \frac { \theta } { 2 } } ( - a ^ { 2 } - i a ) F ^ { \alpha , \lambda } ( t ) + i a \frac { \sqrt { \theta } ( 1 - \beta ) } { \sqrt { 2 \lambda \mu } ( \beta + 1 ) } } \int _ { 0 } ^ { t } g ( a , s ) f ^ { \alpha , \lambda } ( t - s ) d s } } \\ { { + \displaystyle { \frac { 1 + \beta ^ { 2 } } { 2 \mu \lambda ( 1 + \beta ) ^ { 2 } } } \int _ { 0 } ^ { t } g ^ { 2 } ( a , s ) f ^ { \alpha , \lambda } ( t - s ) d s } } \end{array}
$$

and from those of $\rho$ and ν in Section 4.1, we finally obtain that $g ( a , t )$ is equal to

$$
\frac { \theta } { 2 } ( - a ^ { 2 } - i a ) F ^ { \alpha , \lambda } ( t ) + i a \rho \nu \int _ { 0 } ^ { t } g ( a , s ) f ^ { \alpha , \lambda } ( t - s ) d s + \frac { \nu ^ { 2 } } { 2 \theta } \int _ { 0 } ^ { t } \big ( g ( a , s ) \big ) ^ { 2 } f ^ { \alpha , \lambda } ( t - s ) d s .
$$

Thus,

$$
L _ { p } ( a , t ) = \exp \Big ( \int _ { 0 } ^ { t } g ( a , s ) \big ( 1 + \xi \frac { ( t - s ) ^ { - \alpha } } { \lambda \Gamma ( 1 - \alpha ) } \big ) d s \Big )
$$

with

$$
g ( a , t ) = \int _ { 0 } ^ { t } \left( \frac { \theta } { 2 } ( - a ^ { 2 } - i a ) + i a \rho \nu g ( a , s ) + \frac { \nu ^ { 2 } } { 2 \theta } \big ( g ( a , s ) \big ) ^ { 2 } \right) f ^ { \alpha , \lambda } ( t - s ) d s .
$$

Let us now set $h = g / ( \theta \lambda )$ . Then

$$
L _ { p } ( a , t ) = \exp \Big ( \int _ { 0 } ^ { t } h ( a , s ) \big ( \theta \lambda + V _ { 0 } \frac { ( t - s ) ^ { - \alpha } } { \Gamma ( 1 - \alpha ) } \big ) d s \Big ) ,
$$

with

$$
h ( a , t ) = \int _ { 0 } ^ { t } \Big ( \frac { 1 } { 2 } ( - a ^ { 2 } - i a ) + i a \lambda \rho \nu h ( a , s ) + \frac { ( \lambda \nu ) ^ { 2 } } { 2 } \big ( h ( a , s ) \big ) ^ { 2 } \Big ) \frac { 1 } { \lambda } f ^ { \alpha , \lambda } ( t - s ) d s .\tag{31}
$$

Using Lemma $\mathrm { { A . 2 } }$ , we have that Equation (31) can also be written under the following form:

$$
D ^ { \alpha } h ( a , t ) = \frac { 1 } { 2 } ( - a ^ { 2 } - i a ) + \lambda ( i a \rho \nu - 1 ) h ( a , s ) + \frac { ( \lambda \nu ) ^ { 2 } } { 2 } \big ( h ( a , s ) \big ) ^ { 2 } , I ^ { 1 - \alpha } h ( a , 0 ) = 0 .
$$

<!-- page: 31 -->

## 6.2.4 Uniqueness of the solution of (24)

For a given $a \in \mathbb { R }$ , consider two continuous solutions $h _ { 1 } ( a , . )$ and $h _ { 2 } ( a , . )$ of (24) or equivalently of (31). We have that $| h _ { 1 } ( a , t ) - h _ { 2 } ( a , t ) |$ is smaller than

$$
\int _ { 0 } ^ { t } { \big ( } | a \rho \nu | { \big | } h _ { 1 } ( a , s ) - h _ { 2 } ( a , s ) { \big | } + { \frac { \lambda \nu ^ { 2 } } { 2 } } { \big | } { \big ( } h _ { 1 } ( a , s ) { \big ) } ^ { 2 } - { \big ( } h _ { 2 } ( a , s ) { \big ) } ^ { 2 } { \big | } { \big ) } f ^ { \alpha , \lambda } ( t - s ) d s .
$$

Using the continuity of $h _ { 1 } ( a , . )$ and $h _ { 2 } ( a , . )$ , this is also smaller than

$$
c ( a ) \int _ { 0 } ^ { t } | h _ { 1 } ( a , s ) - h _ { 2 } ( a , s ) | f ^ { \alpha , \lambda } ( t - s ) d s .
$$

Thanks to Lemma A.3, this gives $h _ { 1 } ( a , . ) = h _ { 2 } ( a , . )$

## Acknowledgments

We thank Masaaki Fukasawa, Jim Gatheral and Antoine Jacquier for many interesting discussions and Christa Cuchiero and Josef Teichmann for very relevant comments about the afine nature of the processes considered in this work.

## A Appendix

We gather in this section some useful technical results.

## A.1 Mittag-Lefler functions

Let $( \alpha , \beta ) \in ( \mathbb { R } _ { + } ^ { * } ) ^ { 2 }$ . The Mittag-Lefler function $E _ { \alpha , \beta }$ is defined for $z \in \mathbb { C }$ by

$$
E _ { \alpha , \beta } ( z ) = \sum _ { n \geq 0 } \frac { z ^ { n } } { \Gamma ( \alpha n + \beta ) } .
$$

For $( \alpha , \lambda ) \in ( 0 , 1 ) \times { \mathbb { R } } _ { + }$ , we also define

$$
f ^ { \alpha , \lambda } ( t ) = \lambda t ^ { \alpha - 1 } E _ { \alpha , \alpha } ( - \lambda t ^ { \alpha } ) , t > 0 ,
$$

$$
F ^ { \alpha , \lambda } = \int _ { 0 } ^ { t } f ^ { \alpha , \lambda } ( s ) d s , t \geq 0 .
$$

The function $f ^ { \alpha , \lambda }$ is a density function on $\mathbb { R } _ { + }$ called Mittag-Lefler density function. The following properties of $f ^ { \alpha , \lambda }$ and $F ^ { \alpha , \lambda }$ can be found in [21, 34, 36]. We have

$$
f ^ { \alpha , \lambda } ( t ) \underset { t  0 ^ { + } } { \sim } \frac { \lambda } { \Gamma ( \alpha ) } t ^ { \alpha - 1 } , f ^ { \alpha , \lambda } ( t ) \underset { t  \infty } { \sim } \frac { \alpha } { \lambda \Gamma ( 1 - \alpha ) } t ^ { - ( \alpha + 1 ) }
$$

and

$$
F ^ { \alpha , \lambda } ( t ) = 1 - E _ { \alpha , 1 } ( - \lambda t ^ { \alpha } ) , F ^ { \alpha , \lambda } ( t ) \underset { t  0 ^ { + } } { \sim } \frac { \lambda } { \Gamma ( \alpha + 1 ) } t ^ { \alpha } , 1 - F ^ { \alpha , \lambda } ( t ) \underset { t  \infty } { \sim } \frac { 1 } { \lambda \Gamma ( 1 - \alpha ) } t ^ { - \alpha } .
$$

Finally, for $\alpha \in ( 1 / 2 , 1 ) , f ^ { \alpha , \lambda }$ is square-integrable and its Laplace transform is given for $z \geq 0$ by

$$
\hat { f } ^ { \alpha , \lambda } ( z ) = \int _ { 0 } ^ { \infty } f _ { \alpha , \lambda } ( s ) e ^ { - z s } d s = \frac { \lambda } { \lambda + z ^ { \alpha } } .
$$

<!-- page: 32 -->

## A.2 Wiener-Hopf equations

The following result is used extensively in this work to solve Wiener-Hopf type equations, see for example [3].

Lemma A.1. Let g be a measurable locally bounded function from R to $\mathbb { R } ^ { d }$ and $\phi : \mathbb { R } _ { + } $ $\mathcal { M } ^ { d } ( \mathbb { R } )$ be a matrix-valued function with integrable components such that $\begin{array} { r } { { \cal S } ( \int _ { 0 } ^ { \infty } \phi ( s ) d s ) < 1 } \end{array}$ Then there exists a unique locally bounded function f from R to $\mathbb { R } ^ { d }$ solution of

$$
f ( t ) = g ( t ) + \int _ { 0 } ^ { t } \phi ( t - s ) . f ( s ) d s , t \geq 0
$$

given by

$$
f ( t ) = g ( t ) + \int _ { 0 } ^ { t } \psi ( t - s ) . g ( s ) d s , t \geq 0 ,
$$

where $\psi = \sum _ { k \geq 1 } \phi ^ { * k }$

## A.3 Fractional diferential equations

We end this appendix with some useful results about fractional diferential equations. The next lemma can be found in [40].

Lemma A.2. Let h be a continuous function from [0, 1] to R, $\alpha \in ( 0 , 1 ]$ and $\lambda \in \mathbb { R }$ . There is a unique continuous solution to the equation

$$
D ^ { \alpha } y ( t ) = \lambda y ( t ) + h ( t ) , I ^ { 1 - \alpha } y ( 0 ) = 0
$$

given by

$$
y ( t ) = \int _ { 0 } ^ { t } ( t - s ) ^ { \alpha - 1 } E _ { \alpha , \alpha } { \bigl ( } \lambda ( t - s ) ^ { \alpha } { \bigr ) } h ( s ) d s .
$$

We also have the following useful result.

Lemma A.3. Let h be a non-negative continuous function from [0, 1] to R such that for any $t \in [ 0 , 1 ]$ 2

$$
h ( t ) \leq \varepsilon + C \int _ { 0 } ^ { t } f ^ { \alpha , \lambda } ( t - s ) h ( s ) d s ,
$$

for some $\varepsilon \geq 0$ and $C \geq 0$ . Then for any $t \in [ 0 , 1 ]$ 2

$$
h ( t ) \leq C ^ { \prime } \varepsilon ,
$$

with

$$
C ^ { \prime } = 1 + C \lambda \int _ { 0 } ^ { 1 } s ^ { \alpha - 1 } E _ { \alpha , \alpha } \bigl ( \lambda ( C - 1 ) s ^ { \alpha } \bigr ) d s > 0 .
$$

In particular, $i f \varepsilon = 0$ then $h = 0$

<!-- page: 33 -->

Proof:

Let

$$
f ( t ) = h ( t ) - C \int _ { 0 } ^ { t } f ^ { \alpha , \lambda } ( t - s ) h ( s ) d s .
$$

and $g = h - f$ . The function g is solution of

$$
g ( t ) = C \int _ { 0 } ^ { t } { f ^ { \alpha , { \lambda } } ( t - s ) \big ( g ( s ) + f ( s ) \big ) } d s .
$$

Thus, from Lemma A.2, g is the unique solution of

$$
D ^ { \alpha } g ( t ) = \lambda ( C - 1 ) g ( t ) + C \lambda f ( t ) , I ^ { 1 - \alpha } g ( 0 ) = 0 .
$$

Hence using again Lemma A.2, we deduce that

$$
g ( t ) = C \lambda \int _ { 0 } ^ { t } ( t - s ) ^ { \alpha - 1 } E _ { \alpha , \alpha } { \big ( } \lambda ( C - 1 ) ( t - s ) ^ { \alpha } { \big ) } f ( s ) d s .
$$

Therefore,

$$
g ( t ) \leq C \lambda \varepsilon \int _ { 0 } ^ { t } s ^ { \alpha - 1 } E _ { \alpha , \alpha } \big ( \lambda ( C - 1 ) s ^ { \alpha } \big ) d s .
$$

Using that $h = f + g$ together with the fact that $E _ { \alpha , \alpha }$ is non-negative, we get the result.

## References

[1] H. Albrecher, P. Mayer, W. Schoutens, and J. Tistaert. The little Heston trap. Wilmott Magazine, pages 83–92, January 2007. [2] E. Bacry, S. Delattre, M. Hofmann, and J.-F. Muzy. Modelling microstructure noise with mutually exciting point processes. Quantitative Finance, 13(1):65–77, 2013. [3] E. Bacry, S. Delattre, M. Hofmann, and J.-F. Muzy. Some limit theorems for Hawkes processes and application to financial statistics. Stochastic Processes and their Applications, 123(7):2475–2499, 2013. [4] E. Bacry, T. Jaisson, and J.-F. Muzy. Estimation of slowly decreasing Hawkes kernels: Application to high frequency order book modelling. Quantitative Finance, 16(8):1179– 1201, 2016. [5] C. Bayer, P. Friz, and J. Gatheral. Pricing under rough volatility. Quantitative Finance, 16(6):887–904, 2016. [6] M. Bennedsen, A. Lunde, and M. S. Pakkanen. Hybrid scheme for Brownian semistationary processes. arXiv preprint arXiv:1507.03004, 2015. [7] J.-P. Bouchaud and M. Potters. Theory of financial risk and derivative pricing: from statistical physics to risk management. Cambridge university press, 2003. [8] P. Carr and D. Madan. Option valuation using the fast Fourier transform. Journal of Computational Finance, 2(4):61–73, 1999.

<!-- page: 34 -->

[9] A. A. Christie. The stochastic behavior of common stock variances: Value, leverage and interest rate efects. Journal of Financial Economics, 10(4):407–432, 1982. [10] K. Diethelm, N. J. Ford, and A. D. Freed. A predictor-corrector approach for the numerical solution of fractional diferential equations. Nonlinear Dynamics, 29(1-4):3–22, 2002. [11] K. Diethelm, N. J. Ford, and A. D. Freed. Detailed error analysis for a fractional Adams method. Numerical algorithms, 36(1):31–52, 2004. [12] K. Diethelm and A. D. Freed. The fracpece subroutine for the numerical solution of diferential equations of fractional order. In Forschung und Wissenschaftliches Rechnen 1998, pages 57–71. Gesellschaft f¨ur Wisseschaftliche Datenverarbeitung Gottingen, Germany, 1999. [13] A. A. Dragulescu and V. M. Yakovenko. Probability distribution of returns in the Heston model with stochastic volatility. Quantitative finance, 2(6):443–453, 2002. [14] O. El Euch, M. Fukasawa, and M. Rosenbaum. The microstructural foundations of leverage efect and rough volatility. Working paper, 2016. [15] M. Forde, A. Jacquier, and R. Lee. The small-time smile and term structure of implied volatility under the Heston model. SIAM Journal on Financial Mathematics, 3(1):690– 708, 2012. [16] M. Fukasawa. Asymptotic analysis for stochastic volatility: Martingale expansion. Finance and Stochastics, 15(4):635–654, 2011. [17] J. Gatheral. The volatility surface: a practitioner’s guide, volume 357. John Wiley & Sons, 2011. [18] J. Gatheral, T. Jaisson, and M. Rosenbaum. Volatility is rough. Available at SSRN 2509457, 2014. [19] H. Guennoun, A. Jacquier, and P. Roome. Asymptotic behaviour of the fractional Heston model. Available at SSRN 2531468, 2014. [20] S. J. Hardiman, N. Bercot, and J.-P. Bouchaud. Critical reflexivity in financial markets: a Hawkes process analysis. The European Physical Journal B, 86(10):1–9, 2013. [21] H. J. Haubold, A. M. Mathai, and R. K. Saxena. Mittag-lefler functions and their applications. Journal of Applied Mathematics, 2011. [22] A. G. Hawkes and D. Oakes. A cluster process representation of a self-exciting process. Journal of Applied Probability, pages 493–503, 1974. [23] S. L. Heston. A closed-form solution for options with stochastic volatility with applications to bond and currency options. Review of Financial Studies, 6(2):327–343, 1993. [24] A. Itkin. Pricing options with VG model using FFT. arXiv preprint physics/0503137, 2005.

<!-- page: 35 -->

[25] J. Jacod and A. Shiryaev. Limit theorems for stochastic processes, volume 288. Springer Science & Business Media, 2013. [26] A. Jacquier and P. Roome. The small-maturity Heston forward smile. SIAM Journal on Financial Mathematics, 4(1):831–856, 2013. [27] A. Jacquier and P. Roome. Large-maturity regimes of the Heston forward smile. Stochastic Processes and their Applications, 126(4):1087–1123, 2016. [28] T. Jaisson and M. Rosenbaum. Rough fractional difusions as scaling limits of nearly unstable heavy tailed Hawkes processes. The Annals of Applied Probability, to appear, 2016. [29] T. Jaisson, M. Rosenbaum, et al. Limit theorems for nearly unstable Hawkes processes. The Annals of Applied Probability, 25(2):600–631, 2015. [30] A. Janek, T. Kluge, R. Weron, and U. Wystup. FX smile in the Heston model. In Statistical Tools for Finance and Insurance, pages 133–162. Springer, 2011. [31] C. Kahl and P. J¨ackel. Not-so-complex logarithms in the Heston model. Wilmott magazine, pages 94–103, September 2005. [32] A. L. Lewis. A simple option formula for general jump-difusion and other exponential l´evy processes. Available at SSRN 282110, 2001. [33] C. Li and C. Tao. On the fractional Adams method. Computers & Mathematics with Applications, 58(8):1573–1588, 2009. [34] F. Mainardi. On some properties of the Mittag-Lefler function. arXiv preprint arXiv:1305.0161. [35] B. B. Mandelbrot. The variation of certain speculative prices. In Fractals and Scaling in Finance, pages 371–418. Springer, 1997. [36] A. M. Mathai and H. J. Haubold. Special functions for applied scientists. Springer, 2008. [37] A. Mazzon and A. Pascucci. The forward smile in local-stochastic volatility models. Available at SSRN 2560300, 2015. [38] S.-H. Poon. The Heston option pricing model. Unpublished Draft, 2009. [39] D. Revuz and M. Yor. Continuous martingales and Brownian motion, volume 293. Springer Science & Business Media, 1999. [40] S. G. Samko, A. A. Kilbas, and O. I. Marichev. Fractional integrals and derivatives, volume 1993. Theory and Applications, Gordon and Breach, Yverdon, 1993. [41] M. Schmelzle. Option pricing formulae using Fourier transform: Theory and application. Preprint, http://pfadintegral. com, 2010.
