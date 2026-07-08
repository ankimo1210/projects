# Page 12

![Page 12](../assets/page_images/page_012.png)

## Extracted OCR/Text Layer

```text
Morgan Stanley
Confidential
TW: TradeWeb
i) ee
BBG: Bloomberg
(686
}———>
BV: BondVision
BV
MA: MarketAxess
a
GLM: Global Limit manager
external
MDS: Market-Data Services
internal
STP: Straight-through processing
Order Router
A: indicative composite bid/ask px
(normalizes)
B: dropcopy position
Quote
GUI
Figure 3: System layout of the MS RFQ autoquoting complex. The Winning-Probability Model
resides within the Algo-Pricer box. The Quote Manager contains logic that produces the final price
that is attached to the Quote, but the GLM limits, as governed by ETRM, may restrict the price
or even the quote-message itself.
« Inquiry Manager:
Orders from the market possess state, and the state
is maintained,
on a per-order basis, by the finit
there is a dedicated Inquiry Manager instance for each RFQ marketplace.
The market-
associated Inquiry Manager forwards an inbound RFQ inquiry to both the Algo Pricer and
Quote Manager (QM) via message-path c.
state machines internal
to this component.
Moreover,
+ Algo Pricer: The Algo Pricer houses the Winning-Probability Model.
In order to assist
in model pricing, the Algo Pricer subscribes to a data-enrichment feed from message-paths
e and f, and to reference data. Market information is provided by the mid service along
message-path ¢, and the reference data that is consumed includes FID1 Tools, which is the
authoritative MS source of security definitions [6], as well as client-tier information.
+ Quote Manager: This component produces the final price returned to the market, subject
to risk controls via the global limit manager (GLM) and trader input via the eQuote GUL
The Quote Manager creates its own quote-candidate price based on a rules-based system
that includes trader input and current market prices, and then waits for the Algo Pricer
to publish its model-based candidate price.
The Quote Manager applies the market-risk
controls detailed in section [7] via GLM. Subject to risk, trader, and market conditions, the
Quote Manager returns a model price, if it lies within bounds, or a most restricted QM price:
in either event, the QM price is what is returned. The return message-path is c’ followed by
b’ and then back to TW.
Note that an RFQ may not be answered at all if doing so would result in a trade that exceeds
the risk limits.
129576: Winning-Probability Model for
EUGV
RFQ Pricing
Page 12 of 73
[git]
= Branch:
ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)

```
