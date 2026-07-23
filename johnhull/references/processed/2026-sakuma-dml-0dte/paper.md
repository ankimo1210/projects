# 2026-sakuma-dml-0dte

<!-- page: 1 -->

## Diferential Machine Learning for 0DTE Options with Stochastic Volatility and Jumps

Takayuki Sakuma<sup>∗</sup>

Faculty of Economics and Business Administration, Soka University

July 14, 2026

## Abstract

We present a diferential machine learning method for zero-days-to-expiry (0DTE) options under a stochastic-volatility jump-difusion model. To handle the ultra-short-maturity regime, we express the option price in Black–Scholes form with a maturity-gated variance correction, combining supervision on prices and Greeks with a PIDE-residual penalty. Prices and Greeks are derived from a single trained pricing network, while jump-term identifiability is ensured by a jump-operator network fitted jointly in a three-stage procedure. The method improves jump-term approximation relative to one-stage baselines while maintaining comparable pricing errors. Furthermore, it reduces errors in Greeks, produces stable one-day delta hedges, and ofers significant speedups over Fourier-based benchmarks. Calibration experiments demonstrate the network’s eficiency as a pricer and incorporating jump-intensity price sensitivity into the learning process further improves the overall model fit. We also consider a jump rough Heston model.

## 1 Introduction

Zero-days-to-expiry (0DTE) options have grown rapidly over the past few years and now account for a large share of trading volume. Recent empirical work documents frequent intraday jumps in 0DTE markets [Bozovic(2025)], studies the role of gamma-related open-interest exposures [Dim et al.(2024)], and analyzes the pricing implications of short-horizon tail risk in 0DTE options [Bandi et al.(2023)]. These findings raise two practical challenges: first, the underlying dynamics may be better described by a difusion model with jumps; second, the very short maturities and frequent intraday rebalancing demand fast computation of option prices and Greeks.

We apply diferential machine learning (DML) [Huge and Savine(2020), Frandsen et al.(2022)] to 0DTE options under the Bates stochastic-volatility jump-difusion (SVJD) model. Learning-based models can reduce pricing costs: once trained, prices and Greeks are obtained from a single network evaluation. However, the numerically most challenging region is near the money, where Greeks can become very large for 0DTE options with jumps. A common approach in machine-learning PDE solvers is to enforce the governing PDE by penalizing its residual at sampled state points, together with terminal and boundary conditions [Raissi et al.(2019)]. Several recent studies apply this residual-penalty approach to option pricing with jumps by including a PIDE-residual term in the training objective [Fu and Hirsa(2020), Sun et al.(2025), Bansal et al.(2026)]. Three design choices are central to our approach:

1. We adopt DML, training a single price network jointly on option values and Greeks. The Greeks are obtained by automatic diferentiation of the network output with respect to its inputs and enter the loss directly.

2. Instead of predicting prices directly, the network learns a variance correction inside a Black–Scholes formula [Black and Scholes(1973)], scaled so that the correction vanishes as τ → 0. This preserves the correct short-maturity limit (the payof) and reduces the approximation burden in the near-singular region. More broadly, this design is related to neural-network surrogates for option pricing and impliedvolatility computation [Liu et al.(2019)], and to implied-volatility smoothing methods that impose no-arbitrage structure to improve surface regularity [Ackerer et al.(2020)].

arXiv:2603.07600v5 [q-fin.CP] 13 Jul 2026

<sup>∗</sup>e-mail: tsakuma@soka.ac.jp.

<!-- page: 2 -->

3. We introduce a second neural network to represent the compensated jump operator. If the jump component is identified only through a PIDE-residual penalty, the optimizer can trade of difusion and jump errors while keeping the overall residual small. A small residual therefore does not guarantee that the learned jump operator matches the model-implied jump integral. The second network makes the residual penalty informative about the jump contribution.

Recent calibration studies using DML fall into two broad strands. Sridi and Bilokon (2023) apply DML to the calibration of vanilla European puts under the Heston model, while Polala and Hientzsch (2023) extend parametric DML to joint pricing and calibration problems [Sridi and Bilokon(2023), Polala and Hientzsch(2023)]. In these approaches, DML primarily replaces the pricer to gain speed. Zhang et al. (2025), by contrast, propose a gradient-based scheme that learns both prices and sensitivities with respect to model parameters [Zhang et al.(2025)]. We ask whether our approach can play both roles: as a fast pricer in calibration and as a way to improve calibration in a focused extension. We also ask whether our DML framework can be extended to rough volatility models. To this end, we consider a jump rough Heston model based on a multi-factor Markovian approximation, which replaces the fractional kernel by a finite sum of exponentials [Abi Jaber and El Euch(2019)].

Paper organization. Section 2 presents the Bates stochastic-volatility jump-difusion model. Section 3 introduces the DML-based neural network and the three-stage training scheme. Section 4 specifies the loss functions and constraints. Section 5 reports numerical experiments, including calibration exercises.

## 2 Bates model

We work with the Bates stochastic-volatility jump-difusion (SVJD) model, which combines a Heston-type variance process with Merton-style lognormal price jumps [Merton(1976), Heston(1993), Bates(1996)]. For brevity, we refer to this simply as the Bates model throughout the paper. Under the risk-neutral measure, let $S _ { t }$ denote the underlying asset, $V _ { t }$ the instantaneous variance, r the risk-free rate, and $q$ the dividend. The dynamics are

$$
\frac { d S _ { t } } { S _ { t ^ { - } } } = \left( r - q - \lambda \kappa _ { J } \right) d t + \sqrt { V _ { t } } d W _ { t } ^ { S } + \left( e ^ { Y } - 1 \right) d N _ { t } ,\tag{1}
$$

$$
d V _ { t } = \kappa ( \theta - V _ { t } ) d t + \sigma _ { v } \sqrt { V _ { t } } d W _ { t } ^ { V } ,\tag{2}
$$

where $( W _ { t } ^ { S } , W _ { t } ^ { V } )$ is a two-dimensional Brownian motion with correlation $\rho , \ N _ { t }$ is a Poisson process with intensity $\lambda ,$ , and the jump sizes are i.i.d. with $Y \sim \mathcal { N } ( \mu _ { J } , \sigma _ { J } ^ { 2 } )$ . Here κ is the variance mean-reversion speed in (2) and $\begin{array} { r } { \kappa _ { J } = \mathbb { E } [ e ^ { Y } - 1 ] = \exp ( \mu _ { J } + \frac { 1 } { 2 } \sigma _ { J } ^ { 2 } ) - 1 } \end{array}$

For a European call option with maturity τ and strike K, the risk-neutral call price C satisfies the following PIDE:

$$
\frac { \partial C } { \partial \tau } = ( r - q ) S \frac { \partial C } { \partial S } + \kappa ( \theta - V ) \frac { \partial C } { \partial V } + \frac 1 2 V S ^ { 2 } \frac { \partial ^ { 2 } C } { \partial S ^ { 2 } } + \frac 1 2 \sigma _ { v } ^ { 2 } V \frac { \partial ^ { 2 } C } { \partial V ^ { 2 } } + \rho \sigma _ { v } V S \frac { \partial ^ { 2 } C } { \partial S \partial V } - r C + \lambda \mathcal { I } [ C ] ,\tag{3}
$$

with terminal condition $C ( S , V , 0 ) = ( S - K ) ^ { + }$ . The compensated jump operator is

$$
\mathcal { I } [ C ] ( S , V , \tau ) = \int _ { \mathbb { R } } \left[ C ( S e ^ { y } , V , \tau ) - C ( S , V , \tau ) - ( e ^ { y } - 1 ) S C _ { S } ( S , V , \tau ) \right] f _ { Y } ( y ) d y ,\tag{4}
$$

where $f _ { Y }$ denotes the density of the logarithmic jump size Y . We use the dimensionless log-moneyness

$$
x : = \log ( S / K ) , \quad \quad \tau : = T - t
$$

<!-- page: 3 -->

and the difusion part of the operator is

$$
\begin{array} { r } { \mathcal { L } _ { \mathrm { d i f f } } u = u _ { t } + ( r - q ) u _ { x } + \kappa ( \theta - V ) u _ { V } + \frac { 1 } { 2 } V \big ( u _ { x x } - u _ { x } \big ) + \rho \sigma _ { v } V u _ { x V } + \frac { 1 } { 2 } \sigma _ { v } ^ { 2 } V u _ { V V } - r u , } \end{array}\tag{5}
$$

where $u _ { t } = - u _ { \tau }$ since $\tau$ is time-to-maturity. We define the residua

$$
R ( { \bf x } ) : = \mathcal { L } _ { \mathrm { d i f f } } u _ { \phi } ( { \bf x } ) + \lambda J _ { \psi } ( { \bf x } ) ,\tag{6}
$$

where $J _ { \psi }$ denotes a neural approximation to the normalized compensated jump operator

$$
J _ { \psi } ( \mathbf { x } ) : = \int _ { \mathbb { R } } \left[ u ( x + y , V , \tau ) - u ( x , V , \tau ) - ( e ^ { y } - 1 ) u _ { x } ( x , V , \tau ) \right] f _ { Y } ( y ) d y .\tag{7}
$$

In the architecture below, the second network outputs $J _ { \psi }$ directly and is supervised against a numerical quadrature proxy for $J _ { \psi } ( \mathbf { x } )$

