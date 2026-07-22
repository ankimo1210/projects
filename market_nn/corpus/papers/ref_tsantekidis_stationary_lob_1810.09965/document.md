# Using Deep Learning for price prediction by exploiting stationary limit order book features

Avraam Tsantekidis a , Nikolaos Passalis a , Anastasios Tefas a , Juho Kanniainen b , Moncef Gabbouj c , Alexandros Iosifidis d

a Department of Informatics, Aristotle University of Thessaloniki, Thessaloniki, Greece

b Laboratory of Industrial and Information Management, Tampere University of Technology, Tampere, Finland c

Laboratory of Signal Processing, Tampere University of Technology, Tampere, Finland

d Department of Engineering, Electrical and Computer Engineering, Aarhus University, Denmark

## Abstract

The recent surge in Deep Learning (DL) research of the past decade has successfully provided solutions to many difficult problems. The field of quantitative analysis has been slowly adapting the new methods to its problems, but due to problems such as the non-stationary nature of financial data, significant challenges must be overcome before DL is fully utilized. In this work a new method to construct stationary features, that allows DL models to be applied effectively, is proposed. These features are thoroughly tested on the task of predicting mid price movements of the Limit Order Book. Several DL models are evaluated, such as recurrent Long Short Term Memory (LSTM) networks and Convolutional Neural Networks (CNN). Finally a novel model that combines the ability of CNNs to extract useful features and the ability of LSTMs' to analyze time series, is proposed and evaluated. The combined model is able to outperform the individual LSTM and CNN models in the prediction horizons that are tested.

Keywords: Limit Order Book, Stationary Features, Price Forecasting, Deep Learning

## 1. Introduction

In the last decade Machine Learning (ML) has been rapidly evolving due to the profound performance improvements that Deep Learning (DL) has ushered. Deep Learning has outperformed previous state-of-the-art methods in many fields of Machine Learning, such as Natural Language Processing (NLP) [1], image processing [2] and speech generation [3]. As the number of new methods incorporating Deep Learning in many scientific fields increase, the proposed solutions begin to span across other disciplines where Machine Learning was used in a limited capacity. One such example is the quantitative analysis of the stock markets and the usage of Machine Learning to predict price movements or the volatility of the future prices or the detection of anomalous events in the markets.

In the field of quantitative analysis, the mathematical modelling of the markets has been the de facto approach to model stock price dynamics for trading, market making, hedging, and risk management. By utilizing a time series of values, such as the price fluctuations of financial products being traded in the markets, one can construct statistical models which can assist in the extraction of useful information about the current state of the market and a set of probabilities for possible future states, such as price or volatility changes. Many models, such as the Black-Scholes-Merton model [4], attempted to mathematically deduce the price of options and can be used to provide useful indications of future price movements.

Email addresses: avraamt@csd.auth.gr (Avraam Tsantekidis), passalis@csd.auth.gr (Nikolaos Passalis), tefas@aiia.csd.auth.gr (Anastasios Tefas), juho.kanniainen@tut.fi (Juho Kanniainen), moncef.gabbouj@tut.fi (Moncef Gabbouj), alexandros.iosifidis@eng.au.dk (Alexandros Iosifidis)

However, at some point as more market participants started using the same model the behaviour of the price changed to the point that it could no longer be taken advantage of. Newer models, such as the stochastic modelling of limit order book dynamics [5], the jump-diffusion processes for stock dynamics [6] and volatility estimation of market microstructure noise [7] have been attempts predict multiple aspects of the financial markets. However such models are designed to be tractable, even at the cost of reliability and accuracy, and thus they do not necessarily fit empirical data very well.

The aforementioned properties put handcrafted models at a disadvantage, since the financial markets very frequently exhibit irrational behaviour, mainly due to the large influence of human activity, which frequently causes these models to fail. Combining Machine Learning models with handcrafted features usually improves the forecasting abilities of such models, by overcoming some of the aforementioned limitations, and improving predictions about various aspects of financial markets. This led many organizations that participate in the Financial Markets, such as Hedge Funds and investment firms, to increasingly use ML models, along with the conventional mathematical models, to make crucial decisions.

Furthermore, the introduction of electronic trading, that also led to the automation of trading operations, has magnified the volume of exchanges, producing a wealth of data. Deep Learning models are perfect candidates for analyzing such amounts of data, since they perform significantly better than the conventional Machine Learning methodologies when a large amount of data is available. This is one of the reasons that Deep Learning is starting to have a role in analyzing the data coming from financial exchanges. [8, 9]

The most detailed type of data that financial exchanges are gathering is the comprehensive logs of every submitted order and event that is happening within their internal matching engine. This log can be used to reconstruct the Limit Order Book (LOB), which is explained further in Section 3. A basic task that can arise from this data is the prediction of future price movements of an asset by examining the current and past supply and demand of Limit Orders. This type of comprehensive logs kept by the exchanges is excessively large and traditional Machine Learning techniques, such as Support Vector Machines (SVMs) [10], usually cannot be applied out-of-the-box. Utilizing this kind of data directly with existing Deep Learning methods is also not possible due to their nonstationary nature. Prices fluctuate and suffer from stochastic drift, so in order for them to be effectively utilized by DL methods a preprocessing step is required to generate stationary features from them.

The main contribution of this work is the proposal of a set of stationary features that can be readily extracted from the Limit Order Book. The proposed features are thoroughly evaluated for predicting future mid price movements from large-scale high-frequency Limit Order data using several different Deep Learning models, ranging from simple Multilayer Perceptrons (MLPs) and CNNs to Recurrent Neural Networks (RNNs). Also we propose a novel Deep Learning model that combines the feature extraction ability of Convolutional Neural Networks (CNNs) with the Long Short Term Memory (LSTM) networks' power to analyze time series.

In Section 2 related work which employs ML models on financial data is briefly presented.

Then, the dataset used is described in detail in Section 3. In Section 4 the proposed stationary feature extraction methodology is presented in detail, while in Section 5 the proposed Deep Learning methods are described. In Section 6 the experimental evaluation and comparisons are provided. Finally, conclusions are drawn and future work is discussed in Section 7.

## 2. Related Work

The task of regressing the future movements of financial assets has been the subject of many recent works such as [11, 12, 13]. Proven models such as GARCH are improved and augmented with machine learning component such as Artificial Neural Networks [14]. New hybrid models are employed along with Neural Networks to improve upon previous performance [15].

One of the most volatile financial markets is FOREX, the currency markets. In [16], neural networks are used to predict the future exchange rate of major FOREX pairs such as USD/EUR. The model is tested with different prediction steps ranging from daily to yearly which reaches the conclusion that shorter term predictions tend to be more accurate. Other financial metrics, such as cash flow prediction, are very closely correlated to price prediction.

In [17], the authors propose the 'Deep Portfolio Theory' which applies autoencoders in order to produce optimal portfolios. This approach outperforms several established benchmarks, such as the Biotechnology IBB Index. Likewise in [18], another type of autoencoders, known as Restricted Boltzmann Machine (RBM), is applied to encode the end-of-month prices of stocks. Then, the model is fine-tuned to predict whether the price will move more than the median change and the direction of such movement. This strategy is able to outperform a benchmark momentum strategy in terms of annualized returns.

Another approach is to include data sources outside the financial time series, e.g., [19], where phrases related to finance, such as 'mortgage' and 'bankruptcy' were monitored on the Google trends platform and included as an input to a recurrent neural network along with the daily S&amp;P 500 market fund prices. The training target is the prediction of the future volatility of the market fund's price. This approach can greatly outperform many benchmark methods, such as the autoregressive GARCH and Lasso techniques.

