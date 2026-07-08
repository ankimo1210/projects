# Page 052 - 日本語版

![Page 52](../assets/page_images/page_052.png)

## 日本語メモ

**該当箇所:** 5.3 Sensitivity Analysis / 5.4 Benchmarking

market spread captured、dealer count、life remaining、duration/PV01、notional等への感応度と、外部・内部ベンチマークとの比較。

## 原文OCR/Text Layer

> OCR由来のため、誤認識があります。正確な図表・数式・レイアウトは上のページ画像を確認してください。

```text
Morgan Stanley
Confidential
Probability curves for various notionals and dealer counts
1.0000
aed
‘0-2
0.9000
0.8000
>
=
0.7000
8 0.6000
8 0.5000
© 0.4000
= 0.3000
0.2000
0.1000
0.0000
ain
-
15
ol
-05
0
05
1
15
% TW Spread Captured
—@—2,100k
—e—2;200k
—e—2,500k
—e—2,1MM
—®—2;10MM
—@—5,100k
—@—5;200k
—@—5,500k
—@=5,1MM
—®=5;10MM
—@—10,100k
—@—10,200k
—e—10;500k
—e—10;1MM
10;10MM
Figure 36: Probability curve construct from chosen RFQ and calibration parameters, for varying
notional inputs and dealer counts. For each dealer count group, the notional increases the winning
probability for a fixed x. For each notional group, the dealer count decreases the winning probability
for a fixed x.
This demonstrates the additivity of the combined effects of features on the curve.
The %TW spread captured values still remain within an acceptable range, with a variation below
50% when varying multiple features simultaneously.
‘The notional can be seen to increase the probability of trade for each dealer count group for a
fixed x. Simultaneously, the dealer count can be seen to decrease the probability of trade for each
notional group for a fixed x. The assumption on the additive nature of feature impact on the curve
is therefore objectively validated by this plot.
‘As can also be noted, the « variations remain small when varying multiple features simultane-
ously.
5.4
Benchmarking
The model is inherently dependent on the chosen market spread input - Tradeweb in our case. A
suitable benchmark for the model is therefore the Tradeweb bid-offer spread. It is expected that the
quotes returned by the pricing component which are based on the probability curve model would
roughly fall within the range of the market spread.
‘A quote outside of the market bid-offer spread, here, could be attributed to the business decision
on the point at which to quote on the probability curve, as trading ultimately makes a decision on
this point. However, it may not be expected for a large proportion of inquiries (eg. >50%) to be
priced significantly outside the spread, as the quotes would then be misaligned with the competition.
In this case, it could instead be that the model is returning a probability curve showing a range of
spread captures outside of a competitive region. A model recalibration may be required to mitigate
this, based on expert judgement on the range of spread captures returned.
To test adherence to the benchmark, sample data was collected over a month of inquiries on a
129576: Winning-Probability Model
for EUGV
RFQ Pricing
Page 52 of 73
[git]
Branch: ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)
```