## 3 DML for PIDEs

Figure 1 summarizes the model architecture. The solid arrows correspond to forward evaluations while dashed arrows indicate computations derived from these outputs. The input is

$$
\mathbf { x } = ( x , \tau , V , \kappa , \theta , \sigma _ { v } , \rho , \lambda , \mu _ { J } , \sigma _ { J } ) \in \mathbb { R } ^ { 1 0 } .\tag{8}
$$

Rather than predicting prices directly, the first network outputs a variance correction $\Delta V _ { \phi } ( \mathbf { x } )$ . We define an efective variance

$$
V _ { \mathrm { e f f } } ( { \bf x } ) = \operatorname* { m a x } { \left\{ V + g ( \tau ) \Delta V _ { \phi } ( { \bf x } ) , \varepsilon \right\} } , \qquad g ( \tau ) = 1 - \exp ( - \tau / \tau _ { 0 } ) ,\tag{9}
$$

and we return a Black–Scholes call price with volatility $\sigma _ { \mathrm { e f f } } = \sqrt { V _ { \mathrm { e f f } } }$ . The function $g ( \tau )$ forces the learned variance correction to vanish near expiry, which stabilizes training and preserves the payof limit. Since we work in log-moneyness, we normalize the strike to $K = 1$

$$
u _ { \phi } ( \mathbf { x } ) : = C _ { \mathrm { B S } } ( S = e ^ { x } , K = 1 , r = 0 . 0 1 , q = 0 , \tau , \sigma _ { \mathrm { e f f } } )
$$

and Greeks are obtained by automatic diferentiation of $u _ { \phi }$ . In parallel, a jump-operator network approximates the compensated jump operator $J _ { \psi } ( \mathbf { x } )$ , and the two networks are coupled through the jump-PIDE residual. Because the jump term is not identifiable from a residual loss alone, we supervise $J _ { \psi }$ and use the three-stage schedule described in Subsection 3.2.

## 3.1 Twin network

A standard supervised model fits a network $u _ { \phi } ( \mathbf { x } )$ by

$$
\operatorname* { m i n } _ { \phi } \mathbb { E } \big [ ( u _ { \phi } ( \mathbf { x } ) - u ( \mathbf { x } ) ) ^ { 2 } \big ] .
$$

DML augments this objective by adding supervised targets for selected Greeks $\partial u / \partial x _ { i } .$

$$
\operatorname* { m i n } _ { \phi } \mathbb { E } \Big [ ( u _ { \phi } - u ) ^ { 2 } + \sum _ { i \in \mathcal { I } } \omega _ { i } \big ( \partial _ { x _ { i } } u _ { \phi } - \partial _ { x _ { i } } u \big ) ^ { 2 } \Big ] ,\tag{10}
$$

where $\partial _ { x _ { i } } u _ { \phi }$ are computed by automatic diferentiation and I indexes the Greeks of interest $( \mathrm { e . g . }$ , delta, gamma, and vega). Following Huge and Savine (2020), we use the term “twin network” to denote a single price network paired with Greeks obtained by automatic diferentiation. Because the same parameters ϕ must explain both values and derivatives, derivative supervision supplies shape information and improves accuracy.

<!-- page: 4 -->

![Figure 1: Architecture and training procedure. Stages 1–3 describe the three-stage training scheme. A variance-correction network returns $\Delta V _ { \phi } ( \mathbf { x } )$ , multiplied by a deterministic maturity function $g ( \tau )$ so that the correction vanishes as $\tau 0$ . Prices are produced by substituting the resulting efective variance into the Black–Scholes call formula, yielding $u _ { \phi } ( \mathbf { x } )$ (not the standard BS price unless $\Delta V _ { \phi } \equiv 0 )$ . A separate network outputs the compensated jump contribution $J _ { \psi } ( \mathbf { x } )$ . Greeks are obtained by automatic diferentiation of $u _ { \phi }$ The jump-PIDE residual $R ( \mathbf { x } )$ is computed and penalized at randomly sampled points. Stages 1–3 depict the three-stage training scheme used for jump-term identifiability.](assets/figures/2026-sakuma-dml-0dte-p0004-block-0001-8ebd2b0ff91a2220.jpg)

Training can be further regularized by adding a PDE-residual penalty computed from the same automaticdiferentiation derivatives. However, if we approximate the nonlocal jump operator $J [ u ]$ by a separate network $J _ { \psi } ( \mathbf { x } )$ and use it only through the residual

$$
R ( { \bf x } ) = \mathcal { L } _ { \mathrm { d i f f } } u _ { \phi } ( { \bf x } ) + \lambda J _ { \psi } ( { \bf x } ) ,\tag{11}
$$

$u _ { \phi }$ and $J _ { \psi }$ are not separately identifiable: in principle, for any $u _ { \phi }$ one can set $J _ { \psi } = - \mathcal { L } _ { \mathrm { d i f f } } u _ { \phi } / \lambda$ and obtain $R \equiv 0$ . This mechanism can lead to a degenerate solution in which the jump network cancels difusionoperator errors and reduces the residual without learning a meaningful jump contribution. We therefore supervise the jump operator explicitly. Using reference prices $u ^ { \mathrm { r e f } }$ , we construct a numerical proxy for the jump term and train $J _ { \psi }$ to match it.

## 3.2 Three-stage training with jump supervision

As noted in Section 3.1, $J _ { \psi }$ can act as a residual-cancelling degree of freedom, absorbing difusion-operator errors without approximating the jump operator. We therefore use a three-stage schedule:

1. Stage 1 (price and Greeks). Train the price network while freezing $J _ { \psi } .$ , using the price and Greek terms plus the no-arbitrage penalties.

2. Stage 2 (jump reference). Freeze the price network and train the jump network to match a numerical proxy of the compensated jump term computed from the reference prices:

$$
J ^ { \mathrm { r e f } } ( x , V , \tau ) : = \mathbb { E } \big [ u ^ { \mathrm { r e f } } ( x + Y , V , \tau ) - u ^ { \mathrm { r e f } } ( x , V , \tau ) \big ] - \kappa _ { J } u _ { x } ^ { \mathrm { r e f } } ( x , V , \tau ) .\tag{12}
$$

<!-- page: 5 -->

On randomly sampled state points, we approximate the expectation in (12) with a Gauss–Hermite rule applied to $u ^ { \mathrm { r e f } } ( x + Y , V , \tau )$ and penalize $J _ { \psi } - J ^ { \mathrm { r e f } } ( x , V , \tau )$ using a Huber loss function.

3. Stage 3 (joint refinement). Train both networks jointly. In this stage we retain weak supervision against $J ^ { \mathrm { r e f } } ( x , V , \tau )$ and add a self-consistency regularizer that penalizes the mismatch between $J _ { \psi }$ and a low-order numerical jump evaluation based on the current price network.

## 4 Neural network and training

We use two fully-connected feedforward networks, each with width 192, depth 4, and SiLU activation functions (152,834 parameters in total).

## 4.1 Loss function, constraints, and weights

Let $\widehat { u } = u _ { \phi } ( \mathbf { x } )$ and $( \widehat { \Delta } , \widehat { \Gamma } , \widehat { \nu } )$ denote the corresponding Greeks. We minimize the weighted objective

$$
\begin{array} { r l r } & { } & { \mathcal { L } ( \phi , \psi ) = \mathbb { E } \Big [ w ( { \mathbf x } ) ( \widehat { u } - u ) ^ { 2 } \Big ] + \omega _ { G } \mathbb { E } \Big [ w ( { \mathbf x } ) m ( { \mathbf x } ) \sum _ { g \in \{ \Delta , \Gamma , \nu \} } \omega _ { g } \left( \lambda _ { g } ( \widehat { g } - g ) \right) ^ { 2 } \Big ] } \\ & { } & { + \omega _ { R } \mathbb { E } \Big [ w ( { \mathbf x } ) R ( { \mathbf x } ) ^ { 2 } \Big ] + \omega _ { \mathrm { c o l } } \mathbb { E } \Big [ ( \widehat { u } - u ^ { \mathrm { r e f } } ) ^ { 2 } \Big ] + \omega _ { \mathrm { N A } } \mathbb { E } \big [ \mathcal { P } _ { \mathrm { N A } } ( { \mathbf x } ) \big ] , } \end{array}\tag{13}
$$

with:

$w ( \mathbf { x } )$ upweights the ATM region and short maturities,

$$
w ( \mathbf { x } ) = 1 + W _ { \mathrm { A T M } } \mathbb { I } ( | x | < 0 . 1 ) + W _ { \mathrm { S H O R T } } \mathbb { I } ( \tau < 0 . 0 2 ) + W _ { \mathrm { A T M } \& \mathrm { S H O R T } } \mathbb { I } ( | x | < 0 . 1 , \tau < 0 . 0 2 ) .
$$

$m ( \mathbf { x } ) = \mathbb { I } ( u ^ { \mathrm { r e f } } ( \mathbf { x } ) > 1 0 ^ { - 4 } )$ drops Greek-loss contributions in deep OTM regions.

$\mathcal { P } _ { \mathrm { N A } }$ encodes simple static no-arbitrage constraints: delta bounds $( 0 \leq \Delta \leq 1 )$ , convexity $( u _ { x x } \mathrm { ~ - ~ }$ $u _ { x } \geq 0 )$ , and vega monotonicity $( \nu \geq 0 )$ , implemented as squared positive-part penalties $( \cdot ) _ { + } ^ { 2 }$ , where $( z ) _ { + } = \operatorname* { m a x } \{ z , 0 \}$

