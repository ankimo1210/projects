---
paper_id: "2018-gatheral-jaisson-rosenbaum-volatility-is-rough"
title: "Volatility Is Rough"
authors: "Jim Gatheral; Thibault Jaisson; Mathieu Rosenbaum"
year: "2018"
source_url: "https://arxiv.org/abs/1410.3394"
source_pdf: "references/papers/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf"
source_sha256: "7e3ef4c07c56e2a137f7486609f06405e2166740de3655f6645db65d6a185368"
converter: "PyMuPDF4LLM 1.28.0"
---

<!-- page: 1 -->

# Volatility is rough 

Jim Gatheral Baruch College, City University of New York jim.gatheral@baruch.cuny.edu 

Thibault Jaisson<sup>_∗_</sup> CMAP, Ecole<sup>´</sup> Polytechnique Paris thibault.jaisson@polytechnique.edu 

Mathieu Rosenbaum LPMA, Universit´e Pierre et Marie Curie (Paris 6) mathieu.rosenbaum@upmc.fr 

October 14, 2014 

##### **Abstract** 

Estimating volatility from recent high frequency data, we revisit the question of the smoothness of the volatility process. Our main result is that log-volatility behaves essentially as a fractional Brownian motion with Hurst exponent _H_ of order 0 _._ 1, at any reasonable time scale. This leads us to adopt the fractional stochastic volatility (FSV) model of Comte and Renault [16]. We call our model Rough FSV (RFSV) to underline that, in contrast to FSV, _H <_ 1 _/_ 2. We demonstrate that our RFSV model is remarkably consistent with financial time series data; one application is that it enables us to obtain improved forecasts of realized volatility. Furthermore, we find that although volatility is not long memory in the RFSV model, classical statistical procedures aiming at detecting volatility persistence tend to conclude the presence of long memory in data generated from it. This sheds light on why long memory of volatility has been widely accepted as a stylized fact. Finally, we provide a quantitative market microstructurebased foundation for our findings, relating the roughness of volatility to high frequency trading and order splitting. 

**Keywords:** High frequency data, volatility smoothness, fractional Brownian motion, fractional Ornstein-Uhlenbeck, long memory, volatility persistence, volatility forecasting, option pricing, volatility surface, Hawkes processes, high frequency trading, order splitting. 

> _∗_ Thibault Jaisson gratefully acknowledges financial support from the chair “Risques Financiers” of the Risk Foundation and the chair “March´es en Mutation” of the French Banking Federation.

<!-- page: 2 -->

## **1 Introduction** 

### **1.1 Volatility modeling** 

In the derivatives world, log-prices are often modeled as continuous semimartingales. For a given asset with log-price _Yt_ , such a process takes the form 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0002-03.png)


where _µt_ is a drift term and _Wt_ is a one-dimensional Brownian motion. The term _σt_ denotes the volatility process and is the most important ingredient of the model. In the Black-Scholes framework, the volatility function is either constant or a deterministic function of time. In Dupire’s local volatility model, see [22], the local volatility _σ_ ( _Yt, t_ ) is a deterministic function of the underlying price and time, chosen to match observed European option prices exactly. Such a model is by definition time-inhomogeneous; its dynamics are highly unrealistic, typically generating future volatility surfaces (see Section 1.3 below) completely unlike those we observe. A corollary of this is that prices of exotic options under local volatility can be substantially off-market. On the other hand, in so-called stochastic volatility models, the volatility _σt_ is modeled as a continuous Brownian semi-martingale. Notable amongst such stochastic volatility models are the Hull and White model [32], the Heston model [31], and the SABR model [29]. Whilst stochastic volatility dynamics are more realistic than local volatility dynamics, generated option prices are not consistent with observed European option prices. We refer to [26] and [39] for more detailed reviews of the different approaches to volatility modeling. More recent market practice is to use local-stochastic-volatility (LSV) models which both fit the market exactly and generate reasonable dynamics. 

### **1.2 Fractional volatility** 

In terms of the smoothness of the volatility process, the preceding models offer two possibilities: very regular sample paths in the case of Black-Scholes, and volatility trajectories with regularity close to that of Brownian motion for the local and stochastic volatility models. Starting from the stylized fact that volatility is a long memory process, various authors have proposed models that allow for a wider range of regularity for the volatility. In a pioneering paper, Comte and Renault [16] proposed to model log-volatility using fractional Brownian motion (fBM for short), ensuring long memory by choosing the Hurst parameter _H >_ 1 _/_ 2. A large literature has subsequently developed around such fractional volatility models, for example [12, 15, 44].

<!-- page: 3 -->

The fBM ( _Wt_<sup>_H_)</sup><sup>_t∈_Rwith Hurst parameter</sup><sup>_H∈_(0</sup><sup>_,_1),introduced in [36],is a</sup> centered self-similar Gaussian process with stationary increments satisfying for any _t ∈_ R, ∆ _≥_ 0, _q >_ 0: 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0003-01.png)


with _Kq_ the moment of order _q_ of the absolute value of a standard Gaussian variable. For _H_ = 1 _/_ 2, we retrieve the classical Brownian motion. The sample paths of _W_<sup>_H_</sup> are H¨older-continuous with exponent _r_ , for any _r < H_<sup>1</sup> . Finally, when _H >_ 1 _/_ 2, the increments of the fBM are positively correlated and exhibit long memory in the sense that 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0003-03.png)


Indeed, Cov[ _W_ 1<sup>_H, W_</sup> _k_<sup>_H−W H_</sup> _k−_ 1<sup>]isoforder</sup><sup>_k_2</sup><sup>_H−_2as</sup><sup>_k→∞_.Notethatin</sup> the case of the fBM, there is a one to one correspondence between regularity and long memory through the Hurst parameter _H_ . 

As mentioned earlier, the long memory property of the volatility process has been widely accepted as a stylized fact since the seminal analyses of Ding, Granger and Engle [20], Andersen and Bollerslev [1] and Andersen et al. [3]. Initially, it appears that the term _long memory_ referred to the slow decay of the autocorrelation function (of absolute returns for example), anything slower than exponential. Over time however, it seems that this term has acquired the more precise meaning that the autocorrelation function is not integrable, see [8], and even more precisely that it decays as a power-law with exponent less than 1. Much of the more recent literature, for example [7, 11, 13], assumes long memory in volatility in this more technical sense. Indeed, meaningful results can probably only be obtained under such a specification, since it is not possible to estimate the asymptotic behavior of the covariance function without assuming a specific form. Nevertheless, analyses such as that of Andersen et al. [3] use data that predate the advent of high-frequency electronic trading, and the evidence for long memory has never been sufficient to satisfy remaining doubters such as Mikosch and St˘aric˘a in [38]. To quote Rama Cont in [17]: 

... the econometric debate on the short range or long range nature of dependence in volatility still goes on (and may probably never be resolved)... 

One of our contributions in this paper is (we believe) to finally resolve this question, showing that the autocorrelation function of volatility does not behave as a power law, at least at usual time scales of observation. This implies 

> 1Actually _H_ corresponds to the regularity of the process in a more accurate way: in terms of Besov smoothness spaces, see Section 2.1.

<!-- page: 4 -->

![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0004-00.png)


