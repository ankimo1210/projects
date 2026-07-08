# Page 051 - 日本語版

![Page 51](../assets/page_images/page_051.png)

## 日本語メモ

**該当箇所:** 5.3 Sensitivity Analysis / 5.4 Benchmarking

market spread captured、dealer count、life remaining、duration/PV01、notional等への感応度と、外部・内部ベンチマークとの比較。

## 原文OCR/Text Layer

> OCR由来のため、誤認識があります。正確な図表・数式・レイアウトは上のページ画像を確認してください。

```text
Morgan Stanley
Confidential
5.3.5
Log of Notional
Similarly to the above, the results for the notional feature are presented below, with size ranging
from 100,000 to 20,000,000:
Probability curves for various notionals
1.0000
0.9000
0.8000
= 0.7000
8 06000
‘©
0 5000
=
0 4000
= 0.3000
0.2000
0.1000
0.0000
-15
-1
05
0
05
1
15
% TW Spread Captured
—e—100k
—e—-500k
—e-1MM
—e®—5MM
—®—10MM
—e—20MM
Figure 35: Probability curve construct from chosen RFQ and calibration parameters, for varying
notional inputs. It is shown here that the notional increases the probability of winning the auction
for a fixed «. The %TW spread captured values remain within an acceptable range, with a variation
below 50% from 100k to 20MM notional.
The rationale behind the positive translation of the curve with log of notional is detailed in
The translation of the curve is again small, and in turn so are the « variations.
Log of notional is not a feature in the Gilts three-feature model, and therefore does not need to
be validated in this context.
5.3.6
Multi-variable Sensitivity
The previous sections demonstrated the effects of varying input features individually. The impact
on the curve was a translation along the x-axis in every case study.
‘As a result, and considering no variable interaction within the model, an assumption can be
made that modifying multiple features in combination can result in further translations of the curve
along the x-axis.
To test this, a series of curves were constructed by varying both the notional and dealer count
input features. The dealer counts chosen were 2, 5 and 10. The notional was varied between 100k
and 10MM. In the plot below, the pairing is shown in the legend as ‘dealer count; notional’. Results
129576: Winning-Probability Model for EUGV
RFQ Pricing
Page 51 of 73
[git]
Branch: ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)
```
