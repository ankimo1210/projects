# A stochastic model for order book dynamics

Rama Cont, Sasha Stoikov, Rishi Talreja IEOR Dept, Columbia University, New York rama.cont@columbia.edu, sashastoikov@gmail.com, rt2146@columbia.edu

We propose a stochastic model for the continuous-time dynamics of a limit order book. The model strikes a balance between two desirable features: it captures key empirical properties of order book dynamics and its analytical tractability allows for fast computation of various quantities of interest without resorting to simulation. We describe a simple parameter estimation procedure based on high-frequency observations of the order book and illustrate the results on data from the Tokyo stock exchange. Using Laplace transform methods, we are able to efficiently compute probabilities of various events, conditional on the state of the order book: an increase in the mid-price, execution of an order at the bid before the ask quote moves, and execution of both a buy and a sell order at the best quotes before the price moves. Comparison with highfrequency data shows that our model can capture accurately the short term dynamics of the limit order book.

Key words : Limit order book, financial engineering, Laplace transform inversion, queueing systems, simulation.

## Contents

|   1 Introduction | 1 Introduction                                                    | 1 Introduction                                                                 |   3 |
|------------------|-------------------------------------------------------------------|--------------------------------------------------------------------------------|-----|
|                2 | A continuous-time model for a stylized limit order book           | A continuous-time model for a stylized limit order book                        |   4 |
|                  | 2.1                                                               | Limit order books . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .  |   4 |
|                  | 2.2                                                               | Dynamics of the order book . . . . . . . . . . . . . . . . . . . . . . . . .   |   5 |
|                3 | Parameter estimation                                              | Parameter estimation                                                           |   5 |
|                  | . . . . . . . . . . . . . . . . . . . . .                         | . . . . . . . . . . . . . . . . . . . . .                                      |   6 |
|                  | 3.1                                                               | Description of the data set . . . . .                                          |   6 |
|                  | 3.2                                                               | Estimation procedure . . . . . . . . . . . . . . . . . . . . . . . . . . . .   |   7 |
|                4 |                                                                   |                                                                                |   7 |
|                  | Laplace transform methods for computing conditional probabilities | Laplace transform methods for computing conditional probabilities              |   8 |
|                  | 4.1                                                               | Laplace transforms and first-passage times of birth-death processes . . .      |   9 |
|                  | 4.2                                                               | Direction of price moves . . . . . . . . . . . . . . . . . . . . . . . . . . . |  10 |
|                  | 4.3                                                               | Executing an order before the mid-price moves . . . . . . . . . . . . . .      |  12 |
|                  | 4.4                                                               | Making the spread . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .  |  13 |
|                5 | Numerical Results                                                 | Numerical Results                                                              |  15 |
|                  | 5.1 Long term behavior . . . . . . . . . . . . . . .              | . . . . . . . . . . . . . .                                                    |  15 |
|                  | 5.1.1                                                             | Steady state shape of the book . . . . . . . . . . . . . . . . . . .           |  15 |
|                  | 5.1.2                                                             | Volatility . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .       |  15 |
|                  | 5.2                                                               | Conditional distributions . . . . . . . . . . . . . . . . . . . . . . . . . .  |  16 |
|                  | 5.2.1 One-step transition probabilities . . . . . . . . . .       | . . . . . . . .                                                                |  16 |
|                  | 5.2.2                                                             | Direction of price moves . . . . . . . . . . . . . . . . . . . . . . .         |  17 |
|                  | 5.2.3                                                             | Executing an order before the mid-price moves . . . . . . . . . .              |  18 |
|                  | 5.2.4                                                             | Making the spread . . . . . . . . . . . . . . . . . . . . . . . . . .          |  18 |
|                6 | Conclusion                                                        | Conclusion                                                                     |  18 |

## 1. Introduction

The evolution of prices in financial markets results from the interaction of buy and sell orders through a rather complex dynamic process. Studies of the mechanisms involved in trading financial assets have traditionally focused on quote-driven markets, where a market maker or dealer centralizes buy and sell orders and provides liquidity by setting bid and ask quotes. The NYSE specialist system is an example of this mechanism. In recent years, Electronic Communications Networks (ECN's) such as Archipelago, Instinet, Brut and Tradebook have captured a large share of the order flow by providing an alternative order-driven trading system. These electronic platforms aggregate all outstanding limit orders in a limit order book that is available to market participants and market orders are executed against the best available prices. As a result of the ECN's popularity, established exchanges such as the NYSE, Nasdaq, the Tokyo Stock Exchange and the London Stock Exchange have adopted electronic order-driven platforms, either fully or partially through 'hybrid' systems.

The absence of a centralized market maker, the mechanical nature of execution of orders and -last but not least- the availability of data have made order-driven markets interesting candidates for stochastic modelling . At a fundamental level, models of order book dynamics may provide some insight into the interplay between order flow, liquidity and price dynamics Bouchaud et al. (2002), Smith et al. (2003), Farmer et al. (2004), Foucault et al. (2005). At the level of applications, such models provide a quantitative framework for investors and trading desks to optimize trade execution strategies Alfonsi et al. (2007), Obizhaeva and Wang (2006). An important motivation for modelling high-frequency dynamics of order books is to use the information on the current state of the order book to predict its short-term behavior. The focus is therefore on conditional probabilities of events, given the state of the order book.

The dynamics of a limit order book resembles in many aspects that of a queuing system. Limit orders wait in a queue to be executed against market orders (or canceled). Drawing inspiration from this analogy, we model a limit order book as a continuous-time Markov process that tracks the number of limit orders at each price level in the book. The model strikes a balance between three desirable features: it can be easily calibrated to high-frequency data, reproduces various empirical features of order books and is analytically tractable. In particular, we show that our model is simple enough to allow the use of Laplace transform techniques from the queueing literature to compute various conditional probabilities . These include the probability of the mid-price increasing in the next move, the probability of executing an order at the bid before the ask quote moves and the probability of executing both a buy and a sell order at the best quotes before the price moves, given the state of the order book. We illustrate these computations in a model estimated from order book data for a stock on the Tokyo stock exchange.

Related literature. Various recent studies have focused on limit order books. Given the complexity of the structure and dynamics of order books, it has been difficult to construct models that are both statistically realistic and amenable to rigorous quantitative analysis. Parlour (1998) and Foucault et al. (2005), Rosu (forthcoming) propose equilibrium models of limit order books. These models provide interesting insights into the price formation process but contain unobservable parameters that govern agent preferences. Thus, they are difficult to estimate and use in applications. Some empirical studies on properties of limit order books are Bouchaud et al. (2002), Farmer et al. (2004), and Hollifield et al. (2004). These studies provide an extensive list of statistical features of order book dynamics which are challenging to incorporate in a single model. Bouchaud et al. (2008), Smith et al. (2003), Bovier et al. (2006), Luckock (2003), and Maslov and Mills (2001) propose stochastic models of order book dynamics in the spirit of the one proposed here but focus on unconditional / steady-state distributions of various quantities rather than the conditional quantities we focus on here.

The model proposed here is admittedly simpler in structure than some others existing in the literature: it does not incorporate strategic interaction of traders as in game theoretic approaches Parlour (1998), Foucault et al. (2005) and Rosu (forthcoming), nor does it account for 'long memory' features of the order flow as pointed out by Bouchaud et al. (2002) and Bouchaud et al. (2008). However, contrarily to these models, it leads to an analytically tractable framework where parameters can be easily estimated from empirical data and various quantities of interest may be computed efficiently.

Outline. The paper is organized as follows. § 2 describes a stylized model for the dynamics of a limit order book, where the order flow is described by independent Poisson processes. Estimation of model parameters from high-frequency order book time series data is described in § 3 and illustrated using data from the Tokyo Stock Exchange. In § 4 we show how this model can be used to compute conditional probabilities of various types of events relevant for trade execution using Laplace transform methods. § 5 explores steady state properties of the model using Monte Carlo simulation and compares conditional probabilities computed by simulation to those computed with the Laplace transform methods presented in § 4.

## 2. A continuous-time model for a stylized limit order book

## 2.1. Limit order books

Consider a financial asset traded in an order-driven market. Market participants can post two types of buy/sell orders. A limit order is an order to trade a certain amount of a security at a given price. Limit orders are posted to a electronic trading system and the state of outstanding limit orders can be summarized by stating the quantities posted at each price level: this is known as the limit order book . The lowest price for which there is an outstanding limit sell order is called the ask price and the highest buy price is called the bid price .

A market order is an order to buy/sell (a certain quantity of) the asset at the best available price in the limit order book. When a market order arrives it is matched with the best available price in the limit order book and a trade occurs. The quantities available in the limit order book are updated accordingly.

A limit order sits in the order book until it is either executed against a market order or it is canceled. A limit order may be executed very quickly if it corresponds to a price near the bid and the ask, but may take a long time if the market price moves away from the requested price or if the requested price is too far from the bid/ask. Alternatively, a limit order can be canceled at any time.

We consider a market where limit orders can be placed on a price grid { 1 , . . . , n } representing multiples of a price tick. We track the state of the order book with a continuous-time process X ( t ) ≡ ( X 1 ( t ) , . . . , X n ( t )) t ≥ 0 , where | X p ( t ) | is the number of outstanding limit orders at price p , 1 ≤ p ≤ n . If X p ( t ) &lt; 0, then there are -X p ( t ) bid orders at price p ; if X p ( t ) &gt; 0, then there are X p ( t ) ask orders at price p .

The ask price p A ( t ) at time t is then defined by

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0001" status="decoded_unverified" source-page="4" -->
$$
p _ { A } ( t ) = \inf \{ p = 1 , \dots , n , \ X _ { p } ( t ) > 0 \} \wedge ( n + 1 ) . \\
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0001](images/formula_0001.png)
```text
PDF text layer: p A ( t ) = inf { p =1 , . . . , n, X p ( t ) > 0 }∧ ( n +1) .
```
*Formula quality: `decoded_unverified`; source PDF page 4. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

Similarly, the bid price p B ( t ) is defined by

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0002" status="decoded_unverified" source-page="4" -->
$$
p _ { B } ( t ) \equiv \sup \{ p = 1 , \dots , n , \ X _ { p } ( t ) < 0 , \ \} \vee 0 \\ \\
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0002](images/formula_0002.png)
```text
PDF text layer: p B ( t ) ≡ sup { p =1 , . . . , n, X p ( t ) < 0 , }∨ 0
```
*Formula quality: `decoded_unverified`; source PDF page 4. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

Notice that when there are no ask orders in the book we force an ask price of n +1 and when there are no bid orders in the book we force a bid price of 0. The mid-price p M ( t ) and the bid-ask spread s ( t ) are defined by

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0003" status="decoded_unverified" source-page="4" -->
$$
p _ { M } ( t ) \equiv \frac { p _ { B } ( t ) + p _ { A } ( t ) } { 2 } \quad \text {and} \quad s ( t ) \equiv p _ { A } ( t ) - p _ { B } ( t ) .
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0003](images/formula_0003.png)
```text
PDF text layer: p M ( t ) ≡ p B ( t ) + p A ( t ) 2 and s ( t ) ≡ p A ( t ) -p B ( t ) .
```
*Formula quality: `decoded_unverified`; source PDF page 4. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

