# Page 017 - 日本語版

![Page 17](../assets/page_images/page_017.png)

## 日本語メモ

**該当箇所:** 3.1 Model Assumptions

モデルの主要前提。MSが観測するオークションの代表性、hit-rate曲線のシグモイド形状、タイ率、参加者行動の安定性、ロジスティック回帰の統計前提など。

## 原文OCR/Text Layer

> OCR由来のため、誤認識があります。正確な図表・数式・レイアウトは上のページ画像を確認してください。

```text
Morgan Stanley
Confidential
Tie RFQ % rate per day 2024
SSSSSSSSSSSSESSSESSSSSSSSESSSSSSssgssggssgs
RSRRRRRARARARARRARRARARARARRARRARARARARARRAR
Ties Rate
-++++++++ 30 per. Mov. Avg. (Ties Rate)
Figure 8: Daily tied inquiry rate across markets and EUGV countries. The tie rate is deemed small
enough (around 1%) through time to validate the insignificant tie rate assumption.
4. The market-stability assumption is addressed in part via ex-post analysis, but the assumption
is largely out of the control of the model developer.
Nonetheless, it is common practice to
operate under the assumption that the market remains stable between recalibrations.
‘The model described in this document uses a standard logistic regression approach (see sec-
through which the following standard assumptions are made from a statistical perspec-
1. Binary response variable: The response variable is assumed to be binary - eg.
‘true’ or
‘false’. In the probability curve model, the variable is defined as a binary ‘win’ or ‘loss’ of the
auction - see section
[3.3.3] for further detail.
2. Independence of observations: The observations considered are independent from each
other. In the model described in this document, auctions included in the datasets are unique
~ see sectio:
for further detail on datasets and inputs.
3. Multicollinearity: The correlation between independent variables considered is negligible.
This is illustrated in section
4, Extreme outliers: There are no extreme outliers in the dataset.
In the probability curve
model, single-dealer inquiries as well as other potential outliers are excluded from the dataset.
This process is explained in section
5. Linear relationship between logit and features: The response of the logistic function
to the explanatory variables is linear. For the model in this document, the impact of feature
variables on the logit is detailed in section 2.4] and tested in section
129576: Winning-Probability Model
for EUGV RFQ Pricing
Page 17 of 73
[git]
Branch: ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)
```