• Greek scaling uses $\lambda _ { g } \approx 1 / { \sqrt { \mathbb { E } [ g ^ { 2 } ] } }$ estimated once from the training set.

Self-consistency penalty. During joint training we augment (13) with a penalty that encourages the learned jump network to agree with a low-order numerical evaluation of the compensated operator applied to the current price network:

$$
\mathcal { L } _ { \mathrm { S C } } : = \omega _ { \mathrm { S C } } \mathbb { E } _ { \mathrm { r e s } } \Big [ \big \| J _ { \psi } ( \mathbf { x } ) - \widehat { J } [ u _ { \phi } ] ( \mathbf { x } ) \big \| ^ { 2 } \Big ] ,\tag{14}
$$

$$
\widehat { J } [ u _ { \phi } ] ( \mathbf { x } ) : = \sum _ { i = 1 } ^ { n _ { \mathrm { S C } } } w _ { i } \Big ( u _ { \phi } ( x + \mu _ { J } + \sigma _ { J } z _ { i } , V , \tau ) - u _ { \phi } ( x , V , \tau ) \Big ) - \kappa _ { J } u _ { \phi , x } ( x , V , \tau ) ,\tag{15}
$$

where $( z _ { i } , w _ { i } ) _ { i = 1 } ^ { n _ { \mathrm { S C } } }$ are nodes and weights of a Gauss–Hermite rule for $Z \sim \mathcal { N } ( 0 , 1 )$ , and we use $\omega _ { \mathrm { S C } } =$ $0 . 0 5 , n _ { \mathrm { S C } } = 1 6$

Robust Γ (gamma) loss and numerical filtering. For the most sensitive derivative targets we may replace the squared error in (13) with a robust Huber loss and ignore samples where the reference violates convexity due to numerical quadrature error. We adopt a Huber loss to reduce the impact of isolated quadrature-induced outliers, which is especially relevant for Γ and the jump-term. For Γ this takes the form

$$
\begin{array} { r } { \mathcal { L } _ { \Gamma } : = \mathbb { E } _ { \mathrm { d a t a } } \Big [ w ( \mathbf { x } ) m ( \mathbf { x } ) \mathbb { I } \big ( \Gamma ^ { \mathrm { r e f } } ( \mathbf { x } ) \geq 0 \big ) \mathrm { H u b e r } _ { \delta } \big ( \lambda _ { \Gamma } ( \widehat { \Gamma } ( \mathbf { x } ) - \Gamma ^ { \mathrm { r e f } } ( \mathbf { x } ) ) \big ) \Big ] . } \end{array}\tag{16}
$$

The training stages correspond to diferent restrictions of the full objective:

<!-- page: 6 -->

• Stage 1: minimize (13) using only the price and Greek terms and $\mathcal { P } _ { \mathrm { N A } }$ (i.e. set $\omega _ { R } = \omega _ { \mathrm { c o l } } = 0$ and freeze ψ).

• Stage 2: freeze ϕ and minimize a Huber loss on the jump network, E[Huber $\left( J _ { \psi } - J ^ { \mathrm { r e f } } ( x , V , \tau ) \right) ]$ , where $J ^ { \mathrm { r e f } }$ is computed from the reference Fourier pricer (Section 3.2).

• Stage 3: jointly refine both networks with the full loss (13) (small $\omega _ { R } )$ plus weak jump supervision and the self-consistency penalty (14). For the Γ target we use the robust variant (16).

## 5 Numerical experiments

Our experiments address four questions: how DML and residual regularization afect 0DTE price/Greek accuracy; whether the learned jump term is actually identified; whether the resulting prices and Greeks remain reliable in hedging tests; and whether a parameter-gradient extension can improve calibration. Additional model-choice robustness checks (BS/Merton baselines and an SVCJ extension) are reported in Appendix A.

## 5.1 Setting

Benchmark prices and Greeks are generated by a Fourier-transform pricer for the Bates model (1024-point quadrature; cutof $u _ { \mathrm { m a x } } = 1 0 0 0 )$ [Carr and Madan(1999)]. Reference Greeks are computed by automatic diferentiation of the same implementation.

• Log-moneyness: with probability $p _ { \mathrm { c o r e } } ~ = ~ 0 . 7$ we draw from a near-ATM band $x \sim \mathrm { U n i f } [ - 0 . 1 , 0 . 1 ]$ $( ^ { \mathfrak { s } } \mathrm { A T M ~ c o r e } ^ { \mathfrak { 3 } } )$ ; otherwise $x \sim \mathrm { U n i f } [ - 0 . 5 , 0 . 5 ]$

• Maturity (strict 0DTE): we oversample the shortest maturities. With probability $p _ { \mathrm { s h o r t } } = 0 . 7$ we draw $\tau \sim \mathrm { U n i f } [ 1 0 ^ { - 4 } , 1 / 5 0 4 ] ;$ otherwise $\tau \sim \mathrm { U n i f } [ 1 / 5 0 4 , 1 / 2 5 2 ]$ . Here $p _ { \mathrm { s h o r t } }$ is the mixture weight for that oversampling step.

• Parameters are sampled uniformly over the following ranges:

$$
\begin{array} { r l r } & { } & { v _ { 0 } \in [ 0 . 0 1 , 0 . 2 ] , ~ \kappa \in [ 1 , 5 ] , ~ \theta \in [ 0 . 0 2 , 0 . 1 ] , } \\ & { } & { \sigma _ { v } \in [ 0 . 1 , 1 . 0 ] , ~ \rho \in [ - 0 . 9 , - 0 . 3 ] , ~ \lambda \in [ 0 . 1 , 2 . 0 ] , } \\ & { } & { \mu _ { J } \in [ - 0 . 2 , 0 . 0 ] , ~ \sigma _ { J } \in [ 0 . 0 5 , 0 . 5 ] . } \end{array}
$$

To stabilize jump-term training, we augment the sampled states by pushing points through the jump map $x \mapsto x + Y$ and clamping to $| x | \le 6$ . We compute reference prices on these jump-shifted $( ^ { \ast } \mathrm { { m a r g i n } ^ { \prime \prime } } )$ points and add a small auxiliary price-consistency loss. This extends supervision beyond $| x | \leq 0 . 5$ to the region visited by the jump integral. Deep OTM options have tiny prices and noisy Greeks, so we ignore Greek targets when the reference price is below $1 0 ^ { - 4 }$

We use $\omega _ { G } = 0 . 7 , \omega _ { R } = 0 . 0 1 , \omega _ { \mathrm { c o l } } = 0 . 1 , \omega _ { \mathrm { N A } } = 0 . 0 5 , \mathrm { a n d } \left( \omega _ { \Delta } , \omega _ { \Gamma } , \omega _ { \nu } \right) = \left( 1 . 0 , 0 . 3 , 0 . 5 \right)$ . We also set the self-consistency weight $\omega _ { \mathrm { S C } } = 0 . 0 5$ with $n _ { \mathrm { S C } } = 1 6$ . Finally, we set $( W _ { \mathrm { A T M } } , W _ { \mathrm { S H O R T } } , W _ { \mathrm { A T M } \& \mathrm { S H O R T } } ) =$ $( 1 . 0 , 1 . 0 , 1 . 0 )$

In the ultra-short regime, second derivatives are numerically unstable. We therefore (i) ignore deep-OTM Greek targets, (ii) use robust losses and/or clipping for sensitive targets (Γ and the jump term), and (iii) add no-arbitrage shape penalties, particularly convexity $( u _ { x x } - u _ { x } \ge 0 )$

## 5.2 Accuracy across models

We compare four models:

1. A (price-only): train on prices only (no Greek loss, no residual penalty).

2. B (DML): train on prices and Greeks (via automatic diferentiation), with no residual penalty.

3. C (DML+residual): train on prices, Greeks, and the residual penalty (13).

<!-- page: 7 -->

## 4. D (three-stage): three-stage training with jump supervision (Section 3.2).

We train the one-stage variants (Models A–C) for 100 epochs with Adam (learning rate $1 0 ^ { - 3 } )$ and batch size 64. The three-stage model uses 100 epochs (Stage 1), 60 epochs $\mathrm { ( S t a g e ~ 2 ) }$ , and 30 epochs (Stage 3). Table 1 reports global RMSE, and Table 2 reports RMSE in the region $| x | < 0 . 0 5$ and $\tau \leq 1 / 2 5 2$ . Residual statistics are in Table 3.

We additionally report scale-invariant metrics and tail error quantiles in Table 4. For price RMSE, we use two scale-free metrics:

$$
\mathrm { n R M S E } _ { P } : = \frac { \mathrm { R M S E } _ { P } } { \sqrt { \mathbb { E } [ ( u ^ { \mathrm { r e f } } ) ^ { 2 } ] } } , \qquad \mathrm { r e l R M S E } _ { P } : = \frac { \mathrm { R M S E } _ { P } } { \mathbb { E } [ u ^ { \mathrm { r e f } } ] } .
$$

For Greeks we use