<!-- Start of picture text -->
0.6<br>— 05<br>3<br>Zz<br>g 04<br><eg<br>“0.3<br>0.2<br>1.5<br>-0.4<br>-0.2 1.0 “<br>fog, 0.0 osao<br>Ong<br>Wess 1 02 0.5<br>0.4<br><!-- End of picture text -->

<!-- page: 5 -->

![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0005-00.png)


<!-- Start of picture text -->
a<br>on<br>wo<br>ro)<br>0.0 0.5 1.0 1.5 2.0 2.5<br>Time to expiry t<br><!-- End of picture text -->

<!-- page: 6 -->

to have a value of _H_ close to zero. As we will see in Section 2, our empirical estimates of _H_ from time series data are in fact very small. 

The volatility model that we will specify in Section 3.1, driven by fBM with _H <_ 1 _/_ 2, therefore has the potential to be not only consistent with the empirically observed properties of the volatility time series but also consistent with the shape of the volatility surface. In this paper, we focus on the modeling of the volatility time series. A more detailed analysis of the consistency of our model with option prices is left for a future article. 

### **1.4 Main results and organization of the paper** 

In Section 2, we report our estimates of the smoothness of the log-volatility for selected assets. This smoothness parameter lies systematically between 0 _._ 08 and 0 _._ 2 (in the sense of H¨older regularity for example). Furthermore, we find that increments of the log-volatility are approximately normally distributed and that their moments enjoy a remarkable monofractal scaling property. This leads us to model the log of volatility using a fBM with Hurst parameter _H <_ 1 _/_ 2 in Section 3. Specifically we adopt the fractional stochastic volatility (FSV) model of Comte and Renault [16]. We call our model Rough FSV (RSFV) to underline that, in contrast to FSV, we take _H <_ 1 _/_ 2. We also show in the same section that the RFSV model is remarkably consistent with volatility time series data. The issue of volatility persistence is considered through the lens of the RFSV model in Section 4. Our main finding is that although the RFSV model does not have any long memory property, classical statistical procedures aiming at detecting volatility persistence tend to conclude the presence of long memory in data generated from it. This sheds new light on the supposed long memory in the volatility of financial data. In Section 5, we apply our model to forecasting volatility. In particular, we show that RFSV volatility forecasts outperform conventional AR and HAR volatility forecasts. Finally, in Section 6, we present a market microstructure explanation for the regularities we observe in the volatility process at the macroscopic scale. We show that the empirical behavior of volatility may be explained in terms of order splitting and the high degree of endogeneity of the market ascribed to algorithmic trading. Some proofs are relegated to the appendix. 

## **2 Smoothness of the volatility: empirical results** 

In this section we report estimates of the smoothness of the volatility process for four assets: The DAX and Bund futures contracts, for which we estimate integrated variance directly from high frequency data using an estimator based on the model with uncertainty zones, [42, 43], and the S&P and

<!-- page: 7 -->

NASDAQ indices, for which we use precomputed realized variance estimates from the Oxford-Man Institute of Quantitative Finance Realized Library<sup>3</sup> . 

### **2.1 Estimating the smoothness of the volatility process** 

Let us first pretend that we have access to discrete observations of the volatility process, on a time grid with mesh ∆on [0 _, T_ ]: _σ_ 0 _, σ_ ∆ _, . . . , σk_ ∆ _, . . . , k ∈{_ 0 _, ⌊T/_ ∆ _⌋}_ . Set _N_ = _⌊T/_ ∆ _⌋_ , then for _q ≥_ 0, we define 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0007-03.png)


In the spirit of [46], our main assumption is that for some _sq >_ 0 and _bq >_ 0, as ∆tends to zero, 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0007-05.png)


Under additional technical conditions, Equation (2.1) essentially says that the volatility process belongs to the Besov smoothness space _Bq,_<sup>_sq_</sup> _∞_<sup>anddoes</sup> _s_<sup>_′_</sup> not belong to _Bq,q∞_<sup>,for</sup><sup>_s′_</sup> _q_<sup>_>sq_,see[45].Hence</sup><sup>_sq_canreallybeviewed</sup> as the regularity of the volatility when measured in _lq_ norm. In particular, functions in _Bq,_<sup>_s_</sup> _∞_<sup>forevery</sup><sup>_q>_0enjoytheH¨olderpropertywithparameter</sup> _h_ for any _h < s_ . For example, if log( _σt_ ) is a fBM with Hurst parameter _H_ , then for any _q ≥_ 0, Equation (2.1) holds in probability with _sq_ = _H_ and it can be shown that the sample paths of the process indeed belong to _Bq,_<sup>_H_</sup> _∞_<sup>almostsurely.Assumingtheincrementsofthelog-volatilityprocess</sup> are stationary and that a law of large number can be applied, _m_ ( _q,_ ∆) can also be seen as the empirical counterpart of 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0007-07.png)


Of course, the volatility process is not directly observable, and an exact computation of _m_ ( _q,_ ∆) is not possible in practice. We must therefore proxy spot volatility values by appropriate estimated values. Since the minimal ∆ will be equal to one day in the sequel, we proxy the (true) spot volatility daily at a fixed given time of the day (11 am for example). Two daily spot volatility proxies will be considered: 

- For our ultra high frequency intraday data (DAX future contracts and Bund future contracts<sup>4</sup> , 1248 days from 13/05/2010 to 01/08/2014<sup>5</sup> ), 

> 3 `http://realized.oxford-man.ox.ac.uk/data/download` . The Oxford-Man Institute’s Realized Library contains a selection of daily non-parametric estimates of volatility of financial assets, including realized variance (rv) and realized kernel (rk) estimates. A selection of such estimators is described and their performances compared in, for example, [28] . 

> 4For every day, we only consider the future contract corresponding to the most liquid maturity. 

> 5Data kindly provided by QuantHouse EUROPE/ASIA, http://www.quanthouse.com.

<!-- page: 8 -->

we use the estimator of the integrated variance from 10 am to 11 am London time obtained from the model with uncertainty zones, see [42, 43]. After renormalization, the resulting estimates of integrated variance over very short time intervals can be considered as good proxies for the unobservable spot variance. In particular, the one hour long window on which they are computed is small compared to the extra day time scales that will be of interest here. 

- For the S&P and NASDAQ indices<sup>6</sup> , we proxy daily spot variances by daily realized variance estimates from the Oxford-Man Institute of Quantitative Finance Realized Library (3,540 trading days from January 3, 2000 to March 31, 2014). Since these estimates of integrated variance are for the whole trading day, we expect estimates of the smoothness of the volatility process to be biased upwards, integration being a regularizing operation. We compute the extent of this bias by simulation in Section 3.4. 

In the following, we retain the notation _m_ ( _q,_ ∆) with the understanding that we are only proxying the (true) spot volatility as explained above. We now proceed to estimate the smoothness parameter _sq_ for each _q_ by computing the _m_ ( _q,_ ∆) for different values of ∆and regressing log _m_ ( _q,_ ∆) against log ∆. Note that for a given ∆, several _m_ ( _q,_ ∆) can be computed depending on the starting point. Our final measure of _m_ ( _q,_ ∆) is the average of these values. 

### **2.2 DAX and Bund futures contracts** 