Since most of the trading activity takes place in the vicinity of the bid and ask prices, it is useful to keep track of the number of outstanding orders at a given distance from the bid/ask. To this end, we define

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0004" status="decoded_unverified" source-page="5" -->
$$
Q _ { i } ^ { B } ( t ) = \begin{cases} X _ { p _ { A } ( t ) - i } ( t ) & 0 < i < p _ { A } ( t ) \\ 0 & p _ { A } ( t ) \leq i < n , \end{cases} \quad ( 1 ) \\ \text {orders at a distance} \, i \, \text { from the ask and}
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0004](images/formula_0004.png)
```text
PDF text layer: Q B i ( t ) = { X p A ( t ) -i ( t ) 0 <i<p A ( t ) 0 p A ( t ) ≤ i < n, (1)
```
*Formula quality: `decoded_unverified`; source PDF page 5. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

the number of buy orders at a distance i from the ask and

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0005" status="decoded_unverified" source-page="5" -->
$$
Q _ { i } ^ { A } ( t ) = \begin{cases} X _ { p _ { B } ( t ) + i } ( t ) & 0 < i < n - p _ { B } ( t ) \\ 0 & n - p _ { B } ( t ) \leq i < n , \end{cases} ( 2 ) \\
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0005](images/formula_0005.png)
```text
PDF text layer: Q A i ( t ) = { X p B ( t )+ i ( t ) 0 <i<n -p B ( t ) 0 n -p B ( t ) ≤ i < n, (2)
```
*Formula quality: `decoded_unverified`; source PDF page 5. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

the number of sell orders at a distance i from the bid. Although X ( t ) and ( p A ( t ) , p B ( t ) , Q A ( t ) , Q B ( t )) contain the same information, the second representation highlights the shape or depth of the book relative to the best quotes.

## 2.2. Dynamics of the order book

Let us now describe how the limit order book is updated by the inflow of new orders. For a state x ∈ Z n and 1 ≤ p ≤ n , define

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0006" status="decoded_unverified" source-page="5" -->
$$
x _ { p \pm 1 } & \equiv x \pm ( 0 , \dots , 1 , \dots , 0 ) , \\ + l _ { p } \min i t s = & \quad ( 0 , \dots , 1 , \dots , 0 ) , \\ + l _ { p } ( x ) & = \min i t s + 1 ,
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0006](images/formula_0006.png)
```text
PDF text layer: x p ± 1 ≡ x ± (0 , . . . , 1 , . . . , 0) ,
```
*Formula quality: `decoded_unverified`; source PDF page 5. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

where the 1 in the vector on the right-hand side is in the p -th component. Assuming that all orders are of unit size (in empirical examples we will take this unit to be the average size of limit orders observed for the asset),

- a limit buy order at price level p &lt; p A ( t ) increases the quantity at level p : x → x p -1
- a market buy order decreases the quantity at the ask price: x → x p A ( t ) -1
- a limit sell order at price level p &gt; p B ( t ) increases the quantity at level p : x → x p +1
- a market sell order decreases the quantity at the bid price: x → x p B ( t )+1
- a cancellation of an oustanding limit sell order at price level p &gt; p B ( t ) decreases the quantity at level p : x → x p -1
- a cancellation of an oustanding limit buy order at price level p &lt; p A ( t ) decreases the quantity at level p : x → x p +1

The evolution of the order book is thus driven by the incoming flow of market orders, limit orders and cancellations at each price level, each of which can be represented as a counting process. It is empirically observed Bouchaud et al. (2002) that incoming orders arrive more frequently in the vicinity of the current bid/ask price and the rate of arrival of these orders depends on the distance to the bid/ask.

To capture these empirical features in a model that is analytically tractable and allows to compute quantities of interest in applications -most notably conditional probabilities of various eventswe propose a stochastic model where the events outlined above are modelled using independent Poisson processes. More precisely, we assume that, for i ≥ 1,

- Limit buy (resp. sell) orders arrive at a distance of i ticks from the opposite best quote at independent, exponential times with rate λ ( i ),
- Market buy (resp. sell) orders arrive at independent, exponential times with rate μ ,
- Cancellations of limit orders at a distance of i ticks from the opposite best quote occur at a rate proportional to the number of outstanding orders: if the number of outstanding orders at that level is x then the cancellation rate is θ ( i ) x . This assumption can be understood as follows: if we have a batch of x outstanding orders, each of which can be canceled at an exponential time with parameter θ ( i ), then the overall cancellation rate for the batch is θ ( i ) x .

- The above events are mutually independent.

Typically, the arrival rates λ : { 1 , . . . , n } → [0 , ∞ ) are decreasing functions of the distance to the bid/ask: most orders are placed close to the current price. Empirical studies suggest a power law

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0007" status="decoded_unverified" source-page="6" -->
$$
\lambda ( i ) = \frac { k } { i ^ { \alpha } }
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0007](images/formula_0007.png)
```text
PDF text layer: λ ( i ) = k i α
```
*Formula quality: `decoded_unverified`; source PDF page 6. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

as a plausible specification (see Zovko and Farmer (2002) or Bouchaud et al. (2002)).

Given the above assumptions, X is a continuous-time Markov chain with state space Z n and transition rates given by

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0008" status="decoded_unverified" source-page="6" -->
$$
x & \to x _ { p - 1 } \quad \text {with rate} \quad \lambda ( p _ { A } ( t ) - p ) \quad \text {for } p < p _ { A } ( t ) , \\ x & \to x _ { p + 1 } \quad \text {with rate} \quad \lambda ( p - p _ { B } ( t ) ) \quad \text {for } p > p _ { B } ( t ) , \\ x & \to x _ { p _ { B } ( t ) + 1 } \quad \text {with rate} \quad \mu \\ x & \to x _ { p _ { A } ( t ) - 1 } \quad \text {with rate} \quad \mu \\ x & \to x _ { p + 1 } \quad \text {with rate} \ \theta ( p _ { A } ( t ) - p ) | x _ { p } | \quad \text {for } p < p _ { A } ( t ) , \\ x & \to x _ { p - 1 } \quad \text {with rate} \ \theta ( p - p _ { B } ( t ) ) | x _ { p } | \quad \text {for } p > p _ { B } ( t ) , \\
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0008](images/formula_0008.png)
```text
PDF text layer: x → x p -1 with rate λ ( p A ( t ) -p ) for p < p A ( t ), x → x p +1 with rate λ ( p -p B ( t )) for p > p B ( t ), x → x p B ( t )+1 with rate μ x → x p A ( t ) -1 with rate μ x → x p +1 with rate θ ( p A ( t ) -p ) | x p | for p < p A ( t ), x → x p -1 with rate θ ( p -p B ( t )) | x p | for p > p B ( t ),
```
*Formula quality: `decoded_unverified`; source PDF page 6. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

Proposition 1 X is an ergodic Markov process. In particular, X has a proper stationary distribution.

Proof. Define N ≡ ( N ( t ) , t ≥ 0), where N ( t ) ≡ ∑ n i =1 | X i ( t ) | . Then X ( t ) = (0 , . . . , 0) if and only if N ( t ) = 0. But N is simply a birth-death process with birth rate bounded from above by λ ≡ 2 ∑ n i =0 λ ( i ) and death rate in state i , μ i ≡ 2 μ + iθ . Then, we have the inequalities

and

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0009" status="decoded_unverified" source-page="6" -->
$$
\sum _ { i = 1 } ^ { \infty } \frac { \lambda ^ { i } } { \mu _ { 1 } \cdots \mu _ { i } } < \sum _ { i = 1 } ^ { \infty } \frac { 1 } { i ! } \left ( \frac { \lambda } { \theta } \right ) ^ { i } = e ^ { \frac { \lambda } { \theta } } - 1 < \infty ,
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0009](images/formula_0009.png)
```text
PDF text layer: ∞ ∑ i =1 λ i μ 1 · · · μ i < ∞ ∑ i =1 1 i ! ( λ θ ) i = e λ θ -1 < ∞ ,
```
*Formula quality: `decoded_unverified`; source PDF page 6. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0010" status="decoded_unverified" source-page="6" -->
$$
\sum _ { i = 1 } ^ { \infty } \frac { \mu _ { 1 } \cdots \mu _ { i } } { \lambda ^ { i } } > \sum _ { i = 1 } ^ { M } \frac { \mu _ { 1 } \cdots \mu _ { i } } { \lambda ^ { i } } + \sum _ { i = M + 1 } ^ { \infty } \left ( \frac { 2 \mu + M \theta } { \lambda } \right ) ^ { i } = \infty , \\ \intertext { s o n e l g r a l e g e n u o g h s o t a t h a t 2 \mu + M \theta > \lambda . T h e r e f o r e , b y ( A s m u s e n 2003 , C }
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0010](images/formula_0010.png)
```text
PDF text layer: ∞ ∑ i =1 μ 1 · · · μ i λ i > M ∑ i =1 μ 1 · · · μ i λ i + ∞ ∑ i = M +1 ( 2 μ + Mθ λ ) i = ∞ ,
```
*Formula quality: `decoded_unverified`; source PDF page 6. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

for M&gt; 0 chosen large enough so that 2 μ + Mθ&gt;λ . Therefore, by (Asmussen 2003, Corollary 2.5) the birth-death process is ergodic. Since X is clearly irreducible, it follows that X is also ergodic. □

The ergodicity of X is a desirable feature: it allows to compare time averages of various quantities (average shape of the order book, average price impact, etc.) to expectations of these quantities computed in the model. The steady-state behavior of X will be further discussed in § 5.1.

## 3. Parameter estimation

## 3.1. Description of the data set

Our data consists of time-stamped sequences of trades (market orders) and quotes (prices, quantities of outstanding limit orders) for the 5 best price levels on each side of the order book, for stocks traded on the Tokyo stock exchange. This data set, referred to as Level II order book data, provides a more detailed view of price dynamics than the Trade and Quotes (TAQ) data often used for high frequency data analysis, which consist of prices and sizes of trades (market orders) and time-stamped updates in the price and size of the bid and ask quotes.

In Table 1, we display a sample of three consecutive trades for Sky Perfect Communications. Each row provides the time, size and price of a market order. We also display a sample of Level II bid side quotes. Each row displays the 5 bid prices (pb1, pb2, pb3, pb4 and pb5), as well as the quantity of shares bid at these respective prices (qb1, qb2, qb3, qb4, qb5).

Table 1 A sample of 3 trades and 5 quotes for Sky Perfect Communications

| time    |   price |   size |
|---------|---------|--------|
| 9:11:01 |   74300 |      1 |
| 9:11:04 |   74600 |      2 |
| 9:11:19 |   74400 |      1 |

| time    |   pb1 |   pb2 |   pb3 |   pb4 |   pb5 |   qb1 |   qb2 |   qb3 |   qb4 |   qb5 |
|---------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|
| 9:11:01 | 74300 | 74200 | 74000 | 73900 | 73800 |    12 |    13 |     1 |    52 |    11 |
| 9:11:03 | 74400 | 74300 | 74200 | 74000 | 73900 |    20 |    12 |    13 |     1 |    52 |
| 9:11:04 | 74400 | 74300 | 74200 | 74000 | 73900 |    21 |    11 |    13 |     1 |    52 |
| 9:11:05 | 74400 | 74300 | 74200 | 74000 | 73900 |    34 |     4 |    13 |     1 |    52 |
| 9:11:19 | 74400 | 74300 | 74200 | 74000 | 73900 |    33 |     4 |    13 |     1 |    52 |

## 3.2. Estimation procedure

Recall that in our stylized model we assume orders to be of unit size. In the data set, we first compute the average size of market orders S m , of limit orders S l and of canceled orders S c and choose the size unit to be the average size of a limit order S l : a block of orders of size S l is counted as one event. The limit order arrival rate function for 1 ≤ i ≤ 5 can be estimated by

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0011" status="decoded_unverified" source-page="7" -->
$$
\hat { \lambda } ( i ) = \frac { N _ { l } ( i ) } { T } ,
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0011](images/formula_0011.png)
```text
PDF text layer: ˆ λ ( i ) = N l ( i ) T ,
```
*Formula quality: `decoded_unverified`; source PDF page 7. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

