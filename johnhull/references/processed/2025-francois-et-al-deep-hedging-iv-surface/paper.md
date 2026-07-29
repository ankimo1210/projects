# 2025-francois-et-al-deep-hedging-iv-surface

<!-- page: 1 -->

## Deep Hedging with Options Using the Implied Volatility Surface

Pascal Françoisa, Geneviève Gauthierb, Frédéric Godin†,c

Carlos Octavio Pérez-Mendozac

aDepartment of Finance, HEC Montréal, Montreal, Canada

bGERAD and Department of Decision Sciences, HEC Montréal, Montreal, Canada

Concordia University, Department of Mathematics and Statistics, Montreal, Canada

August 14, 2025

## Abstract

We propose a deep hedging framework for index option portfolios, grounded in a realistic market simulator that captures the joint dynamics of S&P 500 returns and the full implied volatility surface. Our approach integrates surface-informed decisions with multiple hedging instruments and explicitly accounts for transaction costs. The hedging strategy also considers the variance risk premium embedded in the hedging instruments, enabling more informed and adaptive risk management. Tested on a historical outof-sample set of straddles from 2020 to 2023, our method consistently outperforms traditional delta-gamma hedging strategies across a range of market conditions.

JEL classification: C45, C61, G32.

Keywords: Deep reinforcement learning, optimal hedging, implied volatility surfaces.