DAX and Bund futures are amongst the most liquid assets in the world and moreover, the model with uncertainty zones used to estimate volatility is known to apply well to them, see [19]. So we can be confident in the reliability of our volatility proxy. Nevertheless, as an extra check, we will confirm the quality of our volatility proxy by Monte Carlo simulation in Section 3.4. 

Plots of log _m_ ( _q,_ ∆) vs log ∆for different values of _q_ , are displayed for the DAX in Figure 2.1, and for the Bund in Figure 2.2. 

> 6And also the CAC40, Nikkei and FTSE indices in some specific parts of the paper.

<!-- page: 9 -->

![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0009-00.png)


<!-- Start of picture text -->
—0.5<br>-1.0<br>-1.5<br>=> -2.0 .<br>=<br>2 -2.5 ” .<br>—3.0 * * q=0.5<br>t * ~ + q=1=<br>—3.5 - ~*~ * q =1.5<br>* * q=2<br>+ q=3<br>—4.0<br>0.0 0.5 1.0 1.5 2.0 2.5 3.0 3.5 4.0<br>log(A)<br>—0.5<br>-1.0<br>-1.5 ,<br>a~ 72-0 **. * * ™<br>=-2.5 atelia wellle<br>= + + *<br>-3.0 el<br>z wr a Te q=0.5<br>3.5 * * * * * * q=1<br>* * g=1.5<br>—4.0 + + q=2<br>+ q=3<br>—4.5<br>0.0 0.5 1.0 1.5 2.0 2.5 3.0 3.5 4.0<br>log(A)<br><!-- End of picture text -->

<!-- page: 10 -->

![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0010-00.png)


<!-- Start of picture text -->
0.40<br>0.35<br>0.30<br>0.25<br>J 0.20<br>0.15<br>0.10<br>0.05<br>0.00<br>0.0 05 10 15 2.0 25 3.0<br>q<br><!-- End of picture text -->


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0010-01.png)


<!-- Start of picture text -->
0.25<br>0.20<br>015<br>SF<br>0.10<br>0.05<br>0.00<br>0.0 05 10 15 2.0 25 3.0<br>q<br><!-- End of picture text -->

<!-- page: 11 -->

![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0011-00.png)


<!-- Start of picture text -->
ae<br>-1.0 J<br>_ 15 ne<br>: «<br>* * q=0.5<br>—2.5 ~ + q =]<br>* * g=1.5<br>* * q=2<br>+ q=3<br>—3.0<br>0.0 0.5 1.0 1.5 2.0 2.5 3.0 3.5 4.0<br>log(A)<br>—0.5<br>-1.0<br>-1.5 - 2<br>on ae<br>= -2.0 wee<br>S *<br>Ss<br>s * <i*<br>—2.5<br>*, * * q=0.5<br>~ + q=1<br>—3.0 * * g=1.5<br>* * q=2<br>+ q=3<br>—3.5<br>0.0 0.5 1.0 1.5 2.0 2.5 3.0 3.5 4.0<br>log(A)<br><!-- End of picture text -->

<!-- page: 12 -->

![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0012-00.png)


<!-- Start of picture text -->
0.45<br>0.400.35<br>0.30<br>0.25<br>0.20<br>0.15<br>0.10<br>0.05<br>0.08, 9 0.5 10 15 2.0 25 3.0<br>q<br><!-- End of picture text -->


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0012-01.png)


<!-- Start of picture text -->
0.45<br>0.400.35 J4<br>0.30<br>0.25<br>0.20<br>0.15<br>0.10<br>y<br>0.05<br>0.000.0 0.5 1.0 15 2.0 25 3.0<br>q<br><!-- End of picture text -->

<!-- page: 13 -->

![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0013-00.png)


<!-- Start of picture text -->
g In<br>| \<br>z A/ \|<br>3 f \<br>3 _ _All(liliie -<br><!-- End of picture text -->


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0013-01.png)


<!-- Start of picture text -->
|<br>; / it<br>.| ‘lhi iy \<br>° i ;<br>|__AAllhsog) te _Al Drm a<br><!-- End of picture text -->


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0013-02.png)


<!-- Start of picture text -->
hi N<br>J<br>8 — _AllAliii _— -<br><!-- End of picture text -->


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0013-03.png)


<!-- Start of picture text -->
3 lf<br>| nt<br>8 ano _ eat(iIIie. Qo<br><!-- End of picture text -->

<!-- page: 14 -->

the crisis. 

## **3 A simple model compatible with the empirical smoothness of the volatility** 

In this section, we specify the Rough FSV model and demonstrate that it reproduces the empirical facts presented in Section 2. 

### **3.1 Specification of the RFSV model** 

In the previous section, we showed that, empirically, the increments of the log-volatility of various assets enjoy a scaling property with constant smoothness parameter and that their distribution is close to Gaussian. This naturally suggests the simple model: 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0014-05.png)


where _W_<sup>_H_</sup> is a fractional Brownian motion with Hurst parameter equal to the measured smoothness of the volatility and _ν_ is a positive constant. We may of course write (3.1) under the form 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0014-07.png)


where _σ_ is another positive constant. 

However this model is not stationary, stationarity being desirable both for mathematical tractability and also to ensure reasonableness of the model at very large times. This leads us to impose stationarity by modeling the log-volatility as a fractional Ornstein-Uhlenbeck process (fOU process for short) with a very long reversion time scale. 

A stationary fOU process ( _Xt_ ) is defined as the stationary solution of the stochastic differential equation 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0014-11.png)


where _m ∈_ R and _ν_ and _α_ are positive parameters, see [12]. As for usual Ornstein-Uhlenbeck processes, there is an explicit form for the solution which is given by 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0014-13.png)


Here the stochastic integral with respect to fBM is simply a pathwise RiemannStieltjes integral, see again [12].

<!-- page: 15 -->

We thus arrive at the final specification of our Rough Fractional Stochastic Volatility (RFSV) model for the volatility on the time interval of interest [0 _, T_ ]: 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0015-01.png)


where ( _Xt_ ) satisfies Equation (3.3) for some _ν >_ 0 _, α >_ 0, _m ∈_ R and _H <_ 1 _/_ 2 the measured smoothness of the volatility. Such a model is indeed stationary. However, if _α ≪_ 1 _/T_ , the log-volatility behaves locally (at time scales smaller than _T_ ) as a fBM. This observation is formalized in Proposition 3.1 below. 

**Proposition 3.1.** _Let W_<sup>_H_</sup> _be a fBM and X_<sup>_α_</sup> _defined by_ (3.3) _for a given α >_ 0 _. As α tends to zero,_ 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0015-04.png)


The proof is given in Appendix A.1. 

Proposition 3.1 implies that in the RFSV model, if _α ≪_ 1 _/T_ , and we confine ourselves to the interval [0 _, T_ ] of interest, we can proceed as if the the log-volatility process were a fBM. Indeed, simply setting _α_ = 0 in (3.3) gives (at least formally) _Xt − Xs_ = _ν_ ( _Wt_<sup>_H_</sup> _− Ws_<sup>_H_)andweimmediatelyrecover</sup> our simple non-stationary fBM model (3.1). 

The following corollary implies that the (exact) scaling property of the fBM is approximately reproduced by the fOU process when _α_ is small. 

