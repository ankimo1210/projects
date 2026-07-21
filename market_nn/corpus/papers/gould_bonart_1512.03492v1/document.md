# Queue Imbalance as a One-Tick-Ahead Price Predictor in a Limit Order Book

Martin D. Gould ∗‡ and Julius Bonart ‡

‡ CFM-Imperial Institute of Quantitative Finance, Department of Mathematics, Imperial College, London SW7 2AZ

December 14, 2015

## Abstract

We investigate whether the bid/ask queue imbalance in a limit order book (LOB) provides significant predictive power for the direction of the next mid-price movement. We consider this question both in the context of a simple binary classifier, which seeks to predict the direction of the next mid-price movement, and a probabilistic classifier, which seeks to predict the probability that the next mid-price movement will be upwards. To implement these classifiers, we fit logistic regressions between the queue imbalance and the direction of the subsequent mid-price movement for each of 10 liquid stocks on Nasdaq. In each case, we find a strongly statistically significant relationship between these variables. Compared to a simple null model, which assumes that the direction of mid-price changes is uncorrelated with the queue imbalance, we find that our logistic regression fits provide a considerable improvement in binary and probabilistic classification for large-tick stocks, and provide a moderate improvement in binary and probabilistic classification for small-tick stocks. We also perform local logistic regression fits on the same data, and find that this semi-parametric approach slightly outperform our logistic regression fits, at the expense of being more computationally intensive to implement.

Keywords: Price prediction; queue imbalance; high-frequency trading; limit order books; market microstructure.

## 1 Introduction

In most modern financial markets, trade occurs via a continuous double-auction mechanism called a limit order book (LOB) [Gould et al., 2013]. In an LOB, traders interact by submitting orders that state their desires to buy or sell a specified quantity of an asset at a specified price. Active orders reside in a queue until they are either cancelled by their owner or executed against an order of opposite type. Thanks to electronic LOB trading platforms, traders from around the world can monitor the quantities that are available for purchase or sale at specified prices, and can thereby deduce a detailed, up-to-date picture of market state.

∗ Corresponding author. Email: m.gould@imperial.ac.uk.

Since the widespread uptake of LOB trading, the question of whether information about LOB state can be used to formulate predictions of future price movements has remained a topic of primary interest to practitioners and researchers alike. Due to the potentially lucrative benefits of success, the topic has attracted the attention of countless professional and novice traders, who have sought to reap the financial rewards of discovering strategies that successfully forecast future prices. The question has similarly attracted the attention of many scholars from a wide range of disciplines, who have attempted to quantify several important empirical properties of price series [Chakraborti et al., 2011, Cont, 2001], to understand the origins and nature of price movements [Bouchaud et al., 2009, Farmer et al., 2006], and to propose and evaluate models designed to explain the market dynamics from which price movements emerge [Farmer et al., 2005, Gould et al., 2013].

A key difficulty in using information about LOB state to predict future price movements is the need to identify which state variables to use as inputs when making predictions. In recent years, some authors (see, e.g., Cartea et al. [2015] and Yang and Zhu [2015]) have proposed that the queue imbalance , which describes the difference between the volumes offered for purchase or sale at the best bid and ask quotes in a limit order book (LOB), could constitute a simple yet powerful quantity that is suitable for this purpose. Despite reasonably widespread discussion of this idea among practitioners, detailed, scientific analysis of the true predictive power of this measure has remained limited. Given the apparent prevalence of this approach among many real traders, developing a detailed understanding of both its statistical performance and the possible market dynamics underlying its success is an important and timely task.

In this paper, we study a recent, high-quality data set that describes the LOB activity for each of 10 liquid stocks on Nasdaq to assess whether the queue imbalance provides significant predictive power for the direction of the next mid-price movement. We consider this question both in the context of a simple binary classifier, which seeks to predict the direction of the next mid-price movement, and a probabilistic classifier, which seeks to predict the probability that the next mid-price movement will be upwards.

To implement these classifiers, we fit logistic regressions between the queue imbalance and the direction of the subsequent mid-price movement for each of the stocks in our sample. We ensure that our results are statistically and scientifically rigorous by implementing formal hypothesis tests and quantitative performance measures of out-of-sample forecasting. For each of the 10 stocks in our sample, we test and strongly reject the hypothesis that the fitted regression curve does not find a statistically significant relationship between queue imbalance and the direction of the subsequent mid-price movement.

We also introduce a simple null model, which assumes that the direction of mid-price changes is uncorrelated with the queue imbalance. Compared to the null model, we find that our logistic regressions improve out-of-sample performance of binary classification by about 50-60% for large tick stocks and about 10-30% for small-tick stocks. We find that our results for probabilistic predictions are slightly weaker, but still improve out-of-sample predictive performance by about 20-30% for large-tick stocks and about 2-6% for small-tick stocks.

Although our logistic regression fits indicate that queue imbalance provides significant predictive power for price prediction, the parametric nature of this approach obscures the detailed market dynamics that relate queue imbalance to subsequent mid-price movements. To help address this problem, we also complement our logistic regressions with a semi-parametric approach, by fitting local logistic regression curves to the same data. In contrast to the logistic regression fits, whose shapes are constrained by the parametric form of the logistic sigmoid function, our local logistic fits illustrate a more subtle relationship between queue imbalance and mid-price movements, and thereby help to illuminate how the market microstructure underpins our results. We find that our local logistic regressions slightly outperform our logistic regressions for both binary classification and probabilistic prediction, although we note that the strength of this improvement is relatively small given the considerable increase in computational power required to fit a local logistic regression. To conclude, we discuss how several important differences in LOB behaviour could help to explain the differences that we observe between small- and large-tick stocks, and discuss many possible avenues for future research.

There are many practical applications for the findings that we present. First, the ability to predict future price movements is a valuable tool for practitioners seeking to design trading strategies in financial markets. Many financial institutions invest vast sums of money to improve the predictive power of their forecasts by a tiny fraction of a percentage point, whereas the prediction methods that we present are extremely simple to implement and outperform our simple null model by a considerable margin. Second, thanks to their computational simplicity, the methods that we discuss can also be employed by electronic trading algorithms in real time, to help improve their performance. Third, the ability to formulate accurate forecasts of future price movements could be useful for traders who seek to implement optimal execution algorithms by deciding between submitting limit or market orders. Fourth, the empirical framework that we consider is also a useful laboratory in which to test models. Specifically, comparing a model's price predictions for a given queue imbalance to the corresponding result fitted directly from data could be useful as an indicator for how the model needs to be improved, or to rule it out altogether.

The paper proceeds as follows. In Section 2, we provide a detailed description of price formation in an LOB. In Section 3, we discuss several other publications that have addressed price prediction in an LOB, and we define the measures and terminology that we use for our own study. In Section 4, we describe the data that forms the basis of our empirical calculations. In Section 5, we discuss our statistical methodology. We present our main results in Section 6 and discuss our findings in Section 7. Section 8 concludes.

## 2 Order Queues and Price Changes in a Limit Order Book

## 2.1 Limit Order Books

More than half of the world's financial markets use electronic limit order books (LOBs) to facilitate trade [Ro¸ su, 2009]. In contrast to quote-driven systems, in which prices are set by designated market makers, trade in an LOB occurs via a continuous double-auction mechanism whereby institutions submit orders. An order x = ( p x , ω x , t x ) submitted at time t x with price p x and size ω x &gt; 0 (respectively, ω x &lt; 0) is a commitment by its owner to sell (respectively, buy) up to | ω x | units of the asset at a price no less than (respectively, no greater than) p x .

Whenever an institution submits a buy (respectively, sell) order x , an LOB's trade-matching algorithm checks whether it is possible for x to match to an active sell (respectively, buy) order y such that p y ≤ p x (respectively, p y ≥ p x ). If so, the matching occurs immediately and the owners of the relevant orders agree a trade for the specified amount at the specified price. If not, then x becomes active, and it remains active until either it matches to an incoming sell (respectively, buy) order, or it is cancelled .

Orders that result in an immediate matching upon arrival are called market orders . Orders that do not - instead becoming active orders - are called limit orders . 1 The LOB L ( t ) is the set of all active orders for a given asset on a given platform at a given time t . For a detailed introduction to LOBs, see Gould et al. [2013].

At a given time t , the bid price b ( t ) is the highest stated price among active buy orders,

$$b ( t ) \coloneqq \max _ { \{ x \in \mathcal { L } ( t ) | \omega _ { x } < 0 \} } p _ { x } ,$$

and the ask price a ( t ) is the lowest stated price among active sell orders,

$$a ( t ) \colon = \min _ { \{ x \in \mathcal { L } ( t ) | \omega _ { x } > 0 \} } p _ { x } .$$

The bid price and ask price are collectively called the best quotes . The bid-ask spread at time t is

$$s ( t ) \colon = a ( t ) - b ( t ) .$$

$$m ( t ) \colon = \frac { a ( t ) + b ( t ) } { 2 } .$$