where N l ( i ) is the total number of limit orders that arrived at a distance i from the opposite best quote. N l ( i ) is obtained by enumerating the number of times that a quote increases in size at a distance of 1 ≤ i ≤ 5 ticks from the opposite best quote. We then extrapolate by fitting a power law function of the form

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0012" status="decoded_unverified" source-page="7" -->
$$
\hat { \lambda } ( i ) = \frac { k } { i ^ { \alpha } }
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0012](images/formula_0012.png)
```text
PDF text layer: ˆ λ ( i ) = k i α
```
*Formula quality: `decoded_unverified`; source PDF page 7. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

(suggested by Zovko and Farmer (2002) or Bouchaud et al. (2002)). The power law parameters k and α are obtained by a least squares fit

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0013" status="decoded_unverified" source-page="7" -->
$$
\min _ { k , \alpha } \sum _ { i = 1 } ^ { 5 } \left ( \hat { \lambda } ( i ) - \frac { k } { i ^ { \alpha } } \right ) ^ { 2 } .
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0013](images/formula_0013.png)
```text
PDF text layer: min k,α 5 ∑ i =1 ( ˆ λ ( i ) -k i α ) 2 .
```
*Formula quality: `decoded_unverified`; source PDF page 7. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

Estimated arrival rates at distances 0 ≤ i ≤ 10 from the opposite best quote are displayed in Figure 1(a).

The arrival rate of market orders is then estimated by

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0014" status="decoded_unverified" source-page="7" -->
$$
\hat { \mu } = \frac { N _ { m } } { T } \frac { S _ { m } } { S _ { l } } ,
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0014](images/formula_0014.png)
```text
PDF text layer: ˆ μ = N m T S m S ,
```
*Formula quality: `decoded_unverified`; source PDF page 7. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

l

where T is the length of our sample (in minutes) and N m is the number of market orders. Note that we ignore market orders that do not affect the best quotes, as is the case when a market order is matched by a hidden or 'iceberg' order.

Since the cancellation rate in our model is proportional to the number of orders at a particular price level, in order to estimate cancellation rate we first need to estimate the steady state shape of the order book Q i , which is the average number of orders at a distance of i ticks from the opposite best quote, for 1 ≤ i ≤ 5. If M is the number of quote rows and S B i ( j ) the number of shares bid at a distance of i ticks from the ask on the j th row, for 1 ≤ j ≤ M , we have

Figure 1 The arrival rates as a function of the distance from the opposite quote

![Image](images/image_000000_bc3c4a0e5df843b91c400905f5027cc20cbb14990ecbd754fe031dfb46845b60.png)

Estimated parameters: Sky Perfect Communications.

|           |    1 |    2 |    3 |    4 |    5 |
|-----------|------|------|------|------|------|
| ˆ λ ( i ) | 1.85 | 1.51 | 1.09 | 0.88 | 0.77 |
| ˆ θ ( i ) | 0.71 | 0.81 | 0.68 | 0.56 | 0.47 |
| ˆ μ       | 0.94 |      |      |      |      |
| k         | 1.92 |      |      |      |      |
| α         | 0.52 |      |      |      |      |

Table 2

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0015" status="decoded_unverified" source-page="8" -->
$$
Q _ { i } ^ { B } = \frac { 1 } { S _ { l } } \frac { 1 } { M } \sum _ { j = 1 } ^ { M } S _ { i } ^ { B } ( j ) \\
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0015](images/formula_0015.png)
```text
PDF text layer: Q B i = 1 S l 1 M M ∑ j =1 S B i ( j )
```
*Formula quality: `decoded_unverified`; source PDF page 8. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

The vector Q A i is obtained analogously and Q i is the average of Q A i and Q B i .

An estimator for the cancellation rate function is then given by

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0016" status="decoded_unverified" source-page="8" -->
$$
\hat { \theta } ( i ) = \frac { N _ { c } ( i ) } { T Q _ { i } } \frac { S _ { c } } { S _ { l } } \quad \text {for} \quad i \leq 5 \quad \text {and} \quad \hat { \theta } ( i ) = \hat { \theta } ( 5 ) \quad \text {for} \quad i > 5 .
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0016](images/formula_0016.png)
```text
PDF text layer: ˆ θ ( i ) = N c ( i ) TQ i S c S l for i ≤ 5 and ˆ θ ( i ) = ˆ θ (5) for i > 5 .
```
*Formula quality: `decoded_unverified`; source PDF page 8. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

The fitted values are displayed in Figure 1(b). N c ( i ) is obtained by counting the number of times that a quote decreases in size at a distance of 1 ≤ i ≤ 5 ticks from the opposite best quote, excluding decreases due to market orders.

Estimated parameter values for Sky Perfect Communications are given in Table 2.

## 4. Laplace transform methods for computing conditional probabilities

As noted above, an important motivation for modelling high-frequency dynamics of order books is to use the information provided by the limit order book for predicting short-term behavior of various quantities which are useful in trade execution and algorithmic trading. For instance, the probability of the mid-price moving up versus down, the probability of executing a limit order at the bid before the ask quote moves and the probability of executing both a buy and a sell order at the best quotes before the price moves. These quantities can be expressed in terms of conditional probabilities of events, given the state of the order book. In this section we show that the model proposed in § 2 allows such conditional probabilities to be analytically computed using Laplace methods. After presenting some background on Laplace transforms in § 4.1, we give various examples of these computations. The probability of an increase in the mid-price is discussed in § 4.2, the probability that a limit order executes before the price moves is discussed in § 4.3 and the probability of executing both a buy and a sell limit order before the price moves is discussed in § 4.4. Laplace transform methods allow efficient computation of these quantities, bypassing the need for Monte Carlo simulation.

## 4.1. Laplace transforms and first-passage times of birth-death processes

We first recall some basic facts about two-sided Laplace transforms and discuss the computation of Laplace transforms for first-passage times of birth-death processes (Abate and Whitt (1999)). Given a function f : R → R , its two-sided Laplace transform is given by

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0017" status="decoded_unverified" source-page="9" -->
$$
\hat { f } ( s ) = \int _ { - \infty } ^ { \infty } e ^ { - s t } f ( t ) d t , \\
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0017](images/formula_0017.png)
```text
PDF text layer: ˆ f ( s ) = ∫ ∞ -∞ e -st f ( t ) dt,
```
*Formula quality: `decoded_unverified`; source PDF page 9. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

where s is a complex numbers. When f is the probability density function (pdf) of some random variable X , its two-sided Laplace transform can also be written as

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0018" status="decoded_unverified" source-page="9" -->
$$
\hat { f } ( s ) = \mathbb { E } [ e ^ { - s X } ] .
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0018](images/formula_0018.png)
```text
PDF text layer: ˆ f ( s ) = E [ e -sX ] .
```
*Formula quality: `decoded_unverified`; source PDF page 9. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

In this case, we also say that ˆ f is the two-sided Laplace transform of the random variable itself. We work with two-sided Laplace transforms here because for our purposes the function f will usually correspond to the pdf of a random variable with both positive and negative support. From now on, we drop the prefix 'two-sided' when referring to two-sided Laplace transforms. When we say conditional Laplace-transform of the random variable X conditional on the event A , we mean the Laplace transform of the conditional pdf of X given A .

Recall that if X and Y are independent random variables with well-defined Laplace transforms, then

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0019" status="decoded_unverified" source-page="9" -->
$$
\hat { f } _ { X + Y } ( s ) = \mathbb { E } [ e ^ { - s ( X + Y ) } ] = \mathbb { E } [ e ^ { - s X } ] \mathbb { E } [ e ^ { - s Y } ] = \hat { f } _ { X } ( s ) \hat { f } _ { Y } ( s ) .
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0019](images/formula_0019.png)
```text
PDF text layer: ˆ f X + Y ( s ) = E [ e -s ( X + Y ) ] = E [ e -sX ] E [ e -sY ] = ˆ f X ( s ) ˆ f Y ( s ) . (3)
```
*Formula quality: `decoded_unverified`; source PDF page 9. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

If for some γ ∈ R we have ∫ ∞ -∞ | ˆ f ( σ + iω ) | dω &lt; ∞ and f ( t ) is continuous at t , then the inverse transform is given by the Bromwich contour integral

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0020" status="decoded_unverified" source-page="9" -->
$$
f ( t ) = \frac { 1 } { 2 \pi i } \int _ { \sigma - i \infty } ^ { \sigma + i \infty } e ^ { t s } \hat { f } ( s ) d s . \\
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0020](images/formula_0020.png)
```text
PDF text layer: f ( t ) = 1 2 πi ∫ σ + i ∞ σ -i ∞ e ts ˆ f ( s ) ds. (4)
```
*Formula quality: `decoded_unverified`; source PDF page 9. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

̸

The continued fraction associated with a sequence { a n , n ≥ 1 } of partial numerators and { b n , n ≥ 1 } of partial denominators, which are complex numbers with a n =0 for all n ≥ 1, is the sequence { w n , n ≥ 1 } , where

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0021" status="decoded_unverified" source-page="9" -->
$$
w _ { n } = t _ { 1 } \circ t _ { 2 } \circ \dots \circ t _ { n } ( 0 ) , n \geq 1 , \quad t _ { k } ( u ) = \frac { a _ { k } } { b _ { k } + u } , k \geq 1 .
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0021](images/formula_0021.png)
```text
PDF text layer: w n = t 1 ◦ t 2 ◦··· ◦ t n (0) , n ≥ 1 , t k ( u ) = a k b + u , k ≥ 1 .
```
*Formula quality: `decoded_unverified`; source PDF page 9. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

k

If w ≡ lim n →∞ w n , then the continued fraction is said to be convergent and the limit w is said to be the value of the continued fraction (Abate and Whitt (1999)). In this case, we write

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0022" status="decoded_unverified" source-page="9" -->
$$
w \equiv \Phi _ { n = 1 } ^ { \infty } \frac { a _ { n } } { b _ { n } } .
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0022](images/formula_0022.png)
```text
PDF text layer: w ≡ Φ ∞ n =1 a n b n .
```
*Formula quality: `decoded_unverified`; source PDF page 9. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

Consider now a birth-death process with constant birth rate λ and death rates μ i in state i ≥ 1, and let σ b denote the first-passage time of this process to 0 given it begins in state b . Next, notice that we can write σ as the sum

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0023" status="decoded_unverified" source-page="10" -->
$$
\sigma _ { b } = \sigma _ { b , b - 1 } + \sigma _ { b - 1 , b - 2 } + \cdots + \sigma _ { 1 , 0 } ,
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0023](images/formula_0023.png)
```text
PDF text layer: σ b = σ b,b -1 + σ b -1 ,b -2 + · · · + σ 1 , 0 ,
```
*Formula quality: `decoded_unverified`; source PDF page 10. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

where σ i,i -1 denotes the first-passage time of the birth-death process from the state i to the state i -1, for i =1 , . . . , b , and all terms on the right-hand side are independent. If ˆ f b denotes the Laplace transform of σ b and ˆ f i,i -1 denotes the Laplace transform of σ i,i -1 , for i =1 , . . . , b , then we have by (3),

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0024" status="decoded_unverified" source-page="10" -->
$$
\hat { f } _ { b } ( s ) = \Pi _ { i = 1 } ^ { b } \hat { f } _ { i , i - 1 } ( s ) . & & ( 5 ) \\ \hat { f } _ { b } ( s ) = \Pi _ { i = 1 } ^ { b } \hat { f } _ { i , i - 1 } ( s ) . & & \\ \hat { f } _ { b } ( s ) = \Pi _ { i = 1 } ^ { b } .
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0024](images/formula_0024.png)
```text
PDF text layer: ˆ f b ( s ) = Π b i =1 ˆ f i,i -1 ( s ) . (5)
```
*Formula quality: `decoded_unverified`; source PDF page 10. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