**Corollary 3.1.** _Let q >_ 0 _, t >_ 0 _,_ ∆ _>_ 0 _. As α tends to zero, we have_ 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0015-09.png)


The proof is given in Appendix A.2. 

#### **RFSV versus FSV** 

We recognize our RFSV model (3.4) as a particular case of the classical FSV model of Comte and Renault [16]. The key difference is that here we take _H <_ 1 _/_ 2 and _α ≪_ 1 _/T_ , whereas to accommodate the assumption of long memory, Comte and Renault have to choose _H >_ 1 _/_ 2. The analysis of Fukasawa referred to earlier in Section 1.3 implies in particular that if _H >_ 1 _/_ 2, the volatility skew function _ψ_ ( _τ_ ) is _increasing_ in time to expiration _τ_ (at least for small _τ_ ), which is obviously completely inconsistent with the approximately 1 _/_<sup>_√_</sup> _<u>τ</u>_ skew term structure that is observed. To generate a decreasing term structure of volatility skew for longer expirations, Comte and Renault are then forced to choose _α ≫_ 1 _/T_ . Consequently, for very short expirations ( _τ ≪_ 1 _/α_ ), models of the Comte and Renault type with

<!-- page: 16 -->

_H >_ 1 _/_ 2 still generate a term structure of volatility skew that is inconsistent with the observed one, as explained for example in Section 4 of [15]. 

In contrast, the choice _H <_ 1 _/_ 2 enables us to reproduce both the observed smoothness of the volatility process and generate a term structure of volatility skew in agreement with the observed one. The choice _H <_ 1 _/_ 2 is also consistent with what is improperly called mean reversion by practitioners, which is the fact that if volatility is unusually high, it tends to decline and if it is unusually low, it tends to increase. Finally, taking _α_ very small implies that the dynamics of our process is close to that of a fBM, see Proposition 3.1. This last point is particularly important. Indeed, recall that at the time scales we are interested in, the important feature we have in mind is really this fBM like-behavior of the log-volatility. 

We could no doubt have considered other stationary models satisfying Proposition 3.1 and Corollary 3.1, where log-volatility behaves as a fBM at reasonable time scales; the choice of the fOU process is probably the simplest way to accommodate this local behavior together with the stationarity property. 

### **3.2 RFSV model autocovariance functions** 

From Proposition 3.1 and Corollary 3.1, we easily deduce the following corollary, where _o_ (1) tends to zero as _α_ tends to zero. 

**Corollary 3.2.** _Let q >_ 0 _, t >_ 0 _,_ ∆ _>_ 0 _. As α tends to zero,_ 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0016-06.png)


Consequently, in the RFSV model, for fixed _t_ , the covariance between _Xt_ and _Xt_ +∆ is linear with respect to ∆<sup>2</sup><sup>_H_</sup> . This result is very well satisfied empirically. For example, in Figure 3.1, we see that for the S&P, the empirical autocovariance function of the log-volatility is indeed linear with respect to ∆<sup>2</sup><sup>_H_</sup> . Note in passing that at the time scales we consider, the term Var[ _Xt_<sup>_α_]</sup> is higher than 2<sup><u>1</u></sup><sup>_ν_2 ∆2</sup><sup>_H_intheexpressionforCov[</sup><sup>_X_</sup> _t_<sup>_α, X_</sup> _t_<sup>_α_</sup> +∆<sup>].</sup>

<!-- page: 17 -->

![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0017-00.png)


<!-- Start of picture text -->
0.24<br>0.22<br>0.20<br>a<br>€ 018<br>0.16<br>0.14<br>1.0 15 2.0 2.5 3.0<br>Ae<br><!-- End of picture text -->

<!-- page: 18 -->

![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0018-00.png)


<!-- Start of picture text -->
0.35<br>0.30<br>*<br>0.2 5 Sad*.tHe<br>i—S *,he<br>& 0.20 i,<br>yy <9<br>roy<br>2 ~<br>0.15 %<br>0.10<br>0.05<br>1.0 15 2.0 2.5 3.0 3.5 4.0 4.5<br>Alt<br><!-- End of picture text -->

<!-- page: 19 -->

![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0019-00.png)


<!-- Start of picture text -->
-9.5<br>—10.0<br>= 10.5. we ** * a><br>=<br>& -11.0<br>><br>fo}<br>Q<br>oa<br>2<br>-11.5<br>-12.0 ¢<br>-12.50) 1 2 3 4 5 6<br>log(A)<br><!-- End of picture text -->

<!-- page: 20 -->

![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0020-00.png)


<!-- Start of picture text -->
3s<br>S<br>N<br>a ¢?<br>a<br>E<br>p> st<br>2g<br>2<br>9<br>2<br>9<br>0 1 2 3 4<br>log(A)<br><!-- End of picture text -->

<!-- page: 21 -->

![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0021-00.png)


<!-- Start of picture text -->
-1.0 | =<br>_ * * UZq=0.5<br>: * * UZ q=1<br>= * * UZQG=15<br>* * UZ q=2<br>* * UZq=3<br>- e © RV g=0.5<br>ee RVg=1<br>~ ee RVG=1.5<br>© @ RV q=2<br>e e RVqg=3<br>485 0.5 1.0 15 2.0 2.5 3.0 3.5 4.0<br>log(A)<br><!-- End of picture text -->

<!-- page: 22 -->

![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0022-00.png)


<!-- Start of picture text -->
0.06 Data<br>0.05<br>0.04<br>0.03<br>0.02<br>0.01 { |<br>0.005 500 1000 1500 2000 2500 3000 3500<br>0.06 Model<br>0.05<br>0.04<br>0.03<br>0.02<br>0.01 ! |<br>0.005 500 1000 1500 2000 2500 3000 3500<br><!-- End of picture text -->

<!-- page: 23 -->

At the visual level, we observe that this fractal-type behavior is also reproduced in our model, as we now explain. Denote by _L_<sup>_x,H_</sup> the law of the geometric fractional Brownian motion with Hurst exponent _H_ and volatility _x_ on [0 _,_ 1], that is ( _e_<sup>_xW H_</sup> _t_ ) _t∈_ [0 _,_ 1]. Then, when _α_ is very small, the rescaled volatility process on [0 _,_ ∆]: ( _σt_ ∆ _/σ_ 0) _t∈_ [0 _,_ 1], has approximately the law _L_<sup>_ν_∆</sup><sup>_H,H_</sup> . Now remark that for _H_ small, the function _u_<sup>_H_</sup> increases very slowly. Thus, over a large range of observation scales ∆, the rescaled volatility processes on [0 _,_ ∆] have approximately the same law. For example, between an observation scale of one day and five years (1250 open days), the coefficient _x_ characterizing the law of the volatility process is “only” multiplied by 1250<sup>0</sup><sup>_._14</sup> = 2 _._ 7. It follows that in the RFSV model, the volatility process over one day resembles the volatility process over a decade. 

## **4 Spurious long memory of volatility?** 

We revisit in this section the issue of long memory of volatility through the lens of our model. As mentioned earlier in the introduction, the long memory of volatility is widely accepted as a stylized fact. Specifically, this means that the autocovariance function Cov[log( _σt_ ) _,_ log( _σt_ +∆)] (or sometimes Cov[ _σt, σt_ +∆]) goes slowly to zero as ∆ _→∞_ and often even more precisely, that it behaves as ∆<sup>_−γ_</sup> , with _γ <_ 1 as ∆ _→∞_ . 

In previous sections, we showed that both in the data and in our model, 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0023-04.png)