1 Some platforms allow other order types (such as fill-or-kill, stop-loss, or peg orders [Knight Capital Group, 2015]), but it is always possible to decompose the resulting order flow into limit and/or market orders. Therefore, we study LOBs in terms of these simple building blocks.

The mid price at time t is We say that a price p is on the buy side of L ( t ) if p ≤ b ( t ), on the sell side of L ( t ) if p ≥ a ( t ), or inside the bid-ask spread if b ( t ) &lt; p &lt; a ( t ).

## 2.2 Order Queues in a Limit Order Book

LOBs implement two resolution parameters: the tick size π &gt; 0, which specifies the smallest permissible price interval between different orders, and the lot size σ &gt; 0, which specifies the smallest amount of the asset that can be traded. All orders must arrive with a price that is a positive integer multiple of π and a size that is an integer multiple of σ . For example, if π = $0 . 01, then the largest permissible order price that is strictly less than $1 . 00 is $0 . 99. Similarly, if σ = 10 shares, the the smallest permissible order size that is strictly greater than 100 shares is 110 shares.

Because the tick size is strictly positive, the price axis of an LOB is a onedimensional lattice, whose points correspond to positive integer multiples of π . An LOB can therefore be regarded as a set of queues, each of which consists of active buy or sell orders at a specified price (see Figure 1). At a given price p and time t , the total size of active buy orders (i.e., the length of the queue of buy limit orders) is given by

$$n ^ { b } ( p , t ) \coloneqq \sum _ { \{ x \in \mathcal { L } ( t ) | \omega _ { x } < 0 , p _ { x } = p \} } | \omega _ { x } |$$

and the total size of active sell orders (i.e., the length of the queue of sell limit orders) is given by

$$\ n ^ { a } ( p , t ) \coloneqq \sum _ { \{ x \in \mathcal { L } ( t ) | \omega _ { x } > 0 , p _ { x } = p \} } \omega _ { x } .$$

In an LOB, the value of b ( t ) increases whenever a new buy limit order arrives inside the bid-ask spread, and decreases whenever the total volume of buy limit orders at b ( t ) depletes to 0 (which occurs when all buy limit orders at b ( t ) either match to an incoming sell market order or are cancelled by their owners). Similarly, the value of a ( t ) decreases whenever a new sell limit order arrives inside the bid-ask spread, and increases whenever the total volume of sell limit orders at a ( t ) depletes to 0. The value of m ( t ) increases (respectively, decreases) whenever either either of b ( t ) or a ( t ) increases (respectively, decreases).

## 3 Price Prediction and Queue Imbalance in an LOB

During the past 20 years, many empirical and theoretical studies have sought to establish links between the state of an LOB and the subsequent price changes that occur within it. The literature on this topic is vast, and spans many different disciplines, including economics, physics, mathematics, statistics, and psychology. For a recent survey of work in this field, see Gould et al. [2013]. In this section, we review a selection of publications most relevant to our work, and introduce the notion of queue imbalance, which forms the basis for our empirical study.

Figure 1: Schematic of an LOB. The horizontal lines within the blocks at each price level denote how the total size at that price is composed of different active orders.

![Image](images/image_000000_097b7acc4c3b0e6c8df5ef078c6eaa2ec12a279bb130b222b1507be5b7d326cd.png)

## 3.1 Zero-Intelligence Models of LOB State

Early studies of the links between queue dynamics and price formation in an LOB typically assumed that order flows were governed by simple, independent stochastic processes. Several authors postulated models of LOB state to formulate predictions of future price movements. Models of this type are often called 'zero-intelligence' LOB models, because they are not motivated by rational traders who seek to achieve specified trading goals. Smith et al. [2003] introduced a zero-intelligence model in which limit order arrivals, market order arrivals, and cancellations all occur as mutually independent Poisson processes with fixed rate parameters. Cont et al. [2010] extended this model by allowing the rates of limit order arrivals and cancellations to vary across prices. Huang et al. [2015] studied a model in which the order arrival rates depend on the lengths of order queues in L ( t ). Mike and Farmer [2008] considered a zero-intelligence framework in which order flows also exhibit long-range autocorrelations, in agreement with empirical data.

Despite the apparent simplicity of these approaches, zero-intelligence LOB models suffer from several important drawbacks. First, the LOB dynamics that emerge from their interacting order flows are often extremely complex. Consequently, most analysis of zero-intelligence LOB models relies heavily on exten- sive simulations, rather than analytical treatment. Second, although they make reasonably good predictions of the long-run statistical properties of LOB state (see, e.g., Farmer et al. [2005]), zero-intelligence LOB models typically produce poor predictions of price movements. Third, because such models ignore the strategies implemented by real traders, they fail to capture many important correlations and feedback loops between different order flows. This weakness further harms their ability to make good predictions of future price movements in real markets.

## 3.2 Simplifying the State Space

Motivated by these weaknesses, several authors have proposed models that seek to produce more realistic LOB dynamics on a simplified LOB state space. Cont and De Larrard [2013] introduced a model in which n b ( b ( t ) , t ) and n a ( a ( t ) , t ) are assumed to be governed by independent diffusion processes. By studying this model in the hydrodynamic limit, in which stochastic fluctuations are dominated by deterministic flows, the authors obtained analytical expressions for several quantities of interest, such as the distribution of times between price changes, the distribution and autocorrelation of price changes, and the probability of a mid-price movement in a given direction, given n b ( b t , t ) and n a ( a t , t ).

