# The price impact of order book events

Rama Cont, Arseniy Kukanov and Sasha Stoikov

March 2011

## Abstract

We study the price impact of order book events - limit orders, market orders and cancelations - using the NYSE TAQ data for 50 U.S. stocks. We show that, over short time intervals, price changes are mainly driven by the order flow imbalance , defined as the imbalance between supply and demand at the best bid and ask prices. Our study reveals a linear relation between order flow imbalance and price changes, with a slope inversely proportional to the market depth. These results are shown to be robust to seasonality effects, and stable across time scales and across stocks. We argue that this linear price impact model, together with a scaling argument, implies the empirically observed 'square-root' relation between price changes and trading volume. However, the relation between price changes and trade volume is found to be noisy and less robust than the one based on order flow imbalance.

## Contents

| 1 Introduction   | 1 Introduction                         | 1 Introduction                            |   2 |
|------------------|----------------------------------------|-------------------------------------------|-----|
|                  | 1.1                                    | Summary . . . . . . . . . . . . . . . .   |   2 |
|                  | 1.2                                    | Outline . . . . . . . . . . . . . . . . . |   3 |
| 2                | A model for the price impact of orders | A model for the price impact of orders    |   3 |
|                  | 2.1                                    | Variables . . . . . . . . . . . . . . . . |   3 |
|                  | 2.2                                    | A stylized model of the order book . .    |   5 |
|                  | 2.3                                    | Model specification . . . . . . . . . . . |   6 |
| 3                | Estimation and results                 | Estimation and results                    |   8 |
|                  | 3.1                                    | The trades and quotes (TAQ) data . .      |   8 |
|                  | 3.2                                    | Empirical findings . . . . . . . . . . .  |   8 |
|                  | 3.3                                    | Intraday patterns . . . . . . . . . . . . |  14 |
| 4                | Price impact of trades                 | Price impact of trades                    |  16 |
|                  | 4.1                                    | Trade imbalance vs order flow imbalance   |  16 |
|                  | 4.2                                    | Does volume move the prices? . . . . .    |  18 |
| 5                | Conclusion                             | Conclusion                                |  21 |
| A                | Appendix: TAQ data processing          | Appendix: TAQ data processing             |  26 |

## 1 Introduction

The availability of high-frequency records of trades and quotes has stimulated an extensive empirical and theoretical literature on the relation between order flow, liquidity and price movements in order-driven markets. A particularly important issue for applications is the impact of orders on prices: the optimal liquidation of a large block of shares, given a fixed time horizon, crucially involves assumptions on price impact (see Bertsimas and Lo [6], Almgren and Chriss [2], Obizhaeva and Wang [35]).

Various models for price impact have been proposed in the literature but there is little agreement on how to model it [7]. In the empirical literature, price impact has been described by various authors as linear, non-linear, square root, virtual, mechanical, temporary, instantaneous, permanent or transient. The only consensus seems to be the intuitive notion that imbalance between supply and demand moves prices.

The empirical literature on price impact has primarily focused on trades. One approach is to study the impact of 'parent orders' gradually executed over time using proprietary data (see Engle et. al [14], Almgren et. al [3]). Alternatively, empirical studies on public data [16, 18, 20, 28, 29, 43, 38, 39] have investigated the relation between the direction and sizes of trades and price changes and typically conclude that the price impact of trades is an increasing, concave ('square root') function of their size. This focus on trades leaves out the information in quotes, which provide a more detailed picture of price formation [15], and raises a natural question: is volume of trades truly the best explanatory variable for price movements in markets where many quote events can happen between two trades?

Understanding the price impact of orders is also important from a theoretical perspective, in the context of optimal order execution. Huberman and Stanzl [25] show that there are arbitrage opportunities if the effect of trades on prices is permanent and the impact is non-linear; Gatheral [19] extends this analysis by showing that if the price impact function is non-linear, impact needs to decay in a particular way to exclude arbitrage. Bouchaud et al. [9] associated the decay of price impact of trades with limit orders, arguing that there is a 'delicate interplay between two opposite tendencies: strongly correlated market orders that lead to super-diffusion (or persistence), and mean reverting limit orders that lead to sub-diffusion (or anti-persistence)'. This insight implies that looking solely at trades, without including the effect of limit orders amounts to ignoring an important part of the price formation mechanism.

There is ample evidence that limit orders play an important role in determining price dynamics. Arriving limit orders significantly reduce the impact of trades [44] and the concave shape of the price impact function changes depending on the contemporaneous limit order arrivals [41]. The outstanding limit orders (also known as market depth) significantly affect the impact of an individual trade ([30]) and low depth is associated with large price changes [45, 17]. Hasbrouck and Seppi [22] use depth as one of the factors that determine price impact. The emphasis in these studies remains, however, on trades and there are few empirical studies that focus on limit orders from the outset. Notable exceptions are Engle &amp; Lunde [15], Hautsch and Huang [23] who perform an impulse-response analysis of limit and market orders, Hopman [24] who analyzes the impact of different order categories over 30 minute intervals and Bouchaud et al. [12] who examine the impact of market orders, limit orders and cancelations at the level of individual events.

## 1.1 Summary

We conduct in this study an empirical investigation of the impact of order book events -market orders, limit orders and cancelations- on equity prices. Although previous studies give a relatively complex description of this impact, we argue that, in fact, their impact on price dynamics may be modeled parsimoniously through a single variable, the order flow imbalance (OFI), which represents the net order flow at the bid and ask and tracks changes in the size of the bid and ask queues by

- increasing every time the bid size increases, the ask size decreases or the bid/ask prices increase
- decreases every time the bid size decreases, the ask size increases or the bid/ask prices decrease.

Interestingly, this variable treats a market sell and a cancel buy of the same size as equivalent, since they have the same effect on the size of the bid queue. We find that this aggregate variable explains mid-price changes over short time scales in a linear fashion, for a large sample of stocks, with an average R 2 of 65%. The resulting price impact model relates prices, trades, limit orders and cancelations in a simple way: it is linear , requires the estimation of a single parameter and it is robust across stocks and across timescales.

The slope of this relation, which we call the price impact coefficient , exhibits intraday seasonality in line with known intraday patterns observed in spreads, market depth and price volatility [1, 4, 31, 34] which have been explained in terms of intraday shifts in information asymmetry [33] or informativeness of trades [21]. Motivated by a stylized model of the order book, we relate the intraday changes in the price impact coefficient to variations in market depth and show that price impact is inversely proportional to the depth of the order book. This allows us to explain intraday patterns in price impact and price volatility using only observable quantities - the order flow imbalance and the market depth, as opposed to unobservable parameters previously invoked in the literature, such as information asymmetry or informativeness of trades.

The intuition that 'it takes volume to move prices', though widely confirmed by empirical studies [27], is not easy to explain theoretically (see [37, Chapter 6.2]). In Section 4, we show that our price impact model, together with a scaling argument, leads to an apparent 'square root' relation between price changes and trade volume, similar to some findings in the empirical literature [11, 40]. However, we argue that this relation is not robust and is a statistical artifact due to the aggregation of data.

## 1.2 Outline

The article is structured as follows. In Section 2, motivated by a stylized model of the order book, we specify a parsimonious model that links stock price changes, order flow imbalance and market depth. Section 3 describes the trades and quotes data and estimation results for our model. There, we also show how intraday patterns in depth and order flow imbalance generate intraday patterns in price impact and price volatility. In Section 4 we discuss the role of trading volume as an explanatory variable and show that order flow imbalance is more effective in explaining price moves than variables based on trades. We also derive a scaling relation between order flow imbalance and traded volume and show how the 'square-root' price impact of volume follows from our model. We present our conclusions in Section 5.

## 2 A model for the price impact of orders

## 2.1 Variables

We focus on 'Level I order book': the limit orders sitting at the best bid and ask. Every observation of the bid and the ask consists of the bid price P B , the size q B of the bid queue (in number of shares), the ask price P A and the size q A of the ask queue (in number of shares):

![Image](images/image_000000_8ff7b0c123f5d4483d6eb44a9eb63d5d42a2c13fa9b2fb6c6868758c92762423.png)

The bid price and size represent the demand for a stock, while the ask price and size represent the supply. We enumerate these observations by n and compare ( P B n -1 , q B n -1 , P A n -1 , q A n -1 ) with ( P B n , q B n , P A n , q A n ). Between two such observations, only one of the following events can occur:

- P B n &gt; P B n -1 or q B n &gt; q B n -1 signifying an increase in demand
- P B n &lt; P B n -1 or q B n &lt; q B n -1 signifying a decrease in demand
- P A n &lt; P A n -1 or q A n &gt; q A n -1 signifying an increase in supply
- P A n &gt; P A n -1 or q A n &lt; q A n -1 signifying a decrease in supply

We define the variable e n which measures the contribution of the n -th event to the size of bid and ask queues:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0001" status="verified_source" source-page="4" -->
$$
e_n=I_{\{P^B_n\geq P^B_{n-1}\}}q^B_n-I_{\{P^B_n\leq P^B_{n-1}\}}q^B_{n-1}-I_{\{P^A_n\leq P^A_{n-1}\}}q^A_n+I_{\{P^A_n\geq P^A_{n-1}\}}q^A_{n-1}
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0001](images/formula_0001.png)
*Formula quality: `verified_source`; source PDF page 4. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:91 (score=0.9333).*
<!-- formula-end -->

Note that if q B increases but P B remains the same, we assign e n = q B n -q B n -1 , representing the size that was added at the bid. If q B decreases, we also assign e n = q B n -q B n -1 , representing the size that was removed from the bid, whether due to a market sell or cancel buy order. If P B increases, we let e n = q B n , representing the size of a price-improving limit order. If P B decreases, we let e n = q B n -1 , representing the size that was removed, whether due to a market order or a cancellation. The same classification is done for events on the ask side, with signs reversed.

Events affecting the order book occur at random times τ n , and we define N ( t ) = max { n | τ n ≤ t } to be the number of events during [0 , t ]. We define the order flow imbalance over time intervals [ t k -1 , t k ] as a sum of individual event contributions e n over these intervals:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0002" status="verified_source" source-page="4" -->
$$
OFI_{k}=\sum_{n=N(t_{k-1})+1}^{N(t_{k})}{e_n},
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0002](images/formula_0002.png)
*Formula quality: `verified_source`; source PDF page 4. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:97 (score=1.0).*
<!-- formula-end -->

where N ( t k -1 ) + 1 and N ( t k ) are the index of the first and the index of the last event in the interval [ t k -1 , t k ]. The order flow imbalance is a measure of supply/demand imbalance, which encompasses trades, limit orders and cancelations. Whereas previous studies [10, 20, 22, 29, 38, 43] focused on measures of 'trade imbalance' 1 , using orders provides a more natural way of measuring supply and demand.

We also consider mid-price changes (in number of ticks) over the same time grid:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0003" status="verified_source" source-page="4" -->
$$
\Delta P_{k}=(P_{k}-P_{k-1})/\delta,
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0003](images/formula_0003.png)
*Formula quality: `verified_source`; source PDF page 4. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:101 (score=1.0).*
<!-- formula-end -->

where P k is the mid-quote price at time t k and δ is the tick size (equal to 1 cent in our data).

1 Hopman [24] computes the supply/demand imbalance based on limit orders and trades, but not cancelations.

## 2.2 A stylized model of the order book

Consider first a stylized model of the order book in which

1. the number of shares at each price level beyond the best bid/ask is equal to D .
2. limit orders arrivals and cancelations occur only at the best bid/ask.

We will show that under these assumptions a linear relation holds between order flow imbalance and price changes. Consider three scenarios, when only market buy orders, limit buy orders or limit sell cancels happen over some time interval [ t, t +∆ t ]:

- Market sell orders remove M s shares from the bid.
- Market sell orders remove M s shares from the bid, while limit buy orders add L b shares to the bid.
- Market sell orders and limit buy cancels remove M s + C b shares from the bid, while limit buy orders add L b shares to the bid.

![Image](images/image_000001_aee7ee31c27d76e67dfd4cda1e4a8bd08c0015bd4211a46095fe317bb32e8c0a.png)

![Image](images/image_000002_dd37ca2bc9898d897f65d5f13c7ccfa043600447444a8c254a0c3d4a57c0e45e.png)

![Image](images/image_000003_a80e94bfc0304b29c9e7ddaec3a1d1196e18c1992c1e1a6e2d7a2fa12c91c0a9.png)

The three variables M b , C s and L s for the ask can be defined analogously. Under the above assumptions, the impact of order book events at the bid (ask) side of the book is additive and only depends on their net effect on the bid (ask) queue size:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0004" status="verified_source" source-page="6" -->
$$
\Delta P^b= \lceil (L^b-C^b-M^s)/D \rceil
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0004](images/formula_0004.png)
*Formula quality: `verified_source`; source PDF page 6. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:155 (score=1.0).*
<!-- formula-end -->

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0005" status="verified_source" source-page="6" -->
$$
\Delta P^a= -\lceil (L^s-C^s-M^b)/D \rceil
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0005](images/formula_0005.png)
*Formula quality: `verified_source`; source PDF page 6. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:159 (score=1.0).*
<!-- formula-end -->

These relations are remarkably simple - they involve no parameters and incorporate the effects of all order book events on bid and ask prices. Although the following analysis can be carried for the bid and the ask prices separately, we take their average (the mid-price) to simplify the analysis:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0006" status="verified_source" source-page="6" -->
$$
\Delta P= \frac{1}{2}\lceil (L^b-C^b-M^s)/D \rceil - \frac{1}{2}\lceil (L^s-C^s-M^b)/D \rceil
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0006](images/formula_0006.png)
*Formula quality: `verified_source`; source PDF page 6. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:163 (score=1.0).*
<!-- formula-end -->

Note that the above is equivalent (up to truncation) to

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0007" status="verified_source" source-page="6" -->
$$
\Delta P=\frac{OFI}{2D}+\epsilon,
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0007](images/formula_0007.png)
*Formula quality: `verified_source`; source PDF page 6. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:167 (score=1.0).*
<!-- formula-end -->

where OFI = L b -C b -M s -L s + C s + M b and ϵ is the truncation error. This expression for OFI is obtained from its definition by grouping individual order contrubutions e i by their types (limit buys, market sells, etc).

## 2.3 Model specification

In reality, order books have complex dynamics and the relation (1) will only hold in a statistical sense. For example, limit orders and cancelations occur at all levels of the order book. The distribution of depth across price levels often has humps, gaps and is itself a separate object of study [39, 46]. Moreover, the depth is subject to important intraday fluctuations. Finally, there may be hidden orders in the book which are not reported in the data [5]. With these considerations, we suggest the following relation:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0008" status="verified_source" source-page="6" -->
$$
\Delta P_{k}=\beta \quad OFI_{k}+\epsilon_{k},
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0008](images/formula_0008.png)
*Formula quality: `verified_source`; source PDF page 6. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:176 (score=1.0).*
<!-- formula-end -->