and 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0023-06.png)


for some constants _A_ , _B_ , _C_ and _D_ . Thus, neither in the model nor in the data does the autocovariance function decay as a power law. And neither the data nor the model exhibits long memory<sup>10</sup> , see again Figure 3.3. 

We now revisit some standard statistical procedures aimed at identifying long memory that have been used in the financial econometrics literature. In the sequel, we apply these both to the data and to sample paths of the RFSV model. Such procedures are of course designed to identify long memory under rather strict modeling assumptions; spurious results may obviously then be obtained if the model underlying the estimation procedure 

> 10In fact the notion of empirical long memory does not make much sense outside the power law case. Indeed the empirical values of covariances at very large time scales are never measurable and thus one cannot conclude if the series of covariances converges in general. All that we say here is that the autocovariance of the (log-)volatility does not behave as a power law.

<!-- page: 24 -->

![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0024-00.png)


<!-- Start of picture text -->
4 Data<br>3<br>2<br>~ 1<br>40<br>25 -1-2<br>-3<br>-4<br>-5<br>0 1 2 3 4 5<br>log(A)<br>4 Model<br>3<br>2<br>~4 0 1<br>2S -1-2<br>-3<br>-4<br>-5<br>) 1 2 3 4 5<br>log(A)<br><!-- End of picture text -->

<!-- page: 25 -->

![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0025-00.png)


<!-- Start of picture text -->
Data<br>0.8<br>0.6<br>0.4<br>sy<br>0.2<br>o.of" "= Pee NAIA AINA ee AINA TETER LENE SSSR EIS<br>0 20 40 60 80 100<br>A<br>Model<br>0.8<br>0.6<br>404<br>sy<br>0.2<br>O.0f/ 7 VN AAS EAE LEAT SEE ENR US ES SAE IN SSA SA PAINE<br>) 20 40 60 80 100<br>A<br><!-- End of picture text -->

<!-- page: 26 -->

## **5 Forecasting using the RFSV model** 

In this section, we present an application of our model: forecasting the log-volatility and the variance. 

### **5.1 Forecasting log-volatility** 

The key formula on which our prediction method is based is the following one: 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0026-04.png)


where _W_<sup>_H_</sup> is a fBM with _H <_ 1 _/_ 2 and _Ft_ the filtration it generates, see Theorem 4.2 of [41]. By construction, over any reasonable time scale of interest, as formalized in Corollary 3.1, we may approximate the fOU volatility process in the RFSV model as log _σt_<sup>2</sup><sup>_≈_2</sup><sup>_ν W H_</sup> _t_ + _C_ for some constants _ν_ and _C_ . Our prediction formula for log-variance then follows:<sup>11</sup> 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0026-06.png)


This formula, or rather its approximation through a Riemann sum (we assume in this section that the volatilities are perfectly observed, although they are in fact estimated), is used to forecast the log-volatility 1, 5 and 20 days ahead (∆= 1 _,_ 5 _,_ 20). 

We now compare the predictive power of formula (5.1) with that of AR and HAR forecasts, in the spirit of [18]<sup>12</sup> . Recall that for a given integer _p >_ 0, the AR(p) and HAR predictors take the following form (where the index _i_ runs over the series of daily volatility estimates): 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0026-09.png)


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0026-10.png)


_•_ HAR : 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0026-12.png)


> 11The constants 2 _ν_ and _C_ cancel when deriving the expression. 

> 12 Note that we do not consider GARCH models here since we have access to high frequency volatility estimates and not only to daily returns. Indeed, it is shown in [4] that forecasts based on the time series of realized variance outperform GARCH forecasts based on daily returns.

<!-- page: 27 -->

We estimate AR coefficients using the R `stats` library<sup>13</sup> on a rolling time window of 500 days. In the HAR case, we use standard linear regression to estimate the coefficients as explained in [18]. In the sequel, we consider _p_ = 5 and _p_ = 10 in the AR formula. Indeed, these parameters essentially give the best results for the horizons at which we wish to forecast the volatility (1, 5 and 20 days). For each day, we forecast volatility for five different indices<sup>14</sup> . 

We then assess the quality of the various forecasts by computing the ratio _P_ between the mean squared error of our predictor and the (approximate) variance of the log-variance: 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0027-02.png)


where E[log( _σt_<sup>2</sup> +∆<sup>)]denotestheempiricalmeanofthelog-varianceoverthe</sup> whole time period. 

||AR(5)|AR(10)|HAR(3)|RFSV|
|---|---|---|---|---|
|SPX2.rv ∆= 1|0.317|0.318|0.314|**0.313**|
|SPX2.rv ∆= 5|0.459|0.449|0.437|**0.426**|
|SPX2.rv ∆= 20|0.764|0.694|0.656|**0.606**|
|FTSE2.rv ∆= 1|0.230|0.229|0.225|**0.223**|
|FTSE2.rv ∆= 5|0.357|0.344|0.337|**0.320**|
|FTSE2.rv ∆= 20|0.651|0.571|0.541|**0.472**|
|N2252.rv ∆= 1|0.357|0.358|0.351|**0.345**|
|N2252.rv ∆= 5|0.553|0.533|0.513|**0.504**|
|N2252.rv ∆= 20|0.875|0.795|0.746|**0.714**|
|GDAXI2.rv ∆= 1|0.237|0.238|0.234|**0.231**|
|GDAXI2.rv ∆= 5|0.372|0.362|0.350|**0.339**|
|GDAXI2.rv ∆= 20|0.661|0.590|0.550|**0.498**|
|FCHI2.rv ∆= 1|0.244|0.244|0.241|**0.238**|
|FCHI2.rv ∆= 5|0.378|0.373|0.366|**0.350**|
|FCHI2.rv ∆= 20|0.669|0.613|0.598|**0.522**|


Table 5.1: Ratio _P_ for the AR, HAR and RFSV predictors. 

We note from Table 5.1 that the RFSV forecast consistently outperforms the AR and HAR forecasts, especially at longer horizons. Moreover, our forecasting method is more parsimonious since it only requires the parameter 

> 13More precisely, we use the default Yule-Walker method. 

> 14In addition to S&P and NASDAQ, we also investigate CAC40, FTSE and Nikkei, over the same time period as S&P and NASDAQ. For simplicity, the parameter _H_ used in our predictor is computed only once for each asset, using the whole time period. This yields similar results to using a moving time window adapted in time.

<!-- page: 28 -->

_H_ to forecast the log-variance. Compare this with the AR and HAR methods, for which coefficients depend on the forecast time horizon and must be recomputed if this horizon changes. 

Remark that our predictor can be linked to that of [21], where the issue of the prediction of the log-volatility in the multifractal random walk model of [5] is tackled. In this model, 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0028-02.png)


which is the limit of our predictor when _H_ tends to zero. 

Note also that our prediction formula may be rewritten as 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0028-05.png)


For a given small _ε >_ 0, let _r_ be the smallest real number such that 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0028-07.png)