$$
\mathrm { n R M S E } _ { \Delta } : = \frac { \mathrm { R M S E } _ { \Delta } } { \sqrt { \mathbb { E } [ ( \Delta ^ { \mathrm { r e f } } ) ^ { 2 } ] } } , \qquad \mathrm { n R M S E } _ { \Gamma } : = \frac { \mathrm { R M S E } _ { \Gamma } } { \sqrt { \mathbb { E } [ ( \Gamma ^ { \mathrm { r e f } } ) ^ { 2 } ] } } .
$$

The tail metrics $| e _ { P } | _ { p }$ and $| e _ { \Gamma } | _ { p }$ denote the p-th percentile of the absolute price and gamma errors, respectively. Tables 1–4 suggest three points. First, Model B improves delta accuracy (first-order risk) and vega accuracy relative to the price-only fit (Model A) (Table 1). For gamma Γ, improvements are clearer in tail error quantiles than in global RMSE (Table 4). Second, the one-stage PIDE residual penalty (Model C) does not improve prices or Greeks relative to Model B. This is consistent with jump models, where the residual can be reduced via cancellation between the diferential and jump terms rather than by learning an interpretable jump operator. Third, the three-stage model (Model D) yields the best overall $\Delta$ and vega RMSE among the Greek-supervised models and slightly improves Γ tail error quantiles, although Γ remains the most delicate target in the region $( | x | < 0 . 0 5 , \tau \le 1 / 2 5 2 )$

Figure 2 visualizes true vs predicted prices and Greeks for Model D. In the ultra-short maturity regime $( \tau 0 )$ , Γ is extremely localized around the money: for the majority of (deep ITM/OTM) evaluation points the true Γ is numerically close to zero, so the scatter plots naturally show a dense cluster at $\Gamma \approx 0$

## 5.3 Jump-term comparison

This subsection clarifies why a small PIDE residual alone is not evidence that the learned jump component represents the intended compensated jump integral. We first report error distributions for the final threestage model (Figure 3), and then directly test whether the learned compensated jump contribution $J _ { \psi }$ matches a numerical proxy computed from the reference pricer (Figure 4).

We focus on the domain $| x | \leq 0 . 5$ . Despite its small PIDE residual, the residual-regularized model C (DML+residual) without jump supervision shows a large mismatch between $J _ { \psi }$ and $J ^ { \mathrm { r e f } } \ ( \mathrm { R M S E } = 9 . 3 4 \times$ $1 0 ^ { - 2 } )$ . The three-stage model yields a smaller jump-term error $( \mathrm { R M S E } = 1 . 3 5 \times 1 0 ^ { - 2 } )$ . Price RMSE on the same points is comparable $\mathrm { { ( C \colon 7 . 1 7 \times 1 0 ^ { - 3 } } }$ , D: $5 . 8 9 \times 1 0 ^ { - 3 } )$ . Therefore, residual magnitude alone is not suficient for model selection when difusion and jump terms can ofset each other.

This indicates that when the jump contribution is a free network output, it can absorb approximation errors from the difusion part and still drive the residual toward zero. Supervising $J _ { \psi }$ against a numerical proxy (three-stage schedule) improves identification of the jump contribution.

## 5.4 One-day delta-hedging

The data-generating process is the Bates model, and we simulate $n _ { \mathrm { p a t h s } } = 5 0 0 0$ paths of $( S _ { t } , V _ { t } )$ over one trading day $T = 1 / 2 5 2$ using an Euler scheme with $n _ { \mathrm { s t e p s } } = 2 4$ . Jumps are simulated by a Bernoulli approximation with step probability $p \approx \lambda \Delta t$ . To avoid unrealistically large per-step jump probabilities when $\lambda \Delta t$ is not very small, we cap this probability at 0.2, i.e. we use $p = \operatorname* { m i n } ( \lambda \Delta t , 0 . 2 )$ . We use a stressed parameter set

$$
( v _ { 0 } , \kappa , \theta , \sigma _ { v } , \rho , \lambda , \mu _ { J } , \sigma _ { J } ) = ( 0 . 0 4 , 3 . 0 , 0 . 0 4 , 1 . 0 , - 0 . 8 , 2 . 0 , - 0 . 0 5 , 0 . 2 0 ) ,
$$

chosen to amplify jump activity and gamma efects. First, we conduct stock-only ∆ hedges, where the hedge portfolio contains the underlying and a cash account. We run the hedge separately for each strike $K \in \{ 0 . 9 , 1 . 0 , 1 . 1 \}$ on the same set of simulated $( S _ { t } , V _ { t } )$ paths, yielding 5000 P&L outcomes per strike. At $t = 0$ , we short one call with strike $K \in \{ 0 . 9 , 1 . 0 , 1 . 1 \}$ and maturity T. At each rebalance time $t _ { k } ,$ we

<!-- page: 8 -->

[Table source crop](assets/tables/2026-sakuma-dml-0dte-p0008-block-0001-eab4494b0842d636.jpg)
Table 1: RMSE (price and Greeks) on the validation set $( N = 5 0 0 , \mathrm { s e e d } { = } 4 2 )$

[Table source crop](assets/tables/2026-sakuma-dml-0dte-p0008-block-0002-0e8079eaed978e1d.jpg)
Table 2: RMSE in the strict short-dated ATM bucket $( | x | < 0 . 0 5 , \tau \le 1 / 2 5 2 )$ , computed on the validation sample (N = 500, seed=42).

[Table source crop](assets/tables/2026-sakuma-dml-0dte-p0008-block-0003-532f2fd8d84265db.jpg)
Table 3: Residual statistics of the PIDE check: mean absolute residual $\mathbb { E } | R |$ and $\operatorname { s d } ( R )$ Table 4: Normalized RMSEs and tail absolute errors (validation sample; $N = 5 0 0 .$ , seed=42).

[Table source crop](assets/tables/2026-sakuma-dml-0dte-p0008-block-0004-cc0f4d6f804f86f3.jpg)


[Table source crop](assets/tables/2026-sakuma-dml-0dte-p0008-block-0005-9bef2f2a7b955398.jpg)
Table 5: One-day ∆-hedging P&L summary.

Conditioning on whether at least one price jump occurs along the underlying path, we find much larger dispersion for the DML hedge on jump samples. Specifically, $\mathrm { s d ( P \& L _ { D M L } ) \approx 0 . 0 2 2 6 3 }$ on jump samples $( N = 1 5 0$ pooled path–strike observations) versus ≈ 0.00971 on no-jump samples $( N = 1 4 , 8 5 0 )$ This confirms that realized jumps substantially thicken the one-day hedge-P&L tails in this stressed experiment.

Second, we compare three one-option second-order hedges: (i) a ratio-type $\Delta + \Gamma$ hedge; (ii) a weighted ridge least-squares (LS) hedge that fits (∆, Γ) jointly across stock and one hedge option; and (iii) a P&Lincrement regression hedge (PL-LS) that learns state-dependent hedge ratios with ridge regularization.

<!-- page: 9 -->

![](assets/figures/2026-sakuma-dml-0dte-p0009-block-0001-85dada519d7fb817.jpg)

![Figure 2: Three-stage model: true vs predicted (price, delta, gamma, vega) on validation. (a) Price residuals ub <sup>−</sup> u.](assets/figures/2026-sakuma-dml-0dte-p0009-block-0002-96d075f3d7a157c1.jpg)

![(b) PIDE residual R(x) (three-stage). Figure 3: Error distributions for the three-stage model.](assets/figures/2026-sakuma-dml-0dte-p0009-block-0003-0560e0a3ebf16ae7.jpg)

Here “ratio-type” means that the hedge-option position is chosen from an explicit gamma ratio with ridge regularization, and the stock position is then set to neutralize the remaining delta. Such a hedge, using only one additional option, can be ill-conditioned when the hedge option’s gamma is small, because the hedge weight efectively scales like a ratio of gammas.

The LS and PL-LS hedges use the same instrument set but choose the positions jointly from a penalized

<!-- page: 10 -->

![(a) C (DML+residual)](assets/figures/2026-sakuma-dml-0dte-p0010-block-0001-521959ae77eefcef.jpg)

![(b) D (three-stage)](assets/figures/2026-sakuma-dml-0dte-p0010-block-0002-1a04fa6b7e50bde9.jpg)

![Figure 4: Jump-term check in the data domain $( | x | \leq 0 . 5 )$ : predicted compensated jump term vs numeric integral proxy. Figure 5: One-day ∆-hedging P&L (True vs DML delta), stressed Bates parameter regime.](assets/figures/2026-sakuma-dml-0dte-p0010-block-0003-84304e0fb59ce656.jpg)

fitting criterion or from a regression on price increments.

Concretely, for a given hedge strike $K _ { \mathrm { H } }$ , let $C _ { t } ^ { \mathrm { m a i n } }$ and $C _ { t } ^ { \mathrm { H } }$ denote the prices of the liability option and the hedge option, and let $( \Delta _ { t } ^ { \mathrm { m a i n } } , \Gamma _ { t } ^ { \mathrm { m a i n } } )$ and $( \Delta _ { t } ^ { \mathrm { H } } , \Gamma _ { t } ^ { \mathrm { \bar { H } } } )$ denote their spot Greeks. For the self-financing portfolio

$$
\Pi _ { t } = - C _ { t } ^ { \operatorname* { m a i n } } + w _ { \mathrm { H } , t } C _ { t } ^ { \mathrm { H } } + w _ { S , t } S _ { t } + B _ { t } ,
$$

