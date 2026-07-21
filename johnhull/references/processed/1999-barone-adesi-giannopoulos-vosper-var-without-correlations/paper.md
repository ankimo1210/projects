---
paper_id: "1999-barone-adesi-giannopoulos-vosper-var-without-correlations"
title: "VaR Without Correlations for Portfolios of Derivative Securities"
authors: "Giovanni Barone-Adesi; Kostas Giannopoulos; Les Vosper"
year: "1999"
source_url: "https://doc.rero.ch/record/306980"
source_pdf: "references/papers/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf"
source_sha256: "787964528e645ecdf2c6bbf494f8dac345e69b2fcfc1a38c1777251708807d30"
converter: "PyMuPDF4LLM 1.28.0"
---

<!-- page: 1 -->

![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0001-00.png)


<!-- Start of picture text -->
Decanato della Facolta di Scienze economiche<br><!-- End of picture text -->

<!-- page: 2 -->

# **VaR Without Correlations for Portfolios of Derivative** 

# **Securities** 

**_Giovanni Barone-Adesi_** 

U.S.I., Lugano 

& 

City University Business School, London 

## **_Kostas Giannopoulos_** 

University of Westminster, London 

## **_Les Vosper_** 

The London Clearing House Ltd 

April 1997 

Revised September 1998 

Revised  March  1999

<!-- page: 3 -->

## _Abstract_ 

_We propose filtering historical simulation by GARCH processes to model the future distribution of assets and swap values.  Options’ price changes are computed by full reevaluation on the changing prices of underlying assets.  Our methodology takes implicitly into account assets’ correlations without restricting their values over time or computing them explicitly.  VaR values for portfolios of derivative securities are obtained without linearising them. Historical simulation assigns equal probability to past returns, neglecting current market conditions. Our methodology is a refinement of historical simulation._ 

## **1 INTRODUCTION** 

Current methods of evaluating the risk of portfolios of derivative securities are unsatisfactory. Delta-gamma hedging becomes unstable for large asset price changes or for options at the money with short maturities (Allen 1997). Monte-Carlo simulations assume a particular distributional form, imposing the structure of the risk that they were supposed to investigate. Moreover, they often use factorisation techniques that are sensitive to the ordering of the data. Historical simulations usually sample from past data with equal probabilities. Therefore they are appropriate only if returns are i.i.d. (independently and identically distributed), an assumption violated by volatilities changing over time.This misspecification leads to inconsistent estimates of Value at Risk,as documented by Hendricks (1996) and  Mc Neal and Frei (!998). 

An overview of VaR (Value at Risk) estimation techniques is available in Davé and Stahl (1997). They show the effects of ignoring non-normality and volatility clustering in the computation of VaR. Even for the simple portfolios they consider current VaR methodologies underestimate substantially the severity of losses. From their results they infer that historical simulation modulated by a GARCH process is likely to be a better method. Such a technique is implemented with good results by Barone-Adesi, Bourgoin & Giannopoulos (1998) for a portfolio replicating a stock market index. 

We propose to extend the recent methodology of Barone-Adesi, Bourgoin & Giannopoulos (1998) to portfolios with changing weights that may also include

<!-- page: 4 -->

derivative securities. Following them we model changes in asset prices to depend on current asset volatilities. Asset volatilities are simulated to depend on the most recently sampled portfolio returns. Our simulation is based on the combination of GARCH modelling (parametric) and historical portfolio returns (non-parametric).  Historical residual returns are adapted to current market conditions by scaling them by the ratio of current over past conditional volatility. By dividing historical residual returns by this volatility we standardise them for our simulation. These standardised residuals are then scaled by a volatility forecast that reflects current market conditions.  Our simulated returns are based on these residuals. 

The simulated returns are the basis of our simulation. To simulate a pathway of returns for each of a number of different assets over next 10 days we select randomly 10 past sets or “strips” of returns, each return in a strip corresponding to an asset’s price change which occurred on a day in the past. Thus each strip of returns represents a sample of the co-movements between asset prices. We compute residual returns from the returns.   We then iteratively construct the daily volatilities for each asset that each of these strips of residuals imply according to the chosen GARCH model. We use ratio of these volatilities over historical volatility to change the scale of each of our sampled residuals. The resulting simulated asset returns therefore reflect current market conditions rather than historical ones. Derivatives on the assets are simulated by full re-evaluation at each point in time. 

GARCH models are based on the assumption that residual asset returns follow a normal distribution. If  residual returns are not normal GARCH estimates may be consistent but inefficient. A better filter could then be selected. Following a large literature in financial econometrics we will focus on GARCH. 

