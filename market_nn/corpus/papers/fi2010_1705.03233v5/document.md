# Benchmark Dataset for Mid-Price Forecasting of Limit Order Book Data with Machine Learning Methods

Adamantios Ntakaris a, ∗ , Martin Magris b , Juho Kanniainen b , Moncef Gabbouj a , Alexandros Iosifidis c

a Laboratory of Signal Processing, Tampere University of Technology, Korkeakoulunkatu 1, Tampere, Finland

b Laboratory of Industrial and Information Management, Tampere University of Technology, Korkeakoulunkatu 8, Tampere, Finland

c Department of Engineering, Electrical and Computer Engineering, Aarhus University, Inge Lehmanns Gade 10, Aarhus, Denmark

## Abstract

Managing the prediction of metrics in high-frequency financial markets is a challenging task. An efficient way is by monitoring the dynamics of a limit order book to identify the information edge. This paper describes the first publicly available benchmark dataset of high-frequency limit order markets for mid-price prediction. We extracted normalized data representations of time series data for five stocks from the NASDAQ Nordic stock market for a time period of ten consecutive days, leading to a dataset of ≈ 4,000,000 time series samples in total. A day-based anchored cross-validation experimental protocol is also provided that can be used as a benchmark for comparing the performance of state-of-the-art methodologies. Performance of baseline approaches are also provided to facilitate experimental comparisons. We expect that such a largescale dataset can serve as a testbed for devising novel solutions of expert systems for high-frequency limit order book data analysis.

Keywords: high-frequency trading, limit order book, mid-price, machine learning, ridge regression, single hidden feedforward neural network

## 1. Introduction

Automated trading became a reality when the majority of exchanges adopted it globally. This environment is ideal for high-frequency traders. High-frequency trading (HFT) and a centralized matching engine, referred to as a limit order book (LOB), are the main drivers for generating big data Seddon &amp; Currie (2017). In this paper, we describe a new order book dataset consisting of approximately four million events for ten consecutive trading days for five stocks.

∗ Corresponding author

E-mail address: adamantios.ntakaris@tuni.fi (Adamantios Ntakaris)

The data is derived from the ITCH feed provided by NASDAQ OMX Nordic and consists of the time-ordered sequences of messages that track and record all the events occurring in the specific market. It provides a complete market-wide history of ten trading days. Additionally, we define an experimental protocol to evaluate the performance of research methods in mid-price prediction. 1

Datasets, like the one presented here, come with challenges, including the selection of appropriate data transformation, normalization, description, and classification. This type of massive dataset requires a very good understanding of the available information that can be extracted for further processing. We follow the information edge, as has been recently presented by Kercheval &amp; Zhang (2015). The authors provide a detailed description of representations that can be used for a mid-price movement prediction metric. In light of this data representation, they apply non-linear classification based on support vector machines (SVM) in order to predict the movement of this metric. Such a supervised learning model exploits class labels 2 for short- and long-term prediction. However, they train their model based on a very small (when compared to the size of the data that can be available for such applications) dataset of 4000 samples. This is due to the limitations of many non-linear kernel-based classification models related to their time and space complexity with respect to the training data size. On the other hand, Sirignano (2016) uses large amounts of data for non-linear classification based on a feedforward network. The author takes advantage of the local spatial structure 3 of the data for modelling the joint distribution of the LOB's state based on its current state.

Despite the major importance of publicly available datasets for advancing research in the HFT field, there are no detailed public available benchmark datasets for method evaluation purposes. In this paper, we describe the first publicly available dataset 4 for an LOB-based HFT that has been collected in the hope of facilitating future research in the field. Based on Kercheval &amp; Zhang (2015), we provide time series representations approximately 4 , 000 , 000 trading events and annotations for five classification problems. Baseline results of two widely used methods, i.e. linear and non-linear regression models, are also provided. In this way, we introduce this new problem for the expert systems community and provide a testbed for facilitating future research. We hope that attracting the interest of expert systems will lead to the rapid improvement of the performance achieved in the provided dataset, thus leading to much better state-of-the-art solutions to this important problem.

The dataset described in this paper can be useful for financial expert systems in two ways. First, it can be used to identify circumstances under which markets are stable, which is very important for liquidity providers (market makers) to make the spread. Consequently, such an intelligent system would be valuable as a framework that can increase liquidity provision. Secondly, analysis of the data can be used for model selection by speculative traders, who are trading based on their predictions on market movements. In future research, this paper can be employed to identify order book spoofing, i.e. situations where markets are exposed to manipulation by limit orders. In this case, spoofers could aim to move markets in certain directions by limit orders that are cancelled before they are filled. Therefore, this research is relevant not only for market makers and traders, but also for supervisors and regulators.

1 Mid-price is the average of the best bid and best ask prices.

2 Labels are extracted from annotations provided by experts and represent the direction of the mid-price. Three different states are defined, i.e. upward, downward, and stationary movement.

3 By local movement, the author means that the conditional movement of the future price (e.g. best ask price movement) depends, locally, on the current LOB state.

4 The dataset can be downloaded from: http://urn.fi/urn:nbn:fi:csckata20170601153214969115

Therefore, the present work has the following contributions: 1) To the best of our knownledge this is the first publicly available LOB-ITCH dataset for machine learning experiments on the prediction of mid-price movements. 2) We provide baselines methods based on ridge regression and a new implementation of an RBF neural network based on k-means algorithm. 3) The paper provides information about the prediction of mid-price movements to market makers, traders, and regulators. This paper does not suggest any trading strategies and is reliant on purely machine learning metrics prediction. Overall, this work is an empirical exploration of the challenges that come with high-frequency trading and machine learning applications.

The data from Nasdanq Helsinki Stock Exchange offers important benefits. In the United States the limit orders for a given asset are spread between several exchanges, causing fragmentation of liquidity. The fragmentation poses a problem for empirical research, because, as Gould et al. (2013) point out, the 'differences between different trading platforms' matching rules and transaction costs complicate comparisons between different limit order books for the same asset.' These issues related to fragmentation are not present with data obtained from less fragmented Nasdaq Nordic markets. Moreover, Helsinki Exchange is a pure limit order market, where the market makers have a limited role.

The rest of the paper is organized as follows. We provide a comprehensive literature review of the field in Section 2. Dataset and experimental protocol descriptions are provided in Section 3. Quantitative and qualitative comparisons of the new dataset, along with related data sources, are provided in Section 4. In Section 5, we describe the engineering of our baselines. Section 6 presents our empirical results and Section 7 concludes.

## 2. Machine Learning for HFT and LOB

The complex nature of HFT and LOB spaces is suitable for interdisciplinary research. In this section, we provide a comprehensive review of recent methods exploiting machine learning approaches. Regression models, neural networks, and several other methods have been proposed to make inferences of the stock market. Existing literature ranges metric prediction to optimal trading strategies identification. Research community has tried to tackle the challenges of prediction and data inference from different angles. While mid-price prediction can be considered a traditional time series prediction problem, there are several challenges that justify HFT as a unique problem.

## 2.1. Regression Analysis

Regression models have been widely used for HFT and LOB prediction. Zheng et al. (2012) utilize logistic regression in order to predict the inter-trade price jump. Alvim et al. (2010) use support vector regression (SVR) and partial least squares (PLS) for trading volume forecasting for ten Bovespa stocks. Pai &amp; Lin (2005) use a hybrid model for stock price prediction. They combine an auto-regressive integrated moving average (ARIMA) model and an SVM classifier in order to model non-linearities of class structure in regression estimation models. Liu &amp; Park (2015) develop a multivariate linear model to explain short-term stock price movement where a bid-ask spread is used for classification purposes. Detollenaere &amp; D'hondt (2017) apply an adaptive least absolute shrinkage and selection operator (LASSO) 5 for variable selection, which best explains the transaction cost of the split order. They apply an adjusted ordinal logistic method for classifying ex ante transaction costs into groups. Cenesizoglu et al. (2014) work on a similar problem. They hold that the state of the limit order can be informative for the direction of future prices and try to prove their position by using an autoregressive model.

Panayi et al. (2016) use generalized linear models (GLM) and generalized additive models for location, shape and scale (GAMLSS) models in order to relate the threshold exceedance duration (TED), which measures the length of time required for liquidity replenishment, to the state of the LOB. Yu (ober) tries to extract information from order information and order submission based on the ordered probit model. 6 The author shows, in the case of Shanghai's stock market, that an LOB's information is affected by the trader's strategy, with different impacts on the bid and ask sides. Amaya et al. (2015) use panel regression 7 for order imbalances and liquidity costs in LOBs so as to identify resilience in the market. Their findings show that such order imbalances cause liquidity issues that last for up to ten minutes. Malik &amp; Lon Ng (2014) analyse the asymmetric intra-day patterns of LOBs. They apply regression with a power transformation on the notional volume weighted average price (NVWAP) curves in order to conclude that both sides of the market behave asymmetrically to market conditions. 8 In the same direction, Ranaldo (2004) examines the relationship between trading activity and the order flow dynamics in LOBs, where the empirical investigation is based on a probit model. Cao et al. (2009) examine the depth of different levels of an order book by using an autoregressive (AR) model of order 5 (the AR(5) framework). They find that levels beyond the best bid and best ask prices provide moderate information regarding the true value of an asset. Finally, Creamer (2012) suggests that the LogitBoost algorithm is ideal for selecting the right combination of technical indicators. 9

