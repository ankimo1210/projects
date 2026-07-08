# Page 20

![Page 20](../assets/page_images/page_020.png)

## Extracted OCR/Text Layer

```text
Morgan Stanley
Confidential
presented - this will be referred to as the ‘online’ phase.
The main offline sources are listed below. These are tables stored in the MS BMET database
and queried using internal q/kdb+ code. In the below and for the remainder of the document, the
‘client tier’ refers to the internal MS classification of its clients by Sales and Trading.
+ BMET logs of input data: The calibration process uses historical inputs to the MS algo-
rithms contributing to price construction, such as RFQ data (client tier, mid price, security,
etc.), and market data (composites / mids). Inquiry states are also used - see sectio:
the definition of auction outcomes.
+ BMET logs of output data: The calibration process also uses historical outputs from
the MS algorithms contributing to price construction.
This includes information on the
price formation, such as final price returned and input configuration - eg. probability curve
calibration that was used for each RFQ.
The main online sources are listed below:
+ Marketplace RFQ Engines: The model uses inquiry data from various markets, primarily
TW, BBG, BV and MA.
+ Marketplace Indicative Feeds: Composites, indicative market feeds are published by the
respective marketplaces.
«
FID1 Reference Data:
In particular, client tier and product definitions are consumed by
the Algo Pricer and passed to the model.
«
Filter: The Filter subscription layer provides indicative and Morgan Stanley (MS) mids as
well as other quantitative features of EUGV and UKGV inquiries.
3.3.2
Observable Inputs
From the data sources above, the following is a list of example observable inputs:
«
Security: [marketplace] the product definition from the marketplace.
+ RFQ features: [marketplace] eg. the quantity that the customer is looking to deal for, the
side of the request (buy or sell), the number of dealers in competition.
+ Market Composites: [marketplace] the prevailing composite indicative bid, ask and mid
prices.
3.3.3
Model Features
The model features are chosen based on expert judgement and statistical significance for the data
segmentation in question. They are a combination of both RFQ and market data (see section [f] for
additional detail). Some desks may make a business decision to zero out some features where it is
appropriate for their current strategy. Historically, and for the purpose of this document we have
defined a set of features as the following:
129576: Winning-Probability Model for
EUGV RFQ Pricing
Page
20 of 73
[git]
= Branch:
ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)

```