Therefore, in order to compute ˆ f b , it suffices to compute the simpler Laplace transforms ˆ f i,i -1 , for i =1 , . . . , b . By Equation (4.9) of Abate and Whitt (1999), we see that the Laplace transform of ˆ f i,i -1 is given by

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0025" status="decoded_unverified" source-page="10" -->
$$
\hat { f } _ { i , i - 1 } ( s ) = - \frac { 1 } { \lambda } \Phi _ { k = i } ^ { \infty } \frac { - \lambda \mu _ { k } } { \lambda + \mu _ { k } + s } .
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0025](images/formula_0025.png)
```text
PDF text layer: ˆ f i,i -1 ( s ) = -1 λ Φ ∞ k = i -λμ k λ + μ k + s . (6)
```
*Formula quality: `decoded_unverified`; source PDF page 10. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

The computation there is based on a recursive relationship between the ˆ f i,i -1 , i =1 , . . . , b , which is derived by considering the first transition of the birth-death process. Combining (5) and (6), we obtain

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0026" status="decoded_unverified" source-page="10" -->
$$
\hat { f } _ { b } ( s ) = \left ( - \frac { 1 } { \lambda } \right ) ^ { b } \left ( \Pi _ { i = 1 } ^ { b } \Phi _ { k = i } ^ { \infty } \frac { - \lambda \mu _ { k } } { \lambda + \mu _ { k } + s } \right ) . \\ \text {result in all our computations below}
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0026](images/formula_0026.png)
```text
PDF text layer: ˆ f b ( s ) = ( -1 λ ) b ( Π b i =1 Φ ∞ k = i -λμ k λ + μ k + s ) . (7)
```
*Formula quality: `decoded_unverified`; source PDF page 10. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

We will use this result in all our computations below.

## 4.2. Direction of price moves

We now compute the probability that the mid-price increases at its next move. The first move in the mid-price occurs at the first-passage time of the bid or ask queue to zero or, if the bid/ask spread is greater than one, the first time a limit order arrives inside the spread. Throughout this section, let X A ≡ X p A ( · ) ( · ) and X B ≡| X p B ( · ) ( · ) | , and let σ A and σ B be the first-passage times of X A and X B to 0, respectively. Let W B ≡{ W B ( t ) , t ≥ 0 } ( W A ≡{ W A ( t ) , t ≥ 0 } ) denote the number of orders remaining at the bid (ask) at time t of the initial X B (0) ( X A (0)) orders and let ϵ B ( ϵ A ) be the first-passage time of W B ( W A ) to 0. Furthermore, let T be the time of the first change in mid-price:

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0027" status="decoded_unverified" source-page="10" -->
$$
T \equiv \inf \{ t \geq 0 , \, p _ { M } ( t ) \neq p _ { M } ( 0 ) \} . \\
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0027](images/formula_0027.png)
```text
PDF text layer: T ≡ inf { t ≥ 0 , p M ( t ) = p M (0) } .
```
*Formula quality: `decoded_unverified`; source PDF page 10. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

̸

In this subsection, we are interested in computing the conditional probability that the mid-price increases before decreasing:

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0028" status="decoded_unverified" source-page="10" -->
$$
\mathbb { P } [ p _ { M } ( T ) > p _ { M } ( 0 ) | X _ { A } ( 0 ) = a , X _ { B } ( 0 ) = b , s ( 0 ) = S ] ,
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0028](images/formula_0028.png)
```text
PDF text layer: P [ p M ( T ) >p M (0) | X A (0) = a, X B (0) = b, s (0) = S ] , (8)
```
*Formula quality: `decoded_unverified`; source PDF page 10. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

where S &gt; 0. For ease of notation, we will omit the conditioning variables in all proofs below.

The idea for computing (8) is to observe that X A and X B behave as independent birth-death processes and W A and W B behave as independent pure-death processes for t ≤ T . More precisely:

## Lemma 2 Let s (0) = S . Then

1. There exist independent birth-death processes ˜ X A and ˜ X B with birth rate λ ( S ) and death rate μ + iθ ( S ) in state i ≥ 1 , such that for all 0 ≤ t ≤ T , ˜ X A ( t ) = X A ( t ) and ˜ X B ( t ) = X B ( t ) .
2. There exist independent pure death processes ˜ W A and ˜ W B with death rate μ + iθ ( S ) in state i ≥ 1 , such that for all 0 ≤ t ≤ T , ˜ W A ( t ) = W A ( t ) and ˜ W B ( t ) = W B ( t ) . Furthermore, ˜ W A is independent of ˜ X B , ˜ W B is independent of ˜ X A , ˜ W A ≤ ˜ X A and ˜ W B ≤ ˜ X B .

B

The conditional probability (8) can then be computed as follows:

Proposition 3 (Probability of increase in mid-price) Let ˆ f j,S be given by

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0029" status="decoded_unverified" source-page="11" -->
$$
\hat { f } _ { j , S } ( s ) = \left ( - \frac { 1 } { \lambda ( S ) } \right ) ^ { j } \left ( \Pi _ { i = 1 } ^ { b } \Phi _ { k = i } ^ { \infty } \frac { - \lambda ( S ) \left ( \mu + k \theta ( S ) \right ) } { \lambda ( S ) + \mu + k \theta ( S ) + s } \right ) , \\
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0029](images/formula_0029.png)
```text
PDF text layer: ˆ f j,S ( s ) = ( -1 λ ( S ) ) j ( Π b i =1 Φ ∞ k = i -λ ( S ) ( μ + kθ ( S )) λ ( S ) + μ + kθ ( S ) + s ) , (9)
```
*Formula quality: `decoded_unverified`; source PDF page 11. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0030" status="decoded_unverified" source-page="11" -->
$$
& \text {for } j \geq 1 , \text { and } \iota \, \text { } \Lambda _ { s } \equiv \sum _ { i = 1 } ^ { S - 1 } \lambda ( i ) . \text { Then } ( 8 ) \text { is given by the inverse Laplace transform of } \\ & \hat { F } _ { a , b , S } ( s ) = \frac { 1 } { s } \left ( \hat { f } _ { b , S } ( s + \Lambda _ { S } ) + \frac { \Lambda _ { S } } { \Lambda _ { S } + s } ( 1 - \hat { f } _ { b , S } ( s + \Lambda _ { S } ) ) \right ) \left ( \hat { f } _ { a , S } ( \Lambda _ { S } - s ) + \frac { \Lambda _ { S } } { \Lambda _ { S } - s } ( 1 - \hat { f } _ { a , S } ( \Lambda _ { S } - s ) ) \right ) , \\ & \text {evaluated at } 0 , \text { when } S = 1 , \text { (10) } \text { reduces to }
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0030](images/formula_0030.png)
```text
PDF text layer: for j ≥ 1 , and let Λ S ≡ ∑ S -1 i =1 λ ( i ) . Then (8) is given by the inverse Laplace transform of ˆ F a,b,S ( s ) = 1 s ( ˆ f b,S ( s +Λ S ) + Λ S Λ S + s (1 -ˆ f b,S ( s +Λ S )) )( ˆ f a,S (Λ S -s ) + Λ S Λ S -s (1 -ˆ f a,S (Λ S -s )) ) , (10)
```
*Formula quality: `decoded_unverified`; source PDF page 11. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

evaluated at 0. When S =1 , (10) reduces to

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0031" status="decoded_unverified" source-page="11" -->
$$
\hat { F } _ { a , b , 1 } ( s ) = \frac { 1 } { s } \hat { f } _ { a , 1 } ( s ) \hat { f } _ { b , 1 } ( - s ) .
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0031](images/formula_0031.png)
```text
PDF text layer: ˆ F a,b, 1 ( s ) = 1 s ˆ f a, 1 ( s ) ˆ f b, 1 ( -s ) . (11)
```
*Formula quality: `decoded_unverified`; source PDF page 11. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

Proof. We will first focus on the special case when S =1 and then extend the analysis to the case S &gt; 1 using Lemma 4 below. Construct ˜ X A and ˜ X B as in Lemma 2. When S =1, the price changes for the first time exactly when one of the two independent birth-death processes ˜ X A and ˜ X B reaches the state 0 for the first time. Both of these birth-death processes have constant birth rates λ (1) and death rates μ + iθ (1), i ≥ 1. Thus, given our initial conditions, the distribution of T is given by the minimum of the independent first passage times σ A and σ B . Furthermore, the quantity (8) is given by P [ σ A &lt;σ B ]. By (7), the conditional Laplace transform of σ A -σ B given the initial conditions is given by ˆ f a, 1 ( s ) ˆ f b, 1 ( -s ) so that the conditional Laplace transform of the cumulative distribution function (cdf) of σ A -σ B is given by (11). Thus, our desired probability is given by the inverse Laplace transform of (11) evaluated at 0.

We now move on to the case where S &gt; 1. Let σ i A denote the first time an ask order arrives i ticks away from the bid and σ i B denote the first time a bid order arrives i ticks away from the ask, for i =1 , . . . , S -1. The time of the first change in mid-price is now given by

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0032" status="decoded_unverified" source-page="11" -->
$$
T = \sigma _ { A } \wedge \sigma _ { B } \wedge \min \{ \sigma _ { A } ^ { i } , \sigma _ { B } ^ { i } , \, i = 1 , \dots , S - 1 \} . \\ \tilde { \ } r a c { \sigma } { ( i ) } .
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0032](images/formula_0032.png)
```text
PDF text layer: T = σ A ∧ σ B ∧ min { σ i A , σ i B , i =1 , . . . , S -1 } .
```
*Formula quality: `decoded_unverified`; source PDF page 11. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

Notice that ˜ X A and ˜ X B are independent of the mutually independent arrival times σ i A , σ i B , for i = 1 , . . . , S -1. Also, notice that σ i A and σ i B are exponentially distributed with rates λ ( i ) for i =1 , . . . , S -1. The first change in mid-price is an increase if there is an arrival of a limit bid order within S -1 ticks of the best ask or ˜ X A hits zero, before there is an arrival of a limit ask order within S -1 ticks of the best bid or ˜ X B hits zero. Thus, the quantity (8) can be written as

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0033" status="decoded_unverified" source-page="11" -->
$$
\mathbb { P } [ \sigma _ { A } \wedge \sigma _ { B } ^ { 1 } \wedge \dots \wedge \sigma _ { B } ^ { S - 1 } < \sigma _ { B } \wedge \sigma _ { A } ^ { 1 } \wedge \dots \wedge \sigma _ { A } ^ { S - 1 } ] = \mathbb { P } [ \sigma _ { A } \wedge \sigma _ { B } ^ { \Sigma } < \sigma _ { B } \wedge \sigma _ { A } ^ { \Sigma } ] , \\ \\ \sigma _ { A } \wedge \sigma _ { B } ^ { S } \wedge \dots \wedge \sigma _ { B } ^ { S - 1 } < \sigma _ { B } \wedge \sigma _ { A } ^ { 1 } \wedge \dots \wedge \sigma _ { A } ^ { S - 1 } ] = \mathbb { P } [ \sigma _ { A } \wedge \sigma _ { B } ^ { \Sigma } < \sigma _ { B } \wedge \sigma _ { A } ^ { \Sigma } ] , \\
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0033](images/formula_0033.png)
```text
PDF text layer: P [ σ A ∧ σ 1 B ∧ . . . ∧ σ S -1 B <σ B ∧ σ 1 A ∧ . . . ∧ σ S -1 A ] = P [ σ A ∧ σ Σ B <σ B ∧ σ Σ A ] , (12)
```
*Formula quality: `decoded_unverified`; source PDF page 11. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