Then we have, with an error of order _ε_ , 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0028-09.png)


Consequently, the volatility process needs to be considered (roughly) down to time _t −_ ∆ _r_ if one wants to forecast up to time ∆in the future. The relevant regression window is thus linear in the forecasting horizon. For example, for _r_ = 1, _ε_ = 0 _._ 35 which is not so unreasonable. In this case, as is well-known to practitioners, to predict volatility one week ahead, one should essentially look at the volatility over the last week. If trying to predict the volatility one month ahead, one should look at the volatility over the last month. 

### **5.2 Variance prediction** 

Recall that log _σt_<sup>2</sup><sup>_≈_2</sup><sup>_ν W H_</sup> _t_ + _C_ for some constant _C_ . In [41], it is shown that _W_<sup>_H_conditionallyGaussianwithconditionalvariance</sup> _t_ +∆<sup>is</sup> 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0028-13.png)


with 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0028-15.png)

<!-- page: 29 -->

![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0029-00.png)


� where log( _σt_<sup>2</sup> +∆<sup>)istheestimatorfromSection5.1and</sup><sup>_ν_2isestimatedas</sup> the exponential of the intercept in the linear regression of log( _m_ (2 _,_ ∆)) on log(∆). 

As in the previous paragraph, we compare in Table 5.2 the performance of the RFSV forecast with those of AR and HAR forecasts (constructed on variance rather than log-variance this time). 

||AR(5)|AR(10)|HAR(3)|RFSV|
|---|---|---|---|---|
|SPX2.rv ∆= 1|0.520|0.566|0.489|**0.475**|
|SPX2.rv ∆= 5|0.750|0.745|0.723|**0.672**|
|SPX2.rv ∆= 20|1.070|1.010|1.036|**0.903**|
|FTSE2.rv ∆= 1|0.612|0.621|0.582|**0.567**|
|FTSE2.rv ∆= 5|0.797|0.770|0.756|**0.707**|
|FTSE2.rv ∆= 20|1.046|0.984|0.935|**0.874**|
|N2252.rv ∆= 1|0.554|0.579|**0.504**|0.505|
|N2252.rv ∆= 5|0.857|0.807|0.761|**0.729**|
|N2252.rv ∆= 20|1.097|1.046|1.011|**0.964**|
|GDAXI2.rv ∆= 1|0.439|0.448|0.399|**0.386**|
|GDAXI2.rv ∆= 5|0.675|0.650|0.616|**0.566**|
|GDAXI2.rv ∆= 20|0.931|0.850|0.816|**0.746**|
|FCHI2.rv ∆= 1|0.533|0.542|0.470|**0.465**|
|FCHI2.rv ∆= 5|0.705|0.707|0.691|**0.631**|
|FCHI2.rv ∆= 20|0.982|0.952|0.912|**0.828**|


Table 5.2: Ratio _P_ for the AR, HAR and RFSV predictors. 

We find again that the RFSV forecast typically outperforms HAR and AR, although it is worth noting that the HAR forecast is already visibly superior to the AR forecast. 

## **6 The microstructural foundations of the irregularity of the volatility** 

We gather in this section some ideas which may help to understand why the observed volatility appears so irregular. The starting point is the analysis of the order flow through Hawkes processes. These processes are extensions of Poisson processes where the intensity at a given time depends on the

<!-- page: 30 -->

location of the past jumps. More precisely, let us consider a time period starting at 0 and denote by _Nt_ the number of transactions between 0 and _t_ . Assuming the point process _Nt_ follows a Hawkes process means its intensity at time _t_ , _λt_ , takes the form: 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0030-01.png)


where the _Ji_ are the past jump times, _µ_ is a positive constant and _φ_ is a non negative deterministic function called kernel. 

When trying to calibrate such models on high frequency data, two main phenomena almost systematically occur: 

- The _L_<sup>1</sup> norm of _φ_ is close to one, see [23, 24, 30, 35]. 

- The function _φ_ has a power law tail, see [6, 30]. 

The first of these two facts means the degree of endogeneity of the market is very high, that is one given order endogenously generates many other orders, see [23, 24, 30]. This recent feature of financial markets is obviously related to electronic high frequency trading, where market participants automatically react to other participants orders through their algorithms. The second observation tells us that generally, a given order influences other orders over a long time period. This is likely due to the splitting of large orders. Indeed, many orders are actually part of a metaorder whose full execution can take a large amount of time. 

We believe these two phenomena together lead to a superposition effect inducing this irregular volatility. Indeed, it is explained in [33, 34] that the macroscopic scaling limit of Hawkes processes with power law tail and kernel with _L_<sup>1</sup> norm close to one can be seen as an integrated fractional process, with Hurst parameter _H_ smaller than 1 _/_ 2. This signifies that at large sampling scales, the dynamics of the cumulated order flow is well approximated by an integrated fractional process, with _H <_ 1 _/_ 2. Then, it is clearly established that there is a linear relation between cumulated order flow and integrated variance. Thus we retrieve here that because of this superposition effect, the volatility should behave as a fractional process with _H <_ 1 _/_ 2. 

## **7 Conclusion** 

Using daily realized variance estimates as proxies for daily spot (squared) volatilities, we uncovered two startlingly simple regularities in the resulting

<!-- page: 31 -->

time series. First we found that the distributions of increments of logvolatility are approximately Gaussian, consistent with many prior studies. Secondly, we established the monofractal scaling relationship 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0031-01.png)


where _H_ can be seen as a measure of smoothness characteristic of the underlying volatility process; typically, 0 _._ 06 _< H <_ 0 _._ 2. The simple scaling relationship (7.1) naturally suggests that log-volatility may be modeled using fractional Brownian motion. 

The resulting Rough Fractional Stochastic Volatility (RFSV) model turns out to be formally almost identical to the FSV model of Comte and Renault [16], with one major difference: In the FSV model, _H >_ 1 _/_ 2 to ensure long memory whereas in the RFSV model _H <_ 1 _/_ 2, typically, _H ≈_ 0 _._ 1. Moreover, in the FSV model, the mean reversion coefficient _α_ has to be large compared to 1 _/T_ to ensure a decaying volatility skew; in the RFSV model, the volatility skew decays naturally just like the observed volatility skew, _α ≪_ 1 _/T_ and indeed for time scales of practical interest, we may proceed as if _α_ were exactly zero. 

We further showed that applying standard statistical estimators to volatility time series simulated with the RFSV model would lead us to erroneously deduce the presence of long memory, with parameters similar to those found in prior studies. Despite that volatility in the RFSV model (or in the data) is not long memory, we can therefore explain why long memory of volatility is widely accepted as a stylized fact. 

As an application of the RFSV model, we showed how to forecast volatility at various times cales, at least as well as Fulvio Corsi’s impressive HAR estimator, but with only one parameter – _H_ ! 

Finally, we explained how the RFSV model could emerge as the scaling limit of a Hawkes process description of order flow. 

In future work, we will explore the implications of the RFSV model (written under the physical measure P), for option pricing (under the pricing measure Q). In particular, following Mandelbrot and Van Ness, the fBM that appears in the definition (3.4) of the RFSV model may be represented as a fractional integral of a standard Brownian motion as follows [36]: 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0031-08.png)