where β is the price impact coefficient and ϵ k is a noise term due to the influence of deeper levels of the order book and rounding errors. Our earlier discussion suggests that the price impact coefficient is inversely related to market depth, which is itself subject to intraday fluctuations. We define a measure of depth by averaging the bid/ask queue sizes over intervals [ T i -1 , T i ]:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0009" status="verified_source" source-page="6" -->
$$
AD_{i}=\frac{1}{2(N(T_{i})-N(T_{i-1})-1)}\sum_{n=N(T_{i-1})+1}^{N(T_{i})}{(q^B_n+q^A_n)}
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0009](images/formula_0009.png)
*Formula quality: `verified_source`; source PDF page 6. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:181 (score=0.9429).*
<!-- formula-end -->

We therefore specify the following relation between the price impact coefficient β i in the time interval [ T i -1 , T i ] and our measure of market depth as:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0010" status="verified_source" source-page="6" -->
$$
\beta_i=\frac{c}{AD_{i}^\lambda} +\nu_{i},
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0010](images/formula_0010.png)
*Formula quality: `verified_source`; source PDF page 6. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:184 (score=1.0).*
<!-- formula-end -->

where c, λ are constants and ν i is a noise term. Note that the stylized model exposed above corresponds to λ = 1.

Similarly, for the ask:

The specification (2-3) may be regarded as a model of the instantaneous price impact over a short time interval [ t k -1 , t k ]. An order, submitted at τ ∈ [ t k -1 , t k ], has a contribution e τ and joins the aggregate order flow imbalance OFI k . If the order goes in the same direction as the majority of the orders ( sgn ( e τ ) = sgn ( OFI k )), it reinforces the concurrent order flow imbalance and can affect the price. If the order goes against the concurrent order flow imbalance ( sgn ( e τ ) = -sgn ( OFI k )), it is compensated by other orders and may have an instantaneous impact of zero. In our model all events (including trades) have a linear price impact, equal to β on average. Their realized impact, however, depends on the rest of the orders that arrive during the same time interval.

The idea that the concurrent limit order activity can make a difference in terms of trades' impact was demonstrated by Stephens et al. [41], where authors show that the shape of the price impact function essentially depends on the contemporaneous limit order activity. Our approach can also be related to the model proposed by Bouchaud et al. [12]. where order book events have a linear impact on prices, which depends on their signs and types 2 . The major difference of our models lies in the aggregation across time and events. As argued in [12], order book events have complicated auto- and cross-correlation structures on the timescale of individual events, which typically vanish after 10 seconds. In our data the autocorrelations at a timescale of 10 seconds are small and quickly vanish as well (ACF plots for a representative stock are shown on Figure 1). Finally, Hasbrouck and Seppi [22] propose a model similar to (2, 3) for explaining the price impact of trades. Although their focus is on trades, they also allow the price impact coefficient to depend on contemporaneous liquidity factors and change through time.

However, the linear equation (2) is quite different from models of price impact that consider only the size of trades [18, 20, 29, 43, 38, 39]. Instead of modeling price impact of trades as a (nonlinear) function of trade size, we show that the price impact of all events (including trades) is a linear function of their size after events are aggregated into a single imbalance variable. In Section 4 we will argue that, first, the effect of trades on prices is adequately captured by the order flow imbalance and, second, that if one leaves out all events except trades, the relation 2 leads to an apparent concave relation between price changes and trade volume.

The next section provides an overview of the estimation results for our model.

Figure 1: ACF of the mid-price changes ∆ P k , the order flow imbalance OFI k and the 5% significance bounds for the Schlumberger stock (SLB).

![Image](images/image_000004_4e3d78759723888e4adec1f48c54d05a5ca348995a6632b67975b6e3009dda94.png)

2 Note that in our case all order book events have the same average impact, equal to β i , regardless of their type. As shown in [12], average impacts of different event types are empirically very similar, allowing to reasonably approximate them with a single number.

## 3 Estimation and results

## 3.1 The trades and quotes (TAQ) data

Our data set consists of one calendar month (April, 2010) of trades and quotes (TAQ) data for 50 stocks. The stocks were selected by a random number generator from the S&amp;P 500 constituents. The S&amp;P 500 composition for that month was obtained from Compustat and the data for individual stocks was obtained from the TAQ consolidated quotes and TAQ consolidated trades databases. The data were obtained through Wharton Research Data Services (WRDS).

Consolidated quotes contains all changes in queue sizes at the best bid and ask. For each stock, a data update consists of a timestamp (rounded to the nearest second), bid price, bid size, ask price, ask size and exchange flag. Consolidated trades (or market orders) consist of a timestamp, a price and a size. These two data sets are often referred to as Level 1 data, as opposed to Level 2 data, which also includes quote updates deeper in the book.

Our reason for using TAQ data rather than Level 2 order book data, is that it is far more accessible, yet contains all events in the top order book (best bid and ask updates). We demonstrate that Level 1 TAQ data can be successfully used to study limit orders and we hope that more empirical studies of that subject will follow. We note that the ratio of the number of quote updates to the number trades is roughly 40 to 1 in our data. Many empirical studies have focused exclusively on trades rather than quotes, but the sheer ratio in the size of these data sets is a good indicator that more information may be conveyed by the quotes than by trades.

Using a procedure described in detail in the appendix, we aggregate all quote updates to estimate the National Best Bid and Offer sizes and prices (NBBO) at each quote update. Instead of aggregating all exchanges in this fashion, one may also simply filter by the exchange flag and study one exchange at the time. Focussing on one exchange at a time yields similar results.

We use a uniform grid in time { t 0 , . . . , t N } with a timescale t k -t k -1 ≡ ∆ t = 10 seconds to compute the price changes and the order flow imbalances. To test the robustness of our findings to the choice of the basic timescale, we repeated our calculations on a subsample of stocks for different values of ∆ t , ranging from 10 quote updates (usually less than half of a second in our data) up to 10 minutes. The fit of our model generally increases with ∆ t , but the rest of the results stays the same. Time aggregation serves two purposes: first, it alleviates the issue of data discreteness and second, it mitigates the errors due to the trade matching algorithm (described in the Appendix).

## 3.2 Empirical findings

We assume that the price impact coefficient β is constant over each half-hour interval [ T i , T i +1 ] and estimate the model by ordinary least squares regression in each half-hour subsample for each stock:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0011" status="verified_source" source-page="8" -->
$$
\Delta P_{k}=\hat{\alpha}_{i}+\hat{\beta}_{i}OFI_{k}+\hat{\epsilon}_{k},
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0011](images/formula_0011.png)
*Formula quality: `verified_source`; source PDF page 8. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:231 (score=1.0).*
<!-- formula-end -->

Figure 2 presents a scatter plot of ∆ P k against OFI k for one of the half-hour subsamples. Table 2 reports regression outputs, averaged across time for each stock. This table provides strong evidence of a linear relation between order flow imbalance and price changes. The goodness of fit is surprisingly high for all of the stocks, suggesting that the model (2) performs well regardless of stock-specific features 3 . In addition to the high quality of fits, the regression coefficient β i is virtually always statistically significant (at a 95% level of the z-test), while the intercept is mostly insignificant. Figure 3 represents the histogram of excess kurtosis values of the residuals ˆ ϵ k across subsamples: the relatively low level of kurtosis shows that the residuals are not predominantly associated with large price changes. Since the regression residuals demonstrate heteroscedasticity, we used White's heteroscedasticity-consistent standard errors for the z-test. To check for higher order/nonlinear dependence we add a quadratic term ˆ γ Q,i OFI k | OFI k | to the regression. The increase in R 2 , from 65% to 68% on average, is barely noticeable and the coefficient ˆ γ Q,i is statistically insignificant in most samples.

3 We note that OFI k includes the contributions of price-changing order book events, leading to a possible tautology in the regression (4). This problem is inherent to all price impact modeling, because the explanatory variables (events or trades) can directly cause price changes. To test that the high R 2 in our regressions is not due to this tautology, we estimated (4) on a subsample of stocks, excluding the price-changing events from OFI k . With this change the R 2 declined, but remained in the 35%-60% region.

Figure 2: Scatter plot of ∆ P k against OFI k for the Schlumberger stock (SLB), 04/01/2010 11:30-12:00pm.

![Image](images/image_000005_411736a37fbca7a8a236c301c6524e0ecd54c0b2cbc329ec2e55d5ae6e7c67d0.png)

Figure 3: Distribution of excess kurtosis of the residuals ˆ ϵ k across stocks and time.

![Image](images/image_000006_d9a5229e9e7650ff91b58a73215fe7150d77984af2b708deb46bfb2568ce15b8.png)

Table 1. Descriptive statistics

| Name                    | Ticker   |   Price |   Daily volume, shares |   Number of best quote updates |   Number of trades |   Average Spread, cents |   Maximum spread, cents |   Best quote depth, shares |
|-------------------------|----------|---------|------------------------|--------------------------------|--------------------|-------------------------|-------------------------|----------------------------|
| Advanced Micro Devices  | AMD      |    9.61 |               20872996 |                         417204 |               6687 |                       1 |                       1 |                       1035 |
| Apollo Group            | APOL     |   62.92 |                1949337 |                         172942 |               4095 |                       2 |                       5 |                         15 |
| American Express        | AXP      |   45.21 |                8678723 |                         559701 |               7748 |                       1 |                      24 |                         79 |
| Autozone                | AZO      |  179.03 |                 243197 |                          43682 |               1081 |                       9 |                      35 |                          7 |
| Bank of America         | BAC      |   18.43 |              164550168 |                        1529395 |              15008 |                       1 |                       1 |                       3208 |
| Becton Dickinson        | BDX      |   78.07 |                1130362 |                          61029 |               2968 |                       2 |                       5 |                         15 |
| Bank of New York Mellon | BK       |   31.77 |                6310701 |                         285619 |               5518 |                       1 |                       1 |                        122 |
| Boston Scientific       | BSX      |    7.13 |               25746787 |                         309441 |               6768 |                       1 |                       1 |                       2965 |
| Peabody Energy corp     | BTU      |   47.14 |                5210642 |                         298616 |               7267 |                       1 |                       3 |                         29 |
| Caterpillar             | CAT      |   67.20 |                6664891 |                         392499 |               8224 |                       1 |                       2 |                         38 |
| Chubb                   | CB       |   52.22 |                1951618 |                         149010 |               3601 |                       1 |                       2 |                         43 |
| Carnival                | CCL      |   40.16 |                4275911 |                         215427 |               5503 |                       1 |                       2 |                         53 |
| Cincinnati Financial    | CINF     |   29.41 |                 688914 |                          51373 |               1528 |                       1 |                       2 |                         42 |
| CME Group               | CME      |  322.83 |                 418955 |                          38504 |               1412 |                      31 |                     103 |                          5 |
| Coach                   | COH      |   41.91 |                3126469 |                         176795 |               4458 |                       1 |                       2 |                         41 |
| ConocoPhillips          | COP      |   56.09 |                9644544 |                         426614 |               8621 |                       1 |                       2 |                         84 |
| Coventry Health Care    | CVH      |   24.16 |                1157022 |                          79305 |               2213 |                       1 |                       2 |                         38 |
| Denbury Resources       | DNR      |   17.88 |                5737740 |                         263173 |               4643 |                       1 |                       1 |                        186 |
| Devon Energy            | DVN      |   66.98 |                3260982 |                         177006 |               5805 |                       2 |                       4 |                         18 |
| Equifax                 | EFX      |   35.34 |                 799505 |                          62957 |               1945 |                       1 |                       3 |                         39 |
| Eaton                   | ETN      |   78.53 |                1757136 |                          67989 |               3580 |                       2 |                       6 |                         13 |
| Fiserv                  | FISV     |   52.56 |                1038311 |                          58304 |               2208 |                       1 |                       3 |                         20 |
| Hasbro                  | HAS      |   39.48 |                1322037 |                          86040 |               2672 |                       1 |                       2 |                         34 |
| HCP                     | HCP      |   32.63 |                2872521 |                         213045 |               4357 |                       1 |                       2 |                         48 |
| Starwood Hotels         | HOT      |   50.59 |                3164807 |                         150252 |               5106 |                       2 |                       4 |                         22 |
| Kohl's                  | KSS      |   56.88 |                3064821 |                         128196 |               4936 |                       1 |                       3 |                         27 |
| L-3 Communications      | LLL      |   94.64 |                 670937 |                          72818 |               2141 |                       2 |                       6 |                          9 |
| Lockheed Martin         | LMT      |   84.14 |                1416072 |                          88254 |               3333 |                       2 |                       5 |                         15 |
| Macy's                  | M        |   23.40 |                8324639 |                         491756 |               6469 |                       1 |                       1 |                        176 |
| Marriott                | MAR      |   34.45 |                5014098 |                         238190 |               5499 |                       1 |                       2 |                         65 |
| McAfee                  | MFE      |   40.04 |                2469324 |                         109073 |               3561 |                       1 |                       2 |                         40 |
| McGraw-Hill             | MHP      |   34.90 |                1954576 |                         102389 |               3261 |                       1 |                       2 |                         42 |
| Medco Health Solutions  | MHS      |   63.22 |                2798098 |                         109382 |               4680 |                       1 |                       3 |                         25 |
| Merck                   | MRK      |   36.03 |               13930842 |                         448748 |               7997 |                       1 |                       1 |                        231 |
| Marathon Oil            | MRO      |   32.33 |                5035354 |                         341408 |               5522 |                       1 |                       1 |                        143 |
| MeadWestvaco            | MWV      |   26.96 |                1035547 |                          92825 |               2312 |                       1 |                       3 |                         37 |
| Newmont Mining          | NEM      |   53.43 |                5673718 |                         435295 |               7717 |                       1 |                       2 |                         38 |
| Omnicom                 | OMC      |   41.17 |                3357585 |                         150800 |               4359 |                       1 |                       2 |                         65 |
| MetroPCS Communications | PCS      |    7.53 |                4424560 |                         107967 |               2901 |                       1 |                       1 |                        523 |
| Pultegroup              | PHM      |   11.80 |                6834683 |                         262420 |               4604 |                       1 |                       1 |                        319 |
| PerkinElmer             | PKI      |   23.98 |                1268774 |                          78114 |               2127 |                       1 |                       2 |                         72 |
| Ryder System            | R        |   44.01 |                 631889 |                          47422 |               2085 |                       2 |                       5 |                         11 |
| Reynolds American       | RAI      |   54.44 |                 773387 |                          56236 |               2076 |                       1 |                       4 |                         22 |
| Schlumberger            | SLB      |   67.94 |                9476060 |                         440839 |              10286 |                       1 |                       2 |                         39 |
| Teco Energy             | TE       |   16.52 |                1070815 |                          70318 |               1807 |                       1 |                       1 |                        148 |
| Time Warner Cable       | TWC      |   53.21 |                1770234 |                          88286 |               3554 |                       2 |                       3 |                         22 |
| Whirlpool               | WHR      |   97.73 |                1424264 |                         134152 |               3348 |                       4 |                       9 |                         10 |
| Windstream              | WIN      |   11.03 |                2508830 |                         104887 |               2937 |                       1 |                       1 |                        798 |
| Watson Pharmaceuticals  | WPI      |   42.51 |                 895967 |                          63094 |               2024 |                       1 |                       3 |                         29 |
| XTO Energy              | XTO      |   48.13 |                7219436 |                         612804 |               5040 |                       1 |                       7 |                        225 |
| Grand mean              |          |   51.75 |                7512376 |                         223232 |               4552 |                       2 |                       6 |                        227 |