In principle  any GARCH or other time series model is suitable for our methodology provided it generates i.i.d residuals from our return series. Therefore residual diagnostics as well as the Rsquare of the Pagan-Ullah regression are important criteria for our model selection. The high t-statistics of our model parameters suggest that our models are wellspecified. Missspecification would result in poor predictions of conditional variances leading to poor backtesting results.

<!-- page: 5 -->

The core of our methodology is the historical returns of the data. The “raw” returns, however,  are unsuitable for historical simulation because they do not fulfil the properties<sup>1</sup> necessary for reliable results. 

Among others Mandelbrot (1963) found that most financial series contain volatility clusters. In VaR analysis, volatility clusters imply that the probability of a specific loss being incurred is not the same on each day. During days of higher volatility we will expect larger than usual losses. 

## **SIMULATING A SINGLE PATHWAY** 

In our simulation we do not impose any theoretical distribution on the data. We use the empirical (historical) distribution of the return series. To render returns i.i.d. we need to remove any serial correlation and volatility clusters present in the dataset. Serial correlations can be removed by adding an MA term in the conditional mean equation. To remove volatility clusters it is necessary to model the process that generates them. We propose to capture volatility clusters by modelling returns as GARCH processes (Bollerslev, 1986)<sup>2</sup> . When appropriate we insert a moving average (MA) term in the conditional mean equation (1) to remove any serial dependency. As an example an ARMA-GARCH(1,1) model can be written as: 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0005-06.png)


where µ is the AR(1) term, θ is the MA term, ω is a constant and ε _t_ the random residual. 

The GARCH(1,1) equation defines the volatility of ε _t_ as a function of the constant ω plus two terms reflecting the contributions of the most recent surprise ε _t_ − 1 and the last 

> 1 For simulation, returns should be random numbers drawn from a stationary distribution  i.e. they should be identically and independently distributed (i.i.d.). 

> 2 The particular form of GARCH process used for a series was determined by statistical testing. Although the GARCH(1,1) specification is suitable for most series it may not be adequate for all the assets in the portfolio. Its failure may produce residuals that are not i.i.d. and do not satisfy the requirements of our historical simulation. We are currently investigating, in a different study, the relevance of GARCH mispecification on our VaR computations.

<!-- page: 6 -->

_VaR Without Correlations for Portfolios of Derivative Securities_ 

period’s volatility _h_ t-1 , respectively. The constants α and γ determine the influence of the last observation and its asymmetry. 

^ To standardise residual returns we need to divide the estimated residual, ε _t_<sup>by the</sup> 

^ corresponding daily volatility estimate, _ht_ 3. Thus, the standardised residual return is given as: 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0006-05.png)


Under the GARCH hypothesis the set of standardised residuals are independently and identically distributed (i.i.d.) and therefore suitable for historical simulation. Empirical observations may depart from that to some degree. 

As Barone-Adesi, Bourgoin and Giannopoulos (1998) have shown, historical standardised innovations can be drawn randomly (with replacement) and after being scaled with current volatility, may be used as innovations in the conditional mean (1) and variance (2) equations to generate pathways for future prices and variances respectively. Our methodology stands as follows: 

- we draw standardised residual returns as a random vector ε _t_ of outcomes from a data set Θ : 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0006-09.png)


- 

- • to get the innovation forecast (simulated) value for period t+1, _zt_ + 1 ,  we draw a random standardised residual return from the dataset `T` and scale it with the volatility of period<sup>4</sup> t+1 : 

> 3 Henceforth, simply  h and ε . 

> <sup>4</sup> The variance of period t+1  can be calculated at the end of period t as: 

> 2 � _h_ t+1  = ω<sup>�</sup> + α<sup>�</sup> ε _t_ + β _h_ t, in which ε _t_ is the latest estimated residual return in (1).

<!-- page: 7 -->

![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0007-02.png)


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0007-03.png)


- we begin simulation of the pathway of the asset’s price from the currently known asset * 

- price, at period t. The simulated price _pt_ + 1 for t+1 is given as 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0007-05.png)


where _z_<sup>*</sup> is estimated as in (4). 

For i = 2, 3...  the volatility is unknown and must be simulated from the randomly selected re-scaled residuals.  In general _ht_ * + _i_ , the (simulated) volatility estimate for period t+i, is obtained as: 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0007-08.png)


where _z_<sup>*</sup> is estimated as in (4). 

* * New elements ε _t_ are drawn from the dataset `T` to form the simulated prices _pt_ + _i_ as in (5). 

The “empirical” distribution of simulated prices at the chosen time horizon (e.g. i = 10) for a single asset is obtained by replicating the above procedure a large number of times e.g. 5000. 

## **2 SIMULATING MULTIPLE PATHWAYS** 

