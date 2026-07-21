---
paper_id: "2002-hagan-et-al-managing-smile-risk"
title: "Managing Smile Risk"
authors: "Patrick S. Hagan; Deep Kumar; Andrew S. Lesniewski; Diana E. Woodward"
year: "2002"
source_url: "https://www.wilmott.com/managing-smile-risk/"
source_pdf: "references/papers/2002-hagan-et-al-managing-smile-risk.pdf"
source_sha256: "c267782462f7e762455c481cbdd32e41f2f984c74e89708796836d80515aeaca"
converter: "PyMuPDF4LLM 1.28.0"
---

<!-- page: 1 -->

## MANAGING SMILE RISK 

### PATRICK S. HAGAN<sup>¤</sup> , DEEP KUMAR<sup>y</sup> , ANDREW S. LESNIEWSKI<sup>z</sup> , AND DIANA E. WOODWARD<sup>x</sup> 

Abstract. Market smiles and skews are usually managed by using local volatility models a la Dupire. We discover that the dynamics of the market smile predicted by local vol models is opposite of observed market behavior: when the price of the underlying decreases, local vol models predict that the smile shifts to higher prices; when the price increases, these models predict that the smile shifts to lower prices. Due to this contradiction between model and market, delta and vega hedges derived from the model can be unstable and may perform worse than naive Black-Scholes’ hedges. 

To eliminate this problem, we derive the SABR model, a stochastic volatility model in which the forward value satis…es 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0001-04.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0001-05.png)


and the forward F<sup>^</sup> and volatility ^a are correlated: dW1dW2 = ½dt. We use singular perturbation techniques to obtain the prices of European options under the SABR model, and from these prices we obtain explicit, closed-form algebraic formulas for the implied volatility as functions of today’s forward price f = F<sup>^</sup> (0) and the strike K . These formulas immediately yield the market price, the market risks, including vanna and volga risks, and show that the SABR model captures the correct dynamics of the smile. We apply the SABR model to USD interest rate options, and …nd good agreement between the theoretical and observed smiles. 

Key words. smiles, skew, dynamic hedging, stochastic vols, volga, vanna 

1. Introduction. European options are often priced and hedged using Black’s model, or, equivalently, the Black-Scholes model. In Black’s model there is a one-to-one relation between the price of a European option and the volatility parameter ¾B. Consequently, option prices are often quoted by stating the implied volatility ¾B, the unique value of the volatility which yields the option’s dollar price when used in Black’s model. In theory, the volatility ¾B in Black’s model is a constant. In practice, options with di¤erent strikes K require di¤erent volatilities ¾B to match their market prices. See …gure 1. Handling these market skews and smiles correctly is critical to …xed income and foreign exchange desks, since these desks usually have large exposures across a wide range of strikes. Yet the inherent contradiction of using di¤erent volatilities for di¤erent options makes it di¢cult to successfully manage these risks using Black’s model. 

The development of local volatility models by Dupire [2], [3] and Derman-Kani [4], [5] was a major advance in handling smiles and skews. Local volatility models are self-consistent, arbitrage-free, and can be calibrated to precisely match observed market smiles and skews. Currently these models are the most poThis model was featured at a Risk conference in 2000, and istherefore in the public domain. So post away. Of course any mentioning of my name in public or publications would be welcome since I am still trying to establish my reputation.pular way of managing smile and skew risk. However, as we shall discover in section 2, the dynamic behavior of smiles and skews predicted by local vol models is exactly opposite the behavior observed in the marketplace: when the price of the underlying asset decreases, local vol models predict that the smile shifts to higher prices; when the price increases, these models predict that the smile shifts to lower prices. In reality, asset prices and market smiles move in the same direction. This contradiction between the model and the marketplace tends to de-stabilize the delta and vega hedges derived from local volatility models, and often these hedges perform worse than the naive Black-Scholes’ hedges. 

To resolve this problem, we derive the SABR model, a stochastic volatility model in which the asset price and volatility are correlated. Singular perturbation techniques are used to obtain the prices of European options under the SABR model, and from these prices we obtain a closed-form algebraic formula for the 

> ¤phagan@nomurany.com; Nomura Securities International; 2 World Financial Center, Bldg B; New York NY 10281 

> yBNP Paribas; 787 Seventh Avenue; New York NY 10019 

> zBNP Paribas; 787 Seventh Avenue; New York NY 10019 

> xSociete Generale; 1221 Avenue of the Americas; New York NY 10020

<!-- page: 2 -->

implied volatility as a function of today’s forward price f and the strike K. This closed-form formula for the implied volatility allows the market price and the market risks, including vanna and volga risks, to be obtained immediately from Black’s formula. It also provides good, and sometimes spectacular, …ts to the implied volatility curves observed in the marketplace. See …gure 1.1. More importantly, the formula shows that the SABR model captures the correct dynamics of the smile, and thus yields stable hedges. 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0002-01.png)


<!-- Start of picture text -->
M99 Eurodollar option<br>30<br>25<br>20<br>15<br>10<br>5<br>92.0 93.0 94.0 95.0 96.0 97.0<br>Strike<br>Vol (%)<br><!-- End of picture text -->

Fig. 1.1. Implied volatility for the June 99 Eurodollar options. Shown are close-of-day values along with the volatilities predicted by the SABR model. Data taken from Bloomberg information services on March 23, 1999. 

2. Reprise. Consider a European call option on an asset A with exercise date tex, settlement date tset, and strike K . If the holder exercises the option on tex, then on the settlement date tset he receives the underlying asset A and pays the strike K . To derive the value of the option, de…ne F<sup>^</sup> (t) to be the forward price of the asset for a forward contract that matures on the settlement date tset, and de…ne f = F<sup>^</sup> (0) to be today’s forward price. Also let D(t) be the discount factor for date t; that is, let D(t) be the value today of $1 to be delivered on date t. In Appendix A the fundamental theorem of arbitrage free pricing [6], [7] is used to develop the theoretical framework for European options. There it is shown that the value of the call option is 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0002-04.png)


and the value of the corresponding European put is 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0002-06.png)


Here the expectation E is over the forward measure, and “jF0” can be interpretted as “given all information available at t = 0.” See Appendix A. In Appendix A it is also shown that the forward price F<sup>^</sup> (t) is a

<!-- page: 3 -->

Martingale under the forward measure. Therefore, the Martingale representation theorem implies that F<sup>^</sup> (t) evolves according to 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0003-01.png)


for some coe¢cient C(t; ¤), where dW is Brownian motion in this measure. The coe¢cient C (t; ¤) may be deterministic or random, and may depend on any information that can be resolved by time t. This is as far as the fundamental theory of arbitrage free pricing goes. In particular, one cannot determine the coe¢cient C(t; ¤) on purely theoretical grounds. Instead one must postulate a mathematical model for C (t; ¤): 

European swaptions …t within an indentical framework. Consider a European swaption with exercise date tex and …xed rate (strike) Rfix. Let Rs(t) be the swaption’s forward swap rate as seen at date t, and let R0 = R<sup>^</sup> s(0) be the forward swap rate as seen today. In Appendix A we show that the value of a payer swaption is 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0003-04.png)


and the value of a receiver swaption is 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0003-06.png)


Here L0 is today’s value of the level (annuity ), which is a known quantity, and E is the expectation over the level measure of Jamshidean [9]. In Appendix A it is also shown that the forward swap rate R<sup>^</sup> s(t) is a Martingale in this measure, so once again 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0003-08.png)


where dW is Brownian motion. As before, the coe¢cient C(t; ¤) may be deterministic or random, and cannot be determined from fundamental theory. Apart from notation, this is identical to the framework provided by equations 2.1a - 2.1c for European calls and puts. Caplets and ‡oorlets can also be included in this picture, since they are just one period payer and receiver swaptions. For the remainder of the paper, we adopt the notation of 2.1a - 2.1c for general European options. 

2.1. Black’s model and implied volatilities. To go any further requires postulating a model for the coe¢cient C (t; ¤). In [10], Black postulated that the coe¢cient C(t; ¤) is ¾BF<sup>^</sup> (t), where the volatilty ¾B is a constant. The forward price F<sup>^</sup> (t) is then geometric Brownian motion: 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0003-11.png)


Evaluating the expected values in 2.1a, 2.1b under this model then yields Black’s formula, 

(2.4a) Vcall = D(tset)ff N (d1) ¡ K N (d2)g; (2.4b) Vput = Vcall + D(tset)[K ¡ f ]; 

where 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0003-15.png)


for the price of European calls and puts, as is well-known [10], [11], [12].

<!-- page: 4 -->

All parameters in Black’s formula are easily observed, except for the volatility ¾B..An option’s implied volatility is the value of ¾B that needs to be used in Black’s formula so that this formula matches the market price of the option. Since the call (and put) prices in 2.4a - 2.4c are increasing functions of ¾B, the volatility ¾B implied by the market price of an option is unique. Indeed, in many markets it is standard practice to quote prices in terms of the implied volatility ¾B; the option’s dollar price is then recovered by substituting the agreed upon ¾B into Black’s formula. 

The derivation of Black’s formula presumes that the volatility ¾B is a constant for each underlying asset A. However, the implied volatility needed to match market prices nearly always varies with both the strike K and the time-to-exercise tex. See …gure 2.1. Changing the volatility ¾B means that a di¤erent model is being used for the underlying asset for each K and tex. This causes several problems managing large books of options. 

The …rst problem is pricing exotics. Suppose one needs to price a call option with strike K 1 which has, say, a down-and-out knock-out at K2 < K 1. Should we use the implied volatility at the call’s strike K 1, the implied volatility at the barrier K2, or some combination of the two to price this option? Clearly, this option cannot be priced without a single, self-consistent, model that works for all strikes without “adjustments.” 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0004-03.png)


<!-- Start of picture text -->
0.28<br>0.26<br>1m<br>0.24<br>3m<br>6m<br>0.22<br>12m<br>0.20<br>0.18<br>80 90 100 110 120<br>Strike<br>Vol<br><!-- End of picture text -->

