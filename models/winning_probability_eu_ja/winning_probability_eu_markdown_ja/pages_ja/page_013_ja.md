# Page 013 - 日本語版

![Page 13](../assets/page_images/page_013.png)

## 日本語メモ

**該当箇所:** 2.5-2.7 MS Autoquoting Complex / Policy

MSのRFQ自動クォート構成、Order Router、Inquiry Manager、Algo Pricer、Quote Manager、GLM、Mid Service等の役割を図3で説明する。

## 原文OCR/Text Layer

> OCR由来のため、誤認識があります。正確な図表・数式・レイアウトは上のページ画像を確認してください。

```text
Morgan Stanley
Confidential
+ GLM: The global limit manager feeds the ETRM limits to the Quote Manager. These limits
are detailed in section
[Z| and include risk, price, and operational parameters.
+ Reference prices: Risk limits prevent a quote from being off-market, and this is accom-
plished by subscribing to real-time bid and offer pricing feeds from the market.
+ Mid Service: The mid service consumes market information and uses the available data
to provide a mid quote to be used in downstream components, including the algo pricer via
message-path e. The pricer bases the construction of the quote on the mid returned by the
service.
« Risk HQ: Risk HQ consumes information on trading positions and provides a cost associated
to risk of trading a product to downstream components, including the algo pricer via message-
path f, The pricer bases part of the construction of the quote on the cost returned by the
component, where deemed applicable by the business.
* eQuote GUI: The trading desk controls pricing and risk acceptance through the eQuote
GUI. Traders can adjust pricing parameters on the GUI, within limits, and can handle trades
that go manual.
« BMET database:
All phases of the autoquoting cycle are recorded to the MS-internal
Business Metrics (BMET) database [5].
2.6
Summary
The sections above give an account of the characteristics of the request-for-quotation markets for
EUGV and UKGV bonds, and the creation of a quantitative model intended to autoquote RFQ
inquiries must take these characteristics into account.
2.7
Regulatory and Policy Requirements
The algo model covered in this document was developed in adherence to all aspects of the US Federal
Reserve's “Supervisory Guidance on Model Risk Management (SR 11-7)” [IJ and the European
Commission’s “MiFID II Regulatory Technical Standards 6 (RTS-6)” [5]. Within Morgan Stanley,
the model was developed in adherence to the “Global Model Risk Management Policy”
[3] and
its supplement, “Electronic Trading Algorithm Models: Supplement to the Global Model Risk
Management Policy” [7].
3
Model Description
3.1
Model Assumptions
The model described in this document assumes the following from a business perspective:
1. Visibility: As per sectior
the model can only be trained on data that the trading desk
collects.
Therefore, there is a model assumption that the auctions that are observed are
representative of the universe of all relevant auctions.
2. Parametric form: As per section [2.4] a probability curve is expected to resemble a sigmoid
function. Based on data analysis, this model makes the assumption that a parametric sigmoid
curve can fit a historically-observed probability curve with bound error.
129576: Winning-Probability Model for
EUGV RFQ Pricing
Page 13 of 73
[git]
= Branch:
ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)
```
