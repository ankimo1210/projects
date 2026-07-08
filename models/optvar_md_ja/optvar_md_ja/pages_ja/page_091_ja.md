# ページ 091

![ページ 091](../assets/page_images/page-091.jpg)

## 原文OCRテキスト

```text
Morgan Stanley                                                                                        Confidential

                       18
                  25




                      — optivar Hedger
                  00. — NoHedge
                       o           25      50       75      100      ws      150     us     200
                                                              »                               x10

Figure 74: Comparison of the portfolio variance values after hedging using Opt-Var versus no hedge
for different risk aversion \ values.

5.5.5    Trading Cost

To prove that the Opt-Var results meet the trading cost criteria (1), we look at the value of the
trading cost term Costy = C"|u|-+u' Mu in the objective function|I| We compare the value of the
trading cost term of Opt-Var proposed hedges with the trading cost of a simple hedging strategy
that hedges all the risk to zero. The comparison is already done in section          for the specific
example we tested. As shown in figure        the trading cost value for Opt-Var increases with the
increase of  but it is always smaller than the trading cost term of the simple strategy that hedges
all the risk. Figure [99] to figure [103] in section [13.3.2] in the appendix gives the same plots for all
the 100 examples.           It is shown that the trading cost term value of the Opt-Var proposed hedges are
always smaller than that of the simple hedging strategy that hedges all the risk to zero for all the
100 examples. This illustrates that the Opt-Var results satisfy the trading cost criteria (i).
    To test that the Opt-Var results satisfy the trading cost criteria (ii), we look at the trades
proposed by Opt-Var in reaction to a large position increase in a specific bucket. Specifically, we
set an initial position of a specific bucket to be 25000 PVO1 while keeping the initial position of the
rest of the buckets at 0. We conduct the test using the same production parameters as described
in section             Given this parameter setup, 25,000 PVO1 is a large position increase - well above
the hedgeable risk limit 10,000 PVO1. A simple hedging strategy that minimizes the portfolio
variance without considering the trading cost would propose hedges only in this specific bucket
where the initial position is not zero. However, the cost of a large hedge trade in one product can
be prohibitive. We demonstrate that in such cases, Opt-Var will propose hedges in different buckets
to reduce the trading costs while still achieve the same level of portfolio variance by utilizing the
correlation between different buckets.
    Figure[75]below shows the Opt-Var proposed trades in reaction to 25,000 PVO01 position increase
in Buxl bucket for different \ values, ranging from zero to 2e-4. We can see from the plot, Opt-Var
proposes to trade a big size of Buxl, especially when the ) value is big. But it also proposes to
trade some amount of BUND, OAT, and BTP contracts. Figure [76] compares the trading costs
of Opt-Var proposed trades and the cost of trading the single product that has a non-zero initial
position. The horizontal axis gives the portfolio variance after trading the hedges, and the vertical
   is gives the value of the trading cost term Cost, in the objective function as described in section
         The blue line depicts the trading cost of Opt-Var hedger, and the orange line depicts the
      ing cost of a simple strategy which only trades Buxl. According to the plot, to achieve the same

130115: Opt-Var                                                                                     Page 91 of 136
                              [git] « Branch: iropt-var@be27d1a = Release:   (2024-10-31)
```
