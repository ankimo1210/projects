# ページ 089

![ページ 089](../assets/page_images/page-089.jpg)

## 原文OCRテキスト

```text
Morgan Stanley                                                                                Confidential


    The same tests are applied to all the 100 examples we introduced in section            The plots
of the objective function value F, after hedging are presented in section [I3.2} in Figure [89] to [93]
‘As shown in the plots, the Opt-Var hedging strategy always reaches to a smaller objective function
value for different A values for all the 100 examples.
5.5     Outcome         Analysis and Backtesting
     In this section we analyse the Opt-Var model results and prove that the outcome satisfies what
we expect from the Opt-Var model. As described in sectior           the goal of the hedge calculator
is to propose hedge trades to control the risks to be within the risk limits and balance the trade-
off between portfolio variance, trading costs and alpha capturing. Therefore, the outcome of the
Opt-Var model should satisfy the below criteria:
5.5.1     Test Criteria

 Risk Limits

         (i) The net portfolio risk after hedging should be within the hedgeable risk limit.
         (ii) The risk in each bucket after hedging should be within the bucket risk limit.

 Trade Size Limit

         (i) The trade size for each proposed hedge should be within the trade size limit for the
             specific bucket.
 Portfolio Variance

         (i) The portfolio variance becomes smaller after hedging with Opt-Var, when A is not set
             to zero.

 Trading Cost

          (i) The cost to trade the hedges proposed by Opt-Var is smaller than hedging everything
              to zero risk.
         (ii) When we need to considerably reduce the risk, the hedges proposed by Opt-Var spread
              out to different buckets instead of only in one bucket. This way, it helps to reduce the
              total trading cost while reaching the same portfolio variance target.
      We conduct the tests using EU data. The parameters used are the same as section |5.

5.5.2     Risk Limits

To test this criteria, we check that the net portfolio risk after hedging is below the hedgeable risk
limit and the risk in each bucket is below the specific bucket risk limit for all the 100 examples we
test. The results are shown in table B0|below. The net portfolio risk and bucket risks are all below
the specified risk limits for all the 100 examples. This proves that the risk limits test criteria is
satisfied.




130115: Opt-Var                                                                          Page 89 of 136

                          [git] « Branch: iropt-var@be27d1a = Release:   (2024-10-31)
```