Fig. 2.1. Implied volatility ¾B(K ) as a function of the strike K for 1 month, 3 month, 6 month, and 12 month European options on an asset with forward price 100. 

The second problem is hedging. Since di¤erent models are being used for di¤erent strikes, it is not clear that the delta and vega risks calculated at one strike are consistent with the same risks calculated at other strikes. For example, suppose that our 1 month option book is long high strike options with a total ¢ risk of +$1MM , and is long low strike options with a ¢ of ¡$1MM . Is our is our option book really ¢-neutral, or do we have residual delta risk that needs to be hedged? Since di¤erent models are used at each strike, it is not clear that the risks o¤set each other. Consolidating vega risk raises similar concerns. Should we assume parallel or proportional shifts in volatility to calculate the total vega risk of our book? More explicitly, suppose that ¾B is 20% at K = 100 and 24% at K = 90, as shown for the 1m options in …gure 2.1. Should we calculate vega by bumping ¾B by, say, 0:2% for both options? Or by bumping ¾B by 0:2% for the …rst option and by 0:24% for the second option? These questions are critical to e¤ective book

<!-- page: 5 -->

management, since this requires consolidating the delta and vega risks of all options on a given asset before hedging, so that only the net exposure of the book is hedged. Clearly one cannot answer these questions without a model that works for all strikes K. 

The third problem concerns evolution of the implied volatility curve ¾B(K). Since the implied volatility ¾B depends on the strike K, it is likely to also depend on the current value f of the forward price: ¾B = ¾B(f;K ). In this case there would be systematic changes in ¾B as the forward price f of the underlying changes See …gure 2.1. Some of the vega risks of Black’s model would actually be due to changes in the price of the underlying asset, and should be hedged more properly (and cheaply) as delta risks. 

2.2. Local volatility models. An apparent solution to these problems is provided by the local volatility model of Dupire [2], which is also attributed to Derman [4], [5]. In an insightful work, Dupire essentially argued that Black was to bold in setting the coe¢cient C (t; ¤) to ¾BF<sup>^</sup> . Instead one should only assume that C is Markovian: C = C(t; F<sup>^</sup> ). Re-writing C(t; F<sup>^</sup> ) as ¾loc(t; F<sup>^</sup> )F<sup>^</sup> then yields the “local volatility model,” where the forward price of the asset is 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0005-03.png)


in the forward measure. Dupire argued that instead of theorizing about the unknown local volatility function ¾loc(t; F<sup>^</sup> ), one should obtain ¾loc (t; F<sup>^</sup> ) directly from the marketplace by “calibrating” the local volatility model to market prices of liquid European options. 

In calibration, one starts with a given local volatility function ¾loc (t; F<sup>^</sup> ), and evaluates 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0005-06.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0005-07.png)


to obtain the theoretical prices of the options; one then varies the local volatility function ¾loc(t; F<sup>^</sup> ) until these theoretical prices match the actual market prices of the option for each strike K and exercise date tex. In practice liquid markets usually exist only for options with speci…c exercise dates t<sup>1</sup> ex<sup>; t2</sup> ex<sup>; t3</sup> ex<sup>; : : :;for</sup> example, for 1m, 2m, 3m, 6m, and 12m from today. Commonly the local vols ¾loc (t; F<sup>^</sup> ) are taken to be piecewise constant in time: 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0005-09.png)


One …rst calibrates ¾<sup>(1)</sup> loc<sup>( ^F)to reproducetheoption pricesatt1</sup> ex<sup>forall strikes K ,thencalibrates ¾(2)</sup> loc<sup>(F^)to</sup> reproduce the option prices at t<sup>2</sup> ex<sup>, forallK,and soforth .This calibration process can be greatlysimpli…ed</sup> by using the results in [13] and [14]. There we solve to obtain the prices of European options under the local volatility model 2.5a - 2.5c, and from these prices we obtain explicit algebraic formulas for the implied volatility of the local vol models. 

Once ¾loc(t; F<sup>^</sup> ) has been obtained by calibration, the local volatility model is a single, self-consistent model which correctly reproduces the market prices of calls (and puts) for all strikes K and exercise dates tex without “adjustment.” Prices of exotic options can now be calculated from this model without ambiguity. This model yields consistent delta and vega risks for all options, so these risks can be consolidated across strikes. Finally, perturbing f and re-calculating the option prices enables one to determine how the implied volatilites change with changes in the underlying asset price. Thus, the local volatility model thus provides a method of pricing and hedging options in the presence of market smiles and skews. It is perhaps the most popular method of managing exotic equity and foreign exchange options. Unfortunately, the local

<!-- page: 6 -->

volatility model predicts the wrong dynamics of the implied volatility curve, which leads to inaccruate and often unstable hedges. 

To illustrate the problem, consider the special case in which the local vol is a function of F<sup>^</sup> only: 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0006-02.png)


In [13] and [14] singular perturbation methods were used to analyze this model. There it was found that European call and put prices are given by Black’s formula 2.4a - 2.4c with the implied volatility 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0006-04.png)


On the right hand side, the …rst term dominates the solution and the second term provides a much smaller correction The omitted terms are very small, usually less than 1% of the …rst term. 

The behavior of local volatility models can be largely understood by examining the …rst term in 2.8. The implied volatility depends on both the strike K and the current forward price f: So supppose that today the forward price is f0 and the implied volatility curve seen in the marketplace is ¾<sup>0</sup> B<sup>(K).Calibratingthe</sup> model to the market clearly requires choosing the local volatility to be 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0006-07.png)


Now that the model is calibrated, let us examine its predictions. Suppose that the forward value changes from f0 to some new value f . From 2.8, 2.9 we see that the model predicts that the new implied volatility curve is 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0006-09.png)


for an option with strike K, given that the current value of the forward price is f. In particular, if the forward price f0 increases to f , the implied volatility curve moves to the left ; if f0 decreases to f , the implied volatility curve moves to the right. Local volatility models predict that the market smile/skew moves in the opposite direction as the price of the underlying asset. This is opposite to typical market behavior, in which smiles and skews move in the same direction as the underlying. 

To demonstrate the problem concretely, suppose that today’s implied volatility is a perfect smile 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0006-12.png)


around today’s forward price f0. Then equation 2.8 implies that the local volatility is 

(2.11b) ¾loc(F<sup>^</sup> ) = ® + 3¯(F<sup>^</sup> ¡ f0)<sup>2</sup> + ¢ ¢ ¢ : 

As the forward price f evolves away from f0 due to normal market ‡uctuations, equation 2.8 predicts that the implied volatility is 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0006-16.png)


. The implied volatility curve not only moves in the opposite direction as the underlying, but the curve also shifts upward regardless of whether f increases or decreases. Exact results are illustrated in …gures 2.2 - 2.4. There we assumed that the local volatility ¾loc ( F<sup>^</sup> ) was given by 2.11b, and used …nite di¤erence methods to obtain essentially exact values for the option prices, and thus implied volatilites. 

Hedges calculated from the local volatility model are wrong. To see this, let BS(f; K; ¾B; tex) be Black’s formula 2.4a - 2.4c for, say, a call option. Under the local volatility model, the value of a call option is given by Black’s formula 

(2.12a) Vcall = BS(f; K; ¾B(K; f ); tex)

<!-- page: 7 -->

![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0007-00.png)


<!-- Start of picture text -->
0.28<br>0.26<br>0.24<br>0.22<br>0.20<br>0.18<br>80 90 100f0 110 K 120<br>Implied Vol<br><!-- End of picture text -->

Fig. 2.2. Exact implied volatility ¾B(K; f0) (solid line) obtained from the local volatility ¾loc( F<sup>^</sup> ) (dashed line): 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0007-02.png)


<!-- Start of picture text -->
0.28<br>0.26<br>0.24<br>0.22<br>0.20<br>0.18<br>80 90f 10f 0 110 K120<br>Implied Vol<br><!-- End of picture text -->

Fig. 2.3. Implied volatility ¾B(K; f ) if the forward price decreases from f0 to f (solid line). 

with the volatility ¾B(K; f ) given by 2.8. Di¤erentiating with respect to f yields the ¢ risk 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0007-05.png)


predicted by the local volatility model. The …rst term is clearly the ¢ risk one would calculate from Black’s model using the implied volatility from the market. The second term is the local volatility model’s correction to the ¢ risk, which consists of the Black vega risk multiplied by the predicted change in ¾B due to changes in the underlying forward price f . In real markets the implied volatily moves in the opposite direction as the direction predicted by the model. Therefore, the correction term needed for real markets should have the opposite sign as the correction predicted by the local volatility model. The original Black model yields more accurate hedges than the local volatility model, even though the local vol model is self-consistent across strikes and Black’s model is inconsistent. 

Local volatility models are also peculiar theoretically. Using any function for the local volatility ¾ loc (t; F<sup>^</sup> ) except for a power law, 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0007-08.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0007-09.png)

<!-- page: 8 -->

![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0008-00.png)


<!-- Start of picture text -->
0.28<br>0.26<br>0.24<br>0.22<br>0.20<br>0.18<br>80 90 100f0 110f K120<br>Implied Vol<br><!-- End of picture text -->

Fig. 2.4. Implied volatility ¾B(K; f ) if the forward prices increases from f0 to f (solid line). 

introduces an intrinsic “length scale” for the forward price F<sup>^</sup> into the model. That is, the model becomes inhomogeneous in the forward price F<sup>^</sup> . Although intrinsic length scales are theoretically possible, it is di¢cult to understand the …nancial origin and meaning of these scales [15], and one naturally wonders whether such scales should be introduced into a model without speci…c theoretical justi…cation. 

2.3. The SABR model. The failure of the local volatility model means that we cannot use a Markovian model based on a single Brownian motion to manage our smile risk. Instead of making the model non-Markovian, or basing it on non-Brownian motion, we choose to develop a two factor model. To select the second factor, we note that most markets experience both relatively quiescent and relatively chaotic periods. This suggests that volatility is not constant, but is itself a random function of time. Respecting the preceding discusion, we choose the unknown coe¢cient C (t; ¤) to be ®^F<sup>^¯</sup> , where the “volatility” ®^ is itself a stochastic process. Choosing the simplest reasonable process for ®^ now yields the “stochastic-®¯½ model,” which has become known as the SABR model. In this model, the forward price and volatility are 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0008-04.png)