5 Adaptive weights are used for penalizing different coefficients in the l 1 penalty term.

6 The method is the generalization of a linear regression model when the dependent variable is discrete.

7 Panel regression models provide information on data characteristics individually, but also across both individuals over time.

8 Market conditions of an industry sector have an impact on sellers and buyers who are related to it. Factors to consider include the number of competitors in the sector. For example, if there is a surplus, new companies may find it difficult to enter the market and remain in business.

## 2.2. Neural Networks

HFT is mainly a scalping 10 strategy according to which the chaotic nature of the data creates the proper framework for the application of neural networks. Levendovszky &amp; Kia (2012) propose a multi-layer feedforward neural network for predicting the price of EUR/USD pair, trained by using the backpropagation algorithm. Sirignano (2016) proposes a new method for training deep neural networks that tries to model the joint distribution of the bid and ask depth, where a focal point is the spatial nature 11 of LOB levels. Bogoev &amp; Karam (2016) propose the use of a single-hidden layer feedforward neural (SLFN) network for the detection of quote stuffing and momentum ignition. Dixon (2016) uses a recurrent neural network (RNN) for mid-price predictions of T-bond 12 and ES futures 13 based on ultra-high-frequency data. Rehman et al. (2014) apply recurrent cartesian genetic programming evolved artificial neural network (RCGPANN) for predicting five currency rates against the Australian dollar. Galeshchuk (2016) suggests that a multi-layer perceptron (MLP) architecture, with three hidden layers, is suitable for exchange rate prediction. Majhi et al. (2009) use the Functional Link Artificial Neural Network (FLANN) in order to predict price movements in the DJIA 14 and S&amp;P500 15 stock indices.

Deep belief networks employed by Sharang &amp; Rao (2015) to design a mediumfrequency portfolio trading strategy. Hallgren &amp; Koski (2016) use continuous time bayesian networks (CTBNs) for causality detection. They apply their model on tick-by-tick high frequency foreign exchange (FX) data EUR/USD by using a Skellam process. 16 Sandoval &amp; Hern´ andez (2015) create a profitable trading strategy by combining hierarchical hidden Markov models (HHMM), where they consider wavelet-based LOB information filtering. In their work, they also consider a two-layer feedforward neural network in order to classify the upcoming states. They nevertheless report limitations in the neural network in terms of the volume of the input data.

9 Technical indicators are mainly used for short-term price movement predictions. They are formulas based on historical data.

10 Scalping is a type of trading strategy according to which the trader tries to make a profit for small changes in a stock.

11 The spatial nature of this type of neural network and its gradient can be evaluated at far fewer grid points. This makes the model less computationally expensive. Furthermore, the suggested architecture can model the entire distribution in the R d space.

12 Treasury bond (T-bond) is a long-term fixed interest rate debt security issued by the federal government.

13 E-mini S&amp;P 500 (ES futures) are electronically traded futures contracts whose value is one-fifth that size of standard S&amp;P futures.

14 The Dow Jones Industrial Average (DJIA) is the price-weighted average of the 30 largest, publicly-owned U.S. companies.

15 S&amp;P500 is the index that provides a summary of the overall market by tracking some of the 500 top stocks in U.S. stock market.