To estimate risks for a portfolio of multiple assets we need to preserve the multivariate properties of asset returns;  however, methodologies which use the correlation matrix of asset returns encounter various problems with this.  The use of conditional multivariate econometric models which allow for correlations to change over time is restricted to a few series at a time.  The number of terms in a correlation matrix increases with the square of the number of assets in the portfolio:  for large portfolios the number of pairwise correlations becomes unmanageable.

<!-- page: 8 -->

When estimating time-varying correlation coefficients independently from each other, there is no guarantee that the resulting matrix satisfies the multivariate properties of the data.  In fact the resulting matrix may not be positive definite. 

Additionally, the estimation of VaR from the correlation matrix requires knowledge of the probability distribution of each asset series.  However, empirical distributions may not conform to any known distribution:  often the empirical histograms are smoothed and forced to follow a known distribution convenient for the calculations.  VaR measures which are based on arbitrary distributional assumptions may be unreliable;  preliminary smoothing of data can cover up the non-normality of the data;  VaR estimation, which is highly dependent on the good prediction of uncommon events, may be adversely affected from smoothing the data. 

Finally, correlations measured from daily returns can be demonstrated to be unstable. Even their sign is ambiguous.  Estimated correlation coefficients can be the subject of such great changes at any time, which even conditional models do not capture, that the successful forecast of portfolio losses may be seriously inhibited. 

Our approach does not employ a correlation matrix.  For a portfolio of multiple assets we extend our simulation methodology<sup>5</sup> to simulate multiple pathways.  We select a random date from the dataset, which will have an associated set of residual returns.  This “strip” of residual returns, derived at a common date in the past, is one sample from which we begin modelling the co-movements between respective asset prices. 

Thus for each asset for i = 1….10 days we have the sampled residuals denoted by subscripts 1, 2, 3,....,  for the different assets. 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0008-07.png)


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0008-08.png)


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0008-09.png)


> 5 Additional reading about the this methodology can be found in Efron and Tibshirani (1993).

<!-- page: 9 -->

* with _ei_ ∈Θ and so on for all the assets in the dataset: Θ = {Θ 1<sup>,...,</sup> Θ _N_ }<sup>. From the</sup> dataset Θ of historical standardised innovations, for i = 1, a date is randomly drawn and hence the associated residuals _e_ 1* , _e_ 2* , _e_ 3* are selected.  At i = 2  another date is drawn, with its corresponding residuals, and so on for i = 3, 4....etc.  Thus pathways for variances, _h_ , and prices, _p_ , are constructed for each asset which reflect the comovements between asset prices: 

For i = 1 to 10: 

Asset 1: 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0009-05.png)


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0009-06.png)


Asset 3: 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0009-08.png)


where _z_<sup>*</sup> is estimated as in (4). 

## **3 AN EMPIRICAL INVESTIGATION** 

We illustrate our methodology with a numerical example of a portfolio of three assets. Our hypothetical portfolio is invested across three LIFFE futures contracts  and  a call option on the Long Gilt future with net lots 2,-5, 10 and 7;  lot conversion factors for the contracts are 2500, 500, 2500 and 500  respectively. Our historical data sets consists of two years of daily<sup>6</sup> prices, from 4 January 1994 until 27 December 1995, for three 

> 6 All three contracts are traded on the London International Futures Exchange (LIFFE) at different delivery months.

<!-- page: 10 -->

interest rate futures contracts, the 10-year German Government Bund (A), Long Gilt (G) and the three-month EuroSwiss Franc (S) contracts<sup>7</sup> . 

Given the daily price, _pt_ we obtain the daily returns _rt_ as 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0010-04.png)


and then we form continuous series of historical returns by rolling a few days before the expiration date to the next front month contract. 

For each historical return series we fit the most suitable GARCH-ARMA  specification, as in equations (1) and (2) to obtain i.i.d. residual returns. The parameter estimates together with standard errors and the likelihood value are shown in table 1. 

> 7  The price of the LIFFE Euroswiss contract is derived by subtracting the appropriate forward-forward interest rate from 100. Hence pathway calculations are made using 100 minus the quoted price.

<!-- page: 11 -->

- Table 1: GARCH Estimates 

|Series|ω|α<br>|β<br>|γ|µ<br> θ|R squared|ML|
|---|---|---|---|---|---|---|---|
|A|0|0.07754|0.86421|-0.00292083|-0.4310|0.381|-1383.99|
|StdError||0.023|0.033|0.000767|0.044|||
|G|0|0.042527794|0.910057127|0.006027014|0|0.313|-1562.43|
|Std Error||0.01286|0.02324|0.00098939||||
|S|1.797378*10<sup>~~-5~~</sup><br>|0.123744|0.791801||0|0.324|-2026.21|
|Std Error|8.914*10<sup>~~-6~~</sup>|0.0298|0.064|||||