under the forward measure, where the two processes are correlated by: 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0008-06.png)


Many other stochastic volatility models have been proposed, for example [16], [17], [18], [19]; these models will be treated in section 5. However, the SABR model has the virtue of being the simplest stochastic volatility model which is homogenous in F<sup>^</sup> and ®^. We shall …nd that the SABR model can be used to accurately …t the implied volatility curves observed in the marketplace for any single exercise date tex. More importantly, it predicts the correct dynamics of the implied volatility curves. This makes the SABR model an e¤ective means to manage the smile risk in markets where each asset only has a single exercise date; these markets include the swaption and caplet/‡oorlet markets. As written, the SABR model may or may not …t the observed volatility surface of an asset which has European options at several di¤erent exercise dates; such markets include foreign exchange options and most equity options. Fitting volatility surfaces requires the dynamic SABR model which is introduced and analyzed in section 4.

<!-- page: 9 -->

It has been claimed by many authors that stochastic volatility models are models of incomplete markets, because the stochastic volatility risk cannot be hedged. This is not true. It is true that the risk to changes in ®^ (the vega risk) cannot be hedged by buying or selling the underlying asset. However, vega risk can be hedged by buying or selling options on the asset in exactly the same way that ¢-hedging is used to neutralize the risks to changes in the price F<sup>^</sup> . In practice, vega risks are hedged by buying and selling options as a matter of routine, so whether the market would be complete if these risks were not hedged is a moot question. 

The SABR model 2.15a - 2.15c is analyzed in Appendix B. There singular perturbation techniques are used to obtain the prices of European options. From these prices, the options’ implied volatility ¾B(K; f ) is then obtained. The upshot of this analysis is that under the SABR model, the price of European options is given by Black’s formula, 

(2.16a) Vcall = D(tset)ff N (d1) ¡ K N (d2)g; (2.16b) Vput = Vcall + D(tset)[K ¡ :f ]; 

with 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0009-04.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0009-05.png)


where the implied volatility ¾B(f; K) is given by 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0009-07.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0009-08.png)


Here 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0009-10.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0009-11.png)


and x(z) is de…ned by 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0009-13.png)


For the special case of at-the-money options, options struck at K = f , this formula reduces to 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0009-15.png)


These formulas are the main result of this paper. Although it appears formidable, the formula is explicit and only involves elementary trignometric functions. Implementing the SABR model for vanilla options is very easy, since once this formula is programmed, we just need to send the options to a Black pricer.In the next section we examine the qualitative behavior of this formula, and how it can be used to managing smile risk. 

The complexity of the formula is needed for accurate pricing. Omitting the last line of 2.17a, for example, can result in a relative error that exceeds three per cent in extreme cases. Although this error term seems “ ” small, it is large enough to be required for accurate pricing. The omitted terms + ¢ ¢ ¢ are much, much smaller. Indeed, even though we have derived more accurate expressions by continuing the perturbation

<!-- page: 10 -->

expansion to higher order, 2.17a - 2.17c is the formula we use to value and hedge our vanilla swaptions, caps, and ‡oors. We have not implemented the higher order results, believing that the increased precision of the higher order results is super‡uous. 

There are two special cases of note: ¯ = 1, representing a stochastic log normal model), and ¯ = 0, representing a stochastic normal model. The implied volatility for these special cases is obtained in the last section of Appendix B. 

3. Managing smile risk. The complexity of the above formula for ¾B(K; f ) obscures the qualitative behavior of the SABR model. To make the model’s phenomenology and dynamics more transparent, note that formula 2.17a - 2.17c can be approximated as 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0010-03.png)


provided that the strike K is not too far from the current forward f . Here the ratio 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0010-05.png)


measures the strength º of the volatility of volatility (the “volvol”) compared to the local volatility ®=f<sup>1¡¯</sup> at the current forward. Although equations 3.1a - 3.1b should not be used to price real deals, they are accurate enough to depict the qualitative behavior of the SABR model faithfully. 

As f varies during normal trading, the curve that the ATM volatility ¾B (f; f ) traces is known as the backbone, while the smile and skew refer to the implied volatility ¾B (K; f ) as a function of strike K for a …xed f. That is, the market smile/skew gives a snapshot of the market prices for di¤erent strikes K at a given instance, when the forward f has a speci…c price. Figures 3.1 and 3.2. show the dynamics of the smile/skew predicted by the SABR model. 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0010-08.png)


<!-- Start of picture text -->
22%<br>20%<br>β = 0<br>18%<br>16%<br>14%<br>12%<br>10%<br>8%<br>4% 6% 8% 10% 12%<br>Imp<br><!-- End of picture text -->

Fig. 3.1. Backbone and smiles for ¯ = 0. As the forward f varies, the implied volatiliity ¾B (f; f ) of ATM options traverses the backbone (dashed curve). Shown are the smiles ¾B(K; f ) for three di¤erent values of the forward. Volatility data from 1 into 1 swaption on 4/28/00, courtesy of Cantor-Fitzgerald. 

Let us now consider the implied volatility ¾B(K;f ) in detail. The …rst factor ®=f<sup>1¡¯</sup> in 3.1a is the implied volatility for at-the-money (ATM) options, options whose strike K equals the current forward f . So the backbone traversed by ATM options is essentially ¾B(f; f ) = ®=f<sup>1¡¯</sup> for the SABR model. The

<!-- page: 11 -->

![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0011-00.png)


<!-- Start of picture text -->
22%<br>20%<br>18% β = 1<br>16%<br>14%<br>12%<br>10%<br>8%<br>4% 6% 8% 10% 12%<br>Implie<br><!-- End of picture text -->

Fig. 3.2. Backbone and smiles as above, but for ¯ = 1. 

backbone is almost entirely determined by the exponent ¯ , with the exponent ¯ = 0 (a stochastic Gaussian model) giving a steeply downward sloping backbone, and the exponent ¯ = 1 giving a nearly ‡at backbone. The second term ¡<sup><u>1</u></sup> 2<sup>(1 ¡ ¯ ¡ ½¸)log K=frepresentstheskew,theslopeoftheimpliedvolatilitywith</sup> respect to the strike K . The ¡<sup><u>1</u></sup> 2<sup>(1¡ ¯)log K=fpartisthebetaskew,whichisdownwardslopingsince</sup> ^ ^ 0· ¯ · 1. It arises because the “local volatility” ®F<sup>^¯</sup> =F<sup>^1</sup> = ®=F<sup>^1¡¯</sup> is a decreasing function of the forward price. The second part<sup>~~1~~</sup> 2<sup>½¸ log K=fisthevannaskew,theskewcaused bythecorrelationbetween</sup> the volatility and the asset price. Typically the volatility and asset price are negatively correlated, so on average, the volatility ® would decrease (increase) when the forward f increases (decreases). It thus seems unsurprising that a negative correlation ½ causes a downward sloping vanna skew. 

It is interesting to compare the skew to the slope of the backbone. As f changes to f<sup>0</sup> the ATM vol changes to 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0011-04.png)


Near K = f , the ¯ component of skew expands as 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0011-06.png)


so the slope of the backbone ¾B (f; f ) is twice as steep as the slope of rthe smile ¾ B(K; f ) due to the ¯-component of the skew. 

<u>1</u> The last term in 3.1a also contains two parts. The …rst part 12<sup>(1 ¡ ¯)2 log2 K=fappearstobeasmile</sup> (quadratic) term, but it is dominated by the downward sloping beta skew, and, at reasonable strikes K , it just modi…es this skew somewhat. The second part 12 ~~1~~<sup>(2¡ 3½2)¸2 log2 K=fis the smileinduced bythevolga</sup> (vol-gamma) e¤ect. Physically this smile arises because of “adverse selection”: unusually large movements of the forward F<sup>^</sup> happen more often when the volatility ® increases, and less often when ® decreases, so strikes K far from the money represent, on average, high volatility environments. 

3.1. Fitting market data. The exponent ¯ and correlation ½ a¤ect the volatility smile in similar ways. They both cause a downward sloping skew in ¾B(K; f) as the strike K varies. From a single market snapshot of ¾B(K;f ) as a function of K at a given f , it is di¢cult to distinguish between the two parameters.

<!-- page: 12 -->

This is demonstrated by …gure 3.3. There we …t the SABR parameters ®; ½; º with ¯ = 0 and then re-…t the parameters ®; ½; º with ¯ = 1. Note that there is no substantial di¤erence in the quality of the …ts, despite the presence of market noise. This matches our general experience: market smiles can be …t equally well with any speci…c value of ¯. In particular, ¯ cannot be determined by …tting a market smile since this would clearly amount to “…tting the noise.” 

# **1y into 1y** 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0012-02.png)


<!-- Start of picture text -->
22%<br>20%<br>18%<br>16%<br>14%<br>12%<br>4% 6% 8% 10% 12%<br>Implie<br><!-- End of picture text -->

Fig. 3.3. Implied volatilities as a function of strike. Shown are the curves obtained by …tting the SABR model with exponent ¯ = 0 and with ¯ = 1 to the 1y into 1y swaption vol observed on 4/28/00. As usual, both …ts are equally good. Data courtesy of Cantor-Fitzgerald. Figure 3.3 also exhibits a common data quality issue. Options with strikes K away from the current forward f trade less frequently than at-the-money and near-the-money options. Consequently, as K moves away from f , the volatility quotes become more suspect because they are more likely to be out-of-date and not represent bona …de o¤ers to buy or sell options. 

Suppose for the moment that the exponent ¯ is known or has been selected. Taking a snapshot of the market yields the implied volatility ¾B(K; f ) as a function of the strike K at the current forward price f . With ¯ given, …tting the SABR model is a straightforward procedure. The three parameters ®; ½; and º have di¤erent e¤ects on the curve: the parameter ® mainly controls the overall height of the curve, changing the correlation ½ controls the curve’s skew, and changing the vol of vol º controls how much smile the curve exhibits. Because of the widely seperated roles these parameters play, the …tted parameter values tend to be very stable, even in the presence of large amounts of market noise. 

