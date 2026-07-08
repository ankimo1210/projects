# ページ 009

![ページ 009](../assets/page_images/page-009.jpg)

## 原文OCRテキスト

```text
Morgan Stanley                                                                                        Confidential


We have theoretically demonstrated the stability properties of the optimizer, which is confirmed
numerically. Superior performance, in terms of hedging cost required to achieve a given level of
risk reduction, is shown relative to alternative approaches.

2     Business and Algo Description
    The Opt-Var model detailed in this document is the key component of Morgan Stanley’s au-
tohedger algo for the electronic market making business in EU and US government bond markets
(EGB and UST markets). The autohedger is an automated hedging algorithm designed to man-
age the risks in these trading books. Despite the fact that different government bonds and hedge
instruments are traded in the respective markets, the automated hedging is done according to the
same principles in both regions.


                                 inventory
              4 client
                  trades   by)   bonds
                                                    cted
                                             2P ventory,                   3 trades
                                                            Auto-Hedger                     market
                                 hedges
                                   y.
                                                           4 hedge bonds



Figure 4: A schematic diagram of the hedging process. In Step 1, new inventory comes into the
bond book. In Step 2, the illiquid inventory is projected onto the target hedge position. Finally, in
Step 3 trades are placed in the market so as to achieve the optimized version of the target hedge.
    In this section, we first give an overview of the autohedger. Then, we explain the concept of
portfolio risk, which is the risk that the autohedger is managing. Following that, we introduce the
three key functional components in the autohedger and how they interact with each other: the risk
calculator, the hedge calculator, and the hedge executor.
2.1    Autohedger           Overview
The autohedger is an automated algorithm that operates in the following context: during market
hours, the EGB and UST e-trading desks buy and sell securities with clients through a Request for
Quote (RFQ) protocol in government bond marketplaces such as Tradeweb and Bloomberg. These
desks also trade directly with other brokers via B2B markets such as MTS and BrokerTec. When
those trading activities result in "Done" trades (that is, when trades are actually executed), the risk
is added to the e-trading books portfolio, and this portfolio risk needs to be managed effectively
through appropriate hedging activities.
    Hedging is a risk management strategy to offset potential losses in the portfolio by taking an
opposite position in a related asset. At Morgan Stanley’s government bond e-trading desks, we
use the on-the-run bonds and bond futures as the hedging instruments in EU. Specifically, at
the moment this document is written, there are seven hedge instruments in the EU sphere: SHTZ,

130115: Opt-Var                                                                                      Page 9 of 136

                            [git] « Branch: iropt-var@be27d1a = Release:     (2024-10-31)
```