The low standard errors as well as the residual statistics (not reported) support our parametrization choices. The equations are estimated in four steps. First by OLS to get starting values, then by downhill simplex (because its robustness to bad starting values and discontinuities). The BHHH algorithm was then used to refine convergence and finally a quasi Newton method, the BFGS, was used to get reliable standard errors. 

As an example let the current close business be February 21, 1996; we want to estimate the portfolio VaR over the next 2 business days.  The closing prices and annualised volatilities for the three futures on that date are reported in table 2: 

- Table 2: Close Prices and conditional volatility on 21&22 February 

||Prices on Feb<br>21<br> <br>|Return at Close of<br>Business|Vol. p.a.(Feb21)|Vol. p.a.(Feb22)|
|---|---|---|---|---|
|A|97.39|0.00446|0.10053|0.09347|
|G|107.219||0.10086|0.09623|
|S|97.48||0.37021|0.35436|
|Call option (G)|0.67169||||


The conditional volatility of the next date, i.e. February 22, is calculated by substituting the last trading date’s residual error and variance into equation (2). To simulate asset prices for February 22 we draw a random (with replacement) row<sup>8</sup> of  historical 

> <sup>8</sup> A row contains the –standardised - innovations that occur on a random date from the past across all contracts.

<!-- page: 12 -->

(standardised) asset residual returns<sup>9</sup> and re-scale them with the corresponding asset’s volatility on February 22 to form a random surprise, ε t , in equation (1). In this way we generate parallel pathways for all linear assets in the portfolio without imposing the degree of cross correlation between the assets. By taking a row of random residuals we maintain the co-movement between the assets when we generate the simulated forecasts. 

Table 3 shows a sample of the standardised residuals for each asset used in our simulation. 

## • Table 3. Historical Standardised Residuals 

|Date|A|G|S|
|---|---|---|---|
|05/01/94|0.00000|0.00000|0.00000|
|06/01/94|-0.15123|0.08776|0.69159|
|07/01/94|0.85533|1.25962|0.00000|
|10/01/94|0.18241|-0.32852|0.96747|
|11/01/94|-0.24443|-0.94479|-0.58417|
|12/01/94|0.29110|0.27269|-0.41143|
|13/01/94|-1.15592|-1.13077|0.86704|
|14/01/94|-0.77676|-0.35823|0.65085|
|17/01/94|-0.38586|0.27006|-0.22329|
|18/01/94|0.32893|1.20579|-0.23623|
|.|.|.|.|
|13/11/95|0.93074|0.43796|-0.72107|
|.|.|.|.|
|21/02/96|0.40954|1.01243|0.085935|


- Let us assume that the random set of standardised residuals are :  -1.15592, 

- -1.13077 and 0.86704 

for A, G and S<sup>10</sup> contracts respectively<sup>11</sup> . At the first simulation run, the one date ahead re-scaled residuals, z<sup>*</sup> , for the three futures will be: 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0012-08.png)


> <sup>9</sup> Table 1 is an extract, for illustrative purposes, of standardised residual returns based on closing prices for three futures over a two year period.  We can have as many columns of residual returns as there are assets, or as in the case of swaps in a given currency, a set of columns of interest rate residual returns e.g. from 1 day to 10 years per currency, from which swap evaluations may be performed. 10 This set corresponds to the 13.01.94 

> 11 As the random sampling is with replacement, we may draw the same date more than once during the simulation process.

<!-- page: 13 -->

![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0013-02.png)


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0013-03.png)


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0013-04.png)


These are also the innovations for equation (1). Recall from equation (5) the ith forecast for 22 February is given by: 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0013-06.png)


where ( µ<sup>�</sup> _i_ rt +<sup>θˆ</sup> _i_<sup>*z*</sup> i,t<sup>+z*</sup> i,t+1<sup>) is the simulated return. This gives us:</sup> 

A: p<sup>*</sup> 1,t+1<sup>=  97.39 +97.39(-0.43084*0.00446+-0.00680612)</sup> = 97.39+97.39(-0.00872862) = 96.5399197 

G: p<sup>*</sup> 2,t+1<sup>= 107.219 +(107.219*-0.00685464)= 106.4840526</sup> 

S: p<sup>*</sup> 3,t+1<sup>= 100-(2.52+(2.52*0.019354571)=97.43122648</sup> � Working price =100- 97.43122648 =2.56877 

To produce the ith simulated volatility for the second date ahead we substitute ε t-1 with 

* * * _z_ 1, _t_ + 1<sup>,</sup><sup>_z_</sup> 2, _t_ + 1<sup>,</sup><sup>_z_</sup> 3, _t_ + 1<sup>, in (2).  Hence the simulated variance for February, 23 1996 for</sup> contract A is: 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0013-13.png)