Despite the appealing nature of these results, Gar` eche et al. [2013] presented empirical results to illustrate that the dynamics of n b ( b t , t ) and n a ( a t , t ) are strongly influenced by a coupling between the two queues, and thereby brought into question Cont and de Larrard's assumption of independence between the dynamics of n b ( b t , t ) and n a ( a t , t ). Avellaneda et al. [2011] studied a similar model in which n b ( b t , t ) and n a ( a t , t ) are also governed by diffusion processes, but with a specified correlation ρ . The authors solved their model to deduce a simple, closed-form predictor for the direction of the next mid-price movement, given n b ( b t , t ), n a ( a t , t ), and ρ . Although their assumption that n b ( b t , t ) and n a ( a t , t ) are related by a simple correlation parameter is clearly a simplification of reality, the authors argued that their model produces reasonably good predictions of price movements in real LOBs.

## 3.3 Queue Imbalance in an LOB

In a recent publication, Yang and Zhu [2015] argued that the property of the best bid and ask queues most useful for price prediction is not their lengths, but rather their imbalance. Specifically, at a given time t , let

$$I ( t ) \coloneqq \frac { n ^ { b } ( b _ { t } , t ) - n ^ { a } ( a _ { t } , t ) } { n ^ { b } ( b _ { t } , t ) + n ^ { a } ( a _ { t } , t ) }$$

denote the queue imbalance at time t . The quantity I measures the (normalized) difference between n b ( b t , t ) and n a ( a t , t ), and thereby provides a quantitative assessment of the relative strengths of buying and selling pressure in an LOB. 2

2 Yang and Zhu [2015] define the queue imbalance using only n b ( b t , t ) on the numerator. This produces a linear rescaling of our definition in Equation (7), such that I ∈ [0 , 1]. We

If I ≈ 0 (which occurs when n b ( b t , t ) and n a ( a t , t ) are approximately equal), then the buying and selling pressures are approximately balanced. If I &gt; 0 (which occurs when n b ( b t , t ) &gt; n a ( b t , t )), then the bid queue is longer than the ask queue, which suggests that there is a net positive buying pressure in the LOB. Conversely, if I &lt; 0 (which occurs when n b ( b t , t ) &lt; n a ( b t , t )), then the ask queue is longer than the bid queue, which suggests that there is a net positive selling pressure in the LOB. Values of I close to 1 suggest a very strong buying pressure, and values of I close to -1 suggest a very strong selling pressure.

Empirical study of how the queue imbalance in an LOB affects future price changes dates back almost a decade, to when Cao et al. [2009] studied how the value of I at a specified depth inside the LOB (i.e., not only at the best quotes) influenced mid-price returns during the subsequent 5-minute interval. Stoikov and Waeber [2015] noted that the optimal execution of a single order over a short time horizon depends on the queue imbalance in an LOB. Cartea et al. [2015] studied queue imbalance at the trade-by-trade level on Nasdaq, and noted that the rate of buy (respectively, sell) market order arrivals and the probability of observing an upward (respectively, downward) price movement both increase considerably when I is strongly positive (respectively, strongly negative). Based on their analysis, they designed a trading algorithm whose objective is to place both buy and sell limit orders and thereby generate profits from round-trip trades.

Similarly to these previous publications, the aim of the present paper is to investigate whether queue imbalance I influences the future price dynamics in an LOB. Specifically, we seek to complement the analyses of queue imbalance in these papers with a more formal, quantitative analysis of whether the queue imbalance I in an LOB provides significant predictive power for the direction of the next mid-price movement. In contrast to the previous work in this area, we do not restrict our attention to large-tick stocks, but rather study the predictive power of queue imbalance for a selection of both small-tick and large-tick stocks. By comparing our results from these different stocks, we seek to illuminate how the underlying market microstructure underpins the usefulness of I as a predictor of future price movements.

## 4 Data

The data that we study originates from the LOBSTER database, which provides an event-by-event description of the temporal evolution of the LOB for each stock listed on Nasdaq. 3 The LOBSTER database contains very detailed information regarding the temporal evolution of the relevant LOBs. However, for the present study we require only the time series of bid prices b ( t ), ask prices a ( t ), and queue lengths n b ( b ( t ) , t ) and n a ( a ( t ) , t ). We derive all of the statistics that we use for our empirical analysis from these 4 simple time series. To pro- duce our empirical results in Section 6, we study these time series for a selection of 10 liquid stocks during the entire year of 2014.

choose to use n b ( b t , t ) -n a ( a t , t ) as the numerator because it instead produces an imbalance on the interval [ -1 , 1], and thereby simplifies sign conventions.

3 For a detailed introduction to LOBSTER, see http://LOBSTER.wiwi.hu-berlin.de .

The Nasdaq platform operates continuous trading from 09:30 to 16:00 on each weekday. Trading does not occur on weekends or public holidays, so we exclude these days from our analysis. We also exclude all activity during the first and last 30 minutes of each trading day, to ensure that our results are not affected by the abnormal trading behaviour that can occur shortly after the opening auction or shortly before the closing auction. After making these exclusions, we therefore study all trading activity from 10:00 to 15:30 on each of the 252 trading days in 2014.

On the Nasdaq platform, each stock is traded in a separate LOB with pricetime priority, with a tick size of π = $0 . 01 (see Section 2). Although this tick size is common to all stocks, the prices of different stocks on Nasdaq vary across several orders of magnitude (from about $1 to more than $1000). Therefore, the relative tick size (i.e., the ratio between the stock price and π ) varies considerably across different stocks.

In order to facilitate comparisons between stocks with different relative tick sizes, we first ranked all stocks listed on the Nasdaq exchange according to their total dollar volume of trades during 2014. From this list, we then selected the top 5 entries whose maximal trade price was below $50 . 00, and the top 5 entries whose minimal trade price was above $100 . 00 (see Table 1). We call the first group of stocks large-tick stocks because their low price makes their relative tick size large, and we call the second group of stocks small-tick stocks because their high price makes their relative tick size small. We also repeated our calculations for several other stocks whose prices fell between these two thresholds. We found that some such stocks behaved similarly to the large-tick stocks in our sample, whereas other behaved similarly to the small-tick stocks in our sample. In order to illustrate the clear separation between the results for different types of stocks, we present only our results for the large-tick and small-tick stocks in our sample, and not for the other stocks with intermediate tick size. Table 1 lists the names of the stocks that we choose in this way, along with several summary statistics that describe their aggregate market activity.

The LOBSTER data has many important benefits that make it particularly suitable for our study. First, the data is recorded directly by the Nasdaq servers. Therefore, we avoid the many difficulties associated with data sets that are recorded by third-party providers, such as misaligned time stamps or incorrectly ordered events. Second, the data is fully self-consistent, in the sense that it does not report any activities or updates that would violate the standard rules of LOB trading. By contrast, many other LOB data sets suffer from recording errors that can constitute a considerable source of noise when performing detailed analysis. Third, each limit order described in the data constitutes a firm commitment to trade. Therefore, our results reflect the market dynamics for real trading opportunities, not 'indicative' declarations of possible intent.

The LOBSTER database describes all LOB activity that occurs on Nasdaq, but does not provide any information regarding order flow for the same assets on different platforms. To minimize the possible impact on our results, we restrict Table 1: Summary statistics describing trading activity for the (top panel) large-tick and (bottom panel) small-tick stocks in our sample, which describes LOB activity on Nasdaq during 2014. The large-tick stocks are Microsoft (MSFT), Intel (INTC), Micron Technology (MU), Cisco Systems (CSCO), and Oracle (ORCL). The small-tick stocks are Google (GOOG), Amazon (AMZN), Tesla Motors (TSLA), Priceline (PCLN), and Netflix (NFLX). For each stock, the columns list the total size of market order arrivals V MO (measured in billions of $), the total size of limit order arrivals at the best quotes V LO (measured in billions of $), the minimum trade price p min (measured in $), the maximum trade price p max (measured in $), the mean size of the bid queue 〈 n b ( b ( t ) , t ) 〉 (measured in number of shares), the mean size of the ask queue 〈 n a ( a ( t ) , t ) 〉 (measured in number of shares), and the mean bid-ask spread 〈 s ( t ) 〉 (measured in $).

| 〈 s ( t ) 〉 ($)         | 0 . 013 0 . 013   | 0 . 014   | 0 . 012   | 0 . 015   | 0 . 360 0 . 195    | 0 . 212   | 1 . 111   | 0 . 352   |
|-------------------------|-------------------|-----------|-----------|-----------|--------------------|-----------|-----------|-----------|
| 〈 n a ( a ( t ) , t ) 〉 | 6286 . 8 9879 . 5 | 3922 . 8  | 18128 . 0 | 3244 . 9  | 134 . 9 155 . 6    | 203 . 2   | 80 . 2    | 120 . 0   |
| 〈 n b ( b ( t ) , t ) 〉 | 6206 . 7 9597 . 5 | 3802 . 9  | 17114 . 9 | 3113 . 7  | 133 . 4 158 . 1    | 204 . 4   | 80 . 3    | 120 . 3   |
| p max ($)               | 49 . 94 37 . 84   | 36 . 50   | 28 . 59   | 46 . 70   | 1228 . 88 407 . 80 | 291 . 40  | 1375 . 18 | 488 . 98  |
| p min ($)               | 34 . 97 23 . 50   | 20 . 65   | 21 . 29   | 35 . 65   | 498 . 32 285 . 05  | 136 . 90  | 1017 . 07 | 299 . 50  |
| V LO ($bn)              | 782 . 04 462 . 71 | 341 . 83  | 448 . 87  | 254 . 02  | 265 . 70 146 . 99  | 111 . 60  | 304 . 14  | 135 . 79  |
| V MO ($bn)              | 48 . 22 31 . 22   | 28 . 72   | 24 . 99   | 16 . 00   | 62 . 05 57 . 02    | 51 . 37   | 43 . 24   | 40 . 69   |
|                         | MSFT INTC         | MU        | CSCO      | ORCL      | GOOG AMZN          | TSLA      | PCLN      | NFLX      |

our attention to stocks for which Nasdaq is the primary trading venue and therefore captures the majority of order flow. Our results enable us to identify several robust statistical regularities linking queue imbalance to the directions of mid-price movements, which is precisely the aim of our study. We therefore do not regard this feature of the LOBSTER data to be a serious limitation for the present study.

## 5 Methodology

## 5.1 Sample Construction

For each stock and each trading day in our sample, we first create an ordered set T of times at which the mid price changes,

̸

$$T = \left \{ t \left | \ m ( t ) \neq \lim _ { \varepsilon \downarrow 0 } m ( t - \varepsilon ) \right \} .$$

Let t 1 &lt; t 2 &lt; . . . &lt; t N denote the times in T , and let t 0 denote the time of the first LOB event for the given stock on the given day (which, for our data, occurs at or after 10:00 - see Section 4).

For each time t i ∈ T , we calculate an indicator variable y i to describe whether or not the mid-price movement at t i was upwards,

$$y _ { i } \colon = \begin{{cases} & 1 , \quad \text {if } m ( t _ { i } ) > m ( t _ { i - 1 } ) , \\ & 0 , \quad \text {if } m ( t _ { i } ) < m ( t _ { i - 1 } ) . \end{cases}$$

We choose to study price changes via this simple indicator variable, rather than studying the signed change in mid price, because the magnitude of such price changes are determined not only by n b ( b ( t ) , t ) and n a ( a ( t ) , t ), but also by the prices and lengths of order queues deeper into the LOB. We therefore restrict our attention to the direction of mid-price movements, not their size.

For each time t i ∈ T , we choose a time ˜ t i uniformly at random in the open interval ( t i -1 , t i ) and sample the imbalance I ( ˜ t i ) at this time. To ease exposition, we introduce the notation

$$I _ { i } = I ( \tilde { t } _ { i } ) .$$

In this paper, we seek to assess the predictive power of I i for forecasting y i . There are many other possible choices for when to sample the imbalance to perform predictions (such as sampling I immediately after t i -1 or immediately before t i ), but we restrict our attention to the case of sampling ˜ t i uniformly at random. We return to the discussion of possible alternative approaches in Section 8.

For all stocks in our sample, both the number and temporal spacing between LOB events that affect n b ( b ( t ) , t ) and n a ( a ( t ) , t ) (i.e., market order arrivals and limit order arrivals and cancellations at the best quotes) varies considerably across different time intervals ( t i -1 , t i ). In some cases, the arrivals of such events are highly clustered, in the sense that the time intervals contain some periods with no updates to n b ( b ( t ) , t ) and n a ( a ( t ) , t ) and other periods with many updates to n b ( b ( t ) , t ) and n a ( a ( t ) , t ). In order to understand whether this event clustering strongly influences our results, we also repeated all of our calculations when constructing our random sample in event time . To do so, for each time t i ∈ T , we first construct a list of the times that either n b ( b ( t ) , t ) or n a ( a ( t ) , t ) changed, during the time interval ( t i -1 , t i ). We then choose our sampling time ˜ t i uniformly at random from this (discrete) set of event times. We found that all of our empirical results when choosing ˜ t i in this way were qualitatively the same as those that we report throughout the paper, for which we choose ˜ t i uniformly at random in the open interval ( t i -1 , t i ).

## 5.2 In-Sample and Out-of-Sample Data

The number of mid-price changes that occur in a single trading day varies considerably both across different stocks and across different days. To ensure that our sample contains the same number of data points for each stock each day, we therefore draw a random subsample with a fixed size among the N possible choices in the set T . For the results that we show in Section 6, we use a random subsample size 4 of 100. For each stock, we then aggregate the subsamples from each of the 252 different trading days to produce an aggregated data set of 25200 data points.

A key contribution of the present work is assessing the strength of predictive power provided by I . To avoid the possible dangers of data snooping when performing this analysis, we randomly partition each stock's aggregated data set into two disjoint subsets: a training set, which contains 80% of the data (i.e., 20160 data points), and a testing set, which contains 20% of the data (i.e., 5040 data points). We perform the fits of our logistic regressions and local logistic regressions using the training set (i.e., 'in sample'), then evaluate the predictive power of these fits using the testing set (i.e., 'out of sample').

## 5.3 Formulating Predictions

The aim of the present study is to assess the predictive power of I i for forecasting y i . We first consider this question in the context of a simple binary classifier, which seeks to predict whether, for a given queue imbalance I i , the value of y i will be 0 or 1 (i.e., whether the direction of the next mid-price movement will be upwards or downwards). To perform this binary classification, we seek to estimate a function ˆ y that maps queue imbalance onto some subset of R , and a threshold value y ∗ ∈ R , such that:

- if ˆ y ( I i ) &gt; y ∗ , then we predict y i to equal 1,
- if ˆ y ( I i ) &lt; y ∗ , then we predict y i to equal 0,

4 We also repeated all of our calculations with a variety of subsample sizes ranging from 50 to 1000, and we found that our results were qualitatively the same in each case.

- if ˆ y ( I i ) = y ∗ , then we predict y i to equal either 0 or 1, each with probability 1 / 2.

We then consider this question in the context of a probabilistic classifier, which, for a given queue imbalance I i , seeks to predict the probability that y i = 1. We note that if we choose the function y i for our binary classifier such that

$$\hat { y } \colon ( - 1 , 1 ) \to [ 0 , 1 ] \, ,$$

$$\hat { y } _ { i } \colon = \mathbb { P } \left ( y _ { i } = 1 | I _ { i } \right ) ,$$

then we can use the same function ˆ y to perform both binary classification and probabilistic prediction.

Consider a queue imbalance I i ′ chosen uniformly at random among all observations for which y i = 1 and another queue imbalance I j ′ chosen uniformly at random among all observations for which y i = 0. If I i provides predictive power to perform binary classification, then the resulting values of ˆ y will satisfy

$$\mathbb { P } ( \hat { y } _ { i ^ { \prime } } > \hat { y } _ { j ^ { \prime } } ) > 1 / 2 .$$

If, however, I i provides no predictive power to perform binary classification, then the resulting values of ˆ y will satisfy

$$\mathbb { P } ( \hat { y } _ { i ^ { \prime } } > \hat { y } _ { j ^ { \prime } } ) = \mathbb { P } ( \hat { y } _ { j ^ { \prime } } > \hat { y } _ { i ^ { \prime } } ) = 1 / 2 .$$

Similarly, if I i provides predictive power to perform probabilistic classification, then the resulting values of ˆ y will satisfy

$$\mathbb { P } ( \hat { y } _ { i ^ { \prime } } > 1 / 2 ) > 1 / 2 \text { and } \mathbb { P } ( \hat { y } _ { j ^ { \prime } } > 1 / 2 ) < 1 / 2 .$$

If, however, I i provides no predictive power to perform probabilistic classification, then the resulting values of ˆ y will satisfy

$$\mathbb { P } ( \hat { y } _ { i ^ { \prime } } > 1 / 2 ) = 1 / 2 \text { and } \mathbb { P } ( \hat { y } _ { j ^ { \prime } } > 1 / 2 ) = 1 / 2 .$$

To formulate our estimate of the function ˆ y , we perform a logistic regression of y i onto I i . Specifically, we use the data in our training set to calculate maximum likelihood estimates of the coefficients x 0 and x 1 in the relationship

$$\hat { y } ( I ) = \frac { 1 } { 1 + e ^ { - ( x _ { 0 } + I x _ { 1 } ) } } .$$

For a detailed introduction to logistic regression, see Hosmer and Lemeshow [2004], McCullagh and Nelder [1989].

and if we interpret ˆ y as

## 5.4 Assessing Predictions

To assess the predictive power of our logistic regressions for performing binary and probabilistic classification, we compare their output to that of a simple null model in which we assume that I provides no useful information for predicting the direction of mid-price movements, such that

$$\hat { y } ( I ) = 1 / 2 \text { for all } I .$$

In words, our null model predicts that the probability of an upward price movement is always 1 / 2, irrespective of the queue imbalance.

To assess the predictive power of our fits for performing binary classification, we calculate the out-of-sample receiver operating characteristic (ROC) curves and the corresponding area-under-ROC-curve statistics. The area under the ROC curve quantifies how successfully the logistic regression fits classify cases that result in a price move of a given direction. More precisely, for a given queue imbalance I i ′ chosen uniformly at random among all observations for which y i = 1 and another queue imbalance I j ′ chosen uniformly at random among all observations for which y i = 0, the area under the ROC curve is equal to the probability that the resulting values of ˆ y will satisfy ˆ y i ′ &gt; ˆ y j ′ . For a detailed introduction to ROC curves, see Bradley [1997] and Hanley and McNeil [1982].

To assess the predictive power of our fitted logistic regressions for performing probabilistic classification, we use our function ˆ y to make out-of-sample forecasts ˆ y i for each I i in the testing set, and calculate the corresponding residuals

$$r _ { i } \colon = \hat { y } _ { i } - y _ { i } ,$$

We then calculate the mean square residual across all observations in the testing set. For the null model, ˆ y i = 0 . 5 for all i , so r i is given by

$$r _ { i } = \left \{ \begin{array} { l l } { - 1 / 2 , } & { \text {if } y _ { i } = 1 , } \\ { 1 / 2 , } & { \text {if } y _ { i } = 0 } \end{array}$$

and the mean squared residual is exactly 1 / 4.

## 5.5 Local Logistic Regression

After performing our logistic regression fits, we also consider an alternative estimation of the function ˆ y by performing a local logistic regression of y i onto I i . A local logistic regression is a semi-parametric estimation method that fits a separate logistic regression at each point in the domain. Specifically, for a given imbalance I , the local logistic regression estimator of ˆ y ( I ) is obtained by performing a standard logistic regression at I , but weighting the input observations according to their distance from I . For a detailed introduction to local logistic regression, see Loader [2006]. When performing our local logistic regression fits, we use a standard tricube weight function with a nearest-neighbour bandwidth parameter, whose value we choose by performing a 5-fold cross validation in the training set. For a detailed discussion of parameter estimation via cross validation, see Hastie et al. [2010].

## 6 Results

We now present our main empirical results. In Section 6.1, we calculate the distribution of queue imbalances that we observe in our sample. We perform our logistic regression fits in Section 6.2 and assess their out-of-sample performance in Section 6.3. In Section 6.4, we perform our local logistic regression fits and analyze the resulting curves.

## 6.1 Distribution of I

To help understand the distribution of queue imbalances that occur in our sample, we first calculate histograms of I i for each of the 10 stocks. We plot these histograms in Figure 2.

Figure 2: Histograms of I for each of the 10 stocks in our sample. The left panel shows the results for large-tick stocks and the right panel shows the results for small-tick stocks.

![Image](images/image_000001_3084aa88b42383e1359b52662cfd6ba85ad00cfdb893399da1cd33215f4149c4.png)

For large-tick stocks, it is common to observe a wide range of imbalances between about -0 . 5 and about 0 . 5. The distribution of I decays gradually outside of this range. For some large-tick stocks, this decrease is approximately monotonic, up to statistical noise. For others, such as CSCO, there is another small local maximum close to I = ± 1.

For small-tick stocks, the story is less straightforward due to a strong roundnumber effect that appears at some values of I . Specifically, there exist several queue imbalances that occur much more commonly than do their neighbouring values. This effect is particularly prominent at I = 0 and I = ± 1 / 3, but is also visible at several other round-number values in the domain of I . To illustrate why these round-number effects appear strongly for small-tick stocks, but not for large-tick stocks, we also calculate the empirical cumulative density functions (ECDFs) of the best-quote queue lengths n b ( b ( t ) , t ) and n a ( a ( t ) , t ) (see Figure 3). For large-tick stocks, the curves decay smoothly across the whole domain, which indicates that it is common to observe queues of a wide range of different lengths. For small-tick stocks, by contrast, the ECDFs contain large jumps at some round numbers, such as 100 and 200. This implies that it is much more common to observe queues of these round-number lengths than it is to observe queues of other lengths. These round-number effects for small-tick stocks subsequently manifest in the histograms in Figure 2. For example, if n b ( b ( t ) , t ) = 200 and n a ( a ( t ) , t ) = 100 (both of which occur commonly), then I ( t ) = (200 -100) / (200 + 100) = 1 / 3.

Figure 3: Empirical cumulative density functions (ECDFs) of the best-quote queue lengths n b ( b ( t ) , t ) and n a ( a ( t ) , t ). In order to illustrate the tail behaviour, the plots show the survivor functions (i.e., 1 -ECDF) in doubly logarithmic coordinates.

![Image](images/image_000002_2b22fd467c312aca69134f5c833e87dd0c1bc97525d2bb7e6f0844082ad2e5cf.png)

## 6.2 Logistic Regression Fits

We next perform our logistic regression fits of ˆ y versus I (see Section 5.3). Figure 4 shows the fitted logistic regression curves for each of the stocks in our sample, and Table 2 shows the corresponding maximum likelihood estimates and standard errors of the logistic regression coefficients.

Several particularly salient features are apparent from these results. First, the fitted value of x 0 is small for all stocks in our sample. This suggests that there is an approximately symmetric behaviour for buy-side and sell-side activity. Specifically, the relationship between upward price movements for a given imbalance I = k is approximately the same as the relationship between downward price movements for a given imbalance I = -k , for k ∈ [0 , 1]. By continuity of the logistic regression function, it thereby follows that upward and downward price movements are approximately equally likely when I = 0.

Second, the fitted value of x 1 is positive in each case. This implies that the fitted logistic regression line is a monotone increasing function of I , and therefore suggests that the larger the queue imbalance, the higher the probability that the next mid-price movement will be upwards.

Figure 4: Logistic regression fits of ˆ y versus I . The left panel shows the results for large-tick stocks and the right panel shows the results for small-tick stocks.

![Image](images/image_000003_3021daf075d7403ca3f336c47c8f54d63fed7a587e690b39447ac06ef727c3c8.png)

Table 2: Maximum likelihood estimates of the intercept x 0 and coefficient x 1 in the logistic regression fits of ˆ y versus I . The top panel shows the results for large-tick stocks and the bottom panel shows the results for small-tick stocks. The numbers in parentheses indicate 1 standard error, which we estimate from the corresponding Fisher information matrix. For a full discussion of our logistic regression methodology, see Section 5.3.

|      | x 0      | x 0      | x 1      | x 1      |
|------|----------|----------|----------|----------|
|      | Estimate | St. Err. | Estimate | St. Err. |
| MSFT | 0 . 01   | (0 . 02) | 2 . 49   | (0 . 04) |
| INTC | 0 . 03   | (0 . 02) | 2 . 56   | (0 . 04) |
| MU   | 0 . 03   | (0 . 02) | 2 . 03   | (0 . 04) |
| CSCO | 0 . 06   | (0 . 02) | 2 . 73   | (0 . 04) |
| ORCL | 0 . 05   | (0 . 02) | 2 . 25   | (0 . 04) |
| GOOG | 0 . 03   | (0 . 01) | 0 . 54   | (0 . 02) |
| AMZN | 0 . 03   | (0 . 01) | 0 . 85   | (0 . 03) |
| TSLA | - 0 . 01 | (0 . 01) | 0 . 60   | (0 . 03) |
| PCLN | 0 . 03   | (0 . 01) | 0 . 50   | (0 . 02) |
| NFLX | 0 . 01   | (0 . 01) | 0 . 65   | (0 . 02) |

Table 3: Test statistics for (first two columns) Wald tests for individual coefficients and (third column) likelihood ratio test for the full logistic regression fits of ˆ y versus I . The top panel shows the results for large-tick stocks and the bottom panel shows the results for small-tick stocks. For all tests, the asymptotic distribution of the test statistic is given by a χ 2 distribution with 1 degree of freedom, for which the 95% critical value is 3 . 84 and the 99% critical value is 6 . 63. Entries marked with an asterisk are statistically significant at the 95% level, and entries marked with a double-asterisk are statistically significant at the 99% level.

|      | x 0        | x 1          | Full Model   |
|------|------------|--------------|--------------|
| MSFT | 0 . 30     | 3831 . 73 ∗∗ | 5265 . 76 ∗∗ |
| INTC | 2 . 61     | 4081 . 01 ∗∗ | 5696 . 82 ∗∗ |
| MU   | 3 . 06     | 3171 . 89 ∗∗ | 3976 . 12 ∗∗ |
| CSCO | 11 . 13 ∗∗ | 4261 . 37 ∗∗ | 6205 . 00 ∗∗ |
| ORCL | 9 . 59 ∗∗  | 3698 . 73 ∗∗ | 4852 . 68 ∗∗ |
| GOOG | 4 . 74 ∗   | 469 . 55 ∗∗  | 483 . 24 ∗∗  |
| AMZN | 3 . 00     | 1002 . 24 ∗∗ | 1061 . 45 ∗∗ |
| TSLA | 1 . 02     | 564 . 90 ∗∗  | 583 . 63 ∗∗  |
| PCLN | 3 . 28     | 502 . 32 ∗∗  | 517 . 13 ∗∗  |
| NFLX | 0 . 34     | 761 . 92 ∗∗  | 791 . 63 ∗∗  |

Third, the fitted values of x 1 are much larger for large-tick stocks (for which they vary from about 2 to about 3) than for small-tick stocks (for which they vary from about 0 . 5 to about 0 . 8). These differences in parameter estimates similarly produce substantial differences in the logistic regression fits. For large-tick stocks, the large values of x 1 produce substantial curvature in the fitted logistic regression curves (see the left panel of Figure 4), whereas for small-tick stocks, the small values of x 1 produce much flatter, shallower fitted logistic regression curves (see the right panel of Figure 4). Together, these results suggest that strong imbalances (of either sign) lead to stronger levels of predictability for large-tick stocks than they do for small-tick stocks. For example, the logistic regression curves predict that when I is close to 1, the probability of an upward price move is about 0 . 8 to 0 . 9 for large-tick stocks, but only about 0 . 6 to 0 . 7 for small-tick stocks.

We next turn to the question of whether the x 0 and x 1 coefficients cause a statistically significant impact in the output of the logistic regressions. To address this question, we perform a Wald test for the x 0 and x 1 coefficients in turn (see the first two columns of Table 3).

At the 95% level, the intercept x 0 is not statistically significant for MSFT, INTC, MU, AMZN, TSLA, PCLN, or NFLX, but is statistically significant for CSCO, ORCL, and GOOG. For CSCO and ORCL, x 0 is also statistically significant at the 99% level. This result suggests that there is a statistically significant asymmetry between buy-side and sell-side activity for these stocks. We stress, however, that the strength of this asymmetry is very weak (see Table 2), and that we are only able to detect it with statistical significance because our sample is large. Therefore, even for these stocks, the behaviour of the fitted logistic regression curve is very close to symmetric about I = 0.

The coefficient x 1 is statistically significant at the 99% level for all 10 stocks in our sample. This implies that the logistic regressions detect a strongly statistically significant relationship between the queue imbalance and the direction of the subsequent mid-price movement.

We next turn to the question of the statistical significance of the full logistic regression fits. To address this question, we perform a likelihood ratio test of the fitted logistic regressions against a nested model that contains only the intercept term, and thereby excludes the possible influence of queue imbalance (see the third column of Table 3). For all 10 stocks in our sample, the results of the likelihood ratio test are statistically significant at the 99% level, which allows us to conclude with high statistical confidence that the relationship between ˆ y and I illustrated by our logistic regressions is highly statistically significant.

## 6.3 Assessing Predictive Power

In Section 6.2, we concluded from our logistic regressions that the relationship between the queue imbalance and the direction of the subsequent midprice movement is highly statistically significant. We now turn to the question of how strongly the estimated logistic regression curve ˆ y improves the out-ofsample performance of binary and probabilistic classification, in comparison to a simple null model, which assumes that the direction of mid-price changes is uncorrelated with the queue imbalance I . Due to the large size of our sample, it could be the case that ˆ y produces a relatively small increase in predictive power, despite the logistic regression fits being statistically significant.

We first address the out-of-sample performance of our logistic regression fits for performing binary classification. To do so, we calculate the ROC curves (see Section 5.3) for each of our logistic regression fits in Section 6.2. We show these ROC curves, together with the corresponding ROC curve for the null model, in Figure 5.

In each case, the out-of-sample ROC curves lie above the grey line for all choices of specificity, which implies that the logistic regression fits outperform the out-of-sample predictive power of the null model at all levels of specificity. In Table 4, we list the area under the ROC curve for each stock (see Section 5.4).

For large-tick stocks, the area under the ROC curve varies from about 0 . 7 to about 0 . 8. For small-tick stocks, the results are weaker, and vary from about 0 . 6 to about 0 . 65. In both cases, however, these results indicate that I provides a substantial improvement in the out-of-sample predictive power of the binary classifier. To verify that these results are not influenced by over-fitting, we also calculate the area under the corresponding ROC curves for the in-sample fits. In each case, the in-sample values of the statistics in Table 4 are very similar to the corresponding out-of-sample values, which indicates that the predictive power of the logistic regressions is similar for both the training and testing data.

Figure 5: Receiver operating characteristic (ROC) curves for the out-of-sample predictive power of a binary classifier, based on the logistic regression fits of ˆ y versus I from Section 6.2. The left panel shows the results for large-tick stocks and the right panel shows the results for small-tick stocks. The grey line in each plot denotes the expected performance of the null model, which assumes that the probability of an upward price movement is always equal to 1 / 2, irrespective of the queue imbalance.

![Image](images/image_000004_45750f3fb9dfd19228abf61e170d874b9d93cf2612eb86f9242af24add9da0cb.png)

Table 4: Area under the ROC curves (see Figure 5) for the logistic regression fits of ˆ y versus I shown in Figure 4. The top panel shows the results for large-tick stocks and the bottom panel shows the results for small-tick stocks. For the null model (i.e., ˆ y ( I ) = 0 . 5 for all I ), the expected area under the ROC curve is 0 . 5.

|      | In Sample   | Out of Sample   |
|------|-------------|-----------------|
| MSFT | 0 . 781     | 0 . 762         |
| INTC | 0 . 791     | 0 . 798         |
| MU   | 0 . 747     | 0 . 752         |
| CSCO | 0 . 802     | 0 . 805         |
| ORCL | 0 . 770     | 0 . 770         |
| GOOG | 0 . 592     | 0 . 581         |
| AMZN | 0 . 635     | 0 . 642         |
| TSLA | 0 . 602     | 0 . 602         |
| PCLN | 0 . 592     | 0 . 583         |
| NFLX | 0 . 616     | 0 . 627         |

Table 5: Mean squared residual r i of the logistic regression fits of ˆ y versus I shown in Figure 4. The top panel shows the results for large-tick stocks and the bottom panel shows the results for small-tick stocks. For the null model (i.e., ˆ y ( I ) = 0 . 5 for all I ), the mean squared residual is 0 . 25.

|      | In Sample   | Out of Sample   |
|------|-------------|-----------------|
| MSFT | 0 . 191     | 0 . 198         |
| INTC | 0 . 186     | 0 . 183         |
| MU   | 0 . 204     | 0 . 202         |
| CSCO | 0 . 181     | 0 . 180         |
| ORCL | 0 . 195     | 0 . 195         |
| GOOG | 0 . 244     | 0 . 246         |
| AMZN | 0 . 237     | 0 . 235         |
| TSLA | 0 . 243     | 0 . 243         |
| PCLN | 0 . 244     | 0 . 245         |
| NFLX | 0 . 240     | 0 . 239         |

We next address the out-of-sample predictive power of our probabilistic classifier. To do so, we compute the mean squared residual r i (see Equation (19)) between the observed value of y i and the predicted probability ˆ y i , across all observations in the testing set (see Table 5).

For large-tick stocks, the mean squared residuals vary from about 0 . 18 to about 0 . 2. For small-tick stocks, the mean squared residuals vary from about 0 . 235 to about 0 . 245. For the null model, the mean squared residual of the null model is exactly 1 / 4 (see Section 5.4). Therefore, when compared to the null model, the logistic regression fits provide a reduction in mean squared residual of about 20% to 30% for large-tick stocks, and about 2% to 6% for small-tick stocks. For all stocks, the in-sample values of the mean squared residuals are very similar to the corresponding out-of-sample values, which confirms that the logistic regressions do not suffer from over-fitting.

The results in Tables 4 and 5 together present an interesting picture of the out-of-sample performance of our logistic regression fits. In terms of binary classification of the direction of price movements (which we measure by calculating the area under the ROC curve), the logistic regression fits perform well for large-tick stocks and reasonably well for small-tick stocks. In terms of predicting the probability of an upwards mid-price movement (which we measure by calculating the mean squared residuals), the logistic regression fits again perform well for large-tick stocks. For small-tick stocks, however, the results are much weaker, and the logistic regression fits only slightly outperform the null model. Therefore, despite the queue imbalance being a statistically significant predictor of subsequent price movements for all stocks, the improvement in out-of-sample forecasting power that it provides varies considerably across stocks.

## 6.4 Local Logistic Regressions

In Sections 6.2 and 6.3, we calculated logistic regression fits to estimate a parametric relationship between the queue imbalance and the direction of the subsequent mid-price movement. Although these results are useful for perform fast and simple calculations regarding the statistical significance of the possible relationship between I and y , the parametric nature of this approach could obscure the detailed market dynamics that underpin this relationship, because the shape of the fitted logistic regression curves is constrained by the parametric form of the logistic sigmoid function in Equation (17).

To help address this problem, we now complement our results in Sections 6.2 and 6.3 with a semi-parametric approach, by fitting local logistic regression curves to the same data (see Section 5.3). In contrast to the logistic regression fits, these semi-parametric fits enable us to consider more carefully the subtle relationship between queue imbalance and mid-price movements, and thereby help to illuminate the market dynamics that underpin our results.

Figure 6 shows our fitted local logistic regression curves for each of the stocks in our sample. For each fit, we use a tricube weight function with a nearest-neighbour bandwidth parameter. To choose this bandwidth parameter, we perform a 5-fold cross validation within our training set, using the mean squared residual r i (which we seek to minimize) as our objective function. Although the globally optimal choice of bandwidth parameter varies somewhat across the different stocks in our sample, in all cases it resides between about 0 . 5 and about 0 . 8. For the results that we present in this section, we use the bandwidth parameter 0 . 65. We also repeated all of our calculations for a range of different bandwidth choices between 0 . 6 and about 0 . 7, and we found that our results were qualitatively similar for all choices in this range.

For large-tick stocks, the local logistic regression curves are approximately monotone increasing functions of I , which suggests that larger values of I i correspond to larger values of y i . Similarly to the logistic regression curves (see Figure 4), the local logistic regressions predict that the probability of an upward price movement is about 0 . 8 to 0 . 9 when I is close to 1. In contrast to the logistic regression curves, however, the local logistic regression curves suggest that the behaviour of the system exhibits 2 different regimes. For values of I between about -0 . 25 and about 0 . 25, the ˆ y curve is quite steep, which indicates that when the bid and ask queues have similar lengths, a relatively small difference in the queue imbalance corresponds to a considerable change in the probability that the next price movement will be upwards. Outside of this region, the steepness of the ˆ y curve decreases considerably. Therefore, for values of I less than about -0 . 25 or greater than about 0 . 25, a further difference in queue imbalance corresponds to a smaller change in the probability that the next price movement will be upwards.

For small-tick stocks, the local logistic regression curves predict that the probability of an upward price movement is about 0 . 6 when I is close to 1. For all small-tick stocks except PCLN, the local logistic regression curves are nonmonotonic in I . This result is rather puzzling, because it suggests that there are cases when a weaker imbalance increases the probability of an upward midprice movement. This counter-intuitive finding brings into question whether the fitted local logistic regressions ˆ y really detect a meaningful relationship, or simply over-fit to noise.

Figure 6: Local logistic regression fits of ˆ y versus I . For each curve, we use a tricube weight function and a nearest-neighbour bandwidth of 0 . 65. The left panel shows the results for large-tick stocks and the right panel shows the results for small-tick stocks. For full details of our local logistic regression methodology, see Section 5.3 and the discussion in the main text.

![Image](images/image_000005_2c71c3d3ce6b34e3aa60e20e618931e712cbf9a8afc160365b6bb28adb32397c.png)

To address this question, we again consider the out-of-sample predicted power of the local logistic regression curves for performing binary classification and probabilistic classification. Figure 7 shows the out-of-sample ROC curves (see Section 5.3) for each of our local logistic regression fits, together with the corresponding ROC curve for the null model of ˆ y ( I ) = 1 / 2 for all I .

For each stock, the out-of-sample ROC curve for the local logistic regressions is very similar to the corresponding ROC curve for the logistic regression. In all cases, the ROC curve lies above the grey line, which indicates that the local logistic regression fits outperform the out-of-sample predictive power of the null model at all levels of specificity.

To quantify the strength of this increase in predictive power, and to consider the out-of-sample predictive power of the local logistic regression curves for performing probabilistic classification, we again calculate the area under the ROC curve (see the first two columns of Table 6) and the mean squared residual r i (see the final two columns of Table 6).

Similarly to our results in Tables 4 and 5, the in-sample values of the statistics in Table 6 are very similar to the corresponding out-of-sample values, which indicates that the predictive power of the local logistic regressions is similar for both the training and testing data. Therefore, the unusual shape of the ˆ y functions in Figure 7 is not a consequence of over-fitting to noise.

By comparing the performance measures for the logistic regressions in Ta- bles 4 and 5 to the corresponding performance measures for the local logistic regressions (see Table 6), we are able to quantify the differences between these different approaches. Interestingly, the values in Tables 4 and 5 are all very similar to the corresponding values in Table 6. This suggests that the performance of these two different approaches is quite similar. Detailed comparisons of these tables reveal that the local logistic regressions slightly outperform the logistic regressions in some cases, but these improvements are all quite small. We provide a more detailed comparison of our results from logistic regression and local logistic regression in Section 7.

Figure 7: Receiver operating characteristic (ROC) curves for the out-of-sample predictive power of the local logistic regression fits of ˆ y versus I . The left panel shows the results for large-tick stocks and the right panel shows the results for small-tick stocks. The grey line in each plot denotes the expected performance of the null model, which assumes that the probability of an upward price movement is always equal to 1 / 2, irrespective of the queue imbalance.

![Image](images/image_000006_d881eb68ad42aa5b6a7be7675927248c5538be809ace26f0c2a1a984033ffe03.png)

Table 6: Statistics describing the predictive power of the local logistic regression fits of ˆ y versus I . The first two columns show the area under the ROC curve and the second two columns show the mean squared residual of the fits. The top panel shows the results for large-tick stocks and the bottom panel shows the results for small-tick stocks. For the null model (i.e., ˆ y ( I ) = 0 . 5 for all I ), the expected area under the ROC curve is 0 . 5 and the mean squared residual is 0 . 25. For a full discussion of our local logistic regression methodology, see Section 5.3 and the discussion in the main text.

|      | Area Under ROC Curve   | Area Under ROC Curve   | Mean Squared Residual   | Mean Squared Residual   |
|------|------------------------|------------------------|-------------------------|-------------------------|
|      | In Sample              | Out of Sample          | In Sample               | Out of Sample           |
| MSFT | 0 . 781                | 0 . 762                | 0 . 190                 | 0 . 198                 |
| INTC | 0 . 791                | 0 . 798                | 0 . 185                 | 0 . 183                 |
| MU   | 0 . 747                | 0 . 752                | 0 . 204                 | 0 . 202                 |
| CSCO | 0 . 802                | 0 . 805                | 0 . 181                 | 0 . 179                 |
| ORCL | 0 . 770                | 0 . 770                | 0 . 195                 | 0 . 195                 |
| GOOG | 0 . 592                | 0 . 581                | 0 . 244                 | 0 . 246                 |
| AMZN | 0 . 636                | 0 . 642                | 0 . 236                 | 0 . 235                 |
| TSLA | 0 . 602                | 0 . 603                | 0 . 242                 | 0 . 242                 |
| PCLN | 0 . 592                | 0 . 583                | 0 . 244                 | 0 . 245                 |
| NFLX | 0 . 616                | 0 . 627                | 0 . 240                 | 0 . 239                 |

## 7 Discussion

Our results in Section 6 illustrate the existence of a statistically significant relationship between the queue imbalance and the direction of the subsequent midprice movement. For large-tick stocks, the relationship depends quite strongly on the queue imbalance (see upper rows of Table 2) and provides a considerable improvement in out-of-sample predictive power in terms of both binary classification (see Table 4) and probabilistic classification (see Table 5). For small-tick stocks, the relationship depends less strongly on the queue imbalance (see lower rows of Table 2), and the improvement in out-of-sample predictive power is more moderate (see Table 6).

Among the stocks in our sample, the weakest out-of-sample performance that we observe occurs in the probabilistic classification for GOOG, for which our fits outperform the null model by about 2%. Although this number is certainly small compared to the performance that we achieve for other stocks, it is important to remember that many practitioners invest huge sums of money to improve their trading strategies by tiny fractions of a percentage point. Therefore, even this very moderate performance for GOOG could be economically significant for some market participants. Moreover, both of our performance measures are unconditional averages that make forecasts for all data points, many of which correspond to situations where the imbalance is small (see Figure 2), and therefore where the predictability of the mid-price movement is weak. If we considered only the situations in which the queue imbalance was close to ± 1, then the out-of-sample performance of our estimators would improve considerably. This observation is particularly important from a practical standpoint, because some practitioners may only be interested in forecasting when the ability to do so is likely to be strong, and may therefore simply abstain from trading when I ≈ 0.

Similarly, it seems reasonable to assume that I is less informative when both n b ( b ( t ) , t ) and n a ( a ( t ) , t ) are small, because the arrival of a single buy (respectively, sell) market order is likely to cause the mid price to increase (respectively, decrease). Therefore, if we considered only the situations in which both n b ( b ( t ) , t ) and n a ( a ( t ) , t ) are considerably larger than 0, then the out-ofsample performance of our estimators would again improve considerably.

It is interesting to consider why our results for large-tick stocks are so dif- ferent from our results for small-tick stocks. We believe that the answer to this puzzle lies in the underlying market microstructure. Recall from Section 2 that in an LOB, there are usually two ways for m ( t ) to change: by a new limit order arriving inside the bid-ask spread, or by one of the bid or ask queue lengths depleting to 0. However, the mean bid-ask spread for the large-tick stocks in our sample is very close to its minimum possible value of the platform's tick size, s ( t ) = π = $0 . 01 (see Table 1). This behaviour has an important consequence for LOB dynamics, because it removes the possibility that a new limit order will arrive inside the bid-ask spread, and thereby eliminates one of the two possible reasons for changes in m ( t ). It is therefore reasonable to believe that the queue imbalance (which quantifies the relative lengths of the bid and ask queues) will provide stronger predictive power when s ( t ) = π , because the probability of an upwards price movement is governed only by the probability that the ask queue depletes before the bid queue (which, in turn, depends directly on the queue lengths), and not on the probability that a new buy limit order arrives inside the spread.

Even when s ( t ) &gt; π , there are still strong reasons for why market participants may behave differently for small-tick and large-tick stocks. Similarly to most other LOBs, the Nasdaq platform operates a price-time priority rule (see Section 4), by which priority is given to the active buy (respectively, sell) orders with the highest (respectively, lowest) price, and ties are broken by selecting the active order with the earliest submission time. When s ( t ) &gt; π , any market participant has the opportunity to submit a buy (respectively, sell) limit order with higher priority than any others in the LOB, simply by choosing the price of this order to be one tick higher than b ( t ) (respectively, lower than a ( t )). Therefore, the tick size π determines the cost of 'buying' priority in the LOB. For large-tick stocks, this cost is relatively high, so many traders choose to submit new limit orders that wait in the queues at the best quotes, and the typical sizes of n b ( b ( t ) , t ) and n a ( a ( t ) , t ) are large. For small-tick stocks, this cost is relatively low, so many traders choose to submit new limit orders inside the bid-ask spread, and the typical sizes of n b ( b ( t ) , t ) and n a ( a ( t ) , t ) are small. As noted above, the predictive power of I is likely to be larger in situations where n b ( b ( t ) , t ) and n a ( a ( t ) , t ) are larger. In this way, the stronger out-of-sample performance for large-tick stocks can similarly be attributed to the longer queue lengths that typically occur for these stocks.

For some stocks in our sample, we find a weak but statistically significant asymmetry in the fitted logistic regressions, which manifests as a non-zero value of the intercept x 0 (see Table 2). For these stocks, this result suggests that even when the imbalance is slightly less than 0, the probability that the next midprice movement will be upwards is greater than 1 / 2. We propose two possible explanations for this finding. First, the arrival of exogenous news may cause traders to change their trading behaviours, irrespective of the queue imbalance. For example, if a trader receives news that a given company's earnings have outperformed expectations, then he/she may submit a large market order to buy the stock (and thereby cause an increase in mid price), even if the current queue imbalance is negative. We note that all stocks for which we find x 0 to be statistically significantly positive underwent considerable price increases during 2014, which is consistent with this hypothesis of an exogenous buying pressure. Second, some strategic liquidity providers may implement complex strategies that skew the queue imbalance via an asymmetric submission of limit orders. For example, if a strategic liquidity provider fears the possibility of a strong downward price movement, then he/she may choose to submit fewer sell limit orders than buy limit orders, even in the absence of any information about the likely future value of the asset. In a recent empirical study of strategic liquidity provision on Nasdaq, Bonart and Gould [2015] found strong evidence to suggest that liquidity providers implement strategies that created imbalanced net order flow at the best quotes. Although it is difficult to test these theories directly, we believe that both of these explanations are likely to contribute to the behaviour that we observe.

In addition to our logistic regression fits, we also perform local logistic regression fits on the data. By comparing the entries in Tables 4 and 5 to the corresponding entries in Table 6, it is possible to compare the performance of the logistic regression and local logistic regression fits. Most of the entries in Tables 4 and 5 are equal to the corresponding entries in Table 6, even up to the third decimal place. This implies that the performance of the two methods is very similar. In a small number of cases, however, the local logistic regression fits slightly outperform the corresponding logistic regression fits.

Both approaches have benefits and drawbacks. Performing logistic regression is much less computationally intensive than performing local logistic regression, and the full fit of the logistic regression model consists of just 2 scalar values, x 0 and x 1 . Saving the fitted logistic regression curve to a computer hard disk therefore requires very little storage space. By contrast, saving the fitted local logistic regression curve requires saving a full copy of the training data, which can be very large. However, local logistic regression has the important benefit of providing more detailed information about the underlying LOB dynamics, because the fitted regression curve is not constrained by the parametric form of the logistic sigmoid function. Therefore, careful analysis of the local logistic regression fits can provide deeper understanding of the results.

## 8 Conclusions and Outlook

In this paper, we have presented an empirical study of whether the queue imbalance I provides significant predictive power for the direction y of the next mid-price movement. We used data describing the LOB activity for each of 10 liquid stocks on Nasdaq during 2014 to fit logistic regression curves that enabled us to perform both binary classification and probabilistic classification of y , given I . For all 10 stocks in our sample, we found that our logistic regressions identified a strongly statistically significant relationship between I and y .

For the large-tick stocks in our sample, our logistic regression fits provide a considerable improvement in both binary and probabilistic classification. For the small-tick stocks, we found that the increase in predictive power was more moderate, particularly for probabilistic classification. We argued that the reason for these differences was the differences in underlying market microstructure. We also performed local logistic regression fits on the same data, and found that this semi-parametric approach slightly outperforms the logistic regression fits, at the expense of being more computationally expensive.

In addition to these practical benefits, our results also highlight many possible avenues for future research. Throughout this paper, we have chosen to measure the queue imbalance via the quantity I , according to Equation (7), sampled at a time chosen uniformly at random between subsequent changes of m ( t ). Although we identify a statistically significant relationship between I and y , there are many other possible ways to measure queue imbalance in an LOB. For example, we could measure the value of I immediately after or immediately before each mid-price change, to examine how its predictive power varies according to the length of time that elapses before the next price change. Similarly, it would be interesting to see whether an alternative definition of the queue imbalance could provide stronger out-of-sample predictive power than the quantity I that we used for this study. Other possibilities could include quantities such as log( n b ( b ( t ) , t ) /n a ( a ( t ) , t )), or even simply n b ( b ( t ) , t ) -n a ( a ( t ) , t ). Moreover, we have only studied the imbalance between the best bid and ask queues. It is possible that the predictive power of our approach could be improved by also incorporating other statistics about the lengths or imbalance of other queues deeper into the LOB.

Our results also raise interesting questions about the predictability of price movements on longer time scales. For example, does I provide useful information about the direction of price movements further into the future? If so, how does this predictive power diminish over time? And how do price movements remain unpredictable on longer timescales, given that we show them to be quite predictable in our one-step-ahead framework?

Understanding the relationship between queue imbalance and subsequent price movements is also an important theoretical question. It would therefore be interesting to build models for how imbalance could evolve over time, and could thereby affect the subsequent evolution of LOB state. In comparison to modelling the full state of an LOB (which is an extremely high-dimensional problem), the simple, one-dimensional nature of I ( t ) makes modelling its temporal evolution an attractive task. We aim to address these and many other questions about the predictive power of queue imbalance in our future work.

## Acknowledgements

We thank Jean-Philippe Bouchaud, Rama Cont, Jonathan Donier, Till Hoffmann, Nick Jones, Julien Kockelkoren, Charles-Albert Lehalle, and Douglas Machado for useful discussions. We thank Jonas Haase and Ruihong Huang for technical support. Martin D. Gould gratefully acknowledges support from the James S. McDonnell Foundation and Julius Bonart gratefully acknowledges support from CFM.

## References

- M. Avellaneda, J. Reed, and S. Stoikov. Forecasting prices from level-I quotes in the presence of hidden liquidity. Algorithmic Finance , 1(1):35-43, 2011.
- J. Bonart and M. D. Gould. Strategic liquidity provision in a limit order book. arXiv:1511.04116 , 2015.
- J. P. Bouchaud, J. D. Farmer, and F. Lillo. How markets slowly digest changes in supply and demand. In T. Hens and K. R. Schenk-Hopp´ e, editors, Handbook of Financial Markets: Dynamics and Evolution , pages 57-160. North-Holland, Amsterdam, The Netherlands, 2009.
- A. P. Bradley. The use of the area under the ROC curve in the evaluation of machine learning algorithms. Pattern Recognition , 30(7):1145-1159, 1997.
- C. Cao, O. Hansch, and X. Wang. The information content of an open limitorder book. Journal of Futures Markets , 29(1):16, 2009.
6. ´ A. Cartea, R. F. Donnelly, and S. Jaimungal. Enhancing trading strategies with order book signals. Working Paper, SSRN eLibrary ID 2668277 , 2015.
- A. Chakraborti, I. M. Toke, M. Patriarca, and F. Abergel. Econophysics review I: Empirical facts. Quantitative Finance , 11(7):991-1012, 2011.
- R. Cont. Empirical properties of asset returns: stylized facts and statistical issues. Quantitative Finance , 1(2):223-236, 2001.
- R. Cont and A. De Larrard. Price dynamics in a Markovian limit order market. SIAM Journal on Financial Mathematics , 4(1):1-25, 2013.
- R. Cont, S. Stoikov, and R. Talreja. A stochastic model for order book dynamics. Operations Research , 58(3):549-563, 2010.
- J. D. Farmer, P. Patelli, and I. I. Zovko. The predictive power of zero intelligence in financial markets. Proceedings of the National Academy of Sciences of the United States of America , 102(6):2254-2259, 2005.
- J. D. Farmer, A. N. Gerig, F. Lillo, and S. Mike. Market efficiency and the long-memory of supply and demand: Is price impact variable and permanent or fixed and temporary? Quantitative Finance , 6(2):107-112, 2006.
- A. Gar` eche, G. Disdier, J. Kockelkoren, and J. P. Bouchaud. Fokker-Planck description for the queue dynamics of large tick stocks. Physical Review E , 88(3):032809, 2013.
- M. D. Gould, M. A. Porter, S. Williams, M. McDonald, D. J. Fenn, and S. D. Howison. Limit order books. Quantitative Finance , 13(11):1709-1742, 2013.
- J. A. Hanley and B. J. McNeil. The meaning and use of the area under a receiver operating characteristic curve. Radiology , 143(1):29-36, 1982.

