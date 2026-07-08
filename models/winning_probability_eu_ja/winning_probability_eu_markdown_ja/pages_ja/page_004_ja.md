# Page 004 - 日本語版

![Page 4](../assets/page_images/page_004.png)

## 日本語メモ

**該当箇所:** 1 Executive Summary

モデル目的、概要、前提、性能評価、結果要約。RFQのスプレッド獲得率と約定確率の関係をロジスティック回帰で表す。

## 原文OCR/Text Layer

> OCR由来のため、誤認識があります。正確な図表・数式・レイアウトは上のページ画像を確認してください。

```text
Morgan Stanley
Confidential
1
Executive Summary
1.1.
Model Purpose and Intended Use
The purpose of the probability curve model described in the document is to represent the re-
lationship between market spread captured and probability of trading. The model will be used
in the automated market-making pricing components, where it is intended to assist in the quote
construction process.
The specific scope of application is the European Government (EUGV) and UK Government
(UKGV) bond spaces, including UK inflation. The model will reside in algorithms captured by the
Model Control System (MCS) legal entity.
1.2.
Model Description Summary
The model uses standard logistic regression methods to estimate the relationship between spread
and trading probability, based on historical auction data available to the Firm. The model outputs
feature coefficients used to describe this relationship, in order to generate probability curves for
incoming auctions - see section
[2] for details on probability curves, and section
2-|for details on
the trade auction process.
Inputs to the model include market data, as well as information on the security being traded
at the time. Other information concerning the parameters of incoming auctions is also included.
The model has a tiering of 1 as determined by its high ‘Materiality’ and medium ‘Complexity’
ratings.
Materiality and Complexity are each derived from two sub-tiers. For Materiality, the two sub-
tiers are ‘Usage’ and ‘Reliance’. For Complexity the two sub-tiers are ‘Specificity’ and ‘Processing’.
Guidance on tiering assessments for each component can be found in section 5 of the tiering docu-
mentation [I].
‘The Materiality of the model is high due to high Usage and medium Reliance.
The model has high Usage. Models in Macro can be used by different algos with different
metrics, Metrics are not comparable, and therefore a conservative approach has been taken.
The model has medium Reliance. The quoting algorithm can continue to price clients even
when the model is (a) either not operational, or (b) has not been calibrated. Prices sent to clients
are subject to rigorous price verification and benchmarking to external reference prices prior to
publication.
The Complexity of the model is medium due to medium Specificity and medium Processing.
The model has medium Specificity as the model provides a point of estimate of the probability of
execution at a given bid-offer spread.
‘The model has medium Processing as the calibration, run off-line, is based on logistic regression.
‘As per the tiering documentation, the overall tier of the model is 1.
1.3.
Key Assumptions and Limitations
The model is based on the following key assumptions, which are detailed further in sectior
+ The auctions seen by MS are sufficient to represent the market as a whole - further detail on
this is provided in sectioi
+ The probability curve will resemble a sigmoid function.
+ The auction tie rate is negligible.
129576: Winning-Probability Model for
EUGV RFQ Pricing
Page 4 of 73
[git]
= Branch:
ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)
```