=  0 +0.07754(-0.00680612+ -0.00292083)<sup>2</sup> +0.86421*0.00003467  = 0.0000373 

Similarly we calculate the ith simulated variances for contracts G and S to be

<!-- page: 14 -->

![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0014-02.png)


We repeat the above calculations to get the N days ahead forecasts of the variances and prices for each of the three futures contracts. For example to obtain the 2 day ahead price forecasts:  we randomly sample another row with historical standardised residuals,  for each of the three contracts. Let us assume that this random set corresponds to November 13, 1995, and the values are  0.93074, 0.43796,  -0.72107, for A, G and S respectively. When these random historical standardised residuals are re-scaled by the day 2 simulated volatilities the following set of scaled residuals are produced: 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0014-04.png)


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0014-05.png)


* * * Hence, _z_ 1, _t_ + 2<sup>,</sup><sup>_z_</sup> 2, _t_ + 2<sup>,</sup><sup>_z_</sup> 3, _t_ + 2<sup>are the simulated residuals for February 23. Therefore, the</sup> simulated set of prices for the same date will be: 

- A: p<sup>*</sup> 1,t+2<sup>=  96.5399197+96.5399197* ( -0.43084*-0.00872862+0.00568421)</sup> = 97.45172459 

G: p<sup>*</sup> 2,t+2<sup>=  106.4840526+106.4840526*0.002787115</sup> = 106.780836 

S: p<sup>*</sup> 3,t+2<sup>=  100-(2.56877+2.56877* -0.015446403)</sup> = 97.47090479 

Note µ 2 and µ 3 = 0 so the AR term is absent in these equations.

<!-- page: 15 -->

_VaR Without Correlations for Portfolios of Derivative Securities_ 

The above steps can be repeated to produce the entire set of, let us say 5000, simulated values. Figure 1 illustrates examples of distributions of price pathways for 21.02.96,  for the LIFFE German Bund financial futures contract. 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0015-03.png)


<!-- Start of picture text -->
1 Day ahead Empirical Distribution for Contract A<br>300<br>250<br>200<br>150<br>100<br>50<br>0<br>Frequency<br>94.65 94.85 95.04 95.24 95.44 95.63 95.83 96.02 96.22 96.42 96.61 96.81 97.01 97.20 97.40 97.60 97.79 97.99 98.18 98.38 98.58 98.77 98.97 99.17<br><!-- End of picture text -->

**Figure 1.** The 1-day ahead distribution of German Bund Futures Prices 

Similarly, for longer VaR horizons our steps can be repeated to obtain a simulated pathway for each date ahead.  Figure 2 shows the distribution of the 5000 simulation runs for the 10<sup>th</sup> date ahead for the German Bund. The asymmetry of our simulated distribution is apparent.

<!-- page: 16 -->

**Figure 2.** The 10-day ahead distribution of German Bund Futures Prices over 5000 runs 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0016-03.png)


<!-- Start of picture text -->
10 Day Ahead Empirical Distribution for Contract A<br>400<br>350<br>300<br>250<br>200<br>150<br>100<br>50<br>0<br>Frequency<br>82.91 83.91 84.90 85.90 86.90 87.90 88.90 89.89 90.89 91.89 92.89 93.89 94.88 95.88 96.88 97.88 98.88 99.87 100.87 101.87 102.87 103.86 104.86 105.86<br><!-- End of picture text -->

## **3.1 Options** 

Options price paths are obtained from the corresponding asset price paths by using an options pricing model applied to each asset price in the path and other relevant option pricing parameters e.g. implied volatility, σ , strike price, x, time to expiry, T-t, and interest rate, r .  For the present we keep the values of these other parameters equal to their values at the start of simulation. 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0016-06.png)


where _pt_ is the underlying asset price at current time t.  The price path for the call option on a given asset is: 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0016-08.png)


Where _pt_ ,..., _pt_ + _i_<sup>is the first vector (i.e. for the first asset) from (15).</sup>

<!-- page: 17 -->

Additional option pathways use the asset prices from the corresponding asset price vectors in (15).  Figure 3 illustrates an example of the ten day ahead distribution of prices for an out-of-the money call option, for 5000 simulation runs on the LIFFE Long Gilt futures contract. The time to expiry was one and a half months (expiry date 22/3/96), the strike price was 108 points and the underlying futures price was 107.219. The option’s market price was 0.670 and the ten-day median forecast price was 0.477. The minimum price was 0.00018 and the maximum 4.82152 illustrating the non-linearity of option pricing. 

