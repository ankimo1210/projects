# ページ 010

![ページ 010](../assets/page_images/page-010.jpg)

## 原文OCRテキスト

```text
Morgan Stanley                                                                                   Confidential


BOBL, BUND, BUXL, OAT, BTS, BTP, all of which are liquid front bond futures. However, based
on the business request, we will add the UK long gilt front future (FLG) to the hedge instrument
space in the near future. Within UST there are 18 hedge instruments: the 2Y, 3Y, 5Y, 7Y, 10Y,
20Y, 30Y on-the-run bonds, the TU, FV, TY, UXY, US, UL front bond futures and the SHY,
IEI, IEF, TLH, TLT bond ETFs. The number and choice of the hedge instruments are business
decisions and are subject to change based on business needs.
    Back bond futures are handled by a separate instance of Opt-Var with zero lambda and zero
bucket risk limit constraint{?] It has the effect of liquidating any back future position in the
portfolio.
    To recap: the goal of the autohedger is to manage the portfolio risk - as projected to the hedge
instruments listed above - through automated hedging activities.
2.2       Portfolio Risk
At any time of the day, the e-trading book holds a set of positions of bonds and futures coming
from the trading activities with clients and other brokers. To measure the risk held in the e-trading
book, we map the positions of each security to the hedge instruments space, a.k.a. different risk
buckets. To do this, we use the pre-determined hedge ratios that input to the autohedger. We call
the ensemble of the mapped risk positions to the hedge instruments space the portfolio risk. Figure
       ‘ives an example of how we use the hedge ratios to convert the original position to the portfolio
risk in the hedge instruments space. In the example, we have a trade to buy a particular Italian
bond with a size of 100 PVO1.              After the trade is done, the position of this bond in the trading
book will increase by 100 PVO1. We then map this bond position to the hedge instrument space.
The projected risk to hedge instrument i is given by Risk; = tradeSize * HedgeRatio;. The green
box below gives the hedge ratios of this bond. With these hedge ratios, the portfolio risk increase
after this trade      is shown in the yellow box. This portfolio risk in the hedge instruments space is
what monitored and managed by the autohedger. One should also note that the original positions
of each security and the hedge ratios are the input to the autohedger but not the Opt-Var model,
while the portfolio risk in the hedge instrument space is the input of the Opt-Var model.

                                                      Hedge Ratios          Portfolio Risk
                              Trade                     SHTZ: 0.0000          SHTZ: 0.00
                             Security:                  BOBL: 0.0000          BOBL: 0.00
                          170005534141                 BAUNIDE D2SED         BUND: -28.60
                             Side: Buy                  BUXL: 0.3339          BUXL: 33.30
                                                         OAT: 0.0000           OAT: 0.00
                         Size: 100 PVO1                  BTS: 0.0000
                                                        BTP: 0.8997,



Figure 5: Illustration of how the pre-determined hedge ratios are used to project the Italian bond
position IT0005534141 to the space of bond futures.


2.3.      Inputs and        Outputs       Volume

We here describe the typical volume of the inputs and outputs of the Opt-Var model, using the
example in the US. The autohedger usually daily executes orders with a total volume of between
      See section [3] for the definition of lambda and bucket risk limit




130115: Opt-Var                                                                                Page   10 of 136

                             [git] « Branch: iropt-var@be27d1a = Release:   (2024-10-31)
```
