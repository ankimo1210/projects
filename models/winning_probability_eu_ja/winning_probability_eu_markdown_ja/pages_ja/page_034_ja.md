# Page 034 - 日本語版

![Page 34](../assets/page_images/page_034.png)

## 日本語メモ

**該当箇所:** 5.1 Model Diagnostic Testing

係数の安定性・有意性、モデル予測可能性、バックテスト期間でのreliability plot等を用いた診断テスト。

## 原文OCR/Text Layer

> OCR由来のため、誤認識があります。正確な図表・数式・レイアウトは上のページ画像を確認してください。

```text
Morgan Stanley
Confidential
‘Sep-Oct 2024
=
‘Oct-Nov 2024
¢
Figure 17: Model reliability over backtest timeframe. From left to right, monthly out-of-sample
results in the range September 2024 to November 2024. The realized and predicted hit rates are
well correlated during each test, showing the consistency of the model performance and its accuracy
over time.
In these plots, the dataset is divided into predicted probability buckets, for which realized hit
rate and predicted hit rate are evaluated as follows:
N
realizedH
it Rate = xu ==1)
(14)
i=1
1
N
predictedH
it Rate = NW Yi)
(15)
i=l
where N is the number of i elements in the dataset. The red line represents the ‘no resolution
threshold’, and the purple, the ‘no skill threshold’ - ie. poor resolution. The black dotted line
represents perfect reliability - ie. a one-to-one relationship between prediction and production.
‘The distribution of mean predicted probability is drawn at the bottom of each reliability plot.
This shows the number of inquiries per probability bucket, which is deemed significant from 500
by the business - deviations between true and predicted probability are only investigated if the
underlying number of observations is above this threshold.
The distribution is also consistent
through time, with the bulk of the RFQs placed in lower probability bins - ie. to be quoted with
lower margins for a higher chance of winning the auction. This is potentially indicative of the
aggressiveness of the model, which can be tuned in accordance with the busin:
A relatively strong linear relationship between realized and predicted hit rate is maintained
throughout the backtest where RFQ buckets are significant (i.e. higher than 500 data points).
This serves to illustrate the consistency of the model performance as well as its accuracy.
‘Accuracy also seems to increase somewhat with time - this could be attributed to a change in
underlying dataset mirroring a change in market conditions from previous year (2023) to current
year (2024). In this case the business may decide to action a lookback reduction and recalibration
to only account for more current underlying data (e.g. in this case, calibrating the model solely on
available 2024 auction data).
Additional quantitative measures on model accuracy are provided in section
5.5
129576: Winning-Probability Model for
EUGV RFQ Pricing
Page 34 of 73
[git]
Branch:
ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)
```
