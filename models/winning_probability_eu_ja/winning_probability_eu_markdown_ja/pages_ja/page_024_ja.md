# Page 024 - 日本語版

![Page 24](../assets/page_images/page_024.png)

## 日本語メモ

**該当箇所:** 4 Model Development and Selection Process

セグメンテーション、特徴量選択、代替アプローチ、ステークホルダーや独立ソースからの貢献を整理する。

## 原文OCR/Text Layer

> OCR由来のため、誤認識があります。正確な図表・数式・レイアウトは上のページ画像を確認してください。

```text
Morgan Stanley
Confidential
Framework
Components
Python
numpy, pandas, scipy, sklearn
‘The parameters used in the implementation of the logistic regression model are the following
default settings from the sklearn package:
Solver
C
Ibfgs
1.0
4
Model Development and Selection Process
4.1
Model Segmentation and Variable Selection
Both model segmentation and variable selection processes are based on a combination between
expert input, and statistical metrics that allow us to quantitatively measure the impact on model
accuracy.
4.1.1
Model Segmentation
Currently one curve model is generally calibrated per client tier and per country, with an aim
to keep to a minimum the segmentation required. Example segmented datasets are presented in
i
Additional example data segmentation is tested and documented in section
The samples are generally equally weighed - this means that the model is calibrated by ticket
(RFQ) count, as each inquiry is treated evenly. This ticket count approach can however be further
broken down - in some cases (certain client groups or product sets), a pvOl-weighted sampling
methodology is preferred by the business to better answer client requirements.
The data can additionally be segmented into maturity ranges for countries where expert opinion
suggests that calibrations containing lower bond maturities do not capture well the behaviour of
higher maturities. This is particularly true for countries which offer a larger universe of bonds - eg.
Italy.
The exact segmentation can subject to change according to on-going talks with trading on
business focus, and will be a continued point of discussion. However the modelling strategy remains
the same.
4.1.2.
Variable Selection
The curve calibration process uses a combination of features, as any of the following:
+ Market data through time (any market deemed relevant by the business) - bid, offer, mid,
sizes, liquidity, available trade information, and any derived calculation (eg.
distance to
market composites)
« Available RFQ details - date, time, dealer count, side, notional, pv01, client-related informa-
tion, inquiry outcome, protocol, leg count, leg number
+ MS internal price construction algorithm outputs - quotes returned, trading probability re-
turned, historical probability curve parameters used for each RFQ, pricing method
+ Voice trader historical RFQ data - quotes returned, pricing method
129576: Winning-Probability Model
for
EUGV
RFQ Pricing
Page 24 of 73
[git]
= Branch:
ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)
```