Table 1 presents the average mid-price, daily transaction volume, daily number of best quote updates, daily number of trades, spread and the depth at the best bid and ask for 50 randomly chosen U.S. stocks. All values are calculated from the filtered data, that consists of 21 trading day during April, 2010.

Table 2. Relation between price changes and order flow imbalance.

̸

̸

̸

| Ticker    | Average results   | Average results   | Average results   | Average results   | Average results   | Average results   | Average results   | Hypothesis testing   | Hypothesis testing   | Hypothesis testing   |
|-----------|-------------------|-------------------|-------------------|-------------------|-------------------|-------------------|-------------------|----------------------|----------------------|----------------------|
| Ticker    | ˆ α               | t (ˆ α )          | ˆ β               | t ( ˆ β )         | ˆ γ Q             | t (ˆ γ Q )        | R 2               | { α = 0 }            | { β = 0 }            | { γ Q = 0 }          |
| AMD       | -0.0032           | -0.17             | 0.0008            | 9.96              | 1.4E-07           | 0.68              | 64%               | 0%                   | 98%                  | 22%                  |
| APOL      | 0.0038            | 0.10              | 0.0555            | 10.32             | -2.2E-04          | -1.17             | 63%               | 12%                  | 91%                  | 4%                   |
| AXP       | 0.0019            | 0.08              | 0.0082            | 13.87             | -3.8E-06          | -0.88             | 69%               | 11%                  | 100%                 | 5%                   |
| AZO       | 0.0101            | 0.33              | 0.1619            | 6.39              | -9.3E-04          | -0.89             | 47%               | 23%                  | 97%                  | 3%                   |
| BAC       | -0.0018           | -0.09             | 0.0002            | 18.36             | 1.9E-09           | 0.01              | 79%               | 1%                   | 100%                 | 8%                   |
| BDX       | -0.0008           | -0.06             | 0.0536            | 10.08             | -1.1E-04          | -0.38             | 63%               | 9%                   | 100%                 | 8%                   |
| BK        | -0.0078           | -0.19             | 0.0069            | 14.97             | -4.0E-06          | -0.57             | 74%               | 3%                   | 100%                 | 6%                   |
| BSX       | 0.0000            | -0.01             | 0.0003            | 6.12              | 7.8E-08           | 1.14              | 58%               | 0%                   | 81%                  | 22%                  |
| BTU       | 0.0048            | 0.12              | 0.0242            | 14.51             | -3.5E-05          | -1.26             | 72%               | 11%                  | 100%                 | 3%                   |
| CAT       | 0.0147            | 0.23              | 0.0194            | 14.85             | -1.9E-05          | -1.13             | 71%               | 12%                  | 99%                  | 3%                   |
| CB        | -0.0086           | -0.07             | 0.0191            | 11.97             | -3.5E-07          | 0.00              | 64%               | 5%                   | 100%                 | 8%                   |
| CCL       | -0.0067           | -0.18             | 0.0140            | 13.88             | -1.2E-05          | -0.64             | 70%               | 3%                   | 99%                  | 7%                   |
| CINF      | -0.0030           | -0.02             | 0.0260            | 10.73             | -7.0E-06          | 0.27              | 70%               | 1%                   | 98%                  | 16%                  |
| CME       | 0.0506            | 0.05              | 0.6262            | 4.98              | -7.2E-03          | -0.99             | 35%               | 15%                  | 94%                  | 2%                   |
| COH       | -0.0221           | -0.45             | 0.0179            | 12.75             | -1.7E-05          | -0.77             | 69%               | 2%                   | 100%                 | 3%                   |
| COP       | -0.0008           | 0.06              | 0.0084            | 12.50             | -5.8E-06          | -1.17             | 68%               | 10%                  | 100%                 | 3%                   |
| CVH       | -0.0034           | -0.06             | 0.0217            | 10.83             | 7.6E-06           | 0.20              | 65%               | 3%                   | 99%                  | 10%                  |
| DNR       | -0.0008           | -0.04             | 0.0045            | 12.76             | -1.3E-07          | 0.19              | 69%               | 1%                   | 99%                  | 13%                  |
| DVN       | 0.0112            | 0.18              | 0.0370            | 11.48             | -1.0E-04          | -1.59             | 65%               | 17%                  | 97%                  | 0%                   |
| EFX       | -0.0032           | -0.04             | 0.0222            | 8.71              | 6.4E-05           | 0.64              | 56%               | 1%                   | 98%                  | 18%                  |
| ETN       | -0.0076           | 0.05              | 0.0712            | 10.51             | -2.3E-04          | -1.14             | 65%               | 14%                  | 98%                  | 1%                   |
| FISV      | -0.0002           | 0.06              | 0.0397            | 10.42             | -2.3E-05          | -0.19             | 63%               | 4%                   | 100%                 | 8%                   |
| HAS       | -0.0031           | -0.02             | 0.0222            | 11.45             | 4.7E-06           | 0.21              | 67%               | 3%                   | 100%                 | 16%                  |
| HCP       | -0.0078           | -0.17             | 0.0150            | 13.60             | -1.4E-05          | -0.46             | 67%               | 2%                   | 100%                 | 6%                   |
| HOT       | -0.0012           | 0.05              | 0.0345            | 12.64             | -7.2E-05          | -1.21             | 68%               | 10%                  | 99%                  | 2%                   |
| KSS       | -0.0030           | -0.04             | 0.0317            | 13.82             | -5.4E-05          | -0.80             | 71%               | 10%                  | 98%                  | 3%                   |
| LLL       | 0.0160            | 0.32              | 0.1000            | 11.76             | -3.8E-04          | -0.75             | 67%               | 14%                  | 96%                  | 3%                   |
| LMT       | 0.0006            | 0.00              | 0.0520            | 13.58             | -1.2E-04          | -0.98 0.13        | 72%               | 14%                  | 100%                 | 1%                   |
| M         | -0.0010           | 0.04 -0.02        | 0.0043 0.0121     | 15.82 14.61       | 8.8E-08 -4.1E-06  | -0.23             | 75% 71%           | 0% 3%                | 100%                 | 12%                  |
| MAR MFE   | -0.0039 0.0087    | 0.16              | 0.0205            | 12.72             | -3.8E-05          | -0.38             | 68%               | 7%                   | 100% 100%            | 4% 7%                |
| MHP       | -0.0073           | -0.13             | 0.0211            | 11.62             | 5.8E-06           | 0.14              | 68%               | 2%                   | 99%                  | 11%                  |
| MHS       | -0.0055           | -0.16             | 0.0334            | 11.70             | -8.3E-05          | -1.10             | 66%               | 9%                   | 99%                  | 3%                   |
| MRK MRO   | -0.0065           | -0.20             | 0.0032            | 12.53 13.67       | -5.4E-07          | -0.38             | 69%               | 1% 5%                | 100% 100%            | 8% 13%               |
| MWV       | 0.0018            | 0.07              | 0.0058            |                   | -3.6E-07          | 0.22              | 69%               |                      | 100%                 | 7%                   |
|           | -0.0011           | 0.01              | 0.0205            | 11.79             | -1.7E-05          | -0.25             | 68%               | 3%                   |                      |                      |
| NEM       | -0.0102           | -0.22             | 0.0170            | 13.81             | -1.9E-05          | -1.36             | 71%               | 8%                   | 100%                 | 2%                   |
| OMC       | -0.0099           | -0.28             | 0.0144            | 11.88             | -4.5E-06          | -0.01             | 65%               | 2%                   | 99%                  | 13% 24%              |
| PCS       | -0.0006           | -0.03             | 0.0015            | 5.21              | 1.8E-06           | 1.01              | 53%               | 0%                   | 79%                  |                      |
| PHM       | 0.0006            | 0.03              | 0.0027            | 10.33             | 8.4E-07           | 0.55              | 66%               | 1%                   | 98%                  | 21%                  |
| PKI       | -0.0004           | -0.03             | 0.0102            | 7.25              | 4.1E-05           | 1.10              | 53%               | 2%                   | 94%                  | 29%                  |
| R RAI SLB | 0.0006 -0.0070    | 0.03              | 0.0667            | 10.14 10.40       | 3.7E-05 2.6E-05   | 0.01              | 63% 76%           | 8%                   | 98% 100%             | 10% 11%              |
|           | -0.0077           | -0.10             | 0.0396            |                   | 1.4E-05           |                   |                   | 5%                   | 100%                 |                      |
|           |                   | -0.15             | 0.0198            | 16.76             |                   | 0.01              | 66%               | 7%                   |                      | 1%                   |
| TE        | 0.0011            | 0.05              | 0.0049            | 6.66              | -1.8E-05          | -1.15 1.45        | 54%               | 2%                   | 86%                  | 30%                  |
| TWC       | -0.0130 -0.0004   | -0.13             | 0.0384            | 11.80             | -5.6E-05          | -0.44             | 64%               | 8% 22%               | 99% 97%              | 5% 4%                |
| WHR       | 0.0628            | 0.63 -0.03        | 0.1278 0.0009     | 10.26 3.12        | -3.3E-04          | -0.80 0.76        | 65% 44%           |                      | 60% 98%              | 15%                  |
| WIN WPI   | -0.0090           | -0.21             | 0.0270            | 10.47             | 1.5E-06 2.9E-05   | 0.28              | 66%               | 1% 3%                |                      | 14%                  |
| XTO       | -0.0088           | -0.18             |                   |                   | 2.7E-07           | 0.30              | 65%               | 0%                   |                      | 18%                  |
|           |                   | -0.02             | 0.0029            | 13.28             | -2.0E-04          | -0.28             | 65%               |                      | 100%                 |                      |
| Average   | 0.0002            |                   | 0.0398            | 11.47             |                   |                   |                   | 6%                   | 97%                  | 9%                   |

Table 2 presents a cross-section of results (averaged across time) for the regressions:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0012" status="decoded_unverified" source-page="11" -->
$$
\Delta P _ { k } & = \hat { \alpha } _ { i } + \hat { \beta } _ { i } O F I _ { k } + \hat { \epsilon } _ { k } , \\ \Delta P _ { k } & = \hat { \alpha } _ { Q , i } + \hat { \beta } _ { Q , i } O F I _ { k } + \hat { \gamma } _ { Q , i } O F I _ { k } | O F I _ { k } | + \hat { \epsilon } _ { Q , k } ,
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0012](images/formula_0012.png)
```text
PDF text layer: ∆ P k = ˆ α i + ˆ β i OFI k +ˆ ϵ k , ∆ P k = ˆ α Q,i + ˆ β Q,i OFI k + ˆ γ Q,i OFI k | OFI k | +ˆ ϵ Q,k ,
```
*Formula quality: `decoded_unverified`; source PDF page 11. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

where ∆ P k are the 10-second mid-price changes and OFI k are the contemporaneous order flow imbalances. These regressions were estimated using 273 half-hour subsamples (indexed by i ) for each stock and their outputs were averaged across subsamples. Each subsample typically contains about 180 observations (indexed by k ). The t-statistics were computed using White's standard errors. For brevity, we report the R 2 , the average ˆ α i and the average ˆ β i only for the first regression (with a single OFI k term). There is almost no difference between averages of estimates ˆ β i and ˆ β Qi and the R 2 in two regressions. The last three columns report the percentage of samples where the coefficient(s) passed the z-test at the 5% significance level.

Next, we estimate the parameters λ and c in (3). For each stock, we first obtain ˆ λ fi t via a loglinear regression:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0013" status="verified_source" source-page="12" -->
$$
\log{\hat{\beta}_i}=\hat{\alpha_{L,i}}-\hat{\lambda}\log{AD_i}+\hat{\epsilon}_{L,i}
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0013](images/formula_0013.png)
*Formula quality: `verified_source`; source PDF page 12. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:518 (score=0.9375).*
<!-- formula-end -->

Then, using ˆ λ , we estimate c in a linear regression:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0014" status="verified_source" source-page="12" -->
$$
\hat{\beta}_i=\hat{\alpha_{M,i}}+\frac{\hat{c}}{AD^{\hat{\lambda}}_i}+\hat{\epsilon}_{M,i}
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0014](images/formula_0014.png)
*Formula quality: `verified_source`; source PDF page 12. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:524 (score=0.92).*
<!-- formula-end -->

Both regressions are estimated using ordinary least squares. The results are presented in Table 3: the quality of these fits convincingly demonstrates that the instantaneous price impact (measured by ˆ β i ) is inversely related to market depth. There are three stocks with bad fits (namely APOL, AZO and CME) and we note that they also have wide spreads and low values of depth. It is possible that for these stocks other factors, such as the presence of hidden orders and depth beyond the best price levels the order book may dominate the instantaneous price impact. The intercept ˆ α L,i is highly statistically significant (being an estimate of parameter c ) and ˆ α M,i , which is included to absorb the means, is mostly insignificant. Since the residuals of these regressions appear to be autocorrelated, the t-statistics and confidence intervals in Table 3 are computed with Newey-West standard errors. Coinciding with our intuition for (1), estimates ˆ λ are very close to 1 across stocks and the hypothesis { λ = 1 } cannot be rejected for 35 out of 50 stocks. The restricted model (with λ = 1) also demonstrates a good quality of fit, making this a good approximation. However, the coefficient ˆ c is generally different from c = 1 2 in (1). Lower values of ˆ c mean that mid-prices are (on average) more resilient to the incoming orders than indicated by AD i (which is only a rough measure of market depth). In summary, λ = 1 appears to be a good approximation for most of the stocks and only the constant c needs to be calibrated to the data. The general case of regression (5) is illustrated on Figure 4 by a scatter plot for a representative stock.

Figure 4: Log-log scatter plot of the price impact coefficient estimate ˆ β i against average market depth AD i for the Schlumberger stock (SLB).

![Image](images/image_000007_58569f548de1a0b7e076ead75da21508e615a693141a25850fb4d737c1875f51.png)

Table 3. Relation between the price impact coefficient and market depth.