with _γ_ = 2<sup><u>1</u></sup><sup>_−H_.Theobservedanticorrelationbetweenpricemovesand</sup> volatility moves may then be modeled naturally by anticorrelating the Brow-

<!-- page: 32 -->

nian motion _W_ that drives the volatility process with the Brownian motion driving the price process. As already shown by Fukasawa [25], such a model with a small _H_ reproduces the observed decay of at-the-money volatility skew with respect to time to expiry, asymptotically for short times. We will show that an appropriate extension of Fukasawa’s model, consistent with the RFSV model, fits the entire implied volatility surface remarkably well, not just for short expirations. Moreover, despite that it would seem from (7.2) that knowledge of the entire path _{Ws_ : _s < t}_ of the Brownian motion would be required, it turns out that the statistics of this path necessary for option pricing are traded and thus easily observed. 

## **A Proofs** 

### **A.1 Proof of Proposition 3.1** 

Starting from Equation (3.3) and applying integration by parts, we get 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0032-04.png)


Therefore, 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0032-06.png)


Consequently, 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0032-08.png)


where _W_<sup>ˆ</sup> _t_<sup>_H_</sup> = sup _s∈_ [0 _,t_ ] _|Ws_<sup>_H|_.Usingthemaximuminequalityof[40],weget</sup> 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0032-10.png)


with _c_ some constant. The term on the right hand side is easily seen to go to zero as _α_ tends to zero. 

### **A.2 Proof of Corollary 3.1** 

We first recall Equation (2.2) in [12] which writes: 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0032-14.png)

<!-- page: 33 -->

with _K_ = _ν_<sup>2</sup> Γ(2 _H_ + 1)sin( _πH_ ) _/_ (2 _π_ )<sup>15</sup> . Now remark that 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0033-01.png)


Therefore, 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0033-03.png)


This implies that for fixed ∆, E[ _|Xt_<sup>_α_</sup> +∆<sup>_−X_</sup> _t_<sup>_α|_2]isuniformlyboundedby</sup> 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0033-05.png)


Moreover, _Xt_<sup>_α_</sup> +∆<sup>_−X_</sup> _t_<sup>_α_isaGaussianrandomvariableandthusforevery</sup> _q_ , its ( _q_ + 1)<sup>_th_</sup> moment is uniformly bounded (in _α_ ) so that the family _|Xt_<sup>_α_</sup> +∆<sup>_−X_</sup> _t_<sup>_α|q_isuniformlyintegrable.Therefore,sincebyProposition3.1,</sup> 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0033-07.png)


we get the convergence of the sequence of expectations. 

> 15This covariance is real because it is the Fourier transform of an even function.

<!-- page: 34 -->

## **B Estimations of** _H_ 

### **B.1 On indices** 

|Index|_ζ_0_._5_/_0_._5|_ζ_1|_ζ_1_._5_/_1_._5|_ζ_2_/_2|_ζ_3_/_3|
|---|---|---|---|---|---|
|SPX2.rv|0.128|0.126|0.125|0.124|0.124|
|FTSE2.rv|0.132|0.132|0.132|0.131|0.127|
|N2252.rv|0.131|0.131|0.132|0.132|0.133|
|GDAXI2.rv|0.141|0.139|0.138|0.136|0.132|
|RUT2.rv|0.117|0.115|0.113|0.111|0.108|
|AORD2.rv|0.072|0.073|0.074|0.075|0.077|
|DJI2.rv|0.117|0.116|0.115|0.114|0.113|
|IXIC2.rv|0.131|0.133|0.134|0.135|0.137|
|FCHI2.rv|0.143|0.143|0.142|0.141|0.138|
|HSI2.rv|0.079|0.079|0.079|0.080|0.082|
|KS11.rv|0.133|0.133|0.134|0.134|0.132|
|AEX.rv|0.145|0.147|0.149|0.149|0.149|
|SSMI.rv|0.149|0.153|0.156|0.158|0.158|
|IBEX2.rv|0.138|0.138|0.137|0.136|0.133|
|NSEI.rv|0.119|0.117|0.114|0.111|0.102|
|MXX.rv|0.077|0.077|0.076|0.075|0.071|
|BVSP.rv|0.118|0.118|0.119|0.120|0.120|
|GSPTSE.rv|0.106|0.104|0.103|0.102|0.101|
|STOXX50E.rv|0.139|0.135|0.130|0.123|0.101|
|FTSTI.rv|0.111|0.112|0.113|0.113|0.112|
|FTSEMIB.rv|0.130|0.132|0.133|0.134|0.134|


Table B.1: Estimates of _ζq_ for all indices in the Oxford-Man dataset.

<!-- page: 35 -->

### **B.2 On time intervals**<sup>16</sup> 

|Index|H (frst half)|H (second half)|
|---|---|---|
|SPX2.rk|0.115|0.158|
|FTSE2.rk|0.140|0.156|
|N2252.rk|0.083|0.134|
|GDAXI2.rk|0.154|0.168|
|RUT2.rk|0.098|0.149|
|AORD2.rk|0.059|0.114|
|DJI2.rk|0.123|0.151|
|IXIC2.rk|0.094|0.156|
|FCHI2.rk|0.140|0.146|
|HSI2.rk|0.072|0.129|
|KS11.rk|0.109|0.147|
|AEX.rk|0.168|0.151|
|SSMI.rk|0.206|0.183|
|IBEX2.rk|0.122|0.149|
|NSEI.rk|0.112|0.124|
|MXX.rk|0.068|0.118|
|BVSP.rk|0.074|0.134|
|GSPTSE.rk|0.075|0.147|
|STOXX50E.rk|0.138|0.132|
|FTSTI.rk|0.080|0.171|
|FTSEMIB.rk|0.133|0.140|


Table B.2: Estimates of _H_ over two different time intervals for all indices in the Oxford-Man dataset 

## **C The effect of smoothing** 

Although we are really interested in the model 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0035-05.png)


consider the more tractable (fractional Stein and Stein or fSS) model: 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0035-07.png)


where _vt_ = _σ_<sup>2</sup> . We cannot observe _vt_ but suppose we can proxy it by the average 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0035-09.png)


> 16Note that we used realized kernel rather than realized variance estimates to generate Table B.2. Results obtained using different variance estimators are almost indistinguishable.

<!-- page: 36 -->

| | ~~a~~ ) ff | [fi 


![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0036-01.png)


<!-- Start of picture text -->
|<br><!-- End of picture text -->

| 

| 

fd] = ~~f~~ 

/ | ~~—_—_{~~ 

/ | ~~— ——-{~~

<!-- page: 37 -->

![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0037-00.png)


<!-- Start of picture text -->
a<br>a<br>oO<br>o<br>oO<br>MH<br>o<br>= ©<br>oO<br>Te)<br>oO<br>=<br>oO<br>o<br>oO<br>0.0 0.2 0.4 0.6 0.8 1.0<br>6<br><!-- End of picture text -->

<!-- page: 38 -->

![](assets/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf-0038-00.png)


<!-- Start of picture text -->
a<br>vs<br>v7<br><I1 o aePoaaewat”<br>Eas o= a—a- ** tad<br>“7 a ae<br>= os Pail<br>fy] < at<br>~ ce<br>t - ae<br>2<br>I<br>.<br>0 1 2 3 4<br>logA<br><!-- End of picture text -->