ar 2023[a- :000

\*François is supported by a fellowship from the Canadian Institute of Derivatives. Gauthier is supported by the Natural Sciences and Engineering Research Council of Canada (NSERC, RGPIN-2024-03791), a professorship funded by HEC Montréal, and the HEC Montréal Foundation. Godin is funded by NSERC (RGPIN-2024-04593).

†Corresponding author. Email: frederic.godin@concordia.ca.

<!-- page: 2 -->

## 1 Introduction

Hedging decisions are inherently tied to the information available at the time they are made. Traditional approaches typically rely on dynamics of the underlying asset, which are estimated on historical data. Some studies extend this framework by incorporating localized information from the implied volatility (IV) surface, such as at-the-money or short-term implied volatilities (Bates, 2005; Alexander and Nogueira, 2007; François and Stentoft, 2021). In this paper, we address the hedging problem for an index option portfolio using a richer set of information—namely, characteristics of the full implied volatility surface. By exploiting the structure of the entire surface, we aim to better capture market expectations and variance dynamics.

Capturing such information at each decision point increases the dimensionality of the state vector. This makes reinforcement learning (RL) a natural choice for identifying optimal hedging strategies. Deep hedging, introduced by Buehler et al. (2019), leverages deep reinforcement learning to dynamically adapt to evolving market conditions, capturing both shifting expectations and historical patterns. While this approach has shown remarkable flexibility and adaptability (e.g., Du et al. (2020), Cao et al. (2020), Carbonneau (2021), Wu and Jaimungal (2023), Cao et al. (2023)), the training of the neural network requires a market simulator. François et al. (2024) demonstrate that deep hedging strategies can effectively mitigate transaction costs while incorporating information from the implied volatility (IV surface. Their study, however, focuses on the hedging of European options using only the underlying asset. The potential benefits of expanding the hedging set to include additional instruments, alongside IV-informed policies, remain unexplored.

<!-- page: 3 -->

We build on the framework introduced by François et al. (2024), extending it to address the risk management of index option portfolios through the inclusion of an additional hedging instrument. This extension introduces significant challenges, both computational and conceptual. First, the state vector requires further information about the additional hedging instrument and the portfolio to be hedged. Second, to ensure that the RL agent learns a true hedging strategy rather than engaging in speculative behavior, we introduce penalty terms in the reward function that discourages excessive risk-taking. This design helps steer the agent toward strategies that align with the core objective of minimizing portfolio risk in a realistic trading environment.

Our study is distinctive in that it simultaneously leverages rich information derived from the implied volatility surface and its dynamics, explicitly accounts for transaction costs—which are particularly significant when trading options—and departs from traditional portfolio tracking by adopting a global hedging objective focused on minimizing terminal hedging error.

Numerical results for hedging a short position on a straddle show that all our RL algorithms consistently and substantially outperform the practitioner's delta and delta-gamma approaches. In some cases, the RL agent relying only on the underlying as the hedging instrument even outperforms delta-gamma hedging: this happens in particular in the presence of transaction costs when a tail risk performance metric is considered.

The outperformance of RL approaches can be attributed to several factors. First, RL strategies typically rely on smaller trades. This more gradual rebalancing reduces the likelihood of having to unwind large positions shortly after they are established. Second, the early-stage divergence between RL and delta-gamma positions reflects the RL agent's deliberate efforts to limit short exposure to the variance risk premium embedded in the option used for hedging. Thanks to our enriched informational state vector, the RL agent learns and adapts to the time-varying variance risk premium, which is a key driver of hedging costs. The impact of risk premia materializes over the long term and is therefore not captured by myopic Greeks-based approaches.

<!-- page: 4 -->

As the model is trained on market data from 1996 to 2020, we use recent option data from 2021 to 2023 to evaluate whether our trained RL algorithm maintains its performance out-of-sample. For this backtesting study, we introduce a new benchmark: the RL algorithm without IV information. We demonstrate the superiority of the RL algorithms with the full information over both the practitioners' delta-gamma strategy and the RL algorithms with limited information. The RL algorithms without IV information do not outperform the practitioners' delta-gamma approach in terms of mean squared hedging errors. These results highlight the importance of feeding relevant market information to the RL hedging agent. The paper is organized as follows. Section 2 frames the hedging problem in terms of a deep reinforcement learning framework. Section 3 provides the components of the market simulator. Section 4 presents the numerical results.1 Section 5 presents the out-of-sample backtesting results. Section 6 concludes.

1The Python code to replicate the numerical experiments from this paper can be found at the following link: https://github.com/cpmendoza/deep-hedging\_with\_options.git.

<!-- page: 5 -->

## 2 Deep hedging framework

In this section, we present the mathematical formulation of the hedging problem, along with the computational scheme to obtain the numerical solution.

## 2.1 The hedging problem

We propose dynamic hedging strategies for managing portfolios of options. Our approach focuses on minimizing a risk measure applied to terminal hedging error while considering variable market conditions and accounting for transaction costs.

The goal is to hedge a short position in a portfolio of contingent claims written on the same underlying asset, S, over the hedging period $0 , \ldots , T$ . The time-t market value of the portfolio is denoted $\mathcal { P } _ { t }$ . For illustrative purposes, our numerical examples use a European straddle portfolio with maturity $T .$ In this case, the value $\mathcal { P } _ { T }$ represents the portfolio's terminal payoff, which is given by the mapping $\Psi _ { T } ( S _ { T } ) = \mathrm { m a x } ( S _ { T } - K , 0 ) + \mathrm { m a x } ( K - S _ { T } , 0 )$ with K being the strike price

The hedging strategy involves managing a self-financing portfolio composed of the risk-free asset, the underlying asset, and a hedging option. Specifically, the hedging option is a European option on the same underlying asset with a longer maturity $T ^ { * } > T$ . The strategy is represented by the predictable process $\{ \phi _ { t } \} _ { t = 1 } ^ { T } ,$ with $\phi _ { t } = ( \phi _ { t } ^ { ( r ) } , \phi _ { t } ^ { ( S ) } , \phi _ { t } ^ { ( \mathrm { O } ) } )$ , where $\phi _ { t } ^ { ( r ) }$ is the cash held at time t — 1 and carried forward to the next period. Moreover, $\phi _ { t } ^ { ( S ) }$ and $\phi _ { t } ^ { \mathrm { ( O ) } }$ are respectively the number of shares of the underlying asset $S$ and the number of hedging options in the hedging portfolio, both held during the interval $( t - 1 , t ]$ . The time-t hedging

<!-- page: 6 -->

portfolio value is

$$
V _ { t } ^ { \phi } = \phi _ { t } ^ { ( r ) } \mathrm { e } ^ { r _ { t } \Delta } + \phi _ { t } ^ { ( S ) } S _ { t } \mathrm { e } ^ { q _ { t } \Delta } + \phi _ { t } ^ { ( \mathrm { O } ) } \mathrm { O } _ { t } ( T ^ { * } )
$$

where $\mathrm { O } _ { t } ( T ^ { * } )$ is the time-t hedging option value, $\Delta = { \frac { 1 } { 2 5 2 } }$ represents the time increment in years, $r _ { t }$ is the time-t annualized continuously compounded risk-free rate and $q _ { t }$ is the annualized underlying asset dividend yield, both on the interval $( t - 1 , t ]$ . To account for transaction costs the self-financing condition entails that for $t = 0 , \ldots , T - 1$

$$
\phi _ { t + 1 } ^ { ( r ) } + \phi _ { t + 1 } ^ { ( S ) } S _ { t } + \phi _ { t + 1 } ^ { ( C ) } \Omega _ { t } ( T ^ { * } ) = V _ { t } ^ { \phi } - \kappa _ { 1 } S _ { t } \mid \phi _ { t + 1 } ^ { ( S ) } - \phi _ { t } ^ { ( S ) } \mid - \kappa _ { 2 } \Omega _ { t } ( T ^ { * } ) \mid \phi _ { t + 1 } ^ { ( 0 ) } - \phi _ { t } ^ { ( 0 ) } \mid \phi _ { t } ^ { ( 0 ) }\tag{1}
$$

where $\kappa _ { 1 }$ and $\kappa _ { 2 }$ represent the proportional transaction cost rates for the underlying asset and the hedging option, respectively. Transaction costs for options are typically higher than those for the underlying asset. Consequently, we assume $\kappa _ { 1 } < < \kappa _ { 2 }$

The optimal sequence of actions $\phi = \{ \phi _ { t } \} _ { t = 1 } ^ { T }$ corresponds to that which minimizes the application of a risk measure $\rho$ to $\xi _ { T } ^ { \phi }$ , the hedging error at maturity for a short position in the option portfolio:

$$
\xi _ { T } ^ { \phi } = \mathcal { P } _ { T } - V _ { T } ^ { \phi } .
$$

A positive value in $\xi _ { T } ^ { \phi }$ implies that the hedging strategy does not have enough funds to cover the portfolio value $\mathcal { P } _ { T }$ . Our goal is to find the hedging strategy $\phi ^ { * }$ such that

$$
\phi ^ { * } = \arg \operatorname* { m i n } _ { \phi } \left\{ \rho \left( \xi _ { T } ^ { \phi } \right) \right\} .\tag{2}
$$

Each time-t action $\phi _ { t + 1 }$ is a function of currently available information on the market:

<!-- page: 7 -->

$\phi _ { t + 1 } = \tilde { \phi } ( X _ { t } )$ for some function $\tilde { \phi }$ of the state variables vector $X _ { t }$ . Due to Equation $( 1 ) , \phi _ { t + 1 } ^ { ( r ) }$ is fully determined when $\phi _ { t + 1 } ^ { ( S ) }$ and $\phi _ { t + 1 } ^ { \mathrm { ( O ) } }$ are specified, and as such the time-t action to be chosen is $( \phi _ { t + 1 } ^ { ( S ) } , \phi _ { t + 1 } ^ { ( \mathrm { O } ) } )$ 1

This paper examines three widely recognized risk measures in the literature:

• Mean Square Error (MSE): $\rho \left( \xi _ { T } ^ { \phi } \right) = \mathbb { E } \left[ \left( \xi _ { T } ^ { \phi } \right) ^ { 2 } \right]$

• Semi Mean-Square Error (SMSE): $\rho \left( \xi _ { T } ^ { \phi } \right) = \mathbb { E } \left[ \left( \xi _ { T } ^ { \phi } \right) ^ { 2 } \mathbb { 1 } _ { \{ \xi _ { T } ^ { \phi } \geq 0 \} } \right]$

• Conditional Value-at-Risk $\left( \mathrm { C V a R } _ { \alpha } \right) : \rho \left( \xi _ { T } ^ { \phi } \right) = \mathbb { E } \left[ \xi _ { T } ^ { \phi } \middle | \xi _ { T } ^ { \phi } \geq \mathrm { V a R } _ { \alpha } \left( \xi _ { T } ^ { \phi } \right) \right]$ , where $\mathrm { V a R } _ { \alpha } \left( \xi _ { T } ^ { \phi } \right)$ is the Value-at-Risk defined as VaRα $\begin{array} { r } { \left( \xi _ { T } ^ { \phi } \right) = \operatorname* { m i n } _ { c } \left\{ c : \mathbb { P } \left( \xi _ { T } ^ { \phi } \leq c \right) \geq \alpha \right\} } \end{array}$ , and $\alpha \in ( 0 , 1 )$

## 2.2 Reinforcement learning and deep hedging

The problem described in Equation (2) is addressed by directly estimating the policy function (the investment strategy $\tilde { \phi } )$ using a policy gradient method. This approach leverages a parametric representation of the policy function through an Artificial Neural Network (ANN). Specifically, the policy $\tilde { \phi } ,$ governed by a parameter vector $\theta ,$ is optimized to minimize the risk measure $\rho$ evaluated at the terminal hedging error. Representing the policy generated by the ANN as $\tilde { \phi } _ { \theta }$ , the hedging strategy is defined as $\phi _ { t + 1 } = \tilde { \phi } _ { \theta } ( X _ { t } )$ . Problem (2) can therefore be approximated as

$$
\arg \operatorname* { m i n } _ { \theta } \left\{ \rho \left( \xi _ { T } ^ { \tilde { \phi } _ { \theta } } \right) \right\} .\tag{3}
$$

Given the inherent continuity of ANNs, the mapping $\phi _ { t + 1 } = \tilde { \phi } _ { \theta } ( X _ { t } )$ may lead to frequent small adjustments in the hedging position, potentially increasing long-term transaction costs. To mitigate this effect, we introduce a no-trade region, within which there is no rebalancing In practice, the no-trade region has a negligible impact on the performance of the ANN, but it improves the results of our benchmark strategies. Further details are provided in Appendix A.

<!-- page: 8 -->

As shown in François et al. (2024), the policy $\tilde { \phi } _ { \theta }$ may inadvertently incorporate speculative elements, such as doubling strategies, where agents continuously increase their exposure in an attempt to recover successive losses. Such strategies are undesirable as they deviate from sound risk management principles. To prevent this problem, we introduce a soft tracking error constraint

$$
S C ( \theta ) = \mathbb { P } \left( \operatorname* { m a x } _ { t \in \{ 0 , . . . , T \} } \left\{ \xi _ { t } ^ { \tilde { \phi } _ { \theta } } \right\} > V _ { 0 } \right)\tag{4}
$$

that penalizes the network during training if the time-t tracking error,

$$
\xi _ { t } ^ { \tilde { \phi } _ { \theta } } = \mathcal { P } _ { t } - V _ { t } ^ { \tilde { \phi } _ { \theta } } ,\tag{5}
$$

exceeds the initial hedging portfolio value at any time t. This design does not penalize gains, consistent with the asymmetric nature of rational agents. As a result, instead of solving Problem (3), the objective function employed in our approach is

$$
\mathcal { O } ( \theta ; \lambda ) = \rho \left( \xi _ { T } ^ { \tilde { \phi } _ { \theta } } \right) + \lambda S C ( \theta ) ,\tag{6}
$$

where λ is a hyperparameter that controls the soft constraint weight in the optimization process. It is determined independently using a validation set during the model selection procedure.

We employ a Recurrent Neural Network with a Feedforward Connection (RNN-FNN), integrating Long Short-Term Memory (LSTM) networks with Feedforward Neural Network (FFNN) architectures. This hybrid design has demonstrated superior training performance compared to conventional ANN architectures, as shown in Fecamp et al. (2020) and François et al. (2024). The RNN-FNN network is defined as a composition of LSTM cells $\{ C _ { l } \} _ { l = 1 } ^ { L _ { 1 } }$ and FFNN layers $\{ \mathcal { L } _ { j } \} _ { j = 1 } ^ { L _ { 2 } }$ under the following functional representation:

<!-- page: 9 -->

$$
\tilde { \phi } _ { \boldsymbol { \theta } } ( X _ { t } ) = ( \underbrace { \mathcal { L } _ { J } \circ \mathcal { L } _ { L _ { 2 } } \circ \mathcal { L } _ { L _ { 2 } - 1 } \circ \ldots \circ \mathcal { L } _ { 1 } } _ { \mathrm { F F N N ~ l a y e r s ~ } } \circ \underbrace { C _ { L _ { 1 } } \circ C _ { L _ { 1 } - 1 } \ldots \circ C _ { 1 } } _ { \mathrm { L S T M ~ c e l l s ~ } } ) ( X _ { t } ) .
$$

The explicit formulas for this ANN are detailed in François et al. (2024).

## 2.3 Neural network optimization

The RNN-FNN network $\tilde { \phi } _ { \theta } ( \cdot )$ is optimized with the Mini-batch Stochastic Gradient Descent method (MSGD). This training procedure relies on updating iteratively all the trainable parameters of the optimization problem based on the recursive equations

$$
\theta _ { j + 1 } = \theta _ { j } - \eta _ { j } \frac { \partial } { \partial \theta } \hat { \mathcal { O } } ( \theta ; \lambda ) ,\tag{7}
$$

where $\eta _ { j }$ are the learning rates that determine the magnitude of change of parameters per time step. These rates are dynamically adjusted using the Adam optimization algorithm.2 Additionally, $\hat { \mathcal { O } } ( \theta ; \lambda )$ is the Monte-Carlo estimate of the objective function defined by Equation (6). Further details can be found in Appendix B.

2Adam is an adaptive learning rate method designed to accelerate training in deep neural networks and promote rapid convergence, as detailed in Kingma and Ba (2015).

<!-- page: 10 -->

## 3 Market simulator

Our approach incorporates a market simulator to emulate the joint dynamics of the S&P 500 price and of its associated IV surface. Indeed, optimal actions are characterized by the behavior of the underlying asset and the hedging instrument prices. Using a simulator provides the advantage of generating a large diversity of scenarios, enabling RL agents to explore the state space while identifying optimal policies. This alleviates the issue of scarcity in real market data.

We leverage the JIVR model from François et al. (2023), which captures the temporal dynamics of S&P 500 returns alongside the key drivers of the IV surface, while accounting for their interdependencies. The JIVR framework works with interpretable factors and enables the replication of a wide range of realistic IV surface shapes observed in practice.3 The market simulator has been estimated using a daily dataset of observed implied volatilities—covering a broad range of moneyness and time-to-maturity—alongside S&P 500 returns from 1996 to 2020; it can therefore reflect a broad array of market conditions. It captures the self-contained properties of the option market, consistently with the "instrumental approach" of option pricing detailed in Rebonato (2005).

3Other approaches could be pursued to generate IV surface scenarios, such as generative AI models detailed in Chen et al. (2023), Choudhary et al. (2024) and Vuletić and Cont (2024).

<!-- page: 11 -->

## 3.1 Daily implied volatility surfaces

The time-t IV associated to an option with time-to-maturity $\begin{array} { r } { \tau _ { t } = \frac { T - t } { 2 5 2 } } \end{array}$ years and (scaled) moneyness $\begin{array} { r } { M _ { t } = \frac { 1 } { \sqrt { \tau _ { t } } } \log \frac { S _ { t } e ^ { ( r _ { t } - q _ { t } ) \tau _ { t } } } { K } } \end{array}$ is modeled as

$$
\sigma ( M _ { t } , \tau _ { t } , \beta _ { t } ) = \sum _ { i = 1 } ^ { 5 } \beta _ { t , i } f _ { i } ( M _ { t } , \tau _ { t } ) .\tag{8}
$$

The vector $\beta _ { t } = ( \beta _ { t , 1 } , \beta _ { t , 2 } , \beta _ { t , 3 } , \beta _ { t , 4 } , \beta _ { t , 5 } )$ represents the IV factor coefficients at time t, while the functions $\{ f _ { i } \} _ { i = 1 } ^ { 5 }$ allow representing the long-term at-the-money (ATM) level, the timeto-maturity slope, the moneyness slope, the smile attenuation, and the smirk, respectively. A detailed description of the functional components $\{ f _ { i } \} _ { i = 1 } ^ { 5 }$ of the IV surface can be found in Appendix C.1.

## 3.2 Joint implied volatility and return

The JIVR model introduced by François et al. (2023) builds upon the IV representation (8), offering an explicit formulation for the joint dynamics of the IV surface and the S&P 500 price. This joint representation is based on an econometric model for (i) the underlying asset returns, and (ii) fluctuations of the IV surface coefficients $\beta _ { t }$ along with a mean-reversion component for their volatilities $h _ { t }$ . The multivariate time series of the JIVR model is provided in Appendix C.2.

The JIVR model is used to generate paths of the state variables $( S _ { t } , \{ \beta _ { t , i } \} _ { i = 1 } ^ { 5 } , h _ { t , R } , \{ h _ { t , i } \} _ { i = 1 } ^ { 5 } )$ 2 which drive the market dynamics, where $h _ { t , R }$ and $\{ h _ { t , i } \} _ { i = 1 } ^ { 5 }$ are volatilities for the S&P 500 and each of the IV factors. Estimates of the model parameters and volatility series $\{ \hat { h } _ { t , i } \} _ { t = 1 } ^ { N }$ 1

<!-- page: 12 -->

with $i \in \{ 1 , \ldots , 5 , R \}$ are taken from François et al. (2023).⁴

## 4 Numerical study

## 4.1 Market settings for numerical experiments

We consider daily trading periods. For each simulated path, initial conditions of the JIVR model, $( \{ \beta _ { 0 , i } \} _ { i = 1 } ^ { 5 } , h _ { 0 , R } , \{ h _ { 0 , i } \} _ { i = 1 } ^ { 5 } )$ , are randomly sampled from the daily estimated values in our data set, covering the period from January 4, 1996, to December 31, 2020. Across all experiments, the annualized continuously compounded risk-free rate and dividend yield are assumed to remain constant, with values fixed at $r = 2 . 6 6 \%$ and $q = 1 . 7 7 \%$ , respectively.5 Without loss of generality, the initial value of the underlying asset is set to $S _ { 0 } = 1 0 0 . ^ { 6 }$ The hedged portfolio is an ATM straddle with a maturity of $T = 6 3$ days. At any time $t < T$ , the portfolio value $\mathcal { P } _ { t }$ is determined using the IV surface prevailing at that moment.

The hedging instruments are the risk-free asset, the underlying asset, and an option with a maturity longer than that of the straddle—specifically, an ATM European call option with an initial maturity of $T ^ { * } = 8 4$ days. Positions in all hedging instruments are rebalanced daily. The hedge follows the self-financing dynamics from Equation (1), incorporating proportional transaction costs on both the underlying asset and the hedging option. As reported in Chaudhury (2019), the average cost for S&P 500 index call options is 0.95%. To evaluate its impact, we consider $\kappa _ { 2 } \in \{ 0 . 5 \% , 1 \% , 1 . 5 \% , 2 \% \}$ . In contrast, transaction costs for the underlying asset are negligible, around 0.047% according to Bazzana and Collini (2020). We set $\kappa _ { 1 } = 0 . 0 5 \%$ . The initial hedging portfolio value matches the straddle price, i.e., $V _ { 0 } = P _ { 0 }$

4François et al. (2023) use a maximum likelihood approach on a multivariate time series made of S&P 500 returns and surface coefficients estimates {βt}t=1, with sample dates extending between January 4, 1996 and December 31, 2020.

5The annualized rates of the S&P 500 dividend yield (1.77%) and the zero-coupon yield (2.66%) are calculated as the average over the sample period from January 4, 1996, to December 31, 2020, using OptionMetrics data.

6In our setting, the value of the portfolio to be hedged is proportional to the underlying asset initial value.

<!-- page: 13 -->

## 4.2 Benchmarks

We benchmark the performance of our framework against several established approaches: (i) the RL method proposed by François et al. (2024), which incorporates IV-informed decisions using only the underlying asset as a hedging instrument, (ii) delta hedging (D), where only the underlying asset is used for hedging, and (ii) delta-gamma (DG) hedging, which includes the additional hedging option in the portfolio.

For the second and third benchmarks, the delta and gamma of financial instruments are computed using the practitioner's approach, i.e., using the current IV value. In the case of delta hedging, the delta is adjusted based on the correction introduced by Leland (1985), which accounts for the impact of proportional transaction costs on the underlying asset position. In both benchmarks, the volatility parameter is updated daily according to the prevailing IV surface, which aligns the hedging strategies with dynamic market conditions. The explicit formulas for these two benchmarks are provided in Appendix D.

For all three benchmarks, we further enhance the performance by incorporating the no-trade region, as defined in Equation (10).7 Additionally, the no-trade boundary l is optimized separately for each risk measure used for benchmarking, with each benchmark exhibiting its own distinct optimal value of l. Further details are provided in Appendix D.3.

7The optimization process is carried out as detailed in Section 2.3, following Equation (7), using Mini-batch Stochastic Gradient Descent.

<!-- page: 14 -->

## 4.3 Neural network settings

## 4.3.1 Neural network architecture

We consider a RNN-FNN architecture with two LSTM cells of width 56, two FFNN-hidden layers of width 56 with ReLU activation function $( \mathrm { i . e . , ~ } g _ { \mathcal { L } _ { i } } ( X ) = \operatorname* { m a x } ( 0 , X ) \mathrm { ~ f o r ~ } i = 1 , 2 )$ 2 and one two-dimensional output FFNN layer with a linear activation function. Numerical experiments detailed in Appendix J from the Supplementary Material suggest the value $\lambda = 1$ for the soft constraint hyperparameter, which is learned from the validation set.

Agents are trained as described in Section 2.3 on a training set of 400,000 independent simulated paths with mini-batch size of 1000 and an initial learning rate of 0.0005. In addition, we include dropout regularization method with parameter $p = 0 . 5$ as in François et al. (2024). The training procedure is implemented in Python, using Tensorflow and considering the Glorot and Bengio (2010) random initialization of the initial parameters of the neural network. The performance assessment is obtained from a test set of 100,000 independent paths.

## 4.3.2 State space

The state space presented in Table 1 includes the state variables generated by the JIVR model, along with a new set of state variables associated with the straddle and hedging portfolio.

In our illustrative example, the RL agent seeks to hedge a straddle contract with the same specifications across different market dynamics. According to the terminology of Peng et al. (2024), this problem is a contract-specific reinforcement learning task, where the optimization problem is solved for a given contract with predefined parameters. Variables related to the target portfolio (such as $\mathcal { P } _ { t } , \Delta _ { t } ^ { P }$ , and $\Gamma _ { t } ^ { P } )$ are not strictly necessary, as they can theoretically be recovered by the ANN if needed. However, our numerical experiments demonstrate that in practice their inclusion enhances training performance across all risk measures (details in Appendix E). Furthermore, incorporating these state variables extends our framework to enable its application in a contract-unified setting, allowing for the optimization of portfolios with any combination of options and contract parameters.

<!-- page: 15 -->

[Table source crop](assets/tables/2025-francois-et-al-deep-hedging-iv-surface-p0015-block-0001-136eb4eca2bb5ac3.jpg)
Table 1: State variables.

## 4.4 Benchmarking of hedging strategies

## 4.4.1 Benchmarking in the absence of transaction costs

We begin by evaluating the hedging performance of both benchmark methods and RL agents trained using three different risk measures: MSE, SMSE, and $\mathrm { C V a R _ { 9 5 \% } }$ . This evaluation considers the estimated values of each risk measure alongside the sample average of the

<!-- page: 16 -->

hedging error,

$$
\mathrm { m e a n } \left( \xi _ { T } ^ { \tilde { \phi } _ { \theta } } \right) = \frac { 1 } { N } \sum _ { i = 1 } ^ { N } \xi _ { T , i } ^ { \tilde { \phi } _ { \theta } } ,
$$

where $\xi _ { T , i } ^ { \tilde { \phi } _ { \theta } }$ represents the i-th terminal hedging error in the test set of size N. Additionally, we incorporate the sample standard deviation of the terminal hedging error, std $\left( \xi _ { T } ^ { \tilde { \phi } _ { \theta } } \right)$ , as a metric to quantify the variability of hedging errors within the test set. Our analysis is conducted under the assumption of zero transaction costs, i.e. $\kappa _ { 1 } = \kappa _ { 2 } = 0$

![Figure 1: Hedging performance metrics under the assumption of zero transaction costs. (S) D (S) RL-MSE (S) RL-SMSE(S) RL-CVaR 95% (S + O) DG (S + O) MSE (S + O)SMSE (S + O) CVaR 95% Results are computed using 100,000 out-of-sample paths in the absence of transaction costs $\left( \kappa _ { 1 } = \kappa _ { 2 } = 0 \right)$ . Agents are trained according to the conditions outlined in Section 4.3. The hedged position is an ATM straddle with a maturity of $T = 6 3$ days and an average value of \$7.55 across all initial conditions. Methods denoted by (S) represent hedging with the risk-free and underlying assets, while those denoted by $( \mathrm { S } + \mathrm { O } )$ incorporate an ATM call option with an initial maturity of $T ^ { * } = 8 4$ days. D stands for delta hedging, DG denotes delta-gamma hedging, and RL refers to reinforcement learning strategies.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0016-block-0004-d4f4a840f63452a8.jpg)

Figure 1 presents the risk measures for the various hedging strategies in two cases. In the first case (the first four columns for each metric), the hedging instruments are limited to the risk-free asset and the underlying asset. In the second scenario (the last four columns) the ATM call option is introduced as an additional hedging instrument. In both cases, RL strategies consistently outperform the benchmarks and achieve the optimal values when the performance assessment metric matches the risk measure used during training. Our numerical results highlight the benefits of incorporating a second hedging instrument. Specifically, all strategies that include an option as an additional hedging instrument exhibit lower risk in terms of standard deviation, MSE, SMSE, and $\mathrm { C V a R _ { 9 5 \% } }$ , compared to those relying solely on a single hedging instrument. Notably, for tail risk captured by $\mathrm { C V a R _ { 9 5 \% } }$ , the RL agent—trained on the money account and the underlying asset only—achieves a performance comparable to that of delta-gamma hedging.

<!-- page: 17 -->

![Figure 2: Hedging error distribution in the absence of transaction costs.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0017-block-0002-6f15a8b945416a9b.jpg)

![](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0017-block-0003-f765083a91073428.jpg)

![](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0017-block-0004-7bcc2304701c8b5a.jpg)

Figure 2 depicts the distribution of hedging errors across various strategies. Panel A contrasts the hedging error distributions of the benchmark and RL agents—both using only the underlying asset—with the traditional DG strategy, showing that incorporating an option significantly reduces risk. Panel B compares the DG strategy to the RL-MSE strategy, both utilizing three hedging instruments, highlighting the RL approach's superior performance in variance reduction. Finally, Panel C compares the three RL agents, revealing that strategies based on asymmetric risk measures produce distributions with greater skewness.

<!-- page: 18 -->

## 4.4.2 Benchmarking in the presence of transaction costs

We now measure the impact of transaction costs on the hedging performance.

Figure 3 displays the optimal values of risk measures for two distinct hedging configurations: one relying solely on the risk-free asset and the underlying asset (first four columns in each group), and another that includes an ATM call option as an additional hedging instrument (last four columns). The comparison contrasts strategies without a no-trade region (solid bars) against those incorporating a no-trade region (striped bars). The no-trade region primarily benefits delta-gamma hedging. In the case of delta hedging, transaction costs associated with trading the underlying asset are minimal and have negligible impact on performance. For reinforcement learning (RL) approaches, trading costs are already internalized within the optimization of the neural network policy, rendering the additional constraint of a no-trade region unnecessary. This is consistent with the persistently low threshold values reported in Figure 13 of Appendix A.

<!-- page: 19 -->

![Figure 3: Hedging performance in the presence of transaction costs.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0019-block-0001-043bc11017eecbc3.jpg)

![SMSE](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0019-block-0002-41b798511455c1fd.jpg)

![](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0019-block-0003-8867a1d1344e1e81.jpg)

RL agents consistently outperform benchmarks across all risk measures and choices of hedging instruments. Using the MSE as a performance metric, adding an ATM call option as a hedging instrument significantly improves hedging performance. In particular, this holds for the DG strategy, which outperforms RL agents not using options. In terms of downside risk management—assessed via SMSE and CVaR metrics—it is noteworthy that, in the presence of transaction costs, the RL algorithm that relies solely on the risk-free asset and the underlying asset either outperforms or provides a performance similar to that of delta-gamma hedging. RL algorithms that incorporate an option as part of the hedging instruments achieve even stronger performance.

<!-- page: 20 -->

![Figure 4: Hedging error distribution in the presence of transaction costs.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0020-block-0002-f61dd40aa129e69c.jpg)

![](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0020-block-0003-487b1645d49477d6.jpg)

![Results are computed using 100,000 out-of-sample paths according to the conditions outlined in Section 4.3. The hedged position is an ATM straddle with a maturity of $T = 6 3$ days and an average value of \$7.55. The hedging instrument is an ATM call option with a maturity of $T ^ { * } = 8 4$ days. The transaction cost parameter for the underlying asset is set to $\kappa _ { 1 } = 0 . 0 5 \%$](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0020-block-0004-06a19cfb5033c8b3.jpg)

To further highlight the advantage of RL over DG, Figure 4 presents histograms of hedging error distributions at maturity for both strategies under two different transaction cost scenarios. RL agents constantly produce narrower distributions across all risk measures, indicating greater resilience to rising transaction costs. This stability is particularly beneficial from a risk management perspective, as it ensures more reliable performance despite increasing costs.

4.5 Assessing the presence of speculative components in hedging positions This section examines whether the RL risk management includes speculative elements, such as strategies that reap the time-varying risk premia embedded in hedging instruments. The risk premium (RP) is defined as the difference between the discounted expected payoff and the option price at time t, i.e.,

<!-- page: 21 -->

$$
\mathrm { R P } _ { t } = \exp ( - r ( T ^ { * } - t ) ) \mathbb { E } [ \operatorname* { m a x } ( S _ { T ^ { * } } - K ^ { * } , 0 ) \mid \mathcal { F } _ { t } ] - \mathrm { O } _ { t } ( T ^ { * } ) ,\tag{9}
$$

where $K ^ { * }$ is the hedging option strike price, the expectation is under the physical measure and $\mathcal { F } _ { t }$ denotes the information available at time $t . ^ { 8 }$ The risk premium is estimated using a stochastic-on-stochastic simulation approach, where the present value of the expected payoff is computed through a nested simulation at each time step within the simulated paths.

![Figure 5: Ranked data of risk premium and hedging option positions.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0021-block-0004-b555f6a1832533b1.jpg)

![](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0021-block-0005-61592e57b52cb8c0.jpg)

![Results are computed using a sample of $2 0 { , } 0 0 0$ data points from the 100,000 out-of-sample paths. The hedged position is an ATM straddle with a maturity of $T = 6 3$ days. The hedging instrument is an ATM call option with an initial maturity of $T ^ { * } = 8 4$ days. Transaction cost levels are set to 0%.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0021-block-0006-5720b041353899c3.jpg)

We investigate whether a statistical relationship exists between the risk premium $\mathrm { R P } _ { t }$ and the hedging position $\phi _ { t + 1 } ^ { \mathrm { ( O ) } }$ . Figure 5 presents a scatter plot of ranked data for these variables, using 20,000 samples from the 100,000 out-of-sample paths, which is repeated for the three risk measures. The plot reveals no strong dependence patterns, suggesting a weak or insignificant relationship. This finding is further supported by sample correlations ranging from -0.001 to -0.006, indicating that RL agents do not systematically seek to capture risk premium benefits. As a complementary analysis, we examine whether our approach embeds speculative elements, such as statistical arbitrage overlays, that may deviate from sound risk management practices. Our results indicate that RL agents do not engage in such strategies, regardless of the risk measure used in optimization. Further details are provided in Appendix F.

8The usual definition of the risk premium is a return difference. However, when options are DOTM and their value is very low, this definition leads to numerical instability.

<!-- page: 22 -->

## 4.6 Analysis of hedging positions

## 4.6.1 Comparison with benchmarks

We analyze the relationship between the hedging option positions produced by the DG strategy and those generated by RL agents. This analysis aims to understand how the RL outperformance documented in Section 4.4.1 and Section 4.4.2 emerges by studying the positions taken by the hedger. Figure 6 presents for various days t, the sample correlation between DG and RL hedging option positions, $\phi _ { t } ^ { \mathrm { ( O , D G ) } }$ and $\phi _ { t } ^ { \mathrm { ( O , R L ) } }$ , under the MSE, SMSE, and $\mathrm { C V a R _ { 9 5 \% } }$ risk measures. The correlation is computed for two scenarios: one without transaction costs and another with $\kappa _ { 1 } = 0 . 0 5 \%$ and $\kappa _ { 2 } = 1 \%$ for illustration.

Our numerical results reveal a consistent pattern across all risk measures, highlighting a significant divergence between RL and DG hedging strategies in terms of correlation, particularly at the start of the hedging horizon. Indeed, the RL agent benefits from learning experience to anticipate the future movements of state variables over multiple future periods. By contrast, the DG hedging agent is myopic in that he readjusts his hedging positions based on local risk. As time-to-maturity shrinks, both strategies become more similar. The inclusion of transaction costs leads the RL agent to maintain a distinct approach, with correlation remaining near zero for a significant portion of the hedging horizon.

<!-- page: 23 -->

![Figure 6: Pearson correlation between DG and RL agents' hedging option positions.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0023-block-0001-96e14cf975752586.jpg)

![](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0023-block-0002-380f8f22e490f785.jpg)

![Results are based on a sample of 100,000 out-of-sample paths. Agents are trained under the conditions described in Section 4.3. The hedged position is an ATM straddle with a maturity of $T = 6 3$ day. The hedging instrument is an ATM call option with a maturity of $T ^ { * } = 8 4 ~ \mathrm { d a y s }$](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0023-block-0003-4eeffb4b5f910946.jpg)

A potential secondary source of divergence between these strategies stems from differences in rebalancing size. While the rebalancing frequency influences the timing of adjustments, the magnitude of these adjustments plays a key role in differentiating the hedging behaviors. Figure 7 illustrates the average hedging option position, along with the interquartile range, over time for all risk measures. The analysis is presented for two scenarios: one without transaction costs (first row), and another with transaction costs set to $\kappa _ { 1 } = 0 . 0 5 \%$ and $\kappa _ { 2 } = 1 \%$ (second row).

Our findings indicate that RL agents tend to hold smaller option positions during the early stages of the hedging period, a trend that is more pronounced with the introduction of transaction costs. This behavior arises from the substantial transaction cost associated with the hedging option, suggesting that RL agents favor more frequent rebalancing with smaller initial positions, gradually increasing their hedging positions over time. By deferring full engagement with the hedge, the RL agent seeks to balance cost efficiency with effective risk management, avoiding taking positions that might need to be unwound shortly after. Additionally, lower option positions in early stages allow the agent to initially limit the (short) exposure to the variance risk premium while progressively scaling up the hedging positions. Thus, RL agents achieve twofold cost reductions, where both explicit transaction costs and implicit costs related to short exposure to the variance risk premium are managed. In contrast, DG strategies adopt larger option positions early in the period to fully neutralize gamma risk. However, this approach leads to prolonged exposure to the volatility premium, making it suboptimal.

<!-- page: 24 -->

![Figure 7: Distribution of hedging option positions.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0024-block-0001-583cc99c622287a1.jpg)

![](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0024-block-0002-f287cef8153f3f4a.jpg)

![](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0024-block-0003-3a7aa945b21d3995.jpg)

![](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0024-block-0004-b257475af7b90427.jpg)

![](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0024-block-0005-6b24fd47c69858f7.jpg)

![Results are computed over 100,000 out-of-sample paths according to the conditions outlined in Section 4.3.1. The hedged position is an ATM straddle with a maturity of $T = 6 3$ days. The hedging instrument is an ATM call option with a maturity of $T ^ { * } = 8 4 ~ \mathrm { d a y s }$ . IQR stands for the interquartile range, representing the range between the 25th and 75th percentiles.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0024-block-0006-d950ae3210c9a7d0.jpg)

## 4.6.2 Sensitivity analysis

We analyze the sensitivity of RL agents' positions to variations in the risk factors defining the IV surface, examining how they leverage information from its shape. Our analysis begins by evaluating RL policy behavior across different initial scenarios for the state variables $( \{ \beta _ { t , i } \} _ { i = 1 } ^ { 5 } , h _ { t , R } )$

<!-- page: 25 -->

To assess the impact of each state variable, we sort the initial state vectors in the test set according to each variable and observe the corresponding hedging positions in the same order. This method accounts for the interdependence between these state variables and the broader state vector components, as detailed in Table 1, and reveals how changes in a selected variable influence hedging decisions.

Figure 8 presents the hedging positions of the RL agent trained with the MSE risk measure under a no-transaction-cost scenario. Each panel displays the hedging positions when the initial state vectors are sorted according to each state variable, $( \{ \beta _ { t , i } \} _ { i = 1 } ^ { 5 } , h _ { t , R } )$

These empirical results suggest that the position in the hedging option exhibits a decreasing trend with respect to the conditional variance of the underlying asset returns, the long-term ATM level $\beta _ { 1 }$ and the time-to-maturity slope $\beta _ { 2 }$ of the IV surface.9 As noted in François et al. (2024), RL agents utilize both the historical variance process and market expectations of future volatility to adjust their positions. For instance, smaller positions on the hedging option when $\beta _ { 1 } , \beta _ { 2 }$ or $\sqrt { h _ { R } }$ are higher can be explained by the higher cost of hedging in such circumstances. Indeed, both option prices and associated proportional transaction costs are higher.

9By contrast, there is no clear pattern related with the other factors as shown in panels C, D and E.

<!-- page: 26 -->

Figure 8: Impact of state variables on hedging positions.

![Results are computed using a sample of 20,000 data points from 100,000 out-of-sample paths for an ATM straddle with maturity of $T = 6 3$ days. The hedging instrument is an ATM call option with an initial maturity of $T ^ { * } = 8 4$ days. Transaction cost levels are set to 0%.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0026-block-0002-649732d100603e74.jpg)

## 4.7 Tracking error analysis

The differences between positions of RL and DG agents allow RL agents to achieve higher performance with respect to terminal hedging error. This section investigates whether RL agents also retains good tracking performance before maturity.

We analyze the time-t tracking error $\xi _ { t } ^ { \tilde { \phi } _ { \theta } }$ defined in Equation (5) across all test set paths throughout the hedging period. This comparison is conducted by evaluating three key metrics on each rebalancing day t: the average tracking error (ATE), root-mean squared tracking error (RMSTE), and semi root-mean squared tracking error (SRMSTE), given respectively by

$$
\mathrm { A T E } = \frac { 1 } { N } \sum _ { i = 1 } ^ { N } \xi _ { t , i } ^ { ( \vec { \phi } _ { \theta } , l ) } , \mathrm { R M S T E } = \sqrt { \frac { 1 } { N } \sum _ { i = 1 } ^ { N } \left( \xi _ { t , i } ^ { ( \vec { \phi } _ { \theta } ) } \right) ^ { 2 } } , \mathrm { S R M S T E } = \sqrt { \frac { 1 } { N } \sum _ { i = 1 } ^ { N } \left( \xi _ { t , i } ^ { ( \vec { \phi } _ { \theta } ) } \mathbb { 1 } _ { \left\{ \xi _ { t , i } ^ { ( \vec { \phi } _ { \theta } ) } > 0 \right\} } \right) ^ { 2 } } ,
$$

<!-- page: 27 -->

where $\xi _ { t , i } ^ { \tilde { \phi } _ { \theta } }$ represents the time-t tracking error of the i-th path in the test set.

![Figure 9: Evolution of tracking error metrics across rebalancing days. Results are computed over 100,000 out-of-sample paths under the conditions outlined in Section 4.3.1. The hedged position is an ATM straddle with a maturity of $T = 6 3$ days and an average value of \$7.55. The hedging instrument is an ATM call option with a maturity of $T ^ { * } = 8 4$ days.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0027-block-0002-8de35e666b5c73c3.jpg)

Figure 9 presents the evolution of these metrics over the hedging period under two scenarios: without transaction costs (Panel A) and with transaction costs (Panel B). Panel B accounts for multiple DG strategies, each corresponding to a different optimal no-trade threshold l. The results indicate that, regardless of transaction costs, both the standard and asymmetric tracking error metrics (columns 2 and 3 of Figure 9) exhibit a monotonic upward trend for DG strategies. In contrast, RL strategies lead to curves that flatten out or even decrease through time, demonstrating their ability to correct for past errors. Conversely, DG strategies are purely forward-looking, leading to the accumulation of unaddressed errors over time. Furthermore, columns 2 and 3 show that RL agents maintain strong option-tracking performance in the absence of transaction costs, despite adopting strategies that differ from those derived using the DG approach. However, once transaction costs are introduced (panels B2 and B3 of Figure 9), the RL agent trained under the CVaR risk measure exhibits larger tracking error. This is primarily driven by the nature of the objective function, which focuses on minimizing the tail of losses only at the end of the hedging period. As a result, early deviations between the hedging and target portfolios do not necessarily lead to a loss in the tail of the distribution, and therefore do not require immediate correction, as positions can be rebalanced closer to maturity while keeping the CVaR at low levels. Larger tracking errors in early stages are expected because the RL optimization leads to smaller hedging positions, see Figure 7.

<!-- page: 28 -->

In terms of the sample average tracking error (column 1), DG strategies exhibit values close to zero across all rebalancing days in absence of transaction costs. The RL agent trained under the MSE risk metric follows closely, which aligns with the symmetric nature of this risk measure, as it penalizes both losses and gains equally. In contrast, RL strategies optimized using SMSE and CVaR deviate further from zero, particularly displaying a negative average hedging error. This behavior reflects the asymmetric nature of these risk metrics, which do not penalize gains. These differences become even more pronounced when transaction costs are introduced, further emphasizing the distinct risk preferences embedded in each optimization approach

## 5 Out-of-sample backtesting

We assess the performance of our framework under actual market conditions, using historical option prices sourced from OptionMetrics observed between December 31, 2020, and October

<!-- page: 29 -->

31, 2023. We evaluate the hedging performance across 4,134 near-the-money 63-day European straddles, where the option strike lies within ±10% of the underlying asset's initial price. Each straddle is hedged using a combination of a call option with a longer maturity (between 78 and 84 days of maturity depending on availability), the underlying asset and the cash account.10

We compare the performance of the practitioners' delta-gamma hedging with that of the RL algorithms with and without IV surface information.11 Figure 10 shows that, in terms of MSE, the RL algorithm without IV surface information performs worse than the two other approaches. Interestingly, in the absence of transaction costs, the practitioners' deltagamma hedging and the RL algorithm with IV information exhibit very similar MSE. The RL-algorithm with the complete information slightly outperforms the other approaches in presence of transaction costs, again in terms of MSE. The main conclusion is that RL approaches do not necessarily dominate traditional methods; their performance critically depends on the information provided to the algorithm. However, in terms of tail risk, the RL algorithms clearly outperform the practitioners' delta-gamma approach. Moreover, receiving information about the IV surface clearly improves the performance the RL algorithm.

10On each day of the out-of-sample dataset, the IV parameters βt are estimated. We then re-estimate their joint dynamics with the S&P 500 returns to recreate the state space. To ensure consistency with the simulation environment used during training, all underlying price paths are rescaled to start at a normalized value of 100.

11The RL benchmark without IV surface information is analogous to the proposed RL method, except that predictors βt,1, . . . , βt,5, ht,1, . . . , ht,5 are dropped from the state space.

<!-- page: 30 -->

![Figure 10: Out-of-sample backtest performance metrics on hedging errors, with and without transaction costs. The backtest is conducted on 4,134 around-the-money straddle intruments, using actual market prices observed between December 31, 2020 and October 31, 2023.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0030-block-0001-8e68f8000ef3dd7d.jpg)

Further evidence of the RL approach's superior performance is provided by the distribution of hedging errors (without transaction costs) shown in Figure 11. The first row compares the RL algorithm with the full information to the practitioners' delta-gamma strategy. It is clear that the distribution of the practitioners' delta-gamma strategy is shifted to the right and exhibits a heavier right tail. In the second row, we observe the benefits of incorporating IV information into the RL strategies. The distribution of hedging errors is more concentrated around zero when such information is included,

Although risk management is primarily associated with measures of dispersion and downside risk, it is interesting to note that only the practitioners' delta-gamma strategy exhibits a negative cumulative P&L (see Figure 12). Moreover, having the full information about the IV surface helps the RL algorithm achieve the best cumulative P&L. We observe that the cumulative P&L of the RL algorithm with the full information increases significantly in the second half of the sample. Examining market conditions (Panel B to Panel E), we see that this period is associated with IV slopes that are strongly positive (see Panel D). In the middle of the sample, there is a period of high volatility (see Panel E), but this information is captured by both the practitioners' delta-gamma hedging and the RL algorithms.

<!-- page: 31 -->

![Figure 11: Distribution of hedging errors for near-at-the-money straddles.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0031-block-0001-bd9eeb7596fd98b5.jpg)

These findings demonstrate that RL agents achieve consistent and competitive performance when applied to unseen historical market conditions, despite being trained on simulated data Their ability to adapt to diverse environments and maintain superior risk control highlights the practical value of this approach in hedging tasks.

<!-- page: 32 -->

![Figure 12: Time series of hedging strategies P&L and market conditions.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0032-block-0001-939b2a72b98f5b54.jpg)

![](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0032-block-0002-a3492215ace38276.jpg)

![](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0032-block-0003-4257240ed5cec8d6.jpg)

![](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0032-block-0004-adb234f1bd6f5736.jpg)

![](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0032-block-0005-3ee7cf61e60b809c.jpg)

<!-- page: 33 -->

## 6 Conclusion

This study develops a deep hedging framework to manage the risk associated with S&P 500 options with a hedging portfolio including both options and underlying asset shares. In our work the information related to implied volatility surfaces is included within the set of state variables. The key differentiating aspect of our work is that with this information in hand, the adjustments in hedging positions not only integrate forward-looking expectations of market dynamics, but also capture the current price levels for options (and the associated variance risk premium) within rebalancing decisions. The IV surface, conveniently represented by a parametric form, proves to be instrumental in refining the hedging policy. A soft constraint is included in the optimization scheme to mitigate speculative behavior, ensuring that hedging strategies focus on effective risk management.

Our approach consistently outperforms traditional benchmarks both with and without transaction costs. It also highlights the substantial hedging benefits of incorporating additional instruments, such as options. Our study further documents the reasons driving the hedging outperformance of the reinforcement learning agent. In contrast to the myopic delta-gamma hedging, deep hedging begins with smaller option positions. This leads to less transaction costs and, more importantly, provides more flexibility for appropriately rebalancing the hedging portfolio when uncertainty about the final moneyness of the position to hedge is gradually resolved. Smaller early-stage positions in the hedging option also reduce exposure to the variance risk premium, leading to lower losses. We show that reinforcement learning agents effectively incorporate both historical variance and market expectations of future volatility into their hedging decisions. The observed decline in hedging option positions in response to higher conditional variance, long-term ATM implied volatility level and time-to-maturity slope underscores the agents' ability to dynamically mitigate risk, acting as a protective mechanism against volatility fluctuations.

<!-- page: 34 -->

Out-of-sample backtests using historical data and various levels of transaction costs show that the reinforcement learning hedging performance is robust to diverse market conditions and superior to that of benchmarks in terms of downside risk management, on top of providing superior profitability. Such tests highlight the importance of information embedded in implied volatility surfaces. This confirms that deep hedging with options using the implied volatility surface is a sound and practically applicable hedging approach.

## References

Alexander, C. and Nogueira, L. M. (2007). Model-free hedge ratios and scale-invariant models. Journal of Banking & Finance, 31(6):1839–1861. Assa, H. and Karai, K. M. (2013). Hedging, Pareto optimality, and good deals. Journal of Optimization Theory and Applications, 157:900–917. Balduzzi, P. and Lynch, A. W. (1999). Transaction costs and predictability: Some utility cost calculations. Journal of Financial Economics, 52(1):47–78. Bates, D. S. (2005). Hedging the smirk. Finance Research Letters, 2(4):195–200.

Bazzana, F. and Collini, A. (2020). How does HFT activity impact market volatility and the bid-ask spread after an exogenous shock? An empirical analysis on S&P 500 ETF. The North American Journal of Economics and Finance, 54:101240.

Black, F. and Scholes, M. (1973). The pricing of options and corporate liabilities. Journal of

<!-- page: 35 -->

Political Economy, 81(3):637–654.

Buehler, H., Gonon, L., Teichmann, J., and Wood, B. (2019). Deep hedging. Quantitative Finance, 19(8):1271–1291.

Buehler, H., Murray, P., Pakkanen, M. S., and Wood, B. (2021). Deep hedging: learning to remove the drift under trading frictions with minimal equivalent near-martingale measures. arXiv preprint arXiv:2111.07844.

Cao, J., Chen, J., Farghadani, S., Hull, J., Poulos, Z., Wang, Z., and Yuan, J. (2023). Gamma and vega hedging using deep distributional reinforcement learning. Frontiers in Artificial Intelligence, 6:1129370.

Cao, J., Chen, J., Hull, J., and Poulos, Z. (2020). Deep hedging of derivatives using reinforcement learning. The Journal of Financial Data Science.

Carbonneau, A. (2021). Deep hedging of long-term financial derivatives. Insurance: Mathematics and Economics, 99:327–340.

Carr, P. and Wu, L. (2014). Static hedging of standard options. Journal of Financial Econometrics, 12(1):3–46.

Chaudhury, M. (2019). Option bid-ask spread and liquidity. SSRN.

Chen, J., Hull, J., Poulos, Z., Rasul, H., Veneris, A., and Wu, Y. (2023). A variational autoencoder approach to conditional generation of possible future volatility surfaces.

Choudhary, V., Jaimungal, S., and Bergeron, M. (2024). FuNVol: Multi-asset implied volatility market simulator using functional principal components and neural SDEs. Quantitative Finance, 24(8):1077–1103.

<!-- page: 36 -->

Clewlow, L. and Hodges, S. (1997). Optimal delta-hedging under transactions costs. Journal of Economic Dynamics and Control, 21(8-9):1353–1376.

Constantinides, G. M. (1986). Capital market equilibrium with transaction costs. Journal of Political Economy, 94(4):842–862.

Davis, M. H. A. and Norman, A. R. (1990). Portfolio selection with transaction costs. Mathematics of Operations Research, 15(4):676–713.

Du, J., Jin, M., Kolm, P. N., Ritter, G., Wang, Y., and Zhang, B. (2020). Deep reinforcement learning for option replication and hedging. The Journal of Financial Data Science, 2(4):44–57.

Fecamp, S., Mikael, J., and Warin, X. (2020). Deep learning for discrete-time hedging in incomplete markets. Journal of Computational Finance, 25(2).

François, P. and Stentoft, L. (2021). Smile-implied hedging with volatility risk. Journal of Futures Markets, 41(8):1220–1240.

François, P., Galarneau-Vincent, R., Gauthier, G., and Godin, F. (2022). Venturing into uncharted territory: An extensible implied volatility surface model. Journal of Futures Markets, 42(10):1912–1940.

François, P., Galarneau-Vincent, R., Gauthier, G., and Godin, F. (2023). Joint dynamics for the underlying asset and its implied volatility surface: A new methodology for option risk management. SSRN.

François, P., Gauthier, G., Godin, F., and Mendoza, C. O. P. (2024). Enhancing deep hedging of options with implied volatility surface feedback information. SSRN.

<!-- page: 37 -->

François, P., Gauthier, G., Godin, F., and Mendoza, C. O. P. (2025). Is the difference between deep hedging and delta hedging a statistical arbitrage? Finance Research Letters, 73:106590. Glorot, X. and Bengio, Y. (2010). Understanding the difficulty of training deep feedforward neural networks. In Proceedings of the thirteenth international conference on artificial intelligence and statistics, pages 249–256. JMLR Workshop and Conference Proceedings. Goodfellow, I., Bengio, Y., and Courville, A. (2016). Deep learning. MIT press. Henrotte, P. (1993). Transaction costs and duplication strategies. Graduate School of Business, Stanford University. Hodges, S. D. and Neuberger, A. (1989). Optimal replication of contingent claims under transaction costs. Review Futures Market, 8:222-239 Horikawa, H. and Nakagawa, K. (2024). Relationship between deep hedging and delta hedging: Leveraging a statistical arbitrage strategy. Finance Research Letters, page 105101. Kingma, D. P. and Ba, J. (2015). Adam: A method for stochastic optimization. In 3rd International Conference on Learning Representations, ICLR 2015, San Diego, CA, USA, May 7-9, 2015, Conference Track Proceedings. Leland, H. E. (1985). Option pricing and replication with transactions costs. The Journal of Finance, 40(5):1283–1301. Martellini, L. and Priaulet, P. (2002). Competing methods for option hedging in the presence of transaction costs. Journal of Derivatives, 9(3):26. Peng, X., Zhou, X., Xiao, B., and Wu, Y. (2024). A risk sensitive contract-unified reinforcement

<!-- page: 38 -->

learning approach for option hedging. arXiv preprint arXiv:2411.09659.

Rebonato, R. (2005). Volatility and correlation: The perfect hedger and the fox. John Wiley & Sons.

Toft, K. B. (1996). On the mean-variance tradeoff in option replication with transactions costs. Journal of Financial and Quantitative Analysis, 31(2):233–263.

Vuletić, M. and Cont, R. (2024). VolGAN: A generative model for arbitrage-free implied volatility surfaces. Applied Mathematical Finance, 31(4):203–238.

Wu, D. and Jaimungal, S. (2023). Robust risk-aware option hedging. Applied Mathematical Finance, 30(3):153–174.

## Appendices

## A No trade region

At time t, the no-trade region¹2 is determined by the distance between the current portfolio position, $\phi _ { t }$ , and the next position proposed by the ANN, $ { \tilde { \phi } } _ { \theta } ( X _ { t } )$ . Specifically, rebalancing

occurs only if the cumulative deviation in positions across hedging instruments exceeds a

12No-trade regions, which mitigate the impact of transaction costs, have been extensively studied in the portfolio optimization literature. Constantinides (1986) first introduced the idea that proportional transaction costs give rise to such regions—a concept further developed by Davis and Norman (1990) and Balduzzi and Lynch (1999), who emphasized portfolio allocation over rebalancing costs. In the hedging context, optimal rebalancing based on delta variations has been explored by Henrotte (1993), Toft (1996), and Martellini and Priaulet (2002). Hodges and Neuberger (1989) and Clewlow and Hodges (1997) examine hedging within a utility-maximization framework. The optimal hedging strategy consists of no-trade bands around delta, whose width depends on the hedger's risk aversion

<!-- page: 39 -->

threshold l:

$$
( \phi _ { t + 1 } ^ { ( S ) } , \phi _ { t + 1 } ^ { ( O ) } ) = \left\{ \begin{array} { l l } { ( \phi _ { t } ^ { ( S ) } , \phi _ { t } ^ { ( O ) } ) , } & { \mathrm { i f ~ } | \phi _ { t } ^ { ( S ) } - \tilde { \phi } _ { \theta } ^ { ( S ) } ( X _ { t } ) | + | \phi _ { t } ^ { ( O ) } - \tilde { \phi } _ { \theta } ^ { ( O ) } ( X _ { t } ) | \leq \ell , } \\ { } & { } \\ { \left( \tilde { \phi } _ { \theta } ^ { ( S ) } ( X _ { t } ) , \tilde { \phi } _ { \theta } ^ { ( O ) } ( X _ { t } ) \right) , } & { \mathrm { o t h e r w i s e . } } \end{array} \right.\tag{10}
$$

The bank account position is determined by the self-financing constraint (1). This formulation expresses the no-trade region in terms of the number of shares of option contracts, providing a measure of the distance at which rebalancing becomes cost-effective, capturing the trade-off between transaction costs and maintaining proximity to the desired portfolio adjustments. Indeed, when rebalancing actions proposed by the neural network are minor, they are not implemented because (i) this only leads to a small misalignment with the ideal hedging positions and (ii) this allows avoiding transaction costs.13 The rebalancing threshold l is treated as a learnable parameter included in the ANN parameters θ, allowing the model to jointly optimize the size of rebalancing actions and decisions of whether or not to rebalance. This analysis incorporates the no-trade region, defined by Equation (10), to optimize rebalancing frequency while accounting for transaction costs. For benchmarks, the rebalancing threshold l is estimated using the approach described in Appendix D.3. In contrast, RL strategies estimate this parameter jointly with other ANN parameters during training.

13We tried other specifications for the no-trade region (for instance explicitly capturing transaction cost amounts), with results being qualitatively similar.

<!-- page: 40 -->

![Figure 13: Optimal rebalancing threshold l values for DG and RL strategies. Optimal values are computed across different transaction cost levels using 100,000 out-of-sample paths. The hedged position is an ATM straddle with a maturity of $T = 6 3$ days. The hedging instrument is an ATM call option with a maturity of $T ^ { * } = 8 4$ days.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0040-block-0001-527265cc039dc4f3.jpg)

Figure 13 reports the optimal rebalancing thresholds l across different transaction cost levels for both DG (gray) and RL (blue) strategies, considering all risk measures. Remarkably, the RL algorithms barely rely on the no-trade region, as the optimal values of l are close to zero. Figure 3 provides further evidence of this phenomenon: risk metrics associated with the RL approaches are minimally affected by the presence of the no-trade region. Such no-trade region is primarily introduced to assist the delta-gamma benchmarks, which are not inherently designed to handle transaction costs efficiently. In the absence of transaction costs, the optimal no-trade region parameter l collapses to zero.

## B Details for the MSGD training approach

The MSGD method estimates the objective function $\mathcal { O } ( \theta ; \lambda )$ by using small samples of the hedging error, referred to as batches. Let $\mathbb { B } _ { j } = \left\{ \xi _ { T , i } ^ { \tilde { \phi } _ { \theta _ { j } } } \right\} _ { i = 1 } ^ { B _ { \mathrm { b a t c h } } }$ be the j-th batch simulated with policy parameters $\theta _ { j }$ . Using a subset from generated paths, it represents a set of hedging errors

$$
\begin{array} { r } { \xi _ { T , i } ^ { \tilde { \theta } _ { \theta _ { j } } } = \Psi ( S _ { T , i } ^ { ( j ) } ) - V _ { T , i } ^ { \tilde { \phi } _ { \theta _ { j } } } \quad \mathrm { f o r } \quad i \in \{ 1 , \dots , B _ { \mathrm { b a t c h } } \} , \ j \in \{ 1 , \dots , N _ { \mathrm { b a t c h } } \} , } \end{array}
$$

<!-- page: 41 -->

where $S _ { T , i } ^ { ( j ) }$ and $V _ { T , i } ^ { \tilde { \phi } _ { \theta _ { j } } }$ respectively represent the time-T underlying asset price and the terminal value of the hedging portfolio for path i of batch $j .$ The batch size is $B _ { \mathrm { b a t c h } } = 1 0 0 0$ , and the total number of batches is $N _ { \mathrm { b a t c h } } = 4 0 0$ . The objective function estimates for batch $\mathbb { B } _ { j }$ are

$$
\begin{array} { l } { \displaystyle \hat { \mathcal { O } } ^ { ( \mathrm { M S E } ) } ( \theta _ { j } ; \lambda , \mathbb { B } _ { j } ) = \frac { 1 } { B _ { \mathrm { b a t c h } } } \sum _ { i = 1 } ^ { B _ { \mathrm { b a t c h } } } \left( \xi _ { T , i } ^ { \hat { \theta } _ { \theta _ { j } } } \right) ^ { 2 } + \lambda \cdot \widehat { S C } ( \theta _ { j } , \mathbb { B } _ { j } ) , } \\ { \displaystyle \hat { \mathcal { O } } ^ { ( \mathrm { S M S E } ) } ( \theta _ { j } ; \lambda , \mathbb { B } _ { j } ) = \frac { 1 } { B _ { \mathrm { b a t c h } } } \sum _ { i = 1 } ^ { B _ { \mathrm { b a t c h } } } \left( \xi _ { T , i } ^ { \hat { \theta } _ { \theta _ { j } } } \right) ^ { 2 } \mathbb { 1 } \int _ { \left\{ \xi _ { T , i } ^ { \hat { \theta } _ { \theta _ { j } } } \geq 0 \right\} } + \lambda \cdot \widehat { S C } ( \theta _ { j } , \mathbb { B } _ { j } ) , } \\ { \displaystyle \hat { \mathcal { O } } ^ { ( \mathrm { C N a R } ) } ( \theta _ { j } ; \lambda , \mathbb { B } _ { j } ) = \widehat { \mathrm { V a R } } _ { \alpha } ( \mathbb { B } _ { j } ) + \frac { 1 } { ( 1 - \alpha ) B _ { \mathrm { b a t c h } } } \sum _ { i = 1 } ^ { B _ { \mathrm { b a t c h } } } \operatorname* { m a x } \left( \xi _ { T , i } ^ { \hat { \theta } _ { \theta _ { j } } } - \widehat { \mathrm { V a R } } _ { \alpha } ( \mathbb { B } _ { j } ) , 0 \right) + \lambda \cdot \widehat { S C } ( \theta _ { j } , \mathbb { B } _ { j } ) , } \end{array}
$$

where

$$
\widehat { S C } ( \theta _ { j } , \mathbb { B } _ { j } ) = \frac { 1 } { B _ { \mathrm { b a t c h } } } \sum _ { i = 1 } ^ { B _ { \mathrm { b a t c h } } } \mathbb { 1 } _ { \left\{ \operatorname* { m a x } _ { t \in \{ 0 , \ldots , T \} } \left[ P _ { t , i } - V _ { t , i } ^ { \tilde { \phi } _ { \theta _ { j } } } \right] > V _ { 0 , i } ^ { \tilde { \phi } _ { \theta _ { j } } } \right\} } ,
$$

and $\widehat { \mathrm { V a R } } _ { \alpha } ( \mathbb { B } _ { j } ) = \boldsymbol { \xi } _ { T , \left[ \mathbb { \alpha } \cdot B _ { \mathrm { b a t c h } } \right] } ^ { \tilde { \phi } _ { \theta _ { j } } } \mathrm { ~ }$ is the value-at-risk estimation derived from the ordered sample $\left\{ \xi _ { T , [ i ] } ^ { \tilde { \phi } _ { \theta _ { j } } } \right\} _ { i = 1 } ^ { B _ { \mathrm { b a t c h } } }$ , where [·] is the ceiling function. These empirical approximations are used to estimate the gradient of the objective function required in Equation (7). The gradient of these empirical objective functions has analytical expressions for FFNN, LSTM and RNN-FNN networks, which can be computed through backpropagation, see for instance Goodfellow et al. (2016).

<!-- page: 42 -->

## C Joint implied volatility and return model

## C.1 Daily implied volatility surface

The full functional representation of the IV surface model introduced by François et al. (2022) is given by:

$$
\begin{array} { r l } & { \sigma ( M _ { t } , \tau _ { t } , \beta _ { t } ) = \underbrace { \beta _ { t , 1 } } _ { f _ { 1 } : \mathrm { ~ L o n g ~ t e m ~ A r n ~ I V ~ } } + \beta _ { t , 2 } \underbrace { e ^ { - \sqrt { \pi _ { t } / T _ { c o n v } } } } _ { f _ { 2 } : \mathrm { ~ Y i m e s t o - m a t u r i t y ~ s l o p e } } + \beta _ { t , 3 } \underbrace { \left( M _ { t } \mathbb { I } _ { \{ M _ { t } \geq 0 \} } + \frac { e ^ { 2 M _ { t } } - 1 } { e ^ { 2 M _ { t } } + 1 } \mathbb { 1 } _ { \{ M _ { t } < 0 \} } \right) } _ { f _ { 3 } : \mathrm { ~ M o n g n e s s ~ s l o p e } } } \\ & { + \beta _ { t , 4 } \underbrace { \left( 1 - e ^ { - M _ { t } ^ { 2 } } \right) \log ( \tau _ { t } / T _ { m a x } ) } _ { f _ { 4 } : \mathrm { ~ S u i l e a t e m u a t i o n } } + \beta _ { t , 5 } \underbrace { \left( 1 - e ^ { \left( 3 M _ { t } \right) ^ { 3 } } \right) \log ( \tau _ { t } / T _ { m a x } ) } _ { f _ { 5 } : \mathrm { ~ S u i r k ~ } } \mathbb { 1 } _ { \{ M _ { t } < 0 \} } , \quad \tau _ { t } \in [ T _ { m i n } , T _ { m a x } ] . } \end{array}\tag{11}
$$

As in François et al. (2022), we set $T _ { m a x } = 5$ years, $T _ { m i n } = 6 / 2 5 2$ and $T _ { c o n v } = 0 . 2 5$

## C.2 Joint implied volatility and return dynamics

The multivariate time series representation of the JIVR model, as introduced by François et al. (2023), consists of two key components: one capturing the returns of the underlying asset and another modeling the fluctuations of the implied volatility (IV) surface coefficients. The first component is inspired from the NGARCH(1,1) process with normal inverse Gaussian (NIG) innovations and is formulated as

$$
R _ { t + 1 } = \xi _ { t + 1 } - \psi ( \sqrt { h _ { t + 1 , R } \Delta } ) + \sqrt { h _ { t + 1 , R } \Delta } \epsilon _ { t + 1 , R } ,
$$

$$
\begin{array} { r l r } {  { h _ { t + 1 , R } = Y _ { t } + \kappa _ { R } ( h _ { t , R } - Y _ { t } ) + a _ { R } h _ { t , R } ( \epsilon _ { t , R } ^ { 2 } - 1 - 2 \gamma _ { R } \epsilon _ { t , R } ) , } } \\ & { } & \\ & { } & { Y _ { t } = \bigg ( \omega _ { R } \sigma ( 0 , \frac { 1 } { 1 2 } , \beta _ { t } ) \bigg ) ^ { 2 } , ~ } \end{array}
$$

<!-- page: 43 -->

where the equity risk premium is

$$
\xi _ { t + 1 } = \psi ( - \lambda \sqrt { h _ { t + 1 , R } \Delta } ) - \psi ( ( 1 - \lambda ) \sqrt { h _ { t + 1 , R } \Delta } ) + \psi ( \sqrt { h _ { t + 1 , R } \Delta } ) .
$$

The innovation process $\{ \epsilon _ { t , R } \} _ { t = 0 } ^ { T }$ is a sequence of iid standardized NIG random variables¹4 and $\psi$ represents its cumulant generating function.

The evolution of the long-term factor $\beta _ { 1 }$ is modeled as

$$
\beta _ { t + 1 , 1 } = \alpha _ { 1 } + \sum _ { i = 1 } ^ { 5 } \theta _ { 1 , j } \beta _ { t , j } + \sqrt { h _ { t + 1 , 1 } \Delta } \epsilon _ { t + 1 , 1 } ,
$$

$$
h _ { t + 1 , 1 } = U _ { t } + \kappa _ { 1 } \big ( h _ { t , 1 } - U _ { t } \big ) + a _ { 1 } h _ { t , 1 } \big ( \epsilon _ { t , 1 } ^ { 2 } - 1 - 2 \gamma _ { 1 } \epsilon _ { t , 1 } \big ) ,
$$

$$
U _ { t } = \left( \omega _ { 1 } \sigma \Big ( 0 , \frac { 1 } { 1 2 } , \beta _ { t } \Big ) \right) ^ { 2 } .
$$

The evolution of the other four IV coefficients, namely for $i \in \{ 2 , 3 , 4 , 5 \}$ , is

$$
\beta _ { t + 1 , i } = \alpha _ { i } + \sum _ { j = 1 } ^ { 5 } \theta _ { i , j } \beta _ { t , j } + \nu \beta _ { t - 1 , 2 } \mathbb { 1 } _ { \{ i = 2 \} } + \sqrt { h _ { t + 1 , i } \Delta } \epsilon _ { t + 1 , i } ,
$$

$$
h _ { t + 1 , i } = \sigma _ { i } ^ { 2 } + \kappa _ { i } \big ( h _ { t , i } - \sigma _ { i } ^ { 2 } \big ) + a _ { i } h _ { t , i } \big ( \epsilon _ { t , i } ^ { 2 } - 1 - 2 \gamma _ { i } \epsilon _ { t , i } \big ) ,
$$

where $\{ \epsilon _ { t , i } \} _ { i = 1 } ^ { 5 }$ are time-independent standardized NIG random variables with parameters $\{ ( \zeta _ { i } , \varphi _ { i } ) \} _ { i = 1 } ^ { 5 }$

The JIVR model imposes a dependence structure on the contemporaneous innovations, i.e., $\boldsymbol { \epsilon } _ { t } = ( \epsilon _ { t , R } , \epsilon _ { t , 1 } , . . . , \epsilon _ { t , 5 } )$ , through a Gaussian copula, which is parameterized using a covariance

14A complete description of the NIG specification is available in François et al. (2023).

<!-- page: 44 -->

matrix $\Sigma$ of dimension $6 \times 6$ . Parameter estimates for the entire JIVR model are sourced from Table 5 and Table 6 of François et al. (2023).

## D Benchmarks

The benchmarks presented in this appendix assume that implied volatilities adhere to the IV model specified in Equation (8).

## D.1 Leland model

The Leland delta hedging strategy, introduced by Leland (1985), modifies the classical option replication framework of Black and Scholes (1973) by incorporating transaction costs, represented by the proportion $\kappa ,$ and the rebalancing frequency λ. The hedging position in the underlying asset is given by

$$
\phi _ { t + 1 } ^ { ( S ) } = \mathrm { e } ^ { - q _ { t } \tau _ { t } } \Phi \left( \tilde { d } _ { t } \right) ,
$$

where

$$
\widetilde { d } _ { t } = \frac { \log \left( \frac { S _ { t } } { K } \right) + \left( r _ { t } - q _ { t } + \frac { 1 } { 2 } \widetilde { \sigma } _ { t } ^ { 2 } \right) \tau _ { t } } { \widetilde { \sigma } _ { t } \sqrt { \tau _ { t } } }
$$

with the adjusted volatility

$$
\tilde { \sigma } _ { t } = \sigma ( M _ { t } , \tau _ { t } , \beta _ { t } ) \sqrt { 1 + \sqrt { \frac { 2 } { \pi } } \frac { 2 \kappa } { \sigma ( M _ { t } , \tau _ { t } , \beta _ { t } ) \sqrt { \lambda } } } .
$$

Here, $\Phi$ denotes the cumulative distribution function of the standard normal distribution.

<!-- page: 45 -->

## D.2 Delta-gamma hedging

The delta-gamma hedging strategy involves both the underlying asset $S$ and an additional hedging instrument, O. This setup allows for neutralizing both the delta and gamma of the portfolio. The trading strategy $\phi$ is fully determined by the process $( \phi ^ { ( S ) } , \phi ^ { ( \mathrm { O } ) } )$ , expressed as

$$
\left( \phi _ { t + 1 } ^ { ( S ) } , \phi _ { t + 1 } ^ { ( \mathrm { O } ) } \right) = \left( \Delta _ { t } ^ { \mathcal { P } } - \frac { \Gamma _ { t } ^ { \mathcal { P } } } { \Gamma _ { t } ^ { ( \mathrm { O } ) } } \Delta _ { t } ^ { ( \mathrm { O } ) } , \frac { \Gamma _ { t } ^ { \mathcal { P } } } { \Gamma _ { t } ^ { ( \mathrm { O } ) } } \right) ,
$$

where $\Delta _ { t } ^ { \mathcal { P } } , \Gamma _ { t } ^ { \mathcal { P } }$ , and $\Delta _ { t } ^ { \mathrm { ( O ) } } , \Gamma _ { t } ^ { \mathrm { ( O ) } }$ represent the delta and gamma of the hedged portfolio and of the hedging option, respectively. The self-financing constraint (1) fully determines $\phi _ { t + 1 } ^ { ( r ) }$ . For all Greeks we use the implied volatility $\sigma ( M _ { t } , \tau _ { t } , \beta _ { t } )$ from the static surface as the volatility input parameter.

## D.3 No-trade region

This is a recursive construction. In the time interval $( t - 1 , t ]$ , denote the hedging portfolio with the no-trade threshold l by $\phi _ { t } ^ { ( \ell ) } = \left( \phi _ { t } ^ { ( \ell , r ) } , \phi _ { t } ^ { ( \ell , S ) } , \phi _ { t } ^ { ( \ell , 0 ) } \right)$ . At time $t ,$ its value is

$$
V _ { t } ^ { ( \ell , \phi ) } = \phi _ { t } ^ { ( \ell , r ) } \mathrm { e } ^ { r _ { t } \Delta } + \phi _ { t } ^ { ( \ell , S ) } S _ { t } \mathrm { e } ^ { q _ { t } \Delta } + \phi _ { t } ^ { ( \ell , \mathrm { O } ) } O _ { t } \left( T ^ { * } \right) .
$$

The no-trade region constraint is set up such that

$$
\begin{array} { r } { \left( \phi _ { t + 1 } ^ { ( \ell , S ) } , \phi _ { t + 1 } ^ { ( \ell , 0 ) } \right) = \left\{ \begin{array} { l l } { \left( \phi _ { t } ^ { ( \ell , S ) } , \phi _ { t } ^ { ( \ell , 0 ) } \right) , } & { \mathrm { i f ~ } \left. \phi _ { t } ^ { ( \ell , S ) } - \left( \Delta _ { t } ^ { P } - \frac { \Gamma _ { t } ^ { P } } { \Gamma _ { t } ^ { ( 0 ) } } \Delta _ { t } ^ { ( 0 ) } \right) \right. + \left. \phi _ { t } ^ { ( \ell , 0 ) } - \frac { \Gamma _ { t } ^ { P } } { \Gamma _ { t } ^ { ( 0 ) } } \right. \leq \ell , } \\ { \left( \Delta _ { t } ^ { P } - \frac { \Gamma _ { t } ^ { P } } { \Gamma _ { t } ^ { ( 0 ) } } \Delta _ { t } ^ { ( 0 ) } , \frac { \Gamma _ { t } ^ { P } } { \Gamma _ { t } ^ { ( 0 ) } } \right) , } & { \mathrm { o t h e r w i s e } . } \end{array} \right. } \end{array}
$$

<!-- page: 46 -->

The bank account position is

$$
\phi _ { t + 1 } ^ { ( \ell , r ) } = V _ { t } ^ { ( \ell , \phi ) } - \phi _ { t + 1 } ^ { ( \ell , S ) } S _ { t } - \phi _ { t + 1 } ^ { ( \ell , O ) } O _ { t } ( T ^ { * } ) - \kappa _ { 1 } \left| \phi _ { t + 1 } ^ { ( \ell , S ) } - \phi _ { t } ^ { ( \ell , S ) } \right| S _ { t } - \kappa _ { 2 } \left| \phi _ { t + 1 } ^ { ( \ell , O ) } - \phi _ { t } ^ { ( \ell , O ) } \right| O _ { t } ( T ^ { * } ) .
$$

The parameter l is optimized by minimizing one of the three objective functions computed on the entire learning set:

$$
\begin{array} { r l } & { \hat { \mathcal { O } } ^ { ( \mathrm { M S E } ) } ( \ell ) = \displaystyle \frac { 1 } { N } \sum _ { i = 1 } ^ { N } \left( \xi _ { T , i } ^ { \phi ^ { ( \ell ) } } \right) ^ { 2 } } \\ & { \hat { \mathcal { O } } ^ { ( \mathrm { S M S E } ) } ( \ell ) = \displaystyle \frac { 1 } { N } \sum _ { i = 1 } ^ { N } \left( \xi _ { T , i } ^ { \phi ^ { ( \ell ) } } \right) ^ { 2 } \mathbb { 1 } _ { \left\{ \xi _ { T , i } ^ { \phi } \geq 0 \right\} } } \\ & { \hat { \mathcal { O } } ^ { ( \mathrm { C V a R } ) } ( \ell ) = \widehat { \mathrm { V a R } } _ { \alpha } + \displaystyle \frac { 1 } { ( 1 - \alpha ) N } \sum _ { i = 1 } ^ { N } \operatorname* { m a x } \left( \xi _ { T , i } ^ { \phi ^ { ( \ell ) } } - \widehat { \mathrm { V a R } } _ { \alpha } , 0 \right) } \end{array}
$$

where $\xi _ { T , i } ^ { \phi ^ { ( \ell ) } } = \mathcal { P } _ { T , i } - V _ { T , i } ^ { \phi ^ { ( \ell ) } }$ and $\widehat { \mathrm { V a R } } _ { \alpha } = \xi _ { T , [ [ \alpha \cdot N ] ] } ^ { \phi ^ { ( \ell ) } }$ is the value-at-risk estimate derived from the ordered sample $\left\{ \xi _ { T , [ i ] } ^ { \phi ^ { ( \ell ) } } \right\} _ { i = 1 } ^ { N }$

## E Impact of state variable inclusion on hedging performance

To evaluate the impact of including state variables $\mathcal { P } _ { t } , \ \Delta _ { t } ^ { P }$ , and $\gamma _ { t } ^ { P }$ in the reinforcement learning framework, we conduct additional numerical experiments. Specifically, we compare the performance of RL agents trained with and without these variables across various risk measures. Table 2 demonstrates that the inclusion of state variables consistently improves hedging performance because they provide additional structure, which helps with the training

<!-- page: 47 -->

[Table source crop](assets/tables/2025-francois-et-al-deep-hedging-iv-surface-p0047-block-0001-ba0bb0102e8ebc74.jpg)
Table 2: Optimal risk measure values for different state space configurations.

## F Statistical arbitrage

This analysis examines whether our framework can embed a speculative layer, such as statistical arbitrage, by leveraging the structural properties of the risk measure that guides the hedging optimization process.

Following the definition in Assa and Karai (2013) and studies such as Buehler et al. (2021), Horikawa and Nakagawa (2024), and François et al. (2025), we define statistical arbitrage strategies as profit-seeking trading strategies that exploit the blind spots of the risk measure. Specifically, we assess whether the difference between RL strategies, $\phi ^ { R L }$ , and DG strategies, $\phi ^ { D G }$ , denoted as

$$
\phi ^ { - } = \phi ^ { R L } - \phi ^ { D G } ,
$$

exhibits statistical arbitrage characteristics with respect to a risk measure $\rho .$ More precisely, we examine whether

$$
\rho \left( - V _ { T } ^ { \phi ^ { - } } ( 0 ) \right) < 0
$$

<!-- page: 48 -->

occurs. This condition implies that the strategy that requires no initial investment is strictly less risky than a null investment according to $\rho .$ We investigate whether $\phi ^ { - }$ behaves as statistical arbitrage within our framework, analyzing whether RL merely introduces a speculative component to the DG strategy or if another mechanism is at play. This analysis is conducted using $\mathrm { C V a R _ { 9 5 \% } }$ and SMSE as risk measures.

Table 3 presents the hedging error risk associated with the trading strategy $\phi ^ { - }$ , which represents the differential position between the RL and DG strategies. This analysis is conducted across the strategies obtained under different risk measures while hedging an ATM straddle intrument with a maturity of $T = 6 3$ days.

[Table source crop](assets/tables/2025-francois-et-al-deep-hedging-iv-surface-p0048-block-0003-70b91a2a106ca823.jpg)
Table 3: Statistical arbitrage statistic.

Our numerical results show no evidence of statistical arbitrage, as all hedging error risks produce positive values. To further illustrate the absence of arbitrage-like behavior, Figure 14 presents the profit and losses (P&L) of the strategy $\phi ^ { - }$ at time $T$ with no initial investment, considering two scenarios: one without transaction costs and another with transaction cost levels set at 0.05% for $\kappa _ { 1 }$ and 0.5% for $\kappa _ { 2 }$ . The three panels display distributions that are either symmetric around zero or shifted to the left, indicating the absence of profit-seeking trading strategies. This reinforces the conclusion that the RL strategies within our framework are solely focused on hedging, without introducing speculative overlays.

<!-- page: 49 -->

![](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0049-block-0002-e61d55acb560b4cd.jpg)

![Figure 14: P&L distribution for the strategy $\phi ^ { - }$](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0049-block-0003-02ebe23eb0eef33e.jpg)

![Distributions are computed using 100,000 out-of-sample paths. The P&L is simply defined by the portfolio value $V _ { T } ^ { \phi ^ { - } } ( 0 )$ at maturity. The hedge consists of an ATM straddle with a maturity of $T = 6 3$ days. The hedging instrument is an ATM call option with a maturity of $T ^ { * } = 8 4$ days.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0049-block-0004-0f6c50460a4c3e5f.jpg)

<!-- page: 50 -->

## Supplementary material (not part of the paper)

## G Systematic outperformance of RL agents

We validate the outperformance of RL agents by hedging a straddle instrument with a maturity of $T = 6 3$ days, incorporating an ATM call option with a maturity of $T ^ { * } = 8 4$ days as a hedging instrument. In this validation, we analyze the empirical distribution of each risk measure under transaction cost levels set to $\kappa _ { 1 } = 0 . 0 5 \%$ and $\kappa _ { 2 } = 0 . 5 \%$ for simplicity. The empirical distributions are derived by bootstrapping the hedging error over 100,000 paths, with batches of size 1,000. As shown in Figure 15, the RL approach consistently outperforms the delta gamma strategy, as evidenced by the non-overlapping empirical distributions.

![Figure 15: Empirical distribution of risk measures.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0050-block-0004-5dd874121de612cd.jpg)

![](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0050-block-0005-6f121d9d3e12a7b5.jpg)

![Results are computed using bootstrapping with a sample size of 1,000 over 100,000 out-of-sample paths according to the conditions outlined in Section 4.3.1. The hedge consists of an ATM straddle with a maturity of $T = 6 3$ days and an average value of \$7.55. The hedging instrument is an ATM call option with a maturity of $T ^ { * } = 8 4$ days. Transaction cost levels are set to 0.05% for $\kappa _ { 1 }$ and 0.5% for $\kappa _ { 2 }$](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0050-block-0006-b790ff0c3e1017b3.jpg)

<!-- page: 51 -->

## H JIVR Model parameters

The standardized NIG random variable € has the two-parameter NIG density function

$$
f ( x ) = \frac { B _ { 1 } \left( \sqrt { \frac { \varphi ^ { 6 } } { \varphi ^ { 2 } + \zeta ^ { 2 } } + \left( \varphi ^ { 2 } + \zeta ^ { 2 } \right) \left( x + \frac { \varphi ^ { 2 } \zeta } { \varphi ^ { 2 } + \zeta ^ { 2 } } \right) ^ { 2 } } \right) } { \pi \sqrt { \frac { 1 } { \varphi ^ { 2 } + \zeta ^ { 2 } } + \frac { \varphi ^ { 2 } + \zeta ^ { 2 } } { \varphi ^ { 6 } } \left( x + \frac { \varphi ^ { 2 } \zeta } { \varphi ^ { 2 } + \zeta ^ { 2 } } \right) ^ { 2 } } } e ^ { \left( \frac { \varphi ^ { 4 } } { \varphi ^ { 2 } + \zeta ^ { 2 } } + \zeta \left( x + \frac { \varphi ^ { 2 } \zeta } { \varphi ^ { 2 } + \zeta ^ { 2 } } \right) \right) } ,
$$

where $B _ { 1 } ( \cdot )$ denotes the modified Bessel function of the second kind with index 1. The standard four-parameter $( \alpha , \beta , \delta , \mu )$ density function can be recovered by setting $\beta = \zeta$ and ${ \sqrt { \alpha ^ { 2 } - \beta ^ { 2 } } } = \varphi$ , while enforcing a zero mean and unit variance to express $\delta$ and $\mu$ in terms of αand $\beta$ . The parameters governing the excess return component of the model are given by

$$
\begin{array} { r } { ( \Theta _ { R } = ( \lambda , \kappa _ { R } , \gamma _ { R } , a _ { R } , \omega _ { R } , \zeta _ { R } , \varphi _ { R } ) . } \end{array}
$$

Parameters for the IV coefficient marginal processes are denoted

$$
\{ \Theta _ { i } = ( \omega _ { 1 } , \alpha _ { i } , \theta _ { i , 1 } , \theta _ { i , 2 } , \theta _ { i , 3 } , \theta _ { i , 4 } , \theta _ { i , 5 } , \nu , \sigma _ { i } , \kappa _ { i } , a _ { i } , \gamma _ { i } , \zeta _ { i } , \varphi _ { i } ) \} _ { i = 1 } ^ { 5 } .
$$

<!-- page: 52 -->

[Table source crop](assets/tables/2025-francois-et-al-deep-hedging-iv-surface-p0052-block-0001-a6ffe437b00f054a.jpg)
Table 4: Estimated Gaussian copula parameters.

[Table source crop](assets/tables/2025-francois-et-al-deep-hedging-iv-surface-p0052-block-0002-e76a1c16d6857c78.jpg)
Table 5: JIVR model parameter estimates.

<!-- page: 53 -->

## I Impact of no-trade regions

Since the no-trade region is determined by the rebalancing threshold, we assess its impact by examining how it influences both the rebalancing frequency and hedging cost. The rebalancing frequency, defined as the proportion of days on which portfolio positions are adjusted along a given path, is given by

$$
\mathrm { R F } _ { l } = \frac { 1 } { T } \sum _ { t = 0 } ^ { T - 1 } \mathbb { 1 } _ { \{ \phi _ { t + 1 } \neq \phi _ { t } \} } .\tag{12}
$$

The hedging cost

$$
\mathrm { H C } _ { l } = \sum _ { t = 0 } ^ { T - 1 } e ^ { - r \Delta t } \mathcal { H } \mathcal { C } _ { t } ,\tag{13}
$$

is the sum of discounted transaction costs over a given path where the transaction cost at time $t , \mathcal { H } \mathcal { C } _ { t }$ , is

$$
\mathcal { H C } _ { t } = \kappa _ { 1 } S _ { t } \mid \phi _ { t + 1 } ^ { ( S ) } - \phi _ { t } ^ { ( S ) } \mid + \kappa _ { 2 } \mathrm { O } _ { t } ( T ^ { * } ) \mid \phi _ { t + 1 } ^ { ( \mathrm { O } ) } - \phi _ { t } ^ { ( \mathrm { O } ) } \mid .\tag{14}
$$

This analysis evaluates the trade-off between portfolio adjustment frequency and transaction costs. Figure 16 illustrates the effect of the transaction costs on both rebalancing frequency and hedging cost across all risk measures and transaction cost levels.

<!-- page: 54 -->

![Figure 16: Rebalancing frequency and average hedging transaction costs.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0054-block-0001-99c5e6468ef0856e.jpg)

![](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0054-block-0002-1396265e772d7c71.jpg)

![](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0054-block-0003-000323435dd9c8f4.jpg)

![](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0054-block-0004-562d21958beec9aa.jpg)

![](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0054-block-0005-f90fe0f95e42ba53.jpg)

![Results are computed over 100,000 out-of-sample paths according to the conditions outlined in Section 4.3.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0054-block-0006-760904d0a731aeaf.jpg)

Results depicted in Figure 16 show that RL agents resort to a higher average rebalancing frequency compared to DG strategies, which tend to behave more like semi-static approaches with fewer rebalancing days. This finding aligns with the observations of Carr and Wu (2014), who show that increasing the rebalancing frequency does not necessarily improve the performance of option tracking frameworks such as delta hedging in the presence of transaction cost.

Conversely, as $\kappa _ { 2 }$ increases, RL agents retain high rebalancing frequency, but keep average transaction costs to a level similar to DG. Thus, more gradual and frequent adjustments from

<!-- page: 55 -->

RL mitigate risk more effectively than DG as documented in Section 4.4.2, while leading to similar transaction costs.

## J Soft constraint regularization

The estimation of the penalization parameter λ introduced in Equation (6), which governs the weight of the soft constraint in the optimization process, is approached as a model selection problem. In this framework, the model is trained multiple times using fixed values of λ, iterating across four different values for λ.

The optimal λ is then selected based on an evaluation conducted on the validation set,15 considering two key factors: the soft constraint value and the risk measure. To determine the optimal λ, we hedge an ATM straddle with a maturity of $T = 6 3$ days, assuming no transaction costs $( \kappa _ { 1 } = \kappa _ { 2 } = 0 \% )$ . The hedging strategy optimization considers three risk measures: MSE, SMSE, and $\mathrm { C V a R _ { 9 5 \% } }$ . This process is repeated for different values of λ: 0, 0.5, 1, and 1.5. Figure 17 presents the optimal soft constraint values and risk measure outcomes for each λ, evaluated on a validation set.

15The validation set consists of 100,000 independent simulated paths, generated as outlined in Section 4.1. This set is distinct from the training and test sets described in Section 4.3.1.

<!-- page: 56 -->

![Figure 17: Risk measure and soft constraint values. Results are computed over 100,000 out-of-sample paths according to the conditions outlined in Section 4.3.1. The hedge consists of an ATM straddle with a maturity of $T = 6 3$ days and an average value of \$7.55. The hedging instrument is an ATM call option with a maturity of $T ^ { * } = 8 4$ days.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0056-block-0001-44e50ae3aabb99bd.jpg)

The results illustrated in Figure 17 highlight the heightened sensitivity to variations in the penalization parameter λ when using asymmetric risk measures. The SMSE risk measure exhibits significant sensitivity of $\rho ,$ achieving its minimum value at λ = 1, which aligns with the corresponding minimum value of the soft constraint penalty. For the CVaR, the soft constraint penalty demonstrates greater sensitivity compared to the risk measure itself, indicating that CVaR is more susceptible to higher tracking error in the absence of the soft constraint.

The minimum value of the soft constraint penalty for CVaR also occurs at λ = 1, corresponding to the stabilization point of the risk measure. In contrast, the MSE risk measure is mildly affected by the soft constraint. Yet its minimum value is also observed at λ = 1, mirroring the behavior of the other risk measures.

<!-- page: 57 -->

Based on these findings, we select λ = 1 for our subsequent experiments. This value leads to soft constraint penalty levels that remain below 0.025% across all risk measures, minimizing the likelihood of observing paths with large tracking error.

## K In-sample backtest

In this section, we benchmark our approach using historical paths generated by the JIVR model, covering the period from January 5, 1996, to December 31, 2020, to assess the effectiveness of RL agents. This experiment evaluates the performance of risk management strategies based on the historical series $( R _ { t } , \beta _ { t } )$ . Hedging performance is assessed by introducing a new ATM straddle instrument with a 63-day maturity every 21 business days along the historical paths. The initial hedging portfolio values are set equal to the straddle prices, which are computed using the prevailing implied volatility surface on the day the hedge is initiated.

To evaluate the robustness of our approach under diverse market conditions, we compare cumulative P&Ls. The cumulative P&L at a given date is defined as the sum of the total P&L generated by all straddle trades whose hedging period has expired. Figure 18 illustrates the evolution of cumulative P&Ls, where each of the two panels correspond to different transaction cost levels

<!-- page: 58 -->

![Figure 18: Cumulative P&L for the hedge of ATM straddles under real asset price dynamics.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0058-block-0001-07c782a8f91acb79.jpg)

![Results are computed based on the observed P&L from hedging 296 straddle positions with maturity 63-days under real market conditions observed from May 1, 1996, to December 31, 2020. A new ATM straddle is considered every 21 business days. Agents are trained according to the conditions outlined in Section 4.3 using an ATM call option with a maturity of $T ^ { * } = 8 4$ days as the hedging instrument.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0058-block-0002-a06f1aebc953d597.jpg)

As illustrated in Figure 18, RL strategies consistently outperform the benchmarks in both scenarios, namely with and without transaction costs. Notably, the gap between the cumulative P&L of RL agents and the benchmarks widens significantly as transaction costs increase, highlighting the adaptability of the RL approach to transaction costs across diverse market conditions. Additionally, RL strategies optimized using the MSE function yield lower cumulative P&L compared to those optimized with asymmetric risk measures, reflecting the inherent differences in the objectives of these risk measures.

To evaluate hedging errors under real asset price dynamics, we analyze the distribution of terminal errors generated by 296 ATM straddles from May 1, 1996, to December 31, 2020. Figure 19 presents the histogram of hedging errors for benchmark strategies and RL agents across all risk measures, without transaction costs.

<!-- page: 59 -->

![Figure 19: Hedging error distribution for a ATM straddle instrument with a maturity of 63 days under real asset price dynamics.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0059-block-0001-a77361387d388d52.jpg)

![](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0059-block-0002-2db541e579ae28cb.jpg)

![Results are computed based on the observed P&L from hedging 296 ATM straddle instruments with maturity of $T = 6 3$ under real market conditions observed from May 1, 1996, to December 31, 2020. The hedging instrument is an ATM call option with a maturity of $T ^ { * } = 8 4$ days. Transaction cost levels are set to 0%.](assets/figures/2025-francois-et-al-deep-hedging-iv-surface-p0059-block-0003-809ace3a127a89ca.jpg)

As shown in Figure 19, RL strategies exhibit a hedging error distribution that is shifted towards the left, highlighting greater profitability and lower downside risk. These findings highlight the robustness of the RL approach to different market conditions and transaction cost levels.