- T. Hastie, R. Tibshirani, and J. Friedman. The Elements of Statistical Learning . Springer, New York, NY, USA, 2010.
- D. W. Hosmer and S. Lemeshow. Applied Logistic Regression . Wiley, New York, NY, USA, 2004.
- W. Huang, C. A. Lehalle, and M. Rosenbaum. Simulating and analyzing order book data: The queue-reactive model. Journal of the American Statistical Association , 110(509):107-122, 2015.
4. [Knight Capital Group. Retrieved 14 April 2015 from http://www.hotspotfx. com/download/userguide/HSFX/HSFX\_UserGuide\_wrapper.html , 2015.](http://www.hotspotfx.com/download/userguide/HSFX/HSFX_UserGuide_wrapper.html)
- C. Loader. Local Regression and Likelihood . Springer, New York, NY, USA, 2006.
- P. McCullagh and J. A. Nelder. Generalized Linear Models , volume 37. Chapman and Hall, London, UK, 1989.
- S. Mike and J. D. Farmer. An empirical behavioral model of liquidity and volatility. Journal of Economic Dynamics and Control , 32(1):200-234, 2008. ISSN 0165-1889.
- I. Ro¸ su. A dynamic model of the limit order book. Review of Financial Studies , 22(11):4601-4641, 2009.
- E. Smith, J. D. Farmer, L. Gillemot, and S. Krishnamurthy. Statistical theory of the continuous double auction. Quantitative Finance , 3(6):481-514, 2003.
- S. Stoikov and R. Waeber. Reducing transaction costs with low-latency trading algorithms. Working Paper, SSRN eLibrary ID 2661618 , 2015.
- T. W. Yang and L. Zhu. A reduced-form model for level-1 limit order books. arXiv:1508.07891 , 2015.