where σ Σ A and σ Σ B are independent exponential random variables both with rate Λ S . In order to compute (12), we first need to compute the conditional Laplace transform of the minimum σ B ∧ σ Σ A . This is given in Lemma 4, substituting σ Σ A for Z . The conditional Laplace transform of the random variable σ B ∧ σ Σ A -σ A ∧ σ Σ B can then be computed using (3) and the probability (8) can be computed by inverting the conditional Laplace transform of the cdf of this random variable and evaluating at 0 as in the case S =1. □

Lemma 4 Let Z be an exponentially distributed random variable with parameter Λ . Then the Laplace transform of the random variable σ B ∧ Z is given by

where ˆ f b is given in (9) .

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0034" status="decoded_unverified" source-page="11" -->
$$
\hat { f } _ { b } ( s + \Lambda ) + \frac { \Lambda } { \Lambda + s } ( 1 - \hat { f } _ { b } ( s + \Lambda ) ) ,
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0034](images/formula_0034.png)
```text
PDF text layer: ˆ f b ( s +Λ)+ Λ Λ+ s (1 -ˆ f b ( s +Λ)) ,
```
*Formula quality: `decoded_unverified`; source PDF page 11. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

Proof. We first compute the density f σ B ∧ Z of the random variable σ B ∧ Z in terms of the density f b of the random variable σ B . Since Z is exponential with rate Λ, we have for all t ≥ 0,

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0035" status="decoded_unverified" source-page="12" -->
$$
\mathbb { P } [ \sigma _ { B } \wedge Z < t ] = 1 - \mathbb { P } [ \sigma _ { B } > t ] \mathbb { P } [ Z > t ] = 1 - ( 1 - F _ { \sigma _ { B } } ( t ) ) e ^ { - \Lambda t } .
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0035](images/formula_0035.png)
```text
PDF text layer: P [ σ B ∧ Z < t ] = 1 -P [ σ B >t ] P [ Z > t ] = 1 -(1 -F σ B ( t )) e -Λ t .
```
*Formula quality: `decoded_unverified`; source PDF page 12. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

Taking derivatives with respect to t gives

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0036" status="decoded_unverified" source-page="12" -->
$$
f _ { \sigma _ { B } \wedge Z } ( t ) = f _ { b } ( t ) e ^ { - \Lambda t } + \Lambda ( 1 - F _ { b } ( t ) ) e ^ { - \Lambda t } ,
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0036](images/formula_0036.png)
```text
PDF text layer: f σ B ∧ Z ( t ) = f b ( t ) e -Λ t +Λ(1 -F b ( t )) e -Λ t ,
```
*Formula quality: `decoded_unverified`; source PDF page 12. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

for t ≥ 0, where F b ( t ) is the cdf of σ B . Also, f σ B ∧ Z ( t ) = 0 for t &lt; 0. The Laplace transform of σ B ∧ Z is thus given by

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0037" status="decoded_unverified" source-page="12" -->
$$
\text {given by} & & \hat { f } _ { \sigma B \wedge Z } ( s ) = \int _ { - \infty } ^ { \infty } e ^ { - s t } f _ { \sigma _ { B } \wedge \sigma _ { B } ^ { \Sigma } } ( t ) d t \\ & = \int _ { 0 } ^ { \infty } e ^ { - s t } \left ( f _ { b } ( t ) e ^ { - \Lambda t } + \Lambda \left ( 1 - F _ { b } ( t ) \right ) e ^ { - \Lambda t } \right ) d s \\ & = \int _ { 0 } ^ { \infty } e ^ { - t ( s + \Lambda ) } f _ { b } ( t ) d t + \Lambda \int _ { 0 } ^ { \infty } \left ( 1 - F _ { b } ( t ) \right ) e ^ { - t ( s + \Lambda ) } d t \\ & = \hat { f } _ { b } ( s + \Lambda ) + \frac { \Lambda } { \Lambda + s } \left ( 1 - \hat { f } _ { b } ( s + \Lambda ) \right ) , \\ \intertext { l e a s t h e q u a l i y f o w s f r o w } \text {section 3 yields a numerical procedure for computing the probability that the next }
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0037](images/formula_0037.png)
```text
PDF text layer: ˆ f σ B ∧ Z ( s ) = ∫ ∞ -∞ e -st f σ B ∧ σ Σ B ( t ) dt = ∫ ∞ 0 e -st ( f b ( t ) e -Λ t +Λ(1 -F b ( t )) e -Λ t ) ds = ∫ ∞ 0 e -t ( s +Λ) f b ( t ) dt +Λ ∫ ∞ 0 (1 -F b ( t )) e -t ( s +Λ) dt = ˆ f b ( s +Λ)+ Λ Λ+ s ( 1 -ˆ f b ( s +Λ) ) ,
```
*Formula quality: `decoded_unverified`; source PDF page 12. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

where the last equality follows from integration by parts. □

Proposition 3 yields a numerical procedure for computing the probability that the next change in the mid-price will be an increase. We discuss implementation of the procedure in § 5.2.3.

## 4.3. Executing an order before the mid-price moves

Traders who submit limit orders obtain a better price than if they had submitted a market order but face the risk of non-execution and the 'winner's curse'. Whereas a market order executes with certainty, limit orders stay in the order book until either a matching order is entered or the order is canceled. The probability that a limit order is executed before the price moves is therefore useful in quantifying the choice between a limit order and a market order. We now compute the probability that an order placed at the bid price is executed before any movement in the mid-price, given that the order is not canceled. Our result holds for initial spread S ≡ s (0) ≥ 1, but we remark that in the case where S =1 the probability we are interested is equal to the probability that the order is executed before the mid-price moves away from the desired price, given the order is not canceled. Although we focus here on an order placed at the bid price, since our model is symmetric in bids and asks, our result also holds for orders placed at the ask price.

We introduce some new notation, which we will used in this subsection as well as the next. Let NC b ( NC a ) denote the event that an order that never gets canceled is placed at the bid (ask) at time 0.

Then, the probability that an order placed at the bid is executed before the mid-price moves is given by

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0038" status="decoded_unverified" source-page="12" -->
$$
\mathbb { P } [ \epsilon _ { B } < T | X _ { B } ( 0 ) = b , X _ { A } ( 0 ) = a , s ( 0 ) = S , N C _ { b } ] .
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0038](images/formula_0038.png)
```text
PDF text layer: P [ ϵ B <T | X B (0) = b, X A (0) = a, s (0) = S,NC b ] . (13)
```
*Formula quality: `decoded_unverified`; source PDF page 12. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

Proposition 5 (Probability of order execution before mid-price moves) Define ˆ f a,S ( s ) as in (9) and let ˆ g j,S be given by

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0039" status="decoded_unverified" source-page="12" -->
$$
\hat { g } _ { j , S } ( s ) = \Pi _ { i = 1 } ^ { j } \frac { \mu + \theta ( S ) ( i - 1 ) } { \mu + \theta ( S ) ( i - 1 ) + s }
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0039](images/formula_0039.png)
```text
PDF text layer: ˆ g j,S ( s ) = Π j i =1 μ + θ ( S )( i -1) μ + θ ( S )( i -1) + s (14)
```
*Formula quality: `decoded_unverified`; source PDF page 12. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

for j ≥ 1 , and let Λ S ≡ ∑ S -1 i =1 λ ( i ) . Then the quantity (13) is given by the inverse Laplace transform of

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0040" status="decoded_unverified" source-page="13" -->
$$
\hat { F } _ { a , b , S } ( s ) & = \frac { 1 } { s } \hat { g } _ { b , S } ( s ) \left ( \hat { f } _ { b , S } ( 2 \Lambda _ { S } - s ) + \frac { 2 \Lambda _ { S } } { 2 \Lambda _ { S } - s } ( 1 - \hat { f } _ { b , S } ( 2 \Lambda _ { S } - s ) ) \right ) , \\ \intertext { v a l u a t e d } \hat { F } _ { a , b , S } ( s ) & = \frac { 1 } { s } \hat { g } _ { b , S } ( s ) \left ( \hat { f } _ { b , S } ( 2 \Lambda _ { S } - s ) + \frac { 2 \Lambda _ { S } } { 2 \Lambda _ { S } - s } ( 1 - \hat { f } _ { b , S } ( 2 \Lambda _ { S } - s ) ) \right ) , \\ \intertext { v a l u a t e d } \intertext { v e c h a l l } \hat { g } _ { a , b , S } ( s ) & = 1 - ( 1 5 ) \ r e d u c e s \ t o
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0040](images/formula_0040.png)
```text
PDF text layer: ˆ F a,b,S ( s ) = 1 s ˆ g b,S ( s ) ( ˆ f b,S (2Λ S -s ) + 2Λ S 2Λ S -s (1 -ˆ f b,S (2Λ S -s )) ) , (15)
```
*Formula quality: `decoded_unverified`; source PDF page 13. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

evaluated at 0 . When S =1 , (15) reduces to

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0041" status="decoded_unverified" source-page="13" -->
$$
\hat { F } _ { a , b , 1 } ( s ) = \frac { 1 } { s } \hat { g } _ { b , 1 } ( s ) \hat { f } _ { a , 1 } ( - s ) .
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0041](images/formula_0041.png)
```text
PDF text layer: ˆ F a,b, 1 ( s ) = 1 s ˆ g b, 1 ( s ) ˆ f a, 1 ( -s ) . (16)
```
*Formula quality: `decoded_unverified`; source PDF page 13. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

Proof. Construct ˜ X A and ˜ W B using Lemma 2. Let us first consider the case S =1. Let T ′ ≡ ϵ B ∧ T denote the first time when either the process ˜ W B hits 0 or the mid-price changes. Conditional on an infinitely patient order being placed at the bid price at time 0, T ′ is the first time when either that order gets executed or the mid-price changes. Notice that conditional on our initial conditions, ϵ B is given by a sum of b independent exponentially distributed random variables with parameters μ +( i -1) θ (1), for i =1 , . . . , b , and independent of ˜ X A . Thus, the conditional Laplace transform of ϵ B given our initial conditions is given by (14). Since, in the case S =1 the mid-price can change before time ϵ B if and only if σ A &lt;ϵ B , the quantity (13) can be written simply as P [ ϵ B &lt;σ A ]. Using (3) with the conditional Laplace transforms of ϵ B and σ A , given in (14) and (9) respectively, we obtain (16).

This analysis can be extended to the case where S &gt; 1 just as in the proof of Proposition 3. When S &gt; 1, our desired quantity can be written as P [ ϵ B &lt;σ A ∧ σ Σ B ∧ σ Σ A ]. Since the conditional distribution of σ Σ B ∧ σ Σ A is exponential with parameter 2Λ S . As in the proof of Proposition 3, Lemma 4 then yields the result. □

## 4.4. Making the spread