The exponent ¯ can be determined from historical observations of the “backbone” or selected from “aesthetic considerations.” Equation 2.18 shows that the implied volatility of ATM options is 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0012-06.png)


The exponent ¯ can be extracted from a log log plot of historical observations of f; ¾AT M pairs. Since both f and ® are stochastic variables, this …tting procedure can be quite noisy, and as the [¢ ¢ ¢ ]tex term is typically less than one or two per cent, it is usually ignored in …tting ¯.

<!-- page: 13 -->

Selecting ¯ from “aesthetic” or other a priori considerations usually results in ¯ = 1 (stochastic lognormal), ¯ = 0 (stochastic normal), or ¯ =<sup><u>1</u></sup> 2<sup>(stochasticCIR)models.Proponentsof¯=1citelognormal</sup> models as being “more natural.” or believe that the horizontal backbone best represents their market. These proponents often include desks trading foreign exchange options. Proponents of ¯ = 0 usually believe that a normal model, with its symmetric break-even points, is a more e¤ective tool for managing risks, and would claim that ¯ = 0 is essential for trading markets like Yen interest rates, where the forwards f can be negative or near zero. Proponents of ¯ =<sup><u>1</u></sup> 2<sup>areusuallyUSinterestratedesks thathavedevelopedtrustinCIR</sup> models. 

It is usually more convenient to use the at-the-money volatility ¾AT M ; ¯; ½; and º as the SABR parameters instead of the original parameters ®,¯; ½; º:The parameter ® is then found whenever needed by inverting 2.18 on the ‡y; this inversion is numerically easy since the [¢ ¢¢ ]tex term is small. With this parameterization, …tting the SABR model requires …tting ½ and º to the implied volatility curve, with ¾ATM and ¯ given. In many markets, the ATM volatilities need to be updated frequently, say once or twice a day, while the smiles and skews need to be updated infrequently, say once or twice a month. With the new parameterization, ¾AT M can be updated as often as needed, with ½, º (and ¯) updated only as needed. 

Let us apply SABR to options on US dollar interest rates. There are three key groups of European options on US rates: Eurodollar future options, caps/‡oors, and European swaptions. Eurodollar future options are exchange-traded options on the 3 month Libor rate; like interest rate futures, EDF options are quoted on 100(1 ¡ rLibor). Figure 1.1 …ts the SABR model (with ¯ = 1) to the implied volatility for the June 99 contracts, and …gures 3.4 - 3.7 …t the model (also with ¯ = 1) to the implied volatility for the September 99, December 99, and March 00 contracts. All prices were obtained from Bloomberg Information Services on March 23, 1999. Two points are shown for the same strike where there are quotes for both puts and calls. Note that market liquidity dries up for the later contracts, and for strikes that are too far from the money. Consequently, more market noise is seen for these options. 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0013-03.png)


<!-- Start of picture text -->
U 9 9 E u r o d o l l a r o p t i o n<br>30<br>25<br>20<br>15<br>10<br>93.0 94.0 95.0 96.0 97.0<br>S t r i k e<br>Vol (%)<br><!-- End of picture text -->

Fig. 3.4. Volatility of the Sep 99 EDF options 

Caps and ‡oors are sums of caplets and ‡oorlets; each caplet and ‡oorlet is a European option on the 3 month Libor rate. We do not consider the cap/‡oor market here because the broker-quoted cap prices must be “stripped” to obtain the caplet volatilities before SABR can be applied. 

A m year into n year swaption is a European option with m years to the exercise date (the maturity); if it is exercised, then one receives an n year swap (the tenor, or underlying) on the 3 month Libor rate. See Appendix A. For almost all maturities and tenors, the US swaption market is liquid for at-the-money

<!-- page: 14 -->

![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0014-00.png)


<!-- Start of picture text -->
Z 9 9 E u r o d o l l a r o p t i o n<br>20<br>18<br>16<br>14<br>92.0 93.0 94.0 95.0 96.0<br>S t r i k e<br>Vol (%)<br><!-- End of picture text -->

Fig. 3.5. Volatility of the Dec 99 EDF options 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0014-02.png)


<!-- Start of picture text -->
H 0 0 E u r o d o l l a r o p t i o n<br>24<br>22<br>20<br>18<br>16<br>14<br>92.0 93.0 94.0 95.0 96.0 97.0<br>S t r i k e<br>Vol (%)<br><!-- End of picture text -->

Fig. 3.6. Volatility of the Mar 00 EDF options 

swaptions, but is ill-liquid for swaptions struck away from the money. Hence, market data is somewhat suspect for swaptions that are not struck near the money. Figures 3.8 - 3.11 …ts the SABR model (with ¯ = 1) to the prices of m into5Y swaptions observed on April 28, 2000. Data supplied courtesy of CantorFitzgerald. 

We observe that the smile and skew depend heavily on the time-to-exercise for Eurodollar future options and swaptions. The smile is pronounced for short-dated options and ‡attens for longer dated options; the skew is overwhelmed by the smile for short-dated options, but is important for long-dated options. This picture is con…rmed tables 3.1 and 3.2. These tables show the values of the vol of vol º and correlation ½ obtained by …tting the smile and skew of each “m into n” swaption, again using the data from April 28, 2000. Note that the vol of vol º is very high for short dated options, and decreases as the time-to-exercise increases, while the correlations starts near zero and becomes substantially negative. Also note that there is little dependence of the market skew/smile on the length of the underlying swap; both º and ½ are fairly constant across each row. This matches our general experience: in most markets there is a strong smile for

<!-- page: 15 -->

### **M 0 0 E u r o d o l l a r o p t i o n** 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0015-01.png)


<!-- Start of picture text -->
24<br>22<br>20<br>18<br>16<br>14<br>92.0 93.0 94.0 95.0 96.0 97.0<br>S t r i k e<br>Vol (%)<br><!-- End of picture text -->

Fig. 3.7. Volatility of the Jun 00 EDF options 

**3M into 5Y** 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0015-04.png)


<!-- Start of picture text -->
20%<br>18%<br>16%<br>14%<br>12%<br>4% 6% 8% 10% 12%<br><!-- End of picture text -->

Fig. 3.8. Volatilities of 3 month into 5 year swaption 

short-dated options which relaxes as the time-to-expiry increases; consequently the volatility of volatility º is large for short dated options and smaller for long-dated options, regardless of the particular underlying. Our experience with correlations is less clear: in some markets a nearly ‡at skew for short maturity options develops into a strongly downward sloping skew for longer maturities. In other markets there is a strong downward skew for all option maturities, and in still other markets the skew is close to zero for all maturities. 

3.2. Managing smile risk. After choosing ¯ and …tting ½, º , and either ® or ¾AT M , the SABR model 

^ ^ (3.4a) dF<sup>^</sup> = ®F<sup>^¯</sup> dW1; F (0) = f ^ ^ ^ (3.4b) d® = º® dW2; ®(0) = ® 

with 

(3.4c) dW1 dW2 = ½dt

<!-- page: 16 -->

![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0016-00.png)


<!-- Start of picture text -->
1Y into 5Y<br>18%<br>17%<br>16%<br>15%<br>14%<br>13%<br>4% 6% 8% 10% 12%<br><!-- End of picture text -->

Fig. 3.9. Volatilities of 1 year into 1 year swaptions 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0016-02.png)


<!-- Start of picture text -->
5Y into 5Y<br>17%<br>16%<br>15%<br>14%<br>13%<br>12%<br>4% 6% 8% 10% 12%<br><!-- End of picture text -->

Fig. 3.10. Volatilities of 5 year into 5 year swaptions 

…ts the smiles and skews observed in the market quite well, especially considering the quality of price quotes away from the money . Let us take for granted that it …ts well enough. Then we have a single, self-consistent model that …ts the option prices for all strikes K without “adjustment,” so we can use this model to price exotic options without ambiguity. The SABR model also predicts that whenever the forward price f changes, the the implied volatility curve shifts in the same direction and by the same amount as the price f . This predicted dynamics of the smile matches market experience. If ¯ < 1, the “backbone” is downward sloping, so the shift in the implied volatility curve is not purely horizontal. Instead, this curve shifts up and down as the at-the-money point traverses the backbone. Our experience suggests that the parameters ½ and º are very stable (¯ is assumed to be a given constant), and need to be re-…t only every few weeks. This stability may be because the SABR model reproduces the usual dynamics of smiles and skews. In contrast, the at-the-money volatility ¾ ATM , or, equivalently, ® may need to be updated every few hours in fast-paced markets. 

Since the SABR model is a single self-consistent model for all strikes K, the risks calculated at one strike

<!-- page: 17 -->

![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0017-00.png)


<!-- Start of picture text -->
10Y into 5Y<br>13%<br>12%<br>11%<br>10%<br>9%<br>4% 6% 8% 10% 12%<br><!-- End of picture text -->

Fig. 3.11. Volatilities of 10 year into 5 year options 

|º|1Y|2Y|3Y|4Y|5Y|7Y|10Y|
|---|---|---|---|---|---|---|---|
|1M|76.2%|75.4%|74.6%|74.1%|75.2%|73.7%|74.1%|
|3M|65.1%|62.0%|60.7%|60.1%|62.9%|59.7%|59.5%|
|6M|57.1%|52.6%|51.4%|50.8%|49.4%|50.4%|50.0%|
|1Y|59.8%|49.3%|47.1%|46.7%|46.0%|45.6%|44.7%|
|3Y|42.1%|39.1%|38.4%|38.4%|36.9%|38.0%|37.6%|
|5Y|33.4%|33.2%|33.1%|32.6%|31.3%|32.3%|32.2%|
|7Y|30.2%|29.2%|29.0%|28.2%|26.2%|27.2%|27.0%|
|10Y|26.7%|26.3%|26.0%|25.6%|24.8%|24.7%|24.5%|
||||Tab|le 3.1||||