16 A Skellam process is defined as S ( t ) = N (1) ( t ) -N (2 ( t ) , t ⩾ 0 where N (1) ( t ) and N (2) ( t ) are two independent homogeneous Poisson processes.

## 2.3. Maximum Margin and Reinforcement Learning

Palguna &amp; Pollak (2016) use nonparametric methods on features derived from LOB, which are incorporated into order execution strategies for mid-price prediction. In the same direction, Kercheval &amp; Zhang (2015) employ a multiclass SVM for mid-price and price spread crossing prediction. Han et al. (2015) base their research on Kercheval &amp; Zhang (2015) by using multi-class SVM for mid-price movement prediction. More precisely, they compare multi-class SVM (exploring linear and RBF kernels) to decision trees using bagging for variance reduction.

Kim (2001) uses input/output hidden Markov models (IOHMMs) and reinforcement learning (RL) in order to identify the order flow distribution and market-making strategies, respectively. Yang et al. (2015) apply apprenticeship learning 17 methods, like linear inverse reinforcement learning (LIRL) and Gaussian process IRL (GPIRL), to recognize traders or algorithmic trades based on the observed limit orders. Chan &amp; Shelton (2001) use RL for market-making strategies, where experiments based on a Monte Carlo simulation and a stateaction-reward-state-action (SARSA) algorithm test the efficacy of their policy. In the same vein, Kearns &amp; Nevmyvaka (2013) implement RL for trade execution optimization in lit and dark pools. Especially in the case of dark pools, they apply a censored exploration algorithm to the problem of smart order routing (SOR). Yang et al. (arch) examine an IRL algorithm for the separation of HFT strategies from other algorithmic trading activities. They also apply the same algorithm to the identification of manipulative HFT strategies (i.e. spoofing). Felker et al. (2014) predict changes in the price of quotes from several exchanges. They apply feature-weighted Euclidean distance to the centroid of a training cluster. They calculate this type of distance to the centroid of a training cluster where feature selection is taken into consideration because several exchanges are included in their model.

## 2.4. Additional Methods for HFT and LOB

HFT and LOB research activity also covers topics like the optimal submission strategies of bid and ask orders with a focus on the inventory risk that stems from an asset's value uncertainty, as in the work of Avellaneda &amp; Stoikov (2008). Chang (2015) models the dynamics of LOB by using a Bayesian inference of the Markov chain model class, tested on high-frequency data. An

17 Motivation for apprenticeship learning is to use IRL techniques to learn the reward function and then use this function in order to define a Markov decision problem (MDP).

&amp; Chan (2017) suggest a new stochastic model which is based on independent compound Poisson processes of the order flow. Talebi et al. (2014) try to predict trends in the FX market by employing a multivariate Gaussian classifier (MGC) combined with Bayesian voting. Fletcher et al. (2010) examine trading opportunities for the EUR/USD where the price movement is based on multiple kernel learning (MKL). More specifically, the authors utilize SimpleMKL, and the more recent LPBoostMKL, methods for training a multi-class SVM. Christensen &amp; Woodmansey (2013) develop a classification method based on Gaussian kernel in order to identify iceberg 18 orders for GLOBEX.

Maglaras et al. (2015) consider the LOB as a multi-class queueing system in order to solve the problem placement of limit and market order placements. Mankad et al. (2013) apply a static plaid clustering technique to synthetic data in order to classify the different types of trades. Aramonte et al. (2013) show that the information asymmetry in a high-frequency environment is crucial.

Vella &amp; Ng (2016) use higher order fuzzy systems (i.e. an adaptive neurofuzzy inference system) by introducing T2 fuzzy sets where the goal is to reduce microstructure noise in the HFT sphere. Abernethy &amp; Kale (2013) apply market-maker strategies based on low regret algorithms for the stock market. Almgren &amp; Lorenz (2006) explain price momentum by modelling Brownian motion with a drift whose distribution is updated based on Bayesian inference. Næs &amp; Skjeltorp (2006) show that the order book slope measures the elasticity of supplied quantity as a function of asset prices related to volatility, trading activity, and an asset's dispersion beliefs.

## 3. The LOB Dataset

In this section, we describe in detail our dataset collected in order to facilitate future research in LOB-based HFT. We start by providing a detailed description of the data in Section 3.1. Data processing steps are followed in order to extract message books and LOBs, as described in Section 3.2.

## 3.1. Data Description

Extracting information from the ITCH flow, and without relying on thirdparty data providers, we analyse stocks from different industry sectors for ten full days of ultra-high-frequency intra-day data. The data provides information regarding trades against hidden orders. Coherently, the non-displayable hidden portions of the total volume of a so-called iceberg order are not accessible from the data. Our ITCH feed data is day-specific and market-wide, which means that we deal with one file per day with data over all the securities. Information (block A in Fig. 1) regarding (i) messages for order submissions, (ii) trades, and (iii) cancellations, is included. For each order, its type (buy/sell), price, quantity, and exact time stamp on a millisecond basis is available. In addition, (iv) administrative messages (i.e. trading halts or basic security data), (v) event controls (i.e. start and ending of trading days, states of market segments), and (vi) net order imbalance indicators are also included.

18 Iceberg order is the conditional request made to the broker to sell or buy a larger quantity of the stock, but in smaller predefined quantities.

Fig. 1. Data processing flow

![Image](images/image_000000_c3a497e4dba3f2e543e412de21ed39fd34778b4a9b2fa45cf05509baac3b3cec.png)

The next step is the development and implementation of a C++ converter to extract all the information relevant to a given security. We perform the same process for five stocks traded on the NASDAQ OMX Nordic at the Helsinki exchange from 1 June 2010 to 14 June 2010 19 . This data is stored in a Linux cluster. Information related to the five stocks is illustrated in Table 1. The selected stocks 20 are traded in one exchange (Helsinki) only. By choosing only one stock market exchange, the trader has the advantage of avoiding issues associated with fragmented markets. In the case of fragmented markets, the limit orders for a given asset are spread between several exchanges, posing problems from empirical data analysis O'Hara &amp; Ye (2011).

19 There have been about 23,000 active order books, the vast majority of which are very

Table 1 Stocks used in the analysis

| Id    | ISIN Code    | Company          | Sector             | Industry                |
|-------|--------------|------------------|--------------------|-------------------------|
| KESBV | FI0009000202 | Kesko Oyj        | Consumer Defensive | Grocery Stores          |
| OUT1V | FI0009002422 | Outokumpu Oyj    | Basic Materials    | Steel                   |
| SAMPO | FI0009003305 | Sampo Oyj        | Financial Services | Insurance               |
| RTRKS | FI0009003552 | Rautaruukki Oyj  | Basic Materials    | Steel                   |
| WRT1V | FI0009000727 | W¨ artsil¨ a Oyj | Industrials        | Diversified Industrials |

The Helsinki Stock Exchange, operated by NASDAQ Nordic, is a pure electronic limit order market. The ITCH feed keeps a record of all the events, including those that take place outside active trading hours. At the Helsinki exchange, the trading period goes from 10:00 to 18:25 (local time, UTC/GMT +2 hours). However, in the ITCH feed, we observe several records outside those trading hours. In particular, we consider the regulated auction period before 10:00, which is used to set the opening price of the day (the so-called pre-opening period) before trading begins. This is a structurally different mechanism following different rules with respect to the order book flow during trading hours. Similarly, another structural break in the order book's dynamics is due to the different regulations that are in force between 18:25 and 18:30 (the so-called post-opening period). As a result, we retain exclusively the events occurring between 10:30 and 18:00. More information related to the above-mentioned issues can be found in Siikanen et al. (2017b) and Siikanen et al. (2017a). Here, the order book is expected to have comparable dynamics with no biases or exceptions caused by its proximity to the market opening and closing times.

## 3.2. Limit Order and Message Books

Message and limit order books are processed for each of the 10 days for the five stocks. More specifically, there are two types of messages that are particularly relevant here: (i) 'add order messages', corresponding to order submissions, and (ii) 'modify order messages', corresponding to updates on the status of existing orders through order cancellations and order executions.

illiquid, show sporadic activity, and correspond to little and noisy data.

20 The choice is driven by the necessity of having a sufficient amount of data for training (this excludes illiquid stocks) while covering different industry sectors. These five selected stocks (see Table 1), which aggregate input message list and order book data for feature extraction, are about 4GB; RTRKS was suspended from trading and delisted from the Helsinki exchange on 20 Nov 2014.

Example message 21 and limit order 22 books are illustrated in Table 2 and Table 3, respectively.

Table 2 Message list example

|     Timestamp |      Id |   Price |   Quantity | Event        | Side   |
|---------------|---------|---------|------------|--------------|--------|
| 1275386347944 | 6505727 |  126200 |        400 | Cancellation | Ask    |
| 1275386347981 | 6505741 |  126500 |        300 | Submission   | Ask    |
| 1275386347981 | 6505741 |  126500 |        300 | Cancellation | Ask    |
| 1275386348070 | 6511439 |  126100 |         17 | Execution    | Bid    |
| 1275386348070 | 6511439 |  126100 |         17 | Submission   | Bid    |
| 1275386348101 | 6511469 |  126600 |        300 | Cancellation | Ask    |

LOB is a centralized trading method that is incorporated by the majority of exchanges globally. It aggregates the limit orders of both sides (i.e. the ask and bid sides) of the stock market (e.g. the Nordic stock market). LOB matches every new event type according to several characteristics. Event types and LOB characteristics describe the current state of this matching engine. Event types can be executions, order submissions, and order cancellations. Characteristics of LOB are the resolution parameters Gould et al. (2013), which are the tick size π (i.e. the smallest permissible price between different orders), and the lot size σ (i.e. the smallest amount of a stock that can be traded and is defined as { k σ | k = 1 , 2 , ... } ). Order inflow and resolution parameters will formulate the dynamics of the LOB, whose current state will be identified by the state variable of four elements ( s b t , q b t , s a t , q a t ) , t ≥ 0, where s b t ( s b t ) is the best bid (ask) price and q b t ( q a t ) is the size of the best bid (ask) level at time t.

In our data, timestamps are expressed in milliseconds based on 1 Jan 1970 format and shifted by three hours with respect to Eastern European Time (in the data, the trading day goes from 7:00 to 15:25). ITHC feed prices are recorded up to 4 decimal and, in our data, the decimal point is removed by multiplying the price by 10,000 where currency is in Euro for the Helsinki exchange. The tick size, defined as the smallest possible gap between the ask and bid prices, is one cent. Similarly, orders' quantities are constrained to integers greater than one.

Table 3 Order book example

|               |           |        | Level 1   | Level 1   | Level 1   | Level 1   | Level 2   | Level 2   | Level 2   | Level 2   | ...      |
|---------------|-----------|--------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|----------|
|               |           |        | Ask       | Ask       | Bid       | Bid       | Ask       | Ask       | Bid       | Bid       |          |
| Timestamp     | Mid-price | Spread | Price     | Quantity  | Price     | Quantity  | Price     | Quantity  | Price     | Quantity  | Quantity |
| 1275386347944 | 126200    | 200    | 126300    | 300       | 126100    | 17        | 126400    | 4765      | 126000    | 2800      | ...      |
| 1275386347981 | 126200    | 200    | 126300    | 300       | 126100    | 17        | 126400    | 4765      | 126000    | 2800      | ...      |
| 1275386347981 | 126200    | 200    | 126300    | 300       | 126100    | 17        | 126400    | 4765      | 126000    | 2800      | ...      |
| 1275386348070 | 126050    | 100    | 126100    | 291       | 126000    | 2800      | 126200    | 300       | 125900    | 1120      | ...      |
| 1275386348070 | 126050    | 100    | 126100    | 291       | 126000    | 2800      | 126200    | 300       | 125900    | 1120      | ...      |
| 1275386348101 | 126050    | 100    | 126100    | 291       | 126000    | 2800      | 126200    | 300       | 125900    | 1120      | ...      |

## 3.3. Data Availability and Distribution

In compliance with NASDAQ OMX agreements, the normalized feature dataset is made available to the research community. 23 The open-access version of our data has been normalized in order to prevent reconstruction of the original NASDAQ data.

## 3.4. Experimental Protocol

In order to make our dataset a benchmark that can be used for the evaluation of HTF methods based on LOB information, the data is accompanied by the following experimental protocol. We develop a day-based prediction framework following an anchored forward cross-validation format. More specifically, the training set is increases by one day in each fold and stops after n -1 days (i.e. after 9 days in our case where n = 10). On each fold, the test set corresponds to one day of data, which moves in a rolling window format. The experimental setup is illustrated in Fig. 2. Performance is measured by calculating the mean accuracy, recall, precision, and F1 score over all folds, as well as the corresponding standard deviation. We measure our results based on these metrics, which are defined as follows:

<!-- formula-start id="fi2010_1705.03233v5:formula:0001" status="verified_source_and_manual" source-page="11" -->
$$
\mathrm{Accuracy} = \frac{TP+TN}{TP+TN+FP+FN} \tag{1}
$$
![Source formula fi2010_1705.03233v5:formula:0001](images/formula_0001.png)
*Formula quality: `verified_source_and_manual`; source PDF page 11. Matched to exact arXiv source 1705.03233v5 at Benchmark_Dataset_for_Mid-Price_Forecasting_of_Limit_Order_Book_Data_with_Machine_Learning_Methods.tex:271 (score=1.0).*
<!-- formula-end -->

<!-- formula-start id="fi2010_1705.03233v5:formula:0002" status="verified_source_and_manual" source-page="11" -->
$$
\mathrm{Precision} = \frac{TP}{TP+FP} \tag{2}
$$
![Source formula fi2010_1705.03233v5:formula:0002](images/formula_0002.png)
*Formula quality: `verified_source_and_manual`; source PDF page 11. Matched to exact arXiv source 1705.03233v5 at Benchmark_Dataset_for_Mid-Price_Forecasting_of_Limit_Order_Book_Data_with_Machine_Learning_Methods.tex:275 (score=1.0).*
<!-- formula-end -->

<!-- formula-start id="fi2010_1705.03233v5:formula:0003" status="verified_source_and_manual" source-page="11" -->
$$
\mathrm{Recall} = \frac{TP}{TP+FN} \tag{3}
$$
![Source formula fi2010_1705.03233v5:formula:0003](images/formula_0003.png)
*Formula quality: `verified_source_and_manual`; source PDF page 11. Matched to exact arXiv source 1705.03233v5 at Benchmark_Dataset_for_Mid-Price_Forecasting_of_Limit_Order_Book_Data_with_Machine_Learning_Methods.tex:279 (score=1.0).*
<!-- formula-end -->

<!-- formula-start id="fi2010_1705.03233v5:formula:0004" status="verified_source_and_manual" source-page="11" -->
$$
F_1 = 2\times\frac{\mathrm{Precision}\times\mathrm{Recall}}{\mathrm{Precision}+\mathrm{Recall}} \tag{4}
$$
![Source formula fi2010_1705.03233v5:formula:0004](images/formula_0004.png)
*Formula quality: `verified_source_and_manual`; source PDF page 11. Matched to exact arXiv source 1705.03233v5 at Benchmark_Dataset_for_Mid-Price_Forecasting_of_Limit_Order_Book_Data_with_Machine_Learning_Methods.tex:283 (score=1.0).*
<!-- formula-end -->

where TP and TF represents the true positives and true negatives, respectively, of the mid-price prediction label compared with the ground truth, where FP and FN represents the false positives and false negatives, respectively. From among the above metrics, we focus on the F1 score performance. The main reason that we focus on F1 score is based on its ability to only be affected in one direction of skew distributions, in the case of unbalanced classes like ours. On the contary, accuracy cannot differentiate between the number of correct labels (i.e. related to mid-price movement direction prediction) of different classes where the other three metrics can separate the correct labels among different classes with F1 being the harmonic mean of Precision and Recall.

We follow an event-based inflow, as used in Li et al. (2016). This is due to the fact that events (i.e. orders, executions, and cancellations) do not follow a uniform inflow rate. Time intervals between two consecutive events can vary from milliseconds to several minutes of difference. Event-based data representation avoids issues related to such big differences in data flow. As a result, each of our representations is a vector that contains information for 10 consecutive events. Event-based data description leads to a dataset of approximately half a million representations (i.e. 394,337 representations). We represent these events using the 144-dimensional representation proposed recently by Kercheval &amp; Zhang (2015), formed by three types of features: a) the raw data of a 10level limit order containing price and volume values for bid and ask orders, b) features describing the state of the LOB, exploiting past information, and c) features describing the information edge in the raw data by taking time into account. Derivations of time, stock price, and volume are calculated for short and long-term projections. More specifically, types in features u 7 , u 8 , and u 9 are: trades, orders, cancellations, deletion, execution of a visible limit order , and execution of a hidden limit order . Expressions used for calculating these features are provided in Table 4. One limitation of the adopted features is the lack of information related to order flow (i.e. the sequence of order book messages). However, as can be seen in the Results Section 6,, the baselines achieve relatively good performance and therefore we leave the introduction of extra features that can enhance performance to future research.