We now compute the probability that two orders, one placed at the bid price and one placed at the ask price, are both executed before the mid-price moves, given that the orders are not canceled. If the probability of executing both a buy and a sell limit order before the price moves is high, a statistical arbitrage strategy can be designed by submitting limit orders at the bid and the ask and wait for both orders to execute. If both orders execute before the price moves, the strategy has paid off the bid-ask spread: we refer to this situation as 'making the spread'. Otherwise, losses may be minimized by submitting a market order and losing the bid-ask spread. We restrict attention to the case where the initial spread is one tick: S =1. The probability of making the spread can be expressed as

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0042" status="decoded_unverified" source-page="13" -->
$$
\mathbb { P } [ \max \{ \epsilon _ { A } , \epsilon _ { B } \} < T | X _ { B } ( 0 ) = b , X _ { A } ( 0 ) = a , s ( 0 ) = 1 , N C _ { a } , N C _ { b } ] . \\ \\
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0042](images/formula_0042.png)
```text
PDF text layer: P [max { ϵ A , ϵ B } <T | X B (0) = b, X A (0) = a, s (0) = 1 , NC a , NC b ] . (17)
```
*Formula quality: `decoded_unverified`; source PDF page 13. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

The following result allows to compute this probability using Laplace transform methods:

Proposition 6 The probability (17) of making the spread is given by h a,b + h b,a , where

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0043" status="decoded_unverified" source-page="13" -->
$$
h _ { a , b } = \sum _ { i = 0 } ^ { \infty } \sum _ { j = 1 } ^ { a } \mathbb { P } [ \epsilon _ { j } < \sigma _ { i } ] \int _ { 0 } ^ { \infty } P _ { 0 , i } ^ { X } ( t ) P _ { a , j } ^ { W } ( t ) g _ { b } ( t ) d t ,
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0043](images/formula_0043.png)
```text
PDF text layer: h a,b = ∞ ∑ i =0 a ∑ j =1 P [ ϵ j <σ i ] ∫ ∞ 0 P X 0 ,i ( t ) P W a,j ( t ) g b ( t ) dt, (18)
```
*Formula quality: `decoded_unverified`; source PDF page 13. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0044" status="decoded_unverified" source-page="13" -->
$$
P _ { 0 , i } ^ { X } ( t ) & = \frac { e ^ { - \lambda ^ { X } ( t ) } \lambda ^ { X } ( t ) ^ { i } } { i ! } , \quad \lambda ^ { X } ( t ) \equiv \frac { \lambda } { \theta } \left ( 1 - e ^ { - \theta t } \right ) \\ P _ { a } ^ { W } ( t ) & \equiv \left ( e ^ { Q _ { a } ^ { W } t } \right ) \quad \equiv \left ( \sum _ { \substack { i = 0 \\ i \neq t } } ^ { \infty } \frac { t ^ { k } } { Q _ { a } ^ { W } ( a ^ { W } ) ^ { k } } \right )
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0044](images/formula_0044.png)
```text
PDF text layer: P X 0 ,i ( t ) = e -λ X ( t ) λ X ( t ) i i ! , λ X ( t ) ≡ λ θ ( 1 -e -θt ) (19)
```
*Formula quality: `decoded_unverified`; source PDF page 13. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0045" status="decoded_unverified" source-page="13" -->
$$
P _ { a , j } ^ { W } ( t ) \equiv \left ( e ^ { Q _ { a } ^ { W } t } \right ) _ { a , j } \equiv \left ( \sum _ { k = 0 } ^ { \infty } \frac { t ^ { k } } { k ! } ( Q _ { a } ^ { W } ) ^ { k } \right ) _ { a , j }
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0045](images/formula_0045.png)
```text
PDF text layer: P W a,j ( t ) ≡ ( e Q a W t ) a,j ≡ ( ∞ ∑ k =0 t k k ! ( Q W a ) k ) a,j (20)
```
*Formula quality: `decoded_unverified`; source PDF page 13. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

where

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0046" status="decoded_unverified" source-page="14" -->
$$
Q _ { a } ^ { w } \equiv \begin{bmatrix} 0 & 0 & 0 & \cdots & 0 \\ \mu & - \mu & 0 & \cdots & 0 \\ 0 & \mu + \theta - \mu - \theta & \cdots & 0 & \\ \vdots & \vdots & \ddots & \ddots & \vdots \\ 0 & 0 & \cdots & \mu + ( a - 1 ) \theta - \mu - ( a - 1 ) \theta \\ \end{bmatrix} .
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0046](images/formula_0046.png)
```text
PDF text layer: Q W a ≡ ⎡ ⎢ ⎢ ⎢ ⎢ ⎢ ⎣ 0 0 0 · · · 0 μ -μ 0 · · · 0 0 μ + θ -μ -θ · · · 0 . . . . . . . . . . . . . . . 0 0 · · · μ +( a -1) θ -μ -( a -1) θ ⎤ ⎥ ⎥ ⎥ ⎥ ⎥ ⎦ . (21)
```
*Formula quality: `decoded_unverified`; source PDF page 14. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

and g b is the inverse Laplace transform of ˆ g b, 1 , which is given in (14) .

Proof. Since S =1, T =min { σ A , σ B } , and the quantity (17) can be written as

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0047" status="decoded_unverified" source-page="14" -->
$$
\mathbb { P } [ \max \{ \epsilon _ { B } , \epsilon _ { A } \} < \min \{ \sigma _ { B } , \sigma _ { A } \} ] . \\ \\ \tilde { z }
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0047](images/formula_0047.png)
```text
PDF text layer: P [max { ϵ B , ϵ A } < min { σ B , σ A } ] . (22)
```
*Formula quality: `decoded_unverified`; source PDF page 14. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

Construct ˜ X A , ˜ X B , ˜ W A and ˜ W B using Lemma 2. Let T ′ =max { ϵ A , ϵ B } ∧ T denote the first time when either both the processes ˜ W A and ˜ W B have hit 0 or the mid-price has changed. Conditional on infinitely patient orders being placed at the best bid and ask prices at time 0, T ′ is the first time when either both the orders get executed or the mid-price changes. Furthermore, by Lemma 2, ˜ W A and ˜ W B are independent pure death processes with death rate μ + iθ (1) in state i ≥ 1, and ˜ W A ( t ) ≤ ˜ X A ( t ) and ˜ W B ( t ) ≤ ˜ X B ( t ). This implies that ϵ A and ϵ B are independent and σ A and σ B are independent with ϵ A ≤ σ A and ϵ B ≤ σ B . Using these properties we obtain

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0048" status="decoded_unverified" source-page="14" -->
$$
\mathbb { P } [ \max \{ \epsilon _ { B } , \epsilon _ { A } \} < \min \{ \sigma _ { B } , \sigma _ { A } \} ] & = \mathbb { P } [ \epsilon _ { B } < \sigma _ { A } , \epsilon _ { A } < \sigma _ { B } ] \\ & = \mathbb { P } [ \epsilon _ { B } < \sigma _ { A } , \epsilon _ { A } < \sigma _ { B } , \epsilon _ { B } < \epsilon _ { A } ] + \mathbb { P } [ \epsilon _ { B } < \sigma _ { A } , \epsilon _ { A } < \sigma _ { B } , \epsilon _ { A } < \epsilon _ { B } ] \\ & = \mathbb { P } [ \epsilon _ { A } < \sigma _ { B } , \epsilon _ { B } < \epsilon _ { A } ] + \mathbb { P } [ \epsilon _ { B } < \sigma _ { A } , \epsilon _ { A } < \epsilon _ { B } ] \\ & = h _ { a , b } + h _ { b , a }
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0048](images/formula_0048.png)
```text
PDF text layer: P [max { ϵ B , ϵ A } < min { σ B , σ A } ] = P [ ϵ B <σ A , ϵ A <σ B ] = P [ ϵ B <σ A , ϵ A <σ B , ϵ B <ϵ A ] + P [ ϵ B <σ A , ϵ A <σ B , ϵ A <ϵ B ] = P [ ϵ A <σ B , ϵ B <ϵ A ] + P [ ϵ B <σ A , ϵ A <ϵ B ] = h a,b + h b,a (23)
```
*Formula quality: `decoded_unverified`; source PDF page 14. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

where we define h a,b = P [ ϵ B &lt;ϵ A &lt;σ B ], the probability that the order placed at the bid is executed before the order placed at the ask and the order at the ask is executed before the bid quote disappears. We now focus on computing h a,b . Conditioning on the value of ϵ B gives

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0049" status="decoded_unverified" source-page="14" -->
$$
h _ { a , b } = \int _ { 0 } ^ { \infty } \mathbb { P } [ \epsilon _ { B } < \epsilon _ { A } < \sigma _ { B } | \epsilon _ { B } = t ] g _ { b } ( t ) d t . \\ \\ C _ { a } \, f _ { a } = \int _ { 0 } ^ { \infty } \mathbb { P } [ \epsilon _ { B } < \epsilon _ { A } < \sigma _ { B } | \epsilon _ { B } = t ] g _ { b } ( t ) d t .
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0049](images/formula_0049.png)
```text
PDF text layer: h a,b = ∫ ∞ 0 P [ ϵ B <ϵ A <σ B | ϵ B = t ] g b ( t ) dt. (24)
```
*Formula quality: `decoded_unverified`; source PDF page 14. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

Focusing on the first factor in the integrand in (24) and conditioning on the values of ˜ X B ( t ) and ˜ W A ( t ) gives us

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0050" status="decoded_unverified" source-page="14" -->
$$
W _ { A } ( t ) \text { gives us } & \\ & \mathbb { P } [ t _ { B } < \epsilon _ { A } < \sigma _ { B } | _ { \mathcal { B } } = t ] = \sum _ { i = 0 } ^ { \alpha } \mathbb { P } [ \epsilon _ { B } < \epsilon _ { A } < \sigma _ { B } | _ { \mathcal { B } } = t , \tilde { X } _ { B } ( t ) = i , \tilde { W } _ { A } ( t ) = j ] \mathbb { P } [ \tilde { X } _ { B } ( t ) = i , \tilde { W } _ { A } ( t ) = j | _ { E } = t ] \\ & = \sum _ { i = 0 } ^ { \alpha } \sum _ { 1 } ^ { \ell } \mathbb { P } [ \tilde { \epsilon } _ { j } < \sigma _ { i } ] \mathbb { P } [ \tilde { X } _ { B } ( t ) = i | \epsilon _ { B } = t ] \mathbb { P } [ \tilde { W } _ { A } ( t ) = j | _ { E } = t ] \\ & = \sum _ { i = 0 } ^ { \alpha } \sum _ { 1 } ^ { \ell } \mathbb { P } [ \tilde { \epsilon } _ { j } < \sigma _ { i } ] \mathbb { P } [ \tilde { X } _ { B } ( t ) = i | \epsilon _ { B } = t ] \mathbb { P } [ \tilde { W } _ { A } ( t ) = j ] \\ & = \left ( 2 5 \right ) \\ & \text {Combining the equations (23)-(25) and using Tonelli's theorem to interchange the integral and the} \\
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0050](images/formula_0050.png)
```text
PDF text layer: P [ ϵ B <ϵ A <σ B | ϵ B = t ] = ∞ ∑ i =0 a ∑ j =0 P [ ϵ B <ϵ A <σ B | ϵ B = t, ˜ X B ( t ) = i, ˜ W A ( t ) = j ] P [ ˜ X B ( t ) = i, ˜ W A ( t ) = j | ϵ B = t ] = ∞ ∑ i =0 a ∑ j =1 P [ ϵ j <σ i ] P [ ˜ X B ( t ) = i | ϵ B = t ] P [ ˜ W A ( t ) = j | ϵ B = t ] = ∞ ∑ i =0 a ∑ j =1 P [ ϵ j <σ i ] P [ ˜ X B ( t ) = i | ϵ B = t ] P [ ˜ W A ( t ) = j ] (25)
```
*Formula quality: `decoded_unverified`; source PDF page 14. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

