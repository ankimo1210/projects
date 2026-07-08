# Page 037 - 日本語版

![Page 37](../assets/page_images/page_037.png)

## 日本語メモ

**該当箇所:** 5.2 Scenario Analysis and Stress Testing

ボラティリティケースと流動性ケースでのストレステスト。市場不安定化や低流動性下での性能を確認する。

## 原文OCR/Text Layer

> OCR由来のため、誤認識があります。正確な図表・数式・レイアウトは上のページ画像を確認してください。

```text
Morgan Stanley
Confidential
+ AP Score Diff: the AP score (average-precision score) is
a performance measurement statis-
tic for classification problems at various threshold settings. Additional documentation is made
available by the sklearn package developers [I]. The AP score can take values from 0 to 1.
We monitor the signed difference between AP score and baseline of % positives in the data
sample as:
APScoreDif f = APScore — %DoneInquiries
(17)
where % Done inquiries represents the % of positives in the data sample. We expect this
value to be positive for good model performance.
Accounting for all countries in scope (listed in sectior
for the metrics defined above, using expert experience an
thresholds can for instance be set as the following:
, acceptability thresholds can be set
istorical data. For our purposes, the
HR Diff (%)
AP Score Diff (%)
<=15
>=0
‘The quantitative thresholds detailed above are a general representation of acceptability, and
are typically considered as a group of scores rather than individual metrics. Lower scores can be
accepted based on expert advice on the dataset and corresponding market conditions at the time.
‘Two examples where expert interpretation may be applied are given below:
« Segmentation liquidity: countries with lower liquidity may be considered unlikely to form
a significant part of the inquiry flow, and as such lower scores are accepted.
+ Model overrides: knowledge on model overrides in production (described in section
[7) can
also help inform on the acceptability of scores. For example, lower scores are acceptable for
segments where the model is only applied to the pricing strategy of a subset of bonds, or
where the model is overriden for all bonds.
Additional information on metric monitoring and acceptability thresholds is given in section [9
Measures obtained on the out-of-sample set for the volatility test are presented in the table
below:
HR Diff (%)
AP Score Diff (%)
14
35.0
Preferred metrics and applicable metric thresholds for each segment are set following expert
advice as described above. Here they fall within the acceptable range, and therefore show that the
model is applicable to volatile market conditions.
Reviewing the same metrics for Gilts, the 10Y benchmark Gilt was chosen as a good indicator.
The figure below shows the TW spread over the first nine months of 2024 for this bond.
129576: Winning-Probability Model for
EUGV RFQ Pricing
Page
37 of 73
[git]
= Branch:
ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)
```