Volatility of volatility º for European swaptions. Rows are time-to-exercise; columns are tenor of the underlying swap. 

are consistent with the risks calculated at other strikes. Therefore the risks of all the options on the same asset can be added together, and only the residual risk needs to be hedged. 

Let us set aside the ¢ risk for the moment, and calculate the other risks. Let BS(f; K; ¾B; tex) be Black’s formula 2.4a - 2.4c for, say, a call option. According to the SABR model, the value of a call is 

(3.5) Vcall = BS(f; K; ¾B(K; f ); tex) 

where the volatility ¾B(K; f ) ´ ¾B(K;f ; ®; ¯; ½; º) is given by equations 2.17a - 2.17c. Di¤erentiating<sup>1</sup> with respect to ® yields the vega risk, the risk to overall changes in volatility: 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0017-08.png)


This risk is the change in value when ® changes by a unit amount. It is traditional to scale vega so that it represents the change in value when the ATM volatility changes by a unit amount. Since ±¾ATM = 

> 1 In practice risks are calculated by …nite di¤erences: valuing the option at ®, re-valuing the option after bumping the forward to ® + ±, and then subtracting to determine the risk This saves di¤erentiating complex formulas such as 2.17a - 2.17c.

<!-- page: 18 -->

|½|1Y|2Y|3Y|4Y|5Y|7Y|10Y|
|---|---|---|---|---|---|---|---|
|1M|4.2%|-0.2%|-0.7%|-1.0%|-2.5%|-1.8%|-2.3%|
|3M|2.5%|-4.9%|-5.9%|-6.5%|-6.9%|-7.6%|-8.5%|
|6M|5.0%|-3.6%|-4.9%|-5.6%|-7.1%|-7.0%|-8.0%|
|1Y|-4.4%|-8.1%|-8.8%|-9.3%|-9.8%|-10.2%|-10.9%|
|3Y|-7.3%|-14.3%|-17.1%|-17.1%|-16.6%|-17.9%|-18.9%|
|5Y|-11.1%|-17.3%|-18.5%|-18.8%|-19.0%|-20.0%|-21.6%|
|7Y|-13.7%|-22.0%|-23.6%|-24.0%|-25.0%|-26.1%|-28.7%|
|10Y|-14.8%|-25.5%|-27.7%|-29.2%|-31.7%|-32.3%|-33.7%|


Table 3.2 

Matrix of correlations ½ between the underlying and the volatility for European swaptons. 

(@¾AT M =@®)±®, the vega risk is 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0018-04.png)


where ¾ATM (f ) = ¾B(f; f ) is given by 2.18. Note that to leading order, @¾B=@® ¼ ¾B =® and @¾ ATM =@® ¼ ¾AT M =®, so the vega risk is roughly given by 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0018-06.png)


Qualitatively, then, vega risks at di¤erent strikes are calculated by bumping the implied volatility at each strike K by an amount that is proportional to the implied volatiity ¾B (K; f ) at that strike. That is, in using equation 3.7a, we are essentially using proportional, and not parallel, shifts of the volatility curve to calculate the total vega risk of a book of options. 

Since ½ and º are determined by …tting the implied volatility curve observed in the marketplace, the SABR model has risks to ½ and º changing. Borrowing terminology from foreign exchange desks, vanna is the risk to ½ changing and volga (vol gamma) is the risk to º changing: 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0018-09.png)


Vanna basically expresses the risk to the skew increasing, and volga expresses the risk to the smile becoming more pronounced. These risks are easily calculated by using …nite di¤erences on the formula for ¾B in equations 2.17a - 2.17c. If desired, these risks can be hedged by buying or selling away-from-the-money options. 

The delta risk expressed by the SABR model depends on whether one uses the parameterization ®, ¯, ½, º or ¾AT M , ¯, ½, º . Suppose …rst we use the parameterization ®, ¯, ½, º, so that ¾B(K; f ) ´ ¾B(K; f ; ®; ¯; ½; º). Di¤erentiating respect to f yields the ¢ risk 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0018-12.png)

<!-- page: 19 -->

The …rst term is the ordinary ¢ risk one would calculate from Black’s model. The second term is the SABR model’s correction to the ¢ risk. It consists of the Black vega times the predicted change in the implied volatility ¾B caused by the change in the forward f . As discussed above, the predicted change consists of a sideways movement of the volatility curve in the same direction (and by the same amount) as the change in the forward price f . In addition, if ¯ < 1 the volatility curve rises and falls as the at-the-money point traverses up and down the backbone. There may also be minor changes to the shape of the skew/smile due to changes in f . 

Now suppose we use the parameterization ¾AMT , ¯, ½, º. Then ® is a function of ¾AT M and f de…ned implicitly by 2.18. Di¤erentiating 3.5 now yields the ¢ risk 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0019-02.png)


The delta risk is now the risk to changes in f with ¾ATM held …xed. The last term is just the change in ® needed to keep ¾AT M constant while f changes. Clearly this last term must just cancel out the vertical component of the backbone, leaving only the sideways movement of the implied volatilty curve. Note that this term is zero for ¯ = 1. 

Theoretically one should use the ¢ from equation 3.9 to risk manage option books. In many markets, however, it may take several days for volatilities ¾B to change following signi…cant changes in the forward price f. In these markets, using ¢ from 3.10 is a much more e¤ective hedge. For suppose one used ¢ from equation 3.9. Then, when the volatility ¾AT M did not immediately change following a change in f , one would be forced to re-mark ® to compensate, and this re-marking would change the ¢ hedges. As ¾ ATM equilibrated over the next few days, one would mark ® back to its original value, which would change the ¢ hedges back to their original value. This “hedging chatter” caused by market delays can prove to be costly. 

4. The dynamic SABR model. Quote results for smile and skew. 

For each exercise date, same smile as in the static SABR model! Same smile dynamics! Calibrating volatility surface is no harder than calibrating smile. 

Show some results. FX options? 

## 5. Conclusions. Other models. Give results for other models 

SABR and dynamic SABR have the advantage of being the simplest models which can be used to risk-manage smiles/skews. 

## Appendix A. Martingale pricing. 

Quote martingale theory. Derive the martingale pricing formulas for general options and for swaptions. 

## Appendix B. Analysis of the SABR model. 

Here we use singular perturbation techniques to price European options under the SABR model. Our analysis is based on a small volatility expansion, where we take both the volatility ®^ and the “volvol” º to be small. To carry out this analysis in a systematic fashion, we re-write ®^ ¡! "®;^ and º ¡! "º, and analyze 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0019-14.png)


with 

(B.1c) dW1dW2 = ½dt; 

in the limit " ¿ 1. This is the distinguished limit [21], [22] in the language of singular perturbation theory. After obtaining the results we replace "®^ ¡! ®;^ and "º ¡! º to get the answer in terms of the original

<!-- page: 20 -->

variables.^ We …rst analyze the model with a general C ( F<sup>^</sup> ), and then specialize the results to the power law F<sup>¯</sup> . This is notationally simpler than working with the power law throughout, and the more general result may prove valuable in some future application. 

We …rst use the forward Kolmogorov equation to simplify the option pricing problem. Suppose the ^ economy is in state F<sup>^</sup> (t) = f; ®(t) = ® at date t. De…ne the probability density p(t; f; ®; T; F; A) by 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0020-02.png)


As a function of the forward variables T; F; A; the density p satis…es the forward Kolmogorov equation (the F½okker-Planck equation) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0020-04.png)


with 

- (B.3b) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0020-07.png)


as is well-known [24], [25], [26]. Here, and throughout, we use subscripts to denote partial derivatives. 

Let V (t; f; ®) be the value of a European call option at date t, when the economy is in state F<sup>^</sup> (t) = ^ f; ®(t) = ®. Let tex be the option’s exercise date, and let K be its strike. Omitting the discount factor D(tset), which factors out exactly, the value of the option is 

- (B.4) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0020-11.png)


See 2.1a. Since 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0020-13.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0020-14.png)


we can re-write V (t; f; ®) as 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0020-16.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0020-17.png)


We substitute B.3a for pT into B.6. Integrating the A derivatives "<sup>2</sup> ½º [A<sup>2</sup> C (F )p]F A and<sup><u>1</u></sup> 2<sup>"2º2[A2p]AAover</sup> all A yields zero. Therefore our option price reduces to 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0020-19.png)


where we have switched the order of integration. Integrating by parts twice with respect to F now yields 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0020-21.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0020-22.png)


The problem can be simpli…ed further by de…ning 

- (B.9) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0020-25.png)

<!-- page: 21 -->

Then P satis…es the backward’s Kolmogorov equation [24], [25], [26] 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0021-01.png)


Since t does not appear explicitly in this equation, P depends only on the combination T ¡ t, and not on t and T separately. So de…ne 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0021-03.png)


Then our pricing formula becomes 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0021-05.png)


where P (¿; f; ®; K) is the solution of the problem 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0021-07.png)


In this appendix we solve B.13a, B.13b to obtain P (¿; f;®; K), and then substitute this solution into B.12 to obtain the option value V (t; f; ®). This yields the option price under the SABR model, but the resulting formulas are awkward and not very useful. To cast the results in a more usable form, we re-compute the option price under the normal model 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0021-09.png)


and then equate the two prices to determine which normal volatility ¾N needs to be used to reproduce the option’s price under the SABR model. That is, we …nd the “implied normal volatility” of the option under the SABR model. By doing a second comparison between option prices under the log normal model 

- (B.14b) dF<sup>^</sup> = ¾BF dW<sup>^</sup> 

and the normal model, we then convert the implied normal volatility to the usual implied log-normal (BlackScholes) volatility. That is, we quote the option price predicted by the SABR model in terms of the option’s implied volatility. 

B.1. Singular perturbation expansion. Using a straightforward perturbation expansion would yield a Gaussian density to leading order, 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0021-14.png)