| Ticker   | Parameter estimates   | Parameter estimates   | Parameter estimates   | Parameter estimates   | 5% confidence intervals   | 5% confidence intervals   | 5% confidence intervals   | 5% confidence intervals   | Fit measures          | Fit measures            |
|----------|-----------------------|-----------------------|-----------------------|-----------------------|---------------------------|---------------------------|---------------------------|---------------------------|-----------------------|-------------------------|
| Ticker   | ˆ c                   | ˆ λ                   | t (ˆ c )              | t ( ˆ λ )             | ˆ c l                     | ˆ c u                     | ˆ λ l                     | ˆ λ u R 2                 | corr [ ˆ β, ˆ ˆ β ] 2 | corr [ ˆ β, ˆ ˆ β ∗ ] 2 |
| AMD      | 0.23                  | 0.94                  | 27.74                 | 23.11                 | 0.22                      | 0.25                      | 0.86                      | 1.02 78%                  | 86%                   | 86%                     |
| APOL     | 0.27                  | 0.36                  | 4.43                  | 1.05                  | 0.15                      | 0.39                      | -0.32                     | 2%                        | 30%                   | 31%                     |
| AXP      | 0.14                  | 0.83                  | 13.95                 | 26.48                 | 0.12                      | 0.16                      | 1.04 0.77 0.89            | 84%                       | 76%                   | 76%                     |
| AZO      | 0.39                  | 0.67                  | 5.48                  | 5.10                  | 0.25                      | 0.41                      | 0.92                      | 13%                       | 17%                   | 16%                     |
| BAC      | 0.27                  | 0.96                  | 25.27                 | 19.74                 | 0.25                      | 0.53 0.29                 | 0.90                      | 1.03 76%                  | 87%                   | 87%                     |
| BDX      | 0.38                  | 1.04                  | 22.83                 | 18.64                 | 0.35                      | 0.41                      | 0.93                      | 1.15 71%                  | 68%                   | 68%                     |
| BK       | 0.21                  | 0.92                  | 17.52                 | 54.54                 | 0.19                      | 0.24                      | 0.88                      | 0.95 93%                  | 91%                   | 90%                     |
| BSX      | 0.35                  | 0.98                  | 14.98                 | 24.55                 | 0.31                      | 0.40                      | 0.90                      | 1.05 73%                  | 81%                   | 81%                     |
| BTU      | 0.42                  | 1.12                  | 40.90                 | 36.77                 | 0.40                      | 0.44                      | 1.06                      | 1.18 87%                  | 83%                   | 83%                     |
| CAT      | 0.29                  | 0.96                  | 21.70                 | 16.87                 | 0.27                      | 0.32                      | 0.85                      | 1.07 87%                  | 83%                   | 83%                     |
| CB       | 0.32                  | 1.02                  | 27.08                 | 49.61                 | 0.30                      | 0.34                      | 0.98                      | 1.06 92%                  | 89%                   | 89%                     |
| CCL      | 0.26                  | 0.96                  | 24.36                 | 37.55                 | 0.24                      | 0.29                      | 0.91                      | 1.01 87%                  | 83%                   | 83%                     |
| CINF     | 0.31                  | 0.97                  | 20.05                 | 47.39                 | 0.28                      | 0.34                      | 0.93                      | 1.01 92%                  | 88%                   | 88%                     |
| CME      | 1.27                  | 0.50                  | 2.55                  | 1.99                  | 0.29                      | 2.24                      | 0.01                      | 0.99 2%                   | 4%                    | 3%                      |
| COH      | 0.37                  | 1.05                  | 15.29                 | 36.65                 | 0.32                      | 0.43                      | 0.98                      | 1.12 77%                  | 75%                   | 75%                     |
| COP      | 0.13                  | 0.80                  | 8.52                  | 15.95                 | 0.10                      | 0.16                      | 0.70                      | 0.89 75%                  | 66%                   | 66%                     |
| CVH      | 0.32                  | 1.03                  | 26.50                 | 37.51                 | 0.29                      | 0.34                      | 0.98                      | 1.08 89%                  | 89%                   | 89%                     |
| DNR      | 0.23                  | 0.96                  | 32.44                 | 40.90                 | 0.22                      | 0.24                      | 0.92                      | 1.01 91%                  | 89%                   | 89%                     |
| DVN      | 0.26                  | 0.91                  | 13.50                 | 16.66                 | 0.22                      | 0.30                      | 0.80                      | 1.02 45%                  | 56%                   | 56%                     |
| EFX      | 0.30                  | 0.99                  | 20.16                 | 26.13                 | 0.27                      | 0.33                      | 0.92                      | 1.07 84%                  | 79%                   | 79%                     |
| ETN      | 0.45                  | 1.07                  | 11.51                 | 17.34                 | 0.38                      | 0.53                      | 0.95                      | 1.19 60%                  | 56%                   | 56%                     |
| FISV     | 0.34                  | 1.01                  | 23.35                 | 30.70                 | 0.31                      | 0.36                      | 0.94                      | 1.07 84%                  | 77%                   | 77%                     |
| HAS      | 0.32                  | 1.00                  | 26.36                 | 46.00                 | 0.30                      | 0.34                      | 0.96                      | 1.05 89%                  | 83%                   | 83%                     |
| HCP      | 0.19                  | 0.89                  | 22.93                 | 51.27                 | 0.17                      | 0.21                      | 0.86                      | 0.93 94%                  | 90%                   | 90%                     |
| HOT      | 0.44                  | 1.12                  | 19.53                 | 26.59                 | 0.40                      | 0.48                      | 1.04                      | 1.20 82%                  | 80%                   | 79%                     |
| KSS      | 0.39                  | 1.05                  | 24.40                 | 33.17                 | 0.36                      | 0.42                      | 0.99                      | 1.11 85%                  | 78%                   | 78%                     |
| LLL      | 0.43                  | 1.01                  | 13.21                 | 14.45                 | 0.37                      | 0.50                      | 0.87                      | 1.14 51%                  | 58%                   | 58%                     |
| LMT      | 0.50                  | 1.14                  | 7.31                  | 13.49                 | 0.37                      | 0.64                      | 0.98                      | 1.31 60%                  | 52%                   | 52%                     |
| M        | 0.19                  | 0.90                  | 37.41                 | 57.39                 | 0.18                      | 0.20                      | 0.87                      | 0.93 94%                  | 92%                   | 92%                     |
| MAR      | 0.28                  | 0.98                  | 22.58                 | 50.20                 | 0.25                      | 0.30                      | 0.94                      | 1.02 92%                  | 88%                   | 88%                     |
| MFE      | 0.31                  | 1.01                  | 20.28                 | 46.20                 | 0.28                      | 0.34                      | 0.96                      | 1.05 91%                  | 86%                   | 86%                     |
| MHP      | 0.27                  | 0.94                  | 19.60                 | 33.62                 | 0.24                      | 0.30                      | 0.89                      | 82%                       | 74%                   | 74%                     |
| MHS      | 0.53                  | 1.16                  | 17.03                 | 34.25                 | 0.47                      | 0.59                      | 1.10                      | 1.00 1.23 85%             | 81%                   | 80%                     |
| MRK      | 0.13                  | 0.81                  | 18.07                 | 32.20                 | 0.11                      | 0.14                      | 0.76                      | 0.86 87%                  | 81%                   | 81%                     |
| MRO      | 0.23                  | 0.94                  | 35.54                 | 49.68                 | 0.21                      | 0.24                      | 0.91                      | 0.98 94%                  | 93%                   | 93%                     |
| MWV      | 0.32                  | 1.05                  | 28.07                 | 37.81                 | 0.30                      | 0.34                      | 1.00                      | 1.10 90%                  | 85%                   | 85%                     |
| NEM      | 0.26                  | 0.98                  | 18.79                 | 25.97                 | 0.23                      | 0.28                      | 0.91                      | 1.05 81%                  | 77%                   | 77%                     |
| OMC      | 0.30                  | 0.96                  | 29.47                 | 17.76                 | 0.28                      | 0.32                      | 0.85                      | 1.06 83%                  | 85%                   | 85%                     |
| PCS      | 0.30                  | 1.02                  | 21.27                 | 18.73                 | 0.27                      | 0.33                      | 0.90                      | 1.14 53%                  | 82%                   | 82%                     |
| PHM      | 0.28                  | 0.98                  | 36.43                 | 35.12                 | 0.26                      | 0.29                      | 0.93                      | 1.04 86%                  | 90%                   | 90%                     |
| PKI      | 0.30                  | 1.07                  |                       |                       | 0.28                      | 0.32                      | 1.00                      | 1.13                      | 88%                   | 87%                     |
| R        | 0.37                  | 1.02                  | 26.59 18.51           | 38.35 15.76           | 0.33                      | 0.41                      | 0.90                      | 82%                       | 58%                   | 58%                     |
| RAI      | 0.35                  | 1.03                  | 24.94                 | 40.46                 | 0.32                      | 0.38                      | 0.98                      | 1.15 57% 1.08 86%         | 76%                   | 76%                     |
| SLB      | 0.35                  | 1.06                  | 18.98                 | 40.60                 | 0.31                      | 0.38                      | 1.01                      | 91%                       | 88%                   | 88%                     |
|          |                       |                       |                       |                       |                           |                           |                           | 1.12                      |                       |                         |
| TE       | 0.21                  | 1.00                  | 16.18                 | 24.28                 | 0.18                      | 0.24                      | 0.92                      | 1.09 70%                  | 86%                   | 86%                     |
| WHR      | 0.78                  | 1.18                  | 9.24                  | 11.54                 | 0.61                      | 0.94                      | 0.98                      | 1.38 44%                  |                       |                         |
| WIN      | 5.81                  | 1.60                  | 16.09                 | 11.70                 | 5.11                      | 6.52                      | 1.33                      | 1.87 28%                  | 43%                   | 42% 71%                 |
| WPI      | 0.27                  | 0.92                  | 19.33                 | 28.99                 | 0.24                      | 0.30                      | 0.86                      | 0.98 78%                  | 71% 76%               | 76%                     |
| XTO      | 0.31                  | 1.04                  | 30.85                 | 39.51                 | 0.29                      | 0.33                      | 0.98                      | 1.09 89%                  | 91%                   | 91%                     |
| Grand    | 0.45                  | 0.98                  | 20.74                 | 29.53                 | 0.38                      | 0.52                      | 0.88                      | 1.08 74%                  | 75%                   | 75%                     |
| mean     |                       |                       |                       |                       |                           |                           |                           |                           |                       |                         |

Table 3 presents the results of regressions:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0015" status="decoded_unverified" source-page="13" -->
$$
\log \hat { \beta } _ { i } & = \alpha \hat { L } _ { , i } - \hat { \lambda } \log A D _ { i } + \hat { \epsilon } _ { L , i } , \\ \hat { \beta } _ { i } & = \alpha \hat { M } _ { , i } + \frac { \hat { c } } { A D _ { i } ^ { \lambda } } + \hat { \epsilon } _ { M , i } ,
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0015](images/formula_0015.png)
```text
PDF text layer: log ˆ β i = ˆ α L,i -ˆ λ log AD i +ˆ ϵ L,i , ˆ β i = ˆ α M,i + ˆ c AD ˆ λ i +ˆ ϵ M,i ,
```
*Formula quality: `decoded_unverified`; source PDF page 13. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

where ˆ β i is the price impact coefficient for the i -th half-hour subsample and AD i is the average market depth for that subsample. These regressions were estimated for each of the 50 stocks, using 273 estimates of ˆ β i for that stock, obtained from (4). The second regression uses estimates ˆ λ obtained from the first regression. The t-statistics and the confidence intervals were computed using Newey-West standard errors. Confidence intervals are built with normal critical values. The last three columns provide three alternative fit measures - the R 2 of the linear regression (5), the squared correlation between ˆ β i and fitted values ˆ ˆ β i = ˆ c AD ˆ λ i and the squared correlation between ˆ β i and ˆ ˆ β ∗ i = ˆ c AD i .

## 3.3 Intraday patterns

The link that we established between the price impact and the market depth has an important implication. Since the market depth follows a predictable pattern of intraday seasonality ([1], [31]), the price impact coefficient must also have a predictable intraday pattern. To demonstrate it, we averaged ˆ β i for each stock and each half-hour interval across days, resulting in the intraday seasonality pattern for that stock, normalized these values by the average ˆ β i of that stock and averaged the normalized seasonality patterns across stocks. The same procedure was repeated for AD i and the results are shown on Figure 5.

Figure 5: Intraday patterns in the price impact coefficient ˆ β i and the average depth AD i .

![Image](images/image_000008_fb9cccdf89d455eb797a2e42c0d6f1d995cc89ccf5bbf3029b076ed56af750da.png)

Near the market open, depth is two times lower than it is on average, indicating that the order book is relatively shallow. In a shallow market, the incoming orders can easily affect the mid-price and the price impact coefficient is two times higher near the market open than on average. Moreover, price impact is five times higher at the market open compared to the market close.

The intraday pattern in price impact can be used to explain the intraday patterns in price volatility, observed by many researchers ([1], [4], [21], [33]). Similarly to the price impact coefficient and the market depth, we computed the intraday patterns in variances of ∆ P k and OFI k , using half-hour subsamples (indexed by i ). Taking the variance on both sides of equation (2) demonstrates the link between var [∆ P k ] i , var [ OFI k ] i and β i :

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0016" status="verified_source" source-page="14" -->
$$
var[\Delta P_{k}]_i=\beta^2_ivar[OFI_{k}]_i+var[\epsilon_{k}]_i
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0016](images/formula_0016.png)
*Formula quality: `verified_source`; source PDF page 14. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:691 (score=1.0).*
<!-- formula-end -->

The average patterns are plotted on Figure 6. Notice that the price volatility has a sharp peak near the market open, while the volatility of order flow imbalance has a peak near the market close. This peak is, however, offset by a low price impact, which gradually declines throughout the day. For the i -th half-hour interval, the equation (7) implies that var [∆ P k ] i ≈ ˆ β 2 i var [ OFI k ] i which is demonstrated on Figure 6 4 .

4 ˆ β 2 i var [ OFI k ] i was computed from the average patterns of ˆ β i and var [ OFI k ] i

Figure 6: Intraday seasonality in variances var [∆ P k ] i , var [ OFI k ] i , the price impact coefficient ˆ β i and the expression β 2 i var [ OFI k ] i .

![Image](images/image_000009_da2d9398801d06649c566b37a9a93ff902ce2cb5babd72ec76ddefbe6693e2a6.png)

The intraday pattern in price variance was explained by Madhavan et al. [33] in terms of a structural model. They argued that the volatility is higher in the morning because of the higher inflow of both public and private information. Similarly, Hasbrouck [21] argued that the peak of price volatility at market open is mostly due to higher intensity of public information. Both studies agree that the impact of trades is larger in the morning. Our model contributes to this discussion by explaining the peak of price volatility using tangible quantities, rather than unobservable parameters. We also argue that the price impact of trades and the information asymmetry may be, in fact, two sides of the same coin.

First, we associate the higher volatility of order flow imbalance at market the open and close with a higher rate of trading, that is, higher inflow of public and private information. Second, if the bid-ask spread is small (it is mostly equal to 1 cent in our data), limit order traders may avoid being 'picked off' only by lowering the number of submitted orders, reducing the depth. Therefore, if limit order traders are aware of information asymmetry in the morning, the low depth may simply indicate this asymmetry. In our model, low depth also implies a higher price impact, making the information advantages harder to realize at the market open.

## 4 Price impact of trades

## 4.1 Trade imbalance vs order flow imbalance

The previous section discussed the linear relation between price changes and OFI k - our measure of supply/demand imbalance. However, little has been said about trade imbalances, which are widely used in the academic literature [10, 20, 22, 24, 29, 38] and in practice [43]. The aim of this section is to compare the price impact of trades and order flow imbalance and show that the (nonlinear) price impact of trade volume may be derived from our linear model for the price impact of order flow.