The surge of DL methods has dramatically improved the performance over many conventional machine learning methods on tasks, such as speech recognition [20], image captioning[21, 22], and question answering [23]. The most important building blocks of DL are the Convolutional Neural Networks (CNN) [24], and the Recurrent Neural Networks (RNNs). Also worth mentioning is the improvement of RNNs with the introduction of Long Short-Term Memory Units (LSTMs) [25], which has made the analysis of time series using DL easier and more performant.

Unfortunately DL methods are prone to overfit especially in tasks such as price regression and many works exist trying to prevent such overfitting [26, 27]. Some might attribute overfitting to the lack of huge amounts of data that other tasks such as image and speech processing have available to them. A very rich data source for financial forecasting is the Limit Order Book. One of the few applications of ML in high frequency Limit Order Book data is [8], where several handcrafted features are created, including price deltas, bid-ask spreads and price and volume derivatives. An SVM is then trained to predict the direction of future mid price movements using all the handcrafted features. In [28] a neural network architecture incorporating the idea of bilinear projection augmented with a temporal attention mechanism is used to predict LOB mid price.

Similarly in [29, 30] utilize the Limit Order Book data along with ML methods such as multilinear methods and smart feature selection to predict the future price movements. In our previous work [31,

9, 32] we introduced a large-scale high-frequency Limit Order Book dataset, that is also used in this paper, and we employed three simple DL models, the Convolutional Neural Networks (CNN), the Long-Short Term Memory Recurrent Neural Networks (LSTM RNNs) and the Neural Bag-ofFeatures (N-BoF) model, to tackle the problem of forecasting the mid price movements. However, these approaches directly used the non-stationary raw Order Book data, making them vulnerable to distribution shifts and harming their ability to generalize on unseen data, as we also experimentally demonstrate in this paper.

To the best of our knowledge this is the first work that proposes a structured approach for extracting stationary price features from the Limit Order Book that can be effectively combined with Deep Learning models. We also provide an extensive evaluation of the proposed methods on a large-scale dataset with more than 4 million events. Also, a powerful model, that combines the CNN feature extraction properties with the LSTM's time series modelling capabilities, is proposed in order to improve the accuracy of predicting the price movement of stocks. The proposed combined model is also compared with the previously introduced methods using the proposed stationary price features.

## 3. Limit Order Book Data

In an order-driven financial market, a market participant can place two types of buy/sell orders. By posting a limit order , a trader promises to buy (sell) a certain amount of an asset at a specified price or less (more). The limit order book compromises on the valid limit order that are not executed or cancelled yet.

This Limit Order Book (LOB) contains all existing buy and sell orders that have been submitted and are awaiting to be executed. A limit order is placed on the queue at a given price level, where, in the case of standard limit orders, the execution priority at a given price level is dictated by the arrival time (first in, first out). A market order is is an order to immediately buy/sell a certain quantity of the asset at the best available price in the limit order book. If the requested price of a limit order is far from the best prices, it may take a long time for the execution of the limit order, in which case, the order can finally be cancelled by the trader. The orders are split between two sides, the bid (buy) and the ask (sell) side. Each side contains the orders sorted by their price, in descending order for the bid side and ascending order for the ask side.

Following the notation used in [5], a price grid is defined as { ρ (1) ( t ) , . . . , ρ ( n ) ( t ) } , where ρ ( j ) ( t ) &gt; ρ ( i ) ( t ) for all j &gt; i . The price grid contains all possible prices and each consecutive price level is incremented by a single tick from the previous price level. The state of the order book is a continuous-time process v ( t ) ≡ ( v (1) ( t ) , v (2) ( t ) , . . . , v ( n ) ( t ) ) t ≥ 0 , where | v ( i ) ( t ) | is the number of outstanding limit orders at price ρ ( i ) ( t ), 1 ≤ i ≤ n . If v ( i ) ( t ) &lt; 0, then there are -v ( i ) ( t ) bid orders at price ρ ( i ) ( t ); if v ( i ) ( t ) &gt; 0, then there are v ( i ) ( t ) ask orders at price ρ ( i ) ( t ). That is, v ( i ) ( t ) &gt; 0 refers to ask orders and v ( i ) ( t ) &lt; 0 bid orders.

The location of the best ask price in the price grid is defined by:

<!-- formula-start id="ref_tsantekidis_stationary_lob_1810.09965:formula:0001" status="verified_source" source-page="4" -->
$$
i_a^{(1)}(t) = \inf\{i = 1, \dots, n\ ;\ v^{(i)}(t)>0 \},
$$
![Source formula ref_tsantekidis_stationary_lob_1810.09965:formula:0001](images/formula_0001.png)
*Formula quality: `verified_source`; source PDF page 4. Matched to exact arXiv source 1810.09965v1 at conv_lstm_main.tex:113 (score=0.8125).*
<!-- formula-end -->

and, correspondingly, the location of the best bid price is defined by:

<!-- formula-start id="ref_tsantekidis_stationary_lob_1810.09965:formula:0002" status="verified_source" source-page="4" -->
$$
i_b^{(1)}(t) = \sup\{i = 1, \dots, n\ ;\ v^{(i)}(t)<0 \}.
$$
![Source formula ref_tsantekidis_stationary_lob_1810.09965:formula:0002](images/formula_0002.png)
*Formula quality: `verified_source`; source PDF page 4. Matched to exact arXiv source 1810.09965v1 at conv_lstm_main.tex:117 (score=0.8125).*
<!-- formula-end -->

For simplicity, we denote the best ask and bid prices as p (1) a ( t ) ≡ ρ ( i (1) a ( t ) ) ( t ) and p (1) b ( t ) ≡ ρ ( i (1) b ( t ) ) ( t ), respectively. Notice that if there are no ask (bid) orders in the book, the ask (bid) price is not defined.

More generally, given that the k th best ask and bid prices exist, their locations are denoted as i ( k ) a ( t ) ≡ i a ( t )+ k -1 and i ( k ) b ( t ) ≡ i b ( t )+ k -1. The k th best ask and bid prices are correspondingly denoted by p ( k ) a ( t ) ≡ ρ ( i ( k ) a ( t ) ) ( t ) and p ( k ) b ( t ) ≡ ρ ( i ( k ) b ( t ) ) ( t ), respectively. Correspondingly, we denote the number of outstanding limit orders at the k th best ask and bid levels by ν ( k ) a ( t ) ≡ v ( i ( k ) a ( t ) ) ( t ) and ν ( k ) b ( t ) ≡ v ( i ( k ) b ( t ) ) ( t ), respectively.

Limit Order Book data can be used for a variety of tasks, such as the estimation of the future price trend or the regression of useful metrics, like the price volatility. Other possible tasks may include the early prediction of anomalous events, like extreme changes in price which may indicate manipulation in the markets. These examples are a few of multiple applications which can aid investors to protect their capital when unfavourable conditions exist in the markets or, in other cases, take advantage of them to profit.

Most modern methods that utilize financial time series data employ subsampling techniques, such as the well-known OHLC (Open-High-Low-Close) candles [33], in order to reduce the number of features of each time interval. Although the OHLC candles preserve useful information, such as the market trend and movement ranges within the specified intervals, it removes possibly important microstructure information. Since the LOB is constantly receiving new orders in inconsistent intervals, it is not possible to subsample time-interval features from it in a way that preserves all the information it contains. This problem can be addressed, to some extent, using recurrent neural network architectures, such as LSTMs, that are capable of natively handling inputs of varying size. This allows to directly utilize the data fully without using a time interval-based subsampling.

The LOB data used in this work is provided by Nasdaq Nordic and consists of 10 days worth of LOB events for 5 different Finnish company stocks, namely Kesko Oyj, Outokumpu Oyj, Sampo, Rautaruukki and Wartsila Oyj [34, 35]. The exact time period of the gathered data begins from the 1st of June 2010 to the 14th of June 2010. Also, note that trading only happens during business days.