23 We thank Ms. Sonja Salminen at NASDAQ for her support and help.

![Image](images/image_000001_6f0a1f1aa613a2f6c2c9f3bbf2bcf42b1fbe552d1ca5794972f1e642b4626921.png)

We provide three sets of data, each created by following a different data normalization strategy, i.e. z-score, min-max, and decimal precision normalization, for every i datasample. Z-score, in particular, is the normalization process through which we subtract the mean from our input data for each feature sep- arately and divide by the standard deviation of the given sample:

<!-- formula-start id="fi2010_1705.03233v5:formula:0005" status="verified_source_and_manual" source-page="13" -->
$$
x_i^{(\mathrm{Zscore})} = \frac{x_i-\frac{1}{N}\sum_{j=1}^{N}x_j}{\sqrt{\frac{1}{N}\sum_{j=1}^{N}(x_j-\bar{x})^2}} \tag{5}
$$
![Source formula fi2010_1705.03233v5:formula:0005](images/formula_0005.png)
*Formula quality: `verified_source_and_manual`; source PDF page 13. Matched to exact arXiv source 1705.03233v5 at Benchmark_Dataset_for_Mid-Price_Forecasting_of_Limit_Order_Book_Data_with_Machine_Learning_Methods.tex:300 (score=1.0).*
<!-- formula-end -->

where ¯ x denotes the mean vector, as appears in Eq. 5. On the other hand, min-max scaling, as described by:

<!-- formula-start id="fi2010_1705.03233v5:formula:0006" status="verified_source_and_manual" source-page="13" -->
$$
x_i^{(\mathrm{MM})} = \frac{x_i-x_{\min}}{x_{\max}-x_{\min}} \tag{6}
$$
![Source formula fi2010_1705.03233v5:formula:0006](images/formula_0006.png)
*Formula quality: `verified_source_and_manual`; source PDF page 13. Matched to exact arXiv source 1705.03233v5 at Benchmark_Dataset_for_Mid-Price_Forecasting_of_Limit_Order_Book_Data_with_Machine_Learning_Methods.tex:306 (score=1.0).*
<!-- formula-end -->

is the process of subtracting the minimum value from each feature and dividing it by the difference between the maximum and minimum value of that feature sample. The third scaling setup is the decimal precision approach. This normalization method is based on moving the decimal points of each of the feature values. Calculations follow the absolute value of each feature sample:

<!-- formula-start id="fi2010_1705.03233v5:formula:0007" status="verified_source_and_manual" source-page="13" -->
$$
x_i^{(\mathrm{DP})} = \frac{x_i}{10^k} \tag{7}
$$
![Source formula fi2010_1705.03233v5:formula:0007](images/formula_0007.png)
*Formula quality: `verified_source_and_manual`; source PDF page 13. Matched to exact arXiv source 1705.03233v5 at Benchmark_Dataset_for_Mid-Price_Forecasting_of_Limit_Order_Book_Data_with_Machine_Learning_Methods.tex:311 (score=1.0).*
<!-- formula-end -->

where k is the integer that will give us the maximum value for | x DP | &lt; 1.

Table 4 Feature Sets