For convenience we will call 'buy trade' a transaction initiated by a market buy order and 'sell trade' a transaction initiated by a market sell order. We define the trade imbalance during a time interval [ t k -1 , t k ] as the difference between volumes of buy and sell trades during that interval:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0017" status="verified_source" source-page="16" -->
$$
TI_{k} =\sum_{n=N(t_{k-1})+1}^{N(t_{k})}{b_n}-\sum_{n=N(t_{k-1})+1}^{N(t_{k})}{s_n},
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0017](images/formula_0017.png)
*Formula quality: `verified_source`; source PDF page 16. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:721 (score=1.0).*
<!-- formula-end -->

Here, b n is the size of a buyer-initiated trade that occurs at the n -th quote; b n = 0 if no buy trade occurs at that quote. Similarly, s n is the size of a sell trade that occurs at the n -th quote or zero. The procedure that matches trades with quotes and classifies them as buys or sells is described in the Appendix.

To compare the explanatory power of trade and order flow imbalances with respect to price changes, we perform the following regressions:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0018" status="verified_source" source-page="16" -->
$$
\begin{aligned}\Delta P_{k}=\hat{\alpha}_i+\hat{\beta}_iOFI_{k}+\hat{\epsilon}_{k}\end{aligned}
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0018](images/formula_0018.png)
*Formula quality: `verified_source`; source PDF page 16. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:726 (score=1.0).*
<!-- formula-end -->

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0019" status="verified_source" source-page="16" -->
$$
\begin{aligned}\Delta P_{k}=\hat{\alpha}_{T,i}+\hat{\beta}_{T,i}TI_k+\hat{\epsilon}_{T,k}\end{aligned}
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0019](images/formula_0019.png)
*Formula quality: `verified_source`; source PDF page 16. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:729 (score=1.0).*
<!-- formula-end -->

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0020" status="verified_source" source-page="16" -->
$$
\begin{aligned}\Delta P_{k}=\hat{\alpha}_{D,i}+\hat{\theta}_{O,i}OFI_k+\hat{\theta}_{T,i}TI_k+\hat{\epsilon}_{D,k}\end{aligned}
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0020](images/formula_0020.png)
*Formula quality: `verified_source`; source PDF page 16. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:732 (score=1.0).*
<!-- formula-end -->

The regressions are estimated separately for every half-hour subsample of data (indexed by i ). If the effect of trades is included in the order flow imbalance, the coefficients ˆ θ T,i in (8c) must be indistinguishable from zero. We note that regressions (8a-8c) contain only the linear terms, because we found no evidence of non-linear price impacts in our data (for neither OFI k nor TI k ). The average results of these regressions are presented in Panel A of Table 4. Clearly, when OFI k and TI k are taken individually, each of them has a statistically significant influence on price changes. Comparing the two we observe that OFI k explains price changes better than TI k - the average R 2 for order flow imbalance is 65% compared to 32% for the trade imbalance. When two variables are used together to explain price changes, the dependence on trade imbalance becomes questionable. The average t-statistic of TI k decreases by a factor of four and the coefficients ˆ θ T,i are statistically significant in only 31% of subsamples. However, the dependence on OFI k remains convincingly strong.

Our findings show that:

1. The order flow imbalance OFI k explains price movements better than the imbalance of trades.
2. The effect of trade imbalance is adequately included in OFI k , a more general measure of supply/demand imbalance.

Table 4. Comparison of order flow imbalance and trade imbalance.

̸

|                            | Panel A: Detailed results for changes in mid prices   | Panel A: Detailed results for changes in mid prices   | Panel A: Detailed results for changes in mid prices   | Panel A: Detailed results for changes in mid prices   | Panel A: Detailed results for changes in mid prices   | Panel A: Detailed results for changes in mid prices   | Panel A: Detailed results for changes in mid prices   | Panel A: Detailed results for changes in mid prices   | Panel A: Detailed results for changes in mid prices   | Panel A: Detailed results for changes in mid prices   | Panel A: Detailed results for changes in mid prices   | Panel A: Detailed results for changes in mid prices   | Panel A: Detailed results for changes in mid prices   | Panel A: Detailed results for changes in mid prices   |
|----------------------------|-------------------------------------------------------|-------------------------------------------------------|-------------------------------------------------------|-------------------------------------------------------|-------------------------------------------------------|-------------------------------------------------------|-------------------------------------------------------|-------------------------------------------------------|-------------------------------------------------------|-------------------------------------------------------|-------------------------------------------------------|-------------------------------------------------------|-------------------------------------------------------|-------------------------------------------------------|
| Ticker                     | Order flow imbalance                                  | Order flow imbalance                                  | Order flow imbalance                                  | Order flow imbalance                                  | Trade imbalance                                       | Trade imbalance                                       | Trade imbalance                                       | Both covariates                                       | Both covariates                                       | Both covariates                                       | Both covariates                                       | Both covariates                                       | Both covariates                                       | Both covariates                                       |
|                            | R 2                                                   | t ( ˆ β )                                             | { β = 0 }                                             | F                                                     | R 2                                                   | t ( ˆ β T )                                           | β T = 0 }                                             | F                                                     | R 2 t                                                 | ( ˆ θ O )                                             | t ( ˆ θ T )                                           | { θ O = 0 }                                           | { θ T = 0 }                                           | F                                                     |
| AMD                        | 64%                                                   | 9.96                                                  | 98%                                                   | 382                                                   | 39%                                                   | 4.15                                                  | 86%                                                   | 140                                                   | 67%                                                   | 6.49                                                  | 1.26                                                  | 93%                                                   | 34%                                                   | 214                                                   |
| APOL                       | 63%                                                   | 10.32                                                 | 91%                                                   | 396                                                   | 30%                                                   | 4.14                                                  | 84%                                                   | 83                                                    | 66%                                                   | 8.00                                                  | 1.09                                                  | 89%                                                   | 26%                                                   | 211                                                   |
| AXP                        | 69%                                                   | 13.87                                                 | 100%                                                  | 449                                                   | 34%                                                   | 4.72                                                  | 83%                                                   | 101                                                   | 71%                                                   | 10.05                                                 | 1.50                                                  | 100%                                                  | 44%                                                   | 241                                                   |
| AZO                        | 47%                                                   | 6.39                                                  | 97%                                                   | 179                                                   | 30%                                                   | 4.09                                                  | 90%                                                   | 87                                                    | 54%                                                   | 5.02                                                  | 2.34                                                  | 96%                                                   | 68%                                                   | 118                                                   |
| BAC                        | 79%                                                   | 18.36                                                 | 100%                                                  | 774                                                   | 45%                                                   | 6.31                                                  | 96%                                                   | 157                                                   | 80%                                                   | 12.55                                                 | 0.72                                                  | 99%                                                   | 19%                                                   | 397                                                   |
| BDX                        | 63%                                                   | 10.08                                                 | 100%                                                  | 362                                                   | 28%                                                   | 4.02                                                  | 82%                                                   | 79                                                    | 65%                                                   | 7.88                                                  | 1.23                                                  | 97%                                                   | 34%                                                   | 195                                                   |
| BK                         | 74%                                                   | 14.97                                                 | 100%                                                  | 610                                                   | 36%                                                   | 4.58                                                  | 81%                                                   | 117                                                   | 75%                                                   | 10.68                                                 | 0.68                                                  | 99%                                                   | 17%                                                   | 313                                                   |
| BSX                        | 58%                                                   | 6.12                                                  | 81%                                                   | 338                                                   | 31%                                                   | 2.57                                                  | 54%                                                   | 106                                                   | 62%                                                   | 4.51                                                  | 0.57                                                  | 73%                                                   | 12%                                                   | 189                                                   |
| BTU                        | 72%                                                   | 14.51                                                 | 100%                                                  | 527                                                   | 35%                                                   | 5.21                                                  | 88%                                                   | 103                                                   | 74%                                                   | 10.90                                                 | 1.31                                                  | 99%                                                   | 32%                                                   | 277                                                   |
| CAT                        | 71%                                                   | 14.85                                                 | 99%                                                   | 498                                                   | 33%                                                   | 5.01                                                  | 86%                                                   | 94                                                    | 72%                                                   | 11.27                                                 | 1.28                                                  | 99%                                                   | 38%                                                   | 262                                                   |
| CB                         | 64%                                                   | 11.97                                                 | 100%                                                  | 378                                                   | 33%                                                   | 4.66                                                  | 88%                                                   | 102                                                   | 66%                                                   | 8.42                                                  | 1.34                                                  | 99%                                                   | 37%                                                   | 202                                                   |
| CCL                        | 70%                                                   | 13.88                                                 | 99%                                                   | 478                                                   | 32%                                                   | 4.55                                                  | 85%                                                   | 93                                                    | 71%                                                   | 10.50                                                 | 0.98                                                  | 99%                                                   | 26%                                                   | 247                                                   |
| CINF                       | 70%                                                   | 10.73                                                 | 98%                                                   | 552                                                   | 39%                                                   | 4.26                                                  | 87%                                                   | 141                                                   | 72%                                                   | 7.17                                                  | 1.01                                                  | 96%                                                   | 27%                                                   | 297                                                   |
| CME                        | 35%                                                   | 4.98                                                  | 94%                                                   | 112                                                   | 24%                                                   | 3.39                                                  | 75%                                                   | 63                                                    | 44%                                                   | 4.10                                                  | 2.18                                                  | 92%                                                   | 59%                                                   | 78                                                    |
| COH                        | 69%                                                   | 12.75                                                 | 100%                                                  | 457                                                   | 29%                                                   | 3.91                                                  | 82%                                                   | 80                                                    | 70%                                                   | 10.06                                                 | 0.87                                                  | 100%                                                  | 22%                                                   | 238                                                   |
| COP                        | 68%                                                   | 12.50                                                 | 100%                                                  | 450                                                   | 35%                                                   | 4.92                                                  | 84%                                                   | 107                                                   | 70%                                                   | 9.19                                                  | 1.42                                                  | 100%                                                  | 40%                                                   | 240                                                   |
| CVH                        | 65%                                                   | 10.83                                                 | 99%                                                   | 418                                                   | 35%                                                   | 4.10                                                  | 84%                                                   | 114                                                   | 67%                                                   | 7.30                                                  | 1.01                                                  | 97%                                                   | 25%                                                   | 222                                                   |
| DNR                        | 69%                                                   | 12.76                                                 | 99%                                                   | 471                                                   | 32%                                                   | 3.98                                                  | 81%                                                   | 101                                                   | 70%                                                   | 9.29                                                  | 1.01                                                  | 97%                                                   | 24%                                                   | 246                                                   |
| DVN                        | 65%                                                   | 11.48                                                 |                                                       |                                                       | 33%                                                   | 4.83                                                  | 88%                                                   | 96                                                    | 68%                                                   | 8.58                                                  | 1.70                                                  | 93%                                                   | 48%                                                   | 226                                                   |
| EFX                        | 56%                                                   | 8.71                                                  | 97% 98%                                               | 414 289                                               | 31%                                                   | 3.72                                                  | 80%                                                   | 101                                                   | 60%                                                   | 6.21                                                  | 1.64                                                  | 96%                                                   | 43%                                                   | 167                                                   |
| ETN FISV                   | 65% 63%                                               | 10.51 10.42                                           | 98% 100%                                              | 389 380                                               | 25% 28%                                               | 3.59 3.79                                             | 71% 81%                                               | 69 79                                                 | 67% 65%                                               | 8.66 8.12                                             | 1.04 0.88                                             | 98% 100%                                              | 29% 25%                                               | 209 201                                               |
| HAS                        | 67%                                                   | 11.45                                                 | 100%                                                  | 427                                                   | 32%                                                   | 4.04                                                  | 84%                                                   | 97                                                    | 68%                                                   | 8.53                                                  | 0.89                                                  | 100%                                                  | 24%                                                   | 223                                                   |
| HCP                        | 67%                                                   | 13.60                                                 | 100%                                                  | 417                                                   | 31%                                                   | 4.43                                                  | 82%                                                   | 91                                                    | 68%                                                   | 10.01                                                 | 1.05                                                  | 100%                                                  | 32%                                                   | 217                                                   |
| HOT                        | 68%                                                   | 12.64                                                 | 99%                                                   | 438                                                   | 27%                                                   | 3.86                                                  | 77%                                                   | 74                                                    | 70%                                                   | 9.94                                                  | 1.17                                                  | 99%                                                   | 29%                                                   | 231                                                   |
| KSS                        | 71%                                                   | 13.82                                                 | 98%                                                   | 525                                                   | 31%                                                   | 4.43                                                  | 81%                                                   | 91                                                    | 72%                                                   | 10.83                                                 | 0.94                                                  | 97%                                                   | 25%                                                   | 274                                                   |
| LLL                        | 67%                                                   | 11.76                                                 | 96%                                                   | 485                                                   | 36%                                                   | 5.07                                                  | 90%                                                   | 117                                                   | 70%                                                   | 8.58                                                  | 1.63                                                  | 94%                                                   | 44%                                                   | 270                                                   |
| LMT                        |                                                       |                                                       |                                                       | 516                                                   |                                                       |                                                       |                                                       |                                                       |                                                       | 10.19                                                 | 1.50                                                  | 99%                                                   | 40%                                                   |                                                       |
| M                          | 72%                                                   | 13.58                                                 | 100%                                                  | 640                                                   | 35%                                                   | 4.89                                                  | 90%                                                   | 105                                                   | 73%                                                   | 11.38                                                 | 0.97                                                  |                                                       |                                                       | 277                                                   |
|                            | 75%                                                   | 15.82                                                 | 100%                                                  |                                                       | 35%                                                   | 4.41                                                  | 84%                                                   | 108                                                   | 76% 72%                                               | 10.45                                                 |                                                       | 100%                                                  | 26%                                                   | 330                                                   |
|                            |                                                       | 14.61                                                 | 100%                                                  | 498                                                   | 34%                                                   | 4.77                                                  | 89%                                                   | 105                                                   | 69%                                                   | 9.06                                                  | 1.05                                                  | 100%                                                  | 27% 18%                                               | 258                                                   |
| MAR MFE                    | 71% 68%                                               | 12.72                                                 | 100% 99%                                              | 463 489                                               | 31% 31%                                               | 4.17 3.85                                             | 82% 84%                                               | 93 96                                                 | 70%                                                   |                                                       | 0.73                                                  | 99% 98%                                               | 19%                                                   | 239                                                   |
| MHP MHS                    | 68% 66%                                               | 11.62 11.70                                           | 99%                                                   | 414                                                   | 28%                                                   | 4.03                                                  | 77%                                                   | 80                                                    | 68%                                                   | 8.92 9.10                                             | 0.77 1.11                                             | 99%                                                   | 27%                                                   | 257 218                                               |
| MRK                        | 69%                                                   | 12.53                                                 | 100%                                                  | 451                                                   | 31%                                                   | 4.08                                                  | 82%                                                   | 93                                                    | 70%                                                   | 9.20                                                  | 0.76                                                  | 100%                                                  | 20%                                                   | 235                                                   |
| MRO                        | 69%                                                   | 13.67                                                 | 100%                                                  | 465                                                   | 35%                                                   | 4.66                                                  | 89%                                                   | 104                                                   | 70%                                                   | 9.73                                                  | 0.91                                                  | 100%                                                  | 24%                                                   | 241                                                   |
| MWV                        | 68%                                                   | 11.79                                                 | 100%                                                  | 452                                                   | 34%                                                   | 4.37                                                  | 86%                                                   | 102                                                   | 69%                                                   | 8.63                                                  | 0.80                                                  | 100%                                                  | 24%                                                   | 237                                                   |
| NEM                        | 71%                                                   | 13.81                                                 | 100%                                                  | 490                                                   | 34%                                                   | 4.99                                                  | 81%                                                   | 100                                                   | 72%                                                   | 10.24                                                 | 1.53                                                  | 99%                                                   | 43% 24%                                               | 260 216                                               |
| OMC PCS                    | 65% 53%                                               | 11.88 5.21                                            | 99% 79%                                               | 411 297                                               | 30% 35%                                               | 4.14 2.68                                             | 85%                                                   | 88 169                                                | 67% 58%                                               | 8.99 3.44                                             | 0.96 0.86                                             | 99% 71%                                               | 20%                                                   | 195                                                   |
| PHM                        | 66%                                                   | 10.33                                                 | 98%                                                   |                                                       | 35%                                                   | 3.87                                                  | 59% 84%                                               | 115                                                   | 68%                                                   | 7.28                                                  |                                                       | 93%                                                   | 29%                                                   | 224                                                   |
| PKI                        | 53%                                                   | 7.25                                                  | 94%                                                   | 416 263                                               | 28%                                                   | 3.03                                                  | 70%                                                   | 89                                                    | 57%                                                   | 5.39                                                  | 0.95 1.24                                             | 88%                                                   | 32%                                                   | 148                                                   |
| R                          | 63%                                                   | 10.14                                                 | 98%                                                   | 352                                                   | 27%                                                   | 3.92                                                  | 86%                                                   | 71                                                    | 65%                                                   | 8.07                                                  | 1.20                                                  | 97%                                                   | 30%                                                   | 188                                                   |
| RAI                        | 66%                                                   | 10.40                                                 | 100%                                                  | 422                                                   | 36%                                                   | 4.67                                                  | 89%                                                   | 111                                                   | 68%                                                   | 7.52                                                  | 1.24                                                  | 99%                                                   | 31% 36%                                               | 224                                                   |
| SLB                        | 76%                                                   | 16.76                                                 | 100%                                                  | 644                                                   | 32%                                                   | 4.54                                                  |                                                       |                                                       | 77%                                                   |                                                       | 1.11                                                  | 100%                                                  |                                                       | 336                                                   |
|                            |                                                       |                                                       |                                                       |                                                       |                                                       |                                                       | 79%                                                   | 94                                                    |                                                       | 13.02                                                 |                                                       |                                                       |                                                       |                                                       |
| TE                         | 54%                                                   | 6.66                                                  | 86% 99%                                               | 301                                                   | 37%                                                   | 3.27                                                  | 67%                                                   | 175                                                   | 60%                                                   | 4.34                                                  | 1.32 1.34                                             | 79% 99%                                               | 29%                                                   | 200 201                                               |
| TWC WHR                    | 64% 65%                                               | 11.80 10.26                                           | 97%                                                   | 377 394                                               | 31% 29%                                               | 4.26 4.29                                             | 77% 88%                                               | 93 85                                                 | 66% 67%                                               | 8.46                                                  | 1.43                                                  | 96%                                                   | 39%                                                   | 217                                                   |
|                            |                                                       | 3.12                                                  | 60%                                                   | 243                                                   | 41%                                                   | 2.68                                                  | 54%                                                   | 249                                                   | 58%                                                   | 8.17 1.78                                             |                                                       | 42%                                                   | 37% 29% 30% 27%                                       | 206                                                   |
| WIN WPI                    | 44% 66%                                               | 10.47                                                 | 98%                                                   | 437                                                   | 32%                                                   | 3.91                                                  | 83%                                                   | 100                                                   | 68%                                                   | 7.82                                                  | 1.39 1.05                                             | 97%                                                   |                                                       | 232                                                   |
| XTO                        | 65%                                                   | 13.28                                                 | 100%                                                  | 399                                                   | 21%                                                   | 3.05                                                  |                                                       | 54                                                    | 66%                                                   | 10.72                                                 |                                                       | 100%                                                  |                                                       | 209                                                   |
|                            |                                                       |                                                       |                                                       |                                                       |                                                       |                                                       | 63%                                                   |                                                       |                                                       |                                                       | 1.05                                                  |                                                       |                                                       | 231                                                   |
| Grand                      | 65%                                                   | 11.47                                                 | 97%                                                   | 429                                                   | 32%                                                   |                                                       | 81%                                                   | 103                                                   |                                                       |                                                       |                                                       | 95%                                                   | 31%                                                   |                                                       |
| mean                       |                                                       |                                                       |                                                       |                                                       |                                                       | 4.18 results                                          | changes                                               | in transaction                                        | 67%                                                   | 8.49 prices                                           | 1.16                                                  |                                                       | 54%                                                   | 245                                                   |
| L = 2 trades               | 14%                                                   | 15.74                                                 | Panel 98%                                             | B: 464                                                | Average 1%                                            | 2.69                                                  | 63% 75%                                               | 26 113                                                | 15% 39%                                               | 14.17                                                 | -2.58                                                 | 98%                                                   |                                                       | 379                                                   |
| L = 5 trades L = 10 trades | 38% 51%                                               | 19.42 17.78                                           | 98% 98%                                               | 753 655                                               | 8% 13%                                                | 4.50 4.55                                             | 75%                                                   | 100                                                   | 51%                                                   | 16.85 14.97                                           | -0.20 0.57                                            | 98% 98%                                               | 9% 9%                                                 | 329                                                   |