Using the Black ’76 model and the futures price path for contract G the following price pathway was generated for the call option above. 

Table 4: Option Pricing Model Input Values and Results 

||Close of Business|One Day Ahead|Two Days Ahead|
|---|---|---|---|
|Futures Price Path|107.219|106.4841|106.7808|
|Strike Price|108.00|108.00|108.00|
|Implied Volatility|0.08|0.08|0.08|
|Time to Expiry|0.087302|0.083333|0.079365|
|Call Path(generated<br>by Black ’76 model)|0.67169|0.40956|0.47953|

<!-- page: 18 -->

![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0018-02.png)


<!-- Start of picture text -->
Figure 3<br><!-- End of picture text -->


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0018-03.png)


<!-- Start of picture text -->
Empirical Distribution for Call G for April 1996<br>900<br>800<br>700<br>600<br>500<br>400<br>300<br>200<br>100<br>0<br>Prices<br>Frequency<br>0.000 0.223 0.445 0.668 0.891 1.113 1.336 1.559 1.781 2.004 2.227 2.449 2.672 2.895 3.117 3.340 3.563 3.785 4.008 4.231 4.453 4.676 4.899 5.121<br><!-- End of picture text -->

## **3.2 Aggregating Asset Pathways to Obtain Portfolio Pathways** 

For the first simulation we select the asset pathways which correspond to the contracts in the portfolio.  These are the vectors 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0018-06.png)


for n assets and a time horizon of i days. The position-weighted pathways in the portfolio are the vectors: 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0018-08.png)


where the scalars w1, w2, w3,....,wn  are the weights of contracts in the portfolio.

<!-- page: 19 -->

The vectors of  pathways are added to form the portfolio path π t+ τ 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0019-03.png)


The price pathways above are modified by weights derived by multiplying together the relevant number of lots, the lot conversion factor and the currency rate  (to Sterling). The exchange rate from DM is taken to be constant at 2.24 and the exchange rate from Swiss francs to Sterling taken constant at 1.82. The lot conversion factors are 2500 for the Euroswiss and Bund contracts  and 500 for both Long Gilt contracts 

A: w1p1{t,,t+1,t+2}=    1/(2.24)*2500*2[97.3900, 96.5399, 97.4517] = [£217388, £215491, £217526] 

G: w2p2,{t,t+1,t+2} =  500*-5[107.2190, 106.4841, 106.7808] =[-£268048, -£266210, -£266952] 

Call Option on G = 500*7[0.6717, 0.4096, 0.4759] = [£2351, £1433, £1666] 

S: w3p3,{t.t+1,1+2} = 1/(1.82)*2500*10[97.4800, 97.4312,97.4709] = [£1292, £788, £915] 

Thus the portfolio path based on prices is π t,t+1,t+2 = w1p1{t,,t+1,t+2}+ w2p2,{t,t+1,t+2}+ w3p3,{t.t+1,1+2} = [£217388,     £215491,  £217526] +[-£268048, -£266210, -£266952] + [£1292,       £788,        £915] + [£2351,       £1433,      £1666] = [-£47016, -£48498, -£46845] 

The change in the portfolio’s value after 2 days from its closing value is 

(-£46844.92496) -(-£47016.4787) = £171.5537 which in this (first) simulation path is a gain in value. 

By repeating the above procedure with different random values the empirical distribution of portfolio values can be obtained.  The  representative “lowest value” of the portfolio e.g. for the 99<sup>th</sup> percentile, can be compared to the value of the portfolio at the start of simulation, to obtain the 99<sup>th</sup> percentile loss.  A ten-day ahead multi-contract portfolio

<!-- page: 20 -->

_VaR Without Correlations for Portfolios of Derivative Securities_ 

example (a portfolio of futures and options in a variety of LIFFE contracts) is illustrated in Figure 4:

<!-- page: 21 -->

### **��������** 

10-day ahead Portfolio Value Distribution over 5000 Simulations 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0021-04.png)


<!-- Start of picture text -->
Histogram for Sample Member Portfolio<br>300<br>250<br>200<br>150<br>100<br>50<br>0<br>Simulated Values<br>Frequency<br>1280282 1281170 1282058 1282946 1283834 1284722 1285610 1286498 1287386 1288274 1289163 1290051 1290939 1291827 1292715 1293603 1294491 1295379 1296267 1297155 1298043 1298931 1299819 1300707<br><!-- End of picture text -->

## **4 SWAPS** 

Our methodology can be applied to any type of asset.  We may have a portfolio comprising exchange traded futures and options, interest rate and currency swaps and swaptions. 

