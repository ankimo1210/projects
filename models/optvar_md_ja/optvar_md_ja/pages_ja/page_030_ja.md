# ページ 030

![ページ 030](../assets/page_images/page-030.jpg)

## 原文OCRテキスト

```text
Morgan Stanley                                                                                Confidential


of the hedges and decompose the total risk into those spread pairs - we call this risk decomposition.
The specific spreads are chosen by the bookrunners. The moment this document is written, we are
using the liquid German, French and Italian futures as the hedge instruments, and we consider risk
of the spreads BOBL vs. BUND, BUXL vs. BUND, OAT vs. BUND, BTP vs. BUND, BTS vs.
SHTZ, and outright risk of BUND, SHTZ.
     ‘The holding times of the spreads and outright risks can be calculated the same way as described
above, and we define the corresponding risk decomposition holding time scaler K = (Ki), where
i=1,...,d, j =1,...,d' are the indices of the risk decompositions and d’ is the number of the
risk decompositions (the order of the risk decompositions here is: Outright SHTZ, BOBL-BUND,
Outright BUND, BUXL-BUND, OAT-BUND, BTS-SHTZ, BTP-BUND, and d’ = 7). Now, to
scale the covariance matrix by the risk decomposition holding time matrix K, we observe that the
original space of instruments is mapped to the decomposition space via d, = Pp, where P is the
(invertible) linear map that satisfies
  P :(Dshtz+ Phobl, Pounds Pouzl; Poat; Pits, Potp)
         + (Pshtzs Poobl — Pound Pounds Pouzt ~ Pound; Poat ~ Pound» Pies ~ Pshtz> Potp ~ Pound) | = dr-
     We then have that the decomposition covariance matrix is given by Ng, = PEP, and then
(just as above) the scaled version is given by 54, = Na, 0K. Finally, to recover the induced scaled
covariance matrix in the original outright futures space, we transform the scaled risk decomposition
covariance matrix via © = P~!¥q,(P~')'; it is this matrix ¥ that is used in the Opt-Var objective.

3.5.2    Linear and Quadratic Costs

In this section, we describe the estimation approach for the linear cost parameter C’ and quadratic
cost parameter M in the objective function (I).

EU

     In EU, we observe a linear relationship between the unit cost to buy or sell the hedge instruments
and the trade size.
     We use the volume weighted average bid-offer spread (aka VWAP cost) in basis points bp to
trade a fixed PVO1 as the unit cost. To analyse the relationship between the unit cost and trade
size, we can plot the median unit cost for different trade sizes over a certain lookback period.
     The moment this document is written, we are using seven futures as the hedge instruments in
EU. The plots in Figure [I5] gives the median VWAP cost (in bp) for a given trade size (in PVO1)
for each of these hedge instruments, and these plots are obtained using the data from 2023-03-01
to 2023-05-31. The same plot for FLG future is shown in Figure [16] obtained using data from
2024-02-01 to 2024-02-29. The horizontal axis gives the trade size in PVO1, and the vertical axis
shows the VWAP cost in bp. Looking at the shape of the scatter plots, we find a linear relationship
between the VWAP cost and the trade size, and the relationship can be expressed via the following
linear regression equation for each future i:

                                     VwapCost = cj + mj * TradeSize,                                     (11)
where TradeSize is the trade size in PVO1.




130115: Opt-Var                                                                             Page   30 of 136

                        [git] « Branch: iropt-var@be27d1a = Release:   (2024-10-31)
```