| Feature Set      | Description                                                                                                                                                                                                                                                                                                                                                                     | Details                                                                                                        |
|------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| Basic            | u 1 = { P ask i ,V ask i ,P bid i ,V bid i } n i =1                                                                                                                                                                                                                                                                                                                             | 10(=n)-level LOB Data                                                                                          |
| Time-Insensitive | u 2 = { ( P ask i - P bid i ) , ( P ask i + P bid i ) / 2 } n i =1 u 3 = { P ask n - P ask 1 ,P bid 1 - P bid n , &#124; P ask i +1 - P ask i &#124; , &#124; P bid i +1 - P bid i &#124;} n i +1 u 4 = { 1 n n ∑ i =1 P ask i , 1 n n ∑ i =1 P bid i , 1 n n ∑ i =1 V ask i , 1 n n ∑ i =1 V bid i } u 5 = { n ∑ i =1 ( P ask i - P bid i ) , n ∑ i =1 ( V ask i - V bid i ) } | Spread & Mid-Price Price Differences Price & Volume Means Accumulated Differences                              |
| Time-Sensitive   | u 6 = { dP ask i /dt,dP bid i /dt,dV ask i /dt,dV bid i /dt } n i =1 u 7 = { λ 1 ∆ t ,λ 2 ∆ t ,λ 3 ∆ t ,λ 4 ∆ t ,λ 5 ∆ t ,λ 6 ∆ t } u 8 = { 1 λ 1 ∆ t >λ 1 ∆ T , 1 λ 2 ∆ t >λ 2 ∆ T , 1 λ 3 ∆ t >λ 3 ∆ T , 1 λ 4 ∆ t >λ 4 ∆ T , 1 λ 5 ∆ t >λ 5 ∆ T , 1 λ 6 ∆ t >λ u 9 = { dλ 1 /dt,dλ 2 /dt,dλ 3 /dt,dλ 4 /dt,dλ 5 /dt,dλ 6 /dt }                                               | Price & Volume Derivation Average Intensity per Type Relative Intensity Comparison Limit Activity Accelaration |

Having defined the event representations, we use five different projection horizons for our labels. Each of these horizons portrays a different future projection interval of the mid-price movement (i.e. upward, downward, and stationary mid-price movement). More specifically, we extract labels based on short-term and long-term, event -based, relative changes for the next 1, 2, 3, 5, and 10 events for our representations dataset.

Our labels describe the percentage change of the mid-price, which is calculated as follows:

<!-- formula-start id="fi2010_1705.03233v5:formula:0008" status="verified_source_and_manual" source-page="13" -->
$$
l_i^{(j)} = \frac{1}{k}\sum_{j=i+1}^{i+k}\frac{m_j-m_i}{m_i} \tag{8}
$$
![Source formula fi2010_1705.03233v5:formula:0008](images/formula_0008.png)
*Formula quality: `verified_source_and_manual`; source PDF page 13. Matched to exact arXiv source 1705.03233v5 at Benchmark_Dataset_for_Mid-Price_Forecasting_of_Limit_Order_Book_Data_with_Machine_Learning_Methods.tex:347 (score=1.0).*
<!-- formula-end -->

where m j is the future mid-prices ( k = 1, 2, 3, 5, or 10 next events in our representations) and m i is the current mid-price. The extracted labels are based on a threshold for the percentage change of 0.002. For percentage changes equal to or greater than 0.002, we use label 1. For percentage change that varies from -0.00199 to 0.00199, we use label 2, and, for percentage change smaller or equal to -0.002, we use label 3.

## 4. Existing Datasets Described in the Literature

In this section, we list existing HFT datasets described in the literature and provide qualitative and quantitative comparisons to our dataset. The following works mainly focus on datasets that are related to machine learning methods.

There are mainly three sources of data from which a high-frequency trader can choose. The first option is the use of publicly available data (e.g. (1) Dukascopy and (2) truefx), where no prior agreement is required for data acquisition. The second option is publicly available data upon request for academic purposes, which can be found in (3) Brogaard et al. (2014), (4) Hasbrouck &amp; Saar (2013), (5) De Winne &amp; D'hondt (2007), Detollenaere &amp; D'hondt (2017) and Carrion (2013). Finally, the third and most common option is data through platforms requiring a subscription fee, like those in (6) Kercheval &amp; Zhang (2015), Li et al. (2016), and (7) Sirignano (2016). Existing data sources and characteristics are listed in Table 5.

Table 5 HFT Dataset Examples

|    | Dataset      | Public Avl.   | Unit Time   | Period        | Asset Class / Num. of Stocks   | Size                 | Annotations   |
|----|--------------|---------------|-------------|---------------|--------------------------------|----------------------|---------------|
|  1 | Dukascopy    | ✓             | ms          | up-to-date    | various                        | ≈ 20,000 events/day  | 5             |
|  2 | truefx       | ✓             | ms          | up-to-date    | 15 FX pairs                    | ≈ 300,000 events/day | 5             |
|  3 | NASDAQ       | AuR           | ms          | 2008-09       | Equity / 120                   | -                    | 5             |
|  4 | NASDAQ       | AuR           | ms          | 10/07 & 06/08 | Equity / 500                   | ≈ 55,000 events/day  | 5             |
|  5 | NASDAQ       | 5             | ms          | -             | Equity / 5                     | 2,000 data points    | 5             |
|  6 | Euronext     | AuR           | -           | -             | Several Products               | -                    | 5             |
|  7 | NASDAQ       | 5             | ns          | 01/14-08/15   | Equity / 489                   | 50 TB                | 5             |
|  8 | Our - NASDAQ | ✓             | ms          | 01-14/06/10   | Equity / 5                     | 4 M samples          | ✓             |

In particular, the datasets are in millisecond resolution, except for number six in the table. Access to various asset classes including FX, commodities, indices, and stocks is also provided. To the best of our knowledge, there is no available literature based on this type of dataset for equities. Another source of free tick-by-tick historical data is the truefx.com site, but the site provides data only for the FX market for several pairs of currencies in a millisecond resolution. The data contains information regarding timestamps (in millisecond resolution) and bid and ask prices. Each of these .csv files contains approximately 200,000 events per day. This type of data is used in a mean-reverting jump-diffusion model, as presented in Suwanpetai (2016).

There is a second category of datasets available upon request (AuR), as seen in Hasbrouck &amp; Saar (2013). In this paper, the authors use the NASDAQ OMX ITCH for two periods: October 2007 and June 2008. For that period, they run samples of ten-minutes intervals for each day where they set a cut-off mechanism for available messages per period. 24 The main disadvantage of uniformly sampling HFT data is that the trader loses vital information. Events come randomly, with inactive periods varying from a few milliseconds to several minutes or hours. In our work, we overcome this challenge by considering the information based on event inflow, rather than equal time sampling. Another example of data that is available only for academic purposes is Brogaard et al. (2014). The dataset contains information regarding timestamps, price, and buy-sell side prices but no other details related to daily events or feature vectors. In Hasbrouck &amp; Saar (2013), the authors provide a detailed description of their NASDAQ OMX ITCH data, which is not directly accessible for testing and comparison with their baselines. They use this data to applying low-latency strategies based on measures that capture links between submissions, cancellations, and executions. Authors in De Winne &amp; D'hondt (2007) and Detollenaere &amp; D'hondt (2017) use similar datasets from Euronext for limit order book construction. They specify that their dataset is available upon request from the provider. What is more, the data provider supplies with details regarding the LOB construction by the user. Our work fills that gap since our dataset provides the full limit order book depth and it is ready for use and comparison to our baselines.

The last category of dataset has dissemination restrictions. An example is the paper by Kercheval &amp; Zhang (2015), where the authors are trying to predict the mid-price movement by using machine learning (i.e. SVM). They train their model with a very small number of samples (i.e. 4000 samples). The HFT activity can produce a huge volume of trading events daily, like our database does with 100,000 daily events for only one stock. Moreover, the datasets in Kercheval &amp; Zhang (2015) and Sirignano (2016) are not publicly available, which makes comparison with other methods impossible. In the same direction, we also add works such as Hasbrouck (2009), Kalay et al. (2004), and Kalay et al. (2002) which utilize TAQ and Tel-Aviv stock exchange datasets (not for machine learning methods), and require subscription.

## 5. Baselines

In order to provide performance baselines for our new dataset of HFT with LOB data, we conducted experiments with two regression models using the data representations described in Section 3.4. Details on the models used are provided in Section 5.1 and Section 5.2. The baseline performances are provided in Section 6.

## 5.1. Ridge Regression (RR)

Ridge regression defines a linear mapping, expressed by the matrix W ∈ R D × C , that optimally maps a set of vectors x i ∈ R D , i = 1 , . . . , N to another set of vectors (noted as target vectors) t i ∈ R C , i = 1 , . . . , N , by optimizing the following criterion:

24 The authors provide a threshold, which is based on 250 events per 10-minute sample interval.

<!-- formula-start id="fi2010_1705.03233v5:formula:0009" status="verified_source_and_manual" source-page="16" -->
$$
W^* = \operatorname*{arg\,min}_{W}\sum_{i=1}^{N}\lVert W^T x_i-t_i\rVert_2^2+\lambda\lVert W\rVert_F^2 \tag{9}
$$
![Source formula fi2010_1705.03233v5:formula:0009](images/formula_0009.png)
*Formula quality: `verified_source_and_manual`; source PDF page 16. Matched to exact arXiv source 1705.03233v5 at Benchmark_Dataset_for_Mid-Price_Forecasting_of_Limit_Order_Book_Data_with_Machine_Learning_Methods.tex:392 (score=0.8286).*
<!-- formula-end -->

or using a matrix notation:

<!-- formula-start id="fi2010_1705.03233v5:formula:0010" status="verified_source_and_manual" source-page="16" -->
$$
W^* = \operatorname*{arg\,min}_{W}\lVert W^T X-T\rVert_F^2+\lambda\lVert W\rVert_F^2 \tag{10}
$$
![Source formula fi2010_1705.03233v5:formula:0010](images/formula_0010.png)
*Formula quality: `verified_source_and_manual`; source PDF page 16. Matched to exact arXiv source 1705.03233v5 at Benchmark_Dataset_for_Mid-Price_Forecasting_of_Limit_Order_Book_Data_with_Machine_Learning_Methods.tex:397 (score=0.7407).*
<!-- formula-end -->

In the above, X = [ x i , . . . , x N ] and T = [ t i , . . . , t N ] are matrices formed by the samples x i and t i as columns, respectively.

In our case, each sample x i corresponds to an event, represented by a vector (with D = 144), as described in Section 3.4. For the three-class classification problems in our dataset, the elements of vectors t i ∈ R C ( C = 3 in our case) take values equal to t ik = 1, if x i belongs to class k , and, if t ik = -1, otherwise. The solution of Eq. 10 is given by:

<!-- formula-start id="fi2010_1705.03233v5:formula:0011" status="verified_source_and_manual" source-page="16" -->
$$
W = X(X^T X+\lambda I)^{-1}T^T \tag{11}
$$
![Source formula fi2010_1705.03233v5:formula:0011](images/formula_0011.png)
*Formula quality: `verified_source_and_manual`; source PDF page 16. Matched to exact arXiv source 1705.03233v5 at Benchmark_Dataset_for_Mid-Price_Forecasting_of_Limit_Order_Book_Data_with_Machine_Learning_Methods.tex:403 (score=1.0).*
<!-- formula-end -->

<!-- formula-start id="fi2010_1705.03233v5:formula:0012" status="verified_source_and_manual" source-page="16" -->
$$
W = (XX^T+\lambda I)^{-1}XT^T \tag{12}
$$
![Source formula fi2010_1705.03233v5:formula:0012](images/formula_0012.png)
*Formula quality: `verified_source_and_manual`; source PDF page 16. Matched to exact arXiv source 1705.03233v5 at Benchmark_Dataset_for_Mid-Price_Forecasting_of_Limit_Order_Book_Data_with_Machine_Learning_Methods.tex:407 (score=1.0).*
<!-- formula-end -->

or

where I is the identity matrix of appropriate dimensions. Here, we should note that, in our case, where the size of the data is big, W should be computed using Eq. 12, since the calculation of Eq. 11 is computationally very expensive.

After the calculation of W , a new (test) sample x ∈ R D is mapped on its corresponding representation in space R C , i.e. o = W T x , and is classified according to the maximal value of its projection, i.e.:

<!-- formula-start id="fi2010_1705.03233v5:formula:0013" status="verified_source_and_manual" source-page="16" -->
$$
l_x = \operatorname*{arg\,max}_{k} o_k \tag{13}
$$
![Source formula fi2010_1705.03233v5:formula:0013](images/formula_0013.png)
*Formula quality: `verified_source_and_manual`; source PDF page 16. Matched to exact arXiv source 1705.03233v5 at Benchmark_Dataset_for_Mid-Price_Forecasting_of_Limit_Order_Book_Data_with_Machine_Learning_Methods.tex:413 (score=0.6667).*
<!-- formula-end -->

## 5.2. SLFN Network-based Nonlinear Regression

We also test the performance of a non-linear regression model. Since the application of kernel-based regression is computationally too intensive for the size of our data, we use a SLFN (Fig. 3) network-based regression model. Such a model is formed as follows:

For fast network training, we train our network based on the algorithm proposed in Huang et al. (2012), Zhang et al. (June), and Iosifidis et al. (2017). This algorithm is formed by two processing steps. In the first step, the network's hidden layer weights are determined either randomly Huang et al. (2012) or by applying clustering on the training data. We apply K -means clustering in order to determine K prototype vectors, which are subsequently used as the network's hidden layer weights.

Having determined the network's hidden layer weights V ∈ R D × K , the input data x i , i = 1 , . . . , N are non-linearly mapped to vectors h i ∈ R K , expressing the data representations in the feature space determined by the network's hidden layer outputs R K . We use the radial basis function, i.e. h i = φ RBF ( x i ), calculated in an element-wise manner, as follows:

Fig. 3. SLFN

![Image](images/image_000002_da1d4d71c5dcaa81b29b65150eddb380ddc3546b5786bf6d78a7482693ba31bf.png)

<!-- formula-start id="fi2010_1705.03233v5:formula:0014" status="verified_source_and_manual" source-page="17" -->
$$
h_{ik}=\exp\!\left(\frac{\lVert x_i-v_k\rVert_2^2}{2\sigma^2}\right),\quad k=1,\ldots,K \tag{14}
$$
![Source formula fi2010_1705.03233v5:formula:0014](images/formula_0014.png)
*Formula quality: `verified_source_and_manual`; source PDF page 17. Matched to exact arXiv source 1705.03233v5 at Benchmark_Dataset_for_Mid-Price_Forecasting_of_Limit_Order_Book_Data_with_Machine_Learning_Methods.tex:433 (score=1.0).*
<!-- formula-end -->

where σ is a hyper-parameter denoting the spread of the RBF neuron and v k corresponds to the k -th column of V .

The network's output weights W ∈ R K × C are subsequently determined by solving for:

<!-- formula-start id="fi2010_1705.03233v5:formula:0015" status="verified_source_and_manual" source-page="17" -->
$$
W^* = \operatorname*{arg\,min}_{W}\lVert W^T H-T\rVert_F^2+\lambda\lVert W\rVert_F^2 \tag{15}
$$
![Source formula fi2010_1705.03233v5:formula:0015](images/formula_0015.png)
*Formula quality: `verified_source_and_manual`; source PDF page 17. Matched to exact arXiv source 1705.03233v5 at Benchmark_Dataset_for_Mid-Price_Forecasting_of_Limit_Order_Book_Data_with_Machine_Learning_Methods.tex:439 (score=0.7407).*
<!-- formula-end -->

where H = [ h 1 , . . . , h N ] is a matrix formed by the network's hidden layer outputs for the training data and T is a matrix formed by the network's target vectors t i , i = 1 , . . . , N as defined in Section 5.1. The network's output weights are given by:

<!-- formula-start id="fi2010_1705.03233v5:formula:0016" status="verified_source_and_manual" source-page="17" -->
$$
W = (HH^T+\lambda I)^{-1}HT^T \tag{16}
$$
![Source formula fi2010_1705.03233v5:formula:0016](images/formula_0016.png)
*Formula quality: `verified_source_and_manual`; source PDF page 17. Matched to exact arXiv source 1705.03233v5 at Benchmark_Dataset_for_Mid-Price_Forecasting_of_Limit_Order_Book_Data_with_Machine_Learning_Methods.tex:443 (score=1.0).*
<!-- formula-end -->

After calculation of the network parameters V and W , a new (test) sample x ∈ R D is mapped on its corresponding representations in spaces R K and R C , i.e. h = φ RBF ( x ) and o = W T h , respectively. It is classified according to the maximal network output, i.e.:

<!-- formula-start id="fi2010_1705.03233v5:formula:0017" status="verified_source_and_manual" source-page="17" -->
$$
l_x = \operatorname*{arg\,max}_{k} o_k \tag{17}
$$
![Source formula fi2010_1705.03233v5:formula:0017](images/formula_0017.png)
*Formula quality: `verified_source_and_manual`; source PDF page 17. Matched to exact arXiv source 1705.03233v5 at Benchmark_Dataset_for_Mid-Price_Forecasting_of_Limit_Order_Book_Data_with_Machine_Learning_Methods.tex:448 (score=0.6667).*
<!-- formula-end -->

## 6. Results

In our first set of experiments, we have applied two supervised machine learning methods, as described in Section 5.1 and Section 5.2, on a dataset that does not include the auction period. Results with the auction period will also be available. Since there is not a widely adopted experimental protocol for these datasets, we provide information for the five different label scenarios under the three normalization setups.

Table 6 Results Based on Unfiltered Representations

| Labels   | RR Accuracy   | RR Precision   | RR Recall     | RR F 1        |
|----------|---------------|----------------|---------------|---------------|
| 1        | 0,637 ± 0,055 | 0,505 ± 0,145  | 0,337 ± 0,003 | 0,268 ± 0,014 |
| 2        | 0,555 ± 0,064 | 0,504 ± 0,131  | 0,376 ± 0,023 | 0,320 ± 0,050 |
| 3        | 0,489 ± 0,061 | 0,423 ± 0,109  | 0,397 ± 0,031 | 0,356 ± 0,070 |
| 5        | 0,429 ± 0,049 | 0,402 ± 0,113  | 0,425 ± 0,038 | 0,400 ± 0,093 |
| 10       | 0,453 ± 0,054 | 0,400 ± 0,105  | 0,400 ± 0,030 | 0,347 ± 0,066 |
| Labels   | SLFN Accuracy | SLFN Precision | SLFN Recall   | SLFN F 1      |
| 1        | 0,636 ± 0,055 | 0,299 ± 0,075  | 0,335 ± 0,002 | 0,262 ± 0,015 |
| 2        | 0,536 ± 0,069 | 0,387 ± 0,132  | 0,345 ± 0,009 | 0,260 ± 0,035 |
| 3        | 0,473 ± 0,074 | 0,334 ± 0,080  | 0,357 ± 0,005 | 0,270 ± 0,021 |
| 5        | 0,381 ± 0,038 | 0,342 ± 0,058  | 0,370 ± 0,020 | 0,327 ± 0,043 |
| 10       | 0,401 ± 0,039 | 0,284 ± 0,102  | 0,356 ± 0,020 | 0,290 ± 0,070 |

Table 7 Results based on Z-score Normalization

| Labels   | RR Accuracy   | RR Precision   | RR Recall     | RR F 1        |
|----------|---------------|----------------|---------------|---------------|
| 1        | 0,480 ± 0,040 | 0,418 ± 0,021  | 0,435 ± 0,029 | 0,410 ± 0,022 |
| 2        | 0,498 ± 0,052 | 0,444 ± 0,025  | 0,443 ± 0,031 | 0,440 ± 0,031 |
| 3        | 0,463 ± 0,045 | 0,438 ± 0,027  | 0,437 ± 0,033 | 0,433 ± 0,034 |
| 5        | 0,439 ± 0,042 | 0,436 ± 0,028  | 0,433 ± 0,028 | 0,427 ± 0,041 |
| 10       | 0,429 ± 0,046 | 0,429 ± 0,028  | 0,429 ± 0,043 | 0,416 ± 0,044 |
| Labels   | SLFN Accuracy | SLFN Precision | SLFN Recall   | SLFN F 1      |
| 1        | 0,643 ± 0,056 | 0,512 ± 0,037  | 0,366 ± 0,019 | 0,327 ± 0,046 |
| 2        | 0,556 ± 0,066 | 0,550 ± 0,029  | 0,378 ± 0,011 | 0,327 ± 0,030 |
| 3        | 0,512 ± 0,069 | 0,497 ± 0,024  | 0,424 ± 0,047 | 0,389 ± 0,082 |
| 5        | 0,473 ± 0,036 | 0,468 ± 0,024  | 0,464 ± 0,028 | 0,459 ± 0,031 |
| 10       | 0,477 ± 0,048 | 0,453 ± 0,056  | 0,432 ± 0,025 | 0,410 ± 0,040 |

The tables in this section provide details regarding the results of experiments conducted on raw data and three different normalization setups. We present these results, for our baseline models, in order to give insight into the pre-processing step for a dataset like ours, to examine the strength of the predictability of the projected time horizon, and to understand the implications of the suggested methods. Data normalization can significantly improve metric's performance in combination with the use of the right classifier. More specifically, we measure the predictability power of our models via the performance of the metrics of accuracy, precision, recall, and F1 score. For instance, Table 6 presents the results based on raw data (i.e. no data decoding), and in the case of the linear classifier RR and label 5 (i.e. the 5 th mid-price event as predicted horizon), we achieve an F1 score of 40%, where as in Table 7 (i.e. the Z-score data decoding method), Table 8 (i.e. min-max data decoding method), and Table 9 (i.e. the decimal precision decoding method), we achieve 43%, 42%, and 40%, respectively. This shows that in the case of the linear classifier, the suggested decoding methods did not offer any significant improvements, since the variability of the performance range is approximately 3%. On the other hand, our non-linear classifier (i.e. SLFN) for the same projected time horizon (i.e. label 5) reacted more efficiently in the decoding process. SLFN achieves 33% for the F1 score for non-normalized data, while the Z-score, min-max and decimal precision methods achieve 46%, 43%, and 43%, respectively. As a result, normalization improves the F1 score performance by almost 10%.

Table 8 Results Based on Min-Max Normalization

| Labels   | RR Accuracy   | RR Precision   | RR Recall     | RR F 1        |
|----------|---------------|----------------|---------------|---------------|
| 1        | 0,637 ± 0,054 | 0,499 ± 0,118  | 0,339 ± 0,005 | 0,272 ± 0,015 |
| 2        | 0,561 ± 0,063 | 0,467 ± 0,117  | 0,400 ± 0,028 | 0,368 ± 0,060 |
| 3        | 0,492 ± 0,070 | 0,428 ± 0,111  | 0,400 ± 0,030 | 0,357 ± 0,072 |
| 5        | 0,437 ± 0,048 | 0,419 ± 0,078  | 0,429 ± 0,043 | 0,417 ± 0,063 |
| 10       | 0,452 ± 0,054 | 0,421 ± 0,110  | 0,399 ± 0,028 | 0,348 ± 0,066 |
| Labels   | SLFN Accuracy | SLFN Precision | SLFN Recal    | SLFN F 1      |
| 1        | 0,640 ± 0,055 | 0,488 ± 0,104  | 0,348 ± 0,007 | 0,291 ± 0,022 |
| 2        | 0,558 ± 0,065 | 0,469 ± 0,066  | 0,399 ± 0,023 | 0,367 ± 0,050 |
| 3        | 0,499 ± 0,063 | 0,447 ± 0,068  | 0,410 ± 0,032 | 0,370 ± 0,063 |
| 5        | 0,453 ± 0,038 | 0,441 ± 0,041  | 0,444 ± 0,030 | 0,432 ± 0,050 |
| 10       | 0,450 ± 0,048 | 0,432 ± 0,070  | 0,406 ± 0,037 | 0,377 ± 0,062 |

Table 9 Results Based on Decimal Precision Normalization

| Labels   | RR Accuracy   | RR Precision   | RR Recall     | RR F 1        |
|----------|---------------|----------------|---------------|---------------|
| 1        | 0,638 ± 0,054 | 0,518 ± 0,132  | 0,341 ± 0,007 | 0,277 ± 0,018 |
| 2        | 0,551 ± 0,066 | 0,473 ± 0,118  | 0,372 ± 0,018 | 0,315 ± 0,045 |
| 3        | 0,490 ± 0,069 | 0,432 ± 0,113  | 0,386 ± 0,023 | 0,330 ± 0,059 |
| 5        | 0,435 ± 0,051 | 0,406 ± 0,115  | 0,430 ± 0,039 | 0,405 ± 0,095 |
| 10       | 0,451 ± 0,052 | 0,417 ± 0,108  | 0,399 ± 0,029 | 0,349 ± 0,067 |
| Labels   | SLFN Accuracy | SLFN Precision | SLFN Recall   | SLFN F 1      |
| 1        | 0,641 ± 0,055 | 0,512 ± 0,027  | 0,351 ± 0,007 | 0,297 ± 0,024 |
| 2        | 0,565 ± 0,063 | 0,505 ± 0,020  | 0,410 ± 0,026 | 0,385 ± 0,054 |
| 3        | 0,504 ± 0,061 | 0,465 ± 0,032  | 0,421 ± 0,040 | 0,393 ± 0,073 |
| 5        | 0,457 ± 0,038 | 0,451 ± 0,029  | 0,449 ± 0,031 | 0,438 ± 0,046 |
| 10       | 0,461 ± 0,053 | 0,453 ± 0,036  | 0,420 ± 0,035 | 0,399 ± 0,053 |

Normalization and model selection can also affect the predictability of midprice movements over the projected time horizon. Very interesting results come to light if we try to compare the F1 performance over different time horizons. For instance, we can see that regardless of the decoding method, the F1 score is always better for label 5 than 1, meaning that our models' predictions are better further in the future. This result is significant, especially with unfiltered data and min-max and decimal precision normalizations, when F1 score is approximately 27%, in the case of the one-step prediction problem (label 1), and 43% in the case of the five-step problem (label 5).

Another aspect of the experimental results above stems from the pros and cons of linear and non-linear classifiers. More specifically, the RR linear classifier performed better on the raw dataset and for the Z-score decoding method in terms of F1 when compared to the SLFN (i.e. non-linear classifier). This is not the case for the last decoding methods (i.e. min-max and decimal precision), where our non-linear classifier presents similar or better results than RR. An explanation for this F1 performance discrepancy is due to each of these methods' engineering has. The RR classifier tends to be very efficient in high-dimensional problems, and these types of problems are linearly separable, in most cases. Another reason that RR can perform better when compared to a non-linear classifier is that RR can control the complexity by penalizing the bias, via crossvalidation, using the ridge parameter. On the other hand, a non-linear classifier is prone to overfitting, which means that in some cases it offers a better degree of freedom for class separation.

## 7. Conclusion

This paper described a new benchmark dataset formed by the NASDAQ ITCH feed data for five stocks for ten consecutive trading days. Data representations that were exploited by order flow features were made available. We formulated five classification tasks based on mid-price movement predictions for 1, 2, 3, 5, and 10 predicted horizons. Baseline performances of two regression models were also provided in order to facilitate future research on the field. Despite the data size, we achieved an average out-of-sample performance (F1) of, approximately, 46% for both methods. These very promising results show that machine learning can effectively predict mid-price movement.

Potential avenues of research that can benefit from exploiting the provided data include: a) prediction of the stability of the market, which is very important for liquidity providers (market makers) to make the spread, as well as for traders to increase liquidity provision (when markets can be predicted to be stable); b) prediction on market movements, which is important for expert systems used by speculative traders; c) identification of order book spoofing, i.e. situations where markets are manipulated by limit orders. While there is no spoofing activity information available for the provided data, the exploitation of such a large corpus of data can be used in order to identify patterns in stock markets that can be further analysed as normal or abnormal.