Since the “+ ¢ ¢ ¢ ” involves powers of (f ¡ K )="®C (K), this expansion would become inaccurate as soon as (f ¡ K )C<sup>0</sup> (K)=C (K) becomes a signi…cant fraction of 1; i.e., as soon as C(f ) and C (K) are signi…cantly di¤erent. Stated di¤erently, small changes in the exponent cause much greater changes in the probability density. A better approach is to re-cast the series as 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0021-16.png)

<!-- page: 22 -->

and expand the exponent, since one expects that only small changes to the exponent will be needed to e¤ect the much larger changes in the density. This expansion also describes the basic physics better — P is essentially a Gaussian probability density which tails o¤ faster or slower depending on whether the “di¤usion coe¢cient” C(f ) decreases or increases. 

We can re…ne this approach by noting that the exponent is the integral 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0022-02.png)


Suppose we de…ne the new variable 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0022-04.png)


so that the solution P is essentially e<sup>¡z2=2</sup> . To leading order, the density is Gaussian in the variable z, which is determined by how “easy” or “hard” it is to di¤use from K to f , which closely matches the underlying physics. The fact that the Gaussian changes by orders of magnitude as z<sup>2</sup> increases should be largely irrelevent to the quality of the expansion. This approach is directly related to the geometric optics technique that is so successful in wave propagation and quantum electronics [27], [22]. To be more speci…c, we shall use the near identity transform method to carry out the geometric optics expansion. This method, pioneered in [28], transforms the problem order-by-order into a simple canonical problem, which can then be solved trivially. Here we obtain the solution only through O("<sup>2</sup> ), truncating all higher order terms. 

Let us change variables from f to 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0022-07.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0022-08.png)


and to avoid confusion, we de…ne 

(B.18b) B("®z) = C(f): 

Then 

(B.19a) 

and 

(B.19b) 

(B.19c) 

(B.19d) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0022-17.png)


Also, 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0022-19.png)

<!-- page: 23 -->

Therefore, B.12 through B.13b become 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0023-01.png)


where P (¿; z; ®) is the solution of 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0023-03.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0023-04.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0023-05.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0023-06.png)


Accordingly, let us de…ne P<sup>^</sup> (¿; z;®) by 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0023-08.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0023-09.png)


In terms of P<sup>^</sup> , we obtain 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0023-11.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0023-12.png)


where P<sup>^</sup> (¿; z; ®) is the solution of 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0023-14.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0023-15.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0023-16.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0023-17.png)


To leading order P<sup>^</sup> is the solution of the standard di¤usion problem P<sup>^</sup> ¿ =<sup><u>1</u></sup> 2<sup>P^zzwithP^= ±(z)at¿= 0.</sup> So it is a Gaussian to leading order. The next stage is to transform the problem to the standard di¤usion problem through O("), and then through O("<sup>2</sup> ), . . . . This is the near identify transform method which has proven so powerful in near-Hamiltonian systems [28]. 

Note that the variable ® does not enter the problem for P<sup>^</sup> until O("), so 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0023-20.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0023-21.png)


Consequently, the derivatives P<sup>^</sup> z® , P<sup>^</sup> ®® , and P<sup>^</sup> ® are all O("). Recall that we are only solving for P<sup>^</sup> through O("<sup>2</sup> ). So, through this order, we can re-write our problem as 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0023-23.png)


Let us now eliminate the<sup>~~1~~</sup> 2<sup>"a(B0=B) ^Pzterm.De…neH(¿ ;z; ®)by</sup> 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0023-25.png)

<!-- page: 24 -->

Then 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0024-01.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0024-02.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0024-03.png)


The option price now becomes 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0024-05.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0024-06.png)


where 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0024-08.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0024-09.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0024-10.png)


Equations B.30a, B.30b are independent of ® to leading order, and at O(") they depend on ® only through<sup>0</sup> the last term "½º®(Hz® +<sup>~~1~~</sup> 2<sup>"®</sup><sup>~~B~~</sup> B<sup>H®).Asabove,sinceB.30aisindependentof®toleadingorder,wecan</sup> conclude that the ® derivatives H® and Hz® are no larger than O("), and so the last term is actually no larger than O("<sup>2</sup> ). Therefore H is independent of ® until O("<sup>2</sup> ) and the ® derivatives are actually no larger than O("<sup>2</sup> ). Thus, the last term is actually only O("<sup>3</sup> ), and can be neglected since we are only working through O("<sup>2</sup> ). So, 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0024-12.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0024-13.png)


There are no longer any ® derivatives, so we can now treat ® as a parameter instead of as an independent variable. That is, we have succeeded in e¤ectively reducing the problem to one dimension. 

Let us now remove the Hz term through O("<sup>2</sup> ). To leading order, B<sup>0</sup> ("®z)=B("®z) and B<sup>00</sup> ("®z)=B("®z) are constant. We can replace these ratios by 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0024-16.png)


commiting only an O(") error, where the constant z0 will be chosen later. We now de…ne H<sup>^</sup> by 

(B.33) H = e<sup>"2½º®b1z 2=4</sup> H:<sup>^</sup> 

Then our option price becomes 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0024-20.png)

<!-- page: 25 -->

where H<sup>^</sup> is the solution of 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0025-01.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0025-02.png)


We’ve almost beaten the equation into shape. We now de…ne 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0025-04.png)


which can be written implicitly as 

(B.36b) "ºz = sinh "ºx ¡ ½(cosh "ºx ¡ 1): 

In terms of x, our problem is 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0025-08.png)


with 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0025-10.png)


Here 

(B.39) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0025-13.png)


The …nal step is to de…ne Q by 

^ (B.40) H = I<sup>1=2</sup> ("ºz(x))Q =<sup>¡</sup> 1 ¡ 2"½ºz + "<sup>2</sup> º<sup>2</sup> z<sup>2¢1=4</sup> Q: 

Then 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0025-17.png)


and so 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0025-19.png)


where Q is the solution of 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0025-21.png)


for ¿ > 0, with 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0025-23.png)

<!-- page: 26 -->

As above, we can replace I("ºz); I<sup>0</sup> ("ºz); I<sup>00</sup> ("ºz) by the constants I("ºz0); I<sup>0</sup> ("ºz0); I<sup>00</sup> ("ºz0), and commit only O(") errors. De…ne the constant · by 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0026-01.png)


where z 0 will be chosen later. Then through O("<sup>2</sup> ), we can simplify our equation to 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0026-03.png)


The solution of B.45a, B.45b is clearly 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0026-05.png)


through O("<sup>2</sup> ). This solution yields the option price 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0026-07.png)


Observe that this can be written as 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0026-09.png)


Moreover, quite amazingly, 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0026-11.png)


through O("<sup>2</sup> ). This can be shown by expanding "<sup>2</sup> µ through O("<sup>2</sup> ), and noting that "<sup>2</sup> µ=x<sup>2</sup> matches ·=3. Therefore our option price is 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0026-13.png)


and changing integration variables to 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0026-15.png)


reduces this to 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0026-17.png)

<!-- page: 27 -->

That is, the value of a European call option is given by 

(B.52a) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0027-02.png)


with 

(B.52b) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0027-05.png)


through O("<sup>2</sup> ). 

B.2. Equivalent normal volatility. Equations B.52a and B.52a are a formula for the dollar price of the call option under the SABR model. The utility and beauty of this formula is not overwhelmingly apparent. To obtain a useful formula, we convert this dollar price into the equivalent implied volatilities. We …rst obtain the implied normal volatility, and then the standard log normal (Black) volatility. 

Suppose we repeated the above analysis for the ordinary normal model 

(B.53a) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0027-10.png)


where the normal volatily ¾ N is constant, not stochastic. (This model is also called the absolute or Gaussian model). We would …nd that the option value for the normal model is exactly 

(B.53b) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0027-13.png)


This can be seen by setting C(f) to 1, setting "® to ¾ N and setting º to 0 in B.52a, B.52b. Working out this integral then yields the exact European option price 

(B.54a) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0027-16.png)


for the normal model, where N is the normal distribution and G is the Gaussian density 

(B.54b) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0027-19.png)


From B.53b it is clear that the option price under the normal model matches the option price under the SABR model B.52a, B.52a if and only if we choose the normal volatility ¾N to be 

(B.55) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0027-22.png)


Taking the square root now shows the option’s implied normal (absolute) volatility is given by 

(B.56) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0027-25.png)


through O("<sup>2</sup> ). 

Before continuing to the implied log normal volatility, let us seek the simplest possible way to re-write this answer which is correct through O("<sup>2</sup> ). Since x = z[1 + O(")], we can re-write the answer as 

(B.57a) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0027-29.png)

<!-- page: 28 -->

where 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0028-01.png)


This factor represents the average di¢culty in di¤using from today’s forward f to the strike K, and would be present even if the volatility were not stochastic. 

The next factor is 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0028-04.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0028-05.png)


where 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0028-07.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0028-08.png)


Here fav =<sup>p</sup> fK is the geometric average of f and K . (The arithmetic average could have been used equally well at this order of accuracy). This factor represents the main e¤ect of the stochastic volatility. 

The coe¢cients Á1, Á2, and Á3 provide relatively minor corrections. Through O("<sup>2</sup> ) these corrections 

are 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0028-12.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0028-13.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0028-14.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0028-15.png)


where 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0028-17.png)


Let us brie‡y summarize before continuing. Under the normal model, the value of a European call option with strike K and exercise date ¿ ex is given by B.54a, B.54b. For the SABR model, 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0028-19.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0028-20.png)


the value of the call option is given by the same formula, at least through O("<sup>2</sup> ), provided we use the implied normal volatility 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0028-22.png)

<!-- page: 29 -->

Here 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0029-01.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0029-02.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0029-03.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0029-04.png)


The …rst two factors provide the dominant behavior, with the remaining factor 1+[¢ ¢ ¢ ]"<sup>2</sup> ¿ ex usually provideing corrections of around 1% or so. 

One can repeat the analysis for a European put option, or simply use call/put parity. This shows that the value of the put option under the SABR model is 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0029-07.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0029-08.png)


where the implied normal volatility ¾N is given by the same formulas B.59a - B.59c as the call. 

