# Page 025 - 日本語版

![Page 25](../assets/page_images/page_025.png)

## 日本語メモ

**該当箇所:** 4 Model Development and Selection Process

セグメンテーション、特徴量選択、代替アプローチ、ステークホルダーや独立ソースからの貢献を整理する。

## 原文OCR/Text Layer

> OCR由来のため、誤認識があります。正確な図表・数式・レイアウトは上のページ画像を確認してください。

```text
Morgan Stanley
Confidential
+ Available historical data on inquiry state - win/loss of the auction, visible data if won (eg.
cover prices)
+ Security details - bond data such as maturity date, issue date, dpdy, issuing country, coupon,
repo rate, currency, description, yield through time, price through time
Expert judgement and statistical significance tests are used to create a combination of features
relevant to the segmented dataset. The combination is also selected in such a way that minimal (or
no) change is made from one dataset’s chosen features to the other, in order to simplify the model
and increase maintainability.
Parameter significance metrics are output in the calibration Jupyter notebook, and can as-
sist with judgement on whether the model needs reviewing. Example metrics are illustrated in
section 5.L1l
In addition, cross-correlation maps can be drawn to narrow down the impact of features on the
dataset. If parameters are highly correlated, they can be eliminated to simplify the model and its
implementation in production. On the other hand, it may be decided to keep parameters in if the
expectation is that they make significant business sense.
Such a map is shown below in figure [J] In this map, three additional potential features are
shown to demonstrate the elimination process:
+ coverQuote: The second-best price for the RFQ, only made available for ‘Done’ inquiries.
Further detail is provided in section
« twSpread: The spread of the particular product in the Tradeweb marketplace.
+ absPv01: The absolute value of the pv01, or change in ‘present value’ of a bond with a
1-basis point move in yield.
It can be seen, for example, that absolute pv01 is relatively highly correlated to the quantity
feature chosen. Similar observations can be made with cover quotes and Tradeweb spreads, which
correlate well with life remaining and can thus be excluded from the list of features. The business
regards the percent life remaining parameter as relevant information to the model - this may be
reviewed in the future in accordance with MRM procedures.
:
Winning-Probability Model for EUGV RFQ Pricing
of 73
[git]
= Branch:
ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)
```