<!-- page: 39 -->

- [6] E. Bacry and J.-F. Muzy. Hawkes model for price and trades highfrequency dynamics. _Quantitative Finance_ , 14(7):1147–1166, 2014. 

- [7] S. R. Bentes and M. M. Cruz. Is stock market volatility persistent? A fractionally integrated approach. 2011. 

- [8] J. Beran. _Statistics for long-memory processes_ , volume 61. CRC Press, 1994. 

- [9] J.-P. Bouchaud and M. Potters. _Theory of financial risk and derivative pricing: From statistical physics to risk management_ . Cambridge University Press, 2003. 

- [10] P. Carr and L. Wu. What type of process underlies options? A simple robust test. _Journal of Finance_ , 58(6):2581–2610, 2003. 

- [11] Z. Chen, R. T. Daigler, and A. M. Parhizgari. Persistence of volatility in futures markets. _Journal of Futures Markets_ , 26(6):571–594, 2006. 

- [12] P. Cheridito, H. Kawaguchi, and M. Maejima. Fractional OrnsteinUhlenbeck processes. _Electron. J. Probab_ , 8(3):14, 2003. 

- [13] A. Chronopoulou. Parameter estimation and calibration for longmemory stochastic volatility models. In F. G. Viens, M. C. Mariani, and I. Florescu, editors, _Handbook of Modeling High-Frequency Data in Finance_ , pages 219–231. John Wiley & Sons, 2011. 

- [14] A. Chronopoulou and F. G. Viens. Estimation and pricing under longmemory stochastic volatility. _Annals of Finance_ , 8(2-3):379–403, 2012. 

- [15] F. Comte, L. Coutin, and E. Renault. Affine fractional stochastic volatility models. _Annals of Finance_ , 8(2-3):337–378, 2012. 

- [16] F. Comte and E. Renault. Long memory in continuous-time stochastic volatility models. _Mathematical Finance_ , 8(4):291–323, 1998. 

- [17] R. Cont. Volatility clustering in financial markets: Empirical facts and agent-based models. In G. Teyssi`ere and A. P. Kirman, editors, _Long Memory in Economics_ , pages 289–309. Springer Berlin Heidelberg, 2007. 

- [18] F. Corsi. A simple approximate long-memory model of realized volatility. _Journal of Financial Econometrics_ , 7(2):174–196, 2009. 

- [19] K. Dayri and M. Rosenbaum. Large tick assets: Implicit spread and optimal tick size. _Working paper_ , 2013. 

- [20] Z. Ding, C. W. Granger, and R. F. Engle. A long memory property of stock market returns and a new model. _Journal of Empirical Finance_ , 1(1):83–106, 1993.

<!-- page: 40 -->

- [21] J. Duchon, R. Robert, and V. Vargas. Forecasting volatility with the multifractal random walk model. _Mathematical Finance_ , 22(1):83–108, 2012. 

- [22] B. Dupire. Pricing with a smile. _Risk Magazine_ , 7(1):18–20, 1994. 

- [23] V. Filimonov and D. Sornette. Quantifying reflexivity in financial markets: Toward a prediction of flash crashes. _Physical Review E_ , 85(5):056108, 2012. 

- [24] V. Filimonov and D. Sornette. Apparent criticality and calibration issues in the Hawkes self-excited point process model: Application to high-frequency financial data. _arXiv preprint arXiv:1308.6756_ , 2013. 

- [25] M. Fukasawa. Asymptotic analysis for stochastic volatility: Martingale expansion. _Finance and Stochastics_ , 15(4):635–654, 2011. 

- [26] J. Gatheral. _The volatility surface: A practitioner’s guide_ , volume 357. John Wiley & Sons, 2006. 

- [27] J. Gatheral and A. Jacquier. Arbitrage-free SVI volatility surfaces. _Quantitative Finance_ , 14(1):59–71, 2014. 

- [28] J. Gatheral and R. C. Oomen. Zero-intelligence realized variance estimation. _Finance and Stochastics_ , 14(2):249–283, 2010. 

- [29] P. S. Hagan, D. Kumar, A. S. Lesniewski, and D. E. Woodward. Managing smile risk. _Wilmott Magazine_ , pages 84–108, 2002. 

- [30] S. J. Hardiman, N. Bercot, and J.-P. Bouchaud. Critical reflexivity in financial markets: A Hawkes process analysis. _arXiv preprint arXiv:1302.1405_ , 2013. 

- [31] S. L. Heston. A closed-form solution for options with stochastic volatility with applications to bond and currency options. _Review of Financial Studies_ , 6(2):327–343, 1993. 

- [32] J. Hull and A. White. One-factor interest-rate models and the valuation of interest-rate derivative securities. _Journal of Financial and Quantitative Analysis_ , 28(02):235–254, 1993. 

- [33] T. Jaisson and M. Rosenbaum. Limit theorems for nearly unstable Hawkes processes. _The Annals of Applied Probability, to appear_ , 2013. 

- [34] T. Jaisson and M. Rosenbaum. Fractional diffusions as scaling limits of nearly unstable heavy-tailed Hawkes processes. _Working paper_ , 2014. 

- [35] M. Lallouache and D. Challet. Statistically significant fits of Hawkes processes to financial data. _Available at SSRN 2450101_ , 2014.

<!-- page: 41 -->

- [36] B. B. Mandelbrot and J. W. Van Ness. Fractional Brownian motions, fractional noises and applications. _SIAM review_ , 10(4):422–437, 1968. 

- [37] R. N. Mantegna and H. E. Stanley. _Introduction to econophysics: Correlations and complexity in finance_ . Cambridge University Press, 2000. 

- [38] T. Mikosch and C. St˘aric˘a. Is it really long memory we see in financial returns. In P. Embrechts, editor, _Extremes and integrated risk management_ , pages 149–168. Risk Books, 2000. 

- [39] M. Musiela and M. Rutkowski. _Martingale methods in financial modelling_ , volume 36. Springer, 2006. 

- [40] A. Novikov and E. Valkeila. On some maximal inequalities for fractional Brownian motions. _Statistics & Probability Letters_ , 44(1):47–54, 1999. 

- [41] C. J. Nuzman and V. H. Poor. Linear estimation of self-similar processes via Lamperti’s transformation. _Journal of Applied Probability_ , 37(2):429–452, 2000. 

- [42] C. Y. Robert and M. Rosenbaum. A new approach for the dynamics of ultra-high-frequency data: The model with uncertainty zones. _Journal of Financial Econometrics_ , 9(2):344–366, 2011. 

- [43] C. Y. Robert and M. Rosenbaum. Volatility and covariation estimation when microstructure noise and trading times are endogenous. _Mathematical Finance_ , 22(1):133–164, 2012. 

- [44] M. Rosenbaum. Estimation of the volatility persistence in a discretely observed diffusion model. _Stochastic Processes and their Applications_ , 118(8):1434–1462, 2008. 

- [45] M. Rosenbaum. First order p-variations and Besov spaces. _Statistics & Probability Letters_ , 79(1):55–62, 2009. 

- [46] M. Rosenbaum. A new microstructure noise index. _Quantitative Finance_ , 11(6):883–899, 2011.