Combining the equations (23)-(25) and using Tonelli's theorem to interchange the integral and the summation gives us

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0051" status="decoded_unverified" source-page="14" -->
$$
h _ { a , b } = & \sum _ { i = 0 } ^ { \infty } \sum _ { j = 1 } ^ { a } \mathbb { P } [ \epsilon _ { j } < \sigma _ { i } ] \int _ { 0 } ^ { \infty } \mathbb { P } [ \tilde { X } _ { B } ( t ) = i | \epsilon _ { B } = t ] \mathbb { P } [ \tilde { W } _ { A } ( t ) = j ] g _ { b } ( t ) d t . \\ + \colon & \mathbb { T } [ \tilde { X } _ { B } ( t ) \quad \cdot \quad ] = \L _ { i } \L _ { j } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b } \L _ { t } \L _ { a } \L _ { a } \L _ { b
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0051](images/formula_0051.png)
```text
PDF text layer: h a,b = ∞ ∑ i =0 a ∑ j =1 P [ ϵ j <σ i ] ∫ ∞ 0 P [ ˜ X B ( t ) = i | ϵ B = t ] P [ ˜ W A ( t ) = j ] g b ( t ) dt.
```
*Formula quality: `decoded_unverified`; source PDF page 14. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

The quantity P [ ˜ X B ( t ) = i | ϵ B = t ] can be computed using an analogy with the M/M/ ∞ queue. The number of orders in the bid queue at the time when the bid order placed at time 0 has executed is simply the number of customers in an initially empty M/M/ ∞ queue with arrival rate λ and service rate θ , which has a Poisson distribution with mean given by (19). This remark leads to ( ?? ).

The quantity P [ ˜ W A ( t ) = j ] is the probability that a pure death process with death rate μ +( k -1) θ (1) in state k ≥ 1 is in state j at time t , given it begins in state a . The infinitesimal generator of this pure death process is given by (21). Thus, by Corollary II.3.5 of Asmussen (2003), P [ ˜ W A ( t ) = j ] is given by (20). □

## 5. Numerical Results

Our stochastic model allows one to compute various quantities of interest by simulating the evolution of the order book and and by using the Laplace transform methods presented in § 4, based on parameters μ , λ and θ estimated from the order flow. In this section we compute these quantities for the example of Sky Perfect Communications and compare them to empirically observed values, in order to assess the precision of the description provided by our model.

In § 5.1, we compare empirically observed long-term behavior (e.g. unconditional properties) of the order book to simulations of the fitted model. Although these quantities may not be particularly important for traders who are interested in trading in a short time scale, they indicate how well the model reproduces the average properties of the order book. In § 5.2, we compare conditional probabilities of various events in our model to frequencies of the events in the data. We also compare results using the Laplace transform methods developed in § 4 to our simulation results.

## 5.1. Long term behavior

Recent empirical studies on order books Bouchaud et al. (2002, 2008) have mainly focused on average properties of the order book, which, in our context correspond to unconditional expectations of quantities under the stationary measure of X : the steady state shape of the book and the volatility of the mid-price. The ergodicity of the Markov chain X , shown in Proposition 1, implies that such expectations E [ f ( X ∞ )] can be computed in the model by simulating the order book over a large horizon T and averaging f ( X ( t )) over the simulated path:

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0052" status="decoded_unverified" source-page="15" -->
$$
\frac { 1 } { T } \int _ { 0 } ^ { T } f ( X ( t ) ) d t \rightarrow E [ f ( X _ { \infty } ) ] \quad \text {as} \quad T \rightarrow \infty . \\ \text {state shape of the book} \quad \text {We simulate the order book}
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0052](images/formula_0052.png)
```text
PDF text layer: 1 T ∫ T 0 f ( X ( t )) dt → E [ f ( X ∞ )] as T →∞ .
```
*Formula quality: `decoded_unverified`; source PDF page 15. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

5.1.1. Steady state shape of the book We simulate the order book over a long horizon ( n =10 6 events) and observe the mean number of orders Q i at distances 1 ≤ i ≤ 30 ticks from the opposite best quote. The results are displayed in Figure 2. The steady state profile of the order book describes the average market impact of trades Farmer et al. (2004), Bouchaud et al. (2008). Figure 2 shows that the average profile of the order book displays a hump (in this case, at two ticks from the bid/ask), as observed in empirical studies Bouchaud et al. (2008). Note that this hump feature does not result from any fine-tuning of model parameters or additional ingredients (such as correlation between order flow and past price moves).

5.1.2. Volatility Define the realized volatility of the asset over a day to be given by

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0053" status="decoded_unverified" source-page="15" -->
$$
R V _ { n } = \sqrt { \sum _ { i = 1 } ^ { n } \left ( \log \left ( \frac { P _ { i + 1 } } { P _ { i } } \right ) \right ) ^ { 2 } } , \\ \text {ties in a day and the prices } P _ { i } \, \text { represent}
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0053](images/formula_0053.png)
```text
PDF text layer: RV n = √ √ √ √ n ∑ i =1 ( log ( P i +1 P i )) 2 ,
```
*Formula quality: `decoded_unverified`; source PDF page 15. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

where n is the number of quotes in a day and the prices P i represent the mid-price of the stock. In the first day of the sample, we compute a realized volatility of 0 . 0219 after a total of 370 trades. After repeatedly simulating our model for 370 trades (using parameters λ , μ and θ estimated from the order book time series) we obtained a 95% confidence interval for realized volatility of 0 . 0228 ± 0 . 0003. Interestingly, this estimator yields the correct order of magnitude for realized volatility solely based on intensity parameters for the order flow ( λ,μ,θ ).

Figure 2 Simulation of the steady state profile of the order book: Sky Perfect Communications.

![Image](images/image_000001_1651737b365e6a588d10f41075b6b3447abd13b9fb969ad6bc72f7e9d398e53f.png)

## 5.2. Conditional distributions

As discussed in the introduction, conditional distributions are the main quantities of interest for applications in high-frequency trading. A good description of conditional distributions of variables describing the order book give one the ability to predict their behavior in the short term, which is of obvious interest in optimal trade execution and the design of trading strategies.

5.2.1. One-step transition probabilities In order to assess the model's usefulness for shortterm prediction of order book behavior, we compare one-step transition probabilities implied by our model to corresponding empirical frequencies. In particular, we consider the probability that the number of orders at a given price level increases given that it changes.

Define T m as the time of the m th event in the order book:

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0054" status="decoded_unverified" source-page="16" -->
$$
T _ { 0 } = 0 , \quad T _ { m + 1 } \equiv \inf \{ t \geq T _ { m } | X ( t ) \neq X ( T _ { m } ) \} .
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0054](images/formula_0054.png)
```text
PDF text layer: T 0 =0 , T m +1 ≡ inf { t ≥ T m | X ( t ) = X ( T m ) } . (26)
```
*Formula quality: `decoded_unverified`; source PDF page 16. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

̸

The probability that the number of orders at a distance i from the opposite best quote moves from n to n +1 at the next change is given by

̸

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0055" status="decoded_unverified" source-page="16" -->
$$
P _ { i } ( n ) & \equiv \mathbb { P } [ Q _ { i } ^ { A } ( T _ { m + 1 } ) = n + 1 \, | \, Q _ { i } ^ { A } ( T _ { m } ) = n , Q _ { i } ^ { A } ( T _ { m + 1 } ) \neq n , s ( T _ { m } ) = 1 ] = \left \{ \frac { \frac { \lambda ( 1 ) } { \lambda ( 1 + \mu + n \theta ( 1 ) } } , \quad i = 1 , \\ \frac { \lambda ( 1 ) + \mu + n \theta ( 1 ) } { \lambda ( i ) + n \theta ( i ) } , \quad i > 1 . \\ \intertext { T o s c h o w h y t h e o w y o r m o c i g n e a i v i c a n d o n t h o s e i n g e i n o r s o n c e }
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0055](images/formula_0055.png)
```text
PDF text layer: P i ( n ) ≡ P [ Q A i ( T m +1 ) = n +1 | Q A i ( T m ) = n,Q A i ( T m +1 ) = n,s ( T m ) = 1] = { λ (1) λ (1)+ μ + nθ (1) , i =1 , λ ( i ) λ ( i )+ nθ ( i ) , i > 1 . (27)
```
*Formula quality: `decoded_unverified`; source PDF page 16. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

To see how the above expression arises, consider the case i =1. The next change in Q A 1 is an increase if an arrival of a limit order at price Q A 1 occurs before any of the limit orders at Q A 1 cancel or a market buy order occurs. But since an arrival of a limit order at price Q A 1 occurs with rate λ (1) and a cancellation or market buy order occurs at rate μ + nθ (1), the probability that an arrival of a limit order occurs first is given by λ (1) / ( λ (1) + μ + nθ (1)).

Denoting empirical quantities with a hat, e.g. ˆ Q B i ( t ) is the empirically observed number of bid orders at a distance of i units from the ask price at time t , an estimator for the above probability is given by

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0056" status="decoded_unverified" source-page="16" -->
$$
\hat { P } _ { i } ( n ) \equiv \frac { \hat { B } _ { u p } + \hat { A } _ { u p } } { \hat { B } _ { c h a n g e } + \hat { A } _ { c h a n g e } } ,
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0056](images/formula_0056.png)
```text
PDF text layer: ˆ P i ( n ) ≡ ˆ B up + ˆ A up ˆ B change + ˆ A change ,
```
*Formula quality: `decoded_unverified`; source PDF page 16. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

Figure 3 Probability of an increase in the number of orders at distance i from the opposite best quote in the next change, for i =1 , . . . , 5.

![Image](images/image_000002_7eb9974d5370b76af5deae57417de152b017cc0948525a183c4fe16d058a1bc7.png)

where

̸

<!-- formula-start id="ref_cont_stochastic_order_book_dynamics_2010:formula:0057" status="decoded_unverified" source-page="17" -->
$$
\hat { B } _ { u p } & = \left | \{ m | \hat { Q } _ { i } ^ { B } ( \hat { T } _ { m } ) = n , \, \hat { Q } _ { i } ^ { B } ( \hat { T } _ { m + 1 } ) > n \} \right | \\ \hat { A } _ { u p } & = \left | \{ m | \hat { Q } _ { i } ^ { A } ( \hat { T } _ { m } ) = n , \, \hat { Q } _ { i } ^ { A } ( \hat { T } _ { m + 1 } ) > n \} \right | \\ \hat { B } _ { c h a n g e } & = \left | \{ m | \hat { Q } _ { i } ^ { B } ( \hat { T } _ { m } ) = n , \, \hat { Q } _ { i } ^ { B } ( \hat { T } _ { m + 1 } ) \ne n \} \right | \\ \hat { A } _ { c h a n g e } & = \left | \{ m | \hat { Q } _ { i } ^ { A } ( \hat { T } _ { m } ) = n , \, \hat { Q } _ { i } ^ { A } ( \hat { T } _ { m + 1 } ) \ne n \} \right | \\ \intertext { a n d } \hat { P } _ { i } ( n ) \text { for } 1 \leq i \leq 5 \text { are shown for Sky Perfect Communicacy} . \intertext { a r e a s o n a l b y } \text { close in most cases, indicating that the short }
$$
![Source formula ref_cont_stochastic_order_book_dynamics_2010:formula:0057](images/formula_0057.png)
```text
PDF text layer: ˆ B up = ∣ ∣ ∣ { m | ˆ Q B i ( ˆ T m ) = n, ˆ Q B i ( ˆ T m +1 ) >n } ∣ ∣ ∣ ˆ A up = ∣ ∣ ∣ { m | ˆ Q A i ( ˆ T m ) = n, ˆ Q A i ( ˆ T m +1 ) >n } ∣ ∣ ∣ ˆ B change = ∣ ∣ ∣ { m | ˆ Q B i ( ˆ T m ) = n, ˆ Q B i ( ˆ T m +1 ) = n } ∣ ∣ ∣ ˆ A change = ∣ ∣ { m | ˆ Q A i ( ˆ T m ) = n, ˆ Q A i ( ˆ T m +1 ) = n } ∣ ∣
```
*Formula quality: `decoded_unverified`; source PDF page 17. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