## Acknowledgment

This work was supported by H2020 Project BigDataFinance MSCA-ITNETN 675044 (http://bigdatafinance.eu), Training for Big Data in Financial Re- search and Risk Management.

## References

- Abernethy, J. &amp; Kale, S. (2013). Adaptive market making via online learning. In Advances in Neural Information Processing Systems , pages 2058-2066.
- Almgren, R. &amp; Lorenz, J. (2006). Bayesian adaptive trading with a daily cycle. The Journal of Trading , 1(4):38-46.
- Alvim, L. G., dos Santos, C. N., &amp; Milidiu, R. L. (2010). Daily volume forecasting using high frequency predictors. In Proceedings of the 10th IASTED International Conference (Vol. 674, No. 047, p. 248).
- Amaya, D., Filbien, J.-Y., Okou, C., &amp; Roch, A. F. (2015). Distilling liquidity costs from limit order books. Available at SSRN: https : //papers.ssrn.com/sol 3 /papers.cfm ? abstract id = 2660226.
- An, Y. &amp; Chan, N. H. (2017). Short-term stock price prediction based on limit order book dynamics. Journal of Forecasting , 36(5):541-556.
- Aramonte, S., Schindler, J. W., &amp; Rosen, S. (2013). Assessing and combining financial conditions indexes. Available at SSRN: https : //papers.ssrn.com/sol 3 /papers.cfm ? abstract id = 2976840.
- Avellaneda, M. &amp; Stoikov, S. (2008). High-frequency trading in a limit order book. Quantitative Finance , 8(3):217-224.
- Bogoev, D. &amp; Karam, A. (2016). An empirical detection of high frequency trading strategies.
- Brogaard, J., Hendershott, T., &amp; Riordan, R. (2014). High-frequency trading and price discovery. Review of Financial Studies , 27(8):2267-2306.
- Cao, C., Hansch, O., &amp; Wang, X. (2009). The information content of an open limit-order book. Journal of futures markets , 29(1):16-41.
- Carrion, A. (2013). Very fast money: High-frequency trading on the nasdaq. Journal of Financial Markets , 16(4):680-711.
- Cenesizoglu, T., Dionne, G., &amp; Zhou, X. (2014). Effects of the limit order book on price dynamics. Available at: https : //depot.erudit.org/bitstream/ 003996 dd/ 1 /CIRPEE 14 -26 .pd f .
- Chan, N. T. &amp; Shelton, C. (2001). An electronic market-maker. Available at: https : //dspace.mit.edu/bitstream/handle/ 1721 . 1 / 7220 /AIM -2001 -005 .pd f ? sequence = 2.
- Chang, Y. L. (2015). Inferring markov chain for modeling order book dynamics in high frequency environment. International Journal of Machine Learning and Computing , 5(3):247.

- Christensen, H. L. &amp; Woodmansey, R. (2013). Prediction of hidden liquidity in the limit order book of globex futures. The Journal of Trading , 8(3):68-95.
- Creamer, G. (2012). Model calibration and automated trading agent for euro futures. Quantitative Finance , 12(4):531-545.
- De Winne, R. &amp; D'hondt, C. (2007). Hide-and-seek in the market: placing and detecting hidden orders. Review of Finance , 11(4):663-692.
- Detollenaere, B. &amp; D'hondt, C. (2017). Identifying expensive trades by monitoring the limit order book. Journal of Forecasting , 36(3):273-290.
- Dixon, M. (2016). High frequency market making with machine learning. Available at SSRN: https : //papers.ssrn.com/sol 3 /papers.cfm ? abstract id = 2868473.
- Felker, T., Mazalov, V., &amp; Watt, S. M. (2014). Distance-based high-frequency trading. Procedia Computer Science , 29:2055-2064.
- Fletcher, T., Hussain, Z., &amp; Shawe-Taylor, J. (2010). Multiple kernel learning on the limit order book. In WAPA , pages 167-174.
- Galeshchuk, S. (2016). Neural networks performance in exchange rate prediction. Neurocomputing , 172:446-452.
- Gould, M. D., Porter, M. A., Williams, S., McDonald, M., Fenn, D. J., &amp; Howison, S. D. (2013). Limit order books. Quantitative Finance , 13(11):17091742.
- Hallgren, J. &amp; Koski, T. (2016). Testing for causality in continuous time bayesian network models of high-frequency data. arXiv preprint arXiv:1601.06651 .
- Han, J., Hong, J., Sutardja, N., &amp; Wong, S. F. (2015). Machine learning techniques for price change forecast using the limit order book data.
- Hasbrouck, J. (2009). Trading costs and returns for us equities: Estimating effective costs from daily data. The Journal of Finance , 64(3):1445-1477.
- Hasbrouck, J. &amp; Saar, G. (2013). Low-latency trading. Journal of Financial Markets , 16(4):646-679.
- Huang, G.-B., Zhou, H., Ding, X., &amp; Zhang, R. (2012). Extreme learning machine for regression and multiclass classification. IEEE Transactions on Systems, Man, and Cybernetics, Part B (Cybernetics) , 42(2):513-529.
- Iosifidis, A., Tefas, A., &amp; Pitas, I. (2017). Approximate kernel extreme learning machine for large scale data classification. Neurocomputing , 219:210-220.
- Kalay, A., Sade, O., &amp; Wohl, A. (2004). Measuring stock illiquidity: An investigation of the demand and supply schedules at the tase. Journal of Financial Economics , 74(3):461-486.

- Kalay, A., Wei, L., &amp; Wohl, A. (2002). Continuous trading or call auctions: Revealed preferences of investors at the tel aviv stock exchange. the Journal of Finance , 57(1):523-542.
- Kearns, M. &amp; Nevmyvaka, Y. (2013). Machine learning for market microstructure and high frequency trading. High frequency trading: New realities for traders, markets and regulators. Risk Books.
- Kercheval, A. N. &amp; Zhang, Y. (2015). Modelling high-frequency limit order book dynamics with support vector machines. Quantitative Finance , 15(8):13151329.
- Kim, A. J. (2001). Technical report. Input/Output Hidden Markov Models for Modeling Stock Order Flows (No. 1370). MITAI Lab Tech. Rep.
- Levendovszky, J. &amp; Kia, F. (2012). Prediction based-high frequency trading on financial time series. Periodica Polytechnica. Electrical Engineering and Computer Science , 56(1):29.
- Li, X., Xie, H., Wang, R., Cai, Y., Cao, J., Wang, F., Min, H., &amp; Deng, X. (2016). Empirical analysis: stock market prediction via extreme learning machine. Neural Computing and Applications , 27(1):67-78.
- Liu, J. &amp; Park, S. (2015). Behind stock price movement: Supply and demand in market microstructure and market influence. The Journal of Trading , 10(3):13-23.
- Maglaras, C., Moallemi, C. C., &amp; Zheng, H. (2015). Optimal execution in a limit order book and an associated microstructure market impact model. Availab le at SSRN: https : //papers.ssrn.com/sol 3 /papers.cfm ? abstract id = 2610808.
- Majhi, R., Panda, G., &amp; Sahoo, G. (2009). Development and performance evaluation of flann based model for forecasting of stock markets. Expert systems with applications , 36(3):6800-6808.
- Malik, A. &amp; Lon Ng, W. (2014). Intraday liquidity patterns in limit order books. Studies in Economics and Finance , 31(1):46-71.
- Mankad, S., Michailidis, G., &amp; Kirilenko, A. (2013). Discovering the ecosystem of an electronic financial market with a dynamic machine-learning method. Algorithmic Finance , 2(2):151-165.
- Næs, R. &amp; Skjeltorp, J. A. (2006). Order book characteristics and the volumevolatility relation: Empirical evidence from a limit order market. Journal of Financial Markets , 9(4):408-432.
- O'Hara, M. &amp; Ye, M. (2011). Is market fragmentation harming market quality? Journal of Financial Economics , 100(3):459-474.

- Pai, P.-F. &amp; Lin, C.-S. (2005). A hybrid arima and support vector machines model in stock price forecasting. Omega , 33(6):497-505.
- Palguna, D. &amp; Pollak, I. (2016). Mid-price prediction in a limit order book. IEEE Journal of Selected Topics in Signal Processing , 10(6):1083-1092.
- Panayi, E., Peters, G. W., Danielsson, J., &amp; Zigrand, J.-P. (2016). Designating market maker behaviour in limit order book markets. Econometrics and Statistics .
- Ranaldo, A. (2004). Order aggressiveness in limit order book markets. Journal of Financial Markets , 7(1):53-74.
- Rehman, M., Khan, G. M., &amp; Mahmud, S. A. (2014). Foreign currency exchange rates prediction using cgp and recurrent neural network. IERI Procedia , 10:239-244.
- Sandoval, J. &amp; Hern´ andez, G. (2015). Computational visual analysis of the order book dynamics for creating high-frequency foreign exchange trading strategies. Procedia Computer Science , 51:1593-1602.
- Seddon, J. J. &amp; Currie, W. L. (2017). A model for unpacking big data analytics in high-frequency trading. Journal of Business Research , 70:300-307.
- Sharang, A. &amp; Rao, C. (2015). Using machine learning for medium frequency derivative portfolio trading. arXiv preprint arXiv:1512.06228 .
- Siikanen, M., Kanniainen, J., &amp; Luoma, A. (2017a). What drives the sensitivity of limit order books to company announcement arrivals? Available at SSRN: https : //papers.ssrn.com/sol 3 /papers.cfm ? abstract id = 2891262.
- Siikanen, M., Kanniainen, J., &amp; Valli, J. (2017b). Limit order books and liquidity around scheduled and non-scheduled announcements: Empirical evidence from NASDAQ Nordic. Finance Research Letters, 21, 264-271.
- Sirignano, J. (2016). Deep learning for limit order books. Available at SSRN: https : //papers.ssrn.com/sol 3 /papers.cfm ? abstract id = 2710331.
- Suwanpetai, P. (2016). Estimation of exchange rate models after news announcement. In Sixth Asia-Pacific Conference on Global Business, Economics, Finance and Social Sciences . AP16Thai Conference.
- Talebi, H., Hoang, W., &amp; Gavrilova, M. L. (2014). Multi-scale foreign exchange rates ensemble for classification of trends in forex market. Procedia Computer Science , 29:2065-2075.
- Vella, V. &amp; Ng, W. L. (2016). Improving risk-adjusted performance in high frequency trading using interval type-2 fuzzy logic. Expert Systems with Applications , 55:70-86.

- Yang, S., Paddrik, M., Hayes, R., Todd, A., Kirilenko, A., Beling, P., &amp; Scherer, W. (2012, March). Behavior based learning in identifying high frequency trading strategies. In Computational Intelligence for Financial Engineering &amp; Economics (CIFEr), 2012 IEEE Conference on (pp. 1-8). IEEE.
- Yang, S. Y., Qiao, Q., Beling, P. A., Scherer, W. T., &amp; Kirilenko, A. A. (2015). Gaussian process-based algorithmic trading strategy identification. Quantitative Finance , 15(10):1683-1703.
- Yu, Y. (2006, October). The Limit Order Book Information and the Order Submission Strategy: A Model Explanation. In Service Systems and Service Management, 2006 International Conference on (Vol. 1, pp. 687-691). IEEE.
- Zhang, K., Kwok, J. T., &amp; Parvin, B. (2009, June). Prototype vector machine for large scale semi-supervised learning. In Proceedings of the 26th Annual International Conference on Machine Learning (pp. 1233-1240). ACM.
- Zheng, B., Moulines, E., &amp; Abergel, F. (2012). Price jump prediction in limit order book. Available at SSRN: https : //papers.ssrn.com/sol 3 /papers.cfm ? abstract id = 2026454.