The data consists of consecutive snapshots of the LOB state after each state altering event takes place. This event might be an order insertion, execution or cancellation and after it interacts with the LOB and change its state a snapshot of the new state is taken. The LOB depth of the data that are used is 10 for each side of Order Book, which ends up being 10 active orders (consisting of price and volume) for each side adding up to a total of 40 values for each LOB snapshot. This ends up summing to a total of 4 . 5 million snapshots that can be used to train and evaluate the proposed models.

In this work the task we aim to accomplish is the prediction of price movements based on current and past changes occurring in the LOB. This problem is formally defined as follows: Let x ( t ) ∈ R q denote the feature vector that describes the condition of the LOB at time t for a specific stock, where q is the dimensionality of the corresponding feature vector. The direction of the mid-price of that stock is defined as l k ( t ) = {-1 , 0 , 1 } depending on whether the mid price decreased (-1), remained stationary (0) or increased (1) after k LOB events occurred. The number of orders k is also called prediction horizon . We aim to learn a model f k ( x ( t )), where f k : R n →{-1 , 0 , 1 } , that predicts the direction l k ( t ) of the mid-price after k orders. In the following Section the aforementioned features and labels, as well as the procedure to calculate them are explained in depth.

## 4. Stationary Feature and Label Extraction

The raw LOB data cannot be directly used for any ML task without some kind of preprocessing. The order volume values can be gathered for all stocks' LOBs and normalized together, since they are expected to follow the same distribution. However, this is not true for price values, since the value of a stock or asset may fluctuate and increase with time to never before seen levels. This means that the statistics of the price values can change significantly with time, rendering the price time series non-stationary.

Simply normalizing all the price values will not resolve the non-stationarity, since there will always be unseen data that may change the distribution of values to ranges that are not present in the current data. We present two solutions for this problem, one used in past work where normalization is applied constantly using past available statistics and a new approach to completely convert the price data to stationary values.

## 4.1. Input Normalization

The most common normalization scheme is standardization (z-score):

<!-- formula-start id="ref_tsantekidis_stationary_lob_1810.09965:formula:0003" status="verified_source" source-page="6" -->
$$
x_{\text{norm}} = \dfrac{{x} - \bar{x}}{\sigma_{\bar{x}}}
,
$$
![Source formula ref_tsantekidis_stationary_lob_1810.09965:formula:0003](images/formula_0003.png)
*Formula quality: `verified_source`; source PDF page 6. Matched to exact arXiv source 1810.09965v1 at conv_lstm_main.tex:148 (score=0.7027).*
<!-- formula-end -->

where x is a feature to be normalized, ¯ x is the mean and σ ¯ x is the standard deviation across all samples. Such normalization is separately applied to the order size values and the price values. Using this kind of 'global' normalization allows the preservation of the different scales between prices of different stocks, which we are trying to avoid. The solution presented in [31, 9] is to use zscore to normalize each stock-day worth of data with the means and standard deviations calculated using previous day's data of the same stock. This way a major problem is avoided which is the distribution shift in stock prices, that can be caused by events such as stock splits or the large shifts in price that can happen over longer periods of time.

Unfortunately this presents another important issue for learning. The difference between the price values in different LOB levels are almost always minuscule. Since all the price levels are normalized using z-score with the same statistics, extracting features at that scale is hard. In this work we propose a novel approach to remedy this problem. Instead of normalizing the raw values of the LOB depth, we modify the price values to be their percentage difference to the current mid price of the Order Book. This removes the non-stationarity from the price values, makes the feature extraction process easier and significantly improves the performance of ML models, as it is also experimentally demonstrated in Section 6. To compensate for the removal of the price value itself we add an extra value to each LOB depth sample which is the percentage change of the mid price since the previous event.

The mid-price is defined as the mid-point between the best bid and the best ask prices at time t by

<!-- formula-start id="ref_tsantekidis_stationary_lob_1810.09965:formula:0004" status="verified_source" source-page="6" -->
$$
p_m^{(1)} (t) = \dfrac{p_a^{(1)}(t) + p_b^{(1)}(t)}{2}
.
$$
![Source formula ref_tsantekidis_stationary_lob_1810.09965:formula:0004](images/formula_0004.png)
*Formula quality: `verified_source`; source PDF page 6. Matched to exact arXiv source 1810.09965v1 at conv_lstm_main.tex:157 (score=0.4516).*
<!-- formula-end -->

<!-- formula-start id="ref_tsantekidis_stationary_lob_1810.09965:formula:0005" status="text_layer_fallback" source-page="6" -->
![Source formula ref_tsantekidis_stationary_lob_1810.09965:formula:0005](images/formula_0005.png)
```text
PDF text layer: p ′ ( i ) a ( t ) = p ( i ) a ( t ) p m ( t ) -1 , (3)
```
*Formula quality: `text_layer_fallback`; source PDF page 6. No reliable LaTeX decode; use the source crop and PDF text layer together.*
<!-- formula-end -->