For example a swap with three cash-flows remaining before it matures has its value denoted by an appropriate swap valuation function of zero coupon interest rates: 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0021-08.png)


where φ represents parameters defined in the swap contract necessary to value it (e.g. coupon, floating and fixed interest rates, notional principal amount, payment dates of the cash-flows, maturity date, etc.); ι 1 , ι 2 , and ι 3 are zero coupon interest rates (term

<!-- page: 22 -->

structure) for dates corresponding to the future payment dates.  The value of a swap at a given close of business will utilise the zero coupon rates (term structure) at this time. 

We consider interest rate swaps to demonstrate how the methodology may be applied. A pathway of swap values is obtained by simulating zero coupon interest rates curves.  For the first scenario we simulate 10 zero coupon rates  for each day of the holding period. This is replicated to obtain 5000 such simulations.   To simulate a zero coupon rate curve we need to define how we create it from the source interest rates e.g. money market rates, interest rate futures and quoted swap rates for various maturities e.g. to 10 years.  These source rates, which could be depicted as a curve, allow a zero coupon rate curve to be created<sup>12</sup> from them;  the zero coupon rate curve is defined by points of constant maturity which correspond to the maturities of the source rates. 

We treat each of the source rates as an asset and simulate a single pathway for each source rate, as described in the foregoing sections for futures pathways i.e. starting from logarithmic returns from historical time series of (constant maturity) source interest rates. We obtain a pathway for each source interest rate at the current close of business i.e. we simulate the source interest rate curve for each day of the holding period (i=10).  For each of these we apply the methodology, described by Hull (1997), to convert them to zero coupon interest rate curves.  Replication of the process obtains 5000 zero coupon rate curves defined by a small number (ten) constant maturity points. 

Interest rate swaps are evaluated from each of the simulated yield curves.  This necessitates interpolation between the constant maturity points.  During the simulation process we use linear interpolation as we believe this to be sufficiently accurate for simulation processes and much faster to compute than other methods (e.g. cubic splines), given the number of simulations we require. 

In this way we create pathways of swaps prices which correspond in order (a holding period of 10 days over 5000 scenarios) to the futures and options pathways.  The 5000 simulated portfolio values for exchange traded instruments and interest rate derivatives together can therefore be estimated, regardless of type or currency of instrument. 

> 12 The methodology for the creation of zero coupon rate curves is described  in “Options, Futures and Other Derivatives”, by John C. Hull, Prentice Hall (1997).

<!-- page: 23 -->

Figure 5 is an example of the term structure of interest rates out to 10 years for Sterling prior to simulatation, produced by linear interpolation: 

### **��������** 

#### **GBP Term Structure** 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0023-05.png)


<!-- Start of picture text -->
7.60%<br>7.40%<br>7.20%<br>7.00%<br>6.80%<br>6.60%<br>6.40%<br>6.20%<br>6.00%<br>0 1 2 3 4 5 6 7 8 9 10<br>years<br><!-- End of picture text -->

For simplicity, if we consider that the three asset (interest rate) pathways from equations (11), (13) and (15) correspond to the cash-flow dates for our swap (no interpolation of rates required), then writing ι<sup>*</sup> for _p_<sup>*</sup> , we depict the 10 x 3 matrix: 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0023-07.png)


where i = 1 to 10 days.

<!-- page: 24 -->

Each column of the matrix represents equations (11), (13) and (15) respectively i.e. they are the asset pathways to 10 days. To obtain a swap value pathway we require a row from the matrix for each day in the swap value path: 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0024-03.png)


For swap portfolios, the swap value pathways are aggregated as described generally for any set of assets, in equations (19) to (21); the net positions wn for swaps can be represented as +1 or -1 for each swap, to describe the payment or receipt of fixed interest cash-flows respectively.  Furthermore, aggregated values for portfolios of swaps and futures and options contracts may be obtained with no fundamental change to our methodology.  5000 simulation runs may be performed for portfolios of swaps, futures and options, from which worst case losses can be obtained.<sup>13</sup> 

In figure 6, we simulate 5000 values of a random portfolio of “plain vanilla” interest rate swaps in Sterling, over a 10 day holding period.  The 5000 portfolio values are obtained from 5000 simulated interest rate term structures. 

> 13 Appropriate currency exchange rates for the given close of business are currently used in the simulations where contracts are denominated in different currencies, to convert all values to a common currency.

<!-- page: 25 -->

Figure 6: 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0025-01.png)


<!-- Start of picture text -->
GBP Contracts<br>Yd<br>6a<br>30<br>4a<br>30<br>20<br>1d<br>a<br>4480,000 5,120,000 5,760,000 6,400,000<br><!-- End of picture text -->

<!-- page: 26 -->