the ratio-type $\Delta + \Gamma$ implementation updates the hedge-option position at each rebalance date by the ridgestabilized gamma match

$$
w _ { \mathrm { H } , t } = \frac { \Gamma _ { t } ^ { \mathrm { m a i n } } \Gamma _ { t } ^ { \mathrm { H } } } { ( \Gamma _ { t } ^ { \mathrm { H } } ) ^ { 2 } + \eta _ { \Gamma } } ,
$$

which approximates $\Gamma _ { t } ^ { \mathrm { m a i n } } / \Gamma _ { t } ^ { \mathrm { H } }$ when $| \Gamma _ { t } ^ { \mathrm { H } } |$ is not too small. The stock position is then chosen as

$$
w _ { S , t } = \Delta _ { t } ^ { \mathrm { m a i n } } - w _ { \mathrm { H } , t } \Delta _ { t } ^ { \mathrm { H } } ,
$$

so that the portfolio is approximately both delta- and gamma-neutral. At inception we set

$$
B _ { 0 } = C _ { 0 } ^ { \mathrm { m a i n } } - w _ { \mathrm { H } , 0 } C _ { 0 } ^ { \mathrm { H } } - w _ { S , 0 } S _ { 0 } ,
$$

<!-- page: 11 -->

and at each rebalance date update $( w _ { \mathrm { H } , t } , w _ { S , t } )$ and the cash account so that the strategy remains selffinancing. The weighted ridge LS hedge uses the same instrument pair $( S _ { t } , C _ { t } ^ { \mathrm { H } } )$ , but chooses (w<sub>S</sub>, w<sub>H</sub>) by minimizing

$$
\operatorname* { m i n } _ { w _ { S } , w _ { \mathrm { H } } } \ w _ { \Delta } ( \Delta _ { t } ^ { \mathrm { m a i n } } - w _ { S } - w _ { \mathrm { H } } \Delta _ { t } ^ { \mathrm { H } } ) ^ { 2 } + w _ { \Gamma } ( \Gamma _ { t } ^ { \mathrm { m a i n } } - w _ { \mathrm { H } } \Gamma _ { t } ^ { \mathrm { H } } ) ^ { 2 } + \lambda ( w _ { S } ^ { 2 } + w _ { \mathrm { H } } ^ { 2 } ) .
$$

PL-LS estimates time-dependent coeficient vectors $\left( A _ { k } , B _ { k } \right)$ from a ridge regression of option price increments $\Delta C _ { \mathrm { m a i n } }$ on basis-weighted $( \Delta S , \Delta C _ { \mathrm { h e d g e } } )$ and then sets the hedge using $w _ { S } = \phi ^ { \top } A _ { k }$ and $w _ { \mathrm { H } } = \phi ^ { \top } B _ { k }$ (with $\phi = [ 1 , \log m , ( \log m ) ^ { \bar { 2 } } , V , \tau ] ^ { \dot { \tau } } )$

We fix the liability option as a one-day ATM call with $K _ { \operatorname* { m a i n } } = 1 . 0 0$ and $T = 1 / 2 5 2$ . We then run four separate hedging experiments, each using the stock plus one additional same-maturity call with hedge strike $K _ { \mathrm { H } } \in \{ 0 . 9 9 , 1 . 0 0 , 1 . 0 1 , 1 . 0 2 \}$ . Figure 6 pools the resulting P&L observations across these four $K _ { \mathrm { H } }$ choices.

Figure 6 summarizes the comparison: the left column shows the central-region P&L density for the ratiotype $\Delta + \Gamma$ , LS, and PL-LS hedges, plotted separately for (top) true Greeks and (bottom) DML Greeks. The two central-density panels are visually similar at this scale, consistent with the close agreement between the DML and benchmark Greeks. In addition, our DML pricer outputs $( u , \Delta , \Gamma )$ in a single forward pass, so these quantities can be computed without re-pricing loops or finite diferences.

The right panel shows the tail of the ratio-type $\Delta + \Gamma$ hedge via the CCDF of |P&L|. LS and PL-LS are omitted on the right because their tails collapse near zero at this scale. Appendix A reports additional

![](assets/figures/2026-sakuma-dml-0dte-p0011-block-0007-0bc6d2154a342766.jpg)

![Figure 6: ∆ + Γ hedging illustration for a one-day ATM liability call $( K _ { \mathrm { m a i n } } = 1 . 0 0 )$ . In each run the hedge portfolio contains the stock and one additional one-day call at a single strike $K _ { \mathrm { H } } \in \{ 0 . 9 9 , 1 . 0 0 , 1 . 0 1 , 1 . 0 2 \}$ ; the four $K _ { \mathrm { H } }$ choices are run separately and the plotted distributions pool the resulting outcomes across them. Left: central-region density of hedging P&L for ratio-type $\Delta + \Gamma , \mathrm { L S }$ , and $\mathrm { P L } { \mathrm { - } } \mathrm { L S }$ , shown separately for (top) true Greeks and (bottom) DML Greeks. The two central-density panels are almost indistinguishable at this scale, reflecting that the DML Greeks are close to the benchmark. Right: tail behavior of the ratio-type $\Delta + \Gamma$ hedge, shown as the CCDF of $| \mathrm { P } \& \mathrm { L } |$ (true vs. DML) on log scales; a one-option gamma-based ratio hedge can become unstable when the hedge option’s gamma is near zero.](assets/figures/2026-sakuma-dml-0dte-p0011-block-0008-bdea1960b5b18345.jpg)

model-choice checks. In particular, a Merton jump-difusion baseline improves substantially over Black– Scholes when prices are generated under the Bates model, while an SVCJ extension with contemporaneous variance jumps is almost indistinguishable from the Bates model.

<!-- page: 12 -->

## 5.5 Calibration experiments

In the spirit of [Sridi and Bilokon(2023)] and [Polala and Hientzsch(2023)], we use the trained DML model as a fast pricing surrogate in calibration, but, for simplicity, calibrate only $\beta = ( v _ { 0 } , \theta , \lambda )$ while keeping the remaining parameters fixed. All calibration targets in this subsection are European calls with $S _ { 0 } = 1$ $r = 0 . 0 1 , q = 0$ , and strikes parameterized by log-moneyness $x = \log ( S _ { 0 } / K )$ . For a panel $\{ ( x _ { i } , \tau _ { i } , P _ { i } ^ { \mathrm { o b s } } ) \} _ { i = 1 } ^ { N } .$ we solve the weighted least-squares problem with L-BFGS-B

$$
\widehat { \beta } \ : = \ : \arg \operatorname* { m i n } _ { \beta \in \mathcal { B } } \sum _ { i = 1 } ^ { N } w _ { i } \ : \Big ( P ^ { \mathrm { m o d e l } } ( x _ { i } , \tau _ { i } ; \beta , \bar { \eta } ) - P _ { i } ^ { \mathrm { o b s } } \Big ) ^ { 2 } ,\tag{17}
$$

with $v _ { 0 } , \theta \in [ 0 . 0 0 5 , 0 . 5 ]$ and $\lambda \in [ 0 . 0 1 , 2 . 0 ]$ . Unless otherwise noted, we use

$$
w _ { i } = 3 ^ { 1 \{ | x _ { i } | < 0 . 1 \} } 3 ^ { 1 \{ \tau _ { i } < 1 / 2 5 2 \} }
$$

for the calibration weights. In Experiments 2–4, we also assign the short-maturity weight when $\tau _ { i } = 1 / 2 5 2$ Thus near-the-money calls receive weight 3, short-maturity calls receive weight 3, and calls satisfying both conditions receive weight 9.

Experiment 1. The call panel contains 68 prices with parameters $( v _ { 0 } , \theta , \lambda ) = ( 0 . 0 4 , 0 . 0 4 , 0 . 3 0 )$ . The calls lie on a log-moneyness grid $x \in [ - 0 . 5 , 0 . 5 ]$ with 17 equally spaced points and maturities $\tau \in \{ 0 . 2 5 , 0 . 5 0 , 0 . 7 5 , 1 . 0 0 \} / 2 5 2 .$ Replacing the direct Fourier pricer with the trained DML surrogate makes calibration about 90× faster. The surface fit remains accurate: the DML calibration yields price RMSE $1 . 5 3 \times 1 0 ^ { - 5 }$ , versus $1 . 2 3 \times 1 0 ^ { - 7 }$ for direct Fourier calibration. The fitted parameters, however, difer more noticeably. The DML calibration settles at $\hat { \lambda } = 0 . 2 0$ , while direct Fourier calibration recovers $\hat { \lambda } \approx 0 . 3 0$ . Even direct Fourier calibration does not recover the generating vector exactly, returning $\hat { \theta } = 0 . 0 5$ . On such a short-maturity panel, exact parameter recovery is therefore dificult even when pricing error is tiny, a point reinforced by the identification results in Experiment 3.

Experiment 2. We next examine how model misspecification manifests itself in calibration. The impliedvolatility surface is specified as

$$
\sigma _ { \mathrm { p m } } ( x , \tau ) = a ( \tau ) \bigl ( 1 - b ( \tau ) x + c ( \tau ) x ^ { 2 } \bigr ) ,
$$