Table 4 presents the average results of regressions:

∆ P k = ˆ α i + ˆ β i OFI k +ˆ ϵ k ,

∆ P k = ˆ α T,i + ˆ β T,i TI k +ˆ ϵ T,k ,

∆ P k = ˆ α D,i + ˆ θ O,i OFI k + ˆ θ T,i TI k +ˆ ϵ D,k ,

where ∆ P k are the 10-second mid-price changes (Panel A) or changes in trade prices between L trades (Panel B), OFI k are the contemporaneous order flow imbalances and TI k are the contemporaneous trade imbalances. For Panel A, these regressions were estimated using 273 half-hour subsamples (indexed by i ) for each stock and their outputs were averaged across subsamples. Each subsample typically contains about 180 observations (indexed by k ). For Panel B, data was pooled across half-hour subsamples, resulting in 13 subsamples for each stock. The t-statistics were computed using White's standard errors. For each of three regressions, Table 4 reports the average R 2 , the average tstatistic of the coefficient(s), the percentage of samples where the coefficient(s) passed the z-test at the 5% significance level and the F-statistic of the regression. The outputs for Panel B were averaged across stocks.

̸

̸

̸

As a robustness check, we repeated regressions (8a-8c) with differences between transaction prices P t k instead of differences in mid-prices P k . This time price differences were computed in trade time as ∆ L P t k = P t k -P t k -L for L trades. The average results across five stocks, picked at random 5 are presented in Panel B of Table 4. Our findings for transaction prices are essentially the same as for mid prices OFI k explains price changes better than TI k . Moreover, the effect of trades on prices seems to be captured by the order flow imbalance. The variable TI k becomes statistically insignificant when used together with OFI k in the regression and the increase in R 2 from adding TI k as an extra regressor is not economically significant.

Interestingly, we found that the relation between ∆ L P t k and OFI k is concave in some samples, and similarly for ∆ L P t k and TI k . We estimated regressions (8a) and (8b) for transaction price changes with additional quadratic terms OFI k | OFI k | (respectively, TI k | TI k | ) and found that they are significant in nearly half of the samples with t-statistics of -2.8 on average (-2.3 for TI k | TI k | ). Sampling data at special times (trade times) may introduce biases to the right side of the regression. One possible explanation is that traders submit their orders when they expect their impact to be minimal, leading to a concave (sublinear) impact. Supporting this idea of sampling biases, we found that when mid-prices are sampled at trade times, the price impact of OFI k is again concave in some samples. On another hand, when we regressed last trade prices sampled at 1-minute frequency on OFI k , we observed the concave price impact once again. This suggests that using either trade times or trade prices may lead to non-linear price impact. However the quadratic term in our regressions is insignificant in about half of the samples and marginally significant in the the other half of the data.

## 4.2 Does volume move the prices?

The relation between price changes and volume is empirically confirmed by many authors (see [27] for a review). Recently, traded volume became an important metric for order execution algorithms - these algorithms often attempt to match a certain percentage of the total traded volume to reduce the price impact. However, it remains unclear whether the traded volume truly determines the magnitude of price moves and whether it is a good metric for price impact. Casting doubt on this assertion, Jones et al. [26] showed that the relation between the daily volatility and the daily volume is essentially due to the number of trades and not the volume per se (also see [ ? ] for the discussion).

We extend this result in two ways. First, we show that even when prices are driven by order flow imbalance, an apparent (concave) dependence on traded volume may emerge as an artifact due to data aggregation. Second, we empirically confirm that the price-volume relation is an indirect one - it becomes statistically insignificant after accounting for the order flow imbalance.

The volume traded during a time interval [ t k -1 , t k ] is:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0021" status="verified_source" source-page="18" -->
$$
VOL_{k} =\sum_{n=N(t_{k-1})+1}^{N(t_{k})}{b_n}+\sum_{n=N(t_{k-1})+1}^{N(t_{k})}{s_n}=\sum_{n=N(t_{k-1})+1}^{N(t_{k})}{w_n},
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0021](images/formula_0021.png)
*Formula quality: `verified_source`; source PDF page 18. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:910 (score=1.0).*
<!-- formula-end -->

where w n = b n + s n is the size of any trade (either buy or sell) if it occurs at the n -th quote or zero otherwise. Comparing this definition with the definition of OFI k we note that both quantities are sums of random variables. As the aggregation window [ t k -1 , t k ] becomes progressively larger, the behavior of these sums (under certain assumptions) will be governed by the Law of Large Numbers and the Central Limit Theorem. We consider a time interval [0 , T ) and denote by N ( T ) the number of order book events during that time interval. We also denote by OFI ( T ) and V OL ( T ), respectively, the order flow imbalance and the traded volume during [0 , T ). The following proposition shows a link between OFI ( T ) and V OL ( T ) as T grows.

5 The stocks tickers were BDX, CB, MHS, PHM and PKI. We computed price changes for L = 2 , 5 , 10 trades to mitigate the possible issues with trade and quote alignment in the TAQ data and we correspondingly computed order flow imbalances and trade imbalances during the time intervals between 2, 5 or 10 consecutive trades. To ensure that there is an ample amount of data for each regression, we pooled data across days for each stock and each time interval.

## Proposition 1. Assume that

1. Order book events accumulate over time at some average rate Λ : N ( T ) T → Λ , as T →∞
2. { e i } ∞ i =1 are i.i.d. random variables with a finite variance σ 2 ,
3. { w i } ∞ i =1 are i.i.d. random variables with a finite mean µπ , where π is the proportion of order book events that correspond to trades and µ is the mean trade size.

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0022" status="verified_source" source-page="19" -->
$$
{\rm Then}\qquad\frac{\sqrt{\mu\pi}}{\sigma}\frac{OFI(T)}{\sqrt{VOL(T)}}\Rightarrow \xi,~as~ T\rightarrow\infty
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0022](images/formula_0022.png)
*Formula quality: `verified_source`; source PDF page 19. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:925 (score=0.9365).*
<!-- formula-end -->

where ξ ∼ N (0 , 1) is a standard normal random variable and ⇒ denotes convergence in distribution.

Proof: First, we apply the law of large numbers to the traded volume. Assumption (1) ensures that N ( T ) →∞ as T →∞ :

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0023" status="verified_source" source-page="19" -->
$$
\frac{VOL(T)}{N(T)}=\frac{\sum_{i=1}^{N(T)}w_i}{N(T)}\rightarrow \mu\pi, w.p. 1, ~as~ T\rightarrow\infty,
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0023](images/formula_0023.png)
*Formula quality: `verified_source`; source PDF page 19. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:932 (score=1.0).*
<!-- formula-end -->

Second, event contributions e i have a finite variance σ 2 and, under our assumptions, we can apply the classical central limit theorem to the order flow imbalance:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0024" status="verified_source" source-page="19" -->
$$
\frac{OFI(T)}{\sigma\sqrt{N(T)}}\equiv\frac{\sum_{i=1}^{N(T)}{e_i}}{\sigma\sqrt{N(T)}}\Rightarrow \xi, ~as~ T\rightarrow\infty,
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0024](images/formula_0024.png)
*Formula quality: `verified_source`; source PDF page 19. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:936 (score=0.9459).*
<!-- formula-end -->

where ξ ∼ N (0 , 1) is a standard normal random variable. Although the denominator σ √ N ( T ) is random, it goes to infinity by assumption (1) and Anscombe's lemma ensures that we can use such a normalization in the central limit theorem [13, Lemma 2.5.8]. Since the square root function is continuous, the convergence in (10) takes place almost-surely and the limit in (10) is deterministic, we can combine (10) and (11) in the following way:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0025" status="verified_source" source-page="19" -->
$$
\frac{\sqrt{\mu\pi}}{\sigma}\frac{OFI(T)}{\sqrt{VOL(T)}}\equiv
\frac{\frac{\sum_{i=1}^{N(T)}{e_i}}{\sigma\sqrt{N(T)}}}{\sqrt{\frac{\sum_{i=1}^{N(T)}{w_i}}{\mu\pi (N(T))}}}\Rightarrow \xi,~as~ T\rightarrow\infty
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0025](images/formula_0025.png)
*Formula quality: `verified_source`; source PDF page 19. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:942 (score=0.9652).*
<!-- formula-end -->

■

If the time interval [0 , T ) includes a large enough number of order book events and trades, the above limit argument implies a noisy scaling relation between order flow imbalance and the square root of traded volume:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0026" status="verified_source" source-page="19" -->
$$
OFI(T)=\xi\frac{\sigma}{\sqrt{\mu\pi}}\sqrt{VOL(T)},
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0026](images/formula_0026.png)
*Formula quality: `verified_source`; source PDF page 19. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:949 (score=1.0).*
<!-- formula-end -->

where µ, π and σ are constants and ξ ∼ N (0 , 1). Now, assume that it holds not just for the first interval, but for every time interval [ t k -1 , t k ) of large enough length ∆ t , regardless of its index k . Then, (13) can be substituted into our model (2), to yield:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0027" status="verified_source" source-page="19" -->
$$
\Delta P_{k}= \theta_{k}\sqrt{VOL_{k}}+\epsilon_{k},
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0027](images/formula_0027.png)
*Formula quality: `verified_source`; source PDF page 19. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:955 (score=1.0).*
<!-- formula-end -->