̸

∣ ∣ In Figure 3, P i ( n ) and ˆ P i ( n ) for 1 ≤ i ≤ 5 are shown for Sky Perfect Communications. We see that these probabilities are reasonably close in most cases, indicating that the short-term dynamics of the order book are well-described by the model.

̸

5.2.2. Direction of price moves This section and the next two are devoted to the computation of conditional probabilities using the Laplace transform methods described in § 4. These computations require the numerical inversion of Laplace transforms. The inversions are performed by shifting the random variable X under study by a constant c such that P [ X + c ≥ 0] ≈ 1, then inverting the corresponding one-sided Laplace transform using the methods proposed in Abate and Whitt (1992) and Abate and Whitt (1995). When computing the probability of an increase in mid-price, one can find a good shift c by using the fact that when a = b the probability of an increase in mid-price is .5. This shift c should also serve well for cases where a = b . Table 3 compares the empirical frequencies of an increase in mid-price to model-implied probabilities, given an initial configuration of b orders at the bid price, a orders at the ask price and a spread of 1, for various values of a and b . We computed these quantities using Monte Carlo simulation (using 30,000 replications) and the Laplace transform methods described in § 4. The simulation results, reported as 95% confidence intervals, agree with the Laplace transform computations and show that the probability of an increase in the mid-price is well captured by the model.

|    |    a |    a |    a |    a |    a |
|----|------|------|------|------|------|
| b  |    1 |    2 |    3 |    4 |    5 |
| 1  | .512 | .304 | .263 | .242 | .226 |
| 2  | .691 | .502 | .444 | .376 | .359 |
| 3  | .757 | .601 | .533 | .472 | .409 |
| 4  | .806 | .672 | .580 | .529 | .484 |
| 5  | .822 | .731 | .640 | .714 | .606 |

|    | a           | a           | a           | a           | a           |
|----|-------------|-------------|-------------|-------------|-------------|
| b  | 1           | 2           | 3           | 4           | 5           |
| 1  | .499 ± .006 | .333 ± .005 | .258 ± .005 | .213 ± .005 | .187 ± .005 |
| 2  | .663 ± .005 | .495 ± .006 | .411 ± .006 | .346 ± .005 | .307 ± .005 |
| 3  | .743 ± .006 | .589 ± 006  | .506 ± .006 | .434 ± .006 | .389 ± .006 |
| 4  | .788 ± .005 | .652 ± .006 | .564 ± .006 | .503 ± .006 | .452 ± .006 |
| 5  | .811 .004   | .693 .005   | .615 .006   | .547 .006   | .504 .006   |

±

±

±

±

±

Table 3 Probability of an increase in mid-price: empirical frequencies (top), simulation results (95% confidence intervals) (middle), and Laplace transform method results (bottom).

|    |    a |    a |    a |    a |    a |
|----|------|------|------|------|------|
| b  |    1 |    2 |    3 |    4 |    5 |
| 1  | .500 | .336 | .259 | .216 | .188 |
| 2  | .664 | .500 | .407 | .348 | .307 |
| 3  | .741 | .593 | .500 | .437 | .391 |
| 4  | .784 | .652 | .563 | .500 | .452 |
| 5  | .812 | .693 | .609 | .548 | .500 |

5.2.3. Executing an order before the mid-price moves Table 4 gives probabilities computed using both simulation and our Laplace transform method for executing a bid order before a change in mid-price for various values of a and b and for S =1. Since our data set does not allow us to track specific orders, empirical values for these quantities, as well as the quantities in § 5.2.4, are not obtainable.

5.2.4. Making the spread Table 5 gives probabilities computed using both simulation and our Laplace transform method for executing both a bid and an ask order at the best quotes before the mid-price changes. One interesting observation here is that for a fixed value of a , as b is increased, the probability of making the spread is not monotonic. Thus, for a fixed number of orders at the ask price the probability of making the spread is maximized for a nontrivial optimal number of orders at the bid price.

## 6. Conclusion

We have proposed a stylized stochastic model describing the dynamics of a limit order book, where the occurrence of different types of events -market orders, limit orders and cancellations- are described in terms of independent Poisson processes.

The formulation of the model, which can be viewed as a queuing system, is entirely based on observable quantities and its parameters can be easily estimated from observations of the events in the order book. The model is simple enough to allow analytical computation of various conditional

|    | a           | a           | a           | a           | a           |
|----|-------------|-------------|-------------|-------------|-------------|
| b  | 1           | 2           | 3           | 4           | 5           |
| 1  | .498 ± .004 | .642 ± .004 | .709 ± .004 | .748 ± .004 | .779 ± .004 |
| 2  | .299 ± .004 | .451 ± .004 | .536 ± .004 | .592 ± .004 | .632 ± .004 |
| 3  | .204 ± .004 | .335 ± .004 | .422 ± .004 | .484 ± .004 | .532 ± .004 |
| 4  | .152 ± .003 | .264 ± .004 | .344 ± .004 | .403 ± .004 | .450 ± .004 |
| 5  | .117 .003   | .213 .004   | .291 .004   | .342 .004   | .394 .004   |

±

±

±

±

±

|    |    a |    a |    a |    a |    a |
|----|------|------|------|------|------|
| b  |    1 |    2 |    3 |    4 |    5 |
| 1  | .497 | .641 | .709 | .749 | .776 |
| 2  | .302 | .449 | .535 | .591 | .631 |
| 3  | .206 | .336 | .422 | .483 | .528 |
| 4  | .152 | .263 | .344 | .404 | .452 |
| 5  | .118 | .213 | .287 | .346 | .393 |

Table 4 Probability of executing a bid order before a change in mid-price: simulation results (95% confidence intervals) (top) and Laplace transform method results (bottom).

|    | a           | a           | a           | a           | a           |
|----|-------------|-------------|-------------|-------------|-------------|
| b  | 1           | 2           | 3           | 4           | 5           |
| 1  | .268 ± .004 | .306 ± .004 | .312 ± .004 | .301 ± .004 | .286 ± .004 |
| 2  | .306 ± .004 | .384 ± .004 | .406 ± .004 | .411 ± .004 | .401 ± .004 |
| 3  | .312 ± .004 | .406 ± .004 | .441 ± .004 | .455 ± .004 | .456 ± .004 |
| 4  | .301 ± .004 | .411 ± .004 | .455 ± .004 | .473 ± .004 | .485 ± .004 |
| 5  | .286 .004   | .401 .004   | .456 .004   | .485 .004   | .491 .004   |

±

±

±

±

±

Table 5 Probability of making the spread: simulation results (95% confidence intervals) (top) and Laplace transform method results (bottom).

|    |    a |    a |    a |    a |    a |
|----|------|------|------|------|------|
| b  |    1 |    2 |    3 |    4 |    5 |
| 1  | .266 | .308 | .309 | .300 | .288 |
| 2  | .308 | .386 | .406 | .406 | .400 |
| 3  | .309 | .406 | .441 | .452 | .452 |
| 4  | .300 | .406 | .452 | .471 | .479 |
| 5  | .288 | .400 | .452 | .479 | .491 |

probabilities of order book events via Laplace transform methods, yet rich enough to capture adequately the short-term behavior of the order book: conditional distributions of various quantities of interest show good agreement with the corresponding empirical distributions for parameters estimated from data sets from the Tokyo Stock Exchange. The ability of our model to compute conditional distributions is useful for short-term prediction and design of automated trading strategies. Finally, simulation results illustrate that our model also yields realistic features for long-term (steady state) average behavior of the order book profile and of price volatility.

One by-product of this study is to show how far a stochastic model can go in reproducing the dynamic properties of a limit order book without resorting to detailed behavioral assumptions about market participants or introducing unobservable parameters describing agent preferences, as in the market microstructure literature.

This model can be extended in various ways to take into account a richer set of empirically observed properties Bouchaud et al. (2008). Correlation of the order flow with recent price behavior can be modeled by introducing state-dependent intensities of order arrivals. The heterogeneity of order sizes, which appears to be an important ingredient, can be incorporated via a distribution of order sizes. Both of these features conserve the Markovian nature of the process. A more realistic distribution of inter-event times may also be introduced by modelling the event arrivals via renewal processes. It remains to be seen whether the analytical tractability of the model can be preserved when such ingredients are introduced. We look forward to exploring such extensions in a future work.

## Acknowledgments

The authors thank Ning Cai, Alexander Cherny, Jim Gatheral, Zongjian Liu, Peter Randolph and Ward Whitt for useful discussions.

## References

- Abate, J., W. Whitt. 1992. The Fourier-series method for inverting transforms of probability distributions. Queueing Systems 10 5-88.
- Abate, J., W. Whitt. 1995. Numerical inversion of Laplace transforms of probability distributions. ORSA Journal on Computing 7 (1) 36-43.
- Abate, J., W. Whitt. 1999. Computing Laplace transforms for numerical inversion via continued fractions. INFORMS Journal on Computing 11 (4) 394-405.
- Alfonsi, A., A. Schied, A. Schulz. 2007. Optimal execution strategies in limit order books with general shape functions. Working paper.
- Asmussen, S. 2003. Applied Probability and Queues . Springer-Verlag.
- Bouchaud, J. P., D. Farmer, F. Lillo. 2008. How markets slowly digest changes in supply and demand. Th. Hens, K. Schenk-Hoppe, eds., Handbook of Financial Markets: Dynamics and Evolution . Academic Press.
- Bouchaud, Jean-Philippe, Marc M´ ezard, Marc Potters. 2002. Statistical properties of stock order books: empirical results and models. Quantitative Finance 2 251-256.
- Bovier, A., J. ˘ Cern´ y, O. Hryniv. 2006. The opinion game: Stock price evolution from microscopic market modelling. Int. J. Theor. Appl. Finance 9 91-111.
- Farmer, J. Doyne, L´ aszl´ o Gillemot, Fabrizio Lillo, Szabolcs Mike, Anindya Sen. 2004. What really causes large price changes? Quantitative Finance 4 383-397.
- Foucault, T., O. Kadan, E. Kandel. 2005. Limit order book as a market for liquidity. Review of Financial Studies 18 (4) 1171-1217.
- Hollifield, B., R. A. Miller, P. Sandas. 2004. Empirical analysis of limit order markets. Review of Economic Studies 71 (4) 1027-1063.
- Luckock, H. 2003. A steady-state model of the continuous double auction. Quantitative Finance 3 385-404.
- Maslov, S., M. Mills. 2001. Price fluctuations from the order book perspective - empirical facts and a simple model. PHYSICA A 299 234.
- Obizhaeva, A., J. Wang. 2006. Optimal trading strategy and supply/demand dynamics. Working paper, MIT.
- Parlour, Ch. A. 1998. Price dynamics in limit order markets. Review of Financial Studies 11 (4) 789-816.
- Rosu, I. forthcoming. A dynamic model of the limit order book. Review of Financial Studies .

- Smith, E., J. D. Farmer, L. Gillemot, S. Krishnamurthy. 2003. Statistical theory of the continuous double auction. Quantitative Finance 3 (6) 481-514.
- Zovko, I., J. Doyne Farmer. 2002. The power of patience; A behavioral regularity in limit order placement. Quantitative Finance 2 387-392.