with $a ( \tau ) = 0 . 1 8 + 0 . 0 3 e ^ { - 3 5 \tau } + 0 . 0 0 5 \sin ( 1 5 0 \tau ) , b ( \tau ) = 0 . 2 0 + 0 . 1 0 e ^ { - 1 5 \tau }$ , and $c ( \tau ) = 0 . 0 8 + 0 . 0 5 e ^ { - 2 0 \tau }$ . We convert this surface to call prices, floor volatilities at 5% and cap them at 100% pointwise, and then fit the Bates model by Fourier-pricer calibration under the box constraints in (17). Figure 7 shows structured residuals across moneyness and maturity. The fit pushes $\hat { \theta } \ \mathrm { t o }$ its lower bound 0.005, λ<sup>ˆ</sup> to its lower bound 0.01, and ˆv<sub>0</sub> to 0.0073. This pattern indicates that the optimizer suppresses both variance and jump activity in order to mimic a surface that lies outside the model class.

<!-- page: 13 -->

![Figure 7: Residual heatmap from Fourier pricer calibration to a smooth pseudo-market surface. We use 66 Black–Scholes calls on the grid $x \in \left[ - 0 . 2 5 , 0 . 2 5 \right]$ with 11 equally spaced points and $\tau \in$ {0.25, 0.50, 0.75, 1.00, 2.00, 5.00}/252.](assets/figures/2026-sakuma-dml-0dte-p0013-block-0001-8b09d320a25c76bf.jpg)

Experiment 3. Here we show how longer expiries improve identification of slower-moving stochasticvolatility parameters. Starting from (0.03, 0.03, 0.15), the 0DTE-only calibration recovers $( \hat { v } _ { 0 } , \hat { \theta } , \hat { \lambda } ) = ( 0 . 0 4 0 1 , 0 . 0 3 0 4 , 0 . 3 0 2 1 )$ By contrast, the mixed-expiry panel recovers (0.0400, 0.0600, 0.3000). Figure 8 reports the corresponding multistart results across six starting values, including (0.03, 0.03, 0.15). The 0DTE-only fits produce <sup>ˆ</sup>θ values in the range [0.019, 0.099], whereas the mixed-expiry fits concentrate in [0.059, 0.060].

![Figure 8: Calibrated θ across six starting values. We generate calls with parameters $( v _ { 0 } , \theta , \lambda ) \ =$ $( 0 . 0 4 , 0 . 0 6 , 0 . 3 0 )$ on the common grid $x \in [ - 0 . 2 5 , 0 . 2 5 ]$ with 11 equally spaced points. We compare a 44 0DTE-only panel with $\tau \in \{ 0 . 2 5 , 0 . 5 0 , 0 . 7 5 , 1 . 0 0 \} / 2 5 2$ against an 88 mixed-expiry panel that additionally includes $\tau \in \{ 2 . 0 0 , 5 . 0 0 , 1 0 . 0 0 , 2 0 . 0 0 \} / 2 5 2$](assets/figures/2026-sakuma-dml-0dte-p0013-block-0003-fd1c97fc31f80a8b.jpg)

<!-- page: 14 -->

Experiment 4. Inspired by the parameter-sensitivity supervision in [Zhang et al.(2025)], we consider a parameter-gradient extension focused on jump intensity. We train two DML networks on calls generated by the Bates model: one on prices only, and one on prices together with the price sensitivity with respect to λ. Letting $\xi _ { j }$ denote the full network input for training sample $j ,$ we train the sensitivity-augmented network with

$$
\mathcal { L } _ { \phi } ^ { ( \lambda ) } = \frac { 1 } { M } \sum _ { j = 1 } ^ { M } \left( \widehat { P } _ { \phi } ( \xi _ { j } ) - P _ { j } \right) ^ { 2 } + \omega _ { \lambda } \frac { 1 } { M } \sum _ { j = 1 } ^ { M } \left( \partial _ { \lambda } \widehat { P } _ { \phi } ( \xi _ { j } ) - g _ { j } ^ { ( \lambda ) } \right) ^ { 2 } ,\tag{18}
$$

where $\omega _ { \lambda } = 2 0$ and $g _ { j } ^ { ( \lambda ) }$ is the jump-intensity price-sensitivity label generated by automatic diferentiation. Calibration still solves weighted least squares in price space:

$$
\widehat { \lambda } = \arg \operatorname* { m i n } _ { \lambda \in [ 0 . 0 1 , 2 . 0 ] } \sum _ { i = 1 } ^ { N } w _ { i } \Big ( \widehat { P } _ { \phi } ( x _ { i } , \tau _ { i } ; \lambda ) - P _ { i } ^ { \mathrm { o b s } } \Big ) ^ { 2 } .\tag{19}
$$

Table 6 shows that Fourier pricer calibration recovers $\hat { \lambda } = 0 . 5 9 9 9 7$ for $\lambda _ { \mathrm { t r u e } } = 0 . 6 0$ . The price-only DML proxy overestimates jump intensity, yielding $\hat { \lambda } = 0 . 7 3 8 7 8$ , whereas the price+λ-sensitivity DML moves the estimate to $\hat { \lambda } \ : = \ : 0 . 5 6 8 8 9$ . We use the same mixed-expiry grid as Calibration Experiment 3 so that the jump-gradient calibration is not evaluated on a distinct expiry panel. The sensitivity-supervised surrogate does not exactly recover λ, but it materially reduces the absolute error from about 0.139 to about 0.031. For ultra-short maturities, λ is the parameter most directly tied to jump exposure, so supervising $\partial _ { \lambda } P$ appears helpful for calibrating that direction, even though it does not solve the full multi-parameter calibration problem by itself.

Table 6: Gradient-based calibration in the jump-intensity direction. The revised replication script uses the same mixed-expiry grid as Calibration Experiment 3, $\tau \in \{ 0 . 2 5 , 0 . 5 0 , 0 . 7 5 , 1 . 0 0 , 2 . 0 0 , 5 . 0 0 , 1 0 . 0 0 , 2 0 . 0 0 \} / 2 5 2$ with $x \in [ - 0 . 5 , 0 . 5 ]$ on 21 points.

[Table source crop](assets/tables/2026-sakuma-dml-0dte-p0014-block-0007-9a02e03657547d3c.jpg)


## 5.6 Extension to rough volatility

Here we ask whether the Bates/SVJD-B DML architecture can be extended to rough volatility. We replace the Markovian state $( s , v , \tau )$ with an M-factor Markovian approximation of rough volatility, so that the pricing network uses $( s , y _ { 1 } , \dotsc , y _ { M } , \tau )$ as input [Abi Jaber and El Euch(2019)]. Specifically, we approximate the fractional kernel

$$
K _ { H } ( t ) = \frac { t ^ { H - 1 / 2 } } { \Gamma ( H + 1 / 2 ) }\tag{20}
$$

by a finite sum of exponentials,

$$
K _ { H } ( t ) \approx K _ { M } ( t ) = \sum _ { m = 1 } ^ { M } c _ { m } e ^ { - \gamma _ { m } t }\tag{21}
$$

where the coeficients $c _ { m }$ are estimated by nonnegative least squares. Let

$$
\boldsymbol { u } = u ( s , y _ { 1 } , \ldots , y _ { M } , \tau ) , \qquad V ^ { M } ( y ) = v _ { 0 } + \sum _ { m = 1 } ^ { M } y _ { m } ,
$$

and define

$$
b _ { m } ( y ) = - \gamma _ { m } y _ { m } + c _ { m } \kappa ( \theta - V ^ { M } ( y ) ) .
$$

<!-- page: 15 -->

The M-factor rough difusion generator is

$$
\begin{array} { l } { { \displaystyle { \cal A } _ { M } ^ { \mathrm { r o u g h } } u = ( r - q ) s u _ { s } + \sum _ { m = 1 } ^ { M } b _ { m } ( y ) u _ { y _ { m } } + \frac { 1 } { 2 } V ^ { M } s ^ { 2 } u _ { s s } } } \\ { { \displaystyle ~ + \rho \xi V ^ { M } s \sum _ { m = 1 } ^ { M } c _ { m } u _ { s y _ { m } } + \frac { 1 } { 2 } \xi ^ { 2 } V ^ { M } \sum _ { m = 1 } ^ { M } c _ { m } c _ { \ell } u _ { y _ { m } y _ { \ell } } } . } \end{array}\tag{22}
$$

The jump-network target is the compensated price-jump operator per unit intensity,

$$
\mathcal { I } ^ { \mathrm { l a b e l } } ( s , y , \tau ) = \mathbb { E } _ { Z } \{ u ( s e ^ { Z } , y , \tau ) - u ( s , y , \tau ) \} - \kappa _ { J } s u _ { s } ( s , y , \tau ) , \qquad Z \sim N ( \mu _ { J } , \sigma _ { J } ^ { 2 } ) ,\tag{23}
$$

where $\kappa _ { J } = \mathbb { E } [ e ^ { Z } - 1 ]$ . The reference prices are computed using the rough-volatility variance-reduction method of McCrickerd and Pakkanen [McCrickerd and Pakkanen(2018)], combined with Merton’s lognormaljump mixture [Merton(1976)]. As in the Bates/SVJD-B experiment, Gauss–Hermite quadrature is used only to construct supervised labels for this compensated jump operator under the reference model.

The pricing-equation residual uses the learned jump block $\widehat { \mathcal { I } } _ { \phi } .$