where θ k = β i ξ k σ √ µπ is a slope coefficient and ξ k ∼ N (0 , 1) is a noise term due to scaling. Due to the scaling approximation, the slope θ k in (14) is a random normal variable: θ k ∼ N (0 , β 2 i σ 2 µπ ). For every time interval [ t k -1 , t k ) the ratio √ µπ σ OFI k √ V OL k is a different draw from the N (0 , 1) distribution, leading to a different θ k in each case. This additional randomness makes this model considerably less robust than (2) and we do not recommend to use it.

Equation (14) shows that even if prices are driven by the order flow imbalance (i.e. even if ϵ k = 0 ∀ k ), there will be a noisy square-root relation between the price changes and the traded volume. However, if the assumptions of Proposition 1 do not hold (e.g. { e i } ∞ i =1 are strongly dependent or have infinite variance), the price-volume relation may have a different exponent. A variety of exponents 0 &lt; H &lt; 1 have been observed in the relation between prices changes and trade sizes [8], suggesting the following model:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0028" status="verified_source" source-page="20" -->
$$
\Delta P_{k}= \theta_{k}VOL^H_{k}+\epsilon_{k},
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0028](images/formula_0028.png)
*Formula quality: `verified_source`; source PDF page 20. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:982 (score=1.0).*
<!-- formula-end -->

To estimate the exponent H , we put ϵ k = 0 and θ k = ¯ θ i ξ k in (15) and fit a logarithmic regression to every half-hour subsample, indexed by i :

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0029" status="verified_source" source-page="20" -->
$$
\log{|\Delta P_{t_k}|}= \log{\hat{\bar{\theta}}_i}+\hat{H}_i\log{VOL_{k}}+\log{\hat{\xi}_{k}}
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0029](images/formula_0029.png)
*Formula quality: `verified_source`; source PDF page 20. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:986 (score=1.0).*
<!-- formula-end -->

Based on Proposition 1, we expect the price-volume relation to be indirect (i.e. come through OFI k ) and noisy. To empirically confirm this, we compare the following three regressions:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0030" status="verified_source" source-page="20" -->
$$
\begin{aligned}|\Delta P_{k}|=\hat{\alpha}_{O,i}+\hat{\beta}_{O,i}|OFI_{k}|+\hat{\epsilon}_{O,k}\end{aligned}
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0030](images/formula_0030.png)
*Formula quality: `verified_source`; source PDF page 20. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:991 (score=0.9655).*
<!-- formula-end -->

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0031" status="verified_source" source-page="20" -->
$$
\begin{aligned}|\Delta P_{k}|=\hat{\alpha}_{V,i}+\hat{\beta}_{V,i}VOL^{\hat{H}_i}_{k}+\hat{\epsilon}_{V,k}\end{aligned}
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0031](images/formula_0031.png)
*Formula quality: `verified_source`; source PDF page 20. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:994 (score=0.9485).*
<!-- formula-end -->

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0032" status="verified_source" source-page="20" -->
$$
\begin{aligned}|\Delta P_{k}|=\hat{\alpha}_{W,i}+\hat{\phi}_{O,i}|OFI_{k}|+\hat{\phi}_{V,i}VOL^{\hat{H}_i}_{k}+\hat{\epsilon}_{W,k}\end{aligned}
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0032](images/formula_0032.png)
*Formula quality: `verified_source`; source PDF page 20. Matched to exact arXiv source 1011.6402v3 at OrderImbalanceFinal.tex:997 (score=0.9828).*
<!-- formula-end -->

These regressions are estimated for every half-hour subsample with the exponents ˆ H i preestimated by (16). The averages of ˆ H i and their standard deviation for each stock are presented on the left panel in Table 5. The exponent varies considerably across stocks and time, but is generally below 1/2 in our data. The average results of regressions (17a-17c) for each stock are presented on the middle and right panels. We observe that | OFI k | explains the magnitude of price moves better than V OL ˆ H i k . Although both variables appear to be statistically significant when taken individually, only | OFI k | remains significant in the multiple regression. Thus, the dependence between the magnitude of price moves and the traded volume is mostly due to correlation between V OL k and | OFI k | . Interestingly, the number of trades variable (suggested in [26]) is also statistically significant on a stand-alone basis, but becomes insignificant when added to (17c) as a third variable.

## 5 Conclusion

We have introduced order flow imbalance , a variable that cumulates the sizes of order book events, treating the contributions of market, limit and cancel orders equally, and provided empirical and theoretical evidence for a linear relation between high-frequency price changes and order flow imbalance for individual stocks. We have shown that this linear model is robust across stocks and the impact coefficient is inversely proportional to market depth. These relations suggest that prices respond to changes in the supply and demand for shares at the best quotes, and that the impact coefficient fluctuates with the amount of liquidity provision, or depth, in the market. Moreover, we have demonstrated that order flow imbalance is a stronger driver of high-frequency price changes than standard measures of trade imbalance. Trades seem to carry little to no information about price changes after the simultaneous order flow imbalance is taken into account. If trades do not help to explain price changes after controlling for the order flow imbalance, it is highly possible that the relation between price changes and traded volume simply capture the noisy scaling relation between these variables.

Overall, these findings seem to give an intuitive picture of the price impact of order book events, which is somewhat simpler than the one conveyed by previous studies.

Table 5. Comparison of traded volume and order flow imbalance.

̸

̸

| Ticker   | Avg       | Stdev     | Order flow imbalance   | Order flow imbalance   | Order flow imbalance   | Traded volume   | Traded volume   | Traded volume   | Traded volume   | Both covariates   | Both covariates   | Both covariates   | Both covariates   | Both covariates   | Both covariates   | Both covariates   | Both covariates   |
|----------|-----------|-----------|------------------------|------------------------|------------------------|-----------------|-----------------|-----------------|-----------------|-------------------|-------------------|-------------------|-------------------|-------------------|-------------------|-------------------|-------------------|
|          | ˆ H       | ˆ H       | R 2                    | t ( ˆ β O )            | β O = 0                | F               | R 2             | t ( ˆ β V )     | β V = 0         | F                 | R 2               | t ( ˆ φ O )       | t ( ˆ φ V )       | φ O = 0           | φ V = 0           | F                 | F                 |
| AMD      | 0.06      | 0.08      | 63%                    | 10.3                   | 99%                    | 356             | 14%             | 4.5             | 83%             | 34                | 63%               | 9.4               | 1.1               | 99%               | 35%               | 182               | 182               |
| APOL     | 0.24      | 0.08      | 53%                    | 8.3                    | 90%                    | 258             | 25%             | 6.8             | 99%             | 63                | 57%               | 6.9               | 2.9               | 89%               | 84%               | 144               | 144               |
| AXP      | 0.16      | 0.08      | 55%                    | 10.5                   | 100%                   | 249             | 20%             | 6.6             | 100%            | 48                | 57%               | 9.0               | 2.8               | 100%              | 81%               | 133               | 133               |
| AZO      | 0.43      | 0.22      | 39%                    | 5.5                    | 96%                    | 131             | 32%             | 5.3             | 100%            | 93                | 50%               | 4.3               | 3.6               | 94%               | 96%               | 98                | 98                |
| BAC      | 0.09      | 0.08      | 73%                    | 16.3                   | 100%                   | 560             | 24%             | 5.6             | 83%             | 61                | 74%               | 13.9              | 1.2               | 96%               | 35%               | 285               | 285               |
| BDX      | 0.26      | 0.10      | 55%                    | 8.4                    | 99%                    | 261             | 27%             | 6.3             | 100%            | 71                | 58%               | 6.7               | 2.9               | 98%               | 84%               | 147               | 147               |
| BK       | 0.11      | 0.07      | 68%                    | 13.1                   | 100%                   | 437             | 19%             | 6.6             | 97%             | 46                | 68%               | 11.5              | 2.0               | 99%               | 58%               | 225               | 225               |
| BSX      | -0.17     | 2.41      | 68%                    | 8.4                    | 100%                   | 486             | 14%             | 3.3             | 95%             | 33                | 69%               | 8.0               | 0.1               | 97%               | 12%               | 246               | 246               |
| BTU CAT  | 0.24      | 0.07      | 58%                    | 10.5                   | 99%                    | 283             | 23%             | 6.8             | 99%             | 57                | 60%               | 8.9               | 2.4               | 99%               | 78%               | 151               | 151               |
| CB       | 0.22      | 0.07 0.09 | 56% 56%                | 10.4                   | 98% 99%                | 250             | 19%             | 6.0 6.4         | 98% 99%         | 44 58             | 57% 58%           | 8.9               | 2.1               | 98%               | 63%               | 131               | 131               |
| CCL      | 0.19      |           |                        | 10.1                   |                        | 261             | 23%             | 6.1             |                 | 45                | 62%               | 8.2               | 2.6               | 99%               | 74%               | 141               | 141               |
| CINF     | 0.14 0.13 | 0.07      | 60%                    | 11.3                   | 100% 99%               | 309             | 19% 30%         | 6.6             | 99% 98%         | 85                | 69%               | 9.9 8.7           | 2.4 2.0           | 99% 99%           | 74%               | 162 55%           | 162 55%           |
| CME      | 0.49      | 0.12 0.24 | 67% 28%                | 10.6 4.1               | 94%                    | 505 78          | 30%             | 4.8             | 99%             | 83                | 42%               | 3.2               | 3.6               | 86%               | 94%               | 268 71            | 268 71            |
| COH      | 0.16      |           | 60%                    | 10.4                   | 100%                   | 277             | 22%             | 6.5             | 99%             | 52                | 58%               | 8.9               | 2.2               | 98%               | 69%               |                   |                   |
| COP      | 0.19      | 0.07 0.07 | 56%                    | 9.8                    | 99%                    | 299             | 20%             | 6.0             | 96%             | 49                | 61%               | 8.4               | 2.4               | 100%              | 70% 70%           | 157               | 145               |
| DNR      | 0.08      |           | 62%                    | 10.2                   | 100%                   | 352             | 17%             | 5.9             |                 | 72                | 64%               | 8.2               | 1.8               | 100%              |                   | 193               | 193               |
| CVH      | 0.18      | 0.10 0.07 | 64%                    | 12.0                   | 99% 93%                | 376             | 27%             | 6.3             | 99% 95%         | 38                | 65%               | 10.7              | 2.2               | 99%               | 55%               | 189               | 189               |
| DVN      | 0.26      | 0.07      | 52% 52%                | 8.6                    |                        | 236             | 24% 26%         | 6.7 5.4         | 100% 99%        | 59 69             | 55%               | 7.1               | 2.9               | 91%               |                   | 81% 131           | 81% 131           |
| EFX      | 0.20      | 0.11      |                        | 8.1                    | 99%                    | 241             |                 |                 |                 |                   | 56%               | 6.4               | 2.7               | 97%               | 75%               | 137               | 137               |
| ETN      | 0.26      | 0.10      | 55%                    | 8.2                    | 97%                    | 252             | 27%             | 6.4             | 99%             | 70                | 58%               | 6.8               | 2.9               | 96% 99%           | 83%               | 142               | 142               |
| FISV     | 0.19      | 0.11      | 57%                    | 9.1                    | 100%                   | 284             | 25%             | 5.9             | 100%            | 65                | 59%               | 7.3               | 2.2 2.3           | 100%              | 66%               | 153               | 153               |
| HAS      | 0.20      | 0.09      | 61%                    | 10.1                   | 100%                   | 328             | 26%             | 6.2             | 100%            | 67                | 63%               | 8.2               |                   |                   | 73%               | 175               | 175               |
| HCP      | 0.14      | 0.07      | 57%                    | 11.1                   | 100%                   | 268             | 21%             | 7.0             | 99%             | 50                | 59%               | 9.3               | 2.7               | 100%              | 79% 85%           | 143 145           | 143 145           |
| HOT KSS  | 0.23      | 0.08      | 57%                    | 9.7                    | 98%                    | 263             | 24%             | 6.9             | 100% 99%        | 60                | 60%               | 8.2               | 3.0               | 98%               | 86%               |                   |                   |
|          | 0.24      | 0.08      | 60%                    | 10.8                   | 97%                    | 318             | 25%             | 6.6             |                 | 61                | 62%               | 9.0               | 2.4               | 97%               | 74%               | 169               | 169               |
| LLL      | 0.33      | 0.12      | 58%                    | 9.4                    | 94%                    | 323             | 34%             | 6.9             | 100%            | 101               | 63%               | 7.1               | 3.0               | 91%               |                   | 188               | 188               |
| LMT      | 0.28      | 0.09      | 61%                    | 10.7                   | 99%                    | 327             | 31%             | 7.3             | 100%            | 85                | 64%               | 8.4               | 2.9               | 99%               | 84%               | 182               | 182               |
| M        | 0.11 0.15 | 0.07 0.07 | 69% 61%                | 13.9 12.3              | 100% 100%              | 463             | 20% 21%         | 6.3 6.9         | 99% 99%         | 46 50             | 69%               | 12.2 10.4         | 2.0 2.4           | 100% 100%         | 60% 71%           | 238 170           | 238 170           |
| MAR MFE  | 0.16      | 0.09      | 60%                    | 10.9                   | 99%                    | 324 318         | 24%             | 7.1             | 98%             | 62                | 62% 62%           | 8.8               | 2.5               | 99%               | 71%               | 170               | 170               |
| MHP      | 0.20      | 0.10      | 62%                    | 10.2                   | 99%                    | 377             | 25%             | 5.9             | 99%             | 62                | 64%               | 8.5               | 1.9               | 99%               |                   | 55% 199           | 55% 199           |
| MHS      | 0.23      | 0.08      | 56%                    | 9.2                    | 99%                    | 258             | 24%             |                 | 100%            |                   | 58%               |                   | 2.6               | 98%               |                   |                   |                   |
|          |           |           | 62%                    |                        |                        |                 |                 | 6.6             |                 | 58                |                   | 7.7               |                   |                   | 77%               | 139               | 139               |
| MRK      | 0.10      | 0.07      |                        | 11.0                   | 100%                   | 330             | 17%             | 5.4             | 99%             | 40                | 63%               | 9.8               | 1.8               | 100%              | 55%               | 170               | 170               |
| MRO      | 0.09      | 0.06      | 61%                    | 11.8                   | 100%                   | 333             | 16%             | 6.3             | 95%             | 36                | 63%               | 10.6              | 2.0               | 100%              | 54%               | 172               | 172               |
| MWV      | 0.18      | 0.10      | 62%                    | 10.3                   | 100%                   | 330             | 28%             | 6.7             | 100%            | 75                | 64%               | 8.2               | 2.4               | 100%              | 74%               | 180               | 180               |
| NEM      | 0.20      | 0.07      | 56%                    | 9.9                    | 99%                    | 253             | 20%             | 6.1             | 99%             | 47                | 58%               | 8.6               | 2.5               | 99%               | 75% 73%           | 135               | 135               |
| OMC      | 0.15      | 0.09      | 57%                    | 10.1                   | 99%                    | 286             | 20%             | 6.4             | 98%             | 48                | 59%               | 8.6               | 2.4               | 98%               |                   | 151               | 151               |
| PCS      | 0.11      | 0.18      | 62%                    | 7.1                    | 96%                    | 411             | 18%             | 3.7             | 97%             | 54                | 63%               | 6.5               | 0.7               | 93%               | 20%               | 214               | 214               |
| PHM      | 0.07      | 0.08      | 64%                    | 10.2                   | 100%                   | 384             | 15%             | 5.5             | 90%             | 34                | 65%               | 9.4               | 1.2               | 99%               | 40%               | 195               | 195               |
| PKI      | 0.11      | 0.11      | 55%                    | 7.8                    | 99%                    | 266             | 20%             |                 | 97%             | 47                | 57%               | 6.7               | 1.8               | 98%               | 53%               | 141               | 141               |
| R RAI    | 0.27 0.25 | 0.11 0.10 | 56% 61%                | 8.6                    | 98%                    | 259             | 28% 28%         | 4.8 6.0 5.7     | 100% 100%       | 74                | 59%               | 6.9               | 2.9 2.4           | 97% 99%           | 85% 71%           | 147               | 182               |
| SLB TE   | 0.24 0.09 | 0.07 1.69 | 62% 60%                | 9.2 12.0               | 99%                    | 334 330         | 18%             | 4.4             | 85%             | 73                | 63%               | 7.2               | 1.3               | 98%               | 39%               | 51% 196           | 171               |
|          |           |           |                        | 8.0                    | 99%                    |                 | 19%             | 5.5             | 98%             | 46 48             | 63%               | 7.6 10.6          | 1.7               | 99%               |                   |                   |                   |
| TWC      | 0.25      | 0.10      |                        |                        | 98% 99%                | 371             |                 | 6.6             |                 |                   | 61% 58%           | 7.6               | 3.0               | 99%               |                   | 81%               | 142               |
| WHR      | 0.34      | 0.11      | 55% 56%                | 9.7 8.2                | 97%                    | 253 272         | 27% 29%         | 6.3             | 100% 100%       | 73 78             | 59%               | 6.6               |                   | 2.9 95%           | 86% 156 29% 179   | 86% 156 29% 179   | 86% 156 29% 179   |
| WIN WPI  | 0.06 0.22 | 0.26 0.10 | 48% 61%                | 3.9 9.6                | 79%                    | 340             | 10% 28%         | 2.8 5.8         | 50% 100%        | 34 75             | 49%               | 3.7 7.7           | 0.6 2.2           | 79% 98%           | 71%               | 196               | 196               |
| XTO      |           |           |                        |                        | 98%                    | 361             |                 |                 |                 |                   | 64%               |                   |                   |                   |                   | 125               | 125               |
|          | 0.08      | 0.06      | 53%                    | 10.9                   | 100%                   | 238             | 15%             | 6.5             | 100%            | 32                | 55%               | 9.6               | 2.7               | 100%              | 78%               | 168               | 168               |
| Grand    | 0.18      | 0.18      | 58%                    | 9.8                    | 98%                    | 313             | 23%             | 6.0             | 97%             | 58                | 61%               | 8.3               | 2.3               | 97%               |                   |                   |                   |
| mean     |           |           |                        |                        |                        |                 |                 |                 |                 |                   |                   |                   |                   | 67%               |                   |                   |                   |