### **��������** 

**Sterling Interest Rate Term Structures:  actual and after simulation, at 99th percentile and 10 day holding period** 


![](assets/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf-0026-04.png)


<!-- Start of picture text -->
8.00%<br>7.50%<br>7.00%<br>6.50%<br>6.00%<br>5.50%<br>5.00%<br>years<br>actual after 10 days simulated for 99th percentile<br>0 1 2 3 4 5 6 7 8 9 10<br><!-- End of picture text -->

## **5 CONCLUSION** 

Our methodology simulates the returns of portfolios of derivative securities taking into account information available on current market conditions.  We preserve the information on historical non-normalities of security returns and their co-movements, without introducing the complexities and the noise associated with the computation of  large covariance matrices. 

Our methodology leads to a fast evaluation of VaR.  That is possible because it requires a simple historical simulation to be run each day through a preset time-series filter. The number of our computations increases linearly with the number of assets. 

The reliability of our evaluation depends on the quality of the filters used in our time series analysis. A better filter would by definition lead to a better assessment of risk.

<!-- page: 27 -->

Therefore the adequacy of a particular filter in a given context needs to be verified through backtesting. In any event, the necessity of meeting the requirements of historical simulation must be recognised.

<!-- page: 28 -->

## **Bibliography** 

- **Allen  S (1997), “Comparing and Contrasting Different Approaches to Computing Value at Risk”, Risk Conference, New York, July.** 

- **Barone-Adesi G, F Bourgoin & K Giannopoulos (1998), “A Probabilistic Approach to Worst Case Scenarios”,** **_Risk_ , August 1998.** 

- **Bollerslev T (1986), “Generalised Autoregressive Conditional Heteroskedasticity”,** **_Journal of Econometrics_ , 31 , 307-27.** 

- **Davé R and S Gerhard (1997), “On the Accuracy of VaR Estimates Based on the VarianceCovariance Approach”, Olsen & Associates Research Institute, Zurich.** 

- **Efron B and R Tibshirani (1993), “An Introduction to the Bootstrap”,  Chapman & Hall: Monographs on Statistics and Applied Probability 57 .** 

- **Hendricks D (1994), “Evaluation of Value at Risk  Models Using Historical Data”, FRBNY, New York.** 

**Hull J C (1997) “ Options, Futures and Other Derivatives”, Prentice Hall** 

- **Mandelbrot B (1963), “The Variation of Certain Speculative Prices”,** **_Journal of Business_ , 36 , 394-419.** 

- **Mc Neal A and Frei  R  (1998) “Estimation of Tail-Related Risk Measures for Heteroscedastic Financial Time Series : an Extreme Value Approach” ETH, Zurich.** 

## **_________________________________________________________________** 

```
We are grateful to The London Clearing House for their financial
support. In particular we thank Andrew Lamb and Sara Williams for
their continuous support and encouragement. We also thank David
Bolton, Stavros Kontopanos, Clare Larter and Richard Paine for
providing programming assistance and Cassandra Chinkin for
producing the empirical examples.
```

<!-- page: 29 -->

### **QUADERNI DELLA FACOLTÀ** 

_I quaderni sono richiedibili (nell’edizione a stampa) alla Biblioteca universitaria di Lugano via Ospedale 13  CH 6900 Lugano_ 

_tel. +41 91 9124675 ; fax +41 91 9124647 ; e-mail: biblioteca@lu.unisi.ch La versione elettronica (file PDF) è disponibile all’URL: http://www.lu.unisi.ch/biblioteca/Pubblicazioni/f_pubblicazioni.htm_ 

_The working papers (printed version) may be obtained by contacting the Biblioteca universitaria di Lugano via Ospedale 13  CH 6900 Lugano_ 

_tel. +41 91 9124675 ; fax +41 91 9124647 ; e-mail: biblioteca@lu.unisi.ch The electronic version (PDF files) is available at URL: http://www.lu.unisi.ch/biblioteca/Pubblicazioni/f_pubblicazioni.htm_ 

### Quaderno n. 98-01 

**P. Balestra** , _Efficient (and parsimonious) estimation of structural dynamic error component models_ 

### Quaderno n. 99-01 

**M. Filippini** , _Cost and scale efficiency in the nursing home sector : evidence from Switzerland_ 

Quaderno n. 99-02 

**L.Bernardi** , _I sistemi tributari di oggi : da dove vengono e dove vanno_ 

Quaderno n. 99-03 

**L.L.Pasinetti** , _Economic theory and technical progress_ 

Quaderno n. 99-04 

**G. Barone-Adesi, K. Giannopoulos, L. Vosper** , _VaR without correlations for portfolios of derivative securities_