$$
\mathcal { R } _ { \theta , \phi } ^ { M } = \partial _ { \tau } \widehat { u } _ { \theta } - \mathcal { A } _ { M } ^ { \mathrm { r o u g h } } \widehat { u } _ { \theta } - \lambda \widehat { \mathcal { I } } _ { \phi } + r \widehat { u } _ { \theta }\tag{24}
$$

and the price network is trained on inputs $( \log ( S / K ) , y _ { 1 } , \dots , y _ { M } , \tau )$ with a loss function similar to (13):

$$
\begin{array} { r } { \mathcal { L } _ { \mathrm { R H M } } = \mathcal { L } _ { \mathrm { p r i c e } } + \omega _ { \Delta } \mathcal { L } _ { \Delta } + \omega _ { \Gamma } \mathcal { L } _ { \Gamma } + \omega _ { J } \mathcal { L } _ { \mathrm { j u m p } } + \omega _ { R } \mathbb { E } \{ ( \mathcal { R } _ { \theta , \phi } ^ { M } ) ^ { 2 } \} + \omega _ { \mathrm { N A } } \mathbb { E } \left[ \mathcal { P } _ { \mathrm { N A } } ^ { M } ( x , y , \tau ) \right] . } \end{array}\tag{25}
$$

The term ${ \mathcal { L } } _ { \mathrm { j u m p } }$ trains the learned jump block $\hat { \mathcal { T } } _ { \phi }$ against (23) and $\mathcal { P } _ { \mathrm { N A } } ^ { M }$ denotes the rough-state analogue of the no-arbitrage penalty $\mathcal { P } _ { \mathrm { N A } }$ in (13), applied to the M-factor RHM-DML price surface $\widehat { u } _ { \theta } ( x , y , \tau )$

We generate a volatility surface from a higher-dimensional RHM with $( M , H ) \ = \ ( 1 2 , 0 . 0 7 )$ and fit Bates/SVJD-B, SVCJ, and a lower-dimensional RHM approximation with $( M , H ) = ( 4 , 0 . 1 0 )$ . Table 7 reports implied-volatility RMSEs under three calibration grids. The RHM-with-jumps specification attains the lowest implied-volatility RMSE in all three grids, supporting the interpretation that rough memory helps reproduce the shape of the implied-volatility surface when combined with jumps.

[Table source crop](assets/tables/2026-sakuma-dml-0dte-p0015-block-0012-d44a3cae362d3171.jpg)
Table 7: Implied-volatility errors. Calibration uses log $( S / K ) \ \in \ \{ - 0 . 1 8 , - 0 . 0 9 , 0 , 0 . 0 9 , 0 . 1 8 \}$ and the maturity grid indicated in the first column: $\mathrm { 0 D T E \mathrm { - } o n l y ~ = ~ \{ 0 . 2 5 , 0 . 5 0 , 0 . 7 5 , 1 . 0 0 \} / 2 5 2 , ~ 0 D T E \mathrm { + } 5 D ~ = ~ }$ $\{ 0 . 2 5 , 0 . 5 0 , 0 . 7 5 , 1 . 0 0 , 2 . 0 0 , 5 . 0 0 \} / 2 5 2$ , and mixed- $\mathrm { e x p i r y } = \{ 0 . 2 5 , 0 . 5 0 , 0 . 7 5 , 1 . 0 0 , 2 . 0 0 , 5 . 0 0 , 1 0 . 0 0 , 2 0 . 0 0 \} / 2 5 2 .$ The evaluation grid used to compute the errors is $\begin{array} { r } { \log ( S / K ) ~ \in ~ \{ - 0 . 1 4 , - 0 . 0 4 , 0 . 0 4 , 0 . 1 4 \} } \end{array}$ and $\tau \in$ {1.50, 5.00}/252.

Table 8 reports the accuracy of the finite-factor RHM-DML model under the residual-regularized DML framework. Price, delta, and jump-operator errors remain small, whereas gamma has the largest tail error because it is a second derivative concentrated around the 0DTE near-ATM region.

<!-- page: 16 -->

[Table source crop](assets/tables/2026-sakuma-dml-0dte-p0016-block-0001-3f526be371a9efcc.jpg)
Table 8: M-factor RHM-DML accuracy $( M = 4 )$ . Accuracy is measured against a conditional-Merton Monte Carlo reference model. The jump operator is the compensated per-unit-intensity jump contribution learned by $\hat { \mathcal { T } } _ { \phi }$

Table 9 reports results for terminal one-step delta hedges. We choose the initial delta at $t = 0$ and simulate $1 0 { , } 0 0 0$ terminal payofs for a one-day ATM call with $\tau = 1 / 2 5 2$ The Black–Scholes IV delta yields the smallest mean absolute P&L and RMSE, but the remaining tail losses indicate that a single stock-delta hedge cannot remove jump risk. Perfect hedging in rough Heston models is theoretically possible when the forward variance curve is available as a hedging instrument [El Euch and Rosenbaum(2018)]; more applied work formulates rough-volatility hedging through additional instruments or finite-factor partial hedging [Fukasawa et al.(2021), Motte and Hainaut(2024)]. Survey evidence also emphasizes that rough-volatility models may be valuable for pricing and risk management, but that practical implementation remains numerically and methodologically demanding [Hiraki and Shinozaki(2024)]. Rough models without jumps can struggle to reproduce wide-moneyness implied-volatility smiles, motivating a rough-plus-jump rather than a pure-rough comparison [Bandi et al.(2026)].

[Table source crop](assets/tables/2026-sakuma-dml-0dte-p0016-block-0003-69c8020757a66385.jpg)
Table 9: Terminal stock-delta hedging results. Mean $| P \& L |$ is the sample mean of absolute terminal hedge P&L; q95 and q99 denote the 95th and 99th percentiles of absolute terminal hedge P&L. The fitted deltas are evaluated using the model parameters calibrated from the 0DTE+5D row of Table 7. Bates/SVJD-B and SVCJ have identical rounded values. The M-factor RHM-DML delta reproduces the fitted RHM-MC delta.

## 6 Conclusion

We develop a diferential machine learning framework for 0DTE options under the Bates model. The method embeds the price in a Black–Scholes representation with a maturity-gated variance correction and combines joint price-and-Greek supervision with jump-aware PIDE regularization. Across the numerical experiments, the three-stage design improves identification of the jump term while keeping price accuracy competitive, delta and vega errors low, and inference substantially faster than the Fourier benchmark. The calibration exercises show both the value and the limits of the approach: the network is a useful fast surrogate inside weighted least-squares calibration, but short-dated panels can still sufer from misspecification and weak parameter identification. Supervising jump-intensity sensitivity further improves recovery in this direction, reducing the jump-intensity calibration error relative to a price-only surrogate. The framework can also be extended to rough volatility models through a multi-factor Markovian approximation. Future research will extend the framework from simulation to market data.

## Declaration of AI-assisted technologies

During the preparation of this manuscript, the author used generative AI and AI-assisted tools to assist with manuscript drafting, language refinement, code drafting and debugging, and discussion of the presentation

<!-- page: 17 -->

of the research. The author directed the project, reviewed, revised, and verified the manuscript and code, and takes full responsibility for the final manuscript.

## References