Table 5 presents the average results of regressions:

<!-- formula-start id="ref_cont_price_impact_1011.6402:formula:0033" status="decoded_unverified" source-page="22" -->
$$
| \Delta P _ { k } | & = \hat { \alpha } _ { O , i } + \hat { \beta } _ { O , i } | O F I _ { k } | + \hat { \epsilon } _ { O , k } , \\ | \Delta P _ { k } | & = \hat { \alpha } _ { V , i } + \hat { \beta } _ { V , i } V O L _ { k } ^ { \hat { H } _ { i } } + \hat { \epsilon } _ { V , k } , \\ | \Delta P _ { k } | & = \hat { \alpha } _ { W , i } + \hat { \phi } _ { O , i } | O F I _ { k } | + \hat { \phi } _ { V , i } V O L _ { k } ^ { \hat { H } _ { i } } + \hat { \epsilon } _ { W , k } ,
$$
![Source formula ref_cont_price_impact_1011.6402:formula:0033](images/formula_0033.png)
```text
PDF text layer: | ∆ P k | = ˆ α O,i + ˆ β O,i | OFI k | +ˆ ϵ O,k , | ∆ P k | = ˆ α V,i + ˆ β V,i V OL ˆ H i k +ˆ ϵ V,k , | ∆ P k | = ˆ α W,i + ˆ φ O,i | OFI k | + ˆ φ V,i V OL ˆ H i k +ˆ ϵ W,k ,
```
*Formula quality: `decoded_unverified`; source PDF page 22. Machine-decoded LaTeX; verify against the linked source crop before use.*
<!-- formula-end -->

where ∆ P k are the 10-second mid-price changes, OFI k are the contemporaneous order flow imbalances and V OL k are the contemporaneous trade volumes. The exponents ˆ H i were estimated in each subsample beforehand using a logarithmic regression: log | ∆ P k | = log ˆ ¯ θ i + ˆ H i log V OL k + log ˆ ξ k . These regressions were estimated using 273 half-hour subsamples (indexed by i ) for each stock and their outputs were averaged across subsamples. Each subsample typically contains about 180 observations (indexed by k ). The t-statistics were computed using White's standard errors. For each of three regressions, Table 5 reports the average R 2 , the average t-statistic of the coefficient(s), the percentage of samples where the coefficient(s) passed the z-sest at the 5% significance level and the F-statistic of the regression.

̸

̸

## References

- [1] H. Ahn, K. Bae, and K. Chan , Limit orders, depth, and volatility: evidence from the stock exchange of Hong Kong , Journal of Finance, 56 (2001), pp. 767-788.
- [2] R. Almgren and N. Chriss , Optimal execution of portfolio transactions , Journal of Risk, 3 (2000), pp. 5-39.
- [3] R. Almgren, C. Thum, E. Hauptmann, and H. Li , Direct estimation of equity market impact , Journal of Risk, 18 (2005), p. 57.
- [4] T. Andersen and T. Bollerslev , Deutsche mark - dollar volatility: intraday activity patterns, macroeconomic announcements, and longer run dependencies , Journal of Finance, 53 (1998), p. 219.
- [5] M. Avellaneda, S. Stoikov, and J. Reed , Forecasting prices from level-I quotes in the presence of hidden liquidity . Working paper, 2010.
- [6] D. Bertsimas and A. Lo , Optimal control of execution costs , Journal of Financial Markets, 1 (1998), pp. 1-50.
- [7] J.-P. Bouchaud , Encyclopedia of Quantitative Finance , Wiley, 2010, ch. Price Impact.
- [8] J.-P. Bouchaud, D. Farmer, and F. Lillo , Handbook of financial markets: dynamics and evolution , Elsevier: Academic Press, 2009, ch. How markets slowly digest changes in supply and demand.
- [9] J.-P. Bouchaud, Y. Gefen, M. Potters, and M. Wyart , Fluctuations and response in financial markets: the subtle nature of 'random' price changes , Quantitative Finance, 4 (2004), p. 176.
- [10] T. Chordia, R. Roll, and A. Subrahmanyam , Liquidity and market efficiency , Journal of Financial Economics, 87 (2008), p. 249.
- [11] P. K. Clark , A subordinated stochastic process model with finite variance for speculative price , Econometrica, 41 (1973), pp. 135-155.
- [12] Z. Eisler, J.-P. Bouchaud, and J. Kockelkoren , The price impact of order book events: market orders, limit orders and cancellations , Quantitative Finance Papers 0904.0900, arXiv.org, Apr. 2009.
- [13] P. Embrechts, C. Kluppelberg, and T. Mikosch , Modelling extremal events for insurance and finance , Springer, 1997.
- [14] R. Engle, R. Ferstenberg, and J. Russel , Measuring and modeling execution cost and risk . NYU Working Paper No. FIN-06-044, 2006.
- [15] R. Engle and A. Lunde , Trades and quotes: a bivariate point process , Journal of Financial Econometrics, 1 (2003), pp. 159-188.
- [16] M. Evans and R. Lyons , Order flow and exchange rate dynamics , Journal of Political Economy, 110 (2002), p. 170.
- [17] J. D. Farmer, L. Gillemot, F. Lillo, S. Mike, and A. Sen , What really causes large price changes? , Quantitative Finance, 4 (2004), pp. 383-397.

- [18] X. Gabaix, P. Gopikrishnan, V. Plerou, and H. Stanley , A theory of power-law distributions in financial market fluctuations , Nature, 423 (2003), p. 267.
- [19] J. Gatheral , No-dynamic-arbitrage and market impact , Quantitative Finance, 10 (2010), p. 749.
- [20] J. Hasbrouck , Measuring the information content of stock trades , Journal of Finance, 46 (1991), pp. 179-207.
- [21] , The summary informativeness of stock trades: An econometric analysis , Review of Financial Studies, 4 (1991), p. 571.
- [22] J. Hasbrouck and D. Seppi , Common factors in prices, order flows and liquidity , Journal of Finance and Economics, 59 (2001), p. 383.
- [23] N. Hautsch and R. Huang , The market impact of a limit order . SFB 649 Discussion Papers, 2009.
- [24] C. Hopman , Do supply and demand drive stock prices? , Quantitative Finance, 7 (2007), pp. 37-53.
- [25] G. Huberman and W. Stanzl , Price manipulation and quasi-arbitrage , Econometrica, 72 (2004), pp. 1247-1275.
- [26] C. Jones, G. Kaul, and M. Lipson , Transactions, volume, and volatility , Review of Financial Studies, 7 (1994), pp. 631-651.
- [27] J. Karpoff , The relation between price changes and trading volume: A survey , Journal of Financial and Quantitative Analysis, 22 (1987), p. 109.
- [28] D. Keim and A. Madhavan , The upstairs market for large-block transactions: Analysis and measurement of price effects , Review of Economic Studies, 9 (1996), p. 1.
- [29] A. Kempf and O. Korn , Market depth and order size , Journal of Financial Markets, 2 (1999), p. 29.
- [30] P. Knez and M. Ready , Estimating the profits from trading strategies , Review of Financial Studies, 9 (1996), p. 1121.
- [31] C. Lee, B. Mucklow, and M. Ready , Spreads, depths, and the impact of earnings information: an intraday analysis , Review of Financial Studies, 6 (1993), pp. 345-374.
- [32] C. Lee and M. Ready , Inferring trade direction from intraday data , Journal of Finance, 46 (1991), pp. 733-746.
- [33] A. Madhavan, M. Richardson, and M. Roomans , Why do security prices change? a transaction-level analysis of nyse stocks , Review of Financial Studies, 10 (1997), p. 1035.
- [34] T. McInish and R. Wood , An analysis of intraday patterns in bid/ask spreads for nyse stocks , Journal of Finance, 47 (1992), pp. 753-764.
- [35] A. Obizhaeva and J. Wang , Optimal trading strategy and supply/demand dynamics . NBER Working Papers, No 11444, 2005.
- [36] E. Odders-White , On the occurrence and consequences of inaccurate trade classification , Journal of Financial Markets, 3 (2000), pp. 259-286.

- [37] M. O'Hara , Market Microstructure Theory , Wiley, 1998.
- [38] V. Plerou, P. Gopikrishnan, X. Gabaix, and H. Stanley , Quantifying stock-price response to demand fluctuations , Physical Review E, 66 (2002), p. 027104.
- [39] M. Potters and J. Bouchaud , More statistical properties of order books and price impact , Physica A, 324 (2003), p. 133 140.
- [40] G. Richardson, S. E. Sefcik, and R. Thompson , A test of dividend irrelevance using vol? ume reaction to a change in dividend polic , Journal of Financial Economics, 17 (1986), pp. 313-333.
- [41] C. Stephens, H. Waelbroeck, and A. Mendoza , Relating market impact to aggregate order flow: the role of supply and demand in explaining concavity and order flow dynamics . Working Paper Series, 11 2009.
- [42] E. Theissen , A test of the accuracy of the lee/ready trade classification algorithm , Journal of International Financial Markets, Institutions and Money, 11 (2001), pp. 147-165.
- [43] N. Torre and M. Ferrari , The Market Impact Model , BARRA, 1997.
- [44] P. Weber and B. Rosenow , Order book approach to price impact , Quantitative Finance, 5 (2005), pp. 357-364.
- [45] P. Weber and B. Rosenow , Large stock price changes: volume or liquidity? , Quantitative Finance, 6 (2006), p. 7.
- [46] I. Zovko and J. D. Farmer , The power of patience: A behavioral regularity in limit order placement , Quantitative Finance, 2 (2002), pp. 387-392.

## A Appendix: TAQ data processing

Quotes data were filtered as follows:

1. Timestamp ∈ [9:30 am, 4:00 pm].
2. Bid, ask, bid size, ask size are positive.
3. Quote mode ̸∈ { 4 , 7 , 9 , 11 , 13 , 14 , 15 , 19 , 20 , 27 , 28 }

Trades data were filtered as follows:

1. Timestamp ∈ [9:30 am, 4:00 pm].
2. Price and size are positive.
3. Correction indicator ≤ 2.
4. Condition ̸∈ { ' O ' , ' Z ' , ' B ' , ' T ' , ' L ' , ' G ' , ' W ' , ' J ' , ' K ' }

From the filtered quotes data we construct the National Best Bid and Offer (NBBO) quotes. This is done by scanning through the filtered quotes data, while maintaining a matrix with the best quotes for every exchange. When a new entry is read, we check the exchange flag of that entry and update the corresponding row in the exchange matrix. Using this matrix, the NBBO prices are computed at each entry as the highest bid and the lowest ask across all exchanges. The NBBO sizes are simply the sums of all sizes at the NBBO bid and ask across all exchanges.

After the NBBO quotes are computed, we applied a simple quote test to the NBBO quotes and the filtered trades data. This test matches trades with NBBO quotes and computes the direction of matched trades. A trade is matched with a quote, if:

1. Trade is not inside the spread, i.e.
2. (a) Trade price ≥ NBBO ask: in this case the trade is considered to be a buy trade.
3. (b) Trade price ≤ NBBO bid: in this case the trade is considered to be a sell trade.
2. Trade date = quote date.
3. Trade timestamp ∈ [quote timestamp, quote timestamp + 1 second].
4. If the above conditions allow to match a trade with several quotes, it is matched with the earliest quote.

There are other routines to estimate trade direction, including the tick test and the LeeReady rule [32]. Although the latter is used quite frequently, there seems to be no compelling evidence of superiority of either of these heuristics [36, 42]. To test the robustness of our findings to the choice of a trade direction test, we compared our results on a subsample of data, applying alternatively the tick test or the quote test and it led to virtually the same results.

Finally, we removed observations with extremely high bid-ask spreads. To apply this filter coherently across stocks, we computed for each stock the 95-th percentile of its bid-ask spread distribution and removed the 5% of that stock's quotes with the spreads above that percentile.
