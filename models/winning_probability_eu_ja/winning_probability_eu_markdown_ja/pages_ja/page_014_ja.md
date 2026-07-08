# Page 014 - 日本語版

![Page 14](../assets/page_images/page_014.png)

## 日本語メモ

**該当箇所:** 3.1 Model Assumptions

モデルの主要前提。MSが観測するオークションの代表性、hit-rate曲線のシグモイド形状、タイ率、参加者行動の安定性、ロジスティック回帰の統計前提など。

## 原文OCR/Text Layer

> OCR由来のため、誤認識があります。正確な図表・数式・レイアウトは上のページ画像を確認してください。

```text
Morgan Stanley
Confidential
3. Insignificant tie rate: As per section{2.3| dealers can tie at the winning or cover prices. Tied
auctions have formed part of a bespoke trading strategy in the past. This can be revisited
in the case that the tie rate exceeds a significance threshold of 15%.
However, based on
data analysis on the product range for which the EUGV probability curve model applies, an
assumption is made that the realized tie rate at DoneTied and TiedTradedAway is insignificant.
4. Market Stability: The model assumes that the behaviour of market participants is suitably
stable between training periods such that out-of-sample model performance is itself stable.
‘The key business assumptions are supported by the following:
1. The model scope inquiry daily rate seen by MS is plotted in figure[J. The 30d moving average
hovers around 6000 RFQs across different markets, and figure
[J]shows us that more than 50%
of those originate from the Tradeweb marketplace.
From this, it can be assumed that the visibility rate can be proxied by the MS market share
from Tradeweb, who provide us with this market data. As shown in figure [6] the share is
around 50%. The MS auction participation levels can therefore be deemed substantial and
level enough to validate the first modelling assumption.
It is not possible to estimate how MS would have quoted or how the market reacted if MS had
a lower or higher visibility rate. Only periodic recalibration can control for this assumption;
it is not otherwise quantifiable.
Total inquiries per day 2024
16000
14000
12000
10000
8000
6000
4000
2000
Figure 4: Daily RFQ count that MS responded to and where outcome is known and can be used
for model training purposes (i.e. excluding CustomerRejected, CustomerTimeOut). In-comp only,
date ranging from 2024/01/01 to 2024/11/22.
129576: Winning-Probability Model
for EUGV
RFQ Pricing
Page
14
of 73
[git]
Branch: ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)
```