We can revert to the original units by replacing "® ¡! ®, "º ¡! º everywhere in the above formulas; this is equivalent to setting " to 1 everywhere. 

B.3. Equivalent Black vol. With the exception of JPY traders, most traders prefer to quote prices in terms of Black (log normal) volatilities, rather than normal volatilities. To derive the implied Black volatility, consider Black’s model 

- (B.61) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0029-13.png)


where we have written the volatility as "¾B to stay consistent with the preceding analysis. For Black’s model, the value of a European call with strike K and exercise date ¿ ex is 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0029-15.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0029-16.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0029-17.png)


with 

- (B.62c) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0029-20.png)


where we are omitting the overall factor D(tset) as before. 

We can obtain the implied normal volatility for Black’s model by repeating the preceding analysis for the SABR model with C(f) = f and º = 0. Setting C (f ) = f and º = 0 in B.59a -B.59c shows that the normal volatility is 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0029-23.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0029-24.png)


through O("<sup>2</sup> ). Indeed, in [14] it is shown that the implied normal volatility for Black’s model is 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0029-26.png)

<!-- page: 30 -->

through O("<sup>4</sup> ). We can …nd the implied Black vol for the SABR model by setting ¾N obtained from Black’s model in equation B.63 equal to ¾N obtained from the SABR model in B.59a - B.59c. Through O("<sup>2</sup> ) this yields 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0030-01.png)


This is the main result of this article. As before, the implied log normal volatility for puts is the same as for calls, and this formula can be re-cast in terms of the original variables by simpley setting " to 1: 

B.4. Stochastic ¯ model. As originally stated, the SABR model consists of the special case C (f ) = 

f<sup>¯</sup> : 

(B.66a) (B.66b) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0030-06.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0030-07.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0030-08.png)


Making this substitution in ?? - ?? shows that the implied normal volatility for this model is 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0030-10.png)


through O("<sup>2</sup> ), where fav =<sup>p</sup> fK as before and 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0030-12.png)


We can simplify this formula by expanding 

(B.68a) f ¡ K = ~~p~~ fK log f=K<sup>©</sup> 1 + 241<sup>log2 f=K+</sup> 19201<sup>log4 f=K+ ¢ ¢ ¢;</sup> (B.68b) f<sup>1¡¯</sup> ¡ K<sup>1¡¯</sup> = (1 ¡ ¯)(fK )<sup>(1¡¯)=2</sup> log f=K n1 +<sup><u>(1¡</u></sup> 24<sup><u>¯)2</u></sup> log<sup>2</sup> f=K +<sup><u>(1</u></sup> 1920<sup>¡</sup><sup><u>¯)4</u>log4 f=K+ ¢¢ ¢</sup> 

and neglecting terms higher than fourth order. This expansion reduces the implied normal volatility to 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0030-16.png)


where 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0030-18.png)

<!-- page: 31 -->

This is the formula we use in pricing European calls and puts. 

To obtain the implied Black volatility, we equate the implied normal volatility ¾N (K ) for the SABR model obtained in B.69a - B.69b to the implied normal volatility for Black’s model obtained in B.63. This shows that the implied Black volatility for the SABR model is 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0031-02.png)


through O("<sup>2</sup> ), where ³ and x^(³) are given by B.69b as before. Apart from setting " to 1 to recover the original units, this is the formula quoted in section 2, and …tted to the market in section 3. 

B.5. Special cases. Two special cases are worthy of special treatment: the stochastic normal model (¯ = 0) and the stochastic log normal model (¯ = 1). Both these models are simple enough that the expansion can be continued through O("<sup>4</sup> ). For the stochastic normal model (¯ = 0) the implied volatilities of European calls and puts are 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0031-05.png)


through O("<sup>4</sup> ), where 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0031-07.png)


For the stochastic log normal model (¯ = 1) the implied volatilities are 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0031-09.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0031-10.png)


through O("<sup>4</sup> ), where 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0031-12.png)


## Appendix C. Analysis of the dynamic SABR model. 

We use e¤ective medium theory [23] to extend the preceding analysis to the dynamic SABR model. As before, we take the volatility °(t)^® and “volvol” º(t) to be small, writng °(t) ¡! "°(t); and º (t) ¡! "º(t), and analyze 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0031-15.png)


(C.1b)

<!-- page: 32 -->

with 

(C.1c) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0032-02.png)


in the limit " ¿ 1. We obtain the prices of European options, and from these prices we obtain the implied volatity of these options. After obtaining the results, we replace "°(t) ¡! °(t) and "º(t) ¡! º (t) to get the answer in terms of the original variables. 

^ Suppose the economy is in state F<sup>^</sup> (t) = f; ®(t) = ® at date t. Let V (t; f;®) be the value of, say, a European call option with strike K and exercise date tex. As before, de…ne the transition density p(t; f; ®; T; F; A) by 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0032-05.png)


and de…ne 

(C.2b) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0032-08.png)


Repeating the analysis in Appendix B through equation B.10a, B.10b now shows that the option price is given by 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0032-10.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0032-11.png)


where P (t; f; ®; T; K) is the solution of the backwards problem 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0032-13.png)


We eliminate °(t) by de…ning the new time variable 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0032-15.png)


Then the option price becomes 

(C.6) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0032-18.png)


where P (s; f; ®; s<sup>0</sup> ;K ) solves the forward problem 

(C.7a) 

(C.7b) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0032-22.png)


Here 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0032-24.png)


We solve this problem by using an e¤ective media strategy [23]. In this strategy our objective is to determine which constant values ¹´ and À¹ yield the same option price as the the time dependent coe¢cients ´(s) and À(s). If we could …nd these constant values, this would reduce the problem to the non-dynamic SABR model solved in Appendix B.

<!-- page: 33 -->

We carry out this strategy by applying the same series of time-independent transformations that was used to solve the non-dynamic SABR model in Appendix B, de…ning the transformations in terms of the ¹ ¹ (as yet unknown) constants ´ and À. The resulting problem is relatively complex, more complex than the canonical problem obtained in Appedix B. We use a regular perturbation expansion to solve this problem, and once we have solved this problem, we choose ¹´ and À¹ so that all terms arising from the time dependence of ´(t) and À(t) cancel out. As we shall see, this simultaneously determines the “e¤ective” parameters and allows us to use the analysis in Appendix B to obtain the implied volatility of the option. 

C.1. Transformation. As in Appendix B, we change independent variables to 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0033-02.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0033-03.png)


and de…ne 

(C.9b) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0033-06.png)


We then change dependent variables from P to P<sup>^</sup> , and then to H: 

- (C.9c) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0033-09.png)


- (C.9d) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0033-11.png)


Following the reasoning in Appendix B, we obtain 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0033-13.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0033-14.png)


where H (s; z;®; s<sup>0</sup> ) is the solution of 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0033-16.png)


for s < s<sup>0</sup> , and 

- (C.11b) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0033-19.png)


through O("<sup>2</sup> ). See B.29, B.31a, and B.31b. There are no ® derivatives in equations C.11a, C.11b, so we can treat ® as a parameter instead of a variable. Through O("<sup>2</sup> ) we can also treat B<sup>0</sup> =B and B<sup>00</sup> =B as constants: 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0033-21.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0033-22.png)


where z 0 will be chosen later. Thus we must solve 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0033-24.png)


- (C.13b) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0033-26.png)

<!-- page: 34 -->

At this point we would like to use a time-independent transformation to remove the zHz term from equation C.13a. It is not possible to cancel this term exactly, since the coe¢cient ´(s) is time dependent. Instead we use the transformation 

## (C.14) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0034-02.png)


where the constant ± will be chosen later. This transformation yields 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0034-04.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0034-05.png)


(C.15b) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0034-07.png)


through O("<sup>2</sup> ). Later the constant ± will be selected so that the change in the option price caused by the term ~~1~~ 2<sup>"2®b1´zH^zisexactlyo¤setbythechangeinpricedueto</sup> ~~1~~ 2<sup>"2®b1±z</sup> H<sup>^</sup> z term. In this way to the transformation cancels out the zHz term “on average.” 

In a similar vein we de…ne 

(C.16a) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0034-11.png)


and 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0034-13.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0034-14.png)


where the constants ¹´ and À¹ will be chosen later. This yields 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0034-16.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0034-17.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0034-18.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0034-19.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0034-20.png)


through O("<sup>2</sup> ). Here we used z = x + ¢ ¢ ¢ and zH<sup>^</sup> z = xH<sup>^</sup> x + ¢¢ ¢ to leading order to simplify the results. Finally, we de…ne 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0034-22.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0034-23.png)


Then the price of our call option is 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0034-25.png)


where Q(s; x; s<sup>0</sup> ) is the solution of 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0034-27.png)

<!-- page: 35 -->

![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0035-00.png)


(C.20b) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0035-02.png)


Using 

(C.21) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0035-05.png)


we can simplify this to 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0035-07.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0035-08.png)


(C.22b) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0035-10.png)


¹ ¹ ¹ through O("<sup>2</sup> ). Note that I; I<sup>0</sup> ; and I<sup>00</sup> can be replaced by the constants I("Àz 0); I<sup>0</sup> ("Àz0), and I<sup>00</sup> ("Àz0) through O("<sup>2</sup> ). 

C.2. Perturbation expansion. Suppose we were to expand Q(s; x; s<sup>0</sup> ) as a power series in " : 

(C.23) Q(s; x; s<sup>0</sup> ) = Q<sup>(0)</sup> (s; x; s<sup>0</sup> ) + "Q<sup>(1)</sup> (s; x; s<sup>0</sup> ) + "<sup>2</sup> Q<sup>(2)</sup> (s; x; s<sup>0</sup> ) + ¢ ¢ ¢ : 

Substituting this expansion into C.22a, C.22b yields the following hierarchy of equations. To leading order we have 

(C.24a) 

(C.24b) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0035-17.png)


At O(") we have 

(C.25a) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0035-20.png)


- (C.25b) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0035-22.png)


At O("<sup>2</sup> ) we can break the solution into 

(C.26) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0035-25.png)