[Abi Jaber and El Euch(2019)] Abi Jaber, E. and El Euch, O. (2019). Multifactor approximation of rough volatility models. SIAM Journal on Financial Mathematics, 10(2):309–349. [Ackerer et al.(2020)] Ackerer, D., Tagasovska, N., and Vatter, T. (2020). Deep smoothing of the implied volatility surface. Advances in Neural Information Processing Systems, 33. [Bandi et al.(2023)] Bandi, F. M., Fusari, N., and Ren\`o, R. (2023). 0DTE Option Pricing. Working paper. Available at SSRN: https://ssrn.com/abstract=4503344 (doi:10.2139/ssrn.4503344). [Bandi et al.(2026)] Bandi, F. M., Fusari, N., Gazzani, G., and Ren\`o, R. (2026). Ultra-short-term volatility surfaces. arXiv preprint arXiv:2603.29430. [Bansal et al.(2026)] Bansal, S., Boro, P., and Natesan, S. (2026). Application of physics informed neural networks to partial integro-diferential equations in financial modeling and decision making. Applied Soft Computing, 186:114208. [Bates(1996)] Bates, D. S. (1996). Jumps and stochastic volatility: Exchange rate processes implicit in Deutsche mark options. The Review of Financial Studies, 9(1):69–107. [Black and Scholes(1973)] Black, F. and Scholes, M. (1973). The pricing of options and corporate liabilities. Journal of Political Economy, 81(3):637–654. [Boyle et al.(1997)] Boyle, P., Broadie, M., and Glasserman, P. (1997). Monte Carlo methods for security pricing. Journal of Economic Dynamics and Control, 21(8–9):1267–1321. [Broadie and Kaya(2006)] Broadie, M. and Kaya, O. (2006). Exact simulation of stochastic volatility and other afine jump difusion processes. Operations Research, 54(2):217–231. [Bozovic(2025)] Bozovic, M. (2025). Intraday Jumps and 0DTE Options: Pricing and Hedging Implications. Working paper. Available at SSRN: https://ssrn.com/abstract=5223127 (doi:10.2139/ssrn.5223127). [Carr and Madan(1999)] Carr, P. and Madan, D. B. (1999). Option valuation using the fast Fourier transform. Journal of Computational Finance, 2(4):61–73. [Dim et al.(2024)] Dim, C., Eraker, B., and Vilkov, G. (2024). 0DTEs: Trading, Gamma Risk and Volatility Propagation. Working paper. Available at SSRN: https://ssrn.com/abstract=4692190 (doi:10.2139/ssrn.4692190). [Dufie et al.(2000)] Dufie, D., Pan, J., and Singleton, K. (2000). Transform analysis and asset pricing for afine jump-difusions. Econometrica, 68(6):1343–1376. [El Euch and Rosenbaum(2018)] El Euch, O. and Rosenbaum, M. (2018). Perfect hedging in rough Heston models. The Annals of Applied Probability, 28(6):3813–3856. [Fukasawa et al.(2021)] Fukasawa, M., Horvath, B., and Tankov, P. (2021). Hedging under rough volatility. arXiv preprint arXiv:2105.04073. [Frandsen et al.(2022)] Frandsen, M. G., Pedersen, T. C., and Poulsen, R. (2022). Delta force: option pricing with diferential machine learning. Digital Finance, 4(1):1–15. [Fu and Hirsa(2020)] Fu, W. and Hirsa, A. (2020). An unsupervised deep learning approach to solving partial integro-diferential equations. arXiv preprint arXiv:2006.15012. [Glasserman(2004)] Glasserman, P. (2004). Monte Carlo Methods in Financial Engineering. Springer, New York.

<!-- page: 18 -->

[Heston(1993)] Heston, S. L. (1993). A closed-form solution for options with stochastic volatility with applications to bond and currency options. The Review of Financial Studies, 6(2):327–343. [Hiraki and Shinozaki(2024)] Hiraki, K. and Shinozaki, T. (2024). A survey of rough volatility. IMES Discussion Paper Series, 2024-E-06, Institute for Monetary and Economic Studies, Bank of Japan. [McCrickerd and Pakkanen(2018)] McCrickerd, R. and Pakkanen, M. S. (2018). Turbocharging Monte Carlo pricing for the rough Bergomi model. Quantitative Finance, 18(11):1877–1886. [Merton(1976)] Merton, R. C. (1976). Option pricing when underlying stock returns are discontinuous. Journal of Financial Economics, 3(1–2):125–144. [Huge and Savine(2020)] Huge, B. and Savine, A. (2020). Diferential machine learning. arXiv preprint arXiv:2005.02347. [Liu et al.(2019)] Liu, S., Oosterlee, C. W., and Bohte, S. M. (2019). Pricing options and computing implied volatilities using neural networks. Risks, 7(1):16. [Raissi et al.(2019)] Raissi, M., Perdikaris, P., and Karniadakis, G. E. (2019). Physics-informed neural networks: A deep learning framework for solving forward and inverse problems involving nonlinear partia diferential equations. Journal of Computational Physics, 378:686–707. [Motte and Hainaut(2024)] Motte, E. and Hainaut, D. (2024). Partial hedging in rough volatility models. SIAM Journal on Financial Mathematics, 15(3):601–652. [Polala and Hientzsch(2023)] Polala, A. K. and Hientzsch, B. (2023). Parametric diferential machine learning for pricing and calibration. arXiv preprint arXiv:2302.06682. [Sridi and Bilokon(2023)] Sridi, A. and Bilokon, P. (2023). Applying deep learning to calibrate stochastic volatility models. arXiv preprint arXiv:2309.07843. [Sun et al.(2025)] Sun, Q., Huang, H., Yang, X., and Zhang, Y. (2025). Stochastic jump difusion process informed neural networks for accurate American option pricing under data scarcity. Applied Soft Computing, 176:113164. [Zhang et al.(2025)] Zhang, C., Amici, G., and Morandotti, M. (2025). Calibrating the Heston model with deep diferential networks. Decisions in Economics and Finance. doi:10.1007/s10203-025-00558-1.

## A Model comparison

Because 0DTE options are extremely short-dated, it is natural to ask whether simpler dynamics would sufice for the pricing and hedging checks considered in this paper. This appendix reports two model-comparison checks: (i) Black–Scholes and Merton jump-difusion baselines versus the Bates model, and (ii) an SVCJtype extension with contemporaneous jumps in price and variance, specified within the afine jump-difusion framework of [Dufie et al.(2000)].

## A.1 Black–Scholes and Merton versus the Bates model

We use the Fourier pricer as a benchmark and compare two analytic baselines: (i) Black–Scholes with constant volatility $\sigma = \sqrt { v _ { 0 } }$ and no jumps, and (ii) Merton’s lognormal jump-difusion [Merton(1976)] with the same jump parameters $( \lambda , \mu _ { J } , \sigma _ { J } )$ and constant difusion volatility $\sqrt { v _ { 0 } }$ . The parameter set is the stressed regime used in the hedging experiment in the main text:

$$
( v _ { 0 } , \kappa , \theta , \sigma _ { v } , \rho , \lambda , \mu _ { J } , \sigma _ { J } ) = ( 0 . 0 4 , 3 . 0 , 0 . 0 4 , 1 . 0 , - 0 . 8 , 2 . 0 , - 0 . 0 5 , 0 . 2 0 ) ,
$$

with $r = 1 \%$ and $q = 0$

Merton’s jump-difusion substantially reduces pricing error relative to Black–Scholes (Table 10), indicating that even overnight options load on jump risk.

<!-- page: 19 -->

[Table source crop](assets/tables/2026-sakuma-dml-0dte-p0019-block-0001-31cf98b1df42db25.jpg)
Table 10: Pricing error of Black–Scholes and Merton relative to Bates benchmark prices, evaluated on a 164- point (x, τ) grid. The second column reports RMSE on the core short-dated bucket $( | x | < 0 . 0 5 , \ \tau \le 1 / 2 5 2 )$ (92 grid points, including repeated endpoints).

We also run a one-day discrete-time ∆ hedge under simulated Bates dynamics (using the same setup as Section 5.4) and compute hedge deltas using BS, Merton, and the Bates model. Table 11 reports summary statistics, both unconditionally and conditional on whether at least one jump occurs along the path. Jump realizations dominate tail outcomes and cannot be hedged away by delta hedging; diferences across delta models are therefore small relative to jump-driven tail risk in this setup.

## A.2 SVCJ vs Bates: do volatility jumps matter for 0DTE?

To assess whether volatility jumps matter for 0DTE options, we consider an SVCJ-type extension (stochastic volatility with contemporaneous jumps in price and variance) in which price and variance jump simultaneously at Poisson times. Within the afine jump-difusion framework of [Dufie et al.(2000)], we specify the log-price jump as $Y \sim \mathcal { N } ( \mu _ { J } , \sigma _ { J } ^ { 2 } )$ and the variance jump as $Z \sim { \mathrm { E x p } } ( { \mathrm { m e a n } } = \mu _ { v J } ) $ , with Z independent of Y but arriving with the same intensity λ. We set $\mu _ { v J } = 0 . 0 2$ (a positive variance-jump mean), and keep $( v _ { 0 } , \kappa , \theta , \sigma _ { v } , \rho , \lambda , \mu _ { J } , \sigma _ { J } )$ equal to the stressed regime above. Table 12 shows that the incremental pricing efect of adding variance jumps is small. For very short maturities, vega exposure is limited; variance jumps can therefore be weakly identified unless longer expiries are included in calibration/training. The evaluation grid here uses four same-day maturity slices, $\tau \in \{ 0 . 2 5 , 0 . 5 0 , 0 . 7 5 , 1 . 0 0 \} \times ( 1 / 2 5 2 )$ . Accordingly, the metric “ATM” aggregates all grid points with $| x | < 0 . 1$ across all four slices, whereas “ATM+short” additionally imposes $\tau < 1 / 2 5 2$ , i.e. it retains only the first three slices.

We conduct one-day delta hedging under simulated SVCJ dynamics and compare hedges based on Bates vs SVCJ deltas. Table 13 shows that the P&L distributions are very similar at the reported precision.

<!-- page: 20 -->

[Table source crop](assets/tables/2026-sakuma-dml-0dte-p0020-block-0001-db60cafce2b3d17c.jpg)
Table 11: One-day discrete-time ∆-hedging P&L under simulated Bates dynamics. “jump” means the path contains at least one price jump during the day; “no-jump” means no price jump occurs. The last column reports a nonparametric 95% bootstrap CI for CVaR <sub>%</sub>.

[Table source crop](assets/tables/2026-sakuma-dml-0dte-p0020-block-0002-9dbab6ac403dc675.jpg)
Table 12: Incremental pricing efect of adding variance jumps, reported as the price diference $C ^ { \mathrm { S V C J } } - C ^ { \mathrm { B a t e s } }$ and summarized by its RMSE over several evaluation subsets $( \mu _ { v J } = 0 . 0 2 )$ . All metrics are evaluated on the same 164-point (x, τ) grid.

[Table source crop](assets/tables/2026-sakuma-dml-0dte-p0020-block-0003-9c17f81a9b2caaf6.jpg)
Table 13: One-day ∆-hedging P&L under simulated SVCJ dynamics: summary statistics comparing deltas from Bates vs SVCJ (negative values indicate profit). The last column reports a nonparametric 95% bootstrap CI for $\mathrm { C V a R _ { 1 \% } }$