<!-- formula-start id="ref_tsantekidis_stationary_lob_1810.09965:formula:0006" status="verified_source" source-page="6" -->
$$
{p'}^{(i)}(t) = \dfrac{p^{(i)}(t)}{p_m(t)} - 1
$$
![Source formula ref_tsantekidis_stationary_lob_1810.09965:formula:0006](images/formula_0006.png)
*Formula quality: `verified_source`; source PDF page 6. Matched to exact arXiv source 1810.09965v1 at conv_lstm_main.tex:195 (score=0.7407).*
<!-- formula-end -->

Let and

<!-- formula-start id="ref_tsantekidis_stationary_lob_1810.09965:formula:0007" status="verified_source" source-page="7" -->
$$
{p'}_m(t) = \dfrac{p_m(t)}{p_m(t-1)} - 1
$$
![Source formula ref_tsantekidis_stationary_lob_1810.09965:formula:0007](images/formula_0007.png)
*Formula quality: `verified_source`; source PDF page 7. Matched to exact arXiv source 1810.09965v1 at conv_lstm_main.tex:199 (score=0.8148).*
<!-- formula-end -->

Equations (3) and (4) serve as statistic features that represent the proportional difference between i th price and the mid-price at time t . Equation (2), on the other hand, serves as a dynamic feature that captures the proportional mid-price movement over the time period (that is, it represents asset's return in terms of mid-prices).

We also use the cumulative sum of the sizes of the price levels as a feature, also know as Total Depth:

<!-- formula-start id="ref_tsantekidis_stationary_lob_1810.09965:formula:0008" status="text_layer_fallback" source-page="7" -->
![Source formula ref_tsantekidis_stationary_lob_1810.09965:formula:0008](images/formula_0008.png)
```text
PDF text layer: ν ′ ( k ) a ( t ) = k ∑ i =1 ν ( i ) a ( t ) (6)
```
*Formula quality: `text_layer_fallback`; source PDF page 7. No reliable LaTeX decode; use the source crop and PDF text layer together.*
<!-- formula-end -->

<!-- formula-start id="ref_tsantekidis_stationary_lob_1810.09965:formula:0009" status="verified_source" source-page="7" -->
$$
\nu'^{(k)}(t) = \sum_{i=1}^k{\nu^{(i)}(t)}
$$
![Source formula ref_tsantekidis_stationary_lob_1810.09965:formula:0009](images/formula_0009.png)
*Formula quality: `verified_source`; source PDF page 7. Matched to exact arXiv source 1810.09965v1 at conv_lstm_main.tex:205 (score=0.6).*
<!-- formula-end -->

where ν ( i ) a ( t ) is number of outstanding limit order at the i th best ask price level and ν ( i ) b ( t ) is number of outstanding limit order at the b th best ask price level.

The proposed stationary features are briefly summarized in Table 1. After constructing these three types of stationary features, each of them is separately normalized using standardization (zscore), as described in (1), and concatenated into a single feature vector x t , where t denotes the time step.

The input used for the time-aware models, such as the CNN, LSTM and CNN-LSTM, is the sequence of vectors X = { x 0 , x 1 , . . . , x w } , where w is the number of total number of events each one represented by a different time step input. For the models that need all the input into a single vector, such as the SVM and MLP models, the matrix X is flatten into a single dimension so it can be used as input for these models.

## 4.2. Labels

The proposed models aim to predict the future movements of the mid price. Therefore, the ground truth labels must be appropriately generated to reflect the future mid price movements. Note that the mid price is a 'virtual' value and no order can be guaranteed to immediately executed if placed at that exact price. However being able to predict its upwards or downwards movement provides a good estimate of the price of the future orders. A set of discrete choices must be constructed from our data to use as target for our classification models. The labels for describing the movement denoted by y t ∈ {-1 , 0 , 1 } , where t denotes the timestep.

Simply using p m ( t + k ) &gt; p m ( t ) to determine the upward direction of the mid price would introduce unmanageable amount of noise, since the smallest change would be registered as an upward or downward movement. To remedy this, in our previous work [31, 9] the noisy changes of the mid price were filtered by employing two averaging filters. One averaging filter was used on a window of size k of the past values of the mid price and another averaging was applied on a future window k :

Table 1: Brief description of each proposed stationary feature

| Feature                | Description                                                                                                                          |
|------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| Price level difference | The difference of each price level to the current mid price, see Eq. (3),(4) p ′ ( i ) ( t ) = p ( i ) ( t ) p m ( t ) - 1           |
| Mid price change       | The change of the current mid price to the mid price of the previous time step, see Eq. (5) p ′ m ( t ) = p m ( t ) p m ( t - 1) - 1 |
| Depth size cumsum      | Total depth at each price level, see Eq. (6), (7) ν ′ ( k ) ( t ) = k ∑ i =1 ν ( i ) ( t )                                           |

<!-- formula-start id="ref_tsantekidis_stationary_lob_1810.09965:formula:0010" status="text_layer_fallback" source-page="8" -->
![Source formula ref_tsantekidis_stationary_lob_1810.09965:formula:0010](images/formula_0010.png)
```text
PDF text layer: m b ( t ) = 1 k +1 k ∑ i =0 p m ( t -i ) (8)
```
*Formula quality: `text_layer_fallback`; source PDF page 8. No reliable LaTeX decode; use the source crop and PDF text layer together.*
<!-- formula-end -->

<!-- formula-start id="ref_tsantekidis_stationary_lob_1810.09965:formula:0011" status="text_layer_fallback" source-page="8" -->
![Source formula ref_tsantekidis_stationary_lob_1810.09965:formula:0011](images/formula_0011.png)
```text
PDF text layer: m a ( t ) = 1 k k ∑ i =1 p m ( t + i ) (9)
```
*Formula quality: `text_layer_fallback`; source PDF page 8. No reliable LaTeX decode; use the source crop and PDF text layer together.*
<!-- formula-end -->

where p t is the mid price as described in Equation (2). The label l t , that expresses the direction of price movement at time t , is extracted by comparing the previously defined quantities ( m b and m a ). However, using the m b values to create labels for the samples, as in [31, 9], is making the problem significantly easier and predictable due to the slower adaptation of the mean filter values to sudden changes in price. Therefore, in this work we remedy this issue by replacing m b with the mid price. Therefore, the labels are redefined as:

<!-- formula-start id="ref_tsantekidis_stationary_lob_1810.09965:formula:0012" status="verified_source" source-page="8" -->
$$
l_t =
\begin{cases}
 1, & \text{if } \dfrac{m_a(t)}{p_m(t)} > 1 + \alpha
\vspace{0.2cm}\\
-1, & \text{if } \dfrac{m_a(t)}{p_m(t)} < 1 - \alpha
\vspace{0.2cm}\\
 0, & \text{otherwise}
\end{cases}
$$
![Source formula ref_tsantekidis_stationary_lob_1810.09965:formula:0012](images/formula_0012.png)
*Formula quality: `verified_source`; source PDF page 8. Matched to exact arXiv source 1810.09965v1 at conv_lstm_main.tex:226 (score=0.7368).*
<!-- formula-end -->

where α is the threshold that determines how significant a mid price change m a ( t ) must be in order to label the movement as upward or downward. Values that do not satisfy this inequality are considered as insignificant and are labeled as having no price movement, or in other words being 'stationary'. The resulting labels present the trend to be predicted. This process is applied across all time steps of the dataset to produce labels for all the depth samples.

Figure 1: A visual representation of the evaluated CNN model. Each layer includes the filter input size and the number of filters used.

![Image](images/image_000000_7c45a394aaf830171836eba242b80135188f307ead9d7bde1d4bd4d74fd58a79.png)

## 5. Machine Learning Models

In this section we explain the particular inner workings of the CNN and LSTM models that are used and present how they are combined to form the proposed CNN-LSTM model. The technical details of each model are explained along with the employed optimization procedure.

## 5.1. Convolutional Neural Networks

Convolutional Neural Networks (CNNs) consist of the sequential application of convolutional and pooling layers usually followed by some fully connected layers, as shown in Figure 1. Each convolutional layer i is equipped with a set of filters W i ∈ R S × D × N that is convolved with an input tensor, where S is the number of used filters, D is the filter size, and N is the number of the input channels. The input tensor X ∈ R ( B × T × F ) is consisted by the temporally ordered features described in Section 4.1, where B is the batch size, T is the number of time steps and F is the number of features per time step.

In this work we leverage the causal padding introduced in [3] to avoid using future information to produce features for the current time step. Using a series of convolutional layers allows for capturing the fine temporal dynamics of the time series as well as correlating temporally distant features. After the last convolutional/pooling layer a set of fully connected layers are used to classify the input time series. The network's output expresses the categorical distribution for the three direction labels (upward, downward and stationary), as described in (10), for each time-step.

We also employ a temporal batching technique, similar to the one used in LSTMs, to increase the computational efficiency and reduce memory requirements of our experiments when training with CNNs. Given the above described input tensor X and convolution filters W i the last convolution produces a tensor with dimensions ( B,T,S,N ), which in most uses cases is flattened to a tensor of size ( B,T × S × N ) before being fed to a fully connected layer. Instead we retain the temporal ordering by only reducing the tensor to dimension ( B,T,S × N ). An identical fully connected network with a softmax output is applied for each S × N vectors leading to T different predictions.

Since we are using causal convolutions with 'full' padding, all the convolutional layers produce the same time steps T , hence we do not need to worry about label alignment to the correct time step. Also the causal convolutions ensure that no information from the future leaks to past time step filters. This technique reduces the receptive field of the employed CNN, but this can be easily remedied by using a greater number of convolutional layers and/or a larger filter size D .

## 5.2. Long Short Term Memory Recurrent Neural Networks

One of the most appropriate Neural Network architectures to apply on time series is the Recurrent Neural Network (RNN) architecture. Although powerful in theory, this type of network suffers from the vanishing gradient problem, which makes the gradient propagation through a large number of steps impossible. An architecture that was introduced to solve this problem is the Long Short Term Memory (LSTM) networks [25]. This architecture protects its hidden activation from the decay of unrelated inputs and gradients by using gated functions between its 'transaction' points. The protected hidden activation is the 'cell state' which is regulated by said gates in the following manner:

<!-- formula-start id="ref_tsantekidis_stationary_lob_1810.09965:formula:0013" status="text_layer_fallback" source-page="10" -->
![Source formula ref_tsantekidis_stationary_lob_1810.09965:formula:0013](images/formula_0013.png)
```text
PDF text layer: f t = σ ( W xf · x + W hf · h t -1 + b f ) (11)
```
*Formula quality: `text_layer_fallback`; source PDF page 10. No reliable LaTeX decode; use the source crop and PDF text layer together.*
<!-- formula-end -->

<!-- formula-start id="ref_tsantekidis_stationary_lob_1810.09965:formula:0014" status="text_layer_fallback" source-page="10" -->
![Source formula ref_tsantekidis_stationary_lob_1810.09965:formula:0014](images/formula_0014.png)
```text
PDF text layer: i t = σ ( W xi · x + W hi · h t -1 + b i ) (12)
```
*Formula quality: `text_layer_fallback`; source PDF page 10. No reliable LaTeX decode; use the source crop and PDF text layer together.*
<!-- formula-end -->

<!-- formula-start id="ref_tsantekidis_stationary_lob_1810.09965:formula:0015" status="text_layer_fallback" source-page="10" -->
![Source formula ref_tsantekidis_stationary_lob_1810.09965:formula:0015](images/formula_0015.png)
```text
PDF text layer: c ′ t = tanh ( W hc · h t -1 + W xc · x t + b c ) (13)
```
*Formula quality: `text_layer_fallback`; source PDF page 10. No reliable LaTeX decode; use the source crop and PDF text layer together.*
<!-- formula-end -->

<!-- formula-start id="ref_tsantekidis_stationary_lob_1810.09965:formula:0016" status="text_layer_fallback" source-page="10" -->
![Source formula ref_tsantekidis_stationary_lob_1810.09965:formula:0016](images/formula_0016.png)
```text
PDF text layer: c t = f t · c t -1 + i t · c ′ t (14)
```
*Formula quality: `text_layer_fallback`; source PDF page 10. No reliable LaTeX decode; use the source crop and PDF text layer together.*
<!-- formula-end -->

<!-- formula-start id="ref_tsantekidis_stationary_lob_1810.09965:formula:0017" status="text_layer_fallback" source-page="10" -->
![Source formula ref_tsantekidis_stationary_lob_1810.09965:formula:0017](images/formula_0017.png)
```text
PDF text layer: o t = σ ( W oc · c t + W oh · h t -1 + b o ) (15)
```
*Formula quality: `text_layer_fallback`; source PDF page 10. No reliable LaTeX decode; use the source crop and PDF text layer together.*
<!-- formula-end -->

<!-- formula-start id="ref_tsantekidis_stationary_lob_1810.09965:formula:0018" status="text_layer_fallback" source-page="10" -->
![Source formula ref_tsantekidis_stationary_lob_1810.09965:formula:0018](images/formula_0018.png)
```text
PDF text layer: h t = o t · σ ( c t ) (16)
```
*Formula quality: `text_layer_fallback`; source PDF page 10. No reliable LaTeX decode; use the source crop and PDF text layer together.*
<!-- formula-end -->

where f t , i t and o t are the activations of the input, forget and output gates at time-step t , which control how much of the input and the previous state will be considered and how much of the cell state will be included in the hidden activation of the network. The protected cell activation at time-step t is denoted by c t , whereas h t is the activation that will be given to other components of the model. The matrices W xf , W hf , W xi , W hi , W hc , W xc , W oc , W oh are used to denote the weights connecting each of the activations with the current time step inputs and the previous time step activations.

## 5.3. Combination of models (CNN-LSTM)

We also introduce a powerful combination of the two previously described models. The CNN model is identically applied as described in Section 5.1, using causal convolutions and temporal batching to produce a set of features for each time step. In essence the CNN acts as the feature extractor of the LOB depth time series, which produces a new time series of features with the same length as the original one, with each of them having time steps corresponding to one another.

An LSTM layer is then applied on the time series produced by the CNN, and in turn produces a label for each time step. This works in a very similar way to the fully connected layer described in 5.1 for temporal batching, but instead of the Fully Connected layer the LSTM allows the model to incorporate the features from past steps. The model architecture is visualized in Figure 2.

## 5.4. Optimization

The parameters of the models are learned by minimizing the categorical cross entropy loss defined as:

<!-- formula-start id="ref_tsantekidis_stationary_lob_1810.09965:formula:0019" status="verified_source" source-page="11" -->
$$
\mathcal{L}(\mathbf{W}) = -\sum_{i=1}^{L} y_i \cdot \log \hat{y}_i,
$$
![Source formula ref_tsantekidis_stationary_lob_1810.09965:formula:0019](images/formula_0019.png)
*Formula quality: `verified_source`; source PDF page 11. Matched to exact arXiv source 1810.09965v1 at conv_lstm_main.tex:289 (score=0.6667).*
<!-- formula-end -->

where L is the number of different labels and the notation W is used to refer to the parameters of the models. The ground truth vector is denoted by y , while ˆ y is the predicted label distribution. The loss is summed over all samples in each batch. Due to the unavoidable class imbalance of this type of dataset, a weighted loss is employed to improve the mean recall and precision across all classes:

<!-- formula-start id="ref_tsantekidis_stationary_lob_1810.09965:formula:0020" status="verified_source" source-page="11" -->
$$
\mathcal{L}(\mathbf{W}) = -\sum_{i=1}^{L} c_{y_i} \cdot y_i \cdot \log \hat{y}_i,
$$
![Source formula ref_tsantekidis_stationary_lob_1810.09965:formula:0020](images/formula_0020.png)
*Formula quality: `verified_source`; source PDF page 11. Matched to exact arXiv source 1810.09965v1 at conv_lstm_main.tex:293 (score=0.6538).*
<!-- formula-end -->

where c y i is the assigned weight for the class of y i . The individual weight c i assigned to each class i is calculated as:

<!-- formula-start id="ref_tsantekidis_stationary_lob_1810.09965:formula:0021" status="verified_source" source-page="11" -->
$$
c_i = \dfrac{|\mathcal{D}|}{n \cdot |\mathcal{D}_i|},
$$
![Source formula ref_tsantekidis_stationary_lob_1810.09965:formula:0021](images/formula_0021.png)
*Formula quality: `verified_source`; source PDF page 11. Matched to exact arXiv source 1810.09965v1 at conv_lstm_main.tex:298 (score=0.5714).*
<!-- formula-end -->

where |D| is the total number of samples in our dataset D , n is the total number of classes (which in our case is 3) and D i is set of samples from our dataset that have been labeled to belong in class i .

The most commonly used method to minimize the loss function defined in (18) and learn the parameters W of the model is gradient descent [36]:

<!-- formula-start id="ref_tsantekidis_stationary_lob_1810.09965:formula:0022" status="verified_source" source-page="11" -->
$$
\mathbf{W}' = \mathbf{W} - \eta \cdot \dfrac{\partial \mathcal{L}}{\partial \mathbf{W}}
$$
![Source formula ref_tsantekidis_stationary_lob_1810.09965:formula:0022](images/formula_0022.png)
*Formula quality: `verified_source`; source PDF page 11. Matched to exact arXiv source 1810.09965v1 at conv_lstm_main.tex:305 (score=0.2692).*
<!-- formula-end -->

where W ′ are the parameters of the model after each gradient descent step and η is the learning rate. In this work we utilize the RMSProp optimizer [37], which is an adaptive learning rate method and has been shown to improve the training time and performance of DL models.

The LSTM, CNN and CNN-LSTM models along with all the training algorithms were developed using Keras [38], which is a framework built on top of the Tensorflow library [39].

## 6. Experimental Evaluation

All the models were tested for step sizes k = 10 , 50 , 100 , and 200 in (9), where the α value for each was set at 2 × 10 -5 , 9 × 10 -5 , 3 × 10 -4 and 3 . 5 × 10 -4 respectively. The parameter α was chosen in conjunction with the future horizon with the aim to have relatively balanced distribution of labels across classes. In a real trading scenario it is not possible to have a profitable strategy that creates as many trade signals as 'no-trade' signals, because it would accumulate enormous commission costs. For that reason α is selected with the aim to get a logical ratio of about 20% long, 20% short and 60% stationary labels. The effect of varying the parameter α on the class distribution of labels is shown in Table 2. Note that increasing the α allows for reducing the number of trade signals which should be changed depending on the actual commission and slippage costs that are expected to occur.

Figure 2: CNN-LSTM model

![Image](images/image_000001_5ae69c9985a845ea4dc5686b21e8161c58a5916483d9f37cc9aff2a8d9db789e.png)

Table 2: Example of sample distribution across classes depending on α for prediction horizon k = 100

| α              | Down   | Stationary   | Up     |
|----------------|--------|--------------|--------|
| 1 . 0 × 10 - 5 | 0 . 39 | 0 . 17       | 0 . 45 |
| 2 . 0 × 10 - 5 | 0 . 38 | 0 . 19       | 0 . 43 |
| 5 . 0 × 10 - 5 | 0 . 35 | 0 . 25       | 0 . 41 |
| 1 . 0 × 10 - 4 | 0 . 30 | 0 . 33       | 0 . 36 |
| 2 . 0 × 10 - 4 | 0 . 23 | 0 . 49       | 0 . 28 |
| 3 . 0 × 10 - 4 | 0 . 18 | 0 . 60       | 0 . 22 |
| 3 . 5 × 10 - 4 | 0 . 15 | 0 . 66       | 0 . 19 |

We tested the CNN and LSTM models using the raw features and the proposed stationary features separately and compared the results. The architecture of the three models that were tested is described bellow.

The proposed CNN model consists of the following sequential layers:

1. 1D Convolution with 16 filters of size (10 , 42)
2. 1D Convolution with 16 filters of size (10 , )
3. 1D Convolution with 32 filters of size (8 , )
4. 1D Convolution with 32 filters of size (6 , )
5. 1D Convolution with 32 filters of size (4 , )
6. Fully connected layer with 32 neurons
7. Fully connected layer with 3 neurons

The activation function used for all the convolutional and fully connected layer of the CNN is the Parametric Rectifying Linear Unit (PRELU) [40]. The last layer uses the softmax function for the prediction of the probability distribution between the different classes. All the convolutional layers are followed by a Batch Normalization (BN) layer after them.

Figure 3: Mean cost per recurrent step of the LSTM network

![Image](images/image_000002_3972a1f43676059ebe35643189bc944fd400928e2470cbd853f8b4fcd6571a0a.png)

The LSTM network uses 32 hidden neurons followed by a feed-forward layer with 64 neurons using Dropout and PRELU as activation function. Experimentally we found out that the hidden layer of the LSTM should contain 64 or less hidden neurons to avoid over-fitting the model. Experimenting with higher number of hidden neurons would be feasible if the dataset was even larger.

Finally the CNN-LSTM model applies the convolutional feature extraction layers on the input and then feeds them in the correct temporal order to an LSTM model. The CNN component is comprised of the following layers:

1. 1D Convolution with 16 filters of size (5 , 42)
2. 1D Convolution with 16 filters of size (5 , )
3. 1D Convolution with 32 filters of size (5 , )
4. 1D Convolution with 32 filters of size (5 , )

Note that the receptive field of each convolutional filter in the CNN module is smaller that the standalone CNN, since the LSTM can capture most of the information from past time steps. The LSTM module has the same exact architecture as the standalone LSTM. A visual representation of this CNN-LSTM model is shown in Figure 2. Likewise, PRELU is the activation function used for the CNN and the fully connected layers, while the softmax function is used for the output layer of the network to predict the probability distribution of the classes.

One recurring effect we observe when training LSTM networks on LOB data is that for the first steps of observation the predictions y i yield a bigger cross entropy cost, meaning worse performance in our metrics. We run a set of experiments where the LSTM was trained for all the steps of the input windows T . The resulting mean cost per time step can be observed in Figure 3. As a result, trying to predict the price movement using insufficient past information is not possible and should be avoided since it leads to noisy gradients. To avoid this, a 'burn-in' input is initially used to build its initial perception of the market before actually making correct decisions. In essence the first 'burn-in' steps of the input are skipped, by not allowing any gradient to alter our model until after the 100th time step. We also apply the same method to the CNN-LSTM model.

Table 3: Experimental results for different prediction horizons k . The values that are reported are the mean of each metric for the last 20 training epochs.

| Feature Type               | Model                      | Mean Recall                | Mean Precision             | Mean F1                    | Cohen's κ                  |
|----------------------------|----------------------------|----------------------------|----------------------------|----------------------------|----------------------------|
| Prediction Horizon k = 10  | Prediction Horizon k = 10  | Prediction Horizon k = 10  | Prediction Horizon k = 10  | Prediction Horizon k = 10  | Prediction Horizon k = 10  |
| Raw Values                 | SVM                        | 0 . 35                     | 0 . 43                     | 0 . 33                     | 0 . 04                     |
| Raw Values                 | MLP                        | 0 . 34                     | 0 . 34                     | 0 . 09                     | 0 . 00                     |
| Raw Values                 | CNN                        | 0 . 51                     | 0 . 42                     | 0 . 38                     | 0 . 14                     |
| Raw Values                 | LSTM                       | 0 . 49                     | 0 . 41                     | 0 . 35                     | 0 . 12                     |
| Stationary Features        | SVM                        | 0 . 33                     | 0 . 46                     | 0 . 30                     | 0 . 011                    |
| Stationary Features        | MLP                        | 0 . 34                     | 0 . 35                     | 0 . 09                     | 0 . 00                     |
| Stationary Features        | CNN                        | 0 . 54                     | 0 . 44                     | 0 . 43                     | 0 . 19                     |
| Stationary Features        | LSTM                       | 0 . 55                     | 0 . 45                     | 0 . 42                     | 0 . 18                     |
| Stationary Features        | CNNLSTM                    | 0 . 56                     | 0 . 45                     | 0 . 44                     | 0 . 21                     |
| Prediction Horizon k = 50  | Prediction Horizon k = 50  | Prediction Horizon k = 50  | Prediction Horizon k = 50  | Prediction Horizon k = 50  | Prediction Horizon k = 50  |
| Raw Values                 | SVM                        | 0 . 35                     | 0 . 41                     | 0 . 32                     | 0 . 03                     |
| Raw Values                 | MLP                        | 0 . 41                     | 0 . 38                     | 0 . 21                     | 0 . 04                     |
| Raw Values                 | CNN                        | 0 . 50                     | 0 . 42                     | 0 . 37                     | 0 . 13                     |
| Raw Values                 | LSTM                       | 0 . 46                     | 0 . 40                     | 0 . 34                     | 0 . 10                     |
| Stationary Features        | SVM                        | 0 . 39                     | 0 . 41                     | 0 . 38                     | 0 . 09                     |
|                            | MLP                        | 0 . 49                     | 0 . 43                     | 0 . 38                     | 0 . 14                     |
|                            | CNN                        | 0 . 55                     | 0 . 45                     | 0 . 43                     | 0 . 20                     |
|                            | LSTM                       | 0 . 56                     | 0 . 46                     | 0 . 44                     | 0 . 21                     |
|                            | CNNLSTM                    | 0 . 56                     | 0 . 47                     | 0 . 47                     | 0 . 24                     |
| Prediction Horizon k = 100 | Prediction Horizon k = 100 | Prediction Horizon k = 100 | Prediction Horizon k = 100 | Prediction Horizon k = 100 | Prediction Horizon k = 100 |
| Raw Values                 | SVM                        | 0 . 35                     | 0 . 46                     | 0 . 33                     | 0 . 05                     |
| Raw Values                 | MLP                        | 0 . 45                     | 0 . 39                     | 0 . 26                     | 0 . 06                     |
| Raw Values                 | CNN                        | 0 . 49                     | 0 . 42                     | 0 . 37                     | 0 . 12                     |
| Raw Values                 | LSTM                       | 0 . 45                     | 0 . 39                     | 0 . 34                     | 0 . 09                     |
| Stationary Features        | SVM                        | 0 . 36                     | 0 . 46                     | 0 . 35                     | 0 . 07                     |
|                            | MLP                        | 0 . 50                     | 0 . 43                     | 0 . 39                     | 0 . 14                     |
|                            | CNN                        | 0 . 54                     | 0 . 46                     | 0 . 44                     | 0 . 21                     |
|                            | LSTM                       | 0 . 56                     | 0 . 46                     | 0 . 44                     | 0 . 20                     |
|                            | CNNLSTM                    | 0 . 55                     | 0 . 47                     | 0 . 48                     | 0 . 24                     |
| Prediction Horizon k = 200 | Prediction Horizon k = 200 | Prediction Horizon k = 200 | Prediction Horizon k = 200 | Prediction Horizon k = 200 | Prediction Horizon k = 200 |
| Raw Values                 | SVM                        | 0 . 35                     | 0 . 44                     | 0 . 31                     | 0 . 04                     |
| Raw Values                 | MLP                        | 0 . 44                     | 0 . 40                     | 0 . 32                     | 0 . 08                     |
| Raw Values                 | CNN                        | 0 . 47                     | 0 . 43                     | 0 . 39                     | 0 . 14                     |
| Raw Values                 | LSTM                       | 0 . 42                     | 0 . 39                     | 0 . 36                     | 0 . 08                     |
| Stationary Features        | SVM                        | 0 . 38                     | 0 . 46                     | 0 . 36                     | 0 . 10                     |
|                            | MLP                        | 0 . 49                     | 0 . 45                     | 0 . 42                     | 0 . 17                     |
|                            | CNN                        | 0 . 51                     | 0 . 47                     | 0 . 45                     | 0 . 20                     |
|                            | LSTM                       | 0 . 52                     | 0 . 47                     | 0 . 46                     | 0 . 22                     |
|                            | CNNLSTM                    | 0 . 53                     | 0 . 48                     | 0 . 49                     | 0 . 25                     |

Figure 4: F1 and Cohen's κ metrics during training for prediction horizon k = 100. Plots are smoothed with a mean filter with window=3 to reduce fluctuations.

![Image](images/image_000003_7a1dc729178c3f2daeea05ab51aeec1fd61b460df52acd66a1e56813e82a12a3.png)

For training the models, the dataset is split as follows. The first 7 days of each stock are used to train the models, while the final 3 days are used as test data. The experiments were conducted for 4 different prediction horizons k , as defined in (9) and (10).

Performance is measured using Cohen's kappa [41], which is used to evaluate the concordance between sets of given answers, taking into consideration the possibility of random agreements happening. The mean recall, mean precision and mean F1 score between all 3 classes is also reported. Recall is the number of true positives samples divided by the sum of true positives and false negatives, while precision is the number of true positive divided by the sum of true positives and false positives. F1 score is the harmonic mean of the precision and recall metrics.

The results of the experiments are shown in Table 3. The results are compared for the models trained on the raw price features with the ones trained using the extracted stationary features. The results confirm that extracting stationary features from the data significantly improve performance of Deep Learning models such as CNNs and LSTMs.

We also trained a Linear SVM model and a simple MLP model and compared them to the DL models. The SVM model was trained using Stochastic Gradient Descent since the size of the dataset is too large to use a regular Quadratic Programming solver. The SVM model implementation is provided by the sklearn library [42]. The MLP model consists of three fully connected layers with sizes 128, 64, 32, and PRELU as activations for each layers. Dropout is also used to avoid overfitting and the softmax activation function was used in the last layer.

Since both the SVM and the MLP models cannot iterate over timesteps to gain the same amount of information as the CNN and LSTM-based models, a window of 50 depth events is used and is flattened into a single sample. This process is applied in a rolling fashion for all the dataset to generate a dataset upon which the two models can be trained. One important note is the training fluctuations that are observed in Figure 4, which are caused by the great class imbalance. Similar issues where observed in initial experiments with CNN and LSTM models but using the weighted loss described in 5.4 the fluctuations subsided.

The proposed stationary price features significantly outperform the raw price features for all the tested models. This can be attributed to a great extent to the stationary nature of the proposed features. The employed price differences provide an intrinsically stationary and normalized price measure that can be directly used. This is in contrast with the raw price values that requires careful normalization to ensure that their values remain into a reasonable range and suffer for significantly non-stationarity issues when the price increases to levels not seen before. By converting the actual prices to the their difference to the mid price and normalize that, this important feature is exaggerated to avoid being suppressed by the much larger price movements through time. The proposed combination model CNN-LSTM also outperforms its separated individual component models as shown in Figure 4 and Table 3 showing that it can better handle the LOB data and use them to take advantage of the microstructure existing within the data to produce more accurate predictions.

## 7. Conclusion

In this paper we proposed a novel method for extracting stationary features from raw LOB data, suitable for use with different DL models. Using different ML models, i.e., SVMs, MLPs, CNNs and LSTMs, it was experimentally demonstrated that the proposed features significantly outperform the raw price features. The proposed stationary features achieve this by making the difference between the prices in the LOB depth the main metric instead of the price itself, which usually fluctuates much more through time than the price level within the LOB. A novel combined CNN-LSTM model was also proposed for time series predictions and it was demonstrated that exhibits more stable behaviour and leads to better results that the CNN and LSTM models.

There are several interesting future research directions. As with all the DL application, more data would enable the use of bigger models that would not be at risk of being overtrained as it was observed in this work. An RNN-type of network could be also used to perform a form of 'intelligent' r-sampling extracting useful features from a specific and limited time-interval of depth events, which would avoid losing information and allow for the later models produce prediction for a certain time period and not for a number of following events. Another important addition would be an attention mechanism [21], [43], which would allow for the better observation of the features by the network allowing it to ignore noisy parts of the data and use only the relevant information.

## Acknowledgment

The research leading to these results has received funding from the H2020 Project BigDataFinance MSCA-ITN-ETN 675044 (http://bigdatafinance.eu), Training for Big Data in Financial Research and Risk Management.

## References

- [1] H. Deng, L. Zhang, X. Shu, Feature memory-based deep recurrent neural network for language modeling, Applied Soft Computing 68 (2018) 432-446.
- [2] M. Larsson, Y. Zhang, F. Kahl, Robust abdominal organ segmentation using regional convolutional neural networks, Applied Soft Computing.
- [3] A. Van Den Oord, S. Dieleman, H. Zen, K. Simonyan, O. Vinyals, A. Graves, N. Kalchbrenner, A. Senior, K. Kavukcuoglu, Wavenet: A generative model for raw audio, arXiv preprint arXiv:1609.03499.
- [4] F. Black, M. Scholes, The pricing of options and corporate liabilities, Journal of Political Economy 81 (3) (1973) 637-654.

- [5] R. Cont, S. Stoikov, R. Talreja, A stochastic model for order book dynamics, Operations research 58 (3) (2010) 549-563.
- [6] F. M. Bandi, R. Ren` o, Price and volatility co-jumps, Journal of Financial Economics 119 (1) (2016) 107-146.
- [7] Y. A¨ ıt-Sahalia, P. A. Mykland, Estimating volatility in the presence of market microstructure noise: A review of the theory and practical considerations, in: Handbook of financial time series, Springer, 2009, pp. 577-598.
- [8] A. N. Kercheval, Y. Zhang, Modelling high-frequency limit order book dynamics with support vector machines, Quantitative Finance 15 (8) (2015) 1315-1329.
- [9] A. Tsantekidis, N. Passalis, A. Tefas, J. Kanniainen, M. Gabbouj, A. Iosifidis, Using deep learning to detect price change indications in financial markets, in: Proceedings of the European Signal Processing Conference, 2017, pp. 2511-2515.
- [10] V. Vapnik, I. Guyon, T. Hastie, Support vector machines, Mach. Learn 20 (3) (1995) 273-297.
- [11] A. Kazem, E. Sharifi, F. K. Hussain, M. Saberi, O. K. Hussain, Support vector regression with chaos-based firefly algorithm for stock market price forecasting, Applied soft computing 13 (2) (2013) 947-958.
- [12] T.-J. Hsieh, H.-F. Hsiao, W.-C. Yeh, Forecasting stock markets using wavelet transforms and recurrent neural networks: An integrated system based on artificial bee colony algorithm, Applied soft computing 11 (2) (2011) 2510-2525.
- [13] L. Lei, Wavelet neural network prediction method of stock price trend based on rough set attribute reduction, Applied Soft Computing 62 (2018) 923-932.
- [14] K. Michell, et al., A stock market risk forecasting model through integration of switching regime, anfis and garch techniques, Applied Soft Computing 67 (2018) 106-116.
- [15] C.-F. Huang, A hybrid stock selection model using genetic algorithms and support vector regression, Applied Soft Computing 12 (2) (2012) 807-818.
- [16] S. Galeshchuk, Neural networks performance in exchange rate prediction, Neurocomputing 172 (2016) 446-452.
- [17] J. Heaton, N. Polson, J. Witte, Deep portfolio theory, arXiv preprint arXiv:1605.07230.
- [18] L. Takeuchi, Y.-Y. A. Lee, Applying deep learning to enhance momentum trading strategies in stocks.
- [19] R. Xiong, E. P. Nichols, Y. Shen, Deep learning stock volatility with google domestic trends, arXiv preprint arXiv:1512.04916.
- [20] A. Graves, A.-r. Mohamed, G. Hinton, Speech recognition with deep recurrent neural networks, in: Proceedings of the IEEE International Conference on Acoustics, Speech and Signal Processing, 2013, pp. 6645-6649.

- [21] K. Xu, J. Ba, R. Kiros, K. Cho, A. C. Courville, R. Salakhutdinov, R. S. Zemel, Y. Bengio, Show, attend and tell: Neural image caption generation with visual attention., in: Proceedings of the International Conference on Machine Learning, Vol. 14, 2015, pp. 77-81.
- [22] J. Mao, W. Xu, Y. Yang, J. Wang, Z. Huang, A. Yuille, Deep captioning with multimodal recurrent neural networks (m-rnn), arXiv preprint arXiv:1412.6632.
- [23] Y. Zhu, O. Groth, M. Bernstein, L. Fei-Fei, Visual7w: Grounded question answering in images, in: Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition, 2016, pp. 4995-5004.
- [24] Y. LeCun, Y. Bengio, et al., Convolutional networks for images, speech, and time series, The handbook of brain theory and neural networks 3361 (10) (1995) 1995.
- [25] S. Hochreiter, J. Schmidhuber, Long short-term memory, Neural Computation 9 (8) (1997) 1735-1780.
- [26] D.-x. Niu, H.-f. Shi, D. D. Wu, Short-term load forecasting using bayesian neural networks learned by hybrid monte carlo algorithm, Applied Soft Computing 12 (6) (2012) 1822-1827.
- [27] L. Xi, H. Muzhou, M. H. Lee, J. Li, D. Wei, H. Hai, Y. Wu, A new constructive neural network method for noise processing and its application on stock market prediction, Applied Soft Computing 15 (2014) 57-66.
- [28] D. T. Tran, A. Iosifidis, J. Kanniainen, M. Gabbouj, Temporal attention augmented bilinear network for financial time-series data analysis, arXiv preprint arXiv:1712.00975.
- [29] A. Ntakaris, J. Kanniainen, M. Gabbouj, A. Iosifidis, Mid-price prediction based on machine learning methods with technical and quantitative indicators.
- [30] D. T. Tran, M. Magris, J. Kanniainen, M. Gabbouj, A. Iosifidis, Tensor representation in highfrequency financial data for price change prediction, in: Computational Intelligence (SSCI), 2017 IEEE Symposium Series on, IEEE, 2017, pp. 1-7.
- [31] A. Tsantekidis, N. Passalis, A. Tefas, J. Kanniainen, M. Gabbouj, A. Iosifidis, Forecasting stock prices from the limit order book using convolutional neural networks, in: Proceedings of the IEEE Conference on Business Informatics, Vol. 1, 2017, pp. 7-12.
- [32] N. Passalis, A. Tsantekidis, A. Tefas, J. Kanniainen, M. Gabbouj, A. Iosifidis, Time-series classification using neural bag-of-features, in: Proceedings of the European Signal Processing Conference, 2017, pp. 301-305.
- [33] D. Yang, Q. Zhang, Drift-independent volatility estimation based on high, low, open, and close prices, The Journal of Business 73 (3) (2000) 477-492.
- [34] A. Ntakaris, M. Magris, J. Kanniainen, M. Gabbouj, A. Iosifidis, Benchmark dataset for midprice prediction of limit order book data, arXiv preprint arXiv:1705.03233.
- [35] M. Siikanen, J. Kanniainen, A. Luoma, What drives the sensitivity of limit order books to company announcement arrivals?, Economics Letters 159 (2017) 65-68.

- [36] P. J. Werbos, Backpropagation through time: what it does and how to do it, Proceedings of the IEEE 78 (10) (1990) 1550-1560.
- [37] T. Tieleman, G. Hinton, Lecture 6.5-rmsprop: Divide the gradient by a running average of its recent magnitude, COURSERA: Neural networks for machine learning 4 (2) (2012) 26-31.
- [38] [F. Chollet, et al., Keras, https://github.com/keras-team/keras (2015).](https://github.com/keras-team/keras)
- [39] M. Abadi, A. Agarwal, P. Barham, E. B. et at., TensorFlow: Large-scale machine learning on heterogeneous systems, software available from tensorflow.org (2015). URL https://www.tensorflow.org/
- [40] K. He, X. Zhang, S. Ren, J. Sun, Delving deep into rectifiers: Surpassing human-level performance on imagenet classification, in: Proceedings of the IEEE International Conference on Computer Vision, 2015, pp. 1026-1034.
- [41] J. Cohen, A coefficient of agreement for nominal scales, Educational and Psychological Measurement 20 (1) (1960) 37-46.
- [42] F. Pedregosa, G. Varoquaux, A. Gramfort, V. Michel, B. Thirion, O. Grisel, M. Blondel, P. Prettenhofer, R. Weiss, V. Dubourg, et al., Scikit-learn: Machine learning in python, Journal of Machine Learning Research 12 (Oct) (2011) 2825-2830.
- [43] K. Cho, A. Courville, Y. Bengio, Describing multimedia content using attention-based encoderdecoder networks, IEEE Transactions on Multimedia 17 (11) (2015) 1875-1886.