where 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0035-27.png)


(C.27b) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0035-29.png)


where 

(C.28a) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0035-32.png)

<!-- page: 36 -->

![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0036-00.png)


and where 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0036-02.png)


(C.29b) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0036-04.png)


Once we have solved these equations, then the option price is then given by 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0036-06.png)


The terms Q<sup>(1)</sup> ; Q<sup>(2a)</sup> ; and Q<sup>(2b)</sup> arise from the time-dependence of the coe¢cients ´(s) and À(s). Indeed, if ´(s) and À(s) were constant in time, we would have Q<sup>(1)</sup> ´ Q<sup>(2a)</sup> ´ Q<sup>(2b)</sup> ´ 0, and the solution would be just Q<sup>(s)</sup> ´ Q<sup>(0)</sup> + "<sup>2</sup> Q<sup>(2s)</sup> . Therefore, we will …rst solve for Q<sup>(1)</sup> ; Q<sup>(2a)</sup> ; and Q<sup>(2b)</sup> , and then try to choose ¹ ¹ the constants ±, ´; and À so that the last three integrals are zero for all x. In this case, the option price woud be given by 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0036-08.png)


and, through O("<sup>2</sup> ), Q<sup>(s)</sup> would be the solution of the static problem 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0036-10.png)


(C.31c) 

This is exactly the time-independent problem solved in Appendix B. See equations B.42, B.43a, and B.43b. So if we can carry out this strategy, we can obtain option prices for the dynamic SABR model by reducing them to the previously-obtained prices for the static model. 

C.2.1. Leading order analysis. The solution of C.24a, C.24b is Gaussian: 

(C.32a) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0036-15.png)


where 

(C.32b) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0036-18.png)


For future reference, note that 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0036-20.png)

<!-- page: 37 -->

C.2.2. Order ". Substituting Q<sup>(0)</sup> into the equation for Q<sup>(1)</sup> and using C.33a yields 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0037-01.png)


with the “initial” condition Q<sup>(1)</sup> = 0 at s = s<sup>0</sup> . The solution is 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0037-03.png)


where 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0037-05.png)


This term contributes 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0037-07.png)


to the option price. See equations C.30a, C.30b. To eliminate this contribution, we chose ¹´ so that A(s; sex) = 0: 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0037-09.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0037-10.png)


C.2.3. The "<sup>2</sup> Q<sup>(2a)</sup> term. From equation C.28a we obtain 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0037-12.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0037-13.png)


for s < s<sup>0</sup> , with Q<sup>(2a)</sup> = 0 at s = s<sup>0</sup> . Solving then yields 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0037-15.png)


This term makes a contribution of 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0037-17.png)


to the option price, so we choose 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0037-19.png)


to eliminate this contribution.

<!-- page: 38 -->

C.2.4. The "<sup>2</sup> Q<sup>(2b)</sup> term. Substituting Q<sup>(1)</sup> and Q<sup>(0)</sup> into equation C.29a, we obtain (C.42a) Q<sup>(2</sup> s<sup>b)</sup> +<sup>~~1~~</sup> 2<sup>Q</sup> xx<sup>(2b)</sup> = (´ ¡ ¹´)AxGxxxxx + 2(´ ¡ ¹´)As<sup>0</sup> xGxxx ¡<sup>~~1~~</sup> 2<sup>·x2Gxx;</sup> for s < s<sup>0</sup> , where 

(C.42b) · = À<sup>2</sup> (s) ¡ ¹À<sup>2</sup> ¡ 3¹´[´(s) ¡ ¹´]: 

This can be re-written as 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0038-03.png)


Solving this with the initial condition Q<sup>(2b)</sup> = 0 at s = s<sup>0</sup> yields 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0038-05.png)


This can be written as 

¹ Recall that ´ was chosen above so that A(s; sex) = 0. Therefore the contribution of Q<sup>(2b)</sup> to the option price is 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0038-08.png)


where · = À<sup>2</sup> (s) ¡ ¹À<sup>2</sup> ¡ 3¹´[´(s) ¡ ¹´]. 

We can choose the remaining “e¤ective media” parameter ¹À to set either the coe¢cient of Gs(x=<sup>p</sup> s ex ¡ s) or the coe¢cient of G(x=<sup>~~p~~</sup> sex ¡ s) to zero, but cannot set both to zero to completely eliminate the contri¹ bution of the term Q<sup>(2b)</sup> . We choose À to set the coe¢cient of Gs(x=<sup>p</sup> sex ¡ s) to zero, for reasons that will become apparent in a moment: 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0038-11.png)


Then the remaining contribution to the option price is 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0038-13.png)

<!-- page: 39 -->

where 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0039-01.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0039-02.png)


Here we have used Since Rs sex (sex ¡ ~s)(´ (~s) ¡ ¹´)ds~ = 0 to simplify C.48b. 

C.3. Equivalent volatilities. Let us gather the results together. The static problem C.31b - C.31c is homogeneous in time, so its solution Q<sup>(s)</sup> depends only on the time di¤erence ¿ ¡ ¿<sup>0</sup> . The option price is thus 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0039-05.png)


where Q<sup>s</sup> (¿; x) is the solution of 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0039-07.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0039-08.png)


(C.50b) 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0039-10.png)


Here we have replaced ± with ¹´. See C.41.Since the static solution is Gaussian to leading order, Q<sup>s</sup> = G (x=<sup>p</sup> ¿ ), we can re-write the option price as 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0039-12.png)


through O("<sup>2</sup> ), where 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0039-14.png)


The partial di¤erential equation C.50a, C.50b, and option price C.51a are identical to the equations obtained in Appendix B for the original non-dynamic SABR model, provided we make the identi…cations 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0039-16.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0039-17.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0039-18.png)


See equations B.42 - B.43b. Following the reasoning in the preceding Appendix now shows that the European call price is given by the formula 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0039-20.png)


with the implied normal volatility 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0039-22.png)

<!-- page: 40 -->

where 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0040-01.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0040-02.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0040-03.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0040-04.png)


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0040-05.png)


Equivalently, the option prices are given by Black’s formula with the e¤ective Black volatility of 


![](assets/2002-hagan-et-al-managing-smile-risk.pdf-0040-07.png)


Appendix D. Analysis of other stochastic vol models. Adapt analysis to other SV models. Just quote results? 

Appendix E. Analysis of other stochastic vol models. Adapt analysis to other SV models. Just quote results? 

### REFERENCES 

[1] D. T. Breeden and R. H. Litzenberger, Prices of state-contingent claims implicit in option prices, J. Business, 51 (1994), pp. 621-651. 

> [2] Bruno Dupire, Pricing with a smile, Risk, Jan. 1994, pp. 18–20. 

> [3] Bruno Dupire, Pricing and hedging with smiles, in Mathematics of Derivative Securities, M.A. H. Dempster and S. R. Pliska, eds., Cambridge University Press, Cambridge, 1997, pp. 103–111 

> [4] E. DermaN and I. Kani, Riding on a smile, Risk, Feb. 1994, pp. 32–39. 

> [5] E. Derman and I. Kani, Stochastic implied trees: Arbitrage pricing with stochastic term and strike structure of volatility, Int J. Theor Appl Finance, 1 (1998), pp. 61–110. 

> [6] Harrison and Pliska, Martingale pricing, SIAM J. Abbrev. Correctly, 2 (1992), pp. 000–000. 

> [7] El Karoui & friends, Martingale pricing in incomplete markets, SIAM J. Abbrev. Correctly, 2 (1992), pp. 000–000. 

> [8] Oxendall, Martingale pricing in incomplete markets, SIAM J. Abbrev. Correctly, 2 (1992), pp. 000–000. 

> [9] Jamshidean, Jamshidean uses level numeraire, SIAM J. Abbrev. Correctly, 2 (1992), pp. 000–000. 

> [10] Fischer Black, Black’s model 1, SIAM J. Abbrev. Correctly, 2 (1992), pp. 000–000. 

> [11] John C. Hull, A Beginner’s Book of Option Pricing, Springer-Verlag, Berlin, New York, 1991. 

> [12] Paul X Wilmott, Another Beginner’s Book of Option Pricing, Springer-Verlag, Berlin, New York, 1991 

> [13] Patrick S. Hagan and Diana E. Woodward, Equivalent Black volatilities, App. Math. Finance, 6 (1999), pp. 147–157 

> [14] P. S. Hagan, A. Lesniewski and D. E. Woodward, Geometric optics, App. Math. Finance, 6 (1999), pp. 147–157 

> [15] Fred Wan, A Beginner’s Book of Modeling, Springer-Verlag, Berlin, New York, 1991. 

> [16] Hull and White, Stochastic vol models, App. Math. Finance, 6 (1987), pp. 147–157 

> [17] Heston, Stochactic vol models, App. Math. Finance, 6 (1999), pp. 147–157 

> [18] Someone else, Stochactic vol models, App. Math. Finance, 6 (1999), pp. 147–157 

> [19] Someone else, Stochactic vol models, App. Math. Finance, 6 (1999), pp. 147–157 

> [20] Paribas option guy, Vanna & volga, App. Math. Finance, 6 (1999), pp. 147–157 

> [21] J. D. Cole, Perturbation Theory, Springer-Verlag, Berlin, New York, 1991.

<!-- page: 41 -->

- [22] J. Kevorkian and J. D. Cole, Perturbation Theory, Springer-Verlag, Berlin, New York, 1991. 

- [23] Andrew Norris, E¤ective medium theory, SIAM J Appl Math, 6 (1999), pp. 147–157 

- [24] Math Guy A, Stochastic Processes A, Springer-Verlag, Berlin, New York, 1991 

- [25] Math Guy B, Stochastic Processes B, Springer-Verlag, Berlin, New York, 1991 

- [26] Math Guy C, Stochastic Processes C, Springer-Verlag, Berlin, New York, 1991 

- [27] G. B. Whitham, Linear and Nonlinear Waves, Springer-Verlag, Berlin, New York, 1991 

- [28] John C. Neu, Thesis, Springer-Verlag, Berlin, New York, 1991
